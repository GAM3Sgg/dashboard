#!/usr/bin/env python3
"""
Gaming Trends Daily Report — Twitch + IGDB combined.
Tracks top games by live viewership (Twitch), breakout games surging in attention,
top games by language/region, and upcoming/anticipated releases (IGDB + Steam wishlists).
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
STEAM_KEY_FILE = Path.home() / ".openclaw" / "credentials" / "steam-api.json"

# Non-game Twitch categories to filter out
BLACKLIST_CATEGORIES = {
    "just chatting", "irl", "always on", "music", "art", "asmr",
    "sports", "pools, hot tubs, and beaches", "talk shows & podcasts",
    "food & drink", "travel & outdoors", "makers & crafting",
    "science & technology", "special events", "politics",
    "software and game development", "chess", "poker",
}

# Top languages to track (ISO 639-1 codes)
TRACKED_LANGUAGES = {
    "en": "English", "es": "Spanish", "pt": "Portuguese",
    "ja": "Japanese", "ko": "Korean", "fr": "French",
    "de": "German", "ru": "Russian", "zh": "Chinese",
    "tr": "Turkish", "ar": "Arabic", "it": "Italian",
}

# ── Auth ──────────────────────────────────────────────────────────────────────

def load_credentials():
    with open(CREDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_steam_key():
    try:
        with open(STEAM_KEY_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("key", "")
    except Exception:
        return ""

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

def steam_get(url, params=None):
    """GET request to Steam Store API."""
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "GamingTrends/1.0"})
    time.sleep(REQUEST_DELAY)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  Steam error: {e}", file=sys.stderr)
        return {}

# ── Formatting helpers ────────────────────────────────────────────────────────

def fmt_num(n):
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n:,.0f}"
    return str(n)

def pct_change_str(current, previous):
    if not previous or not current:
        return ""
    change = ((current - previous) / previous) * 100
    if abs(change) < 1:
        return ""
    sign = "+" if change > 0 else ""
    return f" ({sign}{change:.0f}%)"

def twitch_link(name):
    """Create clickable Twitch directory link."""
    slug = name.lower().replace(" ", "-").replace("'", "").replace(":", "").replace(".", "")
    safe = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="https://www.twitch.tv/directory/category/{urllib.parse.quote(slug)}">{safe}</a>'

def igdb_link(game):
    """Create clickable IGDB link."""
    name = safe_html(game.get("name", "Unknown"))
    url = game.get("url", "")
    if url:
        return f'<a href="{url}">{name}</a>'
    return name

def steam_link(name, appid):
    """Create clickable Steam store link."""
    safe = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="https://store.steampowered.com/app/{appid}">{safe}</a>'

def safe_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

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
        elif "Switch" in n and "2" in n:
            short.append("Switch 2")
        elif "Switch" in n:
            short.append("Switch")
        else:
            short.append(n[:10])
    return " · ".join(dict.fromkeys(short))

# ── Snapshots ─────────────────────────────────────────────────────────────────

def load_snapshots():
    if SNAPSHOT_FILE.exists():
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_snapshot(snapshots, today_key, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshots[today_key] = data
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    snapshots = {k: v for k, v in snapshots.items() if k >= cutoff}
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshots, f, indent=2)
    return snapshots

def get_previous_snapshot(snapshots, today_key):
    dates = sorted(k for k in snapshots if k < today_key)
    return snapshots[dates[-1]] if dates else {}

# ── Twitch data ───────────────────────────────────────────────────────────────

def is_game_category(name):
    return name.lower() not in BLACKLIST_CATEGORIES

def fetch_top_games(client_id, token, count=100):
    """Fetch top games by current viewer count, filtering non-game categories."""
    games = []
    cursor = None
    fetched = 0
    while len(games) < count and fetched < 300:
        params = {"first": 100}
        if cursor:
            params["after"] = cursor
        resp = twitch_get("games/top", params, client_id, token)
        batch = resp.get("data", [])
        if not batch:
            break
        for g in batch:
            if is_game_category(g["name"]) and len(games) < count:
                games.append(g)
        fetched += len(batch)
        cursor = resp.get("pagination", {}).get("cursor")
        if not cursor:
            break
    return games

def enrich_with_streams(client_id, token, games, count=15):
    """Get viewer + stream counts for top N games."""
    results = []
    for game in games[:count]:
        game_id = game["id"]
        game_name = game["name"]
        resp = twitch_get("streams", {"game_id": game_id, "first": 100}, client_id, token)
        streams = resp.get("data", [])
        total_viewers = sum(s.get("viewer_count", 0) for s in streams)
        stream_count = len(streams)
        results.append({
            "id": game_id,
            "name": game_name,
            "viewers": total_viewers,
            "streams": stream_count,
        })
    return results

def fetch_breakout_games(client_id, token, top_game_ids, count=50):
    """Fetch games outside top N to find breakout titles.
    We look at lower-ranked games and compare to yesterday's snapshot."""
    games = fetch_top_games(client_id, token, count=count)
    breakout_candidates = [g for g in games if g["id"] not in top_game_ids]
    # Enrich top 20 candidates with stream data
    results = []
    for game in breakout_candidates[:20]:
        game_id = game["id"]
        game_name = game["name"]
        resp = twitch_get("streams", {"game_id": game_id, "first": 100}, client_id, token)
        streams = resp.get("data", [])
        total_viewers = sum(s.get("viewer_count", 0) for s in streams)
        stream_count = len(streams)
        results.append({
            "id": game_id,
            "name": game_name,
            "viewers": total_viewers,
            "streams": stream_count,
        })
    return results

def fetch_top_by_language(client_id, token, lang_code, limit=3):
    """Get top games for a specific language by looking at top streams."""
    resp = twitch_get("streams", {"language": lang_code, "first": 100}, client_id, token)
    streams = resp.get("data", [])
    # Aggregate viewers per game
    game_viewers = {}
    game_names = {}
    game_ids = {}
    for s in streams:
        gid = s.get("game_id", "")
        gname = s.get("game_name", "")
        if not gid or not gname or not is_game_category(gname):
            continue
        game_viewers[gid] = game_viewers.get(gid, 0) + s.get("viewer_count", 0)
        game_names[gid] = gname
        game_ids[gid] = gid
    # Sort by viewers
    ranked = sorted(game_viewers.items(), key=lambda x: -x[1])[:limit]
    return [(game_names[gid], viewers) for gid, viewers in ranked]

# ── Steam wishlists ──────────────────────────────────────────────────────────

def fetch_steam_wishlisted():
    """Fetch Steam's most wishlisted upcoming games."""
    import re
    url = "https://store.steampowered.com/search/results/"
    params = {
        "filter": "popularwishlist",
        "ignore_preferences": 1,
        "json": 1,
        "count": 25,
        "cc": "us",
        "l": "english"
    }
    data = steam_get(url, params)
    if not data:
        return []

    results = []
    for item in data.get("items", []):
        name = item.get("name", "")
        logo = item.get("logo", "")
        # Extract appid from logo URL: /apps/APPID/
        m = re.search(r"/apps/(\d+)/", logo)
        appid = m.group(1) if m else ""
        if name and appid:
            results.append({"appid": appid, "name": name})
    return results[:15]

# ── IGDB data ─────────────────────────────────────────────────────────────────

def fetch_upcoming_releases(client_id, token):
    """Notable games releasing in next 60 days with exact dates.
    Filters to hypes >= 3 to exclude shovelware."""
    now_dt = datetime.now()
    now = int(now_dt.timestamp())
    future = int((now_dt + timedelta(days=60)).timestamp())

    # Fetch all hyped games in next 60 days, paginated
    games = []
    seen_ids = set()
    for offset in range(0, 1000, 500):
        body = (
            f"fields name,url,hypes,follows,total_rating,first_release_date,platforms.name;"
            f" where first_release_date >= {now} & first_release_date <= {future} & hypes >= 3;"
            f" sort first_release_date asc; limit 500; offset {offset};"
        )
        page = igdb_post("games", body, client_id, token) or []
        for g in page:
            if g["id"] not in seen_ids:
                games.append(g)
                seen_ids.add(g["id"])
        if len(page) < 500:
            break

    # Get human-readable dates + date_format from release_dates endpoint
    # date_format: 0=YYYYMMDD (exact day), 1=YYYYMM (month), 2=YYYYQ (quarter), 3=YYYY, 4=TBD
    rd_map = {}
    game_ids = [str(g["id"]) for g in games]
    for batch_start in range(0, len(game_ids), 500):
        batch = game_ids[batch_start:batch_start + 500]
        ids_str = ",".join(batch)
        rd_body = (
            f"fields game,date,human,platform.name,date_format;"
            f" where game = ({ids_str});"
            f" limit 500;"
        )
        rd_raw = igdb_post("release_dates", rd_body, client_id, token) or []
        for entry in rd_raw:
            gid = entry.get("game")
            if not gid:
                continue
            if gid not in rd_map:
                rd_map[gid] = {
                    "human": entry.get("human", ""),
                    "date_format": entry.get("date_format", 99),
                    "platforms": []
                }
            else:
                if entry.get("date_format", 99) < rd_map[gid]["date_format"]:
                    rd_map[gid]["human"] = entry.get("human", "")
                    rd_map[gid]["date_format"] = entry.get("date_format", 99)
            if entry.get("platform"):
                rd_map[gid]["platforms"].append(entry["platform"])

    results = []
    for g in games:
        gid = g.get("id")
        rd = rd_map.get(gid, {})
        ts = g.get("first_release_date")
        date_fmt = rd.get("date_format", 99)

        # Only include games with confirmed exact dates (date_format 0 = YYYYMMDD)
        if date_fmt != 0:
            continue

        human = rd.get("human", "")
        if not human and ts:
            human = datetime.fromtimestamp(ts).strftime("%b %d, %Y")
        results.append({
            "name": g.get("name", ""),
            "url": g.get("url", ""),
            "hypes": g.get("hypes", 0) or 0,
            "follows": g.get("follows", 0) or 0,
            "total_rating": g.get("total_rating"),
            "date": ts,
            "human": human,
            "platforms": rd.get("platforms", g.get("platforms", []))
        })
    # Sort chronologically
    results.sort(key=lambda x: x.get("date") or 0)
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

def fetch_igdb_popular(client_id, token):
    """Get most popular upcoming/unreleased games from IGDB popularity primitives."""
    # Fetch top 50 by want-to-play, then filter to unreleased
    body = "fields game_id,value,popularity_type; where popularity_type = 7; sort value desc; limit 50;"
    raw = igdb_post("popularity_primitives", body, client_id, token)
    if not raw:
        return []

    game_ids = [str(entry["game_id"]) for entry in raw if "game_id" in entry]
    if not game_ids:
        return []

    # Resolve game names — filter to unreleased or future release dates
    now = int(datetime.now().timestamp())
    ids_str = ",".join(game_ids)
    body2 = (
        f"fields name,first_release_date,follows,url,platforms.name;"
        f" where id = ({ids_str}) & (first_release_date > {now} | first_release_date = null);"
        f" limit 50;"
    )
    games = igdb_post("games", body2, client_id, token)

    pop_map = {entry["game_id"]: entry["value"] for entry in raw}
    for g in games:
        g["popularity"] = pop_map.get(g["id"], 0)

    return sorted(games, key=lambda x: -x.get("popularity", 0))[:10]

def match_wishlisted_to_igdb(wishlisted, client_id, token):
    """Cross-reference Steam wishlisted games with IGDB for release dates."""
    results = []
    for game in wishlisted[:10]:
        name = game["name"]
        # Search IGDB for this game
        safe_name = name.replace('"', '\\"')
        body = f'search "{safe_name}"; fields name,first_release_date,follows,url,platforms.name; limit 1;'
        matches = igdb_post("games", body, client_id, token)
        if matches:
            match = matches[0]
            match["steam_appid"] = game["appid"]
            results.append(match)
        else:
            results.append({
                "name": name,
                "steam_appid": game["appid"],
                "first_release_date": None,
                "url": "",
                "follows": 0,
            })
    return results

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

    # ── 1. Twitch: Top 5 Most Streamed Games ──
    print("Fetching Twitch top games...", file=sys.stderr)
    all_games = fetch_top_games(client_id, token, count=50)
    top15 = enrich_with_streams(client_id, token, all_games, count=15)
    # Also enrich positions 16-50 for breakout detection
    top15_ids = {g["id"] for g in all_games[:15]}

    lines.append("<b>TOP 15 MOST STREAMED</b>")
    lines.append("")
    for i, g in enumerate(top15, 1):
        name = g["name"]
        viewers = g["viewers"]
        streams = g["streams"]
        change = pct_change_str(viewers, prev_viewers.get(name, 0))
        link = twitch_link(name)
        lines.append(f"{i}. {link}")
        lines.append(f"   {fmt_num(viewers)} viewers · {streams}+ streams{change}")
    lines.append("")

    # ── 2. Breakout Games (surging in viewers/streams) ──
    print("Fetching breakout candidates...", file=sys.stderr)
    breakout_raw = fetch_breakout_games(client_id, token, top15_ids, count=50)

    # Build full viewer map for snapshot
    all_enriched = top15 + breakout_raw
    current_viewers = {g["name"]: g["viewers"] for g in all_enriched}
    current_streams = {g["name"]: g["streams"] for g in all_enriched}

    if prev_viewers:
        # Score breakout by: % viewer increase OR high stream count for new entries
        breakout_scored = []
        for g in breakout_raw:
            name = g["name"]
            curr_v = g["viewers"]
            prev_v = prev_viewers.get(name, 0)

            if prev_v >= 200 and curr_v > prev_v:
                # Returning game surging
                pct = ((curr_v - prev_v) / prev_v) * 100
                breakout_scored.append({**g, "score": pct, "type": "surge",
                    "label": f"{fmt_num(prev_v)} → {fmt_num(curr_v)} (+{pct:.0f}%)"})
            elif prev_v == 0 and curr_v >= 500:
                # New entry with significant viewers
                breakout_scored.append({**g, "score": curr_v, "type": "new",
                    "label": f"{fmt_num(curr_v)} viewers [NEW]"})

        breakout_scored.sort(key=lambda x: -x["score"])
        breakout_top = breakout_scored[:10]
    else:
        # No previous data — show top 10 by viewers outside top 5
        breakout_top = sorted(breakout_raw, key=lambda x: -x["viewers"])[:10]
        for g in breakout_top:
            g["label"] = f"{fmt_num(g['viewers'])} viewers"
            g["type"] = "current"

    if breakout_top:
        lines.append("<b>BREAKOUT — SURGING IN ATTENTION</b>")
        lines.append("")
        for g in breakout_top:
            link = twitch_link(g["name"])
            streams = g["streams"]
            lines.append(f"  {link} — {g['label']} · {streams}+ streams")
        lines.append("")

    # ── 3. Top 3 Games by Language ──
    print("Fetching language breakdown...", file=sys.stderr)
    lang_section = []
    for code, lang_name in sorted(TRACKED_LANGUAGES.items(), key=lambda x: x[1]):
        top3 = fetch_top_by_language(client_id, token, code, limit=3)
        if top3:
            games_str = " · ".join(f"{safe_html(n)} ({fmt_num(v)})" for n, v in top3)
            lang_section.append(f"  <b>{lang_name}:</b> {games_str}")

    if lang_section:
        lines.append("<b>TOP GAMES BY LANGUAGE</b>")
        lines.append("")
        lines.extend(lang_section)
        lines.append("")

    # ── 4. Most Wishlisted on Steam → IGDB release dates ──
    print("Fetching Steam wishlisted games...", file=sys.stderr)
    wishlisted = fetch_steam_wishlisted()
    if wishlisted:
        print("Cross-referencing with IGDB...", file=sys.stderr)
        wishlist_igdb = match_wishlisted_to_igdb(wishlisted, client_id, token)
        lines.append("<b>MOST WISHLISTED (Steam) + RELEASE DATES</b>")
        lines.append("")
        for i, g in enumerate(wishlist_igdb[:10], 1):
            name = g.get("name", "Unknown")
            appid = g.get("steam_appid", "")
            s_link = steam_link(name, appid) if appid else safe_html(name)
            release = fmt_date(g.get("first_release_date"))
            follows = g.get("follows", 0) or 0
            meta = [release]
            if follows:
                meta.append(f"{fmt_num(follows)} IGDB follows")
            igdb_url = g.get("url", "")
            if igdb_url:
                meta.append(f'<a href="{igdb_url}">IGDB</a>')
            lines.append(f"  {i}. {s_link} — {' · '.join(meta)}")
        lines.append("")

    # ── 5. IGDB Most Popular (want-to-play) ──
    print("Fetching IGDB popularity...", file=sys.stderr)
    popular = fetch_igdb_popular(client_id, token)
    if popular:
        lines.append("<b>IGDB — MOST WANTED</b>")
        lines.append("")
        for g in popular[:10]:
            link = igdb_link(g)
            date = fmt_date(g.get("first_release_date"))
            follows = g.get("follows", 0) or 0
            meta = []
            if date != "TBA":
                meta.append(date)
            if follows:
                meta.append(f"{fmt_num(follows)} follows")
            meta_str = f" — {' · '.join(meta)}" if meta else ""
            lines.append(f"  {link}{meta_str}")
        lines.append("")

    # ── 6. Upcoming Releases (next 60 days, notable only) ──
    print("Fetching upcoming releases...", file=sys.stderr)
    upcoming = fetch_upcoming_releases(client_id, token)
    if upcoming:
        lines.append("<b>UPCOMING RELEASES (60 DAYS)</b>")
        lines.append("")
        for g in upcoming[:30]:  # Telegram gets top 30
            name = safe_html(g["name"])
            url = g.get("url", "")
            link = f'<a href="{url}">{name}</a>' if url else name
            date = g.get("human", "TBA")
            plats = fmt_platforms(g.get("platforms", []))
            meta = []
            if plats:
                meta.append(plats)
            hypes = g.get("hypes", 0)
            if hypes:
                meta.append(f"{fmt_num(hypes)} hype")
            meta_str = f" — {' · '.join(meta)}" if meta else ""
            lines.append(f"  {date}: {link}{meta_str}")
        lines.append("")

    # ── 7. Just Released (7 days) ──
    just_released = fetch_just_released(client_id, token)
    if just_released:
        lines.append("<b>JUST RELEASED (7 DAYS)</b>")
        lines.append("")
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

    # ── Save snapshot ──
    # Format releases for dashboard (full list, not capped like Telegram)
    releasing_data = []
    for g in upcoming:
        plats = fmt_platforms(g.get("platforms", []))
        releasing_data.append({
            "name": g.get("name", ""),
            "date": g.get("human", "TBA"),
            "platforms": plats,
            "hypes": g.get("hypes", 0),
            "igdb_url": g.get("url", ""),
        })
    snapshot_data = {
        "top_game_names": [g["name"] for g in all_enriched[:50]],
        "viewers": {g["name"]: g["viewers"] for g in all_enriched},
        "streams": {g["name"]: g["streams"] for g in all_enriched},
        "releasing": releasing_data,
        "date": datetime.now().isoformat()
    }
    save_snapshot(snapshots, today, snapshot_data)

    report = "\n".join(lines)
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

    game_appearances = {}
    for snap in period_snaps.values():
        for name in snap.get("top_game_names", []):
            game_appearances[name] = game_appearances.get(name, 0) + 1

    total_days = len(period_snaps)
    consistent = sorted(game_appearances.items(), key=lambda x: -x[1])[:10]

    lines.append(f"<b>MOST CONSISTENT (top games for {total_days} days)</b>")
    for name, count in consistent:
        pct = (count / total_days) * 100
        lines.append(f"  {twitch_link(name)} — {count}/{total_days} days ({pct:.0f}%)")
    lines.append("")

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
            lines.append(f"  {twitch_link(name)}: {fmt_num(prev)} → {fmt_num(curr)} (+{pct:.0f}%)")
        lines.append("")

    if fallers:
        lines.append(f"<b>BIGGEST FALLERS ({days}d)</b>")
        for name, curr, prev, pct in fallers:
            lines.append(f"  {twitch_link(name)}: {fmt_num(prev)} → {fmt_num(curr)} ({pct:.0f}%)")
        lines.append("")

    first_names = set(first_snap.get("top_game_names", []))
    last_names = set(last_snap.get("top_game_names", []))
    new_this_period = last_names - first_names
    dropped = first_names - last_names

    if new_this_period:
        lines.append(f"<b>NEW ENTRIES THIS {period_name}</b>")
        for name in sorted(new_this_period):
            viewers = last_v.get(name, 0)
            lines.append(f"  {twitch_link(name)} — {fmt_num(viewers)} viewers")
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
