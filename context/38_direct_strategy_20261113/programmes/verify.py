#!/usr/bin/env python3
"""Offline semantic/negative fixtures and deterministic replay. Writes HERE only."""
import sys
sys.dont_write_bytecode=True
import copy
import csv
import hashlib
import importlib.util
import json
import subprocess
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

O=Path(__file__).resolve().parent
R=O.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p):return json.loads(Path(p).read_text())
def rows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')))
spec=js(O/'programme_specs.json');cov=js(O/'search_coverage.json');manifest=js(O/'input_manifest.json')
checks={};errors=[]
def check(k,c,detail=None):
    checks[k]=dict(pass_=bool(c),detail=detail)
    if not c:errors.append(k)

s=importlib.util.spec_from_file_location('p38_weekly_generate_readonly',O/'generate.py')
G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
G.COHORTS.update(spec['resources']);G.OPTIONS.update(spec['chain_options']);G.PATHS.update(spec['paths'])
def compact(jobs):
    return sorted((j['id'],f['flight_id'],f['tail'],f['origin'],f['destination'],f['dep'],f['arr'],f['block'],f['kind'])
                  for j in jobs for f in j['flights'])

def independent_calendar(jobs,positions):
    """Separate continuous datetime proof on3whole weekly repeats, no modulo
    adjacency implementation shared with generator. Uses real IANA dates.
    """
    allfs=[]
    for w in (-1,0,1):
        for j in jobs:
            for f in j['flights']:
                allfs.append(dict(f,dep_date=G.REF+timedelta(minutes=f['dep']+w*G.WEEK),
                                  arr_date=G.REF+timedelta(minutes=f['arr']+w*G.WEEK)))
    for tail,initial in positions.items():
        seq=sorted([f for f in allfs if f['tail']==tail],key=lambda f:(f['dep_date'],f['flight_id']))
        pos=initial;ready=None
        for f in seq:
            if pos!=f['origin'] or (ready is not None and f['dep_date']<ready):return False
            if (f['arr_date']-f['dep_date']).total_seconds()!=f['block']*60:return False
            a=f['dep_date'].astimezone(ZoneInfo(G.ZONES[f['origin']]))
            b=f['arr_date'].astimezone(ZoneInfo(G.ZONES[f['destination']]))
            if (b.astimezone(timezone.utc)-a.astimezone(timezone.utc)).total_seconds()!=f['block']*60:return False
            pos=f['destination'];ready=f['arr_date']+timedelta(minutes=60)
        if pos!=initial:return False
    return all(f['tail'] in positions and f['tail']!='R1' for f in allfs)

def guard(m):
    return [p for p,h in m.items() if not (R/p).is_file() or sha(R/p)!=h]

check('protected1621',len(manifest['protected1621'])==1621 and not guard(manifest['protected1621']))
check('completed_P36_P37_hashes',not guard(manifest['completed_P36_P37']),len(manifest['completed_P36_P37']))
check('input_read_hashes',not guard(manifest['read_sources']),len(manifest['read_sources']))
check('no_mutable_metadata_guard',all('publication_instruction' not in p and 'source_pins' not in p and '.git/' not in p
     and not (p.startswith('context/38_') and not any(x in p for x in ['/market_admission/','/cost_admission/','/contract/','/pair_seed.csv','/source_gate_for_calculation.md']))
     for p in manifest['read_sources']))
for name in ['programme_catalog.csv','old_assignment_actions.csv','calendar_checks.csv','rejections.csv','representative_calendars.csv']:
    raw=list(csv.reader((O/name).open(newline='')))
    check('width_'+name,bool(raw) and len(set(raw[0]))==len(raw[0]) and all(len(r)==len(raw[0]) for r in raw[1:]),len(raw)-1)
check('bounded150to500',150<=len(spec['programmes'])<=500,len(spec['programmes']))
check('financial_keys_unique',len({p['financial_template_key'] for p in spec['programmes']})==len(spec['programmes']))
check('primary_resource_counts',[len(spec['resources'][k]['old_jobs']) for k in ['K1','K2','K3']]==[11,15,15])
check('canonical_K1_T1',all(j['tail']=='T1' for j in spec['resources']['K1']['old_jobs']))
check('working1_2_3_plus_one_R1',all(len(spec['resources'][k]['positions'])==n and spec['resources'][k]['reserve']['id']=='R1'
      and spec['resources'][k]['reserve']['working'] is False for k,n in [('K1',1),('K2',2),('K3',3)]))
check('partially_unknown_never_actual0',all(c['outside_D'] is None and c['F'] is None and c['actual_release'] is None
      and c['actual_initial_positions'] is None for c in spec['resources'].values())
      and spec['resources']['K3']['old_D3'] is None and spec['gates']['reserve_R1_price'] is None
      and spec['gates']['fullPnL'] is None and spec['gates']['cash'] is None)
check('no_monthly_income_or_old_builder',not manifest['monthly_income_called'] and not manifest['old_builders_or_verifiers_called']
      and spec['financial_helper']['monthly_engine_called'] is False)

byid={p['id']:p for p in spec['programmes']}
allvariants=[];bad=[];oldbad=[];tailbad=[];boundbad=[];ferrybad=[];durationsbad=[]
for p in spec['programmes']:
    for v in p['variants']:
        allvariants.append((p['id'],v));co=spec['resources'][v['cohort']]
        states=G.states_for(v);ids={j['id'] for j in co['old_jobs']}
        if set(v['action_map'])!=ids:oldbad.append(p['id'])
        for state,jobs in states.items():
            old=[j for j in jobs if not j['id'].startswith('NEW-')]
            # All old IDs exactly once per state, same changes in W and R.
            if len({j['id'] for j in old})!=len(old) or not {j['id'] for j in old}.issubset(ids):oldbad.append((p['id'],state))
            if not independent_calendar(jobs,co['positions']):bad.append((p['id'],state))
            if not G.check_calendar(jobs,co['positions'],full=True)['hard_pass']:bad.append((p['id'],state,'generator'))
            if any(f['tail'] not in co['positions'] or f['tail']=='R1' for j in jobs for f in j['flights']):tailbad.append(p['id'])
            for j in jobs:
                for f in j['flights']:
                    if f['kind']=='PAID_FERRY' and (f['seats']!=0 or f.get('revenue',0)!=0):ferrybad.append(f['flight_id'])
                    if f['arr']-f['dep']!=f['block']:durationsbad.append(f['flight_id'])
        oldr=[j for j in states['REPLACE'] if j['id'] in ids]
        if compact(oldr)!=compact(states['WITHOUT_NEW']):oldbad.append((p['id'],'W/R'))
        counts=Counter(spec['chain_options'][o]['tail'] for o in v['option_ids'])
        if v['cohort'].startswith('K') and max(counts.values(),default=0)>2:boundbad.append(p['id'])
        if v['cohort'].startswith('K') and not v['legacy_programme_ids']:
            if any(j['origin']!='SVX' or j['destination']!='SVX' for o in v['option_ids'] for j in spec['chain_options'][o]['jobs']):tailbad.append((p['id'],'REGIONAL_PHANTOM'))
check('all_variants_all3states_independent_periodic',not bad,dict(variants=len(allvariants),states=3*len(allvariants),bad=bad[:10]))
check('oldids_unique_same_action_allstates',not oldbad,oldbad[:10])
check('no_phantom_tail_or_regional_free_airframe',not tailbad,tailbad[:10])
check('max2closedpaths_per_workingtail',not boundbad)
check('all_ferry_capacity_revenue_zero',not ferrybad)
check('all_UTC_local_durations',not durationsbad)
check('calendar_receipt_exact',len(rows(O/'calendar_checks.csv'))==3*len(allvariants)
    and all(r['hard_pass']=='True' and r['crew_FDP_rest']=='UNKNOWN' and r['actual_initial_ready']=='UNKNOWN'
            for r in rows(O/'calendar_checks.csv')))
act=rows(O/'old_assignment_actions.csv')
check('action_rows_unique_all_old_once',len({(r['programme_id'],r['variant'],r['old_stable_id']) for r in act})==len(act)
      and all(r['WITHOUT_NEW']==r['REPLACE'] and r['cancellation_shared_W_R']=='True' and r['cancellation_cost']=='UNKNOWN' for r in act))
# Independent reconstruction of all60 exact legacy calendars, including aliases.
inventory=rows(O.parent/'contract/programme_inventory.csv')
refs=spec['legacy_programme_references']
check('all60_and37positive',len(refs)==60 and set(refs)=={r['candidate_id'] for r in inventory}
      and sum(r['positive_new_vs_same_without']=='True' for r in inventory)==37)
eq={(r['candidate_id'],r['state']):(r['equivalent_candidate'],r['equivalent_state']) for r in rows(G.P36/'pass2/equivalence_map.csv') if r['scenario']=='base'}
ledger=rows(G.P36/'pass2/revenue_cost_ledger.csv')
legacybad=[]
for cid,ref in refs.items():
    v=byid[ref['programme_id']]['variants'][ref['variant_index']]
    ss=G.states_for(v)
    for state in ss:
        alias,label=eq[cid,state]
        expected=sorted((r['job_id'],r['flight_id'].removesuffix('/W1'),r['tail'],r['origin'],r['destination'],
                         G.minute(r['departure_utc']),round(float(r['fixed_crew_excluded'])/15000*60),
                         'PAID_FERRY' if r['kind']=='positioning' else 'SERVICE')
            for r in ledger if r['scenario']=='base' and r['candidate_id']==alias and r['state']==label and r['flight_id'].endswith('/W1'))
        got=sorted((j['id'],f['flight_id'],f['tail'],f['origin'],f['destination'],f['dep'],f['block'],f['kind']) for j in ss[state] for f in j['flights'])
        if expected!=got:legacybad.append((cid,state))
check('all60_exact_legacy_180states',not legacybad,legacybad[:10])
seed={r['pair'] for r in rows(O.parent/'pair_seed.csv')}
covered=cov['seed_pair_coverage']
check('all25_seed_explicit_reasons',set(r['pair'] for r in covered)==seed and all(r['reason'] and r['selected_financial_templates']>0 for r in covered))
check('103paths_real_search',sum(p['source']=='P36_103' for p in spec['paths'].values())==103
      and all(r.get('assigned_config_attempts',0)>0 for r in cov['path_coverage']))
check('discrete_axes_exact',cov['search_axes']['ISO_start_days']==list(range(1,8))
      and cov['search_axes']['local_windows']==[6,10,14,20] and cov['search_axes']['frequencies']==[1,2,3,5,7]
      and cov['search_axes']['old_shifts']==[-180,-120,-60,-30,30,60,120,180])
catalog=rows(O/'programme_catalog.csv')
check('mixed_same_tail_and_multi_tail1_2_3',
      any(r['cohort']=='K1' and int(r['paths'])==2 for r in catalog)
      and any(r['cohort']=='K2' and int(r['new_working_tails'])==2 for r in catalog)
      and any(r['cohort']=='K3' and int(r['new_working_tails'])==3 for r in catalog))
classes={x for r in catalog for x in r['families'].split(';')}
check('selected_truecycles4_5_6_concat_rt',{'TRUE_CYCLE4','TRUE_CYCLE5','TRUE_CYCLE6','CONCAT_RT','RT','TRIANGLE'}.issubset(classes),sorted(classes))
check('all_physical_action_families',{'INSERT','SHIFT','REMOVE','SWAP'}.issubset({r['action_family'] for r in catalog}),
      sorted({r['action_family'] for r in catalog}))
# Fixtures with controlled UTC minutes; no dependency on favourable old clocks.
def job(jid,path,start,block=60,gap=60,tail='T1'):
    fs=[];t=start
    for i,(a,b) in enumerate(zip(path,path[1:])):
        fs.append(dict(flight_id=jid+'/L'+str(i+1),job_id=jid,tail=tail,origin=a,destination=b,
                       dep=t,arr=t+block,block=block,kind='SERVICE',seats=100,evidence='fixture'))
        t+=block+gap
    return G.complete_job(dict(id=jid,tail=tail,flights=fs))
pos={'T1':'SVX'}
a=job('A',['SVX','KUF','SVX'],0)
good=job('B',['SVX','UFA','SVX'],240)
short=job('B',['SVX','UFA','SVX'],239)
overlap=job('B',['SVX','UFA','SVX'],30)
check('fixture_turn60_vs59',G.check_calendar([a,good],pos)['hard_pass'] and not G.check_calendar([a,short],pos)['hard_pass'])
check('fixture_overlap_rejected',not G.check_calendar([a,overlap],pos)['hard_pass'])
check('fixture_mixed_cannot_sum_solo_feasibility',G.check_calendar([a],pos)['hard_pass']
      and G.check_calendar([overlap],pos)['hard_pass'] and not G.check_calendar([a,overlap],pos)['hard_pass'])
oldfixture=job('OLD_UNION',['SVX','OMS','SVX'],90)
secondnew=job('NEWSECOND',['SVX','UFA','SVX'],300)
check('fixture_shared_minclosure_oldid_once',G.clashes([oldfixture],[a,secondnew])==['OLD_UNION']
      and G.check_calendar([a,secondnew],pos)['hard_pass'])
moved=G.changed([oldfixture],swaps={'OLD_UNION':'T2'})
check('fixture_whole_old_transfer_requires_working_tail',G.check_calendar(moved+[a],{'T1':'SVX','T2':'SVX'})['hard_pass']
      and not G.check_calendar(moved+[a],{'T1':'SVX'})['hard_pass']
      and {f['tail'] for f in moved[0]['flights']}=={'T2'})
sun=job('SUN',['SVX','KUF','SVX'],G.WEEK-180)
mon=job('MON',['SVX','UFA','SVX'],0)
check('fixture_weekwrap_no_reset',not G.check_calendar([sun,mon],pos)['hard_pass'] and not independent_calendar([sun,mon],pos))
phantom=job('PHANTOM',['GOJ','KUF','GOJ'],100,tail='T9')
check('fixture_no_phantom',not G.check_calendar([phantom],pos)['hard_pass'])
notclosed=job('AWAY',['SVX','GOJ'],100)
check('fixture_position_not_teleport',not G.check_calendar([notclosed],pos)['hard_pass'])
# Separate UTC midnight diagnostic can be below8 each day and still cannot
# assert a lawful crew duty. No FDP number is manufactured.
long=job('LONG',['SVX','KJA','SVX'],21*60,block=270,gap=60)
ck=G.check_calendar([long],pos,full=True)
check('fixture_midnight_not_FDP',ck['hard_pass'] and ck['FDP']=='UNKNOWN_NOT_CHECKED_BY_MIDNIGHT'
      and sum(f['block'] for f in long['flights'])==540)
dup=[a,copy.deepcopy(a)]
check('fixture_duplicate_old_rejected',not G.check_calendar(dup,pos)['hard_pass'])
reverse=(G.path_class(dict(path=['SVX','CEK','MRV','SVX'])),G.path_class(dict(path=['SVX','MRV','CEK','SVX'])))
check('fixture_small_reverse_and_truecycle_vs_concat',reverse==('TRIANGLE','TRIANGLE')
      and G.path_class(dict(path=['SVX','KUF','UFA','REN','SVX']))=='TRUE_CYCLE4'
      and G.path_class(dict(path=['SVX','KUF','SVX','UFA','SVX']))=='CONCAT_RT')
# Same direct-only financial key can have different calendar feasibility.
for oid,j in [('FIXA',a),('FIXB',good),('FIXBAD',overlap)]:
    G.OPTIONS[oid]=dict(id=oid,jobs=[j],tail='T1',path_id='FIXPATH'+('A' if oid=='FIXA' else 'B'),
                       topology_class='RT',iso_weekdays=[1])
v1=dict(cohort='FIX',action_map={},option_ids=['FIXA','FIXB'],new_jobs=[a,good])
v2=dict(cohort='FIX',action_map={},option_ids=['FIXA','FIXBAD'],new_jobs=[a,overlap])
check('fixture_financial_equivalence_not_calendar_proof',G.finite_signature(v1)==G.finite_signature(v2)
      and G.check_calendar(v1['new_jobs'],pos)['hard_pass'] and not G.check_calendar(v2['new_jobs'],pos)['hard_pass'])
evidence=spec['supply_evidence'];source=rows(O.parent/'market_admission/canonical_services.csv')
check('all130_evidence_periods_preserved',len(evidence)==130 and all(
    any(e['service_id']==s['service_id'] and all(e[k]==s[k] for k in ['origin','destination','valid_start','valid_end','covered_dates','departure_local','arrival_local','source_id']) for e in evidence)
    for s in source))
check('own_RW_TOF_GOJ_positive_not_zero',any(e['pair']=='SVX-TOF' and '5003' in e['flight'] for e in evidence)
      and any(e['pair']=='GOJ-SVX' and ('5030' in e['flight'] or '5029' in e['flight']) for e in evidence)
      and 'CONFLICT' in spec['period_gates']['WZ5030'])
check('TOF_not_TOX',spec['timezones']['TOF']=='Asia/Tomsk' and 'TOX' not in spec['timezones'])
overnights=[(a,b,o) for o in spec['chain_options'].values() for j in o['jobs'] for a,b in zip(j['flights'],j['flights'][1:])
            if b['dep']-a['arr']>=480 and a['destination']!='SVX']
check('real_overnight_cost_unknown',bool(overnights) and all(o['overnight_cost'] is None for a,b,o in overnights))
n=spec['nested_allocations']
nestedbad=[]
for p in n['pairs']:
    lo=byid[p['lower_programme']]['variants'][0];hi=p['upper_variant']
    if lo['cohort']!='K2' or hi['cohort']!='K3' or lo['action_map']!=hi['action_map']:nestedbad.append(p['id'])
    if {j['id'] for j in G.COHORTS['K2']['old_jobs']}!=set(p['master_old_job_ids']):nestedbad.append(p['id'])
    for st,jobs in G.states_for(hi).items():
        if not independent_calendar(jobs,G.COHORTS['K3']['positions']):nestedbad.append((p['id'],st))
check('nested_K2_K3_same_master_physical_allstates',len(n['pairs'])>0 and not nestedbad,nestedbad)
check('K1_K2_core_constraint_no_fake_marginal',n['K1_to_K2']['status']=='CORE_CONSTRAINT_FOR_MONTHLY_ENGINE'
      and len(n['K1_to_K2']['canonical_K1_missing_master_ids'])==4
      and n['K1_to_K2']['fixed_master_KEEP_one_tail_hard_pass'] is False and n['actual_marginal_value'] is None)
# Reuse ONLY the completed pure calendar API, never evaluate_month/income.
cs=importlib.util.spec_from_file_location('p38_contract_calendar_only',O.parent/'contract/month_adapter.py')
C=importlib.util.module_from_spec(cs);cs.loader.exec_module(C)
monthly_receipts=[];datebad=[]
representatives=rows(O/'representative_calendars.csv')
for sid in ('K1','K2','K3'):
    pid=next(r['programme_id'] for r in representatives if r['cohort']==sid)
    v=byid[pid]['variants'][0];positions=spec['resources'][sid]['positions']
    for month in (1,2,7):
        for state,jobs in G.states_for(v).items():
            try:
                cal=C.calendar_events(jobs,C.resources(positions),2027,month)
                monthly_receipts.append(dict(programme_id=pid,cohort=sid,state=state,month=month,flights=len(cal['flights']),
                    BH8_diagnostics=len(cal['errors']),carry=cal['carry']))
            except Exception as e:datebad.append(dict(cohort=sid,month=month,state=state,error=str(e)))
check('representative1_2_3tails_allstates_JanFebJul_calendar_only',not datebad and len(monthly_receipts)==27,datebad)
early=C.resources(pos);early[0]['type']='SJ100_PD8'
early_rejected=False
try:C.calendar_events([a],early,2027,2)
except ValueError as e:early_rejected='SJ_BEFORE_H2' in str(e)
check('fixture_future_SJ_not_existing_RRJ_beforeH2',early_rejected and 'UNKNOWN' in spec['period_gates']['SJ'])
# At least2commercial departures each direction for triangle pilot test.
pilot=[]
for pid,v in allvariants:
    if v['cohort'] not in ('K1','K2','K3'):continue
    inv=Counter((f['origin'],f['destination']) for o in v['option_ids'] for j in spec['chain_options'][o]['jobs']
                for f in j['flights'] if f['kind']=='SERVICE')
    if inv['GOJ','KJA']>=2 and inv['KJA','GOJ']>=2:pilot.append(pid)
check('both_triangle_orientations_pilot2each',bool(pilot),pilot[:6])
# Exact generated-byte replay. No old exporters/verifiers, no writes elsewhere.
names=['programme_specs.json','programme_catalog.csv','old_assignment_actions.csv','calendar_checks.csv',
       'search_coverage.json','rejections.csv','representative_calendars.csv','input_manifest.json','README.md','engine_handoff.md']
before={n:sha(O/n) for n in names}
run=subprocess.run([sys.executable,'-B',str(O/'generate.py')],cwd=R,capture_output=True,text=True)
after={n:sha(O/n) for n in names}
check('deterministic_repeat',run.returncode==0 and before==after,dict(exit=run.returncode,changed=[n for n in names if before[n]!=after[n]],stderr=run.stderr[-2000:]))
check('protected1621_after_repeat',not guard(manifest['protected1621']))
check('completed_P36_P37_after_repeat',not guard(manifest['completed_P36_P37']))
required=['README.md','engine_handoff.md','programme_specs.json','programme_catalog.csv','old_assignment_actions.csv',
          'calendar_checks.csv','search_coverage.json','rejections.csv','generate.py','verify.py','input_manifest.json']
check('required_outputs',all((O/n).is_file() for n in required))
out=dict(status='PASS' if not errors else 'FAIL',checks=checks,errors=errors,
         counts=cov['output_counts'],fixture_scope='weekly feasibility/specs only; actual release/crew/slot/MRO/OD/net/fullPnL UNKNOWN',
         monthly_calendars_only=monthly_receipts,monthly_income_calls=0,
         deterministic_output_hashes=after,generate_sha256=sha(O/'generate.py'),verify_sha256=sha(O/'verify.py'),
         protected_count=1621,completed_P36_P37_files=len(manifest['completed_P36_P37']))
(O/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(status=out['status'],checks=len(checks),errors=errors,counts=out['counts']),ensure_ascii=False))
raise SystemExit(bool(errors))
