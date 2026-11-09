#!/usr/bin/env python3
"""Independent grain/lineage/quarantine/calendar checks against pinned core release."""
import csv
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
SHA = 'b264780e65a0e04afd42da811652039c70fc1def'
ROOT = 'context/16_agent_research/core/integration_v1/'
SOURCE = 'a875cdd1ecaf778f53ba06cab1c66581a7f215c6'
OUT = BASE/'reviews'/'core_b264780'
RAW = BASE/'raw'/'core_b264780'
receipts = []
differences = []

def digest(b):
    return hashlib.sha256(b).hexdigest()

def get(path, sha=SHA, rooted=True):
    full = ROOT+path if rooted else path
    b = subprocess.check_output(['git','show',sha+':'+full])
    p=RAW/sha/full;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        assert p.read_bytes()==b
    else:
        p.write_bytes(b)
    receipts.append(dict(git_sha=sha,path=full,sha256=digest(b),bytes=len(b)))
    return b

def js(path):
    return json.loads(get(path))

def table(path):
    return list(csv.DictReader(io.StringIO(get(path).decode())))

def equal(kind,a,b,key=''):
    if a!=b:
        differences.append(dict(kind=kind,key=key,actual=a,expected=b))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    im=js('input_manifest.json');om=js('operating/output_manifest.json')
    equal('INPUT_MANIFEST_HASH',digest(get('input_manifest.json')),'3c3d3b1b843fe32f91b98fa2b033706d29a6e5e41e32844f631958f97f7a0040')
    equal('OUTPUT_MANIFEST_HASH',digest(get('operating/output_manifest.json')),'be78b61e2c26d7bc5f9dd7d1cfcc05de2568a8f41c0ca0edd8757671a6113a93')
    for r in im['files']:
        b=get(r['path']);original=get(r['source_git_path'],r['source_commit'],False)
        equal('INPUT_HASH',digest(b),r['sha256'],r['path'])
        equal('SOURCE_COPY',digest(b),digest(original),r['path'])
    for r in om['files']:
        b=get(r['path']);equal('OUTPUT_HASH',digest(b),r['sha256'],r['path'])
        equal('OUTPUT_SIZE',len(b),r['size_bytes'],r['path'])
        if r['record_count'] is not None:
            equal('OUTPUT_COUNT',len(list(csv.DictReader(io.StringIO(b.decode())))),r['record_count'],r['path'])
    equal('CONTRACT_HASH',digest(get('contract.json')),om['contract_sha256'])
    original_market=table('inputs/normalized/market_observation.csv')
    market=table('operating/market_observation_v1.csv')
    equal('CM01_COUNT',len(market),len(original_market))
    equal('CM01_UNIQUE_IDS',len({r['observation_id'] for r in market}),24)
    semantic=['source_id','entity_id','metric','period_start','period_end','unit','observation_kind']
    equal('CM01_SEMANTIC_GRAIN',len({tuple(r[k] for k in semantic)for r in market}),24)
    # Compare all original fields and their values, including the two colliding legacy IDs.
    old_counter=Counter(tuple(sorted(r.items()))for r in original_market)
    restored=[]
    for r in market:
        restored.append({k:(r['legacy_observation_id'] if k=='observation_id' else r[k])for k in original_market[0]})
    equal('CM01_NO_DATA_LOSS',Counter(tuple(sorted(r.items()))for r in restored),old_counter)
    equal('CM01_LEGACY_UNIQUE',len({r['observation_id']for r in original_market}),23)

    overlay=table('operating/omsk_departure_overlay.csv')
    old_oms=table('inputs/branches/operating_evidence/normalized/omsk_outbound_week_20261207.csv')
    equal('CM02_COUNT_RETAINED',len(overlay),len(old_oms))
    equal('CM02_UNIQUE_OUTPUT',len({r['source_instance_id']for r in overlay}),98)
    held=[r for r in overlay if 'Тобольск' in r['source_next_stop_label']]
    equal('CM02_HELD_COUNT',len(held),2)
    equal('CM02_IDENTITIES_CLEARED',all(not r[k]for r in held for k in ['destination_iata','destination_airport_key','destination_iana']),True)
    equal('CM02_NOT_REPLACED_RMZ',all(r['legacy_destination_iata']=='TOX' and r['acceptance']=='QUARANTINE_AIRPORT_ALIAS'for r in held),True)
    # Origin timestamps remain useful even with destination identity held.
    for r in overlay:
        equal('OMS_DEPARTURE_UTC',dt.datetime.fromisoformat(r['departure_local']).astimezone(dt.timezone.utc).isoformat(),r['departure_utc'],r['source_instance_id'])
    key=['source_text_line','departure_date_local']
    old_by_key={tuple(r[k]for k in key):r for r in old_oms}
    for r in overlay:
        old=old_by_key[r['source_row'],r['departure_date_local']]
        equal('OMS_SOURCE_LITERAL', [r['source_next_stop_label'],r['departure_local'],r['source_flight_label']], [old['next_airport_name'],old['departure_local'],old['flight_numbers_source']],r['source_instance_id'])

    quarantine=table('operating/quarantine.csv')
    airports=table('operating/airport_keys.csv');areas=table('operating/area_keys.csv')
    aps={r['airport_key_version']:r for r in airports}
    equal('QUARANTINE_TOTAL',len(quarantine),30)
    for r in airports:
        if r['key_acceptance']=='QUARANTINE':
            equal('AIRPORT_NO_TZ_FALLBACK',[r['iana_timezone'],r['timezone_key_version']],['',''],r['airport_id'])
    for r in areas:
        if r['key_acceptance']=='QUARANTINE_TIMEZONE':
            equal('AREA_NO_TZ_FALLBACK',r['iana_timezone'],'',r['canonical_id'])
    rules=table('operating/service_rules.csv');instances=table('operating/dated_instances.csv')
    source_svx={r['source_table_row']:r for r in table('inputs/branches/operating_evidence/normalized/svx_published_schedule_rules.csv')}
    source_oms={r['source_text_line']:r for r in table('inputs/branches/operating_evidence/normalized/omsk_domestic_timetable_rows.csv')}
    def normalized_clock(s):
        hh,mm=re.search(r'(?<!\d)(\d{1,2})[:.](\d{2})(?!\d)',s).groups()
        return f'{int(hh):02d}:{mm}'
    equal('RULE_COUNT',len(rules),7)
    equal('RULE_UNIQUE',len({r['service_rule_id']for r in rules}),len(rules))
    rule_by_id={r['service_rule_id']:r for r in rules}
    for r in rules:
        if r['source_id']=='svx_schedule':
            source=source_svx[r['source_row']]
            equal('SVX_LITERAL_RULE',[r['departure_local'],r['arrival_local'],r['weekdays_iso'],r['source_flight_label'],r['source_carrier_label'],r['period_raw']], [normalized_clock(source['departure_local_raw']),normalized_clock(source['arrival_local_raw']),source['weekdays_iso'],source['flight_number_raw'],source['carrier_raw'],source['validity_raw']],r['service_rule_id'])
            equal('SVX_YEAR_NOT_IMPUTED',[r['valid_from'],r['valid_to'],r['year_status']],['','','UNKNOWN'])
        else:
            no,direction=r['source_row'].split(':');source=source_oms[no]
            dep,arr=(source['omsk_departure_local_raw'],source['onward_arrival_local_raw'])if direction=='OUT'else(source['preceding_origin_departure_local_raw'],source['omsk_arrival_local_raw'])
            equal('OMS_LITERAL_RULE',[r['departure_local'],r['arrival_local'],r['weekdays_iso'],r['source_carrier_label'],r['period_raw']],[normalized_clock(dep),normalized_clock(arr),source['weekdays_raw'].replace(',',';'),source['carrier_raw'],source['period_raw']],r['service_rule_id'])
            native_dates=re.findall(r'\d{1,2}\.\d{1,2}\.\d{2,4}',source['period_raw'])
            parsed=[]
            for literal in native_dates:
                day,month,year=literal.split('.')
                parsed.append(dt.datetime.strptime(literal,'%d.%m.%Y'if len(year)==4 else'%d.%m.%y').date().isoformat())
            equal('OMS_PERIOD',[r['valid_from'],r['valid_to']],[parsed[0],parsed[-1]],r['service_rule_id'])
        equal('LEGAL_OPERATOR_NOT_FILLED',[r['operating_carrier_id'],r['marketing_carrier_id']],['',''])
        for direction in ['origin','destination']:
            a=aps[r[direction+'_airport_key']]
            equal('TARGET_KEY_NOT_QUARANTINED',a['key_acceptance']=='QUARANTINE',False,r['service_rule_id'])
            equal('TARGET_ZONE_LINEAGE',r[direction+'_iana'],a['iana_timezone'],r['service_rule_id'])
        if r['weekday_basis'].startswith('OMS_TURN_DATE'):
            equal('REMOTE_DAY_NOT_EXPANDED',any(d['service_rule_id']==r['service_rule_id']for d in instances),False,r['service_rule_id'])
        if r['year_status']=='UNKNOWN':
            equal('SVX_UNKNOWN_YEAR_NOT_EXPANDED',any(d['service_rule_id']==r['service_rule_id']for d in instances),False,r['service_rule_id'])
    expected=set()
    for r in rules:
        if not r['valid_from'] or r['weekday_basis'] not in ['OMS_ORIGIN_WEEKDAY','ORIGIN_WEEKDAY_EXPLICIT'] or r['rule_acceptance']=='QUARANTINE':
            continue
        for n in range(21):
            day=dt.date(2026,12,7)+dt.timedelta(days=n)
            if r['valid_from']<=day.isoformat()<=r['valid_to'] and str(day.isoweekday())in r['weekdays_iso'].split(';'):
                expected.add((r['service_rule_id'],day.isoformat()))
    equal('DATED_EXPANSION_SET',{(r['service_rule_id'],r['departure_date_local'])for r in instances},expected)
    equal('DATED_COUNT',len(instances),12)
    for r in instances:
        day=r['departure_date_local'];source=rule_by_id[r['service_rule_id']]
        dep=dt.datetime.fromisoformat(day+'T'+source['departure_local']).replace(tzinfo=ZoneInfo(source['origin_iana']))
        equal('DATED_UTC',r['departure_utc'],dep.astimezone(dt.timezone.utc).isoformat(),r['instance_id'])
        equal('ARRIVAL_UNKNOWN',[r['arrival_utc'],r['arrival_date_local'],r['arrival_day_offset']],['','',''],r['instance_id'])
        equal('PRODUCT_UNKNOWN',r['product_acceptance'],'UNKNOWN',r['instance_id'])
    physical=table('operating/physical_leg_requirements.csv')
    c01=[r for r in physical if r['experiment_id']=='C01']
    equal('C01_SINGLE_LEGSET',len({r['physical_leg_set_id']for r in c01}),1)
    equal('C01_FOUR_LEGS',len(c01),4)
    equal('C01_BOTH_MODES_REFERENCE_SAME_SET',all(r['modes_referencing_same_set']=='SYNC;UNSYNC'for r in c01),True)
    for r in table('operating/coverage.csv'):
        matching=lambda d:d['origin_iata']==r['origin_iata']and d['destination_iata']==r['destination_iata']
        equal('COVERAGE_RULE_COUNT',int(r['retained_rule_count']),sum(matching(d)for d in rules))
        equal('COVERAGE_DATE_COUNT',int(r['retained_dated_departures_07_27']),sum(matching(d)for d in instances))
        equal('COVERAGE_WEEK_COUNT',int(r['retained_dated_departures_07_13']),sum(matching(d)and d['departure_date_local']<='2026-12-13'for d in instances))
        equal('NO_ABSENCE_INFERENCE',r['absence_of_service_claim'],'FALSE')
    result=dict(input_git_sha=SHA,frozen_source_sha=SOURCE,input_hashes_checked=len(im['files']),output_hashes_checked=len(om['files']),market_rows=len(market),market_semantic_ids=len({r['observation_id']for r in market}),source_oms_departures_retained=len(overlay),tobolsk_alias_rows_held=len(held),quarantine_records=len(quarantine),quarantine_reasons=dict(Counter(r['reason']for r in quarantine)),service_rules=len(rules),dated_origin_departures=len(instances),dated_departures_first_week=sum(r['departure_date_local']<='2026-12-13'for r in instances),historical_board_rows=len(table('operating/historical_board.csv')),differences=differences,integration_acceptance='PASS_SCOPED'if not differences else'CHANGES',CM01='CLOSED_IN_DERIVATIVE_ORIGINAL_RETAINED',CM02='MITIGATED_BY_QUARANTINE_IDENTITY_UNKNOWN',actual_flight_product='UNKNOWN',market_forecast='NOT_EVALUATED')
    (OUT/'input_manifest.json').write_text(json.dumps(dict(inputs=receipts),indent=2)+'\n')
    (OUT/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    print(json.dumps(result,ensure_ascii=False,default=str));assert not differences

if __name__=='__main__':
    main()
