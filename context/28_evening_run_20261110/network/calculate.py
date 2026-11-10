#!/usr/bin/env python3
"""Fixed, diagnostic network experiments; no author model mutation or annualisation.

Run from any directory with Python 3.11, numpy/scipy. Inputs are pinned Git blobs.
Money is RUB at the author's scenario price basis, not a booking or a forecast.
"""
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
OWNER = HERE / "inputs/owner4a976"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def write(name, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open("w") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


PARAMS = read(OWNER / "data/assumptions/network.csv")
NODES = {r["iata"]: r for r in read(OWNER / "data/processed/catchments.csv")}
SOUTH = {r["region"] for r in read(OWNER / "data/assumptions/south_west_regions.csv")}
DEMAND = {frozenset((r["a"], r["b"])): r for r in read(OWNER / "data/processed/od_pairs.csv")}
for r in read(OWNER / "data/processed/demand_estimates.csv"):
    if r["od_base"]:
        DEMAND[frozenset((r["a"], r["b"]))] = r
RW = {frozenset((r["a"], r["b"])): r for r in read(OWNER / "data/manual/rw_routes_now.csv")}
CARDS = read(OWNER / "data/external/colleagues/route_product_cards.csv")
INPUT_ROWS = {}


def assumptions(s):
    return {r["parameter"]: float(r[s]) for r in PARAMS}


def distance(a, b):
    A, B = NODES[a], NODES[b]
    la, lo, lb, lob = [math.radians(float(v)) for v in
                      (A["latitude_deg"], A["longitude_deg"], B["latitude_deg"], B["longitude_deg"])]
    return 2 * 6371 * math.asin(math.sqrt(math.sin((lb-la)/2)**2 + math.cos(la)*math.cos(lb)*math.sin((lob-lo)/2)**2))


def pair(a, b, s, f):
    A = assumptions(s)
    D = DEMAND[frozenset((a, b))]
    direct = D.get("direct_now", "") == "True" or D.get("route") == "прямой рейс"
    annual = float(D["od_" + s])
    seg = float(D.get("segments_base") or D.get("segments_on_link") or D["od_base"])
    if s == "cautious":
        seg *= annual / float(D["od_base"])
    dem = annual / 104  # one direction in an explicitly diagnostic seven-day experiment
    seg_week = seg / 104
    share = min(A["capture_competitive"], f/(f + seg_week/(A["seats"]*A["competitor_lf"]))) if direct else A["capture_open"]*(1-math.exp(-f/A["capture_freq_scale"]))
    km = distance(a, b)
    fare = A["fare_fixed_rub"] + A["fare_per_km_rub"] * km
    row = dict(scenario=s, origin=a, destination=b, annual_od_model_both_directions=annual,
               annual_segments_competition_proxy=seg, diagnostic_week_od_one_direction=dem,
               direct_in_author_input=direct, frequency_each_direction=f,
               capture_scenario=share, captured_local_one_direction=min(dem*share, f*A["seats"]*A["lf_max"]),
               net_fare_rub=fare, km=km, od_method=D.get("od_method") or D.get("route"),
               winter_factor=D.get("winter_factor", ""), summer_factor=D.get("summer_factor", ""),
               own_rw_frequency_proxy=RW.get(frozenset((a,b)), {}).get("freq_week_each_way", ""),
               units="annual journeys both directions; seven-day diagnostic local journeys one direction; RUB/journey")
    INPUT_ROWS[(s, a, b, f)] = row
    return row


def flight(a, b, s, block_override=None):
    A = assumptions(s)
    km = distance(a, b)
    south = bool({NODES[a]["region"], NODES[b]["region"]} & SOUTH)
    bh = block_override if block_override is not None else A["block_fixed_h"] + km * A["route_factor_south" if south else "route_factor"] / A["block_speed_kmh"]
    fixed = ((A["fuel_t_per_hour"]*bh + A["fuel_t_per_cycle"])*A["fuel_rub_per_t"]
             + (A["mro_rub_per_hour"]+A["crew_rub_per_hour"]+A["navigation_rub_per_hour"])*bh
             + A["ground_rub_per_flight"]+A["deicing_rub_per_flight"])
    return bh, fixed


def fixed_program(id_, s, hub, spokes, f=2):
    A = assumptions(s)
    costs = hours = rev = pax = old_proxy = 0.0
    rows = []
    for x in spokes:
        D = pair(hub, x, s, f)
        q = D["captured_local_one_direction"]
        h, c = flight(hub, x, s)
        costs += 2*f*c + 2*q*A["pax_cost_rub"]
        hours += 2*f*h
        rev += 2*q*D["net_fare_rub"]
        pax += 2*q
        old_proxy += 2*min(q, float(D["own_rw_frequency_proxy"] or 0)*100*A["rw_existing_lf"])
        rows.append(dict(hypothesis="C03" if hub=="KUF" else "C04", network=id_, scenario=s,
                         origin=hub, destination=x, frequency_each_direction=f,
                         flights_week=2*f, block_hours_week=2*f*h, local_journeys_week=2*q,
                         segments_week=2*q, ticket_revenue_rub_week=2*q*D["net_fare_rub"],
                         variable_cost_rub_week=2*f*c+2*q*A["pax_cost_rub"],
                         local_only_contribution_rub_week=2*q*D["net_fare_rub"]-2*f*c-2*q*A["pax_cost_rub"],
                         seats_per_flight=100, planning_lf=A["lf_max"], load_factor=q/(f*100),
                         diagnostic="fixed candidate; no transfer revenue; not published timetable"))
    return dict(hypothesis="C03" if hub=="KUF" else "C04", network=id_, scenario=s,
                routes=len(spokes), frequency_each_direction=f, block_hours_week=hours,
                aircraft_hours_lower_bound=math.ceil(hours/70), local_journeys_week=pax,
                segments_week=pax, ticket_revenue_rub_week=rev, variable_cost_rub_week=costs,
                contribution_rub_week=rev-costs, Kmax_rub_week=rev-costs,
                support_break_even_rub_per_local_journey=max(0,costs-rev)/pax,
                fare_multiplier_at_fixed_volumes=costs/rev,
                own_migrated_proxy_week=old_proxy,
                full_result_formula="contribution + signed_D_other - K_unincluded; Kmax at D_other=0",
                cash="UNKNOWN: deposits/startup/payment timing; no subsidies booked"), rows


def three_pools(s, cap, d1, d2, dt, f1, f2, ft):
    """One direction, two physical legs; through fare exactly once. Exact LP."""
    p = assumptions(s)["pax_cost_rub"]
    unit = [f1-p, f2-p, ft-2*p]
    sol = linprog([-x for x in unit], A_ub=[[1,0,1],[0,1,1]], b_ub=[cap,cap],
                  bounds=[(0,d1),(0,d2),(0,dt)], method="highs")
    assert sol.success, sol.message
    a,b,t = sol.x
    assert a+t <= cap+1e-7 and b+t <= cap+1e-7
    return a,b,t, a*unit[0]+b*unit[1]+t*unit[2]


def synchronization(s):
    A=assumptions(s); f=2; cap=f*100*A["lf_max"]
    a=pair("NJC","UFA",s,f); b=pair("UFA","MRV",s,f); t=pair("NJC","MRV",s,f)
    dl1=a["captured_local_one_direction"];dl2=b["captured_local_one_direction"]
    fare_t=t["net_fare_rub"]*A["transfer_fare_factor"]
    # Direct NJC-MRV already exists in author data. Do not label this an unserved market.
    dt=t["diagnostic_week_od_one_direction"] * min(A["capture_transfer"]*(1-math.exp(-f/3)), t["capture_scenario"])
    fixed=sum(2*f*flight(x,y,s)[1] for x,y in [("NJC","UFA"),("UFA","MRV")])
    base_m=dl1*(a["net_fare_rub"]-A["pax_cost_rub"])+dl2*(b["net_fare_rub"]-A["pax_cost_rub"])
    rows=[]
    for loss in [0,.05,.15]:
        x,y,z,m=three_pools(s,cap,dl1,dl2*(1-loss),dt,a["net_fare_rub"],b["net_fare_rub"],fare_t)
        rows.append(dict(hypothesis="C01",scenario=s,network="UFA_same_legs_sync", local_loss_fraction_south=loss,
                         baseline="same four diagnostic unsynchronised flights; two operating days",
                         local_before_week=2*(dl1+dl2), local_after_week=2*(x+y),
                         new_through_journeys_week=2*z, total_journeys_week=2*(x+y+z),
                         segments_week=2*(x+y+2*z), capacity_per_leg_one_direction=cap,
                         local_lost_timing_week=2*dl2*loss,
                         local_displaced_capacity_week=2*(dl1+dl2*(1-loss)-x-y),
                         through_net_fare_rub=fare_t, contribution_unsync_rub_week=2*base_m-fixed,
                         contribution_sync_rub_week=2*m-fixed, delta_contribution_rub_week=2*(m-base_m),
                         Kmax_retiming_rub_week=2*(m-base_m),
                         Kmax_full_base_rub_week=2*m-fixed,
                         full_result_formula="delta_contribution - K_retiming + signed_D_other; new full base separately: sync_contribution - K_full_base + D_old",
                         cash="UNKNOWN; same included flight costs cancel only for timing comparison"))
    return rows


def extension(s):
    A=assumptions(s);f=2;cap=f*100*A["lf_max"]
    d1=pair("SVX","OMS",s,f);d2=pair("OMS","KJA",s,f);dt=pair("SVX","KJA",s,f)
    q1=d1["captured_local_one_direction"];q2=d2["captured_local_one_direction"]
    qt=dt["diagnostic_week_od_one_direction"]*min(A["capture_transfer"]*(1-math.exp(-f/3)),dt["capture_scenario"])
    ft=dt["net_fare_rub"]*A["transfer_fare_factor"]
    x,y,z,m=three_pools(s,cap,q1,q2,qt,d1["net_fare_rub"],d2["net_fare_rub"],ft)
    # Published directional timing reference: 100/105 existing, 135/135 new minutes.
    oldfixed=f*(flight("SVX","OMS",s,100/60)[1]+flight("OMS","SVX",s,105/60)[1])
    addedfixed=2*f*flight("OMS","KJA",s,135/60)[1]
    oldm=q1*(d1["net_fare_rub"]-A["pax_cost_rub"])
    delta=2*(m-oldm)-addedfixed
    rows=[]
    for turn in [30,45,60]:
        # Reference return OMS 00:50. Candidate arrives OMS 00:00, goes to KJA and back.
        elapsed=475+3*turn
        delay=(135+135+3*turn)-50
        rows.append(dict(hypothesis="C07",scenario=s,network="SVX_OMS_KJA_OMS_SVX",turn_minutes=turn,
                         reference_block_minutes=205,candidate_block_minutes=475,
                         candidate_elapsed_minutes=elapsed, extra_block_hours_week=2*f*135/60,
                         return_delay_vs_published_minutes=delay,
                         next_SVX_departure_earliest_local=(datetime(2026,12,9,1,35)+timedelta(minutes=delay+turn)).isoformat(),
                         baseline="published WZ5071 8/11 Dec 21:20 to OMS00:00; WZ5072 9/12 Dec00:50 to SVX01:35",
                         old_local_journeys_week=2*q1,new_local_on_old_pair_week=2*x,
                         new_local_OMS_KJA_week=2*y,new_through_SVX_KJA_week=2*z,
                         new_segment_delta_week=2*(x+y+2*z-q1),
                         extra_fixed_flight_cost_rub_week=addedfixed,
                         delta_ticket_revenue_rub_week=2*((x-q1)*d1["net_fare_rub"]+y*d2["net_fare_rub"]+z*ft),
                         delta_contribution_rub_week=delta,
                         Kmax_total_rub_week=delta,
                         break_even_total_local_OMS_KJA_each_direction_week=(addedfixed/2-z*(ft-2*A["pax_cost_rub"])-(x-q1)*(d1["net_fare_rub"]-A["pax_cost_rub"] ))/(d2["net_fare_rub"]-A["pax_cost_rub"]),
                         full_result_formula="delta_contribution - K_extension - L_next_assignment + signed_D_other; unknown terms retained",
                         cash="UNKNOWN; no hypothetical support recognised"))
    return rows


def main():
    for item in json.loads((HERE/"input_manifest.json").read_text()):
        assert hashlib.sha256((HERE/item["local"]).read_bytes()).hexdigest()==item["sha256"]
    fixed=[]; routes=[]; sync=[]; chain=[]
    for s in ["base","cautious"]:
        for id_,hub,spokes in [
            ("KUF4", "KUF", ["ARH","OMS","NJC","MRV"]),
            ("OMS1", "OMS", ["KJA"]),
            ("OMS4", "OMS", ["KJA","KUF","GOJ","NOZ"]),
            ("OMS8", "OMS", ["KJA","KUF","GOJ","NOZ","GSV","UFA","TOF","VOG"]),
        ]:
            summary, details=fixed_program(id_,s,hub,spokes)
            fixed.append(summary);routes.extend(details)
        sync.extend(synchronization(s));chain.extend(extension(s))
    write("fixed_programs.csv",fixed);write("fixed_routes.csv",routes)
    write("C01_synchronization.csv",sync);write("C07_extension.csv",chain)
    write("demand_fare_inputs.csv",list(INPUT_ROWS.values()))
    print(json.dumps(dict(fixed=fixed,C01=sync,C07=chain),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
