from pathlib import Path
import urllib.request,hashlib,json,re,html,concurrent.futures,datetime
from html.parser import HTMLParser
B=Path(__file__).resolve().parent; (B/'sources').mkdir(exist_ok=True)
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ['script','style']:self.skip+=1
  if t in ['p','br','div','h1','h2','li']:self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ['script','style']:self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)
def plain(s):
 p=Text();p.feed(s);return '\n'.join(re.sub(r'\s+',' ',l).strip() for l in ''.join(p.parts).splitlines() if l.strip())
urls={
 'N01_RW_2021':'https://flyredwings.com/press/news/permskij-kraj-aviakompaniya-red-wings-i-mezhdunarodnyj-aeroport-permi-podpisali-soglashenie-o-sotrudnichestve/',
 'N02_RW_WINTER':'https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/',
 'N03_RW_MSQ':'https://flyredwings.com/press/news/red-wings-nachala-vypolnyat-polety-iz-permi-v-minsk/',
 'N04_RW_BUS':'https://flyredwings.com/press/news/red-wings-zapuskaet-novye-rejsy-v-batumi-iz-shesti-gorodov/',
 'N05_AIRPORT_2025':'https://t.me/s/permairport/327',
 'N06_AIRPORT_WINTER':'https://t.me/s/permairport/384',
 'N07_S7':'https://t.me/s/permairport/336',
 'N08_RW_COUNT':'https://t.me/s/permairport/343',
 'N09_UVT':'https://t.me/s/permairport/334',
 'N10_TAS':'https://t.me/s/permairport/370',
 'N11_AIRPORT_HOME':'https://aviaperm.ru/',
 'N12_DISCOUNT':'https://aviaperm.ru/upload/open_info/2022/skidki20222.pdf',
 'N13_REGION_ORDER':'https://mintrans.permkrai.ru/download.php?id=391929',
 'N14_NOVAPORT':'https://t.me/s/novaport_holding/469',
 'N15_NOVAPORT_APRON':'https://t.me/s/novaport_holding/219',
 'N16_RW_SALE':'https://flyredwings.com/november-sale-2026/',
 'N17_BUS_SVX':'https://bus.tutu.ru/raspisanie/gorod_Perm/Ekaterinburg_Aeroport_Koltsovo/',
 'N18_ROSTEC':'https://www.rostec.ru/media/news/narabotka-ustanovok-odk-aviadvigatel-i-odk-permskie-motory-na-obektakh-tek-prevysila-50-mln-chasov/',
 'N19_AZIMUTH':'https://azimuth.ru/ru/news/aviakompaniya-azimut-uvelichivaet-chislo-napravleniy-v-ramkah-akcii-simfoniya-poleta'
}
def fetch(k,u):
 row={'source_id':k,'url':u,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=25);raw=r.read();row.update(http_status=r.status,final_url=r.url,content_type=r.headers.get('Content-Type'),response_bytes=len(raw),response_sha256=hashlib.sha256(raw).hexdigest())
  if raw.startswith(b'%PDF'):
   path='sources/'+k+'.pdf';(B/path).write_bytes(raw);row.update(status='primary_pdf_captured',saved_path=path,saved_sha256=hashlib.sha256(raw).hexdigest())
  else:
   s=raw.decode('utf-8','replace')
   if 't.me/s/' in u:
    post=u.split('/s/')[1];start=re.search(r'<div class="tgme_widget_message text_not_supported_wrap[^>]+data-post="'+re.escape(post)+'"',s)
    if not start:start=re.search(r'<div[^>]+data-post="'+re.escape(post)+'"',s)
    if start:
     sub=s[start.start():];nxt=re.search(r'<div class="tgme_widget_message text_not_supported_wrap',sub[10:]);s=sub[:nxt.start()+10] if nxt else sub
     row['status']='exact_post_http_captured'
    else:row['status']='exact_post_not_found';s='Целевое сообщение не выделено. Использовать pinned источник.'
   elif 'flyredwings.com' in u:
    st=s.find('<h1');s=s[st:] if st>=0 else s
    cuts=[p for p in [s.find('Перейти ко всем новостям'),s.find('<footer')] if p>0]
    if cuts:s=s[:min(cuts)]
    row['status']='primary_article_http_captured'
   else:row['status']='http_text_requires_content_check'
   t=plain(s);path='sources/'+k+'.txt';(B/path).write_text(t+'\n');row.update(saved_path=path,saved_sha256=hashlib.sha256((t+'\n').encode()).hexdigest(),chars=len(t))
 except Exception as e:row.update(status='fetch_failed',error=type(e).__name__+': '+str(e))
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(lambda kv:fetch(*kv),urls.items()))
(B/'fetch_receipts.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
for r in rows:print(r['source_id'],r['status'],r.get('chars',r.get('response_bytes')),r.get('error',''))
