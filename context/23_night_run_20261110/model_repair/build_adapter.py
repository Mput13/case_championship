#!/usr/bin/env python3
"""Proposed mapping only. No common economic comparison or financial rerun."""
import csv
import datetime as dt
import importlib
import json
import sys
from pathlib import Path

from prepare import AUTHOR,CIRI
from replay import table,js

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'proposed_common_view'


def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))


def main():
    OUT.mkdir(exist_ok=True)
    # The principal Ciri calendar is exported by the same constructors already
    # used in the frozen replay. No evaluate/search is called again.
    sys.path.insert(0,str(ROOT/'ciri/scripts'))
    review=importlib.import_module('build_aircraft_route_review')
    definitions=json.loads((ROOT/'ciri/context/17_aircraft_route_review/model/selected_networks.json').read_text())
    profile='ROUTE_INPUTS_UPPER_100'
    m=review.setup(profile)
    networks={
        'D_SVX8':review.make_direct(m,'D_SVX8',definitions['UNKNOWN_TIME_PLUS60_100|D_case']['jobs']),
        'D_previous_best8':review.make_direct(m,'D_previous_best8',definitions[profile+'|D_case']['jobs'])}
    for name in ('H_UFA_4','H_UFA_8'):
        d=definitions[profile+'|'+name]
        networks[name]=review.legacy.hub(m,d['hub'],d['leaves'],d['frequency'],name)
    calendar=[]
    for name,n in networks.items():
        for l in n['legs']:
            row=dict(l,profile=profile)
            a,b=l['origin'],l['destination']
            row['original_block_method']=l['block_method'];row['original_source']=l['source']
            row['block_method']='published max directional proxy' if (a,b) in m.route_blocks else '30min+great_circle/750; rounded5min'
            row['source']='stage17/evidence/directional_blocks.csv' if (a,b) in m.route_blocks else 'RouteModel.block and coordinates'
            row['source_commit']=CIRI
            calendar.append(row)
    table(ROOT/'ciri/principal_calendar.csv',calendar)
    caps=read(ROOT/'ciri/flight_capacity.csv')
    legs={(l['profile'],l['network'],l['id']):l for l in calendar}
    physical=[]
    for c in caps:
        l=legs[c['profile'],c['network'],c['flight_id']]
        assert int(c['block_minutes'])==l['block_minutes']
        # UTC minute counters start at 00:00 UTC on the model Monday.
        start=dt.datetime(2026,12,7,tzinfo=dt.timezone.utc)
        physical.append(dict(model_id='ciri_route_model',author_ref='Цири/mput',source_commit=CIRI,
            input_set_id='ciri_93fa_saved_inputs',run_id='AUTHOR_REPLAY',mode='AUTHOR_REPLAY',
            scenario_id=c['scenario'],candidate_id=c['network'],profile=c['profile'],
            physical_leg_id=c['flight_id'],origin=c['origin'],destination=c['destination'],aircraft=l['aircraft'],
            departure_utc=(start+dt.timedelta(minutes=l['departure_utc_minute'])).isoformat(),
            arrival_utc=(start+dt.timedelta(minutes=l['arrival_utc_minute'])).isoformat(),
            seats=c['capacity_scenario'],occupied=c['occupied'],block_minutes=c['block_minutes'],
            flight_variable_cost_rub=c['flight_variable_cost'],original_block_method=l['original_block_method'],
            corrected_block_method=l['block_method'],physical_status='SCENARIO_CALENDAR_NOT_DISPATCH_CLEARANCE'))
    table(OUT/'physical_leg.csv',physical)
    itinerary=[];incidence=[];money=[];markets={}
    for i,s in enumerate(read(ROOT/'ciri/itinerary_sales.csv')):
        key=f"{s['profile']}|{s['network']}|{s['scenario']}|I{i:03}"
        meta=dict(model_id='ciri_route_model',author_ref='Цири/mput',source_commit=CIRI,
                  input_set_id='ciri_93fa_saved_inputs',run_id='AUTHOR_REPLAY',mode='AUTHOR_REPLAY',
                  scenario_id=s['scenario'],candidate_id=s['network'],profile=s['profile'],
                  period_start='2026-12-07',period_end='2026-12-13',direction_scope='DIRECTED_ENDPOINT_OD',
                  market_unit='SCENARIO_ENDPOINT_OD',currency='RUB',
                  price_basis='net realised scenario fare per one-way journey',tax_basis='ex recoverable VAT',
                  value_status='SCENARIO_ASSUMPTION',acceptance_scope='AUTHOR_REPLAY_MATCHED_AND_CALENDAR_ACCOUNTING')
        itinerary.append(dict(meta,itinerary_id=key,origin=s['origin'],destination=s['destination'],
                              model_day=s['day'],trips=s['sold_journeys'],segments=s['segment_pax'],
                              transfer=s['transfer'],fare_once=s['fare_once']))
        for seq,flight_id in enumerate(s['flight_ids'].split(';'),1):
            assert (s['profile'],s['network'],flight_id) in legs
            incidence.append(dict(meta,itinerary_id=key,sequence=seq,physical_leg_id=flight_id,seats=s['sold_journeys']))
        for entry in ('gross_revenue','foregone_RW_revenue','new_pax_variable','saved_old_pax_variable'):
            money.append(dict(meta,itinerary_id=key,entry=entry,amount_rub=s[entry],
                              sign_in_contribution=1 if entry in ('gross_revenue','saved_old_pax_variable') else -1))
        mk=(s['profile'],s['network'],s['scenario'],s['origin'],s['destination'])
        if mk not in markets:
            markets[mk]=dict(meta,market_id='-'.join((s['origin'],s['destination'])),D=s['D'],
                             source_grain='AUTHOR_SCENARIO_WEEKLY_ONE_DIRECTION_OD',
                             observed_endpoint_demand=False,existing_RW_direct_seat_cap=s['known_direct_RW_capacity'])
    for p in physical:
        money.append(dict(model_id='ciri_route_model',source_commit=CIRI,scenario_id=p['scenario_id'],
                          candidate_id=p['candidate_id'],profile=p['profile'],physical_leg_id=p['physical_leg_id'],
                          entry='flight_variable_cost',amount_rub=p['flight_variable_cost_rub'],sign_in_contribution=-1))
    table(OUT/'itinerary.csv',itinerary);table(OUT/'itinerary_leg.csv',incidence)
    table(OUT/'capacity_allocation.csv',incidence);table(OUT/'money_ledger.csv',money)
    table(OUT/'market_pool.csv',markets.values())
    candidate=[];summary=[]
    for row in read(ROOT/'evaluation_summary.csv')+read(ROOT/'market_bound_only_summary.csv'):
        r=dict(row,mode='AUTHOR_REPLAY' if row['run_id']=='AUTHOR_REPLAY' else 'CORRECTED_REPLAY',
               route_definition='hub spokes OR reversible triangle programs; see route_definitions.csv',
               source_grain='ANNUALIZED_SYNTHETIC_SYMMETRIC_WEEK',
               money_definition='GROSS_REVENUE_MINUS_NEW_VARIABLE_COST_NO_RW_MIGRATION',
               resource_envelope_id='ANASTASIA_9_WORKING_PLUS_1_RESERVE',
               common_numeric_comparison_allowed=False,
               incompatibility_reason='undated annualisation; resource envelope and money definition differ from Ciri',
               full_budget=None,net_new_RW_journeys=None,
               missing_reason='no full fixed/donor budget; no author migration; no dated calendar')
        summary.append(r)
        candidate.append(dict(model_id=r['model_id'],source_commit=AUTHOR,author_ref=r['author_ref'],
                              candidate_id=r['candidate_id'],run_id=r['run_id'],scenario_id=r['scenario_id'],
                              mechanism='AUTHOR_SYNTHETIC_NEW_PROGRAM',decision_status='AUTHOR_PROPOSAL' if r['run_id']=='AUTHOR_REPLAY' else 'AGENT_PROPOSAL',
                              baseline='author same inputs',readiness='CONDITIONAL_ACCOUNTING_NOT_MARKET_VALIDATED'))
    resources=[]
    for row in read(ROOT/'ciri/context/21_team_proposals/comparison.csv'):
        r=dict(row,model_id='ciri_route_model',source_commit=CIRI,author_ref='Цири/mput',
               mode='AUTHOR_REPLAY',run_id='AUTHOR_REPLAY',input_set_id='ciri_93fa_saved_inputs',
               scenario_id=row['scenario'],candidate_id=row['network'],period_start='2026-12-07',period_end='2026-12-13',
               direction_scope='SUM_DIRECTED_ENDPOINT_OD',market_unit='SCENARIO_ENDPOINT_OD',currency='RUB',
               price_basis='net realised scenario one-way fare',tax_basis='ex recoverable VAT',value_status='SCENARIO_ASSUMPTION',
               acceptance_scope='AUTHOR_REPLAY_MATCHED;DATED_CAPACITY_AND_MONEY_ACCOUNTING',
               source_grain='DATED_SCENARIO_WEEK',money_definition='INCREMENT_AFTER_OWN_RW_MIGRATION_BEFORE_BASE_FLEET_OPPORTUNITY',
               resource_envelope_id='CIRI_4_WORKING_PLUS_1_RESERVE',route_definition='unique unordered physical airport pairs',
               full_budget=None,net_new_RW_journeys=None,
               missing_reason='fixed/startup/opportunity/cash budgets and lost business elsewhere incomplete',
               common_numeric_comparison_allowed=False,
               incompatibility_reason='different resource/date/money/input set from Anastasia; no harmonisation run')
        summary.append(r)
        resources.append(dict(model_id='ciri_route_model',source_commit=CIRI,candidate_id=row['network'],scenario_id=row['scenario'],
                              active_ceiling=4,reserve_assumption=1,actually_allocated=row['active_allocated'],
                              block_hours=row['weekly_block_hours'],status='MODEL_SCHEDULE_ALLOCATION_NOT_CONFIRMED_RW_RESOURCE'))
        candidate.append(dict(model_id='ciri_route_model',source_commit=CIRI,author_ref='Цири/mput',candidate_id=row['network'],
                              scenario_id=row['scenario'],run_id='AUTHOR_REPLAY',mechanism='ADD_PROGRAM_KEEP_EXISTING_RW',
                              decision_status='AUTHOR_PROPOSAL',readiness='CONDITIONAL_NOT_ACTUAL_REPLACEMENT_OR_SEASON'))
    table(OUT/'evaluation_summary.csv',summary);table(OUT/'candidate_register.csv',candidate)
    table(OUT/'resource_ledger.csv',resources)
    params=[]
    for p in read(ROOT/'author/data/assumptions/network.csv'):
        for scen in ('base','cautious'):
            params.append(dict(model_id='anastasia_network',source_commit=AUTHOR,parameter=p['parameter'],scenario_id=scen,
                               value=p[scen],unit=p['unit'],author_source=p['source'],decision_status='AUTHOR_PROPOSAL',
                               range_meaning='named author scenarios, not statistical confidence interval'))
    table(OUT/'parameter_registry.csv',params)
    js(OUT/'status.json',dict(status='PROPOSED_ADAPTER_NOT_COMMON_COMPARISON',
        common_comparison_run=False,methods_commit='344f4425ba3fbb73b45a5cbcd223089e2ca7b5d4',
        methods_independent_review='PENDING',
        anastasia_aggregate_tables='../ledgers/; never treated as dated physical_leg',
        ciri_physical_legs=len(physical),ciri_itineraries=len(itinerary),
        missing=['Anastasia dated physical_leg/calendar','complete fixed/cash/donor budgets','observed endpoint OD'],
        no_new_financial_replay=True))
    print(json.dumps(dict(status='PASS',common_comparison=False,dated_legs=len(physical),itineraries=len(itinerary))))


if __name__=='__main__':main()
