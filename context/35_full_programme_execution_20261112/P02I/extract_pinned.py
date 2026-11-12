"""Извлечение только международных/городских строк exact git blobs; Git read-only."""
from pathlib import Path
import csv, hashlib, io, json, subprocess

ROOT = Path(__file__).resolve().parent
P02 = 'd9486f113f074c185a94bcc5c0afeef12ea3574f'
BASE = 'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6'
FIVE = 'c18f7640ea36647a05b39089e5293f22dd009f63'
PLAN = 'b4d2ddf690440eb5cd051839cc263cf16b364ca4'
FOREIGN = {'IST','SAW','AYT','TBS','BUS','EVN','GYD','ALA','NQZ','SCO','KGF','TAS','SKD','UGC','NMA','BHK','FRU','OSS','MSQ','TLV','DXB','DWC','AUH','SHJ','CAI','HRG','SSH','UTP','HKT','CXR','DAD','PKX','PEK','URC','HAK','HRI'}
pins=[]
def blob(commit,path):
    b=subprocess.check_output(['git','show',f'{commit}:{path}'])
    pins.append({'commit':commit,'git_path':path,'git_blob':subprocess.check_output(['git','rev-parse',f'{commit}:{path}']).decode().strip(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
    return b
def dump_csv(path,rows):
    if not rows: return
    with (ROOT/path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def select_csv(commit,path,predicate):
    b=blob(commit,path);out=[]
    reader=csv.DictReader(io.StringIO(b.decode()))
    previous_line=1
    for record,row in enumerate(reader,1):
        line_start=previous_line+1; line_end=reader.line_num; previous_line=line_end
        if predicate(row):
            out.append({'source_commit':commit,'source_git_path':path,'source_file_sha256':hashlib.sha256(b).hexdigest(),'source_csv_record_number':record,'source_csv_line_start':line_start,'source_csv_line_end':line_end,'source_row_sha256':hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),**row})
    return out
def main():
    (ROOT/'inputs').mkdir(parents=True,exist_ok=True)
    p=json.loads(blob(PLAN,'context/34_full_programme_plan_20261112/variant_research_plan.json'))
    cities={r['iata'] for r in p['seed_cities']}
    (ROOT/'inputs/seed_cities.json').write_text(json.dumps(p['seed_cities'],ensure_ascii=False,indent=2)+'\n')
    products=select_csv(P02,'context/35_full_programme_execution_20261112/P02/competitor_products.csv',lambda r:(r.get('origin') in FOREIGN or r.get('destination') in FOREIGN) and (r.get('origin') in cities or r.get('destination') in cities))
    dump_csv(Path('inputs/pinned_international_products.csv'),products)
    signals=select_csv(BASE,'data/processed/longlist.csv',lambda r:r.get('iata') in cities)
    # Не переносим авторские demand/score как международный спрос: сохраняем только роль и источники.
    fields=['city','iata','pax_2025','pax_2025_qualifier','pax_source_url','base_carriers','base_source','transfer_zone','transfer_source','rw_support','rw_support_source','ssj_ops','ssj_source','ssj_mro','ssj_mro_source','h24','h24_source']
    dump_csv(Path('inputs/city_signals.csv'),[{k:v for k,v in r.items() if k.startswith('source_') or k in fields} for r in signals])
    tg=select_csv(BASE,'data/raw/telegram/flyredwings.csv',lambda r:any(t in r.get('text','').lower() for t in ['стамбул','батуми','тбилиси','вьетнам','ту-214','ту-204','ереван','казахстан','баку','тель-авив','китай']))
    dump_csv(Path('inputs/rw_international_announcements.csv'),tg)
    for city in ['UFA','GOJ','CEK','PEE','TJM']:
        path=f'context/33_five_city_reassessment_20261112/cities/{city}/routes.csv'
        rows=select_csv(FIVE,path,lambda r:any(r.get(k) in FOREIGN for k in ['origin','destination','from','to','airport']))
        dump_csv(Path(f'inputs/{city}_international_routes.csv'),rows)
        ids={x for r in rows for x in r.get('source_ids','').split(';') if x}
        source_rows=select_csv(FIVE,f'context/33_five_city_reassessment_20261112/cities/{city}/sources.csv',lambda r:r.get('source_id') in ids)
        dump_csv(Path(f'inputs/{city}_international_sources.csv'),source_rows)
    for commit,path in [
        ('b7d74e67dd6c603db049b1915b1afec987e3b458','context/35_full_programme_execution_20261112/P00R/contract_addendum.json'),
        ('79dc698b99dfe866886d32376ed388e85bdd039c','context/35_full_programme_execution_20261112/P03/handoff.json'),
        ('620a0ac4bb11763319c4227485f6a3996b91d367','context/35_full_programme_execution_20261112/P04/handoff.json'),
        ('982f13d9b6c378ed9581125ecc5c40f17dade6a3','context/35_full_programme_execution_20261112/P06/producer_contract.json')]:
        blob(commit,path) # Только hash и чтение; не копия чужого пакета.
    (ROOT/'input_manifest.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'seed_cities':len(cities),'international_products':len(products),'city_signals':len(signals),'rw_announcements':len(tg),'pins':len(pins)},ensure_ascii=False))
if __name__=='__main__': main()
