import subprocess
import time
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = [
    "mvp_stats.py",
    "points.py",
    "games.py",
    "control_center.py"
]

processes = []

def start_script(script):
    path = os.path.join(BASE_DIR, script)
    return subprocess.Popen([sys.executable, path])

def main():
    print("🚀 Starting Lichess System...\n")

    for script in SCRIPTS:
        print(f"▶ starting {script}")
        p = start_script(script)
        processes.append((script, p))
        time.sleep(0.5)

    print("\n⚡ ALL SYSTEMS RUNNING\n")

    # Watchdog loop (keeps process alive)
    while True:
        for i, (name, p) in enumerate(processes):
            if p.poll() is not None:  # crashed
                print(f"⚠️ {name} crashed → restarting")
                new_p = start_script(name)
                processes[i] = (name, new_p)

        time.sleep(5)

if __name__ == "__main__":
    main()
