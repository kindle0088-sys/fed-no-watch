#!/usr/bin/env python3
"""
Merge collected data from all sources, deduplicate, sort, and output.
Usage: python3 tools/build_data.py
Output: assets/js/data.js (JavaScript data file for the static site)
"""

import json
import os
import sys
from datetime import datetime, timezone

# Ensure we can import collectors
sys.path.insert(0, os.path.dirname(__file__))

# ---- Import collectors ----

# Fed collector
from collect_fed import collect_all as collect_fed_all

# WallStreetCN collector
from collect_wallstreet import collect_all as collect_wallstreet_all


# ---- Deduplication ----

def normalize_url(url):
    """Normalize URL for dedup: strip trailing slash, utm params, etc."""
    if not url:
        return ''
    url = url.split('?')[0]  # strip query params
    url = url.rstrip('/')
    return url.lower()


def dedup_items(items):
    """Deduplicate by normalized URL, keep first occurrence."""
    seen_urls = set()
    seen_ids = set()
    deduped = []

    for item in items:
        url = normalize_url(item.get('url', ''))
        item_id = item.get('id', '')

        if url and url in seen_urls:
            continue
        if item_id and item_id in seen_ids:
            continue

        if url:
            seen_urls.add(url)
        if item_id:
            seen_ids.add(item_id)

        deduped.append(item)

    return deduped


def parse_dt_sort_key(item):
    """Get sort key from published_at."""
    dt = item.get('published_at', '')
    if not dt:
        return ''  # no-date items go last
    # Remove timezone info for comparison
    return dt.replace('+00:00', '').replace('Z', '')


def collect_and_merge():
    """Run all collectors, dedup, sort, and return merged list."""
    all_items = []

    print('[build] Collecting Fed RSS...', file=sys.stderr)
    try:
        fed_items = collect_fed_all()
        print(f'[build] Fed RSS: {len(fed_items)} items', file=sys.stderr)
        all_items.extend(fed_items)
    except Exception as e:
        print(f'[build] Fed collection failed: {e}', file=sys.stderr)

    print('[build] Collecting WallStreetCN...', file=sys.stderr)
    try:
        wscn_items = collect_wallstreet_all()
        print(f'[build] WallStreetCN: {len(wscn_items)} items', file=sys.stderr)
        all_items.extend(wscn_items)
    except Exception as e:
        print(f'[build] WallStreetCN collection failed: {e}', file=sys.stderr)

    print(f'[build] Total before dedup: {len(all_items)}', file=sys.stderr)
    all_items = dedup_items(all_items)
    print(f'[build] Total after dedup: {len(all_items)}', file=sys.stderr)

    # Sort by published_at descending
    all_items.sort(key=parse_dt_sort_key, reverse=True)

    return all_items


def build_site_data(items):
    """Build full site data object."""
    # FOMC meeting dates from Fed calendar (next few)
    fomc_dates = [
        {'date': '2026-07-29', 'label': 'FOMC Meeting'},
        {'date': '2026-09-16', 'label': 'FOMC Meeting + SEP'},
        {'date': '2026-10-28', 'label': 'FOMC Meeting'},
        {'date': '2026-12-09', 'label': 'FOMC Meeting + SEP'},
    ]

    data = {
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'site_title': 'Fed No Watch',
        'site_subtitle': '美联储新闻时间线 —— 每天跟上联储动态',
        'items': items,
        'fed_rate': {
            'target_lower': 3.50,
            'target_upper': 3.75,
            'effective_rate': 3.63,
            'rate_date': '2026-06-24',
            'fomc_dates': fomc_dates,
            'cme_probabilities': {
                'hold': 62.4,
                'hike_25bp': 37.6,
                'note': 'Source: CME FedWatch via growbeansprout.com as of 2026-06-23'
            }
        },
        'sources': [
            {
                'id': 'federal_reserve',
                'label': 'Federal Reserve',
                'description': 'Official US central bank press releases, FOMC statements, and speeches.',
                'homepage': 'https://www.federalreserve.gov/newsevents.htm'
            },
            {
                'id': 'wallstreetcn',
                'label': '华尔街见闻',
                'description': '中国领先的金融信息提供商，覆盖全球金融市场。',
                'homepage': 'https://wallstreetcn.com'
            },
        ],
        'stats': {
            'total_items': len(items),
            'fed_official': sum(1 for i in items if i.get('source') == 'federal_reserve'),
            'wallstreetcn': sum(1 for i in items if i.get('source') == 'wallstreetcn'),
        }
    }

    return data


DATA_OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'js', 'data.js')


def write_data_js(data):
    """Write site data as a JavaScript file."""
    os.makedirs(os.path.dirname(DATA_OUTPUT), exist_ok=True)

    # Pretty-print JSON
    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    js_content = f'const SITE_DATA = {json_str};\n'

    with open(DATA_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f'[build] Wrote {DATA_OUTPUT} ({os.path.getsize(DATA_OUTPUT)} bytes)', file=sys.stderr)


if __name__ == '__main__':
    items = collect_and_merge()
    site_data = build_site_data(items)
    write_data_js(site_data)
    print(json.dumps(site_data.get('stats', {}), ensure_ascii=False))
