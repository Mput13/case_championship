"""Read-only review of frozen inputs; writes exclusively to review_final. No search/optimizer.
Uses pinned Demand reader and statutory model fare-cap helper, independently reconstructs
flows, costs, accounting, sensitivities and calendar. Does not establish source truth.
"""
import sys,csv,json,math,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent; ROOT=OUT.parent; WORK=ROOT.parent.parent
LATEST=ROOT/'inputs/model_schedule/latest'
sys.path.insert(0,str(LATEST/'src'))
import network_model as m
D=m.Demand(); AS=m.load_assumptions()
def read(p): return list(csv.DictReader(p.open()))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,v): (OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
checks=[]
def check(n,ok,detail=''): checks.append(dict(check=n,status='PASS' if ok else 'FAIL',detail=str(detail)))
def near(a,b): return abs(float(a)-float(b))<.02
fixed=read(ROOT/'model_schedule/fixed_networks.csv'); freeze=json.loads((ROOT/'model_schedule/freeze.json').read_text()); baseline=read(ROOT/'economics/baseline_ledger.csv')
protected=json.loads((ROOT/'protected_tracked_files.json').read_text())
check('owner_436_protected_hashes',len(protected)==436 and all((WORK/p).is_file() and sha(WORK/p)==h for p,h in protected.items()),'Only named 436 paths; no context28 inventory')
manifest=json.loads((ROOT/'economics/manifest.json').read_text())
watched={Path(e['path']):e['sha256'] for e in manifest['inputs']}
watched.update({ROOT/'economics'/e['path']:e['sha256'] for e in manifest['outputs']})
schedule_before={p:sha(p) for p in (ROOT/'model_schedule').iterdir() if p.is_file()}
watched.update(schedule_before)
check('economics_manifest_hashes',all(p.is_file() and sha(p)==h for p,h in watched.items()))
for e in json.loads((ROOT/'model_schedule/replay_inputs_manifest.json').read_text())['files']:
 p=Path(e['local_path']); p=p if p.is_absolute() else ROOT/'inputs/model_schedule'/p
 data=p.read_bytes(); blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 check(('raw_snapshot_hash_' if e['commit']=='UNTRACKED_RAW_FROM_PRIOR_AUDIT' else 'pin_blob_')+e['path'],sha(p)==e['sha256'] and blob==(e.get('expected_git_blob') or e.get('git_blob',blob)) and (e['commit']==freeze['pin'] if '/latest/' in str(p) and e['commit']!='UNTRACKED_RAW_FROM_PRIOR_AUDIT' else True),e['status'])
check('exact_pin',freeze['pin']=='0b0fbcb742ea2e54e05b80a5b8e890200fd5daae')

def calc(net,A=None,scale=1,scen='base'):
 A=dict(A or AS[net['scenario']]); W=A['weeks_per_year']; rows=[r for r in fixed if r['network_id']==net['id']]
 # Aggregate physical pairs before assigning shared demand; no duplicate direct markets.
 groups=defaultdict(list)
 for r in rows: groups[tuple(sorted((r['origin'],r['destination'])))].append(r)
 local={}; total={}; fg={}; fares={}; freq={}; lengths={}
 for pair,rr in groups.items():
  a,b=pair; f=sum(int(r['frequency_each_direction_week']) for r in rr); freq[pair]=f; km=D.km(a,b);lengths[pair]=km
  fares[pair]=A['fare_fixed_rub']+A['fare_per_km_rub']*km
  comp=D.seg(a,b,scen)/(2*W)/(A['seats']*A['competitor_lf'])
  share=0 if km<A['transfer_min_km'] else (min(A['capture_competitive'],f/(f+comp)) if D.has_direct(a,b) and comp else (0 if D.has_direct(a,b) else A['capture_open']*(1-math.exp(-f/A['capture_freq_scale']))))
  local[pair]=D.get(a,b,scen)*scale/(2*W)*share
 transfers=[]
 if net['id'].startswith('OMS'):
  S=net['spokes']
  for i,x in enumerate(S):
   for y in S[i+1:]:
    km=D.km(x,y);px=tuple(sorted(('OMS',x)));py=tuple(sorted(('OMS',y)))
    if km<A['transfer_min_km'] or D.has_direct(x,y) or x in m.CLOSED or y in m.CLOSED or (lengths[px]+lengths[py])/km>A['transfer_max_circuity']:continue
    t=D.get(x,y,scen)*scale/(2*W)*A['capture_transfer']*(1-math.exp(-min(freq[px],freq[py])/A['capture_freq_scale']))
    transfers.append((px,py,km,t))
 load=dict(local)
 for x,y,km,t in transfers:load[x]+=t;load[y]+=t
 caps={p:min(1,freq[p]*A['seats']*A['lf_max']/v) if v else 1 for p,v in load.items()}
 local={p:v*caps[p] for p,v in local.items()};total=dict(local);trrev=defaultdict(float);od=0;trticket=0
 for x,y,km,t in transfers:
  t*=min(caps[x],caps[y]);total[x]+=t;total[y]+=t;od+=2*t*W
  ticket=2*t*(A['fare_fixed_rub']+A['fare_per_km_rub']*km)*A['transfer_fare_factor'];trticket+=ticket*W
  trrev[x]+=ticket*lengths[x]/(lengths[x]+lengths[y]);trrev[y]+=ticket*lengths[y]/(lengths[x]+lengths[y])
 rev=grant=Q=hours=legs=tonnes=0
 for pair,rr in groups.items():
  a,b=pair; f=freq[pair];km=lengths[pair];mg=min(local[pair],m.RW_FREQ.get(frozenset(pair),0)*A['seats']*A['rw_existing_lf'])
  for r in rr:
   rf=int(r['frequency_each_direction_week']);frac=rf/f
   # Pinned cap/subsidy helper reused, not independently a legal-price validation.
   lr,g=m.leg_with_subsidy(D,A,a,b,rf,local[pair]*frac,trrev[pair]*frac,2*mg*fares[pair]*frac)
   rev+=lr*W;grant+=g*W;Q+=2*mg*fares[pair]*frac*W
   bh=A['block_fixed_h']+km*(A['route_factor_south'] if D.south(a,b) else A['route_factor'])/A['block_speed_kmh']
   hours+=2*rf*bh;legs+=2*rf;tonnes+=2*rf*(bh*A['fuel_t_per_hour']+A['fuel_t_per_cycle'])*W
 seg=2*sum(total.values())*W; details={k:hours*W*A[k+'_rub_per_hour'] for k in ['mro','crew','navigation']}
 details.update(ground=legs*W*A['ground_rub_per_flight'],deicing=legs*W*A['deicing_rub_per_flight'],pax_cost=seg*A['pax_cost_rub'])
 gross=tonnes*A['fuel_rub_per_t'];credit=tonnes*A['fuel_compensation_rub_per_t'];cost=gross-credit+sum(details.values())
 return dict(revenue_net_rub_year=rev,route_grant_rub=grant,forgone_rw_rub=Q,ticket_before_forgone_rub=rev-grant+Q,net_ticket_rub=rev-grant,cost_rub_year=cost,contribution_rub_year=rev-cost,flights_week=legs,block_h_week=hours,fuel_tonnes=tonnes,gross_fuel_rub=gross,fuel_credit_rub=credit,net_fuel_rub=gross-credit,other_variable_rub=sum(details.values()),passenger_segments_year=seg,local_endpoint_od_year=2*sum(local.values())*W,transfer_od_year=od,transfer_ticket_before_cap_rub=trticket,**{k+'_rub':v for k,v in details.items()})
published=read(LATEST/'data/processed/network_routes.csv')
for net in freeze['networks']:
 if net['id']=='OMS_RAMP3_BASE':
  ramp=next(r for r in read(LATEST/'data/processed/fleet_ramp.csv') if r['hub']=='OMS' and r['scenario']=='base' and r['fleet_cap']=='3')
  check('ramp_published_composition',ramp['spokes'].split(';')==net['spokes'])
  _,raw=m.hub_network('OMS',D,AS['base'],'base',[],fixed_spokes=net['spokes'])
  check('ramp_frequency_small_pinned_replay',all(raw[0][r['destination']]['freq']==int(r['frequency_each_direction_week']) for r in fixed if r['network_id']==net['id']))
 else:
  rr=[r for r in fixed if r['network_id']==net['id']]
  pp=[r for r in published if r['scenario']==net['scenario'] and (r['variant']=='Хаб OMS' if net['id'].startswith('OMS') else r['variant'] in net['triangles'])]
  check(net['id']+'_published_frequencies',Counter((r['origin'],r['destination'],int(r['frequency_each_direction_week'])) for r in rr)==Counter((r['from'],r['to'],int(r['freq_week_each_way'])) for r in pp))
results={}
for net,b in zip(freeze['networks'],baseline):
 z=calc(net);results[net['id']]=z
 check(net['id']+'_independent_ledger',all(near(v,b[k]) for k,v in z.items()),{k:v-float(b[k]) for k,v in z.items() if not near(v,b[k])})
 check(net['id']+'_freeze',all(near(z[k],net[k]) for k in ('contribution_rub_year','revenue_net_rub_year','cost_rub_year')))
 rows=[r for r in fixed if r['network_id']==net['id']]
 check(net['id']+'_tonnes_from_export_blocks',near(z['fuel_tonnes'],sum(2*int(r['frequency_each_direction_week'])*(float(r['model_block_h_oneway'])*1.55+.20)*52 for r in rows)))
 for k in (0,3024,32930):
  stress=calc(net,dict(AS[net['scenario']],fuel_compensation_rub_per_t=k))
  check(net['id']+'_credit_only_'+str(k),near(stress['contribution_rub_year'],z['contribution_rub_year']+(k-32930)*z['fuel_tonnes']) and all(near(stress[key],z[key]) for key in ['passenger_segments_year','ticket_before_forgone_rub','other_variable_rub','fuel_tonnes','forgone_rw_rub']))
 for r in read(ROOT/'economics/fixed_network_sensitivities.csv'):
  if r['network_id']!=net['id']:continue
  s=float(r['s']);k=float(r['k_rub_t'])
  if r['case'].startswith('PURE'):v=z['contribution_rub_year']+(k-32930)*z['fuel_tonnes']+(s-1)*z['ticket_before_forgone_rub']
  elif r['case'].startswith('RETAINED'):v=calc(net,scale=s)['contribution_rub_year']
  else:v=z['contribution_rub_year']-z['route_grant_rub']
  check(net['id']+'_sensitivity_'+r['case']+'_'+str(k)+'_'+str(s),near(v,r['Fmax_rub_year']))
 for r in read(ROOT/'economics/breakeven_frontier.csv'):
  if r['network_id']!=net['id']:continue
  F=float(r['F_budget_axis_rub_year']);k=float(r['k_rub_t']);root=r['required_retained_model_od_fraction']
  if root:
   ok=z['contribution_rub_year']<F if root.startswith('UNREACHABLE') else near(calc(net,scale=float(root))['contribution_rub_year'],F)
   if not root.startswith('UNREACHABLE'):
    t=float(root);ok=ok and calc(net,scale=max(0,t-1e-5))['contribution_rub_year']<F and calc(net,scale=min(1,t+1e-5))['contribution_rub_year']>=F
  else:
   ok=near(z['contribution_rub_year']+(float(r['required_credit_rub_t'])-32930)*z['fuel_tonnes'],F) and near(z['contribution_rub_year']+(k-32930)*z['fuel_tonnes']+(float(r['required_receipts_or_fare_multiplier'])-1)*z['ticket_before_forgone_rub'],F)
  check(net['id']+'_frontier_'+str(k)+'_'+str(F)+'_'+bool(root).__str__(),ok)
 for r in read(ROOT/'economics/seasonality_cases.csv'):
  if r['network_id']!=net['id']:continue
  n=int(r['period_weeks'])
  if r['case']=='UNCHANGED_WEEKLY_PROFILE':v={key:val*n/52 for key,val in z.items() if key not in ('flights_week','block_h_week')}
  else:
   A=dict(AS['cautious_sub' if net['scenario'].endswith('_sub') else 'cautious']) if r['case'].startswith('CAUTIOUS') else dict(AS[net['scenario']],weeks_per_year=48)
   v=calc(net,A,scen='cautious' if r['case'].startswith('CAUTIOUS') else 'base')
  check(net['id']+'_season_numbers_'+r['case']+str(n),all(near(val,r[key]) for key,val in v.items()))
  if r['case']=='UNCHANGED_WEEKLY_PROFILE':check(net['id']+'_season_metadata_'+str(n),int(float(r['weeks']))==n,'Known finding F01: weeks52 vs period; *_year labels period totals')
for r in read(ROOT/'economics/network_comparison.csv'):
 h=results[r['hub']];d=results[r['direct']];delta=h['contribution_rub_year']-d['contribution_rub_year']+(float(r['k_rub_t'])-32930)*(h['fuel_tonnes']-d['fuel_tonnes'])
 check('comparison_'+r['hub']+r['direct']+r['k_rub_t'],near(delta,r['hub_minus_direct_F_switch_rub']))
check('admissions_zero',all(r['numeric_model_update']=='0' and r['additional_passengers']=='0' for r in read(ROOT/'economics/findings_admission.csv')))
# Calendar independently from timestamps, including cycle boundary and next-week connections.
fl=read(ROOT/'model_schedule/proposed_initial_flights.csv');dt=datetime.fromisoformat
zones={'OMS':'Asia/Omsk','MOW':'Europe/Moscow','GOJ':'Europe/Moscow','VOG':'Europe/Volgograd','IKT':'Asia/Irkutsk','NOZ':'Asia/Novokuznetsk','UFA':'Asia/Yekaterinburg'}
check('44_unique_flights',len(fl)==len({r['flight_id'] for r in fl})==44)
cnt=Counter((r['origin'],r['destination']) for r in fl)
check('ramp_frequencies',all(cnt[(r['origin'],r['destination'])]==cnt[(r['destination'],r['origin'])]==int(r['frequency_each_direction_week']) for r in fixed if r['network_id']=='OMS_RAMP3_BASE'))
check('UTC_local_IANA_duration_dayroll',all(dt(r['departure_utc']).astimezone(ZoneInfo(zones[r['origin']])).isoformat()==r['departure_local'] and dt(r['arrival_utc']).astimezone(ZoneInfo(zones[r['destination']])).isoformat()==r['arrival_local'] and (dt(r['arrival_utc'])-dt(r['departure_utc'])).total_seconds()/60==float(r['block_min']) and (dt(r['arrival_local']).date()-dt(r['departure_local']).date()).days==int(r['local_arrival_day_delta']) for r in fl))
highfails=0; rotation=read(ROOT/'model_schedule/rotation_checks.csv');rot={r['check_id']:r for r in rotation if r['check_id'].startswith('F')}
for tail in ('S1','S2'):
 fs=sorted([r for r in fl if r['tail_slot']==tail],key=lambda r:r['departure_utc']);ok=True
 for i,r in enumerate(fs):
  prev=fs[i-1]; dep=dt(r['departure_utc'])+(timedelta(days=7) if i==0 else timedelta());gap=(dep-dt(prev['arrival_utc'])).total_seconds()/60
  ok &= prev['destination']==r['origin'] and gap>=60
  highgap=gap-(float(prev['scenario_block_high_min'])-float(prev['block_min']));highfails+=highgap<60
  if i>0:ok &= near(gap,rot[r['flight_id']]['ground_gap_min']) and near(highgap,rot[r['flight_id']]['ground_gap_if_preceding_leg_high_min'])
 check('weekly_continuity_turns_'+tail,ok,'Airport codes only; actual MOW airport UNKNOWN')
check('nominal_high_resource',sum(float(r['block_min']) for r in fl)/60==136 and sum(float(r['scenario_block_high_min']) for r in fl)/60==161.5)
check('22_high_turn_failures',highfails==22,highfails)
cons=read(ROOT/'model_schedule/connection_checks.csv');found={}; passed=0
for a in fl:
 if a['destination']!='OMS':continue
 for dest in set(zones)-{'OMS',a['origin']}:
  candidates=[]
  for b in fl:
   if b['origin']!='OMS' or b['destination']!=dest:continue
   dep=dt(b['departure_utc'])
   while dep<dt(a['arrival_utc']):dep+=timedelta(days=7)
   candidates.append(((dep-dt(a['arrival_utc'])).total_seconds()/60,b['flight_id'],dep))
  wait,fid,dep=min(candidates);found[(a['flight_id'],dest)]=(wait,fid,dep);passed+=45<=wait<=240
check('110_nearest_weekly_connections',len(found)==len(cons)==110 and all(near(found[(r['inbound_id'],r['destination'])][0],r['wait_min']) and found[(r['inbound_id'],r['destination'])][1]==r['outbound_id'] and found[(r['inbound_id'],r['destination'])][2]==dt(r['departure_utc']) for r in cons))
check('15_screened_not_passengers',passed==15 and all(r['passengers_added']=='0' and r['mct_min']=='UNKNOWN' for r in cons))
check('inputs_unchanged_at_exit',all(sha(p)==h for p,h in watched.items()) and all(sha(WORK/p)==h for p,h in protected.items()))
with (OUT/'actual_checks.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['check','status','detail']);w.writeheader();w.writerows(checks)
fail=[c for c in checks if c['status']=='FAIL']
dump('validation.json',dict(verdict='CHANGES',checks_count=len(checks),failed_checks=fail,known_metadata_failures=20,unexpected_failures=[c for c in fail if '_season_metadata_' not in c['check']],operational_scenario_failures={'high_hours':161.5,'capacity_hours':140,'turn_failures':highfails},source_facts_verified_by_replay=False,scope='Independent formulas/flows/calendar; pinned Demand and fare-cap helper reused; no external research; no optimizer; no context28 inventory',protected_count=len(protected)))
dump('independent_results.json',results)
print(json.dumps({'checks':len(checks),'failed':len(fail),'unexpected':[c for c in fail if '_season_metadata_' not in c['check']]}))
