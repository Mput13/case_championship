#!/usr/bin/env python3
"""One explicit finalized research round; default is a non-writing dry run.

Admission records are evidence qualifications, not an independent source review.
Only --apply consumes the single final-round receipt. No source or owner edits.
"""
import argparse
import collections
import csv
from datetime import date
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from build_baseline import (HERE, OUT, REPO, NAMES, SCENARIOS, NUMERIC, MONEY_RESULT,
    read_csv, write_csv, write_json, sha256, load_inputs, independent_ledger, near)
from prepare_admission import FIELDS, COST_UNITS, TAX, PERIOD

STATUS = {'direct_input', 'proxy', 'scenario_only', 'rejected_missing_scope'}
UNITS = dict(COST_UNITS, weekly_demand='endpoint_journeys/week/direction', fare_once_net='RUB/endpoint_journey')


class AdmissionError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AdmissionError(message)


def local_file(relative):
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(), 'expected nonempty OUT-relative artifact path')
    path = (OUT / relative).resolve()
    require(path.is_relative_to(OUT.resolve()) and path.is_file(), f'artifact missing or outside OUT: {relative}')
    return path


def bound_file(relative, expected):
    path = local_file(relative)
    require(isinstance(expected, str) and len(expected) == 64 and sha256(path) == expected, f'SHA-256 mismatch: {relative}')
    return path


def period_covers(row):
    try:
        return date.fromisoformat(row['source_period_start']) <= date.fromisoformat(PERIOD['start']) and date.fromisoformat(row['source_period_end']) >= date.fromisoformat(PERIOD['end'])
    except (KeyError, ValueError):
        return False


def validate_finding(row, pair_support):
    fid = row.get('finding_id', '<missing>')
    status = row.get('admission_status')
    require(status in STATUS, f'{fid}: admission status missing/invalid')
    require(row.get('apply') in ('true', 'false'), f'{fid}: apply must be explicit true/false')
    require(bool(row.get('claim')) and bool(row.get('reliability')), f'{fid}: separate claim/reliability required')
    if status == 'rejected_missing_scope':
        require(row['apply'] == 'false' and bool(row.get('rejection_reason')), f'{fid}: rejected finding cannot apply; give missing scope')
        return None
    # Even context-only admitted findings need evidence fields; an unsupported
    # parameter can be retained with apply=false and no numerical substitution.
    require(all(row.get(k) for k in ('source_url', 'source_artifact', 'source_sha256', 'source_unit', 'source_tax_basis', 'source_kind', 'source_scope', 'source_period_start', 'source_period_end', 'condition')), f'{fid}: evidence metadata incomplete')
    try:
        start, end = date.fromisoformat(row['source_period_start']), date.fromisoformat(row['source_period_end'])
        require(start <= end, f'{fid}: source period reversed')
    except ValueError as e:
        raise AdmissionError(f'{fid}: source period must be ISO dates') from e
    if row['apply'] == 'false':
        return None
    parameter = row.get('model_parameter')
    require(parameter in UNITS, f'{fid}: parameter outside fixed-network adapter scope: {parameter}')
    require(row.get('model_unit') == UNITS[parameter], f'{fid}: model unit mismatch for {parameter}')
    require((row.get('model_period_start'), row.get('model_period_end')) == (PERIOD['start'], PERIOD['end']), f'{fid}: model period mismatch')
    sc, recipe, network = row.get('scenario'), row.get('recipe'), row.get('network')
    require(sc in SCENARIOS, f'{fid}: use explicit base/cautious scenario')
    require(network in (*NAMES, 'ALL'), f'{fid}: new network not allowed')
    try:
        value = float(row['value'])
    except (KeyError, ValueError) as e:
        raise AdmissionError(f'{fid}: numeric value required; UNKNOWN is not zero') from e
    require(math.isfinite(value) and value >= 0, f'{fid}: nonnegative finite value required')
    if parameter == 'deicing_probability':
        require(value <= 1, f'{fid}: probability must be at most one')
    require(bool(row.get('conversion')), f'{fid}: explicit conversion/no-conversion statement required')
    if status == 'direct_input':
        require(period_covers(row), f'{fid}: direct_input source must cover exact target week')
        require(row['source_unit'] == row['model_unit'], f'{fid}: source grain differs; use proxy/scenario instead of direct_input')
    if parameter == 'weekly_demand':
        require(recipe in ('C', 'N'), f'{fid}: demand needs explicit recipe C or N')
        require(row.get('model_tax_basis') == 'NOT_APPLICABLE_QUANTITY', f'{fid}: demand tax basis must be quantity-only')
    else:
        require(recipe == 'ALL', f'{fid}: fares/costs must change both C and N symmetrically')
        require(row.get('model_tax_basis') == TAX, f'{fid}: model net tax basis mismatch')
        if status == 'direct_input':
            require(row['source_tax_basis'] == TAX, f'{fid}: source/model tax bases differ; direct input refused')
    if parameter in COST_UNITS:
        require(network == 'ALL' and not row.get('pair'), f'{fid}: shared costs apply to all fixed flown legs in all networks')
        require(row['source_scope'] == 'ALL_FIXED_FLOWN_LEGS', f'{fid}: shared-cost applicability must be explicit, not a single-airport fact')
        if status == 'direct_input':
            require(row['source_kind'] == 'applicable_all_flown_legs_net_cost', f'{fid}: a tariff/assumption is not all-leg actual cost')
    else:
        pair = row.get('pair', '')
        require(pair.count('-') == 1 and pair == '-'.join(sorted(pair.split('-'))), f'{fid}: canonical existing airport pair required')
        networks = NAMES if network == 'ALL' else (network,)
        affected = [n for n in networks if pair in pair_support[n]]
        require(bool(affected) and (network == 'ALL' or len(affected) == 1), f'{fid}: pair outside fixed offer support')
        if parameter == 'weekly_demand' and status == 'direct_input':
            require(row['source_kind'] == 'observed_endpoint_od' and row.get('carrier') == 'ALL_MARKET', f'{fid}: airport/route segments/one-carrier/offer is not total-market endpoint OD')
            require(row['source_scope'] == 'BOTH_DIRECTIONS_SAME_D:' + pair, f'{fid}: symmetric-pair adapter cannot apply one-direction/asymmetric observation as fact')
        if parameter == 'fare_once_net':
            require(status != 'proxy', f'{fid}: fare proxy must be explicit scenario_only')
            if status == 'direct_input':
                require(row['source_kind'] == 'rw_realized_net_fare' and row.get('carrier') == 'RW', f'{fid}: retail quote is not realized RW net yield')
                require(row['source_scope'] == 'BOTH_DIRECTIONS_SAME_FARE:' + pair, f'{fid}: same fare must be justified on both directions')
            elif row['source_kind'] == 'retail_quote':
                require(row.get('carrier') and row.get('conversion'), f'{fid}: retail-to-net basket/tax/carrier reconciliation missing')
    return dict(row, numeric_value=value)


def read_package(relative):
    package_path = local_file(relative)
    package = json.loads(package_path.read_text())
    contract = json.loads((HERE / 'integration_contract.json').read_text())
    require(package.get('schema_version') == 1 and package.get('round') == 'FINAL_TARGETED_INTEGRATION', 'wrong integration schema/round')
    require(package.get('ready') is True and package.get('all_findings_enumerated') is True, 'BASELINE_ONLY: final research package not ready/enumerated')
    for key, filename in [('baseline_sha256', 'baseline_comparison.csv'), ('network_contract_sha256', 'network_contract.json')]:
        require(package.get(key) == contract.get(key) == sha256(HERE / filename), f'{filename}: baseline binding mismatch')
    require(contract.get('source_manifest_sha256') == sha256(HERE / 'source_manifest.json'), 'source manifest binding mismatch')
    for source in json.loads((HERE / 'source_manifest.json').read_text())['entries']:
        path = REPO / source['local_path']
        require(path.resolve().is_relative_to(OUT.resolve()) and sha256(path) == source['sha256'], f"frozen source bytes changed: {source['local_path']}")
    researchers = package.get('researchers', [])
    require(len(researchers) == 3 and len({r.get('researcher_id') for r in researchers}) == 3, 'exactly three distinct finalized research manifests required')
    expected_ids, researcher_ids = {}, set()
    for r in researchers:
        require(r.get('status') == 'FINAL', f"researcher not FINAL: {r.get('researcher_id')}")
        path = bound_file(r.get('manifest_path'), r.get('manifest_sha256'))
        manifest = json.loads(path.read_text())
        rid = r['researcher_id']
        require(manifest.get('researcher_id') == rid and manifest.get('status') == 'FINAL', f'{rid}: finalized manifest identity mismatch')
        ids = manifest.get('finding_ids')
        require(isinstance(ids, list) and all(isinstance(x, str) and x for x in ids) and len(ids) == len(set(ids)), f'{rid}: exact unique finding_ids required')
        expected_ids[rid] = set(ids)
        researcher_ids.add(rid)
    findings_path = bound_file(package.get('findings_csv'), package.get('findings_sha256'))
    with findings_path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        require(set(FIELDS) <= set(reader.fieldnames or []), 'findings CSV schema incomplete')
        rows = list(reader)
    require(package.get('finding_count') == len(rows), 'finding count mismatch')
    ids = [r.get('finding_id') for r in rows]
    require(all(ids) and len(ids) == len(set(ids)), 'finding IDs must be nonempty and unique')
    require(all(r.get('researcher_id') in researcher_ids for r in rows), 'finding has unknown researcher')
    for rid, expected in expected_ids.items():
        require({r['finding_id'] for r in rows if r['researcher_id'] == rid} == expected, f'{rid}: missing/extra finding admission rows')
    # Bind source bytes for every admitted finding, including context-only ones.
    for row in rows:
        if row.get('admission_status') != 'rejected_missing_scope':
            bound_file(row.get('source_artifact'), row.get('source_sha256'))
    return package_path, package, rows


def compute(rows):
    m, _, comparisons, sales, capacity, _, config = load_inputs()
    mapping = read_csv(HERE / 'source_snapshot/methods/runs/common_demand_v1/demand_mapping.csv')
    pair_support = {n: {x['pair'] for x in mapping if x['network'] == n} for n in NAMES}
    applied = [v for r in rows if (v := validate_finding(r, pair_support)) is not None]
    # Detect all overlaps, including ALL versus specific-network updates.
    seen = set()
    for row in applied:
        networks = NAMES if row['network'] == 'ALL' else (row['network'],)
        recipes = ('C', 'N') if row['recipe'] == 'ALL' else (row['recipe'],)
        for n in networks:
            if row['model_parameter'] in ('weekly_demand', 'fare_once_net') and row['pair'] not in pair_support[n]:
                continue
            for recipe in recipes:
                key = n, row['scenario'], recipe, row['model_parameter'], row.get('pair', '')
                require(key not in seen, f"overlapping parameter changes: {key}")
                seen.add(key)
    baseline = read_csv(HERE / 'baseline_comparison.csv')
    output, detail_output, handoff, leg_output = [], [], [], []
    for n in NAMES:
        for sc in SCENARIOS:
            reference = next(r for r in comparisons if (r['network'], r['scenario']) == (n, sc))
            key = reference['source_profile'], reference['source_network'], sc
            ss = [r for r in sales if (r['profile'], r['network'], r['scenario']) == key]
            cc = [r for r in capacity if (r['profile'], r['network'], r['scenario']) == key]
            old_p = config['scenarios'][sc]
            for recipe in ('C', 'N'):
                changed = [r for r in applied if r['network'] in ('ALL', n) and r['scenario'] == sc and r['recipe'] in ('ALL', recipe)]
                p, legs = dict(old_p), [dict(r) for r in cc]
                offers = [dict(r) for r in m.prepare(ss, cc, sc, old_p)]
                demand = {tuple(r['pair'].split('-')): float(r['C_week_direction'] if recipe == 'C' else r['N_week_direction_stress']) for r in mapping if (r['network'], r['scenario']) == (n, sc)}
                effective_ids = []
                for row in changed:
                    parameter, value = row['model_parameter'], row['numeric_value']
                    if parameter in COST_UNITS:
                        old = p[parameter]
                        p[parameter] = value
                    else:
                        pair = tuple(row['pair'].split('-'))
                        if pair not in demand:
                            continue
                        if parameter == 'weekly_demand':
                            old = demand[pair]
                            demand[pair] = value
                        else:
                            old = sorted({o['fare'] for o in offers if m.pair(o['origin'], o['destination']) == pair})
                            for o in offers:
                                if m.pair(o['origin'], o['destination']) == pair:
                                    o['fare'] = value  # original oldfare/can/direct cap deliberately preserved
                    effective_ids.append(row['finding_id'])
                    handoff.append(dict(what=row['claim'], file_parameter=f"{n}/{sc}/{recipe}:{parameter}:{row.get('pair','')}", before=old,
                                        after=value, condition=row['condition'], source=row['source_url'], source_sha256=row['source_sha256'],
                                        reliability=row['reliability'], admission_status=row['admission_status'], finding_id=row['finding_id'],
                                        status='SEPARATE_FINAL_SENSITIVITY_OWNER_UNCHANGED'))
                # Retain exactly the same local-first objective and tie breakers.
                offers.sort(key=lambda o: (o['transfer'], -(o['fare'] - o['can'] * o['oldfare'] - len(o['legs']) * p['pax_cost']) / len(o['legs']), o['origin'], o['destination'], o['day'], tuple(o['legs'])))
                for leg in legs:
                    leg['flight_variable_cost'] = m.flight_cost(float(leg['block_minutes']), p)
                    leg_output.append(dict(network=n, scenario=sc, recipe=recipe, flight_id=leg['flight_id'], before=next(r['flight_variable_cost'] for r in cc if r['flight_id'] == leg['flight_id']), after=leg['flight_variable_cost'], tax_basis=TAX, applicable_scope='FIXED_FLOWN_LEG_SCENARIO'))
                totals, details, _ = m.simulate(offers, legs, p, demand)
                independent_ledger(details, legs, totals, p, (n, sc, recipe, 'final scenario'))
                before = next(r for r in baseline if (r['network'], r['scenario'], r['recipe']) == (n, sc, recipe))
                if not effective_ids:
                    for k in NUMERIC:
                        near(totals[k], before[k], ('unchanged adapter case', n, sc, recipe, k))
                output.append(dict(network=n, scenario=sc, baseline_recipe=recipe, variant='FINAL_ADMITTED_FIXED_SUPPLY_SENSITIVITY',
                                   period_start=PERIOD['start'], period_end=PERIOD['end'], price_basis='EXPLICIT_ADMITTED_NET_SCENARIO', tax_basis=TAX,
                                   before_contribution=float(before[MONEY_RESULT]), delta_contribution=totals[MONEY_RESULT] - float(before[MONEY_RESULT]),
                                   applied_findings=';'.join(effective_ids), full_pnl=None, full_budget=None, peak_cash=None, launch_accepted=False, **totals))
                detail_output.extend(dict(network=n, scenario=sc, baseline_recipe=recipe, **d) for d in details)
    return applied, output, detail_output, handoff, leg_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, help='OUT-relative finalized package JSON')
    parser.add_argument('--apply', action='store_true', help='write a separate final_round output once; never changes baseline/owner')
    args = parser.parse_args()
    receipt = HERE / 'final_round/integration_receipt.json'
    try:
        require(not receipt.exists(), 'single final integration already consumed; second applied round/re-check refused')
        package_path, package, rows = read_package(args.package)
        applied, output, details, handoff, costs = compute(rows)
        protected = json.loads((OUT / 'protected_city_stage.json').read_text())
        require(all(sha256(REPO / path) == h for path, h in protected.items()), 'protected city-stage hash mismatch')
        result = dict(status='VALIDATED_DRY_RUN' if not args.apply else 'FINAL_SCOPED_SENSITIVITY',
                      package_sha256=sha256(package_path), baseline_sha256=sha256(HERE / 'baseline_comparison.csv'),
                      network_contract_sha256=sha256(HERE / 'network_contract.json'), findings=len(rows), applied_findings=len(applied),
                      cases=len(output), protected_all_match=True, full_PnL=None, peak_cash=None,
                      source_review='explicit supplied admission and byte hashes only; not independent market/source approval',
                      actual_operating_acceptance=False)
        if args.apply:
            dest = HERE / 'final_round'
            dest.mkdir(exist_ok=True)
            write_csv(dest / 'integration_admission.csv', rows, FIELDS)
            write_csv(dest / 'integration_comparison.csv', output)
            write_csv(dest / 'integration_itineraries.csv', details)
            write_csv(dest / 'flight_cost_changes.csv', costs)
            write_csv(dest / 'owner_handoff.csv', handoff, ['what','file_parameter','before','after','condition','source','source_sha256','reliability','admission_status','finding_id','status'])
            result['output_sha256'] = {str(p.name): sha256(p) for p in sorted(dest.glob('*.csv'))}
            write_json(receipt, result)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (AdmissionError, KeyError, ValueError) as e:
        print(json.dumps(dict(status='REJECTED_NO_INTEGRATION', reason=str(e)), ensure_ascii=False))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
