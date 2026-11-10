#!/usr/bin/env python3
"""Controlled demand-recipe substitution on exact context21 supply; stdlib."""
import collections
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'inputs/set001/tsiri_93fa/context'
OUT = ROOT / 'runs/common_demand_v1'
MONEY = ['gross_revenue', 'foregone_RW_revenue', 'new_pax_variable', 'saved_old_pax_variable']


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    if name.endswith('.json'):
        (OUT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    else:
        with (OUT/name).open('w', newline='') as f:
            w=csv.DictWriter(f, list(dict.fromkeys(k for r in data for k in r)))
            w.writeheader();w.writerows(data)


def near(x, y, label, tolerance=1e-6):
    assert abs(float(x)-float(y)) <= tolerance, (label, x, y)


def pair(a,b):
    return tuple(sorted((a,b)))


def flight_cost(minutes, p):
    h=minutes/60
    basket=49.45*(553+499)+19300+8100+16668
    return ((p['fuel_t_per_hour']*h+p['fuel_t_per_cycle'])*(p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t'])
            +h*(p['mro_rub_per_hour']+p['crew_rub_per_hour']+p['navigation_rub_per_hour'])
            +basket*p['airport_factor']+p['deicing_probability']*p['deicing_operation_rub'])


def prepare(ss, cc, scenario, params):
    counts=collections.Counter((s['origin'],s['destination']) for s in ss)
    known_pairs={pair(s['origin'],s['destination']) for s in ss
                 if s['known_direct_RW_capacity'] and float(s['known_direct_RW_capacity'])>0}
    offers=[]
    for s in ss:
        trans=s['transfer']=='True'
        legs=s['flight_ids'].split(';');freq=counts[s['origin'],s['destination']]
        peak=.45 if scenario=='base' else .30
        q=peak*(1-math.exp(-freq/3))*(.65 if trans else 1)
        can=(.6 if scenario=='base' else .8) if pair(s['origin'],s['destination']) in known_pairs else (.05 if scenario=='base' else .1)
        fare=float(s['fare_once'])
        oldfare=fare/(params['transfer_fare_factor'] if trans else 1)*params['old_RW_fare_ratio']
        offers.append(dict(source=s, origin=s['origin'], destination=s['destination'],
                           day=int(s['day']),legs=legs,transfer=trans,D=float(s['D']),
                           coefficient=q/freq,fare=fare,oldfare=oldfare,can=can,
                           known=None if s['known_direct_RW_capacity']=='' else float(s['known_direct_RW_capacity'])))
    offers.sort(key=lambda o:(o['transfer'], -(o['fare']-o['can']*o['oldfare']-len(o['legs'])*params['pax_cost'])/len(o['legs']),
                             o['origin'],o['destination'],o['day'],tuple(o['legs'])))
    return offers


def simulate(offers, cc, params, demand=None, multiplier=1, enforce_market_cap=False):
    caps={c['flight_id']:float(c['capacity_scenario']) for c in cc}
    initial=caps.copy();migration={};out=[];totals=collections.Counter()
    for o in offers:
        migration[o['origin'],o['destination']]=o['known'] or 0
    market_sold=collections.Counter();market_D={}
    for o in offers:
        k=(o['origin'],o['destination'])
        D=(o['D'] if demand is None else demand[pair(*k)])*multiplier
        if k in market_D:near(D,market_D[k],'shared market D identity')
        options=[D*o['coefficient']]+[caps[i] for i in o['legs']]
        if enforce_market_cap:options.append(max(0,D-market_sold[k]))
        sold=min(options)
        for leg in o['legs']:caps[leg]-=sold
        direct=min(sold*o['can'],migration[k]);migration[k]-=direct
        unknown=sold*o['can']-direct # all selected source markets have old_rw_segments=2
        migrated=direct+unknown
        values=dict(sold_journeys=sold,transfer_journeys=sold if o['transfer'] else 0,
                    segment_pax=sold*len(o['legs']),migrated_RW_total=migrated,
                    migrated_RW_direct=direct,migrated_RW_unverified_connecting=unknown,
                    gross_revenue=sold*o['fare'],foregone_RW_revenue=migrated*o['oldfare'],
                    new_pax_variable=sold*len(o['legs'])*params['pax_cost'],
                    saved_old_pax_variable=(direct+2*unknown)*params['pax_cost'])
        totals.update(values);market_sold[k]+=sold;market_D[k]=D
        out.append(dict(origin=k[0],destination=k[1],day=o['day'],flight_ids=';'.join(o['legs']),
                        transfer=o['transfer'],D=D,desired=D*o['coefficient'],fare_once=o['fare'],**values))
    cost=sum(float(c['flight_variable_cost']) for c in cc)
    totals['flight_variable_cost']=cost
    totals['incremental_revenue']=totals['gross_revenue']-totals['foregone_RW_revenue']
    totals['contribution_before_base_fleet_opportunity']=totals['incremental_revenue']-cost-totals['new_pax_variable']+totals['saved_old_pax_variable']
    totals['load_factor']=totals['segment_pax']/sum(initial.values())
    totals['net_new_RW_journeys_scenario']=totals['sold_journeys']-totals['migrated_RW_total']
    assert all(-1e-8<=caps[i]<=initial[i]+1e-8 for i in caps)
    assert all(market_sold[k]<=market_D[k]+1e-8 for k in market_sold)
    near(sum(initial.values())-sum(caps.values()),totals['segment_pax'],'seat conservation')
    return dict(totals),out,caps


def main():
    contract=json.loads((ROOT/'common_demand_contract.json').read_text())
    results=rows(SRC/'21_team_proposals/comparison.csv')
    sales=rows(SRC/'17_aircraft_route_review/model/sales.csv')
    capacities=rows(SRC/'17_aircraft_route_review/model/capacity.csv')
    flights=rows(SRC/'17_aircraft_route_review/model/flights.csv')
    config=json.loads((SRC/'15_team_update/model/configuration.json').read_text())['scenarios']
    nd={pair(r['a'],r['b']):r for r in rows(ROOT/'inputs/set001/nastya_2f03/data/processed/demand_pairs.csv')}
    summaries=[];exported=[];demand_rows=[];checks=[];exclusions=[];cost_checks=[]
    for r in results:
        sc=r['scenario'];p=config[sc];key=(r['source_profile'],r['source_network'])
        ss=[s for s in sales if (s['profile'],s['network'],s['scenario'])==(*key,sc)]
        cc=[c for c in capacities if (c['profile'],c['network'],c['scenario'])==(*key,sc)]
        ff=[f for f in flights if (f['profile'],f['network'])==key]
        capids=[c['flight_id'] for c in cc];flightids=[f['id'] for f in ff]
        assert len(capids)==len(set(capids)) and len(flightids)==len(set(flightids))
        assert set(capids)==set(flightids)=={i for s in ss for i in s['flight_ids'].split(';')}
        fmap={f['id']:f for f in ff}
        for c in cc:
            f=fmap[c['flight_id']]
            assert (c['origin'],c['destination'])==(f['origin'],f['destination'])
            near(c['block_minutes'],f['block_minutes'],'flight/cap time')
            expected=flight_cost(float(f['block_minutes']),p)
            near(expected,c['flight_variable_cost'],'per-flight independent formula')
            cost_checks.append(dict(network=r['network'],scenario=sc,flight_id=c['flight_id'],
                                   exported_cost=float(c['flight_variable_cost']),formula_cost=expected,delta=expected-float(c['flight_variable_cost'])))
        near(sum(float(c['flight_variable_cost']) for c in cc),r['flight_variable_cost'],'full flight cost sum')
        offers=prepare(ss,cc,sc,p)
        total,detail,caps=simulate(offers,cc,p)
        original={s['flight_ids']:s for s in ss}
        assert len(original)==len(ss)
        for s in detail:
            for k in ['sold_journeys','transfer_journeys','segment_pax','migrated_RW_total','migrated_RW_direct','migrated_RW_unverified_connecting']+MONEY:
                near(s[k],original[s['flight_ids']][k],('baseline detail',r['network'],k))
        for k,v in total.items():
            if k in r:near(v,r[k],('baseline summary',r['network'],k))
        for c in cc:near(float(c['capacity_scenario'])-caps[c['flight_id']],c['occupied'],'occupied replay')
        checks.append(dict(network=r['network'],scenario=sc,itineraries=len(ss),flights=len(ff),source_profile=key[0],source_network=key[1],status='PASS'))
        pairs={pair(s['origin'],s['destination']) for s in ss}
        missing=sorted(pairs-nd.keys())
        if missing:
            exclusions.append(dict(network=r['network'],scenario=sc,missing_pairs=';'.join('-'.join(k)for k in missing),reason='HOLD_NO_ZIA_TO_MOW_SUBSTITUTION'))
            continue
        demand={}
        for k in sorted(pairs):
            n=nd[k];field='observed' if sc=='base' and n['observed'] and n['observed_coverage']!='airline_group' else 'pax_'+sc
            annual=float(n[field]);weekly=annual/104;demand[k]=weekly
            old={float(s['D']) for s in ss if pair(s['origin'],s['destination'])==k};assert len(old)==1
            demand_rows.append(dict(network=r['network'],scenario=sc,pair='-'.join(k),C_week_direction=old.pop(),
                                    N_annual_proxy=annual,N_field=field,N_coverage=n['observed_coverage'],N_period=n['observed_period'],
                                    N_week_direction_stress=weekly,N_method=n['method'],
                                    status='SOURCE_RECIPE_SCALE_NOT_OBSERVED_ENDPOINT_OD'))
        for recipe,ds in [('C',None),('N',demand)]:
            for multiplier in contract['probe_multipliers']:
                totals,detail,caps=simulate(offers,cc,p,ds,multiplier)
                meta=dict(mode='COMMON_COMPARISON',network=r['network'],scenario=sc,recipe=recipe,multiplier=multiplier,
                          experiment_id=contract['id'],source_commit='93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
                          source_variant='context21_team_proposals',source_profile=key[0],source_network=key[1],
                          input_set_id='set001+common_demand_contract_v1',period_start='2026-12-07',period_end='2026-12-13',
                          price_basis='CIRI_NET_SCENARIO_FARE',tax_basis='EX_RECOVERABLE_VAT_AS_AUTHOR_SCENARIO',
                          active_ceiling=4,active_allocated=r['active_allocated'],reserve_assumption=1,
                          acceptance='OWNER_REPLAY_AND_CONSERVATION_PASS_INDEPENDENT_PENDING',decision_status='AGENT_PROPOSAL')
                summaries.append(dict(**meta,**totals))
                if multiplier==1:exported.extend(dict(**meta,**x) for x in detail)
    save('summary.csv',summaries);save('itinerary_at_unit_scale.csv',exported)
    save('demand_mapping.csv',demand_rows);save('excluded_candidates.csv',exclusions)
    save('baseline_checks.csv',checks);save('flight_cost_checks.csv',cost_checks)
    save('validation.json',dict(status='PASS_OWNER_CHECKS',baseline_cases=len(checks),baseline_itineraries=sum(c['itineraries']for c in checks),
                                per_flight_cost_checks=len(cost_checks),controlled_cases=len(summaries),
                                acceptance_scope='FIXED_CONTEXT21_SUPPLY_INPUT_RECIPE_EXPERIMENT',independent_review='PENDING',
                                full_author_strategy_comparison=False,observed_OD=False,full_budget=False))
    print(json.dumps(dict(baseline_cases=len(checks),controlled_cases=len(summaries))))


if __name__=='__main__':main()
