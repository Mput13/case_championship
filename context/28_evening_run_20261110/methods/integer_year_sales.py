"""Integer dated flights and per-week shared-seat one-fare allocation, on frozen v2 readiness/choices."""
import calendar,csv,datetime as dt,functools,hashlib,json,math
from collections import defaultdict
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from model_kernel import ROOT,load,nm
from dated_offer import revalue
OUT=ROOT/'runs/integer_year_v1';OUT.mkdir(parents=True,exist_ok=True)
net=json.loads((ROOT/'runs/selection_v1/networks.json').read_text());plans=json.loads((ROOT/'runs/resource_v1/plans.json').read_text())
intervals=list(csv.DictReader((ROOT/'runs/annual_v1/program_intervals.csv').open()))
exposure=list(csv.DictReader((ROOT/'runs/annual_v1/annual_budget.csv').open()))
resource_lookup={(r['branch'],r['availability'],r['date']):r for r in csv.DictReader((ROOT/'runs/annual_v1/aircraft_calendar_daily.csv').open())}
D,_=load();base_dt=dt.datetime(2027,1,1,tzinfo=dt.timezone.utc)
@functools.lru_cache(None)
def valued(key,year):
 n=net[key];A,r=revalue(n,D,366 if calendar.isleap(year) else 365)
 legmap={}
 if n['metrics']['kind']=='HUB':
  for x,l in r[0].items():
   for a,b in ((l['a'],l['b']),(l['b'],l['a'])):legmap[(a,b)]=dict(l,local_on_flight=l['local_carried']/l['freq'],migrated_on_flight=l['migrated']/l['freq'])
 else:
  # Each triangle leg has its own share of pooled pair demand, so use a task key.
  for t in r:
   b,x,y=t[1:4]
   for task,seq in [('-'.join((b,x,y,b)),t[8]),('-'.join((b,y,x,b)),list(reversed(t[8])))]:
    for l in seq:legmap[(task,frozenset((l['a'],l['b'])))]=dict(l,local_on_flight=l['carried_dir_week']/l['freq'],migrated_on_flight=l['migrated']/l['freq'])
 return A,r,legmap

def emit_day(key,date,case):
 n=net[key];A,r,legmap=valued(key,date.year);plan=plans[key];out=[];idx=0
 for base,b in plan['bases'].items():
  for tail,slot in enumerate(b['slots'][date.weekday()]):
   now=dt.datetime.combine(date,dt.time(6),tzinfo=dt.timezone.utc)
   for task in slot['tasks']:
    for a,z,bh in zip(task['airports'],task['airports'][1:],task['blocks']):
     idx+=1;l=legmap[(a,z)] if n['metrics']['kind']=='HUB' else legmap[(task['id'],frozenset((a,z)))]
     q=l['local_on_flight'];mg=l['migrated_on_flight'];fare=nm.fare(A,l['km']);fixed=nm.leg_cost(A,l['km'],l['south'],0)[1]
     arr=now+dt.timedelta(hours=bh)
     out.append(dict(case=case,flight_id=f'{case}/{date}/{idx:03}',date=str(date),network_id=key,origin=a,destination=z,departure_utc=now.isoformat(),arrival_utc=arr.isoformat(),tail=f'{base}-{tail}',block_hours=bh,capacity_model=A['seats']*A['lf_max'],local_journeys=q,migrated_journeys=mg,local_ticket_before_migration=q*fare,foregone_ticket=mg*fare,local_support=(q-mg)*nm.sub(A,a,z),fixed_flight_cost=fixed,local_pax_cost=q*A['pax_cost_rub'],local_contribution=(q-mg)*fare+(q-mg)*nm.sub(A,a,z)-fixed-q*A['pax_cost_rub']))
     now=arr+dt.timedelta(minutes=45)
 return out

def solve_week(fs,quotas,units,H,dated=True):
 if not quotas:return 0.,0.,[],[],0.
 incoming=defaultdict(list);outgoing=defaultdict(list)
 for i,f in enumerate(fs):
  if f['destination']==H:incoming[f['origin']].append(i)
  if f['origin']==H:outgoing[f['destination']].append(i)
 keys=list(quotas);cols=[]
 if dated:
  for pair in keys:
   for i in incoming[pair[0]]:
    for j in outgoing[pair[1]]:
     wait=(dt.datetime.fromisoformat(fs[j]['departure_utc'])-dt.datetime.fromisoformat(fs[i]['arrival_utc'])).total_seconds()/60
     if 60<=wait<=180:cols.append((pair,i,j,wait))
  rhs=[f['capacity_model']-f['local_journeys'] for f in fs]+[quotas[k] for k in keys]
  mat=lil_matrix((len(rhs),len(cols)))
  for j,(pair,i,k,w) in enumerate(cols):mat[i,j]=1;mat[k,j]=1;mat[len(fs)+keys.index(pair),j]=1
 else:
  spoke_in=sorted(incoming);spoke_out=sorted(outgoing);cols=[(pair,None,None,None) for pair in keys if pair[0] in incoming and pair[1] in outgoing]
  rhs=[sum(fs[i]['capacity_model']-fs[i]['local_journeys'] for i in incoming[x]) for x in spoke_in]+[sum(fs[i]['capacity_model']-fs[i]['local_journeys'] for i in outgoing[x]) for x in spoke_out]+[quotas[k] for k in keys]
  mat=lil_matrix((len(rhs),len(cols)))
  for j,(pair,i,k,w) in enumerate(cols):mat[spoke_in.index(pair[0]),j]=1;mat[len(spoke_in)+spoke_out.index(pair[1]),j]=1;mat[len(spoke_in)+len(spoke_out)+keys.index(pair),j]=1
 if not cols:return 0.,0.,[],[],0.
 rhs=np.array(rhs);mat=mat.tocsr();c=-np.array([units[x[0]] for x in cols]);r=linprog(c,A_ub=mat,b_ub=rhs,bounds=(0,None),method='highs');assert r.success,r.message
 used=mat@r.x;assert np.max(used-rhs)<1e-6
 gap=abs(float(rhs@r.ineqlin.marginals)-r.fun);assert gap<1e-4
 return -r.fun,float(sum(r.x)),[(cols[i],float(x)) for i,x in enumerate(r.x) if x>1e-8],(used[:len(fs)].tolist() if dated else []),gap

groups=defaultdict(list)
for r in intervals:
 if r['branch'] not in ('PHASED','PARTIAL_FIRST4','DELAY6','NO_NEW') or r['availability']!='14D_GROUNDING_STRESS' or r['network'] not in ('OMS','KUF','DIRECT'):continue
 groups[tuple(r[k] for k in ('branch','scenario','network','year'))].append(r)
annual=[];weekly=[];examples=[];exampleitins=[];examplecap=[];certmax=0.;annualmarket=[];choice_adjustments=[];resource_checks=0
for g,ivals in sorted(groups.items()):
 branch,scenario,H,y=g;year=int(y);case='/'.join(g);byweek=defaultdict(list);qweek=defaultdict(lambda:defaultdict(float));uweek=defaultdict(dict);localmarkets=defaultdict(float);fiscal=defaultdict(float)
 dayids={}
 for row in ivals:
  date=dt.date.fromisoformat(row['start']);end=dt.date.fromisoformat(row['end_exclusive'])
  while date<end:dayids[date]=row['selected_id'];date+=dt.timedelta(days=1)
 weekdates=defaultdict(list)
 for date in sorted(dayids):weekdates[date-dt.timedelta(days=date.weekday())].append(date)
 for monday,dates in sorted(weekdates.items()):
  minimum_working=min(int(resource_lookup[(branch,'14D_GROUNDING_STRESS',str(date))]['working_new']) for date in dates)
  original_ids=set(dayids[d] for d in dates);eligible=[key for key in original_ids if key!='KEEP' and plans[key]['working_tails']<=minimum_working]
  if scenario.startswith('cautious') and monday.isocalendar().week in (2,15,28,41):eligible=[]
  finals=[key for key in eligible if net[key]['metrics']['model_8_12_pair_gate']];pool=finals or eligible
  chosen=max(pool,key=lambda key: net[key]['metrics']['contribution_rub_year']) if pool else 'KEEP'
  choice_adjustments.append(dict(case=case,week_start=str(monday),minimum_working_available=minimum_working,original_daily_ids=' | '.join(sorted(original_ids)),weekly_selected_id=chosen,changed=original_ids!={chosen},reason='ONE_WEEKLY_OFFER_USING_MIN_DAILY_AVAILABLE_RESOURCE; entry or maintenance can defer change up to6days'))
  if chosen=='KEEP':continue
  key=chosen;A,r,legmap=valued(key,year);week=str(monday)
  for date in dates:
   fs=emit_day(key,date,case);byweek[week].extend(fs)
   for f in fs:localmarkets[tuple(sorted((f['origin'],f['destination'])))]+=f['local_journeys']
   if H!='DIRECT':
    for x,z,km,t in r[1]:
     u=nm.fare(A,km)*A['transfer_fare_factor']-2*A['pax_cost_rub']+nm.sub(A,H,x)+nm.sub(A,H,z)
     for pair in ((x,z),(z,x)):
      qweek[week][pair]+=t/7
      if pair in uweek[week]:assert abs(uweek[week][pair]-u)<1e-7
      uweek[week][pair]=u
 totals=defaultdict(float);usedmarkets=defaultdict(float)
 for week,fs in sorted(byweek.items()):
  tail_hours=defaultdict(float);tail_days=defaultdict(float);tailseq=defaultdict(list)
  for f in fs:
   tail_hours[f['tail']]+=f['block_hours'];tail_days[(f['tail'],f['date'])]+=f['block_hours'];tailseq[f['tail']].append(f)
  assert max(tail_hours.values(),default=0)<=70+1e-6
  assert max(tail_days.values(),default=0)<=14+1e-6
  for tail,seq in tailseq.items():
   seq=sorted(seq,key=lambda f:f['departure_utc'])
   for prev,nxt in zip(seq,seq[1:]):
    assert prev['destination']==nxt['origin']
    assert dt.datetime.fromisoformat(prev['arrival_utc'])+dt.timedelta(minutes=45)<=dt.datetime.fromisoformat(nxt['departure_utc'])
    resource_checks+=1
  local=sum(f['local_contribution'] for f in fs);capacity_gain,capacity_q,_,_,gap0=solve_week(fs,qweek[week],uweek[week],H,False)
  gain,q,alloc,used,gap=solve_week(fs,qweek[week],uweek[week],H,True);certmax=max(certmax,gap,gap0)
  assert gain<=capacity_gain+1e-5
  totals['dated_flights']+=len(fs);totals['block_hours']+=sum(f['block_hours'] for f in fs);totals['local_journeys']+=sum(f['local_journeys'] for f in fs);totals['migrated_journeys']+=sum(f['migrated_journeys'] for f in fs);totals['transfer_journeys']+=q
  totals['local_only_contribution']+=local;totals['capacity_only_transfer_gain']+=capacity_gain;totals['dated_transfer_gain']+=gain
  for col,qty in alloc:usedmarkets[tuple(sorted(col[0]))]+=qty
  weekly.append(dict(case=case,week_start=week,dated_flights=len(fs),local_only_contribution=local,capacity_only_contribution=local+capacity_gain,dated_MCT_contribution=local+gain,transfer_journeys=q,source_transfer_quota=sum(qweek[week].values()),mct_minutes=60,max_wait_minutes=180,primal_dual_gap=gap,capacity_primal_dual_gap=gap0))
  if case=='PHASED/base_sub/OMS/2028':
   examples.extend(fs)
   for i,f in enumerate(fs):examplecap.append(dict(flight_id=f['flight_id'],capacity=f['capacity_model'],local=f['local_journeys'],transfer=used[i] if len(used) else 0,residual=f['capacity_model']-f['local_journeys']-(used[i] if len(used) else 0)))
   for (pair,i,j,w),qty in alloc:exampleitins.append(dict(case=case,origin=pair[0],destination=pair[1],inbound_flight=fs[i]['flight_id'],outbound_flight=fs[j]['flight_id'],wait_minutes=w,journeys=qty,one_fare_margin=uweek[week][pair],margin=qty*uweek[week][pair]))
 # No annual OD is exceeded even when a calendar year has 53 occurrences of a weekday.
 for pair in set(localmarkets)|set(usedmarkets):
  observed_model=D.get(pair[0],pair[1],'cautious' if scenario.startswith('cautious') else 'base');q=localmarkets[pair]+usedmarkets[pair]
  assert q<=observed_model+1e-6,(case,pair,q,observed_model)
  annualmarket.append(dict(case=case,origin=pair[0],destination=pair[1],annual_model_OD=observed_model,local_journeys=localmarkets[pair],transfer_journeys=usedmarkets[pair],slack=observed_model-q))
 orig=next(r for r in exposure if r['branch']==branch and r['availability']=='14D_GROUNDING_STRESS' and r['scenario']==scenario and r['network']==H and r['year']==y)
 for field in ('dated_flights','block_hours','local_journeys','migrated_journeys','transfer_journeys','local_only_contribution','capacity_only_transfer_gain','dated_transfer_gain'):totals[field]+=0
 row=dict(case=case,branch=branch,scenario=scenario,network=H,year=year,**totals)
 row.update(dated_contribution_rub=totals['local_only_contribution']+totals['dated_transfer_gain'],integer_capacity_only_contribution_rub=totals['local_only_contribution']+totals['capacity_only_transfer_gain'],v2_active_day_equivalent_contribution=float(orig['contribution_rub']),dated_journeys=totals['local_journeys']+totals['transfer_journeys'],dated_segments=totals['local_journeys']+2*totals['transfer_journeys'],net_added_segments_listed_keep_only=totals['local_journeys']+2*totals['transfer_journeys']-totals['migrated_journeys'],support='OWNER_SHADOW_ONLY' if scenario.endswith('_sub') else 'NONE',actual_grant=None,actual_fleet=None,dispatch='CONSTRUCTIVE_DATES_ONLY_NO_CREW_AIRPORT_APPROVAL',interpretation='Failure of this fixed constructive timetable does not prove no feasible better bank schedule',full_pnl=None)
 annual.append(row)
 print(case,int(totals['dated_flights']),round(row['dated_contribution_rub']/1e6,3),flush=True)
def dump(name,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
dump('weekly_choice_adjustments.csv',choice_adjustments);dump('annual_comparison.csv',annual);dump('weekly_allocation.csv',weekly);dump('annual_market_caps.csv',annualmarket);dump('OMS_2028_dated_flights.csv',examples);dump('OMS_2028_dated_itineraries.csv',exampleitins);dump('OMS_2028_capacity.csv',examplecap)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS_OWNER_SCOPED',input_subject='aa7779192d809558e38b1eb9bdfa25913a3afdc8',annual_cases=len(annual),weekly_cases=len(weekly),maximum_primal_dual_gap=certmax,dated_example_flights=len(examples),dated_example_transfers=len(exampleitins),annual_market_cap_checks=len(annualmarket),tail_continuity_checks=resource_checks,weekly_choices=len(choice_adjustments),weekly_choice_policy='MIN_DAILY_WORKING_RESOURCE_NO_MIDWEEK_OFFER_CHANGE',actual_fleet_market_award_dispatch='NOT_ACCEPTED',scope='Integer dated supply, continuous model passenger quantities; fixed local sales, no network/bank reoptimisation'),indent=2)+'\n')
