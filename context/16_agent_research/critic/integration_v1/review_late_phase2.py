#!/usr/bin/env python3
"""Scoped late adapters, source-gate joins and conditional calendar-flex check."""
import csv
import datetime as dt
import io
import json
import review_input_set002 as c

H='6ed8788882e7b4d07044b4f6e686ff71eadd8ac5'
E='ef365ac2a936117e5b3bb12ea99c816d7b1a101c'
HR=c.HR;AR=c.AR
OUT=c.BASE/'reviews'/'late_phase2'

def rows(sha,path):return list(csv.DictReader(io.StringIO(c.capture(sha,path).decode())))
def obj(sha,path):return json.loads(c.capture(sha,path))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inputs=obj(H,HR+'input_sets/phase2-frozen-003.json')
    for r in inputs['inputs']:
        source=c.capture(r['source_git_sha'],r['source_path']);stored=c.capture(H,HR+r['stored_path'])
        c.equal('003SOURCEHASH',c.digest(source),r['source_sha256'],r['input_id'])
        c.equal('003STOREDHASH',c.digest(stored),r['stored_sha256'],r['input_id'])
        if r['transform']=='identity':c.equal('003IDENTITY',c.digest(stored),c.digest(source))
        else:
            selected=[r for r in csv.DictReader(io.StringIO(source.decode()))if r['iata']in {'KVX','MRV','NJC','UFA','SVX','OMS','KJA'}]
            c.equal('003SEVENAIRPORTFILTER',list(csv.DictReader(io.StringIO(stored.decode()))),selected)
    join='operating_join/126bccd230436e9f/';flex='c14_calendar_flex/13bad5060a24f3ce/'
    jm=obj(H,HR+join+'manifest.json');fm=obj(H,HR+flex+'manifest.json')
    for folder,m in [(join,jm),(flex,fm)]:
        for r in m['files']:c.equal('LATE_OUTPUT_HASH',c.digest(c.capture(H,HR+folder+r['path'])),r['sha256'],folder+r['path'])
    for file,expected in [('input_sets/phase2-frozen-003.json',jm['inputs']['input_manifest_sha256']),('scripts/core_operating_join.py',jm['inputs']['script_sha256']),('scripts/c14_calendar_flex.py',fm['inputs']['script']),('c14_products/3906edd033f75bc6/flight_hotel_calendar.csv',fm['inputs']['product_csv']),('inputs/alternative_fa39de4/normalized/dated_flights.csv',fm['inputs']['dated_flights'])]:
        c.equal('LATE_INPUT_HASH',c.digest(c.capture(H,HR+file)),expected,file)
    dated=rows(H,HR+join+'dated_source_acceptance.csv')
    source_dated={r['instance_id']:r for r in rows(H,HR+'inputs/core_b264780/dated_instances.csv')}
    for r in dated:
        c.equal('JOIN_SOURCE_FIELDS_PRESERVED',r,{k:source_dated[r['instance_id']][k]for k in r},r['instance_id'])
    gates=rows(H,HR+join+'service_rule_gates.csv');source_rules={r['service_rule_id']:r for r in rows(H,HR+'inputs/core_b264780/service_rules.csv')}
    for r in gates:c.equal('RULE_GATES_PRESERVED',r,{k:source_rules[r['service_rule_id']][k]for k in r})
    keys=rows(H,HR+join+'airport_key_join.csv')
    stored_keys={r['iata']:r for r in rows(H,HR+'inputs/core_b264780/airport_keys.csv')}
    previous_keys={r['iata']:r for r in rows(H,HR+'runs/c26661067277af20/airport_keys.csv')}
    for r in keys:
        c.equal('AIRPORT_ID_ZONE_MATCH_FLAGS',[r['id_matches'],r['iana_matches'],r['quarantine_reason']],['True','True',''])
        source=stored_keys[r['iata']];previous=previous_keys[r['iata']]
        c.equal('AIRPORT_JOIN_CONTENT',[r['experiment_airport_id'],r['core_airport_id'],r['experiment_iana'],r['core_iana'],r['core_airport_key_version']],[previous['airport_id'],source['airport_id'],previous['iana'],source['iana_timezone'],source['airport_key_version']])
    req=rows(H,HR+join+'physical_requirement_coverage_join.csv')
    source_req={r['physical_leg_key']:r for r in rows(H,HR+'inputs/core_b264780/physical_leg_requirements.csv')}
    coverage={(r['experiment_id'],r['origin_iata'],r['destination_iata']):r for r in rows(H,HR+'inputs/core_b264780/coverage.csv')}
    for r in req:
        c.equal('REQUIREMENTS_PRESERVED',{k:r[k]for k in source_req[r['physical_leg_key']]},source_req[r['physical_leg_key']])
        cov=coverage[r['experiment_id'],r['origin_iata'],r['destination_iata']]
        for k in ['retained_rule_count','retained_dated_departures_07_27','complete_calendar_instances','absence_of_service_claim']:c.equal('COVERAGE_JOIN',r[k],cov[k])
    source_products={r['product_request_id']:r for r in rows(H,HR+'c14_products/3906edd033f75bc6/flight_hotel_calendar.csv')}
    returns=sorted([r for r in rows(H,HR+'inputs/alternative_fa39de4/normalized/dated_flights.csv')if r['origin_iata']=='MRV'],key=lambda r:r['departure_local_date'])
    flexible=rows(H,HR+flex+'later_return_date_tradeoff.csv')
    c.equal('FLEX_GRID_COUNT',len(flexible),len(source_products))
    c.equal('FLEX_GRID_IDS',{r['product_request_id']for r in flexible},set(source_products))
    for r in flexible:
        source=source_products[r['product_request_id']];wanted=source['booked_checkout_local_date']
        c.equal('FLEX_SOURCE_PRODUCT_FIELDS',[r['property_id'],r['stay_basis'],r['original_hotel_nights'],r['original_checkout_local_date'],r['exact_return_gate']],[source['property_id'],source['stay_basis'],source['hotel_nights'],wanted,source['calendar_gate']])
        future=[f for f in returns if f['departure_local_date']>=wanted];chosen=future[0]if future else None
        extra=(dt.date.fromisoformat(chosen['departure_local_date'])-dt.date.fromisoformat(wanted)).days if chosen else None
        c.equal('FLEX_EARLIEST_CAPTURED_RETURN',[r['next_captured_return_id'],r['next_captured_return_date']],[chosen['instance_id'],chosen['departure_local_date']]if chosen else['',''])
        c.equal('FLEX_EXTRA_NIGHTS',r['additional_booked_nights'],str(extra)if extra is not None else'')
        c.equal('FLEX_REVISED_NIGHTS',r['revised_booked_nights'],str(int(source['hotel_nights'])+extra)if extra is not None else'')
        c.equal('FLEX_NOT_CONFIRMED',[r[k]for k in ['hotel_extended_inventory','late_admission','extra_hotel_charge','extra_airfare','ground_compatibility','flight_inventory','customer_acceptance','full_product_acceptance']],['UNKNOWN']*8)
    eb=c.capture(E,AR+'dataset_manifest.json');em=json.loads(eb)
    c.equal('EF_MANIFEST',c.digest(eb),'659e08565b9175289e5d117aee596967629620a08ca13e7a890730a51c061117')
    entries={r['path']:r for r in em['public_files']}
    selected=['normalized/flight_rules_v2.csv','normalized/flight_rules.csv','normalized/dated_flights.csv','normalized/conditional_stay_calendars.csv']
    for p in selected:c.equal('EF_SELECTED_HASH',c.digest(c.capture(E,AR+p)),entries[p]['sha256'],p)
    c.equal('EF_DATED_FLIGHTS_UNCHANGED',c.digest(c.capture(E,AR+'normalized/dated_flights.csv')),c.digest(c.capture(c.ALT,AR+'normalized/dated_flights.csv')))
    c.equal('EF_CONDITIONAL_CASES_UNCHANGED',c.digest(c.capture(E,AR+'normalized/conditional_stay_calendars.csv')),c.digest(c.capture('f92f21e143c923c79656e15776e6f66732f70f50',AR+'normalized/conditional_stay_calendars.csv')))
    v2=rows(E,AR+'normalized/flight_rules_v2.csv');old={r['rule_id']:r for r in rows(E,AR+'normalized/flight_rules.csv')}
    for r in v2:
        source=old[r['rule_id']]
        c.equal('EF_LEGAL_ROLES_CLEARED',[r['operating_carrier_id'],r['operating_carrier_iata'],r['marketing_carrier_iata']],['','',''])
        c.equal('EF_COMPONENT_TYPES',[r['value_status'],r['day_offset_value_status'],r['timezone_value_status']],['OBSERVED','DERIVED','DERIVED'])
        for k in ['origin_iata','destination_iata','departure_local_time','arrival_local_time','valid_from','valid_to','weekdays_iso','arrival_day_offset']:c.equal('EF_CLOCK_RULE_UNCHANGED',r[k],source[k])
    c.equal('EF_OLD_FLIGHT_BYTES',c.digest(c.capture(E,AR+'normalized/flight_rules.csv')),c.digest(c.capture(c.ALT,AR+'normalized/flight_rules.csv')))
    result=dict(hypotheses_sha=H,alternative_sha=E,core003_inputs_checked=len(inputs['inputs']),operating_join_rows=dict(airport_keys=len(keys),physical_requirements=len(req),rule_gates=len(gates),dated_source=len(dated)),arrival_utc_still_unknown=sum(not r['arrival_utc']for r in dated),flex_rows=len(flexible),positive_extensions=sum(bool(r['additional_booked_nights'])and int(r['additional_booked_nights'])>0 for r in flexible),extension_nights=sorted({int(r['additional_booked_nights'])for r in flexible if r['additional_booked_nights']and int(r['additional_booked_nights'])>0}),beyond_capture_unknown=sum(not r['next_captured_return_id']for r in flexible),ef_typed_adapter_rows=len(v2),ef_selected_artifacts_checked=len(selected),differences=c.differences,acceptance='PASS_LATE_JOIN_AND_FLEX_ARITHMETIC_ONLY'if not c.differences else'CHANGES',flex_scope='Changes requestednights only underexplicitcustomerSCENARIO; not acceptedoriginal7/10/14product, billabledays or preference',full_product='UNKNOWN',market_launch='NOT_ACCEPTED',not_reviewed='EFoptionalC10 semantictruth andnewreceptionPDF extraction; core505C07conditionalreconciliation outside earlier930audit')
    (OUT/'input_manifest.json').write_text(json.dumps(dict(inputs=c.receipts),indent=2)+'\n')
    (OUT/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    print(json.dumps(result,ensure_ascii=False,default=str));assert not c.differences

if __name__=='__main__':main()
