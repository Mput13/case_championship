#!/usr/bin/env python3
"""Model route unions and explicit symbolic full-budget completion."""
import collections
import itertools
import json
import common_demand as m

OUT=m.ROOT/'runs/final_variants_v1'


def main():
    contract=json.loads((m.ROOT/'final_variant_contract.json').read_text())
    rs=m.rows(m.SRC/'21_team_proposals/comparison.csv')
    flights=m.rows(m.SRC/'17_aircraft_route_review/model/flights.csv')
    source={};members=[]
    for r in rs:
        if r['scenario']!='base':continue
        n=r['network'];key=r['source_profile'],r['source_network']
        ff=[f for f in flights if(f['profile'],f['network'])==key]
        assert len(ff)==len({f['id']for f in ff})
        pairs={m.pair(f['origin'],f['destination'])for f in ff}
        assert not any('MOW'in p for p in pairs)
        source[n]=dict(pairs=pairs,flights=ff,working=int(r['active_allocated']),source_profile=key[0],source_network=key[1])
    rows=[];look={}
    for count in range(1,5):
        for subset in itertools.combinations(sorted(source),count):
            name='+'.join(subset);pairs=set.union(*(source[n]['pairs']for n in subset))
            working=sum(source[n]['working']for n in subset)
            row=dict(portfolio=name,input_set_id=contract['id'],component_count=count,
                     sum_component_pair_counts=sum(len(source[n]['pairs'])for n in subset),unique_model_airport_pairs=len(pairs),
                     duplicate_pair_count_removed=sum(len(source[n]['pairs'])for n in subset)-len(pairs),
                     model_dated_flight_instances=sum(len(source[n]['flights'])for n in subset),
                     airport_pairs=';'.join('-'.join(p)for p in sorted(pairs)),
                     working_allocated=working,reserve_assumption=1,new_UFA_base_count=int(any(n.startswith('H_UFA')for n in subset)),
                     model_8_12_count_gate=8<=len(pairs)<=12,current4_working_gate=working<=4,
                     joint_model_gates_pass=8<=len(pairs)<=12 and working<=4,
                     accepted_operating_routes=None,actual_available_aircraft=None,complete_case_acceptance=False,
                     scope='MODEL_UNION_AND_ASSIGNED_RESOURCE_ONLY; NO_SOURCE_OR_LAUNCH_UPGRADE')
            rows.append(row);look[name]=row
            for p in sorted(pairs):
                producers=[n for n in subset if p in source[n]['pairs']]
                legs=[(n,f)for n in producers for f in source[n]['flights']if m.pair(f['origin'],f['destination'])==p]
                members.append(dict(portfolio=name,airport_a=p[0],airport_b=p[1],component_programs=';'.join(producers),
                                    namespaced_flight_ids=';'.join(n+'|'+f['id']for n,f in legs),dated_flight_instances=len(legs),
                                    source_keys=';'.join(n+'|'+source[n]['source_profile']+'|'+source[n]['source_network']for n in producers),
                                    date_min=min(f['date']for _,f in legs),date_max=max(f['date']for _,f in legs),
                                    operating_acceptance='NOT_ESTABLISHED'))
    assert len(rows)==15
    assert look['H_UFA_4+H_UFA_8']['unique_model_airport_pairs']==8
    assert look['H_UFA_4+H_UFA_8']['sum_component_pair_counts']==12
    for name in ['D_SVX8+H_UFA_4','D_previous_best8+H_UFA_4']:
        assert look[name]['unique_model_airport_pairs']==12 and look[name]['joint_model_gates_pass']
    assert sum(r['joint_model_gates_pass']for r in rows)==5
    budgets=[]
    for r in m.rows(m.ROOT/'runs/portfolio_v2/summary.csv'):
        u=look[r['portfolio']];c=float(r['contribution_before_base_fleet_opportunity'])
        assert int(r['working_required'])==u['working_allocated']
        assert int(r['new_UFA_base_count'])==u['new_UFA_base_count']
        budgets.append(dict(portfolio=r['portfolio'],scenario=r['scenario'],capture_law=r['capture_law'],
                            money_input_set_id=r['input_set_id'],union_input_set_id=contract['id'],
                            money_period=r['numerical_price_period'],contribution_before_base_fleet_opportunity=c,
                            model_airport_pairs=u['unique_model_airport_pairs'],working_allocated=u['working_allocated'],
                            joint_model_gates_pass=u['joint_model_gates_pass'],
                            n_if_every_working_and_one_reserve_are_incremental=u['working_allocated']+1,
                            b_if_new_UFA_base_is_incremental=u['new_UFA_base_count'],
                            full_PnL=None,peak_cash_need=None,
                            required_external_donor_gain_if_excluded_costs_zero=-c,
                            required_donor_gain_general='-C + F_incremental + B_incremental + S_excluded + L_recognized',
                            negative_if_external_donor_zero_and_excluded_costs_nonnegative=c<0,
                            missing='Named donor delta; incremental fixed contracts; launch recognition; dated gross cash; annual seasonality',
                            decision_status='CONDITIONAL_COMPARISON_NO_WINNER'))
    assert len(budgets)==90 and all(r['negative_if_external_donor_zero_and_excluded_costs_nonnegative']for r in budgets)
    status=dict(status='PASS_OWNER_SET_UNION_AND_BUDGET_IDENTITY',portfolio_count=15,joint_count_resource_gates_pass=5,
                budget_rows=90,independent_review='PENDING_NEW_SYNTHESIS_SCOPE',complete_case_acceptance=False,
                routes_are_model_airport_endpoint_pairs=True,observed_market=False,full_budget=False)
    old=m.OUT
    try:
        m.OUT=OUT;m.save('network_union.csv',rows);m.save('network_pair_members.csv',members)
        m.save('budget_conditions.csv',budgets);m.save('validation.json',status)
    finally:m.OUT=old
    print(json.dumps(status))


if __name__=='__main__':main()
