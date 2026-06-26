"""Stop services started by scripts/start_all.py."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import time


ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / ".secure_agg_pids.json"


def main() -> None:
    """Terminate recorded demo service processes."""
    if not PID_FILE.exists():
        print("No PID file found.")
        return

    pids = json.loads(PID_FILE.read_text(encoding="utf-8"))
    for name, pid in pids.items():
        try:
            os.kill(int(pid), signal.SIGTERM)
            print(f"{name}: stopped")
        except ProcessLookupError:
            print(f"{name}: not running")

    time.sleep(0.5)
    PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
