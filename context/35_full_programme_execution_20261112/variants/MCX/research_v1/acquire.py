import urllib.request,pathlib,hashlib,json,datetime,concurrent.futures,re,html
from urllib.parse import urljoin
D=pathlib.Path(__file__).resolve().parent;(D/'sources').mkdir(exist_ok=True)
urls={'MCX-SCHEDULE':'https://mcx.aero/board/schedule/','MCX-TARIFFS':'https://mcx.aero/partners/for-airlines/tariffs/','MCX-OLDTARIFF':'https://mcx.aero/info/sbory_i_tarify_na_aeroportovye_uslugi_/','MCX-PARTNERS':'https://mcx.aero/partners/','RW-WINTER':'https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/','MCX-STATS2026':'https://mintransdag.ru/news/za-9-mesiacev-2026-goda-aeroport-maxackaly-obsluzil-bolee-2-millionov-passazirov'}
def clean(s):
 s=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',s,flags=re.S|re.I)
 return '\n'.join(html.unescape(re.sub('<[^>]+>','',s)).strip().split()) if False else re.sub(r'\n\s*\n+','\n',html.unescape(re.sub('<[^>]+>','\n',s)))
def f(kv):
 k,u=kv;at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 try:
  with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as r:b=r.read();status=r.status;final=r.url
  (D/'sources'/f'{k}.html').write_bytes(b);s=b.decode('utf-8','replace');t=clean(s);(D/'sources'/f'{k}.txt').write_text(t)
  links=[{'title':' '.join(clean(a[2]).split()),'href':urljoin(u,html.unescape(a[1]))} for a in re.findall(r'<a\b[^>]*href=([\"\x27])(.*?)\1[^>]*>(.*?)</a>',s,re.S|re.I)]
  (D/'sources'/f'{k}.links.json').write_text(json.dumps(links,ensure_ascii=False,indent=2))
  return {'source_id':k,'url':u,'final_url':final,'retrieved_at':at,'http_status':status,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'text_chars':len(t)}
 except Exception as e:return {'source_id':k,'url':u,'retrieved_at':at,'error':str(e)}
if __name__=='__main__':
 res=list(concurrent.futures.ThreadPoolExecutor(6).map(f,urls.items()));(D/'fetch_receipts.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps(res,ensure_ascii=False))
 for k in ['MCX-TARIFFS','MCX-OLDTARIFF']:
  j=json.loads((D/'sources'/f'{k}.links.json').read_text());print(k,json.dumps([x for x in j if 'pdf' in x['href'].lower() or '2026' in x['title'] or '2025' in x['title']],ensure_ascii=False)[:14000])
 s=(D/'sources/MCX-SCHEDULE.html').read_text();i=s.find('WZ 5917');print('CARD',s[max(0,i-2500):i+9000])
