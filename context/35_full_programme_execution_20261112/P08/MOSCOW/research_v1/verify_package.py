#!/usr/bin/env python3
"""Проверка сохранённых результатов независимо от импорта генератора."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
import calendar, csv, hashlib, io, json, math, subprocess

R=Path(__file__).resolve().parent
CHECKS=[]
def check(name,ok,details):
 CHECKS.append(dict(check=name,status='PASS' if ok else 'FAIL',evidence=details))
def load(p):return json.loads((R/p).read_text())
def rows(p):return list(csv.DictReader((R/p).open()))
def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))

M=load('input_manifest.json');ref_errors=[];selected=0
for item in M['inputs']:
 b=subprocess.check_output(['git','show',item['commit']+':'+item['git_path']])
 if digest(b)!=item['source_blob_sha256']:ref_errors.append(item['input_id']+':source hash')
 if digest((R/item['extract_path']).read_bytes())!=item['extract_sha256']:ref_errors.append(item['input_id']+':extract hash')
 if item['extract_path'].endswith('.csv'):
  source=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
  for row in rows(item['extract_path']):
   selected+=1;n=int(row['_source_data_row']);orig=source[n-1]
   if digest(canonical(orig))!=row['_source_row_sha256']:ref_errors.append(f"{item['input_id']}:{n}:row hash")
   if {k:v for k,v in row.items() if not k.startswith('_source_')}!=orig:ref_errors.append(f"{item['input_id']}:{n}:contents")
check('exact_git_blobs_extracts_and_logical_row_hashes',not ref_errors,dict(inputs=len(M['inputs']),selected_csv_rows=selected,errors=ref_errors[:15]))

sources=load('sources_registry.json');errs=[]
for s in sources:
 for field in ['source_id','url','organization','publication_date','period','unit','granularity','status','coverage','retrieved_at']:
  if field not in s:errs.append(s['source_id']+':missing:'+field)
 if s.get('saved_path') and digest((R/s['saved_path']).read_bytes())!=s['saved_text_sha256']:errs.append(s['source_id']+':text hash')
check('source_receipts_metadata_and_saved_text_hashes',not errs,dict(records=len(sources),saved=sum(bool(s.get('saved_path')) for s in sources),errors=errs))

source_map={s['source_id']:s for s in sources};ge=[]
for row in rows('ground_products.csv'):
 text=(R/source_map[row['source_id']]['saved_path']).read_text().splitlines()
 extract='\n'.join(text[int(row['source_line_start'])-1:int(row['source_line_end'])])
 if digest(extract.encode())!=row['source_extract_sha256']:ge.append(row['ground_product_id']+':line hash')
 elapsed=(datetime.fromisoformat(row['arrival_local'])-datetime.fromisoformat(row['departure_local'])).total_seconds()/60
 if elapsed!=int(row['elapsed_min']):ge.append(row['ground_product_id']+':duration')
 if row['comparable_RT_basket']!='False' or row['open_seats']!='UNKNOWN':ge.append(row['ground_product_id']+':admission')
check('ground_source_line_hashes_and_elapsed_times',not ge,dict(ground_products=len(rows('ground_products.csv')),errors=ge,meaning='Направленные строки2026; не сопоставимая RT корзина/открытые кресла.'))

B=load('programme_candidates.json');P={p['programme_id']:p for p in B['programmes']};F=load('dated_templates/flights.json');FI={f['template_flight_id']:f for f in F}
rot=rows('dated_templates/rotations.csv');rt=rows('dated_templates/trip_windows.csv');pairs=rows('programme_pairs.csv')
check('unique_flight_and_programme_ids',len(FI)==len(F) and len(P)==len(B['programmes']),dict(flights=len(F),programmes=len(P)))
check('only_physical_airports_in_flights',all(f['origin_airport'] not in ['MOW','UNKNOWN'] and f['destination_airport'] not in ['MOW','UNKNOWN'] for f in F), 'MOW отсутствует в физических плечах')
check('no_inventory_or_economic_acceptance_from_templates',all(f['saleable_seats'] is None and f['operator_id'] is None and not f['inventory_admitted'] for f in F) and all(not p['operational_admission'] and p['economic_evaluation'].startswith('NOT_RUN') and all(p[k] is None for k in ['passengers_incremental','revenue_incremental_rub','full_result_incremental_rub','cash_minimum_rub']) for p in P.values()),'Все неизвестные capacity/operator/financial outputs остаются null, статусы не admission.')
groups=defaultdict(list)
for p in P.values():groups[p['comparison_group_id']].append(p)
check('same_resource_for_three_forms',all(len(pp)==3 and len({p['resource_envelope_id'] for p in pp})==1 and len({p['physical_base_airport'] for p in pp})==1 for pp in groups.values()),dict(groups=len(groups),meaning='same conditional fleet/base/date envelope; equal BH не заявлены'))
check('all_new_Tu214_maincase_zero',all(p['maincase_new_Tu214']==0 for p in P.values()),'Действующий Tu бизнес не обнулён; запрет новых ресурсов относится только к maincase новой поставки.')

byrot=defaultdict(list)
for f in F:byrot[f['rotation_id']].append(f)
e=[];timecount=0;unknown=0
for row in rot:
 seq=sorted(byrot[row['rotation_id']],key=lambda x:x['leg_order']);path=row['ordered_airports'].split('>');base=P[row['programme_id']]['physical_base_airport']
 if [seq[0]['origin_airport']]+[f['destination_airport'] for f in seq]!=path or path[0]!=path[-1] or path[0]!=base:e.append(row['rotation_id']+':adjacency')
 if any(seq[i]['destination_airport']!=seq[i+1]['origin_airport'] for i in range(len(seq)-1)):e.append(row['rotation_id']+':physical break')
 if all(f['arrival_utc'] is not None and f['departure_utc'] is not None for f in seq):
  timecount+=1
  for i,f in enumerate(seq):
   if dt(f['arrival_utc'])<=dt(f['departure_utc']) or (dt(f['arrival_utc'])-dt(f['departure_utc'])).total_seconds()/60!=f['block_reference_min']:e.append(f['template_flight_id']+':block')
   if i and (dt(f['departure_utc'])-dt(seq[i-1]['arrival_utc'])).total_seconds()/60<45:e.append(row['rotation_id']+':turn')
   local=(dt(f['departure_utc'])+timedelta(hours=f['departure_utc_offset_hours'])).strftime('%Y-%m-%d %H:%M')
   if local!=f['departure_local']:e.append(f['template_flight_id']+':local clock')
  blocksum=sum(f['block_reference_min'] for f in seq)
  if blocksum!=int(row['block_reference_min']):e.append(row['rotation_id']+':total block')
  elapsed=(dt(seq[-1]['arrival_utc'])-dt(seq[0]['departure_utc'])).total_seconds()/60
  if elapsed!=float(row['elapsed_reference_min']):e.append(row['rotation_id']+':elapsed')
 else:
  unknown+=1
  if row['block_reference_min']!='UNKNOWN':e.append(row['rotation_id']+':unknown converted to number')
check('rotations_close_adjacency_times_turns_and_unknowns',not e,dict(rotations=len(rot),fully_timed=timecount,explicit_partial=unknown,errors=e[:15]))

overlaps=[]
for pid in P:
 ff=sorted([f for f in F if f['programme_id']==pid and f['departure_utc'] and f['arrival_utc']],key=lambda f:f['departure_utc'])
 for a,b in zip(ff,ff[1:]):
  if dt(a['arrival_utc'])>dt(b['departure_utc']):overlaps.append((a['template_flight_id'],b['template_flight_id']))
check('active_tail_has_no_overlap_within_each_alternative',not overlaps,dict(errors=overlaps[:10],scope='KEEP/standby/crew реальных IDs отсутствуют, эта проверка их не подтверждает'))

freqerrors=[]
for pid,p in P.items():
 week=[f for f in F if f['programme_id']==pid and f['reference_week']=='2028-07-10' and f['rotation_id'].endswith(('2028-07-10','2028-07-14'))]
 counts=Counter((f['origin_airport'],f['destination_airport']) for f in week)
 if len(week)!=p['weekly_physical_legs']:freqerrors.append(pid+':weekly legs')
 if all(f['block_reference_min'] is not None for f in week):
  if abs(sum(f['block_reference_min'] for f in week)/60-p['weekly_reference_block_h'])>0.000051:freqerrors.append(pid+':BH')
 for row in [r for r in pairs if r['programme_id']==pid]:
  a,z=row['origin_a'],row['origin_b']
  if counts[(a,z)]!=int(row['departures_a_to_b_week']) or counts[(z,a)]!=int(row['departures_b_to_a_week']):freqerrors.append(pid+':directed frequency')
rotation_ids={r['rotation_id'] for r in rot}
for pair in pairs:
 for rid in pair['full_rotation_ids'].split(';'):
  if rid not in rotation_ids:freqerrors.append(pair['programme_id']+':rotation reference')
check('weekly_leg_counts_BH_and_directional_pair_frequencies',not freqerrors,dict(pairs=len(pairs),errors=freqerrors[:15]))

cal=rows('monthly_calendar.csv');ce=[];annual=defaultdict(int)
for row in cal:
 year,month=map(int,row['month'].split('-'));expected=[date(year,month,n).isoformat() for n in range(1,calendar.monthrange(year,month)[1]+1) if date(year,month,n).isoweekday() in [1,5]]
 if row['scenario_service_dates'].split(';')!=expected:ce.append(row['programme_id']+row['month'])
 if row['actual_project_legs']!='UNKNOWN' or row['ready_date']!='UNKNOWN':ce.append(row['programme_id']+':readiness manufactured')
 if row['programme_id']=='MOW-C19-T':annual[year]+=len(expected)
check('24_month_calendar_is_date_enumeration_not_52_weeks',not ce and all(sum(r['programme_id']==p for r in cal)==24 for p in P) and annual[2027]==105 and annual[2028]==104,dict(rows=len(cal),C19_T_proposed_service_days=dict(annual),errors=ce[:10],meaning='105/104 только календарь предлагаемой формы, не годовая программа/пассажиры'))

te=[]
for t in rt:
 if t['useful_calendar_found']!='True':continue
 of=[FI[i] for i in t['outbound_flight_ids'].split(';')];bf=[FI[i] for i in t['return_flight_ids'].split(';')]
 if of[0]['origin_airport']!=t['origin'] or of[-1]['destination_airport']!=t['destination'] or bf[0]['origin_airport']!=t['destination'] or bf[-1]['destination_airport']!=t['origin']:te.append(t['programme_id']+':endpoints')
 oa=dt(of[-1]['arrival_utc'])+timedelta(hours=of[-1]['arrival_utc_offset_hours']);bd=dt(bf[0]['departure_utc'])+timedelta(hours=bf[0]['departure_utc_offset_hours']);nights=(bd.date()-oa.date()).days
 if nights!=int(t['stay_nights']) or not int(t['target_min_nights'])<=nights<=int(t['target_max_nights']):te.append(t['programme_id']+':stay')
 if t['friday_to_monday_3_nights_found']=='True':
  wo=[FI[i] for i in t['weekend_outbound_flight_ids'].split(';')];wr=[FI[i] for i in t['weekend_return_flight_ids'].split(';')]
  if datetime.fromisoformat(wo[0]['departure_local']).isoweekday()!=5 or datetime.fromisoformat(wr[0]['departure_local']).isoweekday()!=1:te.append(t['programme_id']+':weekend')
check('real_dated_outbound_and_return_paths_for_each_trip_test',not te,dict(trip_rows=len(rt),errors=te[:15],limit='Цена/кресла/MCT/door-to-door не подтверждаются календарной геометрией.'))
sample={t['programme_id']+':'+t['origin']:t for t in rt if t['reference_week']=='2028-07-10' and t['programme_id'].startswith('MOW-C19')}
expected={'MOW-C19-T:VOG':True,'MOW-C19-T:MCX':False,'MOW-C19-C:VOG':True,'MOW-C19-C:MCX':True,'MOW-C19-O:VOG':True,'MOW-C19-O:MCX':False}
check('C19_weekend_counterexample_is_directional',all((sample[k]['friday_to_monday_3_nights_found']=='True')==v for k,v in expected.items()),expected)
check('C08_chain_budget_failure_not_general_economic_rejection',P['MOW-C08-C']['max_daily_reference_block_h']>10 and P['MOW-C08-T']['max_daily_reference_block_h']<10 and not P['MOW-C08-C']['operational_admission'] and P['MOW-C08-C']['full_result_incremental_rub'] is None,'Конкретная C цепочка выходит за10h, T в данной точке нет; ни одна не имеет экономического admission.')

adis=rows('hypothesis_dispositions.csv');legacy=set(r['variant'] for r in rows('inputs/AUTHOR_network_routes.csv'))
check('all_14_author_geographies_and_C08_C19_C25_have_disposition',len(legacy)==14 and legacy<={r['hypothesis_id'] for r in adis} and {'C08','C19','C25'}<={r['hypothesis_id'] for r in adis},dict(author_geographies=len(legacy),dispositions=len(adis)))
A={r['assumption_id'] for r in load('assumptions.json')};missing=[]
for p in P.values():
 missing.extend(set(p['assumption_ids'])-A)
check('all_programme_assumption_ids_registered',not missing and len(A)==22,dict(assumptions=len(A),missing=missing))
check('no_undisclosed_actual_future_SJ_deliveries',all(p['future_sj_ready_date'] is None and p['donor_prior_task_id'] is None for p in P.values()) and load('delivery_branches.json')['branches'][-1]['new_SJ_count']==0,'Ready dates/count forecast UNKNOWN; H2 boundary не принят за коммерческий ввод.')

report=dict(status='PASS' if all(c['status']=='PASS' for c in CHECKS) else 'FAIL',scope='локальная проверка происхождения и календарной арифметики Stage A; не независимый внешний review, не market/dispatch/economics acceptance',checks=CHECKS,checks_passed=sum(c['status']=='PASS' for c in CHECKS),checks_total=len(CHECKS),economic_evaluation='NOT_RUN',operational_acceptance='UNKNOWN',source_coverage='PARTIAL',independent_acceptance='NOT_PERFORMED_BY_THIS_SELF_CHECK')
(R/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','checks_passed','checks_total','economic_evaluation','independent_acceptance']},ensure_ascii=False))
if report['status']!='PASS':
 print(json.dumps([c for c in CHECKS if c['status']=='FAIL'],ensure_ascii=False,indent=2));raise SystemExit(1)
