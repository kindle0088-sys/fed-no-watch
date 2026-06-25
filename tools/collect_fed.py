#!/usr/bin/env python3
"""
Collect Federal Reserve official RSS feeds and output normalized JSON.
Usage: python3 tools/collect_fed.py
Output: stdout JSON array of items, or --save to write to a temp file
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; FedNoWatch/1.0)'}

RSS_FEEDS = {
    'press_all': {
        'url': 'https://www.federalreserve.gov/feeds/press_all.xml',
        'category': 'press_release',
        'label': 'Federal Reserve Press Release',
    },
    'press_monetary': {
        'url': 'https://www.federalreserve.gov/feeds/press_monetary.xml',
        'category': 'fomc',
        'label': 'FOMC',
    },
    'speeches': {
        'url': 'https://www.federalreserve.gov/feeds/speeches.xml',
        'category': 'speech',
        'label': 'Fed Speech',
    },
}


def fetch_rss(feed_key, feed_info):
    """Fetch and parse an RSS feed, return list of normalized items."""
    req = urllib.request.Request(feed_info['url'], headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8')
    except Exception as e:
        print(f'[WARN] Failed to fetch {feed_key}: {e}', file=sys.stderr)
        return []

    items = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f'[WARN] Failed to parse RSS {feed_key}: {e}', file=sys.stderr)
        return []

    for entry in root.findall('.//item'):
        title = (entry.findtext('title') or '').strip()
        link = (entry.findtext('link') or '').strip()
        pub_date_str = (entry.findtext('pubDate') or '').strip()
        description = (entry.findtext('description') or '').strip()

        if not title or not link:
            continue

        # Parse publication date
        published_at = None
        for fmt in [
            '%a, %d %b %Y %H:%M:%S GMT',
            '%a, %d %b %Y %H:%M:%S %Z',
        ]:
            try:
                d = datetime.strptime(pub_date_str, fmt)
                published_at = d.replace(tzinfo=timezone.utc).isoformat()
                break
            except ValueError:
                continue

        item_id = f'fed-{feed_key}-{link.rstrip("/").split("/")[-1]}'

        # Try to extract speaker from speech title (e.g. "Cook, Welcome Remarks")
        speaker = None
        if feed_key == 'speeches':
            if ',' in title:
                speaker = title.split(',')[0].strip()

        items.append({
            'id': item_id,
            'source': 'federal_reserve',
            'source_label': feed_info['label'],
            'category': feed_info['category'],
            'title': title,
            'summary': description[:500] if description else '',
            'url': link,
            'published_at': published_at or pub_date_str,
            'language': 'en',
            'speaker': speaker,
            'keywords': ['federal reserve'],
        })

    return items


def collect_all():
    all_items = []
    seen_ids = set()

    for feed_key, feed_info in RSS_FEEDS.items():
        items = fetch_rss(feed_key, feed_info)
        for item in items:
            if item['id'] not in seen_ids:
                seen_ids.add(item['id'])
                all_items.append(item)

    # Sort by published_at descending
    all_items.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    return all_items


if __name__ == '__main__':
    items = collect_all()
    print(json.dumps(items, ensure_ascii=False, indent=2))
    print(f'[INFO] Collected {len(items)} items from Fed RSS', file=sys.stderr)
