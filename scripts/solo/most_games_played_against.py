import requests
import json
from collections import defaultdict

# =========================
# ⚙️ SETTINGS
# =========================

USERNAME = "DarkOnCrack"

# ♟ Available Lichess perfTypes:
# bullet
# blitz
# rapid
# classical
# ultraBullet
# correspondence
# chess960
# crazyhouse
# antichess
# atomic
# horde
# kingOfTheHill
# racingKings
# threeCheck

PERF_TYPE = "ultraBullet"

MAX_GAMES = 5000000
MIN_GAMES_VS = 1

# =========================
# START INFO
# =========================

print("\n" + "=" * 60)
print(f"👤 Analyzing user: {USERNAME}")
print(f"♟ Variant: {PERF_TYPE}")
print(f"🎮 Max games: {MAX_GAMES}")
print("=" * 60)

# =========================
# FETCH (PAGINATION + LIVE STREAM)
# =========================

def fetch_games():

    url = f"https://lichess.org/api/games/user/{USERNAME}"

    headers = {
        "Accept": "application/x-ndjson"
    }

    games_loaded = 0
    until = None

    while games_loaded < MAX_GAMES:

        params = {
            "max": 10000,
            "perfType": PERF_TYPE,
            "moves": False,
            "pgnInJson": False
        }

        if until:
            params["until"] = until

        response = requests.get(url, params=params, headers=headers, stream=True)

        if response.status_code != 200:
            print("❌ Fehler beim Laden:", response.status_code)
            break

        batch = []
        last_id = None

        for line in response.iter_lines():

            if not line:
                continue

            game = json.loads(line)
            batch.append(game)
            last_id = game.get("id")

        if not batch:
            break

        games_loaded += len(batch)

        print(f"📦 Loaded {games_loaded} games so far...")

        yield batch   # 🔥 LIVE STREAM

        if len(batch) < 10000:
            break

        until = last_id

# =========================
# STATS
# =========================

stats = defaultdict(lambda: {
    "games": 0,
    "wins": 0,
    "losses": 0,
    "draws": 0
})

games = 0

# =========================
# ANALYSE
# =========================

for batch in fetch_games():

    for game in batch:

        try:
            white = game["players"]["white"]["user"]["name"]
            black = game["players"]["black"]["user"]["name"]

            winner = game.get("winner")

            if white.lower() == USERNAME.lower():
                opponent = black
                user_color = "white"
            else:
                opponent = white
                user_color = "black"

            games += 1

            # 🔥 LIVE PRINT
            print(f"⚡ Analyzing game {games}: vs {opponent}")

            stats[opponent]["games"] += 1

            if winner is None:
                stats[opponent]["draws"] += 1

            elif winner == user_color:
                stats[opponent]["wins"] += 1

            else:
                stats[opponent]["losses"] += 1

        except:
            continue

# =========================
# FILTER + SORT
# =========================

filtered_stats = {
    opponent: s
    for opponent, s in stats.items()
    if s["games"] >= MIN_GAMES_VS
}

sorted_stats = sorted(
    filtered_stats.items(),
    key=lambda x: x[1]["games"],
    reverse=True
)

# =========================
# OUTPUT
# =========================

print("\n" + "=" * 70)
print(f"📊 MOST PLAYED OPPONENTS ({PERF_TYPE})")
print("=" * 70)

if not sorted_stats:
    print("❌ No opponents found.")
else:

    rank = 1

    best_opponent = None
    worst_opponent = None

    for opponent, s in sorted_stats:

        games_count = s["games"]
        wins = s["wins"]
        losses = s["losses"]
        draws = s["draws"]

        winrate = (wins / games_count) * 100 if games_count > 0 else 0

        print(
            f"{rank}. {opponent} | "
            f"{games_count} games | "
            f"{wins}W {losses}L {draws}D | "
            f"{winrate:.1f}% WR"
        )

        if best_opponent is None or winrate > best_opponent[1]:
            best_opponent = (opponent, winrate, games_count)

        if games_count >= 5:
            if worst_opponent is None or winrate < worst_opponent[1]:
                worst_opponent = (opponent, winrate, games_count)

        rank += 1

    print("\n" + "=" * 70)

    if best_opponent:
        print(f"🔥 BEST MATCHUP: {best_opponent[0]} ({best_opponent[1]:.1f}% WR | {best_opponent[2]} games)")

    if worst_opponent:
        print(f"💀 WORST MATCHUP: {worst_opponent[0]} ({worst_opponent[1]:.1f}% WR | {worst_opponent[2]} games)")

print("\n✅ Analysis complete.")
