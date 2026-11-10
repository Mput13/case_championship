import calendar,csv,datetime as dt,json,math
from collections import defaultdict,Counter
from model_kernel import ROOT
p=ROOT/'runs/resource_v1';plans=json.loads((p/'plans.json').read_text());net=json.loads((ROOT/'runs/selection_v1/networks.json').read_text())
rows=[];checks=0
start=dt.datetime(2028,8,7,6,tzinfo=dt.timezone.utc)
for key,plan in plans.items():
 if plan['status']!='CONSTRUCTED_CONDITIONAL':continue
 got=Counter();n=net[key]
 for base,b in plan['bases'].items():
  for tail in range(b['working_tails']):
   total=sum(day[tail]['block'] for day in b['slots']);assert total<=70+1e-6
   for day,slots in enumerate(b['slots']):
    slot=slots[tail];assert slot['block']<=14+1e-6 and slot['elapsed']<=16+1e-6
    now=start+dt.timedelta(days=day);last=base
    for task in slot['tasks']:
     assert task['base']==base and task['airports'][0]==base and task['airports'][-1]==base
     got[task['id']]+=1
     for k,(a,z,bh) in enumerate(zip(task['airports'],task['airports'][1:],task['blocks'])):
      assert a==last;arr=now+dt.timedelta(hours=bh)
      # Export every constructed program at a clearly hypothetical week, not source observations.
      rows.append(dict(network_id=key,source_model='4a9763565f70b9ab1eddde2f5daca07687560948',scenario=n['metrics']['scenario'],network=n['metrics']['network'],route=a+'-'+z,date=str(now.date()),departure_utc=now.isoformat(),arrival_utc=arr.isoformat(),origin=a,destination=z,tail=f'{base}-{tail+1}',aircraft='SJ100_FUTURE_SSJ100_PARAMETER_ANALOG',block_hours=bh,source_status='HYPOTHETICAL_CONSTRUCTIVE_WEEK; AIRPORT_CREW_MCT_NOT_ACCEPTED',physical_airport_resolved=('MOW' not in (a,z))))
      now=arr+dt.timedelta(minutes=45);last=z;checks+=1
     assert last==base
    assert (now-(start+dt.timedelta(days=day))).total_seconds()/3600<=16+1e-6
 from dated_offer import jobs_for
 assert got==Counter({j['id']:j['freq'] for j in jobs_for(n)}),key
with (p/'dated_rotations.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
a=list(csv.DictReader((ROOT/'runs/annual_v1/annual_budget.csv').open()));months=list(csv.DictReader((ROOT/'runs/annual_v1/monthly_budget.csv').open()));res=list(csv.DictReader((ROOT/'runs/annual_v1/aircraft_calendar_daily.csv').open()))
for r in res:
 num=lambda k:int(r[k])
 assert num('received_new')==num('in_entry_new')+num('entered_new')
 assert num('entered_new')==num('planned_grounded_new')+num('reserve_new')+num('working_new')
 assert num('reserve_new')<=1 and min(num(k) for k in ('received_new','in_entry_new','entered_new','planned_grounded_new','reserve_new','working_new'))>=0
 keys=('branch','availability','scenario','network','year')
index=defaultdict(list)
for r in months:index[tuple(r[k] for k in keys)].append(r)
for r in a:
 mm=index[tuple(r[k] for k in keys)];assert len(mm)==12
 for field in ('contribution_rub','segments','journeys','support_rub','ticket_after_migration_rub','variable_cost_rub','active_days','new_received_aircraft_days','working_aircraft_days'):
  assert abs(sum(float(x[field]) for x in mm)-float(r[field]))<.001,(r,field)
for receipt in (ROOT/'inputs').glob('*/receipt.json'):
 import hashlib
 d=json.loads(receipt.read_text())
 for x in d['files']:assert hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256']
result=dict(status='PASS_OWNER_SCOPED',constructed_networks=len(plans),dated_flight_rows=len(rows),flight_location_no_overlap_and_block_checks=checks,resource_days=len(res),monthly_to_annual_identities=len(a)*9,dispatch_acceptance=False,MCT_and_saleable_transfers='NOT_CHECKED_YET; annual all-transfer money conditional',milp='Feasible integer assignments rechecked; no infeasibility claim from timeout')
(ROOT/'runs/annual_v1/semantic_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
