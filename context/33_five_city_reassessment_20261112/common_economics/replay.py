#!/usr/bin/env python3
"""Bounded, immutable replay. Writes only beside this script; no training/network.

python3 context/33_five_city_reassessment_20261112/common_economics/replay.py
Runtime uses exact Git blobs and one hash-pinned, read-only external raw CSV.
Temporary runtime is removed on exit. --verify checks delivered artifact hashes.
"""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
PACKAGE = OUT.parent
SHA = 'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6'
RAW_HASH = '2228111a787e39dd158f4025bd4a2158327479ece589c0cbd34b4108c8ce865a'
RAW = Path('/Users/a/.t3/worktrees/case_championship/t3-3ad9d77e-a918da4e879409a8/context/23_night_run_20261110/model_repair/author/data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv')
HUBS = ['UFA', 'PEE', 'CEK', 'TJM', 'GOJ', 'OMS']
ALTS = HUBS + ['DIRECT']
MODES = {'rules500': (500, 500), 'rules0': (0, 0),
         'local0_only': (500, 0), 'od_gate0_only': (0, 500)}
PRODUCTS = {'author8_12': (8, 12), 'start3_6': (3, 6)}
CODE = ['network_model', 'demand_model', 'rules', 'airports_meta']
DATA = [
    'assumptions/' + x + '.csv' for x in [
        'network', 'subsidy_hub_airports', 'siberia_fareast_regions',
        'subsidy_cap_84_103', 'subsidy_special_fare', 'resort_airports',
        'demand', 'range', 'south_west_regions', 'bases', 'longlist_params']
] + ['raw/favt_subsidy_2026.csv'] + [
    'manual/' + x + '.csv' for x in ['rw_routes_now', 'closed_airports', 'airport_names']
] + ['processed/' + x for x in [
    'catchments.csv', 'od_fit.json', 'od_pairs.csv', 'demand_estimates.csv',
    'demand_pairs.csv', 'network_summary.csv', 'network_routes.csv']]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def blob(path):
    return subprocess.check_output(['git', 'show', f'{SHA}:{path}'], cwd=REPO)


def read_csv_bytes(b):
    return list(csv.DictReader(b.decode('utf-8-sig').splitlines()))


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csvout(name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)


def near(x, y, what, tol=1e-5):
    if not math.isclose(x, y, abs_tol=tol, rel_tol=1e-11):
        raise AssertionError((what, x, y))


def independent_money(A, L, carried, compensation=None):
    """Direct scalar reconstruction; deliberately does not call author cost/fare."""
    k = A['route_factor_south'] if L['south'] else A['route_factor']
    bh = A['block_fixed_h'] + L['km'] * k / A['block_speed_kmh']
    flights = 2 * L['freq']
    tons = flights * (bh * A['fuel_t_per_hour'] + A['fuel_t_per_cycle'])
    comp = A['fuel_compensation_rub_per_t'] if compensation is None else compensation
    fixed = tons * (A['fuel_rub_per_t'] - comp)
    fixed += flights * (bh * sum(A[k] for k in [
        'mro_rub_per_hour', 'crew_rub_per_hour', 'navigation_rub_per_hour'])
        + A['ground_rub_per_flight'] + A['deicing_rub_per_flight'])
    cost = fixed + 2 * carried * A['pax_cost_rub']
    fare = A['fare_fixed_rub'] + A['fare_per_km_rub'] * L['km']
    return bh, tons, cost, fare, fixed


def normalize(nm, D, A, scen, alt, choice, mode, product, cap, purpose):
    W = A['weeks_per_year']
    if alt == 'DIRECT':
        programs = choice
        legs = [dict(L, program='-'.join(c[1:4])) for c in choice for L in c[8]]
        trans = []
        hours, cost, rev, seg = (sum(c[i] for c in choice) for i in [4, 5, 6, 7])
        local, transfer = seg, 0
        flights = sum(2 * L['freq'] for L in legs)
        migr, forgone = (sum(c[i] for c in choice) for i in [9, 10])
        n = len(programs)
        names = ['-'.join(c[1:4]) for c in programs]
    else:
        chosen, r = choice
        rawlegs, trans, hours, cost, rev, local, transfer, flights, migr, forgone, subs = r
        assert subs == 0
        legs = [dict(L, program=f'{alt}-{X}') for X, L in rawlegs.items()]
        seg = sum(2 * L['carried_dir_week'] for L in legs)
        n = len(chosen)
        names = [f'{alt}-{x}' for x in chosen]
    ident = f'{purpose}:{scen}:{alt}:{mode}:{product}:cap{cap}'
    for L in legs:
        if alt == 'DIRECT':
            L['local_carried'] = L['carried_dir_week']
            L['transfer_carried'] = 0
        assert L['a'] not in nm.CLOSED and L['b'] not in nm.CLOSED
        assert L['km'] <= D.green(L['a'], L['b']) + 1e-9
        assert A['min_freq_week'] <= L['freq'] <= (A['direct_max_freq_week'] if alt == 'DIRECT' else A['max_freq_week'])
        assert 0 <= L['carried_dir_week'] <= A['seats'] * A['lf_max'] * L['freq'] + 1e-7
        bh, tons, cc, ff, fixed = independent_money(A, L, L['carried_dir_week'])
        near(bh, L['block_h'], 'block hours')
        near(cc, L['cost_week'], 'independent flight costs')
        near(L['local_carried'] + L['transfer_carried'], L['carried_dir_week'], 'leg membership')
    near(seg, local + 2 * transfer, 'segments=local+2transfer')
    near(hours, sum(2 * L['freq'] * L['block_h'] for L in legs), 'resource sum')
    near(cost, sum(L['cost_week'] for L in legs), 'cost sum')
    near(rev, sum(L['rev_week'] for L in legs), 'revenue sum')
    tfare = lambda km: A['fare_fixed_rub'] + A['fare_per_km_rub'] * km
    tr_rev = sum(2 * t * tfare(km) * A['transfer_fare_factor'] for x, y, km, t in trans)
    grosslocal = sum(2 * L['local_carried'] * tfare(L['km']) for L in legs)
    near(rev, grosslocal + tr_rev - forgone, 'full through revenue, once per transfer OD')
    near(transfer, sum(2 * t for x, y, km, t in trans), 'transfer pairs sum')
    pairlegs = collections.defaultdict(list)
    for L in legs:
        pairlegs[tuple(sorted((L['a'], L['b'])))].append(L)
    # Physical OD pooling check independent of author joint(), for DIRECT.
    if alt == 'DIRECT':
        for pair, members in pairlegs.items():
            L = members[0]
            F = sum(l['freq'] for l in members)
            if L['km'] < MODES[mode][1]:
                share = 0
            elif L['competitive']:
                fc = L['seg'] / (A['seats'] * A['competitor_lf'])
                share = min(A['capture_competitive'], F / (F + fc)) if fc > 0 else 0
            else:
                share = A['capture_open'] * (1 - math.exp(-F / A['capture_freq_scale']))
            carried = min(L['dem'] * share, F * A['seats'] * A['lf_max'])
            near(carried, sum(l['carried_dir_week'] for l in members), 'direct pooled OD')
            for l in members:
                near(l['carried_dir_week'], carried * l['freq'] / F, 'direct allocation')
    else:
        seen = set()
        byr = {L['b']: L for L in legs}
        trload = collections.Counter()
        for x, y, km, t in trans:
            assert x in byr and y in byr and x != y
            p = tuple(sorted((x, y)))
            assert p not in seen
            seen.add(p)
            assert not D.has_direct(x, y)
            assert km >= MODES[mode][0] - 1e-9
            assert (D.km(alt, x) + D.km(alt, y)) / km <= A['transfer_max_circuity'] + 1e-9
            assert 2 * t * W <= D.get(x, y, scen) + 1e-7
            trload[x] += t
            trload[y] += t
        for L in legs:
            near(L['transfer_carried'], trload[L['b']], 'transfer membership on each leg')
            assert 2 * L['local_carried'] * W <= D.get(alt, L['b'], scen) + 1e-7
    countmin, countmax = PRODUCTS[product]
    used = math.ceil(hours / (A['block_h_per_day'] * 7) - 1e-12) + int(A['spare_aircraft'])
    assert used <= cap
    tons = sum(independent_money(A, L, L['carried_dir_week'])[1] for L in legs)
    row = dict(network_id=ident, purpose=purpose, demand_scenario=scen, alternative=alt,
               mode=mode, product=product, construction_cap=cap,
               status='ok' if countmin <= n <= countmax else 'not_feasible_min_routes',
               program_grain='triangle' if alt == 'DIRECT' else 'hub_spoke',
               programs=n, unique_undirected_legs=len(pairlegs), leg_occurrences=len(legs),
               aircraft_including_one_spare=used, spare_aircraft=1,
               resource_limit_block_h_week=(cap - 1) * A['block_h_per_day'] * 7,
               block_h_week=hours, flights_week=flights,
               seat_legs_year=flights * A['seats'] * W, weeks_per_year=W,
               segments_year=seg * W, local_od_year=local * W,
               transfer_od_year=transfer * W, od_year=(local + transfer) * W,
               transfer_share_of_od=transfer / (local + transfer) if local + transfer else 0,
               transfer_share_of_segments=2 * transfer / seg if seg else 0,
               gross_local_revenue_rub_year=grosslocal * W,
               full_transfer_revenue_rub_year=tr_rev * W,
               forgone_rw_revenue_rub_year=forgone * W, rw_migrated_od_year=migr * W,
               net_revenue_rub_year=rev * W, variable_cost_rub_year=cost * W,
               contribution_rub_year=(rev - cost) * W, fuel_t_year=tons * W,
               omitted_fixed_cost_rub_year=None, full_profit_rub_year=None,
               program_list=';'.join(names))
    return dict(row=row, legs=legs, transfers=trans, A=dict(A))


def baseline_check(net, saved, routes):
    r = net['row']
    pub = next(x for x in saved if x['scenario'] == r['demand_scenario'] and (x['hub'] or 'DIRECT') == r['alternative'])
    fields = {
        'routes': r['programs'], 'aircraft': r['aircraft_including_one_spare'],
        'flights_week': r['flights_week'], 'segments_year': round(r['segments_year']),
        'od_trips_year': round(r['od_year']), 'transfer_od_year': round(r['transfer_od_year']),
        'revenue_mln_year': round(r['net_revenue_rub_year'] / 1e6),
        'var_cost_mln_year': round(r['variable_cost_rub_year'] / 1e6),
        'result_mln_year': round(r['contribution_rub_year'] / 1e6),
        'rw_migrated_year': round(r['rw_migrated_od_year']),
        'rw_forgone_mln_year': round(r['forgone_rw_revenue_rub_year'] / 1e6),
    }
    for k, v in fields.items():
        near(v, float(pub[k]), f'published baseline {r["alternative"]}:{k}', tol=1e-9)
    W = r['weeks_per_year']
    pubs = [x for x in routes if x['scenario'] == r['demand_scenario'] and (
        x['variant'].startswith('Прямые ') if r['alternative'] == 'DIRECT' else x['variant'] == 'Хаб ' + r['alternative'])]
    assert len(pubs) == len(net['legs'])
    for L in net['legs']:
        variant = 'Прямые ' + L['program'] if r['alternative'] == 'DIRECT' else 'Хаб ' + r['alternative']
        x = next(x for x in pubs if x['from'] == L['a'] and x['to'] == L['b'] and x['variant'] == variant)
        for k, v in {'freq_week_each_way': L['freq'], 'pax_year_segments': round(2 * L['carried_dir_week'] * W),
                     'revenue_mln_year': round(L['rev_week'] * W / 1e6, 1),
                     'cost_mln_year': round(L['cost_week'] * W / 1e6, 1),
                     'result_mln_year': round((L['rev_week'] - L['cost_week']) * W / 1e6, 1)}.items():
            near(v, float(x[k]), 'published route ' + k, tol=1e-8)
    return dict(network_id=r['network_id'], summary_fields=len(fields),
                route_rows=len(pubs), route_fields_per_row=5, pass_all=True)


def stress(net, compensation, transfer_keep):
    """Freeze legs, frequencies and served local OD. Remove transfer OD with no resale."""
    r, A, legs = net['row'], net['A'], net['legs']
    W = A['weeks_per_year']
    cost = tons = hours = seg = 0.0
    for L in legs:
        p = L['local_carried'] + L['transfer_carried'] * transfer_keep
        bh, t, c, fare, fixed = independent_money(A, L, p, compensation)
        cost += c * W
        tons += t * W
        hours += 2 * L['freq'] * bh
        seg += 2 * p * W
        assert p <= L['freq'] * A['seats'] * A['lf_max'] + 1e-7
    od_transfer = r['transfer_od_year'] * transfer_keep
    rev_transfer = r['full_transfer_revenue_rub_year'] * transfer_keep
    rev = r['gross_local_revenue_rub_year'] + rev_transfer - r['forgone_rw_revenue_rub_year']
    near(seg, r['local_od_year'] + 2 * od_transfer, 'stress OD identity')
    near(hours, r['block_h_week'], 'stress fixed resource')
    expected = (r['contribution_rub_year']
        + r['fuel_t_year'] * (compensation - A['fuel_compensation_rub_per_t'])
        - (1 - transfer_keep) * (r['full_transfer_revenue_rub_year']
            - 2 * r['transfer_od_year'] * A['pax_cost_rub']))
    near(rev - cost, expected, 'stress difference identity')
    return dict(network_id=r['network_id'], demand_scenario=r['demand_scenario'],
        alternative=r['alternative'], mode=r['mode'], product=r['product'],
        fuel_compensation_rub_per_t=compensation, transfer_keep_fraction=transfer_keep,
        scenario_meaning='fixed_schedule_cost_only' if transfer_keep == 1 else 'fixed_schedule_no_resale',
        contribution_rub_year=rev-cost, net_revenue_rub_year=rev,
        variable_cost_rub_year=cost, full_transfer_revenue_rub_year=rev_transfer,
        local_od_year=r['local_od_year'], transfer_od_year=od_transfer, segments_year=seg,
        block_h_week=hours, flights_week=r['flights_week'], fuel_t_year=tons,
        schedules_frozen=True, capacity_pass=True, identity_pass=True,
        joint_adverse=(compensation == 0 and transfer_keep == 0))


def threshold_rows(comparisons):
    out = []
    groups = collections.defaultdict(list)
    for r in comparisons:
        if r['status'] == 'ok':
            groups[tuple(r[k] for k in ['demand_scenario','mode','product','budget_aircraft'])].append(r)
    for key, rs in groups.items():
        for i, j in itertools.combinations(rs, 2):
            gap = i['contribution_rub_year'] - j['contribution_rub_year']
            dh = (i['block_h_week'] - j['block_h_week']) * i['weeks_per_year']
            out.append(dict(demand_scenario=key[0], mode=key[1], product=key[2], budget_aircraft=key[3],
                i=i['alternative'], j=j['alternative'], network_i=i['selected_network_id'], network_j=j['selected_network_id'],
                contribution_i_minus_j_rub_year=gap,
                fixed_cost_difference_threshold_rub_year=gap,
                common_extra_hour_cost_equality_rub_h=gap/dh if abs(dh)>1e-9 else None,
                annual_block_hours_i_minus_j=dh,
                interpretation='i beats j iff F_i-F_j < gap; with extra common hourly cost k: gap-k*delta_hours > F_i-F_j'))
    return out


def run(raw):
    start = time.monotonic()
    import numpy as np
    import pandas as pd
    import scipy
    # Validate shared inputs; never edit or silently replace them.
    pinned_inputs = json.loads((PACKAGE / 'input_manifest.json').read_text())
    for x in pinned_inputs:
        b = (PACKAGE / x['path']).read_bytes()
        assert sha(b) == x['sha256'] and len(b) == x['bytes'], x['path']
    if not raw.is_file():
        raise FileNotFoundError(f'BLOCKED_RAW_MISSING: {raw}; required SHA256 {RAW_HASH}; no fallback permitted')
    rawbytes = raw.read_bytes()
    assert sha(rawbytes) == RAW_HASH, 'BLOCKED_RAW_HASH_MISMATCH'
    manifest = dict(subject=SHA, raw_path=str(raw), raw_sha256=RAW_HASH,
        no_training=True, all_cities_included=HUBS,
        input_manifest_sha256=sha((PACKAGE/'input_manifest.json').read_bytes()),
        shared_inputs_verified=len(pinned_inputs), python=platform.python_version(),
        numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__, runtime_files=[])
    manifest['preflight'] = subprocess.check_output(['/Users/a/bin/dev-job','preflight'], text=True).strip()
    with tempfile.TemporaryDirectory(prefix='.runtime-', dir=OUT) as tmp:
        root = Path(tmp)
        for p in ['src/' + x + '.py' for x in CODE] + ['data/' + x for x in DATA]:
            b = blob(p)
            f = root / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b)
            manifest['runtime_files'].append(dict(path=p,sha256=sha(b),bytes=len(b),exact_git_blob=True))
        f = root / 'data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv'
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(rawbytes)
        manifest['runtime_files'].append(dict(path=f.relative_to(root).as_posix(),sha256=sha(rawbytes),bytes=len(rawbytes),exact_git_blob=False))
        dump('runtime_manifest.json', manifest)
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(root / 'src'))
        import network_model as nm
        D, AS = nm.Demand(), nm.load_assumptions()
        nodes = list(D.n.index)
        original_share = nm.leg_share
        cache, allnets, bases, basechecks = {}, {}, [], []
        saved, savedroutes = (read_csv_bytes(blob('data/processed/' + p)) for p in ['network_summary.csv','network_routes.csv'])

        def candidate(scen, alt, mode, product, cap):
            key = (scen, alt, mode, product, cap)
            if key in cache:
                return cache[key]
            gate, local = MODES[mode]
            A = dict(AS[scen], fleet_cap=cap, transfer_min_km=gate,
                     min_routes=PRODUCTS[product][0], max_routes=PRODUCTS[product][1])
            # Main rules500/rules0 branches use unmodified author function.
            nm.leg_share = original_share if gate == local else lambda L, f, aa: original_share(L, f, dict(aa, transfer_min_km=local))
            t = time.monotonic()
            try:
                ch = nm.direct_network(D, A, scen, nodes) if alt == 'DIRECT' else nm.hub_network(alt, D, A, scen, nodes)
                net = normalize(nm,D,A,scen,alt,ch,mode,product,cap,'candidate')
                net['row']['elapsed_seconds'] = time.monotonic()-t
            except ValueError as e:
                if str(e) != 'Нет допустимой сети при заданном ресурсе':
                    raise
                net = dict(row=dict(network_id=':'.join(map(str,key)),status='not_feasible_no_candidate',
                    demand_scenario=scen, alternative=alt, mode=mode, product=product, construction_cap=cap,
                    diagnostic=str(e)))
            finally:
                nm.leg_share = original_share
            cache[key] = net
            allnets[net['row']['network_id']] = net
            return net

        # Exactly the author's caps and best_of rule, independently aggregated.
        for scen in ['base','cautious']:
            for alt in ALTS:
                ns = [candidate(scen,alt,'rules500','author8_12',c) for c in nm.search_caps(AS[scen])]
                valid = [n for n in ns if n['row']['status'] == 'ok']
                chosen = max(valid or ns, key=lambda n:(n['row']['contribution_rub_year'],-n['row']['block_h_week']))
                bases.append(dict(chosen['row'],purpose='published_baseline'))
                basechecks.append(baseline_check(chosen,saved,savedroutes))
                print('BASELINE',scen,alt,round(chosen['row']['contribution_rub_year']/1e6,3),'PASS',flush=True)
                csvout('baseline.csv',bases)
        dump('baseline_checks.json',basechecks)
        comparisons = []
        for scen in ['base','cautious']:
            for product in PRODUCTS:
                modes = list(MODES) if product == 'author8_12' else ['rules500','rules0']
                for mode in modes:
                    for alt in ALTS:
                        ns = []
                        for cap in range(2,8):
                            ns.append(candidate(scen,alt,mode,product,cap))
                            valid = [n for n in ns if n['row']['status'] == 'ok']
                            if valid:
                                best = max(valid, key=lambda n:(n['row']['contribution_rub_year'],-n['row']['block_h_week']))
                                r = dict(best['row'],budget_aircraft=cap,selected_network_id=best['row']['network_id'])
                            else:
                                r = dict(demand_scenario=scen,alternative=alt,mode=mode,product=product,
                                    budget_aircraft=cap,status='not_feasible_min_routes_in_constructed_candidates',
                                    selected_network_id=None,contribution_rub_year=None,
                                    largest_constructed_programs=max(n['row'].get('programs',0) for n in ns))
                            comparisons.append(r)
                        print('GRID',scen,product,mode,alt,'done',len(cache),'elapsed',round(time.monotonic()-start,1),flush=True)
                        csvout('comparison.csv',comparisons)
        # Keep the raw controlled-cap search visible. A changed greedy path must
        # not erase a previously constructed feasible network. Re-evaluate every
        # distinct program set from the four rule branches using the SAME author
        # fixed-selection API under each main branch; do not borrow its economics.
        csvout('comparison_greedy.csv', comparisons)
        retained, seen = [], set()
        original_nets = list(allnets.values())
        for source in original_nets:
            if 'legs' not in source or source['row']['status'] != 'ok':
                continue
            sr = source['row']
            scen, alt, product = (sr[k] for k in ['demand_scenario','alternative','product'])
            for mode in ['rules500','rules0']:
                if alt == 'DIRECT':
                    # fixed_selection bypasses the author's initial candidate
                    # filter: explicitly validate the central OD gate ourselves.
                    programs=collections.defaultdict(list)
                    for L in source['legs']:
                        programs[L['program']].append(L)
                    if any(D.km(*name.split('-')[1:]) < MODES[mode][0] for name in programs):
                        continue
                    signature=tuple(sorted((name,tuple(L['freq'] for L in ls)) for name,ls in programs.items()))
                else:
                    signature=tuple(sorted(L['b'] for L in source['legs']))
                key=(scen,alt,product,mode,signature)
                if key in seen:
                    continue
                seen.add(key)
                A=dict(source['A'],transfer_min_km=MODES[mode][0])
                nm.leg_share=original_share
                if alt == 'DIRECT':
                    pseudo=[]
                    for name,ls in programs.items():
                        B,X,Y=name.split('-')
                        pseudo.append((0,B,X,Y,0,0,0,0,ls))
                    ch=nm.direct_network(D,A,scen,nodes,fixed_selection=pseudo)
                    hours=sum(c[4] for c in ch)
                else:
                    ch=nm.hub_network(alt,D,A,scen,nodes,fixed_spokes=list(signature))
                    hours=ch[1][2]
                cap=math.ceil(hours/(A['block_h_per_day']*7)-1e-12)+1
                A['fleet_cap']=cap
                n=normalize(nm,D,A,scen,alt,ch,mode,product,cap,'retained'+str(len(retained)+1))
                n['row']['source_network_id']=sr['network_id']
                n['row']['evaluation_method']='author_fixed_spokes_recompute_frequency' if alt!='DIRECT' else 'author_fixed_triangles_and_frequency'
                ident=n['row']['network_id']
                allnets[ident]=n
                retained.append(n['row'])
        csvout('retained_network_bounds.csv',retained)
        for index, row in enumerate(comparisons):
            if row['mode'] not in ['rules500','rules0']:
                continue
            possible=[n for n in allnets.values() if n['row']['status']=='ok' and all(
                n['row'][k]==row[k] for k in ['demand_scenario','alternative','mode','product'])
                and n['row']['aircraft_including_one_spare']<=row['budget_aircraft']]
            if possible:
                best=max(possible,key=lambda n:(n['row']['contribution_rub_year'],-n['row']['block_h_week']))
                comparisons[index]=dict(best['row'],budget_aircraft=row['budget_aircraft'],
                    selected_network_id=best['row']['network_id'],selection_pool='controlled_caps_plus_retained_program_sets')
        csvout('comparison.csv',comparisons)
        # Dump every construction, not only survivors, for feasibility audit.
        csvout('candidates.csv',[n['row'] for n in allnets.values()])
        legsrows, odrows, physicalrows, samples = [], [], [], []
        for ident,n in allnets.items():
            if 'legs' not in n:
                continue
            r,A = n['row'],n['A']
            W = A['weeks_per_year']
            groups = collections.defaultdict(list)
            for L in n['legs']:
                lr = dict(network_id=ident,program=L['program'],a=L['a'],b=L['b'],km=L['km'],
                    frequency_week_each_way=L['freq'],flights_week=2*L['freq'],block_h_oneway=L['block_h'],
                    block_h_week=2*L['freq']*L['block_h'],
                    local_od_year=2*L['local_carried']*W,transfer_segments_year=2*L['transfer_carried']*W,
                    segments_year=2*L['carried_dir_week']*W,seat_legs_year=2*L['freq']*A['seats']*W,
                    lf=L['lf'],net_revenue_rub_year=L['rev_week']*W,
                    variable_cost_rub_year=L['cost_week']*W,contribution_rub_year=(L['rev_week']-L['cost_week'])*W,
                    rw_migrated_od_year=2*L['migrated']*W,
                    direct_now=L['competitive'],demand_source=D.method(L['a'],L['b']))
                legsrows.append(lr)
                groups[tuple(sorted((L['a'],L['b'])))].append(lr)
                if len(samples)<14 or (r['construction_cap']==5 and r['mode']=='rules0' and r['product']=='start3_6' and len(samples)<40):
                    bh,tons,cost,fare,fixed=independent_money(A,L,L['carried_dir_week'])
                    samples.append(dict(network_id=ident,a=L['a'],b=L['b'],km=L['km'],frequency=L['freq'],
                        author_cost_week=L['cost_week'],independent_cost_week=cost,block_h=bh,fuel_t_week=tons,
                        fare_rub=fare,pax_variable_rub_week=2*L['carried_dir_week']*A['pax_cost_rub'],
                        other_variable_rub_week=fixed,pass_check=True))
            for pair,ls in groups.items():
                physicalrows.append(dict(network_id=ident,a=pair[0],b=pair[1],program_members=len(ls),
                    aggregate_frequency_week_each_way=sum(l['frequency_week_each_way'] for l in ls),
                    flights_week=sum(l['flights_week'] for l in ls),
                    block_h_week=sum(l['block_h_week'] for l in ls),
                    segments_year=sum(l['segments_year'] for l in ls)))
                fare = A['fare_fixed_rub'] + A['fare_per_km_rub'] * ls[0]['km']
                local = sum(l['local_od_year'] for l in ls)
                mig = sum(l['rw_migrated_od_year'] for l in ls)
                odrows.append(dict(network_id=ident,kind='local',a=pair[0],b=pair[1],via=None,
                    od_year=local,segments_per_od=1,full_fare_rub=fare,full_revenue_rub_year=local*fare,
                    passenger_variable_rub_year=local*A['pax_cost_rub'],rw_migrated_od_year=mig,
                    current_rw_forgone_rub_year=mig*fare,
                    unit_contribution_before_schedule_cost_rub=fare-A['pax_cost_rub'],
                    additional_rw_diversion_loss_per_od_rub=fare))
            for x,y,km,t in n['transfers']:
                q = 2*t*W
                fare = (A['fare_fixed_rub']+A['fare_per_km_rub']*km)*A['transfer_fare_factor']
                odrows.append(dict(network_id=ident,kind='transfer',a=x,b=y,via=r['alternative'],
                    od_year=q,segments_per_od=2,full_fare_rub=fare,full_revenue_rub_year=q*fare,
                    passenger_variable_rub_year=q*2*A['pax_cost_rub'],rw_migrated_od_year=0,
                    current_rw_forgone_rub_year=0,
                    unit_contribution_before_schedule_cost_rub=fare-2*A['pax_cost_rub'],
                    additional_rw_diversion_loss_per_od_rub=fare))
        csvout('network_legs.csv',legsrows)
        csvout('physical_legs.csv',physicalrows)
        csvout('od_flows.csv',odrows)
        csvout('independent_arithmetic_samples.csv',samples)
        selected = set(r['selected_network_id'] for r in comparisons if r['status']=='ok')
        selected.update(r['network_id'] for r in bases)
        stressrows=[]
        robustness=[]
        for ident in sorted(selected):
            n=allnets[ident]
            r,A=n['row'],n['A']
            for comp,keep in itertools.product([32930,3024,0],[1,0.5,0]):
                stressrows.append(stress(n,comp,keep))
            marginal = r['full_transfer_revenue_rub_year']-2*r['transfer_od_year']*A['pax_cost_rub']
            robustness.append(dict(network_id=ident,
                contribution_rub_year=r['contribution_rub_year'],
                maximum_omitted_additions_for_zero_rub_year=r['contribution_rub_year'],
                extra_hour_cost_for_zero_rub_h=r['contribution_rub_year']/(r['block_h_week']*r['weeks_per_year']),
                full_transfer_marginal_rub_year=marginal,
                transfer_keep_fraction_for_zero=1-r['contribution_rub_year']/marginal if marginal>0 else None,
                fuel_compensation_for_zero_rub_t=A['fuel_compensation_rub_per_t']-r['contribution_rub_year']/r['fuel_t_year'],
                local_lost_od_fraction_for_zero=r['contribution_rub_year']/(r['gross_local_revenue_rub_year']-r['local_od_year']*A['pax_cost_rub']) if r['local_od_year'] else None,
                additional_rw_diversion_local_fraction_for_zero=r['contribution_rub_year']/r['gross_local_revenue_rub_year'] if r['gross_local_revenue_rub_year'] else None,
                interpretation='thresholds conditional on fixed schedules; negative zero-threshold means already below zero; fractions outside [0,1] not an admissible reduction; fixed cost remains unknown'))
        csvout('fixed_schedule_stress.csv',stressrows)
        csvout('absolute_thresholds.csv',robustness)
        csvout('pairwise_thresholds.csv',threshold_rows(comparisons))
        # Explicit observed-envelope rankings, with KEEP=0 kept separate.
        leaders=[]
        for scen,mode,product,budget in itertools.product(['base','cautious'],MODES,PRODUCTS,range(2,8)):
            rows=[r for r in comparisons if r['demand_scenario']==scen and r['mode']==mode and r['product']==product and r['budget_aircraft']==budget and r['status']=='ok']
            if not rows:
                continue
            rs=sorted(rows,key=lambda r:-r['contribution_rub_year'])
            leaders.append(dict(demand_scenario=scen,mode=mode,product=product,budget_aircraft=budget,
                observed_best=rs[0]['alternative'],best_contribution_rub_year=rs[0]['contribution_rub_year'],
                runner_up=rs[1]['alternative'] if len(rs)>1 else None,
                best_minus_runner_rub_year=rs[0]['contribution_rub_year']-rs[1]['contribution_rub_year'] if len(rs)>1 else None,
                positive_before_unknown_fixed_cost=rs[0]['contribution_rub_year']>0,
                keep_no_new_program_contribution_rub_year=0,
                status='observed_constructed_envelope_not_global_optimum'))
        csvout('leaders.csv',leaders)
        checks=dict(subject=SHA,status='PASS',published_baselines=len(basechecks),
            published_summary_numeric_cells=sum(x['summary_fields'] for x in basechecks),
            published_route_rows=sum(x['route_rows'] for x in basechecks),
            constructed_networks=len(cache),networks_with_legs=sum('legs' in n for n in allnets.values()),
            retained_program_set_evaluations=len(retained),
            comparison_rows=len(comparisons),fixed_schedules_stressed=len(selected),stress_rows=len(stressrows),
            all_networks_independent_cost_reconstruction=True,all_networks_segment_identity=True,
            all_networks_capacity_resource_od_membership_checked=True,
            direct_physical_od_pooling_checked=True,baseline_route_precision_checked=True,
            main_distance_branches_original_code=True,no_demand_refit=True,
            temporary_runtime_removed_on_exit=True,elapsed_seconds=time.monotonic()-start,
            not_run=['calendar_connections_and_tail_crew_plan','legal_fuel_payment_entitlement',
                     '2027_2028_actual_deliveries_and_service_entry','market_capture_and_fares_validation',
                     'full_incremental_base_lease_cash_costs','joint_hub_plus_direct_shared_market_program',
                     'reoptimization_under_stress','global_optimum_proof'])
        dump('checks.json',checks)
    print('COMPLETE',json.dumps(checks),flush=True)


def manifest():
    files=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name != 'artifact_manifest.json':
            b=p.read_bytes()
            files.append(dict(path=p.name,sha256=sha(b),bytes=len(b)))
    dump('artifact_manifest.json',dict(subject=SHA,files=files))


def verify():
    m=json.loads((OUT/'artifact_manifest.json').read_text())
    for x in m['files']:
        p=OUT/x['path']
        assert sha(p.read_bytes())==x['sha256'] and p.stat().st_size==x['bytes'],p
    print('PASS_ARTIFACT_HASHES',len(m['files']))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-connectivity',type=Path,default=RAW)
    ap.add_argument('--verify',action='store_true')
    ap.add_argument('--manifest-only',action='store_true')
    args=ap.parse_args()
    if args.verify:
        verify()
    elif args.manifest_only:
        manifest()
    else:
        run(args.raw_connectivity)
        manifest()
