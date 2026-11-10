#!/usr/bin/env python3
"""Frontier review and new synthesis event; v5/v6 snapshots stay immutable."""
import common_demand as m


def main():
    rows=m.rows(m.ROOT/'runs/admission_v2/acceptance_matrix.csv')
    for r in rows:
        if r['artifact']=='hypothesis_frontier':
            r.update(review_commit='58a02028e062b1abd803d99e19f630b75ec80657',verdict='APPROVE_SCOPED_EXACT_519998',
                     current_derivative='62independent calendar/capacity/mechanical checks;35preserved/32untested; original sourceHOLD retained',
                     does_not_approve='source/paidmarket/actualresource/fullbudget/MR10corrections/final8-12choice')
        if r['artifact']=='methods-allocation-and-final-variants-v6':
            r.update(input_commit='ba9f6b85b4f8c9847948ae428ef3fbcfca9e2009',verdict='MR12_RUNNING_EXACT_ba9f',
                     current_derivative='Root432hashes/327oldbytes/48dual arithmetic/15unions/90identities; independent primal/source semantics pending')
    rows.append(dict(artifact='methods-finite-budget-choice-and-model-projection-v7',input_commit='EXACT_COMMIT_FROM_DELIVERY',review_commit='',
                     verdict='OWNER_CHECKS_ONLY_INDEPENDENT_PENDING',scope='18finite affine choice problems/408inequalities;58semantic source projections',
                     current_derivative='Source C local-first only; exactba9input receipt; no LP alpha/threshold inheritance',
                     does_not_approve='completebudget/realcosts/operatingroutes/observedOD/teamselection/globaloptimum'))
    old=m.OUT
    try:
        m.OUT=m.ROOT/'runs/admission_v3';m.save('acceptance_matrix.csv',rows)
        m.save('status.json',dict(status='NEW_FRONTIER_AND_SYNTHESIS_EVENT',historical_v5_v6_unchanged=True,
                                 original_primary='CHANGES',original_cost='CHANGES',delay_holds=4,clock_holds=12,
                                 frontier_scope='calendar/capacity/mechanical only',untested_hypotheses=32,
                                 independent_v7='PENDING'))
    finally:m.OUT=old


if __name__=='__main__':main()
