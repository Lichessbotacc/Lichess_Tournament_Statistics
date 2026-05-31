#!/usr/bin/env python3
import requests
import re
import json
from collections import defaultdict

# =====================================

# CONFIG

# =====================================

CREATOR = "ajedrezconzeta"
KEYWORD = "Teamkampf"      # "" = alle
TOP_N = 10

# =====================================

# LOAD TOURNAMENT PAGE

# =====================================

url = f"https://lichess.org/@/{CREATOR}/tournaments/created"

r = requests.get(url)

if r.status_code != 200:
print("Fehler beim Laden der Creator-Seite")
exit()

html = r.text

# =====================================

# EXTRACT TOURNAMENT IDS

# =====================================

tournament_ids = sorted(
set(re.findall(r"/tournament/([A-Za-z0-9]{8})", html))
)

print(f"Gefundene Turniere: {len(tournament_ids)}")

# =====================================

# PROCESS TOURNAMENTS

# =====================================

records = []

headers = {
"Accept": "application/x-ndjson"
}

for tid in tournament_ids:

```
tournament_url = f"https://lichess.org/tournament/{tid}"

page = requests.get(tournament_url)

if page.status_code != 200:
    continue

page_html = page.text

if KEYWORD and KEYWORD.lower() not in page_html.lower():
    continue

print(f"Scanne {tid}")

results_url = f"https://lichess.org/api/tournament/{tid}/results"

rr = requests.get(results_url, headers=headers)

if rr.status_code != 200:
    continue

team_scores = defaultdict(int)

for line in rr.text.splitlines():

    if not line.strip():
        continue

    try:
        data = json.loads(line)
    except:
        continue

    team = data.get("team")
    score = data.get("score", 0)

    if team:
        team_scores[team] += score

if not team_scores:
    continue

best_team, best_score = max(
    team_scores.items(),
    key=lambda x: x[1]
)

records.append({
    "team": best_team,
    "score": best_score,
    "id": tid,
    "url": f"https://lichess.org/tournament/{tid}"
})
```

# =====================================

# WORLD RECORD

# =====================================

if not records:
print("Keine Teamdaten gefunden.")
exit()

records.sort(key=lambda x: x["score"], reverse=True)

world_record = records[0]

print("\n" + "=" * 60)
print("TEAM WORLD RECORD")
print("=" * 60)

print(f"Team : {world_record['team']}")
print(f"Score: {world_record['score']}")
print(f"Link : {world_record['url']}")

print("\nTOP TURNIERE\n")

for i, r in enumerate(records[:TOP_N], 1):
print(
f"{i}. {r['team']} - {r['score']} pts\n"
f"   {r['url']}"
)
