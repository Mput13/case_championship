#!/usr/bin/env python3
"""Isolated P09 adapter: pinned calendars, P06 allocator, operations and finance.

Market inputs are frozen offline. No P09 source or output is ever written.
Two price policies; explicit finite direct supply; common project/KEEP markets.
"""
import sys
sys.dont_write_bytecode=True
import copy, csv, hashlib, importlib, json, math
from collections import defaultdict
from pathlib import Path
from functools import lru_cache

ROOT=Path(__file__).resolve().parent
P09=ROOT.parent/'35_full_programme_execution_20261112/P09'
sys.path.insert(0,str(P09))
import programme_builder as b
import evaluate_programmes as legacy
from engine.choice import utility
from build_competition_market import season, clip

ORIGINAL_DAILY=legacy.daily_evaluate
ORIGINAL_MONTHLY_FINANCE=legacy.monthly_finance
MARKETS={r['pair']:r for r in json.loads((ROOT/'market_competition_209.json').read_text())}
CONFIG=None
CACHE={}
PRICE_CACHE={}
UNKNOWN_PAIRS=set()
CHECKS=dict(allocation_calls=0,max_demand_residual=0.,max_seat_excess=0.,max_competitor_capacity_excess=0.)
CONFIGURATIONS=[
 dict(config='p09_legacy_check',scenario='base',pricing_policy='legacy',response=False,expansion=False,fuel_net=False),
 dict(config='comp_market_base',scenario='base',pricing_policy='market_match',response=False,expansion=False,fuel_net=False),
 dict(config='comp_market_base_yield',scenario='base',pricing_policy='yield_optimal',response=False,expansion=False,fuel_net=False),
 dict(config='comp_market_cautious',scenario='cautious',pricing_policy='market_match',response=True,expansion=False,fuel_net=False),
 dict(config='comp_market_cautious_yield',scenario='cautious',pricing_policy='yield_optimal',response=True,expansion=False,fuel_net=False),
 dict(config='comp_expansion_stress_2028',scenario='cautious',pricing_policy='market_match',response=True,expansion=True,fuel_net=False),
 dict(config='comp_expansion_stress_2028_yield',scenario='cautious',pricing_policy='yield_optimal',response=True,expansion=True,fuel_net=False),
 dict(config='comp_net_fuel_conditional',scenario='base',pricing_policy='yield_optimal',response=False,expansion=False,fuel_net=True),
]

def configure(config):
    global CONFIG
    CONFIG=dict(config);CACHE.clear();PRICE_CACHE.clear();legacy.DAY_CACHE.clear()
    legacy.daily_evaluate=ORIGINAL_DAILY if config['pricing_policy']=='legacy' else daily_evaluate
    legacy.monthly_finance=monthly_finance

def lookup(m):
    pair=m.get('physical_airport_pair') or '-'.join(sorted((m['origin_market'],m['destination_market'])))
    if pair in MARKETS:return MARKETS[pair]
    UNKNOWN_PAIRS.add(pair)
    ref=b.p05.gross_fare(m['distance_km'])
    # Shared connecting alternatives for indirect endpoints outside 209 leg pairs.
    # Coverage is explicitly UNKNOWN. No assertion of direct-monopoly protection.
    return dict(pair=pair,direct_carrier_details=[],direct_season_indices={'winter':1.,'shoulder':1.,'summer':1.},
        transfer_season_indices={'winter':1.,'shoulder':1.,'summer':1.},F_comp_direct_20kg=None,F_comp_transfer_20kg=ref*1.15,
        transfer_duration_minutes=90+1.4*m['distance_km']/750*60+120,competitor_daily_seats=0.,W_comp_2027=.25,W_comp_2028=.35,
        direct_presence_quality='UNKNOWN_OUTSIDE_209',risk_factors=dict(aeroflot_cluster=0,nordwind_kzn=0,s7_regional=0,lcc189=0),rw_subsidized_2026=False)

def annotate_physical_markets(frags):
    """Keep common CITY:MOW demand while looking up exact airport competition.

    The non-AUTH matrix has one physical endpoint pair per directional city pool.
    Multiple-airport AUTH portfolios require their own substitution adapter.
    """
    physical=defaultdict(set)
    for frag in frags:
        for p in frag['products']:
            if p['owner']=='RW':
                route=p['route_airports'];physical[b.core.pool_key(p)].add('-'.join(sorted((route[0],route[-1]))))
    for frag in frags:
        frag['markets']=[dict(m,physical_airport_pair=next(iter(physical[b.core.pool_key(m)]))) if len(physical[b.core.pool_key(m)])==1 else m for m in frag['markets']]
    return frags

def vat_for(p):
    return 0. if CONFIG['scenario']=='base' and not set(p['route_airports'])&b.p05.MOSCOW else .10

def expansion_intensity(day):
    if not CONFIG['expansion']:return 0.
    return 1. if day[:4]=='2028' else .25 if day[5:7]>='10' else 0.

def competitor_products(m,old,entered=False,neutral=False):
    """Old inclusive reference mass 0.6 is split, never duplicated.

    Neutral check: same reference fare/time, frequency 1, nonbinding supply =>
    sum exp(U_air)=.6 exactly, reproducing P05 old outside choice mass.
    """
    market=lookup(m);c=b.p05.coefficients(CONFIG['scenario']);day=old['departure_date'];s=season(day[5:7])
    ref=old['reference_gross_fare'];rt=old['reference_duration_minutes']
    # Preserve the pinned unrounded P05 distance on ordinary city pairs. Only
    # Moscow needs the exact-airport adapter instead of the CITY:MOW proxy.
    dist=float(market.get('distance_km',m['distance_km'])) if 'MOW' in (m['origin_market'],m['destination_market']) else m['distance_km']
    refu=c['price_per_rub']*ref+c['time_per_minute']*rt
    ds=market['direct_carrier_details'];total=sum(d['daily_seats'] for d in ds)
    rho=min(.9,total/(total+100)) if total else 0.
    intensity=expansion_intensity(day);w=market['W_comp_2028' if day[:4]=='2028' else 'W_comp_2027']
    out=[]
    for d in ds:
        share=d['daily_seats']/total
        freq=d['daily_departures'];capacity=d['daily_seats']
        fare=d['seasonal_fares'][s]
        floor=d['variable_floor_subsidy20_stress'] if CONFIG['response'] else d['variable_floor_unsubsidized']
        # Response stop threshold reserves a 3% cushion above the researched cash
        # floor; the table already has selling costs. This cushion is a scenario,
        # not another recognised cost or a claim about future VAT.
        grossfloor=floor/.97
        if CONFIG['response'] and entered:
            cut=.15 if d['carrier'] in ('DP','N4','5N') or d['subsidy_2026_awarded_or_eligible'] else .10
            fare=min(fare,max(grossfloor,fare*(1-cut)))
        if intensity:
            freq*=1+intensity*w*.75;capacity*=1+intensity*w*.75
            fare=min(fare,max(grossfloor,fare*(1-intensity*w*.10)))
        p=copy.copy(old)
        p.update(product_id=old['product_id']+':DIRECT:'+d['carrier'],kind='outside',owner='AIR_COMP_DIRECT',outside_component='EXPLICIT_DIRECT_COMPETITOR',
            gross_fare=ref if neutral else fare,net_fare=0.,duration_minutes=rt if neutral else 45+dist/750*60,
            frequency=1. if neutral else freq,capacity=m['potential_journeys'] if neutral else capacity,
            intercept=math.log(.6*rho*share)-refu,legs=[],carrier=d['carrier'],unconstrained_capacity_not_physical=False,
            capacity_status='directional_daily_2026_sample_extrapolated_scenario',var_floor_gross=grossfloor,
            response_applied=entered and CONFIG['response'],assumption_id='COMP-DIRECT-v1')
        p['intercept']+=c['price_per_rub']*p['gross_fare']+c['time_per_minute']*p['duration_minutes']+c['log_frequency']*math.log(p['frequency'])
        p['choice_utility_encoding']='explicit_price_time_frequency_folded_into_outside_intercept;finite_capacity'
        out.append(p)
    # Scenario entrants: a weighted 2/week feeder, only where that strategy has a
    # matching endpoint. Not a claim of a published flight or of spare SSJ tails.
    risk=market['risk_factors'];ends=set(market['pair'].split('-'))
    entry_factor=max(risk.get('aeroflot_cluster',0) if 'SVX' in ends else 0.,risk.get('nordwind_kzn',0) if 'KZN' in ends else 0.,risk.get('s7_regional',0) if ends&{'IKT','VVO','KHV','KJA','BAX'} else 0.)
    if intensity and entry_factor and not neutral:
        freq=2/7*intensity*entry_factor
        fare=(market['F_comp_direct_20kg'] or min(ref,market['F_comp_transfer_20kg']*.9))*market['direct_season_indices'][s]
        p=copy.copy(old);p.update(product_id=old['product_id']+':EXPANSION',kind='outside',owner='AIR_COMP_DIRECT',outside_component='SCENARIO_NEW_ENTRY',
            gross_fare=fare,net_fare=0.,duration_minutes=45+dist/750*60,frequency=freq,capacity=freq*100,
            intercept=math.log(.6*.25)-refu,legs=[],carrier='SCENARIO_ENTRY',var_floor_gross=None,assumption_id='COMP-EXPANSION-ENTRY')
        p['intercept']+=c['price_per_rub']*p['gross_fare']+c['time_per_minute']*p['duration_minutes']+c['log_frequency']*math.log(p['frequency'])
        out.append(p)
    transferfare=market['F_comp_transfer_20kg']*market['transfer_season_indices'][s]
    # Transfer price response uses a two-leg cost analogue. No new physical
    # connecting seat inventory is manufactured from search itineraries.
    if CONFIG['response'] and entered:
        tfloor=(market.get('competitor_var_floor') or ref*.45)*1.35/.97
        transferfare=min(transferfare,max(tfloor,transferfare*.9))
    p=copy.copy(old);p.update(product_id=old['product_id']+':TRANSFER',kind='outside',owner='AIR_COMP_TRANSFER',outside_component='UNREPRESENTED_CONNECTING_AIR',
        gross_fare=ref if neutral else transferfare,net_fare=0.,duration_minutes=rt if neutral else market['transfer_duration_minutes'],
        frequency=1.,capacity=m['potential_journeys'],legs=[],intercept=math.log(.6*(1-rho))-refu,
        capacity_status='potential_demand_upper_bound_NOT_physical_transfer_seats',assumption_id='COMP-TRANSFER-v1')
    p['intercept']+=c['price_per_rub']*p['gross_fare']+c['time_per_minute']*p['duration_minutes']
    out.append(p)
    return out

def marginal_pax_cost(p,flights):
    return sum(sum(b.pax_rate(flights[l]['origin_airport'],k)[0] for k in ['terminal_domestic','pax_service_domestic']) for l in p['legs'])

def flight_cost(f,scenario,fuel_net=False):
    c='base_point' if scenario=='base' else 'cautious_point'
    rates={k:float(b.COSTS['HIST-'+k][c]) for k in ['fuel_t_per_hour','fuel_t_per_cycle','mro_rub_per_hour','crew_rub_per_hour','navigation_rub_per_hour']}
    bh=(b.p05.utc(f['arrival_utc'])-b.p05.utc(f['departure_utc'])).total_seconds()/3600
    cost=(bh*rates['fuel_t_per_hour']+rates['fuel_t_per_cycle'])*(80000 if fuel_net else 136300)
    cost+=bh*sum(rates[k] for k in ['mro_rub_per_hour','crew_rub_per_hour','navigation_rub_per_hour'])
    cost+=sum(49.45*float(b.COSTS.get(f['origin_airport']+'-'+k,b.COSTS['UFA-'+k])['value']) for k in ['takeoff_landing','security'])
    return cost

def rw_price(p,m,competitors,flights):
    market=lookup(m);s=season(p['departure_date'][5:7]);ref=p['reference_gross_fare'];idx=market['direct_season_indices'][s]
    direct=[q for q in competitors if q['owner']=='AIR_COMP_DIRECT'];conn=next(q for q in competitors if q['owner']=='AIR_COMP_TRANSFER')
    beta=b.p05.coefficients(CONFIG['scenario']);vot=abs(beta['time_per_minute']/beta['price_per_rub'])
    premium=min(ref*.15,max(0,conn['duration_minutes']-p['duration_minutes'])*vot)
    upper=min(ref*idx,conn['gross_fare']+premium)
    if direct:
        # A direct SJ service receives no premium over an equally direct rival.
        # 3% is a transparent corridor scenario, not an observed brand premium.
        direct_anchor=min(q['gross_fare'] for q in direct)
        upper=min(upper,direct_anchor*1.10)
        matched=min(upper,direct_anchor*1.03)
    else:matched=min(upper,conn['gross_fare']+premium)
    vat=vat_for(p)
    distribution=.03 if CONFIG['scenario']=='base' else .08
    netfactor=(1-distribution)/(1+vat)
    paxcost=marginal_pax_cost(p,flights)
    operating=sum(flight_cost(flights[l],CONFIG['scenario'],CONFIG['fuel_net']) for l in p['legs'])
    # Per-seat 85% planning load is a scenario price floor, not identified demand.
    low=(operating/(min(flights[l]['saleable_seats'] for l in p['legs'])*.85)+paxcost)/netfactor
    if CONFIG['pricing_policy']=='market_match':return max(500,matched),dict(lower=low,upper=upper,below_cost_floor=matched<low)
    # If willingness-to-pay ceiling is below the operating planning floor, no
    # feasible profitable grid exists: quote the ceiling, retain loss, do not raise.
    if low>upper:return max(500,upper),dict(lower=low,upper=upper,below_cost_floor=True)
    candidates=sorted(set([low,upper,clip(matched,low,upper)]+[low+(upper-low)*i/10 for i in range(11)]))
    pkey=(m['demand_pool_id'],p['departure_date'][:7],round(p['duration_minutes'],2),p['frequency'],round(p['intercept'],5),round(m['potential_journeys'],4),round(operating),tuple(round(q['gross_fare']) for q in competitors),CONFIG['config'])
    if pkey in PRICE_CACHE:return PRICE_CACHE[pkey]
    # One route-season quote optimised for a representative directional product.
    # P06 subsequently resolves common inventory and transfer displacement. This
    # is a constrained one-dimensional yield search, not a network optimum.
    other=[utility(q,beta) for q in competitors]+[math.log(.3),math.log(.1)]
    mx=max(other);lse=mx+math.log(sum(math.exp(u-mx) for u in other))
    best=None
    for price in candidates:
        u=p['intercept']+beta['price_per_rub']*price+beta['time_per_minute']*p['duration_minutes']+beta['log_frequency']*math.log(p['frequency'])
        share=1/(1+math.exp(clip(lse-u,-700,700)))
        carried=min(m['potential_journeys']*share,min(flights[l]['saleable_seats'] for l in p['legs']))
        contribution=carried*(netfactor*price-paxcost)-operating
        if best is None or contribution>best[0]:best=(contribution,price)
    result=(best[1],dict(lower=low,upper=upper,below_cost_floor=False,objective='single_product_expected_contribution_before_shared_P06_inventory'))
    PRICE_CACHE[pkey]=result
    return result

def transform(frag,fs,neutral=False):
    c=b.p05.coefficients(CONFIG['scenario']);byf={f['flight_instance_id']:f for f in fs}
    marketby={b.core.pool_key(m):m for m in frag['markets']};rwkeys={b.core.pool_key(p) for p in frag['products'] if p['owner']=='RW'}
    out=[];comp=defaultdict(list)
    for p in frag['products']:
        if p.get('outside_component')=='UNREPRESENTED_EXISTING_AIR':
            key=b.core.pool_key(p);m=marketby[key]
            cp=competitor_products(m,p,key in rwkeys,neutral);comp[key]=cp;out+=cp
        else:out.append(copy.copy(p))
    for p in out:
        if p['owner']=='RW' and not neutral:
            p['gross_fare'],bounds=rw_price(p,marketby[b.core.pool_key(p)],comp[b.core.pool_key(p)],byf)
            p['net_fare']=b.p05.net_fare(p['gross_fare'],vat_for(p),.03 if CONFIG['scenario']=='base' else .08)
            p['competitive_price_bounds']=bounds;p['pricing_policy']=CONFIG['pricing_policy']
    return dict(frag,products=out,response_policy=dict(rules=[]))

def verify_allocation(bundle,products,a):
    CHECKS['allocation_calls']+=1
    totals=defaultdict(float)
    for x in a['allocations']:totals[b.core.pool_key(x)]+=x['final_choice']
    for m in bundle['markets']:CHECKS['max_demand_residual']=max(CHECKS['max_demand_residual'],abs(totals[b.core.pool_key(m)]-m['potential_journeys']))
    for s in a['seats']:CHECKS['max_seat_excess']=max(CHECKS['max_seat_excess'],s['carried_segments']-s['saleable_seats'])
    ps={p['product_id']:p for p in products}
    for x in a['allocations']:
        p=ps[x['product_id']]
        if p['owner']=='AIR_COMP_DIRECT':CHECKS['max_competitor_capacity_excess']=max(CHECKS['max_competitor_capacity_excess'],x['final_choice']-p['capacity'])

def daily_evaluate(pfs,kfs,scenario,transfers,response,record=False):
    day=(pfs or kfs)[0]['departure_utc'][:10]
    key=b.digest([day[:7],CONFIG['config'],scenario,transfers,legacy.daily_shape(pfs),legacy.daily_shape(kfs)])
    if key in CACHE and not record:return CACHE[key]
    frags=annotate_physical_markets(b.pair_fragments(pfs,kfs,scenario,transfers,'passive'));outputs=[]
    for fs,frag in zip((pfs,kfs),frags):
        frag=transform(frag,fs)
        bundle=dict(flights=fs,markets=frag['markets'],products=frag['products'],choice_model=b.p05.coefficients(scenario),contracts=[],economic_events=[],response_policy=frag['response_policy'])
        assert not b.check_itineraries(bundle)
        products=b.apply_response(bundle);allocation=b.allocate(bundle,products);verify_allocation(bundle,products,allocation)
        ps={p['product_id']:p for p in products};rw=[a for a in allocation['allocations'] if a['owner']=='RW']
        row=dict(journeys=sum(a['carried'] for a in rw),passenger_segments=sum(a['carried']*len(ps[a['product_id']]['legs']) for a in rw),revenue_net=sum(a['carried']*ps[a['product_id']]['net_fare'] for a in rw),transfer_journeys=sum(a['carried'] for a in rw if len(ps[a['product_id']]['legs'])>1),potential_journeys=sum(m['potential_journeys'] for m in frag['markets']),outside_air_choice=sum(a['final_choice'] for a in allocation['allocations'] if a['owner'].startswith('AIR_COMP')),seat_capacity=sum(f['saleable_seats'] for f in fs),unfilled_seats=sum(x['unsold_seats'] for x in allocation['seats']),departing_pax_by_airport={})
        fby={f['flight_instance_id']:f for f in fs}
        for r in allocation['seats']:
            a=fby[r['flight_instance_id']]['origin_airport'];row['departing_pax_by_airport'][a]=row['departing_pax_by_airport'].get(a,0)+r['carried_segments']
        if record:row.update(products=products,allocation=allocation,markets=frag['markets'])
        outputs.append(row)
    if not record:CACHE[key]=outputs
    return outputs

def monthly_finance(cal,monthly,programme,scenario):
    if not CONFIG['fuel_net']:return ORIGINAL_MONTHLY_FINANCE(cal,monthly,programme,scenario)
    old=b.economic_events
    def events(c,s,p):
        es=old(c,s,p)
        for e in es:
            if e['economic_event_id'].endswith(':fuel'):
                e['rate']=80000;e['amount']=e['quantity']*80000;e['source_id']+=';CONDITIONAL_NET_FUEL80_NO_RECEIPT_CONFIRMED'
        return es
    b.economic_events=events
    try:return ORIGINAL_MONTHLY_FINANCE(cal,monthly,programme,scenario)
    finally:b.economic_events=old

def evaluate(programme,config,delivery='phased'):
    if CONFIG!=config:configure(config)
    return legacy.evaluate(programme,delivery,config['scenario'],'passive')

def neutral_calibration_test(programme):
    configure(CONFIGURATIONS[1]);pc=b.build_calendar(programme,'phased');kc=b.build_calendar(b.KEEP,'phased')
    maxerr=0.;calls=0
    for day in ['2028-12-04','2028-12-05','2028-07-03']:
        pfs=[f for f in pc['flights'] if f['departure_utc'][:10]==day];kfs=[f for f in kc['flights'] if f['departure_utc'][:10]==day]
        for fs,frag in zip((pfs,kfs),annotate_physical_markets(b.pair_fragments(pfs,kfs,'base',programme.get('transfers',True),'passive'))):
            bundle=dict(flights=fs,markets=frag['markets'],products=frag['products'],choice_model=b.p05.coefficients('base'),contracts=[],economic_events=[])
            a=b.allocate(bundle,frag['products']);nf=transform(frag,fs,neutral=True);na=b.allocate(dict(bundle,products=nf['products']),nf['products'])
            old={x['product_id']:x['carried'] for x in a['allocations'] if x['owner']=='RW'}
            new={x['product_id']:x['carried'] for x in na['allocations'] if x['owner']=='RW'}
            for pid,q in old.items():maxerr=max(maxerr,abs(q-new[pid]))
            verify_allocation(dict(bundle,products=nf['products']),nf['products'],na);calls+=1
    assert maxerr<1e-8,maxerr
    return dict(status='PASS',component_allocations=calls,max_rw_carried_error=maxerr,condition='all competitor prices/time/frequency reset to old reference; nonbinding capacity; inclusive air mass .6')
