#!/usr/bin/env python3
"""Join frozen acquired schedule evidence; retain independent acceptance axes.

No download, fleet allocation, demand, capacity, or money model. Unknown years,
arrival days and legal operators are not filled from auxiliary convenience maps.
"""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
I=ROOT/'inputs';O=ROOT/'operating'
PIN='a875cdd1ecaf778f53ba06cab1c66581a7f215c6'
P='branches/operating_evidence/normalized/'
ALIAS={'Киров':'KVX','Минеральные Воды':'MRV','Нижневартовск':'NJC','Уфа':'UFA','Екатеринбург':'SVX','Омск':'OMS','Красноярск':'KJA'}
def read(p):return list(csv.DictReader(p.open()))
def sid(tag,parts):return tag+':'+hashlib.sha256(json.dumps(parts,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
def write(name,rows,fields=None):
    fields=fields or list(rows[0])
    with (O/name).open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,extrasaction='raise');w.writeheader();w.writerows(rows)
def clock(s):
    m=re.search(r'(?<!\d)(\d{1,2})[:.\-](\d{2})(?!\d)',s)
    return f'{int(m[1]):02d}:{m[2]}' if m else ''
def offset(s):
    m=re.search(r'\(\s*\+(\d+)\s*\)',s)
    return m[1] if m else ''
def period(s):
    dates=re.findall(r'\d{1,2}\.\d{1,2}\.\d{2,4}',s)
    def parse(x):
        d,m,y=map(int,x.split('.'));return dt.date(y+2000 if y<100 else y,m,d).isoformat()
    if len(dates)==1:return parse(dates[0]),parse(dates[0])
    if len(dates)==2:return parse(dates[0]),parse(dates[1])
    return '',''
def main():
    O.mkdir(exist_ok=True);manifest=json.loads((ROOT/'input_manifest.json').read_text())
    for e in manifest['files']:assert hashlib.sha256((ROOT/e['path']).read_bytes()).hexdigest()==e['sha256']
    contract=manifest['contract'];pair_exp={tuple(pair):exp for exp,pairs in contract['experiments'].items() for pair in pairs}
    aps=read(I/'normalized/airport_version.csv');bycode={a['iata_code']:a for a in aps if a['iata_code']}
    assert len(bycode)==sum(bool(a['iata_code']) for a in aps)
    source_entries=json.loads((I/'dataset_manifest.json').read_text())['datasets']
    sources={e['original_dataset_id']:e for e in source_entries if 'branches/operating_evidence/' in (e.get('raw_path') or '')}
    tzrows=read(I/'normalized/timezone_crosscheck.csv');tz_by_entity={r['entity_id']:r for r in tzrows}
    tzversion=hashlib.sha256((I/'normalized/timezone_crosscheck.csv').read_bytes()).hexdigest()[:16]
    quarantine=[];airportkeys=[]
    for a in aps:
        reasons=[]
        if a['geographic_review']:reasons.append('COORDINATE_DISAGREEMENT_OVER_10KM')
        if a['timezone_validation_status']=='OFFSET_CONFLICT_REQUIRES_REVIEW':reasons.append('TIMEZONE_CONFLICT')
        tz=a['iana_timezone'] if not reasons else ''
        airportkeys.append(dict(airport_key_version=a['airport_id']+'@'+PIN,airport_id=a['airport_id'],iata=a['iata_code'],icao=a['icao_code'],name=a['name'],
            source_region_id=a['region_id'],iana_timezone=tz,published_iana_timezone=a['published_iana_timezone'],
            timezone_status=a['timezone_validation_status'],timezone_key_version=('TZ:'+tz+'@'+tzversion) if tz else '',identity_status='SOURCE_DIRECTORY_ID_ONLY',
            key_acceptance='QUARANTINE' if reasons else 'SOURCE_KEY_WITH_SCOPE_LIMITS',quarantine_reason=';'.join(reasons),source_commit=PIN))
        for reason in reasons:quarantine.append(dict(record_type='AIRPORT_KEY',record_id=a['airport_id'],source_table='normalized/airport_version.csv',reason=reason,blocked_use='Airport/city join or timezone conversion through this conflicting crosswalk',replacement='UNKNOWN'))
    ak={a['iata']:a for a in airportkeys if a['iata']}
    write('airport_keys.csv',airportkeys)
    keys=read(I/'canonical_keys.csv');area=[dict(r,key_version=r['canonical_id']+'@'+PIN) for r in keys if r['entity_type'] in {'city','travel_city','region'}]
    for r in area:
        conflict=tz_by_entity.get(r['canonical_id'],{}).get('crosscheck_status')=='OFFSET_CONFLICT_REQUIRES_REVIEW'
        r['key_acceptance']='QUARANTINE_TIMEZONE' if conflict else 'SOURCE_AREA_KEY_ONLY; NOT_CATCHMENT'
        if conflict:
            assert not r['iana_timezone']
            quarantine.append(dict(record_type='AREA_KEY',record_id=r['canonical_id'],source_table='canonical_keys.csv',reason='TIMEZONE_CONFLICT',blocked_use='City/travel-market timezone or airport fallback',replacement='UNKNOWN'))
    write('area_keys.csv',area)
    carriers=read(I/P/'carrier_source_aliases.csv')
    for c in carriers:
        c.update(carrier_key_version=c['carrier_key']+'@'+PIN,legal_operator_id='',marketing_carrier_id='',acceptance='SOURCE_LABEL_AND_PREFIX_ONLY')
    write('carrier_keys.csv',carriers)
    tzkeys=[]
    for zone in sorted({r['iana_timezone'] for r in airportkeys if r['iana_timezone']}):
        matches=[r for r in tzrows if r['usable_iana_timezone']==zone]
        offsets={r['published_offset_minutes'] for r in matches if r['published_offset_minutes']}
        assert len(offsets)==1
        tzkeys.append(dict(timezone_key_version='TZ:'+zone+'@'+tzversion,iana_timezone=zone,reference_date='2026-12-07',
            utc_offset_minutes=next(iter(offsets)),value_status='DERIVED',source_id='frozen timezone_crosscheck',source_commit=PIN,
            acceptance='DIRECTORY_CORROBORATION_ONLY; NOT_STATUTORY_BOUNDARY_VERIFICATION'))
    write('timezone_keys.csv',tzkeys)
    rules=[];historical=[]
    def rule(src,source_row,a,b,dep,arr,valid_from='',valid_to='',weekdays='',date_basis='UNKNOWN',carrier='',flight='',stops='UNKNOWN',period_raw='',dep_date='',arrival_date='',original=None):
        if (a,b) not in pair_exp:return
        source=sources[src];reasons=[]
        for code in [a,b]:
            if code not in ak:reasons.append('AIRPORT_KEY_MISSING:'+code)
            elif ak[code]['key_acceptance']=='QUARANTINE':reasons.append('AIRPORT_KEY_QUARANTINE:'+code)
            elif not ak[code]['iana_timezone']:reasons.append('TIMEZONE_UNKNOWN:'+code)
        r=dict(service_rule_id=sid('RULE',[src,source_row,a,b,flight,dep,arr,valid_from,valid_to,weekdays]),experiment_id=pair_exp[a,b],
            physical_leg_key='LEG:'+a+':'+b,origin_iata=a,destination_iata=b,
            origin_airport_key=ak.get(a,{}).get('airport_key_version',''),destination_airport_key=ak.get(b,{}).get('airport_key_version',''),
            valid_from=valid_from,valid_to=valid_to,departure_date_local=dep_date,arrival_date_local=arrival_date,
            weekdays_iso=weekdays,weekday_basis=date_basis,departure_local=clock(dep),arrival_local=clock(arr),
            departure_day_offset='0',arrival_day_offset=offset(arr) if not (dep_date and arrival_date) else str((dt.date.fromisoformat(arrival_date)-dt.date.fromisoformat(dep_date)).days),
            arrival_day_offset_status='EXPLICIT_DATE_OR_NEXT_DAY_MARKER' if offset(arr) or (dep_date and arrival_date) else 'UNKNOWN',
            origin_iana=ak.get(a,{}).get('iana_timezone',''),destination_iana=ak.get(b,{}).get('iana_timezone',''),
            origin_timezone_status=ak.get(a,{}).get('timezone_status','UNKNOWN'),destination_timezone_status=ak.get(b,{}).get('timezone_status','UNKNOWN'),
            origin_timezone_key_version=ak.get(a,{}).get('timezone_key_version',''),destination_timezone_key_version=ak.get(b,{}).get('timezone_key_version',''),
            source_carrier_label=carrier,source_flight_label=flight,operating_carrier_id='',marketing_carrier_id='',
            operating_carrier_status='UNKNOWN_LEGAL_OPERATOR; source label retained',marketing_carrier_status='UNKNOWN',
            nonstop_status=stops,intermediate_status='UNKNOWN' if stops=='UNKNOWN' else 'NONE_LISTED_IN_PUBLISHED_ADJACENT_LEG; not verified nonstop',
            intermediate_iata='',source_id=src,source_row=str(source_row),source_url=source['source_url'],source_raw_sha256=source['sha256'],
            source_retrieved_at_utc=source['retrieved_at_utc'],source_pinned_sha=PIN,
            period_raw=period_raw,departure_clock_raw=dep,arrival_clock_raw=arr,
            value_status='OBSERVED',value_scope='Publisher schedule assertion',source_acquisition_status=source['acquisition_status'],
            rule_acceptance='QUARANTINE' if reasons else 'PUBLISHED_RULE_ONLY',quarantine_reason=';'.join(reasons),
            execution_status='UNKNOWN',time_basis='LOCAL_AT_AIRPORTS' if src in {'svx_schedule','omsk_winter_2026','uvt_schedule_current'} else 'UNKNOWN',
            year_status='EXPLICIT_YEAR' if valid_from or dep_date else 'UNKNOWN',scenario_sync_unsync_legset='C01_SAME_PHYSICAL_LEGS' if pair_exp[a,b]=='C01' else '')
        rules.append(r)
    # SVX airport rules retain their omitted years.
    for x in read(I/P/'svx_published_schedule_rules.csv'):
        rule('svx_schedule',x['source_table_row'],x['origin_airport_iata'],x['destination_airport_iata'],x['departure_local_raw'],x['arrival_local_raw'],
            weekdays=x['weekdays_iso'],date_basis='ORIGIN_WEEKDAY_EXPLICIT; YEAR_UNKNOWN',carrier=x['carrier_raw'],flight=x['flight_number_raw'],period_raw=x['validity_raw'])
    for x in read(I/P/'uvt_schedule_rules_unique.csv'):
        rule('uvt_schedule_current',x['source_table_origin']+':'+x['source_table_row']+':'+x['source_direction'],ALIAS.get(x['origin_city_raw'],''),ALIAS.get(x['destination_city_raw'],''),
            x['departure_local_raw'],x['arrival_local_raw'],x['valid_from'],x['valid_to'],x['weekdays_iso'],'ORIGIN_WEEKDAY_EXPLICIT',x['carrier'],x['flight_number_normalized'],period_raw=x['validity_raw'])
    for x in read(I/P/'iraero_published_itineraries.csv'):
        rule(x['source_dataset_id'],x['source_row'],x['origin_code_raw'],x['destination_code_raw'],x['departure_local'],x['arrival_local'],
            carrier=x['carrier'],flight=x['flight_number_raw'],dep_date=x['departure_date'])
    # PDF pairs are split as adjacent legs. Only OMS-origin weekday is dated.
    for x in read(I/P/'omsk_domestic_timetable_rows.csv'):
        route=[s.strip() for s in re.split(r'\s*[–—-]\s*',x['routing_raw'])]
        if len(route)!=3 or route[1]!='Омск':continue
        remote=ALIAS.get(route[0],'');onward=ALIAS.get(route[2],'');start,end=period(x['period_raw'])
        if not start or end<'2026-12-07' or start>'2026-12-27':continue
        flights=x['flight_numbers_raw'].split('/')
        rule('omsk_winter_2026',x['source_text_line']+':OUT','OMS',onward,x['omsk_departure_local_raw'],x['onward_arrival_local_raw'],start,end,
            x['weekdays_raw'].replace(',',';'),'OMS_ORIGIN_WEEKDAY',x['carrier_raw'],flights[-1].strip(),'PUBLISHED_ADJACENT_STATIONS',x['period_raw'])
        rule('omsk_winter_2026',x['source_text_line']+':IN',remote,'OMS',x['preceding_origin_departure_local_raw'],x['omsk_arrival_local_raw'],start,end,
            x['weekdays_raw'].replace(',',';'),'OMS_TURN_DATE; REMOTE_ORIGIN_DEPARTURE_DATE_UNKNOWN',x['carrier_raw'],flights[0].strip(),'PUBLISHED_ADJACENT_STATIONS',x['period_raw'])
    write('service_rules.csv',rules)
    # Historical November board records cannot establish December service.
    for x in read(I/P/'azimuth_flight_instances.csv'):
        a=ALIAS.get(x['origin_name_raw'],'');b=ALIAS.get(x['destination_name_raw'],'')
        if (a,b) not in pair_exp:continue
        historical.append(dict(source_instance_id=sid('HIST',['azimuth_board',x['source_row']]),experiment_id=pair_exp[a,b],origin_iata=a,destination_iata=b,
            departure_local=x['departure_planned_local'],arrival_local=x['arrival_planned_local'],source_carrier_label=x['carrier'],source_flight_label=x['flight_number_normalized'],
            operating_carrier_id='',marketing_carrier_id='',time_basis='UNKNOWN',execution_status=x['flight_status_reported'] or 'UNKNOWN',
            source_id='azimuth_board',source_row=x['source_row'],source_pinned_sha=PIN,acceptance='HISTORICAL_BOARD_ONLY; OUTSIDE_DECEMBER_WINDOW',
            limitation='Year inferred from snapshot; not December recurrence or verified nonstop'))
    write('historical_board.csv',historical)
    dated=[]
    for r in rules:
        if not r['valid_from'] or r['weekday_basis'] not in {'OMS_ORIGIN_WEEKDAY','ORIGIN_WEEKDAY_EXPLICIT'} or r['rule_acceptance']=='QUARANTINE':continue
        for n in range(21):
            day=dt.date(2026,12,7)+dt.timedelta(days=n)
            if not r['valid_from']<=day.isoformat()<=r['valid_to'] or str(day.isoweekday()) not in r['weekdays_iso'].split(';'):continue
            dep=dt.datetime.fromisoformat(day.isoformat()+'T'+r['departure_local']).replace(tzinfo=ZoneInfo(r['origin_iana']))
            row=dict(r);row.update(instance_id=sid('DEP',[r['service_rule_id'],day.isoformat()]),departure_date_local=day.isoformat(),departure_utc=dep.astimezone(dt.timezone.utc).isoformat(),
                arrival_utc='',arrival_date_local='',value_status='DERIVED',value_scope='Calendar expansion of published rule',
                calendar_acceptance='DATED_DEPARTURE_ONLY; ARRIVAL_DAY_UNKNOWN',product_acceptance='UNKNOWN',execution_status='UNKNOWN')
            # Unknown arrival day is deliberately not inferred from a plausible block time.
            dated.append(row)
    write('dated_instances.csv',dated)
    # Inherited Tobolsk aliases are quarantined even though not target legs.
    omsk_overlay=[]
    for x in read(I/P/'omsk_outbound_week_20261207.csv'):
        held='Тобольск' in x['next_airport_name'];code=x['destination_airport_iata']
        if held:
            quarantine.append(dict(record_type='SOURCE_DATED_DEPARTURE',record_id=x['source_text_line']+':'+x['departure_date_local'],source_table=P+'omsk_outbound_week_20261207.csv',
                reason='CM02_TOBOLSK_CITY_ALIAS_TO_TOX_UNRESOLVED; RMZ is a separate airport',blocked_use='Physical airport identity, capacity aggregation, downstream timezone fallback',replacement='UNKNOWN'))
        other_hold=ak.get(code,{}).get('key_acceptance')=='QUARANTINE'
        omsk_overlay.append(dict(source_instance_id=sid('OMS',[x['source_text_line'],x['departure_date_local'],x['outbound_flight_numeric']]),
            origin_iata='OMS',destination_iata='' if held or other_hold else code,
            destination_airport_key='' if held or other_hold else x['destination_airport_key'],
            destination_iana='' if held or other_hold else x['destination_iana_timezone'],
            legacy_destination_iata=code,legacy_destination_airport_key=x['destination_airport_key'],
            departure_date_local=x['departure_date_local'],departure_local=x['departure_local'],departure_utc=x['departure_utc'],
            source_next_stop_label=x['next_airport_name'],source_carrier_label=x['carrier_raw'],source_flight_label=x['flight_numbers_source'],
            operating_carrier_id='',marketing_carrier_id='',acceptance='QUARANTINE_AIRPORT_ALIAS' if held else ('QUARANTINE_AIRPORT_KEY' if other_hold else 'DATED_DEPARTURE_SOURCE_ASSERTION'),
            source_id='omsk_winter_2026',source_pinned_sha=PIN,source_row=x['source_text_line'],
            limitation='UTC is an origin clock transformation, not destination identity proof; legacy fields are audit-only'))
    write('omsk_departure_overlay.csv',omsk_overlay)
    for q in quarantine:q['quarantine_id']=sid('Q',[q['record_type'],q['record_id'],q['reason']])
    write('quarantine.csv',quarantine)
    coverage=[]
    for pair,exp in pair_exp.items():
        rs=[r for r in rules if (r['origin_iata'],r['destination_iata'])==pair];ds=[r for r in dated if (r['origin_iata'],r['destination_iata'])==pair]
        hs=[r for r in historical if (r['origin_iata'],r['destination_iata'])==pair]
        coverage.append(dict(experiment_id=exp,origin_iata=pair[0],destination_iata=pair[1],retained_rule_count=len(rs),retained_dated_departures_07_27=len(ds),
            retained_dated_departures_07_13=sum(r['departure_date_local']<='2026-12-13' for r in ds),historical_board_count=len(hs),
            complete_calendar_instances=0,source_scope='Frozen acquired tables only; not a comprehensive schedule search',
            absence_of_service_claim='FALSE',gap='ARRIVAL_DAY/OPERATOR/EXECUTION_UNKNOWN' if ds else 'NO_ACCEPTED_DATED_RECORD_IN_FROZEN_TABLES'))
    write('coverage.csv',coverage)
    # CM01: preserve every correct observation and distinguish semantic key/version.
    market=read(I/'normalized/market_observation.csv')
    for r in market:
        r['legacy_observation_id']=r['observation_id']
        r['observation_id']=sid('OBS',[r[k] for k in ['source_id','entity_id','metric','period_start','period_end','unit','observation_kind']])
        r['observation_version_id']=sid('OBSVER',[r['observation_id'],r['snapshot_at_utc'],r['value'],r['qualifier']])
    assert len(market)==24 and len({r['observation_id'] for r in market})==24
    write('market_observation_v1.csv',market)
    write('audit_resolution.csv',[dict(finding_id='CM01',input_commit=PIN,resolution='FIXED_IN_DERIVATIVE',artifact='market_observation_v1.csv',boundary='Both correct periods preserved;24semanticIDs unique; frozen original unchanged'),
        dict(finding_id='CM02',input_commit=PIN,resolution='QUARANTINE_PENDING_IDENTITY',artifact='quarantine.csv',boundary='Two inherited city-to-TOX mappings blocked; no silent substitution to RMZ')])
    result=dict(input_set_id=manifest['input_set_id'],source_commit=PIN,service_rules=len(rules),dated_departures=len(dated),historical_board=len(historical),
        quarantined_records=len(quarantine),complete_calendar_instances=0,market_rows=24,market_unique_semantic_ids=24,
        source_truth_acceptance='No OD/fleet/capacity/net yield/operating execution accepted')
    (O/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
