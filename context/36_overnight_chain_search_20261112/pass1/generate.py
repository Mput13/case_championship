#!/usr/bin/env python3
"""P36 pass1. Deterministic bounded weekly search; all writes under this file's dir.

Read-only imports of completed P31/P34 adapters, NEVER their build()/verify().
No network, git mutation, external research, dispatch or optimum assertion.
"""
import sys
sys.dont_write_bytecode = True
import csv
import hashlib
import importlib.util
import io
import itertools
import json
import math
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
TEAM = 'cd04921fe5dd14dbf5c469b7f15a5efc203abc7b'
STEP = '6cbe817320f75db9823984e7c4eeb6091fd7d996'
C31 = ROOT/'context/31_direct_growth_research_20261112'
C34 = ROOT/'context/34_new_direct_top5_20261112'
NODES = ('SVX','ZIA','DME','KUF','UFA','CEK','TJM','OMS','PEE','GOJ','KJA','TOF','MRV','AER','REN','IKT')
ZONES = dict(SVX='Asia/Yekaterinburg', ZIA='Europe/Moscow', DME='Europe/Moscow',
 KUF='Europe/Samara', UFA='Asia/Yekaterinburg', CEK='Asia/Yekaterinburg',
 TJM='Asia/Yekaterinburg', OMS='Asia/Omsk', PEE='Asia/Yekaterinburg',
 GOJ='Europe/Moscow', KJA='Asia/Krasnoyarsk', TOF='Asia/Tomsk', MRV='Europe/Moscow',
 AER='Europe/Moscow', REN='Asia/Yekaterinburg', IKT='Asia/Irkutsk')
UTC = timezone.utc
EPOCH = datetime(2027,2,1,tzinfo=UTC)
END = datetime(2027,3,1,tzinfo=UTC)
WEEK = 7*1440
TURN = 60
WINDOWS = (6,10,14,20)
FREQUENCIES = (1,2,3,5,7)
DAY_OFFSETS = {1:(0,),2:(0,3),3:(0,2,4),5:(0,1,2,3,4),7:tuple(range(7))}
MOVE_OFFSETS = (-180,-120,-60,-30,30,60,120,180)
ACTIONS = ('INSERT',)+tuple('MOVE%+d'%n for n in MOVE_OFFSETS)+('REMOVE1','REMOVE2','REMOVE3','MIN_CLOSURE','ALL_AFFECTED','SWAP')
SOURCES = {}
COUNTS = Counter()

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(name, obj):
    p = HERE/name
    assert p.resolve().is_relative_to(HERE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')

def table(name, rows, fields=None):
    p=HERE/name
    assert p.resolve().is_relative_to(HERE)
    p.parent.mkdir(parents=True,exist_ok=True)
    rows=list(rows)
    fields=fields or list(rows[0])
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k:'UNKNOWN' if v is None else round(v,4) if isinstance(v,float) else v for k,v in r.items()})

def read(p):
    p=Path(p)
    if p.is_relative_to(ROOT) and not p.is_relative_to(HERE):
        SOURCES[str(p.relative_to(ROOT))]={'kind':'completed_local','sha256':digest(p)}
    with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def capture(ref, path, alias):
    b=subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)
    p=HERE/'inputs'/alias
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(b)
    SOURCES[path+'@'+ref]={'kind':'git_blob','commit':ref,'path':path,
      'git_blob':subprocess.check_output(['git','rev-parse',ref+':'+path],cwd=ROOT,text=True).strip(),
      'snapshot':str(p.relative_to(HERE)),'sha256':hashlib.sha256(b).hexdigest()}
    return b.decode()

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def protection():
    expected=json.loads((STUDY/'protected_files.json').read_text())
    bad=[p for p,h in expected.items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
    return {'expected':len(expected),'checked':len(expected),'changed_or_missing':bad,'pass':not bad}

def initialize():
    global P34, RE, ANCHORS, UNIVERSE, POSITIVE, CLASSIFY
    assert protection()['pass'], 'Protected inputs already differ; stop'
    base='context/35_full_programme_execution_20261112/'
    selections={
      'P08/SVX/research_v1/HANDOFF.md':'svx_handoff.md',
      'P08/SVX/research_v1/evidence/SVX_primary_schedule_products.csv':'svx_primary.csv',
      'P08/SVX/research_v1/block_time_inputs.csv':'svx_blocks.csv',
      'P08/SVX/research_v1/dated_templates/historical_chain_legs.csv':'svx_chain_controls.csv',
      'P08/MOSCOW/research_v1/KEEP_evidence.csv':'moscow_keep.csv',
      'P08/MOSCOW/research_v1/airport_status.csv':'moscow_airports.csv',
      'P08/MOSCOW/research_v1/handoff.json':'moscow_handoff.json',
      'P09/handoff.json':'p09_handoff.json',
      'P09/international/programmes.json':'international_programmes.json',
      'P09/international/assumptions.json':'international_assumptions.json',
      'P02I/international_market_cards.csv':'international_market_cards.csv',
      'P15/integration_coverage.json':'p15_coverage.json',
      'P15/handoff.md':'p15_handoff.md'}
    for p,a in selections.items():capture(TEAM,base+p,a)
    for p,a in [('data/manual/rw_routes_now.csv','step1_rw_routes.csv'),('data/assumptions/network.csv','step1_network.csv')]:
        capture(STEP,p,a)
    # Only completed adapters are imported. Their __main__ / build functions never run.
    P34=load('p36_completed_p34',C34/'calculation/calculate.py');RE=P34.RE
    ANCHORS=read(HERE/'inputs/svx_primary.csv')
    UNIVERSE={r['pair_id']:r for r in read(C31/'route_economics/route_universe.csv')}
    POSITIVE=[]
    # Preserve positive old service facts, regardless of a later UNKNOWN in P36 research.
    for sub in ('source_recovery_competitors/schedules.csv',):
        p=C34/sub
        POSITIVE.extend(r for r in read(p) if r['status']=='PUBLISHED_PATTERN_ONLY')
    assert len(POSITIVE)==46
    table('inputs/p34_new_schedules_preserved.csv',read(C34/'source_recovery_new/schedules.csv'))
    CLASSIFY=read(C34/'source_recovery_new/classification.csv')
    for p in [C31/'route_economics/API_handoff.json',C31/'ops_inputs/directed_blocks.csv',
              C31/'ops_inputs/calendar_engine.py',C34/'calculation/calculate.py',
              C31/'route_economics/calculate.py',C31/'audit/common_contract.json',
              ROOT/'context/32_delay_cargo_research_20261112/calculation/control_flights.csv']:
        SOURCES[str(p.relative_to(ROOT))]={'kind':'completed_local','sha256':digest(p)}
    # Hash the immutable transitive input directories used by the imported P05/P06/P04 adapters.
    for d in (RE.P05DIR, RE.P06DIR, RE.P04DIR, RE.BASE):
        for p in sorted(d.rglob('*')):
            if p.is_file() and p.suffix in ('.py','.csv','.json') and '__pycache__' not in p.parts:
                SOURCES[str(p.relative_to(ROOT))]={'kind':'pinned_dependency','sha256':digest(p)}
    table('inputs/p34_positive_service_preserved.csv',POSITIVE,
      list(dict.fromkeys(k for r in POSITIVE for k in r)) if POSITIVE else ['status'])
    table('inputs/p34_novelty_classification_preserved.csv',CLASSIFY)

def city(a):return 'MOW' if a in ('ZIA','DME') else a
def pair(a,b):return '-'.join(sorted((city(a),city(b))))
def iso(n):return (EPOCH+timedelta(minutes=n)).isoformat()
def localmin(day,clock,airport):
    return ((EPOCH+timedelta(days=day)).replace(hour=clock//60,minute=clock%60,tzinfo=ZoneInfo(ZONES[airport])).astimezone(UTC)-EPOCH).total_seconds()/60

@lru_cache(None)
def edge(a,b):
    km,h=RE.geometry(a,b)
    minutes=P34.block(a,b)
    ferry=(set((a,b)) in ({'SVX','CEK'},{'SVX','PEE'},{'SVX','TJM'}))
    q,qc,src,via,_=RE.DEMAND.prior(a,b)
    if src=='BASE_GRAVITY_EXTRAPOLATION' and km<500:ferry=True
    return dict(origin=a,destination=b,city_od=city(a)+'>'+city(b),pair_id=pair(a,b),
      km=km,minutes=minutes,block_evidence=P34.block_source(a,b),
      kind='PAID_FERRY' if ferry else 'SERVICE',prior_source=src,
      market_quality='NO_SALES_UNSUPPORTED_SHORT_FEEDER' if ferry else 'SCENARIO_PRIOR_NOT_OBSERVED_OD',
      prior_in_1334=pair(a,b) in UNIVERSE,actual_slot=None,type='RRJ-95B_CONDITIONAL',
      prior_annual_both=q,actual_netfare=None,novelty='UNKNOWN_OR_EXISTING_NOT_ZERO_OWN_SALES')

def route_values(path):
    return [edge(a,b) for a,b in zip(path,path[1:])]

def oneleg_value(e,scenario,full=False):
    c=RE.costs(e['origin'],e['destination'],scenario,e['minutes']/60)
    fare=0 if e['kind']=='PAID_FERRY' else RE.fare(e['origin'],e['destination'],scenario)[1]
    return 100*fare-c['fixed_cost']

def build_paths():
    """Degree/beam bounds recorded, including every generated partial and closed path."""
    all_edges=[edge(a,b) for a in NODES for b in NODES if city(a)!=city(b)]
    edge_bounds=[]
    for e in all_edges:
        co=RE.costs(e['origin'],e['destination'],'cautious',e['minutes']/60)
        fare=0 if e['kind']=='PAID_FERRY' else RE.fare(e['origin'],e['destination'],'cautious')[1]
        edge_bounds.append(dict(origin=e['origin'],destination=e['destination'],kind=e['kind'],
          cautious_netfare=fare,cautious_avoidable_cost_transfer=co['fixed_cost'],
          cautious_full100_cap=100*fare-co['fixed_cost'],
          cautious_fuel_RUB_t=co['fuel_price'],fuel_break_even_full100_RUB_t=(100*fare-co['other_cost'])/co['fuel_t'],
          netfare_break_even_full100=co['fixed_cost']/100 if fare else None,
          interpretation='upper bound only; paid ferry0 revenue; omitted nonnegative station/overnight F excluded'))
    table('graph_edges.csv',all_edges)
    table('edge_structural_bounds.csv',edge_bounds)
    dump('structural_proof.json',dict(
      directed_edges=len(all_edges),maximum_cautious_full100_per_leg=max(r['cautious_full100_cap'] for r in edge_bounds),
      every_graph_edge_negative=all(r['cautious_full100_cap']<0 for r in edge_bounds),
      maximum_fuel_break_even_full100_RUB_t=max(r['fuel_break_even_full100_RUB_t'] for r in edge_bounds),
      conclusion='Every graph leg has negative cautious contribution even at100 paid seats under fixed P31 netfare/cost transfer. Any nonempty chain is a sum of such negatives before omitted F: wider path search cannot produce positive standalone new contribution at these inputs. This is a model-structural result, not observed economics or a restriction on real fares/costs.',
      thresholds='edge fuel/netfare thresholds and family structural_bounds.csv; actual demand at revised fares requires recoupled P05/P06;100 seats is capacity upper bound only'))
    adj={a:sorted([b for b in NODES if city(a)!=city(b) and edge(a,b)['minutes']<=330],
      key=lambda b:(-oneleg_value(edge(a,b),'base'),b))[:8] for a in NODES}
    proposed={};partial=[]
    def add(path,family,overnight=0):
        key=(tuple(path),overnight)
        if any(edge(a,b)['minutes']>330 for a,b in zip(path,path[1:])):return
        proposed[key]={'path':list(path),'family':family,'overnight_after':overnight,
          'optimistic_cap_cautious_per_rotation':sum(oneleg_value(e,'cautious') for e in route_values(path))}
    for base in ('SVX','ZIA','DME'):
        for b in NODES:
            if city(b)!=city(base):add([base,b,base],'RT')
        beam=[([base],0.)]
        for depth in range(1,6):
            nxt=[]
            for path,score in beam:
                for b in adj[path[-1]]:
                    if b in path or city(b)==city(base):continue
                    p=path+[b];s=score+oneleg_value(edge(path[-1],b),'base')
                    nxt.append((p,s))
                    if depth>=2:
                        add(p+[base],'TRIANGLE' if depth==2 else 'CYCLE'+str(depth+1))
            nxt.sort(key=lambda x:(-x[1],x[0]));selected=nxt[:24]
            partial.extend({'base':base,'depth':depth,'path':'-'.join(p),'optimistic_partial_base':s,
              'disposition':'EXPAND' if i<24 else 'BEAM_CAP24_NOT_EXPANDED'} for i,(p,s) in enumerate(nxt))
            beam=selected
        # Short cycles preserve operations diversity even if the revenue beam favours long sectors.
        regional=[x for x in ('UFA','KUF','REN','GOJ','OMS','TJM','TOF','CEK','PEE') if x!=base]
        for k in (3,4,5,6):
            for off in (0,2):
                mid=regional[off:off+k-1]
                p=[base]+mid+[base]
                add(p,'TRIANGLE' if k==3 else 'CYCLE'+str(k))
                add(list(reversed(p)),'TRIANGLE' if k==3 else 'CYCLE'+str(k))
        add([base,'KUF',base,'UFA',base],'CONCAT_RT')
        add([base,'OMS',base,'GOJ',base],'CONCAT_RT')
    # Category beam: all RTs; two orientation-pairs per cycle family/base (one short, one cap leader).
    chosen=set()
    for key,r in proposed.items():
        if r['family'] in ('RT','CONCAT_RT'):chosen.add(key)
    for base in ('SVX','ZIA','DME'):
        for family in ('TRIANGLE','CYCLE4','CYCLE5','CYCLE6'):
            rs=[(k,r) for k,r in proposed.items() if r['path'][0]==base and r['family']==family]
            if not rs:continue
            bycap=max(rs,key=lambda kr:(kr[1]['optimistic_cap_cautious_per_rotation'],kr[0]))
            short=min(rs,key=lambda kr:(sum(e['minutes'] for e in route_values(kr[1]['path'])),kr[0]))
            for k,r in (bycap,short):
                chosen.add(k)
                rev=(tuple(reversed(r['path'])),0)
                add(list(reversed(r['path'])),family)
                chosen.add(rev)
            # Real overnight away from base, after an intermediate leg. Not a reset at midnight.
            for k,r in (short,):
                after=max(1,(len(r['path'])-1)//2)
                add(r['path'],'MULTIDAY_'+family,after)
                chosen.add((tuple(r['path']),after))
    rows=[];paths={}
    for i,(key,r) in enumerate(sorted(proposed.items()),1):
        pid='P%04d'%i;r=dict(r,id=pid)
        chosenflag=key in chosen
        rows.append(dict(path_id=pid,path='-'.join(r['path']),family=r['family'],
          legs=len(r['path'])-1,overnight_after=r['overnight_after'],
          optimistic_cap_cautious_per_rotation=r['optimistic_cap_cautious_per_rotation'],
          disposition='PARAMETER_SEARCH' if chosenflag else 'CATEGORY_BEAM_NOT_TIME_EXPANDED'))
        if chosenflag:paths[pid]=r
    table('path_registry.csv',rows)
    table('path_expansion.csv',partial)
    return paths,adj,len(proposed),len(partial)

def make_job(id_,path,day,clock,tail,source,scope):
    start=localmin(day,clock,path[0]);flights=[];t=start
    for i,e in enumerate(route_values(path)):
        flights.append(dict(job_id=id_,flight_id=id_+'/L'+str(i+1),tail=tail,origin=e['origin'],destination=e['destination'],
          dep=t,arr=t+e['minutes'],block=e['minutes'],kind=e['kind'],evidence=e['block_evidence']))
        t+=e['minutes']+TURN
    return dict(id=id_,tail=tail,origin=path[0],destination=path[-1],start=start,end=t-TURN,
      flights=flights,source=source,scope=scope,actual_registration=None,actual_release=None)

def build_baselines():
    b1=[]
    for p in P34.keep_patterns():
        day=p['weekdays'][0]-1
        hh,mm=map(int,p['departure_local'].split(':'))
        b1.append(make_job(p['id'],p['path'],day,hh*60+mm,'T1',
           'P34.keep_patterns + P32 EQUAL_BUFFER_B30 UTC corrected','SCOPED_P34'))
    # Full seven-day scenario for a selected own programme, not the carrier's entire actual KEEP.
    # Exact source clocks, with explicit scenario recurrence and closed return analogue.
    wanted=[('GOJ','07:00','вс',(6,)),('GOJ','07:35','ср',(2,)),
      ('GOJ','08:40','пт',(4,)),('GOJ','08:35','пн',(0,)),
      ('OMS','21:20','вт, пт',(1,4)),('KUF','22:45','ежедневно',tuple(range(7))),
      ('UFA','22:30','вт, чт, пт, вс',(3,6))]
    b2=[];assignment=[]
    for dest,clock,ru,days in wanted:
        matches=[r for r in ANCHORS if r['carrier_source_label']=='RED WINGS' and r['destination']==dest
          and r['departure_local']==clock and r['weekdays_ru']==ru]
        assert matches,(dest,clock,ru)
        # Stable lexical choice among period alternatives; no assertion of 2027 applicability.
        r=sorted(matches,key=lambda x:x['record_id'])[0]
        for day in days:
            hh,mm=map(int,clock.split(':'))
            jid='OWN-'+r['flight']+'-ISO'+str(day+1)
            job=make_job(jid,['SVX',dest,'SVX'],day,hh*60+mm,'T1',r['record_id'],
              'FULL_WEEK_SELECTED_KEEP_SCENARIO_RECURRENCE_RETURN_TAIL_UNKNOWN')
            b2.append(job)
            assignment.append(dict(old_job_id=jid,source_record_id=r['record_id'],published_outbound_clock=clock,
              published_days=ru,scenario_iso_day=day+1,return_basis='P34/P31 directed block + turn60 SCENARIO',
              note='UFA Thu/Sun recurrence2 scenario, not cancellation of observed Tue/Fri; scope is selected programme'))
    # Deterministic interval colouring, 2 compatible existing SVX working tails. No donor margin selection.
    ready={'T1':-1e9,'T2':-1e9}
    for job in sorted(b2,key=lambda j:(j['start'],j['id'])):
        available=[t for t in ready if ready[t]<=job['start']]
        assert available,'Constructed selected KEEP needs >2 tails'
        tail=available[0];ready[tail]=job['end']+TURN;job['tail']=tail
        for f in job['flights']:f['tail']=tail
    setups={
      'B1S':dict(baseline='SCOPED_P34',jobs=b1,positions={'T1':'SVX'},target='T1',cohort='E1',unknown='BLOCKED'),
      'B1I':dict(baseline='SCOPED_P34',jobs=b1,positions={'T1':'SVX'},target='T1',cohort='E1',unknown='IDLE_SCENARIO'),
      'B2S':dict(baseline='FULL_WEEK_SCENARIO',jobs=b2,positions={'T1':'SVX','T2':'SVX'},target='T1',cohort='E2_SVX',unknown='IDLE_SCENARIO'),
      'B2T':dict(baseline='FULL_WEEK_SCENARIO',jobs=b2,positions={'T1':'SVX','T2':'SVX'},target='T2',cohort='E2_SVX',unknown='IDLE_SCENARIO')}
    for base in ('DME','ZIA'):
        for gate in ('BLOCKED','IDLE_SCENARIO'):
            code='M'+base+('S' if gate=='BLOCKED' else 'I')
            setups[code]=dict(baseline='SCOPED_P34_MOSCOW_EXTERNAL_D',jobs=b1,
              positions={'T1':'SVX','T2':base},target='T2',cohort='E2_SVX_PLUS_CONDITIONAL_MOSCOW_RRJ',unknown=gate)
    rows=[]
    for name,jobs in (('SCOPED_P34',b1),('FULL_WEEK_SCENARIO',b2)):
        for week in range(4):
            for j in jobs:
                for f in j['flights']:
                    dep=f['dep']+week*WEEK;arr=f['arr']+week*WEEK
                    rows.append(dict(baseline=name,old_job_id=j['id'],flight_id=f['flight_id']+'/W'+str(week+1),
                      tail=f['tail'],origin=f['origin'],destination=f['destination'],departure_utc=iso(dep),arrival_utc=iso(arr),
                      departure_local=(EPOCH+timedelta(minutes=dep)).astimezone(ZoneInfo(ZONES[f['origin']])).isoformat(),
                      arrival_local=(EPOCH+timedelta(minutes=arr)).astimezone(ZoneInfo(ZONES[f['destination']])).isoformat(),
                      block_minutes=f['block'],source=j['source'],status=j['scope'],actual_registration=None,
                      actual_release=None,actual_old_revenue=None,actual_avoidable_cost=None))
    table('baseline_schedule.csv',rows)
    table('inputs/baseline_anchor_mapping.csv',assignment)
    return setups

def new_jobs(p,days,hour,target):
    jobs=[]
    for day in days:
        jid='NEW-ISO'+str(day+1)
        j=make_job(jid,p['path'],day,hour*60,target,'P36 path graph; all clocks SCENARIO','NEW_CHAIN')
        after=p['overnight_after']
        if after:
            # An explicit paid overnight of at least 8h to the next local 06:00.
            last=j['flights'][after-1]
            airport=last['destination'];arr=EPOCH+timedelta(minutes=last['arr'])
            local=arr.astimezone(ZoneInfo(ZONES[airport]));morning=local.replace(hour=6,minute=0)
            while morning.astimezone(UTC)<arr+timedelta(hours=8):morning+=timedelta(days=1)
            ready=(morning.astimezone(UTC)-EPOCH).total_seconds()/60
            shift=ready-j['flights'][after]['dep']
            assert shift>=0
            for f in j['flights'][after:]:f['dep']+=shift;f['arr']+=shift
            j['end']+=shift;j['overnight_minutes']=ready-last['arr']
        jobs.append(j)
    return jobs

def overlap(a,b):return a['start']<b['end']+TURN and b['start']<a['end']+TURN

def conflicts(old,new,target):
    out=[]
    for j in old:
        if j['tail']!=target:continue
        if any(overlap(dict(j,start=j['start']+s,end=j['end']+s),n) for n in new for s in (-WEEK,0,WEEK)):
            out.append(j['id'])
    return sorted(out)

def changed_jobs(old,remove=(),move=None,swap=None):
    out=[]
    for j in old:
        if j['id'] in remove:continue
        q=dict(j);q['flights']=[dict(f) for f in j['flights']]
        shift=move[1] if move and move[0]==j['id'] else 0
        if shift:
            q['start']+=shift;q['end']+=shift
            for f in q['flights']:f['dep']+=shift;f['arr']+=shift
        if swap and j['id'] in swap:
            q['tail']='T2' if j['tail']=='T1' else 'T1'
            for f in q['flights']:f['tail']=q['tail']
        out.append(q)
    return out

def physics(jobs,positions,entry_check=True):
    """Circular-week UTC continuity/turn/position and Feb completion. 8BH separate."""
    errors=set();daily=Counter();events=defaultdict(list)
    for j in jobs:
        if j['tail']=='R1':errors.add('RESERVE_USED')
        if positions.get(j['tail'])!=j['origin']:errors.add('POSITION_REQUIRES_PAID_FERRY')
        for sh in (-WEEK,0,WEEK):
            events[j['tail']].append((j['start']+sh,j['end']+sh,j['origin'],j['destination'],j['id']))
        for week in range(4):
            for f in j['flights']:
                dep=f['dep']+week*WEEK;arr=f['arr']+week*WEEK
                if entry_check and (dep<0 or arr>28*1440):errors.add('ENTRY_OR_MONTH_END_COMPLETION')
                cursor=dep
                while cursor<arr:
                    day=math.floor(cursor/1440);end=min(arr,(day+1)*1440)
                    daily[(j['tail'],day)]+=end-cursor;cursor=end
    for tail,seq in events.items():
        seq.sort();pos=positions[tail];last=None
        for start,end,a,b,id_ in seq:
            if last is not None and start<last+TURN:errors.add('OVERLAP_OR_TURN')
            if pos!=a:errors.add('POSITION_REQUIRES_PAID_FERRY')
            last=end;pos=b
    return sorted(errors),max(daily.values(),default=0)/60

def action_apply(action,setup,new):
    old=setup['jobs'];target=setup['target'];cs=conflicts(old,new,target)
    remove=[];move=None;swap=None;err=None
    if action.startswith('MOVE'):
        if not cs:err='NO_CONFLICT_TO_MOVE'
        else:move=(cs[0],int(action[4:]))
    elif action.startswith('REMOVE'):
        n=int(action[6:])
        if len(cs)<n:err='INSUFFICIENT_CONFLICTS_NO_EXTRA_DONOR'
        else:remove=cs[:n]
    elif action in ('MIN_CLOSURE','ALL_AFFECTED'):
        if not cs:err='NO_CONFLICT_TO_REMOVE'
        else:remove=cs
    elif action=='SWAP':
        if len(setup['positions'])<2:err='NO_SECOND_WORKING_TAIL'
        elif len(set(setup['positions'].values()))>1:err='NO_RENDEZVOUS_PAID_FERRY_QUEUE'
        elif len(cs)!=1:err='SWAP_ONE_PAIR_CAP_OR_NO_TARGET'
        else:
            others=[j for j in old if j['tail']!=target]
            for j in sorted(others,key=lambda j:j['id']):
                test=changed_jobs(old,swap=(cs[0],j['id']))
                e,_=physics(test+new,setup['positions'])
                if not e:swap=(cs[0],j['id']);break
            if not swap:err='NO_PHYSICALLY_COMPATIBLE_SWAP'
    modified=changed_jobs(old,remove,move,swap)
    return modified,dict(remove=remove,move=move,swap=swap,conflicts=cs,error=err)

def unknown_gate(setup,new,act):
    if setup['unknown']=='IDLE_SCENARIO':return None
    windows=[j for j in setup['jobs'] if j['id'] in act['remove'] and j['tail']==setup['target']]
    # Release windows are only the original, explicit removed-job occupancy.
    for n in new:
        if not any(w['start']<=n['start'] and w['end']>=n['end'] for w in windows):
            return 'UNKNOWN_OCCUPANCY_BLOCKED'
    return None

def flatten(jobs):
    for week in range(4):
        for j in jobs:
            for f in j['flights']:
                yield dict(f,dep=f['dep']+week*WEEK,arr=f['arr']+week*WEEK,flight_id=f['flight_id']+'/W'+str(week+1))

def allocate_market(potential,groups):
    """Finite city/month pool, exact capped aggregate MNL with fixed outside weight 1."""
    result={};active=dict(groups);remaining=potential;outside=1.
    while active:
        denom=outside+sum(v['weight'] for v in active.values())
        quantities={k:remaining*v['weight']/denom for k,v in active.items()}
        capped=[k for k,v in active.items() if quantities[k]>v['capacity']]
        if not capped:
            result.update(quantities);break
        for k in capped:
            result[k]=active[k]['capacity'];remaining-=result[k];del active[k]
    return result

def screen_jobs(jobs,scenario):
    """Small analytic direct-market screen only; P06 full dated products reserved for pass2."""
    groups=defaultdict(list);cost=0.;fuel=0.;other=0.;fullrev=0.;netseats=0
    for f in flatten(jobs):
        e=edge(f['origin'],f['destination'])
        c=RE.costs(f['origin'],f['destination'],scenario,f['block']/60)
        cost+=c['fixed_cost'];fuel+=c['fuel_t'];other+=c['other_cost']
        if f['kind']=='PAID_FERRY':continue
        net=RE.fare(f['origin'],f['destination'],scenario)[1]
        fullrev+=100*net;netseats+=100
        groups[(city(f['origin']),city(f['destination']))].append(f)
    revenue=0.;pax=0.;poolledger=[]
    for (a,b),fs in groups.items():
        q,src,via=RE.annual(a,b,scenario,2027)
        pot=q*.5*RE.P05.monthly_profile(2027)[2]/.6
        byphysical=defaultdict(list)
        for f in fs:byphysical[(f['origin'],f['destination'])].append(f)
        alternatives={}
        for (pa,pb),seq in byphysical.items():
            freq=len(seq)/4
            duration=sum(f['block'] for f in seq)/len(seq)
            net=RE.fare(pa,pb,scenario)[1]
            alternatives[(pa,pb)]=dict(weight=RE.mass(pa,pb,freq,scenario,duration=duration),capacity=len(seq)*100,net=net)
        alloc=allocate_market(pot,alternatives)
        assert sum(alloc.values())<=pot+1e-7
        for k,n in alloc.items():revenue+=n*alternatives[k]['net'];pax+=n
        poolledger.append(dict(city_od=a+'>'+b,potential=pot,allocated=sum(alloc.values()),source=src))
    return dict(revenue=revenue,cost=cost,subtotal=revenue-cost,pax=pax,full100_cap=fullrev-cost,
      fuel_t=fuel,other_cost=other,full100_revenue=fullrev,
      fuel_price_break_even_full100=(fullrev-other)/fuel if fuel else None,
      netfare_break_even_full100=cost/netseats if netseats else None,
      pools=poolledger,actual_full_profit=None)

def econ_paths(paths):
    econ={};rows=[]
    for pid,p in paths.items():
        for freq in FREQUENCIES:
            nj=new_jobs(p,DAY_OFFSETS[freq],6,'T1')
            vals={s:screen_jobs(nj,s) for s in ('base','cautious')}
            id_=pid+'F'+str(freq);econ[id_]=vals
            for s,v in vals.items():
                rows.append(dict(economic_id=id_,path_id=pid,frequency_per_week=freq,departures_per_leg_month=4*freq,
                  scenario=s,**{k:v[k] for k in v if k!='pools'},
                  scope='STANDALONE_NEW_ONLY_NOT_DELTA_KEEP; timing no measured utility; station_F/donor/ownshift UNKNOWN',
                  actual_demand=None,cargo=0,support=0))
    table('economics_screen.csv',rows)
    cautious=[r for r in rows if r['scenario']=='cautious']
    summary=[]
    for family in sorted({p['family'] for p in paths.values()}):
        rs=[r for r in cautious if paths[r['path_id']]['family']==family]
        summary.append(dict(family=family,screen_cases=len(rs),full100_positive_cases=sum(r['full100_cap']>0 for r in rs),
          maximum_full100_cap=max(r['full100_cap'] for r in rs),
          maximum_landed_fuel_break_even_RUB_t=max(r['fuel_price_break_even_full100'] for r in rs),
          cautious_fuel_RUB_t=161696,
          minimum_weighted_netfare_multiplier_to_full100_BE=min(r['cost']/r['full100_revenue'] for r in rs if r['full100_revenue']>0),
          interpretation='optimistic100seat bound before nonnegative omitted F; not observed demand; raising fare changes demand'))
    table('structural_bounds.csv',summary)
    return econ

def materialized_rows(cid,state,jobs):
    out=[]
    for f in flatten(jobs):
        dep=EPOCH+timedelta(minutes=f['dep']);arr=EPOCH+timedelta(minutes=f['arr'])
        e=edge(f['origin'],f['destination'])
        out.append(dict(candidate_id=cid,state=state,old_or_new_job_id=f['job_id'],flight_id=f['flight_id'],tail=f['tail'],
          origin=f['origin'],destination=f['destination'],city_od=e['city_od'],departure_utc=dep.isoformat(),arrival_utc=arr.isoformat(),
          departure_local=dep.astimezone(ZoneInfo(ZONES[f['origin']])).isoformat(),arrival_local=arr.astimezone(ZoneInfo(ZONES[f['destination']])).isoformat(),
          block_minutes=f['block'],kind=f['kind'],saleable_seats=0 if f['kind']=='PAID_FERRY' else 100,
          market_source=e['prior_source'],market_quality=e['market_quality'],block_source=f['evidence'],
          actual_registration=None,slot=None,crew_FDP_rest=None,MRO=None,type_release=None))
    return out

def run_search(paths,setups,econ):
    configs=[];shortpool=[];reasons=Counter();coverage=Counter();count=0
    fields=['id','config','setup','action','score','bhmax','removed','result']
    action_ids={a:'A%02d'%i for i,a in enumerate(ACTIONS)}
    result_ids={};result_rows=[]
    with (HERE/'candidate_chains.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader()
        for pid,p in sorted(paths.items()):
            base=p['path'][0]
            for freq in FREQUENCIES:
                seen=set()
                for seed in range(7):
                    days=tuple(sorted((seed+x)%7 for x in DAY_OFFSETS[freq]))
                    if days in seen:continue
                    seen.add(days)
                    for hour in WINDOWS:
                        cfg='G%05d'%(len(configs)+1)
                        configs.append(dict(config_id=cfg,path_id=pid,iso_weekdays=';'.join(str(d+1) for d in days),
                          p31_weekdays_0_to_6=';'.join(map(str,days)),frequency_per_week=freq,departure_local='%02d:00'%hour,
                          source='SCENARIO_NO_DAY_TIME_WTP',monthly_repeat_weeks=4))
                        cases=('B1S','B1I','B2S','B2T') if base=='SVX' else ('M'+base+'S','M'+base+'I')
                        for name in cases:
                            setup=setups[name];new=new_jobs(p,days,hour,setup['target'])
                            for action in ACTIONS:
                                count+=1;cid='C%07d'%count
                                modified,act=action_apply(action,setup,new)
                                if act['error']:
                                    hard=[];bh=0.;gate=act['error'];disposition='ACTION_UNAVAILABLE'
                                else:
                                    hard,bh=physics(modified+new,setup['positions'])
                                    gate=unknown_gate(setup,new,act)
                                    disposition='HARD_REJECT' if hard else 'OCCUPANCY_BLOCKED' if gate else 'RESOURCE_8BH_QUEUE' if bh>8+1e-9 else 'CONDITIONAL_SCREEN'
                                ev=econ[pid+'F'+str(freq)];sb=ev['base']['subtotal'];sc=ev['cautious']['subtotal']
                                reason=gate if disposition in ('ACTION_UNAVAILABLE','OCCUPANCY_BLOCKED') else '+'.join(hard) if hard else disposition
                                reasons[(name,action,reason)]+=1
                                for dim,val in [('airport',base),('family',p['family']),('frequency',freq),('window',hour),('action',action),('setup',name)]:
                                    coverage[(dim,str(val),disposition)]+=1
                                resultkey=(disposition,tuple(hard),gate or '')
                                if resultkey not in result_ids:
                                    rid='R%03d'%len(result_ids);result_ids[resultkey]=rid
                                    result_rows.append(dict(result_id=rid,disposition=disposition,hard=';'.join(hard),gate=gate or ''))
                                w.writerow(dict(id=cid,config=cfg,setup=name,action=action_ids[action],score=pid+'F'+str(freq),
                                  bhmax=round(bh,3),removed=len(act['remove']),result=result_ids[resultkey]))
                                if disposition in ('CONDITIONAL_SCREEN','RESOURCE_8BH_QUEUE'):
                                    shortpool.append(dict(id=cid,config=cfg,setup=name,action=action,path_id=pid,
                                      family=p['family'],base=base,freq=freq,days=days,hour=hour,
                                      economic_id=pid+'F'+str(freq),score_base=sb,score_caut=sc,bh=bh,
                                      act=act,disposition=disposition))
            print('path',pid,p['family'],base,'attempts',count,flush=True)
    table('schedule_configs.csv',configs)
    table('disposition_ids.csv',result_rows)
    table('action_ids.csv',[dict(action_id=id_,action=a) for a,id_ in action_ids.items()])
    table('rejection_counts.csv',[dict(setup=n,action=a,reason=r,count=c) for (n,a,r),c in sorted(reasons.items())])
    table('coverage.csv',[dict(dimension=d,value=v,disposition=s,count=c) for (d,v,s),c in sorted(coverage.items())])
    return shortlist(shortpool,paths,setups,econ),count,len(configs),coverage

def shortlist(pool,paths,setups,econ):
    # Diverse conditional screens; only nonnegative resource/finance assertion is not used.
    # Select on new contribution, never on removing a model-negative donor.
    rank=lambda r:(r['disposition']=='CONDITIONAL_SCREEN',r['score_caut'],r['score_base'],-r['bh'],r['id'])
    pool.sort(key=rank,reverse=True)
    selected=[];seen=set();category_rows=[]
    def take(category,predicate,n=1):
        candidates=[r for r in pool if predicate(r)]
        added=0
        for r in candidates:
            signature=(r['path_id'],r['setup'],r['action'],r['freq'],r['hour'])
            if signature in seen:continue
            seen.add(signature);selected.append(dict(r,selection_category=category));added+=1
            if added==n:break
        category_rows.append(dict(category=category,available=len(candidates),selected=added,
          disposition='REPRESENTATIVE_NOT_WINNER' if added else 'NO_PHYSICAL_RESOURCE_SCREEN_PASS; see rejection_counts'))
    for base in ('SVX','ZIA','DME'):
        for family in ('RT','TRIANGLE','CYCLE4','CYCLE5','CYCLE6','CONCAT_RT'):
            take(base+'/'+family,lambda r,b=base,f=family:r['base']==b and r['family']==f)
        take(base+'/MULTIDAY',lambda r,b=base:r['base']==b and r['family'].startswith('MULTIDAY'))
    for name,pred in [
      ('zero_removal',lambda r:len(r['act']['remove'])==0 and r['action']=='INSERT'),
      ('remove1',lambda r:len(r['act']['remove'])==1),
      ('remove2',lambda r:len(r['act']['remove'])==2),
      ('remove3plus',lambda r:len(r['act']['remove'])>=3),
      ('swap',lambda r:r['act']['swap'] is not None),
      ('move',lambda r:r['act']['move'] is not None),
      ('strict_known_window',lambda r:r['setup']=='B1S')]:take(name,pred,2)
    for freq in FREQUENCIES:take('frequency'+str(freq),lambda r,f=freq:r['freq']==f)
    # Bound the full schedules; preserve early category representatives and fill up to36.
    selected=selected[:36]
    if len(selected)<30:take('overall_screen',lambda r:True,30-len(selected))
    selected=selected[:36]
    table('shortlist_category_coverage.csv',category_rows)
    result=[];actions=[];schedules=[];states=[];poolrows=[];details={};overnights=[]
    for i,r in enumerate(selected,1):
        p=paths[r['path_id']];setup=setups[r['setup']]
        new=new_jobs(p,r['days'],r['hour'],setup['target'])
        modified,act=action_apply(r['action'],setup,new)
        errors,bh=physics(modified+new,setup['positions']);assert not errors
        cid=r['id']
        details[cid]={'candidate':r,'setup_id':r['setup'],'new_jobs':new,'changed_old_jobs':modified}
        standalone=econ[r['economic_id']]['cautious']
        result.append(dict(candidate_id=cid,category=r['selection_category'],setup=r['setup'],cohort=setup['cohort'],
          path_id=r['path_id'],path='-'.join(p['path']),family=p['family'],iso_weekdays=';'.join(str(d+1) for d in r['days']),
          frequency_per_week=r['freq'],local_start='%02d:00'%r['hour'],action=r['action'],
          removed_jobs=';'.join(act['remove']),moved_job=act['move'][0] if act['move'] else '',
          swap_jobs=';'.join(act['swap'] or []),new_standalone_base=r['score_base'],new_standalone_cautious=r['score_caut'],
          cautious_full100_cap=standalone['full100_cap'],max_daily_BH=bh,physical_status='UTC_CONSISTENT_SCENARIO',
          resource_status='8BH_DIAGNOSTIC_FAIL_NOT_FDP' if bh>8 else '8BH_DIAGNOSTIC_PASS_NOT_FDP',
          source_gate='SCENARIO_NOT_LAUNCH; slot/crew/MRO/AFM/release UNKNOWN',
          donor_D=None,unobserved_loss=None,move_or_swap_sales_loss=None,station_F=None,full_delta=None,cash=None,
          threshold_rule='D+unobserved_loss+retiming_loss+F+ownshift+overnight_delta < replace_minus_without_new_screen',
          status='VALIDATION_CANDIDATE' if r['score_caut']>0 else 'NEGATIVE_STANDALONE_COMPARATOR_NOT_LAUNCH'))
        for j in setup['jobs']:
            op='remove' if j['id'] in act['remove'] else 'move' if act['move'] and j['id']==act['move'][0] else 'swap' if act['swap'] and j['id'] in act['swap'] else 'keep'
            actions.append(dict(candidate_id=cid,old_job_id=j['id'],old_flight_ids=';'.join(f['flight_id'] for f in j['flights']),
              action=op,from_tail=j['tail'],to_tail=next((x['tail'] for x in modified if x['id']==j['id']),''),
              delta_minutes=act['move'][1] if op=='move' else 0,old_revenue=None,old_avoidable_cost=None,
              actual_loss=None,loss_rule='UNKNOWN; do not set 0 or pay a donor twice',source=j['source']))
        for state,js in [('KEEP',setup['jobs']),('WITHOUT_NEW',modified),('REPLACE',modified+new)]:
            schedules+=materialized_rows(cid,state,js)
        for s in ('base','cautious'):
            vals={state:screen_jobs(js,s) for state,js in [('KEEP',setup['jobs']),('WITHOUT_NEW',modified),('REPLACE',modified+new)]}
            for state,v in vals.items():
                states.append(dict(candidate_id=cid,scenario=s,state=state,scoped_prior_net_revenue=v['revenue'],
                  scoped_avoidable_cost_transfer=v['cost'],scoped_known_subtotal=v['subtotal'],
                  delta_vs_keep_screen=v['subtotal']-vals['KEEP']['subtotal'],
                  replace_vs_without_new_screen=vals['REPLACE']['subtotal']-vals['WITHOUT_NEW']['subtotal'],
                  cancellation_cost=None,cancellation_treatment='same C in WITHOUT_NEW/REPLACE; cancels in comparison',
                  actual_moscow_international_D=None,actual_retiming_loss=None,actual_unobserved_occupancy=None,
                  overnight_parking_setup_reserve_F=None,actual_full_delta=None,cash=None,
                  interpretation='ANALYTIC_DIRECT_POOL_SCREEN_NOT_P06_FINAL; all three same fleet/date/scenario; time elasticity UNKNOWN'))
                poolrows.extend(dict(candidate_id=cid,scenario=s,state=state,**pr) for pr in v['pools'])
        for week in range(4):
            for j in new:
                for a,b in zip(j['flights'],j['flights'][1:]):
                    if b['dep']-a['arr']>TURN:
                        overnights.append(dict(candidate_id=cid,job_id=j['id'],week=week+1,airport=a['destination'],
                          start_utc=iso(a['arr']+week*WEEK),end_utc=iso(b['dep']+week*WEEK),
                          minutes=b['dep']-a['arr'],cost=None,cost_gate='PAID_STATION_OVERNIGHT_PARKING_CREW_UNKNOWN_NOT_FREE'))
    table('shortlist.csv',result)
    table('action_map.csv',actions)
    table('shortlist_full_schedules.csv',schedules)
    table('three_state_screen.csv',states)
    table('three_state_pool_checks.csv',poolrows)
    table('overnights.csv',overnights,['candidate_id','job_id','week','airport','start_utc','end_utc','minutes','cost','cost_gate'])
    dump('shortlist_requests.json',details)
    return result

def documents(paths,setups,adj,proposals,partials,attempts,configs,short):
    definitions={name:{k:v for k,v in s.items() if k!='jobs'}|{'old_job_ids':[j['id'] for j in s['jobs']]} for name,s in setups.items()}
    dump('baseline_definitions.json',dict(
      baselines=definitions,actual_registration=None,actual_release=None,
      scope='B1 P34 six closed weekly jobs + corrected fixed FOLLOW, other hours UNKNOWN. B2 selected full seven-day own programme SCENARIO, not whole company observed KEEP.',
      b2='GOJ4, KUF7, OMS2, UFA2 RT/week from fresh own anchors; UFA Thu/Sun2 explicit selected-programme recurrence, exact future/other sales UNKNOWN. Return timing and two-tail assignments SCENARIO.',
      reserve={'id':'R1','working':False,'location':None,'actual_release':None},
      e1_b2_gate='E1 cannot claim two-tail constructed KEEP: >1 working required; B2 searched only E2_SVX.',
      moscow='E2 conditional RRJ at physical ZIA or DME with external D UNKNOWN; no observed free tail. International KEEP net revenue unknown; never domestic-formula foreign job or D=0.',
      positions='T1 SVX initial conditional. T2 SVX or scenario Moscow RRJ. No other airport initial base; every chain closes or paid positioning needed.',
      b777_tu='DME CXR B777/Tu not SSJ resource; ZIA old hangar not available capacity',
      without_new='exact same remove/move/swap as REPLACE, without new jobs; C cancellation common',
      unknown='B1S/MDMES/MZIAS block outside known removed-job windows; B1I/B2S/B2T/M*I use separate IDLE_SCENARIO opportunity loss UNKNOWN. Known-subtotal zero outside scope is never whole-company KEEP0.'))
    dump('search_space.json',dict(
      airports=list(NODES),gated_queue=['VVO','KHV'],extra_airports_added=[],max_leg_minutes=330,
      allowed_directed_graph=adj,graph_rule='all distinct physical/city nodes, degree8 ranked optimistic base cap for expansion; all base RTs checked independently of degree; no DME-ZIA own-city service',
      starts=['SVX','ZIA','DME'],max_legs=6,cycle_rule='simple physical cycles3..6; both orientations retained for category beams; CONCAT_RT explicitly repeated base; no a->a leg',
      path_proposals=proposals,partial_expansions=partials,partial_beam_cap_per_base_depth=24,
      category_beam='all admissible RT and2 concat RT/base; cap leader+shortest, each reverse for triangle/4/5/6; shortest cycle/base/family also overnight variant',
      searched_paths=len(paths),searched_configs=configs,candidate_action_attempts=attempts,
      weekdays_iso=list(range(1,8)),p31_weekday_mapping='ISO minus1, 0..6 only at RE calendar boundary',
      start_hours_local=list(WINDOWS),time_status='SCENARIO; no measured WTP/slot and no time revenue premium',
      frequencies=list(FREQUENCIES),frequency_day_offsets={str(k):v for k,v in DAY_OFFSETS.items()},
      start_day_seeds=7,duplicates='identical weekday sets deduplicated, especially freq7 seven seeds -> one; no missing weekday',
      actions=list(ACTIONS),actions_apply_to='every unique config and applicable setup; unavailable/blocked recorded, no finance pruning of physical checks',
      removal_rule='remove only conflicts; no extra negative donor manufactured; min closure equals ALL_AFFECTED for independent closed old jobs; not arbitrary powerset',
      move_rule='one lexically first conflicting weekly job, offsets +/-30/60/120/180; all4 dated occurrences; other subsets NOT_SEARCHED',
      swap_rule='one conflicting whole job + one compatible whole job other tail, all4 occurrences; same SVX rendezvous; first physical pair; other swaps/ferry-assisted crossbase queue',
      period=['2027-02-01','2027-02-28'],repeat_weeks=4,month_end='all legs constructed; any completion outside Feb UTC availability rejected, never truncated',
      overnight='after middle leg to next local06 with >=8h ground; paid cost UNKNOWN; not crew-rest approval',
      score='standalone P05 monthly pool+P04 avoidable transfer for each path/freq, common base/cautious fleet/dates; thin rows reference economic_id; analytic3way shortlist only',
      pruning='finite node/block/degree/beam bounds only, finance cap diagnoses and ranks but does not assert global optimality',
      unsearched=['all simple paths outside degree8/beam24/category beam','arbitrary day subsets not the five rotating patterns','mixed paths and different clocks within a weekly candidate','new jobs split over working tails','multi-job retiming combinatorics','ferry-assisted crossbase swaps','other initial bases','stress turn90/holds/final crew/AFM gates','joint P06 final market choice with completed P36 research','other months and deliveries operational integration'],
      global_optimum=False))
    dump('contracts.json',dict(
      version='P36-PASS1-WEEKLY-1',write_scope=str(HERE.relative_to(ROOT)),
      states=['KEEP','WITHOUT_NEW','REPLACE'],score_primary='REPLACE minus SAME WITHOUT_NEW; compare all alternatives, not cancellation gain attributed to new chain',
      three_state_model='analytic capped direct-market MNL on common P05 monthly directed city pools, fixed outside mass1; exact group capacity caps, not full P06 dated-seat/through allocation',
      city_od='DME/ZIA MOW joint, physical tails/UTC airports separate',
      demand='prior/.6*0.5*P05 Feb profile; full28days; freq=dated departures/4; repeated old/new products share city pool; not one monthly OD per job/window',
      supply='100 seats scenario; unsupported short feeders paid ferry0 sales. No support/cargo in main.',
      facts_unknown=['observed endpoint OD','actual net fares','slots','tail registration/release','crew FDP/rest','AFM/variant route limits','MRO','international Moscow D','retiming demand loss','own through/interline demand','station/overnight/parking/setup/reserve costs','full profit','cash'],
      currency='constant2026RUB scenario transfer P31/P34, not future vendor contract',
      cancellations='same actual cancellation C both WITHOUT_NEW and REPLACE; unknown C vs KEEP, not automatically avoided fixed salary/lease',
      incremental_rule='numeric subtotal is scoped screen. Full delta = subtotal minus unobserved opportunity D minus retime/swap demand loss minus omitted F and differential overnight/parking; UNKNOWNs do not become0',
      retimed_utility='P05 has no measured slot elasticity: do not award premium or assert actual loss0',
      production='8BH/day UTC split preserved as diagnostic separate from hard position/overlap/turn/entry; not FDP',
      resource_cases={
        'S0':{'new_SJ':0},
        'S1':{'illustrative_entry':['2027-08-01','2027-11-01'],'entry_is_delivery':False},
        'S1D6':{'illustrative_entry':['2028-02-01','2028-05-01'],'entry_is_delivery':False}},
      sj='resource-only pass2 queue; not before H22027 and stated entry; no RRJ=PD8 operating equality',
      market_gate='P36 research not read. User completed gates: recovery actual path P36/market_recovery COMPLETE verify PASS, all46 old P34 positives retained, numeric updates0. BUS=Batumi, official ZIA08:10 Tue/Fri/Sun mixed Tu/SSJ exact tail UNKNOWN. WZ901 secondary historical only, Moscow donor unresolved. Ops completed numeric updates0, no free tail/cheap overnight. Admission files reserved pass2.',
      AI_use='implementation and scenario search by Codex; no external new search or invented observation; not independent research acceptance'))
    table('resource_cases.csv',[
      dict(case=c,month=m,RRJ_working_scenario=n,protected_reserve=1,new_SJ_resource_only=sj,
        actual_entry=None,PD8_equivalence='NOT_ASSUMED',status='PASS2_RESOURCE_ONLY')
      for c,entries in [('S0',()),('S1',('2027-08','2027-11')),('S1D6',('2028-02','2028-05'))]
      for m in ['2027-02','2027-08','2027-11','2028-02','2028-05'] for n in (1,2)
      for sj in [sum(d<=m for d in entries)]])
    # Small local delta, keeping truth and completion labels separate.
    fresh_rw=read(HERE/'inputs/step1_rw_routes.csv')
    old_rw=read(RE.BASE/'data/manual/rw_routes_now.csv')
    same=fresh_rw==old_rw
    (HERE/'source_delta.md').write_text(f'''# Свежая дельта и допуск pass1

Team `{TEAM}`, шаг1 `{STEP}`. Минимальные P36 snapshots сверены с manifest; дополнительные точечные blobs лежат в inputs/ и source_manifest.json. Старые builders/verify не запускались. Local bb6e933 и published3010698 имеют одинаковое дерево; история не исправлялась.

P08/SVX/research_v1/HANDOFF.md: Stage A, U1/U12/U123/U1234 и RET; Stage B NOT_RUN, свободный парк UNKNOWN. Опубликованные own anchors GOJ/OMS/KUF/UFA реально найдены в `SVX_primary_schedule_products.csv`; recurrence, замкнутые возвраты и назначение хвостов в B2 — SCENARIO. UFA2 — параметр выбранного полного недельного сценария, не утверждение отмены реальных рейсов.

P08/MOSCOW/research_v1: KEEP_evidence и airport_status сохраняют ZIA BUS/TBS mixed-type и Tu TLV, DME CXR widebody, KGD historical. Ничто из этого не создаёт свободный RRJ; D international UNKNOWN. Исторический ангар ZIA не free capacity. Есть физические ZIA и DME, один MOW OD.

Название P08I проверено по реальным именам дерева: самостоятельного корня с таким именем нет, сам P08 существует (SVX и MOSCOW); international составляющая реально находится в P02I и P09/international. Прочитаны international_market_cards.csv, programmes.json и assumptions.json: не присваиваем международным заданиям domestic RUB formula.

P09/handoff.json: 178 конструкций/1958 evaluations, demand SCENARIO_NOT_IDENTIFIED, acceptance false; E1 существующего SSJ — отдельный несопоставимый subgroup. P15/integration_coverage.json и handoff.md связывают условные результаты/панель, не дают market/ops/финансовую истинность. P15 не изменялся.

Fresh шаг1 rw_routes_now совпадает по прочитанным CSV rows с P31 frozen input: **{same}**. Fresh network сохранён как provenance, его legacy настройки не заменяют P31/P34 P04/P05 и запрет PD8=RRJ. Основной численный prior — уже готовые1334пары/P31, не Wikipedia.

Все46старых P34 PUBLISHED_PATTERN_ONLY rows сохранены в inputs/p34_positive_service_preserved.csv с исходными датами/source IDs; положительный факт не обнуляется последующим UNKNOWN. Новые research-пакеты не читались. User completed-input gate: recovery COMPLETE/verify PASS по реальному пути P36/market_recovery/, numeric OD/netyield/resource updates0. WZ901 Sep24 ZIA–KGD secondary historical only, QUARANTINED для текущего RRJ/донора; P36-WEB1 на UNKNOWN других пар не source fact. BUS — IATA Батуми, не автобус. Root открыл official RW Georgia: ZIA–Batumi Tue/Fri/Sun08:10 mixed Tu/SSJ, exact tail UNKNOWN. Ops COMPLETE numeric updates0, не доказывает free tail/cheap overnight. Root admissions market_recovery_admission.md и operations_cost_admission.md — completed входы pass2, без ожидания и нового поиска.
''')
    neg=sum(float(r['new_standalone_cautious'])<0 for r in short)
    (HERE/'README.md').write_text(f'''# P36 pass1 — недельные цепочки и действия

Локальный первый проход готов: **{attempts:,}** попыток config×baseline×action, {len(paths)} ограниченных путей, {configs} уникальных недельных календарных настроек, {len(short)} разных представителей shortlist. Это кандидаты проверки, не готовые запуски и не глобальный optimum.

Исследуются RT, обе ориентации triangle, настоящие closed4/5/6legs, CONCAT_RT и ночёвки вне базы. Все пути и отсечения есть в path_registry/path_expansion/search_space. 1–7ISO, 06/10/14/20 local и частоты1/2/3/5/7 — SCENARIO, не измеренный спрос удобного окна. Полный февраль2027 содержит4повтора; все плечи строятся целиком, выход за availability отклоняется.

B1 SCOPED_P34 оставляет остальные часы UNKNOWN/blocked; отдельная ветвь IDLE_SCENARIO имеет неизвестный unobserved loss. B2 — полный семидневный сценарий выбранной own программы GOJ4/KUF7/OMS2/UFA2 на2условных SVX tail, не наблюдённое расписание всего перевозчика. E1 отдельно; E2 Moscow требует условный рабочий RRJ и внешний D UNKNOWN. R1 не работает. Борт не появляется в новом аэропорту: цепь от SVX/DME/ZIA замыкается, неподтверждённый feeder оплачивается как ferry без продаж.

Физика UTC position/overlap/turn60/entry проверена отдельно от8BH/day. 8BH — диагностика, не FDP. Crew/MRO/AFM/slot/реальные регистрации и освобождение UNKNOWN. Даже физически согласованный swap не доказывает допуск и нулевую потерю продаж.

Экономический screen использует готовые P05 monthly priors и P04 cost transfer, отдельный100seat optimistic cap, base/caut на тех же датах и парке. Cargo/support0. Операционный поиск не зарабатывает премию за время. Thin candidate_chains.score ссылается на economics_screen.economic_id; action/result раскрываются в action_ids.csv/disposition_ids.csv, config — в schedule_configs.csv, setup — baseline_definitions.json. Полные три расписания только для shortlist. {neg} осторожных самостоятельных отрицательных представителей оставлены как category comparators, не победители; положительный эффект удаления старого не называется доходом нового.

Структурный осторожный предел: **каждое** допустимое направленное ребро16узлов отрицательно даже при100оплаченных креслах (edge_structural_bounds.csv/structural_proof.json). Поэтому любая непустая новая цепь при тех же cost/netfare не станет положительной от широты перебора. Среди searched RT минимальное повышение взвешенного netfare для full100 break-even ≈16.3%, или landed fuel до≈130872₽/т вместо161696₽/т; спрос при новом тарифе надо пересчитать. Это верхний screen до F/overnight и opportunityD, не фактическая прибыль. Для всех семейств пороги лежат в structural_bounds.csv; перенос cost anchors на сеть — гипотеза, не контракт.

Для shortlist есть KEEP / WITHOUT_NEW / REPLACE в three_state_screen: общий конечный MOW/city OD pool, capacity100, analytic capped direct-market MNL. Это не финальный P06 joint выбор с through/contract и completed новым research. Общий cancellation C у последних двух одинаков; full delta, cash, donor D, unobserved/retiming loss и F остаются UNKNOWN. Числа — только известный scoped scenario subtotal. Предполагаемые ночёвки записаны с UNKNOWN paid cost, не бесплатны.

Главные гипотезы pass2: реальные продажи/own shift и pure new contribution против WITHOUT_NEW; release и outside D для Москвы; короткие соседние OD, когда ferry не требуется; differential station/parking/overnight/setup/reserve; физически согласованные swaps; осторожный fuel/netfare gate при100креслах. Resource S0/S1/S1D6 вынесены отдельно, не новые SJ в феврале и не эквивалент PD8=RRJ.

Запуск: `python3 -B generate.py`, затем `python3 -B verify.py` из этой папки. validation.json фиксирует2реальных прогона, byte reproducibility,1418 protected файлов, все плечи/пулы/3состояния/слоты/types и fixture проверки. Старые builders, внешние источники и Git mutation не запускались. STOP после engine_handoff.md; pass2 отдельный.
''')
    (HERE/'engine_handoff.md').write_text('''# Handoff pass1 → pass2

Пакет завершён локально. Следующий проход должен прочитать completed admission новых research, затем объединение представителей категорий, а не весь thin screen. Свежий WZ901 snippet quarantined и не источник борта/донора. Старые positive P34 primary/dated rows остаются фактами с исходными scope/date.

Входы: shortlist.csv, shortlist_requests.json, shortlist_full_schedules.csv (KEEP/WITHOUT_NEW/REPLACE), action_map.csv, graph_edges.csv, economics_screen.csv, baseline_definitions.json, contracts.json, source_manifest.json. request задаёт целые closed weekly jobs с UTC минутами от2027-02-01T00Z; ISO weekdays преобразуются в P31 weekdays0..6 ровно один раз.

API существующий: P31 route_economics.calculate.evaluate_combined_programme и choice_bundle; P03 ops_inputs.calendar_engine.generate ISO1..7. Не вызывать старые build/verify. P34 keep_patterns / retained_patterns дают исправленный P32 FOLLOW. Сам full-month P31 старый short-horizon bug не исправлен глобально: требовать Feb01–28 и freq=dated departures*7/28,4повтора.

Для лидеров собрать три одинаковые оболочки флота: KEEP; те же removal/retiming/swap без новых; REPLACE. Выполнить совместный P05/P06 monthly direct+own/through/contract пересчёт на общем cityOD/dated seats, не суммировать solo margin и не вычитать donor второй раз. three_state_screen уже finite-pool-aware, но analytic preliminary без dated-seat и through: не выдавать за producer acceptance.

Ranking критерий нового: REPLACE minus WITHOUT_NEW с той же отменойC. Даже если WITHOUT_NEW выиграл уKEEP, это самостоятельная альтернатива. Старые потери move/swap, unknown занятость/D, station/overnight/setup/reserve_F и cancellation vsKEEP не нули. Москва — conditional existing RRJ, внешний internationalD UNKNOWN; CXR B777/Tu и старый ангар не ресурс. Для регионов только closed origins и платные ferry, не новая база.

Из shortlist взять union по SVX/Moscow, RT/triangle/4+/multiday,0/1/multiple removals/real swap/move, с фокусом UTC-consistent ≤8BH. RESOURCE_8BH_QUEUE и отрицательные category comparators не победители; отсутствие нужного физического класса объясняется shortlist_category_coverage/rejection_counts. Пределы поиска в search_space, оптимума нет.

Дальше stress turn90, holds30/60/120 по каждому плечу и следующему заданию; actual crew/rest/MRO/slot/AFM gates. Реальные netfare/demand/fuel/airport avoidability вместо сценариев только с допущенными completed источниками. Costscreen full100_cap/fuel_price_break_even_full100/netfare_break_even_full100 — потолок/пороги, не спрос. Класс с отрицательным осторожным full100_cap не спасает более широкий поиск при тех же cost/fare; менять можно только доказанные input/threshold assumptions.

S0/S1 Aug/Nov2027 entry и S1D6 Feb/May2028 — только resource cases, не обещанные поставки. Нельзя SJ до H22027/entry, нельзя переносить RRJ операционные характеристики на PD8. Main fullmonthFeb4weeks, другие месяцы по действительному календарю.

Права: запись только pass1 до этого handoff; далее STOP. NO commit/push/merge/reset/checkout.1418 protected неизменны. Research in-progress не читались; никаких внешних поисков, субагентов и панели.
''')

def main():
    initialize()
    paths,adj,proposals,partials=build_paths()
    setups=build_baselines()
    econ=econ_paths(paths)
    short,attempts,configs,coverage=run_search(paths,setups,econ)
    documents(paths,setups,adj,proposals,partials,attempts,configs,short)
    # Check the six existing minimal snapshots, without depending on research-agent directories.
    for r in json.loads((STUDY/'input_snapshot_manifest.json').read_text()):
        assert digest(STUDY/r['snapshot'])==r['sha256']
        SOURCES[r['path']+'@'+r['commit']]={'kind':'existing_minimal_snapshot',**r}
    dump('source_manifest.json',dict(team=TEAM,step1=STEP,sources=SOURCES,
       P36_research_read=False,quarantined=['WZ901 secondary MOW snippet','P36-WEB1 unrelated UNKNOWN attachment'],
       no_external_search=True,protected=protection()))
    print(json.dumps(dict(attempts=attempts,paths=len(paths),configs=configs,shortlist=len(short),protected=protection()),ensure_ascii=False))

if __name__=='__main__':main()
