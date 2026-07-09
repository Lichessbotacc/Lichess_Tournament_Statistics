#!/usr/bin/env python3
"""
most_active_blitz_players.py

Findet moeglichst viele AKTIVE Lichess-Blitz-Spieler (nicht nur die
staerksten nach Rating) und baut daraus ein "Wer hat in den letzten
7 Tagen die meisten Blitz-Partien gespielt"-Ranking (Top 100).

Gedacht fuer einen GitHub-Action-Cron-Trigger alle 6 Stunden (siehe
.github/workflows/blitz-activity.yml), nicht als Dauer-Loop.

-------------------------------------------------------------------
WIE DER SPIELER-POOL WAECHST
-------------------------------------------------------------------
Lichess hat keine oeffentliche API, die "alle aktiven Spieler" auflistet.
Stattdessen sammelt dieses Skript den Pool aus mehreren Quellen und
SPEICHERT ihn dauerhaft in KNOWN_PLAYERS_FILE - der Pool waechst also mit
jedem Lauf weiter:

  1. Top-200 Blitz-Spieler nach Rating (/api/player/top/200/blitz).
  2. Teilnehmer aus allen aktuell sichtbaren offiziellen Blitz-Arenen
     (/api/tournament -> created/started/finished, gefiltert auf
     perf == "blitz"), jeweils ALLE Teilnehmer via
     /api/tournament/{id}/results (nicht nur die Top-Platzierten).
  3. Optional: Mitglieder aus selbst konfigurierten Teams (EXTRA_TEAM_IDS
     unten), z.B. deine eigenen DarkOn-Teams oder andere grosse
     Blitz-Communities.

Da alle 6 Stunden neue/andere Turniere sichtbar sind, sammelt sich der
Pool ueber Tage/Wochen zu vielen Tausend erfassten aktiven Spielern an -
weit mehr als nur die 200 staerksten nach Rating.

-------------------------------------------------------------------
KONFIGURATION
-------------------------------------------------------------------
LICHESS_TOKEN als Umgebungsvariable/GitHub Secret setzen (ein Token ohne
besondere Scopes reicht fuer alle hier genutzten oeffentlichen Endpunkte,
erhoeht aber das Rate-Limit gegenueber unauthentifizierten Anfragen).

EXTRA_TEAM_IDS: Liste zusaetzlicher Team-Slugs, deren Mitglieder ebenfalls
in den Pool aufgenommen werden sollen (optional, kann leer bleiben).

SINCE_DAYS: Zeitraum in Tagen, ueber den Blitz-Partien gezaehlt werden
(Standard: 7 = letzte Woche).

MAX_GAMES_PER_QUERY: Obergrenze, wie viele Partien pro Spieler maximal
gezaehlt werden (Deckel gegen Ausreisser mit zehntausenden Partien pro
Woche und gegen zu lange Laufzeiten). 1000 ist grosszuegig - realistisch
spielt niemand mehr als ca. 1000 Blitz-Partien in 7 Tagen.

REQUEST_DELAY_SECONDS: Pause zwischen einzelnen API-Aufrufen, um das
Lichess-Rate-Limit nicht zu reissen.

Sobald Lichess mit HTTP 429 antwortet, bricht das Skript SOFORT ab (kein
Retry innerhalb des Laufs), speichert aber vorher alles bisher Ermittelte.
Der naechste geplante Lauf (z.B. in 6 Stunden) macht dort weiter, wo
aufgehoert wurde.

Ausfuehren (einmaliger Durchlauf):
    python3 most_active_blitz_players.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Python puffert print()-Ausgaben, wenn stdout kein echtes Terminal ist
# (z.B. in GitHub Actions) - dadurch wirken Ausgaben nicht "live", sondern
# kommen erst gebuendelt am Ende an. Fix: stdout auf Line-Buffering
# umstellen, damit jede Zeile sofort ausgegeben wird.
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("LICHESS_TOKEN", "")

# Zusaetzliche Teams, deren Mitglieder ebenfalls in den Spieler-Pool
# aufgenommen werden sollen (Team-Slugs, klein geschrieben). Kann leer sein.
EXTRA_TEAM_IDS = [
     "darkonblitz-dob",
     "darkonteams",
]

SINCE_DAYS = 7
MAX_GAMES_PER_QUERY = 1000
TOP_N = 100
REQUEST_DELAY_SECONDS = 1.0

KNOWN_PLAYERS_FILE = Path("known_players.json")
LEADERBOARD_FILE = Path("blitz_leaderboard.json")

BASE_URL = "https://lichess.org"
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
NDJSON_HEADERS = {**HEADERS, "Accept": "application/x-ndjson"}


class RateLimitError(Exception):
    """Wird ausgeloest, wenn Lichess mit HTTP 429 antwortet."""


# ---------------------------------------------------------------------------
# HTTP HELPERS
# ---------------------------------------------------------------------------
def _request(url: str, headers: dict, timeout: int = 30):
    req = urllib.request.Request(url, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RateLimitError(f"Rate Limit bei {url}") from exc
        raise


def fetch_json(url: str) -> dict:
    with _request(url, HEADERS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_ndjson(url: str, headers: dict = None):
    """Generator: liest eine ndjson-Antwort Zeile fuer Zeile."""
    with _request(url, headers or NDJSON_HEADERS, timeout=60) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            yield json.loads(line)


# ---------------------------------------------------------------------------
# SPIELER-POOL SAMMELN
# ---------------------------------------------------------------------------
def load_known_players() -> set:
    if KNOWN_PLAYERS_FILE.exists():
        try:
            data = json.loads(KNOWN_PLAYERS_FILE.read_text())
            if isinstance(data, list):
                return set(data)
        except (json.JSONDecodeError, OSError):
            pass
    return set()


def save_known_players(players: set) -> None:
    KNOWN_PLAYERS_FILE.write_text(json.dumps(sorted(players), indent=2))


def get_top_blitz_players() -> set:
    print("Hole Top-200 Blitz-Spieler nach Rating...")
    try:
        data = fetch_json(f"{BASE_URL}/api/player/top/200/blitz")
        users = {u["username"].lower() for u in data.get("users", [])}
        print(f"  {len(users)} Spieler aus Top-Liste.")
        return users
    except (RateLimitError, urllib.error.URLError, urllib.error.HTTPError, KeyError) as exc:
        print(f"  [WARNUNG] Top-Liste konnte nicht geladen werden: {exc}")
        return set()


def get_visible_blitz_tournament_ids() -> list:
    """
    Holt aktuell sichtbare offizielle Turniere (erstellt/laufend/kuerzlich
    beendet) und filtert auf Blitz. Liefert Liste von Turnier-IDs.
    """
    print("Suche aktuell sichtbare Blitz-Arenen...")
    try:
        data = fetch_json(f"{BASE_URL}/api/tournament")
    except (RateLimitError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"  [WARNUNG] Turnierliste konnte nicht geladen werden: {exc}")
        return []

    ids = []
    for bucket in ("finished", "started", "created"):
        for t in data.get(bucket, []):
            perf = t.get("perf", {})
            perf_key = perf.get("key") if isinstance(perf, dict) else None
            if perf_key == "blitz" and t.get("id"):
                ids.append(t["id"])

    print(f"  {len(ids)} Blitz-Arena(n) gefunden.")
    return ids


def get_tournament_participants(tournament_id: str) -> set:
    """Alle Teilnehmer eines Turniers (nicht nur Top-Platzierte)."""
    url = f"{BASE_URL}/api/tournament/{tournament_id}/results?sheet=false"
    users = set()
    try:
        for row in fetch_ndjson(url):
            name = row.get("username")
            if name:
                users.add(name.lower())
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"  [WARNUNG] Teilnehmer von Turnier {tournament_id} nicht ladbar: {exc}")
    return users


def get_team_members(team_id: str) -> set:
    print(f"Hole Mitglieder von Team '{team_id}'...")
    url = f"{BASE_URL}/api/team/{team_id}/users"
    users = set()
    try:
        for row in fetch_ndjson(url):
            name = row.get("username") or row.get("id")
            if name:
                users.add(name.lower())
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"  [WARNUNG] Mitglieder von Team '{team_id}' nicht ladbar: {exc}")
    print(f"  {len(users)} Mitglieder gefunden.")
    return users


def build_player_pool(known_players: set) -> set:
    """
    Erweitert known_players um neu gefundene Spieler aus allen Quellen.
    Gibt die (erweiterte) Gesamtmenge zurueck.
    """
    pool = set(known_players)

    pool |= get_top_blitz_players()
    time.sleep(REQUEST_DELAY_SECONDS)

    tournament_ids = get_visible_blitz_tournament_ids()
    for t_id in tournament_ids:
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            participants = get_tournament_participants(t_id)
        except RateLimitError as exc:
            print(f"[RATE LIMIT] {exc} - Pool-Sammlung wird an dieser Stelle beendet.")
            return pool
        new_count = len(participants - pool)
        pool |= participants
        if new_count:
            print(f"  Turnier {t_id}: {len(participants)} Teilnehmer "
                  f"({new_count} davon neu im Pool).")

    for team_id in EXTRA_TEAM_IDS:
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            pool |= get_team_members(team_id.lower())
        except RateLimitError as exc:
            print(f"[RATE LIMIT] {exc} - Pool-Sammlung wird an dieser Stelle beendet.")
            return pool

    return pool


# ---------------------------------------------------------------------------
# PARTIEN ZAEHLEN
# ---------------------------------------------------------------------------
def count_recent_blitz_games(username: str, since_ms: int) -> int:
    """Zaehlt Blitz-Partien eines Spielers seit since_ms (gedeckelt)."""
    params = urllib.parse.urlencode({
        "since": since_ms,
        "perfType": "blitz",
        "max": MAX_GAMES_PER_QUERY,
        "moves": "false",
        "tags": "false",
        "opening": "false",
        "clocks": "false",
        "evals": "false",
    })
    url = f"{BASE_URL}/api/games/user/{username}?{params}"
    count = 0
    for _ in fetch_ndjson(url):
        count += 1
    return count


# ---------------------------------------------------------------------------
# LEADERBOARD / "LIVE"-ANZEIGE
# ---------------------------------------------------------------------------
def load_leaderboard() -> dict:
    if LEADERBOARD_FILE.exists():
        try:
            data = json.loads(LEADERBOARD_FILE.read_text())
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"updated_at": None, "counts": {}}


def save_leaderboard(leaderboard: dict) -> None:
    LEADERBOARD_FILE.write_text(json.dumps(leaderboard, indent=2, sort_keys=True))


def profile_url(username: str) -> str:
    return f"{BASE_URL}/@/{username}"


def print_top(counts: dict, n: int = TOP_N) -> list:
    ranking = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]
    print()
    print("=" * 70)
    print(f"  TOP {n} AKTIVSTE BLITZ-SPIELER (letzte {SINCE_DAYS} Tage)")
    print("=" * 70)
    for i, (name, cnt) in enumerate(ranking, start=1):
        print(f"  {i:>3}. {name:<20} {cnt:>5} Partien   {profile_url(name)}")
    print("=" * 70)
    return ranking


def flashy_new_entry_banner(rank: int, name: str, count: int) -> None:
    print()
    print("  " + "*" * 60)
    if rank <= 3:
        print(f"  *** NEUER TOP-{rank}!! {name.upper()} MIT {count} PARTIEN! ***")
    elif rank <= 10:
        print(f"  *** NEU IN DEN TOP 10: {name} ({count} Partien)! ***")
    else:
        print(f"  * Neu in Top {TOP_N}: {name} ({count} Partien) - Platz {rank}")
    print(f"  -> {profile_url(name)}")
    print("  " + "*" * 60)


def get_current_rank(name: str, counts: dict) -> int:
    ranking = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    for i, (n, _c) in enumerate(ranking, start=1):
        if n == name:
            return i
    return -1


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    if not TOKEN:
        print("Hinweis: Kein LICHESS_TOKEN gesetzt - es wird unauthentifiziert "
              "abgefragt (niedrigeres Rate-Limit). Fuer bessere Performance "
              "LICHESS_TOKEN als Umgebungsvariable/Secret setzen.")

    known_players = load_known_players()
    print(f"Bereits bekannte Spieler im Pool: {len(known_players)}")
    print("=" * 70)

    pool = build_player_pool(known_players)
    new_players = len(pool - known_players)
    print()
    print(f"Spieler-Pool nach dieser Sammelrunde: {len(pool)} "
          f"({new_players} neu hinzugekommen).")
    save_known_players(pool)

    leaderboard = load_leaderboard()
    counts = leaderboard.get("counts", {})

    since_ms = int((datetime.now(timezone.utc) - timedelta(days=SINCE_DAYS)).timestamp() * 1000)

    print()
    print(f"Zaehle Blitz-Partien der letzten {SINCE_DAYS} Tage fuer "
          f"{len(pool)} Spieler...")
    print("=" * 70)

    processed = 0
    for username in sorted(pool):
        try:
            time.sleep(REQUEST_DELAY_SECONDS)
            new_count = count_recent_blitz_games(username, since_ms)
        except RateLimitError as exc:
            print(f"[RATE LIMIT] {exc}")
            print("Breche Skript sofort ab und speichere den bisherigen Stand. "
                  "Naechster Lauf macht hier weiter (z.B. in 6 Stunden).")
            leaderboard["counts"] = counts
            leaderboard["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_leaderboard(leaderboard)
            print_top(counts)
            return
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f"  [WARNUNG] '{username}' konnte nicht abgefragt werden: {exc}")
            continue

        old_count = counts.get(username)
        counts[username] = new_count
        processed += 1

        # "Live"-Reaktion: pruefen, ob der Spieler mit dem neuen Wert
        # (erstmals oder neu) in die Top-N aufsteigt - falls ja, sofort
        # auffaelligen Banner anzeigen, ohne auf das Laufende zu warten.
        if new_count > 0 and (old_count is None or new_count != old_count):
            rank = get_current_rank(username, counts)
            if 0 < rank <= TOP_N:
                flashy_new_entry_banner(rank, username, new_count)

        if processed % 25 == 0:
            print(f"  ... {processed}/{len(pool)} Spieler verarbeitet.")

    leaderboard["counts"] = counts
    leaderboard["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_leaderboard(leaderboard)

    print_top(counts)
    print()
    print(f"Fertig. {processed} Spieler in diesem Lauf abgefragt, "
          f"{len(counts)} Spieler insgesamt im Leaderboard.")


if __name__ == "__main__":
    main()
