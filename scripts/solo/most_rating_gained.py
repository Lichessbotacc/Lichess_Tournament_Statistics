import requests
import json
from collections import defaultdict

# =========================
# CONFIG
# =========================

USERNAME = "DarkOnCrack"

PERF_TYPE = "rapid"   # "blitz", "bullet", "ultrabullet", "" = all

MAX_GAMES = 10000000
LIVE_PRINTS = True

# =========================
# START INFO
# =========================

print("\n" + "=" * 60)
print(f"⚡ Rating Analysis for: {USERNAME}")
print(f"♟ Variant: {PERF_TYPE if PERF_TYPE else 'ALL'}")
print("=" * 60)

# =========================
# DATA
# =========================

rating_balance = defaultdict(int)
games_count = defaultdict(int)

total_games = 0

# =========================
# STREAM
# =========================

def game_stream():

    url = f"https://lichess.org/api/games/user/{USERNAME}"
    headers = {"Accept": "application/x-ndjson"}

    until = None
    fetched = 0

    while fetched < MAX_GAMES:

        params = {
            "max": 1000,
            "moves": False,
            "pgnInJson": False
        }

        if PERF_TYPE:
            params["perfType"] = PERF_TYPE

        if until:
            params["until"] = until

        response = requests.get(url, params=params, headers=headers, stream=True)

        if response.status_code != 200:
            print("❌ Error:", response.status_code)
            break

        batch = 0
        last_created_at = None

        for line in response.iter_lines():

            if not line:
                continue

            try:
                game = json.loads(line)
            except:
                continue

            batch += 1
            fetched += 1

            last_created_at = game.get("createdAt")

            yield game

        if batch == 0:
            break

        until = last_created_at

        print(f"📦 Loaded: {fetched} games")


# =========================
# ANALYSIS
# =========================

for game in game_stream():

    try:
        white = game["players"]["white"]["user"]["name"]
        black = game["players"]["black"]["user"]["name"]

        winner = game.get("winner")

        white_data = game["players"]["white"]
        black_data = game["players"]["black"]

        if white.lower() == USERNAME.lower():
            opponent = black
            me = white_data
            color = "white"
        else:
            opponent = white
            me = black_data
            color = "black"

        total_games += 1

        # =========================
        # RATING DIFF FIX
        # =========================

        rating_diff = me.get("ratingDiff", 0)

        # =========================
        # LIVE PRINT
        # =========================

        if LIVE_PRINTS:
            sign = "+" if rating_diff > 0 else ""
            print(
                f"⚡ Game {total_games} vs {opponent} | "
                f"{sign}{rating_diff} | "
                f"https://lichess.org/{game.get('id')}"
            )

        rating_balance[opponent] += rating_diff
        games_count[opponent] += 1

    except:
        continue


# =========================
# SORT
# =========================

best = sorted(rating_balance.items(), key=lambda x: x[1], reverse=True)
worst = sorted(rating_balance.items(), key=lambda x: x[1])

# =========================
# OUTPUT
# =========================

print("\n" + "=" * 70)
print("🏆 BEST RATING FARM")
print("=" * 70)

rank = 1

for opponent, score in best[:25]:

    if games_count[opponent] < 5:
        continue

    print(
        f"{rank}. {opponent} | "
        f"+{score} rating | "
        f"{games_count[opponent]} games"
    )

    rank += 1

print("\n" + "=" * 70)
print("💀 WORST MATCHUPS")
print("=" * 70)

rank = 1

for opponent, score in worst[:25]:

    if games_count[opponent] < 5:
        continue

    print(
        f"{rank}. {opponent} | "
        f"{score} rating | "
        f"{games_count[opponent]} games"
    )

    rank += 1

print("\n✅ Done")
