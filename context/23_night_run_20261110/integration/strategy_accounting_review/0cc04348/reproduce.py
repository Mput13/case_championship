#!/usr/bin/env python3
"""MR09 independent stdlib oracle. Reads pinned objects only via git show.

No author module is imported or patched. Author output tables are comparison
targets, read after calculations from frozen primitive inputs. A few pure
author functions are later executed as the subject of synthetic tests only.
"""
import ast
import collections
import csv
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import subprocess
from datetime import datetime

PIN = 'c24bbd36356f46763eed5a1654573b6de31adc6b'
PREFIX = 'context/23_night_run_20261110/methods/'
HERE = Path(__file__).resolve().parent
REPO = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=HERE, text=True).strip())
TS = 'inputs/set001/tsiri_93fa/context/'
HY = 'inputs/set001/hypotheses_6ed8/context/16_agent_research/hypotheses/experiment_v1/'
inputs = {}
checks = []


def read(name, grain='pinned source file', role='input'):
    raw = subprocess.check_output(['git', 'show', PIN + ':' + PREFIX + name], cwd=REPO)
    inputs[name] = dict(path=PREFIX + name, commit=PIN, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), grain=grain, role=role)
    return raw.decode('utf-8-sig')


def rows(name, grain='table row', role='input'):
    return list(csv.DictReader(io.StringIO(read(name, grain, role))))


def obj(name, role='input'):
    return json.loads(read(name, 'JSON document', role))


def save(name, data):
    if name.endswith('.json'):
        (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        return
    fields = list(dict.fromkeys(k for r in data for k in r))
    with (HERE / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fields, lineterminator='\n')
        w.writeheader()
        w.writerows(data)


def equal(x, y, label, tol=1e-6):
    delta = abs(float(x) - float(y))
    assert delta <= tol, (label, x, y, delta)
    return delta


def check(label, **data):
    checks.append(dict(check=label, status='PASS', **data))


def cost(minutes, p):
    # Direct arithmetic from the source recipe: hourly terms plus one cycle.
    h = minutes / 60
    fuel = (h * p['fuel_t_per_hour'] + p['fuel_t_per_cycle']) * (p['fuel_rub_per_t'] + p['fuel_uplift_rub_per_t'])
    ground = (49.45 * 553 + 49.45 * 499 + 19300 + 8100 + 16668) * p['airport_factor']
    return fuel + h * (p['mro_rub_per_hour'] + p['crew_rub_per_hour'] + p['navigation_rub_per_hour']) + ground + p['deicing_probability'] * p['deicing_operation_rub']


def main():
    # Record the reviewed logic and labels without using it as an executable oracle.
    for name in ['portfolio_comparison.py', 'resource_comparison.py', 'product_accounting_bridge.py',
                 'common_demand.py', 'probe_kover_timebase.py', 'strategy_accounting_readout.md', 'acceptance_events.json']:
        read(name, 'reviewed source/claim', 'review_subject')
    contract = obj('portfolio_contract.json')
    config = obj(TS + '15_team_update/model/configuration.json')
    comp = rows(TS + '21_team_proposals/comparison.csv', 'program x scenario')
    sales = rows(TS + '17_aircraft_route_review/model/sales.csv', 'dated offered final itinerary x scenario')
    caps = rows(TS + '17_aircraft_route_review/model/capacity.csv', 'physical flight x scenario')
    flights = rows(TS + '17_aircraft_route_review/model/flights.csv', 'dated physical flight/planning label')
    names = sorted({r['network'] for r in comp})
    assert len(names) == 4 and len(comp) == 8
    program = {}
    calendars = []
    source_cost_checks = 0
    for r in comp:
        n, sc = r['network'], r['scenario']
        p = config['scenarios'][sc]
        identity = r['source_profile'], r['source_network']
        ss = [dict(s) for s in sales if (s['profile'], s['network'], s['scenario']) == (*identity, sc)]
        cc = [dict(c) for c in caps if (c['profile'], c['network'], c['scenario']) == (*identity, sc)]
        ff = [dict(f) for f in flights if (f['profile'], f['network']) == identity]
        assert len({f['id'] for f in ff}) == len(ff)
        assert len({c['flight_id'] for c in cc}) == len(cc)
        fm = {f['id']: f for f in ff}
        assert set(fm) == {c['flight_id'] for c in cc} == {i for s in ss for i in s['flight_ids'].split(';')}
        for c in cc:
            f = fm[c['flight_id']]
            assert (c['origin'], c['destination']) == (f['origin'], f['destination'])
            equal(c['block_minutes'], f['block_minutes'], 'capacity block time')
            equal(cost(float(f['block_minutes']), p), c['flight_variable_cost'], 'independent flight recipe')
            source_cost_checks += 1
        equal(sum(float(f['block_minutes']) for f in ff) / 60, r['weekly_block_hours'], 'program hours')
        tails = sorted({f['aircraft'] for f in ff})
        assert len(tails) == int(r['active_allocated'])
        for label in tails:
            seq = sorted([f for f in ff if f['aircraft'] == label], key=lambda f: float(f['departure_utc_minute']))
            gaps = []
            daily = collections.defaultdict(list)
            for f in seq:
                d, a = float(f['departure_utc_minute']), float(f['arrival_utc_minute'])
                equal(a - d, f['block_minutes'], 'elapsed block')
                assert 0 <= d < a <= 7 * 1440
                daily[int(d // 1440)].append(f)
            for a, b in zip(seq, seq[1:]):
                assert a['destination'] == b['origin'], ('location discontinuity', n, label)
                gaps.append(float(b['departure_utc_minute']) - float(a['arrival_utc_minute']))
                assert gaps[-1] >= 45
            max_daily = max(sum(float(f['block_minutes']) for f in fs) / 60 for fs in daily.values())
            max_span = max((max(float(f['arrival_utc_minute']) for f in fs) - min(float(f['departure_utc_minute']) for f in fs)) / 60 for fs in daily.values())
            assert max_daily <= config['config']['planning_cap_block_h']
            assert max_span <= config['config']['span_cap_h']
            calendars.append(dict(network=n, scenario=sc, planning_label=n + '|' + label, legs=len(seq),
                                  min_turn=min(gaps), max_daily_block_h=max_daily, max_daily_span_h=max_span,
                                  calendar='MODEL_LABELS_ONLY', actual_tail='UNKNOWN', slots='UNKNOWN', crew='UNKNOWN'))
        for s in ss:
            linked = s['flight_ids'].split(';')
            assert len(linked) == len(set(linked))
            seq = [fm[i] for i in linked]
            assert seq[0]['origin'] == s['origin'] and seq[-1]['destination'] == s['destination']
            assert (len(seq) > 1) == (s['transfer'] == 'True')
            for a, b in zip(seq, seq[1:]):
                assert a['destination'] == b['origin']
                wait = float(b['departure_utc_minute']) - float(a['arrival_utc_minute'])
                assert config['config']['min_connection_minutes'] <= wait <= config['config']['max_connection_minutes']
            s['flight_ids'] = ';'.join(n + '|' + i for i in linked)
            s['_program'] = n
        for c in cc:
            c['flight_id'] = n + '|' + c['flight_id']
        program[n, sc] = r, ss, cc, {n + '|' + i: f for i, f in fm.items()}
    check('source_calendar_and_per_flight_recipe', flight_cost_cases=source_cost_checks, planning_label_scenario_rows=len(calendars))
    save('independent_calendar_checks.csv', calendars)

    def run(subset, sc, law):
        p = config['scenarios'][sc]
        parts = [program[n, sc] for n in subset]
        offers = [s for _, ss, _, _ in parts for s in ss]
        capacity = {c['flight_id']: float(c['capacity_scenario']) for _, _, cc, _ in parts for c in cc}
        fm = {i: f for _, _, _, ffs in parts for i, f in ffs.items()}
        assert len(capacity) == sum(len(cc) for _, _, cc, _ in parts) == len(fm)
        initial = dict(capacity)
        grouped = collections.defaultdict(list)
        for s in offers:
            grouped[s['origin'], s['destination']].append(s)
        known_pairs = {frozenset(k) for k, ss in grouped.items() if any(s['known_direct_RW_capacity'] and float(s['known_direct_RW_capacity']) > 0 for s in ss)}
        rates, oldfares, fractions, frequencies, migration_budget = {}, {}, {}, {}, {}
        for k, ss in grouped.items():
            for field in ['D', 'fare_once', 'transfer', 'known_direct_RW_capacity']:
                assert len({s[field] for s in ss}) == 1
            times = {(fm[s['flight_ids'].split(';')[0]]['date'], float(fm[s['flight_ids'].split(';')[0]]['departure_utc_minute'])) for s in ss}
            freq = len(ss) if law == 'COUNT_ALL_OFFERS' else len(times)
            frequencies[k] = len(ss), len(times)
            rates[k] = (.45 if sc == 'base' else .30) * (-math.expm1(-freq / 3)) * (.65 if ss[0]['transfer'] == 'True' else 1) / len(ss)
            fractions[k] = ((.6 if sc == 'base' else .8) if frozenset(k) in known_pairs else (.05 if sc == 'base' else .1))
            oldfares[k] = float(ss[0]['fare_once']) * p['old_RW_fare_ratio'] / (p['transfer_fare_factor'] if ss[0]['transfer'] == 'True' else 1)
            migration_budget[k] = float(ss[0]['known_direct_RW_capacity'] or 0)
        def order(s):
            k = s['origin'], s['destination']
            legs = s['flight_ids'].split(';')
            margin_per_seat = (float(s['fare_once']) - fractions[k] * oldfares[k] - len(legs) * p['pax_cost']) / len(legs)
            return s['transfer'] == 'True', -margin_per_seat, *k, int(s['day']), tuple(legs)
        detail = []
        used = collections.Counter()
        sold_market = collections.Counter()
        for s in sorted(offers, key=order):
            k = s['origin'], s['destination']
            legs = s['flight_ids'].split(';')
            desired = float(s['D']) * rates[k]
            q = min([desired] + [capacity[i] for i in legs])
            direct = min(q * fractions[k], migration_budget[k])
            migration_budget[k] -= direct
            unverified = q * fractions[k] - direct
            for i in legs:
                used[i] += q
                capacity[i] -= q
            sold_market[k] += q
            detail.append(dict(program=s['_program'], origin=k[0], destination=k[1], day=int(s['day']), flight_ids=s['flight_ids'],
                               transfer=s['transfer'] == 'True', D=float(s['D']), desired=desired, fare_once=float(s['fare_once']),
                               sold_journeys=q, transfer_journeys=q if len(legs) > 1 else 0, segment_pax=q * len(legs),
                               migrated_RW_direct=direct, migrated_RW_unverified_connecting=unverified, migrated_RW_total=direct + unverified,
                               gross_revenue=q * float(s['fare_once']), foregone_RW_revenue=(direct + unverified) * oldfares[k],
                               new_pax_variable=q * len(legs) * p['pax_cost'], saved_old_pax_variable=(direct + 2 * unverified) * p['pax_cost']))
        keys = ['sold_journeys', 'transfer_journeys', 'segment_pax', 'migrated_RW_total', 'migrated_RW_direct',
                'migrated_RW_unverified_connecting', 'gross_revenue', 'foregone_RW_revenue', 'new_pax_variable', 'saved_old_pax_variable']
        result = {k: math.fsum(d[k] for d in detail) for k in keys}
        result['flight_variable_cost'] = math.fsum(cost(float(f['block_minutes']), p) for f in fm.values())
        result['incremental_revenue'] = result['gross_revenue'] - result['foregone_RW_revenue']
        result['contribution_before_base_fleet_opportunity'] = result['incremental_revenue'] - result['flight_variable_cost'] - result['new_pax_variable'] + result['saved_old_pax_variable']
        result['load_factor'] = result['segment_pax'] / math.fsum(initial.values())
        result['net_new_RW_journeys_scenario'] = result['sold_journeys'] - result['migrated_RW_total']
        equal(math.fsum(used.values()), result['segment_pax'], 'seat incidence')
        for i in initial:
            assert -1e-8 <= capacity[i] <= initial[i] + 1e-8
            equal(initial[i] - capacity[i], used[i], 'individual flight seats')
        market = []
        for k, ss in grouped.items():
            D = float(ss[0]['D'])
            ds = [d for d in detail if (d['origin'], d['destination']) == k]
            assert sold_market[k] <= D + 1e-8
            assert migration_budget[k] >= -1e-8
            direct = sum(d['migrated_RW_direct'] for d in ds)
            known = float(ss[0]['known_direct_RW_capacity'] or 0)
            assert direct <= known + 1e-8
            market.append(dict(origin=k[0], destination=k[1], D=D, all_offers=frequencies[k][0], distinct_times=frequencies[k][1],
                               components=len({s['_program'] for s in ss}), additive_sold=sum(float(s['sold_journeys']) for s in ss),
                               pooled_sold=sold_market[k], known_own_cap=known, direct_migration=direct,
                               unverified_connecting_migration=sum(d['migrated_RW_unverified_connecting'] for d in ds)))
        working = sum(int(r['active_allocated']) for r, _, _, _ in parts)
        additive = math.fsum(float(r['contribution_before_base_fleet_opportunity']) for r, _, _, _ in parts)
        return dict(portfolio='+'.join(subset), scenario=sc, capture_law=law, working_required=working, reserve_assumption=1,
                    current4_working_ceiling_pass=working <= 4, extra_working_above4=max(0, working - 4),
                    new_UFA_base_count=int(any(n.startswith('H_UFA') for n in subset)), **result,
                    additive_component_contribution=additive, delta_vs_additive=result['contribution_before_base_fleet_opportunity'] - additive), detail, market

    calculated, details, markets = [], [], []
    for size in range(1, 5):
        for subset in itertools.combinations(names, size):
            for sc in ['base', 'cautious']:
                for law in ['COUNT_ALL_OFFERS', 'COUNT_DISTINCT_DEPARTURE_TIMES']:
                    r, dd, mm = run(subset, sc, law)
                    calculated.append(r)
                    meta = {k: r[k] for k in ['portfolio', 'scenario', 'capture_law']}
                    markets.extend(dict(**meta, **d) for d in mm)
                    if size == 2:
                        details.extend(dict(**meta, **d) for d in dd)
                    if size == 1:
                        original = program[subset[0], sc][0]
                        for k in r.keys() & original.keys():
                            if isinstance(r[k], (float, int)):
                                equal(r[k], original[k], 'singleton ' + k)
    # Only now consult the subject's outputs, as comparison targets.
    expected = rows('runs/portfolio_v1/summary.csv', 'portfolio x scenario x frequency law', 'comparison_target')
    key = lambda r: (r['portfolio'], r['scenario'], r['capture_law'])
    em = {key(r): r for r in expected}
    assert len(em) == len(expected) == len(calculated) == 60
    deltas = []
    for r in calculated:
        mx = 0
        for k, v in r.items():
            if isinstance(v, bool):
                assert str(v) == em[key(r)][k]
            elif isinstance(v, (int, float)):
                mx = max(mx, equal(v, em[key(r)][k], 'portfolio ' + str(key(r)) + ' ' + k))
        deltas.append(dict(portfolio=r['portfolio'], scenario=r['scenario'], capture_law=r['capture_law'], max_abs_numeric_delta=mx,
                           market_guard='PASS', seats_each_flight='PASS', onefare='PASS', flightcost_once='PASS', known_migration_budget='PASS'))
    expected_detail = rows('runs/portfolio_v1/pair_portfolio_itineraries.csv', 'pair portfolio x dated itinerary', 'comparison_target')
    dk = lambda r: (*key(r), r['origin'], r['destination'], r['flight_ids'])
    dm = {dk(r): r for r in expected_detail}
    assert len(dm) == len(expected_detail) == len(details)
    max_detail_delta = 0
    for r in details:
        for k, v in r.items():
            if isinstance(v, (float, int)) and not isinstance(v, bool):
                max_detail_delta = max(max_detail_delta, equal(v, dm[dk(r)][k], 'pair itinerary ' + k))
    distinct = {tuple((k, round(v, 8)) for k, v in r.items() if isinstance(v, (float, int)) and not isinstance(v, bool)) for r in calculated}
    assert len(distinct) == 30 and sum(r['current4_working_ceiling_pass'] for r in calculated) == 28
    assert all(m['all_offers'] == m['distinct_times'] for m in markets)
    assert all(r['contribution_before_base_fleet_opportunity'] < 0 for r in calculated)
    check('portfolio_reproduction', cases=60, subsets=15, distinct_outcomes=30, ceiling_pass=28,
          pair_itineraries=len(details), max_detail_delta=max_detail_delta, max_summary_delta=max(d['max_abs_numeric_delta'] for d in deltas))
    save('independent_portfolios.csv', calculated)
    save('independent_pair_itineraries.csv', details)
    save('independent_market_pools.csv', markets)
    save('portfolio_comparison_checks.csv', deltas)
    marginals = []
    singles = {(r['portfolio'], r['scenario'], r['capture_law']): r for r in calculated if '+' not in r['portfolio']}
    for r in calculated:
        subset = r['portfolio'].split('+')
        if len(subset) != 2:
            continue
        for incumbent, added in [subset, subset[::-1]]:
            old = singles[incumbent, r['scenario'], r['capture_law']]
            added_r = singles[added, r['scenario'], r['capture_law']]
            scoped = [d for d in details if key(d) == key(r)]
            def contribution_for(n):
                dd = [d for d in scoped if d['program'] == n]
                fc = float(program[n, r['scenario']][0]['flight_variable_cost'])
                return sum(d['gross_revenue'] - d['foregone_RW_revenue'] - d['new_pax_variable'] + d['saved_old_pax_variable'] for d in dd) - fc
            incumbent_joint = contribution_for(incumbent)
            new_joint = contribution_for(added)
            delta_total = r['contribution_before_base_fleet_opportunity'] - old['contribution_before_base_fleet_opportunity']
            incumbent_change = incumbent_joint - old['contribution_before_base_fleet_opportunity']
            equal(delta_total, incumbent_change + new_joint, 'joint marginal including incumbent loss')
            marginals.append(dict(**{k: r[k] for k in ['portfolio', 'scenario', 'capture_law']}, incumbent=incumbent, added=added,
                                  incumbent_loss_or_gain=incumbent_change, added_joint_contribution=new_joint,
                                  added_standalone_contribution=added_r['contribution_before_base_fleet_opportunity'],
                                  total_marginal=delta_total, delta_from_standalone=delta_total - added_r['contribution_before_base_fleet_opportunity']))
    save('independent_marginals.csv', marginals)

    # Resource lower bounds: read replayed hours as pinned inputs, do not reopen MR08.
    resource_cfg = obj(TS + '16_conditional_decision/assumptions.json')['resource']
    na = {r['parameter']: r for r in rows('inputs/set001/nastya_2f03/data/assumptions/network.csv', 'parameter x scenario')}
    evaluations = rows('inputs/model-repair-001/proposed_common_view/evaluation_summary.csv', 'author replay candidate x scenario')
    resources = []
    for r in evaluations:
        if r['model_id'] != 'anastasia_network_author':
            continue
        sc = r['scenario_id']
        h = float(r['weekly_block_hours'])
        working = float(na['fleet_cap'][sc]) - float(na['spare_aircraft'][sc])
        author_cap = working * 7 * float(na['block_h_per_day'][sc])
        common_cap = resource_cfg['active_aircraft'] * resource_cfg['work_days'] * resource_cfg['planning_cap_block_h']
        assert author_cap == 630 and common_cap == 240
        resources.append(dict(model='anastasia', candidate=r['candidate_id'], scenario=sc, weekly_block_hours=h,
                              author_cap=author_cap, common_cap=common_cap, common_necessary_gate=h <= common_cap,
                              ceil_working_6days=math.ceil(h / 60), ceil_working_7days=math.ceil(h / 70),
                              calendar=None, actual_tail_requirement=None, acceptance='HOURS_ONLY_CALENDAR_NOT_RUN'))
    for r in comp:
        ff = list(program[r['network'], r['scenario']][3].values())
        h = sum(float(f['block_minutes']) for f in ff) / 60
        resources.append(dict(model='ciri_context21', candidate=r['network'], scenario=r['scenario'], weekly_block_hours=h,
                              author_cap=240, common_cap=240, common_necessary_gate=h <= 240,
                              ceil_working_6days=math.ceil(h / 60), ceil_working_7days=math.ceil(h / 70),
                              calendar='MODEL_LABELS_CHECKED', actual_tail_requirement=None,
                              planning_labels=len({f['aircraft'] for f in ff}), acceptance='MODEL_CALENDAR_NOT_ACTUAL_DISPATCH'))
    er = rows('runs/resource_v1/resource_envelopes.csv', 'model x candidate x scenario', 'comparison_target')
    eri = {(r['model'], r['candidate'], r['scenario']): r for r in er}
    assert len(resources) == len(eri) == 20
    for r in resources:
        target = eri[r['model'], r['candidate'], r['scenario']]
        equal(r['weekly_block_hours'], target['weekly_block_hours'], 'resource hours')
        equal(r['ceil_working_6days'], target['minimum_working_by_hours_only'], 'resource ceil')
        assert str(r['common_necessary_gate']) == target['common_hours_necessary_gate_pass']
        if r['model'] == 'anastasia':
            assert target['actual_dated_tail_requirement'] == ''
    npass = [r for r in resources if r['model'] == 'anastasia' and r['common_necessary_gate']]
    assert {(r['candidate'], r['scenario']) for r in npass} == {('KUF', 'base'), ('KUF', 'cautious'), ('GOJ', 'cautious')}
    check('resources', rows=20, anastasia_necessary_pass=3, calendar_null_not_pass=True)
    save('independent_resources.csv', resources)

    # Every relative boundary includes the full symbolic difference in O.
    boundaries = []
    for sc in ['base', 'cautious']:
        for a, b in itertools.combinations(names, 2):
            ar, br = singles[a, sc, 'COUNT_ALL_OFFERS'], singles[b, sc, 'COUNT_ALL_OFFERS']
            dc = ar['contribution_before_base_fleet_opportunity'] - br['contribution_before_base_fleet_opportunity']
            dn = (ar['working_required'] + 1) - (br['working_required'] + 1)
            db = ar['new_UFA_base_count'] - br['new_UFA_base_count']
            boundaries.append(dict(scenario=sc, left=a, right=b, contribution_difference=dc, F_coefficient=dn, B_coefficient=db,
                                   criterion_left_at_least_right=f'{dn}*F + {db}*B + (O_left-O_right) <= {dc:.10f}',
                                   scope='F,B>=0; same additional rates, period, markets; conditional losses only'))
    def C(n, sc='base'):
        return singles[n, sc, 'COUNT_ALL_OFFERS']['contribution_before_base_fleet_opportunity']
    thresholds = dict(base_B_H4_vs_Dprev=C('H_UFA_4') - C('D_previous_best8'),
                      base_FplusB_H4_vs_DSVX=C('H_UFA_4') - C('D_SVX8'),
                      base_F_Dprev_vs_DSVX=C('D_previous_best8') - C('D_SVX8'),
                      cautious_F_Dprev_vs_DSVX=C('D_previous_best8', 'cautious') - C('D_SVX8', 'cautious'))
    for k, expected_value in zip(thresholds, [400166.28, 2703326.68, 2303160.40, 3319608.30]):
        equal(thresholds[k], expected_value, k, tol=.005)
    def after_budget(n, sc, F, B, O=0):
        r = singles[n, sc, 'COUNT_ALL_OFFERS']
        return r['contribution_before_base_fleet_opportunity'] - (r['working_required'] + 1) * F - r['new_UFA_base_count'] * B - O
    boundary_sides = []
    tests = [('H_UFA_4', 'D_previous_best8', 'base', 'B', thresholds['base_B_H4_vs_Dprev']),
             ('H_UFA_4', 'D_SVX8', 'base', 'FplusB', thresholds['base_FplusB_H4_vs_DSVX']),
             ('D_previous_best8', 'D_SVX8', 'base', 'F', thresholds['base_F_Dprev_vs_DSVX']),
             ('D_previous_best8', 'D_SVX8', 'cautious', 'F', thresholds['cautious_F_Dprev_vs_DSVX'])]
    for left, right, sc, axis, threshold in tests:
        for offset in [-1, 0, 1]:
            value = threshold + offset
            F, B = (0, value) if axis == 'B' else (value, 0) if axis == 'F' else (.4 * value, .6 * value)
            difference = after_budget(left, sc, F, B) - after_budget(right, sc, F, B)
            equal(difference, -offset, 'budget boundary side')
            boundary_sides.append(dict(left=left, right=right, scenario=sc, axis=axis, threshold=threshold, offset=offset,
                                       F=F, B=B, O_difference=0, left_minus_right_after_budget=difference))
    for sc in ['base', 'cautious']:
        assert C('D_previous_best8', sc) > C('H_UFA_8', sc)
    assert C('D_previous_best8', 'cautious') > C('H_UFA_4', 'cautious')
    save('independent_budget_boundaries.csv', boundaries)
    save('budget_boundary_sides.csv', boundary_sides)
    save('budget_thresholds.json', thresholds)
    check('relative_budget_boundaries', inequalities=len(boundaries), side_witnesses=len(boundary_sides), unknown_O_kept=True, KEEP_relative_zero_not_business_profit=True)

    product_rows = rows(HY + 'cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv', 'product x gap x fare x journey cost')
    selected = [r for r in product_rows if float(r['residual_funding_gap_rub']) == 1000000 and float(r['net_fare_rub_per_oneway_journey']) == 8000 and float(r['variable_cost_rub_per_oneway_journey']) == 500]
    assert len(selected) == 3
    units = []
    for r in selected:
        legs = int(r['legs_per_oneway_journey'])
        for scenario, var in [('AUTHOR500_PER_JOURNEY', 500), ('COMMON500_PER_OCCUPIED_SEGMENT', 500 * legs)]:
            per_return = 2 * (8000 - var)
            clients = math.ceil(1000000 / per_return)
            assert (clients - 1) * per_return < 1000000 <= clients * per_return
            if scenario.startswith('AUTHOR'):
                equal(clients, r['roundtrip_customers'], 'frozen author client threshold')
                equal(2 * clients * legs, r['physical_boardings'], 'frozen boardings')
            units.append(dict(candidate=r['candidate'], scenario=scenario, legs=legs, roundtrip_clients=clients,
                              endpoint_journeys=2 * clients, occupied_segments=2 * clients * legs,
                              contribution=clients * per_return, one_client_below=(clients - 1) * per_return,
                              source_unit='journey', scenario_cost_per_journey=var, real_gap=None, actual_tariff=None, residual_seats=None))
    eu = rows('runs/product_bridge_v1/journey_segment_unit_bridge.csv', 'product x unit scenario', 'comparison_target')
    eum = {(r['candidate'], r['scenario']): r for r in eu}
    for r in units:
        for k in ['roundtrip_clients', 'endpoint_journeys', 'occupied_segments', 'contribution']:
            equal(r[k], eum[r['candidate'], r['scenario']][k], 'product bridge ' + k)
    c07 = next(r for r in rows(HY + 'runs/c26661067277af20/c07_comparison.csv', 'C07 turn variant vs frozen reference') if r['variant'] == 'C07_chain_turn45')
    product_legs = rows(HY + 'runs/c26661067277af20/physical_legs.csv', 'product variant x dated physical leg')
    raw_variants = {}
    for variant in ['C07_chain_turn45', 'C07_reference']:
        vv = [r for r in product_legs if r['variant'] == variant]
        # Each row belongs to one illustrative C07 rotation, not an annual schedule.
        assert vv
        block = sum(float(r['block_minutes']) for r in vv)
        for r in vv:
            equal((datetime.fromisoformat(r['arrival_utc']) - datetime.fromisoformat(r['departure_utc'])).total_seconds() / 60,
                  r['block_minutes'], 'C07 physical leg duration')
        raw_variants[variant] = dict(block=block, legs=len(vv), elapsed=(max(datetime.fromisoformat(r['arrival_utc']) for r in vv) - min(datetime.fromisoformat(r['departure_utc']) for r in vv)).total_seconds() / 60)
    a, b = raw_variants['C07_chain_turn45'], raw_variants['C07_reference']
    equal(a['block'], c07['block_candidate_minutes'], 'C07 raw candidate block')
    equal(b['block'], c07['block_baseline_minutes'], 'C07 raw reference block')
    equal(a['elapsed'] - b['elapsed'], c07['return_delay_vs_reference_minutes'], 'C07 raw elapsed difference')
    delta_minutes = a['block'] - b['block']
    delta_legs = a['legs'] - b['legs']
    assert delta_minutes == 270 and delta_legs == 2 and float(c07['return_delay_vs_reference_minutes']) == 355
    c07_costs = []
    for sc, p in config['scenarios'].items():
        # Sum all candidate flights minus all reference flights. No bridge helper.
        added = 4 * cost(float(c07['block_candidate_minutes']) / 4, p) - 2 * cost(float(c07['block_baseline_minutes']) / 2, p)
        fare = (added + 200 * p['pax_cost']) / 200
        c07_costs.append(dict(scenario=sc, added_block_minutes=delta_minutes, added_departures=delta_legs,
                              added_elapsed_minutes=355, added_flight_cost=added, fare_at100_eachdirection=fare,
                              unknown_next_assignment=True, unknown_base=True, unknown_actual_tariff=True,
                              basis='CIRI_UFA_REFERENCE_RECIPE_NOT_OMS_KJA_CONTRACT'))
    ec = rows('runs/product_bridge_v1/c07_cost_recipe_bridge.csv', 'C07 recipe x scenario', 'comparison_target')
    for r, target in zip(c07_costs, ec):
        assert r['scenario'] == target['scenario']
        equal(r['added_flight_cost'], target['added_flight_cost_rub'], 'C07 flight cost')
        equal(r['fare_at100_eachdirection'], target['minimum_net_oneway_fare_if100local_each_direction'], 'C07 fare')
    save('independent_product_units.csv', units)
    save('independent_c07_costs.csv', c07_costs)
    check('product_bridge', unit_cases=6, cost_cases=2, assumption_unit_change_not_author_arithmetic_error=True)

    # Temporal counterexample only; no MR02 cash, costs, sources or root correction replay.
    definition = obj('inputs/cost-kover-001/scenario_definitions.json')
    kl = [r for r in rows('inputs/cost-kover-001/inputs/tsiri_flights.csv', 'absolute UTC-minute physical flight') if r['profile'] == 'ROUTE_INPUTS_UPPER_100' and r['network'] == 'H_UFA_8']
    assert definition['period_start'] == '2026-12-07'
    def touching(r, day):
        return ((r['origin'] == 'UFA' and day * 1440 <= float(r['departure_utc_minute']) < (day + 1) * 1440)
                or (r['destination'] == 'UFA' and day * 1440 <= float(r['arrival_utc_minute']) < (day + 1) * 1440))
    touched = {r['id'] for r in kl if touching(r, 0)}
    assert len(touched) == 16 and sum(touching(r, 1) for r in kl) == 16
    shifted = [dict(r, departure_utc_minute=float(r['departure_utc_minute']) + (1440 if r['id'] in touched else 0),
                    arrival_utc_minute=float(r['arrival_utc_minute']) + (1440 if r['id'] in touched else 0)) for r in kl]
    def sweep(seq):
        events = collections.defaultdict(lambda: [[], []])
        for f in seq:
            events[float(f['departure_utc_minute'])][1].append(f['id'])
            events[float(f['arrival_utc_minute'])][0].append(f['id'])
        active, peak, timeline = set(), 0, []
        times = sorted(events)
        for i, t in enumerate(times):
            ended, started = events[t]
            active.difference_update(ended)  # Half-open [dep,arr): arrivals leave first.
            active.update(started)
            peak = max(peak, len(active))
            timeline.append(dict(start_utc_minute=t, end_utc_minute=times[i + 1] if i + 1 < len(times) else t,
                                 in_flight=len(active), flight_ids=';'.join(sorted(active))))
        return peak, timeline
    base_peak, base_time = sweep(kl)
    shifted_peak, shifted_time = sweep(shifted)
    assert (base_peak, shifted_peak) == (4, 8)
    conflicts = []
    for label in sorted({r['aircraft'] for r in shifted}):
        seq = sorted([r for r in shifted if r['aircraft'] == label], key=lambda r: float(r['departure_utc_minute']))
        for a, b in zip(seq, seq[1:]):
            gap = float(b['departure_utc_minute']) - float(a['arrival_utc_minute'])
            discontinuity = a['destination'] != b['origin']
            if discontinuity or gap < 45:
                conflicts.append(dict(label=label, left=a['id'], right=b['id'], gap_minutes=gap,
                                      airport_discontinuity=discontinuity, overlap=gap < 0))
    assert len(conflicts) == 23
    probe = obj('checks/kover_timebase/probe.json', 'comparison_target')
    assert len(probe['corrected_delay_rotation_issues']) == len(conflicts)
    assert probe['baseline_peak_simultaneous_flights'] == base_peak and probe['shifted_peak_simultaneous_flights'] == shifted_peak
    save('independent_temporal_intervals.csv', [dict(scenario='baseline', **r) for r in base_time] + [dict(scenario='day1_shifted_1440', **r) for r in shifted_time])
    save('independent_temporal_conflicts.csv', conflicts)
    witness = next(r for r in shifted_time if r['in_flight'] == 8 and r['end_utc_minute'] > r['start_utc_minute'])
    save('temporal_counterexample.json', dict(epoch='2026-12-07T00:00:00Z', interval='[departure,arrival)',
         baseline_peak=base_peak, shifted_peak=shifted_peak, shifted_legs=16, planning_sequence_conflicts=len(conflicts),
         peak_witness=witness, minimum_airborne_aircraft=8, baseline_working=4, even_total_with_reserve=5,
         actual_recovery='HOLD_NO_SUPPLIED_RESOURCE_OR_NEW_CALENDAR', MR02_broad_scope='NOT_RUN', root_correction='NOT_ADOPTED'))
    check('temporal_resource_counterexample', shifted_legs=16, rotation_conflicts=23, baseline_peak=4, shifted_peak=8, half_open=True)

    # Reviewer-owned numeric counterexamples; not presented as actual demand.
    q = lambda freq: .45 * (-math.expm1(-freq / 3))
    overlap = next(r for r in calculated if r['portfolio'] == 'D_SVX8+D_previous_best8' and r['scenario'] == 'base' and r['capture_law'] == 'COUNT_ALL_OFFERS')
    h_overlap = next(r for r in calculated if r['portfolio'] == 'H_UFA_4+H_UFA_8' and r['scenario'] == 'base' and r['capture_law'] == 'COUNT_ALL_OFFERS')
    equal(overlap['delta_vs_additive'], -446063.89, 'D overlap delta', .005)
    # The brief states this value rounded to six decimals in million RUB.
    assert round(h_overlap['delta_vs_additive'] / 1000000, 6) == -1.944893
    # Duplicate timestamps: two flights, one temporal opportunity; both retain seats/costs.
    same_time = dict(D=480, separate_claims=2 * 480 * q(1), count_all_offers=480 * q(2), count_distinct_times=480 * q(1),
                     offers=2, distinct_departures=1, flights_paid=2,
                     implication='Coincident supply does not establish additional temporal convenience; laws diverge in this synthetic case.')
    assert same_time['count_all_offers'] < same_time['separate_claims'] < 480
    # Extract source functions as the SUT, never as the independent oracle.
    tree = ast.parse(read('common_demand.py', 'reviewed pure function bodies', 'review_subject'))
    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'near', 'pair', 'prepare', 'simulate'}]
    sut = dict(collections=collections, math=math)
    exec(compile(ast.Module(body=funcs, type_ignores=[]), PIN + ':common_demand.py', 'exec'), sut)
    def synthetic_offer(day, linked, destination='B', D=10000, fare=8000, known='30'):
        return dict(origin='A', destination=destination, day=str(day), flight_ids=linked, transfer=str(';' in linked),
                    D=str(D), fare_once=str(fare), known_direct_RW_capacity=known)
    synthetic_caps = [dict(flight_id=i, capacity_scenario='80', flight_variable_cost='1000') for i in ['f1', 'f2']]
    synthetic_sales = [synthetic_offer(1, 'f1'), synthetic_offer(2, 'f2')]
    pbase = config['scenarios']['base']
    migrated_result, migrated_detail, _ = sut['simulate'](sut['prepare'](synthetic_sales, synthetic_caps, 'base', pbase), synthetic_caps, pbase)
    equal(migrated_result['migrated_RW_direct'], 30, 'synthetic shared direct budget SUT')
    equal(migrated_result['migrated_RW_unverified_connecting'], 66, 'synthetic unverified connecting migration SUT')
    equal(migrated_result['saved_old_pax_variable'], 81000, 'synthetic shared direct saved cost SUT')
    equal(migrated_result['contribution_before_base_fleet_opportunity'], 511000, 'synthetic migration ledger SUT')
    # Small old direct inventory: budget exhaustion changes direct/connecting mix,
    # not the total assumed migration. Resetting cap per program wrongly doubles it.
    own = dict(offers_sold=[80, 80], migration_fraction=.6, known_direct_budget=30,
               shared_direct=[30, 0], wrong_reset_direct=[30, 30], unverified_connecting=[18, 48],
               correct_saved_old_pax_cost=(30 + 2 * 66) * 500,
               wrong_reset_saved_old_pax_cost=(60 + 2 * 36) * 500,
               implication='Known direct budget remains30; connecting migration is unverified, not an observed shared inventory.')
    own['subject_result'] = migrated_result
    own['subject_direct_allocations'] = [r['migrated_RW_direct'] for r in migrated_detail]
    # One local journey and one through journey compete for f1. High through
    # fare does not overtake local-first; through revenue is still counted once.
    local_sales = [synthetic_offer(1, 'f1', D=500, fare=5000, known=''),
                   synthetic_offer(1, 'f1;f2', destination='C', D=10000, fare=20000, known='')]
    local_caps = [dict(flight_id=i, capacity_scenario='100', flight_variable_cost='1000') for i in ['f1', 'f2']]
    local_result, local_detail, local_remaining = sut['simulate'](sut['prepare'](local_sales, local_caps, 'base', pbase), local_caps, pbase)
    local_q = 500 * q(1)
    through_q = 100 - local_q
    equal(local_detail[0]['sold_journeys'], local_q, 'local-first SUT')
    equal(local_detail[1]['sold_journeys'], through_q, 'shared seat residual SUT')
    equal(local_result['gross_revenue'], local_q * 5000 + through_q * 20000, 'through fare once SUT')
    equal(local_result['segment_pax'], local_q + 2 * through_q, 'itinerary leg incidence SUT')
    equal(local_remaining['f1'], 0, 'shared first leg SUT')
    local_seat_example = dict(local_sold=local_q, through_sold=through_q, shared_first_leg_used=100,
                              subject_result=local_result, subject_remaining=local_remaining,
                              implication='Local-first can bind a high-fare connection; one through ticket consumes each leg and earns one fare.')
    # Aggregate hours can pass despite simultaneous flight count exceeding supply.
    synthetic_hours = dict(aircraft_limit=1, work_days=6, daily_hours=10, total_block_hours=2,
                           aggregate_limit=60, intervals=[[0, 60], [0, 60]], peak_airborne=2,
                           implication='Necessary hours pass; one aircraft cannot operate both intervals.')
    unequal_O = dict(F=0, B=0, O_Dprev=0, O_H4=thresholds['base_B_H4_vs_Dprev'] + 1,
                     H4_minus_Dprev_after_O=-1, implication='Equal-O relative ordering reverses with explicit additional O; unknown O cannot be set to zero.')
    half_open = dict(intervals=[[0, 60], [60, 120]], expected_peak=1, wrong_closed_interval_peak=2,
                     implication='Touching arrival/departure endpoints do not overlap in airborne count; turnaround is a separate constraint.')
    endpoint_peak, _ = sweep([dict(id='a', departure_utc_minute=0, arrival_utc_minute=60), dict(id='b', departure_utc_minute=60, arrival_utc_minute=120)])
    assert endpoint_peak == 1
    increased_transfer = next(r for r in markets if r['portfolio'] == 'H_UFA_4+H_UFA_8' and r['scenario'] == 'base' and r['capture_law'] == 'COUNT_ALL_OFFERS' and (r['origin'], r['destination']) == ('MRV', 'OMS'))
    assert increased_transfer['pooled_sold'] > increased_transfer['additive_sold']
    increased_transfer['implication'] = 'Reduced local capture frees shared seats; some existing transfer sales can increase. No cross-program connection was created.'
    save('counterexamples.json', dict(status='REVIEWER_CONSTRUCTED', actual_overlap_D=overlap, actual_overlap_H=h_overlap,
         duplicated_departure=same_time, shared_old_inventory=own, hours_not_calendar=synthetic_hours,
         local_first_onefare_seats=local_seat_example, unequal_other_costs=unequal_O, interval_endpoint=half_open,
         actual_transfer_increase=increased_transfer,
         no_launch=dict(all60_contributions_negative=True, KEEP='zero delta from itself; company PnL UNKNOWN', actual_donor='UNKNOWN')))
    check('reviewer_counterexamples', classes=9, pure_subject_function_synthetic_tests=2, actual_overlap_deltas=True, new_sources_or_frontier=False)
    authority = []
    for path in ['context/23_night_run_20261110/contract.md', 'context/23_night_run_20261110/briefs/strategy_accounting_review.md']:
        commit = '87ee52de15c2bdf396d9c06ba600fd413d5ab4a8'
        raw = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=REPO)
        authority.append(dict(path=path, commit=commit, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), grain='review authority'))
    save('source_manifest.json', dict(input_commit=PIN, access='git show only', author_module_executed=False,
         author_functions_as_subject='pair/prepare/simulate/near only, two synthetic tests; not oracle', review_authority=authority,
         output_tables_are_oracles=False, sources=list(inputs.values())))
    save('checks.json', dict(status='PASS_INDEPENDENT_SCOPED', input_commit=PIN, checks=checks,
         inherited_holds=['PRIMARY17B_OLD_SVX_LINEAGE_HOLD', 'MR02_DOUBLE_TIMEBASE_AND_DELAY_FEASIBILITY_HOLD'],
         not_run=['MR08 broad common model review', 'MR02 source/cost/cash review', 'root correction acceptance',
                  'new frontier experiments', 'observed demand', 'actual dispatch', 'full budget', 'launch acceptance']))
    print(json.dumps(dict(status='PASS', checks=len(checks), source_files=len(inputs), portfolio_cases=60,
                          overlap_D=overlap['delta_vs_additive'], overlap_H=h_overlap['delta_vs_additive'], temporal_conflicts=len(conflicts))))


if __name__ == '__main__':
    main()
