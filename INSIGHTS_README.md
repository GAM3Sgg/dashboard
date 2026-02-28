# GAM3S.GG Insights Dashboard

Fetches GA4 & Search Console data, analyzes performance trends, outputs a formatted message for Telegram.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify Credentials
Script looks for credentials at: `~/.openclaw/credentials/gam3s-google-sa.json`
- Confirm the file exists and is readable

### 3. Run the Script
```bash
python gam3s_insights.py
```

This will:
- Fetch data from GA4 (property 334095714)
- Fetch data from Search Console (gam3s.gg)
- Analyze pages, languages, games, spikes
- Output a formatted Telegram message
- Save the message to `insights_output.txt`

## Configuration

Edit these in `gam3s_insights.py` if needed:
- `GA4_PROPERTY_ID = "334095714"` - GA4 property ID
- `SEARCH_CONSOLE_DOMAIN = "gam3s.gg"` - Domain to analyze
- `TIMEZONE = pytz.timezone('Asia/Dubai')` - Timezone for timestamps

## Output

The script prints a formatted message with:
- 📊 Top performing pages (7/14/30 days)
- 🌍 Language performance (all 19 languages)
- 🔥 Traffic spikes and trends
- 📈 Quick summary stats
- 💡 Actionable insights for the team

## Next Steps

1. Run once to see the output format
2. Provide feedback on style/metrics/layout
3. We'll iterate and refine
4. Set up automated daily runs at 1pm Dubai time

## Troubleshooting

- **Credentials error**: Verify `~/.openclaw/credentials/gam3s-google-sa.json` exists and is valid
- **API errors**: Check GA4 property ID and Search Console domain permissions
- **Missing data**: GA4 may take 24-48 hours to populate new data

---

Built for GAM3S.GG by Vegeta ⚡
