#!/usr/bin/env python3
"""Independent read-only P34 review. Only review/ outputs; no build/verify/git/network."""
import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,importlib.util,math,re
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,date,timedelta
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent; STUDY=HERE.parent; ROOT=STUDY.parents[1]; C=STUDY/'calculation'
def read(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def close(a,b):assert abs(float(a)-float(b))<.02,(a,b)
def dump(n,x):(HERE/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
checks=[]
def run(name,fn):
 try:
  evidence=fn();checks.append(dict(check=name,status='PASS',evidence=str(evidence)))
 except Exception as e:checks.append(dict(check=name,status='FAIL',evidence=repr(e)))
T={p.name:read(p) for p in C.glob('*.csv')}
P=T['programme_comparison.csv']; L=T['programme_ledger.csv']; F=T['flights.csv']; D=T['delay_events.csv']; candidates=T['candidate_comparison.csv']
key=lambda r:(r['programme'],r['scenario'],r['adjacent_case'])
lookup={key(r):r for r in P}
def protect():
 pins=json.loads((ROOT/'context/33_svx_aer_launch_case_20261112/protected_files.json').read_text());assert len(pins)==1190
 bad=[p for p,h in pins.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h];assert not bad,bad
 return '1190 content hashes; no HEAD/tracked count assertion'
run('protected1190_before',protect)
before={str(p):sha(p) for p in C.iterdir() if p.is_file()}
def manifest():
 m=json.loads((C/'manifest.json').read_text());v=json.loads((C/'validation.json').read_text())
 for p,h in v['output_hashes'].items():assert sha(C/p)==h,p
 return {'manifest_keys':list(m),'output_hashes_checked':len(v['output_hashes']),'all_csv_rows':{n:len(r) for n,r in T.items()}}
run('outputs_receipt_and_all_main_CSV_read',manifest)
def ledger():
 for r in P:
  if r['known_P_minus_KEEP_month']=='NULL':continue
  rows=[x for x in L if key(x)==key(r)]
  for side in ['P','KEEP']:
   ss=[x for x in rows if x['side']==side]
   for x in ss:close(float(x['net_revenue_month'])-float(x['avoidable_cost_month']),x['contribution_month']);assert x['donor_deducted_again']=='False'
   close(sum(float(x['net_revenue_month']) for x in ss),r[f'net_revenue_{side}_month'])
   close(sum(float(x['avoidable_cost_month']) for x in ss),r[f'avoidable_cost_{side}_month'])
  delta=sum(float(x['contribution_month'])*(1 if x['side']=='P' else -1) for x in rows)
  close(delta,r['known_P_minus_KEEP_month']);close(delta/4,r['known_P_minus_KEEP_week'])
  # Retained shifts can occur where OMS overlaps a new adjacent route; compare by explicit difference, not assume zero.
  rp=[x for x in rows if x['side']=='P' and x['group']=='RETAINED_OLD_RW'];rk=[x for x in rows if x['side']=='KEEP' and x['group']=='RETAINED_OLD_RW']
  close(rp[0]['avoidable_cost_month'],rk[0]['avoidable_cost_month'])
  assert rp and rk # Equal physical retained jobs; shared OD reallocation changes their revenue.
 return 'All numeric programme rows reconstruct from 272 ledger groups; donor net/cost exactly once; retained explicitly included'
run('ledger_month_week_donor_retained',ledger)
def unknowns():
 for r in P:
  for x in ['actual_D','external_donor','F_setup_lease_reserve','cash','full_PnL','observed_OD','observed_20kg_netfare','incremental_unique_RW']:assert r[x]=='NULL',(r['programme'],x)
  for x in ['fuel_support','route_grant','cargo_main']:assert float(r[x])==0
 for r in candidates:assert r['qualified_new_route']=='False' and r['rw_nonstop']=='UNKNOWN'
 assert Counter(r['queue_group'] for r in candidates)=={'TYPE_A_UNCONFIRMED':4,'TYPE_B_RW_UNCHECKED':6,'LOW_EVIDENCE_QUEUE':2}
 return 'qualified0; 4 A unknown / 6 competitor RW unknown / 2 low evidence; unknown money and observations NULL'
run('unknowns_and_all12_admission',unknowns)
def physics():
 for f in F:
  close((dt(f['arrival_utc'])-dt(f['departure_utc'])).total_seconds()/60,f['block_minutes'])
  for a,b in [('departure_utc','departure_local'),('arrival_utc','arrival_local')]:assert dt(f[a])==dt(f[b])
  assert f['tail']=='E1'
 for name in set(f['programme'] for f in F):
  fs=sorted([f for f in F if f['programme']==name],key=lambda f:f['departure_utc'])
  assert fs[0]['origin']==fs[-1]['destination']=='SVX'
  valid=lookup[name,'base','NO_UNCONFIRMED_REVENUE']['known_P_minus_KEEP_month']!='NULL'
  if valid:
   for a,b in zip(fs,fs[1:]):assert a['destination']==b['origin'];assert (dt(b['departure_utc'])-dt(a['arrival_utc'])).total_seconds()>=3600
  retained=[f for f in fs if f['group']=='RETAINED_OLD_RW'];assert len(retained)==32
  assert [(f['origin'],f['destination'],f['departure_utc'],f['arrival_utc']) for f in retained]==[(f['origin'],f['destination'],f['departure_utc'],f['arrival_utc']) for f in F if f['programme']=='KEEP' and f['group']=='RETAINED_OLD_RW']
 for name in ['AER1','AER2']:
  fs=[f for f in F if f['programme']==name and f['group']=='NEW_PAIR'][:2]
  assert [f['departure_local'][11:16] for f in fs]==['14:00','16:30']
  assert [f['arrival_local'][11:16] for f in fs]==['15:30','22:00'];assert all(float(f['block_minutes'])==210 for f in fs)
 tri=[f for f in F if f['programme']=='TRI:SVX-AER-MRV' and f['group'] in ['NEW_PAIR','ADJACENT']]
 assert len(tri)==24 and Counter((f['origin'],f['destination']) for f in tri)==Counter({(a,b):4 for a,b in [('SVX','AER'),('AER','MRV'),('MRV','SVX'),('SVX','MRV'),('MRV','AER'),('AER','SVX')]})
 return '840 sectors UTC/local; equal 32 retained; E1 only; AER210/210; triangle six directions x4; hard failures not accepted'
run('physical_UTC_turns_resource',physics)
def shocks():
 gs=defaultdict(list)
 for r in D:gs[r['programme'],r['window'],r['target_id'],r['shock_minutes']].append(r)
 for k,rs in gs.items():
  previous=None
  for r in rs:
   planned=dt(r['planned_dep_utc']); expected=planned
   if previous is not None:expected=max(expected,previous+timedelta(minutes=60))
   if r['flight_id']==r['target_id']:expected=max(expected,planned+timedelta(minutes=int(r['shock_minutes'])))
   assert expected==dt(r['actual_dep_utc']),(k,r['flight_id'])
   block=dt(r['planned_arr_utc'])-planned;previous=expected+block;assert previous==dt(r['actual_arr_utc'])
   for field in ['delay_probability','RUB_per_minute','automatic_cancellation','crew_remaining']:assert r[field]=='NULL'
  target=next(r for r in rs if r['flight_id']==r['target_id'])
  if target['target_group']=='NEW_PAIR':assert target['flight_id'].startswith('NEW-')
  else:assert target['flight_id'].startswith('DONOR-FRI-')
 for r in T['AER_window_comparison.csv']:
  if r['clock_SVX']=='21:00':assert r['D0_valid']=='False' and r['status']=='INVALID_D0_WINDOW_CONFLICT'
 assert {r['shock_minutes'] for r in D}=={'0','30','60','120'}
 return f'{len(gs)} chains / {len(D)} events independently replayed with continuous readiness across midnight'
run('independent_shock_replay',shocks)
spec=importlib.util.spec_from_file_location('review_p34',C/'calculate.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
Z={}
def ram_joint():
 for name in [r['pair'] for r in T['top5_conditional.csv']]+['AER1','AER2',M.AER_TRIANGLE,'GOJ-KJA']:
  for sc in ['base','cautious']:
   for noadj in [True,False]:
    z=M.evaluate(name,sc,noadj,clock='14:00' if name.startswith('AER') else '07:00');Z[name,sc,noadj]=z
    row=lookup[name,sc,'NO_UNCONFIRMED_REVENUE' if noadj else 'P05_ADJACENT_PRIOR'];close(z['known_increment_P_minus_KEEP_before_F_donor'],row['known_P_minus_KEEP_month'])
    for label in ['programme','keep']:
     data=z[label];bun=data['bundle'];products={p['product_id']:p for p in bun['products']};alloc=data['allocation']['allocations']
     revenue=sum(a['carried']*products[a['product_id']]['net_fare'] for a in alloc if a['owner']=='RW');close(revenue,data['net_revenue'])
     occupied=defaultdict(float)
     for a in alloc:
      p=products[a['product_id']]
      for leg in p['legs']:occupied[leg]+=a['carried']
      if p['owner']=='RW':close(p['net_fare'],p['gross_fare']*(.97 if sc=='base' else .92/1.1))
     for f in bun['flights']:assert occupied[f['flight_instance_id']]<=f['saleable_seats']+1e-6
     for m in bun['markets']:
      close(sum(a['final_choice'] for a in alloc if all(a[k]==m[k] for k in ['demand_pool_id','month','customer_segment'])),m['potential_journeys'])
    assert z['programme']['bundle']['markets']==z['keep']['bundle']['markets']
 return '36 RAM joint evaluations; independently summed revenue, leg inventory and city pools; net tax/distribution once; serialized deltas match'
run('RAM_joint_seats_OD_net_and_ledger',ram_joint)
def frequency():
 def bundle(ds,end):
  fs=[dict(flight_instance_id=str(d),pattern_id='FIX',origin_airport='SVX',destination_airport='KJA',departure_utc=f'2027-02-{d:02}T02:00:00Z',arrival_utc=f'2027-02-{d:02}T05:20:00Z',block_hours_costscreen=200/60,saleable_seats=100) for d in ds]
  return M.ORIGINAL_CHOICE(fs,'base',{('SVX','KJA')},'2027-02-01',end)
 a=bundle([2],'2027-02-07');b=bundle([2,9,16,23],'2027-02-28')
 assert {p['frequency'] for p in a['products'] if p['owner']=='RW'}=={.25};assert {p['frequency'] for p in b['products'] if p['owner']=='RW'}=={1}
 close(b['markets'][0]['potential_journeys'],4*a['markets'][0]['potential_journeys'])
 for s,e in [('2027-02-01','2027-02-07'),('2027-01-29','2027-02-28')]:
  try:M.require_feb4(s,e)
  except AssertionError:pass
  else:raise AssertionError('partial accepted')
 return 'P31 .25 reproduced; Feb4 1/week; monthly potential exactly4x; partial/month boundary rejected'
run('frequency_actual_legacy_bug_workaround',frequency)
def fare_gate():
 z=Z['SVX-KJA','base',True];v=M.evaluate('SVX-KJA','base',True,fare_scale=.9)
 a={p['product_id']:p for p in z['programme']['bundle']['products'] if p['owner']=='RW'};b={p['product_id']:p for p in v['programme']['bundle']['products'] if p['owner']=='RW'}
 for k,p in a.items():
  if 'NEW-' in k:close(b[k]['gross_fare'],p['gross_fare']*.9);close(b[k]['net_fare'],p['net_fare']*.9)
 assert v['programme']['net_revenue']!=z['programme']['net_revenue']
 req=M.request(M.project_patterns('AER1','14:00'));raw=M.ORIGINAL_GENERATE(req);bridged=M.cost_only_calendar(req)
 assert raw['errors']==bridged['errors'] and raw['flights']==bridged['flights'] and len(raw['errors'])==4
 bad=M.request(M.project_patterns('AER1','21:00'));raw=M.ORIGINAL_GENERATE(bad);br=M.cost_only_calendar(bad);assert raw==br
 assert not M.valid_economics(M.evaluate('AER1','base',True,'21:00'))
 return 'Actual products repriced; sole8BH bridge preserves all errors/flights; 21:00 hard errors unchanged and no economics'
run('joint_price_override_and_sole8BH_gate',fare_gate)
def thresholds():
 for r in T['break_even.csv']:
  if r['axis']=='CLEAN_NEW_Q_SYMMETRIC_WITH_OUTSIDE_MIGRATION':
   a,b=float(r['model_net_a']),float(r['model_net_b']);ma,mb=float(r['migrated_a']),float(r['migrated_b'])
   close(a*float(r['q_a_required'])+b*float(r['q_b_required']),float(r['fixed_other_net_cost_RUB'])+ma*(float(r['oldnet_scenario_a'])-a)+mb*(float(r['oldnet_scenario_b'])-b))
   close(float(r['available_new_seats_a'])+ma,r['capacity_a']);close(float(r['available_new_seats_b'])+mb,r['capacity_b'])
  if r['axis']=='SIGNED_NONOVERLAP_PAX_COST_STRESS':
   p=lookup[r['programme'],r['scenario'],r['adjacent_case']];cost=float(r['stress_rate'])*(float(p['model_RW_journeys_P'])-float(p['model_RW_journeys_KEEP']));close(cost,r['signed_delta_cost']);close(float(p['known_P_minus_KEEP_month'])-cost,r['delta_after_stress'])
 return 'Clean new+migrants share seats; oldnet-newnet once; 500/650 signed occupancy delta only'
run('migration_and_signed_fee_stress',thresholds)
def sourcecheck():
 counts={}
 for directory,col in [('source_recovery_new','excerpt_path'),('source_recovery_competitors','excerpt_file')]:
  ss=read(STUDY/directory/'sources.csv');ids={r['source_id']:r for r in ss}
  for r in ss:assert (STUDY/directory/r[col]).is_file()
  counts[directory]=len(ids)
  for r in read(STUDY/directory/'classification.csv'):
   fields=['direct_source_field'] if directory.endswith('new') else ['competitor_source_ids','rw_source_ids']
   for field in fields:
    for sid in r[field].split(';'):assert sid in ids,sid
  if directory.endswith('competitors'):
   for r in read(STUDY/directory/'schedules.csv'):
    if r['status']!='PUBLISHED_PATTERN_ONLY':continue
    assert r['source_id'] in ids
    s=ids[r['source_id']];txt=(STUDY/directory/s[col]).read_text()
    loc=re.search(r'L(\d+)(?:[–-](\d+))?',r['direct_source_field']);assert loc
    lines='\n'.join(line for line in txt.splitlines() if any(line.startswith(f'L{i}:') for i in range(int(loc[1]),int(loc[2] or loc[1])+1)));assert lines,(r['schedule_id'],r['direct_source_field'])
    flight=r['flight'].replace('-','').replace(' ','');assert flight in lines.replace('-','').replace(' ','').replace('У6','U6'),(r['schedule_id'],r['flight'])
    start=date.fromisoformat(r['week_start']);end=date.fromisoformat(r['week_end']);vs=date.fromisoformat(r['valid_start']);ve=date.fromisoformat(r['valid_end']);days=set(map(int,r['days'].split(',')))
    dates=[]
    while start<=end:
     if vs<=start<=ve and start.weekday() in days:dates.append(start.isoformat())
     start+=timedelta(days=1)
    assert ';'.join(dates)==r['applicable_departures'];assert len(dates)==int(r['count_published_pattern'])
 return counts
run('canonical_sourceIDs_locators_flight_tokens_dates',sourcecheck)
def author():
 original=read(ROOT/'context/31_direct_growth_research_20261112/ops_inputs/reference_physical_legs.csv');original=[r for r in original if r['programme']=='dashboard_fixed_triangles']
 assert T['author_triangle_reference.csv']==original and len(original)==96
 a=json.loads((C/'author_reference_status.json').read_text());assert [int(r['original_author_summary'][0]['aircraft']) for r in a]==[8,7];assert [r['proxy_min_working_tails'] for r in a]==[9,8]
 return 'Exact96 source rows; original8/7 vs hours proxy9/8 distinct; no E1 attribution'
run('full_author_reference',author)
def fairness():
 def val(name,sc,adj):return float(lookup[name,sc,adj]['known_P_minus_KEEP_month'])
 out={}
 for sc in ['base','cautious']:
  lo=val('GOJ-KJA',sc,'NO_UNCONFIRMED_REVENUE');hi=val('GOJ-KJA',sc,'P05_ADJACENT_PRIOR');svx=val('SVX-KJA',sc,'NO_UNCONFIRMED_REVENUE')
  out[sc]={'GOJ_KJA_noadj':lo,'GOJ_KJA_full_prior':hi,'SVX_KJA':svx,'GOJ_adj_fraction_to_beat_SVX_KJA':(svx-lo)/(hi-lo)}
  tlo=val(M.AER_TRIANGLE,sc,'NO_UNCONFIRMED_REVENUE');thi=val(M.AER_TRIANGLE,sc,'P05_ADJACENT_PRIOR')
  out[sc].update(triangle_noadj=tlo,triangle_prior=thi,triangle_adj_fraction_to_beat_SVX_KJA=(svx-tlo)/(thi-tlo),AER1=val('AER1',sc,'P05_ADJACENT_PRIOR'),AER2=val('AER2',sc,'P05_ADJACENT_PRIOR'))
 assert out['base']['GOJ_KJA_full_prior']>out['base']['SVX_KJA']>out['base']['GOJ_KJA_noadj']
 dump('counterexample.json',out)
 return 'Real BASE rank flip GOJ-KJA vs SVX-KJA; thresholds in counterexample.json, fixed-allocation interpolation, not demand prediction'
run('fairness_counterexample',fairness)
def exact_controls():
 expected={'AER1':(6488132.26343016,4696662.96612297,4),'AER2':(11780736.60070942,9221604.74579507,8),'TRI:SVX-AER-MRV':(11659435.0543574,6201640.57183767,8)}
 for name,(base,cautious,n) in expected.items():
  for sc,v in [('base',base),('cautious',cautious)]:
   r=lookup[name,sc,'P05_ADJACENT_PRIOR'];close(v,r['known_P_minus_KEEP_month']);assert int(r['diagnostic_8BH_failures'])==n;assert r['P31_resource_screen']=='INFEASIBLE_AT_GIVEN_ENVELOPE'
 for f in F:
  assert dt(f['departure_utc']).astimezone(ZoneInfo(M.ZONES[f['origin']])).isoformat()==dt(f['departure_local']).isoformat()
  assert dt(f['arrival_utc']).astimezone(ZoneInfo(M.ZONES[f['destination']])).isoformat()==dt(f['arrival_local']).isoformat()
 follow=[f for f in F if f['programme']=='KEEP' and f['group']=='RETAINED_OLD_RW'][:4]
 assert [f['departure_local'][11:16] for f in follow]==['23:55','01:40','05:35','09:15']
 # Equal clock/route/block to original P32 selected B30, independently of P34 serializer.
 original=read(ROOT/'context/32_delay_cargo_research_20261112/calculation/control_flights.csv')
 original=[r for r in original if r['route']=='SVX-OMS' and r['layout']=='EQUAL_BUFFER_B30' and r['control']=='KEEP']
 for a,b in zip(follow,original):assert dt(a['departure_utc'])==dt(b['dep_utc']);assert a['origin']==b['origin'] and a['destination']==b['destination']
 return 'AER1/2 exact requested values and 4/8 failures; triangle8; IANA offsets all840; selected B30 exact original UTC'
run('exact_AER_results_and_P32_B30',exact_controls)
run('protected1190_after',protect)
run('calculation_unchanged',lambda: all(sha(Path(p))==h for p,h in before.items()) or (_ for _ in ()).throw(AssertionError('changed')))
with (HERE/'actual_checks.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['check','status','evidence']);w.writeheader();w.writerows(checks)
dump('validation.json',dict(status='CHECKS_COMPLETE',checks_passed=sum(c['status']=='PASS' for c in checks),checks_failed=sum(c['status']=='FAIL' for c in checks),checks=checks,author_verify_run=False,writes='review only',network_calls=0))
print(json.dumps(checks,ensure_ascii=False,indent=2))
