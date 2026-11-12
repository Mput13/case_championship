import pathlib,json,csv,hashlib,subprocess,collections,datetime
B=pathlib.Path(__file__).resolve().parent
errors=[];checks=[]
def check(name,condition,detail=''):
 checks.append({'check':name,'pass':bool(condition),'detail':detail})
 if not condition:errors.append(name)
def readj(n):return json.loads((B/n).read_text())
def rows(n):
 with (B/n).open() as f:return list(csv.DictReader(f))
def sha(b):return hashlib.sha256(b).hexdigest()
required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json','input_pins.json','resource_probe_results.json','resource_probe_flights.csv','competitor_seasonal_summary.csv','price_observations.csv','sources.csv']
check('required_outputs_nonempty',all((B/x).is_file() and (B/x).stat().st_size for x in required))
for f in B.rglob('*.json'):
 if f.name not in ['output_manifest.json','validation.json']:
  try:json.loads(f.read_text())
  except Exception as e:errors.append('json:'+str(f)+':'+str(e))
check('json_parse',not any(x.startswith('json:') for x in errors))
progs=readj('programme_candidates.json')['programmes'];pids={x['programme_id'] for x in progs};hyp=readj('hypotheses.json')['hypotheses'];A={r['assumption_id'] for r in rows('assumptions.csv')};S={r['source_id'] for r in rows('sources.csv')}
check('programme_ids_unique',len(pids)==len(progs));check('hypothesis_ids_unique',len({x['hypothesis_id'] for x in hyp})==len(hyp))
check('hypothesis_outcomes_and_tests',all(x.get('stage_A_outcome') and x.get('condition_for_reconsideration') and x.get('distinguishing_test') and x.get('ancestorIDs') for x in hyp))
check('hypothesis_programmes_exist',all(p in pids for x in hyp for p in x['programme_ids']))
check('programme_assumptions_exist',all(a in A for x in progs for a in x['assumption_ids']))
check('route_assumptions_exist',all(a in A for x in progs for r in x['route_changes'] for a in r['assumption_ids']))
check('zero_new_Tu214_explicit',all(x['fleet_variants']['Tu214_new_count']==0 for x in progs))
check('future_KEEP_unknown_explicit',all(x['keep_sales_and_actions']['future_keep_status']=='UNKNOWN' for x in progs))
check('null_not_zero_markets',all(r['delta_journeys']=='UNKNOWN' and r['delta_revenue_net_rub']=='UNKNOWN' for r in rows('market_deltas.csv')))
check('deltas_programmes_exist',all(r['programme_id'] in pids for r in rows('market_deltas.csv')))
check('sources_in_evidence_exist',all(r['source_id'] in S for r in rows('evidence.csv')))
check('source_registry_metadata',all(r['url'] and r['organization'] and r['published_at'] and r['period'] and r['unit'] and r['grain'] and r['status'] and r['coverage'] for r in rows('sources.csv')))
check('csv_data_metadata',all(all(r.get(k) for k in ['unit','period','coverage','status','source_id']) for n in ['evidence.csv','market_deltas.csv','comparison_requests.csv','assumptions.csv','resource_probe_flights.csv','schedule_observations.csv','competitor_seasonal_summary.csv','price_observations.csv'] for r in rows(n)))
for r in readj('input_pins.json'):
 raw=subprocess.check_output(['git','show',r['commit']+':'+r['path']])
 check('exact_pin:'+r['source_id'],sha(raw)==r['sha256'],r['commit']+':'+r['path'])
for r in readj('fetch_receipts.json'):
 if r['status']=='HTTP_READ':
  check('http_body:'+r['source_id'],sha((B/'sources'/f'{r["source_id"]}.html').read_bytes())==r['sha256'])
  check('http_text:'+r['source_id'],sha((B/r['text_path']).read_bytes())==r['text_sha256'])
 else:check('http_error_retained:'+r['source_id'],bool(r.get('error')))
# Canonical city row hashes revalidate the selected upstream rows, not only the copied JSON file.
for fn,tag in [('P02_competitor_products.json','P02'),('P02_calendar_inventory.json','P02'),('P02_fare_panel.json','P02'),('P02_market_coverage.json','P02'),('OLD_claims.json','OLD'),('OLD_sources.json','OLD'),('P03_airport_constraints.json','P03'),('P04_cost_ranges.json','P04')]:
 z=readj('pinned/'+fn)
 ok=all(sha(json.dumps(x['row'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==x['source_row_sha256'] for x in z)
 check('city_rows_hash:'+fn,ok,str(len(z))+' selected rows')
# Date and endpoint arithmetic independent of serialized diagnostic summary.
fl=rows('resource_probe_flights.csv');by=collections.defaultdict(list)
for r in fl:by[(r['programme_id'],r['aircraft_id'])].append(r)
mechanical=[]
for (pid,tail),fs in by.items():
 fs.sort(key=lambda r:r['departure_utc']);prev=None;daily=collections.Counter();ok=True
 for r in fs:
  dep=datetime.datetime.fromisoformat(r['departure_utc']);arr=datetime.datetime.fromisoformat(r['arrival_utc'])
  ok &= abs((arr-dep).total_seconds()/60-float(r['block_minutes_scenario']))<1e-8
  daily[str(dep.date())]+=float(r['block_minutes_scenario'])/60
  if prev:ok &= prev['destination_airport']==r['origin_airport'] and (dep-datetime.datetime.fromisoformat(prev['arrival_utc'])).total_seconds()>=45*60
  prev=r
 ok &= max(daily.values())<=8+1e-8 and fs[0]['origin_airport']==fs[-1]['destination_airport']
 check('rotation_independent:'+pid+':'+tail,ok)
 mechanical.append((pid,tail))
check('7_distinct_rotation_probes',len({x[0] for x in mechanical})==7)
obs=rows('schedule_observations.csv');keys={(r['origin'],r['destination'],r['airline'],r['flight'],r['departure_date']) for r in obs}
check('schedule_dates_unique',len(keys)==len(obs))
check('unknown_TOF_KEJ_not_zero',all(r['published_endpoint_count']=='UNKNOWN' for r in rows('competitor_seasonal_summary.csv') if r['destination'] in ['TOF','KEJ']))
check('stage_A_not_financial_acceptance',readj('readiness.json')['money_verdict']=='UNKNOWN_NOT_CALCULATED')
result={'status':'PASS' if not errors else 'FAIL','checks_passed':sum(x['pass'] for x in checks),'checks_total':len(checks),'errors':errors,'checks':checks,'scope':'Локальная структура, точные источниковые hashes и простая геометрия. Не рынок, не операционная готовность и не финансовая приёмка.','independent_review':'NOT_RUN; эти проверки автора пакета.'}
(B/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if errors:print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(1)
# Manifest excludes itself; all other package files, including this validator and validation receipt, are covered.
files=[]
for f in sorted(B.rglob('*')):
 if not f.is_file() or f.name=='output_manifest.json' or '__pycache__' in f.parts:continue
 files.append({'path':str(f.relative_to(B)),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())})
manifest={'package_id':'UFA-research-v1','status':'STAGE_A_COMPLETE_NOT_ECONOMIC_ACCEPTANCE','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hash_algorithm':'SHA256 exact bytes','manifest_self_excluded':True,'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'files':files}
(B/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'files':len(files),'bytes':manifest['total_bytes'],'manifest_sha256':sha((B/'output_manifest.json').read_bytes())},ensure_ascii=False))
