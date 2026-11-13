#!/usr/bin/env python3
"""Narrow independent P40 review. Run with network/.venv/bin/python3 -B.
Writes only review/validation.json. No builders/exporters/verify scripts run.
Reuses network receipts; costs assembled independently; only top three bounded
annual combinations are repriced from pinned source primitives.
"""
import sys
sys.dont_write_bytecode = True
import csv, json, math, hashlib, importlib.util
from pathlib import Path
from itertools import product
from collections import defaultdict

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
def read(name):
    with (ROOT/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
def js(name): return json.loads((ROOT/name).read_text())
def module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec); spec.loader.exec_module(obj); return obj
API=module('review_network_api', ROOT/'network/api.py')
P=js('calculation/policy.json'); IR=js('budget/assumptions.json')['irrops']
PARAM={r['parameter_id']:r for r in read('budget/cost_parameters.csv')}
BOQ=read('budget/station_BoQ.csv'); ONCE=read('budget/oneoff_cash.csv')
checks=defaultdict(int); failures=[]; maxima=defaultdict(float)
def eq(group, label, actual, expected, tol=0.01):
    checks[group]+=1
    error=abs(float(actual)-float(expected)); maxima[group]=max(maxima[group],error)
    if error>tol: failures.append(dict(group=group,label=label,actual=actual,expected=expected,error=error))
def yes(group,label,value): eq(group,label,int(bool(value)),1,0)
def rate(key,b): return float(PARAM[key][b])
def station(b):
    total=0
    for r in BOQ:
        if r['variant']!=P['station_variant'][b] or r['scenario']!=b: continue
        q=float(r['qty']); rt=float(r['rate'])
        if r['item_id']=='it_support': total+=float(r['coverage_hours_year'])*rt*12/float(r['effective_hours_FTE_year'])
        else:
            if b!='low' and r['item_id'] in ('station_manager','transfer_coordinator','local_ops'): q=math.ceil(q)
            total+=q*rt*12
    return total
def itrate(b):
    r=next(r for r in BOQ if r['scenario']==b and r['item_id']=='it_support')
    return float(r['rate'])*12/float(r['effective_hours_FTE_year'])

def independent(v,cid,b):
    j=['low','base','high'].index(b); d=v['drivers']; ap=v['airports']
    w=1 if v['season']=='annual' else {'summer':7/12,'winter':5/12}[v['season']]
    omsdep=ap.get('OMS',{}).get('departures',0); mowdep=ap.get('MOW',{}).get('departures',0)
    nonbase=set(ap)-{'OMS','MOW'}
    # Network OMS round trips have two departures; each direct circuit has three.
    circuits=omsdep+(d['departures']-2*omsdep)/3
    crew=circuits*[0,.01,.05][j]
    affected=d['transfer_journeys']*[.002,.01,.03][j]+d['local_journeys']*[.001,.005,.015][j]
    nights=affected*IR['overnight_share_of_affected'][j]*IR['nights_per_overnight'][j]
    hublocal=API.expenses_for('OMS',v['scenario'],v['season'])['drivers']['local_journeys'] if omsdep else 0
    groups=(d['transfer_journeys']*[.002,.01,.03][j]+hublocal*[.001,.005,.015][j]/2)/40 if omsdep else 0
    q=dict(covered_aircraft_years=P['retained_fleet'][cid]*w,
      uncovered_dcs_departures=d['departures']*[0,.5,1][j],
      uncovered_outstation_months=len(nonbase)*12*w,
      uncovered_outstation_callout_departures=sum(ap[a]['departures'] for a in nonbase)*[0,.05,.2][j],
      uncovered_mow_coordination_departures=mowdep*[0,1,1][j],
      uncovered_oms_basing_aircraft_months=P['based_OMS_tails'][cid]*12*w,
      uncovered_extra_bag_services=omsdep*[0,.01,.05][j],
      uncovered_rep_workplace_services=omsdep*[0,0,1][j],
      single_room_nights=nights+4*crew,double_room_nights=0,
      uncovered_crew_person_days=4*crew,uncovered_crew_position_segments=8*crew,
      uncovered_crew_vehicle_trips=2*crew,uncovered_passenger_meals=affected*IR['meals_per_affected'][j],
      uncovered_rebooked_journeys=affected*IR['rebooking_share_of_affected'][j],
      uncovered_bus_started_hours=groups*[0,2,2][j],uncovered_meal_distribution_services=groups*[0,1,1][j])
    cost={k:float(r[b])*q[r['qty']] for k,r in PARAM.items()}
    cost['station']=station(b)*w if omsdep else 0
    cost['mow_parking']=P['based_MOW_tails'][cid]*12*w*117100*[0,1,2][j]
    return v['operating_subtotal_before_uncovered_rub']-sum(cost.values()),q,cost

R=read('calculation/results.csv'); Q=read('calculation/quantities.csv'); L=read('calculation/launch.csv')
S=read('calculation/seasonal_results.csv')
def find(rows,cid,m,b): return next(r for r in rows if (r['case_id'],r['market'],r['budget'])==(cid,m,b))
for cid in API.MAIN:
  for m in ['base','cautious']:
    v=API.expenses_for(cid,m)
    comp=v['components']; d=v['drivers']
    eq(1,cid+' included',sum(c['cost_signed_rub'] for c in comp.values()),v['included_costs_rub'])
    eq(1,cid+' subtotal',v['net_revenue_after_old_fare_forgone_rub']-v['included_costs_rub'],v['operating_subtotal_before_uncovered_rub'])
    eq(4,cid+' journeys',d['local_journeys']+d['transfer_journeys'],d['journeys'])
    eq(4,cid+' segments',d['local_journeys']+2*d['transfer_journeys'],d['segments'])
    for b in ['low','base','high']:
      r=find(R,cid,m,b); qstored=find(Q,cid,m,b); residual,q,cost=independent(v,cid,b)
      eq(1,cid+' residual '+m+'/'+b,residual,r['residual_after_recurring_rub'])
      eq(1,cid+' preinsurance',residual+cost['insurance'],r['residual_before_insurance_rub'])
      eq(1,cid+' recurring',sum(cost.values()),r['annual_or_period_recurring_rub'])
      for k,val in q.items(): eq(2,cid+'/'+k,val,qstored[k])
      eq(2,cid+' fixed months',r['fixed_months'],12)
      sr=[x for x in S if (x['case_id'],x['market'],x['budget'])==(cid,m,b)]
      for k in ['network_subtotal_rub','annual_or_period_recurring_rub','insurance_rub','residual_after_recurring_rub']:
        eq(2,cid+' seasonal sum '+k,sum(float(x[k]) for x in sr),r[k])
      if m=='base':
        eq(6,cid+' credit rate',comp['fuel_credit_rub']['unit_rate'],32930)
        eq(6,cid+' fuel stress',residual-d['fuel_t']*(32930-3024),r['residual_fuel_credit_3024_rub'])
      l=find(L,cid,m,b); j=['low','base','high'].index(b)
      totals=defaultdict(float)
      for z in ONCE:
        if z['scenario']==b and (z['item_id']=='pool_security' or ('OMS' in v['airports'] and z['item_id'].startswith(P['station_variant'][b]+'_'))):
          totals[z['ledger']]+=float(z['amount_cash'])
      it=len(set(v['airports'])-{'OMS'})*[50,100,200][j]*itrate(b)
      crew=P['working_fleet'][cid]*[0,1,2][j]*(4*(4100+rate('crew_perdiem',b)+2*rate('crew_position',b))+2*rate('crew_transfer',b))
      totals['ONEOFF_EXPENSE']+=it+crew
      basis=sum(cost[k] for k in ['oms_parking','mow_parking','outstation_sla','outstation_callout','mow_extra','oms_extra_bag','oms_rep_desk'])
      wc=basis/365*[0,15,30][j]
      for key,ledger in [('oneoff_expense_rub','ONEOFF_EXPENSE'),('CAPEX_rub','CAPEX'),('refundable_deposits_rub','REFUNDABLE_DEPOSIT')]: eq(4,cid+'/'+key,l[key],totals[ledger])
      eq(4,cid+' launch cash',l['launch_cash_rub'],sum(totals.values())+wc)
      eq(4,cid+' annual PnL not cash',l['steady_state_after_CAPEX_3y_stress_rub'],residual-totals['CAPEX']/3)

# Annual quantities already incorporate season exposure: independently inspect route rows.
for r in read('network/route_ledger.csv'):
  if r['case_id'] not in API.MAIN: continue
  weeks=(52 if r['scenario']=='base' else 48)*({'summer':7/12,'winter':5/12}[r['season']])
  eq(2,'route exposure',float(r['frequency_week_each_direction'])*2*weeks,r['departures'])
for key,val,unit in [('oms_parking',117100,'RUB/aircraft-month'),('oms_extra_bag',4450,'RUB/service'),('hotel_single',4100,'RUB/room-night')]:
  eq(2,key,rate(key,'base'),val); yes(2,key+' unit',PARAM[key]['unit']==unit)
eq(2,'IT hourly base',itrate('base'),801.4285714285714)
eq(2,'station base',station('base'),find(R,'OMS','base','base')['station_OMS_rub'])
for cid,n,tails in [('OMS',8,7),('DIRECT2',4,4),('HYBRID',10,11)]:
  r=find(R,cid,'base','base'); eq(3,cid+' unique nonbase',r['nonbase_stations'],n); eq(3,cid+' tails',r['retained_tails'],tails)
eq(3,'shared pool+office',find(L,'HYBRID','base','base')['refundable_deposits_rub'],5018000)
od=read('network/od_inventory.csv')
hubod={tuple(sorted((r['origin'],r['destination']))) for r in od if r['case_id']=='OMS'}
directod={tuple(sorted((r['origin'],r['destination']))) for r in od if r['case_id']=='DIRECT2'}
yes(4,'hub/direct nonempty disjoint OD',bool(hubod) and bool(directod) and not hubod.intersection(directod))

# Rank the supplied 50 seasonal receipts (625 combinations); no demand rerun for all.
C=read('calculation/bounded10_candidates.csv'); combos=[]
for a,b in product([r for r in C if r['season']=='summer'],[r for r in C if r['season']=='winter']):
  if max(float(a['direct_weekly_BH']),float(b['direct_weekly_BH']))<=140+1e-9:
    combos.append((float(a['HYBRID10_central_period_residual_rub'])+float(b['HYBRID10_central_period_residual_rub']),a,b))
eq(5,'combinations',25*25,625); eq(5,'feasible',len(combos),361)
combos.sort(key=lambda x:x[0],reverse=True)
# Pinned source primitives, independent orchestration (no calculation/build import).
src=ROOT/'network/source/f20000e7'; sys.path.insert(0,str(src/'src'))
import demand_model as dm
dm.TOCHNO=src/'data/raw/tochno_selected.csv.gz'
import network_model as nm
D=nm.Demand(); A=nm.load_assumptions()['base']
chains=[['MOW','GSV','MRV','MOW'],['MOW','AER','VOG','MOW']]
top=[]; cache={}
def reprice(row):
  s=row['season']; fs=(int(row['GSV_MRV_freq']),int(row['AER_VOG_freq'])); key=(s,fs)
  if key in cache: return cache[key]
  w={'summer':7/12,'winter':5/12}[s]; E=52*w
  v=API.expenses_for('OMS','base',s)
  bhweek=0; direct_before=0
  for ch,f in zip(chains,fs):
    for a,b in zip(ch,ch[1:]):
      sf,ratios=nm.season_part(a,b,A,s); km=D.km(a,b)
      leg=dict(km=km,competitive=D.has_direct(a,b),dem=D.get(a,b,'base')/104*sf,seg=D.seg(a,b,'base')/104*sf)
      carried=nm.spill_carried(leg['dem']*nm.leg_share(leg,f,A),f,ratios,A)
      migrated=min(carried,nm.rw_pax_week(a,b,A)*sf)
      bh,cost=nm.leg_cost(A,km,D.south(a,b),carried/f)
      rev,_=nm.leg_with_subsidy(D,A,a,b,f,carried,forgone_rev=2*migrated*nm.fare(A,km),season=s)
      before=(rev-2*f*cost)*E; direct_before+=before
      v['operating_subtotal_before_uncovered_rub']+=before
      v['drivers']['departures']+=2*f*E; v['drivers']['local_journeys']+=2*carried*E
      for airport in (a,b):
        v['airports'].setdefault(airport,{'departures':0})['departures']+=f*E
      bhweek+=2*f*bh
  residual,_,_=independent(v,'HYBRID10','base')
  eq(5,'reprice '+str(key),residual,row['HYBRID10_central_period_residual_rub'])
  eq(5,'BH '+str(key),bhweek,row['direct_weekly_BH'])
  cache[key]=(residual,bhweek,direct_before); return cache[key]
for score,a,b in combos[:3]:
  aa=reprice(a); bb=reprice(b)
  eq(5,'annual top3',aa[0]+bb[0],score)
  top.append(dict(GSV_summer=int(a['GSV_MRV_freq']),AER_summer=int(a['AER_VOG_freq']),GSV_winter=int(b['GSV_MRV_freq']),AER_winter=int(b['AER_VOG_freq']),residual_rub=aa[0]+bb[0],weekly_BH=[aa[1],bb[1]],direct_before_rub=aa[2]+bb[2]))
yes(5,'winner frequencies',tuple(top[0][k] for k in ['GSV_summer','AER_summer','GSV_winter','AER_winter'])==(5,6,5,6))
eq(5,'winner result',top[0]['residual_rub'],find(R,'HYBRID10','base','base')['residual_after_recurring_rub'])
for r in C:
  # Physical feasibility independently computed for ALL 50 rows without demand repricing.
  bh=sum(2*int(r[key])*nm.leg_cost(A,D.km(a,b),D.south(a,b),0)[0] for ch,key in zip(chains,['GSV_MRV_freq','AER_VOG_freq']) for a,b in zip(ch,ch[1:]))
  eq(5,'receipt physical BH',bh,r['direct_weekly_BH'])
pub=[r for r in read('network/published_allocation_comparison.csv') if r['scenario']=='base']
published=sum(float(r['published_subtotal_rub']) for r in pub)
fresh=sum(float(r['fixed_subtotal_rub']) for r in pub)
eq(7,'published rounded',round(published/1e6),113)
eq(7,'fresh direct',fresh,find(R,'DIRECT2','base','base')['network_subtotal_rub'])
eq(7,'published hybrid rounded',round((published+float(find(R,'OMS','base','base')['network_subtotal_rub']))/1e6),568)

# Hash receipts, without rebuilding or repeating prior audits.
manifest=js('calculation/input_manifest.json')
for r in manifest: yes(8,'input '+r['path'],hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'])
receipts={name:js(name)['status'] for name in ['network/validation.json','budget/validation_pass1.json','budget/validation_pass2.json','calculation/validation.json']}
for name,status in receipts.items(): yes(8,name,status=='PASS')
summary={cid:{k:float(find(R,cid,'base','base')[k]) for k in ['network_subtotal_rub','annual_or_period_recurring_rub','insurance_rub','residual_before_insurance_rub','residual_after_recurring_rub','residual_fuel_credit_3024_rub']} for cid in ['OMS','DIRECT2','HYBRID','HYBRID10']}
out=dict(status='PASS' if not failures else 'FAIL',checks_by_review_point=dict(checks),max_abs_error_by_point=dict(maxima),failures=failures,top3_independently_repriced=top,seasonal_demand_reprices=len(cache),critical_sums=summary,reused_receipts=receipts,method='Independent budget arithmetic; original source primitives for top3, receipt ranking for remaining bounded candidates; no exporter/full audit/build run',limitations='Conditional scenario only: contracts, coverage, slots, rotations, actual profit and full 2027 not proven. No independent empirical demand validation.')
(HERE/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
sys.exit(bool(failures))
