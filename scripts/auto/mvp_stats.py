import requests
import json
from collections import defaultdict

# =========================
# ⚙️ CONFIG
# =========================

TEAM_ID = "solo-blitz-league"
MAX_TOURNEYS = 35
TOURNEY_KEYWORD = ""

ONLY_TEAM_MEMBERS = True

MIN_GAMES_FOR_MVP = 10  # kleine Schwelle gegen Noise

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

selected_tourneys = [
    t for t in tournaments
    if TOURNEY_KEYWORD == "" or TOURNEY_KEYWORD.lower() in t["fullName"].lower()
][:MAX_TOURNEYS]

total_tournaments = len(selected_tourneys)

print("\n" + "=" * 70)
print(f"🏆 BALANCED MVP DASHBOARD – {TEAM_ID}")
print("=" * 70)

print(f"\n📊 Turniere: {total_tournaments} | Filter: {TOURNEY_KEYWORD or 'ALL'}\n")

# =========================
# 📊 DATA
# =========================

games = defaultdict(int)
wins = defaultdict(int)
tournament_participation = defaultdict(set)

# =========================
# 🔎 2. DATA COLLECT
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
            tournament_participation[u].add(t["id"])

            if winner == "white":
                wins[u] += 1

        # BLACK
        if black_user and (not ONLY_TEAM_MEMBERS or black_team == TEAM_ID):
            u = black_user.lower()

            games[u] += 1
            tournament_participation[u].add(t["id"])

            if winner == "black":
                wins[u] += 1

# =========================
# 🧮 MVP CALCULATION
# =========================

def winrate(u):
    g = games[u]
    return (wins[u] / g) if g > 0 else 0

def participation(u):
    return len(tournament_participation[u]) / total_tournaments if total_tournaments > 0 else 0

def game_score(u):
    # normalisieren (0–1 Bereich, damit fair)
    return min(games[u] / 100, 1)

def mvp(u):
    return (
        winrate(u) * 0.6 +
        game_score(u) * 0.25 +
        participation(u) * 0.15
    ) * 100

# =========================
# 🔥 FILTER + SORT
# =========================

players = [
    u for u in games
    if games[u] >= MIN_GAMES_FOR_MVP
]

ranked = sorted(players, key=lambda u: mvp(u), reverse=True)

# =========================
# 🏆 OUTPUT
# =========================

print("\n⚡ BALANCED MVP RANKING\n")

for i, u in enumerate(ranked, 1):

    g = games[u]
    w = wins[u]
    wr = winrate(u) * 100
    t = len(tournament_participation[u])

    print(
        f"{i}. {u}: {mvp(u):.1f} MVP | "
        f"{wr:.1f}% WR | "
        f"{g} games | "
        f"{t}/{total_tournaments} tournaments"
    )
