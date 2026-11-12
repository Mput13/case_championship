"""Локальная текстовая загрузка публичных источников; записи только в research_v1."""
import csv, hashlib, html, io, json, re, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import requests

ROOT = Path(__file__).resolve().parent
(ROOT/'evidence').mkdir(exist_ok=True)
PINS = {'author':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','five':'c18f7640ea36647a05b39089e5293f22dd009f63','plan':'b4d2ddf690440eb5cd051839cc263cf16b364ca4','P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(path,obj): (ROOT/path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def pin_inputs():
    paths={'author':['data/manual/rw_routes_now.csv','data/manual/known_flows.csv','data/manual/airport_tech.csv','data/manual/rail_schedule_spotchecks.csv','data/processed/longlist.csv','data/processed/catchments.csv','data/assumptions/bases.csv'], 'P02':['competitor_products.csv','fare_panel.csv','market_coverage.csv','historical_demand_context.csv','physical_adjacent_leg_candidates.csv','ordered_itineraries.csv','clock_conflicts.csv','competitor_responses.csv'], 'P03':['airport_constraints.csv','existing_commitments.csv','aircraft_type_parameters.csv'], 'P04':['airport_coverage.csv','cost_ranges.csv','budget_components.csv','thresholds.csv','event_rate_map.csv'], 'plan':['city_research_seed.csv','variant_research_plan.json','common_spec.json'], 'P00R':['contract_addendum.json'], 'P06':['producer_contract.json','README.md']}
    manifest=[]; extracts=[]
    for pack,ps in paths.items():
        for short in ps:
            path=short if pack=='author' else ('context/34_full_programme_plan_20261112/' if pack=='plan' else f'context/35_full_programme_execution_20261112/{pack}/')+short
            b=subprocess.check_output(['git','show',PINS[pack]+':'+path]);s=b.decode()
            blob=subprocess.check_output(['git','rev-parse',PINS[pack]+':'+path],text=True).strip()
            manifest.append(dict(package=pack,commit=PINS[pack],path=path,git_blob=blob,sha256=sha(b),bytes=len(b)))
            if short.endswith('.csv'):
                for n,row in enumerate(csv.DictReader(io.StringIO(s)),2):
                    if 'KZN' in str(row) or 'Казан' in str(row):
                        canonical=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
                        extracts.append(dict(source_id=f'PIN-{pack}',source_commit=PINS[pack],source_path=path,source_csv_record=n-1,source_row_id=row.get('product_id') or row.get('commitment_id') or row.get('candidate_id') or f'record:{n-1}',canonical_row_sha256=sha(canonical),row=row))
            elif pack=='plan' and short=='variant_research_plan.json':
                j=json.loads(s);dump('legacy_KZN.json',[x for x in j['legacy_hypotheses'] if 'KZN' in str(x) or 'Казан' in str(x)])
    dump('input_manifest.json',dict(pins=PINS,files=manifest,row_hash_method='sha256 UTF-8 JSON ensure_ascii=False sort_keys=True separators comma colon; source_csv_record excludes header, starts at1'))
    dump('pinned_KZN_rows.json',extracts)

def text_content(s):
    class Text(HTMLParser):
        def __init__(self): super().__init__();self.parts=[];self.skip=0
        def handle_starttag(self,t,a):
            if t in ('script','style','svg'):self.skip+=1
            if not self.skip and t in ('p','div','tr','li','h1','h2','h3','br'):self.parts.append('\n')
        def handle_endtag(self,t):
            if t in ('script','style','svg'):self.skip=max(0,self.skip-1)
            if not self.skip and t in ('p','div','tr','li','h1','h2','h3'):self.parts.append('\n')
        def handle_data(self,d):
            if not self.skip:self.parts.append(d+' ')
    p=Text();p.feed(s)
    return '\n'.join(' '.join(line.split()) for line in ''.join(p.parts).splitlines() if line.strip())

def fetch(item):
    sid,url=item;stamp=datetime.now(timezone.utc).isoformat();session=requests.Session()
    try:
        r=session.get(url,timeout=25)
        # Public server explicitly supplies this cookie in its own response. No user auth.
        if 'kazan.aero' in url and 'document.cookie=' in r.text:
            m=re.search("document.cookie='([^']+)'",r.text)
            if m:session.cookies.set(*m[1].split('=',1),domain='kazan.aero');r=session.get(url,timeout=25)
        ispdf='pdf' in r.headers.get('content-type','') or r.content[:4]==b'%PDF'
        suffix='.pdf' if ispdf else '.html';p=ROOT/'evidence'/(sid+suffix);p.write_bytes(r.content)
        if not ispdf:
            r.encoding=r.apparent_encoding
            (ROOT/'evidence'/(sid+'.txt')).write_text(text_content(r.text))
        return dict(source_id=sid,url=url,final_url=r.url,retrieved_at=stamp,http_status=r.status_code,bytes=len(r.content),sha256=sha(r.content),path=str(p.relative_to(ROOT)),content_type=r.headers.get('content-type'),status='FETCHED' if r.ok else 'HTTP_ERROR')
    except Exception as e:return dict(source_id=sid,url=url,retrieved_at=stamp,status='FETCH_ERROR',error=str(e))

if __name__=='__main__':
    if sys.argv[1]=='pins':pin_inputs()
    elif sys.argv[1]=='fetch':
        items=json.loads((ROOT/sys.argv[2]).read_text());rs=list(ThreadPoolExecutor(max_workers=6).map(fetch,items.items()))
        out=ROOT/'fetch_receipts.json';old=json.loads(out.read_text()) if out.exists() else [];dump('fetch_receipts.json',old+rs)
        for r in rs:print(r['source_id'],r['status'],r.get('http_status'),r.get('bytes'),r.get('error',''))
