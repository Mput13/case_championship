from pathlib import Path
import urllib.request,datetime,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
SAFE_RESPONSE_HEADERS={'content-type','content-length','content-encoding','last-modified','etag','date','cache-control','expires','accept-ranges'}
def safe_headers(headers):
  return {k:v for k,v in headers.items() if k.lower() in SAFE_RESPONSE_HEADERS}
SOURCES=[('azimuth_about.html','https://azimuth.ru/ru/about/azimuth'),('tochno_about.html','https://tochno.st/datasets/intercity_connectivity'),('tochno_intercity.zip','https://storage.yandexcloud.net/tochno-st-catalog/Geo/data_intercity_connectivity_162_v20260629/data_intercity_connectivity_162_v20260629_csv.zip')]
manifest=[]
for name,url in SOURCES:
  now=datetime.datetime.now(datetime.timezone.utc).isoformat()
  try:
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Red Wings case source check)'})
    with urllib.request.urlopen(req,timeout=40) as r: b=r.read();headers=safe_headers(r.headers);status=r.status
    p=ROOT/'raw/primary'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    manifest.append({'dataset_id':name,'source_url':url,'raw_path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'retrieved_at_utc':now,'bytes':len(b),'http_status':status,'headers':headers,'grain':'webpage' if name.endswith('html') else 'directed city pair by transport','geographic_coverage':'Russia','temporal_coverage':'snapshot 2026-11-09; source periods vary','record_count':None,'acquisition_status':'ACQUIRED_RAW','limitations':'Origin metadata not equivalent to factual validation'})
  except Exception as e: manifest.append({'source_url':url,'retrieved_at_utc':now,'acquisition_status':'ACCESS_FAILED','error':str(e)})
(ROOT/'primary_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print([(x['dataset_id'],x.get('bytes')) for x in manifest])
