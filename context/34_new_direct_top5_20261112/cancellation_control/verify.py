#!/usr/bin/env python3
"""Run two actual calculations; verify economics, physics, sources and preservation."""
import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,subprocess,os
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STUDY=HERE.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):
    with (HERE/n).open(newline='') as f:return list(csv.DictReader(f))
def num(r,k):return float(r[k])
def close(a,b):assert abs(a-b)<max(2e-5,abs(b)*1e-9),(a,b)
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
def preserved():
    paths=[]
    for folder in ['31_direct_growth_research_20261112','32_delay_cargo_research_20261112','33_svx_aer_launch_case_20261112','34_new_direct_top5_20261112']:
        paths += [p for p in (ROOT/'context'/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and HERE not in p.parents]
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def hashes():return {p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='validation.json'}
def main():
    before=preserved();checks=[];runs=[]
    for _ in range(2):
        r=subprocess.run([sys.executable,'-B',str(HERE/'calculate.py')],cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
        assert r.returncode==0,r.stdout+'\n'+r.stderr
        runs.append(dict(returncode=r.returncode,stdout=r.stdout.strip(),output_hashes=hashes()))
    assert runs[0]['output_hashes']==runs[1]['output_hashes']
    checks.append('two_real_joint_calculation_runs_byte_identical_including_manifest')
    assert all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in before.items())
    pins=json.loads((ROOT/'context/33_svx_aer_launch_case_20261112/protected_files.json').read_text())
    assert len(pins)==1190 and all(sha(ROOT/p)==h for p,h in pins.items())
    checks.append('1190_and_all_preexisting_P31_P32_P33_P34_author_review_coordinator_bytes_preserved_no_HEAD_check')
    import importlib.util
    spec=importlib.util.spec_from_file_location('cancel_verify',HERE/'calculate.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
    assert C.P.frequency_fixture()['full_Feb_four_departures_frequency']==1
    ps=read('comparison.csv');ls=read('ledger.csv');fs=read('flights.csv');ts=read('pairwise_thresholds.csv')
    assert len(ps)==24 and len(ts)==32
    unknowns=['actual_D','external_donor','F_setup_lease_reserve','cash','full_PnL','existing_slots','actual_fixed_parking','actual_cancellation_contracts','actual_gates','penalty_storage_actual']
    for r in ps:
        assert all(r[k]=='NULL' for k in unknowns)
        assert all(num(r,k)==0 for k in ['fuel_support','route_grant','cargo_main'])
        close(num(r,'known_P_minus_KEEP_month')/4,num(r,'known_P_minus_KEEP_week'))
        close(num(r,'known_P_minus_KEEP_month'),num(r,'net_revenue_P_month')-num(r,'avoidable_cost_P_month')-num(r,'net_revenue_KEEP_month')+num(r,'avoidable_cost_KEEP_month'))
        assert num(r,'net_revenue_KEEP_month')>0 and num(r,'avoidable_cost_KEEP_month')>0 and num(r,'model_RW_journeys_KEEP')>0
        if r['programme']=='KEEP':close(num(r,'known_P_minus_KEEP_month'),0)
        ledger=[x for x in ls if all(x[k]==r[k] for k in ['programme','scenario','adjacent_case'])]
        close(sum((1 if x['side']=='P' else -1)*num(x,'contribution_month') for x in ledger),num(r,'known_P_minus_KEEP_month'))
        for side in ['P','KEEP']:
            side_ls=[x for x in ledger if x['side']==side]
            close(sum(num(x,'net_revenue_month') for x in side_ls),num(r,'net_revenue_'+side+'_month'))
            close(sum(num(x,'avoidable_cost_month') for x in side_ls),num(r,'avoidable_cost_'+side+'_month'))
            for x in side_ls:
                assert x['donor_deducted_again']=='False'
                close(num(x,'fuel_cost_month')+num(x,'other_cost_month'),num(x,'avoidable_cost_month'))
                close(num(x,'contribution_month'),num(x,'net_revenue_month')-num(x,'avoidable_cost_month'))
                for key in ['net_revenue','avoidable_cost','contribution','journeys','flights','block_hours']:close(num(x,key+'_month')/4,num(x,key+'_per4'))
        if r['programme'].startswith('CANCEL'):
            assert num(r,'new_pair_journeys_month')==num(r,'new_pair_revenue_month')==num(r,'adjacent_revenue_month')==0
            p=[x for x in ledger if x['side']=='P']
            assert num(next(x for x in p if x['group']=='DONOR_TUE_OMS'),'flights_month')==0
            assert num(next(x for x in p if x['group']=='DONOR_FRI_KUF'),'flights_month')==(8 if r['programme']=='CANCEL_TUE_KEEP_FRI' else 0)
            retained=next(x for x in ledger if x['side']=='P' and x['group']=='RETAINED_OLD_RW')
            oldret=next(x for x in ledger if x['side']=='KEEP' and x['group']=='RETAINED_OLD_RW')
            assert num(retained,'journeys_month')>num(oldret,'journeys_month')
            close(num(retained,'avoidable_cost_month'),num(oldret,'avoidable_cost_month'))
    checks.append('P_KEEP_nonzero_sales_delta0_joint_revenue_cost_ledger_donor_once_retained_reallocation_no_NEW_NULL_actuals')
    grouped=defaultdict(list)
    for f in fs:grouped[f['programme'],f['side']].append(f)
    ref={(x['flight_id'],x['origin'],x['destination'],x['departure_utc'],x['arrival_utc']) for x in grouped['KEEP','KEEP'] if x['group']=='RETAINED_OLD_RW'}
    assert len(ref)==32
    expected={'CANCEL_TUE_KEEP_FRI':40,'CANCEL_BOTH':32,'AER1':48,'AER2':48,'TRI:SVX-AER-MRV':56,'KEEP':48}
    for (name,side),rows in grouped.items():
        assert len(rows)==(48 if side=='KEEP' else expected[name])
        assert ref=={(x['flight_id'],x['origin'],x['destination'],x['departure_utc'],x['arrival_utc']) for x in rows if x['group']=='RETAINED_OLD_RW'}
        assert len(rows)==len({(x['origin'],x['destination'],x['departure_utc']) for x in rows})
        ordered=sorted(rows,key=lambda x:x['departure_utc']);assert ordered[0]['origin']==ordered[-1]['destination']=='SVX'
        for f in ordered:
            assert f['tail']=='E1' and f['initial_location']=='SVX' and f['origin']!=f['destination']
            close((dt(f['arrival_utc'])-dt(f['departure_utc'])).total_seconds()/60,num(f,'block_minutes'));assert num(f,'block_minutes')>0
            for port,lc,uc in [('origin','departure_local','departure_utc'),('destination','arrival_local','arrival_utc')]:
                loc=datetime.fromisoformat(f[lc]);expectedloc=dt(f[uc]).astimezone(ZoneInfo(C.P.ZONES[f[port]]))
                assert loc.replace(tzinfo=None)==expectedloc.replace(tzinfo=None) and loc.utcoffset()==expectedloc.utcoffset()
        for a,b in zip(ordered,ordered[1:]):
            assert a['destination']==b['origin']
            assert (dt(b['departure_utc'])-dt(a['arrival_utc'])).total_seconds()/60>=60-1e-8
        if side=='P':
            for r in [x for x in ps if x['programme']==name]:
                close(num(r,'block_hours_month'),sum(num(f,'block_minutes') for f in rows)/60)
                assert num(r,'cycles_month')==len(rows)
        if side=='P' and name.startswith('CANCEL'):
            assert not any(f['group'] in ['NEW_PAIR','ADJACENT'] for f in rows)
            assert all(f['destination']=='SVX' for f in ordered if f['origin']!='SVX')
    # FOLLOW dates independently reconstructed from the canonical P32 source.
    for shift in [0,3]:
        for week in range(4):
            for s in C.P.FOLLOW:
                t=C.P.dt(s['dep_utc'])+timedelta(days=shift+week*7)
                assert any(x['origin']==s['origin'] and x['destination']==s['destination'] and dt(x['departure_utc'])==t and num(x,'block_minutes')==float(s['block_min']) for x in grouped['KEEP','KEEP'])
    checks.append('exact_P_KEEP_inventory_times_UTC_local_position_turns_cycles_BH_32_P32_FOLLOW_initial_final_SVX_no_R1_SJ_or_zero_leg')
    for t in ts:
        lookup={r['programme']:r for r in ps if all(r[k]==t[k] for k in ['scenario','adjacent_case'])};a,b=lookup[t['A']],lookup[t['B']]
        d=num(a,'known_P_minus_KEEP_month')-num(b,'known_P_minus_KEEP_month')
        close(d,num(t,'scoped_A_minus_B_month'));close(d,num(t,'omitted_cost_A_minus_B_tie_threshold_month'))
        close(d/4,num(t,'scoped_A_minus_B_per4'))
        close(d,sum(num(t,g+'_contribution_difference_month') for g in ['donor','retained','new_flights']))
        if t['A'] in ['AER1','AER2'] and t['B'].startswith('CANCEL'):
            close(num(t,'donor_contribution_difference_month'),0);close(num(t,'retained_contribution_difference_month'),0)
            close(d,num(t,'new_flights_contribution_difference_month'))
    bridge=C.P.read(STUDY/'coordinator/AER_result_bridge.csv')
    for b in bridge:
        t=next(t for t in ts if t['A']==b['programme'] and t['B'].startswith('CANCEL') and t['scenario']==b['scenario'] and t['adjacent_case']=='P05_ADJACENT_PRIOR')
        close(num(t,'scoped_A_minus_B_month'),float(b['new_flight_contribution_RUB']))
    for name,target in [('CANCEL_TUE_KEEP_FRI',6651599.0539063385),('CANCEL_BOTH',13131476.9213618)]:
        r=next(r for r in ps if r['programme']==name and r['scenario']=='cautious' and r['adjacent_case']=='P05_ADJACENT_PRIOR');close(num(r,'known_P_minus_KEEP_month'),target)
    checks.append('pairwise_replacement_beyond_cancellation_exact_AER_bridge_invariant_threshold_signed_no_doublecount')
    for sc in ['base','cautious']:
        rows=[r for r in ps if r['scenario']==sc and r['adjacent_case']=='P05_ADJACENT_PRIOR']
        assert [r['programme'] for r in sorted(rows,key=lambda r:int(r['conditional_rank_among_6']))]==[r['programme'] for r in sorted(rows,key=lambda r:-num(r,'known_P_minus_KEEP_month'))]
    m=json.loads((HERE/'manifest.json').read_text())
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in m['source_inputs'])
    assert all(sha(HERE/r['path'])==r['sha256'] for r in m['outputs'])
    assert all(x['OD_conservation'] and x['seat_conservation'] and x['same_P_KEEP_potential'] and x['frequency_full_month'] for x in m['allocation_checks'])
    assert all(sha(ROOT/p)==h for p,h in before.items())
    assert not list(HERE.rglob('__pycache__'))
    checks.append('same_P34_contract_source_hashes_OD_seats_monthly_frequency_full_prior_and_stress_rank')
    validation=dict(status='PASS_CONDITIONAL_CANCELLATION_COUNTERFACTUAL',actual_calculation_runs=2,joint_evaluations_per_run=24,two_runs_byte_identical=True,checks=checks,protected1190_count=1190,all_preexisting_files_checked=len(before),preserved_snapshot_sha256=digest(before),preexisting_content_preserved=True,no_HEAD_assertion=True,runs=runs,remaining='actual PnL/fixed parking/Fcancellation/contracts/D/gates/crew/MRO/slots/payload NULL; model is not an operational closure instruction')
    (HERE/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status=validation['status'],checks=len(checks),runs=2,protected1190='PASS',preexisting_files=len(before))))
if __name__=='__main__':main()
