# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## API Keys

- LarryBrain key stored securely in ~/.openclaw/credentials/larrybrain.json (not in conversation context)

---

## Sub-Agents (Marketing Team)

You have 3 marketing specialist personas. Delegate marketing tasks by spawning a sub-agent (under YOUR agent ID, do NOT use agentId parameter) and telling it to adopt the right persona.

**IMPORTANT: Do NOT pass agentId when spawning. Spawn under your own agent (main) so the Telegram announce-back works. Instead, include the persona instructions and skill paths in the task description.**

### Trunks (SEO & Site Structure)
- **Skills path:** `~/clawd/agents/trunks/skills/`
- **Persona file:** `~/clawd/agents/trunks/AGENTS.md`
- **Domain:** SEO audits, AI search optimization, schema markup, programmatic SEO, competitor/alternative pages, analytics tracking, A/B testing, content strategy
- **When to delegate:** Anything about search rankings, site structure, structured data, SEO content, analytics setup, or testing

### Gohan (Marketing, Launch & Growth)
- **Skills path:** `~/clawd/agents/gohan/skills/`
- **Persona file:** `~/clawd/agents/gohan/AGENTS.md`
- **Domain:** Product launches, email sequences, cold outreach, social content, referral programs, pricing strategy, marketing ideas, churn prevention, copywriting, copy editing, content strategy
- **When to delegate:** Anything about launches, emails, growth tactics, pricing, outreach, retention, or marketing copy

### Frieza (Copy, Ads & Conversion)
- **Skills path:** `~/clawd/agents/frieza/skills/`
- **Persona file:** `~/clawd/agents/frieza/AGENTS.md`
- **Domain:** Ad creative, paid ads (Google/Meta/LinkedIn/X), copywriting, copy editing, CRO (pages, signup flows, onboarding, forms, popups, paywalls), marketing psychology
- **When to delegate:** Anything about ad campaigns, ad creative, conversion optimization, landing pages, signup flows, or persuasion tactics

### How to Spawn

When delegating, use `sessions_spawn` WITHOUT agentId. Include in the task:
1. "Read and follow the persona at ~/clawd/agents/<name>/AGENTS.md"
2. "Read the relevant skill(s) from ~/clawd/agents/<name>/skills/<skill-name>/SKILL.md"
3. The actual task from OG

Example task: "Read and follow ~/clawd/agents/trunks/AGENTS.md for your persona. Then read ~/clawd/agents/trunks/skills/seo-audit/SKILL.md and use it to audit gam3s.gg/guides for SEO issues."

### Routing Rules
- If a task clearly fits one persona, spawn one sub-agent with that persona
- If a task spans two personas, pick the primary domain or spawn both
- Always relay the sub-agent's response back to OG — don't silently consume it
- Sub-agents have NO credential access and cannot run shell commands — they are knowledge-only specialists

### CRITICAL: Sub-Agent Behavior
- **Spawn and wait.** After calling `sessions_spawn`, tell OG you've spawned the agent and what it's working on. Then WAIT for the automatic announce-back. Do NOT use `sessions_send` to talk to the sub-agent while it's working — it will timeout because the sub-agent is busy.
- **Do NOT use `sessions_send` on sub-agent sessions.** The announce mechanism handles result delivery automatically.
- **Do NOT use `subagents list` to check status** unless OG specifically asks. The sub-agent will announce when done.
- When the announce arrives, relay the result to OG immediately and ask "What's next?"

---

Add whatever helps you do your job. This is your cheat sheet.
