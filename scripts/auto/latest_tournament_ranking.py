import requests
import json
from collections import defaultdict

TEAM_ID = "darkonteams"  # dein Team

headers = {
    "Accept": "application/x-ndjson"
}

# 🔎 1. Neuestes beendetes Turnier holen
url = f"https://lichess.org/api/team/{TEAM_ID}/arena?status=finished"

response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Fehler beim Laden der Turniere")
    exit()

tournaments = []

for line in response.text.splitlines():
    if not line.strip():
        continue
    data = json.loads(line)
    tournaments.append(data)

if not tournaments:
    print("Keine Turniere gefunden")
    exit()

# 👉 NEUESTES Turnier
tourney = tournaments[0]
TOURNEY_ID = tourney["id"]

print(f"Analysiere Turnier: {tourney['fullName']}")
print(f"https://lichess.org/tournament/{TOURNEY_ID}\n")

# 🔎 2. Spiele zählen
games_url = f"https://lichess.org/api/tournament/{TOURNEY_ID}/games"

response = requests.get(games_url, headers=headers, stream=True)

if response.status_code != 200:
    print("Fehler beim Laden der Spiele")
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

# 🔎 3. Sortieren
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

# 🏆 Ausgabe
print("Rangliste nach gespielten Partien:\n")

for i, (user, games) in enumerate(sorted_players, 1):
    link = f"https://lichess.org/tournament/{TOURNEY_ID}?player={user}"
    print(f"{i}. {user}: {games} Spiele → {link}")
