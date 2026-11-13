#!/usr/bin/env python3
"""Bounded P38 weekly programme specifications. No monthly economics/imports.
Only writes next to this file. Python -B; completed inputs only, no network/git.
"""
import sys
sys.dont_write_bytecode = True
import ast
import copy
import csv
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P36 = ROOT/'context/36_overnight_chain_search_20261112'
P37 = ROOT/'context/37_svx_kja_keep_check_20261112/calculation'
P38 = HERE.parent
REF = datetime(2027, 2, 1, tzinfo=timezone.utc)  # Monday codec only, NOT operating period
WEEK, TURN = 10080, 60
WINDOWS = (6, 10, 14, 20)
FREQUENCIES = (1, 2, 3, 5, 7)
DAY_OFFSETS = {1:(0,), 2:(0,3), 3:(0,2,4), 5:(0,1,2,3,4), 7:tuple(range(7))}
SHIFTS = (-180,-120,-60,-30,30,60,120,180)
ZONES = dict(SVX='Asia/Yekaterinburg', ZIA='Europe/Moscow', DME='Europe/Moscow',
 KUF='Europe/Samara', UFA='Asia/Yekaterinburg', CEK='Asia/Yekaterinburg',
 TJM='Asia/Yekaterinburg', OMS='Asia/Omsk', PEE='Asia/Yekaterinburg',
 GOJ='Europe/Moscow', KJA='Asia/Krasnoyarsk', TOF='Asia/Tomsk', MRV='Europe/Moscow',
 AER='Europe/Moscow', REN='Asia/Yekaterinburg', IKT='Asia/Irkutsk')
LIMITS = dict(final_financial_templates=420, single_reservoir_per_class=1,
             same_tail_options=28, same_tail_pair_attempts_per_tail=378,
             fleet_tail_packs=14, fleet_beam=40, fleet_depth=3,
             pair_swap_trials=8, successful_action_variants_per_mixed=2,
             focused_mix_rotations=7, focused_second_windows=[10,20], nested_pairs=8)
READS, COUNTS, REJECT = {}, Counter(), Counter()
REJECT_EXAMPLES = {}
EDGES, PATHS, COHORTS, OPTIONS = {}, {}, {}, {}
ALL = {}
SINGLE = {}
PATH_STATS = defaultdict(Counter)
PAIR_STATS = defaultdict(Counter)

def serial(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(x): return hashlib.sha256(serial(x).encode()).hexdigest()[:20]
def read(p):
    READS[str(Path(p).relative_to(ROOT))] = digest(p)
    return list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')))
def jsread(p):
    READS[str(Path(p).relative_to(ROOT))] = digest(p)
    return json.loads(Path(p).read_text())
def textread(p):
    READS[str(Path(p).relative_to(ROOT))] = digest(p)
    return Path(p).read_text()
def dump(n,x):
    assert Path(n).name==n
    (HERE/n).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def table(n,rows,fields=None):
    assert Path(n).name==n
    rows=list(rows); fields=fields or list(rows[0])
    with (HERE/n).open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,lineterminator='\n');w.writeheader()
        for r in rows:w.writerow({k:('UNKNOWN' if v is None else v) for k,v in r.items()})
def dt(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
def minute(s): return int(round((dt(s)-REF).total_seconds()/60))
def loc(t,a): return (REF+timedelta(minutes=t)).astimezone(ZoneInfo(ZONES[a]))
def localminute(day,hour,a):
    return int(((REF+timedelta(days=day)).replace(hour=hour,minute=0,tzinfo=ZoneInfo(ZONES[a])).astimezone(timezone.utc)-REF).total_seconds()/60)
def city(a): return 'MOW' if a in ('DME','ZIA') else a
def pair(a,b): return '-'.join(sorted((a,b)))
def legs(jobs): return [f for j in jobs for f in j['flights']]
def complete_job(j):
    j['flights'].sort(key=lambda f:(f['dep'],f['flight_id']))
    j.update(start=j['flights'][0]['dep'],end=j['flights'][-1]['arr'],
             origin=j['flights'][0]['origin'],destination=j['flights'][-1]['destination'])
    return j

def check_calendar(jobs, positions, turn=60, full=False):
    """Periodic, no ready=0 reset. Compare predecessor/successor across week.
    Anchor is at first departure of a closed job, not UTC Monday midnight.
    Every event is checked against one predecessor including week wrap.
    """
    fs=legs(jobs); ids=[f['flight_id'] for f in fs]
    errs=[]; daily=Counter(); localdaily=Counter(); gaps=[]; seams={}
    if len(ids)!=len(set(ids)):errs.append('DUPLICATE_FLIGHT_ID')
    if len({j['id'] for j in jobs})!=len(jobs):errs.append('DUPLICATE_JOB_ID')
    for f in fs:
        if f['tail'] not in positions:errs.append('PHANTOM_OR_RESERVE_TAIL')
        if f['origin'] not in ZONES or f['destination'] not in ZONES:errs.append('NONPHYSICAL_AIRPORT')
        if f['arr']-f['dep']!=f['block'] or f['block']<=0:errs.append('BLOCK_DURATION')
        if f['kind']=='PAID_FERRY' and (f.get('seats',0)!=0 or f.get('revenue',0)!=0):errs.append('FERRY_SALES')
        for off,aggregate in [(0,daily),(int(loc(f['dep'],f['origin']).utcoffset().total_seconds()/60),localdaily)]:
            t=f['dep']+off;e=f['arr']+off
            while t<e:
                end=min(e,(t//1440+1)*1440)
                aggregate[f['tail'],(t//1440)%7]+=end-t;t=end
    for tail,initial in positions.items():
        seq=sorted([f for f in fs if f['tail']==tail],key=lambda f:(f['dep'],f['flight_id']))
        if not seq:
            seams[tail]=dict(position='SVX' if initial=='SVX' else initial,ready_minute=None,anchor_basis='periodic scenario idle; actual UNKNOWN')
            continue
        # A job can start before UTC Monday or finish after Sunday. Sort one
        # representative of every flight modulo week for an exact cyclic proof.
        ss=sorted([(f['dep']%WEEK,f['arr']-f['dep'],f) for f in seq],key=lambda x:(x[0],x[2]['flight_id']))
        for i,(d,b,f) in enumerate(ss):
            pd,pb,pf=ss[i-1]
            if i==0:pd-=WEEK
            gap=d-(pd+pb)
            gaps.append(gap-turn)
            if pf['destination']!=f['origin']:errs.append('POSITION')
            if gap<0:errs.append('OVERLAP')
            elif gap<turn:errs.append('TURN')
        # Closed jobs anchor every tail at a known physical base once per week.
        starts=sorted([j for j in jobs if j['tail']==tail],key=lambda j:(j['start'],j['id']))
        if starts and starts[0]['origin']!=initial:errs.append('INITIAL_ANCHOR_POSITION')
        prior=[(d-WEEK,b,f) for d,b,f in ss]
        d,b,f=prior[-1];end=d+b
        seams[tail]=dict(position=('IN_AIR:'+f['origin']+'>'+f['destination']) if end>0 else f['destination'],
                         ready_minute=end+turn,preceding_flight=f['flight_id'],
                         anchor_basis='derived periodic boundary; actual readiness UNKNOWN')
    out=dict(hard_pass=not errs,errors=sorted(set(errs)),flight_count=len(fs),weekwrap_checked=True,
             min_slack_after_turn=min(gaps) if gaps else None,
             max_UTC_day_BH=round(max(daily.values(),default=0)/60,6),
             max_departure_local_day_BH=round(max(localdaily.values(),default=0)/60,6),
             BH8_diagnostic_exceeded=any(v>480 for v in daily.values()),
             FDP='UNKNOWN_NOT_CHECKED_BY_MIDNIGHT',initial_ready_actual=None,
             midnight_carry=seams)
    if full:out['UTC_day_BH']={t+'/'+str(d+1):round(v/60,6) for (t,d),v in sorted(daily.items())}
    return out

def reject(stage,reason,example):
    REJECT[stage,reason]+=1
    REJECT_EXAMPLES.setdefault((stage,reason),serial(example)[:700])

def load_inputs():
    # This fixed receipt is the completed 1621-file preservation set. No git,
    # coordinator source pins, panel logs, or other mutable metadata are read.
    protected=jsread(P38/'cost_admission/excerpts/preservation_before.json')
    assert len(protected)==1621
    for n in ('source_gate_for_calculation.md','market_admission/README.md','cost_admission/README.md',
              'contract/engine_handoff.md','contract/month_adapter.py'):
        textread(P38/n)
    for n in ('source_manifest.json','baseline_definitions.json','shortlist_requests.json'):
        jsread(P36/'pass1'/n)
    jsread(P36/'pass2/input_manifest.json')
    jsread(P37/'source_manifest.json')
    resource=jsread(P38/'contract/resource_contract.json')
    textread(P36/'pass2/calculate.py')  # read AST only below; never execute
    seeds=read(P38/'pair_seed.csv')
    marketpairs=read(P38/'market_admission/canonical_pairs.csv')
    services=read(P38/'market_admission/canonical_services.csv')
    read(P38/'cost_admission/canonical_cost_items.csv')
    read(P38/'cost_admission/reserve_launch_costs.csv')
    read(P36/'pass2/final3_weekly_schedule.csv')
    top5=read(P36/'pass2/top5_pairs.csv')
    bep=read(P37/'break_even.csv')
    assert [(r['scenario'],r['n_out'],r['n_back']) for r in bep if r['metric']=='balanced_minimum_strict' and r['horizon']=='ONE_ROTATION']==[('base','69','69'),('cautious','115','115')]
    EDGES.update({(r['origin'],r['destination']):r for r in read(P36/'pass1/graph_edges.csv')})
    registry=read(P36/'pass1/path_registry.csv')
    for r in registry:
        if r['disposition']=='PARAMETER_SEARCH':
            PATHS[r['path_id']]=dict(id=r['path_id'],path=r['path'].split('-'),family=r['family'],
                overnight_after=int(r['overnight_after']),source='P36_103',
                old_optimistic_cautious_bound=float(r['optimistic_cap_cautious_per_rotation']))
    assert len(PATHS)==103
    # Parse a completed literal, not old choose_candidates() or imports.
    tree=ast.parse((P36/'pass2/calculate.py').read_text())
    custom=next(ast.literal_eval(x.value) for x in ast.walk(tree) if isinstance(x,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='custom' for t in x.targets))
    for name,path,days,after in custom:
        pid='X_'+name
        PATHS[pid]=dict(id=pid,path=path,family='RT' if len(path)==3 else 'TRIANGLE',
                       overnight_after=after,source='P36_pass2_required',old_optimistic_cautious_bound=None)
    # Exact legacy states from the complete ledger; equivalence aliases resolved.
    eq={(r['candidate_id'],r['state']):(r['equivalent_candidate'],r['equivalent_state'])
        for r in read(P36/'pass2/equivalence_map.csv') if r['scenario']=='base'}
    grouped=defaultdict(dict)
    for r in read(P36/'pass2/revenue_cost_ledger.csv'):
        if r['scenario']!='base' or not r['flight_id'].endswith('/W1'):continue
        b=int(EDGES[r['origin'],r['destination']]['minutes'])
        assert abs(b-float(r['fixed_crew_excluded'])/15000*60)<1e-5
        k=(r['candidate_id'],r['state']);jid=r['job_id']
        j=grouped[k].setdefault(jid,dict(id=jid,tail=r['tail'],flights=[],source='completed P36 ledger',actual_registration=None,actual_release=None))
        d=minute(r['departure_utc']);kind='PAID_FERRY' if r['kind']=='positioning' else 'SERVICE'
        j['flights'].append(dict(flight_id=r['flight_id'].removesuffix('/W1'),job_id=jid,tail=r['tail'],
            origin=r['origin'],destination=r['destination'],dep=d,arr=d+b,block=b,kind=kind,
            seats=0 if kind=='PAID_FERRY' else 100,evidence=EDGES[r['origin'],r['destination']]['block_evidence']))
    for v in grouped.values():
        for j in v.values():complete_job(j)
    legacyrows={r['candidate_id']:r for r in read(P36/'pass2/candidate_results.csv') if r['scenario']=='base'}
    assert len(legacyrows)==60 and sum(float(r['new_minus_same_WITHOUT_NEW'])>0 for r in legacyrows.values())==37
    legacy={}
    for cid,r in legacyrows.items():
        states={s:list(grouped[eq[cid,s]].values()) for s in ('KEEP','WITHOUT_NEW','REPLACE')}
        legacy[cid]=(r,states)
    b2=copy.deepcopy(legacy['X_SVX_KJA'][1]['KEEP'])
    for c in resource['cohorts']:
        ids={j['id'] for j in c['old_jobs']}
        jobs=[copy.deepcopy(j) for j in b2 if j['id'] in ids]
        assert len(jobs)==len(ids)
        COHORTS[c['id']]=dict(id=c['id'],old_jobs=jobs,positions=c['positions'],
            primary=True,baseline=c['baseline'],outside_D=None,old_D3=c['old_D3'],
            outside_work='UNKNOWN; scenario gaps conditional, never actual release',
            reserve=dict(id='R1',working=False,actual_available=None,opportunity_cost=None),
            actual_initial_positions=None,actual_release=None,F=None,lease=None,crew=None)
    assert len(COHORTS['K1']['old_jobs'])==11 and len(COHORTS['K2']['old_jobs'])==15
    # Preserve the original cohorts of all 60, separately from canonical K1.
    bd=jsread(P36/'pass1/baseline_definitions.json')['baselines']
    for cid,(r,states) in legacy.items():
        if r['setup'] in ('B2S','B2T'):sid='K2'
        else:
            sid='LEGACY_'+r['setup']
            if sid not in COHORTS:
                b=bd[r['setup']]
                COHORTS[sid]=dict(id=sid,old_jobs=states['KEEP'],positions=b['positions'],primary=False,
                    baseline=b['baseline'],outside_D=None,old_D3='not applicable',outside_work=b['unknown'],
                    reserve=dict(id='R1',working=False,actual_available=None,opportunity_cost=None),
                    actual_initial_positions=None,actual_release=None,F=None,lease=None,crew=None)
        assert check_calendar(states['KEEP'],COHORTS[sid]['positions'])['hard_pass']
        register_legacy(cid,sid,r,states)
    # Hash ONLY fixed completed P36/P37 trees, not a recursive guard of P38.
    completed={}
    for folder in (P36/'pass1',P36/'pass2',P37):
        for p in sorted(folder.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                completed[str(p.relative_to(ROOT))]=digest(p)
    return dict(protected=protected,completed=completed,seed=seeds,marketpairs=marketpairs,
                services=services,top5=top5,registry=registry,legacy=legacy,resource=resource)

def path_class(path):
    p=path['path'];n=len(p)-1
    if n==2:return 'RT'
    if len(set(p[:-1]))==n:return 'TRIANGLE' if n==3 else 'TRUE_CYCLE'+str(n)
    return 'CONCAT_RT'

def new_option(pid,days,hour,tail,paid_base_feeder=True):
    p=PATHS[pid];base=p['path'][0]
    spec=dict(path_id=pid,tail=tail,iso_weekdays=sorted(d+1 for d in days),
              local_window=f'{hour:02}:00',window_airport=base,overnight_after=p['overnight_after'],
              feeder_from='SVX' if base!='SVX' and paid_base_feeder else None,
              feeder_kind='PAID_FERRY' if base!='SVX' and paid_base_feeder else None)
    oid='O'+key(spec)
    if oid in OPTIONS:return oid
    jobs=[]
    for day in days:
        jid='NEW-'+oid+'-ISO'+str(day+1);t=localminute(day,hour,base);flights=[]
        if base!='SVX' and paid_base_feeder:
            e=EDGES['SVX',base];b=int(e['minutes'])
            flights.append(dict(origin='SVX',destination=base,dep=t-60-b,arr=t-60,block=b,
                                kind='PAID_FERRY',seats=0,evidence='P36 directed block; paid SVX feeder scenario, no sales'))
        for i,(a,b) in enumerate(zip(p['path'],p['path'][1:]),1):
            e=EDGES[a,b];mins=int(e['minutes'])
            flights.append(dict(origin=a,destination=b,dep=t,arr=t+mins,block=mins,kind=e['kind'],
                                seats=0 if e['kind']=='PAID_FERRY' else 100,evidence=e['block_evidence']))
            t+=mins+60
            if i==p['overnight_after']:
                arr=loc(t-60,b);morning=arr.replace(hour=6,minute=0,second=0,microsecond=0)
                while morning<arr+timedelta(hours=8):morning+=timedelta(days=1)
                t=int((morning.astimezone(timezone.utc)-REF).total_seconds()/60)
        if base!='SVX' and paid_base_feeder:
            e=EDGES[base,'SVX'];mins=int(e['minutes'])
            flights.append(dict(origin=base,destination='SVX',dep=t,arr=t+mins,block=mins,
                                kind='PAID_FERRY',seats=0,evidence='P36 directed block; paid return feeder scenario, no sales'))
        for i,f in enumerate(flights,1):f.update(flight_id=jid+'/L'+str(i),job_id=jid,tail=tail)
        jobs.append(complete_job(dict(id=jid,tail=tail,flights=flights,source='P38 weekly scenario',actual_registration=None,actual_release=None)))
    OPTIONS[oid]=dict(id=oid,**spec,jobs=jobs,source_family=p['family'],topology_class=path_class(p),
        actual_slot=None,actual_commercial_schedule=None,actual_newness=None,feeder_revenue=0,
        overnight_cost=None if p['overnight_after'] else 'not applicable')
    return oid

def action_map(old,changed):
    by={j['id']:j for j in changed};out={}
    for j in old:
        q=by.get(j['id'])
        if q is None:out[j['id']]=dict(action='REMOVE',from_tail=j['tail'],to_tail=None,shift_minutes=0,reason='common closure for all new jobs')
        else:
            shift=q['start']-j['start'];tail=q['tail']
            a='SWAP' if tail!=j['tail'] else 'SHIFT' if shift else 'RETAIN'
            out[j['id']]=dict(action=a,from_tail=j['tail'],to_tail=tail,shift_minutes=shift,
                             reason='physically checked entire closed old job' if a!='RETAIN' else 'existing retained')
    return out

def variant(cohort,options,changed,label,legacy_ids=None):
    c=COHORTS[cohort];new=[j for o in options for j in OPTIONS[o]['jobs']]
    amap=action_map(c['old_jobs'],changed)
    return dict(cohort=cohort,option_ids=sorted(options),action_map=amap,action_label=label,
                legacy_ids=legacy_ids or [],new_jobs=new,changed_old_jobs=changed)

def finite_signature(v):
    """Direct-only financial candidate class, never a calendar feasibility proof.
    No time premium: exclude clock but include directed local day inventories,
    physical airports, kinds, tails, overnight quantities and exact old changes.
    Optional through allocations MUST use the full exact-calendar cache instead.
    """
    inv=Counter((f['tail'],f['origin'],f['destination'],f['kind'],loc(f['dep'],f['origin']).isoweekday())
                for j in v['new_jobs'] for f in j['flights'])
    chains=sorted((OPTIONS[o]['tail'],
        tuple((f['origin'],f['destination'],f['kind']) for f in OPTIONS[o]['jobs'][0]['flights']),
        len(OPTIONS[o]['jobs'])) for o in v['option_ids'])
    overnight=[]
    for j in v['new_jobs']:
        for a,b in zip(j['flights'],j['flights'][1:]):
            if b['dep']-a['arr']>=480:overnight.append((j['tail'],a['destination'],b['dep']-a['arr']))
    return key(dict(cohort=v['cohort'],actions=v['action_map'],inventory=sorted([list(k)+[n] for k,n in inv.items()]),
                    chains=chains,overnights=sorted(overnight)))

def register(v,stage):
    fid=finite_signature(v)
    if fid not in ALL:ALL[fid]=dict(id='W'+fid,financial_key=fid,variants=[],stages=set())
    a=ALL[fid];a['stages'].add(stage)
    sig=key(dict(options=v['option_ids'],actions=v['action_map']))
    if not any(x['_calendar_key']==sig for x in a['variants']):
        if len(a['variants'])<2 or v['legacy_ids']:
            a['variants'].append(dict(v,_calendar_key=sig))
        else:COUNTS['calendar_variants_pruned_cap2']+=1
    else:
        for x in a['variants']:
            if x['_calendar_key']==sig:x['legacy_ids']=sorted(set(x['legacy_ids']+v['legacy_ids']))
    return fid

def register_legacy(cid,sid,r,states):
    oldids={j['id'] for j in states['KEEP']}
    new=[j for j in states['REPLACE'] if j['id'] not in oldids]
    opt=dict(path_id='LEGACY:'+cid,tail=new[0]['tail'] if new else None,
        iso_weekdays=sorted({loc(j['start'],j['origin']).isoweekday() for j in new}),local_window='EXACT_P36_LEDGER',
        window_airport=r['path'].split('-')[0],overnight_after=None,feeder_from=None,feeder_kind=None,
        jobs=new,source_family='LEGACY_EXACT',topology_class=path_class(dict(path=r['path'].split('-'))),
        actual_slot=None,actual_commercial_schedule=None,actual_newness=None,feeder_revenue=0,overnight_cost=None)
    oid='L'+cid;OPTIONS[oid]=dict(id=oid,**opt)
    # WITHOUT_NEW may alias KEEP; assert old identities and same old changes.
    changed=states['WITHOUT_NEW']
    assert {j['id'] for j in changed}.issubset(oldids)
    assert serial(sorted(changed,key=lambda j:j['id']))==serial(sorted([j for j in states['REPLACE'] if j['id'] in oldids],key=lambda j:j['id']))
    v=variant(sid,[oid],changed,'LEGACY_'+r['action'],[cid])
    for s,j in states.items():assert check_calendar(j,COHORTS[sid]['positions'])['hard_pass'],(cid,s)
    register(v,'legacy60')

def clashes(old,new):
    # Every old/new job is closed at its tail's initial base. Occupancy through
    # a real overnight is reserved; we do not reuse the same tail while away.
    return sorted(j['id'] for j in old if any(j['tail']==n['tail'] and
        any(j['start']+w*WEEK<n['end']+60 and n['start']<j['end']+w*WEEK+60 for w in (-1,0,1))
        for n in new))

def changed(old,removed=(),shifts=None,swaps=None):
    shifts=shifts or {};swaps=swaps or {};out=[]
    for j in old:
        if j['id'] in removed:continue
        delta=shifts.get(j['id'],0);tail=swaps.get(j['id'],j['tail'])
        if not delta and tail==j['tail']:out.append(j);continue
        q=copy.deepcopy(j);q['tail']=tail
        for f in q['flights']:f['dep']+=delta;f['arr']+=delta;f['tail']=tail
        complete_job(q);out.append(q)
    return out

def dispositions(sid,option_ids,stage,all_actions=True):
    c=COHORTS[sid];new=[j for o in option_ids for j in OPTIONS[o]['jobs']]
    ck=check_calendar(new,c['positions']);COUNTS[stage+'_new_checks']+=1
    if not ck['hard_pass']:
        reject(stage,'NEW_'+','.join(ck['errors']),option_ids);return []
    conflict=clashes(c['old_jobs'],new)
    out=[];seen=set();trials=[('INSERT',(),{}, {})]
    if conflict:
        trials += [('SHIFT'+('%+d'%d),(),{j:d for j in conflict},{}) for d in SHIFTS]
        for n in (1,2,3):
            # These bounded removal actions never gratuitously delete donors.
            # Inapplicable exact cardinalities are counted rather than padded.
            if len(conflict)==n:trials.append(('REMOVE'+str(n),tuple(conflict),{},{}))
            else:reject(stage,'REMOVE'+str(n)+'_CANNOT_CLEAR_EXACT_CONFLICT_SET',dict(conflicts=conflict,options=option_ids))
        trials += [('MIN_CLOSURE',tuple(conflict),{},{}),('ALL_AFFECTED',tuple(conflict),{},{})]
        if len(c['positions'])>1:
            # Whole closed jobs transferred only between existing working tails.
            by={j['id']:j for j in c['old_jobs']}
            for receive in c['positions']:
                swaps={j:receive for j in conflict if by[j]['tail']!=receive}
                if len(swaps)==len(conflict):trials.append(('SWAP_TRANSFER_TO_'+receive,(),{},swaps))
            pairs=0
            for a in conflict:
                for b in c['old_jobs']:
                    if by[a]['tail']==b['tail'] or b['id'] in conflict:continue
                    if pairs>=LIMITS['pair_swap_trials']:break
                    trials.append(('SWAP_PAIR',(),{},{a:b['tail'],b['id']:by[a]['tail']}));pairs+=1
        else:reject(stage,'SWAP_NO_SECOND_WORKING_TAIL',option_ids)
    else:
        COUNTS[stage+'_no_conflict_action_variants_not_needed']+=1
    for label,remove,shift,swap in trials:
        COUNTS[stage+'_action_attempts']+=1
        change=changed(c['old_jobs'],remove,shift,swap)
        sig=key([(j['id'],j['tail'],j['start']) for j in change])
        if sig in seen:COUNTS[stage+'_equivalent_actions']+=1;continue
        seen.add(sig)
        result=check_calendar(change+new,c['positions'])
        if not result['hard_pass']:
            reject(stage,label+':'+','.join(result['errors']),dict(options=option_ids,conflicts=conflict));continue
        # Removal/shift cannot invalidate W silently.
        w=check_calendar(change,c['positions'])
        if not w['hard_pass']:
            reject(stage,label+':WITHOUT_'+','.join(w['errors']),option_ids);continue
        v=variant(sid,option_ids,change,label);v['_physics']=result
        out.append(v);COUNTS[stage+'_action_feasible']+=1
    out.sort(key=priority)
    return out if all_actions else out[:LIMITS['successful_action_variants_per_mixed']]

def priority(v):
    acts=list(v['action_map'].values())
    return (sum(a['action']=='REMOVE' for a in acts),
            sum(a['action']=='SWAP' for a in acts),sum(a['action']=='SHIFT' for a in acts),
            sum(abs(a['shift_minutes']) for a in acts),
            v.get('_physics',{}).get('BH8_diagnostic_exceeded',False),
            -len(v['option_ids']), tuple(v['option_ids']),v['action_label'])

def afamily(v):
    return 'REMOVE' if any(a['action']=='REMOVE' for a in v['action_map'].values()) else \
           'SWAP' if any(a['action']=='SWAP' for a in v['action_map'].values()) else \
           'SHIFT' if any(a['action']=='SHIFT' for a in v['action_map'].values()) else 'INSERT'

def single_search():
    for pid,p in sorted(PATHS.items()):
        for freq in FREQUENCIES:
            for rotation in range(7):
                days=sorted({(rotation+x)%7 for x in DAY_OFFSETS[freq]})
                # Seven rotations of frequency7 are identical.
                if freq==7 and rotation:COUNTS['single_equivalent_day_rotations']+=1;continue
                for h in WINDOWS:
                    for sid in ('K1','K2','K3'):
                        for tail in COHORTS[sid]['positions']:
                            oid=new_option(pid,days,h,tail)
                            PATH_STATS[pid]['assigned_config_attempts']+=1
                            for v in dispositions(sid,[oid],'single'):
                                PATH_STATS[pid]['feasible_action_calendars']+=1
                                k=(sid,pid,tail,freq,afamily(v))
                                if k not in SINGLE or priority(v)<priority(SINGLE[k]):SINGLE[k]=v
    for v in SINGLE.values():register(v,'single_reservoir')
    COUNTS['single_reservoir_classes']=len(SINGLE)

def diversify(items,n,group):
    groups=defaultdict(list)
    for v in sorted(items,key=priority):groups[group(v)].append(v)
    out=[];depth=0
    while len(out)<n:
        added=0
        for g in sorted(groups,key=str):
            if depth<len(groups[g]):out.append(groups[g][depth]);added+=1
            if len(out)==n:break
        if not added:break
        depth+=1
    return out

def mixed_search():
    packs=defaultdict(list)
    # Focus set is fixed from old top5/AER and required orientations; no cities
    # are scanned anew. All 103 already had the full discrete single search.
    focus=['X_AER1','X_SVX_KJA','X_SVX_IKT','X_GOJ_KJA_F','X_GOJ_KJA_R',
           'X_TJM_MRV_F','X_TJM_MRV_R','X_CEK_MRV_F','X_CEK_MRV_R',
           'X_GOJ_TOF_F','X_GOJ_TOF_R','X_AER_MRV','X_MRV_AER']
    # Deterministic seeded calendar overlays expose AER 2/3/5 days + KJA/IKT/GOJ
    # on other days and both triangle directions. Every combination is replayed.
    recipes=[('X_AER1',f,b) for f in (2,3,5) for b in ('X_SVX_KJA','X_SVX_IKT','X_GOJ_KJA_F','X_GOJ_KJA_R')]
    recipes += [('X_GOJ_KJA_F',2,'X_GOJ_KJA_R'),('X_TJM_MRV_F',2,'X_TJM_MRV_R'),
                ('X_CEK_MRV_F',2,'X_CEK_MRV_R'),('X_AER_MRV',2,'X_MRV_AER')]
    for sid in ('K1','K2','K3'):
        for tail in COHORTS[sid]['positions']:
            singles=[v for k,v in SINGLE.items() if k[0]==sid and k[2]==tail]
            def grp(v):
                o=OPTIONS[v['option_ids'][0]];pid=o['path_id']
                return (0 if pid in focus else 1,o['topology_class'],pid if pid in focus else 'CONTROL')
            options=diversify(singles,LIMITS['same_tail_options'],grp)
            for a,b in itertools.combinations(options,2):
                if OPTIONS[a['option_ids'][0]]['path_id']==OPTIONS[b['option_ids'][0]]['path_id']:
                    COUNTS['mixed_same_path_not_second_distinct_path']+=1;continue
                ids=a['option_ids']+b['option_ids']
                for v in dispositions(sid,ids,'same_tail',False):
                    register(v,'same_tail_beam');packs[sid,tail].append(v)
            for p,f,q in recipes:
                for rotation in range(7):
                    d1=sorted({(rotation+x)%7 for x in DAY_OFFSETS[f]})
                    for off in (1,3):
                        d2=sorted({(rotation+off+x)%7 for x in DAY_OFFSETS[2 if p=='X_GOJ_KJA_F' else 1]})
                        for second_hour in LIMITS['focused_second_windows']:
                            ids=[new_option(p,d1,6,tail),new_option(q,d2,second_hour,tail)]
                            for v in dispositions(sid,ids,'focused_mix',False):
                                register(v,'focused_mixed');packs[sid,tail].append(v)
            packs[sid,tail]+=options
    # Different chains on 2/3 tails, with up to two closed paths on EACH tail.
    # Recompute one joint old action map after every extension (never sum states).
    for sid in ('K2','K3'):
        beam=[None]
        for tail in COHORTS[sid]['positions']:
            options=diversify([v for v in packs[sid,tail] if len(v['option_ids'])==1],6,
                lambda v:tuple(OPTIONS[o]['topology_class'] for o in v['option_ids']))
            options+=diversify([v for v in packs[sid,tail] if len(v['option_ids'])==2],8,
                lambda v:tuple(OPTIONS[o]['topology_class'] for o in v['option_ids']))
            nxt=[]
            for b in beam:
                for a in options:
                    ids=(b['option_ids'] if b else [])+a['option_ids']
                    for v in dispositions(sid,ids,'fleet_mix',False):
                        register(v,'fleet_beam');nxt.append(v)
            lengths=sorted({len(v['option_ids']) for v in nxt})
            beam=[]
            for length in lengths:
                beam+=diversify([v for v in nxt if len(v['option_ids'])==length],
                    max(1,LIMITS['fleet_beam']//len(lengths)),
                    lambda v:tuple(sorted(set(OPTIONS[o]['path_id'] for o in v['option_ids']))))
            beam=beam[:LIMITS['fleet_beam']]
            COUNTS['fleet_retained_states_depth_'+sid+'_'+tail]=len(beam)
    COUNTS['whole_week_mixed_distinct_financial_classes']=sum(any(len(v['option_ids'])>=2 for v in a['variants']) for a in ALL.values())

def select_templates():
    selected={}
    def take(a):
        if len(selected)<LIMITS['final_financial_templates']:selected.setdefault(a['financial_key'],a)
    # All60 exact legacy references, even nonpositive, retain aliases and
    # separate cohorts. They may share a financial class but never share proof.
    for a in ALL.values():
        if 'legacy60' in a['stages']:take(a)
    rest=[a for a in ALL.values() if a['financial_key'] not in selected]
    # Force useful product-test and mixed-frequency witnesses before the
    # category quotas. Feasibility is proved, sales/economics remain UNKNOWN.
    for sid in ('K1','K2','K3'):
        own=[a for a in rest if a['variants'][0]['cohort']==sid]
        for x,y in (('SVX','KJA'),('SVX','IKT'),('GOJ','KJA')):
            eligible=[]
            for a in own:
                v=a['variants'][0]
                inv=Counter((f['origin'],f['destination']) for f in legs(v['new_jobs']) if f['kind']=='SERVICE')
                if inv[x,y]>=2 and inv[y,x]>=2:eligible.append(a)
            if eligible:take(min(eligible,key=lambda a:priority(a['variants'][0])))
        for freq in (2,3,5):
            eligible=[a for a in own if any(
                OPTIONS[o]['path_id']=='X_AER1' and len(OPTIONS[o]['iso_weekdays'])==freq
                for o in a['variants'][0]['option_ids']) and len(a['variants'][0]['option_ids'])>=2]
            if eligible:take(min(eligible,key=lambda a:priority(a['variants'][0])))
        for length in (2,3,4,5,6):
            eligible=[a for a in own if len(a['variants'][0]['option_ids'])==length]
            if eligible:take(min(eligible,key=lambda a:priority(a['variants'][0])))
    rest=[a for a in rest if a['financial_key'] not in selected]
    # Explicit witnesses: each seed pair, family, cohort, action and path-count.
    def attrs(a):
        v=a['variants'][0];ops=[OPTIONS[o] for o in v['option_ids']]
        return dict(cohort=v['cohort'],mode='MULTI_TAIL' if len({o['tail'] for o in ops})>1 else 'SAME_TAIL_MIXED' if len(ops)>1 else 'SINGLE',
                    action=afamily(v),families=tuple(sorted({o['topology_class'] for o in ops})),
                    paths=len(ops),newtails=len({o['tail'] for o in ops}),
                    overnight=any(o.get('overnight_after') for o in ops),
                    ferry=any(f['kind']=='PAID_FERRY' for f in legs(v['new_jobs'])))
    groups=defaultdict(list)
    for a in rest:
        v=a['variants'][0];d=attrs(a)
        g=(d['cohort'],d['mode'],d['families'],d['action'],d['newtails'])
        groups[g].append(a)
    # Within each bounded class prefer few removed jobs and then more mixed
    # paths. This is calendar admission, not monetary or observed ranking.
    for g in groups:groups[g].sort(key=lambda a:priority(a['variants'][0]))
    depth=0
    while len(selected)<LIMITS['final_financial_templates']:
        count=0
        for g in sorted(groups,key=str):
            if depth<len(groups[g]):take(groups[g][depth]);count+=1
        if not count:break
        depth+=1
    return list(selected.values())

def nested_pairs(selected):
    """Real K2/K3 paired allocations with identical master old obligations.
    K1/K2 core incompatibility is explicitly exported, no invented marginal.
    """
    master=COHORTS['K2']['old_jobs'];missing=sorted(set(j['id'] for j in master)-set(j['id'] for j in COHORTS['K1']['old_jobs']))
    constraints=dict(master_old_job_ids=sorted(j['id'] for j in master),
        K1_to_K2=dict(status='CORE_CONSTRAINT_FOR_MONTHLY_ENGINE',canonical_K1_missing_master_ids=missing,
            fixed_master_KEEP_one_tail_hard_pass=check_calendar(changed(master,swaps={j:'T1' for j in missing}),{'T1':'SVX'})['hard_pass'],
            required='Solve both lower/upper allocations with all15 obligations; allow explicit remove/retime/transfer and own C differences. Canonical K1 subtotal cannot substitute.',
            marginal_value=None),
        K2_to_K3=dict(status='PAIRED_WEEKLY_ALLOCATIONS_EXPORTED',master_old_job_ids=sorted(j['id'] for j in master)),
        formula='joint optimal contribution upper - lower - uncovered outside opportunity - new fixed payments - incremental shared R1; C differences explicit; no second old-sale deduction',
        optimum_proved=False,actual_C_difference=None,actual_D_difference=None,actual_F_difference=None,actual_marginal_value=None)
    pairs=[]
    candidates=[a for a in selected if a['variants'][0]['cohort']=='K2' and len(a['variants'][0]['option_ids'])>=2 and 'legacy60' not in a['stages']]
    candidates.sort(key=lambda a:priority(a['variants'][0]))
    for a in candidates[:LIMITS['nested_pairs']]:
        low=a['variants'][0]
        # Select an additional different path on T3 with no new-vs-new conflict.
        for pid in ('X_SVX_KJA','X_SVX_IKT','X_GOJ_KJA_F','X_GOJ_KJA_R'):
            oid=new_option(pid,[1,4],10,'T3')
            high=variant('K3',low['option_ids']+[oid],low['changed_old_jobs'],'NESTED_KEEP_SAME_OLD_CHANGE')
            high['_physics']=check_calendar(high['changed_old_jobs']+high['new_jobs'],COHORTS['K3']['positions'])
            if high['_physics']['hard_pass']:
                fid=register(high,'nested_allocation');upper=ALL[fid]
                # Nested exports are standalone allocation specs, not additional
                # selected financial classes, so the420 upper bound stays exact.
                pairs.append(dict(id='N23-'+str(len(pairs)+1),lower_programme=a['id'],
                    upper_variant=export_variant(high),master_old_job_ids=constraints['master_old_job_ids'],
                    same_old_action_map=low['action_map']==high['action_map'],
                    cancellation_difference='SYMBOLIC_C_UPPER_MINUS_C_LOWER; same map => common scoped cancellations',
                    outside_D_difference=None,fixed_cost_difference=None,R1_difference=None,marginal_value=None))
                break
    constraints['pairs']=pairs
    return constraints

def export_variant(v):
    return dict(cohort=v['cohort'],option_ids=v['option_ids'],action_map=v['action_map'],
                action_label=v['action_label'],legacy_programme_ids=v['legacy_ids'],
                initial_positions=COHORTS[v['cohort']]['positions'],
                initial_positions_actual=None,initial_ready_actual=None,
                exact_calendar_cache_key=key(dict(options=[OPTIONS[o] for o in v['option_ids']],actions=v['action_map'],cohort=COHORTS[v['cohort']])),
                outside_D=None,F=None,old_D3=None if v['cohort']=='K3' else 'not applicable')

def states_for(v):
    c=COHORTS[v['cohort']];keep=c['old_jobs']
    amap=v['action_map']
    change=changed(keep,[j for j,a in amap.items() if a['action']=='REMOVE'],
                   {j:a['shift_minutes'] for j,a in amap.items() if a['shift_minutes']},
                   {j:a['to_tail'] for j,a in amap.items() if a['action']=='SWAP'})
    new=[j for o in v['option_ids'] for j in OPTIONS[o]['jobs']]
    return dict(KEEP=keep,WITHOUT_NEW=change,REPLACE=change+new)

def coverage_and_output(inputs,selected,nested):
    used_options={o for a in selected for v in a['variants'] for o in v['option_ids']}
    used_options|={o for p in nested['pairs'] for o in p['upper_variant']['option_ids']}
    programmes=[];catalog=[];actions=[];checks=[];legacyrefs={}
    for a in selected:
        variants=[export_variant(v) for v in a['variants']]
        programmes.append(dict(id=a['id'],financial_template_key=a['financial_key'],variants=variants,selection_sources=sorted(a['stages'])))
        for vi,v in enumerate(variants):
            vid=a['id']+'/V'+str(vi+1);c=COHORTS[v['cohort']];states=states_for(v)
            for cid in v['legacy_programme_ids']:legacyrefs[cid]=dict(programme_id=a['id'],variant_index=vi)
            for jid,action in v['action_map'].items():
                actions.append(dict(programme_id=a['id'],variant=vi+1,cohort=v['cohort'],old_stable_id=jid,**action,
                    KEEP='RETAIN',WITHOUT_NEW=action['action'],REPLACE=action['action'],
                    cancellation_shared_W_R=True,cancellation_cost=None,old_profit=None,uncovered_own_shift=None))
            for state,jobs in states.items():
                ck=check_calendar(jobs,c['positions'],full=True)
                assert ck['hard_pass'],(vid,state,ck)
                checks.append(dict(programme_id=a['id'],variant=vi+1,cohort=v['cohort'],state=state,
                    hard_pass=ck['hard_pass'],periodic_previous_next_week=True,flights_week=ck['flight_count'],
                    min_slack_turn60=ck['min_slack_after_turn'],max_UTC_day_BH=ck['max_UTC_day_BH'],
                    max_departure_local_day_BH=ck['max_departure_local_day_BH'],
                    BH8_diagnostic_exceeded=ck['BH8_diagnostic_exceeded'],crew_FDP_rest='UNKNOWN',
                    actual_entry_release='UNKNOWN',actual_initial_ready='UNKNOWN',slot_MRO_payload='UNKNOWN'))
            fs=legs([j for o in v['option_ids'] for j in OPTIONS[o]['jobs']]);ops=[OPTIONS[o] for o in v['option_ids']]
            pairs=sorted({pair(f['origin'],f['destination']) for f in fs})
            for pp in pairs:PAIR_STATS[pp]['selected_variants']+=1
            catalog.append(dict(programme_id=a['id'],variant=vi+1,cohort=v['cohort'],
                working_tails=len(c['positions']),reserve_separate='R1_NONWORKING',
                paths=len(ops),new_working_tails=len({o['tail'] for o in ops}),
                source_path_ids=';'.join(o['path_id'] for o in ops),families=';'.join(sorted({o['topology_class'] for o in ops})),
                frequencies_week=';'.join(str(len(o['iso_weekdays'])) for o in ops),
                physical_pairs=';'.join(pairs),action_family=afamily(v),
                old_removed=sum(x['action']=='REMOVE' for x in v['action_map'].values()),
                old_shifted=sum(x['action']=='SHIFT' for x in v['action_map'].values()),
                old_transferred=sum(x['action']=='SWAP' for x in v['action_map'].values()),
                paid_ferry_legs=sum(f['kind']=='PAID_FERRY' for f in fs),
                legacy_programmes=';'.join(v['legacy_programme_ids']),
                main='DIRECT_ONLY_JOINT_PENDING',actual_profit=None,financial_rank='NOT_COMPUTED'))
    assert len(legacyrefs)==60
    # Keep every positive evidence row, with periods intact and bounded alias
    # key. Cross-airport conflicting clocks remain separate alternatives.
    evidence=[dict(service_id=r['service_id'],pair=r['pair'],origin=r['origin'],destination=r['destination'],
        flight=r['flight'],operator=r['carrier_operated'],valid_start=r['valid_start'],valid_end=r['valid_end'],
        covered_dates=r['covered_dates'],days_mon0=r['days_mon0'],departure_local=r['departure_local'],
        arrival_local=r['arrival_local'],arr_day_offset=r['arr_day_offset'],source_id=r['source_id'],
        source_locator=r['source_locator'],year_basis=r['year_basis'],status=r['status'],
        physical_pattern_dedup_hint=key([r['origin'],r['destination'],r['flight'],r['valid_start'],r['valid_end'],
                                        r['days_mon0'],r['departure_local'],r['arrival_local']]),
        admission='SUPPLY_ONLY_PERIOD_LIMITED; not OD/not actual tail availability') for r in inputs['services']]
    specs=dict(schema='P38_WEEKLY_PROGRAMMES_1',reference_monday_codec='2027-02-01T00:00:00+00:00',
        reference_is_operating_period=False,repeat='ISO weekly scenario; actual dated service positive only inside source periods',
        timezone_policy='UTC minute codec + local IANA; instantiate against actual Monday dates; no reset at boundaries',
        timezones=ZONES,turn_minutes=60,resources=COHORTS,paths={p:PATHS[p] for p in PATHS},
        chain_options={o:OPTIONS[o] for o in sorted(used_options)},programmes=programmes,legacy_programme_references=legacyrefs,
        master_old_obligations=COHORTS['K2']['old_jobs'],nested_allocations=nested,
        supply_evidence=evidence,
        period_gates=dict(WZ5030='CONFLICT_GOJ_SVX_PUBLIC_CLOCKS; KEEP retains verified P36 scenario, not convenient new primary clock',
            TOF='Tomsk; TOX is Tobolsk and not in this universe',
            own_RW_TOF_GOJ='positive constraints retained; include actual dated own inventory when supplied; no zero-own default',
            SJ='S0 existing RRJ only; SJ/PD8 future operator entry/cost UNKNOWN, never use RRJ economics as fact'),
        gates=dict(actual_tail_release=None,crew_rest_FDP=None,slots=None,MRO_capacity_release=None,payload_actual=None,
            initial_ready_actual=None,opportunity_D=None,station_overnight_reserve_launch_F=None,
            existing_lease_avoidable=False,fixed_crew_avoidable=False,reserve_R1_price=None,
            support_incremental_revenue_main=0,cargo_incremental_revenue_main=0,block_contract_revenue_main=0,
            ferry_revenue=0,fullPnL=None,cash=None),
        financial_helper=dict(primary='DIRECT_ONLY',monthly_engine_called=False,actual_rubles=None,
            state_order=['KEEP','WITHOUT_NEW','REPLACE'],state_rule='same old action_map in WITHOUT_NEW and REPLACE; append new jobs once',
            joint_rule='allocate all retained/new physical inventory once per dated flight, shared directed city OD/month, DME/ZIA share MOW; endpoint tariff once',
            product_pool_key='city(origin)>city(destination)/YYYY-MM',
            flight_instance_key='flight_id@actual_reference_Monday',capacity_key='dated physical flight_id',
            accounting='UTC departure month; full flight cost once, crossing flight context retained',
            cancellation_rule='C common W/R; C versus KEEP or different action maps explicit; not part of pure new margin',
            own_loss_rule='modelled own transfer inside joint delta; only uncovered external own sales remain symbolic',
            monthly_adapter='../contract/month_adapter.py: evaluate_month(states,tails,year,month,scenario); only next-stage caller',
            cache_rule='use full dated events, resources/initial ready, actions, OD/profile/response/cost/tax/source hashes; financial class is NOT proof/cache for calendar/through'),
        future_stress_spec=dict(delays_minutes=[30,60,120],turn_minutes=[60,90],
            perturb='each new leg and adjacent retained old departure; cascade on same tail across next day/week/month',
            current_scope='specification only; not repeated294test suite; actual latest slot/crew thresholds UNKNOWN'))
    dump('programme_specs.json',specs)
    table('programme_catalog.csv',catalog)
    table('old_assignment_actions.csv',actions)
    table('calendar_checks.csv',checks)
    rejected=[dict(stage=s,reason=r,count=n,example=REJECT_EXAMPLES[s,r]) for (s,r),n in sorted(REJECT.items())]
    table('rejections.csv',rejected,['stage','reason','count','example'])
    seedcoverage=[]
    selectedpairs={p for r in catalog for p in r['physical_pairs'].split(';')}
    for r in inputs['seed']:
        p=r['pair'];found=[x['programme_id'] for x in catalog if p in x['physical_pairs'].split(';')]
        market=next(x for x in inputs['marketpairs'] if x['pair']==p)
        seedcoverage.append(dict(pair=p,selected_financial_templates=len(set(found)),representatives=sorted(set(found))[:5],
            prior_programme_ids=r['programmes'].split(';'),reason='EXACT_LEGACY_AND_BOUNDED_WEEKLY_COVERED' if found else 'NOT_SELECTED_CAP420; remains in legacy reference and bounded registry',
            prior_top5=r['prior_top5'],own_RW_status=market['own_rw_nonstop'],
            market_reason=market['reason']))
    coverage=dict(search='deterministic discrete single expansion + diverse same-tail/fleet beam; not full combinatorial optimization',
        limits=LIMITS,counts=dict(sorted(COUNTS.items())),search_axes=dict(ISO_start_days=list(range(1,8)),
            local_windows=list(WINDOWS),frequencies=list(FREQUENCIES),frequency_offsets={str(k):list(v) for k,v in DAY_OFFSETS.items()},
            old_shifts=list(SHIFTS),working_tails=[1,2,3],max_different_closed_paths_per_tail=2,
            reserve='R1 separate, nonworking'),
        input_counts=dict(P36_parameter_paths=103,P36_registry_paths=len(inputs['registry']),additional_required_paths=len(PATHS)-103,
            legacy_programmes=60,legacy_positive_new=37,seed_pairs=25,service_evidence_rows=130),
        output_counts=dict(financial_templates=len(programmes),calendar_variants=len(catalog),state_calendar_checks=len(checks),
            chain_options=len(used_options),nested_pairs=len(nested['pairs'])),
        seed_pair_coverage=seedcoverage,
        path_coverage=[dict(path_id=p,path='-'.join(PATHS[p]['path']),family=PATHS[p]['family'],
            topology_class=path_class(PATHS[p]),**PATH_STATS[p]) for p in sorted(PATHS)],
        not_searched=['P36 registry paths outside103 except fixed14 required controls; no new city universe',
            'all 2-path combinations of every frequency/time/rotation; same-tail beam28 and fixed recipes only',
            'more than2 distinct new closed paths per working tail or >3 working tails',
            'all independent per-job shift vectors; common signed shift of whole conflicting set only',
            'arbitrary donor deletion unrelated to new closure, arbitrary multi-job swaps beyond transfer and8pairs',
            'reuse old jobs inside long new job base-return gaps; whole closed-job occupancy reserved',
            'unrestricted assignment of every retained old job to every tail or all fleet pack combinations',
            'joint monthly economics, annual portfolio optimum, actual sales/dispatch, new SJ economics',
            'extra delay suite; future stress specifications only'],
        bound_policy='P36 old optimistic cautious capacity bounds exported only; not used to claim actual profit or hard economic pruning. Physical pruning + state equivalence + fixed beam limits.',
        selection_policy='all60 exact legacy references + deterministic round-robin cohort/mode/topology/action; no scalar cross-baseline revenue ranking',
        financial_equivalence='directed local-day/physical-airport/tail/kind inventory + path grouping + overnight quantities + exact old actions; calendars checked individually. Through/time utility requires exact cache.',
        marginal_resource_rule=nested,
        missing_requested_files=['P38TASK.md not found in repository/scratch; user task text used',
                                  'P36/pass2/source_manifest.json absent; completed input_manifest.json used'],
        no_other_agent_outputs_read=True,no_old_exporters_called=True,monthly_engine_called=False)
    dump('search_coverage.json',coverage)
    # A small 3-resource witness set, not420x3xmonths.
    write_representatives(selected)
    return specs,coverage

def write_representatives(selected):
    rows=[]
    for sid in ('K1','K2','K3'):
        eligible=[a for a in selected if a['variants'][0]['cohort']==sid and len(a['variants'][0]['option_ids'])>=2]
        if not eligible:continue
        a=max(eligible,key=lambda x:(len({OPTIONS[o]['tail'] for o in x['variants'][0]['option_ids']}),
                                    len(x['variants'][0]['option_ids']),-priority(x['variants'][0])[0],x['id']))
        v=export_variant(a['variants'][0])
        for state,jobs in states_for(v).items():
            for f in sorted(legs(jobs),key=lambda f:(f['tail'],f['dep'],f['flight_id'])):
                rows.append(dict(programme_id=a['id'],cohort=sid,state=state,tail=f['tail'],flight_id=f['flight_id'],
                    origin=f['origin'],destination=f['destination'],departure_UTC_codec=(REF+timedelta(minutes=f['dep'])).isoformat(),
                    arrival_UTC_codec=(REF+timedelta(minutes=f['arr'])).isoformat(),departure_local_codec=loc(f['dep'],f['origin']).isoformat(),
                    arrival_local_codec=loc(f['arr'],f['destination']).isoformat(),origin_IANA=ZONES[f['origin']],destination_IANA=ZONES[f['destination']],
                    block_minutes=f['block'],kind=f['kind'],seats=f['seats'],ferry_revenue=0 if f['kind']=='PAID_FERRY' else 'JOINT_PENDING',
                    actual_period='UNKNOWN_SCENARIO_CODEC_ONLY'))
    table('representative_calendars.csv',rows)

def main():
    inputs=load_inputs()
    single_search()
    mixed_search()
    selected=select_templates()
    nested=nested_pairs(selected)
    specs,coverage=coverage_and_output(inputs,selected,nested)
    write_docs(specs,coverage)
    protectedbad=[p for p,h in inputs['protected'].items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
    completebad=[p for p,h in inputs['completed'].items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
    assert not protectedbad and not completebad,(protectedbad,completebad)
    dump('input_manifest.json',dict(schema='P38_WEEKLY_INPUT_MANIFEST_1',read_sources=READS,
        protected1621=inputs['protected'],completed_P36_P37=inputs['completed'],
        protected_changed=[],completed_changed=[],contract_completed_steer='user13Nov2026; engine_handoff/resource_contract/month_adapter read after COMPLETE',
        excluded='orchestrator mutable metadata, other live/new foreign outputs, git refs audit',
        old_builders_or_verifiers_called=False,monthly_income_called=False,subagents=False,network=False,
        write_scope=str(HERE.relative_to(ROOT)),bytecode_disabled=True))
    print(serial(dict(status='GENERATED',templates=len(specs['programmes']),legacy=len(specs['legacy_programme_references']),
                      counts=coverage['output_counts'],attempts=coverage['counts'])))

def write_docs(specs,cov):
    counts=cov['output_counts'];attempt=cov['counts']
    catalogue=list(csv.DictReader((HERE/'programme_catalog.csv').open()))
    resources=Counter(r['cohort'] for r in catalogue)
    modes=Counter((r['cohort'],int(r['paths']),int(r['new_working_tails'])) for r in catalogue)
    head=f"""# P38 weekly programmes — completed bounded generation

Созданы **{counts['financial_templates']} недублирующихся direct-only финансовых классов**, {counts['calendar_variants']} проверенных календарных вариантов и {counts['state_calendar_checks']} полных проверок KEEP / WITHOUT_NEW / REPLACE. Все60 legacy-программ /37 positive воспроизведены из completed P36 ledger, включая исходные alias; все25 seed-пар имеют представителей и адресную причину покрытия. Это weekly specs и физические условные сценарии, **не финансовый рейтинг, не месячный доход и не разрешение запуска**.

Основной контракт после completed steer: K1 = B2/T1 с11 old jobs; K2 =15 old RT на T1/T2; K3 = тот же K2 + условный RRJ T3, D3 UNKNOWN. R1 отдельный один нерабочий резерв. Ранний prototype T2/4KUF не используется как K1. Старые B1/DME/ZIA сохранены отдельно только для точного покрытия legacy; их итоги нельзя ранжировать против K1/K2/K3 скалярной выручкой.

Перебор:103 time-expanded пути P36 +14 фиксированных pass2 controls, тот же16-airport universe. ISO1–7, local06/10/14/20, frequency1/2/3/5/7, все7 циклических offsets P36, с устранением одинаковых7/week rotations. Реально {attempt['single_new_checks']:,} назначенных single-config calendars и {attempt['single_action_attempts']:,} попыток old actions. Mixed: {attempt['same_tail_new_checks']:,} same-tail beam attempts, {attempt['focused_mix_new_checks']:,} фиксированных overlays и {attempt['fleet_mix_new_checks']:,} fleet extensions. Полная комбинаторная оптимизация не заявляется; точные caps/counts/NOT searched в search_coverage.json. На хвост до2 paths, на3 хвоста до6; ограниченный beam сохраняет рабочие различия календаря.

Базовые операции: вставка в условный idle window, общие shifts конфликтующих whole old jobs ±30/60/120/180; remove1/2/3, минимальная closure / all-affected, физически передаваемые whole jobs и до8 pair swaps. Минимальный removal-set — объединение конфликтов всех новых paths, по stable ID один раз. Extra donor removals ради красивого TOTAL не добавляются. Каждая смесь проверяется заново совместно, состояния не суммируются.

Физика: UTC/local IANA, направленные блоки P36, position/overlap/turn60, полный недельный цикл со следующим/предыдущим повтором; ночь вне базы не сбрасывает хвост. Кодек Monday2027-02-01 не означает продажи/исполнение этого периода. Actual initial position/ready/release остаются UNKNOWN; календарный anchor явный условный. UTC8BH/day и departure-local-day8BH — только диагностика, не FDP и не crew-rest approval. Crew/slots/MRO/payload остаются gates. Новые канонические DME/ZIA пути начинаются из SVX с оплачиваемыми замкнутыми ferry0sales; отдельные legacy Moscow требуют conditional physical RRJ, не B777/Ту.

Все130 admitted service evidence rows сохранены с именованными периодами и dedup hints; это не130 независимых рейсов/частот. RW TOF/GOJ не обнулены; TOF=Томск, TOX не используется. December positive не продлён на February. WZ5030 public GOJ/SVX clocks конфликтуют: исходный проверенный P36 KEEP scenario оставлен, conflict gate экспортирован. Published schedule не доказывает actual tail availability/endpoint OD/newness.

Примерные текущие варианты по ресурсам: {dict(resources)}. Все семейства RT, обе ориентации triangle, truecycles4–6 и CONCAT_RT различаются. Некоторые проверки имеют8BH diagnostic exceedance; они физически допустимые comparators, не legal shifts. Pilot2each witness по GOJ–KJA сохраняется отдельно от исходного1RT control; никакой спрос этим не доказан.

Рубли/месячный P06/old income не вычислялись. Все F/D/crew/lease/reserve/overnight/launch/fullPnL/cash UNKNOWN; fixed lease/salary не избегаемы. Support/cargo/block MAIN0 до договора; это не0 для неизвестных затрат. Общий C у W/R сокращается в R−W, C против KEEP и разных removal sets остаётся символическим. Own transfers внутри joint allocation не вычитать повторно.

Для marginalnexttail экспортированы {counts['nested_pairs']} реальных paired K2→K3 allocations с одинаковым master15 old universe и одинаковой old action map. D3/fixed/R1 difference UNKNOWN, value=NULL. K1→K2: canonical K1 исключает4 T2 obligations, а fixed master15 KEEP на1 хвост не помещается; core constraint явно передан следующему engine. Требуется вложенная оптимизация одинаковых15 обязательств с явными remove/move/C/D; raw K2−K1 запрещён.

Запись только programmes/, без субагентов, контактов, Git mutation, панели, поиска источников, old builders/verify или вызова monthly income. P38TASK.md не найден; ТЗ из сообщения пользователя. P36/pass2/source_manifest.json отсутствует: использован completed input_manifest.json. Contract прочитан только после completed steer. Завершённые hash guards:1621 protected + completed P36/pass1/pass2 и P37/calculation + конкретные прочитанные источники; mutable orchestrator/new foreign output не guard.

Проверка: существующий context/28_end_to_end_audit_20261110/code/sandbox/venv/bin/python -B context/38_direct_strategy_20261113/programmes/verify.py. validation.json содержит фактический результат fixtures, независимую проверку3 недель всех вариантов,27 Jan/Feb/Jul calendar-only receipts для1/2/3 рабочих хвостов и byte-identical repeat. Pass не означает dispatch/actual economics.

Выходы: programme_specs.json (основной компактный API), programme_catalog.csv, old_assignment_actions.csv, calendar_checks.csv, search_coverage.json, rejections.csv, generate.py, verify.py, validation.json, input_manifest.json, representative_calendars.csv и engine_handoff.md. Completed handoff; STOP.
"""
    (HERE/'README.md').write_text(head)
    handoff=f"""# Weekly engine handoff — completed

Принимать programme_specs.json schema P38_WEEKLY_PROGRAMMES_1 и catalogue. В нём {counts['financial_templates']} financial classes / {counts['calendar_variants']} календарных вариантов, legacy reference map всех60 и130 периодных supply evidence rows. Финальный месячный assembler выбирает несколько вариантов только после совместной аллокации; **не суммировать solo margins и не называть этот shortlist optimum**. Canonical primary cohort K1=11 T1 oldjobs, K2=15 B2, K3=same15+T3(D3UNKNOWN).

## Как восстановить состояния

resources[cohort].old_jobs задаёт точный KEEP bank. Для каждого programme.variants[]:
1. Применить action_map один раз по old stable ID: REMOVE исключает, SHIFT переносит все dep/arr job на shift_minutes, SWAP меняет tail всего job. RETAIN оставляет.
2. Это WITHOUT_NEW. Для REPLACE добавить chain_options[option_ids].jobs ровно один раз. Старые jobs и их изменения у W/R тождественны.
3. Генерировать ISO recurrence на реальных Monday dates с предыдущими/следующими repetitions, не range(4) и не ready0. Минуты dep/arr относятся к условному Monday UTC codec; могут быть <0/>10080. Локальные дни/блоки/overnight уже закодированы, IANA в timezones.
4. Dated key = flight_id@actual_Monday. Физическая capacity одна; SERVICE100 scenario seats, PAID_FERRY0 seats/revenue, расходы не удалять.
5. Передавать states/tails следующему joint engine; contract/month_adapter.py: evaluate_month — существующий адрес API, здесь он НЕ вызывался. Verify использует только calendar_events.

Catalogue показывает3states physical checks отдельно от8BH. calendar_checks — {counts['state_calendar_checks']} циклических proofs; representative_calendars — только3 witnesses, без всех шаблонов×месяцы. Начальная periodic position/ready может включать IN_AIR на UTC boundary; actual ready/release UNKNOWN. Type existing RRJ only. SJ/PD8 future entry не получает RRJ economics.

## Joint financial seam

Primary DIRECT_ONLY. Строить все retained/new directed products совместно: один cityOD/month pool, DME/ZIA физически разные и в choice один MOW. Endpoint tariffonce, shared leg seats once; through только отдельный явно условный rerun по полному calendar. Известное own RW TOF/GOJ не равно0: supply_evidence сохраняет positive periods, но не доказывает полный замкнутый KEEP на actual tail. Неполные clock/return/period inventory закрывать условным gate, не выдуманной ротацией.

Для каждого cohort/menu общий world/OD/profile/response/cost/tax definition во всех K/W/R. R−W = new incremental after joint own recapture; W−K = oldchanges; R−K = total. Общий cancellationC W/R не входит в newmargin; при разных change sets он различается. Донор/own shift, уже представленный retained/removed product delta, второй раз не вычитать. Непокрытая external own/interline loss остаётся UNKNOWN. F/D/newcrew/overnight/parking/R1/launch не0. All actual rubles/fullPnL/cash=NULL.

financial_template_key — bounded direct-only equivalence: directed physical airport/tail/kind/local weekday inventory, grouped closed path topology, actual overnight quantities, exact old action map, один cohort. Для каждого calendar variant отдельная физическая проверка. Этот key НЕ использовать как календарный или through cache. Полный cache включает timestamps/ready/resources/actions/initial positions/cost/tax/OD/profile/response/source hashes.

## Следующий хвост и pilot product

nested_allocations содержит {counts['nested_pairs']} paired K2→K3 plans: master15 identical; lower ID и upper exact variant, same old action map, explicit C rule и UNKNOWN outsideD/fixed/R1 differences. Это реальные allocations, не оптимальные рубли. Требуется jointoptimum(k+1)−jointoptimum(k) в общем мире после differential resource costs.

K1→K2 core_constraint: master15 содержит4 T2 obligations вне canonical K1; фиксированные часы15 на1tail конфликтуют. Нужен самостоятельный nested lower allocation со всеми обязательствами и явными remove/retime/C/D; от raw primary cohort totals marginal value не получать. Ни одно значение marginalvalue здесь не придумано.

Проверенный mixed witness включает обе ориентации GOJ–KJA по2 commercial departures/direction/week; single1RT controls сохранены. Дальнейший pilot budget/q/net/exit/slots/crew — задача общего engine по контракту, никакой рекомендации запуска здесь нет.

## Границы поиска и проверки

search_coverage.json — exactattempts,117 source path records (103 P36 +14 required), все25 seed reasons, fixed caps, physical rejection counts и честный NOTsearched. Beam28 options/tail,14 packs/tail(6single+8mixed),40 fleet states с квотой по числу paths, максимум2 paths/tail. Focused overlays пробуют second local10/20, 7rotations и2discrete offsets. Minimalclosure union строится по всей смеси; донорское удаление oldjob не дублируется.

P36 optimistic bounds только подписанный старый scenario context; экономического pruning по фактическим рублям нет. Слабые рынки сохранены как family controls и не навязываются портфелю. Необходимые futurefinalist specs: delay30/60/120 и turn90 с carryover;294 прежних tests не повторялись. Crew/rest/FDP/slot/MRO/payload/PD8 permission actualUNKNOWN.

Sourceguard: input_manifest.json фиксирует1621protected, completedP36/P37 и readinput hashes. Не guard mutablemetadata и новые чужие outputs. verify.py реально проверяет all60/180states, allvariants3states, old uniqueness, 1/2/3+R1, real localUTC durations, weekwrap/overlap/turn, no phantom/ferry sales, UNKNOWN, reverse/truecycle/concat, financialeq≠calendarproof, nestedconstraints,27datedcalendar receipts и deterministic byte repeat. Проверять validation.json; семантика actual external market/release этим не доказывается.

Completed handoff, запись только programmes/. STOP, без ожидания других агентов.
"""
    (HERE/'engine_handoff.md').write_text(handoff)

if __name__=='__main__':main()
