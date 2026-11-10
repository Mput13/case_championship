#!/usr/bin/env python3
"""Explicit C/N interaction: recompute cancellation, never transplant its delta."""
import json
from datetime import datetime,timedelta,timezone
import common_demand as m


def main():
    contract=json.loads((m.ROOT/'kover_demand_contract.json').read_text())
    sales=m.rows(m.ROOT/'runs/common_demand_v1/itinerary_at_unit_scale.csv')
    base=m.rows(m.ROOT/'runs/common_demand_v1/summary.csv')
    flights=m.rows(m.SRC/'17_aircraft_route_review/model/flights.csv')
    definitions=json.loads((m.ROOT/'inputs/cost-kover-001/scenario_definitions.json').read_text())
    params=json.loads((m.SRC/'15_team_update/model/configuration.json').read_text())['scenarios']
    reference=m.rows(m.ROOT/'runs/kover_accounting_v1/cancellation_checks.csv')
    epoch=datetime(2026,12,7,tzinfo=timezone.utc);end=epoch+timedelta(days=1)
    output=[];incidence=[]
    for n in ['H_UFA_4','H_UFA_8']:
        for sc in ['base','cautious']:
            p=params[sc]
            for recipe in ['C','N']:
                r=next(r for r in base if r['network']==n and r['scenario']==sc and r['recipe']==recipe and float(r['multiplier'])==1)
                ss=[s for s in sales if s['network']==n and s['scenario']==sc and s['recipe']==recipe and float(s['multiplier'])==1]
                ff=[f for f in flights if(f['profile'],f['network'])==(r['source_profile'],r['source_network'])]
                ids={f['id']for f in ff};assert {i for s in ss for i in s['flight_ids'].split(';')}==ids
                touched={f['id']for f in ff if(f['origin']=='UFA'and epoch<=epoch+timedelta(minutes=float(f['departure_utc_minute']))<end)
                         or(f['destination']=='UFA'and epoch<=epoch+timedelta(minutes=float(f['arrival_utc_minute']))<end)}
                affected=[s for s in ss if touched.intersection(s['flight_ids'].split(';'))]
                loss=sum(float(s['gross_revenue'])for s in affected);q=sum(float(s['sold_journeys'])for s in affected)
                for s in affected:
                    m.near(float(s['fare_once'])*float(s['sold_journeys']),s['gross_revenue'],'one fare')
                    incidence.append(dict(candidate=n,scenario=sc,recipe=recipe,origin=s['origin'],destination=s['destination'],
                                          flight_ids=s['flight_ids'],affected_leg_count=len(touched.intersection(s['flight_ids'].split(';'))),
                                          journeys=float(s['sold_journeys']),lost_fare_once=float(s['gross_revenue']),new_pax_cost_avoided=float(s['new_pax_variable'])))
                for policy in contract['policies']:
                    named=next(x for x in definitions['scenarios']if x['id']==policy)
                    fractions=definitions['avoidability_profiles'][named['avoidability']]
                    saved=sum(float(s['new_pax_variable'])for s in affected)*fractions['new_pax_variable']
                    for f in ff:
                        if f['id']not in touched:continue
                        h=float(f['block_minutes'])/60;fuel=h*p['fuel_t_per_hour']+p['fuel_t_per_cycle']
                        values=dict(fuel_product=fuel*p['fuel_rub_per_t'],fuel_uplift=fuel*p['fuel_uplift_rub_per_t'],
                                    mro=h*p['mro_rub_per_hour'],crew=h*p['crew_rub_per_hour'],navigation=h*p['navigation_rub_per_hour'],
                                    airport_turn=(49.45*(553+499)+19300+8100+16668)*p['airport_factor'],deicing=p['deicing_probability']*p['deicing_operation_rub'])
                        saved+=sum(v*fractions[k]for k,v in values.items())
                    delta=saved-loss
                    if recipe=='C':
                        ref=next(x for x in reference if(x['candidate_id'],x['scenario'],x['policy'])==(n,sc,policy))
                        m.near(delta,ref['delta'],'C reference delta');m.near(q,ref['affected_journeys'],'C reference journeys')
                    output.append(dict(experiment=contract['id'],candidate=n,scenario=sc,recipe=recipe,policy=policy,
                                       cancelled_physical_legs=len(touched),unserved_journeys=q,lost_fare_once=loss,avoidable_costs=saved,
                                       baseline_contribution=float(r['contribution_before_base_fleet_opportunity']),delta_before_unknown=delta,
                                       contribution_after_before_unknown=float(r['contribution_before_base_fleet_opportunity'])+delta,
                                       remaining_journeys=float(r['sold_journeys'])-q,full_budget=None,actual_cash_peak=None,
                                       status='COMMON_SCENARIO_RECOMPUTED_FROM_OWN_SALES; NO_OBSERVED_OD_OR_LAUNCH',independent_review='PENDING'))
    differences=[]
    for n in ['H_UFA_4','H_UFA_8']:
        for sc in ['base','cautious']:
            for policy in contract['policies']:
                c=next(r for r in output if(r['candidate'],r['scenario'],r['policy'],r['recipe'])==(n,sc,policy,'C'))
                new=next(r for r in output if(r['candidate'],r['scenario'],r['policy'],r['recipe'])==(n,sc,policy,'N'))
                differences.append(dict(candidate=n,scenario=sc,policy=policy,C_delta=c['delta_before_unknown'],N_delta=new['delta_before_unknown'],
                                        error_if_C_delta_reused_for_N=c['delta_before_unknown']-new['delta_before_unknown'],
                                        delta_sign_changes=c['delta_before_unknown']*new['delta_before_unknown']<0,
                                        conclusion='Overlay must be re-evaluated against exact itinerary quantities and input set'))
    old=m.OUT
    try:
        m.OUT=m.ROOT/'runs/kover_demand_v1';m.save('summary.csv',output);m.save('affected_itinerary.csv',incidence);m.save('interaction_deltas.csv',differences)
        m.save('validation.json',dict(status='PASS_OWNER_ARITHMETIC',cases=len(output),C_cases_matched=8,
                                      independent_review='PENDING_NEW_SCOPE',delay_integrated=False,probability=None,observed_endpoint_demand=False))
    finally:m.OUT=old
    print(json.dumps(differences))


if __name__=='__main__':main()
