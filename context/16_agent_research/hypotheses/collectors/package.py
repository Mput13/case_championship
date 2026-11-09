#!/usr/bin/env python3
"""Build one portable index without modifying original source snapshots."""
from pathlib import Path
from datetime import datetime,timezone
import csv,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ignored(p):return subprocess.run(['git','check-ignore','--no-index','-q',str(p)]).returncode==0
def write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    ds=[]
    for filename,base in [('inputs/capture_manifest.json',''),('contributions/source_access/dataset_manifest_public.json','contributions/source_access'),('contributions/existing_map/dataset_manifest.json','contributions/existing_map'),('contributions/existing_map/review_source_manifest.json','contributions/existing_map'),('inputs/peer_status_manifest.json',''),('inputs/late_update_manifest.json','')]:
        for r0 in json.load((ROOT/filename).open())['datasets']:
            r=dict(r0);r['upstream_manifest']=filename
            for key in ['raw_path','text_path','derived_path']:
                if r.get(key):r[key]=str(Path(base)/r[key]) if base else r[key]
            r['size_bytes']=r.get('size_bytes',r.get('byte_size',r.get('bytes')))
            r['organisation']=r.get('organisation',r.get('organization','UNKNOWN'))
            r.setdefault('publication_date',r.get('published_at','UNKNOWN'))
            r.setdefault('units','per source file; UNKNOWN if absent')
            r.setdefault('key_fields',r.get('join_keys','UNKNOWN'))
            if r.get('raw_path'):
                assert sha(ROOT/r['raw_path'])==r['sha256'],r['raw_path']
            r['admission_status']='SOURCE_SCOPE_ONLY'
            r['publication_status']='LOCAL_RAW_ONLY' if r.get('raw_path') and ignored(ROOT/r['raw_path']) else 'PUBLISHED_RESEARCH_ARTIFACT'
            if r['dataset_id'] in ['GIT-front-fetch_telegram.py','GIT-front-_manifest.json'] or 'favt_posts' in r.get('source_path',''):
                r['admission_status']='PARSER_CONTAMINATION_HOLD_FOR_EVENT_USE'
                r['limitations']+='; old Telegram extraction cannot support event counts; see critic review snapshot'
            ds.append(r)
    g=json.load((ROOT/'inputs/geometry_manifest.json').open());g['admission_status']='COORDINATES_ONLY';ds.append(g)
    ids=[r['dataset_id'] for r in ds];assert len(ids)==len(set(ids))
    manifest=dict(schema_version='hypotheses-manifest-v1',path_base='.',generated_at_utc=datetime.now(timezone.utc).isoformat(),status='RESEARCH_QUEUE_WITH_PARTIAL_CHECKS',datasets=ds,full_economics='NOT_EVALUATED',limitations='Source integrity and card validity are not market, operational or launch acceptance')
    (ROOT/'dataset_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    cols=['dataset_id','source_url','organisation','publication_date','retrieved_at_utc','grain','geographic_coverage','temporal_coverage','record_count','units','acquisition_status','admission_status','raw_path','sha256','size_bytes','license','limitations','upstream_manifest']
    write(ROOT/'source_registry.csv',[{k:r.get(k,'') for k in cols} for r in ds])
    rejected=[dict(item_id='HYP-S01',status='ACCESS_FAILED',reason='OurAirports country endpoint certificate expired: CERTIFICATE_VERIFY_FAILED',scope='Only this URL path; upstream public mirror successfully acquired as HYP-S03',next_step='Use preserved mirror bytes; no TLS bypass'),dict(item_id='WEB-CASE',status='TOOL_ACCESS_FAILED',reason='Two web.open calls: URL https://mai-way.ru/tasks/red-wings/ is not accessible via this tool.',scope='Native fetch path; plain public HTTP200, cause UNKNOWN',next_step='Preserved SA00 raw and diagnostic, no restart'),dict(item_id='FRONT-TELEGRAM',status='HOLD',reason='PARSER_CONTAMINATION: reply preview selected as main body',scope='Old event/restriction/news extraction, not unrelated sources',next_step='Full historical reparse and airport-level event audit; NOT_RUN here'),dict(item_id='OD-NETFARE-FLEET',status='UNKNOWN',reason='No comparable observed OD, net realised fare or confirmed free fleet for the 35 proposals',scope='Economics/launch remains NOT_EVALUATED; no zero imputation',next_step='D08/D09/D12 and dated programs before common evaluator')]
    write(ROOT/'rejected_or_unavailable.csv',rejected)
    inventory=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.name in ['artifact_manifest.json','validation.json']:continue
        inventory.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),size_bytes=p.stat().st_size,git_policy='LOCAL_IGNORED_RAW' if ignored(p) else 'REVIEWABLE_ARTIFACT'))
    (ROOT/'artifact_manifest.json').write_text(json.dumps({'path_base':'.','files':inventory},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'sources':len(ds),'artifacts':len(inventory),'source_hashes':'PASS'}))
if __name__=='__main__':main()
