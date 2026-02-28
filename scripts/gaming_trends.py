#!/usr/bin/env python3
"""
Gaming Trends Daily Report — Twitch + IGDB combined.
Tracks top games by live viewership (Twitch) and upcoming/recent releases (IGDB).
"""

import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

REQUEST_DELAY = 0.3
DATA_DIR = Path(__file__).parent / "gaming_trends_data"
SNAPSHOT_FILE = DATA_DIR / "daily_snapshots.json"
CREDS_FILE = Path.home() / ".openclaw" / "credentials" / "twitch-api.json"

# ── Auth ──────────────────────────────────────────────────────────────────────

def load_credentials():
    with open(CREDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_access_token(client_id, client_secret):
    """Get OAuth2 app access token (client credentials flow)."""
    url = "https://id.twitch.tv/oauth2/token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["access_token"]

# ── API helpers ───────────────────────────────────────────────────────────────

def twitch_get(endpoint, params, client_id, token):
    """GET request to Twitch Helix API."""
    qs = urllib.parse.urlencode(params)
    url = f"https://api.twitch.tv/helix/{endpoint}?{qs}"
    req = urllib.request.Request(url, headers={
        "Client-Id": client_id,
        "Authorization": f"Bearer {token}"
    })
    time.sleep(REQUEST_DELAY)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def igdb_post(endpoint, body, client_id, token):
    """POST request to IGDB API (Apicalypse query syntax)."""
    url = f"https://api.igdb.com/v4/{endpoint}"
    req = urllib.request.Request(url, data=body.encode("utf-8"), method="POST", headers={
        "Client-Id": client_id,
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/plain"
    })
    time.sleep(REQUEST_DELAY)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  IGDB error ({endpoint}): {e}", file=sys.stderr)
        return []

# ── Formatting helpers ────────────────────────────────────────────────────────

def fmt_num(n):
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n:,.0f}"
    return str(n)

def pct_change(current, previous):
    if not previous or not current:
        return ""
    change = ((current - previous) / previous) * 100
    if abs(change) < 1:
        return ""
    sign = "+" if change > 0 else ""
    return f" ({sign}{change:.0f}%)"

def twitch_link(name, game_id=None):
    """Create Twitch directory link."""
    slug = name.lower().replace(" ", "-").replace("'", "").replace(":", "")
    safe = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="https://www.twitch.tv/directory/category/{urllib.parse.quote(slug)}">{safe}</a>'

def safe_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ── Snapshots ─────────────────────────────────────────────────────────────────

def load_snapshots():
    if SNAPSHOT_FILE.exists():
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_snapshot(snapshots, today_key, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshots[today_key] = data
    # 30-day retention
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    snapshots = {k: v for k, v in snapshots.items() if k >= cutoff}
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshots, f, indent=2)
    return snapshots

def get_previous_snapshot(snapshots, today_key):
    dates = sorted(k for k in snapshots if k < today_key)
    return snapshots[dates[-1]] if dates else {}

# ── Twitch data ───────────────────────────────────────────────────────────────

def fetch_top_games(client_id, token, count=100):
    """Fetch top games by current viewer count."""
    games = []
    cursor = None
    while len(games) < count:
        params = {"first": min(100, count - len(games))}
        if cursor:
            params["after"] = cursor
        resp = twitch_get("games/top", params, client_id, token)
        batch = resp.get("data", [])
        if not batch:
            break
        games.extend(batch)
        cursor = resp.get("pagination", {}).get("cursor")
        if not cursor:
            break
    return games

def fetch_stream_counts(client_id, token, game_ids):
    """Get viewer + stream counts per game via streams endpoint."""
    counts = {}
    for gid in game_ids:
        resp = twitch_get("streams", {"game_id": gid, "first": 1}, client_id, token)
        # The pagination total isn't available, but we can get viewer count from games/top
        # Just count streams for top games
        streams = resp.get("data", [])
        if streams:
            counts[gid] = {"live_streams": len(streams)}
    return counts

def get_top_games_with_viewers(client_id, token):
    """Get top games with viewer counts from the top games endpoint."""
    # Twitch /games/top doesn't return viewer counts directly in newer API
    # We need to use /streams to aggregate
    # But for efficiency, we'll fetch top games and then get stream data

    # Step 1: Get top 100 games
    games_raw = fetch_top_games(client_id, token, count=100)

    # Step 2: For top 30, get stream data to count viewers
    results = []
    for game in games_raw[:30]:
        game_id = game["id"]
        game_name = game["name"]

        # Fetch first page of streams for this game (sorted by viewers desc)
        resp = twitch_get("streams", {"game_id": game_id, "first": 100}, client_id, token)
        streams = resp.get("data", [])

        total_viewers = sum(s.get("viewer_count", 0) for s in streams)
        stream_count = len(streams)

        # For very popular games, there are more than 100 streams
        # The first page gives us a good approximation
        # We note this is a lower bound for massive games

        results.append({
            "id": game_id,
            "name": game_name,
            "viewers": total_viewers,
            "streams": stream_count,
            "box_art_url": game.get("box_art_url", "")
        })

    return results

# ── IGDB data ─────────────────────────────────────────────────────────────────

def fetch_upcoming_releases(client_id, token):
    """Games releasing in the next 14 days via release_dates endpoint."""
    now = int(datetime.now().timestamp())
    future = int((datetime.now() + timedelta(days=14)).timestamp())
    body = (
        f"fields game.name,game.url,game.follows,game.total_rating,date,platform.name,human;"
        f" where date >= {now} & date <= {future};"
        f" sort date asc; limit 50;"
    )
    raw = igdb_post("release_dates", body, client_id, token)
    # Dedupe by game name (multiple platforms create multiple entries)
    seen = {}
    results = []
    for entry in raw:
        game = entry.get("game", {})
        name = game.get("name", "")
        if not name or name in seen:
            # Merge platform into existing entry
            if name in seen and entry.get("platform"):
                seen[name]["platforms"].append(entry["platform"])
            continue
        item = {
            "name": name,
            "url": game.get("url", ""),
            "follows": game.get("follows", 0) or 0,
            "total_rating": game.get("total_rating"),
            "date": entry.get("date"),
            "human": entry.get("human", ""),
            "platforms": [entry["platform"]] if entry.get("platform") else []
        }
        seen[name] = item
        results.append(item)
    return results

def fetch_just_released(client_id, token):
    """Games released in the last 7 days via release_dates endpoint."""
    ago = int((datetime.now() - timedelta(days=7)).timestamp())
    now = int(datetime.now().timestamp())
    body = (
        f"fields game.name,game.url,game.follows,game.total_rating,game.rating,date,platform.name,human;"
        f" where date >= {ago} & date <= {now};"
        f" sort date desc; limit 50;"
    )
    raw = igdb_post("release_dates", body, client_id, token)
    seen = {}
    results = []
    for entry in raw:
        game = entry.get("game", {})
        name = game.get("name", "")
        if not name or name in seen:
            if name in seen and entry.get("platform"):
                seen[name]["platforms"].append(entry["platform"])
            continue
        item = {
            "name": name,
            "url": game.get("url", ""),
            "follows": game.get("follows", 0) or 0,
            "total_rating": game.get("total_rating"),
            "rating": game.get("rating"),
            "date": entry.get("date"),
            "human": entry.get("human", ""),
            "platforms": [entry["platform"]] if entry.get("platform") else []
        }
        seen[name] = item
        results.append(item)
    return results

def fetch_most_anticipated(client_id, token):
    """Top upcoming games by follows count."""
    now = int(datetime.now().timestamp())
    body = (
        f"fields name,first_release_date,platforms.name,follows,url;"
        f" where first_release_date > {now} & follows > 0;"
        f" sort follows desc; limit 10;"
    )
    return igdb_post("games", body, client_id, token)

def fmt_date(unix_ts):
    if not unix_ts:
        return "TBA"
    return datetime.fromtimestamp(unix_ts).strftime("%b %d")

def fmt_platforms(platforms):
    if not platforms:
        return ""
    names = [p.get("name", "") for p in platforms[:5]]
    short = []
    for n in names:
        if "PC" in n or "Windows" in n:
            short.append("PC")
        elif "PlayStation 5" in n:
            short.append("PS5")
        elif "PlayStation 4" in n:
            short.append("PS4")
        elif "Xbox Series" in n:
            short.append("XSX")
        elif "Xbox One" in n:
            short.append("XB1")
        elif "Switch" in n:
            short.append("Switch")
        else:
            short.append(n[:10])
    return " · ".join(dict.fromkeys(short))  # dedupe while preserving order

def igdb_link(game):
    name = safe_html(game.get("name", "Unknown"))
    url = game.get("url", "")
    if url:
        return f'<a href="{url}">{name}</a>'
    return name

# ── Report builder ────────────────────────────────────────────────────────────

def build_report(mode="daily"):
    creds = load_credentials()
    client_id = creds["client_id"]
    client_secret = creds["client_secret"]

    print("Authenticating with Twitch...", file=sys.stderr)
    token = get_access_token(client_id, client_secret)

    today = datetime.now().strftime("%Y-%m-%d")
    snapshots = load_snapshots()
    prev = get_previous_snapshot(snapshots, today)
    prev_viewers = prev.get("viewers", {})
    prev_names = set(prev.get("top_game_names", []))

    if mode == "daily":
        return build_daily_report(client_id, token, today, snapshots, prev_viewers, prev_names)
    elif mode == "weekly":
        return build_summary_report(snapshots, today, 7)
    elif mode == "monthly":
        return build_summary_report(snapshots, today, 30)

def build_daily_report(client_id, token, today, snapshots, prev_viewers, prev_names):
    lines = []
    lines.append(f"<b>GAMING TRENDS — {today}</b>")
    lines.append("")

    # ── Twitch: Top Games by Viewership ──
    print("Fetching Twitch top games...", file=sys.stderr)
    top_games = get_top_games_with_viewers(client_id, token)

    lines.append("<b>TWITCH — TOP GAMES BY VIEWERS</b>")
    lines.append("")
    for i, g in enumerate(top_games[:20], 1):
        name = g["name"]
        viewers = g["viewers"]
        streams = g["streams"]
        change = pct_change(viewers, prev_viewers.get(name, 0))
        new_badge = " [NEW]" if name not in prev_names and prev_names else ""
        link = twitch_link(name)
        lines.append(f"{i}. {link}{new_badge}")
        lines.append(f"   {fmt_num(viewers)} viewers · {streams}+ streams{change}")
    lines.append("")

    # ── Rising / Falling ──
    if prev_viewers:
        current_viewers = {g["name"]: g["viewers"] for g in top_games}
        all_names = set(current_viewers.keys()) | set(prev_viewers.keys())

        changes = []
        for name in all_names:
            curr = current_viewers.get(name, 0)
            prev_v = prev_viewers.get(name, 0)
            if prev_v >= 500 and curr > 0:  # minimum threshold
                pct = ((curr - prev_v) / prev_v) * 100
                changes.append((name, curr, prev_v, pct))

        rising = sorted([c for c in changes if c[3] > 20], key=lambda x: -x[3])[:5]
        falling = sorted([c for c in changes if c[3] < -20], key=lambda x: x[3])[:5]

        if rising:
            lines.append("<b>RISING</b>")
            for name, curr, prev_v, pct in rising:
                lines.append(f"  {safe_html(name)}: {fmt_num(prev_v)} → {fmt_num(curr)} (+{pct:.0f}%)")
            lines.append("")

        if falling:
            lines.append("<b>FALLING</b>")
            for name, curr, prev_v, pct in falling:
                lines.append(f"  {safe_html(name)}: {fmt_num(prev_v)} → {fmt_num(curr)} ({pct:.0f}%)")
            lines.append("")

    # ── New Entries ──
    if prev_names:
        current_names = {g["name"] for g in top_games[:30]}
        new_entries = current_names - prev_names
        if new_entries:
            lines.append("<b>NEW ENTRIES TODAY</b>")
            for name in sorted(new_entries):
                game = next((g for g in top_games if g["name"] == name), None)
                if game:
                    lines.append(f"  {safe_html(name)} — {fmt_num(game['viewers'])} viewers")
            lines.append("")

    # ── IGDB: Upcoming Releases ──
    print("Fetching IGDB releases...", file=sys.stderr)
    upcoming = fetch_upcoming_releases(client_id, token)
    if upcoming:
        lines.append("<b>RELEASING NEXT 14 DAYS</b>")
        for g in upcoming[:12]:
            name = safe_html(g["name"])
            url = g.get("url", "")
            link = f'<a href="{url}">{name}</a>' if url else name
            date = g.get("human", "TBA")
            plats = fmt_platforms(g.get("platforms", []))
            meta = []
            if plats:
                meta.append(plats)
            follows = g.get("follows", 0)
            if follows:
                meta.append(f"{fmt_num(follows)} follows")
            meta_str = f" — {' · '.join(meta)}" if meta else ""
            lines.append(f"  {date}: {link}{meta_str}")
        lines.append("")

    # ── IGDB: Just Released ──
    just_released = fetch_just_released(client_id, token)
    if just_released:
        lines.append("<b>JUST RELEASED (7 DAYS)</b>")
        for g in just_released[:10]:
            name = safe_html(g["name"])
            url = g.get("url", "")
            link = f'<a href="{url}">{name}</a>' if url else name
            rating = g.get("total_rating") or g.get("rating")
            rating_str = f" — {rating:.0f}/100" if rating else ""
            plats = fmt_platforms(g.get("platforms", []))
            plat_str = f" ({plats})" if plats else ""
            lines.append(f"  {link}{plat_str}{rating_str}")
        lines.append("")

    # ── IGDB: Most Anticipated ──
    anticipated = fetch_most_anticipated(client_id, token)
    if anticipated:
        lines.append("<b>MOST ANTICIPATED</b>")
        for g in anticipated[:10]:
            link = igdb_link(g)
            date = fmt_date(g.get("first_release_date"))
            follows = g.get("follows", 0) or 0
            meta = [date]
            if follows:
                meta.append(f"{fmt_num(follows)} follows")
            lines.append(f"  {link} — {' · '.join(meta)}")
        lines.append("")

    # ── Cross-reference: Twitch trending + upcoming ──
    if upcoming:
        twitch_names = {g["name"].lower() for g in top_games[:30]}
        releasing_on_twitch = [g for g in upcoming if g.get("name", "").lower() in twitch_names]
        if releasing_on_twitch:
            lines.append("<b>TRENDING ON TWITCH + RELEASING SOON</b>")
            for g in releasing_on_twitch:
                name = safe_html(g["name"])
                url = g.get("url", "")
                link = f'<a href="{url}">{name}</a>' if url else name
                lines.append(f"  {link} — {g.get('human', 'TBA')}")
            lines.append("")

    # ── Save snapshot ──
    snapshot_data = {
        "top_games": [{"id": g["id"], "name": g["name"]} for g in top_games[:30]],
        "top_game_names": [g["name"] for g in top_games[:30]],
        "viewers": {g["name"]: g["viewers"] for g in top_games},
        "date": datetime.now().isoformat()
    }
    save_snapshot(snapshots, today, snapshot_data)

    report = "\n".join(lines)

    # Save to file
    output_file = Path(__file__).parent / "gaming_trends_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {output_file}", file=sys.stderr)

    return report

def build_summary_report(snapshots, today, days):
    """Weekly or monthly summary."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    period_snaps = {k: v for k, v in snapshots.items() if cutoff <= k <= today}

    if len(period_snaps) < 2:
        return f"Not enough data for {days}-day summary. Need at least 2 days of snapshots."

    period_name = "WEEKLY" if days <= 7 else "MONTHLY"
    lines = [f"<b>GAMING TRENDS — {period_name} SUMMARY ({days}d)</b>", ""]

    # Consistency: games that appeared most often in top 30
    game_appearances = {}
    for snap in period_snaps.values():
        for name in snap.get("top_game_names", []):
            game_appearances[name] = game_appearances.get(name, 0) + 1

    total_days = len(period_snaps)
    consistent = sorted(game_appearances.items(), key=lambda x: -x[1])[:10]

    lines.append(f"<b>MOST CONSISTENT (top 30 for {total_days} days)</b>")
    for name, count in consistent:
        pct = (count / total_days) * 100
        lines.append(f"  {safe_html(name)} — {count}/{total_days} days ({pct:.0f}%)")
    lines.append("")

    # Biggest risers/fallers: compare first and last snapshot viewers
    sorted_dates = sorted(period_snaps.keys())
    first_snap = period_snaps[sorted_dates[0]]
    last_snap = period_snaps[sorted_dates[-1]]

    first_v = first_snap.get("viewers", {})
    last_v = last_snap.get("viewers", {})

    changes = []
    for name in set(first_v.keys()) & set(last_v.keys()):
        if first_v[name] >= 500:
            pct = ((last_v[name] - first_v[name]) / first_v[name]) * 100
            changes.append((name, last_v[name], first_v[name], pct))

    risers = sorted([c for c in changes if c[3] > 10], key=lambda x: -x[3])[:5]
    fallers = sorted([c for c in changes if c[3] < -10], key=lambda x: x[3])[:5]

    if risers:
        lines.append(f"<b>BIGGEST RISERS ({days}d)</b>")
        for name, curr, prev, pct in risers:
            lines.append(f"  {safe_html(name)}: {fmt_num(prev)} → {fmt_num(curr)} (+{pct:.0f}%)")
        lines.append("")

    if fallers:
        lines.append(f"<b>BIGGEST FALLERS ({days}d)</b>")
        for name, curr, prev, pct in fallers:
            lines.append(f"  {safe_html(name)}: {fmt_num(prev)} → {fmt_num(curr)} ({pct:.0f}%)")
        lines.append("")

    # New entries over the period
    first_names = set(first_snap.get("top_game_names", []))
    last_names = set(last_snap.get("top_game_names", []))
    new_this_period = last_names - first_names
    dropped = first_names - last_names

    if new_this_period:
        lines.append(f"<b>NEW ENTRIES THIS {period_name}</b>")
        for name in sorted(new_this_period):
            viewers = last_v.get(name, 0)
            lines.append(f"  {safe_html(name)} — {fmt_num(viewers)} viewers")
        lines.append("")

    if dropped:
        lines.append(f"<b>DROPPED OFF THIS {period_name}</b>")
        for name in sorted(dropped):
            lines.append(f"  {safe_html(name)}")
        lines.append("")

    report = "\n".join(lines)
    output_file = Path(__file__).parent / "gaming_trends_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    return report

# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = "daily"
    if "--weekly" in sys.argv:
        mode = "weekly"
    elif "--monthly" in sys.argv:
        mode = "monthly"

    report = build_report(mode)
    print(report)
