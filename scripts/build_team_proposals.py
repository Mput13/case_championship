#!/usr/bin/env python3
"""Replay frozen stage-17 networks for the short team proposals; no optimisation."""
import csv
import hashlib
import json
import math
from pathlib import Path

import build_aircraft_route_review as review

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'context/21_team_proposals'
MODEL = ROOT / 'context/17_aircraft_route_review/model'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    definitions = json.loads((MODEL / 'selected_networks.json').read_text())
    with (MODEL / 'comparison.csv').open(newline='') as stream:
        previous = list(csv.DictReader(stream))
    profile = 'ROUTE_INPUTS_UPPER_100'
    m = review.setup(profile)
    direct_def = definitions['UNKNOWN_TIME_PLUS60_100|D_case']
    networks = {
        'D_SVX8': review.make_direct(m, 'D_SVX8', direct_def['jobs']),
        'D_previous_best8': review.make_direct(
            m, 'D_previous_best8', definitions[profile + '|D_case']['jobs']),
    }
    for name in ['H_UFA_4', 'H_UFA_8']:
        d = definitions[profile + '|' + name]
        networks[name] = review.legacy.hub(m, d['hub'], d['leaves'], d['frequency'], name)
    checks, results, routes = {}, [], []
    numeric_keys = [
        'sold_journeys', 'transfer_journeys', 'segment_pax',
        'migrated_RW_total', 'incremental_revenue', 'incremental_operating_cost',
        'contribution_before_base_fleet_opportunity', 'weekly_legs', 'weekly_block_hours',
    ]
    for name, net in networks.items():
        assert net is not None
        audit, _ = m.audit(net)
        assert audit['feasible'], (name, audit)
        checks[name + '_rotation_model_pass'] = True
        source_profile, source_name = (
            ('UNKNOWN_TIME_PLUS60_100', 'D_case') if name == 'D_SVX8'
            else (profile, 'D_case' if name == 'D_previous_best8' else name)
        )
        for scenario in ['base', 'cautious']:
            result, sales, capacities = m.evaluate(net, scenario, detail=True)
            old = next(r for r in previous if r['profile'] == source_profile
                       and r['network'] == source_name and r['scenario'] == scenario)
            for key in numeric_keys:
                assert math.isclose(result[key], float(old[key]), rel_tol=1e-10, abs_tol=1e-5), (name, scenario, key)
            assert math.isclose(sum(r['occupied'] for r in capacities),
                                sum(r['segment_pax'] for r in sales), abs_tol=1e-6)
            assert math.isclose(result['incremental_revenue'] - result['incremental_operating_cost'],
                                result['contribution_before_base_fleet_opportunity'], abs_tol=1e-6)
            result.update(active_allocated=len({l['aircraft'] for l in net['legs']}),
                          reserve_scenario=1, common_active_ceiling=4,
                          physical_pairs=len({review.core.pair(l['origin'], l['destination']) for l in net['legs']}),
                          source_profile=source_profile, source_network=source_name,
                          scope='ADDITIONAL_FLIGHTS_NOT_ACTUAL_REPLACEMENT_OR_SEASON')
            results.append(result)
            checks[name + '_' + scenario + '_replays_frozen_result_and_balances'] = True
        for pair in sorted({review.core.pair(l['origin'], l['destination']) for l in net['legs']}):
            a, b = pair.split('-')
            legs = [l for l in net['legs'] if review.core.pair(l['origin'], l['destination']) == pair]
            routes.append(dict(network=name, pair=pair,
                               departures_A_B=sum(l['origin'] == a for l in legs),
                               departures_B_A=sum(l['origin'] == b for l in legs),
                               block_A_B=m.block(a, b), block_B_A=m.block(b, a),
                               technical_status='требует эксплуатационной проверки'))
    # The SVX contour uses published directional proxies on every leg: its replay
    # under the common profile does not silently import the unknown-time stress.
    assert all((l['origin'], l['destination']) in m.route_blocks for l in networks['D_SVX8']['legs'])
    checks['D_SVX8_all_legs_have_published_directional_proxy'] = True
    for filename, rows in [('comparison.csv', results), ('routes.csv', routes)]:
        with (OUT / filename).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    sources = [MODEL / 'selected_networks.json', MODEL / 'comparison.csv',
               ROOT / 'context/17_aircraft_route_review/assumptions.json',
               ROOT / 'context/17_aircraft_route_review/evidence/directional_blocks.csv',
               ROOT / 'context/17_aircraft_route_review/evidence/published_service_facts.csv',
               ROOT / 'context/16_conditional_decision/assumptions.json',
               Path(__file__).resolve()]
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    report = dict(status='PASS', checks=checks, input_sha256=manifest,
                  no_new_market_or_cost_assumptions=True, no_new_optimisation=True,
                  dispatch_clearance=False, actual_replacement_calculated=False,
                  seasonal_program_calculated=False)
    (OUT / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', checks=len(checks), results=len(results)), ensure_ascii=False))


if __name__ == '__main__':
    main()
