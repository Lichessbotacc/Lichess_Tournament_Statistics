import requests
import json
from collections import defaultdict

TEAM_ID = "solo-blitz-league"
MAX_TOURNEYS = 35

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

print(f"\n🏆 Team-Ranking für Team: {TEAM_ID}")
print(f"Analysierte Turniere: {len(selected_tourneys)}\n")

# 🔥 Tracking
games_count = defaultdict(int)
tournament_participation = defaultdict(set)

# 🔎 2. Games aus Turnieren
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

        # 🔥 nur echte Teamspiele zählen
        if white_team == TEAM_ID and white_user:
            games_count[white_user] += 1
            tournament_participation[white_user].add(tourney_id)

        if black_team == TEAM_ID and black_user:
            games_count[black_user] += 1
            tournament_participation[black_user].add(tourney_id)

# 🔎 3. Sortieren
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

# 🏆 4. Ausgabe
print(f"\n🏆 Rangliste – {TEAM_ID}\n")

for i, (user, games) in enumerate(sorted_players, 1):
    tournaments_played = len(tournament_participation[user])
    print(f"{i}. {user}: {games} games played and ({tournaments_played}/{len(selected_tourneys)} tournaments played!)")
