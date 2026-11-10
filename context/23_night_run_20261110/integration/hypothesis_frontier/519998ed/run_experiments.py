#!/usr/bin/env python3
"""Three bounded offline comparisons. No source fetch, optimizer or demand fitting."""
from pathlib import Path
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from collections import Counter
import csv, json, hashlib, math

ROOT=Path(__file__).resolve().parent
IN=ROOT/'inputs/experiment'
H='6ed8788882e7b4d07044b4f6e686ff71eadd8ac5'
UTC=ZoneInfo('UTC')
ZONES={'SVX':'Asia/Yekaterinburg','OMS':'Asia/Omsk','KJA':'Asia/Krasnoyarsk','NJC':'Asia/Yekaterinburg','UFA':'Asia/Yekaterinburg','MRV':'Europe/Moscow'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(p.open()))
def write(p,rows):
    assert rows
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def js(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def stamp(s):return datetime.fromisoformat(s)
def minutes(a,b):return (a-b).total_seconds()/60

def retiming_bounds(baseline,m,t,maximum):
    pairs={(r['origin'],r['destination']):r for r in baseline}
    n_in=pairs['NJC','UFA'];s_out=pairs['UFA','MRV'];s_in=pairs['MRV','UFA'];n_out=pairs['UFA','NJC']
    w_out=minutes(stamp(s_out['departure_utc']),stamp(n_in['arrival_utc']))
    w_in=minutes(stamp(n_out['departure_utc']),stamp(s_in['arrival_utc']))
    turn=minutes(stamp(s_in['departure_utc']),stamp(s_out['arrival_utc']))
    xmin=max(0,m-w_out);outbound_only_xmax=maximum-w_out
    ymin=max(0,w_in-maximum,xmin+t-turn);ymax=w_in-m
    xmax=min(outbound_only_xmax,ymax+turn-t)
    feasible=xmin<=xmax and ymin<=ymax
    return dict(baseline_out_wait_minutes=w_out,baseline_in_wait_minutes=w_in,baseline_south_turn_minutes=turn,
                south_departure_shift_min_minutes=xmin,south_departure_shift_max_minutes=xmax,
                outbound_only_shift_max_minutes=outbound_only_xmax,
                south_return_shift_min_minutes=ymin if feasible else None,south_return_shift_max_minutes=ymax,
                max_connection_minimum_given_turn_minutes=(w_out+w_in+turn-t)/2,
                joint_constraints='x in [xmin,xmax]; y in [max(0,195-180,x+turn_min-45),195-M]; no earlier departures than baseline',feasible=feasible)

def plan_row(run,variant,src,start,end,source_id=None):
    return dict(model_id='HYPOTHESIS_FRONTIER',author_ref='Sol 6.1 xhigh; scenario derived from Astra hypotheses',source_commit=H,input_set_id='frontier-frozen-001',
                run_id=run,scenario_id=variant,leg_id=variant+':'+src['leg_id'],source_leg_id=source_id or src['leg_id'],tail=src['tail'],origin=src['origin'],destination=src['destination'],
                departure_utc=start.isoformat(),arrival_utc=end.isoformat(),departure_local=start.astimezone(ZoneInfo(ZONES[src['origin']])).isoformat(),arrival_local=end.astimezone(ZoneInfo(ZONES[src['destination']])).isoformat(),
                block_minutes=minutes(end,start),nominal_seats=100,capacity_status='SCENARIO_NOT_PAYLOAD',value_status='DERIVED_FROM_SCENARIO',operating_acceptance='UNKNOWN; not observed tail/slot/crew/MRO')

def hf01(contract,run):
    out=ROOT/'runs/hf01';out.mkdir(parents=True,exist_ok=True)
    raw=read(IN/'runs/c26661067277af20/physical_legs.csv')
    base=[r for r in raw if r['variant']=='C01_unsync' and r['departure_utc'].startswith('2026-12-07')]
    assert len(base)==4
    params=contract['tests'][0]['parameters'];boundaries=[];deadlines=[];legs=[];cohorts=[]
    operating_dates=json.loads((IN/'scenario_programs.json').read_text())['operating_dates']
    for m in params['connection_min_minutes']:
        for t in params['turn_min_minutes']:
            b=retiming_bounds(base,m,t,params['connection_max_minutes'])
            profile=f'HF01_M{m}_T{t}'
            row=dict(run_id=run,scenario_id=profile,candidate_id='C01',period_start='2026-12-07',period_end='2026-12-25',connection_min_minutes=m,turn_min_minutes=t,**b,
                     delta_flight_count=0,delta_total_block_minutes=0,south_delta_elapsed_minutes=t-45 if b['feasible'] else None,
                     frozen_sync_return_slip_minutes=135,earlier_than_frozen_sync_minutes=135-b['south_return_shift_min_minutes'] if b['feasible'] else None,
                     baseline_status='HYPOTHETICAL_SAME_LEGS_NOT_ACTUAL_EXISTING_NETWORK',resource_available=None,real_resource_reason='Dated real tail/slots/crew/MRO/overnight and next assignment UNKNOWN',
                     delta_money_rub=None,delta_money_reason='Complete K(q), paid OD/fare and local sales changes UNKNOWN',acceptance='OWNER_SCENARIO_ARITHMETIC_ONLY')
            boundaries.append(row)
            for limit in params['allowed_south_return_slip_minutes']:
                deadlines.append(dict(run_id=run,scenario_id=profile,allowed_return_slip_minutes=limit,required_slip_minutes=b['south_return_shift_min_minutes'],
                                      gate='FEASIBLE_SCENARIO_TIMES' if b['feasible'] and b['south_return_shift_min_minutes']<=limit else 'INFEASIBLE_SCENARIO_LIMITS',
                                      reason='2*M+turn <=180 and required return slip <= allowed' if b['feasible'] else '2*M+turn >180; no same-north-wave solution',real_operation='UNKNOWN'))
            generated={}
            if b['feasible']:
                x=b['south_departure_shift_min_minutes'];y=b['south_return_shift_min_minutes']
                for day in operating_dates:
                    source=[r for r in raw if r['variant']=='C01_unsync' and r['departure_utc'].startswith(day)]
                    assert len(source)==4
                    for r in source:
                        shift=x if (r['origin'],r['destination'])==('UFA','MRV') else y if (r['origin'],r['destination'])==('MRV','UFA') else 0
                        rr=plan_row(run,profile,r,stamp(r['departure_utc'])+timedelta(minutes=shift),stamp(r['arrival_utc'])+timedelta(minutes=shift))
                        legs.append(rr);generated[day,r['origin'],r['destination']]=rr
            for day in ['2026-12-07','2026-12-11']:
                for nights in [7,10,14]:
                    checkout=(date.fromisoformat(day)+timedelta(days=nights)).isoformat()
                    matched=b['feasible'] and checkout in operating_dates
                    out_ids=[generated[day,a,z]['leg_id'] for a,z in [('NJC','UFA'),('UFA','MRV')]] if b['feasible'] else []
                    in_ids=[generated[checkout,a,z]['leg_id'] for a,z in [('MRV','UFA'),('UFA','NJC')]] if matched else []
                    cohorts.append(dict(run_id=run,scenario_id=profile,departure_date=day,hotel_nights=nights,booked_checkout_date=checkout,
                                        return_home_date=generated[checkout,'UFA','NJC']['arrival_local'][:10] if matched else None,
                                        outbound_leg_ids=';'.join(out_ids),return_leg_ids=';'.join(in_ids),
                                        gate='DATE_AND_CLOCK_SCENARIO_PASS' if matched else 'NO_RETURN_DATE_IN_SCENARIO' if b['feasible'] else 'CONNECTION_TURN_INFEASIBLE',
                                        endpoint_journeys_per_roundtrip=2,physical_boardings_per_roundtrip=4,fare_applications_per_roundtrip=2,market='UNKNOWN'))
    write(out/'retiming_boundaries.csv',boundaries);write(out/'return_deadlines.csv',deadlines);write(out/'physical_legs.csv',legs);write(out/'dated_products.csv',cohorts)
    summary=dict(test_id='HF01',run_id=run,boundary_rows=len(boundaries),feasible_profiles=sum(b['feasible'] for b in boundaries),infeasible_profiles=sum(not b['feasible'] for b in boundaries),
                 deadline_rows=len(deadlines),deadline_infeasible=sum(r['gate'].startswith('INFEASIBLE') for r in deadlines),physical_legs=len(legs),dated_products=len(cohorts),
                 important_case='M60/T45: x=y=120min; waits60/75min, unchanged345min SOUTH elapsed, return15min earlier than frozen sync; real resource UNKNOWN',
                 independent_review='PENDING',source_acceptance='NO_NEW_SOURCE_ADMISSION',market_acceptance='NOT_ESTABLISHED')
    js(out/'summary.json',summary);return summary

def hf07(contract,run):
    out=ROOT/'runs/hf07';out.mkdir(parents=True,exist_ok=True)
    raw=read(IN/'runs/c26661067277af20/physical_legs.csv')
    reference=[r for r in raw if r['variant']=='C07_reference']
    start=min(stamp(r['departure_utc']) for r in reference);finish=max(stamp(r['arrival_utc']) for r in reference)
    base_elapsed=minutes(finish,start);base_block=sum(int(r['block_minutes']) for r in reference)
    params=contract['tests'][1]['parameters'];bounds=[];limits=[];legs=[]
    for t in params['turn_minutes']:
        source=[r for r in raw if r['variant']==f'C07_chain_turn{t}']
        assert len(source)==4
        chain_finish=max(stamp(r['arrival_utc']) for r in source)
        elapsed=minutes(chain_finish,start);slip=minutes(chain_finish,finish)
        for slack in params['net_arrival_deadline_slack_minutes']:
            required=max(0,slip-slack);variant=f'HF07_T{t}_L{slack}'
            shifted_start=start-timedelta(minutes=required);shifted_finish=chain_finish-timedelta(minutes=required)
            bounds.append(dict(run_id=run,scenario_id=variant,candidate_id='C07',turn_minutes=t,baseline_elapsed_minutes=base_elapsed,chain_elapsed_minutes=elapsed,delta_elapsed_minutes=elapsed-base_elapsed,
                               baseline_block_minutes=base_block,chain_block_minutes=sum(int(r['block_minutes']) for r in source),delta_block_minutes=270,
                               net_arrival_deadline_slack_minutes=slack,required_departure_advance_minutes=required,
                               reference_departure_svx_local=start.astimezone(ZoneInfo(ZONES['SVX'])).isoformat(),reference_return_svx_local=finish.astimezone(ZoneInfo(ZONES['SVX'])).isoformat(),
                               departure_svx_local_at_minimum_advance=shifted_start.astimezone(ZoneInfo(ZONES['SVX'])).isoformat(),candidate_return_svx_local=shifted_finish.astimezone(ZoneInfo(ZONES['SVX'])).isoformat(),
                               deadline_utc=(finish+timedelta(minutes=slack)).isoformat(),delta_flight_count=2,actual_tail_available=None,actual_tail_reason='No real donor/tail/next assignment/crew/MRO. Advance changes published base-leg times and possibly local dates.',
                               delta_money_rub=None,delta_money_reason='New legs/ground events plus changed base-leg sales/opportunity/obligations UNKNOWN',value_status='SCENARIO_WITH_OTHER_CARRIER_BLOCK_PROXY'))
            for allowance in params['advance_allowance_minutes']:
                limits.append(dict(run_id=run,scenario_id=variant,advance_allowance_minutes=allowance,required_advance_minutes=required,
                                   gate='PASS_SCENARIO_RETURN_LIMIT' if allowance>=required else 'FAIL_SCENARIO_RETURN_LIMIT',
                                   actual_operational_gate='UNKNOWN',deadline_semantics='Latest arrival after deducting any next-task turnaround; not crew-duty limit'))
            for r in source:
                legs.append(plan_row(run,variant,r,stamp(r['departure_utc'])-timedelta(minutes=required),stamp(r['arrival_utc'])-timedelta(minutes=required)))
    write(out/'return_advance_boundaries.csv',bounds);write(out/'advance_limits.csv',limits);write(out/'physical_legs.csv',legs)
    summary=dict(test_id='HF07',run_id=run,deadline_cases=len(bounds),advance_limit_cases=len(limits),failed_limits=sum(r['gate'].startswith('FAIL') for r in limits),physical_legs=len(legs),
                 frozen_reference='SVX dep2026-12-08 21:20+05, return2026-12-09 01:35+05; date alignment conditional',
                 exact_return_required_advance_minutes={str(t):next(r['required_departure_advance_minutes'] for r in bounds if r['turn_minutes']==t and r['net_arrival_deadline_slack_minutes']==0) for t in params['turn_minutes']},
                 actual_free_aircraft='UNKNOWN',independent_review='PENDING',market_acceptance='NOT_ESTABLISHED')
    js(out/'summary.json',summary);return summary

def hf14(contract,run):
    out=ROOT/'runs/hf14';out.mkdir(parents=True,exist_ok=True)
    products=read(IN/'c14_products/3906edd033f75bc6/flight_hotel_calendar.csv')
    flights=read(IN/'inputs/alternative_fa39de4/normalized/dated_flights.csv')
    returns=sorted([f for f in flights if f['origin_iata']=='MRV' and f['destination_iata']=='KVX'],key=lambda r:r['departure_utc'])
    rows=[];summaries=[];params=contract['tests'][2]['parameters']
    for limit in params['maximum_additional_booked_nights']:
        these=[]
        for p in products:
            desired=date.fromisoformat(p['booked_checkout_local_date'])
            later=[f for f in returns if date.fromisoformat(f['departure_local_date'])>=desired]
            chosen=later[0] if later else None
            extra=(date.fromisoformat(chosen['departure_local_date'])-desired).days if chosen else None
            gate='DATE_MATCH_ONLY' if extra is not None and extra<=limit else 'NEEDS_MORE_BOOKED_NIGHTS_THAN_ALLOWED' if extra is not None else 'UNKNOWN_AFTER_CAPTURE'
            new=dict(run_id=run,scenario_id=f'HF14_FLEX{limit}',candidate_id='C14',product_request_id=p['product_request_id'],
                     date_stay_combination_id='|'.join([p['outbound_instance_id'],p['stay_basis'],p['hotel_nights']]),property_id=p['property_id'],
                     outbound_instance_id=p['outbound_instance_id'],original_return_instance_id=p['return_instance_id'],outbound_departure_local=p['outbound_departure_local'],outbound_arrival_local=p['outbound_arrival_local'],
                     booked_checkin_date=p['booked_checkin_local_date'],original_nights=int(p['hotel_nights']),original_checkout_date=desired.isoformat(),
                     max_additional_booked_nights=limit,minimum_additional_booked_nights=extra,revised_booked_nights=int(p['hotel_nights'])+extra if extra is not None else None,
                     next_captured_return_id=chosen['instance_id'] if chosen else None,next_captured_return_date=chosen['departure_local_date'] if chosen else None,
                     date_gate=gate,flight_inventory='UNKNOWN',hotel_minimum_stay='UNKNOWN',hotel_admission='UNKNOWN',hotel_extended_inventory='UNKNOWN',property_time_basis=p['property_iana'],ground_transfer='UNKNOWN',
                     customer_extension_acceptance='UNKNOWN',current_full_product_gate='UNKNOWN_NOT_ESTABLISHED',additional_stay_price_rub=None,stay_price_reason='Billed person/bed days and rates for revised stay unknown; nights are not billed days',
                     rw_airline_revenue_rub=None,rw_revenue_reason='Incumbent A4 advertised service; no RW commercial rights, fare or full RW operating chain',
                     same_incumbent_published_flights_delta=0,rw_operating_flight_delta=None,rw_operating_delta_reason='No complete RW calendar/resource/admitted product',
                     endpoint_journeys_per_customer=2,endpoint_service_claim_per_oneway_product=1,physical_seat_segments_per_oneway_product=None,physical_nonstop_acceptance='UNKNOWN; endpoint schedule does not prove physical nonstop or same tail; actual leg seats cannot yet be allocated',
                     publication_period='captured dates2026-12-07..24; not complete market schedule',value_status='DERIVED_PUBLISHED_CALENDAR_PLUS_CUSTOMER_TOLERANCE_SCENARIO')
            these.append(new);rows.append(new)
        counts=Counter(r['date_gate'] for r in these)
        combos={r['date_stay_combination_id'] for r in these}
        assert len(combos)==12
        summaries.append(dict(run_id=run,scenario_id=f'HF14_FLEX{limit}',max_additional_booked_nights=limit,property_request_rows=len(these),distinct_date_stay_combinations=len(combos),
                              date_matched_property_rows=counts['DATE_MATCH_ONLY'],date_matched_distinct_combinations=len({r['date_stay_combination_id'] for r in these if r['date_gate']=='DATE_MATCH_ONLY'}),
                              beyond_tolerance_property_rows=counts['NEEDS_MORE_BOOKED_NIGHTS_THAN_ALLOWED'],after_capture_unknown_property_rows=counts['UNKNOWN_AFTER_CAPTURE'],
                              accepted_full_products=None,accepted_reason='No complete booking/market acceptance; matched properties and policies are overlapping alternatives, never independent travelers',new_rw_flights=None))
    write(out/'bookability_tolerance.csv',rows);write(out/'tolerance_summary.csv',summaries)
    js(out/'summary.json',dict(test_id='HF14',run_id=run,rows=len(rows),tolerances=summaries,independent_review='PENDING',full_product_acceptance='UNKNOWN_NOT_ZERO_DEMAND',physical_leg_assignment='NO_NEW_RW_PHYSICAL_ASSIGNMENT'))
    return dict(test_id='HF14',rows=len(rows),policies=summaries)

def economics(run):
    out=ROOT/'runs/economics';out.mkdir(parents=True,exist_ok=True)
    terms=[]
    for test,baseline,entries in [
      ('HF01','same four hypothetical unsync flights',[
        ('delta_flight_cost','-','0 ONLY_IF identical per-leg costs/contracts; real timing premiums UNKNOWN'),
        ('new_endpoint_revenue','+','q_out*F_out + q_return*F_return; through fare once per itinerary'),
        ('new_journey_expense','-','q_out*v_out + q_return*v_return, only amounts not already netted from F'),
        ('retiming_base_overnight_reserve_switching','-','Full incremental terms and included-in must be established'),
        ('changed_local_margin','+/-','Revenue minus passenger expense only; flight costs separately; depends on q/seat allocation'),
        ('other_retained_network_and_opportunity_margin','+/-','One own-network effect; not gross old revenue plus the same old margin')]),
      ('HF07','KEEP published timing reference SVX-OMS-SVX',[
        ('delta_flight_cost','-','All OMS-KJA-KJA-OMS flight costs; any timing change on base legs included'),
        ('target_local_OMS_KJA_revenue','+','One fare per local endpoint journey; two independent directions not presumed same customers'),
        ('target_local_journey_expense','-','Per local journey expense not already netted'),
        ('delta_base_leg_margin','+/-','Both dated SVX-OMS legs; earlier start/later return may change all paid products'),
        ('delta_ground_crew_MRO_fixed_switching','-','Every new paid event/contract term; movement counts are not bill counts'),
        ('other_resource_opportunity_and_obligations','-','Actual donor/next assignment UNKNOWN; no fixed-cost saving from an idle-looking interval')]),
      ('HF14','passenger calendar on incumbent flights; RW investment baseline preserve own network',[
        ('incumbent_physical_flights','0 conditional','Same captured published flights in calendar policies; no airline savings inferred'),
        ('extra_stay_and_transfer_cost_to_customer','-','Booked nights do not establish billed person/bed days, inventory or total price'),
        ('customer_willingness_premium','+','UNKNOWN; date match is not paid premium or measured choice'),
        ('RW_full_proposed_chain_cost','-','Every SVX-KVX-MRV-KVX-SVX leg, plus full incremental fixed/resource cost if RW enters'),
        ('RW_new_endpoint_revenue_and_base_margin','+','No current A4 offer is RW fare; base-leg revenue not free/guaranteed'),
        ('RW_obligations_opportunity_and_own_migration','-','One coherent baseline; preserve contracts and avoid duplicate donor/cannibalization')])]:
        for term,sign,reason in entries:
            terms.append(dict(run_id=run,test_id=test,baseline=baseline,term_id=term,delta_sign=sign,value_rub=None,currency='RUB',price_basis=None,tax_basis=None,value_status='UNKNOWN',reason=reason,
                              full_money_delta_rub=None,full_money_status='UNKNOWN; do not sum NULL as0',accounting_scope='Delta relative to named baseline; capex/deposits/working capital require separate cash timing and are not automatically P&L expenses'))
    write(out/'monetary_difference_terms.csv',terms)
    # Narrow capacity-conditioned counterexamples. These are not OD/fare estimates.
    fixtures=[];loads=[];sales=[]
    for c,physical_per_oneway,local_each,required_gap in [('C01',2,80,300000),('C01',2,80,500000),('C07',1,80,300000),('C07',1,80,500000)]:
        fare=8000;variable=500;residual=100-local_each
        q=math.ceil(required_gap/(2*(fare-variable)))
        fixture=f'{c}_G{required_gap}'
        feasible=q<=residual
        fixtures.append(dict(run_id=run,fixture_id=fixture,candidate_id=c,unit='one allocated pair of directional departure opportunities, not weekly/annual forecast',
                             nominal_seats_each_leg=100,local_sales_each_used_leg=local_each,residual_each_leg=residual,
                             net_fare_per_endpoint_journey=8000,journey_expense=500,assumed_K_fixed_rub=required_gap,required_q_each_direction=q,
                             capacity_gate='PASS_FIXTURE_ONLY' if feasible else 'FAIL_PRESERVING_LOCALS',
                             endpoint_journeys=2*q,physical_boardings=2*q*physical_per_oneway,through_fare_applications=2*q,
                             ticket_revenue_once_rub=2*q*fare,threshold_contribution_rub=2*q*(fare-variable)-required_gap,
                             contribution_one_journey_each_direction_below_rub=2*(q-1)*(fare-variable)-required_gap,
                             maximum_new_contribution_with_locals_preserved_rub=2*residual*(fare-variable),
                             actual_K_fare_OD_residual_seats='UNKNOWN',assumption='Nominal100/local80/fare8000/expense500 are declared mechanical fixtures; local losses not also added to K; if K depends on q invert full K(q) instead'))
        for direction in ['OUT','BACK']:
            ids=[fixture+':'+direction+':'+str(i+1) for i in range(physical_per_oneway)]
            sales.append(dict(fixture_id=fixture,itinerary_id=fixture+':'+direction,leg_ids=';'.join(ids),quantity=q,net_fare_per_journey=fare,ticket_revenue=q*fare,endpoint_journeys=q,physical_boardings=q*physical_per_oneway))
            for ident in ids:loads.append(dict(fixture_id=fixture,leg_id=ident,nominal_seats=100,local_seats=80,new_journeys=q,total_load=80+q,gate='PASS' if 80+q<=100 else 'FAIL',value_status='MECHANICAL_NOT_MARKET'))
    write(out/'capacity_conditioned_thresholds.csv',fixtures);write(out/'fixture_itinerary.csv',sales);write(out/'fixture_capacity_allocation.csv',loads)
    js(out/'summary.json',dict(terms=len(terms),threshold_counterexamples=len(fixtures),real_full_budget='UNKNOWN',real_cash='UNKNOWN',independent_review='PENDING'))
    return dict(terms=len(terms),counterexamples=len(fixtures))

def main():
    contract=json.loads((ROOT/'test_contract.json').read_text())
    manifest=json.loads((ROOT/'source_manifest.json').read_text())
    for entry in manifest['inputs']:assert sha(ROOT/entry['stored_path'])==entry['sha256'],entry['input_id']
    hashes={n:sha(ROOT/n) for n in ['source_manifest.json','test_contract.json','run_experiments.py']}
    run=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:20]
    results=[hf01(contract,run),hf07(contract,run),hf14(contract,run)]
    econ=economics(run)
    js(ROOT/'run_receipt.json',dict(run_id=run,input_set_id='frontier-frozen-001',hashes=hashes,source_commit=H,tests=[r['test_id'] for r in results],economics=econ,
                                 network_access='NONE',new_dependencies='NONE',independent_review='PENDING',source_market_operating_acceptance='NOT_ESTABLISHED'))
    print(json.dumps(dict(run_id=run,tests=[r['test_id'] for r in results],economics=econ)))

if __name__=='__main__':main()
