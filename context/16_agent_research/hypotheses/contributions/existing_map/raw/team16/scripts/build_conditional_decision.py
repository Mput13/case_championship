#!/usr/bin/env python3
"""Bounded route/frequency search and break-even gates; frozen inputs, stdlib only."""
from __future__ import annotations
import ast,collections,copy,csv,hashlib,itertools,json,math,subprocess,sys
from pathlib import Path
import build_team_comparison as old
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'context/16_conditional_decision';M=OUT/'model'
P=json.loads((OUT/'assumptions.json').read_text())
def csvread(p):
 with p.open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
def save(name,rows):
 rows=list(rows)
 if not rows:return
 with (M/name).open('w',encoding='utf-8',newline='')as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n');w.writeheader();w.writerows(rows)
def js(name,d):(M/name).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def val(r):return r['contribution_before_base_fleet_opportunity']
def green(m,a,b):return m.distance(a,b)*(P['south_detour'] if {a,b}&set(P['south_airports'])else 1)<=P['green_km']

def setup():
 m=old.Model();m.cfg.update(P['resource']);m.make_networks();original=copy.deepcopy(m.markets)
 # Existing team coordinate dictionary is parsed, not executed (dist.py prints tables on import).
 a=next(n.value for n in ast.parse((ROOT/'tools/dist.py').read_text()).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='A'for t in n.targets));coords=ast.literal_eval(a)
 aliases={'MCX':'Махачкала','KGD':'Калининград','REN':'Оренбург','BAX':'Барнаул','IKT':'Иркутск','VVO':'Владивосток','KHV':'Хабаровск'}
 for i,n in aliases.items():
  la,lo=coords[n];m.geo[i]={'iata':i,'lat':la,'lon':lo}
 for a,b in itertools.combinations(sorted(m.geo),2):m.market(a,b)
 for k,r in m.markets.items():
  a,b=k.split('-');r.update(m.band_values(a,b))
 # Stage12 dated inventory was filtered to its own route set. Add the fresh primary GOJ departures.
 for row in csvread(OUT/'research/goj_svx_own_calendar.csv'):
  m.rw[(row['origin'],row['destination'])]+=int(row['assumed_seats_from_RW_configuration'])
 for k,r in m.markets.items():
  a,b=k.split('-')
  if m.rw.get((a,b),0)>0 or m.rw.get((b,a),0)>0:
   for sc in ['base','cautious']:
    r['cannibal_'+sc]=P['known_incumbent_migration'][sc]
 for sc,p in m.scenarios.items():
  for g in ['open','competitive','uncertain']:p['capture_'+g]=P['local_peak'][sc]
 return m,original

def evaluation(m,n,sc,*,demand=1.,yield_factor=1.,cost=1.,migration=1.,transfer=1.,city=None,city_factor=1.,detail=False):
 # Scale the foregone incumbent yield too: a common yield scenario must not freeze old RW revenue.
 p=m.scenarios[sc];orig=p['old_RW_fare_ratio'];p['old_RW_fare_ratio']=orig*yield_factor
 try:
  r,ss,cc=m.evaluate(n,sc,demand_scale=demand,fare_scale=yield_factor,cost_scale=cost,migration_scale=migration,
      transfer_scale=transfer,market_scales={k:city_factor for k in m.markets if city and city in k.split('-')},detail=detail)
  for key in ['sold_journeys','transfer_journeys','local_journeys','segment_pax','gross_revenue','foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable','old_RW_segment_pax','migrated_RW_direct','migrated_RW_unverified_connecting','migrated_RW_total','net_new_journeys']:
   r.setdefault(key,0.)
  return r,ss,cc
 finally:p['old_RW_fare_ratio']=orig

def direct(m,name,jobs):
 # Every task starts and ends at its existing base. No unpriced ferry or new base.
 tasks=[]
 for index,j in enumerate(jobs):
  f=j['frequency'];route=j['route'];days=[1,3,5][:f]if len(route)==3 else {1:[1,4],2:[1,2,4,5],3:[1,2,3,4,5,6]}[f]
  for k,d in enumerate(days):
   r=route if len(route)==3 or k%2==0 else route[::-1]
   length=sum(m.block(a,b)for a,b in zip(r,r[1:]));span=length+(len(r)-2)*m.cfg['turn_minutes']
   tasks.append(dict(base=r[0],day=d,route=r,minutes=length,span=span,job=index,flexible=(len(route)==3 and f==1)))
 # Spread one-weekly rotations across the week before allocating fixed-base tails.
 for base in sorted({t['base']for t in tasks}):
  load=collections.Counter()
  for t in tasks:
   if t['base']==base and not t['flexible']:load[t['day']]+=t['minutes']
  for t in sorted([t for t in tasks if t['base']==base and t['flexible']],key=lambda t:(-t['minutes'],t['route'])):
   t['day']=min(range(1,m.cfg['work_days']+1),key=lambda d:(load[d],d));load[t['day']]+=t['minutes']
 bases=sorted({t['base']for t in tasks});chosen=None
 for total in range(1,m.cfg['active_aircraft']+1):
  for counts in itertools.product(range(1,total+1),repeat=len(bases)):
   if sum(counts)!=total:continue
   allocations=dict(zip(bases,counts));plan=[];good=True
   for base in bases:
    for day in range(1,7):
     bins=[[]for _ in range(allocations[base])]
     for t in sorted([t for t in tasks if t['base']==base and t['day']==day],key=lambda t:(-t['minutes'],t['route'])):
      fit=[]
      for i,bb in enumerate(bins):
       bh=sum(z['minutes']for z in bb)+t['minutes'];span=sum(z['span']for z in bb)+t['span']+len(bb)*m.cfg['turn_minutes']
       if bh<=m.cfg['planning_cap_block_h']*60 and span<=m.cfg['span_cap_h']*60:fit.append((bh,i))
      if not fit:good=False;break
      bins[min(fit)[1]].append(t)
     if not good:break
     for i,bb in enumerate(bins):
      plan.extend((base,day,i,t)for t in bb)
    if not good:break
   if good:chosen=plan;break
  if chosen is not None:break
 if not tasks:chosen=[]
 if chosen is None:return None
 legs=[];starts={}
 for base,day,i,t in chosen:
  tail=f'{base}{i+1}';k=(day,tail);clock=starts.get(k,300)
  for a,b in zip(t['route'],t['route'][1:]):clock=m.add_leg(legs,name,day,tail,a,b,clock,m.cfg)
  starts[k]=clock
 n=dict(name=name,hub=None,kind='direct',frequency='selected',legs=legs,cfg=m.cfg,jobs=jobs)
 n['itineraries']=m.itineraries(n);return n

def hub(m,h,leaves,freq,name):
 # Two orientations give return transfers on different dates; f=1 is spokes-only within this week.
 k=len(leaves)//2;aa,bb=m.best_partition(h,leaves,k);legs=[]
 for day in range(1,freq+1):
  a,b=(aa,bb)if day%2 else(bb,aa)
  best=None
  for perm in itertools.permutations(range(k)):
   bad=0;peak=0
   for i,j in enumerate(perm):
    am=m.block(h,a[i])+m.block(a[i],h);pm=m.block(h,b[j])+m.block(b[j],h)
    start=720-am-m.cfg['turn_minutes'];end=720+m.cfg['bank_wait_minutes']+pm+m.cfg['turn_minutes']
    bad+=am+pm>m.cfg['planning_cap_block_h']*60 or end-start>m.cfg['span_cap_h']*60;peak=max(peak,am+pm)
   option=(bad,peak,perm)
   if best is None or option<best:best=option
  bad,_,perm=best;nexttail=k
  for i,j in enumerate(perm):
   first=f'H{i+1}';second=first;am=m.block(h,a[i])+m.block(a[i],h);pm=m.block(h,b[j])+m.block(b[j],h)
   if am+pm>m.cfg['planning_cap_block_h']*60 or am+pm+2*m.cfg['turn_minutes']+m.cfg['bank_wait_minutes']>m.cfg['span_cap_h']*60:nexttail+=1;second=f'H{nexttail}'
   clock=m.add_leg(legs,name,day,first,h,a[i],720-am-m.cfg['turn_minutes'],m.cfg);m.add_leg(legs,name,day,first,a[i],h,clock,m.cfg)
   clock=m.add_leg(legs,name,day,second,h,b[j],720+m.cfg['bank_wait_minutes'],m.cfg);m.add_leg(legs,name,day,second,b[j],h,clock,m.cfg)
 n=dict(name=name,hub=h,kind='hub',frequency=freq,legs=legs,cfg=m.cfg,leaves=leaves)
 n['itineraries']=m.itineraries(n)
 # A one-day bank cannot be sold as a two-way weekly connecting product.
 n['itineraries']={key:its for key,its in n['itineraries'].items()if not its[0]['transfer']or (key[::-1]in n['itineraries']and n['itineraries'][key[::-1]][0]['transfer'])}
 return n

def metric(m,n,sc,**kw):
 r,_,_=evaluation(m,n,sc,**kw);a,_=m.audit(n)
 r.update(active_peak=a['active_peak'],active_allocated=len({l['aircraft']for l in n['legs']}),range_screen_pass=all(green(m,l['origin'],l['destination'])for l in n['legs']),
          algebraic_resource_pass=a['feasible'],physical_pairs=len({old.pair(l['origin'],l['destination'])for l in n['legs']}),
          feasibility='CONDITIONAL: crew/slots/payload/TO/available aircraft and protected ticket UNKNOWN')
 return r

def independent(m,selected,summary,sales,caps):
 tests={};ids={l['id']:l for n in selected.values()for l in n['legs']}
 for r in summary:
  key=(r['network'],r['scenario']);ss=[s for s in sales if(s['network'],s['scenario'])==key];cc=[s for s in caps if(s['network'],s['scenario'])==key]
  for field in ['sold_journeys','transfer_journeys','segment_pax','gross_revenue','incremental_revenue']:
   assert math.isclose(r[field],sum(s[field]for s in ss),abs_tol=1e-5)
  used=collections.Counter()
  for s in ss:
   ii=s['flight_ids'].split(';');assert len(ii)==(2 if s['transfer']else 1)
   assert math.isclose(s['gross_revenue'],s['sold_journeys']*s['effective_fare'],abs_tol=1e-5)
   for i in ii:used[i]+=s['sold_journeys']
  for c in cc:assert abs(used[c['id']]-c['sold_segment_pax'])<1e-5 and used[c['id']]<=100+1e-5
  assert abs(val(r)-r['incremental_revenue']+r['incremental_operating_cost'])<1e-5
 tests['independent_sales_two_seats_one_fare_cost_reconciliation']=True
 for name,n in selected.items():
  if name.startswith('B0'):continue
  a,_=m.audit(n);assert a['feasible'] and len({l['aircraft']for l in n['legs']})<=m.cfg['active_aircraft'] and all(green(m,l['origin'],l['destination'])for l in n['legs'])
  for tail in {l['aircraft']for l in n['legs']}:
   rr=sorted([l for l in n['legs']if l['aircraft']==tail],key=lambda l:l['departure_utc_minute'])
   assert rr[0]['origin']==rr[-1]['destination']
   for a,b in zip(rr,rr[1:]):assert a['destination']==b['origin']and a['arrival_utc_minute']+45<=b['departure_utc_minute']
 tests['independent_closed_chains_range_turn_and_resource']=True
 for name,n in selected.items():
  for a,b in n['itineraries']:assert m.market(a,b)is m.markets[old.pair(a,b)]
 tests['canonical_shared_OD_for_all_alternatives']=True
 assert len(m.networks['B0']['legs'])==72;tests['B0_preserved_not_optimized_comparator']=True
 assert val(evaluation(m,selected['NO_LAUNCH'],'base')[0])==0;tests['no_launch_zero_incremental']=True
 base=json.loads((OUT/'prior_tree_manifest.json').read_text());changed=[]
 for path,sha in base['blobs'].items():
  q=ROOT/path;actual=subprocess.check_output(['git','hash-object',str(q)],text=True).strip()
  if actual!=sha:
   prior=subprocess.check_output(['git','show',base['base_commit']+':'+path],cwd=ROOT)
   assert path=='README.md'and q.read_bytes().startswith(prior);changed.append(path)
 tests['all_prior_394_files_preserved_except_append_only_index']=True
 return tests

def main():
 M.mkdir(parents=True,exist_ok=True);m,original=setup();destinations=sorted(set(r['iata']for r in csvread(ROOT/'data/processed/longlist.csv'))|{'ARH','MMK','NJC'})
 jobs=[];excluded=[]
 for base in ['ZIA','SVX']:
  valid=[]
  for dst in destinations:
   if not green(m,base,dst)or m.distance(base,dst)<P['direct_min_km']:
    excluded.append(dict(base=base,destination=dst,km=m.distance(base,dst),reason='outside green2300/1.20south'if not green(m,base,dst)else 'under500km ground-advantage scenario screen'));continue
   valid.append(dst)
   for f in P['frequencies']:jobs.append(dict(base=base,route=[base,dst,base],frequency=f))
  for a,b in itertools.combinations(valid,2):
   if green(m,a,b)and m.distance(a,b)>=P['direct_min_km']:
    for f in P['frequencies']:jobs.append(dict(base=base,route=[base,a,b,base],frequency=f))
 candidates=[];dnets=[]
 for i,j in enumerate(jobs):
  n=direct(m,f'D{i:03d}',[j])
  if n is None:continue
  dnets.append(n)
  for sc in ['base','cautious']:
   r=metric(m,n,sc);r.update(route='-'.join(j['route']),frequency=j['frequency'],search_scope='independent existing-base closed cycle');candidates.append(r)
 save('direct_candidates.csv',candidates);save('direct_screen_exclusions.csv',excluded)
 marginal=[]
 for sc in ['base','cautious']:
  last=0
  for r in sorted([r for r in candidates if r['scenario']==sc and r['route']=='SVX-MRV-SVX'],key=lambda r:r['frequency']):
   marginal.append(dict(scenario=sc,frequency=r['frequency'],contribution=val(r),increment_vs_previous_frequency=val(r)-last,sold_journeys=r['sold_journeys'],note='No positive increment -> do not add frequency; baseline common OD and fares'))
   last=val(r)
 save('pilot_frequency_margins.csv',marginal)
 selected={'NO_LAUNCH':direct(m,'NO_LAUNCH',[]),'B0_reference':copy.deepcopy(m.networks['B0'])};selected['B0_reference']['name']='B0_reference'
 for l in selected['B0_reference']['legs']:l['network']='B0_reference'
 best=max((r for r in candidates if r['scenario']=='base'),key=val);probe=copy.deepcopy(next(n for n in dnets if n['name']==best['network']));probe['original_search_id']=probe['name'];selected['D_pilot']=probe
 def select_direct(minpairs,per_pair=False):
  chosen=[];seen=set();current=direct(m,'search',[]);currentval=0
  for iteration in range(8):
   proposals=[]
   for i,j in enumerate(jobs):
    if i in seen:continue
    # Keep at most one frequency choice of each circuit.
    if any(j['route']==a['route']for a in chosen):continue
    n=direct(m,'search',chosen+[j])
    if n is None:continue
    r=metric(m,n,'base');gain=val(r)-currentval
    newpairs=r['physical_pairs']-len({old.pair(l['origin'],l['destination'])for l in current['legs']})
    score=gain/max(1,newpairs)if per_pair else gain
    proposals.append((score,-i,n,j,r))
   if not proposals:break
   score,ni,n,j,r=max(proposals,key=lambda q:(q[0],q[1]));gain=val(r)-currentval
   if gain<=0 and currentval==0 and minpairs==0:break
   if gain<=0 and r['physical_pairs']>=minpairs and len(chosen)>0 and len({old.pair(l['origin'],l['destination'])for l in current['legs']})>=minpairs:break
   chosen.append(j);seen.add(-ni);current=n;currentval=val(r)
   if r['physical_pairs']>=minpairs and minpairs>0:break
  return direct(m,'D_improved'if minpairs==0 else'D_case8',chosen)
 selected['D_improved']=select_direct(0)
 designs=[select_direct(8),select_direct(8,per_pair=True)]
 searchaudit=[dict(method='absolute_gain'if i==0 else'gain_per_new_pair',pairs=metric(m,n,'base')['physical_pairs'],contribution=val(metric(m,n,'base')))for i,n in enumerate(designs)]
 current=max(designs,key=lambda n:val(metric(m,n,'base')))
 # Two bounded local passes: remove one circuit or replace it, preserving 8..12 physical pairs.
 for step in range(2):
  best=current;bestv=val(metric(m,current,'base'));jj=current['jobs']
  for remove in range(len(jj)):
   rest=jj[:remove]+jj[remove+1:]
   for replacement in [None]+jobs:
    if replacement is not None and any(replacement['route']==x['route']for x in rest):continue
    trial=direct(m,'D_case8',rest+([replacement]if replacement else[]))
    if trial is None:continue
    r=metric(m,trial,'base')
    if 8<=r['physical_pairs']<=12 and val(r)>bestv+1e-6:best,bestv=trial,val(r)
  searchaudit.append(dict(method=f'local_single_circuit_pass{step+1}',pairs=metric(m,best,'base')['physical_pairs'],contribution=bestv))
  if best is current:break
  current=best
 selected['D_case8']=current
 save('direct_design_search.csv',searchaudit)
 hr=[];hnets={}
 for h in P['hub_cities']:
  leaves=sorted({l['destination']for l in m.networks['H_'+h+'_compact']['legs']if l['origin']==h})
  for size in P['hub_rays']:
   for combo in itertools.combinations(leaves,size):
    if not all(green(m,h,d)for d in combo):continue
    for f in P['frequencies']:
     name=f'H_{h}_{size}_{f}_'+'.'.join(combo);n=hub(m,h,list(combo),f,name);a,_=m.audit(n)
     if not a['feasible']:continue
     hnets[name]=n
     for sc in ['base','cautious']:
      r=metric(m,n,sc);r.update(city=h,rays=size,frequency=f,leaves=';'.join(combo));hr.append(r)
 save('hub_candidates.csv',hr)
 for h in P['hub_cities']:
  for rays in [4,8]:
   # Freeze selection by base scenario; evaluate the same network cautiously.
   rr=[r for r in hr if r['scenario']=='base'and r['city']==h and r['rays']==rays and(r['transfer_journeys']>0)]
   best=max(rr,key=val);selected[f'H_{h}_{rays}']=copy.deepcopy(hnets[best['network']])
 # One weekly service on all eight spokes has no reciprocal in-week bank here.
 for h in ['GOJ','UFA']:
  rr=[r for r in hr if r['scenario']=='base'and r['city']==h and r['rays']==8 and r['frequency']==1]
  basis=hnets[max(rr,key=val)['network']]
  radial=direct(m,f'S_{h}_8_1',[dict(base=h,route=[h,d,h],frequency=1)for d in basis['leaves']])
  radial.update(hub=h,kind='radial_base_no_transfer',frequency=1,leaves=basis['leaves'])
  selected[f'S_{h}_8_1']=radial
 # Stable selected IDs and fresh globally unique dated leg IDs.
 for name,n in selected.items():
  remap={l['id']:f'{name}_{i:03d}'for i,l in enumerate(n['legs'])}
  for l in n['legs']:l['network']=name;l['id']=remap[l['id']]
  for its in n['itineraries'].values():
   for it in its:it['legs']=[remap[x]for x in it['legs']]
  n['name']=name
 summary=[];sales=[];caps=[];routes=[];resources=[]
 for name,n in selected.items():
  a,_=m.audit(n);a['network']=name
  bases=sorted({j['base']for j in n.get('jobs',[])})if n.get('jobs')is not None else [n['hub']]if n['hub']else ['ZIA','SVX']
  a.update(active_allocated=len({l['aircraft']for l in n['legs']}),operating_bases=';'.join(bases),reserve_assumed_location=n['hub']or'SVX',uncovered_bases_if_simultaneous_AOG=max(0,len(bases)-1),reserve_note='One reserve not instantly at bothZIA/SVX; no ferry recovery/compensation inferred')
  resources.append(a)
  for key in sorted({old.pair(l['origin'],l['destination'])for l in n['legs']}):
   ff=[l for l in n['legs']if old.pair(l['origin'],l['destination'])==key];x,y=key.split('-');routes.append(dict(network=name,pair=key,departures_each_direction=sum(l['origin']==x for l in ff),reverse_departures=sum(l['origin']==y for l in ff),green=green(m,x,y),block_A_B=m.block(x,y),block_B_A=m.block(y,x),OD_method='common scenario distance bands, never airport pax or seats'))
  for sc in ['base','cautious']:
   r,ss,cc=evaluation(m,n,sc,detail=True);a=metric(m,n,sc);r.update({k:a[k]for k in ['active_peak','active_allocated','range_screen_pass','algebraic_resource_pass','physical_pairs','feasibility']});summary.append(r);sales+=ss;caps+=cc
 save('comparison.csv',summary);save('routes.csv',routes);save('flights.csv',[l for n in selected.values()for l in n['legs']]);save('sales.csv',sales);save('capacity.csv',caps);save('resources.csv',resources)
 # A relaxation ignores packaging/time resources and maximizes each nonstop OD independently.
 relaxed=[]
 for a,b in sorted({tuple(sorted((l['origin'],l['destination'])))for n in dnets for l in n['legs']}):
  for sc in ['base','cautious']:
   maxf=int(240*60/(m.block(a,b)+m.block(b,a)));best=0;bestf=0
   for f in range(1,maxf+1):
    legs=[]
    for i in range(f):
     clock=m.add_leg(legs,'relax',1,str(i),a,b,300,m.cfg);m.add_leg(legs,'relax',1,str(i),b,a,clock,m.cfg)
    n=dict(name='relax',hub=None,kind='direct',frequency='RELAXED_NO_TIME_LIMIT',legs=legs,cfg=m.cfg);n['itineraries']=m.itineraries(n);v=val(evaluation(m,n,sc)[0])
    if v>best:best=v;bestf=f
   relaxed.append(dict(pair=old.pair(a,b),scenario=sc,frequency_relaxation_max=maxf,best_frequency_including_zero=bestf,upper_bound_contribution=best,interpretation='independent pair relaxation, ignores packing; shared canonical OD, symmetric f; not all possible global route markets'))
 save('direct_relaxation_bound.csv',relaxed)
 # Sensitivity changes identical canonical OD or cost/yield rules across alternatives.
 sens=[];grids=P['sensitivity']
 for sc in ['base','cautious']:
  for par,grid in grids.items():
   for x in grid:
    kw={'city':par[5:],'city_factor':x}if par.startswith('city_')else{par:x}
    for name,n in selected.items():
     if name=='B0_reference':continue
     r=metric(m,n,sc,**kw);sens.append(dict(network=name,scenario=sc,parameter=par,value=x,contribution=val(r),sold=r['sold_journeys'],transfers=r['transfer_journeys']))
 save('sensitivity.csv',sens)
 switches=[]
 for sc in ['base','cautious']:
  for par,grid in grids.items():
   for x in grid:
    rr=[r for r in sens if r['scenario']==sc and r['parameter']==par and r['value']==x]
    full=[r for r in rr if r['network'] in ['D_case8','H_GOJ_8','H_UFA_8','H_CEK_8','H_TJM_8']]
    best=max(full,key=lambda r:r['contribution']);hubbest=max([r for r in full if r['network'].startswith('H_')],key=lambda r:r['contribution'])
    allbest=max(rr,key=lambda r:r['contribution'])
    switches.append(dict(scenario=sc,parameter=par,value=x,best_hub8=hubbest['network'],best_full8=best['network'],best_full8_contribution=best['contribution'],best_with_no_launch=allbest['network'],best_with_no_launch_contribution=allbest['contribution'],interpretation='Fixed networks selected in base; one-at-a-time shared input stress; not probability or calibrated bounds'))
 save('switch_summary.csv',switches)
 budgets=[]
 for sc in ['base','cautious']:
  directref=next(r for r in summary if r['network']=='D_case8'and r['scenario']==sc)
  for r in summary:
   if r['scenario']==sc and r['network'].startswith(('H_','S_')):
    budgets.append(dict(network=r['network'],scenario=sc,max_extra_base_before_tie_with_Dcase8=val(r)-val(directref),max_base_before_zero=val(r),fixed_costs_actual='UNKNOWN',interpretation='Signed budget; negative means needs support/cost or demand change even with free new base; fixed fleet and opportunity excluded'))
 save('base_budgets.csv',budgets)
 usedkeys={old.pair(a,b)for n in selected.values()for a,b in n['itineraries']}
 save('markets.csv',[dict(pair=k,demand_base=m.markets[k]['demand_base'],demand_cautious=m.markets[k]['demand_cautious'],net_fare_base=m.markets[k]['fare_base'],net_fare_cautious=m.markets[k]['fare_cautious'],cannibal_base=m.markets[k]['cannibal_base'],cannibal_cautious=m.markets[k]['cannibal_cautious'],published_RW_overlap=any(m.rw.get((a,b),0)>0 for a,b in [tuple(k.split('-')),tuple(k.split('-')[::-1])]),observed_OD=None,observed_net_fare=None,method=m.markets[k]['range_basis'],unit='endpoint journeys/week/direction; RUB/net whole one-way journey',source='stage15 common band experiment; coordinates from stage11 and tools/dist.py; NOT observed demand')for k in sorted(usedkeys)])
 thresholds=[]
 for name,n in selected.items():
  if name in ['NO_LAUNCH','D_improved','B0_reference']:continue
  for sc in ['base','cautious']:
   r=next(r for r in summary if r['network']==name and r['scenario']==sc);peak=r['active_allocated']
   for basecost,fixed in [(0,0),(0,P['fixed_per_allocated_working_or_reserve_tail_week']),(P['new_base_week_scenario'] if n['hub']else 0,P['fixed_per_allocated_working_or_reserve_tail_week'])]:
    fixed_total=fixed*(peak+1)+basecost;initial=val(r)-fixed_total
    for par in ['yield_factor','demand','cost']:
     lo,hi=(0.1,5.)if par=='cost'else(0.,16.)
     def gap(x):return val(evaluation(m,n,sc,**{par:x})[0])-fixed_total
     if gap(lo)*gap(hi)>0:root=None;result=None
     else:
      for _ in range(35):
       mid=(lo+hi)/2
       if gap(lo)*gap(mid)<=0:hi=mid
       else:lo=mid
      root=(lo+hi)/2;result=evaluation(m,n,sc,**{par:root})[0]
     thresholds.append(dict(network=name,scenario=sc,parameter=par,breakeven_multiplier=root,pax_at_threshold=None if result is None else result['sold_journeys'],transfer_at_threshold=None if result is None else result['transfer_journeys'],fixed_per_allocated_tail_week=fixed,tails_charged=peak+1,new_base_per_week=basecost,contribution_at_baseline_after_fixed=initial,status='NO_ROOT_IN_TESTED_RANGE'if root is None else'BISECTION_CONDITIONAL_NO_DEMAND_PRICE_ELASTICITY'))
 save('breakeven.csv',thresholds)
 # Passenger booking gate for the one-route pilot; each directional flight must earn its cost.
 pilot=selected['D_pilot'];gate=[]
 for sc in ['base','cautious']:
  r=next(r for r in summary if r['network']=='D_pilot'and r['scenario']==sc)
  for a,b in pilot['itineraries']:
   its=pilot['itineraries'][(a,b)];market=m.markets[old.pair(a,b)];price=market['fare_'+sc];p=m.scenarios[sc];can=market['cannibal_'+sc]
   legcost=sum(m.flight_cost(l,sc)for l in pilot['legs']if l['origin']==a and l['destination']==b)
   # Conservative gate gives no uncertain cost credit for displaced old sales.
   margin=price*(1-can*p['old_RW_fare_ratio'])-p['pax_cost']
   gate.append(dict(origin=a,destination=b,scenario=sc,departures=len(its),net_fare_assumption=price,can_assumption=can,net_new_margin_per_booked=margin,flight_cost=legcost,
     required_paid_pax_before_fixed=legcost/margin if margin>0 else None,capacity=100*len(its),scenario_sold_pax=sum(s['sold_journeys']for s in sales if s['network']=='D_pilot'and s['scenario']==sc and s['origin']==a),
     required_paid_pax_with_1million_allocated_fixed_per_week=(legcost+P['fixed_per_allocated_working_or_reserve_tail_week'])/margin if margin>0 else None,gate='Paid bookings/guaranteed block revenue, not capacity times target load; retained incumbent contribution must be netted'))
 save('pilot_booking_gate.csv',gate)
 assumptions=dict(as_of='2026-11-09',week='2026-12-07/13',demand='UNKNOWN empirical OD; common bands from stage15; 0.5..3 scale is stress grid NOT empirical bounds',fare='UNKNOWN net settlements; common bands; 0.75..2 grid stress; old foregone yield scales too',capture='SCENARIO same peak0.45 base/0.30 cautious for all local OD; f-response 1-exp(-f/3); no measured share',transfer='SCENARIO stage15 0.45/0.30 and competition factor0.65; reciprocal same-week dates required',cost='UFA announced fuel136300/t base reference;160000 stress. All-airport basket/burn/TO/crew are scenarios. Cost scale0.7..1.3 is arithmetic stress, not contracts',fleet='ceiling4active100seats+1reserve; minimum scheduled peak charged in fixed sensitivity; availability UNKNOWN',fixed='0 or500000/allocated tail/week and0/500000newbase/week illustration only; no observed base/fleet cost',range='hard conservative screen2300km; southGCx1.20 forAER/MRV/VOG/MCX; not payload/dispatch approval',ground='direct legs under500km excluded in this experiment; not a legal restriction; detailed ground-choice calibration absent',pool='all20longlist cities plusARH/MMK/NJC; existingbasesZIA/SVX; outbacks and reversibletriangles, f1/2/3; hubs GOJ/UFA/TJM/CEK 4/6/8-of-old8 rays f1/2/3',optimization='bounded finite enumeration plus direct marginal greedy; pair relaxation bound only for enumerated direct OD; no global optimal claim',unchanged_policy='B0 retained reference but2pairs fail conservative screen; no launch is available; fixed minima/8routes not forced on pilot')
 js('assumptions.json',assumptions)
 tests=independent(m,selected,summary,sales,caps);assert all(r['best_frequency_including_zero']==0 for r in relaxed);tests['direct_pair_relaxation_best_zero_under_current_inputs']=True
 tests['direct_case_has_at_least_eight_pairs']=next(r['physical_pairs']for r in summary if r['network']=='D_case8')>=8
 tests['all_accepted_candidate_routes_green']=all(r['range_screen_pass']for r in summary if r['network']!='B0_reference')
 tests['known_RW_overlap_keeps_separate_migration_scenario']=all(m.markets[k]['cannibal_base']>=P['known_incumbent_migration']['base']for k in m.markets if any(m.rw.get((a,b),0)>0 for a,b in [tuple(k.split('-')),tuple(k.split('-')[::-1])]))
 tests['all_baseline_launches_negative']=all(val(r)<0 for r in summary if r['weekly_legs']>0)
 tests['all_enumerated_solo_circuits_and_hub_variants_negative']=all(val(r)<0 for r in candidates+hr)
 assert all(tests.values());js('validation.json',dict(status='PASS',tests=tests,direct_circuit_candidates=len(dnets),hub_candidates=len(hnets),observed_OD_rows=0,limits='Conditional arithmetic only, no empirical market validation'))
 files=[Path(__file__),ROOT/'scripts/write_conditional_note.py',OUT/'assumptions.json',*list((OUT/'research').glob('*.csv')),ROOT/'scripts/build_team_comparison.py',ROOT/'tools/dist.py',ROOT/'context/15_team_update/model/overrides.json']+[p for p in old.READS if p.is_relative_to(ROOT)and not p.is_relative_to(M)]
 js('input_manifest.json',{'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(set(files))},'prior_tree':'../prior_tree_manifest.json'})
 js('selected_networks.json',{name:{k:n[k]for k in ['hub','kind','frequency']if k in n}|{'jobs':n.get('jobs'),'leaves':n.get('leaves')}for name,n in selected.items()})
 import write_conditional_note
 write_conditional_note.main()
 print(json.dumps({'status':'PASS','direct_candidates':len(dnets),'hub_candidates':len(hnets),'pilot':pilot.get('jobs'),'base':[(r['network'],round(val(r)/1e6,3))for r in summary if r['scenario']=='base']},ensure_ascii=False))
if __name__=='__main__':main()
