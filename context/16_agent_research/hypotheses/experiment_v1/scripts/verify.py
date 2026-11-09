#!/usr/bin/env python3
"""Independent output checks plus adversarial mechanical fixtures; no network."""
from pathlib import Path
from datetime import datetime,date
from collections import Counter,defaultdict
import csv,json,hashlib,sys,importlib.util
ROOT=Path(__file__).resolve().parents[1]
def rows(path):return list(csv.DictReader(path.open()))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    run_id=sys.argv[1];out=ROOT/'runs'/run_id;checks=[]
    def check(name,condition,scope):
        checks.append({'check':name,'status':'PASS' if condition else 'FAIL','scope':scope})
    manifest=json.loads((out/'output_manifest.json').read_text())
    check('output_hashes',all(sha(out/r['path'])==r['sha256'] for r in manifest['files']),'byte integrity')
    check('frozen_input_snapshots',all(sha(ROOT/'snapshots'/(h+'.blob'))==h for h in manifest['input_hashes'].values()),'immutable replay inputs')
    legs=rows(out/'physical_legs.csv');check('leg_id_unique',len({r['leg_id'] for r in legs})==len(legs),'physical movement keys')
    check('positive_utc_blocks',all((datetime.fromisoformat(r['arrival_utc'])-datetime.fromisoformat(r['departure_utc'])).total_seconds()/60==int(r['block_minutes'])>0 for r in legs),'UTC arithmetic')
    match=defaultdict(list)
    for r in legs:
        if r['variant'].startswith('C01_'):match[r['departure_utc'][:10],r['variant']].append((r['tail'],r['origin'],r['destination'],r['block_minutes'],r['nominal_seats']))
    dates={k[0] for k in match}
    check('hub_same_legs_duration_capacity_tails',all(sorted(match[d,'C01_sync'])==sorted(match[d,'C01_unsync']) for d in dates),'matched hypothetical programs')
    times=defaultdict(list)
    for r in legs:times[r['variant'],r['leg_id'].rsplit('_',2)[1],r['tail']].append(r)
    check('tail_geographic_continuity',all(seq[0]['origin']==seq[-1]['destination'] and all(a['destination']==b['origin'] and datetime.fromisoformat(a['arrival_utc'])<=datetime.fromisoformat(b['departure_utc']) for a,b in zip(seq,seq[1:])) for seq in [sorted(v,key=lambda x:x['departure_utc']) for v in times.values()]),'whole dated rotation across UTC midnight')
    resources=rows(out/'resource_checks.csv');check('tail_closed',all(r['initial_airport']==r['final_airport'] for r in resources),'every evaluated rotation')
    chain=rows(out/'c07_comparison.csv')
    check('chain_all_legs_and_elapsed',all(int(r['legs_candidate'])==4 and int(r['block_candidate_minutes'])==475 and int(r['elapsed_candidate_minutes'])==475+3*int(r['variant'].split('turn')[1]) and int(r['elapsed_baseline_minutes'])==255 for r in chain),'table clocks and ground additions; not dispatch block clearance')
    check('chain_does_not_reuse_reference_slot',all(int(r['return_delay_vs_reference_minutes'])>0 and r['same_reference_slot_gate'].startswith('FAIL') and r['donor_id']=='UNKNOWN' for r in chain),'replacement remains unproven')
    cohorts=rows(out/'c01_dated_cohorts.csv')
    check('cohort_nights_from_stay_dates',all((date.fromisoformat(r['checkout_local'])-date.fromisoformat(r['booked_stay_start_local'])).days==int(r['hotel_nights']) for r in cohorts),'dated customer cohorts')
    check('connection_fare_once_two_seats',all(int(r['fare_applications'])==1 and int(r['leg_seats_consumed'])==2 and len(r['leg_ids'].split(';'))==2 for r in rows(out/'c01_connections.csv')),'itinerary vs segments')
    real=rows(out/'c14_real_calendar_requests.csv');check('c14_no_november_extrapolation',len(real)==21 and all(r['calendar_gate']=='UNKNOWN' and not r['outbound_service_id'] and not r['return_service_id'] for r in real),'no December rule admitted in input001')
    boundary=[r for r in rows(out/'c14_conditional_stay_dates.csv') if r['checkout_local']=='2026-12-28']
    check('horizon_unknown_not_impossible',len(boundary)==1 and boundary[0]['calendar_gate']=='UNKNOWN_HORIZON_COVERAGE','booked14Dec plus14nights')
    money=rows(out/'conditional_thresholds.csv');correct=True
    for r in money:
        gap=int(r['residual_funding_gap_rub']);margin=int(r['net_fare_rub_per_oneway_journey'])-int(r['variable_cost_rub_per_oneway_journey'])
        q=next((x for x in range(1001) if 2*x*margin>=gap),None)
        correct &= q==int(r['required_paid_journeys_each_direction']) and int(r['required_ticket_revenue_rub'])==2*q*int(r['net_fare_rub_per_oneway_journey'])
    check('money_threshold_independent_integer_search',correct and len(money)==108,'same declared arithmetic grid, no demand validation')
    check('no_actual_market_imputation',all(r['actual_funding_gap']==r['actual_net_fare']==r['market_demand']=='UNKNOWN' for r in money),'unknowns preserved')
    spec=importlib.util.spec_from_file_location('evaluator',ROOT/'scripts/evaluate.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    check('inverse_zero_and_negative_margin',module.inverse(1,0,1) is None and module.inverse(1,1,1) is None and module.inverse(0,1,1)==0 and module.inverse(15,8,0)==1,'failure boundary fixtures')
    allocation=module.seat_allocation([{'leg_id':'A','nominal_seats':100},{'leg_id':'B','nominal_seats':100}],[{'leg_ids':['A'],'quantity':80,'net_fare':5000},{'leg_ids':['B'],'quantity':80,'net_fare':5000},{'leg_ids':['A','B'],'quantity':25,'net_fare':8000}])
    check('shared_capacity_detects_overbooking',set(allocation['exceeded_leg_ids'])=={'A','B'} and allocation['ticket_revenue_once_per_journey']==1000000,'joint local and transfer seat fixture')
    check('acceptance_separated',all(r['train_holdout']=='NO_LABELS' and r['market']=='NOT_ACCEPTED' and r['launch']=='NOT_EVALUATED' for r in rows(out/'acceptance.csv')),'no quality forecast from absent labels')
    result={'run_id':run_id,'status':'PASS' if all(r['status']=='PASS' for r in checks) else 'FAIL','checks':checks,'review_type':'AUTHOR_OFFLINE_CHECKS; independent critic review separate','limits':['No observed endpoint demand or net realised fare','No confirmed aircraft/crew/dispatch feasibility','Clock design is hypothetical except scoped source references','No full case network of8-12 routes selected']}
    target=ROOT/'checks'/run_id;target.mkdir(parents=True,exist_ok=True);(target/'author_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'checks':len(checks),'failed':[r['check'] for r in checks if r['status']=='FAIL']}));sys.exit(result['status']!='PASS')
if __name__=='__main__':main()
