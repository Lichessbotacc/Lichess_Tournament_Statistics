import requests
import json
import time
from collections import defaultdict

# 🔥 SETTINGS
TARGET_TEAM = "darkonteams"
TOURNEY_IDS = ["cWTnOS4Q"]

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "lichess-stats-bot"
})

# -----------------------------------------
# SAFE REQUEST HELPER
# -----------------------------------------
def safe_get(url, retries=3, timeout=10):
    for i in range(retries):
        try:
            r = session.get(url, timeout=timeout)

            if r.status_code == 429:
                print("⚠️ Rate limit – warte 2s...")
                time.sleep(2)
                continue

            if r.status_code != 200:
                print(f"❌ HTTP Error {r.status_code}")
                time.sleep(1)
                continue

            return r

        except requests.RequestException as e:
            print(f"⚠️ Request Fehler: {e}")
            time.sleep(1)

    return None


# -----------------------------------------
# TEAM LADEN (ROBUST)
# -----------------------------------------
print(f"📥 Lade Team: {TARGET_TEAM}")

team_members = set()
page = 1

while True:
    url = f"https://lichess.org/api/team/{TARGET_TEAM}/users?page={page}"
    r = safe_get(url)

    if not r:
        print("❌ Team konnte nicht geladen werden")
        break

    try:
        data = r.json()
    except Exception:
        print("❌ JSON Fehler bei Team API")
        print(r.text[:200])
        break

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
    time.sleep(0.2)  # respektvoll zur API

print(f"✅ Teammitglieder: {len(team_members)}")


# -----------------------------------------
# TOURNAMENT AUSWERTUNG (NDJSON SAFE)
# -----------------------------------------
points = defaultdict(int)

for tid in TOURNEY_IDS:
    print(f"\n📊 Turnier: {tid}")

    url = f"https://lichess.org/api/tournament/{tid}/results"
    r = safe_get(url)

    if not r:
        print(f"❌ Turnier {tid} nicht geladen")
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

        if username not in team_members:
            continue

        print(f"{tid} | {username} +{score}")
        points[username] += score


# -----------------------------------------
# RANKING
# -----------------------------------------
ranking = sorted(points.items(), key=lambda x: x[1], reverse=True)

print("\n🏆 TEAM RANKING\n")

if not ranking:
    print("Keine Daten gefunden.")
else:
    for i, (user, score) in enumerate(ranking, 1):
        print(f"{i}. {user}: {score}")
