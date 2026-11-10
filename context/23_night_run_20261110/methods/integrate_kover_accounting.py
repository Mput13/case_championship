#!/usr/bin/env python3
"""Join the corrected MR02 projection to exact context21 and invert costs.

Only the frozen C-recipe and enumerated program are covered. No overlay money
is applied to N demand, portfolios, new products, or different calendars.
"""
import collections
import json
from datetime import datetime,timedelta,timezone
import common_demand as m

ROOT=m.ROOT
ORIG=ROOT/'inputs/cost-kover-001'
FIX=ROOT/'inputs/cost-timebase-002'
OUT=ROOT/'runs/kover_accounting_v1'
MAP={'H_UFA_4':'H_UFA_4','H_UFA_8':'H_UFA_8','D_case':'D_previous_best8'}


def main():
    corrected=m.rows(FIX/'scenario_summary.csv');original=m.rows(ORIG/'scenario_summary.csv')
    definitions=json.loads((ORIG/'scenario_definitions.json').read_text())
    results=m.rows(m.SRC/'21_team_proposals/comparison.csv')
    source_result={(r['network'],r['scenario']):r for r in results}
    sales=m.rows(m.SRC/'17_aircraft_route_review/model/sales.csv')
    flights=m.rows(m.SRC/'17_aircraft_route_review/model/flights.csv')
    cfg=json.loads((m.SRC/'15_team_update/model/configuration.json').read_text())
    assert cfg['config']['disruption_compensation_rub_journey']==5000
    episode=definitions['episode'];start=datetime.fromisoformat(episode['start_utc']);end=datetime.fromisoformat(episode['end_utc_exclusive'])
    epoch=datetime.fromisoformat(definitions['period_start']).replace(tzinfo=timezone.utc)
    audits=[];rows=[]
    for s in corrected:
        if s['network']not in MAP:continue
        n=MAP[s['network']];sc=s['author_scenario'];r=source_result[n,sc]
        assert s['profile']==r['source_profile'] and s['network']==r['source_network']
        assert s['period_start']=='2026-12-07'and s['period_end']=='2026-12-13'
        assert s['source_commit']=='93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
        m.near(s['author_contribution_rub'],r['contribution_before_base_fleet_opportunity'],'exact baseline contribution')
        old=next(x for x in original if all(x[k]==s[k]for k in ['profile','network','author_scenario','scenario_id']))
        original_delta=float(old['overlay_delta_before_unknown_rub'])
        gated=s['overlay_delta_before_unknown_rub']==''
        if gated:
            assert s['scenario_id']=='delay_bank_next_day_fare_retained'and n.startswith('H_UFA')
            assert all(s[k]==''for k in ['remaining_endpoint_journeys','unserved_endpoint_journeys','contribution_after_overlay_before_unknown_rub'])
        else:m.near(s['overlay_delta_before_unknown_rub'],original_delta,'day1 arithmetic same after epoch correction')
        row=dict(model_variant='context21_team_proposals',candidate_id=n,source_profile=r['source_profile'],source_network=r['source_network'],
                 author_scenario=sc,scenario_id=s['scenario_id'],source_commit=s['source_commit'],input_set_id='set001+C_recipe+cost-timebase-002',
                 correction_commit='87ee52de15c2bdf396d9c06ba600fd413d5ab4a8',baseline_contribution=float(r['contribution_before_base_fleet_opportunity']),
                 overlay_delta=None if gated else float(s['overlay_delta_before_unknown_rub']),
                 contribution_after_before_unknown=None if gated else float(s['contribution_after_overlay_before_unknown_rub']),
                 unserved_journeys=None if gated else float(s['unserved_endpoint_journeys']),
                 remaining_journeys=None if gated else float(s['remaining_endpoint_journeys']),
                 additional_cash_peak_net_fixture=None if gated else float(s['additional_cash_peak_timing_stress_rub']),
                 actual_full_budget=None,actual_full_cash_peak=None,delay_status='HOLD_RESOURCE_CONFLICT'if gated else 'NOT_HELD_BY_TIMEBASE_FIX',
                 scope='ENUMERATED_FROZEN_C_SALES_ONLY_NOT_N_RECIPE_OR_PORTFOLIOS',independent_correction_review='NOT_RUN',
                 original_cost_review='PENDING',decision_status='AGENT_PROPOSAL')
        rows.append(row)
        if s['scenario_id'].startswith('cancel'):
            p=cfg['scenarios'][sc];key=r['source_profile'],r['source_network']
            ff=[f for f in flights if(f['profile'],f['network'])==key]
            ss=[x for x in sales if(x['profile'],x['network'],x['scenario'])==(*key,sc)]
            touched={f['id']for f in ff if (f['origin']==episode['airport']and start<=epoch+timedelta(minutes=float(f['departure_utc_minute']))<end)
                     or (f['destination']==episode['airport']and start<=epoch+timedelta(minutes=float(f['arrival_utc_minute']))<end)}
            affected=[x for x in ss if touched.intersection(x['flight_ids'].split(';'))]
            loss=sum(float(x['gross_revenue'])for x in affected);q=sum(float(x['sold_journeys'])for x in affected)
            policy=next(x for x in definitions['scenarios']if x['id']==s['scenario_id'])
            fractions=definitions['avoidability_profiles'][policy['avoidability']]
            saved=sum(float(x['new_pax_variable'])for x in affected)*fractions['new_pax_variable']
            for f in ff:
                if f['id']not in touched:continue
                h=float(f['block_minutes'])/60;fuel=h*p['fuel_t_per_hour']+p['fuel_t_per_cycle']
                comps=dict(fuel_product=fuel*p['fuel_rub_per_t'],fuel_uplift=fuel*p['fuel_uplift_rub_per_t'],
                           mro=h*p['mro_rub_per_hour'],crew=h*p['crew_rub_per_hour'],navigation=h*p['navigation_rub_per_hour'],
                           airport_turn=(49.45*(553+499)+19300+8100+16668)*p['airport_factor'],deicing=p['deicing_probability']*p['deicing_operation_rub'])
                saved+=sum(value*fractions[k]for k,value in comps.items())
            m.near(len(touched),s['cancelled_physical_legs'],'epoch touched count')
            m.near(q,s['unserved_endpoint_journeys'],'union once')
            m.near(loss,s['lost_net_revenue_rub'],'fare once')
            m.near(saved-loss,row['overlay_delta'],'independent cancellation ledger')
            audits.append(dict(candidate_id=n,scenario=sc,policy=s['scenario_id'],cancelled_legs=len(touched),affected_journeys=q,
                               lost_fare_once=loss,avoidable_costs=saved,delta=saved-loss,status='PASS_OWNER_RECOMPUTATION_OF_DAY1_ONLY'))
    # D_SVX8 is not MR02 D_pilot: prove the zero effect directly from its own
    # flights for the named UFA episode; do not copy a differently sized program.
    for sc in ['base','cautious']:
        r=source_result['D_SVX8',sc];ff=[f for f in flights if(f['profile'],f['network'])==(r['source_profile'],r['source_network'])]
        assert len(ff)==int(r['weekly_legs'])and all(episode['airport']not in(f['origin'],f['destination'])for f in ff)
        for policy in definitions['scenarios']:
            rows.append(dict(model_variant='context21_team_proposals',candidate_id='D_SVX8',source_profile=r['source_profile'],source_network=r['source_network'],
                             author_scenario=sc,scenario_id=policy['id'],source_commit='93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
                             input_set_id='set001+C_recipe+EXPLICIT_NO_UFA_ENDPOINT_CONTROL',correction_commit=None,
                             baseline_contribution=float(r['contribution_before_base_fleet_opportunity']),overlay_delta=0.,
                             contribution_after_before_unknown=float(r['contribution_before_base_fleet_opportunity']),unserved_journeys=0.,
                             remaining_journeys=float(r['sold_journeys']),additional_cash_peak_net_fixture=0.,actual_full_budget=None,actual_full_cash_peak=None,
                             delay_status='NAMED_EPISODE_DOES_NOT_TOUCH_ENUMERATED_NEW_FLIGHTS',scope='NEW_PROGRAM_ONLY_OLD_COMPANY_DISRUPTION_UNKNOWN',
                             independent_correction_review='NOT_APPLICABLE_DERIVED_CONTROL',original_cost_review='PENDING',decision_status='AGENT_PROPOSAL'))
    thresholds=[]
    for r in rows:
        if r['candidate_id']not in ['H_UFA_4','H_UFA_8']or not r['scenario_id'].startswith('cancel'):continue
        q=r['unserved_journeys'];sc=r['author_scenario'];comparison=source_result['D_previous_best8',sc]
        difference=r['contribution_after_before_unknown']-float(comparison['contribution_before_base_fleet_opportunity'])
        thresholds.append(dict(candidate_id=r['candidate_id'],scenario=sc,policy=r['scenario_id'],unserved_journeys=q,
                               extra_burden_per_unserved_to_erase_cancel_accrual_delta=r['overlay_delta']/q,
                               difference_vs_previous8_before_fixed=difference,
                               extra_burden_per_unserved_for_relative_equality_before_fixed=difference/q,
                               same_burden5000_per_journey_difference=difference-5000*q,
                               burden5000_source='context15 configuration.disruption_compensation_rub_journey; author stress NOT legal/actual compensation',
                               formula='Difference - theta*unserved - (additional fixed/base/other differences); no second own-migration/donor deduction',
                               economic_caveat='Transport volumes differ; negative equality threshold means already behind; no launch or restrictions-benefit recommendation'))
    cash=[]
    for n in ['H_UFA_4','H_UFA_8']:
        for sc in ['base','cautious']:
            for policy in ['cancel_pretravel_no_protection','cancel_usage_billed_sensitivity']:
                events=[x for x in m.rows(FIX/'cash_fixture.csv')if x['network']==n and x['author_scenario']==sc and x['scenario_id']==policy]
                target=next(r for r in rows if r['candidate_id']==n and r['author_scenario']==sc and r['scenario_id']==policy)
                total=trough=0.
                for e in sorted(events,key=lambda x:(float(x['relative_day']),x['event'])):
                    computed=float(e['delta_pnl_rub'])-float(e['delta_inventory_rub'])+float(e['delta_payables_rub'])+float(e['delta_deferred_ticket_liability_rub'])
                    m.near(computed,e['delta_cash_rub'],'balance-sheet cash bridge')
                    total+=computed;trough=min(trough,total)
                m.near(total,target['overlay_delta'],'terminal delta cash');m.near(-trough,target['additional_cash_peak_net_fixture'],'event peak')
                cash.append(dict(candidate_id=n,scenario=sc,policy=policy,event_count=len(events),net_fixture_funding=-trough,
                                 final_delta_cash=total,actual_gross_funding=None,status='PASS_OWNER_EVENT_LEDGER_ARITHMETIC_NOT_ACTUAL_CASH'))
    old=m.OUT
    try:
        m.OUT=OUT;m.save('context21_overlay.csv',rows);m.save('cancellation_checks.csv',audits);m.save('burden_thresholds.csv',thresholds);m.save('cash_checks.csv',cash)
        m.save('status.json',dict(status='PASS_OWNER_SCOPED_ACCOUNTING',rows=len(rows),held_delay_rows=sum(r['overlay_delta']is None for r in rows),
                                  cancellation_recomputations=len(audits),cash_recomputations=len(cash),independent_review='PENDING_NEW_INTEGRATION',
                                  correction_acceptance='PARENT_TIMEBASE_AND_DELTA_CHECK_ONLY',applied_to_N_demand=False,applied_to_portfolios=False,
                                  observed_downtime_or_probability=False,full_budget=False,all_other_risks_retained=True))
    finally:m.OUT=old
    print(json.dumps(dict(rows=len(rows),held_delays=sum(r['overlay_delta']is None for r in rows),cancellation_checks=len(audits))))


if __name__=='__main__':main()
