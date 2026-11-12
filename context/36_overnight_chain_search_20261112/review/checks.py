#!/usr/bin/env python3
"""Bounded independent acceptance. Imports pure API only; never runs builders/verify/main.
Independent CSV identities, costs, seat incidence and calendar recurrence.
Eight full API requests; targeted P06 reallocation fixtures, no search.
"""
import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,importlib.util,copy,traceback
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parent; P=R.parent/'pass2'; ROOT=R.parents[2]
def rows(name,base=P):return list(csv.DictReader((base/name).open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b,tol=.02):assert abs(float(a)-float(b))<=tol,(a,b,tol)
def dt(s):return datetime.fromisoformat(s)
checks={}; evidence={}
def test(name,fn):
    try:fn();checks[name]='PASS';print('PASS',name,flush=True)
    except Exception as e:checks[name]='FAIL';print('FAIL',name,repr(e),flush=True);traceback.print_exc()
protected=json.loads((R.parent/'protected_files.json').read_text())
manifest=json.loads((P/'input_manifest.json').read_text())
guards={**protected,**manifest['completed_guard'],**manifest['read_sources']}
guards.update({str(p.relative_to(ROOT)):sha(p) for p in P.iterdir() if p.is_file()})
baseline_actual={f:sha(ROOT/f) for f in guards}
manifest_mismatches={f:{'pinned':h,'review_start':baseline_actual[f]} for f,h in guards.items() if baseline_actual[f]!=h}
mutable_meta='context/36_overnight_chain_search_20261112/delegation.local.json'
evidence['preexisting_manifest_mismatches']=manifest_mismatches
print('Preexisting manifest mismatches:',json.dumps(manifest_mismatches),flush=True)
def unchanged():
    assert len(protected)==1418
    assert set(manifest_mismatches)<= {mutable_meta},manifest_mismatches
    for f,h in protected.items():assert sha(ROOT/f)==h,f
    for f,h in guards.items():
        if f!=mutable_meta:assert sha(ROOT/f)==h,f
        assert sha(ROOT/f)==baseline_actual[f],('changed during review',f)
test('protected_1418_and_completed_sources_before',unchanged)
spec=importlib.util.spec_from_file_location('review_pure_p36',P/'calculate.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
# No exporter/main/choose_candidates/legacy verify is called.
S=rows('three_state_comparison.csv'); C=rows('candidate_results.csv'); L=rows('revenue_cost_ledger.csv'); A=rows('directional_sales_ledger.csv')
st={(r['candidate_id'],r['scenario'],r['state']):r for r in S}
ll=defaultdict(list);aa=defaultdict(list)
for r in L:ll[r['candidate_id'],r['scenario'],r['state']].append(r)
for r in A:aa[r['candidate_id'],r['scenario'],r['state']].append(r)
def key(cid,sc,state):
    s=st[cid,sc,state];return s['equivalent_ledger_candidate'],sc,s['equivalent_ledger_state']
def ledger(cid,sc,state):return ll[key(cid,sc,state)]
finals=['C0121799','X_SVX_IKT','X_SVX_KJA']
coverage=json.loads((P/'coverage_delta.json').read_text())
M.WORLDS.update({k:{tuple(x.split('>')) for x in v} for k,v in coverage['worlds'].items()})
def ledgers():
    for r in S:
        k=key(r['candidate_id'],r['scenario'],r['state']);ls=ll[k];sales=aa[k]
        close(sum(float(x['net_revenue']) for x in sales),r['net_revenue'])
        close(sum(float(x['monthly_journeys']) for x in sales),r['rw_journeys'])
        close(sum(float(x['revenue_once_allocated']) for x in ls),r['net_revenue'])
        close(sum(float(x['avoidable_variable_scenario']) for x in ls),r['avoidable_variable_scenario'])
        close(float(r['net_revenue'])-float(r['avoidable_variable_scenario']),r['known_subtotal_before_C_D_F'])
        assert len(ls)==int(r['flights_month'])
        assert all(r[x]=='NULL' for x in ['fullPnL','cash','actual_outside_D','retiming_sales_loss','own_external_marketed_shift','F_station_position_overnight_parking_reserve_launch'])
    for k,sales in aa.items():
        seg=Counter();pool=Counter();byid={r['flight_id']:r for r in ll[k]};freq=Counter((r['origin'],r['destination']) for r in ll[k])
        for r in sales:
            q=float(r['monthly_journeys']);close(q*float(r['net_fare']),r['net_revenue']);pool[r['city_od']]+=q
            legs=r['legs'].split(';')
            for f in legs:seg[f]+=q
            if len(legs)==1:
                f=byid[legs[0]];close(r['frequency_week'],freq[f['origin'],f['destination']]/4)
            else:
                assert len(legs)==2
                f,g=map(byid.get,legs);h=M.P34.block(f['origin'],f['destination'])
                gap=(dt(g['departure_utc'])-dt(f['departure_utc'])).total_seconds()/60-h
                assert f['tail']==g['tail'] and f['destination']==g['origin'] and 60<=gap<=240
        for f,r in byid.items():
            close(seg[f],r['total_segment_q']);assert seg[f]<=float(r['seats'])+1e-6
        for p,q in pool.items():
            assert 'DME' not in p and 'ZIA' not in p
            a,b=p[5:].split('>');annual=M.RE.annual(a,b,k[1],2027)[0]
            assert q<=annual*.5*M.RE.P05.monthly_profile(2027)[2]/.6+1e-4
    evidence['ledger_scope']={'state_scenario_rows':len(S),'unique_ledgers':len(ll),'flight_rows':len(L),'sales_rows':len(A)}
test('all_six_state_scenario_ledgers_per_candidate_OD_frequency_seat_incidence_one_fare',ledgers)
def deltas():
    for r in C:
        ss=[st[r['candidate_id'],r['scenario'],x] for x in ['KEEP','WITHOUT_NEW','REPLACE']]
        assert len({tuple(s[x] for x in ['cohort_key','working_tails','tail_positions','seats_scenario']) for s in ss})==1
        k,w,p=[float(s['known_subtotal_before_C_D_F']) for s in ss]
        close(w-k,r['old_change_minus_KEEP_before_C']);close(p-w,r['new_minus_same_WITHOUT_NEW']);close(p-k,r['REPLACE_minus_KEEP_before_C_D_F'])
        assert ss[1]['cancellation_C']==ss[2]['cancellation_C']=='NULL'
    for r in rows('old_assignment_actions.csv'):
        for state in ['KEEP','WITHOUT_NEW','REPLACE']:
            fs=[f for f in ledger(r['candidate_id'],r['scenario'],state) if f['job_id']==r['old_assignment_id']]
            close(sum(float(f['revenue_once_allocated']) for f in fs),r[state+'_revenue']);close(sum(float(f['avoidable_variable_scenario']) for f in fs),r[state+'_variable_cost'])
            if r['action']=='REMOVE' and state!='KEEP':assert not fs
    scan=rows('without_new_state_screen.csv');assert len(scan)==314
    for r in rows('without_new_screen_selection.csv'):
        close(r['screen'],max(float(x['known_subtotal']) for x in scan if x['scenario']==r['scenario']))
    evidence['final_new_delta']={sc:{c:float(next(r for r in C if r['candidate_id']==c and r['scenario']==sc)['new_minus_same_WITHOUT_NEW']) for c in finals} for sc in ['base','cautious']}
test('same_park_old_IDs_no_double_donor_157_bounded_removals',deltas)
def costs():
    for r in L:
        sc=r['scenario'];h=M.P34.block(r['origin'],r['destination'])/60
        # Independent arithmetic from admitted scenario units.
        rate=137996 if sc=='base' else 161696
        burn=h*(1.55 if sc=='base' else 1.9)+(.2 if sc=='base' else .25)
        close(burn,r['fuel_t'],.00001)
        close(float(r['fuel_t'])*rate,r['fuel']);close(r['landed_fuel_rub_t'],rate)
        close(sum(float(r[x]) for x in ['fuel','variable_mro_scenario','navigation_scenario','ground_cycle_scenario','deice_scenario']),r['avoidable_variable_scenario'])
        close(h*(15000 if sc=='base' else 22000),r['fixed_crew_excluded'])
        assert all(float(r[x])==0 for x in ['support','cargo','lease_avoided'])
    bounds=rows('structural_cautious_bounds.csv');assert len(bounds)==238
    for r in bounds:
        h=float(r['block_minutes'])/60;t=h*1.9+.25;o=h*63000+155307;co=t*161696+o;net=float(r['cautious_netfare'])
        close(co,r['avoidable_variable_cost']);close(100*net-co,r['adjusted_full100_cap']);assert 100*net-co<0
        close((100*net-o)/t,r['fuel_break_even_full100']);close(co/100,r['netfare_min_full100'])
    evidence['structural_examples']=[r for r in bounds if (r['origin'],r['destination']) in [('SVX','AER'),('SVX','UFA')]]
    assert max(float(r['new_minus_same_WITHOUT_NEW']) for r in C if r['scenario']=='cautious')<0
test('cost_units_fixedcrew_excluded_238_cautious_bounds',costs)
monthly=rows('final3_monthly_schedule.csv')
def calendar():
    for cid in finals:
        for state in ['KEEP','WITHOUT_NEW','REPLACE']:
            for tail in ['T1','T2']:
                fs=sorted([r for r in monthly if (r['candidate_id'],r['state'],r['tail'])==(cid,state,tail)],key=lambda r:r['departure_utc'])
                if not fs:continue
                pos='SVX';ready=M.EPOCH;bh=Counter()
                for r in fs:
                    dep,arr=dt(r['departure_utc']),dt(r['arrival_utc']);assert r['origin']==pos and dep>=ready
                    close((arr-dep).total_seconds()/60,r['block_minutes']);assert arr<=M.EPOCH+timedelta(days=28)
                    for field,zone in [('departure','origin'),('arrival','destination')]:
                        t=dt(r[field+'_utc']).astimezone(ZoneInfo(r[zone+'_timezone']));assert t.isoformat()==r[field+'_local']
                    cur=dep
                    while cur<arr:
                        end=min(arr,cur.replace(hour=0,minute=0,second=0)+timedelta(days=1));bh[cur.date()]+=(end-cur).total_seconds()/3600;cur=end
                    pos=r['destination'];ready=arr+timedelta(minutes=60)
                assert pos=='SVX' and max(bh.values())<=8+1e-6
                assert dt(fs[0]['departure_utc'])+timedelta(days=28)>=ready
                cnt=Counter(r['flight_id'].rsplit('/W',1)[0] for r in fs);assert set(cnt.values())=={4}
                week=[r for r in fs if dt(r['departure_utc'])<M.EPOCH+timedelta(days=7)]
                assert dt(week[0]['departure_utc'])+timedelta(days=7)>=dt(week[-1]['arrival_utc'])+timedelta(minutes=60)
    weekly=rows('final3_weekly_schedule.csv')
    for cid in finals:
        for state in ['KEEP','WITHOUT_NEW','REPLACE']:
            for tail in ['T1','T2']:
                assert {int(r['iso_departure_weekday']) for r in weekly if (r['candidate_id'],r['state'],r['tail'],r['kind'])==(cid,state,tail,'DAY_POSITION_NOT_A_FLIGHT')}==set(range(1,8))
    evidence['calendar_scope']='All final3 states, both tails, four weeks, weekly and month-end circular readiness; initial readiness only scenario.'
test('all_final3_calendar_local_UTC_60turn_8BH_week_month_wrap',calendar)
def delays():
    groups=defaultdict(list)
    for r in rows('delay_propagation.csv'):groups[tuple(r[x] for x in ['candidate_id','injection_flight','hold_minutes','turn_minutes'])].append(r)
    for k,rs in groups.items():
        for i,r in enumerate(rs):
            scheduled=dt(r['scheduled_departure_utc']);ready=dt(r['ready_before_utc']);inj=int(k[2]) if r['downstream_flight_id']==k[1] else 0
            dep=max(scheduled+timedelta(minutes=inj),ready);assert dep==dt(r['actual_departure_utc'])
            duration=dt(r['scheduled_arrival_utc'])-scheduled;assert dep+duration==dt(r['actual_arrival_utc'])
            assert dep+duration+timedelta(minutes=int(k[3]))==dt(r['ready_after_utc'])
            if i:assert r['ready_before_utc']==rs[i-1]['ready_after_utc'] and r['position_before']==rs[i-1]['position_after']
            assert r['minute_cost']=='NULL'
    for cid in finals:assert {(k[2],k[3]) for k in groups if k[0]==cid}=={(h,t) for h in ['30','60','120'] for t in ['60','90']}
    evidence['delay_groups']=len(groups)
test('delay_recurrence_30_60_120_turn90_no_midnight_reset',delays)
# Reconstruct weekly exact jobs from saved dated inventory, independently of search selection.
def candidate(cid,sc='base',state='REPLACE'):
    groups=defaultdict(list)
    for r in ledger(cid,sc,state):
        dep=(dt(r['departure_utc'])-M.EPOCH).total_seconds()/60
        if dep>=10080:continue
        h=M.P34.block(r['origin'],r['destination'])
        groups[r['job_id']].append(dict(flight_id=r['flight_id'].rsplit('/W',1)[0],job_id=r['job_id'],tail=r['tail'],origin=r['origin'],destination=r['destination'],dep=dep,arr=dep+h,block=h,kind='PAID_FERRY' if r['kind']=='positioning' else 'SERVICE',evidence='review reconstruction'))
    jobs=[]
    for jid,fs in groups.items():
        fs.sort(key=lambda f:f['dep']);jobs.append(dict(id=jid,tail=fs[0]['tail'],origin=fs[0]['origin'],destination=fs[-1]['destination'],start=fs[0]['dep'],end=fs[-1]['arr'],flights=fs))
    setup=next(r['setup'] for r in C if r['candidate_id']==cid)
    return dict(setup_id=setup,changed_old_jobs=[j for j in jobs if not j['id'].startswith('NEW-')],new_jobs=[j for j in jobs if j['id'].startswith('NEW-')])
Z={}
def api():
    requests=[(c,s,'REPLACE') for c in finals for s in ['base','cautious']]+[('C0121723','base','WITHOUT_NEW'),('C0163363','cautious','WITHOUT_NEW')]
    for cid,sc,state in requests:
        z=M.evaluate(candidate(cid,sc,state),sc,state);Z[cid,sc,state]=z
        close(z['known_contribution'],st[cid,sc,state]['known_subtotal_before_C_D_F'])
        close(z['rw_journeys'],st[cid,sc,state]['rw_journeys']);print(' API',cid,sc,state,z['known_contribution'],flush=True)
    evidence['full_API_requests']=len(requests)
test('eight_pure_API_recalculations',api)
# Direct P06 seam with independent scalar transformations (no use of M.replay).
def bundle(cid,sc,state,through=True):
    fs=[]
    for r in ledger(cid,sc,state):
        h=M.P34.block(r['origin'],r['destination'])/60
        fs.append(dict(flight_instance_id=r['flight_id'],pattern_id=r['job_id'],origin_airport=r['origin'],destination_airport=r['destination'],departure_utc=r['departure_utc'],arrival_utc=(dt(r['departure_utc'])+timedelta(hours=h)).isoformat(),saleable_seats=float(r['seats']),block_hours_costscreen=h,calendar_kind=r['kind'],tail_id=r['tail']))
    world=M.WORLDS[st[cid,sc,state]['cohort_key']]
    return M.make_choice(fs,sc,world,M.START,M.END,world=world,through=through)
def alloc_value(b,cost,scale=1,fare=1):
    b=copy.deepcopy(b)
    for m in b['markets']:m['potential_journeys']*=scale
    ff={f['flight_instance_id']:f for f in b['flights']}
    for p in b['products']:
        if p['owner']=='RW' and any(ff[f]['pattern_id'].startswith('NEW-') for f in p['legs']):p['gross_fare']*=fare;p['net_fare']*=fare
    alloc=M.RE.allocate_p06(b,b['products']);ps={p['product_id']:p for p in b['products']}
    return sum(a['carried']*ps[a['product_id']]['net_fare'] for a in alloc['allocations'] if a['owner']=='RW')-cost,alloc,b

def sensitivity():
    out={}
    for cid in finals:
        vals={}
        for state in ['KEEP','WITHOUT_NEW','REPLACE']:
            b=bundle(cid,'base',state,False);v,_,_=alloc_value(b,float(st[cid,'base',state]['avoidable_variable_scenario']));vals[state]=v
            expected=next(r for r in rows('sensitivity.csv') if (r['candidate_id'],r['scenario'],r['case'])==(cid,'base','DIRECT_ONLY_NO_CONDITIONAL_THROUGHS'));close(v,expected[state])
        out[cid]=vals['REPLACE']-vals['WITHOUT_NEW']
    assert out['X_SVX_KJA']>out['X_SVX_IKT'];evidence['direct_only_BASE_new_delta']=out
    z=Z['C0121799','base','REPLACE'];b=z['bundle'];cost=z['known_cost']
    tr=[r for r in rows('thresholds.csv') if r['candidate_id']=='C0121799' and r['scenario']=='base']
    qr=next(r for r in tr if r['threshold']=='q_common_MNL_refined_crossing');scale=float(qr['value'])
    v,al,bb=alloc_value(b,cost,scale);seats={r['flight_instance_id']:r for r in al['seats']}
    for r in tr:
        if r['threshold']=='q_direction_at_common_MNL_crossing':
            fs=[f for f in b['flights'] if (f['origin_airport'],f['destination_airport'])==(r['origin'],r['destination']) and f['pattern_id'].startswith('NEW-')]
            q=sum(seats[f['flight_instance_id']]['carried_segments'] for f in fs)/len(fs);close(q,r['value'],.002)
            pot=next(m['potential_journeys'] for m in bb['markets'] if m['demand_pool_id']==M.RE.P05.pool(r['origin'],r['destination']));close(pot,r['directed_monthly_potential'],.01)
    # All eligible saved B2 alternatives at the one reported crossing, no new search.
    rivals=[];seen=set();cohort=st['C0121799','base','REPLACE']['cohort_key']
    for r in S:
        if r['scenario']!='base' or r['cohort_key']!=cohort:continue
        k=key(r['candidate_id'],'base',r['state'])
        if k in seen or k==key('C0121799','base','REPLACE'):continue
        seen.add(k);c=candidate(r['candidate_id'],'base',r['state']);jobs=c['changed_old_jobs']+c['new_jobs'];hard,bh=M.G.physics(jobs,M.SETUPS[c['setup_id']]['positions'])
        if hard or bh>8+1e-9:continue
        vb,_,_=alloc_value(bundle(r['candidate_id'],'base',r['state']),float(r['avoidable_variable_scenario']),scale)
        rivals.append((vb,r['candidate_id'],r['state']))
    best=max(rivals);close(v-best[0],qr['delta_recomputed'],30);assert best[1:]==(qr['stress_alternative_id'],qr['stress_alternative_state'])
    for r in tr:
        if r['threshold']=='fare_MNL_refined_crossing':
            fv,_,_=alloc_value(b,cost,fare=float(r['value']));close(fv-float(r['alternative_known_subtotal']),r['delta_recomputed'],20)
    evidence['AER_crossing']={'scale':scale,'delta_RUB':v-best[0],'rival':best[1:],'eligible_states_reallocated':len(rivals),'q_per_leg':q,'monthly_potential_direction':pot}
    # Two physical Moscow airports share city pool; four dated departures mean 1/week.
    fs=copy.deepcopy(b['flights'][:4])
    for i,f in enumerate(fs):
        f.update(flight_instance_id='FIX'+str(i),pattern_id='NEW-FIX',origin_airport='DME' if i%2 else 'ZIA',destination_airport='GOJ',departure_utc=(M.EPOCH+timedelta(days=7*(i//2),hours=6)).isoformat(),arrival_utc=(M.EPOCH+timedelta(days=7*(i//2),hours=8)).isoformat())
    world={('MOW','GOJ'),('GOJ','MOW')};mb=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False)
    assert len(mb['markets'])==2 and len({m['demand_pool_id'] for m in mb['markets']})==2
    orig=sum(m['potential_journeys'] for m in mb['markets'])
    for opt in [dict(direction_split=.35),dict(day_stress=.5)]:
        nb=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False,**opt);close(sum(m['potential_journeys'] for m in nb['markets']),orig)
    # Explicit dated frequency fixture: four weekly departures -> 1/week.
    for i,f in enumerate(fs):
        f['origin_airport']='DME';f['departure_utc']=(M.EPOCH+timedelta(days=7*i,hours=6)).isoformat();f['arrival_utc']=(M.EPOCH+timedelta(days=7*i,hours=8)).isoformat()
    fb=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False)
    assert all(p['frequency']==1 for p in fb['products'] if p['owner']=='RW')
    weak=M.make_choice(fs,'base',world,M.START,M.END,world=world,through=False,weak_adjacent=True);close(sum(m['potential_journeys'] for m in weak['markets']),orig)
test('direct_only_reversal_AER_q_fare_crossings_all_alternatives_shared_MOW',sensitivity)
def resource_market():
    for r in rows('resource_cases.csv'):
        count=sum(e<=r['month']+'-01' for e in r['illustrative_entries'].split(';') if e);assert count==int(r['scenario_postentry_available'])
        if r['month']<'2027-07':assert count==0
        assert r['SJ_PD8_cost']==r['fullPnL']=='NULL' and r['RRJ_analogy_admitted']=='False'
    services=rows('canonical_services.csv',ROOT/'P36/market_recovery');assert sum(r['service_id'].startswith('P34-') for r in services)==46
    assert manifest['numeric_research_updates']==0
    assert all('UNPROVED' in r['actual_newness'] for r in rows('top5_pairs.csv'))
    registry=rows('path_registry.csv',R.parent/'pass1');assert any(r['path']=='SVX-OMS-SVX-GOJ-SVX' and r['family']=='CONCAT_RT' for r in registry)
test('resource_entry_market_no_update_CONCAT_RT_label',resource_market)
test('protected_and_all_inputs_after',unchanged)
result={'status':'PASS' if all(x=='PASS' for x in checks.values()) else 'FAIL','checks':checks,'evidence':evidence,'source_hashes':{f:sha(ROOT/f) for f in guards if f.startswith(str(P.relative_to(ROOT))+'/') or f in [str((R.parent/'protected_files.json').relative_to(ROOT)),str((R.parent/'source_pins.json').relative_to(ROOT))]},'verified_hash_count':len(guards),'verified_hash_manifest_sha256':hashlib.sha256(json.dumps(guards,sort_keys=True).encode()).hexdigest(),'manifest_preexisting_exceptions':manifest_mismatches,'review_checks_sha256':sha(Path(__file__)),'not_checked':['actual invoices/OD/booking/registration/crew/slots/AFM/MRO','global optimum or expanded network','complete external own/interline/three-leg products','actual initial aircraft readiness'],'scope':'One bounded independent acceptance; no builders, no network, no source writes.'}
(R/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('FINAL',result['status'],flush=True)
sys.exit(0 if result['status']=='PASS' else 1)
