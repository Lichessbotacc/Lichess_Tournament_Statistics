import requests
import json
from collections import defaultdict

TOURNEY_IDS = [
    "cWTnOS4Q"
]

points = defaultdict(int)

for tid in TOURNEY_IDS:

    print(f"\nLade Turnier {tid}...\n")

    url = f"https://lichess.org/api/tournament/{tid}/results"

    response = requests.get(
        url,
        headers={"Accept": "application/x-ndjson"},
        stream=True
    )

    if response.status_code != 200:
        print(f"Fehler bei {tid}")
        continue

    for line in response.iter_lines():

        if not line:
            continue

        player = json.loads(line)

        username = player["username"]
        score = player["score"]

        # 🔥 LIVE OUTPUT PRO EINTRAG
        print(f"{tid} | {username} +{score}")

        points[username] += score

# Ranking
ranking = sorted(points.items(), key=lambda x: x[1], reverse=True)

print("\n🏆 GESAMTRANKING\n")

for pos, (user, score) in enumerate(ranking, 1):
    print(f"{pos}. {user}: {score}")
