import requests
import json
from collections import defaultdict
from datetime import datetime

USERNAME = "DarkOnCrack"

# 🔧 OPTIONAL FILTER
KEYWORD = "Solo Bullet"
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

    tournament_ids.append(t["id"])
    tournament_list.append((t["id"], t.get("fullName", "Unknown")))


# 🔹 Games zählen + W/D/L
stats = defaultdict(lambda: {"w": 0, "d": 0, "l": 0})

for tid, _ in tournament_list:
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

            wres = game["status"]  # win/loss/draw info kommt indirekt über status
            winner = game.get("winner")

        except:
            continue

        # nur zählen wenn User beteiligt
        for player in [white, black]:
            if player not in stats:
                stats[player] = {"w": 0, "d": 0, "l": 0}

        # Ergebnis bestimmen
        if winner == "white":
            stats[white]["w"] += 1
            stats[black]["l"] += 1
        elif winner == "black":
            stats[black]["w"] += 1
            stats[white]["l"] += 1
        else:
            stats[white]["d"] += 1
            stats[black]["d"] += 1


# 🔹 Filtern + Sortieren
filtered = []
for user, s in stats.items():
    games = s["w"] + s["d"] + s["l"]
    if games >= MIN_GAMES:
        winrate = (s["w"] / games) * 100 if games > 0 else 0
        filtered.append((user, games, s["w"], s["d"], s["l"], winrate))

sorted_players = sorted(filtered, key=lambda x: x[1], reverse=True)


# 🔥 OUTPUT
print("\n⚡ BEST PERFORMANCE (W/D/L + Winrate)\n")

print("📌 TURNIERE:\n")
for tid, name in tournament_list:
    print(f"- {name} ({tid})")

print("\n📊 SPIELER:\n")

for i, (user, games, w, d, l, wr) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {w}W {d}D {l}L | {wr:.2f}% | {games} games")
