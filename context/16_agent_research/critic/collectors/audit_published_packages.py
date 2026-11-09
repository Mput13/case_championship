#!/usr/bin/env python3
"""Audit narrow published alternative/hypotheses inputs without executing their code."""
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

BASE=Path(__file__).resolve().parents[1]
ALT='5819ea357434617612aaeb3b8060b54e260ec93d'
HYP='46d7994f1abb65c693ad75045ef8b25cc43eb6b2'
ROOT='context/16_agent_research/'
MANIFEST=[]
SAFE_HEADERS={'content-type','content-length','content-encoding','last-modified','etag','date','cache-control','expires','accept-ranges'}

def sanitize_manifest(value):
    """Imported receipts are metadata; never persist arbitrary HTTP headers."""
    removed=0
    if isinstance(value,dict):
        for key in list(value):
            if key.lower() in {'cookie','set-cookie','authorization','proxy-authorization'}:
                del value[key];removed+=1;continue
            child=value[key]
            if key.lower() in {'headers','response_headers'} and isinstance(child,dict):
                kept={k:v for k,v in child.items() if k.lower() in SAFE_HEADERS}
                removed+=len(child)-len(kept);value[key]=kept
            else:removed+=sanitize_manifest(child)
    elif isinstance(value,list):
        for child in value:removed+=sanitize_manifest(child)
    return removed

def blob(sha,role,name):
    path=ROOT+role+'/'+name;b=subprocess.check_output(['git','show',sha+':'+path])
    original_hash=hashlib.sha256(b).hexdigest();original_bytes=len(b);removed=0
    if name=='dataset_manifest.json':
        document=json.loads(b);removed=sanitize_manifest(document)
        if removed:b=(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode()
    p=BASE/'raw/final_packages'/sha/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    MANIFEST.append(dict(input_sha=sha,author_attribution='Astra '+role+' research role; upstream Git authorship retained',repo_path=path,local_path=str(p.relative_to(BASE)),sha256=original_hash,bytes=original_bytes,stored_sha256=hashlib.sha256(b).hexdigest(),stored_bytes=len(b),header_fields_removed=removed,storage_transform='JSON metadata header whitelist' if removed else 'NONE_EXACT_BYTES'))
    return b
def table(sha,role,name):
    b=blob(sha,role,name)
    if name.endswith('.gz'):b=gzip.decompress(b)
    return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
def key_unique(rows,fields):
    k=[tuple(r[f]for f in fields)for r in rows]
    return dict(rows=len(rows),unique=len(set(k)),duplicate_rows=len(k)-len(set(k)))
def optional(s):return float(s)if s!=''else None
def eq(a,b):return a is None and b is None or a is not None and b is not None and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7)

def main():
    prefix='modules/tourism/'
    areas=table(ALT,'alternative',prefix+'normalized/areas.csv')
    obs=table(ALT,'alternative',prefix+'normalized/primary_observations.csv.gz')
    inc=table(ALT,'alternative',prefix+'normalized/primary_monthly_increments.csv')
    profiles=table(ALT,'alternative',prefix+'normalized/primary_seasonality_profiles.csv')
    coverage=table(ALT,'alternative',prefix+'primary_coverage.csv')
    for name in ['findings.md','integration_plan.md','collectors/normalize_primary.py','collectors/normalize_tourism.py']:
        blob(ALT,'alternative',prefix+name)
    canonical={r['area_id']for r in areas if r['in_disjoint_reference_panel']=='True'}
    values={(r['dataset_id'],r['area_id'],r['year'],int(r['period_end_month'])):optional(r['value'])for r in obs}
    errors=[]
    for r in inc:
        k=(r['dataset_id'],r['area_id'],r['year']);m=int(r['month']);cur=values.get((*k,m));prev=0 if m==1 else values.get((*k,m-1));expected=cur-prev if cur is not None and prev is not None else None
        if expected is not None and expected<0:expected=None
        if not eq(optional(r['monthly_increment']),expected):errors.append(dict(key=(*k,m),kind='monthly_increment'))
    grouped=collections.defaultdict(list)
    for r in inc:grouped[(r['dataset_id'],r['area_id'],r['year'])].append(r)
    for r in profiles:
        k=(r['dataset_id'],r['area_id'],r['year']);q=sorted(grouped[k],key=lambda x:int(x['month']));v=[optional(x['monthly_increment'])for x in q];complete=len(v)==12 and all(x is not None for x in v);total=sum(v)if complete else None
        if complete!=(r['complete_12_months']=='True')or not eq(total,optional(r['annual_ytd_total'])):errors.append(dict(key=k,kind='annual_total'))
        for name,months in [('summer_jun_aug_share',[6,7,8]),('winter_dec_jan_feb_share',[1,2,12])]:
            expected=sum(v[m-1]for m in months)/total if total else None
            if not eq(optional(r[name]),expected):errors.append(dict(key=k,kind=name))
    # Reconcile all four publisher JSON tables with exported original cells, not mirror values.
    primary_mismatch=0;raw_filled=0
    for indicator in [62073,62074,62301,62302]:
        src=json.loads(blob(ALT,'alternative',prefix+f'raw/fedstat_{indicator}_data.json'))['results']
        for r in obs:
            if r['dataset_id']!=f'emiss_{indicator}':continue
            loc=r['raw_json_locator'];head,field=loc.split('].');n=int(head.split('[')[1]);s=str(src[n][field]).replace(' ','').replace('\u00a0','').replace(',','.')
            try:v=float(s)
            except ValueError:v=None
            raw_filled+=v is not None
            if not eq(v,optional(r['value'])):primary_mismatch+=1
    sites=table(ALT,'alternative','modules/business/normalized/sibur_sites.csv')
    membership=table(ALT,'alternative','modules/business/normalized/group_site_membership.csv')
    gaz=table(ALT,'alternative','modules/business/normalized/gazprom_shift_observations.csv')
    rn=table(ALT,'alternative','modules/business/normalized/historical_vankor_routes.csv')
    for name in ['modules/business/findings.md','modules/business/collectors/normalize_business.py','modules/telegram_correction/coverage.json','modules/telegram_correction/findings.md','dataset_manifest.json','findings.md','signal_cards.csv']:
        blob(ALT,'alternative',name)
    cat=table(HYP,'hypotheses','candidates.csv');anc=table(HYP,'hypotheses','existing_hypotheses.csv');queue=table(HYP,'hypotheses','experiments_queue.csv');requests=table(HYP,'hypotheses','data_requests.csv');ev=table(HYP,'hypotheses','contributions/source_access/observations.csv')
    hmanifest=json.loads(blob(HYP,'hypotheses','dataset_manifest.json'))
    for name in ['methods.md','findings.md','candidate_schema.json','validation.json','collectors/validate.py','evaluation_runs.jsonl']:
        blob(HYP,'hypotheses',name)
    old={r['id']for r in anc};valid_evidence={r['observation_id']for r in ev}|{r['dataset_id']for r in hmanifest['datasets']}
    unmatched_anc=[dict(candidate_id=r['candidate_id'],ancestor=a)for r in cat for a in r['ancestor_ids'].split(';')if a not in old]
    unmatched_ev=[dict(candidate_id=r['candidate_id'],evidence=a)for r in cat for a in r['primary_evidence_ids'].split(';')if a and a not in valid_evidence]
    equal_to_previous={}
    previous=BASE/'evidence/cross_role_snapshot_v2/hypotheses'
    for name in ['candidates.csv','experiments_queue.csv']:
        captured=BASE/'raw/final_packages'/HYP/ROOT/'hypotheses'/name
        equal_to_previous[name]=(previous/name).read_bytes()==captured.read_bytes()
    out=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),input_shas={'alternative':ALT,'hypotheses':HYP},
        tourism=dict(primary_cell_keys=key_unique(obs,['dataset_id','area_id','year','period_end_month']),increment_keys=key_unique(inc,['dataset_id','area_id','year','month']),profile_keys=key_unique(profiles,['dataset_id','area_id','year']),canonical_areas=len(canonical),overlapping_parent_ids_excluded=not({'OKATO:11000000000','OKATO:71000000000'}&canonical),raw_filled_cells_reconciled=raw_filled,raw_cell_mismatches=primary_mismatch,arithmetic_errors=errors,complete2025=dict(collections.Counter(r['dataset_id']for r in profiles if r['year']=='2025'and r['complete_12_months']=='True')),scope='YTD differences are DERIVED registered accommodation seasonality; no origin, air mode, unique persons, airport catchment, causal route effect or2026/2025 comparability established'),
        business=dict(site_keys=key_unique(sites,['site_id']),membership_keys=key_unique(membership,['group_id','site_id']),membership_identity_matches={r['site_id']for r in sites}=={r['site_id']for r in membership},russian_sites=sum(r['country_iso_curated']=='RU'for r in sites),coordinates_missing=sum(r['latitude_source']==''for r in sites),gazprom_observations=len(gaz),historical_routes=len(rn),historical_volume_not_imputed=all(r['annual_passengers']==r['weekly_flights']==''for r in rn),scope='Group-to-site membership and employer headcount; not site-to-site travel OD or paid demand; historical airport hints cannot be automatic keys'),
        hypotheses=dict(candidate_keys=key_unique(cat,['candidate_id']),ancestor_records=len(anc),queue_rows=len(queue),unmatched_ancestor_ids=unmatched_anc,unmatched_evidence_ids=unmatched_ev,exact_D01_D30={r['data_id']for r in requests}=={f'D{i:02}'for i in range(1,31)},candidate_and_queue_match_prior_geometry_snapshot=equal_to_previous,economics_status=dict(collections.Counter(r['evaluation_status']for r in cat)),scope='Evidence IDs resolve structurally; source content does not thereby prove candidate demand; attributed ancestry is not an independent experiment'),
        acceptance='Scoped transformations and structural links only; no forecast/feature/launch acceptance')
    (BASE/'evidence/published_packages_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    (BASE/'evidence/published_packages_manifest.json').write_text(json.dumps(dict(captured_at_utc=out['generated_at_utc'],inputs=MANIFEST),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
