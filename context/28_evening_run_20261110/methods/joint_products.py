"""C31 one-week replacement and C35 25-day block: dated union, no repeat market/cost."""
import csv,datetime as dt,json
from collections import defaultdict
from model_kernel import ROOT
P=ROOT/'inputs/products_3889';OUT=ROOT/'runs/joint_products_v1';OUT.mkdir(parents=True,exist_ok=True)
def read(n):return list(csv.DictReader((P/'outputs'/n).open()))
fs=read('dated_flights.csv');c31=read('C31_replacement_frontier.csv');c35=read('C35_partner_thresholds.csv')
added=[f for f in fs if f['hypothesis']=='C31' and f['network']=='ADD_SSJ_OMS']
old=[f for f in fs if f['hypothesis']=='C35' and f['network']=='rw_KEEP_retimed']
feed=[f for f in fs if f['hypothesis']=='C35' and f['network']=='external_feed']
assert len(added)==4 and len(old)==16 and len(feed)==16
links=[]
for g in added+old:
 if not any(f['date']==g['date'] for f in feed):
  links.append(dict(date=g['date'],rw_flight=g['flight_id'],rw_variant=g['network'],feed_flight=None,wait_minutes=None,mct_minutes=90,max_wait_minutes=180,eligible=False))
 for f in feed:
  if f['date']!=g['date']:continue
  if f['destination']=='SVX' and g['origin']=='SVX':a,b=f,g
  elif g['destination']=='SVX' and f['origin']=='SVX':a,b=g,f
  else:continue
  wait=(dt.datetime.fromisoformat(b['departure_utc'])-dt.datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
  links.append(dict(date=f['date'],rw_flight=g['flight_id'],rw_variant=g['network'],feed_flight=f['flight_id'],wait_minutes=wait,mct_minutes=90,max_wait_minutes=180,eligible=90<=wait<=180))
assert sum(r['eligible'] for r in links if r['rw_variant']=='ADD_SSJ_OMS')==0
assert sum(r['eligible'] for r in links if r['rw_variant']=='rw_KEEP_retimed')==16
assert {f['date'] for f in added}=={'2027-07-05','2027-07-08'}
assert {f['date'] for f in added}.isdisjoint({f['date'] for f in feed})
rows=[];capacity=[]
for s in ('base','cautious'):
 a=next(r for r in c31 if r['scenario']==s and r['demand_layer']=='nastya_primary' and float(r['additional_mrv_paid_each_leg_probe'])==0 and float(r['foregone_tu_old_mission_contribution_probe'])==0)
 b=next(r for r in c35 if r['scenario']==s and float(r['K_probe'])==0)
 q31=float(a['additional_oms_paid_segments']);q35=float(b['through_oneway_journeys'])
 for f in old+added:
  own=85. if f in old else q31/len(added);through=q35/len(old) if f in old else 0.
  assert own+through<=100+1e-7
  capacity.append(dict(scenario=s,flight_id=f['flight_id'],date=f['date'],variant=f['network'],physical_capacity=100,protected_existing_sales_all_markets=85 if f in old else 0,new_endpoint_SVX_OMS=q31/len(added) if f in added else 0,new_through_IJK_OMS=through,total=own+through,physical_slack=100-own-through,model_lf_target=85 if s=='base' else 80,scope='PHYSICAL_SEATS; not permission to exceed commercial LF policy or observed old sales'))
 ceiling=float(a['maximum_tu_new_allin_cost_plus_K']);product=float(b['variable_incremental_contribution_at_block_probe'])
 for L in (0,1000000,3000000):
  for tu in (2000000,4000000,6000000):
   rows.append(dict(scenario=s,window_start='2027-07-05',window_end='2027-07-30',C31_operated_week_only='2027-07-05/2027-07-11; later weeks KEEP',C35_full_contract='2027-07-06/2027-07-30; no proration',new_endpoint_local_segments=q31,through_journeys=q35,partner_reserved_segments=160,partner_payment=float(b['partner_block_total_probe']),C31_ceiling_before_Tu_K_and_old_Tu_donor=ceiling,C35_contribution_after_partner_and_listed_own_loss=product,listed_C35_own_margin_loss=float(b['lost_previous_own_contribution_probe']),Tu_old_mission_loss_probe=L,Tu_allin_new_cost_probe=tu,conditional_joint_before_K_and_other_network=ceiling+product-L-tu,maximum_Tu_allin_plus_K_at_given_donor=ceiling+product-L,unlisted_signed_other_network='UNKNOWN; cannot reuse same lost journey in C35 and donor term',actual_joint_result='UNKNOWN',market_rule='SVX-OMS f4-f2 once; IJK-OMS once, distinct endpoint market; shared flight seats constrained'))
def dump(n,rr):
 with (OUT/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
dump('dated_connection_union.csv',links);dump('shared_flight_capacity.csv',capacity);dump('joint_frontier.csv',rows)
checks=dict(status='PASS_OWNER_SCOPED',input_commit='388908b6da3539484cb8e2e03ada6ff5cb2204a4',C31_new_flights=4,C35_old_rw_flights=16,C35_partner_flights=16,usable_new_C31_connections=0,usable_existing_retimed_C35_connections=16,capacity_rows=len(capacity),joint_frontiers=len(rows),same_period_policy='One actual C31 diagnostic week plus full C35 contract; not steady annual combination',commercial_LF_policy='Separate from physical100; existing85 are a conditional protected inventory fixture, not endpoint demand observation',internal_own_feed='Separate final Products variant, not included in external-feed union',actual_partner_Tu_old_network='UNKNOWN')
(OUT/'validation.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))
