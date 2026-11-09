#!/usr/bin/env python3
"""Join advertised dated flights to explicit booked hotel dates; no prices imputed."""
from pathlib import Path
from datetime import datetime,date,time,timedelta,timezone
from zoneinfo import ZoneInfo
import csv,json,hashlib,itertools
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'inputs/alternative_fa39de4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(p.open()))
def write(p,data):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def clock_minutes(clock):
    t=time.fromisoformat(clock);return t.hour*60+t.minute
def main():
    manifest_path=ROOT/'input_sets/phase2-frozen-002.json';manifest=json.loads(manifest_path.read_text());contract=json.loads((ROOT/'contract.json').read_text())
    assert sha(ROOT/'contract.json')==manifest['contract_sha256']
    for r in manifest['inputs']:assert sha(ROOT/r['stored_path'])==r['sha256']
    input_hashes={'manifest':sha(manifest_path),'contract':sha(ROOT/'contract.json'),'script':sha(Path(__file__))}
    run_id=hashlib.sha256(json.dumps(input_hashes,sort_keys=True).encode()).hexdigest()[:16];out=ROOT/'c14_products'/run_id
    attempt={'utc':datetime.now(timezone.utc).isoformat(),'module':'C14_PRODUCT','run_id':run_id,'input_hashes':input_hashes,'input_set_id':manifest['input_set_id']}
    try:
        if out.exists():
            frozen=json.loads((out/'output_manifest.json').read_text())
            for r in frozen['files']:assert sha(out/r['path'])==r['sha256']
            attempt['status']='REPLAY_HASH_MATCH';print(json.dumps(attempt));return
        out.mkdir(parents=True)
        flights=rows(DATA/'normalized/dated_flights.csv');rules={r['rule_id']:r for r in rows(DATA/'normalized/flight_rules.csv')};hotels=rows(DATA/'stay_offer/stay_rules.csv');offers={r['property_id']:r for r in rows(DATA/'stay_offer/public_offers.csv')}
        start=date.fromisoformat(contract['period']['start']);end=date.fromisoformat(contract['period']['end']);horizon=date.fromisoformat(contract['period']['product_return_horizon'])
        departures=[r for r in flights if r['origin_iata']=='KVX' and start<=date.fromisoformat(r['departure_local_date'])<=end]
        returns={r['departure_local_date']:r for r in flights if r['origin_iata']=='MRV'}
        checks=[]
        for f in flights:
            rule=rules[f['rule_id']];day=date.fromisoformat(f['departure_local_date']);dep=datetime.fromisoformat(f['departure_local_datetime']);arr=datetime.fromisoformat(f['arrival_local_datetime'])
            assert date.fromisoformat(rule['valid_from'])<=day<=date.fromisoformat(rule['valid_to']) and day.isoweekday() in {int(x) for x in rule['weekdays_iso'].split(';')}
            assert rule['clock_basis']=='AIRPORT_PUBLISHED_LOCAL_TIME'
            assert dep.astimezone(timezone.utc).isoformat()==f['departure_utc'] and arr.astimezone(timezone.utc).isoformat()==f['arrival_utc']
            assert int((arr-dep).total_seconds()/60)==int(f['planned_duration_minutes'])
            assert (arr.date()-dep.date()).days==int(f['arrival_day_offset'])
        assert len({r['instance_id'] for r in flights})==len(flights)==12
        keys=rows(DATA/'reference/airport_keys.csv')
        assert all(ZoneInfo(r['used_iana_timezone']).utcoffset(datetime(2026,12,7))==ZoneInfo(r['published_iana_timezone']).utcoffset(datetime(2026,12,7)) for r in keys)
        products=[]
        for outbound,hotel,nights,stay_basis in itertools.product(departures,hotels,[7,10,14],['BOOK_DEPARTURE_DATE_REQUIRES_LATE_ADMISSION','BOOK_AIRPORT_ARRIVAL_DATE_REGULAR_CHECKIN']):
            checkin=date.fromisoformat(outbound['departure_local_date'] if stay_basis.startswith('BOOK_DEPARTURE') else outbound['arrival_local_date']);checkout=checkin+timedelta(days=nights);back=returns.get(checkout.isoformat())
            offer=offers[hotel['property_id']];horizon_known=checkout<=horizon
            calendar='RETURN_RULE_PRESENT' if back else 'NO_EXACT_RETURN_IN_CAPTURED_RULES'
            if not horizon_known:calendar='UNKNOWN_HORIZON_COVERAGE'
            # A property clock with unknown IANA is never silently assigned the airport zone.
            budget=clock_minutes(back['departure_local_datetime'][11:16])-clock_minutes(hotel['checkout_by']) if back else None
            arrival_clock=clock_minutes(outbound['arrival_local_datetime'][11:16]);until_checkin=clock_minutes(hotel['checkin_from'])-arrival_clock if stay_basis.startswith('BOOK_AIRPORT') else None
            products.append(dict(product_request_id=f"{outbound['instance_id']}:{hotel['property_id']}:{nights}:{stay_basis}",outbound_instance_id=outbound['instance_id'],return_instance_id=back['instance_id'] if back else '',
                origin='KVX',destination='MRV',target_endpoint_product='KVX_MRV_RETURN_WITH_NAMED_PROPERTY',outbound_departure_local=outbound['departure_local_datetime'],outbound_arrival_local=outbound['arrival_local_datetime'],
                property_id=hotel['property_id'],stay_basis=stay_basis,booked_checkin_local_date=checkin.isoformat(),booked_checkout_local_date=checkout.isoformat(),hotel_nights=nights,
                return_departure_local=back['departure_local_datetime'] if back else '',return_home_arrival_local=back['arrival_local_datetime'] if back else '',calendar_gate=calendar,
                property_iana=hotel['timezone_iana'],date_alignment='BOOKED_DATE_ASSUMPTION; airport arrival day is not observed hotel admission day',
                conditional_return_ground_plus_airport_buffer_budget_minutes=budget,conditional_airport_arrival_to_regular_checkin_clock_gap_minutes=until_checkin,
                conditional_clock_basis='SCENARIO_SAME_CIVIL_CLOCK_AS_MRV; property IANA UNKNOWN',hotel_checkin_clock=hotel['checkin_from'],hotel_checkout_clock=hotel['checkout_by'],
                hotel_min_stay_gate='UNKNOWN',hotel_admission_gate='UNKNOWN',hotel_late_rule=hotel['late_arrival_rule'],transfer_duration_minutes='',transfer_duration_status='UNKNOWN',
                tariff_calendar_contains_stay=date.fromisoformat(offer['valid_from'])<=checkin and checkout<=date.fromisoformat(offer['valid_through']),
                public_property_tariff=offer['tariff_amount_per_person'],public_tariff_unit=offer['price_unit'],billing_days_for_requested_nights='UNKNOWN',total_stay_price='',airfare_quote='',realised_airline_revenue='',
                inventory_gate='UNKNOWN',operating_carrier_actual='UNKNOWN',marketing_carrier=rules[outbound['rule_id']]['marketing_carrier_iata'],nonstop_status='UNKNOWN',full_product_gate='UNKNOWN',value_type='DERIVED_ADVERTISED_CALENDAR_WITH_EXPLICIT_BOOKED_DATE_SCENARIOS'))
        write(out/'flight_hotel_calendar.csv',products)
        # Calendar coverage of all seven requested departure dates, separately from physical execution.
        coverage=[]
        for offset in range(7):
            day=start+timedelta(days=offset);found=[r for r in departures if r['departure_local_date']==day.isoformat()]
            coverage.append(dict(date=day.isoformat(),route='KVX-MRV',captured_advertised_departures=len(found),schedule_scope='THIS_AIRPORT_CAPTURE_ONLY',observed_execution='UNKNOWN',inventory='UNKNOWN',date_status='RULE_PRESENT' if found else 'NO_RULE_IN_CAPTURE; NOT_ZERO_MARKET_DEMAND',source_sha256=next(iter(rules.values()))['source_sha256']))
        write(out/'departure_date_coverage.csv',coverage)
        ground=rows(DATA/'ground_transfer/ground_alternatives.csv');rail=[]
        for f in departures:
            for station in ['rail_essentuki','rail_kislovodsk']:
                matched=[r for r in ground if r['origin_place_id']=='rail_mineralnye_vody' and r['destination_place_id']==station and r['service_date']==f['arrival_local_date']]
                rail.append(dict(outbound_instance_id=f['instance_id'],airport_arrival_date=f['arrival_local_date'],station_destination=station,matched_exact_date_rows=len(matched),date_coverage='EXACT_DATE_ROWS_PRESENT' if matched else 'UNKNOWN_DATE_COVERAGE',airport_to_station_service='UNKNOWN',station_to_property_service='UNKNOWN',complete_ground_connection='UNKNOWN',no_weekday_fill=True))
        write(out/'ground_date_join.csv',rail)
        # Same-date advertised airport turn interval; no claim of a single aircraft or lawful turn.
        turns=[]
        for f in [r for r in flights if r['origin_iata']=='MRV']:
            next_row=next((r for r in flights if r['origin_iata']=='KVX' and r['departure_local_date']==f['arrival_local_date']),None)
            if next_row:
                minutes=int((datetime.fromisoformat(next_row['departure_utc'])-datetime.fromisoformat(f['arrival_utc'])).total_seconds()/60)
                turns.append(dict(airport='KVX',arrival_instance_id=f['instance_id'],departure_instance_id=next_row['instance_id'],published_gap_minutes=minutes,same_aircraft='UNKNOWN',actual_operating_carrier='UNKNOWN',technical_turn_minimum='UNKNOWN',status='DERIVED_CLOCK_GAP_ONLY'))
        write(out/'advertised_turn_gaps.csv',turns)
        checks=[{'check':'twelve_instances_rule_period_weekday_utc_rollover','status':'PASS'}, {'check':'timezone_names_offsets_equal_no_property_timezone_filled','status':'PASS'},
            {'check':'every_night_count_from_booked_dates','status':'PASS' if all((date.fromisoformat(r['booked_checkout_local_date'])-date.fromisoformat(r['booked_checkin_local_date'])).days==r['hotel_nights'] for r in products) else 'FAIL'},
            {'check':'no_hotel_tariff_times_nights_imputation','status':'PASS' if all(r['billing_days_for_requested_nights']=='UNKNOWN' and r['total_stay_price']=='' for r in products) else 'FAIL'},
            {'check':'no_full_product_or_market_acceptance','status':'PASS' if all(r['full_product_gate']=='UNKNOWN' and r['realised_airline_revenue']=='' for r in products) else 'FAIL'},
            {'check':'ground_actual_arrival_dates_not_filled','status':'PASS' if all(r['date_coverage']=='UNKNOWN_DATE_COVERAGE' for r in rail) else 'FAIL'}]
        assert all(r['status']=='PASS' for r in checks)
        summary={'input_set_id':manifest['input_set_id'],'outbound_dates':[r['departure_local_date'] for r in departures],'planned_instances':len(flights),'flight_hotel_date_requests':len(products),'matched_return_calendar_rows':sum(r['calendar_gate']=='RETURN_RULE_PRESENT' for r in products),'full_products_accepted':0,'full_products_status':'UNKNOWN_NOT_ZERO_DEMAND','airport_turn_gaps_minutes':sorted(set(r['published_gap_minutes'] for r in turns)),'source_day_change':'Mon/Thu in current airport capture, versus older Mon/Fri announcement','independent_critic':'PENDING','train_holdout':'NO_LABELS'}
        for name,obj in [('checks.json',checks),('summary.json',summary)]: (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
        (out/'output_manifest.json').write_text(json.dumps({'run_id':run_id,'input_hashes':input_hashes,'files':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()]},indent=2)+'\n')
        attempt.update(status='COMPLETE_SCOPED',summary=summary);print(json.dumps(attempt,ensure_ascii=False))
    except Exception as e:
        attempt.update(status='FAILED',error_type=type(e).__name__,error=str(e));raise
    finally:
        with (ROOT/'module_attempts.jsonl').open('a') as f:f.write(json.dumps(attempt,ensure_ascii=False)+'\n')
if __name__=='__main__':main()
