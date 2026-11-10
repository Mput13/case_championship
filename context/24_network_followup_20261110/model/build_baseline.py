#!/usr/bin/env python3
"""Deterministic, offline fixed-network ledger replay and integration contract.

No upstream main(), optimizer, external research, or unfinished research files.
"""
import collections
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE.parent
REPO = OUT.parents[1]
METHODS = HERE / 'source_snapshot/methods'
CONTEXT = HERE / 'source_snapshot/context21/context'
RUN = METHODS / 'runs/common_demand_v1'
NAMES = ('D_SVX8', 'H_UFA_4', 'H_UFA_8')
SCENARIOS = ('base', 'cautious')
MONEY_RESULT = 'contribution_before_base_fleet_opportunity'
NUMERIC = ('sold_journeys', 'transfer_journeys', 'segment_pax', 'migrated_RW_total',
           'migrated_RW_direct', 'migrated_RW_unverified_connecting', 'gross_revenue',
           'foregone_RW_revenue', 'new_pax_variable', 'saved_old_pax_variable',
           'flight_variable_cost', 'incremental_revenue', MONEY_RESULT, 'load_factor',
           'net_new_RW_journeys_scenario')
LOCAL_SHA = '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
METHODS_SHA = 'a77e4cfbd14e560d26407479b7252cfcb15f4f41'
OWNER_SHA = '54cddfa6a9ac6c58bf8ed87eda9c3765edd674b6'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest()


def near(x, y, label, tolerance=1e-6):
    delta = abs(float(x) - float(y))
    assert math.isfinite(delta) and delta <= tolerance, (label, x, y, delta)
    return delta


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_inputs():
    m = load_module('common_demand', METHODS / 'common_demand.py')
    b = load_module('common_boundaries', METHODS / 'common_boundaries.py')
    return m, b, read_csv(CONTEXT / '21_team_proposals/comparison.csv'), \
        read_csv(CONTEXT / '17_aircraft_route_review/model/sales.csv'), \
        read_csv(CONTEXT / '17_aircraft_route_review/model/capacity.csv'), \
        read_csv(CONTEXT / '17_aircraft_route_review/model/flights.csv'), \
        json.loads((CONTEXT / '15_team_update/model/configuration.json').read_text())


def source_manifest():
    entries = []
    for e in json.loads((HERE / 'export_receipts.json').read_text()):
        path = REPO / e['local_path']
        index = 'owner' if e['source_commit'] == OWNER_SHA else 'methods'
        tree = json.loads((OUT / f'sources/{index}_tree_index.json').read_text())['tree']
        item = next(r for r in tree if r['path'] == e['source_path'])
        actual = git_blob(path.read_bytes())
        assert actual == item['sha'], ('MCP export blob mismatch', path, actual, item['sha'])
        entries.append(dict(**e, sha256=sha256(path), git_blob=actual, expected_git_blob=item['sha'],
                            bytes=path.stat().st_size, integrity='MATCH_SUPPLIED_EXACT_TREE_INDEX',
                            source_url=f"https://raw.githubusercontent.com/Mput13/case_championship/{e['source_commit']}/{e['source_path']}"))
    for path in sorted((HERE / 'source_snapshot/context21').rglob('*')):
        if not path.is_file():
            continue
        source_path = str(path.relative_to(HERE / 'source_snapshot/context21'))
        data = subprocess.check_output(['git', 'show', f'{LOCAL_SHA}:{source_path}'], cwd=REPO)
        assert path.read_bytes() == data
        entries.append(dict(source_commit=LOCAL_SHA, source_path=source_path,
                            local_path=str(path.relative_to(REPO)), access='local_git_show',
                            sha256=sha256(path), git_blob=git_blob(data), bytes=len(data),
                            integrity='BYTE_IDENTICAL_LOCAL_EXACT_GIT_OBJECT'))
    for path in sorted((OUT / 'baseline').rglob('*')):
        if not path.is_file():
            continue
        source_path = str(path.relative_to(OUT / 'baseline'))
        data = subprocess.check_output(['git', 'show', f'{LOCAL_SHA}:{source_path}'], cwd=REPO)
        assert path.read_bytes() == data, ('supplied baseline mismatch', path)
        entries.append(dict(source_commit=LOCAL_SHA, source_path=source_path,
                            local_path=str(path.relative_to(REPO)), access='supplied_baseline_verified_local_git_show',
                            sha256=sha256(path), git_blob=git_blob(data), bytes=len(data),
                            integrity='BYTE_IDENTICAL_LOCAL_EXACT_GIT_OBJECT'))
    for name in ['methods_handoff_compact.md', 'morning_report_README.md', 'morning_report_review.md', 'morning_report_data.json']:
        path = OUT / 'sources' / name
        entries.append(dict(local_path=str(path.relative_to(REPO)), sha256=sha256(path), bytes=path.stat().st_size,
                            access='supplied_local_handoff', integrity='HASHED_SUPPLIED_EXPORT',
                            scope='report transfer/review scope only; not new demand/source verification'))
    write_json(HERE / 'source_manifest.json', dict(
        methods_commit=METHODS_SHA, owner_commit=OWNER_SHA, context21_commit=LOCAL_SHA,
        entries=entries, errors=[],
        known_access_limit='latest night/methods Git objects absent after upstream TLS failure; not git-show verified; exact MCP exports verified by supplied tree blob hashes',
        exploratory_local_path_misses=[
            {'path': 'context/15_team_update/model/simulator.py', 'error': "fatal: path does not exist in '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'", 'effect': 'not needed; required replay functions imported from exact methods snapshot'},
            {'path': 'context/21_team_proposals/build.py', 'error': "fatal: path does not exist in '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'", 'effect': 'not needed; no original generator/optimizer replay claimed'}],
        external_research='NOT_PERFORMED_IN_THIS_IMPLEMENTATION_SCOPE'))
    return entries


def independent_ledger(detail, cc, totals, p, tag):
    used = collections.Counter()
    migration = collections.defaultdict(float)
    demand_by_market = {}
    for r in detail:
        legs = r['flight_ids'].split(';')
        sold = float(r['sold_journeys'])
        near(sold * len(legs), r['segment_pax'], (tag, 'segments'))
        near(sold * float(r['fare_once']), r['gross_revenue'], (tag, 'fare once'))
        near(float(r['migrated_RW_direct']) + float(r['migrated_RW_unverified_connecting']), r['migrated_RW_total'], (tag, 'migration parts'))
        near(float(r['segment_pax']) * p['pax_cost'], r['new_pax_variable'], (tag, 'new passenger costs'))
        near((float(r['migrated_RW_direct']) + 2 * float(r['migrated_RW_unverified_connecting'])) * p['pax_cost'], r['saved_old_pax_variable'], (tag, 'saved old segments'))
        for leg in legs:
            used[leg] += sold
        key = r['origin'], r['destination']
        migration[key] += sold
        if key in demand_by_market:
            near(demand_by_market[key], r['D'], (tag, 'one market D'))
        demand_by_market[key] = float(r['D'])
    for c in cc:
        assert -1e-8 <= used[c['flight_id']] <= float(c['capacity_scenario']) + 1e-8
    assert set(used) <= {r['flight_id'] for r in cc}
    assert all(sold <= demand_by_market[k] + 1e-8 for k, sold in migration.items())
    near(sum(used.values()), totals['segment_pax'], (tag, 'shared seat conservation'))
    near(totals['sold_journeys'] + totals['transfer_journeys'], totals['segment_pax'], (tag, 'journey/segment identity'))
    near(totals['sold_journeys'] - totals['migrated_RW_total'], totals['net_new_RW_journeys_scenario'], (tag, 'own RW deduction'))
    near(totals['gross_revenue'] - totals['foregone_RW_revenue'], totals['incremental_revenue'], (tag, 'incremental revenue'))
    near(totals['gross_revenue'] - totals['foregone_RW_revenue'] - totals['new_pax_variable'] + totals['saved_old_pax_variable'] - totals['flight_variable_cost'], totals[MONEY_RESULT], (tag, 'money identity'))


def main():
    manifest = source_manifest()
    m, b, comparisons, sales, capacity, flights, config = load_inputs()
    original_checks, common_checks, flight_checks, replay_rows, supply, frequencies = [], [], [], [], [], []
    demand_map = read_csv(RUN / 'demand_mapping.csv')
    ntable = {m.pair(r['a'], r['b']): r for r in read_csv(METHODS / 'inputs/nastya_2f03/demand_pairs.csv')}
    original_summary = read_csv(RUN / 'summary.csv')
    original_detail = read_csv(RUN / 'itinerary_at_unit_scale.csv')
    report = json.loads((OUT / 'sources/morning_report_data.json').read_text())
    report_rows = report['common_rows']
    assert len(report_rows) == 12 and len(report['inventory35']) == 35 and len(report['finite_networks']) == 15
    common_unit = [r for r in original_summary if float(r['multiplier']) == 1]
    assert len(common_unit) == 12
    contexts = {}
    worst = 0.0
    mapping_checks = 0
    for r in comparisons:
        n, sc = r['network'], r['scenario']
        key = r['source_profile'], r['source_network']
        ss = [x for x in sales if (x['profile'], x['network'], x['scenario']) == (*key, sc)]
        cc = [x for x in capacity if (x['profile'], x['network'], x['scenario']) == (*key, sc)]
        ff = [x for x in flights if (x['profile'], x['network']) == key]
        assert len({x['id'] for x in ff}) == len(ff) == len(cc) == len({x['flight_id'] for x in cc})
        assert {x['id'] for x in ff} == {x['flight_id'] for x in cc} == {i for x in ss for i in x['flight_ids'].split(';')}
        fmap = {x['id']: x for x in ff}
        p = config['scenarios'][sc]
        for c in cc:
            f = fmap[c['flight_id']]
            assert (c['origin'], c['destination']) == (f['origin'], f['destination'])
            near(c['block_minutes'], f['block_minutes'], 'flight block')
            cost = m.flight_cost(float(f['block_minutes']), p)
            near(cost, c['flight_variable_cost'], 'independent flight cost')
            flight_checks.append(dict(network=n, scenario=sc, flight_id=f['id'], formula_cost=cost,
                                      ledger_cost=c['flight_variable_cost'], delta=cost-float(c['flight_variable_cost'])))
        offers = m.prepare(ss, cc, sc, p)
        totals, detail, residual = m.simulate(offers, cc, p)
        independent_ledger(detail, cc, totals, p, (n, sc, 'original'))
        original = {x['flight_ids']: x for x in ss}
        assert len(original) == len(ss)
        for d in detail:
            for field in NUMERIC:
                if field in d and field in original[d['flight_ids']]:
                    worst = max(worst, near(d[field], original[d['flight_ids']][field], ('original detail', n, sc, field)))
        for field, value in totals.items():
            if field in r:
                worst = max(worst, near(value, r[field], ('original summary', n, sc, field)))
        for c in cc:
            near(float(c['capacity_scenario']) - residual[c['flight_id']], c['occupied'], 'original occupied')
        original_checks.append(dict(network=n, scenario=sc, itineraries=len(ss), flights=len(ff), status='PASS_FIXED_LEDGER_REPLAY'))
        if n not in NAMES:
            continue
        contexts[n, sc] = (offers, cc, p)
        mappings = [x for x in demand_map if (x['network'], x['scenario']) == (n, sc)]
        C, N = {}, {}
        for row in mappings:
            pair = tuple(row['pair'].split('-'))
            source = ntable[pair]
            field = 'observed' if sc == 'base' and source['observed'] and source['observed_coverage'] != 'airline_group' else 'pax_' + sc
            assert row['N_field'] == field and row['N_coverage'] == source['observed_coverage'] and row['N_period'] == source['observed_period']
            near(row['N_annual_proxy'], source[field], 'N source annual')
            near(float(source[field]) / 104, row['N_week_direction_stress'], 'N /104')
            cvalues = {float(o['D']) for o in offers if m.pair(o['origin'], o['destination']) == pair}
            assert len(cvalues) == 1
            near(cvalues.pop(), row['C_week_direction'], 'C source directed week')
            C[pair], N[pair] = float(row['C_week_direction']), float(row['N_week_direction_stress'])
            mapping_checks += 1
        assert set(C) == {m.pair(o['origin'], o['destination']) for o in offers}
        if sc == 'base':
            for f in ff:
                departure = int(f['departure_utc_minute'])
                arrival = int(f['arrival_utc_minute'])
                near(arrival - departure, f['block_minutes'], 'absolute UTC epoch block')
                assert f['date'] == ( __import__('datetime').date(2026, 12, 7) + __import__('datetime').timedelta(days=departure//1440)).isoformat()
                supply.append(dict(common_network=n, **f, aircraft_type='100-seat SSJ-class author scenario; actual tail/type dispatch UNKNOWN',
                                   epoch='2026-12-07T00:00:00Z; absolute minutes; do not add day again'))
            counts = collections.Counter((f['origin'], f['destination']) for f in ff)
            for (a, z), count in sorted(counts.items()):
                selected = [f for f in ff if (f['origin'], f['destination']) == (a, z)]
                frequencies.append(dict(network=n, origin=a, destination=z, departures_week=count,
                                        dates=';'.join(f['date'] for f in selected),
                                        flight_ids=';'.join(f['id'] for f in selected),
                                        status='MODEL_DATED_LEGS_NOT_PUBLISHED_OR_PERFORMED'))
        for recipe, demand in [('C', C), ('N', N)]:
            tag = n, sc, recipe
            calculated, det, caps = m.simulate(offers, cc, p, demand)
            independent_ledger(det, cc, calculated, p, tag)
            expected = next(x for x in common_unit if (x['network'], x['scenario'], x['recipe']) == tag)
            supplied = next(x for x in report_rows if (x['network'], x['scenario'], x['recipe']) == tag)
            for field in NUMERIC:
                worst = max(worst, near(calculated[field], expected[field], ('exact methods common', tag, field)))
                worst = max(worst, near(calculated[field], supplied[field], ('morning common', tag, field)))
            edetail = {x['flight_ids']: x for x in original_detail if (x['network'], x['scenario'], x['recipe']) == tag}
            assert len(edetail) == len(det)
            for d in det:
                for field in ['D', 'desired', 'fare_once'] + list(NUMERIC):
                    if field in d:
                        worst = max(worst, near(d[field], edetail[d['flight_ids']][field], ('exact common detail', tag, field)))
            row = dict(supplied)
            row.update(calculated)
            row.update(replay_scope='FIXED_LEDGER_ALLOCATION_MIGRATION_COST_ONLY',
                       verification='PASS_LOCAL_REPLAY_AND_EXACT_EXPORT_RECONCILIATION',
                       aircraft_type='100-seat author SSJ-class scenario; no physical fleet acceptance',
                       dated_legs=len(ff), seats_per_leg=100,
                       full_budget=None, full_pnl=None, peak_cash=None, launch_accepted=False)
            replay_rows.append(row)
            common_checks.append(dict(network=n, scenario=sc, recipe=recipe, itineraries=len(det), flights=len(ff), status='PASS'))
            contexts[n, sc, recipe] = (offers, cc, p, demand)
    assert len(original_checks) == 8 and sum(x['itineraries'] for x in original_checks) == 224
    assert len(common_checks) == 12 and mapping_checks == 72
    # Model supply/contract binding, including H_UFA_4's exact MRV (not another profile's GOJ).
    contract = json.loads((HERE / 'freeze/network_contract.json').read_text())
    for n in NAMES:
        ff = [f for f in supply if f['common_network'] == n]
        c = contract['networks'][n]
        assert len(ff) == c['dated_legs']
        assert len({f['aircraft'] for f in ff}) == c['model_working_aircraft']
        assert sorted({'-'.join(m.pair(f['origin'], f['destination'])) for f in ff}) == sorted(c['pairs'])
    write_csv(HERE / 'baseline_comparison.csv', replay_rows)
    write_csv(HERE / 'dated_legs.csv', supply)
    write_csv(HERE / 'frequencies.csv', frequencies)
    write_csv(HERE / 'baseline_replay_checks.csv', original_checks + common_checks)
    write_csv(HERE / 'flight_cost_checks.csv', flight_checks)
    # Full finite-rule demand curves, not a network search; compare all exported boundaries.
    curves, bounds, point_checks = {}, [], 0
    for n in NAMES:
        for sc in SCENARIOS:
            offers, cc, p, C = contexts[n, sc, 'C']
            N = contexts[n, sc, 'N'][3]
            caps = {r['flight_id']: float(r['capacity_scenario']) for r in cc}
            for recipe in ('C', 'N', 'C_TO_N_BLEND'):
                ds = C if recipe == 'C' else N
                demands = {k: (C[k], N[k] - C[k]) if recipe == 'C_TO_N_BLEND' else (0, ds[k]) for k in C}
                end = 1 if recipe == 'C_TO_N_BLEND' else max(caps[o['legs'][0]] / (ds[m.pair(o['origin'], o['destination'])] * o['coefficient']) for o in offers if not o['transfer'])
                pieces, checked = b.trace(offers, cc, p, demands, end)
                point_checks += checked
                curves[n, sc, recipe] = pieces
                roots = []
                for piece in pieces:
                    slope = piece['contribution_slope']
                    if abs(slope) > 1e-10:
                        root = -piece['contribution_intercept'] / slope
                        if piece['left'] - 1e-9 <= root <= piece['right'] + 1e-9:
                            roots.append(root)
                extrema = [(b.at(pieces, x), x) for x in {p['left'] for p in pieces} | {end}]
                maximum, at_maximum = max(extrema)
                exported = next(r for r in read_csv(RUN / 'exact_demand_boundaries.csv') if (r['network'], r['scenario'], r['recipe']) == (n, sc, recipe))
                near(maximum, exported['maximum_contribution'], 'boundary maximum', 1e-5)
                near(end, exported['domain_end'], 'boundary domain')
                assert len(pieces) == int(exported['region_count'])
                exported_roots = [float(x) for x in exported['zero_crossings'].split(';') if x]
                assert len(roots) == len(exported_roots)
                for x, y in zip(roots, exported_roots):
                    near(x, y, 'boundary zero', 1e-8)
                if recipe != 'C_TO_N_BLEND':
                    tail, _, _ = m.simulate(offers, cc, p, ds, end * 2)
                    near(tail[MONEY_RESULT], b.at(pieces, end), 'local saturation tail', 1e-5)
                    near(tail['transfer_journeys'], 0, 'local saturation transfer tail')
                bounds.append(dict(network=n, scenario=sc, recipe=recipe, domain_end=end,
                                   regions=len(pieces), zero_crossings=';'.join(format(x, '.12g') for x in roots),
                                   maximum_contribution_RUB_week=maximum, maximum_at=at_maximum,
                                   scope='FIXED_LOCAL_FIRST_OFFERS_FARES_MIGRATION_COST_NO_FULL_BUDGET'))
    d, h = curves['D_SVX8', 'base', 'C_TO_N_BLEND'], curves['H_UFA_4', 'base', 'C_TO_N_BLEND']
    cuts = sorted({0., 1.} | {r['right'] for r in d + h})
    alpha_roots = []
    for l, r in zip(cuts, cuts[1:]):
        dl, dr = b.at(d, l) - b.at(h, l), b.at(d, r) - b.at(h, r)
        if dl * dr < 0:
            alpha_roots.append(l - dl * (r-l) / (dr-dl))
    assert len(alpha_roots) == 1
    alpha = alpha_roots[0]
    upstream = read_csv(RUN / 'recipe_rank_boundaries.csv')[0]
    near(alpha, upstream['alpha'], 'exact alpha', 1e-10)
    near(b.at(d, alpha), upstream['contribution_a'], 'alpha contribution', 1e-5)
    assert b.at(d, alpha) < 0 and b.at(h, alpha) < 0
    scale = next(-piece['contribution_intercept'] / piece['contribution_slope'] for piece in curves['H_UFA_4', 'base', 'C'] if abs(piece['contribution_slope']) > 1e-10 and piece['left'] <= -piece['contribution_intercept'] / piece['contribution_slope'] <= piece['right'])
    threshold_total, _, _ = m.simulate(*contexts['H_UFA_4', 'base', 'C'][:3], contexts['H_UFA_4', 'base', 'C'][3], multiplier=scale)
    near(threshold_total[MONEY_RESULT], 0, 'H_UFA4 C base zero', 1e-4)
    scenarios = [
        dict(threshold_id='T01', network='D_SVX8 vs H_UFA_4', scenario='base', parameter='alpha',
             value=alpha, unit='dimensionless C_to_N_market_demand_interpolation',
             contribution_a_RUB_week=b.at(d, alpha), contribution_b_RUB_week=b.at(h, alpha),
             condition='D_pair(alpha)=(1-alpha)*C_pair+alpha*N_pair, alpha in [0,1]; same dated offers, local-first ordering, through fares, migration/caps and costs; no fixed/base/external donor differences',
             meaning='relative contribution tie; both negative; not empirical share/probability; not transferable to LP or a different allocator'),
        dict(threshold_id='T02', network='H_UFA_4', scenario='base', parameter='common_C_demand_multiplier',
             value=scale, unit='dimensionless scale applied to every fixed C directed endpoint D',
             contribution_a_RUB_week=threshold_total[MONEY_RESULT], contribution_b_RUB_week='',
             condition='same local-first dated supply/100-seat caps/net fares/capture/migration/cost; all C endpoint markets scaled together; no excluded costs included',
             meaning='zero contribution before fleet/base/support/start/exit/opportunity; not break-even full PnL or forecast; excluded positive costs raise the required scale')]
    write_csv(HERE / 'scenario_thresholds.csv', scenarios)
    write_csv(HERE / 'fixed_rule_bounds.csv', bounds)
    # Static current-owner audit, without imports, optimizers or annual-to-weekly substitution.
    owner_summary = read_csv(OUT / 'owner_snapshot/data/processed/network_summary.csv')
    assumptions = {r['parameter']: r for r in read_csv(OUT / 'owner_snapshot/data/assumptions/network.csv')}
    owner_checks = []
    for r in owner_summary:
        sc = r['scenario']
        seg, od, trans = (int(r[k]) for k in ('segments_year', 'od_trips_year', 'transfer_od_year'))
        residual = seg - od - trans
        assert abs(residual) <= 1 and float(r['check_segments_minus_od']) == 0
        money_residual = int(r['revenue_mln_year']) - int(r['var_cost_mln_year']) - int(r['result_mln_year'])
        assert abs(money_residual) <= 1  # independent whole-million rounding, not exact unrounded money
        assert int(r['result_mln_year']) < 0
        owner_checks.append(dict(scenario=sc, variant=r['variant'], model_weeks=assumptions['weeks_per_year'][sc],
                                 annual_segment_identity_rounding_residual=residual,
                                 annual_money_rounding_residual_mln=money_residual,
                                 result_mln_year=r['result_mln_year'],
                                 audit='STATIC_EXPORT_SCHEMA_AND_ROUNDING_IDENTITIES_ONLY',
                                 replay='NOT_RUN_OWNER_OPTIMIZER', common_weekly_input='NO'))
    write_csv(HERE / 'owner_snapshot_checks.csv', owner_checks)
    protected = json.loads((OUT / 'protected_city_stage.json').read_text())
    protected_checks = {path: dict(expected=h, actual=sha256(REPO / path), match=sha256(REPO / path) == h) for path, h in protected.items()}
    assert all(r['match'] for r in protected_checks.values())
    assert subprocess.check_output(['git', 'branch', '--show-current'], cwd=REPO, text=True).strip() == 'research/network-evidence-followup-20261110'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip() == '6ec84a7d2a6eb50b547a61df82fc5a424f48f146'
    contract.update(aircraft_type='100-seat SSJ-class author scenario; aircraft registration/dispatch limits UNKNOWN',
                    supply_ledger='dated_legs.csv', frequencies_ledger='frequencies.csv', supply_sha256=sha256(HERE / 'dated_legs.csv'),
                    snapshot_manifest='source_manifest.json', threshold_scope='FIXED_LOCAL_FIRST_ONLY',
                    integration_contract='integration_contract.json')
    # Preserve the initial freeze contract; derived bindings are a separate deliverable.
    write_json(HERE / 'network_contract.json', contract)
    validation = dict(status='PASS_SCOPED_BASELINE_ONLY', research_integration='NOT_RUN_PENDING_ONE_FINAL_EXPLICIT_ROUND',
                      full_replay=False, fixed_ledger_replay=True,
                      replay_scope='8 original context21 summary cases/224 itineraries, then 12 common C/N unit-scale cases; not source-demand validation, original network generation, operating feasibility or full PnL',
                      source_original_cases=len(original_checks), source_original_itineraries=sum(x['itineraries'] for x in original_checks),
                      common_unit_cases=len(common_checks), common_unit_itineraries=sum(x['itineraries'] for x in common_checks),
                      demand_mapping_rows=mapping_checks, independently_recomputed_flight_cost_rows=len(flight_checks),
                      maximum_arithmetic_delta=worst, absolute_tolerance_RUB=1e-6,
                      common_all_contributions_negative=all(float(r[MONEY_RESULT]) < 0 for r in replay_rows),
                      common_dated_legs=len(supply), fixed_rule_curve_count=len(bounds),
                      piecewise_numeric_point_checks=point_checks,
                      owner_snapshot_files=5, owner_static_export_rows=len(owner_checks), owner_optimizer='NOT_RUN',
                      protected_city_stage=protected_checks, protected_all_match=True,
                      baseline_source_manifest_entries=len(manifest),
                      source_blob_match=True, random_seed='NOT_USED_DETERMINISTIC',
                      unknowns_are_null=True, full_PnL=None, peak_cash=None, operating_acceptance=False)
    write_json(HERE / 'validation.json', validation)
    write_audit(validation, scenarios, owner_checks)
    print(json.dumps({k: validation[k] for k in ['status', 'source_original_cases', 'source_original_itineraries', 'common_unit_cases', 'common_unit_itineraries', 'maximum_arithmetic_delta', 'protected_all_match']}, ensure_ascii=False))


def write_audit(validation, thresholds, owner_checks):
    alpha, scale = thresholds
    negative = sum(int(x['result_mln_year']) < 0 for x in owner_checks)
    text = f'''# Проверка фиксированного baseline

Статус **BASELINE_ONLY / PASS_SCOPED**. Research-файлы этого прохода не интегрированы и их готовность не опрашивалась. Следующий раунд — единственная адресная интеграция по `integration_contract.json` и `integrate_once.py`. Все выводы относятся к трём зафиксированным сетям, а не к оптимальному выбору маршрутов или городской оценке.

## Что воспроизведено

Exact methods `{METHODS_SHA}` получен через `mcp__codex_apps__github_fetch`, не через отсутствующий локальный Git object. Все MCP bytes совпали с Git blob SHA из переданных exact tree indexes; SHA-256 и пути в `source_manifest.json`. Старые ledger inputs выгружены `git show {LOCAL_SHA}:<path>` без checkout. Импортированы только чистые функции methods; upstream `main`, генераторы сети, ranking и owner optimizer не запускались.

Повторены 8 исходных context21 итогов и 224 маршрута продажи с миграцией; затем 12 C/N × base/cautious строк на одинаковых D_SVX8/H_UFA_4/H_UFA_8. Сверены точные summary, itinerary и 12 строк morning report; максимальное расхождение {validation['maximum_arithmetic_delta']:.12g}. Проверены 72 C/N mapping rows против exact старой матрицы N и weekly C, формула затрат каждого используемого leg, места на общих плечах, D-cap, один through fare и вычитание own-RW migration. Это **fixed-ledger replay**, не полное воспроизведение генерации сети, проверка действительного спроса/нетто-доходности/эксплуатации или полного бюджета. Ночной Git object не объявляется доступным.

`baseline_comparison.csv` сохраняет все исходные денежные статьи и метаданные. Все 12 вкладов отрицательны до fleet/base/opportunity. Контрольные base суммы совпали с supplied exact rows (не с округлёнными prose числами).

## Supply и единицы

`dated_legs.csv` и `frequencies.csv` фиксируют все 64 dated legs: D_SVX8 — 16 legs/1 модельный рабочий борт, H_UFA_4 — 16/2, H_UFA_8 — 32/4, условный резерв 1 на вариант. Тип — авторский 100-кресельный SSJ-class сценарий; реальные регистрационные борта, payload/range/crew/MRO и парк UNKNOWN. D_SVX8 летит 7–12 декабря; две UFA программы сжаты на 7–8 декабря внутри целевой недели 7–13 декабря 2026. Это не равномерная частота и не утверждение опубликованного/исполненного расписания. UTC-minute уже абсолютный от 07.12 00:00Z: второй раз day не прибавляется. H_UFA_4 выбран из ROUTE_INPUTS_UPPER_100 с MRV, а не из другого profile с GOJ. Никаких новых сетей не подбиралось.

C — недельный endpoint-сценарий Цири. N — годовой scale proxy exact 2f03, делённый на 104 = 2 направления × 52 недели **в обоих** общих сценариях. Поля N/period/coverage сохраняются в exact mapping; airport flow, airline group lower bound и модельные route segments не становятся наблюдённым winter endpoint OD. Из нового owner OD module входы не заимствуются. Розничное предложение — не net yield; опубликованные рейсы/кресла — offer, не paid demand. Airport total, route segments, endpoint journeys и transfer journeys — разные единицы. Для этих одно-/двухплечевых продуктов `segment_pax = sold_journeys + transfer_journeys`; прирост RW поездок — sold минус own-RW migration. Through fare начислен один раз, кресло занято на каждом плече.

Тариф `CIRI_NET_SCENARIO_FARE`; налоговая база `EX_RECOVERABLE_VAT_AS_AUTHOR_SCENARIO` — авторский сценарий, не доказательство применимости вычета или achieved yield. У базового керосина Цири 136300 + 1696 RUB/t; у текущего owner 134896 уже объединены в одном параметре. Их нельзя смешивать или добавлять uplift дважды. Корзина handling и deicing учтены один раз на каждый flown leg. Новые затраты меняются симметрично на всех flown legs с отдельным admission периода/единиц/налогов; субсидия требует собственной applicable scope и не включена автоматически.

## Два адресных порога

1. **α = {alpha['value']:.12f}**: D_pair(α)=(1−α)C_pair+αN_pair для **каждого endpoint-рынка** при base и неизменных supply, тарифах, capture, migration/caps, local-first + исходной внутригрупповой сортировке. Это равенство contribution D_SVX8 и H_UFA_4: {alpha['contribution_a_RUB_week']/1e6:.9f} млн RUB/нед. у обоих. При меньшем α меньше теряет UFA4, при большем D_SVX8; это не прибыль, вероятность, оценённая сезонность или доля пересадок. Fixed/base/external donor различия отсутствуют из объекта порога; при их изменении равенство меняется. На LP, иной allocator/offer universe и cautious порог не переносится.

2. **C/base H_UFA_4: общий множитель спроса {scale['value']:.10f}** даёт нулевой author contribution при исходных seats/fare/capture/local-first/migration/затратах. Это одновременное масштабирование всех C endpoint D, не рост «пассажиров аэропорта» и не утверждение, что рынок выдержит цены. Положительные исключённые расходы повышают порог полного PnL; фактические F/B неизвестны. В `fixed_rule_bounds.csv` проверены все исходные конечные curves, но они не расширяют universe и не являются глобальными network bounds. В cautious даже максимумы этих трёх fixed local-first программ отрицательны; рост только D не закрывает вклад в этом объекте, не запрещая иных продуктов/цен/сетей.

Exact piecewise curves проверены в {validation['piecewise_numeric_point_checks']} точках, включая границы и середины интервалов; за saturation дополнительно сверено постоянное хвостовое значение. Числа получены кодом, без подгонки к положительному результату.

## Текущий owner: отдельный контур

Пять exact файлов `{OWNER_SHA}` сохранены в `../owner_snapshot/`, blob-хеши сверены. Owner не запускался. В assumptions явно 52 base и 48 cautious модельных недель; {negative} из 12 annual summary вкладов отрицательны. `owner_snapshot_checks.csv` проверяет только экспортированные годовые segment/OD/transfer и money тождества с допуском округления (до одного пассажира/миллиона RUB), а не подтверждает генерацию/весь owner набор. Годовые суммы и другой состав нельзя подставить вместо недельных common C/N. Owner fleet cap 10 и более частые сети также не подменяют common ceiling 4 и dated legs. Отрицательные условные OMS/REN не назначают реальные донорские борта.

## Admission и оставшиеся gates

`input_admission.csv` описывает текущие model inputs и разрешённые способы изменения. `input_admission_template.csv` — по одной строке на **каждую** находку трёх research agents, с отдельными source, source period, unit, tax basis, reliability, pair/flight и admission: direct_input / proxy / scenario_only / rejected_missing_scope. Наличие доказательства предложения или общей годовой статистики не даёт direct_input paid winter OD. Immutable source bytes должны быть привязаны SHA-256. Незавершённые результаты не импортируются.

C01 NJC>UFA>MRV: нужны конкретные protected product, MCT/turn, исходная dated rotation и цена изменения местных продаж. Это отдельный gate, не автоматически H_UFA_4. C07 SVX>OMS>KJA>OMS>SVX: next assignment, датированная цепочка, эксплуатация/спрос — отдельный gate; не принятая программа. Closed OD, contracts, free aircraft, achieved net yield остаются UNKNOWN.

Полный incremental budget: `contribution + external_donor_delta − incremental_F − incremental_B − support − start_recognized − exit_recognized − other_excluded`. Никакая неизвестная статья не превращена в ноль. Legacy own-RW foregone revenue уже внутри contribution: не вычитать повторно и не добавлять fictitious cancelled-flight savings. Реальные donor KEEP/CANCEL/REPLACE требуют именованных обязательств; full PnL/peak cash NULL. Cash — отдельные dated gross receipts/payments, депозиты, capex/финансирование. Условное нулевое исключение используется только в математическом объекте порога, не как установленный бюджет.

Список пробелов — `gap_map.csv`; передача owner — `owner_handoff.csv`. Фактические параметры owner не изменены. Scope финального адаптера ограничен фиксированными сетями, недельным endpoint D, net fare once, разделёнными fuel/uplift/hourly costs и passenger cost; все unsupported changes отклоняются, review round не расширяет обзор.

## Воспроизведение и целостность

Из корня реальной копии: `python3 context/24_network_followup_20261110/model/build_baseline.py`. Сеть не требуется. Собственный код только в `OUT/model/*.py`; historical code snapshots — evidence, не изменённые original scripts. Все {len(validation['protected_city_stage'])} protected_city_stage хешей совпали, HEAD/base и ветка проверены. Commit/push, checkout/reset/worktree, правки stage1/ranking/weights/dashboard/src и сообщения другим не выполнялись.
'''
    (HERE / 'model_audit.md').write_text(text)


if __name__ == '__main__':
    main()
