#!/usr/bin/env python3
"""Explicit unit and cost-recipe bridges; no product demand forecast."""
import json
import math
import common_demand as m

SOURCE=m.ROOT/'inputs/set001/hypotheses_6ed8/context/16_agent_research/hypotheses/experiment_v1'
OUT=m.ROOT/'runs/product_bridge_v1'


def main():
    original=m.rows(SOURCE/'cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv')
    selected=[r for r in original if float(r['residual_funding_gap_rub'])==1000000
              and float(r['net_fare_rub_per_oneway_journey'])==8000
              and float(r['variable_cost_rub_per_oneway_journey'])==500]
    assert len(selected)==3
    units=[]
    for r in selected:
        legs=int(r['legs_per_oneway_journey']);gap=float(r['residual_funding_gap_rub']);fare=float(r['net_fare_rub_per_oneway_journey'])
        for name,cost in [('AUTHOR500_PER_JOURNEY',500),('COMMON500_PER_OCCUPIED_SEGMENT',500*legs)]:
            margin=2*(fare-cost);n=math.ceil(gap/margin)
            assert n*margin>=gap and (n-1)*margin<gap
            if name.startswith('AUTHOR'):m.near(n,r['roundtrip_customers'],'author threshold')
            units.append(dict(candidate=r['candidate'],template=r['itinerary_template_id'],origin=r['target_origin'],destination=r['target_destination'],
                              scenario=name,mode='AUTHOR_REPLAY_ARITHMETIC'if name.startswith('AUTHOR')else 'COMMON_COMPARISON_UNIT_SCENARIO',
                              gap=gap,fare_once= fare,legs_per_oneway=legs,oneway_passenger_cost=cost,roundtrip_clients=n,
                              endpoint_journeys=2*n,occupied_segments=2*n*legs,gross_ticket_revenue=2*n*fare,
                              contribution=n*margin,contribution_one_client_below=(n-1)*margin,actual_gap=None,actual_residual_seats=None,
                              source_status='FROZEN_PRODUCT_ARITHMETIC_NOT_MARKET',decision_status='AGENT_PROPOSAL_UNIT_BRIDGE'))
    chain=next(r for r in m.rows(SOURCE/'runs/c26661067277af20/c07_comparison.csv')if r['variant']=='C07_chain_turn45')
    dh=(float(chain['block_candidate_minutes'])-float(chain['block_baseline_minutes']))/60
    dl=int(chain['legs_candidate'])-int(chain['legs_baseline'])
    assert dh==4.5 and dl==2
    config=json.loads((m.SRC/'15_team_update/model/configuration.json').read_text())['scenarios']
    costs=[]
    for sc,p in config.items():
        hourly=p['fuel_t_per_hour']*(p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t'])+p['mro_rub_per_hour']+p['crew_rub_per_hour']+p['navigation_rub_per_hour']
        per_dep=p['fuel_t_per_cycle']*(p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t'])+(49.45*(553+499)+19300+8100+16668)*p['airport_factor']+p['deicing_probability']*p['deicing_operation_rub']
        cost=dh*hourly+dl*per_dep
        # Since the source cost recipe is affine in minutes and departure count,
        # total block minutes may be split arbitrarily across the stated legs.
        exact=4*m.flight_cost(float(chain['block_candidate_minutes'])/4,p)-2*m.flight_cost(float(chain['block_baseline_minutes'])/2,p)
        m.near(cost,exact,'block/cycle cost bridge')
        costs.append(dict(candidate='C07',scenario=sc,mode='COMMON_COMPARISON_COST_RECIPE_ONLY',added_block_hours=dh,added_departures=dl,
                          added_elapsed_minutes=chain['return_delay_vs_reference_minutes'],hourly_variable_rub=hourly,departure_variable_rub=per_dep,
                          added_flight_cost_rub=cost,minimum_net_oneway_fare_if100local_each_direction=cost/200+p['pax_cost'],
                          binding_assumption='Only OMS-KJA local revenue covers added flights;100paid per direction; no migration; full residual seats unverified',
                          excluded='Retiming loss, donor next assignment, positioning, fixed/base/cash, unknown airport-specific billing, Kover and new demand',
                          airport_cost_basis='CIRI_UFA_REFERENCE_BASKET_REUSED_AS_EXPLICIT_SCENARIO_NOT_OMS_OR_KJA_CONTRACT',
                          block_basis='FROZEN_HYPOTHESIS_PROXY_NOT_RW_DISPATCH',real_budget=None,decision_status='AGENT_PROPOSAL'))
    old=m.OUT
    try:
        m.OUT=OUT;m.save('journey_segment_unit_bridge.csv',units);m.save('c07_cost_recipe_bridge.csv',costs)
        m.save('status.json',dict(status='PASS_OWNER_ARITHMETIC',independent_review='PENDING',full_third_financial_model=False,
                                  author_outputs_unchanged=True,unknowns_not_zero=True,
                                  cost_kover_source_audit='SEPARATE_ROOT_PACKAGE_PENDING; no new rate-source assertions here'))
    finally:m.OUT=old
    print(json.dumps(dict(unit_cases=len(units),cost_bridge_cases=len(costs))))


if __name__=='__main__':main()
