"""Bounded offline checks of the P03 tranche; no claim of independent review."""
import collections,csv,hashlib,json,math,subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path
P=Path(__file__).resolve().parent
def rows(n):
 with (P/n).open(newline='') as f:return list(csv.DictReader(f))
checks=[]
def check(name,ok,detail=''):
 checks.append(dict(check=name,status='PASS' if ok else 'FAIL',detail=detail))
 if not ok:raise AssertionError(name+':'+str(detail))

inputs=json.loads((P/'input_manifest.json').read_text())
for r in inputs:
 b=(P/r['local_path']).read_bytes()
 check('input_hash:'+r['path'],hashlib.sha256(b).hexdigest()==r['sha256'])
 check('exact_git_blob:'+r['path'],b==subprocess.check_output(['git','show',r['commit']+':'+r['path']]))
cal=rows('fleet_calendar.csv');airports=rows('airport_constraints.csv');mins=rows('minimum_resource_required.csv');ev=rows('diagnostic_delivery_events.csv');assumptions=rows('assumptions_register.csv');sources=rows('sources.csv')
check('fleet_calendar_unique_keys',len(cal)==len({(r['calendar_id'],r['aircraft_or_cohort_id'],r['date']) for r in cal}),len(cal))
check('airport_unique_physical_keys',len(airports)==len({r['iata'] for r in airports}) and 'MOW' not in {r['iata'] for r in airports},len(airports))
seed=rows('inputs/b4d2ddf6/context/34_full_programme_plan_20261112/city_research_seed.csv')
check('all20seeds',len(seed)==20 and {r['iata'] for r in seed}<={r['iata'] for r in airports})
check('threshold_unique_keys',len(mins)==240 and len({r['requirement_id'] for r in mins})==240)
check('forecast_unknown',all(r['delivery_forecast']=='UNKNOWN' for r in cal+mins+ev))
check('no_false_operational_acceptance',all(r['approved_project_block_hours']=='UNKNOWN' and r['schedule_acceptance']=='NOT_CHECKED' for r in cal))
check('type_families_complete',{'RRJ95_FAMILY','TU214_EXISTING','TU204_100B','B777_200ER','SJ100_PD8','TU214_NEW_DOMESTIC'}=={r['aircraft_type'] for r in cal})
crew_cal=rows('crew_calendar.csv')
check('separate_crew_calendar',len(crew_cal)==144 and len({(r['crew_pool_id'],r['date']) for r in crew_cal})==144 and all(r['resource_acceptance']=='UNKNOWN' for r in crew_cal))
check('four_branch_coverage',{'phased','partial','delayed','no_new'}=={r['delivery_scenario_id'] for r in cal})
check('early_sj_zero_handover',all(r['delivery_in_month']=='0' and r['delivered_by_period_end']=='0' for r in cal if r['aircraft_type']=='SJ100_PD8' and r['date']<'2027-07-01'))
check('no_new_zero_new_only',all(r['delivery_in_month']=='0' for r in cal if r['delivery_scenario_id']=='no_new' and r['aircraft_type'] in ['SJ100_PD8','TU214_NEW_DOMESTIC']))
check('existing_not_imputed_zero',all(r['approved_project_block_hours']=='UNKNOWN' and r['conditionally_inducted_by_period_end']=='UNKNOWN' for r in cal if r['aircraft_type']=='RRJ95_FAMILY' and r['delivery_scenario_id']=='no_new'))
check('tu_not_subject_to_sj_h2',all(r['delivery_in_month']!='0' for r in cal if r['record_kind']=='parametric_resource' and r['aircraft_type']=='TU214_NEW_DOMESTIC' and r['date']=='2027-01-01' and r['delivery_scenario_id']!='no_new'))
check('leap_month',all(r['days_in_month']=='29' for r in cal if r['date']=='2028-02-01'))

for r in [x for x in cal if x['record_kind']=='diagnostic_resource_case']:
 branch=r['delivery_scenario_id'];events=[x for x in ev if x['delivery_scenario_id']==branch]
 start=date.fromisoformat(r['date']);end=date.fromisoformat(r['period_end'])
 def intersection(s):return max(0,(end-max(start,s)).days+1)
 taildays=sum(intersection(date.fromisoformat(e['conditional_entry_date'])) for e in events)
 first=min((date.fromisoformat(e['conditional_entry_date']) for e in events),default=date(2100,1,1))
 reserve_days=intersection(first)
 check('interval_tail_days:'+r['calendar_id']+':'+r['date'],int(r['conditional_ready_aircraft_days'])==taildays and int(r['conditional_reserve_aircraft_days'])==reserve_days and int(r['screening_block_hours_before_additional_outage'])==8*(taildays-reserve_days))
check('event_h2_and_entry_lag',all(date.fromisoformat(e['handover_date'])>=date(2027,7,1) and (date.fromisoformat(e['conditional_entry_date'])-date.fromisoformat(e['handover_date'])).days==30 for e in ev))
check('diagnostic_counts_from_threshold',collections.Counter(e['delivery_scenario_id'] for e in ev)=={'phased':4,'partial':2,'delayed':4})

# Independent arithmetic on an actual eight-pair archive example, using the weighted distance sum.
archive=rows('inputs/dceadc98/data/processed/network_routes.csv')
g=[r for r in archive if r['scenario']=='base' and r['variant']=='Хаб GOJ']
sumf=sum(Decimal(r['freq_week_each_way']) for r in g)
sumfkm=sum(Decimal(r['freq_week_each_way'])*Decimal(r['km']) for r in g)
check('goj_concrete_source_sample',len(g)==8 and sumf==30 and sumfkm==34186 and all('MOW' not in [r['from'],r['to']] for r in g),{'sum_frequency_each_way':str(sumf),'weighted_km_frequency':str(sumfkm)})
h=sumf+Decimal('2.4')*sumfkm/Decimal(750)
r=next(r for r in mins if r['requirement_id']=='P03-MIN-GOJ-base-K1.2-U8')
check('goj_required_resource_threshold',h==Decimal('139.3952') and Decimal(r['block_proxy_hours_week'])==h and int(r['minimum_working_tails_hours_only'])==3 and int(r['minimum_total_tails_under_policy'])==4)
for key,group in __import__('itertools').groupby(sorted(mins,key=lambda r:(r['programme_id'],r['block_proxy_k'],float(r['screening_utilisation']))),key=lambda r:(r['programme_id'],r['block_proxy_k'])):
 a=list(group);check('more_daily_capacity_never_more_tails:'+str(key),[int(r['minimum_total_tails_under_policy']) for r in a]==sorted([int(r['minimum_total_tails_under_policy']) for r in a],reverse=True))

ready=rows('diagnostic_programme_readiness.csv')
check('phased_and_delayed_threshold_dates',all(r['first_full_threshold_date']=={'phased':'2028-05-01','delayed':'2028-10-31','partial':'NOT_REACHED_IN_DIAGNOSTIC','no_new':'NOT_REACHED_IN_DIAGNOSTIC'}[r['delivery_scenario_id']] for r in ready))
check('sourced_airport_samples',next(r for r in airports if r['iata']=='GSV')['public_parking_positions']=='21' and next(r for r in airports if r['iata']=='KUF')['runway_published_m']=='3001x45','Visually/textually reconciled with captured primary pages; no invented second runway retained.')
check('no_MRO_fraction_as_access',all(r['available_mro_capacity']=='UNKNOWN' and r['sj100_pd8_admission']=='UNKNOWN' for r in airports))

ids={r['assumption_id'] for r in assumptions};sids={r['source_id'] for r in sources}
for name in ['fleet_calendar.csv','crew_calendar.csv','airport_constraints.csv','minimum_resource_required.csv','diagnostic_delivery_events.csv','diagnostic_programme_readiness.csv','aircraft_type_parameters.csv','existing_commitments.csv']:
 for row in rows(name):
  check('assumption_refs:'+name+':'+str(len(checks)),bool(row.get('assumption_ids')) and set(row['assumption_ids'].split(';'))<=ids)
  if row.get('source_id'):check('source_refs:'+name+':'+str(len(checks)),set(row['source_id'].split(';'))<=sids,row['source_id'])
for r in sources:
 if r['local_path']:check('source_file_hash:'+r['source_id'],hashlib.sha256((P/r['local_path']).read_bytes()).hexdigest()==r['sha256'])

op=json.loads((P/'operating_rules.json').read_text());crew=op['crew_rules']
check('law381_identity_validity',crew['effective_from']=='2026-03-01' and crew['effective_to_exclusive']=='2032-03-01' and 'No139' in crew['order_points']['3'])
check('crew_cumulative_limits',crew['flight_time_limits_pt9']['ordinary_hours']=={'calendar_month':80,'calendar_quarter':240,'calendar_year':800})
# Deliberate adverse examples: aggregate hours pass while distinct real constraints fail.
check('counterexample_overlap',4<=56 and max(0,min(9,9)-max(7,7))>0,'Two flights07:00-09:00 need different simultaneous tails even with4<56weeklyhours.')
night=next(r for r in crew['minimum_flight_crew_duty_pt12_appendix1_minutes'] if r['base_report']=='22:00-06:00')
check('counterexample_night_5_landings',night['landings_5plus']==390 and 7*60>390,'Ordinary7h duty with5landings at night exceeds6h30; augmented/exception not assumed.')
check('counterexample_rest_normal_vs_minimum',14<2*10 and crew['appendix5_minimum_rest_hours'][0]['base']==12,'14h is more than minimum12h but less than normal20h; pt54 conditions required.')
check('counterexample_monthly_crew_sets',math.ceil(31*8/80)==4,'If flighttime=8h/day,31days need>=4completecrewsets by80hmonthlylimit before all other constraints.')

modified=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],text=True).splitlines()
prefix='context/35_full_programme_execution_20261112/P03/'
check('write_boundary',all(line[3:].startswith(prefix) for line in modified),[line for line in modified if not line[3:].startswith(prefix)])
result={'status':'PASS_OFFLINE_PACKAGE_CHECKS','checks_passed':len(checks),'independent_review':False,'live_operational_acceptance':'NOT_RUN','actual_RW_delivery_forecast':'UNKNOWN','actual_tail_crew_MRO_schedule':'NOT_PROVIDED','numeric_diagnostic_only':True,'check_groups':dict(collections.Counter(r['check'].split(':')[0] for r in checks)),'source_samples_checked':['GOJ8 frequencies and weighted distance','GSV21stands andKUF3001x45','law381 order identity/validity andtables'],'counterexamples_exercised':['simultaneoustailoverlap','nightduty5landings','normalrestvsconditionalminimum','monthlycrewsetlowerbound'],'not_claimed':['route payload/airspace acceptance','currentMROcertificates','contractedcapacity','crewrostercompliance','complete seasonal schedule','network economics or financial acceptance']}
(P/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
