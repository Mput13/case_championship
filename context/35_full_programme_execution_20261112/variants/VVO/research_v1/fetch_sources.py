"""Read-only public HTTP capture; outputs stay in this package. No browser/API purchases."""
import datetime, hashlib, json, re, urllib.request, urllib.parse
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parent
class Document(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[];self.links=[];self.link=None
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag in ['script','style','noscript']:self.skip+=1
  if tag=='a':self.link=[attrs.get('href',''),'']
  if tag in ['p','div','tr','br','li','h1','h2','h3','h4']:self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ['script','style','noscript']:self.skip=max(0,self.skip-1)
  if tag=='a' and self.link:self.links.append({'href':self.link[0],'text':self.link[1].strip()});self.link=None
  if tag in ['p','div','tr','li','h1','h2','h3','h4']:self.parts.append('\n')
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
  if self.link:self.link[1]+=data
 def text(self):return '\n'.join(re.sub(r'\s+',' ',x).strip() for x in ''.join(self.parts).splitlines() if x.strip())

def fetch(source_id,url):
 d=ROOT/'sources';d.mkdir(exist_ok=True)
 receipt_path=d/(source_id+'.receipt.json')
 if receipt_path.exists():return json.loads(receipt_path.read_text())
 receipt={'source_id':source_id,'requested_url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  safe_url=urllib.parse.quote(url,safe=":/?=&%+#@")
  req=urllib.request.Request(safe_url,headers={'User-Agent':'Mozilla/5.0 (research; public source capture)'})
  with urllib.request.urlopen(req,timeout=35) as response:
   raw=response.read();ct=response.headers.get('Content-Type','');receipt.update({'url':response.url,'http_status':response.status,'content_type':ct,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'status':'CAPTURED'})
  suffix='.pdf' if 'pdf' in ct or url.lower().endswith('.pdf') else ('.doc' if url.lower().endswith('.doc') else '.html')
  target=d/(source_id+suffix);target.write_bytes(raw);receipt['path']=str(target.relative_to(ROOT))
  if suffix=='.html':
   parser=Document();parser.feed(raw.decode('utf-8',errors='replace'));(d/(source_id+'.txt')).write_text(parser.text()+'\n');receipt['text_path']='sources/'+source_id+'.txt';receipt['links']=parser.links
 except Exception as exc:receipt.update({'status':'FETCH_FAILED','error':type(exc).__name__+': '+str(exc)})
 receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');return receipt

if __name__=='__main__':
 import sys
 r=fetch(sys.argv[1],sys.argv[2]);print(json.dumps({k:v for k,v in r.items() if k!='links'},ensure_ascii=False))
