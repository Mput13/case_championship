#!/usr/bin/env python3
"""Seal/check the MR07 directory, excluding only this manifest's own bytes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--write-manifest', action='store_true')
args = parser.parse_args()

required = ['report.md','findings.json','independent_review.py','source_manifest.json',
            'checks.json','handoff.json','progress.md','independent_lp.json',
            'independent_bounds.csv','independent_inequalities.csv','independent_thresholds.csv',
            'independent_pairwise.csv','independent_accounting.json','counterexamples.json']
for name in required:
    assert (ROOT/name).is_file(), name
findings = json.loads((ROOT/'findings.json').read_text())
checks = json.loads((ROOT/'checks.json').read_text())
handoff = json.loads((ROOT/'handoff.json').read_text())
assert findings['verdict'] == handoff['verdict'] == 'APPROVE_SCOPED'
assert not findings['confirmed_P1_P2_defects']
assert checks['status'] == 'PASS_SCOPED'
assert (checks['network_scenarios'],checks['dual_inequalities'],checks['threshold_rows'],checks['pairwise_rows']) == (8,224,24,12)
assert handoff['reviewed_commit'] == findings['source_commit'] == '2a74b05179d3619c03fdab3b038fbe7587d85eca'
assert handoff['subagents_used'] is False and handoff['author_code_executed'] is False
for name,expected in [('independent_bounds.csv',8),('independent_inequalities.csv',224),
                      ('independent_thresholds.csv',24),('independent_pairwise.csv',12),
                      ('independent_shadow_prices.csv',160),('independent_local_solution.csv',160)]:
    with (ROOT/name).open(newline='') as f:
        assert len(list(csv.DictReader(f))) == expected, name
entries = []
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.name == 'output_manifest.json':
        continue
    assert not p.is_symlink() and '__pycache__' not in p.parts
    raw = p.read_bytes()
    kind = ('review/source/output receipt' if p.suffix == '.json' else
            'independent numerical rows; see header and report for grain' if p.suffix == '.csv' else
            'review report or progress' if p.suffix == '.md' else
            'reproducible independent calculation/package validation code')
    entries.append(dict(path=str(p.relative_to(ROOT)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),grain=kind))
manifest = dict(review_id='MR07',reviewed_commit=handoff['reviewed_commit'],
    excludes=['output_manifest.json: manifest cannot hash itself'],files=entries)
target = ROOT/'output_manifest.json'
if args.write_manifest:
    target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
else:
    assert json.loads(target.read_text()) == manifest, 'Package hash mismatch: inspect the change before resealing'
print(json.dumps(dict(status='PASS_SCOPED',files=len(entries),bytes=sum(r['bytes'] for r in entries),
    numeric_checks=checks['checks'],verdict=findings['verdict'],mode='seal' if args.write_manifest else 'verify')))
