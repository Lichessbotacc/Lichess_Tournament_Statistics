import requests
import json
from collections import defaultdict

TEAM_ID = "darkonteams"
MAX_TOURNEYS = 10
FILTER_TEAM_ONLY = True  # 🔥 hier an/aus

headers = {
    "Accept": "application/x-ndjson"
}

# 🔎 1. Team-Mitglieder holen
team_members = set()

if FILTER_TEAM_ONLY:
    url = f"https://lichess.org/api/team/{TEAM_ID}/users"
    response = requests.get(url, headers=headers)

    for line in response.text.splitlines():
        if not line.strip():
            continue
        user = json.loads(line)
        team_members.add(user["name"])

    print(f"Team-Mitglieder geladen: {len(team_members)}")

# 🔎 2. Turniere holen
url = f"https://lichess.org/api/team/{TEAM_ID}/arena?status=finished"
response = requests.get(url, headers=headers)

tournaments = []
for line in response.text.splitlines():
    if not line.strip():
        continue
    tournaments.append(json.loads(line))

selected_tourneys = tournaments[:MAX_TOURNEYS]

print(f"\nAnalysiere {len(selected_tourneys)} Turniere:\n")

games_count = defaultdict(int)

# 🔎 3. Spiele zählen
for t in selected_tourneys:
    tourney_id = t["id"]
    print(f"- {t['fullName']}")

    games_url = f"https://lichess.org/api/tournament/{tourney_id}/games"
    response = requests.get(games_url, headers=headers, stream=True)

    for line in response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        white = game["players"]["white"]["user"]["name"]
        black = game["players"]["black"]["user"]["name"]

        # 🔥 Filter anwenden
        if not FILTER_TEAM_ONLY or white in team_members:
            games_count[white] += 1

        if not FILTER_TEAM_ONLY or black in team_members:
            games_count[black] += 1

# 🔎 4. Sortieren
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

# 🏆 Ausgabe
print("\n🏆 Team-Rangliste:\n")

for i, (user, games) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {games} Spiele")
