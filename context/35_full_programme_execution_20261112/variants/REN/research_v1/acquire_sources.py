from pathlib import Path
import requests,lxml.html,hashlib,json,datetime,concurrent.futures
ROOT=Path(__file__).resolve().parent
S=ROOT/'sources';S.mkdir(exist_ok=True)
URLS={
'REN-SCHEDULE-OUT':'https://ar-ren.ru/schedule/',
'REN-SCHEDULE-IN':'https://ar-ren.ru/schedule/?type=arr',
'REN-TECH':'https://ar-ren.ru/partners/airlines/airport/',
'REN-COORD':'https://ar-ren.ru/partners/airlines/coordination/',
'REN-TARIFF-INDEX':'https://ar-ren.ru/partners/airlines/pricelists/',
'REN-DISCLOSURE':'https://ar-ren.ru/partners/about/info/',
'REN-WINTER26':'https://ar-ren.ru/about/news/aeroport-orenburg-perekhodit-na-osenne-zimnee/',
'REN-TERMINAL26':'https://ar-ren.ru/about/news/sostoyalas-prezentatsiya-novogo-aerovokzalnogo-kompleksa-aer/',
'REN-WINTER-PREP':'https://ar-ren.ru/about/news/aeroport-orenburg-gotov-k-rabote-v-osenne-zimnem-/',
'RW-REN-EVN26':'https://flyredwings.com/press/news/red-wings-nachnet-letat-v-erevan-iz-orenburga/',
'REN-GOJ-RGK26':'https://ar-ren.ru/about/news/iz-orenburga-startovali-reysy-v-nizhniy-novgorod-i-gorno-alt/',
'REN-GROUND':'https://ar-ren.ru/passengers/how-to-get/',
'REN-PAX25-IF':'https://www.interfax-russia.ru/volga/news/passazhiropotok-aeroporta-orenburga-v-2025g-ne-dostig-pokazatelya-2024g-v-1-mln-chelovek',
'RW-MSQ':'https://flyredwings.com/directions/minsk/'
}
def get(item):
 k,u=item
 try:
  r=requests.get(u,timeout=40);b=r.content;(S/(k+'.html')).write_bytes(b)
  doc=lxml.html.fromstring(b.decode('utf8',errors='replace'))
  for x in doc.xpath('//script|//style|//svg'):x.drop_tree()
  (S/(k+'.txt')).write_text(' '.join(doc.text_content().split()))
  links=[{'title':' '.join(a.text_content().split()),'url':requests.compat.urljoin(r.url,a.get('href',''))} for a in doc.xpath('//a[@href]')]
  if k in ['REN-TARIFF-INDEX','REN-DISCLOSURE','REN-GROUND']:(S/(k+'.links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2))
  if 'SCHEDULE' in k:
   rows=[]
   for ti,t in enumerate(doc.xpath('//table')):
    for ri,tr in enumerate(t.xpath('.//tr')):
     cells=[' '.join(x.text_content().split()) for x in tr.xpath('./td|./th')]
     rows.append({'table':ti,'row':ri,'cells':cells,'row_sha256_html_normalized':hashlib.sha256(lxml.html.tostring(tr)).hexdigest()})
   (ROOT/(k+'.rows.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
  return {'source_id':k,'url':u,'final_url':r.url,'http_status':r.status_code,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
 except Exception as e:return {'source_id':k,'url':u,'error':str(e)}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:rec=list(ex.map(get,URLS.items()))
 (S/'fetch_receipts.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2))
 for x in rec:print(x['source_id'],x.get('http_status',x.get('error')),x.get('bytes'))
