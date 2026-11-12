"""Закрепление запечатанных городских входов; запись только внутри P09."""
from pathlib import Path
import csv, hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO = ROOT.parents[2]
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')
def digest(x): return sha(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
def write_csv(p, rows):
    if not rows: return
    with p.open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def capture():
    intake=json.loads((BASE/'P00/sealed_intake.json').read_text())
    expected={x['path'].rstrip('/'):x['manifest_sha256'] for x in intake['packages']}
    expected['context/35_full_programme_execution_20261112/P08/SVX/research_v1']='db88e7c0ab962662afc962931d4184d4d836b866c6b1cc93ee607e32b241bce2'
    candidates=sorted((BASE/'variants').glob('*/research_v1'))+[BASE/'P08/SVX/research_v1',BASE/'P08/MOSCOW/research_v1',BASE/'P11',BASE/'P02I']
    receipts=[]
    for p in candidates:
        rel=p.relative_to(REPO).as_posix()
        ms=[p/n for n in ['manifest.json','output_manifest.json'] if (p/n).exists()]
        if not ms:
            receipts.append(dict(path=rel,status='OPEN_NO_SEALED_MANIFEST'));continue
        mf=ms[0]; raw=mf.read_bytes(); h=sha(raw)
        if rel in expected and h!=expected[rel]:
            receipts.append(dict(path=rel,status='OPEN_CHANGED_MANIFEST',expected=expected[rel],actual=h));continue
        j=json.loads(raw); entries=j.get('files',j.get('artifacts',[]))
        if isinstance(entries,dict): entries=[dict(v,path=k) if isinstance(v,dict) else dict(path=k,sha256=v) for k,v in entries.items()]
        copied=[]; errors=[]
        for e in entries:
            name=e.get('path', e.get('relative_path',''))
            f=p/name
            if not f.exists() and (REPO/name).exists(): f=REPO/name
            if not f.exists() or not f.resolve().is_relative_to(p.resolve()):
                errors.append(name+':missing_or_outside');continue
            dat=f.read_bytes()
            if sha(dat)!=e['sha256']: errors.append(name+':hash_mismatch');continue
            # Only structured producer results; never copy archived inputs, PDFs or full fixtures.
            n=f.relative_to(p)
            selected=(len(n.parts)==1 and (n.suffix=='.json' and any(x in n.name.lower() for x in ['programme','hypoth','case','handoff','readiness','contract','digital','access','international']) or n.suffix=='.csv' and any(x in n.name.lower() for x in ['assumption','cost','eligibility','market_delta','source','evidence','direct_candidate'])))
            if selected:
                dest=ROOT/'sealed'/p.relative_to(BASE)/n
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(dat)
                copied.append(dict(path=n.as_posix(),sha256=sha(dat),bytes=len(dat)))
        if mf.read_bytes()!=raw: errors.append('manifest_changed_during_capture')
        dest=ROOT/'sealed'/p.relative_to(BASE)/mf.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        receipts.append(dict(path=rel,manifest_sha256=h,status='REJECT_HASH_ERROR' if errors else 'HASHES_VERIFIED',coordinator_scope_accepted=rel in expected,errors=errors,files_verified=len(entries),selected_files=copied))
    dump(ROOT/'sealed_intake_snapshot.json', intake)
    dump(ROOT/'city_input_receipts.json',receipts)
    rev='b4d2ddf690440eb5cd051839cc263cf16b364ca4'
    for name in ['variant_research_plan.json','common_spec.json','requirements.csv']:
        src='context/34_full_programme_plan_20261112/'+name
        data=subprocess.check_output(['git','show',rev+':'+src],cwd=REPO)
        p=ROOT/'subject/PLAN'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    return receipts

def records(obj, names):
    if isinstance(obj,list):return obj
    for k in names:
        if k in obj:
            x=obj[k]
            if isinstance(x,list): return x
            if isinstance(x,dict):return [dict(v,programme_id=v.get('programme_id',k2)) for k2,v in x.items() if isinstance(v,dict)]
    return []

def normalize(receipts):
    programmes=[]; hypotheses=[]
    for receipt in receipts:
        if receipt['status']!='HASHES_VERIFIED':continue
        p=ROOT/'sealed'/Path(receipt['path']).relative_to(BASE.relative_to(REPO))
        city=p.parent.name if p.name=='research_v1' else p.name
        for name,types,target in [('programme_candidates.json',['programmes','candidates'],programmes),('hypotheses.json',['hypotheses','items'],hypotheses)]:
            f=p/name
            if not f.exists():continue
            j=json.loads(f.read_text())
            for i,r in enumerate(records(j,types)):
                if not isinstance(r,dict):continue
                ident=r.get('programme_id',r.get('hypothesis_id',r.get('id',f'{city}:row{i+1}')))
                target.append(dict(id=ident,city=city,source_path=receipt['path']+'/'+name,source_file_sha256=sha(f.read_bytes()),source_row_id=ident,source_row_index=i,source_row_sha256=digest(r),manifest_sha256=receipt['manifest_sha256'],coordinator_scope_accepted=receipt['coordinator_scope_accepted'],raw=r))
    dump(ROOT/'normalized_candidates.json',programmes)
    dump(ROOT/'normalized_hypotheses.json',hypotheses)
    plan=json.loads((ROOT/'subject/PLAN/variant_research_plan.json').read_text())
    dump(ROOT/'legacy_hypotheses.json',plan['legacy_hypotheses'])
    print(json.dumps(dict(packages=len(receipts),verified=sum(r['status']=='HASHES_VERIFIED' for r in receipts),programmes=len(programmes),hypotheses=len(hypotheses),legacy=len(plan['legacy_hypotheses'])),ensure_ascii=False))

if __name__=='__main__': normalize(capture())
