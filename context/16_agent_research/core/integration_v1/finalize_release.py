#!/usr/bin/env python3
"""Validate/output a small consumable release manifest from frozen input tables."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent;O=ROOT/'operating'
def read(f):return list(csv.DictReader(f.open()))
def write(name,rows,fields=None):
    with (O/name).open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    manifest=json.loads((ROOT/'input_manifest.json').read_text());rules=read(O/'service_rules.csv');instances=read(O/'dated_instances.csv')
    assert len({r['service_rule_id'] for r in rules})==len(rules)
    assert len({r['instance_id'] for r in instances})==len(instances)==12
    assert all(r['operating_carrier_id']==r['marketing_carrier_id']=='' for r in rules+instances)
    assert all(r['arrival_day_offset']==r['arrival_utc']=='' for r in instances)
    assert all('UNKNOWN' in r['calendar_acceptance'] for r in instances)
    overlay=read(O/'omsk_departure_overlay.csv');held=[r for r in overlay if r['acceptance']=='QUARANTINE_AIRPORT_ALIAS']
    assert len(overlay)==98 and len(held)==2
    assert all(r['destination_iata']==r['destination_airport_key']==r['destination_iana']=='' for r in held)
    market=read(O/'market_observation_v1.csv');assert len(market)==len({r['observation_id'] for r in market})==24
    repeated=[r for r in market if r['legacy_observation_id']=='favt_ru:4262:carrier_passengers']
    assert len(repeated)==2 and {r['period_start'] for r in repeated}=={'2025-01-01','2025-05-01'}
    quarantine=read(O/'quarantine.csv');assert len({r['quarantine_id'] for r in quarantine})==len(quarantine)
    byid={r['airport_id']:r for r in read(O/'airport_keys.csv')}
    assert all(not byid[q['record_id']]['iana_timezone'] for q in quarantine if q['record_type']=='AIRPORT_KEY')
    coverage=read(O/'coverage.csv');assert all(r['absence_of_service_claim']=='FALSE' for r in coverage)
    missing=[]
    for r in coverage:
        if r['retained_dated_departures_07_13']=='0':missing.append(dict(experiment_id=r['experiment_id'],origin_iata=r['origin_iata'],destination_iata=r['destination_iata'],
            missing_requirement='Accepted origin-date flight evidence in7–13Dec frozen scope',status='UNKNOWN',reason=r['gap'],not_inferred='No zero-demand/no-service inference'))
    write('unmatched.csv',missing)
    legs=[]
    for exp,pairs in manifest['contract']['experiments'].items():
        setid=exp+':LEGSET:'+hashlib.sha256(json.dumps(pairs).encode()).hexdigest()[:16]
        for a,b in pairs:legs.append(dict(experiment_id=exp,physical_leg_set_id=setid,physical_leg_key='LEG:'+a+':'+b,origin_iata=a,destination_iata=b,
            modes_referencing_same_set='SYNC;UNSYNC' if exp=='C01' else 'REFERENCE',resource_availability='UNKNOWN',claim='Required comparison structure; not allocated aircraft or new capacity'))
    write('physical_leg_requirements.csv',legs)
    dictionary=[]
    grains={'service_rules.csv':'Publisher rule × source row × direction; not unique physical capacity',
        'dated_instances.csv':'Rule × explicit origin departure date; arrival day still UNKNOWN',
        'historical_board.csv':'Source November board row; not winter recurrence',
        'airport_keys.csv':'Source airport identity × frozen commit',
        'area_keys.csv':'Source namespace area identity × frozen commit; not catchment',
        'carrier_keys.csv':'Source publisher label/prefix; legal operator and marketing unresolved',
        'timezone_keys.csv':'IANA assertion × frozen crosscheck version; reference date2026-12-07',
        'quarantine.csv':'Record × independent block reason',
        'coverage.csv':'Experiment × directed required leg; sample coverage not service universe',
        'market_observation_v1.csv':'Source/entity/metric/period/unit/kind; snapshot is version',
        'omsk_departure_overlay.csv':'Original dated OMS source row; safe destination fields null when held',
        'physical_leg_requirements.csv':'One required directed leg; sync/unsync refer to same set'}
    for f in sorted(O.glob('*.csv')):
        if f.name=='table_dictionary.csv':continue
        with f.open() as h:fields=csv.DictReader(h).fieldnames
        for field in fields:
            unit='text/category or publisher literal'
            if field.endswith('_iata') or field=='iata':unit='IATA-style source code; not city identity proof'
            elif 'day_offset' in field and not field.endswith('status'):unit='integer calendar days; blank UNKNOWN'
            elif field.endswith('_utc'):unit='ISO8601 UTC timestamp'
            elif field.endswith('_local'):unit='Local civil date/clock; IANA and day offset required'
            elif field=='weekdays_iso':unit='1=Monday,...,7=Sunday; semicolon-separated'
            elif field=='utc_offset_minutes':unit='minutes east of UTC at reference date'
            elif 'count' in field or 'departures_' in field:unit='retained source records; not passengers/capacity'
            elif field.endswith('_id') or 'key' in field:unit='versioned identifier; namespace preserved'
            dictionary.append(dict(table=f.name,grain=grains.get(f.name,'See contract and row status'),field=field,unit=unit,
                null_policy='Blank with status/reason; no imputation from an auxiliary table',acceptance='Only the explicit acceptance axis; not execution/demand/fleet approval'))
    write('table_dictionary.csv',dictionary)
    files=[]
    for f in sorted(O.iterdir()):
        if not f.is_file() or f.name=='output_manifest.json':continue
        count=None
        if f.suffix=='.csv':count=len(read(f))
        files.append(dict(path='operating/'+f.name,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),size_bytes=f.stat().st_size,record_count=count))
    out=dict(release_version='core-operating-integration-v1.1',input_set_id=manifest['input_set_id'],source_commit=manifest['frozen_source_commit'],
        contract_sha256=hashlib.sha256((ROOT/'contract.json').read_bytes()).hexdigest(),files=files,
        validation=dict(all_pass=True,market_unique_ids=24,CM01_both_correct_periods_preserved=True,CM02_held_alias_rows=2,arrival_days_not_filled=True,
            operator_marketing_not_filled=True,quarantined_timezones_not_used=True,C01_shared_physical_legset=True),
        acceptance='SCOPED_INTEGRATION_AND_CALENDAR_EXTRACTION_ONLY; no full passenger product, OD, performed flight, seats, fleet or net yield acceptance',
        immutable_consumption='Pin this manifest SHA and containing Git commit. New C14 peer data requires a separate addendum input-set.')
    (O/'output_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('validated',len(files),'artifacts;',len(missing),'unmatched directed legs; source calendar departures',len(instances))
if __name__=='__main__':main()
