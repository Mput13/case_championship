#!/usr/bin/env python3
"""Bounded public carrier reads. No cookies, auth, JS execution, or booking writes.

GET for official public pages; POST only the public get-availability query.
Headers are explicitly whitelisted. Credentials/session fields are never saved.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADERS = {'content-type', 'content-length', 'last-modified', 'etag', 'date', 'cache-control', 'retry-after'}
LIMIT = 3_000_000


def scrub(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if re.search(r'(^|_)(token|session|cookie|auth|authorization|sid)(_|$)', k, re.I) else scrub(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    ap.add_argument('--url', required=True)
    ap.add_argument('--outbound')
    ap.add_argument('--return-date')
    args = ap.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.id):
        raise ValueError('Invalid source id')
    parsed = urllib.parse.urlsplit(args.url)
    if parsed.scheme != 'https' or parsed.hostname not in {'azimuth.ru', 'booking.azimuth.ru'} or parsed.username or parsed.password:
        raise ValueError('Official HTTPS public carrier sources only')
    for folder in ['raw_hold', 'receipts']:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    target = ROOT / 'raw_hold' / (args.id + '.bin')
    receipt = ROOT / 'receipts' / (args.id + '.json')
    if target.exists() or receipt.exists():
        raise ValueError('Frozen id exists; choose a new id')
    method = 'GET'
    body = None
    request_parameters = None
    if args.outbound:
        if args.url != 'https://booking.azimuth.ru/rpc/tsh' or not args.return_date:
            raise ValueError('Only fixed get-availability endpoint and round-trip dates are allowed')
        for value in [args.outbound, args.return_date]:
            dt.datetime.strptime(value, '%d.%m.%Y')
        method = 'POST'
        request_parameters = {'owrt': 'RT', 'departure_point': 'KVX', 'arrival_point': 'MRV',
                              'outbound_date': args.outbound, 'return_date': args.return_date,
                              'adult_count': 1, 'child_count': 0, 'infant_count': 0,
                              'direct_only': 'Y', 'date_range': 3, 'promocode': '',
                              'return_full_names': 'Y', 'child_alone': ''}
        body = json.dumps([['trace', {}], ['get-availability', request_parameters]]).encode()
    rec = {'snapshot_id': args.id, 'source_url': args.url, 'method': method,
           'request_parameters': request_parameters, 'retrieved_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
           'source_status': 'ACCESS_FAILED', 'publication_date': 'UNKNOWN', 'licence': 'UNKNOWN',
           'headers_policy': 'seven-field-whitelist-no-cookie-auth',
           'raw_publication_status': 'LOCAL_HOLD_IGNORED', 'collector_version': 'air-offer-public-v1',
           'reproduce_command': ['python3', 'context/16_agent_research/alternative/product_probe_v1/air_offer/collect_sources.py',
                                 '--id', args.id + '_refresh', '--url', args.url]}
    if args.outbound:
        rec['reproduce_command'] += ['--outbound', args.outbound, '--return-date', args.return_date]
    response = None
    try:
        headers = {'User-Agent': 'case5-public-research/1'}
        if body is not None:
            headers['Content-Type'] = 'application/json; charset=UTF-8'
        req = urllib.request.Request(args.url, data=body, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(req, timeout=35)
        except urllib.error.HTTPError as exc:
            response = exc
            rec['error'] = f'HTTPError: HTTP Error {exc.code}: {exc.reason}'
        with response:
            raw = response.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise ValueError('3MB source guard exceeded')
            rec.update(http_status=response.status,
                       response_headers={k.lower(): v for k, v in response.headers.items() if k.lower() in HEADERS},
                       source_sha256=hashlib.sha256(raw).hexdigest(), source_size_bytes=len(raw))
        redacted = raw
        ctype = rec['response_headers'].get('content-type', '')
        if 'json' in ctype:
            obj = json.loads(raw)
            redacted = (json.dumps(scrub(obj), ensure_ascii=False, indent=2) + '\n').encode()
            rec['raw_storage_transform'] = 'JSON reserialization with credential-session field redaction'
        elif 'html' in ctype:
            redacted = re.sub(rb'(<(?:input|meta)\b[^>]*\bname=[\"\x27](?:authenticity_token|csrf[^\"\x27]*|[^\"\x27]*token)[\"\x27][^>]*\b(?:value|content)=[\"\x27])[^\"\x27]*', rb'\1[REDACTED]', raw, flags=re.I)
            rec['raw_storage_transform'] = 'Redact hidden form credential values; public content unchanged'
        target.write_bytes(redacted)
        rec.update(source_status='ACQUIRED_RAW' if rec['http_status'] < 400 else 'HTTP_ERROR_WITH_BODY',
                   raw_path='raw_hold/' + target.name, stored_sha256=hashlib.sha256(redacted).hexdigest(), stored_size_bytes=len(redacted))
    except Exception as exc:
        rec['error'] = f'{type(exc).__name__}: {exc}'
    rec['completed_at_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    receipt.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: rec.get(k) for k in ['snapshot_id', 'source_status', 'http_status', 'source_size_bytes', 'error']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
