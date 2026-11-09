#!/usr/bin/env python3
"""Acquire narrowly selected official Remezov identity/context pages."""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

BASE=Path(__file__).resolve().parent
SOURCES=[
    ('RMZ01','https://ar-rmz.ru/partners/airlines/airport/','official aerodrome identity; USTJ'),
    ('RMZ02','https://ar-rmz.ru/about/news/aeroport-remezov-otmechaet-5-letie/','2026-09-24 airport statement lists Omsk in Remezov network; not proof of every December flight'),
]
SAFE={'content-type','content-length','last-modified','etag','date','cache-control','content-encoding'}
class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in {'script','style'}:self.skip+=1
    def handle_endtag(self,t):
        if t in {'script','style'}:self.skip=max(0,self.skip-1)
    def handle_data(self,d):
        if not self.skip:self.parts.append(d)
def main():
    out=[];raw=BASE/'raw/primary';raw.mkdir(parents=True,exist_ok=True)
    for id,url,scope in SOURCES:
        at=dt.datetime.now(dt.timezone.utc).isoformat();r={'source_id':id,'source_url':url,'retrieved_at_utc':at,'organization':'Аэропорт Ремезов','scope':scope,'license':'UNKNOWN; full HTML remains local ignored'}
        try:
            with urllib.request.urlopen(url,timeout=20)as response:
                body=response.read(1_000_001);r.update(http_status=response.status,response_headers={k:v for k,v in response.headers.items()if k.lower()in SAFE})
            if len(body)>1_000_000:raise ValueError('Page exceeds1MB limit')
            file=raw/(id+'_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.html');file.write_bytes(body);r.update(raw_path=str(file.relative_to(BASE)),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),access_status='ACQUIRED_RAW')
            p=Text();p.feed(body.decode());s=re.sub(r'\s+',' ',' '.join(p.parts))
            r['target_markers']={'USTJ':'USTJ'in s,'Remezov':'Ремезов'in s,'Omsk':'Омск'in s,'publication20260924':'24 сентября 2026'in s}
        except Exception as error:r.update(access_status='ACCESS_FAILED',error=type(error).__name__+': '+str(error))
        out.append(r)
    (BASE/'primary_manifest.json').write_text(json.dumps({'sources':out,'boundary':'Official published identity/network claims; not operational clearance, target-week performed flights or demand'},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:r.get(k)for k in ['source_id','access_status','bytes','target_markers']}for r in out],ensure_ascii=False))
if __name__=='__main__':main()
