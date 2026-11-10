"""Dated readiness/maintenance, fixed-offer annual exposure and signed budget boundaries."""
import calendar,csv,datetime as dt,hashlib,json,math
from collections import defaultdict
from model_kernel import ROOT,load,metrics,nm
from dated_offer import revalue
OUT=ROOT/'runs/annual_v1';OUT.mkdir(parents=True,exist_ok=True)
net=json.loads((ROOT/'runs/selection_v1/networks.json').read_text())
plans=json.loads((ROOT/'runs/resource_v1/plans.json').read_text())
D,AS=load()
def dump(name,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def addmonths(d,m):
 y=d.year+(d.month-1+m)//12;mo=(d.month-1+m)%12+1
 return dt.date(y,mo,min(d.day,calendar.monthrange(y,mo)[1]))
batches=[('2027-07-01',3),('2027-10-01',1),('2028-04-01',2),('2028-07-01',2)]
branches={'PHASED':(0,False),'PARTIAL_FIRST4':(0,True),'DELAY3':(3,False),'DELAY6':(6,False),'DELAY12':(12,False),'NO_NEW':(0,False)}
tails=[]
for branch,(delay,partial) in branches.items():
 if branch=='NO_NEW':continue
 idx=0
 for date,count in (batches[:2] if partial else batches):
  received=addmonths(dt.date.fromisoformat(date),delay)
  for k in range(count):
   idx+=1;ready=received+dt.timedelta(days=30)
   tails.append(dict(branch=branch,tail=f'{branch}-SJ_ANALOG-{idx:02d}',received=received,ready=ready,maintenance_start=addmonths(ready,12)+dt.timedelta(days=14*k),maintenance_end=addmonths(ready,12)+dt.timedelta(days=14*(k+1))))
resource=[];resource_lookup={}
for branch in branches:
 bt=[t for t in tails if t['branch']==branch]
 for availability in ('NO_SCHEDULED_GROUNDING','14D_GROUNDING_STRESS'):
  date=dt.date(2027,1,1)
  while date<=dt.date(2028,12,31):
   received=sum(t['received']<=date for t in bt);entered=sum(t['ready']<=date for t in bt)
   grounded=sum(t['maintenance_start']<=date<t['maintenance_end'] for t in bt) if availability.startswith('14D') else 0
   serviceable=entered-grounded;reserve=min(1,serviceable);working=serviceable-reserve
   r=dict(branch=branch,availability=availability,date=str(date),received_new=received,in_entry_new=received-entered,entered_new=entered,planned_grounded_new=grounded,reserve_new=reserve,working_new=working,company_total_entered='LEGACY_ENTERED(t) + entered_new',legacy_existing_duties='PRESERVED_IN_KEEP_NOT_AVAILABLE_TO_PROJECT_BY_DEFAULT',actual_RW_delivery_status='SCENARIO_NOT_CONFIRMED')
   resource.append(r);resource_lookup[(branch,availability,str(date))]=r;date+=dt.timedelta(days=1)
# Fixed offer revaluation: calendar-year OD divided by actual calendar weeks, then exposure integrated by date.
valuations=[];offers={};seen=set()
for key,plan in plans.items():
 n=net[key];m=n['metrics']
 sig=(m['scenario'],m['network'],tuple((j['a'],j['b'],j['freq']) for j in (list(n['result'][0].values()) if m['kind']=='HUB' else [l for t in n['result'] for l in t[8]])))
 if sig in seen:continue
 seen.add(sig)
 for year in (2027,2028):
  days=366 if calendar.isleap(year) else 365;A,r=revalue(n,D,days);mm=metrics(m['kind'],m['network'],A,r)
  transfer_increment=0.
  if m['kind']=='HUB':
   for x,y,km,t in r[1]:
    transfer_increment+=2*t*(nm.fare(A,km)*A['transfer_fare_factor']+nm.sub(A,m['network'],x)+nm.sub(A,m['network'],y)-2*A['pax_cost_rub'])*A['weeks_per_year']
  mm.update(id=key,scenario=m['scenario'],year=year,constructed_working=plan['working_tails'],reserve=1,source_program_count=m['program_count'],local_only_no_refill_contribution_rub_year=mm['contribution_rub_year']-transfer_increment,all_transfer_increment_rub_year=transfer_increment,calendar_basis='UNIFORM_ANNUAL_OD_ACTUAL_365_OR_366_DAY_DENOMINATOR',connection_acceptance='UNKNOWN_UNTIL_DATED_MCT_AND_INVENTORY_CHECK',fixed_offer=True)
  valuations.append(mm);offers[(key,year)]=mm
# Explicit four closed calendar weeks for cautious are diagnostic, not historical kover durations.
def closed(date):
 year=date.year
 return any(dt.date.fromisocalendar(year,w,1)<=date<dt.date.fromisocalendar(year,w,1)+dt.timedelta(days=7) for w in (2,15,28,41))
monthly=[];intervals=[];annual=[];gates=[]
for branch in branches:
 for avail in ('NO_SCHEDULED_GROUNDING','14D_GROUNDING_STRESS'):
  for scenario in AS:
   for family in ('OMS','KUF','UFA','REN','GOJ','DIRECT'):
    for year in (2027,2028):
     candidates=[x for x in valuations if x['year']==year and x['scenario']==scenario and x['network']==family and x['constructed_working'] is not None]
     date=dt.date(year,1,1);end=dt.date(year,12,31);sums=defaultdict(float);mons={};cur=None
     while date<=end:
      rr=resource_lookup[(branch,avail,str(date))];lost=closed(date) if scenario.startswith('cautious') else False
      eligible=[x for x in candidates if x['constructed_working']<=rr['working_new'] and x['model_city_pairs']<=12]
      # Final 8-12 candidates first; a smaller program is explicitly a pilot if no final fits.
      finals=[x for x in eligible if x['model_8_12_pair_gate']]
      pool=finals or eligible
      chosen=max(pool,key=lambda x:(x['contribution_rub_year'],-x['constructed_working'])) if pool and not lost else None
      status=('FINAL_8_12_CONDITIONAL' if chosen['model_8_12_pair_gate'] else 'PILOT_NOT_FINAL_CASE') if chosen else ('DIAGNOSTIC_CLOSED_WEEK' if lost and rr['working_new'] else 'KEEP_NO_NEW_WORKING_RESOURCE')
      # Required-program flow and its full-budget headroom are retained even when negative.
      ident=chosen['id'] if chosen else 'KEEP';tag=(ident,status)
      if cur is None or cur['tag']!=tag:
       if cur:cur['end_exclusive']=str(date);intervals.append({k:v for k,v in cur.items() if k!='tag'})
       cur=dict(branch=branch,availability=avail,scenario=scenario,network=family,year=year,start=str(date),end_exclusive=None,selected_id=ident,status=status,tag=tag)
      month=str(date)[:7]
      if month not in mons:mons[month]=defaultdict(float)
      for s in (sums,mons[month]):
       s['calendar_days']+=1;s['new_received_aircraft_days']+=rr['received_new'];s['new_entered_aircraft_days']+=rr['entered_new'];s['new_grounded_aircraft_days']+=rr['planned_grounded_new'];s['new_reserved_aircraft_days']+=rr['reserve_new']
       if chosen:
        denom=366 if calendar.isleap(year) else 365
        for field in ('ticket_before_migration_rub_year','foregone_ticket_rub_year','ticket_after_migration_rub_year','support_rub_year','variable_cost_rub_year','contribution_rub_year','journeys_year','segments_year','transfer_journeys_year','migrated_segments_year','net_added_segments_listed_keep_only','local_only_no_refill_contribution_rub_year','all_transfer_increment_rub_year'):
         s[field.replace('_year','')]+=chosen[field]/denom
        s['active_days']+=1;s['working_aircraft_days']+=chosen['constructed_working'];s['allocated_reserve_days']+=1;s['final_gate_days']+=int(chosen['model_8_12_pair_gate']);s['pilot_days']+=int(not chosen['model_8_12_pair_gate'])
        s['block_hours_equivalent']+=chosen['block_hours_week']/7;s['flights_equivalent']+=chosen['flights_week']/7
        s['unallocated_working_aircraft_days']+=rr['working_new']-chosen['constructed_working']
        s['economic_KEEP_days_before_excluded_costs']+=int(chosen['contribution_rub_year']<=0)
       else:s['keep_days']+=1;s['unallocated_working_aircraft_days']+=rr['working_new']
      date+=dt.timedelta(days=1)
     if cur:cur['end_exclusive']=str(end+dt.timedelta(days=1));intervals.append({k:v for k,v in cur.items() if k!='tag'})
     def finish(s):
      for field in ('ticket_before_migration_rub','foregone_ticket_rub','ticket_after_migration_rub','support_rub','variable_cost_rub','contribution_rub','journeys','segments','transfer_journeys','migrated_segments','net_added_segments_listed_keep_only','local_only_no_refill_contribution_rub','all_transfer_increment_rub','active_days','keep_days','final_gate_days','pilot_days','working_aircraft_days','allocated_reserve_days','block_hours_equivalent','flights_equivalent','economic_KEEP_days_before_excluded_costs'):
       s[field]+=0
      out=dict(s);c=s['contribution_rub'];sub=s['support_rub'];ticket=s['ticket_after_migration_rub'];c0=c-sub;tr=s['all_transfer_increment_rub']
      out.update(full_delta_pnl=None,full_company_pnl=None,peak_cash=None,excluded_cost_headroom_if_external_donor_delta_zero=c,external_signed_donor_delta_required_if_K_zero=max(0.,-c),support_fraction_for_variable_zero=(sub-c)/sub if sub>0 else None,support_fraction_with_K_D='(K_excluded-D_external-C_without_support)/S_model',transfer_realization_fraction_for_variable_zero=-s['local_only_no_refill_contribution_rub']/tr if tr>0 else None,all_in_cost_formula='DeltaPnL = C + D_external - K_excluded; no second net VAT deduction',whole_company_formula='P_or_PnL_KEEP_domestic(t)+KEEP_international(t)+KEEP_charter(t)+signed_project_delta(t)',economic_action='CONDITIONAL_LAUNCH_ONLY_IF_KminusD_LE_HEADROOM' if c>0 else 'KEEP_UNLESS_NAMED_POSITIVE_DONOR_OR_VALID_ADDITIONAL_SUPPORT',support_policy='OWNER_PASSENGER_RATE_SHADOW_ONLY' if scenario.endswith('_sub') else 'NO_SUPPORT',actual_future_support_rub=None,flow_grain='DATED_ACTIVE_DAY_EXPOSURE_OF_FIXED_WEEKLY_OFFER; not sold bookings or dated transfer acceptance')
      return out
     common=dict(branch=branch,availability=avail,scenario=scenario,network=family,year=year)
     annual.append(common|finish(sums))
     monthly.extend(common|{'month':month}|finish(vals) for month,vals in mons.items())
dump('aircraft_calendar_daily.csv',resource)
dump('fixed_offer_year_values.csv',valuations)
dump('program_intervals.csv',intervals)
dump('annual_budget.csv',annual)
dump('monthly_budget.csv',monthly)
dump('delivery_cohorts.csv',[{k:str(v) if isinstance(v,dt.date) else v for k,v in t.items()} for t in tails])
for r in annual:
 assert abs(r['ticket_after_migration_rub']+r['support_rub']-r['variable_cost_rub']-r['contribution_rub'])<1e-4
 assert abs(r['segments']-r['journeys']-r['transfer_journeys'])<1e-6
 assert r['active_days']+r['keep_days']==r['calendar_days']
 if r['branch']=='NO_NEW':assert r['active_days']==0 and r['contribution_rub']==0
(OUT/'validation.json').write_text(json.dumps({'status':'PASS_OWNER_SCOPED','resource_daily_rows':len(resource),'annual_rows':len(annual),'monthly_rows':len(monthly),'program_intervals':len(intervals),'fixed_offer_values':len(valuations),'cash':'UNKNOWN_DATED_PAYMENT_TIMES_NOT_GIVEN','future_actual_fleet':'UNKNOWN_SCENARIO_N_ONLY','dispatch':'CONSTRUCTIVE_ROTATIONS_ONLY_NO_AIRPORT_CREW_OR_TRANSFER_ACCEPTANCE','no_new_branch':'KEEP_EXISTING_NETWORK_NO_UNNAMED_DONOR; C33/C31 require exact packages'},indent=2)+'\n')
print('annual rows',len(annual),'intervals',len(intervals),flush=True)
for r in annual:
 if r['availability']=='14D_GROUNDING_STRESS' and r['scenario']=='base_sub' and r['network'] in ('OMS','KUF','DIRECT') and r['branch'] in ('PHASED','PARTIAL_FIRST4','DELAY6','NO_NEW'):
  print(r['branch'],r['network'],r['year'],r['active_days'],round(r['contribution_rub']/1e6,3),r['final_gate_days'],flush=True)
