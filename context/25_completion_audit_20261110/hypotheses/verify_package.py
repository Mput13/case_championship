"""Validate the finite audit deliverables, citations and write boundary; seal hashes."""
from collections import Counter
import csv
import hashlib
import json
import subprocess

from source_access import OUT, REPO, PINS, dump


def read_csv(name):
    with (OUT/name).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))


def verify_evidence(e):
    p=OUT/e['local_path']
    assert p.is_file(),e
    lines=p.read_text(encoding='utf-8-sig').splitlines()
    assert 1<=e['line']<=e['line_end']<=len(lines),e
    expected=subprocess.check_output(['git','show',e['commit']+':'+e['path']],cwd=REPO)
    assert expected==p.read_bytes(),e


def main():
    rows=read_csv('disposition.csv')
    assert len(rows)==35
    assert [r['candidate_id'] for r in rows]==[f'C{i:02d}' for i in range(1,36)]
    assert Counter(r['disposition'] for r in rows)=={'DEFERRED_UNKNOWN_WITH_PARTIAL_TESTS':3,'NOT_EVALUATED_OUR_SCOPE':32}
    for r in rows:
        assert all(value for key,value in r.items()),(r['candidate_id'],'empty required field')
        assert r['documented_early_rejection'].startswith('ABSENT')
        assert r['source_commit']==PINS['hypotheses']
        for ev in json.loads(r['evidence_json']):verify_evidence(ev)
    findings=json.loads((OUT/'findings.json').read_text())
    assert len(findings['findings'])==5
    for f in findings['findings']:
        assert f['minimal_fix'] and f['evidence']
        for ev in f['evidence']:verify_evidence(ev)
    checks=json.loads((OUT/'checks.json').read_text())
    assert all(c['passed'] for c in checks['checks'])
    assert len(read_csv('money_recalculation.csv'))==108
    assert len(read_csv('breakeven_recalculation.csv'))==42
    assert len(read_csv('historical_economics.csv'))==38
    assert len(read_csv('positive_historical_scenarios.csv'))==20
    sources=json.loads((OUT/'source_manifest.json').read_text())
    for s in sources['files']:
        p=OUT/s['local_path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256']
        assert len(p.read_bytes())==s['bytes']
    required=['report.md','disposition.csv','findings.json','handoff.json','source_manifest.json','checks.json']
    assert all((OUT/p).is_file() for p in required)
    # Only audit files may differ from the parent. Untracked paths are checked too.
    prefix=str(OUT.relative_to(REPO))+'/'
    changed=subprocess.check_output(['git','diff','--name-only',PINS['base']],cwd=REPO,text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=REPO,text=True).splitlines()
    assert all(p.startswith(prefix) for p in changed+untracked),changed+untracked
    receipt=dict(status='PASS',rows=35,unique_ids=35,findings=5,
                 source_files=len(sources['files']),personal_check_rows=checks['summary']['passed'],
                 required_outputs_present=True,evidence_paths_and_lines_valid=True,
                 source_hashes_valid=True,write_boundary=prefix,
                 interpreted_acceptance='OFFLINE_AUDIT_ONLY; no live market/operating/full-money acceptance')
    dump('validation_receipt.json',receipt)
    files=[]
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p==OUT/'manifest.json' or '__pycache__' in p.parts:
            continue
        blob=p.read_bytes()
        files.append(dict(path=str(p.relative_to(OUT)),bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()))
    dump('manifest.json',dict(base_parent=PINS['base'],pins=PINS,files=files,
                              verification='verify_package.py; manifest excludes its own hash',
                              package_scope='one finite review; scripts and captured sources only inside assigned folder'))
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    main()
