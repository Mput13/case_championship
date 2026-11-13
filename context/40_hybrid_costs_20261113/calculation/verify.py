#!/usr/bin/env python3
"""Required arithmetic/scope/API/hash/deterministic checks. Offline; this directory only."""
import sys
sys.dont_write_bytecode=True
import json
import math
import subprocess
from itertools import product
from pathlib import Path
import build as B

CHECKS=[]
def check(name,condition):
    CHECKS.append(name)
    if not condition:
        raise AssertionError(name)

def close(name,a,b,tol=1e-4):
    check(name,abs(float(a)-float(b))<=tol)

def rows(file): return B.read(B.HERE/file)
def n(r,k): return float(r[k])
def key(r): return (r['case_id'],r['market'],r['budget'])

def verify():
    # Capture exact external and code/config inputs before any rebuilding.
    old=json.loads((B.HERE/'input_manifest.json').read_text())
    check('explicit_input_hashes_unchanged_before_repeat',old==B.manifest())
    check('no_venv_or_whole_directory_hash',all('.venv' not in r['path'] and (B.ROOT/r['path']).is_file() for r in old))
    result=rows('results.csv');seasonal=rows('seasonal_results.csv')
    qty={key(r):r for r in rows('quantities.csv')}
    launches={key(r):r for r in rows('launch.csv')}
    check('36_annual_cases',len(result)==36)
    check('unique_annual_keys',len({key(r) for r in result})==36)
    check('72_seasonal_cases',len(seasonal)==72)
    decomposition=['insurance_rub','station_OMS_rub','oms_basing_rub','mow_parking_analogue_rub',
                   'SLA_rub','callout_rub','dcs_rub','mow_coordination_rub',
                   'additional_bag_rub','repdesk_rub','passenger_irrops_rub','crew_extra_rub']
    for r in result:
        cid,market,budget=key(r);label='/'.join(key(r));j=B.P['budget_scenarios'].index(budget)
        q=qty[key(r)];l=launches[key(r)]
        close(label+'/revenue-cost',n(r,'net_revenue_rub')-n(r,'included_costs_rub'),n(r,'network_subtotal_rub'))
        close(label+'/recurring_decomposition',sum(n(r,k) for k in decomposition),n(r,'annual_or_period_recurring_rub'))
        close(label+'/residual',n(r,'network_subtotal_rub')-n(r,'annual_or_period_recurring_rub'),n(r,'residual_after_recurring_rub'))
        close(label+'/insurance_bridge',n(r,'residual_after_recurring_rub')+n(r,'insurance_rub'),n(r,'residual_before_insurance_rub'))
        close(label+'/retained_fleet',n(r,'retained_tails'),B.P['retained_fleet'][cid],0)
        close(label+'/insurance_not_quote',n(r,'insurance_rub'),B.P['insurance_RUB_tail_year'][j]*B.P['retained_fleet'][cid])
        close(label+'/oms_parking_unit',n(r,'oms_basing_rub'),117100*12*B.P['based_OMS_tails'][cid])
        close(label+'/MOW_analogue_explicit',n(r,'mow_parking_analogue_rub'),117100*12*B.P['based_MOW_tails'][cid]*B.P['mow_parking_OMS_analogue_multiplier'][j])
        rr=[s for s in seasonal if key(s)==key(r)]
        check(label+'/two_seasons',len(rr)==2)
        for k in decomposition+['network_subtotal_rub','included_costs_rub','net_revenue_rub',
                                 'annual_or_period_recurring_rub','residual_after_recurring_rub','staff_rounding_delta_rub']:
            close(label+'/season_sum/'+k,sum(n(s,k) for s in rr),n(r,k))
        for s in rr:
            close(label+'/'+s['season']+'/fixed_months',n(s,'fixed_months'),12*B.P['season_weights'][s['season']])
        codes=q['nonbase_station_codes'].split(';')
        check(label+'/stations_unique',len(codes)==len(set(codes)) and not {'OMS','MOW'}&set(codes))
        expected={'OMS':8,'GSV_MRV':2,'AER_VOG':2,'DIRECT2':4,'HYBRID':10,'DIRECT2_10':4,'HYBRID10':10}[cid]
        close(label+'/station_count',len(codes),expected,0)
        close(label+'/SLA_12_months',n(q,'uncovered_outstation_months'),expected*12)
        close(label+'/SLA_unit',n(r,'SLA_rub'),expected*12*B.rate('outstation_sla',budget))
        close(label+'/callout_uncovered_share',n(q,'uncovered_outstation_callout_departures'),n(q,'nonbase_departures')*B.P['outstation_callout_share'][j])
        close(label+'/DCS_net_share',n(q,'uncovered_dcs_departures'),n(q,'source_departures')*B.P['dcs_uncovered_departure_share'][j])
        close(label+'/MOW_coordination_share',n(q,'uncovered_mow_coordination_departures'),n(q,'MOW_departures')*B.P['mow_coordination_uncovered_share'][j])
        close(label+'/bag_per_order',n(r,'additional_bag_rub'),4450*n(q,'OMS_departures')*B.P['oms_additional_bag_order_share_of_OMS_departures'][j])
        close(label+'/repdesk_workplace',n(r,'repdesk_rub'),1229.51*n(q,'OMS_departures')*B.P['oms_additional_repdesk_share_of_OMS_departures'][j])
        close(label+'/transfer_affected_not_segments',n(q,'affected_transfers'),n(q,'source_transfer_journeys')*B.P['irrops_transfer_affected_share'][j])
        close(label+'/local_affected_not_transfer',n(q,'affected_local_direct'),n(q,'source_local_journeys')*B.P['irrops_local_direct_affected_share'][j])
        affected=n(q,'affected_transfers')+n(q,'affected_local_direct')
        ir=B.ASS['irrops']
        close(label+'/hotel_single_occupancy',n(q,'passenger_single_room_nights'),affected*ir['overnight_share_of_affected'][j]*ir['nights_per_overnight'][j])
        close(label+'/no_double_occupancy_addition',n(q,'double_room_nights'),0)
        close(label+'/rooms_pax_plus_crew',n(q,'single_room_nights'),n(q,'passenger_single_room_nights')+n(q,'crew_single_room_nights'))
        close(label+'/rebook_incremental_units',n(q,'uncovered_rebooked_journeys'),affected*ir['rebooking_share_of_affected'][j])
        close(label+'/crew_four',n(q,'crew_single_room_nights'),n(q,'selected_crew_extra_circuits')*4)
        close(label+'/crew_position_person_segments',n(q,'uncovered_crew_position_segments'),n(q,'selected_crew_extra_circuits')*8)
        if cid.startswith('HYBRID'):
            local_oms=B.API.expenses_for('OMS',market)['drivers']['local_journeys']
        elif cid=='OMS': local_oms=n(q,'source_local_journeys')
        else: local_oms=0
        expected_groups=(n(q,'affected_transfers')+local_oms*B.P['irrops_local_direct_affected_share'][j]*0.5)/40
        close(label+'/OMS_only_expected_events',n(q,'OMS_expected_event_groups'),expected_groups)
        close(label+'/bus_started_hours',n(q,'uncovered_bus_started_hours'),expected_groups*B.P['irrops_bus_started_hours_per_event_group'][j])
        close(label+'/distribution_per_service',n(q,'uncovered_meal_distribution_services'),expected_groups*B.P['irrops_distribution_services_per_event_group'][j])
        # Match budget API exactly, with only explicit integer staff and MOW analogue differences.
        exposures={k:n(q,k) for k in {p['qty'] for p in B.PARAMS.values()}|{'oms_retained_months'}}
        ev=B.BA.evaluate(exposures,budget,B.P['station_variant'][budget])
        check(label+'/budget_API_complete',not ev['missing_exposures'])
        close(label+'/budget_API_convergence',ev['total_selected_operating']+n(r,'staff_rounding_delta_rub')+n(r,'mow_parking_analogue_rub'),n(r,'annual_or_period_recurring_rub'))
        if cid in B.MAIN:
            v=B.API.expenses_for(cid,market)
            close(label+'/network_API_subtotal',v['operating_subtotal_before_uncovered_rub'],n(r,'network_subtotal_rub'))
            close(label+'/network_cost_ledger_once',sum(x['cost_signed_rub'] for x in v['components'].values()),n(r,'included_costs_rub'))
            close(label+'/unique_pax_identity',v['drivers']['segments'],v['drivers']['local_journeys']+2*v['drivers']['transfer_journeys'])
            close(label+'/journeys_identity',v['drivers']['journeys'],v['drivers']['local_journeys']+v['drivers']['transfer_journeys'])
            source=next(x for x in B.read(B.NET/'annual_results.csv') if x['case_id']==cid and x['scenario']==market)
            close(label+'/annual_export_convergence',n(source,'subtotal_rub'),n(r,'network_subtotal_rub'))
        close(label+'/launch_cash_identity',n(l,'launch_cash_rub'),sum(n(l,k) for k in ['oneoff_expense_rub','CAPEX_rub','refundable_deposits_rub','working_capital_rub']))
        close(label+'/CAPEX_3year_only',n(l,'capex_depreciation_3y_rub'),n(l,'CAPEX_rub')/3)
        close(label+'/no_annual_launch_cash_writeoff',n(l,'steady_state_after_CAPEX_3y_stress_rub'),n(r,'residual_after_recurring_rub')-n(l,'CAPEX_rub')/3)
        close(label+'/no_annual_oneoff_writeoff',n(l,'entry_year_PnL_if_full_steady_year_rub'),n(l,'steady_state_after_CAPEX_3y_stress_rub')-n(l,'oneoff_expense_rub'))
        close(label+'/one_pool_deposit',n(l,'refundable_pool_deposit_count'),1,0)
        close(label+'/IT_setup_unit_conversion',n(l,'IT_actual_hour_rate_rub'),B.it_hour(budget))
        close(label+'/IT_setup_hours',n(l,'IT_setup_hours'),n(l,'IT_setup_markets')*B.P['it_configuration_hours_per_unique_nonOMS_market'][j])
        close(label+'/IT_setup_amount',n(l,'IT_setup_rub'),n(l,'IT_setup_hours')*B.it_hour(budget))
        check(label+'/setup_markets_unique',len(l['IT_setup_market_codes'].split(';'))==len(set(l['IT_setup_market_codes'].split(';'))))
        close(label+'/launch_market_count',n(l,'IT_setup_markets'),{'OMS':9,'GSV_MRV':3,'AER_VOG':3,'DIRECT2':5,'HYBRID':11,'DIRECT2_10':5,'HYBRID10':11}[cid],0)
        if market=='base':
            close(label+'/fuelcredit_same_schedule_debit',n(r,'fuel_credit_reduction_rub'),n(q,'source_fuel_t')*29906)
            close(label+'/fuelcredit_once',n(r,'residual_fuel_credit_3024_rub'),n(r,'residual_after_recurring_rub')-n(q,'source_fuel_t')*29906)
    # Staff rounding and outsourced hours are checked at source-item level.
    for r in rows('station.csv'):
        label='station/'+r['variant']+'/'+r['budget']+'/'+r['item']
        close(label+'/amount',n(r,'annual_rub'),n(r,'quantity')*n(r,'periods')*n(r,'rate'))
        close(label+'/rounding_bridge',n(r,'annual_rub')-n(r,'fractional_BoQ_rub'),n(r,'rounding_delta_rub'))
        src=next(x for x in B.BOQ if x['variant']==r['variant'] and x['scenario']==r['budget'] and x['item_id']==r['item'])
        if r['item'] in B.P['ceil_staff_groups'] and r['budget'] in B.P['ceil_staff_in']:
            close(label+'/ceil_separate',n(r,'quantity'),math.ceil(float(src['qty'])),0)
        if r['item']=='it_support':
            close(label+'/outsourced_hours',n(r,'quantity'),float(src['coverage_hours_year']))
            close(label+'/not_FTE_month_as_hour',n(r,'rate'),float(src['rate'])*12/float(src['effective_hours_FTE_year']))
    # Recompute bounded optimum from compact 50-row source-evaluation certificate.
    cand=rows('bounded10_candidates.csv');check('bounded/50_cached_joint_evals',len(cand)==50)
    by={(r['season'],int(r['GSV_MRV_freq']),int(r['AER_VOG_freq'])):r for r in cand}
    feasible=[]
    for a,b,c,d in product(range(3,8),repeat=4):
        sm=by[('summer',a,b)];wi=by[('winter',c,d)]
        if max(n(sm,'direct_weekly_BH'),n(wi,'direct_weekly_BH'))<=140+1e-9:
            feasible.append(n(sm,'HYBRID10_central_period_residual_rub')+n(wi,'HYBRID10_central_period_residual_rub'))
    info=json.loads((B.HERE/'bounded10.json').read_text())
    close('bounded/feasible_count',len(feasible),info['feasible'],0)
    close('bounded/625_search_optimum',max(feasible),info['HYBRID10_best_residual_rub'])
    close('bounded/common_OD_empty',len(info['common_OD_intersection']),0,0)
    check('bounded/BH_both_seasons',max(info['DIRECT2_weekly_BH'].values())<=140)
    check('bounded/full7_7_API_replay',info['full_7_7_replay_max_abs_error_rub']<1e-4)
    best=next(r for r in result if key(r)==('HYBRID10','base','base'))
    close('bounded/annual_assembly',n(best,'residual_after_recurring_rub'),max(feasible))
    proof=json.loads((B.NET/'joint_OD_proof.json').read_text())
    check('common_OD_frozen_filter',not proof['shared_OD'] and not proof['physical_leg_intersection'])
    for market in ['base','cautious']:
        oq=qty[('OMS',market,'base')];dq=qty[('DIRECT2',market,'base')];hq=qty[('HYBRID',market,'base')]
        check(market+'/joint_station_union',set(hq['nonbase_station_codes'].split(';'))==set(oq['nonbase_station_codes'].split(';'))|set(dq['nonbase_station_codes'].split(';')))
        for budget in ['low','base','high']:
            oo=next(r for r in result if key(r)==('OMS',market,budget))
            dd=next(r for r in result if key(r)==('DIRECT2',market,budget))
            hh=next(r for r in result if key(r)==('HYBRID',market,budget))
            close(market+'/'+budget+'/shared_SLA_two_stations_once',n(oo,'SLA_rub')+n(dd,'SLA_rub')-n(hh,'SLA_rub'),2*12*B.rate('outstation_sla',budget))
            close(market+'/'+budget+'/hybrid_fixed_cost_joint_bridge',n(hh,'annual_or_period_recurring_rub'),n(oo,'annual_or_period_recurring_rub')+n(dd,'annual_or_period_recurring_rub')-2*12*B.rate('outstation_sla',budget))
    # Full outputs are deterministic on a second execution of the same pure assembly.
    outputs=['results.csv','seasonal_results.csv','quantities.csv','seasonal_quantities.csv',
             'launch.csv','station.csv','included.csv','sensitivities.csv','thresholds.csv',
             'bounded10.json','bounded10_candidates.csv','invoice_event_example.json','RESULTS.md','input_manifest.json']
    hashes={name:B.sha(B.HERE/name) for name in outputs}
    rebuilt=subprocess.run([sys.executable,'-B',str(B.HERE/'build.py')],cwd=B.HERE,
                           text=True,capture_output=True,check=True)
    check('fresh_process_build_succeeded',json.loads(rebuilt.stdout)['status']=='BUILT')
    for name in outputs:
        check('deterministic_byte_identical/'+name,B.sha(B.HERE/name)==hashes[name])
    check('explicit_inputs_unchanged_after_repeat',B.manifest()==old)
    h=next(r for r in result if key(r)==('HYBRID','base','base'))
    output=dict(status='PASS',checks_passed=len(CHECKS),failures=0,
                external_network_used=False,delegation=False,git_mutations=False,
                writes='calculation/ only',explicit_input_files=len(old),
                deterministic_repeat='14 output files byte-identical across fresh Python3 processes',
                HYBRID_central_residual_rub=n(h,'residual_after_recurring_rub'),
                HYBRID10_central_residual_rub=n(best,'residual_after_recurring_rub'),
                bounded_feasible_combinations=len(feasible),
                checked=['money identities','12-month fixed coverage','unique stations/deposits/resources',
                         'unit rates and selected quantities','disjoint passenger exposure',
                         'network and budget API convergence','same-schedule fuelcredit substitution',
                         'bounded625 search','explicit input hashes','deterministic rebuild'],
                limitations='Arithmetic/scenario scope only. No proof of actual coverage/contracts, insurance market price, roster, slots, tax treatment or actual profit.')
    B.dump('validation.json',output)
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=='__main__':
    verify()
