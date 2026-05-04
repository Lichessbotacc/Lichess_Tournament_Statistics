import requests
import json

TOURNEY_ID = "spring26"  # <-- hier deine Turnier-ID einsetzen

url = f"https://lichess.org/api/tournament/{TOURNEY_ID}/results"

headers = {
    "Accept": "application/x-ndjson"
}

response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Fehler beim Abrufen der Daten:", response.status_code)
    exit()

games_count = {}

for line in response.text.splitlines():
    if not line.strip():
        continue

    data = json.loads(line)  # ✅ statt eval

    username = data.get("username")
    games = data.get("games", 0)

    if username:
        games_count[username] = games

# sortieren nach Anzahl Spiele (absteigend)
sorted_players = sorted(games_count.items(), key=lambda x: x[1], reverse=True)

print("Rangliste nach gespielten Partien:")
for i, (user, games) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {games} Spiele")
