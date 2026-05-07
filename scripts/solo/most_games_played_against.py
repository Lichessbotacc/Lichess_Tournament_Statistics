import requests
import json
from collections import defaultdict

# =========================
# ⚙️ SETTINGS
# =========================

USERNAME = "DarkOnCrack"

PERF_TYPE = "ultraBullet"

MAX_GAMES = 500000
MIN_GAMES_VS = 50

# =========================

url = f"https://lichess.org/api/games/user/{USERNAME}"

headers = {
    "Accept": "application/x-ndjson"
}

print(f"\n📥 Lade {PERF_TYPE} Partien von {USERNAME}...\n")

# =========================
# PAGINATION (ONLY ADDITION)
# =========================

def fetch_all_games():
    games = []
    until = None

    while len(games) < MAX_GAMES:

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

        games.extend(batch)

        print(f"📦 {len(games)} Spiele geladen...")

        if len(batch) < 10000:
            break

        until = last_id

    return games


# =========================
# LOAD
# =========================

all_games = fetch_all_games()

# =========================
# ANALYSE (UNCHANGED LOGIC)
# =========================

opponents = defaultdict(int)

games = 0

for game in all_games:

    try:
        white = game["players"]["white"]["user"]["name"]
        black = game["players"]["black"]["user"]["name"]

        if white.lower() == USERNAME.lower():
            opponent = black
        else:
            opponent = white

        opponents[opponent] += 1
        games += 1

        if games % 100 == 0:
            print(f"⚡ {games} Spiele analysiert...")

    except:
        continue

# =========================
# SORT
# =========================

sorted_opponents = sorted(
    opponents.items(),
    key=lambda x: x[1],
    reverse=True
)

# =========================
# OUTPUT
# =========================

print("\n" + "=" * 50)
print(f"📊 MOST PLAYED OPPONENTS ({PERF_TYPE})")
print("=" * 50)

rank = 1

for opponent, count in sorted_opponents:

    if count < MIN_GAMES_VS:
        continue

    print(f"{rank}. {opponent}: {count} games")
    rank += 1

print("\n✅ Fertig.")
