#!/usr/bin/env python3
"""Coordinator intake of exact digital final; no independent market acceptance."""
import csv
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path

SHA = 'd48b4a4f86de29aa968665f1601b785bd1824c54'
ROOT = 'context/28_evening_run_20261110/digital_growth/'
def blob(sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path])
def rows(name):
    return list(csv.DictReader(io.StringIO(blob(SHA, ROOT + name).decode())))
def near(actual, expected):
    assert math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-7), (actual, expected)

m = json.loads(blob(SHA, ROOT + 'manifest.json'))
for x in m['inputs']:
    b = blob(x['commit'], x['path'])
    assert len(b) == x['bytes'] and hashlib.sha256(b).hexdigest() == x['sha256']
for x in m['artifacts']:
    b = blob(SHA, ROOT + x['path'])
    assert len(b) == x['bytes'] and hashlib.sha256(b).hexdigest() == x['sha256']
p = json.loads(blob(SHA, ROOT + 'parameters.json'))
digital = rows('digital_thresholds.csv')
for r in digital:
    x = next(x for x in p['digital_scenarios'] if (x['id'], x['scenario']) == (r['id'], r['scenario']))
    gross = x['eligible_events'] * x['uplift_absolute'] * x['unit_contribution_rub']
    cost = x['cannibalized_contribution_rub'] + x['annual_support_cash_rub'] + x['implementation_cash_rub']
    near(r['first_year_result_after_implementation_rub'], gross - cost)
    near(r['break_even_uplift_absolute'], cost / (x['eligible_events'] * x['unit_contribution_rub']))
    assert r['cash_in_effect'] == 'NOT_ESTIMATED'
resource = rows('resource_scale.csv')
for r in resource:
    capacity = float(r['seats']) * float(r['load_factor']) * 365 * float(r['productive_hours_per_active_day']) * float(r['availability_including_reserve']) / float(r['block_hours_per_leg'])
    near(r['passenger_segments_per_stock_year'], capacity)
    assert math.ceil((float(r['target_passenger_segments_per_year']) - p['red_wings_passengers']) / capacity) == int(r['additional_stock_equivalent_ceil'])
power = rows('experiment_power.csv')
for r in power:
    baseline = float(r['assumed_baseline'])
    n = math.ceil(2 * (1.96 + .84)**2 * baseline * (1-baseline) / float(r['absolute_MDE'])**2)
    assert n == int(r['events_per_arm_approx'])
    near(r['traffic_days_approx'], 2*n / float(r['assumed_eligible_events_per_year']) * 365)
shares = rows('market_share_scenarios.csv')
for r in shares:
    before = float(r['rw_before']) / float(r['baseline_market']) * 100
    after = float(r['rw_landmark']) / float(r['scenario_market']) * 100
    near(r['rw_share_before_pct'], before)
    near(r['rw_share_after_pct'], after)
    near(r['change_pp'], after-before)
mixed = rows('mixed_scale.csv')
near(sum(float(r['incremental_passenger_fraction']) for r in mixed), 1)
near(sum(float(r['incremental_passengers']) for r in mixed), p['number_two_landmark']-p['red_wings_passengers'])
for r in mixed:
    x = next(x for x in p['resource_scenarios'] if x['id'] == r['id'])
    hours = float(r['incremental_passengers']) / (x['seats'] * x['load_factor']) * x['block_hours_per_leg']
    near(r['block_hours'], hours)
    assert math.ceil(hours/(365*x['productive_hours_per_active_day']*x['availability_including_reserve'])) == int(r['additional_stock_equivalent_ceil'])
assert all(float(r['first_year_result_after_implementation_rub']) < 0 for r in digital if r['scenario'] == 'cautious')
d03 = next(r for r in digital if r['id']=='D03' and r['scenario']=='cautious')
assert float(d03['break_even_uplift_absolute']) > .4
result = {
    'subject_sha': SHA, 'status': 'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING',
    'checks': {'pinned_inputs': len(m['inputs']), 'artifact_hashes': len(m['artifacts']), 'digital_rows': len(digital), 'resource_rows': len(resource), 'power_rows': len(power), 'share_rows': len(shares), 'mixed_rows': len(mixed)},
    'preserved_limits': ['D03 measures a decrease in repeat-contact probability, not ticket conversion', 'Power is a normal approximation under stated independent-case assumptions', 'Digital scenarios are not additive independently; no actual cash savings or passenger growth proved', 'Resource equivalents are not N(t), deliveries, free fleet or an operating network', 'Full primary carrier ranking remains unavailable'],
    'not_run': ['independent live passenger journey', 'causal business effect', 'personal visual QA', 'full independent source review'],
}
Path(__file__).with_name('digital_final_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(result, ensure_ascii=False))
