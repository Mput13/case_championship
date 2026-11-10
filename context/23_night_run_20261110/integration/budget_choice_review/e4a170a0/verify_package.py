#!/usr/bin/env python3
"""Read-only review-package verification; no resealing."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
SCOPE=ROOT.relative_to(REPO).as_posix()+'/'
manifest=json.loads((ROOT/'output_manifest.json').read_text())
expected={r['path']for r in manifest['files']}
actual={p.relative_to(ROOT).as_posix()for p in ROOT.rglob('*')if p.is_file()and p.name!='output_manifest.json'}
assert expected==actual,('file set',expected^actual)
for r in manifest['files']:
    b=(ROOT/r['path']).read_bytes()
    assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
checks=json.loads((ROOT/'checks.json').read_text())
assert checks['status']=='PASS'and checks['personal_checks_passed']==len(checks['checks'])
assert all(x['status']=='PASS'for x in checks['checks'])
expected_counts={'independent_candidates.csv':90,'independent_pairwise_inequalities.csv':408,
                 'independent_dominance_certificates.csv':51,'independent_witness_slacks.csv':201,
                 'independent_constraint_terms.csv':18,'independent_constraint_floors.csv':6,
                 'independent_projection.csv':58,'independent_byte_preservation.csv':381,
                 'independent_determinism.csv':13}
for n,count in expected_counts.items():
    with(ROOT/n).open(newline='')as f:assert len(list(csv.DictReader(f)))==count,n
findings=json.loads((ROOT/'findings.json').read_text())
handoff=json.loads((ROOT/'handoff.json').read_text())
assert findings['verdict']==handoff['verdict']=='APPROVE_SCOPED'
assert findings['new_P1_P2']==0 and not findings['blocking_findings']
assert handoff['personal_checks_passed']==checks['personal_checks_passed']
branch=subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip()
assert branch=='research/night-budget-choice-review-20261110',branch
changed=subprocess.check_output(['git','diff','--name-only','b20d4346b6aede514dbed59112bcf878232819c8','--'],cwd=REPO,text=True).splitlines()
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=REPO,text=True).splitlines()
assert all(p.startswith(SCOPE)for p in changed+untracked),('out-of-scope files',changed+untracked)
assert not(ROOT/'_runtime').exists()
print(json.dumps(dict(status='PASS',sealed_files=len(expected),personal_assertions=checks['personal_checks_passed'],
                      branch=branch,write_scope_verified=True,runtime_absent=True)))
