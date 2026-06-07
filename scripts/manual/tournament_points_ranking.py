import requests
from collections import defaultdict

# Turniere
TOURNEY_IDS = [
    "cWTnOS4Q"
]

# Team-ID aus der URL:
# https://lichess.org/team/darkonteams
TEAM_ID = "darkonteams"

# -----------------------------------------
# Teammitglieder laden
# -----------------------------------------

print("Lade Teammitglieder...")

team_members = set()

page = 1

while True:
    url = f"https://lichess.org/api/team/{TEAM_ID}/users?page={page}"

    response = requests.get(url)

    if response.status_code != 200:
        print("Fehler beim Laden der Teammitglieder.")
        break

    data = response.json()

    users = data.get("currentPageResults", [])

    if not users:
        break

    for user in users:
        team_members.add(user["name"])

    page += 1

print(f"{len(team_members)} Teammitglieder gefunden.")

# -----------------------------------------
# Punkte sammeln
# -----------------------------------------

points = defaultdict(int)
tournaments_played = defaultdict(int)

for tid in TOURNEY_IDS:

    print(f"Lade Turnier {tid}...")

    page = 1

    while True:

        url = f"https://lichess.org/api/tournament/{tid}/results?nb=200&page={page}"

        response = requests.get(url)

        if response.status_code != 200:
            print(f"Fehler bei Turnier {tid}")
            break

        data = response.json()

        if not data:
            break

        for player in data:

            username = player["username"]

            if username in team_members:

                points[username] += player["score"]
                tournaments_played[username] += 1

        page += 1

# -----------------------------------------
# Ranking
# -----------------------------------------

ranking = sorted(
    points.items(),
    key=lambda x: x[1],
    reverse=True
)

print("\n🏆 DARKONTEAMS ARENA PUNKTE\n")

for pos, (user, score) in enumerate(ranking, 1):

    played = tournaments_played[user]

    print(
        f"{pos}. {user} | "
        f"Points: {score} | "
        f"Tournaments: {played}"
    )
