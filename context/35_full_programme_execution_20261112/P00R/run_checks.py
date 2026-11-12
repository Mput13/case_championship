#!/usr/bin/env python3
"""Independent arithmetic for P00R fixtures, not a run or approval of P06."""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from datetime import datetime
from itertools import accumulate
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]

def read_json(name):
    return json.loads((OUT / name).read_text())

def read_csv(name):
    with (OUT / name).open(newline='') as f:
        return list(csv.DictReader(f))

def calculate(cid, x):
    if cid == 'CE01':
        return {'delta': x['project_future']-x['keep_future']}
    if cid == 'CE02':
        records = [tuple(x['old_key'])+(m,) for m in ['fixed_programme','feasible_adaptation']]
        return {'distinct_records':len(set(records))}
    if cid == 'CE03':
        events=sorted([(t,delta) for a,b in x['flights'] for t,delta in [(a,1),(b,-1)]])
        peak=max(accumulate(delta for _,delta in events))
        active=x['available']-x['reserve']
        hours=sum(b-a for a,b in x['flights'])
        return dict(total_block_hours=hours,active_required=peak,active_available=active,
                    feasible=peak<=active and hours<=active*x['block_limit'])
    if cid == 'CE04':
        minutes=(datetime.fromisoformat(x['depart'])-datetime.fromisoformat(x['arrive'])).total_seconds()/60
        return dict(connection_min=minutes,bookable=x['min_connection_min']<=minutes<=x['max_connection_min'])
    if cid == 'CE05':
        loc=x['committed_local_ab']
        through=min(x['through_requests'],x['seats_ab']-loc,x['seats_bc'])
        assert through>=0
        loads=[loc+through,through]
        return dict(through_carried=through,ab_load=loads[0],bc_load=loads[1],journeys=loc+through,
                    segments=sum(loads),revenue=loc*x['local_fare']+through*x['through_fare'])
    if cid == 'CE06':
        return dict(revenue=x['journeys']*x['fare'],segments=x['journeys']*x['legs'])
    if cid == 'CE07':
        solo=x['market']*x['standalone_rw_weight']/(x['standalone_rw_weight']+x['competitor_weight'])
        joint=x['market']*sum(x['joint_rw_weights'])/(sum(x['joint_rw_weights'])+x['competitor_weight'])
        return dict(standalone_each=solo,joint_rw=joint,joint_other=x['market']-joint,sum_standalone=solo*len(x['joint_rw_weights']))
    if cid == 'CE08':
        return {'rw_'+k: x['market']*x['rw_weight']/(x['rw_weight']+x['competitor_'+k]+x['outside_weight']) for k in ['before','after']}
    if cid == 'CE09':
        return dict(net_new_journeys=x['same_rw_journeys']-x['same_rw_journeys'],
                    delta_segments=x['same_rw_journeys']*(x['new_legs']-x['old_legs']))
    if cid == 'CE10':
        return dict(total_allocated=x['airport_a']+x['airport_b'])
    if cid == 'CE11':
        keep=x['keep_revenue']-x['keep_cost']
        remaining=x['project_old_revenue']-x['project_old_cost']
        project=remaining+x['project_new_revenue']-x['project_new_cost']
        return dict(keep_result=keep,project_result=project,delta_result=project-keep,lost_donor_contribution=keep-remaining)
    if cid == 'CE12':
        before_fixed=x['revenue_a']+x['revenue_b']-x['flight_cost_a']-x['flight_cost_b']
        return dict(sum_standalone_result=before_fixed-2*x['shared_base_cost'],joint_result=before_fixed-x['shared_base_cost'])
    if cid == 'CE13':
        op=x['revenue']+x['support']-x['variable_cost']-x['fixed_cost']-x['startup_expense']-x['depreciation']
        cf=[-x['capex']-x['deposit'],x['ticket_cash_m1']-x['variable_cost']-x['fixed_cost']-x['startup_expense'],x['ticket_cash_m2'],x['support_cash_m3']+x['deposit_refund_m3']]
        assert x['tax_cash']==x['interest_cash']==[0,0,0,0], 'This isolated fixture explicitly excludes tax/interest, not the real programme.'
        cumulative=list(accumulate(cf))
        closing_ticket_ar=x['revenue']-x['ticket_cash_m1']-x['ticket_cash_m2']
        closing_support_ar=x['support']-x['support_cash_m3']
        closing_deposit=x['deposit']-x['deposit_refund_m3']
        bridge=op+x['depreciation']-x['capex']-closing_ticket_ar-closing_support_ar-closing_deposit
        assert bridge==sum(cf)
        funding=max(0,max(x['minimum_cash']-x['opening_cash']-c for c in cumulative))
        # A financing draw addresses liquidity but does not change earned result.
        funded=[c+funding for c in cumulative]
        assert min(funded)>=x['minimum_cash']
        return dict(operating_result=op,cash_before_financing=cf,cumulative_cash=cumulative,
                    peak_funding_month_end=funding,terminal_shortfall=max(0,-cumulative[-1]),cash_from_profit_bridge=bridge)
    if cid == 'CE14':
        return dict(net_expense=x['gross_fuel']-x['fuel_support'],cash_m1=-x['gross_fuel'],cash_m3=x['fuel_support'])
    if cid == 'CE15':
        return dict(full_delta=None if x['missing_cost'] is None else x['known_delta_before_missing_cost']-x['missing_cost'],
                    break_even_missing_cost=x['known_delta_before_missing_cost'])
    if cid == 'CE16':
        return dict(delta_share_pp=(x['project_rw']/x['project_market']-x['keep_rw']/x['keep_market'])*100)
    if cid == 'CE17':
        return dict(annual_pax=x['summer_weeks']*x['summer_pax_week']+x['other_weeks']*x['other_pax_week'])
    if cid == 'CE18':
        event_cf=[x['prelaunch_cash'],x['month1_payments_first'],x['month1_receipts_last']]
        return dict(month_end_funding=max(0,-sum(event_cf)),event_order_funding=max(0,-min(accumulate(event_cf))))
    if cid == 'CE19':
        return dict(larger_feasible_set_keeps_candidate=True,
                    new_result_after_extra_commitment=x['candidate_contribution']-x['new_committed_idle_lease'])
    if cid == 'CE20':
        return dict(revenue=x['yield_rub_per_pax_km']*x['journeys']*x['distance_km'])
    raise ValueError(cid)

def equal(actual, expected):
    if isinstance(expected,dict):
        return actual.keys()==expected.keys() and all(equal(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):
        return len(actual)==len(expected) and all(equal(a,b) for a,b in zip(actual,expected))
    if expected is None or isinstance(expected,bool):
        return actual is expected
    if isinstance(expected,(int,float)):
        return math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-9)
    return actual==expected

def rejected_wrong_values(cid, actual, bad):
    # Map intentionally wrong labels to the matching metric; comparing differently
    # shaped dictionaries would be a vacuous counterexample check.
    alias={
        'CE01': {'historical_delta':'delta'},
        'CE02': {'old_key_distinct_records':'distinct_records'},
        'CE03': {'hours_only_feasible':'feasible'},
        'CE04': {'same_clock_connection_min':'connection_min'},
        'CE08': {'rw_after_frozen':'rw_after'},
        'CE10': {'separate_full_markets':'total_allocated'},
        'CE11': {'double_deduction_delta':'delta_result','deduct_old_revenue_only_delta':'delta_result'},
        'CE13': {'funding_from_terminal_only':'peak_funding_month_end','profit_as_cash':'cash_from_profit_bridge'},
        'CE14': {'net_expense_after_double_support':'net_expense'},
        'CE15': {'full_delta_assuming_zero':'full_delta'},
        'CE16': {'delta_share_pp_fixed_denominator':'delta_share_pp'},
        'CE17': {'annual_pax_peak_times_52':'annual_pax'},
        'CE18': {'sufficient_liquidity_claim':'event_order_funding'},
        'CE19': {'must_be_at_least':'new_result_after_extra_commitment'},
        'CE20': {'revenue_without_distance':'revenue'},
    }
    for key,value in bad.items():
        target=alias.get(cid,{}).get(key,key)
        assert target in actual,(cid,target)
        assert actual[target]!=value,(cid,key,actual[target],value)
    return len(bad)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cases',nargs='*',help='Repeat only affected case IDs when a concrete input changes.')
    ap.add_argument('--verify-handoff',action='store_true')
    args=ap.parse_args()
    cases=read_json('counterexample_inputs.json')
    registry=read_json('assumptions_register.json')
    review=read_json('method_review.json')
    sources=read_csv('sources.csv')
    patches=read_csv('schema_patch.csv')
    csv_cases=read_csv('minimal_counterexamples.csv')
    assert len({c['case_id'] for c in cases})==len(cases)
    assert len({s['source_id'] for s in sources})==len(sources)
    assert len({r['assumption_id'] for r in registry})==len(registry)
    assert set(review['used_assumption_ids'])=={r['assumption_id'] for r in registry}
    for c,row in zip(cases,csv_cases,strict=True):
        assert row['case_id']==c['case_id']
        assert json.loads(row['inputs'])==c['inputs']
        assert json.loads(row['expected'])==c['expected']
        assert c['assumption_id'] in review['used_assumption_ids']
        assert set(c['source_ids'])<={s['source_id'] for s in sources}
    for f in review['findings']:
        assert set(f['minimum_fix'])<={p['patch_id'] for p in patches}
        assert set(f['counterexample_ids'])<={c['case_id'] for c in cases}
    for r in registry:
        assert all(k in r and r[k]!='' for k in ['value','unit','selected_by','basis','approval_status','lower','upper','affected_conclusions','sensitivity','refinement_method'])
    for q in read_csv('clarification_requests.csv'):
        assert q['status']=='USER_CONFIRMED' and q['resolution_source']
    selected=[c for c in cases if not args.cases or c['case_id'] in args.cases]
    if args.cases:
        assert set(args.cases)=={c['case_id'] for c in selected}
    results=[]
    for c in selected:
        actual=calculate(c['case_id'],c['inputs'])
        assert equal(actual,c['expected']),(c['case_id'],actual,c['expected'])
        rejected=rejected_wrong_values(c['case_id'],actual,c['incorrect_result'])
        results.append(dict(case_id=c['case_id'],status='PASS',actual=actual,rejected_wrong_values=rejected))
    verified=[]
    for inp in read_json('input_manifest.json')['inputs']:
        b=subprocess.check_output(['git','show',inp['commit']+':'+inp['path']],cwd=ROOT)
        assert hashlib.sha256(b).hexdigest()==inp['sha256']
        assert len(b)==inp['bytes']
        verified.append(inp['path'])
    prefix=str(OUT.relative_to(ROOT))+'/'
    changes=subprocess.check_output(['git','diff','--name-only',review['reviewed_plan_commit']],cwd=ROOT,text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    assert all(p.startswith(prefix) for p in changes+untracked),(changes,untracked)
    if args.verify_handoff:
        manifest=read_json('artifact_manifest.json')
        handoff=read_json('handoff.json')
        assert manifest['review_payload_commit']==handoff['review_payload_commit']
        for item in manifest['files']:
            b=(OUT/item['file']).read_bytes()
            assert hashlib.sha256(b).hexdigest()==item['sha256']
            if item['commit_scope']=='review_payload_commit':
                pinned=subprocess.check_output(['git','show',handoff['review_payload_commit']+':'+prefix+item['file']],cwd=ROOT)
                assert pinned==b,item['file']
        print(json.dumps({'handoff':'PASS','payload_commit':handoff['review_payload_commit'],'manifest_files':len(manifest['files'])}))
    result=dict(status='PASS',scope='P00R independent synthetic arithmetic and artifact integrity; not P06 acceptance',
                cases_checked=len(results),results=results,pinned_inputs_verified=len(verified),
                referential_integrity='PASS',unknown_not_zero='PASS (CE15)' if any(c['case_id']=='CE15' for c in selected) else 'NOT_RUN_IN_SUBSET; see sealed full checks.json',write_boundary='PASS',
                not_run=review['not_run'],command='python3 '+prefix+'run_checks.py'+(' --cases '+' '.join(args.cases) if args.cases else ''))
    # Verification of sealed artifacts must not mutate the evidence it just checked.
    if not args.verify_handoff:
        (OUT/('checks_subset.json' if args.cases else 'checks.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['results','not_run']},ensure_ascii=False))

if __name__=='__main__':
    main()
