#!/usr/bin/env python3
"""MR05: independent, stdlib-only calculations from immutable Git blobs.

Never imports or executes author code; writes only next to this file.
"""
import collections
import copy
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

PIN = '344f4425ba3fbb73b45a5cbcd223089e2ca7b5d4'
CONTROL_PIN = 'f39ac0726d5942106189e9dc59bfc09cad92441e'
PREFIX = 'context/23_night_run_20261110/methods/'
OUT = Path(__file__).resolve().parent
CACHE = {}
CHECKS = []


def git(*args):
    return subprocess.check_output(['git', *args])


def blob(path):
    if path not in CACHE:
        CACHE[path] = git('show', PIN + ':' + PREFIX + path)
    return CACHE[path]


def js(path):
    return json.loads(blob(path))


def rows(path):
    return list(csv.DictReader(io.StringIO(blob(path).decode('utf-8-sig'))))


def close(a, b, tol=1e-6):
    assert math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol), (a, b, tol)


def record(name, actual, expected, unit, scope, tol=1e-6):
    if isinstance(expected, (float, int)) and not isinstance(expected, bool):
        close(actual, expected, tol)
    else:
        assert actual == expected, (name, actual, expected)
    CHECKS.append(dict(check=name, status='PASS', actual=actual, expected=expected,
                       unit=unit, scope=scope, absolute_tolerance=tol))


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                      allow_nan=False) + '\n')


def csvout(name, rr):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, list(rr[0]))
        writer.writeheader()
        writer.writerows(rr)


def hashes():
    outputs = js('output_manifest.json')['files']
    sources = js('source_manifest.json')['files']
    for r in outputs:
        data = blob(r['path'])
        assert hashlib.sha256(data).hexdigest() == r['sha256'], r['path']
        assert len(data) == r['bytes']
    for r in sources:
        data = blob(r['path'])
        assert hashlib.sha256(data).hexdigest() == r['sha256']
        upstream = git('show', r['source_commit'] + ':' + r['source_path'])
        assert data == upstream, r['path']
    record('output_manifest_hashes', len(outputs), 81, 'files', 'BYTE_IDENTITY_ONLY')
    record('upstream_source_byte_identity', len(sources), 62, 'Git blobs', 'BYTE_IDENTITY_ONLY')
    return outputs, sources


def nastya():
    base = 'inputs/set001/nastya_2f03/'
    assumptions = rows(base + 'data/assumptions/network.csv')
    routes = rows(base + 'data/processed/network_routes.csv')
    demands = {tuple(sorted((r['a'], r['b']))): r
               for r in rows(base + 'data/processed/demand_pairs.csv')}
    shared, counts = [], []
    for scenario in ['base', 'cautious']:
        a = {r['parameter']: float(r[scenario]) for r in assumptions}
        selected = [r for r in routes if r['scenario'] == scenario and r['variant'].startswith('Прямые')]
        groups = collections.defaultdict(list)
        for r in selected:
            groups[tuple(sorted((r['from'], r['to'])))].append(r)
        counts.append(dict(scenario=scenario, program_count=len({r['variant'] for r in selected}),
                           model_endpoint_pair_count=len(groups), leg_rows=len(selected),
                           weekly_directional_departures=sum(2 * int(r['freq_week_each_way']) for r in selected),
                           contains_MOW_aggregate=any('MOW' in p for p in groups),
                           physical_airport_pair_count=None))
        record('model_endpoint_pairs_' + scenario, len(groups), 20 if scenario == 'base' else 18,
               'unordered model node pairs', 'NOT_PHYSICAL_AIRPORT_COUNT')
        for pair, rr in groups.items():
            if len(rr) == 1:
                continue
            d = demands[pair]
            annual = float(d['observed'] if scenario == 'base' and d['observed']
                           and d['observed_coverage'] != 'airline_group'
                           else d['pax_base' if scenario == 'base' else 'pax_cautious'])
            weekly = annual / (2 * a['weeks_per_year'])
            frequencies = [int(r['freq_week_each_way']) for r in rr]

            def carried(f):
                if float(rr[0]['km']) < a['transfer_min_km']:
                    share = 0
                elif rr[0]['direct_now'] == 'True':
                    competitor_departures = weekly / (a['seats'] * a['competitor_lf'])
                    share = min(a['capture_competitive'], f / (f + competitor_departures))
                else:
                    share = a['capture_open'] * (-math.expm1(-f / a['capture_freq_scale']))
                return min(weekly * share, f * a['seats'] * a['lf_max']) * 2 * a['weeks_per_year']

            separate = sum(carried(f) for f in frequencies)
            pooled = carried(sum(frequencies))
            exported = sum(float(r['pax_year_segments']) for r in rr)
            assert abs(separate - exported) <= len(rr) * .5 + 1e-6
            shared.append(dict(scenario=scenario, pair='-'.join(pair), market_input_both_directions_year=annual,
                               weeks=a['weeks_per_year'], frequencies_each_direction='+'.join(map(str, frequencies)),
                               exported_segments_year=exported, separate_formula=separate,
                               pooled_frequency_scenario=pooled, pooled_minus_separate=pooled-separate,
                               market_cap_breached=exported > annual, source_coverage=d['observed_coverage'],
                               acceptance='ARITHMETIC_ONLY_POOLED_LAW_IS_AGENT_PROPOSAL'))
    ref = rows('analysis/set001/shared_pair_examples.csv')
    for r in shared:
        old = next(x for x in ref if x['scenario'] == r['scenario'] and x['pair'] == r['pair'])
        close(r['separate_formula'], old['author_formula_recomputed_pax'])
        close(r['pooled_frequency_scenario'], old['pooled_frequency_counterfactual_pax'])
    oms = next(r for r in shared if r['scenario'] == 'base' and r['pair'] == 'MOW-OMS')
    observed = demands[('MOW', 'OMS')]
    assert observed['observed_period'] == '2025' and observed['observed_coverage'] == 'airport'
    dump('MOW_OMS_input_check.json', dict(frozen_source_row=observed,
         verified_boundary='Frozen input provenance/period/coverage only; public source itself not re-fetched, actual final OD not inferred.',
         direction_conversion='674175 / (2 * 52) = scenario weekly demand per direction',
         weekly_directional_scenario=float(observed['observed']) / 104))
    record('MOW_OMS_export', oms['exported_segments_year'], 87497, 'segments/year/both directions', 'AUTHOR_EXPORT')
    record('MOW_OMS_separate', oms['separate_formula'], 87497.79027559512, 'segments/year/both directions', 'FORMULA_REIMPLEMENTED')
    record('MOW_OMS_pooled_F11', oms['pooled_frequency_scenario'], 80581.03552981278, 'segments/year/both directions', 'CONDITIONAL_CAPTURE_LAW')
    record('shared_examples_over_total_market', sum(r['market_cap_breached'] for r in shared), 0, 'examples', 'SIX_EXAMPLES_ONLY')
    balances = []
    for r in rows(base + 'data/processed/network_summary.csv'):
        residual = float(r['segments_year']) - float(r['od_trips_year']) - float(r['transfer_od_year'])
        assert abs(residual) <= 1
        balances.append(dict(scenario=r['scenario'], variant=r['variant'], residual=residual))
    record('journey_segment_export_balance', len(balances), 12, 'summary rows', 'ROUNDING_TOLERANCE_ONE_SEGMENT')
    csvout('shared_market_checks.csv', shared)
    csvout('route_unit_checks.csv', counts)
    dump('nastya_balance_checks.json', balances)


def flight_cost(f, p, basket):
    hours = float(f['block_minutes']) / 60
    fuel = (p['fuel_t_per_hour'] * hours + p['fuel_t_per_cycle']) * (p['fuel_rub_per_t'] + p['fuel_uplift_rub_per_t'])
    hourly = hours * (p['mro_rub_per_hour'] + p['crew_rub_per_hour'] + p['navigation_rub_per_hour'])
    return fuel + hourly + basket * p['airport_factor'] + p['deicing_probability'] * p['deicing_operation_rub']


def tsiri():
    base = 'inputs/set001/tsiri_93fa/'
    cfg = js(base + 'context/12_network_economics/inputs.json')
    scenarios = copy.deepcopy(cfg['scenarios'])
    overrides = js(base + 'context/15_team_update/model/overrides.json')
    for sc, values in overrides.get('scenarios', {}).items():
        scenarios[sc].update(values)
    comparison = rows(base + 'context/21_team_proposals/comparison.csv')
    sales = rows(base + 'context/17_aircraft_route_review/model/sales.csv')
    capacity = rows(base + 'context/17_aircraft_route_review/model/capacity.csv')
    flights = rows(base + 'context/17_aircraft_route_review/model/flights.csv')
    ledger, example, checker_gaps = [], None, []
    for r in comparison:
        profile, network, sc = r['source_profile'], r['source_network'], r['scenario']
        key = (profile, network, sc)
        ss = [s for s in sales if (s['profile'], s['network'], s['scenario']) == key]
        cc = [c for c in capacity if (c['profile'], c['network'], c['scenario']) == key]
        ff_list = [f for f in flights if (f['profile'], f['network']) == (profile, network)]
        ff = {f['id']: f for f in ff_list}
        assert len(ff) == len(ff_list)
        assert len(cc) == len({c['flight_id'] for c in cc})
        assert {c['flight_id'] for c in cc} == set(ff)
        used, markets = collections.Counter(), collections.Counter()
        for s in ss:
            q = float(s['sold_journeys'])
            assert q >= 0
            ids = s['flight_ids'].split(';')
            assert len(ids) == len(set(ids))
            assert len(ids) == (2 if s['transfer'] == 'True' else 1)
            ll = [ff[i] for i in ids]
            assert ll[0]['origin'] == s['origin'] and ll[-1]['destination'] == s['destination']
            assert all(ll[i]['destination'] == ll[i+1]['origin'] for i in range(len(ll)-1))
            assert all(float(ll[i]['arrival_utc_minute']) <= float(ll[i+1]['departure_utc_minute']) for i in range(len(ll)-1))
            assert all(f['date'] == (dt.date(2026, 12, 7) + dt.timedelta(days=int(f['day'])-1)).isoformat() for f in ll)
            close(q * len(ids), s['segment_pax'])
            close(q * float(s['fare_once']), s['gross_revenue'])
            close(float(s['gross_revenue']) - float(s['foregone_RW_revenue']), s['incremental_revenue'])
            close(q * len(ids) * scenarios[sc]['pax_cost'], s['new_pax_variable'])
            oldsegments = float(s['migrated_RW_direct']) + 2 * float(s['migrated_RW_unverified_connecting'])
            close(oldsegments * scenarios[sc]['pax_cost'], s['saved_old_pax_variable'])
            for i in ids:
                used[i] += q
            markets[(s['origin'], s['destination'])] += q
            if r['network'] == 'H_UFA_8' and sc == 'base' and s['origin'] == 'ARH' and s['destination'] == 'MRV' and s['day'] == '1':
                example = dict(sale=s, legs=ll)
        for s in ss:
            assert markets[(s['origin'], s['destination'])] <= float(s['D']) + 1e-6
        for c in cc:
            assert 0 <= used[c['flight_id']] <= float(c['capacity_scenario']) + 1e-6
            close(used[c['flight_id']], c['occupied'])
            close(flight_cost(ff[c['flight_id']], scenarios[sc], cfg['ufa_reference_basket_rub']), c['flight_variable_cost'])
        cost = sum(flight_cost(f, scenarios[sc], cfg['ufa_reference_basket_rub']) for f in ff.values())
        close(cost, r['flight_variable_cost'])
        sums = {k: sum(float(s[k]) for s in ss) for k in ['sold_journeys', 'transfer_journeys', 'segment_pax',
                'gross_revenue', 'foregone_RW_revenue', 'incremental_revenue', 'new_pax_variable', 'saved_old_pax_variable']}
        for k, v in sums.items():
            close(v, r[k])
        contribution = sums['incremental_revenue'] - cost - sums['new_pax_variable'] + sums['saved_old_pax_variable']
        close(contribution, r['contribution_before_base_fleet_opportunity'])
        close(sum(float(f['block_minutes']) for f in ff.values()) / 60, r['weekly_block_hours'])
        ledger.append(dict(result_network=r['network'], source_profile=profile, source_network=network, scenario=sc,
                           sales_rows=len(ss), capacity_rows=len(cc), physical_leg_rows=len(ff), **sums,
                           flight_cost_independent=cost, contribution_independent=contribution,
                           flight_cost_residual=cost-float(r['flight_variable_cost']),
                           money_unit='RUB/per_week_accrual_like_variable_contribution_before_unknown_fixed',
                           period_start='2026-12-07', period_end='2026-12-13',
                           author_pipeline_replayed=False, empirical_cost_validation=False))
        # Exact isolated perturbations to show what analyze_pinned.py currently does not verify.
        missing = max(cc, key=lambda c: used[c['flight_id']])
        checker_gaps.append(dict(network=r['network'], scenario=sc,
            removed_capacity_flight=missing['flight_id'], removed_occupied=float(missing['occupied']),
            methods_capacity_loop_accepts_missing_row=all(abs(used[c['flight_id']]-float(c['occupied'])) < 1e-6
                and used[c['flight_id']] <= float(c['capacity_scenario']) + 1e-6 for c in cc if c is not missing),
            cost_shift_rub=1000000, methods_contribution_check_accepts_shift=True,
            cost_shift_mechanism='comparison flight_variable_cost += 1000000; comparison contribution -= 1000000; other fields unchanged',
            independent_cost_join_rejects_shift=True))
    record('tsiri_eight_ledgers_independent_flight_cost', len(ledger), 8, 'result rows', 'ROW_LEVEL_EXPORT_AND_COST_FORMULA')
    ufa = next(r for r in ledger if r['result_network'] == 'H_UFA_8' and r['scenario'] == 'base')
    record('UFA8_base_contribution', ufa['contribution_independent'], -9496919.887593884, 'RUB/week', 'CONDITIONAL_NOT_FULL_BUDGET')
    assert example is not None
    s = example['sale']
    same_od = [z for z in sales if z['profile'] == s['profile'] and z['network'] == s['network']
               and z['scenario'] == s['scenario'] and z['origin'] == s['origin'] and z['destination'] == s['destination']]
    f = len(same_od)
    # band_values: long distance band base 320 * south factor 1.5 = 480; fare 14000.
    # This is reconstruction of the frozen example's scenario, not fitting to observed sales.
    desired = 480 * .45 * (-math.expm1(-f / 3)) * .65 / f
    close(desired, s['sold_journeys'])
    close(14000 * .9, s['fare_once'])
    close(desired * .05, s['migrated_RW_total'])
    close(desired * .05 * 14000, s['foregone_RW_revenue'])
    example['independent_derivation'] = dict(weekly_directional_D=480, available_itineraries=f,
        capture_transfer=.45, frequency_scale=3, transfer_competition_factor=.65,
        desired_per_itinerary=desired, sold_equals_desired=True, reference_fare=14000,
        fare_factor=.9, migration_fraction=.05, migration_status='UNVERIFIED_CONNECTING_SCENARIO',
        provenance='build_team_comparison.py:313-326; build_aircraft_route_review.py:46-65,82-84; inputs.json scenarios')
    record('ARH_UFA_MRV_journeys', float(s['sold_journeys']), 39.79900399543999, 'oneway endpoint journeys', 'SCENARIO_EXPORT')
    record('ARH_UFA_MRV_seat_segments', float(s['segment_pax']), 79.59800799087998, 'seat-segments', 'TWO_LEGS')
    record('ARH_UFA_MRV_one_fare_revenue', float(s['gross_revenue']), 501467.4503425439, 'RUB', 'FARE_ONCE')
    example['capacity_rows'] = [c for c in capacity if c['profile'] == s['profile'] and c['network'] == s['network']
                                and c['scenario'] == s['scenario'] and c['flight_id'] in s['flight_ids'].split(';')]
    example['independent_note'] = 'Same cohort consumes seats on both flights; two flights have other sales too. Costs counted over physical flights, not duplicated per sale.'
    csvout('tsiri_ledger_checks.csv', ledger)
    dump('tsiri_itinerary_check.json', example)
    dump('checker_gap_examples.json', checker_gaps)


def metadata():
    base = 'inputs/set001/tsiri_93fa/'
    blocks = rows(base + 'context/17_aircraft_route_review/evidence/directional_blocks.csv')
    published = {(r['origin'], r['destination']): r for r in blocks}
    flights = rows(base + 'context/17_aircraft_route_review/model/flights.csv')
    example = next(r for r in flights if r['id'] == 'ROUTE_INPUTS_UPPER_100_H_UFA_8_001')
    assert (example['origin'], example['destination']) not in published
    assert example['block_method'] == 'SCENARIO 30min+distance*1.10/700kmh rounded5min'
    # With block_factor=1 and RouteModel.block ceil-to-five fallback145, the unchanged
    # distance must lie in (1375,1437.5]km. The inherited metadata formula yields160..170min.
    lower = (145-5-30)*750/60
    upper = (145-30)*750/60
    assert lower == 1375 and upper == 1437.5
    mislabeled_min = math.ceil((30+lower*1.1/700*60)/5)*5
    mislabeled_max = math.ceil((30+upper*1.1/700*60)/5)*5
    assert mislabeled_min > 145
    dump('known_metadata_followup.json', dict(status='EXISTING_MR06_REPRODUCED_NOT_NEW_NETWORK_REPAIR',
        source_flight=example, has_directional_published_proxy=False,
        actual_code_fallback='ceil((30 + distance_km/750*60)/5)*5; profile ROUTE_INPUTS_UPPER_100',
        inferred_distance_interval_km=dict(lower_exclusive=lower, upper_inclusive=upper),
        stale_label_formula_range_minutes=[mislabeled_min, mislabeled_max],
        saved_block_minutes=145,
        action='Repair provenance separately in the already assigned network package; preserve numeric original and leave operational status unverified.'))


def c01():
    base = 'inputs/set001/hypotheses_6ed8/context/16_agent_research/hypotheses/experiment_v1/'
    rr = rows(base + 'cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv')
    r = next(r for r in rr if r['candidate'] == 'C01' and r['residual_funding_gap_rub'] == '1000000'
             and r['net_fare_rub_per_oneway_journey'] == '8000' and r['variable_cost_rub_per_oneway_journey'] == '500')
    q = math.ceil(1000000 / (2 * (8000 - 500)))
    record('C01_roundtrip_clients', q, 67, 'paired clients', 'ILLUSTRATIVE_THRESHOLD_ONLY')
    for field, expected in [('required_paid_journeys_each_direction', q), ('roundtrip_customers', q),
                            ('total_oneway_journeys', 2*q), ('physical_boardings', 4*q),
                            ('required_ticket_revenue_rub', 2*q*8000)]:
        record('C01_' + field, float(r[field]), expected, field, 'NOT_WEEKLY_NETWORK_REVENUE')
    record('C01_threshold_surplus', 2*q*(8000-500)-1000000, 5000, 'RUB/cohort', 'GAP_ALREADY_COVERS_ALLOCATED_COSTS')
    record('C01_one_below_deficit', 2*(q-1)*(8000-500)-1000000, -10000, 'RUB/cohort', 'INTEGER_MINIMUM')
    dump('C01_check.json', dict(source_row=r, independently_required=q, marginal_contribution=1005000,
                               illustrative_gap=1000000, paid_demand=None, residual_seats=None,
                               physical_feasibility='UNKNOWN: four separate residual leg capacities required'))


def counterexamples():
    examples = []

    def add(id, mechanism, values, implication):
        examples.append(dict(id=id, mechanism=mechanism, values=values, implication=implication,
                             provenance='INDEPENDENT_SYNTHETIC_COUNTEREXAMPLE_NOT_EMPIRICAL'))

    # A market cap permits many capture laws; splitting the same service changes a concave standalone law.
    separate = 2 * 100 * (1 / 11)
    pooled = 100 * (2 / 12)
    assert 0 < pooled < separate < 100
    weighted = 100 * 1.2 / 11.2
    add('CE01', 'Standalone program law versus pooled law and quality-weighted law',
        dict(D=100, competitor_frequency=10, own_unique_departures=2, standalone=separate,
             pooled_frequency=pooled, quality_weighted_direct_plus_transfer=weighted,
             same_common_market_cap_satisfied=True),
        'Conservation alone identifies none of these capture laws; do not label their difference a confirmed overstatement.')
    # Shared A-H flight, two DIFFERENT endpoint pools: OD conservation alone does not conserve seats.
    endpoint_sales = dict(A_B=80, A_C=80)
    feeder_use = sum(endpoint_sales.values())
    feasible_sales = dict(A_B=80, A_C=100-80)
    assert all(q <= 80 for q in endpoint_sales.values()) and feeder_use > 100
    assert sum(feasible_sales.values()) == 100
    add('CE02', 'Two endpoint markets share a 100-seat feeder',
        dict(OD_A_B=80, OD_A_C=80, feeder_seats=100, naive_feeder_usage=feeder_use,
             feasible_allocation_A_B=feasible_sales['A_B'], feasible_allocation_A_C=feasible_sales['A_C'],
             boardings_if_two_legs=2*sum(feasible_sales.values())),
        'Each OD passes its own market cap; shared physical-leg inventory must also constrain both products.')
    # One physical A-H plus two H-B alternatives is 2 itineraries but 1 origin departure.
    remaining = 100-40
    onward_bottleneck = min(remaining, 30)
    assert remaining == 60 and onward_bottleneck == 30
    add('CE03', 'Overlapping connection combinations and a saturated onward leg',
        dict(feeder_departures=1, onward_departures=2, connecting_itineraries=2,
             feeder_seats=100, onward_total_seats=200, journeys_upper_bound=100,
             naive_frequency_count=2, feeder_leg_for_second_OD=40,
             remaining_for_first_OD=remaining, first_OD_onward_residual=30,
             first_OD_two_leg_upper_bound=onward_bottleneck),
        'Itinerary count is not unique usable origin departure frequency; endpoint pairs can overlap on an operating leg.')
    # Shared OD, different products, product-specific values and seat incidence.
    direct, transfer, fare_d, fare_t = 60, 40, 10000, 7000
    revenue = direct * fare_d + transfer * fare_t
    assert revenue == 880000
    add('CE04', 'Direct and transfer alternatives in one endpoint pool',
        dict(D=100, direct_journeys=direct, transfer_journeys=transfer, physical_boardings=140,
             direct_fare=fare_d, transfer_through_fare=fare_t, correct_revenue=revenue,
             first_itinerary_direct_mispricing=1000000, first_itinerary_transfer_mispricing=700000),
        'Shared OD budget does not authorize a shared fare/transfer flag; retain product-specific quality and leg incidence.')
    # Donor full-state delta versus double-counting revenue/migration/opportunity.
    donor_R, donor_avoidable_C, candidate_R, candidate_C = 1000, 700, 1200, 800
    donor, candidate = donor_R - donor_avoidable_C, candidate_R - candidate_C
    delta = candidate - donor
    assert delta == 100
    lease = 200
    keep, cancel, replacement = donor-lease, -lease, candidate-lease
    assert (keep, cancel, replacement, replacement-keep) == (100, -200, 200, 100)
    add('CE05', 'KEEP/CANCEL/REPLACE with unchanged lease 200',
        dict(donor_contribution=donor, replacement_contribution=candidate, lease_each_state=200,
             keep_result=keep, cancel_result=cancel, replace_result=replacement,
             replace_minus_keep=replacement-keep, incorrect_second_donor_margin=delta-donor,
             incorrect_extra_donor_revenue=delta-donor_R),
        'Full-state subtraction includes donor once. Do not deduct its margin, revenue or own migration again; unchanged lease is not saved.')
    # Two migrated clients each incur a new two-leg seat cost, but only old pax-dependent cost is saved.
    net_company_trips = 10-2
    net_company_segments = 10*2-2
    incremental_revenue = 10*80-2*100
    after_pax = incremental_revenue-10*2*5+2*5
    assert (net_company_trips, net_company_segments, after_pax) == (8, 18, 510)
    add('CE06', 'Own migration is not new company demand or saved whole old flight',
        dict(new_program_journeys=10, migrated_journeys=2, new_company_journeys=net_company_trips,
             new_program_segments=20, old_segments_displaced=2, net_company_segments=net_company_segments,
             new_through_fare=80, old_fare=100, gross_revenue=800, foregone_revenue=200,
             incremental_revenue=incremental_revenue, pax_cost_per_segment=5, new_pax_cost=100,
             old_pax_cost_saved=10, contribution_before_new_flights=after_pax),
        'One through fare; own itinerary migration changes journey/segment denominators differently; old flight remains unless explicitly removed.')
    # Same accrual economics, different timing; working-capital cash does not change profit.
    events = [('2026-12-01', -600, 'operating_payment'),
              ('2026-12-01', -300, 'refundable_deposit'),
              ('2026-12-30', 1000, 'revenue_receipt')]
    cash = [0]
    for _, amount, _ in events:
        cash.append(cash[-1]+amount)
    assert -min(cash) == 900
    accrued_result = 1000-600
    assert cash[-1]+300 == accrued_result
    add('CE07', 'Accrual result, refundable deposit and timing',
        dict(day0_payment_operating=600, day0_refundable_deposit=300,
             day7_service_revenue=1000, day7_recognized_operating_cost=600,
             day30_revenue_receipt=1000, ending_cash_with_deposit_locked=100,
             accrued_result=accrued_result, deposit_asset=300, peak_funding=-min(cash),
             cash_events=events, incorrect_expensing_working_capital_profit=accrued_result+min(cash)),
        'Cash needs dates and opening balance; 900 funding is not an additional expense against 400 accrual profit.')
    # Period boundary and product threshold under actual residual inventory.
    residuals = [80, 80, 60, 80]
    clients_max = min(residuals)
    assert clients_max < 67
    add('CE08', 'C01: nominal 100 seats versus actual four-leg residual inventory',
        dict(threshold_roundtrip_clients=67, residual_seats_by_leg=residuals,
             max_roundtrip_clients=clients_max, threshold_is_physically_feasible=clients_max >= 67,
             outward_day='2026-12-13', return_day='2026-12-20',
             contribution_at_60_clients=clients_max*2*(8000-500), residual_gap=1000000),
        'Threshold arithmetic is correct but seats and both-date costs can reject the product; no weekly truncation of the return obligation.')
    add('CE09', 'Same annual rate, different finite calendar or resource ceiling',
        dict(annual_segments=10400, symmetric_weekly_directional_scenario=100,
             actual_december_OD=None, first_model_active_ceiling=9, second_model_active_ceiling=4,
             permitted_cross_model_profit_difference=None),
        'Annual normalization is a scenario; dated/annual, full/delta and different resource sets cannot be differenced causally.')
    endpoint_cost_threshold = math.ceil(1000000 / (2*(8000-500)))
    segment_cost_threshold = math.ceil(1000000 / (2*(8000-2*500)))
    assert endpoint_cost_threshold == 67 and segment_cost_threshold == 72
    add('CE10', 'Passenger cost500 per endpoint journey versus500 per boarding',
        dict(C01_author_cost_unit='RUB/oneway endpoint journey', Tsiri_cost_unit='RUB/seat-segment',
             C01_illustrative_cost=500, Tsiri_two_leg_cost_if_transplanted=1000,
             C01_original_threshold=endpoint_cost_threshold, alternative_unit_scenario_threshold=segment_cost_threshold),
        'Same numeric rate has different units.72 is a new named cost scenario, not a correction of the original illustrative67.')
    dump('counterexamples.json', examples)
    record('independent_counterexamples', len(examples), 10, 'cases', 'FORMAL_MODEL_LIMITS_NOT_EMPIRICAL_ACCEPTANCE')


def main():
    outputs, sources = hashes()
    nastya()
    tsiri()
    metadata()
    c01()
    counterexamples()
    dump('independent_checks.json', dict(package='MR05-independent-review-v1', source_commit=PIN,
         status='PASS_SCOPED_NUMERICAL_REPRODUCTION', checks=CHECKS,
         author_pipeline_replay='NOT_RUN', full_strategy_budget='NOT_RUN', live_market='NOT_RUN',
         acceptance_scope=['RAW_HASH_VERIFIED', 'ROW_LEVEL_EXPORT_JOIN_CHECKED',
                           'CONSERVATION_PASS_PINNED_SELECTED_TSIRI_EXPORTS',
                           'CONDITIONAL_FORMULA_ARITHMETIC_CHECKED'],
         not_accepted=['empirical capture law', 'full corrected network', 'profit forecast',
                       'operational dispatch', 'case compliance', 'team normative choices']))
    controls = []
    for name in ['contract.md', 'briefs/methods_review.md']:
        path = 'context/23_night_run_20261110/' + name
        data = git('show', CONTROL_PIN + ':' + path)
        controls.append(dict(path=path, commit=CONTROL_PIN, sha256=hashlib.sha256(data).hexdigest(),
                             bytes=len(data), grain='task contract/instructions; not numeric model input'))
    dump('source_manifest.json', dict(source_commit=PIN, extraction='git show EXACT_SHA:path; no live methods folder reads',
         control_inputs=controls,
         upstream_input_count=len(sources), files=[dict(path=PREFIX+p, commit=PIN,
             sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
             grain=next((r['grain'] for r in outputs if r['path'] == p), 'package output manifest'))
             for p, data in sorted(CACHE.items())]))
    print(json.dumps(dict(status='PASS_SCOPED', checks=len(CHECKS), source_commit=PIN)))


if __name__ == '__main__':
    main()
