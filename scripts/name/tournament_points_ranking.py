import requests
import json
from collections import defaultdict

# =========================
# ⚙️ CONFIG
# =========================

USERNAME = "DarkOnCrack"

# 🔧 OPTIONAL FILTER
KEYWORDS = ["Solo Rapid"]   # [] = alle Turniere
MIN_PLAYERS = 0
SINCE_YEAR = 0
MAX_TOURNEYS = 500

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# 🔎 1. TURNIERE LADEN
# =========================

url = f"https://lichess.org/api/user/{USERNAME}/tournament/created"
response = requests.get(url, headers=headers, stream=True)

if response.status_code != 200:
    print("Fehler beim Laden der Turniere")
    exit()

tournaments = [
    json.loads(line)
    for line in response.text.splitlines()
    if line.strip()
]

# =========================
# 🔥 FILTER
# =========================

selected_tourneys = []
for t in tournaments:
    name = t.get("fullName", "").lower()
    created = t.get("created")

    year = 0
    if created:
        year = int(created // 1000)
        year = int(__import__("datetime").datetime.utcfromtimestamp(year).year)

    if KEYWORDS:
        if not any(k.lower() in name for k in KEYWORDS):
            continue

    if MIN_PLAYERS and t.get("nbPlayers", 0) < MIN_PLAYERS:
        continue

    if SINCE_YEAR and year < SINCE_YEAR:
        continue

    selected_tourneys.append(t)

selected_tourneys = selected_tourneys[:MAX_TOURNEYS]

print(f"\n🏆 USER: {USERNAME}")
print(f"TURNIERE: {len(selected_tourneys)}\n")

# =========================
# 📊 DATA
# =========================

points = defaultdict(float)
player_tournament_participation = defaultdict(set)

# =========================
# 🔎 2. TURNIERE DURCHGEHEN
# =========================

for t in selected_tourneys:

    tid = t["id"]

    print("\n" + "=" * 55)
    print(f"🏆 {t.get('fullName')}")
    print(f"🔗 https://lichess.org/tournament/{tid}")
    print("=" * 55)

    # =========================
    # 🔵 OFFICIAL RESULTS (WICHTIG!)
    # =========================

    results_url = f"https://lichess.org/api/tournament/{tid}/results"
    r_response = requests.get(results_url, headers=headers)

    if r_response.status_code != 200:
        continue

    for line in r_response.text.splitlines():
        if not line.strip():
            continue

        data = json.loads(line)

        username = data.get("username")
        score = data.get("score", 0)

        if not username:
            continue

        user = username.lower()

        points[user] += float(score)
        player_tournament_participation[user].add(tid)


# =========================
# 🏆 FINAL RANKING
# =========================

sorted_players = sorted(points.items(), key=lambda x: x[1], reverse=True)

print("\n" + "=" * 60)
print("🏆 FINAL RANKING (OFFICIAL LICHESS SCORE)")
print("=" * 60 + "\n")

total_tournaments = len(selected_tourneys)

for i, (user, score) in enumerate(sorted_players, 1):

    played = len(player_tournament_participation[user])

    print(f"{i}. {user}: {score:.1f} points ({played}/{total_tournaments})")
