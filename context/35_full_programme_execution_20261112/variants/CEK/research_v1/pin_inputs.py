from pathlib import Path
import subprocess,hashlib,csv,io,json
ROOT=Path(__file__).resolve().parent
PINS={'BASE':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63','PLAN':'65cab12d2eae49dc91d1f77dd4860bc9bd7e20d2','P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
manifest=[]
def pull(key,path,kind='filter'):
 b=subprocess.check_output(['git','show',PINS[key]+':'+path]); s=b.decode('utf-8-sig'); out=ROOT/'inputs'/key/(Path(path).name);out.parent.mkdir(parents=True,exist_ok=True)
 item={'source_id':'PIN-'+key+'-'+Path(path).stem,'commit':PINS[key],'path':path,'blob_oid':subprocess.check_output(['git','rev-parse',PINS[key]+':'+path],text=True).strip(),'sha256':hashlib.sha256(b).hexdigest(),'selected_path':str(out.relative_to(ROOT)),'selection':'CEK / Челябинск в значениях полей; строки сохраняют исходный line и hash','source_rows':[]}
 if path.endswith('.csv'):
  reader=csv.DictReader(io.StringIO(s)); rows=[]
  for n,r in enumerate(reader,2):
   if (kind=='all' or (key=='BASE' and path.endswith('network_routes.csv') and (r.get('from')=='CEK' or r.get('to')=='CEK')) or (key=='BASE' and path.endswith('longlist.csv') and r.get('iata')=='CEK') or (key not in ['BASE'] and any('CEK' in str(v) or 'Челябин' in str(v) for v in r.values()))):
    h=hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();item['source_rows'].append({'source_csv_line':n,'canonical_row_sha256':h});rows.append({**r,'source_commit':PINS[key],'source_path':path,'source_csv_line':n,'source_row_sha256':h})
  with out.open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(reader.fieldnames)+['source_commit','source_path','source_csv_line','source_row_sha256']);w.writeheader();w.writerows(rows)
  item.update(selected_count=len(rows),row_hash_definition='SHA256 UTF-8 JSON исходных полей; sort_keys=True,separators=(comma,colon),ensure_ascii=False')
 elif kind=='all':out.write_bytes(b);item['selection']='Целиком: компактный общий контракт/метаданные, без fixture'
 elif key=='PLAN':
  j=json.loads(s);sel={'legacy_hypotheses':[x for x in j['legacy_hypotheses'] if 'CEK' in str(x)],'seed_cities':[x for x in j['seed_cities'] if 'CEK' in str(x)],'legacy_policy':j['legacy_policy']};out.write_text(json.dumps(sel,ensure_ascii=False,indent=2)+'\n');item['selection']='CEK seed и относящиеся к CEK legacy гипотезы'
 else: raise ValueError(path)
 item['selected_sha256']=hashlib.sha256(out.read_bytes()).hexdigest();manifest.append(item)
pull('BASE','data/processed/network_routes.csv');pull('BASE','data/manual/rw_routes_now.csv');pull('BASE','data/processed/longlist.csv')
for f in ['sources.csv','claims.csv','routes.csv','features.csv','model_routes_extract.csv']:pull('FIVE','context/33_five_city_reassessment_20261112/cities/CEK/'+f,'all')
pull('PLAN','context/34_full_programme_plan_20261112/variant_research_plan.json')
for f in ['calendar_inventory.csv','market_coverage.csv','competitor_products.csv','physical_adjacent_leg_candidates.csv','ordered_itineraries.csv','clock_conflicts.csv','historical_demand_context.csv','historical_route_context.csv','demand_history_coverage.csv','alternatives_contract.csv','season_coverage.csv','market_binding_requests.csv','competitor_responses.csv','fare_panel.csv']:
 pull('P02','context/35_full_programme_execution_20261112/P02/'+f)
for f in ['airport_coverage.csv']:pull('P04','context/35_full_programme_execution_20261112/P04/'+f)
for f in ['thresholds.csv']:pull('P04','context/35_full_programme_execution_20261112/P04/'+f,'all')
for key,f in [('P00R','contract_addendum.json'),('P03','sp_adapter/interface_contract.json'),('P06','producer_contract.json')]:pull(key,'context/35_full_programme_execution_20261112/'+key+'/'+f,'all')
(ROOT/'source_pins.json').write_text(json.dumps({'as_of':'2026-11-12','pins':PINS,'records':manifest,'branch_policy':'Только git show exact SHA; Git не изменяется; PLAN закреплён на стартовом HEAD, не moving branch.'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({x['source_id']:x.get('selected_count','contract') for x in manifest},ensure_ascii=False))
