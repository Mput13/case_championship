#!/usr/bin/env python3
"""Owner checks using a minute-grid oracle and separate accounting assertions.

This is deliberately NOT an independent review or source/market acceptance.
"""
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import Counter, defaultdict
import csv, json, hashlib, subprocess, copy

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
def read(p):return list(csv.DictReader((ROOT/p).open()))
def js(p):return json.loads((ROOT/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def dt(x):return datetime.fromisoformat(x)
def md(a,b):return (a-b).total_seconds()/60
CHECKS=[]
def check(name,condition,detail):
    CHECKS.append(dict(check_id=name,status='PASS' if condition else 'FAIL',detail=detail,scope='SELF_CHECK_ONLY'))
    assert condition,(name,detail)

def fixture_audit(sales,loads):
    by_leg={r['leg_id']:r for r in loads}
    if len(by_leg)!=len(loads):return False
    allocated=Counter()
    for s in sales:
        ids=s['leg_ids'].split(';')
        if len(ids)!=len(set(ids)) or not ids or any(i not in by_leg for i in ids):return False
        if int(s['endpoint_journeys'])!=int(s['quantity']):return False
        if int(s['physical_boardings'])!=len(ids)*int(s['quantity']):return False
        if int(s['ticket_revenue'])!=int(s['quantity'])*int(s['net_fare_per_journey']):return False
        for ident in ids:allocated[ident]+=int(s['quantity'])
    for ident,r in by_leg.items():
        if allocated[ident]!=int(r['new_journeys']):return False
        if int(r['total_load'])!=int(r['local_seats'])+allocated[ident]:return False
        if (int(r['total_load'])<=int(r['nominal_seats']))!=(r['gate']=='PASS'):return False
    return True

def main():
    manifest=js('source_manifest.json')
    verified=0
    for r in manifest['inputs']:
        b=subprocess.check_output(['git','show',r['source_commit']+':'+r['source_path']],cwd=REPO)
        assert b==(ROOT/r['stored_path']).read_bytes()
        assert sha(b)==r['sha256']
        verified+=1
    check('S01_EXACT_GIT_BLOBS',verified==56,dict(verified=verified,bytes=sum(r['bytes'] for r in manifest['inputs']),claim='Git bytes only, not raw primary source reacquisition'))
    specs=read('inputs/hypotheses/candidates.csv');inventory=read('inventory35.csv')
    check('I01_ALL35',len(specs)==len(inventory)==35 and len({r['candidate_id'] for r in inventory})==35,'IDs C01..C35 preserved')
    fields={'author_ref':'author','ancestor_ids':'ancestor_ids','author_paths':'proposed_paths','author_network_form':'network_form','author_frequency':'frequency_proposal','author_stop_rule':'stop_rule','author_demand_status':'demand_status','author_net_fare_status':'net_fare_status','author_resource_status':'resource_status','author_evaluation_status':'evaluation_status'}
    check('I02_AUTHOR_FIELDS',all(all(r[k]==s[v] for k,v in fields.items()) for r,s in zip(inventory,specs)),'Original statuses, paths, author/family and stop rules not overwritten')
    queued={i for r in read('experiment_queue.csv') for i in r['candidate_ids'].split(';')}
    check('I03_NO_DROPPED_ID',queued=={r['candidate_id'] for r in specs},dict(queued=len(queued)))
    check('I04_THREE_SELECTED',sum(r['state'].startswith('SELECTED') for r in read('experiment_queue.csv'))==3,'Only HF01/HF07/HF14 selected; no hidden mixed experiment')
    bounds=read('runs/hf01/retiming_boundaries.csv')
    oracle=[]
    for r in bounds:
        m=int(r['connection_min_minutes']);t=int(r['turn_min_minutes'])
        candidates=[(y,x) for x in range(241) for y in range(196) if m<=x-60<=180 and m<=195-y<=180 and 45+y-x>=t]
        feasible=bool(candidates)
        check('HF01_GRID_'+r['scenario_id'],feasible==(r['feasible']=='True') and (not feasible or (min(candidates)[0]==float(r['south_return_shift_min_minutes']) and max(x for y,x in candidates)==float(r['south_departure_shift_max_minutes']))),dict(m=m,t=t,solutions=len(candidates),minimum_y=min(candidates)[0] if candidates else None))
        oracle.append(dict(scenario_id=r['scenario_id'],minute_grid_pairs=241*196,feasible_pairs=len(candidates),minimum_return_slip_minutes=min(candidates)[0] if candidates else None))
    check('HF01_M60_T45',next(r for r in bounds if r['scenario_id']=='HF01_M60_T45')['earlier_than_frozen_sync_minutes']=='15.0','M60/T45: north unchanged, same345min SOUTH occupied, 15min earlier than frozen sync')
    check('HF01_M90_REFUSED',all(r['feasible']=='False' for r in bounds if r['connection_min_minutes']=='90'),'No M90 fit with turns30/45/60; an infeasible clock is not zero demand')
    # Continuous boundary: 2*m+t=180, not merely the selected integer grid.
    check('HF01_CONTINUOUS_BOUNDARY',2*67.5+45==180 and 2*67.5001+45>180,'At turn45, M67.5 is boundary and any greater M fails with fixed northern clocks')
    grouped=defaultdict(list)
    for r in read('runs/hf01/physical_legs.csv'):grouped[r['scenario_id'],r['departure_utc'][:10]].append(r)
    expected_pairs={('NJC','UFA'),('UFA','NJC'),('UFA','MRV'),('MRV','UFA')}
    for (profile,day),seq in grouped.items():
        assert len(seq)==4 and {(r['origin'],r['destination']) for r in seq}==expected_pairs
        p={(r['origin'],r['destination']):r for r in seq}
        m=int(profile.split('_M')[1].split('_')[0]);t=int(profile.split('_T')[1])
        for tail in ['NORTH','SOUTH']:
            ordered=sorted([r for r in seq if r['tail']==tail],key=lambda r:r['departure_utc'])
            assert ordered[0]['origin']==ordered[-1]['destination']
            assert ordered[0]['destination']==ordered[1]['origin']
            assert all(md(dt(r['arrival_utc']),dt(r['departure_utc']))==float(r['block_minutes']) for r in ordered)
            assert md(dt(ordered[1]['departure_utc']),dt(ordered[0]['arrival_utc']))>=t
        assert m<=md(dt(p['UFA','MRV']['departure_utc']),dt(p['NJC','UFA']['arrival_utc']))<=180
        assert m<=md(dt(p['UFA','NJC']['departure_utc']),dt(p['MRV','UFA']['arrival_utc']))<=180
        assert sum(float(r['block_minutes']) for r in seq)==540
        assert all(r['nominal_seats']=='100' for r in seq)
    check('HF01_PHYSICAL_CONSERVATION',len(grouped)==36,dict(operating_date_profiles=len(grouped),physical_legs=144,tail_positions='NJC/NJC and UFA/UFA; hypothetical starts only'))
    all_legs={r['leg_id']:r for r in read('runs/hf01/physical_legs.csv')}
    cohorts=read('runs/hf01/dated_products.csv')
    for r in cohorts:
        if r['gate']!='DATE_AND_CLOCK_SCENARIO_PASS':continue
        for key in ['outbound_leg_ids','return_leg_ids']:
            ids=r[key].split(';');assert len(ids)==len(set(ids))==2
            a,b=[all_legs[i] for i in ids]
            assert a['destination']==b['origin'] and dt(a['arrival_utc'])<dt(b['departure_utc'])
        assert int(r['endpoint_journeys_per_roundtrip'])==int(r['fare_applications_per_roundtrip'])==2
        assert int(r['physical_boardings_per_roundtrip'])==4
        assert date.fromisoformat(r['booked_checkout_date'])-date.fromisoformat(r['departure_date'])==timedelta(days=int(r['hotel_nights']))
        assert date.fromisoformat(r['return_home_date'])==date.fromisoformat(r['booked_checkout_date'])+timedelta(days=1)
    counts=Counter(r['scenario_id'] for r in cohorts if r['gate']=='DATE_AND_CLOCK_SCENARIO_PASS')
    check('HF01_DATED_RETURN',len(counts)==6 and set(counts.values())=={5},dict(successful_profiles=6,matched_combinations_each='5/6; 10night Mon7Dec checkout17Dec absent from fixed dates'))
    c7=read('runs/hf07/return_advance_boundaries.csv')
    for r in c7:
        t=int(r['turn_minutes']);slack=int(r['net_arrival_deadline_slack_minutes']);advance=float(r['required_departure_advance_minutes'])
        elapsed=475+3*t
        assert float(r['chain_elapsed_minutes'])==elapsed
        assert float(r['delta_elapsed_minutes'])==elapsed-255
        assert advance==max(0,elapsed-255-slack)
        end=dt(r['candidate_return_svx_local']);deadline=dt(r['deadline_utc'])
        assert end<=deadline
        if advance>0:assert end+timedelta(minutes=1)>deadline
    check('HF07_DEADLINE_BOUNDARIES',len(c7)==18,'One minute less advance fails at every active deadline; net arrival slack excludes any next-task turn')
    c7plans=defaultdict(list)
    for r in read('runs/hf07/physical_legs.csv'):c7plans[r['scenario_id']].append(r)
    for profile,seq in c7plans.items():
        seq=sorted(seq,key=lambda r:r['departure_utc']);t=int(profile.split('_T')[1].split('_')[0])
        assert len(seq)==4 and seq[0]['origin']==seq[-1]['destination']=='SVX'
        assert [(r['origin'],r['destination']) for r in seq]==[('SVX','OMS'),('OMS','KJA'),('KJA','OMS'),('OMS','SVX')]
        assert sum(float(r['block_minutes']) for r in seq)==475
        assert all(a['destination']==b['origin'] and md(dt(b['departure_utc']),dt(a['arrival_utc']))==t for a,b in zip(seq,seq[1:]))
    check('HF07_ALL_LEGS',len(c7plans)==18,dict(plans=18,legs=72,delta_block_minutes=270,operating_carrier_proxy='Retained; no RW dispatch admission'))
    check('HF07_NOT_FREE_RESOURCE',all(r['actual_tail_available']=='' and r['delta_money_rub']=='' for r in c7),'Exact return/earlier departure is not actual free aircraft or negative costs')
    c14=read('runs/hf14/bookability_tolerance.csv');summary=read('runs/hf14/tolerance_summary.csv')
    check('HF14_NESTED_TOLERANCE',[int(r['date_matched_distinct_combinations']) for r in summary]==[6,7,9,11],'0/1/2/3 extra booked nights:6/7/9/11 of12 date/stay combinations; property copies not additive demand')
    check('HF14_NULL_NOT_ZERO',all(r['accepted_full_products']=='' for r in summary),'All four full-product counts NULL, not inferred zero sales/demand')
    check('HF14_HORIZON',all(sum(r['date_gate']=='UNKNOWN_AFTER_CAPTURE' for r in c14 if r['scenario_id']==f'HF14_FLEX{i}')==2 for i in range(4)),'Checkout25Dec requests: next return beyond captured24Dec stays UNKNOWN at every policy')
    for r in c14:
        if r['minimum_additional_booked_nights']=='':continue
        wanted=date.fromisoformat(r['original_checkout_date']);returned=date.fromisoformat(r['next_captured_return_date'])
        assert (returned-wanted).days==int(r['minimum_additional_booked_nights'])
        assert int(r['revised_booked_nights'])==int(r['original_nights'])+int(r['minimum_additional_booked_nights'])
        assert (r['date_gate']=='DATE_MATCH_ONLY')==(int(r['minimum_additional_booked_nights'])<=int(r['max_additional_booked_nights']))
    check('HF14_BOOKING_HOLDS',all(r['current_full_product_gate']=='UNKNOWN_NOT_ESTABLISHED' and r['rw_airline_revenue_rub']=='' and r['rw_operating_flight_delta']=='' and r['additional_stay_price_rub']=='' for r in c14),'No nightly multiplication, fare attribution to RW or physical leg acceptance from endpoint rules')
    sales=read('runs/economics/fixture_itinerary.csv');loads=read('runs/economics/fixture_capacity_allocation.csv')
    check('E01_ONE_FARE_AND_EACH_LEG',fixture_audit(sales,loads),'A through fare once per journey, seat on every leg; expected overflows explicitly FAIL')
    check('E02_POSITIVE_SALES_THRESHOLD',all(float(r['threshold_contribution_rub'])>=0 and float(r['contribution_one_journey_each_direction_below_rub'])<0 for r in read('runs/economics/capacity_conditioned_thresholds.csv')),'Exact integer lower boundary in four declared mechanical fixtures')
    check('E03_CAPACITY_COUNTEREXAMPLE',all(r['capacity_gate']=='FAIL_PRESERVING_LOCALS' and r['required_q_each_direction']=='34' and r['maximum_new_contribution_with_locals_preserved_rub']=='300000' for r in read('runs/economics/capacity_conditioned_thresholds.csv') if r['assumed_K_fixed_rub']=='500000'),'K500k needs34 per direction; remaining20 cannot deliver more than300k at margin7500; no demand gain repairs occupied seats')
    changed=copy.deepcopy(sales);changed[0]['leg_ids']=changed[0]['leg_ids'].split(';')[0]
    check('M01_MISSING_LEG_REFUSED',not fixture_audit(changed,loads),'Deleting a through leg breaks boardings/allocation')
    changed=copy.deepcopy(sales);changed[0]['ticket_revenue']=str(2*int(changed[0]['ticket_revenue']))
    check('M02_DOUBLE_FARE_REFUSED',not fixture_audit(changed,loads),'One fare per each leg instead of per endpoint journey rejected')
    changed=copy.deepcopy(sales);changed[0]['leg_ids']+=';'+changed[0]['leg_ids'].split(';')[0]
    check('M03_DUPLICATE_LEG_REFUSED',not fixture_audit(changed,loads),'Duplicate consumption in same itinerary rejected')
    changed=copy.deepcopy(loads);changed[0]['total_load']=str(int(changed[0]['total_load'])-1)
    check('M04_HIDDEN_LOAD_REFUSED',not fixture_audit(sales,changed),'Hidden one-seat shortfall rejected')
    check('E04_FULL_MONEY_UNKNOWN',all(r['value_rub']==r['full_money_delta_rub']=='' for r in read('runs/economics/monetary_difference_terms.csv')),'18 explicitly named unknown money terms; NULL never summed as0')
    receipt=js('run_receipt.json')
    for n,h in receipt['hashes'].items():assert sha((ROOT/n).read_bytes())==h
    check('R01_PINNED_RUN',receipt['tests']==['HF01','HF07','HF14'],'Input manifest, predeclared scenario contract and executor hashed in run_id')
    # Re-run only our code. Compare every derived run byte, including receipt.
    before={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/'runs').rglob('*') if p.is_file()}
    subprocess.check_output(['python3','-B',str(ROOT/'run_experiments.py')],cwd=REPO)
    after={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/'runs').rglob('*') if p.is_file()}
    check('R02_DETERMINISTIC_REPLAY',before==after,dict(files=len(before),executed='Own offline code only; no foreign code/imports, no network or dependencies'))
    (ROOT/'self_checks.json').write_text(json.dumps(dict(acceptance='SELF_CHECK_ONLY_NOT_INDEPENDENT_REVIEW',run_id=receipt['run_id'],checks=CHECKS,pass_count=len(CHECKS),fail_count=0,minute_grid_oracle=oracle,real_market_source_operating_acceptance='NOT_ESTABLISHED'),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(checks=len(CHECKS),passed=len(CHECKS),independent_review='PENDING')))

if __name__=='__main__':main()
