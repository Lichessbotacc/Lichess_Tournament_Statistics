import requests
import json
from collections import defaultdict

TEAM_ID = "solo-bullet-league"
MAX_TOURNEYS = 1
TOURNEY_KEYWORD = "solo"

headers = {
    "Accept": "application/x-ndjson"
}

# 🔎 1. Turniere holen
url = f"https://lichess.org/api/team/{TEAM_ID}/arena?status=finished"
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Fehler beim Laden der Turniere")
    exit()

tournaments = [json.loads(line) for line in response.text.splitlines() if line.strip()]

# 🔥 Filter
filtered = [
    t for t in tournaments
    if TOURNEY_KEYWORD == "" or TOURNEY_KEYWORD.lower() in t["fullName"].lower()
]

selected_tourneys = filtered[:MAX_TOURNEYS]

print(f"\n🏆 POINTS RANKING – Team: {TEAM_ID}")
print(f"Turniere: {len(selected_tourneys)} | Filter: {TOURNEY_KEYWORD if TOURNEY_KEYWORD else 'ALL'}\n")

points = defaultdict(float)

# 🔎 2. Games durchgehen (MIT TEAM CHECK)
for t in selected_tourneys:
    tourney_id = t["id"]
    print(f"- {t['fullName']} https://lichess.org/tournament/{tourney_id}")

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

        winner = game.get("winner")  # "white", "black", oder None

        # 🟢 WHITE
        if white_user and (white_team == TEAM_ID or white_team is None):
            if winner == "white":
                points[white_user] += 2
            elif winner is None:
                points[white_user] += 1

        # 🔵 BLACK
        if black_user and (black_team == TEAM_ID or black_team is None):
            if winner == "black":
                points[black_user] += 2
            elif winner is None:
                points[black_user] += 1

# 🔎 3. Sortieren
sorted_players = sorted(points.items(), key=lambda x: x[1], reverse=True)

# 🏆 4. Ausgabe
print("\n🏆 POINTS RANKING:\n")

for i, (user, score) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {score} points")
