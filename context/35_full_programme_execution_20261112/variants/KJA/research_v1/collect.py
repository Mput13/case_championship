from pathlib import Path
import subprocess, csv, io, json, hashlib, urllib.request, datetime, concurrent.futures
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parent
BASE='context/35_full_programme_execution_20261112/'
PINS={'AUTHOR':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63','P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
def dump(p,obj):
 p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def gitread(pkg,path):
 return subprocess.check_output(['git','show',PINS[pkg]+':'+path])
def matched(r):
 return any(v=='KJA' or 'Красноярск'==v or (k in ['market_id','itinerary','path','route','geography_or_airport'] and 'KJA' in v) for k,v in r.items() if v)
def extract():
 selections={'AUTHOR':['data/manual/known_flows.csv','data/manual/rw_routes_now.csv','data/manual/longlist_manual.csv','data/manual/airport_tech.csv','data/processed/network_routes.csv'],
 'P02':[BASE+'P02/'+f for f in ['city_coverage.csv','market_coverage.csv','competitor_products.csv','fare_panel.csv','historical_demand_context.csv','historical_route_context.csv','physical_adjacent_leg_candidates.csv','ordered_itineraries.csv']],
 'P03':[BASE+'P03/airport_constraints.csv'],
 'P04':[BASE+'P04/'+f for f in ['airport_coverage.csv','cost_ranges.csv','thresholds.csv']]}
 manifest=[]
 for pkg,paths in selections.items():
  for path in paths:
   raw=gitread(pkg,path);rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
   selected=[]
   for n,r in enumerate(rows,2):
    if matched(r) or (pkg=='P04' and path.endswith('thresholds.csv')):
     canonical=json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
     selected.append({'source_csv_line':n,'source_row_sha256':hashlib.sha256(canonical).hexdigest(),**r})
   out='inputs/'+pkg+'_'+Path(path).name
   if selected:
    p=ROOT/out;p.parent.mkdir(exist_ok=True)
    with p.open('w') as f:
     w=csv.DictWriter(f,fieldnames=list(selected[0]));w.writeheader();w.writerows(selected)
   manifest.append({'source_id':'PIN-'+pkg+'-'+Path(path).stem,'commit':PINS[pkg],'path':path,'git_blob':subprocess.check_output(['git','rev-parse',PINS[pkg]+':'+path],text=True).strip(),'sha256':hashlib.sha256(raw).hexdigest(),'source_rows':len(rows),'selected_rows':len(selected),'selection':'KJA endpoints/city, not any mention in a coverage list; P04 thresholds all named rows','extract_path':out if selected else None})
 for pkg,path in [('P06',BASE+'P06/producer_contract.json'),('P06',BASE+'P06/README.md'),('P04',BASE+'P04/event_rate_map.csv'),('P00R','context/34_full_programme_plan_20261112/variant_research_plan.json'),('P00R','context/34_full_programme_plan_20261112/common_spec.json')]:
  raw=gitread(pkg,path)
  manifest.append({'source_id':'PIN-'+pkg+'-'+Path(path).stem,'commit':PINS[pkg],'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'extract_path':None,'read_only_reference':True})
 dump('source_pins.json',{'pins':PINS,'files':manifest,'rule':'No moving ref reads; source row hash is UTF8 canonical sorted JSON of parsed source row; line is CSV record index+2, not physical multiline offset.'})

class Plain(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[];self.links=[]
 def handle_starttag(self,t,a):
  if t in ['script','style','noscript']:self.skip+=1
  if t in ['p','div','br','li','h1','h2','h3','tr']:self.parts.append('\n')
  if t=='a':self.links.extend(v for k,v in a if k=='href')
 def handle_endtag(self,t):
  if t in ['script','style','noscript'] and self.skip:self.skip-=1
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)
def fetch_one(item):
 sid,url=item;now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r={'source_id':sid,'url':url,'retrieved_at_system_clock':now,'task_as_of':'2026-11-12','clock_note':'task as_of supplied by coordinator; system retrieval clock retained separately'}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research; public text)'})
  with urllib.request.urlopen(req,timeout=35) as q:
   limit=16000000 if sid=='KJA-SCHEDULE' else 2500000
   raw=q.read(limit);r.update(http_status=q.status,final_url=q.url,content_type=q.headers.get('Content-Type'),raw_bytes=len(raw),read_limit=limit,potentially_truncated=len(raw)==limit)
  r['raw_sha256']=hashlib.sha256(raw).hexdigest();p=Plain();p.feed(raw.decode('utf-8',errors='replace'))
  txt='\n'.join(x.strip() for x in ''.join(p.parts).splitlines() if x.strip())
  dest=ROOT/'sources'/f'{sid}.txt';dest.parent.mkdir(exist_ok=True);dest.write_text(txt)
  r.update(text_path=str(dest.relative_to(ROOT)),text_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),status='FETCHED_TEXT',links=p.links)
 except Exception as e:r.update(status='FETCH_ERROR',error=repr(e))
 return r
def fetch(items):
 receipts_path=ROOT/'fetch_receipts.json';receipts=json.loads(receipts_path.read_text()) if receipts_path.exists() else []
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:results=list(ex.map(fetch_one,items))
 receipts.extend(results);dump('fetch_receipts.json',receipts)
 for r in results: print(r['source_id'],r['status'],r.get('error',''),r.get('text_path',''))

if __name__=='__main__':
 extract()
 fetch([
 ('KJA-2025','https://team.kja.aero/media/aeroport-krasnoyarsk-po-itogam-2025-goda-1-1'),
 ('KJA-ABOUT','https://team.kja.aero/about'),
 ('KJA-PASSENGER','https://www.kja.aero/'),
 ('KJA-GROUND','https://travel.kja.aero/how-to-get'),
 ('KRASAVIA-NEWS','https://www.krasavia.ru/news/'),
 ('FAVT-LOCAL26','https://kras-m.favt.ru/novosti-novosti/?id=11977'),
 ('RW-ABOUT','https://flyredwings.com/about/'),
 ('RW-WINTER','https://flyredwings.com/press/news/red-wings-perekhodit-na-zimnee-raspisanie/'),
 ])
