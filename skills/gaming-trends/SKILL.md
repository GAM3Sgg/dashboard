---
name: gaming-trends
description: "Run and send the Gaming Trends daily report (Twitch + IGDB). Use when: user asks about trending games, what's popular, Twitch viewers, game releases, upcoming games, IGDB, or says 'gaming trends'. NOT for: Steam-specific data (use steam-trending), analytics (use gam3s-insights)."
metadata: { "openclaw": { "emoji": "📺" } }
---

# Gaming Trends Report (Twitch + IGDB)

Combined daily report: top games by Twitch live viewership + IGDB release calendar and most anticipated games.

## When to Use

- "What's trending?" / "What games are popular right now?"
- "Twitch viewers" / "What are people watching?"
- "Any new releases?" / "What's coming out this week?"
- "Most anticipated games" / "upcoming releases"
- "Gaming trends" / "send me the trends report"
- "Weekly gaming summary" / "monthly gaming summary"

## How to Run

**Daily report (default):**
```bash
cd C:\Users\User\clawd\scripts && set PYTHONIOENCODING=utf-8 && python send_gaming_trends_telegram.py
```

**Weekly summary (7-day trends):**
```bash
cd C:\Users\User\clawd\scripts && set PYTHONIOENCODING=utf-8 && python send_gaming_trends_telegram.py --weekly
```

**Monthly summary (30-day rollup):**
```bash
cd C:\Users\User\clawd\scripts && set PYTHONIOENCODING=utf-8 && python send_gaming_trends_telegram.py --monthly
```

Generate without sending to Telegram:
```bash
cd C:\Users\User\clawd\scripts && set PYTHONIOENCODING=utf-8 && python gaming_trends.py
```

## What It Contains

### Daily Report
- **Twitch Top Games** — top 20 by live viewers, stream counts, day-over-day % change, [NEW] badges
- **Rising / Falling** — biggest viewership swings vs yesterday
- **New Entries** — games appearing in top 30 for the first time
- **Releasing This Week** — IGDB upcoming releases with platform and follower data
- **Just Released (72h)** — recent releases with ratings
- **Most Anticipated** — top 10 upcoming by IGDB hype score
- **Cross-reference** — games trending on Twitch that are also releasing soon

### Weekly/Monthly Summary
- Most consistent games (days in top 30)
- Biggest risers and fallers over the period
- New entries and dropped games

## After Running

Tell OG the report has been sent to Telegram. If error, check:
- Twitch credentials at `~/.openclaw/credentials/twitch-api.json`
- Python at `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`

## Notes

- Uses Twitch Helix API (top games, streams) + IGDB API (games database)
- Same Twitch Developer credentials for both APIs
- Credentials at `~/.openclaw/credentials/twitch-api.json`
- Daily snapshots at `C:\Users\User\clawd\scripts\gaming_trends_data/daily_snapshots.json`
- Scheduled task runs daily at 3:00 PM Dubai time
- Day-over-day comparison requires at least 2 days of data
