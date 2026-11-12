#!/usr/bin/env python3
"""P36 bounded second pass. Read-only completed imports; writes only HERE.

Exact dated events -> P31 evaluate_combined_programme -> pinned P06.allocate.
No network, legacy builders, git mutation, dispatch approval or actual PnL.
"""
import sys
sys.dont_write_bytecode = True
import copy
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
P1 = STUDY/'pass1'
START, END = '2027-02-01', '2027-02-28'
EPOCH = datetime(2027, 2, 1, tzinfo=timezone.utc)
WEEK = 10080
READS = {}
CALLS = Counter()

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    p = Path(p)
    if not p.is_relative_to(HERE):
        READS[str(p.relative_to(ROOT))] = sha(p)
    return list(csv.DictReader(p.open(encoding='utf-8-sig', newline='')))

def jsread(p):
    p = Path(p)
    if not p.is_relative_to(HERE):
        READS[str(p.relative_to(ROOT))] = sha(p)
    return json.loads(p.read_text())

def dump(n, x):
    assert Path(n).name == n
    (HERE/n).write_text(json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n')

def table(n, rows, fields=None):
    assert Path(n).name == n
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    assert fields
    with (HERE/n).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: 'NULL' if v is None else round(v, 7) if isinstance(v, float) else v for k, v in r.items()})

def load(name, p):
    READS[str(p.relative_to(ROOT))] = sha(p)
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

G = load('p36_pass1_readonly', P1/'generate.py')
P34 = load('p36_p34_readonly', ROOT/'context/34_new_direct_top5_20261112/calculation/calculate.py')
RE = P34.RE
G.RE, G.P34 = RE, P34
G.ANCHORS = read(P1/'inputs/svx_primary.csv')
G.UNIVERSE = {r['pair_id']: r for r in read(RE.HERE/'route_universe.csv')}
# build_baselines is pure except its two table exports: suppress those exports.
G.table = lambda *args, **kwargs: None
SETUPS = G.build_baselines()
ZONES = G.ZONES
ORIG_COST = RE.costs
ORIG_CHOICE = RE.choice_bundle
ORIG_CAL = RE.OPS_CALENDAR.generate
NODES = tuple(G.NODES)

def iso(t):
    return (EPOCH+timedelta(minutes=t)).isoformat()

def local(t, a):
    return (EPOCH+timedelta(minutes=t)).astimezone(ZoneInfo(ZONES[a])).isoformat()

def directions(jobs, through=True):
    fs = list(G.flatten(jobs))
    out = {(RE.city(f['origin']), RE.city(f['destination'])) for f in fs if f['kind'] != 'PAID_FERRY'}
    if through:
        for f, g in connections(fs):
            out.add((RE.city(f['origin']), RE.city(g['destination'])))
    return out | {(b, a) for a, b in out}

def connections(fs):
    """Conditional offered two-leg throughs, same tail, 60..240min connection.

    No free extra aircraft, no ferry sales, no fictitious roundtrip journey.
    Endpoint fare once, both physical capacities once. Product offering is an
    explicit scenario, not evidence of actual RW connecting sales/contracts.
    """
    out = []
    for f in fs:
        if f.get('kind', f.get('calendar_kind')) in ('PAID_FERRY', 'positioning'):
            continue
        for g in fs:
            if g.get('kind', g.get('calendar_kind')) in ('PAID_FERRY', 'positioning'):
                continue
            a = f.get('origin', f.get('origin_airport'))
            b = f.get('destination', f.get('destination_airport'))
            c = g.get('origin', g.get('origin_airport'))
            d = g.get('destination', g.get('destination_airport'))
            if 'dep' in f:
                gap = g['dep']-f['arr']; same = f['tail'] == g['tail']
            else:
                gap = (datetime.fromisoformat(g['departure_utc'])-datetime.fromisoformat(f['arrival_utc'])).total_seconds()/60
                same = f['tail_id'] == g['tail_id']
            if same and b == c and RE.city(a) != RE.city(d) and 60 <= gap <= 240:
                out.append((f, g))
    return out

def event_calendar(req):
    """Verified exact-event adapter for P31's calendar_requests seam.

    Original P03 cannot encode overnight and independent retiming of dated
    legs. Never fabricate pattern clocks or drop an infeasible leg. Validate
    exact positions, turn, horizon and per-tail UTC-day BH; 8BH only a queue.
    """
    jobs = req['exact_jobs']
    errors, bh = G.physics(jobs, req['positions'])
    if errors:
        raise ValueError(('HARD_CALENDAR', errors))
    fs = list(G.flatten(jobs))
    for tail,initial in req['positions'].items():
        pos=initial;ready=0
        for f in sorted([f for f in fs if f['tail']==tail],key=lambda f:(f['dep'],f['flight_id'])):
            if (f['origin']!=pos or f['dep']<ready or f['block']<=0 or
                abs(f['arr']-f['dep']-f['block'])>1e-9 or f['dep']<0 or f['arr']>28*1440 or
                f['origin']=='MOW' or f['destination']=='MOW' or RE.city(f['origin'])==RE.city(f['destination'])):
                raise ValueError(('EXACT_FLIGHT_POSITION_TURN_BLOCK_HORIZON',f['flight_id']))
            pos=f['destination'];ready=f['arr']+60
        if pos!=initial:raise ValueError(('MONTH_END_POSITION',tail,pos,initial))
    daily = Counter()
    for f in fs:
        cursor = f['dep']
        while cursor < f['arr']:
            d = math.floor(cursor/1440); e = min(f['arr'], (d+1)*1440)
            daily[f['tail'], d] += e-cursor; cursor = e
    flights = [dict(flight_id=f['flight_id'], rotation_id=f['job_id'], tail=f['tail'],
                    origin=f['origin'], destination=f['destination'], departure_utc=iso(f['dep']),
                    arrival_utc=iso(f['arr']), block_minutes=f['block'],
                    kind='positioning' if f['kind'] == 'PAID_FERRY' else 'service', evidence=f['evidence']) for f in fs]
    dr = [dict(tail=t, date=(EPOCH+timedelta(days=d)).date().isoformat(), block_hours=v/60) for (t,d),v in sorted(daily.items())]
    errs = [r['tail']+'/'+r['date']+':SCENARIO_8BH_SCREEN_EXCEEDED_NOT_CREW_LAW' for r in dr if r['block_hours'] > 8+1e-9]
    return dict(status='COST_ONLY_8BH_QUEUE' if errs else 'CONDITIONAL_EXACT_EVENTS_NOT_DISPATCH',
                errors=errs, flights=flights, daily=dr, rotations=[], reserve=['R1_UNRELEASED'], max_bh=bh)

def request(jobs, setup):
    return dict(tails=[dict(id=t, type='RRJ-95B', initial_location=a, saleable_seats=100,
                           available_from=START+'T00:00:00+00:00', available_to='2027-03-01T00:00:00+00:00', reserve=False)
                      for t,a in setup['positions'].items()]+[dict(id='R1_UNRELEASED', type='RRJ-95B', reserve=True, initial_location='UNKNOWN')],
                blocks=[], patterns=[], exact_jobs=jobs, positions=setup['positions'],
                block_case='nominal', turn_minutes=60, diagnostic_bh_day=8)

def variable_cost(a, b, sc, hours=None, fuel_scale=1):
    c = dict(ORIG_COST(a, b, sc, hours))
    h = c['block_hours_costscreen']
    rate = float(RE.COSTS['HIST-crew_rub_per_hour']['base_point' if sc == 'base' else 'cautious_point'])
    c['fixed_crew_excluded'] = h*rate
    c['other_cost'] -= c['fixed_crew_excluded']
    c['fuel_price'] *= fuel_scale
    c['fuel_cost'] = c['fuel_t']*c['fuel_price']
    c['fixed_cost'] = c['other_cost']+c['fuel_cost']
    return c

def make_choice(flights, sc, affected, start, end, demand_overrides=None, response='passive',
                world=None, through=True, fare_scale=1, demand_scale=1, direction_split=.5,
                day_stress=None, weak_adjacent=False):
    assert (start,end) == (START,END)
    assert 0 <= direction_split <= 1
    bun = ORIG_CHOICE(flights, sc, world or affected, start, end, demand_overrides, response)
    # One pool per directed city OD/month. Throughs reuse precisely that pool.
    markets = {m['demand_pool_id']: m for m in bun['markets']}
    fby = {f['flight_instance_id']: f for f in flights}
    if through:
        groups = defaultdict(list)
        for f,g in connections(flights):
            groups[RE.city(f['origin_airport']), RE.city(g['destination_airport'])].append((f,g))
        for (a,b), paths in sorted(groups.items()):
            market = markets[RE.P05.pool(a,b)]
            freq = len(paths)/4
            gross, net = RE.fare(a,b,sc)
            durations = [(datetime.fromisoformat(g['arrival_utc'])-datetime.fromisoformat(f['departure_utc'])).total_seconds()/60 for f,g in paths]
            duration = sum(durations)/len(durations)
            weight = RE.mass(a,b,freq,sc,gross,duration)
            cf = RE.P05.coefficients(sc)
            intercept = math.log(weight/len(paths))+cf['stop_penalty']-cf['price_per_rub']*gross-cf['time_per_minute']*duration-cf['log_frequency']*math.log(freq)
            for (f,g),dur in zip(paths,durations):
                p = RE.P05.product('THROUGH:'+f['flight_instance_id']+'+'+g['flight_instance_id'], market,
                                   'air','RW',gross,dur,freq,[f['flight_instance_id'],g['flight_instance_id']],
                                   f['departure_utc'][:10], net, intercept)
                p['p36_through'] = True
                bun['products'].append(p)
    for m in bun['markets']:
        # annual() is symmetric; lexicographic direction gets the stated split.
        p = m['demand_pool_id'].removeprefix('CITY:').split('>')
        assert len(p) == 2
        fraction = direction_split if p[0] < p[1] else 1-direction_split
        m['potential_journeys'] *= demand_scale*fraction/.5
        if weak_adjacent and not any(x in p for x in ('SVX','MOW')):
            m['potential_journeys'] *= .5
    # Day stress allocates each monthly pool across all seven requested days;
    # products are available only on their departure weekday. Sum stays monthly.
    if day_stress is not None:
        weights = [1+day_stress*x for x in (-1,-1,0,0,0,1,1)]
        assert min(weights) > 0 and abs(sum(weights)-7) < 1e-9
        nm=[]; np=[]
        for m in bun['markets']:
            for dow,w in enumerate(weights):
                q=dict(m, customer_segment='requested_weekday_'+str(dow), potential_journeys=m['potential_journeys']*w/7)
                nm.append(q)
        for p in bun['products']:
            if p['owner']=='RW':
                dow = datetime.fromisoformat(fby[p['legs'][0]]['departure_utc']).astimezone(ZoneInfo(ZONES[fby[p['legs'][0]]['origin_airport']])).weekday()
                np.append(dict(p,customer_segment='requested_weekday_'+str(dow)))
            else:
                for dow in range(7):
                    np.append(dict(p,product_id=p['product_id']+':D'+str(dow),customer_segment='requested_weekday_'+str(dow)))
        bun['markets'],bun['products']=nm,np
    for p in bun['products']:
        if p['owner']=='RW' and any(fby[f]['pattern_id'].startswith('NEW-') for f in p['legs']):
            if fare_scale != 1:
                p['gross_fare'] *= fare_scale
                p['net_fare'] *= fare_scale
                # Intercept is held, so P06 recalculates price utility/capture.
    return bun

WORLDS = {}

def cohort_key(c):
    s=SETUPS[c['setup_id']]
    # B2S/T are same two-tail baseline, DME and ZIA physically separate.
    return s['cohort']+'|'+s['baseline']+'|'+json.dumps(s['positions'],sort_keys=True)+'|availability='+s['unknown']

def evaluate(c, sc='base', label='REPLACE', **sensitivity):
    setup=SETUPS[c['setup_id']]
    keep=setup['jobs']
    jobs=keep if label=='KEEP' else c['changed_old_jobs']+(c['new_jobs'] if label=='REPLACE' else [])
    reqs={'P':request(jobs,setup),'KEEP':request(keep,setup)}
    fuel_scale=sensitivity.pop('fuel_scale',1)
    def choice(*args,**kwargs):
        return make_choice(*args,**kwargs,world=WORLDS[cohort_key(c)],**sensitivity)
    RE.choice_bundle=choice
    RE.costs=lambda a,b,s,hours=None:variable_cost(a,b,s,hours,fuel_scale)
    RE.OPS_CALENDAR.generate=event_calendar
    try:
        z=RE.evaluate_combined_programme([],sc,keep_patterns=[],start=START,end=END,
                donor_loss=None,omitted_F=None,existing_slots=len(setup['positions']),delivery_scenario='S0',
                reserve_available=None,calendar_requests=reqs)
        assert 'programme' in z
        CALLS['P31_joint_calls']+=1
        return z['programme']
    finally:
        RE.choice_bundle=ORIG_CHOICE; RE.costs=ORIG_COST; RE.OPS_CALENDAR.generate=ORIG_CAL

def serial(x):
    return json.dumps(x,sort_keys=True,separators=(',',':'))

def old_choice_score(jobs,sc):
    """Exact old-only P06 choice seam for the existing thin removal sets.

    Not another calendar search/full programme producer: validate the known
    old inventory once, allocate its common pools including feasible throughs.
    Empty-own pools omitted here carry only outside choices and zero RW revenue.
    Only two resulting leaders enter the <=60 detailed candidate programmes.
    """
    cal=event_calendar(request(jobs,SETUPS['B2T']))
    flights=[dict(flight_instance_id=f['flight_id'],pattern_id=f['rotation_id'],origin_airport=f['origin'],
        destination_airport=f['destination'],departure_utc=f['departure_utc'],arrival_utc=f['arrival_utc'],
        saleable_seats=100 if f['kind']=='service' else 0,block_hours_costscreen=f['block_minutes']/60,
        calendar_kind=f['kind'],tail_id=f['tail']) for f in cal['flights']]
    world=directions(jobs)
    bun=make_choice(flights,sc,world,START,END,world=world)
    alloc=RE.allocate_p06(bun,bun['products']);CALLS['P06_existing_old_disposition_selection']+=1
    ps={p['product_id']:p for p in bun['products']}
    rev=sum(a['carried']*ps[a['product_id']]['net_fare'] for a in alloc['allocations'] if a['owner']=='RW')
    cost=sum(variable_cost(f['origin_airport'],f['destination_airport'],sc,f['block_hours_costscreen'])['fixed_cost'] for f in flights)
    return dict(net_revenue=rev,variable_cost=cost,known_subtotal=rev-cost)

def choose_candidates():
    # Required contract is read before selecting or calculating anything.
    for n in ['contracts.json','baseline_definitions.json','search_space.json','source_manifest.json']:
        jsread(P1/n)
    shortlist=read(P1/'shortlist.csv')
    candidates=jsread(P1/'shortlist_requests.json')
    for c in candidates.values(): c['selection']='PASS1_36_REPRESENTATIVES'
    configs={r['config_id']:r for r in read(P1/'schedule_configs.csv')}
    paths={r['path_id']:r for r in read(P1/'path_registry.csv')}
    actions={r['action_id']:r['action'] for r in read(P1/'action_ids.csv')}
    econ={(r['economic_id'],r['scenario']):r for r in read(P1/'economics_screen.csv')}
    # Eight targeted screens: each represented setup's economic leader plus
    # same-B2 4+ control. Existing shortlist is not an economic ranking.
    leaders={};remove_states={};reconstruct_seen=set()
    specs=[('B1I','ANY'),('B1S','ANY'),('B2S','ANY'),('B2T','ANY'),
           ('MDMEI','ANY'),('MZIAI','ANY'),('B2T','FOURPLUS'),('B2T','TRIANGLE')]
    for r in read(P1/'candidate_chains.csv'):
        if r['result'] in ('R005','R006') and r['setup'] in ('B2S','B2T') and int(r['removed'])>0:
            rid=(r['config'],r['setup'],r['action'])
            if rid not in reconstruct_seen:
                reconstruct_seen.add(rid)
                cfg=configs[r['config']];p=paths[cfg['path_id']];ss=SETUPS[r['setup']]
                nj=G.new_jobs(dict(path=p['path'].split('-'),overnight_after=int(p['overnight_after'])),
                    [int(d)-1 for d in cfg['iso_weekdays'].split(';')],int(cfg['departure_local'].split(':')[0]),ss['target'])
                changed,act=G.action_apply(actions[r['action']],ss,nj)
                if not act['error']:
                    signature=tuple(sorted(act['remove']))
                    remove_states.setdefault(signature,(r,changed,nj,act,p,cfg))
        if r['result']!='R005':continue
        cfg=configs[r['config']]; path=paths[cfg['path_id']]
        for setup,group in specs:
            if r['setup']!=setup:continue
            if group=='FOURPLUS' and int(path['legs'])<4:continue
            if group=='TRIANGLE' and path['family']!='TRIANGLE':continue
            score=float(econ[r['score'],'base']['subtotal'])
            k=setup,group
            if k not in leaders or (score,r['id'])>(leaders[k][0],leaders[k][1]['id']):leaders[k]=(score,r)
    for (sid,group),(score,r) in leaders.items():
        cfg=configs[r['config']]; p=paths[cfg['path_id']];setup=SETUPS[sid]
        path=dict(path=p['path'].split('-'),overnight_after=int(p['overnight_after']))
        days=[int(d)-1 for d in cfg['iso_weekdays'].split(';')]
        h=int(cfg['departure_local'].split(':')[0]);new=G.new_jobs(path,days,h,setup['target'])
        changed,act=G.action_apply(actions[r['action']],setup,new)
        assert not act['error']
        candidates.setdefault(r['id'],dict(setup_id=sid,changed_old_jobs=changed,new_jobs=new,
            candidate=dict(id=r['id'],setup=sid,action=actions[r['action']],act=act,path_id=cfg['path_id'],
                           family=p['family'],freq=int(cfg['frequency_per_week']),days=days,hour=h),
            selection='THIN_ECONOMIC_LEADER_'+sid+'_'+group))
    # Bounded exact pass includes direct-screen leaders of every distinct
    # removal set admitted by the existing registry, not just new-route leaders.
    # Only two selected old-disposition programmes get full evaluation.
    remove_selection=[];old_scores={};old_rows=[]
    for signature,(r,changed,nj,act,p,cfg) in sorted(remove_states.items()):
        for sc in ('base','cautious'):
            value=old_choice_score(changed,sc);old_scores[signature,sc]=value
            old_rows.append(dict(scenario=sc,source_candidate=r['id'],removed_old_ids=';'.join(signature),
                **value,scope='existing thin removal set only; exact dated P06 direct+conditional through; before actual C/D/F'))
    for sc in ('base','cautious'):
        signature,(r,changed,nj,act,p,cfg)=max(remove_states.items(),key=lambda kv:(old_scores[kv[0],sc]['known_subtotal'],kv[0]))
        cid=r['id'];remove_selection.append(dict(scenario=sc,candidate=cid,removed=';'.join(signature),screen=old_scores[signature,sc]['known_subtotal']))
        candidates.setdefault(cid,dict(setup_id=r['setup'],changed_old_jobs=changed,new_jobs=nj,
            candidate=dict(id=cid,setup=r['setup'],action=actions[r['action']],act=act,path_id=cfg['path_id'],
                family=p['family'],freq=int(cfg['frequency_per_week']),days=[int(d)-1 for d in cfg['iso_weekdays'].split(';')],hour=int(cfg['departure_local'].split(':')[0])),
            selection='THIN_WITHOUT_NEW_LEADER_'+sc))
    CALLS['thin_unique_old_removal_sets']=len(remove_states)
    table('without_new_screen_selection.csv',remove_selection)
    table('without_new_state_screen.csv',old_rows)
    custom=[('AER1',['SVX','AER','SVX'],[0],0),('AER2',['SVX','AER','SVX'],[0,3],0),
            ('AER_MRV',['SVX','AER','MRV','SVX'],[0],0),('MRV_AER',['SVX','MRV','AER','SVX'],[0],0),
            ('SVX_KJA',['SVX','KJA','SVX'],[0],0),('SVX_IKT',['SVX','IKT','SVX'],[0],1),
            ('GOJ_KJA_F',['SVX','GOJ','KJA','SVX'],[0],2),('GOJ_KJA_R',['SVX','KJA','GOJ','SVX'],[0],1),
            ('TJM_MRV_F',['SVX','TJM','MRV','SVX'],[0],0),('TJM_MRV_R',['SVX','MRV','TJM','SVX'],[0],0),
            ('CEK_MRV_F',['SVX','CEK','MRV','SVX'],[0],0),('CEK_MRV_R',['SVX','MRV','CEK','SVX'],[0],0),
            ('GOJ_TOF_F',['SVX','GOJ','TOF','SVX'],[0],2),('GOJ_TOF_R',['SVX','TOF','GOJ','SVX'],[0],1)]
    for name,path,days,after in custom:
        sid='B2T'; setup=SETUPS[sid];hour=20 if name in ('AER1','AER2') else 6
        new=G.new_jobs(dict(path=path,overnight_after=after),days,hour,setup['target'])
        # Remove exactly conflicts on target, never a profitable-looking extra donor.
        action='ALL_AFFECTED' if G.conflicts(setup['jobs'],new,setup['target']) else 'INSERT'
        changed,act=G.action_apply(action,setup,new)
        assert not act['error']
        candidates['X_'+name]=dict(setup_id=sid,changed_old_jobs=changed,new_jobs=new,
            candidate=dict(id='X_'+name,setup=sid,action=action,act=act,path_id='BOUNDED_REQUIRED_'+name,
                           family='RT' if len(path)==3 else 'TRIANGLE',freq=len(days),days=days,hour=hour),
            selection='MANDATORY_CLOSED_PATH_BOTH_ORIENTATIONS_WITH_PAID_FEEDERS',overnight_after=after)
    assert len(candidates)<=60
    return dict(sorted(candidates.items())),shortlist,leaders

def extraction(cid,sc,state,z):
    ps={p['product_id']:p for p in z['bundle']['products']}
    ff={f['flight_instance_id']:f for f in z['bundle']['flights']}
    sales=[];revby=Counter();qby=Counter();direct=Counter();through=Counter()
    for a in z['allocation']['allocations']:
        if a['owner']!='RW':continue
        p=ps[a['product_id']]
        sales.append(dict(candidate_id=cid,scenario=sc,state=state,product_id=a['product_id'],
            city_od=a['demand_pool_id'],departure_date=p['departure_date'],customer_segment=a['customer_segment'],
            product_kind='CONDITIONAL_THROUGH' if len(p['legs'])>1 else 'DIRECT',legs=';'.join(p['legs']),
            monthly_journeys=a['carried'],gross_fare=p['gross_fare'],net_fare=p['net_fare'],
            net_revenue=a['carried']*p['net_fare'],frequency_week=p['frequency'],
            status='MODEL_SCENARIO_NOT_OBSERVED',support=0,cargo=0))
        for fid,weight in zip(p['legs'],p['revenue_weights']):
            revby[fid]+=a['carried']*p['net_fare']*weight
            qby[fid]+=a['carried']
            (through if len(p['legs'])>1 else direct)[fid]+=a['carried']
    ledger=[]
    for fid,f in ff.items():
        cost=variable_cost(f['origin_airport'],f['destination_airport'],sc,f['block_hours_costscreen'])
        key='base_point' if sc=='base' else 'cautious_point';h=f['block_hours_costscreen']
        ledger.append(dict(candidate_id=cid,scenario=sc,state=state,flight_id=fid,job_id=f['pattern_id'],
            tail=f['tail_id'],origin=f['origin_airport'],destination=f['destination_airport'],departure_utc=f['departure_utc'],
            kind=f['calendar_kind'],seats=f['saleable_seats'],direct_q=direct[fid],through_segment_q=through[fid],total_segment_q=qby[fid],
            revenue_once_allocated=revby[fid],fuel_t=cost['fuel_t'],landed_fuel_rub_t=cost['fuel_price'],fuel=cost['fuel_cost'],
            variable_mro_scenario=h*float(RE.COSTS['HIST-mro_rub_per_hour'][key]),
            navigation_scenario=h*float(RE.COSTS['HIST-navigation_rub_per_hour'][key]),
            ground_cycle_scenario=96089 if sc=='base' else 115307,deice_scenario=15000 if sc=='base' else 40000,
            avoidable_variable_scenario=cost['fixed_cost'],fixed_crew_excluded=cost['fixed_crew_excluded'],
            known_subtotal=revby[fid]-cost['fixed_cost'],support=0,cargo=0,lease_avoided=0,
            actual_revenue=None,actual_avoidable_cost=None,fullPnL=None,cash=None))
    return sales,ledger

def main():
    protected=jsread(STUDY/'protected_files.json')
    assert len(protected)==1418 and all(sha(ROOT/p)==h for p,h in protected.items())
    # Completed admission: all positive rows survive; no_update is preservation.
    market={n:read(ROOT/'P36/market_recovery'/n) for n in ['canonical_market_pairs.csv','canonical_services.csv','unknown_fields.csv','source_admission.csv']}
    assert len([r for r in market['canonical_services.csv'] if r['service_id'].startswith('P34-')])==46
    for p in sorted((STUDY/'research_operations_cost').glob('*')):
        if p.is_file():READS[str(p.relative_to(ROOT))]=sha(p)
    for n in ['TASKS.md','market_recovery_admission.md','operations_cost_admission.md','source_pins.json']:
        READS[str((STUDY/n).relative_to(ROOT))]=sha(STUDY/n)
    candidates,shortlist,leaders=choose_candidates()
    for c in candidates.values():
        key=cohort_key(c);WORLDS.setdefault(key,set())
        for jobs in (SETUPS[c['setup_id']]['jobs'],c['changed_old_jobs'],c['changed_old_jobs']+c['new_jobs']):
            WORLDS[key].update(directions(jobs))
    cache={};results={};mapping=[];sales=[];ledger=[];three=[];cr=[]
    for cid,c in candidates.items():
        results[cid]={}
        setup=SETUPS[c['setup_id']]
        hard,bh=G.physics(c['changed_old_jobs']+c['new_jobs'],setup['positions'])
        assert not hard,(cid,hard)
        for sc in ('base','cautious'):
            results[cid][sc]={}
            for state in ('KEEP','WITHOUT_NEW','REPLACE'):
                jobs=setup['jobs'] if state=='KEEP' else c['changed_old_jobs']+(c['new_jobs'] if state=='REPLACE' else [])
                k=(cohort_key(c),sc,serial(jobs))
                if k not in cache:cache[k]=(cid,state,evaluate(c,sc,state))
                oc,os,z=cache[k];results[cid][sc][state]=z
                mapping.append(dict(candidate_id=cid,scenario=sc,state=state,equivalent_candidate=oc,equivalent_state=os))
                if (cid,state)==(oc,os):
                    ss,ll=extraction(cid,sc,state,z);sales+=ss;ledger+=ll
                three.append(dict(candidate_id=cid,cohort_key=cohort_key(c),scenario=sc,state=state,
                    equivalent_ledger_candidate=oc,equivalent_ledger_state=os,
                    working_tails=len(setup['positions']),tail_positions=serial(setup['positions']),seats_scenario=100,
                    flights_month=len(z['bundle']['flights']),rw_journeys=z['rw_journeys'],net_revenue=z['net_revenue'],
                    avoidable_variable_scenario=z['known_cost'],known_subtotal_before_C_D_F=z['known_contribution'],
                    cancellation_C=None if state!='KEEP' else 0,actual_outside_D=None,retiming_sales_loss=None,
                    own_external_marketed_shift=None,F_station_position_overnight_parking_reserve_launch=None,
                    fullPnL=None,cash=None))
            z=results[cid][sc];k,w,r=[z[x]['known_contribution'] for x in ('KEEP','WITHOUT_NEW','REPLACE')]
            new=[f for j in c['new_jobs'] for f in j['flights']]
            cr.append(dict(candidate_id=cid,selection=c['selection'],setup=c['setup_id'],cohort_key=cohort_key(c),
                scenario=sc,path='-'.join([new[0]['origin']]+[f['destination'] for f in c['new_jobs'][0]['flights']]),
                frequency_week=c['candidate']['freq'],action=c['candidate']['action'],
                affected_old_ids=';'.join(sorted(set(c['candidate']['act']['remove'])|set(c['candidate']['act']['swap'] or [])|({c['candidate']['act']['move'][0]} if c['candidate']['act']['move'] else set()))),
                old_change_minus_KEEP_before_C=w-k,new_minus_same_WITHOUT_NEW=r-w,
                REPLACE_minus_KEEP_before_C_D_F=r-k,KEEP=k,WITHOUT_NEW=w,REPLACE=r,
                max_daily_BH=bh,resource_queue='8BH_FAIL' if bh>8+1e-9 else '8BH_PASS_NOT_FDP',
                cautious_standalone_upper_bound=sum(100*(0 if f['kind']=='PAID_FERRY' else RE.fare(f['origin'],f['destination'],'cautious')[1])-variable_cost(f['origin'],f['destination'],'cautious',f['block']/60)['fixed_cost'] for f in new)*4,
                cancellation_C_threshold_same_without=w-k,unknown_outside_D=None,unknown_retiming=None,unknown_own_external_shift=None,unknown_F=None,
                fullPnL=None,cash=None,launch_status='NOT_PROVEN'))
    for r in cr:
        best=max(('KEEP','WITHOUT_NEW','REPLACE'),key=lambda st:r[st])
        r['known_preferred_same_disposition']=best
        r['actual_disposition']='UNKNOWN_PENDING_OLDPROFIT_C_D_F; NOT_LAUNCH'
        r['cancellation_common_to_without_replace']=True
    table('candidate_results.csv',cr);table('three_state_comparison.csv',three)
    table('equivalence_map.csv',mapping);table('directional_sales_ledger.csv',sales);table('revenue_cost_ledger.csv',ledger)
    finals=produce_finalists(candidates,results,cr)
    decision_outputs(candidates,results)
    schedule_outputs(finals,candidates,results)
    action_outputs(candidates,results)
    threshold_outputs(finals,candidates,results,cr)
    sensitivity_outputs(finals,candidates,results)
    delay_outputs(finals,candidates)
    structure=structural_outputs()
    structure['joint_cautious_largest_new_minus_same_without']=max(r['new_minus_same_WITHOUT_NEW'] for r in cr if r['scenario']=='cautious')
    structure['joint_cautious_positive_new_cases']=[r['candidate_id'] for r in cr if r['scenario']=='cautious' and r['new_minus_same_WITHOUT_NEW']>=0]
    structure['joint_interpretation']='Actual joint recalculation including conditional two-leg through/retained; not inferred solely from structural edge ceiling.'
    dump('structural_cautious_assessment.json',structure)
    top_pairs_outputs(candidates,results,market)
    resource_outputs()
    registry=read(P1/'path_registry.csv')
    added=[]
    for cid,c in candidates.items():
        if not cid.startswith('X_'):continue
        path=[c['new_jobs'][0]['flights'][0]['origin']]+[f['destination'] for f in c['new_jobs'][0]['flights']]
        matches=[r for r in registry if r['path']=='-'.join(path) and int(r['overnight_after'])==c.get('overnight_after',0)]
        added.append(dict(id=cid,path=path,overnight_after=c.get('overnight_after',0),
            matching_pass1_path_ids=[r['path_id'] for r in matches],
            already_in_pass1_time_beam=any(r['disposition']=='PARAMETER_SEARCH' for r in matches),
            weekdays_iso=[d+1 for d in c['candidate']['days']],departure_local_hour=c['candidate']['hour'],frequency_week=c['candidate']['freq'],
            target_tail=SETUPS[c['setup_id']]['target'],closure='SVX_to_SVX_on_same_existing_conditional_tail',
            leg_kinds=[f['kind'] for f in c['new_jobs'][0]['flights']],paid_ferry_sales=0))
    coverage=dict(pass1_attempts=480240,pass1_paths=103,pass1_representatives=36,detailed_candidates=len(candidates),
        additional_thin_leaders=[dict(setup=k[0],category=k[1],candidate=v[1]['id'],screen=v[0]) for k,v in sorted(leaders.items())],
        bounded_added_closed_paths=added,
        evaluated_unique_state_scenario=len(cache),finalists=finals,all_shortlist_evaluated=all(r['candidate_id'] in candidates for r in shortlist),
        worlds={k:sorted(a+'>'+b for a,b in v) for k,v in WORLDS.items()},
        engine_calls=dict(CALLS),no_global_optimum=True,unsearched='arbitrary old removals; mixed new paths; multi-tail new chains; all beams outside pass1; 3+leg products; actual international/contract inventory',
        model='P31 joint + exact event adapter + P06 physical inventory; conditional two-leg offered throughs, unobserved external own sales UNKNOWN',
        search_stopped='bounded representatives/leaders/mandatory controls; no broad rerun or infinite cautious search')
    dump('coverage_delta.json',coverage)
    # Pin complete pass1 and P36 admissions, plus all imported transitive inputs.
    completed={}
    for d in (STUDY,ROOT/'P36/market_recovery'):
        for p in sorted(d.rglob('*')):
            if p.is_file() and not p.is_relative_to(HERE) and '__pycache__' not in p.parts:
                completed[str(p.relative_to(ROOT))]=sha(p)
    for d in (RE.P05DIR,RE.P06DIR,RE.P04DIR,RE.BASE):
        for p in d.rglob('*'):
            if p.is_file() and p.suffix in ('.py','.csv','.json') and '__pycache__' not in p.parts:READS[str(p.relative_to(ROOT))]=sha(p)
    for p in (RE.HERE/'calculate.py',RE.ROOT/'ops_inputs/calendar_engine.py',RE.ROOT/'audit/common_contract.json'):
        READS[str(p.relative_to(ROOT))]=sha(p)
    dump('input_manifest.json',dict(read_sources=READS,completed_guard=completed,protected_hash_file=str((STUDY/'protected_files.json').relative_to(ROOT)),
        protected_expected=1418,numeric_research_updates=0,market_no_update='preserve prior value; UNKNOWN never overwrites positive facts',
        AI_use='Codex calculation implementation; no subagents/network/contact/booking; scenario not observed',
        currency='constant 2026 RUB scenario; not a Feb2027 invoice',actual_market_OD=None,actual_netfare=None,actual_fullPnL=None,cash=None))
    write_readme(finals,candidates,results,cr,structure)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    print(json.dumps(dict(candidates=len(candidates),unique_state_scenarios=len(cache),finalists=finals,engine_calls=dict(CALLS)),ensure_ascii=False))

def produce_finalists(candidates,results,rows):
    ranked=sorted([r for r in rows if r['scenario']=='base' and r['setup'] in ('B2S','B2T') and r['resource_queue']!='8BH_FAIL'],
                  key=lambda r:(-r['REPLACE'],-r['new_minus_same_WITHOUT_NEW'],r['candidate_id']))
    finals=[];pairs=set()
    for r in ranked:
        c=candidates[r['candidate_id']]
        signature=tuple(sorted({RE.pid(f['origin'],f['destination']) for f in c['new_jobs'][0]['flights']}))
        if signature in pairs:continue
        finals.append(r['candidate_id']);pairs.add(signature)
        if len(finals)==3:break
    assert len(finals)==3
    return finals

def decision_outputs(candidates,results):
    rows=[]
    for cid,c in candidates.items():
        for sc in ('base','cautious'):
            z=results[cid][sc]
            own=max(z,key=lambda st:z[st]['known_contribution'])
            allopts=menu(candidates,results,cid,sc)
            best=max(allopts,key=lambda x:x[2]['known_contribution'])
            removals=[x for x in allopts if x[1]!='REPLACE']
            bw=max(removals,key=lambda x:x[2]['known_contribution'])
            k=z['KEEP']['known_contribution'];w=z['WITHOUT_NEW']['known_contribution'];r=z['REPLACE']['known_contribution']
            rows.append(dict(candidate_id=cid,scenario=sc,cohort_key=cohort_key(c),known_best_same_disposition=own,
                known_best_all_eligible_id=best[0],known_best_all_eligible_state=best[1],known_best_all_subtotal=best[2]['known_contribution'],
                best_WITHOUT_NEW_or_KEEP_id=bw[0],best_WITHOUT_NEW_or_KEEP_state=bw[1],best_WITHOUT_NEW_or_KEEP_subtotal=bw[2]['known_contribution'],
                best_without_minus_KEEP_before_C=bw[2]['known_contribution']-k,
                new_gain_same_remove=r-w,old_change_gain_before_C=w-k,total_gain_before_unknown=r-k,
                conditional_rule='KEEP if unknown cancellation/opportunity/ownshift/F exceeds known removal/replace advantage; removal only if C+lostsales < W-K; replace only if incremental new margin covers differential F/D/ownshift AND beats same-cohort alternatives',
                actual_decision='NOT_IDENTIFIED; no launch recommendation',actual_outside_D=None,actual_cancellation_C=None,actual_F=None))
    table('disposition_decisions.csv',rows)

def menu(candidates,results,cid,sc,exclude_self=False):
    """All numerically comparable known-subtotal states, same fixed cohort.

    Unknown C/D/F can change this conditional envelope. It is never an actual
    cancellation recommendation. Deduplicate exactly identical event states.
    """
    rows=[];seen=set()
    for other,c in candidates.items():
        if cohort_key(c)!=cohort_key(candidates[cid]):continue
        for state,z in results[other][sc].items():
            if exclude_self and other==cid and state=='REPLACE':continue
            jobs=SETUPS[c['setup_id']]['jobs'] if state=='KEEP' else c['changed_old_jobs']+(c['new_jobs'] if state=='REPLACE' else [])
            hard,bh=G.physics(jobs,SETUPS[c['setup_id']]['positions'])
            if hard or bh>8+1e-9:continue
            signature=serial(jobs)
            if signature in seen:continue
            if exclude_self:
                own=serial(candidates[cid]['changed_old_jobs']+candidates[cid]['new_jobs'])
                if signature==own:continue
            seen.add(signature);rows.append((other,state,z))
    return rows

def schedule_outputs(finals,candidates,results):
    weekly=[];monthly=[];gates=[];duty=[]
    for cid in finals:
        c=candidates[cid];s=SETUPS[c['setup_id']]
        for state in ('KEEP','WITHOUT_NEW','REPLACE'):
            jobs=s['jobs'] if state=='KEEP' else c['changed_old_jobs']+(c['new_jobs'] if state=='REPLACE' else [])
            fs=list(G.flatten(jobs))
            for tail,initial in s['positions'].items():
                seq=sorted([f for f in fs if f['tail']==tail],key=lambda f:f['dep'])
                pos=initial;ready=0;prior=None
                for f in seq:
                    assert pos==f['origin'] and f['dep']>=ready
                    gap=f['dep']-(prior['arr'] if prior else 0)
                    action='NEW' if f['job_id'].startswith('NEW-') else 'KEEP'
                    if f['job_id'] in (c['candidate']['act']['swap'] or []):action='SWAP'
                    if c['candidate']['act']['move'] and f['job_id']==c['candidate']['act']['move'][0]:action='MOVE'
                    r=dict(candidate_id=cid,state=state,week=int(f['dep']//WEEK)+1,tail=tail,
                        iso_departure_weekday=datetime.fromisoformat(local(f['dep'],f['origin'])).isoweekday(),
                        old_or_new_id=f['job_id'],flight_id=f['flight_id'],assignment_action=action,
                        position_before=pos,origin=f['origin'],destination=f['destination'],position_after=f['destination'],
                        departure_utc=iso(f['dep']),arrival_utc=iso(f['arr']),departure_local=local(f['dep'],f['origin']),arrival_local=local(f['arr'],f['destination']),
                        origin_timezone=ZONES[f['origin']],destination_timezone=ZONES[f['destination']],block_minutes=f['block'],
                        ready_after_turn60_utc=iso(f['arr']+60),prior_ground_minutes=gap,prior_slack_after_turn60=max(0,gap-60),
                        prior_overnight_airport=f['origin'] if prior and gap>=480 else None,
                        overnight_paid_cost=None if prior and gap>=480 else 'NOT_AN_OVERNIGHT_ITEM',
                        kind=f['kind'],saleable_seats=0 if f['kind']=='PAID_FERRY' else 100,actual_tail=None,slot=None,crew_rest_approval=None,MRO=None)
                    monthly.append(r)
                    if 0<=f['dep']<WEEK:weekly.append(r)
                    pos=f['destination'];ready=f['arr']+60;prior=f
                assert pos==initial
                # Explicit idle/end positions for all seven days; no invisible free T2.
                for day in range(7):
                    start=day*1440;end=start+1440
                    daily=[f for f in seq if f['dep']<end and f['arr']>start]
                    def at_point(minute):
                        pos=initial
                        for f in seq:
                            if f['arr']<=minute:pos=f['destination']
                            elif f['dep']<=minute<f['arr']:return 'IN_FLIGHT:'+f['origin']+'>'+f['destination']
                        return pos
                    before=at_point(start);after=at_point(end)
                    weekly.append(dict(candidate_id=cid,state=state,week=1,tail=tail,iso_departure_weekday=day+1,
                        old_or_new_id='DAY_POSITION',flight_id='',assignment_action='DAY_SUMMARY',position_before=before,
                        day_summary_basis='UTC date; flight weekday is origin local',
                        position_after=after,departure_utc=iso(start),arrival_utc=iso(end),kind='DAY_POSITION_NOT_A_FLIGHT',
                        block_minutes=sum(max(0,min(end,f['arr'])-max(start,f['dep'])) for f in daily),
                        actual_tail=None,slot=None,crew_rest_approval=None,MRO=None))
                weekly.append(dict(candidate_id=cid,state=state,week=1,tail='R1_UNRELEASED',kind='RESERVE_NOT_SCHEDULED',
                    position_before=None,position_after=None,actual_tail=None)) if tail==next(iter(s['positions'])) else None
                # A ground gap >=8h identifies candidate crew change/rest point,
                # never declares that the gap is legal rest.
                wseq=[f for f in seq if 0<=f['dep']<WEEK]
                groups=[]
                for f in wseq:
                    if not groups or f['dep']-groups[-1][-1]['arr']>=480:groups.append([])
                    groups[-1].append(f)
                for n,grp in enumerate(groups):
                    start=grp[0]['dep'];end=grp[-1]['arr']
                    following=next((f for f in seq if f['dep']>end),None)
                    d=dict(candidate_id=cid,state=state,tail=tail,duty_group=n+1,first_utc=iso(start),last_utc=iso(end),
                        first_local=local(start,grp[0]['origin']),last_local=local(end,grp[-1]['destination']),
                        flight_ids=';'.join(f['flight_id'] for f in grp),elapsed_aircraft_chain_minutes=end-start,
                        illustrative_report_release_buffer_minutes=90,required_crew_duty_minutes_with_60report_30release=end-start+90,
                        next_ground_minutes=following['dep']-end if following else None,
                        possible_rest_after_90buffers_minutes=following['dep']-end-90 if following else None,
                        crew_rest_gate='UNKNOWN; approve roster/FDP incl night sectors, report/release and legal rest or swap crew',
                        meaning='continuous elapsed, no UTC midnight reset; >=8h gap is grouping assumption only')
                    duty.append(d)
        gates += [dict(candidate_id=cid,gate=x,status='UNKNOWN',required_evidence=y) for x,y in [
            ('tail_release_and_outside_D','Actual RRJ registration/7-day old assignment and outside-scope margin; no free regional or Moscow tail'),
            ('slots_and_latest_gates','Airport dated slots, curfew and latest arrival/departure; delay slack is not slot permission'),
            ('crew_FDP_rest','Approve duty rows, night work, report/release, rests, replacement crew; 8BH is not FDP'),
            ('variant_MTOW_track_payload','Actual RRJ variant/MTOW/AFM, runway, weather, alternate, fuel payload; no 2300km or +20% exclusion'),
            ('MRO_reserve_station','Maintenance windows, outstation support, dispatch and actually released separate reserve R1'),
            ('station_overnight_F','Invoice/tax/avoidability incl paid ferry, parking, hotel, transfers, reserve and launch'),
            ('market_and_own_shift','Observed directed OD/netyield, old marketed connecting and contract sales; existing two-leg model is conditional')]]
    table('final3_weekly_schedule.csv',weekly);table('final3_monthly_schedule.csv',monthly)
    table('duty_rest_gates.csv',duty);table('operational_gates.csv',gates)

def action_outputs(candidates,results):
    rows=[]
    for cid,c in candidates.items():
        s=SETUPS[c['setup_id']];changed={j['id']:j for j in c['changed_old_jobs']}
        for old in s['jobs']:
            new=changed.get(old['id'])
            action='REMOVE' if new is None else 'SWAP' if new['tail']!=old['tail'] else 'MOVE' if new['start']!=old['start'] else 'KEEP'
            for sc in ('base','cautious'):
                vals={}
                for state in ('KEEP','WITHOUT_NEW','REPLACE'):
                    _,ll=extraction(cid,sc,state,results[cid][sc][state])
                    rs=[r for r in ll if r['job_id']==old['id']]
                    vals[state]=(sum(r['revenue_once_allocated'] for r in rs),sum(r['avoidable_variable_scenario'] for r in rs))
                rows.append(dict(candidate_id=cid,scenario=sc,old_assignment_id=old['id'],old_flight_ids=';'.join(f['flight_id'] for f in old['flights']),
                    action=action,from_tail=old['tail'],to_tail=new['tail'] if new else None,
                    retime_minutes=new['start']-old['start'] if new else None,
                    old_dep_utc=iso(old['start']),changed_dep_utc=iso(new['start']) if new else None,
                    why='target-tail interval/turn conflict with exact new closed job' if action!='KEEP' else 'retained same source assignment',
                    retained_transfer='whole closed SVX job; both tails meet SVX and continuity checked' if action=='SWAP' else '',
                    KEEP_revenue=vals['KEEP'][0],KEEP_variable_cost=vals['KEEP'][1],
                    WITHOUT_NEW_revenue=vals['WITHOUT_NEW'][0],WITHOUT_NEW_variable_cost=vals['WITHOUT_NEW'][1],
                    REPLACE_revenue=vals['REPLACE'][0],REPLACE_variable_cost=vals['REPLACE'][1],
                    actual_old_profit=None,actual_cancellation_C=None,actual_retiming_loss=None,actual_outside_D=None,
                    source=old['source'],status=old['scope']))
    table('old_assignment_actions.csv',rows)

REPLAYS={}
REPLAYDETAILS={}
def replay(z, demand_scale=1, fare_scale=1, split=.5):
    """P06 reallocation, no second calendar/full producer assembly.

    Empty-own pools retain only outside alternatives and contribute zero RW
    revenue at every stress, so they may be omitted from this sensitivity seam.
    """
    key=(id(z),demand_scale,fare_scale,split)
    if key in REPLAYS:return REPLAYS[key]
    bun=copy.deepcopy(z['bundle'])
    active={p['demand_pool_id'] for p in bun['products'] if p['owner']=='RW'}
    bun['markets']=[m for m in bun['markets'] if m['demand_pool_id'] in active]
    bun['products']=[p for p in bun['products'] if p['demand_pool_id'] in active]
    for m in bun['markets']:
        a,b=m['demand_pool_id'].removeprefix('CITY:').split('>');m['potential_journeys']*=demand_scale*(split if a<b else 1-split)/.5
    ff={f['flight_instance_id']:f for f in bun['flights']}
    for p in bun['products']:
        if p['owner']=='RW' and any(ff[f]['pattern_id'].startswith('NEW-') for f in p['legs']):
            p['gross_fare']*=fare_scale;p['net_fare']*=fare_scale
    alloc=RE.allocate_p06(bun,bun['products']);CALLS['P06_sensitivity_reallocations']+=1
    ps={p['product_id']:p for p in bun['products']}
    rev=sum(a['carried']*ps[a['product_id']]['net_fare'] for a in alloc['allocations'] if a['owner']=='RW')
    val=rev-z['known_cost'];REPLAYS[key]=val
    directed=defaultdict(lambda:[0,0])
    seat={r['flight_instance_id']:r for r in alloc['seats']}
    for fid,f in ff.items():
        if f['pattern_id'].startswith('NEW-') and f['saleable_seats']>0:
            k=(f['origin_airport'],f['destination_airport'])
            directed[k][0]+=seat[fid]['carried_segments'];directed[k][1]+=1
    REPLAYDETAILS[key]=dict(directed=directed,potentials={m['demand_pool_id']:m['potential_journeys'] for m in bun['markets']})
    return val

def fuel_terms(z,sc):
    cs=[variable_cost(f['origin_airport'],f['destination_airport'],sc,f['block_hours_costscreen']) for f in z['bundle']['flights']]
    return sum(c['fuel_t'] for c in cs),sum(c['other_cost'] for c in cs)

def threshold_outputs(finals,candidates,results,cr):
    rows=[]
    for cid in finals:
        c=candidates[cid]
        for sc in ('base','cautious'):
            z=results[cid][sc];rp=z['REPLACE'];k,w,r=[z[x]['known_contribution'] for x in ('KEEP','WITHOUT_NEW','REPLACE')]
            rivals=menu(candidates,results,cid,sc,True)
            best=max(rivals,key=lambda x:x[2]['known_contribution']);bv=best[2]['known_contribution'];head=r-bv
            common=dict(candidate_id=cid,scenario=sc,alternative_id=best[0],alternative_state=best[1],
                        alternative_known_subtotal=bv,known_delta_vs_best_alternative=head,
                        scope='model known variable subtotal; actual C_D_F external ownshift UNKNOWN; same fleet')
            for name,value,formula in [
                ('F_plus_outside_D_plus_retime_plus_external_ownshift_max',head,'R - max(all eligible same-cohort alternatives); negative means already behind before unknowns'),
                ('new_vs_same_without_headroom',r-w,'REPLACE-WITHOUT_NEW; common cancellation C cancels; no donor deduction again'),
                ('required_old_cancellation_cost_for_WITHOUT_NEW_to_tie_KEEP',w-k,'C must be <= W-K; C is cost, not presumed 0'),
                ('required_old_cancellation_cost_for_REPLACE_to_tie_KEEP',r-k,'C + differential D/F/lostsales must be <= R-K'),
                ('donor_actual_loss_max_before_F',head,'Total displaced old opportunity/international D not already in joint ledger <= headroom'),
                ('overnight_reserve_launch_budget_max',head,'sum incremental overnight/parking/reserve/launch <= headroom after other unknown deductions')]:
                rows.append(common|dict(threshold=name,value=value,unit='RUB/month',formula=formula))
            # Exact affine landed fuel envelope against every feasible rival.
            tf,other=fuel_terms(rp,sc);inter=rp['net_revenue']-other
            lower,upper=0.0,float('inf');impossible=False
            for _,_,alt in rivals:
                af,ao=fuel_terms(alt,sc);a=inter-(alt['net_revenue']-ao);b=tf-af
                if abs(b)<1e-9:
                    if a < -1e-6:impossible=True
                elif b>0:upper=min(upper,a/b)
                else:lower=max(lower,a/b)
            feasible=not impossible and upper>=max(0,lower)
            rows.append(common|dict(threshold='landed_fuel_all_alternative_envelope',value=upper if math.isfinite(upper) else None,
                minimum_feasible=lower,feasible_nonnegative_interval=feasible,unit='RUB/t',
                formula='for EACH rival: (Rrev-Rother)-(Arev-Aother) >= (Rtonnes-Atonnes)*landed_price; same price all legs, uplift once'))
            # Candidate quotation only: all NEW-containing products reprice, MNL
            # recomputed, rival remains the offered alternative (no invented q).
            grid=[.5,.65,.8,.9,1,1.1,1.2,1.4,1.6,2]
            vals=[(f,replay(rp,fare_scale=f)-bv) for f in grid]
            positive=[f for f,v in vals if v>=0]
            rows.append(common|dict(threshold='new_quote_netfare_multiplier_MNL_grid',value=min(positive) if positive else None,
                tested_range='0.50..2.00',unit='multiplier',formula='gross/net BOTH change; fixed utility intercept, P06 reallocates; rival quote unchanged; no solution on tested grid' if not positive else 'first nonnegative tested multiplier; see evidence rows; nonmonotone, not extrapolated'))
            rows.append(common|dict(threshold='maximum_new_quote_discount_on_tested_grid',value=1-min(positive) if positive and min(positive)<=1 else None,
                unit='fraction',formula='1-lowest winning tested fare multiplier, rival best conditional alternative fixed; negative/absent headroom is not discount permission'))
            for f,v in vals:rows.append(common|dict(threshold='fare_MNL_evidence',value=f,delta_recomputed=v,unit='multiplier'))
            # Refine each observed price crossing, preserving the calibrated
            # intercept and recoupling choice/capacity on every step.
            lower_crossings=[]
            for (lo,lv),(hi,hv) in zip(vals,vals[1:]):
                if (lv<0)==(hv<0):continue
                left,right=lo,hi
                for _ in range(16):
                    mid=(left+right)/2;mv=replay(rp,fare_scale=mid)-bv
                    if (mv<0)==(lv<0):left=mid
                    else:right=mid
                mid=(left+right)/2
                rows.append(common|dict(threshold='fare_MNL_refined_crossing',value=mid,bracket_low=left,bracket_high=right,
                    delta_recomputed=replay(rp,fare_scale=mid)-bv,unit='fare_multiplier',
                    formula='16 bisections inside observed sign crossing; response is nonmonotone outside bracket; rival offered quote held'))
                if lv<0:lower_crossings.append(mid)
            if lower_crossings:
                low=min(lower_crossings)
                rows.append(common|dict(threshold='maximum_discount_refined_observed_interval',value=1-low,unit='fraction',
                    formula='lower fare boundary of observed winning interval, same MNL repricing; no untested global optimum claim'))
                for f in c['new_jobs'][0]['flights']:
                    if f['kind']!='PAID_FERRY':rows.append(common|dict(threshold='directional_netfare_at_refined_crossing',
                        origin=f['origin'],destination=f['destination'],value=RE.fare(f['origin'],f['destination'],sc)[1]*low,
                        unit='RUB/journey',formula='direct netfare reference at recoupled quote boundary; through uses endpoint fare once'))
            # Common demand scale: recompute EVERY same-cohort alternative;
            # retain one directed monthly pool per pair and its neutral split.
            demand_grid=[.02,.05,.1,.2,.35,.5,1,1.5,2,3,5]
            win=[]
            for mult in demand_grid:
                rr=replay(rp,demand_scale=mult)
                aa=max((replay(alt,demand_scale=mult),aid,st) for aid,st,alt in rivals)
                delta=rr-aa[0]
                if delta>=0:win.append(mult)
                rows.append(common|dict(threshold='q_both_directions_common_MNL_evidence',value=mult,delta_recomputed=delta,
                    stress_alternative_id=aa[1],stress_alternative_state=aa[2],unit='monthly_OD_multiplier',
                    formula='same multiplier on ALL pools and alternatives; directional split .5/.5; capacity cannot create demand'))
            rows.append(common|dict(threshold='required_q_common_multiplier_on_tested_grid',value=min(win) if win else None,
                tested_range='0.02..5.0',unit='monthly_OD_multiplier',formula='first winning grid point only; no empirical demand interval'))
            if win and min(win)>.02:
                hi=min(win);lo=max(x for x in demand_grid if x<hi)
                def qdelta(mult):
                    return replay(rp,demand_scale=mult)-max(replay(alt,demand_scale=mult) for _,_,alt in rivals)
                if qdelta(lo)<0:
                    for _ in range(12):
                        mid=(lo+hi)/2
                        if qdelta(mid)>=0:hi=mid
                        else:lo=mid
                    mid=(lo+hi)/2;replay(rp,demand_scale=mid)
                    breakpoint_best=max((replay(alt,demand_scale=mid),aid,ast) for aid,ast,alt in rivals)
                    rows.append(common|dict(threshold='q_common_MNL_refined_crossing',value=mid,bracket_low=lo,bracket_high=hi,
                        stress_alternative_id=breakpoint_best[1],stress_alternative_state=breakpoint_best[2],
                        delta_recomputed=qdelta(mid),unit='monthly_OD_multiplier',formula='all eligible alternatives recoupled on same demand; 12 bisections in first observed crossing'))
                    detail=REPLAYDETAILS[id(rp),mid,1,.5]
                    for (a,b),(q,n) in sorted(detail['directed'].items()):
                        rows.append(common|dict(threshold='q_direction_at_common_MNL_crossing',origin=a,destination=b,value=q/n,
                            stress_alternative_id=breakpoint_best[1],stress_alternative_state=breakpoint_best[2],
                            monthly_segment_q=q,monthly_dated_departures=n,
                            directed_monthly_potential=detail['potentials'].get(RE.P05.pool(a,b)),unit='pax/new_departure',
                            formula='P06 seats at common OD break-even, both directions explicit, not observed; monthly potential before choice'))
            # Revenue upper-bound sales proof, explicitly with retained effects.
            _,ll=extraction(cid,sc,'REPLACE',rp)
            new=[x for x in ll if x['job_id'].startswith('NEW-')]
            oldrev=sum(x['revenue_once_allocated'] for x in ll if not x['job_id'].startswith('NEW-'))
            need=rp['known_cost']+bv-oldrev
            service=[x for x in new if x['seats']>0]
            caprev=sum(100*RE.fare(x['origin'],x['destination'],sc)[1] for x in service)
            rows.append(common|dict(threshold='direct_new_sales_equal_fraction_of_full100_necessary_bound',value=need/caprev if caprev else None,
                required_new_allocated_revenue=need,full100_direct_revenue_ceiling=caprev,unit='fraction_of_100_seats_each_new_direction',
                formula='(all variable cost + best alternative - current retained allocated revenue)/new direct full100 revenue; retained/through allocation changes make this a diagnostic bound, NOT a demand solution'))
            for f in service[:len(c['new_jobs'][0]['flights'])]:
                rows.append(common|dict(threshold='directional_q_netfare_reference',origin=f['origin'],destination=f['destination'],
                    value=f['total_segment_q'],netfare=RE.fare(f['origin'],f['destination'],sc)[1],unit='scenario_pax_per_departure',
                    formula='direct + through capacity-shared passengers; not observed; netfare is direct scenario and through pays endpoint once'))
    table('thresholds.csv',rows)

def sensitivity_outputs(finals,candidates,results):
    rows=[]
    cases=[('MAIN',{}),('DIRECT_ONLY_NO_CONDITIONAL_THROUGHS',dict(through=False)),
           ('DIRECTION_65_35',dict(direction_split=.65)),('DIRECTION_35_65',dict(direction_split=.35)),
           ('DAY_REQUEST_NEUTRAL',dict(day_stress=0)),
           ('DAY_REQUEST_STRESS_PLUS50',dict(day_stress=.5)),('DAY_REQUEST_STRESS_MINUS50',dict(day_stress=-.5)),
           ('WEAK_ALL_NONBASE_ENDPOINT_POOLS_HALF',dict(weak_adjacent=True))]
    for cid in finals:
        c=candidates[cid]
        for sc in ('base','cautious'):
            for name,opts in cases:
                z=results[cid][sc] if not opts else {st:evaluate(c,sc,st,**opts) for st in ('KEEP','WITHOUT_NEW','REPLACE')}
                k,w,r=[z[st]['known_contribution'] for st in ('KEEP','WITHOUT_NEW','REPLACE')]
                rows.append(dict(candidate_id=cid,scenario=sc,case=name,KEEP=k,WITHOUT_NEW=w,REPLACE=r,
                    old_change_minus_KEEP=w-k,new_minus_WITHOUT_NEW=r-w,total_minus_KEEP=r-k,
                    scope='identical demand/fare/cost world ALL 3 states; no observed day/direction; +/- day weights .5..1.5 normalized monthly',
                    fullPnL=None,cash=None,support=0,cargo=0))
    table('sensitivity.csv',rows)

def delay_outputs(finals,candidates):
    rows=[];summaries=[]
    for cid in finals:
        c=candidates[cid];jobs=c['changed_old_jobs']+c['new_jobs']
        # Include previous and following weeks, so neither midnight nor a weekly
        # boundary resets position/readytime. All February follows to week5.
        fs=[]
        for w in range(-1,6):
            for j in jobs:
                for f in j['flights']:
                    fs.append(dict(f,dep=f['dep']+w*WEEK,arr=f['arr']+w*WEEK,flight_id=f['flight_id']+'/W'+str(w+1)))
        targets=[f for f in fs if 0<=f['dep']<WEEK and f['job_id'].startswith('NEW-')]
        new_targets=list(targets)
        # Each new leg, plus closest old before and after each new job/tail.
        for tail in sorted({f['tail'] for f in targets}):
            seq=sorted([f for f in fs if f['tail']==tail],key=lambda f:f['dep'])
            for n in list(targets):
                if n['tail']!=tail:continue
                before=[f for f in seq if not f['job_id'].startswith('NEW-') and f['arr']<=n['dep']]
                after=[f for f in seq if not f['job_id'].startswith('NEW-') and f['dep']>=n['arr']]
                if before:targets.append(before[-1])
                if after:targets.append(after[0])
        # If the changed tail retains no old job (daily AER replacement), the
        # nearest retained is on the other working tail. Perturb it separately
        # on that tail; shared crew/dispatch coupling is an UNKNOWN ops gate,
        # never invented cross-tail aircraft propagation.
        old_all=[f for f in fs if not f['job_id'].startswith('NEW-')]
        for n in new_targets:
            before=[f for f in old_all if f['arr']<=n['dep']]
            after=[f for f in old_all if f['dep']>=n['arr']]
            if before:targets.append(max(before,key=lambda f:f['arr']))
            if after:targets.append(min(after,key=lambda f:f['dep']))
        targets={f['flight_id']:f for f in targets}
        for target in targets.values():
            seq=sorted([f for f in fs if f['tail']==target['tail']],key=lambda f:f['dep'])
            for turn in (60,90):
                base=[];ready=-1e20
                for f in seq:
                    dep=max(f['dep'],ready);arr=dep+f['block'];ready=arr+turn;base.append((dep,arr))
                for hold in (30,60,120):
                    ready=-1e20;pos=seq[0]['origin'];started=False;absorbed=None;old=[];maxlag=0;count=0
                    for i,f in enumerate(seq):
                        injection=hold if f['flight_id']==target['flight_id'] else 0
                        dep=max(f['dep']+injection,ready);arr=dep+f['block'];prevready=ready;ready=arr+turn
                        assert pos==f['origin'];pos=f['destination']
                        if injection:started=True
                        if not started:continue
                        lag=dep-base[i][0];maxlag=max(maxlag,lag)
                        if not f['job_id'].startswith('NEW-') and lag>1e-9:old.append(f['flight_id'])
                        if lag<=1e-9 and absorbed is None:absorbed=f['flight_id']
                        rows.append(dict(candidate_id=cid,injection_flight=target['flight_id'],injection_kind='NEW' if target['job_id'].startswith('NEW-') else 'NEAREST_RETAINED',
                            hold_minutes=hold,turn_minutes=turn,downstream_flight_id=f['flight_id'],old_assignment_id=f['job_id'],tail=f['tail'],
                            origin=f['origin'],destination=f['destination'],scheduled_departure_utc=iso(f['dep']),scheduled_arrival_utc=iso(f['arr']),
                            baseline_turn_case_dep_utc=iso(base[i][0]),actual_departure_utc=iso(dep),actual_arrival_utc=iso(arr),
                            position_before=f['origin'],position_after=pos,ready_before_utc=iso(prevready) if prevready>-1e10 else None,
                            ready_after_utc=iso(ready),delay_vs_turn_case_minutes=lag,total_delay_vs_schedule=dep-f['dep'],
                            needed_slot_slack_minutes=dep-f['dep'],required_tail_or_crew_or_cancel='if latest gate/rest cannot cover propagated minutes; actual gate UNKNOWN',
                            day_crossed=datetime.fromisoformat(iso(dep)).date()!=datetime.fromisoformat(iso(f['dep'])).date(),minute_cost=None))
                        count+=1
                        # Continue through next UTC day, even after absorption.
                        if absorbed and f['dep']>=target['dep']+1440:break
                    summaries.append(dict(candidate_id=cid,injection_flight=target['flight_id'],hold_minutes=hold,turn_minutes=turn,
                        first_absorbed_at=absorbed,affected_old_ids=';'.join(old),maximum_incremental_delay=maxlag,
                        downstream_rows=count,actual_latest_gate=None,actual_crew_gate=None,delay_probability=None,retime_reserve_cost=None))
    table('delay_propagation.csv',rows);table('delay_summary.csv',summaries)

def structural_outputs():
    rows=[]
    for a in NODES:
        for b in NODES:
            if RE.city(a)==RE.city(b):continue
            e=G.edge(a,b);h=e['minutes']/60
            old=ORIG_COST(a,b,'cautious',h);new=variable_cost(a,b,'cautious',h)
            net=0 if e['kind']=='PAID_FERRY' else RE.fare(a,b,'cautious')[1]
            rows.append(dict(origin=a,destination=b,kind=e['kind'],block_minutes=e['minutes'],cautious_netfare=net,
                original_P31_cost=old['fixed_cost'],excluded_fixed_crew=new['fixed_crew_excluded'],avoidable_variable_cost=new['fixed_cost'],
                original_full100_cap=100*net-old['fixed_cost'],adjusted_full100_cap=100*net-new['fixed_cost'],
                fuel_t=new['fuel_t'],fuel_price=new['fuel_price'],other_variable=new['other_cost'],
                fuel_break_even_full100=(100*net-new['other_cost'])/new['fuel_t'],
                netfare_min_full100=new['fixed_cost']/100,netfare_raise_min_fraction=new['fixed_cost']/(100*net)-1 if net else None,
                formula='fuel_t=(hours*1.9+0.25); landed161696 ONCE; other=hours*(55000+8000)+115307+40000; fixedcrew excluded; opaque pax basket/F UNKNOWN'))
    assert len(rows)==238
    table('structural_cautious_bounds.csv',rows)
    aer=next(r for r in rows if r['origin']=='SVX' and r['destination']=='AER')
    proof=dict(edges=238,original_all_full100_negative=all(r['original_full100_cap']<0 for r in rows),
        adjusted_all_full100_negative=all(r['adjusted_full100_cap']<0 for r in rows),
        adjusted_maximum_cap=max(r['adjusted_full100_cap'] for r in rows),AER=aer,
        fuel_base_product=136300,fuel_base_uplift=1696,base_landed=137996,cautious_landed=161696,
        uplift_rule='base product136300+uplift1696 once. Cautious161696 already landed; no second1696/storage1353. Source transfer scenario, invoice/tax compatibility UNKNOWN.',
        cost_unit_audit='hours x tonnes/hour + tonnes/cycle, times RUB/tonne; hour rates RUB/hour, service/deice per physical cycle. No kg/tonne or minute/hour conversion error found.',
        meaning='Standalone full100 direct contribution ceiling under these priors. NOT a theorem about retained recapture/conditional through fares: joint results test those separately. No empirical claim that real market is loss making.',
        change_gate='Minimum input change in structural CSV is necessary capacity ceiling only; MNL netfare grid/q tests still needed and unknown F must be funded.')
    dump('structural_cautious_assessment.json',proof)
    return proof

def top_pairs_outputs(candidates,results,market):
    pairs=[('SVX','KJA'),('GOJ','KJA'),('TJM','MRV'),('CEK','MRV'),('GOJ','TOF'),('SVX','IKT')]
    rows=[]
    for a,b in pairs:
        eligible=[]
        for cid,c in candidates.items():
            if c['setup_id'] not in ('B2S','B2T'):continue
            if not any(RE.pair(f['origin'],f['destination'])==RE.pair(a,b) for j in c['new_jobs'] for f in j['flights']):continue
            _,bh=G.physics(c['changed_old_jobs']+c['new_jobs'],SETUPS[c['setup_id']]['positions'])
            eligible.append((cid,c,bh))
        # Prefer diagnostic-admissible, then entire-chain incremental contribution.
        cid,c,bh=max(eligible,key=lambda x:(x[2]<=8+1e-9,results[x[0]]['base']['REPLACE']['known_contribution']-results[x[0]]['base']['WITHOUT_NEW']['known_contribution']))
        services=[r for r in market['canonical_services.csv'] if set(r['pair'].split('-'))=={a,b}]
        rows.append(dict(pair=a+'-'+b,candidate_id=cid,whole_closed_chain='-'.join([c['new_jobs'][0]['flights'][0]['origin']]+[f['destination'] for f in c['new_jobs'][0]['flights']]),
            actual_newness='UNPROVED_CONDITIONAL; no RW row is not absence',RW_current_nonstop='UNKNOWN',
            competitors=';'.join(sorted({r['carrier_operated']+':'+r['flight'] for r in services})) or 'UNKNOWN_NOT_ABSENT',
            positive_service_rows=len(services),quality=';'.join(sorted({r['evidence_class'] for r in services})) or 'UNKNOWN',
            covered_feb_dates=';'.join(sorted({r['covered_dates'] for r in services if r['week_start']=='2027-02-01'})) or 'UNKNOWN',
            BASE_chain_delta_vs_same_without=results[cid]['base']['REPLACE']['known_contribution']-results[cid]['base']['WITHOUT_NEW']['known_contribution'],
            CAUT_chain_delta_vs_same_without=results[cid]['cautious']['REPLACE']['known_contribution']-results[cid]['cautious']['WITHOUT_NEW']['known_contribution'],
            max_daily_BH=bh,what_changes_rank='invoice landed fuel/services; validated endpoint netyield/OD and old contribution; through/feeder and overnight/reserve F; crew/tail gate',
            status='conditional research priority, not launch or proven new route',fullPnL=None))
    rows.sort(key=lambda r:(r['max_daily_BH']>8+1e-9,-r['BASE_chain_delta_vs_same_without'],r['pair']))
    for n,r in enumerate(rows):r['conditional_rank']=n+1
    table('top5_pairs.csv',rows[:5]);table('mandatory_pair_controls.csv',rows)

def resource_outputs():
    rows=[]
    for case,entries in [('S0',[]),('S1',['2027-08-01','2027-11-01']),('S1D6',['2028-02-01','2028-05-01'])]:
        for period in ['2027-02-01','2027-08-01','2027-11-01','2028-02-01','2028-05-01']:
            dt=datetime.fromisoformat(period);import calendar
            rows.append(dict(case=case,month=period[:7],calendar_days=calendar.monthrange(dt.year,dt.month)[1],
                main_existing_B2_working_tails=2,separate_reserve='R1_UNRELEASED_UNKNOWN',
                illustrative_entries=';'.join(entries),scenario_postentry_available=sum(e<=period for e in entries),
                entry_is_delivery=False,forecast=False,certification=None,actual_SJ_count=None,
                gate='resource-only; not before H22027 AND illustrative entry; actual certification/dispatch/MRO/type economics UNKNOWN',
                SJ_PD8_revenue=None,SJ_PD8_fuel=None,SJ_PD8_cost=None,RRJ_analogy_admitted=False,fullPnL=None))
    table('resource_cases.csv',rows)

def write_readme(finals,candidates,results,cr,structure):
    lines=['# P36 pass2 — завершённый локальный расчёт', '',
        '**Запуск не доказан. Ни один вариант не рекомендован к запуску.** Это второй расчётный проход, не новый обзор рынка. '+
        f'Проверены все36 представителей pass1 и ограниченные дополнительные лидеры/обязательные цепи: всего{len(candidates)} кандидатов. '+
        'Их KEEP/WITHOUT_NEW/REPLACE используют одинаковый парк, общий directed city OD и полный февраль2027 (28дней,4повтора).', '',
        'Основной результат — известный сценарный subtotal до C, фактического outside donorD, потерь переноса/внешних own connecting продаж и F '+
        '(станция, позиционирование сверх явно оплаченных ferry, ночёвка, стоянка, резерв, запуск). UNKNOWN не0; fullPnL/cash=NULL. '+
        'Не вычитаем старый доход или донора повторно после jointdelta. Общий cancellationC у WITHOUT_NEW и REPLACE сокращается. '+
        'Снятие может быть лучше KEEP только если C и прочие потери ниже соответствующего порога; это не доказательство доходности новой цепи.', '',
        'Основная совместная модель: чистые P31 evaluate_combined_programme/choice_bundle + P06 allocate. Точный event-calendar adapter '+
        'сохраняет все события, ночёвки и old IDs, проверяет позицию/turn60/полный месяц; старый P03 pattern API это не кодирует. '+
        'Модель включает все old/new direct продукты и условно предлагаемые двухплечевые same-tail through с60–240мин пересадки '+
        'по сценарию тарифа endpoint P05, одной выручкой и общими физическими креслами; штраф остановки P05 применён. '+
        'Это не full producer acceptance: фактический перечень marketed own/3+leg/interline/contract products и их продажи неизвестен, '+
        'внешний shift остаётся отдельным вычетом. Неподтверждённые блок-контракты не изобретены; поддержка/cargo0.', '',
        'P05 OD/netfare/направление/день — priors и сценарии, не наблюдения. Main split50/50, месячно гибкий спрос; '+
        'направленные35/65 и65/35 и симметричные day weights0.5–1.5 сохраняют месячный OD. Нет премии времени или экспертной скидки. '+
        'Weak-adjacent стресс уменьшает все nonbase endpoint pools на50% во всех трёх состояниях, не удаляет только доходы треугольника. '+
        'DME/ZIA физически различны, один MOW pool. 100seats — сценарий.', '',
        'Постоянная аренда и постоянная зарплата экипажей не избегаемы. Основной variable ledger исключает ставку crew15/22тыс₽/BH из P31; '+
        'избегаемость MRO/ground/deice остаётся подписанным сценарием до invoice. P04 pax basket исключён из-за неизвестного overlap; '+
        'пассажирские услуги и договорные минимумы входят в UNKNOWN F. Топливо base136300+1696=137996₽/т, cautious161696₽/т landed once; '+
        'это перенос прежнего сценария, не верифицированная совместимая налоговая база/февральский счёт.', '',
        'Три различных полезных условных программы на одном B2 (2SVX tail, выбранные GOJ4/KUF7/OMS2/UFA2):', '',
        '|Кандидат/цепь|Раз в неделю|BASE new−WITHOUT_NEW, ₽/мес|CAUT new−WITHOUT_NEW, ₽/мес|',
        '|---|---:|---:|---:|']
    for cid in finals:
        c=candidates[cid];path='–'.join([c['new_jobs'][0]['flights'][0]['origin']]+[f['destination'] for f in c['new_jobs'][0]['flights']])
        vals=[results[cid][sc]['REPLACE']['known_contribution']-results[cid][sc]['WITHOUT_NEW']['known_contribution'] for sc in ('base','cautious')]
        lines.append(f'|{cid}: {path}|{c["candidate"]["freq"]}|{vals[0]:,.0f}|{vals[1]:,.0f}|')
    first=finals[0];c=candidates[first];base=results[first]['base'];caut=results[first]['cautious']
    act=c['candidate']['act'];affected=sorted(set(act['remove'])|set(act['swap'] or [])|({act['move'][0]} if act['move'] else set()))
    candidates4=[r for r in cr if r['scenario']=='base' and r['setup'] in ('B2S','B2T') and len(r['path'].split('-'))>=5 and r['resource_queue']!='8BH_FAIL']
    b4=max(candidates4,key=lambda r:r['REPLACE']) if candidates4 else None
    a=structure['AER']
    lines += ['', 'Полные три состояния финалистов (известный variable subtotal, млн₽/февраль; ещё доC/D/F):', '',
              '|Кандидат|Сценарий|KEEP|WITHOUT_NEW|REPLACE|', '|---|---|---:|---:|---:|']
    for cid in finals:
        for sc in ('base','cautious'):
            rr=results[cid][sc]
            lines.append('|'+cid+'|'+sc+'|'+'|'.join(f'{rr[st]["known_contribution"]/1e6:.3f}' for st in ('KEEP','WITHOUT_NEW','REPLACE'))+'|')
    lines += ['', 'Лучшие доступные WITHOUT_NEW также пересчитаны совместно, на том же B2:']
    for sc in ('base','cautious'):
        opts=menu(candidates,results,first,sc)
        w=max((x for x in opts if x[1]!='REPLACE'),key=lambda x:x[2]['known_contribution'])
        gain=w[2]['known_contribution']-results[first][sc]['KEEP']['known_contribution']
        lines.append(f'- {sc}: {w[0]} {w[1]}, subtotal{w[2]["known_contribution"]/1e6:.3f}млн₽; '+
                     f'порогC+потерь противKEEP≤{gain/1e6:.3f}млн₽. Старые IDs — old_assignment_actions. Это условный эффект priors, не предложение фактически снять рейсы.')
    th=read(HERE/'thresholds.csv')
    for sc in ('base','cautious'):
        xs=[r for r in th if r['candidate_id']==first and r['scenario']==sc]
        f=next(r for r in xs if r['threshold']=='F_plus_outside_D_plus_retime_plus_external_ownshift_max')
        q=[r for r in xs if r['threshold']=='directional_q_netfare_reference']
        lines.append(f'\nПервый кандидат {sc}: '+', '.join(r['origin']+'→'+r['destination']+f' q={float(r["value"]):.2f}, net={float(r["netfare"]):.2f}₽' for r in q)+
                     f'; differential F+D+lostsales+C headroom против {f["alternative_id"]}/{f["alternative_state"]} = {float(f["value"])/1e6:.3f}млн₽. '+
                     'Это разность неизвестных затрат двух альтернатив, не бесплатный бюджет; q модельное, full100 только cap.')
        qgate=[r for r in xs if r['threshold']=='q_direction_at_common_MNL_crossing']
        if qgate:
            lines.append('Общий MNL break-even по спросу против envelope всех доступных альтернатив: '+
                ', '.join(r['origin']+'→'+r['destination']+f' q≈{float(r["value"]):.2f}/вылет при potential≈{float(r["directed_monthly_potential"]):.0f}/месяц' for r in qgate)+
                '; это проверенный сценарный порог, не оценка реального OD. Цена и все остальные рынки сохранены в общем мире.')
    lines += ['', 'Физическая согласованность не означает свободный парк или допуск. B2 — сценарная выбранная oldprogramme, '+
        'не фактическая ротация. B1SCOPED оставляет чужие часы blocked; B1IDLE и условная Москва содержат UNKNOWN outsideD. '+
        'E1/Москва в отдельных cohorts и не ранжируются против B2 суммой. WZ901 ZIA–KGD24.09 не перенесён в KEEP; BUS=Батуми, '+
        '08:10вт/пт/вс mixed Tu/SSJ не доказывает RRJ ресурс.', '',
        ('Лучший проверенный B2 класс4+ — '+b4['candidate_id']+' '+b4['path']+f'; new−WITHOUT_NEW={b4["new_minus_same_WITHOUT_NEW"]:,.0f}₽ BASE. Это контроль, не победитель.' if b4 else 'В B2 нет диагностически допустимого4+ в ограниченном наборе; прежние4+ остаются контролями.'), '',
        '**Структурный осторожный результат.** Все238 рёбер при full100 отрицательны в старом P31; '+
        f'после исключения fixedcrew все238 также отрицательны={structure["adjusted_all_full100_negative"]}. '+
        f'AER: старый cost{a["original_P31_cost"]:,.1f}₽/плечо,100×net{a["cautious_netfare"]:,.4f}; '+
        f'variable cost{a["avoidable_variable_cost"]:,.1f}, потолок{a["adjusted_full100_cap"]:,.1f}. '+
        f'Необходимый AER structural net≥{a["netfare_min_full100"]:,.1f}₽ (+{a["netfare_raise_min_fraction"]:.1%}) '+
        f'или landedfuel≤{a["fuel_break_even_full100"]:,.1f}₽/т при full100, ещё доF. '+
        'Это необходимый capacity ceiling standalone, не фактический спрос и не автоматическое доказательство joint retained/through эффекта. '+
        f'Самый высокий joint CAUT new−sameWITHOUT_NEW среди60 = {structure["joint_cautious_largest_new_minus_same_without"]:,.0f}₽, тоже отрицательный. '+
        'Совместные CAUT результаты и direct-only стресс проверены отдельно; более широкий поиск при фиксированном отрицательном ceiling не лечит priors. '+
        'MNL price grid пересчитывает capture; fare×100 не сохраняет100 пассажиров.', '',
        '**Первая проверка — invoice и oldprofit, затем цепь '+first+'.** AffectedoldIDs: '+('; '.join(affected) or 'нет снятых/перенесённых внутри selectedscope; outsideoccupancy UNKNOWN')+'. '+
        'Это адресный кандидат для валидации, не пилот. BASE new−sameWITHOUT_NEW='+f'{base["REPLACE"]["known_contribution"]-base["WITHOUT_NEW"]["known_contribution"]:,.0f}₽; '+
        'CAUT='+f'{caut["REPLACE"]["known_contribution"]-caut["WITHOUT_NEW"]["known_contribution"]:,.0f}₽. '+
        'Точные directedq/netfare, диапазон MNL-теста и F/ночёвка/резерв/донор/cancellation gates — thresholds.csv; отрицательный headroom требует изменения подтверждённых входов до запуска. '+
        'В первую очередь нужны совместимые fuel/uplift/service invoices и реальная старая маржа/бронирования всех затронутых IDs: '+
        'без них знак actual KEEP/remove/replace не установлен.', '',
        'Календари final3 содержат KEEP/WITHOUT_NEW/REPLACE по tail, все4повтора, local/IANA/UTC, позиции, turn60 и резерв. '+
        'duty_rest_gates показывает непрерывный elapsed и явные сценарные60report+30release buffers; группировка по8h ground не утверждает законный rest. '+
        'UTC20:00 не сбрасывает смену. BH8fail вынесены в candidate_results, в финалисты не включены. '+
        'delay_propagation:30/60/120 на каждом новом weekly плече и ближайших retained, turn60/90, через следующий день/неделю, '+
        'с readytime и списком затронутых old. Вероятность/цена минуты/slot latest/crew limit UNKNOWN.', '',
        'Market recovery фактически P36/market_recovery: все46 положительных P34 сохранены; numericupdates0, no_update сохраняет старое. '+
        'Новизна топ5 UNPROVED; опубликованный конкурентный паттерн не гарантирует futureexecution и не заменяет наблюдаемый OD. '+
        'S0 использует действующий условный парк. S1 Aug/Nov2027 и S1D6 Feb/May2028 — только resource-only entry gates; '+
        'доставка≠ввод, доH22027 нет новыхSJ, PD8≈RRJ не допущено, экономика нового типа NULL.', '',
        'Файлы: candidate_results и three_state_comparison — разложение (a)oldchange (b)new vsremove (c)total (d)UNKNOWN; '+
        'equivalence_map ссылается на недублируемые ledgers. old_assignment_actions содержит каждый old ID и revenue/cost трёх состояний. '+
        'top5_pairs ранжирует лучшую закрытую цепь, не голую региональную пару. coverage_delta фиксирует ограниченное покрытие, не optimum. '+
        'Код/manifest/verify/validation воспроизводимы. Защита1418 и все completedP36/pass1 hashes проверяются. Запись только pass2; '+
        'без поиска, субагентов, контактов, броней, панели, Git mutation. AI использован для кода и расчёта, не для создания наблюдений.', '',
        'Запуск: существующий `context/28_end_to_end_audit_20261110/code/sandbox/venv/bin/python -B '+str(HERE.relative_to(ROOT))+'/calculate.py`; '+
        'затем тем же Python `-B .../verify.py` (детерминированный повтор и содержательные fixtures). STOP после handoff.']
    (HERE/'README.md').write_text('\n'.join(lines)+'\n')
    (HERE/'handoff.md').write_text('# Handoff P36 pass2\n\nЛокальный пакет завершён. Финалисты: '+', '.join(finals)+'. '+
        'Запуск НЕ доказан, fullPnL/cash=NULL. Читать README, three_state_comparison, thresholds и operational_gates. '+
        'Проверены36pass1 плюс boundedleaders/mandatoryclosedpaths, не новый глобальный поиск. '+
        'No-update canonical admission сохранён; старые результаты и1418protected не менялись. '+
        'validation.json содержит фактические результаты запуска/повтора/fixtures, не dispatch. '+
        'Далее адресная независимая рецензия может проверить адаптер exactevents, two-leg through scenario, fixedcrew avoidability, '+
        'лучшие WITHOUT_NEW и неизвестные C/D/F/ownshift. Работа окончена, STOP; рецензента не ждём.\n')

if __name__=='__main__':
    main()

