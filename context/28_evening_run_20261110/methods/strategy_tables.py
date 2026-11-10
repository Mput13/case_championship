"""Final decision tables from immutable inputs; one bounded shared-market union, no new search."""
import csv,json,math
from collections import defaultdict
from model_kernel import ROOT
OUT=ROOT/'strategy';OUT.mkdir(exist_ok=True)
def read(p):return list(csv.DictReader((ROOT/p).open()))
def dump(n,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
net=json.loads((ROOT/'runs/selection_v1/networks.json').read_text());plans=json.loads((ROOT/'runs/resource_v1/plans.json').read_text())
names={r['iata']:r.get('main_city') or r.get('city') or r.get('name') or r['iata'] for r in read('inputs/nastya_4a976/data/processed/catchments.csv')}
names['MOW']='Москва (агрегат, аэропорт не выбран)'
options=[];routes=[]
for f in read('runs/selection_v1/preserved_frontiers.csv'):
 if f['cap']!='10' or not f['calendar'].startswith('AUTHOR'):continue
 if f['network']=='DIRECT' and f['policy']!='SIGNED_CITY_PAIRS_PRESERVE':continue
 key=f['selected_id'];n=net[key];m=n['metrics'];p=plans[key]
 options.append(dict(option=key,scenario=m['scenario'],family=m['network'],model_endpoint_pairs=m['model_city_pairs'],eight_twelve_gate=m['model_8_12_pair_gate'],constructed_working_tails=p['working_tails'],reserve=1,total_planning_tails=p['working_tails']+1,block_hours_week=m['block_hours_week'],flights_week=m['flights_week'],annual_contribution_source=m['contribution_rub_year'],support_status='HISTORICAL_OWNER_SHADOW' if m['scenario'].endswith('_sub') else 'NONE',annual_journeys_source=m['journeys_year'],annual_segments_source=m['segments_year'],actual_resource_market_fullPnL='UNKNOWN',source_calendar=m['calendar'],physical_airports=m['physical_airport_assignment'],selection='BEST_FOUND_PRESERVED_NOT_GLOBAL_OPTIMUM'))
 if m['kind']=='HUB':
  for x,l in n['result'][0].items():routes.append(dict(option=key,program=m['network'],origin=m['network'],destination=x,origin_name=names[m['network']],destination_name=names[x],frequency_each_direction_week=l['freq'],physical_airport_resolved=x!='MOW',route_unit='UNORDERED_ENDPOINT_PAIR'))
 else:
  for t in n['result']:
   for l in t[8]:routes.append(dict(option=key,program='-'.join(t[1:4]),origin=l['a'],destination=l['b'],origin_name=names[l['a']],destination_name=names[l['b']],frequency_each_direction_week=l['freq'],physical_airport_resolved='MOW' not in (l['a'],l['b']),route_unit='PROGRAM_LEG; aggregate duplicate endpoint pairs before counting'))
for r in options:r.update(source_model_sha='4a9763565f70b9ab1eddde2f5daca07687560948',projection_status='OWNER_SYNTHESIS; selection source independently scoped')
for r in routes:r.update(scenario=r['option'].split('/')[1],network=r['option'].split('/')[2],route='-'.join(sorted((r['origin'],r['destination']))),date=None,calendar_basis='AUTHOR_FIXED_WEEKLY_52_OR48; NOT_DATED_FLIGHT',source_model_sha='4a9763565f70b9ab1eddde2f5daca07687560948')
dump('finite_options.csv',options);dump('option_routes.csv',routes)
cal=read('runs/annual_v1/aircraft_calendar_daily.csv');readiness=[]
for opt in options:
 if opt['scenario'] not in ('base','base_sub'):continue
 for branch in sorted({r['branch'] for r in cal}):
  for year in ('2027','2028'):
   dates=[r['date'] for r in cal if r['branch']==branch and r['availability']=='14D_GROUNDING_STRESS' and r['date'].startswith(year) and int(r['working_new'])>=opt['constructed_working_tails']]
   readiness.append(dict(option=opt['option'],branch=branch,year=year,required_working_tails=opt['constructed_working_tails'],days_with_aggregate_resource=len(dates),first_date_with_resource=min(dates) if dates else None,last_date_with_resource=max(dates) if dates else None,gate='AGGREGATE_N_ONLY; weekly choice can defer; registered tail/base/crew/bank not accepted'))
dump('finite_option_readiness.csv',readiness)
# C03 KUF4 + C04 OMS8:11 distinct pairs, two programmes share KUF-OMS.
rr=read('inputs/network_b471/v2/outputs/fixed_routes.csv');dd=read('inputs/network_b471/v2/outputs/demand_fare_inputs.csv');mixed=[];mixroutes=[]
for s in ('base','cautious'):
 A=net[f'AUTHOR_52_48_CONCENTRATED/{s}/OMS/GREEDY/cap4']['assumptions']
 selected=[r for r in rr if r['scenario']==s and r['network'] in ('KUF4','OMS8')];pairs=defaultdict(list)
 for r in selected:pairs[tuple(sorted((r['origin'],r['destination'])))].append(r)
 assert len(pairs)==11 and len(selected)==12
 naive=sum(float(r['local_only_contribution_rub_week']) for r in selected);total=naive;qdelta=0
 for pair,rs in pairs.items():
  f=sum(float(r['frequency_each_direction']) for r in rs);oldq=sum(float(r['local_journeys_week']) for r in rs);newq=oldq
  d=next(r for r in dd if r['scenario']==s and {r['origin'],r['destination']}==set(pair) and r['frequency_each_direction']=='2')
  if len(rs)>1:
   dem=float(d['diagnostic_week_od_one_direction']);seg=float(d['annual_segments_competition_proxy'])/104
   capture=min(A['capture_competitive'],f/(f+seg/(A['seats']*A['competitor_lf']))) if d['direct_in_author_input']=='True' else A['capture_open']*(1-math.exp(-f/A['capture_freq_scale']))
   newq=2*min(dem*capture,f*A['seats']*A['lf_max']);assert newq<=2*dem+1e-8
  delta=(newq-oldq)*(float(d['net_fare_rub'])-A['pax_cost_rub']);total+=delta;qdelta+=newq-oldq
  mixroutes.append(dict(scenario=s,origin=pair[0],destination=pair[1],programmes=';'.join(r['network'] for r in rs),joint_frequency_each_direction=f,naive_independent_local_journeys=oldq,pooled_local_journeys=newq,contribution_correction=delta,flights_preserved=sum(int(r['flights_week']) for r in rs)))
 mixed.append(dict(option='KUF4_PLUS_OMS8_LOCAL_ONLY',scenario=s,diagnostic_period='2026-12-07/2026-12-13; annual OD/104 per direction',distinct_endpoint_pairs=11,route_program_rows=12,flights_week=sum(int(r['flights_week']) for r in selected),block_hours_week=sum(float(r['block_hours_week']) for r in selected),working_slots_by_separate_base_constructions=3,reserve_actual='UNKNOWN_TWO_BASE_COVERAGE',naive_sum_contribution=naive,shared_market_corrected_contribution=total,shared_market_sales_correction=qdelta,extra_other_network_credit_needed_before_K=-total,transfer_revenue='NOT_INCLUDED; source ideal bank not accepted as dated sales',support=0,actual_fleet_fullPnL='UNKNOWN',comparison='Specific mixed11 recipe fails local-only no-support conditions; not global mixed optimum'))
dump('mixed11_routes.csv',mixroutes);dump('mixed11_budget.csv',mixed)
# Historical scale bridge explicitly separated from future whole-company forecast.
scale=[]
for r in read('runs/integer_year_v1/annual_comparison.csv'):
 if r['branch']!='PHASED' or r['year']!='2028' or r['scenario'] not in ('base','base_sub'):continue
 new=float(r['net_added_segments_listed_keep_only']);scale.append(dict(case=r['case'],dated_new_segments_less_listed_migration=new,historical_RW_2025_segments=2700000,historical_second_carrier_2025_segments=13800000,illustration_keep2025_unchanged_plus_project=2700000+new,remaining_to_historical_second_if_no_other_change=13800000-2700000-new,future_KEEP2028='UNKNOWN',future_total_market2028='UNKNOWN',future_rank_share='NOT_ESTIMATED',formula='S_RW2028=KEEP_RW2028+new_segments-listed_migration-other_lost_segments; no journeys/segments mixing'))
dump('whole_company_bridge.csv',scale)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS_OWNER_SYNTHESIS',finite_options=len(options),option_route_rows=len(routes),readiness_rows=len(readiness),mixed11_cases=len(mixed),mixed_route_rows=len(mixroutes),whole_company_rows=len(scale),review_scope='New synthesis/mixed counterexample not inherited from EV-MR03'),indent=2)+'\n')
print(json.dumps(mixed,ensure_ascii=False,indent=2))
