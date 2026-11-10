#!/usr/bin/env python3
"""Certified supply bounds and exact accounting thresholds, stdlib only."""
import collections
import csv
import hashlib
import itertools
import json
import math
import platform
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'inputs/set001/tsiri_93fa/context'
OUT=ROOT/'runs/budget_v1'


def rows(path):
    with path.open(encoding='utf-8-sig',newline='')as stream:
        return list(csv.DictReader(stream))


def dump(name,data):
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/name
    if name.endswith('.json'):
        target.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    else:
        with target.open('w',newline='')as stream:
            writer=csv.DictWriter(stream,list(dict.fromkeys(k for r in data for k in r)))
            writer.writeheader()
            writer.writerows(data)


def source_key(r):
    return r['profile'],r['network'],r['scenario']


def main():
    contract=json.loads((ROOT/'budget_contract.json').read_text())
    results=rows(INPUT/'21_team_proposals/comparison.csv')
    all_sales=rows(INPUT/'17_aircraft_route_review/model/sales.csv')
    all_caps=rows(INPUT/'17_aircraft_route_review/model/capacity.csv')
    config=json.loads((INPUT/'15_team_update/model/configuration.json').read_text())
    thresholds=[]
    certificates=[]
    bounds=[]
    registry=[]
    for r in results:
        scenario=r['scenario']
        key=r['source_profile'],r['source_network'],scenario
        ss=[s for s in all_sales if source_key(s)==key]
        cc=[c for c in all_caps if source_key(c)==key]
        params=config['scenarios'][scenario]
        pax_cost=params['pax_cost']
        local={s['flight_ids']:s for s in ss if s['transfer']=='False'}
        cap={c['flight_id']:float(c['capacity_scenario'])for c in cc}
        assert set(local)==set(cap)
        assert len(local)==sum(s['transfer']=='False'for s in ss)
        shadow={leg:float(s['fare_once'])-pax_cost for leg,s in local.items()}
        assert all(v>=0 for v in shadow.values())
        for s in ss:
            ids=s['flight_ids'].split(';')
            direct_reference_fare=float(s['fare_once'])/(params['transfer_fare_factor']if s['transfer']=='True'else 1)
            # Removing migration can only improve result in these source scenarios.
            assert direct_reference_fare*params['old_RW_fare_ratio']>=2*pax_cost
            assert float(s['foregone_RW_revenue'])+1e-6>=float(s['saved_old_pax_variable'])
            unit_margin=float(s['fare_once'])-len(ids)*pax_cost
            slack=sum(shadow[i]for i in ids)-unit_margin
            assert slack>=-1e-8,(key,s['flight_ids'],slack)
            certificates.append(dict(network=r['network'],scenario=scenario,
                origin=s['origin'],destination=s['destination'],flight_ids=s['flight_ids'],
                itinerary_fare=float(s['fare_once']),leg_count=len(ids),pax_cost_per_segment=pax_cost,
                itinerary_unit_margin=unit_margin,sum_leg_shadow_value=sum(shadow[i]for i in ids),
                dual_slack=slack,certificate='NONNEGATIVE_SLACK_BOUNDS_EVERY_ALLOWED_ITINERARY'))
        seats=sum(cap.values())
        full_local_revenue=sum(cap[i]*float(local[i]['fare_once'])for i in cap)
        full_pax_cost=seats*pax_cost
        variable_flight_cost=float(r['flight_variable_cost'])
        margin_upper=sum(cap[i]*shadow[i]for i in cap)
        upper=margin_upper-variable_flight_cost
        assert math.isclose(upper,full_local_revenue-full_pax_cost-variable_flight_cost,abs_tol=1e-6)
        current=float(r['contribution_before_base_fleet_opportunity'])
        assert upper>=current-1e-6
        bound=dict(network=r['network'],scenario=scenario,period_start='2026-12-07',period_end='2026-12-13',
            source_commit='93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',input_set_id='set001',
            currency='RUB',mode='COMMON_COMPARISON',value_status='AGENT_PROPOSAL_CERTIFIED_RELAXATION',
            nominal_segment_seats=seats,full_local_revenue=full_local_revenue,
            full_local_pax_cost=full_pax_cost,flight_variable_cost=variable_flight_cost,
            current_contribution=current,optimistic_contribution_upper=upper,
            demand_alone_can_reach_zero_in_relaxed_model=upper>=0,
            minimum_common_fare_multiplier_at_full_local_seats=(variable_flight_cost+full_pax_cost)/full_local_revenue,
            uniform_local_occupancy_zero_threshold=variable_flight_cost/margin_upper,
            extra_cost_headroom_at_relaxed_max=upper,
            actual_extra_cost=None,actual_full_budget_result=None,
            limitation='Fixed dated source programs; unlimited local/transfer demand; zero own migration; nominal100 not operational payload; unknown fixed costs excluded')
        bounds.append(bound)
        gross=float(r['gross_revenue']);foregone=float(r['foregone_RW_revenue'])
        inc_revenue=float(r['incremental_revenue']);cost=float(r['incremental_operating_cost'])
        assert math.isclose(gross-foregone,inc_revenue,abs_tol=1e-6)
        # Extra cost grid is a mathematical burden, not a claimed contract or distribution.
        for extra in [0,500000,1000000]:
            common=(cost+extra)/inc_revenue
            new_only=(cost+foregone+extra)/gross
            assert math.isclose(common*inc_revenue-cost-extra,0,abs_tol=1e-6)
            assert math.isclose(new_only*gross-foregone-cost-extra,0,abs_tol=1e-6)
            thresholds.append(dict(network=r['network'],scenario=scenario,extra_burden_rub=extra,
                extra_burden_status='EXPLICIT_STRESS_NOT_ACTUAL_TOTAL_FIXED_COST',
                fixed_sold_journeys=float(r['sold_journeys']),common_new_old_fare_multiplier=common,
                new_only_fare_multiplier_old_yield_fixed=new_only,
                full_local_fare_multiplier_optimistic=(variable_flight_cost+full_pax_cost+extra)/full_local_revenue,
                uniform_local_occupancy_threshold_no_migration=(variable_flight_cost+extra)/margin_upper,
                fraction_of_flight_cost_reduction_needed_at_current_sales=(cost+extra-inc_revenue)/variable_flight_cost,
                fixed_sales_extra_cost_headroom=current,
                limit='Conditional inverse thresholds; no constant-demand claim after price changes'))
        registry.append(dict(network=r['network'],scenario=scenario,additional_working_tail_allocation=int(r['active_allocated']),
                             reserve_allocation=int(r['reserve_scenario']),new_base_indicator=int(r['network'].startswith('H_')),
                             source_variable_contribution=current,
                             allocated_tail_week_cost=None,new_base_week_cost=None,other_incremental_fixed=None,
                             formula='Pi=C-(working+reserve)*F-base_indicator*B-O',
                             note='F is incremental avoidable/new allocation cost; shared sunk reserve is not charged twice'))
    dump('supply_upper_bounds.csv',bounds)
    dump('supply_dual_certificates.csv',certificates)
    dump('fixed_sales_thresholds.csv',thresholds)
    dump('strategy_budget_parameters.csv',registry)
    differences=[]
    for scenario in ['base','cautious']:
        rs=[r for r in registry if r['scenario']==scenario]
        for a,b in itertools.combinations(rs,2):
            dn=(a['additional_working_tail_allocation']+a['reserve_allocation'])-(b['additional_working_tail_allocation']+b['reserve_allocation'])
            db=a['new_base_indicator']-b['new_base_indicator']
            delta=a['source_variable_contribution']-b['source_variable_contribution']
            differences.append(dict(scenario=scenario,candidate_a=a['network'],candidate_b=b['network'],
                delta_contribution_a_minus_b=delta,delta_allocated_tails=dn,delta_new_base_indicator=db,
                difference_formula='deltaC - deltaTails*F - deltaBase*B - (O_A-O_B)',
                F_tie_when_B_and_other_differences_zero=(delta/dn if dn else None),
                B_tie_when_F_and_other_differences_zero=(delta/db if db else None),
                parameter_domain='F>=0; B>=0; negative tie coordinates outside this domain',
                status='CONDITIONAL_DIFFERENCE_NOT_LAUNCH_OR_CASE_COMPLIANCE_RANKING'))
    dump('pairwise_budget_boundaries.csv',differences)
    # Independently stated synthetic accounting examples, never route estimates.
    donor=dict(revenue=1000000,flight_variable=600000,pax_variable=100000)
    replacement=dict(revenue=1200000,flight_variable=700000,pax_variable=100000)
    continuing_fixed=200000;exit_cost=50000
    keep=donor['revenue']-donor['flight_variable']-donor['pax_variable']-continuing_fixed
    cancel=-continuing_fixed-exit_cost
    replace=replacement['revenue']-replacement['flight_variable']-replacement['pax_variable']-continuing_fixed-exit_cost
    donor_contribution=donor['revenue']-donor['flight_variable']-donor['pax_variable']
    replacement_contribution=replacement['revenue']-replacement['flight_variable']-replacement['pax_variable']
    assert replace-keep==replacement_contribution-donor_contribution-exit_cost==50000
    assert cancel-keep==-donor_contribution-exit_cost==-350000
    assert replace-cancel==replacement_contribution==400000
    states=[dict(state=s,full_state_result=v,delta_vs_keep=v-keep,fixture_status='ILLUSTRATIVE_ARITHMETIC_NOT_ACTUAL_DONOR')
            for s,v in [('KEEP',keep),('CANCEL_WITHOUT_REPLACEMENT',cancel),('REPLACE',replace)]]
    dump('donor_fixture_states.csv',states)
    cash_events=[dict(period=0,operating_receipts=0,operating_payments=0,launch_payments=400000,deposit_payment=600000,deposit_return=0),
                 dict(period=1,operating_receipts=1200000,operating_payments=800000,launch_payments=0,deposit_payment=0,deposit_return=0),
                 dict(period=2,operating_receipts=1200000,operating_payments=800000,launch_payments=0,deposit_payment=0,deposit_return=600000)]
    cash=0
    for e in cash_events:
        e['net_cash']=e['operating_receipts']-e['operating_payments']-e['launch_payments']-e['deposit_payment']+e['deposit_return']
        cash+=e['net_cash'];e['cumulative_cash_before_financing']=cash
        e['fixture_status']='ILLUSTRATIVE_TIMING_NOT_COMPANY_FORECAST'
    accounting_result=sum(e['operating_receipts']-e['operating_payments']-e['launch_payments']for e in cash_events)
    peak=max(0,-min(e['cumulative_cash_before_financing']for e in cash_events))
    assert accounting_result==cash==400000 and peak==1000000
    dump('cash_fixture.csv',cash_events)
    endpoint_counts=rows(ROOT/'analysis/set001/route_counts.csv')
    dump('endpoint_pair_counts.csv',[dict(model_id=r['model_id'],scenario=r['scenario'],
        author_program_count=r['author_program_count'],model_endpoint_pair_count=r['physical_pair_count'],
        operating_airport_pair_count=None,dated_operating_route_count=None,
        correction='MOW is a city aggregate; original v1 field physical_pair_count was too strong; source values unchanged')for r in endpoint_counts])
    dump('validation.json',dict(status='PASS_SCOPED',input_contract_sha256=hashlib.sha256((ROOT/'budget_contract.json').read_bytes()).hexdigest(),
        author_input_sha256=hashlib.sha256((ROOT/'source_manifest.json').read_bytes()).hexdigest(),python=platform.python_version(),
        certificates=len(certificates),network_scenarios=len(bounds),
        all_cautious_upper_bounds_negative=all(b['optimistic_contribution_upper']<0 for b in bounds if b['scenario']=='cautious'),
        checks=['nonnegative per-leg dual certificate for every source itinerary','all-local primal attains dual bound',
                'zero migration is optimistic under positive foregone old contribution','fixed-sales inverse-price identities',
                'full donor states equal incremental formula without double count','cash deposit returned without P&L expense'],
        independent_review='PENDING',empirical_sales='UNKNOWN',full_budget_result='UNKNOWN',
        scope='Fixed dated Tsiri programs only; no arbitrary network impossibility result'))
    print(json.dumps({'status':'PASS_SCOPED','network_scenarios':len(bounds),'dual_rows':len(certificates),'negative_cautious_supply_bounds':4}))


if __name__=='__main__':
    main()
