#!/usr/bin/env python3
"""P38 full-month exposure/API utility. No search, exporter, or old-file writes.

python3 -B context/38_direct_strategy_20261113/contract/month_adapter.py --month 2027-07 --candidate X_SVX_KJA
All results are conditional model diagnostics; actual demand/dispatch/PnL UNKNOWN.
The CLI writes JSON to stdout only. Import with Python -B (also set below).
"""
import sys
sys.dont_write_bytecode = True
import argparse
import calendar
import copy
import csv
import hashlib
import importlib.util
import inspect
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P36 = ROOT / 'context/36_overnight_chain_search_20261112'
UTC = timezone.utc
REFERENCE = datetime(2027, 2, 1, tzinfo=UTC)  # Monday, not month-number index
ZONES = dict(SVX='Asia/Yekaterinburg', ZIA='Europe/Moscow', DME='Europe/Moscow',
 KUF='Europe/Samara', UFA='Asia/Yekaterinburg', CEK='Asia/Yekaterinburg',
 TJM='Asia/Yekaterinburg', OMS='Asia/Omsk', PEE='Asia/Yekaterinburg',
 GOJ='Europe/Moscow', KJA='Asia/Krasnoyarsk', TOF='Asia/Tomsk', MRV='Europe/Moscow',
 AER='Europe/Moscow', REN='Asia/Yekaterinburg', IKT='Asia/Irkutsk')

def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@lru_cache(None)
def engine():
    return load('p38_readonly_p31', ROOT/'context/31_direct_growth_research_20261112/route_economics/calculate.py')

@lru_cache(None)
def block_api():
    return load('p38_readonly_p34', ROOT/'context/34_new_direct_top5_20261112/calculation/calculate.py')

def dt(s):
    x = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if x.tzinfo is None:
        raise ValueError('timezone required')
    return x.astimezone(UTC)

def bounds(year, month):
    start = datetime(year, month, 1, tzinfo=UTC)
    return start, start + timedelta(days=calendar.monthrange(year, month)[1])

def exposure(year, month):
    start, end = bounds(year, month)
    n = (end-start).days
    days = [(start+timedelta(days=i)).date() for i in range(n)]
    return dict(month=f'{year}-{month:02}', days=n,
        iso_weekday_counts={str(d):sum(x.isoweekday()==d for x in days) for d in range(1,8)},
        seasons={12:'winter',1:'winter',2:'winter',3:'spring',4:'spring',5:'spring',
                 6:'summer',7:'summer',8:'summer',9:'autumn',10:'autumn',11:'autumn'}[month])

@lru_cache(None)
def ledger():
    return read(P36/'pass2/revenue_cost_ledger.csv')

def p36_weekly(candidate, state):
    """Reconstruct exact weekly events, retaining IDs, tails, ferry and overnights.

    Departure comes from the completed ledger; directed block from its same
    P34 block API, cross-checked against the ledger's excluded crew-hours.
    This is recurrence of a scenario, not extension of a published timetable.
    """
    eq = [r for r in read(P36/'pass2/equivalence_map.csv')
          if r['candidate_id']==candidate and r['scenario']=='base' and r['state']==state]
    if len(eq)!=1:
        raise ValueError('unknown candidate/state')
    alias, label = eq[0]['equivalent_candidate'], eq[0]['equivalent_state']
    rows = [r for r in ledger() if r['candidate_id']==alias and r['state']==label
            and r['scenario']=='base' and r['flight_id'].endswith('/W1')]
    jobs = {}
    for r in rows:
        mins = block_api().block(r['origin'], r['destination'])
        if abs(mins-float(r['fixed_crew_excluded'])/15000*60)>1e-5:
            raise ValueError('directed block/ledger mismatch')
        dep = (dt(r['departure_utc'])-REFERENCE).total_seconds()/60
        jid = r['job_id']
        f = dict(flight_id=r['flight_id'].removesuffix('/W1'), job_id=jid, tail=r['tail'],
            origin=r['origin'], destination=r['destination'], dep=dep, arr=dep+mins,
            block=mins, kind='PAID_FERRY' if r['kind']=='positioning' else 'SERVICE',
            evidence='P36 completed scenario ledger + same directed P34 block analogue')
        jobs.setdefault(jid, dict(id=jid, tail=r['tail'], flights=[]))['flights'].append(f)
    for j in jobs.values():
        j['flights'].sort(key=lambda f:f['dep'])
    return list(jobs.values())

def candidate_positions(candidate):
    r = next(r for r in read(P36/'pass2/three_state_comparison.csv') if r['candidate_id']==candidate)
    return json.loads(r['tail_positions'])

def resources(positions):
    """Explicit HYPOTHETICAL envelope, never actual released stock."""
    out = [dict(id=t, type='RRJ-95B', initial_location=a, reserve=False,
        available_from='2026-12-01T00:00:00Z', available_to='2028-02-01T00:00:00Z',
        saleable_seats=100, admission='SCENARIO_ONLY', actual_release=None) for t,a in positions.items()]
    out.append(dict(id='R1', type='RRJ-95B', initial_location='SVX', reserve=True,
        available_from='2026-12-01T00:00:00Z', available_to='2028-02-01T00:00:00Z',
        admission='SEPARATE_HYPOTHETICAL_RESERVE_ACTUAL_UNKNOWN', actual_release=None))
    return out

def cohort(k):
    if k not in (1,2,3):
        raise ValueError('working cohort must be 1/2/3')
    jobs = p36_weekly('X_SVX_KJA', 'KEEP')
    if k==1:
        jobs = [j for j in jobs if j['tail']=='T1']
    return dict(jobs=jobs, tails=resources({f'T{i}':'SVX' for i in range(1,k+1)}),
        old_D3=None if k==3 else 'not applicable',
        scope='K1 selected B2 T1 jobs; K2 full B2; K3 same B2 jobs + conditional RRJ T3, old D3 UNKNOWN')

def calendar_events(jobs, tails, year, month, turn=60):
    """Continuous padded periodic calendar, then select UTC month departures.

    Include previous and next week as boundary context, never reset position
    or turn at week/month boundaries. Dates/weekday counts are real. Inputs
    may have multiple paths/jobs per week and multi-day jobs. Long jobs require
    a larger pad, calculated from their actual event span.
    """
    start, end = bounds(year, month)
    bytail = {t['id']:t for t in tails}
    if len(bytail)!=len(tails):
        raise ValueError('duplicate tail')
    reserve = [t for t in tails if t.get('reserve')]
    if len(reserve)!=1:
        raise ValueError('one separate explicit reserve required')
    if any(not t.get('available_from') or not t.get('available_to') or
           t.get('initial_location') in (None,'UNKNOWN','MOW') for t in tails):
        raise ValueError('explicit availability and physical initial positions required')
    if not (dt(reserve[0]['available_from'])<=start and dt(reserve[0]['available_to'])>=end):
        raise ValueError('reserve unavailable for full month')
    fs = [f for j in jobs for f in j['flights']]
    if len({f['flight_id'] for f in fs})!=len(fs):
        raise ValueError('duplicate template flight; unify retained old jobs before combining paths')
    for f in fs:
        if f['tail'] not in bytail:
            raise ValueError('MISSING_WORKING_RESOURCE:'+f['tail'])
        if bytail[f['tail']].get('reserve'):
            raise ValueError('RESERVE_USED_AS_WORKING')
        if f['origin']=='MOW' or f['destination']=='MOW':
            raise ValueError('physical airport required')
        if f['origin'] not in ZONES or f['destination'] not in ZONES:
            raise ValueError('missing timezone')
        if f['block']<=0 or abs(f['arr']-f['dep']-f['block'])>1e-6:
            raise ValueError('invalid block')
    pad = max(7, math.ceil(max([abs(f['dep'])+f['block'] for f in fs] or [0])/1440)+7)
    first = start-timedelta(days=start.weekday()+pad)
    first -= timedelta(days=first.weekday())
    last = end+timedelta(days=pad)
    allflights = []
    monday = first
    while monday<last:
        for j in jobs:
            for f in j['flights']:
                dep = monday+timedelta(minutes=f['dep'])
                arr = monday+timedelta(minutes=f['arr'])
                t = bytail[f['tail']]
                # Require availability for flights touching the evaluated month;
                # surrounding repetitions only check periodic seams.
                touching = dep<end and arr>=start
                if touching and (dep<dt(t['available_from']) or arr>dt(t['available_to'])):
                    raise ValueError('OUTSIDE_RESOURCE_AVAILABILITY')
                if touching and t['type'].startswith('SJ'):
                    if dep<dt('2027-07-01T00:00:00Z') or dep<dt(t['available_from']):
                        raise ValueError('SJ_BEFORE_H2_AND_SCENARIO_ENTRY')
                fid = f['flight_id']+'@'+monday.date().isoformat()
                allflights.append(dict(flight_id=fid, rotation_id=j['id']+'@'+monday.date().isoformat(),
                    template_id=f['flight_id'], tail=f['tail'], origin=f['origin'], destination=f['destination'],
                    departure_utc=dep.isoformat(), arrival_utc=arr.isoformat(),
                    departure_local=dep.astimezone(ZoneInfo(ZONES[f['origin']])).isoformat(),
                    arrival_local=arr.astimezone(ZoneInfo(ZONES[f['destination']])).isoformat(),
                    local_iso_weekday=dep.astimezone(ZoneInfo(ZONES[f['origin']])).isoweekday(),
                    block_minutes=f['block'], kind='positioning' if f['kind']=='PAID_FERRY' else 'service',
                    evidence=f.get('evidence','SCENARIO')))
        monday += timedelta(days=7)
    daily = Counter()
    carry = {}
    for tid,t in bytail.items():
        seq = sorted([f for f in allflights if f['tail']==tid],key=lambda f:dt(f['departure_utc']))
        pos, ready = t['initial_location'], None
        for f in seq:
            dep, arr = dt(f['departure_utc']), dt(f['arrival_utc'])
            if pos!=f['origin'] or (ready is not None and dep<ready):
                raise ValueError('CONTINUOUS_POSITION_OVERLAP_OR_TURN:'+f['flight_id'])
            for w in t.get('maintenance_windows',[]):
                if dep<dt(w['end']) and arr>dt(w['start']) and dep<end and arr>=start:
                    raise ValueError('MAINTENANCE_CONFLICT')
            pos, ready = f['destination'], arr+timedelta(minutes=turn)
            cursor = max(dep,start)
            while cursor<min(arr,end):
                edge=min(arr,end,datetime.combine(cursor.date()+timedelta(days=1),datetime.min.time(),UTC))
                daily[tid,cursor.date().isoformat()] += (edge-cursor).total_seconds()/3600
                cursor=edge
        for label,cut in [('start',start),('end',end)]:
            prior=[f for f in seq if dt(f['departure_utc'])<cut]
            f=prior[-1] if prior else None
            carry[tid+'/'+label]=dict(position=(('IN_AIR:'+f['origin']+'>'+f['destination'])
                if dt(f['arrival_utc'])>cut else f['destination']) if f else t['initial_location'],
                ready_utc=(dt(f['arrival_utc'])+timedelta(minutes=turn)).isoformat() if f else None,
                flight=f['flight_id'] if f else None)
    flights=[f for f in allflights if start<=dt(f['departure_utc'])<end]
    if len({f['flight_id'] for f in flights})!=len(flights):
        raise ValueError('duplicate dated inventory')
    dr=[dict(tail=t,date=d,block_hours=h) for (t,d),h in sorted(daily.items())]
    errs=[r['tail']+'/'+r['date']+':SCENARIO_8BH_NOT_FDP' for r in dr if r['block_hours']>8+1e-8]
    return dict(status='CONDITIONAL_EXACT_MONTH_NOT_DISPATCH',flights=flights,daily=dr,
        errors=errs,rotations=[],reserve=[t['id'] for t in reserve],carry=carry,
        boundary_flights=[f for f in allflights if dt(f['departure_utc'])<start<dt(f['arrival_utc'])],
        calendar=exposure(year,month),initial_positions_basis='explicit periodic-scenario anchor, not actual dispatch',
        accounting='departures/whole-flight cost by UTC departure month; BH split UTC midnight; local weekday exported')

def pool_days(total, year, month, multipliers=None):
    """Jan holiday/sales-day stress redistributes ONE monthly pool; no new OD."""
    n=calendar.monthrange(year,month)[1]
    weights=[(multipliers or {}).get(date(year,month,d).isoformat(),1.0) for d in range(1,n+1)]
    if total<0 or min(weights)<0 or sum(weights)<=0:
        raise ValueError('invalid daily exposure')
    return {date(year,month,d+1).isoformat():total*w/sum(weights) for d,w in enumerate(weights)}

def evaluate_month(states, tails, year, month, scenario='base', demand_overrides=None,
                   response='passive', full=False):
    """P31 joint calculation + frozen P06 allocator, same world in all 3 states.

    Direct-only primary. Each call is joint across old/new flights and tails.
    No cache or optimizer. Supports K3 through one declared in-memory resource
    enum extension; economics/allocation code unchanged. Thread unsafe by design.
    """
    if set(states)!={'KEEP','WITHOUT_NEW','REPLACE'}:
        raise ValueError('all three states required')
    if any(t['type'].startswith('SJ') for t in tails):
        raise ValueError('PD8 economics UNKNOWN; use resource envelope, not RRJ costing')
    re=engine()
    cals={s:calendar_events(j,tails,year,month) for s,j in states.items()}
    start,end=bounds(year,month)
    endday=(end-timedelta(days=1)).date().isoformat()
    world={(re.city(f['origin']),re.city(f['destination'])) for c in cals.values()
           for f in c['flights'] if f['kind']=='service'}
    world |= {(b,a) for a,b in world}
    n=sum(not t.get('reserve') for t in tails)
    if n not in (1,2,3):
        raise ValueError('1/2/3 working + separate reserve')
    orig=(re.choice_bundle,re.costs,re.OPS_CALENDAR.generate,re.evaluate_combined_programme)
    def choice(flights,sc,affected,a,b,overrides=None,react='passive'):
        commercial=[f for f in flights if f['saleable_seats']>0 and f['calendar_kind']=='service']
        bun=orig[0](commercial,sc,world,a,b,overrides,react)
        # Ferry does not increase commercial frequency/utility. Its physical
        # zero-seat inventory and costs remain in the full joint calculation.
        bun['flights']=flights
        # Zero-seat positioning stays physical/costed but is never marketed.
        seats={f['flight_instance_id']:f['saleable_seats'] for f in flights}
        bun['products']=[p for p in bun['products'] if p['owner']!='RW' or
            all(seats[x]>0 for x in p['legs'])]
        return bun
    def variable(a,b,sc,hours=None):
        c=dict(orig[1](a,b,sc,hours))
        rate=float(re.COSTS['HIST-crew_rub_per_hour']['base_point' if sc=='base' else 'cautious_point'])
        fixed=c['block_hours_costscreen']*rate
        c['fixed_crew_excluded']=fixed
        c['other_cost']-=fixed
        c['fixed_cost']-=fixed
        return c
    def exact(req):
        return req['calendar_result']
    if n==3:
        src=inspect.getsource(orig[3])
        needle='existing_slots not in (0,1,2)'
        if src.count(needle)!=1:
            raise ValueError('P31 enum seam changed; re-audit required')
        local={}
        exec(compile(src.replace(needle,'existing_slots not in (0,1,2,3)'),'<P38_resource_enum_only>','exec'),re.__dict__,local)
        joint=local['evaluate_combined_programme']
    else:
        joint=orig[3]
    results={}
    re.choice_bundle, re.costs, re.OPS_CALENDAR.generate = choice,variable,exact
    try:
        for state in ('WITHOUT_NEW','REPLACE'):
            req={label:dict(tails=copy.deepcopy(tails),blocks=[],patterns=[],turn_minutes=60,
                           calendar_result=cals[s]) for label,s in [('P',state),('KEEP','KEEP')]}
            z=joint([],scenario,keep_patterns=[],start=start.date().isoformat(),end=endday,
                demand_overrides=demand_overrides,donor_loss=None,omitted_F=None,existing_slots=n,
                delivery_scenario='S0',reserve_available=None,response=response,calendar_requests=req)
            if 'programme' not in z:
                raise ValueError('P31 rejected complete calendar: '+str(z.get('status')))
            results[state]=z['programme']
            results['KEEP']=z['keep']
    finally:
        re.choice_bundle,re.costs,re.OPS_CALENDAR.generate,re.evaluate_combined_programme=orig
    subt={s:z['known_contribution'] for s,z in results.items()}
    out=dict(month=f'{year}-{month:02}',scenario=scenario,working_tails=n,separate_reserve='R1',
        exposure=exposure(year,month),primary='DIRECT_ONLY',through_products=0,
        states={s:dict(subtotal=subt[s],journeys=z['rw_journeys'],net_revenue=z['net_revenue'],
            variable_cost=z['known_cost'],departures=len(cals[s]['flights']),
            BH8_diagnostics=cals[s]['errors']) for s,z in results.items()},
        new_minus_same_without=subt['REPLACE']-subt['WITHOUT_NEW'],
        old_change_minus_keep=subt['WITHOUT_NEW']-subt['KEEP'],
        total_minus_keep=subt['REPLACE']-subt['KEEP'],fullPnL=None,cash=None,
        old_D3=None if n==3 else 'not applicable',resource_admission='hypothetical; actual release/reserve UNKNOWN',
        resource_enum_extension='P31 0/1/2 to 0/1/2/3 in memory only' if n==3 else None)
    if full:
        out.update(results=results,calendars=cals)
    return out

def inverse_threshold(required_revenue, net, departures, seats=100):
    if net<=0 or departures<=0:
        raise ValueError('positive net and dated departures required')
    q=max(0,required_revenue)/(net*departures)
    return dict(required_q_per_departure=q,capacity_possible=q<=seats,
        interpretation='necessary revenue/capacity threshold; inverse OD needs joint choice re-run')

def inverse_od(programmes, target, tails, year, month, scenario='base',
               focus_pairs=None, omitted_difference=0, iterations=18):
    """Bounded inverse OD calculation against an explicit same-cohort menu.

    No network generation. Demand changes in ALL alternatives/states together.
    Reports a bracketed numerical crossing, not an observed market or global
    optimum. Actual omitted_difference is UNKNOWN unless explicitly supplied;
    zero here is a labelled lower-bound experiment, never financial admission.
    """
    if target not in programmes or not programmes:
        raise ValueError('target and explicit alternatives required')
    re=engine()
    start,end=bounds(year,month)
    keep=lambda ss:json.dumps(ss['KEEP'],sort_keys=True)
    if len({keep(ss) for ss in programmes.values()})!=1:
        raise ValueError('alternatives must have identical KEEP obligations')
    pairs={tuple(sorted((re.city(a),re.city(b)))) for a,b in (focus_pairs or [])}
    if not pairs:
        raise ValueError('explicit focus city pairs required')
    pools={f'{a}>{b}/{year}-{month:02}':re.annual(a,b,scenario,year)[0]*.5*
        re.P05.monthly_profile(year)[month]/.6 for pair in pairs for a,b in (pair,pair[::-1])}
    if any(v is None or v<0 for v in pools.values()):
        raise ValueError('explicit prior/override required')
    cache={}
    def score(scale):
        if scale not in cache:
            override={k:v*scale for k,v in pools.items()}
            zs={k:evaluate_month(s,tails,year,month,scenario,override) for k,s in programmes.items()}
            alt=[(z['states'][state]['subtotal'],k+'/'+state)
                for k,z in zs.items() for state in ('KEEP','WITHOUT_NEW','REPLACE')
                if (k,state)!=(target,'REPLACE')]
            best=max(alt)
            margin=zs[target]['states']['REPLACE']['subtotal']-best[0]-omitted_difference
            cache[scale]=(margin,best[1])
        return cache[scale]
    grid=[0,.25,.5,1,2,4,8,16,32,64]
    samples=[dict(scale=x,margin=score(x)[0],best_alternative=score(x)[1]) for x in grid]
    base=dict(month=f'{year}-{month:02}',scenario=scenario,target=target,
        alternative_menu=list(programmes),primary='DIRECT_ONLY',focus_pools=pools,
        baseline_margin=score(1)[0],omitted_difference=omitted_difference,
        admission='conditional prior sensitivity; omitted actual F/D/C/ownloss UNKNOWN',
        samples=samples,maximum_tested_scale=64,global_minimum_proved=False)
    if score(0)[0]>0:
        return dict(base,status='ALREADY_AHEAD_WITH_ZERO_FOCUS_OD',crossing_scale=0)
    bracket=next(((a,b) for a,b in zip(grid,grid[1:]) if score(a)[0]<=0<score(b)[0]),None)
    if bracket is None:
        return dict(base,status='NO_WINNING_OD_IN_TESTED_BRACKET',crossing_scale=None,
            explanation='No positive crossing through64x prior; capacity/net/cost or alternative may bind. Not an infinite-demand proof.')
    lo,hi=bracket
    for _ in range(iterations):
        mid=(lo+hi)/2
        if score(mid)[0]>0:hi=mid
        else:lo=mid
    return dict(base,status='BRACKETED_CONDITIONAL_CROSSING',crossing_scale=hi,
        required_change_from_prior_fraction=hi-1,
        required_directed_monthly_potential={k:v*hi for k,v in pools.items()},
        bracket=[lo,hi],bracket_margins=[score(lo)[0],score(hi)[0]],
        explanation='One numerical crossing against stated menu; inspect sampled monotonicity, no global minimum or observed OD claim.')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--month',required=True)
    ap.add_argument('--candidate',default='X_SVX_KJA')
    ap.add_argument('--scenario',choices=['base','cautious'],default='base')
    args=ap.parse_args()
    y,m=map(int,args.month.split('-'))
    if y!=2027:
        raise ValueError('P38 calendar target is 2027')
    st={s:p36_weekly(args.candidate,s) for s in ('KEEP','WITHOUT_NEW','REPLACE')}
    print(json.dumps(evaluate_month(st,resources(candidate_positions(args.candidate)),y,m,args.scenario),ensure_ascii=False,indent=2,allow_nan=False))
