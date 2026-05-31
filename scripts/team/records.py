#!/usr/bin/env python3

import requests
import json
import time

CREATOR = "ajedrezconzeta"
TOP_N = 5

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})


# =========================
# GET USER TOURNAMENTS (REAL API WAY)
# =========================

def get_user_tournaments(user, max_pages=20):
    """
    IMPORTANT:
    Lichess does NOT give full creator history via HTML.
    We use tournament search endpoint instead.
    """

    all_tournaments = []

    for page in range(max_pages):

        url = "https://lichess.org/api/tournament"

        params = {
            "page": page,
            "status": "finished",
            "user": user
        }

        try:
            r = session.get(url, params=params, timeout=10)

            if r.status_code != 200:
                break

            data = r.json()

            if not isinstance(data, list) or not data:
                break

            all_tournaments.extend(data)

            time.sleep(0.2)

        except:
            break

    return all_tournaments


# =========================
# SAFE RESULTS PARSER
# =========================

def get_results(tid):
    url = f"https://lichess.org/api/tournament/{tid}/results"

    try:
        r = session.get(url, timeout=10)
        if r.status_code != 200:
            return []

        return [
            json.loads(line)
            for line in r.text.splitlines()
            if line.strip()
        ]

    except:
        return []


# =========================
# MAIN
# =========================

print("Lade Creator Turniere...")

tournaments = get_user_tournaments(CREATOR, max_pages=30)

print(f"Gefunden: {len(tournaments)} Turniere")

# =========================
# FILTER TEAM BATTLES
# =========================

team_battles = [
    t for t in tournaments
    if isinstance(t, dict) and t.get("teamBattle") is True
]

print(f"Team Battles: {len(team_battles)}")

# =========================
# ANALYZE
# =========================

records = []

for t in team_battles:

    tid = t.get("id")
    name = t.get("fullName", tid)

    print(f"Analysiere: {name}")

    results = get_results(tid)

    best_user = None
    best_score = -1

    for r in results:

        if not isinstance(r, dict):
            continue

        user = r.get("username")
        score = r.get("score", 0)

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
# OUTPUT
# =========================

if not records:
    print("\n❌ Keine Team Battles vom User gefunden.")
    exit()

records.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 60)
print("🏆 CREATOR TEAM BATTLE ANALYSIS")
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
