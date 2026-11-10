#!/usr/bin/env python3
"""Cash timing, alternatives, and slot readiness. Offline diagnostic axes only."""
import calendar,csv,datetime as dt,hashlib,json,math
from collections import defaultdict
from pathlib import Path
B=Path(__file__).resolve().parent; O=B/"outputs"; P=json.loads((B/"parameters.json").read_text())
read=lambda name:list(csv.DictReader((O/name).open()))
AA=list(csv.DictReader((B/"inputs/nastya/data/assumptions/network.csv").open()))
A={s:{r['parameter']:float(r[s]) for r in AA} for s in ['base','cautious']}
def write(name,rows):
    rows=list(rows)
    with (O/name).open('w',newline='') as f:
        w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def c0(s,h):
    a=A[s]
    return (a['fuel_t_per_hour']*h+a['fuel_t_per_cycle'])*a['fuel_rub_per_t']+h*(a['mro_rub_per_hour']+a['crew_rub_per_hour']+a['navigation_rub_per_hour'])+a['ground_rub_per_flight']+a['deicing_rub_per_flight']
def day(s):return dt.date.fromisoformat(s)
flights=read('dated_flights.csv'); events=[]; cash=[]
dictionary=[]
for r in read('C10_contract_thresholds.csv'):
    if r['K_probe']!='0':continue
    dictionary.append(dict(hypothesis='C10',scenario=r['scenario'],phase=r['phase'],cohorts=r['cohorts'],people=r['people_in_new_cohorts'],full_guarantee_intercept_K0=r['minimum_guarantee_return_per_person'],ordinary_indifference_intercept_Kdelta0=r['minimum_guarantee_to_beat_ordinary_return_per_person'],cost_rub_to_person_fare_slope=1/float(r['people_in_new_cohorts']),full_boundary='G >= intercept_full + K_block/people',ordinary_boundary='G >= intercept_ordinary + (K_block - K_ordinary)/people',shared_cost_rule='Same base/aircraft/donor costs in both offers cancel in the ordinary comparison; only contract delta remains',actual_K_block='UNKNOWN',actual_K_ordinary='UNKNOWN',old_grid_K_probe_interpretation='Full column: uncounted block-program K; ordinary-indifference column: differential K. These are two distinct sensitivity projections, not one adopted budget'))
write('C10_budget_envelopes.csv',dictionary)
resource=[]
groups=defaultdict(list)
for r in flights:groups[(r['hypothesis'],r['scenario'],r['network'],r['tail_slot'],r['date'])].append(r)
for (cid,scenario,network,tail,d),rr in sorted(groups.items()):
    rr.sort(key=lambda r:r['departure_utc'])
    elapsed=(dt.datetime.fromisoformat(rr[-1]['arrival_utc'])-dt.datetime.fromisoformat(rr[0]['departure_utc'])).total_seconds()/3600
    ground=[(dt.datetime.fromisoformat(b['departure_utc'])-dt.datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60 for a,b in zip(rr,rr[1:])]
    resource.append(dict(hypothesis=cid,scenario=scenario,network=network,date=d,tail_slot=tail,flight_legs=len(rr),block_hours=sum(float(r['block_hours']) for r in rr),elapsed_hours=elapsed,minimum_ground_minutes=min(ground) if ground else None,crew_duty_acceptance='UNKNOWN_NOT_INFERRED_FROM_BLOCK_HOURS',tail_availability='UNKNOWN',route_chain='-'.join([rr[0]['origin']]+[r['destination'] for r in rr])))
write('resource_calendar.csv',resource)
basefrontier=[]
for s in A:
    r=next(r for r in read('C14_full_package_thresholds.csv') if r['scenario']==s and r['K_probe']=='0')
    ferries=[x for x in flights if x['hypothesis']=='C14' and 'FERRY' in x['status']]
    saving=sum(c0(s,float(x['block_hours'])) for x in ferries)
    people=float(r['distinct_return_customers'])
    basefrontier.append(dict(hypothesis='C14',scenario=s,positioning_cost_avoidable_if_kvx_based=saving,maximum_added_kvx_base_and_foregone_offday_work_cost_vs_ferry=saving,minimum_air_return_with_kvx_base_before_base_K=float(r['minimum_air_guarantee_return_per_person'])-saving/people,kvx_resource_span_days=50,productive_days=8,offdays_require_alternative_or_parking=42,actual_base_cost='UNKNOWN',actual_offday_mission_value='UNKNOWN',condition='Base envelope includes positioning into/out of KVX, parking, crew, offday donor loss and exit; no free base'))
write('C14_base_vs_positioning.csv',basefrontier)
def event(cid,s,entity,d,amount,kind):
    events.append(dict(hypothesis=cid,scenario=s,entity=entity,date=str(d),amount_rub=amount,kind=kind,status='TIMING_FIXTURE_AT_K0_NOT_ACTUAL_CASH'))
for s in A:
    # C10 n=1 closed launch: guarantee paid in advance; retail/cost on flight day.
    r=next(r for r in read('C10_contract_thresholds.csv') if r['scenario']==s and r['phase']=='launch_closed' and r['cohorts']=='1' and r['K_probe']=='0')
    start=day(P['C10']['start']);end=start+dt.timedelta(days=28);G=float(r['minimum_corporate_guarantee_total'])
    event('C10',s,'airline',start-dt.timedelta(days=14),G,'CORPORATE_PREPAYMENT_AT_BREAK_EVEN_G')
    for d in [start,end]:
        event('C10',s,'airline',d,float(r['retail_revenue'])/2,'RETAIL_COLLECTION')
        event('C10',s,'airline',d,-float(r['airline_variable_cost'])/2,'OPERATING_PAYMENT')
    # C14 airline and tour operator are separate entities, hotel money is not RW revenue.
    r=next(r for r in read('C14_full_package_thresholds.csv') if r['scenario']==s and r['K_probe']=='0')
    people=P['C14']['cohort_people'][s];G=float(r['minimum_air_guarantee_return_per_person']);price=float(r['minimum_package_price_per_person'])
    hotelperson=14*7760*P['C14']['hotel_stress_factor'][s]
    for h in [x for x in read('C14_cohorts.csv') if x['scenario']==s]:
        d=day(h['outbound']);pay=d-dt.timedelta(days=14)
        event('C14',s,'airline',pay,people*G,'TOUR_OPERATOR_AIR_GUARANTEE')
        event('C14',s,'tour_operator',pay,people*price,'PACKAGE_COLLECTION_FROM_CUSTOMERS')
        event('C14',s,'tour_operator',pay,-people*G,'AIR_BLOCK_PAYMENT_TO_RW')
        event('C14',s,'tour_operator',d-dt.timedelta(days=30),-people*hotelperson*.5,'HOTEL_50PCT_PREPAY')
        event('C14',s,'tour_operator',d,-people*hotelperson*.5,'HOTEL_BALANCE')
        other=sum(P['C14'][k][s] for k in ['return_ground_transfer_per_person_rub','product_service_per_person_rub','protection_per_person_rub'])
        event('C14',s,'tour_operator',d,-people*other,'GROUND_SERVICE_AND_BLOCKED_PROTECTION_RESERVE')
    revdays=defaultdict(float)
    for x in read('C14_dated_seats.csv'):
        if x['scenario']!=s:continue
        d=day(x['date']);revdays[d]+=int(x['used_seats'])*A[s]['pax_cost_rub']
        event('C14',s,'airline',d,int(x['retail_people'])*float(r['airfare_reference_return'])/2,'RETAIL_COLLECTION')
    for d,v in revdays.items():
        fs=[x for x in flights if x['hypothesis']=='C14' and x['date']==str(d)]
        event('C14',s,'airline',d,-sum(c0(s,float(x['block_hours'])) for x in fs)-v,'ALL_FOUR_LEGS_OPERATING_PAYMENT')
    # C17 operating treasury, summer p70 probe, no upfront/granted support cash.
    for y in [2027,2028]:
        months={int(r['month']):r for r in read('C17_monthly_calendar.csv') if r['scenario']==s and r['year']==str(y)}
        for x in [x for x in flights if x['hypothesis']=='C17' and x['network']==f'seasonal_{y}']:
            d=day(x['date']);winter='MMK' in [x['origin'],x['destination']];summer='RGK' in [x['origin'],x['destination']]
            m=months[d.month]
            q=float(m['winter_rw_paid_segments'])/(2*int(m['winter_roundtrips'])) if winter else 70 if summer else 0
            F=A[s]['fare_fixed_rub']+A[s]['fare_per_km_rub']*1656 if winter else P['C17']['rgk_fare_rub'][s] if summer else 0
            entity=f'airline_{y}_summerp70'
            if q:event('C17',s,entity,d,q*F,'FARE_COLLECTION_ON_SERVICE_DAY')
            event('C17',s,entity,d,-c0(s,float(x['block_hours']))-q*A[s]['pax_cost_rub'],'OPERATING_PAYMENT_NO_GRANT_COLLECTION')
    # C31 at cost ceiling, L=0 is a diagnostic point, not zero actual donor value.
    r=next(r for r in read('C31_replacement_frontier.csv') if r['scenario']==s and r['demand_layer']=='nastya_primary' and r['additional_mrv_paid_each_leg_probe']=='0' and r['foregone_tu_old_mission_contribution_probe']=='0')
    d=day(P['C31']['week_start']);ceiling=float(r['maximum_tu_new_allin_cost_plus_K'])
    event('C31',s,'incremental_KEEP_comparison_L0_at_cost_ceiling',d-dt.timedelta(days=1),-ceiling,'TU_ALLIN_INVOICE_PREPAID_BEFORE_SERVICE')
    for offset in [0,3]:
        event('C31',s,'incremental_KEEP_comparison_L0_at_cost_ceiling',d+dt.timedelta(days=offset),float(r['old_ssj_mrv_variable_cost_saved'])/2,'AVOIDED_KEEP_SSJ_PAYMENT_NOT_NEW_REVENUE')
        event('C31',s,'incremental_KEEP_comparison_L0_at_cost_ceiling',d+dt.timedelta(days=offset),float(r['additional_oms_variable_contribution'])/2,'NET_NEW_OMS_SERVICE_CASH_TIMING_PROBE')
    # C35 full month block prepaid, revenue on flown service dates.
    r=next(r for r in read('C35_partner_thresholds.csv') if r['scenario']==s and r['K_probe']=='0')
    d0=day(P['C35']['start']);event('C35',s,'airline',d0-dt.timedelta(days=14),-float(r['partner_block_total_probe']),'MONTH_PARTNER_BLOCK_PREPAY')
    dd=sorted(set(x['date'] for x in flights if x['hypothesis']=='C35'))
    for d in dd:
        event('C35',s,'airline',day(d),float(r['customer_total_fare_revenue'])/len(dd),'THROUGH_FARE_COLLECTION')
        event('C35',s,'airline',day(d),-float(r['rw_pax_handling_protection_cost'])/len(dd),'HANDLING_AND_PROTECTION_RESERVE')
    # Lost old contribution is opportunity cost, not a second new-project cash payment.
    cash.append(dict(hypothesis='C35',scenario=s,entity='airline',kind='CASH_VS_ECONOMIC_DIFFERENCE',lost_previous_margin_opportunity_cost=float(r['lost_previous_own_contribution_probe']),comment='Subtract in incremental economic result; not a duplicated cash disbursement on new flights'))
for cid,s,entity in sorted(set((e['hypothesis'],e['scenario'],e['entity']) for e in events)):
    bal=0; minimum=0;agg=defaultdict(float)
    for e in events:
        if (e['hypothesis'],e['scenario'],e['entity'])==(cid,s,entity):agg[e['date']]+=e['amount_rub']
    for d in sorted(agg):bal+=agg[d];minimum=min(minimum,bal)
    cash.append(dict(hypothesis=cid,scenario=s,entity=entity,kind='TIMING_FIXTURE_K0',cash_balance_end=bal,minimum_external_funding_if_same_day_netting=-minimum,unknown_cash='K cash, tax timing, guarantees/refunds, collateral, actual payment dates and default remain UNKNOWN'))
write('cash_events.csv',events);write('cash_summary.csv',cash)

# C17 alternatives with explicit actual calendar and unknown demand.
alts=[]
for s in A:
    for y in [2027,2028]:
        ref=next(r for r in read('C17_seasonal_thresholds.csv') if r['scenario']==s and r['year']==str(y))
        annual_dates=[dt.date(y,1,1)+dt.timedelta(days=i) for i in range(366 if calendar.isleap(y) else 365)]
        annual_dates=[d for d in annual_dates if d.weekday() in [2,5]]
        positioning=[x for x in flights if x['hypothesis']=='C17' and x['network']==f'seasonal_{y}' and x['status']=='PROPOSED_FERRY']
        hpos=float(positioning[0]['block_hours']);F=P['C17']['rgk_fare_rub'][s];v=A[s]['pax_cost_rub'];h=P['C17']['rgk_block_hours_analog']
        for alternative,n in [('SUMMER_RGK_ONLY_KEEP_WINTER_OTHER',int(ref['summer_roundtrips'])),('RGK_YEAR_ROUND',len(annual_dates))]:
            fixed=2*n*c0(s,h)+2*c0(s,hpos)
            for p in [40,70,85,100]:
                alts.append(dict(hypothesis='C17',scenario=s,year=y,alternative=alternative,roundtrips=n,positioning_legs=2,paid_each_leg_probe=p,paid_segments=2*n*p,variable_contribution=2*n*p*(F-v)-fixed,break_even_people_each_leg_before_K=fixed/(2*n*(F-v)),maximum_K=2*n*p*(F-v)-fixed,actual_demand='UNKNOWN',reference='S06 historical advertised floor; not realised yield'))
write('C17_alternatives.csv',alts)

# One-slot sensitivity: calendar admission, NOT a company fleet or supply forecast.
ready=[]
for label,t in P['readiness_probes'].items():
    if label=='status':continue
    at=day(t['delivered'])+dt.timedelta(days=t['introduction_days']) if t['delivered'] else dt.date(9999,1,1)
    for s in A:
        ready.append(dict(hypothesis='C10',scenario=s,delivery_probe=label,ready_date=at,original_first_cohort='2027-01-04',original_program_can_start=at<=day('2027-01-04'),reason='Original January2027 programme needs existing donor; new H2 aircraft cannot serve earlier dates'))
        groups=[r for r in read('C14_cohorts.csv') if r['scenario']==s and day(r['outbound'])>=at]
        dd=sorted(set(r[k] for r in groups for k in ['outbound','return_date']))
        people=len(groups)*P['C14']['cohort_people'][s];retail=2*len(dd)*P['C14']['retail_people_per_kvx_mrv_leg'][s]
        core=next(r for r in read('C14_full_package_thresholds.csv') if r['scenario']==s)
        baseflights=[r for r in flights if r['hypothesis']=='C14' and r['date'] in dd]
        cost=sum(c0(s,float(r['block_hours'])) for r in baseflights)+(2*people+retail)*A[s]['pax_cost_rub']
        floor=(cost-retail*float(core['airfare_reference_return'])/2)/people if people else None
        ready.append(dict(hypothesis='C14',scenario=s,delivery_probe=label,ready_date=at,admitted_cohorts=len(groups),admitted_customers=people,admitted_roundtrips=len(dd),admitted_flight_legs=len(baseflights),block_hours=sum(float(r['block_hours']) for r in baseflights),minimum_air_return_guarantee_before_K=floor,resource_status='SSJ_COST_ANALOG_ONLY_FOR_NEW_SJ_NOT_ACCEPTED',not_launched_costs='EXIT_AND_PRECOMMITMENTS_UNKNOWN_IF_ZERO_FLIGHTS'))
        for y in [2027,2028]:
            core=next(r for r in read('C17_seasonal_thresholds.csv') if r['scenario']==s and r['year']==str(y))
            md=[r for r in read('C17_monthly_calendar.csv') if r['scenario']==s and r['year']==str(y)]
            fs=[r for r in flights if r['hypothesis']=='C17' and r['network']==f'seasonal_{y}' and r['status']=='PROPOSED' and day(r['date'])>=at]
            nm=sum(r['destination']=='MMK' or r['origin']=='MMK' for r in fs);ng=len(fs)-nm;paid=0
            for m in md:
                n=sum((r['destination']=='MMK' or r['origin']=='MMK') and day(r['date']).month==int(m['month']) for r in fs)
                if int(m['winter_roundtrips']):paid+=float(m['winter_rw_paid_segments'])*n/(2*int(m['winter_roundtrips']))
            season_ids=set('WINTER_EARLY' if day(r['date']).month<=3 else 'SUMMER' if day(r['date']).month<=9 else 'WINTER_LATE' for r in fs)
            hpos=float(next(r for r in flights if r['hypothesis']=='C17' and r['status']=='PROPOSED_FERRY')['block_hours'])
            poscost=2*len(season_ids)*c0(s,hpos)
            km=1656;Fm=A[s]['fare_fixed_rub']+A[s]['fare_per_km_rub']*km;v=A[s]['pax_cost_rub']
            wintercost=sum(c0(s,float(r['block_hours'])) for r in fs if 'MMK' in [r['origin'],r['destination']])
            summerfix=ng*c0(s,P['C17']['rgk_block_hours_analog'])
            for p in [70,100]:
                result=paid*(Fm-v)-wintercost+ng*p*(P['C17']['rgk_fare_rub'][s]-v)-summerfix-poscost
                ready.append(dict(hypothesis='C17',scenario=s,delivery_probe=label,ready_date=at,year=y,winter_roundtrips=nm//2,summer_roundtrips=ng//2,positioning_legs=2*len(season_ids),winter_paid_segments=paid,summer_paid_each_leg_probe=p,variable_contribution_before_K=result,resource_status='SSJ_COST_ANALOG_ONLY_FOR_NEW_SJ_NOT_ACCEPTED',not_launched_costs='EXIT_AND_PRECOMMITMENTS_UNKNOWN_IF_ZERO_FLIGHTS'))
for cid in ['C31','C35']:
    ready.append(dict(hypothesis=cid,delivery_probe='ALL_FOUR_NEW_AIRCRAFT_BRANCHES',resource_status='REQUIRES_EXISTING_CONFIRMED_RESOURCE_IN_EVERY_BRANCH; NO_AUTOMATIC_EXTRA_AIRCRAFT',reason='C31 two existing types; C35 partner plus existing RW rotations'))
write('slot_readiness_sensitivity.csv',ready)

items=[]
for p in sorted(O.iterdir()):
    if p.is_file() and p.name!='manifest.json':
        raw=p.read_bytes();items.append(dict(path=str(p.relative_to(B)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(O/'manifest.json').write_text(json.dumps(items,indent=2)+'\n')
print(json.dumps(dict(cash_events=len(events),alternatives=len(alts),readiness_rows=len(ready))))
