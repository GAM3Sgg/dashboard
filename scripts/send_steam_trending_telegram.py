#!/usr/bin/env python3
"""
Send Steam Trending report to Telegram.
Can be run standalone (scheduled task) or imported.
"""

import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

# Telegram config (same as insights)
CREDS_FILE = Path.home() / ".openclaw" / "credentials" / "telegram-bot.json"
with open(CREDS_FILE, "r", encoding="utf-8") as _f:
    _creds = json.load(_f)
BOT_TOKEN = _creds["bot_token"]
CHAT_ID = _creds["chat_id"]
MAX_MSG_LEN = 4000


def send_telegram(text: str, parse_mode: str = "HTML"):
    """Send a message via Telegram Bot API with retry. HTML parse_mode for hyperlinks."""
    import time as _time
    chunks = split_message(text)
    for chunk in chunks:
        params = {
            'chat_id': CHAT_ID,
            'text': chunk,
            'disable_web_page_preview': 'true',
        }
        if parse_mode:
            params['parse_mode'] = parse_mode
        data = urllib.parse.urlencode(params).encode('utf-8')
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        for attempt in range(3):
            req = urllib.request.Request(url, data=data)
            try:
                resp = urllib.request.urlopen(req, timeout=30)
                result = json.loads(resp.read())
                if not result.get('ok'):
                    print(f"Telegram API error: {result}")
                    # If HTML parse failed, retry without parse_mode
                    if parse_mode and 'parse' in str(result).lower():
                        plain_params = {
                            'chat_id': CHAT_ID,
                            'text': chunk,
                            'disable_web_page_preview': 'true',
                        }
                        plain_data = urllib.parse.urlencode(plain_params).encode('utf-8')
                        plain_req = urllib.request.Request(url, data=plain_data)
                        urllib.request.urlopen(plain_req, timeout=30)
                break  # success
            except Exception as e:
                print(f"Telegram send attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    _time.sleep(2)
        _time.sleep(0.5)  # small delay between chunks


def split_message(text: str) -> list:
    if len(text) <= MAX_MSG_LEN:
        return [text]
    chunks = []
    current = ""
    sections = text.split('\n\n')
    for section in sections:
        if len(current) + len(section) + 2 <= MAX_MSG_LEN:
            current = current + '\n\n' + section if current else section
        else:
            if current:
                chunks.append(current.strip())
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
    # Detect mode from args
    mode = "daily"
    if "--weekly" in sys.argv:
        mode = "weekly"
    elif "--monthly" in sys.argv:
        mode = "monthly"

    print(f"Generating Steam Trending report ({mode})...")
    sys.path.insert(0, str(Path(__file__).parent))
    from steam_trending import build_report

    try:
        report = build_report(mode)

        output_file = Path(__file__).parent / "steam_trending_output.txt"
        output_file.write_text(report, encoding="utf-8")
        print(f"Report saved to {output_file}")

        print("Sending to Telegram...")
        send_telegram(report)
        print("Sent successfully!")

    except Exception as e:
        error_msg = f"Steam Trending report failed:\n{e}"
        print(error_msg)
        send_telegram(error_msg, parse_mode="")
        raise


if __name__ == "__main__":
    main()
