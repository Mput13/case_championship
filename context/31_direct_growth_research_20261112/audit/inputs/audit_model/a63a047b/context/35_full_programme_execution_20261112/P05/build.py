"""Build P05 from immutable inputs. Outputs stay in this package directory."""
import copy
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

from model import ROOT, VERSION, Demand, city, monthly_profile, producer_fragment, read_csv, write_csv, write_json


def assumption(aid,value,unit,basis,range_,affected,sensitivity,refinement):
    return dict(assumption_id=aid,value=value,unit=unit,selected_by="P05 research agent gpt-6.1-sol xhigh",
                basis=basis,approval_status="ANALYST_ROUTINE_CHOICE_NOT_USER_APPROVED_PARAMETER",range_or_unknown=range_,
                affected_conclusions=affected,sensitivity=sensitivity,refinement=refinement,version=VERSION)


def assumptions():
    return [
        assumption("P05-A01","author od_pairs.od_base and od_cautious; gravity fallback only when absent","bidirectional annual endpoint journeys scenario",
                   "Pinned dceadc9 src/od_model.py recovers OD from mixed segment counts with shortest one-stop2026 network. Its legacy fit includes fourH1rows doubled, one regionalrow and one internally citedKUFrow. Pure od_pairs avoids demand_estimates December seats; legacy annualization is retained only as scenario lineage, not accepted historical full-year fact. It does NOT identify true endpoint OD.",
                   "UNKNOWN population forecast bounds; legacy cautious/base residual0.3508 is stress, not confidence interval",
                   "all market scales and carried passengers","scale0.1, legacy0.3508,1,legacy2.2398; solve cost/share demand threshold",
                   "Monthly ticket/coupon OD2025 and2026 incl transfers, ticketing coverage and ground/no-travel sampling"),
        assumption("P05-A02",0.5,"directional share of bidirectional OD","Source totals combine both directions; neutral symmetric split, no measured directionality",
                   "Logical0..1 with opposite=1-share; empirical bounds UNKNOWN","directional market and load asymmetry","0.3/0.5/0.7 diagnostic; reverse changes jointly","Separate departure/arrival OD counts by month"),
        assumption("P05-A03","AeroflotGroup domestic2025 monthly shares, leap-day daily-intensity adjustment; national_blocks and flat_daily diagnostics","annual fraction",
                   "NEW_AEROFLOT_2025_MONTHLY sheetAeroflotGroup row13 exact monthly carrier traffic. NEW_AEROFLOT_2026_MONTHLY JanOct reserved for out-of-period profile test. Transferred to endpoint markets as analogue. National checks H1=38.1/81.45;Q3=25.2/81.45;Q4=18.15/81.45. Carrier mix, supply and route differences unresolved.",
                   "UNKNOWN route seasonal envelope; flat_daily is diagnostic counterfactual","month volumes, weak season and month funding",
                   "Aeroflot2025 vs national_blocks vs flat_daily;2026outofperiod aggregate check; independent route month multipliers renormalized annually","Monthly same-pair OD; airports/airlines full-year comparable counts"),
        assumption("P05-A04","base2025 level flat; cautious legacyOD*cumulative0.962^(year-2025)","annual multiplier",
                   "Base is no-growth scenario; cautious continues observed national domestic2025 decline3.8%, not a forecast. No optimism selected for profitability.",
                   "UNKNOWN forward market growth range","2027–2028 total market","vary annual growth; change-of-decision threshold from supplied costs","Comparable2026 same-market observations and forecast assumptions"),
        assumption("P05-A05","reference air0.6;ground0.3;no-travel0.1; potential=legacyair/0.6","shares of potential pool",
                   "Unidentified mapping: reference normalization reproduces air prior as an algebraic identity. Outside composite represents unresolved competing air; not physical seats. One outside choice only.",
                   "airshare0<s<=1; sample0.3/0.6/0.85 diagnostic, empirical bounds UNKNOWN; ground/no-travel split UNKNOWN",
                   "induced journeys, ground substitution, diversion and new-to-RW","hold realizedair fixed, vary potential mapping; ownRW share UNKNOWN0..1 logical envelope","Multimodal trip survey and true ticketOD; ownRW source sales"),
        assumption("P05-A06","gross=max(5200,5200+6.3*(km-393)); constant2026RUB; one basket","RUB/oneway journey including20kg",
                   "P02 Standard WZ quotes5200 on8Dec2026 and12Jan2027, same market/airline. 6.3RUB/km is an explicit transfer of author's scenario curve slope, formerly labelled net; here NEW gross scenario, not fitted law. Floor5200 is analyst scenario.",
                   "UNKNOWN real market fare curve; two independent flight-date baskets, not four independent fares",
                   "price choice and revenues","fare multipliers0.7/1/1.3/1.5 recalculate choice; max-fare thresholds","Same-date alternative carrier20kg totals across seasons and lead times; realized booking ledger"),
        assumption("P05-A07","base odds halve per3000RUB/per120min;frequency coefficient1;stop penalty ln2. cautious1500RUB/240min/.5/ln4","utility units",
                   "Interpretable analyst diagnostic points; MIT supports model structure and data requirements, NOT these coefficients. No booking choices/availability panel identifies them.",
                   "UNKNOWN empirical coefficient bounds; stress grids diagnostic only","all allocation and capture rankings",
                   "price halfodds1500/3000/6000;time60/120/240;freq0/.5/1;stop0/ln2/ln4; IIA clone counterexample",
                   "Estimate likelihood on actual accepted/rejected alternatives with seat availability; holdout on markets/time blocks"),
        assumption("P05-A08","dated P03 RW scenario flights only; cohort tied to first departure UTC day; monthly share prorated by calendar days;45..240min connection;equal-leg revenue weights; diagnostic proposed retail products without advance sales/contractblocks","day/minute/fraction",
                   "No demand permitted on an unsupplied date. Date-flexibility, commercial connection acceptance, MCT and proration not measured; numeric window is a diagnostic candidate generator, not certified airportMCT.",
                   "UNKNOWN actual date-flexibility/MCT; test45/60/90 and max180/240; proration any nonnegative sum1",
                   "dated itinerary usability and allocation; does not annualize P03 December week",
                   "remove transfer products, alter connection window; direct retained","Ticket availability, airportMCT, RW through-ticket agreements, preferred travel-day survey"),
        assumption("P05-A09","ground reference fare0.5*airfare; rail hours from author table else96h; scenario capacity=potential, hence nonbinding","RUB/minute/journeys",
                   "Rail time is a legacy source proxy (sometimes96h imputation); fare and capacity are explicit illustrative alternative, not a measured train/bus inventory. Ground intercept normalization is not observed preference.",
                   "UNKNOWN fare/capacity/support; factor0.25/0.5/1 diagnostic, do not interpret as empirical bounds",
                   "ground-versus-air choice and baseline mapping","vary price/time/capacity; absent ground alternative scenario","Primary dated railway/bus fare20kg-equivalent basket and availability; applicable journey time"),
        assumption("P05-A10","regional baseVAT0 subject to eligibility; cautiousVAT0.10 diagnostic; future actual rate UNKNOWN","tax fraction",
                   "FNS2019 source describes outside Moscow/Moscowregion route condition; all intermediate points matter. It is not accepted2027–2028 legal determination. Stress is not legal fact.",
                   "UNKNOWN future legal treatment;0/.10 diagnostic cases","net journey revenue only; income tax remains P04 separately","net=G/(1+VAT); check whole ordered route","Current TaxCode for travel date, operator/legal invoice mapping; P04 legal review"),
        assumption("P05-A11","distribution drag base3%, cautious8%, ceiling0% only structural bound","fraction of transport revenue excludingVAT",
                   "No RW agency/acquiring agreement. These are analyst diagnostic points, not negotiated cost estimates. Model nets distribution once; P04 must exclude corresponding duplicated passenger cost.",
                   "UNKNOWN empirical drag bounds; mathematical0..1","net revenue and incremental operating result","solve maximum affordable distribution drag from actual incremental cost; sweep0/.03/.08/.15","RW sales-channel mix, agent/acquiring rates, commissions policy and cost ledger"),
        assumption("P05-A12","20kg basket includes its baggage; additional ancillary and separately paid pass-through excluded in reference scenario; cash_profileUNKNOWN","RUB/journey and cash dates",
                   "No extra baggage income added to included allowance. Airline airport/handling costs stay P04, not pass-through. Carried journeys not multiplied again by refund probability; cancellations retained fees require separate events.",
                   "Actual extra ancillary/pass-through/cash UNKNOWN; reference exclusion is a scope choice, not actual zero",
                   "net fare, no double refund/distribution/airport deductions; no cash forecast","vary ancillary and genuine pass-through separately; no invented settlement date","Fare tax breakdown, agent settlement, refunds/no-shows and ancillary recognized revenue"),
        assumption("P05-A13","same high-level passive or price_match10 policy forP andKEEP; month/cohort-specific triggers precomputed","policy",
                   "Incumbent reaction unobserved;10%farecut is diagnostic. P06early sums frequencies across months; adapter binds rule to exact pool/month/cohort then emits activated intercept shift. No added competitor supply.",
                   "UNKNOWN reaction policy;0/10/20%farecut diagnostic only","competitive capture and deltas","compare passive vs pricecut; scope-leak counterexample","Dated competitor price/capacity response panel, local city research"),
        assumption("P05-A14","MOW airport demand aliases one city pool; all others author endpoint markets; physical airport legs unchanged","market mapping",
                   "One forecast per directed endpoint pair independent of programme. Author catchment overlaps may bias prior population; no claim that regional population is uniquely assigned. No same-city airport source counts added.",
                   "UNKNOWN own-airport substitution and disjoint catchment geometry","sharedpool conservation, MOW demand and own migration","reuse same pool across all alternatives; do not duplicateMOW forZIA","Geocoded catchment/trip origins, airport-choice survey and nonoverlap partition"),
        assumption("P05-A15","grouped leave-origin-out OLS only for annual airport segment proxy; exclude partial-year, regional and airline-subset rows","validation design",
                   "Retained observations have same reported annual airport segment unit. These historical sources are inherited secondary extracts. Segment proxy prediction cannot validate endpointOD, monthly seasons or behaviour.",
                   "External primary endpointOD holdout UNKNOWN","validation/calibration status","report every heldout prediction incl failures; no train reuse as empiricalholdout","New independent compatible endpointOD observations outside fitting group"),
        assumption("P05-A16","unconstrained share and revenue thresholds; actual full operating costs not supplied toP05","threshold method",
                   "Threshold computations use conservation/choice algebra. Endogenous price-demand response recomputed. Cost threshold remains symbolic until P04programme drivers, alternative use and KEEP scope accepted.",
                   "UNKNOWN actual breakeven cost; no profitability assertion","price, demand and commission decision thresholds","break-evenRUB=carried*netfare; affordability condition explicit","Full incremental programme costs and jointly recomputedKEEP"),
    ]


def main():
    manifest=json.loads((ROOT/"input_manifest.json").read_text())
    for r in manifest:
        assert hashlib.sha256((ROOT/r["local_path"]).read_bytes()).hexdigest()==r["sha256"], r["input_id"]
    d=Demand(); cov=read_csv(ROOT/"inputs/P02/market_coverage.csv")
    domestic=set(); exclusions=[]
    for r in cov:
        a,b=city(r["origin"]),city(r["destination"])
        if a in d.nodes and b in d.nodes and a!=b:
            domestic.add(tuple(sorted((a,b))))
        else:
            exclusions.append(dict(market_id=r["market_id"],origin=r["origin"],destination=r["destination"],disposition="P02I_SEPARATE_VERSION_OR_UNKNOWN_NODE",reason="No unsourced foreign OD or node extrapolation in standaloneCASE_SJ",status="not_zero_demand"))
    p03=json.loads((ROOT/"inputs/P03/sp_adapter/p06_bound_fragments.json").read_text())
    flights=p03["branches"]["phased"]["project"]["flights"]
    nodes={city(f[k]) for f in flights for k in ("origin_airport","destination_airport")}
    # Include all endpoint pairs on this diagnostic network, including transfers.
    domestic.update(tuple(sorted(x)) for x in itertools.combinations(nodes,2))
    reg=assumptions();write_json(ROOT/"assumptions_register.json",reg);write_csv(ROOT/"assumptions_register.csv",reg)
    write_csv(ROOT/"assumption_changes.csv",[dict(assumption_id=r["assumption_id"],change="NEW_EXPLICIT_P05_SCENARIO_OR_ADAPTER",previous="Historical baseline preserved; new values not retroactive corrections",affected=r["affected_conclusions"]) for r in reg])
    rows=[]
    for a,b in sorted(domestic):
        for scenario in ("base","cautious"):
            for x,y in [(a,b),(b,a)]:
                for year in (2027,2028):
                    for mon in range(1,13):
                        m=d.market(x,y,f"{year}-{mon:02d}",scenario)
                        rows.append({k:(";".join(v) if isinstance(v,list) else v) for k,v in m.items()})
    write_csv(ROOT/"od_monthly.csv",rows)
    write_csv(ROOT/"market_exclusions.csv",exclusions)
    prof=[]
    for year in (2027,2028):
        for name in ("aeroflot_2025_domestic","national_blocks","flat_daily"):
            for month,share in monthly_profile(year,name).items():
                prof.append(dict(year=year,month=month,profile=name,annual_share=share,status="scenario_analogue_not_route_month_observation",source_id="NEW_AEROFLOT_2025_MONTHLY" if name=="aeroflot_2025_domestic" else "NEW_FAVT_H1;NEW_MINTRANS_9M;NEW_FAVT_2025",assumption_id="P05-A03"))
    write_csv(ROOT/"month_profiles.csv",prof)
    fragments={};nets=[];legs=[]
    for scenario in ("base","cautious"):
        frag=producer_fragment(flights,scenario);frag["assumptions"]=reg
        nets.extend(frag.pop("net_yield_rows"))
        keep=copy.deepcopy(frag);keep["products"]=[p for p in keep["products"] if p["kind"]!="air"]
        for pp in frag["products"]:
            for seq,(fid,w) in enumerate(zip(pp["legs"],pp["revenue_weights"]),1):
                legs.append(dict(scenario_id=scenario,itinerary_id=pp["product_id"],departure_date=pp["departure_date"],leg_sequence=seq,flight_instance_id=fid,
                                 net_journey_fare_rub=pp["net_fare"],revenue_allocation_weight=w,assumption_id="P05-A08"))
        fragments[scenario]=dict(project=frag,keep=keep)
    write_json(ROOT/"producer_fragments.json",fragments)
    write_csv(ROOT/"net_yield.csv",nets)
    write_csv(ROOT/"ordered_legs.csv",legs)
    from model import coefficients
    write_json(ROOT/"choice_model.json",dict(version=VERSION,model="conditional_logit_with_capacity_recapture_P06",calibration_status="SCENARIO_NOT_IDENTIFIED",
        scenarios={s:coefficients(s) for s in ("base","cautious")},utility="intercept + beta_price*gross_fare + beta_time*duration_minutes + beta_frequency*ln(frequency); stop penalty and per-date normalization in intercept",
        supply="Externally supplied exact dated physical legs only. Unknown competitor air is outside composite, not physical inventory; not carrier segment output.",
        potential_mapping="realized_air_reference/0.6; reference air/ground/no-travel masses0.6/0.3/0.1; normalized algebraically, NOT empirical calibration",
        outside_interpretation="NO_TRAVEL and UNREPRESENTED_EXISTING_AIR separate choice masses; potential pool includes both. No double no-travel deduction.",
        date_cohorts="Disjoint customer_segment travel_date:YYYY-MM-DD, monthly potential prorated by actual days. Remaining dates stay outside diagnostic fragment, not zero demand.",
        own_migration="UNKNOWN existingRW share. Requires explicit KEEP old products before new-toRW or compatible carrier share claims.",
        IIA="Known MNL limitation. Do not treat fare families for same physical service as independent equivalent opportunities; route/date normalization retained.",
        price_and_net="Choice uses gross comparable basket; revenue uses one net fare per carried journey. Net distribution drag excluded from P04cost duplication.",
        unresolved=["booking-choice likelihood unavailable","season/lead effects confounded in quotations","true endpointOD reconstruction not externally validated","same-market2026 monthly demand sparse"],
        required_patch_ids=["SP02","SP03","SP05","SP06","SP12","SP13"],assumption_ids=[r["assumption_id"] for r in reg]))
    # Historical rows retained separately, never assigned monthly observations.
    hist=read_csv(ROOT/"inputs/P02/historical_demand_context.csv")
    write_csv(ROOT/"historical_evidence.csv",[dict(r,grain="airport_passenger_segment" if r["coverage"]=="airport" else "region_or_airline_subset_segment",endpoint_OD_observed=False,
            monthly_observation=False,direct_annualization_applied_by_P05=False,inherited_prior_contains_legacy_annualization=r['annual_factor']!='1',collection="reused_pinned_P02v2") for r in hist])
    write_json(ROOT/"build_summary.json",dict(version=VERSION,input_files=len(manifest),P02_source_markets=len(cov),domestic_unordered_pairs=len(domestic),directed_ODs=2*len(domestic),
        forecast_months=24,forecast_scenarios=2,od_monthly_rows=len(rows),international_or_unknown_node_source_rows=len(exclusions),
        dated_P03_flights=len(flights),diagnostic_markets=len(fragments["base"]["project"]["markets"]),diagnostic_products=len(fragments["base"]["project"]["products"]),
        diagnostic_date_span=[min(f["departure_utc"][:10] for f in flights),max(f["departure_utc"][:10] for f in flights)],net_fare_rows=len(nets),
        acceptance="USABLE_SCENARIO_MODEL_AND_DATED_CHOICE_FRAGMENT; NOT_EMPIRICAL_CALIBRATION_OR_FULL_RW_ECONOMICS"))
    print((ROOT/"build_summary.json").read_text())


if __name__=="__main__":
    main()
