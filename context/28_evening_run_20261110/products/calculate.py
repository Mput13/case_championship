#!/usr/bin/env python3
"""Bounded product experiments. Pure stdlib; offline, pinned input bytes only.

K is a signed, exhaustive incremental-cost envelope specified in README, NOT zero
actual overhead. Positive K_ceiling is a condition, never a profit forecast.
"""
import calendar
import csv
import datetime as dt
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
P = json.loads((HERE / "parameters.json").read_text())
A_ROWS = list(csv.DictReader((HERE / "inputs/nastya/data/assumptions/network.csv").open()))
A = {s: {r["parameter"]: float(r[s]) for r in A_ROWS} for s in ["base", "cautious"]}
D = {frozenset([r["a"], r["b"]]): r for r in csv.DictReader((HERE / "inputs/nastya/data/processed/demand_estimates.csv").open())}
N = {r["iata"]: r for r in csv.DictReader((HERE / "inputs/nastya/data/processed/catchments.csv").open())}
CHECKS = []


def check(name, condition):
    CHECKS.append({"check": name, "passed": bool(condition)})
    if not condition:
        raise AssertionError(name)


def write(name, rows):
    rows = list(rows)
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(rows)


def date(s):
    return dt.date.fromisoformat(s)


def days(start, end):
    for i in range((end - start).days + 1):
        yield start + dt.timedelta(days=i)


def hav(a, b):
    la1, lo1 = [math.radians(float(N[a][k])) for k in ["latitude_deg", "longitude_deg"]]
    la2, lo2 = [math.radians(float(N[b][k])) for k in ["latitude_deg", "longitude_deg"]]
    return 12742 * math.asin(math.sqrt(math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2))


def distance(a, b):
    r = D.get(frozenset([a, b]))
    return float(r["km"]) if r else hav(a, b)


def bh(a, b, south=False):
    return .5 + distance(a, b) * (1.2 if south else 1.1) / 750


def fare(s, a, b):
    return A[s]["fare_fixed_rub"] + A[s]["fare_per_km_rub"] * distance(a, b)


def c0(s, hours):
    a = A[s]
    return ((a["fuel_t_per_hour"]*hours+a["fuel_t_per_cycle"])*a["fuel_rub_per_t"]
            + hours*(a["mro_rub_per_hour"]+a["crew_rub_per_hour"]+a["navigation_rub_per_hour"])
            + a["ground_rub_per_flight"]+a["deicing_rub_per_flight"])


def demand(s, a, b):
    return float(D[frozenset([a, b])]["od_"+s])


def capshare(s, f, competitive=True):
    return A[s]["capture_competitive" if competitive else "capture_open"]*(1-math.exp(-f/3))


def utc(t):
    return t.astimezone(dt.timezone.utc)


FLIGHTS = []


def flight(cid, program, day, origin, dest, departure_clock, hours, tail, seats=100, kind="PROPOSED", pax=0):
    tz = {"SVX":5,"PEE":5,"UFA":5,"SGC":5,"KVX":3,"MRV":3,"MMK":3,"OMS":6,"IJK":4,"RGK":7,"ZIA":3,"TLV":3}
    dep = dt.datetime.combine(day, dt.time.fromisoformat(departure_clock),dt.timezone(dt.timedelta(hours=tz[origin])))
    arr = (utc(dep)+dt.timedelta(hours=hours)).astimezone(dt.timezone(dt.timedelta(hours=tz[dest])))
    fid=f"{cid}:{program}:{day}:{origin}-{dest}"
    FLIGHTS.append(dict(hypothesis=cid,network=program,flight_id=fid,date=day,route=f"{origin}-{dest}",origin=origin,destination=dest,departure_local=dep.isoformat(),arrival_local=arr.isoformat(),departure_utc=utc(dep).isoformat(),arrival_utc=utc(arr).isoformat(),block_hours=hours,tail_slot=tail,seats=seats,fixture_pax=pax,status=kind))
    check("seats "+fid,0 <= pax <= seats)
    return fid,arr


# C10: first cohorts have no predecessor. Closing flights are included.
c10=[]
for s in A:
    q=P["C10"]["corporate_people"][s]; r=P["C10"]["retail_people_per_leg"][s]
    h=bh("UFA","SGC"); F=fare(s,"UFA","SGC"); v=A[s]["pax_cost_rub"]
    for n in P["C10"]["cohorts_in_first_28_days"]:
        for phase in ["steady28","launch_closed"]:
            legs=2*n if phase=="steady28" else 4*n
            corp=2*n*q; retail=legs*r; fixed=legs*c0(s,h)
            retail_revenue=retail*F
            interval_days=28 if phase=="steady28" else 29+(n-1)*28//n
            same_flights_frequency=(legs/2)*7/interval_days
            ordinary=min(100*legs,demand(s,"UFA","SGC")*interval_days/365*capshare(s,same_flights_frequency))
            ordinary_margin=ordinary*(F-v)-fixed
            for K in P["C10"]["k_probe_rub_per_28_days"]:
                floor=(fixed+v*(corp+retail)+K-retail_revenue)/(n*q)
                relative_floor=(ordinary_margin+fixed+v*(corp+retail)+K-retail_revenue)/(n*q)
                c10.append(dict(hypothesis="C10",scenario=s,phase=phase,cohorts=n,roundtrips=legs/2,people_in_new_cohorts=n*q,corporate_seat_segments=corp,retail_seat_segments=retail,block_hours=legs*h,reference_oneway_fare=F,reference_return_fare=2*F,airline_variable_cost=fixed+v*(corp+retail),retail_revenue=retail_revenue,corporate_revenue_at_reference=corp*F,variable_contribution_at_reference=retail_revenue+corp*F-fixed-v*(corp+retail),ordinary_same_flights_model_paid_segments=ordinary,ordinary_same_flights_variable_contribution=ordinary_margin,minimum_guarantee_to_beat_ordinary_return_per_person=relative_floor,K_probe=K,minimum_guarantee_return_per_person=floor,minimum_corporate_guarantee_total=floor*n*q,full_incremental_at_reference_and_K=retail_revenue+corp*F-fixed-v*(corp+retail)-K,actual_contract_revenue="UNKNOWN",actual_full_result="UNKNOWN"))
        check(f"C10 capacity {s}/{n}",q+r<=100)
        for j in range(n):
            dep=date(P["C10"]["start"])+dt.timedelta(days=j*28//n)
            ret=dep+dt.timedelta(days=28)
            if s=="base":
                for d,is_start in [(dep,True),(ret,False)]:
                    flight("C10",f"launch{n}",d,"UFA","SGC","08:00",h,"SSJ_C10",pax=r+(q if is_start else 0))
                    flight("C10",f"launch{n}",d,"SGC","UFA","12:00",h,"SSJ_C10",pax=r+(0 if is_start else q))
write("C10_contract_thresholds.csv",c10)

# C14: six weekly 14-night cohorts; eight complete roundtrips + eight ferry RT.
c14=[]; cohorts=[]; beds=[]; seats=[]
t=P["C14"]; start=date(t["first_departure"]); depdays=[start+dt.timedelta(days=7*j) for j in range(t["cohorts"])]; all_days=sorted(set(depdays+[d+dt.timedelta(days=14) for d in depdays]))
h=bh("KVX","MRV",True); hp=bh("SVX","KVX")
for s in A:
    q=t["cohort_people"][s]; r=t["retail_people_per_kvx_mrv_leg"][s]; v=A[s]["pax_cost_rub"]; F=fare(s,"KVX","MRV")
    airlegs=2*len(all_days); ferry_legs=airlegs; packpax=2*len(depdays)*q; retailpax=airlegs*r; people=len(depdays)*q
    totalair=airlegs*c0(s,h)+ferry_legs*c0(s,hp)+v*(packpax+retailpax)
    hoteldays=people*t["contract_billable_bed_days"]; hotel=hoteldays*t["hotel_bed_day_rub_2026"]*t["hotel_stress_factor"][s]
    ground=people*t["return_ground_transfer_per_person_rub"][s]; service=people*t["product_service_per_person_rub"][s]; risk=people*t["protection_per_person_rub"][s]
    for K in t["k_probe_rub_program"]:
        airfloor=(totalair-retailpax*F+K)/people
        totalfloor=airfloor+(hotel+ground+service+risk)/people
        c14.append(dict(hypothesis="C14",scenario=s,program="SVX_KVX_MRV_full_chain",cohorts=len(depdays),cohort_people=q,distinct_return_customers=people,airline_seat_segments=packpax,retail_seat_segments=retailpax,revenue_legs=airlegs,positioning_legs=ferry_legs,block_hours=airlegs*h+ferry_legs*hp,hotel_billable_bed_days=hoteldays,peak_beds=2*q,airline_variable_cost=totalair,hotel_cost=hotel,ground_cost=ground,product_service=service,expected_protection_probe=risk,retail_revenue=retailpax*F,airfare_reference_return=2*F,variable_airline_contribution_at_reference=packpax*F+retailpax*F-totalair,K_probe=K,minimum_air_guarantee_return_per_person=airfloor,minimum_package_price_per_person=totalfloor,partner_air_return_purchase_price_indifference=airfloor,actual_airline_full_result="UNKNOWN",hotel_quote_2027="UNKNOWN"))
    for j,d in enumerate(depdays):
        cohorts.append(dict(hypothesis="C14",scenario=s,cohort=f"H{j+1}",outbound=d,return_date=d+dt.timedelta(days=14),checkin_local=f"{d}T14:00:00+03:00",checkout_local=f"{d+dt.timedelta(days=14)}T10:00:00+03:00",nights=14,billable_bed_days_per_person=t["contract_billable_bed_days"],billable_days_status="REQUIRES_EXPLICIT_HOTEL_CONTRACT_NOT_INFERRED_FROM_NIGHTS",people=q))
    for d in days(start,all_days[-1]):
        occupied=sum(q for x in depdays if x<=d<x+dt.timedelta(days=14))
        beds.append(dict(hypothesis="C14",scenario=s,date=d,occupied_beds=occupied,required_rooms_twin=math.ceil(occupied/2)))
    for d in all_days:
        outq=q if d in depdays else 0; backq=q if d-dt.timedelta(days=14) in depdays else 0
        for direction,qty in [("KVX-MRV",outq),("MRV-KVX",backq)]:
            seats.append(dict(hypothesis="C14",scenario=s,date=d,route=direction,package_people=qty,retail_people=r,used_seats=qty+r,residual_seats=100-qty-r))
            check(f"C14 dated capacity {s}/{d}/{direction}",qty+r<=100)
        if s=="base":
            flight("C14","SVX_KVX_MRV_full_chain",d,"SVX","KVX","08:30",hp,"SSJ_C14",kind="PROPOSED_FERRY")
            flight("C14","SVX_KVX_MRV_full_chain",d,"KVX","MRV","09:00",h,"SSJ_C14",pax=outq+r)
            flight("C14","SVX_KVX_MRV_full_chain",d,"MRV","KVX","14:30",h,"SSJ_C14",pax=backq+r)
            flight("C14","SVX_KVX_MRV_full_chain",d,"KVX","SVX","18:30",hp,"SSJ_C14",kind="PROPOSED_FERRY")
    check("C14 no double sold cohort "+s,sum(x["package_people"] for x in seats if x["scenario"]==s)==packpax)
    check("C14 bedday conservation "+s,sum(x["occupied_beds"] for x in beds if x["scenario"]==s)==people*14)
write("C14_full_package_thresholds.csv",c14);write("C14_cohorts.csv",cohorts);write("C14_bed_occupancy.csv",beds);write("C14_dated_seats.csv",seats)

# C17: month-specific demand allocation; demand not shifted into operated months.
c17=[]; monthly=[]
t=P["C17"]; hm=bh("PEE","MMK"); hg=t["rgk_block_hours_analog"]; hp=bh("SVX","PEE")
for year in t["years"]:
    winterdates=[d for d in days(dt.date(year,1,1),dt.date(year,12,31)) if d.month in t["winter_months"] and d.weekday() in t["flight_weekdays"]]
    summerdates=[d for d in days(dt.date(year,1,1),dt.date(year,12,31)) if d.month in t["summer_months"] and d.weekday() in t["flight_weekdays"]]
    for s in A:
        v=A[s]["pax_cost_rub"]; Fm=fare(s,"PEE","MMK"); Fg=t["rgk_fare_rub"][s]
        weights={m:calendar.monthrange(year,m)[1]*(float(D[frozenset(["PEE","MMK"])]["winter_factor"]) if m in [12,1,2] else float(D[frozenset(["PEE","MMK"])]["summer_factor"]) if m in [6,7,8] else 1) for m in range(1,13)}
        wm=0
        for m in range(1,13):
            n=sum(d.month==m for d in winterdates); ng=sum(d.month==m for d in summerdates)
            local_demand=demand(s,"PEE","MMK")*weights[m]/sum(weights.values())
            paid=min(2*n*100,local_demand*capshare(s,2,False)) if n else 0
            wm+=paid
            monthly.append(dict(hypothesis="C17",scenario=s,year=year,month=m,winter_roundtrips=n,summer_roundtrips=ng,winter_all_market_directional_journeys=local_demand,winter_rw_paid_segments=paid,mmk_annual_model_od=demand(s,"PEE","MMK"),rgk_annual_od="UNKNOWN",offseason_use="OTHER_MISSION_OR_PARKING_REQUIRES_K" if n+ng==0 else "SEASONAL_PROGRAM",resource_pool="ONE_PEE_SSJ_SLOT_NOT_WHOLE_FLEET"))
        nm=2*len(winterdates); ng=2*len(summerdates)
        winter_margin=wm*(Fm-v)-nm*c0(s,hm)
        # Three closed seasonal programmes Jan-Mar, Jun-Sep, Dec: six positioning legs.
        ferrycost=6*c0(s,hp)
        for K in t["k_probe_rub_year"]:
            summer_needed=(ng*c0(s,hg)+ferrycost+K-winter_margin)/(Fg-v)
            for p in t["summer_paid_people_each_leg_probes"]:
                result=winter_margin+ng*(p*(Fg-v)-c0(s,hg))-ferrycost-K
                c17.append(dict(hypothesis="C17",scenario=s,year=year,winter_roundtrips=len(winterdates),summer_roundtrips=len(summerdates),positioning_legs=6,block_hours=nm*hm+ng*hg+6*hp,winter_paid_segments=wm,winter_average_paid_people_each_leg=wm/nm,winter_variable_contribution=winter_margin,rgk_reference_oneway_fare=Fg,summer_people_each_leg_probe=p,summer_paid_segments=ng*p,seasonal_variable_contribution_before_K=result+K,K_probe=K,full_incremental_at_probe_and_K=result,minimum_summer_paid_segments_for_whole_year=summer_needed,minimum_summer_paid_people_each_leg=summer_needed/ng,summer_seat_capacity=100*ng,summer_threshold_physical_feasible=summer_needed<=100*ng,winter_only_break_even_people_each_leg=c0(s,hm)/(Fm-v),summer_only_break_even_people_each_leg=c0(s,hg)/(Fg-v),actual_full_result="UNKNOWN",summer_actual_demand="UNKNOWN"))
    for dest,dd,hh in [("MMK",winterdates,hm),("RGK",summerdates,hg)]:
        for d in dd:
            flight("C17",f"seasonal_{year}",d,"PEE",dest,"08:00",hh,"SSJ_C17")
            flight("C17",f"seasonal_{year}",d,dest,"PEE","13:40",hh,"SSJ_C17")
    for d,a,b in [(dt.date(year,1,1),"SVX","PEE"),(dt.date(year,3,31),"PEE","SVX"),(dt.date(year,6,1),"SVX","PEE"),(dt.date(year,9,30),"PEE","SVX"),(dt.date(year,12,1),"SVX","PEE"),(dt.date(year,12,31),"PEE","SVX")]:
        flight("C17",f"seasonal_{year}",d,a,b,"05:00" if a=="SVX" else "20:00",hp,"SSJ_C17",kind="PROPOSED_FERRY")
write("C17_seasonal_thresholds.csv",c17);write("C17_monthly_calendar.csv",monthly)

# C31: common MRV sales cancel; foregone Tu mission remains a separate signed term.
c31=[]; resource=[]
t=P["C31"]; h_m=bh("SVX","MRV",True); h_o=bh("SVX","OMS"); nlegs=4
for s in A:
    v=A[s]["pax_cost_rub"]; Fm=fare(s,"SVX","MRV"); Fo=fare(s,"SVX","OMS"); oldp=t["old_ssj_paid_people_each_leg"][s]
    old_ssj_cost=nlegs*(c0(s,h_m)+v*oldp)
    for layer,annual in [("nastya_primary",demand(s,"SVX","OMS")),("colleagues_prior_not_averaged",float(D[frozenset(["SVX","OMS"])]["colleagues_od_"+s]))]:
        additional=annual*(capshare(s,4)-capshare(s,2))*7/365
        newp=min(400,additional)
        omsmargin=newp*(Fo-v)-nlegs*c0(s,h_o)
        for extra in t["mrv_additional_paid_people_each_leg_probes"]:
            check("C31 replacement seats",oldp+extra<=t["replacement_seats"])
            for L in t["replacement_old_contribution_rub_week_probes"]:
                ceiling=old_ssj_cost+extra*nlegs*Fm+omsmargin-L
                for cost in t["replacement_allin_cost_rub_week_probes"]:
                    c31.append(dict(hypothesis="C31",scenario=s,demand_layer=layer,week_start=t["week_start"],old_ssj_paid_mrv_segments=oldp*nlegs,old_ssj_mrv_variable_cost_saved=old_ssj_cost,old_ssj_mrv_revenue=oldp*nlegs*Fm,additional_oms_paid_segments=newp,additional_oms_variable_contribution=omsmargin,additional_mrv_paid_each_leg_probe=extra,additional_mrv_revenue=extra*nlegs*Fm,foregone_tu_old_mission_contribution_probe=L,maximum_tu_new_allin_cost_plus_K=ceiling,maximum_tu_rub_per_mrv_block_hour_plus_K=ceiling/(nlegs*3.5),tu_new_allin_cost_probe=cost,full_incremental_at_probe_before_K=ceiling-cost,required_extra_mrv_paid_each_leg_at_cost_and_L=(cost+L-old_ssj_cost-omsmargin)/(nlegs*Fm),actual_tu_tail="UNKNOWN",actual_tu_cost="UNKNOWN",actual_full_result="UNKNOWN"))
    for old_rt in [1,2]:
        resource.append(dict(hypothesis="C31",scenario=s,old_tu_mission=f"ZIA-TLV {old_rt}RT/week",old_tu_hours_released=old_rt*11.5,new_tu_mrv_hours=14,first_week_positioning_hours_probe=5.2,first_week_hours_required=19.2,first_week_resource_balance=old_rt*11.5-19.2,old_ssj_hours_released=nlegs*h_m,new_ssj_oms_hours=nlegs*h_o,ssj_hours_balance=nlegs*(h_m-h_o),available_registered_tu_and_crew="UNKNOWN",resource_admitted=False))
for offset in [0,3]:
    d=date(t["week_start"])+dt.timedelta(days=offset)
    flight("C31","KEEP_SSJ_MRV",d,"SVX","MRV","08:00",h_m,"SSJ_C31_OLD",pax=85,kind="KEEP_SCENARIO_NOT_OBSERVED")
    flight("C31","KEEP_SSJ_MRV",d,"MRV","SVX","11:30",h_m,"SSJ_C31_OLD",pax=85,kind="KEEP_SCENARIO_NOT_OBSERVED")
    flight("C31","REPLACE_TU_MRV",d,"SVX","MRV","08:00",3.5,"TU214_C31",seats=194,pax=85)
    flight("C31","REPLACE_TU_MRV",d,"MRV","SVX","11:30",3.5,"TU214_C31",seats=194,pax=85)
for offset in [1,4]:
    d=date(t["week_start"])+dt.timedelta(days=offset)
    flight("C31","ADD_SSJ_OMS",d,"SVX","OMS","08:00",h_o,"SSJ_C31_FREED")
    flight("C31","ADD_SSJ_OMS",d,"OMS","SVX","11:30",h_o,"SSJ_C31_FREED")
write("C31_replacement_frontier.csv",c31);write("C31_two_aircraft_resource.csv",resource)

# C35: one customer fare; partner receives prepaid block, not a second fare.
c35=[]; connections=[]
t=P["C35"]; dd=[d for d in days(date(t["start"]),date(t["end"])) if d.weekday() in t["flight_weekdays"]]
nlegs=2*len(dd); block=nlegs*t["protected_seat_block_each_leg"]
for s in A:
    gross=demand(s,"IJK","OMS")*A[s]["capture_transfer"]*(1-math.exp(-2/3))*((date(t["end"])-date(t["start"])).days+1)/365
    Q=min(block,gross); cann=Q*t["own_cannibalised_fraction_probe"][s]
    F=fare(s,"IJK","OMS")*A[s]["transfer_fare_factor"]
    directcost=Q*(A[s]["pax_cost_rub"]+t["journey_handling_rub"][s]+t["expected_disruption_cost_rub_per_journey_probe"][s])
    lost=cann*t["previous_own_contribution_rub_per_cannibalised_journey_probe"]
    for K in t["k_probe_rub_program"]:
        maxblock=(Q*F-directcost-lost-K)/block
        c35.append(dict(hypothesis="C35",scenario=s,program="IJK_SVX_OMS_external_feed_conditional",start=t["start"],end=t["end"],roundtrips_each_operator=len(dd),protected_seat_segments_each_operator=block,through_oneway_journeys=Q,own_cannibalised_journeys_probe=cann,incremental_rw_passenger_segments=Q-cann,customer_oneway_fare=F,customer_total_fare_revenue=Q*F,partner_block_total_probe=block*t["partner_block_unit_price_probe_rub"],rw_pax_handling_protection_cost=directcost,lost_previous_own_contribution_probe=lost,variable_incremental_contribution_at_block_probe=Q*F-directcost-lost-block*t["partner_block_unit_price_probe_rub"],K_probe=K,full_incremental_at_block_probe_and_K=Q*F-directcost-lost-block*t["partner_block_unit_price_probe_rub"]-K,maximum_partner_price_per_reserved_seat=maxblock,minimum_paid_journeys_at_block_probe_and_K=(block*t["partner_block_unit_price_probe_rub"]+K)/(F-directcost/Q-lost/Q),maximum_routine_protected_people_each_leg=15,actual_partner="UNCONFIRMED",actual_full_result="UNKNOWN"))
    check("C35 block residual "+s,t["retained_rw_local_people_each_leg"]+t["protected_seat_block_each_leg"]<=100)
    check("C35 conservation "+s,Q<=block)
for d in dd:
    a,arr1=flight("C35","external_feed",d,"IJK","SVX","08:00",70/60,"PARTNER_C35",seats=50)
    b,arr2=flight("C35","rw_KEEP_retimed",d,"SVX","OMS","11:40",100/60,"RW_EXISTING_C35",kind="PROPOSED_RETIME_KEEP")
    c,arr3=flight("C35","rw_KEEP_retimed",d,"OMS","SVX","15:30",100/60,"RW_EXISTING_C35",kind="PROPOSED_RETIME_KEEP")
    e,arr4=flight("C35","external_feed",d,"SVX","IJK","17:40",70/60,"PARTNER_C35",seats=50)
    for first,second,arr,dep,side in [(a,b,arr1,dt.datetime.combine(d,dt.time(11,40),dt.timezone(dt.timedelta(hours=5))),"out"),(c,e,arr3,dt.datetime.combine(d,dt.time(17,40),dt.timezone(dt.timedelta(hours=5))),"back")]:
        wait=(utc(dep)-utc(arr)).total_seconds()/60
        connections.append(dict(hypothesis="C35",date=d,direction=side,first_flight=first,second_flight=second,connection_minutes=wait,planning_mct=90,mct_status="SCENARIO_NOT_AIRPORT_CERTIFIED",calendar_gate=wait>=90,inventory_gate="UNKNOWN",partner_contract_gate="UNKNOWN"))
        check("C35 connection "+first,wait>=90)
write("C35_partner_thresholds.csv",c35);write("C35_connections.csv",connections)

write("dated_flights.csv",FLIGHTS)
# Every concrete aircraft-slot chain must have enough elapsed time and airport continuity.
groups=defaultdict(list)
for f in FLIGHTS:
    groups[(f["hypothesis"],f["network"],f["tail_slot"],str(f["date"]))].append(f)
for k,fs in groups.items():
    fs.sort(key=lambda f:f["departure_utc"])
    for x,y in zip(fs,fs[1:]):
        check("same day tail connection "+y["flight_id"], x["destination"]==y["origin"] and dt.datetime.fromisoformat(y["departure_utc"])-dt.datetime.fromisoformat(x["arrival_utc"])>=dt.timedelta(minutes=45))

summary=[]
for cid,rows in [("C10",c10),("C14",c14),("C17",c17),("C31",c31),("C35",c35)]:
    summary.append(dict(id=cid,status="EVALUATED_CONDITIONAL_THRESHOLD",scenario_rows=len(rows),market_acceptance="NOT_ESTABLISHED",resource_acceptance="NOT_ESTABLISHED",full_budget_acceptance="NOT_ESTABLISHED",forecast="NO"))
write("hypothesis_status.csv",summary)
(OUT/"checks.json").write_text(json.dumps({"passed":sum(x["passed"] for x in CHECKS),"total":len(CHECKS),"independent_review":"NOT_RUN","checks":CHECKS},ensure_ascii=False,indent=2)+"\n")
files=[]
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name!="manifest.json":
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
(OUT/"manifest.json").write_text(json.dumps(files,indent=2)+"\n")
print(json.dumps({"hypotheses":5,"dated_flight_rows":len(FLIGHTS),"checks":len(CHECKS),"output_files":len(files)},indent=2))
