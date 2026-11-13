#!/usr/bin/env python3
"""Verify P38 without running any previous builder/verify/exporter.

Only validation.json in this directory is written. Python standard library.
"""
import sys
sys.dont_write_bytecode=True
import copy
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import month_adapter as M

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CHECKS=[]
RECEIPTS={}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def digest(x):
    return sha(json.dumps(x,sort_keys=True,separators=(',',':')).encode())

def read(name):
    with (HERE/name).open(newline='') as f:
        return list(csv.DictReader(f))

def js(name):
    return json.loads((HERE/name).read_text())

def check(name,fn):
    try:
        result=fn()
        CHECKS.append(dict(name=name,status='PASS'))
        if result is not None:
            RECEIPTS[name]=result
    except Exception as e:
        CHECKS.append(dict(name=name,status='FAIL',error=type(e).__name__+': '+str(e)))

def raises(fn,part):
    try:
        fn()
    except ValueError as e:
        assert part in str(e),(part,str(e))
        return str(e)
    raise AssertionError('expected rejection: '+part)

def guard():
    g=js('source_manifest.json')['guard']
    registered=json.loads((ROOT/g['registry']).read_text())
    immutable={p:h for p,h in registered.items() if not any(x in p.lower() for x in ('delegation','tasklog','task_log'))}
    actual={p:sha((ROOT/p).read_bytes()) for p in immutable}
    assert len(registered)==1621 and len(immutable)==1614
    assert actual==immutable
    assert digest(actual)==g['immutable_digest']
    return dict(registry_total=len(registered),immutable_verified=len(actual),
        mutable_metadata_excluded=7,immutable_digest=digest(actual))

def sources():
    man=js('source_manifest.json')
    for name,expected in man.get('artifact_sha256',{}).items():
        assert sha((HERE/name).read_bytes())==expected,'artifact changed: '+name
    for r in man['sources']:
        b=subprocess.check_output(['git','show',r['git_sha']+':'+r['path']]) if r['git_sha'] else (ROOT/r['path']).read_bytes()
        assert sha(b)==r['sha256'],r['path']
        assert not any(x in r['path'].lower() for x in ('delegation','tasklog','task_log'))
    for g in man['runtime_groups']:
        p=ROOT/g['path']
        m={str(f.relative_to(ROOT)):sha(f.read_bytes()) for f in sorted(p.rglob('*'))
            if f.is_file() and f.suffix in g['extensions'] and '__pycache__' not in f.parts}
        assert len(m)==g['count'] and digest(m)==g['sha256'],g['path']
    return dict(exact_source_records=len(man['sources']),runtime_groups=len(man['runtime_groups']))

def universe():
    inv=read('programme_inventory.csv');pairs=read('pair_universe.csv')
    cr=M.read(M.P36/'pass2/candidate_results.csv')
    positive={r['candidate_id'] for r in cr if float(r['new_minus_same_WITHOUT_NEW'])>0}
    assert len(cr)==120 and len(inv)==60 and len(positive)==37
    assert {r['candidate_id'] for r in inv if r['positive_new_vs_same_without']=='True'}==positive
    physical=set()
    for cid in positive:
        for j in M.p36_weekly(cid,'REPLACE'):
            if j['id'].startswith('NEW-'):
                physical.update('-'.join(sorted((f['origin'],f['destination']))) for f in j['flights'])
    assert physical=={r['pair'] for r in pairs} and len(physical)==25
    assert {r['pair'] for r in pairs if r['classification']=='PAID_POSITIONING_ONLY'}=={'CEK-SVX','SVX-TJM'}
    assert len([r for r in pairs if r['old_top5']=='True'])==5
    assert {r['pair'] for r in pairs if r['codec_present']=='False'}=={'CEK-SVX','SVX-ZIA'}
    assert all(r['contract_codec_retained']=='True' for r in pairs)
    # Every reconstructed candidate/state uses exact completed event IDs,
    # including four deduplicated REPLACE aliases, not only beautiful winners.
    for r in inv:
        for state in ('KEEP','WITHOUT_NEW','REPLACE'):
            M.p36_weekly(r['candidate_id'],state)
    return dict(programmes=60,positive=37,physical_pairs=25,old_top5=5,
        positioning_only=['CEK-SVX','SVX-TJM'],legacy_P31_missing=['CEK-SVX','MOW-SVX'],
        contract_keeps_all_physical_pairs=True)

def monthly_sources():
    a=read('monthly_input_audit.csv')
    assert all(r['endpoint_OD_admitted']=='False' for r in a)
    assert next(r for r in a if r['kind']=='ENDPOINT_OD')['value']=='0'
    counts=Counter(r['kind'] for r in a)
    assert counts['CARRIER_PROFILE']==counts['AIRPORT_PROFILE']==12
    assert counts['ALTERNATIVE_CARRIER_PROFILE']==9
    # Verify exact physical CSV line, cell/value/period, not an acceptance label.
    for r in a:
        gitsha,path,line=r['source'].split(':')
        text=subprocess.check_output(['git','show',gitsha+':'+path],text=True)
        if r['observation_id']=='FILE_SUMMARY':
            assert len(list(csv.DictReader(text.splitlines())))==int(r['value'])
        else:
            header=text.splitlines()[0]
            one=list(csv.DictReader([header,text.splitlines()[int(line)-1]]))[0]
            assert one['value']==r['value']
            if one.get('observation_id'):
                assert one['observation_id']==r['observation_id']
    return dict(snapshot_rows=len(a),counts=dict(counts),new_endpoint_OD_admission=0)

def calendar12():
    e=[M.exposure(2027,m) for m in range(1,13)]
    assert sum(x['days'] for x in e)==365
    for x in e:
        assert sum(x['iso_weekday_counts'].values())==x['days']
        assert set(x['iso_weekday_counts'].values())<={4,5}
    assert list(e[1]['iso_weekday_counts'].values())==[4]*7
    assert e[0]['iso_weekday_counts']==dict(zip(map(str,range(1,8)),[4,4,4,4,5,5,5]))
    assert e[6]['iso_weekday_counts']==dict(zip(map(str,range(1,8)),[4,4,4,5,5,5,4]))
    c=M.cohort(2)
    for m in range(1,13):
        cal=M.calendar_events(c['jobs'],c['tails'],2027,m)
        assert {f['tail'] for f in cal['flights']}=={'T1','T2'}
        assert cal['reserve']==['R1']
        assert len({f['flight_id'] for f in cal['flights']})==len(cal['flights'])
        assert all(f['departure_local'] and f['arrival_local'] and 1<=f['local_iso_weekday']<=7 for f in cal['flights'])
        # UTC departure assignment, not a 4x copy of February.
        assert all(f['departure_utc'].startswith(f'2027-{m:02}') for f in cal['flights'])
        e[m-1]['B2_old_departures']=len(cal['flights'])
    return e

def profile_once():
    re=M.engine();profile=re.P05.monthly_profile(2027)
    snap=js('common_contract.json')['demand']['profile_snapshot']['rows']
    assert math.isclose(sum(profile.values()),1,abs_tol=1e-12)
    assert all(math.isclose(profile[r['month']],r['share_2027'],abs_tol=1e-12) for r in snap)
    q=re.annual('SVX','KJA','base',2027)[0]
    annual=0
    for m in range(1,13):
        s,e=M.bounds(2027,m)
        b=re.choice_bundle([],'base',{('SVX','KJA')},s.date().isoformat(),(e-timedelta(days=1)).date().isoformat())
        pot=b['markets'][0]['potential_journeys'];annual+=pot
        assert math.isclose(pot,q*.5*profile[m]/.6,abs_tol=1e-8)
    assert math.isclose(annual,q*.5/.6,abs_tol=1e-8)
    jan_total=q*.5*profile[1]/.6
    jan=M.pool_days(jan_total,2027,1,{f'2027-01-{d:02}':2 for d in range(1,9)})
    assert len(jan)==31 and math.isclose(sum(jan.values()),jan_total,abs_tol=1e-8)
    assert jan['2027-01-01']>jan['2027-01-15']
    return dict(profile_sum=sum(profile.values()),annual_directed_pool=annual,
        Jan_holiday_pool_unchanged=True,month_number_not_season_index=True)

def resource_guards():
    c=M.cohort(2)
    out={}
    out['missing_T2']=raises(lambda:M.calendar_events(c['jobs'],[t for t in c['tails'] if t['id']!='T2'],2027,2),'MISSING_WORKING_RESOURCE')
    bad=copy.deepcopy(c['jobs']);bad[0]['flights'][0]['tail']='R1'
    out['reserve_work']=raises(lambda:M.calendar_events(bad,c['tails'],2027,2),'RESERVE_USED_AS_WORKING')
    out['duplicate_oldjob']=raises(lambda:M.calendar_events(c['jobs']+c['jobs'],c['tails'],2027,2),'duplicate template flight')
    out['no_reserve']=raises(lambda:M.calendar_events(c['jobs'],[t for t in c['tails'] if t['id']!='R1'],2027,2),'separate explicit reserve')
    for k in (1,2,3):
        co=M.cohort(k);states={s:co['jobs'] for s in ('KEEP','WITHOUT_NEW','REPLACE')}
        z=M.evaluate_month(states,co['tails'],2027,2)
        assert abs(z['total_minus_keep'])<1e-8 and z['working_tails']==k
        assert z['fullPnL'] is None
        if k==3:
            assert z['old_D3'] is None
        out['K'+str(k)]=dict(old_jobs=len(co['jobs']),working=k,reserve='R1',total_minus_keep=z['total_minus_keep'],D3=z['old_D3'])
    assert M.cohort(2)['jobs']==M.cohort(3)['jobs']
    assert len(M.cohort(1)['jobs'])==11 and len(M.cohort(2)['jobs'])==15
    sj=copy.deepcopy(c['tails']);sj[0]['type']='SJ-100-PD8';sj[0]['available_from']='2027-08-01T00:00:00Z'
    out['SJ_before_entry']=raises(lambda:M.calendar_events(c['jobs'],sj,2027,2),'AVAILABILITY')
    out['PD8_cost']=raises(lambda:M.evaluate_month({s:c['jobs'] for s in ('KEEP','WITHOUT_NEW','REPLACE')},sj,2027,8),'PD8 economics UNKNOWN')
    return out

def boundary():
    # An explicit closed Sunday->Monday job crossing 31Jan/1Feb, including an
    # in-flight tail at month boundary. No month-end position reset allowed.
    dep=6*1440+23*60+30
    fs=[dict(flight_id='BOUND/L1',job_id='BOUND',tail='T1',origin='SVX',destination='GOJ',
             dep=dep,arr=dep+100,block=100,kind='SERVICE'),
        dict(flight_id='BOUND/L2',job_id='BOUND',tail='T1',origin='GOJ',destination='SVX',
             dep=dep+160,arr=dep+260,block=100,kind='SERVICE')]
    jobs=[dict(id='BOUND',tail='T1',flights=fs)];tails=M.resources({'T1':'SVX'})
    jan=M.calendar_events(jobs,tails,2027,1);feb=M.calendar_events(jobs,tails,2027,2)
    assert jan['carry']['T1/end']==feb['carry']['T1/start']
    assert jan['carry']['T1/end']['position']=='IN_AIR:SVX>GOJ'
    assert len(jan['flights'])==9 and len(feb['flights'])==8
    assert len(feb['boundary_flights'])==1
    return dict(Jan_departures=9,Feb_departures=8,carry=jan['carry']['T1/end'],
        no_phantom_return_or_extra_tail=True)

def joint_and_inverse():
    states={s:M.p36_weekly('X_SVX_KJA',s) for s in ('KEEP','WITHOUT_NEW','REPLACE')}
    tails=M.resources({'T1':'SVX','T2':'SVX'})
    outputs=[]
    for month in range(1,13):
        # 12 complete monthly reruns plus necessary inverse OD, not a capacity forecast.
        z=M.evaluate_month(states,tails,2027,month,full=True)
        for s,x in z['results'].items():
            assert all(len(p['legs'])==1 for p in x['bundle']['products'] if p['owner']=='RW')
            assert x['allocation']['allocations']
            pots={(m['demand_pool_id'],m['month'],m['customer_segment']):m['potential_journeys'] for m in x['bundle']['markets']}
            carried=Counter()
            for a in x['allocation']['allocations']:
                carried[a['demand_pool_id'],a['month'],a['customer_segment']]+=a['carried']
            assert all(carried[k]<=v+1e-6 for k,v in pots.items())
        inverse=M.inverse_od({'KJA':states},'KJA',tails,2027,month,'base',[('SVX','KJA')],iterations=12)
        assert inverse['status']=='BRACKETED_CONDITIONAL_CROSSING'
        assert inverse['bracket_margins'][0]<=0<inverse['bracket_margins'][1]
        outputs.append(dict(month=z['month'],new_minus_same_without=z['new_minus_same_without'],
            departures=z['states']['REPLACE']['departures'],
            conditional_directed_potential=inverse['required_directed_monthly_potential'],
            required_change_from_prior_fraction=inverse['required_change_from_prior_fraction'],
            inverse_basis='joint against identical KEEP/WITHOUT_NEW; omitted actual costs UNKNOWN'))
    # Explicit 2-leader + AER-control alternative menu for a real envelope test.
    menu={'KJA':states}
    for name,cid in [('IKT','X_SVX_IKT'),('AER_CONTROL','C0121799')]:
        menu[name]={s:M.p36_weekly(cid,s) for s in states}
    inv=M.inverse_od(menu,'KJA',tails,2027,2,'base',[('SVX','KJA')],iterations=12)
    caution=M.evaluate_month(states,tails,2027,2,'cautious')
    assert caution['new_minus_same_without']<0
    return dict(months=outputs,Feb_against_bounded_alternative_menu=inv,
        Feb_cautious_new_delta=caution['new_minus_same_without'],through_products_primary=0,
        no_observed_OD_or_forecast_claim=True)

def mow_shared():
    # Same city OD served by two separate physical airports and tails.
    jobs=[]
    for n,airport in enumerate(('DME','ZIA'),1):
        dep=(n-1)*1440+600
        fs=[dict(flight_id=f'MOW{n}/L1',job_id=f'MOW{n}',tail=f'T{n}',origin=airport,destination='GOJ',dep=dep,arr=dep+100,block=100,kind='SERVICE'),
            dict(flight_id=f'MOW{n}/L2',job_id=f'MOW{n}',tail=f'T{n}',origin='GOJ',destination=airport,dep=dep+160,arr=dep+260,block=100,kind='SERVICE')]
        jobs.append(dict(id=f'MOW{n}',tail=f'T{n}',flights=fs))
    z=M.evaluate_month(dict(KEEP=[],WITHOUT_NEW=[],REPLACE=jobs),M.resources({'T1':'DME','T2':'ZIA'}),2027,7,full=True)
    b=z['results']['REPLACE']['bundle'];pools={m['demand_pool_id'] for m in b['markets']}
    assert pools=={'CITY:MOW>GOJ','CITY:GOJ>MOW'}
    assert {f['origin_airport'] for f in b['flights']}>={'DME','ZIA'}
    for pool in pools:
        potential=next(m['potential_journeys'] for m in b['markets'] if m['demand_pool_id']==pool)
        carried=sum(a['carried'] for a in z['results']['REPLACE']['allocation']['allocations'] if a['demand_pool_id']==pool)
        assert carried<=potential+1e-6
    return dict(physical_airports=['DME','ZIA'],directed_city_pools=sorted(pools),monthly_OD_not_duplicated=True)

def units_p37():
    re=M.engine();out={}
    assert math.isclose(re.P05.net_fare(11000,.1,.03),9700,abs_tol=1e-9)
    assert re.P05.net_fare(10000,0,.03)==9700
    assert re.P05.net_fare(10000,None,.03) is None
    for sc in ('base','cautious'):
        gross,net=re.fare('SVX','KJA',sc)
        c=re.costs('SVX','KJA',sc,200/60)
        crew=(15000 if sc=='base' else 22000)*200/60
        cost=2*(c['fixed_cost']-crew)
        need=math.floor(cost/(2*net))+1
        assert need==(69 if sc=='base' else 115)
        assert math.isclose(c['fuel_cost'],c['fuel_t']*c['fuel_price'],abs_tol=1e-8)
        assert c['fuel_price']==(137996 if sc=='base' else 161696)
        out[sc]=dict(net_per_ticket=net,rotation_variable_cost=cost,
            balanced_minimum_strict_each_direction=need,capacity_feasible=need<=100,
            F_D_cannib_R1='UNKNOWN; zero only for this conditional lower bound')
    assert M.inverse_threshold(2*100*10000+1,10000,2)['capacity_possible'] is False
    return dict(P37=out,fuel_units='tonnes × landed RUB/tonne once',
        tax_bridge='scenario only; no automatic VAT or distribution removal from quotes',block_cargo_primary=0)

def output_scope():
    expected={'README.md','engine_handoff.md','case_requirements.csv','pair_universe.csv','programme_inventory.csv',
        'source_delta.csv','monthly_input_audit.csv','common_contract.json','resource_contract.json',
        'month_adapter.py','verify.py','validation.json','source_manifest.json'}
    current={p.name for p in HERE.iterdir() if p.is_file()}
    # This verifier creates validation.json after checking the other files.
    assert current-{'validation.json'}==expected-{'validation.json'},current^expected
    return dict(expected_files=len(expected),writes='validation.json only during this verification')

if __name__=='__main__':
    for name,fn in [('protected_before',guard),('source_hashes',sources),('universe_60_37_25',universe),
        ('monthly_input_lineage',monthly_sources),('calendar_12_months',calendar12),
        ('month_number_profile_once_and_Jan_pool',profile_once),('resource_and_K1_K2_K3_guards',resource_guards),
        ('week_month_boundary',boundary),('joint_12_months_and_inverse_OD',joint_and_inverse),
        ('MOW_shared_pool',mow_shared),('P37_and_primary_tax_fuel_units',units_p37),
        ('output_scope',output_scope),('protected_after',guard)]:
        check(name,fn)
    result=dict(status='PASS' if all(c['status']=='PASS' for c in CHECKS) else 'FAIL',
        checks=CHECKS,receipts=RECEIPTS,actual_market_acceptance=False,actual_dispatch=False,
        fullPnL=None,cash=None,scope='Contract verification, not optimization or forecast')
    (HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'],checks=CHECKS),ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='PASS' else 1)
