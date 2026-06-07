import requests
import json
from collections import defaultdict

# 🔥 TEAM FESTLEGEN
TARGET_TEAM = "darkonteams"

# 🔥 TURNIERE
TOURNEY_IDS = ["cWTnOS4Q"]

# -----------------------------------------
# Teammitglieder laden
# -----------------------------------------
print(f"Lade Teammitglieder von {TARGET_TEAM}...")

team_members = set()
page = 1

headers = {
    "Accept": "application/json",
    "User-Agent": "lichess-team-stats-script"
}

while True:
    url = f"https://lichess.org/api/team/{TARGET_TEAM}/users?page={page}"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print("❌ Fehler beim Laden des Teams")
        break

    data = r.json()

    # 🔥 robuste API-Auswertung (Lichess kann variieren)
    users = (
        data.get("currentPageResults")
        or data.get("users")
        or data.get("members")
        or []
    )

    if not users:
        break

    for u in users:
        name = u.get("name") or u.get("username")
        if name:
            team_members.add(name)

    page += 1

print(f"✅ {len(team_members)} Teammitglieder geladen.")

# -----------------------------------------
# Turniere auswerten
# -----------------------------------------
points = defaultdict(int)

for tid in TOURNEY_IDS:

    print(f"\n📊 Lade Turnier {tid}...\n")

    url = f"https://lichess.org/api/tournament/{tid}/results"

    r = requests.get(
        url,
        headers={"Accept": "application/x-ndjson"},
        stream=True
    )

    if r.status_code != 200:
        print(f"❌ Fehler bei Turnier {tid}")
        continue

    for line in r.iter_lines():

        if not line:
            continue

        try:
            player = json.loads(line)
        except json.JSONDecodeError:
            continue

        username = player.get("username")
        score = player.get("score", 0)

        if not username:
            continue

        # 🔥 nur Teammitglieder
        if username not in team_members:
            continue

        print(f"{tid} | {username} +{score}")

        points[username] += score

# -----------------------------------------
# Ranking erstellen
# -----------------------------------------
ranking = sorted(points.items(), key=lambda x: x[1], reverse=True)

print(f"\n🏆 {TARGET_TEAM.upper()} RANKING\n")

if not ranking:
    print("Keine Daten gefunden.")
else:
    for i, (user, score) in enumerate(ranking, 1):
        print(f"{i}. {user}: {score}")
