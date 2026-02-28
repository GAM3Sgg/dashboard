#!/usr/bin/env python3
"""
Send GAM3S.GG Insights report to Telegram.
Can be run standalone (scheduled task) or imported.
"""

import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

# Telegram config
BOT_TOKEN = "REDACTED_TOKEN"
CHAT_ID = "1881550684"
MAX_MSG_LEN = 4000  # Telegram limit is 4096, leave buffer


def send_telegram(text: str, parse_mode: str = "Markdown"):
    """Send a message via Telegram Bot API. Splits long messages automatically."""
    chunks = split_message(text)
    for chunk in chunks:
        data = urllib.parse.urlencode({
            'chat_id': CHAT_ID,
            'text': chunk,
            'parse_mode': parse_mode,
            'disable_web_page_preview': 'true',
        }).encode('utf-8')
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        req = urllib.request.Request(url, data=data)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            if not result.get('ok'):
                print(f"Telegram API error: {result}")
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            # Try again without parse_mode in case of formatting issues
            data = urllib.parse.urlencode({
                'chat_id': CHAT_ID,
                'text': chunk,
                'disable_web_page_preview': 'true',
            }).encode('utf-8')
            req = urllib.request.Request(url, data=data)
            try:
                urllib.request.urlopen(req, timeout=30)
            except Exception as e2:
                print(f"Fallback send also failed: {e2}")


def split_message(text: str) -> list:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= MAX_MSG_LEN:
        return [text]

    chunks = []
    current = ""
    # Split by double newlines (sections) first
    sections = text.split('\n\n')
    for section in sections:
        if len(current) + len(section) + 2 <= MAX_MSG_LEN:
            current = current + '\n\n' + section if current else section
        else:
            if current:
                chunks.append(current.strip())
            # If a single section is too long, split by single newlines
            if len(section) > MAX_MSG_LEN:
                lines = section.split('\n')
                current = ""
                for line in lines:
                    if len(current) + len(line) + 1 <= MAX_MSG_LEN:
                        current = current + '\n' + line if current else line
                    else:
                        if current:
                            chunks.append(current.strip())
                        current = line
            else:
                current = section
    if current:
        chunks.append(current.strip())
    return chunks


def main():
    print("Generating GAM3S.GG insights report...")

    # Import and run the insights generator
    sys.path.insert(0, str(Path(__file__).parent))
    from gam3s_insights import GAM3SInsights

    # Pass --monthly or --30d to include 30-day section
    monthly = any(f in sys.argv for f in ('--monthly', '--30d'))

    try:
        insights = GAM3SInsights()
        message = insights.build_report(include_30d=monthly)

        # Save to file
        output_file = Path(__file__).parent / "insights_output.txt"
        output_file.write_text(message, encoding="utf-8")
        print(f"Report saved to {output_file}")

        # Send to Telegram
        print("Sending to Telegram...")
        send_telegram(message)
        print("Sent successfully!")

    except Exception as e:
        error_msg = f"⚠️ GAM3S.GG Insights failed:\n{e}"
        print(error_msg)
        send_telegram(error_msg, parse_mode="")
        raise


if __name__ == "__main__":
    main()
