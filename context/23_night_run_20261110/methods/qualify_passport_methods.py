#!/usr/bin/env python3
"""Append methods qualifications to the exact passport owner snapshot."""
import json
import common_demand as m

PASSPORT='46fd52db073cffc46a598f44489d0761c6853410'
UPDATES={
 'R01':('Finite conditional choices now explicit; no team-selected profitable action or observed share effect.','budget_choice_readout.md;model_comparison.md'),
 'R06':('C/N controlled demand recipe on Ciri dated supply; not whole-model contest. Annual Nastya money remains separate.','model_comparison.md;runs/final_model_projection_v1/source_results.csv'),
 'R07':('Gross journeys, segments and own migration distinguished. Annual company increment and compatible denominator remain UNKNOWN.','model_comparison.md'),
 'R08':('Source base/cautious retained; fixed cautious-product upper bounds negative. Stress axes are not empirical probabilities.','budget_readout.md;common_comparison_readout.md'),
 'R09':('Exact MR02 units and source limits retained. New fixed-offer LP MR12 scoped; no realized fares or operating rates established.','decision_conditions.md;inputs/cost-kover-001/findings.md'),
 'R10':('Current portfolios have dated model pairs and weekly accounting; annual per-city-pair demand/seasonality not supplied by week multiplication.','runs/final_variants_v1/network_pair_members.csv;model_comparison.md'),
 'R11':('MR12 accepts15model airport-pair unions:five satisfy8-12pair/4working gates, including two12pair mixes. City-to-airport definition, selected operating network and budget still require resolution.','runs/final_variants_v1/network_union.csv;inputs/allocation-review-001/report.md'),
 'R12':('MR09 model-hour/calendar checks andMR12allocated labels do not prove actual aircraft. Conditional future resource and delayed delivery remain separate.','runs/resource_v1/resource_envelopes.csv;model_comparison.md'),
 'R13':('Two12pair mixed candidates require3/4working labels with one assumed reserve; jointD/own-cap ledgers checkedMR11. AllsourceC contributions negative before excluded costs.','runs/portfolio_v2/summary.csv;runs/final_variants_v1/budget_conditions.csv'),
 'R14':('Step gates:dated commercial product/resource, bounded pilot, then jointnetwork and fullbudget. No-kover and fleet-delay branches retained; date of lifting restrictions UNKNOWN.','model_comparison.md;decision_conditions.md'),
 'R18':('Pinned source/common/LP/finitebudget recipes available; v7domain completeness underMR13, no moving input use.','reproduce.md;budget_choice_contract.json'),
 'A01':('MR11f7a andMR12ba9 scoped passes. Changed input must pass new key/hash/oracle admission; old coverage check alone accepts a duplicateN mutation.','inputs/integration-review-001/findings.json;runs/input_admission_v1/checks.json'),
 'A02':('FullPnL/cashNULL; namedexternal donor and incrementalF/B/support/launch boundaries explicit. Negative actions retainKEEPdelta0 comparator.','decision_conditions.md;budget_choice_readout.md'),
 'A03':('Local-first alpha/scalebounds, fixed-offer objectives andfiniteF/Bchoice domains are distinct. MR12 accepts exactLPcases; MR13checks exactv7 only.','model_comparison.md;budget_choice_readout.md'),
 'A04':('MR10scoped87ee epoch/gating andMR11f7a interaction approved. FourdelayHOLD and UNKNOWNalternative recovery remain; no final cash/dispatch acceptance.','inputs/correction-review-001/handoff.json;inputs/integration-review-001/handoff.json'),
 'A05':('Newcurrentevents forMR10/MR11/MR12/frontierreview; original17b/afadeeCHANGES and12clockholds preserved. Passport ownas-of pending text is immutable.','runs/admission_v4/acceptance_matrix.csv')
}


def main():
    requirements=m.rows(m.ROOT/'inputs/passport-001/requirements_evidence.csv')
    claims=m.rows(m.ROOT/'inputs/passport-001/claims.csv')
    assert len(requirements)==len({r['requirement_id']for r in requirements})==26
    assert len(claims)==len({r['claim_id']for r in claims})==33
    req=[];qualified=[]
    for r in requirements:
        addition,links=UPDATES.get(r['requirement_id'],('No additional methods qualification; retain exact passport owner scope.',''))
        req.append(dict(passport_commit=PASSPORT,passport_requirement_id=r['requirement_id'],
                        original_kind=r['requirement_kind'],original_requirement=r['requirement_paraphrase'],
                        original_available_result=r['available_result'],original_gap=r['gap'],
                        methods_addendum=addition,methods_evidence=links,
                        requirement_fully_satisfied_by_this_addendum=False,passport_independent_review='PENDING'))
    for r in claims:
        tag='ORIGINAL_SCOPE_RETAINED';wording='';scope='No blanket promotion of original source/market/budget acceptance.'
        if r['claim_id']=='C12':
            tag='NEW_CURRENT_QUALIFICATION_EVENT_NOT_REWRITE'
            wording='После cutoff паспорта получены отдельные APPROVE_SCOPED: MR10 для metadata/timebase corrections, MR11 для exact methods f7a, FRONTIER_REVIEW для календарных/механических границ exact519998. Они не принимают реальные продажи, парк или полный бюджет.'
        if r['claim_id']=='S03':
            tag='PROPOSED_WORDING_PRECISION_NO_NUMERIC_CHANGE'
            wording='При сохранённых тарифах, расходах, собственной миграции и local-first рост сценарного спроса не устраняет отрицательный вклад D_SVX8: при насыщении всех локальных мест он остаётся −449 822,70 RUB/неделю. Для UFA4/UFA8 первые нули C достигаются при множителях2,4617708804/2,9194370052 до исключённых расходов.'
            scope='Clarifies that the saturation limit is not a shortage of demand; fixed local-first only, not the new LP allocator.'
        if r['claim_id']in ['S01','S04']:scope='Source local-first conditions only; do not transfer alpha or budget threshold to changed allocation/input.'
        if r['claim_id']=='X01':scope='Five model count/resource gates now checkedMR12; operating selectednetwork, positive fullbudget andlaunch still not established.'
        if r['claim_id']=='X06':scope='MR10passed corrected snapshot metadata only; absence of card notabsence ofcompetitor, no blanket source acceptance.'
        qualified.append(dict(passport_commit=PASSPORT,passport_claim_id=r['claim_id'],original_group=r['group'],
                              original_wording=r['ready_russian_wording'],original_acceptance_scope=r['acceptance_scope'],
                              qualification_kind=tag,current_wording_proposal=wording,current_scope=scope,
                              original_overwritten=False,passport_independent_review='PENDING'))
    old=m.OUT
    try:
        m.OUT=m.ROOT/'runs/passport_methods_v1';m.save('requirement_addendum.csv',req);m.save('claim_qualifications.csv',qualified)
        m.save('status.json',dict(status='OWNER_CURRENT_METHODS_QUALIFICATIONS_ONLY',passport_commit=PASSPORT,
                                 original_requirements=26,original_claims=33,methods_requirement_addenda=len(UPDATES),
                                 full_requirement_or_market_acceptance=False,originals_unchanged=True,
                                 namespaces='passport_claim_id is not frontier hypothesis Cxx; no short-ID cross join',
                                 independent_review='PENDING'))
    finally:m.OUT=old


if __name__=='__main__':main()
