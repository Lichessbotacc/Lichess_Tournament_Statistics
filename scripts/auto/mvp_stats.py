import requests
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import os

# =========================
# ⚙️ CONFIG
# =========================

TEAM_ID = "darkonteams"
ONLY_TEAM_MEMBERS = True
TOURNEY_KEYWORD = "LMAO"
MAX_TOURNEYS = 10
MIN_GAMES_FOR_MVP = 50

headers = {
    "Accept": "application/x-ndjson",
    "User-Agent": "mvp-stats-bot"
}

# =========================
# 💾 CACHE (NEW)
# =========================

PROCESSED_FILE = "processed_games.json"

if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "r") as f:
        processed_games = set(json.load(f))
else:
    processed_games = set()

cache = {}

# =========================
# 🔎 1. TURNIERE LADEN
# =========================

url = f"https://lichess.org/api/team/{TEAM_ID}/arena?status=finished"
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("❌ Fehler beim Laden der Turniere")
    exit()

tournaments = []
for line in response.text.splitlines():
    if line.strip():
        try:
            tournaments.append(json.loads(line))
        except:
            continue

selected_tourneys = [
    t for t in tournaments
    if TOURNEY_KEYWORD.lower() in t.get("fullName", "").lower()
][:MAX_TOURNEYS]

print("\n" + "=" * 60)
print(f"🏆 MVP STATS – {TEAM_ID}")
print(f"📊 Turniere: {len(selected_tourneys)}")
print("=" * 60)

# =========================
# 📊 DATA
# =========================

games = defaultdict(int)
wins = defaultdict(int)
participation = defaultdict(set)

# =========================
# ⚡ FAST GAME PROCESSING
# =========================

def process_game(game):
    global processed_games

    game_id = game.get("id")
    if not game_id or game_id in processed_games:
        return

    white = game.get("players", {}).get("white", {})
    black = game.get("players", {}).get("black", {})

    white_user = white.get("user", {}).get("name")
    black_user = black.get("user", {}).get("name")

    white_team = white.get("team")
    black_team = black.get("team")

    winner = game.get("winner")

    if white_user:
        u = white_user.lower()
        games[u] += 1
        participation[u].add(game["tournamentId"])
        if winner == "white":
            wins[u] += 1

    if black_user:
        u = black_user.lower()
        games[u] += 1
        participation[u].add(game["tournamentId"])
        if winner == "black":
            wins[u] += 1

    processed_games.add(game_id)

# =========================
# 🔎 2. TURNIERE ANALYSIEREN (PARALLEL)
# =========================

for t in selected_tourneys:

    print(f"\n🏁 {t.get('fullName')}")
    print(f"🔗 https://lichess.org/tournament/{t.get('id')}")

    games_url = f"https://lichess.org/api/tournament/{t['id']}/games"

    r = requests.get(games_url, headers=headers)
    if r.status_code != 200:
        continue

    game_list = []

    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            game_list.append(json.loads(line))
        except:
            continue

    # 🔥 PARALLEL PROCESSING
    with ThreadPoolExecutor(max_workers=8) as ex:
        ex.map(process_game, game_list)

# =========================
# 💾 SAVE STATE (NEW)
# =========================

with open(PROCESSED_FILE, "w") as f:
    json.dump(list(processed_games), f)

# =========================
# 🧠 MVP FORMEL (unchanged)
# =========================

def winrate(u):
    return wins[u] / games[u] if games[u] > 0 else 0

def activity(u):
    return min(games[u] / 50, 1)

def tourney_participation(u):
    return len(participation[u]) / len(selected_tourneys) if selected_tourneys else 0

def mvp_score(u):
    return (
        winrate(u) * 0.6 +
        activity(u) * 0.25 +
        tourney_participation(u) * 0.15
    ) * 100

# =========================
# 🏆 FILTER + SORT
# =========================

players = [
    u for u in games
    if games[u] >= MIN_GAMES_FOR_MVP
]

ranked = sorted(players, key=mvp_score, reverse=True)

# =========================
# 📊 OUTPUT
# =========================

print("\n" + "=" * 60)
print("🏆 FINAL MVP RANKING")
print("=" * 60 + "\n")

for i, u in enumerate(ranked, 1):

    g = games[u]
    w = wins[u]
    wr = winrate(u) * 100
    t = len(participation[u])

    print(
        f"{i}. {u}: {mvp_score(u):.1f} MVP | "
        f"{wr:.1f}% WR | "
        f"{g} games | "
        f"{t}/{len(selected_tourneys)} tournaments"
    )
