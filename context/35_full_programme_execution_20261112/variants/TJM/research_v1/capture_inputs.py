"""Read exact Git blobs; write only this research directory. No Git mutations."""
import csv, datetime, hashlib, io, json, pathlib, subprocess, urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent
P = 'context/35_full_programme_execution_20261112/'
PINS = {'AUTHOR':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63','P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
manifest=[]
def blob(pin,path):
    b=subprocess.check_output(['git','show',PINS[pin]+':'+path])
    manifest.append({'pin_id':pin,'commit':PINS[pin],'path':path,'blob_oid':subprocess.check_output(['git','rev-parse',PINS[pin]+':'+path],text=True).strip(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
    return b
def dump(name,v):
    (ROOT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def subset(pin,path,name,predicate):
    b=blob(pin,path); reader=csv.DictReader(io.StringIO(b.decode('utf-8-sig')))
    out=[]
    for n,r in enumerate(reader,2):
        if predicate(r):
            out.append({'source_file':path,'source_commit':PINS[pin],'source_row_number':n,'source_row_id':r.get('product_id') or r.get('schedule_instance_id') or r.get('source_id') or r.get('hypothesis_id') or f'row:{n}','source_row_sha256':hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'row_hash_method':'sha256 canonical parsed row JSON, not raw CSV bytes','data':r})
    dump(name,out)
    print(name,len(out))
def tjm(r):return any('TJM' in str(v) or 'Тюмен' in str(v) for v in r.values())
if __name__=='__main__':
    for f in ['sources.csv','claims.csv','features.csv','routes.csv','selected_subsidy_rows.csv','selected_model_routes.csv']:
        subset('FIVE','context/33_five_city_reassessment_20261112/cities/TJM/'+f,'pinned_five_'+f.replace('.csv','.json'),lambda r:True)
    for f in ['network_routes.csv','network_summary.csv','longlist.csv']:
        subset('AUTHOR','data/processed/'+f,'pinned_author_'+f.replace('.csv','.json'),tjm)
    for f in ['competitor_products.csv','calendar_inventory.csv','market_coverage.csv','alternatives_contract.csv','physical_adjacent_leg_candidates.csv','season_coverage.csv']:
        subset('P02',P+'P02/'+f,'pinned_p02_'+f.replace('.csv','.json'),tjm)
    for f in ['airport_constraints.csv','existing_commitments.csv']:
        subset('P03',P+'P03/'+f,'pinned_p03_'+f.replace('.csv','.json'),tjm)
    subset('P03',P+'P03/aircraft_type_parameters.csv','pinned_p03_ssj_types.json',lambda r:r['aircraft_type'] in ['RRJ95B','RRJ95LR_100','SJ100_PD8'])
    subset('P04',P+'P04/airport_coverage.csv','pinned_p04_airport_coverage.json',tjm)
    subset('P04',P+'P04/thresholds.csv','pinned_p04_thresholds.json',lambda r:True)
    subset('P04',P+'P04/event_rate_map.csv','pinned_p04_cost_drivers.json',lambda r:r['rate_id'].startswith(('HIST-','UNK-','KUF-')) and not any(x in r['rate_id'] for x in ['Tu214','other_existing_RW_type']))
    plan=json.loads(blob('P06','context/34_full_programme_plan_20261112/variant_research_plan.json'))
    dump('pinned_plan_tjm.json',{'seed_cities':[r for r in plan['seed_cities'] if tjm(r)],'legacy_hypotheses':[r for r in plan['legacy_hypotheses'] if tjm(r)],'legacy_direct_rotation_seeds':[r for r in plan['legacy_direct_rotation_seeds'] if tjm(r)]})
    for pin,f in [('P00R','contract_addendum.json'),('P06','producer_contract.json')]:
        b=blob(pin,P+pin+'/'+f);dump('pinned_'+pin.lower()+'_'+f,json.loads(b))
    dump('source_pins.json',{'pins':PINS,'files':manifest,'read_method':'git show EXACT_SHA:path; canonical parsed-row hashes in subset files','git_mutations':False})

    class Parser(HTMLParser):
        def __init__(self):super().__init__();self.text=[];self.links=[];self.skip=0
        def handle_starttag(self,tag,attrs):
            if tag in ('script','style'):self.skip+=1
            if tag=='a':
                d=dict(attrs)
                if d.get('href'):self.links.append(d['href'])
        def handle_endtag(self,tag):
            if tag in ('script','style'):self.skip=max(0,self.skip-1)
        def handle_data(self,data):
            if not self.skip and data.strip():self.text.append(data.strip())
    urls={
        'TJM-N01':'https://flyredwings.com/directions/tyumen/',
        'TJM-N02':'https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/',
        'TJM-N03':'https://mcx.aero/board/schedule/',
        'TJM-N04':'https://tjmport.ru/partners/airlines/documents/',
        'TJM-N05':'https://yamalaero.ru/about/news/Yamal-Airlines-has-introduced-new-hangar-complex/',
        'TJM-N06':'https://yamalaero.ru/about/news/dmitriy-artyukhov-anton-alikhanov-i-aleksandr-moor-visited-the-new-aviation-hangar-Yamal-Airlines/',
        'TJM-N07':'https://www.utair.ru/support/4/obshie_pravila_perevozki_bagazha/transfer_bagazha',
        'TJM-N08':'https://tjmport.ru/passengers/information/schedule/',
        'TJM-N09':'https://flyredwings.com/november-sale-2026/',
        'TJM-N10':'https://trip.utair.ru/airport/tjm',
        'TJM-N11':'https://goj.aero/flight/season-schedule/',
    }
    def fetch(kv):
        sid,url=kv;rec={'source_id':sid,'url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'urllib text HTTP GET; no browser or checkout'}
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=25) as res:
                b=res.read();rec.update(http_status=res.status,content_type=res.headers.get('Content-Type'),url_final=res.url,bytes=len(b),raw_sha256=hashlib.sha256(b).hexdigest())
            h=Parser();h.feed(b.decode('utf-8',errors='replace'));txt='\n'.join(h.text)
            (ROOT/(sid+'.txt')).write_text(txt+'\n');dump(sid+'_links.json',h.links)
            rec.update(text_sha256=hashlib.sha256((txt+'\n').encode()).hexdigest(),text_file=sid+'.txt',status='FETCHED_TEXT_REQUIRES_CONTENT_CHECK')
        except Exception as e:rec.update(status='FETCH_ERROR',error=repr(e))
        return rec
    receipts=list(ThreadPoolExecutor(max_workers=6).map(fetch,urls.items()));dump('fetch_receipts.json',receipts)
    for r in receipts:print(r['source_id'],r['status'],r.get('bytes'),r.get('error',''))
