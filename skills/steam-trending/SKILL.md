---
name: steam-trending
description: "Run and send the Steam Trending Games daily report. Use when: user asks about Steam trends, trending games, top sellers, most played games, rising games, player counts, Steam charts, what's hot on Steam, or says 'steam report'. NOT for: specific game help, game recommendations, or non-Steam platforms."
metadata: { "openclaw": { "emoji": "🎮" } }
---

# Steam Trending Games Report

Generate and send the Steam Trending Games daily report with player counts, trending, top sellers, rising/falling games, and deals.

## When to Use

✅ **USE this skill when the user says things like:**

- "What's trending on Steam?" / "Steam trends"
- "Send me the Steam report" / "Steam charts"
- "Most played games" / "top sellers" / "what's hot?"
- "Player counts" / "which games are rising?"
- "Any new games blowing up?" / "Steam trending"
- "Steam weekly summary" / "weekly steam recap"
- "Steam monthly summary" / "monthly steam stats"

## How to Run

**Daily report (default):**
```bash
cd C:\Users\User\clawd && set PYTHONIOENCODING=utf-8 && python send_steam_trending_telegram.py
```

**Weekly summary (7-day trends):**
```bash
cd C:\Users\User\clawd && set PYTHONIOENCODING=utf-8 && python send_steam_trending_telegram.py --weekly
```

**Monthly summary (30-day rollup):**
```bash
cd C:\Users\User\clawd && set PYTHONIOENCODING=utf-8 && python send_steam_trending_telegram.py --monthly
```

Generate without sending to Telegram:
```bash
cd C:\Users\User\clawd && set PYTHONIOENCODING=utf-8 && python steam_trending.py
cd C:\Users\User\clawd && set PYTHONIOENCODING=utf-8 && python steam_trending.py --weekly
cd C:\Users\User\clawd && set PYTHONIOENCODING=utf-8 && python steam_trending.py --monthly
```

The report will be:
1. Saved to `C:\Users\User\clawd\steam_trending_output.txt`
2. Sent to OG on Telegram (if using send_steam_trending_telegram.py)

## What It Contains

### Daily Report
- **New & Trending** — top 15 with player counts, % change, genre, [NEW]/[JUST LAUNCHED] badges
- **Top Sellers (Paid)** — paid games with prices and player counts
- **Top Free-to-Play** — F2P games separated
- **Rising / Falling** — biggest player count swings vs yesterday
- **New Entries Today** — games appearing for first time on lists
- **Review Spotlight** — sentiment shifts, highlights (Very Positive+), warnings (Mixed/Negative)
- **Biggest Deals** — top discounts
- **Coming Soon / Unreleased** — upcoming games + unreleased games already trending (pre-orders, early access, demos)
- **Actionable Next Steps** — Cover Now / Watch This Week / Check If Listed on GAM3S.GG

### Weekly Summary (--weekly)
- Most consistent trending and top sellers (days on chart)
- Biggest risers and fallers over 7 days
- New entries and dropped games
- Review sentiment shifts

### Monthly Summary (--monthly)
- Same as weekly but over 30 days

## After Running

Tell OG the report has been sent to Telegram. If there was an error, suggest checking:
- Steam API key at `~/.openclaw/credentials/steam-api.json`
- Python is available at `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`

## Notes

- Uses Steam Store API (featured categories, search) + Steam Web API (player counts)
- API key stored at `~/.openclaw/credentials/steam-api.json`
- Daily snapshots stored at `C:\Users\User\clawd\steam_data/daily_snapshots.json` (14 day retention)
- Day-over-day comparison requires at least 2 days of data
- Scheduled task runs daily at 2:00 PM Dubai time
- Some apps return 404 on player count (e.g. hardware like Steam Deck) — this is normal
