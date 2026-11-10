#!/usr/bin/env python3
"""Verify exact input bytes and all review artifacts; optional manifest creation."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=HERE, text=True).strip())
MANIFEST = HERE / 'output_manifest.json'
PIN = 'c24bbd36356f46763eed5a1654573b6de31adc6b'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def grain(path):
    mapping = {
        'independent_portfolios.csv': 'portfolio subset x scenario x frequency law',
        'independent_pair_itineraries.csv': 'pair portfolio x scenario x law x dated offered itinerary',
        'independent_market_pools.csv': 'portfolio x scenario x law x directed final OD',
        'independent_marginals.csv': 'pair x scenario x law x incumbent/addition orientation',
        'portfolio_comparison_checks.csv': 'portfolio x scenario x law conservation/comparison check',
        'independent_calendar_checks.csv': 'program x scenario x dedicated planning label',
        'independent_resources.csv': 'model x candidate x scenario necessary resource envelope',
        'independent_budget_boundaries.csv': 'scenario x unordered program pair symbolic inequality',
        'budget_boundary_sides.csv': 'boundary x threshold offset -1/0/+1 RUB',
        'independent_product_units.csv': 'product x cost-unit scenario x paired return cohort',
        'independent_c07_costs.csv': 'C07 one illustrative rotation x cost scenario',
        'independent_temporal_intervals.csv': 'schedule x half-open consecutive event interval',
        'independent_temporal_conflicts.csv': 'planning label x adjacent shifted physical legs',
    }
    return mapping.get(path.name, 'review document/script/receipt')


def main():
    own = sorted(p for p in HERE.iterdir() if p.is_file() and p.name != MANIFEST.name)
    assert not any(p.is_dir() for p in HERE.iterdir()), 'Unexpected runtime/dependency directory'
    if '--write-manifest' in sys.argv:
        artifacts = []
        for p in own:
            raw = p.read_bytes()
            row = dict(path=p.name, sha256=sha(raw), bytes=len(raw), grain=grain(p))
            if p.suffix == '.csv':
                row['rows'] = len(list(csv.DictReader(raw.decode().splitlines())))
            artifacts.append(row)
        MANIFEST.write_text(json.dumps(dict(review_id='MR09_STRATEGY_ACCOUNTING', input_commit=PIN,
            self_excluded='output_manifest.json only; delivery envelope may be finalized after payload commit',
            artifacts=artifacts), ensure_ascii=False, indent=2) + '\n')
    outputs = json.loads(MANIFEST.read_text())
    assert outputs['input_commit'] == PIN
    expected = {r['path']: r for r in outputs['artifacts']}
    assert set(expected) == {p.name for p in own}, 'Unmanifested or missing review file'
    for p in own:
        raw = p.read_bytes()
        assert sha(raw) == expected[p.name]['sha256'] and len(raw) == expected[p.name]['bytes'], p.name
    source = json.loads((HERE / 'source_manifest.json').read_text())
    for r in source['sources'] + source['review_authority']:
        raw = subprocess.check_output(['git', 'show', r['commit'] + ':' + r['path']], cwd=ROOT)
        assert sha(raw) == r['sha256'] and len(raw) == r['bytes'], r['path']
    checks = json.loads((HERE / 'checks.json').read_text())
    findings = json.loads((HERE / 'findings.json').read_text())
    handoff = json.loads((HERE / 'handoff.json').read_text())
    assert checks['input_commit'] == findings['input_commit'] == handoff['input_commit'] == PIN
    assert all(r['status'] == 'PASS' for r in checks['checks'])
    assert findings['new_actionable_findings'] == [] and handoff['verdict'] == 'APPROVE_SCOPED'
    assert findings['scope_verdicts'][5]['verdict'] == 'CHANGES'
    assert len(findings['inherited_holds']) == 2
    print(json.dumps(dict(status='PASS', review_artifacts=len(own), input_files=len(source['sources']),
                          review_authority_files=len(source['review_authority']), input_commit=PIN)))


if __name__ == '__main__':
    main()
