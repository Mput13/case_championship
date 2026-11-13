"""Independent acceptance: pure APIs only; writes restricted to this review directory."""
import sys, json, csv, hashlib, math, copy, calendar, traceback
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime,timedelta,timezone
R=Path(__file__).resolve().parent; P=R.parent; ROOT=P.parents[1]
sys.dont_write_bytecode=True;sys.path.insert(0,str(P/'economics'))
import core as C
E=C.Engine('independent-review-20261113'); T=C.templates(); results=[]
def rows(n):return C.read(P/'economics'/f'{n}.csv')
def near(a,b):assert abs(float(a)-float(b))<0.0002,(a,b)
def test(name,f):
 try:
  receipt=f();results.append(dict(name=name,status='PASS',receipt=receipt));print('PASS',name,json.dumps(receipt,ensure_ascii=False),flush=True)
 except Exception as e:
  results.append(dict(name=name,status='FAIL',error=repr(e)));print('FAIL',name,traceback.format_exc(),flush=True)
def preservation():
 b=json.loads((R/'baseline.json').read_text());assert all(C.sha(ROOT/p)==h for p,h in b.items())
 reg=C.js(P/'protected_files.json'); excluded=[p for p in reg if any(x in p.lower() for x in ['delegation','tasklog','task_log'])]
 assert all(C.sha(ROOT/p)==h for p,h in reg.items() if p not in excluded)
 manifest=C.js(P/'economics/input_manifest.json');assert all(C.sha(ROOT/p)==h for p,h in manifest['input_sha256'].items())
 return dict(completed_files=len(b),registry=len(reg),immutable=len(reg)-len(excluded),mutable_exclusions=excluded)
M=rows('programmes_monthly'); idx={(r['candidate'],int(r['month'][-2:]),r['scenario'],r['state']):r for r in M}
def scalars():
 for r in M:
  near(float(r['net_revenue'])-float(r['variable_cost']),r['known_subtotal_before_C_D_F'])
  k,w,z=[idx[r['candidate'],int(r['month'][-2:]),r['scenario'],s] for s in C.STATES]
  for col,a,b in [('old_change_W_minus_K',w,k),('new_R_minus_W',z,w),('total_R_minus_K',z,k)]:near(r[col],float(a['known_subtotal_before_C_D_F'])-float(b['known_subtotal_before_C_D_F']))
  assert r['through_journeys']=='0' and r['full_profit']==r['cash']==r['external_own_diversion']=='NULL'
  assert r['reserve_working']=='False'
 caut=[r for r in M if r['scenario']=='cautious' and r['state']=='REPLACE' and not r['candidate'].startswith('PRIMARY_')]
 assert len(caut)==5232 and all(float(r['new_R_minus_W'])<0 for r in caut)
 checked=0
 for a in rows('annual_results'):
  cid=a['candidate'];sc=a['scenario'];s=a['state']
  if cid not in T:continue
  if s=='THREE_STATE_DELTA':
   for acol,mcol in [('W_minus_K','old_change_W_minus_K'),('R_minus_W','new_R_minus_W'),('R_minus_K','total_R_minus_K')]:near(a[acol],sum(float(idx[cid,m,sc,'REPLACE'][mcol]) for m in range(1,13)))
  else:
   for acol,mcol in [('known_annual_subtotal','known_subtotal_before_C_D_F'),('net_revenue','net_revenue'),('variable_cost','variable_cost'),('departures','departures')]:near(a[acol],sum(float(idx[cid,m,sc,s][mcol]) for m in range(1,13)))
  checked+=1
 return dict(month_rows=len(M),annual_rows=checked,caut_population=len(caut),largest_caut_R_W=max(float(r['new_R_minus_W']) for r in caut))
def coverage():
 p=rows('pair_results');th=rows('pair_month_thresholds');seed={r['pair'] for r in p if r['in_seed25']=='True'}
 assert seed=={r['pair'] for r in C.read(P/'contract/pair_universe.csv')} and len(seed)==25
 assert len(p)==44 and len(th)==44*48
 for pair in seed:assert len({(r['physical_direction'],r['month'],r['scenario']) for r in th if r['pair']==pair})==48
 assert {r['pair'] for r in p if r['commercial']=='False' and r['in_seed25']=='True'}=={'CEK-SVX','SVX-TJM'}
 assert len(T)==436 and len(C.programme_input()['programmes'])==420
 return dict(seed=25,extra_template_pairs=19,thresholds=len(th),oldtop5=sum(r['old_top5']=='True' for r in p))
def reconstruction_reference():
 spec=C.programme_input(); out=[]
 for cohort in ['K1','K2','K3']:
  t=next(t for t in T.values() if t['cohort']==cohort and 'variant' in t)
  v=t['variant'];keep=copy.deepcopy(spec['resources'][cohort]['old_jobs']);changed=[]
  for j in keep:
   a=v['action_map'][j['id']]
   if a['action']=='REMOVE':continue
   j=copy.deepcopy(j);j['tail']=a['to_tail']
   for f in j['flights']:f.update(tail=a['to_tail'],dep=f['dep']+a['shift_minutes'],arr=f['arr']+a['shift_minutes'])
   changed.append(j)
  states={'KEEP':keep,'WITHOUT_NEW':changed,'REPLACE':changed+[copy.deepcopy(j) for oid in v['option_ids'] for j in spec['chain_options'][oid]['jobs']]}
  assert states==t['states']
  for s,m,sc in [('KEEP',2,'base'),('REPLACE',7,'cautious'),('WITHOUT_NEW',7,'base')]:
   z=E.score(states[s],t['tails'],m,sc);f=C.full_p06(z['cal'],t['tails'],m,sc)
   near(z['net_revenue'],f['revenue']);near(z['journeys'],f['journeys'])
   near(z['subtotal'],idx[t['id'],m,sc,s]['known_subtotal_before_C_D_F'])
   caps={x['flight_instance_id']:x['saleable_seats'] for x in f['bundle']['flights']};used=Counter();products={x['product_id']:x for x in f['bundle']['products']}
   for a in f['allocation']['allocations']:
    for leg in products[a['product_id']]['legs']:used[leg]+=a['carried']
   assert all(n<=caps[k]+1e-6 for k,n in used.items())
   cost=0
   for x in z['cal']['flights']:
    c=C.RE.costs(x['origin'],x['destination'],sc,x['block_minutes']/60);crew=float(C.RE.COSTS['HIST-crew_rub_per_hour']['base_point' if sc=='base' else 'cautious_point'])*x['block_minutes']/60
    near(c['fuel_cost'],c['fuel_t']*c['fuel_price']);cost+=c['fuel_cost']+c['other_cost']-crew
   near(cost,z['variable_cost']);out.append(dict(cohort=cohort,candidate=t['id'],state=s,month=m,scenario=sc,revenue=f['revenue'],departures=z['departures']))
 for cid in [next(cid for cid,t in T.items() if any(f['origin'] in ['DME','ZIA'] for j in t['states']['REPLACE'] for f in j['flights']))]:
  t=T[cid];z=E.score(t['states']['REPLACE'],t['tails'],2,'base',fare_scale=.9);f=C.full_p06(z['cal'],t['tails'],2,'base',fare_scale=.9);near(z['net_revenue'],f['revenue']);out.append(dict(MOW=cid,retail_rechoice=True))
 return out
finals=C.js(P/'economics/run_receipt.json')['finalists']
def calendars():
 out=[];mr=rows('three_finalists_monthly')
 for cid in finals:
  t=T[cid];st=C.annual_calendar({m:t['states']['REPLACE'] for m in range(1,13)},t['tails']);assert not st['conflicts']
  for m in range(1,13):
   cal=C.M.calendar_events(t['states']['REPLACE'],t['tails'],2027,m);ff=cal['flights'];assert not any(f['tail']=='R1' for f in ff)
   rr=[r for r in mr if r['candidate']==cid and r['month']==f'2027-{m:02}'];assert sum(int(r['physical_dated_departures']) for r in rr)==len(ff)
   for r in rr:
    own=[f for f in ff if (f['tail'],f['origin'],f['destination'])==(r['tail'],r['origin'],r['destination'])];assert len(own)==int(r['physical_dated_departures']);near(float(r['effective_physical_departures_week']),len(own)*7/calendar.monthrange(2027,m)[1])
   assert C.semantic_flights(ff)==C.semantic_flights(st['calendars'][m]['flights'])
  out.append(dict(candidate=cid,months=12,whole_year_events=len(st['events']),wrap='periodic fixture only'))
 return out

def delays():
 out=[]
 # Independently propagate all retained receipt examples, then stress the same trigger at90.
 for r in rows('delay_details'):
  t=T[r['candidate']];st=C.annual_calendar({m:t['states']['REPLACE'] for m in range(1,13)},t['tails']);seq=sorted([f for f in st['events'] if f['tail']==r['tail']],key=lambda f:f['departure_utc']);i=next(i for i,f in enumerate(seq) if f['flight_id']==r['trigger']);values={}
  for turn in [60,90]:
   ready=None;affected=0;maxprop=0
   for n,f in enumerate(seq[i:]):
    dep=C.M.dt(f['departure_utc']);arr=C.M.dt(f['arrival_utc'])
    if dep>C.M.dt(seq[i]['departure_utc'])+timedelta(days=14):break
    actual=max(dep+timedelta(minutes=int(r['hold_minutes']) if n==0 else 0),ready or dep);delay=(actual-dep).total_seconds()/60
    if n and delay<=1e-9:break
    if n:affected+=1;maxprop=max(maxprop,delay)
    ready=actual+(arr-dep)+timedelta(minutes=turn)
   values[turn]=(affected,maxprop)
  assert values[60][0]==int(r['propagated_flights']);near(values[60][1],r['buffer_needed_minutes'])
  out.append(dict(candidate=r['candidate'],trigger=r['trigger'],hold=r['hold_minutes'],kind=r['target_kind'],turn60=values[60],turn90=values[90]))
 (R/'delay_comparison.json').write_text(json.dumps(out,indent=2))
 changed=[r for r in out if r['turn60']!=r['turn90']]
 return dict(reconstructed=len(out),changed_at90=len(changed),examples=changed[:3],month_end_examples=[r for r in out if '12-27' in r['trigger']][:2],finding='90-minute delay branch missing from supplied outputs')
def inverse():
 r=next(r for r in rows('pair_month_thresholds') if r['status']=='DIRECTED_OD_WINNING_INTERVAL' and float(r['required_potential'])>1)
 t=T[r['candidate']];m=int(r['month'][-2:]);sc=r['scenario'];key=tuple(r['city_direction'].split('>'));target=E.score(t['states']['REPLACE'],t['tails'],m,sc)
 alts=[E.score(i['jobs'],i['tails'],m,sc) for i in C.native_menus()[t['cohort_key']]];alts=[a for a in alts if a['semantic']!=target['semantic']]
 # Independent lambda solver (bisection), rather than production piecewise inverse/kernel.
 def revenue(market,q):
  gg=market['groups'];lo=0.;hi=q/market['outside_weight']+1
  for _ in range(70):
   mid=(lo+hi)/2;total=market['outside_weight']*mid+sum(min(g['capacity'],g['weight']*mid) for g in gg)
   if total>q:hi=mid
   else:lo=mid
  return sum(min(g['capacity'],g['weight']*(lo+hi)/2)*g['net'] for g in gg)
 def val(z,q):return z['subtotal']-z['markets'][key]['revenue']+revenue(z['markets'][key],q)
 def diff(q):return val(target,q)-max(val(z,q) for z in alts)
 q=float(r['required_potential']);lo=q*.99;hi=q*1.01;assert diff(lo)<0<diff(hi)
 for _ in range(50):
  mid=(lo+hi)/2
  if diff(mid)>0:hi=mid
  else:lo=mid
 near((lo+hi)/2,q)
 pilot=[]
 for sc in ['base','cautious']:
  t=T['X_SVX_KJA'];z=E.score(t['states']['REPLACE'],t['tails'],2,sc);k=E.score(t['states']['KEEP'],t['tails'],2,sc)
  flights=[f for f in z['flights'] if f['pattern_id'].startswith('NEW-') and f['saleable_seats']];net=sum(C.RE.fare(f['origin_airport'],f['destination_airport'],sc)[1] for f in flights)
  need=k['subtotal']+z['variable_cost']-z['retained_revenue'];n=math.floor(need/net)+1;assert n==(69 if sc=='base' else 115);assert (n-1)*net<=need<n*net;pilot.append(dict(scenario=sc,integer=n))
 return dict(pair=r['city_direction'],month=m,scenario=sc,reported=q,independent_bisection=(lo+hi)/2,other_OD_fixed=True,p37=pilot)
def resource():
 rr=rows('resource_marginal');out={}
 for kind in ['FINITE_MENU_FRONTIER','ANNUAL_STITCHED_FINITE_FRONTIER']:
  rs=[r for r in rr if r['record_type']==kind];groups=defaultdict(list)
  for r in rs:groups[r['month'],r['scenario']].append(r);assert r['master_old_obligations']=='15' and r['full_marginal_profit']=='NULL' and r['background_flying_tails']=='0'
  for g in groups.values():
   g.sort(key=lambda x:int(x['working_budget']))
   for a,b in zip(g,g[1:]):
    delta=float(b['finite_menu_V_before_unknown_C_D_F'])-float(a['finite_menu_V_before_unknown_C_D_F']);assert delta>=-.0001;near(delta,b['paired_delta_before_C_D_lease_R1'])
  out[kind]=len(rs)
 nested=[r for r in rr if r['record_type']=='PROVIDED_EXACT_NESTED_PAIR'];assert len(nested)==192 and len({r['pair_id'] for r in nested})==8
 for r in nested:near(float(r['upper_known_subtotal'])-float(r['lower_known_subtotal']),r['paired_delta_before_C_D_lease_R1'])
 return out|dict(nested_pairs=8,nested_rows=192,scope='scalar identity and monotonicity; not independent frontier search')

def stitched_policy():
 out=[]
 for cohort in ['K1','K2','K3']:
  v=next(r for r in rows('season_vs_yearround') if r['cohort']==cohort and r['scenario']=='base');key=v['cohort_key'];plan=[r for r in rows('seasonal_plan') if r['cohort_key']==key and r['scenario']=='base'];menu=C.native_menus()[key];pol={}
  for m in range(1,13):
   rr=[r for r in plan if r['month']==f'2027-{m:02}'];label=rr[0]['selected'];item=next(i for i in menu if i['candidate']+'/'+i['state']==label);pol[m]=item['jobs']
  tails=menu[0]['tails'];actual=C.annual_calendar(pol,tails);assert not actual['conflicts']
  # Independent date-first selection, generated once per weekly job occurrence.
  independent=[];mon=datetime(2026,11,30,tzinfo=C.UTC);alljobs={C.digest(j):j for jj in pol.values() for j in jj}
  while mon<datetime(2028,2,1,tzinfo=C.UTC):
   for j in alljobs.values():
    first=mon+timedelta(minutes=min(f['dep'] for f in j['flights']))
    if C.digest(j) not in {C.digest(x) for x in pol[first.month]}:continue
    for f in j['flights']:
     d=mon+timedelta(minutes=f['dep']);a=mon+timedelta(minutes=f['arr'])
     if d.year==2027:independent.append((f['tail'],f['origin'],f['destination'],d.isoformat(),a.isoformat()))
   mon+=timedelta(days=7)
  delivered=[(f['tail'],f['origin'],f['destination'],f['departure_utc'],f['arrival_utc']) for m in range(1,13) for f in actual['calendars'][m]['flights']]
  assert sorted(independent)==sorted(delivered)
  zs=[C.score_calendar(actual['calendars'][m],tails,2027,m,'base') for m in range(1,13)];near(sum(z['subtotal'] for z in zs),v['stitched_seasonal_known_subtotal'])
  out.append(dict(cohort=cohort,annual=sum(z['subtotal'] for z in zs),checked_seams='all12 including Jan/Dec and September deterministically',flights=len(independent)))
 return out

def through_and_peaks():
 t=T['X_GOJ_KJA_F'];cal=E.calendar(t['states']['REPLACE'],t['tails'],7);full=C.full_p06(cal,t['tails'],7,'base',through=True);products={p['product_id']:p for p in full['bundle']['products']};used=Counter();rev=0
 for a in full['allocation']['allocations']:
  p=products[a['product_id']]
  for leg in p['legs']:used[leg]+=a['carried']
  if a['owner']=='RW':rev+=a['carried']*p['net_fare']
 caps={f['flight_instance_id']:f['saleable_seats'] for f in full['bundle']['flights']};assert all(q<=caps[k]+1e-6 for k,q in used.items());near(rev,full['revenue']);assert full['through_products']>0
 for m in [1,7]:
  q=C.potential('SVX','KJA',2027,m,'base');weights={f'2027-{m:02}-{d:02}':1.5 if d<=10 else .5 for d in range(1,calendar.monthrange(2027,m)[1]+1)};near(sum(C.M.pool_days(q,2027,m,weights).values()),q)
 return dict(through_products=full['through_products'],fare_once=True,physical_capacity_checked=True,monthly_peak_pool_conserved=True)

def nested_values():
 spec=C.programme_input();byid={p['id']:p for p in spec['programmes']};out=[]
 for pair in spec['nested_allocations']['pairs']:
  lo=next(v for v in byid[pair['lower_programme']]['variants'] if v['cohort']=='K2');hi=pair['upper_variant'];assert lo['action_map']==hi['action_map']
  vals=[]
  for v in [lo,hi]:
   states=C.restore_variant(v,spec);tails=C.M.resources(v['initial_positions']);vals.append(E.score(states['REPLACE'],tails,7,'cautious')['subtotal'])
  row=next(r for r in rows('resource_marginal') if r['record_type']=='PROVIDED_EXACT_NESTED_PAIR' and r['pair_id']==pair['id'] and r['month']=='2027-07' and r['scenario']=='cautious');near(vals[1]-vals[0],row['paired_delta_before_C_D_lease_R1']);out.append(dict(pair=pair['id'],delta=vals[1]-vals[0]))
 return out

for n,f in [('preservation_before',preservation),('coverage',coverage),('all_scalar_month_annual_identities',scalars),('independent_reconstruction_full_P06',reconstruction_reference),('36_finalist_calendars',calendars),('delay_recurrence_60_and_90',delays),('inverse_bisection_and_integer_BEP',inverse),('resource_scalar_frontiers',resource),('whole_job_stitched_annual',stitched_policy),('through_and_peak_conservation',through_and_peaks),('all8_nested_recalculation_July_cautious',nested_values),('preservation_after',preservation)]:test(n,f)
(R/'validation.json').write_text(json.dumps(dict(verdict='CHANGES',execution_checks=results,all_executed_checks_pass=all(r['status']=='PASS' for r in results),acceptance_complete=False,reason='Missing delivered turn90 delay stress; see findings.csv. PASS is limited to named tests; not source truth or dispatch acceptance.'),ensure_ascii=False,indent=2)+'\n')
