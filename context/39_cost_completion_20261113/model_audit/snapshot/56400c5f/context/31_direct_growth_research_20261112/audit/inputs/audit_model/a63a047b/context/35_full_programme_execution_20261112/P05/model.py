"""P05 scenario demand, passenger choice and journey revenue; Python standard library.

No observations are generated here. Annual author OD estimates remain an explicitly
unidentified prior. Products use externally supplied dated legs, never P02 offers
as physical inventory. All money is per one-way endpoint journey.
"""
import calendar
import copy
import csv
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = "P05-v1-scenario-20261112"
MOSCOW = {"MOW", "SVO", "DME", "VKO", "ZIA"}


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields=None):
    rows = list(rows)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: "UNKNOWN" if v is None else v for k, v in r.items()})


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def city(iata):
    return "MOW" if iata in MOSCOW else iata


def pool(a, b):
    return "CITY:" + city(a) + ">" + city(b)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [float(a["latitude_deg"]), float(a["longitude_deg"]), float(b["latitude_deg"]), float(b["longitude_deg"])])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 12742 * math.asin(min(1, math.sqrt(h)))


@lru_cache(maxsize=None)
def monthly_profile(year, profile="aeroflot_2025_domestic"):
    """National domestic carrier counts transferred as a scenario, not OD data.

    38.1m H1, 63.3m Jan-Sep, 81.45m year. Uniform daily intensity
    within each observed block is maximum-entropy interpolation, not observation.
    Leap years retain the annual block shares.
    """
    days = {m: calendar.monthrange(year, m)[1] for m in range(1, 13)}
    if profile == "aeroflot_2025_domestic":
        rows=[r for r in read_csv(ROOT/"aviation_monthly_history.csv") if r["month"].startswith("2025-") and r["entity"]=="Aeroflot Group" and r["metric"]=="passengers_domestic"]
        if len(rows)!=12:
            raise ValueError("full primary monthly profile required")
        daily={int(r["month"][5:]):float(r["value"])/calendar.monthrange(2025,int(r["month"][5:]))[1] for r in rows}
        annual=sum(daily[m]*days[m] for m in days)
        return {m:daily[m]*days[m]/annual for m in days}
    if profile == "flat_daily":
        return {m: days[m] / sum(days.values()) for m in days}
    blocks = [(range(1, 7), 38.1 / 81.45), (range(7, 10), (63.3-38.1)/81.45), (range(10, 13), (81.45-63.3)/81.45)]
    return {m: share*days[m]/sum(days[k] for k in ms) for ms, share in blocks for m in ms}


def coefficients(scenario="base"):
    return {
        "price_per_rub": -math.log(2)/(3000 if scenario == "base" else 1500),
        "time_per_minute": -math.log(2)/(120 if scenario == "base" else 240),
        "log_frequency": 1.0 if scenario == "base" else 0.5,
        "stop_penalty": -math.log(2) if scenario == "base" else -math.log(4),
        "assumption_id": "P05-A07",
        "calibration_status": "SCENARIO_NOT_IDENTIFIED_FROM_BOOKINGS",
        "version": VERSION,
    }


def gross_fare(distance, multiplier=1):
    # 5200 RUB Standard 20kg quote, SVX-UFA; distance slope is legacy analogue.
    # Anchor and slope do not identify realised yield or a causal price curve.
    return multiplier * max(5200, 5200 + 6.3*(distance-393))


def net_fare(gross, vat, distribution, pass_through=0, ancillary=0):
    if None in (gross, vat, distribution, pass_through, ancillary):
        return None
    if gross < pass_through or not 0 <= distribution <= 1 or vat < 0:
        raise ValueError("invalid revenue bridge")
    return (gross-pass_through)/(1+vat)*(1-distribution) + ancillary


def utility(p, c):
    if p["availability"] is None:
        raise ValueError("unknown availability is not unavailable supply")
    if p["availability"] is False:
        return -math.inf
    if p["kind"] == "outside":
        return p["intercept"]
    return p["intercept"] + c["price_per_rub"]*p["gross_fare"] + c["time_per_minute"]*p["duration_minutes"] + c["log_frequency"]*math.log(p["frequency"])


def choice_shares(products, c):
    us = [utility(p, c) for p in products]
    mx = max(us)
    ws = [math.exp(u-mx) for u in us]
    return {p["product_id"]: w/sum(ws) for p, w in zip(products, ws)}


class Demand:
    def __init__(self):
        p = ROOT / "inputs/BASE"
        self.nodes = {r["iata"]: r for r in read_csv(p/"data/processed/catchments.csv")}
        mows = [self.nodes[x] for x in MOSCOW if x in self.nodes]
        self.nodes["MOW"] = dict(self.nodes["SVO"], iata="MOW", pop=str(sum(float(x["pop"]) for x in mows)), main_city="Москва")
        self.od = {tuple(sorted((r["a"], r["b"]))): r for r in read_csv(p/"data/processed/od_pairs.csv")}
        self.segments = {tuple(sorted((r["a"], r["b"]))): r for r in read_csv(p/"data/processed/demand_pairs.csv")}
        self.fit = json.loads((p/"data/processed/od_fit.json").read_text())

    def prior(self, a, b):
        a,b=city(a),city(b)
        key=tuple(sorted((a,b)))
        if key in self.od:
            r=self.od[key]
            return float(r["od_base"]), float(r["od_cautious"]), "BASE_OD_PRIOR", r["via"], float(r["km"])
        if a not in self.nodes or b not in self.nodes:
            return None, None, "UNKNOWN_NODE", None, None
        A,B=self.nodes[a],self.nodes[b]
        s=self.segments.get(key)
        rail=float(s["rail_hr"]) if s and s["rail_hr"] else 96
        c=self.fit["coefficients"]
        q=math.exp(c["const"]+c["lnPP"]*math.log(float(A["pop"])*float(B["pop"]))+c["lnRail"]*math.log(rail)+c["mow"]*("MOW" in key)+c["resort"]*bool({"AER","MRV"}&set(key)))
        return q, q*self.fit["cautious_factor"], "BASE_GRAVITY_EXTRAPOLATION", "UNKNOWN", km(A,B)

    def market(self,a,b,month,scenario="base",segment="all",cohort_weight=1):
        q, cautious, source, via, distance=self.prior(a,b)
        if q is None:
            raise ValueError(f"unknown annual prior {a}>{b}; supply explicit scenario")
        y,m=map(int,month.split("-"))
        annual=q if scenario=="base" else cautious*(1-.038)**(y-2025)
        realized=annual*.5*monthly_profile(y)[m]*cohort_weight
        potential=realized/.6
        return dict(demand_pool_id=pool(a,b),month=month,customer_segment=segment,potential_journeys=potential,
                    market_basis="potential_travel",mapping_to_potential="author_realized_air_OD_prior / reference_air_share0.6; outside options chosen once; directional0.5; cohort_weight="+str(cohort_weight),
                    origin_market=city(a),destination_market=city(b),direction=city(a)+">"+city(b),source_id=source,
                    source_period="2025 heterogeneous segment-supported OD reconstruction; not observed endpoint OD",
                    as_of="2026-11-12",coverage="CASE_SJ domestic endpoint market; seasonal AeroflotGroup2025 analogue; conditional estimate; no international extension",
                    status="scenario",assumption_id="P05-A01",assumption_ids=["P05-A01","P05-A02","P05-A03","P05-A04","P05-A05"],
                    lower=None,upper=None,range_basis="UNKNOWN empirical forecast interval; base/cautious are stress points",
                    realized_air_reference_journeys=realized,annual_both_directions_prior=q,annual_both_directions_scenario=annual,
                    distance_km=distance,reference_via=via,market_version=VERSION,external_scenario_id=scenario)


def product(pid,m,kind,owner,gross,duration,frequency,legs,day,net,intercept=0,capacity=None):
    return dict(product_id=pid,demand_pool_id=m["demand_pool_id"],month=m["month"],customer_segment=m["customer_segment"],kind=kind,owner=owner,
                gross_fare=gross,net_fare=net,fare_unit="RUB/journey",currency="RUB",duration_minutes=duration,frequency=frequency,
                availability=True,capacity=capacity,legs=legs,departure_date=day,min_connection_minutes=45,max_connection_minutes=240,
                revenue_weights=[1/len(legs)]*len(legs) if legs else [],committed_sales=0,contract_only=False,cash_profile=None,
                assumption_id="P05-A08",assumption_ids=["P05-A06","P05-A07","P05-A08","P05-A09","P05-A10","P05-A11","P05-A12"],
                intercept=intercept,source_id="P03_PINNED_DATED_SCENARIO" if legs else "P05_EXPLICIT_SCENARIO",status="scenario",
                fare_basis="scenario_20kg_inclusive_oneway_adult",baggage="20kg_included",sales_channel="UNKNOWN",
                booking_lead_days=None,commercial_status="conditional_scenario_not_booking_inventory",net_yield_status="SCENARIO_NOT_REALIZED",
                coverage="diagnostic selected dates only; competing air represented in outside composite; not full supply acceptance")


def utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def producer_fragment(flights, scenario="base"):
    """Real airport IDs and exact dated flight IDs from P03, not synthetic AAA.

    Cohorts cannot change travel day. Only supplied dates enter the allocation;
    there is no extrapolation of the diagnostic week to the rest of the month.
    Unknown competitor inventory remains an explicitly modelled outside option,
    never an invented air flight. Its final_choice is NOT an observed air segment.
    """
    if len({f['flight_instance_id'] for f in flights})!=len(flights):
        raise ValueError("duplicate physical flight ID")
    for f in flights:
        if f.get('physical_adjacent_leg') is not True:
            raise ValueError("published endpoint offer is not a physical adjacent leg")
        if not '2027-01' <= f['departure_utc'][:7] <= '2028-12':
            raise ValueError("dated supply outside forecast horizon")
    flights=[f for f in flights if f['scheduled_status']!='cancelled']
    d=Demand(); c=coefficients(scenario); paths=[]
    for f in flights:
        paths.append([f])
    for f,g in itertools.product(flights, repeat=2):
        if f["destination_airport"]!=g["origin_airport"] or f["origin_airport"]==g["destination_airport"]:
            continue
        wait=(utc(g["departure_utc"])-utc(f["arrival_utc"])).total_seconds()/60
        if 45<=wait<=240:
            paths.append([f,g])
    groups=defaultdict(list)
    for path in paths:
        a,b=path[0]["origin_airport"],path[-1]["destination_airport"]
        if city(a)==city(b):
            continue
        day=path[0]["departure_utc"][:10]
        groups[(a,b,day)].append(path)
    markets=[];products=[];netrows=[]
    for (a,b,day),options in sorted(groups.items()):
        month=day[:7]
        m=d.market(a,b,month,scenario,segment="travel_date:"+day,cohort_weight=1/calendar.monthrange(int(day[:4]),int(day[5:7]))[1])
        markets.append(m); dist=m["distance_km"]; refgross=gross_fare(dist)
        seg=d.segments.get(tuple(sorted((city(a),city(b)))))
        rail=float(seg["rail_hr"])*60 if seg and seg["rail_hr"] else 96*60
        # Reference composite air time is an explicit geometric analogue.
        reftime=45+dist/650*60+(120 if m["reference_via"] else 0)
        refu=c["price_per_rub"]*refgross+c["time_per_minute"]*reftime
        prefix=m["demand_pool_id"]+":"+day+":"+scenario
        residual=product(prefix+":other_air_residual",m,"outside","OTHER",None,None,None,[],day,None,math.log(.6))
        residual.update(outside_component="UNREPRESENTED_EXISTING_AIR",unconstrained_capacity_not_physical=True,
                        reference_gross_fare=refgross,reference_duration_minutes=reftime,reference_frequency=1,
                        source_id="BASE_OD_PRIOR_AND_P05_SCENARIO",assumption_id="P05-A05")
        products.append(residual)
        ng=product(prefix+":no_travel",m,"outside","OTHER",None,None,None,[],day,None,math.log(.1))
        ng.update(outside_component="NO_TRAVEL",assumption_id="P05-A05")
        products.append(ng)
        groundgross=.5*refgross
        gi=math.log(.3)-c["price_per_rub"]*groundgross-c["time_per_minute"]*rail
        gp=product(prefix+":ground",m,"ground","OTHER",groundgross,rail,1,[],day,None,gi,capacity=m["potential_journeys"])
        gp.update(capacity_status="explicit_scenario_nonbinding_upper_envelope_not_observed_seats",assumption_id="P05-A09")
        products.append(gp)
        counts=Counter(tuple(x["origin_airport"] for x in path)+ (path[-1]["destination_airport"],) for path in options)
        for path in options:
            legs=[f["flight_instance_id"] for f in path]
            route=tuple(x["origin_airport"] for x in path)+(path[-1]["destination_airport"],)
            n=counts[route]
            duration=(utc(path[-1]["arrival_utc"])-utc(path[0]["departure_utc"])).total_seconds()/60
            gross=refgross
            # Cautious tax is a diagnostic rate; actual future legal treatment UNKNOWN.
            vat=0 if scenario=="base" and not (set(route)&MOSCOW) else .10
            distribution=.03 if scenario=="base" else .08
            net=net_fare(gross,vat,distribution)
            intercept=math.log(.6)-refu+c["stop_penalty"]*(len(path)-1)-math.log(n)
            pid="P05:"+hashlib.sha256((scenario+"|"+"|".join(legs)).encode()).hexdigest()[:20]
            pp=product(pid,m,"air","RW",gross,duration,n,legs,day,net,intercept)
            pp.update(reference_gross_fare=refgross,reference_duration_minutes=reftime,route_airports=list(route),
                      path_stop_penalty=c["stop_penalty"]*(len(path)-1),frequency_normalisation=-math.log(n),
                      price_year=2026,forecast_price_policy="constant_2026_RUB_reference; no nominal2027_contract_claim")
            products.append(pp)
            netrows.append(dict(product_id=pid,demand_pool_id=m["demand_pool_id"],month=month,departure_date=day,scenario_id=scenario,
                                gross_fare_rub=gross,vat_rate_scenario=vat,distribution_rate_scenario=distribution,pass_through_rub=0,
                                additional_ancillary_rub=0,net_journey_fare_rub=net,recognition="carried_journey_once",refund_policy="no_refund_multiplier_on_already_carried_journeys",
                                price_year=2026,status="scenario",actual_realized_net_fare=None,lower=None,upper=None,
                                assumption_ids="P05-A06;P05-A10;P05-A11;P05-A12",source_id="P02_COMPARABLE_QUOTES_AND_REGISTERED_ANALOGUES"))
    return dict(version=VERSION,scope="CASE_SJ",scenario_id=scenario,diagnostic_only=True,
                markets=markets,products=products,contracts=[],choice_model=c,
                response_policy=dict(response_policy_id="P05-PASSIVE-v1",rules=[],assumption_id="P05-A13"),
                assumptions=[],net_yield_rows=netrows,
                missing_fields=["actual competing physical inventory and dated2027–2028 offers","own existing RW sales and migration","carrier revenue/cash contracts","true potential-travel mapping and behavioural parameters"],
                admission="ENGINE_CHOICE_AND_ITINERARY_FRAGMENT_ONLY_NOT_FULL_BUSINESS_OR_OPERATIONAL_ACCEPTANCE")


def materialize_response(fragment, policy, reference=None):
    """Bind trigger to pool/month/cohort, then emit unconditional P06 rules.

    P06 early apply_response aggregates frequencies across months and segments.
    This adapter prevents that leak by evaluating the high-level trigger here.
    Caller applies the SAME policy to project and KEEP independently.
    The residual competing-air inclusive value is scenario choice mass, not supply.
    """
    f=copy.deepcopy(fragment);rules=[]
    if policy=="passive":
        return f
    c=f["choice_model"]
    for p in f["products"]:
        if p.get("outside_component")!="UNREPRESENTED_EXISTING_AIR":
            continue
        group=[q for q in f["products"] if (q["demand_pool_id"],q["month"],q["customer_segment"]) == (p["demand_pool_id"],p["month"],p["customer_segment"]) and q["kind"]=="air" and q["owner"]=="RW" and q["availability"]]
        if not group:
            continue
        fare_delta=c["price_per_rub"]*p["reference_gross_fare"]*(-.10)
        rules.append(dict(demand_pool_id=p["demand_pool_id"],rw_frequency_at_least=0,target_product_ids=[p["product_id"]],
                          gross_fare_multiplier=1,frequency_multiplier=1,intercept_delta=fare_delta,assumption_id="P05-A13",
                          trigger_month=p["month"],trigger_customer_segment=p["customer_segment"],interpretation="scenario incumbent fare-10percent; inclusive-value change, not added physical supply"))
    f["response_policy"]=dict(response_policy_id="P05-PRICE_MATCH10-v1",rules=rules,assumption_id="P05-A13")
    return f


def price_for_share(products, target_id, coefficients_, target_share):
    """Unconstrained target share threshold; capacity/incremental cost separate."""
    if not 0<target_share<1 or coefficients_["price_per_rub"]>=0:
        raise ValueError("target share/price coefficient")
    p=next(p for p in products if p["product_id"]==target_id)
    others=[utility(x,coefficients_) for x in products if x["product_id"]!=target_id]
    mx=max(others);lse=mx+math.log(sum(math.exp(u-mx) for u in others))
    u_without_price=utility(p,coefficients_)-coefficients_["price_per_rub"]*p["gross_fare"]
    return (math.log(target_share/(1-target_share))+lse-u_without_price)/coefficients_["price_per_rub"]


if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--flights-json",required=True,help="List of dated RW scenario flight records supplied by P03/P07; no P02 offer conversion; competitor products supplied separately")
    ap.add_argument("--scenario",choices=["base","cautious"],default="base")
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    target=Path(a.output).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError("P05 may write only within its assigned directory")
    write_json(target,producer_fragment(json.loads(Path(a.flights_json).read_text()),a.scenario))
