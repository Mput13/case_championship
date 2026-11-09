#!/usr/bin/env python3
"""Offline, auditable scenario comparison. Python 3 standard library only.

No traffic is inferred from capacity. Demand, capture and yields are independent
scenario inputs. Dated itineraries consume capacity on every segment. B0 is never
resized to match A's hours. Output is an operating contribution, not net profit.
"""
import copy
import csv
import datetime as dt
import itertools
import json
import math
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'context/12_network_economics'
OLD=ROOT/'context/11_practical_screening'
GEO={r['iata']:r for r in json.loads((OLD/'coordinates.json').read_text())}
RULES=json.loads((OUT/'schedule_rules.json').read_text())
SOURCES={r['id']:r for r in json.loads((OUT/'sources.json').read_text())}
INPUT=json.loads((OUT/'inputs.json').read_text())
SEATS=INPUT['capacity_seats']
MARKETS={r['pair']:r for r in INPUT['markets']}
TZ={'GOJ':3,'OMS':6,'KUF':4,'MMK':3,'UFA':5,'AER':3,'VOG':3,'ARH':3,'MRV':3,'ZIA':3,'GSV':4,'SVX':5,'NJC':5}
RU=['пн','вт','ср','чт','пт','сб','вс']
MONTHS={x:i+1 for i,x in enumerate(['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'])}

def pair(a,b): return '-'.join(sorted([a,b]))
def distance(a,b):
    x,y=GEO[a],GEO[b]; la,lb=map(math.radians,[x['lat'],y['lat']]); dl=math.radians(y['lon']-x['lon'])
    return 12742*math.asin(min(1,math.sqrt(math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin(dl/2)**2)))
def dump(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(str(x).replace('|','/').replace('\n',' ') for x in r)+' |' for r in rows])
def datepart(t):
    if len(t)==10 and t[4]=='-':return dt.date.fromisoformat(t)
    d,m=t.split();m=MONTHS[m]; return dt.date(2026 if m>=10 else 2027,m,int(d))
def applies(r,d):
    lo,hi=map(datepart,r['period'].split(' / '))
    return lo<=d<=hi and (r['weekdays']=='ежедневно' or RU[d.weekday()] in r['weekdays'].split(', '))
def minutes(s):return int(s[:2])*60+int(s[3:5])
def published_block(r):
    v=minutes(r['arrival_local'])-minutes(r['departure_local'])+(TZ[r['origin']]-TZ[r['destination']])*60
    if '(+1)' in r['arrival_local']: v+=1440
    if v<=0: v+=1440
    assert 15<=v<=600,(r,v)
    return v

def calendar(start):
    rows={}; conflicts=[]
    for r in RULES:
        for day in range(7):
            date=dt.date.fromisoformat(start)+dt.timedelta(days=day)
            if not applies(r,date): continue
            key=(r['origin'],r['destination'],date.isoformat(),r['flight'])
            if key in rows:
                old=rows[key]
                if (old['departure_local'],old['arrival_local'])!=(r['departure_local'],r['arrival_local']):
                    conflicts.append(dict(week=start,key='/'.join(key),source1=old['source'],source2=r['source'],
                        times1=old['departure_local']+'→'+old['arrival_local'],times2=r['departure_local']+'→'+r['arrival_local']))
                # Use departure airport's publication if both ends publish.
                if r['source'][:3].upper()!=r['origin']:continue
            rows[key]=dict(r,date=date.isoformat(),block_minutes=published_block(r))
    return list(rows.values()),conflicts

def competition():
    allrows=[]; conflict=[]; result=[]
    fares=json.loads((OUT/'advertised_fares.json').read_text())
    for week in INPUT['calendar_weeks']:
        rows,cc=calendar(week);allrows+=rows;conflict+=cc
        for m in INPUT['markets']:
            a,b=m['pair'].split('-')
            for origin,dest in [(a,b),(b,a)]:
                rs=[r for r in rows if r['origin']==origin and r['destination']==dest]
                coverage=[s['id'] for s in SOURCES.values() if 'schedule_rows' in s and
                          ((s['id'].endswith('_arr') and s['id'][:3].upper()==dest) or
                           (not s['id'].endswith('_arr') and s['id'][:3].upper()==origin)) and
                          (s.get('coverage')!='route specific only' or pair(origin,dest)=='AER-UFA')]
                status='LISTED' if rs else ('NOT_LISTED_IN_PRIMARY_SNAPSHOT' if coverage else 'UNKNOWN_CURRENT_PRIMARY')
                count=Counter(r['carrier'] for r in rs)
                ff=[r for r in fares if pair(r['origin'],r['destination'])==m['pair']]
                result.append(dict(week=week,origin=origin,destination=dest,status=status,
                    departures=len(rs) if coverage or rs else '',rw_departures=sum(r['flight'].startswith('WZ-') for r in rs) if coverage or rs else '',
                    carriers='; '.join(f'{k}:{v}' for k,v in sorted(count.items())),
                    flights='; '.join(sorted({r['flight'] for r in rs})),
                    published_periods='; '.join(sorted({r['period'] for r in RULES if r['origin']==origin and r['destination']==dest})),
                    summer_2027='UNKNOWN',source_ids=';'.join(coverage),
                    comparable_fare_20kg_rub='',fare_status='NO_MATCHED_FINAL_QUOTE',
                    advertised_RW='; '.join(f"{r['origin']}→{r['destination']} {r['date']}: from {r['advertised_from_rub']}" for r in ff),
                    project_class=m['project_class'],demand_evidence=m['evidence']))
    csvout('competition.csv',result);csvout('published_flight_dates.csv',allrows)
    csvout('schedule_time_conflicts.csv',conflict)
    # Different airport sources can disagree on the date set as well as clocks.
    mismatch=[]
    for week in INPUT['calendar_weeks']:
        for m in INPUT['markets']:
            if not m['local_pair']:continue
            a,b=m['pair'].split('-')
            for origin,dest in [(a,b),(b,a)]:
                sr=defaultdict(set)
                for r in RULES:
                    if (r['origin'],r['destination'])!=(origin,dest):continue
                    for day in range(7):
                        d=dt.date.fromisoformat(week)+dt.timedelta(days=day)
                        if applies(r,d):sr[r['source']].add((r['flight'],d.isoformat()))
                if len(sr)>1 and len({tuple(sorted(x)) for x in sr.values()})>1:
                    mismatch.append(dict(week=week,origin=origin,destination=dest,
                        counts=';'.join(f'{s}:{len(v)}' for s,v in sr.items()),
                        source_date_sets=json.dumps({s:sorted(v) for s,v in sr.items()},ensure_ascii=False)))
    csvout('schedule_date_conflicts.csv',mismatch)
    return result

def block_inputs():
    out={}; detail=[]; current,_=calendar(INPUT['calendar_weeks'][-1])
    for m in INPUT['markets']:
        if not m['local_pair']:continue
        a,b=m['pair'].split('-')
        for x,y in [(a,b),(b,a)]:
            rr=[r for r in RULES if (r['origin'],r['destination'])==(x,y)]
            now=[r for r in current if (r['origin'],r['destination'])==(x,y)]
            ssj=[r for r in now if 'RRJ' in r['aircraft']] or [r for r in rr if 'RRJ' in r['aircraft']]
            jet=[r for r in now if any(t in r['aircraft'] for t in ['737','320','CRJ'])]
            chosen=ssj or jet
            # A dated SSJ flight outside the model week is still only a block-time analog.
            v=max(published_block(r) for r in chosen) if chosen else m['block_scenario_minutes']
            method='published_SSJ_analog' if ssj else ('published_other_jet_analog' if jet else 'SCENARIO_not_dispatch_plan')
            out[(x,y)]=v
            detail.append(dict(origin=x,destination=y,minutes=v,method=method,
                range_minutes=f'{round(v*.9)}–{round(v*1.2)}',source_ids=';'.join(sorted({r['source'] for r in chosen})),
                evidence_flights=';'.join(sorted({r['flight'] for r in chosen})),
                selection='maximum published SSJ time in reference week; otherwise dated SSJ analog; otherwise current other jet; otherwise scenario'))
    csvout('block_times.csv',detail)
    return out

BLOCK=block_inputs()
INCUMBENT,_=calendar(INPUT['calendar_weeks'][-1])
RW_DIRECT_FLIGHTS=Counter((r['origin'],r['destination']) for r in INCUMBENT if r['flight'].startswith('WZ-'))

def networks():
    old=json.loads((OLD/'inputs.json').read_text()); legs=[]
    def add(net,day,plane,a,b,start):
        v=BLOCK[(a,b)]
        legs.append(dict(network=net,day=day,aircraft=plane,origin=a,destination=b,
            departure_utc_minute=start,arrival_utc_minute=start+v,block_minutes=v,
            id=f'{net}-{day}-{len(legs)}'))
        return start+v+45
    for day in range(1,7):
        for i,p in enumerate(old['hub_pairs'],1):
            morning,afternoon=p if day%2 else p[::-1]
            # Same spokes, frequencies and alternating bank as the previous sketch.
            start=720-BLOCK[('GOJ',morning)]-45-BLOCK[(morning,'GOJ')]
            t=add('A',day,f'A{i}','GOJ',morning,start)
            add('A',day,f'A{i}',morning,'GOJ',t)
            t=add('A',day,f'A{i}','GOJ',afternoon,795)
            add('A',day,f'A{i}',afternoon,'GOJ',t)
        for net,extra in [('B0',False),('B',True)]:
            for i,cycle in enumerate(old['direct_cycles'],1):
                route=list(cycle if day%2 else cycle[::-1])
                if extra and i==2 and day<=4:
                    p=route.index('GSV'); route=route[:p+1]+['AER','GSV']+route[p+1:]
                t=300
                for a,b in zip(route,route[1:]): t=add(net,day,f'{net}{i}',a,b,t)
                if extra and i==3:
                    t=add(net,day,f'{net}{i}','SVX','OMS',t)
                    add(net,day,f'{net}{i}','OMS','SVX',t)
    csvout('project_flights.csv',legs)
    return legs

LEGS=networks()

def itineraries(net):
    legs=[r for r in LEGS if r['network']==net]; out=defaultdict(list)
    for r in legs:
        out[(r['origin'],r['destination'])].append(dict(day=r['day'],legs=[r['id']],transfer=False,wait=0))
    if net=='A':
        for a in legs:
            if a['destination']!='GOJ':continue
            for b in legs:
                if b['origin']!='GOJ' or a['day']!=b['day'] or a['origin']==b['destination']:continue
                wait=b['departure_utc_minute']-a['arrival_utc_minute']
                detour=(distance(a['origin'],'GOJ')+distance('GOJ',b['destination']))/distance(a['origin'],b['destination'])
                if 60<=wait<=240 and detour<=1.6:
                    out[(a['origin'],b['destination'])].append(dict(day=a['day'],legs=[a['id'],b['id']],transfer=True,wait=wait))
    return out

ITINS={net:itineraries(net) for net in ['A','B0','B']}
TRANSFER_KEYS={pair(a,b) for (a,b),its in ITINS['A'].items() if its[0]['transfer']}

def evaluate(net,scenario,transfer_scale=1,fare_scale=1,cost_scale=1,priority='local_first',demand_scale=1,can_scale=1,market_scales=None):
    p=copy.deepcopy(INPUT['scenarios'][scenario]); legs=[r for r in LEGS if r['network']==net]
    caps={r['id']:float(SEATS) for r in legs}; traffic=[]; offers=[]
    migration_left={key:n*100. for key,n in RW_DIRECT_FLIGHTS.items()} # incumbent RW SSJ configuration from the airline
    for (a,b),its in ITINS[net].items():
        market=MARKETS[pair(a,b)]; trans=its[0]['transfer']; f=len(its)
        D=market['demand_'+scenario]*demand_scale*(market_scales or {}).get(market['pair'],1)
        qmax=p['capture_'+('transfer' if trans else market['capture_group'])]
        q=qmax*(1-math.exp(-f/p['frequency_scale']))
        # Every transfer OD uses the same underlying market as a direct alternative.
        if trans:
            q=min(1,q*market.get('transfer_competition_factor',1)*transfer_scale)
        desired=D*q
        fare=market['fare_'+scenario]*fare_scale*(p['transfer_fare_factor'] if trans else 1)
        can=min(1,market['cannibal_'+scenario]*can_scale)
        oldfare=market['fare_'+scenario]*p['old_RW_fare_ratio'] # unchanged incumbent price in fare sensitivity
        oldseg=market['old_rw_segments']
        margin=fare-can*oldfare-p['pax_cost']*(len(its[0]['legs'])-can*oldseg)
        for it in its:
            offers.append(dict(origin=a,destination=b,market=market['pair'],desired=desired/f,fare=fare,
                cannibal_fraction=can,oldfare=oldfare,oldseg=oldseg,margin=margin,**it))
    # Deterministic allocation: local bookings first, no backfilling between dates.
    # Reverse priority is separately tested. It is not a calibrated booking curve.
    offers.sort(key=lambda o:((o['transfer'] if priority=='local_first' else not o['transfer']),
                              -o['margin']/len(o['legs']),o['origin'],o['destination'],o['day']))
    for o in offers:
        sold=min(o['desired'],*(caps[x] for x in o['legs']))
        for x in o['legs']:caps[x]-=sold
        migrated=sold*o['cannibal_fraction']
        if o['oldseg']==1 and (o['origin'],o['destination']) in migration_left:
            k=(o['origin'],o['destination']);migrated=min(migrated,migration_left[k]);migration_left[k]-=migrated
        traffic.append(dict(network=net,scenario=scenario,origin=o['origin'],destination=o['destination'],day=o['day'],
            transfer=o['transfer'],flight_ids=';'.join(o['legs']),desired_pax=o['desired'],sold_pax=sold,
            migrated_RW_pax=migrated,net_new_pax=sold-migrated,segment_pax=sold*len(o['legs']),
            gross_revenue=sold*o['fare'],foregone_RW_revenue=migrated*o['oldfare'],
            incremental_revenue=sold*o['fare']-migrated*o['oldfare'],
            new_pax_variable=sold*len(o['legs'])*p['pax_cost'],saved_old_pax_variable=migrated*o['oldseg']*p['pax_cost']))
    costrows=[]
    for r in legs:
        h=r['block_minutes']/60
        tons=p['fuel_t_per_hour']*h+p['fuel_t_per_cycle']
        fuel=tons*(p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t'])
        mro=h*p['mro_rub_per_hour'];crew=h*p['crew_rub_per_hour'];nav=h*p['navigation_rub_per_hour']
        ground=INPUT['ufa_reference_basket_rub']*p['airport_factor']
        deice=p['deicing_probability']*p['deicing_operation_rub']
        costrows.append(dict(network=net,scenario=scenario,flight_id=r['id'],fuel_t=tons,fuel_cost=fuel*cost_scale,
            mro_cost=mro*cost_scale,crew_cost=crew*cost_scale,navigation_cost=nav*cost_scale,
            ground_fixed=ground*cost_scale,deicing_reserve=deice*cost_scale,
            flight_fixed_cost=(fuel+mro+crew+nav+ground+deice)*cost_scale,
            sold_segment_pax=SEATS-caps[r['id']]))
    sums={k:sum(t[k] for t in traffic) for k in ['sold_pax','migrated_RW_pax','net_new_pax','segment_pax','gross_revenue',
        'foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable']}
    flightcost=sum(t['flight_fixed_cost'] for t in costrows)
    contrib=sums['incremental_revenue']-flightcost-sums['new_pax_variable']+sums['saved_old_pax_variable']
    result=dict(network=net,scenario=scenario,weekly_legs=len(legs),weekly_block_hours=sum(r['block_minutes'] for r in legs)/60,
        **sums,local_pax=sum(t['sold_pax'] for t in traffic if not t['transfer']),
        transfer_pax=sum(t['sold_pax'] for t in traffic if t['transfer']),
        offered_pax=sum(t['desired_pax'] for t in traffic),
        seats=len(legs)*SEATS,load_factor=sums['segment_pax']/(len(legs)*SEATS),
        flight_fixed_cost=flightcost,incremental_operating_cost=flightcost+sums['new_pax_variable']-sums['saved_old_pax_variable'],
        contribution_before_base_and_fleet=contrib)
    assert all(-1e-6<=c<=SEATS+1e-6 for c in caps.values())
    assert abs(sum(SEATS-c for c in caps.values())-sums['segment_pax'])<1e-6
    assert abs(sums['sold_pax']+result['transfer_pax']-sums['segment_pax'])<1e-6
    assert sums['migrated_RW_pax']<=sums['sold_pax']+1e-6
    for key,n in RW_DIRECT_FLIGHTS.items():
        m=MARKETS.get(pair(*key))
        if m and m['old_rw_segments']==1:
            migrated=sum(t['migrated_RW_pax'] for t in traffic if (t['origin'],t['destination'])==key)
            assert migrated<=n*100+1e-6
    assert abs(sums['sold_pax']-sums['net_new_pax']-sums['migrated_RW_pax'])<1e-6
    for t in traffic:
        m=MARKETS[pair(t['origin'],t['destination'])]
        expected=m['fare_'+scenario]*fare_scale*(p['transfer_fare_factor'] if t['transfer'] else 1)
        assert abs(t['gross_revenue']-t['sold_pax']*expected)<1e-6
    for (a,b),its in ITINS[net].items():
        ds=sum(o['desired'] for o in offers if (o['origin'],o['destination'])==(a,b))
        D=MARKETS[pair(a,b)]['demand_'+scenario]*demand_scale*(market_scales or {}).get(pair(a,b),1)
        assert ds<=D+1e-6
    return result,traffic,costrows

def operational_audit():
    rows=[]
    for net in ['A','B0','B']:
        for day in range(1,7):
            for plane in sorted({r['aircraft'] for r in LEGS if r['network']==net}):
                rs=sorted([r for r in LEGS if r['network']==net and r['day']==day and r['aircraft']==plane],key=lambda r:r['departure_utc_minute'])
                hours=sum(r['block_minutes'] for r in rs)/60;span=(rs[-1]['arrival_utc_minute']-rs[0]['departure_utc_minute'])/60
                assert all(x['destination']==y['origin'] and x['arrival_utc_minute']+45<=y['departure_utc_minute'] for x,y in zip(rs,rs[1:]))
                rows.append(dict(network=net,day=day,aircraft=plane,block_hours=hours,span_hours=span,
                    exceeds_10h_planning_cap=hours>10,exceeds_16h_span=span>16,
                    first_utc_minute=rs[0]['departure_utc_minute'],last_utc_minute=rs[-1]['arrival_utc_minute']))
    csvout('operational_audit.csv',rows)
    # Test all morning/afternoon assignments in the hub, without changing the bank.
    # An unpaired afternoon job requires another aircraft; this is a constructive
    # reassignment at GOJ, not a claim that crews, maintenance or slots are available.
    realloc=[];reassigned=[]
    for day in range(1,7):
        jobs={}
        for r in LEGS:
            if r['network']=='A' and r['day']==day:
                jobs.setdefault((r['aircraft'],r['departure_utc_minute']>=795),[]).append(r)
        am=[x for (k,pm),x in jobs.items() if not pm];pm=[x for (k,p),x in jobs.items() if p]
        def hrs(job):return sum(x['block_minutes'] for x in job)/60
        options=[]
        for perm in itertools.permutations(range(4)):
            bad=sum(hrs(am[i])+hrs(pm[j])>10 for i,j in enumerate(perm))
            options.append((bad,perm))
        bad,perm=min(options)
        byplane=[];nextplane=4
        for i,j in enumerate(perm):
            left=f'A{i+1}'
            right=left if hrs(am[i])+hrs(pm[j])<=10 else f'A{(nextplane:=nextplane+1)}'
            for job,tail in [(am[i],left),(pm[j],right)]:
                for l in job:reassigned.append({**l,'original_aircraft':l['aircraft'],'aircraft':tail})
            if right==left:byplane.append(am[i]+pm[j])
            else:byplane.extend([am[i],pm[j]])
        assert all(hrs(j)<=10 for j in byplane)
        realloc.append(dict(day=day,constructive_active_at_10h=4+bad,
                            morning_to_afternoon='; '.join(am[i][0]['destination']+'→'+pm[j][0]['destination'] for i,j in enumerate(perm)),
                            max_block_hours=max(hrs(j) for j in byplane),
                            max_span_hours=max((max(l['arrival_utc_minute'] for l in j)-min(l['departure_utc_minute'] for l in j))/60 for j in byplane),
                            caveat='unmatched afternoon excursion uses an extra GOJ aircraft; crew and dispatch validation pending'))
    csvout('hub_reassignment.csv',realloc)
    csvout('hub_reassigned_flights.csv',reassigned)
    stress=[]
    for factor in [1,1.1,1.2]:
        for turn in [45,60]:
            am=[[r for r in LEGS if r['network']=='A' and r['day']==1 and r['aircraft']==f'A{i}' and r['departure_utc_minute']<795] for i in range(1,5)]
            pm=[[r for r in LEGS if r['network']=='A' and r['day']==1 and r['aircraft']==f'A{i}' and r['departure_utc_minute']>=795] for i in range(1,5)]
            hours=lambda job:sum(r['block_minutes'] for r in job)*factor/60
            bad=min(sum(hours(am[i])+hours(pm[j])>10 for i,j in enumerate(perm)) for perm in itertools.permutations(range(4)))
            for net in ['A','B0','B']:
                old=[r for r in rows if r['network']==net]
                counts=Counter((r['day'],r['aircraft']) for r in LEGS if r['network']==net)
                stress.append(dict(network=net,block_time_factor=factor,turn_minutes=turn,
                    weekly_block_hours=sum(r['block_hours'] for r in old)*factor,
                    original_rotation_days_over_10h=sum(r['block_hours']*factor>10 for r in old),
                    original_rotation_max_span_hours=max(r['span_hours']+(r['block_hours']*(factor-1))+(2 if net=='A' else counts[(r['day'],r['aircraft'])]-1)*(turn-45)/60 for r in old),
                    hub_constructive_active_after_reassignment=4+bad if net=='A' else '',
                    caveat='time stress only; no proof of slots, crews, maintenance or reserve coverage'))
    csvout('operational_stress.csv',stress)
    return rows,realloc

def calculate():
    comps=competition(); audit,reassign=operational_audit()
    csvout('incumbent_migration_caps.csv',[dict(origin=a,destination=b,week=INPUT['calendar_weeks'][-1],
        published_RW_flights=n,seats_upper_bound=n*100,note='physical upper bound only, not observed passengers or demand')
        for (a,b),n in sorted(RW_DIRECT_FLIGHTS.items())])
    summaries=[];traffic=[];costs=[]; pairresults=[];legthreshold=[]
    for scenario in ['base','cautious']:
        for net in ['A','B0','B']:
            result,t,c=evaluate(net,scenario);summaries.append(result);traffic+=t;costs+=c
            for key in sorted({pair(r['origin'],r['destination']) for r in t}):
                rr=[r for r in t if pair(r['origin'],r['destination'])==key]; m=MARKETS[key]
                pairresults.append(dict(network=net,scenario=scenario,pair=key,kind='transfer' if rr[0]['transfer'] else 'local',
                    demand_per_direction=m['demand_'+scenario],fare=m['fare_'+scenario],
                    captured_pax=sum(r['sold_pax'] for r in rr),migrated_RW_pax=sum(r['migrated_RW_pax'] for r in rr),
                    incremental_revenue=sum(r['incremental_revenue'] for r in rr),
                    passenger_margin=sum(r['incremental_revenue']-r['new_pax_variable']+r['saved_old_pax_variable'] for r in rr)))
            for key in sorted({pair(r['origin'],r['destination']) for r in LEGS if r['network']==net}):
                rr=[r for r in LEGS if r['network']==net and pair(r['origin'],r['destination'])==key]
                cc=[r for r in c if r['flight_id'] in {x['id'] for x in rr}]; m=MARKETS[key];p=INPUT['scenarios'][scenario]
                f=len(rr)/2;capture=p['capture_'+m['capture_group']]*(1-math.exp(-f/p['frequency_scale']))
                unit=m['fare_'+scenario]-p['pax_cost']
                cash=sum(r['flight_fixed_cost'] for r in cc)
                legthreshold.append(dict(network=net,scenario=scenario,pair=key,departures_per_direction=f,
                    cash_cost_week=cash,average_cost_flight=cash/len(rr),
                    break_even_pax_per_departure=cash/len(rr)/unit,
                    required_total_OD_per_direction_week_no_cannibal=cash/(2*unit*capture),
                    assumption='standalone direct service; no transfer, no cannibalisation, no base/fleet cost; necessary not sufficient for A'))
    csvout('network_comparison.csv',summaries);csvout('itinerary_sales.csv',traffic);csvout('flight_costs.csv',costs)
    csvout('pair_results.csv',pairresults);csvout('pair_thresholds.csv',legthreshold)
    extras=[]
    for sc in ['base','cautious']:
        for key in ['AER-GSV','OMS-SVX']:
            rs={n:next(r for r in pairresults if r['network']==n and r['scenario']==sc and r['pair']==key) for n in ['B0','B']}
            cs={n:sum(r['flight_fixed_cost'] for r in costs if r['network']==n and r['scenario']==sc and pair(next(l for l in LEGS if l['id']==r['flight_id'])['origin'],next(l for l in LEGS if l['id']==r['flight_id'])['destination'])==key) for n in ['B0','B']}
            dm=rs['B']['passenger_margin']-rs['B0']['passenger_margin'];dc=cs['B']-cs['B0']
            # Demand threshold holds capture response/yield constant and excludes seat limits;
            # explicitly flag thresholds whose implied incremental passengers exceed seats.
            dp=rs['B']['captured_pax']-rs['B0']['captured_pax']; added=8 if key=='AER-GSV' else 12
            unit=dm/dp if dp>0 else 0;needed=dc/unit if unit>0 else math.inf
            def extra_at(scale):
                vals={}
                for n in ['B0','B']:
                    _,tt,cc=evaluate(n,sc,market_scales={key:scale})
                    ids={l['id'] for l in LEGS if l['network']==n and pair(l['origin'],l['destination'])==key}
                    mm=sum(t['incremental_revenue']-t['new_pax_variable']+t['saved_old_pax_variable'] for t in tt if pair(t['origin'],t['destination'])==key)
                    vals[n]=mm-sum(c['flight_fixed_cost'] for c in cc if c['flight_id'] in ids)
                return vals['B']-vals['B0']
            saturated=extra_at(1000)
            exact='';exact_status='NO_BREAK_EVEN_EVEN_WITH_SATURATED_MARKET'
            if saturated>=0:
                lo,hi=0.,1000.
                for _ in range(45):
                    mid=(lo+hi)/2
                    if extra_at(mid)>=0:hi=mid
                    else:lo=mid
                exact=MARKETS[key]['demand_'+sc]*hi;exact_status='SCENARIO_THRESHOLD_WITH_CAPACITY'
            extras.append(dict(scenario=sc,pair=key,added_legs=added,added_cost=dc,added_pax=dp,
                added_passenger_margin=dm,incremental_contribution=dm-dc,
                required_added_pax=needed,added_seats=added*SEATS,
                required_OD_per_direction_if_uncapped=MARKETS[key]['demand_'+sc]*dc/dm if dm>0 else math.inf,
                exact_required_OD_per_direction_week=exact,exact_threshold_status=exact_status,
                saturated_market_incremental_contribution=saturated,
                caveat='uncapped linear extrapolation is illustrative only; exact threshold uses capacity in both B and B0'))
    csvout('reinforcement_test.csv',extras)
    sensitivity=[];thresholds=[]
    for sc in ['base','cautious']:
        cache={}
        def joint(scale):
            if scale not in cache:
                # A transfer OD which is direct in B (ARH–MRV, KUF–OMS) must
                # change in B as well. Otherwise the sensitivity favours A.
                ms={k:scale for k in TRANSFER_KEYS}
                rr={n:evaluate(n,sc,market_scales=ms)[0] for n in ['A','B0','B']}
                direct=max(rr['B0']['contribution_before_base_and_fleet'],rr['B']['contribution_before_base_and_fleet'])
                cache[scale]=(rr['A'],direct)
            return cache[scale]
        grid=[i/20 for i in range(201)]+[20,50,1000]
        for scale in grid:
            a,benchmark=joint(scale)
            sensitivity.append(dict(scenario=sc,transfer_demand_multiplier=scale,transfer_pax=a['transfer_pax'],
                contribution_A_before_base=a['contribution_before_base_and_fleet'],best_direct_contribution=benchmark,
                max_hub_base_rub_week_vs_direct=a['contribution_before_base_and_fleet']-benchmark,
                max_hub_base_rub_week_vs_no_launch=a['contribution_before_base_and_fleet']))
        for annualbase in [0,50_000_000,150_000_000]:
            for reference in ['best_direct','no_launch']:
                targetbase=annualbase/52
                def gap(x):
                    a,direct=joint(x)
                    return a['contribution_before_base_and_fleet']-(direct if reference=='best_direct' else 0)-targetbase
                brackets=[(x,y) for x,y in zip(grid,grid[1:]) if gap(x)*gap(y)<0]
                positive=[x for x in grid if gap(x)>=0]
                top=joint(1000)[0]
                if not positive:
                    thresholds.append(dict(scenario=sc,base_cost_annual_equivalent=annualbase,reference=reference,
                        required_transfer_pax_week='',required_transfer_OD_multiplier='',
                        status='NO_CROSSING_ON_GRID_0_TO_10_AND_SATURATION',max_transfer_pax=top['transfer_pax'],
                        winning_market_multiplier_windows='none on tested grid'))
                    continue
                roots=[]
                for left,right in brackets:
                    gl=gap(left)
                    for _ in range(40):
                        mid=(left+right)/2
                        if gl*gap(mid)<=0:right=mid
                        else:left=mid;gl=gap(left)
                    roots.append((left+right)/2)
                first=min(positive)
                hi=max((r for r in roots if r<=first),default=first)
                r=joint(hi)[0]
                thresholds.append(dict(scenario=sc,base_cost_annual_equivalent=annualbase,reference=reference,
                    required_transfer_pax_week=r['transfer_pax'],required_transfer_OD_multiplier=hi,status='FIRST_SCENARIO_CROSSING_ON_GRID',max_transfer_pax=top['transfer_pax'],
                    winning_market_multiplier_windows='roots='+','.join(f'{x:.5f}' for x in roots)+'; tested positive range='+str(min(positive))+'..'+str(max(positive))))
    csvout('hub_base_sensitivity.csv',sensitivity);csvout('transfer_thresholds.csv',thresholds)
    fixed_thresholds=[];break_even=[];capturegrid=[]
    for sc in ['base','cautious']:
        direct=max(evaluate(n,sc)[0]['contribution_before_base_and_fleet'] for n in ['B0','B'])
        scales=[i/20 for i in range(201)]+[20,50,1000]
        sales={x:evaluate('A',sc,transfer_scale=x)[0] for x in scales}
        for x,r in sales.items():capturegrid.append(dict(scenario=sc,capture_multiplier=x,transfer_pax=r['transfer_pax'],
            contribution_before_base=r['contribution_before_base_and_fleet'],direct_contribution=direct))
        for annualbase in [0,50_000_000,150_000_000]:
            for ref,target in [('best_direct',direct),('no_launch',0)]:
                target+=annualbase/52
                maxsales=sales[1000]
                wins=[x for x,r in sales.items() if r['contribution_before_base_and_fleet']>=target]
                if not wins:
                    fixed_thresholds.append(dict(scenario=sc,base_cost_annual_equivalent=annualbase,reference=ref,
                        required_transfer_pax='',transfer_capture_multiplier='',max_transfer_pax=maxsales['transfer_pax'],status='NO_CROSSING_ON_CAPTURE_GRID_WITH_FIXED_OD'))
                else:
                    hi=min(wins);lo=max((x for x in scales if x<hi),default=0)
                    for _ in range(45):
                        mid=(lo+hi)/2
                        if evaluate('A',sc,transfer_scale=mid)[0]['contribution_before_base_and_fleet']>=target:hi=mid
                        else:lo=mid
                    x=evaluate('A',sc,transfer_scale=hi)[0]
                    fixed_thresholds.append(dict(scenario=sc,base_cost_annual_equivalent=annualbase,reference=ref,
                        required_transfer_pax=x['transfer_pax'],transfer_capture_multiplier=hi,max_transfer_pax=maxsales['transfer_pax'],status='CONDITIONAL_CAPTURE_THRESHOLD_FIXED_OD'))
            for n in ['A','B0','B']:
                r=evaluate(n,sc)[0];base=annualbase/52 if n=='A' else 0
                netpax=r['new_pax_variable']-r['saved_old_pax_variable']
                break_even.append(dict(scenario=sc,network=n,hub_base_annual_equivalent=annualbase if n=='A' else 0,
                    fare_multiplier_for_zero_contribution_at_fixed_sales=(r['foregone_RW_revenue']+r['incremental_operating_cost']+base)/r['gross_revenue'],
                    flight_cost_multiplier_for_zero_contribution_at_fixed_sales=(r['incremental_revenue']-netpax-base)/r['flight_fixed_cost'],
                    current_avg_net_journey_revenue=r['gross_revenue']/r['sold_pax'],
                    required_avg_net_journey_revenue=(r['foregone_RW_revenue']+r['incremental_operating_cost']+base)/r['sold_pax'],
                    caveat='fixed sales mix and incumbent fares; no price elasticity; before fixed fleet cost'))
    csvout('capture_transfer_thresholds.csv',fixed_thresholds)
    csvout('capture_sensitivity.csv',capturegrid)
    csvout('break_even_yield_cost.csv',break_even)
    incumbent,_=calendar(INPUT['calendar_weeks'][-1]);redeploy=[]
    for sc in ['base','cautious']:
        for net in ['A','B0','B']:
            r,_,cc=evaluate(net,sc);credit=0.;details=[]
            for (a,b) in sorted({(l['origin'],l['destination']) for l in LEGS if l['network']==net}):
                old=sum(x['origin']==a and x['destination']==b and x['flight'].startswith('WZ-') for x in incumbent)
                ids={l['id'] for l in LEGS if l['network']==net and (l['origin'],l['destination'])==(a,b)}
                n=min(old,len(ids))
                if n:
                    val=sum(x['flight_fixed_cost'] for x in cc if x['flight_id'] in ids)/len(ids)*n
                    credit+=val;details.append(f'{a}–{b}:{n}')
            redeploy.append(dict(network=net,scenario=sc,avoidable_old_flight_cost_upper_bound=credit,
                old_flights_replaced=';'.join(details),additive_contribution=r['contribution_before_base_and_fleet'],
                contribution_with_optimistic_withdrawal_credit=r['contribution_before_base_and_fleet']+credit,
                status='UPPER_BOUND_ONLY: old traffic and revenue lost on cancellation not known; not a complete replacement case'))
    csvout('incumbent_redeployment_bound.csv',redeploy)
    costlimits=[]
    for sc in ['base','cautious']:
        aa=next(r for r in summaries if r['network']=='A' and r['scenario']==sc)
        bb=next(r for r in summaries if r['network']=='B0' and r['scenario']==sc)
        delta=aa['contribution_before_base_and_fleet']-bb['contribution_before_base_and_fleet']
        dh=aa['weekly_block_hours']-bb['weekly_block_hours'];dn=aa['weekly_legs']-bb['weekly_legs']
        dtfuel=sum(r['fuel_t'] for r in costs if r['network']=='A' and r['scenario']==sc)-sum(r['fuel_t'] for r in costs if r['network']=='B0' and r['scenario']==sc)
        costlimits.append(dict(scenario=sc,advantage_A_before_base=delta,
            additional_common_rub_per_hour_for_tie=delta/dh,additional_common_rub_per_flight_for_tie=delta/dn,
            additional_common_fuel_rub_per_t_for_tie=delta/dtfuel,
            condition='each parameter changes separately; fixed sales, incumbent fares, no base/fleet cost; negative means A already loses'))
    csvout('comparison_cost_thresholds.csv',costlimits)
    update_city_ranking()
    robustness=[]
    for sc in ['base','cautious']:
        cases=[('default',{}),('transfer_booked_first',{'priority':'transfer_first'}),
            ('no_RW_cannibalisation',{'can_scale':0}),('double_RW_cannibalisation',{'can_scale':2}),
            ('all_fares_plus_25pct',{'fare_scale':1.25}),('all_costs_minus_25pct',{'cost_scale':.75}),
            ('all_OD_double',{'demand_scale':2}),('all_OD_zero',{'demand_scale':0})]
        for label,kw in cases:
            results={n:evaluate(n,sc,**kw)[0] for n in ['A','B0','B']}
            for n,r in results.items():
                robustness.append(dict(scenario=sc,test=label,network=n,pax=r['sold_pax'],transfer_pax=r['transfer_pax'],
                    contribution_before_base=r['contribution_before_base_and_fleet'],
                    best_including_no_launch=max(['A','B0','B','NO_LAUNCH'],key=lambda x:0 if x=='NO_LAUNCH' else results[x]['contribution_before_base_and_fleet'])))
    csvout('robustness.csv',robustness)
    # Conservation tests with deliberate saturation and simple analytic fare accounting.
    for n in ['A','B0','B']:evaluate(n,'base',demand_scale=1000)
    for n in ['B0','B']:
        assert all(len(o['legs'])==1 for its in ITINS[n].values() for o in its)
    assert len([l for l in LEGS if l['network']=='B0'])==72
    assert len([l for l in LEGS if l['network']=='B'])==92
    assert len([l for l in LEGS if l['network']=='A'])==96
    assert all(pair(a,b) in MARKETS for n,ii in ITINS.items() for a,b in ii)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'inputs.json',OUT/'schedule_rules.json',OUT/'sources.json',OLD/'coordinates.json',OLD/'inputs.json',Path(__file__).resolve()]}
    dump('validation.json',dict(status='PASS',input_sha256=hashes,tests=['all segments within 100 seats including saturation stress',
        'transfer consumes two seats and one fare','migrated passengers and foregone revenue separately reconciled',
        'total offers on each directed OD never exceed independent scenario OD, including max capture stress',
        'migration from confirmed old RW nonstops cannot exceed their published weekly seats; connecting baseline capacity UNKNOWN',
        'same OD input used in direct and transfer alternatives','B0 preserved: 72 flights; B:92; A:96',
        'spatial continuity and 45-minute turns','published schedule counted by dated flight, duplicates removed'],
        limitations=['scenario demand and choice coefficients not estimated','planning-cap violations are reported, not suppressed',
            'no claim of closed booking fare or OD data','no annual traffic forecast','fleet/base fixed costs excluded; thresholds shown']))
    dump('result.json',dict(summary=summaries,extra=extras,thresholds=thresholds,hub_reassignment=reassign))
    make_tables(summaries,extras,comps,thresholds)
    make_chart(summaries)
    print(json.dumps(dict(status='PASS',results=[dict(network=r['network'],scenario=r['scenario'],
        pax=round(r['sold_pax']),contribution_million_rub=round(r['contribution_before_base_and_fleet']/1e6,3)) for r in summaries]),ensure_ascii=False))

def update_city_ranking():
    original=list(csv.DictReader((OLD/'ranking.csv').open()))
    base=[{**r,**{k:float(r[k]) for k in ['market','competition','geography','technical','basing']}}
          for r in original if r['weights']=='base' and r['scope']=='new_node']
    weights=json.loads((OLD/'inputs.json').read_text())['weights'];rows=[];full=[]
    for case in ['UFA_RRJ_admission_confirmed','all_technical_equal_100','omit_technical_weight',
                 'equal_technical_UFA_basing_80_scenario']:
        for label,ww in weights.items():
            ww=copy.deepcopy(ww);rr=copy.deepcopy(base)
            for r in rr:
                if r['iata']=='UFA':r['technical']=75
                if case in ['all_technical_equal_100','equal_technical_UFA_basing_80_scenario']:r['technical']=100
                if case=='equal_technical_UFA_basing_80_scenario' and r['iata']=='UFA':r['basing']=80
            if case=='omit_technical_weight':
                ww['technical']=0;total=sum(ww.values());ww={k:v/total for k,v in ww.items()}
            for r in rr:r['score']=sum(ww[k]*r[k] for k in ww)
            rr.sort(key=lambda r:-r['score'])
            rows.append(dict(case=case,weights=label,top3=' > '.join(r['iata'] for r in rr[:3]),
                GOJ_score=next(r['score'] for r in rr if r['iata']=='GOJ'),UFA_score=next(r['score'] for r in rr if r['iata']=='UFA'),
                status='SENSITIVITY_NOT_PROOF_OF_DEMAND_OR_BASING'))
            for i,r in enumerate(rr,1):full.append(dict(case=case,weights=label,rank=i,iata=r['iata'],score=r['score']))
    csvout('city_ranking_update.csv',rows);csvout('city_ranking_update_full.csv',full)
    cities=json.loads((OLD/'inputs.json').read_text())['cities'];inv=[]
    for c in cities:
        inv.append(dict(city=c['city'],iata=c['iata'],population_city_2025_thousands=c['population_thousands'],
            demographic_status='SECONDARY city proper; catchment and age structure UNKNOWN',
            demographic_source_registry='../11_practical_screening/sources.json POP-1/POP-2',
            airport_pax_2025=c['airport_pax_2025'],airport_pax_qualifier=c['pax_qualifier'],
            aviation_source_ids=';'.join(c['sources']),
            aviation_update='RRJ admission/H24/public transfer procedure/tariffs' if c['iata']=='UFA' else ('dated seasonal rows' if c['iata'] in ['GOJ','KUF','GSV'] else 'previous verified screen'),
            economic_income_wages_business_OD='',economic_status='NOT_COLLECTED as comparable city/catchment series',
            airport_contract_costs='',airport_public_cost_reference='UFA public prices only; no signed hub contract' if c['iata']=='UFA' else '',
            tourism_monthly_paid_trips='',tourism_status='NOT_COLLECTED; qualitative route/region leads are not air OD',
            ground_door_to_door_time_fare='',ground_status='UNVERIFIED leads in earlier research; no same-date pair-level matrix',
            use_in_choice='population scale/geography in screening only; airport totals never route demand'))
    csvout('city_data_inventory.csv',inv)

def make_chart(summaries):
    data={sc:{r['network']:r['contribution_before_base_and_fleet']/1e6 for r in summaries if r['scenario']==sc} for sc in ['base','cautious']}
    markup='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{font-family:var(--font-sans,Arial);color:var(--foreground,CanvasText)}body{margin:0}p{margin:0 0 12px;line-height:1.5}.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:12px 0}select{font:inherit;color:inherit;background:var(--secondary,Canvas);border:1px solid var(--border,GrayText);border-radius:var(--radius,8px);padding:6px}label{font-size:14px}input{accent-color:var(--primary,Highlight);vertical-align:middle;max-width:180px}.muted{color:var(--muted-foreground,GrayText);font-size:13px}.chart{width:100%;height:285px;display:block}svg text{fill:var(--foreground,CanvasText);font-family:var(--font-sans,Arial)}.note{border-top:1px solid var(--border,GrayText);padding-top:12px}output{font-variant-numeric:tabular-nums}.key{font-weight:600}
</style><body><p class="key">Дополнительный результат, млн ₽ за неделю</p><div class="controls"><label>Сценарий <select id="scenario"><option value="base">Базовый</option><option value="cautious">Осторожный</option></select></label><label>Новая база А: <output id="baseLabel">50</output> млн ₽/год-экв.<br><input id="baseCost" type="range" min="0" max="200" step="5" value="50" aria-label="Стоимость новой базы А"></label></div><svg id="chart" class="chart" viewBox="0 0 680 285" role="img" aria-label="Сравнение дополнительного результата А, Б0 и Б"></svg><p id="ranking" class="key"></p><p class="muted note">Продажи и часть расходов — сценарные. Пересадка занимает оба плеча, билет учтён один раз, переток RW вычтен. Фиксированная стоимость парка и центрального аппарата ещё не включена. ×52 означает годовой эквивалент недели.</p><script>
const data=__DATA__; const names={A:'А: хаб',B0:'Б0: прямая',B:'Б: усиление'};const colors={A:'var(--chart-1,Highlight)',B0:'var(--chart-2,GrayText)',B:'var(--chart-3,Highlight)'};
const fmt=n=>n.toLocaleString('ru-RU',{minimumFractionDigits:2,maximumFractionDigits:2});
function draw(){const sc=document.getElementById('scenario').value;const base=Number(document.getElementById('baseCost').value);document.getElementById('baseLabel').textContent=base;const vals={...data[sc]};vals.A-=base/52;const x=v=>620+v/120*470;let s='';for(const tick of [-120,-90,-60,-30,0]){s+=`<line x1="${x(tick)}" y1="14" x2="${x(tick)}" y2="242" stroke="var(--border,GrayText)"/><text x="${x(tick)}" y="267" text-anchor="middle" font-size="13">${tick}</text>`;}['A','B0','B'].forEach((n,i)=>{const y=24+i*57;const left=x(vals[n]);s+=`<text x="0" y="${y+23}" font-size="15">${names[n]}</text><rect x="${left}" y="${y}" width="${620-left}" height="34" rx="4" fill="${colors[n]}"/><text x="${left-8}" y="${y+23}" text-anchor="end" font-size="14">${fmt(vals[n])}</text>`;});s+='<text x="0" y="223" font-size="14">Без расширения</text><circle cx="620" cy="218" r="4" fill="var(--foreground,CanvasText)"/><text x="608" y="223" text-anchor="end" font-size="14">0</text>';document.getElementById('chart').innerHTML=s;const win=Object.keys(vals).sort((a,b)=>vals[b]-vals[a])[0];document.getElementById('ranking').textContent=`Среди проектов выше ${names[win]}. Все три результата отрицательны.`;}
document.getElementById('scenario').addEventListener('change',draw);document.getElementById('baseCost').addEventListener('input',draw);draw();
</script></body></html>'''
    (OUT/'comparison_chart.html').write_text(markup.replace('__DATA__',json.dumps(data)))

def make_tables(summary,extra,comps,thresholds):
    chunks=['<!-- Generated by scripts/build_network_economics.py. -->',
        '## Сравнение одной сценарной недели',
        table(['Сценарий','Сеть','Рейсы / ч','Местные OD','Трансфер OD','Все OD / сегменты','Переток RW','Выручка gross / incremental, млн ₽','Расходы incremental, млн ₽','Вклад до базы и фикс. парка, млн ₽','Загрузка (результат)'],
            [[r['scenario'],r['network'],f"{r['weekly_legs']} / {r['weekly_block_hours']:.1f}",f"{r['local_pax']:.0f}",f"{r['transfer_pax']:.0f}",
              f"{r['sold_pax']:.0f} / {r['segment_pax']:.0f}",f"{r['migrated_RW_pax']:.0f}",
              f"{r['gross_revenue']/1e6:.2f} / {r['incremental_revenue']/1e6:.2f}",f"{r['incremental_operating_cost']/1e6:.2f}",
              f"{r['contribution_before_base_and_fleet']/1e6:.2f}",f"{100*r['load_factor']:.1f}%"] for r in summary]),
        '## Все 20 пар: конкуренция, собственные рейсы, границы знания',
        'Числа через косую черту — в двух направлениях пары в указанном порядке. NOT LISTED означает отсутствие в проверенной таблице, UNKNOWN — текущая первичная таблица не получена. Ноль в таблице не является доказательством отсутствия продаж с пересадкой.']
    rr=[]
    for m in INPUT['markets']:
        if not m['local_pair']:continue
        a,b=m['pair'].split('-'); info=[]
        for week in INPUT['calendar_weeks']:
            rs=[r for r in comps if r['week']==week and pair(r['origin'],r['destination'])==m['pair']]
            rs=sorted(rs,key=lambda r:0 if r['origin']==a else 1)
            info.append(' / '.join(str(r['departures']) if r['departures']!='' else '?' for r in rs))
        rs=[r for r in comps if r['week']==INPUT['calendar_weeks'][-1] and pair(r['origin'],r['destination'])==m['pair']]
        rr.append([m['pair'],*info,'; '.join(sorted({r['carriers'] for r in rs if r['carriers']})) or 'UNKNOWN / NOT LISTED',
            ' / '.join(str(r['rw_departures']) if r['rw_departures']!='' else '?' for r in sorted(rs,key=lambda r:r['origin']!=a)),
            m['project_class'],m['seasonality'],m['evidence'],
            ', '.join('['+s+']('+SOURCES[s]['url']+')' for s in m['sources'] if s in SOURCES)])
    chunks.append(table(['Пара','16–22.11','7–13.12','Перевозчики 7–13.12','RW 7–13.12','Проект','Сезонность / ограничения','Спрос: что доказано','Источники'],rr))
    chunks+=['## Сценарии OD и чистого дохода на билет',
        'OD ниже — пассажиры в неделю в одном направлении, до захвата проектом. Это проверяемые допущения; нижняя доказанная граница для неизвестного объёма равна нулю. Доход указан за одно путешествие после скидок, возвратов, каналов продаж и сборов, не по рекламной цене.',
        table(['Пара','Использование','Осторожный / базовый OD','Стресс-диапазон OD','Чистый билет осторожный / базовый, ₽','Основание диапазона / что проверить'],
            [[m['pair'],'местная / прямая' if m['local_pair'] else 'трансфер',f"{m['demand_cautious']} / {m['demand_base']}",m['demand_stress_range'],
              f"{m['fare_cautious']} / {m['fare_base']}",m['range_basis']] for m in INPUT['markets']]),
        '## Проверка добавок Б к Б0',
        table(['Сценарий','Пара','Добавлено рейсов','Доп. пассажиры OD','Доп. расходы, млн ₽','Доп. вклад, млн ₽','Линейный ориентир доп. OD / доп. кресла','Точный порог рынка OD/напр./нед.','Доп. вклад при насыщении, млн ₽'],
            [[r['scenario'],r['pair'],r['added_legs'],f"{r['added_pax']:.0f}",f"{r['added_cost']/1e6:.2f}",f"{r['incremental_contribution']/1e6:.2f}",
              f"{r['required_added_pax']:.0f} / {r['added_seats']}",f"{r['exact_required_OD_per_direction_week']:.0f}" if r['exact_required_OD_per_direction_week']!='' else 'Не достигается при заданных тарифе/перетоке',f"{r['saturated_market_incremental_contribution']/1e6:.2f}"] for r in extra]),
        '## Порог трансферных пассажиров',
        'Меняется весь рынок трансферных пар; на общих OD (ARH–MRV, KUF–OMS) тот же рынок получает и Б0/Б. Местные брони получают места первыми. Преимущество может исчезать при дальнейшем росте рынка: см. оба корня в последнем столбце. Порог при неизменном общем OD и изменении только захвата хаба — отдельно в capture_transfer_thresholds.csv.',
        table(['Сценарий','База, млн ₽/год-экв.','Сравнение','Нужны трансфер OD/нед.','Множитель трансферного рынка','Статус / границы преимущества'],
            [[r['scenario'],r['base_cost_annual_equivalent']/1e6,r['reference'],f"{r['required_transfer_pax_week']:.0f}" if r['required_transfer_pax_week']!='' else '—',
              f"{r['required_transfer_OD_multiplier']:.2f}" if r['required_transfer_OD_multiplier']!='' else '—',r['status']+'; '+r['winning_market_multiplier_windows']] for r in thresholds])]
    chunks+=['## Конкуренты на 13 трансферных OD',
        table(['OD','Вылеты в двух направлениях 7–13.12','Перевозчики','Доказательство / пропуск'],
          [[key,' / '.join(str(r['departures']) if r['departures']!='' else '?' for r in sorted([r for r in comps if r['week']==INPUT['calendar_weeks'][-1] and pair(r['origin'],r['destination'])==key],key=lambda r:r['origin'])),
            '; '.join(sorted({r['carriers'] for r in comps if r['week']==INPUT['calendar_weeks'][-1] and pair(r['origin'],r['destination'])==key and r['carriers']})) or 'UNKNOWN / NOT LISTED',MARKETS[key]['evidence']] for key in sorted(TRANSFER_KEYS)]),
        '## Публичные ценовые ориентиры RW',
        'Все строки — реклама «от», с датой из ссылки. Багаж, итоговая сумма, наличие и прямой характер перелёта не подтверждены. Сопоставимых финальных котировок на 7–13 декабря с 20 кг багажа не получено.',
        table(['Пара / направление','Дата','От, ₽','Ссылка'],[[r['origin']+'→'+r['destination'],r['date'],r['advertised_from_rub'],'[RW]('+r['url']+')'] for r in json.loads((OUT/'advertised_fares.json').read_text())])]
    (OUT/'tables.md').write_text('\n\n'.join(chunks)+'\n')

if __name__=='__main__':calculate()
