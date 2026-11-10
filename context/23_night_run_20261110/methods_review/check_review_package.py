#!/usr/bin/env python3
"""Validate MR05 outputs and their immutable source locations; read-only by default."""
import argparse
import ast
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
SCOPE = 'context/23_night_run_20261110/methods_review/'
SOURCE = '344f4425ba3fbb73b45a5cbcd223089e2ca7b5d4'
BASE = 'f39ac0726d5942106189e9dc59bfc09cad92441e'


def read(name):
    return json.loads((ROOT / name).read_text())


def grain(path):
    if path.suffix == '.py':
        return 'reproducible reviewer calculation or package validation code; no author repair'
    return {
        'independent_checks.json': 'one labeled check with actual/expected/unit/scope',
        'findings.json': 'finding x pinned source lines; severity/impact/minimal fix',
        'source_manifest.json': 'pinned Git blob x exact SHA x SHA256 x source grain; control inputs separately',
        'shared_market_checks.csv': 'scenario x repeated unordered model endpoint pair x annual both-direction demand',
        'route_unit_checks.csv': 'author scenario x model endpoint/program/leg-row counts; physical count NULL',
        'tsiri_ledger_checks.csv': 'result network x source profile/network x scenario x week7-13Dec2026',
        'tsiri_itinerary_check.json': 'one directed dated itinerary x constituent physical legs/capacity rows',
        'MOW_OMS_input_check.json': 'frozen annual2025 observed segment-scale input with period/coverage',
        'nastya_balance_checks.json': 'author scenario x summary variant; journey/segment rounding residual',
        'C01_check.json': 'one paired outward/return cohort x illustrative fare/cost/gap threshold',
        'counterexamples.json': 'independent synthetic case x explicit conservation/accounting assumptions',
        'checker_gap_examples.json': 'selected Tsiri result x isolated semantic checker coverage limit',
        'validator_probes.json': 'original or in-memory mutated CSV reader x exact pinned checker result',
        'known_metadata_followup.json': 'one inherited block-method mismatch already assigned MR06',
        'handoff.json': 'bounded MR05 delivery status/ref, findings, acceptance and remaining questions',
        'report.md': 'human-readable independent review, findings and scope limits',
        'reproduce.md': 'reproduction and scoped publication commands',
        'progress.md': 'completed bounded role status',
    }[path.name]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write-manifest', action='store_true')
    args = parser.parse_args()
    handoff = read('handoff.json')
    assert handoff['source_commit'] == SOURCE and handoff['verdict'] == 'CHANGES'
    findings = read('findings.json')
    counts = collections.Counter(r['severity'] for r in findings['findings'])
    assert {s: counts[s] for s in ['P1', 'P2', 'P3']} == findings['counts'] == handoff['counts']
    for f in findings['findings']:
        for field in ['mechanism', 'reproduction', 'impact', 'minimal_fix', 'status']:
            assert f[field], (f['id'], field)
        for ref in f['sources']:
            data = subprocess.check_output(['git', 'show', SOURCE + ':' + ref['path']]).decode()
            assert 1 <= ref['line_start'] <= ref['line_end'] <= len(data.splitlines()), ref
    assert len(read('counterexamples.json')) == 10
    assert len(read('validator_probes.json')['probes']) == 3
    checks = read('independent_checks.json')
    assert checks['source_commit'] == SOURCE and len(checks['checks']) == 23
    assert all(r['status'] == 'PASS' for r in checks['checks'])
    source = read('source_manifest.json')
    assert source['source_commit'] == SOURCE and source['upstream_input_count'] == 62
    assert len(source['files']) == 82 and len(source['control_inputs']) == 2
    for ref in source['files'] + source['control_inputs']:
        data = subprocess.check_output(['git', 'show', ref['commit'] + ':' + ref['path']])
        assert hashlib.sha256(data).hexdigest() == ref['sha256'] and len(data) == ref['bytes']
    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name != 'output_manifest.json')
    assert all(not p.is_symlink() and p.suffix in ['.py', '.md', '.json', '.csv'] for p in files)
    assert not any('__pycache__' in p.parts for p in files)
    for name in handoff['required_outputs']:
        assert (ROOT / name).is_file() or (args.write_manifest and name == 'output_manifest.json'), name
    # Publication review for newly produced content only; no source secrets are copied.
    secret_patterns = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                       r'\bgh[pousr]_[A-Za-z0-9]{24,}\b', r'\bAKIA[A-Z0-9]{16}\b',
                       r'(?i)authorization\s*[:=]\s*[\"\x27]?Bearer\s+[A-Za-z0-9_.-]{20,}']
    for p in files:
        data = p.read_text()
        if p.suffix == '.json':
            json.loads(data)
        if p.suffix == '.py':
            ast.parse(data)
        if p.suffix == '.csv':
            with p.open(newline='') as stream:
                rr = list(csv.reader(stream))
            assert rr and all(len(r) == len(rr[0]) for r in rr), p.name
        assert not any(re.search(pattern, data) for pattern in secret_patterns), p.name
    diff = subprocess.check_output(['git', 'diff', '--name-only', BASE]).decode().splitlines()
    assert all(p.startswith(SCOPE) for p in diff), diff
    status = subprocess.check_output(['git', 'status', '--porcelain=v1', '-z']).decode().split('\0')
    assert all(not entry or entry[3:].startswith(SCOPE) for entry in status), status
    records = [dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                    bytes=p.stat().st_size, grain=grain(p)) for p in files]
    manifest = dict(package='MR05-independent-review-v1', source_commit=SOURCE,
                    verdict='CHANGES', self_exclusion='output_manifest.json', files=records)
    if args.write_manifest:
        (ROOT / 'output_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    else:
        assert read('output_manifest.json') == manifest, 'output manifest drift'
    print(json.dumps(dict(status='PASS_SCOPED_PACKAGE', files=len(files), findings=len(findings['findings']),
                          numeric_checks=len(checks['checks']), source_blobs=82, control_inputs=2,
                          scope_only=True, publication_content_scan='PASS', empirical_acceptance=False)))


if __name__ == '__main__':
    main()
