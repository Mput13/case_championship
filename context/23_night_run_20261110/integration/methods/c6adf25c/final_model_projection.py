#!/usr/bin/env python3
"""Readable source-result projection with preserved original run labels."""
import collections
import json
import common_demand as m


def main():
    source=m.rows(m.ROOT/'inputs/model-repair-001/proposed_common_view/evaluation_summary.csv')
    result=[];keys=set()
    proposed={'CORRECTED_FIXED_SELECTION','CORRECTED_RESELECTED','CORRECTED_CLAIM_ALLOCATION'}
    for row,r in enumerate(source,2):
        annual=r['model_id'].startswith('anastasia')
        run=r['run_id']
        if run=='AUTHOR_REPLAY':semantic='AUTHOR_REPLAY'
        elif run=='CORRECTED_MARKET_BOUND_ONLY':semantic='CORRECTED_REPLAY_STRUCTURAL_D_GUARD_CURRENT_DELTA_ZERO'
        else:
            assert run in proposed,run
            semantic='COMMON_COMPARISON_PROPOSED_QF_POLICY_NOT_MANDATORY_REPAIR'
        moneyfield='annual_contribution_before_base_fleet_opportunity_rub'if annual else'contribution_before_base_fleet_opportunity'
        journeyfield='annual_trips'if annual else'sold_journeys'
        segmentfield='annual_segments'if annual else'segment_pax'
        k=r['model_id'],run,r['candidate_id'],r['scenario_id'];assert k not in keys;keys.add(k)
        result.append(dict(model_id=r['model_id'],candidate=r['candidate_id'],scenario=r['scenario_id'],
                           original_run_id=run,original_mode=r['mode'],semantic_mode=semantic,
                           original_source_commit=r['source_commit'],received_package_commit='27740ffea0821aa404ecd1013d1bb141613261f3',
                           source_csv='inputs/model-repair-001/proposed_common_view/evaluation_summary.csv',source_csv_line=row,
                           source_input_set=r['input_set_id'],display_profile=r['profile'],source_profile=r['source_profile'],source_network=r['source_network'],
                           comparison_group='ANASTASIA_ANNUAL_'+r['scenario_id']if annual else'CIRI_CONTEXT21_WEEK_'+r['scenario_id'],
                           period='SYNTHETIC_YEAR_52_WEEKS'if annual and r['scenario_id']=='base'else'SYNTHETIC_YEAR_48_WEEKS'if annual else'2026-12-07/2026-12-13',
                           contribution_rub=r[moneyfield],source_money_field=moneyfield,endpoint_journeys=r[journeyfield],passenger_segments=r[segmentfield],
                           money_definition=r['money_definition'],working_ceiling=9 if annual else 4,reserve_ceiling=1,
                           full_budget=None,actual_paid_OD=None,net_new_RW_observed=None,
                           numerical_cross_group_comparison_allowed=False,
                           review='model_repair_review445a5d52_SCOPED_REPLAY_AND_CODE_ONLY',
                           policy_acceptance='AGENT_PROPOSAL'if run in proposed else'NOT_TEAM_STRATEGY_ACCEPTANCE'))
        assert result[-1]['contribution_rub']==r[moneyfield]
    assert len(result)==58
    assert collections.Counter(r['semantic_mode']for r in result)=={
        'AUTHOR_REPLAY':20,'CORRECTED_REPLAY_STRUCTURAL_D_GUARD_CURRENT_DELTA_ZERO':2,
        'COMMON_COMPARISON_PROPOSED_QF_POLICY_NOT_MANDATORY_REPAIR':36}
    old=m.OUT
    try:
        m.OUT=m.ROOT/'runs/final_model_projection_v1';m.save('source_results.csv',result)
        m.save('validation.json',dict(status='PASS_OWNER_PROJECTION',rows=58,original_numeric_strings_preserved=True,
                                      author_rows=20,D_guard_rows=2,proposed_QF_rows=36,
                                      original_run_labels_preserved=True,no_cross_group_ranking=True,independent_projection_review='PENDING'))
    finally:m.OUT=old


if __name__=='__main__':main()
