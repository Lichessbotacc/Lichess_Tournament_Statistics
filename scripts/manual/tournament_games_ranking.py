import requests
import json
from collections import defaultdict

# 🔥 HIER mehrere Turniere eintragen
TOURNEY_IDS = [
    "spring17", "summer17", "autumn17", "winter17",
    "spring18", "summer18", "autumn18", "winter18",
    "spring19", "summer19", "autumn19", "winter19",
    "spring20", "summer20", "autumn20", "winter20",
    "spring21", "summer21", "autumn21", "winter21",
    "spring22", "summer22", "autumn22", "winter22",
    "spring23", "summer23", "autumn23", "winter23",
    "spring24", "summer24", "autumn24", "winter24",
    "spring25", "summer25", "autumn25", "winter25",
    "spring26"
]

headers = {
    "Accept": "application/x-ndjson"
}

games_count = defaultdict(int)

for tid in TOURNEY_IDS:
    print(f"Lade Turnier {tid}...")

    url = f"https://lichess.org/api/tournament/{tid}/games"
    response = requests.get(url, headers=headers, stream=True)

    if response.status_code != 200:
        print(f"Fehler bei {tid}: {response.status_code}")
        continue

    for line in response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        white = game["players"]["white"]["user"]["name"]
        black = game["players"]["black"]["user"]["name"]

        games_count[white] += 1
        games_count[black] += 1

# 🔥 sortieren
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

print("\n⚡ KOMBINIERTE RANGLISTE:\n")

for i, (user, games) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {games} Games played")

    # 🔗 mehrere Links anzeigen
    for tid in TOURNEY_IDS:
        link = f"https://lichess.org/tournament/{tid}?player={user}"
        print(f"   {link}")

    print()
