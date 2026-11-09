#!/usr/bin/env python3
"""Parse acquired raw without network. Standard library + existing openpyxl.
Run: python3 context/16_agent_research/core/branches/social_economy/collectors/normalize_social.py
"""
from pathlib import Path
import collections,csv,datetime,gzip,hashlib,io,json,re,zipfile
import openpyxl
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'raw';OUT=ROOT/'normalized';OUT.mkdir(exist_ok=True)
COMMAND='python3 context/16_agent_research/core/branches/social_economy/collectors/normalize_social.py'
MISSING={'-99999999.0':'NO_INFORMATION_OR_SOURCE_ERROR','-77777777.0':'SUPPRESSED_IN_SOURCE'}
TARGET={'Y477110373','Y477110461','Y477110372','Y477110418','Y477110420','Y477110374','Y477110378','Y477110209','Y477110208','Y477110005','Y477110006','Y477110191','Y477110192'}
ART=[]
def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def savecsv(name,rows,fields=None):
 p=OUT/name;rows=list(rows);fields=fields or (list(rows[0]) if rows else [])
 with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
 artifact=dict(path=str(p.relative_to(ROOT)),sha256=hashfile(p),size_bytes=p.stat().st_size,record_count=len(rows),command=COMMAND)
 if name=='regional_selected_panel.csv':
  b=p.read_bytes();gz=p.with_suffix('.csv.gz')
  with gz.open('wb') as f:
   with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as g:g.write(b)
  artifact.update(path=str(gz.relative_to(ROOT)),sha256=hashfile(gz),size_bytes=gz.stat().st_size,uncompressed_sha256=hashlib.sha256(b).hexdigest(),uncompressed_size_bytes=len(b),compression='gzip');p.unlink()
 ART.append(artifact);return rows

def rowszip(path):
 with zipfile.ZipFile(path) as z:
  name=next(x for x in z.namelist() if x.endswith('.csv'))
  with z.open(name) as f:yield from csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig'),delimiter=';')

def main():
 mf=json.loads((ROOT/'dataset_manifest.json').read_text());byid={x['dataset_id']:x for x in mf['datasets']};stats=[];inventory=[];targets=[];integrity=[]
 fields=['source_dataset_id','source_archive_member','source_row','value_status','value_missing_reason','unit_missing_reason','comment_missing_reason','subsection_missing_reason']
 for p in sorted(RAW.glob('tochno_regions_*.zip')):
  did=p.stem;did='tochno_regions_'+did.removeprefix('tochno_regions_');sentinels=collections.Counter();unique=set();duplicates=0;inv=collections.defaultdict(lambda:dict(rows=0,years=set(),regions=set(),units=set(),missing=0));rows=0
  with zipfile.ZipFile(p) as z:
   member=next(x for x in z.namelist() if x.endswith('.csv'));hh=hashlib.sha256();uncompressed=0
   with z.open(member) as r:
    for block in iter(lambda:r.read(1024*1024),b''):hh.update(block);uncompressed+=len(block)
   byid[did]['csv_member_sha256']=hh.hexdigest();byid[did]['csv_member_uncompressed_bytes']=uncompressed
   norm=OUT/(p.stem+'.csv.gz')
   with norm.open('wb') as binary,gzip.GzipFile(filename='',mode='wb',fileobj=binary,mtime=0) as gz,io.TextIOWrapper(gz,encoding='utf-8',newline='') as f:
    w=None
    for no,r in enumerate(rowszip(p),2):
     rows+=1;raw=dict(r);v=r['indicator_value'];reason=MISSING.get(v,'');sentinels[reason or 'OBSERVED_VALUE']+=1
     key=(r['indicator_code'],r['subsection'],r['object_name'],r['object_level'],r['object_oktmo'],r['year'],r['source'])
     if key in unique:duplicates+=1
     unique.add(key)
     r['indicator_value']='' if reason else v
     for k,sentinel in [('indicator_unit','ND'),('comment','CD'),('subsection','CD')]:
      if r[k]==sentinel:r[k]=''
     r.update(source_dataset_id=did,source_archive_member=member,source_row=no,value_status='UNKNOWN' if reason else 'OBSERVED',value_missing_reason=reason,unit_missing_reason='NOT_FOUND_BY_PUBLISHER' if raw['indicator_unit']=='ND' else '',comment_missing_reason='NOT_APPLICABLE_PER_PUBLISHER' if raw['comment']=='CD' else '',subsection_missing_reason='NOT_APPLICABLE_PER_PUBLISHER' if raw['subsection']=='CD' else '')
     if w is None:w=csv.DictWriter(f,list(r));w.writeheader()
     w.writerow(r)
     k=(r['indicator_code'],r['indicator_name'],r['subsection']);a=inv[k];a['rows']+=1;a['years'].add(r['year']);a['regions'].add(r['object_name']);a['units'].add(r['indicator_unit']);a['missing']+=bool(reason)
     if r['indicator_code'] in TARGET:targets.append(r)
   ART.append(dict(path=str(norm.relative_to(ROOT)),sha256=hashfile(norm),size_bytes=norm.stat().st_size,record_count=rows,compression='gzip',raw_archive_path=str(p.relative_to(ROOT)),command=COMMAND))
   byid[did]['record_count']=rows;byid[did]['acquisition_status']='PARSED';byid[did]['key_fields']='indicator_code;subsection;object_name;object_level;object_oktmo;year;source (object_oktmo alone not unique across inclusive/exclusive AO geographies)'
   stats.append(dict(dataset_id=did,record_count=rows,unique_key_count=len(unique),duplicate_key_count=duplicates,missing_value_counts=dict(sentinels),archive_integrity='PASS' if z.testzip() is None else 'FAIL'))
   for (code,name,sub),a in inv.items():inventory.append(dict(dataset_id=did,indicator_code=code,indicator_name=name,subsection=sub,record_count=a['rows'],first_year=min(a['years']),last_year=max(a['years']),territory_label_count=len(a['regions']),units=' | '.join(sorted(a['units'])),missing_count=a['missing']))
 savecsv('indicator_inventory.csv',inventory)
 savecsv('regional_selected_panel.csv',targets)
 # Latest means latest available period within each reported territory and indicator, including NULL in the latest year.
 latest={}
 for r in targets:
  k=(r['indicator_code'],r['subsection'],r['object_level'],r['object_name'])
  if k not in latest or int(r['year'])>int(latest[k]['year']):latest[k]=r
 latest=savecsv('regional_selected_latest.csv',sorted(latest.values(),key=lambda x:(x['indicator_code'],x['object_name'])))
 # Census geographic dimension. Each record is a source partition, not necessarily one municipality or city.
 census=list(rowszip(RAW/'tochno_settlements_csv.zip'));census_norm=[];regmap=collections.defaultdict(collections.Counter)
 for i,r in enumerate(census,2):
  q=dict(r)
  for k,v in q.items():
   if v in ['Значение отсутствует','None']:q[k]=''
  if q['terson']=='99999999999':q['terson']=''
  q['source_null_fields']=' | '.join(k for k,v in q.items() if v=='')
  q.update(observation_period='2021 census',value_status='OBSERVED',source_dataset_id='tochno_settlements',source_row=i,geography_warning='May be intracity district or municipality residual; do not deduplicate on city/OKTMO alone')
  census_norm.append(q);regmap[q['region']][q['region_iso_code']]+=1
 savecsv('census_2021_settlement_partitions.csv',census_norm)
 byid['tochno_settlements']['record_count']=len(census);byid['tochno_settlements']['acquisition_status']='PARSED';byid['tochno_settlements']['key_fields']='source_row (city/OKTMO may repeat across districts)'
 aliases={'Архангельская область':'Архангельская область (без автономного округа)','г. Москва':'Москва','Республика Северная Осетия-Алания':'Республика Северная Осетия — Алания','г. Севастополь':'Севастополь','г. Санкт-Петербург':'Санкт-Петербург','Тюменская область':'Тюменская область (без автономных округов)','Ханты-Мансийский автономный округ - Югра':'Ханты-Мансийский автономный округ — Югра','Кемеровская область – Кузбасс':'Кемеровская область'}
 income={r['object_name']:r for r in latest if r['indicator_code']=='Y477110374' and r['object_level']=='Регион'}
 bridge=[]
 for name,iso_counts in sorted(regmap.items()):
  rn=aliases.get(name,name);r=income.get(rn)
  area_id=('rosstat_region:'+r['object_oktmo']+(':excl_ao' if 'без автономн' in rn else '')) if r else ''
  bridge.append(dict(canonical_area_id=area_id,census_region_label=name,regional_table_label=rn,regional_oktmo=r['object_oktmo'] if r else '',regional_okato=r['object_okato'] if r else '',modal_source_iso=iso_counts.most_common(1)[0][0],raw_iso_variants=' | '.join(sorted(iso_counts)),raw_iso_variant_count=len(iso_counts),source_iso_disagrees_with_modal_count=sum(iso_counts.values())-iso_counts.most_common(1)[0][1],match_status='MATCHED' if r else 'UNMATCHED',mapping_method='EXPLICIT_ALIAS' if name in aliases else 'EXACT_REGION_LABEL',geographic_rule='Exclude autonomous okrugs from parent region; they have separate ISO records',mapping_status='DERIVED'))
 savecsv('region_crosswalk.csv',bridge)
 bridged={r['census_region_label']:r for r in bridge};joined=[];iso_mismatches=[]
 for r in census_norm:
  b=bridged[r['region']];s=income.get(b['regional_table_label'])
  if r['region_iso_code']!=b['modal_source_iso'] or r['region_iso_code']=='ISO':iso_mismatches.append(dict(source_row=r['source_row'],source_region=r['region'],source_iso=r['region_iso_code'],modal_iso_for_region=b['modal_source_iso'],source_settlement=r['settlement_name'],source_municipality=r['municipality_up_name'],source_latitude=r['geo_lat'],source_longitude=r['geo_lon'],geocoder_qc=r['qc'],source_okato=r['okato'],source_oktmo=r['oktmo'],canonical_area_id=b['canonical_area_id'],action='QUARANTINE geocoded keys/coordinates; use explicit region crosswalk for contextual regional income'))
  joined.append(dict(census_source_row=r['source_row'],canonical_area_id=b['canonical_area_id'],source_region_iso_code=r['region_iso_code'],census_region=r['region'],municipality_up_name=r['municipality_up_name'],settlement_name=r['settlement_name'],district=r['district'],source_oktmo=r['oktmo'],population_persons_2021=r['pop_total'],population_status='OBSERVED',regional_income_source_name=b['regional_table_label'],regional_income_year=s['year'] if s else '',regional_income_rub_month=s['indicator_value'] if s else '',income_scope='REGION, not city or individual passenger',income_status=s['value_status'] if s else 'UNKNOWN',join_status=b['match_status'],income_source_row=s['source_row'] if s else '',income_source_dataset='tochno_regions_living_standards',join_method='Explicit source regional label crosswalk to Rosstat region code and excl-AO scope; raw ISO not used'))
 savecsv('example_join_census_regional_income.csv',joined)
 savecsv('census_geocode_mismatches.csv',iso_mismatches)
 # Preserve the archive workbook's TЕРСОН-МО codes as their own namespace; these are not silently called OKTMO.
 wb=openpyxl.load_workbook(RAW/'rosstat_municipal_2025_archive.xlsx',read_only=True,data_only=True);region_names={str(r[1]).strip() for r in wb['Перечень_субъектов_РФ'].values if r[1] and r[0] is not None};municipal=[];current_region='';arithmetic=[]
 for rowno,row in enumerate(wb['Численность_по_МО'].values,1):
  code,name,total,urban,rural,*_=row
  if not name or not isinstance(total,(float,int)):continue
  name=str(name).strip()
  if name in region_names:current_region=name
  nums=[x if isinstance(x,(float,int)) else '' for x in [total,urban,rural]]
  if nums[1]!='' and nums[2]!='' and abs(nums[0]-nums[1]-nums[2])>0.001:arithmetic.append(rowno)
  municipal.append(dict(source_dataset_id='rosstat_municipal_2025_archive',sheet='Численность_по_МО',source_row=rowno,source_territory_code_namespace='ТЕРСОН-МО',source_territory_code=str(code) if code is not None else '',source_territory_name=name,region_context=current_region,population_total_persons=nums[0],urban_population_persons=nums[1],rural_population_persons=nums[2],observation_date='2025-01-01',value_status='OBSERVED',source_authenticity='UNAFFILIATED_ARCHIVE_MIRROR_NOT_LIVE_VERIFIED',aggregation_warning='Mixed nested geographies. Do not sum all rows. TЕРСОН-МО is not interchangeable with OKTMO.'))
 savecsv('rosstat_population_2025_archive_rows.csv',municipal)
 byid['rosstat_municipal_2025_archive']['record_count']=len(municipal);byid['rosstat_municipal_2025_archive']['acquisition_status']='PARSED';byid['rosstat_municipal_2025_archive']['key_fields']='source_row; source TЕРСОН-МО namespace preserved'
 am=json.loads((RAW/'archive_metadata.json').read_text());af=next(f for f in am['files'] if f['name']=='Сhisl_MO_01-01-2025.xlsx');archive_sha1=hashlib.sha1((RAW/'rosstat_municipal_2025_archive.xlsx').read_bytes()).hexdigest()
 diag=dict(regional_datasets=stats,regional_rows=sum(x['record_count'] for x in stats),census_partitions=len(census),census_regions=len(regmap),census_raw_region_iso_combinations=sum(len(x) for x in regmap.values()),census_iso_mismatch_rows=len(iso_mismatches),census_total_persons=sum(int(r['pop_total']) for r in census),census_sex_additivity_failures=sum(int(r['pop_total'])!=int(r['pop_men'])+int(r['pop_women']) for r in census),crosswalk_unmatched_regions=[r for r in bridge if r['match_status']!='MATCHED'],crosswalk_aliases=aliases,join_rows=len(joined),join_missing_income=sum(not r['regional_income_rub_month'] for r in joined),archive_workbook_rows=len(municipal),archive_arithmetic_failures=arithmetic,archive_sha1_matches_ia_metadata=archive_sha1==af.get('sha1'),archive_note='IA metadata hash checks transport integrity against the archive only, not authenticity against official Rosstat.')
 (OUT/'validation.json').write_text(json.dumps(diag,ensure_ascii=False,indent=2)+'\n')
 mf['generated_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();mf['normalized_artifacts']=ART;mf['normalization_command']=COMMAND
 (ROOT/'dataset_manifest.json').write_text(json.dumps(mf,ensure_ascii=False,indent=2)+'\n')
 # Keep the CSV registry synchronized with parsed manifests.
 fields=list(next(csv.DictReader((ROOT/'source_registry.csv').open(encoding='utf-8'))))
 with (ROOT/'source_registry.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(mf['datasets'])
 print(json.dumps({k:v for k,v in diag.items() if k not in ['regional_datasets','crosswalk_aliases']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
