
#!/usr/bin/env python3

import requests
import json

TOP_N = 5


def search_team_battles(max_pages=5):
    """
    Lichess search API paginiert Ergebnisse.
    Wir sammeln mehrere Seiten.
    """
    all_tournaments = []

    for page in range(max_pages):
        url = "https://lichess.org/api/tournament"

        params = {
            "page": page,
            "perfType": "",
            "status": "finished"
        }

        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            break

        try:
            data = r.json()
        except:
            break

        if not data:
            break

        for t in data:
            all_tournaments.append(t)

    return all_tournaments


def get_results(tid):
    url = f"https://lichess.org/api/tournament/{tid}/results"
    r = requests.get(url, headers={"Accept": "application/x-ndjson"}, timeout=10)

    if r.status_code != 200:
        return []

    results = []
    for line in r.text.splitlines():
        try:
            results.append(json.loads(line))
        except:
            pass

    return results


# =========================
# LOAD TOURNAMENTS
# =========================

print("Lade Turniere...")

tournaments = search_team_battles(max_pages=10)

print(f"Gefunden: {len(tournaments)} Turniere")

# =========================
# FILTER TEAM BATTLES
# =========================

team_battles = []

for t in tournaments:

    if not t.get("teamBattle"):
        continue

    team_battles.append(t)

print(f"Team Battles: {len(team_battles)}")

# =========================
# ANALYZE
# =========================

records = []

for t in team_battles:

    tid = t["id"]
    name = t.get("fullName", tid)

    print(f"Scanne: {name}")

    results = get_results(tid)

    best_player = None
    best_score = -1

    for r in results:

        user = r.get("username")
        score = r.get("score", 0)

        if user and score > best_score:
            best_score = score
            best_player = user

    if not best_player:
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
    exit()

records.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 60)
print("🏆 TEAM BATTLE WORLD RECORD (REAL DATA)")
print("=" * 60)

top = records[0]

print(f"Player: {top['player']}")
print(f"Score : {top['score']}")
print(f"Link  : {top['url']}")

print("\nTOP LIST\n")

for i, r in enumerate(records[:TOP_N], 1):
    print(f"{i}. {r['player']} - {r['score']} Punkte")
    print(f"   {r['url']}")
