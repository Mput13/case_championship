#!/usr/bin/env python3
"""P34: finite conditional programmes, full February; writes only HERE.

No network, git, legacy builds, annualisation, dispatch or investment decision.
Run python3 -B context/34_new_direct_top5_20261112/calculation/verify.py
for two actual calculations, invariants, byte determinism and protection.
"""
import sys
sys.dont_write_bytecode = True
import calendar
import copy
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = HERE.parent
C31 = ROOT/'context/31_direct_growth_research_20261112'
C32 = ROOT/'context/32_delay_cargo_research_20261112'
C33 = ROOT/'context/33_svx_aer_launch_case_20261112'
START, END = '2027-02-01', '2027-02-28'
UTC = timezone.utc
TURN = 60
ZONES = {'SVX':'Asia/Yekaterinburg','KUF':'Europe/Samara','OMS':'Asia/Omsk',
         'GOJ':'Europe/Moscow','KJA':'Asia/Krasnoyarsk','TOF':'Asia/Tomsk',
         'PEE':'Asia/Yekaterinburg','REN':'Asia/Yekaterinburg',
         'TJM':'Asia/Yekaterinburg','CEK':'Asia/Yekaterinburg',
         'MRV':'Europe/Moscow','IKT':'Asia/Irkutsk','VVO':'Asia/Vladivostok',
         'KHV':'Asia/Vladivostok','AER':'Europe/Moscow'}
VERSION = 'P34-FEB4-S1-v1'
AER_TRIANGLE = 'TRI:SVX-AER-MRV'

def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(name, value):
    assert Path(name).name == name
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    sort_keys=True, allow_nan=False)+'\n')

def table(name, rows, fields=None):
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    assert fields and Path(name).name == name
    with (HERE/name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k:'NULL' if v is None else round(v,8) if isinstance(v,float) else v
                        for k,v in r.items()})

def load(name, path):
    s = importlib.util.spec_from_file_location(name,path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

RE = load('p34_completed_route_economics', C31/'route_economics/calculate.py')
DC = load('p34_completed_delay', C32/'calculation/calculate.py')
ORIGINAL_CHOICE = RE.choice_bundle
ORIGINAL_GENERATE = RE.OPS_CALENDAR.generate

def dt(value):
    t = datetime.fromisoformat(value.replace('Z','+00:00'))
    assert t.tzinfo is not None
    return t.astimezone(UTC)

def local(day, clock, airport='SVX'):
    return datetime.fromisoformat(day+'T'+clock).replace(tzinfo=ZoneInfo(ZONES[airport])).astimezone(UTC)

def minutes(delta):
    return delta.total_seconds()/60

def pair(a,b):
    return '-'.join(sorted((a,b)))

def require_feb4(start,end):
    # This workaround deliberately refuses partial months/boundary windows.
    # It does NOT repair the entire legacy API.
    assert (start,end)==(START,END), 'Only full 28-day February 2027 admitted'
    assert (date.fromisoformat(end)-date.fromisoformat(start)).days+1 == 28

FOLLOW = [r for r in read(C32/'calculation/control_flights.csv')
          if r['route']=='SVX-OMS' and r['layout']=='EQUAL_BUFFER_B30' and r['control']=='KEEP']
assert len(FOLLOW)==4

def block(a,b):
    if (a,b) in {('SVX','OMS'),('KUF','SVX')}: return 100
    if (a,b) in {('OMS','SVX'),('SVX','KUF')}: return 105
    if set((a,b))=={'SVX','AER'}: return 210
    return round(RE.geometry(a,b)[1]*60)

def block_source(a,b):
    if set((a,b)) in ({'SVX','OMS'},{'SVX','KUF'}):
        return 'P32_DIRECTED_RRJ95B_ANALOGUE_NOT_OBSERVED_2027_BLOCK'
    if set((a,b))=={'SVX','AER'}: return 'P33_CORRECTED_210_EACH_EXPLICIT_SCENARIO_NOT_OBSERVED'
    return 'SCENARIO_ROUNDED_P31_GEOMETRY_NOT_DISPATCH_BLOCK'

def pattern(id_,path,weekday,clock,daystart=START,dayend=END,positioning=()):
    return dict(id=id_,path=path,weekdays=[weekday],frequency_per_week=1,
                start=daystart,end=dayend,departure_local=clock,
                workingtailids=['E1'],positioning_leg_indices=list(positioning))

def retained_patterns():
    ps=[]
    # The 75-min gap KUF->OMS in P32 is preserved by separate closed RTs.
    # Fri is the exact +3-day date translation of the SAME B variant.
    for dow in (2,5):
        for i in (0,2):
            f=FOLLOW[i]
            day='2027-02-02' if i==0 else '2027-02-03'
            t=dt(f['dep_utc']).astimezone(ZoneInfo(ZONES['SVX']))
            actualdow=dow if i==0 else dow+1
            ps.append(pattern('RET-'+str(dow)+'-'+f['destination'],
                              ['SVX',f['destination'],'SVX'],actualdow,
                              t.strftime('%H:%M')))
    return ps

def keep_patterns():
    return retained_patterns()+[
        pattern('DONOR-TUE-OMS',['SVX','OMS','SVX'],2,'18:00'),
        pattern('DONOR-FRI-KUF',['SVX','KUF','SVX'],5,'18:00')]

def project_patterns(name, clock='07:00'):
    ps=retained_patterns()
    if name=='KEEP': return keep_patterns()
    if name==AER_TRIANGLE:
        # Exactly one existing P31 triangle, not a new combinatorial search.
        legacy=json.loads((C31/'route_economics/patterns.json').read_text())
        src=next(p for p in legacy if p['pattern_id']==AER_TRIANGLE)
        path=src['airports']
        assert path==['SVX','AER','MRV','SVX']
        return ps+[pattern('NEW-TUE-AER-MRV',path,2,clock),
                   pattern('NEW-FRI-AER-MRV',list(reversed(path)),5,clock)]
    if name.startswith('AER'):
        ps.append(pattern('NEW-TUE-AER',['SVX','AER','SVX'],2,clock))
        ps.append(pattern('DONOR-FRI-KUF',['SVX','KUF','SVX'],5,'18:00') if name=='AER1'
                  else pattern('NEW-FRI-AER',['SVX','AER','SVX'],5,clock))
        return ps
    a,b=name.split('-')
    if a=='SVX':
        ps += [pattern('NEW-TUE-'+b,[a,b,a],2,clock),
               pattern('DONOR-FRI-KUF',['SVX','KUF','SVX'],5,'18:00')]
    else:
        # Short, unsupported feeders are PAID nonrevenue positioning in main.
        ferry=lambda path:[i for i,(x,y) in enumerate(zip(path,path[1:]))
                           if 'SVX' in (x,y) and (y if x=='SVX' else x) in ('CEK','TJM','PEE')]
        for dow,path in [(2,['SVX',a,b,'SVX']),(5,['SVX',b,a,'SVX'])]:
            ps.append(pattern('NEW-'+('TUE' if dow==2 else 'FRI')+'-'+name,
                              path,dow,clock,positioning=ferry(path)))
    return ps

def request(patterns):
    keys=sorted({(a,b) for p in patterns for a,b in zip(p['path'],p['path'][1:])})
    return dict(tails=[dict(id='E1',type='RRJ-95B',saleable_seats=100,
                            initial_location='SVX',available_from=START+'T00:00:00Z',
                            available_to=END+'T23:59:59Z',reserve=False,
                            donor='S1 controlled OMS Tue / KUF Fri; actual release UNKNOWN'),
                       dict(id='R1',type='RRJ-95B',reserve=True,initial_location='UNKNOWN',
                            donor='UNKNOWN; conditional separate reserve never scheduled')],
                blocks=[dict(origin=a,destination=b,nominal_minutes=block(a,b),
                             high_minutes=None,evidence=block_source(a,b),aircraft_variant='RRJ-95B') for a,b in keys],
                timezones=ZONES,turn_minutes=TURN,diagnostic_bh_day=8,
                block_case='nominal',patterns=patterns)

def cost_only_calendar(req):
    """Explicit bridge: only 8BH diagnostic failures permit full economics.

    All original errors and all flights survive. No overlap/position failure is
    admitted. P31's resource screen still returns its 8BH violations. This is a
    conditional cost screen, never a second crew envelope or dispatch PASS.
    """
    z=ORIGINAL_GENERATE(req)
    if z['errors'] and all(e.endswith('SCENARIO_8BH_SCREEN_EXCEEDED_NOT_CREW_LAW') for e in z['errors']):
        z['status']='COST_ONLY_FULL_CALENDAR_8BH_FAILED_OPS_QUEUE'
    return z

def evaluate(name, scenario='base', noadj=False, clock='07:00', fare_scale=1.0):
    require_feb4(START,END)
    pp,kp=project_patterns(name,clock),keep_patterns()
    reqs={'P':request(pp),'KEEP':request(kp)}
    a,b=('AER','MRV') if name==AER_TRIANGLE else ('SVX','AER') if name.startswith('AER') else name.split('-') if name!='KEEP' else ('SVX','OMS')
    newkey=pair(a,b)
    def joint_choice(flights,sc,affected,start,end,demand_overrides=None,response='passive'):
        require_feb4(start,end)
        bun=ORIGINAL_CHOICE(flights,sc,affected,start,end,demand_overrides,response)
        fs={f['flight_instance_id']:f for f in flights}
        kept=[]
        for p in bun['products']:
            if p['owner']!='RW': kept.append(p);continue
            f=fs[p['legs'][0]]
            isnew=f['pattern_id'].startswith('NEW-')
            ispair=pair(f['origin_airport'],f['destination_airport'])==newkey
            if noadj and isnew and not ispair: continue
            if isnew and ispair and fare_scale!=1:
                gross,net=RE.fare(f['origin_airport'],f['destination_airport'],sc,
                                  p['gross_fare']*fare_scale)
                # Change actual joint product gross/net; retain calibrated-to-
                # scenario intercept so the price utility also changes.
                p['gross_fare'],p['net_fare']=gross,net
            kept.append(p)
        bun['products']=kept
        return bun
    RE.choice_bundle=joint_choice
    RE.OPS_CALENDAR.generate=cost_only_calendar
    try:
        z=RE.evaluate_combined_programme(pp,scenario,keep_patterns=kp,start=START,end=END,
             donor_loss=None,omitted_F=None,existing_slots=1,delivery_scenario='S0',
             reserve_available=None,calendar_requests=reqs)
    finally:
        RE.choice_bundle=ORIGINAL_CHOICE
        RE.OPS_CALENDAR.generate=ORIGINAL_GENERATE
    z['name'],z['new_pair'],z['requests']=name,newkey,reqs
    return z

def valid_economics(z): return 'programme' in z

def scoped_alloc(z,label='programme'):
    data=z[label]
    ps={p['product_id']:p for p in data['bundle']['products']}
    fs={f['flight_instance_id']:f for f in data['bundle']['flights']}
    out=[]
    for x in data['allocation']['allocations']:
        if x['owner']!='RW':continue
        p=ps[x['product_id']];f=fs[p['legs'][0]]
        key=pair(f['origin_airport'],f['destination_airport'])
        group=('NEW_PAIR' if key==z['new_pair'] else 'ADJACENT') if f['pattern_id'].startswith('NEW-') else 'DONOR' if f['pattern_id'].startswith('DONOR-') else 'RETAINED_OLD_RW'
        out.append(dict(group=group,origin=f['origin_airport'],destination=f['destination_airport'],
                        q=x['carried'],requested=x['requested'],net=p['net_fare'],gross=p['gross_fare'],
                        revenue=x['carried']*p['net_fare'],fid=f['flight_instance_id']))
    return out

def totals(z,group=None,label='programme'):
    rs=[r for r in scoped_alloc(z,label) if group is None or r['group']==group]
    return sum(r['q'] for r in rs),sum(r['revenue'] for r in rs)

def programme_row(z,scenario,noadj):
    raw=z['ops_results']['P']
    fail=[e for e in raw['errors'] if not e.endswith('SCENARIO_8BH_SCREEN_EXCEEDED_NOT_CREW_LAW')]
    common=dict(programme=z['name'],scenario=scenario,adjacent_case='NO_UNCONFIRMED_REVENUE' if noadj else 'P05_ADJACENT_PRIOR',
                comparison_group='LEGACY_AER_TRIANGLE_S1_SCENARIO' if z['name']==AER_TRIANGLE else 'SHUTTLE_CONTROL' if z['name'].startswith('AER') else 'KEEP_CONTROL' if z['name']=='KEEP' else 'TOP5_ALL12_NEWPAIR_QUEUE',
                horizon=START+'/'+END,weeks=4,tail='E1',reserve='R1_UNRELEASED',
                physical_sectors_month=len(raw['flights']),physical_sectors_week=len(raw['flights'])/4,
                block_hours_month=sum(f['block_minutes'] for f in raw['flights'])/60,
                block_hours_week=sum(f['block_minutes'] for f in raw['flights'])/240,
                diagnostic_8BH_failures=len(raw['errors'])-len(fail),
                P31_resource_screen=z.get('resource_necessary_screen','HARD_CALENDAR_FAILURE'),
                geometry_status='INVALID_D0_OR_WINDOW_OPS_QUEUE' if fail else 'SCENARIO_TIMING_ONLY_OPS_QUEUE',
                existing_slots=None,actual_D=None,external_donor=None,F_setup_lease_reserve=None,
                cash=None,full_PnL=None,observed_OD=None,observed_20kg_netfare=None,
                fuel_support=0,route_grant=0,cargo_main=0)
    if not valid_economics(z):
        return dict(common,known_P_minus_KEEP_month=None,known_P_minus_KEEP_week=None,
                    net_revenue_P_month=None,avoidable_cost_P_month=None,net_revenue_KEEP_month=None,
                    avoidable_cost_KEEP_month=None,new_pair_journeys_month=None,new_pair_revenue_month=None,
                    adjacent_journeys_month=None,adjacent_revenue_month=None,incremental_unique_RW=None,
                    missing_retained_lossbudget=None,reason=';'.join(fail))
    p,k=z['programme'],z['keep'];q,r=totals(z,'NEW_PAIR');qa,ra=totals(z,'ADJACENT')
    return dict(common,known_P_minus_KEEP_month=p['known_contribution']-k['known_contribution'],
                known_P_minus_KEEP_week=(p['known_contribution']-k['known_contribution'])/4,
                net_revenue_P_month=p['net_revenue'],avoidable_cost_P_month=p['known_cost'],
                net_revenue_KEEP_month=k['net_revenue'],avoidable_cost_KEEP_month=k['known_cost'],
                new_pair_journeys_month=q,new_pair_revenue_month=r,
                adjacent_journeys_month=qa,adjacent_revenue_month=ra,
                model_RW_journeys_P=p['rw_journeys'],model_RW_journeys_KEEP=k['rw_journeys'],
                model_RW_journey_change=p['rw_journeys']-k['rw_journeys'],incremental_unique_RW=None,
                saturated_flights=sum(s['unsold_seats']<1e-6 and s['saleable_seats']>0 for s in p['allocation']['seats']),
                missing_retained_lossbudget=0,reason='All four following tasks after each slot retained; outside/through RW loss UNKNOWN')

def serialize_flights(name,z):
    fs=sorted(z['ops_results']['P']['flights'],key=lambda f:f['departure_utc'])
    previous=None
    rows=[]
    for f in fs:
        gap=None if previous is None else minutes(dt(f['departure_utc'])-dt(previous['arrival_utc']))
        rid=f['rotation_id'].split('/')[0]
        group='NEW_PAIR' if rid.startswith('NEW-') and pair(f['origin'],f['destination'])==z['new_pair'] else 'ADJACENT' if rid.startswith('NEW-') else 'DONOR' if rid.startswith('DONOR-') else 'RETAINED_OLD_RW'
        rows.append(dict(programme=name,flight_id=f['flight_id'],tail=f['tail'],origin=f['origin'],destination=f['destination'],
                         departure_utc=f['departure_utc'],arrival_utc=f['arrival_utc'],departure_local=f['departure_local'],arrival_local=f['arrival_local'],
                         block_minutes=f['block_minutes'],group=group,kind=f['kind'],turn_required=TURN,
                         preceding_ground_minutes=gap,saleable_seats=0 if f['kind']=='positioning' else 100,
                         evidence=f['evidence'],date_status='SCENARIO',actual_registration=None,
                         slot=None,crew_FDP_rest=None,MRO=None,AFM_payload=None,type_route_release=None))
        previous=f
    return rows

def delay_rows(name,z,window='MAIN'):
    # P32 replay's id-specific shock is bound explicitly to each target below.
    rotations=defaultdict(list)
    for f in z['ops_results']['P']['flights']:rotations[f['rotation_id']].append(f)
    # Preserve the physical task order even when an invalid21:00 AER plan
    # overlaps FOLLOW. It must fail D0, not borrow an aircraft mid-rotation.
    fs=[f for rr in sorted(rotations.values(),key=lambda rr:min(f['departure_utc'] for f in rr))
        for f in sorted(rr,key=lambda f:f['departure_utc'])]
    firstweek=[f for f in fs if f['departure_utc'][:10]<='2027-02-06']
    candidates=[f for f in firstweek if f['rotation_id'].startswith('NEW-') and pair(f['origin'],f['destination'])==z['new_pair']]
    # A Tue-only SVX RT/AER1 has no Friday NEW_PAIR. Explicitly stress the
    # retained Friday donor as a different control, never invent a new leg.
    candidates += [f for f in firstweek if f['rotation_id'].startswith('DONOR-FRI-')]
    events=[];summaries=[]
    for target in candidates:
        # Separate Tue and Fri shocks, including their paid positioning and all
        # subsequent common tasks through Saturday. No midnight reset.
        chain=[]
        for f in firstweek:
            fid='NEW-OUT' if f['flight_id']==target['flight_id'] else f['flight_id']
            chain.append(DC.flight(fid,f['origin'],f['destination'],dt(f['departure_utc']),f['block_minutes'],
                                   'new' if f['rotation_id'].startswith('NEW-') else 'retained',f['evidence']))
        index={id(x):f for x,f in zip(chain,firstweek)}
        for shock in (0,30,60,120):
            rr=DC.replay(chain,TURN,shock=shock,initial_ready=local(START,'00:00'))
            d0=all(abs(r['dep_delay'])<1e-8 for r in DC.replay(chain,TURN,shock=0,initial_ready=local(START,'00:00')))
            late=[]
            for x in rr:
                f=index[id(x['flight'])]
                if x['dep_delay']>0 and not f['rotation_id'].startswith('NEW-'):late.append(f['flight_id'])
                events.append(dict(programme=name,window=window,target_id=target['flight_id'],target_day=target['departure_local'][:10],
                         target_group='NEW_PAIR' if target['rotation_id'].startswith('NEW-') else 'FRI_KEEP_DONOR_CONTROL_NO_NEW_PAIR',
                         target_binding='Only this target is aliased to P32 NEW-OUT; explicit initial_ready',shock_minutes=shock,
                         flight_id=f['flight_id'],origin=f['origin'],destination=f['destination'],
                         planned_dep_utc=f['departure_utc'],actual_dep_utc=x['actual_dep'].isoformat(),
                         planned_arr_utc=f['arrival_utc'],actual_arr_utc=x['actual_arr'].isoformat(),
                         actual_dep_local=x['actual_dep'].astimezone(ZoneInfo(ZONES[f['origin']])).isoformat(),
                         actual_arr_local=x['actual_arr'].astimezone(ZoneInfo(ZONES[f['destination']])).isoformat(),
                         departure_delay_minutes=x['dep_delay'],planned_buffer_minutes=x['buffer'],
                         D0_valid=d0,ground_delay_block_cost=0,delay_probability=None,RUB_per_minute=None,
                         automatic_cancellation=None,crew_remaining=None,R1_extra_capacity=False))
            summaries.append(dict(target_id=target['flight_id'],target_group='NEW_PAIR' if target['rotation_id'].startswith('NEW-') else 'FRI_KEEP_DONOR_CONTROL_NO_NEW_PAIR',shock=shock,D0_valid=d0,late_retained=';'.join(late)))
    return events,summaries

def delay_boundaries(name,z):
    """Aircraft absorption boundary only; target-side remaining block budget."""
    fs=sorted(z['ops_results']['P']['flights'],key=lambda f:f['departure_utc'])
    rows=[]
    for target in fs:
        if target['departure_local'][:10] not in ('2027-02-02','2027-02-05'):continue
        if not target['rotation_id'].startswith('NEW-') or pair(target['origin'],target['destination'])!=z['new_pair']:continue
        remaining=[f for f in fs if f['rotation_id']==target['rotation_id'] and f['departure_utc']>=target['departure_utc']]
        last=max(remaining,key=lambda f:f['arrival_utc'])
        # Same dated retained task, even if an invalid plan crosses its clock.
        dow=2 if target['departure_local'][:10]=='2027-02-02' else 5
        nxt=next(f for f in fs if f['rotation_id'].startswith('RET-'+str(dow)+'-KUF/') and f['departure_local'][:10]==target['departure_local'][:10])
        buffer=minutes(dt(nxt['departure_utc'])-dt(last['arrival_utc']))-TURN
        maxblock=minutes(dt(nxt['departure_utc'])-dt(target['departure_utc']))-len(remaining)*TURN-120
        rows.append(dict(programme=name,scenario='base',axis='AIRCRAFT_ONLY_ABSORB120',target_id=target['flight_id'],
                         next_retained_id=nxt['flight_id'],buffer_to_next_retained_min=buffer,
                         remaining_planned_block_min=sum(f['block_minutes'] for f in remaining),
                         max_remaining_block_min_absorb120=maxblock,extra_block_headroom_min=buffer-120,
                         required_block_shortening_or_extra_buffer_min=max(0,120-buffer),
                         absorb120=buffer>=120,crew_remaining=None,extra_resource_cost=None,
                         unit='MINUTES_NOT_FDP',formula='remainingBH <= nextKEEPdep-targetdep-remaininglegs*turn-120; no midnight reset'))
    return rows

def thresholds(z,scenario):
    if not valid_economics(z) or z['name']=='KEEP':return []
    alloc=scoped_alloc(z);rs=[r for r in alloc if r['group']=='NEW_PAIR']
    dirs=sorted({(r['origin'],r['destination']) for r in rs})
    assert len(dirs)==2
    q=[sum(r['q'] for r in rs if (r['origin'],r['destination'])==d) for d in dirs]
    n=[RE.fare(*d,scenario)[1] for d in dirs]
    caps=[sum(f['saleable_seats'] for f in z['programme']['bundle']['flights']
              if (f['origin_airport'],f['destination_airport'])==d and f['pattern_id'].startswith('NEW-')) for d in dirs]
    # K includes net revenue/cost of all donors and retained tasks once through
    # the full joint P-minus-KEEP; other revenues held fixed for these axes.
    delta=z['known_increment_P_minus_KEEP_before_F_donor']
    K=sum(r['revenue'] for r in rs)-delta
    common=dict(programme=z['name'],scenario=scenario,adjacent_case='NO_UNCONFIRMED_REVENUE',
                direction_a='>'.join(dirs[0]),direction_b='>'.join(dirs[1]),
                fixed_other_net_cost_RUB=K,model_net_a=n[0],model_net_b=n[1],model_q_a=q[0],model_q_b=q[1],
                capacity_a=caps[0],capacity_b=caps[1],actual_old_netfare=None,
                factual_F_donor=None,unit='MONTH_FEB2027',scope='Boundary before outside losses/F; fixed other costs and revenues')
    rows=[]
    def add(axis,**kw):rows.append(dict(common,axis=axis,**kw))
    sym=K/sum(n)
    add('SYMMETRIC_JOINT_Q_BOUNDARY',q_a_required=sym,q_b_required=sym,
        feasible_with_seats=0<=sym<=min(caps),formula='q*(net_a+net_b)=K; symmetry diagnostic, not two independent minima')
    for other in (0,q[1],caps[1]):
        req=(K-other*n[1])/n[0]
        add('Q_A_GIVEN_Q_B',q_b_fixed=other,q_a_required=req,
            feasible_with_seats=0<=req<=caps[0],formula='q_a=(K-q_b*net_b)/net_a')
    for other in (0,q[0],caps[0]):
        req=(K-other*n[0])/n[1]
        add('Q_B_GIVEN_Q_A',q_a_fixed=other,q_b_required=req,
            feasible_with_seats=0<=req<=caps[1],formula='q_b=(K-q_a*net_a)/net_b')
    scale=K/sum(qi*ni for qi,ni in zip(q,n)) if sum(q)>0 else None
    add('NET_FARE_SCALE_FIXED_Q',net_scale_required=scale,
        net_a_required=None if scale is None else n[0]*scale,net_b_required=None if scale is None else n[1]*scale,
        formula='scale=K/(q_a*net_a+q_b*net_b); NOT a price-demand forecast')
    # Exterior own migration only, disjoint from DONOR/RETAINED losses already
    # in K. Migrants occupy new seats and lose old revenue; no free backfill.
    for frac in (0,.25,.5):
        ma,mb=q[0]*frac,q[1]*frac
        old=n # explicitly SIGNED sensitivity reference; actual yield NULL.
        required=(K+ma*(old[0]-n[0])+mb*(old[1]-n[1]))/sum(n)
        add('CLEAN_NEW_Q_SYMMETRIC_WITH_OUTSIDE_MIGRATION',outside_migration_fraction=frac,
            migrated_a=ma,migrated_b=mb,oldnet_scenario_a=old[0],oldnet_scenario_b=old[1],
            q_a_required=required,q_b_required=required,available_new_seats_a=caps[0]-ma,available_new_seats_b=caps[1]-mb,
            feasible_with_seats=0<=required<=min(caps[0]-ma,caps[1]-mb),
            outside_lost_revenue=ma*old[0]+mb*old[1],
            formula='n_a*qnew_a+n_b*qnew_b=K+sum(m*(oldnet-newnet)); qnew+m<=seats; no backfill')
    # P31 main excludes the uncertain per occupied segment charge. Never add
    # 500/650 to an already inclusive cost without invoice-level nonoverlap.
    p=z['programme']['rw_journeys'];k=z['keep']['rw_journeys']
    rate=500 if scenario=='base' else 650
    add('SIGNED_NONOVERLAP_PAX_COST_STRESS',stress_rate=rate,assumption='EXTRA_NONOVERLAP_ONLY; NOT_AN_INVOICE',
        signed_delta_cost=(p-k)*rate,delta_after_stress=delta-(p-k)*rate,
        formula='delta_stress=delta-rate*(occupied_P-occupied_KEEP)')
    add('CARGO_REQUIRED_NET_CONTRIBUTION',required_net_cash=max(0,-delta),cargo_orders=None,cargo_net_rate=None,payload_remaining=None,
        formula='max(0,-known_delta); add actual F and outside loss; no kg/rate/contract inferred')
    return rows

def protect():
    pins=json.loads((C33/'protected_files.json').read_text())
    assert len(pins)==1190
    bad=[p for p,h in pins.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not bad, 'Protected1190 content changed: '+str(bad)
    return dict(count=len(pins),mismatches=bad,head_assertion=False,
                tracked_total_rule='May exceed 1190; no git operation or HEAD equality check')

def frequency_fixture():
    def simple(days):
        return [dict(flight_instance_id='FIX-'+str(d),pattern_id='FIX',origin_airport='SVX',destination_airport='KJA',
               departure_utc=f'2027-02-{d:02}T02:00:00Z',arrival_utc=f'2027-02-{d:02}T05:20:00Z',
               block_hours_costscreen=200/60,saleable_seats=100) for d in days]
    old=ORIGINAL_CHOICE(simple([2]),'base',{('SVX','KJA')},START,'2027-02-07')
    full=ORIGINAL_CHOICE(simple([2,9,16,23]),'base',{('SVX','KJA')},START,END)
    f=lambda z:next(p['frequency'] for p in z['products'] if p['owner']=='RW')
    assert f(old)==.25 and f(full)==1
    assert abs(full['markets'][0]['potential_journeys']/old['markets'][0]['potential_journeys']-4)<1e-10
    for start,end in [('2027-01-29','2027-02-04'),('2027-02-22','2027-03-07'),(START,'2027-02-07')]:
        try:require_feb4(start,end)
        except AssertionError:pass
        else:raise AssertionError('partial or month-boundary exposure admitted')
    return dict(real_P31_7day_frequency=f(old),full_Feb_four_departures_frequency=f(full),
                actual_week_frequency=1,monthly_demand_over_7day=4,demand_prorate_count=1,
                month_boundary_policy='REJECT: full-Feb workaround only; no general legacy repair',annualisation=False)

def build():
    protection=protect();fixture=frequency_fixture()
    seed=read(STUDY/'team_audit/candidate_seed.csv')
    assert len(seed)==12
    names=[r['pair'] for r in seed]+['AER1','AER2','KEEP',AER_TRIANGLE]
    all_z={};prows=[];frows=[];brows=[];ledgers=[];checks=[]
    for name in names:
        for sc in ('base','cautious'):
            for noadj in (False,True):
                z=evaluate(name,sc,noadj,clock='14:00' if name.startswith('AER') else '07:00')
                all_z[name,sc,noadj]=z
                prows.append(programme_row(z,sc,noadj))
                if sc=='base' and not noadj:frows+=serialize_flights(name,z)
                if noadj:brows+=thresholds(z,sc)
                if valid_economics(z):
                    for label in ('programme','keep'):
                        data=z[label]
                        for s in data['allocation']['seats']:
                            assert s['carried_segments']<=s['saleable_seats']+1e-7
                        # Independent pool conservation, beyond the engine's
                        # own assertion; P and KEEP use identical potentials.
                        pools={(m['demand_pool_id'],m['month'],m['customer_segment']):m['potential_journeys'] for m in data['bundle']['markets']}
                        for key,potential in pools.items():
                            used=sum(a['final_choice'] for a in data['allocation']['allocations']
                                     if (a['demand_pool_id'],a['month'],a['customer_segment'])==key)
                            assert abs(used-potential)<1e-6
                        groups=defaultdict(lambda:[0.,0.,0.])
                        alloc=scoped_alloc(z,label)
                        fm={f['flight_instance_id']:f for f in data['bundle']['flights']}
                        for a in alloc:groups[a['group']][0]+=a['q'];groups[a['group']][1]+=a['revenue']
                        for fid,f in fm.items():
                            rid=f['pattern_id'];key=pair(f['origin_airport'],f['destination_airport'])
                            g=('NEW_PAIR' if key==z['new_pair'] else 'ADJACENT') if rid.startswith('NEW-') else 'DONOR' if rid.startswith('DONOR-') else 'RETAINED_OLD_RW'
                            groups[g][2]+=RE.costs(f['origin_airport'],f['destination_airport'],sc,f['block_hours_costscreen'])['fixed_cost']
                        for g,(q,rev,cost) in groups.items():
                            ledgers.append(dict(programme=name,scenario=sc,adjacent_case='NO_UNCONFIRMED_REVENUE' if noadj else 'P05_ADJACENT_PRIOR',
                                 side='P' if label=='programme' else 'KEEP',group=g,journeys_month=q,net_revenue_month=rev,
                                 avoidable_cost_month=cost,contribution_month=rev-cost,
                                 factual_revenue=None,factual_avoidable_cost=None,donor_deducted_again=False))
                        assert abs(sum(v[1] for v in groups.values())-data['net_revenue'])<1e-6
                        assert abs(sum(v[2] for v in groups.values())-data['known_cost'])<1e-6
                    pots=lambda side:{(m['demand_pool_id'],m['month'],m['customer_segment']):m['potential_journeys'] for m in z[side]['bundle']['markets']}
                    assert pots('programme')==pots('keep')
                    checks.append(dict(name=name,scenario=sc,noadj=noadj,seat_conservation=True,OD_conservation=True,identical_P_KEEP_potential=True,donor_once=True))
    recovery_a={r['pair']:r for r in read(STUDY/'source_recovery_new/classification.csv') if r['period']=='target'}
    recovery_b={r['pair']:r for r in read(STUDY/'source_recovery_competitors/classification.csv')}
    candidates=[]
    for r in seed:
        name=r['pair'];z=all_z[name,'base',True];full=all_z[name,'base',False];c=all_z[name,'cautious',True]
        econ=valid_economics(z)
        cls=recovery_a[name]['classification'] if name in recovery_a else recovery_b[name]['target_class'] if name in recovery_b else 'LOW_EVIDENCE_QUEUE'
        group='TYPE_A_UNCONFIRMED' if name in recovery_a else 'TYPE_B_RW_UNCHECKED' if name in recovery_b else 'LOW_EVIDENCE_QUEUE'
        q,rev=totals(z,'NEW_PAIR') if econ else (None,None)
        candidates.append(dict(pair=name,classification=cls,queue_group=group,qualified_new_route=False,conditional_rank=None,
             base_noadj_delta_month=z.get('known_increment_P_minus_KEEP_before_F_donor'),
             base_noadj_delta_week=z.get('known_increment_P_minus_KEEP_before_F_donor')/4 if econ else None,
             cautious_noadj_delta_month=c.get('known_increment_P_minus_KEEP_before_F_donor'),
             base_with_adjacent_delta_month=full.get('known_increment_P_minus_KEEP_before_F_donor'),
             adjacent_dependency_month=(full['known_increment_P_minus_KEEP_before_F_donor']-z['known_increment_P_minus_KEEP_before_F_donor']) if econ else None,
             new_pair_journeys_month=q,new_pair_net_revenue_month=rev,new_pair_RT_week=1,
             programme_sectors_week=len(z['ops_results']['P']['flights'])/4,
             annual_demand_basis=RE.annual(*name.split('-'),'base',2027)[1],
             observed_OD=None,observed_netfare=None,observed_20kg_grossquote=None,
             rw_nonstop='UNKNOWN',incremental_unique_RW=None,actual_donor=None,full_PnL=None,
             ops_queue='D0_WINDOW_CONFLICT_RETAINED_LOSS_UNKNOWN' if not econ else 'SCENARIO_BLOCK_TYPE_PAYLOAD_CREW_MRO_SLOT_RESERVE_RELEASE_PENDING_8BH_DIAGNOSTIC',
             own_history='UNRESOLVED_RELAUNCH_HISTORY_NOT_EXCLUDED' if name=='SVX-KJA' else 'UNKNOWN',
             passenger_hypothesis='Endpoint VFR/business; MRV also health/leisure; timing and willingness to pay unmeasured',
             source='source_recovery_new/classification.csv' if name in recovery_a else 'source_recovery_competitors/classification.csv' if name in recovery_b else 'team_audit/candidate_seed.csv'))
    # Conditional verification order by no-unconfirmed-adjacent revenue floor.
    # Low evidence and physical conflicts stay in all12 matrix, outside top5.
    ranked=sorted([r for r in candidates if r['base_noadj_delta_month'] is not None and r['queue_group']!='LOW_EVIDENCE_QUEUE'],
                  key=lambda r:(-r['base_noadj_delta_month'],r['pair']))
    for i,r in enumerate(ranked,1):r['conditional_rank']=i
    top=ranked[:5]
    assert len(top)==5 and not any(r['qualified_new_route'] for r in candidates)
    table('candidate_comparison.csv',candidates);table('top5_conditional.csv',top)
    table('programme_comparison.csv',prows);table('flights.csv',frows)
    table('programme_ledger.csv',ledgers)
    selected=[r['pair'] for r in top[:3]]
    delays=[];summary={}
    for name in selected+['AER1','AER2',AER_TRIANGLE]:
        ev,ss=delay_rows(name,all_z[name,'base',True]);delays+=ev;summary[name]=ss
        brows+=delay_boundaries(name,all_z[name,'base',True])
    table('break_even.csv',brows)
    windows=[]
    for clock in ('07:00','14:00','21:00'):
        z=evaluate('AER1','base',True,clock)
        ev,ss=delay_rows('AER1',z,clock);delays+=ev
        new=[f for f in z['ops_results']['P']['flights'] if f['rotation_id'].startswith('NEW-')][:2]
        following=next(f for f in sorted(z['ops_results']['P']['flights'],key=lambda f:f['departure_utc']) if f['rotation_id'].startswith('RET-2'))
        gap=minutes(dt(following['departure_utc'])-dt(new[-1]['arrival_utc']))-TURN
        # At fixed q/cost, net discount capacity is delta/q. Negative means an
        # uplift is needed. Reference is P05 model only, no quoted discount.
        reference=all_z['AER1','base',True]
        q,rev=totals(reference,'NEW_PAIR');gross,net=RE.fare('SVX','AER','base')
        allowance=reference['known_increment_P_minus_KEEP_before_F_donor']/q
        for shock in (0,30,60,120):
            sx=next(s for s in ss if s['shock']==shock)
            windows.append(dict(clock_SVX=clock,date='2027-02-02',status='SCENARIO_ONLY' if sx['D0_valid'] else 'INVALID_D0_WINDOW_CONFLICT',
                 out_departure_UTC=new[0]['departure_utc'],out_arrival_AER_local=new[0]['arrival_local'],
                 return_departure_AER_local=new[1]['departure_local'],return_arrival_SVX_local=new[1]['arrival_local'],
                 block_out=210,block_return=210,turn=TURN,shock_minutes=shock,D0_valid=sx['D0_valid'],
                 following_buffer_minutes=gap,absorb120=gap>=120,max_total_block_absorb120=minutes(dt(following['departure_utc'])-dt(new[0]['departure_utc']))-2*TURN-120,
                 late_following=sx['late_retained'],reference='SIGNED_P05_BASE_MODEL_ONLY_AER1_FIXED_Q_FEB4; NOT_CLOCK_PREMIUM',
                 reference_gross= gross,reference_net=net,raw_max_net_discount_RUB_per_journey=allowance,
                 max_nonnegative_net_discount=max(0,allowance),required_net_uplift=max(0,-allowance),
                 gross_discount_equivalent=allowance/.97,actual_quoted_discount=None,existing_slot=None,clock_price_effect=None,
                 crew_remaining=None,extra_resource_cost=None))
    table('delay_events.csv',delays);table('AER_window_comparison.csv',windows)
    # Exact net revenue audit of joint fare override, at a nonzero reduction.
    reference=all_z[selected[0],'base',True]
    altered=evaluate(selected[0],'base',True,fare_scale=.9)
    old=next(r for r in scoped_alloc(reference) if r['group']=='NEW_PAIR')
    new=next(r for r in scoped_alloc(altered) if r['group']=='NEW_PAIR')
    assert abs(new['net']/old['net']-.9)<1e-9 and abs(new['gross']/old['gross']-.9)<1e-9
    # Explicit donor, adjacent, yield, BH/payload, season and migration flips.
    flips=[]
    rate=RE.costs('SVX','KJA','base',1)['fixed_cost']-RE.costs('SVX','KJA','base',0)['fixed_cost']
    for r in top:
        name=r['pair'];z=all_z[name,'base',True];delta=r['base_noadj_delta_month'];q,rev=totals(z,'NEW_PAIR')
        nonpair=rev-delta
        for f,detail,value in [
            ('EXTERIOR_F_PLUS_DONOR_TO_KEEP','Loss outside scoped ledger only; negative means deficit before omissions',delta),
            ('NEWPAIR_NET_YIELD_SCALE_TO_KEEP','Fixed q and all other revenues/costs',nonpair/rev),
            ('PERIOD_Q_REVENUE_MULTIPLIER_TO_KEEP','Fixed fares, own mix and all other items; not seasonal forecast',nonpair/rev),
            ('ADJACENT_NET_REVENUE_NEEDED_TO_KEEP','Starting from noadj stress; unrecovered feeder revenues not automatic',max(0,-delta)),
            ('EXTRA_BLOCK_HOURS_TO_KEEP','Marginal P04 fuel/MRO/block crew/navigation; cycles fixed; negative=no headroom',delta/rate),
            ('PAYLOAD_SEAT_REDUCTION_TO_KEEP','Symmetric lost q, same ref yields; not AFM allowance',delta/(2*RE.fare(*name.split('-'),'base')[1])),
            ('OUTSIDE_MIGRATION_SHARE_TO_KEEP','Lost OLD net=P05 new net signed reference, no backfill, exterior only',delta/rev)]:
            flips.append(dict(programme=name,against='KEEP',axis=f,threshold=value,unit='RUB_MONTH' if f in ('EXTERIOR_F_PLUS_DONOR_TO_KEEP','ADJACENT_NET_REVENUE_NEEDED_TO_KEEP') else 'MODEL_AXIS',
                              explanation=detail,actual_value=None))
    for a,b in zip(top,top[1:]):
        za=all_z[a['pair'],'base',True];zb=all_z[b['pair'],'base',True]
        gap=a['base_noadj_delta_month']-b['base_noadj_delta_month'];q,rev=totals(za,'NEW_PAIR')
        flips.append(dict(programme=a['pair'],against=b['pair'],axis='ADDITIONAL_DISJOINT_DONOR_F_LOSS',threshold=gap,unit='RUB_MONTH',actual_value=None,
                          explanation='A loses rank when extra outside loss_A-loss_B exceeds threshold; both internal donors already in ledger'))
        flips.append(dict(programme=a['pair'],against=b['pair'],axis='NET_YIELD_DROP_FIXED_Q',threshold=gap/q,unit='RUB_PER_JOURNEY',actual_value=None,
                          explanation='Fixed B and A q; A new-pair net revenue reduction only'))
        na=RE.fare(*a['pair'].split('-'),'base')[1]
        for axis,value,unit,detail in [
            ('OUTSIDE_MIGRATION_SHARE_RANK_FLIP',gap/rev,'SHARE','Exterior only, oldnet=newnet signed reference; no backfill'),
            ('ADJACENT_NET_REV_LOSS_RANK_FLIP',gap,'RUB_MONTH','Additional disjoint A adjacent/retained revenue loss; B fixed'),
            ('PERIOD_NEWPAIR_REVENUE_MULTIPLIER_RANK_FLIP',1-gap/rev,'MULTIPLIER','A q*yield scales, B and all other costs/revenues fixed'),
            ('EXTRA_BH_RANK_FLIP',gap/rate,'BLOCK_HOURS_MONTH','A additional directed block cost only; cycles fixed'),
            ('PAYLOAD_LOST_Q_RANK_FLIP',gap/(2*na),'MONTH_JOURNEYS_PER_DIRECTION','Symmetric lost carried q; /4 per departure, not AFM seat allowance')]:
            flips.append(dict(programme=a['pair'],against=b['pair'],axis=axis,threshold=value,unit=unit,actual_value=None,explanation=detail))
    table('donor_rank_flip.csv',flips)
    # Full author direct reference is preserved WITHOUT a resize into E1.
    author_legs=[r for r in read(C31/'ops_inputs/reference_physical_legs.csv') if r['programme']=='dashboard_fixed_triangles']
    table('author_triangle_reference.csv',author_legs)
    author_status=[]
    summaries=read(RE.BASE/'data/processed/network_summary.csv')
    for sc in ('base','cautious'):
        r=next(r for r in read(C31/'ops_inputs/reference_feasibility.csv')
               if r['programme']=='dashboard_fixed_triangles' and r['case']==sc and r['resource']=='E1/S0' and r['month']=='2027-02')
        original=[r for r in summaries if r['scenario']==sc and 'Прям' in r['variant']]
        author_status.append(dict(case=sc,full_original_pattern_count=len({r['pattern'] for r in author_legs if r['case']==sc}),
               full_physical_departures_representative_week=float(r['physical_departures_representative_week']),
               full_costscreen_BH_week=float(r['costscreen_BH_week']),proxy_min_working_tails=int(r['costscreen_min_working']),
               protected_reserve_conditional=1,actual_available_tail_count=None,
               original_author_summary=original,
               status='FULL_AUTHOR_REFERENCE_NOT_RESOURCE_MATCHED_TO_E1',
               scheduled_dates=None,actual_crew_MRO_slots=None,E1_profit_attribution=None,
               resized=False,missing_taildays_and_retained_lossbudget=None,
               caveat='Original annual author outputs are historical scenario reference only; not rerun/admitted/profit or E1 money. P03 hours proxy is not actual dispatch resource proof.'))
    dump('author_reference_status.json',author_status)
    tri_main=all_z[AER_TRIANGLE,'base',False];tri_stress=all_z[AER_TRIANGLE,'base',True]
    dump('AER_triangle_admission.json',dict(pattern_id=AER_TRIANGLE,
          source='context/31_direct_growth_research_20261112/route_economics/patterns.json',
          source_path=['SVX','AER','MRV','SVX'],Tue=['SVX','AER','MRV','SVX'],Fri=['SVX','MRV','AER','SVX'],
          changed_dated_clocks='Scenario07:00 SVX on Feb Tue/Fri; reverse Fri added to cover both directions; no legacy money reused',
          same_resource='E1/R1/S1 donor/FOLLOW exactly as all12',project_sectors_week=6,focal_pair_RT_week=1,
          focal_pair='AER-MRV for stress accounting only; no newness claim',
          selection_reason='The only AER triangle in completed P31 patterns; all three directed adjacent OD priors and geometry exist, no KUF/UFA invented. No broad search.',
          base_joint_delta_with_adjacent=tri_main.get('known_increment_P_minus_KEEP_before_F_donor'),
          base_joint_delta_no_unconfirmed_adjacent=tri_stress.get('known_increment_P_minus_KEEP_before_F_donor'),
          paired_observed_variant_blocks=None,type_payload_crew_MRO_slots=None,actual_donor=None,
          status='CONDITIONAL_COST_ONLY_OPS_QUEUE_NOT_PROVEN_BETTER'))
    admission=[
        dict(input='TASKS;source_pins;team_audit',use='Contract and seed; all complete',limit='Pins are provenance, not OD/netyield observations'),
        dict(input='source_recovery_new',use='4 canonical classifications UNKNOWN',limit='No full dated operator registry; cannot rename UNKNOWN as new'),
        dict(input='source_recovery_competitors',use='6 competitor nonstop; own RW NOT_CONFIRMED',limit='No proof of RW absence; KHV Feb reverse coverage unknown'),
        dict(input='PEE-TOF;OMS-REN',use='All12 low evidence queue, thresholds calculated',limit='Not promoted into top5 to fill evidence gap'),
        dict(input='research_new_markets;research_competitors',use='NOT_CANONICAL_NOT_USED',limit='First not external research; second broken build'),
        dict(input='P08/P09',use='Available hypothesis/coverage only; P08I real-name scan absent',limit='No observed OD or netyield; P09 scope not E1 winter comparison'),
        dict(input='fresh step1 network/rw_routes_now',use='Byte equality checked vs pinned P31',limit='Sparse marketing list not complete own nonstop registry; old through clients not zero'),
        dict(input='P31 evaluate_combined_programme + P05/P04 + P06',use='Single programme and KEEP, shared directed pools and physical seats',limit='Prior/choice uncalibrated, actual F/PnL/cash NULL'),
        dict(input='P31 calendar_engine.generate',use='All physical legs and original errors preserved',limit='Cost-only bridge for sole 8BH diagnostic error; no approval; other failures give NULL economics'),
        dict(input='P32 control_flights.csv',use='SVX-OMS EQUAL_BUFFER_B30 KEEP four FOLLOW; Fri +3d, weekly +7d',limit='Same RRJ95B scenario, actual tail/crew/slots/MRO UNKNOWN'),
        dict(input='P32 replay',use='Explicit target alias NEW-OUT, initial_ready; 30/60/120 Tue/Fri',limit='No midnight reset, ground hold not added to BH, no probability/autocancel model'),
        dict(input='P33 operations original',use='QUARANTINE; separately reconstruct AER 210/210 turn60',limit='Original UTC elapsed330/150; original FOLLOW not used'),
        dict(input='P33 AER completion',use='AER1/AER2/KEEP and 3 clocks with shocks and signed discount threshold',limit='210 is scenario/analogue; convenience fare and factual slots UNKNOWN')]
    admission += [dict(input='P31 existing TRI:SVX-AER-MRV',use='One AER triangle Tue and reverse Fri on same S1; full6legs',limit='Same joint priors/costs plus noadj stress; paired variant/blocks UNKNOWN, not proven better'),
                  dict(input='Full author direct triangle reference',use='All96 directed rows across base/cautious preserved separately, original resource/summary retained',limit='No E1 resize or annual money transfer; actual dated feasibility/donor UNKNOWN')]
    table('admission.csv',admission)
    assumptions=[
      ('A01','Period',START+'/'+END,'Full month, 4 exact Tue/Fri weeks; sums month and /4; no 52/48'),
      ('A02','Resource','E1 existing RRJ-95B 100 seats + separate R1','Variant/registration/release/location of reserve UNKNOWN; no new SJ before H22027'),
      ('A03','Window','07:00 SVX project; AER main14:00; donors18:00; first FOLLOW23:55','Scenario window ends first retained dep minus60; no removed retained task'),
      ('A04','Demand','P05 annual prior / .6 * .5 * Febprofile','One prorate only; gravity OMS-PEE explicit; no observed endpoint OD'),
      ('A05','Money','P04 base/cautious same inherited contract','Constant2026 RUB. Gross/(1+VAT)*(1-distribution); BASE0/.03, cautious.10/.08'),
      ('A06','Costs','P04 directed-block fuel/cycle + MRO/block crew/nav + ground/deice','Avoidable scenario costs only; salaries/lease/setup/reserve actual NULL'),
      ('A07','Support/cargo',0,'Main fuel/grant/cargo0; required cargo netcash only, no orders/rates/payload'),
      ('A08','Exterior own','NULL','Old marketing customers exist; own through/partner unmodelled. Loutside0/25/50 diagnostics only; no observed own=0'),
      ('A09','Donors','Tue OMS RT / Fri KUF RT','Same retained B30 calendar both sides; actual D NULL; loss inside P-KEEP not subtracted again'),
      ('A10','Adjacency','P05 prior plus no-unconfirmed-revenue stress','CEK/TJM/PEE feeders paid ferry in main. No new base; no implicit through fare'),
      ('A11','Pax cost','500 base /650 cautious NONOVERLAP_STRESS_ONLY','Signed occupied-sector difference; invoice overlap UNKNOWN'),
      ('A12','Missing costs','NULL','Factual F/setup/lease/reserve/cash/fullPnL NULL; 0 omissions only stated boundary'),
      ('A13','Payload/crew/slots/MRO','NULL','8BH diagnostic not FDP; geometry not dispatch; probability/RUBminute/cancel NULL'),
      ('A14','Ranking','Base noadj P-KEEP finite seed conditional queue','Not exhaustive maximum, not proven profit, not decision; no pilot for smaller loss')]
    table('assumptions.csv',[dict(id=i,item=k,value=v,limitation=l) for i,k,v,l in assumptions])
    table('assumption_changes.csv',[
      dict(id='C01',old='7day choice freq .25',new='Full Feb4weeks; four departures=1/week',reason='User-required workaround; no P31 edit, no demand compensation'),
      dict(id='C02',old='P33 clocks330/150; erroneous FOLLOW',new='AER210/210 turn60 UTC-derived; FOLLOW only P32 B30',reason='Timezone/turn correction; originals preserved'),
      dict(id='C03',old='No controlled actual KEEP/D',new='One explicit S1 scenario donor+FOLLOW cycle',reason='User-authorized boundary; actual donor/release still NULL'),
      dict(id='C04',old='8BH engine rejects complete calendar',new='Cost-only bridge for sole8BH failures, original errors+resource fail survive',reason='No envelope increase/no trimming/no dispatch. Hard errors NULL economics'),
      dict(id='C05',old='Unsupported short adjacent revenue',new='CEK/TJM/PEE ferry paid; noadj stress on every other project adjacent leg',reason='No free feeder revenue. Same physical costs retained'),
      dict(id='C06',old='AER shuttle controls only',new='Add one ready P31 SVX-AER-MRV triangle plus reverse orientation; original full author reference separately preserved',reason='User scope clarification; same S1 programme; no new city search or money attribution')])
    reqs=[
      ('NEWNESS','Commercial/network','Dated full own/operator register both directions, ordinary16–22Nov and each Feb week; flights/marketing/partner/charter','Qualify new, relaunch or frequency comparator; none qualified now'),
      ('OD','Revenue management','Directed endpoint bookings, cancellations, dates, customer/itinerary IDs including own through/partner and backfill','Replace prior; deduplicate old customers/new journeys and migration'),
      ('YIELD','Commercial/finance','Same quote timestamp economy1adultOW20kg+allfees; gross coupon/VAT/distribution/net reconciliation','No observed basket; test break_even net axes'),
      ('DONOR','Fleet/network/finance','E1 registration/variant release, actual Tue/Fri programmes and all later tasks; net revenue and genuinely avoided costs','Internal donor once; replace S1 and price unmodelled lost own itineraries'),
      ('OPS','Flight operations','Directed winter block/high, routing, AFM payload, available100seats, airport hours/slots, legal FDP/rest, crew changes, MRO','No scenario marked dispatch; close8BH/type/payload/window gates'),
      ('R1','Fleet/finance','Separate released reserve registration/location and cost, positioning/overnight/incremental crew','Reserve not free working capacity; price missing F'),
      ('AER','Slots/pricing','Actual3clock slots and comparable baskets, convenience discounts by date, block210 validation','Clock-price effects/actual discount NULL;5000 expert example not forecast'),
      ('COST','Finance','Fuel/uplift ground/deice/pax fee invoices, VAT eligibility/recovery, costavoidability, setup/lease/cash timing','Prevent VAT/fees/pax500650 doublecount; full profitability unavailable'),
      ('CARGO','Cargo','Net contribution contract, costs, payload/baggage residual, paid weight/rate','Threshold only; no speculative cargo income')]
    table('RW_data_request.csv',[dict(id=i,owner=o,request=q,decision_gate=g) for i,o,q,g in reqs])
    dump('request_config.json',dict(version=VERSION,period=[START,END],turn=TURN,diagnostic_BH=8,
         selected=selected,main_clock_AER='14:00',main_clock_candidates='07:00',
         follow_source='P32 SVX-OMS EQUAL_BUFFER_B30 KEEP; +3days Fri, +7days repeated',
         reserve='R1 never scheduled; actual release/cost NULL',selection='TOP5_CONDITIONAL_CANDIDATES'))
    dump('model_checks.json',dict(frequency=fixture,protection=protection,joint_fare_override=dict(gross_ratio=new['gross']/old['gross'],net_ratio=new['net']/old['net']),
          evaluated_complete_cases=len(checks),allocation_checks=checks,qualified_new_routes=[],selected=selected,
          control_KEEP_identity=all_z['KEEP','base',True]['known_increment_P_minus_KEEP_before_F_donor'],
          delay_summary=summary))
    write_readme(top,selected,all_z,windows)
    # Inputs are pinned by content, never by a stale current HEAD.
    inputs=[STUDY/'TASKS.md',STUDY/'source_pins.json',C33/'protected_files.json',
            C31/'route_economics/calculate.py',C31/'ops_inputs/calendar_engine.py',C32/'calculation/calculate.py',C32/'calculation/control_flights.csv']
    inputs += [C31/'route_economics/patterns.json',C31/'ops_inputs/reference_physical_legs.csv',C31/'ops_inputs/reference_feasibility.csv',RE.BASE/'data/processed/network_summary.csv']
    for folder in ('team_audit','source_recovery_new','source_recovery_competitors'):
        paths=(STUDY/folder).glob('*') if folder=='team_audit' else (STUDY/folder).rglob('*')
        inputs += [p for p in paths if p.is_file() and '__pycache__' not in p.parts]
    dependencies=json.loads((STUDY/'team_audit/dependency_receipt.json').read_text())
    # Pin every declared legacy dependency without copying any package.
    for r in dependencies:
        p=ROOT/r['path'];assert sha(p)==r['sha256'];inputs.append(p)
    fresh=STUDY/'team_audit/source_snapshot/data'
    for rel in ('manual/rw_routes_now.csv','assumptions/network.csv'):
        assert (fresh/rel).read_bytes()==(RE.BASE/'data'/rel).read_bytes()
    protect()
    dump('manifest.json',dict(version=VERSION,period=[START,END],qualified_new_routes=[],
        scope='Finite all12 conditional seed; no exhaustive maximum/proven profit/adopted decision',
        no_HEAD_assertion=True,protection_count=1190,
        inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(set(inputs))],
        outputs=[dict(path=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(HERE.iterdir())
                 if p.is_file() and p.name not in ('manifest.json','validation.json')]))
    print(json.dumps(dict(status='CALCULATED_CONDITIONAL_REVIEW_REQUIRED',qualified_new_routes=0,
                         top5=[r['pair'] for r in top],selected=selected),ensure_ascii=False))

def write_readme(top,selected,all_z,windows):
    lines=[
      '# Условная очередь P34 — полный февраль 2027',
      '',
      f'Первая пара для проверки при выбранной нижней стресс-границе noadj: **{top[0]["pair"]}**, только условно; при полном P05 prior порядок иной. qualified_new_routes = **0**. Это конечное сравнение 12 seed, не исчерпывающий максимум, не доказанная прибыль и не принятое решение.',
      '',
      '**Прямой рейс** — перелёт пассажира без пересадки между двумя городами. **Треугольный оборот** — цепочка работы борта из3секторов; каждый соседний пассажирский рынок может быть прямым, но проезд через третий город не становится nonstop. Основная задача — новые пары и прямые продукты в том числе в треугольных оборотах. Челночные AER1/AER2 — только отдельные контроли, не замена всей прямой стратегии.',
      '',
      'NO_UNCONFIRMED_REVENUE — асимметричный стресс выручки: у треугольника сохраняется центральная пара, у SVX–X RT — весь новый рынок. Это не единый реалистичный BASE и не наблюдённая выручка даже центральной пары. Для TRI:SVX–AER–MRV центральная пара AER–MRV, поэтому стресс выключает SVX–AER и SVX–MRV; AER1/AER2 сохраняют SVX–AER. С полными priors BASE очередь тех же кандидатов: GOJ–KJA, TJM–MRV, CEK–MRV, GOJ–TOF, SVX–KJA. GOJ–KJA меняется с −4.244 до +13.211 млн₽/месяц против +5.519 у SVX–KJA: порог восстановления adjacent-дельты55.93% при прочих фиксированных строках. CAUTIOUS GOJ–KJA остаётся отрицательным. Оба предположения условны; по noadj нельзя объявлять всю треугольную сеть хуже. AER-треугольник full-prior BASE+11.659/CAUTIOUS+6.202 против AER2+11.781/+9.222; он выше AER1, но не обязан побеждать AER2.',
      '',
      'TOP5_CONDITIONAL_CANDIDATES — только очередь асимметричного стресса. Полный P05 prior и cautious нужно показывать с той же заметностью. Все денежные числа ниже — вклад до внешних потерь старых RW, F/резерва/setup/lease и прочих пропусков, RUB постоянных цен2026. Отрицательная граница не повод запускать пилот ради меньшего убытка.',
      '',
      '|Условный порядок|Пара|Класс|BASE без adjacent, млн₽/месяц|CAUTIOUS, млн₽/месяц|',
      '|---:|---|---|---:|---:|']
    for i,r in enumerate(top,1):lines.append(f'|{i}|{r["pair"]}|{r["queue_group"]}|{r["base_noadj_delta_month"]/1e6:.3f}|{r["cautious_noadj_delta_month"]/1e6:.3f}|')
    lines += ['',
      'Четыре GOJ–KJA/GOJ–TOF/KUF–TOF/OMS–PEE остаются UNKNOWN: тип A не подтверждён. Шесть TJM–MRV/CEK–MRV/SVX–KJA/SVX–IKT/SVX–VVO/SVX–KHV имеют COMPETITOR_NONSTOP_RW_NOT_CONFIRMED: тип B с непроверенным собственным RW. PEE–TOF/OMS–REN сохранены в low evidence queue. Подтверждённых частотных comparator из этих12 нет: при подтверждении собственного nonstop перевести туда. История SVX–KJA его не исключает; relaunch unresolved.',
      '',
      'Период **01–28Feb2027**, Tue02/09/16/23 и Fri05/12/19/26. Месяц и /4 — единственные агрегации; без 52/48. P31 choice_bundle на реальном7day fixture даёт0.25/week для1вылета;4вылета за полный28day февраль дают1/week. Спрос prorate ровно один раз. Это ограниченный workaround, частичные месяцы и переходы границ новый расчёт отвергает.',
      '',
      'S1 KEEP: один условно высвобождаемый действующий RRJ-95B E1 в SVX,100 сценарных кресел, отдельно R1 без плановых рейсов. Tue OMS18:00SVX→20:40OMS;21:40OMS→22:25SVX. Fri KUF18:00SVX→18:45KUF;19:45KUF→22:25SVX. Все часы SCENARIO. После каждого окна — одинаковые4 FOLLOW из P32 SVX-OMS/EQUAL_BUFFER_B30/KEEP: KUF23:55SVX→00:40KUF;01:40KUF→04:20SVX; OMS05:35SVX→08:15OMS;09:15OMS→10:00SVX. Пятничный шаблон сдвинут на3дня, затем повторён на7дней. В P/KEEP эти даты/времена совпадают. Actual KEEP/Dactual/регистрация/резерв-release неизвестны.',
      '',
      'P−KEEP содержит потерю донорской net revenue и избегаемые P04 fuel/cycle/MRO/blockcrew/navigation/ground/deice один раз. programme_ledger.csv разделяет donor/retained/newpair/adjacent по обеим сетям. Неизбежная lease/fixedcrew не вычитается как избегаемый донор. Реальные избегаемость/ставки UNKNOWN. Внешний donor/F/собственные through/partner продажи остаются NULL и отдельными порогами. KEEP−KEEP=0, бизнес KEEP не нулевой.',
      '',
      'Вне SVX обе ориентации SVX–A–B–SVX Tue / SVX–B–A–SVX Fri дают6 проектных секторов и1 RT самой пары в неделю. К ним добавляются8 FOLLOW секторов. Для SVX–X — TueRT, FriKEEP и те же8FOLLOW. Никаких бесплатных новых баз/самолёто-дней или обрезки плеч. Короткие SVX–CEK/TJM/PEE — платные ferry с0выручкой в main; noadj stress выключает и остальную недоказанную project adjacent выручку, сохраняя каждый расход. Услуги остаются scenario, позиционирование E1 к исходной SVX/ночёвка/crew вне явной цепи требуют отдельного F; их фактическая цена NULL.',
      '',
      'Полный календарь выдаёт диагностику8BH. Новый cost_only_calendar пропускает в совместную экономику только календари, где единственный класс ошибок — эта диагностика; все исходные ошибки и полные рейсы сохранены, resource screen остаётся failed/ops queue. Порог8BH не поднят; это не FDP и не допуск. Пересечение с FOLLOW/отрицательный turn/позиция дают NULLэкономику и INVALID_D0, а потери дополнительно снятых retained заданий UNKNOWN. SVX–VVO/KHV не получают бесплатный перенос FOLLOW/дополнительный день.',
      '',
      'Три конкретные программы для предметной проверки (geometry/block сценарии, не «выполнимо»):', '']
    for name in selected:
        z=all_z[name,'base',True]
        fs=[f for f in sorted(z['ops_results']['P']['flights'],key=lambda f:f['departure_utc']) if f['rotation_id'].startswith('NEW-') and f['departure_local'][:10] in ('2027-02-02','2027-02-05')]
        lines.append(f'- **{name}**: '+ '; '.join(f'{f["origin"]} {f["departure_local"]} → {f["destination"]} {f["arrival_local"]} ({f["block_minutes"]}min)' for f in fs)+'. UTC, полные даты и все FOLLOW — flights.csv. Пассажир — только гипотеза endpoint VFR/business, MRV также лечение/отдых; наблюдений цели/объёма нет.')
    lines += ['',
      'Для треугольных программ shock30/60/120 на NEW_PAIR Tue и Fri раздельно. В SVXRT/AER1 новый RT только Tue, поэтому FridayNEWPAIR отсутствует: пятничный shock отдельно помечен FRI_KEEP_DONOR_CONTROL_NO_NEW_PAIR и относится к сохранённому донору, не выдуманному новому плечу. delay_events.csv явно называет target_id/target_group и адаптацию к P32 NEW-OUT, содержит D0 и план/факт UTC/local. Оба направления каждого нового RT/треугольника проверены раздельно. Полночь не сбрасывает задержку. Поздние FOLLOW перечислены в model_checks.json; AIRCRAFT_ONLY_ABSORB120 в break_even.csv даёт буфер/maxremainingblock. Удержание на земле не добавлено к blockhourcost. Вероятность, рубль/минута, автоотмена, crewremaining и extraресурс UNKNOWN; R1 не бесплатная capacity.',
      '',
      'AER завершение P33: 1TueRT+FriKEEP и2RT на том же E1/R1. Main14:00SVX→15:30AER,16:30AER→22:00SVX,210/210+60; UTC09:00→12:30/13:30→17:00. Исходный P33давал330/150, его FOLLOW не использованы. Это исправленная каноническая scenario-таблица в flights.csv, не observed block/dispatch. AER_window_comparison.csv:07/14/21SVX, следующая KEEP и0/30/60/120. 21:00не помещается, D0 INVALID. Удобство/неудобство и слоты по источникам UNKNOWN. Максимальный дисконт — только подписанная модельная граница P05 при фиксированных q/cost, отрицательное значение требует повышения net; expert5000 не прогноз, actualquoteddiscount NULL.',
      '',
      'Дополнительно ровно один готовый AER-треугольник P31: **TRI:SVX-AER-MRV** из route_economics/patterns.json. Tue SVX–AER–MRV–SVX, Fri SVX–MRV–AER–SVX, старт07:00SVX, все6секторов, те же E1/R1, оба донора и8FOLLOW. Это единственный AER-треугольник в готовом P31 наборе: KUF/UFA не изобретались. Все три adjacentOD имеют P05prior/costscreen, pairedblock/вариант не доказаны. Обратная ориентация и новые даты/часы явно SCENARIO; исходные деньги не перенесены. programme_comparison.csv сравнивает base/cautious и стресс без SVX-adjacent выручки, AER_triangle_admission.json объясняет admission. Эта программа не входит в12илиtop5 и не объявлена лучше.',
      '',
      'Полная исходная author triangle reference сохранена отдельно: **author_triangle_reference.csv** содержит все96 directed строк двух составов base/cautious, по8треугольников в каждом. **author_reference_status.json** сохраняет исходный author resource (8бортов BASE,7 CAUTIOUS из network_summary), полный объём204/144сектора/неделю и отдельный P03 hours-only proxy9/8рабочих+условный резерв. Эти ресурсные оценки имеют разные определения; фактические хвосты/crew/MRO и даты UNKNOWN. Никакой обрезки подE1 или переноса годовых авторских денег вS1 нет; исходные годовые суммы — только подписанная historical scenario reference. Недостающие taildays/retained lossbudget UNKNOWN. Основная сеть автора сохранена, челночный AER её не подменяет.',
      '',
      'Экономические границы в break_even.csv — совместная прямая n_a*q_a+n_b*q_b=K, симметричная точка помечена, дополнительно q_a|q_b и обратные оси. Netfare threshold фиксирует q/прочие costs и не предсказывает эластичность. Реальный jointfareoverride проверен: gross/net actualproducts меняются на0.9 и choice пересчитывается; screen(gross_override) не используется. BASE явное насыщение: число saturated_flights в programme_comparison.csv и ограничения P06; это не доказательство спроса. OMS–PEE использует gravity extrapolation, остальные — P05 prior, не прогнозы.',
      '',
      'Общие directed cityOD monthly pools и физические seats P06 не дублируются. Retained OLD_RW включены одинаково и их сдвиг учтён joint. Уникальные новые клиенты RW не равны новым посадкам. Неизмеренные own through/partner клиенты не равны0: Loutside0/25/50% — только отдельная диагностика, исключает уже включённые donor/retained потери. Cleanqnew: n*qnew = K+Σm*(oldnet−newnet), qnew+m≤seats; oldnet в диагностике=P05 newnet, actual NULL, backfill отсутствует. Нельзя вычитать этих же доноров снова или считать migrated новыми клиентами.',
      '',
      'Grossquote≠net: P05 gross/(1+VAT)*(1-distribution), BASE VAT0 только допустимый regional scenario и3%, cautious10%/8%. Fees/VAT повторно не вычитаются. 500/650 только подписанный nonoverlap stress на разность occupiedsegments; подтверждение непересечения invoice-level необходимо. Mainfuel/routesupport/cargo0. Cargo — необходимый денежный netcontribution без подтверждённых заказов/ставок/остатка payload. FactualF/setup/lease/reserve/cash/fullPnL NULL; сравнить фактическую прибыльность нельзя.',
      '',
      'Порог смены места/KEEP в donor_rank_flip.csv: внешний donor/F, netyield, migration, adjacent, period, BH и payload. Это одноосные границы при фиксированных остальных элементах, не вероятности. Общие неизменные пропуски не переворачивают ранг, различающиеся могут. Даже положительный scoped вклад не является основанием запуска без admission gates.',
      '',
      'Функции и области: P31 route_economics.evaluate_combined_programme пересчитывает P и KEEP совместно; P05 annual/prior/monthly_profile/fare/choice задают сценарный спрос/цену; P06 engine.choice.allocate распределяет одни directed city pools по products с общей physical seat capacity. P31 ops_inputs.calendar_engine.generate строит полный датированный календарь/UTC turns/позицию/cycles/BH; новый cost_only_calendar сохраняет sole8BH fail для стоимостной диагностики. P32 flight/replay распространяет один hold по max(plan,ready,othergate,shock); новый delay_rows явно связывает target. thresholds выводит линейные оси, не rerun choice. Ни одна функция не доказывает observed OD, прибыль или dispatch.',
      '',
      'P08 доступен, P08I по реальным именам не найден. P08/P09 не калибруют observedOD/netyield. Свежие rw_routes_now/network побайтно равны P31. Canonical input admission и исходники с локаторами: admission.csv и соседние source_recovery_*; сырые research_* исключены. Не требуется новый внешний поиск.',
      '',
      'Воспроизведение и meaningful checks одной командой из корня:',
      '```sh',
      'python3 -B context/34_new_direct_top5_20261112/calculation/verify.py',
      '```',
      'verify запускает calculate.py реально дважды, проверяет байты outputs, frequency fixture, полную физику/cycles/две стороны/UTC, OD/seat, налоги/fees, jointfare, donoronce/migration, nullable неизвестные, D0/shocks и1190protected содержательно. HEAD не фиксируется, trackedtotal может превышать1190. Никаких legacy build/git/сети/записи вне calculation.',
      '',
      'Положительная AER cautious дельта — эффект сравнения со снятым S1: AER1 новый RT −1.954936 + разница donor contributions6.171065 + retained reallocation0.480534 = +4.696663 млн₽/месяц. AER2: −3.909872 +11.874106 +1.257371 = +9.221605. P31 February daily28 отправлений в каждую сторону давал −36.197822 млн₽ без этого S1; здесь4/8, полный Feb joint allocation и210мин вместо geometry≈213.096. Cautious netfare13,241.423890₽ не повышен и support/cargo0. Это не самостоятельная прибыль AER;8BH/dispatch/unknown-F gates сохраняются.',
      '',
      'Независимый review завершён в ../review/ с вердиктом CHANGES: две правки объяснения применены координатором в генераторе этой записки. Численные CSV не менялись; исправленный итог и оба рейтинга — ../RESULTS.md. Повторной независимой приёмки изменённого текста не заявляется.']
    (HERE/'README.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':build()
