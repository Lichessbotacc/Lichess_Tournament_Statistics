import requests
import json
from collections import defaultdict

# =========================
# CONFIG
# =========================

USERNAME = "SeherHavva"
MAX_GAMES = 10000

# Optional:
RATED_ONLY = True
GAME_TYPES = "ultraBullet"
# Beispiel:
# GAME_TYPES = ["bullet", "blitz"]

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# DATA
# =========================

rating_balance = defaultdict(int)
games_count = defaultdict(int)

# =========================
# DOWNLOAD GAMES
# =========================

url = (
    f"https://lichess.org/api/games/user/{USERNAME}"
    f"?max={MAX_GAMES}"
    f"&rated={'true' if RATED_ONLY else 'false'}"
    f"&moves=false"
    f"&pgnInJson=false"
)

print("⚡ Downloading games...\n")

response = requests.get(url, headers=headers, stream=True)

if response.status_code != 200:
    print("❌ Error downloading games")
    exit()

# =========================
# ANALYZE
# =========================

for line in response.iter_lines():
    if not line:
        continue

    game = json.loads(line)

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
        opponent = black
        opponent_name = black_user

    elif black_user.lower() == USERNAME.lower():
        me = black
        opponent = white
        opponent_name = white_user

    else:
        continue

    if not opponent_name:
        continue

    rating_diff = me.get("ratingDiff")

    if rating_diff is None:
        continue

    # Ignore provisional / unstable games
    if me.get("provisional"):
        continue

    rating_balance[opponent_name] += rating_diff
    games_count[opponent_name] += 1

# =========================
# SORT
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

print("\n🏆 BEST RATING FARM\n")

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

print("\n💀 WORST MATCHUPS\n")

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
