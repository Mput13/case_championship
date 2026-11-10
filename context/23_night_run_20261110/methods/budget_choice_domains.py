#!/usr/bin/env python3
"""Exact finite affine comparisons with explicit choice constraints."""
import hashlib
import json
import subprocess
from scipy.optimize import linprog
import common_demand as m

OUT=m.ROOT/'runs/budget_choice_v1'


def main():
    contract=json.loads((m.ROOT/'budget_choice_contract.json').read_text())
    input_hashes=[]
    for name in contract['input_tables']:
        path=m.ROOT/name
        source_path=str(path.relative_to(m.ROOT.parents[2]))
        frozen=subprocess.check_output(['git','show',contract['input_commit']+':'+source_path],cwd=m.ROOT.parents[2])
        assert path.read_bytes()==frozen,('input drift',name)
        input_hashes.append(dict(path=name,source_commit=contract['input_commit'],sha256=hashlib.sha256(frozen).hexdigest()))
    unions={r['portfolio']:r for r in m.rows(m.ROOT/'runs/final_variants_v1/network_union.csv')}
    allrows=m.rows(m.ROOT/'runs/portfolio_v2/summary.csv')
    cases=[];inequalities=[];exclusions=[];witnesses=[]
    for law in sorted({r['capture_law']for r in allrows}):
        for sc in ['base','cautious']:
            for domain in contract['choice_domains']:
                cid=law+'|'+sc+'|'+domain;eligible=[]
                for r in allrows:
                    if r['capture_law']!=law or r['scenario']!=sc:continue
                    n=r['portfolio'];working=int(r['working_required']);base=int(r['new_UFA_base_count'])
                    count=int(unions[n]['unique_model_airport_pairs']);reason=[]
                    if working>4:reason.append('WORKING_LABELS_GT4')
                    if domain!='NO_FINAL_ROUTE_COUNT_GATE'and not 8<=count<=12:reason.append('MODEL_PAIR_COUNT_OUTSIDE8_12')
                    if domain=='FINAL_MODEL_PAIR_COUNT_8_12_AND_NEW_UFA_BASE'and base!=1:reason.append('NO_NEW_UFA_BASE')
                    if reason:exclusions.append(dict(case_id=cid,candidate=n,reason=';'.join(reason),model_pairs=count,working=working))
                    else:eligible.append(dict(name=n,c=float(r['contribution_before_base_fleet_opportunity']),n=working+1,b=base,model_pairs=count))
                assert len(eligible)=={'NO_FINAL_ROUTE_COUNT_GATE':7,'FINAL_MODEL_PAIR_COUNT_8_12':5,'FINAL_MODEL_PAIR_COUNT_8_12_AND_NEW_UFA_BASE':3}[domain]
                for a in eligible:
                    A=[];rhs=[]
                    for b in eligible:
                        if a['name']==b['name']:continue
                        row=[a['n']-b['n'],a['b']-b['b']];bound=a['c']-b['c'];A.append(row);rhs.append(bound)
                        inequalities.append(dict(case_id=cid,candidate=a['name'],alternative=b['name'],
                                                 F_coefficient=row[0],B_coefficient=row[1],rhs_RUB_per_week=bound,
                                                 relation='F_coefficient*F + B_coefficient*B <= rhs',
                                                 excluded_cost_difference_extension='Add O_candidate-O_alternative to left side if not equal',
                                                 money_input_set='CONTEXT21_PORTFOLIO_D_GUARD_V2',decision_status='CONDITIONAL_NO_TEAM_CHOICE'))
                    lp=linprog([1.,1.],A_ub=A,b_ub=rhs,bounds=[(0,None),(0,None)],method='highs')
                    dominators=[b['name']for b in eligible if b['name']!=a['name']and b['n']<=a['n']and b['b']<=a['b']and b['c']>a['c']+1e-6]
                    if lp.success:
                        F,B=map(float,lp.x)
                        assert F>=-1e-7 and B>=-1e-7 and not dominators
                        ja=a['c']-a['n']*F-a['b']*B
                        for b in eligible:
                            jb=b['c']-b['n']*F-b['b']*B
                            assert ja>=jb-1e-5,(cid,a,b,F,B,ja,jb)
                            witnesses.append(dict(case_id=cid,candidate=a['name'],alternative=b['name'],witness_F=F,witness_B=B,
                                                  candidate_adjusted=ja,alternative_adjusted=jb,slack_RUB=ja-jb))
                        assert ja<0
                        state='POSSIBLE_BEST_OR_TIED_WITHIN_ENUMERATED_ACTIONS'
                    else:
                        assert lp.status==2,(cid,a,lp.message)
                        assert dominators,('infeasible without simple dominance proof; investigate',cid,a)
                        F=B=ja=None;state='STRICTLY_DOMINATED_FOR_ALL_NONNEGATIVE_F_B_UNDER_EQUAL_OTHER_TERMS'
                    cases.append(dict(case_id=cid,capture_law=law,scenario=sc,choice_domain=domain,candidate=a['name'],
                                      candidate_count=len(eligible),C=a['c'],n=a['n'],b=a['b'],model_pairs=a['model_pairs'],
                                      state=state,dominators=';'.join(dominators),witness_F=F,witness_B=B,witness_adjusted=ja,
                                      actual_F=None,actual_B=None,full_PnL=None,launch_accepted=False))
    assert len(cases)==90
    # All18 feasible-domain problems have at least one certified best action.
    active={r['case_id']for r in cases if r['witness_F']is not None}
    assert len(active)==18
    # All three capture laws yield the same possible-best identities here;
    # this does not equate their monetary outputs outside the frontier.
    for sc in ['base','cautious']:
        for domain in contract['choice_domains']:
            fronts=[{r['candidate']for r in cases if r['capture_law']==law and r['scenario']==sc and r['choice_domain']==domain and r['witness_F']is not None}for law in sorted({r['capture_law']for r in allrows})]
            assert all(s==fronts[0]for s in fronts)
    penalty_terms=[];penalty_bounds=[]
    for law in sorted({r['capture_law']for r in allrows}):
        for sc in ['base','cautious']:
            baseline=next(r for r in cases if r['capture_law']==law and r['scenario']==sc and r['choice_domain']=='FINAL_MODEL_PAIR_COUNT_8_12'and r['candidate']=='D_previous_best8')
            restricted=[r for r in cases if r['capture_law']==law and r['scenario']==sc and r['choice_domain']=='FINAL_MODEL_PAIR_COUNT_8_12_AND_NEW_UFA_BASE']
            intercepts=[]
            for r in restricted:
                constant=baseline['C']-r['C'];fc=r['n']-baseline['n'];bc=r['b']-baseline['b']
                assert constant>0 and fc>=0 and bc==1
                intercepts.append(constant)
                penalty_terms.append(dict(capture_law=law,scenario=sc,witness_baseline=baseline['candidate'],restricted_candidate=r['candidate'],
                                          baseline_minus_candidate_constant=constant,F_coefficient=fc,B_coefficient=bc,
                                          formula='J_baseline-J_restricted=constant+F_coefficient*F+B_coefficient*B'))
            bound=min(intercepts)
            penalty_bounds.append(dict(capture_law=law,scenario=sc,lower_bound_RUB_per_week_at_B0=bound,additional_B_coefficient=1,
                                       bound='Best_unrestricted_final-J_best_newbase >= lower_bound + B for all F,B>=0',
                                       assumption='Same excluded terms and zero external differences; finite source C universe only',
                                       actual_base_cost=None))
    old=m.OUT
    try:
        m.OUT=OUT;m.save('candidate_domains.csv',cases);m.save('pairwise_inequalities.csv',inequalities)
        m.save('pre_economic_exclusions.csv',exclusions);m.save('feasible_witnesses.csv',witnesses)
        m.save('input_receipt.json',dict(input_set_id=contract['id'],files=input_hashes))
        m.save('new_base_constraint_terms.csv',penalty_terms);m.save('new_base_constraint_floor.csv',penalty_bounds)
        m.save('validation.json',dict(status='PASS_OWNER_FINITE_AFFINE_DOMAINS',choice_problems=18,candidate_domain_rows=len(cases),
                                      pairwise_inequalities=len(inequalities),feasible_best_candidates=sum(r['witness_F']is not None for r in cases),
                                      all_inactive_have_direct_dominance_certificate=True,all_adjusted_actions_negative=True,
                                      capture_law_frontier_identities_equal_in_this_input=True,independent_review='PENDING_NEW_SCOPE'))
    finally:m.OUT=old


if __name__=='__main__':main()
