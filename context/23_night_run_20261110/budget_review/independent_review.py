#!/usr/bin/env python3
"""MR07: rebuild finance and LP from immutable Git blobs; never execute author code.

Run from this checkout: python3 context/23_night_run_20261110/budget_review/independent_review.py
No downloads, model imports, live services, or writes outside this directory.
"""
import collections
import csv
import datetime as dt
from decimal import Decimal as D
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import platform
import subprocess

import numpy as np
import scipy
from scipy.optimize import linprog

PIN = '2a74b05179d3619c03fdab3b038fbe7587d85eca'
ROOT = 'context/23_night_run_20261110/methods/'
OUT = Path(__file__).resolve().parent
TS = 'inputs/set001/tsiri_93fa/'
CTX = TS + 'context/'
sources = {}
checks = []


def blob(path, grain='pinned methodology or scenario table'):
    raw = subprocess.check_output(['git', 'show', PIN + ':' + ROOT + path])
    sources.setdefault(path, dict(path=ROOT + path, commit=PIN, sha256=hashlib.sha256(raw).hexdigest(),
                         bytes=len(raw), grain=grain, access='git show; no working-tree model inputs'))
    return raw


def obj(path):
    return json.loads(blob(path))


def rows(path, grain='one exported CSV row; source_line includes header'):
    data = list(csv.DictReader(io.StringIO(blob(path, grain).decode('utf-8-sig'))))
    return [dict(r, source_line=i + 2) for i, r in enumerate(data)]


def save(name, value):
    p = OUT / name
    if name.endswith('.csv'):
        with p.open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, list(dict.fromkeys(k for r in value for k in r)))
            w.writeheader()
            w.writerows(value)
    else:
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def close(a, b, label, tol=1e-6):
    delta = float(a) - float(b)
    assert abs(delta) <= tol, (label, a, b, delta)
    checks.append(dict(check=label, delta=delta, tolerance=tol))


def dec(r, k):
    return D(r[k])


def key(r):
    return r['profile'], r['network'], r['scenario']


def distance(a, b, geo):
    x, y = geo[a], geo[b]
    la, lb = map(math.radians, [float(x['latitude_deg']), float(y['latitude_deg'])])
    dl = math.radians(float(y['longitude_deg']) - float(x['longitude_deg']))
    return 12742 * math.asin(min(1, math.sqrt(math.sin((lb-la)/2)**2 +
        math.cos(la)*math.cos(lb)*math.sin(dl/2)**2)))


def main():
    config = obj(CTX + '15_team_update/model/configuration.json')
    source12 = obj(CTX + '12_network_economics/inputs.json')
    definitions = obj(CTX + '17_aircraft_route_review/model/selected_networks.json')
    comparison = rows(CTX + '21_team_proposals/comparison.csv')
    flights = rows(CTX + '17_aircraft_route_review/model/flights.csv', 'dated flight, profile x network; no scenario duplication')
    capacities = rows(CTX + '17_aircraft_route_review/model/capacity.csv', 'physical flight x profile x network x scenario')
    sales = rows(CTX + '17_aircraft_route_review/model/sales.csv', 'enumerated dated one-way product x scenario, including zero sales')
    published = rows(CTX + '17_aircraft_route_review/evidence/directional_blocks.csv')
    geo = {r['iata']: r for r in rows('inputs/set001/nastya_2f03/data/processed/catchments.csv',
              'airport coordinates; independent geometric diagnostic only, not author stage11 coordinates')}
    author_bounds = rows('runs/budget_v1/supply_upper_bounds.csv')
    author_dual = rows('runs/budget_v1/supply_dual_certificates.csv')
    author_thresholds = rows('runs/budget_v1/fixed_sales_thresholds.csv')
    author_registry = rows('runs/budget_v1/strategy_budget_parameters.csv')
    author_pairs = rows('runs/budget_v1/pairwise_budget_boundaries.csv')
    bounds, shadow_rows, inequality_rows, universe, local_primal = [], [], [], [], []
    lp_rows, ledgers, thresholds, programs = [], [], [], []
    expected_mapping = {
        'D_SVX8': ('UNKNOWN_TIME_PLUS60_100', 'D_case'),
        'D_previous_best8': ('ROUTE_INPUTS_UPPER_100', 'D_case'),
        'H_UFA_4': ('ROUTE_INPUTS_UPPER_100', 'H_UFA_4'),
        'H_UFA_8': ('ROUTE_INPUTS_UPPER_100', 'H_UFA_8'),
    }
    for summary in comparison:
        name, sc = summary['network'], summary['scenario']
        profile, network = expected_mapping[name]
        assert (summary['source_profile'], summary['source_network']) == (profile, network)
        f = [r for r in flights if (r['profile'], r['network']) == (profile, network)]
        c = [r for r in capacities if key(r) == (profile, network, sc)]
        s = [r for r in sales if key(r) == (profile, network, sc)]
        fm = {r['id']: r for r in f}
        cm = {r['flight_id']: r for r in c}
        assert len(fm) == len(f) == len(cm) == len(c) and set(fm) == set(cm)
        p = config['scenarios'][sc]
        pax = D(str(p['pax_cost']))
        local = {r['flight_ids']: r for r in s if r['transfer'] == 'False'}
        assert len(local) == sum(r['transfer'] == 'False' for r in s) and set(local) == set(fm)
        ids = sorted(fm)
        for leg in ids:
            fr, cr = fm[leg], cm[leg]
            dep, arr = int(fr['departure_utc_minute']), int(fr['arrival_utc_minute'])
            assert fr['date'] == (dt.date(2026, 12, 7) + dt.timedelta(days=dep//1440)).isoformat()
            assert 0 <= dep < arr <= 7*1440 and int(fr['day']) == dep//1440 + 1
            assert arr-dep == int(fr['block_minutes'])
            for field in ['origin', 'destination', 'block_minutes']:
                assert fr[field] == cr[field]
            assert dec(cr, 'capacity_scenario') == dec(fr, 'capacity') == D(config['config']['seats']) == 100
            assert dec(fr, sc + '_capacity_scenario') == 100
            hours = dec(fr, 'block_minutes') / 60
            flight_cost = (
                (D(str(p['fuel_t_per_hour']))*hours + D(str(p['fuel_t_per_cycle']))) *
                (D(str(p['fuel_rub_per_t'])) + D(str(p['fuel_uplift_rub_per_t']))) +
                hours*sum(D(str(p[k])) for k in ['mro_rub_per_hour', 'crew_rub_per_hour', 'navigation_rub_per_hour']) +
                D(str(source12['ufa_reference_basket_rub']))*D(str(p['airport_factor'])) +
                D(str(p['deicing_probability']))*D(str(p['deicing_operation_rub'])))
            close(flight_cost, cr['flight_variable_cost'], name+'/'+sc+'/'+leg+'/rebuild_cost')
            if name == 'D_SVX8':
                pr = next(x for x in published if (x['origin'], x['destination']) == (fr['origin'], fr['destination']))
                close(fr['block_minutes'], pr['max_published_minutes'], leg+'/published_block_no_plus60')
        # Check weekly rotations and allocated tails directly from dated flight rows.
        tails = sorted({r['aircraft'] for r in f})
        for tail in tails:
            ff = sorted([r for r in f if r['aircraft'] == tail], key=lambda r: int(r['departure_utc_minute']))
            assert ff[0]['origin'] == ff[-1]['destination']
            for a, b in zip(ff, ff[1:]):
                assert a['destination'] == b['origin'] and int(a['arrival_utc_minute'])+45 <= int(b['departure_utc_minute'])
        assert len(tails) == int(summary['active_allocated'])
        assert int(summary['reserve_scenario']) == config['config']['spare_aircraft'] == 1
        definition = definitions[profile+'|'+network]
        hub = definition['hub']
        if hub:
            assert len(definition['leaves']) == (4 if name.endswith('_4') else 8)
        # Exhaustive two-flight graph before geometry filtering, using all dated flights.
        graph = []
        for a, b in itertools.product(f, repeat=2):
            wait = int(b['departure_utc_minute']) - int(a['arrival_utc_minute'])
            if (a['destination'] == b['origin'] and a['origin'] != b['destination'] and
                a['day'] == b['day'] and 60 <= wait <= 240):
                detour = (distance(a['origin'], a['destination'], geo) +
                          distance(b['origin'], b['destination'], geo))/distance(a['origin'], b['destination'], geo)
                graph.append((a, b, wait, detour))
        product_ids = [tuple(r['flight_ids'].split(';')) for r in s]
        assert len(product_ids) == len(set(product_ids))
        reconstructed = {(leg,) for leg in ids}
        eligible = [(a, b) for a, b, wait, detour in graph if hub and a['destination'] == hub and detour <= 1.6]
        eligible_od = {(a['origin'], b['destination']) for a, b in eligible}
        for a, b in eligible:
            if (b['destination'], a['origin']) in eligible_od:
                reconstructed.add((a['id'], b['id']))
        assert reconstructed == set(product_ids), (name, sc, reconstructed.symmetric_difference(product_ids))
        for a, b, wait, detour in graph:
            universe.append(dict(network=name, scenario=sc, origin=a['origin'], via=a['destination'], destination=b['destination'],
                flight_ids=a['id']+';'+b['id'], wait_minutes=wait, independent_detour=detour,
                enumerated=(a['id'],b['id']) in reconstructed,
                geometry_status='Independent pinned catchments coordinates; canonical author stage11 geometry not present in methods freeze'))
        # Rebuild all sales money from quantity, per-journey price, leg count, and migration counts.
        gross = foregone = new_pax = saved_old_pax = sold = D(0)
        used = collections.defaultdict(lambda: D(0))
        lambdas = {leg: dec(local[leg], 'fare_once')-pax for leg in ids}
        assert min(lambdas.values()) >= 0
        for leg in ids:
            shadow_rows.append(dict(network=name, scenario=sc, flight_id=leg, source_flight_line=fm[leg]['source_line'],
                source_capacity_line=cm[leg]['source_line'], source_local_sales_line=local[leg]['source_line'],
                capacity=str(dec(cm[leg],'capacity_scenario')), local_fare=local[leg]['fare_once'],
                pax_per_segment=str(pax), lambda_rub_per_seat=str(lambdas[leg])))
            local_primal.append(dict(network=name, scenario=sc, flight_id=leg, local_sold=100, transfer_sold=0,
                seats_used=100, capacity=100, remaining=0, product_exists=True))
        for r in s:
            legs = r['flight_ids'].split(';')
            qty, fare = dec(r,'sold_journeys'), dec(r,'fare_once')
            assert len(legs) == (2 if r['transfer'] == 'True' else 1) and len(legs) == len(set(legs))
            assert r['origin'] == fm[legs[0]]['origin'] and r['destination'] == fm[legs[-1]]['destination']
            assert all(int(fm[x]['day']) == int(r['day']) for x in legs)
            assert qty >= 0
            factor = D(str(p['transfer_fare_factor'])) if len(legs) == 2 else D(1)
            old_fare = fare/factor*D(str(p['old_RW_fare_ratio']))
            m_direct, m_connect = dec(r,'migrated_RW_direct'), dec(r,'migrated_RW_unverified_connecting')
            migrated = m_direct + m_connect
            assert 0 <= migrated <= qty and old_fare >= 2*pax
            rev, loss = qty*fare, migrated*old_fare
            pax_new, pax_saved = qty*len(legs)*pax, (m_direct+2*m_connect)*pax
            assert loss >= pax_saved
            for field, value in [('gross_revenue',rev),('foregone_RW_revenue',loss),('incremental_revenue',rev-loss),
                                 ('new_pax_variable',pax_new),('saved_old_pax_variable',pax_saved),('segment_pax',qty*len(legs)),
                                 ('migrated_RW_total',migrated)]:
                close(value,r[field],name+'/'+sc+'/sales_line'+str(r['source_line'])+'/'+field)
            gross += rev; foregone += loss; new_pax += pax_new; saved_old_pax += pax_saved; sold += qty
            for leg in legs:
                used[leg] += qty
            margin = fare - len(legs)*pax
            slack = sum(lambdas[x] for x in legs)-margin
            assert slack >= 0
            author = next(x for x in author_dual if (x['network'],x['scenario'],x['flight_ids']) == (name,sc,r['flight_ids']))
            for field,value in [('dual_slack',slack),('itinerary_unit_margin',margin),
                                ('sum_leg_shadow_value',sum(lambdas[x] for x in legs))]:
                close(value,author[field],name+'/'+sc+'/dual_line'+str(author['source_line'])+'/'+field)
            inequality_rows.append(dict(network=name,scenario=sc,source_sales_line=r['source_line'],
                author_certificate_line=author['source_line'],flight_ids=r['flight_ids'],sold_journeys=str(qty),
                fare=str(fare),leg_count=len(legs),unit_margin=str(margin),dual_lhs=str(sum(lambdas[x] for x in legs)),
                slack=str(slack),covered=True))
        for leg in ids:
            assert used[leg] <= dec(cm[leg],'capacity_scenario')
            close(used[leg],cm[leg]['occupied'],leg+'/'+sc+'/physical_seat_reconciliation')
        cost = sum(dec(r,'flight_variable_cost') for r in c)
        operating = cost + new_pax - saved_old_pax
        inc_rev = gross - foregone
        contribution = inc_rev - operating
        for field, value in [('gross_revenue',gross),('foregone_RW_revenue',foregone),('incremental_revenue',inc_rev),
                             ('new_pax_variable',new_pax),('saved_old_pax_variable',saved_old_pax),
                             ('flight_variable_cost',cost),('incremental_operating_cost',operating),
                             ('contribution_before_base_fleet_opportunity',contribution),('sold_journeys',sold)]:
            close(value,summary[field],name+'/'+sc+'/summary/'+field)
        seats = sum(dec(r,'capacity_scenario') for r in c)
        full_rev = sum(dec(cm[x],'capacity_scenario')*dec(local[x],'fare_once') for x in ids)
        full_pax = seats*pax
        primal_value = full_rev-full_pax-cost
        dual_value = sum(dec(cm[x],'capacity_scenario')*lambdas[x] for x in ids)-cost
        assert primal_value == dual_value
        declared = next(x for x in author_bounds if (x['network'],x['scenario']) == (name,sc))
        for field,value in [('nominal_segment_seats',seats),('full_local_revenue',full_rev),('full_local_pax_cost',full_pax),
                            ('flight_variable_cost',cost),('current_contribution',contribution),('optimistic_contribution_upper',primal_value)]:
            close(value,declared[field],name+'/'+sc+'/author_bound/'+field)
        # Solve primal AND dual separately. No author's objective, matrix or reported optimum reused.
        A = np.array([[r['flight_ids'].split(';').count(leg) for r in s] for leg in ids], dtype=float)
        v = np.array([float(dec(r,'fare_once')-len(r['flight_ids'].split(';'))*pax) for r in s])
        cap = np.array([float(dec(cm[x],'capacity_scenario')) for x in ids])
        primal = linprog(-v,A_ub=A,b_ub=cap,bounds=(0,None),method='highs')
        dual = linprog(cap,A_ub=-A.T,b_ub=-v,bounds=(0,None),method='highs')
        assert primal.success and dual.success
        assert min(primal.x) >= -1e-8 and max(A@primal.x-cap) <= 1e-8
        assert min(dual.x) >= -1e-8 and min(A.T@dual.x-v) >= -1e-8
        close(-primal.fun-float(cost),primal_value,name+'/'+sc+'/independent_HiGHS_primal')
        close(dual.fun-float(cost),dual_value,name+'/'+sc+'/independent_HiGHS_dual')
        close(max(abs(dual.x-np.array([float(lambdas[x]) for x in ids]))),0,name+'/'+sc+'/solver_dual_vs_reconstructed_lambda')
        lp_rows.append(dict(network=name,scenario=sc,primal_status=int(primal.status),dual_status=int(dual.status),
            variables=len(s),capacity_constraints=len(ids),primal_objective_before_flight_cost=-primal.fun,
            dual_objective_before_flight_cost=dual.fun,contribution=-primal.fun-float(cost),
            max_capacity_excess=float(max(A@primal.x-cap)),max_solver_lambda_difference=float(max(abs(dual.x-np.array([float(lambdas[x]) for x in ids]))))))
        rec = dict(network=name,scenario=sc,flight_count=len(f),dated_start=min(x['date'] for x in f),dated_end=max(x['date'] for x in f),
            local_products=len(local),transfer_products=sum(r['transfer']=='True' for r in s),zero_sale_products=sum(dec(r,'sold_journeys')==0 for r in s),
            segment_seats=str(seats),full_local_revenue=str(full_rev),full_local_pax_cost=str(full_pax),flight_cost=str(cost),
            current_contribution=str(contribution),analytic_primal=str(primal_value),analytic_dual=str(dual_value),
            full_local_fare_multiplier=str((cost+full_pax)/full_rev),uniform_occupancy=str(cost/(full_rev-full_pax)),
            min_lambda=str(min(lambdas.values())),min_transfer_slack=str(min((D(x['slack']) for x in inequality_rows if x['network']==name and x['scenario']==sc and x['leg_count']==2),default=D(0))))
        bounds.append(rec)
        ledgers.append(dict(network=name,scenario=sc,new_revenue=str(gross),old_revenue_foregone=str(foregone),
            new_pax_cost=str(new_pax),old_pax_cost_saved=str(saved_old_pax),flight_cost=str(cost),contribution=str(contribution),
            minimum_old_margin_per_journey=str(min(dec(r,'fare_once')/(D(str(p['transfer_fare_factor'])) if r['transfer']=='True' else 1)*D(str(p['old_RW_fare_ratio']))-2*pax for r in s))))
        registry = next(x for x in author_registry if (x['network'],x['scenario']) == (name,sc))
        assert len(tails) == int(registry['additional_working_tail_allocation'])
        assert int(registry['reserve_allocation']) == 1
        assert int(registry['new_base_indicator']) == int(hub=='UFA')
        assert all(registry[k] == '' for k in ['allocated_tail_week_cost','new_base_week_cost','other_incremental_fixed'])
        programs.append(dict(network=name,scenario=sc,tails=tails,working=len(tails),reserve=1,new_base=int(hub=='UFA'),
            contribution=str(contribution),flights=len(f),endpoint_pairs=len({tuple(sorted((x['origin'],x['destination']))) for x in f}),
            selected_definition_key=profile+'|'+network,source_summary_line=summary['source_line']))
        for burden in [D(0),D(500000),D(1000000)]:
            common = (operating+burden)/inc_rev
            new_only = (operating+foregone+burden)/gross
            full_fare = (cost+full_pax+burden)/full_rev
            occupancy = (cost+burden)/(full_rev-full_pax)
            reduction = (operating+burden-inc_rev)/cost
            # At the full-local price root, check dual feasibility again. For roots
            # below1 this is necessary: negative local margins could break the formula.
            repriced_lambda = {leg:full_fare*dec(local[leg],'fare_once')-pax for leg in ids}
            assert min(repriced_lambda.values()) >= 0
            for offer in s:
                offer_legs = offer['flight_ids'].split(';')
                assert (sum(repriced_lambda[leg] for leg in offer_legs) -
                        (full_fare*dec(offer,'fare_once')-len(offer_legs)*pax)) >= D('-1e-18')
            assert abs(full_fare*full_rev-full_pax-cost-burden) < D('1e-18')
            assert abs(occupancy*(full_rev-full_pax)-cost-burden) < D('1e-18')
            assert abs(common*inc_rev-operating-burden) < D('1e-18')
            assert abs(new_only*gross-foregone-operating-burden) < D('1e-18')
            row = next(x for x in author_thresholds if (x['network'],x['scenario'],D(x['extra_burden_rub'])) == (name,sc,burden))
            for field,value in [('common_new_old_fare_multiplier',common),('new_only_fare_multiplier_old_yield_fixed',new_only),
                                ('full_local_fare_multiplier_optimistic',full_fare),('uniform_local_occupancy_threshold_no_migration',occupancy),
                                ('fraction_of_flight_cost_reduction_needed_at_current_sales',reduction),('fixed_sales_extra_cost_headroom',contribution)]:
                close(value,row[field],name+'/'+sc+'/threshold_line'+str(row['source_line'])+'/'+field)
            thresholds.append(dict(network=name,scenario=sc,extra=str(burden),new_and_old_fares=str(common),new_only_old_fare_fixed=str(new_only),
                full_local_fare=str(full_fare),uniform_local_occupancy=str(occupancy),flight_cost_reduction_at_fixed_sales=str(reduction),
                min_lambda_at_full_local_fare_root=str(min(repriced_lambda.values())),
                uniform_local_solution_within_capacity=occupancy<=1,
                base_headroom_before_selected_burden=str(contribution),residual_headroom_after_selected_burden=str(contribution-burden),source_output_line=row['source_line']))
    assert len(inequality_rows) == len(author_dual) == 224
    assert len(bounds) == 8 and sum(x['local_products'] for x in bounds) == 160 and sum(x['transfer_products'] for x in bounds) == 64
    pairs = []
    for sc in ['base','cautious']:
        for a,b in itertools.combinations([r for r in programs if r['scenario']==sc],2):
            delta = D(a['contribution'])-D(b['contribution'])
            dn = a['working']+a['reserve']-b['working']-b['reserve']
            db = a['new_base']-b['new_base']
            row = next(x for x in author_pairs if (x['scenario'],x['candidate_a'],x['candidate_b']) == (sc,a['network'],b['network']))
            close(delta,row['delta_contribution_a_minus_b'],sc+'/pair/'+a['network']+'/'+b['network'])
            assert dn == int(row['delta_allocated_tails']) and db == int(row['delta_new_base_indicator'])
            for column,den in [('F_tie_when_B_and_other_differences_zero',dn),('B_tie_when_F_and_other_differences_zero',db)]:
                if den:
                    close(delta/den,row[column],sc+'/'+a['network']+'/'+b['network']+'/'+column)
                else:
                    assert row[column] == ''
            pairs.append(dict(scenario=sc,a=a['network'],b=b['network'],delta_contribution=str(delta),delta_tails=dn,delta_base=db,
                F_tie=str(delta/dn) if dn else None,B_tie=str(delta/db) if db else None,
                formula='Pi_A-Pi_B=deltaC-deltaTails*F-deltaBase*B-(O_A-O_B)'))
    save('independent_bounds.csv',bounds)
    save('independent_shadow_prices.csv',shadow_rows)
    save('independent_inequalities.csv',inequality_rows)
    save('independent_local_solution.csv',local_primal)
    save('independent_temporal_universe.csv',universe)
    save('independent_lp.json',dict(scipy=scipy.__version__,numpy=np.__version__,python=platform.python_version(),
        method='two independent HiGHS calls per case: primal max margin, dual min seat cost; no author imports',results=lp_rows))
    save('independent_sales_ledger.csv',ledgers)
    save('independent_thresholds.csv',thresholds)
    save('independent_programs.json',programs)
    save('independent_pairwise.csv',pairs)
    singleton_checks(capacities, sales, config)
    accounting_and_counterexamples(bounds)
    # Inspect and verify source/output manifests from the same pin, never a moving branch.
    manifests = []
    for name, field in [('source_manifest.json','files'),('output_manifest.json','files')]:
        manifest = obj(name)
        for entry in manifest[field]:
            raw = subprocess.check_output(['git','show',PIN+':'+ROOT+entry['path']])
            digest = hashlib.sha256(raw).hexdigest()
            assert digest == entry['sha256'] and len(raw) == entry['bytes'], (name,entry['path'])
            manifests.append(dict(manifest=name,path=entry['path'],expected_sha256=entry['sha256'],observed_sha256=digest,bytes=len(raw),status='MATCH'))
    for name in ['budget_readout.md','budget_contract.json','budget_thresholds.py','verify_budget_lp.py','checks/budget_v1_lp.json',
                 TS+'scripts/build_team_proposals.py',TS+'scripts/build_team_comparison.py',TS+'scripts/build_conditional_decision.py',
                 TS+'scripts/build_aircraft_route_review.py',TS+'scripts/audit_route_economics.py']:
        blob(name,'read-only source or author claim; not executed')
    save('manifest_verification.json',dict(results=manifests,note='Hash verification only; not review of unrelated modules'))
    save('source_manifest.json',dict(review_id='MR07',pin=PIN,read_method='git show',sources=list(sources.values()),
        external_sources=False,author_code_executed=False,author_tests_used_as_acceptance=False))
    save('checks.json',dict(status='PASS_SCOPED',checks=len(checks),max_abs_numeric_delta=max(abs(x['delta']) for x in checks),
        network_scenarios=len(bounds),dual_inequalities=len(inequality_rows),threshold_rows=len(thresholds),pairwise_rows=len(pairs),
        all_cautious_bounds_negative=all(D(x['analytic_primal'])<0 for x in bounds if x['scenario']=='cautious'),
        numeric_checks=checks))
    print(json.dumps(dict(status='PASS_SCOPED',network_scenarios=len(bounds),inequalities=len(inequality_rows),
        thresholds=len(thresholds),pairwise=len(pairs),numeric_checks=len(checks),max_abs_delta=max(abs(x['delta']) for x in checks))))


def singleton_checks(capacities, sales, config):
    """Readout's two SVX outback examples; primary costs and migration, not past author's tests."""
    expected = rows(CTX+'18_unit_economics_audit/breakeven.csv')
    obj(CTX+'18_unit_economics_audit/assumptions.json')
    result = []
    for destination, sc in itertools.product(['MRV','AER'], ['base','cautious']):
        route = 'SVX-'+destination
        cs = [r for r in capacities if key(r)==('UNKNOWN_TIME_PLUS60_100','D_case',sc) and
              {r['origin'],r['destination']}=={'SVX',destination}]
        ss = [r for r in sales if key(r)==('UNKNOWN_TIME_PLUS60_100','D_case',sc) and
              {r['origin'],r['destination']}=={'SVX',destination} and r['transfer']=='False']
        assert len(cs)==len(ss)==2
        p = config['scenarios'][sc]
        pax = D(str(p['pax_cost']))
        margins = {}
        for r in ss:
            q = dec(r,'sold_journeys')
            migration = dec(r,'migrated_RW_total')/q
            old_segments = (dec(r,'migrated_RW_direct')+2*dec(r,'migrated_RW_unverified_connecting'))/q
            margins[r['origin']] = dec(r,'fare_once')*(1-migration*D(str(p['old_RW_fare_ratio'])))-pax+old_segments*pax
        cost = sum(dec(r,'flight_variable_cost') for r in cs)
        for extra in [D(0),D(500000),D(1000000)]:
            threshold = (cost+extra)/sum(margins.values())
            at100 = 100*sum(margins.values())-cost-extra
            row = next(r for r in expected if (r['route'],r['scenario'],D(r['weekly_extra_burden']))==(route,sc,extra))
            close(threshold,row['linear_paid_threshold_NOT_capacity_forecast'],route+'/'+sc+'/symmetric_threshold')
            close(at100,row['contribution_at100_and_current_fare'],route+'/'+sc+'/full100_contribution')
            directionals = {}
            for c in cs:
                v = (dec(c,'flight_variable_cost')+extra/2)/margins[c['origin']]
                directionals[c['origin']] = str(v)
                close(v,row['required_outbound' if c['origin']=='SVX' else 'required_inbound'],route+'/'+sc+'/direction_threshold')
            result.append(dict(route=route,scenario=sc,extra=str(extra),unit_margins={k:str(v) for k,v in margins.items()},
                flight_cost=str(cost),symmetric_paid_each_direction=str(threshold),ceil_each_direction=math.ceil(threshold),
                contribution_at100_each=str(at100),directional_break_even=directionals,
                interpretation='Symmetric total-roundtrip threshold; does not mean every direction separately breaks even. Nominal100 remains not dispatch approval'))
    save('independent_singletons.json',result)


def accounting_and_counterexamples(bounds):
    donor = rows('runs/budget_v1/donor_fixture_states.csv')
    cash = rows('runs/budget_v1/cash_fixture.csv')
    # Full, independently written states. Existing operating costs remain in every state.
    simple = {'KEEP':1000000-600000-100000-200000,
              'CANCEL_WITHOUT_REPLACEMENT':-200000-50000,
              'REPLACE':1200000-700000-100000-200000-50000}
    for r in donor:
        close(simple[r['state']],r['full_state_result'],'donor/'+r['state'])
        close(simple[r['state']]-simple['KEEP'],r['delta_vs_keep'],'donor_delta/'+r['state'])
    # Additional migration fixture: retained old network is DISTINCT from removed donor.
    # Foregone old margin 300000-30000 is represented once in the old network's state.
    full_states = {'KEEP':(2000000-1000000-200000)+(1000000-600000-100000)-200000,
                   'CANCEL':(2000000-1000000-200000)-200000-50000,
                   'REPLACE':(1700000-1000000-170000)+(1200000-700000-100000)-200000-50000}
    delta = full_states['REPLACE']-full_states['KEEP']
    assert delta == 400000-(300000-30000)-300000-50000 == -220000
    # If the donor itself is the old displaced product, CANCEL already removes it;
    # there is no remaining old product whose migration margin should be deducted again.
    same_donor_delta = simple['REPLACE']-simple['KEEP']
    assert same_donor_delta == 400000-300000-50000 == 50000
    balance, accrual, peak = 0,0,0
    derived_cash = []
    for r in cash:
        receipts, payments, launch, deposit, returned = [int(r[k]) for k in ['operating_receipts','operating_payments','launch_payments','deposit_payment','deposit_return']]
        change = receipts-payments-launch-deposit+returned
        balance += change; accrual += receipts-payments-launch; peak = max(peak,-balance)
        close(change,r['net_cash'],'cash/'+r['period']+'/net')
        close(balance,r['cumulative_cash_before_financing'],'cash/'+r['period']+'/balance')
        derived_cash.append(dict(period=r['period'],net_cash=change,balance_before_financing=balance))
    assert balance == accrual == 400000 and peak == 1000000
    fine_cash = 0; fine_peak = 0
    # Same period totals, but payment precedes receipt: funding rises without a P&L change.
    for e in [-400000,-600000,-800000,1200000,-800000,1200000,600000]:
        fine_cash += e; fine_peak=max(fine_peak,-fine_cash)
    assert fine_cash == 400000 and fine_peak == 1800000
    save('independent_accounting.json',dict(author_synthetic_full_states=simple,
        additional_migration_fixture=dict(full_states=full_states,replace_minus_keep=delta,
            decomposition='new contribution 400000 - retained-old margin lost 270000 - donor contribution 300000 - exit 50000',
            actual_RW_donor='UNKNOWN'),same_product_donor_delta=same_donor_delta,
        cash=dict(period_states=derived_cash,accrual_policy='All launch cost expensed at t0; operating receipts/payments assumed equal period revenues/expenses; refundable deposit is an asset, no depreciation/amortisation, taxes, interest or credit sales in this fixture',
            final_cash=balance,total_profit=accrual,period_boundary_peak=peak,
            intraperiod_payment_first_peak=fine_peak,actual_company_peak=None)))
    b = next(x for x in bounds if (x['network'],x['scenario'])==('H_UFA_4','cautious'))
    upper, rev, pc, fc = [D(b[k]) for k in ['analytic_primal','full_local_revenue','full_local_pax_cost','flight_cost']]
    offers = [r for r in rows(CTX+'17_aircraft_route_review/model/sales.csv') if
              key(r)==('ROUTE_INPUTS_UPPER_100','H_UFA_4','cautious')]
    transfer = next(r for r in offers if r['transfer']=='True')
    flight_ids = transfer['flight_ids'].split(';')
    local_fares = {r['flight_ids']:dec(r,'fare_once') for r in offers if r['transfer']=='False'}
    transfer_witness = dict(origin=transfer['origin'],via='UFA',destination=transfer['destination'],
        flight_ids=flight_ids,original_transfer_fare=transfer['fare_once'],sum_local_fares=str(sum(local_fares[x] for x in flight_ids)),
        new_through_fare=str(sum(local_fares[x] for x in flight_ids)+60000),through_sold=100,
        local_sold_on_these_legs=0,local_sold_on_each_other_leg=100,capacity_each_leg=100)
    examples = [
        dict(id='EXPENSIVE_NEW_TRANSFER',change='Add a new two-leg product at sum of those local fares +60000 RUB; sell100 and remove100 locals on each used leg',
             delta=100*60000,new_result=str(upper+6000000),witness=transfer_witness,
             boundary_broken='product universe / through yield; same physical seats; original author arithmetic remains valid'),
        dict(id='ANCILLARY',change='Add4000 RUB net ancillary margin to each of1600 local journeys',
             delta=1600*4000,new_result=str(upper+6400000),boundary_broken='No other revenue/margin'),
        dict(id='NEGATIVE_OLD_MARGIN',change='Hypothetical1600 old migrants, each with old revenue100 and avoidable old passenger cost5100; no donor flight saving',
             delta=1600*5000,new_result=str(upper+8000000),boundary_broken='Old lost contribution nonnegative; incompatible with pinned positive old margins'),
        dict(id='LOWER_FLIGHT_COST',change='Reduce retained weekly flight cost by40 percent',delta=str(fc*D('.4')),
             new_result=str(upper+fc*D('.4')),boundary_broken='Fixed flight cost'),
        dict(id='LARGER_CAPACITY',change='Scale nominal sellable seats100 to200 on every dated leg, keep per-passenger fare/cost and flight cost',
             delta=str(rev-pc),new_result=str(upper+rev-pc),boundary_broken='Fixed100-seat capacity; mathematical only, no SSJ payload or dispatch assertion'),
    ]
    assert all(D(e['new_result'])>0 for e in examples)
    save('counterexamples.json',dict(anchor='H_UFA_4/cautious',original_upper=str(upper),examples=examples,
        negative_margin_with_pinned_passenger_cost=dict(old_fare=100,old_legs=2,pax_per_segment=650,
            migrated_journeys=1600,old_margin_per_journey=-1200,improvement=1920000,new_result=str(upper+1920000),
            interpretation='Invalidates the claimed numerical upper bound outside its old-margin assumption; does not itself reverse the cautious sign with these smaller savings'),
        unchanged_valid_case='Increasing actual payload only up to the already assumed100 seats cannot defeat the negative nominal100 upper bound',
        status='Boundary demonstrations; no real demand/cost/aircraft evidence; no author arithmetic defect'))


if __name__ == '__main__':
    main()
