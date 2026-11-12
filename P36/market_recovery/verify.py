from pathlib import Path
import csv,json,datetime as dt,hashlib
O=Path(__file__).resolve().parent;R=O.parents[1];C=R/'context/36_overnight_chain_search_20261112'
def read(n):
 with (O/n).open() as f:
  reader=csv.DictReader(f);out=list(reader)
  assert out and all(None not in r and None not in r.values() for r in out),n
  return out
checks={};errors=[]
def check(name,condition):
 checks[name]=bool(condition)
 if not condition:errors.append(name)
p=read('canonical_market_pairs.csv');s=read('canonical_services.csv');u=read('unknown_fields.csv');a=read('source_admission.csv');src=read('sources.csv');w=read('WZ901_resolution.csv');ids={r['source_id'] for r in src}
check('schema_11_unique_pairs',len(p)==11 and len({r['pair'] for r in p})==11)
check('schema_source_ids_unique',len(ids)==len(src))
for name,rs in [('pairs',p),('services',s),('unknown',u),('admission',a),('WZ901',w)]:
 check('refs_'+name,all(x in ids for r in rs for k,v in r.items() if k.endswith('source_id') for x in v.split(';') if x))
check('source_excerpts_exist',all(not r['excerpt_file'] or (O/r['excerpt_file']).is_file() for r in src))
check('unknown_separate',all(r['status']!='UNKNOWN' and r['covered_dates'] not in ['', 'UNKNOWN'] for r in s) and all(r['value']=='UNKNOWN' and r['field_status']=='no_update' for r in u))
check('no_absence_or_zero_replacement',all(r['rw_nonstop_nov']==r['rw_nonstop_feb']=='UNKNOWN' and r['directed_daily_od']==r['net_fare']=='UNKNOWN' and r['calibration_update']=='no_update' for r in p))
check('physical_airports_not_city',all(r['origin']!='MOW' and r['destination']!='MOW' for r in s))
by={r['pair']:r for r in p}
check('MOW_shared_OD_separate_airports',by['DME-KGD']['city_pool_id']==by['ZIA-KGD']['city_pool_id']=='MOW-KGD' and by['DME-KGD']['physical_origin']!=by['ZIA-KGD']['physical_origin'])
check('no_foreign_MOW_row_source',all('WZ-' not in r['competitor_source_id']+r['rw_nonstop_source_id']+r['historical_source_id'] for r in p if r['pair'] not in ['DME-KGD','ZIA-KGD']))
period_ok=True
for r in s:
 for t in r['covered_dates'].split(';'):
  d=dt.date.fromisoformat(t)
  period_ok &= r['valid_start']<=t<=r['valid_end'] and d.weekday() in [int(v) for v in r['days_mon0'].split(',')]
  if r['week']!='historical':period_ok &= r['week_start']<=t<=r['week_end']
check('periods_weekdays_no_autoextension',period_ok)
# Exact preservation of old positive rows, including VVO and date-limited KHV context.
old=list(csv.DictReader((R/'context/34_new_direct_top5_20261112/source_recovery_competitors/schedules.csv').open()))
positive=[r for r in old if r['status']=='PUBLISHED_PATTERN_ONLY'];sm={r['service_id']:r for r in s}
check('all_P34_positive_retained',all('P34-'+r['schedule_id'] in sm for r in positive))
check('P34_source_period_clocks_preserved',all(all(sm['P34-'+r['schedule_id']][new]==r[oldkey] for new,oldkey in [('covered_dates','applicable_departures'),('valid_start','valid_start'),('valid_end','valid_end'),('departure_local','dep_local'),('arrival_local','arr_local'),('flight','flight'),('carrier_operated','carrier')]) for r in positive))
kja=[r for r in s if r['pair']=='SVX-KJA' and r['origin']=='SVX']
check('KJA_feb_only_admitted_Tue_Sat',set(int(d) for r in kja if r['week']=='target' for d in r['days_mon0'].split(','))=={1,5})
check('KJA_nov_all_days_observed',set(int(d) for r in kja if r['week']=='ordinary' for d in r['days_mon0'].split(','))==set(range(7)))
check('Yamal_quarantined_not_zero',any(r['decision']=='QUARANTINE_CONTRADICTION' for r in a) and not any('YC-' in r['flight'] for r in s))
check('WZ901_historical_ZIA_only',all(r['origin']=='ZIA' and r['covered_dates']=='2026-09-24' and r['week']=='historical' for r in s if r['flight']=='WZ901'))
check('current_Moscow_gate_unresolved',any(r['field']=='final_gate' and r['field_status']=='GATE_NOT_RESOLVED' for r in w))
requests=json.loads((O/'actual_requests.json').read_text())['requests'];counts={k:sum(len(r['arguments'].get(k,[])) for r in requests) for k in ['search_query','open','find']}
check('external_request_limits',counts['search_query']<=6 and 8<=counts['open']<=10)
check('exact_requests_and_responses_saved',all(r['tool']=='tools.web__run' and r['response'] for r in requests))
protected=json.loads((C/'protected_files.json').read_text());changed=[p for p,h in protected.items() if not (R/p).is_file() or hashlib.sha256((R/p).read_bytes()).hexdigest()!=h]
check('protected_1418_unchanged',len(protected)==1418 and not changed)
result=dict(status='PASS' if not errors else 'FAIL',checks=checks,errors=errors,counts=dict(pairs=len(p),positive_service_patterns=len(s),preserved_P34_patterns=len(positive),unknown_field_rows=len(u),sources=len(src),**counts),protected_files_checked=len(protected),protected_changed=changed,meaning='Schema/refs/period/airport/preservation checks; not independent verification of source truth',research_stop=True,current_Moscow_gate='NOT_RESOLVED',class_A_B='UNPROVED_CONDITIONAL',qualified_new_routes='NOT_ESTABLISHED')
(O/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
