import requests
import json
import time
from collections import defaultdict

# 🔥 SETTINGS
TARGET_TEAM = "darkonteams"
TOURNEY_IDS = ["cWTnOS4Q", "4DzfnhBJ", "qEm4TOdC", "SmRc33Eo", "rDDxmCDh", "kqszcf5M", "BzQpoZmF", "ll7DaWIj"]
REQUEST_DELAY = 1.0   # Sekunden Pause zwischen Requests (Rate-Limit-Schutz)
MAX_RETRIES = 3

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "lichess-team-analyzer"
})


def get_with_retry(url, retries=MAX_RETRIES):
    """GET-Request mit Retry-Logik für 429/5xx Fehler."""
    for attempt in range(1, retries + 1):
        r = session.get(url, stream=True)
        if r.status_code == 200:
            return r
        if r.status_code == 429:
            wait = 5 * attempt
            print(f"⏳ Rate-Limit erreicht, warte {wait}s ... (Versuch {attempt}/{retries})")
            time.sleep(wait)
            continue
        if 500 <= r.status_code < 600:
            print(f"⚠️ Serverfehler {r.status_code}, erneuter Versuch ({attempt}/{retries})")
            time.sleep(2 * attempt)
            continue
        # Anderer Fehler (z.B. 404) -> kein Retry sinnvoll
        return r
    return r  # letzter Versuch, egal wie er ausging


def iter_ndjson(response):
    """Robustes Parsen von NDJSON-Zeilen, ignoriert leere/kaputte Zeilen."""
    for line in response.iter_lines():
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


# -----------------------------------------
# TEAM LADEN (NDJSON SAFE)
# -----------------------------------------
print(f"📥 Lade Team: {TARGET_TEAM}")
# key = lowercase username -> value = "richtige" Original-Schreibweise
team_members = {}

url = f"https://lichess.org/api/team/{TARGET_TEAM}/users"
r = get_with_retry(url)
if r.status_code != 200:
    print("❌ Fehler beim Laden des Teams:", r.status_code)
    print(r.text[:200])
    exit()

for user in iter_ndjson(r):
    name = user.get("name") or user.get("username") or user.get("id")
    if name:
        team_members[name.lower()] = name

print(f"✅ Teammitglieder geladen: {len(team_members)}")

time.sleep(REQUEST_DELAY)

# -----------------------------------------
# TURNIERE AUSWERTEN (NDJSON SAFE)
# -----------------------------------------
# key = lowercase username -> Summe der Punkte
points = defaultdict(int)
# key = lowercase username -> Anzahl Turniere, in denen gewertet wurde
tournaments_played = defaultdict(int)
# key = lowercase username -> "richtige" Anzeige-Schreibweise (aus den Ergebnissen selbst)
display_name = {}

for idx, tid in enumerate(TOURNEY_IDS, 1):
    print(f"\n📊 Turnier ({idx}/{len(TOURNEY_IDS)}): {tid}")
    url = f"https://lichess.org/api/tournament/{tid}/results"
    r = get_with_retry(url)

    if r.status_code != 200:
        print(f"❌ Fehler bei Turnier {tid}: {r.status_code}")
        time.sleep(REQUEST_DELAY)
        continue

    found_in_this_tourney = 0
    for player in iter_ndjson(r):
        username = player.get("username")
        score = player.get("score", 0)
        played_for_team = player.get("team")  # nur bei Team-Battle-Turnieren gesetzt
        if not username:
            continue

        key = username.lower()

        if played_for_team is not None:
            # 🔥 Team-Battle-Turnier: nur zählen, wenn er FÜR dieses Team gespielt hat
            if played_for_team.lower() != TARGET_TEAM.lower():
                continue
        else:
            # 🔥 Normales Arena-Turnier: nur über aktuelle Team-Mitgliedschaft filtern
            if key not in team_members:
                continue

        print(f"  {username} +{score}" + (f"  [team: {played_for_team}]" if played_for_team else ""))
        points[key] += score
        tournaments_played[key] += 1
        display_name[key] = username  # Original-Schreibweise aus den Turnierdaten
        found_in_this_tourney += 1

    if found_in_this_tourney == 0:
        print("  (keine Teammitglieder in diesem Turnier gefunden)")

    time.sleep(REQUEST_DELAY)  # Rate-Limit-Schutz zwischen Turnieren

# -----------------------------------------
# RANKING
# -----------------------------------------
ranking = sorted(points.items(), key=lambda x: x[1], reverse=True)

print(f"\n🏆 {TARGET_TEAM.upper()} RANKING\n")
if not ranking:
    print("Keine Daten gefunden.")
else:
    for i, (key, score) in enumerate(ranking, 1):
        name = display_name.get(key, team_members.get(key, key))
        n_tourneys = tournaments_played[key]
        print(f"{i}. {name}: {score} Punkte  ({n_tourneys} Turnier{'e' if n_tourneys != 1 else ''})")
