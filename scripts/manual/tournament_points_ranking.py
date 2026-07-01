import requests
import json
from collections import defaultdict

# 🔥 SETTINGS
TARGET_TEAM = "darkonteams"
TOURNEY_IDS = ["cWTnOS4Q", "4DzfnhBJ", "qEm4TOdC", "SmRc33Eo","rDDxmCDh","kqszcf5M", "BzQpoZmF", "ll7DaWIj"]

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "lichess-team-analyzer"
})

# -----------------------------------------
# TEAM LADEN (NDJSON SAFE)
# -----------------------------------------
print(f"📥 Lade Team: {TARGET_TEAM}")

team_members = set()

url = f"https://lichess.org/api/team/{TARGET_TEAM}/users"

r = session.get(url, stream=True)

if r.status_code != 200:
    print("❌ Fehler beim Laden des Teams:", r.status_code)
    print(r.text[:200])
    exit()

for line in r.iter_lines():
    if not line:
        continue

    try:
        user = json.loads(line)
    except json.JSONDecodeError:
        continue

    name = user.get("name") or user.get("username") or user.get("id")

    if name:
        team_members.add(name.lower())

print(f"✅ Teammitglieder geladen: {len(team_members)}")

# -----------------------------------------
# TURNIERE AUSWERTEN (NDJSON SAFE)
# -----------------------------------------
points = defaultdict(int)

for tid in TOURNEY_IDS:
    print(f"\n📊 Turnier: {tid}")

    url = f"https://lichess.org/api/tournament/{tid}/results"
    r = session.get(url, stream=True)

    if r.status_code != 200:
        print(f"❌ Fehler bei Turnier {tid}: {r.status_code}")
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

        # 🔥 Team-Filter (case-insensitive)
        if username.lower() not in team_members:
            continue

        print(f"{tid} | {username} +{score}")
        points[username] += score

# -----------------------------------------
# RANKING
# -----------------------------------------
ranking = sorted(points.items(), key=lambda x: x[1], reverse=True)

print(f"\n🏆 {TARGET_TEAM.upper()} RANKING\n")

if not ranking:
    print("Keine Daten gefunden.")
else:
    for i, (user, score) in enumerate(ranking, 1):
        print(f"{i}. {user}: {score}")
