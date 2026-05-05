import requests
import json
from collections import defaultdict
from datetime import datetime

USERNAME = "german11"

# 🔧 FILTER
KEYWORD = ""     # z.B. "marathon", "bullet", "blitz" (None = kein Filter)
MIN_PLAYERS = 0          # z.B. 50
SINCE_YEAR = 0       # nur Turniere ab diesem Jahr

headers = {
    "Accept": "application/x-ndjson"
}

# 🔹 1. Turniere laden
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
    created = t.get("created")  # timestamp (ms)

    year = datetime.utcfromtimestamp(created / 1000).year if created else 0

    # 🔥 FILTER LOGIK
    if KEYWORD and KEYWORD.lower() not in name:
        continue

    if nb_players < MIN_PLAYERS:
        continue

    if year < SINCE_YEAR:
        continue

    tournament_ids.append(t["id"])

print(f"{len(tournament_ids)} Turniere nach Filter\n")


# 🔹 2. Games sammeln
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

        white = game["players"]["white"]["user"]["name"]
        black = game["players"]["black"]["user"]["name"]

        games_count[white] += 1
        games_count[black] += 1


# 🔹 3. Ranking
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

print("\n⚡ KOMBINIERTE RANGLISTE:\n")

for i, (user, games) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {games} Games")

    for tid in tournament_ids:
        print(f"   https://lichess.org/tournament/{tid}?player={user}")

    print()
