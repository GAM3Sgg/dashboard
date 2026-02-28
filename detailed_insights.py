#!/usr/bin/env python3
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2.service_account import Credentials
from pathlib import Path
from datetime import datetime, timedelta
import pytz

creds = Credentials.from_service_account_file(Path.home() / '.openclaw/credentials/gam3s-google-sa.json')
client = BetaAnalyticsDataClient(credentials=creds)

tz = pytz.timezone('Asia/Dubai')
now = datetime.now(tz)
seven_days_ago = now - timedelta(days=7)
yesterday = now - timedelta(days=1)

start_date_7d = seven_days_ago.strftime('%Y-%m-%d')
end_date_7d = yesterday.strftime('%Y-%m-%d')
yesterday_str = yesterday.strftime('%Y-%m-%d')

print('=' * 120)
print('EXPANDED 7-DAY INSIGHTS (Feb 20-26)')
print('=' * 120)
print()

# Top 15 pages with detailed metrics
print('TOP 15 CONTENT PIECES (WITH ENGAGEMENT BREAKDOWN):')
print('-' * 120)

request = RunReportRequest(
    property='properties/334095714',
    date_ranges=[DateRange(start_date=start_date_7d, end_date=end_date_7d)],
    dimensions=[Dimension(name='pageTitle')],
    metrics=[
        Metric(name='sessions'),
        Metric(name='screenPageViews'),
        Metric(name='bounceRate'),
        Metric(name='averageSessionDuration'),
        Metric(name='engagedSessions')
    ]
)

response = client.run_report(request)
pages = []
for row in response.rows:
    title = row.dimension_values[0].value
    sessions = int(row.metric_values[0].value)
    views = int(row.metric_values[1].value)
    bounce = float(row.metric_values[2].value)
    duration = float(row.metric_values[3].value)
    engaged = int(row.metric_values[4].value)
    
    pages.append({
        'title': title,
        'sessions': sessions,
        'views': views,
        'bounce': bounce,
        'duration': duration,
        'engaged': engaged,
        'engagement_rate': (engaged / sessions * 100) if sessions > 0 else 0,
        'pages_per_session': views / sessions if sessions > 0 else 0
    })

pages.sort(key=lambda x: x['sessions'], reverse=True)

for i, p in enumerate(pages[:15], 1):
    clean_title = p['title'].split(' | ')[0][:60]
    print(f"{i:2}. {p['sessions']:>6,} sessions | {p['engagement_rate']:>4.0f}% engaged | {p['duration']:>4.0f}s avg")
    print(f"    {clean_title}")
    print(f"    Views: {p['views']:,} | Pages/session: {p['pages_per_session']:.2f} | Bounce: {p['bounce']:.0f}%")
    print()

# Language breakdown
print()
print('LANGUAGE PERFORMANCE (7-Day):')
print('-' * 120)

request = RunReportRequest(
    property='properties/334095714',
    date_ranges=[DateRange(start_date=start_date_7d, end_date=end_date_7d)],
    dimensions=[Dimension(name='language')],
    metrics=[Metric(name='sessions'), Metric(name='bounceRate'), Metric(name='averageSessionDuration')]
)

response = client.run_report(request)
lang_data = []
for row in response.rows:
    lang = row.dimension_values[0].value
    sessions = int(row.metric_values[0].value)
    bounce = float(row.metric_values[1].value)
    duration = float(row.metric_values[2].value)
    lang_data.append((sessions, lang, bounce, duration))

lang_data.sort(reverse=True)
total_sessions = 364227
for sessions, lang, bounce, duration in lang_data[:12]:
    pct = sessions * 100 / total_sessions
    print(f"  {lang:15} | {sessions:>8,} ({pct:>4.1f}%) | {bounce:>3.0f}% bounce | {duration:>4.0f}s")

print()
print('DEVICE BREAKDOWN (7-Day):')
print('-' * 120)

request = RunReportRequest(
    property='properties/334095714',
    date_ranges=[DateRange(start_date=start_date_7d, end_date=end_date_7d)],
    dimensions=[Dimension(name='deviceCategory')],
    metrics=[Metric(name='sessions'), Metric(name='bounceRate'), Metric(name='averageSessionDuration')]
)

response = client.run_report(request)
for row in response.rows:
    device = row.dimension_values[0].value
    sessions = int(row.metric_values[0].value)
    bounce = float(row.metric_values[1].value)
    duration = float(row.metric_values[2].value)
    pct = sessions * 100 / total_sessions
    print(f"  {device:15} | {sessions:>8,} ({pct:>5.1f}%) | {bounce:>3.0f}% bounce | {duration:>4.0f}s")

# Now do 24-hour
print()
print()
print('=' * 120)
print(f'EXPANDED 24-HOUR INSIGHTS ({yesterday_str})')
print('=' * 120)
print()

print('TOP 15 CONTENT PIECES (WITH ENGAGEMENT BREAKDOWN):')
print('-' * 120)

request = RunReportRequest(
    property='properties/334095714',
    date_ranges=[DateRange(start_date=yesterday_str, end_date=yesterday_str)],
    dimensions=[Dimension(name='pageTitle')],
    metrics=[
        Metric(name='sessions'),
        Metric(name='screenPageViews'),
        Metric(name='bounceRate'),
        Metric(name='averageSessionDuration'),
        Metric(name='engagedSessions')
    ]
)

response = client.run_report(request)
pages_24h = []
for row in response.rows:
    title = row.dimension_values[0].value
    sessions = int(row.metric_values[0].value)
    views = int(row.metric_values[1].value)
    bounce = float(row.metric_values[2].value)
    duration = float(row.metric_values[3].value)
    engaged = int(row.metric_values[4].value)
    
    pages_24h.append({
        'title': title,
        'sessions': sessions,
        'views': views,
        'bounce': bounce,
        'duration': duration,
        'engaged': engaged,
        'engagement_rate': (engaged / sessions * 100) if sessions > 0 else 0,
        'pages_per_session': views / sessions if sessions > 0 else 0
    })

pages_24h.sort(key=lambda x: x['sessions'], reverse=True)

for i, p in enumerate(pages_24h[:15], 1):
    clean_title = p['title'].split(' | ')[0][:60]
    print(f"{i:2}. {p['sessions']:>6,} sessions | {p['engagement_rate']:>4.0f}% engaged | {p['duration']:>4.0f}s avg")
    print(f"    {clean_title}")
    print(f"    Views: {p['views']:,} | Pages/session: {p['pages_per_session']:.2f} | Bounce: {p['bounce']:.0f}%")
    print()

print()
print('LANGUAGE PERFORMANCE (24-Hour):')
print('-' * 120)

request = RunReportRequest(
    property='properties/334095714',
    date_ranges=[DateRange(start_date=yesterday_str, end_date=yesterday_str)],
    dimensions=[Dimension(name='language')],
    metrics=[Metric(name='sessions'), Metric(name='bounceRate'), Metric(name='averageSessionDuration')]
)

response = client.run_report(request)
lang_data_24h = []
for row in response.rows:
    lang = row.dimension_values[0].value
    sessions = int(row.metric_values[0].value)
    bounce = float(row.metric_values[1].value)
    duration = float(row.metric_values[2].value)
    lang_data_24h.append((sessions, lang, bounce, duration))

lang_data_24h.sort(reverse=True)
total_24h = 39645
for sessions, lang, bounce, duration in lang_data_24h[:12]:
    pct = sessions * 100 / total_24h
    print(f"  {lang:15} | {sessions:>8,} ({pct:>4.1f}%) | {bounce:>3.0f}% bounce | {duration:>4.0f}s")

print()
print('DEVICE BREAKDOWN (24-Hour):')
print('-' * 120)

request = RunReportRequest(
    property='properties/334095714',
    date_ranges=[DateRange(start_date=yesterday_str, end_date=yesterday_str)],
    dimensions=[Dimension(name='deviceCategory')],
    metrics=[Metric(name='sessions'), Metric(name='bounceRate'), Metric(name='averageSessionDuration')]
)

response = client.run_report(request)
for row in response.rows:
    device = row.dimension_values[0].value
    sessions = int(row.metric_values[0].value)
    bounce = float(row.metric_values[1].value)
    duration = float(row.metric_values[2].value)
    pct = sessions * 100 / total_24h
    print(f"  {device:15} | {sessions:>8,} ({pct:>5.1f}%) | {bounce:>3.0f}% bounce | {duration:>4.0f}s")

print()
