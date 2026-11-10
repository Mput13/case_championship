#!/usr/bin/env python3
"""Read-only HTTP capture. Writes only evidence/raw/web, retains errors and hash."""
import concurrent.futures,datetime,hashlib,json,pathlib,subprocess,urllib.request
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parent
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0;self.links=[]
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
  if t=='a':self.links.extend(v for k,v in a if k=='href')
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip():self.parts.append(' '.join(d.split()))
def capture(item):
 ident,url=item
 folder=ROOT/'raw/web'/ident;folder.mkdir(parents=True,exist_ok=True)
 r=dict(source_id=ident,url=url,retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; research evidence capture)'})
  with urllib.request.urlopen(req,timeout=20) as response:
   b=response.read(20_000_000);r.update(status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type',''))
  ext='pdf' if b.startswith(b'%PDF') else ('xlsx' if b.startswith(b'PK') and '.xlsx' in url else 'html')
  target=folder/('source.'+ext);target.write_bytes(b)
  r.update(raw_path=str(target.relative_to(ROOT)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  if ext=='pdf':subprocess.run(['pdftotext','-layout',str(target),str(folder/'text.txt')],check=True,capture_output=True)
  elif ext=='html':
   p=Text();p.feed(b.decode('utf-8',errors='replace'));(folder/'text.txt').write_text('\n'.join(p.parts)+'\n');(folder/'links.json').write_text(json.dumps(p.links,ensure_ascii=False,indent=2))
  if ext!='xlsx':
   text=(folder/'text.txt').read_bytes();r.update(text_path=str((folder/'text.txt').relative_to(ROOT)),text_sha256=hashlib.sha256(text).hexdigest())
 except Exception as e:r.update(error=type(e).__name__+': '+str(e))
 (folder/'receipt.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');return r
if __name__=='__main__':
 import sys
 items=json.loads(pathlib.Path(sys.argv[1]).read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  for r in pool.map(capture,items):print(json.dumps(r,ensure_ascii=False))
