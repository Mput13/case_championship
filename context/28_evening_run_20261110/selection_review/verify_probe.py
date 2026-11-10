#!/usr/bin/env python3
"""EV-MR01: exact-blob replay and independent arithmetic/counterexamples.

Uses installed numpy/pandas; copies only the pinned methods package into our
ignored runtime. Never imports the live methods directory. All writes stay here.
Run: OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -B <this file> --owner-replay
"""
import argparse
import collections
import copy
import csv
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
SUBJECT = '48686bf2276c435d7a260f4de6741c9b65d26e32'
SCOPE = 'context/28_evening_run_20261110/methods/'
HERE = Path(__file__).resolve().parent
REPO = Path(subprocess.check_output(['git', '-C', str(HERE), 'rev-parse', '--show-toplevel'], text=True).strip())
RUNTIME = HERE / '.runtime/independent'
EVIDENCE = HERE / 'evidence'
EVIDENCE.mkdir(exist_ok=True)
CHECKS = collections.Counter()


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])


def write(name, obj):
    (EVIDENCE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def near(a, b, label, tolerance=1e-5):
    assert math.isfinite(a) and math.isfinite(b), (label, a, b)
    assert abs(a - b) <= tolerance + 1e-12 * max(abs(a), abs(b)), (label, a, b)
    CHECKS[label.split(':')[0]] += 1


def compare(a, b, label):
    if isinstance(a, (list, tuple)):
        assert len(a) == len(b), label
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, f'{label}/{i}')
    elif isinstance(a, dict):
        assert a.keys() == b.keys(), label
        for k in a:
            compare(a[k], b[k], f'{label}/{k}')
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        near(float(a), float(b), label)
    else:
        assert a == b, (label, a, b)


def extract():
    files = []
    for line in git('ls-tree', '-r', SUBJECT, SCOPE).decode().splitlines():
        meta, path = line.split('\t')
        mode, typ, blob = meta.split()
        assert typ == 'blob' and mode == '100644'
        raw = git('cat-file', 'blob', blob)
        target = RUNTIME / path[len(SCOPE):]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        files.append(dict(path=path, git_blob=blob, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
    (HERE / 'source_manifest.json').write_text(json.dumps(dict(subjectSHA=SUBJECT, scope=SCOPE, files=files), indent=2) + '\n')
    source = json.loads((RUNTIME / 'source_manifest.json').read_text())
    for x in source['files']:
        raw = (RUNTIME / x['path']).read_bytes()
        original = git('show', x['source_commit'] + ':' + x['source_path'])
        assert raw == original, x['path']
        assert hashlib.sha256(raw).hexdigest() == x['sha256'] and len(raw) == x['bytes']
        assert git('rev-parse', x['source_commit'] + ':' + x['source_path']).decode().strip() == x['git_blob']
    manifest = json.loads((RUNTIME / 'output_manifest.json').read_text())
    for x in manifest['files']:
        raw = (RUNTIME / x['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == x['sha256'] and len(raw) == x['bytes']
    write('provenance.json', dict(subjectSHA=SUBJECT, subject_files=len(files), source_files_verified_against_original_git_commits=len(source['files']), output_manifest_files=len(manifest['files']), all_pass=True))


# These formulas deliberately do not call nm.fare, nm.leg_share, nm.leg_cost,
# nm.capture, kernel.metrics or owner verify_selection.
def price(A, km):
    return A['fare_fixed_rub'] + km * A['fare_per_km_rub']


def share(A, L, f):
    if L['km'] < A['transfer_min_km']:
        return 0.0
    if L['competitive']:
        competitor = L['seg'] / (A['seats'] * A['competitor_lf'])
        return min(A['capture_competitive'], f / (f + competitor)) if competitor > 0 else 0.0
    return A['capture_open'] * (1.0 - math.exp(-f / A['capture_freq_scale']))


def cost(A, L, passengers):
    factor = A['route_factor_south'] if L['south'] else A['route_factor']
    hours = A['block_fixed_h'] + L['km'] * factor / A['block_speed_kmh']
    fixed = ((A['fuel_t_per_hour'] * hours + A['fuel_t_per_cycle']) * A['fuel_rub_per_t']
             + hours * (A['mro_rub_per_hour'] + A['crew_rub_per_hour'] + A['navigation_rub_per_hour'])
             + A['ground_rub_per_flight'] + A['deicing_rub_per_flight'])
    return hours, 2 * L['freq'] * fixed + 2 * passengers * A['pax_cost_rub']


def ledger(n, d, check=True):
    m, A, r = n['metrics'], n['assumptions'], n['result']
    W = A['weeks_per_year']
    key = m['id']
    trans = r[1] if m['kind'] == 'HUB' else []
    legs = list(r[0].values()) if m['kind'] == 'HUB' else [L for t in r for L in t[8]]
    pairs = collections.defaultdict(list)
    for L in legs:
        pairs[tuple(sorted((L['a'], L['b'])))].append(L)
    totals = dict(hours=0.0, cost=0.0, tickets=0.0, foregone=0.0, support=0.0, segments=0.0)
    for pair, members in pairs.items():
        L = members[0]
        F = sum(x['freq'] for x in members)
        demand = d.get(*pair, A['demand_scen']) / (2 * W)
        seg = d.seg(*pair, A['demand_scen']) / (2 * W)
        near(L['dem'], demand, 'raw_demand:' + key)
        near(L['seg'], seg, 'competitor_exposure:' + key)
        expected_rw = nm.RW_FREQ.get(frozenset(pair), 0.0) * A['seats'] * A['rw_existing_lf']
        near(L['rw_now'], expected_rw, 'old_RW_week:' + key)
        if m['kind'] == 'DIRECT':
            demand_sold = min(demand * share(A, L, F), F * A['seats'] * A['lf_max'])
            mg = min(demand_sold, expected_rw)
            for l in members:
                near(l['carried_dir_week'], demand_sold * l['freq'] / F, 'shared_market:' + key)
                near(l['migrated'], mg * l['freq'] / F, 'shared_migration:' + key)
        for l in members:
            p = l['carried_dir_week']
            assert p <= l['freq'] * A['seats'] * A['lf_max'] + 1e-7, key
            assert 0 <= l['migrated'] <= p + 1e-7, key
            h, c = cost(A, l, p)
            near(h, l['block_h'], 'block_time:' + key)
            totals['hours'] += 2 * l['freq'] * h
            totals['cost'] += c
            local = l['local_carried'] if m['kind'] == 'HUB' else p
            totals['tickets'] += 2 * local * price(A, l['km'])
            totals['foregone'] += 2 * l['migrated'] * price(A, l['km'])
            subsidy = A['subsidy_rub_per_pax'] * A['use_subsidy'] if 'MOW' not in pair else 0
            totals['support'] += 2 * (local - l['migrated']) * subsidy
            totals['segments'] += 2 * p
    if m['kind'] == 'HUB':
        H = m['network']
        by_x = r[0]
        target_local = {x: L['dem'] * share(A, L, L['freq']) for x, L in by_x.items()}
        wanted = dict(target_local)
        target_trans = []
        for i, x in enumerate(n['chosen']):
            for y in n['chosen'][i + 1:]:
                km = d.km(x, y)
                if km < A['transfer_min_km'] or d.has_direct(x, y):
                    continue
                if (d.km(H, x) + d.km(H, y)) / km > A['transfer_max_circuity']:
                    continue
                count = (d.get(x, y, A['demand_scen']) / (2 * W) * A['capture_transfer']
                         * (1 - math.exp(-min(by_x[x]['freq'], by_x[y]['freq']) / A['capture_freq_scale'])))
                wanted[x] += count
                wanted[y] += count
                target_trans.append((x, y, km, count))
        factors = {x: min(1, by_x[x]['freq'] * A['seats'] * A['lf_max'] / wanted[x]) if wanted[x] else 1 for x in by_x}
        expected_trans = [(x, y, km, count * min(factors[x], factors[y])) for x, y, km, count in target_trans]
        compare(expected_trans, trans, 'hub_transfer_flow:' + key)
        for x, L in by_x.items():
            near(L['local_carried'], target_local[x] * factors[x], 'hub_local_flow:' + key)
            near(L['carried_dir_week'], L['local_carried'] + sum(t for a, b, km, t in trans if x in (a, b)), 'hub_seat_conservation:' + key)
            near(L['migrated'], min(L['local_carried'], L['rw_now']), 'hub_migration:' + key)
        for x, y, km, t in trans:
            totals['tickets'] += 2 * t * price(A, km) * A['transfer_fare_factor']
            eligible_legs = int('MOW' not in (H, x)) + int('MOW' not in (H, y))
            totals['support'] += 2 * t * eligible_legs * A['subsidy_rub_per_pax'] * A['use_subsidy']
        transfer_trips = 2 * sum(t for x, y, km, t in trans)
    else:
        transfer_trips = 0
    totals['contribution'] = totals['tickets'] - totals['foregone'] + totals['support'] - totals['cost']
    if check:
        for field, val in [('block_hours_week', totals['hours']), ('variable_cost_rub_year', totals['cost'] * W),
                           ('ticket_before_migration_rub_year', totals['tickets'] * W), ('foregone_ticket_rub_year', totals['foregone'] * W),
                           ('ticket_after_migration_rub_year', (totals['tickets'] - totals['foregone']) * W),
                           ('support_rub_year', totals['support'] * W), ('contribution_rub_year', totals['contribution'] * W),
                           ('segments_year', totals['segments'] * W), ('transfer_journeys_year', transfer_trips * W),
                           ('journeys_year', (totals['segments'] - transfer_trips) * W)]:
            near(m[field], val, 'independent_ledger:' + key + '/' + field)
        assert m['model_city_pairs'] == len(pairs)
        assert m['model_8_12_pair_gate'] == (8 <= len(pairs) <= 12)
        assert m['pairs'] == ';'.join('-'.join(x) for x in sorted(pairs))
        assert m['block_hours_week'] <= (m['cap'] - A['spare_aircraft']) * A['block_h_per_day'] * 7 + 1e-7
        assert m['full_pnl_rub'] is None and m['cash_rub'] is None and not m['actual_fleet_acceptance']
        if any('MOW' in p for p in pairs):
            assert m['physical_airport_assignment'] == 'MOW_UNRESOLVED'
    return totals


def raw_score(A, legs):
    """Independent singleton frequency, raw tickets and signed contribution."""
    f = int(A['min_freq_week'])
    for _ in range(100):
        loads = [l['dem'] * share(A, l, f) for l in legs]
        nxt = int(min(A['direct_max_freq_week'], max(A['min_freq_week'], math.ceil(max(loads) / (A['seats'] * A['lf_max'])))))
        if nxt == f:
            break
        f = nxt
    hours = costs = tickets = foregone = support = 0.0
    for L in legs:
        p = min(L['dem'] * share(A, L, f), f * A['seats'] * A['lf_max'])
        h, c = cost(A, dict(L, freq=f), p)
        hours += 2 * f * h
        costs += c
        tickets += 2 * p * price(A, L['km'])
        mg = min(p, L['rw_now'])
        foregone += 2 * mg * price(A, L['km'])
        if 'MOW' not in (L['a'], L['b']):
            support += 2 * (p - mg) * A['subsidy_rub_per_pax'] * A['use_subsidy']
    return f, (tickets - costs) / hours, (tickets - foregone + support - costs) / hours


def reject(label, fn):
    try:
        fn()
    except AssertionError:
        return dict(probe=label, rejected=True)
    raise AssertionError('Undetected counterexample: ' + label)


def frontier_check(fronts, nets):
    groups = collections.defaultdict(list)
    for row in fronts:
        key = tuple(row[k] for k in ('calendar', 'scenario', 'network', 'policy'))
        cap = int(row['cap'])
        policy = 'GREEDY' if row['network'] != 'DIRECT' else row['policy'].removesuffix('_PRESERVE')
        eligible = []
        for n in nets.values():
            m = n['metrics']
            if (m['calendar'], m['scenario'], m['network'], m['policy']) != (*key[:3], policy) or m['cap'] > cap:
                continue
            gate = m['model_8_12_pair_gate'] if policy in ('GREEDY', 'SIGNED_CITY_PAIRS') else 8 <= m['program_count'] <= 12
            if gate:
                eligible.append(m)
        expected = max(eligible, key=lambda m: (m['contribution_rub_year'], -m['block_hours_week']))
        assert row['selected_id'] == expected['id'], (key, cap)
        for k in ('contribution_rub_year', 'block_hours_week', 'model_city_pairs'):
            near(float(row[k]), expected[k], 'frontier_selection:' + str(key))
        assert int(row['source_generated_cap']) == expected['cap'] <= cap
        groups[key].append(row)
    transitions = 0
    for key, rows in groups.items():
        rows.sort(key=lambda x: int(x['cap']))
        for a, b in zip(rows, rows[1:]):
            assert float(b['contribution_rub_year']) >= float(a['contribution_rub_year']) - 1e-6, key
            transitions += 1
    return dict(rows=len(fronts), groups=len(groups), monotonic_transitions=transitions)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner-replay', action='store_true')
    args = parser.parse_args()
    extract()
    # Before any execution, inspect only the requested exact snapshot.
    sys.path.insert(0, str(RUNTIME))
    global nm
    kernel = importlib.import_module('model_kernel')
    nm = kernel.nm
    d, scenarios = kernel.load()
    nets = json.loads((RUNTIME / 'runs/selection_v1/networks.json').read_text())
    fronts = list(csv.DictReader((RUNTIME / 'runs/selection_v1/preserved_frontiers.csv').open()))
    allrows = list(csv.DictReader((RUNTIME / 'runs/selection_v1/all_candidates.csv').open()))
    assert len(nets) == len(allrows) == 384 and len(fronts) == 303
    assert {r['id'] for r in allrows} == set(nets)
    for r in allrows:
        for k, v in nets[r['id']]['metrics'].items():
            expected = '' if v is None else str(v)
            assert r[k] == expected, (r['id'], k)
    published = list(csv.DictReader((RUNTIME / 'inputs/nastya_4a976/data/processed/network_summary.csv').open()))
    replay = []
    for scenario, A in scenarios.items():
        for H in ['OMS', 'KUF', 'UFA', 'REN', 'GOJ', 'DIRECT']:
            # Run the original full author selector, not the extracted owner wrapper.
            if H == 'DIRECT':
                result = nm.direct_network(d, A, A['demand_scen'], list(d.n.index))
                key = f'AUTHOR_52_48_CONCENTRATED/{scenario}/DIRECT/AUTHOR_SHORTLIST/cap10'
                hours, contribution, segments = sum(x[4] for x in result), sum(x[6] - x[5] for x in result), sum(x[7] for x in result)
            else:
                selected, result = nm.hub_network(H, d, A, A['demand_scen'], list(d.n.index))
                key = f'AUTHOR_52_48_CONCENTRATED/{scenario}/{H}/GREEDY/cap10'
                assert selected == nets[key]['chosen']
                hours, contribution, segments = result[2], result[4] - result[3], result[5] + 2 * result[6]
            compare(result, nets[key]['result'], 'original_author_replay:' + key)
            target = next(r for r in published if r['scenario'] == scenario and r['hub'] == ('' if H == 'DIRECT' else H))
            for field, value in [('result_mln_year', round(contribution * A['weeks_per_year'] / 1e6)), ('segments_year', round(segments * A['weeks_per_year'])), ('aircraft', math.ceil(hours / (A['block_h_per_day'] * 7)) + A['spare_aircraft'])]:
                assert value == float(target[field]), (scenario, H, field)
                replay.append(dict(scenario=scenario, network=H, field=field, actual=value, expected=float(target[field])))
        print('ORIGINAL_REPLAY', scenario, flush=True)
    assert len(replay) == 72
    write('independent_author_replay.json', replay)
    for key, n in nets.items():
        dd = d if n['metrics']['calendar'].startswith('AUTHOR') else kernel.ScaledDemand(d, 48 / 52)
        ledger(n, dd)
    exact = []
    for scenario, cap, expected in [('base', 10, -367061628.90116817), ('base', 4, -186479510.4910583), ('base_sub', 10, 387722372.7102387)]:
        A = dict(scenarios[scenario], fleet_cap=cap)
        selected, r = nm.hub_network('OMS', d, A, A['demand_scen'], list(d.n.index))
        actual = (r[4] - r[3]) * A['weeks_per_year']
        near(actual, expected, 'exact_OMS_fixture', tolerance=0.001)
        exact.append(dict(scenario=scenario, cap=cap, actual_rub=actual, expected_rub=expected))
    write('exact_oms_fixtures.json', exact)
    frontier = frontier_check(fronts, nets)
    shortlist = []
    changes = list(csv.DictReader((RUNTIME / 'runs/selection_v1/shortlist_changes.csv').open()))
    for calendar in ('AUTHOR_52_48_CONCENTRATED', 'LOST4_UNIFORM_NO_RECAPTURE'):
        for scenario, A in scenarios.items():
            if calendar.startswith('LOST') and not scenario.startswith('cautious'):
                continue
            dd = d if calendar.startswith('AUTHOR') else kernel.ScaledDemand(d, 48 / 52)
            tri, tri_eval, joint, totals = kernel.direct_context(dd, A, A['demand_scen'], list(d.n.index))
            sels, gross, net, evaluate, pair_set = kernel.direct_candidates(dd, A, A['demand_scen'])
            assert len(tri) == len(sels) == 1682
            ranks = []
            for i, (b, x, y, legs) in enumerate(tri):
                f, g, s = raw_score(A, legs)
                assert f == sels[i][3]
                near(g, gross[i], 'singleton_raw_score')
                near(s, net[i], 'singleton_signed_score')
                ranks.append(dict(candidate='-'.join((b, x, y)), raw=g, signed=s))
            old = set(sorted(range(len(tri)), key=lambda i: -ranks[i]['raw'])[:400])
            new = set(sorted(range(len(tri)), key=lambda i: -ranks[i]['signed'])[:400])
            expect_changes = {ranks[i]['candidate'] for i in old ^ new}
            reported = [r for r in changes if r['calendar'] == calendar and r['scenario'] == scenario]
            assert {r['candidate'] for r in reported} == expect_changes
            for r in reported:
                i = next(i for i, x in enumerate(ranks) if x['candidate'] == r['candidate'])
                assert (r['old_in'] == 'True') == (i in old)
                assert (r['new_in'] == 'True') == (i in new)
                near(float(r['gross_score']), ranks[i]['raw'], 'shortlist_row_raw')
                near(float(r['signed_score']), ranks[i]['signed'], 'shortlist_row_signed')
            if calendar.startswith('AUTHOR'):
                old_n = nets[f'{calendar}/{scenario}/DIRECT/AUTHOR_SHORTLIST/cap10']
                new_n = nets[f'{calendar}/{scenario}/DIRECT/SIGNED_SHORTLIST/cap10']
                assert old_n['chosen'] == new_n['chosen']
                near(old_n['metrics']['contribution_rub_year'], new_n['metrics']['contribution_rub_year'], 'shortlist_only_effect')
            shortlist.append(dict(calendar=calendar, scenario=scenario, universe=1682, replacements=len(old-new), changed_rows=len(reported)))
            if calendar.startswith('AUTHOR') and scenario == 'base':
                # Adversarial shared physical pair, with reversed endpoint labels.
                first = next(s for s in sels if all(L['km'] >= A['transfer_min_km'] for L in s[4]))
                second = (first[0], first[1], first[2], first[3], [dict(L, a=L['b'], b=L['a']) for L in first[4]])
                duplicate = joint([first, second])
                fake = dict(metrics=dict(nets['AUTHOR_52_48_CONCENTRATED/base/DIRECT/AUTHOR_SHORTLIST/cap10']['metrics']), assumptions=A, result=duplicate, chosen=[])
                fake['metrics']['id'] = 'counterexample/reversed_duplicate_triangle'
                ledger(fake, dd, check=False)
                pair_loads = {}
                for j, L in enumerate(first[4]):
                    actual = sum(t[8][j]['carried_dir_week'] for t in duplicate)
                    expected = min(L['dem'] * share(A, L, 2*first[3]), 2*first[3]*A['seats']*A['lf_max'])
                    near(actual, expected, 'reversed_endpoint_shared_pool')
                    pair_loads['-'.join(sorted((L['a'], L['b'])))] = dict(aggregate_direction_week=actual, market_direction_week=L['dem'], frequency_sum=2*first[3])
                write('reversed_pair_probe.json', pair_loads)
                # Capacity stress uses the actual joint function and realistic legs,
                # but makes demand huge to force the capacity bound to bind.
                stressed = (first[0], first[1], first[2], first[3], [dict(L, dem=1e9, competitive=False, rw_now=0) for L in first[4]])
                result = joint([stressed])[0]
                for L in result[8]:
                    near(L['carried_dir_week'], L['freq']*A['seats']*A['lf_max'], 'binding_capacity_probe')
                write('capacity_stress_probe.json', dict(freq=first[3], seats=A['seats'], lf=A['lf_max'], carried=[L['carried_dir_week'] for L in result[8]], expected_each=first[3]*A['seats']*A['lf_max']))
            print('SHORTLIST', calendar, scenario, flush=True)
    write('shortlist_independent.json', shortlist)
    probe_results = []
    base_key = 'AUTHOR_52_48_CONCENTRATED/base/OMS/GREEDY/cap10'
    small_key = 'AUTHOR_52_48_CONCENTRATED/base/OMS/GREEDY/cap4'
    assert nets[small_key]['metrics']['contribution_rub_year'] > nets[base_key]['metrics']['contribution_rub_year']
    changed = copy.deepcopy(fronts)
    for row in changed:
        if row['calendar'].startswith('AUTHOR') and row['scenario'] == 'base' and row['network'] == 'OMS' and row['cap'] == '10':
            for k in ('contribution_rub_year', 'block_hours_week', 'model_city_pairs'):
                row[k] = str(nets[base_key]['metrics'][k])
            row['selected_id'], row['source_generated_cap'] = base_key, '10'
    probe_results.append(reject('forget_prior_feasible_OMS_cap4_at_cap10', lambda: frontier_check(changed, nets)))
    for label in ('second_net_VAT_deduction', 'double_transfer_fare', 'segments_as_journeys'):
        mutant = copy.deepcopy(nets[small_key])
        if label == 'second_net_VAT_deduction':
            reduction = mutant['metrics']['ticket_after_migration_rub_year'] / 11
            mutant['metrics']['contribution_rub_year'] -= reduction
        elif label == 'double_transfer_fare':
            amount = sum(2*t*price(mutant['assumptions'], km)*mutant['assumptions']['transfer_fare_factor'] for a,b,km,t in mutant['result'][1]) * mutant['assumptions']['weeks_per_year']
            mutant['metrics']['contribution_rub_year'] += amount
        else:
            mutant['metrics']['journeys_year'] = mutant['metrics']['segments_year']
        probe_results.append(reject(label, lambda m=mutant: ledger(m, d)))
    # Uniform loss removes 4/52 demand, while the author convention concentrates it.
    A = scenarios['cautious']
    annual = d.get('OMS', 'GOJ', 'cautious')
    L = dict(km=d.km('OMS', 'GOJ'), competitive=False)
    q = share(A, L, 3)
    original = annual/(2*48)*q*2*48
    lost = (annual*48/52)/(2*48)*q*2*48
    reference_week = annual/(2*52)*q
    near(lost/(2*48), reference_week, 'LOST4_weekly_exposure')
    near(lost/original, 48/52, 'LOST4_no_rebooking')
    write('calendar_fixture.json', dict(pair='OMS-GOJ', annual_market_both_directions=annual, original_48_concentration_sold_year=original, lost4_no_recapture_sold_year=lost, difference=original-lost, operating_weeks=48, reference_weeks=52, actual_calendar_acceptance=False))
    key_results = []
    for calendar, scenario, network, policy in [('AUTHOR_52_48_CONCENTRATED','base','OMS','PRESERVE_FOUND_FEASIBLE'),('AUTHOR_52_48_CONCENTRATED','base_sub','OMS','PRESERVE_FOUND_FEASIBLE'),('AUTHOR_52_48_CONCENTRATED','base','DIRECT','SIGNED_SHORTLIST_PRESERVE'),('AUTHOR_52_48_CONCENTRATED','base','DIRECT','SIGNED_CITY_PAIRS_PRESERVE'),('AUTHOR_52_48_CONCENTRATED','base_sub','DIRECT','SIGNED_CITY_PAIRS_PRESERVE'),('AUTHOR_52_48_CONCENTRATED','cautious','OMS','PRESERVE_FOUND_FEASIBLE'),('LOST4_UNIFORM_NO_RECAPTURE','cautious','OMS','PRESERVE_FOUND_FEASIBLE')]:
        row = next(r for r in fronts if (r['calendar'],r['scenario'],r['network'],r['policy'],r['cap']) == (calendar,scenario,network,policy,'10'))
        key_results.append(dict(frontier=row, selected_metrics=nets[row['selected_id']]['metrics'], chosen=nets[row['selected_id']]['chosen']))
    write('key_results.json', key_results)
    write('counterexamples.json', probe_results)
    owner = dict(status='NOT_RUN_THIS_INVOCATION')
    if args.owner_replay:
        env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
        for script, argv in [('selection_experiment.py', []), ('verify_selection.py', []), ('package_manifest.py', ['--check'])]:
            with (EVIDENCE / (script + '.log')).open('w') as log:
                subprocess.run([sys.executable, '-B', str(RUNTIME/script), *argv], cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        owner = dict(status='PASS', full_replay_files_match_pinned_output_manifest=True, scripts=['selection_experiment.py','verify_selection.py','package_manifest.py --check'])
    write('summary.json', dict(subjectSHA=SUBJECT, status='PASS_INDEPENDENT_SCOPED', original_author_rounded_checks=len(replay), exact_oms_fixtures=len(exact), networks_independent_raw_flow_and_ledger=384, frontier=frontier, singleton_score_checks=len(shortlist)*1682, shortlist=shortlist, counterexamples=probe_results, check_counts=dict(CHECKS), owner=owner, not_run=['primary market verification','dated dispatch and physical MOW airport assignment','annual N(t)','new Sol packages','future support eligibility','full budget and cash','global optimum']))
    print('PASS_INDEPENDENT_SCOPED', len(replay), len(nets), len(fronts), flush=True)


if __name__ == '__main__':
    main()
