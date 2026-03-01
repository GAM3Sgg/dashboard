#!/usr/bin/env python3
"""Send Gaming Trends (Twitch + IGDB) report to Telegram."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from telegram_sender import send_telegram


def main():
    mode = "daily"
    if "--weekly" in sys.argv:
        mode = "weekly"
    elif "--monthly" in sys.argv:
        mode = "monthly"

    print(f"Generating Gaming Trends report ({mode})...")
    from gaming_trends import build_report

    try:
        report = build_report(mode)

        output_file = Path(__file__).parent / "gaming_trends_output.txt"
        output_file.write_text(report, encoding="utf-8")
        print(f"Report saved to {output_file}")

        print("Sending to Telegram...")
        send_telegram(report)
        print("Sent successfully!")
    except Exception as e:
        error_msg = f"Gaming Trends report failed:\n{e}"
        print(error_msg)
        send_telegram(error_msg, parse_mode="")
        raise


if __name__ == "__main__":
    main()
