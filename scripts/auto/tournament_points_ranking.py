import requests
import json
from collections import defaultdict

TEAM_ID = "official-ultrabullet-teambattles"

# 🎛️ SETTINGS
ONLY_TEAM_MEMBERS = False     # True = nur Team, False = alle Spieler
TOURNEY_KEYWORD = ""       # "" = alle Turniere
MAX_TOURNEYS = 10

DEBUG = False

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

# 🔥 FILTER (Keyword)
filtered = []
for t in tournaments:
    if TOURNEY_KEYWORD == "" or TOURNEY_KEYWORD.lower() in t["fullName"].lower():
        filtered.append(t)

selected_tourneys = filtered[:MAX_TOURNEYS]

print(f"\n🏆 TEAM: {TEAM_ID}")
print(f"MODE: {'TEAM ONLY' if ONLY_TEAM_MEMBERS else 'ALL PLAYERS'}")
print(f"KEYWORD: {TOURNEY_KEYWORD if TOURNEY_KEYWORD else 'ALL'}")
print(f"TURNIERE: {len(selected_tourneys)}\n")

points = defaultdict(int)

# 🔥 für Team-Historie
player_team_counts = defaultdict(lambda: defaultdict(int))

# 🔎 2. Turniere durchgehen
for t in selected_tourneys:
    print(f"▶ {t['fullName']}")

    team_players = set()

    # 🟢 GAMES
    games_url = f"https://lichess.org/api/tournament/{t['id']}/games"
    g_response = requests.get(games_url, headers=headers, stream=True)

    if g_response.status_code != 200:
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

        # 🧠 Team history tracking
        if white_user:
            team_name = white_team if white_team else "unknown"
            player_team_counts[white_user.lower()][team_name] += 1

        if black_user:
            team_name = black_team if black_team else "unknown"
            player_team_counts[black_user.lower()][team_name] += 1

        # 🟢 Team detection
        if white_user and white_team == TEAM_ID:
            team_players.add(white_user.lower())

        if black_user and black_team == TEAM_ID:
            team_players.add(black_user.lower())

    fallback_all = len(team_players) == 0

    if DEBUG:
        print(f"Team-Spieler erkannt: {len(team_players)}")
        if fallback_all:
            print("⚠️ Fallback aktiv (kein Team-Feld gefunden)")

    # 🔵 RESULTS
    results_url = f"https://lichess.org/api/tournament/{t['id']}/results"
    r_response = requests.get(results_url, headers=headers)

    if r_response.status_code != 200:
        continue

    for line in r_response.text.splitlines():
        if not line.strip():
            continue

        data = json.loads(line)

        username = data.get("username")
        score = int(data.get("score", 0))

        if not username:
            continue

        user = username.lower()

        # 🔥 FILTER LOGIC
        if ONLY_TEAM_MEMBERS:
            if fallback_all or user in team_players:
                points[user] += score
        else:
            points[user] += score


# 🧠 Hauptteam bestimmen
def get_main_team(user):
    teams = player_team_counts[user]
    if not teams:
        return "unknown"
    return max(teams.items(), key=lambda x: x[1])[0]


# 🔎 3. Sortieren
sorted_players = sorted(points.items(), key=lambda x: x[1], reverse=True)

# 🏆 4. OUTPUT
print("\n🏆 FINAL RANKING:\n")

for i, (user, score) in enumerate(sorted_players, 1):

    if ONLY_TEAM_MEMBERS:
        print(f"{i}. {user}: {score} points")
    else:
        team = get_main_team(user)
        print(f"{i}. {user}: {score} points ({team})")
