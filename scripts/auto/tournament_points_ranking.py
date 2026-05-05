import requests
import json
from collections import defaultdict

TEAM_ID = "darkonclassical"   # <- hier dein Team eintragen
MAX_TOURNEYS = 1
TOURNEY_KEYWORD = "rapid"

DEBUG = True

headers = {
    "Accept": "application/x-ndjson"
}

# 🔎 1. Turniere holen
url = f"https://lichess.org/api/team/{TEAM_ID}/arena?status=finished"
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Fehler beim Laden der Turniere")
    exit()

tournaments = [
    json.loads(line)
    for line in response.text.splitlines()
    if line.strip()
]

# 🔥 Filter
filtered = [
    t for t in tournaments
    if TOURNEY_KEYWORD.lower() in t["fullName"].lower()
]

selected_tourneys = filtered[:MAX_TOURNEYS]

print(f"\n🏆 POINTS RANKING – Team: {TEAM_ID}")
print(f"Turniere: {len(selected_tourneys)} | Filter: {TOURNEY_KEYWORD}\n")

points = defaultdict(int)

# 🔎 2. Turniere durchgehen
for t in selected_tourneys:
    tourney_id = t["id"]
    print(f"\n=== {t['fullName']} ===")
    print(f"https://lichess.org/tournament/{tourney_id}")

    # 🟢 STEP 1: Team-Spieler sammeln (Games)
    team_players = set()

    games_url = f"https://lichess.org/api/tournament/{tourney_id}/games"
    g_response = requests.get(games_url, headers=headers, stream=True)

    if g_response.status_code != 200:
        print("Fehler bei Games")
        continue

    for line in g_response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        white = game["players"]["white"]
        black = game["players"]["black"]

        white_user = white.get("user", {}).get("name")
        black_user = black.get("user", {}).get("name")

        white_team = white.get("team")
        black_team = black.get("team")

        # ⚠️ nur echte Team-Zuordnung (kein None mehr!)
        if white_user and white_team == TEAM_ID:
            team_players.add(white_user.lower())

        if black_user and black_team == TEAM_ID:
            team_players.add(black_user.lower())

    # 🔥 FALLBACK (wichtig!)
    if len(team_players) == 0:
        if DEBUG:
            print("⚠️ Kein Team-Feld gefunden → Fallback: alle Spieler zählen")
        fallback_all = True
    else:
        fallback_all = False

    print(f"Team-Spieler erkannt: {len(team_players)}")

    # 🔵 STEP 2: Arena Results holen
    results_url = f"https://lichess.org/api/tournament/{tourney_id}/results"
    r_response = requests.get(results_url, headers=headers)

    if r_response.status_code != 200:
        print("Fehler bei Results")
        continue

    matched = 0
    ignored = 0
    total = 0

    for line in r_response.text.splitlines():
        if not line.strip():
            continue

        data = json.loads(line)

        username = data.get("username")
        score = data.get("score", 0)

        if not username:
            continue

        user = username.lower()

        # ✅ LOGIC
        if fallback_all or user in team_players:
            points[user] += score
            matched += 1
            total += score
        else:
            ignored += 1
            if DEBUG:
                print(f"IGNORED: {username} ({score})")

    print(f"Matched: {matched} | Ignored: {ignored} | Points: {total}")

# 🔎 3. Sortieren
sorted_players = sorted(points.items(), key=lambda x: x[1], reverse=True)

# 🏆 4. Output
print("\n🏆 FINAL POINTS RANKING:\n")

for i, (user, score) in enumerate(sorted_players, 1):
    print(f"{i}. {user}: {score} points")
