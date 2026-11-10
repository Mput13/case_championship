#!/usr/bin/env python3
"""Hash, shape, exact-source and permitted-scope checks for this review only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import oracle as o


def inventory():
    return [p for p in sorted(o.OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
            and '.scratch' not in p.parts and p.name!='output_manifest.json']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write-manifest',action='store_true');args=parser.parse_args()
    required=['report.md','findings.json','handoff.json','source_manifest.json','oracle.py','probes.py','checks.json','reproduce.md','progress.md']
    for name in required:assert (o.OUT/name).is_file(),name
    assert not (o.OUT/'.scratch').exists(),'temporary runtime must be cleaned'
    sources=json.loads((o.OUT/'source_manifest.json').read_text())['sources']
    assert len({(x['commit'],x['path']) for x in sources})==len(sources)
    for r in sources:
        b=subprocess.check_output(['git','show',r['commit']+':'+r['path']],cwd=o.REPO)
        assert hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes'],r['path']
        assert r['grain'] and len(r['commit'])==40
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob_sha1']
    files=inventory()
    for p in files:
        b=p.read_bytes()
        if p.suffix=='.json':json.loads(b)
        if p.suffix=='.csv':
            with p.open(newline='') as f:
                reader=csv.reader(f);header=next(reader)
                for i,row in enumerate(reader,2):assert len(row)==len(header),(p,i)
        assert not any(token in b for token in [b'-----BEGIN '+b'PRIVATE KEY-----',b'-----BEGIN '+b'OPENSSH PRIVATE KEY-----',b'Authorization: '+b'Bearer ']),p
    records=[dict(path=str(p.relative_to(o.OUT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                  grain=o.grain_for(str(p.relative_to(o.OUT)))) for p in files]
    if args.write_manifest:
        o.save('output_manifest.json',dict(package='MR11_INDEPENDENT_INTEGRATION_REVIEW',subject=o.SUBJECT,
            acceptance='PACKAGING_SELF_CHECK_ONLY; independent arithmetic separately in report/checks',
            self_hash_excluded='output_manifest.json',files=records))
    else:
        saved=json.loads((o.OUT/'output_manifest.json').read_text())
        assert saved['files']==records,'output file set, shape, size or hash drift'
    rel=str(o.OUT.relative_to(o.REPO))+'/'
    changed=subprocess.check_output(['git','diff','--name-only',o.ROOT],cwd=o.REPO,text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=o.REPO,text=True).splitlines()
    assert all(p.startswith(rel) for p in changed+untracked),('write scope',changed,untracked)
    subprocess.check_call(['git','diff','--check'],cwd=o.REPO)
    c=json.loads((o.OUT/'checks.json').read_text());p=json.loads((o.OUT/'adversarial_probes.json').read_text())
    assert [c[k] for k in ['cancellation_cases','adapter_rows','held_delays','adapter_cancellation_ledgers','cash_ledgers','portfolio_rows','D_guard_cases','prior_portfolio_cases']]==[16,40,4,12,8,90,30,60]
    assert p['count']==len(p['probes'])==17
    assert json.loads((o.OUT/'findings.json').read_text())['new_P1_P2']==[]
    assert json.loads((o.OUT/'handoff.json').read_text())['verdict']=='APPROVE_SCOPED'
    print(json.dumps(dict(status='PASS_PACKAGE',source_hashes=len(sources),output_hashes=len(records),csv_json_shapes='PASS',own_scope_only=True,temporary_runtime_absent=True)))


if __name__=='__main__':main()
