#!/usr/bin/env python3
import common_demand as m


def main():
    rows=m.rows(m.ROOT/'runs/admission_v3/acceptance_matrix.csv')
    for r in rows:
        if r['artifact']=='methods-integration-v5':
            r.update(review_commit='ea2a9626aef75c121f2da7d778b47edce0d571b7',verdict='APPROVE_SCOPED_EXACT_f7a',
                     current_derivative='MR11bounded C/N/adapter/cashfixtures/Dguard pass; duplicateNchangedinput requires newadmission',
                     does_not_approve='changedinputs/observedOD/actualcash/fullbudget/oldsourceorcorrections')
        if r['artifact']=='methods-allocation-and-final-variants-v6':
            r.update(review_commit='5e9b4765c60f4cc7ecb1d1a4dad20d3996235cab',verdict='APPROVE_SCOPED_EXACT_ba9f_A_AND_B',
                     current_derivative='MR12P3O01 correctedtwo prose rounding values only; CSV/calculations immutable',
                     does_not_approve='actualmarket/fleet/fullbudget/launch; newv7choice domains')
        if r['artifact']=='methods-finite-budget-choice-and-model-projection-v7':
            r.update(input_commit='c6adf25cc39712cbfdd2d34acdabd31366b33bce',verdict='MR13_RUNNING_EXACT_c6ad',
                     current_derivative='Root457hashes/381priorbytes/408affine/201witness checks; source/choicecompleteness independentpending')
    rows.append(dict(artifact='passport_bridge',input_commit='46fd52db073cffc46a598f44489d0761c6853410',review_commit='',
                     verdict='OWNER_SYNTHESIS_INDEPENDENT_PENDING',scope='26requirements/33claims; no neweconomic calculation',
                     current_derivative='Originalas-of pending preserved; methods supplies separate currentevent projection',
                     does_not_approve='teamchoices/fullbudget/actualfleet/selected8-12network/submission'))
    rows.append(dict(artifact='methods-input-admission-and-passport-v8',input_commit='EXACT_COMMIT_FROM_DELIVERY',review_commit='',
                     verdict='OWNER_CHECKS_ONLY_INDEPENDENT_PENDING',scope='Read-only admission ofexactf7a data pluscurrentpassportqualifications',
                     current_derivative='384uniquekeys/12summarygroups/160independentoracle rows;7mutations rejected; MR12proseonlyfixed',
                     does_not_approve='newinputsets/newnumericresults/universalvalidator/wholepassportacceptance'))
    old=m.OUT
    try:
        m.OUT=m.ROOT/'runs/admission_v4';m.save('acceptance_matrix.csv',rows)
        m.save('status.json',dict(status='NEW_MR11_MR12_PASSPORT_EVENTS',historical_snapshots_unchanged=True,
                                 original_primary='CHANGES',original_cost='CHANGES',delay_holds=4,clock_holds=12,
                                 new_inputs_automatically_admitted=False,independent_v8='PENDING'))
    finally:m.OUT=old


if __name__=='__main__':main()
