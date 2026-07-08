#!/usr/bin/env python3
"""
Collect WallStreetCN articles related to Federal Reserve.
Usage: python3 tools/collect_wallstreet.py
Output: stdout JSON array of normalized items
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; FedNoWatch/1.0)'}

BASE_URL = 'https://api-one-wscn.awtmt.com/apiv1/search/article'

# Multiple search queries to capture all Fed-related content
QUERIES = [
    '美联储',
    '鲍威尔',
    '联储利率',
    'FOMC',
    '特朗普 美联储',
    '联邦基金利率',
    '美联储 加息',
    '美联储 降息',
    'Wall Street Fed',
]


def fetch_query(query, limit=10):
    """Search WallStreetCN API with a query and return raw response."""
    import urllib.parse
    params = urllib.parse.urlencode({'query': query, 'limit': limit})
    url = f'{BASE_URL}?{params}'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'[WARN] Failed to query "{query}": {e}', file=sys.stderr)
        return None


def parse_item(raw_item, query_used):
    """Parse a WallStreetCN API item into normalized format."""
    resource = raw_item.get('resource', {})
    if not resource:
        resource = raw_item  # fallback if no wrapper

    title = (resource.get('title') or '').strip()
    url = (resource.get('uri') or '').strip()
    if not url and resource.get('url'):
        url = resource['url'].strip()
    summary = (resource.get('content_short') or '').strip()
    ts = resource.get('display_time', 0)
    author_info = resource.get('author', {})

    if not title:
        return None

    # Build an ID
    item_id = url.split('/')[-1] if '/articles/' in url else f'wscn-{hash(title + url) & 0x7fffffff}'

    # Parse timestamp
    published_at = None
    if ts:
        try:
            published_at = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            pass

    # Determine category
    category = 'media_opinion'
    query_lower = query_used.lower()
    if '鲍威尔' in query_lower or '讲话' in query_lower:
        category = 'media_speech'

    title_lower = title.lower()
    if any(w in title_lower for w in ['fomc', '议息', '决议', '声明', 'fed statement']):
        category = 'media_fomc'
    elif any(w in title_lower for w in ['加息', '降息', '利率决议', 'rate decision']):
        category = 'media_rate'

    return {
        'id': f'wscn-{item_id}',
        'source': 'wallstreetcn',
        'source_label': '华尔街见闻',
        'category': category,
        'title': title,
        'summary': summary[:500] if summary else '',
        'url': url if url.startswith('http') else f'https://wallstreetcn.com/articles/{url}',
        'published_at': published_at or '',
        'language': 'zh',
        'speaker': None,
        'keywords': [query_used],
    }


def collect_all():
    all_items = []
    seen_ids = set()

    for query in QUERIES:
        resp = fetch_query(query, limit=10)
        if not resp or resp.get('code') != 20000:
            continue

        data = resp.get('data') or {}
        resp_items = data.get('items') or []
        print(f'[INFO] "{query}" → {len(resp_items)} results', file=sys.stderr)

        for raw_item in resp_items:
            parsed = parse_item(raw_item, query)
            if parsed and parsed['id'] not in seen_ids:
                all_items.append(parsed)

    all_items.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    return all_items


if __name__ == '__main__':
    items = collect_all()
    print(json.dumps(items, ensure_ascii=False, indent=2))
    print(f'[INFO] Collected {len(items)} items from WallStreetCN', file=sys.stderr)
