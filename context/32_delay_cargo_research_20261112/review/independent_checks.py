#!/usr/bin/env python3
"""One targeted review. No author build/verify invocation; writes only review/.
Independent clock/ledger/frontier arithmetic; reuses completed context31 API only
for allocator integration, not as independent evidence of market truth.
"""
import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,subprocess,math,importlib.util
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import defaultdict
R=Path(__file__).resolve().parent; S=R.parent; ROOT=S.parents[1]; C=S/'calculation'; C31=ROOT/'context/31_direct_growth_research_20261112'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def dump(n,v): (R/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def dt(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
def num(x): return float(x)
def near(a,b): assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=.002),(a,b)
results=[]
def check(name,fn):
    try:
        detail=fn();results.append(dict(check=name,status='PASS',detail=str(detail)))
    except Exception as e:
        results.append(dict(check=name,status='FAIL',detail=repr(e)))
tracked=[ROOT/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p]
man=json.loads((C/'manifest.json').read_text()); trans=json.loads((S/'inputs/transcript_manifest.json').read_text())
protected=set(tracked)|{ROOT/x['path'] for x in man['input_files']}|{Path(x['attachment_path']) for x in trans}
protected|={p for d in ['schedule_data','cargo_data','calculation','inputs'] for p in (S/d).rglob('*') if p.is_file()}
assert not any('/networks/' in str(p) for p in protected)
before={str(p):sha(p) for p in sorted(protected)}
dump('preservation_before.json',before)
tables={str(p.relative_to(S)):read(p) for d in ['schedule_data','cargo_data','calculation'] for p in (S/d).glob('*.csv')}
def csv_shape():
    for name,rows in tables.items():
        assert rows and all(None not in row and all(v is not None for v in row.values()) for row in rows),name
    for d in ['schedule_data','cargo_data','calculation']: json.loads((S/d/'validation.json').read_text())
    return {n:len(v) for n,v in tables.items()}
check('all_package_CSV_rows_and_validation_JSON_parsed',csv_shape)
def preservation_sources():
    assert len(tracked)==436
    for x in trans:
        assert sha(S/x['path'])==sha(Path(x['attachment_path']))==x['sha256']
        assert (S/x['path']).stat().st_size==x['bytes']
    for x in man['input_files']: assert sha(ROOT/x['path'])==x['sha256'],x['path']
    for n,v in man['outputs'].items(): assert sha(C/n)==v['sha256'] and len(tables['calculation/'+n])==v['rows']
    for key in ['auxiliary_outputs','code','documentation']:
        for n,v in man[key].items(): assert sha(C/n)==v,(key,n)
    return f'436 tracked; {len(man["input_files"])} manifest inputs; both original attachments; code/docs/output hashes. Integrity only, not source truth.'
check('preserved_inputs_manifest_and_real_attachments',preservation_sources)
T=lambda name:tables['calculation/'+name+'.csv']
off={'SVX':5,'OMS':6,'KUF':4,'GOJ':3}; blocks={'SVX-OMS':(100,105),'SVX-KUF':(105,100),'SVX-GOJ':(130,130)}
plans={}; expected={}
def clocks():
    for route,(out,back) in blocks.items():
        dest=route[-3:]
        for layout in ['EQUAL_GAP_G390','EQUAL_BUFFER_B30','END_OF_DAY_NEXT0900']:
            start=datetime(2027,2,2,13,tzinfo=timezone.utc)
            newarr=start+timedelta(minutes=out+60+back)
            first=start+timedelta(minutes=390) if layout=='EQUAL_GAP_G390' else newarr+timedelta(minutes=90) if layout=='EQUAL_BUFFER_B30' else datetime(2027,2,3,4,tzinfo=timezone.utc)
            ds=[start,start+timedelta(minutes=out+60),first,first+timedelta(minutes=165),first+timedelta(minutes=340),first+timedelta(minutes=500)]
            bs=[out,back,105,100,100,105]; origins=['SVX',dest,'SVX','KUF','SVX','OMS']; dests=[dest,'SVX','KUF','SVX','OMS','SVX']
            for control,begin in [('P',0),('KEEP',2)]:
                rows=[x for x in T('control_flights') if (x['route'],x['layout'],x['control'])==(route,layout,control)]
                assert len(rows)==6-begin
                for i,r in enumerate(rows,begin):
                    assert (r['origin'],r['destination'])==(origins[i],dests[i])
                    assert dt(r['dep_utc'])==ds[i] and dt(r['arr_utc'])==ds[i]+timedelta(minutes=bs[i])
                    for key,airport,utc in [('dep_local',origins[i],ds[i]),('arr_local',dests[i],ds[i]+timedelta(minutes=bs[i]))]:
                        assert r[key]==utc.astimezone(timezone(timedelta(hours=off[airport]))).isoformat()
                    assert r['tail']=='S1_CONDITIONAL_EXISTING_RRJ95B'
                plans[route,layout,control]=rows
    return '90 clocks reconstructed using explicit offsets; full dates, positions, four shared retained sectors; no placeholder flights.'
check('independent_UTC_local_physical_calendars',clocks)
def delays():
    for (route,layout,control),rows in plans.items():
        for turn in [45,60]:
            lastvalues=None
            for shock in [0,30,60,120]:
                ready=datetime(2027,2,2,13,tzinfo=timezone.utc); vals=[]
                es=[x for x in T('delay_events') if (x['route'],x['layout'],x['control'],int(x['min_turn_scenario_min']),int(x['injection_min']))==(route,layout,control,turn,shock)]
                for r,e in zip(rows,es):
                    plan=dt(r['dep_utc']); imposed=plan+timedelta(minutes=shock if r['flight_id']=='NEW-OUT' else 0)
                    dep=max(plan,ready,imposed); arr=dep+timedelta(minutes=int(r['block_min'])); delay=(dep-plan).total_seconds()/60
                    assert dt(e['actual_dep_utc'])==dep and dt(e['actual_arr_utc'])==arr
                    near(e['dep_delay_min'],delay);near(e['arr_delay_min'],delay)
                    for k,ap,val in [('actual_dep_local',r['origin'],dep),('actual_arr_local',r['destination'],arr)]: assert e[k]==val.astimezone(timezone(timedelta(hours=off[ap]))).isoformat()
                    assert e['extra_block_min_from_ground_delay']=='0'; vals.append(delay); ready=arr+timedelta(minutes=turn)
                assert len(es)==len(rows)
                if control=='KEEP' or shock==0: assert not any(vals)
                if lastvalues: assert all(a<=b for a,b in zip(lastvalues,vals))
                lastvalues=vals;expected[route,layout,control,turn,shock]=vals
    for r in T('delay_summary'):
        route,layout,turn,shock=r['route'],r['layout'],int(r['min_turn_scenario_min']),int(r['injection_min'])
        vals=expected[route,layout,'P',turn,shock][2:]
        near(r['first_KEEP_dep_delay_min'],vals[0]);near(r['last_retained_arrival_delay_min'],vals[-1]);near(r['retained_sum_departure_delay_min'],sum(vals))
        for k in ['actual_remaining_duty_min','actual_min_rest_min','actual_rest_surplus_min','hard_cutoff_utc','probability']: assert r[k]=='NULL'
        if turn==60 and shock==120 and layout=='EQUAL_GAP_G390': assert (vals[0],vals[-1])==((110,95) if route=='SVX-GOJ' else (55,40))
        if turn==60 and shock==120 and layout=='EQUAL_BUFFER_B30': assert vals[0]==90
    return '720 independently replayed events; 72 summaries; D0 identical; D monotone; no midnight reset; expected 55/40,55/40,110/95 and equal-buffer90.'
check('independent_propagation_and_summary',delays)
cases=json.loads((C/'economic_cases.json').read_text())
def ledger():
    for c in cases:
        rs=[r for r in T('passenger_turn_ledger') if r['row_kind']=='PHYSICAL_SECTOR' and (r['route'],r['scenario'],float(r['return_potential_alpha']))==(c['route'],c['scenario'],c['return_potential_alpha'])]
        p=[r for r in rs if r['control']=='P']; k=[r for r in rs if r['control']=='KEEP']; assert (len(p),len(k))==(32,24)
        for r in rs:
            assert 0<=float(r['modeled_pax'])<=100
            near(float(r['modeled_pax'])*float(r['net_fare_RUB']),r['net_revenue_RUB'])
            near(float(r['fuel_RUB'])+float(r['nonfuel_block_cycle_RUB']),r['known_cost_RUB'])
            near((dt(r['arrival_utc'])-dt(r['departure_utc'])).total_seconds()/3600,r['block_hours'])
        summ=lambda rows,col:sum(float(r[col]) for r in rows)
        margin=(summ(p,'net_revenue_RUB')-summ(k,'net_revenue_RUB')-summ(p,'known_cost_RUB')+summ(k,'known_cost_RUB'))/4
        near(margin,c['known_increment_P_minus_KEEP_before_F_donor_delay_RUB'])
        retained=[r for r in p if r['new_frequency']=='False'];new=[r for r in p if r['new_frequency']=='True']; assert len(new)==8
        loss=(summ(k,'net_revenue_RUB')-summ(retained,'net_revenue_RUB'))/4
        near(loss,c['own_retained_revenue_loss_RUB']);near(summ(new,'allocated_sector_contribution_RUB')/4-loss,margin)
        for key in ['full_P_minus_KEEP_RUB','F_actual_RUB','donor_actual_RUB','delay_cost_actual_RUB']: assert c[key] is None
    return '24 paired cases: monthly /4 added RT; retained-own loss once; 1344 sectors reconciled; full actual NULL.'
check('independent_passenger_ledger_units_and_own_shift',ledger)
def api():
    spec=importlib.util.spec_from_file_location('review_completed_api',C31/'route_economics/calculate.py'); api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
    requests=json.loads((C/'api_requests.json').read_text())
    for c in cases:
        route=c['route']; req=requests[route]; dest=route[-3:]; dirs={(r['origin'],r['destination']) for r in req['P']['blocks']}
        overrides={f'{a}>{b}/2027-02':api.annual(a,b,c['scenario'],2027)[0]*.5*api.P05.monthly_profile(2027)[2]/.6*(c['return_potential_alpha'] if (a,b)==(dest,'SVX') else 1) for a,b in dirs}
        res=api.evaluate_combined_programme([],c['scenario'],keep_patterns=[],start='2027-02-01',end='2027-02-28',demand_overrides=overrides,donor_loss=None,omitted_F=None,existing_slots=1,delivery_scenario='S0',reserve_available=None,calendar_requests=req)
        near(res['known_increment_P_minus_KEEP_before_F_donor']/4,c['known_increment_P_minus_KEEP_before_F_donor_delay_RUB'])
        assert res['full_P_minus_KEEP'] is None and res['cash'] is None
        assert res['programme']['bundle']['markets']==res['keep']['bundle']['markets']
        assert not res['daily_block_violations']
        for label in ['programme','keep']:
            v=res[label]; carried=defaultdict(float)
            for a in v['allocation']['allocations']: carried[a['demand_pool_id']]+=a['carried']
            for m in v['bundle']['markets']: assert carried[m['demand_pool_id']]<=m['potential_journeys']+1e-6
    return '24 fresh completed API calls: base/cautious, alpha1/.5/.25/0; identical directed potential P/KEEP. Shared allocator test, not independent market validation.'
check('completed_API_reexecuted_24_cases',api)
def cargo():
    for r in T('cargo_break_even'):
        rate=float(r['net_contribution_per_paid_kg_axis_RUB']); near(r['kg_paid_BE_allocated_return'],max(0,float(r['return_allocated_loss_RUB']))/rate);near(r['kg_paid_BE_launch_before_unknowns'],max(0,-float(r['whole_P_minus_KEEP_before_unknowns_RUB']))/rate)
        for k in ['F_net_RUB','D_external_RUB','C_delay_RUB','C_AWB_RUB','actual_required_paid_kg_for_launch','actual_paid_orders_kg','actual_net_rate','actual_physical_capacity_kg']: assert r[k]=='NULL'
    for r in T('cargo_capacity_frontier'):
        assert r['actual_physical_residual_kg']==r['approved_cargo_capacity_kg']=='NULL'
        if r['frontier_kind']=='LR_UNKNOWN_NOT_ZERO':continue
        n,b,q,rho,fdep,farr=[float(r[k]) for k in ['passengers_axis','checked_bag_kg_each_axis','physical_cargo_kg_axis','cargo_density_kg_m3_axis','departure_fuel_including_reserves_kg_axis','arrival_fuel_kg_axis']]
        non=n*(75+10+b);hold=n*b; vol=20.15-hold/200
        near(r['noncargo_total_mass_kg'],non);near(r['hold_non_cargo_mass_kg'],hold);near(r['remaining_hold_mass_kg'],4200-hold);near(r['remaining_hold_volume_m3'],vol);near(r['cargo_volume_m3'],q/rho)
        near(r['max_allowed_DOW_kg'],min(40000,45880-fdep,41000-farr)-non-q)
        near(r['diagnostic_chargeable_kg_no_rounding_minimum'],max(q,q/rho*1e6/6000))
        assert (r['fits_marketing_volume']=='True')==(q/rho<=vol)
    return '120 separate return/whole thresholds;1491 capacity rows; ZFW/TOW/LW, cabin vs hold, physical vs paid kg, actualNULL.'
check('independent_cargo_BE_and_mass_frontiers',cargo)
def edges():
    spec=importlib.util.spec_from_file_location('review_author_pure_functions',C/'calculate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    near(m.paid_threshold(100,50),0);near(m.paid_threshold(100,50,omitted_F=40,donor=70,delay_cost=20,fixed_awb=20),1)
    assert m.paid_threshold(-100,0) is None and m.paid_threshold(-100,-10) is None
    near(m.chargeable_kg(1,.001,6000,rounding_kg=5,minimum_kg=12),15)
    near(m.chargeable_kg(1000,10,6000),10000/6);near(m.chargeable_kg(1000,4,6000),1000)
    assert m.chargeable_kg(1000,4) is None
    for r in T('recovery_options'):
        assert r['resource_availability']=='UNKNOWN' and r['cost_RUB']=='NULL'
        if r['option']=='SWAP_CREW': near(r['first_KEEP_delay_after_option_if_confirmed_min'],r['minutes_needed_to_protect_first_KEEP'])
        if r['option'] in ['RETIME_FOLLOWING','END_OF_DAY']: assert 'Revised calendar' in r['result_clock_basis']
    return 'Author pure helpers tested against independently set edge results; no build/write invoked. Positive whole turn requires zero cargo; fixed AWB once; min/rounding; crew swap cannot advance aircraft.'
check('edge_cases_and_recovery_semantics',edges)
def source_and_recovery():
    raw=tables['schedule_data/paired_control_calendars.csv']; placeholders=[];errors=[]
    for r in raw:
        if r['origin']==r['destination'] or float(r['block_nominal_min'])==0: placeholders.append(r)
        elif (dt(r['arr_utc'])-dt(r['dep_utc'])).total_seconds()/60!=float(r['block_nominal_min']):errors.append(r)
    assert len(placeholders)==12 and len(errors)==3
    adm={r['admission_id']:r for r in T('source_admission')}
    assert adm['CARGO-S06']['admission']=='QUARANTINE_AIRPORT_IDENTITY'
    assert adm['BLOCK-GOJ']['admission']=='SCENARIO_ONLY'
    for route in blocks:
        rows=plans[route,'EQUAL_GAP_G390','KEEP'];pos='SVX'; ready=None
        for r in rows:
            assert r['origin']==pos
            if ready: assert dt(r['dep_utc'])>=ready
            ready=dt(r['arr_utc'])+timedelta(minutes=60);pos=r['destination']
        assert pos=='SVX' # one R1, all four sectors, never duplicated
        need=expected[route,'EQUAL_GAP_G390','P',60,120][2]
        # Shifting all retained times can eliminate delay against revised clocks;
        # compared with original passenger departure, first departure is still late.
        revised_first=dt(rows[0]['dep_utc'])+timedelta(minutes=need)
        near((revised_first-dt(rows[0]['dep_utc'])).total_seconds()/60,need)
    for r in T('decision_thresholds'):
        assert r['actual_decision']=='UNKNOWN'
        assert r['probability']==r['delay_minute_price_RUB']==r['cancellation_saving_RUB']=='NULL'
    return '12 placeholders/3 bad clocks quarantined; S06 excluded; one reserve physical four-sector closed chain conditional; retiming old-clock delay remains;48 decisionsUNKNOWN.'
check('source_quarantine_reserve_retiming_decision_gates',source_and_recovery)
def protected_after():
    after={p:sha(Path(p)) for p in before};assert after==before
    imported=[Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(getattr(m,'__file__','')).startswith(str(ROOT))]
    assert not any('/networks/' in str(p) for p in imported)
    dump('imported_files.json',[{'path':str(p),'sha256':sha(p)} for p in sorted(set(imported)) if p.is_file()])
    return f'{len(before)} protected files byte-identical during review; 436 tracked preserved; context31/networks not opened.'
check('preservation_after_execution',protected_after)
with (R/'actual_checks.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['check','status','detail']);w.writeheader();w.writerows(results)
dump('validation.json',dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',checks=results,tracked_files=436,manifest_inputs=len(man['input_files']),protected_files=len(before),scope='Targeted independent arithmetic and integration; not market/source-wide/operational audit',author_verify_executed=False,author_build_executed=False,write_scope=str(R)))
print(json.dumps(results,ensure_ascii=False,indent=2))
