"""Local sales held fixed: allocate one-fare transfers only through dated feasible connections."""
import csv,datetime as dt,hashlib,json,math
from collections import defaultdict
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from model_kernel import ROOT,nm
OUT=ROOT/'runs/connections_v1';OUT.mkdir(parents=True,exist_ok=True)
net=json.loads((ROOT/'runs/selection_v1/networks.json').read_text())
front=list(csv.DictReader((ROOT/'runs/selection_v1/preserved_frontiers.csv').open()))
ids=sorted({r['selected_id'] for r in front if r['calendar'].startswith('AUTHOR') and r['cap']=='10' and r['network']!='DIRECT'})
flights=list(csv.DictReader((ROOT/'runs/resource_v1/dated_rotations.csv').open()))
byid=defaultdict(list)
for idx,r in enumerate(flights):r=dict(r,flight_id=f'F{idx:05d}');byid[r['network_id']].append(r)
summary=[];assignments=[];caprows=[];certs=[]
for key in ids:
 n=net[key];A=n['assumptions'];m=n['metrics'];r=n['result'];H=m['network'];legs=r[0];tr=r[1];W=A['weeks_per_year']
 fs=byid[key];incoming=defaultdict(list);outgoing=defaultdict(list)
 for i,f in enumerate(fs):
  if f['destination']==H:incoming[f['origin']].append(i)
  if f['origin']==H:outgoing[f['destination']].append(i)
 quotas={};unit={}
 for x,y,km,t in tr:
  u=nm.fare(A,km)*A['transfer_fare_factor']-2*A['pax_cost_rub']+nm.sub(A,H,x)+nm.sub(A,H,y)
  for a,b in ((x,y),(y,x)):quotas[(a,b)]=t;unit[(a,b)]=u
 full_margin=sum(quotas[k]*unit[k] for k in quotas)
 local_c=m['contribution_rub_year']/W-full_margin
 for mct,maxwait in ((45,180),(60,180),(90,180),(60,360)):
  case=f'{key}/mct{mct}/wait{maxwait}';cols=[]
  for pair in quotas:
   x,y=pair
   for i in incoming[x]:
    arrival=dt.datetime.fromisoformat(fs[i]['arrival_utc'])
    for j in outgoing[y]:
     wait=(dt.datetime.fromisoformat(fs[j]['departure_utc'])-arrival).total_seconds()/60
     if mct<=wait<=maxwait:cols.append((pair,i,j,wait,unit[pair]))
  pkeys=list(quotas);pidx={k:i for i,k in enumerate(pkeys)}
  rhs=[]
  for f in fs:
   x=f['origin'] if f['destination']==H else f['destination'];l=legs[x]
   rhs.append(A['seats']*A['lf_max']-l['local_carried']/l['freq'])
  rhs+=list(quotas.values());rhs=np.array(rhs)
  if cols:
   mat=lil_matrix((len(rhs),len(cols)))
   for j,(pair,a,b,wait,u) in enumerate(cols):mat[a,j]=1;mat[b,j]=1;mat[len(fs)+pidx[pair],j]=1
   mat=mat.tocsr();c=-np.array([x[4] for x in cols]);res=linprog(c,A_ub=mat,b_ub=rhs,bounds=(0,None),method='highs');assert res.success,res.message
   x=res.x;used=mat@x;gain=-res.fun;dual=float(rhs@res.ineqlin.marginals);gap=abs(dual-res.fun)
   assert np.max(used-rhs)<1e-6 and gap<1e-4
  else:x=np.array([]);used=np.zeros(len(rhs));gain=0.;gap=0.
  q=float(sum(x));C=local_c+gain
  assert C<=m['contribution_rub_year']/W+1e-5
  summary.append(dict(case=case,network_id=key,scenario=m['scenario'],network=H,planning_mct_minutes=mct,max_wait_minutes=maxwait,candidate_connections=len(cols),source_transfer_journeys_week=sum(quotas.values()),dated_transfer_journeys_week=q,transfer_journey_fraction=q/sum(quotas.values()) if sum(quotas.values()) else None,source_contribution_rub_week=m['contribution_rub_year']/W,local_only_contribution_rub_week=local_c,dated_contribution_rub_week=C,contribution_delta_rub_week=C-m['contribution_rub_year']/W,transfer_margin_realization_fraction=gain/full_margin if full_margin>0 else None,transfer_margin_fraction_needed_for_zero=-local_c/full_margin if full_margin>0 else None,source_support='HISTORICAL_OWNER_SHADOW' if A['use_subsidy'] else 'NONE',scope='FIXED_CONSTRUCTED_WEEK_LOCAL_SALES_HELD; no actual MCT/source/market acceptance; no automatic annualization'))
  for j,qj in enumerate(x):
   if qj<=1e-8:continue
   pair,a,b,wait,u=cols[j];assignments.append(dict(case=case,origin=pair[0],destination=pair[1],inbound_flight=fs[a]['flight_id'],outbound_flight=fs[b]['flight_id'],inbound_arrival=fs[a]['arrival_utc'],outbound_departure=fs[b]['departure_utc'],wait_minutes=wait,journeys=qj,margin_per_journey=u,margin=qj*u,fare_count=1,seat_segments_per_journey=2))
  for i,f in enumerate(fs):caprows.append(dict(case=case,flight_id=f['flight_id'],origin=f['origin'],destination=f['destination'],date=f['date'],departure_utc=f['departure_utc'],model_capacity=A['seats']*A['lf_max'],fixed_local=A['seats']*A['lf_max']-rhs[i],transfer_used=float(used[i]),residual=float(rhs[i]-used[i])))
  certs.append(dict(case=case,primal_dual_gap=gap,max_capacity_or_market_excess=float(max(used-rhs)) if len(rhs) else 0.,objective='MAX_TRANSFER_INCREMENT_WITH_FIXED_LOCAL',columns=len(cols),constraints=len(rhs)))
def dump(name,rows):
 with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
dump('summary.csv',summary);dump('itinerary_assignments.csv',assignments);dump('flight_capacity.csv',caprows);dump('certificates.csv',certs)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS_OWNER_SCOPED',source_package='aa7779192d809558e38b1eb9bdfa25913a3afdc8',networks=len(ids),cases=len(summary),positive_itineraries=len(assignments),primal_dual_certificates=len(certs),full_dated_year_sales='NOT_INFERRED_FROM_THIS_WEEK',independent_review='PENDING'),indent=2)+'\n')
for row in summary:
 if row['scenario']=='base_sub' and row['planning_mct_minutes']==60 and row['max_wait_minutes']==180:print(row['network'],round(row['source_contribution_rub_week']/1e6,3),round(row['dated_contribution_rub_week']/1e6,3),round(row['transfer_journey_fraction'],4))
