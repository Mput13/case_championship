#!/usr/bin/env python3
"""Offline extraction and arithmetic only. Does not run or change the author model."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1] / "inputs" / "model"


def read(name):
    with (MODEL / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    routes = read("network_routes.csv")
    selected = [r for r in routes if r["from"] == "CEK" or r["to"] == "CEK"]
    with (HERE / "model_routes_extract.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(routes[0]))
        writer.writeheader()
        writer.writerows(selected)
    base = [r for r in selected if r["scenario"] == "base" and r["variant"] == "Хаб CEK"]
    sums = {k: sum(float(r[k]) for r in base) for k in (
        "freq_week_each_way", "pax_year_local", "pax_year_transfer_seg", "pax_year_segments",
        "revenue_mln_year", "cost_mln_year", "result_mln_year")}
    by_leg = {r["to"]: {
        "transfer_segment_share_pct": round(100 * float(r["pax_year_transfer_seg"]) / float(r["pax_year_segments"]), 3),
        "scenario_seat_legs_100_seats_52_weeks": 2 * int(r["freq_week_each_way"]) * 100 * 52,
    } for r in base}
    summary = [r for r in read("network_summary.csv") if r["hub"] in ("CEK", "OMS")]
    calc = {
        "status": "offline_arithmetic_not_model_rerun_not_market_validation",
        "author_sha": "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6",
        "prepared_base_sha": "250f8037969b72ca19d573cc7372b17d6fc0355e",
        "input_sha256": {n: hashlib.sha256((MODEL/n).read_bytes()).hexdigest() for n in (
            "network_routes.csv", "network_summary.csv", "catchments.csv", "longlist.csv", "known_flows.csv")},
        "unique_CEK_model_destinations": sorted({r["to"] if r["from"] == "CEK" else r["from"] for r in selected}),
        "CEK_model_rows": len(selected),
        "CEK_base_route_sums": sums,
        "CEK_base_by_leg": by_leg,
        "CEK_base_transfer_OD_from_segments": sums["pax_year_transfer_seg"] / 2,
        "CEK_base_transfer_segment_share_pct": round(100 * sums["pax_year_transfer_seg"] / sums["pax_year_segments"], 3),
        "CEK_base_round_trips_per_week": sums["freq_week_each_way"],
        "CEK_base_one_way_flights_per_week": sums["freq_week_each_way"] * 2,
        "CEK_base_scenario_seat_legs": sums["freq_week_each_way"] * 2 * 100 * 52,
        "CEK_base_aggregate_LF_pct": round(100 * sums["pax_year_segments"] / (sums["freq_week_each_way"] * 2 * 100 * 52), 3),
        "summary_rows_unchanged": summary,
        "two_weekly_round_trips_100_seats_52_weeks": {
            "seat_legs": 2 * 2 * 100 * 52,
            "pax_segments_at_70pct_scenario": 2 * 2 * 100 * 52 * .7,
            "pax_segments_at_85pct_scenario": 2 * 2 * 100 * 52 * .85,
            "assumption": "100 seats, 52 weeks; capacity scenarios, not demand or approved frequencies"},
        "model_MOW_region_scope_upper_bound": {
            "regional_report_pax_approx": 1100000,
            "MQF_all_traffic_operator_approx": 279000,
            "CEK_MOW_loose_lower_bound_approx": 1100000 - 279000,
            "warning": "Only a loose bound if definitions and periods match; rounded regional statement, all MQF traffic subtracted, not a measured CEK OD."},
        "population_definition_difference": {
            "core_model_catchment": 1337331, "expanded_reconstruction_2025": 1689223,
            "difference_people": 1689223 - 1337331,
            "difference_pct_of_core": round(100 * (1689223/1337331-1), 3),
            "warning": "different geography/method; not population growth or new OD"},
        "SUSU_one_roundtrip_per_foreign_student_scenario": {
            "student_count_conflict": [2528, 2540],
            "direct_segment_events_if_one_return_trip_each": [5056, 5080],
            "warning": "Illustrative scenario, not forecast or market bound; includes network-program students whose physical location is unknown."},
        "groundfeed_example_scenario": {
            "bus_minutes_published_example": 168,
            "preflight_buffer_assumption_minutes": 120,
            "minimum_before_flight_from_bus_departure_minutes": 288,
            "warning": "single secondary timetable example; excludes urban access, bus wait and road reliability allowance; not an airport connection guarantee"},
    }
    assert len(base) == 8
    assert len(calc["unique_CEK_model_destinations"]) == 17
    assert abs(sums["pax_year_segments"] - (sums["pax_year_local"]+sums["pax_year_transfer_seg"])) <= 2
    assert abs(sums["result_mln_year"] - (sums["revenue_mln_year"]-sums["cost_mln_year"])) < 1
    (HERE / "calculations.json").write_text(json.dumps(calc, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in calc.items() if k.startswith("CEK_base") or k=="CEK_model_rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
