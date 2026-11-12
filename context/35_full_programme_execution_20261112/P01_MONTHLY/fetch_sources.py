#!/usr/bin/env python3
"""Загрузка только публичных источников; receipts сохраняют точные ошибки и хеши."""
import urllib.request,urllib.parse,concurrent.futures,json,hashlib,datetime,pathlib,sys
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parent
class Text(HTMLParser):
 def __init__(self):super().__init__();self.text=[];self.links=[];self.link=None;self.skip=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ['script','style']:self.skip+=1
  if tag=='a' and 'href' in a:self.link={'href':a['href'],'text':''}
  if tag in ['p','div','br','tr','li','h1','h2','h3','article','item']:self.text.append('\n')
 def handle_endtag(self,tag):
  if tag in ['script','style']:self.skip=max(0,self.skip-1)
  if tag=='a' and self.link:self.links.append(self.link);self.link=None
 def handle_data(self,data):
  if not self.skip:self.text.append(data)
  if self.link:self.link['text']+=data

def fetch(spec):
 k,u=spec['source_id'],spec['url'];p=ROOT/'sources_receipts';p.mkdir(exist_ok=True)
 rec={'source_id':k,'url':u,'accessed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (compatible; research-read-only/1.0)'})
  with urllib.request.urlopen(req,timeout=25) as r:b=r.read();rec.update(http_status=r.status,final_url=r.url,content_type=r.headers.get('Content-Type',''))
  ext='.json' if 'json' in rec['content_type'] else '.xml' if 'xml' in rec['content_type'] or b.startswith(b'<?xml') else '.pdf' if b.startswith(b'%PDF') else '.xlsx' if b.startswith(b'PK') else '.xls' if b.startswith(bytes.fromhex('D0CF11E0')) else '.html'
  f=k+ext;(p/f).write_bytes(b);rec.update(status='FETCHED',sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),raw_file=f)
  if ext in ['.html','.xml','.json']:
   t=Text();t.feed(b.decode('utf-8',errors='replace'));txt='\n'.join(' '.join(x.split()) for x in ''.join(t.text).splitlines() if x.strip());(p/(k+'.txt')).write_text(txt);(p/(k+'_links.json')).write_text(json.dumps(t.links,ensure_ascii=False,indent=2));rec['text_file']=k+'.txt';rec['links_file']=k+'_links.json'
 except Exception as e:rec.update(status='ACCESS_ERROR',error=type(e).__name__+': '+str(e))
 (p/(k+'_receipt.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');return rec
if __name__=='__main__':
 specs=json.loads(pathlib.Path(sys.argv[1]).read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
  for r in ex.map(fetch,specs): print(json.dumps(r,ensure_ascii=False))
