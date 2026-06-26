"""Start coordinator and all three party services."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / ".secure_agg_pids.json"
LOG_DIR = ROOT / "logs"
SERVICES = [
    ("coordinator", ["-m", "secure_agg.cli.coordinator", "--config", "configs/coordinator.json"], "http://127.0.0.1:8000/health"),
    ("P1", ["-m", "secure_agg.cli.party", "--config", "configs/party_p1.json"], "http://127.0.0.1:8101/health"),
    ("P2", ["-m", "secure_agg.cli.party", "--config", "configs/party_p2.json"], "http://127.0.0.1:8102/health"),
    ("P3", ["-m", "secure_agg.cli.party", "--config", "configs/party_p3.json"], "http://127.0.0.1:8103/health"),
]


def is_online(url: str) -> bool:
    """Return whether an HTTP health endpoint responds successfully."""
    try:
        with urlopen(url, timeout=1.0) as response:
            return 200 <= response.status < 300
    except URLError:
        return False
    except TimeoutError:
        return False


def wait_online(name: str, url: str, timeout_seconds: float = 10.0) -> None:
    """Wait for one service to come online."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_online(url):
            print(f"{name}: OK")
            return
        time.sleep(0.2)
    raise RuntimeError(f"{name} did not become ready at {url}")


def main() -> None:
    """Start all demo services and write their process IDs."""
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    processes: dict[str, int] = {}
    LOG_DIR.mkdir(exist_ok=True)
    for name, args, health_url in SERVICES:
        if is_online(health_url):
            print(f"{name}: already running")
            continue
        log_file = (LOG_DIR / f"{name.lower()}.log").open("ab")
        process = subprocess.Popen(
            [sys.executable, *args],
            cwd=ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log_file.close()
        processes[name] = process.pid

    if processes:
        existing: dict[str, int] = {}
        if PID_FILE.exists():
            existing = json.loads(PID_FILE.read_text(encoding="utf-8"))
        existing.update(processes)
        PID_FILE.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    for name, _, health_url in SERVICES:
        wait_online(name, health_url)

    print("All services are running.")


if __name__ == "__main__":
    main()
