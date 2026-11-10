#!/usr/bin/env python3
"""Bounded offline review. Every reviewed input is obtained with git show at a pin.

Run from the prepared checkout: python3 <this file> --stage
Temporary author code/data stay under .runtime and are excluded from the handoff.
No downloads, installations, external calls, author check.py or strategy-budget run.
"""
import argparse
import collections
import contextlib
import csv
import datetime as dt
import functools
import hashlib
import importlib
import io
import itertools
import json
import math
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import traceback
import types

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PREFIX = 'context/23_night_run_20261110/model_repair/'
PAYLOAD = 'dc5c65d12e0236f5aaa6182ca83bda0d52c10f57'
HANDOFF = '27740ffea0821aa404ecd1013d1bb141613261f3'
AUTHOR = '2f03b693a62c219e9475fcd1e26295039f6a49d7'
CIRI = '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
REVIEW_BASE = 'e2ae98e184f48a64dd627dcdb2f2543c73226b3b'
RUNTIME = ROOT / '.runtime'
SNAP = RUNTIME / 'payload'
SOURCES = {}
CHECKS = []
DETAIL = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


@functools.lru_cache(maxsize=None)
def show(ref, path):
    data = subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=REPO)
    SOURCES[ref + ':' + path] = dict(commit=ref, path=path, bytes=len(data), sha256=digest(data))
    return data


def js(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def rows(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def pinned_rows(path, ref=PAYLOAD, prefix=PREFIX):
    return list(csv.DictReader(io.StringIO(show(ref, prefix + path).decode('utf-8-sig'))))


def near(a, b, atol=1e-6):
    assert math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=atol), (a, b)


def table(path, data):
    data = list(data)
    keys = list(dict.fromkeys(k for r in data for k in r))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, keys, lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)


def compare_csv(expected, actual):
    assert len(expected) == len(actual), (len(expected), len(actual))
    max_delta = 0.
    for i, (a, b) in enumerate(zip(expected, actual)):
        assert a.keys() == b.keys(), i
        for k in a:
            try:
                x, y = float(a[k]), float(b[k])
            except (ValueError, TypeError):
                assert a[k] == b[k], (i, k, a[k], b[k])
            else:
                if math.isnan(x) and math.isnan(y):
                    continue
                near(x, y)
                max_delta = max(max_delta, abs(x-y))
    return dict(rows=len(expected), differing_cells=0, max_numeric_abs_delta=max_delta)


def run_check(name, fn):
    try:
        value = fn()
    except Exception as exc:
        CHECKS.append(dict(id=name, status='FAIL', error=repr(exc), traceback=traceback.format_exc()))
        print(name, 'FAIL', repr(exc), flush=True)
    else:
        CHECKS.append(dict(id=name, status='PASS', result=value))
        print(name, 'PASS', flush=True)


def stage():
    # ls-tree supplies only names; all input bytes are read by git show.
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', PAYLOAD, '--', PREFIX], cwd=REPO, text=True).splitlines()
    for name in names:
        target = SNAP / name[len(PREFIX):]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(show(PAYLOAD, name))
    return dict(files=len(names), bytes=sum(p.stat().st_size for p in SNAP.rglob('*') if p.is_file()))


def snapshot_identity():
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',PAYLOAD,'--',PREFIX],cwd=REPO,text=True).splitlines()
    for name in names:
        assert (SNAP/name[len(PREFIX):]).read_bytes()==show(PAYLOAD,name),name
    handoff=json.loads(show(HANDOFF,PREFIX+'handoff.json'))
    assert handoff['payload_commit']==PAYLOAD
    artifact=json.loads(show(PAYLOAD,PREFIX+'artifact_manifest.json'))
    for item in artifact['artifacts']:
        assert digest(show(PAYLOAD,PREFIX+item['path']))==item['sha256'],item['path']
    return dict(snapshot_files=len(names),artifact_hashes=len(artifact['artifacts']),
                input_head=HANDOFF,payload=PAYLOAD,all_snapshot_bytes_equal=True)


def sources():
    for name in ('contract.md','briefs/model_repair_review.md'):
        show(REVIEW_BASE,'context/23_night_run_20261110/'+name)
    manifest = json.loads(show(PAYLOAD, PREFIX + 'source_manifest.json'))
    checked = 0
    for entry in manifest['inputs']:
        data = show(PAYLOAD, PREFIX + entry['local_path'])
        assert digest(data) == entry['sha256']
        if 'raw_sha256' not in entry:
            original = show(entry['source_commit'], entry['source_path'])
            assert data == original
            checked += 1
    for entry in json.loads(show(PAYLOAD, PREFIX + 'ciri/source_manifest.json')):
        data = show(PAYLOAD, PREFIX + entry['local_path'])
        assert digest(data) == entry['sha256']
        assert data == show(entry['source_commit'], entry['source_path'])
        checked += 1
    for name in ('network_routes.csv', 'network_summary.csv', 'mandatory_routes_table.csv'):
        assert show(PAYLOAD, PREFIX+'frozen_exports/'+name) == show(AUTHOR, 'data/processed/'+name)
    for name in ('comparison.csv', 'routes.csv'):
        assert show(PAYLOAD, PREFIX+'ciri/frozen_exports/'+name) == show(CIRI, 'context/21_team_proposals/'+name)
    assert show(PAYLOAD, PREFIX+'ciri/frozen_exports/stage17_flights.csv') == show(CIRI, 'context/17_aircraft_route_review/model/flights.csv')
    receipt = json.loads(show(PAYLOAD, PREFIX+'public_restore_receipt.json'))
    original_receipt = json.loads(show(AUTHOR, 'data/raw/_manifest.json'))
    assert receipt['raw_sha256'] in json.dumps(original_receipt)
    projection = show(PAYLOAD, PREFIX+'inputs/tochno_runtime_projection.csv')
    assert projection == show(PAYLOAD, PREFIX+'author/data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv')
    projected = list(csv.DictReader(io.StringIO(projection.decode('utf-8-sig')), delimiter=';'))
    assert len(projected) == receipt['projected_rows'] == 64440
    assert all(r['transport_type'] in ('air', 'rail') for r in projected)
    return dict(original_files_byte_matched=checked, author_exports_preserved=5, projection_rows=len(projected),
                raw_receipt_hash_preserved=receipt['raw_sha256'], full_raw_download='NOT_RUN',
                limitation='Receipt/raw manifest cross-check, not an independent rehash of absent full raw.')


def deny_network(*args, **kwargs):
    raise RuntimeError('INDEPENDENT_REVIEW_OFFLINE_NETWORK_FORBIDDEN')


def load_anastasia():
    sys.path.insert(0, str(SNAP/'author/src'))
    sys.path.insert(0, str(SNAP))
    return importlib.import_module('network_model'), importlib.import_module('corrected_model')


def author_replay():
    nm, fix = load_anastasia()
    destination = RUNTIME/'author_replay'
    destination.mkdir(exist_ok=True)
    for name in ('demand_fit.json','demand_pairs.csv','kover_days.csv','longlist.csv','longlist_scores_min500.csv'):
        shutil.copyfile(SNAP/'author/data/processed'/name, destination/name)
    original_p, direct_fn, hub_fn = nm.P, nm.direct_network, nm.hub_network
    direct_results, hub_results = {}, {}
    def direct(D,A,sc,nodes):
        result = direct_fn(D,A,sc,nodes)
        direct_results[sc] = result
        return result
    def hub(H,D,A,sc,nodes):
        result = hub_fn(H,D,A,sc,nodes)
        hub_results[sc,H] = result
        return result
    try:
        nm.P, nm.direct_network, nm.hub_network = destination, direct, hub
        with (RUNTIME/'anastasia_replay.log').open('w') as f, contextlib.redirect_stdout(f):
            nm.main()
    finally:
        nm.P, nm.direct_network, nm.hub_network = original_p, direct_fn, hub_fn
    DETAIL['direct_results'], DETAIL['hub_results'] = direct_results, hub_results
    matches = {}
    for name in ('network_routes.csv','network_summary.csv','mandatory_routes_table.csv'):
        expected = pinned_rows('data/processed/'+name, AUTHOR, '')
        matches[name] = compare_csv(expected, rows(destination/name))
    return matches


def share(L, f, A):
    """Scalar oracle, deliberately no calls to nm.leg_share or fix.evaluate."""
    if L['km'] < A['transfer_min_km']:
        return 0.
    if L['competitive']:
        competitor = L['dem'] / (A['seats'] * A['competitor_lf'])
        return min(A['capture_competitive'], f/(f+competitor)) if competitor else 0.
    return A['capture_open'] * -math.expm1(-f/A['capture_freq_scale'])


def cost_per_flight(A, L, passengers):
    factor = A['route_factor_south'] if L['south'] else A['route_factor']
    h = A['block_fixed_h'] + L['km']*factor/A['block_speed_kmh']
    cost = ((A['fuel_t_per_hour']*h + A['fuel_t_per_cycle'])*A['fuel_rub_per_t']
            + (A['mro_rub_per_hour']+A['crew_rub_per_hour']+A['navigation_rub_per_hour'])*h
            + A['ground_rub_per_flight'] + A['deicing_rub_per_flight'] + passengers*A['pax_cost_rub'])
    return h, cost


def oracle_totals(programs, A, law):
    """Pool totals from scalar equations; allocation is immaterial to linear costs."""
    groups = collections.defaultdict(list)
    h = fixed_cost = 0.
    for t in programs:
        f = t['freq']
        for L in t['legs']:
            groups[tuple(sorted((L['a'],L['b'])))].append((L,f))
            lh, lc = cost_per_flight(A,L,0)
            h += 2*f*lh
            fixed_cost += 2*f*lc
    sold = revenue = 0.
    pools = {}
    for key, entries in groups.items():
        L = entries[0][0]
        F = sum(f for _,f in entries)
        available = sum(f*A['seats']*A['lf_max'] for _,f in entries)
        author = sum(min(Li['dem']*share(Li,f,A), f*A['seats']*A['lf_max']) for Li,f in entries)
        if law == 'author':
            count = author
        elif law == 'D':
            count = min(L['dem'],author)
        else:
            count = min(L['dem'],L['dem']*share(L,F,A),available)
        pools['-'.join(key)] = dict(market=L['dem'],frequency=F,seats_at_lf_max=available,sold=count,
                                    independent_author_sold=author)
        sold += 2*count
        revenue += 2*count*(A['fare_fixed_rub']+A['fare_per_km_rub']*L['km'])
    return dict(h=h,c=fixed_cost+sold*A['pax_cost_rub'],r=revenue,s=sold,pools=pools)


def own_templates(nm,D,A,sc,nodes):
    programs=[]
    W=A['weeks_per_year']
    eligible=[x for x in nodes if x not in nm.CLOSED and x not in ('MOW','SVX')]
    for X,Y in itertools.combinations(eligible,2):
        distance=D.km(X,Y)
        if distance<A['transfer_min_km'] or distance>D.green(X,Y) or D.has_direct(X,Y):
            continue
        for B in ('MOW','SVX'):
            bx,yb=D.km(B,X),D.km(Y,B)
            if bx>D.green(B,X) or yb>D.green(Y,B) or bx+yb>A['triangle_detour_factor']*distance+A['triangle_detour_add_km']:
                continue
            legs=[dict(a=a,b=b,km=d,south=D.south(a,b),competitive=D.has_direct(a,b),dem=D.get(a,b,sc)/(2*W))
                  for a,b,d in ((B,X,bx),(X,Y,distance),(Y,B,yb))]
            frequency=int(A['min_freq_week'])
            while True:
                need=max(L['dem']*share(L,frequency,A) for L in legs)/(A['seats']*A['lf_max'])
                next_f=int(min(A['direct_max_freq_week'],max(A['min_freq_week'],math.ceil(need))))
                if frequency==next_f:
                    break
                frequency=next_f
            programs.append(dict(B=B,X=X,Y=Y,legs=legs,freq=frequency))
    return programs


def own_select(nm,D,A,sc,nodes):
    templates=own_templates(nm,D,A,sc,nodes)
    selected=[]
    used=set()
    current=dict(h=0.,c=0.,r=0.)
    trace=[]
    ceiling=(A['fleet_cap']-A['spare_aircraft'])*A['block_h_per_day']*7
    while len(selected)<A['max_routes']:
        choices=[]
        for t in templates:
            if tuple(sorted((t['X'],t['Y']))) in used:
                continue
            trial=oracle_totals(selected+[t],A,'Q')
            if trial['h']>ceiling+1e-9:
                continue
            delta=(trial['r']-trial['c'])-(current['r']-current['c'])
            choices.append((delta/(trial['h']-current['h']),t,trial))
        if not choices:
            break
        score,t,trial=max(choices,key=lambda x:x[0])
        if score<=0 and len(selected)>=A['min_routes']:
            break
        trace.append(dict(step=len(selected)+1,triangle='-'.join((t['B'],t['X'],t['Y'])),
                          frequency=t['freq'],marginal_contribution_per_block_hour=score))
        selected.append(t)
        used.add(tuple(sorted((t['X'],t['Y']))))
        current=trial
    return selected,current,trace


def shared_market_real_replay():
    nm,fix=load_anastasia()
    D=nm.Demand()
    summaries=pinned_rows('evaluation_summary.csv')+pinned_rows('market_bound_only_summary.csv')
    examples=json.loads(show(PAYLOAD,PREFIX+'shared_pair_example.json'))
    details=[]
    traces=[]
    selections=pinned_rows('selected_triangles.csv')
    for sc,A in nm.load_assumptions().items():
        chosen=DETAIL['direct_results'][sc]
        programs=fix.from_author(chosen)
        raw=oracle_totals(programs,A,'author')
        Dguard=oracle_totals(programs,A,'D')
        fixed=oracle_totals(programs,A,'Q')
        for field in ('h','c','r','s'):
            near(raw[field],Dguard[field])
        assert all(p['independent_author_sold']<=p['market']+1e-7 for p in raw['pools'].values())
        minimum,pools=fix.evaluate(nm,programs,A,'standalone_claim','market_bound_only')
        pooled,_=fix.evaluate(nm,programs,A)
        alternative,_=fix.evaluate(nm,programs,A,'standalone_claim')
        for actual,expected in ((minimum,Dguard),(pooled,fixed),(alternative,fixed)):
            for value,field in zip(fix.totals(actual),('h','c','r','s')):
                near(value,expected[field])
        independent,selected_totals,trace=own_select(nm,D,A,sc,list(D.n.index))
        reselected=fix.select(nm,D,A,sc,list(D.n.index))
        expected_names=['-'.join((t['B'],t['X'],t['Y'])) for t in independent]
        actual_names=['-'.join(c[1:4]) for c in reselected]
        assert expected_names==actual_names
        stored=[r for r in selections if r['run_id']=='CORRECTED_RESELECTED' and r['scenario_id']==sc]
        assert expected_names==[r['triangle'] for r in stored]
        for r,t in zip(stored,independent):near(r['frequency'],t['freq'])
        for value,field in zip(fix.totals(reselected),('h','c','r','s')):
            near(value,selected_totals[field])
        W=A['weeks_per_year']
        for mode,expected in (('AUTHOR_REPLAY',raw),('CORRECTED_MARKET_BOUND_ONLY',Dguard),
                              ('CORRECTED_FIXED_SELECTION',fixed),('CORRECTED_RESELECTED',selected_totals),
                              ('CORRECTED_CLAIM_ALLOCATION',fixed)):
            row=next(r for r in summaries if r['run_id']==mode and r['scenario_id']==sc and r['candidate_id']=='DIRECT')
            for field,value in (('annual_trips',expected['s']*W),('annual_gross_revenue_rub',expected['r']*W),
                                ('annual_variable_cost_rub',expected['c']*W),
                                ('annual_contribution_before_base_fleet_opportunity_rub',(expected['r']-expected['c'])*W),
                                ('weekly_block_hours',expected['h'])):
                near(row[field],value,1e-4)
        mow=raw['pools']['MOW-OMS']
        e=next(e for e in examples if e['scenario']==sc)
        before=mow['sold']*2*W
        after=fixed['pools']['MOW-OMS']['sold']*2*W
        near(before,e['before_exact'])
        near(after,e['common_pool_exact'])
        near(mow['market']*2*W,e['annual_input_market'])
        details.append(dict(scenario=sc,annual_MOW_OMS_D=mow['market']*2*W,
            annual_MOW_OMS_author=before,annual_MOW_OMS_Q=after,D_only_contribution_delta=0.,
            Q_fixed_annual_trips_delta=(fixed['s']-raw['s'])*W,
            Q_fixed_annual_contribution_delta=((fixed['r']-fixed['c'])-(raw['r']-raw['c']))*W,
            Q_reselected_annual_contribution=(selected_totals['r']-selected_totals['c'])*W,
            author_triangles=['-'.join(c[1:4]) for c in chosen],reselected_triangles=expected_names,
            unique_pairs_before=len(raw['pools']),unique_pairs_reselected=len(selected_totals['pools'])))
        traces.extend(dict(scenario=sc,**r) for r in trace)
    js(ROOT/'real_market_replay.json',details)
    table(ROOT/'independent_selection_trace.csv',traces)
    return dict(scenarios=2,independent_template_and_selection_oracle=True,D_current_saved_exceedance=False,
                D_only_delta=0.,pooled_Q='AGENT_PROPOSAL',results='real_market_replay.json')


def shared_market_counterexamples():
    nm,fix=load_anastasia()
    A=nm.load_assumptions()['base']
    results=[]
    # 4 * min(300 * .65*(1-exp(-2)),2*85) > D=300. No dependence on author fixture.
    L=dict(a='AAA',b='BBB',km=910.,south=False,competitive=False,dem=300.)
    programs=[dict(B='B',X='X'+str(i),Y='Y'+str(i),freq=2,legs=[dict(L,**({'a':'BBB','b':'AAA'} if i%2 else {}))]) for i in range(4)]
    raw=oracle_totals(programs,A,'author')
    assert raw['pools']['AAA-BBB']['sold']>300
    for allocation in ('frequency','standalone_claim'):
        chosen,pool=fix.evaluate(nm,programs,A,allocation,'market_bound_only')
        near(sum(c[7]/2 for c in chosen),300.)
        assert len(pool)==1
        results.append(dict(case='D_exceedance_four_programs',allocation=allocation,
                            D=300.,author_sold=raw['pools']['AAA-BBB']['sold'],guard_sold=sum(c[7]/2 for c in chosen)))
    # Three overlapping programs, unequal frequencies and reverse representations.
    programs=programs[:3]
    for t,f in zip(programs,(1,2,5)):t['freq']=f
    for law in ('market_bound_only','author_at_total_frequency'):
        economic=[]
        for permutation in itertools.permutations(programs):
            for allocation in ('frequency','standalone_claim'):
                chosen,pools=fix.evaluate(nm,list(permutation),A,allocation,law)
                economic.append(fix.totals(chosen))
                assert len(pools)==1
                sold=sum(c[7]/2 for c in chosen)
                assert sold<=300+1e-7
                for c in chosen:
                    for leg in c[8]:assert 0<=leg['carried_dir_week']<=leg['freq']*A['seats']*A['lf_max']+1e-7
        for metric in range(4):
            for values in economic:near(values[metric],economic[0][metric])
        results.append(dict(case='three_programs_reverse_unequal_frequencies_all_permutations',law=law,
                            runs=len(economic),frequency=8,sold=economic[0][3]/2))
    # Seat saturation and zero capacity must spill; no hidden new sales or revenue.
    crowded=[dict(t,legs=[dict(L,dem=1e8)]) for t in programs]
    for allocation in ('frequency','standalone_claim'):
        chosen,pools=fix.evaluate(nm,crowded,A,allocation)
        near(sum(c[7]/2 for c in chosen),8*A['seats']*A['lf_max'])
        assert pools[0]['spill']>0
        zero=dict(A,lf_max=0.)
        empty,spills=fix.evaluate(nm,crowded,zero,allocation)
        near(sum(c[7] for c in empty),0)
        near(sum(c[6] for c in empty),0)
        assert spills[0]['sold']==0 and spills[0]['spill']>0
    near(sum(fix.weighted_capped(180,[1,4,2],[15,55,200])),180.)
    assert fix.weighted_capped(180,[1,4,2],[15,55,200])==[15.,55.,110.]
    results.append(dict(case='seats_and_zero_capacity',offered_at_lf_max=8*A['seats']*A['lf_max'],zero_capacity_sales=0))
    # Isolate selector's actual code, with a candidate that loses existing sales.
    fake=types.SimpleNamespace(leg_share=lambda L,f,A:-math.expm1(-f),
        leg_cost=lambda A,km,south,pax:(1.,30.),fare=lambda A,km:1.)
    B=dict(seats=1000.,lf_max=1.,fleet_cap=100.,spare_aircraft=0.,block_h_per_day=10.,min_routes=1,max_routes=3)
    def t(name,a,b,demand):
        return dict(B='B',X=name,Y=name+'Y',freq=1,legs=[dict(a=a,b=b,km=1000.,south=False,competitive=False,dem=demand)])
    fixtures=[t('FIRST','A','S',100),t('OVERLAP','S','A',100),t('UNIQUE','U','V',60)]
    fn=fix.templates
    try:
        fix.templates=lambda *a:fixtures
        selected=fix.select(fake,None,B,'synthetic',[])
    finally:
        fix.templates=fn
    assert [c[2] for c in selected]==['FIRST','UNIQUE']
    before,_=fix.evaluate(fake,fixtures[:1],B)
    after,_=fix.evaluate(fake,fixtures[:2],B)
    standalone,_=fix.evaluate(fake,fixtures[1:2],B)
    old_loss=before[0][6]-after[0][6]
    standalone_gain=standalone[0][6]-standalone[0][5]
    actual_gain=sum(c[6]-c[5] for c in after)-sum(c[6]-c[5] for c in before)
    assert old_loss>0 and standalone_gain>0 and actual_gain<0
    near(actual_gain,standalone_gain-old_loss-(standalone[0][6]-after[1][6]))
    results.append(dict(case='selector_charges_loss_of_existing_program',selected=['FIRST','UNIQUE'],
                        standalone_candidate_contribution=standalone_gain,existing_program_revenue_loss=old_loss,
                        full_network_marginal_contribution=actual_gain))
    table(ROOT/'independent_counterexamples.csv',results)
    return dict(cases=results,greedy_order='ties may use enumeration order; not a global optimiser')


def anastasia_primary_ledgers():
    nm,fix=load_anastasia()
    D=nm.Demand()
    summaries=pinned_rows('evaluation_summary.csv')+pinned_rows('market_bound_only_summary.csv')
    summary={(r['run_id'],r['scenario_id'],r['candidate_id']):r for r in summaries}
    counts=collections.Counter()
    examples=[]
    for path in sorted((SNAP/'ledgers').rglob('itinerary.csv')):
        run,sc,candidate=path.relative_to(SNAP/'ledgers').parts[:3]
        A=nm.load_assumptions()[sc]
        factor=2*A['weeks_per_year']
        itineraries=rows(path)
        incidence=rows(path.with_name('itinerary_leg.csv'))
        allocations=rows(path.with_name('capacity_allocation.csv'))
        legs=rows(path.with_name('physical_leg.csv'))
        money=rows(path.with_name('money_ledger.csv'))
        assert incidence==allocations
        by_it={r['itinerary_id']:r for r in itineraries}
        by_leg={r['physical_leg_id']:r for r in legs}
        assert len(by_it)==len(itineraries) and len(by_leg)==len(legs)
        consumption=collections.Counter()
        journeys=segments=transfer=revenue=0.
        market_sold=collections.Counter()
        expected_trips={}
        if candidate!='DIRECT':
            _,source=DETAIL['hub_results'][sc,candidate]
            hub_legs,transfers,_,_,_,_,_,_=source
            expected_trips.update({'LOCAL_'+x:factor*l['local_carried'] for x,l in hub_legs.items()})
            expected_trips.update({'TRANSFER_'+a+'_'+b:factor*t for a,b,_,t in transfers})
        else:
            author=DETAIL['direct_results'][sc]
            if run=='AUTHOR_REPLAY':direct=author
            elif run=='CORRECTED_RESELECTED':direct=fix.select(nm,D,A,sc,list(D.n.index))
            else:
                allocation='standalone_claim' if run in ('CORRECTED_CLAIM_ALLOCATION','CORRECTED_MARKET_BOUND_ONLY') else 'frequency'
                law='market_bound_only' if run=='CORRECTED_MARKET_BOUND_ONLY' else 'author_at_total_frequency'
                direct,_=fix.evaluate(nm,fix.from_author(author),A,allocation,law)
            expected_trips={f'T{ti}_L{li}':factor*l['carried_dir_week'] for ti,c in enumerate(direct) for li,l in enumerate(c[8])}
        assert set(expected_trips)==set(by_it)
        for r in itineraries:
            j=float(r['annual_trips'])
            is_transfer=r['transfer']=='True'
            assert r['direction_scope']=='BOTH_DIRECTIONS_SYMMETRIC'
            assert r['period_start']==r['period_end']==''
            # Older frozen ledgers have period_reason and acceptance_scope;
            # source_grain was added to the generator without rewriting them.
            if 'source_grain' in r:assert r['source_grain']=='UNDATED_SYMMETRIC_PAIR_AGGREGATE_NOT_PHYSICAL_FLIGHT'
            assert r['period_reason']=='annualized scenario; no dated flight calendar'
            assert r['acceptance_scope']=='AGGREGATE_WEEKLY_CONSERVATION_ONLY'
            near(j,expected_trips[r['itinerary_id']])
            ids=r['leg_ids'].split(';')
            assert len(ids)==int(r['leg_count'])==(2 if is_transfer else 1)
            attached=[i for i in incidence if i['itinerary_id']==r['itinerary_id']]
            assert len(attached)==len(ids) and {i['physical_leg_id'] for i in attached}==set(ids)
            distance=D.km(r['origin'],r['destination'])
            fare=(A['fare_fixed_rub']+A['fare_per_km_rub']*distance)*(A['transfer_fare_factor'] if is_transfer else 1)
            near(fare,r['fare_once'])
            near(j*fare,r['gross_revenue'])
            near(j*len(ids),r['annual_segments'])
            for inc in attached:
                near(inc['occupied'],j)
                consumption[inc['physical_leg_id']]+=j
            if is_transfer:
                # In a symmetric aggregate, each incidence is an unordered pair.
                edges=[set((by_leg[key]['origin'],by_leg[key]['destination'])) for key in ids]
                assert len(edges[0]&edges[1])==1
                assert edges[0]^edges[1]=={r['origin'],r['destination']}
                transfer+=j
                if len(examples)<4:
                    examples.append(dict(run=run,scenario=sc,candidate=candidate,itinerary=r['itinerary_id'],
                                         annual_journeys=j,annual_segments=2*j,fare_once=fare,
                                         annual_revenue=j*fare,aggregate_legs=ids))
            market_sold[tuple(sorted((r['origin'],r['destination'])))]+=j
            journeys+=j;segments+=j*len(ids);revenue+=j*fare
        near(segments,journeys+transfer)
        for key,l in by_leg.items():
            assert l['date']=='' and l['date_reason']=='author_has_no_calendar'
            near(l['occupied'],consumption[key])
            near(l['offered_seats'],factor*float(l['frequency_each_direction'])*A['seats'])
            near(l['seats_at_lf_max'],float(l['offered_seats'])*A['lf_max'])
            assert consumption[key]<=float(l['seats_at_lf_max'])+1e-6
        for (a,b),sold in market_sold.items():assert sold<=D.get(a,b,sc)+1e-5
        entries={r['entry']:r for r in money}
        assert len(entries)==len(money)
        assert entries['cannibalization_foregone_revenue']['annual_rub']==''
        assert entries['cannibalization_foregone_revenue']['status']=='NOT_MODELED_BY_AUTHOR'
        assert entries['full_strategy_budget']['annual_rub']==''
        assert entries['full_strategy_budget']['status']=='UNKNOWN_NOT_ZERO'
        near(entries['gross_revenue']['annual_rub'],revenue)
        near(entries['new_pax_variable_cost']['annual_rub'],segments*A['pax_cost_rub'])
        r=summary[run,sc,candidate]
        for field,actual in (('annual_trips',journeys),('annual_segments',segments),('annual_transfer_trips',transfer),
                            ('annual_gross_revenue_rub',revenue)):
            near(r[field],actual,1e-4)
        near(float(entries['flight_variable_cost']['annual_rub'])+float(entries['new_pax_variable_cost']['annual_rub']),
             r['annual_variable_cost_rub'],1e-4)
        counts.update(networks=1,itineraries=len(itineraries),incidences=len(incidence),aggregate_legs=len(legs))
    js(ROOT/'primary_ledger_examples.json',examples)
    return dict(**counts,unit='annual both-direction journeys/segments; one weekly direction x 2 x 52 or 48',
                own_migration='NULL_NOT_MODELED',calendar='NOT_RUN_NO_DATED_AUTHOR_INPUT',
                original_ledgers_read=True,examples='primary_ledger_examples.json')


def anastasia_asymmetric_hub_counterexample():
    nm,_=load_anastasia()
    class Demand:
        distances={frozenset(('H','P')):650.,frozenset(('H','Q')):850.,frozenset(('P','Q')):1250.}
        annual={frozenset(('H','P')):135000.,frozenset(('H','Q')):14000.,frozenset(('P','Q')):155000.}
        def km(self,a,b):return self.distances[frozenset((a,b))]
        def get(self,a,b,sc):return self.annual[frozenset((a,b))]
        def has_direct(self,a,b):return False
        def green(self,a,b):return 3000.
        def south(self,a,b):return False
    A=dict(nm.load_assumptions()['base'],min_routes=2,max_routes=2,fleet_cap=100.)
    _,r=nm.hub_network('H',Demand(),A,'base',['H','P','Q'])
    legs,transfers,h,c,revenue,local,transfer,_=r
    assert len(transfers)==1
    t=transfers[0][3]
    assert t>0 and len({l['freq'] for l in legs.values()})==2
    local_revenue=0.
    for l in legs.values():
        assert l['local_carried']>0
        near(l['transfer_carried'],t)
        near(l['carried_dir_week'],l['local_carried']+t)
        assert l['carried_dir_week']<=l['freq']*A['seats']*A['lf_max']+1e-7
        local_revenue+=2*l['local_carried']*(A['fare_fixed_rub']+A['fare_per_km_rub']*l['km'])
    through_fare=(A['fare_fixed_rub']+A['fare_per_km_rub']*1250)*A['transfer_fare_factor']
    near(revenue,local_revenue+2*t*through_fare)
    near(sum(2*l['carried_dir_week'] for l in legs.values()),local+2*transfer)
    wrong=local_revenue+2*t*sum(A['fare_fixed_rub']+A['fare_per_km_rub']*l['km'] for l in legs.values())*A['transfer_fare_factor']
    assert abs(wrong-revenue)>1000
    result=dict(frequencies={k:l['freq'] for k,l in legs.items()},weekly_both_direction_transfer_journeys=2*t,
                weekly_both_direction_trips=local+transfer,weekly_segments=local+2*transfer,
                through_fare_once=through_fare,weekly_revenue=revenue,wrong_sum_of_leg_fares_revenue=wrong)
    js(ROOT/'independent_anastasia_hub_counterexample.json',result)
    return result


def load_ciri():
    sys.path.insert(0,str(SNAP/'ciri/scripts'))
    return importlib.import_module('build_aircraft_route_review'),importlib.import_module('build_team_proposals')


def ciri_replay_and_primary_accounting():
    review,program=load_ciri()
    original=review.RouteModel.evaluate
    old_out=program.OUT
    destination=RUNTIME/'ciri_replay'
    destination.mkdir(exist_ok=True)
    captures=[]
    def capture(self,net,sc,*args,**kwargs):
        value=original(self,net,sc,*args,**kwargs)
        if kwargs.get('detail'):
            captures.append((self,net,sc,value))
        return value
    try:
        review.RouteModel.evaluate=capture
        program.OUT=destination
        with (RUNTIME/'ciri_replay.log').open('w') as f,contextlib.redirect_stdout(f):
            program.main()
    finally:
        review.RouteModel.evaluate=original
        program.OUT=old_out
    matches={name:compare_csv(pinned_rows('context/21_team_proposals/'+name,CIRI,''),rows(destination/name))
             for name in ('comparison.csv','routes.csv')}
    assert len(captures)==8
    original_sales=pinned_rows('ciri/itinerary_sales.csv')
    original_capacity=pinned_rows('ciri/flight_capacity.csv')
    counts=collections.Counter()
    evidence=[]
    for m,net,sc,(result,sales,capacities) in captures:
        key=(m.profile,net['name'],sc)
        pinned_sales=[r for r in original_sales if (r['profile'],r['network'],r['scenario'])==key]
        pinned_caps=[r for r in original_capacity if (r['profile'],r['network'],r['scenario'])==key]
        # Convert generated values to CSV representations for the value comparator.
        def as_csv(records):return [{k:'' if v is None else str(v) for k,v in r.items()} for r in records]
        compare_csv(pinned_sales,as_csv(sales))
        compare_csv(pinned_caps,as_csv(capacities))
        p=m.scenarios[sc]
        flights={l['id']:l for l in net['legs']}
        assert len(flights)==len(net['legs'])
        used=collections.Counter();sold_by_od=collections.Counter();migration=collections.Counter()
        totals=collections.Counter()
        for s in pinned_sales:
            origin,destination=s['origin'],s['destination']
            j=float(s['sold_journeys']);is_transfer=s['transfer']=='True'
            ids=s['flight_ids'].split(';')
            assert len(ids)==(2 if is_transfer else 1)
            legs=[flights[i] for i in ids]
            assert legs[0]['origin']==origin and legs[-1]['destination']==destination
            assert all(l['date']>='2026-12-07' and l['date']<='2026-12-13' for l in legs)
            for a,b in zip(legs,legs[1:]):
                assert a['destination']==b['origin']
                assert m.cfg['min_connection_minutes']<=b['departure_utc_minute']-a['arrival_utc_minute']<=m.cfg['max_connection_minutes']
            market=m.markets[review.core.pair(origin,destination)]
            fare=market['fare_'+sc]*(p['transfer_fare_factor'] if is_transfer else 1)
            near(s['fare_once'],fare)
            near(s['D'],market['demand_'+sc])
            direct=float(s['migrated_RW_direct']);unknown=float(s['migrated_RW_unverified_connecting'])
            near(s['migrated_RW_total'],direct+unknown)
            near(s['gross_revenue'],j*fare)
            near(s['segment_pax'],j*len(ids))
            near(s['transfer_journeys'],j if is_transfer else 0)
            lost=(direct+unknown)*market['fare_'+sc]*p['old_RW_fare_ratio']
            saved=(direct+2*unknown)*p['pax_cost']
            near(s['foregone_RW_revenue'],lost)
            near(s['saved_old_pax_variable'],saved)
            near(s['new_pax_variable'],j*len(ids)*p['pax_cost'])
            near(s['incremental_revenue'],j*fare-lost)
            sold_by_od[origin,destination]+=j
            migration[origin,destination]+=direct
            for flight in ids:used[flight]+=j
            for field in ('sold_journeys','transfer_journeys','segment_pax','gross_revenue','foregone_RW_revenue',
                          'saved_old_pax_variable','new_pax_variable','incremental_revenue','migrated_RW_total'):
                totals[field]+=float(s[field])
        for (a,b),sold in sold_by_od.items():
            market=m.markets[review.core.pair(a,b)]
            offered=net['itineraries'][a,b]
            is_transfer=offered[0]['transfer']
            q=p['capture_'+('transfer' if is_transfer else market['capture_group'])]*-math.expm1(-len(offered)/p['frequency_scale'])
            if is_transfer:q=min(1,q*market.get('transfer_competition_factor',1))
            assert sold<=market['demand_'+sc]*q+1e-6
            cap=m.rw_cap(a,b)
            if cap is not None:assert migration[a,b]<=cap+1e-6
        for c in pinned_caps:
            occupied=used[c['flight_id']]
            near(c['occupied'],occupied)
            assert 0<=occupied<=float(c['capacity_scenario'])+1e-6
        flight_cost=sum(float(c['flight_variable_cost']) for c in pinned_caps)
        near(result['flight_variable_cost'],flight_cost)
        for field,value in totals.items():near(result[field],value)
        contribution=totals['gross_revenue']-totals['foregone_RW_revenue']-flight_cost-totals['new_pax_variable']+totals['saved_old_pax_variable']
        near(result['contribution_before_base_fleet_opportunity'],contribution)
        near(result['incremental_operating_cost'],flight_cost+totals['new_pax_variable']-totals['saved_old_pax_variable'])
        evidence.append(dict(profile=m.profile,network=net['name'],scenario=sc,journeys=totals['sold_journeys'],
                             segments=totals['segment_pax'],gross_revenue=totals['gross_revenue'],
                             foregone_RW_revenue_once=totals['foregone_RW_revenue'],
                             saved_old_pax_variable_once=totals['saved_old_pax_variable'],contribution=contribution,
                             working_aircraft=len({l['aircraft'] for l in net['legs']}),scenario_flights=len(pinned_caps)))
        counts.update(alternatives_scenarios=1,itineraries=len(pinned_sales),flight_scenario_capacity_rows=len(pinned_caps))
    DETAIL['ciri_captures']=captures
    table(ROOT/'independent_ciri_accounting.csv',evidence)
    return dict(export_matches=matches,**counts,alternative_networks_summed=False,known_RW_migration_shared_cap=True,
                one_through_fare=True,unknown_connecting_migration='SCENARIO_NOT_OBSERVED',
                evidence='independent_ciri_accounting.csv')


def ciri_shared_seats_and_migration_counterexamples():
    review,_=load_ciri()
    m=review.setup('ROUTE_INPUTS_UPPER_100')
    p=dict(m.scenarios['base'],capture_open=1.,capture_transfer=1.,frequency_scale=1.,transfer_fare_factor=.8,
           old_RW_fare_ratio=.75,pax_cost=7.)
    m.scenarios['base']=p
    m.rw=collections.Counter()
    def market(a,b,desired,fare=100.,known=None,oldsegments=1,freq=1):
        k=review.core.pair(a,b)
        q=-math.expm1(-freq)
        r=dict(pair=k,demand_base=desired/q,fare_base=fare,cannibal_base=.25,
               capture_group='open',old_rw_segments=oldsegments)
        if known is not None:r['rw_direct_seats_'+a]=known
        m.markets[k]=r
    m.markets={}
    market('AAA','HHH',60,100,7)
    market('HHH','BBB',20,80,11)
    market('AAA','BBB',90,240,None,2)
    legs=[dict(id='L1',origin='AAA',destination='HHH',block_minutes=60),
          dict(id='L2',origin='HHH',destination='BBB',block_minutes=90)]
    net=dict(name='SHARED_OCCUPIED',legs=legs,itineraries={
        ('AAA','HHH'):[dict(day=1,legs=['L1'],transfer=False)],
        ('HHH','BBB'):[dict(day=1,legs=['L2'],transfer=False)],
        ('AAA','BBB'):[dict(day=1,legs=['L1','L2'],transfer=True)]})
    m.payload=lambda l,sc:dict(capacity={'L1':100,'L2':70}.get(l['id'],100))
    m.flight_cost=lambda l,sc:10.
    evidence=[]
    for priority,expected_transfer in (('local_first',40.),('transfer_first',70.)):
        result,sales,caps=m.evaluate(net,'base',priority=priority,detail=True)
        tr=next(s for s in sales if s['transfer'])
        near(tr['sold_journeys'],expected_transfer)
        near(tr['fare_once'],240*.8)
        near(tr['gross_revenue'],expected_transfer*240*.8)
        for c in caps:
            used=sum(s['sold_journeys'] for s in sales if c['flight_id'] in s['flight_ids'].split(';'))
            near(c['occupied'],used)
            assert used<=c['capacity_scenario']+1e-6
        near(result['segment_pax'],result['sold_journeys']+result['transfer_journeys'])
        evidence.append(dict(case='local_occupancy_transfer_bottleneck',priority=priority,
                            transfer_journeys=tr['sold_journeys'],leg1_occupied=caps[0]['occupied'],leg2_occupied=caps[1]['occupied'],
                            trips=result['sold_journeys'],segments=result['segment_pax'],one_transfer_fare=tr['fare_once']))
    # Two dated offers share ONE old direct capacity budget, each alternative resets it.
    m.markets={}
    market('AAA','BBB',1000,120,12,1,2)
    migration_net=dict(name='MIGRATION_SHARED',legs=[dict(id='D1',origin='AAA',destination='BBB',block_minutes=60),
        dict(id='D2',origin='AAA',destination='BBB',block_minutes=60)],itineraries={
        ('AAA','BBB'):[dict(day=1,legs=['D1'],transfer=False),dict(day=4,legs=['D2'],transfer=False)]})
    repeats=[]
    for _ in range(2):
        r,s,c=m.evaluate(migration_net,'base',detail=True)
        near(r['sold_journeys'],200)
        near(r['migrated_RW_direct'],12)
        near(r['migrated_RW_unverified_connecting'],0)
        near(r['foregone_RW_revenue'],12*120*.75)
        near(r['saved_old_pax_variable'],12*7)
        near(r['contribution_before_base_fleet_opportunity'],200*120-12*120*.75-20-200*7+12*7)
        repeats.append(r['contribution_before_base_fleet_opportunity'])
    near(*repeats)
    evidence.append(dict(case='two_offers_one_migration_cap_repeated_alternatives',trips=200,direct_old_cap=12,
                         lost_revenue_once=1080,saved_old_pax_cost_once=84,contribution_each_alternative=repeats[0]))
    table(ROOT/'independent_ciri_counterexamples.csv',evidence)
    return dict(cases=evidence,nonzero_occupancy_checked=True,unequal_leg_capacities=[100,70],alternative_state_reset=True)


def block_provenance_all_rows():
    review,_=load_ciri()
    models={}
    flights=pinned_rows('ciri/frozen_exports/stage17_flights.csv')
    packaged=pinned_rows('ciri/block_metadata_audit.csv')
    assert len(flights)==len(packaged)==1372
    audits=[];counts=collections.Counter();samples=collections.defaultdict(list)
    for row,supplied in zip(flights,packaged):
        profile=row['profile']
        if profile not in models:models[profile]=review.setup(profile)
        model=models[profile]
        a,b=row['origin'],row['destination']
        # Recompute the distance from pinned coordinates, independent of distance().
        ga,gb=model.geo[a],model.geo[b]
        lat1,lat2=math.radians(ga['lat']),math.radians(gb['lat'])
        dlat=lat2-lat1;dlon=math.radians(gb['lon']-ga['lon'])
        distance=12742*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))
        stress=0
        if profile=='RELAXED_SAME_INPUTS_100':
            override=model.overrides.get('block_minutes',{}).get(a+'-'+b)
            if override is not None:value=override;origin='CORE_OVERRIDE'
            elif (a,b) in model.blocks:value=float(model.blocks[a,b]['minutes']);origin='CORE_BLOCK_TABLE'
            else:value=5*math.ceil((30+distance*1.10/700*60)/5);origin='CORE_COORDINATE_FALLBACK'
        elif (a,b) in model.route_blocks:
            value=float(model.route_blocks[a,b]['max_published_minutes']);origin='ROUTE_DIRECTIONAL_PUBLISHED_PROXY'
        else:
            value=5*math.ceil((30+distance/750*60)/5)
            stress=review.P['unknown_time_stress_minutes'] if profile=='UNKNOWN_TIME_PLUS60_100' else 0
            value+=stress;origin='ROUTE_COORDINATE_FALLBACK'+('_STRESS60' if stress else '')
        expected=math.ceil(value*model.cfg['block_time_factor'])
        actual=model.block(a,b)
        near(actual,expected,0)
        near(row['block_minutes'],expected,0)
        for field in ('original_block_minutes','actual_RouteModel_block','corrected_block_minutes'):
            near(supplied[field],expected,0)
        assert supplied['number_changed']=='False'
        assert row['id']==supplied['flight_id'] and row['network']==supplied['network'] and profile==supplied['profile']
        assert row['block_method']==supplied['original_block_method'] and row['source']==supplied['original_source']
        if profile=='RELAXED_SAME_INPUTS_100':
            assert supplied['metadata_status']=='INHERITED_CORE_MODEL_APPLIES'
        else:assert supplied['metadata_status'].startswith('CORRECTED_METADATA_')
        entry=dict(profile=profile,network=row['network'],flight_id=row['id'],origin=a,destination=b,
                   provenance=origin,stress_minutes=stress,actual_block_minutes=actual,
                   independent_scalar_minutes=expected,saved_block_minutes=float(row['block_minutes']),numeric_change=0)
        audits.append(entry);counts[origin]+=1
        if len(samples[origin])<3 and (a,b) not in {(r['origin'],r['destination']) for r in samples[origin]}:
            samples[origin].append(entry)
    assert sum(v for k,v in counts.items() if k.startswith('CORE'))==300
    assert sum(v for k,v in counts.items() if k.startswith('ROUTE'))==1072
    assert counts['ROUTE_DIRECTIONAL_PUBLISHED_PROXY']==244
    table(ROOT/'independent_MR06.csv',audits)
    js(ROOT/'independent_MR06_examples.json',dict(samples=samples,counts=counts))
    return dict(rows=len(audits),numeric_mismatches=0,metadata_corrections=1072,core_rows_retained=300,
                provenance_counts=counts,sample_pairs_per_provenance={k:len(v) for k,v in samples.items()},
                numerical_flight_time_changes=0,financial_change_run='NOT_RUN_METADATA_ONLY',
                evidence=['independent_MR06.csv','independent_MR06_examples.json'])


def adapter_scope_and_joins():
    status=json.loads(show(PAYLOAD,PREFIX+'proposed_common_view/status.json'))
    assert status['common_comparison_run'] is False
    physical=pinned_rows('proposed_common_view/physical_leg.csv')
    itinerary=pinned_rows('proposed_common_view/itinerary.csv')
    incidence=pinned_rows('proposed_common_view/itinerary_leg.csv')
    allocation=pinned_rows('proposed_common_view/capacity_allocation.csv')
    assert incidence==allocation
    def key(r):return r['model_id'],r['profile'],r['candidate_id'],r['scenario_id'],r['physical_leg_id']
    flights={key(r):r for r in physical}
    assert len(flights)==len(physical)==160
    assert len({r['itinerary_id'] for r in itinerary})==len(itinerary)==224
    consumption=collections.Counter()
    for it in itinerary:
        assert it['period_start']=='2026-12-07' and it['period_end']=='2026-12-13'
        assert it['direction_scope']=='DIRECTED_ENDPOINT_OD'
        links=sorted((r for r in incidence if r['itinerary_id']==it['itinerary_id']),key=lambda r:int(r['sequence']))
        trip=float(it['trips'])
        assert len(links)==(2 if it['transfer']=='True' else 1)
        near(it['segments'],trip*len(links))
        ff=[flights[key(r)] for r in links]
        assert ff[0]['origin']==it['origin'] and ff[-1]['destination']==it['destination']
        for a,b in zip(ff,ff[1:]):
            assert a['destination']==b['origin']
            wait=(dt.datetime.fromisoformat(b['departure_utc'])-dt.datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
            assert 60<=wait<=240
        for link in links:
            near(link['seats'],trip)
            consumption[key(link)]+=trip
    for r in physical:
        near(r['occupied'],consumption[key(r)])
        assert consumption[key(r)]<=float(r['seats'])+1e-6
        assert r['physical_status']=='SCENARIO_CALENDAR_NOT_DISPATCH_CLEARANCE'
    money=pinned_rows('proposed_common_view/money_ledger.csv')
    summaries=pinned_rows('proposed_common_view/evaluation_summary.csv')
    for r in summaries:
        assert r['common_numeric_comparison_allowed']=='False'
        assert r['full_budget']==r['net_new_RW_journeys']==''
        if r['model_id']=='ciri_route_model':
            selected=[x for x in money if (x['model_id'],x['profile'],x['candidate_id'],x['scenario_id'])==
                       (r['model_id'],r['profile'],r['candidate_id'],r['scenario_id'])]
            contribution=sum(float(x['amount_rub'])*int(x['sign_in_contribution']) for x in selected)
            near(r['contribution_before_base_fleet_opportunity'],contribution)
            assert r['resource_envelope_id']=='CIRI_4_WORKING_PLUS_1_RESERVE'
        else:
            assert r['period_start']==r['period_end']==''
            assert r['resource_envelope_id']=='ANASTASIA_9_WORKING_PLUS_1_RESERVE'
            assert r['source_grain']=='ANNUALIZED_SYNTHETIC_SYMMETRIC_WEEK'
    # Ranks describe contribution under EACH mode/scenario only.
    ranks=pinned_rows('conditional_ranks.csv')
    for (mode,sc),rr in itertools.groupby(sorted(ranks,key=lambda r:(r['run_id'],r['scenario_id'])),
                                        key=lambda r:(r['run_id'],r['scenario_id'])):
        rr=list(rr)
        expected=sorted((r for r in pinned_rows('evaluation_summary.csv') if r['run_id']==mode and r['scenario_id']==sc),
                        key=lambda r:-float(r['annual_contribution_before_base_fleet_opportunity_rub']))
        assert [r['candidate_id'] for r in sorted(rr,key=lambda r:int(r['rank']))]==[r['candidate_id'] for r in expected]
        assert all(r['status']=='CONDITIONAL_VARIABLE_CONTRIBUTION_NOT_STRATEGY_RANK' for r in rr)
    definitions=pinned_rows('route_definitions.csv')
    assert all(r['case_route_compliance']=='OPEN_DEFINITION' for r in definitions)
    assert all(r['origin']!='MOW' and r['destination']!='MOW' for r in physical)
    assert any('MOW' in (r['origin'],r['destination']) for r in pinned_rows('ledgers/AUTHOR_REPLAY/base/DIRECT/physical_leg.csv'))
    return dict(physical_rows=160,itinerary_rows=224,evaluation_rows=len(summaries),
                joins='model/profile/network/scenario/physical_leg',COMMON_COMPARISON='NOT_RUN',
                full_budget='NOT_RUN',MOW_to_ZIA_airport_assignment='NOT_RUN_NOT_ASSUMED',
                ranks='CONDITIONAL_VARIABLE_CONTRIBUTION_ONLY',case_8_12_compliance='OPEN_DEFINITION')


def output_manifest():
    artifacts=[]
    for path in sorted(ROOT.iterdir()):
        if not path.is_file() or path.name in ('output_manifest.json','handoff.json'):
            continue
        if path.name.startswith('independent_MR06'):
            grain='frozen stage17 flight x profile x network; branch provenance and scalar/function equality; no time change'
        elif path.name=='source_manifest.json':grain='exact git commit/path bytes and SHA256; no raw/private text'
        elif path.suffix=='.py':grain='independent offline reviewer source and reproduction recipe'
        elif path.name=='independent_selection_trace.csv':grain='scenario x greedy selection step, full-network marginal contribution'
        elif 'counterexamples' in path.name:grain='independent synthetic fixture x policy; not observed demand or sales'
        else:grain='bounded review evidence, verdict, result or instruction; units and scope within artifact'
        data=path.read_bytes()
        artifacts.append(dict(path=path.name,bytes=len(data),sha256=digest(data),grain=grain))
    js(ROOT/'output_manifest.json',dict(input_head=HANDOFF,payload=PAYLOAD,artifacts=artifacts,
        exclusions=['.runtime/','__pycache__/','output_manifest.json (self)','handoff.json (commit receipt)'],
        total_bytes=sum(x['bytes'] for x in artifacts)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', action='store_true')
    args = ap.parse_args()
    RUNTIME.mkdir(exist_ok=True)
    socket.create_connection = deny_network
    socket.socket.connect = deny_network
    if args.stage:
        run_check('pinned_payload_stage', stage)
    assert SNAP.exists(), 'Run with --stage first'
    run_check('all_payload_bytes_and_author_artifact_hashes',snapshot_identity)
    run_check('source_byte_identity_and_projection_receipt', sources)
    run_check('independent_anastasia_author_replay', author_replay)
    # Further independent oracles are registered below as the bounded review proceeds.
    for name, fn in EXTRA_CHECKS:
        run_check(name, fn)
    js(ROOT/'independent_checks.json', dict(input_head=HANDOFF,payload=PAYLOAD,author=AUTHOR,ciri=CIRI,
        author_check_py='NOT_RUN',full_budget_comparison='NOT_RUN_OUTSIDE_SCOPE',
        environment=dict(python=sys.version,numpy=sys.modules['numpy'].__version__,pandas=sys.modules['pandas'].__version__),
        tolerance=dict(default_absolute=1e-6,default_relative=1e-11,large_annual_totals_absolute=1e-4,
                       MR06='exact integer-minute equality'),checks=CHECKS))
    js(ROOT/'source_manifest.json', dict(input_head=HANDOFF,payload=PAYLOAD,source_read_method='git show exact SHA:path',
        inputs=[dict(v,grain=('frozen implementation/input/output at exact path; detailed role in pinned artifact_manifest'
                             if v['commit']==PAYLOAD else 'immutable author input/export or exact handoff')) for v in SOURCES.values()]))
    output_manifest()
    return 1 if any(c['status']=='FAIL' for c in CHECKS) else 0


EXTRA_CHECKS = [('real_D_guard_Q_deltas_and_independent_greedy_selection',shared_market_real_replay),
                ('independent_shared_market_counterexamples',shared_market_counterexamples),
                ('all_anastasia_primary_ledger_rows',anastasia_primary_ledgers),
                ('independent_asymmetric_hub_local_transfer_one_fare',anastasia_asymmetric_hub_counterexample),
                ('independent_ciri_replay_and_primary_accounting',ciri_replay_and_primary_accounting),
                ('ciri_nonzero_occupancy_and_shared_migration_counterexamples',ciri_shared_seats_and_migration_counterexamples),
                ('MR06_actual_functions_and_scalar_provenance_all_1372',block_provenance_all_rows),
                ('common_adapter_joins_units_scope_and_conditional_ranks',adapter_scope_and_joins)]

if __name__ == '__main__':
    raise SystemExit(main())
