#!/usr/bin/env python3
"""Offline consolidation and integrity checks. No download and no score/model.

Child manifests stay authoritative for detailed units. All consolidated paths are
relative to core/. Source status is not promoted by hash validation.
"""
import csv
import datetime as dt
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SAFE={'content-type','content-length','last-modified','etag','date','cache-control'}
FIELDS=['dataset_id','source_url','organization','raw_path','sha256','stored_sha256','size_bytes','stored_size_bytes',
 'retrieved_at_utc','publication_date','temporal_coverage','grain','geographic_coverage','key_fields','units',
 'record_count','record_count_unit','acquisition_status','value_status','license','limitations','decision_use',
 'collector_version','command','origin_group','validation_boundary','manifest_path']
def read_json(p):return json.loads(p.read_text())
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csv_write(p,rows,fields):
    with p.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def rows_count(p):
    if p.name.endswith('.csv') or p.name.endswith('.csv.gz'):
        op=gzip.open if p.name.endswith('.gz') else open
        with op(p,'rt',encoding='utf-8-sig',newline='') as h:
            return max(0,sum(1 for _ in csv.reader(h))-1)
    return None
def origin(e):
    u=e.get('source_url','').lower()
    if 'tochno' in u:return 'TOCHNO_REPUBLICATION: inspect original statistical lineage'
    if 't.me/' in u or 'favt.gov.ru' in u:return 'FAVT_OR_CHANNEL_PUBLISHER: not independent across snapshots'
    if 'ourairports' in u:return 'OURAIRPORTS_COMMUNITY'
    if 'travelpayouts' in u:return 'TRAVELPAYOUTS_DIRECTORY'
    return e.get('organization','UNKNOWN')
def standard(e,manifest,prefix=''):
    e=dict(e);e['original_dataset_id']=e.get('dataset_id','UNKNOWN')
    if prefix:e['dataset_id']=prefix.replace('/','__')+'__'+e['original_dataset_id']
    e['source_url']=e.get('source_url',e.get('url','UNKNOWN'))
    e['organization']=e.get('organization',e.get('source_organization','UNKNOWN'))
    if e.get('raw_path') and prefix:e['raw_path']=prefix+'/'+e['raw_path']
    e['publication_date']=e.get('publication_date',e.get('published_at','UNKNOWN'))
    e['stored_sha256']=e.get('stored_sha256',e.get('compressed_sha256',e.get('sha256')))
    e['stored_size_bytes']=e.get('compressed_size_bytes',e.get('size_bytes'))
    e['manifest_path']=str(manifest.relative_to(ROOT))
    e['value_status']=e.get('value_status','UNKNOWN')
    for key in ['grain','geographic_coverage','temporal_coverage','key_fields','units','license','limitations','collector_version','command','decision_use']:
        e.setdefault(key,'UNKNOWN')
    e.setdefault('record_count',None);e.setdefault('record_count_unit','Source rows if available; NULL for documents/unparsed content')
    e.setdefault('validation_boundary','Retained source bytes and structure only; not independent verification of source claims')
    e['origin_group']=origin(e)
    return e
def header_checks():
    violations=[]
    def walk(x,path,file):
        if isinstance(x,dict):
            for k,v in x.items():
                if k.lower() in {'headers','response_headers','request_headers'} and isinstance(v,dict):
                    for name in v:
                        if name.lower() not in SAFE:violations.append(dict(file=file,path=path+'/'+k,header_name=name))
                if k.lower() in {'set-cookie','cookie','authorization','proxy-authorization'}:
                    violations.append(dict(file=file,path=path,header_name=k))
                walk(v,path+'/'+k,file)
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,path+'/'+str(i),file)
    for f in ROOT.rglob('*.json'):
        if f.name=='bundle_validation.json':continue
        try:walk(read_json(f),'',str(f.relative_to(ROOT)))
        except (ValueError,UnicodeError):pass
    return violations
def main():
    entries=[]
    main_manifests=['acquisition_manifest.json','aux_acquisition_manifest.json','favt_acquisition_manifest.json',
        'mintrans_acquisition_manifest.json','telegram_favt_ru_manifest.json']
    main_manifests += [str(p.relative_to(ROOT)) for p in sorted(ROOT.glob('additional_*_manifest.json')) if p.name!='additional_input_manifest.json']
    for n in main_manifests:
        f=ROOT/n
        for e in read_json(f)['datasets']:entries.append(standard(e,f))
    for b in ['social_economy','operating_evidence']:
        prefix='branches/'+b;f=ROOT/prefix/'dataset_manifest.json';d=read_json(f)
        ds=d if isinstance(d,list) else d['datasets']
        # Enrichment may be stored in registry rather than acquisition receipt.
        registry=ROOT/prefix/'source_registry.csv'
        enrich={r['dataset_id']:r for r in csv.DictReader(registry.open())} if registry.exists() else {}
        for e in ds:
            e=dict(e)
            for k,v in enrich.get(e['dataset_id'],{}).items():
                if (k not in e or e[k] in [None,'UNKNOWN','']) and v!='':e[k]=v
            entries.append(standard(e,f,prefix))
    # Preserve original front archive and other selected reused data receipts.
    f=ROOT/'colleague_raw_manifest.json';d=read_json(f)
    for i,e in enumerate(d['files']):
        e=dict(e);e.update(dataset_id='pinned_reuse_'+str(i),raw_path=e['path'],source_url='https://github.com/Mput13/case_championship/blob/'+e['input_sha']+'/'+e['git_path'],
            organization='Colleague pinned git input',retrieved_at_utc=dt.datetime.fromtimestamp((ROOT/e['path']).stat().st_mtime,dt.timezone.utc).isoformat(),
            publication_date='Git input SHA; source publication date UNKNOWN',record_count=e.get('rows'),
            acquisition_status=e.get('acquisition_status','ACQUIRED_RAW'),command='git show '+e['input_sha']+':'+e['git_path'],
            grain='Pinned source table; inspect original columns',geographic_coverage='Per pinned source',temporal_coverage='Per pinned source',
            limitations=e.get('limitations','Pinned input, not independently validated by its presence in Git'),
            decision_use='Reuse audit and lineage; source-specific restrictions preserved',collector_version='git-show-selected-inputs-v1')
        entries.append(standard(e,f))
    # Exact byte checks; verify original payload when an acquired file is gzip.
    integrity=[]
    for e in entries:
        path=e.get('raw_path')
        if not path:continue
        f=ROOT/path;exists=f.is_file();actual=sha(f) if exists else None
        ok=exists and actual==e.get('stored_sha256')
        check=dict(dataset_id=e['dataset_id'],path=path,exists=exists,stored_hash_matches=ok)
        if exists and f.suffix=='.gz' and e.get('sha256')!=e.get('stored_sha256'):
            b=gzip.decompress(f.read_bytes());check['payload_hash_matches']=hashlib.sha256(b).hexdigest()==e['sha256'];ok &=check['payload_hash_matches']
        check['pass']=ok;integrity.append(check)
    # Inventory includes support documents/code and unregistered sidecar extracts.
    artifacts=[]
    source_by_path={e.get('raw_path'):e['dataset_id'] for e in entries if e.get('raw_path')}
    for f in sorted(ROOT.rglob('*')):
        if not f.is_file() or '__pycache__' in f.parts:continue
        rel=f.relative_to(ROOT);parts=rel.parts
        if not ('raw' in parts or 'normalized' in parts or rel.as_posix()=='canonical_keys.csv'):continue
        raw='raw' in parts
        a=dict(path=rel.as_posix(),sha256=sha(f),size_bytes=f.stat().st_size,record_count=rows_count(f),
            kind='RAW_OR_RAW_SIDECAR' if raw else 'NORMALIZED_OR_DIAGNOSTIC',dataset_id=source_by_path.get(rel.as_posix()),
            command='See source manifest or integration_plan.md offline replay')
        if f.suffix=='.gz':
            b=gzip.decompress(f.read_bytes());a.update(uncompressed_sha256=hashlib.sha256(b).hexdigest(),uncompressed_size_bytes=len(b))
        if raw and not a['dataset_id']:
            a['limitations']='Support file or derived text/code snapshot; not an independently admitted fact table'
            if 'colleague_inputs' in parts:
                j=parts.index('colleague_inputs');s=parts[j+1];gp='/'.join(parts[j+2:])
                a['source_url']='https://github.com/Mput13/case_championship/blob/'+s+'/'+gp
                a['command']='git show '+s+':'+gp
                a['input_sha']=s
        artifacts.append(a)
    violations=header_checks()
    assert not violations, 'Non-whitelisted headers found; see diagnostics before publication'
    ids=[e['dataset_id'] for e in entries];duplicates=[k for k,n in Counter(ids).items() if n>1]
    assert not duplicates,duplicates
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    dump(ROOT/'dataset_manifest.json',dict(schema_version='core-bundle-v1',created_at_utc=now,path_base='context/16_agent_research/core/',
        datasets=entries,artifact_inventory=artifacts,
        validation_boundary='Hashes, selected structural checks, joins and manual source samples; no independent audit of every value; statuses not promoted by byte matches',
        replay='python3 context/16_agent_research/core/collectors/finalize_core.py'))
    csv_write(ROOT/'source_registry.csv',entries,FIELDS)
    cf=['dataset_id','source_url','geographic_coverage','temporal_coverage','grain','record_count','record_count_unit','acquisition_status','value_status','decision_use','limitations']
    csv_write(ROOT/'coverage.csv',entries,cf)
    rejected=[dict(dataset_id=e['dataset_id'],source_url=e['source_url'],status=e['acquisition_status'],
        error=e.get('error',''),reason=e['limitations'],retrieved_at_utc=e.get('retrieved_at_utc'),
        next_step='Use documented surrogate or retain UNKNOWN; no bypass of access controls')
        for e in entries if e['acquisition_status'] in {'ACCESS_FAILED','RESTRICTED_USE','LEAD'}]
    csv_write(ROOT/'rejected_or_unavailable.csv',rejected,['dataset_id','source_url','status','error','reason','retrieved_at_utc','next_step'])
    counts=Counter(e['acquisition_status'] for e in entries)
    validation=dict(created_at_utc=now,source_entries=len(entries),source_status_counts=dict(counts),raw_hash_checks=len(integrity),
        all_registered_raw_hashes_pass=all(c['pass'] for c in integrity),raw_checks=integrity,
        header_whitelist_violations=violations,artifact_files=len(artifacts),artifact_bytes=sum(a['size_bytes'] for a in artifacts),
        unique_source_raw_paths=len(source_by_path),note='File bytes/counts are not source truth, route execution, legality or profitability acceptance')
    dump(ROOT/'diagnostics/bundle_validation.json',validation)
    assert validation['all_registered_raw_hashes_pass'], 'Raw mismatch'
    print(json.dumps({k:v for k,v in validation.items() if k not in ['raw_checks']},ensure_ascii=False))
if __name__=='__main__':main()
