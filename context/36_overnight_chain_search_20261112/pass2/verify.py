#!/usr/bin/env python3
"""Verify actual generated artifacts, repeat once, exercise joint adapter seams.

Only writes validation/run log under HERE. No old builders/verify are invoked.
"""
import sys
sys.dont_write_bytecode=True
import copy
import csv
import hashlib
import importlib.util
import json
import subprocess
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(n):return list(csv.DictReader((HERE/n).open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b,tol=.003):assert abs(float(a)-float(b))<tol,(a,b)
CHECKS={}
def check(n,f):
    f();CHECKS[n]='PASS'

def unchanged():
    m=json.loads((HERE/'input_manifest.json').read_text())
    p=json.loads((ROOT/m['protected_hash_file']).read_text())
    assert len(p)==1418
    for path,h in p.items():assert sha(ROOT/path)==h,path
    for key in ('completed_guard','read_sources'):
        for path,h in m[key].items():assert sha(ROOT/path)==h,path

check('protected1418_completed_pass1_and_research_before',unchanged)
OUTPUTS=[p for p in HERE.iterdir() if p.suffix in ('.csv','.json','.md') and p.name!='validation.json']
before={p.name:sha(p) for p in OUTPUTS}
run=subprocess.run([sys.executable,'-B',str(HERE/'calculate.py')],cwd=ROOT,text=True,capture_output=True)
(HERE/'run_log.txt').write_text('Deterministic repeat command: '+sys.executable+' -B '+str(HERE/'calculate.py')+'\nexit='+str(run.returncode)+'\n'+run.stdout+run.stderr)
assert run.returncode==0,run.stderr
after={p.name:sha(p) for p in OUTPUTS}
assert before==after,{k:(before[k],after[k]) for k in before if before[k]!=after[k]}
CHECKS['actual_initial_run_plus_one_byte_deterministic_repeat']='PASS'

s=importlib.util.spec_from_file_location('p36_verified_second_pass',HERE/'calculate.py')
M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
cr=read('candidate_results.csv');states=read('three_state_comparison.csv')
sales=read('directional_sales_ledger.csv');ledger=read('revenue_cost_ledger.csv')
coverage=json.loads((HERE/'coverage_delta.json').read_text())
finals=coverage['finalists']
st={(r['candidate_id'],r['scenario'],r['state']):r for r in states}
by_sales=defaultdict(list);by_ledger=defaultdict(list)
for r in sales:by_sales[r['candidate_id'],r['scenario'],r['state']].append(r)
for r in ledger:by_ledger[r['candidate_id'],r['scenario'],r['state']].append(r)

def coverage_check():
    shortlist=list(csv.DictReader((M.P1/'shortlist.csv').open()))
    ids={r['candidate_id'] for r in cr}
    assert len(shortlist)==36 and 36<=len(ids)<=60 and len(ids)==coverage['detailed_candidates'] and all(r['candidate_id'] in ids for r in shortlist)
    assert len(states)==len(ids)*6
    for c in ids:
        for sc in ('base','cautious'):assert all((c,sc,x) in st for x in ('KEEP','WITHOUT_NEW','REPLACE'))
    mandatory=['X_AER1','X_AER2','X_AER_MRV','X_MRV_AER','X_SVX_KJA','X_SVX_IKT','X_GOJ_KJA_F','X_GOJ_KJA_R','X_TJM_MRV_F','X_TJM_MRV_R','X_CEK_MRV_F','X_CEK_MRV_R','X_GOJ_TOF_F','X_GOJ_TOF_R']
    assert all(x in ids for x in mandatory)
    assert coverage['all_shortlist_evaluated'] and coverage['no_global_optimum']
check('36_representatives_plus_bounded_leaders_and_required_closed_controls',coverage_check)

def same_fleet_and_deltas():
    for r in cr:
        key=r['candidate_id'],r['scenario'];ss=[st[key+(x,)] for x in ('KEEP','WITHOUT_NEW','REPLACE')]
        assert len({(x['cohort_key'],x['working_tails'],x['tail_positions'],x['seats_scenario']) for x in ss})==1
        k,w,p=[float(x['known_subtotal_before_C_D_F']) for x in ss]
        close(w-k,r['old_change_minus_KEEP_before_C']);close(p-w,r['new_minus_same_WITHOUT_NEW']);close(p-k,r['REPLACE_minus_KEEP_before_C_D_F'])
        close(float(r['old_change_minus_KEEP_before_C'])+float(r['new_minus_same_WITHOUT_NEW']),r['REPLACE_minus_KEEP_before_C_D_F'])
        # Unknown opportunity and fixed salaries are never silently 0.
        assert all(x['actual_outside_D']=='NULL' and x['fullPnL']=='NULL' and x['cash']=='NULL' for x in ss)
        assert ss[1]['cancellation_C']==ss[2]['cancellation_C']=='NULL'
check('three_states_same_fleet_identity_no_double_donor_UNKNOWN_not_zero',same_fleet_and_deltas)

def ledgers():
    for r in states:
        key=r['equivalent_ledger_candidate'],r['scenario'],r['equivalent_ledger_state']
        ll=by_ledger[key];ss=by_sales[key]
        close(sum(float(x['net_revenue']) for x in ss),r['net_revenue'])
        close(sum(float(x['revenue_once_allocated']) for x in ll),r['net_revenue'])
        close(sum(float(x['avoidable_variable_scenario']) for x in ll),r['avoidable_variable_scenario'])
        close(sum(float(x['monthly_journeys']) for x in ss),r['rw_journeys'])
        assert len(ll)==int(r['flights_month'])
    through_count=0
    for r in ledger:
        assert r['origin']!=r['destination'] and r['origin']!='MOW' and r['destination']!='MOW'
        assert M.RE.city(r['origin'])!=M.RE.city(r['destination'])
        assert float(r['total_segment_q'])<=float(r['seats'])+1e-6
        close(float(r['direct_q'])+float(r['through_segment_q']),r['total_segment_q'])
        assert float(r['support'])==float(r['cargo'])==float(r['lease_avoided'])==0
        assert float(r['fixed_crew_excluded'])>0
        if r['kind']=='positioning':assert float(r['seats'])==float(r['total_segment_q'])==float(r['revenue_once_allocated'])==0
    for key,ss in by_sales.items():
        fs=by_ledger[key]
        freq=Counter((r['origin'],r['destination']) for r in fs)
        fby={r['flight_id']:r for r in fs}
        pools=defaultdict(float)
        for r in ss:
            assert r['city_od'].startswith('CITY:') and all(x not in r['city_od'] for x in ('DME','ZIA'))
            if r['product_kind']=='DIRECT':
                f=fby[r['legs']];close(r['frequency_week'],freq[f['origin'],f['destination']]/4,1e-6)
            else:
                through_count+=1;assert len(r['legs'].split(';'))==2
            close(float(r['monthly_journeys'])*float(r['net_fare']),r['net_revenue'])
            pools[r['city_od']]+=float(r['monthly_journeys'])
        for od,q in pools.items():
            a,b=od.removeprefix('CITY:').split('>')
            annual,_,_=M.RE.annual(a,b,key[1],2027)
            pot=annual*.5*M.RE.P05.monthly_profile(2027)[2]/.6
            assert q<=pot+1e-4,(key,od,q,pot)
    assert through_count>0
check('physical_capacity_city_OD_monthly_pool_once_revenue_once_ferry0_support_cargo0',ledgers)

def old_actions():
    for a in read('old_assignment_actions.csv'):
        for state in ('KEEP','WITHOUT_NEW','REPLACE'):
            sr=st[a['candidate_id'],a['scenario'],state]
            key=sr['equivalent_ledger_candidate'],a['scenario'],sr['equivalent_ledger_state']
            xs=[r for r in by_ledger[key] if r['job_id']==a['old_assignment_id']]
            close(sum(float(r['revenue_once_allocated']) for r in xs),a[state+'_revenue'])
            close(sum(float(r['avoidable_variable_scenario']) for r in xs),a[state+'_variable_cost'])
            if a['action']=='REMOVE' and state!='KEEP':assert not xs
        assert a['actual_old_profit']==a['actual_outside_D']=='NULL'
check('all_old_stable_IDs_actions_and_joint_revenue_costs',old_actions)

def old_selection():
    scans=read('without_new_state_screen.csv');selected=read('without_new_screen_selection.csv')
    assert len(scans)==314
    for x in selected:
        assert float(x['screen'])==max(float(r['known_subtotal']) for r in scans if r['scenario']==x['scenario'])
        close(x['screen'],st[x['candidate'],x['scenario'],'WITHOUT_NEW']['known_subtotal_before_C_D_F'])
check('best_WITHOUT_NEW_over157_existing_removal_sets_exact_P06_seam',old_selection)

def calendars():
    monthly=read('final3_monthly_schedule.csv');weekly=read('final3_weekly_schedule.csv')
    for cid in finals:
        for state in ('KEEP','WITHOUT_NEW','REPLACE'):
            seqs=defaultdict(list)
            for r in monthly:
                if (r['candidate_id'],r['state'])==(cid,state):seqs[r['tail']].append(r)
            assert set(seqs)<=set(('T1','T2')) and 'R1_UNRELEASED' not in seqs
            for tail,seq in seqs.items():
                seq.sort(key=lambda r:r['departure_utc']);pos='SVX';ready=datetime(2027,2,1,tzinfo=timezone.utc)
                for r in seq:
                    dep=datetime.fromisoformat(r['departure_utc']);arr=datetime.fromisoformat(r['arrival_utc'])
                    assert pos==r['origin'] and dep>=ready
                    assert dep>=M.EPOCH and arr<=M.EPOCH+timedelta(days=28)
                    assert datetime.fromisoformat(r['departure_local'])==dep and datetime.fromisoformat(r['arrival_local'])==arr
                    close((arr-dep).total_seconds()/60,r['block_minutes']);pos=r['destination'];ready=arr+timedelta(minutes=60)
                assert pos=='SVX'
            cnt=Counter(r['flight_id'].rsplit('/W',1)[0] for rs in seqs.values() for r in rs)
            assert set(cnt.values())=={4}
            for tail in ('T1','T2'):
                days={int(r['iso_departure_weekday']) for r in weekly if r['candidate_id']==cid and r['state']==state and r['tail']==tail and r['kind']=='DAY_POSITION_NOT_A_FLIGHT'}
                assert days==set(range(1,8))
    assert any(r['position_before'].startswith('IN_FLIGHT:') for r in weekly if r['kind']=='DAY_POSITION_NOT_A_FLIGHT')
    for r in cr:
        if r['candidate_id'] in finals:assert float(r['max_daily_BH'])<=8+1e-6 and r['setup'] in ('B2S','B2T')
check('complete_4_repeats_7_days_positions_turn60_timezones_reserve_and_8BH_separate',calendars)

def fixture_flights(pa='SVX',pb='AER',tail='T1',prefix='FIX'):
    out=[]
    for week in range(4):
        dep=M.EPOCH+timedelta(days=7*week,hours=6);h=M.P34.block(pa,pb)/60
        out.append(dict(flight_instance_id=prefix+str(week),pattern_id='NEW-FIX',origin_airport=pa,destination_airport=pb,
            departure_utc=dep.isoformat(),arrival_utc=(dep+timedelta(hours=h)).isoformat(),saleable_seats=100,
            block_hours_costscreen=h,tail_id=tail,calendar_kind='service'))
    return out

def adapter_fixtures():
    # One dated departure in each of four weeks is 1/week, never .25/week.
    fs=fixture_flights();world={('SVX','AER'),('AER','SVX')}
    b=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False)
    rw=[p for p in b['products'] if p['owner']=='RW']
    assert len(rw)==4 and all(p['frequency']==1 for p in rw)
    # DME and ZIA share exactly one forward MOW pool and its one potential.
    mf=fixture_flights('DME','GOJ','T1','DME')+fixture_flights('ZIA','GOJ','T2','ZIA')
    mw={('MOW','GOJ'),('GOJ','MOW')}
    bm=M.make_choice(mf,'base',mw,M.START,M.END,world=mw,through=False)
    assert len(bm['markets'])==2 and len({m['demand_pool_id'] for m in bm['markets']})==2
    ma=M.RE.allocate_p06(bm,bm['products'])
    assert sum(a['carried'] for a in ma['allocations'])<=sum(m['potential_journeys'] for m in bm['markets'])
    # Directional and day stress preserve the monthly two-direction potential.
    total=sum(m['potential_journeys'] for m in b['markets'])
    for split in (.35,.65):
        bb=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False,direction_split=split)
        close(sum(m['potential_journeys'] for m in bb['markets']),total)
        pots={m['demand_pool_id']:m['potential_journeys'] for m in bb['markets']}
        assert abs(pots['CITY:AER>SVX']/total-split)<1e-9
    for day in (-.5,0,.5):
        bb=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False,day_stress=day)
        close(sum(m['potential_journeys'] for m in bb['markets']),total)
        assert len(bb['markets'])==14
    # Raise price sufficiently: MNL must lose passengers, not keep full100.
    b2=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False,fare_scale=2)
    q1=sum(a['carried'] for a in M.RE.allocate_p06(b,b['products'])['allocations'] if a['owner']=='RW')
    q2=sum(a['carried'] for a in M.RE.allocate_p06(b2,b2['products'])['allocations'] if a['owner']=='RW')
    assert q2<q1
    # Explicit identity and new-vs-remove tests on real old programme seam.
    c=dict(setup_id='B2T',changed_old_jobs=M.SETUPS['B2T']['jobs'],new_jobs=[])
    M.WORLDS[M.cohort_key(c)]=M.directions(c['changed_old_jobs'])
    k=M.evaluate(c,'base','KEEP');w=M.evaluate(c,'base','WITHOUT_NEW');p=M.evaluate(c,'base','REPLACE')
    close(k['known_contribution'],w['known_contribution']);close(w['known_contribution'],p['known_contribution'])
    c['changed_old_jobs']=c['changed_old_jobs'][1:]
    w=M.evaluate(c,'base','WITHOUT_NEW');p=M.evaluate(c,'base','REPLACE')
    close(w['known_contribution'],p['known_contribution'])
    # Exact-event adapter refuses an impossible position, never trims a flight.
    req=M.request(M.SETUPS['B2T']['jobs'],M.SETUPS['B2T'])
    req=copy.deepcopy(req);req['exact_jobs'][0]['flights'][0]['origin']='DME'
    try:M.event_calendar(req)
    except ValueError:pass
    else:raise AssertionError('phantom starting location accepted')
    req=M.request(M.SETUPS['B2T']['jobs'],M.SETUPS['B2T']);req=copy.deepcopy(req)
    first,second=req['exact_jobs'][0]['flights']
    second['dep']=first['arr']+45;second['arr']=second['dep']+second['block']
    try:M.event_calendar(req)
    except ValueError:pass
    else:raise AssertionError('inside-job turn45 accepted despite turn60 contract')
check('frequency1_fixture_MOW_shared_pool_day_direction_conservation_price_MNL_identity_adapter_reject',adapter_fixtures)

def contract_capacity_fixture():
    fs=fixture_flights();world={('SVX','AER'),('AER','SVX')}
    bun=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False)
    direct=next(p for p in bun['products'] if p['owner']=='RW')
    cp=dict(direct,product_id='BLOCK_FIX',contract_only=True,net_fare=0)
    bun['products'].append(cp)
    bun['contracts']=[dict(contract_id='CID',product_id='BLOCK_FIX',reserved_seats=20,carried=10,release_unused=False,
        payment_mode='block',economic_event_id='PAY',assumption_id='FIXTURE')]
    bun['economic_events']=[dict(economic_event_id='PAY',category='revenue',owner='CID')]
    alloc=M.RE.allocate_p06(bun,bun['products'])
    seat=next(r for r in alloc['seats'] if r['flight_instance_id']==direct['legs'][0])
    assert seat['unfilled_contract_seats']==10 and seat['carried_segments']<=90+1e-6
    cp['net_fare']=1
    try:M.RE.allocate_p06(bun,bun['products'])
    except Exception as e:assert 'duplicate revenue' in str(e)
    else:raise AssertionError('block plus ticket revenue accepted')
check('P06_contract_capacity_and_double_revenue_rejection_fixture',contract_capacity_fixture)

def delays():
    rows=read('delay_propagation.csv');groups=defaultdict(list)
    for r in rows:
        key=(r['candidate_id'],r['injection_flight'],r['hold_minutes'],r['turn_minutes'])
        groups[key].append(r)
        dep=datetime.fromisoformat(r['actual_departure_utc']);arr=datetime.fromisoformat(r['actual_arrival_utc'])
        assert datetime.fromisoformat(r['ready_after_utc'])==arr+timedelta(minutes=int(r['turn_minutes']))
        assert dep>=datetime.fromisoformat(r['ready_before_utc'])
        assert r['minute_cost']=='NULL'
    for key,rs in groups.items():
        for a,b in zip(rs,rs[1:]):
            assert a['position_after']==b['position_before']
            assert datetime.fromisoformat(b['actual_departure_utc'])>=datetime.fromisoformat(a['ready_after_utc'])
    assert any(r['day_crossed']=='True' and float(r['delay_vs_turn_case_minutes'])>0 for r in rows)
    for cid in finals:
        assert {r['turn_minutes'] for r in rows if r['candidate_id']==cid}=={'60','90'}
        assert {r['hold_minutes'] for r in rows if r['candidate_id']==cid}=={'30','60','120'}
        for stt in ('NEW','NEAREST_RETAINED'):assert any(r['candidate_id']==cid and r['injection_kind']==stt for r in rows)
check('delays_30_60_120_turn60_90_positions_ready_next_day_no_midnight_reset',delays)

def structural():
    proof=json.loads((HERE/'structural_cautious_assessment.json').read_text())
    assert proof['edges']==238 and proof['original_all_full100_negative'] and proof['adjusted_all_full100_negative']
    close(proof['AER']['original_P31_cost'],1568509.4)
    close(proof['AER']['avoidable_variable_cost'],1491509.4)
    assert proof['base_landed']==136300+1696 and proof['cautious_landed']==161696
    assert proof['joint_cautious_largest_new_minus_same_without']<0 and not proof['joint_cautious_positive_new_cases']
    for r in read('resource_cases.csv'):
        assert r['SJ_PD8_cost']=='NULL' and r['RRJ_analogy_admitted']=='False'
        if r['month']=='2027-02':assert r['scenario_postentry_available']=='0'
    for r in read('top5_pairs.csv'):assert 'UNPROVED' in r['actual_newness']
check('cautious_structural_units_fixedcrew_uplift_once_joint_and_resource_entry_gates',structural)
check('protected1418_completed_pass1_and_research_after',unchanged)

result=dict(status='PASS',checks=CHECKS,initial_and_repeat_actual_runs=2,deterministic_files=len(before),
    code_sha256={'calculate.py':sha(HERE/'calculate.py'),'verify.py':sha(HERE/'verify.py')},
    generated_artifact_sha256=after,
    protected_files=1418,completed_P36_and_pass1_unchanged=True,fullPnL=None,cash=None,dispatch_approval=None,
    candidate_count=coverage['detailed_candidates'],finalists=finals,artifact_bytes=sum(p.stat().st_size for p in HERE.iterdir() if p.is_file()),
    limitations='Scenario model; observed OD/netfare, actual old profit/C/D/F, marketed own inventory, crew/slots/AFM/MRO/resource release UNKNOWN.')
(HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
