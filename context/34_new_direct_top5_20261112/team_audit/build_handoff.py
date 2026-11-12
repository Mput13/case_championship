#!/usr/bin/env python3
"""Offline scoped intake. Writes only beside this script; never invokes source builders."""
import csv, hashlib, io, json, pathlib, subprocess
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
B=HERE.parent
C='ac5e3c80ef428e213372c31d15c7a56846671490'
H='79b48152ab8ff2a18648c7d6c5fb1df30525ba01'
BASE='context/35_full_programme_execution_20261112/'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def js(p,x):
 p=HERE/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def rows(b):
 t=b.decode('utf-8-sig');header=t.splitlines()[0];return list(csv.DictReader(io.StringIO(t),delimiter=';' if header.count(';')>header.count(',') else ','))
def table(p,rr):
 p=HERE/p;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
manifest=[]
def take(commit,path,dest=None,ref=None):
 raw=git('show',commit+':'+path);out='source_snapshot/'+(dest or path);p=HERE/out;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 manifest.append(dict(commit=commit,ref=ref,path=path,git_blob=git('rev-parse',commit+':'+path).decode().strip(),sha256=sha(raw),bytes=len(raw),snapshot=out))
 return raw
# Capture protected baseline before doing anything else.
protected=json.loads((ROOT/'context/33_svx_aer_launch_case_20261112/protected_files.json').read_text())
if not (HERE/'preservation_baseline.json').exists(): js('preservation_baseline.json',dict(head=git('rev-parse','HEAD').decode().strip(),protected={p:sha((ROOT/p).read_bytes()) for p in protected},historical_protected_manifest_matches=all(sha((ROOT/p).read_bytes())==h for p,h in protected.items())))
pins=json.loads((B/'source_pins.json').read_text());refs={r:git('rev-parse',r).decode().strip() for r in pins}
assert refs==pins
for x in json.loads((B/'input_snapshot_manifest.json').read_text()):
 raw=take(x['commit'],x['path'],ref=x['ref']);assert sha(raw)==sha((B/x['snapshot']).read_bytes());assert manifest[-1]['git_blob']==x['git_blob']
extra=['P08/SVX/research_v1/evidence/SVX_primary_schedule_products.csv','P08/SVX/research_v1/evidence/P02_market_coverage_selected.csv','P08/MOSCOW/research_v1/economics_contract.json','P08/MOSCOW/research_v1/assumptions.json','P09/handoff.json','P09/handoff.md','P09/canonical_summary.csv','P09/data_contract.json','P09/validation.json','P09/projection_contract.json','P15/integration_coverage.json','P15/handoff.md']
for p in extra:take(C,BASE+p)
local=['context/31_direct_growth_research_20261112/'+p for p in ['audit/common_contract.json','route_economics/API_handoff.json','route_economics/calculate.py','ops_inputs/calendar_engine.py','ops_inputs/handoff.json','ops_inputs/cli_example.json']]+['context/32_delay_cargo_research_20261112/calculation/calculate.py','context/32_delay_cargo_research_20261112/calculation/control_flights.csv','context/33_svx_aer_launch_case_20261112/operations/KEEP_rotation.csv','context/33_svx_aer_launch_case_20261112/operations/notes.md','context/33_svx_aer_launch_case_20261112/inputs/sheremetyevskoe-shosse.txt']
for p in local:
 take(H,p);assert sha((ROOT/p).read_bytes())==manifest[-1]['sha256']
# Real path availability in all locally available origin refs; no fetch and no claims about unfetched history.
av=[]
for line in git('for-each-ref','--format=%(refname:short) %(objectname)','refs/remotes/origin').decode().splitlines():
 r,c=line.split();paths=git('ls-tree','-r','--name-only',c).decode().splitlines();found=[p for p in paths if any(part.upper().startswith('P08I') for part in p.split('/'))]
 av.append(dict(ref=r,commit=c,p08i_paths=found))
js('availability.json',dict(as_of='2026-11-12',scope='all local origin refs; no remote fetch; path names only',refs=av,p08i_found=any(x['p08i_paths'] for x in av),p08_svx=True,p08_moscow=True,p09_results_present=True,p15_binding='OPEN'))
def snap(p):return (HERE/'source_snapshot'/p).read_bytes()
svx=rows(snap(BASE+'P08/SVX/research_v1/direct_candidates.csv'));mow=rows(snap(BASE+'P08/MOSCOW/research_v1/direct_candidates.csv'));me=rows(snap(BASE+'P08/MOSCOW/research_v1/market_evidence.csv'));rw=rows(snap('data/manual/rw_routes_now.csv'))
canon=lambda s:'-'.join(sorted(s.replace(':','-').split('-')))
pairs=['GOJ-KJA','GOJ-TOF','KUF-TOF','OMS-PEE','PEE-TOF','OMS-REN','TJM-MRV','CEK-MRV','SVX-KJA','SVX-IKT','SVX-VVO','SVX-KHV']
oldpath='context/31_direct_growth_research_20261112/route_economics/fastscreen.csv';oldraw=git('show',H+':'+oldpath);old=rows(oldraw)
selected=[r for r in old if canon(r['pair_id']) in {canon(x) for x in pairs} and r['added_pairs_week'] in ['1','2'] and r['year']=='2027']
table('source_snapshot/p31_fastscreen_12pairs.csv',selected)
manifest.append(dict(commit=H,ref='HEAD at intake',path=oldpath,git_blob=git('rev-parse',H+':'+oldpath).decode().strip(),source_sha256=sha(oldraw),snapshot='source_snapshot/p31_fastscreen_12pairs.csv',sha256=sha((HERE/'source_snapshot/p31_fastscreen_12pairs.csv').read_bytes()),selection='12 requested pairs, year2027, base/cautious, added_pairs_week in [1,2]; exact rows, no recomputation',rows=len(selected)))
seed=[]
for pair in pairs:
 key=canon(pair);ss=[r for r in svx if canon(r['airport_pair'])==key];mm=[r for r in mow if key in [canon(x) for x in r['pairs'].split(';')]];ee=[r for r in me if canon(r['airport_pair'])==key];ww=[r for r in rw if canon(r['a']+'-'+r['b'])==key];oo=[r for r in selected if canon(r['pair_id'])==key]
 seed.append(dict(pair=pair,pair_key=key,oldscreen_rows=len(oo),oldscreen_source='source_snapshot/p31_fastscreen_12pairs.csv',oldscreen_scope='2027 annual scenario; NOT target-week rank',old_rw_scenarios=';'.join(sorted({r['old_rw_frequency_scenario'] for r in oo})),p08_svx_ids=';'.join(r['candidate_id'] for r in ss),p08_moscow_ids=';'.join(r['programme_id'] for r in mm),p08_pair_present=bool(ss or mm),p08_market_status=';'.join(r['status'] for r in ee) or ('PARTIAL' if ss else 'NO_P08_PAIR'),p08_signal=';'.join(r['signal'] for r in ss),p08_source_periods=';'.join(r['source_periods'] for r in ss),step1_rw_rows=len(ww),step1_rw_source=';'.join(r['source'] for r in ww),observed_week='2026-11-16/2026-11-22',observed_week_full_coverage=False,target_week='2027-02-01/2027-02-07',target_week_full_coverage=False,rw_nonstop_observed_week='UNKNOWN',rw_nonstop_target_week='UNKNOWN',classification='UNKNOWN_NOT_QUALIFIED',rank='',demand='PRIOR_NOT_OBSERVED',netyield='SCENARIO_NOT_OBSERVED',new_numeric_calibration=False,source='P08 direct_candidates + market_evidence; step1 rw_routes_now; exact pins in inputs_manifest.json',gap='Need dated full competitor/RW coverage for each week; own through/partner passengers; exact basket and net yield; operations/donor pending'))
table('candidate_seed.csv',seed)
oldcontract=json.loads(snap('context/31_direct_growth_research_20261112/audit/common_contract.json'))
contract=dict(version='P34-team-audit-v1',status='PREPARATORY_CONDITIONAL_NOT_FINAL_TOP5',source_commits=pins,period=dict(observed_week=['2026-11-16','2026-11-22'],target_week=['2027-02-01','2027-02-07'],windows=['2027-02-02','2027-02-05'],rule='Weeks separate; published season is not actual flown; no annualisation without explicit repeat/season model'),control_resource=dict(working_tail='E1 conditional existing RRJ; exact variant and released tail UNKNOWN',initial_position='SVX conditional; pay any required positioning',working_tail_count=1,separate_reserve_count=1,reserve='conditional RES-1 never scheduled as working tail',new_SJ_before='2027-07-01 prohibited',published_fleet_is_free=False,KEEP='Same affected future existing products and deferred donor tasks across every alternative',deferred_donors='Both Tue/Fri assignments and eventual displaced/re-timed work UNKNOWN; include eventual avoided cost/net revenue once; no free idle assumption',window_start_end_UTC=None),programmes=dict(KEEP='P=KEEP identity; delta=0, business not zero',triangle_Tue=['SVX','A','B','SVX'],triangle_Fri=['SVX','B','A','SVX'],triangle_sectors=6,triangle_pair_returns_per_week=1,rule='Include all six sectors/cycles/BH/turns, endpoint markets and common OLD_RW; no free base or sum of solo margins; one new pair RT is not two partner RTs',AER_1RT='Tue SVX-AER-SVX; Friday KEEP',AER_2RT='Tue and Fri SVX-AER-SVX',ops_status='pending variant/route/AFM payload/slots/crew/rest/MRO; geometry only; 8BH diagnostic not FDP'),cost=dict(cases=oldcontract['cases'],source='P31 common_contract + fresh step1 network; changes require explicit admission',price_basis='constant 2026 RUB; not nominal forecast',donor='P-minus-KEEP includes donor if in scope. Deduct only outside-scope forgone contribution once; use avoidable costs, not allocated total cost',support_main=0,cargo_main=0,F=None,full_PnL=None,cash=None,tax='gross passenger cash, net accrual and recoverability separated; unknown not zero'),demand=dict(unit='directed endpoint journeys, not sectors or boardings',prior='P05 scenario only; same OD pools for all programmes and KEEP',choice='P05 base/cautious coefficients not empirically calibrated',saturation='shared seat cap is constraint, not observed demand',fare_basket='same quote moment; economy 1 adult one way 20kg + fees; absent basket UNKNOWN',price_sensitivity='sheremetyevskoe-shosse qualitative practice; RUB5000 example is not RW elasticity or OD',no_direct='dated full coverage of all carriers; unknown not qualified; RW nonstop confirmed -> frequency comparator'),discount=dict(valuation='undiscounted target-week operating contribution screen',rate=None,NPV=None,rule='No implicit NPV or cash; multi-period analysis needs explicit dates/rate/price basis'),migration=dict(OLD_RW_0='scenario only, not fact no customer',scope='all common adjacent markets + existing RW nonstop/through/partner/charter',rule='joint allocate P and KEEP on same pools, count coupon/revenue/taxes once; new seats not automatically new RW customers'),units=dict(money='RUB constant2026; net/gross labelled',time='timezone-aware UTC and local IANA; directed block minutes; BH=minutes/60',frequency='closed return per week; each directed leg counted once',passengers='endpoint journeys; physical occupied sectors separate'),P33_correction=dict(input_preserved=True,claimed_blocks=[210,210],actual_input_blocks=[330,150],canonical_clocks=['14:00 SVX','15:30 AER','16:30 AER','22:00 SVX'],turn_min=60,required='Calculator must create corrected canonical CSV with independently checked local/UTC; P33 following KEEP clocks also inconsistent: reuse P32 controlled chain with proper KUF timezone Europe/Samara, blocks100/105, do not inherit P33 follow rows',actual_blocks_slots='UNKNOWN'))
js('common_contract.json',contract)
js('inputs_manifest.json',dict(version=1,head=H,entries=manifest,policy='Exact git blobs except explicit P31 row slice; no external search; immutable in-place APIs retain pinned dependency snapshots; source label is not independent admission'))
print(json.dumps(dict(snapshot_files=len(manifest),snapshot_bytes=sum(p.stat().st_size for p in (HERE/'source_snapshot').rglob('*') if p.is_file()),P08_matches=[r['pair'] for r in seed if r['p08_pair_present']],p08i_found=any(x['p08i_paths'] for x in av),protected=len(protected)),ensure_ascii=False))
