#!/usr/bin/env python3
"""
GAM3S.GG Insights Dashboard v5
GA4 + Search Console combined dashboard.
Daily: 7d + 14d. Monthly (last day of month): adds 30d.
Optimized for 2 Telegram messages max.
"""

import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from urllib.parse import unquote

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, OrderBy
)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build as gapi_build
import pytz

# Configuration
GA4_PROPERTY_ID = "334095714"
GSC_SITE_URL = "sc-domain:gam3s.gg"
CREDS_PATH = Path.home() / ".openclaw" / "credentials" / "gam3s-google-sa.json"
TIMEZONE = pytz.timezone('Asia/Dubai')

INSIGHTS_DATA_DIR = Path(__file__).parent / "insights_data"
INSIGHTS_SNAPSHOT_FILE = INSIGHTS_DATA_DIR / "daily_snapshots.json"


def categorize_page(path: str, title: str) -> str:
    p = path.lower()
    t = title.lower()
    if '/guides/' in p or '/guia/' in p or '/guias/' in p or 'tier' in t or 'best builds' in t:
        return 'Guide'
    if '/news/' in p or '/noticias/' in p or '/noticia/' in p or '/actualites/' in p:
        return 'News'
    return 'Page'


def slug_to_english(slug: str) -> str:
    return slug.replace('-', ' ').title()


def is_non_english_title(title: str) -> bool:
    for ch in title:
        cp = ord(ch)
        if (0x3000 <= cp <= 0x9FFF or 0xAC00 <= cp <= 0xD7AF
                or 0x0400 <= cp <= 0x04FF or 0x0600 <= cp <= 0x06FF
                or 0x0E00 <= cp <= 0x0E7F or 0x0900 <= cp <= 0x097F):
            return True
    non_english_keywords = ['guía', 'guia', 'noticia', 'noticias', 'actualité',
                           'fiyat', 'değer', 'preço', 'precio', 'düşüş',
                           'ランキング', 'おすすめ', '最強', '攻略']
    return any(kw in title.lower() for kw in non_english_keywords)


def clean_title(title: str, topic_slug: str = "") -> str:
    """Remove site suffix, add English context for non-English titles. No truncation."""
    title = re.sub(r'\s*\|\s*GAM3S\.GG\s*$', '', title, flags=re.IGNORECASE)
    title = title.strip()

    # Add English context from URL slug if title is non-English
    if title and topic_slug and is_non_english_title(title):
        english_hint = slug_to_english(topic_slug)
        if (len(english_hint) > 5 and len(english_hint) < 60
                and '/' not in english_hint
                and english_hint.lower() not in title.lower()):
            title += f" ({english_hint})"

    return title or "(untitled)"


def extract_topic_key(path: str) -> str:
    cleaned = re.sub(r'^/[a-z]{2}(?:-[a-z]{2})?/', '/', path)
    cleaned = re.sub(r'^/(guides|guias|guia|news|noticias|noticia|actualites|games|juegos|jeux)/', '/', cleaned)
    match = re.match(r'/([a-z0-9][a-z0-9-]+)', cleaned)
    if match:
        slug = match.group(1).rstrip('-')
        parts = slug.split('-')
        if len(parts) > 6:
            slug = '-'.join(parts[:6])
        if len(slug) > 3:
            return slug
    segments = [s for s in path.split('/') if s and len(s) > 3
                and s not in ('guides', 'guias', 'guia', 'news', 'noticias',
                              'noticia', 'actualites', 'games', 'juegos', 'jeux')]
    if segments:
        slug = segments[-1]
        parts = slug.split('-')
        if len(parts) > 6:
            slug = '-'.join(parts[:6])
        return slug
    return path


class PageRow:
    __slots__ = ('path', 'title', 'sessions', 'users', 'pageviews',
                 'avg_duration', 'bounce_rate', 'category', 'topic', 'date')

    def __init__(self, row, date_val: Optional[str] = None):
        dims = row.dimension_values
        mets = row.metric_values
        idx = 0
        if date_val is not None:
            self.date = dims[0].value
            idx = 1
        else:
            self.date = None
        self.path = dims[idx].value
        self.title = dims[idx + 1].value
        self.sessions = int(mets[0].value)
        self.users = int(mets[1].value)
        self.pageviews = int(mets[2].value)
        self.avg_duration = float(mets[3].value)
        self.bounce_rate = float(mets[4].value)
        self.category = categorize_page(self.path, self.title)
        self.topic = extract_topic_key(self.path)


class LangRow:
    __slots__ = ('lang', 'sessions', 'users', 'pageviews', 'date')

    def __init__(self, row, has_date: bool = False):
        dims = row.dimension_values
        mets = row.metric_values
        idx = 0
        if has_date:
            self.date = dims[0].value
            idx = 1
        else:
            self.date = None
        self.lang = dims[idx].value
        self.sessions = int(mets[0].value)
        self.users = int(mets[1].value)
        self.pageviews = int(mets[2].value)


class GSCRow:
    __slots__ = ('query', 'clicks', 'impressions', 'ctr', 'position')

    def __init__(self, row: dict):
        self.query = row['keys'][0]
        self.clicks = row.get('clicks', 0)
        self.impressions = row.get('impressions', 0)
        self.ctr = row.get('ctr', 0.0)
        self.position = row.get('position', 0.0)


def aggregate_by_topic(rows: List[PageRow]) -> List[Dict]:
    groups = defaultdict(lambda: {
        'sessions': 0, 'users': 0, 'pageviews': 0,
        'bounce_sum': 0.0, 'duration_sum': 0.0, 'count': 0,
        'best_title': '', 'best_sessions': 0, 'category': 'Page',
        'pages': [], 'topic_slug': ''
    })
    for r in rows:
        g = groups[r.topic]
        g['sessions'] += r.sessions
        g['users'] += r.users
        g['pageviews'] += r.pageviews
        g['bounce_sum'] += r.bounce_rate * r.sessions
        g['duration_sum'] += r.avg_duration * r.sessions
        g['count'] += 1
        g['pages'].append(r.path)
        g['topic_slug'] = r.topic
        if r.sessions > g['best_sessions']:
            g['best_sessions'] = r.sessions
            g['best_title'] = clean_title(r.title, r.topic)
            g['category'] = r.category
    result = []
    for topic, g in groups.items():
        if g['sessions'] > 0:
            g['avg_bounce'] = g['bounce_sum'] / g['sessions']
            g['avg_duration'] = g['duration_sum'] / g['sessions']
        else:
            g['avg_bounce'] = 0
            g['avg_duration'] = 0
        g['topic'] = topic
        result.append(g)
    return sorted(result, key=lambda x: x['sessions'], reverse=True)


def filter_by_days(rows, days: int, tz=TIMEZONE):
    cutoff = (datetime.now(tz).date() - timedelta(days=days)).strftime('%Y%m%d')
    return [r for r in rows if r.date is not None and r.date >= cutoff]


def sum_langs(rows: List[LangRow]) -> List[Dict]:
    totals = defaultdict(lambda: {'sessions': 0, 'users': 0, 'pageviews': 0})
    for r in rows:
        t = totals[r.lang]
        t['sessions'] += r.sessions
        t['users'] += r.users
        t['pageviews'] += r.pageviews
    result = [{'lang': k, **v} for k, v in totals.items()]
    return sorted(result, key=lambda x: x['sessions'], reverse=True)


def trend_arrow(current: int, prior: int) -> str:
    if prior == 0:
        return " (new)" if current > 0 else ""
    pct = ((current - prior) / prior) * 100
    if pct >= 10:
        return f" +{pct:.0f}%"
    elif pct <= -10:
        return f" {pct:.0f}%"
    return " (flat)"


def compact_num(n: int) -> str:
    """Format number compactly: 130,510 -> 130K, 1,234,567 -> 1.2M"""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


class GAM3SInsights:
    def __init__(self):
        self.creds = Credentials.from_service_account_file(
            CREDS_PATH,
            scopes=[
                "https://www.googleapis.com/auth/analytics.readonly",
                "https://www.googleapis.com/auth/webmasters.readonly",
            ]
        )
        self.ga4 = BetaAnalyticsDataClient(credentials=self.creds)
        self.gsc = gapi_build('searchconsole', 'v1', credentials=self.creds)

    def _fetch_pages(self, start: str, end: str, limit: int = 200):
        req = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[
                Dimension(name="date"),
                Dimension(name="pagePath"),
                Dimension(name="pageTitle"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
            ],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            limit=limit,
        )
        report = self.ga4.run_report(req)
        return [PageRow(row, date_val=True) for row in report.rows]

    def _fetch_langs(self, start: str, end: str):
        req = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[
                Dimension(name="date"),
                Dimension(name="language"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
            ],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            limit=500,
        )
        report = self.ga4.run_report(req)
        return [LangRow(row, has_date=True) for row in report.rows]

    def _fetch_gsc_queries(self, start: str, end: str, limit: int = 500) -> List[GSCRow]:
        body = {
            'startDate': start, 'endDate': end,
            'dimensions': ['query'], 'rowLimit': limit, 'dataState': 'all',
        }
        resp = self.gsc.searchanalytics().query(siteUrl=GSC_SITE_URL, body=body).execute()
        return [GSCRow(row) for row in resp.get('rows', [])]

    def _fetch_gsc_pages(self, start: str, end: str, limit: int = 200) -> List[dict]:
        body = {
            'startDate': start, 'endDate': end,
            'dimensions': ['page'], 'rowLimit': limit, 'dataState': 'all',
        }
        resp = self.gsc.searchanalytics().query(siteUrl=GSC_SITE_URL, body=body).execute()
        return resp.get('rows', [])

    def save_snapshot(self, data: dict):
        INSIGHTS_DATA_DIR.mkdir(exist_ok=True)
        snapshots = {}
        if INSIGHTS_SNAPSHOT_FILE.exists():
            with open(INSIGHTS_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                snapshots = json.load(f)
        today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        snapshots[today] = data
        cutoff = (datetime.now(TIMEZONE) - timedelta(days=30)).strftime("%Y-%m-%d")
        snapshots = {k: v for k, v in snapshots.items() if k >= cutoff}
        with open(INSIGHTS_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshots, f, indent=2, ensure_ascii=False)

    def build_report(self, include_30d: bool = False) -> str:
        now = datetime.now(TIMEZONE)
        today = now.date()
        header_time = now.strftime("%a, %b %d %Y - %H:%M Dubai Time")

        # Auto-include 30d on last day of month
        tomorrow = today + timedelta(days=1)
        if tomorrow.month != today.month:
            include_30d = True

        # === API CALLS ===
        start_30 = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        start_14 = (today - timedelta(days=14)).strftime('%Y-%m-%d')
        end_today = today.strftime('%Y-%m-%d')

        # Fetch enough days for 14d (or 30d if month-end)
        fetch_start = start_30 if include_30d else start_14
        all_pages = self._fetch_pages(fetch_start, end_today, limit=500)

        # Prior 7 days (days 8-14 ago) for WoW comparison
        prior_end = (today - timedelta(days=8)).strftime('%Y-%m-%d')
        prior_start = (today - timedelta(days=14)).strftime('%Y-%m-%d')
        prior_pages = self._fetch_pages(prior_start, prior_end, limit=200)

        # Languages
        all_langs = self._fetch_langs(fetch_start, end_today)
        prior_langs = self._fetch_langs(prior_start, prior_end)

        # GSC
        gsc_start_7 = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        gsc_queries_7d = self._fetch_gsc_queries(gsc_start_7, end_today, limit=500)
        gsc_queries_prior = self._fetch_gsc_queries(prior_start, prior_end, limit=500)
        gsc_pages_7d = self._fetch_gsc_pages(gsc_start_7, end_today, limit=200)

        # === SLICE & AGGREGATE ===
        pages_7d = filter_by_days(all_pages, 7)
        pages_14d = filter_by_days(all_pages, 14)

        agg_7d = aggregate_by_topic(pages_7d)
        agg_14d = aggregate_by_topic(pages_14d)

        lang_7d = sum_langs(filter_by_days(all_langs, 7))
        lang_14d = sum_langs(filter_by_days(all_langs, 14))

        prior_page_agg = aggregate_by_topic(prior_pages)
        prior_page_map = {g['topic']: g['sessions'] for g in prior_page_agg}
        prior_lang_totals = sum_langs(prior_langs)
        prior_lang_map = {l['lang']: l['sessions'] for l in prior_lang_totals}

        total_7d = sum(r.sessions for r in pages_7d)
        total_prior = sum(r.sessions for r in prior_pages)

        # === SAVE SNAPSHOT ===
        wow_pct = round(((total_7d - total_prior) / total_prior) * 100, 1) if total_prior > 0 else 0

        def _topic_dict(g):
            prior_s = prior_page_map.get(g['topic'], 0)
            growth = round(((g['sessions'] - prior_s) / prior_s) * 100, 1) if prior_s > 0 else None
            return {
                "topic": g['topic'],
                "title": g['best_title'],
                "category": g['category'],
                "sessions": g['sessions'],
                "users": g['users'],
                "pageviews": g['pageviews'],
                "bounce_rate": round(g['avg_bounce'], 3),
                "avg_duration": round(g['avg_duration'], 1),
                "page_count": g['count'],
                "growth_pct": growth,
                "urls": g['pages'][:3],
            }

        # Trending: 50%+ growth AND 500+ sessions, or new with 1000+
        snap_trending = []
        for g in agg_7d:
            prior_s = prior_page_map.get(g['topic'], 0)
            if prior_s > 0:
                growth = ((g['sessions'] - prior_s) / prior_s) * 100
                if growth >= 50 and g['sessions'] >= 500:
                    snap_trending.append({**_topic_dict(g), "growth_pct": round(growth, 1)})
            elif g['sessions'] >= 1000:
                snap_trending.append({**_topic_dict(g), "growth_pct": None})
        snap_trending.sort(key=lambda x: x['sessions'], reverse=True)

        # Fix opportunities: bounce > 80%, sessions >= 500
        snap_fixes = [_topic_dict(g) for g in agg_7d if g['avg_bounce'] > 0.80 and g['sessions'] >= 500]
        snap_fixes.sort(key=lambda x: x['sessions'], reverse=True)

        # GSC: rising queries
        prior_qmap = {q.query: q for q in gsc_queries_prior}
        snap_rising_q = []
        for q in gsc_queries_7d:
            prev = prior_qmap.get(q.query)
            if prev and prev.clicks > 0:
                growth = ((q.clicks - prev.clicks) / prev.clicks) * 100
                if growth >= 50 and q.clicks >= 5:
                    snap_rising_q.append({"query": q.query, "clicks": q.clicks, "impressions": q.impressions,
                                          "ctr": round(q.ctr, 4), "position": round(q.position, 1), "growth_pct": round(growth, 1)})
            elif not prev and q.clicks >= 10:
                snap_rising_q.append({"query": q.query, "clicks": q.clicks, "impressions": q.impressions,
                                      "ctr": round(q.ctr, 4), "position": round(q.position, 1), "growth_pct": None})
        snap_rising_q.sort(key=lambda x: x['clicks'], reverse=True)

        # Content gaps (high impressions, low clicks)
        snap_gaps = []
        for q in gsc_queries_7d:
            if q.impressions >= 500 and q.ctr < 0.02 and q.position <= 20:
                snap_gaps.append({"query": q.query, "impressions": q.impressions, "clicks": q.clicks,
                                  "ctr": round(q.ctr, 4), "position": round(q.position, 1)})
        snap_gaps.sort(key=lambda x: x['impressions'], reverse=True)

        # Page 2 wins
        snap_p2 = []
        for q in gsc_queries_7d:
            if 11 <= q.position <= 20 and q.impressions >= 50:
                snap_p2.append({"query": q.query, "impressions": q.impressions, "clicks": q.clicks,
                                "position": round(q.position, 1)})
        snap_p2.sort(key=lambda x: x['impressions'], reverse=True)

        # Low CTR pages
        snap_low_ctr = []
        for p in gsc_pages_7d:
            impr = p.get('impressions', 0)
            ctr = p.get('ctr', 0)
            clicks = p.get('clicks', 0)
            pos = p.get('position', 0)
            if impr >= 500 and ctr < 0.02 and pos <= 15:
                url = p['keys'][0]
                slug = unquote(url.rstrip('/').split('/')[-1]) if '/' in url else url
                name = slug_to_english(slug) if slug else url
                snap_low_ctr.append({"name": name, "impressions": impr, "clicks": clicks,
                                     "ctr": round(ctr, 4), "position": round(pos, 1)})
        snap_low_ctr.sort(key=lambda x: x['impressions'], reverse=True)

        # Language snapshot
        snap_langs = []
        for l in lang_7d[:15]:
            prior_l = prior_lang_map.get(l['lang'], 0)
            growth = round(((l['sessions'] - prior_l) / prior_l) * 100, 1) if prior_l > 0 else None
            snap_langs.append({"language": l['lang'], "sessions": l['sessions'], "users": l['users'],
                               "pageviews": l['pageviews'], "growth_pct": growth})

        snapshot = {
            "date": now.isoformat(),
            "total_sessions_7d": total_7d,
            "total_sessions_prior": total_prior,
            "wow_pct": wow_pct,
            "top_pages_7d": [_topic_dict(g) for g in agg_7d[:15]],
            "top_guides_7d": [_topic_dict(g) for g in agg_7d if g['category'] == 'Guide'][:15],
            "top_news_7d": [_topic_dict(g) for g in agg_7d if g['category'] == 'News'][:15],
            "languages_7d": snap_langs,
            "trending": snap_trending[:10],
            "fix_opportunities": snap_fixes[:8],
            "gsc_top_queries": [{"query": q.query, "clicks": q.clicks, "impressions": q.impressions,
                                  "ctr": round(q.ctr, 4), "position": round(q.position, 1)} for q in gsc_queries_7d[:15]],
            "gsc_rising_queries": snap_rising_q[:10],
            "content_gaps": snap_gaps[:8],
            "page2_wins": snap_p2[:8],
            "low_ctr_pages": snap_low_ctr[:8],
        }
        self.save_snapshot(snapshot)

        # === HELPERS ===
        def page_line(g):
            arrow = trend_arrow(g['sessions'], prior_page_map.get(g['topic'], 0))
            line = f"  - {g['best_title']}: {g['sessions']:,}{arrow}"
            if g['count'] > 1:
                line += f" [{g['count']} pages]"
            return line

        def top_section(label, items):
            if not items:
                return ""
            lines = [f"{label}"]
            for g in items:
                lines.append(page_line(g))
            return "\n".join(lines) + "\n"

        def by_cat(agg, cat, n):
            return [g for g in agg if g['category'] == cat][:n]

        def lang_line(totals, count=10):
            parts = []
            for l in totals[:count]:
                arrow = trend_arrow(l['sessions'], prior_lang_map.get(l['lang'], 0))
                # Strip " (flat)" to keep compact, only show changes
                if arrow == " (flat)":
                    arrow = ""
                parts.append(f"{l['lang']} {compact_num(l['sessions'])}{arrow}")
            # Split into 2 rows of 5 for readability
            row1 = " · ".join(parts[:5])
            row2 = " · ".join(parts[5:])
            result = f"🌐 {row1}\n"
            if row2:
                result += f"   {row2}\n"
            return result

        # === BUILD MESSAGE ===
        msg = f"📊 *GAM3S.GG Daily Insights*\n_{header_time}_\n\n"

        # WoW
        wow = trend_arrow(total_7d, total_prior)
        msg += f"📈 *This Week vs Last Week*\n  Sessions: {total_7d:,}{wow} (prior: {total_prior:,})\n\n"

        # --- 7 DAYS ---
        guides_7 = by_cat(agg_7d, 'Guide', 3)
        news_7 = by_cat(agg_7d, 'News', 3)

        msg += "📅 *LAST 7 DAYS*\n"
        msg += top_section("🏆 *Top Pages*", agg_7d[:5])
        msg += top_section("🎮 *Top Guides*", guides_7)
        msg += top_section("📰 *Top News*", news_7)
        msg += lang_line(lang_7d)
        msg += "\n"

        # --- 14 DAYS ---
        msg += "📅 *LAST 14 DAYS*\n"
        msg += top_section("🏆 *Top Pages*", agg_14d[:5])
        msg += top_section("🎮 *Top Guides*", by_cat(agg_14d, 'Guide', 3))
        msg += top_section("📰 *Top News*", by_cat(agg_14d, 'News', 3))
        msg += lang_line(lang_14d)

        # --- 30 DAYS (month-end only) ---
        if include_30d:
            agg_30d = aggregate_by_topic(all_pages)
            lang_30d = sum_langs(all_langs)
            msg += "\n📅 *LAST 30 DAYS (Monthly)*\n"
            msg += top_section("🏆 *Top Pages*", agg_30d[:5])
            msg += top_section("🎮 *Top Guides*", by_cat(agg_30d, 'Guide', 3))
            msg += top_section("📰 *Top News*", by_cat(agg_30d, 'News', 3))
            msg += lang_line(lang_30d)

        # --- TRENDING & RISING (merged) ---
        msg += "\n🔥 *Trending & Rising*\n"
        spikes = []
        for g in agg_7d:
            prior = prior_page_map.get(g['topic'], 0)
            if prior > 0:
                growth = ((g['sessions'] - prior) / prior) * 100
                if growth >= 50 and g['sessions'] >= 500:
                    spikes.append({**g, 'growth': growth})
            elif g['sessions'] >= 1000:
                spikes.append({**g, 'growth': None})
        spikes.sort(key=lambda x: x['sessions'], reverse=True)

        # Also find new topics (not in spikes already)
        spike_topics = {s['topic'] for s in spikes}
        new_topics = []
        for g in agg_7d:
            if g['topic'] in spike_topics or g['sessions'] < 500:
                continue
            prior = prior_page_map.get(g['topic'], 0)
            if prior == 0:
                new_topics.append(g)
        new_topics.sort(key=lambda x: x['sessions'], reverse=True)

        if spikes or new_topics:
            for s in spikes[:5]:
                if s['growth'] is not None:
                    msg += f"  🚀 {s['best_title']}: {s['sessions']:,} (+{s['growth']:.0f}%)\n"
                else:
                    msg += f"  ⭐ {s['best_title']}: {s['sessions']:,} (new)\n"
            for nt in new_topics[:3]:
                msg += f"  ⭐ {nt['best_title']}: {nt['sessions']:,} (new)\n"
        else:
            msg += "  Steady week, no major spikes\n"

        # --- FIX OPPORTUNITIES (bounce + language gaps, compact) ---
        high_bounce = [g for g in agg_7d if g['avg_bounce'] > 0.80 and g['sessions'] >= 500]
        high_bounce.sort(key=lambda x: x['sessions'], reverse=True)

        if high_bounce:
            msg += "\n⚠️ *Fix Opportunities*\n"
            for g in high_bounce[:3]:
                msg += f"  - {g['best_title']}: {g['sessions']:,} sessions, {g['avg_bounce']:.0%} bounce, {g['avg_duration']:.0f}s avg\n"

        # Language gaps (compact)
        if lang_7d:
            top_s = lang_7d[0]['sessions']
            gaps = [l for l in lang_7d[3:10] if l['sessions'] / top_s > 0.10]
            growing = [l for l in gaps
                       if prior_lang_map.get(l['lang'], 0) > 0
                       and ((l['sessions'] - prior_lang_map[l['lang']]) / prior_lang_map[l['lang']]) > 0.20]
            if growing:
                msg += "  🌍 Growing languages: "
                parts = []
                for l in growing:
                    arrow = trend_arrow(l['sessions'], prior_lang_map.get(l['lang'], 0))
                    parts.append(f"{l['lang']}{arrow}")
                msg += ", ".join(parts) + " — expand content\n"

        # --- SEARCH CONSOLE ---
        msg += "\n🔍 *Search Console (7d)*\n"

        # Top queries (compact: top 5)
        if gsc_queries_7d:
            for q in gsc_queries_7d[:5]:
                msg += f"  - \"{q.query}\": {q.clicks:,} clicks, {q.impressions:,} impr, {q.ctr:.1%} CTR, pos {q.position:.1f}\n"

        # Rising queries
        prior_qmap = {q.query: q for q in gsc_queries_prior}
        rising_q = []
        for q in gsc_queries_7d:
            prev = prior_qmap.get(q.query)
            if prev and prev.clicks > 0:
                growth = ((q.clicks - prev.clicks) / prev.clicks) * 100
                if growth >= 50 and q.clicks >= 5:
                    rising_q.append({'query': q.query, 'clicks': q.clicks, 'growth': growth, 'position': q.position})
            elif not prev and q.clicks >= 10:
                rising_q.append({'query': q.query, 'clicks': q.clicks, 'growth': None, 'position': q.position})
        rising_q.sort(key=lambda x: x['clicks'], reverse=True)

        if rising_q:
            msg += "  *Rising:*\n"
            for rq in rising_q[:5]:
                if rq['growth'] is not None:
                    msg += f"  📈 \"{rq['query']}\": {rq['clicks']:,} clicks (+{rq['growth']:.0f}%)\n"
                else:
                    msg += f"  ⭐ \"{rq['query']}\": {rq['clicks']:,} clicks (new)\n"

        # --- SEO ACTIONABLES (closing section) ---
        msg += "\n🎯 *Actionables*\n"

        # Content actions
        if guides_7:
            msg += f"  ✅ Ride: {guides_7[0]['best_title']} — create follow-up content\n"
        if spikes:
            best_spike = spikes[0]
            if best_spike['topic'] != (guides_7[0]['topic'] if guides_7 else ''):
                msg += f"  ✅ Trending: {best_spike['best_title']} — capitalize on momentum\n"
        if high_bounce:
            msg += f"  ⚠️ Fix bounce: {high_bounce[0]['best_title']} ({high_bounce[0]['sessions']:,} sessions at {high_bounce[0]['avg_bounce']:.0%})\n"

        # GSC: content gaps (high impressions, low clicks)
        low_ctr = [q for q in gsc_queries_7d if q.impressions >= 500 and q.ctr < 0.02 and q.position <= 20]
        low_ctr.sort(key=lambda x: x.impressions, reverse=True)
        if low_ctr:
            for opp in low_ctr[:3]:
                action = "improve" if opp.clicks > 0 else "create"
                msg += f"  🔍 {action.title()} content for \"{opp.query}\": {opp.impressions:,} impr, only {opp.clicks} clicks\n"

        # GSC: page 2 wins
        page2 = [q for q in gsc_queries_7d if 11 <= q.position <= 20 and q.impressions >= 50]
        page2.sort(key=lambda x: x.impressions, reverse=True)
        if page2:
            for pw in page2[:2]:
                msg += f"  🎯 Push to page 1: \"{pw.query}\" at pos {pw.position:.1f} ({pw.impressions:,} impr)\n"

        # GSC: low CTR pages (fix titles/snippets)
        low_ctr_pages = []
        for p in gsc_pages_7d:
            impr = p.get('impressions', 0)
            ctr = p.get('ctr', 0)
            clicks = p.get('clicks', 0)
            pos = p.get('position', 0)
            if impr >= 500 and ctr < 0.02 and pos <= 15:
                url = p['keys'][0]
                slug = unquote(url.rstrip('/').split('/')[-1]) if '/' in url else url
                name = slug_to_english(slug) if slug else url
                low_ctr_pages.append({'name': name, 'impressions': impr, 'clicks': clicks, 'ctr': ctr, 'position': pos})
        low_ctr_pages.sort(key=lambda x: x['impressions'], reverse=True)
        if low_ctr_pages:
            for lp in low_ctr_pages[:3]:
                msg += f"  📉 Fix title: {lp['name']} — {lp['impressions']:,} impr at {lp['ctr']:.1%} CTR\n"

        # Growing language
        if lang_7d:
            growing_langs = []
            for l in lang_7d[:10]:
                prior = prior_lang_map.get(l['lang'], 0)
                if prior > 0:
                    pct = ((l['sessions'] - prior) / prior) * 100
                    if pct > 20:
                        growing_langs.append((l['lang'], pct))
            if growing_langs:
                growing_langs.sort(key=lambda x: x[1], reverse=True)
                top_g = growing_langs[0]
                msg += f"  🌍 Expand {top_g[0]} content (+{top_g[1]:.0f}% growth)\n"

        msg += f"\n_Next update: Tomorrow at 1pm Dubai Time_"
        return msg

    def run(self, include_30d: bool = False) -> str:
        print("Starting GAM3S.GG insights analysis...")
        print(f"GA4 Property: {GA4_PROPERTY_ID}")
        print(f"Timezone: {TIMEZONE}\n")

        message = self.build_report(include_30d=include_30d)
        print("=" * 70)
        print(message)
        print("=" * 70)
        return message


if __name__ == "__main__":
    import sys
    try:
        # Pass --monthly or --30d flag to include 30-day section
        monthly = any(f in sys.argv for f in ('--monthly', '--30d'))
        insights = GAM3SInsights()
        message = insights.run(include_30d=monthly)

        output_file = Path(__file__).parent / "insights_output.txt"
        output_file.write_text(message, encoding="utf-8")
        print(f"\nOutput saved to {output_file}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise
