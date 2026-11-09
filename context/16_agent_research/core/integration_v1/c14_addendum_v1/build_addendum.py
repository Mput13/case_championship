#!/usr/bin/env python3
"""Separately frozen C14 peer input; independently parse primary cells/replay dates.

No peer code is imported or executed. Source carrier association is not promoted
to a verified legal operating/marketing identity. UTC retains the <24h rollover
assumption. Hotel nights/transfer products are outside this operating-service pass.
"""
import csv
import datetime as dt
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
PEER='fa39de413ac00a93b0214840aae2e7916332cef5'
BASE='context/16_agent_research/alternative/product_probe_v1/'
CORE='b264780e65a0e04afd42da811652039c70fc1def'
COREBASE='context/16_agent_research/core/integration_v1/'
EXPECTED_RAW='e6d324e8a82f6f92ecb3966bac4a836c24fd40d61d28509017a8acbe75fe5a49'
FILES=['table_contract.json','dataset_manifest.json','flight_checkpoint_manifest.json','reference/airport_keys.csv',
 'normalized/flight_rules.csv','normalized/flight_rule_cells.csv','normalized/dated_flights.csv',
 'normalized/flight_validation.json','receipts/kvx_timetable_20261109.json','README.md']
class Parser(HTMLParser):
    """Collect labelled blocks without depending on the peer DOM parser."""
    def __init__(self):
        super().__init__(convert_charrefs=True);self.stack=[];self.blocks=[];self.active=None;self.texts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);classes=a.get('class','').split()
        if tag=='div' and 'result__block' in classes:
            assert self.active is None;self.active=[];self.start_depth=len(self.stack)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr','image','path','use'}:self.stack.append(tag)
    def handle_startendtag(self,t,a):pass
    def handle_endtag(self,tag):
        if tag in self.stack:
            n=len(self.stack)-1-self.stack[::-1].index(tag);self.stack=self.stack[:n]
        if self.active is not None and len(self.stack)<=self.start_depth:
            self.blocks.append(' '.join(' '.join(self.active).split()));self.active=None
    def handle_data(self,s):
        self.texts.append(s)
        if self.active is not None:self.active.append(s)
def read(p):return list(csv.DictReader(p.open()))
def write(name,rows):
    p=ROOT/'outputs'/name
    with p.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    (ROOT/'inputs').mkdir(exist_ok=True);(ROOT/'outputs').mkdir(exist_ok=True)
    inputs=[]
    for p in FILES:
        b=subprocess.check_output(['git','show',PEER+':'+BASE+p]);dest=ROOT/'inputs'/p;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert dest.read_bytes()==b
        else:dest.write_bytes(b)
        inputs.append(dict(path=str(dest.relative_to(ROOT)),source_commit=PEER,source_path=BASE+p,sha256=hashlib.sha256(b).hexdigest(),size_bytes=len(b)))
    assert hashlib.sha256((ROOT/'inputs/flight_checkpoint_manifest.json').read_bytes()).hexdigest()=='7d589e1492688aa29aa8396b7f3e3be64f2674fe98521cba6825a4d02364aaa6'
    assert hashlib.sha256((ROOT/'inputs/dataset_manifest.json').read_bytes()).hexdigest()=='28dd4197df4fca88b8bafbac54c09aab53caf633d8d2748a0862c3d60719fc01'
    # raw_hold is copied once after the expected hash is checked; never published.
    raw=ROOT/'raw_hold/kvx_timetable.bin';body=raw.read_bytes();assert hashlib.sha256(body).hexdigest()==EXPECTED_RAW
    p=Parser();p.feed(body.decode());full=' '.join(' '.join(p.texts).split())
    assert 'в расписании указано местное время аэропортов прилета/вылета' in full
    primary=[]
    for block in p.blocks:
        flight=re.search(r'А4\s*60(?:13|14)',block)
        if not flight:continue
        journey=re.search(r'Направление\s+(\d{2}:\d{2})\s+(.*?)\s+(\d{2}:\d{2})\s+(.*?)\s+Аэропорт прилета',block)
        dates=re.findall(r'\d{2}\.\d{2}\.\d{4}',block)
        weekday=re.search(r'Дни\s+(Пн|Вт|Ср|Чт|Пт|Сб|Вс)',block)
        assert journey and len(dates)==2 and weekday,block[:100]
        primary.append(dict(flight_number=flight[0].replace('А','A').replace(' ',''),origin_name=journey[2],destination_name=journey[4],dep=journey[1],arr=journey[3],
            valid_from=dt.datetime.strptime(dates[0],'%d.%m.%Y').date().isoformat(),valid_to=dt.datetime.strptime(dates[1],'%d.%m.%Y').date().isoformat(),
            weekday=str({'Пн':1,'Вт':2,'Ср':3,'Чт':4,'Пт':5,'Сб':6,'Вс':7}[weekday[1]])))
    assert len(primary)==6
    rules=read(ROOT/'inputs/normalized/flight_rules.csv');dates=read(ROOT/'inputs/normalized/dated_flights.csv')
    def key(r):return (r['flight_number'],r['origin_name_source'],r['destination_name_source'],r['departure_local_time'],r['arrival_local_time'],r['valid_from'],r['valid_to'],r['weekdays_iso'])
    primarykeys={(r['flight_number'],r['origin_name'],r['destination_name'],r['dep'],r['arr'],r['valid_from'],r['valid_to'],r['weekday']) for r in primary}
    assert {key(r) for r in rules}==primarykeys
    corebytes=subprocess.check_output(['git','show',CORE+':'+COREBASE+'operating/airport_keys.csv'])
    corekeys={r['iata']:r for r in csv.DictReader(io.StringIO(corebytes.decode())) if r['iata']}
    primary_inputs_sha=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    inputset='CORE-C14-ADDENDUM-V1:'+hashlib.sha256((primary_inputs_sha+CORE+EXPECTED_RAW).encode()).hexdigest()
    adapted=[];zonetests=[]
    for r in rules:
        a,b=r['origin_iata'],r['destination_iata'];assert corekeys[a]['key_acceptance']!='QUARANTINE' and corekeys[b]['key_acceptance']!='QUARANTINE'
        for code,zone in [(a,r['origin_iana']),(b,r['destination_iana'])]:
            published=corekeys[code]['iana_timezone']
            for date in ['2026-12-07','2026-12-27']:
                candidate=dt.datetime.fromisoformat(date+'T12:00').replace(tzinfo=ZoneInfo(zone)).utcoffset()
                inherited=dt.datetime.fromisoformat(date+'T12:00').replace(tzinfo=ZoneInfo(published)).utcoffset();assert candidate==inherited
            zonetests.append(dict(iata=code,source_iana=zone,core_iana=published,scope='Offsets agree on7/27Dec2026; different names preserved, no statutory boundary claim',status='OFFSET_COMPATIBLE'))
        adapted.append(dict(rule_id=r['rule_id'],experiment_id='C14',input_set_id=inputset,origin_iata=a,destination_iata=b,
            origin_airport_id=r['origin_airport_id'],destination_airport_id=r['destination_airport_id'],source_carrier_association=r['operating_carrier_id'],source_carrier_code=r['operating_carrier_iata'],
            operating_carrier_id='',marketing_carrier_id='',carrier_acceptance='PUBLISHED_ASSOCIATION_ONLY; legal operator/marketing role UNKNOWN',
            source_flight_label=r['flight_number'],valid_from=r['valid_from'],valid_to=r['valid_to'],weekdays_iso=r['weekdays_iso'],
            departure_local=r['departure_local_time'],arrival_local=r['arrival_local_time'],arrival_day_offset=r['arrival_day_offset'],
            origin_iana=r['origin_iana'],destination_iana=r['destination_iana'],timezone_status='OFFSET_COMPATIBLE_WITH_FROZEN_CORE; source names preserved',
            rule_value_status='OBSERVED',day_offset_value_status='DERIVED',timezone_mapping_value_status='DERIVED',
            day_offset_assumption=r['day_offset_status'],nonstop_status='UNKNOWN',intermediate_status='UNKNOWN',
            source_id='kvx_timetable_20261109',source_raw_sha256=EXPECTED_RAW,source_pinned_sha=PEER,source_url=r['source_url'],
            clock_basis=r['clock_basis'],source_acceptance='PRIMARY_PUBLISHED_SCHEDULE; not inventory/execution',
            calendar_acceptance='CONDITIONAL_ON_LT24H_DAY_ROLLOVER',performed_status='UNKNOWN',inventory_status='UNKNOWN'))
    write('service_rules.csv',adapted)
    # Independently expand dates and reconcile every UTC/duration against peer CSV.
    generated=[];byrule={r['rule_id']:r for r in adapted}
    for n in range(21):
        day=dt.date(2026,12,7)+dt.timedelta(days=n)
        for r in adapted:
            if not r['valid_from']<=day.isoformat()<=r['valid_to'] or str(day.isoweekday())!=r['weekdays_iso']:continue
            dep=dt.datetime.fromisoformat(day.isoformat()+'T'+r['departure_local']).replace(tzinfo=ZoneInfo(r['origin_iana']))
            arrday=day+dt.timedelta(days=int(r['arrival_day_offset']))
            arr=dt.datetime.fromisoformat(arrday.isoformat()+'T'+r['arrival_local']).replace(tzinfo=ZoneInfo(r['destination_iana']))
            minutes=int((arr.astimezone(dt.timezone.utc)-dep.astimezone(dt.timezone.utc)).total_seconds()/60)
            assert 0<minutes<24*60
            generated.append(dict(instance_id=r['rule_id']+':'+day.isoformat(),rule_id=r['rule_id'],experiment_id='C14',input_set_id=inputset,
                origin_iata=r['origin_iata'],destination_iata=r['destination_iata'],departure_date_local=day.isoformat(),arrival_date_local=arrday.isoformat(),
                departure_local=dep.isoformat(),arrival_local=arr.isoformat(),departure_utc=dep.astimezone(dt.timezone.utc).isoformat(),arrival_utc=arr.astimezone(dt.timezone.utc).isoformat(),
                arrival_day_offset=r['arrival_day_offset'],elapsed_minutes=minutes,origin_iana=r['origin_iana'],destination_iana=r['destination_iana'],
                operating_carrier_id='',marketing_carrier_id='',source_carrier_association=r['source_carrier_association'],nonstop_status='UNKNOWN',
                value_status='DERIVED',acceptance='CONDITIONAL_CALENDAR_ONLY; DAY_ROLLOVER_LT24H_ASSUMED',performed_status='UNKNOWN',inventory_status='UNKNOWN',
                departure_window_role='OUTBOUND_CANDIDATE_07_13' if r['origin_iata']=='KVX' and day<=dt.date(2026,12,13) else ('RETURN_EVIDENCE_UNTIL27' if r['origin_iata']=='MRV' else 'LATER_OUTBOUND_CONTEXT'),
                hotel_nights_acceptance='UNKNOWN; hotel/transfer/checkin clocks not resolved',source_pinned_sha=PEER,source_raw_sha256=EXPECTED_RAW))
    peerbyid={r['instance_id']:r for r in dates};assert len(generated)==len(peerbyid)==12
    for r in generated:
        other=peerbyid[r['instance_id']]
        for a,b in [('departure_utc','departure_utc'),('arrival_utc','arrival_utc'),('arrival_date_local','arrival_local_date'),('elapsed_minutes','planned_duration_minutes')]:assert str(r[a])==other[b]
    write('dated_instances.csv',generated)
    # A compatible union is a new frozen input set, never a rewrite of base.
    def core_table(path):
        return list(csv.DictReader(io.StringIO(subprocess.check_output(['git','show',CORE+':'+COREBASE+path],text=True))))
    baserules=core_table('operating/service_rules.csv');baseinstances=core_table('operating/dated_instances.csv')
    basemf=json.loads(subprocess.check_output(['git','show',CORE+':'+COREBASE+'operating/output_manifest.json'],text=True))
    cells={r['rule_id']:r for r in read(ROOT/'inputs/normalized/flight_rule_cells.csv')};source_receipt=json.loads((ROOT/'inputs/receipts/kvx_timetable_20261109.json').read_text())
    unionrules=[]
    for r in adapted:
        v={k:'' for k in baserules[0]};cell=cells[r['rule_id']]
        v.update(service_rule_id=r['rule_id'],experiment_id='C14',physical_leg_key='LEG:'+r['origin_iata']+':'+r['destination_iata'],
            origin_iata=r['origin_iata'],destination_iata=r['destination_iata'],
            origin_airport_key=corekeys[r['origin_iata']]['airport_key_version'],destination_airport_key=corekeys[r['destination_iata']]['airport_key_version'],
            valid_from=r['valid_from'],valid_to=r['valid_to'],weekdays_iso=r['weekdays_iso'],weekday_basis='ORIGIN_WEEKDAY_EXPLICIT',
            departure_local=r['departure_local'],arrival_local=r['arrival_local'],departure_day_offset='0',arrival_day_offset=r['arrival_day_offset'],
            arrival_day_offset_status='DERIVED_CLOCK_ROLLOVER_ASSUMES_LESS_THAN24H',origin_iana=r['origin_iana'],destination_iana=r['destination_iana'],
            origin_timezone_status='OFFSET_COMPATIBLE_WITH_FROZEN_CORE',destination_timezone_status='OFFSET_COMPATIBLE_WITH_FROZEN_CORE',
            origin_timezone_key_version='TZ:'+r['origin_iana']+'@'+primary_inputs_sha[:16],destination_timezone_key_version='TZ:'+r['destination_iana']+'@'+primary_inputs_sha[:16],
            source_carrier_label='Азимут (published association)',source_flight_label=r['source_flight_label'],operating_carrier_id='',marketing_carrier_id='',
            operating_carrier_status='UNKNOWN_LEGAL_OPERATOR; source association retained',marketing_carrier_status='UNKNOWN',nonstop_status='UNKNOWN',intermediate_status='UNKNOWN',
            source_id='kvx_timetable_20261109',source_row=cell['block_ordinal'],source_url=r['source_url'],source_raw_sha256=EXPECTED_RAW,
            source_retrieved_at_utc=source_receipt['retrieved_at_utc'],source_pinned_sha=PEER,period_raw=cell['period_display'],departure_clock_raw=cell['departure_display'],arrival_clock_raw=cell['arrival_display'],
            value_status='OBSERVED',value_scope='Publisher timetable cells; day offset and IANA association DERIVED separately',source_acquisition_status='PARSED',
            rule_acceptance='PUBLISHED_RULE_ONLY; DAY_OFFSET_DERIVED',execution_status='UNKNOWN',time_basis='LOCAL_AT_AIRPORTS',year_status='EXPLICIT_YEAR')
        unionrules.append(v)
    basefields=list(baserules[0]);rows=[]
    for component,rs in [(basemf['input_set_id'],baserules),(inputset,unionrules)]:
        for r in rs:rows.append(dict(r,input_set_id=inputset,component_input_set_id=component))
    write('operating_service_rules_union.csv',rows)
    byunionrule={r['service_rule_id']:r for r in unionrules};newinstances=[]
    for r in generated:
        v={k:'' for k in baseinstances[0]};v.update(byunionrule[r['rule_id']])
        v.update(instance_id=r['instance_id'],departure_date_local=r['departure_date_local'],arrival_date_local=r['arrival_date_local'],
            departure_utc=r['departure_utc'],arrival_utc=r['arrival_utc'],value_status='DERIVED',value_scope='Calendar under explicit LT24H rollover assumption',
            calendar_acceptance=r['acceptance'],product_acceptance='UNKNOWN; hotel/transfer/inventory/actual operator not resolved')
        newinstances.append(v)
    rows=[]
    for component,rs in [(basemf['input_set_id'],baseinstances),(inputset,newinstances)]:
        for r in rs:
            date=r['departure_date_local'];scope='PRIMARY_DEPARTURE_07_13' if date<='2026-12-13' else 'LATER_CONTEXT_14_27'
            rows.append(dict(r,input_set_id=inputset,component_input_set_id=component,departure_window_membership=scope))
    assert len(rows)==24 and len({r['instance_id'] for r in rows})==24
    write('operating_dated_instances_union.csv',rows)
    write('source_conflicts.csv',[dict(conflict_id='C14_WEEKDAY_VERSION',older_source_id='SA02',older_days_reported='Monday;Friday',
        older_evidence_status='Prior announcement referenced by frozen peer README; original announcement not independently rechecked in this addendum',
        current_source_id='kvx_timetable_20261109',current_days='Monday;Thursday',current_raw_sha256=EXPECTED_RAW,
        current_acceptance='6PRIMARY_RULE_BLOCKS_MATCHED; future execution UNKNOWN',reference_commit=PEER,
        resolution='Preserve source versions; no Friday recurrence from old announcement in the new dated calendar',
        limitation='A newer schedule does not retroactively falsify a historical announcement or prove inventory')])
    uniquezones={tuple(r.values()):r for r in zonetests};write('timezone_reconciliation.csv',list(uniquezones.values()))
    tzunion=core_table('operating/timezone_keys.csv')
    for zone in sorted({r['origin_iana'] for r in adapted}|{r['destination_iana'] for r in adapted}):
        t=dt.datetime(2026,12,7,12,tzinfo=ZoneInfo(zone))
        tzunion.append(dict(timezone_key_version='TZ:'+zone+'@'+primary_inputs_sha[:16],iana_timezone=zone,reference_date='2026-12-07',
            utc_offset_minutes=int(t.utcoffset().total_seconds()/60),value_status='DERIVED',source_id='C14 peer curated IANA; primary clock footer local',source_commit=PEER,
            acceptance='OFFSET_COMPATIBLE_WITH_BASE; NOT_STATUTORY_BOUNDARY_VERIFICATION'))
    write('timezone_keys_union.csv',tzunion)
    write('field_acceptance.csv',[dict(field_group='Publisher route/clock/period/day cells',value_status='OBSERVED',acceptance='6PRIMARY_BLOCKS_INDEPENDENTLY_MATCHED',limit='Source claim, not actual service'),
        dict(field_group='Arrival day, date, UTC, duration',value_status='DERIVED',acceptance='12INSTANCES_REPLAYED_UNDER_LT24H_ASSUMPTION',limit='No promotion to explicit source day offset'),
        dict(field_group='Carrier legal operating and marketing roles',value_status='UNKNOWN',acceptance='NOT_ACCEPTED',limit='Publisher association retained separately'),
        dict(field_group='Nonstop/intermediate pattern/inventory/performed',value_status='UNKNOWN',acceptance='NOT_ACCEPTED',limit='No seats or actual execution claim'),
        dict(field_group='Local hotel nights and transfer compatibility',value_status='UNKNOWN',acceptance='NOT_EVALUATED_IN_CORE_OPERATING_PASS',limit='Outbound departure date is not hotel check-in date')])
    data=dict(schema_version='core-c14-addendum-v1',input_set_id=inputset,peer_source_commit=PEER,core_key_commit=CORE,
        frozen_inputs=inputs,primary_raw=dict(path='raw_hold/kvx_timetable.bin',sha256=EXPECTED_RAW,size_bytes=len(body),publication='LOCAL_HOLD'),
        core_airport_keys_sha256=hashlib.sha256(corebytes).hexdigest(),base_operating_input_set_id=basemf['input_set_id'],
        base_operating_output_manifest_sha256=hashlib.sha256(subprocess.check_output(['git','show',CORE+':'+COREBASE+'operating/output_manifest.json'])).hexdigest(),
        inherited_quarantine='Use core b264780 operating/quarantine.csv and safe OMS overlay; no legacy source helper bypass',
        validation=dict(primary_blocks_match=6,dated_instances_replayed=12,timezone_offsets_match=True,operating_marketing_roles_not_promoted=True,rollover_assumption_retained=True),
        scope='Separate input set after base b264780. Does not mutate core base/a875 or any previous experiment. No night-product/OD/yield/capacity acceptance.',
        files=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size_bytes=p.stat().st_size) for p in sorted((ROOT/'outputs').iterdir()) if p.is_file()])
    (ROOT/'output_manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(input_set_id=inputset,primary_rule_cells=6,dated_instances=12,outbound_week_candidates=sum(r['departure_window_role']=='OUTBOUND_CANDIDATE_07_13' for r in generated),output_manifest_sha256=hashlib.sha256((ROOT/'output_manifest.json').read_bytes()).hexdigest()),ensure_ascii=False))
if __name__=='__main__':main()
