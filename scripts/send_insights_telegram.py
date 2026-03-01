#!/usr/bin/env python3
"""Send GAM3S.GG Insights report to Telegram."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from telegram_sender import send_telegram


def main():
    print("Generating GAM3S.GG insights report...")
    from gam3s_insights import GAM3SInsights

    monthly = any(f in sys.argv for f in ('--monthly', '--30d'))

    try:
        insights = GAM3SInsights()
        message = insights.build_report(include_30d=monthly)

        output_file = Path(__file__).parent / "insights_output.txt"
        output_file.write_text(message, encoding="utf-8")
        print(f"Report saved to {output_file}")

        print("Sending to Telegram...")
        send_telegram(message)
        print("Sent successfully!")
    except Exception as e:
        error_msg = f"GAM3S.GG Insights failed:\n{e}"
        print(error_msg)
        send_telegram(error_msg, parse_mode="")
        raise


if __name__ == "__main__":
    main()
