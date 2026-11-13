"""P38 economics kernel. Pure reads of completed sources; no old entry points.

Direct markets factor exactly because each retail journey uses one physical leg.
Within an airport/block/new-price class flights are symmetric. Aggregation is
checked against the pinned P06 allocator in verify.py. Through bypasses this
factorisation. No patches of imported modules and no threads are used.
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
from collections import Counter, defaultdict, OrderedDict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P38 = HERE.parent
P36 = ROOT / 'context/36_overnight_chain_search_20261112'
STATES = ('KEEP', 'WITHOUT_NEW', 'REPLACE')
UTC = timezone.utc

def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def js(path):
    return json.loads(Path(path).read_text())

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

M = load('p38_economics_completed_adapter', P38/'contract/month_adapter.py')
RE = M.engine()

def guard():
    reg = js(P38/'protected_files.json')
    imm = {p:h for p,h in reg.items() if not any(t in p.lower() for t in ('delegation','tasklog','task_log'))}
    changed = [p for p,h in imm.items() if sha(ROOT/p) != h]
    if changed:
        raise ValueError('PROTECTED_SOURCE_CHANGED:'+str(changed[:6]))
    return dict(registered=len(reg), immutable=len(imm), excluded_mutable=len(reg)-len(imm), digest=digest(imm))

def semantic_jobs(jobs, retain_ids=False):
    return sorted([(j['id'] if retain_ids else '', j['tail'],
        tuple((f['origin'],f['destination'],float(f['dep']),float(f['arr']),float(f['block']),f['kind'])
              for f in sorted(j['flights'],key=lambda f:f['dep']))) for j in jobs])

def semantic_flights(flights):
    return digest(sorted((f['tail'], f['origin'], f['destination'], f['departure_utc'],
        f['arrival_utc'], f['kind']) for f in flights))

def old(jobs):
    return [j for j in jobs if not j['id'].startswith('NEW-')]

def new(jobs):
    return [j for j in jobs if j['id'].startswith('NEW-')]

@lru_cache(None)
def programme_input():
    config=js(HERE/'config.json')
    if not config.get('completed_programme_gate'):return None
    z=js(P38/'programmes/programme_specs.json')
    if z['schema']!='P38_WEEKLY_PROGRAMMES_1':raise ValueError('unrecognised completed programme schema')
    return z

def restore_variant(v,spec):
    keep=copy.deepcopy(spec['resources'][v['cohort']]['old_jobs'])
    if set(v['action_map'])!={j['id'] for j in keep}:raise ValueError('incomplete old action map')
    changed=[]
    for j in keep:
        action=v['action_map'][j['id']]
        if action['action']=='REMOVE':continue
        q=copy.deepcopy(j);q['tail']=action['to_tail']
        for f in q['flights']:
            f['tail']=q['tail'];f['dep']+=action['shift_minutes'];f['arr']+=action['shift_minutes']
        changed.append(q)
    nn=[copy.deepcopy(j) for oid in v['option_ids'] for j in spec['chain_options'][oid]['jobs']]
    if len({j['id'] for j in changed+nn})!=len(changed+nn):raise ValueError('duplicate merged job')
    return dict(KEEP=keep,WITHOUT_NEW=changed,REPLACE=changed+nn)

@lru_cache(None)
def templates():
    out = {}
    primary = {k:semantic_jobs(M.cohort(k)['jobs'],True) for k in (1,2,3)}
    for r in read(P38/'contract/programme_inventory.csv'):
        cid = r['candidate_id']
        states = {s:M.p36_weekly(cid,s) for s in STATES}
        tails = M.resources(M.candidate_positions(cid))
        key = digest(dict(tails=tails, keep=semantic_jobs(states['KEEP'],True)))[:16]
        k = sum(not t.get('reserve') for t in tails)
        label = 'K2' if k==2 and semantic_jobs(states['KEEP'],True)==primary[2] else 'LEGACY_'+r['setup']
        out[cid] = dict(id=cid, states=states, tails=tails, cohort_key=key,
            cohort=label, source=r, scope='COMPLETED_P36_TEMPLATE_NOT_MIXED_WEEKLY_SEARCH')
    spec=programme_input()
    if spec:
        for p in spec['programmes']:
            for idx,v in enumerate(p['variants']):
                states=restore_variant(v,spec);tails=M.resources(v['initial_positions'])
                if v['legacy_programme_ids']:
                    for cid in v['legacy_programme_ids']:
                        for state in STATES:
                            if semantic_jobs(out[cid]['states'][state],True)!=semantic_jobs(states[state],True):
                                raise ValueError('legacy spec differs from completed adapter:'+cid+'/'+state)
                    continue
                cid=p['id']+'/V'+str(idx)
                paths=[]
                for oid in v['option_ids']:
                    op=spec['chain_options'][oid];ff=op['jobs'][0]['flights']
                    paths.append('-'.join([ff[0]['origin']]+[f['destination'] for f in ff]))
                out[cid]=dict(id=cid,states=states,tails=tails,
                    cohort_key=digest(dict(tails=tails,keep=semantic_jobs(states['KEEP'],True)))[:16],
                    cohort=v['cohort'],source=dict(path=' + '.join(paths),setup=v['cohort'],
                        physical_pairs=';'.join(sorted({'-'.join(sorted((f['origin'],f['destination']))) for j in new(states['REPLACE']) for f in j['flights']})),
                        source='completed programme_specs.json#'+p['id']+'/variants/'+str(idx)),
                    scope='COMPLETED_MIXED_WEEKLY_VARIANT',variant=v,financial_class=p['financial_template_key'])
    return out

@lru_cache(None)
def world():
    # The universe is fixed BEFORE evaluating any candidate or scenario.
    # All city pairs among admitted nodes include conditional through endpoints
    # too; unused pools have outside choices only and cancel identically.
    nodes = sorted({RE.city(f['origin']) for t in templates().values()
        for jobs in t['states'].values() for j in jobs for f in j['flights']} |
        {RE.city(f['destination']) for t in templates().values()
        for jobs in t['states'].values() for j in jobs for f in j['flights']})
    return tuple((a,b) for a in nodes for b in nodes if a!=b)

WORLD_HASH = lambda: digest(world())

@lru_cache(None)
def variable(a,b,block,scenario,incidence=1.0):
    c = dict(RE.costs(a,b,scenario,block/60))
    rate = float(RE.COSTS['HIST-crew_rub_per_hour']['base_point' if scenario=='base' else 'cautious_point'])
    fixed_crew = c['block_hours_costscreen']*rate
    deice = 15000 if scenario=='base' else 40000
    c['fixed_crew_excluded'] = fixed_crew
    c['deice_allowance'] = incidence*deice
    c['other_cost'] -= fixed_crew+(1-incidence)*deice
    c['fixed_cost'] = c['fuel_cost']+c['other_cost']
    return c

def potential(a,b,year,month,scenario,split=.5,weak=False):
    q,src,via = RE.annual(a,b,scenario,year)
    if q is None:
        raise ValueError('NO_ADMITTED_PRIOR:'+a+'>'+b)
    fraction = split if a<b else 1-split
    value = q*RE.P05.monthly_profile(year)[month]*fraction/.6
    if weak and not {'SVX','MOW'} & {a,b}:
        value *= .5
    return value

def convert(cal,tails):
    tm = {t['id']:t for t in tails}
    return [dict(flight_instance_id=f['flight_id'],pattern_id=f['rotation_id'],
        origin_airport=f['origin'],destination_airport=f['destination'],
        departure_utc=f['departure_utc'],arrival_utc=f['arrival_utc'],
        saleable_seats=tm[f['tail']].get('saleable_seats',100) if f['kind']=='service' else 0,
        block_hours_costscreen=f['block_minutes']/60,calendar_kind=f['kind'],tail_id=f['tail'],
        physical_adjacent_leg=True,source_status=f['evidence'],aircraft_variant=tm[f['tail']]['type'])
        for f in cal['flights']]

def direct_groups(fs,scenario,days,fare_scale=1.0):
    """Preserve choice_bundle's per-physical-airport frequency and intercept.

    A group is identical legs only. New and retained flights remain separate so
    internal diversion is measured and new-fare stresses do not reprice KEEP.
    """
    byphysical = defaultdict(list)
    for f in fs:
        if f['saleable_seats'] and f['calendar_kind']=='service':
            byphysical[f['origin_airport'],f['destination_airport']].append(f)
    out = defaultdict(list)
    for (a,b),ff in sorted(byphysical.items()):
        n = len(ff); freq = n*7/days
        h = sum(f['block_hours_costscreen'] for f in ff)/n
        gross,net = RE.fare(a,b,scenario)
        total_weight = RE.mass(a,b,freq,scenario,gross,h*60)
        c = RE.P05.coefficients(scenario)
        sub = defaultdict(list)
        for f in ff:
            sub[f['block_hours_costscreen'], f['pattern_id'].startswith('NEW-'), f['saleable_seats']].append(f)
        for (bh,isnew,seats),gg in sorted(sub.items()):
            scale = fare_scale if isnew else 1
            weight = total_weight*len(gg)/n*math.exp(c['time_per_minute']*(bh-h)*60+
                c['price_per_rub']*gross*(scale-1))
            out[RE.city(a),RE.city(b)].append(dict(a=a,b=b,block=bh*60,n=len(gg),
                new=isnew,seats=seats,capacity=len(gg)*seats,weight=weight,
                gross=gross*scale,net=net*scale,freq=freq,
                flight_ids=[f['flight_instance_id'] for f in gg]))
    return dict(out)

def outside(a,b,scenario,response='passive'):
    if response=='price_match10_capacity25':
        # Outside air is an uncapacitated composite, not invented dated seats.
        # Explicit +25% weekly frequency utility, no factual capacity forecast.
        return .4+(RE.outside_mass(a,b,scenario,'price_match10')-.4)*1.25**RE.P05.coefficients(scenario)['log_frequency']
    return RE.outside_mass(a,b,scenario,response)

def kernel(groups,pot,outside_weight):
    """Exact direct-only constrained logit / P06 simultaneous recapture.

    Solve potential = outside_weight*lambda + sum min(capacity_i,weight_i*lambda).
    Symmetric legs in a class each receive group carried/n. All weights >0.
    """
    if pot<0 or outside_weight<=0:
        raise ValueError('invalid demand/outside mass')
    saturated=0.; active=sum(g['weight'] for g in groups)
    lam=0.
    for g in sorted(groups,key=lambda g:g['capacity']/g['weight']):
        lam=(pot-saturated)/(outside_weight+active)
        if lam<=g['capacity']/g['weight']+1e-12:
            break
        saturated+=g['capacity'];active-=g['weight']
    else:
        lam=(pot-saturated)/outside_weight
    qs=[min(g['capacity'],max(0.,g['weight']*lam)) for g in groups]
    rev=sum(q*g['net'] for q,g in zip(qs,groups))
    return dict(revenue=rev,journeys=sum(qs),q=qs,
        new_revenue=sum(q*g['net'] for q,g in zip(qs,groups) if g['new']),
        new_journeys=sum(q for q,g in zip(qs,groups) if g['new']),
        retained_revenue=sum(q*g['net'] for q,g in zip(qs,groups) if not g['new']),
        retained_journeys=sum(q for q,g in zip(qs,groups) if not g['new']),
        outside=pot-sum(qs))

def knots(groups,ow):
    return sorted({0.} | {ow*(g['capacity']/g['weight'])+
        sum(min(h['capacity'],h['weight']*g['capacity']/g['weight']) for h in groups) for g in groups})

class MarketMap(dict):
    def __init__(self,groups,year,month,scenario,split,weak,response,overrides):
        super().__init__();self.context=(year,month,scenario,split,weak,response,overrides or {})
        for key,gg in groups.items():self[key]=self.make(key,gg)
    def make(self,key,gg):
        year,month,scenario,split,weak,response,overrides=self.context
        a,b=key;pot=overrides.get(key,potential(a,b,year,month,scenario,split,weak));ow=outside(a,b,scenario,response)
        return dict(kernel(gg,pot,ow),potential=pot,groups=gg,outside_weight=ow)
    def __missing__(self,key):
        # All fixed-world outside-only pools exist conceptually. They have no
        # RW revenue/capacity and are represented lazily, never duplicated.
        if key not in world():raise KeyError(key)
        return self.make(key,[])

def score_calendar(cal,tails,year,month,scenario,split=.5,weak=False,
                   response='passive',fare_scale=1.,incidence=1.,overrides=None):
    fs=convert(cal,tails)
    groups=direct_groups(fs,scenario,calendar.monthrange(year,month)[1],fare_scale)
    markets=MarketMap(groups,year,month,scenario,split,weak,response,overrides)
    cost=sum(variable(f['origin'],f['destination'],f['block_minutes'],scenario,incidence)['fixed_cost'] for f in cal['flights'])
    rev=sum(z['revenue'] for z in markets.values())
    return dict(subtotal=rev-cost,net_revenue=rev,variable_cost=cost,
        journeys=sum(z['journeys'] for z in markets.values()),
        new_revenue=sum(z['new_revenue'] for z in markets.values()),
        new_journeys=sum(z['new_journeys'] for z in markets.values()),
        retained_revenue=sum(z['retained_revenue'] for z in markets.values()),
        retained_journeys=sum(z['retained_journeys'] for z in markets.values()),
        departures=len(fs),new_departures=sum(f['pattern_id'].startswith('NEW-') for f in fs),
        ferry_departures=sum(f['saleable_seats']==0 for f in fs),
        BH=sum(f['block_hours_costscreen'] for f in fs),
        max_daily_BH=max([d['block_hours'] for d in cal['daily']] or [0]),
        BH8_diagnostics=len(cal['errors']),markets=markets,
        semantic=semantic_flights(cal['flights']),cal=cal,flights=fs)

class Score(dict):
    def __init__(self,z,engine,jobs,tails,month,turn):
        super().__init__({k:v for k,v in z.items() if k not in ('cal','flights')})
        self.context=(engine,jobs,tails,month,turn)
    def __missing__(self,key):
        engine,jobs,tails,month,turn=self.context
        if key=='cal':return engine.calendar(jobs,tails,month,turn)
        if key=='flights':return convert(engine.calendar(jobs,tails,month,turn),tails)
        raise KeyError(key)

class Engine:
    def __init__(self,source_hash):
        self.source_hash=source_hash
        self.cal_cache=OrderedDict();self.score_cache={};self.calls=Counter()

    def calendar(self,jobs,tails,month,turn=60):
        # Full input key: no candidate-only cache, no cross-cohort optimum.
        key=digest(dict(jobs=jobs,tails=tails,year=2027,month=month,turn=turn,
            source=self.source_hash,world=WORLD_HASH()))
        if key not in self.cal_cache:
            self.cal_cache[key]=M.calendar_events(jobs,tails,2027,month,turn)
            self.calls['calendar']+=1
            if len(self.cal_cache)>128:self.cal_cache.popitem(last=False)
        else:self.cal_cache.move_to_end(key)
        return self.cal_cache[key]

    def score(self,jobs,tails,month,scenario,**kw):
        if any(t['type'].startswith('SJ') for t in tails):
            raise ValueError('SJ_PD8_COST_UNKNOWN_RESOURCE_ENVELOPE_ONLY')
        turn=kw.pop('turn',60)
        options=dict(kw)
        if 'overrides' in options:
            if any(not isinstance(k,tuple) or k not in world() for k in options['overrides']):
                raise ValueError('demand overrides need admitted directed city tuple keys')
            options['overrides']=sorted((list(k),v) for k,v in options['overrides'].items())
        key=digest(dict(jobs=jobs,tails=tails,month=month,turn=turn,scenario=scenario,options=options,
            source=self.source_hash,world=WORLD_HASH()))
        if key not in self.score_cache:
            cal=self.calendar(jobs,tails,month,turn)
            self.score_cache[key]=Score(score_calendar(cal,tails,2027,month,scenario,**kw),self,jobs,tails,month,turn)
            self.calls['joint_direct_factored']+=1
        return self.score_cache[key]

def native_menus():
    out=defaultdict(list)
    seen=defaultdict(set)
    for cid,t in templates().items():
        for state,jobs in t['states'].items():
            sem=digest(semantic_jobs(jobs))
            if sem not in seen[t['cohort_key']]:
                seen[t['cohort_key']].add(sem)
                out[t['cohort_key']].append(dict(candidate=cid,state=state,jobs=jobs,tails=t['tails']))
    # Embed EVERY lower K2 alternative in K3 with T3 idle. This preserves the
    # lower feasible set for all months/scenarios, not just one pruned leader.
    bycohort={t['cohort']:t for t in templates().values()}
    if 'K3' in bycohort:
        k2,k3=bycohort['K2'],bycohort['K3']
        for item in list(out[k2['cohort_key']]):
            sem=digest(semantic_jobs(item['jobs']))
            if sem not in seen[k3['cohort_key']]:
                seen[k3['cohort_key']].add(sem)
                out[k3['cohort_key']].append(dict(item,candidate='IDLE_T3:'+item['candidate'],tails=k3['tails']))
    return dict(out)

def inverse_direction(target,alternatives,key):
    """Exact piecewise-linear inverse within a fixed DIRECT-only menu.

    Only ONE directed city pool changes, identically in every alternative.
    All other pools remain at their declared baseline. No all-OD 'q95'.
    Semantic duplicates of target have already been excluded by the caller.
    """
    market=target['markets'][key];gg=market['groups'];ow=market['outside_weight']
    base=market['potential']
    ts=target['subtotal']-market['revenue']
    aa=[(z['subtotal']-z['markets'][key]['revenue'],z['markets'][key]['groups'],label)
        for label,z in alternatives]
    def value(q,groups):return kernel(groups,q,ow)['revenue']
    def margin(q):
        best=max((fixed+value(q,g),label) for fixed,g,label in aa)
        return ts+value(q,gg)-best[0],best[1]
    points=sorted(set(knots(gg,ow)+[x for _,g,_ in aa for x in knots(g,ow)]))
    found=None
    for lo,hi in zip(points,points[1:]+[math.inf]):
        # Each state is affine between the UNION of all capacity knots.
        x0=lo; x1=(lo+hi)/2 if math.isfinite(hi) else lo+max(1.,base)
        tv0=ts+value(x0,gg);tv1=ts+value(x1,gg)
        lower=lo;upper=hi;possible=True
        for fixed,g,label in aa:
            d0=tv0-fixed-value(x0,g)
            d1=tv1-fixed-value(x1,g)
            slope=(d1-d0)/(x1-x0) if x1>x0 else 0
            if abs(slope)<1e-10:
                if d0<=1e-7:possible=False;break
            else:
                root=x0-d0/slope
                if slope>0:lower=max(lower,root)
                else:upper=min(upper,root)
        if possible and upper>lower+1e-7:
            probe=lower+max(1e-5,abs(lower)*1e-8)
            if probe<upper and margin(probe)[0]>1e-7:
                found=(max(0.,lower),upper);break
    atbase,best=margin(base)
    out=dict(prior_potential=base,baseline_margin=atbase,best_alternative=best,
        method='EXACT_DIRECT_POOL_PIECEWISE_FINITE_MENU',global_optimum=False,
        other_OD_fixed=True,capacity_intervals=len(points))
    if found is None:
        return out|dict(status='NO_OD_WIN_ANY_POTENTIAL_WITHIN_THIS_MENU',required_potential=None,
            required_scale=None,required_change_fraction=None,integer_potential=None,threshold_margin=None)
    q,upper=found
    n=0 if q==0 and margin(0)[0]>1e-7 else math.floor(q)+1
    if n>=upper or margin(n)[0]<=1e-7:
        n=None
    return out|dict(status='DIRECTED_OD_WINNING_INTERVAL',required_potential=q,
        winning_interval_upper=None if not math.isfinite(upper) else upper,
        required_scale=q/base if base else None,required_change_fraction=q/base-1 if base else None,
        integer_potential=n,threshold_margin=margin(n)[0] if n is not None else None,
        q_at_threshold=kernel(gg,q,ow)['journeys'])

def inverse_net(target,alternatives,key):
    # Realised net-yield change is independent of retail gross here. This is a
    # settlement threshold, not a retail pricing experiment or automatic VAT.
    t=target['markets'][key]['revenue'];tf=target['subtotal']-t
    lower=0.;upper=math.inf
    for _,z in alternatives:
        a=z['markets'][key]['revenue'];af=z['subtotal']-a
        slope=t-a;intercept=tf-af
        if abs(slope)<1e-8:
            if intercept<=1e-7:return dict(net_status='NO_COMMON_NET_ONLY_WIN',net_multiplier_equality=None)
        elif slope>0:lower=max(lower,-intercept/slope)
        else:upper=min(upper,-intercept/slope)
    if upper<=lower+1e-9:return dict(net_status='NO_COMMON_NET_ONLY_WIN',net_multiplier_equality=None)
    return dict(net_status='COMMON_REALIZED_NET_WINNING_INTERVAL',net_multiplier_equality=max(0.,lower),
        net_multiplier_upper=None if math.isinf(upper) else upper,
        net_basis='target directed city pool in ALL alternatives; gross/choice fixed; not automatic tax bridge')

def inverse_poolset(target,alternatives,keys):
    """Exact bounded-menu portfolio OD inverse; explicit target markets only."""
    keys=sorted(set(keys))
    if not keys:return dict(status='NO_NEW_COMMERCIAL_POOL',required_scale=None,target_markets=[])
    states=[target]+[z for _,z in alternatives]
    priors={key:target['markets'][key]['potential'] for key in keys}
    fixed=[z['subtotal']-sum(z['markets'][key]['revenue'] for key in keys) for z in states]
    def value(idx,scale):
        return fixed[idx]+sum(kernel(states[idx]['markets'][key]['groups'],priors[key]*scale,
            states[idx]['markets'][key]['outside_weight'])['revenue'] for key in keys)
    points=sorted({0.}|{q/priors[key] for z in states for key in keys if priors[key]>0
        for q in knots(z['markets'][key]['groups'],z['markets'][key]['outside_weight'])})
    for lo,hi in zip(points,points[1:]+[math.inf]):
        mid=(lo+hi)/2 if math.isfinite(hi) else lo+1
        lower,upper=lo,hi;possible=True
        for idx in range(1,len(states)):
            d0=value(0,lo)-value(idx,lo);d1=value(0,mid)-value(idx,mid)
            slope=(d1-d0)/(mid-lo)
            if abs(slope)<1e-8:
                if d0<=1e-7:possible=False;break
            elif slope>0:lower=max(lower,lo-d0/slope)
            else:upper=min(upper,lo-d0/slope)
        if possible and upper>lower+1e-8:
            return dict(status='EXACT_TARGET_SET_OD_INTERVAL',required_scale=max(0.,lower),
                upper_scale=None if math.isinf(upper) else upper,target_markets=[a+'>'+b for a,b in keys],
                baseline_directed_potentials={a+'>'+b:v for (a,b),v in priors.items()},
                other_OD_fixed=True,comparison='same candidate KEEP/WITHOUT_NEW, before differential C/D/F')
    return dict(status='NO_PORTFOLIO_OD_WIN_IN_THIS_MENU',required_scale=None,target_markets=[a+'>'+b for a,b in keys],other_OD_fixed=True)

def full_p06(cal,tails,month,scenario,through=False,day_case=None,response='passive',fare_scale=1.,split=.5,weak=False):
    """Reference full physical inventory; through consumes both legs once."""
    fs=convert(cal,tails);service=[f for f in fs if f['saleable_seats']>0]
    start,end=M.bounds(2027,month);endday=(end-timedelta(days=1)).date().isoformat()
    overrides={f'{a}>{b}/2027-{month:02}':potential(a,b,2027,month,scenario,split,weak) for a,b in world()}
    react='price_match10' if response=='price_match10_capacity25' else response
    bun=RE.choice_bundle(service,scenario,set(world()),start.date().isoformat(),endday,overrides,react)
    bun['flights']=fs
    if response=='price_match10_capacity25':
        delta=RE.P05.coefficients(scenario)['log_frequency']*math.log(1.25)
        for p in bun['products']:
            if p['product_id'].endswith(':other_air'):p['intercept']+=delta
    if through:
        markets={m['demand_pool_id']:m for m in bun['markets']}
        paths=defaultdict(list)
        # Include only supported monthly-departure legs. Cross-month through
        # supply is not silently invented; that additional space is disclosed.
        for f in service:
            for g in service:
                gap=(M.dt(g['departure_utc'])-M.dt(f['arrival_utc'])).total_seconds()/60
                if f['tail_id']==g['tail_id'] and f['destination_airport']==g['origin_airport'] and 60<=gap<=240:
                    a,b=RE.city(f['origin_airport']),RE.city(g['destination_airport'])
                    if a!=b:paths[a,b].append((f,g))
        for (a,b),pp in sorted(paths.items()):
            freq=len(pp)*7/calendar.monthrange(2027,month)[1]
            gross,net=RE.fare(a,b,scenario)
            ds=[(M.dt(g['arrival_utc'])-M.dt(f['departure_utc'])).total_seconds()/60 for f,g in pp]
            duration=sum(ds)/len(ds);c=RE.P05.coefficients(scenario)
            weight=RE.mass(a,b,freq,scenario,gross,duration)
            intercept=math.log(weight/len(pp))+c['stop_penalty']-c['price_per_rub']*gross-c['time_per_minute']*duration-c['log_frequency']*math.log(freq)
            for (f,g),dur in zip(pp,ds):
                bun['products'].append(RE.P05.product('THROUGH:'+f['flight_instance_id']+'+'+g['flight_instance_id'],
                    markets[RE.P05.pool(a,b)],'air','RW',gross,dur,freq,
                    [f['flight_instance_id'],g['flight_instance_id']],f['departure_utc'][:10],net,intercept))
    fby={f['flight_instance_id']:f for f in fs}
    for p in bun['products']:
        if p['owner']=='RW' and any(fby[x]['pattern_id'].startswith('NEW-') for x in p['legs']):
            p['gross_fare']*=fare_scale;p['net_fare']*=fare_scale
    if day_case:
        nm=[];np=[]
        active={p['demand_pool_id'] for p in bun['products'] if p['owner']=='RW'}
        # Outside-only pools are independent and have exactly zero RW economics;
        # keep their fixed-world definition lazy rather than expand 31 copies.
        bun['markets']=[m for m in bun['markets'] if m['demand_pool_id'] in active]
        bun['products']=[p for p in bun['products'] if p['demand_pool_id'] in active]
        daylist=[(start+timedelta(days=i)).date().isoformat() for i in range((end-start).days)]
        weights={d:(1.5 if (day_case=='JAN_PEAK' and int(d[-2:])<=10) or
            (day_case=='SUMMER_PEAK' and datetime.fromisoformat(d).weekday()>=4) else .5) for d in daylist}
        for m in bun['markets']:
            for day,value in M.pool_days(m['potential_journeys'],2027,month,weights).items():
                nm.append(dict(m,customer_segment='requested_date:'+day,potential_journeys=value))
        for p in bun['products']:
            days=[fby[p['legs'][0]]['departure_utc'][:10]] if p['owner']=='RW' else daylist
            for day in days:
                np.append(dict(p,product_id=p['product_id']+':'+day,customer_segment='requested_date:'+day))
        bun['markets'],bun['products']=nm,np
    alloc=RE.allocate_p06(bun,bun['products'])
    products={p['product_id']:p for p in bun['products']}
    rev=sum(a['carried']*products[a['product_id']]['net_fare'] for a in alloc['allocations'] if a['owner']=='RW')
    return dict(revenue=rev,journeys=sum(a['carried'] for a in alloc['allocations'] if a['owner']=='RW'),
        through_products=sum(len(p['legs'])>1 for p in bun['products']),bundle=bun,allocation=alloc)

def recolor_closed(jobs,k):
    """Allocate existing complete SVX jobs, preserving times and all legs.

    This does not generate routes, frequencies or retimings. A first-fit failure
    is only a failure of this bounded allocation; it is not a proof over all
    possible clock changes. No hidden background or reserve work is permitted.
    """
    available=[-1e15]*k;out=[]
    for j in sorted(jobs,key=lambda j:min(f['dep'] for f in j['flights'])):
        ff=sorted(j['flights'],key=lambda f:f['dep'])
        if ff[0]['origin']!='SVX' or ff[-1]['destination']!='SVX':return None
        options=[i for i in range(k) if available[i]<=ff[0]['dep']+1e-9]
        if not options:return None
        idx=min(options,key=lambda i:available[i]);available[idx]=ff[-1]['arr']+60
        q=copy.deepcopy(j);q['tail']=f'T{idx+1}'
        for f in q['flights']:f['tail']=q['tail']
        out.append(q)
    return out

def annual_calendar(policies,tails,turn=60,pre_policy=None,post_policy=None):
    """Stitch full jobs by their FIRST departure month, including carry/wrap.

    Supply 1..12 policies. The same December/January pattern is used for the
    adjacent years to check an explicitly periodic year-wrap envelope. Actual
    starting/return state outside these operations remains UNKNOWN.
    """
    first=datetime(2026,12,1,tzinfo=UTC)
    first-=timedelta(days=first.weekday())
    last=datetime(2028,2,1,tzinfo=UTC)
    alljobs={}
    for jobs in list(policies.values())+([pre_policy] if pre_policy is not None else [])+([post_policy] if post_policy is not None else []):
        for j in jobs:
            sig=digest(j)
            alljobs[sig]=j
    selected_signatures={m:{digest(x) for x in jobs} for m,jobs in policies.items()}
    pre_signatures={digest(x) for x in pre_policy} if pre_policy is not None else None
    post_signatures={digest(x) for x in post_policy} if post_policy is not None else None
    events=[];monday=first
    while monday<last:
        for sig,j in alljobs.items():
            begin=monday+timedelta(minutes=min(f['dep'] for f in j['flights']))
            selected=pre_signatures if begin.year<2027 and pre_signatures is not None else post_signatures if begin.year>2027 and post_signatures is not None else selected_signatures[begin.month]
            if sig not in selected:continue
            for f in j['flights']:
                dep=monday+timedelta(minutes=f['dep']);arr=monday+timedelta(minutes=f['arr'])
                events.append(dict(flight_id=f['flight_id']+'@'+monday.date().isoformat(),
                    rotation_id=j['id']+'@'+monday.date().isoformat(),template_id=f['flight_id'],
                    tail=f['tail'],origin=f['origin'],destination=f['destination'],
                    departure_utc=dep.isoformat(),arrival_utc=arr.isoformat(),block_minutes=f['block'],
                    kind='positioning' if f['kind']=='PAID_FERRY' else 'service',
                    evidence=f.get('evidence','P36 conditional recurrence'),job_first_departure_utc=begin.isoformat()))
        monday+=timedelta(days=7)
    conflicts=[];carry={}
    ids=Counter(f['flight_id'] for f in events)
    for fid,n in ids.items():
        if n>1:conflicts.append(dict(flight=fid,duplicate_count=n,disposition='DUPLICATE_OLD_JOB_OCCURRENCE_AT_POLICY_SEAM_NO_RESET'))
    for t in tails:
        seq=sorted([f for f in events if f['tail']==t['id']],key=lambda f:f['departure_utc'])
        pos=t['initial_location'];ready=None;previous=None
        for f in seq:
            dep=M.dt(f['departure_utc']);arr=M.dt(f['arrival_utc'])
            if dep<datetime(2028,1,1,tzinfo=UTC) and arr>=datetime(2027,1,1,tzinfo=UTC) and (
                    dep<M.dt(t['available_from']) or arr>M.dt(t['available_to'])):
                conflicts.append(dict(tail=t['id'],flight=f['flight_id'],disposition='OUTSIDE_DATED_RESOURCE_AVAILABILITY'))
            if pos!=f['origin'] or ready is not None and dep<ready:
                conflicts.append(dict(tail=t['id'],flight=f['flight_id'],previous=previous,
                    position=pos,required_origin=f['origin'],ready_utc=ready.isoformat() if ready else None,
                    departure_utc=f['departure_utc'],bridge_cost=None,disposition='SELECT_ANOTHER_POLICY_OR_PRICE_BRIDGE_NO_RESET'))
            pos=f['destination'];ready=arr+timedelta(minutes=turn);previous=f['flight_id']
        for cut in [datetime(2027,m,1,tzinfo=UTC) for m in range(1,13)]+[datetime(2028,1,1,tzinfo=UTC)]:
            prior=[f for f in seq if M.dt(f['departure_utc'])<cut]
            f=prior[-1] if prior else None
            carry[t['id']+'/'+cut.date().isoformat()]=dict(position=(('IN_AIR:'+f['origin']+'>'+f['destination'])
                if M.dt(f['arrival_utc'])>cut else f['destination']) if f else t['initial_location'],
                ready_utc=(M.dt(f['arrival_utc'])+timedelta(minutes=turn)).isoformat() if f else None)
    cals={}
    for m in range(1,13):
        start,end=M.bounds(2027,m);daily=Counter()
        for f in events:
            cursor=max(start,M.dt(f['departure_utc']));finish=min(end,M.dt(f['arrival_utc']))
            while cursor<finish:
                edge=min(finish,datetime.combine(cursor.date()+timedelta(days=1),datetime.min.time(),UTC))
                daily[f['tail'],cursor.date().isoformat()]+=(edge-cursor).total_seconds()/3600;cursor=edge
        dr=[dict(tail=t,date=d,block_hours=h) for (t,d),h in sorted(daily.items())]
        cals[m]=dict(flights=[f for f in events if start<=M.dt(f['departure_utc'])<end],daily=dr,
            errors=[str(d) for d in dr if d['block_hours']>8+1e-9],carry=carry,
            boundary_flights=[f for f in events if M.dt(f['departure_utc'])<start<M.dt(f['arrival_utc'])])
    return dict(status='STITCH_CONFLICT' if conflicts else 'PERIODIC_YEAR_STITCH_PASS_CONDITIONAL',
        calendars=cals,conflicts=conflicts,carry=carry,events=events,
        actual_entry_return_state=None,bridge_cost=None if conflicts else 'not required in checked periodic fixture')
