import requests
import json
from collections import defaultdict

# 🔥 HIER TEAM FESTLEGEN
TARGET_TEAM = "darkonteams"

TOURNEY_IDS = ["cWTnOS4Q"]

# -----------------------------------------
# Teammitglieder laden
# -----------------------------------------
print(f"Lade Teammitglieder von {TARGET_TEAM}...")

team_members = set()
page = 1

while True:
    url = f"https://lichess.org/api/team/{TARGET_TEAM}/users?page={page}"
    r = requests.get(url)

    if r.status_code != 200:
        print("Fehler beim Laden des Teams")
        break

    data = r.json()
    users = data.get("currentPageResults", [])

    if not users:
        break

    for u in users:
        team_members.add(u["name"])

    page += 1

print(f"{len(team_members)} Mitglieder geladen.")

# -----------------------------------------
# Turniere auswerten
# -----------------------------------------
points = defaultdict(int)

for tid in TOURNEY_IDS:

    print(f"\nLade Turnier {tid}...\n")

    url = f"https://lichess.org/api/tournament/{tid}/results"

    r = requests.get(
        url,
        headers={"Accept": "application/x-ndjson"},
        stream=True
    )

    if r.status_code != 200:
        print(f"Fehler bei {tid}")
        continue

    for line in r.iter_lines():

        if not line:
            continue

        player = json.loads(line)

        username = player["username"]
        score = player["score"]

        # 🔥 NUR TARGET_TEAM
        if username not in team_members:
            continue

        print(f"{tid} | {username} +{score}")

        points[username] += score

# -----------------------------------------
# Ranking
# -----------------------------------------
ranking = sorted(points.items(), key=lambda x: x[1], reverse=True)

print(f"\n🏆 {TARGET_TEAM.upper()} RANKING\n")

for i, (user, score) in enumerate(ranking, 1):
    print(f"{i}. {user}: {score}")
