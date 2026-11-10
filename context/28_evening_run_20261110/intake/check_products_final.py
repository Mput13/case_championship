#!/usr/bin/env python3
"""Final products receipt, cash aggregation and preservation checks."""
import csv, datetime as dt, hashlib, io, json, math, subprocess
from collections import defaultdict
from pathlib import Path
SHA='388908b6da3539484cb8e2e03ada6ff5cb2204a4';OLD='a39165528ceaa80f026210d0aaae9e2b541e6f51'
ROOT='context/28_evening_run_20261110/products/'
def blob(s,p):return subprocess.check_output(['git','show',s+':'+p])
def data(p):return blob(SHA,ROOT+p)
def rows(p):return list(csv.DictReader(io.StringIO(data(p).decode())))
def near(x,y):assert math.isclose(float(x),float(y),rel_tol=1e-9,abs_tol=1e-5),(x,y)
delivery=json.loads(data('delivery_manifest.json'))['files'];inputs=json.loads(data('input_manifest.json'))['files'];sources=0
for r in delivery+inputs:
 b=data(r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
for r in inputs:
 if r.get('commit'):
  assert data(r['path'])==blob(r['commit'],r['source_path']);sources+=1
preserved=['C10_contract_thresholds','C14_full_package_thresholds','C17_seasonal_thresholds','C31_replacement_frontier','C35_partner_thresholds']
for name in preserved:assert data('outputs/'+name+'.csv')==blob(OLD,ROOT+'outputs/'+name+'.csv')
events=rows('outputs/cash_events.csv');summary=rows('outputs/cash_summary.csv');balances=defaultdict(lambda:defaultdict(float))
for r in events: balances[(r['hypothesis'],r['scenario'],r['entity'])][r['date']]+=float(r['amount_rub'])
checked=0
for r in summary:
 if not r['cash_balance_end']:continue
 series=balances[(r['hypothesis'],r['scenario'],r['entity'])];balance=minimum=0
 for date in sorted(series):
  balance+=series[date];minimum=min(minimum,balance)
 near(balance,r['cash_balance_end']);near(max(0,-minimum),r['minimum_external_funding_if_same_day_netting']);checked+=1
 assert 'UNKNOWN' in r['unknown_cash']
flights=rows('outputs/dated_flights.csv')
for r in flights:
 dep=dt.datetime.fromisoformat(r['departure_utc']);arr=dt.datetime.fromisoformat(r['arrival_utc'])
 near((arr-dep).total_seconds()/3600,r['block_hours'])
 assert dep==dt.datetime.fromisoformat(r['departure_local']) and arr==dt.datetime.fromisoformat(r['arrival_local'])
internal=rows('outputs/addendum_C35_internal_KEEP.csv')
for r in internal:
 near(float(r['through_oneway_journeys'])*2,r['rw_used_seat_segments'])
 near(float(r['customer_total_fare_revenue'])-float(r['incremental_two_leg_pax_handling_protection_cost'])-float(r['lost_previous_own_contribution_probe']),r['maximum_integration_retime_risk_K'])
 near(float(r['maximum_integration_retime_risk_K'])-float(r['K_probe']),r['full_incremental_at_probe_and_K'])
 assert float(r['external_partner_payment'])==0 and float(r['additional_subsidy_from_new_flights'])==0
result={'subject_sha':SHA,'status':'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING','checks':{'delivery_hashes':len(delivery),'input_hashes':len(inputs),'exact_git_sources':sources,'old_money_tables_byte_identical':5,'cash_events':len(events),'cash_summary_cases_reaggregated':checked,'dated_flight_times':len(flights),'internal_KEEP_rows':len(internal)},'qualifications':['Same-day netting is a lower financing boundary under explicit assumed payment dates','Corporate/hotel/partner payment terms are hypothetical, not contracts','Airline and tour operator cash are separate entities; economic opportunity cost not duplicate cash payment','C35 both-own-legs KEEP is conditional on existing flights/inventory and receives no extra-flight subsidy','All five original economic threshold grids preserved; addendum is separate'],'not_run':['independent full review','actual cash/PNR/payment default','full flight resource validation','readiness sensitivity reconstruction','primary source interpretation replay']}
Path(__file__).with_name('products_final_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
