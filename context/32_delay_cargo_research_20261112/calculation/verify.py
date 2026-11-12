#!/usr/bin/env python3
"""Independent invariants + two deterministic builds; writes only calculation/."""
import sys
sys.dont_write_bytecode=True
import json
import math
from collections import defaultdict
from datetime import timedelta
import calculate as c


def close(a,b,tol=1e-6):
    assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=tol),(a,b)


def checks():
    passed=[]
    checks_count=0
    def mark(label,n=1):
        nonlocal checks_count
        passed.append(label)
        checks_count+=n
    # Exact user ASR inputs, never numerical RW parameter sources.
    for x in json.loads((c.STUDY/'inputs/transcript_manifest.json').read_text()):
        p=c.STUDY/x['path']
        assert p.stat().st_size==x['bytes'] and c.digest(p)==x['sha256']
        assert x['numeric_RW_input'] is False
    mark('both transcript bytes/SHA and qualitative-only admission',2)
    raw=c.read(c.STUDY/'schedule_data/paired_control_calendars.csv')
    errors=[]; placeholders=[]
    for r in raw:
        elapsed=c.minutes(c.dt(r['arr_utc']+'+00:00')-c.dt(r['dep_utc']+'+00:00'))
        if r['origin']==r['destination'] or float(r['block_nominal_min'])==0:
            placeholders.append(r)
        elif elapsed!=float(r['block_nominal_min']):errors.append(r)
    assert len(raw)==18 and len(placeholders)==12 and len(errors)==3
    assert {r['pair'] for r in errors}=={'SVX-KUF','SVX-GOJ'}
    for a,b,d0,t0,d1,t1,expected in [
        ('SVX','OMS','2027-02-02','21:20','2027-02-03','00:00',100),
        ('OMS','SVX','2027-02-03','00:50','2027-02-03','01:35',105),
        ('SVX','KUF','2027-02-02','22:45','2027-02-02','23:30',105),
        ('KUF','SVX','2027-02-03','08:00','2027-02-03','10:40',100),
        ('KUF','SVX','2027-02-03','08:00','2027-02-03','10:45',105)]:
        close(c.minutes(c.local(d1,t1,b)-c.local(d0,t0,a)),expected)
    admissions=c.read(c.HERE/'source_admission.csv')
    assert next(r for r in admissions if r['admission_id']=='CARGO-S06')['admission']=='QUARANTINE_AIRPORT_IDENTITY'
    assert next(r for r in admissions if r['admission_id']=='BLOCK-GOJ')['admission']=='SCENARIO_ONLY'
    mark('all18 source calendar rows audited;12 placeholders removed;3 clock errors;B/LR separate;S06 quarantine',25)
    controls=c.read(c.HERE/'control_flights.csv')
    assert len(controls)==90
    for route in c.ROUTES:
        for layout in c.LAYOUTS:
            p=c.chain(route,layout)['P'];k=c.chain(route,layout)['KEEP']
            assert len(p)==6 and len(k)==4 and p[2:]==k
            for fs in (p,k):
                pos='SVX';prior=None
                for f in fs:
                    assert f['origin']==pos and f['origin']!=f['destination'] and f['block']>0
                    assert c.dt(c.clock(f['dep'],f['origin']))==f['dep']
                    assert c.dt(c.clock(f['arr'],f['destination']))==f['arr']
                    close(c.minutes(f['arr']-f['dep']),f['block'])
                    if prior:assert f['dep']>=prior+timedelta(minutes=60)
                    pos=f['destination'];prior=f['arr']
                assert pos=='SVX'
            close(sum(f['block'] for f in p)-sum(f['block'] for f in k),sum(c.ROUTES[route][1:]))
    mark('90 physical UTC/local calendars,common retained tasks,positive blocks,closed position/cycle accounting',90)
    es=c.read(c.HERE/'delay_events.csv')
    grouped=defaultdict(list)
    for e in es:
        key=(e['route'],e['layout'],int(e['min_turn_scenario_min']),int(e['injection_min']),e['control'])
        grouped[key].append(e)
        dep=c.dt(e['actual_dep_utc']);arr=c.dt(e['actual_arr_utc'])
        plan=c.dt(e['planned_dep_utc']);parr=c.dt(e['planned_arr_utc'])
        ready=c.dt(e['aircraft_ready_utc']);gate=c.dt(e['known_other_ready_utc']);hold=c.dt(e['imposed_hold_until_utc'])
        assert dep==max(plan,ready,gate,hold)
        close(c.minutes(arr-dep),e['block_min'])
        close(c.minutes(dep-plan),e['dep_delay_min']);close(c.minutes(arr-parr),e['arr_delay_min'])
        assert float(e['dep_delay_min'])>=0 and int(e['cycle_count'])==1
        assert float(e['extra_block_min_from_ground_delay'])==0
        if e['flight_id']!='NEW-OUT':
            if e['available_buffer_above_min_turn_min']!='NULL':
                expected=max(0,float(e['incoming_delay_min'])-float(e['available_buffer_above_min_turn_min']))
                close(e['dep_delay_min'],expected)
                close(e['buffer_consumed_min'],min(float(e['incoming_delay_min']),float(e['available_buffer_above_min_turn_min'])))
        if e['control']=='KEEP' or int(e['injection_min'])==0:assert float(e['dep_delay_min'])==0
    for key,rr in grouped.items():
        turn=key[2]
        for old,new in zip(rr,rr[1:]):
            assert c.dt(new['actual_dep_utc'])>=c.dt(old['actual_arr_utc'])+timedelta(minutes=turn)
        assert sum(float(e['block_min']) for e in rr)==sum(float(e['block_min']) for e in grouped[key[:3]+(0,key[4])])
    for route in c.ROUTES:
        for layout in c.LAYOUTS:
            for turn in (45,60):
                for fid in [f['fid'] for f in c.chain(route,layout)['P']]:
                    vals=[float(next(e for e in grouped[(route,layout,turn,s,'P')] if e['flight_id']==fid)['dep_delay_min']) for s in c.SHOCKS]
                    assert vals==sorted(vals)
            for shock in c.SHOCKS:
                for f45,f60 in zip(grouped[(route,layout,45,shock,'P')],grouped[(route,layout,60,shock,'P')]):
                    assert float(f60['dep_delay_min'])>=float(f45['dep_delay_min'])
    mark('720 event recurrence,max gates,nonnegative/monotone delay,turn45/60 sensitivity,buffers and unchanged BH/cycles',720)
    summaries=c.read(c.HERE/'delay_summary.csv')
    for s in summaries:
        key=(s['route'],s['layout'],int(s['min_turn_scenario_min']),int(s['injection_min']),'P')
        rs=grouped[key];ff=[e for e in rs if e['kind']=='retained']
        close(sum(float(e['dep_delay_min']) for e in ff),s['retained_sum_departure_delay_min'])
        close(ff[0]['dep_delay_min'],s['first_KEEP_dep_delay_min'])
        close(ff[-1]['arr_delay_min'],s['last_retained_arrival_delay_min'])
        assert sum(float(e['dep_delay_min'])>0 for e in ff)==int(s['delayed_retained_departures'])
        assert s['probability']=='NULL' and s['hard_cutoff_utc']=='NULL'
        assert s['max_injection_before_confirmed_cutoff_min']=='NULL'
        fs=c.chain(s['route'],s['layout'])['P']
        limit=float(s['max_injection_before_hypothetical_cutoff_min'])
        edge=c.replay(fs,key[2],limit)
        above=c.replay(fs,key[2],limit+1)
        close(edge[2]['dep_delay'],30);close(above[2]['dep_delay'],31)
    for route in c.ROUTES:
        s=next(s for s in summaries if s['route']==route and s['layout']=='EQUAL_GAP_G390' and s['min_turn_scenario_min']=='60' and s['injection_min']=='120')
        expected=110 if route=='SVX-GOJ' else 55
        close(s['first_KEEP_dep_delay_min'],expected)
        close(s['last_retained_arrival_delay_min'],expected-15)
        equal=next(s for s in summaries if s['route']==route and s['layout']=='EQUAL_BUFFER_B30' and s['min_turn_scenario_min']=='60' and s['injection_min']=='120')
        close(equal['first_KEEP_dep_delay_min'],90)
        end=next(s for s in summaries if s['route']==route and s['layout']=='END_OF_DAY_NEXT0900' and s['min_turn_scenario_min']=='60' and s['injection_min']=='120')
        close(end['retained_sum_departure_delay_min'],0)
    assert any(c.dt(e['actual_arr_utc']).date()!=c.dt(e['actual_dep_utc']).date() for e in es)
    assert any(s['stop_state']=='HORIZON_WITH_POSITIVE_RESIDUAL' for s in summaries)
    mark('72 reconciled paired summaries,overnight carry and residual,equal-buffer fairness,conditional cutoff edge',72)
    # Exercise other-ready gate, so the max() input is not only decorative.
    fs=c.chain('SVX-OMS','EQUAL_GAP_G390')['P']
    g=fs[2]['dep']+timedelta(minutes=180)
    rr=c.replay(fs,60,30,other_ready={fs[2]['fid']:g})
    assert rr[2]['actual_dep']==g and rr[-1]['dep_delay']>0
    # Conditional recovery: new RT can start earlier ONLY with an earlier tail
    # release. Reserve remains at SVX and flies all retained closed tasks once.
    for route in c.ROUTES:
        fs=c.chain(route,'EQUAL_GAP_G390')['P']
        rr=c.replay(fs,60,120);need=rr[2]['dep_delay']
        revised=[dict(f,dep=f['dep']+timedelta(minutes=need),arr=f['arr']+timedelta(minutes=need)) if f['kind']=='retained' else f for f in fs]
        after=c.replay(revised,60,120)
        assert all(e['dep_delay']==0 for e in after[2:])
        early=[dict(f,dep=f['dep']-timedelta(minutes=need),arr=f['arr']-timedelta(minutes=need)) if f['kind']=='new' else f for f in fs]
        after=c.replay(early,60,120,initial_ready=early[0]['dep'])
        assert all(e['dep_delay']==0 for e in after[2:])
        reserve=c.replay(fs[2:],60,0)
        assert all(e['dep_delay']==0 for e in reserve)
        for a,b in zip(reserve,reserve[1:]):assert b['actual_dep']>=a['actual_arr']+timedelta(minutes=60)
    mark('known external-ready gate + physical recovery,conditional earlier release and one reserve used once',10)
    ledger=c.read(c.HERE/'passenger_turn_ledger.csv')
    cases=json.loads((c.HERE/'economic_cases.json').read_text())
    assert len(cases)==24
    for case in cases:
        rows=[r for r in ledger if r['route']==case['route'] and r['scenario']==case['scenario'] and float(r['return_potential_alpha'])==case['return_potential_alpha'] and r['row_kind']=='PHYSICAL_SECTOR']
        p=[r for r in rows if r['control']=='P'];k=[r for r in rows if r['control']=='KEEP']
        assert len(p)==32 and len(k)==24
        for r in rows:
            assert 0<=float(r['modeled_pax'])<=100+1e-8
            close(float(r['net_fare_RUB'])*float(r['modeled_pax']),r['net_revenue_RUB'],tol=.001)
            close(float(r['fuel_RUB'])+float(r['nonfuel_block_cycle_RUB']),r['known_cost_RUB'])
            close(float(r['net_revenue_RUB'])-float(r['known_cost_RUB']),r['allocated_sector_contribution_RUB'])
            assert r['fixed_opaque_pax_cost_included']=='False' and float(r['support_RUB'])==0
            close(c.minutes(c.dt(r['arrival_utc'])-c.dt(r['departure_utc']))/60,r['block_hours'])
        revp=sum(float(r['net_revenue_RUB']) for r in p);revk=sum(float(r['net_revenue_RUB']) for r in k)
        cp=sum(float(r['known_cost_RUB']) for r in p);ck=sum(float(r['known_cost_RUB']) for r in k)
        close((revp-revk-cp+ck)/4,case['known_increment_P_minus_KEEP_before_F_donor_delay_RUB'])
        new=[r for r in p if r['new_frequency']=='True']
        retained=sum(float(r['net_revenue_RUB']) for r in p if r['new_frequency']=='False')
        oldloss=(revk-retained)/4
        close(oldloss,case['own_retained_revenue_loss_RUB'])
        close(sum(float(r['allocated_sector_contribution_RUB']) for r in new)/4-oldloss,case['known_increment_P_minus_KEEP_before_F_donor_delay_RUB'])
        assert case['full_P_minus_KEEP_RUB'] is None
        if case['return_potential_alpha']==0:close(case['new_back_pax'],0)
    mark('24 joint monthly P-KEEP ledgers,32/24 physical legs,cost/revenue units,own shift once,perturn divide4,full resultNULL',1368)
    # Recheck API allocation conservation and identical P/KEEP markets directly.
    re=c.load_economics()
    for route in c.ROUTES:
        req={'P':c.econ_request(route,True),'KEEP':c.econ_request(route,False)}
        result=re.evaluate_combined_programme([], 'base', keep_patterns=[],start='2027-02-01',end='2027-02-28',
            existing_slots=1,delivery_scenario='S0',reserve_available=None,calendar_requests=req)
        assert not result['daily_block_violations'] and result['resource_necessary_screen']=='RESERVE_UNKNOWN_GATE'
        assert result['programme']['bundle']['markets']==result['keep']['bundle']['markets']
        for label in ('programme','keep'):
            bundle=result[label]['bundle'];alloc=result[label]['allocation']
            markets={m['demand_pool_id']:m['potential_journeys'] for m in bundle['markets']}
            carried=defaultdict(float)
            for a in alloc['allocations']:carried[a['demand_pool_id']]+=a['carried']
            for pool,potential in markets.items():assert carried[pool]<=potential+1e-6
        assert result['full_P_minus_KEEP'] is None
    mark('completed API reused;common directed market pools,seat limits,8BH necessary screen,unknown reserve',3)
    be=c.read(c.HERE/'cargo_break_even.csv')
    for r in be:
        rate=float(r['net_contribution_per_paid_kg_axis_RUB'])
        close(r['kg_paid_BE_allocated_return'],float(r['return_allocated_loss_RUB'])/rate)
        close(r['kg_paid_BE_launch_before_unknowns'],max(0,-float(r['whole_P_minus_KEEP_before_unknowns_RUB']))/rate)
        assert r['actual_required_paid_kg_for_launch']=='NULL' and r['actual_physical_capacity_kg']=='NULL'
    close(c.paid_threshold(100,50),0)  # a negative allocated sector cannot reverse a positive whole turn
    close(c.paid_threshold(100,50,omitted_F=40,donor=70,delay_cost=20,fixed_awb=20),1)
    assert c.paid_threshold(-100,0) is None and c.paid_threshold(-100,-10) is None
    mark('120 paid-kg BE thresholds,whole turn vs allocated sector,F/donor/delay/AWB once,r<=0',124)
    frontier=c.read(c.HERE/'cargo_capacity_frontier.csv')
    for r in frontier:
        assert r['actual_physical_residual_kg']=='NULL' and r['approved_cargo_capacity_kg']=='NULL'
        if r['frontier_kind']=='LR_UNKNOWN_NOT_ZERO':continue
        n=float(r['passengers_axis']);b=float(r['checked_bag_kg_each_axis']);q=float(r['physical_cargo_kg_axis']);rho=float(r['cargo_density_kg_m3_axis'])
        noncargo=n*(75+10+b);fuel=float(r['departure_fuel_including_reserves_kg_axis'])
        close(r['noncargo_total_mass_kg'],noncargo)
        close(r['hold_non_cargo_mass_kg'],n*b)
        close(r['remaining_hold_mass_kg'],4200-n*b)
        close(r['remaining_hold_volume_m3'],20.15-n*b/200)
        close(r['cargo_volume_m3'],q/rho)
        limit=c.mass_boundary(noncargo,q,fuel,1500)
        close(r['max_allowed_DOW_kg'],limit)
        assert limit+noncargo+q<=40000+1e-6
        assert limit+noncargo+q+fuel<=45880+1e-6
        assert limit+noncargo+q+1500<=41000+1e-6
        assert min(40000-(limit+.01)-noncargo-q,45880-(limit+.01)-noncargo-q-fuel,41000-(limit+.01)-noncargo-q-1500)<0
        close(r['diagnostic_chargeable_kg_no_rounding_minimum'],c.chargeable_kg(q,q/rho,6000))
    # Actual DOW here is an artificial unit-test fixture, never a reported load.
    cp=c.conditional_capacity(27000,4500,1500,100,checked=20,cargo_density=100)
    close(cp['pnoncargo'],10500);close(cp['holdmass'],2200);close(cp['free_volume'],10.15)
    close(cp['conditional_upper'],1015);assert cp['approved_capacity'] is None
    cp2=c.conditional_capacity(27000,4500,1500,100,checked=20,cargo_density=250,floor_limit=800,geometry_limit=900)
    close(cp2['approved_capacity'],800)
    close(c.chargeable_kg(1000,10,6000),1666.6666666667)
    close(c.chargeable_kg(1000,4,6000),1000)
    assert c.chargeable_kg(1000,4) is None
    close(c.chargeable_kg(1,0.001,6000,rounding_kg=5,minimum_kg=12),15)
    mark('conditional capacity frontiers,total mass once,cabin vs hold,kg vs m3,AWB,LRNULL,floor/geometry',len(frontier)+10)
    manifest=json.loads((c.HERE/'manifest.json').read_text())
    for x in manifest['input_files']:assert c.digest(c.ROOT/x['path'])==x['sha256']
    for name,x in manifest['outputs'].items():assert c.digest(c.HERE/name)==x['sha256']
    for name,sha in manifest['auxiliary_outputs'].items():assert c.digest(c.HERE/name)==sha
    mark('manifest input/output/code paths and digests',len(manifest['input_files']))
    return passed,checks_count


def main():
    inputs={str(p):c.digest(p) for p in c.input_paths()}
    first=c.build()
    names=sorted(first)+['api_requests.json','economic_cases.json','manifest.json']
    hashes1={n:c.digest(c.HERE/n) for n in names}
    passed,count=checks()
    c.build()
    hashes2={n:c.digest(c.HERE/n) for n in names}
    assert hashes1==hashes2,'Non-deterministic important outputs'
    assert inputs=={str(p):c.digest(p) for p in c.input_paths()},'Read-only input mutated during build/verification'
    report=dict(status='PASS',version=c.VERSION,route_cases=3,validation_groups=passed,
                assertions_or_checked_records=count,determinism='TWO_BUILDS_BYTE_IDENTICAL',
                important_output_sha256=hashes2,input_files_unchanged=len(inputs),
                write_scope=str(c.HERE),dependency_install=False,network_access=False,
                limits='Arithmetic/consistency only; no RW operational approval, actual demand/rate/capacity or full profit assertion')
    c.write_json('validation.json',report)
    print(json.dumps({k:report[k] for k in ('status','route_cases','assertions_or_checked_records','determinism','input_files_unchanged')},sort_keys=True))


if __name__=='__main__':main()
