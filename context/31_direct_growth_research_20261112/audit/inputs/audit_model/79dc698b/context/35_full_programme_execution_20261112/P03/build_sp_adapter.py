"""P03 canonical SP04/07/08 input proposal and a bounded diagnostic timetable.

No real tail registrations, availability, schedules, contracts or payments are invented.
The proposed template uses anonymous scenario units, typed nulls and explicit gates.
"""
import csv,hashlib,json,math,subprocess
from collections import Counter
from datetime import date,datetime,timedelta,timezone
from pathlib import Path

P=Path(__file__).resolve().parent
O=P/'sp_adapter';O.mkdir(exist_ok=True)
PIN='b7d74e67dd6c603db049b1915b1afec987e3b458'
P06='bc70308fe091c5767dbf26b02d06a7d750a65614'
P06_MANIFEST='bd167207beb3c59e4a3339f35922c277eac55f2adcbf501a6b056108165dd087'
OLD='d5d5b8f1651cbea66a55236e986ad9269e7966ff'
PREFIX='context/35_full_programme_execution_20261112/'
INPUTS=['schema_patch.csv','contract_addendum.json','minimal_counterexamples.csv']
def js(name,obj):(O/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
 rows=list(rows)
 with (O/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
def read(name):
 with (P/name).open(newline='') as f:return list(csv.DictReader(f))
def monthadd(d,n):
 y,m=divmod(d.year*12+d.month-1+n,12);return date(y,m+1,d.day)
def ts(d):return d.isoformat()+'T00:00:00Z'
def utc(t):return t.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

pins=[]
for name in INPUTS:
 path=PREFIX+'P00R/'+name
 b=subprocess.check_output(['git','show',PIN+':'+path])
 dest=O/'inputs'/name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(b)
 pins.append(dict(source_id='P00R_'+name,commit=PIN,path=path,sha256=hashlib.sha256(b).hexdigest(),local_path='inputs/'+name))
for name in ['producer_contract.json','examples/demo_bundle.json','README.md','output_manifest.json','engine/common.py','engine/operations.py']:
 path=PREFIX+'P06/'+name;b=subprocess.check_output(['git','show',P06+':'+path])
 dest=O/'inputs'/'P06'/name;dest.parent.mkdir(exist_ok=True,parents=True);dest.write_bytes(b)
 pins.append(dict(source_id='P06_'+name,commit=P06,path=path,sha256=hashlib.sha256(b).hexdigest(),local_path='inputs/P06/'+name))
assert hashlib.sha256((O/'inputs/P06/output_manifest.json').read_bytes()).hexdigest()==P06_MANIFEST
pins.append(dict(source_id='P03_V1_FLEET',commit=OLD,path=PREFIX+'P03/fleet_calendar.csv',sha256=hashlib.sha256(subprocess.check_output(['git','show',OLD+':'+PREFIX+'P03/fleet_calendar.csv'])).hexdigest(),local_path='../fleet_calendar.csv'))
pins.append(dict(source_id='ARCHIVE_NETWORK_ROUTES',commit='dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',path='data/processed/network_routes.csv',sha256=hashlib.sha256((P/'inputs/dceadc98/data/processed/network_routes.csv').read_bytes()).hexdigest(),local_path='../inputs/dceadc98/data/processed/network_routes.csv'))
js('input_manifest.json',pins)

assumptions=[
 dict(assumption_id='P03-A019',parameter='SP07 diagnostic day boundaries and anonymous resource units',value='UTC midnight for selected date; cohorts of1 physical-equivalent unit, not registrations',unit='date/UTC; scenario aircraft unit',selected_by='P03',basis='Preserve previous date-grain scenario and make interval joins explicit. No operator handover or real tail identity provided.',approval_status='User accepts canonical adapter proposal and diagnostics; numerical times not individually user-approved',lower='UNKNOWN',upper='UNKNOWN',range_basis='No factual range claimed',affected_conclusions='sp_adapter resource intervals and assignments',sensitivity='Shift readiness instant and rerun only intersecting assignments',refinement_method='P06 schema and actual named operator acceptance dates'),
 dict(assumption_id='P03-A020',parameter='GOJ8 ordinary-return diagnostic construction',value='u8;k1.2;ceil block time to minute;45min turn;06:00Z first flight;11-17Dec2028 selected week;weekday bin pattern explicit;100seats analogueA012;technical_blocked_seats0 only in diagnostic',unit='block h/day; factor; minute; UTC date; seats',selected_by='P03',basis='Archived30return frequencies and concrete23-bin packing; selected timetable/seat inventory are diagnostic, not demand/crew/MRO feasibility, actual RW cabin/blocked seats or seasonal extrapolation',approval_status='Diagnostic choice; no claim of RW timetable or user approval of each point',lower='UNKNOWN',upper='UNKNOWN',range_basis='u/k points inherited A002/A003; turn, weekdays and actual technical blocked seats have no established operating range',affected_conclusions='minimum working resource for this return design and dated diagnostic legs',sensitivity='Night-stop/chain, frequency, turn, block time, blocked seats and demand-day alternatives remain open',refinement_method='P02 seasonal offers/observations, P07 programme and RW cabin/ground/crew contracts'),
 dict(assumption_id='P03-A021',parameter='JSON unknown representation and P06 ownership binding',value='null plus unknown_dependencies and field status; no coercion to0; P06 bc70308fe091c5767dbf26b02d06a7d750a65614 owned fields',unit='interface convention',selected_by='P03',basis='Pinned P06 producer_contract.json; user explicitly supplied exact interface',approval_status='Protocol resolved by pinned interface; producer data acceptance remains scoped',lower='not applicable',upper='not applicable',range_basis='Protocol, not numerical uncertainty',affected_conclusions='P06 input compatibility and acceptance status',sensitivity='Reject implicit null->0 or empty-array->no-commitments conversions',refinement_method='Rebind only affected fields if coordinator accepts a changed P06 interface'),
 dict(assumption_id='P03-A022',parameter='Conditional current-resource KEEP policy and unresolved payment references',value='same resource_scenario_id and shared obligation refs in P and KEEP; actual obligations/alternative use null; provisional context cash_start2026-11 and price_year2027 for P04 binding without any imputed prices/flows',unit='policy; contract reference; month/year labels',selected_by='User contract SP08; implemented byP03',basis='SP07/SP08 accepted at b7d74e67. Named references and financial context labels are placeholders, not factual lease contracts, zero payments or a chosen inflation transfer.',approval_status='Method accepted; no internal amount/contract inferred',lower='UNKNOWN',upper='UNKNOWN',range_basis='Unknown existence, amount, avoidability and timing remain explicit',affected_conclusions='P-KEEP comparability, unused resource and payments, donor accounting',sensitivity='Additional acquisition/no-acquisition is a separate investment branch; do not subtract donor twice',refinement_method='P04 accepted economic/cash events, price/cash horizon, actual fleet/charter/lease obligations and alternative-use programme')]
for a in assumptions:a.update(source_commit=PIN,version='P03-SP-v2')
csvout('assumption_changes.csv',assumptions);js('assumption_changes.json',assumptions)
full_register=read('assumptions_register.csv')+assumptions
js('assumptions_register_v2.json',full_register);csvout('assumptions_register_v2.csv',full_register)
ids=['P03-A001','P03-A002','P03-A003','P03-A006','P03-A008','P03-A009','P03-A010','P03-A011','P03-A012','P03-A013','P03-A014','P03-A015','P03-A016','P03-A018']+[r['assumption_id'] for r in assumptions]
js('assumption_ids.json',{'inherited_ids':[x for x in ids if x not in {r['assumption_id'] for r in assumptions}],'added_ids':[r['assumption_id'] for r in assumptions],'complete_old_register':'../assumptions_register.json','changes':'assumption_changes.json'})

archive=read('inputs/dceadc98/data/processed/network_routes.csv')
legs=[r for r in archive if r['scenario']=='base' and r['variant']=='Хаб GOJ']
dist={r['to']:float(r['km']) for r in legs};freq={r['to']:int(r['freq_week_each_way']) for r in legs}
rt={a:2*(.5+dist[a]*1.2/750) for a in dist}
singles=['AER','MRV','MMK','KRR']
proof={'scope':'ONLY fixed30 ordinary same-day returns/week, each return indivisible, u8 daily block budget, k1.2 proxy. Not a lower bound for overnight/chain/retimed-frequency programmes.',
 'frequencies_each_way':freq,'roundtrip_proxy_block_hours':rt,
 'long_singletons':{'count':sum(freq[a] for a in singles),'minimum_long_plus_minimum_other':min(rt[a] for a in singles)+min(rt.values()),'reason':'All16 returns in these4markets are>5h; even shortest remaining return cannot join within8h.'},
 'CEK':{'count':3,'compatible_other_only':'UUA','CEK_plus_UUA':rt['CEK']+rt['UUA'],'CEK_plus_UFA':rt['CEK']+rt['UFA'],'CEK_plus_LED':rt['CEK']+rt['LED'],'reason':'Pair3CEK with3UUA for minimum bins; splitting them cannot reduce bins.'},
 'remaining_short':{'returns':8,'markets':'5LED+3UFA','max_returns_per_day':2,'minimum_bins':4},
 'minimum_aircraft_days_week':23,'three_working_aircraft_days_week':21,'minimum_working_tails_for_this_design':4,'policy_reserve':1,'minimum_total_under_policy':5,
 'temporal_sufficiency':'Dated template separately checked for physical adjacency, aircraft-unit overlap, turn and selected daily block limit. Actual crew, MRO, airport admission/slots and day-of-demand suitability UNKNOWN.',
 'not_a_correction_of_frozen_v1':'V1 target4 remains valid as an hours-only necessary threshold. V2 is an additional design-specific constraint.',
 'assumption_ids':['P03-A001','P03-A002','P03-A003','P03-A006','P03-A020']}
assert proof['long_singletons']['count']==16 and proof['long_singletons']['minimum_long_plus_minimum_other']>8
assert rt['CEK']+rt['UUA']<=8 and min(rt['CEK']+rt['UFA'],rt['CEK']+rt['LED'])>8
assert min(rt['LED'],rt['UFA'])*3>8
js('ordinary_return_lower_bound.json',proof)
csvout('minimum_resource_required_v2.csv',[dict(requirement_id='P03-MIN-GOJ-ORDINARY-RETURNS-V2-U8-K1.2',programme_id='ARCHIVE_GOJ8_ORDINARY_RETURN_DESIGN',record_kind='minimum_resource_required',source_commit='dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',flights_week=60,unique_airport_pairs=8,ordinary_returns_week=30,block_proxy_k=1.2,max_daily_block_hours=8,minimum_aircraft_days_week=23,maximum_days_per_working_unit_week=7,minimum_working_units=4,policy_reserve_units=1,minimum_total_units_under_policy=5,full_operational_acceptance='UNKNOWN',bound_scope='Only this indivisible same-day return design and these frequencies/block proxies; other forms remain open',assumption_id=['P03-A001','P03-A002','P03-A003','P03-A006','P03-A020'])])
csvout('variant_proposals_v2.csv',[dict(proposal_id='P03-V04',related_ids='C02;C28;C32;E02;P03-V01',proposal='Compare ordinary-return GOJ8 design against overnight/chain/retimed-frequency alternatives',evidence='P03-ED08;minimum_resource_required_v2.csv',mechanism='Ordinary returns need23aircraft-days underu8/k1.2; changing programme form or frequency changes packing and demand-day value',not_concluded='No rejection of GOJ; no claim of5total being necessary for every GOJ programme',remaining='Crew/MRO/airport/market-day/commercial and financial gates',owner_next='Coordinator/P07 programme comparison through P06')])

# Construct23 dated aircraft-days, covering30 returns. Days are selected diagnostic conditions.
bins=[
 [('AER',),('MRV',),('MMK',),('CEK','UUA')],
 [('AER',),('MRV',),('KRR',),('LED','UFA')],
 [('AER',),('MRV',),('MMK',),('CEK','UUA')],
 [('AER',),('MRV',),('KRR',),('LED','UFA')],
 [('AER',),('MRV',),('CEK','UUA')],
 [('MMK',),('KRR',),('LED','UFA')],
 [('LED','LED')]]
assert sum(len(b) for b in bins)==23
assert Counter(a for b in bins for job in b for a in job)==freq
schedule='P03_GOJ8_ORDINARY_RETURN_DIAGNOSTIC_20281211_V2'
flights=[];template_assignments=[];jobs=[]
start=date(2028,12,11)
assert start.weekday()==0
for day,daybins in enumerate(bins):
 for slot,job in enumerate(daybins,2):
  t=datetime.combine(start+timedelta(days=day),datetime.min.time(),timezone.utc)+timedelta(hours=6)
  blockmin=0
  for ri,a in enumerate(job):
   duration=math.ceil((.5+1.2*dist[a]/750)*60)
   for origin,dest in [('GOJ',a),(a,'GOJ')]:
    fid='P03D-'+t.strftime('%Y%m%dT%H%MZ')+'-'+origin+'-'+dest+'-U'+str(slot)
    arr=t+timedelta(minutes=duration)
    flights.append(dict(schedule_id=schedule,flight_instance_id=fid,operator='P03_DIAGNOSTIC_NOT_AN_OPERATED_RW_FLIGHT',flight_number='P03D'+str(len(flights)+1).zfill(3),origin_airport=origin,destination_airport=dest,departure_utc=utc(t),arrival_utc=utc(arr),local_time_zone={'origin':None,'destination':None,'status':'UNKNOWN; UTC is explicit, crew base local-time check unresolved'},aircraft_variant='SJ100_PD8',seats=100,saleable_seats=100,technical_blocked_seats=0,scheduled_status='proposed',source_status='scenario',source_period='Selected11-17Dec2028 diagnostic week; archived weekly frequencies, not annual offer forecast',assumption_id=['P03-A001','P03-A003','P03-A012','P03-A020'],source_id='ARCHIVE_NETWORK_ROUTES',diagnostic_only=True,unknown_dependencies=['airport_type_payload_slot_and_handling','actual_crew_and_MRO','demand_day_suitability','commercial_seat_commitments'],block_minutes=duration))
    template_assignments.append(dict(flight_instance_id=fid,resource_unit_index=slot,departure_utc=utc(t),arrival_utc=utc(arr),origin_airport=origin,destination_airport=dest,turn_minutes=45,crew_assignment_id=None,maintenance_release_id=None,aircraft_registration=None,assignment_status='anonymous scenario slot; not real aircraft assignment'))
    blockmin+=duration;t=arr+timedelta(minutes=45)
  jobs.append(dict(date=(start+timedelta(days=day)).isoformat(),scenario_unit_index=slot,returns=list(job),block_minutes=blockmin,elapsed_from_first_departure_to_last_arrival_minutes=int((t-timedelta(minutes=45)-(datetime.combine(start+timedelta(days=day),datetime.min.time(),timezone.utc)+timedelta(hours=6))).total_seconds()/60),actual_crew_MRO_airport_status='UNKNOWN',assumption_id=['P03-A020']))
  assert blockmin<=480
csvout('flights_sp04.csv',flights);csvout('return_template_aircraft_days.csv',jobs)
four_landing=[j for j in jobs if len(j['returns'])==2]
max_elapsed=max(j['elapsed_from_first_departure_to_last_arrival_minutes'] for j in four_landing)
js('crew_advisory.json',{'scope':'Diagnostic only; actual crew IDs, base report time, qualification, pre/post duty and rest are UNKNOWN.','four_landing_maximum_departure_to_arrival_minutes':max_elapsed,'conditional_day_report_appendix1_limit_minutes':630,'remaining_minutes_for_combined_pre_post_duty_if_ordinary_day_report':630-max_elapsed,'consequence':'A single ordinary crew for such a day may fail if preparation/postflight exceeds this headroom. Crew changes, report time and operator RPP must be checked. No crew sufficiency asserted.','normal_rest':'Law381pt50 normal rest >=2*completed duty; appendix5 minima require pt54 conditions.','source_ids':['LAW381-REGISTERED-PDF'],'assumption_ids':['P03-A020']})

H0=date(2027,1,1);H1=date(2029,1,1)
events=[];fleet=[];payments=[];opportunities=[];policies=[];contexts=[];assignments=[]
for branch in ['phased','partial','delayed','no_new']:
 rid='P03_RETURNS_V2_'+branch
 n=5 if branch in ['phased','delayed'] else 2 if branch=='partial' else 0
 for u in range(1,6):
  cid=rid+'_SCENARIO_UNIT_'+str(u).zfill(2)
  transfer=monthadd(date(2027,7,1),3*(u-1)+(6 if branch=='delayed' else 0)) if u<=n else None
  entry=transfer+timedelta(days=30) if transfer else None
  pay='P03_UNKNOWN_PAYMENT_REF_'+branch+'_'+str(u)
  opp='P03_UNKNOWN_NEW_RESOURCE_ALTERNATIVE_'+branch+'_'+str(u)
  events.append(dict(resource_scenario_id=rid,aircraft_or_cohort_id=cid,variant='SJ100_PD8',count_if_transferred=1,transfer_date=transfer.isoformat() if transfer else None,service_entry_date=entry.isoformat() if entry else None,aircraft_registration=None,identity_status='anonymous scenario resource unit; no real tail identity asserted',delivery_forecast=None,scenario_status='conditional diagnostic calendar',committed_payment_id=pay,opportunity_reference_id=opp,assumption_id=ids))
  payments.append(dict(committed_payment_id=pay,resource_scenario_id=rid,asset_or_cohort_id=cid,actual_contract_id=None,obligation_exists=None,amount=None,currency=None,payment_date_or_month=None,avoidable=None,terminal_commitments_after2028=None,scope='shared between P and KEEP when incurred; no zero payment assumed',status='unknown_reference_placeholder',source_id='SP08;P03_D04',assumption_id=['P03-A013','P03-A022']))
  opportunities.append(dict(opportunity_reference_id=opp,resource_scenario_id=rid,asset_or_cohort_id=cid,alternative_programme_id=None,alternative_value=None,status='unknown',accounting='Represent alternative in KEEP; never subtract again after P-KEEP.',assumption_id=['P03-A014','P03-A022']))
  boundaries=sorted({H0,H1}|{d for d in [transfer,entry] if d and H0<d<H1})
  for a,b in zip(boundaries,boundaries[1:]):
   ready=entry is not None and a>=entry;transferred=transfer is not None and a>=transfer
   role='reserve' if ready and u==1 else 'active' if ready else 'induction' if transferred else 'not_transferred'
   fleet.append(dict(resource_scenario_id=rid,aircraft_or_cohort_id=cid,date=a.isoformat(),variant='SJ100_PD8',count=1 if ready else 0,inventory_count_if_diagnostic_transfer=1 if transferred else 0,transfer_date=transfer.isoformat() if transfer else None,service_entry_date=entry.isoformat() if entry else None,maintenance=None,crew_available=None,reserve_role=role,location='GOJ' if ready else None,availability_interval={'start_utc':ts(a),'end_utc_exclusive':ts(b)},donor_task_id=None,committed_payment_id=pay,action_keep_add_cut_move='KEEP',opportunity_reference_id=opp,assumption_id=ids,source_status='scenario',availability_status='conditional_before_additional_outage' if ready else 'unavailable_in_selected_diagnostic',actual_aircraft_registration=None,actual_available_count=None,unknown_dependencies=['actual_crew_roster','maintenance_and_release','SJ100_PD8_airport_MRO_approval','real_contract_payments','alternative_new_resource_use'],scope='Scenario resource shared by P and KEEP; no actual tail availability asserted.'))
 policy='P03_KEEP_RETURNS_V2_'+branch
 policies.append(dict(keep_policy_id=policy,fleet_scope_id='CASE_SJ',external_scenario_id='P03_DIAGNOSTIC_EXTERNAL_V2',future_period={'start':'2027-01-01','end':'2028-12-31'},committed_fleet_calendar_id=rid,existing_flights_version=None,existing_tasks_reference='../existing_commitments.csv',alternative_new_resource_use='UNKNOWN; linked opportunity refs required in KEEP, not assumed zero',excluded_unaffected_scope=[],competitor_response_policy_id='SHARED_RESPONSE_POLICY_REQUIRED_UNKNOWN',fixed_or_adaptive='fixed',decision_date='2026-11-12',avoidable_cost_rules={'rule':'same actually committed resource/payment policy in P and KEEP','amounts':'UNKNOWN; do not zero unused-resource payments','donor':'P-KEEP counts changed old tasks once','new_acquisition':'separate investment/no-acquisition branch, not this comparison'},assumption_id=['P03-A014','P03-A022'],resource_scenario_id=rid,shared_committed_payment_ids=[x['committed_payment_id'] for x in payments if x['resource_scenario_id']==rid],unknown_dependencies=['future_existing_flights','current_fleet_commitments','alternative_new_resource_use','avoidable_costs_and_cash'],status='conditional_policy_template'))
 for arm in ['KEEP','P']:
  eid=rid+'_'+arm
  contexts.append(dict(evaluation_id=eid,programme_id='KEEP' if arm=='KEEP' else 'P03_GOJ8_RETURNS_DIAGNOSTIC',programme_version='P03-SP-v2',fleet_scope_id='CASE_SJ',external_scenario_id='P03_DIAGNOSTIC_EXTERNAL_V2',delivery_calendar_id=rid,market_version='UNKNOWN',choice_version='UNKNOWN',cost_version='UNKNOWN',response_policy_id='SHARED_RESPONSE_POLICY_REQUIRED_UNKNOWN',evaluation_mode='fixed_programme',decision_date='2026-11-12',information_set_id='P03_SNAPSHOT_20261112',keep_evaluation_id=rid+'_KEEP',input_manifest_sha256=hashlib.sha256((O/'input_manifest.json').read_bytes()).hexdigest(),resource_scenario_id=rid,keep_policy_id=policy,unknown_dependencies=['market_choice_costs','future_existing_flights','actual_resource_acceptance']))
  if arm=='P':
   for x in template_assignments:
    cid=rid+'_SCENARIO_UNIT_'+str(x['resource_unit_index']).zfill(2)
    assignments.append(dict(evaluation_id=eid,flight_instance_id=x['flight_instance_id'],schedule_id=schedule,resource_scenario_id=rid,aircraft_or_cohort_id=cid,cohort_slot_index=1,assignment_interval={'start_utc':x['departure_utc'],'end_utc':x['arrival_utc']},turn_minutes=45,origin_airport=x['origin_airport'],destination_airport=x['destination_airport'],variant='SJ100_PD8',donor_task_id=None,committed_payment_id='P03_UNKNOWN_PAYMENT_REF_'+branch+'_'+str(x['resource_unit_index']),action_keep_add_cut_move='ADD',opportunity_reference_id='P03_UNKNOWN_NEW_RESOURCE_ALTERNATIVE_'+branch+'_'+str(x['resource_unit_index']),crew_assignment_id=None,maintenance_release_id=None,aircraft_registration=None,status='proposed anonymous scenario assignment',assumption_id=['P03-A012','P03-A019','P03-A020','P03-A022']))

# Four extant families remain explicit unknown KEEP resources and obligations, never omitted as free.
existing=[]
for typ in ['RRJ95_FAMILY','TU214_EXISTING','TU204_100B','B777_200ER']:
 payment='P03_UNKNOWN_EXISTING_PAYMENT_'+typ
 existing.append(dict(aircraft_or_cohort_id='P03_UNKNOWN_EXISTING_'+typ,variant=typ,count=None,available_count=None,committed_count=None,resource_status='unknown',donor_task_id=None,committed_payment_id=payment,actual_contract_id=None,previous_tasks='Partial source snapshot in existing_commitments.csv; future dated assignments unknown',period='2027-01-01/2028-12-31',assumption_id=['P03-A014','P03-A022']))
 payments.append(dict(committed_payment_id=payment,resource_scenario_id='ALL_FUTURE_KEEP',asset_or_cohort_id='P03_UNKNOWN_EXISTING_'+typ,actual_contract_id=None,obligation_exists=None,amount=None,currency=None,payment_date_or_month=None,avoidable=None,terminal_commitments_after2028=None,scope='Existing whole business; shared obligations cannot disappear through unused capacity or exclusion from CASE_SJ growth.',status='unknown_reference_placeholder',source_id='RW-FLEET;SP08;P03_D04',assumption_id=['P03-A014','P03-A022']))

csvout('fleet_calendar_sp07.csv',fleet);csvout('assignments_sp07.csv',assignments);csvout('keep_policies_sp08.csv',policies)
csvout('committed_payment_refs.csv',payments);csvout('prior_task_refs.csv',existing)
csvout('diagnostic_resource_events_v2.csv',events)
summary=[]
for branch in ['phased','partial','delayed','no_new']:
 ev=[e for e in events if e['resource_scenario_id']=='P03_RETURNS_V2_'+branch]
 for year in [2027,2028]:
  for month in range(1,13):
   startmonth=date(year,month,1);endmonth=monthadd(startmonth,1)-timedelta(days=1)
   n=sum(e['service_entry_date'] is not None and e['service_entry_date']<=endmonth.isoformat() for e in ev)
   summary.append(dict(resource_scenario_id='P03_RETURNS_V2_'+branch,month=startmonth.strftime('%Y-%m'),conditional_ready_units_month_end=n,conditional_working_units_after_one_reserve=max(0,n-1),reserve_units=min(1,n),return_design_minimum_working_units=4,policy_total_required=5,threshold_reached_month_end=n>=5,delivery_forecast=None,actual_crew_MRO_airports='UNKNOWN',scope='Monthly scenario resource for fixed ordinary-return design; not whole-case operational acceptance',assumption_id=['P03-A006','P03-A008','P03-A009','P03-A010','P03-A011','P03-A020'] ))
csvout('diagnostic_resource_monthly_v2.csv',summary)
bundle=dict(bundle_version='P03-SP04-SP07-SP08-canonical-v2',bundle_role='Conditional diagnostic operating input; not complete financial or operational acceptance',method_contract_commit=PIN,prior_source_payload_commit=OLD,unknown_encoding={'numeric_unknown':None,'unknown_is_zero':False,'unknown_arrays':'Empty flights/assignments for factual KEEP means missing coverage, not no business; see dependencies.'},forecast={'RW_delivery_forecast':None,'status':'unknown'},horizon={'start_date':'2027-01-01','end_date':'2028-12-31'},evaluation_contexts=contexts,flights=flights,fleet_calendar=fleet,assignments=assignments,keep_policies=policies,prior_task_refs=existing,committed_payment_refs=payments,opportunity_refs=opportunities,unknown_dependencies=['Genuine P04/P05/P07 contributions to complete P06 evaluation bundles','P02 full seasonal physical flights and local time zones','Future existing flights and actual fleet/charter/lease commitments','Actual qualified crew roster and approved MRO calendar','Airport SJ100PD8 reception, payload, handling, slots and day-of-demand suitability','P04 payment/avoidable-cost/cash events and alternative new resource use','Market/choice/cost/response versions'],assumption_ids=ids,source_claims=['P03-v1 source tables unchanged','SP contract pinned at accepted commit','New arithmetic/dated template is a diagnostic, not sourced RW timetable'],operational_acceptance='UNKNOWN',financial_acceptance='NOT_EVALUATED')
js('p03_operating_bundle.json',bundle)
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def scalar_assumption_ids(x):
 if isinstance(x,list):return [scalar_assumption_ids(v) for v in x]
 if isinstance(x,dict):
  out={k:scalar_assumption_ids(v) for k,v in x.items()}
  if isinstance(out.get('assumption_id'),list):
   values=out['assumption_id'];out['assumption_id']=values[-1];out['assumption_ids']=values
  return out
 return x
manifest_for_engine=[{k:r[k] for k in ['source_id','commit','path','sha256']} for r in pins if 'source_id' in r]
engine_assumptions=[]
for r in read('assumptions_register.csv')+assumptions:
 engine_assumptions.append(dict(assumption_id=r['assumption_id'],value=r['value'],unit=r['unit'],selected_by=r['selected_by'],basis=r['basis'],approval_status=r['approval_status'],range_or_unknown={'lower':r['lower'],'upper':r['upper'],'basis':r['range_basis']},affected_conclusions=r['affected_conclusions'],sensitivity=r['sensitivity'],refinement=r.get('refinement_method')))
fragments={}
for branch in ['phased','partial','delayed','no_new']:
 rid='P03_RETURNS_V2_'+branch
 ef=[]
 for e in [x for x in events if x['resource_scenario_id']==rid]:
  entry=date.fromisoformat(e['service_entry_date']) if e['service_entry_date'] else None
  available=max(H0,min(H1,entry)) if entry else H1
  isreserve=e['aircraft_or_cohort_id'].endswith('_01')
  ef.append(dict(aircraft_id=e['aircraft_or_cohort_id'],variant='SJ100_PD8',transfer_date=ts(date.fromisoformat(e['transfer_date'])) if e['transfer_date'] else None,service_entry_date=ts(entry) if entry else None,available_from=ts(available),available_to=ts(H1),initial_location='GOJ' if entry and entry<H1 else None,turn_minutes=45,reserve_intervals=[[ts(available),ts(H1)]] if isreserve and available<H1 else [],maintenance_intervals=None,crew_windows=None,max_daily_block_hours=8,assumption_id='P03-A019',assumption_ids=ids,resource_scenario_id=rid,source_status='scenario',aircraft_identity_status='anonymous unit of explicit scenario, not a real registration',actual_aircraft_registration=None,actual_availability_status='UNKNOWN',committed_payment_id=e['committed_payment_id'],opportunity_reference_id=e['opportunity_reference_id'],empty_availability_reason='not transferred/entered within selected diagnostic horizon' if available==H1 else None,unknown_dependencies=['actual_crew_roster','approved_maintenance_calendar','SJ100_PD8_airport_MRO_and_ferry_readiness','actual_contract_payments','alternative_new_resource_use']))
 ep=[]
 for f in flights:
  x=dict(f);x['assumption_ids']=x['assumption_id'];x['assumption_id']='P03-A020';x['physical_adjacent_leg']=True;x['distance_km']=dist[x['destination_airport'] if x['origin_airport']=='GOJ' else x['origin_airport']];x['project_network']=True;ep.append(x)
 ea=[]
 for a in [x for x in assignments if x['resource_scenario_id']==rid]:
  ea.append(dict(flight_instance_id=a['flight_instance_id'],aircraft_id=a['aircraft_or_cohort_id'],crew_id=None,action='add',assumption_id='P03-A020',assumption_ids=a['assumption_id'],actual_aircraft_registration=None,committed_payment_id=a['committed_payment_id'],opportunity_reference_id=a['opportunity_reference_id']))
 kp=next(dict(x) for x in policies if x['resource_scenario_id']==rid)
 kp.update(future_period=['2027-01','2028-12'],resource_policy='Same conditionally available/committed scenario resource in P and KEEP; real payments remain even when unused.',existing_business='Future whole affected existing business UNKNOWN; existing_commitments.csv is partial history, not zero future flights.',assumption_ids=kp['assumption_id'],assumption_id='P03-A022')
 pair={}
 for arm in ['P','KEEP']:
  ctx=next(dict(x) for x in contexts if x['evaluation_id']==rid+'_'+arm)
  ctx.update(period_start='2027-01',period_end='2028-12',cash_start='2026-11',price_year=2027,affected_scope_id='WHOLE_AFFECTED_RW_SCOPE_UNKNOWN_PENDING_PROGRAMME',input_manifest_sha256=digest(manifest_for_engine))
  pair['project' if arm=='P' else 'keep']=dict(context=ctx,input_manifest=manifest_for_engine,flights=ep if arm=='P' else [],fleet_calendar=ef,assignments=ea if arm=='P' else [],keep_policy=kp,resource_operators=['P03_DIAGNOSTIC_NOT_AN_OPERATED_RW_FLIGHT'],assumptions=engine_assumptions,committed_payment_refs=[x for x in payments if x['resource_scenario_id'] in [rid,'ALL_FUTURE_KEEP']],prior_task_refs=existing,unknown_dependencies=bundle['unknown_dependencies'],producer_coverage={'P03_owned_fields':'mapped to pinned P06-v0.1; source/availability gates remain conditional','other_bundle_required_fields':'omitted for P04/P05/P07 ownership; this is a fragment, not a zero-filled full evaluation bundle','future_KEEP_flights':'UNKNOWN; empty fragment array does not mean no existing/alternative business'},operational_acceptance='UNKNOWN',financial_acceptance='NOT_EVALUATED')
 fragments[branch]=scalar_assumption_ids(pair)
 assert digest(pair['project']['fleet_calendar'])==digest(pair['keep']['fleet_calendar']) and digest(pair['project']['keep_policy'])==digest(pair['keep']['keep_policy'])
js('p06_producer_fragments.json',{'interface_commit':P06,'interface_manifest_sha256':P06_MANIFEST,'role':'P03-owned fragments; merge actual P04/P05/P07 inputs before full evaluate/compare/scenario. No toy economics or demand values copied.', 'branches':fragments})
js('interface_contract.json',{'status':'P06-owned field adapter bound to pinned early interface; complete bundle acceptance NOT_RUN','pinned_method_contract':PIN,'pinned_P06_interface':P06,'P06_interface_manifest_sha256':P06_MANIFEST,'preferred_P06_input':'p06_producer_fragments.json; branches[name].project/keep contain owned fields only','tables':['flights SP04','fleet_calendar SP07','assignments SP07','keep_policies SP08','prior_task_refs','committed_payment_refs','opportunity_refs'],'intervals':'Canonical event intervals are half-open UTC; P06 aircraft objects have available_from/to, explicit transfer/service entry and initial position. Counts remain shared scenario stock, not additive daily arrivals.','identity':'Anonymous explicit scenario aircraft_id, equivalent to cohort size1; never real aircraft registrations. No actual tail data provided.','field_states':'null numeric unknown plus explicit dependencies. Canonical count is selected conditional capacity; actual_available_count remains null.','maintenance_crew':'P06 maintenance_intervals and crew_windows stay null; assignment crew_id null. They are not filled with toy windows or empty maintenance arrays. check_operations must retain CONDITIONAL.','assignment_status':'Proposed in P; actual future KEEP flight assignments missing, not empty business.','same_resource_policy':'Each P and KEEP pair shares the exact fleet_calendar, keep_policy and committed_payment_refs. Alternative use/prices unresolved; no additional donor deduction after P-KEEP.','investment_policy':'Acquiring a different fleet only in P requires a separately named investment/no-acquisition context.','primary_key':'P06 fleet aircraft_id; assignment flight_instance_id; flights flight_instance_id; P and KEEP are separate evaluation contexts.','temporal_template':'60 directed dated adjacent flights,8physicalpairs,23aircraftdays,4anonymousworkingunits; one separate reserve; demand/crew/MRO/airport/financial gates unresolved.','legacy_uua':'UUA remains archived airport-code input; source city-label/airport/type suitability must be verified. No city or airport substitution performed.','integration_trigger':'Merge genuine P04/P05/P07 contributions; do not call complete financial evaluate/compare on this partial producer fragment.'})

clarifications=[dict(question_id='P03-Q02',source='User supplied pinned P06 bc70308fe091c5767dbf26b02d06a7d750a65614',quote='producer_contract.json; examples/demo_bundle.json; README.md; null is UNKNOWN',interpretations='engine-native fields and P03 fragment ownership established',temporary_recommendation='Use p06_producer_fragments.json; no implicit zero or invented aircraft registrations',affected='SP adapter only; source tranche unchanged',continuing_work='dated diagnostic template; return-design lower bound; KEEP/payment references',status='RESOLVED_PINNED_P06_INTERFACE',answer='Exact P06 interface copied and verified; only P03-owned fields instantiated, other owners remain missing rather than toy-filled',recalculation_scope='adapter fields and affected input checks only',coordination='t3_thread_send mode=auto delivered')]
csvout('clarification_requests.csv',clarifications)
js('evidence_delta.json',[dict(delta_id='P03-ED08',kind='new calculation/design constraint; no new market collection',subject='GOJ8 ordinary same-day returns underu8/k1.2',result='23aircraft-days/week -> at least4working; +1reserve policy=5. Existing hours-only4 preserved separately.',bounds='This is not a proof for other programme forms or complete sufficiency for current schedule; crew/MRO/airport/demand-day gates unknown.',source='ordinary_return_lower_bound.json',assumption_ids=['P03-A001','P03-A002','P03-A003','P03-A006','P03-A020']),dict(delta_id='P03-ED09',kind='accepted methodology interface adaptation',subject='SP04/SP07/SP08',result='Dated physical legs and anonymous scenario aircraft_id; shared P/KEEP resource/payment refs; null means UNKNOWN; bound to P06 bc70308.',bounds='Owned fields bound to pinned P06; complete economic bundle and real tail/crew/contract data not supplied.',source='p06_producer_fragments.json',assumption_ids=['P03-A019','P03-A021','P03-A022'])])
print(json.dumps({'flights':len(flights),'assignments':len(assignments),'resource_intervals':len(fleet),'return_aircraft_days':len(jobs),'new_assumptions':len(assumptions),'diagnostic_target':5}))
