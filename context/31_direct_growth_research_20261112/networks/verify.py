#!/usr/bin/env python3
"""Mechanical/scenario verification, not the requested next independent review."""
import sys
sys.dont_write_bytecode=True
import copy
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import calculate as C

HERE=C.HERE
checks=[]


def check(name, condition, detail=''):
    checks.append(dict(name=name,pass_=bool(condition),detail=detail))
    if not condition: print('FAIL',name,detail,flush=True)


def rows(name):
    return C.read(HERE/name)


def hashes():
    return {str(p.relative_to(HERE)):C.sha(p) for p in HERE.rglob('*') if p.is_file() and p.name not in ['validation.json'] and '__pycache__' not in str(p)}


def run():
    protected=json.loads((HERE/'protected_snapshot.json').read_text())
    changed=[s for s,h in protected['files'].items() if not (C.WORKSPACE/s).is_file() or C.sha(C.WORKSPACE/s)!=h]
    check('protected tracked/context30/completed inputs unchanged',not changed,changed[:8])
    check('436 tracked preserved',protected['tracked_count']==436)
    check('HEAD unchanged',subprocess.check_output(['git','rev-parse','HEAD'],cwd=C.WORKSPACE).decode().strip()==protected['head'])
    check('context30 protection present',sum(s.startswith('context/30') for s in protected['files'])==146)

    comparisons=rows('network_comparison.csv'); monthly=rows('monthly_results.csv')
    fs=rows('dated_flights.csv');rs=rows('rotations.csv');ds=rows('resource_checks.csv')
    check('all nine E/S resources',len({r['resource'] for r in comparisons})==9)
    check('main support both zero',all(r['support_route_RUB']=='0' and r['support_fuel_RUB']=='0' for r in monthly))
    check('full programme PnL and cash not invented',all(r['full_incremental_PnL_RUB']=='NULL' and r['incremental_cash_RUB']=='NULL' for r in comparisons))
    check('empty future whole KEEP not zero',all(r['whole_KEEP_cash_RUB']=='NULL' for r in comparisons))
    check('old marketed connection loss remains NULL',all(r['outside_affected_old_RW_and_MQF_marketed_loss_RUB']=='NULL' for r in comparisons))
    check('all main dated flights are explicit diagnostics',all(r['calendar_basis']==C.MAIN_BASIS and r['evidence']==C.MAIN_BASIS for r in fs))
    check('physical airports resolved',all(r['origin']!='MOW' and r['destination']!='MOW' for r in fs))
    check('all rotations close',all(r['closed']=='True' for r in rs))
    check('no unrequested free reserve',all(r['reserve_contract']=='UNKNOWN' and r['protected_reserves']=='1' for r in ds))
    check('daily tails within same N(t)',all(int(r['used_working_tails'])<=int(r['N_working']) for r in ds))
    check('no nominal calendar errors',all(r['position_overlap_entry_block_status']=='CONDITIONAL_PHYSICAL_CONSISTENCY' and not r['errors'] for r in ds))
    check('reserve never works',all(r['tail']!='RES-1' for r in fs))
    check('leap day actually operated',any(r['departure_utc'].startswith('2028-02-29') for r in fs))
    check('no unscaled 52/48 annual multiplier',C.epochs is not None and all(r['crew']=='UNKNOWN' for r in monthly))
    ids=[(r['programme'],r['resource'],r['side'],r['flight_id']) for r in fs]
    check('unique dated physical flightIDs per alternative',len(ids)==len(set(ids)))
    working_by_case={}
    for e in (0,1,2):
        for s in ('S0','S1','S1D6'):
            working_by_case[f'E{e}/{s}']={t['id']:t for t in C.resource(e,s)}
    check('SJ only after common entry and never H1',all(not r['tail'].startswith('SJ-') or r['departure_utc'][:10]>=working_by_case[r['resource']][r['tail']]['available_from'][:10]>='2027-07-01' for r in fs))
    groupm=defaultdict(list)
    for r in monthly: groupm[tuple(r[k] for k in ['programme','resource','scenario','keep_case'])].append(r)
    identities=0
    for r in comparisons:
        if r['programme']=='KEEP': continue
        ms=[m for m in groupm[tuple(r[k] for k in ['programme','resource','scenario','keep_case'])] if m['month'].startswith(r['year'])]
        for field,mf in [('known_increment_upper_conditional_RUB','known_increment_upper_conditional_RUB'),('P_directed_departures','P_departures'),('P_block_hours','P_block_hours')]:
            if field in r and r[field] not in ('NULL',''):
                check('annual equals actual monthly '+str(identities),abs(float(r[field])-sum(float(m[mf]) for m in ms))<1e-4)
                identities+=1
    check('E0/S0 all programmes zero flight resource',all(float(r['P_directed_departures'])==0 and float(r['known_increment_upper_conditional_RUB'])==0 for r in comparisons if r['resource']=='E0/S0'))

    # Same request file is reused by BASE/CAUTIOUS. Check generated times unchanged.
    req=json.loads((HERE/'requests/D3_STAGED_E2_S1.json').read_text())
    a=C.evaluate(req['P'],req['KEEP'],2,'S1','base')
    b=C.evaluate(req['P'],req['KEEP'],2,'S1','cautious')
    check('BASE CAUTIOUS identical physical dated flights',a['ops_results']['P']['flights']==b['ops_results']['P']['flights'])
    check('same shared capacity all main allocations',all(r['seats_ok'] for r in json.loads((HERE/'joint_allocation_checks.json').read_text())))

    # Small, actual dated joint request for targeted edge cases.
    tails=C.resource(1,'S0')
    p=C.pat('TEST',['SVX','OMS','NJC','OMS','SVX'],[1],'2027-01-04','2027-01-04','EX-1')
    pr=C.request([p],tails);kr=C.request([],tails)
    z=C.evaluate(pr,kr,1,'S0','base',hub=True,start='2027-01-04',end='2027-01-10')
    check('dated hub four paid physical legs',len(z['ops_results']['P']['flights'])==4)
    bundle=z['programme']['bundle']; allocation=z['programme']['allocation']
    products={p['product_id']:p for p in bundle['products']}
    through=[p for p in products.values() if p['product_id'].startswith('HUB:')]
    check('both ordered transfer directions exist',len(through)==2 and all(len(p['legs'])==2 for p in through))
    check('dated connection MCT only',all(60<=p['actual_gap_minutes']<=180 for p in through))
    for p in through:
        carried=next(a['carried'] for a in allocation['allocations'] if a['product_id']==p['product_id'])
        check('through journey consumes BOTH legs '+p['product_id'],carried>0 and all(next(s['carried_segments'] for s in allocation['seats'] if s['flight_instance_id']==f)>=carried-1e-6 for f in p['legs']))
    revenue=sum(a['carried']*products[a['product_id']]['net_fare'] for a in allocation['allocations'] if a['owner']=='RW')
    check('through net recognised once',abs(revenue-z['programme']['net_revenue'])<1e-6)
    # Force cross-OD inventory contention. Check simultaneous shared seats/pools.
    heavy=copy.deepcopy(bundle)
    for m in heavy['markets']:m['potential_journeys']=1e6
    aa=C.RE.allocate_p06(heavy,heavy['products'])
    check('shared OD and seats with saturated local+transfer products',all(s['carried_segments']<=s['saleable_seats']+1e-6 for s in aa['seats']) and any(abs(s['carried_segments']-s['saleable_seats'])<1e-6 for s in aa['seats']))
    check('potential conserved under saturated hub contention',all(abs(sum(a['final_choice'] for a in aa['allocations'] if (a['demand_pool_id'],a['month'],a['customer_segment'])==(m['demand_pool_id'],m['month'],m['customer_segment']))-m['potential_journeys'])<1e-6 for m in heavy['markets']))
    # Capacity of either transfer leg zero -> no through journeys on that path.
    for index in (0,1):
        bb=copy.deepcopy(bundle);fid=through[0]['legs'][index]
        for f in bb['flights']:
            if f['flight_instance_id']==fid:f['saleable_seats']=0
        out=C.RE.allocate_p06(bb,bb['products'])
        check('zero transfer leg '+str(index)+' kills journey',next(a['carried'] for a in out['allocations'] if a['product_id']==through[0]['product_id'])==0)
    # Nonbank first partial week has zero connecting passengers by construction.
    hc=rows('dated_connections.csv')
    check('no transfer credited to first nonbank week',all('2027-01-01' not in x['product_id'] and '2027-01-02' not in x['product_id'] and '2027-01-03' not in x['product_id'] for x in hc))

    def rejected(p_req,k_req,e=1,s='S0'):
        try:
            out=C.evaluate(p_req,k_req,e,s,start='2027-01-04',end='2027-01-10')
            return 'programme' not in out or bool(out.get('daily_block_violations'))
        except (ValueError,KeyError):return True
    no_tails=C.request([p],C.resource(0,'S0')); no_k=C.request([],C.resource(0,'S0'))
    check('zero working resource rejects physical programme',rejected(no_tails,no_k,0))
    sj=C.resource(0,'S1');sjp=copy.deepcopy(p);sjp['workingtailids']=['SJ-A']
    check('new SJ in H1 rejected even with order',rejected(C.request([sjp],sj),C.request([],sj),0,'S1'))
    dup=copy.deepcopy(pr);dup['tails'].append(copy.deepcopy(dup['tails'][-1]))
    dupk=copy.deepcopy(kr);dupk['tails'].append(copy.deepcopy(dupk['tails'][-1]))
    check('double-count same reserve rejected',rejected(dup,dupk))
    rp=copy.deepcopy(pr);rp['patterns'][0]['workingtailids']=['RES-1']
    check('protected reserve cannot be working',rejected(rp,kr))
    missing=copy.deepcopy(pr);missing['blocks']=[b for b in missing['blocks'] if (b['origin'],b['destination'])!=('NJC','OMS')]
    check('missing reverse block rejects whole composition no partial money',rejected(missing,kr))
    wrong=copy.deepcopy(pr);wrong['tails'][0]['initial_location']='KUF'
    wrongk=copy.deepcopy(kr);wrongk['tails'][0]['initial_location']='KUF'
    check('positioning not free between airports',rejected(wrong,wrongk))
    overlap=copy.deepcopy(pr);p2=copy.deepcopy(p);p2['id']='TEST2';overlap['patterns'].append(p2)
    check('same tail overlap or physical duplicate rejected',rejected(overlap,kr))
    changed_resource=copy.deepcopy(kr);changed_resource['tails'][0]['initial_location']='KUF'
    check('P KEEP resource calendars cannot differ',rejected(pr,changed_resource))
    # Use valid paired published exact-variant analogue as an independent API control.
    valid=copy.deepcopy(pr);valid['patterns']=[C.pat('PAIR',['SVX','KUF','SVX'],[1],'2027-01-04','2027-01-04','EX-1')]
    valid['tails'][0]['type']='RRJ-95B'
    evidence=[r for r in C.read(C.ROOT/'ops_inputs/directed_blocks.csv') if r['evidence']=='SCENARIO_HISTORICAL_SAME_DIRECTED_ROUTE_VARIANT_ANALOGUE' and r['aircraft_variant']=='RRJ-95B' and {r['origin'],r['destination']}=={'SVX','KUF'}]
    valid['blocks']=[dict(origin=r['origin'],destination=r['destination'],nominal_minutes=float(r['nominal_minutes']),high_minutes=float(r['high_minutes']),aircraft_variant=r['aircraft_variant'],evidence=r['evidence']) for r in evidence]
    vk=copy.deepcopy(valid);vk['patterns']=[]
    zz=C.evaluate(valid,vk,1,'S0',start='2027-01-04',end='2027-01-10')
    check('actual paired same-variant historical analogue API control',len(zz['ops_results']['P']['flights'])==2 and sum(f['block_minutes'] for f in zz['ops_results']['P']['flights'])==205)
    mismatch=copy.deepcopy(valid);mismatch['tails'][0]['type']='RRJ-95LR'
    mk=copy.deepcopy(vk);mk['tails'][0]['type']='RRJ-95LR'
    check('paired analogue cannot silently change aircraft variant',rejected(mismatch,mk))

    print('edge checks finished; deterministic rebuild',flush=True)
    C.build_manifest()
    first=hashes()
    proc=subprocess.run([sys.executable,'-B',str(HERE/'calculate.py')],cwd=C.WORKSPACE,check=False,capture_output=True,text=True)
    check('full build execution success',proc.returncode==0,proc.stdout[-500:]+proc.stderr[-500:])
    second=hashes()
    check('two full builds byte deterministic',first==second,[x for x in first if first.get(x)!=second.get(x)][:8])
    manifest=json.loads((HERE/'manifest.json').read_text())
    check('all output hashes match',all(C.sha(HERE/n)==h for n,h in manifest['outputs'].items()))
    check('all completed input hashes match',all(C.sha(C.ROOT/n)==h for n,h in manifest['inputs'].items()))
    changed=[s for s,h in protected['files'].items() if C.sha(C.WORKSPACE/s)!=h]
    check('protected files unchanged after repeat',not changed,changed[:8])
    C.dump('validation.json',dict(status='PASS_MECHANICAL_CONDITIONAL_NOT_INDEPENDENT_REVIEW' if all(r['pass_'] for r in checks) else 'FAIL',
        checks_count=len(checks),failed_checks=[r for r in checks if not r['pass_']],checks=checks,
        protected_tracked_files=436,protected_context30_files=146,
        deterministic_repeat=True,dispatch_ready=False,full_PnL=None,cash=None,
        new_observed_frequency_OD_netyield_contract_updates=0,
        scope='mechanical and scenario boundary checks only; independent review is NEXT, not performed'))
    print(json.dumps({'checks':len(checks),'failures':len([r for r in checks if not r['pass_']])}),flush=True)
    return 0 if all(r['pass_'] for r in checks) else 1


if __name__=='__main__':
    raise SystemExit(run())
