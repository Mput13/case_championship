#!/usr/bin/env python3
"""Freeze role handoffs and check their bytes; no market-truth acceptance."""
import csv
import gzip
import hashlib
import io
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'context/16_agent_research'
FILES = ['dataset_manifest.json', 'source_registry.csv', 'coverage.csv', 'progress.md',
         'findings.md', 'findings.csv', 'integration_plan.md', 'verification.json',
         'validation.json', 'cross_role_review.md', 'acceptance_gates.json',
         'candidate_schema.json', 'candidates.csv', 'experiments_queue.csv']
SAMPLES = {
    'core': ['normalized/airport_version.csv', 'normalized/airport_timezone_join.csv',
             'normalized/access_alternative.csv.gz',
             'branches/social_economy/normalized/example_join_municipal_2024.csv'],
    'alternative': ['normalized/weather_monthly_2024.csv',
                    'normalized/join_airport_station_mapping.csv',
                    'modules/tourism/normalized/primary_observations.csv.gz',
                    'modules/business/normalized/sibur_sites.csv'],
    'hypotheses': ['candidates.csv', 'existing_hypotheses.csv', 'experiments_queue.csv'],
    'critic': ['findings.csv', 'source_checks.csv'],
}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def git(cwd, *args):
    return subprocess.check_output(['git', '-C', str(cwd), *args], text=True).strip()

def main():
    now = datetime.now(timezone.utc)
    out = BASE / 'coordinator' / now.strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True)
    report = {'captured_at_utc': now.isoformat(), 'scope': 'BYTE_HASH_AND_PARSE_COUNTS_NOT_MARKET_TRUTH', 'roles': []}
    for thread in json.loads((BASE / 'threads.json').read_text()):
        role = thread['role']; wt = Path(thread['worktree'])
        source = wt / 'context/16_agent_research' / role
        dest = out / role; dest.mkdir()
        r = {'role': role, 'source_worktree': str(wt), 'head_sha': git(wt, 'rev-parse', 'HEAD'),
             'branch': git(wt, 'branch', '--show-current'), 'files': [], 'raw_checks': [], 'samples': []}
        for name in FILES:
            f = source / name
            if not f.is_file(): continue
            data = f.read_bytes()
            (dest / name).write_bytes(data)
            r['files'].append({'path': name, 'sha256': sha(data), 'bytes': len(data),
                              'git_status': git(wt, 'status', '--porcelain', '--', str(f)),
                              'stable_after_read': f.read_bytes() == data})
        manifest = json.loads((dest / 'dataset_manifest.json').read_bytes())
        r['manifest_entries'] = len(manifest['datasets'])
        r['acquisition_status_counts'] = dict(Counter(x.get('acquisition_status', 'UNSPECIFIED') for x in manifest['datasets']))
        for d in manifest['datasets']:
            entry = {'dataset_id': d['dataset_id'], 'raw_path': d.get('raw_path'), 'grain': d.get('grain')}
            if not d.get('raw_path'):
                entry['check'] = 'NO_RAW_NOT_CHECKED'
            else:
                p = source / d['raw_path']
                if not p.is_file(): entry['check'] = 'MISSING_LOCAL_FILE'
                else:
                    b = p.read_bytes(); entry['file_sha256'] = sha(b)
                    expected = d.get('stored_sha256') or d.get('compressed_sha256') or d.get('sha256')
                    entry['file_hash_matches'] = sha(b) == expected
                    if b.startswith(b'\x1f\x8b'):
                        dec = gzip.decompress(b)
                        e = d.get('uncompressed_sha256') or (d.get('sha256') if d.get('compressed_sha256') else None)
                        if e: entry['uncompressed_hash_matches'] = sha(dec) == e
                    entry['check'] = 'PASS' if entry['file_hash_matches'] and entry.get('uncompressed_hash_matches', True) else 'HASH_MISMATCH'
            r['raw_checks'].append(entry)
        r['raw_check_counts'] = dict(Counter(x['check'] for x in r['raw_checks']))
        r['unique_raw_paths'] = len(set(x['raw_path'] for x in r['raw_checks'] if x['raw_path']))
        for name in SAMPLES.get(role, []):
            f = source / name
            if not f.is_file(): continue
            b = f.read_bytes(); decoded = gzip.decompress(b) if name.endswith('.gz') else b
            reader = csv.DictReader(io.StringIO(decoded.decode('utf-8-sig')))
            rows = list(reader)
            s = {'path': name, 'sha256': sha(b), 'row_count': len(rows), 'columns': reader.fieldnames,
                 'first_rows': rows[:2], 'stable_after_read': f.read_bytes() == b}
            if name == 'candidates.csv':
                s['selected_for_deepening'] = sum(x.get('selected_for_deepening', '').lower() == 'true' for x in rows)
                s['evaluation_status_counts'] = dict(Counter(x.get('evaluation_status') for x in rows))
            r['samples'].append(s)
        report['roles'].append(r)
    (out / 'checkpoint.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(out), 'roles': [{k:r[k] for k in ['role','head_sha','manifest_entries','raw_check_counts','unique_raw_paths']} for r in report['roles']]}, ensure_ascii=False))

if __name__ == '__main__':
    main()
