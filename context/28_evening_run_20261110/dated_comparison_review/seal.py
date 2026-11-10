"""Create/verify a digest manifest for the review evidence, excluding runtime."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PREFIX='context/28_evening_run_20261110/dated_comparison_review/'
SUBJECT='f99d6cd52dcc06995bf984fddd2f057226243b06'

def rows():
    out=[]
    for p in sorted(HERE.rglob('*')):
        rel=p.relative_to(HERE)
        if not p.is_file() or any(x in rel.parts for x in ('_runtime','__pycache__')) or p.name=='output_manifest.json':continue
        data=p.read_bytes();out.append(dict(path=str(rel),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    assert not (HERE/'_runtime').exists(),'Remove disposable runtime before sealing'
    for p in HERE.glob('*.py'):compile(p.read_text(),str(p),'exec')
    for p in HERE.glob('*.json'):json.loads(p.read_text())
    f=json.loads((HERE/'findings.json').read_text());h=json.loads((HERE/'handoff.json').read_text());i=json.loads((HERE/'independent_results_all.json').read_text());a=json.loads((HERE/'adversarial_results.json').read_text());o=json.loads((HERE/'owner_replay_results.json').read_text())
    assert f['subject_commit']==h['subject_commit']==i['subject']==a['subject']==o['subject']==SUBJECT
    assert f['verdict']==h['verdict']=='APPROVE_SCOPED' and f['findings']==[]
    assert h['adversarial_cases']==a['count']==32 and h['rejected_oracle_mutations']==a['rejected_mutations']==16
    assert i['status']==a['status']==o['status']=='PASS'
    assert json.loads((HERE/'cleanup_results.json').read_text())['removed']
    for link in re.findall(r'\]\(([^)]+)\)',(HERE/'report.md').read_text()):
        assert (HERE/link).is_file(),link
    for c in f['held_claims']:
        loc=c['location'];text=subprocess.check_output(['git','show',SUBJECT+':'+loc['path']],text=True)
        assert 1<=loc['line']<=len(text.splitlines())
    actual=rows()
    if args.verify:
        expected=json.loads((HERE/'output_manifest.json').read_text());assert expected['files']==actual
    else:
        (HERE/'output_manifest.json').write_text(json.dumps(dict(subject_commit=SUBJECT,verdict='APPROVE_SCOPED',scope=PREFIX,excludes=['output_manifest.json','_runtime/','__pycache__/'],files=actual),indent=2)+'\n')
    print(json.dumps(dict(status='PASS',subject=SUBJECT,files=len(actual),bytes=sum(r['bytes'] for r in actual),runtime_absent=True)))

if __name__=='__main__':main()
