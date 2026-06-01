import requests
import json
from collections import defaultdict
from datetime import datetime

USERNAME = "DarkOnCrack"

KEYWORD = "Ultrabullet"

headers = {
    "Accept": "application/x-ndjson"
}

# =========================
# 🔹 LOAD TOURNAMENTS (DEIN CODE FIXED BLEIBT)
# =========================

tournament_list = []

url = f"https://lichess.org/api/user/{USERNAME}/tournament/created"
response = requests.get(url, headers=headers, stream=True)

for line in response.iter_lines():
    if not line:
        continue

    t = json.loads(line)

    name = t.get("fullName", "")
    created = t.get("created", 0)

    if KEYWORD and KEYWORD.lower() not in name.lower():
        continue

    tid = t["id"]
    tournament_list.append((tid, name))


# =========================
# 🏆 GLOBAL WORLD RECORD LIST
# =========================

world_records = []

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
            white_user = game["players"]["white"]["user"]["name"]
            black_user = game["players"]["black"]["user"]["name"]
            winner = game.get("winner")
        except:
            continue

        # ⚡ TEAM IDENTIFICATION (Lichess standard field)
        white_team = game["players"]["white"]["user"].get("team", white_user)
        black_team = game["players"]["black"]["user"].get("team", black_user)

        # =========================
        # SCORE SYSTEM (REALISTIC)
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

    # 🏆 BEST TEAM IN THIS TOURNAMENT
    best_team, best_score = max(team_scores.items(), key=lambda x: x[1])

    world_records.append({
        "team": best_team,
        "score": best_score,
        "tournament": name,
        "url": f"https://lichess.org/tournament/{tid}"
    })


# =========================
# 🔥 GLOBAL TOP 5 WORLD RECORDS
# =========================

world_records.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 60)
print("🏆 TOP 5 TEAM WORLD RECORDS (ALL TOURNAMENTS)")
print("=" * 60)

for i, r in enumerate(world_records[:5], 1):
    print(f"\n{i}. TEAM: {r['team']}")
    print(f"   SCORE: {r['score']}")
    print(f"   TOURNAMENT: {r['tournament']}")
    print(f"   LINK: {r['url']}")
