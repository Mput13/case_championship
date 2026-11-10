#!/usr/bin/env python3
"""MR01/MR06 extension; reads frozen replay, never reruns author or optimisation.

Adds the minimum D/seat-bound variant and audits all saved stage17 flight-time
metadata by calling the actual block functions only. Financial baselines stay
unchanged. Methods itself remains AGENT_PROPOSAL / independent review PENDING.
"""
import csv
import importlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import corrected_model as fix
from prepare import put,show,digest,CIRI
from replay import table,js,ledger

ROOT=Path(__file__).resolve().parent
METHODS='344f4425ba3fbb73b45a5cbcd223089e2ca7b5d4'


def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))


def main():
    spec=[]
    for n in ('comparison_spec.md','decisions.json','requests.json'):
        path='context/23_night_run_20261110/methods/'+n
        data=show(METHODS,path);put(ROOT/'methods_spec'/n,data)
        spec.append(dict(source_commit=METHODS,path=path,sha256=digest(data)))
    js(ROOT/'methods_spec/source_manifest.json',dict(inputs=spec,independent_review='PENDING',status='AGENT_PROPOSAL'))
    sys.path.insert(0,str(ROOT/'author/src'))
    nm=importlib.import_module('network_model');D=nm.Demand()
    definitions=read(ROOT/'selected_triangles.csv')
    baseline=read(ROOT/'evaluation_summary.csv')
    bounds=[];bound_summary=[];route_counts=[]
    for scen,A in nm.load_assumptions().items():
        all_templates={'-'.join((t['B'],t['X'],t['Y'])):t for t in fix.templates(nm,D,A,scen,list(D.n.index))}
        rows=[r for r in definitions if r['run_id']=='AUTHOR_REPLAY' and r['scenario_id']==scen]
        selected=[all_templates[r['triangle']] for r in rows]
        assert all(t['freq']==int(float(r['frequency'])) for t,r in zip(selected,rows))
        result,pools=fix.evaluate(nm,selected,A,'standalone_claim','market_bound_only')
        b=next(r for r in baseline if r['run_id']=='AUTHOR_REPLAY' and r['scenario_id']==scen and r['candidate_id']=='DIRECT')
        h,c,r,s=fix.totals(result);W=A['weeks_per_year']
        # This saved selection does not exceed D. The minimum safeguard has no
        # economic effect here; pooled-curve deltas are a separate scenario.
        for actual,key in ((s*W,'annual_trips'),(r*W,'annual_gross_revenue_rub'),(c*W,'annual_variable_cost_rub')):
            assert math.isclose(actual,float(b[key]),rel_tol=1e-12,abs_tol=1e-5)
        summary=ledger(nm,D,A,'CORRECTED_MARKET_BOUND_ONLY',scen,'DIRECT',direct=result,capture_law='market_bound_only')
        summary.update(capture_law='market_bound_only',capture_status='AGENT_PROPOSAL_MINIMUM_GUARD',
                       pooled_curve_not_implied_by_market_bound=True)
        bound_summary.append(summary)
        for mode in ('AUTHOR_REPLAY','CORRECTED_FIXED_SELECTION','CORRECTED_RESELECTED','CORRECTED_CLAIM_ALLOCATION'):
            path=ROOT/'ledgers'/mode/scen/'DIRECT/market_pool.csv'
            for p in read(path):
                market=float(p['scenario_weekly_one_direction_market']);sold=float(p['actual_sold'])
                bounds.append(dict(run_id=mode,scenario_id=scen,pair=p['pair'],annual_scenario_market=market*2*W,
                    annual_actual_sold=sold*2*W,annual_pooled_curve_capture=float(p['captured_pool'])*2*W,
                    excess_over_entire_D=max(0.,sold-market)*2*W,
                    excess_over_scenario_pooled_curve=max(0.,sold-float(p['captured_pool']))*2*W,
                    law_status='AGENT_PROPOSAL_AUTHOR_CURVE_AT_TOTAL_FREQUENCY',
                    market_status='SCENARIO_OD_USE_OF_SEGMENT_SCALE_NOT_OBSERVED_ENDPOINT_OD'))
        for mode in ('AUTHOR_REPLAY','CORRECTED_FIXED_SELECTION','CORRECTED_RESELECTED'):
            ps=read(ROOT/'ledgers'/mode/scen/'DIRECT/physical_leg.csv')
            programs=[r for r in definitions if r['run_id']==mode and r['scenario_id']==scen]
            route_counts.append(dict(model='Анастасия',run_id=mode,scenario=scen,
                                     service_program_count=len(programs),program_definition='reversible triangle',
                                     unique_unordered_physical_pairs=len(ps),case_route_compliance='OPEN_DEFINITION'))
    assert all(r['excess_over_entire_D']<1e-6 for r in bounds)
    table(ROOT/'common_market_bounds.csv',bounds)
    table(ROOT/'market_bound_only_summary.csv',bound_summary)
    table(ROOT/'route_definitions.csv',route_counts)
    # Audit frozen flights; no new principal replay and no flight-time changes.
    src='context/17_aircraft_route_review/model/flights.csv'
    data=show(CIRI,src);put(ROOT/'ciri/frozen_exports/stage17_flights.csv',data)
    sys.path.insert(0,str(ROOT/'ciri/scripts'))
    review=importlib.import_module('build_aircraft_route_review')
    # setup supplies the pinned additional city coordinates used by stage17;
    # no evaluate(), search() or financial program main() is invoked here.
    model,_=review.legacy.setup();model.__class__=review.RouteModel
    model.route_blocks={(r['origin'],r['destination']):r for r in review.readcsv(review.OUT/'evidence/directional_blocks.csv')}
    rows=[]
    for f in read(ROOT/'ciri/frozen_exports/stage17_flights.csv'):
        profile=f['profile'];model.profile=profile;a=f['origin'];b=f['destination']
        actual=model.block(a,b)
        assert actual==float(f['block_minutes']),(profile,a,b,actual,f['block_minutes'])
        if profile=='RELAXED_SAME_INPUTS_100':
            method=f['block_method'];source=f['source'];method_status='INHERITED_CORE_MODEL_APPLIES'
        elif (a,b) in model.route_blocks:
            method='ceil(max_published_minutes * block_time_factor)'
            source='context/17_aircraft_route_review/evidence/directional_blocks.csv'
            method_status='CORRECTED_METADATA_PUBLISHED_DIRECTIONAL_PROXY'
        else:
            method='ceil((round_up_5min(30 + great_circle_km/750*60) + stress_if_profile) * block_time_factor)'
            source='coordinates.json + RouteModel.block; +60 only UNKNOWN_TIME_PLUS60_100'
            method_status='CORRECTED_METADATA_ROUTE_MODEL_FALLBACK'
        rows.append(dict(profile=profile,network=f['network'],flight_id=f['id'],origin=a,destination=b,
                         original_block_minutes=float(f['block_minutes']),actual_RouteModel_block=actual,
                         corrected_block_minutes=actual,number_changed=False,
                         original_block_method=f['block_method'],original_source=f['source'],
                         corrected_block_method=method,corrected_source=source,metadata_status=method_status,
                         source_commit=CIRI,scope='METADATA_ONLY_NO_NEW_FINANCIAL_REPLAY'))
    table(ROOT/'ciri/block_metadata_audit.csv',rows)
    js(ROOT/'ciri/block_audit_source_manifest.json',dict(source_commit=CIRI,source_path=src,
        sha256=digest(data),rows=len(rows),grain='frozen stage17 profile x network x dated physical flight'))
    counts=Counter((r['profile'],r['metadata_status']) for r in rows)
    table(ROOT/'ciri/block_metadata_summary.csv',[dict(profile=p,status=s,legs=n) for (p,s),n in sorted(counts.items())])
    js(ROOT/'methods_requests_response.json',dict(methods_commit=METHODS,methods_independent_review='PENDING',
        MR01=dict(status='IMPLEMENTED_WITH_EXPLICIT_POLICY_VARIANTS',
                  artifacts=['author_export_comparison.csv','before_after.csv','common_market_bounds.csv',
                             'market_bound_only_summary.csv','route_definitions.csv','selected_triangles.csv','ledgers/'],
                  mandatory='One shared scenario D budget and each physical capacity cap',
                  policy='Q(F) at total frequency is a proposed scenario, not uniquely objective correction',
                  original_saved_outputs_exceed_entire_D=False,
                  no_new_author_replay=True),
        MR06=dict(status='CONFIRMED_STALE_METADATA',saved_legs_checked=len(rows),
                  values_match_actual_function=True,flight_time_changes=0,
                  artifacts=['ciri/block_metadata_audit.csv','ciri/block_metadata_summary.csv'],
                  no_new_financial_replay=True)))
    print(json.dumps(dict(status='PASS',MR01='complete',MR06_legs=len(rows),flight_time_changes=0)))


if __name__=='__main__':main()
