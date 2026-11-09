#!/usr/bin/env python3
"""Verify the separately frozen C14 union, its component lineage and nullable roles."""
import csv
import datetime as dt
import io
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import review_core_integration as c

SHA='d8d8e72a96ef175eb4fb0e14b585b930c42f8249'
ADD=c.ROOT+'c14_addendum_v1/'
ALT='fa39de413ac00a93b0214840aae2e7916332cef5'
AR='context/16_agent_research/alternative/product_probe_v1/'
OUT=Path(__file__).resolve().parent/'reviews'/'core_c14_d8d8e72'

def get(path):
    return c.get(ADD+path,SHA,False)

def table(path):
    return list(csv.DictReader(io.StringIO(get(path).decode())))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mb=get('output_manifest.json');m=json.loads(mb)
    c.equal('ADDENDUM_MANIFEST_HASH',c.digest(mb),'a5bf7463e440fd99edbebe3c5710e7e879abe4907b43d3d3e9676cc290f759d2')
    for r in m['frozen_inputs']:
        b=get(r['path']);source=c.get(r['source_path'],r['source_commit'],False)
        c.equal('ADDENDUM_FROZEN_HASH',c.digest(b),r['sha256'],r['path'])
        c.equal('ADDENDUM_SOURCE_COPY',c.digest(b),c.digest(source),r['path'])
    for r in m['files']:
        b=get(r['path']);c.equal('ADDENDUM_OUTPUT_HASH',c.digest(b),r['sha256'],r['path'])
        c.equal('ADDENDUM_OUTPUT_BYTES',len(b),r['size_bytes'],r['path'])
    base_manifest=c.js('operating/output_manifest.json')
    for r in base_manifest['files']:
        c.equal('BASE_UNMODIFIED',c.digest(c.get(c.ROOT+r['path'],SHA,False)),r['sha256'],r['path'])
    base_rules=c.table('operating/service_rules.csv');base_instances=c.table('operating/dated_instances.csv')
    rules=table('outputs/service_rules.csv');instances=table('outputs/dated_instances.csv')
    union_rules=table('outputs/operating_service_rules_union.csv');union_instances=table('outputs/operating_dated_instances_union.csv')
    tz=table('outputs/timezone_keys_union.csv');tzmap={r['timezone_key_version']:r for r in tz}
    c.equal('TIMEZONE_UNIQUE_KEYS',len(tzmap),len(tz))
    c.equal('UNION_RULE_COUNT',len(union_rules),len(base_rules)+len(rules))
    c.equal('UNION_INSTANCE_COUNT',len(union_instances),len(base_instances)+len(instances))
    c.equal('UNIQUE_INSTANCE_IDS',len({r['instance_id']for r in union_instances}),24)
    c.equal('UNIQUE_RULE_IDS',len({r['service_rule_id']for r in union_rules}),13)
    by_rule={r['service_rule_id']:r for r in union_rules}
    for original,union,idcol in [(base_rules,union_rules,'service_rule_id'),(base_instances,union_instances,'instance_id')]:
        lookup={r[idcol]:r for r in union}
        for r in original:
            c.equal('BASE_COMPONENT_NOT_PROMOTED',{k:lookup[r[idcol]][k]for k in r},r,r[idcol])
            c.equal('BASE_COMPONENT_INPUT_SET',lookup[r[idcol]]['component_input_set_id'],base_manifest['input_set_id'],r[idcol])
    alt_rules={r['rule_id']:r for r in csv.DictReader(io.StringIO(c.get(AR+'normalized/flight_rules.csv',ALT,False).decode()))}
    alt_instances={r['instance_id']:r for r in csv.DictReader(io.StringIO(c.get(AR+'normalized/dated_flights.csv',ALT,False).decode()))}
    for r in rules:
        source=alt_rules[r['rule_id']]
        for out_col,in_col in [('origin_iata','origin_iata'),('destination_iata','destination_iata'),('departure_local','departure_local_time'),('arrival_local','arrival_local_time'),('weekdays_iso','weekdays_iso'),('arrival_day_offset','arrival_day_offset'),('source_flight_label','flight_number')]:
            c.equal('C14_RULE_LITERAL',r[out_col],source[in_col],r['rule_id']+':'+out_col)
        c.equal('C14_LEGAL_ROLES_UNKNOWN',[r['operating_carrier_id'],r['marketing_carrier_id']],['',''])
        c.equal('C14_ASSOCIATION_RETAINED',r['source_carrier_association'],source['operating_carrier_id'])
        c.equal('C14_ROLLOVER_STILL_DERIVED',r['day_offset_value_status'],'DERIVED')
    for r in instances:
        source=alt_instances[r['instance_id']]
        for out_col,in_col in [('departure_date_local','departure_local_date'),('arrival_date_local','arrival_local_date'),('departure_utc','departure_utc'),('arrival_utc','arrival_utc'),('elapsed_minutes','planned_duration_minutes')]:
            c.equal('C14_INSTANCE_NOT_CHANGED',r[out_col],source[in_col],r['instance_id']+':'+out_col)
        c.equal('C14_PERFORMANCE_NOT_FILLED',[r['performed_status'],r['inventory_status'],r['operating_carrier_id'],r['marketing_carrier_id']],['UNKNOWN','UNKNOWN','',''])
    for r in union_rules+union_instances:
        c.equal('UNION_LEGAL_ROLES_NULL',[r['operating_carrier_id'],r['marketing_carrier_id']],['',''])
        for direction in ['origin','destination']:
            key=r[direction+'_timezone_key_version']
            c.equal('TZ_FOREIGN_KEY_EXISTS',key in tzmap,True,key)
            if key in tzmap:
                c.equal('TZ_FOREIGN_KEY_ZONE',r[direction+'_iana'],tzmap[key]['iana_timezone'],key)
                offset=int(dt.datetime(2026,12,7,12,tzinfo=ZoneInfo(r[direction+'_iana'])).utcoffset().total_seconds()/60)
                c.equal('TZ_OFFSET',offset,int(tzmap[key]['utc_offset_minutes']),key)
    for r in union_instances:
        expected='PRIMARY_DEPARTURE_07_13'if r['departure_date_local']<='2026-12-13'else'LATER_CONTEXT_14_27'
        c.equal('WEEK_MEMBERSHIP',r['departure_window_membership'],expected,r['instance_id'])
        c.equal('RULE_FOREIGN_KEY_EXISTS',r['service_rule_id']in by_rule,True,r['instance_id'])
        if r['origin_iata']=='KVX'or r['destination_iata']=='KVX':
            c.equal('C14_COMPONENT_INPUT_SET',r['component_input_set_id'],m['input_set_id'])
            c.equal('NO_FRIDAY_RECURRENCE',dt.date.fromisoformat(r['departure_date_local']).isoweekday()in [1,4],True,r['instance_id'])
    reconciliation=table('outputs/timezone_reconciliation.csv')
    for r in reconciliation:
        for date in ['2026-12-07','2026-12-27']:
            day=dt.datetime.fromisoformat(date+'T12:00')
            c.equal('ALIAS_OFFSET_COMPATIBILITY',day.replace(tzinfo=ZoneInfo(r['source_iana'])).utcoffset(),day.replace(tzinfo=ZoneInfo(r['core_iana'])).utcoffset(),r['iata'])
    conflicts=table('outputs/source_conflicts.csv')
    c.equal('SOURCE_VERSIONS_NOT_MERGED',[(r['older_days_reported'],r['current_days'])for r in conflicts],[('Monday;Friday','Monday;Thursday')])
    result=dict(input_git_sha=SHA,alternative_sha=ALT,core_base_sha=c.SHA,input_set_id=m['input_set_id'],frozen_inputs_checked=len(m['frozen_inputs']),output_hashes_checked=len(m['files']),base_outputs_preserved=len(base_manifest['files']),union_rule_rows=len(union_rules),union_dated_rows=len(union_instances),union_first_week_departures=sum(r['departure_window_membership']=='PRIMARY_DEPARTURE_07_13'for r in union_instances),timezone_keys=len(tz),differences=c.differences,acceptance='PASS_COMPONENT_LINEAGE_AND_CALENDAR_UNION_ONLY'if not c.differences else'CHANGES',airport_primary_source_recheck='See independent fa39 raw6cell/12calendar review at reviews/input_set002',inherited_quarantine='Required: core b264 quarantine and safe OMS overlay; union is not a bypass',hotel_product='NOT_EVALUATED_IN_THIS_OPERATING_UNION',market_economics='NOT_ACCEPTED')
    (OUT/'input_manifest.json').write_text(json.dumps(dict(inputs=c.receipts),indent=2)+'\n')
    (OUT/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    print(json.dumps(result,ensure_ascii=False,default=str));assert not c.differences

if __name__=='__main__':main()
