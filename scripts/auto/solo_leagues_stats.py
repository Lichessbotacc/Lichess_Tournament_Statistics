import requests
import json
from collections import defaultdict

# =========================
# ⚙️ CONFIG
# =========================

TEAMS = {
    "ultrabullet": "solo-ultrabullet-league",
    "bullet": "solo-bullet-league",
    "blitz": "solo-blitz-league",
    "rapid": "solo-rapid-league"
}

START_RATING = 1200
MIN_GAMES = 5
MAX_TOURNEYS = 30

headers = {
    "Accept": "application/x-ndjson",
    "User-Agent": "multi-elo-engine"
}

# =========================
# 📊 DATA STORAGE
# =========================

games = defaultdict(lambda: defaultdict(int))
wins = defaultdict(lambda: defaultdict(int))

# =========================
# 🔎 LOAD DATA
# =========================

for mode, team_id in TEAMS.items():

    print(f"\n⚡ Loading {mode.upper()} ({team_id})")

    url = f"https://lichess.org/api/team/{team_id}/arena?status=finished"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print(f"❌ Error loading {mode}")
        continue

    tournaments = []
    for line in r.text.splitlines():
        if line.strip():
            try:
                tournaments.append(json.loads(line))
            except:
                continue

    tournaments = tournaments[:MAX_TOURNEYS]

    for t in tournaments:

        games_url = f"https://lichess.org/api/tournament/{t['id']}/games"
        gr = requests.get(games_url, headers=headers)

        if gr.status_code != 200:
            continue

        for line in gr.iter_lines(decode_unicode=True):
            if not line:
                continue

            try:
                game = json.loads(line)
            except:
                continue

            white = game.get("players", {}).get("white", {})
            black = game.get("players", {}).get("black", {})

            white_user = white.get("user", {}).get("name")
            black_user = black.get("user", {}).get("name")

            winner = game.get("winner")

            # WHITE
            if white_user:
                u = white_user.lower()
                games[u][mode] += 1
                if winner == "white":
                    wins[u][mode] += 1

            # BLACK
            if black_user:
                u = black_user.lower()
                games[u][mode] += 1
                if winner == "black":
                    wins[u][mode] += 1

# =========================
# 🧠 ELO FUNCTIONS
# =========================

def winrate(user, mode):
    g = games[user][mode]
    return wins[user][mode] / g if g > 0 else 0

def mode_elo(user, mode):
    g = games[user][mode]
    if g < MIN_GAMES:
        return None

    wr = winrate(user, mode)
    return START_RATING + (wr - 0.5) * 800

def global_elo(user):
    elos = []
    total_weight = 0.0

    for mode in TEAMS.keys():
        e = mode_elo(user, mode)
        if e is not None:
            elos.append(e * 0.25)   # 👈 ALL MODES EQUAL WEIGHT
            total_weight += 0.25

    if total_weight == 0:
        return None

    return sum(elos) / total_weight

# =========================
# 🏆 PLAYER LIST
# =========================

players = [
    u for u in games
    if global_elo(u) is not None
]

ranked = sorted(players, key=global_elo, reverse=True)

# =========================
# 📊 OUTPUT
# =========================

print("\n" + "=" * 70)
print("🏆 SOLO LEAGUES – GLOBAL ELO RANKING")
print("=" * 70 + "\n")

for i, u in enumerate(ranked[:25], 1):

    g_total = sum(games[u].values())

    print(f"{i}. {u}")
    print(f"   🌍 Global ELO: {global_elo(u):.1f}")
    print(f"   🎮 Total Games: {g_total}")

    for mode in TEAMS.keys():
        e = mode_elo(u, mode)
        if e is not None:
            print(f"   ⚡ {mode}: {e:.1f} ({games[u][mode]} games)")

    print("")
