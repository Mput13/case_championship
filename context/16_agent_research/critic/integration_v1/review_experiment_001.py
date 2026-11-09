#!/usr/bin/env python3
"""Independent replay of exported phase2 identities, never peer model execution."""
from collections import Counter,defaultdict
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parent
SHA='1a6844511d9f18b11473d02b2f0cb5963f9f173b'
RUN='c26661067277af20'
PREFIX='context/16_agent_research/hypotheses/experiment_v1/'
RECEIPTS=[]

def capture(name):
    data=subprocess.check_output(['git','show',SHA+':'+PREFIX+name])
    path=BASE/'raw/experiment-001'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    RECEIPTS.append(dict(input_git_sha=SHA,repo_path=PREFIX+name,local_path=path.relative_to(BASE).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    return data
def table(data):return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
def stamp(text):return dt.datetime.fromisoformat(text)
def minutes(a,b):return int((a-b).total_seconds()/60)
def as_int(row,field):return int(row[field])

def main():
    failures=[]
    def verify(condition,file,row,kind):
        if not condition:failures.append(dict(file=file,row=row,kind=kind))
    contract_data=capture('contract.json');manifest_data=capture('input_manifest.json');programs_data=capture('scenario_programs.json')
    assert contract_data==(BASE/'frozen_contract.json').read_bytes()
    assert manifest_data==(BASE/'frozen_input_manifest.json').read_bytes()
    contract=json.loads(contract_data);programs=json.loads(programs_data);outmanifest=json.loads(capture('runs/'+RUN+'/output_manifest.json'))
    for path,h in outmanifest['input_hashes'].items():assert hashlib.sha256(capture(path)).hexdigest()==h,path
    assert hashlib.sha256(json.dumps(outmanifest['input_hashes'],sort_keys=True).encode()).hexdigest()[:16]==RUN
    data={}
    for entry in outmanifest['files']:
        b=capture('runs/'+RUN+'/'+entry['path']);assert hashlib.sha256(b).hexdigest()==entry['sha256'];assert len(b)==entry['bytes']
        data[entry['path']]=table(b) if entry['path'].endswith('.csv') else json.loads(b)
    legs=data['physical_legs.csv'];by_id={r['leg_id']:r for r in legs};verify(len(by_id)==len(legs),'physical_legs.csv','all','unique_leg_ids')
    zones={r['iata']:r['iana']for r in data['airport_keys.csv']}
    groups=defaultdict(list)
    for n,r in enumerate(legs,2):
        a,b=stamp(r['departure_utc']),stamp(r['arrival_utc']);verify(b>a and minutes(b,a)==int(r['block_minutes']),'physical_legs.csv',n,'positive_block')
        verify(a.astimezone(ZoneInfo(zones[r['origin']])).isoformat()==r['departure_local'] and b.astimezone(ZoneInfo(zones[r['destination']])).isoformat()==r['arrival_local'],'physical_legs.csv',n,'local_UTC_conversion')
        group_day=re.search(r'_(\d{4}-\d{2}-\d{2})_\d+$',r['leg_id']).group(1);groups[r['variant'],group_day,r['tail']].append(r)
    for day in programs['operating_dates']:
        fingerprints=[]
        for mode in ['sync','unsync']:
            seq=[r for r in legs if r['variant']=='C01_'+mode and day in r['leg_id']]
            fingerprints.append(Counter((r['tail'],r['origin'],r['destination'],r['block_minutes'],r['nominal_seats'])for r in seq))
        verify(fingerprints[0]==fingerprints[1],'physical_legs.csv',day,'C01_same_physical_legs_durations_tails_seats')
    conn=data['c01_connections.csv'];by_conn={r['itinerary_id']:r for r in conn}
    for n,r in enumerate(conn,2):
        path=[by_id[k] for k in r['leg_ids'].split(';')];wait=minutes(stamp(path[1]['departure_utc']),stamp(path[0]['arrival_utc']))
        gate='BELOW_SCENARIO_MIN_CONNECTION' if wait<int(r['min_connection_minutes']) else 'ABOVE_SCENARIO_MAX_CONNECTION'if wait>int(r['max_connection_minutes'])else'PASS_SCENARIO_CLOCK'
        verify(path[0]['destination']==path[1]['origin'] and wait==int(r['actual_wait_minutes']) and gate==r['calendar_gate'],'c01_connections.csv',n,'path_wait_gate')
        verify(r['departure_local']==path[0]['departure_local'] and r['arrival_local']==path[-1]['arrival_local'],'c01_connections.csv',n,'endpoint_timestamps')
        verify((int(r['one_way_journeys']),int(r['leg_seats_consumed']),int(r['fare_applications']))==(1,len(path),1),'c01_connections.csv',n,'one_fare_each_path_leg_once')
    cohorts=data['c01_dated_cohorts.csv']
    for n,r in enumerate(cohorts,2):
        outbound=by_conn[r['outbound_id']];stay=dt.date.fromisoformat(r['booked_stay_start_local']);checkout=stay+dt.timedelta(days=int(r['hotel_nights']));inbound=by_conn.get(r['return_id'])
        gate='PASS_SCENARIO_CALENDAR'if inbound and outbound['calendar_gate']==inbound['calendar_gate']=='PASS_SCENARIO_CLOCK'else'NO_EXACT_PRODUCT_IN_SCENARIO'
        if checkout>dt.date.fromisoformat(contract['period']['product_return_horizon']):gate='UNKNOWN_HORIZON_COVERAGE'
        verify(checkout.isoformat()==r['checkout_local'] and gate==r['calendar_gate'],'c01_dated_cohorts.csv',n,'stay_length_return_calendar')
        verify((r['one_way_journeys'],r['leg_seats_consumed'],r['roundtrip_customers'])==('2','4','1'),'c01_dated_cohorts.csv',n,'roundtrip_units')
        if inbound:verify(inbound['arrival_local'][:10]==r['return_home_arrival_date'],'c01_dated_cohorts.csv',n,'return_home_date')
    resources=data['resource_checks.csv']
    for n,r in enumerate(resources,2):
        seq=sorted(groups[r['variant'],r['date'],r['tail']],key=lambda x:x['departure_utc']);waits=[minutes(stamp(b['departure_utc']),stamp(a['arrival_utc']))for a,b in zip(seq,seq[1:])]
        block=sum(int(x['block_minutes'])for x in seq);elapsed=minutes(stamp(seq[-1]['arrival_utc']),stamp(seq[0]['departure_utc']))
        chain_ok=all(a['destination']==b['origin'] for a,b in zip(seq,seq[1:])) and seq[0]['origin']==r['initial_airport']==seq[-1]['destination']==r['final_airport']
        gate='PASS_SCENARIO_CLOCK'if chain_ok and all(w>=int(r['turn_min_scenario'])for w in waits)and elapsed<=int(r['window_minutes_scenario'])else'FAIL_SCENARIO_CLOCK'
        verify((len(seq),block,sum(waits),elapsed)==tuple(int(r[k])for k in ['physical_leg_count','block_minutes','ground_minutes','elapsed_minutes']) and gate==r['clock_gate'],'resource_checks.csv',n,'resource_sums_closure_turn_window')
    oracle={(r['fare_per_oneway_journey_rub'],r['variable_per_journey_rub'],r['constant_residual_gap_per_period_rub']):r for r in table((BASE/'threshold_oracle.csv').read_bytes())}
    money=data['conditional_thresholds.csv'];moneykeys=[]
    for n,r in enumerate(money,2):
        key=(r['net_fare_rub_per_oneway_journey'],r['variable_cost_rub_per_oneway_journey'],r['residual_funding_gap_rub']);q=int(oracle[key]['required_sales_each_direction']);fare=int(key[0]);margin=fare-int(key[1]);gap=int(key[2]);moneykeys.append((r['candidate'],*key))
        expected=[q,2*q,q,2*q*fare,2*q*margin-gap];fields=['required_paid_journeys_each_direction','total_oneway_journeys','roundtrip_customers','required_ticket_revenue_rub','contribution_at_threshold_rub']
        verify(expected==[int(r[k])for k in fields],'conditional_thresholds.csv',n,'independent_fraction_inverse_units_revenue')
        if q:verify(int(r['contribution_one_customer_below_rub'])==2*(q-1)*margin-gap<0,'conditional_thresholds.csv',n,'minimal_threshold')
        verify(all(r[k]=='UNKNOWN' for k in ['actual_residual_seats','actual_funding_gap','actual_net_fare','market_demand']),'conditional_thresholds.csv',n,'unknowns_preserved')
    verify(len(set(moneykeys))==108,'conditional_thresholds.csv','all','complete_3_by36_unique_grid')
    for n,r in enumerate(data['capacity_allocation_fixtures.csv'],2):
        local=int(r['locals_each_leg']);transfer=int(r['transfer_journeys']);load=local+transfer;cap=int(r['nominal_seats_each_leg'])
        verify(load==int(r['first_leg_load'])==int(r['second_leg_load']) and int(r['ticket_revenue_once_per_journey'])==2*local*5000+transfer*8000 and r['capacity_gate']==('PASS'if load<=cap else'FAIL'),'capacity_allocation_fixtures.csv',n,'shared_seats_revenue_once')
    real=data['c14_real_calendar_requests.csv'];conditional=data['c14_conditional_stay_dates.csv']
    verify(len(real)==21 and all(r['calendar_gate']=='UNKNOWN' and r['booked_checkin_local']==r['checkout_local']==r['outbound_service_id']==r['return_service_id']==''for r in real),'c14_real_calendar_requests.csv','all','no_false_December_product_or_zero_market')
    for n,r in enumerate(conditional,2):
        dep=dt.date.fromisoformat(r['requested_origin_departure_date']);checkin=dt.date.fromisoformat(r['assumed_booked_checkin_local']);checkout=checkin+dt.timedelta(days=int(r['hotel_nights']));inside=checkout<=dt.date.fromisoformat(contract['period']['product_return_horizon']);days=programs['C14']['scenario_weekdays_iso'];good_weekday=dep.isoweekday()in days and checkout.isoweekday()in days
        expected='UNKNOWN_HORIZON_COVERAGE'if not inside else'PASS_WEEKDAY_ONLY_SCENARIO'if good_weekday else'NO_EXACT_WEEKDAY_PRODUCT_IN_SCENARIO'
        verify(checkout.isoformat()==r['checkout_local'] and expected==r['calendar_gate'] and inside==(r['within_return_horizon']=='True'),'c14_conditional_stay_dates.csv',n,'hypothetical_stay_horizon_weekday')
    for n,r in enumerate(data['c07_comparison.csv'],2):
        seq=sorted([x for x in legs if x['variant']==r['variant']],key=lambda x:x['departure_utc']);elapsed=minutes(stamp(seq[-1]['arrival_utc']),stamp(seq[0]['departure_utc']));oracle_rows=table((BASE/'C07_resource_oracle.csv').read_bytes());turn=int(r['variant'].split('turn')[1]);expected=next(x for x in oracle_rows if int(x['turn_scenario_minutes'])==turn)
        verify(elapsed==int(expected['chain_elapsed_minutes'])==int(r['elapsed_candidate_minutes']) and int(r['elapsed_baseline_minutes'])==255 and int(r['return_delay_vs_reference_minutes'])==elapsed-255 and len(seq)==4,'c07_comparison.csv',n,'independent_clock_proxy_chain_and_return_delay')
    output=BASE/'reviews'/RUN;output.mkdir(parents=True,exist_ok=True)
    report=dict(checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),input_git_sha=SHA,run_id=RUN,method='Own CSV/graph/datetime/Fraction accounting; peer scripts read but never executed',output_files_hash_checked=len(outmanifest['files']),physical_leg_rows=len(legs),resource_rows=len(resources),C01_same_leg_date_pairs=len(programs['operating_dates']),connection_rows=len(conn),connection_gate_counts=dict(Counter(r['calendar_gate']for r in conn)),cohort_rows=len(cohorts),cohort_gate_counts=dict(Counter(r['calendar_gate']for r in cohorts)),money_rows=len(money),capacity_boundary_examples=len(data['capacity_allocation_fixtures.csv']),C14_real_requests=len(real),C14_separate_calendar_stresses=len(conditional),C14_stress_gate_counts=dict(Counter(r['calendar_gate']for r in conditional)),differences=failures,arithmetic_status='PASS_SCOPED'if not failures else'FAIL',temporal_status='SCENARIO_ONLY; real datedservice/slots/hoteladmission not established',conditional_comparison='Thresholds and resource screens only; costs/local-sales/baseline/donor remain UNKNOWN',market_status='NOT_ACCEPTED_NO_TARGET_LABELS',full_case_network='NOT_EVALUATED',product_grain_note='C07 money q interpreted as local single-leg OMS-KJA paired product as candidate describes; explicit OD/path field requested, not an assertion that through passenger uses only2boardings')
    (output/'reproduction.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (output/'input_manifest.json').write_text(json.dumps(dict(input_git_sha=SHA,run_id=RUN,files=RECEIPTS),indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False));assert not failures

if __name__=='__main__':main()
