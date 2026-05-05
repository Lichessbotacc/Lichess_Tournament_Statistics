import requests
import json
from collections import defaultdict
from datetime import datetime

# ======================
# 🔧 INPUT
# ======================
INPUT_NAME = "darkonteams"
INPUT_TYPE = "team"   # "user" oder "team"

KEYWORD = "Hourly Ultrabullet"
MIN_PLAYERS = 0
SINCE_YEAR = 0
MIN_GAMES = 1

headers = {
    "Accept": "application/x-ndjson"
}

# ======================
# 🔹 TURNIERE LADEN
# ======================
tournament_ids = []

def add_if_valid(t):
    name = t.get("fullName", "").lower()
    nb_players = t.get("nbPlayers", 0)
    created = t.get("created")

    year = datetime.utcfromtimestamp(created / 1000).year if created else 0

    if KEYWORD and KEYWORD.lower() not in name:
        return
    if MIN_PLAYERS and nb_players < MIN_PLAYERS:
        return
    if SINCE_YEAR and year < SINCE_YEAR:
        return

    tournament_ids.append(t["id"])


# ======================
# USER MODE
# ======================
if INPUT_TYPE == "user":
    url = f"https://lichess.org/api/user/{INPUT_NAME}/tournament/created"
    response = requests.get(url, headers=headers, stream=True)

    for line in response.iter_lines():
        if not line:
            continue
        t = json.loads(line)
        add_if_valid(t)


# ======================
# TEAM MODE (robust + fallback)
# ======================
else:
    # 1) Versuch: Team-API (nicht immer vollständig)
    url = f"https://lichess.org/api/team/{INPUT_NAME}/arena"
    response = requests.get(url, headers=headers, stream=True)

    found_any = False

    for line in response.iter_lines():
        if not line:
            continue
        found_any = True
        t = json.loads(line)
        add_if_valid(t)

    # 2) FALLBACK: globale Suche (wichtig!)
    if not found_any or len(tournament_ids) == 0:
        print("⚠️ Team API leer → fallback search...")

        url = "https://lichess.org/api/tournament"
        response = requests.get(url, headers=headers, stream=True)

        for line in response.iter_lines():
            if not line:
                continue
            t = json.loads(line)

            # Team-Name im Tournament Creator oder Description suchen
            if INPUT_NAME.lower() in json.dumps(t).lower():
                add_if_valid(t)


# ======================
# 🔹 GAMES ZÄHLEN
# ======================
games_count = defaultdict(int)

print(f"DEBUG tournaments found: {len(tournament_ids)}")

for tid in tournament_ids:
    url = f"https://lichess.org/api/tournament/{tid}/games"
    response = requests.get(url, headers=headers, stream=True)

    if response.status_code != 200:
        continue

    for line in response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        try:
            white = game["players"]["white"]["user"]["name"]
            black = game["players"]["black"]["user"]["name"]
        except:
            continue

        games_count[white] += 1
        games_count[black] += 1


# ======================
# 🔹 OUTPUT
# ======================
filtered = [(u, g) for u, g in games_count.items() if g >= MIN_GAMES]
sorted_players = sorted(filtered, key=lambda x: x[1], reverse=True)

print("\n⚡ BEST PERFORMANCE (Most Games Played)\n")

if not sorted_players:
    print("Keine Daten gefunden – überprüfe KEYWORD oder INPUT_TYPE.")
else:
    for i, (user, games) in enumerate(sorted_players, 1):
        print(f"{i}. {user}: {games}")
