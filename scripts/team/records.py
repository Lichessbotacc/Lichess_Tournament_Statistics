#!/usr/bin/env python3

import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

BASE = "https://lichess.org"
TOP_N = 5

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})


# =========================
# GET ALL TOURNAMENTS (PAGED)
# =========================

def fetch_page(page):
    url = f"{BASE}/api/tournament"
    params = {
        "page": page,
        "status": "finished"
    }

    try:
        r = session.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []
        return r.json()
    except:
        return []


def get_all_tournaments(max_pages=15):
    all_t = []

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(fetch_page, p) for p in range(max_pages)]

        for f in as_completed(futures):
            data = f.result()
            if data:
                all_t.extend(data)

    return all_t


# =========================
# RESULTS PARSER
# =========================

def get_results(tid):
    url = f"{BASE}/api/tournament/{tid}/results"

    try:
        r = session.get(url, timeout=10)
        if r.status_code != 200:
            return []

        return [json.loads(l) for l in r.text.splitlines() if l.strip()]
    except:
        return []


# =========================
# LOAD TOURNAMENTS
# =========================

print("Lade Turniere...")

tournaments = get_all_tournaments(max_pages=20)

print(f"Total Turniere geladen: {len(tournaments)}")

# =========================
# FILTER TEAM BATTLES
# =========================

team_battles = [t for t in tournaments if t.get("teamBattle")]

print(f"Team Battles gefunden: {len(team_battles)}")

# =========================
# ANALYZE IN PARALLEL
# =========================

records = []

def process(t):
    tid = t.get("id")
    name = t.get("fullName", tid)

    results = get_results(tid)

    best_user = None
    best_score = -1

    for r in results:
        u = r.get("username")
        s = r.get("score", 0)

        if u and s > best_score:
            best_score = s
            best_user = u

    if not best_user:
        return None

    return {
        "player": best_user,
        "score": best_score,
        "id": tid,
        "name": name,
        "url": f"{BASE}/tournament/{tid}"
    }


print("Analysiere Team Battles...")

with ThreadPoolExecutor(max_workers=10) as ex:
    futures = [ex.submit(process, t) for t in team_battles]

    for f in as_completed(futures):
        res = f.result()
        if res:
            records.append(res)


# =========================
# RESULT
# =========================

if not records:
    print("Keine Daten gefunden.")
    exit()

records.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 60)
print("🏆 ULTRA TEAM BATTLE WORLD SCANNER")
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
