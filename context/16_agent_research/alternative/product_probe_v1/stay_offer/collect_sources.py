#!/usr/bin/env python3
"""Read-only public-source collection using Python standard library; no booking API.

Run: python3 collect_sources.py collect
     python3 collect_sources.py verify
Raw HTTP entities remain ignored; published receipts contain SHA256, not local paths.
Fresh collection writes a new timestamped receipt file and never replaces observations.
"""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent
ALLOWED = {'content-type', 'content-length', 'last-modified', 'etag', 'date', 'cache-control'}

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def fetch(source):
    row = dict(source)
    row.update(observed_at_utc=now(), request_method='GET', auth='none', cookies_used=False,
               raw_retention='HELD_NOT_PUBLISHED', redistribution_license='UNKNOWN',
               extraction_policy='Publish independently transcribed factual fields only; full entities withheld')
    req = urllib.request.Request(source['url'], headers={'User-Agent': 'C14-public-stay-research/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            data = response.read(8_000_001)
            if len(data) > 8_000_000:
                raise ValueError('Response exceeds bounded 8 MB capture limit')
            row.update(http_status=response.status, final_url=response.url,
                       response_headers={k.lower(): v for k, v in response.headers.items() if k.lower() in ALLOWED},
                       raw_sha256=sha(data), bytes=len(data), access_status='FETCHED')
            suffix = '.pdf' if data.startswith(b'%PDF') else '.html'
            (BASE / 'raw_hold' / (source['source_id'] + '_' + sha(data) + suffix)).write_bytes(data)
    except Exception as exc:
        row.update(access_status='FAILED', error_type=type(exc).__name__, error=str(exc),
                   http_status=getattr(exc, 'code', 'UNKNOWN'), raw_sha256='UNKNOWN')
    return row

def collect():
    (BASE / 'raw_hold').mkdir(exist_ok=True)
    (BASE / 'receipts').mkdir(exist_ok=True)
    sources = json.loads((BASE / 'sources.json').read_text())
    if sys.argv[2:]:
        sources = [row for row in sources if row['source_id'] in sys.argv[2:]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, sources))
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = BASE / 'receipts' / (stamp + '.json')
    out.write_text(json.dumps({'collected_at_utc': now(), 'header_whitelist': sorted(ALLOWED), 'sources': rows}, ensure_ascii=False, indent=2) + '\n')
    for row in rows:
        print(row['source_id'], row['access_status'], row.get('bytes', 0), row['raw_sha256'])
    print('receipt', out.relative_to(BASE))

def verify():
    manifest = json.loads((BASE / 'dataset_manifest.json').read_text())
    checked = 0
    for file in manifest['files']:
        data = (BASE / file['path']).read_bytes()
        assert sha(data) == file['sha256'], file['path']
        checked += 1
    for receipt_path in (BASE / 'receipts').glob('*.json'):
        receipt = json.loads(receipt_path.read_text())
        for row in receipt['sources']:
            assert set(row.get('response_headers', {})) <= ALLOWED
            for raw in (BASE / 'raw_hold').glob(row['source_id'] + '_' + row['raw_sha256'] + '.*'):
                assert sha(raw.read_bytes()) == row['raw_sha256'], row['source_id']
    print('PASS', checked, 'published file hashes; receipt header whitelist')

if __name__ == '__main__':
    {'collect': collect, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'verify']()
