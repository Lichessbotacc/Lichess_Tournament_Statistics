import requests
import json
from collections import defaultdict

TEAM_ID = "darkonteams"
MAX_TOURNEYS = 100
TOURNEY_KEYWORD = "hourly ultrabullet"

ONLY_TEAM_MEMBERS = False

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# 🔎 TOURNAMENTS
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

selected = [
    t for t in tournaments
    if TOURNEY_KEYWORD == "" or TOURNEY_KEYWORD.lower() in t["fullName"].lower()
][:MAX_TOURNEYS]

# =========================
# 📊 DATA
# =========================

games = defaultdict(int)
wins = defaultdict(int)
draws = defaultdict(int)
losses = defaultdict(int)
tournament_participation = defaultdict(set)
player_team = defaultdict(lambda: defaultdict(int))

# =========================
# 🔎 PROCESS
# =========================

for t in selected:

    games_url = f"https://lichess.org/api/tournament/{t['id']}/games"
    r = requests.get(games_url, headers=headers, stream=True)

    for line in r.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        white = game["players"]["white"]
        black = game["players"]["black"]

        white_user = white.get("user", {}).get("name")
        black_user = black.get("user", {}).get("name")

        white_team = white.get("team")
        black_team = black.get("team")

        winner = game.get("winner")

        # WHITE
        if white_user and (not ONLY_TEAM_MEMBERS or white_team == TEAM_ID):
            u = white_user.lower()

            games[u] += 1
            tournament_participation[u].add(t["id"])
            player_team[u][white_team or "unknown"] += 1

            if winner == "white":
                wins[u] += 1
            elif winner == "black":
                losses[u] += 1
            else:
                draws[u] += 1

        # BLACK
        if black_user and (not ONLY_TEAM_MEMBERS or black_team == TEAM_ID):
            u = black_user.lower()

            games[u] += 1
            tournament_participation[u].add(t["id"])
            player_team[u][black_team or "unknown"] += 1

            if winner == "black":
                wins[u] += 1
            elif winner == "white":
                losses[u] += 1
            else:
                draws[u] += 1

# =========================
# 🧠 MAIN TEAM
# =========================

def main_team(user):
    if not player_team[user]:
        return "unknown"
    return max(player_team[user].items(), key=lambda x: x[1])[0]

# =========================
# 📊 SORT
# =========================

sorted_players = sorted(games.items(), key=lambda x: x[1], reverse=True)

# =========================
# 🏆 TERMINAL DASHBOARD
# =========================

print("\n" + "=" * 70)
print(f"🏆 CHESS LEAGUE DASHBOARD – {TEAM_ID}")
print("=" * 70)

print(f"\n📊 Turniere: {len(selected)} | Keyword: {TOURNEY_KEYWORD or 'ALL'}")
print(f"🎛️ Mode: {'TEAM ONLY' if ONLY_TEAM_MEMBERS else 'ALL PLAYERS'}\n")

print("-" * 70)
print(f"{'#':<3} {'PLAYER':<20} {'GAMES':<6} {'W/D/L':<12} {'WR%':<6} {'T':<6} {'TEAM'}")
print("-" * 70)

for i, (user, g) in enumerate(sorted_players, 1):

    w = wins[user]
    d = draws[user]
    l = losses[user]

    wr = (w / g * 100) if g > 0 else 0
    tplayed = len(tournament_participation[user])

    team = main_team(user)

    print(
        f"{i:<3} {user:<20} {g:<6} "
        f"{w}/{d}/{l:<8} {wr:5.1f} {tplayed}/{len(selected):<3} {team}"
    )

print("-" * 70)
print("🏁 End of Dashboard\n")
