#!/usr/bin/env python3

import requests
import json
import time
from collections import defaultdict

BASE = "https://lichess.org"
TOP_N = 5

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (TeamBattleScanner)"
})

# =========================
# SAFE REQUEST
# =========================

def safe_get_json(url, params=None):
    try:
        r = session.get(url, params=params, timeout=12)

        if r.status_code != 200:
            return None

        return r.json()

    except:
        return None


def safe_get_text(url):
    try:
        r = session.get(url, timeout=12)

        if r.status_code != 200:
            return None

        return r.text

    except:
        return None


# =========================
# LOAD ALL TOURNAMENTS (PAGED)
# =========================

def load_tournaments(max_pages=20):
    all_tournaments = []

    for page in range(max_pages):

        data = safe_get_json(
            f"{BASE}/api/tournament",
            params={"page": page, "status": "finished"}
        )

        if not data:
            break

        if isinstance(data, list):
            all_tournaments.extend(data)

        time.sleep(0.2)  # mild rate-limit protection

    return all_tournaments


# =========================
# FILTER TEAM BATTLES SAFELY
# =========================

def is_team_battle(t):
    return (
        isinstance(t, dict)
        and t.get("teamBattle") is True
    )


# =========================
# PARSE RESULTS SAFE (NDJSON)
# =========================

def parse_results(tid):
    text = safe_get_text(f"{BASE}/api/tournament/{tid}/results")

    if not text:
        return []

    results = []

    for line in text.splitlines():

        if not line.strip():
            continue

        try:
            obj = json.loads(line)
        except:
            continue

        if isinstance(obj, dict):
            results.append(obj)

    return results


# =========================
# PROCESS ONE TOURNAMENT
# =========================

def process_tournament(t):
    tid = t.get("id")
    name = t.get("fullName", tid)

    if not tid:
        return None

    results = parse_results(tid)

    best_user = None
    best_score = -1

    for r in results:

        if not isinstance(r, dict):
            continue

        user = r.get("username")
        score = r.get("score")

        if not user or not isinstance(score, (int, float)):
            continue

        if score > best_score:
            best_score = score
            best_user = user

    if not best_user:
        return None

    return {
        "player": best_user,
        "score": best_score,
        "id": tid,
        "name": name,
        "url": f"{BASE}/tournament/{tid}"
    }


# =========================
# MAIN
# =========================

print("Lade Turniere...")

tournaments = load_tournaments(max_pages=25)

print(f"Total geladen: {len(tournaments)}")

team_battles = [t for t in tournaments if is_team_battle(t)]

print(f"Team Battles: {len(team_battles)}")

records = []

print("Analysiere...")

for i, t in enumerate(team_battles):

    res = process_tournament(t)

    if res:
        records.append(res)

    if i % 10 == 0:
        time.sleep(0.1)


# =========================
# OUTPUT
# =========================

if not records:
    print("\n❌ Keine Daten gefunden (oder keine öffentlichen Team Battles vorhanden).")
    exit()

records.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 60)
print("🏆 BULLETPROOF TEAM BATTLE WORLD SCANNER")
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
