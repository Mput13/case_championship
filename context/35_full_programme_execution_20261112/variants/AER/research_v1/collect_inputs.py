"""Только чтение exact Git blobs и публичных HTTP GET; запись внутри пакета AER."""
import csv, hashlib, io, json, re, subprocess, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, quote

ROOT = Path(__file__).resolve().parent
PINS = {'MODEL':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6', 'FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63', 'P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458', 'P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f', 'P03':'79dc698b99dfe866886d32376ed388e85bdd039c', 'P04':'620a0ac4bb11763319c4227485f6a3996b91d367', 'P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
BASE = 'context/35_full_programme_execution_20261112/'

def write(name, value):
    p=ROOT/name; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def pin_inputs():
    specs = [(k,BASE+k+'/'+n) for k, names in {
      'P02':['competitor_products.csv','fare_panel.csv','city_coverage.csv','historical_demand_context.csv','calendar_inventory.csv','clock_conflicts.csv','ordered_itineraries.csv','physical_adjacent_leg_candidates.csv','competitor_responses.csv'],
      'P03':['airport_constraints.csv','aircraft_type_parameters.csv','existing_commitments.csv'],
      'P04':['airport_coverage.csv','cost_ranges.csv','thresholds.csv'],
      'P00R':['contract_addendum.json'], 'P06':['producer_contract.json','README.md']}.items() for n in names]
    specs += [('MODEL','data/manual/'+n) for n in ['rw_routes_now.csv','airport_tech.csv','competitor_hubs.csv','longlist_manual.csv','known_flows.csv']]
    specs += [('MODEL','data/processed/longlist_scores.csv'), ('FIVE','context/33_five_city_reassessment_20261112/cities/PEE/routes.csv'),('P06','context/34_full_programme_plan_20261112/city_research_seed.csv'),('P06','context/34_full_programme_plan_20261112/variant_research_plan.json')]
    manifest=[]
    for key,path in specs:
        try: raw=subprocess.check_output(['git','show',PINS[key]+':'+path],stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            manifest.append({'commit':PINS[key],'path':path,'status':'PATH_NOT_FOUND','error':e.stderr.decode().strip()});continue
        item={'commit':PINS[key],'path':path,'git_blob_oid':subprocess.check_output(['git','rev-parse',PINS[key]+':'+path],text=True).strip(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'status':'READ_EXACT_BLOB'}
        if path.endswith('.csv'):
            rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))); selected=[]
            for i,row in enumerate(rows):
                if path.endswith('city_coverage.csv'): match=row.get('city')=='AER'
                elif 'city_research_seed' in path: match=row.get('iata')=='AER'
                elif path.endswith(('aircraft_type_parameters.csv','thresholds.csv')): match=True
                else: match=any(re.search(r'\bAER\b|Сочи',str(v)) for v in row.values())
                if match:
                    canonical=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
                    selected.append({'source_csv_line':i+2,'source_row_sha256':hashlib.sha256(canonical).hexdigest(),'source_row_id':row.get('product_id') or row.get('schedule_instance_id') or row.get('market_id') or row.get('iata') or f'line:{i+2}','data':row})
            item.update(total_rows=len(rows),selected_rows=len(selected),selection='AER endpoint/reference only; shared type/threshold schema retained')
            out='inputs/'+key+'_'+Path(path).name+'.json';write(out,{'provenance':item,'rows':selected});item['local_extract']=out
        elif key in ['P00R','P06'] and 'variant_research' not in path:
            out='inputs/'+key+'_'+Path(path).name
            (ROOT/out).parent.mkdir(exist_ok=True);(ROOT/out).write_bytes(raw);item['local_extract']=out
        manifest.append(item)
    write('source_pins.json',{'pins':PINS,'row_hash_definition':'SHA256 UTF-8 json.dumps(dict,ensure_ascii=False,sort_keys=True,separators=(comma,colon))','inputs':manifest})

class Text(HTMLParser):
    def __init__(self):super().__init__();self.skip=0;self.chunks=[];self.links=[];self.href=None;self.label=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ['script','style','noscript']:self.skip+=1
        if tag=='a':self.href=a.get('href');self.label=[]
        if tag in ['p','br','div','li','h1','h2','h3','tr']:self.chunks.append('\n')
    def handle_endtag(self,tag):
        if tag in ['script','style','noscript'] and self.skip:self.skip-=1
        if tag=='a' and self.href:self.links.append((self.href,' '.join(self.label)));self.href=None
    def handle_data(self,data):
        if not self.skip:
            self.chunks.append(data)
            if self.href:self.label.append(data.strip())

def fetch(sid,url):
    stamp=datetime.now(timezone.utc).isoformat()
    try:
        req=urllib.request.Request(quote(url,safe=':/?=&%+'),headers={'User-Agent':'Mozilla/5.0 (public research)'})
        with urllib.request.urlopen(req,timeout=20) as r:raw=r.read();code=r.status;final=r.url;mime=r.headers.get('Content-Type','')
        ext='pdf' if raw.startswith(b'%PDF') else 'html'
        p=ROOT/'sources'/(sid+'.'+ext);p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
        receipt={'source_id':sid,'url':url,'final_url':final,'fetched_at_utc':stamp,'http_status':code,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'local_path':str(p.relative_to(ROOT)),'mime':mime,'status':'FETCHED'}
        if ext=='html':
            parser=Text();parser.feed(raw.decode('utf-8','replace'));text='\n'.join(re.sub(r'\s+',' ',x).strip() for x in ''.join(parser.chunks).splitlines() if x.strip());(p.with_suffix('.txt')).write_text(text)
            links=[{'label':t,'url':urljoin(final,h)} for h,t in parser.links]
            write('sources/'+sid+'_links.json',links)
        print(sid,code,len(raw))
    except Exception as e:receipt={'source_id':sid,'url':url,'fetched_at_utc':stamp,'status':'FETCH_FAILED','error':str(e)};print(sid,receipt['error'])
    return receipt

if __name__=='__main__':
    import sys
    if len(sys.argv)==1:pin_inputs()
    else:
        receipts=json.loads((ROOT/'fetch_receipts.json').read_text()) if (ROOT/'fetch_receipts.json').exists() else []
        for sid,url in zip(sys.argv[1::2],sys.argv[2::2]):receipts.append(fetch(sid,url))
        write('fetch_receipts.json',receipts)
