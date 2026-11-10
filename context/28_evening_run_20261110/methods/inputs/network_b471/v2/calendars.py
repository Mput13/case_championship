#!/usr/bin/env python3
"""Dated diagnostic rotations. No real tail allocation or crew-duty approval inferred."""
from datetime import datetime, timedelta, timezone
import math
import calculate as calc

UTC=timezone.utc
OFFSETS={'KUF':4,'SVX':5,'OMS':6,'KJA':7,'ARH':3,'NJC':5,'MRV':3,'UFA':5,
         'GOJ':3,'NOZ':7,'GSV':4,'TOF':7,'VOG':3}


def local(t, airport):
    return t.astimezone(timezone(timedelta(hours=OFFSETS[airport]))).isoformat()


def leg(network,variant,tail,number,a,b,dep,minutes,status,source='', identity=''):
    arr=dep+timedelta(minutes=minutes)
    return dict(network=network,variant=variant,tail_scenario=tail,
                flight_id=identity or f'{network}_{tail}_{dep:%Y%m%dT%H%M}_{a}_{b}',
                flight_number=number,origin=a,destination=b,
                service_date=local(dep,a)[:10],departure_utc=dep.isoformat(),arrival_utc=arr.isoformat(),
                departure_local=local(dep,a),arrival_local=local(arr,b),block_minutes=minutes,
                aircraft='SSJ100/RRJ95 100-seat scenario analog; not SJ100 operating approval',
                seats=100,source_id=source,schedule_status=status)


def fixed_rotations():
    allrows=[];summaries=[]
    defs=[('KUF4','KUF',['ARH','OMS','NJC','MRV'],1),
          ('OMS1','OMS',['KJA'],1),('OMS4','OMS',['KJA','KUF','GOJ','NOZ'],1),
          ('OMS8','OMS',['KJA','KUF','GOJ','NOZ','GSV','UFA','TOF','VOG'],2)]
    for network,hub,spokes,tails in defs:
        tasks=[(x,125,145) if (hub,x)==('OMS','KJA') else
                      (x,math.ceil(calc.flight(hub,x,'base')[0]*60),math.ceil(calc.flight(x,hub,'base')[0]*60))
                      for x in spokes]
        if len(tasks)==1:
            bins=[[],[tasks[0]],[],[],[tasks[0]],[],[]]  # Tue/Fri, not adjacent days
        else:
            bins=[]
            for group in [tasks[i:i+4] for i in range(0,len(tasks),4)]:
                short1,short2,long1,long2=sorted(group,key=lambda x:x[1]+x[2])
                bins.extend([[short1,short2],[long1],[long2],[short2],[short1],[long1],[long2]])
        assert len(bins)==tails*7
        for day in bins:
            bh=sum(v+w for _,v,w in day)
            assert bh<=600 and bh+45*(2*len(day)-1)<=840
        for i,day in enumerate(bins):
            tail=f'{hub}_T{i//7+1}';date=datetime(2026,12,7,tzinfo=UTC)+timedelta(days=i%7,hours=4)
            dep=date
            for j,(x,m,n) in enumerate(day):
                out=leg(network,'diagnostic',tail,'PROPOSED',hub,x,dep,m,'DIAGNOSTIC_NOT_PUBLISHED')
                allrows.append(out);dep=datetime.fromisoformat(out['arrival_utc'])+timedelta(minutes=45)
                back=leg(network,'diagnostic',tail,'PROPOSED',x,hub,dep,n,'DIAGNOSTIC_NOT_PUBLISHED')
                allrows.append(back);dep=datetime.fromisoformat(back['arrival_utc'])+timedelta(minutes=45)
            if day:
                summaries.append(dict(network=network,tail_scenario=tail,date=date.date().isoformat(),
                                      rotations=len(day),block_minutes=sum(m+n for _,m,n in day),
                                      elapsed_minutes=(dep-date).total_seconds()/60-45,
                                      location_start=hub,location_end=hub,
                                      reserve='not allocated; pooled cover/maintenance release UNKNOWN',
                                      crew='10bh/day and14h span are diagnostic caps, not regulatory duty clearance'))
    return allrows,summaries


def c01():
    rows=[];connections=[]
    for day in [7,11]:
        for variant in ['sync','unsync']:
            d=datetime(2026,12,day,tzinfo=UTC)
            southstart=10 if variant=='sync' else 8
            southreturn=13*60+35 if variant=='sync' else 11*60+20
            pattern=[('NORTH','NJC','UFA',390,150),('SOUTH','UFA','MRV',southstart*60,155),
                     ('SOUTH','MRV','UFA',southreturn,140),('NORTH','UFA','NJC',16*60+55,145)]
            rr=[leg('C01',variant,t,'PROPOSED',a,b,d+timedelta(minutes=m),h,'DIAGNOSTIC_SOURCE_CLOCK_PROXY',
                    'owner4a976 RPC029/055/054/027') for t,a,b,m,h in pattern]
            rows.extend(rr)
            for a,b in [(rr[0],rr[1]),(rr[2],rr[3])]:
                wait=(datetime.fromisoformat(b['departure_utc'])-datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
                for mct in [45,60,90]:
                    connections.append(dict(network='C01',variant=variant,service_date=d.date().isoformat(),
                                            origin=a['origin'],destination=b['destination'],wait_minutes=wait,
                                            min_connection_minutes=mct,max_connection_minutes=180,
                                            passes=mct<=wait<=180,legs=a['flight_id']+';'+b['flight_id'],
                                            protection='single ticket/through baggage/recovery cost UNKNOWN'))
    return rows,connections


def c07():
    rows=[];nexts=[]
    for day in [8,11]:
        start=datetime(2026,12,day,16,20,tzinfo=UTC)
        for turn in [None,30,45,60]:
            variant='KEEP' if turn is None else 'turn'+str(turn)
            rr=[leg('C07',variant,'SVX_T1','WZ5071','SVX','OMS',start,100,
                    'PUBLISHED_REFERENCE' if turn is None else 'DIAGNOSTIC_CHANGE','svx_dep;oms_winter')]
            if turn is None:
                dep=datetime.fromisoformat(rr[-1]['arrival_utc'])+timedelta(minutes=50)
            else:
                dep=datetime.fromisoformat(rr[-1]['arrival_utc'])+timedelta(minutes=turn)
                rr.append(leg('C07',variant,'SVX_T1','PROPOSED','OMS','KJA',dep,125,'DIAGNOSTIC_PROXY','oms_winter FV6846'))
                dep=datetime.fromisoformat(rr[-1]['arrival_utc'])+timedelta(minutes=turn)
                rr.append(leg('C07',variant,'SVX_T1','PROPOSED','KJA','OMS',dep,145,'DIAGNOSTIC_PROXY','oms_winter FV6845'))
                dep=datetime.fromisoformat(rr[-1]['arrival_utc'])+timedelta(minutes=turn)
            rr.append(leg('C07',variant,'SVX_T1','WZ5072','OMS','SVX',dep,105,
                          'PUBLISHED_REFERENCE' if turn is None else 'DIAGNOSTIC_CHANGE','oms_winter;svx_arr'))
            rows.extend(rr)
            if turn is not None:
                ready=datetime.fromisoformat(rr[-1]['arrival_utc'])+timedelta(minutes=turn)
                # WZ5049 Wed07:25 SVX-REN is a real published opportunity, not an assigned donor.
                next_dep=datetime(2026,12,day+1,2,25,tzinfo=UTC)
                nexts.append(dict(network='C07',variant=variant,day=(start+timedelta(days=1)).date().isoformat(),
                                  ready_SVX_local=local(ready,'SVX'),published_opportunity='WZ5049 SVX-REN07:25 Wed only',
                                  applies_real_example=(day==8),slack_minutes=(next_dep-ready).total_seconds()/60,
                                  fits_if_assigned=ready<=next_dep,actual_tail_assignment='UNKNOWN',
                                  economic_rule='subtract net lost contribution only if this is actually the displaced assignment'))
    return rows,nexts


def c33():
    rows=[];connections=[];waits=[]
    for day in [8,11]:
        d=datetime(2026,12,day,tzinfo=UTC)
        for variant in ['KEEP','retime']:
            pattern=[('WZ1034','KUF','SVX',d+timedelta(hours=4),105,'kuf_dep;svx_arr'),
                     ('WZ5071','SVX','OMS',d+timedelta(hours=16,minutes=20) if variant=='KEEP' else d+timedelta(hours=7),100,'svx_dep;oms_winter'),
                     ('WZ5072','OMS','SVX',d+timedelta(hours=18,minutes=50) if variant=='KEEP' else d+timedelta(days=1,hours=14,minutes=55),105,'oms_winter;svx_arr'),
                     ('WZ1033','SVX','KUF',d+timedelta(days=1,hours=17,minutes=45),105,'svx_dep;kuf_arr')]
            rr=[leg('C33',variant,'SAME_TAIL_SCENARIO',n,a,b,t,m,
                    'PUBLISHED_REFERENCE' if variant=='KEEP' else 'DIAGNOSTIC_RETIMING_SAME_ID_DATE',source,
                    identity=f'{n}_{local(t,a)[:10]}_{a}_{b}') for n,a,b,t,m,source in pattern]
            rows.extend(rr)
            for a,b in [(rr[0],rr[1]),(rr[2],rr[3])]:
                wait=(datetime.fromisoformat(b['departure_utc'])-datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
                for mct in [45,60,90]:
                    connections.append(dict(network='C33',variant=variant,origin=a['origin'],destination=b['destination'],
                                            service_date=a['service_date'],wait_minutes=wait,min_connection_minutes=mct,
                                            max_connection_minutes=180,passes=mct<=wait<=180,
                                            legs=a['flight_id']+';'+b['flight_id']))
            wait=(datetime.fromisoformat(rr[2]['departure_utc'])-datetime.fromisoformat(rr[1]['arrival_utc'])).total_seconds()/60
            waits.append(dict(network='C33',variant=variant,initial_date=d.date().isoformat(),OMS_wait_minutes=wait,
                              total_block_minutes=sum(x['block_minutes'] for x in rr),
                              rotation_elapsed_minutes=(datetime.fromisoformat(rr[-1]['arrival_utc'])-datetime.fromisoformat(rr[0]['departure_utc'])).total_seconds()/60,
                              next_KUF_departure_local=f'2026-12-{day+2:02d}T08:00:00+04:00',
                              next_turn_minutes=510,crew_rest='UNKNOWN; aircraft ground time is not crew clearance'))
    return rows,connections,waits


def main():
    fixed,resources=fixed_rotations();one,connect1=c01();seven,nexts=c07();thirtythree,connect33,waits=c33()
    deployed=[dict(r,network='KUF4_SVX_deployed',tail_scenario='DEPLOYED_SVX_T1',
                   flight_id='DEPLOYED_'+r['flight_id']) for r in fixed if r['network']=='KUF4']
    ferry_min=math.ceil(calc.flight('SVX','KUF','base')[0]*60)
    deployed=[leg('KUF4_SVX_deployed','diagnostic','DEPLOYED_SVX_T1','EMPTY_FERRY','SVX','KUF',
                  datetime(2026,12,6,18,tzinfo=UTC),ferry_min,'DIAGNOSTIC_EMPTY_DEPLOYMENT')]+deployed+[
              leg('KUF4_SVX_deployed','diagnostic','DEPLOYED_SVX_T1','EMPTY_FERRY','KUF','SVX',
                  datetime(2026,12,13,16,tzinfo=UTC),ferry_min,'DIAGNOSTIC_EMPTY_DEPLOYMENT')]
    calc.write('dated_flights.csv',fixed+deployed+one+seven+thirtythree)
    calc.write('fixed_daily_resources.csv',resources)
    calc.write('dated_connections.csv',connect1+connect33)
    calc.write('C07_next_assignment.csv',nexts)
    calc.write('C33_tail_waits.csv',waits)
    calc.write('C33_next_assignment.csv',[
        dict(network='C33',variant='KEEP',date='2026-12-09',tail_ready_SVX_local='2026-12-09T02:20:00+05:00',
             published_opportunity='WZ5049SVX-REN07:25Wed',slack_minutes=305,
             actual_tail_assignment='UNKNOWN',rule='only charge its lost NET contribution if actually assigned'),
        dict(network='C33',variant='retime',date='2026-12-09',tail_ready_SVX_local='2026-12-09T22:25:00+05:00',
             published_opportunity='WZ5049SVX-REN07:25Wed',slack_minutes=-900,
             actual_tail_assignment='UNKNOWN',rule='retimed tail is at OMS during this opportunity; include net loss in L_changed_slots if assigned'),
    ])
    print(f'{len(fixed+deployed+one+seven+thirtythree)} flights; {len(connect1+connect33)} connection checks; all diagnostic/publication labels preserved')


if __name__=='__main__':
    main()
