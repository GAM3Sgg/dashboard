#!/usr/bin/env python3
"""
Shared Telegram Bot API sender — used by all report senders.
Loads credentials from ~/.openclaw/credentials/telegram-bot.json
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

CREDS_FILE = Path.home() / ".openclaw" / "credentials" / "telegram-bot.json"
with open(CREDS_FILE, "r", encoding="utf-8") as _f:
    _creds = json.load(_f)
BOT_TOKEN = _creds["bot_token"]
CHAT_ID = _creds["chat_id"]
MAX_MSG_LEN = 4000


def send_telegram(text: str, parse_mode: str = "HTML"):
    """Send a message via Telegram Bot API with retry and chunking."""
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
                    if parse_mode and 'parse' in str(result).lower():
                        plain_params = {
                            'chat_id': CHAT_ID,
                            'text': chunk,
                            'disable_web_page_preview': 'true',
                        }
                        plain_data = urllib.parse.urlencode(plain_params).encode('utf-8')
                        plain_req = urllib.request.Request(url, data=plain_data)
                        urllib.request.urlopen(plain_req, timeout=30)
                break
            except Exception as e:
                print(f"Telegram send attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2)
        time.sleep(0.5)


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
