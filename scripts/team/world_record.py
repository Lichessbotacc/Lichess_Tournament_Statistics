#!/usr/bin/env python3
import requests
import json
import os
from collections import defaultdict

# =========================
# ⚙️ CONFIG
# =========================

VARIANT = "ultrabullet"
MAX_TOURNEYS_PER_SOURCE = 80

DATA_FILE = "team_db.json"
SOURCES_FILE = "team_sources.json"

headers = {"Accept": "application/x-ndjson"}

# =========================
# 💾 LOAD DB
# =========================

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
else:
    db = {
        "teams": {},
        "seen_tournaments": []
    }

# =========================
# 🔎 HELPERS
# =========================

def load_team_events(team_id):
    url = f"https://lichess.org/api/team/{team_id}/arena?status=finished"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []

    return [json.loads(l) for l in r.text.splitlines() if l.strip()]


def get_results(tid):
    url = f"https://lichess.org/api/tournament/{tid}/results"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []

    return [json.loads(l) for l in r.text.splitlines() if l.strip()]


# =========================
# 🔥 TEAM SOURCES (AUTO EXPANSION)
# =========================

# Start-Seed (wird automatisch erweitert!)
if "sources" not in db:
    db["sources"] = [
        "chesslandia-fan-club-only-under-of-18-years"
    ]

sources = db["sources"]

# =========================
# 🚀 DISCOVER NEW TOURNAMENTS
# =========================

new_tournaments = []

for team in sources:

    events = load_team_events(team)[:MAX_TOURNEYS_PER_SOURCE]

    for t in events:

        tid = t["id"]

        if tid in db["seen_tournaments"]:
            continue

        name = t.get("fullName", "").lower()

        if VARIANT != "all" and VARIANT not in name:
            continue

        new_tournaments.append(tid)
        db["seen_tournaments"].append(tid)

# =========================
# 🧠 PROCESS TOURNAMENTS
# =========================

for tid in new_tournaments:

    results = get_results(tid)

    team_scores = defaultdict(int)

    for r in results:
        team = r.get("team")
        score = r.get("score", 0)

        if team:
            team_scores[team] += score

    if not team_scores:
        continue

    best_team, best_score = max(team_scores.items(), key=lambda x: x[1])

    # =========================
    # 📊 STORE IN DB
    # =========================

    if best_team not in db["teams"]:
        db["teams"][best_team] = {
            "score": 0,
            "events": 0
        }

    db["teams"][best_team]["score"] += best_score
    db["teams"][best_team]["events"] += 1

# =========================
# 🏆 RANKING
# =========================

sorted_teams = sorted(
    db["teams"].items(),
    key=lambda x: x[1]["score"],
    reverse=True
)[:500]

print("\n🏆 TOP 500 TEAM RANKING")
print(f"VARIANT: {VARIANT}\n")

for i, (team, data) in enumerate(sorted_teams, 1):
    print(f"{i}. {team} — {data['score']} pts ({data['events']} events)")

# =========================
# 💾 SAVE DB
# =========================

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, indent=2)
