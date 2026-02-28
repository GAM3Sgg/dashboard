#!/usr/bin/env python3
"""
Send Gaming Trends report to Telegram.
Can be run standalone (scheduled task) or imported.
"""

import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

CREDS_FILE = Path.home() / ".openclaw" / "credentials" / "telegram-bot.json"
with open(CREDS_FILE, "r", encoding="utf-8") as _f:
    _creds = json.load(_f)
BOT_TOKEN = _creds["bot_token"]
CHAT_ID = _creds["chat_id"]

def send_telegram(text, parse_mode="HTML"):
    """Send a message via Telegram Bot API with retry."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                # Fallback: try without parse_mode
                if parse_mode:
                    return send_telegram(text, parse_mode=None)
                raise e

def split_message(text, max_len=4000):
    """Split message into Telegram-safe chunks."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""

    # Split by double-newline (section boundaries)
    sections = text.split("\n\n")
    for section in sections:
        if len(current) + len(section) + 2 > max_len:
            if current:
                chunks.append(current.strip())
                current = ""
            # If single section is too long, split by line
            if len(section) > max_len:
                lines = section.split("\n")
                for line in lines:
                    if len(current) + len(line) + 1 > max_len:
                        if current:
                            chunks.append(current.strip())
                        current = line + "\n"
                    else:
                        current += line + "\n"
            else:
                current = section + "\n\n"
        else:
            current += section + "\n\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks

if __name__ == "__main__":
    try:
        mode = "daily"
        if "--weekly" in sys.argv:
            mode = "weekly"
        elif "--monthly" in sys.argv:
            mode = "monthly"

        sys.path.insert(0, str(Path(__file__).parent))
        from gaming_trends import build_report

        print(f"Building {mode} gaming trends report...", file=sys.stderr)
        report = build_report(mode)

        # Save to file
        output_file = Path(__file__).parent / "gaming_trends_output.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        # Send to Telegram
        chunks = split_message(report)
        print(f"Sending {len(chunks)} message(s) to Telegram...", file=sys.stderr)
        for i, chunk in enumerate(chunks):
            send_telegram(chunk)
            if i < len(chunks) - 1:
                time.sleep(0.5)

        print("Done!", file=sys.stderr)

    except Exception as e:
        error_msg = f"Gaming Trends report error: {e}"
        print(error_msg, file=sys.stderr)
        try:
            send_telegram(error_msg, parse_mode=None)
        except:
            pass
        sys.exit(1)
