#!/usr/bin/env python3

import requests
import re
import json
from collections import defaultdict

CREATOR = "ajedrezconzeta"
TOP_N = 5

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})


# =========================
# 1. GET CREATOR TOURNAMENT IDS (HTML SEED)
# =========================

print("Lade Creator Seite...")

url = f"https://lichess.org/@/{CREATOR}/tournaments/created"
html = session.get(url).text

tournament_ids = list(set(
    re.findall(r"/tournament/([A-Za-z0-9]{8})", html)
))

print(f"Gefunden (HTML): {len(tournament_ids)} Turniere")


# =========================
# 2. SAFE FETCH TOURNAMENT INFO
# =========================

def get_json(url):
    try:
        r = session.get(url, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None


# =========================
# 3. CHECK TEAM BATTLES
# =========================

team_battles = []

for tid in tournament_ids:

    info = get_json(f"https://lichess.org/api/tournament/{tid}")
    if not info:
        continue

    if info.get("teamBattle") is True:
        team_battles.append(info)

print(f"Team Battles: {len(team_battles)}")


# =========================
# 4. ANALYZE RESULTS
# =========================

records = []

for t in team_battles:

    tid = t["id"]
    name = t.get("fullName", tid)

    print(f"Analysiere: {name}")

    r = session.get(
        f"https://lichess.org/api/tournament/{tid}/results",
        headers={"Accept": "application/x-ndjson"}
    )

    if r.status_code != 200:
        continue

    best_user = None
    best_score = -1

    for line in r.text.splitlines():

        try:
            data = json.loads(line)
        except:
            continue

        if not isinstance(data, dict):
            continue

        user = data.get("username")
        score = data.get("score", 0)

        if user and score > best_score:
            best_user = user
            best_score = score

    if best_user:
        records.append({
            "player": best_user,
            "score": best_score,
            "name": name,
            "url": f"https://lichess.org/tournament/{tid}"
        })


# =========================
# 5. OUTPUT
# =========================

if not records:
    print("\n❌ Keine Team Battles gefunden (wahrscheinlich keine im HTML sichtbar).")
    exit()

records.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 60)
print("🏆 FINAL TEAM BATTLE SCANNER")
print("=" * 60)

top = records[0]

print(f"Best Player: {top['player']}")
print(f"Score      : {top['score']}")
print(f"Tournament : {top['name']}")
print(f"Link       : {top['url']}")

print("\nTOP LIST\n")

for i, r in enumerate(records[:TOP_N], 1):
    print(f"{i}. {r['player']} - {r['score']} Punkte")
    print(f"   {r['name']}")
    print(f"   {r['url']}")
