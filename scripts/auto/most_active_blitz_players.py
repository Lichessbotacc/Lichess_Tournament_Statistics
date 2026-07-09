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
  2. Teilnehmer aus ALLEN erreichbaren Blitz-Arenen:
       a) aktuell sichtbare offizielle Turniere
          (/api/tournament -> created/started/finished, gefiltert auf
          perf == "blitz"),
       b) zusaetzlich Arena- UND Swiss-Turniere, die von den
          EXTRA_TEAM_IDS-Teams erstellt wurden - inklusive VERGANGENER
          Turniere (/api/team/{id}/arena und /api/team/{id}/swiss).
          Das ist wichtig, weil /api/tournament nur eine Momentaufnahme
          der GERADE sichtbaren Turniere zeigt, waehrend die Team-Endpunkte
          auch laengst beendete Turniere zurueckgeben. So werden ueber die
          Zeit deutlich mehr Turniere erfasst als nur die paar, die zum
          Zeitpunkt des Laufs zufaellig sichtbar sind.
     Jeweils ALLE Teilnehmer via /api/tournament/{id}/results bzw.
     /api/swiss/{id}/results (nicht nur die Top-Platzierten).
  3. Optional: Mitglieder aus selbst konfigurierten Teams (EXTRA_TEAM_IDS
     unten), z.B. deine eigenen DarkOn-Teams oder andere grosse
     Blitz-Communities.

Da alle 6 Stunden neue/andere Turniere sichtbar sind und zusaetzlich die
komplette Team-Turnierhistorie durchsucht wird, sammelt sich der Pool
ueber Tage/Wochen zu vielen Tausend erfassten aktiven Spielern an - weit
mehr als nur die 200 staerksten nach Rating.

-------------------------------------------------------------------
LIVE-RANKING WAEHREND DER SUCHE
-------------------------------------------------------------------
Das Skript wartet NICHT, bis der komplette Spieler-Pool gesammelt ist,
bevor es Partien zaehlt. Stattdessen wird JEDE Quelle (Top-Liste, jedes
einzelne Turnier, jedes Team) sofort nach dem Einlesen verarbeitet:
neu gefundene bzw. noch nicht in dieser Laufzeit aktualisierte Spieler
werden direkt danach auf ihre Blitz-Partien-Zahl der letzten SINCE_DAYS
Tage geprueft, das Leaderboard wird sofort aktualisiert und bei einem
Top-100-Einstieg erscheint sofort ein auffaelliger Banner - man muss
also nicht auf das Ende des gesamten Laufs warten, um zu sehen, wer
gerade aktiv ist.

-------------------------------------------------------------------
KONFIGURATION
-------------------------------------------------------------------
LICHESS_TOKEN als Umgebungsvariable/GitHub Secret setzen (ein Token ohne
besondere Scopes reicht fuer alle hier genutzten oeffentlichen Endpunkte,
erhoeht aber das Rate-Limit gegenueber unauthentifizierten Anfragen).

EXTRA_TEAM_IDS: Liste zusaetzlicher Team-Slugs. Deren Mitglieder werden
in den Pool aufgenommen UND deren komplette Arena-/Swiss-Turnierhistorie
(auch vergangene Turniere!) wird nach Blitz-Turnieren durchsucht.

SINCE_DAYS: Zeitraum in Tagen, ueber den Blitz-Partien gezaehlt werden
(Standard: 7 = letzte Woche).

MAX_GAMES_PER_QUERY: Obergrenze, wie viele Partien pro Spieler maximal
gezaehlt werden (Deckel gegen Ausreisser mit zehntausenden Partien pro
Woche und gegen zu lange Laufzeiten). 1000 ist grosszuegig - realistisch
spielt niemand mehr als ca. 1000 Blitz-Partien in 7 Tagen.

MAX_TEAM_TOURNAMENTS: Obergrenze, wie viele vergangene Turniere pro Team
und Turniertyp (Arena/Swiss) maximal abgefragt werden.

REQUEST_DELAY_SECONDS: Pause zwischen einzelnen API-Aufrufen, um das
Lichess-Rate-Limit nicht zu reissen.

Sobald Lichess mit HTTP 429 antwortet, bricht das Skript SOFORT ab (kein
Retry innerhalb des Laufs), speichert aber vorher alles bisher Ermittelte
(Pool UND Leaderboard-Stand). Der naechste geplante Lauf (z.B. in 6
Stunden) macht dort weiter, wo aufgehoert wurde.

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
MAX_TEAM_TOURNAMENTS = 100

KNOWN_PLAYERS_FILE = Path("known_players.json")
LEADERBOARD_FILE = Path("blitz_leaderboard.json")
KNOWN_TOURNAMENTS_FILE = Path("known_tournaments.json")

# Eigener Ordner fuer den "immer aktuellen" Top-10-Schnappschuss. Diese
# Dateien werden bei JEDEM einzelnen Live-Update ueberschrieben, sodass
# man dort jederzeit (auch waehrend das Skript noch laeuft) den aktuellen
# Stand sehen kann - unabhaengig von der Konsolen-/Log-Ausgabe, die z.B.
# in GitHub Actions nach dem Lauf schnell unuebersichtlich wird.
STATUS_DIR = Path("status")
TOP10_JSON_FILE = STATUS_DIR / "top100.json"
TOP10_MD_FILE = STATUS_DIR / "top100.md"
TOP_N_LIVE = 100

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
# PERSISTENZ
# ---------------------------------------------------------------------------
def load_json_set(path: Path) -> set:
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, list):
                return set(data)
        except (json.JSONDecodeError, OSError):
            pass
    return set()


def save_json_set(path: Path, values: set) -> None:
    path.write_text(json.dumps(sorted(values), indent=2))


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


# ---------------------------------------------------------------------------
# TURNIERE FINDEN (aktuell sichtbar + Team-Historie, NUR Blitz)
# ---------------------------------------------------------------------------
def get_visible_blitz_tournament_ids() -> list:
    """
    Holt aktuell sichtbare offizielle Turniere (erstellt/laufend/kuerzlich
    beendet) und filtert auf Blitz. Liefert Liste von (id, "arena")-Tupeln.
    Das ist nur eine Momentaufnahme - siehe get_team_tournament_ids fuer
    zusaetzliche, auch vergangene Turniere.
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
                ids.append((t["id"], "arena"))

    print(f"  {len(ids)} Blitz-Arena(n) gefunden.")
    return ids


def get_team_tournament_ids(team_id: str) -> list:
    """
    Holt die komplette Arena- UND Swiss-Turnierhistorie eines Teams
    (auch VERGANGENE, bereits laengst beendete Turniere - anders als
    /api/tournament, das nur die aktuelle Momentaufnahme zeigt) und
    filtert auf Blitz. Liefert Liste von (id, "arena"/"swiss")-Tupeln.
    """
    found = []

    # Arena-Turniere des Teams
    url = f"{BASE_URL}/api/team/{team_id}/arena?max={MAX_TEAM_TOURNAMENTS}"
    try:
        for row in fetch_ndjson(url):
            perf = row.get("perf", {})
            perf_key = perf.get("key") if isinstance(perf, dict) else None
            if perf_key == "blitz" and row.get("id"):
                found.append((row["id"], "arena"))
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"  [WARNUNG] Arena-Historie von Team '{team_id}' nicht ladbar: {exc}")

    # Swiss-Turniere des Teams
    url = f"{BASE_URL}/api/team/{team_id}/swiss?max={MAX_TEAM_TOURNAMENTS}"
    try:
        for row in fetch_ndjson(url):
            variant = row.get("variant", {})
            variant_key = variant.get("key") if isinstance(variant, dict) else None
            clock = row.get("clock", {})
            # Swiss-Turniere haben kein "perf"-Feld wie Arenen, aber ueber
            # die Bedenkzeit laesst sich Blitz (3-8min als Basiszeit)
            # identifizieren; zur Sicherheit zusaetzlich variant == standard.
            limit = clock.get("limit", 0) if isinstance(clock, dict) else 0
            is_blitz_clock = 180 <= limit <= 480
            if variant_key == "standard" and is_blitz_clock and row.get("id"):
                found.append((row["id"], "swiss"))
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"  [WARNUNG] Swiss-Historie von Team '{team_id}' nicht ladbar: {exc}")

    return found


def get_tournament_participants(tournament_id: str, kind: str) -> set:
    """Alle Teilnehmer eines Arena- oder Swiss-Turniers (nicht nur Top-Platzierte)."""
    if kind == "swiss":
        url = f"{BASE_URL}/api/swiss/{tournament_id}/results"
    else:
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


# ---------------------------------------------------------------------------
# PARTIEN ZAEHLEN (nur Blitz, egal aus welchem Turnier der Spieler kam)
# ---------------------------------------------------------------------------
def count_recent_blitz_games(username: str, since_ms: int) -> int:
    """
    Zaehlt NUR Blitz-Partien eines Spielers seit since_ms (gedeckelt).
    perfType=blitz sorgt dafuer, dass ausschliesslich Blitz-Partien
    gezaehlt werden - unabhaengig davon, ob der Spieler urspruenglich aus
    einer Blitz-Arena, einem Blitz-Swiss oder der Top-Liste stammt.
    """
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
# LIVE-RANKING
# ---------------------------------------------------------------------------
def profile_url(username: str) -> str:
    return f"{BASE_URL}/@/{username}"


def get_current_rank(name: str, counts: dict) -> int:
    ranking = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    for i, (n, _c) in enumerate(ranking, start=1):
        if n == name:
            return i
    return -1


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


def write_top10_snapshot(counts: dict) -> None:
    """
    Schreibt den aktuellen Top-100-Stand in status/top100.json und
    status/top100.md - wird bei JEDEM Live-Update ueberschrieben, sodass
    dort immer der aktuelle Stand steht (nicht erst am Ende des Laufs).
    """
    STATUS_DIR.mkdir(exist_ok=True)
    ranking = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N_LIVE]
    now_iso = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "updated_at": now_iso,
        "since_days": SINCE_DAYS,
        "top10": [
            {"rank": i, "username": name, "games": cnt, "profile": profile_url(name)}
            for i, (name, cnt) in enumerate(ranking, start=1)
        ],
    }
    TOP10_JSON_FILE.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))

    lines = [
        f"# Top {TOP_N_LIVE} aktivste Blitz-Spieler (letzte {SINCE_DAYS} Tage)",
        "",
        f"_Zuletzt aktualisiert: {now_iso}_",
        "",
        "| Platz | Spieler | Partien | Profil |",
        "|---|---|---|---|",
    ]
    for i, (name, cnt) in enumerate(ranking, start=1):
        lines.append(f"| {i} | {name} | {cnt} | [{name}]({profile_url(name)}) |")
    TOP10_MD_FILE.write_text("\n".join(lines) + "\n")


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


def update_players_live(usernames: set, already_updated: set, counts: dict,
                         since_ms: int, leaderboard: dict) -> None:
    """
    Zentrale Live-Funktion: bekommt eine Menge frisch gefundener Spieler
    (z.B. Teilnehmer eines einzelnen gerade eingelesenen Turniers), zaehlt
    fuer alle noch nicht in diesem Lauf aktualisierten Spieler sofort die
    Blitz-Partien, aktualisiert das Leaderboard SOFORT (inkl. Speichern
    auf Platte) und zeigt bei Top-100-Neueinsteigern direkt einen Banner.

    'already_updated' verhindert, dass ein Spieler, der in mehreren
    Turnieren/Quellen auftaucht, in einem Lauf mehrfach abgefragt wird.
    """
    new_to_process = sorted(usernames - already_updated)
    if not new_to_process:
        return

    for username in new_to_process:
        try:
            time.sleep(REQUEST_DELAY_SECONDS)
            new_count = count_recent_blitz_games(username, since_ms)
        except RateLimitError:
            raise
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f"  [WARNUNG] '{username}' konnte nicht abgefragt werden: {exc}")
            continue

        already_updated.add(username)
        old_count = counts.get(username)
        counts[username] = new_count

        if new_count > 0 and (old_count is None or new_count != old_count):
            rank = get_current_rank(username, counts)
            if 0 < rank <= TOP_N:
                flashy_new_entry_banner(rank, username, new_count)

        # Nach jedem Spieler sofort persistieren, damit bei einem Abbruch
        # (z.B. Rate Limit) kein bereits berechneter Wert verloren geht.
        leaderboard["counts"] = counts
        leaderboard["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_leaderboard(leaderboard)

        # Top-100-Schnappschuss (status/top100.json + .md) IMMER aktuell
        # halten - das ist der Ort, an dem man "konstant" die Top 100
        # sehen kann, auch waehrend das Skript noch weiterlaeuft.
        write_top10_snapshot(counts)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    if not TOKEN:
        print("Hinweis: Kein LICHESS_TOKEN gesetzt - es wird unauthentifiziert "
              "abgefragt (niedrigeres Rate-Limit). Fuer bessere Performance "
              "LICHESS_TOKEN als Umgebungsvariable/Secret setzen.")

    known_players = load_json_set(KNOWN_PLAYERS_FILE)
    known_tournaments = load_json_set(KNOWN_TOURNAMENTS_FILE)
    print(f"Bereits bekannte Spieler im Pool: {len(known_players)}")
    print(f"Bereits bekannte Turniere: {len(known_tournaments)}")
    print("=" * 70)

    leaderboard = load_leaderboard()
    counts = leaderboard.get("counts", {})
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=SINCE_DAYS)).timestamp() * 1000)

    pool = set(known_players)
    updated_this_run = set()  # verhindert Mehrfach-Abfragen im selben Lauf

    try:
        # 1) Top-200 nach Rating - sofort live verarbeiten
        top_players = get_top_blitz_players()
        pool |= top_players
        update_players_live(top_players, updated_this_run, counts, since_ms, leaderboard)
        time.sleep(REQUEST_DELAY_SECONDS)

        # 2) Alle erreichbaren Blitz-Turniere sammeln: aktuell sichtbare +
        #    komplette Team-Historie (auch vergangene Turniere)
        tournament_sources = list(get_visible_blitz_tournament_ids())
        time.sleep(REQUEST_DELAY_SECONDS)

        for team_id in EXTRA_TEAM_IDS:
            print(f"Suche Blitz-Turnierhistorie von Team '{team_id}' (auch vergangene)...")
            team_tournaments = get_team_tournament_ids(team_id.lower())
            print(f"  {len(team_tournaments)} Blitz-Turnier(e) in der Historie gefunden.")
            tournament_sources.extend(team_tournaments)
            time.sleep(REQUEST_DELAY_SECONDS)

        # Turniere, die wir schon in einem frueheren Lauf komplett
        # verarbeitet haben, ueberspringen wir (spart Anfragen), tragen sie
        # aber nicht doppelt ein.
        new_sources = [(tid, kind) for tid, kind in tournament_sources
                        if tid not in known_tournaments]
        print(f"Davon neu (in frueheren Laeufen noch nicht verarbeitet): {len(new_sources)}")

        # 3) Jedes einzelne Turnier: Teilnehmer holen und SOFORT live
        #    verarbeiten, statt erst alle Turniere zu sammeln.
        for t_id, kind in new_sources:
            time.sleep(REQUEST_DELAY_SECONDS)
            participants = get_tournament_participants(t_id, kind)
            new_count = len(participants - pool)
            pool |= participants
            if new_count:
                print(f"  Turnier {t_id} ({kind}): {len(participants)} Teilnehmer "
                      f"({new_count} davon neu im Pool).")
            update_players_live(participants, updated_this_run, counts, since_ms, leaderboard)
            known_tournaments.add(t_id)

        # 4) Zusaetzliche Team-Mitgliederlisten - ebenfalls sofort live
        for team_id in EXTRA_TEAM_IDS:
            time.sleep(REQUEST_DELAY_SECONDS)
            members = get_team_members(team_id.lower())
            pool |= members
            update_players_live(members, updated_this_run, counts, since_ms, leaderboard)

    except RateLimitError as exc:
        print(f"[RATE LIMIT] {exc}")
        print("Breche Skript sofort ab und speichere den bisherigen Stand "
              "(Spieler-Pool, verarbeitete Turniere und Leaderboard). "
              "Naechster Lauf macht hier weiter (z.B. in 6 Stunden).")

    # Am Ende (oder bei Abbruch) alles persistieren, was bis dahin
    # ermittelt wurde.
    save_json_set(KNOWN_PLAYERS_FILE, pool)
    save_json_set(KNOWN_TOURNAMENTS_FILE, known_tournaments)
    leaderboard["counts"] = counts
    leaderboard["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_leaderboard(leaderboard)
    write_top10_snapshot(counts)

    new_players_total = len(pool - known_players)
    print()
    print(f"Spieler-Pool nach diesem Lauf: {len(pool)} "
          f"({new_players_total} neu hinzugekommen).")
    print(f"In diesem Lauf live abgefragte Spieler: {len(updated_this_run)}.")

    print_top(counts)
    print()
    print(f"Fertig. {len(counts)} Spieler insgesamt im Leaderboard.")


if __name__ == "__main__":
    main()
