#!/usr/bin/env python3
"""
GAM3S.GG 90-Day Vertical Breakdown
Pulls GA4 + GSC data to quantify user behaviors across three verticals:
1. Content & Discovery (guides, news, reviews, games, awards, livestreams)
2. User Profiles (profiles, leaderboard, XP, achievements)
3. GAM3 Quests (quests, mystery boxes, missions)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from urllib.parse import unquote

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, OrderBy, Filter, FilterExpression
)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build as gapi_build
import pytz

# Configuration
GA4_PROPERTY_ID = "334095714"
GSC_SITE_URL = "sc-domain:gam3s.gg"
CREDS_PATH = Path.home() / ".openclaw" / "credentials" / "gam3s-google-sa.json"
TIMEZONE = pytz.timezone('Asia/Dubai')

now = datetime.now(TIMEZONE)
today = now.date()
start_90 = (today - timedelta(days=90)).strftime('%Y-%m-%d')
end_today = today.strftime('%Y-%m-%d')

creds = Credentials.from_service_account_file(
    CREDS_PATH,
    scopes=[
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/webmasters.readonly",
    ]
)
ga4 = BetaAnalyticsDataClient(credentials=creds)
gsc = gapi_build('searchconsole', 'v1', credentials=creds)


def classify_vertical(path: str) -> str:
    p = path.lower()
    # Quests vertical
    if any(x in p for x in ['/quests', '/quest/', '/mystery-box', '/missions']):
        return 'quests'
    # Profile vertical
    if any(x in p for x in ['/profile', '/leaderboard', '/inventory', '/achievements',
                              '/settings', '/connect', '/account']):
        return 'profiles'
    # Content & Discovery
    if any(x in p for x in ['/guides/', '/guia/', '/guias/', '/guide/',
                              '/news/', '/noticias/', '/noticia/', '/actualites/',
                              '/reviews/', '/review/',
                              '/games/', '/game/', '/juegos/', '/jeux/',
                              '/awards', '/gam3-awards',
                              '/genres/', '/genre/',
                              '/streams', '/livestream', '/live',
                              '/analytics']):
        return 'content'
    # Homepage
    if p in ('/', '', '/en/', '/es/', '/pt/', '/ja/', '/fr/', '/de/', '/ko/', '/tr/', '/it/'):
        return 'content'
    return 'other'


def classify_subcategory(path: str) -> str:
    p = path.lower()
    if any(x in p for x in ['/guides/', '/guia/', '/guias/', '/guide/']):
        return 'Guides'
    if any(x in p for x in ['/news/', '/noticias/', '/noticia/', '/actualites/']):
        return 'News'
    if any(x in p for x in ['/reviews/', '/review/']):
        return 'Reviews'
    if any(x in p for x in ['/games/', '/game/', '/juegos/', '/jeux/']):
        return 'Games Library'
    if any(x in p for x in ['/awards', '/gam3-awards']):
        return 'GAM3 Awards'
    if any(x in p for x in ['/genres/', '/genre/']):
        return 'Genres'
    if any(x in p for x in ['/streams', '/livestream', '/live']):
        return 'Livestreams'
    if any(x in p for x in ['/analytics']):
        return 'Game Analytics'
    if p in ('/', '', '/en/', '/es/', '/pt/', '/ja/', '/fr/', '/de/', '/ko/', '/tr/', '/it/'):
        return 'Homepage'
    if any(x in p for x in ['/quests', '/quest/']):
        return 'Quests'
    if any(x in p for x in ['/mystery-box']):
        return 'Mystery Boxes'
    if any(x in p for x in ['/missions']):
        return 'Missions'
    if any(x in p for x in ['/profile']):
        return 'Profiles'
    if any(x in p for x in ['/leaderboard']):
        return 'Leaderboard'
    if any(x in p for x in ['/inventory']):
        return 'Inventory'
    if any(x in p for x in ['/achievements']):
        return 'Achievements'
    if any(x in p for x in ['/connect', '/account', '/settings']):
        return 'Account/Connect'
    return 'Other'


print(f"Fetching GA4 data: {start_90} to {end_today} (90 days)")
print("=" * 70)

# --- GA4: All pages with path, 90 days ---
# We need a big limit to capture all page paths
req = RunReportRequest(
    property=f"properties/{GA4_PROPERTY_ID}",
    date_ranges=[DateRange(start_date=start_90, end_date=end_today)],
    dimensions=[
        Dimension(name="pagePath"),
        Dimension(name="pageTitle"),
    ],
    metrics=[
        Metric(name="sessions"),
        Metric(name="totalUsers"),
        Metric(name="screenPageViews"),
        Metric(name="averageSessionDuration"),
        Metric(name="bounceRate"),
        Metric(name="newUsers"),
    ],
    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
    limit=10000,
)
print("Fetching page-level data...")
report = ga4.run_report(req)
print(f"  Got {len(report.rows)} page rows")

# --- GA4: Overall site totals ---
req_totals = RunReportRequest(
    property=f"properties/{GA4_PROPERTY_ID}",
    date_ranges=[DateRange(start_date=start_90, end_date=end_today)],
    metrics=[
        Metric(name="sessions"),
        Metric(name="totalUsers"),
        Metric(name="screenPageViews"),
        Metric(name="newUsers"),
        Metric(name="averageSessionDuration"),
        Metric(name="bounceRate"),
    ],
    limit=1,
)
print("Fetching site totals...")
totals_report = ga4.run_report(req_totals)

# --- GA4: Event counts (for XP, quest completions etc) ---
req_events = RunReportRequest(
    property=f"properties/{GA4_PROPERTY_ID}",
    date_ranges=[DateRange(start_date=start_90, end_date=end_today)],
    dimensions=[
        Dimension(name="eventName"),
    ],
    metrics=[
        Metric(name="eventCount"),
        Metric(name="totalUsers"),
    ],
    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
    limit=500,
)
print("Fetching event data...")
events_report = ga4.run_report(req_events)
print(f"  Got {len(events_report.rows)} event types")

# --- GA4: Traffic sources ---
req_sources = RunReportRequest(
    property=f"properties/{GA4_PROPERTY_ID}",
    date_ranges=[DateRange(start_date=start_90, end_date=end_today)],
    dimensions=[
        Dimension(name="sessionDefaultChannelGroup"),
    ],
    metrics=[
        Metric(name="sessions"),
        Metric(name="totalUsers"),
        Metric(name="newUsers"),
    ],
    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
    limit=50,
)
print("Fetching traffic sources...")
sources_report = ga4.run_report(req_sources)

# --- GA4: Languages ---
req_langs = RunReportRequest(
    property=f"properties/{GA4_PROPERTY_ID}",
    date_ranges=[DateRange(start_date=start_90, end_date=end_today)],
    dimensions=[
        Dimension(name="language"),
    ],
    metrics=[
        Metric(name="sessions"),
        Metric(name="totalUsers"),
    ],
    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
    limit=50,
)
print("Fetching language data...")
langs_report = ga4.run_report(req_langs)

# --- GA4: Device categories ---
req_devices = RunReportRequest(
    property=f"properties/{GA4_PROPERTY_ID}",
    date_ranges=[DateRange(start_date=start_90, end_date=end_today)],
    dimensions=[
        Dimension(name="deviceCategory"),
    ],
    metrics=[
        Metric(name="sessions"),
        Metric(name="totalUsers"),
    ],
    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
    limit=10,
)
print("Fetching device data...")
devices_report = ga4.run_report(req_devices)

# --- GSC: Top queries 90 days ---
print("Fetching GSC queries (90d)...")
gsc_start = (today - timedelta(days=90)).strftime('%Y-%m-%d')
gsc_queries = gsc.searchanalytics().query(
    siteUrl=GSC_SITE_URL,
    body={
        'startDate': gsc_start, 'endDate': end_today,
        'dimensions': ['query'], 'rowLimit': 1000, 'dataState': 'all',
    }
).execute().get('rows', [])
print(f"  Got {len(gsc_queries)} queries")

# --- GSC: Top pages 90 days ---
print("Fetching GSC pages (90d)...")
gsc_pages = gsc.searchanalytics().query(
    siteUrl=GSC_SITE_URL,
    body={
        'startDate': gsc_start, 'endDate': end_today,
        'dimensions': ['page'], 'rowLimit': 1000, 'dataState': 'all',
    }
).execute().get('rows', [])
print(f"  Got {len(gsc_pages)} pages")

print("\n" + "=" * 70)
print("PROCESSING...")
print("=" * 70)

# ===================== PROCESS DATA =====================

# Site totals
if totals_report.rows:
    m = totals_report.rows[0].metric_values
    site_sessions = int(m[0].value)
    site_users = int(m[1].value)
    site_pageviews = int(m[2].value)
    site_new_users = int(m[3].value)
    site_avg_duration = float(m[4].value)
    site_bounce = float(m[5].value)
else:
    site_sessions = site_users = site_pageviews = site_new_users = 0
    site_avg_duration = site_bounce = 0.0

# Process pages into verticals
verticals = defaultdict(lambda: {
    'sessions': 0, 'users': 0, 'pageviews': 0, 'new_users': 0,
    'bounce_sum': 0.0, 'duration_sum': 0.0,
})
subcategories = defaultdict(lambda: {
    'sessions': 0, 'users': 0, 'pageviews': 0,
    'bounce_sum': 0.0, 'duration_sum': 0.0,
    'top_pages': [],
})

for row in report.rows:
    path = row.dimension_values[0].value
    title = row.dimension_values[1].value
    sessions = int(row.metric_values[0].value)
    users = int(row.metric_values[1].value)
    pageviews = int(row.metric_values[2].value)
    avg_dur = float(row.metric_values[3].value)
    bounce = float(row.metric_values[4].value)
    new_u = int(row.metric_values[5].value)

    vert = classify_vertical(path)
    subcat = classify_subcategory(path)

    v = verticals[vert]
    v['sessions'] += sessions
    v['users'] += users
    v['pageviews'] += pageviews
    v['new_users'] += new_u
    v['bounce_sum'] += bounce * sessions
    v['duration_sum'] += avg_dur * sessions

    sc = subcategories[subcat]
    sc['sessions'] += sessions
    sc['users'] += users
    sc['pageviews'] += pageviews
    sc['bounce_sum'] += bounce * sessions
    sc['duration_sum'] += avg_dur * sessions
    if len(sc['top_pages']) < 5:
        clean_title = title.replace(' | GAM3S.GG', '').strip()
        sc['top_pages'].append({
            'path': path, 'title': clean_title or path,
            'sessions': sessions, 'users': users, 'pageviews': pageviews,
        })

# Events
events = {}
for row in events_report.rows:
    name = row.dimension_values[0].value
    count = int(row.metric_values[0].value)
    ev_users = int(row.metric_values[1].value)
    events[name] = {'count': count, 'users': ev_users}

# Sources
sources = []
for row in sources_report.rows:
    sources.append({
        'channel': row.dimension_values[0].value,
        'sessions': int(row.metric_values[0].value),
        'users': int(row.metric_values[1].value),
        'new_users': int(row.metric_values[2].value),
    })

# Languages
languages = []
for row in langs_report.rows:
    languages.append({
        'lang': row.dimension_values[0].value,
        'sessions': int(row.metric_values[0].value),
        'users': int(row.metric_values[1].value),
    })

# Devices
devices = []
for row in devices_report.rows:
    devices.append({
        'device': row.dimension_values[0].value,
        'sessions': int(row.metric_values[0].value),
        'users': int(row.metric_values[1].value),
    })

# GSC totals
gsc_total_clicks = sum(r.get('clicks', 0) for r in gsc_queries)
gsc_total_impressions = sum(r.get('impressions', 0) for r in gsc_queries)

# ===================== OUTPUT =====================
output = []
def out(s=""):
    output.append(s)
    print(s)

out(f"{'='*70}")
out(f"GAM3S.GG — 90-DAY PLATFORM BEHAVIOR REPORT")
out(f"Period: {start_90} to {end_today}")
out(f"Generated: {now.strftime('%Y-%m-%d %H:%M')} Dubai Time")
out(f"{'='*70}")

out(f"\n{'='*70}")
out("SITE-WIDE TOTALS (90 DAYS)")
out(f"{'='*70}")
out(f"  Total Sessions:        {site_sessions:,}")
out(f"  Total Users:           {site_users:,}")
out(f"  New Users:             {site_new_users:,}")
out(f"  Returning Users:       ~{site_users - site_new_users:,}")
out(f"  Total Pageviews:       {site_pageviews:,}")
out(f"  Avg Session Duration:  {site_avg_duration:.1f}s")
out(f"  Bounce Rate:           {site_bounce:.1%}")
out(f"  GSC Total Clicks:      {gsc_total_clicks:,}")
out(f"  GSC Total Impressions: {gsc_total_impressions:,}")

out(f"\n{'='*70}")
out("TRAFFIC SOURCES (90 DAYS)")
out(f"{'='*70}")
for s in sources:
    pct = (s['sessions'] / site_sessions * 100) if site_sessions else 0
    out(f"  {s['channel']:30s}  {s['sessions']:>8,} sessions ({pct:.1f}%)  |  {s['users']:,} users  |  {s['new_users']:,} new")

out(f"\n{'='*70}")
out("VERTICAL BREAKDOWN (90 DAYS)")
out(f"{'='*70}")

vert_names = {
    'content': '1. CONTENT & DISCOVERY',
    'profiles': '2. USER PROFILES',
    'quests': '3. GAM3 QUESTS',
    'other': '4. OTHER PAGES',
}

for key in ['content', 'profiles', 'quests', 'other']:
    v = verticals[key]
    if v['sessions'] == 0:
        avg_b = avg_d = 0
    else:
        avg_b = v['bounce_sum'] / v['sessions']
        avg_d = v['duration_sum'] / v['sessions']
    pct = (v['sessions'] / site_sessions * 100) if site_sessions else 0

    out(f"\n  --- {vert_names[key]} ---")
    out(f"  Sessions:    {v['sessions']:>10,}  ({pct:.1f}% of total)")
    out(f"  Users:       {v['users']:>10,}")
    out(f"  Pageviews:   {v['pageviews']:>10,}")
    out(f"  New Users:   {v['new_users']:>10,}")
    out(f"  Avg Duration:{avg_d:>10.1f}s")
    out(f"  Bounce Rate: {avg_b:>10.1%}")

out(f"\n{'='*70}")
out("SUBCATEGORY BREAKDOWN (90 DAYS)")
out(f"{'='*70}")

# Sort subcategories by sessions
sorted_subcats = sorted(subcategories.items(), key=lambda x: x[1]['sessions'], reverse=True)
for name, sc in sorted_subcats:
    if sc['sessions'] == 0:
        continue
    avg_b = sc['bounce_sum'] / sc['sessions'] if sc['sessions'] else 0
    avg_d = sc['duration_sum'] / sc['sessions'] if sc['sessions'] else 0
    pct = (sc['sessions'] / site_sessions * 100) if site_sessions else 0

    out(f"\n  [{name}]  —  {sc['sessions']:,} sessions ({pct:.1f}%)  |  {sc['users']:,} users  |  {sc['pageviews']:,} pvs  |  {avg_d:.0f}s avg  |  {avg_b:.0%} bounce")
    for p in sc['top_pages'][:3]:
        out(f"    - {p['title'][:80]}  ({p['sessions']:,} sessions, {p['users']:,} users)")

out(f"\n{'='*70}")
out("KEY EVENTS (90 DAYS)")
out(f"{'='*70}")

# Show all events sorted by count
interesting_events = sorted(events.items(), key=lambda x: x[1]['count'], reverse=True)
for name, ev in interesting_events[:40]:
    out(f"  {name:40s}  {ev['count']:>10,} events  |  {ev['users']:,} users")

out(f"\n{'='*70}")
out("LANGUAGES (TOP 20)")
out(f"{'='*70}")
for i, l in enumerate(languages[:20]):
    pct = (l['sessions'] / site_sessions * 100) if site_sessions else 0
    out(f"  {i+1:2d}. {l['lang']:25s}  {l['sessions']:>8,} sessions ({pct:.1f}%)  |  {l['users']:,} users")

out(f"\n{'='*70}")
out("DEVICES")
out(f"{'='*70}")
for d in devices:
    pct = (d['sessions'] / site_sessions * 100) if site_sessions else 0
    out(f"  {d['device']:15s}  {d['sessions']:>10,} sessions ({pct:.1f}%)  |  {d['users']:,} users")

out(f"\n{'='*70}")
out("SEARCH CONSOLE — TOP 20 QUERIES (90 DAYS)")
out(f"{'='*70}")
gsc_queries_sorted = sorted(gsc_queries, key=lambda x: x.get('clicks', 0), reverse=True)
for q in gsc_queries_sorted[:20]:
    query = q['keys'][0]
    clicks = q.get('clicks', 0)
    impr = q.get('impressions', 0)
    ctr = q.get('ctr', 0)
    pos = q.get('position', 0)
    out(f"  \"{query}\"  —  {clicks:,} clicks  |  {impr:,} impr  |  {ctr:.1%} CTR  |  pos {pos:.1f}")

out(f"\n{'='*70}")
out("SEARCH CONSOLE — TOP PAGES BY CLICKS (90 DAYS)")
out(f"{'='*70}")
gsc_pages_sorted = sorted(gsc_pages, key=lambda x: x.get('clicks', 0), reverse=True)
for p in gsc_pages_sorted[:20]:
    url = p['keys'][0]
    # Shorten URL for display
    short_url = url.replace('https://gam3s.gg', '')
    clicks = p.get('clicks', 0)
    impr = p.get('impressions', 0)
    ctr = p.get('ctr', 0)
    pos = p.get('position', 0)
    out(f"  {short_url[:70]:70s}  {clicks:>6,} clicks  |  {impr:>8,} impr  |  {ctr:.1%} CTR  |  pos {pos:.1f}")

# Save to file
out_text = "\n".join(output)
out_file = Path(__file__).parent / "gam3s_90d_report.txt"
out_file.write_text(out_text, encoding="utf-8")
print(f"\n\nReport saved to: {out_file}")
