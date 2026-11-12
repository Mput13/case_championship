"""P05 numerical checks and explicit empirical/nonempirical validation boundaries."""
import calendar
import copy
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict

from model import ROOT, VERSION, Demand, choice_shares, coefficients, materialize_response, monthly_profile, net_fare, price_for_share, read_csv, write_csv, write_json

sys.path.insert(0,str(ROOT/"inputs/P06"))
from engine.choice import allocate, apply_response
from engine.common import ContractError
from engine.operations import check_itineraries


def run_choice(fragment, flights):
    b={k:fragment[k] for k in ("markets","products","contracts","choice_model","response_policy")}
    b["flights"]=flights;b["economic_events"]=[]
    return allocate(b,apply_response(b))


def summary(fragment, result):
    ps={p["product_id"]:p for p in fragment["products"]}
    rw=[a for a in result["allocations"] if a["owner"]=="RW" and a["kind"]=="air"]
    return dict(RW_journeys=sum(a["carried"] for a in rw),RW_passenger_segments=sum(a["carried"]*len(ps[a["product_id"]]["legs"]) for a in rw),
                net_revenue_scenario=sum(a["carried"]*ps[a["product_id"]]["net_fare"] for a in rw),
                total_potential=sum(m["potential_journeys"] for m in fragment["markets"]),
                total_final_choice=sum(a["final_choice"] for a in result["allocations"]),
                own_migration=None,actual_new_to_RW=None,full_operating_result=None,peak_funding=None)


def solve(A,b):
    a=[list(row)+[v] for row,v in zip(A,b)];n=len(b)
    for col in range(n):
        j=max(range(col,n),key=lambda i:abs(a[i][col]));a[col],a[j]=a[j],a[col]
        if abs(a[col][col])<1e-10:
            raise ValueError("unidentified OLS design")
        den=a[col][col];a[col]=[x/den for x in a[col]]
        for i in range(n):
            if i!=col:
                factor=a[i][col];a[i]=[x-factor*y for x,y in zip(a[i],a[col])]
    return [r[-1] for r in a]


def empirical_checks():
    d=Demand();hist=read_csv(ROOT/"historical_evidence.csv");records=[]
    for r in hist:
        if r["period"]!="2025" or r["coverage"]!="airport" or r["use"]!="fit" or r["annual_factor"]!="1" or not r['source'].startswith('https://'):
            continue
        a,b=r["from_iata"],r["to_iata"]
        s=d.segments.get(tuple(sorted((a,b))))
        if not s or not s["rail_hr"]:
            continue
        X=[1,math.log(float(s["pop_a"])*float(s["pop_b"])),math.log(float(s["rail_hr"])),float("MOW" in (a,b)),float(bool({"AER","MRV"}&{a,b}))]
        records.append(dict(group=a,a=a,b=b,x=X,observed=float(r["pax"]),source=r["source"]))
    predictions=[]
    for group in sorted({r["group"] for r in records}):
        train=[r for r in records if r["group"]!=group]
        A=[[sum(r["x"][i]*r["x"][j] for r in train) for j in range(5)] for i in range(5)]
        b=[sum(r["x"][i]*math.log(r["observed"]) for r in train) for i in range(5)]
        beta=solve(A,b)
        for r in records:
            if r["group"]==group:
                pred=math.exp(sum(a*b for a,b in zip(beta,r["x"])))
                predictions.append(dict(heldout_origin=group,origin=r["a"],destination=r["b"],observed_segments=r["observed"],predicted_segments=pred,
                                        ratio=pred/r["observed"],absolute_percentage_error=abs(pred/r["observed"]-1)*100,training_rows=len(train),
                                        source=r["source"],grain="annual_airport_pair_passenger_segments",not_endpoint_OD_validation=True,assumption_id="P05-A15"))
    write_csv(ROOT/"segment_proxy_holdout.csv",predictions)
    monthly=read_csv(ROOT/"aviation_monthly_history.csv")
    actual={int(r["month"][5:]):float(r["value"]) for r in monthly if r["month"].startswith("2026") and r["entity"]=="Aeroflot Group" and r["metric"]=="passengers_domestic"}
    old={int(r["month"][5:]):float(r["value"]) for r in monthly if r["month"].startswith("2025") and r["entity"]=="Aeroflot Group" and r["metric"]=="passengers_domestic"}
    s25=sum(old[m] for m in actual);s26=sum(actual.values())
    prof=[]
    for m in sorted(actual):
        # No 2026 value was used in the fixed 2025 profile or demand forecast.
        p=old[m]/s25;v=actual[m]/s26
        prof.append(dict(month=f"2026-{m:02d}",predicted_share_from_2025_JanOct=p,observed_share_2026_JanOct=v,share_error_pp=100*(p-v),
                         source_id="NEW_AEROFLOT_2025_MONTHLY;NEW_AEROFLOT_2026_MONTHLY",test="out_of_period_aggregate_season_profile_only",assumption_id="P05-A03"))
    write_csv(ROOT/"season_profile_holdout.csv",prof)
    return dict(segment_proxy=dict(records=len(predictions),heldout_groups=sorted({r["heldout_origin"] for r in predictions}),median_abs_error_percent=statistics.median(r["absolute_percentage_error"] for r in predictions),
                                  maximum_ratio=max(r["ratio"] for r in predictions),minimum_ratio=min(r["ratio"] for r in predictions),
                                  status="OUT_OF_GROUP_PROXY_TEST_ON_INHERITED_HETEROGENEOUS_SOURCE_EXTRACTS_NOT_ENDPOINT_OR_BEHAVIOURAL_VALIDATION"),
                aggregate_season=dict(holdout_months=len(prof),mean_absolute_share_error_pp=statistics.mean(abs(r["share_error_pp"]) for r in prof),
                                      total_variation_distance=.5*sum(abs(r["share_error_pp"])/100 for r in prof),
                                      status="OUT_OF_PERIOD_PRIMARY_CARRIER_AGGREGATE_CHECK; NOT_ROUTE_SEASON_VALIDATION"),
                endpoint_OD_holdout=dict(n=0,status="NOT_AVAILABLE; annualOD prior remains scenario"),
                behavioural_choice_holdout=dict(n=0,status="NOT_IDENTIFIED; no booking choices plus availability"))


def main():
    checks=[]
    def check(name,condition,detail):
        checks.append(dict(check=name,passed=bool(condition),detail=detail))
        if not condition:raise AssertionError(name+": "+str(detail))
    rows=read_csv(ROOT/"od_monthly.csv");groups=defaultdict(list)
    keys=[]
    for r in rows:
        key=(r["external_scenario_id"],r["demand_pool_id"],r["month"],r["customer_segment"])
        keys.append(key);groups[(r["external_scenario_id"],r["demand_pool_id"],r["month"][:4])].append(r)
    check("disjoint_pool_month_segment_keys",len(keys)==len(set(keys)),len(keys))
    check("full_24month_cycle_each_scenario_direction",all(len(v)==12 for v in groups.values()),len(groups))
    maxerr=max(abs(sum(float(r["realized_air_reference_journeys"]) for r in rs)-float(rs[0]["annual_both_directions_scenario"])*.5) for rs in groups.values())
    check("annual_monthly_direction_conservation",maxerr<1e-6,maxerr)
    check("no_unknown_becomes_zero",all(float(r["potential_journeys"])>0 and r["lower"]=="UNKNOWN" and r["upper"]=="UNKNOWN" and r["status"]=="scenario" for r in rows),"All prior positive; unknown empirical intervals retained")
    for y in (2027,2028):
        for name in ("aeroflot_2025_domestic","national_blocks","flat_daily"):
            check("profile_sum_"+str(y)+name,abs(sum(monthly_profile(y,name).values())-1)<1e-12,"full calendar including leap day")
    p03=json.loads((ROOT/"inputs/P03/sp_adapter/p06_bound_fragments.json").read_text())
    flights=p03["branches"]["phased"]["project"]["flights"]
    fs={f["flight_instance_id"]:f for f in flights};frags=json.loads((ROOT/"producer_fragments.json").read_text())
    allocations=[];seatrows=[];summaries={};sensitivity=[];thresholds=[]
    for s,sides in frags.items():
        summaries[s]={}
        check("common_project_keep_markets_"+s,sides["project"]["markets"]==sides["keep"]["markets"],"identical common disjoint demand")
        for side,frag in sides.items():
            u=check_itineraries(dict(products=frag["products"],flights=flights))
            check("ordered_dated_itinerary_contract_"+s+side,not u,u)
            result=run_choice(frag,flights if side=="project" else [])
            summaries[s][side]=summary(frag,result)
            allocations.extend(dict(a,scenario_id=s,side=side) for a in result["allocations"])
            seatrows.extend(dict(a,scenario_id=s,side=side) for a in result["seats"])
            check("pool_conservation_"+s+side,abs(summaries[s][side]["total_potential"]-summaries[s][side]["total_final_choice"])<1e-6,summaries[s][side])
            check("dated_capacity_"+s+side,all(a["carried_segments"]<=a["saleable_seats"]+1e-7 for a in result["seats"]),"common physical inventory; no separate capacity for transfers")
        f=sides["project"];r=run_choice(f,flights)
        ps={p["product_id"]:p for p in f["products"]}
        # One fare per journey. Per-leg revenue only allocates that same fare.
        revenue=sum(a["carried"]*ps[a["product_id"]]["net_fare"] for a in r["allocations"] if a["owner"]=="RW")
        legrev=sum(a["carried"]*ps[a["product_id"]]["net_fare"]*sum(ps[a["product_id"]]["revenue_weights"]) for a in r["allocations"] if a["owner"]=="RW")
        check("one_journey_fare_"+s,abs(revenue-legrev)<1e-7,[revenue,legrev])
        # Actual gross-price perturbation recomputes utility and net revenue.
        for multiplier in (.7,1,1.3,1.5):
            q=copy.deepcopy(f)
            for p in q["products"]:
                if p["kind"]=="air":p["gross_fare"]*=multiplier;p["net_fare"]*=multiplier
            out=run_choice(q,flights)
            sensitivity.append(dict(scenario_id=s,axis="RW_gross_price",value=multiplier,**summary(q,out),assumption_id="P05-A06"))
        for factor in (.1,.3508,1,2.2398):
            q=copy.deepcopy(f)
            for m in q["markets"]:m["potential_journeys"]*=factor
            # Ground envelope follows total potential, not a physical timetable.
            ms={(m['demand_pool_id'],m['month'],m['customer_segment']):m for m in q['markets']}
            for p in q['products']:
                if p['kind']=='ground':p['capacity']=ms[(p['demand_pool_id'],p['month'],p['customer_segment'])]['potential_journeys']
            sensitivity.append(dict(scenario_id=s,axis="potential_scale",value=factor,**summary(q,run_choice(q,flights)),assumption_id="P05-A01"))
        q=materialize_response(f,"price_match10")
        sensitivity.append(dict(scenario_id=s,axis="competitor_response_pricecut",value=.1,**summary(q,run_choice(q,flights)),assumption_id="P05-A13"))
        for axis,values in [('price_halfodds_rub',(1500,3000,6000)),('price_halfodds_rub_at_price1.3',(1500,3000,6000)),('time_halfodds_minutes',(60,120,240)),('log_frequency',(0,.5,1)),('stop_penalty',(0,-math.log(2),-math.log(4)))]:
            for value in values:
                q=copy.deepcopy(f)
                if axis.startswith('price_halfodds_rub'):q['choice_model']['price_per_rub']=-math.log(2)/value
                elif axis=='time_halfodds_minutes':q['choice_model']['time_per_minute']=-math.log(2)/value
                elif axis=='log_frequency':q['choice_model']['log_frequency']=value
                else:
                    for p in q['products']:
                        if p['kind']=='air':p['intercept']+=(value-f['choice_model']['stop_penalty'])*(len(p['legs'])-1)
                # Reanchor fixed reference shares when slopes change: no fake shift
                # in the reference mapping caused only by a utility-unit change.
                deltaP=q['choice_model']['price_per_rub']-f['choice_model']['price_per_rub']
                deltaT=q['choice_model']['time_per_minute']-f['choice_model']['time_per_minute']
                for p in q['products']:
                    if p['kind']=='air':p['intercept']-=deltaP*p['reference_gross_fare']+deltaT*p['reference_duration_minutes']
                    elif p['kind']=='ground':p['intercept']-=deltaP*p['gross_fare']+deltaT*p['duration_minutes']
                if axis=='price_halfodds_rub_at_price1.3':
                    for p in q['products']:
                        if p['kind']=='air':p['gross_fare']*=1.3;p['net_fare']*=1.3
                sensitivity.append(dict(scenario_id=s,axis=axis,value=value,**summary(q,run_choice(q,flights)),assumption_id='P05-A07'))
        for share in (.3,.6,.85):
            q=copy.deepcopy(f)
            for m in q['markets']:m['potential_journeys']=m['realized_air_reference_journeys']/share
            ms={(m['demand_pool_id'],m['month'],m['customer_segment']):m for m in q['markets']}
            for p in q['products']:
                if p.get('outside_component')=='UNREPRESENTED_EXISTING_AIR':p['intercept']=math.log(share)
                elif p.get('outside_component')=='NO_TRAVEL':p['intercept']=math.log((1-share)*.25)
                elif p['kind']=='ground':
                    p['intercept']+=math.log((1-share)*.75/.3)
                    p['capacity']=ms[(p['demand_pool_id'],p['month'],p['customer_segment'])]['potential_journeys']
                elif p['kind']=='air':p['intercept']+=math.log(share/.6)
            sensitivity.append(dict(scenario_id=s,axis='reference_air_share',value=share,**summary(q,run_choice(q,flights)),assumption_id='P05-A05'))
        for pp in f["products"]:
            if pp["kind"]!="air":continue
            others=[x for x in f["products"] if (x["demand_pool_id"],x["month"],x["customer_segment"])==(pp["demand_pool_id"],pp["month"],pp["customer_segment"])]
            fare=price_for_share(others,pp["product_id"],f["choice_model"],.25)
            p0=copy.deepcopy(others)
            for x in p0:
                if x['product_id']==pp['product_id']:x['gross_fare']=max(0,fare)
            thresholds.append(dict(scenario_id=s,product_id=pp["product_id"],demand_pool_id=pp["demand_pool_id"],departure_date=pp["departure_date"],
                target_unconstrained_share=.25,gross_fare_at_target_share_rub=fare,nonnegative_fare_target_feasible=fare>=0,
                current_share=choice_shares(others,f["choice_model"])[pp["product_id"]],actual_full_cost_rub=None,
                maximum_net_incremental_cost_formula="joint incremental revenue less all other accepted net effects; see integration diagnostic; NEVER sum standalone products",
                max_distribution_drag_formula="1 - accepted_incremental_cost*(1+VAT)/(joint_carried*net_of_pass_through_gross); requires fullKEEP",
                assumption_id="P05-A16"))
    check("net_unknown_propagates",net_fare(5200,None,.03) is None,"UnknownVAT does not silently become0")
    check("gross_net_bridge_example",abs(net_fare(5200,.1,.08)-4349.090909090909)<1e-8,"Diagnostic5200RUB; not realised fare")
    # Ref mapping identity is documented as algebra, not an empirical pass.
    check("reference_air_mapping_once",abs((100/.6)*.6-100)<1e-10,dict(realized_air=100,potential=100/.6,wrong_double_no_travel_result=60))
    # Pin early-kernel response scope defect with an independent two-month case.
    p=copy.deepcopy(frags['base']['project']['products'][0]);p.update(product_id='competitor-January',demand_pool_id='scope-test',month='2027-01',frequency=1,gross_fare=100,intercept=0)
    rw=copy.deepcopy(p);rw.update(product_id='RW-February',owner='RW',month='2027-02',frequency=1)
    scoped=dict(products=[p,rw],response_policy=dict(rules=[dict(demand_pool_id='scope-test',rw_frequency_at_least=1,target_product_ids=['competitor-January'],gross_fare_multiplier=.9,frequency_multiplier=1,intercept_delta=0,assumption_id='P05-A13')]))
    leaked=apply_response(scoped)[0]['gross_fare']
    write_json(ROOT/'engine_scope_counterexample.json',dict(subject_commit='bc70308fe091c5767dbf26b02d06a7d750a65614',input=scoped,January_fare_without_January_RW_expected=100,actual=leaked,
        finding='P06early trigger sums RWfrequency across all months/segments; P05 materialize_response scopes before emitting activated rules',impact='conditional new response policy must retain high-level identity; materialized P/KEEP objects may differ and P06earlycompare requires identicalresponse blobs'))
    check("response_scope_counterexample_reproduced",leaked==90,"Defect documented, not P06 patched")
    # Clone demonstration: ordinary MNL changes share if a fare family is duplicated.
    one=[dict(product_id='air',kind='outside',availability=True,intercept=0),dict(product_id='no',kind='outside',availability=True,intercept=0)]
    clone=one+[dict(product_id='air-copy',kind='outside',availability=True,intercept=0)]
    check("fare_family_clone_IIA_counterexample",choice_shares(one,{})['no']==.5 and abs(choice_shares(clone,{})['no']-1/3)<1e-12,"Duplicate same-service fare alternatives change share; panel collapsed at flight-date in identification audit")
    empirical=empirical_checks()
    ic=json.loads((ROOT/'engine_interface/checks.json').read_text())
    check('pinned_evaluate_compare_scenario',ic['scenario_evaluations']==4 and all(x['allocation_executed'] and x['summary']['operating_result'] is None and x['peak_funding'] is None for x in ic['checks']),
          'Real P03/P05 producer records; no copied toy economics; conditional operations; unpriced costs/cash remainnull')
    write_csv(ROOT/"allocations.csv",allocations);write_csv(ROOT/"flight_seat_checks.csv",seatrows);write_csv(ROOT/"sensitivity.csv",sensitivity);write_csv(ROOT/"thresholds.csv",thresholds)
    write_json(ROOT/"diagnostic_results.json",dict(version=VERSION,scope="P03selected11–17Dec2028 only; not annual programme or actualRW results",summaries=summaries,
        result_limits="ExistingRW migration, unknown existing flights/blocks, fulloperating costs and cash missing. KEEP is diagnostic outside alternatives, not accepted whole-businessKEEP."))
    validation=dict(version=VERSION,status="PASS_MECHANICAL_WITH_EXPLICIT_EMPIRICAL_GAPS",checks=checks,empirical=empirical,
                    calibration_status="ANNUAL_OD_AND_CHOICE_PARAMETERS_REMAIN_SCENARIO",independent_review="NOT_RUN_AUTHOR_CANNOT_ACCEPT_OWN_PACKAGE",
                    full_engine_CE_acceptance="NOT_CLAIMED; inputpinP06early",unknown_is_zero=False,scenario_points_are_confidence_bounds=False,
                    actual_RedWings_quality_or_profit_score=None,source_coverage="37 inherited flow records;new264 monthly carrieraggregatecells;0 newprimaryrouteOD observations",
                    used_assumption_ids=[f"P05-A{i:02d}" for i in range(1,17)],engine_interface_checks='engine_interface/checks.json')
    write_json(ROOT/"validation.json",validation)
    print(json.dumps(dict(checks=len(checks),failed=sum(not c['passed'] for c in checks),empirical=empirical,diagnostic_summaries=summaries),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
