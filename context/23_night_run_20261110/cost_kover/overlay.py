#!/usr/bin/env python3
"""Small, offline, deterministic MR02 overlay. Python standard library only.

Does not select networks, fit probabilities, replay the author's full main,
or replace the methods budget/threshold module. Every result is conditional.
"""
import ast
import collections
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / 'inputs'
TOL = 1e-6
COMPONENTS = ('fuel_product', 'fuel_uplift', 'mro', 'crew', 'navigation', 'airport_turn', 'deicing')


def readcsv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def writecsv(path, rows, fields=None):
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def writejson(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def close(a, b, context=''):
    if not math.isclose(float(a), float(b), abs_tol=TOL, rel_tol=1e-12):
        raise AssertionError((context, a, b))


def parameters(scenario):
    old = json.loads((INPUTS / 'tsiri_inputs.json').read_text())
    overrides = json.loads((INPUTS / 'tsiri_overrides.json').read_text())
    p = dict(old['scenarios'][scenario])
    p.update(overrides.get('scenarios', {}).get(scenario, {}))
    return p, old['ufa_reference_basket_rub']


def component_costs(leg, p, basket):
    h = float(leg['block_minutes']) / 60
    fuel = h * p['fuel_t_per_hour'] + p['fuel_t_per_cycle']
    return dict(fuel_product=fuel * p['fuel_rub_per_t'],
                fuel_uplift=fuel * p['fuel_uplift_rub_per_t'],
                mro=h * p['mro_rub_per_hour'], crew=h * p['crew_rub_per_hour'],
                navigation=h * p['navigation_rub_per_hour'],
                airport_turn=basket * p['airport_factor'],
                deicing=p['deicing_probability'] * p['deicing_operation_rub'])


def instant(leg, event):
    return datetime.fromisoformat(leg['date']).replace(tzinfo=timezone.utc) + timedelta(minutes=float(leg[event + '_utc_minute']))


def hits(leg, episode):
    start, end = (datetime.fromisoformat(episode[k]) for k in ['start_utc', 'end_utc_exclusive'])
    if end < start:
        raise ValueError('negative restriction interval')
    return ((leg['origin'] == episode['airport'] and start <= instant(leg, 'departure') < end)
            or (leg['destination'] == episode['airport'] and start <= instant(leg, 'arrival') < end))


def lost_journeys(sales, cancelled):
    """One boolean per itinerary, irrespective of how many of its legs fail."""
    return [r for r in sales if cancelled.intersection(r['flight_ids'].split(';'))]


def validate_capacity(sales, legs, capacity):
    used = collections.Counter()
    ids = {r['id'] for r in legs}
    if len(ids) != len(legs):
        raise ValueError('duplicate physical leg id')
    for r in sales:
        q = float(r['sold_journeys'])
        if q < -TOL:
            raise ValueError('negative journey allocation')
        linked = r['flight_ids'].split(';')
        if len(linked) != len(set(linked)) or not set(linked) <= ids:
            raise ValueError('unknown or repeated physical leg in itinerary')
        for leg_id in linked:
            used[leg_id] += q
    for leg_id in ids:
        cap = float(capacity[leg_id])
        if cap < 0 or used[leg_id] > cap + TOL:
            raise ValueError(('shared seat capacity exceeded', leg_id, used[leg_id], cap))
    return used


def template_rotation(legs, reference=None):
    """Check only author's planning labels, never infer an actual tail cascade."""
    by_tail = collections.defaultdict(list)
    issues = []
    for r in legs:
        by_tail[r['aircraft']].append(r)
    if reference is not None:
        original = collections.defaultdict(list)
        for r in reference:
            original[r['aircraft']].append(r)
        for label, seq in original.items():
            seq.sort(key=lambda r: instant(r, 'departure'))
            kept = sorted(by_tail[label], key=lambda r: instant(r, 'departure'))
            initial, final = seq[0]['origin'], seq[-1]['destination']
            if kept and (kept[0]['origin'] != initial or kept[-1]['destination'] != final):
                issues.append(dict(planning_label=label, issue='changed initial or final position',
                                   expected_initial=initial, expected_final=final))
            elif not kept and initial != final:
                issues.append(dict(planning_label=label, issue='cancelled required positioning',
                                   expected_initial=initial, expected_final=final))
    for label, seq in by_tail.items():
        seq.sort(key=lambda r: instant(r, 'departure'))
        for left, right in zip(seq, seq[1:]):
            if left['destination'] != right['origin'] or instant(right, 'departure') < instant(left, 'arrival') + timedelta(minutes=45):
                issues.append(dict(planning_label=label, left=left['id'], right=right['id']))
    return issues


def bounded_author_cost_replay(legs, caps, scenario):
    """Execute only two pinned flight_cost function bodies, not author main."""
    bodies = []
    for file, cls in [('tsiri_core_model.py', 'Model'), ('tsiri_route_model.py', 'RouteModel')]:
        tree = ast.parse((INPUTS / file).read_text())
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
        fn = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == 'flight_cost')
        ns = {} if not bodies else {'core': SimpleNamespace(Model=SimpleNamespace(flight_cost=bodies[0]))}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(INPUTS / file), 'exec'), ns)
        bodies.append(ns['flight_cost'])
    p, basket = parameters(scenario)
    obj = SimpleNamespace(scenarios={scenario: p}, old={'ufa_reference_basket_rub': basket}, profile='ROUTE_INPUTS_UPPER_100')
    max_delta = 0
    for r in legs:
        minimal = {**r, 'block_minutes': float(r['block_minutes'])}
        value = bodies[1](obj, minimal, scenario)
        target = float(caps[r['id']]['flight_variable_cost'])
        close(value, target, r['id'])
        close(sum(component_costs(r, p, basket).values()), target, r['id'])
        max_delta = max(max_delta, abs(value - target))
    return max_delta


def cash_events(loss, saved, delayed_revenue, action, timing, delay_days=1):
    """Illustrative delta to no-kover. Refund settles liability, not a 2nd loss."""
    events = []
    if timing['precollected_net_fare_fraction'] != 1 or timing['service_relative_day'] != 0:
        raise ValueError('cash timing fixture requires fully precollected net fare and service day0; actual collection adapter UNKNOWN')

    def add(day, event, pnl=0, inventory=0, payables=0, deferred=0):
        cash = pnl - inventory + payables + deferred
        events.append(dict(relative_day=day, event=event, delta_pnl_rub=pnl,
                           delta_inventory_rub=inventory, delta_payables_rub=payables,
                           delta_deferred_ticket_liability_rub=deferred, delta_cash_rub=cash))

    if action == 'cancel':
        fuel = saved['fuel_product']
        other = sum(saved.values()) - fuel
        add(0, 'scheduled_service_not_provided', pnl=-loss + fuel + other,
            inventory=fuel, payables=-other, deferred=loss)
        add(timing['supplier_settlement_relative_day'], 'avoided_conditional_usage_settlement', payables=other)
        add(timing['refund_relative_day'], 'refund_precollected_net_fare_once', deferred=-loss)
        add(timing['fuel_replenishment_relative_day'], 'later_replenishment_reduced_conditionally', inventory=-fuel)
    elif action == 'delay':
        add(0, 'scheduled_revenue_deferred', pnl=-delayed_revenue, deferred=delayed_revenue)
        add(delay_days, 'conditional_delayed_service', pnl=delayed_revenue, deferred=-delayed_revenue)
    else:
        add(0, 'unchanged_no_kover_difference')
    running, trough = 0, 0
    events.sort(key=lambda x: (x['relative_day'], x['event']))
    for e in events:
        running += e['delta_cash_rub']
        trough = min(trough, running)
        e['cumulative_delta_cash_rub'] = running
        e['additional_funding_so_far_rub'] = -trough
    return events, -trough


def apply(legs, sales, caps, baseline, policy, definition):
    p, basket = parameters(baseline['scenario'])
    action = policy['action']
    if action not in {'none', 'cancel', 'delay'}:
        raise ValueError('unknown action')
    touched = {r['id'] for r in legs if policy['episode_active'] and hits(r, definition['episode'])}
    cancelled = touched if action == 'cancel' else set()
    delayed = touched if action == 'delay' else set()
    impacted = lost_journeys(sales, touched)
    affected = lost_journeys(sales, cancelled)
    remaining = [r for r in sales if r not in affected]
    capacities = {key: (0 if key in cancelled else float(v['capacity_scenario'])) for key, v in caps.items()}
    kept = [r for r in legs if r['id'] not in cancelled]
    shifted = []
    for r in kept:
        row = dict(r)
        if row['id'] in delayed:
            minutes = policy['delay_minutes']
            row['departure_utc_minute'] = float(row['departure_utc_minute']) + minutes
            row['arrival_utc_minute'] = float(row['arrival_utc_minute']) + minutes
            horizon = datetime.fromisoformat(definition['period_end']).replace(tzinfo=timezone.utc) + timedelta(days=1)
            if instant(row, 'arrival') >= horizon:
                raise ValueError('delay outside tested weekly horizon; separate accrual accounting required')
            if hits(row, definition['episode']):
                raise ValueError('delayed movement still in restriction interval')
        shifted.append(row)
    used = validate_capacity(remaining, kept, capacities)
    rotated = template_rotation(shifted, reference=legs)
    # We refuse to claim a solved schedule if a narrow cancellation strands a label.
    # Main episode cancels complete daily banks and passes this limited check.
    schedule_status = 'TEMPLATE_ONLY_CONTINUITY_PASS' if not rotated else 'UNRESOLVED_TEMPLATE_DISCONTINUITY'
    saved = {k: 0.0 for k in COMPONENTS + ('new_pax_variable',)}
    if cancelled:
        fractions = definition['avoidability_profiles'][policy['avoidability']]
        for key in saved:
            if not 0 <= fractions[key] <= 1:
                raise ValueError(('invalid avoidable share', key, fractions[key]))
        for r in legs:
            if r['id'] in cancelled:
                for key, value in component_costs(r, p, basket).items():
                    saved[key] += value * fractions[key]
        saved['new_pax_variable'] = sum(float(r['new_pax_variable']) for r in affected) * fractions['new_pax_variable']
    loss = sum(float(r['gross_revenue']) for r in affected)
    lost = sum(float(r['sold_journeys']) for r in affected)
    lost_segments = sum(float(r['segment_pax']) for r in affected)
    # No donor or old migration is subtracted a second time. These are already in
    # the author's state difference. No restoration is asserted without inventory.
    restored_fraction = policy.get('old_migration_restored_fraction', 0)
    if restored_fraction != 0:
        raise ValueError('old RW restoration requires an explicit protected-inventory adapter; UNKNOWN')
    delta = -loss + sum(saved.values())
    delayed_revenue = sum(float(r['gross_revenue']) for r in impacted) if delayed else 0
    events, peak = cash_events(loss, saved, delayed_revenue, action, definition['cash_timing_stress'],
                               delay_days=policy.get('delay_minutes', 0) / 1440)
    close(sum(e['delta_pnl_rub'] for e in events), delta, 'cash accrual reconciliation')
    close(sum(e['delta_cash_rub'] for e in events), delta, 'terminal cash reconciliation in timing fixture')
    common = dict(model_id='Tsiri-stage17-MR02-overlay', author_ref='Цири/mput',
                  input_set_id=definition['input_set_id'], source_commit=definition['source_commit'],
                  run_id='MR02-overlay-v1-set001',
                  mode='COMMON_COMPARISON' if policy['episode_active'] else 'AUTHOR_REPLAY',
                  profile=definition['profile'], network=baseline['network'], candidate_id=baseline['network'],
                  author_scenario=baseline['scenario'], scenario_id=policy['id'],
                  baseline_id=':'.join([definition['profile'], baseline['network'], baseline['scenario'], 'no_kover']),
                  period_start=definition['period_start'], period_end=definition['period_end'],
                  direction_scope='BOTH_DIRECTIONS_SEPARATE_OD', market_unit='SCENARIO_ONEWAY_ENDPOINT_JOURNEY',
                  currency='RUB', price_basis='AUTHOR_NET_FARE_REFERENCE_COSTS_NOT_CONTRACT',
                  tax_basis='AUTHOR_EX_RECOVERABLE_VAT_ACTUAL_UNKNOWN',
                  value_status='CONDITIONAL_STRESS_BEFORE_UNKNOWN' if policy['episode_active'] else 'AUTHOR_EXPORT_ARITHMETIC',
                  acceptance_scope='SCOPED_SELF_CHECK_INDEPENDENT_REVIEW_PENDING')
    legrows = []
    for r in legs:
        cc = component_costs(r, p, basket)
        row = {**common, 'flight_id': r['id'], 'origin': r['origin'], 'destination': r['destination'],
               'planning_aircraft_label': r['aircraft'], 'actual_tail': None,
               'scheduled_departure_utc': instant(r, 'departure').isoformat(),
               'scheduled_arrival_utc': instant(r, 'arrival').isoformat(),
               'action': action if r['id'] in touched else 'unchanged',
               'delay_minutes': policy.get('delay_minutes', 0) if r['id'] in delayed else 0,
               'baseline_occupied': caps[r['id']]['occupied'],
               'remaining_capacity': capacities[r['id']], 'remaining_occupied': used[r['id']],
               'baseline_flight_cost_rub': sum(cc.values()),
               'avoided_flight_cost_rub': sum(cc[k] * definition['avoidability_profiles'][policy['avoidability']][k] for k in COMPONENTS) if r['id'] in cancelled else 0,
               'value_status': 'CONDITIONAL_STRESS' if policy['episode_active'] else 'AUTHOR_BASELINE_ARITHMETIC'}
        if r['id'] in delayed:
            row['conditional_actual_departure_utc'] = (instant(r, 'departure') + timedelta(minutes=policy['delay_minutes'])).isoformat()
            row['conditional_actual_arrival_utc'] = (instant(r, 'arrival') + timedelta(minutes=policy['delay_minutes'])).isoformat()
        legrows.append(row)
    jourrows = []
    for r in impacted:
        linked = r['flight_ids'].split(';')
        is_lost = bool(cancelled.intersection(linked))
        q = float(r['sold_journeys'])
        # Full itinerary refund in the named pretravel/no-protection policy.
        # A delay retains the fare conditional on eventual completion.
        jourrows.append({**common, 'journey_id': r['_journey_id'], 'source_csv_line': r['_source_csv_line'],
                         'origin': r['origin'], 'destination': r['destination'], 'flight_ids': r['flight_ids'],
                         'linked_leg_count': len(linked), 'affected_leg_count': len(touched.intersection(linked)),
                         'fare_once_rub': r['fare_once'], 'affected_endpoint_journeys': q,
                         'unserved_endpoint_journeys': q if is_lost else 0,
                         'conditionally_served_endpoint_journeys': 0 if is_lost else q,
                         'lost_net_revenue_rub': float(r['gross_revenue']) if is_lost else 0,
                         'net_refund_cash_rub': float(r['gross_revenue']) if is_lost else 0,
                         'retained_net_fare_rub': 0 if is_lost else float(r['gross_revenue']),
                         'old_foregone_revenue_unchanged_rub': r['foregone_RW_revenue'],
                         'saved_old_pax_unchanged_rub': r['saved_old_pax_variable'],
                         'actual_reaccommodation': 'UNKNOWN', 'value_status': 'CONDITIONAL_STRESS'})
    summary = {**common, 'restricted_airport': definition['episode']['airport'] if policy['episode_active'] else None,
               'affected_physical_legs': len(touched), 'cancelled_physical_legs': len(cancelled),
               'delayed_physical_legs': len(delayed), 'affected_endpoint_journeys': sum(float(r['sold_journeys']) for r in impacted),
               'unserved_endpoint_journeys': lost, 'unserved_segment_allocations': lost_segments,
               'remaining_endpoint_journeys': sum(float(r['sold_journeys']) for r in remaining),
               'lost_net_revenue_rub': loss, **{'saved_' + k + '_rub': v for k, v in saved.items()},
               'crew_cost_retained_rub': sum(component_costs(r, p, basket)['crew'] for r in legs),
               'author_contribution_rub': float(baseline['contribution_before_base_fleet_opportunity']),
               'overlay_delta_before_unknown_rub': delta,
               'contribution_after_overlay_before_unknown_rub': float(baseline['contribution_before_base_fleet_opportunity']) + delta,
               'additional_cash_peak_timing_stress_rub': peak, 'full_budget_profit_rub': None,
               'actual_full_cash_peak_rub': None, 'template_rotation_status': schedule_status,
               'actual_operational_readiness': 'UNKNOWN', 'independent_review': 'PENDING'}
    return summary, legrows, jourrows, [{**common, **e, 'price_tax_basis': 'NET_AUTHOR_EX_RECOVERABLE_VAT_TIMING_STRESS'} for e in events]


def main():
    definition = json.loads((ROOT / 'scenario_definitions.json').read_text())
    all_legs = readcsv(INPUTS / 'tsiri_flights.csv')
    all_sales = readcsv(INPUTS / 'tsiri_sales.csv')
    all_caps = readcsv(INPUTS / 'tsiri_capacity.csv')
    comparisons = readcsv(INPUTS / 'tsiri_comparison.csv')
    for line, r in enumerate(all_sales, 2):
        r['_source_csv_line'] = line
        r['_journey_id'] = 'tsiri-sales-line-' + str(line)
    summaries, physical, journeys, cash, components, baseline_checks = [], [], [], [], [], []
    for network in definition['networks']:
        for scenario in definition['author_scenarios']:
            filt = lambda r: r['profile'] == definition['profile'] and r['network'] == network
            legs = [r for r in all_legs if filt(r)]
            sales = [r for r in all_sales if filt(r) and r['scenario'] == scenario]
            caps = {r['flight_id']: r for r in all_caps if filt(r) and r['scenario'] == scenario}
            baseline = next(r for r in comparisons if filt(r) and r['scenario'] == scenario)
            used = validate_capacity(sales, legs, {k: float(v['capacity_scenario']) for k, v in caps.items()})
            for key, value in used.items():
                close(value, caps[key]['occupied'], 'baseline occupied')
            fields = ['sold_journeys', 'transfer_journeys', 'segment_pax', 'gross_revenue', 'foregone_RW_revenue', 'incremental_revenue', 'new_pax_variable', 'saved_old_pax_variable']
            for key in fields:
                close(sum(float(r[key]) for r in sales), baseline[key], key)
            for r in sales:
                close(float(r['sold_journeys']) * float(r['fare_once']), r['gross_revenue'], 'one fare')
                close(float(r['sold_journeys']) * len(r['flight_ids'].split(';')), r['segment_pax'], 'one seat per leg')
            close(sum(float(r['flight_variable_cost']) for r in caps.values()), baseline['flight_variable_cost'], 'flight costs summed once')
            c = float(baseline['gross_revenue']) - float(baseline['foregone_RW_revenue']) - float(baseline['flight_variable_cost']) - float(baseline['new_pax_variable']) + float(baseline['saved_old_pax_variable'])
            close(c, baseline['contribution_before_base_fleet_opportunity'], 'author contribution')
            max_delta = bounded_author_cost_replay(legs, caps, scenario)
            p, basket = parameters(scenario)
            for r in legs:
                for name, value in component_costs(r, p, basket).items():
                    components.append(dict(profile=definition['profile'], network=network, author_scenario=scenario, flight_id=r['id'], component=name, value_rub=value, unit='RUB/physical departure', price_basis='AUTHOR_REFERENCE_SCENARIO_NOT_CONTRACT', geography='UFA reference applied by author to every airport; not evidence of local rate', value_status='AUTHOR_FUNCTION_ARITHMETIC_REPLAY'))
            baseline_checks.append(dict(network=network, author_scenario=scenario, legs=len(legs), itineraries=len(sales), result='PASS', bounded_author_flight_cost_max_abs_delta_rub=max_delta, scope='exports, capacity, one-fare identity, pinned flight_cost functions only; full author main NOT_RUN'))
            for policy in definition['scenarios']:
                result, ls, js, cs = apply(legs, sales, caps, baseline, policy, definition)
                summaries.append(result)
                physical.extend(ls)
                journeys.extend(js)
                cash.extend(cs)
    writecsv(ROOT / 'scenario_summary.csv', summaries)
    writecsv(ROOT / 'physical_leg_status.csv', physical)
    writecsv(ROOT / 'affected_legs.csv', [r for r in physical if r['action'] != 'unchanged'])
    writecsv(ROOT / 'affected_journeys.csv', journeys)
    writecsv(ROOT / 'cost_cash_bridge.csv', cash)
    writecsv(ROOT / 'author_flight_cost_components.csv', components)
    writejson(ROOT / 'baseline_checks.json', dict(result='PASS', checks=baseline_checks,
              full_author_replay='NOT_RUN_HERE; pinned model_repair replay in separate reference set002',
              independent_review='PENDING', market_launch='NOT_ACCEPTED'))
    # These are overlay-only integration boundaries. General fixed-sales, supply
    # and donor thresholds remain owned by the pinned methods budget module.
    threshold_rows = []
    for r in summaries:
        if r['scenario_id'] != 'no_kover':
            threshold_rows.append(dict(network=r['network'], author_scenario=r['author_scenario'], scenario_id=r['scenario_id'],
                                      overlay_delta_before_unknown_rub=r['overlay_delta_before_unknown_rub'],
                                      maximum_extra_cost_for_nonnegative_contribution_rub=r['contribution_after_overlay_before_unknown_rub'],
                                      nonnegative_extra_cost_feasible=r['contribution_after_overlay_before_unknown_rub'] >= 0,
                                      boundary='X_disruption + X_other_budget - S_eligible <= C_author + delta_overlay',
                                      pairwise_adapter='Delta_after = Delta_methods + delta_overlay_A - delta_overlay_B - (X_A-X_B); no repeated donor/migration deduction',
                                      probability=None, value_status='CONDITIONAL_BOUNDARY_NOT_BUDGET_OR_PROBABILITY'))
    writecsv(ROOT / 'thresholds.csv', threshold_rows)
    print(json.dumps(dict(scenarios=len(summaries), affected_leg_rows=sum(r['action'] != 'unchanged' for r in physical), affected_itinerary_rows=len(journeys), baseline_groups=len(baseline_checks))))


if __name__ == '__main__':
    main()
