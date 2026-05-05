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

ONLY_TEAM_MEMBERS = True
MAX_TOURNEYS = 100
MIN_GAMES = 1

headers = {
    "Accept": "application/x-ndjson",
    "User-Agent": "multi-mvp-engine"
}

# =========================
# 📊 DATA STORAGE
# =========================

games = defaultdict(lambda: defaultdict(int))
wins = defaultdict(lambda: defaultdict(int))
participation = defaultdict(lambda: defaultdict(set))

# =========================
# 🔎 LOOP THROUGH ALL MODES
# =========================

for mode, team_id in TEAMS.items():

    print("\n" + "=" * 60)
    print(f"⚡ MODE: {mode.upper()}")
    print("=" * 60)

    url = f"https://lichess.org/api/team/{team_id}/arena?status=finished"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
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

            white_team = white.get("team")
            black_team = black.get("team")

            winner = game.get("winner")

            # WHITE
            if white_user:
                u = white_user.lower()
                games[u][mode] += 1
                participation[u][mode].add(t["id"])

                if winner == "white":
                    wins[u][mode] += 1

            # BLACK
            if black_user:
                u = black_user.lower()
                games[u][mode] += 1
                participation[u][mode].add(t["id"])

                if winner == "black":
                    wins[u][mode] += 1

# =========================
# 🧠 CALCULATIONS
# =========================

def winrate(user, mode):
    g = games[user][mode]
    return wins[user][mode] / g if g > 0 else 0

def total_games(user):
    return sum(games[user].values())

def total_winrate(user):
    g = total_games(user)
    if g == 0:
        return 0
    w = sum(wins[user].values())
    return w / g

def mode_strength(user):
    scores = []
    for m in TEAMS.keys():
        if games[user][m] > 0:
            scores.append(winrate(user, m))
    return sum(scores) / len(scores) if scores else 0

def mvp(user):
    return (
        total_winrate(user) * 0.5 +
        min(total_games(user) / 100, 1) * 0.2 +
        mode_strength(user) * 0.3
    ) * 100

# =========================
# 🏆 RANKING
# =========================

players = [
    u for u in games
    if total_games(u) >= MIN_GAMES
]

ranked = sorted(players, key=mvp, reverse=True)

# =========================
# 📊 OUTPUT
# =========================

print("\n" + "=" * 60)
print("🏆 GLOBAL MULTI-LIGA MVP")
print("=" * 60 + "\n")

for i, u in enumerate(ranked, 1):

    tg = total_games(u)
    tw = total_winrate(u) * 100

    print(f"{i}. {u}")
    print(f"   🏆 MVP: {mvp(u):.1f}")
    print(f"   📊 WR: {tw:.1f}% | Games: {tg}")

    for m in TEAMS.keys():
        if games[u][m] > 0:
            wr = winrate(u, m) * 100
            print(f"   ⚡ {m}: {wr:.1f}% ({games[u][m]} games)")

    print("")
