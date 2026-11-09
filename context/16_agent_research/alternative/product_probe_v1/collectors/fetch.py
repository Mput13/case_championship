#!/usr/bin/env python3
"""Small public HTTP acquisition; raw stays in ignored local raw_hold.

Use --id NAME --url URL; bounded3MB, TLS validation, no credentials/cookies.
Re-fetching an existing ID is refused. Safe factual extracts are separate.
"""
import argparse
import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'content-type','content-length','last-modified','etag','date','cache-control'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--id',required=True);ap.add_argument('--url',required=True);args=ap.parse_args()
    if not args.id.replace('_','').replace('-','').isalnum():raise ValueError('Invalid source ID')
    (ROOT/'raw_hold').mkdir(exist_ok=True);(ROOT/'receipts').mkdir(exist_ok=True)
    target=ROOT/'raw_hold'/(args.id+'.bin');receipt=ROOT/'receipts'/(args.id+'.json')
    if target.exists() or receipt.exists():raise ValueError('Frozen source ID already exists; use a new ID')
    rec={'snapshot_id':args.id,'source_url':args.url,'retrieved_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
         'publication_date':'UNKNOWN','source_status':'ACCESS_FAILED','raw_path':'raw_hold/'+target.name,
         'raw_publication_status':'LOCAL_HOLD','licence':'UNKNOWN','headers_policy':'six-field-whitelist',
         'collector_version':'c14-fetch-v1','reproduce_command':['python3','context/16_agent_research/alternative/product_probe_v1/collectors/fetch.py','--id',args.id+'_refresh','--url',args.url]}
    try:
        req=urllib.request.Request(args.url,headers={'User-Agent':'case5-public-research/1'})
        with urllib.request.urlopen(req,timeout=35) as response:
            body=response.read(3_000_001)
            if len(body)>3_000_000:raise ValueError('3MB source guard exceeded')
            rec.update(http_status=response.status,response_headers={k.lower():v for k,v in response.headers.items() if k.lower() in ALLOWED})
        target.write_bytes(body);rec.update(source_status='ACQUIRED_RAW',sha256=hashlib.sha256(body).hexdigest(),size_bytes=len(body))
    except Exception as exc:rec['error']=f'{type(exc).__name__}: {exc}'
    receipt.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:rec.get(k) for k in ['snapshot_id','source_status','http_status','size_bytes','sha256','error']},ensure_ascii=False))

if __name__=='__main__':main()
