#!/usr/bin/env python3
"""Coordinator intake of exact v4. Does not replace independent synthesis review."""
import csv, hashlib, io, json, math, subprocess
from functools import lru_cache
from pathlib import Path

SHA = '9f0b5d25af720107e99e209e1c69b098497358be'
OLD = 'f99d6cd52dcc06995bf984fddd2f057226243b06'
ROOT = 'context/28_evening_run_20261110/methods/'
@lru_cache(maxsize=None)
def blob(s, p): return subprocess.check_output(['git', 'show', s + ':' + p])
def data(p): return blob(SHA, ROOT + p)
def obj(p): return json.loads(data(p))
def rows(p): return list(csv.DictReader(io.StringIO(data(p).decode())))
def near(a, b): assert math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-5), (a, b)

manifest = obj('output_manifest.json')['files']
assert len(manifest) == len({r['path'] for r in manifest}) == 480
for r in manifest:
    b = data(r['path'])
    assert len(b) == r['bytes'] and hashlib.sha256(b).hexdigest() == r['sha256']
prior = json.loads(blob(OLD, ROOT + 'output_manifest.json'))['files']
excluded = {'handoff.json', 'requests.json', 'progress.md', 'README.md'}
preserved = [r['path'] for r in prior if r['path'] not in excluded]
assert len(preserved) == 442
assert all(data(p) == blob(OLD, ROOT+p) for p in preserved)
receipt_count = 0
for item in manifest:
    path = item['path']
    if not (path.startswith('inputs/') and path.endswith('/receipt.json') and path.count('/') == 2): continue
    receipt = obj(path)
    for r in receipt['files']:
        commit = r.get('source_commit', receipt.get('source_commit', receipt.get('commit')))
        prefix = str(Path(path).parent) + '/'
        p = r['path'] if r['path'].startswith(prefix) else prefix + r['path']
        b = data(p)
        assert b == blob(commit, r['source_path'])
        assert len(b) == r['bytes'] and hashlib.sha256(b).hexdigest() == r['sha256']
        receipt_count += 1

options = rows('strategy/finite_options.csv')
routes = rows('strategy/option_routes.csv')
assert len(options) == len({r['option'] for r in options}) == 24
for r in options:
    rr = [x for x in routes if x['option'] == r['option']]
    pairs = {tuple(sorted((x['origin'], x['destination']))) for x in rr}
    assert len(pairs) == int(r['model_endpoint_pairs']) and 8 <= len(pairs) <= 12
    assert int(r['total_planning_tails']) == int(r['constructed_working_tails']) + 1
    assert r['actual_resource_market_fullPnL'] == 'UNKNOWN'
    assert all(not x['date'] and x['calendar_basis'].startswith('AUTHOR') for x in rr)
calendar = rows('runs/annual_v1/aircraft_calendar_daily.csv')
readiness = rows('strategy/finite_option_readiness.csv')
assert len(readiness) == len({(r['option'], r['branch'], r['year']) for r in readiness}) == 144
for r in readiness:
    dates = [x['date'] for x in calendar if x['branch'] == r['branch'] and x['availability'] == '14D_GROUNDING_STRESS' and x['date'].startswith(r['year']) and int(x['working_new']) >= int(r['required_working_tails'])]
    assert len(dates) == int(r['days_with_aggregate_resource'])
    assert (min(dates) if dates else '') == r['first_date_with_resource']
    assert (max(dates) if dates else '') == r['last_date_with_resource']

net = obj('runs/selection_v1/networks.json')
mixed = rows('strategy/mixed11_budget.csv')
mixed_routes = rows('strategy/mixed11_routes.csv')
fixed = rows('inputs/network_b471/v2/outputs/fixed_routes.csv')
demands = rows('inputs/network_b471/v2/outputs/demand_fare_inputs.csv')
examples = []
for s in ('base', 'cautious'):
    a = net[f'AUTHOR_52_48_CONCENTRATED/{s}/OMS/GREEDY/cap4']['assumptions']
    source = [r for r in fixed if r['scenario'] == s and r['network'] in ('KUF4', 'OMS8')]
    target = next(r for r in mixed if r['scenario'] == s)
    rr = [r for r in mixed_routes if r['scenario'] == s]
    assert len(source) == 12 and len(rr) == 11
    shared = next(r for r in rr if {r['origin'], r['destination']} == {'KUF', 'OMS'})
    d = next(r for r in demands if r['scenario'] == s and r['origin'] == 'KUF' and r['destination'] == 'OMS')
    assert d['direct_in_author_input'] == 'False'
    q2 = 2 * float(d['diagnostic_week_od_one_direction']) * a['capture_open'] * (-math.expm1(-2/a['capture_freq_scale']))
    q4 = 2 * float(d['diagnostic_week_od_one_direction']) * a['capture_open'] * (-math.expm1(-4/a['capture_freq_scale']))
    near(q4, q2 * (1 + math.exp(-2/a['capture_freq_scale'])))
    assert q4 <= 2 * float(d['diagnostic_week_od_one_direction'])
    assert q4 <= 2 * 4 * a['seats'] * a['lf_max']
    near(shared['naive_independent_local_journeys'], 2*q2)
    near(shared['pooled_local_journeys'], q4)
    delta = (q4-2*q2) * (float(d['net_fare_rub'])-a['pax_cost_rub'])
    near(shared['contribution_correction'], delta)
    assert all(float(r['contribution_correction']) == 0 for r in rr if r is not shared)
    naive = sum(float(r['local_only_contribution_rub_week']) for r in source)
    near(target['naive_sum_contribution'], naive)
    near(target['shared_market_corrected_contribution'], naive+delta)
    near(target['block_hours_week'], sum(float(r['block_hours_week']) for r in source))
    near(target['flights_week'], sum(float(r['flights_week']) for r in source))
    assert target['flights_week'] == '48' and target['actual_fleet_fullPnL'] == 'UNKNOWN'
    examples.append(dict(scenario=s, q2=q2, q4=q4, shared_money_delta=delta, total=naive+delta))

columns = {'C01':'delta_contribution_rub_week', 'C03':'Kmax_extra_KUF_base_minus_deployment_lodging_rub_week', 'C04':'contribution_rub_week', 'C07':'delta_contribution_rub_week', 'C33':'delta_contribution_rub_week', 'C10':'minimum_guarantee_return_per_person', 'C14':'minimum_package_price_per_person', 'C17':'minimum_summer_paid_people_each_leg', 'C31':'maximum_tu_new_allin_cost_plus_K', 'C35':'maximum_integration_retime_risk_K'}
cards = rows('strategy/hypothesis_decisions.csv')
assert len(cards) == 10 and {r['id'] for r in cards} == set(columns)
source_cells = []
for r in cards:
    assert r['team_accepted'] == 'False' and not r['actual_full_result']
    for s, field in [('base', 'base_value'), ('cautious', 'cautious_value')]:
        matches = [(i+2, x) for i, x in enumerate(rows(r['input_path'])) if x['scenario'] == s and x.get(columns[r['id']]) and math.isclose(float(x[columns[r['id']]]), float(r[field]), rel_tol=1e-12)]
        assert matches, (r['id'], s)
        source_cells.append(dict(id=r['id'], scenario=s, source_sha=r['input_sha'], path=r['input_path'], column=columns[r['id']], matched_lines=[i for i,x in matches], value=r[field]))
queue = rows('strategy/hypothesis_queue35.csv')
assert len(queue) == len({r['id'] for r in queue}) == 35
assert sum(r['evening_status'] == 'RESERVED_NOT_TESTED_THIS_WINDOW' for r in queue) == 25
assert len(rows('strategy/budget_components.csv')) == 21

result = dict(subject_sha=SHA, status='COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING', checks=dict(output_hashes=len(manifest), input_receipt_hashes=receipt_count, previous_files_preserved=len(preserved), finite_options=len(options), route_program_rows=len(routes), resource_gate_rows=len(readiness), card_source_cells=len(source_cells), retained_hypotheses=len(queue)), mixed_examples=examples, source_cells=source_cells, not_run=['independent strategic recommendation review', 'global optimisation or complete dated mixed rotation', 'actual market/awards/fleet/crew/fullPnL/cash'], qualifications=['EV-MR03 remains exactf99', 'Historical support shadow is not future award', 'resource dates are aggregate N(t) gates', 'mixed11 uses shared local market only; no invented transfer sales', '25 reserve not economically rejected'])
Path(__file__).with_name('methods_strategy_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k != 'source_cells'}, ensure_ascii=False))
