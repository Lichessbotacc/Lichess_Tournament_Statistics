import requests
import json
from collections import defaultdict

TEAM_ID = "solo-blitz-league"
MAX_TOURNEYS = 36
TOURNEY_KEYWORD = ""

MIN_GAMES = 20
ONLY_TEAM_MEMBERS = False

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

print("\n" + "=" * 60)
print(f"🏆 BEST PERFORMANCE DASHBOARD – {TEAM_ID}")
print("=" * 60)

print(f"\n📊 Turniere: {len(selected_tourneys)} | Filter: {TOURNEY_KEYWORD or 'ALL'}\n")

# =========================
# 📊 DATA
# =========================

games = defaultdict(int)
wins = defaultdict(int)

# =========================
# 🔎 2. TURNIERE + LINKS
# =========================

for t in selected_tourneys:
    print(f"🏁 {t['fullName']}")
    print(f"🔗 https://lichess.org/tournament/{t['id']}\n")

    games_url = f"https://lichess.org/api/tournament/{t['id']}/games"
    r = requests.get(games_url, headers=headers, stream=True)

    if r.status_code != 200:
        continue

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
            if winner == "white":
                wins[u] += 1

        # BLACK
        if black_user and (not ONLY_TEAM_MEMBERS or black_team == TEAM_ID):
            u = black_user.lower()
            games[u] += 1
            if winner == "black":
                wins[u] += 1

# =========================
# ⚡ BEST PERFORMANCE
# =========================

def winrate(u):
    g = games[u]
    return (wins[u] / g * 100) if g > 0 else 0

performance = [
    (u, winrate(u), games[u])
    for u in games
    if games[u] >= MIN_GAMES
]

performance.sort(key=lambda x: x[1], reverse=True)

# =========================
# 🏆 OUTPUT
# =========================

print("\n⚡ BEST PERFORMANCE (min 20 games)\n")

for i, (user, wr, g) in enumerate(performance, 1):
    print(f"{i}. {user}: {wr:.1f}% WR | {g} games")
