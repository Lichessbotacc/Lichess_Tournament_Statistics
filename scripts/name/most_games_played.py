import requests
import json
from collections import defaultdict
from datetime import datetime

USERNAME = "DarkOnCrack"

# 🔧 OPTIONAL FILTER
KEYWORD = "Solo Rapid"
MIN_PLAYERS = 0
SINCE_YEAR = 0
MIN_GAMES = 1

headers = {
    "Accept": "application/x-ndjson"
}

# 🔹 Turniere laden
tournament_ids = []
tournament_list = []

url = f"https://lichess.org/api/user/{USERNAME}/tournament/created"
response = requests.get(url, headers=headers, stream=True)

for line in response.iter_lines():
    if not line:
        continue

    t = json.loads(line)

    name = t.get("fullName", "").lower()
    nb_players = t.get("nbPlayers", 0)
    created = t.get("created")

    year = datetime.utcfromtimestamp(created / 1000).year if created else 0

    if KEYWORD and KEYWORD.lower() not in name:
        continue
    if MIN_PLAYERS and nb_players < MIN_PLAYERS:
        continue
    if SINCE_YEAR and year < SINCE_YEAR:
        continue

    tid = t["id"]
    tournament_ids.append(tid)

    # 🔥 Lichess Link statt ID
    tournament_list.append((tid, t.get("fullName", "Unknown"), f"https://lichess.org/tournament/{tid}"))


# 🔹 Games + W/D/L
stats = defaultdict(lambda: {"w": 0, "d": 0, "l": 0})

for tid, _, _ in tournament_list:
    url = f"https://lichess.org/api/tournament/{tid}/games"
    response = requests.get(url, headers=headers, stream=True)

    if response.status_code != 200:
        continue

    for line in response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        try:
            white = game["players"]["white"]["user"]["name"]
            black = game["players"]["black"]["user"]["name"]
            winner = game.get("winner")
        except:
            continue

        if winner == "white":
            stats[white]["w"] += 1
            stats[black]["l"] += 1
        elif winner == "black":
            stats[black]["w"] += 1
            stats[white]["l"] += 1
        else:
            stats[white]["d"] += 1
            stats[black]["d"] += 1


# 🔹 Filter + sort
filtered = []
for user, s in stats.items():
    games = s["w"] + s["d"] + s["l"]
    if games >= MIN_GAMES:
        winrate = (s["w"] / games) * 100 if games > 0 else 0
        filtered.append((user, games, s["w"], s["d"], s["l"], winrate))

sorted_players = sorted(filtered, key=lambda x: x[1], reverse=True)


# 🔥 OUTPUT
print("\n⚡ BEST PERFORMANCE (Games → W/D/L → Winrate)\n")

print("📌 TURNIERE:\n")
for _, name, link in tournament_list:
    print(f"- {name} | {link}")

print("\n📊 SPIELER:\n")

for i, (user, games, w, d, l, wr) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {games} games | {w}W {d}D {l}L | {wr:.2f}%")
