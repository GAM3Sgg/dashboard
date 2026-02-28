#!/usr/bin/env python3
"""
Steam Trending Games Daily Report v3
Tracks trending, top sellers, most played, rising games, reviews, genres,
and most wishlisted upcoming games.
Stores daily snapshots for day-over-day, weekly, and monthly comparison.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# Config
CREDENTIALS_FILE = Path.home() / ".openclaw" / "credentials" / "steam-api.json"
DATA_DIR = Path(__file__).parent / "steam_data"
SNAPSHOT_FILE = DATA_DIR / "daily_snapshots.json"

# Rate limiting
REQUEST_DELAY = 0.3  # seconds between API calls

# Blacklist: hardware and non-game items (by appid and name patterns)
BLACKLIST_APPIDS = {
    "1675200",   # Steam Deck
    "2347570",   # Steam Deck OLED
    "353370",    # Steam Controller
    "353380",    # Steam Link
}
BLACKLIST_NAMES = {"steam deck", "steam controller", "steam link", "valve index"}

GAME_TYPE_LABELS = {
    "demo": "Demo",
    "dlc": "DLC",
    "mod": "Mod",
    "video": "Video",
    "hardware": "Hardware",
    "music": "Soundtrack",
}

# Normalize common non-English genre names to English
GENRE_NORMALIZE = {
    "Acción": "Action", "Akcja": "Action", "Экшены": "Action", "Ação": "Action",
    "Aktion": "Action", "アクション": "Action", "액션": "Action",
    "Aventura": "Adventure", "Przygodowe": "Adventure", "Приключения": "Adventure",
    "Abenteuer": "Adventure",
    "Estrategia": "Strategy", "Strategie": "Strategy", "Стратегии": "Strategy",
    "Simulación": "Simulation", "Symulacje": "Simulation", "Симуляторы": "Simulation",
    "Deporte": "Sports", "Спорт": "Sports",
    "Carreras": "Racing", "Гонки": "Racing",
    "Rol": "RPG", "Ролевые": "RPG",
    "Indie": "Indie", "Казуальные": "Casual", "Gelegenheit": "Casual",
}


def load_api_key() -> str:
    with open(CREDENTIALS_FILE, encoding="utf-8") as f:
        return json.load(f)["api_key"]


def api_get(url: str, params: dict = None) -> dict:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "SteamTrendingBot/3.0",
        "Accept": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  API error: {e}")
        return {}


def is_blacklisted(appid: str, name: str) -> bool:
    if appid in BLACKLIST_APPIDS:
        return True
    return any(bl in name.lower() for bl in BLACKLIST_NAMES)


def get_search_results(filter_type: str, count: int = 25) -> list:
    data = api_get("https://store.steampowered.com/search/results/", {
        "filter": filter_type,
        "json": "1",
        "start": "0",
        "count": str(count),
        "cc": "us",
        "l": "english",
        "infinite": "1",
    })
    if not data:
        return []
    html = data.get("results_html", "")
    if not html:
        return []
    return parse_search_html(html, count)


def parse_search_html(html: str, max_items: int = 25) -> list:
    games = []
    pattern = r'data-ds-appid="([^"]+)".*?class="title">(.*?)</span>'
    for match in re.finditer(pattern, html, re.DOTALL):
        if len(games) >= max_items:
            break
        raw_appid = match.group(1).strip()
        appid = raw_appid.split(",")[0].strip()
        name = match.group(2).strip()
        if is_blacklisted(appid, name):
            continue
        price = ""
        price_match = re.search(
            rf'data-ds-appid="{re.escape(raw_appid)}".*?class="discount_final_price">(.*?)</(?:div|span)',
            html, re.DOTALL
        )
        if price_match:
            price = re.sub(r'<[^>]+>', '', price_match.group(1)).strip()
        games.append({"appid": appid, "name": name, "price": price})
    return games


def get_featured_categories() -> dict:
    return api_get("https://store.steampowered.com/api/featuredcategories/", {"cc": "us", "l": "english"})


def get_current_players(appid: int, api_key: str) -> int:
    data = api_get("https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/", {
        "key": api_key,
        "appid": str(appid),
    })
    resp = data.get("response", {})
    if resp.get("result") == 1:
        return resp.get("player_count", 0)
    return 0


def get_app_details(appid: str) -> dict:
    data = api_get("https://store.steampowered.com/api/appdetails/", {
        "appids": appid,
        "cc": "us",
        "l": "english",
    })
    if not data:
        return {}
    app_data = data.get(appid, {})
    if app_data.get("success"):
        return app_data.get("data", {})
    return {}


def get_review_summary(appid: str) -> dict:
    data = api_get(f"https://store.steampowered.com/appreviews/{appid}", {
        "json": "1",
        "language": "all",
        "purchase_type": "all",
        "num_per_page": "0",
        "review_type": "all",
    })
    if not data or not data.get("success"):
        return {}
    summary = data.get("query_summary", {})
    return {
        "score_desc": summary.get("review_score_desc", ""),
        "total_positive": summary.get("total_positive", 0),
        "total_negative": summary.get("total_negative", 0),
        "total_reviews": summary.get("total_reviews", 0),
    }


def enrich_game(game: dict, api_key: str, fetch_reviews: bool = True) -> dict:
    appid = game["appid"]

    # Player count
    players = get_current_players(int(appid), api_key)
    game["players"] = players
    time.sleep(REQUEST_DELAY)

    # App details
    details = get_app_details(appid)
    time.sleep(REQUEST_DELAY)

    if details:
        game["type"] = details.get("type", "game")
        genres = details.get("genres", [])
        genre_names = [g.get("description", "") for g in genres[:3]]
        game["genres"] = [GENRE_NORMALIZE.get(gn, gn) for gn in genre_names]
        game["is_early_access"] = "Early Access" in game["genres"]
        release = details.get("release_date", {})
        game["coming_soon"] = release.get("coming_soon", False)
        game["release_date"] = release.get("date", "")
        if details.get("is_free"):
            game["is_free"] = True
            game["price_str"] = "Free"
        else:
            game["is_free"] = False
            price_info = details.get("price_overview", {})
            if price_info:
                final_cents = price_info.get("final", 0)
                currency = price_info.get("currency", "USD")
                if currency == "USD" and final_cents:
                    game["price_str"] = f"${final_cents / 100:.2f}"
                else:
                    game["price_str"] = price_info.get("final_formatted", game.get("price", ""))
                game["discount_pct"] = price_info.get("discount_percent", 0)
            else:
                game["price_str"] = game.get("price", "")
    else:
        game.setdefault("type", "game")
        game.setdefault("genres", [])
        game.setdefault("is_early_access", False)
        game.setdefault("coming_soon", False)
        game.setdefault("release_date", "")
        game.setdefault("is_free", game.get("price", "").lower() in ("free", "free to play", ""))
        game.setdefault("price_str", game.get("price", ""))

    if fetch_reviews:
        review = get_review_summary(appid)
        game["review_desc"] = review.get("score_desc", "")
        game["review_positive"] = review.get("total_positive", 0)
        game["review_negative"] = review.get("total_negative", 0)
        game["review_total"] = review.get("total_reviews", 0)
        time.sleep(REQUEST_DELAY)

    return game


def load_snapshots() -> dict:
    if not SNAPSHOT_FILE.exists():
        return {}
    try:
        with open(SNAPSHOT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_previous_snapshot(snapshots: dict, days_ago: int = 1) -> dict:
    target = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    candidates = sorted([d for d in snapshots.keys() if d <= target], reverse=True)
    if candidates:
        return snapshots[candidates[0]]
    return {}


def save_snapshot(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    snapshots = load_snapshots()
    today = datetime.now().strftime("%Y-%m-%d")
    snapshots[today] = data
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    snapshots = {k: v for k, v in snapshots.items() if k >= cutoff}
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshots, f, indent=2, ensure_ascii=False)


def fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n:,}"
    return str(n)


def pct_change(current: int, previous: int) -> str:
    if not previous or previous <= 0:
        return ""
    change = ((current - previous) / previous) * 100
    arrow = "+" if change >= 0 else ""
    return f"{arrow}{change:.0f}%"


def parse_release_date(date_str: str):
    """Try to parse a Steam release date string. Returns datetime or None."""
    for fmt in ("%d %b, %Y", "%b %d, %Y", "%d %B, %Y", "%B %d, %Y", "%b %Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def is_just_launched(game: dict) -> bool:
    """Check if game launched in the last 48 hours."""
    if game.get("coming_soon") or not game.get("release_date"):
        return False
    rd = parse_release_date(game["release_date"])
    return rd is not None and (datetime.now() - rd).days <= 2


def steam_url(appid: str) -> str:
    """Build a Steam store URL for a game."""
    return f"https://store.steampowered.com/app/{appid}"


def steam_link(name: str, appid: str) -> str:
    """Build an HTML hyperlink to a Steam store page."""
    url = steam_url(appid)
    # Escape HTML special chars in name
    safe_name = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="{url}">{safe_name}</a>'


def game_label(game: dict) -> str:
    parts = []
    if game.get("coming_soon"):
        rd = game.get("release_date", "TBD")
        parts.append(f"Coming {rd}")
    elif game.get("is_early_access"):
        parts.append("Early Access")
    elif game.get("type", "game") in GAME_TYPE_LABELS:
        parts.append(GAME_TYPE_LABELS[game["type"]])
    return " | ".join(parts)


def format_game_line(i: int, game: dict, prev_players: dict, prev_names: set,
                     show_price: bool = False) -> str:
    name = game.get("name", "Unknown")
    appid = game.get("appid", "")
    players = game.get("players", 0)
    url = steam_url(appid) if appid else ""

    badges = []
    if prev_names and name not in prev_names:
        badges.append("[NEW]")
    if is_just_launched(game):
        badges.append("[JUST LAUNCHED]")
    badge_str = (" " + " ".join(badges)) if badges else ""

    # Player count with day-over-day change
    player_str = ""
    if players > 0:
        prev_p = prev_players.get(appid, 0)
        change = pct_change(players, prev_p) if prev_p > 0 else ""
        change_str = f" {change}" if change else ""
        player_str = f" | {fmt_num(players)} playing now{change_str}"

    price_str = ""
    if show_price and game.get("price_str"):
        price_str = f" | {game['price_str']}"

    label = game_label(game)
    label_str = f" [{label}]" if label else ""

    linked_name = steam_link(name, appid) if appid else name

    return f"{i}. {linked_name}{badge_str}{player_str}{price_str}{label_str}"


def build_daily_report() -> str:
    api_key = load_api_key()
    snapshots = load_snapshots()
    previous = get_previous_snapshot(snapshots)
    prev_players = previous.get("player_counts", {})
    prev_trending_names = {g["name"] for g in previous.get("trending", [])}
    prev_topseller_names = {g["name"] for g in previous.get("topsellers", [])}
    prev_reviews = previous.get("reviews", {})

    # Fetch lists
    print("Fetching New & Trending...")
    trending_raw = get_search_results("popularnew", 20)
    time.sleep(REQUEST_DELAY)

    print("Fetching Top Sellers...")
    topsellers_raw = get_search_results("topsellers", 25)
    time.sleep(REQUEST_DELAY)

    print("Fetching Most Wishlisted...")
    wishlisted_raw = get_search_results("popularwishlist", 10)
    time.sleep(REQUEST_DELAY)

    print("Fetching Featured Categories...")
    featured = get_featured_categories()
    time.sleep(REQUEST_DELAY)

    # Collect unique appids to enrich
    all_games = {}
    for g in trending_raw[:15]:
        all_games.setdefault(g["appid"], g)
    for g in topsellers_raw[:20]:
        all_games.setdefault(g["appid"], g)

    print(f"Enriching {len(all_games)} unique games (details + players + reviews)...")
    for i, (appid, game) in enumerate(all_games.items()):
        print(f"  [{i + 1}/{len(all_games)}] {game.get('name', appid)}")
        enrich_game(game, api_key, fetch_reviews=True)

    # Split trending into released vs unreleased
    trending = []
    unreleased_trending = []
    for g in trending_raw[:15]:
        enriched = all_games.get(g["appid"], g)
        if enriched.get("coming_soon"):
            unreleased_trending.append(enriched)
        else:
            trending.append(enriched)

    # Split top sellers: released paid / released free / unreleased (pre-orders)
    topsellers_paid = []
    topsellers_free = []
    unreleased_sellers = []
    for g in topsellers_raw[:20]:
        enriched = all_games.get(g["appid"], g)
        if enriched.get("coming_soon"):
            unreleased_sellers.append(enriched)
        elif enriched.get("is_free"):
            topsellers_free.append(enriched)
        else:
            topsellers_paid.append(enriched)

    # Merge unreleased from both lists (deduped)
    unreleased_all = {g["appid"]: g for g in unreleased_trending + unreleased_sellers}

    # Extract specials from featured
    specials = []
    if featured:
        for item in featured.get("specials", {}).get("items", []):
            if not is_blacklisted(str(item.get("id", "")), item.get("name", "")):
                specials.append({
                    "appid": str(item.get("id", "")),
                    "name": item.get("name", "Unknown"),
                    "discount": item.get("discount_percent", 0),
                    "final": item.get("final_price", 0),
                })

    # Save snapshot
    player_counts = {aid: g.get("players", 0) for aid, g in all_games.items() if g.get("players", 0) > 0}
    reviews_snapshot = {}
    for aid, g in all_games.items():
        if g.get("review_desc"):
            reviews_snapshot[aid] = {
                "desc": g["review_desc"],
                "positive": g.get("review_positive", 0),
                "negative": g.get("review_negative", 0),
            }

    save_snapshot({
        "trending": [{"name": g.get("name", ""), "appid": g.get("appid", "")} for g in trending_raw[:15]],
        "topsellers": [{"name": g.get("name", ""), "appid": g.get("appid", "")} for g in topsellers_raw[:20]],
        "player_counts": player_counts,
        "reviews": reviews_snapshot,
        "date": datetime.now().isoformat(),
    })

    # ========================
    # BUILD REPORT
    # ========================
    now = datetime.now()
    lines = []
    lines.append("STEAM TRENDING REPORT")
    lines.append(f"{now.strftime('%A, %B %d %Y')} @ {now.strftime('%I:%M %p')}")
    lines.append("")

    # --- NEW & TRENDING ---
    # Note: ordered by Steam's algorithm (sales velocity, revenue, engagement) not player count
    lines.append("NEW & TRENDING (ranked by Steam's algorithm)")
    lines.append("-" * 30)
    for i, g in enumerate(trending, 1):
        lines.append(format_game_line(i, g, prev_players, prev_trending_names))
    lines.append("")

    # --- TOP SELLERS (PAID) ---
    if topsellers_paid:
        lines.append("TOP SELLERS - PAID (ranked by revenue)")
        lines.append("-" * 30)
        for i, g in enumerate(topsellers_paid[:5], 1):
            lines.append(format_game_line(i, g, prev_players, prev_topseller_names, show_price=True))
        lines.append("")

    # --- TOP FREE-TO-PLAY ---
    if topsellers_free:
        lines.append("TOP FREE-TO-PLAY")
        lines.append("-" * 30)
        for i, g in enumerate(topsellers_free[:5], 1):
            lines.append(format_game_line(i, g, prev_players, prev_topseller_names))
        lines.append("")

    # --- PLAYER COUNT MOVERS (day-over-day) ---
    if prev_players:
        movers = []
        name_lookup = {aid: g.get("name", f"App {aid}") for aid, g in all_games.items()}
        for appid, count in player_counts.items():
            prev_p = prev_players.get(appid, 0)
            if prev_p > 100:
                abs_change = count - prev_p
                pct = ((count - prev_p) / prev_p) * 100
                movers.append((appid, count, prev_p, abs_change, pct))

        rising = sorted([m for m in movers if m[3] > 0], key=lambda x: x[3], reverse=True)
        if rising:
            lines.append("RISING (biggest player gains vs yesterday)")
            lines.append("-" * 30)
            for appid, count, prev_p, abs_change, pct in rising[:6]:
                name = name_lookup.get(appid, f"App {appid}")
                lines.append(f"  +{fmt_num(abs_change)} ({pct:+.0f}%) {name} ({fmt_num(prev_p)} -> {fmt_num(count)})")
            lines.append("")

        falling = sorted([m for m in movers if m[4] < -15], key=lambda x: x[4])
        if falling:
            lines.append("FALLING (biggest player drops vs yesterday)")
            lines.append("-" * 30)
            for appid, count, prev_p, abs_change, pct in falling[:5]:
                name = name_lookup.get(appid, f"App {appid}")
                lines.append(f"  {fmt_num(abs_change)} ({pct:+.0f}%) {name} ({fmt_num(prev_p)} -> {fmt_num(count)})")
            lines.append("")

    # --- NEW ENTRIES TODAY ---
    if prev_trending_names or prev_topseller_names:
        new_in_trending = [g for g in trending if g.get("name", "") not in prev_trending_names]
        new_in_topsellers = [g for g in topsellers_paid + topsellers_free if g.get("name", "") not in prev_topseller_names]
        if new_in_trending or new_in_topsellers:
            lines.append("NEW ENTRIES TODAY")
            lines.append("-" * 30)
            seen = set()
            for g in new_in_trending:
                name = g.get("name", "")
                if name and name not in seen:
                    lines.append(f"  Trending: {steam_link(name, g.get('appid', ''))}")
                    seen.add(name)
            for g in new_in_topsellers:
                name = g.get("name", "")
                if name and name not in seen:
                    lines.append(f"  Top Seller: {steam_link(name, g.get('appid', ''))}")
                    seen.add(name)
            lines.append("")

    # --- REVIEW SPOTLIGHT (shifts only: sentiment changes + review count spikes) ---
    review_entries = []
    for aid, g in all_games.items():
        desc = g.get("review_desc", "")
        if not desc:
            continue
        prev_rev = prev_reviews.get(aid, {})
        prev_desc = prev_rev.get("desc", "")
        prev_total = prev_rev.get("positive", 0) + prev_rev.get("negative", 0)
        curr_total = g.get("review_total", 0)
        name = g.get("name", "")
        link = steam_link(name, aid)
        # Sentiment shifted since yesterday
        if prev_desc and prev_desc != desc:
            review_entries.append(
                f"  {link}: {prev_desc} -> {desc} ({fmt_num(curr_total)} reviews)")
        # Sharp review count spike (>20% more reviews in one day = lots of new players reviewing)
        elif prev_total > 100 and curr_total > prev_total * 1.2:
            new_reviews = curr_total - prev_total
            review_entries.append(
                f"  {link}: +{fmt_num(new_reviews)} new reviews today ({desc}, {fmt_num(curr_total)} total)")

    if review_entries:
        lines.append("REVIEW SPOTLIGHT (changes only)")
        lines.append("-" * 30)
        for entry in review_entries:
            lines.append(entry)
        lines.append("")

    # --- BIGGEST DEALS ---
    if specials:
        lines.append("BIGGEST DEALS")
        lines.append("-" * 30)
        top_deals = sorted(specials, key=lambda x: x.get("discount", 0), reverse=True)[:6]
        for deal in top_deals:
            name = deal.get("name", "Unknown")
            appid = deal.get("appid", "")
            disc = deal.get("discount", 0)
            final = deal.get("final", 0)
            price_str = f" (${final / 100:.2f})" if final else ""
            linked = steam_link(name, appid) if appid else name
            lines.append(f"  -{disc}% {linked}{price_str}")
        lines.append("")

    # --- MOST WISHLISTED (upcoming games by wishlist popularity) ---
    if wishlisted_raw:
        lines.append("MOST WISHLISTED (upcoming, ranked by wishlist popularity)")
        lines.append("-" * 30)
        for i, g in enumerate(wishlisted_raw[:10], 1):
            lines.append(f"  {i}. {steam_link(g['name'], g.get('appid', ''))}")
        lines.append("")

    # --- WATCH THIS WEEK (upcoming releases, pre-orders on charts, just launched) ---
    watch = []
    for appid, g in unreleased_all.items():
        rd = g.get("release_date", "TBD")
        price = g.get("price_str", "")
        price_str = f" | {price}" if price and price != "Free" else ""
        badge = ""
        if g.get("is_early_access"):
            badge = " [Early Access]"
        elif g.get("type") == "demo":
            badge = " [Demo]"
        watch.append(f"  -> {steam_link(g['name'], appid)} (launches {rd}, already charting){badge}{price_str}")
    for aid, g in all_games.items():
        if is_just_launched(g) and not g.get("coming_soon"):
            players = g.get("players", 0)
            player_str = f", {fmt_num(players)} players" if players > 0 else ""
            watch.append(f"  -> {steam_link(g['name'], aid)} (just launched{player_str})")

    if watch:
        lines.append("WATCH THIS WEEK")
        lines.append("-" * 30)
        seen = set()
        for w in watch[:6]:
            key = w.split("(")[0].strip()
            if key not in seen:
                lines.append(w)
                seen.add(key)
        lines.append("")

    # Check if listed on GAM3S.GG
    list_on_site = []
    for g in trending + topsellers_paid + topsellers_free:
        name = g.get("name", "")
        if not name:
            continue
        players = g.get("players", 0)
        if players < 10000:
            continue
        if name not in prev_trending_names and name not in prev_topseller_names and (prev_trending_names or prev_topseller_names):
            list_on_site.append((name, g.get("appid", ""), players))

    if list_on_site:
        lines.append("")
        lines.append("CHECK IF LISTED ON GAM3S.GG")
        seen = set()
        for name, appid, players in list_on_site[:5]:
            if name not in seen:
                lines.append(f"  -> {steam_link(name, appid)} -- {fmt_num(players)} players")
                seen.add(name)

    lines.append("")
    return "\n".join(lines)


def build_summary_report(period: str) -> str:
    snapshots = load_snapshots()
    if not snapshots:
        return f"No snapshot data available for {period} summary."

    days = 7 if period == "weekly" else 30
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    range_snapshots = {k: v for k, v in snapshots.items() if cutoff <= k <= today}
    if len(range_snapshots) < 2:
        return f"Need at least 2 days of data for {period} summary. Currently have {len(range_snapshots)} day(s)."

    dates = sorted(range_snapshots.keys())
    first_snap = range_snapshots[dates[0]]
    last_snap = range_snapshots[dates[-1]]

    lines = []
    period_label = "WEEKLY" if period == "weekly" else "MONTHLY (30-DAY)"
    lines.append(f"STEAM {period_label} SUMMARY")
    lines.append(f"{dates[0]} to {dates[-1]} ({len(dates)} days of data)")
    lines.append("")

    all_trending_names = {}
    all_topseller_names = {}

    for date, snap in sorted(range_snapshots.items()):
        for g in snap.get("trending", []):
            name = g.get("name", "")
            if name:
                all_trending_names[name] = all_trending_names.get(name, 0) + 1
        for g in snap.get("topsellers", []):
            name = g.get("name", "")
            if name:
                all_topseller_names[name] = all_topseller_names.get(name, 0) + 1

    name_lookup = {}
    for g in last_snap.get("trending", []) + last_snap.get("topsellers", []):
        if g.get("appid") and g.get("name"):
            name_lookup[g["appid"]] = g["name"]

    lines.append("MOST CONSISTENT TRENDING")
    lines.append("-" * 30)
    consistent = sorted(all_trending_names.items(), key=lambda x: x[1], reverse=True)
    for name, count in consistent[:10]:
        lines.append(f"  {name} -- {count}/{len(dates)} days")
    lines.append("")

    lines.append("MOST CONSISTENT TOP SELLERS")
    lines.append("-" * 30)
    consistent_sellers = sorted(all_topseller_names.items(), key=lambda x: x[1], reverse=True)
    for name, count in consistent_sellers[:10]:
        lines.append(f"  {name} -- {count}/{len(dates)} days")
    lines.append("")

    first_players = first_snap.get("player_counts", {})
    last_players = last_snap.get("player_counts", {})
    changes = []
    for appid in set(first_players.keys()) | set(last_players.keys()):
        fp = first_players.get(appid, 0)
        lp = last_players.get(appid, 0)
        if fp > 100 or lp > 100:
            abs_change = lp - fp
            pct = ((lp - fp) / max(fp, 1)) * 100 if fp > 0 else 0
            name = name_lookup.get(appid, f"App {appid}")
            changes.append((name, fp, lp, abs_change, pct))

    rising = sorted([c for c in changes if c[3] > 0], key=lambda x: x[3], reverse=True)
    if rising:
        lines.append(f"BIGGEST RISERS ({period.upper()})")
        lines.append("-" * 30)
        for name, fp, lp, abs_change, pct in rising[:8]:
            lines.append(f"  +{fmt_num(abs_change)} ({pct:+.0f}%) {name} ({fmt_num(fp)} -> {fmt_num(lp)})")
        lines.append("")

    falling = sorted([c for c in changes if c[3] < 0], key=lambda x: x[3])
    if falling:
        lines.append(f"BIGGEST FALLERS ({period.upper()})")
        lines.append("-" * 30)
        for name, fp, lp, abs_change, pct in falling[:8]:
            lines.append(f"  {fmt_num(abs_change)} ({pct:+.0f}%) {name} ({fmt_num(fp)} -> {fmt_num(lp)})")
        lines.append("")

    first_trending = {g["name"] for g in first_snap.get("trending", [])}
    last_trending = {g["name"] for g in last_snap.get("trending", [])}
    first_sellers = {g["name"] for g in first_snap.get("topsellers", [])}
    last_sellers = {g["name"] for g in last_snap.get("topsellers", [])}

    new_trending = last_trending - first_trending
    new_sellers = last_sellers - first_sellers
    if new_trending or new_sellers:
        lines.append(f"NEW THIS {period.upper()}")
        lines.append("-" * 30)
        for name in sorted(new_trending):
            lines.append(f"  Trending: {name}")
        for name in sorted(new_sellers - new_trending):
            lines.append(f"  Top Seller: {name}")
        lines.append("")

    dropped_trending = first_trending - last_trending
    dropped_sellers = first_sellers - last_sellers
    if dropped_trending or dropped_sellers:
        lines.append(f"DROPPED OFF THIS {period.upper()}")
        lines.append("-" * 30)
        for name in sorted(dropped_trending):
            lines.append(f"  Was trending: {name}")
        for name in sorted(dropped_sellers - dropped_trending):
            lines.append(f"  Was top seller: {name}")
        lines.append("")

    first_reviews = first_snap.get("reviews", {})
    last_reviews = last_snap.get("reviews", {})
    review_shifts = []
    for appid in set(first_reviews.keys()) & set(last_reviews.keys()):
        fd = first_reviews[appid].get("desc", "")
        ld = last_reviews[appid].get("desc", "")
        if fd and ld and fd != ld:
            name = name_lookup.get(appid, f"App {appid}")
            review_shifts.append(f"  {name}: {fd} -> {ld}")
    if review_shifts:
        lines.append("REVIEW SHIFTS")
        lines.append("-" * 30)
        for s in review_shifts:
            lines.append(s)
        lines.append("")

    lines.append("")
    return "\n".join(lines)


def build_report(mode: str = "daily") -> str:
    if mode in ("weekly", "monthly"):
        return build_summary_report(mode)
    return build_daily_report()


if __name__ == "__main__":
    mode = "daily"
    if "--weekly" in sys.argv:
        mode = "weekly"
    elif "--monthly" in sys.argv:
        mode = "monthly"

    report = build_report(mode)
    output_file = Path(__file__).parent / "steam_trending_output.txt"
    output_file.write_text(report, encoding="utf-8")
    print(f"\nReport saved to {output_file}")
    print("=" * 50)
    print(report)
