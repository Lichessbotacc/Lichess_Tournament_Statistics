import requests
import json
from collections import defaultdict

# =========================
# ⚙️ CONFIG
# =========================

TEAM_ID = "lmao-teamfights"

ONLY_TEAM_MEMBERS = True     # True = nur Team, False = alle Spieler
TOURNEY_KEYWORD = ""          # z.B. "8+0" oder "" für alle
MAX_TOURNEYS = 1

DEBUG = False

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# 🔎 1. TURNIERE LADEN
# =========================

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

# 🔥 FILTER
selected_tourneys = []
for t in tournaments:
    if TOURNEY_KEYWORD == "" or TOURNEY_KEYWORD.lower() in t["fullName"].lower():
        selected_tourneys.append(t)

selected_tourneys = selected_tourneys[:MAX_TOURNEYS]

print(f"\n🏆 TEAM: {TEAM_ID}")
print(f"MODE: {'TEAM ONLY' if ONLY_TEAM_MEMBERS else 'ALL PLAYERS'}")
print(f"KEYWORD: {TOURNEY_KEYWORD if TOURNEY_KEYWORD else 'ALL'}")
print(f"TURNIERE: {len(selected_tourneys)}\n")

# =========================
# 📊 DATA
# =========================

points = defaultdict(int)
player_team_counts = defaultdict(lambda: defaultdict(int))

# =========================
# 🔎 2. TURNIERE DURCHGEHEN
# =========================

for t in selected_tourneys:

    print("\n" + "=" * 55)
    print(f"🏆 {t['fullName']}")
    print(f"🔗 https://lichess.org/tournament/{t['id']}")
    print("=" * 55)

    team_players = set()

    # =========================
    # 🟢 GAMES
    # =========================

    games_url = f"https://lichess.org/api/tournament/{t['id']}/games"
    g_response = requests.get(games_url, headers=headers, stream=True)

    if g_response.status_code != 200:
        print("Fehler bei Games")
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

        # 🧠 Team-Historie speichern
        if white_user:
            team_name = white_team if white_team else "unknown"
            player_team_counts[white_user.lower()][team_name] += 1

        if black_user:
            team_name = black_team if black_team else "unknown"
            player_team_counts[black_user.lower()][team_name] += 1

        # 🟢 Team-Erkennung
        if white_user and white_team == TEAM_ID:
            team_players.add(white_user.lower())

        if black_user and black_team == TEAM_ID:
            team_players.add(black_user.lower())

    fallback_all = len(team_players) == 0

    if DEBUG:
        print(f"Team-Spieler erkannt: {len(team_players)}")
        if fallback_all:
            print("⚠️ Fallback aktiv (kein Team-Feld gefunden)")

    # =========================
    # 🔵 RESULTS
    # =========================

    results_url = f"https://lichess.org/api/tournament/{t['id']}/results"
    r_response = requests.get(results_url, headers=headers)

    if r_response.status_code != 200:
        print("Fehler bei Results")
        continue

    matched = 0
    ignored = 0
    total_points = 0

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
                matched += 1
                total_points += score
            else:
                ignored += 1
        else:
            points[user] += score
            matched += 1
            total_points += score

    if DEBUG:
        print(f"Matched: {matched} | Ignored: {ignored} | Points: {total_points}")

# =========================
# 🧠 MAIN TEAM (optional)
# =========================

def get_main_team(user):
    teams = player_team_counts[user]
    if not teams:
        return "unknown"
    return max(teams.items(), key=lambda x: x[1])[0]

# =========================
# 🏆 FINAL RANKING
# =========================

sorted_players = sorted(points.items(), key=lambda x: x[1], reverse=True)

print("\n" + "=" * 60)
print("🏆 FINAL RANKING")
print("=" * 60 + "\n")

for i, (user, score) in enumerate(sorted_players, 1):

    if ONLY_TEAM_MEMBERS:
        print(f"{i}. {user}: {score} points")
    else:
        team = get_main_team(user)
        print(f"{i}. {user}: {score} points ({team})")
