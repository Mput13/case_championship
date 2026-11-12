"""Текстовая HTTP-проверка первичных страниц. Запись только внутри этого пакета."""
import concurrent.futures
import datetime as dt
import hashlib
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URLS = {
    'SVX_DEP': 'https://ar-svx.ru/schedule/',
    'SVX_ARR': 'https://ar-svx.ru/schedule/?type=arr',
    'RGK_SCHEDULE': 'https://rgk-aero.ru/online/schedule/',
    'RGK_TECH': 'https://rgk-aero.ru/partners/airlines/kharakteristika-aeroporta/',
    'RW_DIRECTIONS': 'https://flyredwings.com/directions/ekaterinburg/',
    'RW_SALE': 'https://flyredwings.com/november-sale-2026/',
    'RW_BOARD': 'https://flyredwings.com/flight-board/?target=form',
}

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip += 1
        if tag in ('tr','p','li','h1','h2','h3','div'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag in ('tr','p','li'): self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip: self.parts.append(data+' ')

def fetch(item):
    sid,url=item
    receipt={'source_id':sid,'url':url,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research text fetch)'})
        with urllib.request.urlopen(req,timeout=35) as r:
            raw=r.read(); receipt.update(http_status=r.status,final_url=r.url)
        p=Text();p.feed(raw.decode('utf-8',errors='replace'))
        lines=[re.sub(r'\s+',' ',x).strip() for x in ''.join(p.parts).splitlines()]
        lines=[x for x in lines if x]
        if sid.startswith(('SVX_','RGK_')) or sid=='RW_BOARD':
            (ROOT/'evidence'/f'{sid}_full_text.txt').write_text('\n'.join(f'{i+1}: {x}' for i,x in enumerate(lines))+'\n')
        # Только релевантные станции/рейсы и контекст таблицы; не чужой архив.
        keep=set()
        pattern=r'ОМСК|КРАСНОЯРСК|САМАР|ВОЛГОГРАД|УФА|СУРГУТ|ГОРНО|МИНЕРАЛЬНЫЕ|МУРМАНСК|НИЖНИЙ|КАЗАНЬ|ЕКАТЕРИНБУРГ|ПЕРМЬ|WZ[ -]?(5053|5054|5007|5008|5071|5072|1017|1018|5303|5304)|2026|2027|Период|Дни пол|Вылет|Прилет'
        for i,line in enumerate(lines):
            if re.search(pattern,line,re.I): keep.update(range(max(0,i-2),min(len(lines),i+4)))
        text='\n'.join(f'{i+1}: {lines[i]}' for i in sorted(keep))+'\n'
        path=ROOT/'evidence'/f'{sid}_selected_text.txt';path.write_text(text)
        receipt.update(raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),
                       selected_text_path=str(path.relative_to(ROOT)),
                       selected_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                       status='HTTP_OK_SELECTED_TEXT_NOT_EXECUTION_OR_INVENTORY')
    except Exception as e:
        receipt.update(status='FETCH_FAILED',error=f'{type(e).__name__}: {e}')
    return receipt

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        receipts=list(ex.map(fetch,URLS.items()))
    (ROOT/'evidence'/'live_fetch_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:r.get(k) for k in ('source_id','status','raw_bytes','selected_html_rows','error')} for r in receipts],ensure_ascii=False))
