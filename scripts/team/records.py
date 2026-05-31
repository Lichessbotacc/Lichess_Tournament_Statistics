#!/usr/bin/env python3

import requests
import json
from collections import defaultdict

# =========================
# CONFIG
# =========================

CREATOR = "ajedrezconzeta"
TOP_N = 5

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

# =========================
# LOAD TOURNAMENT IDS
# =========================

url = f"https://lichess.org/@/{CREATOR}/tournaments/created"
r = requests.get(url)

if r.status_code != 200:
    print("Fehler beim Laden der Creator-Seite")
    raise SystemExit(1)

html = r.text

# Turnier-IDs extrahieren
tournament_ids = sorted(set(
    __import__("re").findall(r"/tournament/([A-Za-z0-9]{8})", html)
))

print(f"Gefundene Turniere: {len(tournament_ids)}")

# =========================
# PROCESS TOURNAMENTS
# =========================

records = []

for tid in tournament_ids:

    info_url = f"https://lichess.org/api/tournament/{tid}"
    info = get_json(info_url)

    if not info:
        continue

    # nur Team Battles
    if not info.get("teamBattle"):
        continue

    print(f"Scanne Team-Battle: {tid}")

    results_url = f"https://lichess.org/api/tournament/{tid}/results"
    r = requests.get(results_url, headers={"Accept": "application/x-ndjson"})

    if r.status_code != 200:
        continue

    team_scores = defaultdict(int)

    for line in r.text.splitlines():
        if not line.strip():
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        team = data.get("team")
        score = data.get("score", 0)

        if team:
            team_scores[team] += score

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
    print("Keine Team-Battle-Daten gefunden.")
    raise SystemExit(0)

records.sort(key=lambda x: x["score"], reverse=True)

world_record = records[0]

print("\n" + "=" * 60)
print("TEAM BATTLE WORLD RECORD")
print("=" * 60)

print(f"Team : {world_record['team']}")
print(f"Score: {world_record['score']}")
print(f"Link : {world_record['url']}")

print("\nTOP TURNIERE\n")

for i, r in enumerate(records[:TOP_N], 1):
    print(
        f"{i}. {r['team']} - {r['score']} Punkte\n"
        f"   {r['url']}"
    )
