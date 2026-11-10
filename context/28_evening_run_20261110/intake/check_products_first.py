#!/usr/bin/env python3
"""Root intake of immutable products a391; bounded accounting/calendar checks."""
import csv
import datetime as dt
import hashlib
import io
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path

SHA = 'a39165528ceaa80f026210d0aaae9e2b541e6f51'
ROOT = 'context/28_evening_run_20261110/products/'
def blob(sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path])
def rows(name):
    return list(csv.DictReader(io.StringIO(blob(SHA, ROOT+name).decode())))
def near(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-6), (a,b)
def number(r, key):
    return float(r[key])

manifest = json.loads(blob(SHA, ROOT+'input_manifest.json'))
git_inputs = 0
for x in manifest['files']:
    b = blob(SHA, ROOT+x['path'])
    assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256']
    if x.get('commit'):
        assert b == blob(x['commit'], x['source_path'])
        git_inputs += 1
output = json.loads(blob(SHA, ROOT+'outputs/manifest.json'))
for x in output:
    b = blob(SHA, ROOT+x['path'])
    assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256']
p = json.loads(blob(SHA, ROOT+'parameters.json'))
assumptions = rows('inputs/nastya/data/assumptions/network.csv')
a = {s:{r['parameter']:float(r[s]) for r in assumptions} for s in ('base','cautious')}
od = {frozenset((r['a'],r['b'])):r for r in rows('inputs/nastya/data/processed/demand_estimates.csv')}
def km(x,y): return float(od[frozenset((x,y))]['km'])
def flight_cost(s,h):
    t=a[s]
    fuel=(t['fuel_t_per_hour']*h+t['fuel_t_per_cycle'])*t['fuel_rub_per_t']
    hour=h*sum(t[k] for k in ('mro_rub_per_hour','crew_rub_per_hour','navigation_rub_per_hour'))
    return fuel+hour+t['ground_rub_per_flight']+t['deicing_rub_per_flight']
def fare(s,x,y): return a[s]['fare_fixed_rub']+a[s]['fare_per_km_rub']*km(x,y)

flights=rows('outputs/dated_flights.csv')
assert len({r['flight_id'] for r in flights})==len(flights)
groups=defaultdict(list)
for r in flights:
    dep=dt.datetime.fromisoformat(r['departure_utc']); arr=dt.datetime.fromisoformat(r['arrival_utc'])
    near((arr-dep).total_seconds()/3600,r['block_hours'])
    assert dep==dt.datetime.fromisoformat(r['departure_local']) and arr==dt.datetime.fromisoformat(r['arrival_local'])
    assert 0<=float(r['fixture_pax'])<=float(r['seats'])
    groups[(r['hypothesis'],r['network'],r['tail_slot'])].append((dep,arr,r))
transitions=0
for fs in groups.values():
    fs.sort(key=lambda x:x[0])
    for prev,nxt in zip(fs,fs[1:]):
        assert prev[2]['destination']==nxt[2]['origin']
        assert nxt[0]-prev[1]>=dt.timedelta(minutes=45)
        transitions+=1

c10=rows('outputs/C10_contract_thresholds.csv')
for r in c10:
    s=r['scenario'];legs=2*number(r,'roundtrips');v=a[s]['pax_cost_rub']
    h=.5+km('UFA','SGC')*1.1/750
    cost=legs*flight_cost(s,h)+v*(number(r,'corporate_seat_segments')+number(r,'retail_seat_segments'))
    near(cost,r['airline_variable_cost'])
    near(number(r,'people_in_new_cohorts')*number(r,'minimum_guarantee_return_per_person')+number(r,'retail_revenue')-cost-number(r,'K_probe'),0)
    near(number(r,'corporate_seat_segments'),2*number(r,'people_in_new_cohorts'))
    expected=2*number(r,'cohorts') if r['phase']=='launch_closed' else number(r,'cohorts')
    near(r['roundtrips'],expected)

c14=rows('outputs/C14_full_package_thresholds.csv')
cohorts=rows('outputs/C14_cohorts.csv');beds=rows('outputs/C14_bed_occupancy.csv');seats=rows('outputs/C14_dated_seats.csv')
for r in c14:
    s=r['scenario']; cr=[x for x in cohorts if x['scenario']==s];br=[x for x in beds if x['scenario']==s];sr=[x for x in seats if x['scenario']==s]
    people=sum(float(x['people']) for x in cr)
    near(people,r['distinct_return_customers'])
    for b in br:
        occupied=sum(float(x['people']) for x in cr if x['outbound']<=b['date']<x['return_date'])
        near(occupied,b['occupied_beds'])
    near(max(float(x['occupied_beds']) for x in br),r['peak_beds'])
    near(sum(float(x['occupied_beds']) for x in br),r['hotel_billable_bed_days'])
    near(sum(float(x['package_people']) for x in sr),people*2)
    assert all(float(x['used_seats'])<=100 for x in sr)
    air=(number(r,'airline_variable_cost')-number(r,'retail_revenue')+number(r,'K_probe'))/people
    package=air+sum(number(r,k) for k in ('hotel_cost','ground_cost','product_service','expected_protection_probe'))/people
    near(air,r['minimum_air_guarantee_return_per_person']);near(package,r['minimum_package_price_per_person'])

c17=rows('outputs/C17_seasonal_thresholds.csv');monthly=rows('outputs/C17_monthly_calendar.csv')
for year in (2027,2028):
    dates=[dt.date(year,1,1)+dt.timedelta(days=i) for i in range((dt.date(year+1,1,1)-dt.date(year,1,1)).days)]
    winter=sum(x.month in (1,2,3,12) and x.weekday() in (2,5) for x in dates)
    summer=sum(x.month in (6,7,8,9) and x.weekday() in (2,5) for x in dates)
    for s in a:
        mr=[x for x in monthly if x['scenario']==s and int(x['year'])==year]
        near(sum(float(x['winter_all_market_directional_journeys']) for x in mr),float(od[frozenset(('PEE','MMK'))]['od_'+s]))
        for r in (x for x in c17 if x['scenario']==s and int(x['year'])==year):
            near(winter,r['winter_roundtrips']);near(summer,r['summer_roundtrips'])
            near(sum(float(x['winter_rw_paid_segments']) for x in mr),r['winter_paid_segments'])
            contribution_per_pax=number(r,'rgk_reference_oneway_fare')-a[s]['pax_cost_rub']
            threshold=number(r,'minimum_summer_paid_people_each_leg')
            residual=number(r,'full_incremental_at_probe_and_K')+(threshold-number(r,'summer_people_each_leg_probe'))*2*summer*contribution_per_pax
            near(residual,0)
            assert threshold>100

c31=rows('outputs/C31_replacement_frontier.csv')
for r in c31:
    s=r['scenario'];market=od[frozenset(('SVX','OMS'))]
    annual=float(market[('od_' if r['demand_layer']=='nastya_primary' else 'colleagues_od_')+s])
    delta=annual*a[s]['capture_competitive']*(math.exp(-2/3)-math.exp(-4/3))*7/365
    near(min(400,delta),r['additional_oms_paid_segments'])
    ceiling=number(r,'old_ssj_mrv_variable_cost_saved')+number(r,'additional_oms_variable_contribution')+number(r,'additional_mrv_revenue')-number(r,'foregone_tu_old_mission_contribution_probe')
    near(ceiling,r['maximum_tu_new_allin_cost_plus_K'])
    near(ceiling-number(r,'tu_new_allin_cost_probe'),r['full_incremental_at_probe_before_K'])
c35=rows('outputs/C35_partner_thresholds.csv');connections=rows('outputs/C35_connections.csv')
by_id={r['flight_id']:r for r in flights}
for x in connections:
    before=dt.datetime.fromisoformat(by_id[x['first_flight']]['arrival_utc']);after=dt.datetime.fromisoformat(by_id[x['second_flight']]['departure_utc'])
    near((after-before).total_seconds()/60,x['connection_minutes'])
    assert (after-before)>=dt.timedelta(minutes=90)
for r in c35:
    q=number(r,'through_oneway_journeys');block=number(r,'protected_seat_segments_each_operator')
    assert q<=block and block==160
    near(q*number(r,'customer_oneway_fare'),r['customer_total_fare_revenue'])
    available=number(r,'customer_total_fare_revenue')-number(r,'rw_pax_handling_protection_cost')-number(r,'lost_previous_own_contribution_probe')-number(r,'K_probe')
    near(available/block,r['maximum_partner_price_per_reserved_seat'])
    near(available-number(r,'partner_block_total_probe'),r['full_incremental_at_block_probe_and_K'])

result={'subject_sha':SHA,'status':'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING','checks':{'input_hashes':len(manifest['files']),'exact_git_inputs':git_inputs,'output_hashes':len(output),'dated_flights':len(flights),'within_program_tail_transitions':transitions,'C10_rows':len(c10),'C14_rows':len(c14),'C17_rows':len(c17),'C31_rows':len(c31),'C35_rows':len(c35),'C35_connections':len(connections)},'qualifications':['Full-program resource not admitted by within-program chain checks','K=0 is a threshold boundary, not zero actual costs','C10 launch and steady differ in dates and closing legs','C14 airline and complete package thresholds are different units','C17 rejection applies to the stated joint winter/summer program only','C31 signed replacement envelope is not a Tu214 cost forecast; both old assignments remain relevant','C31/C35 share OMS market and seats; do not add their independent results'],'not_run':['full independent review','live source recapture','full corporate calendar across hypotheses','actual fleet/donor/contract/budget admission','cash and readiness final still in preparation']}
Path(__file__).with_name('products_first_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
