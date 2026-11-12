#!/usr/bin/env python3
"""Independent delivered-table audit, standard library and Decimal only.

Does not import replay.py, numpy, pandas or author model functions.
"""
import collections
import csv
import decimal
import json
from pathlib import Path

P=Path(__file__).resolve().parent
D=decimal.Decimal
decimal.getcontext().prec=35


def rows(name):
    return list(csv.DictReader((P/name).open()))


def n(r,k):
    return D(r[k])


def near(a,b,what):
    assert abs(a-b)<=max(D('.00001'),abs(a)*D('0.00000000001')),(what,str(a),str(b))


def run():
    nets={r['network_id']:r for r in rows('candidates.csv')}
    groups=collections.defaultdict(list)
    ods=collections.defaultdict(list)
    legrows=rows('network_legs.csv')
    for r in legrows:groups[r['network_id']].append(r)
    for r in rows('od_flows.csv'):ods[r['network_id']].append(r)
    for ident,ls in groups.items():
        z=nets[ident]
        W=n(z,'weeks_per_year')
        near(sum(n(l,'block_h_week') for l in ls),n(z,'block_h_week'),'leg hour sum')
        near(sum(n(l,'segments_year') for l in ls),n(z,'segments_year'),'leg segment sum')
        near(sum(n(l,'contribution_rub_year') for l in ls),n(z,'contribution_rub_year'),'leg money sum')
        near(n(z,'segments_year'),n(z,'local_od_year')+2*n(z,'transfer_od_year'),'network OD identity')
        assert n(z,'aircraft_including_one_spare')<=n(z,'construction_cap')
        assert n(z,'block_h_week')<=70*(n(z,'construction_cap')-1)+D('.000000001')
        allpairs={tuple(sorted((l['a'],l['b']))) for l in ls}
        assert len(allpairs)==int(z['unique_undirected_legs'])
        limit=D('.85') if z['demand_scenario']=='base' else D('.8')
        for l in ls:
            assert 0<=n(l,'segments_year')<=n(l,'seat_legs_year')*limit+D('.00001')
            near(n(l,'segments_year'),n(l,'local_od_year')+n(l,'transfer_segments_year'),'leg identity')
            near(n(l,'block_h_week'),2*n(l,'frequency_week_each_way')*n(l,'block_h_oneway'),'leg hours')
        oo=ods[ident]
        near(sum(n(o,'od_year')*n(o,'segments_per_od') for o in oo),n(z,'segments_year'),'OD membership')
        near(sum(n(o,'full_revenue_rub_year')-n(o,'current_rw_forgone_rub_year') for o in oo),n(z,'net_revenue_rub_year'),'through fare once')
        for o in oo:
            near(n(o,'full_revenue_rub_year'),n(o,'od_year')*n(o,'full_fare_rub'),'OD revenue')
    stressrows=rows('fixed_schedule_stress.csv')
    for s in stressrows:
        z=nets[s['network_id']]
        keep=n(s,'transfer_keep_fraction');comp=n(s,'fuel_compensation_rub_per_t')
        paxcost=D(500 if z['demand_scenario']=='base' else 650)
        comp0=D(32930 if z['demand_scenario']=='base' else 3024)
        marginal=n(z,'full_transfer_revenue_rub_year')-2*n(z,'transfer_od_year')*paxcost
        expected=n(z,'contribution_rub_year')+n(z,'fuel_t_year')*(comp-comp0)-(1-keep)*marginal
        near(expected,n(s,'contribution_rub_year'),'stress independent delta')
        near(n(s,'net_revenue_rub_year')-n(s,'variable_cost_rub_year'),expected,'stress money identity')
        near(n(s,'segments_year'),n(z,'local_od_year')+2*n(z,'transfer_od_year')*keep,'stress segments')
        near(n(s,'block_h_week'),n(z,'block_h_week'),'stress frozen hours')
        near(n(s,'flights_week'),n(z,'flights_week'),'stress frozen frequencies')
    comparison=rows('comparison.csv')
    envelopes=collections.defaultdict(list)
    for r in comparison:
        if r['status']!='ok':
            assert r['contribution_rub_year']==''
            continue
        z=nets[r['selected_network_id']]
        assert n(z,'aircraft_including_one_spare')<=n(r,'budget_aircraft')
        assert (8<=int(z['programs'])<=12) if z['product']=='author8_12' else (3<=int(z['programs'])<=6)
        near(n(z,'contribution_rub_year'),n(r,'contribution_rub_year'),'selected economics')
        envelopes[tuple(r[k] for k in ['demand_scenario','mode','product','alternative'])].append(r)
    for key,rr in envelopes.items():
        rr.sort(key=lambda r:n(r,'budget_aircraft'))
        for a,b in zip(rr,rr[1:]):
            assert n(b,'contribution_rub_year')>=n(a,'contribution_rub_year')-D('.000001'),key
    thresholds=rows('cross_product_thresholds.csv')
    for r in thresholds:
        i=nets[r['network_i']];j=nets[r['network_j']]
        near(n(i,'contribution_rub_year')-n(j,'contribution_rub_year'),n(r,'gap_rub_year'),'pair gap')
        if r['extra_common_hour_cost_equality_rub_h']:
            near(n(r,'extra_common_hour_cost_equality_rub_h')*n(r,'annual_block_hours_i_minus_j'),n(r,'gap_rub_year'),'hour threshold')
    result=dict(status='PASS',method='independent stdlib Decimal reconstruction from delivered tables',
        networks=len(groups),legs=len(legrows),stress_rows=len(stressrows),comparison_rows=len(comparison),
        pairwise_cross_product_thresholds=len(thresholds),scope='arithmetic, grain, capacity, aggregate resource and OD membership; not market or calendar validity')
    (P/'independent_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    run()
