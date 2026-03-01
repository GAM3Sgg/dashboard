#!/usr/bin/env python3
"""Send CheapShark Deals report to Telegram."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from telegram_sender import send_telegram


def main():
    print("Generating CheapShark Deals report...")
    from cheapshark_deals import build_report

    try:
        report = build_report()
        print("Sending to Telegram...")
        send_telegram(report)
        print("Sent successfully!")
    except Exception as e:
        error_msg = f"CheapShark Deals report failed:\n{e}"
        print(error_msg)
        send_telegram(error_msg, parse_mode="")
        raise


if __name__ == "__main__":
    main()
