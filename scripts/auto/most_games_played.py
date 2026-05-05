import requests
import json
from collections import defaultdict

TEAM_ID = "solo-blitz-league"
MAX_TOURNEYS = 35
TOURNEY_KEYWORD = ""

ONLY_TEAM_MEMBERS = False   # True = nur Teamspieler

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

filtered = [
    t for t in tournaments
    if TOURNEY_KEYWORD == "" or TOURNEY_KEYWORD.lower() in t["fullName"].lower()
]

selected_tourneys = filtered[:MAX_TOURNEYS]

print(f"\n🏆 WINRATE STATS – Team: {TEAM_ID}")
print(f"Turniere: {len(selected_tourneys)} | Filter: {TOURNEY_KEYWORD if TOURNEY_KEYWORD else 'ALL'}\n")

# =========================
# 📊 DATA
# =========================

games = defaultdict(int)
wins = defaultdict(int)
draws = defaultdict(int)
losses = defaultdict(int)
tournaments_played = defaultdict(set)

# =========================
# 🔎 2. TURNIERE DURCHGEHEN
# =========================

for t in selected_tourneys:
    tourney_id = t["id"]

    print(f"- {t['fullName']} https://lichess.org/tournament/{tourney_id}")

    games_url = f"https://lichess.org/api/tournament/{tourney_id}/games"
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

        winner = game.get("winner")  # "white", "black", None

        # =========================
        # WHITE
        # =========================
        if white_user and (not ONLY_TEAM_MEMBERS or white_team == TEAM_ID):
            u = white_user.lower()

            games[u] += 1
            tournaments_played[u].add(tourney_id)

            if winner == "white":
                wins[u] += 1
            elif winner == "black":
                losses[u] += 1
            else:
                draws[u] += 1

        # =========================
        # BLACK
        # =========================
        if black_user and (not ONLY_TEAM_MEMBERS or black_team == TEAM_ID):
            u = black_user.lower()

            games[u] += 1
            tournaments_played[u].add(tourney_id)

            if winner == "black":
                wins[u] += 1
            elif winner == "white":
                losses[u] += 1
            else:
                draws[u] += 1

# =========================
# 🔎 3. SORT
# =========================

sorted_players = sorted(games.items(), key=lambda x: x[1], reverse=True)

# =========================
# 🏆 OUTPUT
# =========================

print("\n🏆 WINRATE RANKING:\n")

total_tournaments = len(selected_tourneys)

for i, (user, g) in enumerate(sorted_players, 1):

    w = wins[user]
    d = draws[user]
    l = losses[user]

    winrate = (w / g * 100) if g > 0 else 0
    played_t = len(tournaments_played[user])

    print(
        f"{i}. {user}: {g} games | "
        f"{w}W {d}D {l}L | "
        f"{winrate:.1f}% WR "
        f"({played_t}/{total_tournaments} tournaments)"
    )
