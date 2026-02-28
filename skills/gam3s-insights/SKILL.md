---
name: gam3s-insights
description: "Run and send the GAM3S.GG daily insights dashboard (GA4 + Search Console). Use when: user asks for insights, dashboard, report, analytics, stats, traffic, SEO data, search queries, or says 'send me the report'. NOT for: general website questions, content writing, or non-analytics tasks."
metadata: { "openclaw": { "emoji": "📊" } }
---

# GAM3S.GG Insights Dashboard

Generate and send the GAM3S.GG daily analytics dashboard combining GA4 and Google Search Console data.

## When to Use

✅ **USE this skill when the user says things like:**

- "Send me the insights" / "send the report" / "dashboard"
- "How's traffic?" / "how are we doing?" / "what are the numbers?"
- "Show me analytics" / "stats" / "sessions"
- "Search console data" / "search queries" / "SEO report"
- "Run the daily report" / "gam3s insights"
- "What's trending?" / "top pages?" / "top guides?"

## How to Run

Run this command (must use utf-8 encoding on Windows):

```bash
cd C:\Users\User\clawd && set PYTHONIOENCODING=utf-8 && python send_insights_telegram.py
```

Or if only generating without sending to Telegram:

```bash
cd C:\Users\User\clawd && set PYTHONIOENCODING=utf-8 && python gam3s_insights.py
```

The report will be:
1. Saved to `C:\Users\User\clawd\insights_output.txt`
2. Sent to OG on Telegram (if using send_insights_telegram.py)

## What It Contains

- **Week over week summary** — total sessions vs last week
- **7 / 14 / 30 day breakdowns** — top pages, guides, news, languages (all combined across language versions)
- **Trending content** — spike detection (7d vs prior 7d)
- **Rising topics** — growing themes to cover
- **Fix opportunities** — high bounce rate pages
- **Language content gaps** — underserved languages with significant traffic
- **Search Console data** — top queries, rising queries, content gaps, page 2 easy wins, low CTR pages
- **Actionables** — content priorities + SEO action items

## After Running

Tell OG the report has been sent to Telegram. If they're already in the Telegram chat, just confirm it's done. If there was an error, show the error message and suggest checking:
- Google service account credentials at `~/.openclaw/credentials/gam3s-google-sa.json`
- Python dependencies: `pip install -r C:\Users\User\clawd\requirements.txt`

## Notes

- Uses 7 API calls total (4 GA4 + 3 Search Console)
- Service account credentials are at `~/.openclaw/credentials/gam3s-google-sa.json`
- GA4 Property ID: 334095714
- Search Console: sc-domain:gam3s.gg
- Timezone: Asia/Dubai
- Report is formatted in Telegram Markdown
