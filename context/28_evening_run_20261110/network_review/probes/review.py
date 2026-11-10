#!/usr/bin/env python3
"""Pinned offline review. Writes exclusively beside this script; no services.

Run with the already installed Python/scipy, BLAS threads 1. Extracts only the
subject network subtree. Independent packing simplex and 3-D vertex oracle do
not call the subject allocator. --keep-runtime retains the scratch for inspection.
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import itertools
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tarfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta

for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[key] = '1'
sys.dont_write_bytecode = True
SUBJECT = 'b47118a48b6d5480217077bf8699a63665c0eb7a'
FIRST = '941d9ebfe97c86baa210da2c56bb1f94cbe298b0'
PREFIX = 'context/28_evening_run_20261110/network'
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RUNTIME = HERE / '.runtime'
BASE = RUNTIME / PREFIX
V2 = BASE / 'v2'
RECORDS = []
DETAILS = {}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def check(name, condition, **evidence):
    RECORDS.append(dict(name=name, passed=bool(condition), **evidence))
    if not condition:
        raise AssertionError((name, evidence))


def near(a, b, tol=0.00002):
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=tol)


def read(p):
    return list(csv.DictReader(p.open()))


def out(name):
    return read(V2 / 'outputs' / name)


def load(name, p):
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def pins_and_replay():
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir()
    with tarfile.open(fileobj=io.BytesIO(git('archive', SUBJECT, PREFIX))) as archive:
        archive.extractall(RUNTIME, filter='data')
    entries = []
    for line in git('ls-tree', '-r', SUBJECT, '--', PREFIX).decode().splitlines():
        meta, path = line.split('\t')
        b = git('show', SUBJECT + ':' + path)
        check('subject_blob:' + path, b == (RUNTIME / path).read_bytes())
        entries.append(dict(path=path, git_blob=meta.split()[2], sha256=sha(b), bytes=len(b)))
    (HERE.parent / 'subject_manifest.json').write_text(json.dumps(dict(subjectSHA=SUBJECT, files=entries), indent=2)+'\n')
    old = git('ls-tree', '-r', '--name-only', FIRST, '--', PREFIX).decode().splitlines()
    check('all25_original_git_blobs_immutable', len(old)==25 and all(git('show', FIRST+':'+p)==git('show', SUBJECT+':'+p) for p in old))
    n = 0
    for path in [BASE/'input_manifest.json', V2/'additional_input_manifest.json', V2/'final_evidence_input_manifest.json']:
        data = json.loads(path.read_text())
        rows = data if isinstance(data, list) else data['inputs']
        for r in rows:
            raw = git('show', r['commit']+':'+r['path'])
            check('input_pin:' + r['local'], raw == (BASE/r['local']).read_bytes() and sha(raw)==r['sha256'] and len(raw)==r['bytes'])
            n += 1
    check('46_owner_history_audit_evidence_inputs', n==46)
    for r in json.loads((BASE/'public_sources_manifest.json').read_text()):
        check('saved_source_hash:' + r['source_id'], sha((BASE/r['local']).read_bytes())==r['sha256'])
    files = json.loads((V2/'output_manifest.json').read_text())['files']
    check('all50_v2_manifest_files', len(files)==50 and all(sha((V2/r['path']).read_bytes())==r['sha256'] and len((V2/r['path']).read_bytes())==r['bytes'] for r in files))
    expected = {p.relative_to(V2).as_posix():p.read_bytes() for p in V2.rglob('*') if p.is_file()}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GIT_DIR=git('rev-parse','--absolute-git-dir').decode().strip(), GIT_WORK_TREE=str(RUNTIME))
    proc = subprocess.run([sys.executable, str(V2/'run_all.py')], cwd=RUNTIME, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (HERE/'owner_replay.log').write_text(proc.stdout)
    check('owner_run_all_exit', proc.returncode==0, returncode=proc.returncode)
    counts=json.loads((V2/'checks.json').read_text())
    check('owner101_checks_separate', counts['checks_passed']==101 and all(r['passed'] for r in counts['checks']))
    mismatches=[p for p,b in expected.items() if p!='output_manifest.json' and (V2/p).read_bytes()!=b]
    check('50_v2_files_reproduced_byte_exact_manifest_clock_excluded', len(expected)==51 and not mismatches, mismatches=mismatches)
    DETAILS['replay']={'owner_checks':101, 'independent_acceptance':False, 'manifest_generated_at_excluded':True, 'reproduced_files':50, 'all_pinned_files':len(entries)}


def geom(a,b,nodes):
    # Spherical cosine formula, independently of subject haversine.
    u,v=nodes[a],nodes[b]
    la,lb=map(math.radians,[float(u['latitude_deg']),float(v['latitude_deg'])])
    dl=math.radians(float(u['longitude_deg'])-float(v['longitude_deg']))
    return 6371*math.acos(max(-1,min(1,math.sin(la)*math.sin(lb)+math.cos(la)*math.cos(lb)*math.cos(dl))))


def simplex(values, matrix, capacity, upper):
    """Maximize nonnegative bounded packing LP from slack basis; no scipy calls.

    Returns a primal solution and a dual certificate for all capacity and
    product upper-bound constraints. Bland entering/leaving prevents cycling.
    """
    n=len(values)
    rows=[list(map(float,r)) for r in matrix]+[[float(i==j) for i in range(n)] for j in range(n)]
    rhs=list(map(float,capacity))+list(map(float,upper))
    m=len(rows)
    table=[r+[float(i==j) for j in range(m)]+[b] for i,(r,b) in enumerate(zip(rows,rhs))]
    table.append([-float(v) for v in values]+[0.]*(m+1))
    basis=list(range(n,n+m)); pivots=0
    while True:
        entering=next((j for j,x in enumerate(table[-1][:-1]) if x < -1e-8),None)
        if entering is None: break
        eligible=[i for i in range(m) if table[i][entering]>1e-10]
        if not eligible: raise AssertionError('unbounded packing LP')
        ratio=min(table[i][-1]/table[i][entering] for i in eligible)
        leaving=min((i for i in eligible if abs(table[i][-1]/table[i][entering]-ratio)<1e-8),key=lambda i:basis[i])
        pivot=table[leaving][entering]
        table[leaving]=[x/pivot for x in table[leaving]]
        for i in range(m+1):
            if i==leaving: continue
            factor=table[i][entering]
            table[i]=[x-factor*y for x,y in zip(table[i],table[leaving])]
        basis[leaving]=entering;pivots+=1
        assert pivots<10000
    x=[0.]*n
    for i,j in enumerate(basis):
        if j<n:x[j]=table[i][-1]
    dual=table[-1][n:n+m]
    primal=sum(a*b for a,b in zip(values,x));dvalue=sum(a*b for a,b in zip(rhs,dual))
    primal_ok=all(v>=-1e-7 for v in x) and all(sum(a*b for a,b in zip(r,x))<=b+1e-7 for r,b in zip(rows,rhs))
    dual_ok=all(v>=-1e-7 for v in dual) and all(sum(rows[i][j]*dual[i] for i in range(m))>=values[j]-1e-7 for j in range(n))
    assert primal_ok and dual_ok and near(primal,dvalue)
    return x,primal,dict(primal=primal,dual=dvalue,pivots=pivots,capacity_prices=dual[:len(matrix)],upper_prices=dual[len(matrix):])


def vertices3(values, caps, upper):
    """Enumerate every vertex of 2 shared legs + 3 bound constraints."""
    import numpy as np
    rows=[[1,0,1],[0,1,1]]+[[int(i==j) for i in range(3)] for j in range(3)]+[[-int(i==j) for i in range(3)] for j in range(3)]
    rhs=list(caps)+list(upper)+[0]*3
    best=-math.inf;point=None
    for selected in itertools.combinations(range(8),3):
        M=np.array([rows[i] for i in selected],dtype=float)
        if abs(np.linalg.det(M))<1e-10:continue
        x=np.linalg.solve(M,np.array([rhs[i] for i in selected]))
        if all(sum(a*b for a,b in zip(r,x))<=v+1e-7 for r,v in zip(rows,rhs)):
            score=sum(a*b for a,b in zip(values,x))
            if score>best:best,point=score,x.tolist()
    assert point is not None
    return point,best


def numerical():
    calc=load('calculate', V2/'calculate.py')
    params=read(BASE/'inputs/owner4a976/data/assumptions/network.csv')
    nodes={r['iata']:r for r in read(BASE/'inputs/owner4a976/data/processed/catchments.csv')}
    south={r['region'] for r in read(BASE/'inputs/owner4a976/data/assumptions/south_west_regions.csv')}
    od={frozenset((r['a'],r['b'])):r for r in read(BASE/'inputs/owner4a976/data/processed/od_pairs.csv')}
    for r in read(BASE/'inputs/owner4a976/data/processed/demand_estimates.csv'):
        if r['od_base']:od[frozenset((r['a'],r['b']))]=r
    details={'C01':[], 'C07':[], 'C33':[], 'banks':[], 'fixed':[], 'edge':[]}
    for scenario in ['base','cautious']:
        a={r['parameter']:float(r[scenario]) for r in params};p=a['pax_cost_rub'];cap=200*a['lf_max']
        def pair(o,d,f):
            r=od[frozenset((o,d))];annual=float(r['od_'+scenario]);weekly=annual/104
            seg=float(r.get('segments_base') or r.get('segments_on_link') or r['od_base'])
            if scenario=='cautious':seg*=annual/float(r['od_base'])
            direct=r.get('direct_now')=='True' or r.get('route')=='прямой рейс'
            capture=min(a['capture_competitive'],f/(f+seg/104/(100*a['competitor_lf']))) if direct else a['capture_open']*(-math.expm1(-f/a['capture_freq_scale']))
            return dict(q=min(weekly*capture,f*100*a['lf_max']),fare=a['fare_fixed_rub']+a['fare_per_km_rub']*geom(o,d,nodes),annual=annual,week=weekly,direct=direct,capture=capture)
        def cost(o,d,minutes=None):
            bh=minutes/60 if minutes is not None else a['block_fixed_h']+geom(o,d,nodes)*a['route_factor_south' if {nodes[o]['region'],nodes[d]['region']}&south else 'route_factor']/a['block_speed_kmh']
            return bh,(a['fuel_t_per_hour']*bh+a['fuel_t_per_cycle'])*a['fuel_rub_per_t']+bh*(a['mro_rub_per_hour']+a['crew_rub_per_hour']+a['navigation_rub_per_hour'])+a['ground_rub_per_flight']+a['deicing_rub_per_flight']
        for r in out('demand_fare_inputs.csv'):
            if r['scenario']!=scenario:continue
            d=pair(r['origin'],r['destination'],float(r['frequency_each_direction']))
            check('raw_OD_capture_fare:'+scenario+':'+r['origin']+r['destination']+r['frequency_each_direction'],near(d['q'],r['captured_local_one_direction']) and near(d['fare'],r['net_fare_rub']) and near(d['annual']/104,r['diagnostic_week_od_one_direction']))
        # C01 all 6 rows, old and changed price basis.
        d1,d2,dt=pair('NJC','UFA',2),pair('UFA','MRV',2),pair('NJC','MRV',2)
        ft=dt['fare']*a['transfer_fare_factor'];unit=[d1['fare']-p,d2['fare']-p,ft-2*p]
        through=dt['week']*min(a['capture_transfer']*(-math.expm1(-2/3)),dt['capture'])
        fixed=2*sum(cost(o,d,m)[1] for o,d,m in [('NJC','UFA',150),('UFA','NJC',145),('UFA','MRV',155),('MRV','UFA',140)])
        oldfixed=4*(cost('NJC','UFA')[1]+cost('UFA','MRV')[1])
        baseline=d1['q']*unit[0]+d2['q']*unit[1]
        for r in [r for r in out('C01_synchronization.csv') if r['scenario']==scenario]:
            loss=float(r['local_loss_fraction_south']);upper=[d1['q'],d2['q']*(1-loss),through]
            x,obj=vertices3(unit,[cap,cap],upper)
            check('C01_vertex_optimum:'+scenario+':'+str(loss), near(2*(obj-baseline),r['delta_contribution_rub_week']) and near(2*obj-fixed,r['contribution_sync_rub_week']) and near(2*baseline-fixed,r['contribution_unsync_rub_week']))
            old=next(z for z in json.loads((BASE/'first_run.json').read_text())['C01'] if z['scenario']==scenario and near(z['local_loss_fraction_south'],loss))
            check('C01_same_cost_bridge_both_sides:'+scenario+':'+str(loss), near(old['delta_contribution_rub_week'],r['delta_contribution_rub_week']) and near(float(r['contribution_sync_rub_week'])-old['Kmax_full_base_rub_week'],oldfixed-fixed) and near((2*baseline-fixed)-(2*baseline-oldfixed),oldfixed-fixed))
            details['C01'].append(dict(scenario=scenario,loss=loss,vertex=x,delta=2*(obj-baseline),full=2*obj-fixed,cost_bridge=oldfixed-fixed))
        # C07 named endpoints, including refusal bound; no unnamed old clients invented.
        old,new,t=pair('SVX','OMS',2),pair('OMS','KJA',2),pair('SVX','KJA',2)
        ft=t['fare']*a['transfer_fare_factor'];unit=[old['fare']-p,new['fare']-p,ft-2*p]
        fixed=2*(cost('OMS','KJA',125)[1]+cost('KJA','OMS',145)[1]);oldmargin=old['q']*unit[0]
        for r in [r for r in out('C07_demand_bounds.csv') if r['scenario']==scenario]:
            tt=t['week'] if r['stress']=='entire_local_and_through_OD' else t['week']*min(a['capture_transfer']*(-math.expm1(-2/3)),t['capture'])
            ll=new['q'] if r['stress']=='captured_OD' else new['week']
            x,obj=vertices3(unit,[cap,cap],[old['q'],ll,tt]);delta=2*(obj-oldmargin)-fixed
            check('C07_vertex_bound:'+scenario+':'+r['stress'],near(delta,r['delta_contribution_rub_week']))
            if r['stress']=='entire_local_and_through_OD' and scenario=='cautious':check('C07_cautious_refusal_within_named_OD',delta<0)
            if r['stress']=='captured_OD':
                breakeven=(fixed/2-x[2]*unit[2]-(x[0]-old['q'])*unit[0])/unit[1]
                extension=next(z for z in out('C07_extension.csv') if z['scenario']==scenario)
                check('C07_break_even_numerator_denominator:'+scenario,near(breakeven,extension['break_even_total_local_OMS_KJA_each_direction_week']))
                details['C07'].append(dict(scenario=scenario,stress=r['stress'],delta=delta,break_even_local_per_side=breakeven,total_local_OD_per_side=new['week'],numerator=fixed/2-x[2]*unit[2]-(x[0]-old['q'])*unit[0],denominator=unit[1]))
            else:details['C07'].append(dict(scenario=scenario,stress=r['stress'],delta=delta,primal=x))
        # C33 retain every other occupied seat exactly and cancel only its unchanged revenue.
        feed,trunk,t=pair('KUF','SVX',7),pair('SVX','OMS',2),pair('KUF','OMS',2)
        q1,q2=feed['q']*2/7,trunk['q'];ft=t['fare']*a['transfer_fare_factor'];dt=t['week']*a['capture_transfer']*(-math.expm1(-2/3))
        unit=[feed['fare']-p,trunk['fare']-p,ft-2*p];baseline=q1*unit[0]+q2*unit[1]
        for r in [r for r in out('C33_retiming.csv') if r['scenario']==scenario]:
            state=r['occupied_state'];loss=float(r['local_loss_fraction_trunk'])
            sold=cap if state in ['planning_lf_already_sold','planning_lf_sold_allow100'] else 200
            other=[sold-q1,sold-q2] if state!='local_only' else [0,0]
            total=cap if state in ['local_only','planning_lf_already_sold'] else 200
            available=[total-v for v in other]
            x,obj=vertices3(unit,available,[q1,q2*(1-loss),dt]);delta=2*(obj-baseline)
            check('C33_vertex_occupied_fares:'+scenario+':'+state+':'+str(loss),near(delta,r['delta_contribution_rub_week']) and near(2*x[2],r['new_through_journeys_week']) and all(x[i]+x[2]+other[i]<=total+1e-7 for i in [0,1]))
            # Arbitrary retained-client fares must cancel; loss of their job is an external gate.
            retained_margin=other[0]*12345+other[1]*98765
            check('C33_other_clients_cancel_only_if_retained:'+scenario+state+str(loss),near(2*((obj+retained_margin)-(baseline+retained_margin)),delta))
            if state=='all_physical_seats_sold':check('C33_full_seats_no_positive_gain:'+scenario+str(loss),delta<=1e-6 and (loss!=0 or near(delta,0)))
            details['C33'].append(dict(scenario=scenario,state=state,loss=loss,primal=x,retained_other_seats_each_direction=other,delta=delta))
            # Uniform diagnostic splitting is a witness on each of the two dates
            # in both directions, not independent sales of the same pool twice.
            per_date=[v/2 for v in x];other_date=[v/2 for v in other]
            check('C33_per_dated_flight_capacity:'+scenario+state+str(loss),all(per_date[i]+per_date[2]+other_date[i]<=total/2+1e-7 for i in [0,1]))
        # Fixed programs + independent multi-product simplex with primal/dual certificate.
        for network,hub,spokes in [('KUF4','KUF',['ARH','OMS','NJC','MRV']),('OMS1','OMS',['KJA']),('OMS4','OMS',['KJA','KUF','GOJ','NOZ']),('OMS8','OMS',['KJA','KUF','GOJ','NOZ','GSV','UFA','TOF','VOG'])]:
            fixed=hours=localmargin=0.;values=[];upper=[];use=[];products=[]
            for i,spoke in enumerate(spokes):
                d=pair(hub,spoke,2);h1,c1=cost(hub,spoke,125 if (hub,spoke)==('OMS','KJA') else None);h2,c2=cost(spoke,hub,145 if (hub,spoke)==('OMS','KJA') else None)
                fixed+=2*(c1+c2);hours+=2*(h1+h2);localmargin+=2*d['q']*(d['fare']-p)
                values.append(d['fare']-p);upper.append(d['q']);use.append([i]);products.append([hub,spoke,'local'])
            frow=next(r for r in out('fixed_programs.csv') if r['scenario']==scenario and r['network']==network)
            check('fixed_raw_budget_hours:'+scenario+network,near(localmargin-fixed,frow['contribution_rub_week']) and near(hours,frow['block_hours_week']) and localmargin-fixed<0)
            details['fixed'].append(dict(network=network,scenario=scenario,local=localmargin-fixed,block_hours=hours))
            for i,x in enumerate(spokes):
                for j,y in enumerate(spokes[i+1:],i+1):
                    km=geom(x,y,nodes);circuity=(geom(x,hub,nodes)+geom(hub,y,nodes))/km
                    if km<500 or circuity>1.35:
                        continue
                    check('bank_no_missing_admitted_OD:'+network+x+y,frozenset((x,y)) in od)
                    d=pair(x,y,2)
                    if d['direct']:continue
                    values.append(d['fare']*a['transfer_fare_factor']-2*p);upper.append(d['week']*a['capture_transfer']*(-math.expm1(-2/3)));use.append([i,j]);products.append([x,y,'transfer'])
            matrix=[[int(i in leg) for leg in use] for i in range(len(spokes))]
            x,obj,cert=simplex(values,matrix,[cap]*len(spokes),upper)
            row=next(r for r in out('bank_upper_bound.csv') if r['network']==network and r['scenario']==scenario)
            check('bank_independent_simplex_dual:'+scenario+network,near(2*obj-fixed,row['ideal_bank_contribution_rub_week']) and 2*obj-fixed<0)
            details['banks'].append(dict(network=network,scenario=scenario,products=products,solution=x,upper=upper,capacity_each_direction=cap,contribution=2*obj-fixed,certificate=cert))
            # Rebuild as directed leg capacities with two separate OD directions;
            # test the symmetry reduction instead of merely assuming factor 2.
            physical=[(hub,z) for z in spokes]+[(z,hub) for z in spokes]
            directed_use=[];dv=[];du=[]
            for (o,d,kind),value,limit in zip(products,values,upper):
                for start,end in [(o,d),(d,o)]:
                    path=[(start,end)] if kind=='local' else [(start,hub),(hub,end)]
                    directed_use.append(path);dv.append(value);du.append(limit)
            directed_matrix=[[int(leg in path) for path in directed_use] for leg in physical]
            dx,dobj,dcert=simplex(dv,directed_matrix,[cap]*len(physical),du)
            check('bank_directed_OD_and_leg_oracle:'+scenario+network,near(dobj,2*obj))
            details['banks'][-1]['directed_certificate']=dcert
            # Physical capacity and planning LF are different scenario inputs.
            _,physical_obj,_=simplex(values,matrix,[200]*len(spokes),upper)
            details['banks'][-1]['physical100pct_sensitivity_contribution']=2*physical_obj-fixed
            check('bank_LF_is_not_physical_capacity:'+scenario+network,physical_obj>=obj-1e-6)
        # Price/time bridge: both legs/cycles preserved, only elapsed analog changes.
        for r in [r for r in out('first_to_final_bridge.csv') if r['scenario']==scenario]:
            if r['network']=='C01':
                cost_delta=4*(cost('NJC','UFA')[1]+cost('UFA','MRV')[1])-2*sum(cost(o,d,m)[1] for o,d,m in [('NJC','UFA',150),('UFA','NJC',145),('UFA','MRV',155),('MRV','UFA',140)])
            elif r['network']=='KUF4':cost_delta=0
            else:cost_delta=4*cost('OMS','KJA')[1]-2*(cost('OMS','KJA',125)[1]+cost('KJA','OMS',145)[1])
            check('all14_price_time_bridge:'+scenario+r['network']+r['metric'],near(float(r['final'])-float(r['first_slice']),cost_delta) and near(r['delta'],cost_delta))
        # Commercial KUF deployment is identical; only two empty ferry flights
        # differ. No fake subsidy or hidden station profit makes it positive.
        b=next(r for r in out('C03_base_comparison.csv') if r['scenario']==scenario)
        ferry=2*cost('SVX','KUF')[1]
        check('KUF_deployment_cost_threshold:'+scenario,near(ferry,b['ferry_variable_cost_rub_week']) and near(ferry,b['Kmax_extra_KUF_base_minus_deployment_lodging_rub_week']) and near(float(b['contribution_existing_KUF_support_rub_week'])-ferry,b['contribution_weekly_deployment_rub_week']))
        # Independent C01 piecewise threshold roots and infeasible spends.
        d1,d2,t=pair('NJC','UFA',2),pair('UFA','MRV',2),pair('NJC','MRV',2)
        upper=t['week']*min(a['capture_transfer']*(-math.expm1(-2/3)),t['capture']);u=[d1['fare']-p,d2['fare']-p,t['fare']*a['transfer_fare_factor']-2*p]
        base=d1['q']*u[0]+d2['q']*u[1]
        for r in [r for r in out('C01_spend_thresholds.csv') if r['scenario']==scenario]:
            loss=float(r['local_loss_fraction_south']);spend=float(r['diagnostic_extra_spend_rub_week'])
            def delta(z):return 2*(min(d1['q'],cap-z)*u[0]+min(d2['q']*(1-loss),cap-z)*u[1]+z*u[2]-base)
            knots=sorted({0.,upper}|{v for v in [cap-d1['q'],cap-d2['q']*(1-loss)] if 0<=v<=upper})
            roots=[z for z in knots if delta(z)>=spend-1e-7]
            for l,h in zip(knots,knots[1:]):
                dl,dh=delta(l),delta(h)
                if dl<spend<=dh:roots.append(l+(spend-dl)/(dh-dl)*(h-l))
            required=min(roots) if roots else None
            check('C01_threshold_root:'+scenario+str(loss)+str(spend), (required is None and r['feasible_in_named_OD_and_capacity']=='False') or (required is not None and near(2*required,r['minimum_through_journeys_both_directions_week'])))
    # Adversarial packing tests compare owner's solver with an unrelated vertex oracle.
    rng=random.Random(47118)
    cases=[(0,10,10,10,100,100,300),(5,0,0,100,100,100,300),(5,10,10,10,100,100,150),(5,10,10,10,100,100,200),(5,10,10,10,-1,-2,-3),(5,10,10,0,100,100,300)]
    cases += [(rng.choice([0,1,10,100]),*[rng.uniform(0,200) for _ in range(3)],*[rng.uniform(-1000,20000) for _ in range(3)]) for _ in range(120)]
    for k,(cap,d1,d2,dt,f1,f2,ft) in enumerate(cases):
        # Argument fares chosen to realize arbitrary unit margins, including negative.
        owner=calc.three_pools('base',cap,d1,d2,dt,f1+500,f2+500,ft+1000)
        vertex,obj=vertices3([f1,f2,ft],[cap,cap],[d1,d2,dt])
        _,simple,cert=simplex([f1,f2,ft],[[1,0,1],[0,1,1]],[cap,cap],[d1,d2,dt])
        check('adversarial_threepool:'+str(k),near(owner[3],obj) and near(simple,obj))
        if k<6:details['edge'].append(dict(arguments=[cap,d1,d2,dt,f1,f2,ft],objective=obj,vertex=vertex,certificate=cert))
    DETAILS.update(details)


def calendars_and_integration():
    flights=out('dated_flights.csv');check('dated_row_count',len(flights)==146)
    groups=defaultdict(list)
    for r in flights:
        dep=datetime.fromisoformat(r['departure_utc']);arr=datetime.fromisoformat(r['arrival_utc'])
        check('UTC_duration_date:'+r['flight_id']+r['variant'],near((arr-dep).total_seconds()/60,r['block_minutes']) and datetime.fromisoformat(r['departure_local'])==dep and datetime.fromisoformat(r['arrival_local'])==arr and r['departure_local'][:10]==r['service_date'])
        groups[r['network'],r['variant'],r['tail_scenario']].append(r)
    for key,rs in groups.items():
        rs.sort(key=lambda r:r['departure_utc'])
        gaps=[]
        for x,y in zip(rs,rs[1:]):
            gap=(datetime.fromisoformat(y['departure_utc'])-datetime.fromisoformat(x['arrival_utc'])).total_seconds()/60
            gaps.append(gap)
            check('tail_continuity_turn:'+str(key)+x['flight_id'],x['destination']==y['origin'] and gap>= (int(key[1][4:]) if key[0]=='C07' and key[1].startswith('turn') else 45))
    for net,tails,hub in [('KUF4',1,'KUF'),('OMS1',1,'OMS'),('OMS4',1,'OMS'),('OMS8',2,'OMS')]:
        rs=[r for r in flights if r['network']==net]
        check('fixed_tail_slots:'+net,len({r['tail_scenario'] for r in rs})==tails and all(v==2 for v in Counter((r['origin'],r['destination']) for r in rs).values()))
        for tail in {r['tail_scenario'] for r in rs}:
            seq=sorted([r for r in rs if r['tail_scenario']==tail],key=lambda r:r['departure_utc'])
            check('fixed_start_end_base:'+net+tail,seq[0]['origin']==hub and seq[-1]['destination']==hub)
            for day in {r['service_date'] for r in seq}:
                daily=[r for r in seq if r['service_date']==day]
                check('fixed_actual_daily_caps:'+net+tail+day,sum(float(r['block_minutes']) for r in daily)<=600 and (datetime.fromisoformat(daily[-1]['arrival_utc'])-datetime.fromisoformat(daily[0]['departure_utc'])).total_seconds()/60<=840)
    kuf=[r for r in flights if r['network']=='KUF4']
    deployed=[r for r in flights if r['network']=='KUF4_SVX_deployed']
    keys=['origin','destination','departure_utc','arrival_utc','block_minutes','seats']
    check('KUF_same_commercial_flights_deployed',len(deployed)==len(kuf)+2 and Counter(tuple(r[k] for k in keys) for r in kuf)==Counter(tuple(r[k] for k in keys) for r in deployed if r['flight_number']!='EMPTY_FERRY'))
    check('KUF_deployed_start_finish_SVX',deployed[0]['origin']=='SVX' and deployed[-1]['destination']=='SVX')
    for day in ['2026-12-07','2026-12-11']:
        identity=lambda r:(r['origin'],r['destination'],r['service_date'],r['block_minutes'],r['tail_scenario'])
        check('C01_identical_dated_legs_positions:'+day,Counter(identity(r) for r in flights if r['network']=='C01' and r['variant']=='sync' and r['service_date']==day)==Counter(identity(r) for r in flights if r['network']=='C01' and r['variant']=='unsync' and r['service_date']==day))
    for r in out('dated_connections.csv'):
        ids=r['legs'].split(';')
        legs=[next(x for x in flights if x['network']==r['network'] and x['variant']==r['variant'] and x['flight_id']==fid) for fid in ids]
        wait=(datetime.fromisoformat(legs[1]['departure_utc'])-datetime.fromisoformat(legs[0]['arrival_utc'])).total_seconds()/60
        check('MCT_recompute:'+r['network']+r['variant']+r['service_date']+r['origin']+r['min_connection_minutes'],near(wait,r['wait_minutes']) and (r['passes']=='True')==(float(r['min_connection_minutes'])<=wait<=180))
    old=[r for r in flights if r['network']=='C33' and r['variant']=='KEEP'];new=[r for r in flights if r['network']=='C33' and r['variant']=='retime']
    fields=['flight_number','origin','destination','service_date','block_minutes']
    check('C33_eight_same_dated_physical_legs',len(old)==len(new)==8 and Counter(tuple(r[k] for k in fields) for r in old)==Counter(tuple(r[k] for k in fields) for r in new))
    for initial in ['2026-12-08','2026-12-11']:
        for variant in ['KEEP','retime']:
            seq=sorted([r for r in flights if r['network']=='C33' and r['variant']==variant and r['service_date'] in [initial,(datetime.fromisoformat(initial)+timedelta(days=1)).date().isoformat()]],key=lambda r:r['departure_utc'])
            check('C33_rotation_span_and_OMS_wait:'+initial+variant,near(sum(float(r['block_minutes']) for r in seq),415) and near((datetime.fromisoformat(seq[-1]['arrival_utc'])-datetime.fromisoformat(seq[0]['departure_utc'])).total_seconds()/60,2370) and near((datetime.fromisoformat(seq[2]['departure_utc'])-datetime.fromisoformat(seq[1]['arrival_utc'])).total_seconds()/60,50 if variant=='KEEP' else 1815))
    # Next-assignment is derived from flight clocks, not accepted from prefilled slack.
    for r in out('C07_next_assignment.csv'):
        seq=[x for x in flights if x['network']=='C07' and x['variant']==r['variant'] and x['service_date']==r['day'] and x['destination']=='SVX']
        ready=datetime.fromisoformat(seq[0]['arrival_utc'])+timedelta(minutes=int(r['variant'][4:]))
        opportunity=datetime.fromisoformat(r['day']+'T07:25:00+05:00')
        slack=(opportunity-ready).total_seconds()/60
        check('C07_next_opportunity:'+r['day']+r['variant'],near(slack,r['slack_minutes']) and r['actual_tail_assignment']=='UNKNOWN' and (r['applies_real_example']=='True')==(r['day']=='2026-12-09'))
    for day in ['2026-12-08','2026-12-11']:
        following=(datetime.fromisoformat(day)+timedelta(days=1)).date().isoformat()
        for turn in [30,45,60]:
            variant='turn'+str(turn)
            seq=sorted([x for x in flights if x['network']=='C07' and x['variant']==variant and x['service_date'] in [day,following]],key=lambda r:r['departure_utc'])
            keep=sorted([x for x in flights if x['network']=='C07' and x['variant']=='KEEP' and x['service_date'] in [day,following]],key=lambda r:r['departure_utc'])
            delay=(datetime.fromisoformat(seq[-1]['arrival_utc'])-datetime.fromisoformat(keep[-1]['arrival_utc'])).total_seconds()/60
            check('C07_full_rotation_delay:'+day+variant,len(seq)==4 and len(keep)==2 and near(delay,220+3*turn) and near(sum(float(r['block_minutes']) for r in seq),475) and near((datetime.fromisoformat(seq[-1]['arrival_utc'])-datetime.fromisoformat(seq[0]['departure_utc'])).total_seconds()/60,475+3*turn))
    for r in out('C33_next_assignment.csv'):
        leg=next(x for x in flights if x['network']=='C33' and x['variant']==r['variant'] and x['flight_number']=='WZ5072' and x['service_date']==r['date'])
        ready=datetime.fromisoformat(leg['arrival_utc'])+timedelta(minutes=45)
        slack=(datetime.fromisoformat('2026-12-09T07:25:00+05:00')-ready).total_seconds()/60
        check('C33_next_opportunity:'+r['variant'],ready==datetime.fromisoformat(r['tail_ready_SVX_local']) and near(slack,r['slack_minutes']) and r['actual_tail_assignment']=='UNKNOWN')
    # Only selected published IDs matched; no repeat of source parser audit.
    published=read(BASE/'inputs/evidence38f/dated_service_instances.csv')
    selected=[]
    for r in old:
        match=[x for x in published if (x['origin'],x['destination'],x['date'],x['flight'].replace('-',''))==(r['origin'],r['destination'],r['service_date'],r['flight_number'])]
        check('C33_selected_publication:'+r['flight_id'],len(match)==1)
        departure=r['departure_local'][11:16];arrival=r['arrival_local'][11:16]
        arrival_options=[z.strip().split()[0] for z in match[0]['arrival_local'].split('|')]
        check('C33_selected_publication_clocks:'+r['flight_id'],departure==match[0]['departure_local'] and arrival in arrival_options)
        if r['flight_number']=='WZ1034':
            check('C33_latest_conflicting_clock_no_average:'+r['flight_id'],arrival=='10:45' and arrival==max(arrival_options))
        selected+=match
    check('C33_two_conflicts_retained',sum(x['clock_or_type_conflict']=='True' for x in selected)==2)
    DETAILS['calendar']={'alternative_rows':146,'tail_groups':len(groups),'fixed_tails':{'KUF4':1,'OMS1':1,'OMS4':1,'OMS8':2},'C07_Wed_slacks':[10,-50,-110],'C33_Wed_slacks':[305,-900],'published_selected':8,'conflicts_retained':2}
    # No unsupported grant is allowed in the calculated ticket/cost equality.
    for r in out('subsidy_payment_caps_only.csv'):
        check('subsidy_cap_per_performed_flight:'+r['route'],near(float(r['cap_rub_per_oneway_completed_flight'])*float(r['hypothetical_completed_eligible_flights']),r['arithmetic_payment_ceiling_rub']) and r['supported_PnL'].startswith('NOT_CALCULATED'))
    for r in out('subsidy_gap_thresholds.csv'):
        check('subsidy_gap_not_ticket_yield:'+r['scenario'],near(float(r['required_payment_rub_per_added_flight_before_fare_effect'])*4,r['no_support_gap_rub_week']))
    d=out('route_deltas.csv')
    check('route_date_variant_scenario_keys',all(r['scenario'] in ['base','cautious'] and r['variant'] and r['route'] and r['date'] and r['flight_id'] for r in d))
    check('route_keys_not_duplicate_inside_variant',len(d)==len({(r['scenario'],r['network'],r['variant'],r['flight_id']) for r in d}))


def main():
    args=argparse.ArgumentParser();args.add_argument('--keep-runtime',action='store_true');args=args.parse_args()
    try:
        pins_and_replay();numerical();calendars_and_integration()
    finally:
        (HERE/'results.json').write_text(json.dumps(dict(subjectSHA=SUBJECT,checks=RECORDS,checks_passed=sum(r['passed'] for r in RECORDS),checks_failed=sum(not r['passed'] for r in RECORDS),details=DETAILS),ensure_ascii=False,indent=2)+'\n')
    if not args.keep_runtime:shutil.rmtree(RUNTIME)
    print(json.dumps(dict(subjectSHA=SUBJECT,checks_passed=len(RECORDS),runtime_removed=not RUNTIME.exists())))


if __name__=='__main__':main()
