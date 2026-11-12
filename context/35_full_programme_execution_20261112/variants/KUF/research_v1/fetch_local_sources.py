import pathlib,json,hashlib,datetime,urllib.request,concurrent.futures,re
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parent
URLS={
'KUF-2025':'https://ar-kuf.ru/about/news/itogi-raboty-v-novogodnie-prazdnik/',
'KUF-TECH':'https://ar-kuf.ru/partners/airlines/airport/',
'KUF-SLOTS':'https://ar-kuf.ru/partners/airlines/koordinatsiya-raspisaniya/',
'KUF-SUPPORT':'https://ar-kuf.ru/partners/airlines/support/',
'KUF-BUS':'https://ar-kuf.ru/how-to-get/to/bus/',
'KUF-SCHEDULE':'https://ar-kuf.ru/schedule/',
'KUF-SCHEDULE-ARR':'https://ar-kuf.ru/schedule/?type=arr',
'KUF-NEWS':'https://ar-kuf.ru/about/news/',
'KUF-SUKHUM':'https://ar-kuf.ru/about/news/pervyy-reys-iz-samary-v-sukhum/',
'RW-WINTER':'https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/',
'KUF-MRO':'https://yakovlev.ru/press-centre/releases/yakovlev-zapustil-lineynuyu-stantsiyu-tekhnicheskogo-obsluzhivaniya-samoletov-ssj-100-v-aeroportu-sa/',
'KUF-TERMINAL':'https://ar-kuf.ru/partners/airlines/terminal/',
'KUF-PRICELISTS':'https://ar-kuf.ru/partners/airlines/pricelist/'
}
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[];self.links=[];self.rows=[];self.row=None;self.cell=None;self.cells=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ['script','style','noscript']:self.skip+=1
  if tag=='a' and 'href' in a:self.links.append(a['href'])
  if tag=='tr':self.row=[]
  if tag in ['td','th'] and self.row is not None:self.cell=[]
  if tag in ['p','div','br','h1','h2','h3','tr','li']:self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ['script','style','noscript']:self.skip=max(0,self.skip-1)
  if tag in ['td','th'] and self.cell is not None:
   if self.row is not None:self.row.append(' '.join(' '.join(self.cell).split()))
   self.cell=None
  if tag=='tr' and self.row is not None:
   if self.row:self.rows.append(self.row)
   self.row=None
 def handle_data(self,data):
  if not self.skip:
   self.parts.append(data)
   if self.cell is not None:self.cell.append(data)
def get(item):
 sid,url=item;now=datetime.datetime.now(datetime.timezone.utc).isoformat();r={'source_id':sid,'url':url,'retrieved_at':now,'method':'public_HTTP_GET_no_auth_no_browser'}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research text reader'}),timeout=30) as f:raw=f.read();r.update(final_url=f.url,http_status=f.status,raw_sha256=hashlib.sha256(raw).hexdigest(),raw_bytes=len(raw))
  p=Parser();p.feed(raw.decode('utf-8','replace'));text='\n'.join(s.strip() for s in ''.join(p.parts).splitlines() if s.strip());path=ROOT/'sources'/(sid+'.txt');path.write_text(text);r.update(status='FETCHED',text_path=str(path.relative_to(ROOT)),text_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),links=sorted(set(p.links)))
  if p.rows:
   tpath=ROOT/'sources'/(sid+'_tables.json');tpath.write_text(json.dumps(p.rows,ensure_ascii=False,indent=2));r['table_path']=str(tpath.relative_to(ROOT));r['table_sha256']=hashlib.sha256(tpath.read_bytes()).hexdigest()
 except Exception as e:r.update(status='FETCH_FAILED',error=repr(e))
 return r
if __name__=='__main__':
 receipts=list(concurrent.futures.ThreadPoolExecutor(max_workers=5).map(get,URLS.items()))
 (ROOT/'source_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2))
 for r in receipts:print(r['source_id'],r['status'],r.get('raw_bytes',r.get('error')))
