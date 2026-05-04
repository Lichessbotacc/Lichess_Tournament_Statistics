import requests
import json
from collections import defaultdict

TEAM_ID = "darkonblitz-dob"
MAX_TOURNEYS = 30

headers = {
    "Accept": "application/x-ndjson"
}

# 🔎 1. Turniere holen
url = f"https://lichess.org/api/team/{TEAM_ID}/arena?status=finished"

response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Fehler beim Laden der Turniere")
    exit()

tournaments = []

for line in response.text.splitlines():
    if not line.strip():
        continue
    tournaments.append(json.loads(line))

if not tournaments:
    print("Keine Turniere gefunden")
    exit()

selected_tourneys = tournaments[:MAX_TOURNEYS]

print(f"Analysiere die letzten {len(selected_tourneys)} Turniere:\n")

games_count = defaultdict(int)

# 🔎 2. Games aus allen Turnieren
for t in selected_tourneys:
    tourney_id = t["id"]
    print(f"- {t['fullName']}")

    games_url = f"https://lichess.org/api/tournament/{tourney_id}/games"
    response = requests.get(games_url, headers=headers, stream=True)

    if response.status_code != 200:
        print(f"Fehler bei Turnier {tourney_id}")
        continue

    for line in response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        white = game["players"]["white"]
        black = game["players"]["black"]

        white_user = white.get("user", {}).get("name")
        black_user = black.get("user", {}).get("name")

        white_team = white.get("team")
        black_team = black.get("team")

        # 🔥 WICHTIG: nur zählen wenn wirklich für dein Team gespielt wurde
        if white_team == TEAM_ID and white_user:
            games_count[white_user] += 1

        if black_team == TEAM_ID and black_user:
            games_count[black_user] += 1

# 🔎 3. Sortieren
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

# 🏆 4. Ausgabe
print("\n🏆 Team-Rangliste (echte Teamspiele):\n")

for i, (user, games) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {games} Spiele")
