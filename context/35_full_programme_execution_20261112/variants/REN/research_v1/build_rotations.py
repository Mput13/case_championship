"""Датированные операционные прототипы; не подтверждение ресурсов RW/допуска SJ100."""
from pathlib import Path
import csv,json,datetime as dt,hashlib
from collections import defaultdict
R=Path(__file__).resolve().parent
UTC=dt.timezone.utc
OFFSETS={'REN':5,'SVX':5,'GOJ':3,'MRV':3,'OMS':6,'EVN':4}
BLOCK={frozenset(x[:2]):x[2] for x in [('REN','SVX',95),('REN','GOJ',105),('REN','MRV',170),('REN','OMS',150),('REN','EVN',185),('SVX','GOJ',120),('SVX','MRV',210)]}
F=[]
def add(pid,week,tail,date,start,path,gaps=None):
    now=dt.datetime.combine(date,dt.time.fromisoformat(start),UTC)
    for n,(a,b) in enumerate(zip(path,path[1:])):
        elapsed=160 if (a,b)==('EVN','REN') else BLOCK[frozenset([a,b])]
        end=now+dt.timedelta(minutes=elapsed)
        fid=f'{pid}:{date.isoformat()}:{tail}:{n+1}'
        F.append(dict(programme_id=pid,week=week,aircraft_id=tail,flight_instance_id=fid,schedule_id='REN-local-diagnostic-v1',
            operator='RW_SCENARIO_NOT_RESOURCE_CONFIRMED',flight_number='PROPOSED',origin_airport=a,destination_airport=b,
            departure_utc=now.isoformat().replace('+00:00','Z'),arrival_utc=end.isoformat().replace('+00:00','Z'),
            departure_local=now.astimezone(dt.timezone(dt.timedelta(hours=OFFSETS[a]))).isoformat(),
            arrival_local=end.astimezone(dt.timezone(dt.timedelta(hours=OFFSETS[b]))).isoformat(),
            aircraft_variant='RRJ95LR_100_analogue_DIAGNOSTIC',seats=100,technical_blocked_seats='UNKNOWN',saleable_seats='UNKNOWN',
            block_minutes=elapsed,physical_adjacent_leg=True,scheduled_status='proposed',source_status='scenario_analogue',
            source_period='representative_weeks_2028_only',crew_id='UNKNOWN',
            assumption_id='A-REN-02;A-REN-03;A-REN-05;A-REN-06;A-REN-07;A-REN-08;A-REN-18;A-REN-19',
            source_id='programme_candidates.json;REN-SCHEDULE-OUT;REN-GOJ-RGK26;P03',
            unit='physical flight;minutes;nominal seats;UTC',period=week,
            coverage='diagnostic proposal; no real tail/free seats/crew/certification; not annual network',status='conditional_design'))
        if n<len(path)-2:now=end+dt.timedelta(minutes=(gaps[n] if gaps else 60))

WEEKS=['2028-02-14','2028-04-17','2028-07-17','2028-11-13']
for w in WEEKS:
    monday=dt.date.fromisoformat(w);assert monday.weekday()==0
    for day in range(6):
        d=monday+dt.timedelta(days=day);x='GOJ' if day%2==0 else 'MRV'
        # Одинаковый local продукт R1/E1: вылет REN11:30 и тот же return.
        add('CP-REN-R1',w,'G1-T1',d,'06:30',['REN',x,'REN'])
        add('CP-REN-E1',w,'G1-T1',d,'03:55',['SVX','REN',x,'REN','SVX'])
        add('CP-REN-D1',w,'G1-T1',d,'02:00',['SVX',x,'SVX'])
        add('CP-REN-R2',w,'G1-T1',d,'06:30',
            ['REN','GOJ','REN','OMS','REN'] if x=='GOJ' else ['REN','MRV','REN'])
        if day%2==0:
            add('CP-REN-H1',w,'G2-T1',d,'07:25',['SVX','REN','MRV','REN','SVX'],[90,60,90])
            add('CP-REN-H1',w,'G2-T2',d,'06:30',['OMS','REN','GOJ','REN','OMS'],[90,190,90])
            # Тот же состав физических рейсов и мест; разнести T2 на три часа.
            add('CP-REN-H1-U',w,'G2-T1',d,'07:25',['SVX','REN','MRV','REN','SVX'],[90,60,90])
            add('CP-REN-H1-U',w,'G2-T2',d,'09:30',['OMS','REN','GOJ','REN','OMS'],[90,190,90])
    if monday.month==7:
        # X1 — конфликтует с четвергом R1/E1. Отдельный альтернативный кусок, не append.
        add('CP-REN-X1',w,'G1-T1',monday+dt.timedelta(days=3),'06:10',['REN','EVN','REN'],[50])

def savecsv(name,rows):
    with (R/name).open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
savecsv('rotation_templates.csv',F)
groups=defaultdict(list)
for f in F:groups[(f['programme_id'],f['week'],f['aircraft_id'])].append(f)
checks=[];resources=[]
for (pid,week,tail),rows in groups.items():
    rows.sort(key=lambda x:x['departure_utc']);bad=[];gaps=[]
    for prev,nxt in zip(rows,rows[1:]):
        gap=(dt.datetime.fromisoformat(nxt['departure_utc'])-dt.datetime.fromisoformat(prev['arrival_utc'])).total_seconds()/60
        gaps.append(gap)
        if gap<0 or prev['destination_airport']!=nxt['origin_airport']:bad.append([prev['flight_instance_id'],nxt['flight_instance_id'],gap])
    days=defaultdict(list)
    for x in rows:days[x['departure_utc'][:10]].append(x)
    maxspan=max((dt.datetime.fromisoformat(x[-1]['arrival_utc'])-dt.datetime.fromisoformat(x[0]['departure_utc'])).total_seconds()/60 for x in days.values())
    maxblock=max(sum(y['block_minutes'] for y in x) for x in days.values())
    resources.append(dict(programme_id=pid,week=week,aircraft_id=tail,line_tails_in_this_rotation=1,
        flight_segments=len(rows),nominal_segment_seats=len(rows)*100,block_hours=sum(x['block_minutes'] for x in rows)/60,
        max_block_minutes_per_UTC_day=maxblock,max_service_span_minutes_per_UTC_day=maxspan,
        minimum_gap_minutes=min(gaps) if gaps else 'UNKNOWN',crew_legal='UNKNOWN',MRO='UNKNOWN',reserve='UNKNOWN',
        airport_slot='UNKNOWN',required_overnight_airport=rows[0]['origin_airport'],unit='tails;seats/segment;block hours;minutes',
        period=week,coverage='only this explicit diagnostic week; no annualization',status='no_overlap_only' if not bad else 'invalid',
        source_id='rotation_templates.csv',assumption_id='A-REN-03;A-REN-07;A-REN-08;A-REN-09;A-REN-18'))
    checks.append(dict(programme_id=pid,week=week,tail=tail,continuity_and_no_overlap='PASS' if not bad else 'FAIL',errors=bad))
savecsv('resource_diagnostics.csv',resources)

# P06-schema-compatible subset: no fake complete bundle, no fabricated financial/demand fields.
fields=['flight_instance_id','schedule_id','operator','flight_number','origin_airport','destination_airport','departure_utc','arrival_utc','aircraft_variant','seats','physical_adjacent_leg','scheduled_status','source_status','source_period','assumption_id']
(R/'producer_fragment.json').write_text(json.dumps(dict(
    fragment_version='REN-StageA-1',status='INCOMPLETE_NOT_ENGINE_INPUT',
    contract_commit='982f13d9b6c378ed9581125ecc5c40f17dade6a3',
    flights=[{k:x[k] for k in fields} for x in F],
    template_assignments=[{k:x[k] for k in ['flight_instance_id','aircraft_id','crew_id','assumption_id']} for x in F],
    null_fields=['saleable_seats','technical_blocked_seats','real tail','crew_windows','resource availability','fleet_calendar','contracts','markets','choice_model','costs','cash','future_KEEP'],
    programme_control='CP-REN-H1-U: те же flights/counts/номинальные seats, T2 +180мин. Самостоятельный economic comparator требует полного joint recompute.',
    blockers='Не подавать как complete P06 bundle. Поля UNKNOWN и текстовые список null_fields — описания отсутствий; ни один реальный null не заменен нулем.'
),ensure_ascii=False,indent=2)+'\n')

connections=[]
for pid in ['CP-REN-H1','CP-REN-H1-U']:
    for w in WEEKS:
        rows=[x for x in F if x['programme_id']==pid and x['week']==w]
        for date in sorted({x['departure_utc'][:10] for x in rows}):
            today=[x for x in rows if x['departure_utc'].startswith(date)]
            for a,b in [('SVX','GOJ'),('SVX','MRV'),('OMS','GOJ'),('OMS','MRV'),('GOJ','SVX'),('GOJ','OMS'),('MRV','SVX'),('MRV','OMS')]:
                ins=[x for x in today if x['origin_airport']==a and x['destination_airport']=='REN']
                outs=[x for x in today if x['origin_airport']=='REN' and x['destination_airport']==b]
                if not(ins and outs):continue
                gap=(dt.datetime.fromisoformat(outs[0]['departure_utc'])-dt.datetime.fromisoformat(ins[0]['arrival_utc'])).total_seconds()/60
                connections.append(dict(programme_id=pid,date=date,origin=a,via='REN',destination=b,inbound=ins[0]['flight_instance_id'],outbound=outs[0]['flight_instance_id'],
                    connection_minutes=gap,meets_test_MCT90=gap>=90,departure_after_arrival=gap>=0,
                    total_elapsed_minutes=ins[0]['block_minutes']+gap+outs[0]['block_minutes'] if gap>=0 else 'NO_SAME_DAY',
                    max_connection_policy='UNKNOWN; 90 is minimum diagnostic, longer wait evaluated by P05',protected_sale='UNKNOWN',
                    unit='minutes;journey uses two segment inventories;one fare',period=date,coverage='mechanical same-day only;not a sellable itinerary',
                    status='conditional_connection' if gap>=90 else 'missed_same_day_test',source_id='rotation_templates.csv',assumption_id='A-REN-04;A-REN-07'))
savecsv('connection_diagnostics.csv',connections)

# 7/14 ночей: календарное наличие обратных legs, не кресла/билет/места в гостинице.
night_checks=[]
for pid in ['CP-REN-R1','CP-REN-E1','CP-REN-D1','CP-REN-R2','CP-REN-H1']:
    night_checks.append(dict(programme_id=pid,weekdays='1,3,5 и/или2,4,6 по одному и тому же недельному шаблону',
        exact_7_and_14_night_return='conditional_calendar_PASS_if_template_repeated',
        basis='совпадает день недели исходящего и обратного направления; действительность сезона/исключения/seat sale UNKNOWN',
        source_id='rotation_templates.csv',assumption_id='A-REN-02;A-REN-18',status='calendar_only'))
summary={
 'status':'PASS_NO_OVERLAP_AND_LOCATION_CONTINUITY_ONLY',
 'checks':checks,'rows':len(F),'resource_group':'G1 same1 line-tail;G2 same2 line-tails;actual reserve/crew not supplied',
 'economic_run':'NOT_RUN','P06_run':'NOT_RUN',
 'limits':['UTC-day service span is not legal crew duty: report/check-in/rest and crew changes unknown',
           'No actual maintenance/reserve availability accepted; empty Sunday is not evidence of MRO access',
           'H1-T2 needs190min GOJ ground hold to align reverse wave; cost/crew/slot consequences not zero',
           'R2/H1 have long days. Aircraft nonoverlap does not admit crew/TO or prove shortest resource solution',
           'Four sampled weeks remain four weeks, not 2027/28 annual schedule',
           'SJ100_PD8 run NOT_RUN; current SSJ100 analogue cannot certify new variant'],
 'calendar_return_checks':night_checks,
 'nominal_capacity_rule':'100 per segment diagnostic only; each connecting journey consumes two inventories; no demand/capture computed'}
assert all(x['continuity_and_no_overlap']=='PASS' for x in checks)
assert all(x['connection_minutes']==90 for x in connections if x['programme_id']=='CP-REN-H1')
# Прямой независимый контрпример: после сдвига T2 некоторые связи теряются.
assert any(not x['departure_after_arrival'] for x in connections if x['programme_id']=='CP-REN-H1-U')
(R/'resource_checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print('Diagnostic flights',len(F),'tail-weeks',len(checks),'connections',len(connections))
