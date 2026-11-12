#!/usr/bin/env python3
"""Audit dceadc9 without changing the author model. See --help for replay inputs."""
import argparse
import copy
import csv
import hashlib
import itertools
import json
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SHA = "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6"
OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]


def blob(path):
    return subprocess.check_output(["git", "show", f"{SHA}:{path}"], cwd=REPO)


def rows(path):
    return list(csv.DictReader(blob(path).decode("utf-8-sig").splitlines()))


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_csv(name, data):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)


def screening():
    source = json.loads(blob("data/processed/criteria.json"))
    crit, vals = source["criteria"], source["values"]
    cities = rows("data/processed/longlist.csv")
    scales = {}
    for c in crit:
        xs = [v for cell in vals.values() for v in
              (cell.get(c['key'], {}).get('v'), cell.get(c['key'], {}).get('lo'),
               cell.get(c['key'], {}).get('hi')) if v is not None]
        scales[c['key']] = (c['lo'] if c.get('lo') is not None else min(xs),
                            c['hi'] if c.get('hi') is not None else max(xs))

    def utility(x, c):
        lo, hi = scales[c['key']]
        if x is None or hi <= lo:
            return .5
        z = min(1, max(0, (x-lo)/(hi-lo)))
        return 1-z if c['dir'] == '-' else z

    score_rows, matrix = [], {}
    for r in cities:
        i = r['iata']
        z = {c['key']: utility(vals[i].get(c['key'], {}).get('v')
             if vals[i].get(c['key'], {}).get('v') is not None else c.get('fill'), c) for c in crit}
        matrix[i] = z
        s = sum(c['weight'] * z[c['key']] for c in crit) / sum(c['weight'] for c in crit)
        score_rows.append({'iata': i, 'city': r['city'], 'score': s,
                           'distance_to_bases_km': min(float(r['dist_msk_km']), float(r['dist_ekb_km']))})
    ordered = sorted(score_rows, key=lambda r: -r['score'])
    saved = {r['iata']: r for r in rows('data/processed/longlist_scores.csv')}
    checks = [{'name': 'independent weighted scores agree with author rounded exports',
               'pass': all(round(r['score'], 3) == float(saved[r['iata']]['score']) for r in ordered)},
              {'name': 'independent rank agrees with author export',
               'pass': all(n == int(saved[r['iata']]['rank']) for n, r in enumerate(ordered, 1))}]
    scenarios=[]
    for threshold in [0, 166, 167, 250, 300, 350, 380, 400, 500, 650, 800]:
        admitted = [r for r in ordered if r['distance_to_bases_km'] >= threshold]
        scenarios.append({'threshold_km': threshold, 'n_cities': len(admitted),
                          'top3': [r['city'] for r in admitted[:3]],
                          'omsk_rank': next((n for n, r in enumerate(admitted, 1) if r['iata']=='OMS'), None)})
    for n,r in enumerate(ordered,1):
        r['rank_without_filter']=n
        r['rank_500']=next((k for k,q in enumerate([s for s in ordered if s['distance_to_bases_km']>=500],1) if q['iata']==r['iata']),None)
    ablations=[]
    for drop in [[],['last365_days'],['bad_weather_days'],['transfer_demand_base'],['gap_pop']]:
        w = {c['key']: c['weight'] if c['key'] not in drop else 0 for c in crit}
        ranked = sorted(cities, key=lambda r: -sum(w[k]*matrix[r['iata']][k] for k in w)/sum(w.values()))
        for threshold in [0,500]:
            allowed=[r for r in ranked if min(float(r['dist_msk_km']),float(r['dist_ekb_km']))>=threshold]
            ablations.append({'removed_weights':drop,'threshold_km':threshold,'top3':[r['city'] for r in allowed[:3]]})
    economics = rows('data/processed/network_summary.csv')
    comparisons=[]
    for s in ['base','cautious']:
        for r in sorted([r for r in economics if r['scenario']==s and r['hub']], key=lambda r:-float(r['result_mln_year'])):
            m=next(x for x in ordered if x['iata']==r['hub'])
            comparisons.append({'scenario':s, 'city':m['city'], 'iata':r['hub'], 'passes_500':m['distance_to_bases_km']>=500,
                                'aircraft':int(r['aircraft']), 'routes':int(r['routes']),
                                'segments_year':int(r['segments_year']), 'result_mln_year':float(r['result_mln_year']),
                                'status':'author_saved_output_not_independent_full_replay'})
    dump('screening.json', {'subject':SHA,'scenarios':scenarios,'ablation':ablations,'checks':checks})
    write_csv('screening_scores.csv',ordered)
    write_csv('network_saved_comparison.csv',comparisons)
    assert all(c['pass'] for c in checks)
    print(json.dumps(scenarios,ensure_ascii=False),flush=True)


def network(runtime, reselect):
    # Runtime consists solely of exact Git blobs and the separately hashed raw connectivity input.
    sys.path.insert(0, str(runtime/'src'))
    import network_model as nm
    import pandas as pd
    used=[]
    for p in sorted(runtime.rglob('*')):
        if not p.is_file() or p.suffix not in ['.py','.csv','.json'] or '__pycache__' in p.parts:
            continue
        rel=p.relative_to(runtime).as_posix()
        if not rel.startswith(('src/','data/')):continue
        b=p.read_bytes()
        tracked=subprocess.run(['git','cat-file','-e',f'{SHA}:{rel}'],cwd=REPO,capture_output=True).returncode==0
        if tracked:
            assert b==blob(rel),rel
        used.append({'path':rel,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'exact_git_blob':tracked})
    raw=[r for r in used if not r['exact_git_blob']]
    assert len(raw)==1 and raw[0]['sha256']=='2228111a787e39dd158f4025bd4a2158327479ece589c0cbd34b4108c8ce865a'
    dump('runtime_manifest.json', {'subject':SHA,'raw_note':'Raw Tochno v20260629 input recovered from preserved model_repair snapshot. Not tracked at author commit. No new download; hash pinned independently of current model blobs.','files':used})
    D=nm.Demand(); AS=nm.load_assumptions(); A=AS['base']; nodes=list(D.n.index)
    hubs=[r['iata'] for r in rows('data/processed/longlist.csv')]
    routes=rows('data/processed/network_routes.csv')
    gate=[]
    for H in hubs:
        reach=[x for x in nodes if x not in nm.CLOSED and x!=H and A['spoke_min_km']<=D.km(H,x)<=D.green(H,x)]
        additions=[]; old=[]
        for X,Y in itertools.combinations(reach,2):
            d=D.km(X,Y)
            if D.has_direct(X,Y) or (D.km(H,X)+D.km(H,Y))/d>A['transfer_max_circuity']:continue
            (additions if d<500 else old).append({'x':X,'y':Y,'km':d,'od_base':D.get(X,Y,'base')})
        fixed=[]
        for scen in AS:
            spokes=[r['to'] for r in routes if r['scenario']==scen and r['variant']=='Хаб '+H]
            contained=[r for r in additions if r['x'] in spokes and r['y'] in spokes]
            fixed.append({'scenario':scen,'new_pairs_on_saved_spokes':contained})
        gate.append({'hub':H,'old_pair_count':len(old),'additions':additions,'saved_networks':fixed})
    dump('transfer_gate.json',{'subject':SHA,'scope':'Enumeration of the connecting-OD gate only. The same author parameter ALSO controls local demand in leg_share; replay below separates these uses. Other gates include 250 km spokes and 1.35 circuity.','hubs':gate})
    print('transfer gate',[(r['hub'],len(r['additions'])) for r in gate if r['additions']],flush=True)
    if not reselect:return
    results=[]
    saved=rows('data/processed/network_summary.csv')
    original_share=nm.leg_share
    modes={'baseline':(500,500),'remove_transfer_gate':(0,500),'remove_local_gate':(500,0),'remove_both_gates':(0,0)}
    for scen in ['base','cautious']:
        for H in hubs:
            for mode,(transfer_gate,local_gate) in modes.items():
                t=time.monotonic(); aa=dict(AS[scen],transfer_min_km=transfer_gate)
                nm.leg_share=lambda L,f,A: original_share(L,f,dict(A,transfer_min_km=local_gate))
                chosen,r=nm.hub_best(H,D,aa,scen,nodes)
                legs,tr,hours,cost,rev,local,transfer,*_=r
                item={'scenario':scen,'hub':H,'mode':mode,'transfer_min_km':transfer_gate,'local_min_km':local_gate,'spokes':chosen,
                      'aircraft':math.ceil(hours/(aa['block_h_per_day']*7))+int(aa['spare_aircraft']),
                      'result_mln_year':(rev-cost)*aa['weeks_per_year']/1e6,
                      'segments_year':sum(2*L['carried_dir_week'] for L in legs.values())*aa['weeks_per_year'],
                      'elapsed_s':round(time.monotonic()-t,3)}
                if mode=='baseline':
                    baseline=next(q for q in saved if q['scenario']==scen and q['hub']==H)
                    item['published_rounded_match']=(round(item['result_mln_year'])==int(baseline['result_mln_year']) and round(item['segments_year'])==int(baseline['segments_year']))
                    assert item['published_rounded_match'],item
                else:
                    nm.leg_share=original_share
                    _, old_gate = nm.hub_network(H, D, dict(aa, transfer_min_km=500), scen, nodes, fixed_spokes=chosen)
                    item['same_network_under_old_gate_result_mln']=(old_gate[4]-old_gate[3])*aa['weeks_per_year']/1e6
                    item['same_network_under_old_gate_segments']=sum(2*L['carried_dir_week'] for L in old_gate[0].values())*aa['weeks_per_year']
                    item['old_gate_fixed_network_identical']=abs(item['same_network_under_old_gate_result_mln']-item['result_mln_year'])<1e-8 and abs(item['same_network_under_old_gate_segments']-item['segments_year'])<1e-6
                results.append(item);dump('network_reselection.json',results)
                print(json.dumps(item,ensure_ascii=False),flush=True)
        for mode,local_gate in [('baseline',500),('remove_local_gate',0)]:
            nm.leg_share=lambda L,f,A: original_share(L,f,dict(A,transfer_min_km=local_gate))
            aa=AS[scen];t=time.monotonic()
            chosen=nm.direct_best(D,aa,scen,nodes)
            hours=sum(c[4] for c in chosen)
            item={'scenario':scen,'hub':'DIRECT','mode':mode,'local_min_km':local_gate,
                  'aircraft':math.ceil(hours/(aa['block_h_per_day']*7))+int(aa['spare_aircraft']),
                  'spokes':['-'.join(c[1:4]) for c in chosen],
                  'result_mln_year':sum(c[6]-c[5] for c in chosen)*aa['weeks_per_year']/1e6,
                  'segments_year':sum(c[7] for c in chosen)*aa['weeks_per_year'],
                  'elapsed_s':round(time.monotonic()-t,3)}
            if mode=='baseline':
                baseline=next(q for q in saved if q['scenario']==scen and not q['hub'])
                item['published_rounded_match']=round(item['result_mln_year'])==int(baseline['result_mln_year']) and round(item['segments_year'])==int(baseline['segments_year'])
                assert item['published_rounded_match'],item
            results.append(item);dump('network_reselection.json',results)
            print(json.dumps(item,ensure_ascii=False),flush=True)
    nm.leg_share=original_share
    ch, original=nm.hub_best('OMS',D,AS['base'],'base',nodes)
    fuel=[]
    for compensation in [32930,3024,0]:
        aa=dict(AS['base'],fuel_compensation_rub_per_t=compensation)
        _,r=nm.hub_network('OMS',D,aa,'base',nodes,fixed_spokes=ch)
        fuel.append({'fuel_compensation_rub_per_t':compensation,
                     'result_mln_year':(r[4]-r[3])*aa['weeks_per_year']/1e6,
                     'same_spokes_and_frequency':all(original[0][k]['freq']==r[0][k]['freq'] for k in ch),
                     'scope':'fixed OMS base network; all other assumptions fixed; not a legal or future entitlement assessment'})
    dump('fuel_fixed_network.json',fuel)


def prepare_and_run(raw):
    with tempfile.TemporaryDirectory(prefix='rw-distance-audit-') as root:
        root=Path(root)
        paths=subprocess.check_output(['git','ls-tree','-r','--name-only',SHA,'src','data'],cwd=REPO,text=True).splitlines()
        for p in paths:
            if not ((p.startswith('src/') and p.endswith('.py')) or (p.startswith('data/') and p.endswith(('.json','.csv')))):continue
            dst=root/p;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(blob(p))
        dst=root/'data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv'
        dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw.read_bytes())
        network(root,True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runtime',type=Path,help='Isolated src/data directory extracted from the pinned Git SHA, plus the pinned untracked Tochno CSV.')
    ap.add_argument('--raw-connectivity',type=Path,help='Prepare and clean a temporary runtime automatically. Provide the original Tochno v20260629 CSV, SHA256 2228111a787e39dd158f4025bd4a2158327479ece589c0cbd34b4108c8ce865a. Runs all bounded replays.')
    ap.add_argument('--reselect',action='store_true',help='Re-run all fleet caps for 20 hubs with separate local/transfer gates, base/cautious without route subsidies, plus direct-network local-gate control.')
    a=ap.parse_args();screening()
    if a.raw_connectivity:prepare_and_run(a.raw_connectivity)
    elif a.runtime:network(a.runtime.resolve(),a.reselect)
