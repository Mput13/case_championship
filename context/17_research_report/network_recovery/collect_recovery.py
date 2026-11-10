#!/usr/bin/env python3
"""Bounded public read recovery; separate snapshots, no inherited raw copies."""
import csv,io,json,subprocess,hashlib,pathlib,re,urllib.request,urllib.error,urllib.parse,ssl,time,concurrent.futures,threading,sys,shutil
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parent
PINS={'core':'505e24663e5952bae9b9540bb9a5a622663bfc2a','alternative':'ef365ac2a936117e5b3bb12ea99c816d7b1a101c','hypotheses':'6ed8788882e7b4d07044b4f6e686ff71eadd8ac5','critic':'fd086bad2ae30c46e95d6e38954dc99a18627902'}
REFERENCES=[]
def stamp():return datetime.now(timezone.utc).isoformat()
def blob(role,rel):
 path=f'context/16_agent_research/{role}/{rel}'
 raw=subprocess.check_output(['git','show',f'{PINS[role]}:{path}'])
 REFERENCES.append(dict(role=role,source_sha=PINS[role],path=path,sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw)))
 return raw.decode('utf-8')
def rows(role,rel):return list(csv.DictReader(io.StringIO(blob(role,rel))))
def save(name,obj):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def make_plan():
 items=[]
 def add(i,url,role,path,err,date='',purpose='',workaround='',relevance='CURRENT',method='GET',body=None):
  if any(x['item_id']==i for x in items):return
  kind='http403' if '403' in err else '404' if '404' in err else 'backend' if '502' in err or 'concurren' in err else 'unknown'
  d=dict(item_id=i,claim_task=purpose or i,source_url=url,original_commit=PINS.get(role,''),original_path='context/16_agent_research/'+role+'/'+path if role in PINS else path,original_error=err,original_date=date or 'not individually recorded',kind=kind,actual_workaround_omission=workaround or 'Недоступный источник не заменяли нулём; допуск ограничен доступными источниками.',relevance=relevance,method=method,request_body=body)
  items.append(d)
 for r in rows('core','rejected_or_unavailable.csv'):
  if r['status']=='ACCESS_FAILED':add(r['dataset_id'],r['source_url'],'core','rejected_or_unavailable.csv',r['error'],r['retrieved_at_utc'],r['reason'])
 # Recover exact branch errors absent in aggregated rejection table.
 for r in rows('core','branches/operating_evidence/rejected_or_unavailable.csv'):
  i='branches__operating_evidence__'+r['dataset_id']
  for d in items:
   if d['item_id']==i:d['original_error']=r['exact_error'];d['kind']='http403' if '403' in r['exact_error'] else '404' if '404' in r['exact_error'] else 'unknown'
 for r in rows('core','branches/social_economy/rejected_or_unavailable.csv'):
  add(r['dataset_id'],r['source_url'],'core','branches/social_economy/rejected_or_unavailable.csv',r['error'],r['attempted_at_utc'],'Первичные население/доходы/ВРП; сравнение с перепубликацией',r['alternative'],relevance='NOT_NETWORK_RESOURCE_BOUNDARY' if r['status']=='LEAD' else 'CURRENT')
 for r in rows('alternative','modules/tourism/rejected_or_unavailable.csv'):
  if r['status']=='ACCESS_FAILED':add('tourism_'+r['item_id'],r['url'],'alternative','modules/tourism/rejected_or_unavailable.csv',r['exact_error'],purpose='Первичная туристическая статистика',workaround=r['consequence'])
 for r in rows('alternative','modules/business/rejected_or_unavailable.csv'):
  if r['status']=='ACCESS_FAILED':add(r['entry_id'],r['url'],'alternative','modules/business/rejected_or_unavailable.csv',r['reason'],purpose='Первичный корпоративный источник',workaround=r['next_use_or_boundary'])
 for r in rows('critic','rejected_or_unavailable.csv'):
  add('critic_'+r['dataset_id'],r['source_url'],'critic','rejected_or_unavailable.csv',r['error'],purpose='Проверка методологии/студенческих когорт',workaround=r['limitations'])
 r=next(r for r in rows('hypotheses','source_registry.csv') if r['dataset_id']=='HYP-S01')
 assert r['dataset_id']=='HYP-S01'
 add('HYP-S01',r['source_url'],'hypotheses','source_registry.csv','CERTIFICATE_VERIFY_FAILED: expired certificate',r['retrieved_at_utc'],'RU аэропорты','Официально указанный GitHub-hosted upstream airports.csv уже получен HYP-S03.')
 rel='product_probe_v1/air_offer/receipts/availability_07_14_dec2026.json';r=json.loads(blob('alternative',rel))
 body=[['get-availability',r['request_parameters']]]
 add('azimuth_availability',r['source_url'],'alternative',rel,r['error'],r['retrieved_at_utc'],'Цена и кресла KVX–MRV RT 7–14 декабря 2026','UNKNOWN; рекламные 2688 RUB для ноября не использованы как декабрьская оферта.',method='POST',body=body)
 rel='product_probe_v1/receipts/azimuth_config_20261109.json';r=json.loads(blob('alternative',rel))
 add('azimuth_config',r['source_url'],'alternative',rel,r['error'],r['retrieved_at_utc'],'Конфигурация booking frontend; вспомогательный путь','Статический JS доступен; config не является ценой.')
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only',PINS['alternative'],'context/16_agent_research/alternative/product_probe_v1/ground_transfer/receipts'],text=True).splitlines()
 for path in paths:
  rel=path.split('alternative/',1)[1];r=json.loads(blob('alternative',rel));status=r.get('status')
  if r.get('error') or isinstance(status,int) and status>=400:
   add('ground_'+r['source_id'],r['url'],'alternative',rel,r.get('error','HTTP '+str(status)),r.get('started_utc',''),'C14: первичный поезд/наземный трансфер','Частичные прямые СКППК и отдельные вторичные train-строки; полный продукт UNKNOWN.')
 # Known resolved/invalid cases are explicit inventory entries, never silently retried.
 for d in items:
  if d['item_id']=='favt_2026_sep_stats':d['relevance']='INVALID_GUESSED_URL'
 # Safe replacement URLs are additional read actions linked to old failures.
 for i,url,purpose,parent in [
 ('uvt_current','https://www.uvtaero.ru/raspisanie','Действующий путь расписания ЮВТ','branches__operating_evidence__uvt_schedule'),
 ('azimuth_current','https://azimuth.ru/ru/schedule','Действующий путь табло Азимута','branches__operating_evidence__azimuth_schedule'),
 ('case_brief','https://mai-way.ru/tasks/red-wings/','Задание кейса: web.open был недоступен, urllib ранее сработал','source_access_R01')]:
  add(i,url,'hypotheses' if i=='case_brief' else 'core','contributions/source_access/rejected_or_unavailable.csv' if i=='case_brief' else 'branches/operating_evidence/source_registry.csv','native web URL not accessible' if i=='case_brief' else 'Original path HTTP404; replacement acquired earlier',purpose=purpose,workaround='Заменённый путь уже дал исходник; повторная проверка не доказывает Wi-Fi cause.');items[-1]['parent_item']=parent
 save('plan.json',items)
 save('pinned_references.json',list({(r['source_sha'],r['path']):r for r in REFERENCES}.values()))
 print('planned',len(items),flush=True)
 return items
HEADERS={'content-type','content-length','date','last-modified','etag','cache-control','location'}
LIMIT=25*1024*1024
LOCKS={};LOCK=threading.Lock()
def encode_url(u):
 p=urllib.parse.urlsplit(u)
 return urllib.parse.urlunsplit((p.scheme,p.netloc,urllib.parse.quote(p.path,safe='/%:@'),urllib.parse.quote(p.query,safe='=&%+,;:/?@'),p.fragment))
def held_bytes(b):
 # Never publish full documents; strip hidden form values in held HTML too.
 if b'<html' not in b[:5000].lower() and b'<!doctype html' not in b[:5000].lower():return b
 t=b.decode('utf-8',errors='replace')
 def hidden(m):
  tag=m.group(0)
  if re.search(r"type\s*=\s*[\"']hidden[\"']",tag,re.I):
   return re.sub(r"value\s*=\s*([\"']).*?\1",'value=""',tag,flags=re.I|re.S)
  return tag
 t=re.sub(r'<input\b[^>]*>',hidden,t,flags=re.I|re.S)
 def meta(m):
  tag=m.group(0)
  if re.search(r'(csrf|xsrf)',tag,re.I):return re.sub(r"content\s*=\s*([\"']).*?\1",'content=""',tag,flags=re.I|re.S)
  return tag
 return re.sub(r'<meta\b[^>]*>',meta,t,flags=re.I|re.S).encode('utf-8')
def fetch_one(d):
 i=d['item_id'];r=dict(item_id=i,source_url=d['source_url'],method=d['method'],request_started_at_utc=stamp(),collector_version='network-recovery-public-v1',tls_verification=True,headers_whitelist=sorted(HEADERS))
 if d['relevance'] in ['INVALID_GUESSED_URL','NOT_NETWORK_RESOURCE_BOUNDARY']:
  r.update(status='NOT_APPLICABLE',reason=d['relevance'],completed_at_utc=stamp());save('receipts/'+i+'.json',r);return r
 host=urllib.parse.urlsplit(d['source_url']).netloc
 with LOCK:hostlock=LOCKS.setdefault(host,threading.Lock())
 with hostlock:
  data=json.dumps(d['request_body'],ensure_ascii=False).encode() if d.get('request_body') else None
  h={'User-Agent':'Mozilla/5.0 (compatible; PublicResearchRecovery/1.0)','Accept-Encoding':'identity'}
  if data is not None:h['Content-Type']='application/json';r['request_parameters']=d['request_body']
  try:
   req=urllib.request.Request(encode_url(d['source_url']),data=data,headers=h,method=d['method'])
   try:res=urllib.request.urlopen(req,timeout=25)
   except urllib.error.HTTPError as e:res=e;r['error']=f'HTTPError: {e.code} {e.reason}'
   r['http_status']=res.status;r['final_url']=res.geturl();r['response_headers']={k.lower():v for k,v in res.headers.items() if k.lower() in HEADERS}
   length=res.headers.get('Content-Length')
   if length and int(length)>LIMIT:r.update(status='SIZE_LIMIT',announced_bytes=int(length));res.close()
   else:
    b=res.read(LIMIT+1);res.close()
    if len(b)>LIMIT:r.update(status='SIZE_LIMIT',read_at_least_bytes=len(b))
    else:
     digest=hashlib.sha256(b).hexdigest();raw=ROOT/'raw_hold'/f'{i}.bin';raw.parent.mkdir(exist_ok=True);stored=held_bytes(b);raw.write_bytes(stored)
     r.update(status='FETCHED' if 200<=r['http_status']<300 else 'HTTP_ERROR',sha256=digest,size_bytes=len(b),raw_path=str(raw.relative_to(ROOT)),raw_publication='LOCAL_HOLD_IGNORED',format_signature=b[:8].hex(),stored_sha256=hashlib.sha256(stored).hexdigest(),stored_size_bytes=len(stored),storage_transform='Strip hidden form values and csrf meta content in held HTML; otherwise unchanged')
  except Exception as e:r.update(status='ACCESS_FAILED',error=f'{type(e).__name__}: {e}')
  r['completed_at_utc']=stamp();save('receipts/'+i+'.json',r)
  print(i,r['status'],r.get('http_status',''),r.get('size_bytes',''),flush=True)
  return r
if __name__=='__main__':
 items=make_plan() if '--plan' in sys.argv else json.loads((ROOT/'plan.json').read_text())
 if '--fetch' in sys.argv:
  print('disk_free_bytes',shutil.disk_usage(ROOT).free,'max_file',LIMIT,'workers',3,flush=True)
  todo=[d for d in items if not (ROOT/'receipts'/(d['item_id']+'.json')).exists()]
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(fetch_one,todo))
