#!/usr/bin/env python3
"""Verify MR08 hashes, CSV shape, acceptance boundaries and write scope.

--refresh-manifest is an explicit packaging action, never part of verification.
The output manifest excludes itself; exact delivery commit is named externally
or in a subsequent receipt, avoiding a self-referential commit/hash promise.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
SCOPE = 'context/23_night_run_20261110/common_comparison_review/'
BASE = 'f1774e1f66a9483fb618ca6003abd9dc4d8563e1'


def digest(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-manifest',action='store_true')
    args=parser.parse_args()
    manifest_path=ROOT/'output_manifest.json'
    if args.refresh_manifest:
        entries=[]
        for path in sorted(ROOT.rglob('*')):
            if path.is_file() and path!=manifest_path:
                data=path.read_bytes()
                entries.append(dict(path=str(path.relative_to(ROOT)),bytes=len(data),sha256=digest(data)))
        manifest_path.write_text(json.dumps(dict(review_id='MR08',scope=SCOPE,files=entries,
            self_exclusion='output_manifest.json only',hash_acceptance='Byte identity only; see report and handoff for review acceptance'),ensure_ascii=False,indent=2)+'\n')
    manifest=json.loads(manifest_path.read_text())
    for r in manifest['files']:
        data=(ROOT/r['path']).read_bytes()
        assert digest(data)==r['sha256'] and len(data)==r['bytes'],r['path']
        if r['path'].endswith('.csv'):
            cells=list(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
            assert cells and all(len(row)==len(cells[0]) for row in cells),r['path']
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p!=manifest_path}
    assert actual=={r['path'] for r in manifest['files']},'unlisted files'
    sources=json.loads((ROOT/'source_manifest.json').read_text())['entries']
    for r in sources:
        data=subprocess.check_output(['git','show',r['commit']+':'+r['path']])
        assert digest(data)==r['sha256'] and len(data)==r['bytes'],r['path']
        assert r['grain'],r['path']
        if 'rows' in r:assert len(list(csv.DictReader(io.StringIO(data.decode('utf-8-sig')))))==r['rows'],r['path']
    results=json.loads((ROOT/'independent_results.json').read_text())
    assert results['status']=='PASS_SCOPED_INDEPENDENT_NUMERICS'
    assert results['source_lineage_acceptance']=='HOLD_PRESERVED'
    assert not results['author_numerical_code_executed']
    hold=json.loads((ROOT/'source_hold.json').read_text())
    assert hold['status']=='HOLD' and not hold['coordinator_derivative_reviewed']
    findings=json.loads((ROOT/'findings.json').read_text())
    assert findings['new_P1_P2']==[] and findings['source_supported']=='HOLD'
    changed=subprocess.check_output(['git','diff','--name-only',BASE],text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
    assert all(p.startswith(SCOPE) for p in changed+untracked),changed+untracked
    print(json.dumps(dict(status='PASS',output_hashes=len(manifest['files']),source_hashes=len(sources),
        CSV_shapes='PASS',only_own_scope=True,source_hold_preserved=True,acceptance='PACKAGING_ONLY_NOT_EXTRA_SOURCE_OR_MARKET_ACCEPTANCE'),indent=2))


if __name__=='__main__':main()
