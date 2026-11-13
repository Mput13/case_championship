#!/usr/bin/env python3
"""Conditional direct-route cost screen and joint programme adapter, no optimiser.

Only writes under route_economics. P05 fare/choice/profile and P06 inventory
allocation are imported from the audit's immutable git snapshots. See README.
"""
import calendar
import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORKSPACE = ROOT.parents[1]
PIN = ROOT / 'audit/inputs/audit_model'
P05DIR = PIN/'a63a047b/context/35_full_programme_execution_20261112/P05'
P06DIR = PIN/'982f13d9/context/35_full_programme_execution_20261112/P06'
P04DIR = PIN/'620a0ac4/context/35_full_programme_execution_20261112/P04'
P03DIR = PIN/'79dc698b/context/35_full_programme_execution_20261112/P03'
BASE = PIN/'dceadc98'
VERSION = 'RE-1.0-20261112'
SPEC = importlib.util.spec_from_file_location('pinned_p05', P05DIR/'model.py')
P05 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P05)
sys.path.insert(0, str(P06DIR))
from engine.choice import allocate as allocate_p06
OPS_SPEC = importlib.util.spec_from_file_location('completed_ops_calendar', ROOT/'ops_inputs/calendar_engine.py')
OPS_CALENDAR = importlib.util.module_from_spec(OPS_SPEC)
OPS_SPEC.loader.exec_module(OPS_CALENDAR)


def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def dump(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n')


def table(name, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: 'UNKNOWN' if v is None else (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def city(a):
    return P05.city(a)


def pair(a, b):
    return tuple(sorted((city(a), city(b))))


def pid(a, b):
    return '-'.join(pair(a, b))


class SnapshotDemand(P05.Demand):
    """Only path adapter; reuse P05 prior/gravity/market methods unchanged."""
    def __init__(self):
        self.nodes = {r['iata']: r for r in read(BASE/'data/processed/catchments.csv')}
        mows = [self.nodes[x] for x in sorted(P05.MOSCOW) if x in self.nodes]
        self.nodes['MOW'] = dict(self.nodes['SVO'], iata='MOW', pop=str(sum(float(x['pop']) for x in mows)), main_city='Москва')
        self.od = {pair(r['a'], r['b']): r for r in read(BASE/'data/processed/od_pairs.csv')}
        self.segments = {pair(r['a'], r['b']): r for r in read(BASE/'data/processed/demand_pairs.csv')}
        self.fit = json.loads((BASE/'data/processed/od_fit.json').read_text())


DEMAND = SnapshotDemand()
RW = {pair(r['a'], r['b']): r for r in read(BASE/'data/manual/rw_routes_now.csv')}
CLOSED = {r['iata']: r for r in read(BASE/'data/manual/closed_airports.csv')}
COSTS = {r['cost_id']: r for r in read(P04DIR/'cost_ranges.csv')}
CONTRACT = json.loads((ROOT/'audit/common_contract.json').read_text())
GRID = (1, 2, 3, 4, 7)
DAY_GRID = {1: (2,), 2: (1, 4), 3: (0, 2, 4), 4: (0, 2, 4, 6), 7: tuple(range(7))}


def days_in(start, end, weekdays):
    d, e = date.fromisoformat(start), date.fromisoformat(end)
    while d <= e:
        if d.weekday() in weekdays:
            yield d
        d += timedelta(days=1)


@lru_cache(None)
def counts(year, frequency):
    out = Counter(d.month for d in days_in(f'{year}-01-01', f'{year}-12-31', DAY_GRID[frequency]))
    return tuple(out[m] for m in range(1, 13))


@lru_cache(None)
def geometry(a, b):
    # No radius/range filter. This old geometry is a costscreen, NOT block approval.
    a, b = (a, b) if a <= b else (b, a)
    if a not in DEMAND.nodes or b not in DEMAND.nodes:
        return None, None
    km = P05.km(DEMAND.nodes[a], DEMAND.nodes[b])
    return km, .5 + 1.1*km/750


def costs(a, b, scenario, hours=None):
    km, h = geometry(a, b)
    h = hours if hours is not None else h
    if h is None:
        return None
    key = 'base_point' if scenario == 'base' else 'cautious_point'
    rates = {k: float(v[key]) for k, v in COSTS.items() if k.startswith('HIST-')}
    # Local primary reference transferred as a stated scenario, no future contract.
    fuel_price = (float(COSTS['UFA-fuel-20261111']['value']) + float(COSTS['UFA-fuel_uplift']['value'])) if scenario == 'base' else 161696.0
    ground, deice = (96089.0, 15000.0) if scenario == 'base' else (115307.0, 40000.0)
    tonnes = h*rates['HIST-fuel_t_per_hour'] + rates['HIST-fuel_t_per_cycle']
    other = h*sum(rates[x] for x in ('HIST-mro_rub_per_hour', 'HIST-crew_rub_per_hour', 'HIST-navigation_rub_per_hour')) + ground + deice
    return dict(distance_km=km, block_hours_costscreen=h, fuel_t=tonnes, fuel_price=fuel_price,
                fuel_cost=tonnes*fuel_price, other_cost=other, fixed_cost=tonnes*fuel_price+other,
                pax_unknown_stress=rates['HIST-pax_cost_rub'])


def fare(a, b, scenario, gross_override=None):
    km, _ = geometry(a, b)
    if gross_override is None and km is None:
        return None, None
    gross = P05.gross_fare(km) if gross_override is None else gross_override
    vat = 0.0 if scenario == 'base' and 'MOW' not in pair(a, b) else .10
    distribution = .03 if scenario == 'base' else .08
    return gross, P05.net_fare(gross, vat, distribution)


@lru_cache(None)
def annual(a, b, scenario, year):
    # International nodes NEVER enter the domestic gravity extrapolation.
    q, qc, src, via, _ = DEMAND.prior(a, b)
    if q is None:
        return None, src, via
    return (q if scenario == 'base' else qc*.962**(year-2025)), src, via


def mass(a, b, frequency, scenario, gross=None, duration=None, response='passive'):
    """P05 conditional logit: .6/.3/.1 outside masses, no 65% capture.

    Frequency is a registered weekly extension, reference=3, not an estimate.
    The OTHER_AIR mass is an uncapacitated composite, NOT invented flights.
    """
    if frequency <= 0:
        return 0.0
    c = P05.coefficients(scenario)
    _, _, _, via, dist = DEMAND.prior(a, b)
    km, h = geometry(a, b)
    refgross = P05.gross_fare(dist if dist is not None else km)
    gross = fare(a, b, scenario)[0] if gross is None else gross
    reftime = 45+(dist if dist is not None else km)/650*60+(120 if via else 0)
    duration = h*60 if duration is None else duration
    return .6*math.exp(c['price_per_rub']*(gross-refgross)+c['time_per_minute']*(duration-reftime)+c['log_frequency']*math.log(frequency/3))


def outside_mass(a, b, scenario, response='passive'):
    if response == 'price_match10':
        gross = fare(a, b, scenario)[0]
        return .4+.6*math.exp(P05.coefficients(scenario)['price_per_rub']*(-.10*gross))
    if response != 'passive':
        raise ValueError('unknown response scenario')
    return 1.0


def capacity_choice(potential, weight, capacity, outside=1.0):
    """Exact one-RW-product special case of pinned P06 allocate; tested there."""
    return min(capacity, potential*weight/(outside+weight))


def screen(a, b, frequency, scenario, year=2027, direction_fraction=.5,
           gross_ab=None, gross_ba=None, old_frequency=None, demand_multiplier=1.0,
           response='passive', selected_months=tuple(range(1, 13))):
    if frequency not in GRID:
        raise ValueError('finite frequency grid only')
    if not 0 <= direction_fraction <= 1 or demand_multiplier < 0:
        raise ValueError('invalid demand scenario')
    q, src, via = annual(city(a), city(b), scenario, year)
    co = costs(a, b, scenario)
    old = float(RW.get(pair(a, b), {}).get('freq_week_each_way', 0)) if old_frequency is None else old_frequency
    # Moscow historical city-level frequency cannot be allocated to each airport.
    allocation_gate = 'MOW' in pair(a, b)
    if allocation_gate and old_frequency is None:
        old = 0.0
    ga, na = fare(a, b, scenario, gross_ab)
    gb, nb = fare(b, a, scenario, gross_ba)
    nby = counts(year, frequency)
    fields = dict(pair_id=pid(a, b), physical_pair=f'{a}-{b}', origin=a, destination=b,
                  scope='domestic', scenario=scenario, year=year, support='NS', added_pairs_week=frequency,
                  weekdays=';'.join(map(str, DAY_GRID[frequency])), frequency_basis='dated paired returns; old frequency scenario',
                  old_rw_frequency_scenario=old, old_city_frequency_unallocated=RW.get(pair(a,b),{}).get('freq_week_each_way') if allocation_gate else None,
                  old_rw_observation_status='historical snapshot frequency transferred, future actual UNKNOWN' if pair(a,b) in RW else 'UNKNOWN; zero old frequency is explicit empty-affected-KEEP scenario, not evidence of absence',
                  airport_allocation_status='UNKNOWN_GATE_NO_CITY_OD_DUPLICATION' if allocation_gate else 'single_airport',
                  annual_od_both_scenario=q, demand_source=src, endpoint_od_observed=None,
                  competition_status='legacy_direct_flag_only; current dated inventory UNKNOWN',
                  gross_fare_ab=ga, gross_fare_ba=gb, net_fare_ab=na, net_fare_ba=nb,
                  route_support_rub=0.0, fuel_credit_rub=0.0, price_year=2026,
                  ops_status='requires_ops_check', block_basis='geometry_costscreen_not_validated_schedule',
                  full_P_minus_KEEP=None, cash=None, donor_actual=None, reliability='UNKNOWN_OD_NETYIELD_COST_OPS_DONOR',
                  pax_accounting='P05 distribution once; opaque P04 pax basket excluded as F uncertainty')
    if q is None or co is None:
        return fields | dict(screen_status='THRESHOLD_ONLY_UNKNOWN_INPUT')
    totals = Counter()
    for m in selected_months:
        n = nby[m-1]
        days = calendar.monthrange(year, m)[1]
        nold = old*days/7  # explicit continuous frequency scenario, no observed dates
        totaln = n+nold
        ftotal = frequency+old
        potential = q*P05.monthly_profile(year)[m]/.6*demand_multiplier
        outside = outside_mass(a, b, scenario, response)
        w1 = mass(a, b, ftotal, scenario, ga, response=response)
        w2 = mass(b, a, ftotal, scenario, gb, response=response)
        qa = capacity_choice(potential*direction_fraction, w1, 100*totaln, outside)
        qb = capacity_choice(potential*(1-direction_fraction), w2, 100*totaln, outside)
        olda = capacity_choice(potential*direction_fraction, mass(a,b,old,scenario,ga), 100*nold, outside)
        oldb = capacity_choice(potential*(1-direction_fraction), mass(b,a,old,scenario,gb), 100*nold, outside)
        old_after = (qa+qb)*nold/totaln if totaln else 0
        revenue = qa*na+qb*nb
        keep_rev = olda*na+oldb*nb
        fixed_new = 2*n*co['fixed_cost']
        totals.update(pax_ab=qa, pax_ba=qb, keep_pax_ab=olda, keep_pax_ba=oldb,
                      net_revenue=revenue, keep_net_revenue=keep_rev, added_cost=fixed_new,
                      total_cost=2*totaln*co['fixed_cost'], keep_cost=2*nold*co['fixed_cost'],
                      pairs=n, existing_pairs=nold, own_shifted=max(0,olda+oldb-old_after),
                      new_sector_pax=(qa+qb)*n/totaln if totaln else 0,
                      incremental_pax=qa+qb-olda-oldb,
                      potential_ab=potential*direction_fraction, potential_ba=potential*(1-direction_fraction))
    inc = totals['net_revenue']-totals['keep_net_revenue']-totals['added_cost']
    rotations = totals['pairs']
    sumq = totals['pax_ab']+totals['pax_ba']
    incq = totals['incremental_pax']
    mean_net = (na+nb)/2
    be_sum = totals['added_cost']/mean_net if mean_net else None
    closed = [CLOSED[x] for x in pair(a,b) if x in CLOSED]
    return fields | dict(screen_status='CONDITIONAL_NOT_PROFIT', distance_km=co['distance_km'],
                        published_closure_status='SNAPSHOT_RESTRICTED_REOPEN_GATE' if closed else 'no_closed_flag_in_snapshot_not_current_clearance',
                        closure_source=';'.join(x['source'] for x in closed),
                        added_rotations=rotations, directed_added_departures=2*rotations,
                        saleable_added_seats_each_direction=100*rotations,
                        block_hours_added=2*rotations*co['block_hours_costscreen'],
                        elapsed_tail_hours_added=rotations*(2*co['block_hours_costscreen']+1.5),
                        positioning_hours=None, positioning_gate='initial and terminal location/crew/reserve UNKNOWN',
                        cost_one_leg=co['fixed_cost'], cost_paired_return=2*co['fixed_cost'],
                        annual_added_cost=totals['added_cost'], programme_total_known_cost=totals['total_cost'], keep_known_cost=totals['keep_cost'],
                        pax_ab=totals['pax_ab'], pax_ba=totals['pax_ba'], operating_pax=sumq,
                        keep_pax_ab=totals['keep_pax_ab'], keep_pax_ba=totals['keep_pax_ba'],
                        keep_pax=totals['keep_pax_ab']+totals['keep_pax_ba'],
                        additional_rw_pax=incq, new_sector_pax=totals['new_sector_pax'], own_rw_shift_to_new=totals['own_shifted'],
                        net_revenue_after=totals['net_revenue'], keep_net_revenue=totals['keep_net_revenue'],
                        known_increment_P_minus_KEEP_before_F_donor=None if allocation_gate else inc,
                        conditional_new_flight_subtotal_before_unallocated_old_RW=inc if allocation_gate else None,
                        old_RW_allocation_gate='unknown old city RW loss must enter F/KEEP, not assigned zero' if allocation_gate else 'explicit historical-frequency scenario',
                        F_plus_donor_max_RUB=None if allocation_gate else inc,
                        F_plus_donor_plus_unallocated_RW_loss_max_RUB=inc if allocation_gate else None,
                        donor_max_RUB_per_rotation=inc/rotations if rotations and not allocation_gate else None,
                        donor_max_RUB_per_occupied_tail_day=None,
                        donor_max_RUB_per_8h_block_equivalent_tail_day=inc/(2*rotations*co['block_hours_costscreen']/8) if rotations and not allocation_gate else None,
                        tail_day_basis='actual occupied calendar days UNKNOWN; block/8 is only scenario equivalent; positioning excluded gate',
                        F_pax_max_RUB_per_incremental_pax=inc/incq if incq>0 else None,
                        nonoverlap_pax_cost_stress_increment=inc-incq*co['pax_unknown_stress'],
                        required_pax_sum_at_equal_net=be_sum, required_pax_each_direction_at_equal_net=be_sum/2 if be_sum else None,
                        break_even_quantity_basis='incremental paid RW journeys over KEEP; existing own carried passengers not new',
                        required_total_RW_pax_sum_at_equal_net=(totals['keep_pax_ab']+totals['keep_pax_ba']+be_sum) if be_sum else None,
                        required_pax_per_added_leg=be_sum/(2*rotations) if rotations else None,
                        required_net_RUB_per_incremental_pax=totals['added_cost']/incq if incq>0 else None,
                        required_capture_of_prior_air_OD=be_sum/q if q else None,
                        required_incremental_capture_of_potential=be_sum/(q/.6) if q else None,
                        actual_conditional_incremental_capture_potential=incq/(q/.6) if q else None,
                        fuel_price_max_RUB_per_t=(totals['net_revenue']-totals['keep_net_revenue']-2*rotations*co['other_cost'])/(2*rotations*co['fuel_t']) if rotations else None,
                        same_tail_roundtrip_8h_diagnostic='EXCEEDS_SCENARIO_REQUIRES_MULTIDAY_OR_REDESIGN_CHECK' if 2*co['block_hours_costscreen']>8 else 'WITHIN_8H_COSTSCREEN_NOT_OPS_ADMISSION',
                        variant_track_payload_status='UNKNOWN_PRIORITY_LONG_LEG_CHECK' if co['distance_km']>2300 else 'UNKNOWN_REQUIRES_OPS_CHECK',
                        route_day_utilisation_lower_bound_8h=2*co['block_hours_costscreen']/8)


EN = {'Samara':'KUF','Nizhny Novgorod':'GOJ','Yekaterinburg':'SVX','Ufa':'UFA','Saratov':'GSV','Orenburg':'REN','Chelyabinsk':'CEK','Tyumen':'TJM','Omsk':'OMS','Krasnoyarsk':'KJA','Perm':'PEE','Kazan':'KZN','Arkhangelsk':'ARH','Murmansk':'MMK','Sochi':'AER','Kaliningrad':'KGD'}
RU = {'Екатеринбург':'SVX','Горно-Алтайск':'RGK','Томск':'TOF','Нижний Новгород':'GOJ','Ижевск':'IJK','Астрахань':'ASF','Грозный':'GRV','Ставрополь':'STW','Ургенч':'UGC'}


def universe():
    out = {}
    def add(a,b,source,season='all_year_scenario',scope='domestic',issue=''):
        key=pair(a,b)
        if key not in out:
            out[key]=dict(pair_id='-'.join(key), city_origin=key[0], city_destination=key[1], sources=[], season=season, scope=scope, source_issue=issue)
        out[key]['sources'].append(source)
        if issue:
            out[key]['source_issue']=issue
            out[key]['scope']=scope
    for r in read(ROOT/'audit/route_universe.csv'):
        add(r['origin'],r['destination'],'audit/route_universe.csv')
    for r in read(ROOT/'coordinator/calendar_corrected/wide_candidates.csv'):
        add(EN[r['origin']],EN[r['destination']],'coordinator/calendar_corrected/wide_candidates.csv')
    for r in read(ROOT/'source_review/canonical_portfolio_pairs.csv'):
        a,b=r['origin_iata'],r['destination_iata']
        issue='UNRESOLVED_ENDPOINT_COUNTRY_NO_NUMERIC_ADMISSION' if b=='BRU' else ''
        scope='unresolved_endpoint' if issue else 'supplemental_international' if r['scope']=='int' else 'domestic'
        add(a,b,'source_review/canonical_portfolio_pairs.csv',r['hypothesis_season'],scope,issue)
    for r in read(ROOT/'ideas_commercial/route_products.csv'):
        a,b=RU[r['origin']],RU[r['destination']]
        add(a,b,'ideas_commercial/route_products.csv',scope='supplemental_international' if b=='UGC' else 'domestic')
    result=[]
    for key,r in sorted(out.items()):
        r['sources']=';'.join(sorted(set(r['sources'])))
        r['directions']='>'.join(key)+';'+'>' .join(reversed(key))
        r['physical_origin_options']='DME;ZIA' if key[0]=='MOW' else key[0]
        r['physical_destination_options']='DME;ZIA' if key[1]=='MOW' else key[1]
        r['geography']=' / '.join(DEMAND.nodes.get(x,{}).get('region','UNKNOWN') for x in key)
        r['od_status']='SCENARIO_PRIOR_NOT_OBSERVED' if r['scope']=='domestic' else 'UNKNOWN_THRESHOLD_ONLY'
        r['ops_status']='requires_ops_check'
        result.append(r)
    return result


def physical_options(r):
    return [(a,b) for a in r['physical_origin_options'].split(';') for b in r['physical_destination_options'].split(';')]


def materialize_patterns(patterns, scenario, start, end):
    """Dated adjacent legs, every pattern MUST close, no free positioning."""
    flights=[]
    ids=set()
    movements=set()
    for p in patterns:
        if p['pattern_id'] in ids:
            raise ValueError('duplicate pattern id')
        ids.add(p['pattern_id'])
        airports=p['airports']
        if len(airports)<3 or airports[0]!=airports[-1]:
            raise ValueError('pattern must return aircraft; add priced positioning leg')
        if any(a==b for a,b in zip(airports,airports[1:])):
            raise ValueError('zero-length adjacent flight')
        if any(x=='MOW' for x in airports):
            raise ValueError('MOW is city OD, choose physical DME or ZIA')
        if len(set(p['weekdays']))!=len(p['weekdays']) or any(x not in range(7) for x in p['weekdays']):
            raise ValueError('duplicate/invalid weekday')
        for day in days_in(max(start,p.get('start',start)), min(end,p.get('end',end)), p['weekdays']):
            if 'months' in p and day.month not in p['months']:
                continue
            t=datetime.combine(day,datetime.min.time())+timedelta(hours=p.get('departure_hour_utc',6))
            for n,(a,b) in enumerate(zip(airports,airports[1:])):
                g,h=geometry(a,b)
                if h is None:
                    raise ValueError(f'unknown geometry/type/FX: supplemental threshold only {a}-{b}')
                t0=t
                t=t+timedelta(minutes=round(h*60))
                signature=(a,b,t0.isoformat())
                if signature in movements:
                    raise ValueError('duplicate physical scheduled movement across patterns')
                movements.add(signature)
                fid=f"{p['pattern_id']}:{day.isoformat()}:{n}"
                flights.append(dict(flight_instance_id=fid,pattern_id=p['pattern_id'],origin_airport=a,destination_airport=b,
                                    departure_utc=t0.isoformat()+'Z',arrival_utc=t.isoformat()+'Z',saleable_seats=p.get('seats',100),
                                    block_hours_costscreen=h,physical_adjacent_leg=True,source_status='scenario_pending_ops',
                                    aircraft_variant='SSJ100_SaM146_conditional_existing_or_new_type_cost_transfer_gate',
                                    scope=p.get('scope','project')))
                t=t+timedelta(minutes=45)
    return flights


def choice_bundle(flights, scenario, affected_pairs, start, end, demand_overrides=None, response='passive'):
    """One market per directed city OD/month, all flight alternatives share it.

    Monthly flexible travel scenario (not observed DOW). Direct adjacent segments
    only: triangles do not receive implicit transfers or duplicate through fares.
    """
    demand_overrides=demand_overrides or {}
    groups=defaultdict(list)
    for f in flights:
        groups[(city(f['origin_airport']),city(f['destination_airport']),f['departure_utc'][:7])].append(f)
    markets=[]; products=[]
    months=sorted({d.strftime('%Y-%m') for d in days_in(start,end,range(7))})
    for a,b in sorted(affected_pairs):
        for month in months:
            y,m=map(int,month.split('-'))
            q,src,via=annual(a,b,scenario,y)
            override=demand_overrides.get(f'{a}>{b}/{month}')
            if override is None and q is None:
                raise ValueError(f'UNKNOWN domestic demand {a}>{b}; explicit potential override needed')
            days_count=sum(1 for d in days_in(max(start,month+'-01'),min(end,f'{month}-{calendar.monthrange(y,m)[1]:02}'),range(7)))
            horizon_fraction=days_count/calendar.monthrange(y,m)[1]
            pot=q*.5*P05.monthly_profile(y)[m]/.6*horizon_fraction if override is None else override
            if pot < 0:
                raise ValueError('negative potential')
            market=dict(demand_pool_id=P05.pool(a,b),month=month,customer_segment='monthly_flexible_scenario',potential_journeys=pot,
                        market_basis='potential_travel',mapping_to_potential='P05 prior/.6 x directional .5; override if supplied',
                        source_id=src,source_period='2025 prior not observed OD',as_of='2026-11-12',coverage='monthly flexible conditional direct only',status='scenario',assumption_id='P05-A01;P05-A02;P05-A03;RE-A03')
            markets.append(market)
            prefix=f'{a}>{b}:{month}'
            for typ,weight in [('other_air',outside_mass(a,b,scenario,response)-.4),('ground',.3),('no_travel',.1)]:
                p=P05.product(prefix+':'+typ,market,'outside','OTHER',None,None,None,[],month+'-01',None,math.log(weight))
                products.append(p)
            fs=groups.get((a,b,month),[])
            by_airport=defaultdict(list)
            for f in fs:
                by_airport[(f['origin_airport'],f['destination_airport'])].append(f)
            for (pa,pb),inventory in sorted(by_airport.items()):
                # Shared airport alternatives: one MOW pool, uncalibrated access utility.
                freq=len(inventory)*7/calendar.monthrange(y,m)[1]
                gross,net=fare(pa,pb,scenario)
                h=sum(f['block_hours_costscreen'] for f in inventory)/len(inventory)
                weight=mass(pa,pb,freq,scenario,gross,h*60)
                c=P05.coefficients(scenario)
                intercept=math.log(weight)-math.log(len(inventory))-c['price_per_rub']*gross-c['time_per_minute']*(h*60)-c['log_frequency']*math.log(freq)
                for f in inventory:
                    products.append(P05.product('RW:'+f['flight_instance_id'],market,'air','RW',gross,f['block_hours_costscreen']*60,freq,[f['flight_instance_id']],f['departure_utc'][:10],net,intercept))
    return dict(markets=markets,products=products,flights=flights,contracts=[],choice_model=P05.coefficients(scenario))


def evaluate_combined_programme(patterns, scenario='base', keep_patterns=None,
                                start='2027-01-01', end='2028-12-31',
                                demand_overrides=None, donor_loss=None, omitted_F=None,
                                existing_slots=1, delivery_scenario='S0', reserve_available=None,
                                response='passive', extra_products=None, calendar_requests=None):
    """Recompute BOTH P and KEEP; never sum standalone marginal screen rows.

    keep_patterns is REQUIRED: [] explicitly means no affected old flights in
    this scope, not evidence of company KEEP=0. It must include all affected own
    products, including retained ones in patterns. Donor outside scope separate.
    extra_products (optional) can share flight legs across multiple city pools;
    P06 enforces joint physical seats. Caller owns its source/cohort admission.
    Full P06 operations/finance bundle remains assembler responsibility.
    """
    if keep_patterns is None:
        raise ValueError('explicit affected KEEP patterns required; unknown is not zero')
    if scenario not in ('base','cautious') or existing_slots not in (0,1,2) or delivery_scenario not in CONTRACT['resource']['deliveries']:
        raise ValueError('common scenario/resource contract')
    if not ('2027-01-01' <= start <= end <= '2028-12-31'):
        raise ValueError('outside common horizon')
    ops_results={}
    if calendar_requests is not None:
        if set(calendar_requests)!= {'P','KEEP'}:
            raise ValueError('calendar_requests needs complete P and KEEP requests')
        p_req,k_req=calendar_requests['P'],calendar_requests['KEEP']
        canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False)
        if canon(sorted(p_req['tails'],key=lambda t:t['id']))!=canon(sorted(k_req['tails'],key=lambda t:t['id'])):
            raise ValueError('P and KEEP must use identical external tail/resource calendar')
        for key,default in [('block_case','nominal'),('turn_minutes',45),('diagnostic_bh_day',8)]:
            if p_req.get(key,default)!=k_req.get(key,default):
                raise ValueError('P and KEEP must use same external block/turn scenario')
        for request in calendar_requests.values():
            directed=[(x['origin'],x['destination']) for x in request['blocks']]
            if len(set(directed))!=len(directed):
                raise ValueError('select explicit direction/variant source before calendar; no silent overwriting')
            blockmap={(x['origin'],x['destination']):x for x in request['blocks']}
            tailmap={x['id']:x for x in request['tails']}
            entries={x['id']:x['entry'] for x in CONTRACT['resource']['deliveries'][delivery_scenario]}
            for tail in request['tails']:
                if tail.get('reserve') and (tail['type'].startswith('SJ') or tail['id'].startswith('SJ-')):
                    if tail['id'] not in entries or start<entries[tail['id']]:
                        raise ValueError('new SJ cannot be reserve before common dated service entry')
            for pat in request['patterns']:
                for a,b in zip(pat['path'],pat['path'][1:]):
                    variant=blockmap.get((a,b),{}).get('aircraft_variant')
                    if variant is not None and any(tailmap[t]['type']!=variant for t in pat['workingtailids']):
                        raise ValueError('directed block analogue variant does not match selected tail')
        for key in set((x['origin'],x['destination']) for x in p_req['blocks']) & set((x['origin'],x['destination']) for x in k_req['blocks']):
            vals=[next(x for x in req['blocks'] if (x['origin'],x['destination'])==key) for req in [p_req,k_req]]
            if canon(vals[0])!=canon(vals[1]):
                raise ValueError('shared directed block assumption differs between P and KEEP')
        for label in ('P','KEEP'):
            ops_results[label]=OPS_CALENDAR.generate(calendar_requests[label])
        if any(x['status']=='INFEASIBLE' for x in ops_results.values()):
            return dict(version=VERSION,status='INFEASIBLE_CALENDAR_COMPOSITION_NOT_TRIMMED',
                        ops_results=ops_results,known_increment_P_minus_KEEP_before_F_donor=None,
                        full_P_minus_KEEP=None,cash=None,
                        error='No economics on partial rejected calendar. Resolve full fixed composition or explicitly evaluate a different programme.')
        def convert(label):
            tails={t['id']:t for t in calendar_requests[label]['tails']}
            return [dict(flight_instance_id=f['flight_id'],pattern_id=f['rotation_id'],origin_airport=f['origin'],destination_airport=f['destination'],
                         departure_utc=f['departure_utc'],arrival_utc=f['arrival_utc'],saleable_seats=tails[f['tail']].get('saleable_seats',100) if f['kind']=='service' else 0,
                         block_hours_costscreen=f['block_minutes']/60,physical_adjacent_leg=True,source_status=f['evidence'],
                         aircraft_variant=tails[f['tail']]['type'],calendar_kind=f['kind'],tail_id=f['tail'])
                    for f in ops_results[label]['flights']]
        pp,kk=convert('P'),convert('KEEP')
    else:
        pp=materialize_patterns(patterns,scenario,start,end)
        kk=materialize_patterns(keep_patterns,scenario,start,end)
    if any(not start <= f['departure_utc'][:10] <= end for f in pp+kk):
        raise ValueError('calendar flight outside common evaluation horizon')
    keys={pair(f['origin_airport'],f['destination_airport']) for f in pp+kk}
    directions={(a,b) for key in keys for a,b in (key,tuple(reversed(key)))}
    # Identical market set even where a product disappears in P or KEEP.
    results={}
    for label,flights in [('P',pp),('KEEP',kk)]:
        bundle=choice_bundle(flights,scenario,directions,start,end,demand_overrides,response)
        if extra_products:
            bundle['products'].extend(extra_products.get(label,[]))
        alloc=allocate_p06(bundle,bundle['products'])
        products={p['product_id']:p for p in bundle['products']}
        revenue=sum(a['carried']*products[a['product_id']]['net_fare'] for a in alloc['allocations'] if a['owner']=='RW')
        expense=sum(costs(f['origin_airport'],f['destination_airport'],scenario,f['block_hours_costscreen'])['fixed_cost'] for f in flights)
        monthrows=[]
        for month in sorted({m['month'] for m in bundle['markets']}):
            aa=[a for a in alloc['allocations'] if a['month']==month and a['owner']=='RW']
            ff=[f for f in flights if f['departure_utc'].startswith(month)]
            rev=sum(a['carried']*products[a['product_id']]['net_fare'] for a in aa)
            cost=sum(costs(f['origin_airport'],f['destination_airport'],scenario,f['block_hours_costscreen'])['fixed_cost'] for f in ff)
            monthrows.append(dict(month=month,directed_departures=len(ff),rw_journeys=sum(a['carried'] for a in aa),net_revenue=rev,known_cost=cost,known_contribution=rev-cost))
        results[label]=dict(net_revenue=revenue,known_cost=expense,known_contribution=revenue-expense,
                            rw_journeys=sum(a['carried'] for a in alloc['allocations'] if a['owner']=='RW'),
                            monthly=monthrows,allocation=alloc,bundle=bundle)
    increment=results['P']['known_contribution']-results['KEEP']['known_contribution']
    violations=[]
    for label,fs in [('P',pp),('KEEP',kk)]:
        daily=Counter()
        used=defaultdict(set)
        if calendar_requests is not None:
            for r in ops_results[label]['daily']:
                daily[r['date']]+=r['block_hours']
                used[r['date']].add(r['tail'])
            entries={x['id']:x['entry'] for x in CONTRACT['resource']['deliveries'][delivery_scenario]}
            for f in fs:
                if f['aircraft_variant'].startswith('SJ') or f['tail_id'].startswith('SJ-'):
                    if f['tail_id'] not in entries or f['departure_utc'][:10]<entries[f['tail_id']]:
                        violations.append(dict(programme=label,day=f['departure_utc'][:10],tail=f['tail_id'],gate='NEW_SJ_NOT_YET_AVAILABLE_IN_COMMON_SCENARIO'))
        else:
            for f in fs:
                daily[f['departure_utc'][:10]]+=f['block_hours_costscreen']
        for day,hours in sorted(daily.items()):
            working=existing_slots+sum(x['entry']<=day for x in CONTRACT['resource']['deliveries'][delivery_scenario])
            if hours>8*working+1e-9:
                violations.append(dict(programme=label,day=day,block_hours=hours,working_slots=working))
            if len(used[day])>working:
                violations.append(dict(programme=label,day=day,assigned_working_tails=len(used[day]),working_slots=working))
    return dict(version=VERSION,status='CONDITIONAL_CALENDAR_PENDING_CREW_MRO_OPS' if calendar_requests is not None else 'CONDITIONAL_COSTSCREEN_PENDING_OPS',scenario=scenario,support='NS',
                calendar_mode='ops_inputs.calendar_engine same-direction/variant admitted analogue or explicit scenario' if calendar_requests is not None else 'GEOMETRY_COSTSCREEN_DATES_NOT_VALID_BLOCKS',
                ops_results=ops_results,
                programme=results['P'],keep=results['KEEP'],known_increment_P_minus_KEEP_before_F_donor=increment,
                F_plus_donor_max_RUB=increment,full_P_minus_KEEP=increment-donor_loss-omitted_F if donor_loss is not None and omitted_F is not None else None,
                full_result_status='conditional_given_all_F_and_donor' if donor_loss is not None and omitted_F is not None else 'UNKNOWN',
                cash=None,peak_funding=None,resource_necessary_screen='INFEASIBLE_AT_GIVEN_ENVELOPE' if violations or reserve_available is False else 'RESERVE_UNKNOWN_GATE' if reserve_available is None else 'PENDING_OPS',
                daily_block_violations=violations,separate_reserve_required=1,reserve_available=reserve_available,
                existing_slots=existing_slots,delivery_scenario=delivery_scenario,
                gates=['donor actual and unavoidable payments','crew/rest/MRO/tails/positioning/slots','modification/payload/actual track/seasonal block','tax/airport/pax-cost/aircraft-use F','MOW airport allocation where applicable'],
                additivity='DO_NOT_SUM_SOLO_MARGINS; use this function over merged P and KEEP patterns')


def input_manifest():
    sources=[]
    for r in json.loads((ROOT/'audit/source_manifest.json').read_text()):
        local=Path(r['local_path'])
        if local.exists():
            if digest(local)!=r['sha256']:
                raise ValueError('audit pinned blob hash mismatch: '+str(local))
            sources.append(dict(path=str(local.relative_to(ROOT)),sha256=r['sha256'],commit=r['commit'],admission='IMMUTABLE_GIT_BLOB_NOT_SOURCE_VALIDATION'))
    superseded={'ideas_portfolio/pairs.csv','ideas_portfolio/sources.csv','market_supplemental/sources.csv','market_supplemental/directed_services.csv','market_supplemental/route_evidence.csv','coordinator/calendar_corrected/directed_schedule_rows.csv'}
    for folder in ['market_domestic','market_supplemental','ideas_portfolio','ideas_commercial','coordinator/calendar_corrected','source_review','ops_inputs']:
        for f in sorted((ROOT/folder).glob('*')):
            if f.is_file():
                path=str(f.relative_to(ROOT))
                sources.append(dict(path=path,sha256=digest(f),commit=None,
                                    admission='SUPERSEDED_METADATA_USE_SOURCE_REVIEW_CANONICAL' if path in superseded else 'COMPLETED_PACKAGE_WITH_REVIEW_ADMISSION_LIMITS'))
    for f in ['audit/route_universe.csv','audit/common_contract.json','TASKS.md','remote_pins.json']:
        sources.append(dict(path=f,sha256=digest(ROOT/f),commit=None,admission='LOCAL_COORDINATION_INPUT'))
    raw=WORKSPACE/'context/30_defense_research_20261111/inputs/model_schedule/latest/data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv'
    expected='aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53'
    if not raw.exists() or digest(raw)!=expected:
        raise ValueError('raw audit snapshot absent/hash mismatch')
    sources.append(dict(path=str(raw.relative_to(WORKSPACE)),sha256=expected,commit=None,admission='PRIOR_AUDIT_RAW_SNAPSHOT_NOT_GIT_PRIMARY_NOT_NEW_EVIDENCE_NOT_USED_TO_INVENT_OD'))
    return sources


def build():
    manifest=input_manifest()
    u=universe()
    table('route_universe.csv',u)
    screens=[]
    for r in u:
        for a,b in physical_options(r):
            if r['scope']!='domestic':
                for scenario in ('base','cautious'):
                    for freq in GRID:
                        screens.append(dict(pair_id=r['pair_id'],physical_pair=f'{a}-{b}',origin=a,destination=b,scope=r['scope'],scenario=scenario,year=2027,
                                            support='NS',added_pairs_week=freq,screen_status='SUPPLEMENTAL_QUANT_THRESHOLD_ONLY',endpoint_od_observed=None,
                                            full_P_minus_KEEP=None,known_increment_P_minus_KEEP_before_F_donor=None,ops_status='requires_ops_check',
                                            source_issue=r['source_issue'],reliability='UNKNOWN_FX_RIGHTS_TRACK_TAX_TYPE_DEMAND_NETYIELD'))
                continue
            for scenario in ('base','cautious'):
                for year in (2027,2028):
                    for freq in GRID:
                        screens.append(screen(a,b,freq,scenario,year))
    table('fastscreen.csv',screens)
    # Finite diverse shortlist: top six conditional rows without base positioning,
    # top four outside-base ordinary markets (positioning remains a gate), plus
    # six evidence-sensitive packages. No global optimisation claim.
    valid=[r for r in screens if r.get('year')==2027 and r['scenario']=='base' and r.get('known_increment_P_minus_KEEP_before_F_donor') is not None and r.get('published_closure_status')!='SNAPSHOT_RESTRICTED_REOPEN_GATE' and 'MOW' not in pair(r['origin'],r['destination'])]
    best={}
    for r in valid:
        key=r['pair_id']
        if key not in best or r['known_increment_P_minus_KEEP_before_F_donor']>best[key]['known_increment_P_minus_KEEP_before_F_donor']:
            best[key]=r
    ordered=sorted(best.values(),key=lambda r:(-r['known_increment_P_minus_KEEP_before_F_donor'],r['pair_id']))
    chosen=[]
    for group,n in [(list(filter(lambda r:'SVX' in pair(r['origin'],r['destination']),ordered)),6),(list(filter(lambda r:'SVX' not in pair(r['origin'],r['destination']),ordered)),4)]:
        chosen.extend(group[:n])
    for a,b in [('KUF','GOJ'),('SVX','GOJ'),('CEK','MRV'),('TJM','MRV'),('OMS','UFA'),('SVX','TJM')]:
        k=pid(a,b)
        if k in best and all(x['pair_id']!=k for x in chosen):
            chosen.append(best[k])
    shortlist=[]
    for rank,r in enumerate(chosen,1):
        caution=screen(r['origin'],r['destination'],r['added_pairs_week'],'cautious',2027)
        shortlist.append(r|dict(screen_priority=rank,rank_meaning='finite conditional evidence/threshold priority NOT profit recommendation',
                                cautious_same_frequency_increment=caution.get('known_increment_P_minus_KEEP_before_F_donor'),
                                cautious_required_pax_each_direction=caution.get('required_pax_each_direction_at_equal_net'),
                                cautious_net_fare=caution.get('net_fare_ab'),
                                donor_gate='UNKNOWN actual KEEP; signed released tail+reserve+positioning required',
                                launch_gate='OBSERVED_OD_NETYIELD_COST_OPS_DONOR_ALL_UNKNOWN',
                                base_to_cautious='P05 lower OD prior + .962 annual stress; VAT/distribution; P04 burn/hour rates; fuel/airport/deice transfer stress'))
    table('shortlist.csv',shortlist)
    table('candidate_score.csv',shortlist)
    detailed=chosen[:8]
    cases=[];frequencies=[];thresholds=[];patterns=[];monthly=[];support=[]
    for r in chosen:
        a,b,freq=r['origin'],r['destination'],r['added_pairs_week']
        for scenario in ('base','cautious'):
            s=screen(a,b,freq,scenario)
            for f in GRID:
                z=screen(a,b,f,scenario)
                frequencies.append(z|dict(case_type='old_plus_new_SHARED_OD_TOTAL_RW_MINUS_KEEP',existing_frequency_status='PINNED_HISTORICAL_FREQUENCY_TRANSFER_SCENARIO_NOT_FUTURE_FACT'))
            gain=s['known_increment_P_minus_KEEP_before_F_donor']; n=s['added_rotations']; qinc=s['additional_rw_pax']
            for kind,qblock,sell in [('partner_block',20,10),('partner_block',20,16),('partner_block',20,20)]:
                # Unit grid is a threshold illustration, not an offer or sales forecast.
                thresholds.append(dict(pair_id=s['pair_id'],scenario=scenario,mechanism=kind,q_purchased=qblock,s_sold=sell,
                                       net_retail_scenario_RUB=s['net_fare_ab'],other_expense_RUB='F_unknown',target_contribution_RUB=0,
                                       c_max_RUB_per_seat_before_F=sell*s['net_fare_ab']/qblock,
                                       formula='cmax=(s*netretail-other_expenses-target_contribution)/q; q*c ONCE',
                                       RW_operating_pax=0,contract_status='UNKNOWN_PARTNER_QUOTE_AND_RELEASE_RULES',baseline='partner alternative; not extra own flight revenue'))
            for kg in (100,300,500):
                deficit=max(0,-gain)/max(1,2*n)
                thresholds.append(dict(pair_id=s['pair_id'],scenario=scenario,mechanism='cargo',accepted_kg_scenario=kg,
                                       required_net_RUB_per_kg_before_unknown_costs=deficit/kg,
                                       formula='(deficit+handling+extra_fuel+displacement+target)/accepted_kg',
                                       payload_volume_gate='accepted kg <= residual mass AND volume after PAX+baggage; UNKNOWN; not 4.2t free',
                                       contract_status='UNKNOWN_DEMAND_RATE_ACCEPTANCE',baseline='existing paid physical flights; no invented cargo revenue'))
            thresholds.append(dict(pair_id=s['pair_id'],scenario=scenario,mechanism='donor_and_omitted_F',F_plus_donor_max_RUB=gain,
                                   max_donor_loss_RUB_per_rotation=gain/n,formula='full_delta=known_delta-F-donor_loss; donor not revenue; old RW deduction once',
                                   contract_status='UNKNOWN_REAL_DONOR_KEEP_UNAVOIDABLE_PAYMENTS',baseline='same resource calendar and market for P/KEEP'))
            support.append(dict(pair_id=s['pair_id'],scenario=scenario,support_case='NS',route_support_RUB=0,fuel_credit_RUB=0,actual_future_award=None,
                                conditional_increment=gain,recognition='both mechanisms intentionally zero'))
            support.append(dict(pair_id=s['pair_id'],scenario=scenario,support_case='CM',route_support_RUB=None,fuel_credit_RUB=None,actual_future_award=None,
                                conditional_increment=None,mechanism_source='P04/support_terms.csv; support_eligibility_rules.csv; source URL/period retained in source_admission',
                                gate='named operator agreement+applicable period+special fare+eligible flights/volume+regional cofunding+taxpayer+payment dates',
                                formula='recompute fare-coupled demand/net revenue; add eligible route grant once; fuel credit reduces fuel cost once',
                                prohibited='185228 not signed grant; 32930 not 2027 forecast; no automatic 7/12'))
            co=costs(a,b,scenario)
            for credit in (3024,32930):
                support.append(dict(pair_id=s['pair_id'],scenario=scenario,support_case='HISTORICAL_FUEL_DIAGNOSTIC_ONLY',route_support_RUB=0,
                                    fuel_credit_rate_RUB_per_t=credit,fuel_credit_RUB=2*n*co['fuel_t']*credit,
                                    conditional_increment=gain+2*n*co['fuel_t']*credit,actual_future_award=None,
                                    recognition='separate unawarded diagnostic; not CM or expected future support'))
        # Balanced directions remain physical even when demand is asymmetric.
        if r in detailed:
            for scenario in ('base','cautious'):
                for fraction in (.2,.35,.5,.65,.8):
                    z=screen(a,b,freq,scenario,direction_fraction=fraction)
                    cases.append(z|dict(case_id=f'{pid(a,b)}/{scenario}/dir{fraction}',direction_fraction_ab=fraction,
                                        direction_basis='P05-A02 directional scenario; observed directional OD/DOW UNKNOWN',
                                        break_even_total_ab_given_ba=max(0,(z['annual_added_cost']+z['keep_net_revenue']-z['pax_ba']*z['net_fare_ba']))/z['net_fare_ab'],
                                        directional_threshold_note='total required AB passengers given BA, preserves full KEEP revenue; before F/donor',
                                        frequency_balance='equal paid physical outward and return legs; no free positioning'))
                gross=fare(a,b,scenario)[0]
                for ma,mb in [(.8,1.0),(1.0,.8),(1.2,1.0),(1.0,1.2)]:
                    z=screen(a,b,freq,scenario,gross_ab=gross*ma,gross_ba=gross*mb)
                    dqa=z['pax_ab']-z['keep_pax_ab']; dqb=z['pax_ba']-z['keep_pax_ba']
                    cases.append(z|dict(case_id=f'{pid(a,b)}/{scenario}/gross{ma}-{mb}',direction_fraction_ab=.5,
                                        direction_basis='symmetric OD, different common scenario directed gross fares; NOT observed LF',
                                        tariff_scenario='both P and KEEP repriced consistently; P05 choice recalculated; not posted fare data',
                                        break_even_net_BA_given_AB=(z['annual_added_cost']-dqa*z['net_fare_ab'])/dqb if dqb>0 else None,
                                        frequency_balance='equal paid physical outward and return legs'))
                # Bound of profitable directional fractions, recomputed with caps/KEEP.
                good=[]
                for k in range(101):
                    z=screen(a,b,freq,scenario,direction_fraction=k/100)
                    if z['known_increment_P_minus_KEEP_before_F_donor']>=0: good.append(k/100)
                thresholds.append(dict(pair_id=pid(a,b),scenario=scenario,mechanism='directional_asymmetry',
                                       fraction_ab_min_grid=min(good) if good else None,fraction_ab_max_grid=max(good) if good else None,
                                       resolution=.01,formula='recompute both capped directions at each fraction; paired cost retained',
                                       contract_status='SCENARIO_BOUNDARY_NOT_OBSERVED_DIRECTIONAL_OD'))
                lo,hi=0.0,32.0
                possible=screen(a,b,freq,scenario,demand_multiplier=hi)['known_increment_P_minus_KEEP_before_F_donor']>=0
                if possible:
                    for _ in range(36):
                        mid=(lo+hi)/2
                        if screen(a,b,freq,scenario,demand_multiplier=mid)['known_increment_P_minus_KEEP_before_F_donor']>=0:hi=mid
                        else:lo=mid
                thresholds.append(dict(pair_id=pid(a,b),scenario=scenario,mechanism='shared_paid_demand_threshold',
                                       prior_multiplier_break_even=hi if possible else None,
                                       formula='recompute SAME P and KEEP city OD and capacities; above-grid not assumed feasible',contract_status='CONDITIONAL_NO_F_DONOR'))
                s=screen(a,b,freq,scenario)
                retention=1+(s['annual_added_cost']-s['new_sector_pax']*s['net_fare_ab'])/s['keep_net_revenue'] if s['keep_net_revenue']>0 else None
                thresholds.append(dict(pair_id=pid(a,b),scenario=scenario,mechanism='own_rw_retention',
                                       minimum_old_revenue_retention_given_new_sector_sales=retention,
                                       formula='new_sector_net_revenue - (1-retention)*KEEP_net_revenue - added_cost >=0; not new customers',
                                       contract_status='CONDITIONAL_NO_F_DONOR; retention>1 unattainable without more new sales/yield or lower cost'))
                for month in range(1,13):
                    z=screen(a,b,freq,scenario,selected_months=(month,))
                    monthly.append(dict(pair_id=pid(a,b),scenario=scenario,month=f'2027-{month:02}',direction_fraction=.5,
                                        departures_each_direction=z['added_rotations'],pax_ab=z['pax_ab'],pax_ba=z['pax_ba'],
                                        net_revenue_after=z['net_revenue_after'],keep_net_revenue=z['keep_net_revenue'],known_increment=z['known_increment_P_minus_KEEP_before_F_donor'],
                                        profile_basis='P05-A03 carrier national season analogue NOT observed route/DOW'))
            home=a if a=='SVX' else b if b=='SVX' else a
            away=b if home==a else a
            for label,days in [('spread',DAY_GRID[freq]),('weekday',tuple(range(min(freq,5)))),('weekend',(5,6))]:
                pattern=dict(pattern_id=f'{pid(a,b)}:{label}',airports=[home,away,home],weekdays=list(days),start='2027-01-01',end='2028-12-31',
                             seats=100,departure_hour_utc=6,status='pending_ops',DOW_preference='UNIDENTIFIED_SCENARIO_EQUAL_DAILY_DEMAND',
                             positioning_gate='nonbase starts need explicit paid positioning+overnight/tail allocation' if home!='SVX' else 'SVX tail+donor/reserve release gate')
                patterns.append(pattern)
    table('directed_route_cases.csv',cases)
    table('frequency_increment_cases.csv',frequencies)
    table('mechanism_thresholds.csv',thresholds)
    table('support_cases.csv',support)
    table('monthly_route_cases.csv',monthly)
    # Calendar comparison actually runs P06 shared allocation; no claim of better DOW.
    pattern_cases=[]
    for p in patterns:
        for scenario in ('base','cautious'):
            # Existing KEEP footprint uses explicit continuous-history-to-dated scenario.
            a,b=p['airports'][:2]
            old=float(RW.get(pair(a,b),{}).get('freq_week_each_way',0))
            olddays=tuple(range(min(7,max(0,round(old)))))
            keep=[dict(pattern_id=pid(a,b)+':old',airports=p['airports'],weekdays=list(olddays),departure_hour_utc=15)] if olddays else []
            z=evaluate_combined_programme(keep+[p],scenario,keep_patterns=keep,start='2027-07-01',end='2027-07-31',existing_slots=2,reserve_available=None)
            pattern_cases.append(dict(pattern_id=p['pattern_id'],scenario=scenario,month='2027-07',
                                      airports=';'.join(p['airports']),weekdays=';'.join(map(str,p['weekdays'])),
                                      paired_rotations=len(z['programme']['bundle']['flights'])/2-len(z['keep']['bundle']['flights'])/2,
                                      known_increment=z['known_increment_P_minus_KEEP_before_F_donor'],
                                      demand_calendar='monthly_flexible P05 season; observed DOW UNKNOWN',
                                      old_calendar='rounded historical frequency assigned days SCENARIO_NOT_FACT',ops_status='pending_ops'))
    table('route_patterns.csv',[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in p.items()} for p in patterns])
    table('pattern_calendar_cases.csv',pattern_cases)
    dump('patterns.json',patterns)
    # Six finite triangles, adjacent-leg direct ODs only, all legs and return paid.
    triangles=[]
    partners=[x for x in chosen if 'SVX' in pair(x['origin'],x['destination'])]
    for r1,r2 in list(zip(partners,partners[1:]))[:6]:
        b=next(x for x in pair(r1['origin'],r1['destination']) if x!='SVX')
        c=next(x for x in pair(r2['origin'],r2['destination']) if x!='SVX')
        p=dict(pattern_id=f'TRI:SVX-{b}-{c}',airports=['SVX',b,c,'SVX'],weekdays=[1,4],departure_hour_utc=6)
        for scenario in ('base','cautious'):
            z=evaluate_combined_programme([p],scenario,keep_patterns=[],start='2027-07-01',end='2027-07-31',existing_slots=2)
            triangles.append(dict(pattern_id=p['pattern_id'],scenario=scenario,airports=';'.join(p['airports']),weekdays='1;4',
                                  month='2027-07',directed_departures=len(z['programme']['bundle']['flights']),
                                  known_increment_before_affected_KEEP_F_donor=z['known_increment_P_minus_KEEP_before_F_donor'],
                                  full_P_minus_KEEP=None,KEEP_gate='empty affected KEEP is a scenario; actual affected RW/donor UNKNOWN',
                                  ops_status='pending_ops',demand='one directional monthly OD per adjacent leg; no transfers or double through-fare'))
        patterns.append(p|dict(status='pending_ops',DOW_preference='UNIDENTIFIED_SCENARIO'))
    dump('patterns.json',patterns)
    table('triangle_cases.csv',triangles)
    table('route_patterns.csv',[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in p.items()} for p in patterns])
    competition=[]
    for r in chosen:
        for scenario in ('base','cautious'):
            a,b,f=r['origin'],r['destination'],r['added_pairs_week']
            z=screen(a,b,f,scenario,response='price_match10')
            competition.append(dict(pair_id=r['pair_id'],scenario=scenario,response='incumbent_residual_fare_minus10percent_SCENARIO',
                                    observed_competitor_frequency=None,observed_competitor_capacity=None,
                                    conditional_increment=z['known_increment_P_minus_KEEP_before_F_donor'],
                                    incremental_RW_pax=z['additional_rw_pax'],own_rw_shift=z['own_rw_shift_to_new'],
                                    required_capture_of_prior_air_OD=z['required_capture_of_prior_air_OD'],
                                    interpretation='P05 coefficient response sensitivity, not calibrated forecast; no exclusion for competitor presence'))
    table('competition_cases.csv',competition)
    # Preserve all multiple-source rows. Only same direction AND same variant
    # analogue rows may form a paired threshold. Never infer a reverse block.
    analogues=[r for r in read(ROOT/'ops_inputs/directed_blocks.csv') if r['evidence']=='SCENARIO_HISTORICAL_SAME_DIRECTED_ROUTE_VARIANT_ANALOGUE']
    table('block_admission.csv',analogues)
    analogue_cases=[]
    for r in analogues:
        reverses=[s for s in analogues if (s['origin'],s['destination'],s['aircraft_variant'])==(r['destination'],r['origin'],r['aircraft_variant'])]
        if r['origin']>r['destination']:
            continue
        if not reverses:
            analogue_cases.append(dict(pair_id=pid(r['origin'],r['destination']),variant=r['aircraft_variant'],
                                       admission='MISSING_REVERSE_SAME_VARIANT; no geometry substitute',profit=None))
            continue
        for s in reverses:
            for block_case in ('nominal','high'):
                for scenario in ('base','cautious'):
                    a,b=r['origin'],r['destination']
                    ha,hb=float(r[block_case+'_minutes'])/60,float(s[block_case+'_minutes'])/60
                    ca,cb=costs(a,b,scenario,ha),costs(b,a,scenario,hb)
                    gross,net=fare(a,b,scenario)
                    paired=ca['fixed_cost']+cb['fixed_cost']
                    analogue_cases.append(dict(pair_id=pid(a,b),variant=r['aircraft_variant'],block_case=block_case,scenario=scenario,
                                               origin=a,destination=b,block_minutes_ab=ha*60,block_minutes_ba=hb*60,
                                               roundtrip_known_cost_RUB=paired,scenario_net_RUB=net,minimum_paid_pax_sum_before_KEEP_F_donor=paired/net,
                                               minimum_paid_pax_each_symmetric=paired/net/2,
                                               source_ab=r['source_id']+':'+r['source_row'],source_ba=s['source_id']+':'+s['source_row'],
                                               admission='EXPLICIT_HISTORICAL_ANALOGUE_PENDING_OPS; not dispatch block or future bound',profit=None))
    table('ops_analogue_cost_cases.csv',analogue_cases)
    admission=[]
    for s in manifest:
        admission.append(s|dict(metric_status='scenario_or_reference_only',new_endpoint_OD_confirmed=False,new_realised_netyield_confirmed=False))
    admission.extend(dict(path='source_review/source_admission.csv#'+r['row_id'],admission=r['numeric_use'],source_url=r['source_url'],
                          source_date=r['source_date'],checked_date=r['checked_date'],taken_fact=r['taken_fact'],
                          metric_status=r['verdict'],limit=r['reason_and_impact']) for r in read(ROOT/'source_review/source_admission.csv'))
    for key in ['UFA-fuel-20261111','UFA-fuel_uplift']+[x for x in COSTS if x.startswith('HIST-')]:
        r=COSTS[key]
        admission.append(dict(path='P04/cost_ranges.csv#'+key,admission='EXPLICIT_SCENARIO_TRANSFER_NOT_FUTURE_CONTRACT',
                              source_url=r['source_url'],source_date=r['effective_from'],checked_date=r['as_of'],
                              taken_fact=r['value'] or (r['base_point']+' / '+r['cautious_point']),unit=r['unit'],
                              metric_status=r['status'],tax_basis=r['tax_basis'],limit=r['range_basis']))
    admission.append(dict(path='source_review/canonical_portfolio_pairs.csv:SVX-BRU',admission='UNRESOLVED_ENDPOINT_COUNTRY; no numeric route admission; no guessed code mapping',metric_status='source_metadata_gate'))
    admission.append(dict(path='coordinator/calendar_corrected/corrections.json',admission='KUF-GOJ 18:20 UTC4 to18:40 UTC3 =80min; NOT schedule mismatch; secondary authenticity unchanged',metric_status='correction'))
    table('source_admission.csv',admission)
    assumptions=[
        ('P05-A01/A02/A03/A04/A05','OD prior; direction .5; national carrier season; cautious .962; potential / .6','SCENARIO_NOT_OBSERVED','UNKNOWN empirical bounds'),
        ('P05-A06/A10/A11','gross20kg basket -> net VAT/distribution once; no legacy net yield','SCENARIO_NOT_REALIZED','VAT0 regional eligibility; actual tax UNKNOWN'),
        ('P05-A07','price/time/log_frequency coefficients','SCENARIO_NOT_IDENTIFIED','capture/retention conditional; no universal65%'),
        ('RE-A03','weekly frequency reference3; flexible month; residual .6otherair+.3ground+.1no travel','ANALYST_EXTENSION','current other-air inventory and modal shares UNKNOWN'),
        ('RE-COST01/AUDIT-COST01','P04 HIST rates; UFA fuel136300+uplift1696 transferred; cautious161696; airport96089/115307; deice15000/40000','EXPLICIT_SCENARIO_TRANSFER_CONSTANT2026RUB','not future contract or empirical bounds; geometry1.1 only costscreen'),
        ('RE-COST02','opaque pax500/650 EXCLUDED main to avoid distribution overlap; separate nonoverlap stress and Fmax','UNKNOWN_F_PAX','distribution once; no physical pax service assumed free in full result'),
        ('RE-COST03','costs ex VAT reference; VAT recovery/timing UNKNOWN; no fixed payroll added over HISTcrew; reserve/lease/startup/exit/positioning UNKNOWN','UNKNOWN_FULL_COST_F','full P-KEEP/cash null until supplied'),
        ('RE-RW01','historical old freq transferred to same future demand; aggregated total own frequency and seats','SCENARIO_NOT_FUTURE_KEEP','old RW deducted once; shift to new is not new customer'),
        ('RE-MOW01','DME/ZIA physical alternatives share ONE city OD; old city freq unallocated => gate','UNKNOWN_AIRPORT_ALLOCATION','solo alternatives never sum; combined recalc required'),
        ('RE-DOW01','spread/weekday/weekend finite alternatives; equal demand within month','SCENARIO_NO_OBSERVED_DOW','do not call different posted fares different LF'),
        ('RE-OPS01','100 seats;45min turns;8block_h/working_tail/day; separate reserve; no early SJ100','P03_COMMON_DIAGNOSTIC_PENDING_OPS','costscreen not dispatch/type/payload approval'),
        ('RE-KEEP01','affected future KEEP required; donor outside affected scope and missingF separate threshold','UNKNOWN','nonreturnable committed payments remain; company budget not0'),
    ]
    table('assumptions.csv',[dict(assumption_id=i,value=v,status=s,limits=l) for i,v,s,l in assumptions])
    table('ranges.csv',[dict(parameter='net_yield',lower=None,upper=None,threshold='cost/incremental_paid_pax; not confidence interval'),
                        dict(parameter='F_plus_donor',lower=None,upper=None,threshold='known increment (signed); see shortlist'),
                        dict(parameter='directed_fraction',lower=0,upper=1,threshold='scenario domain; mechanism_thresholds gives finite0.01 grid'),
                        dict(parameter='competition_capture_retention',lower=None,upper=None,threshold='conditional P05 logit; empirical parameters UNKNOWN'),
                        dict(parameter='cargo_accepted_kg',lower=None,upper=None,threshold='payload and volume after PAX+baggage required; grids100/300/500not capacity'),
                        dict(parameter='fuel_RUB_per_t',lower=None,upper=None,threshold='remaining net revenue after other costs / tonnes; fastscreen fuel_price_max')])
    supplemental=[]
    for r in u:
        if r['scope']!='domestic':
            supplemental.append(dict(pair_id=r['pair_id'],demand=None,net_fare=None,profit=None,
                                     minimum_total_paid_pax_formula='(all_leg_cost_RUB+F+donor-confirmed_support)/(directed_weighted_net_RUB_per_journey)',
                                     cost_formula='fuel_foreign*FX + airport_tax*FX + actual_track_burn + navigation + crew/MRO + domestic_costs',
                                     max_FX_formula='(net_revenue_RUB-domestic_cost-F-donor)/(foreign_cost_LOCAL); only with compatible revenue FX',
                                     gates='traffic rights/operator/date; FX; foreign tax/fees; actual track; variant/payload; tail availability; contract demand',
                                     source_issue=r['source_issue']))
            if r['scope']!='unresolved_endpoint':
                for roundtrip_cost in (1000000,1500000,2000000):
                    for net in (8000,12000,20000):
                        supplemental.append(dict(pair_id=r['pair_id'],scope='illustrative_threshold_axes_not_cost_or_yield_estimate',
                                                 assumed_all_in_paired_cost_RUB=roundtrip_cost,assumed_directed_net_RUB=net,
                                                 minimum_paid_pax_both=roundtrip_cost/net,minimum_paid_pax_each_symmetric=roundtrip_cost/net/2,
                                                 physical_capacity_test_100_each='EXCEEDS_200' if roundtrip_cost/net>200 else 'WITHIN_SEATS_NOT_DEMAND_OR_OPS',
                                                 demand=None,net_fare=None,profit=None,gates='ALL actual costs, directed sales, FX, rights, track, type UNKNOWN; F/donor excluded axes'))
    table('supplemental_thresholds.csv',supplemental)
    handoff=dict(version=VERSION,status='READY_CONDITIONAL_SCREEN_NOT_LAUNCH',write_scope=str(HERE),
                 canonical_contract='../audit/common_contract.json',function='calculate.evaluate_combined_programme',
                 source_review_gate='../source_review/README.md; canonical_*.csv and R01-R27 admission applied; numerical OD/netyield/contracts updates=0',
                 ops_input_gate='../ops_inputs/handoff.json; preserve multiple directed sources/variants; published minutes not future dispatch',
                 minimum_call="evaluate_combined_programme(patterns, 'base', keep_patterns=[], existing_slots=1, delivery_scenario='S0', reserve_available=None)",
                 keep_warning='[] asserts no affected old own products ONLY for this scope; not KEEP company=0. Include all retained affected RW in both P and KEEP.',
                 tables=['route_universe.csv','fastscreen.csv','candidate_score.csv','shortlist.csv','route_patterns.csv','patterns.json','pattern_calendar_cases.csv','triangle_cases.csv','directed_route_cases.csv','frequency_increment_cases.csv','mechanism_thresholds.csv','support_cases.csv','competition_cases.csv','block_admission.csv','ops_analogue_cost_cases.csv','ranges.csv','source_admission.csv','assumptions.csv','supplemental_thresholds.csv'],
                 scenario_ids=['base','cautious'],support='NS default; CM UNKNOWN conditional only',period=['2027-01-01','2028-12-31'],
                 parameters=dict(patterns='complete P physical closed patterns incl retained old RW',keep_patterns='same affected future scope physical closed patterns',
                                 demand_overrides='directed city>city/YYYY-MM -> potential journeys; identical for P/KEEP',
                                 donor_loss='outside-scope signed forgone donor contribution RUB or null; no double deduction',omitted_F='aggregate net omitted incremental costs RUB or null',
                                 existing_slots='E0/E1/E2 conditional working slots',delivery_scenario='S0/S1/S1D6 common audit entry dates',reserve_available='bool or null; separate tail',
                                 response='passive or price_match10 conditional incumbent residual scenario',extra_products='optional P/KEEP products sharing dated legs and city pools; source/cohort admission caller'),
                 calendar_requests='optional complete {P: ops_inputs.calendar_engine request, KEEP: request}; rejects any partial/infeasible composition; no geometric block fallback. Supply admitted directed blocks and variant, airport IANA zones, tails/reserve and crew/MRO gates.',
                 return_fields=['programme/keep bundle choice fragments','allocation: common OD conservation, dated shared seats','monthly directed departures/RW journeys/revenue/cost','known_increment_P_minus_KEEP_before_F_donor','F_plus_donor_max_RUB','full_P_minus_KEEP nullable','daily resource necessary violations','cash null'],
                 assembler_must_add=['actual dated tail/crew/rest/MRO/reserve/positioning and blocktime to P03','P04 full economic/cash events and tax/contract coverage','current competition and calibrated OD/netyield','all affected RW own connections/donor scope','P06 producer_contract validation before feasible/full result claim'],
                 rules=['NEVER_SUM_SOLO_MARGIN_TABLES','same market calendar and costs for all networks and KEEP','MOW physical DME/ZIA ONE city pool','no new SJ100 before H22027 in any role','emptyfleet_budget_UNKNOWN_not_zero','pending_ops is not feasible'],
                 scope='No new hub; triangles only direct adjacent-leg OD. Full-company KEEP cash and unknown own connections not fabricated.',
                 counts=dict(seed_pairs=1317,city_pairs=len(u),fastscreen_rows=len(screens),shortlist_pairs=len(shortlist),patterns=len(patterns)))
    dump('API_handoff.json',handoff)
    dump('APIhandoff.json',handoff)
    dump('manifest.json',dict(version=VERSION,input_sources=manifest,inputs_are_exact_pins=True,
                              outputs={f.name:digest(f) for f in sorted(HERE.glob('*')) if f.is_file() and f.name not in ('manifest.json','validation.json','protected_snapshot.json')},
                              counts=handoff['counts'],claims='conditional contribution screen, not validated RW profit or global optimum'))
    print(json.dumps(handoff['counts']))


if __name__=='__main__':
    build()
