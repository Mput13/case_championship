#!/usr/bin/env python3
"""Necessary block-hour gates; no conversion of undated flows into schedules."""
import json
import math
import common_demand as m


def main():
    cfg=json.loads((m.SRC/'16_conditional_decision/assumptions.json').read_text())['resource']
    assumptions=m.rows(m.ROOT/'inputs/set001/nastya_2f03/data/assumptions/network.csv')
    ap={r['parameter']:r for r in assumptions}
    source=m.rows(m.ROOT/'inputs/model-repair-001/proposed_common_view/evaluation_summary.csv')
    out=[]
    for r in source:
        if r['model_id']!='anastasia_network_author':continue
        sc=r['scenario_id'];hours=float(r['weekly_block_hours']);daily=float(ap['block_h_per_day'][sc]);working=float(ap['fleet_cap'][sc])-float(ap['spare_aircraft'][sc])
        common_hours=cfg['active_aircraft']*cfg['work_days']*cfg['planning_cap_block_h']
        out.append(dict(model='anastasia',candidate=r['candidate_id'],scenario=sc,weekly_block_hours=hours,
                        author_working_cap=working,author_days=7,author_daily_block_cap=daily,author_aggregate_weekly_cap=working*7*daily,
                        common_working_cap=cfg['active_aircraft'],common_days=cfg['work_days'],common_daily_block_cap=cfg['planning_cap_block_h'],
                        common_aggregate_weekly_cap=common_hours,common_hours_necessary_gate_pass=hours<=common_hours+1e-8,
                        minimum_working_by_hours_only=math.ceil(hours/(cfg['work_days']*cfg['planning_cap_block_h'])),
                        actual_dated_tail_requirement=None,missing_reason='No author dated calendar or physical airport assignment',
                        economic_comparison_allowed=False,status='NECESSARY_RESOURCE_BOUND_NOT_SCHEDULE_FEASIBILITY'))
    for r in m.rows(m.SRC/'21_team_proposals/comparison.csv'):
        hours=float(r['weekly_block_hours'])
        out.append(dict(model='ciri_context21',candidate=r['network'],scenario=r['scenario'],weekly_block_hours=hours,
                        author_working_cap=cfg['active_aircraft'],author_days=cfg['work_days'],author_daily_block_cap=cfg['planning_cap_block_h'],
                        author_aggregate_weekly_cap=cfg['active_aircraft']*cfg['work_days']*cfg['planning_cap_block_h'],
                        common_working_cap=cfg['active_aircraft'],common_days=cfg['work_days'],common_daily_block_cap=cfg['planning_cap_block_h'],
                        common_aggregate_weekly_cap=cfg['active_aircraft']*cfg['work_days']*cfg['planning_cap_block_h'],common_hours_necessary_gate_pass=True,
                        minimum_working_by_hours_only=math.ceil(hours/(cfg['work_days']*cfg['planning_cap_block_h'])),
                        actual_dated_tail_requirement=r['active_allocated'],missing_reason='Model calendar only; fleet/crew/slots not confirmed',
                        economic_comparison_allowed='WITHIN_CONTEXT21_SAME_BASIS_ONLY',status='MODEL_CALENDAR_ALLOCATION_REPORTED'))
    old=m.OUT
    try:
        m.OUT=m.ROOT/'runs/resource_v1';m.save('resource_envelopes.csv',out)
        m.save('status.json',dict(status='PASS_OWNER_ARITHMETIC',common_envelope='4working+1reserve;6days;10block-hours/day',
                                  anastasia_rows=12,anastasia_pass_necessary_hours=sum(r['common_hours_necessary_gate_pass']for r in out if r['model']=='anastasia'),
                                  actual_operating_feasibility=False,independent_review='PENDING',future_delivery_dates=None))
    finally:m.OUT=old


if __name__=='__main__':main()
