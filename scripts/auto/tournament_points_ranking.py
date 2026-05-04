import requests
import json
from collections import defaultdict

TEAM_ID = "DarkOnTeams"
MAX_TOURNEYS = 50
TOURNEY_KEYWORD = "Hourly"  # leer = alle Turniere

headers = {
    "Accept": "application/x-ndjson"
}

# 🔎 1. Turniere holen
url = f"https://lichess.org/api/team/{TEAM_ID}/arena?status=finished"

response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Fehler beim Laden der Turniere")
    exit()

tournaments = []

for line in response.text.splitlines():
    if not line.strip():
        continue
    tournaments.append(json.loads(line))

if not tournaments:
    print("Keine Turniere gefunden")
    exit()

# 🔥 Filter
filtered = []
for t in tournaments:
    name = t["fullName"]

    if TOURNEY_KEYWORD == "" or TOURNEY_KEYWORD.lower() in name.lower():
        filtered.append(t)

selected_tourneys = filtered[:MAX_TOURNEYS]

print(f"\n🏆 POINTS RANKING – Team: {TEAM_ID}")
print(f"Turniere: {len(selected_tourneys)} | Filter: {TOURNEY_KEYWORD if TOURNEY_KEYWORD else 'ALL'}\n")

# 🔥 Punkte sammeln
points = defaultdict(float)

# 🔎 2. Turniere durchgehen
for t in selected_tourneys:
    tourney_id = t["id"]
    print(f"- {t['fullName']} https://lichess.org/tournament/{tourney_id}")

    url = f"https://lichess.org/api/tournament/{tourney_id}/results"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Fehler bei Turnier {tourney_id}")
        continue

    for line in response.text.splitlines():
        if not line.strip():
            continue

        data = json.loads(line)

        username = data.get("username")
        score = data.get("score", 0)

        if username:
            points[username] += score

# 🔎 3. Sortieren
sorted_players = sorted(points.items(), key=lambda x: x[1], reverse=True)

# 🏆 4. Ausgabe
print("\n🏆 POINTS RANKING:\n")

for i, (user, score) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {score} points")
