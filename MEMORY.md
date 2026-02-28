# MEMORY.md - Long-Term Memory

## About OG
- CEO & Founder of GAM3S.GG (gaming discovery platform)
- Timezone: Asia/Dubai (GMT+4)
- Busy - values efficiency

## Key Projects
- GAM3S.GG: Gaming discovery platform, 1.7M+ gamers, 1,000+ games database
- Launched 2022, subscription launching February 2026
- Partners: Ubisoft, Riot Games, Epic Games, Nvidia, Red Bull Gaming, Logitech

## Setup Notes
- OpenClaw installed 2026-02-22
- Agent name: Vegeta
- LarryBrain API key stored securely in ~/.openclaw/credentials/larrybrain.json
- Config optimized 2026-02-22: Haiku primary, 6h cache TTL, memory flush at 40k tokens
- Heartbeat DISABLED for security
- Exec approval required for ALL actions

## Agent Operating Principles
- **CONSENT FIRST**: Never take any action without OG's explicit approval. Present plans, wait for go-ahead.
- **Coding**: always delegate to coding-agent skill (Codex CLI) — don't try to code inline
- **X caution**: X is cracking down on bots + API usage. Tread carefully with any X automation.
- **Email**: don't pursue email access — prompt injection risk, not worth it

## Campaign Planning Context (Feb 24, 2026)
### Games+ March 2026 Launch Strategy (Gohan)
- **Goal:** $30k/month minimum revenue (optimistic: $100k/month)
- **Launch Date:** March 2026
- **Starting Point:** 2M+ registered users, 600K+ MAU, 3M+ monthly organic visits, zero current subscribers
- **Pricing (locked):**
  - $4.99/month (monthly)
  - $40/year ($4/month, 2 months free)
- **Key Offer Features:**
  - Free game every month (Box Inventory)
  - 100% ad-free browsing
  - 48-hour early access to reviews
  - Members-only deals up to 70% off
  - VIP 24/7 support
  - Priority beta invites
  - Exclusive GAMES+ profile badge
- **Email List:** 70k subscribers, 20% open rate, 4% CTR historically
- **Deliverables Completed:** Full launch strategy with audience segmentation, email sequences, in-app placements, paid ads strategy (X + Instagram/TikTok), organic social calendar, conversion funnel, week-by-week timeline, month 1-3 ramp plan, retention strategy, metrics/benchmarks
- **Revenue Targets:** March $12-15k (8,000 subs) → April $20-25k (10,000 subs) → May $30k+ (14,000+ subs)
- **Document:** Full strategy saved and ready for review

### Ramadan Noon Collaboration (Frieza - Feb 25 - Mar 26, 2026)
- **Partner:** Noon (regional shopping platform)
- **Target:** Drive Games+ signups via Noon discount incentives
- **Discount Structure:** 4-week rotating codes
  - Week 1 (Feb 18-24): RMDNREADY | Electronics & Gaming Accessories | 15% new / 10% repeat (cap 100/50 AED)
  - Week 2 (Feb 25-Mar 3): RMDNHOME | TVs, Laptops, Toys & Games | 20% new / 15% repeat (cap 100/75 AED)
  - Week 3 (Mar 4-10): RMDNSTYLE | Watches, Fragrances, Eyewear | 20% new / 15% repeat (cap 100/75 AED)
  - Week 4 (Mar 11-19): RMDNFINAL | Phones, Accessories, Travel Gear | 15% new / 10% repeat (cap 100/50 AED)
- **Post-Signup Email Copy (locked):** 
  - Subject: "Welcome to GAMES.GG! You signed up through our Ramadan campaign with noon — so here's what you unlocked."
  - Shows all 4 codes upfront + categories + discounts + instructions
  - Closing: "Ramadan Kareem, GAMES.GG"
- **Ad Concepts (5 Banner Variations with Full Copy):**
  1. **Blessings Within Reach** (spiritual gifting angle) — "Your Blessing Unlocked: 4 Weeks of Premium Games+ + Noon Discounts"
  2. **Double the Joy** (stacked value) — "Get Premium Games+ + 4 Weeks of Noon Rewards"
  3. **Your Ramadan Companion** (community focus) — "Play Together This Ramadan: Premium Games+ + Weekly Noon Codes"
  4. **Ramadan Rewards** (scarcity/urgency) — "⏰ Ramadan Only: 4 Exclusive Weekly Codes for Premium Members"
  5. **Level Up Your Ramadan** (gamer language) — "Unlock Premium: Games+ + 4 Weeks of Exclusive Rewards"
- **UTM Strategy:** `?utm_source=noon&utm_medium=[placement]&utm_campaign=ramadan_2026&utm_content=[creative_variant]&utm_term=[audience_segment]`
- **Email Sequence (3 Full Templates):**
  - Announcement (Day 1 Ramadan): Subject "🌙 Ramadan Surprise: Games+ Premium + Noon Rewards Inside"
  - Mid-Campaign (Day 15): Subject "⏰ Last Chance: Your Noon Rewards Expire Soon"
  - Final Week (3 days before end): Subject "🎁 Your Ramadan Gaming Reward Expires in 3 Days"
- **Social Content (Full Scripts):**
  - Instagram Stories (4-frame takeover with CTAs)
  - TikTok Reels (15-30 sec with trending music, voiceover, code reveal)
  - X/Twitter (5-tweet thread + single tweet variations)
  - LinkedIn (B2B angle on partnership)
- **Landing Page Structure:** Hero → Offer Summary (Games+ + Noon side-by-side) → Social Proof → FAQ (6 key Qs) → Final CTA → Footer
- **Performance Targets:**
  - Signup conversion: 4-6% (stretch 8-10%)
  - Code redemption: 35%+ (stretch 50%+)
  - ROAS: 3:1+ (discount cost vs. AOV)
  - Signups: 10,000+
- **Timeline:** Prep week -4 to -1, Launch Day 1 Ramadan (Feb 25), Optimize weeks 1-3, Wind-down final week
- **Document:** Full 38KB playbook saved with all concepts, copy, UTM tracking, discount mechanics, CRO playbook, and post-launch analysis framework

**Follow-Up Workflow:**
- If OG requests changes to either campaign, Frieza & Gohan have full context to iterate
- Frieza owns: Ad creative, copy, conversion optimization, Noon partnership logistics
- Gohan owns: Launch timeline, email sequences, in-app strategy, retention, revenue modeling
- Both can reference this session for any refinements needed before launch

## GAM3S.GG Insights Dashboard (Feb 23, 2026)
- **Status**: Configured by OG + Claude, deployed 2026-02-23
- **Script**: `C:\Users\User\clawd\gam3s_insights.py` (DO NOT MODIFY)
- **GA4 Property**: 334095714 | **Search Console**: gam3s.gg
- **Credentials**: ~/.openclaw/credentials/gam3s-google-sa.json
- **Timezone**: Asia/Dubai (1pm daily send)
- **Output format**: Last 7 days only (default) — 14/30 day data on request
- **Send method**: Single consolidated Telegram message (via OpenClaw message tool)
- **Capabilities**: 
  - Top pages, guides, news by category
  - Language performance (19 languages)
  - Search Console query insights
  - Spike detection + actionables
  - Bounce rate analysis
- **My responsibilities**: 
  - ✅ Send daily at 1pm Dubai time
  - ✅ Resend on demand via chat
  - ✅ Answer questions about the data
  - ❌ DO NOT touch code/configuration

---

*Update this file with significant events, decisions, and lessons learned.*
