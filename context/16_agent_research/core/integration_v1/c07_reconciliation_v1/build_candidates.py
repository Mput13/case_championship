#!/usr/bin/env python3
"""Bounded conditional calendar test on frozen C07 records, no acceptance lift.

The SVX source omits year. Candidate dates require an explicit same-local-turn-date
association to OMS inbound/outbound columns. This assumption does not amend the
base rule or prove a passenger product, donor tail, MCT or operating continuity.
"""
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
PIN='b264780e65a0e04afd42da811652039c70fc1def'
BASE='context/16_agent_research/core/integration_v1/operating/'
def load(name):
    b=subprocess.check_output(['git','show',PIN+':'+BASE+name]);return b,list(csv.DictReader(io.StringIO(b.decode())))
def write(name,rows):
    with (ROOT/name).open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    rb,rules=load('service_rules.csv');db,dates=load('dated_instances.csv');byid={r['service_rule_id']:r for r in rules}
    svx=next(r for r in rules if r['source_id']=='svx_schedule' and r['destination_iata']=='OMS')
    outbound_return=next(r for r in rules if r['source_id']=='omsk_winter_2026' and r['source_row']=='68:OUT')
    inbound=next(r for r in rules if r['source_id']=='omsk_winter_2026' and r['source_row']=='68:IN')
    onward=next(r for r in rules if r['source_id']=='omsk_winter_2026' and r['source_row']=='79:OUT')
    assert svx['year_status']=='UNKNOWN' and inbound['weekday_basis'].startswith('OMS_TURN_DATE')
    assert svx['arrival_day_offset']=='1'
    assert svx['departure_local']==inbound['departure_local'] and svx['arrival_local']==inbound['arrival_local']
    assert '5071' in svx['source_flight_label'] and '5071' in inbound['source_flight_label']
    anchors=[d for d in dates if d['service_rule_id']==outbound_return['service_rule_id'] and d['departure_date_local']<='2026-12-13']
    after=[d for d in dates if d['service_rule_id']==onward['service_rule_id'] and d['departure_date_local']<='2026-12-13']
    assert len(anchors)==len(after)==2
    month_number={'янв':1,'фев':2,'мар':3,'апр':4,'май':5,'июн':6,'июл':7,'авг':8,'сен':9,'окт':10,'ноя':11,'дек':12}
    bounds=re.findall(r'(\d{1,2})\s+([а-я]{3})',svx['period_raw'])
    assert len(bounds)==2
    month_day=[(month_number[m],int(d)) for d,m in bounds]
    candidates=[];resources=[]
    for anchor in anchors:
        omsdate=dt.date.fromisoformat(anchor['departure_date_local']);origin_date=omsdate-dt.timedelta(days=1)
        assert str(origin_date.isoweekday()) in svx['weekdays_iso'].split(';')
        # These candidates lie within the source's day/month range, but its year stays unknown.
        assert month_day[0]<=(origin_date.month,origin_date.day)<=month_day[1]
        dep=dt.datetime.fromisoformat(origin_date.isoformat()+'T'+svx['departure_local']).replace(tzinfo=ZoneInfo(svx['origin_iana']))
        arr=dt.datetime.fromisoformat(omsdate.isoformat()+'T'+svx['arrival_local']).replace(tzinfo=ZoneInfo(svx['destination_iana']))
        arrutc=arr.astimezone(dt.timezone.utc)
        nextdep=min((x for x in after if dt.datetime.fromisoformat(x['departure_utc'])>=arrutc),key=lambda x:x['departure_utc'])
        gap=int((dt.datetime.fromisoformat(nextdep['departure_utc'])-arrutc).total_seconds()/60)
        cid='C07-CALENDAR-CANDIDATE:'+origin_date.isoformat()
        candidates.append(dict(candidate_id=cid,source_commit=PIN,first_leg='SVX→OMS',second_leg='OMS→KJA',
            svx_rule_id=svx['service_rule_id'],omsk_inbound_rule_id=inbound['service_rule_id'],omsk_anchor_instance_id=anchor['instance_id'],next_departure_instance_id=nextdep['instance_id'],
            scenario_svx_departure_local=dep.isoformat(),scenario_omsk_arrival_local=arr.isoformat(),published_onward_departure_local=nextdep['departure_local'],
            published_onward_date=nextdep['departure_date_local'],gap_minutes_conditional=gap,gap_value_status='DERIVED',
            source_svx_year_status='UNKNOWN',candidate_value_status='SCENARIO',
            explicit_condition='Inbound OMS00:00 belongs to the same local turn date as paired OMS00:50 departure; SVX year anchored by that dated source',
            source_first_carrier_label=svx['source_carrier_label'],source_onward_carrier_label=onward['source_carrier_label'],
            minimum_connection_time='UNKNOWN',one_ticket='UNKNOWN',baggage_transfer='UNKNOWN',actual_operating_entities='UNKNOWN',
            acceptance='NOT_ADMITTED_OPERATING_SERVICE; CONDITIONAL_CALENDAR_TEST_ONLY'))
        minutes_to_return=int((dt.datetime.fromisoformat(anchor['departure_utc'])-arrutc).total_seconds()/60)
        resources.append(dict(candidate_id=cid,published_linked_return_instance_id=anchor['instance_id'],published_linked_return_origin='OMS',published_linked_return_destination='SVX',
            return_departure_date_local=anchor['departure_date_local'],return_departure_local=anchor['departure_local'],minutes_after_scenario_inbound=minutes_to_return,
            clock_gap_value_status='DERIVED',clock_gap_condition='Under calendar_candidates explicit same-local-turn-date SCENARIO condition',
            hypothetical_onward_rule_id=onward['service_rule_id'],source_onward_carrier_label=onward['source_carrier_label'],
            same_tail_as_inbound='UNKNOWN',donor_for_replacement='UNKNOWN_NOT_SELECTED',free_aircraft='UNKNOWN',
            keep_replace_remove_baseline='NOT_VERIFIED; paired return is evidence to investigate, not an admitted donor',
            acceptance='NO_FREE_RESOURCE_OR_AIRCRAFT_CONTINUITY_INFERRED'))
    write('calendar_candidates.csv',candidates);write('resource_constraints.csv',resources)
    assert sorted(r['gap_minutes_conditional'] for r in candidates)==[90,4410]
    assert all(r['minutes_after_scenario_inbound']==50 for r in resources)
    inputs=[dict(path=BASE+n,source_commit=PIN,sha256=hashlib.sha256(b).hexdigest()) for n,b in [('service_rules.csv',rb),('dated_instances.csv',db)]]
    data=dict(version='c07-conditional-calendar-v1',source_commit=PIN,input_set_id='CORE-C07-CONDITIONAL:'+hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest(),
        inputs=inputs,conditions='Explicit same-OMS-local-turn-date assumption; SVX source year unchanged UNKNOWN',
        output_files=[dict(path=n,sha256=hashlib.sha256((ROOT/n).read_bytes()).hexdigest()) for n in ['calendar_candidates.csv','resource_constraints.csv']],
        validation=dict(candidate_rows=2,conditional_gaps_minutes=[4410,90],published_linked_return_departure_gap_minutes=50,source_rule_not_modified=True),
        acceptance='CONDITIONAL CALENDAR ARITHMETIC ONLY; no donor/aircraft/MCT/ticket/interline/product/economics/OD acceptance')
    (ROOT/'output_manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(data['validation']))
if __name__=='__main__':main()
