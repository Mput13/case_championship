import urllib.request, json, hashlib, concurrent.futures, datetime, sys
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parent/'sources'
class Text(HTMLParser):
    def __init__(self):super().__init__();self.out=[];self.hide=0;self.links=[]
    def handle_starttag(self,t,a):
        if t in ['script','style','noscript']:self.hide+=1
        if t=='a':self.links.extend(v for k,v in a if k=='href')
    def handle_endtag(self,t):
        if t in ['script','style','noscript'] and self.hide:self.hide-=1
    def handle_data(self,s):
        if not self.hide and s.strip():self.out.append(s.strip())
def get(item):
    k,u=item;r={'source_id':k,'url':u,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        res=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=35)
        b=res.read();is_pdf=b[:4]==b'%PDF';suffix='.pdf' if is_pdf else '.html'
        r.update(http_status=res.status,final_url=res.url,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),raw_file=k+suffix)
        (ROOT/(k+suffix)).write_bytes(b)
        if not is_pdf:
            p=Text();p.feed(b.decode('utf8',errors='replace'));txt='\n'.join(p.out)
            (ROOT/(k+'.txt')).write_text(txt);r['text_sha256']=hashlib.sha256(txt.encode()).hexdigest();r['links']=p.links
            r['text_status']='EMPTY_OR_CHALLENGE' if len(txt)<200 else 'EXTRACTED_NOT_FACT_VERDICT'
    except Exception as e:r['error']=repr(e)
    (ROOT/(k+'.receipt.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='links'},ensure_ascii=False),flush=True)
if __name__=='__main__':
    urls=json.loads(sys.argv[1])
    list(concurrent.futures.ThreadPoolExecutor(max_workers=6).map(get,urls.items()))
