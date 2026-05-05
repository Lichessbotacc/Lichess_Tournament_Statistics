import requests
import json
from collections import defaultdict
from datetime import datetime

USERNAME = "Nathanael01"

# 🔧 OPTIONAL FILTER
KEYWORD = None        # z.B. "marathon" oder None = ALLE
MIN_PLAYERS = 0
SINCE_YEAR = 0        # 0 = egal

headers = {
    "Accept": "application/x-ndjson"
}

print("Lade Turniere...")

tournament_ids = []

url = f"https://lichess.org/api/user/{USERNAME}/tournament/created"
response = requests.get(url, headers=headers, stream=True)

if response.status_code != 200:
    print("Fehler beim Laden:", response.status_code)
    exit()

for line in response.iter_lines():
    if not line:
        continue

    t = json.loads(line)

    name = t.get("fullName", "").lower()
    nb_players = t.get("nbPlayers", 0)
    created = t.get("created")

    # Jahr sicher berechnen
    if created:
        year = datetime.utcfromtimestamp(created / 1000).year
    else:
        year = 0

    # 🔥 FILTER (nur wenn gesetzt!)
    if KEYWORD and KEYWORD.lower() not in name:
        continue

    if MIN_PLAYERS and nb_players < MIN_PLAYERS:
        continue

    if SINCE_YEAR and year < SINCE_YEAR:
        continue

    tournament_ids.append(t["id"])

print(f"{len(tournament_ids)} Turniere gefunden\n")


# 🔹 Games sammeln
games_count = defaultdict(int)

for tid in tournament_ids:
    print(f"Lade {tid}...")

    url = f"https://lichess.org/api/tournament/{tid}/games"
    response = requests.get(url, headers=headers, stream=True)

    if response.status_code != 200:
        print(f"Fehler bei {tid}")
        continue

    for line in response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        try:
            white = game["players"]["white"]["user"]["name"]
            black = game["players"]["black"]["user"]["name"]
        except:
            continue  # z.B. anonymous games skippen

        games_count[white] += 1
        games_count[black] += 1


# 🔹 Ranking
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

print("\n⚡ KOMBINIERTE RANGLISTE (Most Games Played):\n")

for i, (user, games) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {games} Games")

    for tid in tournament_ids:
        print(f"   https://lichess.org/tournament/{tid}?player={user}")

    print()
