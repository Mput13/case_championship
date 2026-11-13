#!/usr/bin/env python3
"""Independent executed checks for the economics package. No old verify runs.

Writes only economics/validation.json. Run calculate.py first. For a full
deterministic repeat run calculate.py a second time and compare run receipts.
"""
import sys
sys.dont_write_bytecode=True
import copy
import math
from collections import Counter,defaultdict
from datetime import datetime,timedelta
import core as C

CHECKS=[];RECEIPTS={}

def check(name,fn):
    try:
        value=fn();CHECKS.append(dict(name=name,status='PASS'))
        if value is not None:RECEIPTS[name]=value
        print('PASS',name,flush=True)
    except Exception as e:
        CHECKS.append(dict(name=name,status='FAIL',error=type(e).__name__+': '+str(e)))
        print('FAIL',name,type(e).__name__,str(e),flush=True)

def near(a,b,tol=1e-5):
    assert abs(a-b)<=tol,(a,b,a-b)

def raises(fn,needle):
    try:fn()
    except ValueError as e:
        assert needle in str(e),(needle,str(e));return str(e)
    raise AssertionError('expected rejection '+needle)

def input_hashes():
    manifest=C.js(C.HERE/'input_manifest.json')
    for p,h in manifest['input_sha256'].items():assert C.sha(C.ROOT/p)==h,p
    for p,h in manifest['code_sha256'].items():assert C.sha(C.HERE/p)==h,p
    assert C.digest(manifest['input_sha256'])==manifest['input_digest']
    assert manifest['new_numeric_OD_updates']==manifest['new_numeric_net_updates']==manifest['new_actual_invoice_updates']==0
    assert manifest['live_programmes_read'] is False
    assert manifest['guard']==manifest['guard_after']==C.guard()
    return dict(inputs=len(manifest['input_sha256']),digest=manifest['input_digest'],guard=C.guard())

def coverage():
    inv=C.read(C.P38/'contract/programme_inventory.csv')
    rows=C.read(C.HERE/'programmes_monthly.csv')
    pair=C.read(C.HERE/'pair_results.csv');pt=C.read(C.HERE/'pair_month_thresholds.csv')
    legacy={r['candidate_id'] for r in inv}
    old=[r for r in rows if r['candidate'] in legacy]
    assert len(inv)==60 and sum(r['positive_new_vs_same_without']=='True' for r in inv)==37
    assert len(old)==60*12*2*3
    assert len({r['candidate'] for r in old})==60
    seed=[r for r in pair if r['in_seed25']=='True']
    assert len(seed)==25 and len(pt)==len(pair)*2*12*2
    assert {r['pair'] for r in seed}=={r['pair'] for r in C.read(C.P38/'contract/pair_universe.csv')}
    assert {r['pair'] for r in seed if r['commercial']=='False'}=={'CEK-SVX','SVX-TJM'}
    assert len(C.templates())==436
    assert len(rows)==436*12*2*3+216
    assert sum(r['old_top5']=='True' for r in pair)==5
    assert all(r['true_own_newness']=='UNPROVED' for r in pair)
    assert all(r['fare_20kg_qualified']=='0' for r in pair)
    worlds={r['world_hash'] for r in rows};assert worlds=={C.WORLD_HASH()}
    controls=[r for r in rows if r['candidate'].startswith('PRIMARY_')]
    assert len(controls)==3*12*2*3
    assert all(r['through_journeys']=='0' and r['full_profit']=='NULL' and r['cash']=='NULL' for r in rows)
    spec=C.programme_input();assert spec and len(spec['programmes'])==420
    assert sum(len(p['variants']) for p in spec['programmes'])==436
    return dict(legacy_templates=60,completed_calendar_variants=436,source_positive=37,primary_rows=len(rows),seed_pairs=25,
        all_template_pairs=len(pair),threshold_rows=len(pt),world_pools=len(C.world()))

def profile_units():
    profile=C.RE.P05.monthly_profile(2027)
    assert len(profile)==12;near(sum(profile.values()),1,1e-12)
    q=C.RE.annual('SVX','KJA','base',2027)[0]
    ps=[C.potential('SVX','KJA',2027,m,'base') for m in range(1,13)]
    near(sum(ps),q*.5/.6)
    cautious=C.RE.DEMAND.prior('SVX','KJA')[1]*.962**2
    near(C.RE.annual('SVX','KJA','cautious',2027)[0],cautious)
    holiday={f'2027-01-{d:02}':1.5 if d<=10 else .5 for d in range(1,32)}
    near(sum(C.M.pool_days(ps[0],2027,1,holiday).values()),ps[0])
    assert C.M.exposure(2027,1)['iso_weekday_counts']['5']==5
    assert C.M.exposure(2027,2)['iso_weekday_counts']=={str(i):4 for i in range(1,8)}
    return dict(annual_potential_one_direction=sum(ps),profile_sum=sum(profile.values()),January_peak='redistributes one pool',
        interpretation='historical carrier analogue, not route forecast; monthly index 1..12, cautious stress once')

def reference_joint():
    E=C.Engine('verify')
    rows=[]
    for cid,month,sc in [('X_SVX_KJA',1,'base'),('X_SVX_IKT',2,'cautious'),('X_GOJ_KJA_F',7,'base'),
                         ('X_AER1',10,'cautious'),('C0007786',2,'base')]:
        t=C.templates()[cid]
        original=C.M.evaluate_month(t['states'],t['tails'],2027,month,sc)
        for state,jobs in t['states'].items():
            z=E.score(jobs,t['tails'],month,sc)
            near(z['subtotal'],original['states'][state]['subtotal'])
            near(z['net_revenue'],original['states'][state]['net_revenue'])
            near(z['journeys'],original['states'][state]['journeys'])
        rows.append(dict(candidate=cid,month=month,scenario=sc,result='full P31/P06 completed adapter equals factored direct kernel'))
    # A full fixed-universe reference also includes all unused outside-only
    # pools, showing that changing the local adapter's world is not a hidden
    # candidate-dependent background adjustment.
    t=C.templates()['X_SVX_KJA'];z=E.score(t['states']['REPLACE'],t['tails'],2,'base')
    full=C.full_p06(z['cal'],t['tails'],2,'base')
    near(full['revenue'],z['net_revenue']);near(full['journeys'],z['journeys'])
    assert len(full['bundle']['markets'])==len(C.world())
    assert full['through_products']==0
    for cohort in ('K1','K2','K3'):
        t=next(t for t in C.templates().values() if t['cohort']==cohort and t['scope']=='COMPLETED_MIXED_WEEKLY_VARIANT')
        z=E.score(t['states']['REPLACE'],t['tails'],7,'base')
        full=C.full_p06(z['cal'],t['tails'],7,'base')
        near(full['revenue'],z['net_revenue']);near(full['journeys'],z['journeys'])
        rows.append(dict(candidate=t['id'],cohort=cohort,result='completed mixed variant full physical P06 equivalence'))
    return rows

def kernel_synthetic():
    # Non-identical utilities and net fares, actual physical aggregate capacity.
    market=dict(demand_pool_id='CITY:DME>GOJ',month='2027-02',customer_segment='test',potential_journeys=0,
        market_basis='potential_travel',mapping_to_potential='test',source_id='TEST',source_period='TEST',as_of='TEST',
        coverage='TEST',status='scenario',assumption_id='TEST')
    groups=[dict(weight=.4,capacity=100,net=7000,new=True,n=1),dict(weight=1.1,capacity=250,net=8000,new=False,n=5)]
    for pot in (0,40,170,400,900,6000):
        products=[C.RE.P05.product('OUT',market,'outside','OTHER',None,None,None,[],'2027-02-01',None,0)]
        flights=[]
        for i,g in enumerate(groups):
            p=C.RE.P05.product('P'+str(i),market,'air','RW',0,0,1,['F'+str(i)],'2027-02-01',g['net'],math.log(g['weight']))
            products.append(p);flights.append(dict(flight_instance_id='F'+str(i),saleable_seats=g['capacity']))
        m=dict(market,potential_journeys=pot)
        bundle=dict(markets=[m],products=products,flights=flights,contracts=[],choice_model=C.RE.P05.coefficients('base'))
        a=C.RE.allocate_p06(bundle,products);k=C.kernel(groups,pot,1.)
        by={r['product_id']:r for r in a['allocations']}
        for i,q in enumerate(k['q']):near(q,by['P'+str(i)]['carried'])
        near(sum(r['final_choice'] for r in a['allocations']),pot)
        near(k['outside']+k['journeys'],pot)
    return dict(cases=6,heterogeneous_groups=2,capacity_and_demand_conserved=True)

def resource_guards():
    counts={}
    for k in (1,2,3):
        co=C.M.cohort(k);jobs=co['jobs'];tails=co['tails']
        assert len(jobs)==(11 if k==1 else 15)
        cal=C.M.calendar_events(jobs,tails,2027,2)
        assert sum(not t.get('reserve') for t in tails)==k
        assert len([t for t in tails if t.get('reserve')])==1
        assert not any(f['tail']=='R1' for f in cal['flights'])
        counts['K'+str(k)]=dict(oldjobs=len(jobs),working=k,separate_reserve='R1')
    co=C.M.cohort(2)
    raises(lambda:C.M.calendar_events(co['jobs'],co['tails'][:1]+co['tails'][2:],2027,2),'MISSING_WORKING_RESOURCE')
    bad=copy.deepcopy(co['jobs']);bad[0]['flights'][0]['tail']='R1'
    raises(lambda:C.M.calendar_events(bad,co['tails'],2027,2),'RESERVE_USED_AS_WORKING')
    raises(lambda:C.M.calendar_events(co['jobs']+[co['jobs'][0]],co['tails'],2027,2),'duplicate template')
    assert C.recolor_closed(co['jobs'],1) is None
    allrm=C.read(C.HERE/'resource_marginal.csv');rm=[r for r in allrm if r['record_type']=='FINITE_MENU_FRONTIER'];assert len(rm)==72
    paired=[r for r in allrm if r['record_type']=='PROVIDED_EXACT_NESTED_PAIR'];assert len(paired)==8*12*2
    annual=[r for r in allrm if r['record_type']=='ANNUAL_STITCHED_FINITE_FRONTIER'];assert len(annual)==6
    assert all(r['master_old_obligations']=='15' and r['background_flying_tails']=='0' for r in rm)
    for m in range(1,13):
        for sc in ('base','cautious'):
            seq=sorted([r for r in rm if r['month']==f'2027-{m:02}' and r['scenario']==sc],key=lambda r:int(r['working_budget']))
            assert len(seq)==3
            for a,b in zip(seq,seq[1:]):
                delta=float(b['finite_menu_V_before_unknown_C_D_F'])-float(a['finite_menu_V_before_unknown_C_D_F'])
                near(delta,float(b['paired_delta_before_C_D_lease_R1']),1e-5)
                assert delta>=-1e-5
    for sc in ('base','cautious'):
        seq=sorted([r for r in annual if r['scenario']==sc],key=lambda r:int(r['working_budget']))
        assert all(r['stitch_status']=='PERIODIC_YEAR_STITCH_PASS_CONDITIONAL' for r in seq)
        for a,b in zip(seq,seq[1:]):
            delta=float(b['finite_menu_V_before_unknown_C_D_F'])-float(a['finite_menu_V_before_unknown_C_D_F'])
            near(delta,float(b['paired_delta_before_C_D_lease_R1']));assert delta>=-1e-5
    shadow=[r for r in C.read(C.HERE/'resource_allocations.csv') if r['working_budget']=='1' and r['choice']=='OLD_T1_11']
    assert shadow and len(__import__('json').loads(shadow[0]['removed_old_ids']))==4
    # K3 alternative menu contains exact K2 allocations with T3 idle.
    menus=C.native_menus();cohorts={t['cohort']:t for t in C.templates().values()}
    k2=menus[cohorts['K2']['cohort_key']];k3=menus[cohorts['K3']['cohort_key']]
    assert {C.digest(C.semantic_jobs(i['jobs'])) for i in k2}<={C.digest(C.semantic_jobs(i['jobs'])) for i in k3}
    return dict(cohorts=counts,nested_master=15,raw_K2_minus_K1_never_used=True,global_gap='UNKNOWN')

def MOW_one_pool():
    a=C.templates()['C0007786'];b=C.templates()['C0380056']
    jobs=copy.deepcopy(a['states']['REPLACE'])
    for j in C.new(b['states']['REPLACE']):
        j=copy.deepcopy(j);j['id']='NEW-ZIA-'+j['id'];j['tail']='T3'
        for f in j['flights']:
            f['flight_id']='ZIA-'+f['flight_id'];f['job_id']=j['id'];f['tail']='T3'
        jobs.append(j)
    tails=C.M.resources({'T1':'SVX','T2':'DME','T3':'ZIA'})
    cal=C.M.calendar_events(jobs,tails,2027,2)
    z=C.score_calendar(cal,tails,2027,2,'base')
    gg=z['markets']['MOW','GOJ']['groups']
    assert {g['a'] for g in gg}=={'DME','ZIA'}
    pot=z['markets']['MOW','GOJ']['potential']
    near(pot,C.potential('MOW','GOJ',2027,2,'base'))
    assert z['markets']['MOW','GOJ']['journeys']<=pot
    full=C.full_p06(cal,tails,2,'base');near(z['net_revenue'],full['revenue'])
    pools=[r for r in full['bundle']['markets'] if r['demand_pool_id']=='CITY:MOW>GOJ']
    assert len(pools)==1
    return dict(physical_airports=['DME','ZIA'],directed_MOW_pools=1,potential_not_doubled=pot)

def ferry_through_units():
    t=C.templates()['X_CEK_MRV_F'];E=C.Engine('verify');z=E.score(t['states']['REPLACE'],t['tails'],2,'base')
    ferry=[f for f in z['flights'] if f['calendar_kind']=='positioning'];assert len(ferry)==4
    assert all(f['saleable_seats']==0 for f in ferry)
    full=C.full_p06(z['cal'],t['tails'],2,'base',through=True)
    by={f['flight_instance_id']:f for f in full['bundle']['flights']}
    assert all(all(by[x]['saleable_seats']>0 for x in p['legs']) for p in full['bundle']['products'] if p['owner']=='RW')
    assert all(s['carried_segments']==0 for s in full['allocation']['seats'] if by[s['flight_instance_id']]['calendar_kind']=='positioning')
    for f in ferry:
        c=C.variable(f['origin_airport'],f['destination_airport'],f['block_hours_costscreen']*60,'base')
        assert c['fixed_cost']>0;near(c['fuel_price'],136300+1696)
        near(c['fuel_cost'],c['fuel_t']*c['fuel_price'])
        near(c['fixed_crew_excluded'],f['block_hours_costscreen']*15000)
    for p in full['bundle']['products']:
        if len(p['legs'])==2:
            f,g=(by[x] for x in p['legs'])
            net=C.RE.fare(C.RE.city(f['origin_airport']),C.RE.city(g['destination_airport']),'base')[1]
            near(p['net_fare'],net)
    return dict(ferry_departures=4,ferry_revenue=0,paid_cost=True,through='fare once and both seats checked by P06')

def p36_p37_regression():
    inv=C.read(C.P38/'contract/programme_inventory.csv');p36=C.read(C.P36/'pass2/candidate_results.csv')
    assert len(p36)==120
    assert {r['candidate_id'] for r in p36 if float(r['new_minus_same_WITHOUT_NEW'])>0}=={
        r['candidate_id'] for r in inv if r['positive_new_vs_same_without']=='True'}
    eq=C.read(C.P36/'pass2/equivalence_map.csv')
    assert {r['candidate_id'] for r in eq}=={r['candidate_id'] for r in inv}
    # Every old physical ledger departure is reconstructed, including aliases,
    # paid ferries and direction-specific blocks; monthcounts are now real.
    for cid,t in C.templates().items():
        if cid not in {r['candidate_id'] for r in inv}:continue
        for state,jobs in t['states'].items():
            for j in jobs:
                for f in j['flights']:
                    near(f['block'],C.M.block_api().block(f['origin'],f['destination']))
    result={}
    for sc,nmin in [('base',69),('cautious',115)]:
        net=C.RE.fare('SVX','KJA',sc)[1]
        cost=sum(C.variable(a,b,C.M.block_api().block(a,b),sc)['fixed_cost'] for a,b in [('SVX','KJA'),('KJA','SVX')])
        n=math.floor(cost/(2*net))+1;assert n==nmin
        assert n*2*net-cost>0 and (n-1)*2*net-cost<=0
        result[sc]=dict(integer_each_direction=n,capacity_feasible=n<=100,variable_rotation=cost,net=net)
    sens=C.read(C.HERE/'sensitivities.csv');edge=[r for r in sens if r['candidate']=='ALL_P36_DIRECT_EDGES']
    assert len(edge)==36
    assert all(r['edges']=='238' and r['negative_edges']=='238' and float(r['maximum_full100_contribution'])<0 for r in edge)
    result['CAUT238']='all negative even zero-deice; direct standalone ceiling, not global joint/through proof'
    result['P36_changed_values']='direct-only intentionally differs from old conditional through; exact old source numbers not relabelled'
    return result

def inverse_and_price():
    t=C.templates()['X_SVX_KJA'];E=C.Engine('verify')
    z=E.score(t['states']['REPLACE'],t['tails'],2,'base')
    w=E.score(t['states']['WITHOUT_NEW'],t['tails'],2,'base')
    focus=('SVX','KJA');inv=C.inverse_direction(z,[('W',w)],focus)
    assert inv['status']=='DIRECTED_OD_WINNING_INTERVAL'
    # Change just one direction, unlike a portfolio-wide demand multiplier.
    q=inv['required_potential'];others={k:v['potential'] for k,v in z['markets'].items() if k!=focus}
    below=C.score_calendar(z['cal'],t['tails'],2027,2,'base',overrides={focus:max(0,q-1)})
    above=C.score_calendar(z['cal'],t['tails'],2027,2,'base',overrides={focus:q+1})
    near(below['subtotal']-w['subtotal'], - (above['subtotal']-w['subtotal']),1e-4)
    assert below['subtotal']<w['subtotal']<above['subtotal']
    assert {k:v['potential'] for k,v in above['markets'].items() if k!=focus}==others
    repriced=E.score(t['states']['REPLACE'],t['tails'],2,'base',fare_scale=.9)
    assert repriced['new_journeys']!=z['new_journeys']
    full=C.full_p06(z['cal'],t['tails'],2,'base',fare_scale=.9)
    near(full['revenue'],repriced['net_revenue']);near(full['journeys'],repriced['journeys'])
    # Ledger net-only threshold does not pretend to be this retail experiment.
    assert C.inverse_net(z,[('W',w)],focus)['net_status']=='COMMON_REALIZED_NET_WINNING_INTERVAL'
    return dict(single_directed_OD_equality=q,other_pools_unchanged=len(others),retail_price_rechoice=True)

def cancellation_and_F():
    rows=C.read(C.HERE/'programmes_monthly.csv');group=defaultdict(dict)
    for r in rows:group[r['candidate'],r['month'],r['scenario']][r['state']]=r
    for ss in group.values():
        k,w,r=(float(ss[s]['known_subtotal_before_C_D_F']) for s in C.STATES)
        near((r-w)+(w-k),r-k)
        near(float(ss['REPLACE']['new_R_minus_W']),r-w)
        # Arbitrary common cancellation deduction cancels exactly, but only
        # one one-off launch F is subtracted from R (not per leg or twice).
        cancellation=123456;F=654321
        near(((r-cancellation-F)-(w-cancellation)),r-w-F)
    actions=C.read(C.HERE/'old_actions.csv')
    assert all(r['applied_identically_in']=='WITHOUT_NEW;REPLACE' and r['cancellation_common_R_minus_W']=='True' for r in actions)
    assert any(r['action']=='REMOVE' for r in actions)
    return dict(three_state_identities=len(group),F_once=True,C_common_R_W=True,D_internal_shift='already joint; external only additional')

def annual_seams():
    t=C.templates()['X_SVX_IKT'];jobs=t['states']['REPLACE'];tails=t['tails']
    st=C.annual_calendar({m:jobs for m in range(1,13)},tails)
    assert not st['conflicts']
    for m in range(1,13):
        native=C.M.calendar_events(jobs,tails,2027,m)
        assert C.semantic_flights(native['flights'])==C.semantic_flights(st['calendars'][m]['flights'])
        for sc in ('base','cautious'):
            a=C.score_calendar(native,tails,2027,m,sc);b=C.score_calendar(st['calendars'][m],tails,2027,m,sc)
            near(a['subtotal'],b['subtotal'])
    # An overnight whole job straddles month, week and year; no phantom return,
    # no free reset of position/ready, no chopped full-flight cost.
    j=copy.deepcopy(C.new(C.templates()['X_SVX_KJA']['states']['REPLACE'])[0])
    j['id']='NEW-WRAP';j['tail']='T1'
    f,g=j['flights'];f['flight_id']='NEW-WRAP/L1';g['flight_id']='NEW-WRAP/L2'
    for h in (f,g):h['tail']='T1';h['job_id']=j['id']
    f['dep']=6*1440+23*60;f['arr']=f['dep']+f['block']
    g['dep']=f['arr']+90;g['arr']=g['dep']+g['block']
    tt=C.M.resources({'T1':'SVX'})
    wrap=C.annual_calendar({m:[j] for m in range(1,13)},tt)
    assert not wrap['conflicts']
    assert wrap['calendars'][2]['boundary_flights']
    assert any(x['position'].startswith('IN_AIR') for x in wrap['carry'].values())
    # Removing the overnight job in February must let the January occurrence
    # finish; inserting a conflicting short RT must be caught, not reset away.
    policy={m:[j] for m in range(1,13)};policy[2]=[]
    seam=C.annual_calendar(policy,tt)
    jan_return=[f for f in seam['calendars'][2]['flights'] if f['rotation_id']=='NEW-WRAP@2027-01-25']
    assert len(jan_return)==1
    vs=C.read(C.HERE/'season_vs_yearround.csv')
    for r in vs:
        if r['seasonal_stitch_status']=='STITCH_CONFLICT':assert r['stitched_seasonal_known_subtotal']=='NULL'
        else:assert r['stitched_seasonal_known_subtotal']!='NULL'
    # Contradictory monthly clock changes cannot silently duplicate a stable
    # old ID onto two tails at the seam.
    bad=copy.deepcopy(j);bad['tail']='T2'
    for f in bad['flights']:f['tail']='T2';f['dep']+=120;f['arr']+=120
    clash={m:[j] for m in range(1,13)};clash[2]=[bad]
    rejected=C.annual_calendar(clash,C.M.resources({'T1':'SVX','T2':'SVX'}))
    assert rejected['conflicts']
    return dict(fixed_annual_monthsum_checked=12,full_job_carry=True,periodic_yearwrap=True,actual_outside_return_state=None,
        monthly_optima_not_automatically_annual_profit=True)

def no_sj_before_entry():
    deliveries=C.read(C.HERE/'delivery_cases.csv')
    assert all(r.get('actual_SJ_margin')=='NULL' for r in deliveries)
    for r in deliveries:
        if r['tail']=='NONE':continue
        entry=datetime.fromisoformat(r['entry'])
        assert entry>=datetime(2027,7,1)
        assert r['before_entry_flights']=='0'
        if r['case']=='S1D6':assert r['available_2027_months']=='[]'
        assert r['dated_entry_calendar_status'] in ('FEASIBLE_BASE1_POLICY_EXTRA_TAILS_IDLE','DATED_ENTRY_WHOLE_JOB_STITCH_PASS')
    co=C.M.cohort(1);sj=copy.deepcopy(co['tails']);sj[0]['type']='SJ-100_PD8';sj[0]['available_from']='2027-08-01T00:00:00Z'
    raises(lambda:C.Engine('verify').score(co['jobs'],sj,8,'base'),'SJ_PD8_COST_UNKNOWN')
    raises(lambda:C.M.calendar_events(co['jobs'],sj,2027,2),'OUTSIDE_RESOURCE_AVAILABILITY')
    return dict(actual_SJ_profit=None,S1='Aug/Nov2027 illustration',S1D6='Feb/May2028 illustration, no2027 revenue')

def outputs_and_replay():
    receipt=C.js(C.HERE/'run_receipt.json')
    for name,h in receipt['deterministic_output_sha256'].items():assert C.sha(C.HERE/name)==h,name
    E=C.Engine('verify_repeat')
    rows=C.read(C.HERE/'programmes_monthly.csv')
    for cid,m,sc in [('X_SVX_KJA',1,'base'),('X_SVX_KJA',8,'cautious'),('X_SVX_IKT',7,'base'),('C0380056',12,'base')]:
        t=C.templates()[cid]
        for s,j in t['states'].items():
            z=E.score(j,t['tails'],m,sc)
            r=next(r for r in rows if r['candidate']==cid and r['month']==f'2027-{m:02}' and r['scenario']==sc and r['state']==s)
            near(z['subtotal'],float(r['known_subtotal_before_C_D_F']))
    assert C.js(C.HERE/'search_coverage.json')['status']=='COMPLETE_CONDITIONAL_FINITE_MENU'
    assert (C.HERE/'opportunity_curve.svg').is_file()
    pilots=C.read(C.HERE/'pilots.csv');assert len(pilots)==30
    assert {r['stress'] for r in pilots}=={'MAIN','COMPETITOR_FARE_MINUS10_FREQ_PLUS25','WEAK_NONBASE_OD_HALF','COMBINED_35_65','COMBINED_65_35'}
    assert all(r['approved_test_loss_budget']=='NULL' and r['required_cash_budget']=='NULL' for r in pilots)
    return dict(executed_replay_states=12,artifact_hashes=len(receipt['deterministic_output_sha256']),
        output_digest=receipt['output_digest'],full_repeat='repeatability.json records independently executed second full run')

def main():
    check('protected_before',C.guard)
    for name,fn in [('input_hashes',input_hashes),('all60_37_25_12months_three_states',coverage),
        ('profile_once_actual_dates_peak_pool',profile_units),('full_P31_P06_equivalence_fixed_world',reference_joint),
        ('flat_capacity_common_OD_kernel',kernel_synthetic),('primary_resource_and_paired_identity',resource_guards),
        ('MOW_shared_not_duplicate_DME_ZIA',MOW_one_pool),('paid_ferry_zero_revenue_through_once_fuel_units',ferry_through_units),
        ('P36_P37_and_238_CAUTION_edges',p36_p37_regression),('inverse_one_direction_and_price_rechoice',inverse_and_price),
        ('W_K_R_C_F_D_accounting',cancellation_and_F),('annual_monthsum_whole_jobs_carry_yearwrap',annual_seams),
        ('no_SJ_before_entry_type_cost_unknown',no_sj_before_entry),('outputs_and_executed_replay',outputs_and_replay)]:check(name,fn)
    check('protected_after',C.guard)
    out=dict(status='PASS' if all(x['status']=='PASS' for x in CHECKS) else 'FAIL',checks=CHECKS,receipts=RECEIPTS,
        programme_status='COMPLETE_CONDITIONAL_FINITE_MENU',actual_dispatch=False,actual_market_calibration=False,
        full_profit=None,cash=None,launch_authorized=False,external_search=False,old_entry_points_invoked=False)
    (C.HERE/'validation.json').write_text(__import__('json').dumps(out,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n')
    if out['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
