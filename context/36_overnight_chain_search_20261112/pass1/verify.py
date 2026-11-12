#!/usr/bin/env python3
"""Independent CSV/UTC/action/source tests + two real deterministic regenerations.
All outputs restricted to pass1; never runs any legacy builder or verifier.
"""
import sys
sys.dont_write_bytecode=True
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STUDY=HERE.parent
UTC=timezone.utc
START=datetime(2027,2,1,tzinfo=UTC)
END=datetime(2027,3,1,tzinfo=UTC)
CHECKS=[]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(name):
    with (HERE/name).open(newline='') as f:return list(csv.DictReader(f))
def js(name):return json.loads((HERE/name).read_text())
def dt(s):
    t=datetime.fromisoformat(s);assert t.tzinfo is not None
    return t.astimezone(UTC)
def check(name,condition,detail=None):
    assert condition,(name,detail)
    CHECKS.append(dict(check=name,status='PASS',detail=detail))
def near(a,b):return abs(float(a)-float(b))<.003

def protected():
    expected=json.loads((STUDY/'protected_files.json').read_text())
    bad=[p for p,h in expected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    check('protected1418_unchanged',len(expected)==1418 and not bad,bad)

def output_hashes():
    return {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
      if p.is_file() and p.name not in ('validation.json','output_hashes.json') and p.suffix!='.log'
      and '__pycache__' not in p.parts}

def replay():
    receipts=[]
    for n in (1,2):
        with (HERE/('verify_run%d.log'%n)).open('w') as out:
            p=subprocess.run([sys.executable,'-B',str(HERE/'generate.py')],cwd=HERE,stdout=out,stderr=subprocess.STDOUT)
        check('generation_run%d_exit0'%n,p.returncode==0)
        receipts.append(output_hashes())
    check('two_real_runs_byte_reproducible',receipts[0]==receipts[1],
      [p for p in set(receipts[0])|set(receipts[1]) if receipts[0].get(p)!=receipts[1].get(p)])
    return receipts[-1]

def validate():
    import importlib.util
    spec=importlib.util.spec_from_file_location('p36_verify_generator',HERE/'generate.py')
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    # No initialize here: fixtures must not recapture sources or run a legacy function.
    configs={r['config_id']:r for r in read('schedule_configs.csv')}
    paths={r['path_id']:r for r in read('path_registry.csv')}
    economics={(r['economic_id'],r['scenario']):r for r in read('economics_screen.csv')}
    actions={r['action_id']:r['action'] for r in read('action_ids.csv')}
    results={r['result_id']:r for r in read('disposition_ids.csv')}
    space=js('search_space.json');defs=js('baseline_definitions.json')['baselines']
    short=read('shortlist.csv');shortids={r['candidate_id'] for r in short}
    seen=set();counts=Counter();shortledger={};dims=Counter()
    with (HERE/'candidate_chains.csv').open(newline='') as f:
        for r in csv.DictReader(f):
            assert r['id'] not in seen;seen.add(r['id'])
            assert r['config'] in configs and r['setup'] in defs and r['action'] in actions and r['result'] in results
            assert (r['score'],'base') in economics and (r['score'],'cautious') in economics
            cfg=configs[r['config']];assert r['score']==cfg['path_id']+'F'+cfg['frequency_per_week']
            disposition=results[r['result']]['disposition']
            counts[(r['setup'],actions[r['action']],disposition)]+=1
            dims[r['config'],r['setup']]+=1
            if r['id'] in shortids:shortledger[r['id']]=r
    check('all_attempts_unique_referentially_complete',len(seen)==space['candidate_action_attempts'],len(seen))
    check('every_config_setup_has_all15_actions',set(dims.values())=={15})
    check('thin_ledger_below30MB',(HERE/'candidate_chains.csv').stat().st_size<30_000_000,(HERE/'candidate_chains.csv').stat().st_size)
    check('coverage_reconciles_attempts',sum(int(r['count']) for r in read('coverage.csv') if r['dimension']=='action')==len(seen))
    check('rejection_ledger_reconciles_attempts',sum(int(r['count']) for r in read('rejection_counts.csv'))==len(seen))
    check('airport_universe16',len(space['airports'])==16 and set(space['gated_queue'])=={'VVO','KHV'})
    check('all_requested_frequency_windows',space['frequencies']==[1,2,3,5,7] and space['start_hours_local']==[6,10,14,20])
    for r in configs.values():
        iso=list(map(int,r['iso_weekdays'].split(';')));zero=list(map(int,r['p31_weekdays_0_to_6'].split(';')))
        assert len(iso)==len(set(iso))==int(r['frequency_per_week'])
        assert [n-1 for n in iso]==zero and min(iso)>=1 and max(iso)<=7
    check('ISO_1to7_vs_P31_0to6_all_configs',True,len(configs))
    searched=[p for p in paths.values() if p['disposition']=='PARAMETER_SEARCH']
    selectedkeys={(r['path'],r['overnight_after']) for r in searched}
    for p in searched:
        nodes=p['path'].split('-');assert nodes[0]==nodes[-1]
        assert len(nodes)-1==int(p['legs']) and all(a!=b for a,b in zip(nodes,nodes[1:]))
        if p['family'].startswith('CYCLE'):
            assert len(set(nodes[:-1]))==len(nodes)-1
        if p['family'] in ('TRIANGLE','CYCLE4','CYCLE5','CYCLE6'):
            assert ('-'.join(reversed(nodes)),'0') in selectedkeys
    check('true_closed_cycles_no_selflegs_both_orientations',True,len(searched))
    check('graph_slots_types_unknown_not_silent_PASS',all(e['actual_slot']=='UNKNOWN' and e['type']=='RRJ-95B_CONDITIONAL' for e in read('graph_edges.csv')))
    for (eid,s),r in economics.items():assert int(r['departures_per_leg_month'])==4*int(r['frequency_per_week'])
    check('full28days_weekly_frequency_fixture_1is4_7is28',all(int(r['departures_per_leg_month']) in (4,8,12,20,28) for r in economics.values()))
    check('all46_old_P34_positive_rows_retained',len(read('inputs/p34_positive_service_preserved.csv'))==46)
    check('old_positives_not_relabelled_UNKNOWN',all(r['status']=='PUBLISHED_PATTERN_ONLY' for r in read('inputs/p34_positive_service_preserved.csv')))
    check('shortlist20to40_categories',20<=len(short)<=40 and {'RT','TRIANGLE','CYCLE4','CYCLE5','CYCLE6','CONCAT_RT'}<={r['family'] for r in short})
    check('shortlist_real_swaps_moves_multiremoval',any(r['action']=='SWAP' for r in short) and any(r['action'].startswith('MOVE') for r in short) and any(';' in r['removed_jobs'] for r in short))
    check('shortlist_SVX_ZIA_DME',{'SVX','ZIA','DME'}<={r['path'].split('-')[0] for r in short})
    check('full_delta_D_retime_F_cash_remain_UNKNOWN',all(all(r[k]=='UNKNOWN' for k in ('donor_D','unobserved_loss','move_or_swap_sales_loss','station_F','full_delta','cash')) for r in short))
    schedules=read('shortlist_full_schedules.csv');by=defaultdict(list)
    for r in schedules:by[r['candidate_id'],r['state']].append(r)
    actionmap=defaultdict(list)
    for r in read('action_map.csv'):actionmap[r['candidate_id']].append(r)
    for r in short:
        cid=r['candidate_id'];assert cid in shortledger
        checkdisp=results[shortledger[cid]['result']]['disposition']
        assert checkdisp in ('CONDITIONAL_SCREEN','RESOURCE_8BH_QUEUE')
        setup=defs[r['setup']];positions=setup['positions'];daily=Counter()
        for state in ('KEEP','WITHOUT_NEW','REPLACE'):
            fs=by[cid,state];tails=defaultdict(list);keys=set()
            for f in fs:
                assert f['tail']!='R1' and f['tail'] in positions
                dep,arr=dt(f['departure_utc']),dt(f['arrival_utc'])
                assert START<=dep<arr<=END
                assert (arr-dep).total_seconds()==float(f['block_minutes'])*60
                assert dt(f['departure_local'])==dep and dt(f['arrival_local'])==arr
                assert f['origin']!=f['destination']
                assert f['flight_id'] not in keys;keys.add(f['flight_id'])
                assert f['city_od']==('MOW' if f['origin'] in ('DME','ZIA') else f['origin'])+'>'+('MOW' if f['destination'] in ('DME','ZIA') else f['destination'])
                assert all(f[k]=='UNKNOWN' for k in ('actual_registration','slot','crew_FDP_rest','MRO','type_release'))
                assert int(f['saleable_seats'])==(0 if f['kind']=='PAID_FERRY' else 100)
                tails[f['tail']].append(f)
                if state=='REPLACE':
                    cursor=dep
                    while cursor<arr:
                        nextday=cursor.replace(hour=0,minute=0,second=0)+timedelta(days=1)
                        boundary=min(arr,nextday)
                        daily[f['tail'],cursor.date()]+=(boundary-cursor).total_seconds()/3600
                        cursor=boundary
            for tail,seq in tails.items():
                seq.sort(key=lambda f:f['departure_utc']);pos=positions[tail];ready=None
                for f in seq:
                    assert f['origin']==pos,(cid,state,tail,'position',f)
                    if ready:assert dt(f['departure_utc'])>=ready,(cid,state,tail,'overlap',f)
                    ready=dt(f['arrival_utc'])+timedelta(minutes=60);pos=f['destination']
                assert pos==positions[tail]
        assert abs(max(daily.values())-float(r['max_daily_BH']))<.0001
        kept={f['flight_id']:f for f in by[cid,'KEEP']}
        changed={f['flight_id']:f for f in by[cid,'WITHOUT_NEW']}
        replaced={f['flight_id']:f for f in by[cid,'REPLACE']}
        assert all({x:y for x,y in replaced[k].items() if x!='state'}==
                   {x:y for x,y in v.items() if x!='state'} for k,v in changed.items())
        added=[f for k,f in replaced.items() if k not in changed]
        assert all(f['old_or_new_job_id'].startswith('NEW-') for f in added)
        p=r['path'].split('-')
        assert len(added)==4*int(r['frequency_per_week'])*(len(p)-1),(cid,'missing legs')
        jgroups=defaultdict(list)
        for f in added:jgroups[f['old_or_new_job_id'],f['flight_id'].split('/W')[-1]].append(f)
        for seq in jgroups.values():
            seq.sort(key=lambda f:f['departure_utc'])
            assert [f['origin'] for f in seq]+[seq[-1]['destination']]==p
        assert {a['old_job_id'] for a in actionmap[cid]}==set(setup['old_job_ids'])
        for a in actionmap[cid]:
            old=[f for f in kept.values() if f['old_or_new_job_id']==a['old_job_id']]
            new=[f for f in changed.values() if f['old_or_new_job_id']==a['old_job_id']]
            assert len(old)==8
            if a['action']=='remove':assert not new
            else:
                assert len(new)==8
                for f in old:
                    n=changed[f['flight_id']]
                    assert (dt(n['departure_utc'])-dt(f['departure_utc'])).total_seconds()/60==int(a['delta_minutes'])
                    assert n['tail']==a['to_tail']
            assert a['actual_loss']=='UNKNOWN' and a['old_revenue']=='UNKNOWN'
    check('all_full_schedules_independent_UTC_position_turn_entry_localtypes',True,len(schedules))
    check('no_truncated_new_legs_4repeatweeks_closed_paths',True)
    check('stable_old_ids_all_keep_move_remove_swap_maps_exact',True)
    check('without_new_exact_same_changed_old_as_replace',True)
    # Independent finite monthly pool conservation and 3-state decomposition.
    pools=read('three_state_pool_checks.csv');poolkeys=set()
    for r in pools:
        k=(r['candidate_id'],r['scenario'],r['state'],r['city_od']);assert k not in poolkeys;poolkeys.add(k)
        assert float(r['allocated'])<=float(r['potential'])+.001
    check('one_shared_monthly_directed_city_pool_no_multiplication_per_job',True,len(pools))
    states=read('three_state_screen.csv');groups=defaultdict(dict)
    for r in states:groups[r['candidate_id'],r['scenario']][r['state']]=r
    for k,v in groups.items():
        assert set(v)=={'KEEP','WITHOUT_NEW','REPLACE'}
        for r in v.values():
            assert near(float(r['scoped_prior_net_revenue'])-float(r['scoped_avoidable_cost_transfer']),r['scoped_known_subtotal'])
            assert near(float(r['scoped_known_subtotal'])-float(v['KEEP']['scoped_known_subtotal']),r['delta_vs_keep_screen'])
            assert near(float(v['REPLACE']['scoped_known_subtotal'])-float(v['WITHOUT_NEW']['scoped_known_subtotal']),r['replace_vs_without_new_screen'])
            assert all(r[x]=='UNKNOWN' for x in ('actual_full_delta','actual_moscow_international_D','actual_retiming_loss','cancellation_cost','cash'))
    check('three_states_same_scenario_scope_decomposition',len(groups)==2*len(short))
    # Fixture: midnight splits, hard overlap vs8BH, reserve use, crossbase cannot silently swap.
    def job(id_,start,end,tail='T1',origin='SVX'):
        return dict(id=id_,tail=tail,origin=origin,destination=origin,start=start,end=end,
          flights=[dict(dep=start,arr=end,block=end-start)])
    e,bh=g.physics([job('MIDNIGHT',1430,1470)],{'T1':'SVX'})
    check('fixture_midnight40min_splits10_and30',not e and abs(bh-.5)<1e-9)
    e,bh=g.physics([job('LONG',600,1140)],{'T1':'SVX'})
    check('fixture_9BH_is_diagnostic_not_hard_FDP',not e and bh==9)
    e,bh=g.physics([job('A',600,660),job('B',700,760)],{'T1':'SVX'})
    check('fixture_turn60_hard_reject', 'OVERLAP_OR_TURN' in e)
    e,bh=g.physics([job('A',600,660,origin='ZIA')],{'T1':'SVX'})
    check('fixture_no_magic_crossbase_position', 'POSITION_REQUIRES_PAID_FERRY' in e)
    e,bh=g.physics([job('A',600,660,tail='R1')],{'R1':'SVX'})
    check('fixture_reserve_is_not_working_tail','RESERVE_USED' in e)
    n=g.allocate_market(1000,{'DME':dict(weight=1,capacity=100),'ZIA':dict(weight=1,capacity=100)})
    check('fixture_MOW_shared_pool_capacity',sum(n.values())==200)
    check('structural_cautious_full100_negative_all_searched',all(float(r['full100_cap'])<0 for r in economics.values() if r['scenario']=='cautious'))
    check('structural_all_graph_edges_negative_proves_all_chain_sums',js('structural_proof.json')['every_graph_edge_negative'] and all(float(r['cautious_full100_cap'])<0 for r in read('edge_structural_bounds.csv')))
    resource=read('resource_cases.csv')
    check('no_SJ_Feb2027_PD8_not_RRJ',all(r['new_SJ_resource_only']=='0' for r in resource if r['month']=='2027-02') and all(r['PD8_equivalence']=='NOT_ASSUMED' for r in resource))
    manifest=js('source_manifest.json')
    for key,r in manifest['sources'].items():
        if r['kind']=='git_blob':p=HERE/r['snapshot']
        elif r['kind']=='existing_minimal_snapshot':p=STUDY/r['snapshot']
        else:p=ROOT/key
        assert sha(p)==r['sha256'],key
    check('all_source_snapshot_and_dependency_hashes',True,len(manifest['sources']))
    check('no_P36_inprogress_research_ingested',not manifest['P36_research_read'] and manifest['no_external_search'])
    check('no_pass1_pycache',not list(HERE.rglob('__pycache__')))

def main():
    protected()
    hashes=replay()
    validate()
    protected()
    (HERE/'output_hashes.json').write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n')
    result=dict(status='PASS',checks_passed=len(CHECKS),checks=CHECKS,real_regeneration_runs=2,
      byte_reproducible=True,protected_files=1418,old_builds_run=0,external_searches=0,subagents=0,
      git_mutations=0,market_research_numeric_updates=0,dispatch_ready=False,full_financial_acceptance=False)
    (HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False))

if __name__=='__main__':main()
