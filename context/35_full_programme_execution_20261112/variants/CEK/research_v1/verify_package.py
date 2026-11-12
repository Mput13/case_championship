from pathlib import Path
import csv,json,hashlib,datetime,collections,subprocess
R=Path(__file__).resolve().parent
checks=[]
def check(name,ok,detail=''):checks.append({'check':name,'pass':bool(ok),'detail':detail})
def js(p):return json.loads((R/p).read_text())
def rows(p):return list(csv.DictReader((R/p).open()))
required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json','source_pins.json','sources.csv','flight_patterns.csv','calendar_design.csv','resource_checks.json','README.md','web_receipts.json','search_receipts.json']
check('required_files',all((R/p).is_file() for p in required),required)
for p in R.rglob('*.json'):
 if p.name not in ['output_manifest.json','verification.json']:js(str(p.relative_to(R)))
check('json_parse',True)
pins=js('source_pins.json')
for pin in pins['records']:
 p=R/pin['selected_path'];check('selected_hash:'+pin['source_id'],hashlib.sha256(p.read_bytes()).hexdigest()==pin['selected_sha256'])
 b=subprocess.check_output(['git','show',pin['commit']+':'+pin['path']]);check('source_blob_hash:'+pin['source_id'],hashlib.sha256(b).hexdigest()==pin['sha256'])
 if p.suffix=='.csv':
  rr=rows(pin['selected_path']);original=list(csv.DictReader(__import__('io').StringIO(b.decode('utf-8-sig'))));ok=True
  for r in rr:
   n=int(r['source_csv_line']);v={k:v for k,v in r.items() if k not in ['source_commit','source_path','source_csv_line','source_row_sha256']}
   digest=hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
   ok=ok and digest==r['source_row_sha256'] and v==original[n-2]
  check('row_provenance:'+pin['source_id'],ok,str(len(rr))+' rows')
sourceids={x['source_id'] for x in rows('sources.csv')}
for f in ['evidence.csv','market_deltas.csv']:
 missing=[]
 for r in rows(f):
  for s in r['source_id'].split(';'):
   if s and s not in sourceids:missing.append(s)
 check('source_links:'+f,not missing,sorted(set(missing)))
A=rows('assumptions.csv');aids={r['assumption_id'] for r in A}
check('assumptions_unique',len(aids)==len(A))
check('assumptions_have_owner_range_reason_refinement',all(all(r[k] for k in ['selected_by','why','range_or_UNKNOWN','decision_impact','how_to_refine']) for r in A))
h=js('hypotheses.json')['hypotheses'];check('eight_explainable_hypotheses',len(h)==8 and len({x['hypothesis_id'] for x in h})==8 and all(all(x.get(k) for k in ['signal','source','mechanism','counterfactual','distinguishing_test','ancestorIDs','outcome','condition_of_reconsideration']) for x in h))
pp=js('programme_candidates.json')['programmes'];pids={x['programme_id'] for x in pp};pat=rows('flight_patterns.csv');pmap={x['pattern_id']:x for x in pat}
check('programme_links',all(all(i in pmap for i in x['flight_pattern_ids']) for x in pp))
check('no_tu214_and_no_synthetic_finance',all(x['new_tu214']==0 and x['reserve_units'] is None and 'initial_positions' in x for x in pp) and js('case.json')['ranking'] is None and not js('case.json')['unconditional_profitability_claim'])
check('calendar_has_24_months_each',all(len([m for m in rows('calendar_design.csv') if m['programme_id']==x])==24 for x in pids))
check('calendar_no_2027_current_flight_zero',all(x['future_KEEP_sectors']=='UNKNOWN' for x in rows('calendar_design.csv')))
mechanical=[]
for pid in sorted(pids):
 flights=[r for r in pat if r['programme_id']==pid];tails={r['aircraft_id'] for r in flights};errors=[];byday=collections.defaultdict(int)
 for tail in tails:
  rr=sorted([r for r in flights if r['aircraft_id']==tail],key=lambda r:int(r['start_week_minute']))
  for a,b in zip(rr,rr[1:]):
   if a['destination']!=b['origin']:errors.append('location')
   if int(b['start_week_minute'])-int(a['end_week_minute'])<45:errors.append('turn')
  if rr[-1]['destination']!=rr[0]['origin']:errors.append('week_wrap_location')
  if int(rr[0]['start_week_minute'])+10080-int(rr[-1]['end_week_minute'])<45:errors.append('week_wrap_turn')
  for r in rr:byday[(tail,r['weekday_iso'])]+=int(r['block_minutes'])
 ref=next(x for x in js('resource_checks.json')['checks'] if x['programme_id']==pid)
 check('mechanical:'+pid,not errors and max(byday.values())<=480 and sum(int(x['block_minutes']) for x in flights)==ref['block_minutes_week'],{'tails':len(tails),'block_minutes_week':ref['block_minutes_week'],'errors':errors})
 # recurrence connection checks, both directions
 if pid in ['CEK-H1','CEK-H0']:
  gaps=[]
  for d in range(2,8):
   eastin=[x for x in flights if x['aircraft_id']=='E1' and int(x['weekday_iso'])==d and x['destination'] in ['CEK','SVX']][0]
   westout=[x for x in flights if x['aircraft_id']=='W1' and int(x['weekday_iso'])==d and x['destination']=='MRV'][0]
   gaps.append(int(westout['start_week_minute'])-int(eastin['end_week_minute']))
   if d<7:
    westin=[x for x in flights if x['aircraft_id']=='W1' and int(x['weekday_iso'])==d and x['origin']=='MRV'][0]
    eastout=[x for x in flights if x['aircraft_id']=='E1' and int(x['weekday_iso'])==d and x['origin'] in ['CEK','SVX']][0]
    gaps.append(int(eastout['start_week_minute'])-int(westin['end_week_minute']))
  check('conditional_connections_90min:'+pid,min(gaps)>=90,{'min':min(gaps),'max':max(gaps),'MCT_operational_acceptance':False})
check('all_29_markets_retained',len(rows('market_deltas.csv'))==29 and {r['destination'] for r in rows('market_deltas.csv')}=={r['destination'] for r in rows('inputs/FIVE/routes.csv')})
check('all_15_stage_b_requests',len(rows('comparison_requests.csv'))==15 and all(x['status']=='ОТКРЫТО_STAGE_B' for x in rows('comparison_requests.csv')))
check('zero_quote_gap_not_zero_market',len(rows('inputs/P02/fare_panel.csv'))==0 and all(x['status']=='УСЛОВНЫЙ_РЫНОК_НЕ_ЭКОНОМИЧЕСКИЙ_ОТКАЗ' for x in rows('market_deltas.csv')))
check('readiness_boundaries',not js('readiness.json')['physical_seat_admission'] and not js('readiness.json')['operations_acceptance'] and not js('readiness.json')['financial_acceptance'] and not js('readiness.json')['strategy_complete'])
result={'as_of':'2026-11-12','status':'PASS' if all(x['pass'] for x in checks) else 'FAIL','checks_passed':sum(x['pass'] for x in checks),'checks_total':len(checks),'checks':checks,'authority':'Самопроверка автора пакета; независимая приёмка не проводилась.','does_not_prove':['Рынок/спрос/нетто-тариф','Свободные борта/crew/MRO/reserve','Договоры/slots/MCT/защиту','Экономику/финансирование/достижение№2']}
(R/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
files=[]
for p in sorted(R.rglob('*')):
 if p.is_file() and p.name!='output_manifest.json':files.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
manifest={'package':'CEK/research_v1','status':'STAGE_A_COMPLETE_CONDITIONAL' if result['status']=='PASS' else 'CHECK_FAILED','root':str(R),'as_of':'2026-11-12','file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'hash_algorithm':'SHA256','self_exclusion':'Манифест исключает собственный файл; его SHA256 передаётся координатору отдельно.','files':files,'inputs':'source_pins.json: exact commits, blobs, selected row IDs/hashes','scope':'Только назначенный каталог; никаких Git мутаций или общих файлов.'}
(R/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':str(result['checks_passed'])+'/'+str(len(checks)),'files':len(files),'bytes':manifest['total_bytes'],'manifest_sha256':hashlib.sha256((R/'output_manifest.json').read_bytes()).hexdigest()},ensure_ascii=False))
if result['status']!='PASS':
 print(json.dumps([x for x in checks if not x['pass']],ensure_ascii=False,indent=2));raise SystemExit(1)
