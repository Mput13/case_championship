#!/usr/bin/env python3
"""Separate portfolio-v2 run: hard D guard versus proposed pooled capture."""
import collections
import json
import common_demand as m
import portfolio_comparison as portfolio


def main():
    contract=json.loads((m.ROOT/'portfolio_contract.json').read_text())
    contract['id']='CONTEXT21_PORTFOLIO_D_GUARD_V2'
    contract['capture_laws'].insert(0,'D_GUARD_STANDALONE_CLAIMS: preserve component desired claims; one hard directed D budget after leg caps in fixed allocation order')
    contract['scope_delta']='Only hard D guard comparison added; portfolio_v1 outputs and assumptions remain unchanged'
    out=m.ROOT/'runs/portfolio_v2';out.mkdir(parents=True,exist_ok=True)
    contract_path=m.ROOT/'portfolio_guard_contract.json'
    payload=json.dumps(contract,ensure_ascii=False,indent=2)+'\n'
    if contract_path.exists():assert contract_path.read_text()==payload
    else:contract_path.write_text(payload)
    portfolio.main(contract_path,out)
    previous=m.rows(m.ROOT/'runs/portfolio_v1/summary.csv');new=m.rows(out/'summary.csv')
    def key(r):return r['portfolio'],r['scenario'],r['capture_law']
    old={key(r):r for r in previous};deltas=[]
    for r in new:
        if r['capture_law']!='D_GUARD_STANDALONE_CLAIMS':
            for field in ['sold_journeys','segment_pax','gross_revenue','foregone_RW_revenue','flight_variable_cost','contribution_before_base_fleet_opportunity']:
                m.near(r[field],old[key(r)][field],('v1 preserved',key(r),field))
        else:
            delta=float(r['contribution_before_base_fleet_opportunity'])-float(r['additive_component_contribution'])
            m.near(delta,0,('current D-only delta',key(r)))
            q=old[r['portfolio'],r['scenario'],'COUNT_DISTINCT_DEPARTURE_TIMES']
            deltas.append(dict(portfolio=r['portfolio'],scenario=r['scenario'],additive_contribution=float(r['additive_component_contribution']),
                               hard_D_contribution=float(r['contribution_before_base_fleet_opportunity']),hard_D_delta=delta,
                               proposed_Q_contribution=float(q['contribution_before_base_fleet_opportunity']),
                               proposed_Q_minus_D=float(q['contribution_before_base_fleet_opportunity'])-float(r['contribution_before_base_fleet_opportunity']),
                               status='CURRENT_D_CAP_NONBINDING; Q_RESPONSE_IS_SEPARATE_POLICY'))
    # A counterexample checks that the extra branch actually caps an excessive
    # claim, rather than relying only on the current nonbinding source rows.
    offers=[dict(origin='A',destination='B',legs=[str(i)],D=300.,coefficient=.4,can=0.,known=None,
                 fare=100.,oldfare=100.,transfer=False,day=i+1)for i in range(4)]
    cc=[dict(flight_id=str(i),capacity_scenario=100,flight_variable_cost=0)for i in range(4)]
    total,_,_=m.simulate(offers,cc,dict(pax_cost=0),enforce_market_cap=True)
    m.near(total['sold_journeys'],300,'synthetic shared D saturation')
    try:m.simulate(offers,cc,dict(pax_cost=0))
    except AssertionError:uncapped_rejected=True
    else:raise AssertionError('uncapped excessive claims not rejected')
    old_out=m.OUT
    try:
        m.OUT=out;m.save('guard_vs_curve.csv',deltas)
        m.save('guard_validation.json',dict(status='PASS_OWNER',current_portfolio_D_only_cases=len(deltas),all_current_D_deltas_zero=True,
                                            prior_v1_numeric_cases_preserved=len(previous),synthetic_standalone_sold=400,
                                            synthetic_D=300,synthetic_capped_sold=total['sold_journeys'],uncapped_rejected=uncapped_rejected,
                                            independent_review='PENDING_NEW_V2_SCOPE',allocation_policy='fixed source local-first net-margin order; not uniquely optimal'))
    finally:m.OUT=old_out


if __name__=='__main__':main()
