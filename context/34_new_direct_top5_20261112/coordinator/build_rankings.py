#!/usr/bin/env python3
"""Presentation of existing model rows; no new demand or economic model."""
from pathlib import Path
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
CALC = STUDY / 'calculation'


def read(name):
    with (CALC / name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def write(name, rows):
    with (HERE / name).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    programmes = {(r['programme'], r['scenario'], r['adjacent_case']): r
                  for r in read('programme_comparison.csv')}
    candidates = [r for r in read('candidate_comparison.csv')
                  if r['base_noadj_delta_month'] != 'NULL' and r['queue_group'] != 'LOW_EVIDENCE_QUEUE']
    full = sorted(candidates, key=lambda r: (-float(r['base_with_adjacent_delta_month']), r['pair']))
    stress = sorted(candidates, key=lambda r: (-float(r['base_noadj_delta_month']), r['pair']))
    full_ranks = {r['pair']: i for i, r in enumerate(full, 1)}
    stress_ranks = {r['pair']: i for i, r in enumerate(stress, 1)}
    rows = []
    for r in full:
        name = r['pair']
        values = {(sc, case): programmes[name, sc, case]['known_P_minus_KEEP_month']
                  for sc in ('base', 'cautious')
                  for case in ('P05_ADJACENT_PRIOR', 'NO_UNCONFIRMED_REVENUE')}
        rows.append(dict(pair=name, full_prior_rank=full_ranks[name], asymmetric_stress_rank=stress_ranks[name],
            base_full_prior_RUB=values['base', 'P05_ADJACENT_PRIOR'],
            cautious_full_prior_RUB=values['cautious', 'P05_ADJACENT_PRIOR'],
            base_asymmetric_stress_RUB=values['base', 'NO_UNCONFIRMED_REVENUE'],
            cautious_asymmetric_stress_RUB=values['cautious', 'NO_UNCONFIRMED_REVENUE'],
            classification=r['classification'], qualified_new_route=r['qualified_new_route'],
            ops_status=r['ops_queue'], unit='constant RUB2026 per full February2027',
            scope='P-minus-KEEP before unknown F/outside own-RW/donor losses; both demand assumptions unobserved',
            stress_warning='Asymmetric revenue removal; not a uniform realistic base across rotations'))
    write('rankings_both_assumptions.csv', rows)
    write('top5_full_prior.csv', rows[:5])
    write('top5_asymmetric_stress.csv', sorted(rows, key=lambda r: r['asymmetric_stress_rank'])[:5])

    ledger = read('programme_ledger.csv')
    bridge = []
    for programme in ('AER1', 'AER2'):
        for scenario in ('base', 'cautious'):
            matched = [r for r in ledger if r['programme'] == programme and r['scenario'] == scenario
                       and r['adjacent_case'] == 'P05_ADJACENT_PRIOR']
            def delta(groups):
                return sum(float(r['contribution_month']) * (1 if r['side'] == 'P' else -1)
                           for r in matched if r['group'] in groups)
            new = delta({'NEW_PAIR', 'ADJACENT'})
            donor = delta({'DONOR'})
            retained = delta({'RETAINED_OLD_RW'})
            total = float(programmes[programme, scenario, 'P05_ADJACENT_PRIOR']['known_P_minus_KEEP_month'])
            assert abs(new + donor + retained - total) < 1e-5
            bridge.append(dict(programme=programme, scenario=scenario,
                new_flight_contribution_RUB=new, donor_contribution_change_RUB=donor,
                retained_contribution_change_RUB=retained, total_scoped_delta_RUB=total,
                support=0, cargo=0, actual_donor='UNKNOWN', full_profit='UNKNOWN',
                source='calculation/programme_ledger.csv', unit='constant RUB2026 per February2027'))
    write('AER_result_bridge.csv', bridge)

    before = json.loads((HERE / 'before_review_fix_hashes.json').read_text())
    after = {name: hashlib.sha256((CALC / name).read_bytes()).hexdigest() for name in before}
    assert before == after, 'A numerical artifact changed during explanatory fixes'
    receipt = dict(review_verdict='CHANGES', explanatory_findings_addressed=['R1', 'R2'],
        generator_fix_persists_on_rebuild=True, numerical_artifacts_byte_identical=len(before),
        full_prior_top5=[r['pair'] for r in full[:5]],
        asymmetric_stress_top5=[r['pair'] for r in stress[:5]],
        second_independent_acceptance_claimed=False, qualified_new_routes=0,
        no_launch_approved=True, cancellation_control='separate targeted calculation pending')
    (HERE / 'review_fix_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
