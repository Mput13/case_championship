#!/usr/bin/env python3
"""Conditional local-hotel calendars from an immutable published input commit.

Two explicit reservation-date anchors, never a confirmed booked stay. Transfers
remain unknown; compute their necessary time budgets instead of imputing time.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
PREFIX='context/16_agent_research/alternative/product_probe_v1/'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-commit',required=True)
    ap.add_argument('--air-policy-sha256',required=True);args=ap.parse_args()
    sha=subprocess.check_output(['git','rev-parse',args.input_commit+'^{commit}'],text=True).strip()
    inputs=[]
    def read(rel):
        data=subprocess.check_output(['git','show',sha+':'+PREFIX+rel])
        inputs.append({'path':rel,'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)})
        return list(csv.DictReader(io.StringIO(data.decode('utf-8'))))
    flights=read('normalized/dated_flights.csv');stays=read('stay_offer/stay_rules.csv')
    prices={r['property_id']:r for r in read('stay_offer/public_offers.csv')}
    transfers=read('ground_transfer/transfer_rules.csv')
    policy_path=ROOT/'air_offer/airport_buffers.csv';policy_bytes=policy_path.read_bytes()
    assert hashlib.sha256(policy_bytes).hexdigest()==args.air_policy_sha256
    policy=list(csv.DictReader(io.StringIO(policy_bytes.decode('utf-8'))))
    close=[r for r in policy if r['buffer_id']=='CHECKIN_CLOSE']
    assert len(close)==1
    checkin_close=int(close[0]['minutes_before_scheduled_departure'])
    inputs.append({'path':'air_offer/airport_buffers.csv','sha256':args.air_policy_sha256,'size_bytes':len(policy_bytes),
                   'input_scope':'New primary general policy snapshot, not a specific MRV exception confirmation'})
    outward=[r for r in flights if r['origin_iata']=='KVX' and '2026-12-07'<=r['departure_local_date']<='2026-12-13']
    reverse=[r for r in flights if r['origin_iata']=='MRV' and r['departure_local_date']<='2026-12-27']
    results=[]
    for out in outward:
        dep=dt.datetime.fromisoformat(out['departure_local_datetime']);arr=dt.datetime.fromisoformat(out['arrival_local_datetime'])
        for hotel in stays:
            hid=hotel['property_id'];price=prices[hid]
            for anchor in ['DEPARTURE_DATE_RESERVATION_SCENARIO','ARRIVAL_DATE_RESERVATION_SCENARIO']:
                start=dep.date() if anchor.startswith('DEPARTURE') else arr.date()
                standard_start=dt.datetime.combine(start,dt.time.fromisoformat(hotel['checkin_from']),tzinfo=ZoneInfo('Europe/Moscow'))
                for nights in [7,10,14]:
                    end=start+dt.timedelta(days=nights)
                    matches=[r for r in reverse if r['departure_local_date']==end.isoformat()]
                    assert len(matches)<=1
                    back=matches[0] if matches else None
                    checkout=dt.datetime.combine(end,dt.time.fromisoformat(hotel['checkout_by']),tzinfo=ZoneInfo('Europe/Moscow'))
                    budget=(dt.datetime.fromisoformat(back['departure_local_datetime'])-checkout).total_seconds()/60 if back else None
                    threshold=(standard_start-arr).total_seconds()/60
                    results.append({'product_case_id':f'C14:{out["departure_local_date"]}:{hid}:{anchor[:3]}:{nights}',
                        'candidate_id':'C14','outbound_instance_id':out['instance_id'],'return_instance_id':back['instance_id'] if back else None,
                        'source_input_commit':sha,'outbound_departure_local':dep.isoformat(),'outbound_arrival_local':arr.isoformat(),
                        'property_id':hid,'hotel_iana':'Europe/Moscow','hotel_zone_status':'CURATED_AREA_IANA; no timezone inference from flight code',
                        'reservation_date_anchor':anchor,'assumed_reservation_start_date':start.isoformat(),
                        'assumed_checkout_date':end.isoformat(),'assumed_nights':nights,'calendar_difference_nights':(end-start).days,
                        'actual_booked_checkin_date':None,'actual_booked_checkout_date':None,'booking_status':'UNKNOWN',
                        'standard_checkin_local':standard_start.isoformat(),'standard_checkout_local':checkout.isoformat(),
                        'airport_to_property_total_minutes':None,'transfer_duration_status':'UNKNOWN_EXACT_PROPERTY',
                        'minutes_from_airport_arrival_to_checkin_opening':int(threshold),
                        'checkin_opening_comparison_status':'DERIVED_CLOCK_GAP; opening time is not an arrival deadline; early arrival may wait or require paid exception',
                        'max_exit_wait_transfer_minutes_to_preserve_assumed_checkin_date_exclusive':int((dt.datetime.combine(start+dt.timedelta(days=1),dt.time(0),tzinfo=ZoneInfo('Europe/Moscow'))-arr).total_seconds()/60),
                        'date_preservation_threshold_status':'DERIVED_STRICT_UPPER_BOUND to next local midnight; does not prove reception acceptance or available transfer',
                        'arrival_date_after_reservation_start':arr.date()>start,
                        'late_next_day_acceptance_required':arr.date()>start,'provider_next_day_rule':hotel['late_arrival_rule'],
                        'early_late_rule':hotel['early_late_rule'],'minimum_stay_eligibility':hotel['minimum_stay'],
                        'captured_return_rule_same_checkout_date':bool(back),
                        'return_match_meaning':'CAPTURED_RULE_CALENDAR_MATCH_ONLY' if back else 'NO_MATCH_IN_CAPTURED_RULES; NOT_PROVEN_MARKET_INFEASIBLE',
                        'return_departure_local':back['departure_local_datetime'] if back else None,
                        'max_property_exit_transfer_airport_buffer_minutes':int(budget) if budget is not None else None,
                        'return_budget_status':'DERIVED_CONDITIONAL_LIMIT; actual exit/transfer/checkin buffer UNKNOWN',
                        'general_airport_checkin_closure_minutes':checkin_close,
                        'checkin_policy_scope':close[0]['policy_scope'],
                        'specific_flight_policy_confirmation':close[0]['specific_flight_confirmation'],
                        'max_exit_wait_transfer_queue_minutes_before_general_checkin_close':int(budget-checkin_close) if budget is not None else None,
                        'boarding_cutoff_minutes':None,'boarding_status':'DEADLINE_ON_BOARDING_PASS; numeric unknown',
                        'public_stay_offer_id':price['offer_id'],'public_tariff_rub':price['tariff_amount_per_person'],
                        'public_tariff_unit':price['price_unit'],'price_kind':price['price_kind'],
                        'billable_day_count':None,'confirmed_stay_total_rub':None,'dated_air_fare_quote_rub':None,
                        'inventory_status':'UNKNOWN','product_availability':'UNKNOWN',
                        'value_status':'SCENARIO_ANCHOR_WITH_DERIVED_CALENDAR_AND_TIME_BOUNDS',
                        'unresolved_conditions':'Booked date/late acceptance; exact transfer/time inventory; minimum stay; room inventory; billing days; air fare/seat; performed flight',
                        'recipe_version':'c14-product-calendar-v1'})
    path=ROOT/'normalized/conditional_stay_calendars.csv'
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    report={'input_commit':sha,'rows':len(results),'outbound_instances':len(outward),'properties':len(stays),
        'anchors':{},'count_actual_booked_dates_known':0,'count_actual_transfer_durations_known':0,'confirmed_product_availability_status':'UNKNOWN',
        'scope':'Conditional date and time-budget pass, not schedule/medical/commercial acceptance'}
    for anchor in sorted({r['reservation_date_anchor'] for r in results}):
        subset=[r for r in results if r['reservation_date_anchor']==anchor]
        report['anchors'][anchor]={'rows':len(subset),'captured_same_checkout_date_return_matches':sum(r['captured_return_rule_same_checkout_date'] for r in subset),
            'next_day_provider_acceptance_required':sum(r['late_next_day_acceptance_required'] for r in subset)}
    (ROOT/'normalized/product_calendar_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'frozen_product_inputs.json').write_text(json.dumps({'schema_version':'c14-frozen-product-inputs-v1','input_commit':sha,'files':inputs,
        'timezone_assumption':'Essentuki/Kislovodsk Europe/Moscow, curated territory mapping; checkin clocks provider-published',
        'scope':'Anchor scenarios do not replace UNKNOWN booked dates; complete product eligibility remains UNKNOWN'},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
