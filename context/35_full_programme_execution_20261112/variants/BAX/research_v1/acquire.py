"""Read-only HTTP acquisition. Writes only this BAX package; no browser/session use."""
from pathlib import Path
import concurrent.futures, datetime, hashlib, html, json, re, subprocess, urllib.request

ROOT = Path(__file__).resolve().parent
SOURCES = {
 'BAX-AIRPORT-ROOT':'https://airaltay.ru/',
 'BAX-CONTRACT':'https://airaltay.ru/upload/docs/tip-dog.pdf',
 'BAX-TARIFF2024':'https://airaltay.ru/upload/docs/arenda/Прейскурант 1-2024 аэропортовых сборов и тарифов за наземное обслуживание ВС в аэропорту Барнаул с 01.01.24.pdf',
 'RW-BOARD':'https://flyredwings.com/flight-board/WZ/',
 'RW-WINTER':'https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/',
 'RW-BELAVIA':'https://flyredwings.com/en/press/news/red-wings-i-belavia-rasshiryayut-marshrutnuyu-set-v-ramkax-kod-sheringa/',
 'BAX-TERMINAL':'https://new.barnaul.org/news/prezident-rf-vladimir-putin-ofitsialno-dal-start-rabote-novogo-aerovokzalnogo-kompleksa-mezhdunarodn.html',
 'BAX-HISTORY':'https://www.aex.ru/news/2026/1/12/291397/',
 'BAX-2025-FINAL':'https://barnaul.press/news/passazhiropotok-barnaulskogo-aeroporta-sostavil-pochti-800-tysyach-chelovek.html',
 'BAX-2025-APRIL':'https://www.nia-altay24.ru/news/economy/12137.html',
 'BAX-GROUND':'https://bus.tutu.ru/raspisanie/Barnaul_Avtovokzal/gorod_Tolmachyovo/',
 'BAX-GROUND-RETURN':'https://bus.tutu.ru/raspisanie/gorod_Tolmachyovo/gorod_Barnaul/',
 'BAX-YANDEX':'https://rasp.yandex.ru/station/9623280/?date=all-days',
 'BAX-HTA-CLOCKCHECK':'https://new.pskovavia.ru/passengers/information/schedule/?airport=2521&setFilter=Y',
 'BAX-UTAIR':'https://trip.utair.ru/bax',
 'BAX-N4-TRANSFER':'https://mindortrans.tatarstan.ru/index.htm/news/2514977.htm',
}

def fetch(k, url):
    t=datetime.datetime.now(datetime.timezone.utc).isoformat()
    record={'source_id':k,'url':url,'retrieved_at':t}
    try:
        from urllib.parse import quote, urlsplit, urlunsplit
        u=urlsplit(url); encoded=urlunsplit((u.scheme,u.netloc,quote(u.path,safe='/%'),u.query,u.fragment))
        req=urllib.request.Request(encoded,headers={'User-Agent':'Mozilla/5.0 research-read-only'})
        with urllib.request.urlopen(req,timeout=18) as r:
            body=r.read();record.update(http_status=r.status,final_url=r.url,content_type=r.headers.get('content-type'),bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
        ext='.pdf' if body.startswith(b'%PDF') else '.html'
        path=ROOT/'sources'/(k+ext);path.write_bytes(body);record['path']=str(path.relative_to(ROOT))
        if ext=='.pdf':
            p=subprocess.run(['pdftotext','-layout',str(path),str(path.with_suffix('.txt'))],capture_output=True,text=True)
            record['text_status']='extracted' if p.returncode==0 else p.stderr
        else:
            raw=body.decode('utf-8','replace')
            clean=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',raw,flags=re.S|re.I)
            clean=re.sub(r'</(?:p|div|tr|h[1-6]|li|section)>','\n',clean,flags=re.I)
            clean=html.unescape(re.sub('<[^>]+>',' ',clean))
            clean='\n'.join(re.sub(r'\s+',' ',s).strip() for s in clean.splitlines() if s.strip())
            path.with_suffix('.txt').write_text(clean)
            record['text_status']='bot_challenge_not_content' if ('gorizontal-vertikal' in raw and 'noindex, noarchive' in raw) else 'extracted_unverified'
        record['text_path']=str(path.with_suffix('.txt').relative_to(ROOT))
    except Exception as e:
        record.update(http_status='ERROR',error=type(e).__name__+': '+str(e))
    return record

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        receipts=list(pool.map(lambda x:fetch(*x),SOURCES.items()))
    (ROOT/'fetch_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
    for r in receipts:print(r['source_id'],r['http_status'],r.get('bytes'),r.get('text_status',r.get('error')))
