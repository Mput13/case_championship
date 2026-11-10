#!/usr/bin/env python3
"""Counterexamples and external accounting oracles; no new paid/live execution."""
import csv
import json
import math
import sys
import datetime as dt
from collections import defaultdict
from pathlib import Path

import corrected_model as fix
from replay import table,js

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'author/src'))
import network_model as nm


def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))


def eq(a,b):
    assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-6),(a,b)


def oracle_pool(L,F,A):
    # Deliberately independent of nm.leg_share / fix.evaluate.
    if L['km']<A['transfer_min_km']:return 0.
    if L['competitive']:
        competitor=L['dem']/(A['seats']*A['competitor_lf'])
        share=min(A['capture_competitive'],F/(F+competitor)) if competitor else 0.
    else:share=A['capture_open']*(1-math.exp(-F/A['capture_freq_scale']))
    return L['dem']*share


def group_oracle(chosen,A):
    groups=defaultdict(list)
    for c in chosen:
        for L in c[8]:groups[tuple(sorted((L['a'],L['b'])))].append(L)
    rows=[]
    for key,legs in groups.items():
        F=sum(L['freq'] for L in legs)
        p=oracle_pool(legs[0],F,A)
        sold=sum(L['carried_dir_week'] for L in legs)
        rows.append(dict(pair='-'.join(key),programs=len(legs),frequency=F,pool=p,sold=sold,excess=max(0,sold-p)))
    return rows


def main():
    checks=[]; counterexamples=[]
    A=nm.load_assumptions()['base']
    class TinyDemand:
        def km(self,a,b):
            if 'SVX' in (a,b):return 10000.
            return 1000. if 'MOW' in (a,b) else 700.
        def get(self,a,b,scen):return 104000.
        def green(self,a,b):return 3000.
        def south(self,a,b):return False
        def has_direct(self,a,b):return set((a,b))=={'MOW','A'}
    tiny=dict(A,min_routes=3,max_routes=3,min_freq_week=3,direct_max_freq_week=3,fleet_cap=100)
    nodes=['MOW','SVX','A','B','C'];D=TinyDemand()
    old=nm.direct_network(D,tiny,'base',nodes)
    assert len(old)==3
    before=group_oracle(old,tiny)
    assert sum(r['excess'] for r in before)>0, 'fixture must reject original code'
    for allocation in ('frequency','standalone_claim'):
        corrected,pools=fix.evaluate(nm,fix.from_author(old),tiny,allocation)
        after=group_oracle(corrected,tiny)
        assert all(r['excess']<1e-8 for r in after)
        for row in after:
            key=row['pair']
            cap=sum(L['freq']*tiny['seats']*tiny['lf_max'] for c in corrected for L in c[8]
                    if '-'.join(sorted((L['a'],L['b'])))==key)
            eq(row['sold'],min(row['pool'],cap))
        counterexamples.extend(dict(fixture='three_triangles',allocation=allocation,**r) for r in after)
    counterexamples.extend(dict(fixture='three_triangles_original',allocation='independent_author_claim',**r) for r in before)
    checks.append(dict(name='shared_pair_multiple_triangles',status='PASS',original_code_rejected=True))
    selected=fix.select(nm,D,tiny,'base',nodes)
    assert len(selected)==3 and all(r['excess']<1e-8 for r in group_oracle(selected,tiny))
    checks.append(dict(name='marginal_selection_shared_pool',status='PASS'))

    # Reverse orientation is the same physical pool. Asymmetric program frequencies
    # split one shared budget in 1:3 proportions; no per-direction double counting.
    L=dict(a='MOW',b='OMS',km=1000.,south=False,competitive=True,dem=1000.)
    sample=[dict(B='MOW',X='OMS',Y='X',freq=1,legs=[L]),
            dict(B='MOW',X='OMS',Y='Y',freq=3,legs=[dict(L,a='OMS',b='MOW')])]
    corrected,pools=fix.evaluate(nm,sample,A)
    p0=corrected[0][8][0]['carried_dir_week'];p1=corrected[1][8][0]['carried_dir_week']
    expected=1000*4/(4+1000/(100*.8))
    eq(p0+p1,expected);eq(p1/p0,3)
    assert len(pools)==1
    checks.append(dict(name='asymmetric_frequency_reverse_pair',status='PASS'))
    counterexamples.append(dict(fixture='asymmetric_1_3',pair='MOW-OMS',sold=p0+p1,pool=expected,
                                first_program=p0,second_program=p1,annual_both_directions=(p0+p1)*104))
    # A high capture cannot create seats. A saturated allocation spills explicitly.
    crowded=[dict(t,legs=[dict(t['legs'][0],dem=1e7,competitive=False)]) for t in sample]
    corrected,pools=fix.evaluate(nm,crowded,A)
    eq(sum(L['carried_dir_week'] for c in corrected for L in c[8]),4*100*.85)
    assert pools[0]['spill']>0
    eq(sum(fix.weighted_capped(300,[1,3],[20,200])),220)
    assert fix.weighted_capped(150,[1,3],[20,200])==[20.,130.]
    checks.append(dict(name='capacity_spill_and_redistribution',status='PASS'))
    counterexamples.append(dict(fixture='spill',**pools[0]))
    many=[dict(B='MOW',X='OMS',Y=str(i),freq=3,
               legs=[dict(L,competitive=False,dem=1000.)]) for i in range(4)]
    bound,boundp=fix.evaluate(nm,many,A,'standalone_claim','market_bound_only')
    curve,curvep=fix.evaluate(nm,many,A)
    bound_sold=sum(c[7]/2 for c in bound);curve_sold=sum(c[7]/2 for c in curve)
    eq(bound_sold,1000.)
    assert 4*min(1000*.65*(1-math.exp(-1)),3*100*.85)>1000
    eq(curve_sold,1000*.65*(1-math.exp(-4)))
    assert curve_sold < bound_sold
    assert fix.weighted_capped(100,[1,2],[0,0])==[0.,0.]
    checks.append(dict(name='mandatory_D_cap_distinct_from_scenario_capture_curve',status='PASS',
                        source_saved_pairs_exceed_D=False,synthetic_original_exceeds_D=True))
    counterexamples.append(dict(fixture='minimum_D_cap_vs_pooled_curve',market=1000.,
                                original_seat_capped_claims=1020.,D_bound_sold=bound_sold,
                                pooled_curve_sold=curve_sold,method_choice='AGENT_PROPOSAL'))

    class HubDemand:
        def km(self,a,b):return {frozenset(('H','X')):600,frozenset(('H','Y')):900,
                                 frozenset(('X','Y')):1300}[frozenset((a,b))]
        def get(self,a,b,s):return {frozenset(('H','X')):120000,frozenset(('H','Y')):20000,
                                    frozenset(('X','Y')):100000}[frozenset((a,b))]
        def green(self,a,b):return 3000
        def south(self,a,b):return False
        def has_direct(self,a,b):return False
    ha=dict(A,min_routes=2,max_routes=2,fleet_cap=100)
    _,r=nm.hub_network('H',HubDemand(),ha,'base',['H','X','Y'])
    legs,trans,h,c,rev,od_local,od_transfer,flights=r
    assert {v['freq'] for v in legs.values()}=={14,6}
    assert len(trans)==1
    t=trans[0][3]
    for L in legs.values():
        eq(L['transfer_carried'],t)
        eq(L['carried_dir_week'],L['local_carried']+t)
        assert L['carried_dir_week']<=L['freq']*ha['seats']*ha['lf_max']+1e-6
    local=sum(L['local_carried'] for L in legs.values())
    eq(od_local+od_transfer,2*(local+t))
    eq(sum(2*L['carried_dir_week'] for L in legs.values()),2*local+4*t)
    one_through=(2093+6.30*1300)*.90
    expected_local=sum(2*L['local_carried']*(2093+6.30*L['km']) for L in legs.values())
    eq(rev,expected_local+2*t*one_through)
    wrong_sum_leg_fares=expected_local+2*t*((2093+6.30*600)+(2093+6.30*900))*.90
    assert abs(wrong_sum_leg_fares-rev)>1000
    checks.append(dict(name='hub_asymmetric_local_transfer_one_through_fare_return_vs_oneway',status='PASS',
                        frequencies=[14,6],old_front2272_defect_reintroduced=False))
    counterexamples.append(dict(fixture='hub_14_6',weekly_both_direction_trips=od_local+od_transfer,
                                weekly_transfer_trips=od_transfer,
                                weekly_segments=sum(2*L['carried_dir_week'] for L in legs.values()),
                                weekly_revenue=rev,wrong_two_leg_fares=wrong_sum_leg_fares,
                                annual_trips=(od_local+od_transfer)*52,annual_revenue=rev*52))

    # All actual ledger rows are checked independently of the implementation's sums.
    counts=dict(networks=0,itineraries=0,incidences=0,physical_legs=0,corrected_pools=0)
    for path in sorted((ROOT/'ledgers').rglob('itinerary.csv')):
        it=read(path);inc=read(path.with_name('itinerary_leg.csv'));legs=read(path.with_name('physical_leg.csv'))
        ids={i['itinerary_id']:i for i in it}
        eq(sum(float(i['annual_segments']) for i in it),sum(float(l['occupied']) for l in legs))
        eq(sum(float(i['annual_segments']) for i in it),sum(float(i['annual_trips'])*(2 if i['transfer']=='True' else 1) for i in it))
        for row in inc:eq(float(row['occupied']),float(ids[row['itinerary_id']]['annual_trips']))
        for L in legs:
            eq(float(L['occupied']),sum(float(i['occupied']) for i in inc if i['physical_leg_id']==L['physical_leg_id']))
            assert float(L['occupied'])<=float(L['seats_at_lf_max'])+1e-6
        money={r['entry']:r for r in read(path.with_name('money_ledger.csv'))}
        eq(sum(float(i['annual_trips'])*float(i['fare_once']) for i in it),float(money['gross_revenue']['annual_rub']))
        assert money['cannibalization_foregone_revenue']['status']=='NOT_MODELED_BY_AUTHOR'
        pools=read(path.with_name('market_pool.csv'))
        if it[0]['run_id']!='AUTHOR_REPLAY':
            for p in pools:
                assert float(p['actual_sold'])<=float(p['captured_pool'])+1e-8
                counts['corrected_pools']+=1
        counts['networks']+=1;counts['itineraries']+=len(it);counts['incidences']+=len(inc);counts['physical_legs']+=len(legs)
    checks.append(dict(name='all_actual_output_rows_conservation_and_money',status='PASS',**counts))
    # Fixed allocation variants must agree on economics, without pretending that
    # allocation between programs is identified from observed demand.
    summaries=read(ROOT/'evaluation_summary.csv')
    for scen in ('base','cautious'):
        f=next(r for r in summaries if r['run_id']=='CORRECTED_FIXED_SELECTION' and r['scenario_id']==scen and r['candidate_id']=='DIRECT')
        c=next(r for r in summaries if r['run_id']=='CORRECTED_CLAIM_ALLOCATION' and r['scenario_id']==scen and r['candidate_id']=='DIRECT')
        for key in ('annual_trips','annual_gross_revenue_rub','annual_variable_cost_rub'):eq(float(f[key]),float(c[key]))
    checks.append(dict(name='two_allocation_variants_economics_invariant_at_fixed_frequencies',status='PASS'))
    ciri=json.loads((ROOT/'ciri/replay_validation.json').read_text())
    assert ciri['status']=='PASS' and len(ciri['checks'])==8
    checks.append(dict(name='ciri_actual_dated_incidence_fare_migration_budgets',status='PASS',
                        reference='ciri/replay_validation.json',comparisons=8,dated_legs=160))
    methods=json.loads((ROOT/'methods_requests_response.json').read_text())
    assert methods['MR06']['flight_time_changes']==0 and methods['MR06']['saved_legs_checked']==1372
    checks.append(dict(name='MR06_pinned_block_values_match_actual_function',status='PASS',legs=1372,
                        metadata_corrected_separately=True,financial_replay_repeated=False))
    common=ROOT/'proposed_common_view'
    physical=read(common/'physical_leg.csv');inc=read(common/'itinerary_leg.csv')
    its=read(common/'itinerary.csv')
    def flight_key(r):return (r['profile'],r['candidate_id'],r['scenario_id'],r['physical_leg_id'])
    physical_by_key={flight_key(r):r for r in physical}
    assert len(physical_by_key)==len(physical)==160
    for r in physical:
        used=sum(float(i['seats']) for i in inc if flight_key(i)==flight_key(r))
        eq(used,float(r['occupied']))
        assert used<=float(r['seats'])+1e-6
    for i in its:
        ii=sorted([r for r in inc if r['itinerary_id']==i['itinerary_id']],key=lambda r:int(r['sequence']))
        ff=[physical_by_key[flight_key(r)] for r in ii]
        assert ff[0]['origin']==i['origin'] and ff[-1]['destination']==i['destination']
        assert len(ff)==(2 if i['transfer']=='True' else 1)
        for a,b in zip(ff,ff[1:]):
            assert a['destination']==b['origin']
            minutes=(dt.datetime.fromisoformat(b['departure_utc'])-dt.datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
            assert 60<=minutes<=240
    money=read(common/'money_ledger.csv')
    comparisons=read(ROOT/'ciri/context/21_team_proposals/comparison.csv')
    for r in comparisons:
        mm=[m for m in money if m['profile']==r['profile'] and m['candidate_id']==r['network'] and m['scenario_id']==r['scenario']]
        eq(sum(float(m['amount_rub'])*int(m['sign_in_contribution']) for m in mm),float(r['contribution_before_base_fleet_opportunity']))
    checks.append(dict(name='common_adapter_join_incidence_time_and_money',status='PASS',
                        dated_legs=160,itineraries=len(its),cross_model_economic_comparison=False))
    extracted=json.loads((ROOT/'extraction_validation.json').read_text())
    assert extracted['direct_sets_identical'] and extracted['rail_series_identical']
    checks.append(dict(name='raw_projection_native_links_exact_equivalence',status='PASS',
                        air_links=extracted['directed_air_links'],rail_rows=extracted['rail_rows']))
    table(ROOT/'counterexamples.csv',counterexamples)
    js(ROOT/'checks.json',dict(status='PASS',checks=checks,check_groups=len(checks),
                              author_baseline_expected_to_fail_shared_pair=True,
                              independent_review='PENDING',
                              not_run=['Anastasia dated schedule capacity: no input calendar',
                                       'Anastasia cannibalization: absent from author model',
                                       'observed endpoint OD validation','commercial execution','full strategy budget']))
    print(json.dumps(dict(status='PASS',check_groups=len(checks),actual_rows=counts)))


if __name__=='__main__':main()
