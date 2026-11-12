import concurrent.futures,urllib.request,hashlib,json,pathlib,datetime
from html.parser import HTMLParser
class Extract(HTMLParser):
 def __init__(self): super().__init__();self.skip=0;self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style','noscript'): self.skip+=1
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript'): self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip and data.strip(): self.parts.append(data.strip())
BASE=pathlib.Path(__file__).resolve().parent
URLS={
'NEW-UFA-H1':'https://www.airportufa.ru/news/2026/itogi-pervogo-polugodiya-/',
'NEW-UFA-2025':'https://www.airportufa.ru/news/2025/mezhdunarodnyy-aeroport-ufa-podvel-itogi-2025-goda/',
'NEW-UFA-WINTER':'https://www.airportufa.ru/news/2026/perekhod-na-osenne-zimnee-raspisanie-2026-27gg/',
'NEW-UFA-SUMMER':'https://www.airportufa.ru/news/2026/aeroport-ufa-perekhodit-na-vesenne-letnee-raspisanie/',
'NEW-UFA-TRANSFER':'https://www.airportufa.ru/scoreboard/transfer/',
'NEW-UT-TRANSFER':'https://www.utair.ru/support/4/obshie_pravila_perevozki_bagazha/transfer_bagazha',
'NEW-UFA-TECH':'https://www.airportufa.ru/partners/airlines/specifications/',
'NEW-UFA-BOHTAR':'https://www.airportufa.ru/news/2026/aviakompaniya-norwind-zapuskaet-regulyarnye-reysy-ufa-bokhtar/',
'NEW-UFA-KZN':'https://www.airportufa.ru/news/2024/zapusk-dopolnitelnykh-reysov-iz-ufy-v-kazan/',
'NEW-UFA-KEJ-HIST':'https://www.airportufa.ru/news/2023/iz-ufy-v-kemerovo/',
'NEW-UFA-GROUND':'https://www.airportufa.ru/regulations/get/by-bus/',
'NEW-TOF-SECONDARY':'https://rasp.ru/ufa/tomsk/avia',
'NEW-KEJ-SECONDARY':'https://avia.tutu.ru/rasp/Ufa--Kemerovo/',
'NEW-RW-WINTER':'https://flyredwings.com/news/red-wings-perekhodit-na-zimnee-raspisanie-poletov/'
}
(BASE/'sources').mkdir(exist_ok=True)
def get(kv):
 sid,url=kv; rec={'source_id':sid,'requested_url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research textual fetch'})
  with urllib.request.urlopen(req,timeout=35) as f:raw=f.read();rec.update(final_url=f.url,http_status=f.status,content_type=f.headers.get('Content-Type'))
  rec.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),status='HTTP_READ')
  parser=Extract();parser.feed(raw.decode('utf-8',errors='replace'));txt='\n'.join(parser.parts)
  (BASE/'sources'/f'{sid}.html').write_bytes(raw);(BASE/'sources'/f'{sid}.txt').write_text(txt)
  rec['text_sha256']=hashlib.sha256(txt.encode()).hexdigest();rec['text_path']=f'sources/{sid}.txt'
 except Exception as e:rec.update(status='FETCH_ERROR',error=repr(e))
 return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: receipts=list(pool.map(get,URLS.items()))
(BASE/'fetch_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
for r in receipts:print(r['source_id'],r['status'],r.get('bytes'),r.get('error',''))
