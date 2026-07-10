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
     Jeweils ALLE Teilnehmer via /api/tournament/{id}/results bzw.
     /api/swiss/{id}/results (nicht nur die Top-Platzierten).
  3. Optional: Mitglieder aus selbst konfigurierten Teams (EXTRA_TEAM_IDS).
  4. SNOWBALL-CRAWL ueber die Partien-Gegner ("Lobby"-Ausbreitung), siehe
     Abschnitt "SNOWBALL-CRAWL" weiter unten.

-------------------------------------------------------------------
WARUM EIN LAUF NICHT MEHR "BEI NULL" ANFAENGT (COOLDOWNS)
-------------------------------------------------------------------
Fruehere Version: JEDER bekannte Spieler (alle Top-200, alle Team-
Mitglieder, ...) wurde bei JEDEM Lauf erneut komplett abgefragt, um seine
Partienzahl zu aktualisieren. Bei einem 6-Stunden-Cron heisst das: der
groesste Teil jedes einzelnen Laufs ging dafuer drauf, dieselben paar
hundert bereits bekannten Namen ein weiteres Mal abzufragen - fuer den
Snowball-Crawl (der eigentlich fuer echtes Wachstum sorgt) blieb kaum
noch Zeit/Budget uebrig, und es SAH so aus, als wuerde jeder Lauf einfach
wieder von vorne "Top-Liste -> Turniere -> Teams" durchgehen.

Jetzt hat jeder Spieler einen last_checked-Zeitstempel (gespeichert in
leaderboard.json). Ein bereits bekannter Spieler wird nur dann erneut
abgefragt, wenn CHECK_COOLDOWN_HOURS seit der letzten Abfrage vergangen
sind - ein komplett NEUER Spieler wird dagegen immer sofort abgefragt.
Dasselbe Prinzip gilt fuer:
  - Team-Mitgliederlisten (TEAM_SYNC_COOLDOWN_HOURS) - die komplette
    Roster-Liste eines Teams wird nicht mehr bei jedem Lauf neu geholt.
  - Den Snowball-Crawl (RECRAWL_COOLDOWN_HOURS) - ein Spieler, dessen
    letzte 10 Partien schon einmal nach Gegnern durchsucht wurden, wird
    erst nach Ablauf dieser Frist erneut als Crawl-Seed benutzt (vorher
    haetten seine letzten 10 Partien sich ohnehin kaum von denen beim
    letzten Mal unterschieden -> reine Wiederholung ohne neuen Ertrag).
    Bereits bekannte, aber noch nie gecrawlte Spieler haben dabei immer
    Vorrang vor "Recrawls".

Turniere waren schon vorher ueber known_tournaments.json dauerhaft vor
Doppel-Verarbeitung geschuetzt - das bleibt unveraendert.

Ergebnis: jeder Lauf verbringt seine Zeit ueberwiegend mit tatsaechlich
NEUEN Dingen (neue Turnierteilnehmer, neue Crawl-Gegner, faellige
Cooldown-Refreshs) statt denselben Namen hinterherzulaufen.

-------------------------------------------------------------------
LIVE-RANKING WAEHREND DER SUCHE
-------------------------------------------------------------------
Das Skript wartet NICHT, bis der komplette Spieler-Pool gesammelt ist,
bevor es Partien zaehlt. Jede Quelle wird sofort nach dem Einlesen
verarbeitet, das Leaderboard sofort aktualisiert, und bei einem
Top-100-Einstieg erscheint sofort ein auffaelliger Banner.

-------------------------------------------------------------------
SNOWBALL-CRAWL (Gegner-basierte Pool-Erweiterung)
-------------------------------------------------------------------
  - CRAWL_QUEUE_FILE: FIFO-Warteschlange neu gefundener, noch nie
    gecrawlter Spieler.
  - KNOWN_CRAWLED_FILE: username -> Zeitpunkt des letzten Crawls (frueher
    eine reine Liste, jetzt mit Zeitstempel fuer die Recrawl-Logik).
  - Seed-Auswahl pro Lauf, in dieser Prioritaet:
      1. Nie gecrawlte Spieler aus der FIFO-Queue.
      2. Nie gecrawlte Spieler zufaellig aus dem restlichen Pool.
      3. Erst wenn 1+2 nicht reichen: Spieler, deren letzter Crawl laenger
         als RECRAWL_COOLDOWN_HOURS zurueckliegt.
  - Fuer jeden Seed werden die letzten CRAWL_GAMES_PER_SEED Partien
    angesehen und beide Spielernamen extrahiert. Neue Gegner werden
    sofort live verarbeitet UND ans Ende der Crawl-Queue gehaengt.

-------------------------------------------------------------------
KONFIGURATION
-------------------------------------------------------------------
LICHESS_TOKEN als Umgebungsvariable/GitHub Secret setzen.

EXTRA_TEAM_IDS: Liste zusaetzlicher Team-Slugs.

SINCE_DAYS: Zeitraum in Tagen, ueber den Partien gezaehlt werden (7).

MAX_GAMES_PER_QUERY: Obergrenze Partien/Spieler (Deckel).

MAX_TEAM_TOURNAMENTS: Obergrenze vergangene Turniere pro Team/Typ.

CHECK_COOLDOWN_HOURS: Wie lange ein bereits bekannter Spieler NICHT
erneut auf seine Partienzahl geprueft wird (Standard: 18h). Neue
Spieler werden davon nie ausgebremst.

TEAM_SYNC_COOLDOWN_HOURS: Wie lange eine Team-Mitgliederliste nicht
erneut komplett abgerufen wird (Standard: 12h).

RECRAWL_COOLDOWN_HOURS: Wie lange gewartet wird, bevor ein bereits
gecrawlter Spieler erneut als Crawl-Seed benutzt werden darf (72h).

CRAWL_SEED_COUNT / CRAWL_GAMES_PER_SEED: Snowball-Crawl-Parameter.

REQUEST_DELAY_SECONDS: Pause zwischen API-Aufrufen.

Sobald Lichess mit HTTP 429 antwortet, wartet das Skript automatisch
(Exponential-Backoff) und versucht es danach erneut. Nur bei sehr
langem durchgehendem 429 gibt das Skript fuer DIESEN Lauf auf und
speichert vorher alles bisher Ermittelte.

Ausfuehren (einmaliger Durchlauf):
    python3 most_active_blitz_players.py
"""

import json
import os
import random
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("LICHESS_TOKEN", "")

CLOCK_BASED_PERF_TYPES = {"ultraBullet", "bullet", "blitz", "rapid", "classical"}
VARIANT_PERF_TYPES = {
    "chess960", "crazyhouse", "antichess", "atomic",
    "horde", "kingOfTheHill", "racingKings", "threeCheck",
}
ALLOWED_PERF_TYPES = CLOCK_BASED_PERF_TYPES | VARIANT_PERF_TYPES

PERF_TYPE = os.environ.get("PERF_TYPE", "blitz").strip()
if PERF_TYPE not in ALLOWED_PERF_TYPES:
    sys.exit(
        f"Ungueltiger PERF_TYPE '{PERF_TYPE}'. Erlaubt sind: "
        f"{', '.join(sorted(ALLOWED_PERF_TYPES))}"
    )


def classify_clock_seconds(total_estimated_seconds: float) -> str:
    if total_estimated_seconds < 29:
        return "ultraBullet"
    if total_estimated_seconds < 179:
        return "bullet"
    if total_estimated_seconds < 479:
        return "blitz"
    if total_estimated_seconds < 1499:
        return "rapid"
    return "classical"


def swiss_matches_perf_type(row: dict) -> bool:
    variant = row.get("variant", {})
    variant_key = variant.get("key") if isinstance(variant, dict) else None

    if PERF_TYPE in VARIANT_PERF_TYPES:
        return variant_key == PERF_TYPE

    if variant_key != "standard":
        return False
    clock = row.get("clock", {})
    limit = clock.get("limit", 0) if isinstance(clock, dict) else 0
    increment = clock.get("increment", 0) if isinstance(clock, dict) else 0
    total = limit + 40 * increment
    return classify_clock_seconds(total) == PERF_TYPE


EXTRA_TEAM_IDS = [
     "darkonblitz-dob",
     "darkonteams",
     "--elite-chess-players-union--"
]

SINCE_DAYS = 7
MAX_GAMES_PER_QUERY = 10000
TOP_N = 100
REQUEST_DELAY_SECONDS = 1.0
MAX_TEAM_TOURNAMENTS = 1000

# --- Cooldowns: das ist der eigentliche Fix gegen "jeder Lauf wiederholt
# sich" - siehe Docstring-Abschnitt weiter oben. -----------------------
CHECK_COOLDOWN_HOURS = float(os.environ.get("CHECK_COOLDOWN_HOURS", "18"))
TEAM_SYNC_COOLDOWN_HOURS = float(os.environ.get("TEAM_SYNC_COOLDOWN_HOURS", "12"))
RECRAWL_COOLDOWN_HOURS = float(os.environ.get("RECRAWL_COOLDOWN_HOURS", "72"))

CHECK_COOLDOWN_SECONDS = CHECK_COOLDOWN_HOURS * 3600
TEAM_SYNC_COOLDOWN_SECONDS = TEAM_SYNC_COOLDOWN_HOURS * 3600
RECRAWL_COOLDOWN_SECONDS = RECRAWL_COOLDOWN_HOURS * 3600

# --- Snowball-Crawl ---------------------------------------------------
# Dank der Cooldowns oben faellt jetzt deutlich mehr Zeit/Budget pro Lauf
# fuer den Crawl ab, daher ist der Default hier hoeher als frueher.
CRAWL_SEED_COUNT = int(os.environ.get("CRAWL_SEED_COUNT", "15"))
CRAWL_GAMES_PER_SEED = int(os.environ.get("CRAWL_GAMES_PER_SEED", "10"))

# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent  # scripts/auto -> scripts -> Repo-Root

DATA_DIR = REPO_ROOT / "data" / PERF_TYPE
KNOWN_PLAYERS_FILE = DATA_DIR / "known_players.json"
LEADERBOARD_FILE = DATA_DIR / "leaderboard.json"
KNOWN_TOURNAMENTS_FILE = DATA_DIR / "known_tournaments.json"

CRAWL_QUEUE_FILE = DATA_DIR / "crawl_queue.json"
KNOWN_CRAWLED_FILE = DATA_DIR / "known_crawled.json"       # username -> ISO-Zeitstempel
TEAM_SYNC_STATE_FILE = DATA_DIR / "team_sync_state.json"   # team_id  -> ISO-Zeitstempel

STATUS_DIR = REPO_ROOT / "status" / PERF_TYPE
TOP10_JSON_FILE = STATUS_DIR / "top100.json"
TOP10_MD_FILE = STATUS_DIR / "top100.md"
TOP_N_LIVE = 100

# ---------------------------------------------------------------------------
# LIVE GIT PUSH
# ---------------------------------------------------------------------------
LIVE_GIT_PUSH = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
GIT_PUSH_MIN_INTERVAL_SECONDS = 30
_last_git_push_ts = 0.0
GIT_PUSH_MAX_RETRIES = 8
GIT_PUSH_RETRY_BASE_DELAY_SECONDS = 3


def ensure_on_branch() -> None:
    check = subprocess.run(
        ["git", "symbolic-ref", "-q", "HEAD"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if check.returncode == 0:
        return

    branch = os.environ.get("GITHUB_REF_NAME") or "main"
    print(f"  [GIT] Detached HEAD erkannt - wechsle explizit auf Branch '{branch}'...")
    subprocess.run(
        ["git", "checkout", "-B", branch, f"origin/{branch}"],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    )


def git_commit_and_push(message: str) -> bool:
    if not LIVE_GIT_PUSH:
        return False
    try:
        ensure_on_branch()

        candidate_paths = [
            STATUS_DIR, KNOWN_PLAYERS_FILE, KNOWN_TOURNAMENTS_FILE,
            LEADERBOARD_FILE, CRAWL_QUEUE_FILE, KNOWN_CRAWLED_FILE,
            TEAM_SYNC_STATE_FILE,
        ]
        existing_paths = [str(p) for p in candidate_paths if p.exists()]
        if not existing_paths:
            return False

        subprocess.run(
            ["git", "add", "-f", "--ignore-errors", *existing_paths],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        )
        diff_check = subprocess.run(
            ["git", "diff", "--staged", "--quiet"], cwd=REPO_ROOT
        )
        if diff_check.returncode == 0:
            return False

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        )

        last_error = None
        for attempt in range(1, GIT_PUSH_MAX_RETRIES + 1):
            try:
                subprocess.run(
                    ["git", "pull", "--rebase"],
                    cwd=REPO_ROOT, check=True, capture_output=True, text=True,
                )
                subprocess.run(
                    ["git", "push"],
                    cwd=REPO_ROOT, check=True, capture_output=True, text=True,
                )
                print(f"  [GIT] Live-Push durchgefuehrt: {message}")
                return True
            except subprocess.CalledProcessError as exc:
                last_error = exc
                if attempt < GIT_PUSH_MAX_RETRIES:
                    delay = GIT_PUSH_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    delay += random.uniform(0, delay * 0.5)
                    delay = min(delay, 60)
                    print(f"  [GIT] Push kollidiert (Versuch {attempt}/"
                          f"{GIT_PUSH_MAX_RETRIES}), warte {delay:.1f}s und "
                          f"versuche erneut...")
                    time.sleep(delay)

        stderr = last_error.stderr if last_error and hasattr(last_error, "stderr") else str(last_error)
        print(f"  [WARNUNG] Git-Push nach {GIT_PUSH_MAX_RETRIES} Versuchen "
              f"weiterhin fehlgeschlagen: {stderr}")
        return False
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr if hasattr(exc, "stderr") else str(exc)
        print(f"  [WARNUNG] Git-Commit/Push fehlgeschlagen: {stderr}")
        return False


def maybe_live_push(force: bool = False) -> None:
    global _last_git_push_ts
    now = time.time()
    if not force and (now - _last_git_push_ts) < GIT_PUSH_MIN_INTERVAL_SECONDS:
        return
    _last_git_push_ts = now
    git_commit_and_push(
        f"Live-Update Blitz-Leaderboard {datetime.now(timezone.utc).isoformat()} [skip ci]"
    )

BASE_URL = "https://lichess.org"
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
NDJSON_HEADERS = {**HEADERS, "Accept": "application/x-ndjson"}


class RateLimitError(Exception):
    """Wird ausgeloest, wenn Lichess mit HTTP 429 antwortet."""


# ---------------------------------------------------------------------------
# ZEIT-HELFER (fuer die Cooldown-Logik)
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seconds_since(iso_ts: str) -> float:
    """Sekunden seit einem ISO-Zeitstempel. Bei kaputtem/leerem Wert: unendlich."""
    if not iso_ts:
        return float("inf")
    try:
        then = datetime.fromisoformat(iso_ts)
    except ValueError:
        return float("inf")
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - then).total_seconds()


def is_due(iso_ts: str, cooldown_seconds: float) -> bool:
    """True, wenn seit iso_ts mindestens cooldown_seconds vergangen sind
    (oder iso_ts leer/ungueltig ist -> dann sofort faellig)."""
    return seconds_since(iso_ts) >= cooldown_seconds


def format_duration(total_seconds: float) -> str:
    total_seconds = int(total_seconds)
    m, s = divmod(total_seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# HTTP HELPERS
# ---------------------------------------------------------------------------
RATE_LIMIT_INITIAL_BACKOFF_SECONDS = 20
RATE_LIMIT_MAX_BACKOFF_SECONDS = 300
RATE_LIMIT_MAX_TOTAL_WAIT_SECONDS = 1800


def _request(url: str, headers: dict, timeout: int = 30):
    backoff = RATE_LIMIT_INITIAL_BACKOFF_SECONDS
    total_waited = 0.0
    while True:
        req = urllib.request.Request(url, headers=headers)
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise

            retry_after_header = exc.headers.get("Retry-After") if exc.headers else None
            try:
                wait_s = float(retry_after_header)
            except (TypeError, ValueError):
                wait_s = backoff
            wait_s = max(wait_s, 1.0)

            if total_waited + wait_s > RATE_LIMIT_MAX_TOTAL_WAIT_SECONDS:
                raise RateLimitError(
                    f"Rate Limit bei {url} - trotz {total_waited:.0f}s Warten "
                    f"weiterhin 429, gebe fuer diesen Lauf auf"
                ) from exc

            print(f"  [RATE LIMIT] 429 bei {url} - warte {wait_s:.0f}s und "
                  f"versuche es dann automatisch erneut (insgesamt schon "
                  f"{total_waited:.0f}s gewartet)...")
            time.sleep(wait_s)
            total_waited += wait_s
            backoff = min(backoff * 2, RATE_LIMIT_MAX_BACKOFF_SECONDS)


def fetch_json(url: str) -> dict:
    with _request(url, HEADERS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_ndjson(url: str, headers: dict = None):
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(values), indent=2))


def load_json_list(path: Path) -> list:
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_json_list(path: Path, values: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values, indent=2))


def load_json_dict(path: Path) -> dict:
    """Wie load_json_set, aber fuer username/team_id -> Zeitstempel Mappings.
    Migriert transparent alte Dateien, die noch eine reine Liste waren
    (Vorgaenger-Version von known_crawled.json): die migrierten Eintraege
    bekommen 'jetzt' als Zeitstempel, damit nicht sofort ein Recrawl-Sturm
    losgeht, sondern die normale Cooldown-Frist ab jetzt greift."""
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return data
            if isinstance(data, list):
                stamp = now_iso()
                return {name: stamp for name in data}
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_json_dict(path: Path, values: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values, indent=2, sort_keys=True))


def load_leaderboard() -> dict:
    if LEADERBOARD_FILE.exists():
        try:
            data = json.loads(LEADERBOARD_FILE.read_text())
            if isinstance(data, dict):
                data.setdefault("counts", {})
                data.setdefault("last_checked", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"updated_at": None, "counts": {}, "last_checked": {}}


def save_leaderboard(leaderboard: dict) -> None:
    counts = leaderboard.get("counts", {})
    ranking = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    leaderboard["ranking"] = [
        {"rank": i, "username": name, "games": cnt, "profile": profile_url(name)}
        for i, (name, cnt) in enumerate(ranking, start=1)
    ]
    LEADERBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_FILE.write_text(json.dumps(leaderboard, indent=2, sort_keys=True, ensure_ascii=False))


# ---------------------------------------------------------------------------
# TURNIERE FINDEN (aktuell sichtbar + Team-Historie, NUR PERF_TYPE)
# ---------------------------------------------------------------------------
def get_visible_blitz_tournament_ids() -> list:
    print(f"  -> Suche aktuell sichtbare {PERF_TYPE}-Arenen...")
    try:
        data = fetch_json(f"{BASE_URL}/api/tournament")
    except (RateLimitError, urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"     [WARNUNG] Turnierliste konnte nicht geladen werden: {exc}")
        return []

    ids = []
    for bucket in ("finished", "started", "created"):
        for t in data.get(bucket, []):
            perf = t.get("perf", {})
            perf_key = perf.get("key") if isinstance(perf, dict) else None
            if perf_key == PERF_TYPE and t.get("id"):
                ids.append((t["id"], "arena"))

    print(f"     {len(ids)} {PERF_TYPE}-Arena(n) sichtbar.")
    return ids


def get_team_tournament_ids(team_id: str) -> list:
    found = []

    url = f"{BASE_URL}/api/team/{team_id}/arena?max={MAX_TEAM_TOURNAMENTS}"
    try:
        for row in fetch_ndjson(url):
            perf = row.get("perf", {})
            perf_key = perf.get("key") if isinstance(perf, dict) else None
            if perf_key == PERF_TYPE and row.get("id"):
                found.append((row["id"], "arena"))
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"     [WARNUNG] Arena-Historie von Team '{team_id}' nicht ladbar: {exc}")

    url = f"{BASE_URL}/api/team/{team_id}/swiss?max={MAX_TEAM_TOURNAMENTS}"
    try:
        for row in fetch_ndjson(url):
            if swiss_matches_perf_type(row) and row.get("id"):
                found.append((row["id"], "swiss"))
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"     [WARNUNG] Swiss-Historie von Team '{team_id}' nicht ladbar: {exc}")

    return found


def get_tournament_participants(tournament_id: str, kind: str) -> set:
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
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"     [WARNUNG] Teilnehmer von Turnier {tournament_id} nicht ladbar: {exc}")
    return users


def get_team_members(team_id: str) -> set:
    url = f"{BASE_URL}/api/team/{team_id}/users"
    users = set()
    try:
        for row in fetch_ndjson(url):
            name = row.get("username") or row.get("id")
            if name:
                users.add(name.lower())
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"     [WARNUNG] Mitglieder von Team '{team_id}' nicht ladbar: {exc}")
    return users


def get_top_blitz_players() -> set:
    try:
        data = fetch_json(f"{BASE_URL}/api/player/top/200/{PERF_TYPE}")
        users = {u["username"].lower() for u in data.get("users", [])}
        return users
    except (RateLimitError, urllib.error.URLError, urllib.error.HTTPError, OSError, KeyError) as exc:
        print(f"  [WARNUNG] Top-Liste konnte nicht geladen werden: {exc}")
        return set()


# ---------------------------------------------------------------------------
# SNOWBALL-CRAWL: Gegner aus den letzten Partien eines Spielers extrahieren
# ---------------------------------------------------------------------------
def get_recent_opponents(username: str, limit: int) -> set:
    params = urllib.parse.urlencode({
        "max": limit,
        "perfType": PERF_TYPE,
        "moves": "false",
        "tags": "false",
        "opening": "false",
        "clocks": "false",
        "evals": "false",
    })
    url = f"{BASE_URL}/api/games/user/{username}?{params}"

    opponents = set()
    try:
        for game in fetch_ndjson(url):
            players = game.get("players", {})
            for color in ("white", "black"):
                side = players.get(color, {})
                user = side.get("user", {}) if isinstance(side, dict) else {}
                opp_name = user.get("name") or user.get("id")
                if opp_name and opp_name.lower() != username.lower():
                    opponents.add(opp_name.lower())
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"     [WARNUNG] Partien-Gegner von '{username}' nicht ladbar: {exc}")
    return opponents


def pick_crawl_seeds(queue: list, known_crawled: dict, pool: set) -> tuple:
    """
    Waehlt bis zu CRAWL_SEED_COUNT Spieler als Crawl-Seeds, in dieser
    Prioritaet (siehe Docstring oben fuer die Begruendung):
      1. Nie gecrawlte Spieler aus der FIFO-Queue.
      2. Nie gecrawlte Spieler zufaellig aus dem restlichen Pool.
      3. Spieler, deren letzter Crawl laenger als RECRAWL_COOLDOWN_HOURS
         zurueckliegt (niedrigste Prioritaet - vermeidet, dieselben
         letzten 10 Partien staendig erneut anzusehen).
    """
    seeds = []

    # 1) FIFO-Queue, nur nie gecrawlte Spieler ziehen; alles andere bleibt
    #    fuer spaeter in der Queue stehen.
    remaining_queue = []
    for candidate in queue:
        if len(seeds) < CRAWL_SEED_COUNT and candidate not in known_crawled:
            seeds.append(candidate)
        else:
            remaining_queue.append(candidate)

    # 2) zufaellige, nie gecrawlte Pool-Mitglieder
    if len(seeds) < CRAWL_SEED_COUNT:
        fresh_candidates = [p for p in pool if p not in known_crawled and p not in seeds]
        random.shuffle(fresh_candidates)
        for candidate in fresh_candidates:
            if len(seeds) >= CRAWL_SEED_COUNT:
                break
            seeds.append(candidate)

    # 3) laengst faellige Re-Crawls, nur falls immer noch Luft ist
    if len(seeds) < CRAWL_SEED_COUNT:
        stale_candidates = [
            p for p in pool
            if p not in seeds and p in known_crawled
            and is_due(known_crawled[p], RECRAWL_COOLDOWN_SECONDS)
        ]
        random.shuffle(stale_candidates)
        for candidate in stale_candidates:
            if len(seeds) >= CRAWL_SEED_COUNT:
                break
            seeds.append(candidate)

    return seeds, remaining_queue


def run_snowball_crawl(pool: set, updated_this_run: set, counts: dict, last_checked: dict,
                        since_ms: int, leaderboard: dict, stats: dict) -> set:
    queue = load_json_list(CRAWL_QUEUE_FILE)
    known_crawled = load_json_dict(KNOWN_CRAWLED_FILE)

    seeds, remaining_queue = pick_crawl_seeds(queue, known_crawled, pool)
    if not seeds:
        print("  Keine Seeds verfuegbar (Pool leer oder alles im Recrawl-Cooldown), ueberspringe.")
        return set()

    never_crawled_seeds = sum(1 for s in seeds if s not in known_crawled)
    recrawl_seeds = len(seeds) - never_crawled_seeds
    print(f"  {len(seeds)} Seed-Spieler ({never_crawled_seeds} neu, {recrawl_seeds} Recrawl), "
          f"je die letzten {CRAWL_GAMES_PER_SEED} Partien -> Gegner extrahieren...")

    all_new_opponents = set()
    for seed in seeds:
        time.sleep(REQUEST_DELAY_SECONDS)
        opponents = get_recent_opponents(seed, CRAWL_GAMES_PER_SEED)
        new_opponents = opponents - pool
        if new_opponents:
            print(f"    '{seed}': {len(opponents)} Gegner ({len(new_opponents)} neu im Pool).")

        all_new_opponents |= new_opponents
        pool |= opponents
        known_crawled[seed] = now_iso()
        stats["seeds_crawled"] += 1

        update_players_live(opponents, updated_this_run, counts, last_checked,
                             since_ms, leaderboard, stats)
        for name in sorted(new_opponents):
            if name not in remaining_queue and name not in known_crawled:
                remaining_queue.append(name)

        save_json_list(CRAWL_QUEUE_FILE, remaining_queue)
        save_json_dict(KNOWN_CRAWLED_FILE, known_crawled)
        save_json_set(KNOWN_PLAYERS_FILE, pool)

    print(f"  Crawl fertig: {len(all_new_opponents)} neue Spieler gefunden. "
          f"Neue Queue-Laenge: {len(remaining_queue)}.")
    return all_new_opponents


# ---------------------------------------------------------------------------
# PARTIEN ZAEHLEN
# ---------------------------------------------------------------------------
def count_recent_blitz_games(username: str, since_ms: int) -> int:
    params = urllib.parse.urlencode({
        "since": since_ms,
        "perfType": PERF_TYPE,
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
# AUSGABE-HELFER
# ---------------------------------------------------------------------------
def print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str) -> None:
    print()
    print(f"[{title}]")
    print("-" * 70)


def print_stat(label: str, value, width: int = 42) -> None:
    print(f"  {label:<{width}} {value}")


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
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    ranking = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N_LIVE]
    now = now_iso()

    snapshot = {
        "updated_at": now,
        "since_days": SINCE_DAYS,
        "top10": [
            {"rank": i, "username": name, "games": cnt, "profile": profile_url(name)}
            for i, (name, cnt) in enumerate(ranking, start=1)
        ],
    }
    TOP10_JSON_FILE.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))

    lines = [
        f"# Top {TOP_N_LIVE} aktivste {PERF_TYPE}-Spieler (letzte {SINCE_DAYS} Tage)",
        "",
        f"_Zuletzt aktualisiert: {now}_",
        "",
        "| Platz | Spieler | Partien | Profil |",
        "|---|---|---|---|",
    ]
    for i, (name, cnt) in enumerate(ranking, start=1):
        lines.append(f"| {i} | {name} | {cnt} | [{name}]({profile_url(name)}) |")
    TOP10_MD_FILE.write_text("\n".join(lines) + "\n")


def print_top(counts: dict, n: int = TOP_N) -> list:
    ranking = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]
    print_header(f"TOP {n} AKTIVSTE {PERF_TYPE.upper()}-SPIELER (letzte {SINCE_DAYS} Tage)")
    for i, (name, cnt) in enumerate(ranking, start=1):
        print(f"  {i:>3}. {name:<20} {cnt:>5} Partien   {profile_url(name)}")
    print("=" * 70)
    return ranking


# ---------------------------------------------------------------------------
# ZENTRALE LIVE-VERARBEITUNG (mit Cooldown - der eigentliche Kern-Fix)
# ---------------------------------------------------------------------------
def update_players_live(usernames: set, already_updated: set, counts: dict, last_checked: dict,
                         since_ms: int, leaderboard: dict, stats: dict = None) -> None:
    """
    Bekommt eine Menge Spieler und aktualisiert deren Partienzahl - ABER
    nur, wenn es sich lohnt:
      - Spieler, die in diesem Lauf schon behandelt wurden -> ueberspringen
        (already_updated, wie bisher).
      - Komplett neue Spieler (noch nie in counts) -> IMMER sofort pruefen.
      - Bereits bekannte Spieler -> nur pruefen, wenn seit dem letzten Mal
        mindestens CHECK_COOLDOWN_HOURS vergangen sind. Das ist der Grund,
        warum ein Lauf nicht mehr Hunderte laengst bekannter Namen erneut
        abfragt, bevor er zu irgendwas Neuem kommt.
    """
    if stats is None:
        stats = {"checked": 0, "skipped_cooldown": 0, "new": 0, "failed": 0}

    new_to_process = sorted(usernames - already_updated)
    if not new_to_process:
        return

    for username in new_to_process:
        already_updated.add(username)
        is_new_player = username not in counts

        if not is_new_player and not is_due(last_checked.get(username, ""), CHECK_COOLDOWN_SECONDS):
            stats["skipped_cooldown"] += 1
            continue

        try:
            time.sleep(REQUEST_DELAY_SECONDS)
            new_count = count_recent_blitz_games(username, since_ms)
        except RateLimitError:
            raise
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            print(f"    [WARNUNG] '{username}' konnte nicht abgefragt werden: {exc}")
            stats["failed"] += 1
            continue

        old_count = counts.get(username)
        counts[username] = new_count
        last_checked[username] = now_iso()
        stats["checked"] += 1
        if is_new_player:
            stats["new"] += 1

        if new_count > 0 and (old_count is None or new_count != old_count):
            rank = get_current_rank(username, counts)
            if 0 < rank <= TOP_N:
                flashy_new_entry_banner(rank, username, new_count)

        leaderboard["counts"] = counts
        leaderboard["last_checked"] = last_checked
        leaderboard["updated_at"] = now_iso()
        save_leaderboard(leaderboard)
        write_top10_snapshot(counts)
        maybe_live_push()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    run_start = time.time()

    if not TOKEN:
        print("Hinweis: Kein LICHESS_TOKEN gesetzt - es wird unauthentifiziert "
              "abgefragt (niedrigeres Rate-Limit).")

    known_players = load_json_set(KNOWN_PLAYERS_FILE)
    known_tournaments = load_json_set(KNOWN_TOURNAMENTS_FILE)
    crawl_queue_len = len(load_json_list(CRAWL_QUEUE_FILE))
    known_crawled_len = len(load_json_dict(KNOWN_CRAWLED_FILE))
    team_sync_state = load_json_dict(TEAM_SYNC_STATE_FILE)

    print_header(f"BLITZ-ACTIVITY RUN - {PERF_TYPE} - {now_iso()}")
    print_stat("Bekannte Spieler im Pool", len(known_players))
    print_stat("Bekannte (bereits verarbeitete) Turniere", len(known_tournaments))
    print_stat("Crawl-Queue-Laenge", crawl_queue_len)
    print_stat("Bereits gecrawlte Spieler", known_crawled_len)
    print_stat("Cooldown Spieler-Refresh", f"{CHECK_COOLDOWN_HOURS:.0f}h")
    print_stat("Cooldown Team-Roster-Refresh", f"{TEAM_SYNC_COOLDOWN_HOURS:.0f}h")
    print_stat("Cooldown Recrawl", f"{RECRAWL_COOLDOWN_HOURS:.0f}h")

    leaderboard = load_leaderboard()
    counts = leaderboard.get("counts", {})
    last_checked = leaderboard.get("last_checked", {})
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=SINCE_DAYS)).timestamp() * 1000)

    write_top10_snapshot(counts)

    pool = set(known_players)
    updated_this_run = set()

    save_json_set(KNOWN_PLAYERS_FILE, pool)
    save_json_set(KNOWN_TOURNAMENTS_FILE, known_tournaments)
    save_json_list(CRAWL_QUEUE_FILE, load_json_list(CRAWL_QUEUE_FILE))
    save_json_dict(KNOWN_CRAWLED_FILE, load_json_dict(KNOWN_CRAWLED_FILE))
    save_json_dict(TEAM_SYNC_STATE_FILE, team_sync_state)
    maybe_live_push(force=True)

    overall_stats = {"checked": 0, "skipped_cooldown": 0, "new": 0, "failed": 0, "seeds_crawled": 0}
    phase_stats = {}

    def run_phase(label, usernames):
        before = dict(overall_stats)
        update_players_live(usernames, updated_this_run, counts, last_checked,
                             since_ms, leaderboard, overall_stats)
        phase_stats[label] = {k: overall_stats[k] - before[k] for k in overall_stats}

    try:
        # --- Phase 1: Top-Liste nach Rating -------------------------------
        print_section("1/4 Top-Liste nach Rating")
        top_players = get_top_blitz_players()
        new_in_top = len(top_players - pool)
        pool |= top_players
        save_json_set(KNOWN_PLAYERS_FILE, pool)
        print_stat("Gefunden", f"{len(top_players)} Spieler ({new_in_top} neu im Pool)")
        run_phase("top_liste", top_players)
        print_stat("Neu geprueft", phase_stats["top_liste"]["new"])
        print_stat("Cooldown-Refresh geprueft", phase_stats["top_liste"]["checked"] - phase_stats["top_liste"]["new"])
        print_stat("Uebersprungen (Cooldown)", phase_stats["top_liste"]["skipped_cooldown"])
        time.sleep(REQUEST_DELAY_SECONDS)

        # --- Phase 2: Turniere --------------------------------------------
        print_section("2/4 Turniere (sichtbar + Team-Historie)")
        tournament_sources = list(get_visible_blitz_tournament_ids())
        time.sleep(REQUEST_DELAY_SECONDS)

        for team_id in EXTRA_TEAM_IDS:
            print(f"  -> Turnierhistorie von Team '{team_id}'...")
            team_tournaments = get_team_tournament_ids(team_id.lower())
            print(f"     {len(team_tournaments)} {PERF_TYPE}-Turnier(e) gefunden.")
            tournament_sources.extend(team_tournaments)
            time.sleep(REQUEST_DELAY_SECONDS)

        new_sources = [(tid, kind) for tid, kind in tournament_sources
                        if tid not in known_tournaments]
        print_stat("Turniere insgesamt gesehen", len(tournament_sources))
        print_stat("Davon bereits verarbeitet (übersprungen)",
                    len(tournament_sources) - len(new_sources))
        print_stat("Davon neu zu verarbeiten", len(new_sources))

        tournament_new_players = 0
        for t_id, kind in new_sources:
            time.sleep(REQUEST_DELAY_SECONDS)
            participants = get_tournament_participants(t_id, kind)
            new_count = len(participants - pool)
            tournament_new_players += new_count
            pool |= participants
            if new_count:
                print(f"  Turnier {t_id} ({kind}): {len(participants)} Teilnehmer "
                      f"({new_count} neu im Pool).")
            run_phase("turniere", participants)
            known_tournaments.add(t_id)
            save_json_set(KNOWN_PLAYERS_FILE, pool)
            save_json_set(KNOWN_TOURNAMENTS_FILE, known_tournaments)

        print_stat("Neue Spieler aus Turnieren", tournament_new_players)

        # --- Phase 3: Team-Mitgliederlisten (mit Sync-Cooldown) -----------
        print_section("3/4 Team-Mitgliederlisten")
        for team_id in EXTRA_TEAM_IDS:
            tid = team_id.lower()
            last_sync = team_sync_state.get(tid, "")
            if not is_due(last_sync, TEAM_SYNC_COOLDOWN_SECONDS):
                remaining_h = (TEAM_SYNC_COOLDOWN_SECONDS - seconds_since(last_sync)) / 3600
                print(f"  '{team_id}': übersprungen (Roster erst vor "
                      f"{seconds_since(last_sync) / 3600:.1f}h geholt, "
                      f"noch {remaining_h:.1f}h Cooldown).")
                continue

            time.sleep(REQUEST_DELAY_SECONDS)
            members = get_team_members(tid)
            new_count = len(members - pool)
            pool |= members
            team_sync_state[tid] = now_iso()
            save_json_dict(TEAM_SYNC_STATE_FILE, team_sync_state)
            save_json_set(KNOWN_PLAYERS_FILE, pool)
            print(f"  '{team_id}': {len(members)} Mitglieder ({new_count} neu im Pool).")
            run_phase("teams", members)

        # --- Phase 4: Snowball-Crawl ---------------------------------------
        print_section("4/4 Snowball-Crawl (Partien-Gegner)")
        crawl_stats = {"checked": 0, "skipped_cooldown": 0, "new": 0, "failed": 0, "seeds_crawled": 0}
        new_from_crawl = run_snowball_crawl(pool, updated_this_run, counts, last_checked,
                                             since_ms, leaderboard, crawl_stats)
        for k in overall_stats:
            overall_stats[k] += crawl_stats[k]
        phase_stats["crawl"] = crawl_stats
        pool |= new_from_crawl
        save_json_set(KNOWN_PLAYERS_FILE, pool)

    except RateLimitError as exc:
        print()
        print(f"[RATE LIMIT] {exc}")
        print("Breche Skript sofort ab und speichere den bisherigen Stand. "
              "Naechster Lauf macht hier weiter.")

    save_json_set(KNOWN_PLAYERS_FILE, pool)
    save_json_set(KNOWN_TOURNAMENTS_FILE, known_tournaments)
    leaderboard["counts"] = counts
    leaderboard["last_checked"] = last_checked
    leaderboard["updated_at"] = now_iso()
    save_leaderboard(leaderboard)
    write_top10_snapshot(counts)
    maybe_live_push(force=True)

    elapsed = time.time() - run_start
    new_players_total = len(pool - known_players)

    print_header("ZUSAMMENFASSUNG DIESES LAUFS")
    print_stat("Laufzeit", format_duration(elapsed))
    print_stat("Spieler-Pool vorher -> nachher", f"{len(known_players)} -> {len(pool)} "
               f"(+{new_players_total})")
    print_stat("Neue Partien-Counts (nie geprueft)", overall_stats["new"])
    print_stat("Aktualisierte Counts (Cooldown abgelaufen)",
               overall_stats["checked"] - overall_stats["new"])
    print_stat("Uebersprungen wg. Cooldown", overall_stats["skipped_cooldown"])
    print_stat("Fehlgeschlagene Abfragen", overall_stats["failed"])
    print_stat("Crawl-Seeds in diesem Lauf", overall_stats["seeds_crawled"])
    print_stat("Spieler insgesamt im Leaderboard", len(counts))

    print_top(counts)
    print()
    print("Fertig.")


if __name__ == "__main__":
    main()
