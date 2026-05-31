#!/usr/bin/env python3

import requests
import json
from collections import defaultdict

# =========================
# CONFIG
# =========================

CREATOR = "ajedrezconzeta"
TOP_N = 10

# =========================
# HELPERS
# =========================

def get_json(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

def get_ndjson(url):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return []
        return r.text.splitlines()
    except Exception:
        return []

# =========================
# GET CREATED TOURNAMENTS
# =========================

url = f"https://lichess.org/@/{CREATOR}/tournaments/created"
r = requests.get(url)

if r.status_code != 200:
    print("Fehler beim Laden der Creator-Seite")
    raise SystemExit(1)

html = r.text

tournament_ids = sorted(set(
    __import__("re").findall(r"/tournament/([A-Za-z0-9]{8})", html)
))

print(f"Gefundene Turniere: {len(tournament_ids)}")

# =========================
# PROCESS
# =========================

records = []

for tid in tournament_ids:

    info = get_json(f"https://lichess.org/api/tournament/{tid}")
    if not info:
        continue

    # nur echte Team Battles
    if not info.get("teamBattle"):
        continue

    print(f"\nScanne Team Battle: {info.get('name', tid)}")

    # =========================
    # IMPORTANT FIX:
    # Use GAME STREAM instead of results
    # =========================

    games_url = f"https://lichess.org/api/tournament/{tid}/games"

    games = get_ndjson(games_url)

    team_scores = defaultdict(int)

    for line in games:
        if not line.strip():
            continue

        try:
            game = json.loads(line)
        except:
            continue

        # Team info is stored in player tags or metadata
        white_team = game.get("whiteTeam")
        black_team = game.get("blackTeam")

        winner = game.get("winner")  # "white", "black", or None

        if not white_team or not black_team:
            continue

        # scoring logic
        if winner == "white":
            team_scores[white_team] += 2
        elif winner == "black":
            team_scores[black_team] += 2
        else:
            team_scores[white_team] += 1
            team_scores[black_team] += 1

    if not team_scores:
        continue

    best_team, best_score = max(team_scores.items(), key=lambda x: x[1])

    records.append({
        "team": best_team,
        "score": best_score,
        "id": tid,
        "url": f"https://lichess.org/tournament/{tid}"
    })

# =========================
# RESULT
# =========================

if not records:
    print("\n❌ Keine Team Battle Daten gefunden.")
    raise SystemExit(0)

records.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 60)
print("🏆 TEAM BATTLE WORLD RECORD")
print("=" * 60)

top = records[0]

print(f"Team : {top['team']}")
print(f"Score: {top['score']}")
print(f"Link : {top['url']}")

print("\nTOP TURNIERE\n")

for i, r in enumerate(records[:TOP_N], 1):
    print(f"{i}. {r['team']} - {r['score']} Punkte")
    print(f"   {r['url']}")
