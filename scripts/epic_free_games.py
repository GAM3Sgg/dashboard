#!/usr/bin/env python3
"""
Epic Games Store Free Games — fetches current and upcoming free game promotions.
No authentication required (public endpoint).
"""

import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

REQUEST_DELAY = 0.3
DATA_DIR = Path(__file__).parent / "egs_data"
SNAPSHOT_FILE = DATA_DIR / "daily_snapshots.json"

EGS_FREE_URL = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"


# ── Helpers ──────────────────────────────────────────────────────────────────

def safe_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_store_url(game):
    """Build the EGS store page URL from available slug fields."""
    for mapping in game.get("offerMappings") or []:
        slug = mapping.get("pageSlug")
        if slug and mapping.get("pageType") == "productHome":
            return f"https://store.epicgames.com/en-US/p/{slug}"
    for mapping in (game.get("catalogNs") or {}).get("mappings") or []:
        slug = mapping.get("pageSlug")
        if slug:
            return f"https://store.epicgames.com/en-US/p/{slug}"
    slug = game.get("productSlug") or game.get("urlSlug", "")
    if slug and slug != "[]":
        return f"https://store.epicgames.com/en-US/p/{slug}"
    return ""


def get_offer_dates(game, upcoming=False):
    """Extract start/end dates from promotional offers."""
    promo = game.get("promotions") or {}
    key = "upcomingPromotionalOffers" if upcoming else "promotionalOffers"
    for offer_group in promo.get(key, []):
        for offer in offer_group.get("promotionalOffers", []):
            return offer.get("startDate", ""), offer.get("endDate", "")
    return "", ""


def is_free_promotion(offers_list):
    """Check if any offer in the list is a 100% discount (discountPercentage == 0 means free)."""
    for offer_group in offers_list:
        for offer in offer_group.get("promotionalOffers", []):
            ds = offer.get("discountSetting", {})
            if ds.get("discountPercentage") == 0:
                return True
    return False


def parse_game(game, upcoming=False):
    """Extract relevant fields from an EGS game element."""
    title = game.get("title", "")
    publisher = (game.get("seller") or {}).get("name", "")
    total_price = (game.get("price") or {}).get("totalPrice", {})
    fmt_price = total_price.get("fmtPrice", {})
    original_price = fmt_price.get("originalPrice", "")
    description = game.get("description", "")
    store_url = get_store_url(game)
    start_date, end_date = get_offer_dates(game, upcoming=upcoming)

    return {
        "title": title,
        "publisher": publisher,
        "original_price": original_price,
        "description": description,
        "store_url": store_url,
        "start_date": start_date,
        "end_date": end_date,
    }


# ── API ──────────────────────────────────────────────────────────────────────

def fetch_egs_free_games():
    """Fetch current and upcoming free games from EGS promotions endpoint."""
    params = urllib.parse.urlencode({
        "locale": "en-US",
        "country": "US",
        "allowCountries": "US",
    })
    url = f"{EGS_FREE_URL}?{params}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "OGGamingDashboard/1.0",
        "Accept": "application/json",
    })

    import time
    time.sleep(REQUEST_DELAY)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  EGS API error: {e}", file=sys.stderr)
        return [], []

    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])

    current_free = []
    upcoming_free = []

    for game in elements:
        promo = game.get("promotions") or {}
        current_offers = promo.get("promotionalOffers", [])
        upcoming_offers = promo.get("upcomingPromotionalOffers", [])

        if is_free_promotion(current_offers):
            current_free.append(parse_game(game, upcoming=False))
        elif is_free_promotion(upcoming_offers):
            upcoming_free.append(parse_game(game, upcoming=True))

    return current_free, upcoming_free


# ── Snapshots ────────────────────────────────────────────────────────────────

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


# ── Report builder ───────────────────────────────────────────────────────────

def fmt_date_short(iso_str):
    """Parse ISO date string to 'Mar 07' format."""
    if not iso_str:
        return "TBA"
    try:
        dt = datetime.strptime(iso_str[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%b %d")
    except (ValueError, TypeError):
        return "TBA"


def build_report():
    """Fetch EGS free games and build HTML report."""
    today = datetime.now().strftime("%Y-%m-%d")
    snapshots = load_snapshots()

    lines = []
    lines.append(f"<b>EPIC GAMES — FREE GAMES — {today}</b>")
    lines.append("")

    print("Fetching EGS free games...", file=sys.stderr)
    current_free, upcoming_free = fetch_egs_free_games()

    if current_free:
        lines.append("<b>FREE THIS WEEK</b>")
        lines.append("")
        for g in current_free:
            title = safe_html(g["title"])
            url = g["store_url"]
            link = f'<a href="{url}">{title}</a>' if url else title
            publisher = safe_html(g["publisher"])
            price = safe_html(g["original_price"])
            end = fmt_date_short(g["end_date"])
            lines.append(f"  {link}")
            lines.append(f"   {publisher} · Was {price} · Free until {end}")
        lines.append("")

    if upcoming_free:
        lines.append("<b>FREE NEXT WEEK</b>")
        lines.append("")
        for g in upcoming_free:
            title = safe_html(g["title"])
            url = g["store_url"]
            link = f'<a href="{url}">{title}</a>' if url else title
            publisher = safe_html(g["publisher"])
            price = safe_html(g["original_price"])
            start = fmt_date_short(g["start_date"])
            end = fmt_date_short(g["end_date"])
            lines.append(f"  {link}")
            lines.append(f"   {publisher} · Worth {price} · Free {start} - {end}")
        lines.append("")

    if not current_free and not upcoming_free:
        lines.append("  No free game promotions found right now.")
        lines.append("")

    # Save snapshot
    snapshot_data = {
        "current_free": current_free,
        "upcoming_free": upcoming_free,
        "date": datetime.now().isoformat(),
    }
    save_snapshot(snapshots, today, snapshot_data)

    report = "\n".join(lines)
    output_file = Path(__file__).parent / "epic_free_games_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {output_file}", file=sys.stderr)
    return report


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    report = build_report()
    print(report)
