#!/usr/bin/env python3
"""Offline executable package: author replay, shared-pair repair, complete deltas."""
import contextlib
import csv
import hashlib
import importlib
import json
import math
import platform
import shutil
import socket
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import numpy as np
import corrected_model as fix

ROOT = Path(__file__).resolve().parent
SOURCE = '2f03b693a62c219e9475fcd1e26295039f6a49d7'
MODES = ['AUTHOR_REPLAY','CORRECTED_FIXED_SELECTION','CORRECTED_RESELECTED','CORRECTED_CLAIM_ALLOCATION']
EXPORTS = ['network_routes.csv','network_summary.csv','mandatory_routes_table.csv']


def js(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def table(path, rows):
    rows=list(rows)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        fields=list(dict.fromkeys(k for r in rows for k in r))
        w=csv.DictWriter(f,fields,lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def close(x,y):
    return math.isclose(x,y,rel_tol=1e-10,abs_tol=1e-6)


def ledger(nm,D,A,mode,scen,candidate,hub_result=None,direct=None,capture_law='author_at_total_frequency'):
    W=A['weeks_per_year']; multiplier=2*W
    meta=dict(model_id='anastasia_network_shared_pair_v1' if mode!='AUTHOR_REPLAY' else 'anastasia_network_author',
              author_ref='Анастасия/kiruha355' if mode=='AUTHOR_REPLAY' else 'Codex/Sol repair of Анастасия/kiruha355',
              source_commit=SOURCE,input_set_id='anastasia_2f03_saved_inputs',run_id=mode,
              scenario_id=scen,candidate_id=candidate,period_start=None,period_end=None,
              period_reason='annualized scenario; no dated flight calendar',direction_scope='BOTH_DIRECTIONS_SYMMETRIC',
              market_unit='SCENARIO_ENDPOINT_JOURNEYS_FROM_SEGMENT_PROXY',currency='RUB',
              source_grain='UNDATED_SYMMETRIC_PAIR_AGGREGATE_NOT_PHYSICAL_FLIGHT',
              price_basis='author_scenario_fare',tax_basis=None,tax_basis_reason='not specified by author',
              value_status='SCENARIO_ASSUMPTION',acceptance_scope='AGGREGATE_WEEKLY_CONSERVATION_ONLY')
    itineraries=[]; physical={}; pool=[]

    def leg(L):
        key='-'.join(fix.pair(L['a'],L['b']))
        if key not in physical:
            physical[key]=dict(physical_leg_id=key,origin=min(L['a'],L['b']),destination=max(L['a'],L['b']),
                               date=None,date_reason='author_has_no_calendar',frequency_each_direction=0.,
                               offered_seats=0.,seats_at_lf_max=0.,occupied=0.)
        p=physical[key]
        p['frequency_each_direction']+=L['freq']
        p['offered_seats']+=multiplier*L['freq']*A['seats']
        p['seats_at_lf_max']+=multiplier*L['freq']*A['seats']*A['lf_max']
        p['occupied']+=multiplier*L['carried_dir_week']
        return key

    def itinerary(identifier,a,b,weekly,km,legs,transfer=False):
        trips=weekly*multiplier
        one_fare=nm.fare(A,km)*(A['transfer_fare_factor'] if transfer else 1.)
        itineraries.append(dict(itinerary_id=identifier,market_id='-'.join(fix.pair(a,b)),origin=a,destination=b,
                                annual_trips=trips,transfer=transfer,leg_ids=';'.join(legs),leg_count=len(legs),
                                annual_segments=trips*len(legs),fare_once=one_fare,gross_revenue=trips*one_fare))

    if hub_result is not None:
        legs,trans,h,c,r,od_l,od_t,flights=hub_result
        for X,L in legs.items():
            key=leg(L)
            itinerary('LOCAL_'+X,L['a'],L['b'],L['local_carried'],L['km'],[key])
        for X,Y,km,t in trans:
            itinerary('TRANSFER_'+X+'_'+Y,X,Y,t,km,
                      ['-'.join(fix.pair(candidate,X)),'-'.join(fix.pair(candidate,Y))],True)
    else:
        h,c,r,_=fix.totals(direct)
        for ci,program in enumerate(direct):
            for li,L in enumerate(program[8]):
                key=leg(L)
                itinerary(f'T{ci}_L{li}',L['a'],L['b'],L['carried_dir_week'],L['km'],[key])
        # One scenario budget per pair, including the baseline's actual overclaim.
        _,pool=fix.evaluate(nm,fix.from_author(direct),A,capture_law=capture_law)
        for row in pool:
            row['actual_sold']=physical[row['pair']]['occupied']/multiplier
            row['actual_excess_over_pool']=max(0.,row['actual_sold']-row['captured_pool'])

    travel=sum(i['annual_trips'] for i in itineraries)
    segments=sum(i['annual_segments'] for i in itineraries)
    transfers=sum(i['annual_trips'] for i in itineraries if i['transfer'])
    gross=sum(i['gross_revenue'] for i in itineraries)
    assert close(segments,travel+transfers)
    assert close(segments,sum(p['occupied'] for p in physical.values()))
    assert close(gross,r*W)
    assert all(p['occupied'] <= p['seats_at_lf_max']+1e-6 for p in physical.values())
    out=ROOT/'ledgers'/mode/scen/candidate
    table(out/'itinerary.csv',({**meta,**i} for i in itineraries))
    incidence=[{**meta,'itinerary_id':i['itinerary_id'],'physical_leg_id':l,'occupied':i['annual_trips']}
               for i in itineraries for l in i['leg_ids'].split(';')]
    table(out/'itinerary_leg.csv',incidence)
    table(out/'capacity_allocation.csv',incidence)
    table(out/'physical_leg.csv',({**meta,**p} for p in physical.values()))
    table(out/'market_pool.csv',({**meta,**p} for p in pool))
    table(out/'money_ledger.csv',[
        {**meta,'entry':'gross_revenue','annual_rub':gross,'status':'SCENARIO_CALCULATED'},
        {**meta,'entry':'new_pax_variable_cost','annual_rub':segments*A['pax_cost_rub'],'status':'SCENARIO_CALCULATED'},
        {**meta,'entry':'flight_variable_cost','annual_rub':c*W-segments*A['pax_cost_rub'],'status':'SCENARIO_CALCULATED'},
        {**meta,'entry':'cannibalization_foregone_revenue','annual_rub':None,'status':'NOT_MODELED_BY_AUTHOR'},
        {**meta,'entry':'full_strategy_budget','annual_rub':None,'status':'UNKNOWN_NOT_ZERO'}])
    table(out/'resource_ledger.csv',[{**meta,'weekly_block_hours':h,
        'working_aircraft_ceiling':A['fleet_cap']-A['spare_aircraft'],'reserve_assumption':A['spare_aircraft'],
        'used_aircraft_hour_equivalent':h/(A['block_h_per_day']*7),
        'calendar_aircraft_allocation':None,'calendar_reason':'weekly hours do not prove a feasible dated rotation'}])
    return {**meta,'annual_trips':travel,'annual_segments':segments,'annual_transfer_trips':transfers,
            'annual_gross_revenue_rub':gross,'annual_variable_cost_rub':c*W,
            'annual_contribution_before_base_fleet_opportunity_rub':(r-c)*W,
            'weekly_block_hours':h,'weekly_flights':sum(p['frequency_each_direction']*2 for p in physical.values()),
            'pool_excess_annual':sum(p['actual_excess_over_pool'] for p in pool)*multiplier,
            'pool_capture_annual':sum(p['captured_pool'] for p in pool)*multiplier if pool else None,
            'seats_offered_annual':sum(p['offered_seats'] for p in physical.values()),
            'conservation':'PASS_AGGREGATE','dated_capacity':'NOT_RUN_NO_AUTHOR_CALENDAR',
            'cannibalization':'NOT_MODELED_BY_AUTHOR'}


def main():
    # Every replay invocation is network-free, including imported author code.
    def denied(*args,**kwargs):
        raise RuntimeError('OFFLINE_REPLAY_NETWORK_FORBIDDEN')
    socket.create_connection=denied
    socket.socket.connect=denied
    sys.path.insert(0,str(ROOT/'author/src'))
    nm=importlib.import_module('network_model')
    original_direct=nm.direct_network; original_hub=nm.hub_network
    original_P=nm.P
    saved_direct={}; summaries=[]; captured_hubs={}; outputs={}
    for mode in MODES:
        dest=ROOT/'outputs'/mode
        dest.mkdir(parents=True,exist_ok=True)
        for name in ['demand_fit.json','demand_pairs.csv','kover_days.csv','longlist.csv','longlist_scores_min500.csv']:
            shutil.copyfile(original_P/name,dest/name)
        nm.P=dest

        def direct(D,A,scen,nodes_all):
            if mode=='AUTHOR_REPLAY':
                result=original_direct(D,A,scen,nodes_all)
                saved_direct[scen]=result
            elif mode=='CORRECTED_RESELECTED':
                result=fix.select(nm,D,A,scen,nodes_all)
            else:
                allocation='standalone_claim' if mode=='CORRECTED_CLAIM_ALLOCATION' else 'frequency'
                result,_=fix.evaluate(nm,fix.from_author(saved_direct[scen]),A,allocation)
            summaries.append(ledger(nm,D,A,mode,scen,'DIRECT',direct=result))
            outputs[mode,scen]=result
            return result

        def hub(H,D,A,scen,nodes_all):
            # The correction leaves author hub outputs byte-for-byte at CSV value level.
            key=(H,scen)
            if key not in captured_hubs:
                captured_hubs[key]=original_hub(H,D,A,scen,nodes_all)
            chosen,result=captured_hubs[key]
            summaries.append(ledger(nm,D,A,mode,scen,H,hub_result=result))
            return chosen,result

        nm.direct_network=direct; nm.hub_network=hub
        with (dest/'run.log').open('w') as f,contextlib.redirect_stdout(f):
            nm.main()
    nm.P=original_P; nm.direct_network=original_direct; nm.hub_network=original_hub
    comparisons=[]
    for name in EXPORTS:
        expected=ROOT/'frozen_exports'/name
        actual=ROOT/'outputs/AUTHOR_REPLAY'/name
        a=pd.read_csv(expected).fillna(''); b=pd.read_csv(actual).fillna('')
        assert list(a.columns)==list(b.columns) and a.shape==b.shape
        diff=a.ne(b)
        n=int(diff.sum().sum())
        assert n==0,(name,n)
        comparisons.append(dict(file=name,rows=len(a),columns=len(a.columns),differing_cells=n,
                                semantic_exact_match=True,byte_exact_match=expected.read_bytes()==actual.read_bytes(),
                                byte_difference_reason='source CRLF vs runtime LF; network_summary also signed zero',
                                expected_sha256=hashlib.sha256(expected.read_bytes()).hexdigest(),
                                replay_sha256=hashlib.sha256(actual.read_bytes()).hexdigest()))
    table(ROOT/'author_export_comparison.csv',comparisons)
    table(ROOT/'evaluation_summary.csv',summaries)
    deltas=[]
    metrics=['annual_trips','annual_segments','annual_gross_revenue_rub','annual_variable_cost_rub',
             'annual_contribution_before_base_fleet_opportunity_rub','weekly_block_hours',
             'weekly_flights','pool_excess_annual','seats_offered_annual']
    for mode in MODES[1:]:
        for row in [r for r in summaries if r['run_id']==mode]:
            baseline=next(r for r in summaries if r['run_id']=='AUTHOR_REPLAY'
                          and r['scenario_id']==row['scenario_id'] and r['candidate_id']==row['candidate_id'])
            deltas.append(dict(run_id=mode,scenario_id=row['scenario_id'],candidate_id=row['candidate_id'],
                               **{key+'_before':baseline[key] for key in metrics},
                               **{key+'_after':row[key] for key in metrics},
                               **{key+'_delta':row[key]-baseline[key] for key in metrics}))
    table(ROOT/'before_after.csv',deltas)
    ranks=[]
    for mode in MODES:
        for scen in ('base','cautious'):
            rows=[r for r in summaries if r['run_id']==mode and r['scenario_id']==scen]
            for rank,row in enumerate(sorted(rows,key=lambda r:-r['annual_contribution_before_base_fleet_opportunity_rub']),1):
                ranks.append(dict(run_id=mode,scenario_id=scen,rank=rank,candidate_id=row['candidate_id'],
                                  annual_contribution_rub=row['annual_contribution_before_base_fleet_opportunity_rub'],
                                  status='CONDITIONAL_VARIABLE_CONTRIBUTION_NOT_STRATEGY_RANK'))
    table(ROOT/'conditional_ranks.csv',ranks)
    selections=[]
    for (mode,scen),chosen in outputs.items():
        for c in chosen:
            selections.append(dict(run_id=mode,scenario_id=scen,triangle='-'.join(c[1:4]),frequency=c[8][0]['freq'],
                                   weekly_block_hours=c[4],annual_contribution_rub=(c[6]-c[5])*nm.load_assumptions()[scen]['weeks_per_year']))
    table(ROOT/'selected_triangles.csv',selections)
    # Exact current shared-pair example, before rounding individual route CSV rows.
    examples=[]
    for scen in ('base','cautious'):
        A=nm.load_assumptions()[scen]; W=A['weeks_per_year']
        chosen=saved_direct[scen]
        legs=[L for c in chosen for L in c[8] if fix.pair(L['a'],L['b'])==('MOW','OMS')]
        F=sum(L['freq'] for L in legs); L=legs[0]
        exact=sum(L['carried_dir_week'] for L in legs)*2*W
        pool=L['dem']*nm.leg_share(L,F,A)*2*W
        stored=sum(round(L['carried_dir_week']*2*W) for L in legs)
        examples.append(dict(scenario=scen,pair='MOW-OMS',annual_input_market=L['dem']*2*W,
                             frequencies=[L['freq'] for L in legs],total_frequency=F,
                             before_exact=exact,before_sum_rounded_rows=stored,common_pool_exact=pool,
                             common_pool_rounded=round(pool),exact_excess=exact-pool,
                             cited_rounded_excess=stored-round(pool),unit='annual scenario journeys both directions'))
    js(ROOT/'shared_pair_example.json',examples)
    js(ROOT/'replay_validation.json',dict(status='PASS',author_exports=comparisons,
        corrected_modes=MODES[1:],scenarios=2,ledger_networks=len(summaries),network_blocked=True,
        environment=dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__,platform=platform.platform()),
        frequency_policy='AUTHOR_STANDALONE_FIXED; pooled total frequency; marginal network reselection',
        acceptance=['RAW_HASH_VERIFIED','EXTRACTION_CHECKED','AUTHOR_REPLAY_MATCHED','CONSERVATION_PASS'],
        acceptance_scope='CSV value match and aggregate weekly flow/money accounting; not dated schedule or observed OD',
        independent_review='PENDING',source_supported_endpoint_demand=False,full_profitability=False))
    print(json.dumps(dict(status='PASS',networks=len(summaries),author_csv_differing_cells=0)))


if __name__=='__main__':
    main()
