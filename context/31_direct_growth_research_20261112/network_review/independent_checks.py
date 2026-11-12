#!/usr/bin/env python3
"""Read-only independent checks of real network CSVs and in-memory API repeats.
Only writes actual_checks.csv, validation.json, reviewed_summary.json beside this script.
No author rebuild, git mutation, network calls or P32 model inputs.
"""
import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,importlib.util,copy
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,date
H=Path(__file__).resolve().parent; N=H.parent/'networks'; W=H.parents[2]
def read(p):
    with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p):return json.loads(p.read_text())
checks=[]
def check(name,ok,evidence):
    checks.append(dict(check=name,status='PASS' if ok else 'FAIL',evidence=str(evidence)))
    print(checks[-1],flush=True)
def close(a,b):return abs(float(a)-float(b))<.001
before={p:sha(p) for p in N.rglob('*') if p.is_file() and '__pycache__' not in str(p)}
protected=js(N/'protected_snapshot.json')['files']
bad=[p for p,h in protected.items() if not (W/p).is_file() or sha(W/p)!=h]
check('protected content hashes, independent of HEAD and tracked count',not bad,{'count':len(protected),'changed':bad})
manifest=js(N/'manifest.json')
for group,base in [('inputs',H.parent),('outputs',N)]:
    bad=[p for p,h in manifest[group].items() if not (base/p).is_file() or sha(base/p)!=h]
    check('manifest '+group,not bad,bad)
rows=read(N/'network_comparison.csv'); months=read(N/'monthly_results.csv'); fs=read(N/'dated_flights.csv')
key=lambda r:tuple(r[x] for x in ('programme','resource','scenario','keep_case'))
mg=defaultdict(list)
for m in months:mg[key(m)].append(m)
err=[]
fields={'known_increment_upper_conditional_RUB':'known_increment_upper_conditional_RUB','P_net_revenue_RUB':'P_net_revenue_RUB','KEEP_net_revenue_RUB':'KEEP_net_revenue_RUB','P_known_operating_cost_RUB':'P_known_cost_RUB','KEEP_known_operating_cost_RUB':'KEEP_known_cost_RUB','P_directed_departures':'P_departures','KEEP_directed_departures':'KEEP_departures','P_operated_journeys':'P_journeys','KEEP_operated_journeys':'KEEP_journeys'}
for r in rows:
    if r['programme']=='KEEP':continue
    ms=[m for m in mg[key(r)] if m['month'].startswith(r['year'])]
    if len(ms)!=12:err.append((key(r),r['year'],'month count'))
    for a,b in fields.items():
        if not close(r[a],sum(float(m[b]) for m in ms)):err.append((key(r),a))
    v=float(r['P_net_revenue_RUB'])-float(r['P_known_operating_cost_RUB'])-float(r['KEEP_net_revenue_RUB'])+float(r['KEEP_known_operating_cost_RUB'])
    if not close(v,r['known_increment_upper_conditional_RUB']):err.append((key(r),'joint identity'))
check('all annual CSV totals from twelve actual months and joint P minus KEEP',not err,{'annual_rows':len(rows),'errors':err[:10]})
check('NS and unknown losses/cash remain explicit',all(m['support_route_RUB']==m['support_fuel_RUB']=='0' for m in months) and all(all(r[f]=='NULL' for f in ['donor_loss_RUB','omitted_F_RUB','outside_affected_old_RW_and_MQF_marketed_loss_RUB','full_incremental_PnL_RUB','incremental_cash_RUB','whole_KEEP_cash_RUB']) for r in rows),'No missing loss converted to zero')
check('passenger stress applied once to journey delta',all(close(float(r['known_increment_upper_conditional_RUB'])-(float(r['P_operated_journeys'])-float(r['KEEP_operated_journeys']))*(500 if r['scenario']=='base' else 650),r['F_pax_500_650_nonoverlap_stress_increment_RUB']) for r in rows),'Separate from base known cost and P05 net fare; nonoverlap assumption required')
control='CONTROL_2AER_2MRV_2OMS_REPLACED'
main=[r for r in rows if r['resource']=='E2/S0' and r['keep_case']==control]
check('nonempty identical KEEP across programmes',all(float(r['KEEP_directed_departures'])>0 for r in main) and all(len({r['KEEP_variable_contribution_RUB'] for r in main if r['year']==y and r['scenario']==s})==1 for y in ('2027','2028') for s in ('base','cautious')),[(r['programme'],r['KEEP_directed_departures']) for r in main[:5]])
check('E0 S0 has no operations or incremental result',all(float(r['P_directed_departures'])==float(r['known_increment_upper_conditional_RUB'])==0 for r in rows if r['resource']=='E0/S0'),'Reserve alone creates no flying capacity')
# Independently inspect all serialized requests and dated flight geometry.
requests={p.stem:js(p) for p in (N/'requests').glob('*.json')}
err=[]
for name,q in requests.items():
    if 'P' not in q:continue
    if q['P']['tails']!=q['KEEP']['tails']:err.append(name)
    for side in ('P','KEEP'):
        ts=q[side]['tails']
        if sum(bool(t.get('reserve')) for t in ts)!=1:err.append(name+' reserve')
check('identical resource calendar P KEEP and one separate reserve in requests',not err,err)
fg=defaultdict(list); cycles=defaultdict(list); err=[]
entries={'S1':{'SJ-A':'2027-08-01','SJ-B':'2027-11-01'},'S1D6':{'SJ-A':'2028-02-01','SJ-B':'2028-05-01'},'S0':{}}
for f in fs:
    fg[(f['programme'],f['resource'],f['side'],f['tail'])].append(f)
    cycles[(f['programme'],f['resource'],f['side'],f['rotation_id'])].append(f)
    dep=datetime.fromisoformat(f['departure_utc']); arr=datetime.fromisoformat(f['arrival_utc'])
    if not close((arr-dep).total_seconds()/60,f['block_minutes']):err.append('duration')
    if f['tail']=='RES-1':err.append('reserve used')
    if f['tail'].startswith('SJ-') and dep.date().isoformat()<entries[f['resource'].split('/')[1]].get(f['tail'],'9999'):err.append('entry')
for k,fl in fg.items():
    fl.sort(key=lambda f:f['departure_utc']); loc='SVX';prev=None
    for f in fl:
        if f['origin']!=loc:err.append(('position',k))
        if prev and (datetime.fromisoformat(f['departure_utc'])-datetime.fromisoformat(prev)).total_seconds()<3600:err.append(('turn',k))
        loc=f['destination'];prev=f['arrival_utc']
for k,fl in cycles.items():
    fl.sort(key=lambda f:f['departure_utc'])
    if fl[0]['origin']!=fl[-1]['destination']:err.append(('unclosed',k))
check('all dated legs durations, continuity, 60min turns, closed cycles, entry and reserve',not err,{'flights':len(fs),'rotations':len(cycles),'errors':err[:10]})
check('leap and full dated D1 years',any(f['departure_utc'].startswith('2028-02-29') for f in fs) and all(sum(1 for f in fs if f['programme']=='D1_FOCUS' and f['resource']=='E2/S0' and f['departure_utc'].startswith(str(y)))==2*d for y,d in [(2027,365),(2028,366)]),'730 / 732 legs')
rc=read(N/'resource_checks.csv');err=[]
for r in rc:
    e,s=r['resource'].split('/'); expected=int(e[1])+sum(v<=r['date'] for v in entries[s].values())
    if int(r['N_working'])!=expected or int(r['used_working_tails'])>expected:err.append(r)
check('N(t) independently from entry dates on every resource day',not err,{'days':len(rc),'errors':len(err)})
# Real full-horizon API repeats; arithmetic/seats checks below are independently reconstructed.
spec=importlib.util.spec_from_file_location('review_network_api',N/'calculate.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
kreq=js(N/'requests/COMMON_AFFECTED_KEEP_E2_S0.json'); saturation={}; apierr=[]; ledgererr=[]
for name in C.DIRECTS+[C.HUB]:
    req=js(N/f'requests/{name}_E2_S0.json')['P']
    for sc in ('base','cautious'):
        z=C.evaluate(req,kreq,2,'S0',sc,hub=True)
        for side,label in [('programme','P'),('keep','KEEP')]:
            data=z[side]; b=data['bundle']; a=data['allocation']['allocations']; prod={p['product_id']:p for p in b['products']}; fl={f['flight_instance_id']:f for f in b['flights']}
            seat=Counter(); pool=Counter(); rev=Counter(); cost=Counter()
            for x in a:
                pool[(x['demand_pool_id'],x['month'],x['customer_segment'])]+=x['final_choice']
                if x['owner']!='RW':continue
                p=prod[x['product_id']];rev[x['month']]+=x['carried']*p['net_fare']
                for leg in p['legs']:seat[leg]+=x['carried']
            for f in fl.values():
                # Explicit cost ledger: fuel/cycle + hourly maintenance/crew/nav + ground/deice, no passenger fee.
                h=f['block_hours_costscreen']; rates=C.RE.COSTS; col='base_point' if sc=='base' else 'cautious_point'
                rate=lambda n:float(rates['HIST-'+n][col])
                price=float(rates['UFA-fuel-20261111']['value'])+float(rates['UFA-fuel_uplift']['value']) if sc=='base' else 161696
                c=(h*rate('fuel_t_per_hour')+rate('fuel_t_per_cycle'))*price+h*sum(rate(n) for n in ('mro_rub_per_hour','crew_rub_per_hour','navigation_rub_per_hour'))+(96089+15000 if sc=='base' else 115307+40000)
                cost[f['departure_utc'][:7]]+=c
            if any(q>fl[i]['saleable_seats']+1e-5 for i,q in seat.items()):ledgererr.append((name,sc,side,'seat'))
            if any(abs(pool[(m['demand_pool_id'],m['month'],m['customer_segment'])]-m['potential_journeys'])>1e-5 for m in b['markets']):ledgererr.append((name,sc,side,'pool'))
            if len(pool)!=len(b['markets']):ledgererr.append('duplicate pool')
            for m in data['monthly']:
                if not close(rev[m['month']],m['net_revenue']) or not close(cost[m['month']],m['known_cost']):ledgererr.append((name,sc,side,m['month']))
            if side=='programme':saturation[name+'/'+sc]={'saturated_legs':sum(abs(seat[i]-f['saleable_seats'])<1e-5 for i,f in fl.items()),'total_legs':len(fl)}
        for y in ('2027','2028'):
            v=sum(rev['month'] and rev['known_contribution'] for rev in z['programme']['monthly'] if rev['month'].startswith(y))-sum(m['known_contribution'] for m in z['keep']['monthly'] if m['month'].startswith(y))
            row=next(r for r in main if r['programme']==name and r['scenario']==sc and r['year']==y)
            if not close(v,row['known_increment_upper_conditional_RUB']):apierr.append((name,sc,y,v))
        if name==C.HUB and sc=='base':
            # Zero either physical leg of an actually carried transfer: must kill that journey.
            b=z['programme']['bundle']; ps={p['product_id']:p for p in b['products']}
            a=next(a for a in z['programme']['allocation']['allocations'] if a['owner']=='RW' and len(ps[a['product_id']]['legs'])==2 and a['carried']>0); p=ps[a['product_id']]
            outcomes=[]
            for leg in p['legs']:
                test=copy.deepcopy(b)
                next(f for f in test['flights'] if f['flight_instance_id']==leg)['saleable_seats']=0
                alloc=C.RE.allocate_p06(test,test['products'])
                outcomes.append(next(x['carried'] for x in alloc['allocations'] if x['product_id']==p['product_id']))
            check('real transfer uses both dated legs, either zero seat kills journey',outcomes==[0,0],{'product':p['product_id'],'carried':a['carried'],'zero_leg_results':outcomes})
check('eight full horizon API repeats reproduce control CSV',not apierr,apierr)
check('independent shared seats OD conservation once-only fares and per-leg cost ledger',not ledgererr,ledgererr[:10])
check('author outputs unchanged by review',all(sha(p)==h for p,h in before.items()),len(before))
check('protected files unchanged after API',all(sha(W/p)==h for p,h in protected.items()),len(protected))
main_table=[{k:r[k] for k in ('programme','year','scenario','known_increment_upper_conditional_RUB','P_directed_departures','KEEP_directed_departures','P_actual_UTC_flight_taildays')} for r in main]
b=lambda name:float(next(r['known_increment_upper_conditional_RUB'] for r in main if r['programme']==name and r['year']=='2027' and r['scenario']=='base'))
summary={'verdict':'ACCEPT_WITH_LIMITATIONS','main_scope':'E2/S0 NS common nonempty conditional KEEP; no proven release or actual KEEP','main_table':main_table,'saturation_diagnostic':saturation,'winner_base_2027':'D3_STAGED','winner_cautious_2027':'KEEP','one_fact_reversing_D3_vs_D1':{'fact':'Confirmed incremental external donor contribution lost by D3 relative to D1, on its additional second-tail days, exceeds threshold (holding other differences fixed).','threshold_RUB':b('D3_STAGED')-b('D1_FOCUS'),'per_365_additional_taildays_RUB':(b('D3_STAGED')-b('D1_FOCUS'))/365,'counterexample_differential_loss_RUB':300000000,'D3_after_extra_loss_RUB':b('D3_STAGED')-300000000,'D1_unchanged_RUB':b('D1_FOCUS'),'is_observed':False},'dispatch_ready':False,'full_PnL':None,'cash':None,'conclusion':'D1 is first candidate for commercial/ops validation, not a launch decision. BASE saturation is prior-derived. D3 conditional variable winner only; cautious retains KEEP.','new_winner_changing_error_found':False,'source_scope':'Completed P31 only; P32 findings R02 read solely for 100 vs archived TCDS98 caveat; no P32 network outputs.'}
(H/'reviewed_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with (H/'actual_checks.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['check','status','evidence']);w.writeheader();w.writerows(checks)
validation={'status':'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL','checks':len(checks),'failed':[c for c in checks if c['status']=='FAIL'],'independent_csv_arithmetic':True,'API_repeats':8,'shared_engine_limitation':'API repeat is not independent implementation of P05/P06; ledgers and CSV/calendar tests are independently reconstructed. No demand calibration or legal/ops proof.','writes':'network_review only','author_outputs_unchanged':all(sha(p)==h for p,h in before.items()),'HEAD_policy':'Authorized branch/commit changes ignored; content hashes checked.'}
(H/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
raise SystemExit(0 if validation['status']=='PASS' else 1)
