import subprocess,hashlib,csv,io,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
P='context/35_full_programme_execution_20261112/'
pins={
'BASE':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',
'FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63',
'PLAN':'b4d2ddf690440eb5cd051839cc263cf16b364ca4',
'P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458',
'P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f',
'P03':'79dc698b99dfe866886d32376ed388e85bdd039c',
'P04':'620a0ac4bb11763319c4227485f6a3996b91d367',
'P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
files={
'BASE':['data/manual/rw_routes_now.csv','data/manual/route_competitors.csv','data/manual/known_flows.csv','data/manual/airport_tech.csv','data/manual/rail_schedule_spotchecks.csv','data/manual/fare_offer_spotchecks.csv','data/processed/catchments.csv','data/processed/destinations.csv','data/processed/network_routes.csv','data/assumptions/bases.csv','data/external/colleagues/route_product_cards.csv','context/12_network_economics/block_times.csv','context/12_network_economics/published_flight_dates.csv'],
'PLAN':['context/34_full_programme_plan_20261112/city_research_seed.csv','context/34_full_programme_plan_20261112/variant_research_plan.json','context/34_full_programme_plan_20261112/common_spec.json'],
'P00R':[P+'P00R/contract_addendum.json'],
'P02':[P+'P02/'+f+'.csv' for f in ['competitor_products','fare_panel','calendar_inventory','market_coverage','historical_demand_context','competitor_responses','season_coverage','alternatives_contract','clock_conflicts']],
'P03':[P+'P03/operating_rules.json']+[P+'P03/'+f+'.csv' for f in ['airport_constraints','minimum_resource_required','aircraft_type_parameters','existing_commitments']],
'P04':[P+'P04/'+f+'.csv' for f in ['airport_coverage','airport_reference_examples','event_rate_map','cost_ranges','thresholds']],
'P06':[P+'P06/README.md',P+'P06/producer_contract.json'],
'FIVE':['context/33_five_city_reassessment_20261112/common_economics/report.md']}
manifest=[]
for label,paths in files.items():
 for path in paths:
  ref=pins[label]+':'+path
  try: raw=subprocess.check_output(['git','show',ref],stderr=subprocess.PIPE)
  except subprocess.CalledProcessError as e:
   manifest.append({'label':label,'commit':pins[label],'path':path,'error':e.stderr.decode()});continue
  item={'label':label,'commit':pins[label],'path':path,'blob':subprocess.check_output(['git','rev-parse',ref]).decode().strip(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'read_status':'read'}
  if path.endswith('.csv'):
   reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
   rows=list(reader);selected=[]
   for idx,row in enumerate(rows,2):
    if 'KUF' in json.dumps(row,ensure_ascii=False) or 'Самар' in json.dumps(row,ensure_ascii=False):
     row=dict(row);rh=hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();row['_source_line']=idx;row['_source_row_sha256']=rh;row['_source_commit']=pins[label];row['_source_path']=path;selected.append(row)
   dest=ROOT/'inputs'/(label+'_'+pathlib.Path(path).name)
   if selected:
    with dest.open('w',newline='') as f:
     w=csv.DictWriter(f,fieldnames=list(selected[0]));w.writeheader();w.writerows(selected)
    item['extract_path']=str(dest.relative_to(ROOT));item['extract_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
   item['rows_total']=len(rows);item['rows_KUF']=len(selected);item['columns']=reader.fieldnames
  else:
   text=raw.decode();item['KUF_lines']=[s for s in text.splitlines() if 'KUF' in s or 'Самар' in s][:40]
  manifest.append(item)
(ROOT/'source_pins.json').write_text(json.dumps({'pins':pins,'inputs':manifest,'rule':'Only KUF-matching CSV rows materialized; full source blobs hashed, no copied fixture. Line is CSV record index + header, not physical multiline line.'},ensure_ascii=False,indent=2))
for m in manifest:
 print(m['label'],pathlib.Path(m['path']).name,m.get('rows_KUF','text'),m.get('columns',[])[:12],m.get('error','')[:100])
