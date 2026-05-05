import requests
import json
from collections import defaultdict
from datetime import datetime

USERNAME = "darkoncrack"

# 🔧 OPTIONAL FILTER
KEYWORD = "lmao"
MIN_PLAYERS = 0
SINCE_YEAR = 0
MIN_GAMES = 1   # 🔥 z.B. 20 für echte Rangliste

headers = {
    "Accept": "application/x-ndjson"
}

# 🔹 Turniere laden
tournament_ids = []

url = f"https://lichess.org/api/user/{USERNAME}/tournament/created"
response = requests.get(url, headers=headers, stream=True)

for line in response.iter_lines():
    if not line:
        continue

    t = json.loads(line)

    name = t.get("fullName", "").lower()
    nb_players = t.get("nbPlayers", 0)
    created = t.get("created")

    year = datetime.utcfromtimestamp(created / 1000).year if created else 0

    if KEYWORD and KEYWORD.lower() not in name:
        continue
    if MIN_PLAYERS and nb_players < MIN_PLAYERS:
        continue
    if SINCE_YEAR and year < SINCE_YEAR:
        continue

    tournament_ids.append(t["id"])


# 🔹 Games zählen
games_count = defaultdict(int)

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


# 🔹 filtern + sortieren
filtered = [(u, g) for u, g in games_count.items() if g >= MIN_GAMES]
sorted_players = sorted(filtered, key=lambda x: x[1], reverse=True)


# 🔥 FINAL OUTPUT
print("\n⚡ BEST PERFORMANCE (Most Games Played)\n")

for i, (user, games) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {games}")
