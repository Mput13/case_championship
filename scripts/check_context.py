#!/usr/bin/env python3
"""Offline integrity checks; not an assertion that every external claim is true."""
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / 'context'
errors = []
counts = {'files': 0, 'csv': 0, 'json': 0, 'local_links': 0, 'hashes': 0}

def check(ok, message):
    if not ok:
        errors.append(message)

def records(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

names = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
files = sorted({ROOT / p for p in names if p})
for p in files:
    if not p.is_file():
        continue
    counts['files'] += 1
    rel = p.relative_to(ROOT).as_posix()
    check(not any(x in rel for x in ['_dom.txt', '_messages.json', 'catalog_export', 'local_manifest.json', 'source_names.json', 'deep_research_links.json', 'capture_status.md', 'delegations.json', 'connector_diagnostic.md', 'browser_evidence/']), f'Private raw artifact included: {rel}')
    if p.suffix == '.csv':
        counts['csv'] += 1
        with p.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        check(bool(rows), f'Empty CSV: {rel}')
        if rows:
            check(len(set(rows[0])) == len(rows[0]), f'Duplicate CSV columns: {rel}')
            check(all(len(row) == len(rows[0]) for row in rows[1:]), f'CSV width mismatch: {rel}')
    elif p.suffix == '.json':
        counts['json'] += 1
        try:
            json.loads(p.read_text())
        except json.JSONDecodeError as e:
            errors.append(f'Invalid JSON {rel}: {e}')
    elif p.suffix == '.md':
        text = p.read_text()
        check('file://' not in text, f'Nonportable file URI: {rel}')
        for target in re.findall(r'\]\(([^)]+)\)', text):
            target = target.strip().strip('<>')
            if urlsplit(target).scheme or target.startswith('#'):
                continue
            path = unquote(target.split('#',1)[0])
            if not path:
                continue
            counts['local_links'] += 1
            check((p.parent / path).exists(), f'Broken local link {rel}: {target}')

registry = records(CTX/'05_datasets/source_registry.csv')
ids = {r['record_id'] for r in registry}
check(len(ids) == len(registry), 'Duplicate discovery record IDs')
for r in registry:
    check((CTX/r['provenance']).is_file(), f'Missing provenance {r["record_id"]}')
    u=urlsplit(r['url'])
    check(u.scheme in ('http','https') and bool(u.netloc) and u.username is None, f'Invalid URL {r["record_id"]}')
reviews = records(CTX/'05_datasets/source_reviews.csv')
check(len({r['review_id'] for r in reviews})==len(reviews), 'Duplicate review IDs')
for r in reviews:
    check(not r['original_record_id'] or r['original_record_id'] in ids, f'Missing reviewed record {r["review_id"]}')
    check((CTX/r['provenance']).is_file(), f'Missing review provenance {r["review_id"]}')
index = json.loads((CTX/'05_datasets/source_index.json').read_text())
check(sorted(i for v in index.values() for i in v['records'])==sorted(ids), 'URL index membership mismatch')
for r in registry:
    check(r['source_key'] in index and r['record_id'] in index[r['source_key']]['records'], f'URL key mismatch {r["record_id"]}')

sample_dir = CTX/'07_verification/terra_data/samples'
for item in json.loads((sample_dir/'manifest.json').read_text())['files']:
    data=(sample_dir/item['path']).read_bytes();counts['hashes']+=1
    check(len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'], f'Sample hash/size mismatch: {item["path"]}')
av_dir = CTX/'07_verification/terra_aviation_review'
m = json.loads((av_dir/'sample_manifest.json').read_text())
data = (av_dir/m['output_file']).read_bytes(); counts['hashes']+=1
check(hashlib.sha256(data).hexdigest()==m['output_sha256'], '59496 sample hash mismatch')
check(len(records(av_dir/m['output_file']))==m['rows'], '59496 sample row count mismatch')
cities=records(CTX/'07_verification/terra_cities_review/corrected_cities.csv')
check(len(cities)>=10 and len({r['iata'] for r in cities})==len(cities), 'City count or IATA duplication')
for r in cities:
    check(not r['pax_2025'] or bool(r['pax_source_status'] and r['pax_source_url'] and r['pax_2025_qualifier']), f'City value lacks provenance or qualifier: {r["city"]}')

print(json.dumps({'status':'FAIL' if errors else 'PASS','counts':counts,'discovery_records':len(registry),'unique_urls':len(index),'review_records':len(reviews),'cities':len(cities),'errors':errors},ensure_ascii=False,indent=2))
sys.exit(bool(errors))
