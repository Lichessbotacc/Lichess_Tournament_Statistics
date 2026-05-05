import time
import threading
import os
from collections import defaultdict

# =========================
# GLOBAL LIVE STATE
# =========================
state = {
    "mvp": defaultdict(float),
    "points": defaultdict(float),
    "games": defaultdict(int),
    "tournaments": defaultdict(str),
    "status": {}
}

lock = threading.Lock()

# =========================
# UPDATE FUNCTIONS (used by all scripts)
# =========================

def update(category, key, value):
    with lock:
        if category in ["mvp", "points"]:
            state[category][key] += value
        elif category == "games":
            state[category][key] += 1
        else:
            state[category][key] = value


def set_status(script, status):
    with lock:
        state["status"][script] = status


# =========================
# RENDER DASHBOARD
# =========================

def clear():
    os.system("clear" if os.name != "nt" else "cls")


def render():
    clear()

    with lock:
        print("⚡ LICHESS LIVE CONTROL CENTER\n")

        # STATUS
        print("📡 SCRIPT STATUS:")
        for k, v in state["status"].items():
            print(f" - {k}: {v}")

        print("\n🏆 MVP LEADERBOARD:")
        for i, (p, v) in enumerate(sorted(state["mvp"].items(), key=lambda x: x[1], reverse=True)[:10], 1):
            print(f"{i}. {p}: {round(v,2)}")

        print("\n💰 POINTS:")
        for i, (p, v) in enumerate(sorted(state["points"].items(), key=lambda x: x[1], reverse=True)[:10], 1):
            print(f"{i}. {p}: {round(v,2)}")

        print("\n🎮 GAMES PLAYED:")
        for i, (p, v) in enumerate(sorted(state["games"].items(), key=lambda x: x[1], reverse=True)[:10], 1):
            print(f"{i}. {p}: {v}")

        print("\n--- LIVE RUNNING ---")


# =========================
# SIMULATION (replace with your scripts)
# =========================

def fake_worker():
    players = ["DarkOnCrack", "Alpha", "Beta", "Gamma"]

    i = 0
    while True:
        p = players[i % len(players)]

        update("mvp", p, 1.5)
        update("points", p, 2)
        update("games", p, 1)

        set_status("mvp_stats", "running")
        set_status("points", "running")

        time.sleep(0.5)
        i += 1


# =========================
# DASHBOARD LOOP
# =========================

def dashboard_loop():
    while True:
        render()
        time.sleep(1)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    t1 = threading.Thread(target=fake_worker, daemon=True)
    t2 = threading.Thread(target=dashboard_loop, daemon=True)

    t1.start()
    t2.start()

    while True:
        time.sleep(10)
