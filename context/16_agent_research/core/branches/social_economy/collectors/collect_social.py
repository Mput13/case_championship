#!/usr/bin/env python3
"""Public social/economic raw collection, Python stdlib; TLS verification stays enabled.
Run from repo root: python3 context/16_agent_research/core/branches/social_economy/collectors/collect_social.py
Each raw file is immutable unless --refresh is passed; receipts include byte hashes.
"""
import argparse,csv,datetime,hashlib,json,pathlib,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/'raw';RAW.mkdir(exist_ok=True)
BASE='https://storage.yandexcloud.net/tochno-st-catalog/Rosstat/'
RBASE=BASE+'data_regions_collection_102_v20260313/'
SOURCES=[
 ('rosstat_municipal_2025_archive','https://archive.org/download/rosstat-november-2025/%D0%A1hisl_MO_01-01-2025.xlsx','rosstat_municipal_2025_archive.xlsx','Internet Archive mirror of Rosstat','2025-01-01','municipality/settlement × 2025-01-01','UNKNOWN','Mirror uploaded by unaffiliated account; not byte-verified against Rosstat live file; overlapping territorial levels must not be summed.'),
 ('archive_metadata','https://archive.org/metadata/rosstat-november-2025','archive_metadata.json','Internet Archive','2025-12-03','archive item metadata','UNKNOWN','Metadata establishes uploader and archived hash, not official Rosstat authenticity.'),
 ('tochno_settlements',BASE+'data_settlements_115_v20240326/data_settlements_115_v20240326_csv.zip','tochno_settlements_csv.zip','Если быть точным; Rosstat census source; DaData geocoding','2021 census','municipality/settlement','CC BY 4.0','Processed republication, not independent census; not a current 2026 population; records include territorial levels; preserve hierarchy.'),
 ('tochno_settlements_description',BASE+'data_settlements_115_v20240326/description_settlements_115_v20240326.pdf','tochno_settlements_description.pdf','Если быть точным','dataset v20240326','dataset documentation','CC BY 4.0','Documentation, no passenger-demand measurement.'),
 ('tochno_regions_description',RBASE+'description_regions_collection_102_v20260313.pdf','tochno_regions_description.pdf','Если быть точным','dataset v20260313','dataset documentation','CC BY 4.0','Documentation, no passenger-demand measurement.')]
for no,title in [('01','population'),('02','labor'),('03','living_standards'),('06','tourism'),('08','grp')]:
 SOURCES.append(('tochno_regions_'+title,RBASE+f'data_{no}_socio_economic_102_v20260313.zip',f'tochno_regions_{title}.zip','Если быть точным; Rosstat source','2001–2025 collection; individual indicator coverage differs','region/federal district/country × year × indicator','CC BY 4.0','Processed republication of Rosstat compilations; publication year differs from observation year; nested aggregate territories; regional mean is not city or passenger income.'))


for slug in ['settlements','bdmo','regions_collection']:
 SOURCES.append(('tochno_'+slug+'_page','https://tochno.st/datasets/'+slug,'tochno_'+slug+'_page.html','Если быть точным','snapshot 2026-11-09','source landing page','UNKNOWN','Source provenance and links; snapshot is not a fact table.'))
for fmt in ['csv','xlsx']:
 SOURCES.append(('bdmo_indicator_catalog_'+fmt,'https://docs.google.com/spreadsheets/d/1fain2iBHAJEkaXYk-8aAcjEA8tdR5GKF134AAk1UCSQ/export?format='+fmt,'bdmo_indicator_catalog.'+fmt,'Если быть точным; public linked indicator catalog','v20260928; live catalog snapshot','indicator and download metadata','UNKNOWN','Public source catalog. CSV exports only first description tab; XLSX includes all sheets.'))
for code,title in [('Y48213002','municipal_wages'),('Y48112013','municipal_population')]:
 SOURCES.append(('tochno_bdmo_'+title,BASE+'data_bdmo_118_v20260928/indicators/section41/data_'+code+'_112_v20260928.zip','tochno_bdmo_'+title+'.zip','Если быть точным; Rosstat BDMO source','2008–2025 (wages), 2008–2024 (population); inspect records','municipality × year × period × indicator','UNKNOWN','Processed BDMO republication; changing municipal boundaries; wage is gross employee average at large/medium/nonprofit employers, not resident income.'))
SOURCES.append(('tochno_bdmo_description',BASE+'data_bdmo_118_v20260928/description_bdmo_112_v20260928.pdf','tochno_bdmo_description.pdf','Если быть точным','dataset v20260928','dataset documentation','UNKNOWN','Documentation, not passenger demand.'))

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def collect(refresh=False):
 previous={x['dataset_id']:x for x in json.loads((ROOT/'dataset_manifest.json').read_text()).get('datasets',[])} if (ROOT/'dataset_manifest.json').exists() else {}
 entries=[];fail=[]
 for did,url,name,org,period,grain,lic,limits in SOURCES:
  p=RAW/name
  if did in previous and p.exists() and not refresh:entries.append(previous[did]);continue
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'case5-research/1.0 public-data collection'})
   with urllib.request.urlopen(req,timeout=40) as r:
    expected=r.headers.get('Content-Length')
    if expected and int(expected)>25_000_000:raise ValueError('download cap 25 MB exceeded: '+expected)
    b=r.read(25_000_001)
    if len(b)>25_000_000:raise ValueError('download cap 25 MB exceeded')
    headers={k:r.headers.get(k) for k in ['Content-Type','Content-Length','Last-Modified','ETag','Date','Cache-Control'] if r.headers.get(k) is not None};effective=r.url
   p.write_bytes(b)
   e=dict(dataset_id=did,source_url=url,source_organization=org,raw_path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(b).hexdigest(),size_bytes=len(b),retrieved_at_utc=now(),published_at='UNKNOWN',http_last_modified=headers.get('Last-Modified'),effective_url=effective,grain=grain,geographic_coverage='Russia within source territorial coverage; inspect individual territory labels',temporal_coverage=period,record_count=None,acquisition_status='ACQUIRED_RAW',value_status='OBSERVED',license=lic,limitations=limits,key_fields='source-specific; parser documents fields',collector_version='collect_social.py v1',command='python3 context/16_agent_research/core/branches/social_economy/collectors/collect_social.py')
   if zipfile.is_zipfile(p):
    with zipfile.ZipFile(p) as z:e['archive_members']=[dict(path=i.filename,uncompressed_bytes=i.file_size,compressed_bytes=i.compress_size) for i in z.infolist()]
   entries.append(e);print(did,len(b),flush=True)
  except Exception as ex:fail.append(dict(dataset_id=did,source_url=url,attempted_at_utc=now(),status='ACCESS_FAILED',error=f'{type(ex).__name__}: {ex}'));print('FAIL',did,str(ex),flush=True)
 (ROOT/'dataset_manifest.json').write_text(json.dumps(dict(schema_version='1.0',generated_at_utc=now(),path_base=str(ROOT),datasets=entries),ensure_ascii=False,indent=2)+'\n')
 fields=['dataset_id','source_url','source_organization','raw_path','sha256','size_bytes','retrieved_at_utc','published_at','temporal_coverage','grain','geographic_coverage','record_count','acquisition_status','value_status','license','limitations','collector_version','command']
 with (ROOT/'source_registry.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(entries)
 with (ROOT/'rejected_or_unavailable.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,['dataset_id','source_url','attempted_at_utc','status','error']);w.writeheader();w.writerows(fail)
 return entries
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--refresh',action='store_true');args=a.parse_args();collect(args.refresh)
