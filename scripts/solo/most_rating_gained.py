import requests
import json
import time
from collections import defaultdict

# =========================
# CONFIG
# =========================

USERNAME = "DarkOnCrack"

RATED_ONLY = True
GAME_TYPES = "ultraBullet"  # z.B. ["bullet", "blitz"]

chunk_size = 5000

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# DATA
# =========================

rating_balance = defaultdict(int)
games_count = defaultdict(int)

total_analyzed_games = 0
games_fetched = 0

# =========================
# PAGING SETUP
# =========================

BASE_URL = f"https://lichess.org/api/games/user/{USERNAME}"

last_game_id = None

print(f"\n⚡ Rating Analysis for: {USERNAME}\n")

# =========================
# DOWNLOAD + ANALYZE LOOP
# =========================

while True:

    params = {
        "max": chunk_size,
        "rated": "true" if RATED_ONLY else "false",
        "moves": "false",
        "pgnInJson": "false",
    }

    if last_game_id:
        params["until"] = last_game_id

    print(f"⚡ Fetching chunk... (total analyzed: {total_analyzed_games})")

    response = requests.get(BASE_URL, headers=headers, params=params, stream=True)

    if response.status_code != 200:
        print("❌ Error fetching games")
        break

    lines_in_chunk = 0
    last_id_in_chunk = None

    for line in response.iter_lines():
        if not line:
            continue

        game = json.loads(line)
        lines_in_chunk += 1

        last_id_in_chunk = game.get("id")

        # =========================
        # FILTER GAME TYPE
        # =========================

        speed = game.get("speed", "unknown")

        if GAME_TYPES and speed not in GAME_TYPES:
            continue

        players = game.get("players", {})

        white = players.get("white", {})
        black = players.get("black", {})

        white_user = white.get("user", {}).get("name", "")
        black_user = black.get("user", {}).get("name", "")

        # =========================
        # DETERMINE SIDE
        # =========================

        if white_user.lower() == USERNAME.lower():
            me = white
            opponent_name = black_user
        elif black_user.lower() == USERNAME.lower():
            me = black
            opponent_name = white_user
        else:
            continue

        if not opponent_name:
            continue

        # =========================
        # FILTER VALID GAMES
        # =========================

        rating_diff = me.get("ratingDiff")
        if rating_diff is None:
            continue

        if me.get("provisional"):
            continue

        # =========================
        # APPLY STATS
        # =========================

        rating_balance[opponent_name] += rating_diff
        games_count[opponent_name] += 1

        total_analyzed_games += 1
        games_fetched += 1

    if lines_in_chunk == 0:
        break

    if not last_id_in_chunk:
        break

    last_game_id = last_id_in_chunk

    time.sleep(0.3)

# =========================
# SORT RESULTS
# =========================

best = sorted(rating_balance.items(), key=lambda x: x[1], reverse=True)
worst = sorted(rating_balance.items(), key=lambda x: x[1])

# =========================
# OUTPUT
# =========================

print("\n🏆 BEST RATING FARM\n")

rank = 1
for opponent, score in best[:25]:
    if score <= 0:
        continue

    games = games_count[opponent]

    print(f"{rank}. {opponent}: +{score} rating | {games} games | https://lichess.org/@/{opponent}")
    rank += 1

print("\n💀 WORST MATCHUPS\n")

rank = 1
for opponent, score in worst[:25]:
    if score >= 0:
        continue

    games = games_count[opponent]

    print(f"{rank}. {opponent}: {score} rating | {games} games | https://lichess.org/@/{opponent}")
    rank += 1

# =========================
# FINAL SUMMARY
# =========================

print(f"\n📊 Total analyzed games: {total_analyzed_games}\n")
