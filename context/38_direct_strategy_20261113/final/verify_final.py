#!/usr/bin/env python3
"""Read-only checks of source preservation, final presentation, finance and delays."""
import sys
sys.dont_write_bytecode = True
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERE=Path(__file__).resolve().parent
P=HERE.parent
ROOT=P.parents[1]
E=P/'economics'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f);rows=list(r)
        assert all(None not in row and None not in row.values() for row in rows),p
        return rows
def near(a,b):assert abs(float(a)-float(b))<1e-4,(a,b)
def dt(s):return datetime.fromisoformat(s)

def verify():
    protected=json.loads((P/'protected_files.json').read_text())
    assert len(protected)==1621
    assert all((ROOT/name).is_file() and sha(ROOT/name)==h for name,h in protected.items())
    assembly=json.loads((HERE/'assembly_receipt.json').read_text())
    assert all(sha(E/n)==h for n,h in assembly['inputs'].items())
    assert all(sha(HERE/n)==h for n,h in assembly['outputs'].items())
    assert sha(P/'README.md')==assembly['root_readme_sha256']
    pairs=read(HERE/'all_pairs.csv');top=read(HERE/'top5.csv')
    assert len(pairs)==44 and len({r['pair'] for r in pairs})==44
    assert sum(r['in_seed25']=='True' for r in pairs)==25
    assert sum(r['in_seed25']=='True' and r['commercial']=='True' for r in pairs)==23
    assert len(top)==5 and all(r['cohort']=='K2' and r['pair']!='AER-SVX' for r in top)
    assert [r['pair'] for r in top]==assembly['top5']
    assert [float(r['base_new_minus_same_W']) for r in top]==sorted([float(r['base_new_minus_same_W']) for r in top],reverse=True)
    for path in [HERE/'REPORT.md',HERE/'REPRODUCE.md',HERE/'WEEKLY.md',HERE/'COORDINATOR_REVIEW.md',HERE/'LATE_OWNER_DELTA.md',P/'README.md']:
        for target in re.findall(r'\]\(([^\s)]+)\)',path.read_text()):
            if '://' in target or target.startswith('#'):continue
            resolved=(path.parent/target.split('#')[0]).resolve()
            assert resolved==(HERE/'final_validation.json').resolve() or resolved.exists(),(path,target)

    money=read(E/'programmes_monthly.csv')
    assert len(money)==31608
    groups=defaultdict(dict)
    for r in money:
        near(float(r['net_revenue'])-float(r['variable_cost']),r['known_subtotal_before_C_D_F'])
        assert r['primary']=='DIRECT_ONLY' and float(r['through_journeys'])==0
        assert r['full_profit']=='NULL' and r['cash']=='NULL'
        groups[(r['candidate'],r['month'],r['scenario'])][r['state']]=r
    checked=0
    for states in groups.values():
        if len(states)!=3:continue
        K,W,R=[states[x] for x in ['KEEP','WITHOUT_NEW','REPLACE']]
        k,w,r=[float(x['known_subtotal_before_C_D_F']) for x in [K,W,R]]
        near(w-k,R['old_change_W_minus_K']);near(r-w,R['new_R_minus_W']);near(r-k,R['total_R_minus_K'])
        checked+=1
    assert sum(r['scenario']=='cautious' and r['state']=='REPLACE' and float(r['new_R_minus_W'])<0 for r in money)==5232

    delay=json.loads((E/'delay_stress_validation.json').read_text())
    first=json.loads((P/'delay_first_success.local.json').read_text())
    assert first['output_sha256']==delay['output_sha256'] and first['script_sha256']==delay['script_sha256']
    assert all(sha(E/n)==h for n,h in delay['output_sha256'].items())
    assert all(sha(E/n)==h for n,h in delay['financial_artifacts_unchanged'].items())
    trajectories=read(E/'delay_stress_trajectories.csv')
    bycase=defaultdict(list)
    for r in trajectories:
        key=tuple(r[k] for k in ['candidate','season','turn_minutes','hold_minutes','target_kind','trigger'])
        bycase[key].append(r)
    transitions=0
    for key,rows in bycase.items():
        turn,hold=int(key[2]),int(key[3])
        assert rows[0]['flight']==rows[0]['trigger']
        near((dt(rows[0]['shocked_departure_utc'])-dt(rows[0]['baseline_departure_utc'])).total_seconds()/60,hold)
        for i,r in enumerate(rows):
            planned,pa,base,ba,shock,sa=[dt(r[k]) for k in ['planned_departure_utc','planned_arrival_utc',
                'baseline_departure_utc','baseline_arrival_utc','shocked_departure_utc','shocked_arrival_utc']]
            near((ba-base).total_seconds(),(pa-planned).total_seconds())
            near((sa-shock).total_seconds(),(pa-planned).total_seconds())
            near((base-planned).total_seconds()/60,r['baseline_delay_minutes'])
            near((shock-planned).total_seconds()/60,r['total_delay_minutes'])
            near((shock-base).total_seconds()/60,r['incremental_minutes'])
            assert shock>=base and base>=planned
            if i:
                previous=rows[i-1]
                assert previous['destination']==r['origin']
                expected_base=max(planned,dt(previous['baseline_arrival_utc'])+timedelta(minutes=turn))
                expected_shock=max(planned,dt(previous['shocked_arrival_utc'])+timedelta(minutes=turn))
                assert base==expected_base and shock==expected_shock,(key,r['flight'])
                transitions+=1
    assert len(bycase)==144 and len(trajectories)==5584
    baselines=read(E/'delay_stress_baselines.csv')
    assert all(r['planned_schedule_feasible_2027']=='True' for r in baselines if r['turn_minutes']=='60')
    finals=set(assembly['three_programmes'])
    assert {r['candidate'] for r in baselines if r['turn_minutes']=='90' and r['planned_schedule_feasible_2027']=='False'}==finals
    gates=read(E/'operational_gates.csv')
    assert {r['candidate'] for r in gates if r['gate']=='CONTINUOUS_TURN_90' and r['status']=='CONTINUOUS_TURN_FAIL'}==finals
    late=json.loads((HERE/'late_owner/receipt.json').read_text())
    assert late['last_fetched_step1_pin']=='c11eb8c15d32add540d89d086f62487a5b2d424e'
    for original,h in late['source_sha256'].items():
        assert sha(HERE/'late_owner'/Path(original).name)==h
    late_rows=read(HERE/'late_owner/heading_comparison_check.csv')
    assert len(late_rows)==6
    for r in late_rows:
        near(float(r['displayed_R_minus_KEEP_mln'])-float(r['W_minus_KEEP_mln']),r['correct_new_R_minus_W_mln'])
        if r['scenario']=='cautious':assert float(r['correct_new_R_minus_W_mln'])<0
    output=dict(status='PASS_CONDITIONAL_RESEARCH_PACKAGE',actual_profit_verified=False,actual_dispatch_approved=False,
        root_only_correction_not_new_independent_acceptance=True,protected_unchanged=len(protected),
        numeric_monthly_rows=len(money),three_state_groups=checked,cautious_new_work_negative=5232,
        delay_trace_rows=len(trajectories),independent_trace_transitions=transitions,delay_groups=len(bycase),
        turn90_published_schedules_fail=sorted(finals),all_pairs=len(pairs),seed_pairs=25,
        qualified_fare_updates=0,actual_OD_net_invoice_updates=0,full_truth_audit_complete=False,
        last_fetched_step1=late['last_fetched_step1_pin'],late_owner_denominator_checks=6,
        script_sha256=sha(Path(__file__)),
        final_files_sha256={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='final_validation.json'})
    (HERE/'final_validation.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:output[k] for k in ['status','protected_unchanged','numeric_monthly_rows','three_state_groups','delay_trace_rows','independent_trace_transitions']},ensure_ascii=False))

if __name__=='__main__':verify()
