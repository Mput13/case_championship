#!/usr/bin/env python3
"""Finite, conditional network assembly. Writes only beside this file.

No optimiser or dispatch claim. All main calendars use explicitly DIAGNOSTIC
cost-screen blocks because the two commercial winners lack paired valid blocks.
The completed route API and pinned P06 allocator do the joint recalculation.
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
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORKSPACE = ROOT.parents[1]
VERSION = 'NETWORKS-1-20261112'
spec = importlib.util.spec_from_file_location('completed_route_api', ROOT/'route_economics/calculate.py')
RE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RE)
START, END = '2027-01-01', '2028-12-31'
MONTHS = [f'{y}-{m:02}' for y in (2027, 2028) for m in range(1, 13)]
TZ = {'SVX':'Asia/Yekaterinburg', 'AER':'Europe/Moscow', 'MRV':'Europe/Moscow',
      'KJA':'Asia/Krasnoyarsk', 'OMS':'Asia/Omsk', 'NJC':'Asia/Yekaterinburg', 'KUF':'Europe/Samara'}
DIRECTS = ['D1_FOCUS', 'D2_SEASONAL', 'D3_STAGED']
HUB = 'HUB_OMS_RESOURCE_MATCHED'
ROUTES = [('SVX','AER'), ('SVX','MRV'), ('SVX','KJA'), ('SVX','OMS'), ('OMS','NJC')]
MAIN_BASIS = 'DIAGNOSTIC_GEOMETRY_COSTSCREEN_NOT_OPS_PROVEN'
TURN = 60  # explicit common conservative scenario, not a legal minimum


def read(path):
    return RE.read(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(name, obj):
    p = (HERE/name).resolve()
    assert HERE in p.parents
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n')


def table(name, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: 'NULL' if v is None else json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v,(dict,list,tuple)) else round(v,6) if isinstance(v,float) else v for k,v in r.items()})


def resource(e, s, reserve=True):
    tails = [dict(id=f'EX-{i+1}', type='RRJ95_VARIANT_UNKNOWN', initial_location='SVX',
                  available_from=START+'T00:00:00Z', available_to='2029-01-01T00:00:00Z',
                  saleable_seats=100, donor='UNKNOWN_EXTERNAL_PENDING_DONOR', maintenance_windows=[])
             for i in range(e)]
    for x in RE.CONTRACT['resource']['deliveries'][s]:
        tails.append(dict(id=x['id'], type='SJ100_PD8_UNAPPROVED_COST_TRANSFER', initial_location='SVX',
                          available_from=x['entry']+'T00:00:00Z', available_to='2029-01-01T00:00:00Z',
                          delivery_date=x['delivery'], saleable_seats=100,
                          donor='NEW_INDUCTION_LEASE_RESERVE_COST_UNKNOWN', maintenance_windows=[]))
    if reserve:
        tails.append(dict(id='RES-1', type='RRJ95_VARIANT_UNKNOWN', initial_location='SVX',
                          available_from=START+'T00:00:00Z', reserve=True,
                          donor='UNKNOWN_SEPARATE_RESERVE_DONOR'))
    return tails


def blocks():
    out=[]
    for a,b in ROUTES:
        for x,y in [(a,b),(b,a)]:
            nominal=math.ceil(RE.geometry(x,y)[1]*60)
            out.append(dict(origin=x,destination=y,nominal_minutes=nominal,
                            high_minutes=math.ceil(nominal*1.15), evidence=MAIN_BASIS,
                            source='RE.geometry P03 legacy cost formula; NOT published block',
                            high_basis='NET-A02 uncalibrated +15% stress, NOT a confidence/dispatch bound',
                            aircraft_variant_admission='UNKNOWN; no accepted exact variant'))
    return out


def pat(pid, path, weekdays, start, end, tid, hour='09:00'):
    return dict(id=pid,path=path,weekdays=weekdays,frequency_per_week=len(weekdays),
                start=start,end=end,departure_local=hour,workingtailids=[tid],
                route_adapter_weekdays=[d-1 for d in weekdays],
                block_admission=MAIN_BASIS, crew='UNKNOWN', maintenance='UNKNOWN')


def request(patterns, tails, block_case='nominal'):
    return dict(timezones=TZ, blocks=blocks(), tails=copy.deepcopy(tails), patterns=patterns,
                turn_minutes=TURN, diagnostic_bh_day=8, block_case=block_case,
                reserve_contract='UNKNOWN_NOT_FREE_ALLOCATION',
                previous_payments='SAME_UNAVOIDABLE_PAYMENT_IDS_IN_P_AND_KEEP; AMOUNTS_DATES_UNKNOWN')


def epochs(tails):
    working=[t for t in tails if not t.get('reserve')]
    edges=sorted({START, '2029-01-01'} | {t['available_from'][:10] for t in working})
    for a,b in zip(edges,edges[1:]):
        ts=[t for t in working if t['available_from'][:10]<=a]
        yield a, (date.fromisoformat(b)-timedelta(days=1)).isoformat(), ts


def programme(name, tails, split=7):
    """Predeclared N(t) policies; no trimming of fixed author references."""
    out=[]
    for ei,(a,b,ts) in enumerate(epochs(tails)):
        if not ts: continue
        for month in MONTHS:
            y,m=map(int,month.split('-'))
            lo=max(a, month+'-01'); hi=min(b, f'{month}-{calendar.monthrange(y,m)[1]}')
            if lo>hi: continue
            stem=f'{name}/{ei}/{month}'
            def add(tag, path, days, tail, hour='09:00'):
                if days: out.append(pat(stem+'/'+tag,path,days,lo,hi,tail['id'],hour))
            if name==HUB:
                # Ordered two-leg banks. One aircraft closes at SVX every cycle.
                # First partial week explicitly has NO bank; no annual transfer shortcut.
                hlo=max(lo,'2027-01-04')
                if hlo>hi: continue
                for i,t in enumerate(ts[:2]):
                    out.append(pat(stem+f'/BANK{i+1}', ['SVX','OMS','NJC','OMS','SVX'],
                                   [1,3,5] if i==0 else [2,4,6], hlo, hi,t['id']))
                continue
            if name=='D2_SEASONAL':
                if m in (5,6,7,8,9,10):
                    add('AER',['SVX','AER','SVX'],list(range(1,8)),ts[0])
                else:
                    add('MRV',['SVX','MRV','SVX'],[1,3,5,6,7],ts[0])
                    add('KJA',['SVX','KJA','SVX'],[2,4],ts[0])
                # Deliberately leave extra working slots unused; no weak filler routes.
            elif name=='D3_STAGED' and len(ts)>=2:
                add('AER',['SVX','AER','SVX'],list(range(1,8)),ts[0])
                add('MRV',['SVX','MRV','SVX'],list(range(1,8)),ts[1])
                if len(ts)>=3:
                    add('KJA',['SVX','KJA','SVX'],[2,5],ts[2])
            else:
                add('AER',['SVX','AER','SVX'],list(range(1,split+1)),ts[0])
                add('MRV',['SVX','MRV','SVX'],list(range(split+1,8)),ts[0])
    return out


def old_programme(tails, f=2, common_control=False):
    """Unknown future service represented ONLY by explicit conditional scenarios.
    Common control is 2 AER + 2 MRV + 2 OMS returns/week, on same E2 resource.
    No claim that these are actual existing flights or that MQF legs are RW.
    """
    ts=[t for t in tails if not t.get('reserve')]
    if len(ts)<2: raise ValueError('old-frequency sensitivity requires E2, not an invented tail')
    days=[1,2,3,4,5,6,7][:f]
    ps=[]
    if f:
        ps=[pat('KEEP/AER',['SVX','AER','SVX'],days,START,END,ts[0]['id']),
            pat('KEEP/MRV',['SVX','MRV','SVX'],days,START,END,ts[1]['id'])]
    if common_control:
        ps.append(pat('KEEP/OMS',['SVX','OMS','SVX'],[3,4],START,END,ts[0]['id']))
    return ps


ORIGINAL_CHOICE = RE.choice_bundle
COMMON_DIRECTIONS = {(x,y) for a,b in ROUTES+[('SVX','NJC')] for x,y in [(a,b),(b,a)]}


def common_bundle(flights, scenario, affected_pairs, start, end, demand_overrides=None, response='passive'):
    # Identical complete OD universe even for an empty/no-addition programme.
    return ORIGINAL_CHOICE(flights,scenario,set(affected_pairs)|COMMON_DIRECTIONS,
                           start,end,demand_overrides,response)


def hub_bundle(flights, scenario, affected_pairs, start, end, demand_overrides=None, response='passive'):
    """Minimal local P06-compatible adapter, not the author full hub model.

    Add endpoint SVX<>NJC markets, identical even when KEEP has no bank, and
    dated connections only at OMS with 60<=layover<=180 min. P06 shares each
    physical leg between local and through ODs. One endpoint fare, one journey.
    No connecting/unique RW customer calibration is asserted.
    """
    dirs=set(affected_pairs)|{('SVX','NJC'),('NJC','SVX')}
    bundle=common_bundle(flights,scenario,dirs,start,end,demand_overrides,response)
    markets={(x['demand_pool_id'],x['month']):x for x in bundle['markets']}
    by_origin=defaultdict(list)
    for f in flights: by_origin[f['origin_airport']].append(f)
    candidates=defaultdict(list)
    for f in flights:
        if f['destination_airport']!='OMS': continue
        for g in by_origin['OMS']:
            if (f['origin_airport'],g['destination_airport']) not in [('SVX','NJC'),('NJC','SVX')]: continue
            gap=(datetime.fromisoformat(g['departure_utc'].replace('Z','+00:00'))-datetime.fromisoformat(f['arrival_utc'].replace('Z','+00:00'))).total_seconds()/60
            if 60<=gap<=180:
                candidates[(f['origin_airport'],g['destination_airport'],f['departure_utc'][:7])].append((f,g,gap))
    for (a,b,month),cs in sorted(candidates.items()):
        y,m=map(int,month.split('-')); freq=len(cs)*7/calendar.monthrange(y,m)[1]
        gross,net=RE.fare(a,b,scenario)
        market=markets[(RE.P05.pool(a,b),month)]
        durations=[f['block_hours_costscreen']*60+g['block_hours_costscreen']*60+gap for f,g,gap in cs]
        mean=sum(durations)/len(durations)
        weight=RE.mass(a,b,freq,scenario,gross,mean)*math.exp(RE.P05.coefficients(scenario)['stop_penalty'])
        c=RE.P05.coefficients(scenario)
        intercept=math.log(weight)-math.log(len(cs))-c['price_per_rub']*gross-c['time_per_minute']*mean-c['log_frequency']*math.log(freq)
        for (f,g,gap),duration in zip(cs,durations):
            p=RE.P05.product('HUB:'+f['flight_instance_id']+'>'+g['flight_instance_id'],market,'air','RW',
                             gross,duration,freq,[f['flight_instance_id'],g['flight_instance_id']],
                             f['departure_utc'][:10],net,intercept)
            p.update(connection_airport='OMS',MCT_scenario=60,maximum_connection_minutes=180,
                     actual_gap_minutes=gap,one_through_fare=True,
                     assumption_id=p.get('assumption_id','')+';NET-HUB01')
            bundle['products'].append(p)
    return bundle


@contextmanager
def connecting_adapter(enabled):
    # Scope the local adapter to this call; never edit upstream source files.
    old=RE.choice_bundle
    RE.choice_bundle=hub_bundle if enabled else common_bundle
    try: yield
    finally: RE.choice_bundle=old


def evaluate(p_req, k_req, e, s, scenario='base', hub=False, start=START, end=END, response='passive'):
    with connecting_adapter(hub):
        return RE.evaluate_combined_programme([],scenario,keep_patterns=[],start=start,end=end,
                    existing_slots=e,delivery_scenario=s,reserve_available=None,
                    donor_loss=None,omitted_F=None,response=response,
                    calendar_requests={'P':p_req,'KEEP':k_req})


def stats(z, label, year=None):
    fs=z[label]['bundle']['flights']
    if year: fs=[f for f in fs if f['departure_utc'].startswith(str(year))]
    months=[r for r in z[label]['monthly'] if year is None or r['month'].startswith(str(year))]
    ids={f['flight_instance_id'] for f in fs}
    products={p['product_id']:p for p in z[label]['bundle']['products']}
    aa=[a for a in z[label]['allocation']['allocations'] if a['owner']=='RW' and (year is None or a['month'].startswith(str(year)))]
    bymarket=defaultdict(float)
    for a in aa: bymarket[(a['demand_pool_id'],a['month'])]+=a['carried']
    through=sum(a['carried'] for a in aa if len(products[a['product_id']]['legs'])==2)
    ops=z['ops_results']['P' if label=='programme' else 'KEEP']
    days={(r['tail'],r['date']) for r in ops['daily'] if year is None or r['date'].startswith(str(year))}
    return dict(journeys=sum(r['rw_journeys'] for r in months), revenue=sum(r['net_revenue'] for r in months),
                cost=sum(r['known_cost'] for r in months), contribution=sum(r['known_contribution'] for r in months),
                flights=len(fs), hours=sum(f['block_hours_costscreen'] for f in fs), taildays=len(days),dayset=days,
                occupied_segments=sum(a['carried']*len(products[a['product_id']]['legs']) for a in aa),
                through_journeys=through, market_carried=bymarket, ids=ids)


def result_rows(z, programme_id, e, s, scenario, keep_case, policy='fixed'):
    rows=[]
    for year in (2027,2028):
        common=dict(programme=programme_id,year=year,scenario=scenario,support='NS',resource=f'E{e}/{s}',
                    keep_case=keep_case,policy=policy,calendar_basis=MAIN_BASIS,
                    reserve_availability='UNKNOWN_GATE',donor_loss_RUB=None,omitted_F_RUB=None,
                    outside_affected_old_RW_and_MQF_marketed_loss_RUB=None,whole_KEEP_cash_RUB=None,
                    full_incremental_PnL_RUB=None,incremental_cash_RUB=None,dispatch_ready=False)
        if 'programme' not in z:
            rows.append(common|dict(status=z['status'],known_increment_upper_conditional_RUB=None,
                                    full_profit_status='UNKNOWN',failure_reason=z.get('error')))
            continue
        p,k=stats(z,'programme',year),stats(z,'keep',year)
        inc=p['contribution']-k['contribution']; dq=p['journeys']-k['journeys']
        used=p['taildays']; added=len(p['dayset']-k['dayset'])
        cohort_overlap=sum(min(q,k['market_carried'].get(key,0)) for key,q in p['market_carried'].items())
        rows.append(common|dict(status='CONDITIONAL_DIAGNOSTIC_NOT_LAUNCH' if p['flights'] else 'NO_FLIGHTS_AT_THIS_DATED_RESOURCE',
                    P_operated_journeys=p['journeys'],KEEP_operated_journeys=k['journeys'],
                    model_RW_journey_change_not_new_customers=dq,
                    old_journeys_overlap_upper_bound_not_identified_migration=cohort_overlap,
                    unique_new_RW_customers=None,unknown_marketed_Rw_connection_carrier_segments=None,
                    P_occupied_passenger_segments=p['occupied_segments'],P_through_journeys=p['through_journeys'],
                    P_net_revenue_RUB=p['revenue'],KEEP_net_revenue_RUB=k['revenue'],
                    P_known_operating_cost_RUB=p['cost'],KEEP_known_operating_cost_RUB=k['cost'],
                    P_variable_contribution_RUB=p['contribution'],KEEP_variable_contribution_RUB=k['contribution'],
                    known_increment_upper_conditional_RUB=inc,
                    max_F_plus_external_donor_plus_unmodelled_old_RW_loss_RUB=inc,
                    max_same_loss_RUB_per_actual_P_flight_tailday=inc/used if used else None,
                    max_same_loss_RUB_per_incremental_flight_tailday=inc/added if added else None,
                    P_actual_UTC_flight_taildays=used,incremental_UTC_flight_taildays=added,
                    reserve_protected_calendar_days=366 if year==2028 else 365,
                    P_directed_departures=p['flights'],KEEP_directed_departures=k['flights'],
                    P_block_hours=p['hours'],KEEP_block_hours=k['hours'],
                    F_pax_500_650_nonoverlap_stress_increment_RUB=inc-dq*(500 if scenario=='base' else 650),
                    combined_loss_formula='full_delta=known_delta-F-Doutside-LoldRWoutside; included KEEP never deducted twice',
                    payments='unavoidable old payment schedule SAME in P/KEEP; values/timing UNKNOWN',
                    full_profit_status='UNKNOWN_F_DONOR_OLD_RW_CONNECTIONS_TAX_CASH'))
    return rows


def select_focus():
    """8 split policies, same E1/S0 two-year resource; two sensitivity points.
    Selection uses BASE only, keeps CAUTIOUS unchanged, no scenario hindsight.
    """
    rows=[]; tails=resource(1,'S0')
    for split in range(8):
        req=request(programme('D1_FOCUS',tails,split),tails); k=request([],tails)
        for scenario in ['base','cautious']:
            z=evaluate(req,k,1,'S0',scenario)
            row=dict(candidate=f'FOCUS_AER{split}_MRV{7-split}',AER_RT_week=split,MRV_RT_week=7-split,
                     scenario=scenario,resource='E1/S0',period='2027-01-01/2028-12-31',
                     keep='EMPTY_AFFECTED_KEEP_UPPER_CONDITIONAL',global_optimum=False)
            if 'programme' in z:
                row.update(known_delta_RUB=z['known_increment_P_minus_KEEP_before_F_donor'],
                           P_journeys=z['programme']['rw_journeys'],status=MAIN_BASIS)
            rows.append(row)
    winner=max([r for r in rows if r['scenario']=='base'], key=lambda r:(r['known_delta_RUB'],-r['AER_RT_week']))
    for row in rows: row['selected_from_BASE_only']=row['AER_RT_week']==winner['AER_RT_week']
    return winner['AER_RT_week'],rows


def record_calendar(req, name, e, s, side, flights, rotations, resources, routes):
    ops=RE.OPS_CALENDAR.generate(req)
    key=dict(programme=name,resource=f'E{e}/{s}',side=side,block_case=req['block_case'],calendar_basis=MAIN_BASIS)
    for f in ops['flights']:
        dep=datetime.fromisoformat(f['departure_utc']);arr=datetime.fromisoformat(f['arrival_utc'])
        night=dep.hour<6 or dep.hour>=22 or arr.hour<6 or arr.hour>=22
        flights.append(key|f|dict(UTC_night_endpoint_22_06=night,crew='UNKNOWN',payload_AFM='UNKNOWN',
                                 actual_operated=False,tail_release='UNKNOWN_GATE'))
    for r in ops['rotations']: rotations.append(key|r|dict(turn_minutes=TURN))
    for d in RE.days_in(START,END,range(7)):
        ds=d.isoformat(); rows=[r for r in ops['daily'] if r['date']==ds]
        available=sum(not t.get('reserve') and t['available_from'][:10]<=ds for t in req['tails'])
        resources.append(key|dict(date=ds,N_working=available,used_working_tails=len(rows),
                        block_hours=sum(r['block_hours'] for r in rows),cycles=sum(r['cycles'] for r in rows),
                        protected_reserves=len(ops['reserve']),reserve_contract='UNKNOWN',
                        position_overlap_entry_block_status=ops['status'],crew='UNKNOWN',MRO='UNKNOWN',
                        slots_AFM_route_payload='UNKNOWN',tail_day_basis='actual assigned UTC flight dates, never BH/8',
                        initial_location='SVX_CONDITIONAL_RELEASE_AT_THIS_LOCATION; ferry if not met UNKNOWN',
                        errors='|'.join(ops['errors'][:10])))
    counts=Counter((f['origin'],f['destination'],f['departure_utc'][:7]) for f in ops['flights'])
    for (a,b,m),n in sorted(counts.items()):
        routes.append(key|dict(month=m,origin=a,destination=b,dated_departures=n,
                              calendar_effective_frequency=n*7/calendar.monthrange(int(m[:4]),int(m[5:]))[1],
                              average_frequency_is_not_observed=True))
    return ops


def record_months(z,name,e,s,scenario,keep_case,monthly,connections):
    if 'programme' not in z: return
    p={r['month']:r for r in z['programme']['monthly']}; k={r['month']:r for r in z['keep']['monthly']}
    for m in MONTHS:
        pp=p.get(m,{});kk=k.get(m,{})
        dr=[r for r in z['ops_results']['P']['monthly'] if r['month']==m]
        ro=[r for r in z['ops_results']['P']['rotations'] if '/'+m in r['rotation_id']]
        monthly.append(dict(programme=name,resource=f'E{e}/{s}',scenario=scenario,support='NS',keep_case=keep_case,month=m,
                P_departures=pp.get('directed_departures',0),KEEP_departures=kk.get('directed_departures',0),
                P_journeys=pp.get('rw_journeys',0),KEEP_journeys=kk.get('rw_journeys',0),
                model_journey_change_not_unique_customers=pp.get('rw_journeys',0)-kk.get('rw_journeys',0),
                P_net_revenue_RUB=pp.get('net_revenue',0),KEEP_net_revenue_RUB=kk.get('net_revenue',0),
                P_known_cost_RUB=pp.get('known_cost',0),KEEP_known_cost_RUB=kk.get('known_cost',0),
                known_increment_upper_conditional_RUB=pp.get('known_contribution',0)-kk.get('known_contribution',0),
                P_block_hours=sum(x['block_hours'] for x in dr),P_cycles=sum(x['cycles'] for x in dr),
                P_elapsed_rotation_hours=sum(x['elapsed_minutes'] for x in ro)/60,
                full_incremental_PnL_RUB=None,monthly_cash_RUB=None,crew='UNKNOWN',reserve='UNKNOWN_GATE',
                delivery_use='ONLY_AFTER_COMMON_ENTRY',support_route_RUB=0,support_fuel_RUB=0))
    for label in ['programme','keep']:
        ps={x['product_id']:x for x in z[label]['bundle']['products']}
        for a in z[label]['allocation']['allocations']:
            pr=ps[a['product_id']]
            if pr['product_id'].startswith('HUB:'):
                connections.append(dict(programme=name,resource=f'E{e}/{s}',scenario=scenario,keep_case=keep_case,side=label,
                    product_id=pr['product_id'],month=pr['month'],pool=pr['demand_pool_id'],
                    legs=pr['legs'],MCT_minutes=60,maximum_connection_minutes=180,
                    actual_gap_minutes=pr['actual_gap_minutes'],carried_journeys=a['carried'],
                    one_through_gross_fare=pr['gross_fare'],one_through_net_fare=pr['net_fare'],
                    net_revenue_once=a['carried']*pr['net_fare'],shared_physical_inventory=True))


def assemble():
    split,search=select_focus()
    table('joint_search.csv',search)
    print('finite search selected split',split,flush=True)
    comparisons=[]; monthly=[]; flights=[]; rotations=[]; resources=[]; routes=[]; connections=[]; checks=[]
    for e in (0,1,2):
        for s in ('S0','S1','S1D6'):
            tails=resource(e,s)
            for name in DIRECTS+[HUB]:
                p=request(programme(name,tails,split),tails);k=request([],tails)
                file=f'requests/{name}_E{e}_{s}.json'
                dump(file,dict(P=p,KEEP=k,resource_release='UNKNOWN_CONDITIONAL',
                               policy='predeclared N(t) mapping; base and cautious same physical flights'))
                record_calendar(p,name,e,s,'P',flights,rotations,resources,routes)
                for scenario in ('base','cautious'):
                    z=evaluate(p,k,e,s,scenario,hub=name==HUB)
                    rr=result_rows(z,name,e,s,scenario,'EMPTY_AFFECTED_KEEP_UPPER_CONDITIONAL')
                    comparisons.extend(rr)
                    record_months(z,name,e,s,scenario,'EMPTY_AFFECTED_KEEP_UPPER_CONDITIONAL',monthly,connections)
                    checks.append(dict(programme=name,resource=f'E{e}/{s}',scenario=scenario,
                                       result_status=z['status'],violations=z.get('daily_block_violations',[]),
                                       seats_ok=all(x['carried_segments']+x['unfilled_contract_seats']<=x['saleable_seats']+1e-6 for lab in ['programme','keep'] for x in z.get(lab,{}).get('allocation',{}).get('seats',[]))))
                    if name==HUB:
                        identity=dict(z,programme=z['keep'],ops_results={'P':z['ops_results']['KEEP'],'KEEP':z['ops_results']['KEEP']})
                        comparisons.extend(result_rows(identity,'KEEP',e,s,scenario,'EMPTY_AFFECTED_KEEP_UPPER_CONDITIONAL'))
            print('assembled',f'E{e}/{s}',flush=True)
    # A nonempty common affected KEEP for every alternative, SAME payments/resources.
    e,s=2,'S0'; tails=resource(e,s); control=request(old_programme(tails,2,True),tails)
    dump('requests/COMMON_AFFECTED_KEEP_E2_S0.json',control)
    record_calendar(control,'COMMON_AFFECTED_KEEP',e,s,'KEEP',flights,rotations,resources,routes)
    for name in DIRECTS+[HUB]:
        p=request(programme(name,tails,split),tails)
        for scenario in ('base','cautious'):
            z=evaluate(p,control,e,s,scenario,hub=True)
            comparisons.extend(result_rows(z,name,e,s,scenario,'CONTROL_2AER_2MRV_2OMS_REPLACED'))
            record_months(z,name,e,s,scenario,'CONTROL_2AER_2MRV_2OMS_REPLACED',monthly,connections)
            if name==HUB:
                identity=dict(z,programme=z['keep'],ops_results={'P':z['ops_results']['KEEP'],'KEEP':z['ops_results']['KEEP']})
                comparisons.extend(result_rows(identity,'KEEP',e,s,scenario,'CONTROL_2AER_2MRV_2OMS_REPLACED'))
    # Existing frequencies are sensitivity points, not observations; both legs paid.
    sensitivity=[]
    p=request(programme('D3_STAGED',tails,split),tails)
    for f in (0,1,2,4,7):
        k=request(old_programme(tails,f),tails)
        for scenario in ('base','cautious'):
            z=evaluate(p,k,e,s,scenario)
            for row in result_rows(z,'D3_STAGED',e,s,scenario,f'OLD_NONSTOP_{f}_EACH_PAIR'):
                row['old_frequency_each_pair_per_week']=f
                row['old_marketed_connection_loss_still_UNKNOWN']=True
                sensitivity.append(row)
    table('old_RW_sensitivity.csv',sensitivity)
    response_rows=[]
    for name in DIRECTS+[HUB]:
        p=request(programme(name,tails,split),tails)
        for scenario in ('base','cautious'):
            z=evaluate(p,control,2,'S0',scenario,hub=True,response='price_match10')
            for r in result_rows(z,name,2,'S0',scenario,'CONTROL_2AER_2MRV_2OMS_REPLACED'):
                response_rows.append(r|dict(response='price_match10_unbounded_other_air_composite_scenario',calibrated=False))
    table('competitor_response_stress.csv',response_rows)
    # High block stress is explicitly separate from base/cautious fixed calendars.
    high=[]
    for name in DIRECTS+[HUB]:
        ts=resource(2,'S1');p=request(programme(name,ts,split),ts,'high');k=request([],ts,'high')
        z=evaluate(p,k,2,'S1','base',hub=name==HUB)
        high.append(dict(programme=name,resource='E2/S1',block_case='high',status=z['status'],
                         known_delta=z['known_increment_P_minus_KEEP_before_F_donor'],
                         errors=z['ops_results']['P']['errors'][:12],
                         interpretation='uncalibrated +15% diagnostic only; not evidence every direct route fails'))
    dump('block_stress.json',high)
    # Deterministic post-observation rule, no perfect hindsight composition switch.
    adaptive=[]
    for name in DIRECTS:
        for scenario in ('base','cautious'):
            ms=[r for r in monthly if r['programme']==name and r['resource']=='E1/S0' and r['scenario']==scenario and r['keep_case']=='EMPTY_AFFECTED_KEEP_UPPER_CONDITIONAL']
            first=[r for r in ms if r['month']<='2027-03']
            subtotal=sum(r['known_increment_upper_conditional_RUB'] for r in first)
            used=sum(1 for r in resources if r['programme']==name and r['resource']=='E1/S0' and r['date']<='2027-03-31' and r['used_working_tails'])
            margin=subtotal/used if used else None
            # Proxy illustration requires F/D/L<=headroom; real decision uses observed net margin.
            hold=margin is not None and margin>=50000
            adaptive.append(dict(programme=name,scenario=scenario,resource='E1/S0',decision_date='2027-04-01',
                fixed_rule='retain/expand only if trailing 3 months observed net operating increment > donor net contribution + 50000 RUB per occupied flight tailday; all ops/KEEP gates satisfied',
                proxy_base_cautious_omitted_costs_zero_ONLY_FOR_RULE_ILLUSTRATION=True,
                Q1_known_headroom_per_actual_flight_tailday=margin,
                illustrative_branch='CONTINUE_FIXED' if hold else 'STOP_ADDITIONS_RETURN_TO_KEEP_FROM_APRIL',
                illustrative_2027_variable_delta_RUB=sum(r['known_increment_upper_conditional_RUB'] for r in ms if r['month'].startswith('2027') and (hold or r['month']<='2027-03')),
                illustrative_2028_variable_delta_RUB=sum(r['known_increment_upper_conditional_RUB'] for r in ms if r['month'].startswith('2028')) if hold else 0,
                full_policy_delta_RUB=None,termination_reactivation_costs=None,actual_decision='UNKNOWN_OBSERVED_MARGIN_REQUIRED'))
    table('adaptive_policy.csv',adaptive)
    table('network_comparison.csv',comparisons)
    table('monthly_results.csv',monthly)
    table('dated_flights.csv',flights)
    table('rotations.csv',rotations)
    table('resource_checks.csv',resources)
    table('route_lists.csv',routes)
    table('dated_connections.csv',connections)
    dump('joint_allocation_checks.json',checks)
    calendar_bridge=[]
    for e in (0,1,2):
        for s in ('S0','S1','S1D6'):
            for name in DIRECTS+[HUB]:
                ps=programme(name,resource(e,s),split)
                for yr in (2027,2028):
                    weighted=Counter()
                    for p in ps:
                        lo=max(p['start'],f'{yr}-01-01');hi=min(p['end'],f'{yr}-12-31')
                        if lo>hi: continue
                        span=(date.fromisoformat(hi)-date.fromisoformat(lo)).days+1
                        for a,b in zip(p['path'],p['path'][1:]):
                            weighted[(a,b)]+=p['frequency_per_week']*span/(366 if yr==2028 else 365)
                    for (a,b),avg in sorted(weighted.items()):
                        actual=sum(r['dated_departures'] for r in routes if r['programme']==name and r['resource']==f'E{e}/{s}' and r['origin']==a and r['destination']==b and r['month'].startswith(str(yr)))
                        calendar_bridge.append(dict(programme=name,resource=f'E{e}/{s}',year=yr,origin=a,destination=b,
                            actual_dated_departures=actual,exposure_weighted_weekly_frequency=avg,
                            diagnostic_52_week_departures=avg*52,diagnostic_48_week_departures=avg*48,
                            actual_minus_52=actual-avg*52,actual_minus_48=actual-avg*48,
                            year_days=366 if yr==2028 else 365,
                            interpretation='52/48 diagnostic weighted templates only; economics uses actual dated departures and returns'))
    table('calendar_52_48_bridge.csv',calendar_bridge)
    matched=[]
    for r in comparisons:
        if r['programme']!=HUB: continue
        for name in DIRECTS:
            d=next(x for x in comparisons if x['programme']==name and all(x[k]==r[k] for k in ('resource','year','scenario','keep_case','policy')))
            advantage=d['known_increment_upper_conditional_RUB']-r['known_increment_upper_conditional_RUB']
            matched.append({k:r[k] for k in ['resource','year','scenario','keep_case']}|dict(
                direct=name,hub=HUB,direct_known_delta_RUB=d['known_increment_upper_conditional_RUB'],
                hub_known_delta_RUB=r['known_increment_upper_conditional_RUB'],direct_minus_hub_RUB=advantage,
                direct_taildays=d['P_actual_UTC_flight_taildays'],hub_taildays=r['P_actual_UTC_flight_taildays'],
                ranking_flip_extra_loss_on_current_winner_RUB=abs(advantage),
                flip_per_actual_winner_flight_tailday_RUB=abs(advantage)/(d['P_actual_UTC_flight_taildays'] if advantage>=0 else r['P_actual_UTC_flight_taildays']) if (d['P_actual_UTC_flight_taildays'] if advantage>=0 else r['P_actual_UTC_flight_taildays']) else None,
                full_profit_ranking='UNKNOWN_DIFFERENTIAL_F_DONOR_OLD_RW_LOSS',same_N_t=True,
                same_calendar_costs_OD_choice=True,scope='finite diagnostic matched programme, not author +503'))
    table('matched_hub_comparison.csv',matched)
    ranking=[]
    for resource_id in sorted({r['resource'] for r in comparisons}):
        for year in (2027,2028):
            for sc in ('base','cautious'):
                for kc in sorted({r['keep_case'] for r in comparisons if r['resource']==resource_id}):
                    rr=sorted([r for r in comparisons if r['resource']==resource_id and r['year']==year and r['scenario']==sc and r['keep_case']==kc],key=lambda r:(-r['known_increment_upper_conditional_RUB'],r['programme']))
                    for i,w in enumerate(rr):
                        for l in rr[i+1:]:
                            gap=w['known_increment_upper_conditional_RUB']-l['known_increment_upper_conditional_RUB']
                            ranking.append(dict(resource=resource_id,year=year,scenario=sc,keep_case=kc,
                                conditional_winner=w['programme'],comparator=l['programme'],
                                max_differential_F_donor_old_RW_loss_before_ranking_reversal_RUB=gap,
                                per_actual_winner_P_flight_tailday_RUB=gap/w['P_actual_UTC_flight_taildays'] if w['P_actual_UTC_flight_taildays'] else None,
                                winner_flight_taildays=w['P_actual_UTC_flight_taildays'],
                                loss_basis='extra net F+external donor+unmodelled old RW loss of winner minus comparator; common costs cancel only if actually same',
                                full_profit_rank='UNKNOWN'))
    table('ranking_thresholds.csv',ranking)
    # Preserve full references unchanged and never bring their money into small shells.
    reflegs=read(ROOT/'ops_inputs/reference_physical_legs.csv')
    table('author_fixed_reference_legs.csv',reflegs)
    refs=read(ROOT/'ops_inputs/reference_feasibility.csv')
    table('author_fixed_reference_checks.csv',[x|dict(full_incremental_profit_RUB=None,full_cash_RUB=None,
                 resize=False,old_plus44_plus503_compatibility='NOT_RECALCULATED_NOT_COMPARABLE_TO_P05_NEW_NET') for x in refs])
    definitions=dict(version=VERSION,status='COMPLETED_CONDITIONAL_DIAGNOSTIC_ASSEMBLY',period=[START,END],
        finite_search={'candidate_count':8,'grid':'AER 0..7 and MRV=7-AER RT/week on one working tail; same full dated two-year horizon',
                       'selection':'highest BASE two-year joint delta; CAUTIOUS same composition; ties prefer fewer AER',
                       'selected_AER_RT_week':split,'selected_MRV_RT_week':7-split,
                       'further_compared':'3 predefined direct policies + one miniature OMS hub, 9 resource cases, 2 fixed sensitivities; high block and response separate',
                       'not_searched':'global airport/network/fleet optimisation, fares, all day/times, actual competitor schedules or legal crew rosters'},
        calendars={'route_adapter_Monday':0,'ops_ISO_Monday':1,'turn_minutes':TURN,'block_basis':MAIN_BASIS,
                   'high_block':'separate +15% uncalibrated diagnostic, not base/cautious change',
                   'annual_count':'actual departures/returns Jan1-Dec31; 365/366 dates, not 52/48 multipliers'},
        resource={'E':[0,1,2],'S':RE.CONTRACT['resource']['deliveries'],'reserve':'ONE separate RES-1; actual contract UNKNOWN; never working',
                  'same_N_for_all':True,'initial_position':'conditional SVX release for every working tail in all alternatives; otherwise funded ferry gate',
                  'SJ100':'no pre-entry work/reserve; RRJ cost/block transfer is UNKNOWN, NOT CaseSJ approved',
                  'donor':'one initially identical external pending donor scenario per working/reserve slot, actual loss NULL'},
        programmes={
            'D1_FOCUS':{'one_tail':'selected split, every weekday, ordinary RT; extra tails idle','stage':'start only after launch gates; S0 possible with E>=1'},
            'D2_SEASONAL':{'one_tail':'May-Oct AER7; Nov-Apr MRV5 + KJA2 on complementary ISO weekdays','stage':'seasonal donor replacement; extra tails idle; KJA blocks and prior KEEP unresolved'},
            'D3_STAGED':{'N0':'no flights','N1':'same selected focus split','N2':'AER7 + MRV7','N3plus':'add KJA2, fourth slot idle',
                         'stage':'new capacity at common entry only; no inferred free existing tail'},
            HUB:{'N0':'no flights','N1':'SVX-OMS-NJC-OMS-SVX Mon/Wed/Fri','N2plus':'second identical bank Tue/Thu/Sat; extra tails idle',
                 'MCT':'60 min; max180; dated ordered legs only; Jan1-3 no banks',
                 'fare':'one P05 endpoint gross/net per SVX<>NJC journey, stops penalty; shares seats with locals',
                 'limitations':'minimal P06 adapter; own feeder connections, interline rights, calibrated transfer demand, misconnect/accommodation/cash UNKNOWN'}},
        KEEP={'main':'EXPLICIT EMPTY affected scope, UPPER CONDITIONAL; whole future business UNKNOWN, not zero',
              'common_control':'2 AER + 2 MRV + 2 OMS weekly RT on E2/S0; SAME unavoidable payments; all proposals replace this scope, external donor separate',
              'old_frequency_sensitivity':'0/1/2/4/7 each AER/MRV on E2/S0, not observed; marketed MQF loss outside scope NULL',
              'loss_formula':'Delta=joint(P-KEEP)-F-Dexternal-LoldRWoutside. Never deduct any included KEEP sale twice.',
              'MQF':'marketed RW connecting description only; operating carrier of each leg UNKNOWN; no claim two RW operated legs'},
        support={'NS':{'route_grant':0,'fuel_credit':0},'CM':'NULL until eligibility/operator/route/date/fare/award and tax volume/payment; coupled choice/fare recalculation required',
                 'historical32930':'diagnostic only, no future receipt; 185228 not a signed contract'},
        maturity={'conditional_route_list':['AER-SVX','MRV-SVX','KJA-SVX','CEK-MRV','MRV-TJM','KUF-MRV','KUF-SVX','OMS-UFA','IKT-SVX','SVX-VVO'],
                  'admission':'10 research gates, not 10 launch routes; last two require different multiday/type/payload design; KUF/GOJ negatives not preferred',
                  'triangles':'not admitted in pilot: no positive cautious incremental adjacent third-OD plus paired variant/blocks; triangle screen retained upstream'},
        new_observed_numeric_updates=0, full_PnL=None, cash=None, global_optimum=False)
    dump('network_definitions.json',definitions)
    gates_and_sources(comparisons,split)
    write_readme(comparisons,matched,search,split)
    build_manifest()


def gates_and_sources(comparison,split):
    gates=[]
    for name in DIRECTS+[HUB]:
        for scenario in ['base','cautious']:
            for year in [2027,2028]:
                r=next(r for r in comparison if r['programme']==name and r['resource']=='E2/S0' and r['scenario']==scenario and r['year']==year and r['keep_case']=='CONTROL_2AER_2MRV_2OMS_REPLACED')
                inc=r['known_increment_upper_conditional_RUB']; rev=r['P_net_revenue_RUB']-r['KEEP_net_revenue_RUB']; dq=r['model_RW_journey_change_not_new_customers']
                gates.append(dict(programme=name,year=year,scenario=scenario,resource='E2/S0',
                    closest_launch_state='CONDITIONAL_NOT_APPROVED',gate='JOINT_COMMERCIAL_AND_LOSS_BUDGET',
                    threshold_RUB=inc,threshold_per_actual_P_flight_tailday=r['max_same_loss_RUB_per_actual_P_flight_tailday'],
                    max_outside_old_RW_loss_given_F_D='LoldRWoutside <= threshold - F - Doutside; included KEEP already subtracted',
                    same_choice_net_revenue_scale_for_break_even=r['P_known_operating_cost_RUB']/(r['P_net_revenue_RUB']) if r['P_net_revenue_RUB'] else None,
                    scale_is='algebraic fixed-allocation cost threshold ONLY; changing fares requires P06 choice rerun',
                    max_nonoverlap_F_pax_RUB_per_model_incremental_journey=inc/dq if dq>0 else None,
                    q_net_yield_gate='sum(P dated carried*P net)-sum(KEEP dated carried*KEEP net) >= incremental known cost + F + Dexternal + LoldRWoutside; P06 shared seats and OD must be rerun',
                    measured_OD_yield_contracts='UNKNOWN',crew_MRO_slots_AFM_reserve='UNKNOWN'))
        for gate in ['ACTUAL_RELEASE_AND_DONOR','ONE_PROTECTED_RESERVE','DATED_KEEP_NONSTOP_AND_MARKETED_MQF',
                     'PAIRED_DIRECTION_SEASON_VARIANT_BLOCKS','AFM_ROUTE_PAYLOAD_AIRPORT_RIGHTS','CREW_DUTY_REST_AND_MRO',
                     'NET_YIELD_COST_TAX_COMPONENT_BRIDGE','CASH_AND_UNAVOIDABLE_PAYMENT_DATES']:
            gates.append(dict(programme=name,gate=gate,closest_launch_state='UNKNOWN_REQUIRED',threshold_RUB=None,
                              condition='signed/date-specific evidence; unknown is not free or zero'))
    gates.append(dict(programme='D3_STAGED',gate='EXPANSION_POLICY',closest_launch_state='WAIT_FOR_OBSERVATION',
        condition='3 consecutive observed months: operating increment after all nonoverlap costs and old RW loss per actual donor flight tailday > donor net contribution/tailday + 50000 RUB; at least 50 occupied flight taildays and all ops gates. Expand only at common SJ entry. No LF-only rule.',threshold_RUB=50000))
    table('launch_gates.csv',gates)
    route_gates=[]
    for scenario in ('base','cautious'):
        for a,b in [('SVX','AER'),('SVX','MRV'),('SVX','KJA')]:
            selected=[x for x in blocks() if {x['origin'],x['destination']}=={a,b}]
            gross,net=RE.fare(a,b,scenario)
            cost=sum(RE.costs(x['origin'],x['destination'],scenario,x['nominal_minutes']/60)['fixed_cost'] for x in selected)
            route_gates.append(dict(pair=RE.pid(a,b),scenario=scenario,nominal_diagnostic_roundtrip_cost_RUB=cost,
                gross_scenario_fare_RUB=gross,net_scenario_fare_RUB=net,
                minimum_paid_endpoint_journeys_sum_two_legs_before_affected_KEEP_F_donor_old_RW_loss=cost/net,
                symmetric_minimum_paid_journeys_each_leg_before_affected_KEEP_F_donor_old_RW_loss=cost/(2*net),
                q_net_yield_gate='qAB*yAB + qBA*yBA - affected_KEEP_net_revenue + avoided_KEEP_cost >= roundtrip_cost + F + Dexternal + LoldRWoutside',
                unknown_cost_headroom_at_100_each_leg_RUB=200*net-cost,
                capacity_per_leg=100,observed_q=None,observed_net_yield=None,
                interpretation='necessary conditional cost/yield gate, not LF forecast or sufficient demand proof; shared monthly choice must support q; block/variant still UNKNOWN'))
    table('route_launch_thresholds.csv',route_gates)
    requests=[
        ('R01','RW revenue management','dated marketed AND operated itineraries, coupons/legs, carrier IDs, net sales, avoidable costs, spill and current frequency for AER/MRV/KJA/OMS; MQF products explicitly','unknown affected old RW loss / no double deduction'),
        ('R02','RW fleet/operations','registered working tail and separate reserve, dates/location, committed donor assignments and unavoidable payments, actual donor contribution per occupied flight tailday','E0/E1/E2 not free published stock'),
        ('R03','RW dispatch','both directed seasonal block distributions by exact variant, route/alternate/fuel/payload/AFM/runway/rights and slot confirmations','all diagnostic calendars'),
        ('R04','RW crew/MRO','dated crew identities, report/release, qualifications, cumulative hours/rest, approved MRO and maintenance windows','8 BH is not crew law'),
        ('R05','RW commercial','directional endpoint monthly OD, connecting unique journeys vs segments, actual fare/baggage/refund/VAT/distribution/acquiring bridge and competitors','no capture calibration'),
        ('R06','RW finance','future delivered fuel/ground/deice/crew/MRO/nav/lease/reserve/base/positioning/startup/exit contracts, invoices tax timing and cash baseline','full PnL and cash NULL'),
        ('R07','RW aircraft induction','actual SJ100 delivery and certified entry, PD8 applicable costs/blocks/payload, training/spares/crew/reserve','S1/S1D6 illustrative not forecast'),
        ('R08','RW hub commercial/ops','OMS dated connecting rights, minimum connection, ticket/tariff, baggage/misconnect costs and cohort OD','matched miniature hub not author full network'),
        ('R09','RW legal/finance','CM signed award and special fare/period/eligible flights, fuel taxpayer volume/credit dates','support not assumed received'),
    ]
    table('RW_data_request.csv',[dict(id=i,owner=o,request=q,decision=d,priority='LAUNCH_BLOCKER',value=None) for i,o,q,d in requests])
    src=read(ROOT/'source_review/source_admission.csv')
    table('source_admission.csv',[dict(id=f'CANONICAL-{i+1}',source_file='source_review/source_admission.csv',canonical_record=x,
          numeric_update=0,use='binding metadata admission; canonical copies supersede raw') for i,x in enumerate(src)]+[
        dict(id='WIN-AER',source_file='winner_evidence/own_RW_service.csv;coordinator/winner_primary_check.md',
             URL='https://flyredwings.com/directions/ekaterinburg/sochi/',checked='2026-11-12',
             supports='marketed route page; 3h30 reference',does_not_support='date/frequency/reverse block/operating actual; no paired block admission',numeric_update=0),
        dict(id='WIN-MRV',source_file='winner_evidence/model_admission.csv;coordinator/winner_primary_check.md',
             URL='https://flyredwings.com/directions/ekaterinburg/mineralniye-vody/',checked='2026-11-12',
             supports='page describes marketed connection via MQF',does_not_support='absence of direct; identity of operating carriers/own two legs; zero KEEP',numeric_update=0),
        dict(id='WIN-SEGMENTS',source_file='winner_evidence/README.md',supports='785k/211k old summary bidirectional airport segments, primary locator not recovered',
             does_not_support='2027 endpoint OD or new RW customers; never added to prior',numeric_update=0),
        dict(id='NET-BLOCK',source_file='route_economics/calculate.py;ops_inputs/directed_blocks.csv',supports='explicit geometry diagnostic dates only',
             does_not_support='paired published variant dispatch blocks; current reserve; actual operation',numeric_update=0)])
    changes=[
        ('NET-A01','60min turn common to all; P03 default45','conservative uncalibrated scenario; permits explicit OMS MCT60, not regulatory min'),
        ('NET-A02','ceil legacy geometry minute nominal; ceil(nominal*1.15) high','separate diagnostic plan; missing real pair blocks are still launch gates'),
        ('NET-A03','all initially released working tails at SVX, conditional','same external initial location; if false, paid ferry cannot be omitted'),
        ('NET-A04','main empty affected KEEP only upper conditional; common nonempty control plus old frequency grid','whole KEEP and marketed MQF sales unresolved; external loss NULL'),
        ('NET-A05','no nonoverlap pax500/650 in main subtotal','distribution already in net; stress only, component bridge required'),
        ('NET-HUB01','OMS/SVX/NJC 60..180min two-leg dated adapter; endpoint fare once','minimal compatible model, shared inventory; not full author hub or interline approval'),
        ('NET-A06','fixed BASE-selected split; cautious uses identical dates','no scenario-specific hindsight; separate observed margin policy'),
        ('NET-A07','full F + external donor + unmodelled old RW loss remain NULL','headroom is budget for their sum, not profit, including current marketed connections'),
        ('NET-A08','constant RUB2026; no inflation or FX fabricated','2027/28 figures are conditional comparison, not cash forecast'),
    ]
    table('assumption_changes.csv',[dict(id=i,change=c,limitation=l) for i,c,l in changes])
    appendix=[
        dict(mechanism='PARTNER_BLOCK',main_profit_RUB=None,threshold='q*b + handling + F <= sold*(net retail fare-agent fees); sold<=q, release/time/rights and own-cohort overlap gates',market_share='agent journeys separate; never RW operated passenger share',conditions='signed supplier and buyer; dates, refund, sell-through and capacity rights UNKNOWN'),
        dict(mechanism='CARGO',main_profit_RUB=None,threshold='cargo net yield*kg >= fuel payload penalty + handling + F; kg<=min(residual payload, volume constraint)',market_share='cargo separate',conditions='4200kg is compartment design, not residual after baggage; no signed shipper demand'),
        dict(mechanism='CLOSED_COHORT',main_profit_RUB=None,threshold='guaranteed net payment >= known cost + F + donor + old RW loss - nonoverlapping retail net revenue',market_share='same shared OD and seats, not extra demand by declaration',conditions='cohort overlaps removed; actual contract UNKNOWN'),
        dict(mechanism='INTERNATIONAL',main_profit_RUB=None,threshold='joint net revenue in explicit FX scenario >= all costs + border/handling + F + donor + old RW loss',conditions='canonical source gates, slots/rights/FX/visa and aircraft unknown; SVX-BRU identity unresolved'),
        dict(mechanism='NEW_TYPES',main_profit_RUB=None,threshold='net contribution uplift > lease + induction + reserve + crew/MRO + opportunity loss',conditions='no free Tu214/B777; no dated approved resource. SJ100 already conditional entry only'),
        dict(mechanism='CM',main_profit_RUB=None,threshold='recompute choice at eligible special fare; net eligible grant + fuelcredit once >= NS deficit + extra compliance costs',conditions='no automatic 185228 grant; actual award/fuel taxpayer/volumes/dates UNKNOWN'),
        dict(mechanism='HIST32930_DIAGNOSTIC',main_profit_RUB=None,threshold='diagnostic uplift=eligible consumed fuel_t*32930; not used in ranked main nets',conditions='historical average only, not future bound or paid support'),
    ]
    table('supplemental_appendix.csv',appendix)


def write_readme(comparison,matched,search,split):
    main=[r for r in comparison if r['resource']=='E2/S0' and r['keep_case']=='CONTROL_2AER_2MRV_2OMS_REPLACED']
    lines=[]
    for name in DIRECTS+[HUB,'KEEP']:
        rr=[next(r for r in main if r['programme']==name and r['scenario']==sc and r['year']==yr) for sc,yr in [('base',2027),('base',2028),('cautious',2027),('cautious',2028)]]
        lines.append('| '+name+' | '+' | '.join(f"{r['known_increment_upper_conditional_RUB']/1e6:.1f}" for r in rr)+' |')
    winner=max([r for r in main if r['scenario']=='base' and r['year']==2027],key=lambda r:r['known_increment_upper_conditional_RUB'])
    best=[]
    for res in [f'E{e}/{s}' for e in [0,1,2] for s in ['S0','S1','S1D6']]:
        for kc in sorted({r['keep_case'] for r in comparison if r['resource']==res}):
            for yr in (2027,2028):
                for sc in ('base','cautious'):
                    best.append(max([r for r in comparison if r['resource']==res and r['year']==yr and r['scenario']==sc and r['keep_case']==kc],key=lambda r:(r['known_increment_upper_conditional_RUB'],r['programme']=='KEEP')))
    table('best_checked_programmes.csv',best)
    upper={yr:max([r for r in best if r['year']==yr and r['scenario']=='base' and r['keep_case']=='EMPTY_AFFECTED_KEEP_UPPER_CONDITIONAL'],key=lambda r:r['known_increment_upper_conditional_RUB']) for yr in (2027,2028)}
    dump('result_summary.json',dict(status='COMPLETED_CONDITIONAL_DIAGNOSTIC_NOT_LAUNCH',
        comparison_scope='4 finite policies on E2/S0 with common nonempty affected KEEP; main full profits UNKNOWN',
        maximum_2027_BASE_common_control=winner,maximum_by_resource_year_and_KEEP_case=best,
        upper_conditional_maximum_by_year=upper,
        production_ready=False,missing='paired blocks + actual old nonstop/marketed connections + reserve/donor/crew/MRO/tax/contracts/cash'))
    (HERE/'README.md').write_text(f'''# Сборка прямых сетей, 12.11.2026

**Среди четырёх проверенных политик при E2/S0 и одинаковом непустом affected KEEP лучший BASE-2027 — {winner['programme']}: {winner['known_increment_upper_conditional_RUB']/1e6:.1f} млн RUB условного дополнительного переменного результата.** Это верхний условный subtotal до F, внешнего донора и неучтённой потери прежних RW-маркетируемых продаж. Полная дополнительная прибыль и cash **NULL**. Запуск не доказан. Ни одна новая частота/OD/реализованный netyield/контракт не получены. Отрицательный cautious не доказывает неработоспособность всех direct: исходные choice, gross→net, competitor composite и перенос затрат не калиброваны.

| Программа | BASE 2027, млн | BASE 2028, млн | CAUTIOUS 2027, млн | CAUTIOUS 2028, млн |
|---|---:|---:|---:|---:|
{chr(10).join(lines)}

Среди всех девяти условных оболочек максимальный **upper-case с пустым affected KEEP**: в2027 {upper[2027]['programme']} / {upper[2027]['resource']} — {upper[2027]['known_increment_upper_conditional_RUB']/1e6:.1f} млн; в2028 {upper[2028]['programme']} / {upper[2028]['resource']} — {upper[2028]['known_increment_upper_conditional_RUB']/1e6:.1f} млн. Эти суммы не являются доказанным приростом RW: прежние nonstop/marketed продажи, F и донор неизвестны. Все максимумы при фиксированных E/S/KEEP-case, включая выбор сохранить KEEP, — `best_checked_programmes.csv`.

Это **совместный** пересчёт `evaluate_combined_programme` и pinned P06, а не сумма solo. Контроль — условные 2 RT/нед. AER, 2 MRV и 2 OMS на E2/S0. Все P заменяют тот же affected scope; одинаковые неизбежные старые платежи остаются в обеих сторонах. Донор снаружи scope не входит в переменный frontier и остаётся неизвестным. Старая OMS2 — перенос исторического snapshot как сценарий, AER/MRV2 — sensitivity, не факты будущего KEEP. KEEP как действие «без изменения» имеет относительную переменную добавку0; это не нулевой полный бизнес KEEP. Он выигрывает в отрицательных cautious случаях.

## Конкретные программы и этапы

- **D1_FOCUS:** обычные обороты SVX–AER {split}/нед. и SVX–MRV {7-split}/нед. на одном условно высвобождённом рабочем борте. Дополнительные слоты остаются незанятыми. Выбран из восьми split-политик по BASE за оба года; cautious сохраняет те же даты. Начало только после коммерческих и эксплуатационных gates.
- **D2_SEASONAL:** май–октябрь AER7; ноябрь–апрель MRV5 + KJA2 на разных днях одного борта. Это отдельная сезонная замена донора. Лишние слоты не заполняются слабыми парами; оба направления каждого оборота оплачены.
- **D3_STAGED:** N=0 — нет рейсов; N=1 — D1; N≥2 — ежедневные AER и MRV на разных бортах; N≥3 — KJA2 на третьем. Четвёртый слот не используется. Рост только при наблюдённом net operating increment на фактический donor flight-tailday выше вклада донора +50 тыс. RUB минимум три месяца/50 taildays и пройденных gates. LF сам по себе не условие расширения.

E0/E1/E2 означают 0/1/2 условных существующих рабочих слота, **не свободный опубликованный парк**. RES-1 один отдельный защищённый резерв с собственным неизвестным донором. Везде одна функция N(t), одинаковые начальное местоположение SVX и pending-donor scenario. Если выпуск в SVX не подтверждён, нужен оплаченный датированный ferry: сейчас это gate, не утверждение бесплатного перегона. Полезный запуск на S0 требует E≥1 плюс резерв. E0/S0 даёт нулевую добавку физически, а не свободный самолёт.

S1: SJ-A delivery01.07.2027/entry01.08.2027; SJ-B01.10/01.11.2027. S1D6: entry01.02 и01.05.2028; S0 — без новых поставок. Это сценарии, не прогноз. Нет SJ в работе/резерве/перегоне до entry; даты ввода не означают сертифицированную готовность. PD8 и RRJ blocks/ставки не взаимозаменяемы автоматически. Пересчёт всех девяти E/S находится в `network_comparison.csv`, максимум каждого сценария — `result_summary.json`.

## Календарь и предел эксплуатационного вывода

**Основные планы — `{MAIN_BASIS}`.** Для AER/MRV нет принятого парного блока по направлению/сезону/модификации. Справочные RW3ч30 для AER без дат/частоты не повышены до двустороннего dispatch block. KJA→SVX LR и SVX→KJA B не образуют один доказанный вариант. Поэтому календарь использует ceil старой геометрии как явно отдельный диагностический план. Ни одна его строка не помечена observed. Это позволяет сравнить конкретные деньги и ресурсы при условном block, но **не делает расписание эксплуатационно доказанным**. High +15% — другой неоткалиброванный stress, не доверительная граница. Его ошибки видны в `block_stress.json`; отклонённая целиком программа не получает частичную прибыль.

В `requests/` переданы физические аэропорты, уникальные flightIDs, UTC/local, tails/delivery/entry, полный P и KEEP, nominal/high, 60min turn для всех альтернатив. Все циклы возвращают борт в SVX. `dated_flights`, `rotations`, `resource_checks` проверяют позицию, overlap, turns, ввод, cycles, один резерв и дневной diagnostic8BH. Night endpoint — только UTC22–06 diagnostic, не юридический crew/duty checker. Начальное положение и maintenance windows условны, crew/rest/MRO/slots/AFM/payload/route rights UNKNOWN. Bare BH недостаточно. Денежные расходы начислены на все плечи; неизвестные ввод, резерв, база и ferry остаются в F.

Календарь развёрнут за 365 и366 дат, включает реальные пятницы/возвраты/месяцы и29.02.2028. Никаких множителей52/48 вместо dated суммы. В monthly_results деньги по UTC-дате вылета, BH в ops по фактическому пересечению UTC-месяца; elapsed включает промежуточные turns. Обе чувствительности используют **одни даты/паттерны/nominal blocks**. `adaptive_policy.csv` — отдельная заранее фиксированная политика после Q1: продолжать только по наблюдённой марже, иначе вернуть ресурс KEEP с апреля. Численный branch по модельному Q1 — иллюстрация при нулевых пропущенных затратах, не наблюдение и не одобрение; затраты остановки/возврата неизвестны.

## KEEP, новые пассажиры и пороги

Основные строки `EMPTY_AFFECTED_KEEP_UPPER_CONDITIONAL` раскрывают только верхний случай пустого affected scope. Они не дают весь будущий KEEP=0. **Даже old nonstop=0 не означает нулевые старые RW продажи.** Completed winner evidence и реально открытые parent страницы: AER — route page без расписания; MRV — marketed connection через MQF, cached описание не доказывает отсутствия другого direct. Кто оперирует каждое плечо, объём, доход и избегаемые затраты UNKNOWN. Ни оба MQF-плеча RW, ни все sector pax новыми клиентами не объявляются. 785k/211k — старые bidirectional airport segments с невосстановленным первичным локатором, не добавлены в endpoint prior.

`old_RW_sensitivity.csv` даёт 0/1/2/4/7 старых nonstop RT каждой пары на E2/S0 с совместным P−KEEP. Для неизвестных прежних connecting/marketed sales, не включённых в recombinator, отдельная остаточная потеря L остаётся NULL. Если продажи уже включены в affected KEEP, повторно L не списывается. Одинаковые прежние неизбежные платежи не исчезают при отмене задания. Полная компания KEEP PnL/платёжный календарь отсутствуют, поэтому cash/peak funding/full profit NULL.

Точный бюджет: **F + Dexternal + LoldRWoutside ≤ joint(P−KEEP)**; максимальная сумма есть по году/месяцу и на фактические занятые UTC tail-flightdays, а не BH/8. В control E2/S0 лучшего BASE2027 бюджет {winner['known_increment_upper_conditional_RUB']/1e6:.1f} млн, или {winner['max_same_loss_RUB_per_actual_P_flight_tailday']:,.0f} RUB на P flight-tailday. Отрицательный бюджет означает, что неотрицательные дополнительные потери/затраты не спасают именно эту sensitivity point. При ранжировании двух программ общий внешний донор сокращается лишь если его задания/дни и расходы действительно одинаковы; `matched_hub_comparison.csv` и `ranking_thresholds.csv` показывают абсолютную и дневную дифференциальную потерю, достаточную сменить порядок. `route_launch_thresholds.csv` даёт конкретный q/net gate на обе стороны каждого RT до неизвестных потерь. Actual market share/unique new RW customers NULL. Для hub journeys и occupied leg segments раздельны.

Главная NS экономика: оба support=0. P05 net уже содержит сценарные VAT/distribution/acquiring; passenger500/650 не списаны второй раз, они отдельный nonoverlap stress. Fuel/ground/MRO/crew/nav сценарно перенесены из P04, реальные2027 контракты и налоговый мост неизвестны. Алгебраический revenue scale в gates держит allocation фиксированным; изменение тарифа требует нового choice, это не калиброванный q/yield прогноз. Нужен совместный directional q/netyield, достаточный покрыть incremental costs + F + donor + L при общих seats/OD. Нельзя сравнить старые авторские +44 с новыми P05 gross/net без совместного пересчёта: этого здесь нет.

## OMS на том же ресурсе

`HUB_OMS_RESOURCE_MATCHED` — новый маленький **именованный** comparator, город OMS сохранён. При N1 замкнутые SVX–OMS–NJC–OMS–SVX Mon/Wed/Fri; при N2 второй такой bank Tue/Thu/Sat. Неиспользованные слоты остаются доступными той же оболочке. Первая неполная неделя1–3января без bank: transfer за неё нулевой. Только ordered dated two-leg через OMS с MCT60/max180 дают transfer product. Один endpoint fare признаётся один раз; локальные и transfer потоки совместно расходуют оба общих physical legs через pinned P06. Код `hub_bundle` — минимальный локальный adapter, не сумма RT и не прежний полный hub+503. Through OD prior/choice, baggage/interline/through-ticket/misconnect расходы и rights не доказаны. Его ошибки могут поменять результат; они не скрыты.

`author_fixed_reference_legs.csv` и `author_fixed_reference_checks.csv` сохраняют полные авторские direct/OMS/GOJ без обрезания. BASE old direct требует9 working и OMS8 по прежнему hours-screen, против max4 новой оболочки; там INFEASIBLE при названной proxy/UNKNOWN actual dated feasibility. CAUTIOUS author составы отличаются, это отдельные references, не sensitivity нового fixed состава. Их годовые деньги не присвоены малой оболочке.

## Конечная выборка и ближайший запуск

Восемь совместно пересчитанных недельных split-кандидатов на E1/S0 и три фиксированные политики с OMS при9 E/S — **ограниченная эвристика**, не глобальный максимум и не поиск всех городов/тарифов/DOW. `joint_search.csv` показывает сравниваемое множество. KUF–GOJ/SVX–GOJ с отрицательными условными добавками не выбраны из-за красивого табло. Дальние AER–VVO/KHV остались за дневной сетью: attractive cost screen не CASE_SJready. Треугольники не добавлены: нет достаточных положительных cautious adjacent-OD и paired blocks/варианта; upstream six-cycle screen сохранён как исследовательский вход. Зрелый перечень10 пар в definitions — список будущих gates, не слабые filler routes пилота.

Ближайший к проверке запуска — **D1 с первым существующим слотом и отдельным резервом**, затем D3 только после доказанного наблюдённого преимущества на donor flightdays и ввода. Лучший BASE ещё не проходит cautious/full gate. Точно не хватает: текущего dated nonstop/marketed KEEP и выручки/avoidable costs MQF-продукта; обоих valid blocks/type/payload/slots; освобождённого борта и отдельного резерва; crew/MRO; фактических directional OD/netyield/cost и полного F/donor/cash. `launch_gates.csv` содержит денежные пороги, `RW_data_request.csv` — конкретные запросы. При отрицательном cautious NS сначала нужны доказанные q/yield/контракт затрат или меньший подтверждённый донорский loss budget; запуск по одному LF/меньшему убытку не предлагается.

Партнёрский block/cargo/closed cohort/international/newtypes/CM — только `supplemental_appendix.csv` с символическими thresholds/conditions, без бесплатного profit или смешения agent margin с RW-operated долей. Исторический32930 — только диагностика,185228 не договор. Источниковый приоритет — canonical source_review; completed winner gate добавлен без нового исследования.

## Воспроизведение и передача

Из этой рабочей копии: `python3 -B context/31_direct_growth_research_20261112/networks/calculate.py`, затем `python3 -B context/31_direct_growth_research_20261112/networks/verify.py`. Все записи только `networks/`; исходные API не изменяются. `validation.json` — механические/граничные проверки и детерминированность; `manifest.json` — SHA256 входов/выходов. Tracked436/context30 и завершённые исходные пакеты защищены hashes. Отдельный независимый review **не проводился**, это следующий этап. Работа остановлена после сборки.
''')


def input_paths():
    paths=[ROOT/'TASKS.md',ROOT/'ASSEMBLY_REQUIREMENTS.md',ROOT/'remote_pins.json',ROOT/'audit/common_contract.json']
    for d in ['route_economics','ops_inputs','source_review','winner_evidence']:
        paths.extend(x for x in (ROOT/d).iterdir() if x.is_file())
    paths.append(ROOT/'coordinator/winner_primary_check.md')
    for d in [RE.P05DIR,RE.P06DIR,RE.P04DIR,RE.BASE/'data']:
        paths.extend(x for x in d.rglob('*') if x.is_file() and '__pycache__' not in str(x))
    return sorted(set(paths))


def build_manifest():
    outputs={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['manifest.json','validation.json'] and '__pycache__' not in str(p)}
    dump('manifest.json',dict(version=VERSION,inputs={str(p.relative_to(ROOT)):sha(p) for p in input_paths()},
        outputs=outputs,pins=json.loads((ROOT/'remote_pins.json').read_text()),
        write_scope=str(HERE),new_observed_OD_frequency_netyield_contract_updates=0,
        scope='conditional finite assembly; not independent review or dispatch/finance approval'))


if __name__=='__main__':
    assemble()
