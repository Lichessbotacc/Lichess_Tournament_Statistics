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
  4. SNOWBALL-CRAWL ueber die Partien-Gegner ("Lobby"-Ausbreitung):
     Von einer kleinen Stichprobe bereits bekannter Spieler werden die
     letzten paar Partien angeschaut und ALLE Gegner daraus (egal ob aus
     Turnier oder normaler "Lobby"-Partie) neu in den Pool aufgenommen.
     Diese neuen Spieler werden beim naechsten Lauf ihrerseits als Seeds
     verwendet - der Pool waechst dadurch ueber viele Laeufe hinweg
     komplett unabhaengig von Turnieren/Teams, einfach entlang des
     "wer hat gegen wen gespielt"-Graphen. Siehe Abschnitt
     "SNOWBALL-CRAWL" weiter unten fuer Details.

Da alle 6 Stunden neue/andere Turniere sichtbar sind, zusaetzlich die
komplette Team-Turnierhistorie durchsucht wird und obendrein der
Snowball-Crawl den Partien-Gegnern folgt, sammelt sich der Pool ueber
Tage/Wochen zu vielen Tausend erfassten aktiven Spielern an - weit mehr
als nur die 200 staerksten nach Rating.

-------------------------------------------------------------------
LIVE-RANKING WAEHREND DER SUCHE
-------------------------------------------------------------------
Das Skript wartet NICHT, bis der komplette Spieler-Pool gesammelt ist,
bevor es Partien zaehlt. Stattdessen wird JEDE Quelle (Top-Liste, jedes
einzelne Turnier, jedes Team, jeder Crawl-Schritt) sofort nach dem
Einlesen verarbeitet: neu gefundene bzw. noch nicht in dieser Laufzeit
aktualisierte Spieler werden direkt danach auf ihre Blitz-Partien-Zahl
der letzten SINCE_DAYS Tage geprueft, das Leaderboard wird sofort
aktualisiert und bei einem Top-100-Einstieg erscheint sofort ein
auffaelliger Banner - man muss also nicht auf das Ende des gesamten
Laufs warten, um zu sehen, wer gerade aktiv ist.

-------------------------------------------------------------------
SNOWBALL-CRAWL (Gegner-basierte Pool-Erweiterung)
-------------------------------------------------------------------
Zusaetzlich zu Turnieren/Teams/Top-Liste wird der Pool ueber die
Partien-Historie einzelner Spieler erweitert - das funktioniert
unabhaengig davon, ob jemand je an einem Turnier teilgenommen hat:

  - CRAWL_QUEUE_FILE enthaelt eine FIFO-Warteschlange von Usernamen,
    deren Gegner noch nicht ausgelesen wurden.
  - KNOWN_CRAWLED_FILE merkt sich, wer schon "ausgecrawlt" wurde, damit
    niemand mehrfach abgefragt wird.
  - Pro Lauf werden bis zu CRAWL_SEED_COUNT Spieler aus der Queue
    genommen (ist die Queue leer, wird stattdessen zufaellig aus dem
    bestehenden Pool aufgefuellt, die noch nicht gecrawlt sind).
  - Fuer jeden Seed werden die letzten CRAWL_GAMES_PER_SEED Partien
    (per /api/games/user/{name}, gefiltert auf PERF_TYPE) angesehen und
    BEIDE Spielernamen (weiss/schwarz) extrahiert - unabhaengig davon,
    ob die Partie aus einem Turnier oder einer normalen "Lobby"-Partie
    stammt.
  - Neue Gegner werden sofort live verarbeitet (Partien gezaehlt,
    Leaderboard aktualisiert) UND ans Ende der Crawl-Queue gehaengt,
    damit sie in einem spaeteren Lauf selbst als Seeds dienen.

Dadurch waechst der Pool ueber viele Laeufe hinweg komplett entlang des
"Wer hat gegen wen gespielt"-Graphen weiter - theoretisch unbegrenzt,
begrenzt praktisch nur durch die Anzahl der Laeufe * CRAWL_SEED_COUNT.
Die Rate pro einzelnem Lauf ist bewusst klein gehalten (ein paar Dutzend
zusaetzliche API-Calls), damit ein einzelner Lauf nicht explodiert -
das Wachstum passiert ueber die Zeit, nicht in einem einzigen Durchlauf.

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

CRAWL_SEED_COUNT: Wie viele Spieler pro Lauf als Ausgangspunkt fuer den
Snowball-Crawl genutzt werden (Standard: 10).

CRAWL_GAMES_PER_SEED: Wie viele der letzten Partien pro Seed-Spieler
angesehen werden, um Gegner zu extrahieren (Standard: 10).

REQUEST_DELAY_SECONDS: Pause zwischen einzelnen API-Aufrufen, um das
Lichess-Rate-Limit nicht zu reissen.

Sobald Lichess mit HTTP 429 antwortet, wartet das Skript automatisch
(Exponential-Backoff) und versucht es danach erneut - siehe Abschnitt
RATE-LIMIT-HANDLING weiter unten. Nur wenn ueber sehr lange Zeit
durchgehend 429 kommt, gibt das Skript fuer DIESEN Lauf auf und speichert
vorher alles bisher Ermittelte (Pool, Crawl-Queue UND Leaderboard-Stand).
Der naechste geplante Lauf (z.B. in 6 Stunden) macht dort weiter, wo
aufgehoert wurde.

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

# ---------------------------------------------------------------------------
# SPIELMODUS / VARIANTE AUSWAEHLEN
# ---------------------------------------------------------------------------
# Ueber die Umgebungsvariable PERF_TYPE (oder als Default hier direkt im
# Code) waehlst du aus, welchen Modus das Skript trackt. Alles andere im
# Skript verhaelt sich exakt gleich - nur Bedenkzeit-Filter, API-Parameter
# und Ausgabe-Ordner passen sich automatisch an.
#
# Erlaubte Werte:
#   - Bedenkzeit-basiert (klassische Zeitkontrollen):
#       "ultraBullet", "bullet", "blitz", "rapid", "classical"
#   - Varianten (eigene Regeln, unabhaengig von der Bedenkzeit):
#       "chess960", "crazyhouse", "antichess", "atomic", "horde",
#       "kingOfTheHill", "racingKings", "threeCheck"
#
# Beispiel lokal:      PERF_TYPE=rapid python3 most_active_blitz_players.py
# Beispiel in Actions: env: PERF_TYPE: rapid  (siehe Workflow-Datei)
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
    """
    Ordnet eine geschaetzte Partiedauer (limit + 40*increment, in Sekunden)
    einer Lichess-Bedenkzeit-Kategorie zu - dieselbe Formel/Schwellenwerte,
    die auch Lichess selbst zur Klassifizierung verwendet. Wird gebraucht,
    weil Swiss-Turniere (anders als Arenen) keinen direkten "perf"-Schluessel
    mitliefern, sondern nur clock.limit/clock.increment.
    """
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
    """
    Prueft, ob ein Swiss-Turnier zum aktuell gewaehlten PERF_TYPE passt.
    Bei Bedenkzeit-basierten Typen (blitz, rapid, ...) muss die Variante
    "standard" sein und die Bedenkzeit in die passende Kategorie fallen.
    Bei echten Varianten (atomic, chess960, ...) muss variant.key exakt
    dem PERF_TYPE entsprechen - die Bedenkzeit spielt dann keine Rolle.
    """
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


# Zusaetzliche Teams, deren Mitglieder ebenfalls in den Spieler-Pool
# aufgenommen werden sollen (Team-Slugs, klein geschrieben). Kann leer sein.
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

# --- Snowball-Crawl (Gegner-basierte, "unendliche" Pool-Erweiterung) -------
# Wie viele Spieler pro Lauf als neue Seeds fuer den Gegner-Crawl genutzt
# werden. Bewusst klein gehalten, damit ein einzelner Lauf nicht explodiert
# (das Wachstum passiert ueber viele Laeufe hinweg, siehe Docstring oben).
CRAWL_SEED_COUNT = 10

# Wie viele der letzten Partien pro Seed-Spieler angesehen werden, um
# Gegner zu extrahieren.
CRAWL_GAMES_PER_SEED = 10

# ---------------------------------------------------------------------------
# WICHTIG: Alle Ausgabe-Ordner/-Dateien werden bewusst NICHT relativ zum
# aktuellen Arbeitsverzeichnis (CWD) angelegt, sondern relativ zum eigenen
# Speicherort dieser Datei. Grund: je nachdem, wie genau der GitHub-Actions-
# Workflow das Skript aufruft (z.B. "python3 scripts/auto/datei.py" aus dem
# Repo-Root vs. mit gesetztem working-directory), kann sich das CWD
# unterscheiden - und die Ordner tauchten dann mal hier, mal dort auf oder
# schienen "gar nicht erstellt" zu werden.
#
# Stattdessen: dieses Skript liegt unter <repo>/scripts/auto/dieses_skript.py
# -> zwei Verzeichnisse hoch = Repo-Root. Dort (und NICHT im scripts-Ordner)
# werden data/<perf_type>/ und status/<perf_type>/ IMMER angelegt, egal von
# wo aus das Skript gestartet wird.
#
# JEDER PERF_TYPE BEKOMMT SEINEN EIGENEN ORDNER: Wechselst du z.B. von
# "blitz" auf "rapid", legt das Skript automatisch data/rapid/ und
# status/rapid/ an - die bestehenden blitz-Daten unter data/blitz/ und
# status/blitz/ bleiben davon komplett unberuehrt.
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent  # scripts/auto -> scripts -> Repo-Root

DATA_DIR = REPO_ROOT / "data" / PERF_TYPE
KNOWN_PLAYERS_FILE = DATA_DIR / "known_players.json"
LEADERBOARD_FILE = DATA_DIR / "leaderboard.json"
KNOWN_TOURNAMENTS_FILE = DATA_DIR / "known_tournaments.json"

# Neue Dateien fuer den Snowball-Crawl (siehe Docstring-Abschnitt oben).
CRAWL_QUEUE_FILE = DATA_DIR / "crawl_queue.json"
KNOWN_CRAWLED_FILE = DATA_DIR / "known_crawled.json"

# Eigener Ordner (pro PERF_TYPE) fuer den "immer aktuellen" Top-100-
# Schnappschuss. Diese Dateien werden bei JEDEM einzelnen Live-Update
# ueberschrieben, sodass man dort jederzeit (auch waehrend das Skript
# noch laeuft) den aktuellen Stand sehen kann - unabhaengig von der
# Konsolen-/Log-Ausgabe, die z.B. in GitHub Actions nach dem Lauf schnell
# unuebersichtlich wird.
STATUS_DIR = REPO_ROOT / "status" / PERF_TYPE
TOP10_JSON_FILE = STATUS_DIR / "top100.json"
TOP10_MD_FILE = STATUS_DIR / "top100.md"
TOP_N_LIVE = 100

# ---------------------------------------------------------------------------
# LIVE GIT PUSH
# ---------------------------------------------------------------------------
# Nur automatisch committen/pushen, wenn wir tatsaechlich in einer GitHub
# Action laufen (dort ist GITHUB_ACTIONS=true gesetzt). Bei einem lokalen
# Testlauf soll NICHT versucht werden, ins Repo zu pushen.
LIVE_GIT_PUSH = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"

# Mindestabstand zwischen zwei Live-Pushes. Ohne diesen Deckel wuerde bei
# JEDEM einzelnen verarbeiteten Spieler ein eigener Commit+Push passieren -
# das waeren potenziell hunderte Mini-Commits pro Lauf. Mit dem Deckel gibt
# es trotzdem regelmaessig (alle ~30s) einen Push WAEHREND das Skript noch
# rechnet, nicht erst ganz am Ende.
GIT_PUSH_MIN_INTERVAL_SECONDS = 30
_last_git_push_ts = 0.0

# Da bis zu 13 Matrix-Jobs PARALLEL gegen denselben main-Branch pushen
# koennen, kollidieren gelegentlich zwei Pushes ("cannot lock ref" /
# "remote rejected", weil zwischen deinem "pull --rebase" und deinem
# "push" ein anderer Job schneller war). Das ist normal bei parallelen
# Pushes und kein Bug - deshalb: bei einem fehlgeschlagenen Push einfach
# erneut "pull --rebase" + "push" versuchen, mit kurzer zufaelliger
# Wartezeit dazwischen (verhindert, dass mehrere Jobs immer wieder exakt
# gleichzeitig erneut versuchen).
GIT_PUSH_MAX_RETRIES = 8
GIT_PUSH_RETRY_BASE_DELAY_SECONDS = 3


def ensure_on_branch() -> None:
    """
    Sicherheitsnetz gegen "You are not currently on a branch": Falls der
    Checkout (aus welchem Grund auch immer) im detached HEAD gelandet ist,
    wechselt diese Funktion explizit auf den Branch, der laut GitHub-
    Actions-Umgebungsvariable GITHUB_REF_NAME aktuell laeuft (z.B. "main").
    Ohne echten Branch koennen "git pull --rebase" und "git push" nicht
    wissen, wogegen sie arbeiten sollen.
    """
    check = subprocess.run(
        ["git", "symbolic-ref", "-q", "HEAD"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if check.returncode == 0:
        return  # wir sind schon auf einem echten Branch

    branch = os.environ.get("GITHUB_REF_NAME") or "main"
    print(f"  [GIT] Detached HEAD erkannt - wechsle explizit auf Branch '{branch}'...")
    subprocess.run(
        ["git", "checkout", "-B", branch, f"origin/{branch}"],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    )


def git_commit_and_push(message: str) -> bool:
    """
    Committet und pusht status/ + die Tracking-Dateien direkt aus dem
    laufenden Skript heraus. Dadurch aktualisiert sich das Ranking im
    Repo schon WAEHREND das Skript noch rechnet - nicht erst danach in
    einem separaten Workflow-Schritt.
    """
    if not LIVE_GIT_PUSH:
        return False
    try:
        ensure_on_branch()

        # Nur Pfade zum "git add" geben, die tatsaechlich existieren.
        # Manche Dateien werden erst im Laufe des Skripts geschrieben -
        # wuerden sie hier trotzdem gelistet, obwohl sie noch nicht
        # existieren, bricht "git add" mit "did not match any files" fuer
        # den GESAMTEN Aufruf ab (auch fuer status/, das eigentlich schon
        # da waere).
        candidate_paths = [
            STATUS_DIR, KNOWN_PLAYERS_FILE, KNOWN_TOURNAMENTS_FILE,
            LEADERBOARD_FILE, CRAWL_QUEUE_FILE, KNOWN_CRAWLED_FILE,
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
            return False  # nichts hat sich geaendert

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        )

        # pull --rebase + push mit Retry: bei parallelen Matrix-Jobs kann
        # das push kollidieren ("cannot lock ref" / "remote rejected"),
        # weil ein anderer Job zwischen unserem pull und unserem push
        # etwas anderes gepusht hat. Das ist normal bei paralleler
        # Nutzung desselben Branches - einfach erneut pull+push statt
        # aufzugeben.
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
                    # Exponentiell wachsende Wartezeit + Zufalls-Jitter,
                    # damit nicht alle kollidierenden Jobs exakt
                    # gleichzeitig erneut versuchen.
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
    """
    Throttled Aufruf von git_commit_and_push. 'force=True' erzwingt den
    Push unabhaengig vom letzten Zeitpunkt - genutzt ganz am Anfang (damit
    der Ordner sofort im Repo sichtbar wird) und ganz am Ende des Laufs.
    """
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
# HTTP HELPERS
# ---------------------------------------------------------------------------
# Bei einem Rate Limit (HTTP 429) soll das Skript NICHT mehr abbrechen,
# sondern automatisch warten und es danach einfach erneut versuchen - das
# Skript soll durchlaufen (24/7-Cron), nicht bei jedem 429 aufgeben.
#
# RATE_LIMIT_INITIAL_BACKOFF_SECONDS: Start-Wartezeit, falls Lichess keinen
#   "Retry-After"-Header mitschickt.
# RATE_LIMIT_MAX_BACKOFF_SECONDS: Deckel, damit die Wartezeit bei
#   wiederholten 429s nicht ins Unermessliche waechst (Exponential-Backoff,
#   verdoppelt sich bei jedem weiteren 429, aber nie mehr als dieser Wert).
# RATE_LIMIT_MAX_TOTAL_WAIT_SECONDS: Absolutes Sicherheitsnetz PRO
#   Einzelanfrage - falls Lichess ueber so lange Zeit (Summe aller
#   Wartezeiten fuer diese eine Anfrage) durchgehend 429 zurueckgibt, gibt
#   das Skript fuer DIESEN Lauf auf (speichert alles) statt endlos zu
#   haengen und damit das GitHub-Actions-Zeitlimit des Jobs zu verschwenden.
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(values), indent=2))


def load_json_list(path: Path) -> list:
    """Wie load_json_set, aber ordnungserhaltend (fuer die FIFO-Queue)."""
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
    """
    Speichert das Leaderboard. Neben den rohen "counts" (unsortiertes
    username -> Anzahl-Dict, das ist die eigentliche Speicherform) wird
    zusaetzlich ein sortiertes "ranking"-Feld mit Lichess-Profil-Links
    mitgespeichert, damit man auch direkt in blitz_leaderboard.json eine
    fertig sortierte Rangliste sieht, statt nur das rohe Dict.
    """
    counts = leaderboard.get("counts", {})
    ranking = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    leaderboard["ranking"] = [
        {"rank": i, "username": name, "games": cnt, "profile": profile_url(name)}
        for i, (name, cnt) in enumerate(ranking, start=1)
    ]
    LEADERBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_FILE.write_text(json.dumps(leaderboard, indent=2, sort_keys=True, ensure_ascii=False))


# ---------------------------------------------------------------------------
# TURNIERE FINDEN (aktuell sichtbar + Team-Historie, NUR Blitz)
# ---------------------------------------------------------------------------
def get_visible_blitz_tournament_ids() -> list:
    """
    Holt aktuell sichtbare offizielle Turniere (erstellt/laufend/kuerzlich
    beendet) und filtert auf den aktuell gewaehlten PERF_TYPE. Liefert
    Liste von (id, "arena")-Tupeln. Das ist nur eine Momentaufnahme -
    siehe get_team_tournament_ids fuer zusaetzliche, auch vergangene
    Turniere.
    """
    print(f"Suche aktuell sichtbare {PERF_TYPE}-Arenen...")
    try:
        data = fetch_json(f"{BASE_URL}/api/tournament")
    except (RateLimitError, urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"  [WARNUNG] Turnierliste konnte nicht geladen werden: {exc}")
        return []

    ids = []
    for bucket in ("finished", "started", "created"):
        for t in data.get(bucket, []):
            perf = t.get("perf", {})
            perf_key = perf.get("key") if isinstance(perf, dict) else None
            if perf_key == PERF_TYPE and t.get("id"):
                ids.append((t["id"], "arena"))

    print(f"  {len(ids)} {PERF_TYPE}-Arena(n) gefunden.")
    return ids


def get_team_tournament_ids(team_id: str) -> list:
    """
    Holt die komplette Arena- UND Swiss-Turnierhistorie eines Teams
    (auch VERGANGENE, bereits laengst beendete Turniere - anders als
    /api/tournament, das nur die aktuelle Momentaufnahme zeigt) und
    filtert auf den aktuell gewaehlten PERF_TYPE. Liefert Liste von
    (id, "arena"/"swiss")-Tupeln.
    """
    found = []

    # Arena-Turniere des Teams
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
        print(f"  [WARNUNG] Arena-Historie von Team '{team_id}' nicht ladbar: {exc}")

    # Swiss-Turniere des Teams. Swiss-Turniere haben anders als Arenen
    # KEIN direktes "perf"-Feld - die Zuordnung passiert ueber
    # swiss_matches_perf_type() (Bedenkzeit-Formel bzw. Variantenname,
    # je nachdem was PERF_TYPE gerade ist).
    url = f"{BASE_URL}/api/team/{team_id}/swiss?max={MAX_TEAM_TOURNAMENTS}"
    try:
        for row in fetch_ndjson(url):
            if swiss_matches_perf_type(row) and row.get("id"):
                found.append((row["id"], "swiss"))
    except RateLimitError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
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
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
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
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"  [WARNUNG] Mitglieder von Team '{team_id}' nicht ladbar: {exc}")
    print(f"  {len(users)} Mitglieder gefunden.")
    return users


def get_top_blitz_players() -> set:
    print(f"Hole Top-200 {PERF_TYPE}-Spieler nach Rating...")
    try:
        data = fetch_json(f"{BASE_URL}/api/player/top/200/{PERF_TYPE}")
        users = {u["username"].lower() for u in data.get("users", [])}
        print(f"  {len(users)} Spieler aus Top-Liste.")
        return users
    except (RateLimitError, urllib.error.URLError, urllib.error.HTTPError, OSError, KeyError) as exc:
        print(f"  [WARNUNG] Top-Liste konnte nicht geladen werden: {exc}")
        return set()


# ---------------------------------------------------------------------------
# SNOWBALL-CRAWL: Gegner aus den letzten Partien eines Spielers extrahieren
# ---------------------------------------------------------------------------
def get_recent_opponents(username: str, limit: int) -> set:
    """
    Holt die letzten 'limit' Partien von 'username' (gefiltert auf den
    aktuell gewaehlten PERF_TYPE - egal ob Turnier- oder normale
    "Lobby"-Partie) und liefert die Menge der GEGNER-Usernamen (klein
    geschrieben). Das ist der Kern des Snowball-Crawls: so werden auch
    Spieler gefunden, die nie an einem oeffentlichen Turnier teilgenommen
    haben, aber gegen jemanden aus dem Pool gespielt haben.
    """
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
        print(f"  [WARNUNG] Partien-Gegner von '{username}' nicht ladbar: {exc}")
    return opponents


def pick_crawl_seeds(queue: list, known_crawled: set, pool: set) -> list:
    """
    Waehlt bis zu CRAWL_SEED_COUNT Spieler aus, deren Gegner in diesem Lauf
    ausgelesen werden sollen. Zuerst wird die FIFO-Queue bedient (das sind
    Spieler, die in einem frueheren Lauf als NEUE Gegner gefunden, aber
    noch nicht selbst gecrawlt wurden). Ist die Queue leer (z.B. ganz am
    Anfang, bevor ueberhaupt gecrawlt wurde), wird der bestehende Pool als
    Startpunkt genutzt.
    """
    seeds = []
    remaining_queue = list(queue)

    while remaining_queue and len(seeds) < CRAWL_SEED_COUNT:
        candidate = remaining_queue.pop(0)
        if candidate not in known_crawled:
            seeds.append(candidate)

    if len(seeds) < CRAWL_SEED_COUNT:
        fallback_candidates = list(pool - known_crawled - set(seeds))
        random.shuffle(fallback_candidates)
        for candidate in fallback_candidates:
            if len(seeds) >= CRAWL_SEED_COUNT:
                break
            seeds.append(candidate)

    return seeds, remaining_queue


def run_snowball_crawl(pool: set, updated_this_run: set, counts: dict,
                        since_ms: int, leaderboard: dict) -> set:
    """
    Fuehrt einen Crawl-Schritt aus: waehlt Seeds, holt deren Partien-Gegner,
    nimmt neue Gegner in den Pool auf, verarbeitet sie sofort live (Zaehlen
    + Leaderboard-Update) und haengt sie ans Ende der Crawl-Queue, damit sie
    in einem spaeteren Lauf selbst als Seeds dienen. Gibt die Menge aller
    NEU gefundenen Spieler zurueck (fuer das Pool-Speichern im Aufrufer).
    """
    queue = load_json_list(CRAWL_QUEUE_FILE)
    known_crawled = load_json_set(KNOWN_CRAWLED_FILE)

    seeds, remaining_queue = pick_crawl_seeds(queue, known_crawled, pool)
    if not seeds:
        print("Snowball-Crawl: keine Seeds verfuegbar (Pool noch leer?), ueberspringe.")
        return set()

    print(f"Snowball-Crawl: {len(seeds)} Seed-Spieler, hole je die letzten "
          f"{CRAWL_GAMES_PER_SEED} Partien und extrahiere Gegner...")

    all_new_opponents = set()
    for seed in seeds:
        time.sleep(REQUEST_DELAY_SECONDS)
        opponents = get_recent_opponents(seed, CRAWL_GAMES_PER_SEED)
        new_opponents = opponents - pool
        if new_opponents:
            print(f"  '{seed}': {len(opponents)} Gegner gefunden "
                  f"({len(new_opponents)} davon neu im Pool).")

        all_new_opponents |= new_opponents
        pool |= opponents
        known_crawled.add(seed)

        # Neue Gegner sofort live verarbeiten (zaehlen + Leaderboard) UND
        # ans Ende der Queue haengen, damit sie spaeter selbst als Seeds
        # dienen und ihrerseits Gegner liefern - das ist der eigentliche
        # "Schneeball"-Effekt.
        update_players_live(opponents, updated_this_run, counts, since_ms, leaderboard)
        for name in sorted(new_opponents):
            if name not in remaining_queue and name not in known_crawled:
                remaining_queue.append(name)

        save_json_list(CRAWL_QUEUE_FILE, remaining_queue)
        save_json_set(KNOWN_CRAWLED_FILE, known_crawled)
        save_json_set(KNOWN_PLAYERS_FILE, pool)

    print(f"Snowball-Crawl abgeschlossen: {len(all_new_opponents)} neue Spieler "
          f"insgesamt gefunden. Neue Queue-Laenge: {len(remaining_queue)}.")
    return all_new_opponents


# ---------------------------------------------------------------------------
# PARTIEN ZAEHLEN (nur der gewaehlte PERF_TYPE, egal aus welchem Turnier
# der Spieler urspruenglich kam)
# ---------------------------------------------------------------------------
def count_recent_blitz_games(username: str, since_ms: int) -> int:
    """
    Zaehlt NUR Partien des aktuell gewaehlten PERF_TYPE eines Spielers seit
    since_ms (gedeckelt). perfType=<PERF_TYPE> sorgt dafuer, dass
    ausschliesslich passende Partien gezaehlt werden - unabhaengig davon,
    ob der Spieler urspruenglich aus einer Arena, einem Swiss-Turnier, der
    Top-Liste oder dem Snowball-Crawl stammt.
    """
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
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
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
        f"# Top {TOP_N_LIVE} aktivste {PERF_TYPE}-Spieler (letzte {SINCE_DAYS} Tage)",
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
    print(f"  TOP {n} AKTIVSTE {PERF_TYPE.upper()}-SPIELER (letzte {SINCE_DAYS} Tage)")
    print("=" * 70)
    for i, (name, cnt) in enumerate(ranking, start=1):
        print(f"  {i:>3}. {name:<20} {cnt:>5} Partien   {profile_url(name)}")
    print("=" * 70)
    return ranking


def update_players_live(usernames: set, already_updated: set, counts: dict,
                         since_ms: int, leaderboard: dict) -> None:
    """
    Zentrale Live-Funktion: bekommt eine Menge frisch gefundener Spieler
    (z.B. Teilnehmer eines einzelnen gerade eingelesenen Turniers oder neue
    Gegner aus dem Snowball-Crawl), zaehlt fuer alle noch nicht in diesem
    Lauf aktualisierten Spieler sofort die Blitz-Partien, aktualisiert das
    Leaderboard SOFORT (inkl. Speichern auf Platte) und zeigt bei
    Top-100-Neueinsteigern direkt einen Banner.

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
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
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

        # Throttled Live-Push: pusht regelmaessig (alle ~30s) waehrend das
        # Skript noch rechnet, nicht erst am Ende des kompletten Laufs.
        maybe_live_push()


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
    print(f"Crawl-Queue-Laenge: {len(load_json_list(CRAWL_QUEUE_FILE))}")
    print(f"Bereits gecrawlte Spieler (Gegner ausgelesen): {len(load_json_set(KNOWN_CRAWLED_FILE))}")
    print("=" * 70)

    leaderboard = load_leaderboard()
    counts = leaderboard.get("counts", {})
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=SINCE_DAYS)).timestamp() * 1000)

    # Sofort ganz am Anfang schreiben, damit status/top100.md/.json IMMER
    # existiert - unabhaengig davon, ob spaeter irgendeine Quelle (Top-
    # Liste, Turniere, Teams, Crawl) leer zurueckkommt oder fehlschlaegt.
    # Ab hier wird die Datei danach bei jedem einzelnen Live-Update
    # ueberschrieben.
    write_top10_snapshot(counts)

    pool = set(known_players)
    updated_this_run = set()  # verhindert Mehrfach-Abfragen im selben Lauf

    # Auch known_players.json/known_tournaments.json schon frueh (leer
    # bzw. mit dem bisherigen Stand) anlegen, damit sie ab der ersten
    # Sekunde existieren - WICHTIG: das muss VOR dem ersten Push passieren,
    # sonst versucht git, einen zu diesem Zeitpunkt noch nicht existierenden
    # Pfad hinzuzufuegen.
    save_json_set(KNOWN_PLAYERS_FILE, pool)
    save_json_set(KNOWN_TOURNAMENTS_FILE, known_tournaments)
    save_json_list(CRAWL_QUEUE_FILE, load_json_list(CRAWL_QUEUE_FILE))
    save_json_set(KNOWN_CRAWLED_FILE, load_json_set(KNOWN_CRAWLED_FILE))

    # ... und erst JETZT, wo alle Dateien garantiert existieren, erzwungen
    # ins Repo pushen, damit der Ordner von der ersten Sekunde an auch
    # tatsaechlich auf GitHub sichtbar ist.
    maybe_live_push(force=True)

    try:
        # 1) Top-200 nach Rating - sofort live verarbeiten
        top_players = get_top_blitz_players()
        pool |= top_players
        save_json_set(KNOWN_PLAYERS_FILE, pool)
        update_players_live(top_players, updated_this_run, counts, since_ms, leaderboard)
        time.sleep(REQUEST_DELAY_SECONDS)

        # 2) Alle erreichbaren PERF_TYPE-Turniere sammeln: aktuell sichtbare +
        #    komplette Team-Historie (auch vergangene Turniere)
        tournament_sources = list(get_visible_blitz_tournament_ids())
        time.sleep(REQUEST_DELAY_SECONDS)

        for team_id in EXTRA_TEAM_IDS:
            print(f"Suche {PERF_TYPE}-Turnierhistorie von Team '{team_id}' (auch vergangene)...")
            team_tournaments = get_team_tournament_ids(team_id.lower())
            print(f"  {len(team_tournaments)} {PERF_TYPE}-Turnier(e) in der Historie gefunden.")
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
            save_json_set(KNOWN_PLAYERS_FILE, pool)
            save_json_set(KNOWN_TOURNAMENTS_FILE, known_tournaments)

        # 4) Zusaetzliche Team-Mitgliederlisten - ebenfalls sofort live
        for team_id in EXTRA_TEAM_IDS:
            time.sleep(REQUEST_DELAY_SECONDS)
            members = get_team_members(team_id.lower())
            pool |= members
            save_json_set(KNOWN_PLAYERS_FILE, pool)
            update_players_live(members, updated_this_run, counts, since_ms, leaderboard)

        # 5) SNOWBALL-CRAWL: von ein paar bekannten Spielern aus die letzten
        #    Partien ansehen und ALLE Gegner (Turnier UND normale
        #    "Lobby"-Partien) neu in den Pool aufnehmen. Waechst ueber
        #    viele Laeufe hinweg unbegrenzt weiter, siehe Docstring oben.
        new_from_crawl = run_snowball_crawl(pool, updated_this_run, counts, since_ms, leaderboard)
        pool |= new_from_crawl
        save_json_set(KNOWN_PLAYERS_FILE, pool)

    except RateLimitError as exc:
        print(f"[RATE LIMIT] {exc}")
        print("Breche Skript sofort ab und speichere den bisherigen Stand "
              "(Spieler-Pool, verarbeitete Turniere, Crawl-Queue und "
              "Leaderboard). Naechster Lauf macht hier weiter (z.B. in 6 "
              "Stunden).")

    # Am Ende (oder bei Abbruch) alles persistieren, was bis dahin
    # ermittelt wurde.
    save_json_set(KNOWN_PLAYERS_FILE, pool)
    save_json_set(KNOWN_TOURNAMENTS_FILE, known_tournaments)
    leaderboard["counts"] = counts
    leaderboard["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_leaderboard(leaderboard)
    write_top10_snapshot(counts)
    # Am Ende (oder bei Abbruch durch Rate Limit) auf jeden Fall erzwungen
    # pushen, damit garantiert der letzte Stand im Repo landet.
    maybe_live_push(force=True)

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
