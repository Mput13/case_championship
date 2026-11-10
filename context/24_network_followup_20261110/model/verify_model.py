#!/usr/bin/env python3
"""Offline numerical and admission-boundary verification; no research ingestion."""
import ast
import collections
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from build_baseline import HERE, OUT, REPO, MONEY_RESULT, NUMERIC, read_csv, sha256, write_json, near, load_inputs
from prepare_admission import COST_UNITS, TAX, PERIOD
import integrate_once as adapter


def expect_rejection(name, call, results):
    try:
        call()
    except adapter.AdmissionError as e:
        results.append(dict(check=name, status='PASS_EXPECTED_REJECTION', reason=str(e)))
    else:
        raise AssertionError(('expected rejection', name))


def main():
    results = []
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text())
    results.append(dict(check='own_python_syntax', status='PASS'))
    _, unchanged, _, _, _ = adapter.compute([])
    baseline = read_csv(HERE / 'baseline_comparison.csv')
    for r in unchanged:
        old = next(x for x in baseline if (x['network'], x['scenario'], x['recipe']) == (r['network'], r['scenario'], r['baseline_recipe']))
        for k in NUMERIC:
            near(r[k], old[k], ('identity adapter', k))
    results.append(dict(check='adapter_identity_12_cases', status='PASS'))
    _, _, _, _, capacity, _, config = load_inputs()
    mapping = read_csv(HERE / 'source_snapshot/methods/runs/common_demand_v1/demand_mapping.csv')
    support = {n: {x['pair'] for x in mapping if x['network'] == n} for n in adapter.NAMES}
    fixture = dict(finding_id='SYNTHETIC_UPLIFT_TEST_ONLY', researcher_id='TEST', claim='synthetic +100 RUB/t uplift only',
        admission_status='scenario_only', apply='true', model_parameter='fuel_uplift_rub_per_t', network='ALL', scenario='base', recipe='ALL', pair='',
        value=config['scenarios']['base']['fuel_uplift_rub_per_t'] + 100, source_url='fixture://not_real_research',
        source_artifact='NOT_READ_SYNTHETIC_TEST', source_sha256='NOT_A_SOURCE_RECEIPT',
        source_period_start=PERIOD['start'], source_period_end=PERIOD['end'], source_unit=COST_UNITS['fuel_uplift_rub_per_t'],
        source_tax_basis=TAX, model_period_start=PERIOD['start'], model_period_end=PERIOD['end'],
        model_unit=COST_UNITS['fuel_uplift_rub_per_t'], model_tax_basis=TAX, source_kind='synthetic_fixture',
        source_scope='ALL_FIXED_FLOWN_LEGS', carrier='', conversion='none; synthetic sensitivity',
        condition='verification only, never final source admission', reliability='SYNTHETIC_TEST_NOT_EVIDENCE', rejection_reason='')
    _, changed, _, _, legs = adapter.compute([fixture])
    p = config['scenarios']['base']
    for r in changed:
        ls = [x for x in legs if (x['network'], x['scenario'], x['recipe']) == (r['network'], r['scenario'], r['baseline_recipe'])]
        if r['scenario'] == 'cautious':
            near(r['delta_contribution'], 0, 'unaffected cautious')
            continue
        old = next(x for x in baseline if (x['network'], x['scenario'], x['recipe']) == (r['network'], r['scenario'], r['baseline_recipe']))
        near(r['sold_journeys'], old['sold_journeys'], 'fuel change does not invent demand')
        delta = sum(float(x['after']) - float(x['before']) for x in ls)
        near(r['delta_contribution'], -delta, 'symmetric fuel delta once', 1e-6)
        assert all(float(x['after']) > float(x['before']) for x in ls)
    for n in adapter.NAMES:
        c, nn = [r for r in changed if r['network'] == n and r['scenario'] == 'base']
        near(c['delta_contribution'], nn['delta_contribution'], 'C/N symmetric flown-leg cost', 1e-6)
    results.append(dict(check='synthetic_uplift_delta_all_flown_legs_both_recipes_no_double_count', status='PASS', source_admission='NOT_REAL_RESEARCH'))
    cost_wrong = dict(fixture, network='H_UFA_4')
    expect_rejection('single_network_shared_cost', lambda: adapter.validate_finding(cost_wrong, support), results)
    annual = dict(fixture, model_parameter='weekly_demand', network='D_SVX8', recipe='C', pair='AER-SVX', value='780000',
                  model_unit='endpoint_journeys/week/direction', source_unit='route_segments/year', model_tax_basis='NOT_APPLICABLE_QUANTITY',
                  admission_status='direct_input', source_kind='observed_route_segments', source_scope='BOTH_DIRECTIONS_SAME_D:AER-SVX', carrier='ALL_MARKET')
    expect_rejection('annual_route_segments_as_direct_weekly_endpoint_OD', lambda: adapter.validate_finding(annual, support), results)
    airport = dict(annual, source_unit='endpoint_journeys/week/direction', source_kind='airport_total')
    expect_rejection('airport_total_or_offer_relabelled_as_direct_endpoint_OD', lambda: adapter.validate_finding(airport, support), results)
    one_direction = dict(airport, source_kind='observed_endpoint_od', source_scope='ONE_DIRECTION:AER-SVX')
    expect_rejection('one_direction_observation_into_symmetric_pair', lambda: adapter.validate_finding(one_direction, support), results)
    retail = dict(fixture, model_parameter='fare_once_net', network='D_SVX8', pair='AER-SVX', value='15000', model_unit='RUB/endpoint_journey',
                  source_unit='RUB/endpoint_journey', source_kind='retail_quote', source_scope='BOTH_DIRECTIONS_SAME_FARE:AER-SVX', carrier='RW', admission_status='direct_input')
    expect_rejection('retail_quote_as_achieved_RW_net_yield', lambda: adapter.validate_finding(retail, support), results)
    recipe_cost = dict(fixture, recipe='C')
    expect_rejection('cost_changed_in_only_one_demand_recipe', lambda: adapter.validate_finding(recipe_cost, support), results)
    nan = dict(fixture, value='NaN')
    expect_rejection('nonfinite_unknown_as_numeric_cost', lambda: adapter.validate_finding(nan, support), results)
    new_pair = dict(annual, admission_status='proxy', pair='MOW-ZIA')
    expect_rejection('new_pair_or_MOW_ZIA_substitution', lambda: adapter.validate_finding(new_pair, support), results)
    expect_rejection('outside_OUT_evidence_path', lambda: adapter.local_file('../../src/network_model.py'), results)
    expect_rejection('wrong_source_hash', lambda: adapter.bound_file('model/network_contract.json', '0' * 64), results)
    expect_rejection('unfinished_research_package', lambda: adapter.read_package('model/final_integration_package.template.json'), results)
    assert not (HERE / 'final_round/integration_receipt.json').exists()
    results.append(dict(check='no_final_round_executed_or_consumed', status='PASS'))
    # Determinism includes supply/contract/package hashes, not this test report.
    key_files = ['baseline_comparison.csv', 'network_contract.json', 'source_manifest.json', 'scenario_thresholds.csv',
                 'fixed_rule_bounds.csv', 'validation.json', 'model_audit.md', 'input_admission.csv', 'owner_handoff.csv',
                 'integration_contract.json', 'final_integration_package.template.json']
    before = {name: sha256(HERE / name) for name in key_files}
    subprocess.check_call([sys.executable, str(HERE / 'build_baseline.py')], cwd=REPO, stdout=subprocess.DEVNULL)
    subprocess.check_call([sys.executable, str(HERE / 'prepare_admission.py')], cwd=REPO, stdout=subprocess.DEVNULL)
    assert before == {name: sha256(HERE / name) for name in key_files}
    results.append(dict(check='offline_repeat_deterministic_output_hashes', status='PASS', files=len(key_files)))
    protected = json.loads((OUT / 'protected_city_stage.json').read_text())
    assert all(sha256(REPO / name) == expected for name, expected in protected.items())
    tracked = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=REPO, text=True).splitlines()
    assert not tracked, ('tracked source changed', tracked)
    results.append(dict(check='protected_hashes_and_no_tracked_file_edits', status='PASS', protected_files=len(protected)))
    write_json(HERE / 'adapter_validation.json', dict(status='PASS_SCOPED_SYNTHETIC_AND_REPLAY_CHECKS', checks=results,
               actual_research_integrated=False, final_round_consumed=False, independent_external_source_review=False))
    write_json(HERE / 'output_manifest.json', dict(
        status='BASELINE_ONLY', files=[dict(path=str(path.relative_to(OUT)), bytes=path.stat().st_size, sha256=sha256(path))
        for path in sorted(HERE.iterdir()) if path.is_file() and path.name != 'output_manifest.json'],
        snapshots='source_manifest.json', owner_snapshot='../owner_snapshot', protected_stage='validation.json',
        coverage='all direct model deliverables; immutable snapshot files individually listed in source_manifest.json'))
    print(json.dumps(dict(status='PASS_SCOPED_BASELINE_ONLY', verification_checks=len(results), final_round_consumed=False, protected_all_match=True)))


if __name__ == '__main__':
    main()
