#!/usr/bin/env python3
"""Meaningful numerical, shared-pool, calendar and integrity checks; offline."""
import copy
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode=True
import calculate as c

H=c.HERE
checks=[]


def check(name,condition,detail=''):
    checks.append(dict(name=name,pass_=bool(condition),detail=detail))
    if not condition:
        raise AssertionError(name+': '+detail)


def near(a,b,tol=1e-5):
    return math.isclose(a,b,rel_tol=1e-9,abs_tol=tol)


def rejects(name,fn):
    try:
        fn()
    except (ValueError,AssertionError) as exc:
        check(name,True,str(exc))
    else:
        check(name,False,'invalid input accepted')


def pattern(name='test',a='SVX',b='TJM',days=(0,2,4),hour=6):
    return dict(pattern_id=name,airports=[a,b,a],weekdays=list(days),departure_hour_utc=hour)


def evaluate(ps,**kwargs):
    return c.evaluate_combined_programme(ps,keep_patterns=kwargs.pop('keep_patterns',[]),start=kwargs.pop('start','2027-07-01'),end=kwargs.pop('end','2027-07-31'),**kwargs)


def all_conserved(z):
    for name in ['programme','keep']:
        branch=z[name]
        alloc=branch['allocation'];bundle=branch['bundle']
        for seat in alloc['seats']:
            check('physical seat conservation '+name+' '+seat['flight_instance_id'],seat['carried_segments']+seat['unfilled_contract_seats']<=seat['saleable_seats']+1e-6)
        for m in bundle['markets']:
            q=sum(a['final_choice'] for a in alloc['allocations'] if (a['demand_pool_id'],a['month'],a['customer_segment'])==(m['demand_pool_id'],m['month'],m['customer_segment']))
            check('potential pool conservation '+name+' '+m['demand_pool_id']+' '+m['month'],near(q,m['potential_journeys']))


def run():
    check('P05 gross-to-net units',near(c.P05.net_fare(20000,.1,.08),20000/1.1*.92))
    check('VAT/distribution not multiplied twice',not near(c.P05.net_fare(20000,.1,.08),20000/1.1*.92*.92))
    co=c.costs('SVX','TJM','base')
    check('fuel tonnes are hours times t/hour plus cycle',near(co['fuel_t'],co['block_hours_costscreen']*1.55+.2))
    check('fuel uplift applied once',near(co['fuel_price'],136300+1696))
    check('known cost basket identity',near(co['fixed_cost'],co['fuel_cost']+co['other_cost']))
    check('national season shares sum1 in leap year',near(sum(c.P05.monthly_profile(2028).values()),1))
    check('leap year dated grid 366 days',len(list(c.days_in('2028-01-01','2028-12-31',range(7))))==366)
    # One-product fast path must agree with reused P06, including binding caps.
    for potential in (0,5,100,1000):
        for cap in (10,100):
            for w in (.1,.6,5):
                m=dict(demand_pool_id='T',month='2027-07',customer_segment='all',potential_journeys=potential,market_basis='potential_travel',mapping_to_potential='synthetic',source_id='TEST',source_period='test',as_of='2026-11-12',coverage='test',status='scenario',assumption_id='TEST')
                out=c.P05.product('out',m,'outside','OTHER',None,None,None,[],'2027-07-01',None,0)
                own=c.P05.product('rw',m,'air','RW',0,0,1,[],'2027-07-01',1,math.log(w),cap)
                b=dict(markets=[m],products=[out,own],flights=[],contracts=[],choice_model=c.P05.coefficients())
                z=c.allocate_p06(b,b['products'])
                q=next(a['carried'] for a in z['allocations'] if a['product_id']=='rw')
                check(f'fast path equals P06 potential{potential}/cap{cap}/weight{w}',near(q,c.capacity_choice(potential,w,cap)))
    ps=[pattern()]
    z=evaluate(ps,existing_slots=1,reserve_available=True)
    all_conserved(z)
    f=z['programme']['bundle']['flights']
    check('roundtrip equal outward/return paid legs',Counter((x['origin_airport'],x['destination_airport']) for x in f)[('SVX','TJM')]==len(f)/2)
    check('return cost includes both sectors',near(z['programme']['known_cost'],len(f)*co['fixed_cost']))
    check('full result remains UNKNOWN without F/donor',z['full_P_minus_KEEP'] is None and z['cash'] is None)
    same=evaluate(ps,keep_patterns=ps)
    check('P identical KEEP known delta zero',near(same['known_increment_P_minus_KEEP_before_F_donor'],0))
    paid=evaluate(ps,donor_loss=100,omitted_F=200)
    check('donor and F deducted once',near(paid['full_P_minus_KEEP'],paid['known_increment_P_minus_KEEP_before_F_donor']-300))
    rejects('missing KEEP is not zero',lambda:c.evaluate_combined_programme(ps))
    rejects('open pattern rejected',lambda:evaluate([dict(pattern_id='bad',airports=['SVX','TJM'],weekdays=[1])]))
    rejects('MOW cannot be physical endpoint',lambda:evaluate([pattern(a='MOW',b='OMS')]))
    rejects('duplicate pattern IDs rejected',lambda:evaluate(ps+ps))
    rejects('duplicate physical scheduled movement rejected',lambda:evaluate([pattern('one'),pattern('two')]))
    rejects('duplicate weekday rejected',lambda:evaluate([pattern(days=(1,1))]))
    # Same endpoint shared across two physical airport alternatives, one city pool.
    dme=pattern('DME','DME','OMS',(1,4))
    zia=pattern('ZIA','ZIA','OMS',(1,4))
    shared={'MOW>OMS/2027-07':100,'OMS>MOW/2027-07':100}
    solo1=evaluate([dme],demand_overrides=shared);solo2=evaluate([zia],demand_overrides=shared);joint=evaluate([dme,zia],demand_overrides=shared)
    all_conserved(joint)
    check('Moscow one directed city pool per month',len(joint['programme']['bundle']['markets'])==2)
    check('Moscow common potential not duplicated',near(sum(m['potential_journeys'] for m in joint['programme']['bundle']['markets']),sum(m['potential_journeys'] for m in solo1['programme']['bundle']['markets'])))
    check('solo marginal sums are not joint result',not near(joint['known_increment_P_minus_KEEP_before_F_donor'],solo1['known_increment_P_minus_KEEP_before_F_donor']+solo2['known_increment_P_minus_KEEP_before_F_donor']))
    # Different DOW with same count cannot create unidentified calendar uplift.
    dw1=evaluate([pattern(days=(0,2,4))],start='2027-01-04',end='2027-01-17')
    dw2=evaluate([pattern(days=(1,3,5))],start='2027-01-04',end='2027-01-17')
    check('same-count DOW permutation no fictitious demand lift',near(dw1['programme']['net_revenue'],dw2['programme']['net_revenue']))
    fullmonth=evaluate([pattern()],start='2027-01-01',end='2027-01-31')
    check('partial horizon demand prorates identical external pool',near(sum(m['potential_journeys'] for m in dw1['programme']['bundle']['markets'])/sum(m['potential_journeys'] for m in fullmonth['programme']['bundle']['markets']),14/31))
    zero=evaluate(ps,existing_slots=0,delivery_scenario='S0')
    check('E0 S0 cannot add operating programme',zero['resource_necessary_screen']=='INFEASIBLE_AT_GIVEN_ENVELOPE')
    early=evaluate(ps,existing_slots=0,delivery_scenario='S1',start='2027-01-01',end='2027-01-31')
    check('no new SJ100 resource before H22027',early['resource_necessary_screen']=='INFEASIBLE_AT_GIVEN_ENVELOPE')
    august=evaluate(ps,existing_slots=0,delivery_scenario='S1',start='2027-08-01',end='2027-08-31',reserve_available=True)
    check('S1 dated August entry only conditional resource',not august['daily_block_violations'])
    delayed=evaluate(ps,existing_slots=0,delivery_scenario='S1D6',start='2027-08-01',end='2027-08-31')
    check('S1D6 same August programme resource fails',bool(delayed['daily_block_violations']))
    check('reserve not inferred from working slots',evaluate(ps)['resource_necessary_screen']=='RESERVE_UNKNOWN_GATE')
    check('missing protected reserve explicit failure',evaluate(ps,reserve_available=False)['resource_necessary_screen']=='INFEASIBLE_AT_GIVEN_ENVELOPE')
    tri=evaluate([dict(pattern_id='tri',airports=['SVX','KUF','UFA','SVX'],weekdays=[1])])
    all_conserved(tri)
    tf=tri['programme']['bundle']['flights']
    check('triangle exactly three paid legs per cycle',len(tf)==3*len({x['departure_utc'][:10] for x in tf}))
    balance=Counter()
    for x in tf:balance[x['origin_airport']]+=1;balance[x['destination_airport']]-=1
    check('triangle returns aircraft at every node',all(v==0 for v in balance.values()))
    # A through journey and an adjacent direct journey consume the same dated
    # physical flight, but recognise one journey fare each, not one per leg.
    m=next(x for x in tri['programme']['bundle']['markets'] if x['demand_pool_id']=='CITY:SVX>UFA')
    twolegs=[x['flight_instance_id'] for x in tf[:2]]
    extra=c.P05.product('shared-through-test',m,'air','RW',10000,200,1,twolegs,'2027-07-06',9000,10)
    shared_tri=evaluate([dict(pattern_id='tri',airports=['SVX','KUF','UFA','SVX'],weekdays=[1])],extra_products={'P':[extra]})
    all_conserved(shared_tri)
    alloc=shared_tri['programme']['allocation']
    products={x['product_id']:x for x in shared_tri['programme']['bundle']['products']}
    for leg in twolegs:
        load=sum(a['carried'] for a in alloc['allocations'] if leg in products[a['product_id']]['legs'])
        row=next(x for x in alloc['seats'] if x['flight_instance_id']==leg)
        check('shared adjacent and through inventory '+leg,near(load,row['carried_segments']) and load<=100+1e-6)
    revenue=sum(a['carried']*products[a['product_id']]['net_fare'] for a in alloc['allocations'] if a['owner']=='RW')
    check('shared multi-leg journey net fare recognised once',near(revenue,shared_tri['programme']['net_revenue']))
    # Exact ops module reuse: complete request and no geometry on missing blocks.
    request=json.loads((c.ROOT/'ops_inputs/example_request.json').read_text())
    empty=copy.deepcopy(request);empty['patterns']=[]
    dates=[p['start'] for p in request['patterns']]+[p['end'] for p in request['patterns']]
    oz=c.evaluate_combined_programme([],keep_patterns=[],start=min(dates),end=max(dates),existing_slots=2,
                                     calendar_requests={'P':request,'KEEP':empty})
    check('ops calendar complete synthetic example admitted conditionally',oz['status']=='CONDITIONAL_CALENDAR_PENDING_CREW_MRO_OPS')
    check('ops calendar seven synthetic physical legs',len(oz['programme']['bundle']['flights'])==7)
    check('ops explicit block used not geometry',near(sum(f['block_hours_costscreen'] for f in oz['programme']['bundle']['flights']),7))
    bad=copy.deepcopy(request);bad['blocks']=[]
    missing=c.evaluate_combined_programme([],keep_patterns=[],start=min(dates),end=max(dates),calendar_requests={'P':bad,'KEEP':empty})
    check('missing block rejects full composition no partial economics',missing['status']=='INFEASIBLE_CALENDAR_COMPOSITION_NOT_TRIMMED' and missing['known_increment_P_minus_KEEP_before_F_donor'] is None)
    duplicate=copy.deepcopy(request);duplicate['blocks'].append(copy.deepcopy(duplicate['blocks'][0]))
    rejects('multiple-source blocks must be selected explicitly',lambda:c.evaluate_combined_programme([],keep_patterns=[],calendar_requests={'P':duplicate,'KEEP':empty}))
    changed=copy.deepcopy(empty);changed['tails'][0]['available_from']='2027-02-01T00:00:00Z'
    rejects('P KEEP cannot change resource calendars',lambda:c.evaluate_combined_programme([],keep_patterns=[],calendar_requests={'P':request,'KEEP':changed}))
    # Artifact accounting identities and screen coverage, not mock implementation tests.
    rows=c.read(H/'fastscreen.csv')
    u=c.read(H/'route_universe.csv')
    keys={c.pair(r['origin'],r['destination']) for r in c.read(c.ROOT/'audit/route_universe.csv')}
    check('all 1317 seed city pairs preserved',len(keys)==1317 and keys <= {(r['city_origin'],r['city_destination']) for r in u})
    check('shortlist 12 to20',12<=len(c.read(H/'shortlist.csv'))<=20)
    check('all finite frequency grid values screened',set(int(r['added_pairs_week']) for r in rows)==set(c.GRID))
    check('base and cautious same finite grid years',{(r['physical_pair'],r['year'],r['added_pairs_week']) for r in rows if r['scenario']=='base'}=={(r['physical_pair'],r['year'],r['added_pairs_week']) for r in rows if r['scenario']=='cautious'})
    check('short distance is retained',any(float(r.get('distance_km') or 99999)<500 for r in rows if r.get('distance_km') not in ('UNKNOWN','')))
    check('competitor flag not automatic rejection',any(r.get('competition_status','').startswith('legacy_direct_flag') and r['screen_status']=='CONDITIONAL_NOT_PROFIT' for r in rows))
    ordinary=[r for r in rows if r.get('screen_status')=='CONDITIONAL_NOT_PROFIT']
    for r in ordinary:
        if r['airport_allocation_status']!='single_airport':continue
        revenue=float(r['net_revenue_after']);keep=float(r['keep_net_revenue']);cost=float(r['annual_added_cost']);delta=float(r['known_increment_P_minus_KEEP_before_F_donor'])
        if not near(delta,revenue-keep-cost,tol=.01):raise AssertionError('P KEEP accounting identity '+r['physical_pair'])
        if not near(float(r['new_sector_pax'])-float(r['own_rw_shift_to_new']),float(r['additional_rw_pax']),tol=.01):raise AssertionError('own migration counted new '+r['physical_pair'])
        if not near(float(r['cost_paired_return']),2*float(r['cost_one_leg']),tol=.01):raise AssertionError('return cost missing')
    check('all domestic accounting identities and own migration reconcile',True,str(len(ordinary))+' rows')
    check('MOW unallocated old RW delta stays unknown',all(r['known_increment_P_minus_KEEP_before_F_donor']=='UNKNOWN' for r in ordinary if r['airport_allocation_status']!='single_airport'))
    check('full result never invented',all(r['full_P_minus_KEEP']=='UNKNOWN' for r in rows))
    check('all screen support zero NS',all(r['support']=='NS' and r.get('route_support_rub') in ('0.0','0','') and r.get('fuel_credit_rub') in ('0.0','0','') for r in rows))
    check('BRU identity unresolved no numeric route admission',any(r['pair_id']=='BRU-SVX' and r['scope']=='unresolved_endpoint' for r in u) and all(r['known_increment_P_minus_KEEP_before_F_donor']=='UNKNOWN' for r in rows if r['pair_id']=='BRU-SVX'))
    check('13 analogue source records preserved no overwrite',len(c.read(H/'block_admission.csv'))==13)
    check('opposite directions require exact same variant',all(r.get('profit','UNKNOWN')=='UNKNOWN' for r in c.read(H/'ops_analogue_cost_cases.csv')))
    mech=c.read(H/'mechanism_thresholds.csv')
    blocks=[r for r in mech if r['mechanism']=='partner_block']
    check('block q bought once and sold <= bought',all(float(r['s_sold'])<=float(r['q_purchased']) and near(float(r['c_max_RUB_per_seat_before_F']),float(r['s_sold'])*float(r['net_retail_scenario_RUB'])/float(r['q_purchased']),tol=.01) and r['RW_operating_pax']=='0' for r in blocks))
    support=c.read(H/'support_cases.csv')
    check('CM future award remains UNKNOWN',all(r['actual_future_award']=='UNKNOWN' and r['conditional_increment']=='UNKNOWN' for r in support if r['support_case']=='CM'))
    check('canonical source admission all27 reviewed fields',sum(r['path'].startswith('source_review/source_admission.csv#') for r in c.read(H/'source_admission.csv'))==27)
    # Check protected state before and after deterministic repeat.
    before=json.loads((H/'protected_snapshot.json').read_text())
    def protected():
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.WORKSPACE,text=True).strip()
        check('HEAD unchanged',head==before['head'])
        for name in ('tracked','context30'):
            for path,sha in before[name].items():
                f=c.WORKSPACE/path
                if (c.digest(f) if f.is_file() else None)!=sha:raise AssertionError('protected changed '+path)
            check(name+' contents unchanged',True,str(len(before[name])))
    protected()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    key_outputs=['fastscreen.csv','shortlist.csv','directed_route_cases.csv','frequency_increment_cases.csv','mechanism_thresholds.csv','patterns.json','triangle_cases.csv','APIhandoff.json','source_admission.csv','manifest.json']
    subprocess.run([sys.executable,str(H/'calculate.py')],cwd=c.ROOT,env=env,check=True,capture_output=True,text=True)
    first={x:c.digest(H/x) for x in key_outputs}
    subprocess.run([sys.executable,str(H/'calculate.py')],cwd=c.ROOT,env=env,check=True,capture_output=True,text=True)
    second={x:c.digest(H/x) for x in key_outputs}
    check('two independent important-output builds byte-identical',first==second)
    for name,sha in json.loads((H/'manifest.json').read_text())['outputs'].items():
        if c.digest(H/name)!=sha:raise AssertionError('output manifest mismatch '+name)
    check('all output manifest hashes match',True)
    protected()
    return first


if __name__=='__main__':
    error=None
    hashes={}
    try:
        hashes=run()
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)
    result=dict(status='PASS' if error is None else 'FAIL',checks_count=len(checks),checks=checks,error=error,
                deterministic_repeat_sha256=hashes,
                scope='mechanical/scenario checks only; NOT observed OD, calibrated RW profit, dispatch approval or global optimum',
                protected_tracked_files=436,protected_context30_files=146,new_numeric_observed_OD_netyield_contracts=0)
    c.dump('validation.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','deterministic_repeat_sha256')},ensure_ascii=False))
    if error:sys.exit(1)
