import requests
import json
from collections import defaultdict

TEAM_ID = "darkonteams"
MAX_TOURNEYS = 1000
TOURNEY_KEYWORD = "Hourly Ultrabullet"

ONLY_TEAM_MEMBERS = False   # True = nur Teamspieler, False = alle

headers = {
    "Accept": "application/x-ndjson"
}

# 🔎 1. Turniere holen
url = f"https://lichess.org/api/team/{TEAM_ID}/arena?status=finished"
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Fehler beim Laden der Turniere")
    exit()

tournaments = [
    json.loads(line)
    for line in response.text.splitlines()
    if line.strip()
]

# 🔥 Filter
filtered = [
    t for t in tournaments
    if TOURNEY_KEYWORD == "" or TOURNEY_KEYWORD.lower() in t["fullName"].lower()
]

selected_tourneys = filtered[:MAX_TOURNEYS]

print(f"\n🏆 GAMES RANKING – Team: {TEAM_ID}")
print(f"Turniere: {len(selected_tourneys)} | Filter: {TOURNEY_KEYWORD if TOURNEY_KEYWORD else 'ALL'}\n")

# 📊 DATA
games_count = defaultdict(int)
tournament_participation = defaultdict(set)

# 🔎 2. Turniere durchgehen
for t in selected_tourneys:
    tourney_id = t["id"]

    print(f"- {t['fullName']} https://lichess.org/tournament/{tourney_id}")

    team_players_in_tourney = set()

    # 🟢 GAMES holen
    games_url = f"https://lichess.org/api/tournament/{tourney_id}/games"
    g_response = requests.get(games_url, headers=headers, stream=True)

    if g_response.status_code != 200:
        print(f"Fehler bei Games {tourney_id}")
        continue

    for line in g_response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        white = game["players"]["white"]
        black = game["players"]["black"]

        white_user = white.get("user", {}).get("name")
        black_user = black.get("user", {}).get("name")

        white_team = white.get("team")
        black_team = black.get("team")

        # 🟢 Team-Filter (optional)
        if white_user and (not ONLY_TEAM_MEMBERS or white_team == TEAM_ID):
            games_count[white_user.lower()] += 1
            tournament_participation[white_user.lower()].add(tourney_id)

        if black_user and (not ONLY_TEAM_MEMBERS or black_team == TEAM_ID):
            games_count[black_user.lower()] += 1
            tournament_participation[black_user.lower()].add(tourney_id)

# 🔎 3. Sortieren
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

# 🏆 4. OUTPUT
print("\n🏆 GAMES RANKING:\n")

total_tournaments = len(selected_tourneys)

for i, (user, games) in enumerate(sorted_players, 1):
    played_tournaments = len(tournament_participation[user])

    print(f"{i}. {user}: {games} games ({played_tournaments}/{total_tournaments} tournaments)")
