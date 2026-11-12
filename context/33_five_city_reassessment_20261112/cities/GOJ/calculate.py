#!/usr/bin/env python3
"""Offline diagnostics; does not reselect or mutate the pinned author model."""
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent.parent
MODEL = PACKAGE / "inputs/model"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def save_csv(name, records):
    with (HERE / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def haversine(a, b):
    la, lo = map(math.radians, a)
    lb, lp = map(math.radians, b)
    return 6371.0088 * 2 * math.asin(math.sqrt(
        math.sin((lb-la)/2)**2 + math.cos(la)*math.cos(lb)*math.sin((lp-lo)/2)**2))


def main():
    manifest = json.loads((PACKAGE / "input_manifest.json").read_text())
    checks = []
    for item in manifest:
        actual = hashlib.sha256((PACKAGE / item["path"]).read_bytes()).hexdigest()
        checks.append({"path": item["path"], "sha256": actual,
                       "matches_manifest": actual == item["sha256"]})
    assert all(x["matches_manifest"] for x in checks)
    parameters = {r['parameter']: r for r in rows(MODEL/'network.csv')}
    regions = {r['iata']: r['region'] for r in rows(MODEL/'catchments.csv')}
    south_regions = {r['region'] for r in rows(HERE/'model_south_west_regions.csv')}
    def model_block(destination, km, scenario='base'):
        scenario = scenario.removesuffix('_sub')
        factor = 'route_factor_south' if regions['GOJ'] in south_regions or regions[destination] in south_regions else 'route_factor'
        return (float(parameters['block_fixed_h'][scenario]) + km * float(parameters[factor][scenario])
                / float(parameters['block_speed_kmh'][scenario]))
    model = [r for r in rows(MODEL / "network_routes.csv") if r["from"] == "GOJ"]
    diagnostics = []
    totals = {}
    for r in model:
        cap = 2 * 52 * 100 * int(r["freq_week_each_way"])
        local, transfer = float(r["pax_year_local"]), float(r["pax_year_transfer_seg"])
        segments = float(r["pax_year_segments"])
        diagnostics.append({
            "scenario": r["scenario"], "destination": r["to"],
            "model_destination_name": r["to_city"], "model_km": int(r["km"]),
            "model_frequency_each_direction": int(r["freq_week_each_way"]),
            "seats_two_directions_52_weeks_scenario": cap,
            "model_local_segments": local, "model_transfer_segments": transfer,
            "model_total_segments": segments,
            "transfer_segment_share": round(transfer/segments, 6),
            "local_only_capacity_ratio": round(local/cap, 6),
            "model_variable_result_mln": r["result_mln_year"],
            "status": "PINNED_MODEL_DIAGNOSTIC_NOT_DEMAND_OR_PROFIT"})
        t = totals.setdefault(r["scenario"], {"local": 0, "transfer_segments": 0,
            "segments": 0, "weekly_legs": 0, "block_h_week_formula": 0,
            "sum_rounded_route_variable_results_mln": 0})
        t["local"] += local
        t["transfer_segments"] += transfer
        t["segments"] += segments
        t["weekly_legs"] += 2*int(r["freq_week_each_way"])
        t["block_h_week_formula"] += 2*int(r["freq_week_each_way"])*model_block(r['to'],int(r['km']),r['scenario'])
        t["sum_rounded_route_variable_results_mln"] += float(r["result_mln_year"])
    for t in totals.values():
        t["transfer_segment_share"] = t["transfer_segments"]/t["segments"]
        t["block_h_week_formula"] = round(t["block_h_week_formula"], 3)
        t["sum_rounded_route_variable_results_mln"] = round(t["sum_rounded_route_variable_results_mln"], 1)
    save_csv("model_route_diagnostics.csv", diagnostics)
    # Count actual dated schedule rows, not annual subsidy frequencies or codeshares.
    schedule = rows(HERE / "schedule_observations.csv")
    week = [date(2026, 11, 16)+timedelta(days=i) for i in range(7)]
    days = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6}
    counts, unique = Counter(), set()
    dated = []
    for r in schedule:
        allowed = set(range(7)) if r["days"] == "ежедневно" else {days[d.strip()] for d in r["days"].split(",")}
        for d in week:
            if date.fromisoformat(r["valid_from"]) <= d <= date.fromisoformat(r["valid_to"]) and d.weekday() in allowed:
                key = (r["direction"], d.isoformat(), r["flight"], r["departure_local"])
                assert key not in unique, key
                unique.add(key)
                counts[(r["direction"], r["airport"], r["carrier"])] += 1
                dated.append({"date_local_departure": d.isoformat(), **r})
    save_csv("schedule_week.csv", dated)
    coords = {r["iata"]: (float(r["latitude_deg"]), float(r["longitude_deg"])) for r in rows(MODEL/"catchments.csv")}
    destinations = sorted(set(r["to"] for r in model) | {"SVX", "KUF", "KZN", "KGD", "SGC", "TJM", "MCX", "CSY", "SKX", "IWA", "NBC", "PEE", "NSK"})
    distances = {d: round(haversine(coords["GOJ"], coords[d]), 1) for d in destinations if d in coords}
    # A subset of the local airport invoice, not an all-in turnaround quote.
    fee_scenarios = []
    for mass_t in [45.88, 49.45]:
        for departing_billable_pax in [60, 70, 80]:
            partial = mass_t*(870+663)+departing_billable_pax*(180+780)
            fee_scenarios.append({"mass_t_scenario": mass_t, "billable_pax_scenario": departing_billable_pax,
                "list_partial_rub_ex_vat": round(partial, 2),
                "conditional_40pct_discount_rub_ex_vat": round(partial*.6, 2),
                "conditional_70pct_discount_rub_ex_vat": round(partial*.3, 2)})
    observed_blocks = {"MOW": 80/60, "LED": 2, "AER": 3.75, "MRV": 3+25/60,
                       "CEK": 1+50/60, "UFA": 1+25/60, "KUF": 1.25, "KZN": 1.25,
                       "SVX": 1+55/60, "OVB": 3+25/60, "KGD": 3+10/60}
    block_comparison = []
    for d in ["LED", "AER", "MRV", "CEK", "UFA", "KUF", "KZN", "SVX", "KGD"]:
        model_formula = model_block(d, distances[d])
        block_comparison.append({"destination": d,
            "great_circle_km": distances[d], "model_formula_block_h": round(model_formula, 3),
            "published_example_block_h": round(observed_blocks[d], 3),
            "published_minus_formula_h": round(observed_blocks[d]-model_formula, 3),
            "status": "DIFFERENT_AIRCRAFT_AND_PRODUCT_NOT_AN_SSJ_FLIGHT_PLAN"})
    save_csv("block_comparison.csv", block_comparison)
    # All access/buffer inputs are explicit scenarios; no measured door-to-door claim.
    door_to_door = {d: {"scheduled_block_h": round(b, 4), "access_buffer_exit_egress_h_scenario": 3.5,
                      "air_total_h_scenario": round(b+3.5, 3)} for d,b in observed_blocks.items()}
    result = {
        "status": "OFFLINE_DIAGNOSTICS_ONLY", "as_of": "2026-11-12",
        "input_manifest_verified": checks,
        "pinned_model_sha": "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6",
        "block_formula_provenance": {"formula": "block_fixed_h + km * route_factor / block_speed_kmh; south factor if either region is in pinned list", "region_list_git_path": "data/assumptions/south_west_regions.csv", "region_list_sha256": hashlib.sha256((HERE/'model_south_west_regions.csv').read_bytes()).hexdigest(), "weekly_precision": "published route distances rounded to km; common_economics uses unrounded distance"},
        "model_summaries_from_route_rows": totals,
        "schedule_sample": "2026-11-16/2026-11-22; published product, not operated flights",
        "schedule_counts": [{"direction":k[0],"airport":k[1],"carrier":k[2],"departures":v} for k,v in sorted(counts.items())],
        "great_circle_km_not_road_or_dispatch_distance": distances,
        "partial_GOJ_airport_invoice_scenarios": fee_scenarios,
        "block_comparison": block_comparison,
        "invoice_exclusions": ["full ground handling", "fuel", "MRO", "deicing", "crew", "reserve", "VAT treatment", "discount agreement", "exact passenger billing rules"],
        "two_weekly_rotations_100_seats_52_weeks": {"seats_two_directions": 20800, "segments_at_60pct_scenario": 12480,
            "segments_at_70pct_scenario": 14560, "segments_at_80pct_scenario": 16640, "note": "capacity arithmetic, not demand or breakeven"},
        "door_to_door_scenarios": door_to_door,
        "MOW_comparison_scenario": {"air_hours": round(80/60+3.5,3), "rail_line_hours_from_FPC": 3.8,
            "rail_access_boarding_egress_hours_scenario": 1.25, "rail_total_hours_scenario": 5.05,
            "note": "no waiting-for-departure or fares; changing access can reverse preference"},
        "family_budget_scenario": {"people": 4, "one_way_fare_assumption_rub": 8000, "return_tickets_rub": 64000,
            "regional_monthly_gross_wage_2025_rub": 80778, "ratio_to_one_gross_wage": round(64000/80778,4),
            "note": "fare is an assumption; average gross wage is not disposable household income"},
        "not_run": ["author model reselection", "OD estimation", "profit calculation", "booking transaction", "aircraft dispatch", "cash funding verification"]}
    (HERE/"calculations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"manifest_files":len(checks),"model_routes":len(model),"union":sorted(set(r['to'] for r in model)),
                      "schedule_rows":len(schedule),"dated_rows":len(dated),"model_totals":totals,
                      "fees_49_45t_70pax":fee_scenarios[4]},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
