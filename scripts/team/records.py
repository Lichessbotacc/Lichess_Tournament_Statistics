#!/usr/bin/env python3

import requests
import re
import json

CREATOR = "ajedrezconzeta"
TOP_N = 5


def get_json(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None


# =========================
# GET TOURNAMENT IDS
# =========================

url = f"https://lichess.org/@/{CREATOR}/tournaments/created"
html = requests.get(url).text

tournament_ids = sorted(set(
    re.findall(r"/tournament/([A-Za-z0-9]{8})", html)
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

    name = info.get("name", tid)
    print(f"Scanne: {name}")

    results_url = f"https://lichess.org/api/tournament/{tid}/results"

    r = requests.get(results_url, headers={
        "Accept": "application/x-ndjson"
    })

    if r.status_code != 200:
        continue

    best_player = None
    best_score = -1

    for line in r.text.splitlines():

        if not line.strip():
            continue

        try:
            data = json.loads(line)
        except:
            continue

        username = data.get("username")
        score = data.get("score", 0)

        if username and score > best_score:
            best_score = score
            best_player = username

    if best_player is None:
        continue

    records.append({
        "player": best_player,
        "score": best_score,
        "id": tid,
        "url": f"https://lichess.org/tournament/{tid}"
    })

# =========================
# RESULT
# =========================

if not records:
    print("Keine Daten gefunden.")
    raise SystemExit(0)

records.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 60)
print("🏆 WORLD RECORD (LICHESS TOURNAMENT SCORE)")
print("=" * 60)

top = records[0]

print(f"Player: {top['player']}")
print(f"Score : {top['score']}")
print(f"Link  : {top['url']}")

print("\nTOP LIST\n")

for i, r in enumerate(records[:TOP_N], 1):
    print(f"{i}. {r['player']} - {r['score']} Punkte")
    print(f"   {r['url']}")
