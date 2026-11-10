"""Same OMS12 flights/tails: bounded tail-phase search, with lost links and explicit shift cost."""
import ast,csv,datetime as dt,json
from collections import defaultdict
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from model_kernel import ROOT,nm
OUT=ROOT/'runs/synchronised_v1';OUT.mkdir(parents=True,exist_ok=True)
# Reuse exactly the current one-fare shared-seat LP without running the annual experiment.
tree=ast.parse((ROOT/'integer_year_sales.py').read_text())
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='solve_week'],type_ignores=[]),'integer_year_sales.py:solve_week','exec'))
net=json.loads((ROOT/'runs/selection_v1/networks.json').read_text())
front=list(csv.DictReader((ROOT/'runs/selection_v1/preserved_frontiers.csv').open()))
key=next(r['selected_id'] for r in front if r['calendar'].startswith('AUTHOR') and r['scenario']=='base_sub' and r['network']=='OMS' and r['cap']=='10')
n=net[key];A=n['assumptions'];legs=n['result'][0];H='OMS'
fs=[]
for i,f in enumerate(csv.DictReader((ROOT/'runs/resource_v1/dated_rotations.csv').open())):
 if f['network_id']!=key:continue
 x=f['origin'] if f['destination']==H else f['destination']
 fs.append(dict(f,flight_id=f'F{i:05d}',capacity_model=A['seats']*A['lf_max'],local_journeys=legs[x]['local_carried']/legs[x]['freq']))
quotas={};units={}
for x,y,km,t in n['result'][1]:
 u=nm.fare(A,km)*A['transfer_fare_factor']-2*A['pax_cost_rub']+nm.sub(A,H,x)+nm.sub(A,H,y)
 for pair in ((x,y),(y,x)):quotas[pair]=t;units[pair]=u
full=sum(quotas[p]*units[p] for p in quotas);local=n['metrics']['contribution_rub_year']/A['weeks_per_year']-full
tails=sorted({f['tail'] for f in fs});cache={};history=[]
def shifted(offsets):
 out=[]
 for f in fs:
  delta=dt.timedelta(minutes=offsets[f['tail']]);g=dict(f)
  for field in ('departure_utc','arrival_utc'):g[field]=(dt.datetime.fromisoformat(f[field])+delta).isoformat()
  out.append(g)
 return out
def feasible(offsets):
 for f in shifted(offsets):
  if f['departure_utc'][:10]!=f['date'] or f['arrival_utc'][:10]!=f['date']:return False
 return True
def evaluate(offsets):
 k=tuple(offsets[t] for t in tails)
 if k not in cache:cache[k]=solve_week(shifted(offsets),quotas,units,H,True)
 return cache[k]
zero={t:0 for t in tails};best=dict(zero);score=evaluate(best)[0]
# Finite reproducible coordinate search; no global optimum claim.
for sweep in range(4):
 changed=False
 for tail in tails:
  winner=dict(best);win=score
  for offset in range(-180,361,30):
   candidate=dict(best);candidate[tail]=offset
   if not feasible(candidate):continue
   gain=evaluate(candidate)[0]
   if gain>win+1e-5:winner=candidate;win=gain
  if win>score+1e-5:best=winner;score=win;changed=True
  history.append(dict(sweep=sweep,tail=tail,offset_minutes=best[tail],transfer_margin=score))
 if not changed:break
base=evaluate(zero);alt=evaluate(best);af=shifted(best)
assert alt[0]>=base[0]-1e-6
def edges(fl):
 out=set()
 for i,f in enumerate(fl):
  if f['destination']!=H:continue
  for j,g in enumerate(fl):
   if g['origin']!=H or (f['origin'],g['destination']) not in quotas:continue
   wait=(dt.datetime.fromisoformat(g['departure_utc'])-dt.datetime.fromisoformat(f['arrival_utc'])).total_seconds()/60
   if 60<=wait<=180:out.add((i,j))
 return out
be,ae=edges(fs),edges(af);changes=[]
for state,ee in [('LOST',be-ae),('GAINED',ae-be)]:
 for i,j in sorted(ee):changes.append(dict(state=state,inbound=fs[i]['flight_id'],outbound=fs[j]['flight_id'],origin=fs[i]['origin'],destination=fs[j]['destination']))
def pair_sales(res):
 out=defaultdict(float)
 for (pair,i,j,w),q in res[2]:out[pair]+=q
 return out
bq,aq=pair_sales(base),pair_sales(alt)
pairrows=[dict(origin=p[0],destination=p[1],baseline_journeys=bq[p],alternative_journeys=aq[p],delta=aq[p]-bq[p],one_fare_margin=units[p]) for p in quotas]
flightrows=[];checks=0
for i,(f,g) in enumerate(zip(fs,af)):
 assert all(f[k]==g[k] for k in ('flight_id','tail','origin','destination','block_hours','local_journeys'))
 flightrows.append(dict(g,baseline_departure=f['departure_utc'],baseline_arrival=f['arrival_utc'],shift_minutes=best[f['tail']],transfer_used=alt[3][i] if len(alt[3]) else 0))
for t in tails:
 seq=sorted([f for f in af if f['tail']==t],key=lambda f:f['departure_utc'])
 assert sum(float(f['block_hours']) for f in seq)<=70+1e-6
 for a,b in zip(seq,seq[1:]):
  assert a['destination']==b['origin'] and dt.datetime.fromisoformat(a['arrival_utc'])+dt.timedelta(minutes=45)<=dt.datetime.fromisoformat(b['departure_utc']);checks+=1
def dump(name,rows):
 with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
dump('flights.csv',flightrows);dump('connection_changes.csv',changes);dump('market_changes.csv',pairrows);dump('search_trace.csv',history)
gain=alt[0]-base[0];shift_hours=sum(abs(best[f['tail']]) for f in fs)/60
probes=[dict(shift_cost_per_flight_hour_rub=k,shift_hours=shift_hours,known_extra_flight_cost=0,shift_charge=k*shift_hours,delta_after_shift_charge_before_external_loss=gain-k*shift_hours,external_donor_loss='UNKNOWN_SIGNED',full_result='UNKNOWN') for k in (0,1000,10000,50000,100000)]
dump('shift_cost_frontier.csv',probes)
result=dict(status='PASS_OWNER_SCOPED',network_id=key,flights=len(fs),working_tails=len(tails),reserve_unchanged=1,offset_minutes=best,lp_evaluations=len(cache),tail_continuity_checks=checks,baseline_transfer_journeys=base[1],alternative_transfer_journeys=alt[1],source_transfer_journeys=sum(quotas.values()),baseline_transfer_fraction=base[1]/sum(quotas.values()),alternative_transfer_fraction=alt[1]/sum(quotas.values()),baseline_contribution_rub_week=local+base[0],alternative_contribution_rub_week=local+alt[0],delta_before_shift_cost_and_external_loss=gain,shifted_flight_hours=shift_hours,max_shift_rub_per_flight_hour_at_zero_external_loss=gain/shift_hours if shift_hours else None,lost_possible_connections=len(be-ae),gained_possible_connections=len(ae-be),markets_losing_journeys=sum(r['delta']<-1e-7 for r in pairrows),baseline_primal_dual_gap=base[4],alternative_primal_dual_gap=alt[4],support='HISTORICAL_OWNER_SHADOW',actual_external_connections_crew_slots_airport_MCT='UNKNOWN',global_bank_optimum='NOT_CLAIMED',annual_projection='NOT_RUN',interpretation='Same flights/tails, fixed local sales; shift charge and external signed donor effect remain separate. Lost internal transfers included in LP delta.')
(OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
