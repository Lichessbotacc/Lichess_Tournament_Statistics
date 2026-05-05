import requests
import json
from collections import defaultdict

# =========================
# ⚙️ CONFIG
# =========================

TEAM_ID = "darkonteams"

ONLY_TEAM_MEMBERS = True
TOURNEY_KEYWORD = ""
MAX_TOURNEYS = 1

MIN_GAMES_FOR_MVP = 5

headers = {
    "Accept": "application/x-ndjson",
    "User-Agent": "mvp-stats-bot"
}

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
# 🔎 2. TURNIERE ANALYSIEREN
# =========================

for t in selected_tourneys:

    print(f"\n🏁 {t.get('fullName')}")
    print(f"🔗 https://lichess.org/tournament/{t.get('id')}")

    team_players = set()

    games_url = f"https://lichess.org/api/tournament/{t['id']}/games"

    r = requests.get(games_url, headers=headers)

    if r.status_code != 200:
        continue

    for line in r.iter_lines(decode_unicode=True):
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
            games[u] += 1
            participation[u].add(t["id"])

            if winner == "white":
                wins[u] += 1

            if white_team == TEAM_ID:
                team_players.add(u)

        # BLACK
        if black_user:
            u = black_user.lower()
            games[u] += 1
            participation[u].add(t["id"])

            if winner == "black":
                wins[u] += 1

            if black_team == TEAM_ID:
                team_players.add(u)

# =========================
# 🧠 MVP FORMEL
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
