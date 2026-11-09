#!/usr/bin/env python3
"""Acquire public HTTP source bytes without auth, retries or browser use.

Usage: python3 collectors/fetch_sources.py [source_id ...]
Existing receipts are immutable: use a new id for a later snapshot.
Only whitelisted HTTP response headers are persisted. Frozen source bodies remain
in ignored raw_hold because their redistribution rights/contact content vary.
"""
import concurrent.futures, datetime, hashlib, json, pathlib, sys, urllib.error, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
WHITELIST = {'content-type', 'content-length', 'last-modified', 'etag', 'date', 'cache-control'}
def acquire(source):
    sid = source['source_id']
    receipt = ROOT / 'receipts' / (sid + '.json')
    if receipt.exists():
        return {'source_id': sid, 'status': 'SKIPPED_FROZEN_RECEIPT_EXISTS'}
    meta = {**source, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'acquisition': 'Python stdlib urllib GET; TLS verification enabled; no auth/cookies; Accept-Encoding identity; no retries',
            'headers': {}, 'raw_redistribution': 'HELD_UNKNOWN_LICENCE'}
    try:
        req = urllib.request.Request(source['url'], headers={
            'User-Agent': 'Mozilla/5.0 (compatible; public-source-research/1.0)',
            'Accept-Encoding': 'identity'})
        try:
            response = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            response = e
        with response as r:
            body = r.read(5000001)
            if len(body) > 5000000:
                raise ValueError('Body exceeds bounded 5MB source limit')
            meta.update(status=r.status, final_url=r.url,
                        headers={k.lower(): v for k,v in r.headers.items() if k.lower() in WHITELIST})
            suffix = '.pdf' if 'application/pdf' in meta['headers'].get('content-type','') else '.html'
            relative = pathlib.Path('raw_hold') / (sid + suffix)
            (ROOT / relative).write_bytes(body)
            meta.update(raw_path=str(relative), sha256=hashlib.sha256(body).hexdigest(), byte_length=len(body))
    except Exception as e:
        meta.update(status='ERROR', error=type(e).__name__ + ': ' + str(e))
    meta['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    return {k:v for k,v in meta.items() if k not in ['headers']}
def main():
    sources = json.loads((ROOT / 'collectors/sources.json').read_text())
    if len(sys.argv) > 1:
        wanted = set(sys.argv[1:]); sources = [s for s in sources if s['source_id'] in wanted]
    (ROOT/'raw_hold').mkdir(exist_ok=True); (ROOT/'receipts').mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for item in pool.map(acquire, sources): print(json.dumps(item, ensure_ascii=False))
if __name__ == '__main__': main()
