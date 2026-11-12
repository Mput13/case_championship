import urllib.request,concurrent.futures,json,pathlib,hashlib,datetime
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).parent
urls={
'KHV_SCHEDULE':'https://khvaero.ru/passengers/schedule/',
'KHV_WINTER':'https://khv.aero/airport/news/osenne-zimnee-raspisanie-aeroporta-khabarovsk-rasshirenie-reysov-v-kitay-sovremennye-istoricheskie-m/',
'KHV_TECH':'https://khvaero.ru/airport/about/obshchaya-informatsiya/',
'KHV_2025':'https://khv.aero/airport/news/v-mezhdunarodnom-aeroportu-khabarovsk-podveli-itogi-raboty-za-2025-god/',
'KHV_TRANSFER':'https://khv.aero/airport/news/zona-transfera-v-aeroportu-khabarovsk-prinyala-pervykh-passazhirov/',
'KHV_CARRIERS':'https://khv.aero/airport/companies/?c=russian',
'RW_WINTER':'https://flyredwings.com/press/news/red-wings-perexodit-na-zimnee-raspisanie/',
}
class Txt(HTMLParser):
 def __init__(self):super().__init__();self.a=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ['script','style']:self.skip+=1
  if t in ['p','br','div','tr','h1','h2','li']:self.a.append('\n')
 def handle_endtag(self,t):
  if t in ['script','style']:self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip():self.a.append(d.strip()+' ')
def fetch(it):
 sid,url=it;now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 try:
  res=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=45);b=res.read(); p=ROOT/'sources'/f'{sid}.html';p.write_bytes(b)
  txt=Txt();txt.feed(b.decode('utf-8',errors='replace'));(ROOT/'sources'/f'{sid}.txt').write_text('\n'.join(x.strip() for x in ''.join(txt.a).splitlines() if x.strip())+'\n')
  return dict(source_id=sid,url=url,final_url=res.url,http_status=res.status,observed_at=now,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),local_path=str(p.relative_to(ROOT)))
 except Exception as e:return dict(source_id=sid,url=url,observed_at=now,status='FAILED',error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:rs=list(ex.map(fetch,urls.items()))
(ROOT/'fetch_receipts.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2)+'\n')
for r in rs:print(r['source_id'],r.get('http_status',r.get('error')),r.get('bytes'))
