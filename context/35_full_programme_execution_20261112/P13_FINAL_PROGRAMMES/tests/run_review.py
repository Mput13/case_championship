"""Bounded independent P09 review. Offline; exact Git reads; writes only P13.

Run: PYTHONDONTWRITEBYTECODE=1 python3 context/35_full_programme_execution_20261112/P13_FINAL_PROGRAMMES/tests/run_review.py
No author validator, capture, matrix campaign, Git mutation or network is run.
"""
import collections
import copy
import csv
import gc
import gzip
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1]
ROOT = '736859fdd08448c2564b7b9269b751abe00b5cbc'
PREFIX = 'context/35_full_programme_execution_20261112/P09/'
MANIFEST = '7b20a1a247ee4b3cf96d94648bb36d61482cb0a58eb7a296ada49a78c818d1fa'
READS = {}
RESULTS = []
ASSERTIONS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def gitbytes(path, commit=ROOT, prefix=PREFIX):
    raw = subprocess.check_output(['git', 'show', commit + ':' + prefix + path], cwd=REPO)
    key = commit + ':' + prefix + path
    READS[key] = dict(commit=commit, path=prefix + path, bytes=len(raw), sha256=sha(raw),
                      git_blob_sha1=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())
    if commit == ROOT and prefix == PREFIX and path in FILES:
        expected = FILES[path]
        assert sha(raw) == expected['sha256'] and len(raw) == expected['bytes'], path
    return raw


def j(path):
    return json.loads(gitbytes(path))


def rows(path):
    return list(csv.DictReader(io.StringIO(gitbytes(path).decode())))


def check(name, condition, evidence=None):
    ASSERTIONS.append(dict(check=name, passed=bool(condition), evidence=evidence))
    if not condition:
        raise AssertionError((name, evidence))


def close(name, actual, expected, tolerance=.01):
    check(name, abs(actual - expected) <= tolerance,
          dict(actual=actual, expected=expected, difference=actual-expected, tolerance=tolerance))


def rejects(name, fn, expected):
    try:
        fn()
    except Exception as exc:
        check(name, expected in str(exc), dict(type=type(exc).__name__, actual=str(exc), expected_fragment=expected))
    else:
        check(name, False, dict(expected_fragment=expected, actual='NO_EXCEPTION'))


def identity_leaves(small, full, path='$'):
    # Reviewer implementation, does not invoke the author's projection verifier.
    if isinstance(small, dict):
        assert isinstance(full, dict), path
        counts = [identity_leaves(v, full[k], path+'.'+k) for k,v in small.items()]
    elif isinstance(small, list):
        assert isinstance(full, list) and len(small) == len(full), path
        counts = [identity_leaves(a, z, f'{path}[{i}]') for i,(a,z) in enumerate(zip(small,full))]
    else:
        assert type(small) is type(full) and small == full, (path, small, full)
        return (1, int(small is None))
    return tuple(sum(x[i] for x in counts) for i in range(2))


FILES = {}
manifest_raw = gitbytes('manifest.json')
assert sha(manifest_raw) == MANIFEST
manifest = json.loads(manifest_raw)
FILES = {r['path']:r for r in manifest['files']}
assert manifest['file_count'] == len(FILES) == 2617
assert manifest['bytes'] == sum(r['bytes'] for r in FILES.values()) == 754088586

runtime = Path(tempfile.mkdtemp(prefix='runtime-', dir=OUT/'tests'))
try:
    # Minimal execution inputs, about 1MB; no evaluation input archive or od_monthly.
    selected = {'programme_builder.py','evaluate_programmes.py','canonical_finalists.py',
                'existing_ssj_transfer.py','input_pins.json','programmes.json','existing_ssj/programmes.json',
                'subject/P04/cost_ranges.csv','subject/P05/model.py','subject/P05/assumptions_register.json',
                'subject/P05/aviation_monthly_history.csv',
                'subject/P05/inputs/BASE/data/processed/catchments.csv',
                'subject/P05/inputs/BASE/data/processed/od_pairs.csv',
                'subject/P05/inputs/BASE/data/processed/demand_pairs.csv',
                'subject/P05/inputs/BASE/data/processed/od_fit.json'}
    selected.update(p for p in FILES if p.startswith('subject/P06/engine/') and p.endswith('.py'))
    selected.update(p for p in FILES if p.startswith('sealed/variants/') and '/research_v1/local_cost' in p and p.endswith('.csv'))
    for path in sorted(selected):
        target = runtime/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gitbytes(path))
    for path in ['README.md','handoff.md','handoff.json','choice_report.md','economics_report.md',
                 'data_contract.json','projection_contract.json','canonical_equivalence_checks.json',
                 'validation.json','assemble.py','derive_driver_thresholds.py','replay.py']:
        gitbytes(path)
    sys.path.insert(0, str(runtime))
    b = importlib.import_module('programme_builder')
    e = importlib.import_module('evaluate_programmes')
    c = importlib.import_module('canonical_finalists')
    from engine.common import pool_key
    programmes = {p['programme_id']:p for p in j('programmes.json')['programmes']}
    # Check exact engine provenance against the original fixed commit as well.
    pins = j('input_pins.json')
    engine_pin = manifest['P06_pin']
    for pin in pins:
        if pin['local_path'] in selected:
            raw = (runtime/pin['local_path']).read_bytes()
            check('selected_source_pin:' + pin['local_path'], sha(raw) == pin['sha256'])
        if pin['source_id'] == 'P06' and pin['local_path'].endswith('.py') and '/engine/' in pin['local_path']:
            original = gitbytes(pin['path'], pin['commit'], '')
            check('fixed_engine_origin:' + pin['local_path'], pin['commit'] == engine_pin and sha(original) == pin['sha256'])

    def group1():
        name = 'VOG_RADIAL__phased__base__passive'
        p = programmes['VOG_RADIAL']
        expected = j('evaluations/'+name+'.json')
        start = time.monotonic()
        replay = e.evaluate(p, 'phased', 'base', 'passive')
        replaypath = runtime/'own_overview.json'
        e.export_result(replay,replaypath)
        check('real_24_month_overview_replay_bytes', replaypath.read_bytes() == gitbytes('evaluations/'+name+'.json'),
              dict(actual_sha256=sha(replaypath.read_bytes()), seconds=time.monotonic()-start,
                   flights=replay['calendar_flights'], dates=replay['dates_generated']))
        a,k = b.build_pair(p,'phased','base')
        full = b.core.compare(a,k)
        receipt = j('ui_results/'+name+'.receipt.json')
        serialized = json.dumps(full,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        check('real_24_month_canonical_replay_hash', sha(serialized) == receipt['full']['sha256'],
              dict(actual=sha(serialized), expected=receipt['full']['sha256'], bytes=len(serialized)))
        check('replayed_project_and_keep_bundle_hashes',
              b.digest(a)==receipt['project_bundle_sha256'] and b.digest(k)==receipt['keep_bundle_sha256'])
        savedgz = gitbytes(receipt['full']['path'])
        check('saved_full_compressed_and_uncompressed_hashes',
              sha(savedgz)==receipt['full']['gzip_sha256'] and sha(gzip.decompress(savedgz))==sha(serialized))
        del serialized,savedgz,a,k
        check('canonical_physical_calendar_conditional', not full['project']['operations']['errors'] and
              full['project']['operations']['dispatch_ready'] is False,
              dict(status=full['project']['operations']['status'], unknowns=len(full['project']['operations']['unknowns'])))
        check('maincase_8_to_12_pairs',full['project']['network_target']['status']=='WITHIN_8_12',full['project']['network_target'])
        # Saved UI and saved canonical, for BOTH scenarios; exact JSON types and nulls.
        contract = j('projection_contract.json')
        packraw = gitbytes('ui/VOG_RADIAL.json')
        pack = json.loads(packraw)
        idx = next(x for x in j('ui/index.json')['packages'] if x['programme_id']=='VOG_RADIAL')
        check('ui_package_hash', sha(packraw)==idx['sha256'])
        leaf_proofs=[]
        for ev in pack['evaluations']:
            proof = j(ev['audit_receipt'])
            raw = gzip.decompress(gitbytes(ev['source_full_result_path']))
            source = json.loads(raw)
            small = ev['result']
            leaves, nulls = identity_leaves(small,source)
            check('projection_top_contract_'+proof['evaluation_id'], set(small)==set(contract['paths']['$'])|{'project','keep','network_changes'})
            check('projection_project_contract_'+proof['evaluation_id'], set(small['project'])==set(contract['paths']['$.project'])|{'results_monthly','operations'})
            check('projection_month_contract_'+proof['evaluation_id'], all(set(r)==set(contract['paths']['$.project.results_monthly[*]']) for r in small['project']['results_monthly']))
            check('projection_hash_'+proof['evaluation_id'], b.digest(small)==ev['projection_sha256']==proof['projection_sha256'] and sha(raw)==ev['source_full_result_sha256']==proof['full']['sha256'])
            check('projection_preserves_real_nulls_'+proof['evaluation_id'],nulls>100,dict(leaves=leaves,null_leaves=nulls))
            broken=copy.deepcopy(small);broken['project']['summary']['operating_result']=0
            rejects('projection_null_to_zero_detected_'+proof['evaluation_id'],lambda:identity_leaves(broken,source),'operating_result')
            broken=copy.deepcopy(small);broken['delta_monthly'].pop()
            rejects('projection_array_filter_detected_'+proof['evaluation_id'],lambda:identity_leaves(broken,source),'delta_monthly')
            leaf_proofs.append(dict(evaluation_id=proof['evaluation_id'],leaves=leaves,null_leaves=nulls))
            del source,raw,broken
        check('overview_separate_result_mode', j('data_contract.json')['overview']['result_mode']!=contract['result_mode'])
        close('overview_vs_canonical_journeys',full['delta_summary']['journeys'],replay['delta_journeys'],1e-6)
        close('overview_vs_canonical_revenue',full['delta_summary']['revenue_net'],replay['delta_revenue_net'])
        close('overview_vs_canonical_H',full['thresholds']['net_missing_operating_cost_break_even'],replay['delta_known_operating_subtotal'])
        maxdiff=collections.defaultdict(float)
        for canon,overview in zip(full['project']['results_monthly'],replay['results_monthly']):
            for field in ['journeys','passenger_segments','revenue_net','known_operating_subtotal']:
                maxdiff[field]=max(maxdiff[field],abs(canon[field]-overview[field]))
        check('all_24_month_numeric_equivalence', all(v<(1e-6 if k in ['journeys','passenger_segments'] else .01) for k,v in maxdiff.items()),dict(maxdiff))
        for side in ['project','keep']:
            check('full_unknown_finance_'+side, all(full[side]['summary'][f] is None for f in ['variable_contribution','operating_result','cash_before_financing']))
            check('no_support_'+side,all(r['recognized_support']==0 for r in full[side]['results_monthly']))
            check('reported_share_unknown_'+side,all(r['share'] is None and r['compatible_carried_passengers'] is None for r in full[side]['results_annual']))
        check('full_company_and_incremental_funding_unknown',full['whole_company_funding'] is None and full['project_incremental_funding']['peak_dated_day_end'] is None)
        cash=full['project']['finance']['cash_events']
        post=[x for x in cash if x['payment_date']>'2028-12-31']
        check('post_horizon_payments_retained',len(post)>0,dict(count=len(post),first=post[0]['payment_date']))
        summary=dict(projection=leaf_proofs,delta_journeys=full['delta_summary']['journeys'],
                     delta_revenue_net=full['delta_summary']['revenue_net'],H=full['thresholds']['net_missing_operating_cost_break_even'],
                     monthly_max_difference=dict(maxdiff),post_horizon_cash_events=len(post))
        del replay,full,pack
        gc.collect()
        return summary

    def group2():
        a,k=b.build_pair(programmes['SVX_BANK9'],'phased','base',dates={'2028-12-04','2028-12-05'})
        check('same_common_OD_date_outside_policy', all(b.digest(a[f])==b.digest(k[f]) for f in ['markets','market_calendar','response_policy','fleet_calendar','keep_policy']))
        r=b.core.compare(a,k)
        check('two_date_calendar_has_no_physical_errors',not r['project']['operations']['errors'],r['project']['operations']['errors'])
        sat=copy.deepcopy(a)
        for m in sat['markets']:m['potential_journeys']*=1000
        alloc=b.allocate(sat,b.apply_response(sat))
        ps={p['product_id']:p for p in sat['products']}
        bypool=collections.defaultdict(float)
        for x in alloc['allocations']:bypool[pool_key(x)]+=x['final_choice']
        check('saturated_common_OD_conserved',all(abs(bypool[pool_key(m)]-m['potential_journeys'])<1e-6 for m in sat['markets']),dict(pools=len(bypool),iterations=alloc['iterations']))
        check('saturated_physical_seats_conserved',all(x['carried_segments']<=x['saleable_seats']+1e-6 for x in alloc['seats']))
        transfers=[x for x in alloc['allocations'] if x['owner']=='RW' and len(ps[x['product_id']]['legs'])>1 and x['carried']>0]
        check('real_transfer_products_use_shared_legs',len(transfers)>0,dict(products=len(transfers),journeys=sum(x['carried'] for x in transfers)))
        fin=b.finance(sat,alloc['allocations'],sat['products'])
        fare_once=sum(x['carried']*ps[x['product_id']]['net_fare'] for x in alloc['allocations'] if x['owner']=='RW')
        revenue=sum(x['revenue_net'] for x in fin['results_monthly'])
        duplicated=sum(x['carried']*ps[x['product_id']]['net_fare']*len(ps[x['product_id']]['legs']) for x in alloc['allocations'] if x['owner']=='RW')
        close('through_fare_once',revenue,fare_once,1e-6)
        check('through_fare_test_distinguishes_double_count',duplicated>fare_once+1,dict(correct=fare_once,incorrect_per_leg=duplicated))
        segments=sum(x['carried']*len(ps[x['product_id']]['legs']) for x in alloc['allocations'] if x['owner']=='RW')
        close('each_transfer_leg_consumes_one_seat',sum(x['carried_segments'] for x in alloc['seats']),segments,1e-6)
        # Demonstrate an actually sensitive joint inventory control: market silos oversell.
        silo=collections.defaultdict(float)
        for m in sat['markets']:
            one=copy.deepcopy(sat);one['markets']=[m]
            prods=[p for p in sat['products'] if pool_key(p)==pool_key(m)]
            out=b.allocate(one,prods)
            for seat in out['seats']:silo[seat['flight_instance_id']]+=seat['carried_segments']
        maxsilo=max(silo.values())
        check('independent_market_silos_would_oversell',maxsilo>100+1e-6,dict(max_silo_segments=maxsilo,max_joint_segments=max(s['carried_segments'] for s in alloc['seats'])))
        # Date components have separate physical ids AND a single pool for each OD/date.
        dates={m['customer_segment'].split(':',1)[1] for m in sat['markets']}
        independent_total=0
        for day in dates:
            one=copy.deepcopy(sat);one['markets']=[m for m in sat['markets'] if m['customer_segment']=='travel_date:'+day]
            one['flights']=[f for f in sat['flights'] if f['departure_utc'][:10]==day]
            prods=[p for p in sat['products'] if p['departure_date']==day]
            out=b.allocate(one,prods)
            independent_total+=sum(x['carried'] for x in out['allocations'] if x['owner']=='RW')
        close('joint_vs_disjoint_actual_dates',sum(x['carried'] for x in alloc['allocations'] if x['owner']=='RW'),independent_total,1e-6)
        mutated=copy.deepcopy(a);mutated['markets'].append(copy.deepcopy(mutated['markets'][0]))
        rejects('duplicate_OD_date_rejected',lambda:b.allocate(mutated,mutated['products']),'duplicate demand pool')
        mutated=copy.deepcopy(a);mutated['markets'][0]['potential_journeys']=None
        unknown=b.core.evaluate(mutated)
        check('unknown_demand_propagates_to_journeys',unknown['summary']['journeys'] is None and any('potential demand UNKNOWN' in x for x in unknown['unknown_dependencies']))
        mutated=copy.deepcopy(a);mutated['flights'][0]['saleable_seats']=None
        unknown=b.core.evaluate(mutated)
        check('unknown_seats_not_zero',unknown['summary']['journeys'] is None and any('saleable seats UNKNOWN' in x for x in unknown['unknown_dependencies']))
        mutated=copy.deepcopy(a);next(p for p in mutated['products'] if p['owner']=='RW')['net_fare']=None
        unknown=b.core.evaluate(mutated)
        check('unknown_fare_propagates_to_revenue_and_profit',unknown['summary']['revenue_net'] is None and unknown['summary']['operating_result'] is None and any('journey_revenue:' in x and x.endswith('.amount') for x in unknown['unknown_dependencies']))
        for field in ['markets','fleet_calendar']:
            mutated=copy.deepcopy(k)
            if field=='markets':mutated[field][0]['potential_journeys']+=1
            else:mutated[field][0]['service_entry_date']='2027-01-02T00:00:00Z'
            rejects('mismatched_common_'+field,lambda:b.core.compare(a,mutated),'common input mismatch: '+field)
        mutated=copy.deepcopy(k);mutated['context']['delivery_calendar_id']='P09-none'
        rejects('mismatched_delivery_calendar',lambda:b.core.compare(a,mutated),'mismatch: delivery_calendar_id')
        # The financial headroom equation is an additive equation, not full profit.
        H=r['thresholds']['net_missing_operating_cost_break_even']
        delta=1234.0
        modified=copy.deepcopy(a)
        modified['economic_events'].append(b.econ_event('REVIEW:START','startup',1,delta,'2026-12','REVIEW_EXPLICIT_COUNTEREXAMPLE','P09-MISSING'))
        new=b.core.compare(modified,k)
        close('threshold_includes_prelaunch_cost_once',new['thresholds']['net_missing_operating_cost_break_even'],H-delta,1e-6)
        check('known_addition_does_not_complete_unknown_full_profit',new['delta_summary']['operating_result_including_prelaunch'] is None)
        return dict(actual_dates=sorted(dates),saturated_pools=len(bypool),transfer_products=len(transfers),
                    fare_once=fare_once,incorrect_per_leg_revenue=duplicated,naive_silo_max_segments=maxsilo,
                    H_before=H,H_after_added_prelaunch=new['thresholds']['net_missing_operating_cost_break_even'])

    def group3():
        p=programmes['VOG_RADIAL'];resource=[]
        for delivery in ['phased','partial','delayed','none']:
            pc=b.build_calendar(p,delivery);kc=b.build_calendar(b.KEEP,delivery)
            check('same_fleet_'+delivery,pc['fleet_calendar']==kc['fleet_calendar'])
            ep={f['flight_instance_id']:f for f in pc['flights'] if f['flight_instance_id'].startswith('E1:')}
            ek={f['flight_instance_id']:f for f in kc['flights'] if f['flight_instance_id'].startswith('E1:')}
            check('scoped_future_existing_KEEP_'+delivery,ep==ek and len(ep)==1252)
            check('unused_reserve_'+delivery,not any(x['aircraft_id']=='N1' for x in pc['assignments']))
            po=b.check_operations(dict(context={'period_start':'2027-01','period_end':'2028-12'},resource_operators=['RW_SCENARIO'],**pc))
            check('full_calendar_ops_'+delivery,not po['errors'],po['errors'][:3])
            pe=b.economic_events(pc,'base',p);ke=b.economic_events(kc,'base',b.KEEP)
            shared=lambda es:{x['economic_event_id']:x for x in es if x['category']=='aircraft_use'}
            check('unknown_common_tail_charges_retained_'+delivery,shared(pe)==shared(ke) and all(x['amount'] is None for x in shared(pe).values()))
            if delivery in ['partial','none']:
                r=e.evaluate(p,delivery,'base','passive');path=runtime/('own_'+delivery+'.json');e.export_result(r,path)
                expected=gitbytes('evaluations/VOG_RADIAL__'+delivery+'__base__passive.json')
                check('real_resource_replay_'+delivery,path.read_bytes()==expected,dict(sha256=sha(path.read_bytes()),flights=r['calendar_flights'],pairs=r['unique_pairs_end2028']))
                if delivery=='none':
                    close('no_new_is_KEEP_delta_journeys',r['delta_journeys'],0,1e-6)
                    close('no_new_is_KEEP_delta_H',r['delta_known_operating_subtotal'],0,1e-6)
                    check('no_new_no_project_route',r['unique_pairs_end2028']==0)
                else:check('partial_is_labelled_shortfall_not_maincase',r['unique_pairs_end2028']==3)
            resource.append(dict(delivery=delivery,tails=len(pc['fleet_calendar']),flights=len(pc['flights']),shared_unknown_tail_months=len(shared(pe))))
        bad=next(x for x in rows('scenario_results.csv') if x['status']=='INFEASIBLE_CONSTRUCTED_CALENDAR')
        r=e.evaluate(programmes[bad['programme_id']],bad['delivery'],bad['scenario'],bad['response'])
        check('real_infeasible_calendar_has_no_economics',r['status']=='INFEASIBLE_CONSTRUCTED_CALENDAR' and 'delta_known_operating_subtotal' not in r,dict(programme=bad['programme_id'],error=r['operations'][0]['errors'][:2]))
        import existing_ssj_transfer as ssj
        ssj.install()
        try:
            sp=next(p for p in j('existing_ssj/programmes.json') if p['programme_id']=='SSJ_VOG_RADIAL')
            pc=b.build_calendar(sp,'none');kc=b.build_calendar(b.KEEP,'none')
            check('existing_E1_same_committed_fleet_no_new',pc['fleet_calendar']==kc['fleet_calendar'] and [t['aircraft_id'] for t in pc['fleet_calendar']]==['E1'])
            check('existing_E1_donor_is_replaced_not_kept_twice',not set(f['flight_instance_id'] for f in pc['flights']) & set(f['flight_instance_id'] for f in kc['flights']))
            sr=e.evaluate(sp,'none','base','passive');path=runtime/'own_ssj.json';e.export_result(sr,path)
            check('real_E1_donor_overview_replay',path.read_bytes()==gitbytes('existing_ssj/SSJ_VOG_RADIAL__none__base__passive.json'),dict(sha256=sha(path.read_bytes()),delta_journeys=sr['delta_journeys'],H=sr['delta_known_operating_subtotal']))
            for month in sr['results_monthly']:
                close('donor_joint_delta_'+month['month'],month['delta_known_operating_subtotal'],month['known_operating_subtotal']-month['KEEP_known_operating_subtotal'],1e-6)
            ca,ck=b.build_pair(sp,'none','base',dates={'2028-12-04'})
            # Slice preserves the actual E1 positioning as the slice's explicit initial state.
            for bundle in [ca,ck]:
                bundle['fleet_calendar'][0]['initial_location']=bundle['flights'][0]['origin_airport']
            # Fleet scope must still match: VOG and SVX differ in slice state, so use full receipts
            # for the donor no-second-deduction check; no unsupported compare of slice states.
            receipts=j('existing_ssj/canonical_receipts.json')
            check('donor_no_extra_deduction_in_saved_canonical',all(json.loads(gzip.decompress(gitbytes(x['full']['path'])))['donor_extra_deduction'] is False for x in receipts))
        finally:
            b.build_calendar=ssj.ORIGINAL
        # Independent hand arithmetic: financing cannot erase pre-financing cash need.
        cash=[dict(payment_date='2027-01-01',amount_signed=-100,category='operating'),
              dict(payment_date='2027-01-31',amount_signed=120,category='operating'),
              dict(payment_date='2027-02-01',amount_signed=-30,category='operating'),
              dict(payment_date='2027-01-01',amount_signed=999,category='financing')]
        f=b.funding(cash,'2027-01','2027-02',20,10)
        close('cash_day_end_equation',f['peak_dated_day_end'],90,1e-9)
        close('cash_month_end_does_not_hide_day_end_peak',f['peak_month_end'],0,1e-9)
        mutated=copy.deepcopy(cash);mutated[0]['amount_signed']=None
        check('unknown_cash_amount_not_zero',b.funding(mutated,'2027-01','2027-02',20,10)['peak_dated_day_end'] is None)
        check('unknown_opening_cash_not_zero',b.funding(cash,'2027-01','2027-02',None,10)['peak_dated_day_end'] is None)
        # Registry completeness and limited-search frontier, independently recomputed.
        ds=rows('candidate_dispositions.csv');hs=rows('hypothesis_dispositions.csv')
        check('223_author_and_169_hypothesis_individual_rows',len(ds)==223 and len({x['candidate_id'] for x in ds})==223 and len(hs)==169 and all(x['source_row_sha256'] for x in ds+hs))
        counts=collections.Counter(x['status'] for x in ds)
        check('OPEN_is_visible_and_not_economic_rejection',any('OPEN' in x['status'] for x in ds) and all(x['economic_rejection']=='False' for x in ds),dict(counts))
        resultrows=rows('scenario_results.csv')
        data={(x['programme_id'],x['scenario']):x for x in resultrows if x['delivery']=='phased' and x['response']=='passive'}
        points=[]
        for pid,p in programmes.items():
            if pid=='KEEP' or 'LOCAL_ONLY' in pid or p.get('stage_fragment'):continue
            rr=[data.get((pid,s),{}) for s in ['base','cautious']]
            if all(x.get('status')=='CONDITIONAL_P05_P06_CALCULATED' for x in rr):
                points.append((pid,min(float(x['delta_known_operating_subtotal']) for x in rr),min(float(x['delta_journeys']) for x in rr)))
        front={x[0] for x in points if not any(y[1]>=x[1] and y[2]>=x[2] and (y[1]>x[1]+1e-5 or y[2]>x[2]+1e-5) for y in points)}
        selected=j('finalist_selection.json')
        check('limited_set_frontier_recomputed',front=={x['programme_id'] for x in selected['frontier']} and selected['global_optimum'] is False,sorted(front))
        return dict(resource=resource,donor_delta_journeys=sr['delta_journeys'],donor_H=sr['delta_known_operating_subtotal'],cash_day_end_peak=f['peak_dated_day_end'],cash_month_end_peak=f['peak_month_end'],dispositions=dict(counts),frontier=sorted(front))

    for name,fn in [('G1_REAL_REPLAY_AND_CANONICAL_PROJECTION',group1),('G2_JOINT_OD_SEATS_FARE_AND_UNKNOWN_BOUNDARIES',group2),('G3_RESOURCE_DONOR_CASH_THRESHOLDS_AND_CONCLUSIONS',group3)]:
        start=time.monotonic();n=len(ASSERTIONS)
        print('START',name,flush=True)
        try:
            evidence=fn();result=dict(group=name,status='PASS',checks=len(ASSERTIONS)-n,evidence=evidence)
        except Exception as exc:
            result=dict(group=name,status='FAIL',checks=len(ASSERTIONS)-n,error=str(exc),traceback=traceback.format_exc())
        result['seconds']=time.monotonic()-start;RESULTS.append(result)
        dump(OUT/'tests/results.json',dict(root=ROOT,manifest_sha256=MANIFEST,groups=RESULTS,assertions=ASSERTIONS))
        print(json.dumps(result,ensure_ascii=False),flush=True)
finally:
    dump(OUT/'sources/pins.json',dict(exact_root=ROOT,manifest_sha256=MANIFEST,manifest_payload_files=2617,manifest_payload_bytes=754088586,selection='Selected exact Git bytes only; no full input corpus or payload copy',files=list(READS.values()),unique_bytes_read=sum(x['bytes'] for x in READS.values())))
    shutil.rmtree(runtime)
