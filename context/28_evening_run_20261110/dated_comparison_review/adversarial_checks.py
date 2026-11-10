"""In-memory counterexamples and boundary probes; original subject is untouched.

REJECTED means rejected by this independent checking criterion, unless the
entry explicitly says owner_solver. It is not a claim about owner assertions.
"""
import ast,copy,datetime as dt,json,math
from collections import defaultdict
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
import independent_checks as q

PROBES=[]
ns=dict(dt=dt,defaultdict=defaultdict,np=np,linprog=linprog,lil_matrix=lil_matrix)
tree=ast.parse((q.P/'integer_year_sales.py').read_text())
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='solve_week')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'exact-subject-solve_week','exec'),ns)
owner=ns['solve_week']

def record(name,outcome,**facts):PROBES.append(dict(name=name,result=outcome,**facts))
def reject(name,fn,**facts):
    try:fn()
    except AssertionError:record(name,'REJECTED_BY_REVIEW_ORACLE',**facts);return
    raise AssertionError('Mutation survived: '+name)

def pair(arr,dep,in_cap=10,out_cap=10):
    a=q.stamp(arr);b=q.stamp(dep)
    return [dict(flight_id='IN',origin='X',destination='H',arrival_utc=arr,departure_utc=(a-dt.timedelta(hours=1)).isoformat(),capacity_model=in_cap,local_journeys=0),dict(flight_id='OUT',origin='H',destination='Y',departure_utc=dep,arrival_utc=(b+dt.timedelta(hours=1)).isoformat(),capacity_model=out_cap,local_journeys=0)]

# Date, UTC offset, and inclusive MCT boundaries. A date carries actual duration.
for minutes,expected in [(59+59/60,0),(60,1),(180,1),(180+1/60,0)]:
    arr=dt.datetime(2027,12,31,23,30,tzinfo=dt.timezone.utc);dep=arr+dt.timedelta(minutes=minutes);fs=pair(arr.isoformat(),dep.isoformat());a=q.lp(fs,{('X','Y'):1},{('X','Y'):900},'H');b=owner(fs,{('X','Y'):1},{('X','Y'):900},'H')
    q.near(a['q'],expected);q.near(b[1],expected)
    record('MCT_'+str(minutes),'BOUNDARY_PASS',wait_minutes=minutes,expected_journeys=expected,oracle_journeys=a['q'],owner_solver_journeys=b[1],year_boundary=True)
fs=pair('2027-07-06T10:10:00+05:00','2027-07-06T11:40:00+08:00')
assert q.lp(fs,{('X','Y'):1},{('X','Y'):900},'H')['q']==0 and owner(fs,{('X','Y'):1},{('X','Y'):900},'H')[1]==0
record('UTC_offsets_false_wallclock_90','BOUNDARY_PASS',wallclock_wait_minutes=90,actual_UTC_wait_minutes=-90,oracle_and_owner_journeys=0)
fs=pair('2027-07-05T23:00:00+00:00','2027-07-08T00:30:00+00:00')
assert q.lp(fs,{('X','Y'):1},{('X','Y'):900},'H')['q']==0
record('wrong_date_same_clock','BOUNDARY_PASS',naive_clock_wait_minutes=90,actual_wait_minutes=2970,accepted_journeys=0)

# Duplicating routes must not create another market or flight inventory.
fs=pair('2027-07-05T08:00:00+00:00','2027-07-05T09:30:00+00:00')
fs.append(dict(fs[1],flight_id='OUT2'))
r=q.lp(fs,{('X','Y'):5},{('X','Y'):900},'H');o=owner(fs,{('X','Y'):5},{('X','Y'):900},'H');q.near(r['q'],5);q.near(o[1],5);q.near(r['gain'],4500)
record('duplicate_itinerary_shared_market','BOUNDARY_PASS',candidate_itineraries=2,independent_naive_sales=10,accepted_total_journeys=r['q'],owner_solver_journeys=o[1],occupied_seat_segments=2*r['q'])
fs=pair('2027-07-05T08:00:00+00:00','2027-07-05T09:30:00+00:00',10,4)
r=q.lp(fs,{('X','Y'):10},{('X','Y'):900},'H');q.near(r['q'],4)
record('each_leg_capacity','BOUNDARY_PASS',inbound_inventory=10,outbound_inventory=4,demand=10,journeys=r['q'],segments=8)
reject('double_fare_for_two_seats',lambda:q.near(2*1000-2*100+2*50,900),fare=1000,two_pax_costs=200,two_supports=100,correct_margin=900,mutant_margin=1900)
fs=pair('2027-07-05T08:00:00+00:00','2027-07-05T09:30:00+00:00')
r=q.lp(fs,{('X','Y'):5},{('X','Y'):-1},'H');q.near(r['q'],0)
record('negative_transfer_margin','BOUNDARY_PASS',available_demand=5,unit_margin=-1,accepted_journeys=0)

# Actual resource change: max/mean resource would admit a larger midweek offer.
choices=q.read('runs/integer_year_v1/weekly_choice_adjustments.csv')
example=next(r for r in choices if r['case']=='DELAY6/base_sub/OMS/2028' and r['week_start']=='2028-10-30')
ids=example['original_daily_ids'].split(' | ');larger=max(ids,key=lambda x:q.PLANS[x]['working_tails']);working=q.PLANS[larger]['working_tails'];minimum=int(example['minimum_working_available'])
reject('weekly_max_instead_of_min',lambda: q.near(max(0,working-minimum),0),case=example['case'],week=example['week_start'],daily_working=[3,5,5,5,5,5,5],mutant_selected=larger,mutant_required=working,correct_selected=example['weekly_selected_id'])
start=next(r for r in choices if r['case']=='PHASED/base_sub/OMS/2027' and r['week_start']=='2027-07-26');assert start['weekly_selected_id']=='KEEP' and start['minimum_working_available']=='0'
record('Saturday_entry_no_midweek_launch','BOUNDARY_PASS',week=start['week_start'],availability=[0,0,0,0,0,2,2],selected='KEEP',next_full_week='2027-08-02')

key=next(r['weekly_selected_id'] for r in choices if r['case']=='PHASED/base_sub/OMS/2027' and r['week_start']=='2027-12-27')
_,_,Q,U=q.value(key,2027);quota=sum(Q.values());partial=quota*5/7
reject('partial_last_year_week_times_seven',lambda:q.near(partial,quota),year=2027,week='2027-12-27',days_in_year=5,correct_source_transfer_quota=partial,mutant_quota=quota)
reject('leap_year_365_denominator',lambda:q.near(365000/365,365000/366),annual_bidirectional_OD=365000,correct_daily_both_directions=365000/366,mutant_daily=1000)
closed=q.read('runs/integer_year_v1/weekly_allocation.csv');assert not any(r['case'].split('/')[1].startswith('cautious') and q.day(r['week_start']).isocalendar().week in (2,15,28,41) for r in closed)
sample=next(r for r in closed if r['case']=='PHASED/cautious_sub/OMS/2028' and float(r['source_transfer_quota'])>0)
base=float(sample['source_transfer_quota']);recaptured=base*366/(366-28)
reject('recapture_closed_cautious_days',lambda:q.near(base,recaptured),case=sample['case'],week=sample['week_start'],correct_quota=base,mutant_quota=recaptured)

# No claim of generalized year-boundary robustness: current year-specific code
# chooses within-year minima. Current pinned calendars have matching IDs; a new
# resource event at Jan1 requires grouping both years before selection.
tree=ast.parse((q.P/'integer_year_sales.py').read_text())
weekloop=next(n for n in ast.walk(tree) if isinstance(n,ast.For) and n.lineno==84)
weekloop=copy.deepcopy(weekloop);weekloop.body=[n for n in weekloop.body if n.lineno<=90]
snippet=compile(ast.Module(body=[weekloop],type_ignores=[]),'exact-subject-weekly-selection','exec')
small='AUTHOR_52_48_CONCENTRATED/base_sub/OMS/GREEDY/cap2';large='AUTHOR_52_48_CONCENTRATED/base_sub/OMS/GREEDY/cap4'
lo=q.PLANS[small]['working_tails'];hi=q.PLANS[large]['working_tails'];assert lo<hi
chosen=[];start=dt.date(2027,12,27)
for year,dd,k,cap in [(2027,q.days(start,dt.date(2028,1,1)),small,lo),(2028,q.days(dt.date(2028,1,1),dt.date(2028,1,3)),large,hi)]:
    ns=dict(weekdates={start:dd},dayids={d:k for d in dd},branch='TEST',scenario='base_sub',plans=q.PLANS,net=q.NET,case=f'TEST/base_sub/OMS/{year}',choice_adjustments=[],resource_lookup={('TEST','14D_GROUNDING_STRESS',str(d)):{'working_new':cap} for d in dd})
    exec(snippet,ns);chosen.append(ns['choice_adjustments'][0]['weekly_selected_id'])
assert chosen==[small,large]
record('year_split_policy_limit','HELD_OUTSIDE_PINNED_INPUTS',synthetic_week='2027-12-27/2028-01-02',synthetic_daily_working=[lo]*5+[hi]*2,per_year_minima=[lo,hi],whole_week_minimum=lo,executed_owner_weekly_policy_ids=chosen,current_actual_cross_year_program_changes=0,claim='Exact supplied calendars pass; no generalized proof for a changed Jan1 delivery schedule')

# Retiming must preserve dates even at the weekly edge; test the exact helpers.
ns=dict(dt=dt)
tree=ast.parse((q.P/'synchronised_alternative.py').read_text())
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('shifted','feasible')]
exec(compile(ast.Module(body=defs,type_ignores=[]),'exact-subject-sync-date-helpers','exec'),ns)
ns['fs']=[dict(tail='T',date='2028-08-13',departure_utc='2028-08-13T23:45:00+00:00',arrival_utc='2028-08-13T23:55:00+00:00')]
assert not ns['feasible']({'T':30}) and ns['feasible']({'T':0})
record('Sunday_retime_crosses_week_boundary','OWNER_HELPER_REJECTS',shift_minutes=30,date_before='2028-08-13',date_after='2028-08-14')
ns['fs']=[dict(tail='T',date='2028-08-07',departure_utc='2028-08-07T00:15:00+00:00',arrival_utc='2028-08-07T01:15:00+00:00')]
assert not ns['feasible']({'T':-30})
record('Monday_negative_retime_crosses_boundary','OWNER_HELPER_REJECTS',shift_minutes=-30,original_date='2028-08-07')
sync=json.loads((q.P/'runs/synchronised_v1/validation.json').read_text());delta=sync['delta_before_shift_cost_and_external_loss'];before=sync['baseline_contribution_rub_week'];after=sync['alternative_contribution_rub_week'];q.near(after-before,delta)
reject('discard_internal_losing_markets',lambda:q.near(sum(max(0,float(r['delta']))*float(r['one_fare_margin']) for r in q.read('runs/synchronised_v1/market_changes.csv')),delta),correct_signed_delta=delta,losing_markets=8)
ql=50;mg=20;F=1000;S=50;v=100;fixed=10000
local=(ql-mg)*(F+S)-ql*v-fixed
q.near((local+delta)-local,delta)
reject('repeat_held_local_migration_in_sync_delta',lambda:q.near(delta,delta-mg*(F+S)),fixture_local=ql,fixture_migrated=mg,fixture_local_contribution=local,correct_transfer_only_delta=delta,mutant_delta=delta-mg*(F+S),scope='Synthetic nonzero migration; source OMS12 has zero listed local migration, external loss remains UNKNOWN')
assert sync['annual_projection']=='NOT_RUN'
record('annualize_new_week_without_dated_rerun','HELD_CLAIM',annual_projection=sync['annual_projection'],scope='No annual after-retime result exists')

# Counterfactuals from independently computed product values.
products=json.loads((q.HERE/'product_oracle_values.json').read_text());base=products['base'];cautious=products['cautious'];ceiling=base['joint_ceiling'];loss=base['own_feed_migration_loss']
reject('prorate_external_block_to_C31_week',lambda:q.near(160*3000,160*3000*7/25),reserved_seat_segments=160,correct_payment=480000,mutant_payment=134400,overstatement=345600)
reject('pay_only_sold_block_seats_cautious',lambda:q.near(480000,cautious['through_journeys']*3000),sold_journeys=cautious['through_journeys'],reserved_segments=160,correct_payment=480000,mutant_payment=cautious['through_journeys']*3000)
reject('repeat_C31_across_whole_C35_month',lambda:q.near(ceiling,4*base['C31_ceiling']+base['C35_contribution']),one_week_C31_ceiling=base['C31_ceiling'],correct_joint_ceiling=ceiling,mutant_joint_ceiling=4*base['C31_ceiling']+base['C35_contribution'])
reject('old_endpoint_demand_replaces_allmarket_inventory',lambda:q.near(85+10,5+10),protected_existing_all_market=85,new_through=10,correct_physical_occupancy=95,mutant_small_endpoint=5,mutant_total=15)
reject('commercial_LF_equals_physical_acceptance',lambda: q.near(max(0,95-85),0),physical_capacity=100,planning_limit=85,occupied=95,physical_pass=True,commercial_policy_pass=False)
reject('missing_old_Tu_donor',lambda:q.near(ceiling-1000000,ceiling),correct_at_old_Tu_loss_1m=ceiling-1000000,mutant_no_old_Tu=ceiling)
reject('duplicate_C35_own_loss_as_external_donor',lambda:q.near(ceiling,ceiling-loss),own_loss_already_in_C35=loss,correct_ceiling=ceiling,mutant_ceiling=ceiling-loss)
oldMRV=q.read('inputs/products_3889/outputs/C31_replacement_frontier.csv');r=next(r for r in oldMRV if r['scenario']=='base' and r['demand_layer']=='nastya_primary');common=float(r['old_ssj_mrv_revenue'])
reject('count_common_MRV_old_revenue_again',lambda:q.near(ceiling,ceiling+common),common_MRV_revenue_cancels=common,mutant_joint_ceiling=ceiling+common)
reject('recount_f4_as_increment_over_f2',lambda:q.near(math.exp(-2/3)-math.exp(-4/3),1-math.exp(-4/3)),correct_frequency_increment='f4 - f2',mutant='all f4 counted again')
record('signed_external_effect_and_Tu_donor','BOUNDARY_PASS',formula='delta=4,507,578.986 -101*k_shift -K_fixed +D_external; D can have either sign',joint_formula='C31_ceiling+C35-L_Tu-Tu_allin-K+other_signed_delta',old_Tu_negative_contribution=-1000000,ceiling_if_old_Tu_loss_negative=ceiling+1000000,unknown_actual_values='retained as UNKNOWN; zero values are probes')
record('internal_feed_is_separate','HELD_VARIANT',external_payment_applies_to='external-feed union only',own_feed='not in union and not charged external block')

q.write('adversarial_results.json',dict(subject='f99d6cd52dcc06995bf984fddd2f057226243b06',status='PASS',count=len(PROBES),rejected_mutations=sum(p['result']=='REJECTED_BY_REVIEW_ORACLE' for p in PROBES),probes=PROBES,scope='Synthetic in-memory changes and actual-case mutants; no original source/raw/frozen edits. Owner rejection claimed only where explicitly executed.'))
print(json.dumps(dict(probes=len(PROBES),status='PASS')))
