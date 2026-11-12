"""Текстовая HTTP-загрузка публичных первичных источников; без browser/session/auth."""
from pathlib import Path
from html.parser import HTMLParser
import concurrent.futures, datetime, hashlib, json, sys, urllib.request, urllib.error
ROOT=Path(__file__).resolve().parent
class Text(HTMLParser):
    def __init__(self): super().__init__(); self.skip=0; self.parts=[]; self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'): self.skip+=1
        if tag=='a':
            d=dict(attrs)
            if d.get('href'): self.links.append(d['href'])
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'): self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip(): self.parts.append(' '.join(data.split()))
def fetch(row):
    sid,url=row['source_id'],row['url']; rec={**row,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (public-source research; text fetch)'})
        with urllib.request.urlopen(req,timeout=35) as r: b=r.read(); rec.update(http_status=r.status,final_url=r.url,content_type=r.headers.get('Content-Type',''))
        rec.update(response_bytes=len(b),response_sha256=hashlib.sha256(b).hexdigest())
        if 'pdf' in rec['content_type'] or b[:4]==b'%PDF':
            target=ROOT/'evidence'/f'{sid}.pdf';target.write_bytes(b);rec.update(path=str(target.relative_to(ROOT)),status='FETCHED_PDF_NEEDS_TEXT_EXTRACTION')
        else:
            p=Text();p.feed(b.decode('utf-8',errors='replace'));txt='\n'.join(p.parts)
            target=ROOT/'evidence'/f'{sid}.txt';target.write_text(txt+'\n');rec.update(path=str(target.relative_to(ROOT)),text_sha256=hashlib.sha256((txt+'\n').encode()).hexdigest(),status='FETCHED_TEXT')
            (ROOT/'evidence'/f'{sid}_links.json').write_text(json.dumps(p.links,ensure_ascii=False,indent=2)+'\n')
    except Exception as e: rec.update(status='FETCH_FAILED_NOT_ABSENCE',error=f'{type(e).__name__}: {e}')
    return rec
def main():
    (ROOT/'evidence').mkdir(exist_ok=True)
    rows=json.loads(Path(sys.argv[1]).read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: receipts=list(ex.map(fetch,rows))
    target=ROOT/'fetch_receipts.json'; old=json.loads(target.read_text()) if target.exists() else []
    target.write_text(json.dumps(old+receipts,ensure_ascii=False,indent=2)+'\n')
    for r in receipts:print(r['source_id'],r['status'],r.get('response_bytes'),r.get('error',''))
if __name__=='__main__':main()
