#!/usr/bin/env python3
"""Independent unit ledger and conditional break-even audit of frozen stage17.

No internet, airport-throughput demand conversion, automatic tax credit, or pilot gate.
"""
from __future__ import annotations
import collections,copy,csv,hashlib,json,math,subprocess
from pathlib import Path
import build_aircraft_route_review as model

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'context/18_unit_economics_audit';PREV=ROOT/'context/17_aircraft_route_review'
P=json.loads((OUT/'assumptions.json').read_text())
def read(path):
 with path.open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
def write(name,rows):
 rows=list(rows)
 with (OUT/name).open('w',encoding='utf-8',newline='')as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n');w.writeheader();w.writerows(rows)
def dump(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def near(a,b):assert abs(float(a)-float(b))<1e-5,(a,b)

def flight_parts(minutes,sc,params,mtow=49.45):
 h=minutes/60;tons=params['fuel_t_per_hour']*h+params['fuel_t_per_cycle']
 airport=(mtow*(553+499)+19300+8100+16668)*params['airport_factor']
 return dict(block_hours=h,fuel_t=tons,fuel_product=tons*params['fuel_rub_per_t'],fuel_uplift=tons*params['fuel_uplift_rub_per_t'],mro=h*params['mro_rub_per_hour'],crew=h*params['crew_rub_per_hour'],navigation=h*params['navigation_rub_per_hour'],airport_turn=airport,deicing=params['deicing_probability']*params['deicing_operation_rub'])
COST=['fuel_product','fuel_uplift','mro','crew','navigation','airport_turn','deicing']

def audit_previous(m):
 """Read frozen sales and physical flights, rebuild all costs and revenue independently."""
 flights=read(PREV/'model/flights.csv');sales=read(PREV/'model/sales.csv');comp=read(PREV/'model/comparison.csv');caps=read(PREV/'model/capacity.csv');result=[]
 for r in comp:
  pr,n,sc=r['profile'],r['network'],r['scenario'];p=m.scenarios[sc]
  ff=[f for f in flights if(f['profile'],f['network'])==(pr,n)]
  ss=[s for s in sales if(s['profile'],s['network'],s['scenario'])==(pr,n,sc)]
  cc={c['flight_id']:c for c in caps if(c['profile'],c['network'],c['scenario'])==(pr,n,sc)}
  ledger=collections.Counter();used=collections.Counter();migrated_by_od=collections.Counter()
  for f in ff:
   q=flight_parts(float(f['block_minutes']),sc,p,45.88 if pr=='RRJ95B_MASS_TEST' else 49.45)
   ledger.update({k:q[k]for k in COST});ledger['fuel_t']+=q['fuel_t'];ledger['block_hours']+=q['block_hours']
  for s in ss:
   count=float(s['sold_journeys']);legs=s['flight_ids'].split(';');a,b=s['origin'],s['destination'];market=m.markets[model.core.pair(a,b)]
   direct=float(s['migrated_RW_direct']);unknown=float(s['migrated_RW_unverified_connecting']);oldfare=market['fare_'+sc]*p['old_RW_fare_ratio']
   near(s['gross_revenue'],count*float(s['fare_once']));near(s['foregone_RW_revenue'],(direct+unknown)*oldfare)
   assert len(legs)==(2 if s['transfer']=='True' else 1)
   ledger.update(dict(journeys=count,transfer=count if len(legs)==2 else 0,segment_pax=count*len(legs),gross=count*float(s['fare_once']),foregone=(direct+unknown)*oldfare,pax_cost=count*len(legs)*p['pax_cost'],saved_pax=(direct+2*unknown)*p['pax_cost']))
   for leg in legs:used[leg]+=count
   migrated_by_od[a,b]+=direct
  for leg,count in used.items():near(count,cc[leg]['occupied']);assert count<=float(cc[leg]['capacity_scenario'])+1e-7
  flight_cost=sum(ledger[k]for k in COST);incremental_revenue=ledger['gross']-ledger['foregone'];operating=flight_cost+ledger['pax_cost']-ledger['saved_pax'];profit=incremental_revenue-operating
  for key,val in [('gross_revenue',ledger['gross']),('foregone_RW_revenue',ledger['foregone']),('sold_journeys',ledger['journeys']),('transfer_journeys',ledger['transfer']),('segment_pax',ledger['segment_pax']),('flight_variable_cost',flight_cost),('incremental_revenue',incremental_revenue),('incremental_operating_cost',operating),('contribution_before_base_fleet_opportunity',profit)]:near(r[key],val)
  result.append(dict(profile=pr,network=n,scenario=sc,**dict(ledger),flight_cost=flight_cost,incremental_revenue=incremental_revenue,incremental_operating_cost=operating,contribution=profit,status='PASS_independent_ledger'))
 return result

def direct(m,a,b,f=1):return model.make_direct(m,a+'_'+b,[dict(base=a,route=[a,b,a],frequency=f)])

def unit_margin(m,a,b,sc):
 market=m.markets[model.core.pair(a,b)];p=m.scenarios[sc];can=market['cannibal_'+sc]
 # All tests limited to100pax/departure; existing weekly direct seat caps checked separately.
 oldsegs=1 if m.rw_cap(a,b)is not None else 2
 return market['fare_'+sc]*(1-can*p['old_RW_fare_ratio'])-p['pax_cost']*(1-oldsegs*can)

def thresholds(m,net,a,b,sc,burden=0):
 r,ss,cc=m.evaluate(net,sc,detail=True);p=m.scenarios[sc];market=m.markets[model.core.pair(a,b)];f=sum(l['origin']==a for l in net['legs'])
 F=r['flight_variable_cost']+burden;margin=(unit_margin(m,a,b,sc)+unit_margin(m,b,a,sc))/2
 raw=F/(2*f*margin)if margin>0 else None;within=raw is not None and raw<=100
 paid_now=r['sold_journeys']/(2*f);can=market['cannibal_'+sc];oldsegments=1 if m.rw_cap(a,b)is not None else 2
 net_pax=p['pax_cost']*(1-oldsegments*can);fare=market['fare_'+sc];oldfare=fare*p['old_RW_fare_ratio']
 q=p['capture_'+market['capture_group']]*(1-math.exp(-f/p['frequency_scale']))
 new_yield=F/(2*f*paid_now)+net_pax+can*oldfare
 common_yield=(F/(2*f*paid_now)+net_pax)/(1-can*p['old_RW_fare_ratio'])
 at100=2*f*100*margin-F
 required={}
 for l in net['legs']:
  if l['origin']==a or l['origin']==b:
   cost=sum(flight_parts(l['block_minutes'],sc,p)[k]for k in COST)+burden/(2*f)
   mg=unit_margin(m,l['origin'],l['destination'],sc);value=cost/mg if mg>0 else None
   required['outbound'if l['origin']==a else'inbound']=value
 return dict(route=a+'-'+b,scenario=sc,frequency_per_direction=f,weekly_extra_burden=burden,assumed_net_fare=fare,paid_now_per_departure=paid_now,unit_incremental_margin_current_yield=margin,required_paid_per_departure_if100_feasible=raw if within else None,linear_paid_threshold_NOT_capacity_forecast=raw,within_nominal100=within,required_paid_ceil_if_feasible=math.ceil(raw)if within else None,required_outbound=required['outbound'],required_inbound=required['inbound'],required_OD_week_direction_if_capture_unchanged=raw*f/q if within else None,assumed_OD_week_direction=market['demand_'+sc],assumed_capture_at_frequency=q,required_capture_at_assumed_OD=raw*f/market['demand_'+sc]if within else None,new_net_yield_needed_at_same_sales_old_RW_yield_fixed=new_yield,common_new_and_old_net_yield_needed_at_same_sales=common_yield,common_yield_needed_at100=(F/(2*f*100)+net_pax)/(1-can*p['old_RW_fare_ratio']),contribution_at100_and_current_fare=at100,remaining_extra_fixed_headroom_at100_AFTER_selected_burden=at100 if at100>=0 else None,flight_cost_reduction_needed_at_current_sales=max(0,(-model.contribution(r)+burden)/r['flight_variable_cost']),net_fuel_benefit_needed_at_current_sales=max(0,(-model.contribution(r)+burden)/sum(flight_parts(l['block_minutes'],sc,p)['fuel_t']for l in net['legs'])),conditional_dispatch='NOT_CONFIRMED;100is an optimistic scenario')

def route_audit(m):
 details=[];costs=[];be=[];sensitivity=[];frequency=[];credit=[];bridge=[]
 for a,b in P['routes']:
  n=direct(m,a,b)
  for sc in ['base','cautious']:
   r,ss,cc=m.evaluate(n,sc,detail=True);p=m.scenarios[sc];market=m.markets[model.core.pair(a,b)]
   parts=collections.Counter()
   for l in n['legs']:
    q=flight_parts(l['block_minutes'],sc,p);near(sum(q[k]for k in COST),m.flight_cost(l,sc));parts.update(q)
    costs.append(dict(route=a+'-'+b,scenario=sc,origin=l['origin'],destination=l['destination'],block_minutes=l['block_minutes'],time_evidence=m.route_blocks.get((l['origin'],l['destination']),{}).get('status','UNKNOWN_OPTIMISTIC_PROXY'),**q,flight_total=sum(q[k]for k in COST)))
   near(sum(parts[k]for k in COST),r['flight_variable_cost'])
   details.append(dict(route=a+'-'+b,scenario=sc,paid_per_departure=r['sold_journeys']/2,assumed_fare=market['fare_'+sc],assumed_weekly_OD_direction=market['demand_'+sc],effective_capture=p['capture_uncertain']*(1-math.exp(-1/3)),migration_share=market['cannibal_'+sc],**{k:r[k]for k in ['sold_journeys','gross_revenue','foregone_RW_revenue','incremental_revenue','flight_variable_cost','new_pax_variable','saved_old_pax_variable','contribution_before_base_fleet_opportunity']},**{k:parts[k]for k in COST},fuel_t=parts['fuel_t'],fuel_share_of_flight_cost=(parts['fuel_product']+parts['fuel_uplift'])/r['flight_variable_cost']))
   for burden in P['fixed_extra_burden_per_roundtrip_week_rub']:be.append(thresholds(m,n,a,b,sc,burden))
   for f in [1,2,3]:
    nf=direct(m,a,b,f);rf=m.evaluate(nf,sc)[0]
    frequency.append(dict(route=a+'-'+b,scenario=sc,frequency_per_direction=f,paid_per_departure=rf['sold_journeys']/(2*f),gross_revenue=rf['gross_revenue'],contribution=model.contribution(rf),flight_cost=rf['flight_variable_cost'],frequency_response='UNCALIBRATED; fare held constant'))
   for benefit in P['net_fuel_adjustment_stress_rub_per_t']:
    credit.append(dict(route=a+'-'+b,scenario=sc,net_fuel_benefit_rub_per_t=benefit,extra_income_or_cost_reduction=benefit*parts['fuel_t'],contribution=model.contribution(r)+benefit*parts['fuel_t'],status='NET_ADDITIONAL_ILLUSTRATION_NOT_RW_PAYMENT'))
   for case in P['sensitivity_cases']:
    profit=model.contribution(r);change=0.;caveat='SCENARIO_NOT_OBSERVED'
    if case=='no_migration':change=r['foregone_RW_revenue']-r['saved_old_pax_variable']
    elif case=='no_uplift':change=parts['fuel_uplift']
    elif case=='remove_cycle_fuel_overlap_test':change=2*p['fuel_t_per_cycle']*(p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t']);caveat='Only if hourly burn already includes the same cycle phases; not established from mission fuel data'
    elif case=='remove_receive_release_for_overlap_test_only':change=2*16668*p['airport_factor'];caveat='Only if already in own-MRO/handling contract; NOT established'
    elif case=='pax_cost338_5_reference_only':change=(r['new_pax_variable']-r['saved_old_pax_variable'])*(1-338.5/p['pax_cost']);caveat='UFA public passenger rows only; NOT complete network variable cost'
    elif case=='no_hourly_crew_cash_only':change=parts['crew'];caveat='Short-term avoidable-cash bound only, not full economics'
    elif case=='no_MRO_cash_only':change=parts['mro'];caveat='Wear/maintenance remains an economic cost; not a valid sustainable budget'
    elif case=='fuel_burn_minus20pct_unverified':change=.2*(parts['fuel_product']+parts['fuel_uplift']);caveat='No route-specific burn evidence supports20% reduction'
    elif case=='all_flight_cost_minus20pct_unverified':change=.2*r['flight_variable_cost'];caveat='No contract supports a simultaneous20% saving'
    elif case in ['unknown_leg_plus30min','unknown_leg_plus60min']:
     extra=30 if case.endswith('30min') else 60;change=-sum(sum(flight_parts(l['block_minutes']+extra,sc,p)[k]-flight_parts(l['block_minutes'],sc,p)[k]for k in COST)for l in n['legs']if(l['origin'],l['destination'])not in m.route_blocks);caveat='Time-error stress only on unpublished directions, not a route estimate or valid new schedule'
    sensitivity.append(dict(route=a+'-'+b,scenario=sc,case=case,change_from_baseline=change,contribution=profit+change,caveat=caveat))
  # Sequential bridge, not a causal attribution. Last row must equal cautious model.
  z=copy.deepcopy(m);last=model.contribution(z.evaluate(n,'base')[0]);start=last
  groups=[('demand_and_capture',['capture_open','capture_competitive','capture_uncertain','capture_transfer'],['demand']),('yield_and_foregone_yield',['old_RW_fare_ratio','transfer_fare_factor'],['fare']),('migration',[],['cannibal']),('costs',[k for k in z.scenarios['base']if k not in ['capture_open','capture_competitive','capture_uncertain','capture_transfer','old_RW_fare_ratio','transfer_fare_factor']],[])]
  for name,keys,market_keys in groups:
   for k in keys:z.scenarios['base'][k]=z.scenarios['cautious'][k]
   for value in z.markets.values():
    for k in market_keys:value[k+'_base']=value[k+'_cautious']
   now=model.contribution(z.evaluate(n,'base')[0]);bridge.append(dict(route=a+'-'+b,step=name,previous_contribution=last,change=now-last,contribution=now,order_dependent=True));last=now
  near(last,model.contribution(m.evaluate(n,'cautious')[0]))
 return details,costs,be,sensitivity,frequency,credit,bridge

def max_profit_flow(in_caps,out_caps,edges):
 """Fractional max-weight bipartite flow via residual shortest paths (allows rerouting)."""
 nodes=['S','T']+['I:'+k for k in in_caps]+['O:'+k for k in out_caps];adj={n:[]for n in nodes}
 def edge(a,b,cap,cost):
  x=[b,cap,cost,None];y=[a,0.,-cost,x];x[3]=y;adj[a].append(x);adj[b].append(y)
 for k,v in in_caps.items():edge('S','I:'+k,v,0.)
 for k,v in out_caps.items():edge('O:'+k,'T',v,0.)
 tracked=[]
 for a,b,margin in edges:
  edge('I:'+a,'O:'+b,1e9,-margin);tracked.append(adj['I:'+a][-1])
 gain=0.;flow=0.
 while True:
  dist={k:math.inf for k in nodes};dist['S']=0.;prev={}
  for _ in range(len(nodes)-1):
   changed=False
   for a in nodes:
    if not math.isfinite(dist[a]):continue
    for e in adj[a]:
     if e[1]>1e-8 and dist[a]+e[2]<dist[e[0]]-1e-8:dist[e[0]]=dist[a]+e[2];prev[e[0]]=(a,e);changed=True
   if not changed:break
  if not math.isfinite(dist['T'])or dist['T']>=-1e-8:break
  v='T';amount=math.inf
  while v!='S':a,e=prev[v];amount=min(amount,e[1]);v=a
  v='T'
  while v!='S':a,e=prev[v];e[1]-=amount;e[3][1]+=amount;v=a
  flow+=amount;gain-=amount*dist['T']
 return flow,gain

def hub_probes(m):
 defs=json.load(open(PREV/'model/selected_networks.json'));rows=[];bound=[]
 for name in ['H_UFA_4','H_UFA_8']:
  d=defs[P['profile']+'|'+name];net=model.legacy.hub(m,d['hub'],d['leaves'],d['frequency'],name)
  transfer_markets={model.core.pair(a,b)for a,b in net['itineraries']if a!=d['hub']and b!=d['hub']}
  for sc in ['base','cautious']:
   original={k:m.markets[k]['demand_'+sc]for k in transfer_markets}
   for factor in P['transfer_probe_scales']:
    for k,v in original.items():m.markets[k]['demand_'+sc]=v*factor
    r=m.evaluate(net,sc)[0];rows.append(dict(network=name,scenario=sc,transfer_demand_scale=factor,transfer_journeys=r['transfer_journeys'],load_factor=r['load_factor'],contribution=model.contribution(r),status='UNCHANGED_LOCAL_FIRST_BOOKING_RULES_NOT_GLOBAL_MAXIMUM'))
   for k,v in original.items():m.markets[k]['demand_'+sc]=v
   # Remove transfer products and evaluate fixed local sales first.
   local=copy.deepcopy(net);local['itineraries']={k:v for k,v in local['itineraries'].items()if not v[0]['transfer']}
   local_r,_,cap=m.evaluate(local,sc,detail=True);left={r['flight_id']:r['capacity_scenario']-r['occupied']for r in cap}
   inbound={l['id']:left[l['id']]for l in net['legs']if l['destination']==d['hub']};outbound={l['id']:left[l['id']]for l in net['legs']if l['origin']==d['hub']};edges=[]
   for (a,b),its in net['itineraries'].items():
    assert m.markets[model.core.pair(a,b)]['fare_'+sc]*m.scenarios[sc]['old_RW_fare_ratio']>=2*m.scenarios[sc]['pax_cost']
    for it in its:
     if it['transfer']:
      fare=m.markets[model.core.pair(a,b)]['fare_'+sc]*m.scenarios[sc]['transfer_fare_factor'];margin=fare-2*m.scenarios[sc]['pax_cost'];edges.append((*it['legs'],margin))
   flows,gain=max_profit_flow(inbound,outbound,edges)
   bound.append(dict(network=name,scenario=sc,fixed_local_journeys=local_r['sold_journeys'],local_only_contribution=model.contribution(local_r),optimistic_transfer_journeys=flows,optimistic_transfer_margin=gain,optimistic_total_contribution=model.contribution(local_r)+gain,transfer_migration=0,transfer_OD_limit='NONE',interpretation='Upper bound with locals fixed and existing dated products, not full-network optimum'))
 return rows,bound

def sourced_scale_tests(m,breakeven):
 results=[];gates=[]
 for anchor in read(OUT/'evidence/observed_pair_segments.csv'):
  if anchor['period']!='2025':continue
  a,b=anchor['route'].split('-');annual=float(anchor['value']);reference=annual/(2*52);net=direct(m,a,b)
  for sc in ['base','cautious']:
   threshold=next(r for r in breakeven if r['route']==anchor['route']and r['scenario']==sc and r['weekly_extra_burden']==0)
   q=threshold['assumed_capture_at_frequency']
   gates.append(dict(route=anchor['route'],scenario=sc,historical_segment_reference_per_week_direction=reference,old_assumed_endpoint_OD_week_direction=threshold['assumed_OD_week_direction'],required_endpoint_fraction_times_winter_ratio=threshold['required_OD_week_direction_if_capture_unchanged']/reference if threshold['within_nominal100'] else None,source=anchor['source'],interpretation='Conditional algebraic boundary; endpoint share and seasonality unknown, not an observed OD estimate'))
   for endpoint in P['endpoint_fraction_tests']:
    for winter in P['winter_to_annual_average_tests']:
     z=copy.deepcopy(m);z.markets[model.core.pair(a,b)]['demand_'+sc]=reference*endpoint*winter;r=z.evaluate(net,sc)[0]
     results.append(dict(route=anchor['route'],scenario=sc,endpoint_fraction=endpoint,winter_to_annual_ratio=winter,assumed_OD_week_direction=reference*endpoint*winter,capture=q,paid_per_departure=r['sold_journeys']/2,contribution_before_extra_fixed=model.contribution(r),source=anchor['source'],status='SOURCE_LINKED_SCENARIO_NOT_CONFIRMED_DEMAND_OR_TICKET_YIELD'))
 return results,gates

def input_registry(m):
 units={'fuel_t_per_hour':'t per aircraft block-hour','fuel_t_per_cycle':'t per aircraft departure','fuel_rub_per_t':'RUB/t ex recoverable VAT','fuel_uplift_rub_per_t':'RUB/t','mro_rub_per_hour':'RUB/block-hour','crew_rub_per_hour':'RUB/block-hour','navigation_rub_per_hour':'RUB/block-hour','pax_cost':'RUB/occupied new segment','airport_factor':'multiplier of UFA reference turn','deicing_probability':'probability per departure','deicing_operation_rub':'RUB/deicing operation','capture_uncertain':'maximum captured share before frequency response','capture_transfer':'maximum transfer share before frequency/competition factors','frequency_scale':'departures/week/direction in uncalibrated response','transfer_fare_factor':'multiplier per through journey, not per leg','old_RW_fare_ratio':'foregone old one-way net yield/new reference fare'}
 rows=[];u='https://www.airportufa.ru/upload/medialibrary/d47/ncxe76bimym6txhx3wgk089z7l63pc0x.pdf';f='https://www.airportufa.ru/upload/medialibrary/2bf/ow4eayup87onwcj9faekxpmzamddh571.pdf'
 for k,unit in units.items():
  kind='ANALYST_SCENARIO_NOT_MEASURED';source='context/12_network_economics/inputs.json; context/16_conditional_decision/assumptions.json'
  if k=='fuel_rub_per_t':kind='BASE_PRIMARY_UFA_LOCAL_PRICE; CAUTIOUS_STRESS';source=f
  if k=='fuel_uplift_rub_per_t':kind='PRIMARY_UFA_LOCAL_PRICE; NETWORK_APPLICATION_SCENARIO';source=u
  rows.append(dict(parameter=k,base=m.scenarios['base'][k],cautious=m.scenarios['cautious'][k],unit=unit,status=kind,source=source,limitation='No admitted RW all-airport contract or tail/route actual; not a market confidence interval'))
 for k,base,caut,unit,source,limit in [('OD_market_bands','120..480','40..180','one-way endpoint journeys/week/direction','scripts/build_team_comparison.py::band_values','COMMON ASSUMPTIONS, not actual OD; fare/demand cliffs at600/1200/1800km'),('net_fare_market_bands','5000..14000','3500..10500','RUB/one-way journey ex recoverable VAT','scripts/build_team_comparison.py::band_values','No matched settled yield; airport fee inclusion must agree with net-fare definition'),('unknown_migration_share',.05,.1,'fraction of new journeys','scripts/build_aircraft_route_review.py::setup','Scenario, not observed own connecting displacement'),('known_own_overlap_migration_share',.6,.8,'fraction of new journeys','context/16_conditional_decision/assumptions.json','Observed own schedule does not establish this displacement share'),('UFA_turn_basket',96089.4,115307.28,'RUB/airport turn',u,'49.45t*(553+499)+19300+8100+16668; no separate arrival/release duplication; packages may overlap MRO'),('nominal_seats',100,100,'seats/departure','context/17_aircraft_route_review/assumptions.json','UPPER TEST only, actual tail payload unverified'),('extra_fixed_burden_in_previous_contribution',0,0,'RUB/project week','context/17_aircraft_route_review/README.md','Excluded from contribution, not evidence fixed or opportunity costs are actually zero'),('net_fuel_tax_contract_adjustment_baseline',0,0,'NET ADDITIONAL RUB/t','context/18_unit_economics_audit/evidence/source_checks.json','Unknown RW benefit; no gross deduction without accrued tax and no duplicate supplier discount'),('endpoint_fraction_eta','UNKNOWN','UNKNOWN','fraction of route segments that are true endpoints','context/18_unit_economics_audit/assumptions.json','Test grid0.25/0.5/0.75/1 not measured bounds'),('winter_to_annual_s','UNKNOWN','UNKNOWN','ratio of target week to annual-average endpoint week','context/18_unit_economics_audit/assumptions.json','Test grid0.5/0.75/1 not measured bounds')]:rows.append(dict(parameter=k,base=base,cautious=caut,unit=unit,status='EXPLICIT_SCENARIO_OR_UNKNOWN',source=source,limitation=limit))
 return rows

def main():
 m=model.setup(P['profile']);previous=audit_previous(m)
 route,costs,be,sens,freq,credits,bridge=route_audit(m);hub,bounds=hub_probes(m);scales,gates=sourced_scale_tests(m,be)
 for name,rows in [('previous_reconciliation.csv',previous),('route_ledger.csv',route),('flight_cost_components.csv',costs),('breakeven.csv',be),('sensitivities.csv',sens),('frequency_tests.csv',freq),('net_fuel_adjustments.csv',credits),('base_to_cautious_bridge.csv',bridge),('hub_transfer_probes.csv',hub),('hub_transfer_optimistic_bound.csv',bounds),('source_linked_scale_tests.csv',scales),('source_linked_scale_gates.csv',gates),('input_registry.csv',input_registry(m))]:write(name,rows)
 checks={
  'all_previous_132_results_reconcile':len(previous)==132,
  'route_cost_parts_match_original_solver':True,
  'one_fare_per_journey_and_two_transfer_seats_reconciled':True,
  'all_route_baseline_and_cautious_results_negative':all(r['contribution_before_base_fleet_opportunity']<0 for r in route),
  'one_weekly_has_best_per_flight_sales_in_current_uncalibrated_response':all(next(r['paid_per_departure']for r in freq if r['route']==a+'-'+b and r['scenario']==s and r['frequency_per_direction']==1)>=r['paid_per_departure']for a,b in P['routes']for s in ['base','cautious']for r in freq if r['route']==a+'-'+b and r['scenario']==s),
  'maxprofit_flow_handles_rerouting':True,
  'no_unsupported_credit_automatically_in_baseline':P['net_fuel_adjustment_stress_rub_per_t'][0]==0,
  'all_current_market_bands_and_sales_remain_scenarios':True,
  'source_linked_scale_can_change_sign_without_claiming_observed_OD':any(r['contribution_before_extra_fixed']>0 for r in scales)and all(r['status']=='SOURCE_LINKED_SCENARIO_NOT_CONFIRMED_DEMAND_OR_TICKET_YIELD'for r in scales),
  'transfer_optimistic_bound_covers_all_same_product_demand_probes':all(next(b['optimistic_total_contribution']for b in bounds if(b['network'],b['scenario'])==(r['network'],r['scenario']))>=r['contribution']-1e-6 for r in hub),
 }
 # Counterexample requires reverse-edge rerouting, not a greedy allocation.
 f,g=max_profit_flow({'a':1,'b':1},{'x':1,'y':1},[('a','x',10),('a','y',9),('b','x',8)]);near(f,2);near(g,17)
 for r in be:
  a,b=r['route'].split('-');sc=r['scenario'];n=direct(m,a,b);key=model.core.pair(a,b)
  if r['within_nominal100']:
   p=r['linear_paid_threshold_NOT_capacity_forecast'];F=next(x['flight_variable_cost']for x in route if x['route']==r['route']and x['scenario']==r['scenario'])+r['weekly_extra_burden'];near(2*p*r['unit_incremental_margin_current_yield'],F)
   assert 2*math.ceil(p)*r['unit_incremental_margin_current_yield']>=F-1e-6
   z=copy.deepcopy(m);z.markets[key]['demand_'+sc]=r['required_OD_week_direction_if_capture_unchanged'];near(model.contribution(z.evaluate(n,sc)[0])-r['weekly_extra_burden'],0)
  for mode,col in [('common','common_new_and_old_net_yield_needed_at_same_sales'),('new_only','new_net_yield_needed_at_same_sales_old_RW_yield_fixed')]:
   z=copy.deepcopy(m);value=r[col]
   if mode=='new_only':z.scenarios[sc]['old_RW_fare_ratio']*=z.markets[key]['fare_'+sc]/value
   z.markets[key]['fare_'+sc]=value;near(model.contribution(z.evaluate(n,sc)[0])-r['weekly_extra_burden'],0)
 checks['demand_and_two_fare_breakeven_modes_replay_booking_solver']=True
 # Baseline immutable, only current prose/index updates explicitly allowed.
 baseline=json.load(open(OUT/'baseline.json'));changed=[]
 for path,h in baseline['tracked_files'].items():
  if subprocess.check_output(['git','hash-object',str(ROOT/path)],text=True).strip()!=h:changed.append(path)
 allowed={'README.md','context/17_aircraft_route_review/README.md'};assert set(changed)<=allowed,changed
 checks['previous_numeric_results_and_foreign_files_preserved']=True;assert all(checks.values()),checks
 dump('validation.json',dict(status='PASS',tests=checks,previous_numeric_results=len(previous),route_scenario_ledgers=len(route),sources_are_not_demand_validation=True,prior_document_updates=changed))
 inputs=[Path(__file__),ROOT/'scripts/write_unit_economics_audit.py',OUT/'assumptions.json',OUT/'evidence/source_checks.json',OUT/'evidence/observed_pair_segments.csv',PREV/'assumptions.json',PREV/'model/selected_networks.json',PREV/'model/flights.csv',PREV/'model/sales.csv',PREV/'model/capacity.csv',PREV/'model/comparison.csv',PREV/'evidence/directional_blocks.csv',PREV/'evidence/published_service_facts.csv',ROOT/'context/16_conditional_decision/assumptions.json',ROOT/'context/15_team_update/model/overrides.json',ROOT/'context/12_network_economics/inputs.json',ROOT/'scripts/build_aircraft_route_review.py',ROOT/'scripts/build_team_comparison.py',ROOT/'scripts/build_conditional_decision.py']
 inputs += [PREV/'model/input_manifest.json',*[(ROOT/p)for p in json.load(open(PREV/'model/input_manifest.json'))['sha256']]]
 dump('input_manifest.json',{'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(set(inputs))}})
 import write_unit_economics_audit
 write_unit_economics_audit.main()
 print(json.dumps({'status':'PASS','previous_reconciled':len(previous),'route_scenarios':len(route),'tests':len(checks),'hub_bounds':bounds},ensure_ascii=False))
if __name__=='__main__':main()
