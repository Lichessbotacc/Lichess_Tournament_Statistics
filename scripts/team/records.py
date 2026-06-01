import requests
import json
from collections import defaultdict
from datetime import datetime

USERNAME = "DarkOnCrack"

KEYWORD = "Solo Rapid"
MIN_PLAYERS = 0
SINCE_YEAR = 0

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# 🔹 LOAD TOURNAMENTS (DEIN STYLE)
# =========================

tournament_list = []

url = f"https://lichess.org/api/user/{USERNAME}/tournament/created"
response = requests.get(url, headers=headers, stream=True)

for line in response.iter_lines():
    if not line:
        continue

    t = json.loads(line)

    name = t.get("fullName", "").lower()
    nb_players = t.get("nbPlayers", 0)
    created = t.get("created")

    year = datetime.utcfromtimestamp(created / 1000).year if created else 0

    if KEYWORD and KEYWORD.lower() not in name:
        continue
    if MIN_PLAYERS and nb_players < MIN_PLAYERS:
        continue
    if SINCE_YEAR and year < SINCE_YEAR:
        continue

    tid = t["id"]
    tournament_list.append((tid, t.get("fullName", "Unknown")))

# =========================
# 🏆 WORLD RECORD LOGIC
# =========================

world_record = {
    "team": None,
    "score": -1,
    "tournament": None,
    "url": None
}

# =========================
# 🔹 ANALYSE ALL TEAM BATTLES
# =========================

for tid, name in tournament_list:

    url = f"https://lichess.org/api/tournament/{tid}/games"
    response = requests.get(url, headers=headers, stream=True)

    if response.status_code != 200:
        continue

    team_scores = defaultdict(int)

    for line in response.iter_lines():
        if not line:
            continue

        game = json.loads(line)

        try:
            white = game["players"]["white"]["user"]["name"]
            black = game["players"]["black"]["user"]["name"]
            winner = game.get("winner")
        except:
            continue

        # =========================
        # TEAM NAME FALLBACK
        # =========================
        white_team = game["players"]["white"]["user"].get("team", white)
        black_team = game["players"]["black"]["user"].get("team", black)

        # =========================
        # SCORE SYSTEM
        # =========================
        if winner == "white":
            team_scores[white_team] += 2
        elif winner == "black":
            team_scores[black_team] += 2
        else:
            team_scores[white_team] += 1
            team_scores[black_team] += 1

    if not team_scores:
        continue

    best_team, best_score = max(team_scores.items(), key=lambda x: x[1])

    # =========================
    # 🏆 WORLD RECORD CHECK
    # =========================
    if best_score > world_record["score"]:
        world_record = {
            "team": best_team,
            "score": best_score,
            "tournament": name,
            "url": f"https://lichess.org/tournament/{tid}"
        }

# =========================
# 🔥 OUTPUT
# =========================

if world_record["team"] is None:
    print("❌ Kein Team Battle Rekord gefunden.")
    exit()

print("\n" + "=" * 60)
print("🏆 TEAM WORLD RECORD (MOST POINTS IN A TOURNAMENT)")
print("=" * 60)

print(f"Team        : {world_record['team']}")
print(f"Score       : {world_record['score']}")
print(f"Tournament  : {world_record['tournament']}")
print(f"Link        : {world_record['url']}")
