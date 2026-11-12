#!/usr/bin/env python3
"""Точечные выгрузки из Git: только закреплённые коммиты, без изменения Git."""
from pathlib import Path
import csv, hashlib, io, json, subprocess

ROOT = Path(__file__).resolve().parent
PREFIX = 'context/35_full_programme_execution_20261112/'
PINS = {
 'PLAN': '65cab12d2eae49dc91d1f77dd4860bc9bd7e20d2',
 'AUTHOR': 'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',
 'FIVE': 'c18f7640ea36647a05b39089e5293f22dd009f63',
 'P00R': 'b7d74e67dd6c603db049b1915b1afec987e3b458',
 'P02': 'd9486f113f074c185a94bcc5c0afeef12ea3574f',
 'P03': '79dc698b99dfe866886d32376ed388e85bdd039c',
 'P04': '620a0ac4bb11763319c4227485f6a3996b91d367',
 'P06': '982f13d9b6c378ed9581125ecc5c40f17dade6a3',
}
MOS = {'MOW','ZIA','DME','SVO','VKO'}
DEST = {'ARH','MRV','VOG','MCX','KGD','GOJ','KUF','OMS','GSV','AER','KRO','CEK','PEE','IJK','REN','TJM','NOJ','MQF','SGC','HMA','LED','NYA','TBW'}
PAIRS = {frozenset(x) for x in [('ARH','MRV'),('VOG','MCX'),('KGD','GOJ'),('KGD','KUF'),('GSV','MRV'),('KUF','OMS'),('AER','VOG'),('KRO','MRV'),('AER','KGD'),('CEK','KUF'),('OMS','PEE'),('CEK','IJK'),('REN','TJM'),('CEK','NOJ'),('OMS','REN'),('MQF','SGC'),('HMA','PEE'),('MRV','VOG')]}
MANIFEST=[]

def digest(b): return hashlib.sha256(b).hexdigest()
def canonical(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def write_json(name,o):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def read(label,path):
 sha=PINS[label];b=subprocess.check_output(['git','show',sha+':'+path])
 oid=subprocess.check_output(['git','rev-parse',sha+':'+path],text=True).strip()
 who,when=subprocess.check_output(['git','show','-s','--format=%an%n%aI',sha],text=True).splitlines()[:2]
 return b,dict(input_id=label+'_'+Path(path).name,commit=sha,git_path=path,git_blob_oid=oid,source_blob_sha256=digest(b),source_bytes=len(b),read_method='git show exact_SHA:path',url=f'https://github.com/Mput13/case_championship/blob/{sha}/{path}',organization='команда кейса Red Wings; Git author: '+who,publication_date=when,period='см. период/valid_from/valid_to/as_of каждой исходной строки; commit date не дата факта',unit='см. исходные именованные поля; строки model money не финансовый прогноз',granularity='строки и поля указанного input; CSV logical row / JSON object / numbered source lines',status='закреплённый вход с происхождением; не самостоятельный live/operational/economic admission',coverage='только выбранные московские строки и затронутые пары; полнота источника не заявлена')
def export_csv(label,path,pred,out=None):
 b,m=read(label,path);rows=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))));sel=[]
 for n,r in enumerate(rows,1):
  if pred(r):
   sel.append(dict(r,_source_input_id=m['input_id'],_source_data_row=n,_source_row_sha256=digest(canonical(r)),_source_commit=m['commit'],_source_blob_sha256=m['source_blob_sha256']))
 out=out or ('inputs/'+label+'_'+Path(path).name)
 p=ROOT/out;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(sel[0]) if sel else list(rows[0])+['_source_input_id','_source_data_row','_source_row_sha256','_source_commit','_source_blob_sha256']);w.writeheader();w.writerows(sel)
 m.update(extract_path=out,extract_sha256=digest(p.read_bytes()),source_rows=len(rows),selected_rows=len(sel),row_number_definition='1-based logical CSV data row, header excluded; canonical row SHA256 uses UTF-8 sorted compact JSON')
 MANIFEST.append(m);return sel
def export_json(label,path,transform=lambda o:o,out=None):
 b,m=read(label,path);obj=json.loads(b);ex=transform(obj);out=out or ('inputs/'+label+'_'+Path(path).name);write_json(out,ex)
 m.update(extract_path=out,extract_sha256=digest((ROOT/out).read_bytes()),selection='описана структурой извлечения; исходный blob не копируется целиком, если объект отфильтрован')
 MANIFEST.append(m);return ex
def market(r):
 a=r.get('origin',r.get('from_iata',r.get('from','')));b=r.get('destination',r.get('to_iata',r.get('to','')))
 return bool({a,b}&MOS) or frozenset((a,b)) in PAIRS

if __name__=='__main__':
 export_json('PLAN','context/34_full_programme_plan_20261112/variant_research_plan.json',lambda o:{k:([r for r in o[k] if any(x in str(r) for x in ['C08','C19','C25'])] if k=='legacy_hypotheses' else o[k]) for k in ['legacy_hypotheses','legacy_direct_rotation_seeds','legacy_policy']})
 export_json('PLAN','context/23_night_run_20261110/morning_report_review/route_C08.json')
 export_csv('PLAN','context/23_night_run_20261110/integration/hypothesis_frontier/519998ed/inventory35.csv',lambda r:r['candidate_id'] in {'C08','C19','C25'})
 export_csv('AUTHOR','data/processed/network_routes.csv',lambda r:r['variant'].startswith('Прямые MOW'))
 export_csv('AUTHOR','data/assumptions/network.csv',lambda r:r['parameter'] in {'route_factor','route_factor_south','block_speed_kmh','block_fixed_h','seats','weeks_per_year','min_freq_week','spare_aircraft','capture_open','capture_competitive','block_h_per_day'})
 export_csv('AUTHOR','data/manual/known_flows.csv',market)
 export_csv('AUTHOR','data/manual/airport_tech.csv',lambda r:r['iata'] in DEST|MOS)
 export_csv('AUTHOR','data/processed/catchments.csv',lambda r:r['iata'] in DEST|MOS)
 # Только код расчёта часов и общей физической пары, без полного исходного fixture.
 b,m=read('AUTHOR','src/network_model.py');lines=b.decode().splitlines();segments=[(487,512),(515,576)]
 out='inputs/AUTHOR_network_model_excerpts.txt';(ROOT/out).write_text('\n'.join(f'{n}: {lines[n-1]}' for a,z in segments for n in range(a,z+1))+'\n')
 m.update(extract_path=out,extract_sha256=digest((ROOT/out).read_bytes()),source_line_ranges=segments);MANIFEST.append(m)
 for f in ['competitor_products.csv','calendar_inventory.csv','market_coverage.csv','historical_route_context.csv','historical_demand_context.csv']:
  export_csv('P02',PREFIX+'P02/'+f,market)
 export_csv('P02',PREFIX+'P02/clock_conflicts.csv',lambda r: any(k in str(r) for k in MOS))
 export_csv('P02',PREFIX+'P02/ordered_itineraries.csv',lambda r:False) # Явно пустой московский ordered-leg корпус; RT581/651 не московский вход.
 export_csv('P03',PREFIX+'P03/airport_constraints.csv',lambda r:r['iata'] in DEST|MOS)
 export_csv('P03',PREFIX+'P03/aircraft_type_parameters.csv',lambda r:r['aircraft_type'].startswith(('RRJ','SJ100','TU214')))
 export_csv('P04',PREFIX+'P04/thresholds.csv',lambda r:True)
 export_csv('P04',PREFIX+'P04/financial_cost_coverage.csv',lambda r:any(k in str(r) for k in MOS|{'all','ALL','base','aircraft'}))
 export_json('P00R',PREFIX+'P00R/contract_addendum.json')
 export_json('P06',PREFIX+'P06/producer_contract.json',lambda o:{k:o[k] for k in ['version','status','encoding','context_required','bundle_required','owners','record_templates'] if k in o},'inputs/P06_contract_reference.json')
 # Source pin of reassessment. Only conclusions governing MOW and source acceptance.
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only',PINS['FIVE'],'context/33_five_city_reassessment_20261112'],text=True).splitlines()
 for p in paths:
  if p.endswith('/README.txt'):
   b,m=read('FIVE',p);text=b.decode();keep=[(i+1,l) for i,l in enumerate(text.splitlines()) if any(k in l for k in ['MOW','одинаков','не является','условн','500'])]
   out='inputs/FIVE_relevant_lines.json';write_json(out,keep);m.update(extract_path=out,extract_sha256=digest((ROOT/out).read_bytes()));MANIFEST.append(m);break
 write_json('input_manifest.json',dict(pins=PINS,inputs=MANIFEST,coverage='Точечный московский срез и пары материалов C08/C19/C25/авторских треугольников; не общий архив.',unknown_policy='UNKNOWN / JSON null; пустой extract не доказывает отсутствия рынка'))
 print(json.dumps({m['extract_path']:m.get('selected_rows','JSON/excerpt') for m in MANIFEST},ensure_ascii=False,indent=2))
