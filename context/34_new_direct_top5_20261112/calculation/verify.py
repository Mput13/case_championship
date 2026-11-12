#!/usr/bin/env python3
"""Two real runs + content protection and economically meaningful invariants."""
import sys
sys.dont_write_bytecode=True
import csv
import hashlib
import importlib.util
import json
import math
import os
import subprocess
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
UTC=timezone.utc

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):
    with (HERE/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def js(name):return json.loads((HERE/name).read_text())
def num(r,k):return float(r[k])
def dt(s):
    d=datetime.fromisoformat(s.replace('Z','+00:00'));assert d.tzinfo is not None
    return d.astimezone(UTC)
def mins(a,b):return (dt(a)-dt(b)).total_seconds()/60
def close(a,b,atol=1e-5):assert abs(a-b)<=max(atol,abs(b)*1e-8),(a,b)
def baseline():
    # Content checks on old packages include files newer than Protected1190.
    paths=[]
    for folder in ('31_direct_growth_research_20261112','32_delay_cargo_research_20261112','33_svx_aer_launch_case_20261112'):
        paths += [p for p in (ROOT/'context'/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}
def output_hashes():
    return {p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name!='validation.json'}

def main():
    preserved=baseline()
    checknames=[]
    def passed(name):checknames.append(name)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    runs=[]
    for _ in range(2):
        r=subprocess.run([sys.executable,'-B',str(HERE/'calculate.py')],cwd=ROOT,env=env,text=True,capture_output=True)
        assert r.returncode==0,r.stdout+'\n'+r.stderr
        runs.append(dict(returncode=r.returncode,stdout=r.stdout.strip(),hashes=output_hashes()))
    assert runs[0]['hashes']==runs[1]['hashes'],'Nondeterministic outputs'
    passed('two_actual_runs_byte_identical_including_manifest')
    assert preserved==baseline(),'Old P31/P32/P33 files changed'
    pins=json.loads((ROOT/'context/33_svx_aer_launch_case_20261112/protected_files.json').read_text())
    assert len(pins)==1190 and all(sha(ROOT/p)==h for p,h in pins.items())
    passed('Protected1190_content_and_all_existing_old_package_files_preserved_no_HEAD_check')
    spec=importlib.util.spec_from_file_location('p34_verify_calc',HERE/'calculate.py')
    calc=importlib.util.module_from_spec(spec);spec.loader.exec_module(calc)
    fixture=calc.frequency_fixture()
    assert fixture['real_P31_7day_frequency']==.25 and fixture['full_Feb_four_departures_frequency']==1
    assert fixture['monthly_demand_over_7day']==4 and fixture['demand_prorate_count']==1
    passed('real_P31_week_frequency_bug_and_full_month_workaround_partial_boundary_rejected_demand_once')

    cs=read('candidate_comparison.csv');top=read('top5_conditional.csv');ps=read('programme_comparison.csv')
    fs=read('flights.csv');be=read('break_even.csv');le=read('programme_ledger.csv');de=read('delay_events.csv')
    assert len(cs)==12 and len(top)==5 and len(ps)==16*4
    assert len({r['pair'] for r in cs})==12
    assert all(r['qualified_new_route']=='False' and r['rw_nonstop']=='UNKNOWN' for r in cs)
    assert Counter(r['queue_group'] for r in cs)=={'TYPE_A_UNCONFIRMED':4,'TYPE_B_RW_UNCHECKED':6,'LOW_EVIDENCE_QUEUE':2}
    assert all(r['classification']=='UNKNOWN' for r in cs if r['queue_group']=='TYPE_A_UNCONFIRMED')
    assert all(r['classification']=='COMPETITOR_NONSTOP_RW_NOT_CONFIRMED' for r in cs if r['queue_group']=='TYPE_B_RW_UNCHECKED')
    assert {r['pair'] for r in cs if r['queue_group']=='LOW_EVIDENCE_QUEUE'}=={'PEE-TOF','OMS-REN'}
    expected=sorted([r for r in cs if r['base_noadj_delta_month']!='NULL' and r['queue_group']!='LOW_EVIDENCE_QUEUE'],key=lambda r:(-num(r,'base_noadj_delta_month'),r['pair']))[:5]
    assert [r['pair'] for r in top]==[r['pair'] for r in expected]
    assert next(r for r in cs if r['pair']=='SVX-KJA')['own_history']=='UNRESOLVED_RELAUNCH_HISTORY_NOT_EXCLUDED'
    passed('all12_preserved_honest_newness_qualified0_TOP5_conditional_SVXKJA_not_excluded_by_history')

    for r in ps:
        for k in ('actual_D','external_donor','F_setup_lease_reserve','cash','full_PnL','observed_OD','observed_20kg_netfare','existing_slots'):
            assert r[k]=='NULL',(r['programme'],k)
        assert all(num(r,k)==0 for k in ('fuel_support','route_grant','cargo_main'))
        if r['known_P_minus_KEEP_month']!='NULL':
            close(num(r,'known_P_minus_KEEP_month')/4,num(r,'known_P_minus_KEEP_week'))
            delta=num(r,'net_revenue_P_month')-num(r,'avoidable_cost_P_month')-num(r,'net_revenue_KEEP_month')+num(r,'avoidable_cost_KEEP_month')
            close(delta,num(r,'known_P_minus_KEEP_month'))
            if r['programme']=='KEEP':
                close(delta,0);assert num(r,'net_revenue_KEEP_month')>0 and num(r,'avoidable_cost_KEEP_month')>0
            assert r['missing_retained_lossbudget']=='0'
        else:
            assert r['programme'] in ('SVX-VVO','SVX-KHV')
            assert r['missing_retained_lossbudget']=='NULL' and r['geometry_status']=='INVALID_D0_OR_WINDOW_OPS_QUEUE'
    passed('monthly_week_div4_joint_delta_KEEP_nonzero_business_unknowns_NULL_support_cargo0_hard_fail_NULL')

    byprog=defaultdict(list)
    for f in fs:
        byprog[f['programme']].append(f)
        assert f['tail']=='E1' and f['date_status']=='SCENARIO'
        close(mins(f['arrival_utc'],f['departure_utc']),num(f,'block_minutes'))
        for airport,localkey,utckey in [(f['origin'],'departure_local','departure_utc'),(f['destination'],'arrival_local','arrival_utc')]:
            loc=datetime.fromisoformat(f[localkey]);zone=ZoneInfo(calc.ZONES[airport])
            expected=dt(f[utckey]).astimezone(zone)
            assert loc==expected and loc.utcoffset()==expected.utcoffset()
            assert loc.replace(tzinfo=None)==expected.replace(tzinfo=None)
        assert f['origin']!=f['destination'] and num(f,'block_minutes')>0
        if f['kind']=='positioning':assert num(f,'saleable_seats')==0
        assert f['slot']=='NULL' and f['crew_FDP_rest']=='NULL' and f['AFM_payload']=='NULL'
    assert len(byprog)==16
    reference={(f['flight_id'],f['origin'],f['destination'],f['departure_utc'],f['arrival_utc']) for f in byprog['KEEP'] if f['group']=='RETAINED_OLD_RW'}
    assert len(reference)==32
    for name,rows in byprog.items():
        assert len(rows)==len({(f['origin'],f['destination'],f['departure_utc']) for f in rows})
        assert reference=={(f['flight_id'],f['origin'],f['destination'],f['departure_utc'],f['arrival_utc']) for f in rows if f['group']=='RETAINED_OLD_RW'}
        triangle=name==calc.AER_TRIANGLE or (name not in ('KEEP','AER1','AER2') and not name.startswith('SVX-'))
        assert len(rows)==(56 if triangle else 48)
        news=[f for f in rows if f['group']=='NEW_PAIR']
        if name!='KEEP':
            assert len(news)==(16 if name=='AER2' else 8)
            dirs=Counter((f['origin'],f['destination']) for f in news)
            assert len(dirs)==2 and set(dirs.values())==({8} if name=='AER2' else {4})
        rotations=defaultdict(list)
        for f in rows:rotations['/'.join(f['flight_id'].split('/')[:-1])].append(f)
        for rid,rr in rotations.items():
            rr.sort(key=lambda f:f['departure_utc'])
            assert rr[0]['origin']==rr[-1]['destination']=='SVX'
            for a,b in zip(rr,rr[1:]):
                assert a['destination']==b['origin'];close(mins(b['departure_utc'],a['arrival_utc']),60)
            if triangle and rid.startswith('NEW-'):
                assert len(rr)==3
                day=rid.split('/')[-1];assert datetime.fromisoformat(day).isoweekday() in (2,5)
        if name not in ('SVX-VVO','SVX-KHV'):
            ordered=sorted(rows,key=lambda f:f['departure_utc'])
            for a,b in zip(ordered,ordered[1:]):
                assert a['destination']==b['origin'];assert mins(b['departure_utc'],a['arrival_utc'])>=60-1e-8
        r=next(r for r in ps if r['programme']==name and r['scenario']=='base' and r['adjacent_case']=='P05_ADJACENT_PRIOR')
        close(num(r,'block_hours_month'),sum(num(f,'block_minutes') for f in rows)/60)
    passed('independent_UTC_local_zoneinfo_blocks_turns_closed_cycles_both_directions_all_FOLLOW_same_reserve_unscheduled')
    # Reconstruct the first four FOLLOW from source, and date translations.
    source=[r for r in calc.FOLLOW]
    for weekday,shift in [(2,0),(5,3)]:
        for week in range(4):
            for s in source:
                dep=dt(s['dep_utc'])+timedelta(days=shift+7*week)
                assert any(f['group']=='RETAINED_OLD_RW' and f['origin']==s['origin'] and f['destination']==s['destination'] and dt(f['departure_utc'])==dep and num(f,'block_minutes')==float(s['block_min']) for f in byprog['KEEP'])
    passed('FOLLOW_only_P32_OMS_B30_same_variant_dates_KUF_Samara_not_P33_follow')
    # P33 error fixture read independently from the preserved original CSV.
    original=calc.read(calc.C33/'operations/KEEP_rotation.csv')
    # Its schema is different from the new canonical output; inspect explicit
    # UTC columns by their actual names, never infer from labels.
    old_aer=[r for r in original if 'AER' in r.values()]
    assert old_aer
    elapsed=[]
    for r in old_aer:
        a=r.get('departure_utc',r.get('dep_utc'));b=r.get('arrival_utc',r.get('arr_utc'))
        if a and b:elapsed.append(mins(b,a))
    assert 330 in elapsed and 150 in elapsed,elapsed
    aer=[r for r in byprog['AER1'] if r['group']=='NEW_PAIR']
    first=sorted(aer,key=lambda r:r['departure_utc'])[:2]
    assert first[0]['departure_local']=='2027-02-02T14:00:00+05:00'
    assert first[0]['arrival_local']=='2027-02-02T15:30:00+03:00'
    assert first[1]['departure_local']=='2027-02-02T16:30:00+03:00'
    assert first[1]['arrival_local']=='2027-02-02T22:00:00+05:00'
    assert all(num(f,'block_minutes')==210 for f in aer)
    passed('real_P33_330150_error_canonical_AER210210_turn60_independent_UTC')

    for r in le:assert r['donor_deducted_again']=='False'
    for p in ps:
        if p['known_P_minus_KEEP_month']=='NULL':continue
        ledger=[r for r in le if all(r[k]==p[k] for k in ('programme','scenario','adjacent_case'))]
        delta=sum((1 if r['side']=='P' else -1)*num(r,'contribution_month') for r in ledger)
        close(delta,num(p,'known_P_minus_KEEP_month'))
        assert any(r['side']=='KEEP' and r['group']=='DONOR' for r in ledger)
    checks=js('model_checks.json')
    assert all(all(c[k] for k in ('seat_conservation','OD_conservation','identical_P_KEEP_potential','donor_once')) for c in checks['allocation_checks'])
    close(checks['joint_fare_override']['gross_ratio'],.9);close(checks['joint_fare_override']['net_ratio'],.9)
    close(calc.RE.P05.net_fare(11000,.10,.08),9200)
    assert any(num(r,'saturated_flights')>0 for r in ps if r['scenario']=='base' and r['saturated_flights'])
    assert next(r for r in cs if r['pair']=='OMS-PEE')['annual_demand_basis']=='BASE_GRAVITY_EXTRAPOLATION'
    passed('joint_OD_pool_seat_conservation_BASE_saturation_gravity_label_VAT_distribution_once_real_joint_fare_override')
    passed('internal_donor_net_revenue_avoidable_cost_once_ledger_reconciles_not_triple_subtraction')

    for r in be:
        axis=r['axis']
        if axis=='AIRCRAFT_ONLY_ABSORB120':
            close(num(r,'extra_block_headroom_min'),num(r,'buffer_to_next_retained_min')-120)
            assert (r['absorb120']=='True')==(num(r,'buffer_to_next_retained_min')>=120)
            continue
        K=num(r,'fixed_other_net_cost_RUB');a=num(r,'model_net_a');b=num(r,'model_net_b')
        if axis=='SYMMETRIC_JOINT_Q_BOUNDARY':close(num(r,'q_a_required')*a+num(r,'q_b_required')*b,K)
        if axis=='Q_A_GIVEN_Q_B':close(num(r,'q_a_required')*a+num(r,'q_b_fixed')*b,K)
        if axis=='Q_B_GIVEN_Q_A':close(num(r,'q_a_fixed')*a+num(r,'q_b_required')*b,K)
        if axis=='NET_FARE_SCALE_FIXED_Q':close(num(r,'net_scale_required')*(num(r,'model_q_a')*a+num(r,'model_q_b')*b),K)
        if axis=='CLEAN_NEW_Q_SYMMETRIC_WITH_OUTSIDE_MIGRATION':
            ma=num(r,'migrated_a');mb=num(r,'migrated_b');newq=num(r,'q_a_required')
            close(newq*(a+b),K+ma*(num(r,'oldnet_scenario_a')-a)+mb*(num(r,'oldnet_scenario_b')-b))
            close(num(r,'available_new_seats_a')+ma,num(r,'capacity_a'))
            close(num(r,'available_new_seats_b')+mb,num(r,'capacity_b'))
            close(num(r,'outside_lost_revenue'),ma*a+mb*b)
            feasible=0<=newq<=min(num(r,'available_new_seats_a'),num(r,'available_new_seats_b'))
            assert (r['feasible_with_seats']=='True')==feasible
    assert {r['outside_migration_fraction'] for r in be if r['axis']=='CLEAN_NEW_Q_SYMMETRIC_WITH_OUTSIDE_MIGRATION'}=={'0','0.25','0.5'}
    passed('joint_direction_BE_given_other_axes_clean_new_migrants_occupy_seats_old_net_lost_no_backfill')

    groups=defaultdict(list)
    for r in de:
        groups[r['programme'],r['window'],r['target_id'],r['shock_minutes']].append(r)
        close(mins(r['actual_arr_utc'],r['actual_dep_utc']),mins(r['planned_arr_utc'],r['planned_dep_utc']))
        assert num(r,'ground_delay_block_cost')==0 and r['delay_probability']=='NULL' and r['RUB_per_minute']=='NULL'
        assert r['automatic_cancellation']=='NULL' and r['crew_remaining']=='NULL' and r['R1_extra_capacity']=='False'
        if r['D0_valid']=='True' and r['shock_minutes']=='0':
            close(num(r,'departure_delay_minutes'),0)
        if r['flight_id']==r['target_id']:
            assert num(r,'departure_delay_minutes')>=num(r,'shock_minutes')-1e-8
        airport=r['origin'];expected=dt(r['actual_dep_utc']).astimezone(ZoneInfo(calc.ZONES[airport]))
        assert datetime.fromisoformat(r['actual_dep_local'])==expected
    for key,rows in groups.items():
        assert sum(r['flight_id']==r['target_id'] for r in rows)==1
        if key[1]=='MAIN':assert all(r['D0_valid']=='True' for r in rows)
        # File row order is the intended physical chain; each delay propagates
        # across midnight under max(previousarrival+60,plan,hold).
        for a,b in zip(rows,rows[1:]):
            assert a['destination']==b['origin']
            assert mins(b['actual_dep_utc'],a['actual_arr_utc'])>=60-1e-8
    for name in checks['selected']+[calc.AER_TRIANGLE]:
        targets={key[2] for key in groups if key[0]==name}
        assert any('TUE' in t for t in targets) and any('FRI' in t for t in targets)
        for target in targets:assert {key[3] for key in groups if key[0]==name and key[2]==target}=={'0','30','60','120'}
    wins=read('AER_window_comparison.csv');assert len(wins)==12
    assert all(r['D0_valid']=='False' for r in wins if r['clock_SVX']=='21:00')
    assert all(r['D0_valid']=='True' for r in wins if r['clock_SVX'] in ('07:00','14:00'))
    assert all(r['actual_quoted_discount']=='NULL' and r['existing_slot']=='NULL' and r['clock_price_effect']=='NULL' for r in wins)
    passed('D0_matches_plan_positive_shock_explicit_targets_Tue_Fri_no_midnight_reset_groundhold_not_BH_AER3clocks')

    refs=read('author_triangle_reference.csv')
    legacy=[r for r in calc.read(calc.C31/'ops_inputs/reference_physical_legs.csv') if r['programme']=='dashboard_fixed_triangles']
    assert refs==legacy and len(refs)==96
    status=js('author_reference_status.json');assert len(status)==2
    assert [int(r['original_author_summary'][0]['aircraft']) for r in status]==[8,7]
    assert [r['proxy_min_working_tails'] for r in status]==[9,8]
    assert all(r['E1_profit_attribution'] is None and not r['resized'] for r in status)
    tri=js('AER_triangle_admission.json')
    assert tri['pattern_id']==calc.AER_TRIANGLE and tri['project_sectors_week']==6
    assert tri['Tue']==['SVX','AER','MRV','SVX'] and tri['Fri']==['SVX','MRV','AER','SVX']
    assert calc.AER_TRIANGLE in byprog and calc.AER_TRIANGLE not in {r['pair'] for r in cs}
    passed('author_full_triangle_reference_exact_original_resource_separate_no_E1_money_one_ready_AERtriangle_both_orientations')

    manifest=js('manifest.json')
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in manifest['inputs'])
    assert all(sha(HERE/r['path'])==r['sha256'] for r in manifest['outputs'])
    assert not any('__pycache__' in str(p) for p in HERE.rglob('*'))
    assert preserved==baseline()
    passed('manifest_inputs_outputs_hashes_all_preserved_no_pycache_outside_write_no_git_HEAD_assertion')
    validation=dict(status='PASS_CONDITIONAL_MODEL_REVIEW_EXPLANATION_CHANGES_ADDRESSED',
        tests_passed=len(checknames),checks=checknames,actual_calculation_runs=2,
        determinism=True,qualified_new_routes=0,protected1190_count=1190,
        old_package_file_count=len(preserved),old_package_content_preserved=True,
        no_HEAD_assertion=True,tracked_total_may_exceed1190=True,
        output_hashes=runs[1]['hashes'],runs=[dict(returncode=r['returncode'],stdout=r['stdout']) for r in runs],
        independent_review='CHANGES; R1/R2 explanatory fixes applied by coordinator; no claim of a second independent acceptance',
        remaining='own RW register/OD/yield/actual donor/variant/tail/slots/crew/MRO/payload/F/cash UNKNOWN')
    (HERE/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps(dict(status=validation['status'],tests=len(checknames),two_runs_identical=True,protected1190='PASS'),ensure_ascii=False))

if __name__=='__main__':main()
