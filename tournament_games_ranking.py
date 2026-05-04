import requests
import json
from collections import defaultdict

TOURNEY_ID = "winter23"  # deine Turnier-ID

url = f"https://lichess.org/api/tournament/{TOURNEY_ID}/games"

headers = {
    "Accept": "application/x-ndjson"
}

response = requests.get(url, headers=headers, stream=True)

if response.status_code != 200:
    print("Fehler:", response.status_code)
    exit()

games_count = defaultdict(int)

for line in response.iter_lines():
    if not line:
        continue

    game = json.loads(line)

    white = game["players"]["white"]["user"]["name"]
    black = game["players"]["black"]["user"]["name"]

    games_count[white] += 1
    games_count[black] += 1

# sortieren
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

print("Rangliste nach gespielten Partien:\n")

for i, (user, games) in enumerate(sorted_players, 1):
    link = f"https://lichess.org/tournament/{TOURNEY_ID}?player={user}"
    print(f"{i}. {user}: {games} Games played")
    print(f"   {link}")
