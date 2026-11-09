#!/usr/bin/env python3
"""Trace concrete travel mechanisms to evidence and model fields; no invented OD uplift."""
from __future__ import annotations
import csv,datetime as dt,hashlib,json,math,subprocess
from pathlib import Path
import build_aircraft_route_review as network
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'context/19_demand_mechanisms'
def read(path):
 with path.open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
def write(name,rows):
 rows=list(rows)
 with (OUT/name).open('w',encoding='utf-8',newline='')as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n');w.writeheader();w.writerows(rows)
def dump(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
 cases=json.load(open(OUT/'findings.json'));sources=json.load(open(OUT/'evidence/sources.json'));p=json.load(open(OUT/'assumptions.json'));byid={s['id']:s for s in sources};m=network.setup('ROUTE_INPUTS_UPPER_100')
 inventory=[];current=[];proposals=[]
 for c in cases:
  flat={k:'; '.join(v)if isinstance(v,list)and k!='model_pairs'else v for k,v in c.items()if k!='model_pairs'}
  flat.update(model_pairs=';'.join('-'.join(pair)for pair in c['model_pairs']),source_urls=';'.join(byid[s]['url']for s in c['sources']),new_paid_OD_target_week=None,OD_status='UNKNOWN_NOT_ZERO',automatic_OD_overwrite=False)
  inventory.append(flat)
  if c['model_pairs']:
   for a,b in c['model_pairs']:
    market=m.markets[network.core.pair(a,b)];q=m.scenarios['base']['capture_uncertain']*(1-math.exp(-1/m.scenarios['base']['frequency_scale']))
    current.append(dict(case=c['id'],model_pair=a+'-'+b,current_OD_base_week_direction=market['demand_base'],current_OD_cautious_week_direction=market['demand_cautious'],current_net_fare_base=market['fare_base'],current_one_weekly_capture_scenario=q,current_migration_base=market['cannibal_base'],own_RW_published_nominal_seats_direction=m.rw_cap(a,b),origin_gate='MOW is not ZIA; airport choice unobserved'if a=='ZIA'else'Case mechanism is not observed paid OD',status='CURRENT_MODEL_ASSUMPTIONS_NOT_NEW_FACTS'))
  proposals.append(dict(case=c['id'],shortlist=c['shortlist'],fields_to_revisit=c['model_fields'],accepted_non_OD_evidence=c['proved'],current_model_pairs=';'.join('-'.join(x)for x in c['model_pairs']),new_paid_OD_value=None,new_net_yield_value=None,readiness='NEEDS_DATED_SALES_OR_CONTRACT',facts_do_not_prove=c['not_proved'],next_data=c['next_data'],automatic_OD_or_city_rank_boost=False))
 write('case_inventory.csv',inventory);write('current_model_inputs.csv',current);write('model_change_proposals.csv',proposals)
 quantities=[]
 for c in cases[:2]:
  count=c['people_count'];legs=count*p['cohort_round_trips_scenario_per_person']*2
  quantities.append(dict(case=c['id'],calculation='participants x one roundtrip x2',input_fact=count,output=legs,unit='potential one-way PERSON movements for ONE historical cohort, not flights',status='CONDITIONAL_TRAVEL_ACCOUNT_NOT_OBSERVED_AIR_DEMAND',origin_split='UNKNOWN;43must not be allocated to each origin separately'if c['id']=='C01'else'Moscow study city not a ticket airport',target_week_paid_air_journeys=None,source_ids=';'.join(c['sources'])))
 oldbe=read(ROOT/'context/18_unit_economics_audit/breakeven.csv');g=next(r for r in oldbe if r['route']=='SVX-MRV'and r['scenario']=='base'and r['weekly_extra_burden']=='0')
 extra=math.ceil(float(g['required_paid_ceil_if_feasible'])-float(g['paid_now_per_departure']))
 opening=dt.date(2025,7,25);reference=dt.date(2025,12,7);target=dt.date(2026,12,7)
 for occupancy in p['hotel_room_occupancy_stress']:
  turnover=112*p['hotel_room_guests_scenario']*occupancy*7/p['hotel_mean_stay_days_scenario']
  quantities.append(dict(case='C03',calculation='112rooms x assumed2guests x occupancy x7/assumed14nights',input_fact=112,occupancy_scenario=occupancy,output=turnover,unit='illustrative hotel guest arrivals/week from ALL origins and modes',status='ROOM_TURNOVER_STRESS_NOT_DEMAND',extra_paid_SVX_MRV_journeys_direction_to_old_base_gate=extra,required_combined_origin_air_RW_net_new_date_fit_fraction=extra/turnover,hotel_open_before_both_reference_and_target_december=(opening<reference<target),target_week_paid_air_journeys=None,source_ids='S03;S04'))
 unique=p['shift_example_unique_people'];cycle=p['shift_example_on_days']+p['shift_example_off_days'];arrivals=unique*7/cycle
 quantities.append(dict(case='C07_FORMULA_ONLY',calculation='unique people across BOTH crews x7/(on_days+off_days)',input_fact=None,assumed_unique_people=unique,assumed_cycle_days=cycle,output=arrivals,unit='illustrative one-way arrivals/week/direction BEFORE airport/origin/mode share',status='PURE_SCENARIO_NOT_A_FOUND_WORKFORCE',target_week_paid_air_journeys=None,source_ids='NONE; assumptions.json'))
 quantities.append(dict(case='C07',calculation='historical upper group mention vs nominal100',input_fact=None,secondary_historical_max_mention=118,nominal_aircraft_seats=100,output=None,unit='maximum mention is not actual group size; if118travel together, one100seatflight cannot carry all',status='STALE_SECONDARY_NOT_IMPORTED',target_week_paid_air_journeys=None,source_ids='S15'))
 quantities.append(dict(case='C05',calculation='operator-reported car-time reduction lower bound',input_fact=6,output=6,unit='hours REDUCED, strictly>6; not actual new city-to-city travel time or passenger count',status='PRIMARY_OPERATOR_CLAIM_NOT_MODAL_SHARE',target_week_paid_air_journeys=None,source_ids='S11;S12'))
 write('quantity_scenarios.csv',quantities)
 rejected=[('C01','43forMoscow +43forPetersburg','43is the TOTAL cohort; split unknown'),('C01;C02','summer participants become December weekly OD','Dates do not match; repetition and transport mode unknown'),('C01;C02','study cityMoscow becomes ZIA tickets','Actual origin airport and residence unknown'),('C03','112rooms become112air passengers per flight','Need stays, guest origins, net regional addition, mode, dates and paid airline choice'),('C03','opened2025 means new capacity inDecember2026 vsDecember2025','Opening precedes BOTH December periods; do not double count existing capacity'),('C03','sanatorium growth32percent becomes route growth32percent','Different seller sample, geography, period and unit'),('C04','Tobolsk industrial travellers all assigned toTJM','RemezovRMZ is a separate airport; origins and access choices unknown'),('C04','570kt polypropylene becomes workers or trips','Production volume not people movements'),('C04','plant launch2027 guarantees growing contractor flights','Commissioning and operational phases differ; temporary workforce can shrink'),('C05','road-time gain implies a fixed percent decline in air demand','Modal response and full generalized costs not measured'),('C06','Izhavia exit leaves the entire route vacant','RW announced takeover; transferred bookings belong in own baseline'),('C07','2017lot and118maximum mean current guaranteed group','Primary current contract and actual group calendar not obtained'),('C08','354announced rooms become current booked guests','Primary operating/booking evidence insufficient'),('C09','320trainees mean320air trips throughKazan','Some online/local; centres and airports unknown; Nizhnekamsk is notKazan')]
 write('rejected_inferences.csv',[dict(case=c,wrong_inference=w,reason=r)for c,w,r in rejected])
 tests={
  'all_nine_cases_have_who_origin_destination_dates_and_limits':all(all(c.get(k)for k in ['who','origin','destination','when','why','proved','not_proved','next_data'])for c in cases),
  'all_case_sources_exist':all(s in byid for c in cases for s in c['sources']),
  'six_shortlist_cases_cover_real_people_facility_project_transport_and_exit':sum(c['shortlist']for c in cases)==6,
  'cohort43not_doubled_across_two_origins':quantities[0]['output']==86,
  'cohort15roundtrip_scenario_not_annual_or_weekly':quantities[1]['output']==30,
  'hotel_opening_precedes_both_december_comparators':opening<reference<target,
  'shift_pool_counts_both_crews_once':arrivals==56,
  'no_unknown_paid_OD_replaced_with_zero_or_a_scenario':all(r['new_paid_OD_target_week']is None and not r['automatic_OD_overwrite']for r in inventory),
  'no_city_rank_or_market_uplift_automatically_imported':all(not r['automatic_OD_or_city_rank_boost']for r in proposals),
  'stale_procurement_announcement_and_training_aggregate_not_shortlisted':all(not next(c for c in cases if c['id']==k)['shortlist']for k in ['C07','C08','C09']),
 }
 changed=[]
 for path,h in json.load(open(OUT/'baseline.json'))['tracked_files'].items():
  if subprocess.check_output(['git','hash-object',str(ROOT/path)],text=True).strip()!=h:changed.append(path)
 assert set(changed)<={'README.md'},changed
 tests['all_previous_numeric_results_and_foreign_files_preserved']=True;assert all(tests.values())
 dump('validation.json',dict(status='PASS',tests=tests,case_count=len(cases),shortlist_count=6,new_observed_paid_OD_rows=0,unknown_is_not_zero=True,prior_document_updates=changed))
 import write_demand_mechanisms
 write_demand_mechanisms.main()
 inputs=[Path(__file__),ROOT/'scripts/write_demand_mechanisms.py',OUT/'findings.json',OUT/'assumptions.json',OUT/'evidence/sources.json',OUT/'evidence/team_review.json',ROOT/'context/18_unit_economics_audit/breakeven.csv',ROOT/'context/17_aircraft_route_review/model/input_manifest.json',*[ROOT/k for k in json.load(open(ROOT/'context/17_aircraft_route_review/model/input_manifest.json'))['sha256']]]
 dump('input_manifest.json',{'sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted(set(inputs))}})
 print(json.dumps({'status':'PASS','cases':len(cases),'shortlist':6,'tests':len(tests),'one_cohort_movement_scenarios':[86,30],'hotel_turnover_stress_not_OD':[r['output']for r in quantities if r['case']=='C03'],'numeric_OD_updates':0},ensure_ascii=False))
if __name__=='__main__':main()
