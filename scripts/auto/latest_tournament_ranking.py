import requests
import json
from collections import defaultdict

TEAM_ID = "darkonteams"
MAX_TOURNEYS = 1000
TOURNEY_KEYWORD = "Hourly Ultrabullet"

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

# 🔎 2. Turniere durchgehen
for t in selected_tourneys:
    tourney_id = t["id"]
    print(f"- {t['fullName']} https://lichess.org/tournament/{tourney_id}")

    # 🟢 STEP 1: Team-Spieler in diesem Turnier finden (über Games)
    team_players_in_tourney = set()

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

        if white_user and (white_team == TEAM_ID or white_team is None):
            team_players_in_tourney.add(white_user)

        if black_user and (black_team == TEAM_ID or black_team is None):
            team_players_in_tourney.add(black_user)

    # 🔵 STEP 2: echte Arena-Punkte holen
    results_url = f"https://lichess.org/api/tournament/{tourney_id}/results"
    r_response = requests.get(results_url, headers=headers)

    if r_response.status_code != 200:
        print(f"Fehler bei Results {tourney_id}")
        continue

    for line in r_response.text.splitlines():
        if not line.strip():
            continue

        data = json.loads(line)

        username = data.get("username")
        score = data.get("score", 0)

        # ✅ Nur zählen wenn Spieler fürs Team gespielt hat
        if username in team_players_in_tourney:
            points[username] += score

# 🔎 3. Sortieren
sorted_players = sorted(points.items(), key=lambda x: x[1], reverse=True)

# 🏆 4. Ausgabe
print("\n🏆 POINTS RANKING (ECHTE ARENA POINTS):\n")

for i, (user, score) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {score} points")
