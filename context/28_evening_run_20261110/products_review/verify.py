#!/usr/bin/env python3
"""Independent, bounded, offline review. Reads exact Git objects; never runs owner code.
Writes only next to this file. Reproduce: python3 <this file>.
"""
import calendar, csv, datetime as dt, hashlib, io, json, math, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

SUBJECT='388908b6da3539484cb8e2e03ada6ff5cb2204a4'
OLD='a39165528ceaa80f026210d0aaae9e2b541e6f51'
SOURCE='38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b'
RECEIPT='13f7c373954cc16b33a53b7c46436ee3f15f753b'
PREFIX='context/28_evening_run_20261110/products/'
HERE=Path(__file__).resolve().parent
USED={}; CHECKS=[]; EXAMPLES={}; MUTATIONS=[]

def blob(path, commit=SUBJECT, full=False):
    path=path if full else PREFIX+path
    raw=subprocess.check_output(['git','show',commit+':'+path],cwd=HERE)
    USED[(commit,path)]={'commit':commit,'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return raw

def js(path,**kw): return json.loads(blob(path,**kw))
def rows(path): return list(csv.DictReader(io.StringIO(blob(path).decode())))
def out(name): return rows('outputs/'+name+'.csv')
def F(row,key): return float(row[key])
def date(s): return dt.date.fromisoformat(s)
def eachday(a,b): return [a+dt.timedelta(days=i) for i in range((b-a).days+1)]
def year_days(y): return eachday(dt.date(y,1,1),dt.date(y,12,31))
def check(name,cond,detail=None):
    CHECKS.append({'name':name,'passed':bool(cond),**({'detail':detail} if detail is not None else {})})
    if not cond: raise AssertionError(name+': '+str(detail))
def close(name,actual,expected): check(name,math.isclose(float(actual),float(expected),rel_tol=1e-10,abs_tol=1e-5),{'actual':float(actual),'expected':float(expected)})
def mutation(name,valid,wrong,consequence):
    check('counterexample differs: '+name,not math.isclose(valid,wrong,rel_tol=1e-10,abs_tol=1e-5))
    MUTATIONS.append({'mutation':name,'correct':valid,'wrong':wrong,'error':wrong-valid,'consequence':consequence})

# Integrity independently calculated from Git, not owner verifier.
delivery=js('delivery_manifest.json'); im=js('input_manifest.json')
paths=subprocess.check_output(['git','ls-tree','-r','--full-tree','--name-only',SUBJECT,'--',PREFIX],cwd=HERE).decode().splitlines()
check('complete delivery inventory',set(x[len(PREFIX):] for x in paths if x!=PREFIX+'delivery_manifest.json')=={r['path'] for r in delivery['files']})
for r in delivery['files']:
    b=blob(r['path']);check('delivery '+r['path'],hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes'])
exact=0
for r in im['files']:
    b=blob(r['path']);check('input hash '+r['path'],hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes'])
    if r.get('commit'):
        check('exact copied Git input '+r['path'],b==blob(r['source_path'],r['commit'],True));exact+=1
for r in js('outputs/manifest.json'):
    b=blob(r['path']);check('output hash '+r['path'],hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes'])
MONEY=['C10_contract_thresholds','C14_full_package_thresholds','C17_seasonal_thresholds','C31_replacement_frontier','C35_partner_thresholds']
for n in MONEY: check('old money bytes preserved '+n,blob('outputs/'+n+'.csv')==blob('outputs/'+n+'.csv',OLD))
receipt=js('context/28_evening_run_20261110/evidence_review/handoff.json',commit=RECEIPT,full=True)
source_report=blob('context/28_evening_run_20261110/evidence_review/report.md',RECEIPT,True).decode()
check('source receipt exact subject and boundary',receipt['reviewed_sha']==SOURCE and receipt['verdict']=='APPROVE_SCOPED' and receipt['acceptance_boundary']=='Exact source handoff only; no market/economics/2027award/freefleet acceptance.')
P=js('parameters.json')
AR=rows('inputs/nastya/data/assumptions/network.csv')
A={s:{r['parameter']:float(r[s]) for r in AR} for s in ['base','cautious']}
DR=rows('inputs/nastya/data/processed/demand_estimates.csv')
D={frozenset((r['a'],r['b'])):r for r in DR}

def demand(a,b,s): return float(D[frozenset((a,b))]['od_'+s])
def km(a,b): return float(D[frozenset((a,b))]['km'])
def fare(a,b,s): return A[s]['fare_fixed_rub']+A[s]['fare_per_km_rub']*km(a,b)
def hours(a,b,south=False): return .5+km(a,b)*(1.2 if south else 1.1)/750
# Express cost as one cycle plus one block-hour slope; no imports from owner.
def fixed(s,h):
    p=A[s]
    cycle=p['fuel_t_per_cycle']*p['fuel_rub_per_t']+p['ground_rub_per_flight']+p['deicing_rub_per_flight']
    slope=p['fuel_t_per_hour']*p['fuel_rub_per_t']+sum(p[k] for k in ['crew_rub_per_hour','mro_rub_per_hour','navigation_rub_per_hour'])
    return cycle+h*slope

def capture(s,f,kind='competitive'): return A[s]['capture_'+kind]*(-math.expm1(-f/3))
FL=out('dated_flights');C10=out(MONEY[0]);C14=out(MONEY[1]);C17=out(MONEY[2]);C31=out(MONEY[3]);C35=out(MONEY[4])
# C10 derive service days and returning cohorts separately.
for r in C10:
    s=r['scenario'];n=int(r['cohorts']);q=P['C10']['corporate_people'][s];ret=P['C10']['retail_people_per_leg'][s]
    starts=[date(P['C10']['start'])+dt.timedelta(days=i*28//n) for i in range(n)]
    ends=[d+dt.timedelta(days=28) for d in starts]
    legs=2*n if r['phase']=='steady28' else 2*len(set(starts+ends))
    costs=legs*fixed(s,hours('UFA','SGC'))+(2*n*q+legs*ret)*A[s]['pax_cost_rub']
    retail=legs*ret*fare('UFA','SGC',s);g=(costs+F(r,'K_probe')-retail)/(n*q)
    close('C10 legs from cohort returns',2*F(r,'roundtrips'),legs)
    close('C10 total costs',F(r,'airline_variable_cost'),costs)
    close('C10 full G',F(r,'minimum_guarantee_return_per_person'),g)
    span=28 if r['phase']=='steady28' else (max(ends)-min(starts)).days+1
    ordinary=min(100*legs,demand('UFA','SGC',s)*span/365*capture(s,(legs/2)*7/span))
    margin=ordinary*(fare('UFA','SGC',s)-A[s]['pax_cost_rub'])-legs*fixed(s,hours('UFA','SGC'))
    close('C10 ordinary sold',F(r,'ordinary_same_flights_model_paid_segments'),ordinary)
    close('C10 ordinary G delta envelope',F(r,'minimum_guarantee_to_beat_ordinary_return_per_person'),g+margin/(n*q))
    close('C10 contribution',F(r,'full_incremental_at_reference_and_K'),n*q*2*fare('UFA','SGC',s)+retail-costs-F(r,'K_probe'))
for r in out('C10_budget_envelopes'):
    people=F(r,'people'); slope=F(r,'cost_rub_to_person_fare_slope')
    close('C10 independent envelope slope',slope,1/people)
    check('C10 signed differential K disclosed','K_block - K_ordinary' in r['ordinary_boundary'])
r=next(r for r in C10 if r['scenario']=='base' and r['cohorts']=='1' and r['phase']=='launch_closed' and r['K_probe']=='0')
EXAMPLES['C10']={'base_launch_G':F(r,'minimum_guarantee_return_per_person'),'base_steady_G':F(C10[0],'minimum_guarantee_return_per_person'),'four_cohort_last_return':max(f['date'] for f in FL if f['hypothesis']=='C10' and f['network']=='launch4'),'January_new_H2_aircraft_admitted':False}
mutation('C10 omit empty launch legs',F(r,'minimum_guarantee_return_per_person'),F(C10[0],'minimum_guarantee_return_per_person'),'Underprices finite closed launch')
ordinary0=F(r,'minimum_guarantee_to_beat_ordinary_return_per_person');people=F(r,'people_in_new_cohorts')
mutation('C10 charge shared donor twice in ordinary comparison',ordinary0,ordinary0+3e6/people,'K_block=K_ordinary=3m cancels; only differential K belongs here')

# Inspect actual launched load fixtures rather than trusting a total-flight count.
for n in [1,2,4]:
    depdays=[date(P['C10']['start'])+dt.timedelta(days=j*28//n) for j in range(n)]
    backdays=[d+dt.timedelta(days=28) for d in depdays]
    fs=[f for f in FL if f['hypothesis']=='C10' and f['network']=='launch'+str(n)]
    check('C10 exact finite dated service set '+str(n),{f['date'] for f in fs}=={str(d) for d in depdays+backdays} and len(fs)==4*n)
    for f in fs:
        corporate=(f['origin']=='UFA' and date(f['date']) in depdays) or (f['origin']=='SGC' and date(f['date']) in backdays)
        close('C10 launch/closing real flight load',F(f,'fixture_pax'),15+(80 if corporate else 0))

# C14 use individual hotel-night/customer records and all four legs each operating day.
CO=out('C14_cohorts');BED=out('C14_bed_occupancy');SEAT=out('C14_dated_seats')
for s in A:
    cohorts=[r for r in CO if r['scenario']==s];q=P['C14']['cohort_people'][s];ret=P['C14']['retail_people_per_kvx_mrv_leg'][s]
    dates=sorted(set(date(r[k]) for r in cohorts for k in ['outbound','return_date']));people=6*q
    check('C14 exact six dates '+s,[r['outbound'] for r in cohorts]==[(dt.date(2027,11,1)+dt.timedelta(days=7*i)).isoformat() for i in range(6)])
    for r in cohorts: close('C14 fourteen nights',(date(r['return_date'])-date(r['outbound'])).days,14)
    for r in BED:
        if r['scenario']==s:
            occupied=sum(q for c in cohorts if date(c['outbound'])<=date(r['date'])<date(c['return_date']))
            close('C14 actual daily occupied beds',F(r,'occupied_beds'),occupied)
    close('C14 peak beds',max(F(r,'occupied_beds') for r in BED if r['scenario']==s),2*q)
    close('C14 package seat conservation',sum(F(r,'package_people') for r in SEAT if r['scenario']==s),2*people)
    for r in C14:
        if r['scenario']!=s: continue
        fcost=16*fixed(s,hours('SVX','KVX'))
        ac=16*fixed(s,hours('KVX','MRV',True))+fcost+(2*people+16*ret)*A[s]['pax_cost_rub']
        hotel=people*14*7760*P['C14']['hotel_stress_factor'][s]
        other=people*sum(P['C14'][k][s] for k in ['return_ground_transfer_per_person_rub','product_service_per_person_rub','protection_per_person_rub'])
        air=(ac-16*ret*fare('KVX','MRV',s)+F(r,'K_probe'))/people
        close('C14 all legs cost',F(r,'airline_variable_cost'),ac)
        close('C14 hotel',F(r,'hotel_cost'),hotel)
        close('C14 air boundary',F(r,'minimum_air_guarantee_return_per_person'),air)
        close('C14 full package',F(r,'minimum_package_price_per_person'),air+(hotel+other)/people)
        close('C14 all block hours',F(r,'block_hours'),16*(hours('SVX','KVX')+hours('KVX','MRV',True)))
        check('C14 hotel2027 unknown',r['hotel_quote_2027']=='UNKNOWN')
    b=next(x for x in out('C14_base_vs_positioning') if x['scenario']==s)
    close('C14 base ceiling equals real ferry saving',F(b,'positioning_cost_avoidable_if_kvx_based'),fcost)
    rr=next(r for r in C14 if r['scenario']==s and r['K_probe']=='0')
    EXAMPLES['C14_'+s]={'air_G':F(rr,'minimum_air_guarantee_return_per_person'),'package':F(rr,'minimum_package_price_per_person'),'peak_beds':2*q,'ferry_cost':fcost,'hotel_total':hotel}
    mutation('C14 omit 16 ferry legs '+s,F(rr,'minimum_air_guarantee_return_per_person'),F(rr,'minimum_air_guarantee_return_per_person')-fcost/people,'Requires real base/donor budget instead of hiding delivery flights')

# C17 actual calendars incl leap year; all twelve months retain annual OD.
MONTH=out('C17_monthly_calendar')
for y in [2027,2028]:
    winter=[d for d in year_days(y) if d.month in [1,2,3,12] and d.weekday() in [2,5]]
    summer=[d for d in year_days(y) if d.month in [6,7,8,9] and d.weekday() in [2,5]]
    check('C17 true calendar '+str(y),len(winter)==35 and len(summer)==35)
    for s in A:
        dr=D[frozenset(('PEE','MMK'))];w={m:calendar.monthrange(y,m)[1]*(float(dr['winter_factor']) if m in [12,1,2] else float(dr['summer_factor']) if m in [6,7,8] else 1) for m in range(1,13)}
        wm=0
        for m in range(1,13):
            row=next(r for r in MONTH if r['year']==str(y) and r['scenario']==s and r['month']==str(m));nr=sum(d.month==m for d in winter)
            alloc=demand('PEE','MMK',s)*w[m]/sum(w.values());sold=alloc*capture(s,2,'open') if nr else 0
            close('C17 monthly annual-OD allocation',F(row,'winter_all_market_directional_journeys'),alloc)
            close('C17 monthly sales',F(row,'winter_rw_paid_segments'),sold)
            close('C17 monthly winter dates',F(row,'winter_roundtrips'),nr);wm+=sold
        close('C17 annual OD conservation',sum(F(r,'winter_all_market_directional_journeys') for r in MONTH if r['year']==str(y) and r['scenario']==s),demand('PEE','MMK',s))
        vm=wm*(fare('PEE','MMK',s)-A[s]['pax_cost_rub'])-70*fixed(s,hours('PEE','MMK'))
        for r in C17:
            if r['year']!=str(y) or r['scenario']!=s: continue
            seasonal=vm+70*(F(r,'summer_people_each_leg_probe')*(P['C17']['rgk_fare_rub'][s]-A[s]['pax_cost_rub'])-fixed(s,P['C17']['rgk_block_hours_analog']))-6*fixed(s,hours('SVX','PEE'))
            needed=(70*fixed(s,P['C17']['rgk_block_hours_analog'])+6*fixed(s,hours('SVX','PEE'))+F(r,'K_probe')-vm)/(70*(P['C17']['rgk_fare_rub'][s]-A[s]['pax_cost_rub']))
            close('C17 full year contribution',F(r,'full_incremental_at_probe_and_K'),seasonal-F(r,'K_probe'))
            close('C17 summer threshold',F(r,'minimum_summer_paid_people_each_leg'),needed)
            check('C17 selected no-support recipe infeasible',needed>100 and r['summer_actual_demand']=='UNKNOWN')
        r=next(r for r in C17 if r['year']==str(y) and r['scenario']==s and r['K_probe']=='0')
        EXAMPLES['C17_'+str(y)+'_'+s]={'winter_rt':len(winter),'summer_rt':len(summer),'winter_sold':wm,'winter_margin':vm,'summer_needed_per_flight':F(r,'minimum_summer_paid_people_each_leg')}
        mutation('C17 move all annual winter OD into operated months '+str(y)+s,wm,demand('PEE','MMK',s)*capture(s,2,'open'),'Annual OD must retain non-operating month share')
check('C17 PEE-RGK absent not zero',frozenset(('PEE','RGK')) not in D)

# C31 derive the entire before/after delta from both old assignments, no Tu profit invented.
for r in C31:
    s=r['scenario'];q=P['C31']['old_ssj_paid_people_each_leg'][s];v=A[s]['pax_cost_rub'];L=F(r,'foregone_tu_old_mission_contribution_probe')
    annual=demand('SVX','OMS',s) if r['demand_layer']=='nastya_primary' else float(D[frozenset(('SVX','OMS'))]['colleagues_od_'+s])
    qnew=annual*(capture(s,4)-capture(s,2))*7/365
    newoms=qnew*(fare('SVX','OMS',s)-v)-4*fixed(s,hours('SVX','OMS'))
    saved=4*(fixed(s,hours('SVX','MRV',True))+q*v)
    extra=4*F(r,'additional_mrv_paid_each_leg_probe')*fare('SVX','MRV',s)
    ceiling=saved+newoms+extra-L
    close('C31 shared market delta f4-f2',F(r,'additional_oms_paid_segments'),qnew)
    close('C31 saved SSJ full avoidable cost',F(r,'old_ssj_mrv_variable_cost_saved'),saved)
    close('C31 both old missions cost ceiling',F(r,'maximum_tu_new_allin_cost_plus_K'),ceiling)
    close('C31 allin Tu probe',F(r,'full_incremental_at_probe_before_K'),ceiling-F(r,'tu_new_allin_cost_probe'))
    check('C31 free Tu not assumed',r['actual_tu_tail']=='UNKNOWN' and r['actual_tu_cost']=='UNKNOWN')
for r in out('C31_two_aircraft_resource'):
    released=23 if '2RT' in r['old_tu_mission'] else 11.5
    close('C31 TLV donor release',F(r,'old_tu_hours_released'),released)
    close('C31 first week balance',F(r,'first_week_resource_balance'),released-19.2)
    check('C31 not resource admission',r['resource_admitted']=='False')
for s in A:
    r=next(r for r in C31 if r['scenario']==s and r['demand_layer']=='nastya_primary' and r['additional_mrv_paid_each_leg_probe']=='0' and r['foregone_tu_old_mission_contribution_probe']=='0')
    EXAMPLES['C31_'+s]={'new_oms_segments':F(r,'additional_oms_paid_segments'),'ceiling_Tu_plus_L_plus_K':F(r,'maximum_tu_new_allin_cost_plus_K')}
    mutation('C31 omit 3m donor contribution '+s,F(r,'maximum_tu_new_allin_cost_plus_K')-3e6,F(r,'maximum_tu_new_allin_cost_plus_K'),'Would admit Tu cost despite loss of old TLV mission')

# C35 protected inventory, single journey fare, per-leg variable costs and opportunity margin.
INT=out('addendum_C35_internal_KEEP')
for r in C35:
    s=r['scenario'];v=A[s]['pax_cost_rub'];dd=[d for d in eachday(date(P['C35']['start']),date(P['C35']['end'])) if d.weekday() in [1,4]]
    inv=2*len(dd)*10;gross=demand('IJK','OMS',s)*capture(s,2,'transfer')*25/365;Q=min(inv,gross)
    price=fare('IJK','OMS',s)*A[s]['transfer_fare_factor'];lost=Q*P['C35']['own_cannibalised_fraction_probe'][s]*5000
    var=Q*(v+P['C35']['journey_handling_rub'][s]+P['C35']['expected_disruption_cost_rub_per_journey_probe'][s])
    close('C35 reserved not sold',F(r,'protected_seat_segments_each_operator'),inv)
    close('C35 model journeys capped by block',F(r,'through_oneway_journeys'),Q)
    close('C35 one customer fare',F(r,'customer_total_fare_revenue'),Q*price)
    close('C35 external full reserved block',F(r,'partner_block_total_probe'),inv*3000)
    close('C35 external price ceiling',F(r,'maximum_partner_price_per_reserved_seat'),(Q*price-var-lost-F(r,'K_probe'))/inv)
    check('C35 partner unknown',r['actual_partner']=='UNCONFIRMED')
    for a in [a for a in INT if a['scenario']==s and F(a,'K_probe')==F(r,'K_probe')]:
        p=price if a['fare_case']=='original_no_support_fare' else min(price,8382)
        expected=Q*p-Q*(2*v+P['C35']['journey_handling_rub'][s]+P['C35']['expected_disruption_cost_rub_per_journey_probe'][s])-lost
        close('C35 internal one fare',F(a,'customer_total_fare_revenue'),Q*p)
        close('C35 internal two occupied seat segments',F(a,'rw_used_seat_segments'),2*Q)
        close('C35 internal K ceiling with two pax costs',F(a,'maximum_integration_retime_risk_K'),expected)
        close('C35 internal after K',F(a,'full_incremental_at_probe_and_K'),expected-F(a,'K_probe'))
        check('C35 internal no partner or added flight grant',F(a,'external_partner_payment')==0 and F(a,'additional_subsidy_from_new_flights')==0)
        check('C35 per-leg local capacity',F(a,'retained_local_people_each_leg_fixture')+F(a,'offered_seat_block_per_leg')<=F(a,'total_aircraft_seats_each_leg'))
for s in A:
    r=next(r for r in C35 if r['scenario']==s and r['K_probe']=='0');a=next(a for a in INT if a['scenario']==s and a['fare_case']=='original_no_support_fare' and F(a,'K_probe')==0)
    ceiling=F(a,'maximum_integration_retime_risk_K');q=F(a,'through_oneway_journeys');revenue=F(a,'customer_total_fare_revenue')
    EXAMPLES['C35_'+s]={'external_price_ceiling':F(r,'maximum_partner_price_per_reserved_seat'),'sold_journeys':q,'reserved_block':160,'internal_K':ceiling,'internal_capped_K':F(next(a for a in INT if a['scenario']==s and F(a,'K_probe')==0 and a['fare_case']!='original_no_support_fare'),'maximum_integration_retime_risk_K')}
    mutation('C35 collect fare twice '+s,ceiling,ceiling+revenue,'Same traveler pays one journey fare')
    mutation('C35 omit second-leg passenger cost '+s,ceiling,ceiling+q*A[s]['pax_cost_rub'],'Two own flight legs consume two per-passenger costs')
    mutation('C35 add external and internal alternative '+s,ceiling,ceiling+F(r,'variable_incremental_contribution_at_block_probe'),'Same endpoint journeys and OMS seats sold twice; mutually exclusive feed mode')
    if s=='cautious': mutation('C35 pay only sold partner seats',480000,q*3000,'Guaranteed 160-seat block is prepaid even when only 46.33 journeys sell')

# Flight timestamps: IANA offsets, route continuity, all days, 45-min ground windows.
Z={'UFA':'Asia/Yekaterinburg','SGC':'Asia/Yekaterinburg','SVX':'Asia/Yekaterinburg','KVX':'Europe/Kirov','MRV':'Europe/Moscow','PEE':'Asia/Yekaterinburg','RGK':'Asia/Barnaul','MMK':'Europe/Moscow','OMS':'Asia/Omsk','IJK':'Europe/Samara','ZIA':'Europe/Moscow','TLV':'Asia/Jerusalem'}
chains=defaultdict(list)
for r in FL:
    dep=dt.datetime.fromisoformat(r['departure_local']);arr=dt.datetime.fromisoformat(r['arrival_local'])
    close('flight block duration '+r['flight_id'],(arr-dep).total_seconds()/3600,F(r,'block_hours'))
    for point,t,utcfield in [(r['origin'],dep,'departure_utc'),(r['destination'],arr,'arrival_utc')]:
        check('IANA offset '+r['flight_id']+point,t.utcoffset()==t.astimezone(ZoneInfo(Z[point])).utcoffset())
        check('UTC identity '+r['flight_id']+utcfield,t==dt.datetime.fromisoformat(r[utcfield]))
    if r['fixture_pax']!='':check('flight inventory fixture '+r['flight_id'],0<=F(r,'fixture_pax')<=F(r,'seats'))
    else:check('unknown flight sales not zero '+r['flight_id'],r['fixture_pax_status']=='UNKNOWN_NOT_ZERO')
    chains[(r['hypothesis'],r['network'],r['tail_slot'])].append(r)
for k,rr in chains.items():
    rr.sort(key=lambda r:r['departure_utc'])
    for a,b in zip(rr,rr[1:]):
        check('multi-day tail chain '+b['flight_id'],a['destination']==b['origin'] and dt.datetime.fromisoformat(b['departure_utc'])-dt.datetime.fromisoformat(a['arrival_utc'])>=dt.timedelta(minutes=45))
cf=[r for r in FL if r['hypothesis']=='C31']
check('C31 complete old donor and delivery',sum(r['network']=='KEEP_TU_TLV_CANCEL_IF_REPLACED' for r in cf)==4 and sum('FERRY' in r['status'] for r in cf)==2)
check('C31 freed dates Mon Thu',[r['date'] for r in cf if r['network']=='ADD_SSJ_OMS' and r['origin']=='SVX']==['2027-07-05','2027-07-08'])
for c in out('C35_connections'):
    aa=next(r for r in FL if r['flight_id']==c['first_flight']);bb=next(r for r in FL if r['flight_id']==c['second_flight'])
    close('C35 actual connection minutes',(dt.datetime.fromisoformat(bb['departure_utc'])-dt.datetime.fromisoformat(aa['arrival_utc'])).total_seconds()/60,90)

# Independently generated cash by entity and date; grouped equal-day netting is a lower bound.
EVENT=out('cash_events');SUMMARY=out('cash_summary');expected=defaultdict(float)
def put(cid,s,e,d,x):expected[(cid,s,e,str(d))]+=x
for s in A:
    r=next(r for r in C10 if r['scenario']==s and r['phase']=='launch_closed' and r['cohorts']=='1' and r['K_probe']=='0');d0=date(P['C10']['start'])
    put('C10',s,'airline',d0-dt.timedelta(days=14),F(r,'minimum_corporate_guarantee_total'))
    for d in [d0,d0+dt.timedelta(days=28)]:put('C10',s,'airline',d,(F(r,'retail_revenue')-F(r,'airline_variable_cost'))/2)
    r=next(r for r in C14 if r['scenario']==s and r['K_probe']=='0');q=P['C14']['cohort_people'][s];G=F(r,'minimum_air_guarantee_return_per_person');price=F(r,'minimum_package_price_per_person');hp=14*7760*P['C14']['hotel_stress_factor'][s]
    for c in [c for c in CO if c['scenario']==s]:
        d=date(c['outbound']);pay=d-dt.timedelta(days=14)
        put('C14',s,'airline',pay,q*G)
        put('C14',s,'tour_operator',pay,q*(price-G))
        put('C14',s,'tour_operator',d-dt.timedelta(days=30),-q*hp/2)
        put('C14',s,'tour_operator',d,-q*(hp/2+sum(P['C14'][k][s] for k in ['return_ground_transfer_per_person_rub','product_service_per_person_rub','protection_per_person_rub'])))
    for d in sorted(set(c['date'] for c in SEAT)):
        ss=[x for x in SEAT if x['scenario']==s and x['date']==d]
        put('C14',s,'airline',d,sum(F(x,'retail_people')*fare('KVX','MRV',s)-F(x,'used_seats')*A[s]['pax_cost_rub'] for x in ss)-2*fixed(s,hours('KVX','MRV',True))-2*fixed(s,hours('SVX','KVX')))
    for y in [2027,2028]:
        for f in [f for f in FL if f['hypothesis']=='C17' and f['network']=='seasonal_'+str(y)]:
            d=date(f['date']);q=0;price=0
            if 'MMK' in [f['origin'],f['destination']]:
                m=next(m for m in MONTH if m['scenario']==s and m['year']==str(y) and m['month']==str(d.month));q=F(m,'winter_rw_paid_segments')/(2*F(m,'winter_roundtrips'));price=fare('PEE','MMK',s)
            elif 'RGK' in [f['origin'],f['destination']]:q=70;price=P['C17']['rgk_fare_rub'][s]
            put('C17',s,'airline_'+str(y)+'_summerp70',d,q*(price-A[s]['pax_cost_rub'])-fixed(s,F(f,'block_hours')))
    r=next(r for r in C31 if r['scenario']==s and r['demand_layer']=='nastya_primary' and r['additional_mrv_paid_each_leg_probe']=='0' and r['foregone_tu_old_mission_contribution_probe']=='0');d=date(P['C31']['week_start']);e='incremental_KEEP_comparison_L0_at_cost_ceiling'
    put('C31',s,e,d-dt.timedelta(days=1),-F(r,'maximum_tu_new_allin_cost_plus_K'))
    for offset in [0,3]:put('C31',s,e,d+dt.timedelta(days=offset),(F(r,'old_ssj_mrv_variable_cost_saved')+F(r,'additional_oms_variable_contribution'))/2)
    r=next(r for r in C35 if r['scenario']==s and r['K_probe']=='0');d=date(P['C35']['start'])
    put('C35',s,'airline',d-dt.timedelta(days=14),-480000)
    dates=sorted(set(f['date'] for f in FL if f['hypothesis']=='C35'))
    for d in dates:put('C35',s,'airline',d,(F(r,'customer_total_fare_revenue')-F(r,'rw_pax_handling_protection_cost'))/len(dates))
actual=defaultdict(float)
for e in EVENT:actual[(e['hypothesis'],e['scenario'],e['entity'],e['date'])]+=F(e,'amount_rub')
check('cash dates/entity keys match independent construction',set(actual)==set(expected))
for k in actual:close('cash independent dated net '+str(k),actual[k],expected[k])
for r in SUMMARY:
    if r['kind']!='TIMING_FIXTURE_K0':continue
    keys=sorted(k for k in actual if k[:3]==(r['hypothesis'],r['scenario'],r['entity']));balance=0;minimum=0
    for k in keys:balance+=actual[k];minimum=min(minimum,balance)
    close('cash independently reaggregated end',F(r,'cash_balance_end'),balance)
    close('cash same-day lower financing bound',F(r,'minimum_external_funding_if_same_day_netting'),-minimum)
    if r['hypothesis']=='C14':EXAMPLES['cash_C14_'+r['scenario']+'_'+r['entity']]={'end':balance,'financing_lower_bound':-minimum}
# Entity/cash classification is checked independently from grouped end balances.
for e in EVENT:
    if e['kind'].startswith('HOTEL_'):check('hotel cash belongs to tour operator',e['hypothesis']=='C14' and e['entity']=='tour_operator')
    check('no duplicated opportunity cash expense',not any(t in e['kind'] for t in ['OPPORTUNITY','LOST_PREVIOUS']))
    if e['kind']=='MONTH_PARTNER_BLOCK_PREPAY':
        check('full external block paid14days before first flight',F(e,'amount_rub')==-480000 and e['date']=='2027-06-22')
    if e['kind']=='TOUR_OPERATOR_AIR_GUARANTEE':
        matches=[x for x in EVENT if x['hypothesis']=='C14' and x['scenario']==e['scenario'] and x['date']==e['date'] and x['kind']=='AIR_BLOCK_PAYMENT_TO_RW']
        check('C14 airline receipt matches tour-operator payment',len(matches)==1 and math.isclose(F(e,'amount_rub'),-F(matches[0],'amount_rub')))

# Intraday payment-first shows why netted lower bound is not an unconditional funding budget.
keys=sorted(set((e['hypothesis'],e['scenario'],e['entity']) for e in EVENT))
for key in keys:
    ev=[e for e in EVENT if (e['hypothesis'],e['scenario'],e['entity'])==key];bal=0;low=0
    for d in sorted({e['date'] for e in ev}):
        for e in sorted([e for e in ev if e['date']==d],key=lambda e:F(e,'amount_rub')):bal+=F(e,'amount_rub');low=min(low,bal)
    su=next(r for r in SUMMARY if r['kind']=='TIMING_FIXTURE_K0' and (r['hypothesis'],r['scenario'],r['entity'])==key)
    if key==('C14','base','airline'):mutation('C14 treat same-day netting as intraday finance',-low,F(su,'minimum_external_funding_if_same_day_netting'),'Pay-first order needs more funding than the equal-day lower bound')
# Wrong entity: assign hotel disbursements to airline while leaving tour receipts elsewhere.
hotel=F(next(r for r in C14 if r['scenario']=='base' and r['K_probe']=='0'),'hotel_cost')
mutation('C14 move tour-operator hotel to airline entity',0,-hotel,'Hotel belongs to tour operator; airline earns air guarantee only')
r=next(r for r in C35 if r['scenario']=='base' and r['K_probe']=='0');end=F(next(x for x in SUMMARY if x['hypothesis']=='C35' and x['scenario']=='base' and x['kind']=='TIMING_FIXTURE_K0'),'cash_balance_end')
mutation('C35 charge opportunity margin as new cash disbursement',end,end-F(r,'lost_previous_own_contribution_probe'),'Lost KEEP margin belongs once in incremental economics, not an extra supplier payment')

# Readiness: independently truncate actual flight dates / complete customer round trips.
READY=out('slot_readiness_sensitivity')
for r in READY:
    if r['hypothesis'] in ['C31','C35']:continue
    p=P['readiness_probes'][r['delivery_probe']];ready=date(p['delivered'])+dt.timedelta(days=p['introduction_days']) if p['delivered'] else dt.date(9999,1,1)
    check('ready date',r['ready_date']==str(ready));s=r['scenario']
    if r['hypothesis']=='C10':check('C10 January not funded by H2 plane',r['original_program_can_start']=='False');continue
    if r['hypothesis']=='C14':
        cs=[c for c in CO if c['scenario']==s and date(c['outbound'])>=ready];ds=set(c[k] for c in cs for k in ['outbound','return_date']);q=P['C14']['cohort_people'][s];ret=P['C14']['retail_people_per_kvx_mrv_leg'][s];people=len(cs)*q
        close('C14 readiness groups',F(r,'admitted_cohorts'),len(cs));close('C14 readiness four-leg days',F(r,'admitted_flight_legs'),4*len(ds))
        if people:
            cost=2*len(ds)*(fixed(s,hours('SVX','KVX'))+fixed(s,hours('KVX','MRV',True)))+(2*people+2*len(ds)*ret)*A[s]['pax_cost_rub']
            close('C14 truncated guarantee',F(r,'minimum_air_return_guarantee_before_K'),(cost-2*len(ds)*ret*fare('KVX','MRV',s))/people)
        else:check('C14 empty program floor stays unknown',r['minimum_air_return_guarantee_before_K']=='')
        continue
    y=int(r['year']);winter=[d for d in year_days(y) if d.month in [1,2,3,12] and d.weekday() in [2,5] and d>=ready];summer=[d for d in year_days(y) if d.month in [6,7,8,9] and d.weekday() in [2,5] and d>=ready]
    close('C17 readiness winter dates',F(r,'winter_roundtrips'),len(winter));close('C17 readiness summer dates',F(r,'summer_roundtrips'),len(summer))
    seasons=set('W1' if d.month<=3 else 'S' if d.month<=9 else 'W2' for d in winter+summer)
    sold=0
    for m in range(1,13):
        mr=next(x for x in MONTH if x['year']==str(y) and x['scenario']==s and x['month']==str(m))
        if F(mr,'winter_roundtrips'):sold+=F(mr,'winter_rw_paid_segments')*sum(d.month==m for d in winter)/F(mr,'winter_roundtrips')
    close('C17 readiness monthly demand not reconcentrated',F(r,'winter_paid_segments'),sold)
    result=sold*(fare('PEE','MMK',s)-A[s]['pax_cost_rub'])-2*len(winter)*fixed(s,hours('PEE','MMK'))+2*len(summer)*(F(r,'summer_paid_each_leg_probe')*(P['C17']['rgk_fare_rub'][s]-A[s]['pax_cost_rub'])-fixed(s,P['C17']['rgk_block_hours_analog']))-2*len(seasons)*fixed(s,hours('SVX','PEE'))
    close('C17 readiness truncated cost',F(r,'variable_contribution_before_K'),result)

# Extra C17 alternatives and support probes: limited fares BEFORE per-flight support.
for r in out('C17_alternatives'):
    s=r['scenario'];y=int(r['year']);n=sum(d.weekday() in [2,5] and (r['alternative']=='RGK_YEAR_ROUND' or d.month in [6,7,8,9]) for d in year_days(y));fixedsum=2*n*fixed(s,P['C17']['rgk_block_hours_analog'])+2*fixed(s,hours('SVX','PEE'))
    close('C17 alternative actual calendar',F(r,'roundtrips'),n)
    close('C17 alternative result',F(r,'variable_contribution'),2*n*F(r,'paid_each_leg_probe')*(P['C17']['rgk_fare_rub'][s]-A[s]['pax_cost_rub'])-fixedsum)
SUP=out('addendum_constrained_support_probes')
for r in SUP:
    cid=r['hypothesis'];s=r['scenario'];support=F(r,'reference_max_support_if_all_legs_eligible')
    check('support never confirmed',r['credited_support_in_original_model']=='0' and ('UNKNOWN' in r['actual_award'] or r['actual_award']=='EXTRA_FREQUENCIES_NOT_AUTOMATICALLY_IN_OLD_RW_CONTRACT'))
    if cid=='C10':
        phase,n=r['variant'].split('_cohorts');base=next(x for x in C10 if x['scenario']==s and x['phase']==phase and x['cohorts']==n and x['K_probe']=='0');income=(F(base,'corporate_seat_segments')+F(base,'retail_seat_segments'))*min(fare('UFA','SGC',s),7089);correct=income+2*F(base,'roundtrips')*310249-F(base,'airline_variable_cost')
    elif cid=='C14':
        base=next(x for x in C14 if x['scenario']==s and x['K_probe']=='0');income=(F(base,'airline_seat_segments')+F(base,'retail_seat_segments'))*min(fare('KVX','MRV',s),9021);correct=income+16*403871-F(base,'airline_variable_cost')
    elif cid=='C17':
        year,p=r['variant'].split('_summer_p');base=next(x for x in C17 if x['scenario']==s and x['year']==year and x['summer_people_each_leg_probe']==p and x['K_probe']=='0');reduction=F(base,'winter_paid_segments')*max(0,fare('PEE','MMK',s)-9021)+F(base,'summer_paid_segments')*max(0,P['C17']['rgk_fare_rub'][s]-10953);correct=F(base,'full_incremental_at_probe_and_K')-reduction+140*403871
        close('C17 required support after fare cap',F(r,'minimum_support_required_before_K'),max(0,-(correct-140*403871)))
    elif cid=='C31':
        base=next(x for x in C31 if x['scenario']==s and x['demand_layer']=='nastya_primary');reduction=F(base,'additional_oms_paid_segments')*max(0,fare('SVX','OMS',s)-5157);correct=F(base,'additional_oms_variable_contribution')-reduction+4*225989
    else:check('C35 KEEP no new eligible flight',support==0 and F(r,'potential_eligible_revenue_legs')==0);continue
    close('combined fare-cap-and-support '+cid,F(r,'conditional_contribution_after_fare_cap_and_reference_support_before_K'),correct)

RESULT={'reviewed_sha':SUBJECT,'owner_code_executed':False,'network_used':False,'checks_passed':len(CHECKS),'checks_failed':0,'counts':{'delivery_hashes':len(delivery['files']),'input_hashes':len(im['files']),'exact_git_copies':exact,'money_rows':sum(len(x) for x in [C10,C14,C17,C31,C35]),'dated_flights':len(FL),'cash_events':len(EVENT),'cash_cases':sum(r['kind']=='TIMING_FIXTURE_K0' for r in SUMMARY),'readiness_rows':len(READY),'internal_KEEP_rows':len(INT),'support_rows':len(SUP),'counterexamples':len(MUTATIONS)},'examples':EXAMPLES,'counterexamples':MUTATIONS,'checks':CHECKS}
(HERE/'verification.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2)+'\n')
(HERE/'manifests/input_manifest.json').write_text(json.dumps({'subject':SUBJECT,'files':sorted(USED.values(),key=lambda r:(r['commit'],r['path']))},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in RESULT.items() if k not in ['checks','examples','counterexamples']},indent=2))
print(json.dumps(EXAMPLES,ensure_ascii=False,indent=2))

if '--check-seal' in sys.argv:
    seal=json.loads((HERE/'manifests/output_manifest.json').read_text())
    present={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'manifests/output_manifest.json'}
    assert present=={r['path'] for r in seal['files']}, 'Review output inventory mismatch'
    for item in seal['files']:
        b=(HERE/item['path']).read_bytes()
        assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'], 'Review seal mismatch: '+item['path']
    print('Review output seal verified:',len(seal['files']),'files')
