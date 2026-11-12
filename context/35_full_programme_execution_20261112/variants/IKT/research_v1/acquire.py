import urllib.request,urllib.parse,pathlib,hashlib,json,datetime,concurrent.futures
from html.parser import HTMLParser
class Page(HTMLParser):
 def __init__(self):super().__init__();self.text=[];self.links=[];self.href=None;self.label=[];self.skip=0
 def handle_starttag(self,t,a):
  a=dict(a)
  if t in ['script','style']:self.skip+=1
  if t=='a':self.href=a.get('href');self.label=[]
 def handle_endtag(self,t):
  if t in ['script','style']:self.skip=max(0,self.skip-1)
  if t=='a' and self.href is not None:self.links.append({'text':' '.join(self.label),'url':self.href});self.href=None
 def handle_data(self,d):
  if not self.skip and d.strip():self.text.append(d.strip())
  if self.href is not None:self.label.append(d.strip())
ROOT=pathlib.Path(__file__).resolve().parent
S={
'IKT_NEWS':'https://iktport.ru/ru/about/novosti/',
'IKT_AIRLINES':'https://iktport.ru/ru/passengers/airlines',
'IKT_PARTNERS':'https://iktport.ru/ru/partners/forairlines',
'IKT_RATES_INDEX':'https://iktport.ru/ru/partners/prejskuranty',
'IKT_ROUTES':'https://iktport.ru/ru/passengers/routes-ru',
'IKT_ABOUT':'https://iktport.ru/ru/about/mezhdunarodnyj-aeroport-irkutsk',
'IKT_MARKETING':'https://iktport.ru/documents/marketing/marketing_standart_2026.pdf',
'RW_NOZ_HISTORY':'https://flyredwings.com/press/news/red-wings-dostavit-zhitelej-kuzbassa-k-beregam-bajkala/',
'S7_MRO':'https://www.s7technics.ru/',
'IKT_2025_SECONDARY':'https://38rus.com/more/110166'
}
def fetch(k,u):
 d={'source_id':k,'url':u,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as r:b=r.read();d.update(http_status=r.status,final_url=r.url,content_type=r.headers.get('Content-Type'))
  ext='.pdf' if b.startswith(b'%PDF') else '.html'; p=ROOT/'sources'/(k+ext);p.parent.mkdir(exist_ok=True);p.write_bytes(b);d.update(sha256=hashlib.sha256(b).hexdigest(),path=str(p.relative_to(ROOT)),bytes=len(b))
  if ext=='.html':
   page=Page();page.feed(b.decode('utf-8',errors='replace'));links=[{'text':a['text'],'url':urllib.parse.urljoin(u,a['url'])} for a in page.links];(ROOT/'sources'/(k+'_links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2));(ROOT/'sources'/(k+'.txt')).write_text('\n'.join(page.text))
 except Exception as e:d['error']=str(e)
 return d
if __name__=='__main__':
 import sys
 if len(sys.argv)>1:S=json.loads((ROOT/sys.argv[1]).read_text())
 rs=list(concurrent.futures.ThreadPoolExecutor(max_workers=5).map(lambda kv:fetch(*kv),S.items())); old=ROOT/'fetch_receipts.json'; data=json.loads(old.read_text()) if old.exists() else []; data.extend(rs);old.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print(json.dumps(rs,ensure_ascii=False,indent=2))
