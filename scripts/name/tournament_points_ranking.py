import requests
import json
from collections import defaultdict

USERNAME = "DarkOnCrack"

# 🔧 OPTIONAL FILTER
KEYWORDS = ["Solo Rapid"]
MIN_PLAYERS = 0
SINCE_YEAR = 0
MIN_GAMES = 1

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# 🔎 1. TURNIERE LADEN
# =========================

url = f"https://lichess.org/api/user/{USERNAME}/tournament/created"
response = requests.get(url, headers=headers, stream=True)

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
    name = t["fullName"].lower()

    if KEYWORDS:
        if not any(k.lower() in name for k in KEYWORDS):
            continue

    selected_tourneys.append(t)

selected_tourneys = selected_tourneys[:500]

print(f"\n🏆 USER: {USERNAME}")
print(f"TURNIERE: {len(selected_tourneys)}\n")

# =========================
# 📊 DATA
# =========================

points = defaultdict(int)
player_tournament_participation = defaultdict(set)

# =========================
# 🔎 2. TURNIERE DURCHGEHEN
# =========================

for t in selected_tourneys:

    print("\n" + "=" * 55)
    print(f"🏆 {t['fullName']}")
    print(f"🔗 https://lichess.org/tournament/{t['id']}")
    print("=" * 55)

    games_url = f"https://lichess.org/api/tournament/{t['id']}/games"
    g_response = requests.get(games_url, headers=headers, stream=True)

    if g_response.status_code != 200:
        continue

    for line in g_response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        try:
            white = game["players"]["white"]["user"]["name"]
            black = game["players"]["black"]["user"]["name"]

            white_data = game["players"]["white"]
            black_data = game["players"]["black"]

            winner = game.get("winner")

        except:
            continue

        # Participation tracking
        if white:
            player_tournament_participation[white.lower()].add(t['id'])
        if black:
            player_tournament_participation[black.lower()].add(t['id'])

        # =========================
        # 🔥 ARENA SCORING LOGIK
        # =========================

        if winner == "white":
            points[white.lower()] += 2
            points[black.lower()] += 0

        elif winner == "black":
            points[black.lower()] += 2
            points[white.lower()] += 0

        else:
            points[white.lower()] += 1
            points[black.lower()] += 1

        # ⚡ BERSERK BONUS
        if white_data.get("berserk"):
            points[white.lower()] += 1

        if black_data.get("berserk"):
            points[black.lower()] += 1


# =========================
# 🏆 FINAL RANKING
# =========================

sorted_players = sorted(points.items(), key=lambda x: x[1], reverse=True)

print("\n" + "=" * 60)
print("🏆 FINAL RANKING (Arena Scoring)")
print("=" * 60 + "\n")

total_tournaments = len(selected_tourneys)

for i, (user, score) in enumerate(sorted_players, 1):

    played = len(player_tournament_participation[user])

    print(f"{i}. {user}: {score} points ({played}/{total_tournaments})")
