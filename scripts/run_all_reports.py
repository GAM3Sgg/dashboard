#!/usr/bin/env python3
"""
Run all gaming reports, send to Telegram, rebuild dashboard, push once.
Replaces individual VBS schedulers that each pushed independently.
Logs results to scripts/logs/ for visibility.
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from telegram_sender import send_telegram

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "report_runs.log"

REPORTS = [
    ("Gaming Trends", "send_gaming_trends_telegram"),
    ("Steam Trending", "send_steam_trending_telegram"),
    ("Epic Free Games", "send_epic_free_telegram"),
    ("CheapShark Deals", "send_cheapshark_telegram"),
]


def log(msg):
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def run_all():
    log("=" * 60)
    log("Starting daily report run")

    results = []
    for name, module_name in REPORTS:
        log(f"Running: {name}")
        try:
            mod = __import__(module_name)
            mod.main()
            results.append((name, True, None))
            log(f"  {name}: OK")
        except Exception as e:
            results.append((name, False, str(e)))
            log(f"  {name}: FAILED — {e}")
            traceback.print_exc()

    # Rebuild dashboard and push
    log("Rebuilding dashboard and pushing...")
    try:
        from build_dashboard import main as build_main
        sys.argv = [sys.argv[0], "--push"]
        build_main()
        results.append(("Dashboard push", True, None))
        log("  Dashboard push: OK")
    except Exception as e:
        results.append(("Dashboard push", False, str(e)))
        log(f"  Dashboard push: FAILED — {e}")

    # Summary
    ok_count = sum(1 for _, ok, _ in results if ok)
    fail_count = sum(1 for _, ok, _ in results if not ok)
    log(f"Done: {ok_count} OK, {fail_count} failed")

    # Trim log to last 500 lines
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) > 500:
            LOG_FILE.write_text("\n".join(lines[-500:]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run_all()
