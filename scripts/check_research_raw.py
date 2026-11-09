#!/usr/bin/env python3
"""Validate received bytes and record counts; no claim-level verification implied."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    manifest_bytes = args.manifest.read_bytes()
    results = []
    for d in json.loads(manifest_bytes)['datasets']:
        if not d.get('raw_path'):
            results.append({'dataset_id': d['dataset_id'], 'record_count': None,
                            'check_scope': 'NO_RAW_NOT_CHECKED',
                            'acquisition_status': d.get('acquisition_status'),
                            'error': d.get('error')})
            continue
        path = args.manifest.parent / d['raw_path']
        raw = path.read_bytes()
        decoded = gzip.decompress(raw) if d.get('compression') == 'gzip' else raw
        row = {'dataset_id': d['dataset_id'], 'raw_path': str(path),
               'source_url': d['source_url'], 'raw_file_sha256': digest(raw),
               'hash_matches': digest(decoded) == d['sha256'],
               'size_bytes': len(raw), 'record_count': None,
               'check_scope': 'BYTES_AND_PARSING_NOT_CLAIM_TRUTH'}
        if d.get('compression') == 'gzip':
            row['compressed_hash_matches'] = digest(raw) == d['compressed_sha256']
        if d['suffix'] == 'csv':
            records = list(csv.DictReader(io.StringIO(decoded.decode('utf-8-sig'))))
            row['record_count'] = len(records)
            if d['dataset_id'] == 'ourairports_airports':
                row['ru_records'] = sum(r['iso_country'] == 'RU' for r in records)
                row['ru_with_iata'] = sum(r['iso_country'] == 'RU' and bool(r['iata_code']) for r in records)
        elif d['suffix'] == 'json':
            row['record_count'] = len(json.loads(decoded))
        elif d['suffix'] == 'zip':
            archive = zipfile.ZipFile(io.BytesIO(raw))
            row['archive_members'] = archive.namelist()
            row['csv_counts'] = {}
            for name in archive.namelist():
                if name.endswith('.csv') and not name.startswith('__MACOSX/'):
                    content = archive.read(name).decode('utf-8-sig')
                    dialect = csv.Sniffer().sniff(content[:8192], delimiters=',;\t')
                    reader = csv.DictReader(io.StringIO(content), dialect=dialect)
                    row['csv_counts'][name] = sum(1 for _ in reader)
        if row['record_count'] is not None and d.get('record_count') is not None:
            row['record_count_matches'] = row['record_count'] == d['record_count']
        results.append(row)
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'manifest_sha256': digest(manifest_bytes), 'datasets': results}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    failures = [r['dataset_id'] for r in results if any(
        r.get(key) is False for key in ['hash_matches', 'compressed_hash_matches', 'record_count_matches'])]
    print(json.dumps({'files_checked': sum(r['check_scope'] == 'BYTES_AND_PARSING_NOT_CLAIM_TRUTH' for r in results),
                      'without_raw': sum(r['check_scope'] == 'NO_RAW_NOT_CHECKED' for r in results), 'failures': failures,
                      'counts': {r['dataset_id']: r.get('csv_counts', r['record_count']) for r in results}}, ensure_ascii=False))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
