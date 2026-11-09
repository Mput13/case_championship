#!/usr/bin/env python3
"""Small public HTTP samples. Default TLS validation; no auth or retry. Stdlib only."""
from pathlib import Path
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import csv, hashlib, json, urllib.request, datetime, argparse
ROOT=Path(__file__).resolve().parent.parent
class Text(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[]
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
  if t in ('p','div','h1','h2','h3','li','tr','section','br'):self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)
 def result(self):return '\n'.join(x.strip() for x in ''.join(self.parts).splitlines() if x.strip())+'\n'
def acquire(s):
 row=dict(s);row.update(retrieved_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),collector_version='acquire.py/1',command='python3 context/16_agent_research/hypotheses/contributions/source_access/collectors/acquire.py',license='UNKNOWN',record_count=None,acquisition_status='ACCESS_FAILED',raw_path=None,sha256=None,byte_size=None)
 try:
  req=urllib.request.Request(s['source_url'],headers={'User-Agent':'Mozilla/5.0 (compatible; public research)'})
  with urllib.request.urlopen(req,timeout=35) as f:
   b=f.read(5_000_001)
   if len(b)>5_000_000:raise ValueError('Sample exceeds 5 MB cap; not retained')
   name='raw/'+s['dataset_id']+'.html';(ROOT/name).write_bytes(b)
   row.update(raw_path=name,sha256=hashlib.sha256(b).hexdigest(),byte_size=len(b),http_status=f.status,final_url=f.url,headers=dict(f.headers),acquisition_status='ACQUIRED_RAW',record_count=1)
   txt=Text();txt.feed(b.decode(f.headers.get_content_charset() or 'utf-8',errors='replace'))
   text_path='raw/'+s['dataset_id']+'.txt';(ROOT/text_path).write_text(txt.result());row['text_path']=text_path;row['text_sha256']=hashlib.sha256((ROOT/text_path).read_bytes()).hexdigest()
 except Exception as e:row['error']=repr(e)
 (ROOT/('raw/'+s['dataset_id']+'_receipt.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
 return row
if __name__=='__main__':
 sources=json.loads((ROOT/'sources.json').read_text())
 with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(acquire,sources))
 (ROOT/'dataset_manifest.json').write_text(json.dumps({'schema_version':'1.0','path_base':str(ROOT),'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'datasets':rows},ensure_ascii=False,indent=2)+'\n')
 fields=['dataset_id','source_url','organisation','publication_date','grain','geographic_coverage','temporal_coverage','join_keys','units','license','acquisition_status','retrieved_at_utc','raw_path','sha256','byte_size','record_count','collector_version','command','limitations','error']
 with (ROOT/'source_registry.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
 for r in rows:print(r['dataset_id'],r['acquisition_status'],r.get('byte_size'),r.get('error',''))
