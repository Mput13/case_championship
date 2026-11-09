#!/usr/bin/env python3
"""C07 source-clock and resource oracle on frozen references, no peer model."""
import csv
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parent
RAW=BASE/'raw/frozen-001/inputs/core'

def read(path):return list(csv.DictReader(path.open()))
def write(path,rows):
    with path.open('w',newline='')as f:
        writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)

def main():
    contract=json.loads((BASE/'frozen_contract.json').read_text());sc=contract['frozen_scenarios']
    rows=read(RAW/'omsk_domestic_timetable_rows.csv');zones={r['iata_code']:r['iana_timezone']for r in read(RAW/'airport_timezone_join.csv')}
    rw=next(r for r in rows if r['source_text_line']=='68');fv=next(r for r in rows if r['source_text_line']=='79')
    specifications=[('SVX','OMS',rw,'preceding_origin_departure_local_raw','omsk_arrival_local_raw'),('OMS','SVX',rw,'omsk_departure_local_raw','onward_arrival_local_raw'),('KJA','OMS',fv,'preceding_origin_departure_local_raw','omsk_arrival_local_raw'),('OMS','KJA',fv,'omsk_departure_local_raw','onward_arrival_local_raw')]
    blocks=[]
    # Minimum positive clock interval is an explicitly derived timing proxy.
    # It cannot establish an operating flight, approved SSJ duration or date/slot.
    for origin,destination,row,depfield,arrfield in specifications:
        depclock=row[depfield].replace('.',':');arrclock=row[arrfield].replace('.',':')
        dep=dt.datetime.fromisoformat('2026-12-08T'+depclock).replace(tzinfo=ZoneInfo(zones[origin]))
        options=[]
        for offset in range(3):
            day=dep.date()+dt.timedelta(days=offset);arr=dt.datetime.fromisoformat(day.isoformat()+'T'+arrclock).replace(tzinfo=ZoneInfo(zones[destination]))
            minutes=int((arr.astimezone(dt.timezone.utc)-dep.astimezone(dt.timezone.utc)).total_seconds()/60)
            if minutes>0:options.append((minutes,offset))
        duration,offset=min(options)
        blocks.append(dict(origin=origin,destination=destination,source_text_line=row['source_text_line'],carrier_raw=row['carrier_raw'],published_departure_clock=depclock,published_arrival_clock=arrclock,origin_zone=zones[origin],destination_zone=zones[destination],positive_elapsed_proxy_minutes=duration,inferred_arrival_day_offset=offset,value_status='DERIVED',derivation='Minimum positive elapsed from clocks; not RW clearance',tail_assignment='UNKNOWN',source_scope='Endpoint schedule clocks; no independent nonstop or performance acceptance'))
    b={(r['origin'],r['destination']):r['positive_elapsed_proxy_minutes']for r in blocks}
    grid=[]
    for turn in sc['turn_minutes']:
        rt=b['SVX','OMS']+b['OMS','SVX']+turn
        chain=sum(b.values())+3*turn
        for window in sc['aircraft_window_minutes']:
            grid.append(dict(turn_scenario_minutes=turn,aircraft_elapsed_window_scenario_minutes=window,RT_elapsed_minutes=rt,chain_elapsed_minutes=chain,extra_elapsed_minutes=chain-rt,chain_within_window=chain<=window,slack_minutes=window-chain,nominal_chain_route='SVX-OMS-KJA-OMS-SVX',initial_final_airport_equal=True,actual_tail_available='UNKNOWN',crew_duty_legal='UNKNOWN',slot_dates='UNKNOWN',value_status='SCENARIO'))
    # One source dated at OMS plus independent SVX weekday corroboration.
    svx=next(r for r in read(RAW/'svx_published_schedule_rules.csv')if r['origin_airport_iata']=='SVX'and r['destination_airport_iata']=='OMS'and r['flight_number_raw']=='WZ-5071')
    source_days=set(map(int,rw['weekdays_raw'].split(',')));origin_days=set(map(int,svx['weekdays_iso'].split(';')))
    assert {(d%7)+1 for d in origin_days}==source_days
    dated=[]
    for k in range(7):
        omsday=dt.date(2026,12,7)+dt.timedelta(days=k)
        if omsday.isoweekday() not in source_days:continue
        origin_date=omsday-dt.timedelta(days=1)
        times=[dt.datetime.fromisoformat(origin_date.isoformat()+'T21:20').replace(tzinfo=ZoneInfo(zones['SVX'])),dt.datetime.fromisoformat(omsday.isoformat()+'T00:00').replace(tzinfo=ZoneInfo(zones['OMS'])),dt.datetime.fromisoformat(omsday.isoformat()+'T00:50').replace(tzinfo=ZoneInfo(zones['OMS'])),dt.datetime.fromisoformat(omsday.isoformat()+'T01:35').replace(tzinfo=ZoneInfo(zones['SVX']))]
        elapsed=int((times[-1].astimezone(dt.timezone.utc)-times[0].astimezone(dt.timezone.utc)).total_seconds()/60)
        dated.append(dict(SVX_departure_local=times[0].isoformat(),OMS_arrival_local=times[1].isoformat(),OMS_departure_local=times[2].isoformat(),SVX_arrival_local=times[3].isoformat(),elapsed_reference_minutes=elapsed,source_OMS_text_line=68,source_SVX_table_row=svx['source_table_row'],weekday_bridge='SVX Tue/Fri +1day = OMS Wed/Sat; conditional alignment',SVX_source_year='UNKNOWN_IN_SVX_ROW; explicit2026period from OMS reference',remote_origin_day_assumption='Previous local day; not directly dated by source',dated_service_admission='UNKNOWN_UNCONFIRMED_REMOTE_DAY_ASSIGNMENT',marketing_operating_code_mapping='UNKNOWN',same_tail_assumption='SCENARIO; no assignment observed',value_status='SCENARIO'))
    write(BASE/'C07_clock_proxies.csv',blocks);write(BASE/'C07_resource_oracle.csv',grid);write(BASE/'C07_dated_reference.csv',dated)
    out=dict(source_rows=[68,79],blocks_minutes={a+'-'+b:v for (a,b),v in b.items()},dated_reference_elapsed_minutes=[r['elapsed_reference_minutes']for r in dated],reference_turn_from_published_clocks_minutes=50,scenario_chain_elapsed_minutes=sorted({r['chain_elapsed_minutes']for r in grid}),resource_grid_rows=len(grid),within_window_rows=sum(r['chain_within_window']for r in grid),scope='Timing/reference and scenario arithmetic only; FV carrier clocks do not clear RW SSJ, actual donor/free resource/crew/slots/market UNKNOWN')
    (BASE/'C07_reference_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
