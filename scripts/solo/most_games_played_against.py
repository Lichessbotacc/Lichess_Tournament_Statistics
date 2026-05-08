import requests
import json
from collections import defaultdict

# =========================
# ⚙️ SETTINGS
# =========================

USERNAME = "heallan"

PERF_TYPE = "ultraBullet"

MAX_GAMES = 10000000
MIN_GAMES_VS = 50
LIVE_PRINTS = False

# =========================
# START INFO
# =========================

print("\n" + "=" * 60)
print(f"👤 Analyzing user: {USERNAME}")
print(f"♟ Variant: {PERF_TYPE}")
print(f"🎮 Max games: {MAX_GAMES}")
print("=" * 60)

print(f"\n📥 Lade {PERF_TYPE} Partien von {USERNAME}...\n")

# =========================
# ONLY CHANGE: REQUEST (PAGINATION ADDED)
# =========================

def game_stream():

    url = f"https://lichess.org/api/games/user/{USERNAME}"

    headers = {
        "Accept": "application/x-ndjson"
    }

    until = None
    total = 0

    while total < MAX_GAMES:

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

        batch_count = 0
        last_created_at = None

        for line in response.iter_lines():

            if not line:
                continue

            game = json.loads(line)

            batch_count += 1
            last_created_at = game.get("createdAt")

            yield game   # 🔥 WICHTIG: LIVE STREAM BLEIBT

        total += batch_count

        print(f"📦 {total} games geladen...")

        if batch_count < 10000:
            break

        until = last_created_at


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
# ANALYSE (UNCHANGED LOGIC)
# =========================

for game in game_stream():

    try:
        white = game["players"]["white"]["user"]["name"]
        black = game["players"]["black"]["user"]["name"]

        winner = game.get("winner")

        # Gegner bestimmen
        if white.lower() == USERNAME.lower():
            opponent = black
            user_color = "white"
        else:
            opponent = white
            user_color = "black"

        games += 1

        # Live Print Toggle
        if LIVE_PRINTS:
            game_id = game.get("id")
            game_link = f"https://lichess.org/{game_id}"

            print(
                f"⚡ Analyzing game {games}: "
                f"vs {opponent} | "
                f"{game_link}"
            )

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
# SORTIEREN
# =========================

sorted_stats = sorted(
    stats.items(),
    key=lambda x: x[1]["games"],
    reverse=True
)

# =========================
# OUTPUT
# =========================

print("\n" + "=" * 70)
print(f"📊 MOST PLAYED OPPONENTS ({PERF_TYPE})")
print("=" * 70)

rank = 1

for opponent, s in sorted_stats:

    if s["games"] < MIN_GAMES_VS:
        continue

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

    rank += 1

print("\n✅ Analysis complete.")
