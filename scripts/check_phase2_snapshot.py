#!/usr/bin/env python3
"""Capture pinned Phase2 handoffs and verify bytes; no market acceptance."""
import csv
import hashlib
import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'context/16_agent_research'
PINS = {
    'core': ('505e24663e5952bae9b9540bb9a5a622663bfc2a', 'integration_v1'),
    'alternative': ('ef365ac2a936117e5b3bb12ea99c816d7b1a101c', 'product_probe_v1'),
    'hypotheses': ('6ed8788882e7b4d07044b4f6e686ff71eadd8ac5', 'experiment_v1'),
    'critic': ('1210b476d118dfffe52499d7cc63690e9ec7cf32', 'integration_v1'),
}
EXTRA = {
    'core': ['findings.md', 'progress.md', 'phase2_handoff.md', 'phase2_handoff_manifest.json',
             'operating/coverage.csv', 'operating/market_observation_v1.csv',
             'operating/omsk_departure_overlay.csv', 'operating/quarantine.csv',
             'social/coverage.csv', 'social/findings.md', 'social/table_dictionary.csv'],
    'alternative': ['README.md', 'findings.md', 'progress.md', 'table_contract.json',
                    'incremental_test.md', 'normalized/flight_rules_v2.csv',
                    'normalized/conditional_stay_calendars.csv',
                    'normalized/property_reception_evidence.csv',
                    'c10_optional/findings.md', 'c10_optional/verification.json'],
    'hypotheses': ['handoff.json', 'progress.md', 'README.md', 'checks/fresh_replay.json'],
    'critic': ['professional_review.md', 'evaluation_protocol.md', 'findings.csv',
               'source_checks.csv', 'acceptance_gates.json', 'progress.md'],
}

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def digest(b):
    return hashlib.sha256(b).hexdigest()

def main():
    now = datetime.now(timezone.utc)
    out = BASE / 'coordinator' / now.strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True)
    threads = {x['role']: x for x in json.loads((BASE / 'threads.json').read_text())}
    result = {'captured_at_utc': now.isoformat(), 'scope': 'PINNED_BYTES_AND_SELECTED_GRAIN; NOT_MARKET_ACCEPTANCE', 'roles': []}
    for role, (commit, sub) in PINS.items():
        prefix = f'context/16_agent_research/{role}/{sub}/'
        paths = git('ls-tree', '-r', '--name-only', commit, '--', prefix).decode().splitlines()
        available = {x[len(prefix):] for x in paths}
        report = {'role': role, 'commit': commit,
                  'author': git('show', '-s', '--format=%an', commit).decode().strip(),
                  'copied_files': [], 'manifest_checks': [], 'raw_checks': [], 'csv_examples': []}

        def read(rel):
            return git('show', f'{commit}:{prefix}{rel}')

        def capture(rel):
            b = read(rel)
            dest = out / role / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b)
            report['copied_files'].append({'path': rel, 'sha256': digest(b), 'bytes': len(b)})
            if rel.endswith('.csv'):
                reader = csv.DictReader(io.StringIO(b.decode('utf-8-sig')))
                rows = list(reader)
                report['csv_examples'].append({'path': rel, 'rows': len(rows), 'columns': reader.fieldnames,
                                               'first_two_rows': rows[:2], 'interpretation': 'PARSED; row count is not demand'})
            return b

        names = [x for x in EXTRA[role] if x in available]
        if role == 'hypotheses':
            handoff = json.loads(read('handoff.json'))
            manifests = list(handoff['current_outputs'].values())
        elif role == 'core':
            manifests = ['operating/output_manifest.json', 'c14_addendum_v1/output_manifest.json']
            manifests += [x for x in available if x.startswith('c07_reconciliation_v1/') and x.endswith('manifest.json')]
        elif role == 'alternative':
            manifests = ['dataset_manifest.json', 'flight_checkpoint_manifest.json']
        else:
            manifests = []
            names += [x for x in available if x.startswith('reviews/') and x.endswith(('review.md', 'reproduction.json'))]
        for rel in dict.fromkeys(names):
            capture(rel)
        for rel in dict.fromkeys(manifests):
            m = json.loads(capture(rel))
            for entry in m.get('public_files', m.get('files', [])):
                candidates = {entry['path'], str(Path(rel).parent / entry['path'])} & available
                if len(candidates) != 1:
                    raise ValueError(f'Ambiguous or missing manifest path {role}/{rel}: {entry["path"]}')
                target = candidates.pop()
                b = read(target)
                ok = digest(b) == entry['sha256']
                report['manifest_checks'].append({'manifest': rel, 'path': target, 'sha256': digest(b), 'match': ok})
                if not ok:
                    raise ValueError(f'Hash mismatch {role}/{target}')
                if role in ('hypotheses', 'core') and target.endswith('.csv'):
                    capture(target)
            # Raw checks here deliberately cover root sources only. Module raw is
            # reviewed by critic separately and is not claimed as repeated here.
            raw_entries = m.get('root_sources', [])
            if isinstance(m.get('primary_raw'), dict):
                raw_entries += [m['primary_raw']]
            for entry in raw_entries:
                rp = entry.get('raw_path') or entry.get('path')
                if not rp:
                    continue
                local = Path(threads[role]['worktree']) / prefix / Path(rel).parent / rp
                expected = entry.get('stored_sha256') or entry.get('sha256')
                b = local.read_bytes() if local.is_file() else None
                report['raw_checks'].append({'path': rp, 'expected_sha256': expected,
                                             'stored_sha256': digest(b) if b is not None else None,
                                             'source_status': entry.get('source_status'),
                                             'status': ('ACCESS_FAILED_NO_RAW_NOT_CHECKED'
                                                        if entry.get('source_status') == 'ACCESS_FAILED' and expected is None and b is None
                                                        else 'PASS_STORED_BYTES' if b is not None and digest(b) == expected
                                                        else 'MISSING_OR_DIFFERENT')})
        result['roles'].append(report)
    (out / 'checkpoint.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'path': str(out), 'roles': [
        {'role': r['role'], 'sha': r['commit'], 'manifest_files_checked': len(r['manifest_checks']),
         'selected_raw_checked': len(r['raw_checks']), 'raw_nonpass': [x for x in r['raw_checks'] if x['status'] != 'PASS_STORED_BYTES']}
        for r in result['roles']]}, ensure_ascii=False))

if __name__ == '__main__':
    main()
