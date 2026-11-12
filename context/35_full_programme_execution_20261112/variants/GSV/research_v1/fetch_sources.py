"""Небольшой воспроизводимый HTTP-сбор только местных открытых источников GSV."""
import json,hashlib,pathlib,urllib.request,urllib.parse,datetime,concurrent.futures
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parent
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.links=[];self.skip=0;self.anchor=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('script','style'):self.skip+=1
  if tag=='a':self.anchor=[a.get('href',''),'']
  if tag in ('p','div','li','tr','h1','h2','h3','br'):self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ('script','style') and self.skip:self.skip-=1
  if tag=='a' and self.anchor:self.links.append(self.anchor);self.anchor=None
  if tag in ('p','div','li','tr','h1','h2','h3'):self.parts.append('\n')
 def handle_data(self,s):
  if not self.skip:
   self.parts.append(s)
   if self.anchor:self.anchor[1]+=s
SOURCES={
'GSV-NEWS':'https://ar-gsv.ru/about/news/',
'GSV-TBS':'https://ar-gsv.ru/about/news/iz-aeroport-gagarin-otkryvaetsya-reys-v-tbilisi/',
'GSV-BUS':'https://ar-gsv.ru/about/news/iz-aeroporta-gagarin-otkrylis-reysy-v-gruziyu-/',
'GSV-H12026':'https://ar-gsv.ru/about/news/v-aeroportu-gagarin-vyros-passazhiropotok-na-mezhdunarodnykh/',
'GSV-WINTER':'https://ar-gsv.ru/partners/about/news/gagarin-perekhodit-na-zimnee-raspisanie/',
'GSV-TECH':'https://ar-gsv.ru/partners/airlines/airport/',
'GSV-TERMINAL':'https://ar-gsv.ru/partners/airlines/terminal/',
'GSV-SUPPORT':'https://ar-gsv.ru/partners/airlines/support/',
'GSV-CONTACTS':'https://ar-gsv.ru/partners/airlines/contacts/',
'GSV-SLOTS':'https://ar-gsv.ru/partners/airlines/schedule/',
'GSV-INFO':'https://ar-gsv.ru/about/info/',
'GSV-GROUND':'https://ar-gsv.ru/how-to-get/',
'GSV-ARCHIVE':'https://ar-gsv.ru/about/news/?year=2026',
'GSV-TIMETABLE':'https://ar-gsv.ru/schedule/'
}
def fetch(item):
 sid,url=item;record={'source_id':sid,'requested_url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research text fetch'}),timeout=25) as r:
   b=r.read();record.update(status=r.status,final_url=r.url,content_type=r.headers.get('Content-Type'),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  ext='.pdf' if b[:4]==b'%PDF' else '.html';dest=ROOT/'sources'/f'{sid}{ext}';dest.parent.mkdir(exist_ok=True);dest.write_bytes(b);record['local_path']=str(dest.relative_to(ROOT))
  if ext=='.html':
   p=Parser();p.feed(b.decode('utf-8',errors='replace'));lines=[' '.join(x.split()) for x in ''.join(p.parts).splitlines() if x.strip()];(dest.with_suffix('.txt')).write_text('\n'.join(lines)+'\n');record['text_path']=str(dest.with_suffix('.txt').relative_to(ROOT));record['links']=[{'url':urllib.parse.urljoin(url,h),'label':' '.join(t.split())} for h,t in p.links]
 except Exception as e:record.update(status='FETCH_FAILED',error=repr(e))
 return record
if __name__=='__main__':
 current=json.loads((ROOT/'fetch_receipts.json').read_text()) if (ROOT/'fetch_receipts.json').exists() else []
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:new=list(pool.map(fetch,SOURCES.items()))
 by={r['source_id']:r for r in current};by.update({r['source_id']:r for r in new});(ROOT/'fetch_receipts.json').write_text(json.dumps(list(by.values()),ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{k:r.get(k) for k in ('source_id','status','bytes','error')} for r in new],ensure_ascii=False))
