#!/usr/bin/env python3
import requests
import json
import os
from collections import defaultdict

# =========================
# ⚙️ CONFIG
# =========================

VARIANT = "ultrabullet"
MAX_TEAMS = 200          # wie viele Teams maximal gecrawlt werden
MAX_TOURNEYS = 50        # pro Team

DATA_FILE = "global_team_db.json"

headers = {"Accept": "application/x-ndjson"}

# =========================
# 💾 LOAD DB
# =========================

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
else:
    db = {
        "teams": set(),
        "seen_tournaments": [],
        "records": []
    }

# JSON can't store set → fix
db["teams"] = set(db.get("teams", []))

# =========================
# 🌱 SEED TEAMS
# =========================

if not db["teams"]:
    db["teams"].update([
        "chesslandia-fan-club-only-under-of-18-years",
        "team-chess-players",
        "lichess",
        "chess-network",
    ])

# =========================
# 🔎 HELPERS
# =========================

def load_team_events(team):
    url = f"https://lichess.org/api/team/{team}/arena?status=finished"
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
# 🚀 CRAWL PHASE
# =========================

new_teams_found = set()

for team in list(db["teams"])[:MAX_TEAMS]:

    tournaments = load_team_events(team)[:MAX_TOURNEYS]

    for t in tournaments:

        tid = t["id"]

        if tid in db["seen_tournaments"]:
            continue

        name = t.get("fullName", "").lower()

        if VARIANT != "all" and VARIANT not in name:
            continue

        results = get_results(tid)

        team_scores = defaultdict(int)

        for r in results:
            tname = r.get("team")
            score = r.get("score", 0)

            if tname:
                team_scores[tname] += score

        if not team_scores:
            continue

        best_team, best_score = max(team_scores.items(), key=lambda x: x[1])

        # =========================
        # 🏆 RECORD STORE
        # =========================

        record = {
            "team": best_team,
            "score": best_score,
            "tournament": tid,
            "name": t.get("fullName", "")
        }

        db["records"].append(record)
        db["seen_tournaments"].append(tid)

        print(f"\n🏆 {t['fullName']}")
        print(f"🥇 {best_team}: {best_score}")
        print(f"🔗 https://lichess.org/tournament/{tid}")

        # =========================
        # 🌍 DISCOVER NEW TEAMS
        # =========================

        for r in results:
            if r.get("team"):
                new_teams_found.add(r["team"])

# =========================
# 🌱 EXPAND TEAM GRAPH
# =========================

for t in new_teams_found:
    if len(db["teams"]) < MAX_TEAMS:
        db["teams"].add(t)

# =========================
# 🏆 GLOBAL RECORD
# =========================

if db["records"]:
    best = max(db["records"], key=lambda x: x["score"])

    print("\n" + "=" * 60)
    print("🏆 GLOBAL TEAM WORLD RECORD")
    print("=" * 60)
    print(f"Team: {best['team']}")
    print(f"Score: {best['score']}")
    print(f"Tournament: https://lichess.org/tournament/{best['tournament']}")
    print(f"Name: {best['name']}")

# =========================
# 💾 SAVE DB
# =========================

db["teams"] = list(db["teams"])

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, indent=2)
