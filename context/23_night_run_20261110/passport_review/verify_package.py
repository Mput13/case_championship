#!/usr/bin/env python3
"""Read-only package check by default; --write-manifest freezes own output bytes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
SCOPE='context/23_night_run_20261110/passport_review/'
SUBJECT='46fd52db073cffc46a598f44489d0761c6853410'


def js(name):return json.loads((ROOT/name).read_text())
def rows(name):
    with (ROOT/name).open(newline='') as f:return list(csv.DictReader(f))


def main():
    p=argparse.ArgumentParser();p.add_argument('--write-manifest',action='store_true');a=p.parse_args()
    assert js('checks.json')['status']=='PASS'
    assert not [x for x in js('checks.json')['checks'] if x['status']!='PASS']
    assert js('findings.json')['subject_commit']==SUBJECT
    assert js('findings.json')['verdict']=='APPROVE_SCOPED'
    assert js('findings.json')['findings']==[]
    assert js('handoff.json')['subject_commit']==SUBJECT
    for f,k,n in [('requirement_checks.csv','requirement_id',26),('claim_checks.csv','claim_id',33),('competitor_checks.csv','example_id',28),('decision_checks.csv','decision_id',11),('current_qualification_addendum.csv','addendum_id',8)]:
        rr=rows(f);assert len(rr)==n,(f,len(rr));assert len({r[k] for r in rr})==n,f
    for f in ['requirement_checks.csv','claim_checks.csv','decision_checks.csv']:
        assert all(r.get('verdict',r.get('wording_and_transfer_verdict'))=='APPROVE_SCOPED' for r in rows(f)),f
    assert all(r['identity_count_dates'].startswith('PASS') for r in rows('competitor_checks.csv'))
    assert all(r['minimal_owner_fix']=='NONE' for r in rows('claim_checks.csv'))
    assert js('handoff.json')['counts']['checks']==len(js('checks.json')['checks'])
    assert js('official_receipt.json')['raw_published'] is False
    assert js('official_receipt.json')['full_text_published'] is False
    assert all(r['bytes_match'] and r['sha256_match'] for r in js('subject_manifest_verification.json'))
    assert all(r['bytes_match'] and r['sha256_match'] for r in js('upstream_manifest_verification.json'))
    assert all(x['receipt_registry_match'] and x['raw_body_availability'].endswith('NOT_READ') for x in js('receipt_sample.json'))
    for r in js('source_manifest.json')['sources']:
        assert len(r['commit'])==40 and r['exact_ref']==r['commit']+':'+r['path']
    for f in ROOT.rglob('*'):
        assert not f.is_symlink(),f
        assert f.name not in ['__pycache__','node_modules','.venv','raw'],f
    paths=[f for f in sorted(ROOT.rglob('*')) if f.is_file() and f.name!='output_manifest.json']
    entries=[dict(path=str(f.relative_to(ROOT)),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in paths]
    if a.write_manifest:
        (ROOT/'output_manifest.json').write_text(json.dumps(dict(package_id='passport-review-20261110-v1',algorithm='SHA256',exclusions=['output_manifest.json: self reference'],files=entries),ensure_ascii=False,indent=2)+'\n')
    else:assert entries==js('output_manifest.json')['files'],'Output bytes changed; inspect changes before updating the manifest.'
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='research/night-passport-review-20261110',branch
    # Include untracked scope; git diff alone would miss this entire new package.
    changed=set(subprocess.check_output(['git','diff','--name-only','b20d4346b6aede514dbed59112bcf878232819c8'],text=True).splitlines())
    changed.update(subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines())
    assert all(p.startswith(SCOPE) for p in changed),sorted(changed)
    total=sum(x['bytes'] for x in entries)
    print(json.dumps(dict(status='PASS',files=len(entries),bytes=total,requirements=26,claims=33,competitor_examples=28,decisions=11,own_checks=len(js('checks.json')['checks']),scope_only=True)))


if __name__=='__main__':main()
