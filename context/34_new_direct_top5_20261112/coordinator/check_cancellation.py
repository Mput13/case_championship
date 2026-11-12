#!/usr/bin/env python3
"""Coordinator's independent ledger/inventory check; does not recalibrate demand."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
CONTROL = STUDY / 'cancellation_control'


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def close(a, b):
    assert abs(float(a) - float(b)) < 1e-5, (a, b)


def main():
    rows = read(CONTROL / 'comparison.csv')
    ledger = read(CONTROL / 'ledger.csv')
    flights = read(CONTROL / 'flights.csv')
    pairs = read(CONTROL / 'pairwise_thresholds.csv')
    source = {(r['programme'], r['scenario'], r['adjacent_case']): r
              for r in read(STUDY / 'calculation/programme_comparison.csv')}
    current = {(r['programme'], r['scenario'], r['adjacent_case']): r for r in rows}
    assert len(current) == len(rows) == 24
    for row in rows:
        group = [r for r in ledger if all(r[k] == row[k] for k in ('programme', 'scenario', 'adjacent_case'))]
        contributions = {side: sum(float(r['net_revenue_month']) - float(r['avoidable_cost_month'])
                                  for r in group if r['side'] == side) for side in ('P', 'KEEP')}
        close(contributions['P'] - contributions['KEEP'], row['known_P_minus_KEEP_month'])
        close(float(row['known_P_minus_KEEP_month']) / 4, row['known_P_minus_KEEP_week'])
        assert all(r['donor_deducted_again'] == 'False' for r in group)
        for name in ('cash', 'full_PnL', 'actual_D', 'actual_fixed_parking', 'actual_cancellation_contracts'):
            assert row[name] == 'NULL'
        assert all(float(row[name]) == 0 for name in ('fuel_support', 'route_grant', 'cargo_main'))
        if row['programme'] in ('CANCEL_TUE_KEEP_FRI', 'CANCEL_BOTH'):
            close(row['new_pair_journeys_month'], 0)
            close(row['new_flights_net_revenue_delta_month'], 0)
        else:
            original = source[row['programme'], row['scenario'], row['adjacent_case']]
            close(row['known_P_minus_KEEP_month'], original['known_P_minus_KEEP_month'])

    inventories = defaultdict(list)
    for row in flights:
        assert row['tail'] == 'E1' and row['origin'] != row['destination']
        dep, arr = datetime.fromisoformat(row['departure_utc']), datetime.fromisoformat(row['arrival_utc'])
        close((arr - dep).total_seconds() / 60, row['block_minutes'])
        inventories[row['programme'], row['side']].append(row)
    baseline = None
    for (programme, side), group in inventories.items():
        ordered = sorted(group, key=lambda r: r['departure_utc'])
        assert ordered[0]['origin'] == ordered[-1]['destination'] == 'SVX'
        for a, b in zip(ordered, ordered[1:]):
            assert a['destination'] == b['origin']
            assert (datetime.fromisoformat(b['departure_utc']) - datetime.fromisoformat(a['arrival_utc'])).total_seconds() >= 3600
        retained = [r for r in group if r['group'] == 'RETAINED_OLD_RW']
        assert len(retained) == 32
        signature = sorted(tuple(r[k] for k in ('origin', 'destination', 'departure_utc', 'arrival_utc')) for r in group)
        if side == 'KEEP':
            baseline = signature if baseline is None else baseline
            assert signature == baseline
        if side == 'P' and programme.startswith('CANCEL_'):
            assert not any(r['group'] in ('NEW_PAIR', 'ADJACENT') for r in group)
            assert len(group) == (40 if programme == 'CANCEL_TUE_KEEP_FRI' else 32)

    for row in pairs:
        a = current[row['A'], row['scenario'], row['adjacent_case']]
        b = current[row['B'], row['scenario'], row['adjacent_case']]
        close(float(a['known_P_minus_KEEP_month']) - float(b['known_P_minus_KEEP_month']), row['scoped_A_minus_B_month'])
        close(row['scoped_A_minus_B_month'], row['omitted_cost_A_minus_B_tie_threshold_month'])
        if row['A'] in ('AER1', 'AER2') and row['B'].startswith('CANCEL_'):
            close(row['donor_contribution_difference_month'], 0)
            close(row['retained_contribution_difference_month'], 0)
            close(row['new_flights_contribution_difference_month'], row['scoped_A_minus_B_month'])

    protected = json.loads((ROOT / 'context/33_svx_aer_launch_case_20261112/protected_files.json').read_text())
    assert len(protected) == 1190
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected for name, expected in protected.items())
    receipt = dict(status='PASS_SCOPED_COORDINATOR_CHECK', comparison_rows=len(rows), ledger_rows=len(ledger),
        physical_rows=len(flights), pairwise_rows=len(pairs), identical_KEEP_inventories=True,
        retained_per_inventory=32, old_protected_files=1190, actual_demand_verified=False,
        full_profit_verified=False, dispatch_approved=False, independent_Astra_scope='original P34; this extra control checked by coordinator')
    (HERE / 'cancellation_parent_check.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
