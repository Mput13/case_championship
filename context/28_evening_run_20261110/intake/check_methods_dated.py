#!/usr/bin/env python3
"""Coordinator intake of exact v3: identity, grains and selected arithmetic."""
import csv, datetime as dt, hashlib, io, json, math, subprocess
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
SHA = 'f99d6cd52dcc06995bf984fddd2f057226243b06'
OLD = 'aa7779192d809558e38b1eb9bdfa25913a3afdc8'
ROOT = 'context/28_evening_run_20261110/methods/'
@lru_cache(maxsize=None)
def blob(s, p): return subprocess.check_output(['git', 'show', s + ':' + p])
def data(p): return blob(SHA, ROOT + p)
def obj(p): return json.loads(data(p))
def rows(p): return list(csv.DictReader(io.StringIO(data(p).decode())))
def near(a, b): assert math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-4), (a, b)
manifest = obj('output_manifest.json')['files']
for r in manifest:
    b = data(r['path'])
    assert len(b) == r['bytes'] and hashlib.sha256(b).hexdigest() == r['sha256']
prior = json.loads(blob(OLD, ROOT + 'output_manifest.json'))['files']
preserved, changed = [], []
for r in prior:
    (preserved if data(r['path']) == blob(OLD, ROOT + r['path']) else changed).append(r['path'])
assert set(changed) <= {'README.md', 'handoff.json', 'requests.json', 'output_manifest.json', 'checks/latest.json'}
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
annual = rows('runs/integer_year_v1/annual_comparison.csv')
weekly = rows('runs/integer_year_v1/weekly_allocation.csv')
assert len(annual) == 96 and len({r['case'] for r in annual}) == 96
assert len(weekly) == len({(r['case'], r['week_start']) for r in weekly}) == 2298
sums = defaultdict(lambda: defaultdict(float))
for r in weekly:
    for key in ['dated_flights', 'dated_MCT_contribution', 'capacity_only_contribution', 'transfer_journeys']:
        sums[r['case']][key] += float(r[key])
    assert float(r['primal_dual_gap']) < 1e-4
for r in annual:
    for a, w in [('dated_flights','dated_flights'), ('dated_contribution_rub','dated_MCT_contribution'), ('integer_capacity_only_contribution_rub','capacity_only_contribution'), ('transfer_journeys','transfer_journeys')]:
        near(r[a], sums[r['case']][w])
    assert r['actual_grant'] == r['actual_fleet'] == r['full_pnl'] == ''
markets = rows('runs/integer_year_v1/annual_market_caps.csv')
for r in markets:
    near(float(r['annual_model_OD']) - float(r['local_journeys']) - float(r['transfer_journeys']), r['slack'])
    assert float(r['slack']) >= -1e-6
itins = rows('runs/integer_year_v1/OMS_2028_dated_itineraries.csv')
capacity = rows('runs/integer_year_v1/OMS_2028_capacity.csv')
used = defaultdict(float)
for r in itins:
    assert 60 <= float(r['wait_minutes']) <= 180
    near(float(r['journeys']) * float(r['one_fare_margin']), r['margin'])
    for k in ['inbound_flight', 'outbound_flight']: used[r[k]] += float(r['journeys'])
for r in capacity:
    near(used[r['flight_id']], r['transfer'])
    near(float(r['capacity']) - float(r['local']) - float(r['transfer']), r['residual'])
    assert float(r['residual']) >= -1e-6
sync = obj('runs/synchronised_v1/validation.json')
delta = sync['alternative_contribution_rub_week'] - sync['baseline_contribution_rub_week']
near(delta, sync['delta_before_shift_cost_and_external_loss'])
near(delta / sync['shifted_flight_hours'], sync['max_shift_rub_per_flight_hour_at_zero_external_loss'])
links = rows('runs/joint_products_v1/dated_connection_union.csv')
added = [r for r in links if r['rw_variant'] == 'ADD_SSJ_OMS']
assert len(added) == 4 and {r['date'] for r in added} == {'2027-07-05', '2027-07-08'}
assert all(r['eligible'] == 'False' and not r['feed_flight'] for r in added)
joint = rows('runs/joint_products_v1/joint_frontier.csv')
for r in joint:
    v = float(r['C31_ceiling_before_Tu_K_and_old_Tu_donor']) + float(r['C35_contribution_after_partner_and_listed_own_loss']) - float(r['Tu_old_mission_loss_probe'])
    near(v, r['maximum_Tu_allin_plus_K_at_given_donor'])
    near(v - float(r['Tu_allin_new_cost_probe']), r['conditional_joint_before_K_and_other_network'])
    assert float(r['partner_reserved_segments']) == 160 and r['actual_joint_result'] == 'UNKNOWN'
result = {'subject_sha': SHA, 'status': 'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING',
          'checks': {'output_hashes': len(manifest), 'copied_input_receipt_hashes': receipt_count,
                     'prior_files_byte_identical': len(preserved), 'prior_changed': changed,
                     'annual_cases': len(annual), 'weekly_aggregation_rows': len(weekly),
                     'annual_OD_bound_rows': len(markets), 'OMS_itineraries_two_seats_one_margin': len(itins),
                     'OMS_capacity_rows': len(capacity), 'C31_no_same_date_feed_rows': len(added),
                     'joint_budget_rows': len(joint)},
          'not_run': ['independent LP, timetable and tail-continuity replay', 'physical dispatch and market acceptance',
                      'joint source-model demand validity', 'global bank or network optimisation', 'actual full PnL and cash'],
          'qualifications': ['Fixed timetable result not all-hub impossibility', 'No automatic annualisation of bounded retime',
                             'C31 one week plus complete C35 contract; own-feed is a different alternative',
                             'Historical owner support not future award; final Sol independent reviews still separate']}
Path(__file__).with_name('methods_dated_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
