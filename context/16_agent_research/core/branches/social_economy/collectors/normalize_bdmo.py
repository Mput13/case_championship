#!/usr/bin/env python3
"""No-network normalization of selected BDMO archives; preserves conflicting keys.
Run after normalize_social.py: python3 context/16_agent_research/core/branches/social_economy/collectors/normalize_bdmo.py
"""
from pathlib import Path
import collections,csv,datetime,gzip,hashlib,io,json,zipfile
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'raw';OUT=ROOT/'normalized'
CMD='python3 context/16_agent_research/core/branches/social_economy/collectors/normalize_bdmo.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(r):return tuple(r[k] for k in ['region_id','oktmo','mun_level','year'])
def main():
 mf=json.loads((ROOT/'dataset_manifest.json').read_text());byid={x['dataset_id']:x for x in mf['datasets']};artifacts=mf.get('normalized_artifacts',[]);summary=[];panels={};conflicts=[]
 for suffix in ['municipal_wages','municipal_population']:
  did='tochno_bdmo_'+suffix;p=RAW/(did+'.zip')
  with zipfile.ZipFile(p) as z:
   member=next(n for n in z.namelist() if n.endswith('.csv'));rawsha=hashlib.sha256();uncompressed=0
   with z.open(member) as f:
    for block in iter(lambda:f.read(1024*1024),b''):rawsha.update(block);uncompressed+=len(block)
   with z.open(member) as f:rr=list(csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig'),delimiter=';'))
   integrity=z.testzip() is None
  keys=collections.defaultdict(list);missing=0;years=collections.Counter();levels=collections.Counter();norm=OUT/(did+'.csv.gz')
  with norm.open('wb') as b,gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=0) as g,io.TextIOWrapper(g,encoding='utf-8',newline='') as f:
   w=None
   for no,r in enumerate(rr,2):
    raw=dict(r);nulls={k:('NO_INFORMATION' if v=='ND' else 'NOT_APPLICABLE' if v=='CD' else 'UNDEFINED_CODE' if v=='UD' else 'EMPTY_IN_REPUBLICATION') for k,v in r.items() if v in ['ND','CD','UD','']}
    for k in nulls:r[k]=''
    reason='EMPTY_IN_REPUBLICATION' if not r['indicator_value'] else ''
    missing+=bool(reason);years[r['year']]+=1;levels[r['mun_level']]+=1
    r.update(source_dataset_id=did,source_archive_member=member,source_row=no,value_status='UNKNOWN' if reason else 'OBSERVED',value_missing_reason=reason,source_null_fields=json.dumps(nulls,ensure_ascii=False,sort_keys=True),geography_warning='Nested territorial levels and changing boundaries; do not join across years on oktmo_stable without boundary check')
    if w is None:w=csv.DictWriter(f,list(r));w.writeheader()
    w.writerow(r);keys[key(r)].append(r)
  for k,rows in keys.items():
   if len(rows)>1:
    for r in rows:conflicts.append(dict(dataset_id=did,region_id=r['region_id'],oktmo=r['oktmo'],mun_level=r['mun_level'],year=r['year'],source_row=r['source_row'],municipality=r['municipality'],mun_type=r['mun_type'],indicator_value=r['indicator_value'],comment=r['comment'],action='KEEP_RAW; exclude ambiguous key from example join'))
  panels[suffix]=keys;byid[did].update(record_count=len(rr),acquisition_status='PARSED',key_fields='source_row; candidate analytical keys require uniqueness check; see bdmo_conflicting_keys.csv',csv_member_sha256=rawsha.hexdigest(),csv_member_uncompressed_bytes=uncompressed,license='Creative Commons BY (version not stated in PDF)')
  artifacts.append(dict(path=str(norm.relative_to(ROOT)),sha256=sha(norm),size_bytes=norm.stat().st_size,record_count=len(rr),compression='gzip',command=CMD))
  summary.append(dict(dataset_id=did,record_count=len(rr),regions=len({r['region_id'] for r in rr}),years=dict(years),levels=dict(levels),missing_values=missing,duplicate_candidate_keys=sum(len(x)>1 for x in keys.values()),archive_integrity='PASS' if integrity else 'FAIL'))
 def save(name,rr,fields=None):
  p=OUT/name
  with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fields or list(rr[0]));w.writeheader();w.writerows(rr)
  artifacts.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),size_bytes=p.stat().st_size,record_count=len(rr),command=CMD))
 save('bdmo_conflicting_keys.csv',conflicts)
 wages=panels['municipal_wages'];pop=panels['municipal_population'];joined=[];rejected=[]
 for k,wr in wages.items():
  if k[3]!='2024' or k[2]!='Муниципальное образование верхнего уровня':continue
  pr=pop.get(k,[])
  if len(wr)!=1 or len(pr)!=1:
   rejected.append(dict(region_id=k[0],oktmo=k[1],year=k[3],wage_records=len(wr),population_records=len(pr),reason='NO_POPULATION_MATCH' if not pr else 'AMBIGUOUS_KEY'));continue
  w=wr[0];p=pr[0]
  joined.append(dict(region_id=w['region_id'],region_name=w['region_name'],oktmo=w['oktmo'],mun_level=w['mun_level'],municipality=w['municipality'],year='2024',gross_monthly_wage_rub=w['indicator_value'],wage_observation_status=w['value_status'],wage_period=w['indicator_period'],annual_average_population_persons=p['indicator_value'],population_observation_status=p['value_status'],wage_source_row=w['source_row'],population_source_row=p['source_row'],wage_source_mun_type=w['mun_type'],population_source_mun_type=p['mun_type'],municipal_type_agrees=str(w['mun_type']==p['mun_type']),join_status='DERIVED_JOIN_OF_OBSERVATIONS',scope='Municipality, not individual city, catchment or passenger. Wage excludes small enterprises.'))
 type_review=[r for r in joined if r['municipal_type_agrees']=='False']
 save('example_join_municipal_2024_type_review.csv',type_review)
 joined=[r for r in joined if r['municipal_type_agrees']=='True']
 for r in type_review:rejected.append(dict(region_id=r['region_id'],oktmo=r['oktmo'],year='2024',wage_records=1,population_records=1,reason='MUNICIPAL_TYPE_MISMATCH_REQUIRES_REVIEW'))
 save('example_join_municipal_2024.csv',joined);save('example_join_municipal_2024_rejected.csv',rejected,['region_id','oktmo','year','wage_records','population_records','reason'])
 validation=dict(datasets=summary,joined_2024_top_level_municipalities=len(joined),rejected_2024_keys=len(rejected),join_missing_population_values=sum(not r['annual_average_population_persons'] for r in joined),join_missing_wage_values=sum(not r['gross_monthly_wage_rub'] for r in joined),municipal_type_mismatches_in_clean_join=sum(r['municipal_type_agrees']=='False' for r in joined),municipal_type_mismatches_held_for_review=len(type_review),unit_note='annual average population persons; gross nominal average monthly wages RUB Jan–Dec, large/medium/nonprofit employers')
 (OUT/'bdmo_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
 byid['tochno_bdmo_description']['license']='Creative Commons BY (version not stated in PDF)'
 mf['normalized_artifacts']=artifacts;mf['generated_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();mf['bdmo_normalization_command']=CMD
 (ROOT/'dataset_manifest.json').write_text(json.dumps(mf,ensure_ascii=False,indent=2)+'\n')
 fields=list(next(csv.DictReader((ROOT/'source_registry.csv').open(encoding='utf-8'))))
 with (ROOT/'source_registry.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(mf['datasets'])
 print(json.dumps(validation,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
