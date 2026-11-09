#!/usr/bin/env python3
"""Small public HTTP/git acquisition helper. No credentials or browser state."""
import argparse, csv, hashlib, json, subprocess, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class Text(HTMLParser):
    def __init__(self): super().__init__(); self.bits=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
        elif tag in ('p','div','tr','li','h1','h2','h3','br','td','th'): self.bits.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
    def handle_data(self,d):
        if not self.skip: self.bits.append(d)
def main():
    p=argparse.ArgumentParser(); p.add_argument('dataset_id');p.add_argument('url');p.add_argument('filename');p.add_argument('--owner',default='UNKNOWN');p.add_argument('--grain',default='webpage snapshot');p.add_argument('--geography',default='UNKNOWN');p.add_argument('--period',default='snapshot 2026-11-09');p.add_argument('--license',default='UNKNOWN');p.add_argument('--purpose',default='Route/calendar or cost evidence');p.add_argument('--limitations',default='Published information; not proof of operation, demand or realised revenue');p.add_argument('--git-ref');p.add_argument('--git-path'); a=p.parse_args()
    for d in ('raw','normalized'): (ROOT/d).mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat(); meta=dict(dataset_id=a.dataset_id,source_url=a.url,organization=a.owner,retrieved_at_utc=now,publication_date='UNKNOWN',grain=a.grain,geographic_coverage=a.geography,temporal_coverage=a.period,license=a.license,decision_use=a.purpose,limitations=a.limitations,collector_version='acquire.py/v1',command='python3 '+str(Path(__file__).relative_to(Path.cwd()))+' '+' '.join(__import__('shlex').quote(x) for x in __import__('sys').argv[1:]))
    try:
        if a.git_ref:
            blob=subprocess.check_output(['git','show',a.git_ref+':'+a.git_path]);meta.update(git_ref=a.git_ref,git_path=a.git_path,http_status=None)
        else:
            req=urllib.request.Request(a.url,headers={'User-Agent':'case5-public-research/1.0'})
            with urllib.request.urlopen(req,timeout=35) as response:
                allowed={'content-type','content-length','last-modified','etag','date','cache-control'}
                safe_headers={k:v for k,v in response.headers.items() if k.lower() in allowed}
                blob=response.read(20_000_001);meta.update(http_status=response.status,final_url=response.url,response_headers=safe_headers)
            if len(blob)>20_000_000: raise ValueError('response exceeds 20 MB cap')
        target=ROOT/'raw'/a.filename;target.write_bytes(blob)
        count=None
        if a.filename.endswith('.csv'):
            count=sum(1 for _ in csv.DictReader(blob.decode('utf-8-sig').splitlines()))
        if a.filename.endswith('.html'):
            parser=Text();parser.feed(blob.decode('utf-8','replace'))
            text='\n'.join(x.strip() for x in ''.join(parser.bits).splitlines() if x.strip())
            (ROOT/'normalized'/(a.dataset_id+'.txt')).write_text(text,encoding='utf-8')
        meta.update(raw_path='raw/'+a.filename,sha256=hashlib.sha256(blob).hexdigest(),size_bytes=len(blob),record_count=count,acquisition_status='ACQUIRED_RAW')
    except Exception as error:
        meta.update(raw_path=None,sha256=None,size_bytes=None,record_count=None,acquisition_status='ACCESS_FAILED',exact_error=repr(error))
    path=ROOT/'dataset_manifest.json';old=json.loads(path.read_text()) if path.exists() else []
    old=[r for r in old if r['dataset_id']!=a.dataset_id]+[meta];path.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:meta.get(k) for k in ('dataset_id','acquisition_status','http_status','size_bytes','record_count','exact_error')},ensure_ascii=False))
if __name__=='__main__':main()
