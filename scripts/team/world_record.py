#!/usr/bin/env python3
import requests
import json
import os

TEAM_ID = "ANY"  # optional Filter (z.B. nur bestimmte Team-Events)
VARIANT = "ultrabullet"  # ultrabullet, bullet, blitz, rapid
MAX_TOURNEYS = 200000

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# 1. TEAM BATTLE TURNIERE LADEN
# =========================

url = "https://lichess.org/api/team/battle"

response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Fehler beim Laden der Team Battles")
    exit()

tournaments = [
    json.loads(line)
    for line in response.text.splitlines()
    if line.strip()
]

# =========================
# 2. FILTER (VARIANT)
# =========================

filtered = []

for t in tournaments:
    perf = str(t.get("perf", "")).lower()

    if VARIANT == "all" or VARIANT in perf:
        filtered.append(t)

filtered = filtered[:MAX_TOURNEYS]

print(f"\n🏆 TEAM BATTLE ANALYSIS")
print(f"VARIANT: {VARIANT}")
print(f"TURNIERE: {len(filtered)}\n")

# =========================
# 3. REKORD-SUCHE
# =========================

best_score = 0
best_team = None
best_tournament = None

for t in filtered:

    tid = t["id"]

    # Team standings direkt aus API
    url = f"https://lichess.org/api/tournament/{tid}/results"

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        continue

    teams = {}

    for line in r.text.splitlines():
        if not line.strip():
            continue

        data = json.loads(line)

        team = data.get("team")
        score = data.get("score", 0)

        if not team:
            continue

        teams[team] = teams.get(team, 0) + score

    if not teams:
        continue

    # bestes Team im Turnier
    top_team = max(teams.items(), key=lambda x: x[1])

    team_name, team_score = top_team

    print(f"{t['fullName']}")
    print(f"🥇 {team_name}: {team_score}\n")

    # global record check
    if team_score > best_score:
        best_score = team_score
        best_team = team_name
        best_tournament = t

# =========================
# 4. OUTPUT
# =========================

print("\n" + "=" * 50)
print("🏆 ULTRABULLET TEAM SCORE WORLD RECORD")
print("=" * 50)

if best_team:
    print(f"Team: {best_team}")
    print(f"Score: {best_score}")
    print(f"Turnier: https://lichess.org/tournament/{best_tournament['id']}")
    print(f"Name: {best_tournament['fullName']}")
else:
    print("Keine Daten gefunden.")
