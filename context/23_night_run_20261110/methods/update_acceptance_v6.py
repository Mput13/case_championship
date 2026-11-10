#!/usr/bin/env python3
"""New acceptance snapshot; never rewrite the published v5 projection."""
import json
import common_demand as m


def main():
    rows=m.rows(m.ROOT/'runs/admission_v1/acceptance_matrix.csv')
    review='4604059a675b0be410ff46685ec77fa1dc20933a'
    for r in rows:
        a=r['artifact']
        if a=='methods-strategy-v4':
            r.update(review_commit='0cc043484147cb9f3a23a3d3d2aea9b4a6ce9ed9',verdict='APPROVE_SCOPED_EXACT_c24',
                     current_derivative='MR09 independently repeated mixed/resource/product and4to8airborne witness; old holds retained')
        if a=='primary_lineage_correction':
            r.update(review_commit=review,verdict='APPROVE_SCOPED_DERIVATIVE_METADATA_ONLY',
                     current_derivative='MR10 A passed snapshot FK and value preservation; original17bCHANGES retained',
                     does_not_approve='newrawparse/market/dispatch;12clockholds remain')
        if a=='cost_kover_timebase_correction':
            r.update(review_commit=review,verdict='APPROVE_SCOPED_DERIVATIVE_EPOCH_AND_GATING_ONLY',
                     current_derivative='MR10 B passed epoch/affectedsets/40conservation/4held; originalafadeeCHANGES retained',
                     does_not_approve='alternative recovery feasibility/served-all delay/actualcash/new demand recipes')
        if a=='methods-integration-v5':
            r.update(input_commit='f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9',verdict='MR11_RUNNING_EXACT_f7a',
                     current_derivative='Root checked370hashes and16summary+8delta identities; new independent scope pending')
    rows.append(dict(artifact='hypothesis_frontier',input_commit='519998ed8c97ce5499f356a6d0f81558c7f6ee14',review_commit='',
                     verdict='OWNER_ONLY_FRONTIER_REVIEW_PENDING',scope='35inventory andHF01/HF07/HF14 finite experiments',
                     current_derivative='Separate frozen input; no numeric economic substitution',
                     does_not_approve='paid demand/complete budget/free aircraft/operating network'))
    rows.append(dict(artifact='methods-allocation-and-final-variants-v6',input_commit='EXACT_COMMIT_FROM_DELIVERY',review_commit='',
                     verdict='OWNER_CHECKS_ONLY_INDEPENDENT_PENDING',scope='16fixed-offer cases×3objectives;15routeunions/90budgetconditions',
                     current_derivative='New contracts and outputs; historical scoped passes unchanged',
                     does_not_approve='globalnetworkoptimum/observedOD/completebudget/operatingroutes/teamobjective'))
    context=m.rows(m.ROOT/'runs/admission_v1/market_source_qualification.csv')
    for r in context:
        if r['current_source_input']=='primary-lineage-002':
            r['current_lineage_scope']='MR10_APPROVE_SCOPED_CORRECTED_SNAPSHOT_METADATA_ONLY'
            r['new_independent_correction_review']=review
    old=m.OUT
    try:
        m.OUT=m.ROOT/'runs/admission_v2';m.save('acceptance_matrix.csv',rows);m.save('market_source_qualification.csv',context)
        m.save('status.json',dict(status='NEW_ACCEPTANCE_EVENT_SNAPSHOT',historical_v5_unchanged=True,
                                 original_primary='CHANGES',original_cost='CHANGES',delay_holds=4,clock_holds=12,
                                 source_market_dispatch_promotion=False,independent_v6='PENDING'))
    finally:m.OUT=old


if __name__=='__main__':main()
