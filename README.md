# og-dev-arc

Internal dev tools and automation for GAM3S.GG, powered by Vegeta (OpenClaw agent).

## Structure

```
config/         Vegeta agent configuration (AGENTS.md, SOUL.md, TOOLS.md, etc.)
scripts/        Python tools (insights, steam trending, analytics reports)
schedulers/     Windows Scheduled Task wrappers (VBS/BAT)
agents/         Marketing sub-agents (Trunks/SEO, Gohan/Growth, Frieza/Ads)
skills/         Vegeta skills (gam3s-insights, steam-trending)
docs/           Strategy documents and campaign plans
memory/         Vegeta session memory logs
```

## Active Tools

| Tool | Script | Schedule | What it does |
|------|--------|----------|--------------|
| GAM3S Insights | `scripts/gam3s_insights.py` | Daily 1 PM Dubai | GA4 + Search Console analytics dashboard |
| Steam Trending | `scripts/steam_trending.py` | Daily 3 PM Dubai | Steam trending games, top sellers, player counts |

## Setup

**Python 3.12** required. Install dependencies:
```bash
pip install -r requirements.txt
```

**Credentials** (not in repo):
- Google SA: `~/.openclaw/credentials/gam3s-google-sa.json`
- Steam API: `~/.openclaw/credentials/steam-api.json`

**Scheduled Tasks** (Windows):
- `GAM3S Insights Daily` — runs `schedulers/run_insights_hidden.vbs`
- `Steam Trending Daily` — runs `schedulers/run_steam_trending_hidden.vbs`
- `OpenClaw Gateway Watchdog` — runs `schedulers/watchdog_gateway.vbs` every 5 min
