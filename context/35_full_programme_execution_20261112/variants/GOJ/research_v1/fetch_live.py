"""Public text HTTP reads, no browser/account/booking calls."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib,json,pathlib,urllib.request,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
SOURCES={
 'GOJ-L01':'https://ar-goj.ru/about/news/volga-avia-nachala-provodit-tekhnicheskoe-obsluzhivanie-samo/',
 'GOJ-L02':'https://ar-goj.ru/partners/airlines/airport/',
 'GOJ-L03':'https://ar-goj.ru/partners/airlines/kharakteristiki-terminala/',
 'GOJ-L04':'https://ar-goj.ru/partners/airlines/support/',
 'GOJ-L05':'https://ar-goj.ru/partners/airlines/schedule/',
 'GOJ-L06':'https://ar-goj.ru/about/news/za-2025-god-vyroslo-kolichestvo-nizhegorodtsev-letavshikh-za/',
 'GOJ-L07':'https://ar-goj.ru/about/news/aaeroport-chkalov-perekhodit-na-osenne-zimnee-raspisanie/',
 'GOJ-L08':'https://ar-goj.ru/schedule/',
 'GOJ-L09':'https://ar-goj.ru/schedule/?type=arr',
 'GOJ-L10':'https://ar-goj.ru/partners/airlines/pricelists/',
 'GOJ-L11':'https://ar-goj.ru/about/news/iz-nizhnego-novgoroda-vozobnovlyayutsya-reysy-v-murmansk/',
 'GOJ-L12':'https://flyredwings.com/cities/539/',
 'GOJ-L13':'https://ar-goj.ru/how-to-get/to/bus/',
 'GOJ-L14':'https://uvtaero.ru/raspisanie',
 'GOJ-L15':'https://ar-goj.ru/partners/airlines/koordinatsiya-raspisaniya/',
 'GOJ-L16':'https://ar-goj.ru/upload/iblock/f23/jntigq6a94zp75azjwp229k4hatob3sg/Preyskurant-na-uslugi-i-tovary-AO-MANN-dlya-rossiyskikh-potrebiteley-uslug-i-potrebiteley-uslug-Respubliki-Belarus-s-21.12.2025-_.pdf',
 'GOJ-L17':'https://ar-goj.ru/rules/kontrol-bezopasnosti/',
 'GOJ-L18':'https://cipr.ru/',
 'GOJ-L19':'https://omk.ru/press/gallery/',
 'GOJ-L20':'https://cipr.ru/news/konferencziya-czipr-i-gorodskoj-festival-teh-frendli-vikend-projdut-v-nizhnem-novgorode-s-31-maya-po-5-iyunya-2027-goda/',
}
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.out=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag in ['script','style','noscript']:self.skip+=1
  if tag in ['p','div','tr','h1','h2','li','br','td']:self.out.append('\n')
  if tag=='a':
   a=dict(attrs)
   if a.get('href'):self.links.append(a['href'])
 def handle_endtag(self,tag):
  if tag in ['script','style','noscript']:self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip:self.out.append(data)
def fetch(item):
 sid,url=item;record={'source_id':sid,'url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'method':'public_text_HTTP_GET','organization':'АО МАНН' if 'ar-goj.ru' in url else 'Red Wings' if 'flyredwings' in url else 'Организатор ЦИПР' if 'cipr.ru' in url else 'ОМК' if 'omk.ru' in url else 'ЮВТ Аэро'}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research; public text read)'})
  with urllib.request.urlopen(req,timeout=35) as response:b=response.read();record.update(http_status=response.status,final_url=response.url)
  if url.endswith('.pdf'):
   path=ROOT/'live'/f'{sid}.pdf';path.parent.mkdir(exist_ok=True);path.write_bytes(b)
   t=subprocess.run(['pdftotext','-layout','-','-'],input=b,stdout=subprocess.PIPE,check=True).stdout
   text_path=path.with_suffix('.txt');text_path.write_bytes(t)
   record.update(status='READ_PUBLIC_PDF',raw_sha256=hashlib.sha256(b).hexdigest(),path=str(path.relative_to(ROOT)),text_path=str(text_path.relative_to(ROOT)),text_sha256=hashlib.sha256(t).hexdigest(),effective_from='2026-11-16',guard='announced_future_revision_at_2026-11-12;refresh_applicability_on_new_read')
   return record
  p=Parser();p.feed(b.decode('utf-8','replace'));t='\n'.join(' '.join(x.split()) for x in ''.join(p.out).splitlines() if x.strip())+'\n'
  path=ROOT/'live'/f'{sid}.txt';path.parent.mkdir(exist_ok=True);path.write_text(t)
  record.update(status='READ_PUBLIC_TEXT',raw_sha256=hashlib.sha256(b).hexdigest(),text_sha256=hashlib.sha256(t.encode()).hexdigest(),text_path=str(path.relative_to(ROOT)),links=[x for x in p.links if any(v in x for v in ['.pdf','schedule','koordin','pricelist'])][:35])
 except Exception as e:record.update(status='ACCESS_FAILED_NOT_DISPROOF',error=repr(e))
 return record
if __name__=='__main__':
 receipts=list(ThreadPoolExecutor(max_workers=5).map(fetch,SOURCES.items()))
 (ROOT/'live_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
 for r in receipts:print(r['source_id'],r['status'],r.get('error',''),r.get('links',[]) if r['source_id'] in ['GOJ-L05','GOJ-L10'] else '')
