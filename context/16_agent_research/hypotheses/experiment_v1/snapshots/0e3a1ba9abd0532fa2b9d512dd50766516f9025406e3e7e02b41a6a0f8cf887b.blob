#!/usr/bin/env python3
"""Offline calendar/resource/threshold experiment; never a demand forecast."""
from pathlib import Path
from datetime import datetime,date,time,timedelta,timezone
from zoneinfo import ZoneInfo
from decimal import Decimal,ROUND_CEILING
import csv,json,hashlib,itertools,traceback

ROOT=Path(__file__).resolve().parents[1]
UTC=timezone.utc
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read_csv(path):return list(csv.DictReader(path.open()))
def write_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def write_csv(path,rows):
    assert rows,'Empty output requires an explicit schema'
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def minute_delta(end,start):return int((end-start).total_seconds()/60)
def local_stamp(day,clock,zone):
    return datetime.combine(day,time.fromisoformat(clock.replace('.',':')),ZoneInfo(zone)).astimezone(UTC)
def inverse(gap,fare,cost):
    margin=Decimal(str(fare))-Decimal(str(cost));gap=Decimal(str(gap))
    if gap<=0:return 0
    if margin<=0:return None
    return int((gap/(2*margin)).to_integral_value(rounding=ROUND_CEILING))
def path_status(legs,min_connection,max_connection):
    if any(b['origin']!=a['destination'] for a,b in zip(legs,legs[1:])):return 'DISCONNECTED_PATH'
    waits=[minute_delta(datetime.fromisoformat(b['departure_utc']),datetime.fromisoformat(a['arrival_utc'])) for a,b in zip(legs,legs[1:])]
    if any(x<min_connection for x in waits):return 'BELOW_SCENARIO_MIN_CONNECTION'
    if any(x>max_connection for x in waits):return 'ABOVE_SCENARIO_MAX_CONNECTION'
    return 'PASS_SCENARIO_CLOCK'
def seat_allocation(legs,sales):
    by_id={r['leg_id']:r for r in legs};loads={k:0 for k in by_id};revenue=0
    for sale in sales:
        assert sale['quantity']>=0
        assert len(sale['leg_ids'])==len(set(sale['leg_ids']))
        revenue+=sale['quantity']*sale['net_fare']
        for key in sale['leg_ids']:
            assert key in loads;loads[key]+=sale['quantity']
    exceeded=[k for k,q in loads.items() if q>by_id[k]['nominal_seats']]
    return {'loads':loads,'ticket_revenue_once_per_journey':revenue,'exceeded_leg_ids':exceeded}
def leg(variant,day,index,tail,origin,destination,start,end,zones,source,status='SCENARIO'):
    return dict(variant=variant,leg_id=f'{variant}_{day}_{index}',tail=tail,origin=origin,destination=destination,
                departure_utc=start.isoformat(),arrival_utc=end.isoformat(),
                departure_local=start.astimezone(ZoneInfo(zones[origin])).isoformat(),arrival_local=end.astimezone(ZoneInfo(zones[destination])).isoformat(),
                block_minutes=minute_delta(end,start),nominal_seats=100,capacity_status='SCENARIO_NOT_PAYLOAD',
                physical_status=status,calendar_date_status='SCENARIO_ALIGNMENT_NOT_CONFIRMED_INSTANCE',dispatch_block_status='UNKNOWN',operating_carrier='UNKNOWN',marketing_carrier='UNKNOWN',
                nonstop_status='SCENARIO_DESIGN_NOT_OPERATIONAL_CONFIRMATION',source=source)
def resource_rows(legs,starts,turn_min,windows):
    output=[]
    for tail,initial in starts.items():
        seq=sorted([r for r in legs if r['tail']==tail],key=lambda x:x['departure_utc'])
        current=initial;previous=None;errors=[];waits=[]
        for r in seq:
            dep=datetime.fromisoformat(r['departure_utc']);arr=datetime.fromisoformat(r['arrival_utc'])
            if r['origin']!=current:errors.append('TAIL_POSITION_DISCONTINUITY')
            if arr<=dep:errors.append('NON_POSITIVE_BLOCK')
            if previous is not None:
                wait=minute_delta(dep,previous);waits.append(wait)
                if wait<turn_min:errors.append('TURN_BELOW_SCENARIO_MIN')
            current=r['destination'];previous=arr
        if current!=initial:errors.append('TAIL_NOT_CLOSED')
        elapsed=minute_delta(datetime.fromisoformat(seq[-1]['arrival_utc']),datetime.fromisoformat(seq[0]['departure_utc']))
        for window in windows:
            output.append(dict(variant=seq[0]['variant'],date=seq[0]['departure_local'][:10],tail=tail,initial_airport=initial,final_airport=current,
                physical_leg_count=len(seq),block_minutes=sum(r['block_minutes'] for r in seq),ground_minutes=sum(waits),elapsed_minutes=elapsed,
                turn_min_scenario=turn_min,window_minutes_scenario=window,clock_gate='PASS_SCENARIO_CLOCK' if not errors and elapsed<=window else 'FAIL_SCENARIO_CLOCK',
                reason=';'.join(errors+(['EXCEEDS_SCENARIO_WINDOW'] if elapsed>window else [])),availability='UNKNOWN',crew_legality='UNKNOWN',engineering_clearance='UNKNOWN'))
    return output
def check_inputs(manifest):
    for r in manifest['inputs']:assert sha(ROOT/r['stored_path'])==r['sha256'],r['input_id']

def evaluate(out,contract,programs,manifest):
    check_inputs(manifest)
    scope=['NJC','UFA','MRV','KVX','SVX','OMS','KJA']
    keys=[r for r in read_csv(ROOT/'inputs/core/airport_timezone_join.csv') if r['iata_code'] in scope]
    assert len(keys)==7 and len({r['iata_code'] for r in keys})==7
    assert all(r['iana_timezone'] and r['timezone_validation_status']!='OFFSET_CONFLICT' for r in keys)
    zones={r['iata_code']:r['iana_timezone'] for r in keys}
    write_csv(out/'airport_keys.csv',[dict(airport_id=r['airport_id'],iata=r['iata_code'],iana=r['iana_timezone'],source_status=r['timezone_validation_status'],utc_offset_minutes=int(local_stamp(date(2026,12,7),'12:00',r['iana_timezone']).astimezone(ZoneInfo(r['iana_timezone'])).utcoffset().total_seconds()/60),source_input='core:airport_timezone_join.csv') for r in keys])
    s=contract['frozen_scenarios'];all_legs=[];resources=[];connections=[];cohorts=[]
    # C01: identical directed legs, block durations and tail starts; times differ.
    for mode in ['sync','unsync']:
        for day in programs['operating_dates']:
            legs=[]
            for i,(tail,a,b,dep,arr) in enumerate(programs['C01'][mode+'_utc'],1):
                start=datetime.fromisoformat(day+'T'+dep+':00+00:00');end=datetime.fromisoformat(day+'T'+arr+':00+00:00')
                legs.append(leg('C01_'+mode,day,i,tail,a,b,start,end,zones,'scenario_programs.json:C01'))
            all_legs+=legs
            for turn in s['turn_minutes']:resources+=resource_rows(legs,programs['C01']['tail_starts'],turn,s['aircraft_window_minutes'])
            by_pair={(r['origin'],r['destination']):r for r in legs}
            for a,b,c in [('NJC','UFA','MRV'),('MRV','UFA','NJC')]:
                journey=[by_pair[a,b],by_pair[b,c]]
                for minimum in s['connection_min_minutes']:
                    connections.append(dict(candidate='C01',variant='C01_'+mode,service_date=day,origin=a,destination=c,
                        itinerary_id=f'C01_{mode}_{day}_{a}_{c}_M{minimum}',leg_ids=';'.join(r['leg_id'] for r in journey),
                        departure_local=journey[0]['departure_local'],arrival_local=journey[-1]['arrival_local'],
                        min_connection_minutes=minimum,max_connection_minutes=s['connection_max_minutes'],
                        actual_wait_minutes=minute_delta(datetime.fromisoformat(journey[1]['departure_utc']),datetime.fromisoformat(journey[0]['arrival_utc'])),
                        calendar_gate=path_status(journey,minimum,s['connection_max_minutes']),protected_ticket='UNKNOWN',through_baggage='UNKNOWN',
                        one_way_journeys=1,leg_seats_consumed=2,fare_applications=1,value_type='SCENARIO'))
    for minimum in s['connection_min_minutes']:
        for mode in ['sync','unsync']:
            for day in [d for d in programs['operating_dates'] if d<=contract['period']['end']]:
                outbound=next(r for r in connections if r['variant']=='C01_'+mode and r['service_date']==day and r['origin']=='NJC' and r['min_connection_minutes']==minimum)
                stay_start=date.fromisoformat(outbound['arrival_local'][:10])
                for nights in [7,10,14]:
                    checkout=stay_start+timedelta(days=nights)
                    inbound=next((r for r in connections if r['variant']=='C01_'+mode and r['service_date']==checkout.isoformat() and r['origin']=='MRV' and r['min_connection_minutes']==minimum),None)
                    gate='PASS_SCENARIO_CALENDAR' if inbound and all(x['calendar_gate']=='PASS_SCENARIO_CLOCK' for x in [outbound,inbound]) else 'NO_EXACT_PRODUCT_IN_SCENARIO'
                    if checkout>date.fromisoformat(contract['period']['product_return_horizon']):gate='UNKNOWN_HORIZON_COVERAGE'
                    cohorts.append(dict(candidate='C01',variant='C01_'+mode,outbound_origin_date=day,booked_stay_start_local=stay_start.isoformat(),hotel_nights=nights,checkout_local=checkout.isoformat(),
                        return_origin_date=inbound['departure_local'][:10] if inbound else '',return_home_arrival_date=inbound['arrival_local'][:10] if inbound else '',
                        min_connection_minutes=minimum,outbound_id=outbound['itinerary_id'],return_id=inbound['itinerary_id'] if inbound else '',
                        calendar_gate=gate,one_way_journeys=2,leg_seats_consumed=4,roundtrip_customers=1,value_type='SCENARIO',market_gate='UNKNOWN'))
    write_csv(out/'c01_connections.csv',connections);write_csv(out/'c01_dated_cohorts.csv',cohorts)
    # C07 source clocks are explicitly local. OMS-local date is the timetable anchor.
    source=read_csv(ROOT/'inputs/core/omsk_domestic_timetable_rows.csv')
    rw=next(r for r in source if r['source_text_line']==programs['C07']['omsk_rw_source_line'])
    fv=next(r for r in source if r['source_text_line']==programs['C07']['omsk_rossiya_source_line'])
    anchor=date.fromisoformat(programs['C07']['omsk_anchor_date']);previous=anchor-timedelta(days=1)
    assert anchor.isoweekday() in {int(x) for x in rw['weekdays_raw'].split(',')}
    # FV applies on a separate Saturday; its clock difference is a proxy, not an actual Wednesday flight.
    fv_anchor=date(2026,12,12);fv_previous=fv_anchor-timedelta(days=1)
    stamps={
        'SVX_OMS':(local_stamp(previous,rw['preceding_origin_departure_local_raw'],zones['SVX']),local_stamp(anchor,rw['omsk_arrival_local_raw'],zones['OMS'])),
        'OMS_SVX':(local_stamp(anchor,rw['omsk_departure_local_raw'],zones['OMS']),local_stamp(anchor,rw['onward_arrival_local_raw'],zones['SVX'])),
        'OMS_KJA':(local_stamp(fv_anchor,fv['omsk_departure_local_raw'],zones['OMS']),local_stamp(fv_anchor,fv['onward_arrival_local_raw'],zones['KJA'])),
        'KJA_OMS':(local_stamp(fv_previous,fv['preceding_origin_departure_local_raw'],zones['KJA']),local_stamp(fv_anchor,fv['omsk_arrival_local_raw'],zones['OMS']))}
    blocks={k:minute_delta(b,a) for k,(a,b) in stamps.items()};assert all(0<x<1080 for x in blocks.values())
    write_csv(out/'c07_directional_clock_references.csv',[dict(pair=k,departure_utc=a.isoformat(),arrival_utc=b.isoformat(),elapsed_minutes=blocks[k],source_line=rw['source_text_line'] if 'SVX' in k else fv['source_text_line'],value_type='DERIVED_CONDITIONAL_CLOCK_ARITHMETIC',date_alignment='SCENARIO_OMS_ANCHOR_REMOTE_OFFSET; preceding day selected under positive elapsed<18h; not independently confirmed',application_status='SCENARIO_PROXY_FOR_NEW_RW_LEG' if 'KJA' in k else 'PUBLISHED_ENDPOINT_REFERENCE',actual_operating_block='UNKNOWN') for k,(a,b) in stamps.items()])
    base=[]
    for i,k in enumerate(['SVX_OMS','OMS_SVX'],1):
        a,b=k.split('_');start,end=stamps[k];base.append(leg('C07_reference',str(previous),i,'CHAIN',a,b,start,end,zones,'core timetable line68','TIMETABLE_REFERENCE_WITH_SCENARIO_TAIL'))
    all_legs+=base;resources+=resource_rows(base,{'CHAIN':'SVX'},30,s['aircraft_window_minutes'])
    reference_finish=datetime.fromisoformat(base[-1]['arrival_utc']);chain_results=[]
    for turn in s['turn_minutes']:
        variant=f'C07_chain_turn{turn}';start=stamps['SVX_OMS'][0];legs=[]
        for i,k in enumerate(['SVX_OMS','OMS_KJA','KJA_OMS','OMS_SVX'],1):
            a,b=k.split('_');end=start+timedelta(minutes=blocks[k]);legs.append(leg(variant,str(previous),i,'CHAIN',a,b,start,end,zones,'core lines68/79 + scenario turn','SCENARIO_WITH_TIMETABLE_PROXIES'));start=end+timedelta(minutes=turn)
        all_legs+=legs;resources+=resource_rows(legs,{'CHAIN':'SVX'},turn,s['aircraft_window_minutes'])
        finish=datetime.fromisoformat(legs[-1]['arrival_utc'])
        chain_results.append(dict(variant=variant,baseline='C07_reference',legs_candidate=4,legs_baseline=2,block_candidate_minutes=sum(r['block_minutes'] for r in legs),block_baseline_minutes=sum(r['block_minutes'] for r in base),
            elapsed_candidate_minutes=minute_delta(finish,stamps['SVX_OMS'][0]),elapsed_baseline_minutes=minute_delta(reference_finish,stamps['SVX_OMS'][0]),return_delay_vs_reference_minutes=minute_delta(finish,reference_finish),
            initial_airport='SVX',final_airport='SVX',same_reference_slot_gate='FAIL_CANNOT_KEEP_REFERENCE_RETURN',tail_next_assignment='UNKNOWN',donor_id='UNKNOWN',actual_replaceability='NOT_EVALUATED'))
    write_csv(out/'c07_comparison.csv',chain_results)
    # C14: real evidence never carries November clocks/weekdays into December.
    c14=[];conditional=[]
    start=date.fromisoformat(contract['period']['start']);end=date.fromisoformat(contract['period']['end']);horizon=date.fromisoformat(contract['period']['product_return_horizon'])
    for offset in range((end-start).days+1):
        departure=start+timedelta(days=offset)
        for nights in programs['C14']['hotel_nights']:
            c14.append(dict(candidate='C14',requested_origin_departure_date=departure.isoformat(),hotel_nights=nights,booked_checkin_local='',checkout_local='',outbound_service_id='',return_service_id='',calendar_gate='UNKNOWN',reason='NO_DATED_DECEMBER_BIDIRECTIONAL_RULE; hotel stay dates and transfer/admission UNKNOWN',source_scope='SAO02 announcement; Nov8-10 board is outside target period',market_gate='UNKNOWN'))
            for stay_offset in [0,1]:
                checkin=departure+timedelta(days=stay_offset);checkout=checkin+timedelta(days=nights)
                coverage=checkout<=horizon
                passes=departure.isoweekday() in programs['C14']['scenario_weekdays_iso'] and checkout.isoweekday() in programs['C14']['scenario_weekdays_iso']
                conditional.append(dict(candidate='C14',requested_origin_departure_date=departure.isoformat(),assumed_booked_checkin_local=checkin.isoformat(),hotel_nights=nights,checkout_local=checkout.isoformat(),booked_date_offset_days=stay_offset,
                    within_return_horizon=coverage,calendar_gate='UNKNOWN_HORIZON_COVERAGE' if not coverage else ('PASS_WEEKDAY_ONLY_SCENARIO' if passes else 'NO_EXACT_WEEKDAY_PRODUCT_IN_SCENARIO'),
                    hotel_arrival_local='UNKNOWN',late_night_admission='UNKNOWN',turnaround='UNKNOWN',clock_compatibility='NOT_EVALUATED',value_type='SCENARIO_NOT_DECEMBER_SCHEDULE'))
    write_csv(out/'c14_real_calendar_requests.csv',c14);write_csv(out/'c14_conditional_stay_dates.csv',conditional)
    write_csv(out/'physical_legs.csv',all_legs);write_csv(out/'resource_checks.csv',resources)
    # Invert a residual funding gap. No demand/capture calibration is performed.
    money=[]
    for candidate,gap,fare,expense in itertools.product(contract['candidates'],s['residual_funding_gap_rub'],s['symmetric_oneway_net_fares_rub'],s['per_journey_variable_expense_rub']):
        q=inverse(gap,fare,expense);positive_margin=fare-expense
        money.append(dict(candidate=candidate,residual_funding_gap_rub=gap,net_fare_rub_per_oneway_journey=fare,variable_cost_rub_per_oneway_journey=expense,
            comparison_unit='one paired outward/return cohort; gap must cover all allocated costs across both dates, not weekly forecast',
            required_paid_journeys_each_direction=q,total_oneway_journeys=2*q if q is not None else '',roundtrip_customers=q if q is not None else '',
            physical_boardings=(4 if candidate=='C01' else 2)*q if q is not None else '',required_ticket_revenue_rub=2*q*fare if q is not None else '',
            contribution_at_threshold_rub=2*q*positive_margin-gap if q is not None else '',contribution_one_customer_below_rub=2*(q-1)*positive_margin-gap if q else '',
            nominal_payload_scenario=100,optimistic_nominal_cap_gate='UNKNOWN_MARGIN' if q is None else ('EXCEEDS_NOMINAL_CAP' if q>100 else 'WITHIN_NOMINAL_UPPER_BOUND'),
            actual_residual_seats='UNKNOWN',actual_funding_gap='UNKNOWN',actual_net_fare='UNKNOWN',market_demand='UNKNOWN',evaluation_scope='ILLUSTRATIVE_THRESHOLD_NOT_FORECAST'))
    write_csv(out/'conditional_thresholds.csv',money)
    # Boundary fixtures demonstrate shared seat consumption; neither local load is a forecast.
    fixture_legs=[{'leg_id':x,'nominal_seats':100} for x in ['FIRST','SECOND']];capacity=[]
    for transfer in [20,25]:
        result=seat_allocation(fixture_legs,[{'leg_ids':['FIRST'],'quantity':80,'net_fare':5000},{'leg_ids':['SECOND'],'quantity':80,'net_fare':5000},{'leg_ids':['FIRST','SECOND'],'quantity':transfer,'net_fare':8000}])
        capacity.append(dict(fixture='LOCAL_PLUS_TRANSFER',locals_each_leg=80,transfer_journeys=transfer,first_leg_load=result['loads']['FIRST'],second_leg_load=result['loads']['SECOND'],nominal_seats_each_leg=100,ticket_revenue_once_per_journey=result['ticket_revenue_once_per_journey'],capacity_gate='FAIL' if result['exceeded_leg_ids'] else 'PASS',value_type='MECHANICAL_FIXTURE_NOT_MARKET'))
    write_csv(out/'capacity_allocation_fixtures.csv',capacity)
    replacement=[dict(state='KEEP',incremental_vs_keep='0 by definition',donor_id='UNKNOWN',actual_contribution_rub='',status='NOT_EVALUATED'),
        dict(state='REPLACE',incremental_vs_keep='new avoidable contribution - donor avoidable contribution - switching cost + retained-network delta - fixed-cost delta',donor_id='UNKNOWN',actual_contribution_rub='',status='NOT_EVALUATED'),
        dict(state='CANCEL_WITHOUT_REPLACEMENT',incremental_vs_keep='- donor avoidable contribution - cancellation obligations + retained-network delta - fixed-cost delta',donor_id='UNKNOWN',actual_contribution_rub='',status='NOT_EVALUATED')]
    write_csv(out/'replacement_states.csv',replacement)
    gates=[dict(candidate=c,arithmetic='CHECKED_SEPARATELY',published_calendar='UNKNOWN' if c!='C07' else 'SCOPED_TIMETABLE_REFERENCE',scenario_resource_screen='CONDITIONAL_ONLY',real_resource='UNKNOWN',conditional_economics='THRESHOLDS_ONLY',market='NOT_ACCEPTED',launch='NOT_EVALUATED',train_holdout='NO_LABELS',donor='UNKNOWN') for c in contract['candidates']]
    write_csv(out/'acceptance.csv',gates)
    return {'physical_leg_rows':len(all_legs),'connection_rows':len(connections),'dated_cohorts':len(cohorts),'c14_real_requests':len(c14),'c14_conditional_requests':len(conditional),'threshold_rows':len(money),'resource_checks':len(resources),'market_acceptance':'NONE','full_network_case_solution':'NOT_THIS_EXPERIMENT'}

def main():
    contract=json.loads((ROOT/'contract.json').read_text());programs=json.loads((ROOT/'scenario_programs.json').read_text());manifest=json.loads((ROOT/'input_manifest.json').read_text())
    inputs={p:sha(ROOT/p) for p in ['contract.json','scenario_programs.json','input_manifest.json','scripts/evaluate.py']}
    snapshots=ROOT/'snapshots';snapshots.mkdir(exist_ok=True)
    for p,h in inputs.items():
        target=snapshots/(h+'.blob')
        if target.exists():assert sha(target)==h
        else:target.write_bytes((ROOT/p).read_bytes())
    run_id=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16];out=ROOT/'runs'/run_id
    event={'attempt_utc':datetime.now(UTC).isoformat(),'run_id':run_id,'input_hashes':inputs,'input_set_id':manifest['input_set_id']}
    try:
        if out.exists():
            stored=json.loads((out/'output_manifest.json').read_text())
            for r in stored['files']:assert sha(out/r['path'])==r['sha256']
            event['status']='REPLAY_OUTPUT_HASHES_MATCH';print(json.dumps(event));return
        out.mkdir(parents=True);summary=evaluate(out,contract,programs,manifest)
        write_json(out/'summary.json',summary)
        write_json(out/'output_manifest.json',{'run_id':run_id,'input_hashes':inputs,'files':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()]})
        event.update(status='COMPLETE_SCOPED',summary=summary);print(json.dumps(event))
    except Exception as e:
        event.update(status='FAILED',error_type=type(e).__name__,error=str(e));raise
    finally:
        with (ROOT/'attempts.jsonl').open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
if __name__=='__main__':main()
