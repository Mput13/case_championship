#!/usr/bin/env python3
"""Variant-specific conditional review; no radius gate or generic routing multiplier."""
from __future__ import annotations
import collections,copy,csv,hashlib,itertools,json,math,subprocess
from pathlib import Path
import build_conditional_decision as legacy
import build_team_comparison as core
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'context/17_aircraft_route_review';MODEL=OUT/'model';P=json.loads((OUT/'assumptions.json').read_text())
def readcsv(path):
 with path.open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
def save(name,rows):
 rows=list(rows)
 if not rows:return
 with (MODEL/name).open('w',encoding='utf-8',newline='')as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n');w.writeheader();w.writerows(rows)
def js(name,v):(MODEL/name).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def contribution(r):return r['contribution_before_base_fleet_opportunity']

class RouteModel(core.Model):
 def block(self,a,b,cfg=None):
  c=cfg or self.cfg
  if self.profile=='RELAXED_SAME_INPUTS_100':return core.Model.block(self,a,b,c)
  record=self.route_blocks.get((a,b))
  if record:
   value=float(record['max_published_minutes'])
  else:
   value=math.ceil((30+self.distance(a,b)/750*60)/5)*5
   if self.profile=='UNKNOWN_TIME_PLUS60_100':value+=P['unknown_time_stress_minutes']
  return int(math.ceil(value*c['block_time_factor']))
 def flight_cost(self,l,sc):
  value=core.Model.flight_cost(self,l,sc)
  mtow=45880 if self.profile=='RRJ95B_MASS_TEST'else 49450
  return value+(mtow/1000-49.45)*(553+499)*self.scenarios[sc]['airport_factor']
 def payload(self,l,sc):
  if self.profile not in ['RRJ95B_MASS_TEST','RRJ95LR_MASS_TEST']:return dict(capacity=100,reason='UPPER_SEAT_SUPPLY_ASSUMPTION_NOT_DISPATCH',trip_fuel_kg=None,takeoff_mass_at_100=None)
  mtow=45880 if self.profile=='RRJ95B_MASS_TEST'else 49450
  params=self.scenarios[sc];dow=P['dry_operating_weight_scenario_kg'][sc];reserve=P['residual_and_alternate_fuel_scenario_kg'][sc]
  trip=(params['fuel_t_per_hour']*l['block_minutes']/60+params['fuel_t_per_cycle'])*1000;fuel=trip+reserve
  allowed=min(40000-dow,mtow-dow-fuel,41000-dow-reserve)-P['additional_cargo_kg']
  cap=max(0,min(100,math.floor(allowed/P['person_and_baggage_mass_scenario_kg']))) if fuel<=12327 else 0
  return dict(capacity=cap,reason='ILLUSTRATIVE_MASS_FUEL_BUDGET_NOT_AFM_OR_ROUTE_CLEARANCE',trip_fuel_kg=trip,fuel_with_scenario_reserve_kg=fuel,takeoff_mass_at_100=dow+100*P['person_and_baggage_mass_scenario_kg']+P['additional_cargo_kg']+fuel)
 def evaluate(self,net,sc,priority='local_first',detail=False,**kwargs):
  # Same booking/cannibalisation rules as stage15, with per-leg scenario capacities.
  assert not kwargs,kwargs
  p=self.scenarios[sc];initial={l['id']:self.payload(l,sc)['capacity']for l in net['legs']};caps=initial.copy();offers=[]
  for (a,b),its in net['itineraries'].items():
   market=self.markets[core.pair(a,b)];freq=len(its);trans=its[0]['transfer'];D=market['demand_'+sc]
   q=p['capture_'+('transfer'if trans else market['capture_group'])]*(1-math.exp(-freq/p['frequency_scale']))
   if trans:q=min(1,q*market.get('transfer_competition_factor',1))
   fare=market['fare_'+sc]*(p['transfer_fare_factor']if trans else 1);can=market['cannibal_'+sc]
   for it in its:offers.append(dict(origin=a,destination=b,market=market['pair'],D=D,desired=D*q/freq,fare=fare,oldfare=market['fare_'+sc]*p['old_RW_fare_ratio'],can=can,**it))
  offers.sort(key=lambda o:((o['transfer']if priority=='local_first'else not o['transfer']),-(o['fare']-o['can']*o['oldfare']-len(o['legs'])*p['pax_cost'])/len(o['legs']),o['origin'],o['destination'],o['day'],tuple(o['legs'])))
  migration_left=dict(self.rw);totals=collections.Counter();sales=[]
  for a,b in net['itineraries']:
   known=self.rw_cap(a,b)
   if known is not None:migration_left[(a,b)]=known
  for o in offers:
   sold=min(o['desired'],*(caps[i]for i in o['legs']))
   for i in o['legs']:caps[i]-=sold
   k=(o['origin'],o['destination']);m=self.markets[o['market']];known=self.rw_cap(*k);migrated_direct=min(sold*o['can'],migration_left.get(k,0));migration_left[k]=migration_left.get(k,0)-migrated_direct
   unknown=sold*o['can']-migrated_direct if known is None or m['old_rw_segments']>=2 else 0
   migrated=migrated_direct+unknown;oldsegments=migrated_direct+2*unknown
   values=dict(sold_journeys=sold,transfer_journeys=sold if o['transfer']else 0,segment_pax=sold*len(o['legs']),migrated_RW_total=migrated,migrated_RW_direct=migrated_direct,migrated_RW_unverified_connecting=unknown,gross_revenue=sold*o['fare'],foregone_RW_revenue=migrated*o['oldfare'],incremental_revenue=sold*o['fare']-migrated*o['oldfare'],new_pax_variable=sold*len(o['legs'])*p['pax_cost'],saved_old_pax_variable=oldsegments*p['pax_cost'])
   totals.update(values)
   if detail:sales.append(dict(profile=self.profile,network=net['name'],scenario=sc,origin=o['origin'],destination=o['destination'],day=o['day'],flight_ids=';'.join(o['legs']),fare_once=o['fare'],transfer=o['transfer'],D=o['D'],known_direct_RW_capacity=known,**values))
  for k in ['sold_journeys','transfer_journeys','segment_pax','migrated_RW_total','migrated_RW_direct','migrated_RW_unverified_connecting','gross_revenue','foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable']:totals.setdefault(k,0.)
  flightcost=sum(self.flight_cost(l,sc)for l in net['legs']);operating=flightcost+totals['new_pax_variable']-totals['saved_old_pax_variable']
  result=dict(profile=self.profile,network=net['name'],scenario=sc,**totals,flight_variable_cost=flightcost,incremental_operating_cost=operating,contribution_before_base_fleet_opportunity=totals['incremental_revenue']-operating,weekly_legs=len(net['legs']),weekly_block_hours=sum(l['block_minutes']for l in net['legs'])/60,scenario_segment_seats=sum(initial.values()),load_factor=totals['segment_pax']/sum(initial.values())if sum(initial.values())else 0,dispatch_status=P['route_status_when_unverified'])
  assert all(-1e-6<=caps[k]<=initial[k]+1e-6 for k in caps)
  assert abs(sum(initial.values())-sum(caps.values())-totals['segment_pax'])<1e-5
  caprows=[dict(profile=self.profile,network=net['name'],scenario=sc,flight_id=l['id'],origin=l['origin'],destination=l['destination'],block_minutes=l['block_minutes'],capacity_scenario=initial[l['id']],occupied=initial[l['id']]-caps[l['id']],**{k:v for k,v in self.payload(l,sc).items()if k!='capacity'},flight_variable_cost=self.flight_cost(l,sc))for l in net['legs']]if detail else[]
  return result,sales,caprows

def setup(profile):
 m,_=legacy.setup();m.__class__=RouteModel;m.profile=profile;m.route_blocks={(r['origin'],r['destination']):r for r in readcsv(OUT/'evidence/directional_blocks.csv')}
 if profile!='RELAXED_SAME_INPUTS_100':
  own={}
  for r in readcsv(OUT/'evidence/published_service_facts.csv'):
   if r['flight'].startswith('WZ-')and 'RRJ'in r.get('aircraft','').upper():own[(r['origin'],r['destination'],r['date'],r['flight'])]=r
  m.rw=collections.Counter()
  for r in own.values():m.rw[(r['origin'],r['destination'])]+=100
  for key,market in m.markets.items():
   a,b=key.split('-');known=m.rw.get((a,b),0)>0 or m.rw.get((b,a),0)>0
   for sc in ['base','cautious']:market['cannibal_'+sc]=legacy.P['known_incumbent_migration'][sc]if known else(.05 if sc=='base'else .1)
 m.networks['B0']=core.Model.direct(m,'original');m.networks['B0']['itineraries']=m.itineraries(m.networks['B0'])
 return m

def metric(m,n,sc='base'):
 r=m.evaluate(n,sc)[0];a,_=m.audit(n);r.update(active_allocated=len({l['aircraft']for l in n['legs']}),physical_pairs=len({core.pair(l['origin'],l['destination'])for l in n['legs']}),resource_pass=a['feasible']);return r

def make_direct(m,name,jobs):
 # Retain long candidates: dedicated outstation layovers instead of an implicit daily-return ban.
 short=[];long=[]
 for j in jobs:
  minutes=[m.block(a,b)for a,b in zip(j['route'],j['route'][1:])]
  if any(x>m.cfg['planning_cap_block_h']*60 for x in minutes):return None
  (short if sum(minutes)<=m.cfg['planning_cap_block_h']*60 else long).append(j)
 dedicated=sum(1 if len(j['route'])==3 else j['frequency']for j in long)
 if dedicated>m.cfg['active_aircraft']or(short and dedicated==m.cfg['active_aircraft']):return None
 orig=m.cfg
 if short:
  m.cfg={**orig,'active_aircraft':orig['active_aircraft']-dedicated}
  try:net=legacy.direct(m,name,short)
  finally:m.cfg=orig
  if net is None:return None
 else:net=legacy.direct(m,name,[])
 net['cfg']=orig;legs=net['legs'];num=0
 for j in long:
  route=j['route'];freq=j['frequency']
  if len(route)==3:
   num+=1;tail=f"{j['base']}_OV{num}"
   for k in range(freq):
    day=2*k+1;m.add_leg(legs,name,day,tail,route[0],route[1],300,orig);m.add_leg(legs,name,day+1,tail,route[1],route[2],300,orig)
  else:
   # Each dedicated tail performs CW and CCW cycles, one leg/day; crew/hotel/MRO not confirmed.
   for k in range(freq):
    num+=1;tail=f"{j['base']}_OV{num}"
    for day,(a,b)in enumerate(list(zip(route,route[1:]))+list(zip(route[::-1],route[::-1][1:])),1):m.add_leg(legs,name,day,tail,a,b,300,orig)
 for l in legs:l['overnight_cost_and_remote_MRO']='UNKNOWN; zero additional cash in optimistic comparison'if '_OV'in l['aircraft']else'no scheduled outstation overnight'
 net.update(jobs=jobs,frequency='selected with paid-cost-accounting caveat for layovers')
 net['itineraries']=m.itineraries(net)
 return net

def select(m):
 destinations=sorted(set(r['iata']for r in readcsv(ROOT/'data/processed/longlist.csv'))|{'ARH','MMK','NJC'});jobs=[];solo=[];rejected=[]
 for base in ['ZIA','SVX']:
  commercial=[d for d in destinations if m.distance(base,d)>=P['commercial_min_direct_km']]
  for d in commercial:
   for f in [1,2,3]:jobs.append(dict(base=base,route=[base,d,base],frequency=f))
  for a,b in itertools.combinations(commercial,2):
   if m.distance(a,b)>=P['commercial_min_direct_km']:
    for f in [1,2,3]:jobs.append(dict(base=base,route=[base,a,b,base],frequency=f))
 for i,j in enumerate(jobs):
  n=make_direct(m,f'C{i:04d}',[j])
  if n is None:rejected.append(dict(profile=m.profile,route='-'.join(j['route']),frequency=j['frequency'],reason='MODEL_DAILY_BLOCK_OR_4TAIL_LIMIT; not a technical route ban; dedicated overnight cycles tried'));continue
  r=metric(m,n);solo.append((i,n,r))
 pool=[r|{'route':'-'.join(jobs[i]['route']),'frequency':jobs[i]['frequency']}for i,n,r in solo]
 chosen={};pilot=max(solo,key=lambda q:contribution(q[2]));chosen['D_pilot']=copy.deepcopy(pilot[1]);chosen['D_pilot']['jobs']=[jobs[pilot[0]]]
 # Two independent greedy constructions, no hours equalisation; then one bounded swap pass.
 designs=[]
 for per_pair in [False,True]:
  jj=[];current=make_direct(m,'D',[]);current_v=0
  for step in range(8):
   offers=[];currentpairs=metric(m,current)['physical_pairs']
   for i,n,r0 in solo:
    j=jobs[i]
    if any(j['route']==x['route']for x in jj):continue
    trial=make_direct(m,'D',jj+[j])
    if trial is None:continue
    r=metric(m,trial);newpairs=r['physical_pairs']-currentpairs
    if r['physical_pairs']>12:continue
    gain=contribution(r)-current_v;offers.append((gain/max(1,newpairs)if per_pair else gain,-i,trial,j,r))
   if not offers:break
   score,ni,trial,j,r=max(offers,key=lambda q:(q[0],q[1]));jj.append(j);current=trial;current_v=contribution(r)
   if r['physical_pairs']>=8:break
  designs.append(current)
 best=max(designs,key=lambda n:contribution(metric(m,n)));bestv=contribution(metric(m,best));bestjobs=best['jobs'];upgrade=best
 for drop in range(len(bestjobs)):
  rest=bestjobs[:drop]+bestjobs[drop+1:]
  for i,n,r0 in solo:
   j=jobs[i]
   if any(j['route']==x['route']for x in rest):continue
   trial=make_direct(m,'D',rest+[j])
   if trial is None:continue
   r=metric(m,trial)
   if 8<=r['physical_pairs']<=12 and contribution(r)>bestv+1e-6:bestv=contribution(r);upgrade=trial
 chosen['D_case']=upgrade
 previous=json.load(open(ROOT/'context/16_conditional_decision/model/selected_networks.json'))
 for oldname,newname in [('D_pilot','D_prev_pilot'),('D_case8','D_prev_case')]:
  trial=make_direct(m,newname,previous[oldname]['jobs'])
  if trial is not None:chosen[newname]=trial
 chosen['NO_LAUNCH']=make_direct(m,'NO_LAUNCH',[])
 # Same hub route family as the previous comparison; no single ray is rejected by geography.
 hubs=[]
 for h in ['GOJ','UFA','TJM','CEK']:
  leaves=sorted({l['destination']for l in m.networks['H_'+h+'_compact']['legs']if l['origin']==h})
  for size in [4,6,8]:
   for combo in itertools.combinations(leaves,size):
    for f in [1,2,3]:
     name=f'H_{h}_{size}_{f}_'+'.'.join(combo);n=legacy.hub(m,h,list(combo),f,name);a,_=m.audit(n)
     if a['feasible']:hubs.append((n,metric(m,n)|{'hub':h,'rays':size,'frequency':f,'leaves':';'.join(combo)}))
  for size in [4,8]:
   candidates=[(n,r)for n,r in hubs if r['hub']==h and r['rays']==size and r['transfer_journeys']>0]
   if candidates:chosen[f'H_{h}_{size}']=copy.deepcopy(max(candidates,key=lambda q:contribution(q[1]))[0])
 # Reference physical B0 is re-evaluated, not used as the best direct design.
 chosen['B0_reference']=copy.deepcopy(m.networks['B0'])
 for name,n in chosen.items():
  mapping={l['id']:f'{m.profile}_{name}_{i:03d}'for i,l in enumerate(n['legs'])}
  for l in n['legs']:l.update(id=mapping[l['id']],network=name)
  for its in n['itineraries'].values():
   for it in its:it['legs']=[mapping[x]for x in it['legs']]
  n['name']=name
 return chosen,pool,[r for n,r in hubs],rejected

def independent(m,selected,results,sales,capacity):
 for r in results:
  ss=[s for s in sales if s['network']==r['network']and s['scenario']==r['scenario']];cc=[c for c in capacity if c['network']==r['network']and c['scenario']==r['scenario']]
  for k in ['sold_journeys','transfer_journeys','segment_pax','gross_revenue','incremental_revenue']:assert abs(r[k]-sum(s[k]for s in ss))<1e-5
  used=collections.Counter();od=collections.Counter()
  for s in ss:
   ids=s['flight_ids'].split(';');assert len(ids)==(2 if s['transfer']else 1);assert abs(s['gross_revenue']-s['sold_journeys']*s['fare_once'])<1e-5
   for i in ids:used[i]+=s['sold_journeys']
   od[(s['origin'],s['destination'])]+=s['sold_journeys']
  for key,count in od.items():assert count<=m.markets[core.pair(*key)]['demand_'+r['scenario']]+1e-5
  for c in cc:assert abs(used[c['flight_id']]-c['occupied'])<1e-5 and used[c['flight_id']]<=c['capacity_scenario']+1e-5
  assert abs(r['flight_variable_cost']-sum(c['flight_variable_cost']for c in cc))<1e-5
  assert abs(contribution(r)-r['incremental_revenue']+r['incremental_operating_cost'])<1e-5
 for name,n in selected.items():
  if name=='B0_reference':continue
  assert m.audit(n)[0]['feasible']and len({l['aircraft']for l in n['legs']})<=4
  for tail in {l['aircraft']for l in n['legs']}:
   ff=sorted([l for l in n['legs']if l['aircraft']==tail],key=lambda l:l['departure_utc_minute']);assert ff[0]['origin']==ff[-1]['destination']
   for a,b in zip(ff,ff[1:]):assert a['destination']==b['origin']and a['arrival_utc_minute']+45<=b['departure_utc_minute']


def route_matrix(m):
 rows=[];variants=readcsv(OUT/'evidence/variants.csv');airports={r['iata']:r for r in readcsv(ROOT/'context/15_team_update/evidence/cities_matrix.csv')};runways={r['iata']:r['runway_m']for r in readcsv(ROOT/'data/processed/longlist.csv')}
 for a,b in itertools.combinations(sorted(k for k in m.geo if k!='DME'),2):
  old_rejected=m.distance(a,b)*(1.2 if {a,b}&{'AER','MRV','VOG','MCX'}else 1)>2300
  for x,y in [(a,b),(b,a)]:
   block=m.route_blocks.get((x,y));leg=dict(origin=x,destination=y,block_minutes=m.block(x,y))
   for variant in variants:
    ref=float(variant['catalog_range_km'])if variant['catalog_range_km']else None
    previous=m.profile
    if variant['variant']=='SJ100_PD8':mass_base=mass_caut=None
    else:
     m.profile='RRJ95LR_MASS_TEST'if variant['variant']=='RRJ-95LR-100'else'RRJ95B_MASS_TEST';mass_base=m.payload(leg,'base')['capacity'];mass_caut=m.payload(leg,'cautious')['capacity']
    m.profile=previous
    labels=block['aircraft_labels']if block else''
    rows.append(dict(origin=x,destination=y,variant=variant['variant'],great_circle_km=m.distance(x,y),actual_authorized_track_km=None,legacy_distance_screen_rejected=old_rejected,catalog_reference_km=ref,above_catalog_reference=(m.distance(x,y)>ref)if ref else None,catalog_reference_is_clearance=False,mass_test_capacity_base_NOT_DISPATCH=mass_base,mass_test_capacity_cautious_NOT_DISPATCH=mass_caut,
     published_block_min=None if not block else block['min_published_minutes'],published_block_max=None if not block else block['max_published_minutes'],published_aircraft_labels=labels,block_evidence=None if not block else block['status'],source_urls=variant['source']+(';' +block['source_urls']if block else''),
     origin_reference_runway_length_m=runways.get(x),destination_reference_runway_length_m=runways.get(y),origin_RRJ_family_admission_evidence=airports.get(x,{}).get('rrj_admission'),destination_RRJ_family_admission_evidence=airports.get(y,{}).get('rrj_admission'),dry_operating_weight_actual=None,AFM_payload_range_for_tail=None,dispatch_pax_limit_confirmed=None,forecast_wind_and_reserves=None,airport_runway_PCN_obstacles_for_date=None,current_NOTAM_AIRAC_route=None,available_RW_tails_of_this_variant=None,
     status=P['route_status_when_unverified'],evidence_note='Published operation/type label is supporting context only; does not prove tail modification or100pax performance. Reference-range exceedance raises review priority, never deletes route.'))
 return rows

def main():
 MODEL.mkdir(parents=True,exist_ok=True);allresults=[];allpool=[];allhubs=[];allreject=[];allsales=[];allcaps=[];allflights=[];allroutes=[];selected_def={};counts={};tests={}
 for profile in P['profiles']:
  m=setup(profile);selected,pool,hubs,rejected=select(m);allpool+=pool;allhubs+=hubs;allreject+=rejected
  results=[];sales=[];caps=[]
  for name,n in selected.items():
   selected_def[profile+'|'+name]=dict(jobs=n.get('jobs'),hub=n.get('hub'),leaves=n.get('leaves'),frequency=n['frequency'])
   for l in n['legs']:allflights.append(dict(profile=profile,**l,base_capacity_scenario=m.payload(l,'base')['capacity'],cautious_capacity_scenario=m.payload(l,'cautious')['capacity']))
   for key in sorted({core.pair(l['origin'],l['destination'])for l in n['legs']}):
    a,b=key.split('-');ff=[l for l in n['legs']if core.pair(l['origin'],l['destination'])==key];allroutes.append(dict(profile=profile,network=name,pair=key,departures_A_B=sum(l['origin']==a for l in ff),departures_B_A=sum(l['origin']==b for l in ff),great_circle_km=m.distance(a,b),block_A_B=m.block(a,b),block_B_A=m.block(b,a),technical_status=P['route_status_when_unverified']))
   for sc in ['base','cautious']:
    r,ss,cc=m.evaluate(n,sc,detail=True);r.update(active_allocated=len({l['aircraft']for l in n['legs']}),pairs=len({core.pair(l['origin'],l['destination'])for l in n['legs']}),resource_pass=m.audit(n)[0]['feasible']);results.append(r);sales+=ss;caps+=cc
  independent(m,selected,results,sales,caps);tests[profile+'_independent_accounting_and_rotation']=True
  if profile in ['RRJ95B_MASS_TEST','RRJ95LR_MASS_TEST']:
   variant='RRJ-95B'if profile=='RRJ95B_MASS_TEST'else'RRJ-95LR-100'
   type_record=next(x for x in readcsv(OUT/'evidence/variants.csv')if x['variant']==variant)
   for row in caps:
    count=row['capacity_scenario']
    if count<=0:continue
    sc=row['scenario'];dry=P['dry_operating_weight_scenario_kg'][sc];load=count*P['person_and_baggage_mass_scenario_kg']+P['additional_cargo_kg'];reserve=P['residual_and_alternate_fuel_scenario_kg'][sc]
    assert dry+load<=float(type_record['mzfw_kg'])+1e-6
    assert dry+load+row['fuel_with_scenario_reserve_kg']<=float(type_record['mtow_kg'])+1e-6
    assert dry+load+reserve<=float(type_record['mlw_kg'])+1e-6
    assert row['fuel_with_scenario_reserve_kg']<=float(type_record['reference_usable_fuel_kg_at_density078'])+1e-6
   tests[profile+'_mass_budget_inequalities_from_source_table']=True
  # New solver reproduces the original generic solver when capacities and airport weight are unchanged.
  if profile=='RELAXED_SAME_INPUTS_100':
   for name in ['D_pilot','H_UFA_8']:
    for scale in [1,20]:
     previous={k:v['demand_base']for k,v in m.markets.items()}
     for value in m.markets.values():value['demand_base']*=scale
     n=selected[name];legacy_result=core.Model.evaluate(m,n,'base')[0];new=m.evaluate(n,'base')[0]
     for key in ['sold_journeys','transfer_journeys','gross_revenue','incremental_revenue','contribution_before_base_fleet_opportunity']:assert abs(new[key]-legacy_result[key])<1e-5
     for key,value in previous.items():m.markets[key]['demand_base']=value
   tests['unchanged_100seat_accounting_replays_original_solver_including_saturated_transfer']=True
  allresults+=results;allsales+=sales;allcaps+=caps;counts[profile]=dict(solo=len(pool),hub=len(hubs),rotation_model_rejects=len(rejected))
  print(json.dumps({'profile':profile,'best_direct_pilot':selected_def[profile+'|D_pilot']['jobs'],'best_D_contribution':next(contribution(r)for r in results if r['network']=='D_case'and r['scenario']=='base')},ensure_ascii=False),flush=True)
 save('comparison.csv',allresults);save('direct_candidates.csv',allpool);save('hub_candidates.csv',allhubs);save('rotation_model_rejections.csv',allreject);save('sales.csv',allsales);save('capacity.csv',allcaps);save('flights.csv',allflights);save('routes.csv',allroutes);js('selected_networks.json',selected_def)
 m=setup('ROUTE_INPUTS_UPPER_100');matrix=route_matrix(m);save('route_variant_matrix.csv',matrix)
 old_exclusions=readcsv(ROOT/'context/16_conditional_decision/model/direct_screen_exclusions.csv');restored=[]
 for r in old_exclusions:
  if r['reason'].startswith('outside'):
   a,b=r['base'],r['destination'];present=[x for x in allpool if x['profile']=='ROUTE_INPUTS_UPPER_100'and x['route']=='-'.join([a,b,a])]
   restored.append(dict(origin=a,destination=b,old_reason=r['reason'],new_status=P['route_status_when_unverified'],new_candidate_count=len(present),best_base_contribution=max((contribution(x)for x in present),default=None),non_candidate_reason=''if present else'MODEL_BLOCK/4TAIL_TEST_NOT_FIT; not an aircraft/route ban'))
 for a,b in [('ARH','MRV'),('NJC','VOG')]:
  restored.append(dict(origin=a,destination=b,old_reason='legacy B0 ray outside old distance screen',new_status=P['route_status_when_unverified'],new_candidate_count=sum(x['profile']=='ROUTE_INPUTS_UPPER_100'and a in x['route'].split('-')and b in x['route'].split('-')for x in allpool),best_base_contribution=None,non_candidate_reason='Count is cycles containing pair endpoints, not nonstop dispatch evidence'))
 save('previously_excluded_review.csv',restored)
 tests['all_unknown_route_variant_pairs_retained_for_ops_check']=all(r['status']==P['route_status_when_unverified']for r in matrix)
 tests['all_10_base_distance_exclusions_reviewed']=len(restored)==12
 tests['all_10_base_distance_exclusions_have_actual_candidate_cycles']=all(x['new_candidate_count']>0 for x in restored[:10])
 tests['no_route_distance_or_payload_guarantee_inferred']=all(r['actual_authorized_track_km']is None and r['dispatch_pax_limit_confirmed']is None for r in matrix)
 tests['all_baseline_launch_candidates_negative_in_expanded_search']=all(contribution(r)<0 for r in allpool+allhubs)
 assert all(tests.values()),tests
 changed=[];baseline=json.load(open(OUT/'baseline.json'))
 for path,h in baseline['tracked_files'].items():
  now=subprocess.check_output(['git','hash-object',str(ROOT/path)],text=True).strip()
  if now!=h:changed.append(path)
 allowed={'README.md','CLAUDE.md','docs/17_fleet_range_maintenance_time.md','context/16_conditional_decision/README.md'}
 assert set(changed)<=allowed,changed
 tests['all_previous_numeric_results_preserved_document_updates_authorized']=True
 js('validation.json',dict(status='PASS',tests=tests,profile_candidate_counts=counts,preserved_previous_files_except_documented_updates=changed,observed_OD_added=0,confirmed_dispatch_clearances=0,limits='Conditional mass-budget and economic calculations, not AFM/OFP payload or flight clearance.'))
 inputs=[Path(__file__),ROOT/'scripts/write_route_variant_note.py',OUT/'evidence/sources.json',ROOT/'context/16_conditional_decision/assumptions.json',ROOT/'context/16_conditional_decision/model/comparison.csv',ROOT/'context/16_conditional_decision/model/selected_networks.json',ROOT/'context/16_conditional_decision/research/goj_svx_own_calendar.csv',ROOT/'scripts/collect_route_variant_inputs.py',ROOT/'scripts/build_conditional_decision.py',ROOT/'scripts/build_team_comparison.py',ROOT/'tools/dist.py',OUT/'assumptions.json',*list((OUT/'evidence').glob('*.csv')),*[x for x in core.READS if x.is_relative_to(ROOT)]]
 js('input_manifest.json',{'sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()for x in sorted(set(inputs))}})
 import write_route_variant_note
 write_route_variant_note.main()
 print(json.dumps({'status':'PASS','profiles':len(P['profiles']),'route_variant_direction_rows':len(matrix),'tests':len(tests)}))
if __name__=='__main__':main()
