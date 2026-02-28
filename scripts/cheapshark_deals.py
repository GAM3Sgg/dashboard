#!/usr/bin/env python3
"""
CheapShark Deals — cross-store game deal aggregation.
No authentication required (free public API).
"""

import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

REQUEST_DELAY = 0.4
DATA_DIR = Path(__file__).parent / "cheapshark_data"
SNAPSHOT_FILE = DATA_DIR / "daily_snapshots.json"

BASE_URL = "https://www.cheapshark.com/api/1.0"


# ── API helpers ──────────────────────────────────────────────────────────────

def cs_get(endpoint, params=None):
    """GET request to CheapShark API."""
    url = f"{BASE_URL}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "OGGamingDashboard/1.0"})
    time.sleep(REQUEST_DELAY)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  CheapShark error ({endpoint}): {e}", file=sys.stderr)
        return []


def safe_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── Fetchers ─────────────────────────────────────────────────────────────────

def fetch_stores():
    """Fetch store ID → name mapping."""
    raw = cs_get("stores")
    if not raw:
        return {}
    return {s["storeID"]: s["storeName"] for s in raw if s.get("isActive")}


def fetch_deals(sort_by, page_size=20, **extra_params):
    """Fetch deals with given sort and filters."""
    params = {
        "sortBy": sort_by,
        "onSale": 1,
        "pageSize": page_size,
        "pageNumber": 0,
    }
    params.update(extra_params)
    raw = cs_get("deals", params)
    if not raw or not isinstance(raw, list):
        return []
    return raw


def parse_deal(deal, stores):
    """Extract display fields from a CheapShark deal object."""
    store_id = deal.get("storeID", "")
    store_name = stores.get(store_id, f"Store {store_id}")
    sale_price = deal.get("salePrice", "0")
    normal_price = deal.get("normalPrice", "0")
    savings = deal.get("savings", "0")
    metacritic = deal.get("metacriticScore", "0")
    steam_rating = deal.get("steamRatingPercent", "0")
    steam_app_id = deal.get("steamAppID")
    deal_id = deal.get("dealID", "")

    # Build URLs
    deal_url = f"https://www.cheapshark.com/redirect?dealID={deal_id}" if deal_id else ""
    steam_url = f"https://store.steampowered.com/app/{steam_app_id}" if steam_app_id else ""

    return {
        "title": deal.get("title", ""),
        "sale_price": sale_price,
        "normal_price": normal_price,
        "savings_pct": round(float(savings)),
        "store_name": store_name,
        "store_id": store_id,
        "metacritic": int(metacritic) if metacritic and metacritic != "0" else 0,
        "steam_rating": int(steam_rating) if steam_rating and steam_rating != "0" else 0,
        "steam_rating_text": deal.get("steamRatingText", ""),
        "deal_rating": deal.get("dealRating", ""),
        "deal_url": deal_url,
        "steam_url": steam_url,
        "thumb": deal.get("thumb", ""),
    }


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

# Keywords that indicate non-game items (DLC, soundtracks, bundles, etc.)
JUNK_KEYWORDS = [
    "soundtrack", "ost", "artbook", "art book", "wallpaper", "costume pack",
    "sfx", "sound forge", "sound effect", "royalty free", "music bundle",
    "dlc", "season pass", "content pack", "expansion pass",
    "bundle", "collection pack",
    "rpg bundle", "edition bundle",
    "skin pack", "voice pack", "emote pack",
    "pdf", "ebook", "e-book", "guidebook", "manual",
    "blender", "pathfinder", "c 4th edition",
]


def is_real_game(deal):
    """Filter out non-game items like soundtracks, SFX packs, DLC, bundles."""
    title = deal.get("title", "").lower()
    for kw in JUNK_KEYWORDS:
        if kw in title:
            return False
    return True


def dedup_deals(deals, limit=15):
    """Keep only the best deal per game title (lowest sale price)."""
    seen = {}
    for d in deals:
        title = d["title"].lower().strip()
        if title not in seen or float(d["sale_price"]) < float(seen[title]["sale_price"]):
            seen[title] = d
    return list(seen.values())[:limit]


def build_report():
    """Fetch CheapShark deals and build HTML report."""
    today = datetime.now().strftime("%Y-%m-%d")
    snapshots = load_snapshots()

    lines = []
    lines.append(f"<b>GAME DEALS — {today}</b>")
    lines.append("")

    print("Fetching store directory...", file=sys.stderr)
    stores = fetch_stores()

    # Best deals (CheapShark's Deal Rating)
    print("Fetching best deals...", file=sys.stderr)
    best_raw = fetch_deals("Deal Rating", page_size=40)
    best_deals = dedup_deals([parse_deal(d, stores) for d in best_raw if is_real_game(d)])

    # Biggest discounts — fetch more, filter to meaningful savings, dedup
    print("Fetching biggest discounts...", file=sys.stderr)
    disc_raw = fetch_deals("Savings", page_size=60)
    disc_parsed = [parse_deal(d, stores) for d in disc_raw if is_real_game(d)]
    disc_parsed = [d for d in disc_parsed if d["savings_pct"] >= 50]
    disc_parsed.sort(key=lambda d: -d["savings_pct"])
    biggest_discounts = dedup_deals(disc_parsed)

    # Top rated on sale (metacritic 80+, steam 80+)
    print("Fetching top rated on sale...", file=sys.stderr)
    rated_raw = fetch_deals("Metacritic", page_size=30, desc=1, metacritic=80, steamRating=80)
    top_rated = dedup_deals([parse_deal(d, stores) for d in rated_raw if is_real_game(d)])

    # AAA on sale — filter to meaningful discounts
    print("Fetching AAA deals...", file=sys.stderr)
    aaa_raw = fetch_deals("Savings", page_size=40, AAA=1)
    aaa_parsed = [parse_deal(d, stores) for d in aaa_raw if is_real_game(d)]
    aaa_parsed = [d for d in aaa_parsed if d["savings_pct"] >= 20]
    aaa_parsed.sort(key=lambda d: -d["savings_pct"])
    aaa_deals = dedup_deals(aaa_parsed)

    # Format report sections
    def fmt_section(title, deals):
        section = [f"<b>{title}</b>", ""]
        if not deals:
            section.append("  No deals found.")
            section.append("")
            return section
        for i, d in enumerate(deals[:10], 1):
            name = safe_html(d["title"])
            store = safe_html(d["store_name"])
            section.append(
                f"  {i}. {name} — ${d['sale_price']} "
                f"(was ${d['normal_price']}, -{d['savings_pct']}%) "
                f"· {store}"
            )
            meta = []
            if d["metacritic"]:
                meta.append(f"MC: {d['metacritic']}")
            if d["steam_rating"]:
                meta.append(f"Steam: {d['steam_rating']}%")
            if meta:
                section.append(f"     {' · '.join(meta)}")
        section.append("")
        return section

    lines.extend(fmt_section("BEST DEALS", best_deals))
    lines.extend(fmt_section("BIGGEST DISCOUNTS", biggest_discounts))
    lines.extend(fmt_section("TOP RATED ON SALE (MC 80+)", top_rated))
    lines.extend(fmt_section("AAA ON SALE", aaa_deals))

    # Save snapshot
    snapshot_data = {
        "stores": stores,
        "best_deals": best_deals,
        "biggest_discounts": biggest_discounts,
        "top_rated": top_rated,
        "aaa_deals": aaa_deals,
        "date": datetime.now().isoformat(),
    }
    save_snapshot(snapshots, today, snapshot_data)

    report = "\n".join(lines)
    output_file = Path(__file__).parent / "cheapshark_deals_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {output_file}", file=sys.stderr)
    return report


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    report = build_report()
    print(report)
