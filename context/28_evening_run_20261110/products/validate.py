#!/usr/bin/env python3
"""Owner cross-check of saved outputs; does not import the calculation code.
Recomputes conservation, boundaries and cash reconciliations. Not an independent
review and not market/flight/resource acceptance.
"""
import calendar,csv,datetime as dt,hashlib,json,math
from pathlib import Path
from collections import defaultdict
B=Path(__file__).resolve().parent; O=B/'outputs'; checks=[]
read=lambda n:list(csv.DictReader((O/n).open()))
f=lambda r,k:float(r[k])
def ok(name,cond):
    checks.append(dict(check=name,passed=bool(cond)))
    if not cond:raise AssertionError(name)
def eq(name,a,b,tol=1e-6):ok(name,math.isclose(a,b,rel_tol=1e-10,abs_tol=tol))
P=json.loads((B/'parameters.json').read_text())
for p,h in [('inputs/nastya/data/assumptions/network.csv','8f49f98ea47e0b7a6db5476a67c7556baf6e28e2019d6fb1f3b1361196146012'),('inputs/nastya/src/network_model.py','f069cc79cf0c0d3958e135d1ef7bb4f7b3fa4e6cac117098805d1f20a3743e26')]:
    ok('provided immutable author hash '+p,hashlib.sha256((B/p).read_bytes()).hexdigest()==h)
for r in read('C10_contract_thresholds.csv'):
    n=f(r,'cohorts');corp=f(r,'corporate_seat_segments');ret=f(r,'retail_seat_segments');fare=f(r,'reference_oneway_fare');cost=f(r,'airline_variable_cost');K=f(r,'K_probe');people=f(r,'people_in_new_cohorts')
    eq('C10 one fare per used segment',f(r,'corporate_revenue_at_reference'),corp*fare)
    eq('C10 break-even guarantee',people*f(r,'minimum_guarantee_return_per_person')+ret*fare-cost-K,0)
    eq('C10 ordinary indifference',people*f(r,'minimum_guarantee_to_beat_ordinary_return_per_person')+ret*fare-cost-K,f(r,'ordinary_same_flights_variable_contribution'))
    eq('C10 closed launch number flights',f(r,'roundtrips'),n*(2 if r['phase']=='launch_closed' else 1))
    ok('C10 unknown stays unknown',r['actual_contract_revenue']=='UNKNOWN' and r['actual_full_result']=='UNKNOWN')
for s in ['base','cautious']:
    rr=[r for r in read('C14_cohorts.csv') if r['scenario']==s];q=P['C14']['cohort_people'][s]
    ok('C14 six distinct cohorts '+s,len(rr)==len({r['cohort'] for r in rr})==6)
    for r in rr:eq('C14 actual date interval', (dt.date.fromisoformat(r['return_date'])-dt.date.fromisoformat(r['outbound'])).days,14)
    bed=[r for r in read('C14_bed_occupancy.csv') if r['scenario']==s]
    eq('C14 occupied bedday sum '+s,sum(f(r,'occupied_beds') for r in bed),6*q*14)
    eq('C14 overlap peak '+s,max(f(r,'occupied_beds') for r in bed),2*q)
    ss=[r for r in read('C14_dated_seats.csv') if r['scenario']==s]
    eq('C14 each person consumes two seats '+s,sum(f(r,'package_people') for r in ss),12*q)
    ok('C14 never oversell '+s,all(f(r,'used_seats')<=100 for r in ss))
    for r in [r for r in read('C14_full_package_thresholds.csv') if r['scenario']==s]:
        people=f(r,'distinct_return_customers')
        eq('C14 airline full budget boundary',people*f(r,'minimum_air_guarantee_return_per_person')+f(r,'retail_revenue')-f(r,'airline_variable_cost')-f(r,'K_probe'),0)
        eq('C14 package total does not drop hotel',people*f(r,'minimum_package_price_per_person'),f(r,'airline_variable_cost')-f(r,'retail_revenue')+sum(f(r,k) for k in ['hotel_cost','ground_cost','product_service','expected_protection_probe','K_probe']))
for y in [2027,2028]:
    dd=[dt.date(y,1,1)+dt.timedelta(days=i) for i in range(366 if calendar.isleap(y) else 365)]
    for s in ['base','cautious']:
        rr=[r for r in read('C17_monthly_calendar.csv') if r['scenario']==s and r['year']==str(y)]
        eq('C17 annual OD conserved '+str(y)+s,sum(f(r,'winter_all_market_directional_journeys') for r in rr),f(rr[0],'mmk_annual_model_od'))
        eq('C17 actual winter dates',sum(f(r,'winter_roundtrips') for r in rr),sum(d.month in [1,2,3,12] and d.weekday() in [2,5] for d in dd))
        eq('C17 actual summer dates',sum(f(r,'summer_roundtrips') for r in rr),sum(d.month in [6,7,8,9] and d.weekday() in [2,5] for d in dd))
        r=next(r for r in read('C17_seasonal_thresholds.csv') if r['scenario']==s and r['year']==str(y) and r['K_probe']=='0')
        ok('C17 bounded recipe rejection '+str(y)+s,f(r,'minimum_summer_paid_people_each_leg')>100)
        eq('C17 saved winter sold sum',sum(f(x,'winter_rw_paid_segments') for x in rr),f(r,'winter_paid_segments'))
for r in read('C31_replacement_frontier.csv'):
    expected=f(r,'old_ssj_mrv_variable_cost_saved')+f(r,'additional_mrv_revenue')+f(r,'additional_oms_variable_contribution')-f(r,'foregone_tu_old_mission_contribution_probe')
    eq('C31 signed two-old-mission budget',f(r,'maximum_tu_new_allin_cost_plus_K'),expected)
    eq('C31 budget less new Tu cost',f(r,'full_incremental_at_probe_before_K'),expected-f(r,'tu_new_allin_cost_probe'))
    ok('C31 no assumed available Tu',r['actual_tu_tail']=='UNKNOWN')
for r in read('C31_two_aircraft_resource.csv'):
    ok('C31 one TLV RT insufficient / two fit block-only', (f(r,'first_week_resource_balance')>=0)==('2RT' in r['old_tu_mission']))
    ok('C31 block hours not resource acceptance',r['resource_admitted']=='False')
for r in read('C35_partner_thresholds.csv'):
    Q=f(r,'through_oneway_journeys');F=f(r,'customer_oneway_fare');block=f(r,'protected_seat_segments_each_operator');K=f(r,'K_probe')
    eq('C35 one fare not two',f(r,'customer_total_fare_revenue'),Q*F)
    eq('C35 full block paid including empty',f(r,'partner_block_total_probe'),block*3000)
    eq('C35 prorate boundary',block*f(r,'maximum_partner_price_per_reserved_seat')+f(r,'rw_pax_handling_protection_cost')+f(r,'lost_previous_own_contribution_probe')+K,Q*F)
    eq('C35 net new RW pax',f(r,'incremental_rw_passenger_segments'),Q-f(r,'own_cannibalised_journeys_probe'))
    ok('C35 partner still unconfirmed',r['actual_partner']=='UNCONFIRMED')
ok('C35 counterexample block20 would displace locals',85+20>100 and 85+10<=100)
for r in read('C35_connections.csv'):eq('C35 both waits exact',f(r,'connection_minutes'),90)

# Check complete multi-day tail chains, not only day-one equality.
chains=defaultdict(list)
for r in read('dated_flights.csv'):chains[(r['hypothesis'],r['network'],r['tail_slot'])].append(r)
for key,rr in chains.items():
    rr.sort(key=lambda r:r['departure_utc'])
    for a,b in zip(rr,rr[1:]):
        ok('tail location continuity '+b['flight_id'],a['destination']==b['origin'])
        ok('tail UTC gap '+b['flight_id'],dt.datetime.fromisoformat(b['departure_utc'])-dt.datetime.fromisoformat(a['arrival_utc'])>=dt.timedelta(minutes=45))
for d in ['2027-07-05','2027-07-08']:
    fs=read('dated_flights.csv')
    old=next(r for r in fs if r['hypothesis']=='C31' and r['network']=='KEEP_SSJ_MRV' and r['date']==d and r['destination']=='SVX')
    new=next(r for r in fs if r['hypothesis']=='C31' and r['network']=='ADD_SSJ_OMS' and r['date']==d and r['destination']=='SVX')
    ok('C31 new SSJ task within same freed dates and home-return window '+d,dt.datetime.fromisoformat(new['arrival_utc'])<=dt.datetime.fromisoformat(old['arrival_utc']))
for r in read('cash_summary.csv'):
    if r['kind']!='TIMING_FIXTURE_K0':continue
    if r['hypothesis'] in ['C10','C14','C31']:eq('cash closes at priced zero with prepayment '+r['hypothesis']+r['scenario']+r['entity'],f(r,'cash_balance_end'),0,1e-5)
    if r['hypothesis']=='C17':
        y=r['entity'].split('_')[1]
        x=next(x for x in read('C17_seasonal_thresholds.csv') if x['scenario']==r['scenario'] and x['year']==y and x['K_probe']=='0' and x['summer_people_each_leg_probe']=='70')
        eq('C17 operating cash same accrual under same-day collection fixture',f(r,'cash_balance_end'),f(x,'full_incremental_at_probe_and_K'),1e-5)
    if r['hypothesis']=='C35':
        x=next(x for x in read('C35_partner_thresholds.csv') if x['scenario']==r['scenario'] and x['K_probe']=='0')
        eq('C35 new programme cash vs lost KEEP margin',f(r,'cash_balance_end')-f(x,'lost_previous_own_contribution_probe'),f(x,'variable_incremental_contribution_at_block_probe'))
for s in ['base','cautious']:
    rr=[r for r in read('slot_readiness_sensitivity.csv') if r['hypothesis']=='C14' and r['scenario']==s]
    counts={r['delivery_probe']:int(r['admitted_cohorts']) for r in rr}
    ok('C14 four readiness consequences '+s,counts==dict(on_time_H2_2027=6,partial_late_2027=1,delayed_H2_2028=0,no_new_aircraft=0))
report={'passed':len(checks),'total':len(checks),'independent_review':'NOT_RUN','scope':'owner cross-check of arithmetic/calendar/cash only','checks':checks}
(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
# Refresh owner output receipt including this validation, preserving no external verdict.
items=[]
for p in sorted(O.iterdir()):
    if p.is_file() and p.name!='manifest.json':
        raw=p.read_bytes();items.append(dict(path=str(p.relative_to(B)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(O/'manifest.json').write_text(json.dumps(items,indent=2)+'\n')
print(json.dumps(dict(passed=len(checks),independent_review='NOT_RUN')))
