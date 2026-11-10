#!/usr/bin/env python3
"""Exact independent principal-comparison replay of Ciri/mput at 93fa5cf.

Copies only code and inputs via git show; no network or recalibration. This is
implementation-agent reproduction, not the coordinator's independent review.
"""
import contextlib
import importlib
import json
import math
import socket
import sys
from pathlib import Path

from prepare import CIRI, put, show, digest
from replay import js, table

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'ciri'


def main():
    files=['scripts/'+n+'.py' for n in ['build_team_proposals','build_aircraft_route_review',
                                      'build_conditional_decision','build_team_comparison']]
    files+=['tools/dist.py','data/processed/longlist.csv','context/15_team_update/model/overrides.json']
    files+=['context/12_network_economics/'+n for n in ['inputs.json','sources.json','schedule_rules.json',
             'competition.csv','block_times.csv','published_flight_dates.csv']]
    files+=['context/11_practical_screening/'+n for n in ['inputs.json','coordinates.json']]
    files+=['context/16_conditional_decision/assumptions.json',
            'context/16_conditional_decision/research/goj_svx_own_calendar.csv']
    files+=['context/17_aircraft_route_review/'+n for n in ['assumptions.json',
             'evidence/directional_blocks.csv','evidence/published_service_facts.csv',
             'model/selected_networks.json','model/comparison.csv']]
    manifest=[]
    for path in files:
        data=show(CIRI,path);put(DEST/path,data)
        manifest.append(dict(source_commit=CIRI,author_ref='Цири/mput',source_path=path,
                             local_path=str((DEST/path).relative_to(ROOT)),sha256=digest(data),bytes=len(data)))
    for name in ('comparison.csv','routes.csv'):
        put(DEST/'frozen_exports'/name,show(CIRI,'context/21_team_proposals/'+name))
    def denied(*a,**k):
        raise RuntimeError('OFFLINE_REPLAY_NETWORK_FORBIDDEN')
    socket.create_connection=denied; socket.socket.connect=denied
    sys.path.insert(0,str(DEST/'scripts'))
    program=importlib.import_module('build_team_proposals')
    original=program.review.RouteModel.evaluate
    results=[];sales=[];capacity=[]

    def captured(self,net,sc,*args,**kwargs):
        r,ss,cc=original(self,net,sc,*args,**kwargs)
        if kwargs.get('detail'):
            results.append(r.copy());sales.extend(ss);capacity.extend(cc)
        return r,ss,cc

    program.review.RouteModel.evaluate=captured
    with (DEST/'run.log').open('w') as stream,contextlib.redirect_stdout(stream):
        program.main()
    program.review.RouteModel.evaluate=original
    import csv
    matches=[]
    for name in ('comparison.csv','routes.csv'):
        with (DEST/'frozen_exports'/name).open(newline='') as f: expected=list(csv.DictReader(f))
        with (DEST/'context/21_team_proposals'/name).open(newline='') as f: actual=list(csv.DictReader(f))
        assert len(expected)==len(actual)
        mismatches=[];max_delta=0.
        for i,(a,b) in enumerate(zip(expected,actual)):
            assert a.keys()==b.keys()
            for k,x in a.items():
                y=b[k]
                try:
                    xf,yf=float(x),float(y)
                except ValueError:
                    if x!=y:mismatches.append((i,k,x,y))
                else:
                    max_delta=max(max_delta,abs(xf-yf))
                    if not math.isclose(xf,yf,rel_tol=1e-12,abs_tol=1e-6):mismatches.append((i,k,x,y))
        assert not mismatches,mismatches[:5]
        matches.append(dict(file=name,rows=len(actual),mismatches=0,max_numeric_abs_delta=max_delta))
    checks=[]
    for r in results:
        ss=[s for s in sales if s['network']==r['network'] and s['scenario']==r['scenario']]
        cc=[c for c in capacity if c['network']==r['network'] and c['scenario']==r['scenario']]
        def equal(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-6),(a,b)
        equal(sum(c['occupied'] for c in cc),sum(s['segment_pax'] for s in ss))
        equal(sum(s['gross_revenue'] for s in ss),r['gross_revenue'])
        equal(sum(s['sold_journeys']*s['fare_once'] for s in ss),r['gross_revenue'])
        equal(r['incremental_revenue'],r['gross_revenue']-r['foregone_RW_revenue'])
        equal(r['incremental_operating_cost'],r['flight_variable_cost']+r['new_pax_variable']-r['saved_old_pax_variable'])
        equal(r['contribution_before_base_fleet_opportunity'],r['incremental_revenue']-r['incremental_operating_cost'])
        legs={c['flight_id']:c for c in cc}
        for key,c in legs.items():
            occupied=sum(s['sold_journeys'] for s in ss if key in s['flight_ids'].split(';'))
            equal(occupied,c['occupied'])
            assert 0<=occupied<=c['capacity_scenario']+1e-6
        # The known incumbent direct seat budget is shared across dated offers.
        pools={}
        for s in ss:
            k=(s['origin'],s['destination'])
            pools.setdefault(k,dict(migrated=0.,cap=s['known_direct_RW_capacity']))
            pools[k]['migrated']+=s['migrated_RW_direct']
        assert all(p['cap'] is None or p['migrated']<=p['cap']+1e-6 for p in pools.values())
        checks.append(dict(network=r['network'],scenario=r['scenario'],status='PASS',
                           trips=r['sold_journeys'],segments=r['segment_pax'],
                           one_fare=r['gross_revenue'],dated_legs=len(cc),
                           cannibalization_scope='known direct shared cap; unknown old connecting remains scenario'))
    table(DEST/'itinerary_sales.csv',sales);table(DEST/'flight_capacity.csv',capacity)
    js(DEST/'replay_validation.json',dict(status='PASS',export_comparison=matches,checks=checks,
        source_commit=CIRI,author_ref='Цири/mput',network_blocked=True,independent_review='PENDING',
        source_supported_endpoint_demand=False,calendar_scope='2026-12-07/2026-12-13 scenario schedule; not operation'))
    js(DEST/'source_manifest.json',manifest)
    print(json.dumps(dict(status='PASS',exports=matches,comparisons=len(results),sales=len(sales),legs=len(capacity))))


if __name__=='__main__':main()
