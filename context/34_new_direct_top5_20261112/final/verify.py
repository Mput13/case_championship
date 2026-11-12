#!/usr/bin/env python3
"""Verify final views and optional full rebuild. No network, Git mutation or calibration."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def run(path):
    result = subprocess.run([sys.executable, '-B', str(path)], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def artifacts():
    return {str(path.relative_to(STUDY)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [STUDY/'RESULTS.md', *HERE.iterdir()]
            if path.is_file() and path.name != 'validation.json'}


def main():
    rebuild = []
    if '--rebuild' in sys.argv:
        rebuild.append(run(STUDY/'calculation/verify.py'))
        rebuild.append(run(STUDY/'cancellation_control/verify.py'))
    before = None
    for _ in range(2):
        run(HERE/'build_summary.py')
        now = artifacts()
        assert before is None or before == now, 'Final views are not deterministic'
        before = now
    parent = run(STUDY/'coordinator/check_cancellation.py')
    data = json.loads((HERE/'DATA.json').read_text())
    assert data['qualified_new_routes'] == 0
    assert data['candidates'] == read(STUDY/'coordinator/rankings_both_assumptions.csv')
    assert data['programmes'] == read(STUDY/'calculation/programme_comparison.csv')
    assert data['controls'] == read(STUDY/'cancellation_control/comparison.csv')
    assert len(read(HERE/'AER_WINDOW_DECISION.csv')) == 6
    assert all(r['confirmed_slot'] == r['observed_clock_price'] == 'UNKNOWN'
               for r in read(HERE/'AER_WINDOW_DECISION.csv'))
    for row in data['price_boundaries']:
        source = next(r for r in data['controls'] if r['programme'] == 'AER1'
                      and r['scenario'] == row['scenario'] and r['adjacent_case'] == 'P05_ADJACENT_PRIOR')
        assert abs(row['new_flight_cost_month_RUB'] - float(source['new_flights_avoidable_cost_delta_month'])) < 1e-6
        assert abs(row['required_net_at_model_quantity_RUB'] * row['model_paid_journeys_month'] - row['new_flight_cost_month_RUB']) < 1e-6
        assert row['actual_competitor_fare'] == row['actual_net_RW_yield'] == 'UNKNOWN'
    assert data['price_boundaries'][1]['raw_max_net_discount_vs_model_reference_RUB'] < 0
    chart = json.loads((HERE/'CHART_DATA.json').read_text())
    assert chart['candidates'] == data['candidates']
    assert chart['controls'] == [{key:row[key] for key in ('programme','scenario','adjacent_case',
        'known_P_minus_KEEP_month','diagnostic_8BH_failures')} for row in data['controls']]
    inline = re.search(r'<script type="application/json" id="summary-data">(.*?)</script>',
                       (HERE/'COMPARISON.html').read_text(), re.S)
    assert inline and json.loads(inline.group(1)) == chart
    for path in (STUDY/'RESULTS.md', HERE/'THREE_PROGRAMMES.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if '://' not in link and not link.startswith('#'):
                assert (path.parent/link.split('#')[0]).exists(), (str(path), link)
    assert all(row['max_retained_departure_delay_min'] >= 0 for row in data['delays'])
    golden = json.loads((STUDY/'coordinator/before_review_fix_hashes.json').read_text())
    assert all(hashlib.sha256((STUDY/'calculation'/name).read_bytes()).hexdigest() == value
               for name,value in golden.items())
    receipt = dict(status='PASS_FINAL_VIEWS_WITH_DECLARED_MODEL_LIMITATIONS', qualified_new_routes=0,
        candidate_rows=len(data['candidates']), control_rows=len(data['controls']),
        deterministic_view_builds=2, original_numerical_artifacts_unchanged=len(golden),
        historical_independent_review='CHANGES; R1/R2 explanatory fixes applied',
        extra_cancellation_review_scope='coordinator ledger/inventory checks, not second Astra acceptance',
        parent_check=json.loads(parent), full_rebuild_runs=rebuild,
        actual_demand_fare_dispatch_profit_verified=False, actual_launch_approved=False)
    (HERE/'validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
