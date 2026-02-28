#!/usr/bin/env python3
"""
Build Dashboard Data — reads snapshot files from daily reports and generates
JSON data files for the static GitHub Pages dashboard.
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).parent
DOCS_DATA_DIR = SCRIPTS_DIR.parent / "docs" / "data"

# Snapshot sources
GAMING_TRENDS_SNAPSHOTS = SCRIPTS_DIR / "gaming_trends_data" / "daily_snapshots.json"
STEAM_SNAPSHOTS = SCRIPTS_DIR / "steam_data" / "daily_snapshots.json"

# Latest output files (HTML-formatted reports)
GAMING_TRENDS_OUTPUT = SCRIPTS_DIR / "gaming_trends_output.txt"
STEAM_OUTPUT = SCRIPTS_DIR / "steam_trending_output.txt"


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def build_gaming_trends_data():
    """Build dashboard JSON from gaming trends snapshots + latest output."""
    snapshots = load_json(GAMING_TRENDS_SNAPSHOTS)
    if not snapshots:
        print("  No gaming trends snapshots found, skipping", file=sys.stderr)
        return None

    # Get last 7 days of data for history
    sorted_dates = sorted(snapshots.keys())[-7:]
    latest_date = sorted_dates[-1] if sorted_dates else None
    if not latest_date:
        return None

    latest = snapshots[latest_date]

    # Build top streamed list (ordered)
    top_names = latest.get("top_game_names", [])
    viewers = latest.get("viewers", {})
    streams = latest.get("streams", {})

    # Get previous day for % change
    prev_date = sorted_dates[-2] if len(sorted_dates) >= 2 else None
    prev_viewers = snapshots[prev_date].get("viewers", {}) if prev_date else {}

    top_streamed = []
    for name in top_names[:5]:
        v = viewers.get(name, 0)
        prev_v = prev_viewers.get(name, 0)
        change = round(((v - prev_v) / prev_v) * 100, 1) if prev_v > 0 else None
        slug = name.lower().replace(" ", "-").replace("'", "").replace(":", "").replace(".", "")
        top_streamed.append({
            "name": name,
            "viewers": v,
            "streams": streams.get(name, 0),
            "change_pct": change,
            "twitch_url": f"https://www.twitch.tv/directory/category/{slug}"
        })

    breakout = []
    top5_names = set(top_names[:5])
    for name in top_names[5:25]:
        if name in top5_names:
            continue
        v = viewers.get(name, 0)
        prev_v = prev_viewers.get(name, 0)
        change = round(((v - prev_v) / prev_v) * 100, 1) if prev_v > 0 else None
        slug = name.lower().replace(" ", "-").replace("'", "").replace(":", "").replace(".", "")
        breakout.append({
            "name": name,
            "viewers": v,
            "streams": streams.get(name, 0),
            "change_pct": change,
            "twitch_url": f"https://www.twitch.tv/directory/category/{slug}"
        })

    # History for sparklines
    history = {}
    for d in sorted_dates:
        snap = snapshots[d]
        history[d] = {"viewers": snap.get("viewers", {})}

    # Parse latest output for sections we can't get from snapshots
    # (wishlisted, releasing, languages, just_released)
    extra = parse_gaming_trends_output()

    return {
        "updated": latest.get("date", datetime.now().isoformat()),
        "report_date": latest_date,
        "top_streamed": top_streamed,
        "breakout": breakout,
        "languages": extra.get("languages", {}),
        "wishlisted": extra.get("wishlisted", []),
        "releasing": extra.get("releasing", []),
        "just_released": extra.get("just_released", []),
        "history": history
    }


def parse_gaming_trends_output():
    """Parse the HTML-formatted output file for sections not in snapshots."""
    result = {"languages": {}, "wishlisted": [], "releasing": [], "just_released": []}
    if not GAMING_TRENDS_OUTPUT.exists():
        return result

    with open(GAMING_TRENDS_OUTPUT, "r", encoding="utf-8") as f:
        content = f.read()

    import re

    # Parse languages section
    lang_pattern = r'<b>([\w]+):</b>\s*(.+)'
    for match in re.finditer(lang_pattern, content):
        lang = match.group(1)
        games_str = match.group(2)
        games = []
        for gm in re.finditer(r'([^·]+?)\s*\(([0-9,]+)\)', games_str):
            name = gm.group(1).strip()
            # Strip HTML tags from name
            name = re.sub(r'<[^>]+>', '', name).strip()
            viewers = int(gm.group(2).replace(",", ""))
            games.append({"name": name, "viewers": viewers})
        if games:
            result["languages"][lang] = games

    # Parse wishlisted section
    wish_section = re.search(r'MOST WISHLISTED.*?\n\n(.*?)(?=\n\n<b>|\Z)', content, re.DOTALL)
    if wish_section:
        for line in wish_section.group(1).strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Extract name from first <a> tag
            name_m = re.search(r'<a href="([^"]+)">([^<]+)</a>', line)
            if name_m:
                steam_url = name_m.group(1)
                name = name_m.group(2)
                # Find release date (text between " — " and " · ")
                date_m = re.search(r'</a>\s*—\s*([^·<]+)', line)
                release_date = date_m.group(1).strip() if date_m else "TBA"
                # Find IGDB link
                igdb_m = re.search(r'<a href="(https://www\.igdb\.com[^"]+)">IGDB</a>', line)
                igdb_url = igdb_m.group(1) if igdb_m else ""
                result["wishlisted"].append({
                    "name": name,
                    "steam_url": steam_url,
                    "igdb_url": igdb_url,
                    "release_date": release_date
                })

    # Parse releasing section
    rel_section = re.search(r'RELEASING NEXT 30 DAYS.*?\n\n(.*?)(?=\n\n<b>|\Z)', content, re.DOTALL)
    if rel_section:
        for line in rel_section.group(1).strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Format: "  Mar 19, 2026: <a href="...">Name</a> — platforms · hype"
            date_m = re.match(r'([^:]+):\s*<a href="([^"]+)">([^<]+)</a>\s*(?:—\s*(.*))?', line)
            if date_m:
                date_str = date_m.group(1).strip()
                igdb_url = date_m.group(2)
                name = date_m.group(3)
                meta = date_m.group(4) or ""
                # Extract hype count
                hype_m = re.search(r'(\d+)\s*hype', meta)
                hype = int(hype_m.group(1)) if hype_m else 0
                # Platforms = everything before hype
                platforms = re.sub(r'\s*·?\s*\d+\s*hype\s*$', '', meta).strip()
                result["releasing"].append({
                    "name": name,
                    "date": date_str,
                    "platforms": platforms,
                    "hypes": hype,
                    "igdb_url": igdb_url
                })

    # Parse just released section
    jr_section = re.search(r'JUST RELEASED.*?\n\n(.*?)(?=\n\n<b>|\Z)', content, re.DOTALL)
    if jr_section:
        for line in jr_section.group(1).strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            name_m = re.search(r'<a href="([^"]+)">([^<]+)</a>\s*(?:\(([^)]+)\))?', line)
            if name_m:
                result["just_released"].append({
                    "name": name_m.group(2),
                    "igdb_url": name_m.group(1),
                    "platforms": name_m.group(3) or ""
                })

    return result


def build_steam_data():
    """Build dashboard JSON from steam trending snapshots."""
    snapshots = load_json(STEAM_SNAPSHOTS)
    if not snapshots:
        print("  No steam snapshots found, skipping", file=sys.stderr)
        return None

    sorted_dates = sorted(snapshots.keys())[-7:]
    latest_date = sorted_dates[-1] if sorted_dates else None
    if not latest_date:
        return None

    latest = snapshots[latest_date]
    player_counts = latest.get("player_counts", {})
    reviews = latest.get("reviews", {})

    # Previous day for changes
    prev_date = sorted_dates[-2] if len(sorted_dates) >= 2 else None
    prev_players = snapshots[prev_date].get("player_counts", {}) if prev_date else {}

    def build_game(item):
        appid = item.get("appid", "")
        name = item.get("name", "")
        players = player_counts.get(appid, 0)
        prev_p = prev_players.get(appid, 0)
        change = round(((players - prev_p) / prev_p) * 100, 1) if prev_p > 0 else None
        rev = reviews.get(appid, {})
        return {
            "name": name,
            "appid": appid,
            "players": players,
            "change_pct": change,
            "review": rev.get("desc", ""),
            "review_positive": rev.get("positive", 0),
            "review_negative": rev.get("negative", 0),
            "steam_url": f"https://store.steampowered.com/app/{appid}"
        }

    trending = [build_game(g) for g in latest.get("trending", [])]
    topsellers = [build_game(g) for g in latest.get("topsellers", [])]

    # History for sparklines
    history = {}
    for d in sorted_dates:
        snap = snapshots[d]
        history[d] = {"player_counts": snap.get("player_counts", {})}

    return {
        "updated": latest.get("date", datetime.now().isoformat()),
        "report_date": latest_date,
        "trending": trending,
        "topsellers": topsellers,
        "history": history
    }


def main():
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Building dashboard data...", file=sys.stderr)

    # Gaming Trends
    gt_data = build_gaming_trends_data()
    if gt_data:
        gt_path = DOCS_DATA_DIR / "gaming_trends.json"
        with open(gt_path, "w", encoding="utf-8") as f:
            json.dump(gt_data, f, indent=2, ensure_ascii=False)
        print(f"  Gaming trends: {gt_path}", file=sys.stderr)

    # Steam Trending
    st_data = build_steam_data()
    if st_data:
        st_path = DOCS_DATA_DIR / "steam_trending.json"
        with open(st_path, "w", encoding="utf-8") as f:
            json.dump(st_data, f, indent=2, ensure_ascii=False)
        print(f"  Steam trending: {st_path}", file=sys.stderr)

    print("Dashboard data built.", file=sys.stderr)

    # Auto-push if --push flag
    if "--push" in sys.argv:
        print("Pushing to GitHub...", file=sys.stderr)
        repo_dir = SCRIPTS_DIR.parent
        try:
            subprocess.run(["git", "add", "docs/data/"], cwd=repo_dir, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Update dashboard data"],
                cwd=repo_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "push"], cwd=repo_dir, check=True)
            print("  Pushed to GitHub.", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"  Git push failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
