import requests
import json
import time
from collections import defaultdict

# =========================
# CONFIG
# =========================

USERNAME = "DarkOnCrack"

RATED_ONLY = True

# Beispiele:
# ["ultrabullet"]
# ["bullet", "blitz"]
# [] = alle Varianten
GAME_TYPES = ["ultrabullet"]

chunk_size = 5000

LIVE_PRINTS = True

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# DATA
# =========================

rating_balance = defaultdict(int)
games_count = defaultdict(int)

total_analyzed_games = 0
total_fetched_games = 0

# =========================
# PAGING SETUP
# =========================

BASE_URL = f"https://lichess.org/api/games/user/{USERNAME}"

last_created_at = None

print("\n" + "=" * 60)
print(f"⚡ Rating Analysis for: {USERNAME}")
print(f"🎮 Game types: {GAME_TYPES if GAME_TYPES else 'ALL'}")
print(f"📦 Chunk size: {chunk_size}")
print("=" * 60)

# =========================
# DOWNLOAD + ANALYZE LOOP
# =========================

while True:

    params = {
        "max": chunk_size,
        "moves": False,
        "pgnInJson": False,
    }

    if RATED_ONLY:
        params["rated"] = True

    if last_created_at:
        params["until"] = last_created_at

    print(f"\n📥 Fetching chunk... (analyzed: {total_analyzed_games})")

    response = requests.get(
        BASE_URL,
        headers=headers,
        params=params,
        stream=True
    )

    if response.status_code != 200:
        print(f"❌ Error fetching games: {response.status_code}")
        break

    lines_in_chunk = 0
    last_created_at_in_chunk = None

    for line in response.iter_lines():

        if not line:
            continue

        try:
            game = json.loads(line)

        except:
            continue

        lines_in_chunk += 1
        total_fetched_games += 1

        # Für Pagination
        last_created_at_in_chunk = game.get("createdAt")

        # =========================
        # FILTER GAME TYPE
        # =========================

        speed = game.get("speed", "").lower()

        if GAME_TYPES:
            allowed = [g.lower() for g in GAME_TYPES]

            if speed not in allowed:
                continue

        # =========================
        # PLAYERS
        # =========================

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

        # =========================
        # LIVE PRINT
        # =========================

        if LIVE_PRINTS:

            game_id = game.get("id", "")
            game_link = f"https://lichess.org/{game_id}"

            sign = "+" if rating_diff > 0 else ""

            print(
                f"⚡ Game {total_analyzed_games} | "
                f"vs {opponent_name} | "
                f"{sign}{rating_diff} | "
                f"{game_link}"
            )

    # =========================
    # STOP CONDITIONS
    # =========================

    if lines_in_chunk == 0:
        print("\n✅ No more games found.")
        break

    if not last_created_at_in_chunk:
        print("\n✅ Reached end of games.")
        break

    last_created_at = last_created_at_in_chunk

    print(
        f"📦 Chunk complete | "
        f"Fetched: {total_fetched_games} | "
        f"Analyzed: {total_analyzed_games}"
    )

    # Anti rate-limit
    time.sleep(0.3)

# =========================
# SORT RESULTS
# =========================

best = sorted(
    rating_balance.items(),
    key=lambda x: x[1],
    reverse=True
)

worst = sorted(
    rating_balance.items(),
    key=lambda x: x[1]
)

# =========================
# OUTPUT
# =========================

print("\n" + "=" * 70)
print("🏆 BEST RATING FARM")
print("=" * 70)

rank = 1

for opponent, score in best[:25]:

    if score <= 0:
        continue

    games = games_count[opponent]

    print(
        f"{rank}. {opponent}: "
        f"+{score} rating | "
        f"{games} games | "
        f"https://lichess.org/@/{opponent}"
    )

    rank += 1

print("\n" + "=" * 70)
print("💀 WORST MATCHUPS")
print("=" * 70)

rank = 1

for opponent, score in worst[:25]:

    if score >= 0:
        continue

    games = games_count[opponent]

    print(
        f"{rank}. {opponent}: "
        f"{score} rating | "
        f"{games} games | "
        f"https://lichess.org/@/{opponent}"
    )

    rank += 1

# =========================
# FINAL SUMMARY
# =========================

print("\n" + "=" * 60)
print("📊 FINAL SUMMARY")
print("=" * 60)

print(f"🎮 Total fetched games: {total_fetched_games}")
print(f"✅ Total analyzed games: {total_analyzed_games}")

print("\n✅ Analysis complete.\n")
