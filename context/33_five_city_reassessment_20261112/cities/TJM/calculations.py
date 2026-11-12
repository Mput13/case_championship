#!/usr/bin/env python3
"""Offline arithmetic and registry validation. Does not re-estimate the author's model.
Run from any cwd: python3 <path>/calculations.py
"""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent


def read(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


routes = read(PACK / "inputs/model/network_routes.csv")
base = [r for r in routes if r["scenario"] == "base" and r["from"] == "TJM"]
summaries = read(PACK / "inputs/model/network_summary.csv")
result = {
    "as_of": "2026-11-12",
    "input_model_sha": "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6",
    "kind": "arithmetic on pinned scenarios, not observed demand or new optimization",
    "inputs_sha256": {
        n: hashlib.sha256((PACK / "inputs/model" / n).read_bytes()).hexdigest()
        for n in ["network_routes.csv", "network_summary.csv", "longlist.csv"]
    },
    "base_tjm_routes": [],
}
for r in base:
    local, transfer, segments = (float(r[k]) for k in [
        "pax_year_local", "pax_year_transfer_seg", "pax_year_segments"])
    frequency = float(r["freq_week_each_way"])
    result["base_tjm_routes"].append({
        "to": r["to"], "km": int(r["km"]),
        "frequency_each_way_week": frequency, "local_segments": local,
        "transfer_segments": transfer, "total_segments": segments,
        "transfer_share": transfer / segments,
        "local_only_lf_at_author_frequency": local / (2 * 52 * 100 * frequency),
        "warning": "local demand remains the author's estimate; this is not a standalone forecast",
    })
local = sum(float(r["pax_year_local"]) for r in base)
transfer = sum(float(r["pax_year_transfer_seg"]) for r in base)
segments = sum(float(r["pax_year_segments"]) for r in base)
result["base_tjm_aggregation"] = {
    "local_segments": local, "transfer_segments": transfer,
    "total_segments_route_sum": segments,
    "transfer_share_segments": transfer / segments,
    "flights_week_both_ways": 2 * sum(float(r["freq_week_each_way"]) for r in base),
    "transfer_legs_divided_by_2": transfer / 2,
    "route_result_sum_mln_rounded": sum(float(r["result_mln_year"]) for r in base),
}
result["pinned_tjm_oms_comparison"] = []
for r in summaries:
    if r["hub"] in ["TJM", "OMS"]:
        margin = float(r["result_mln_year"])
        result["pinned_tjm_oms_comparison"].append({
            "scenario": r["scenario"], "iata": r["hub"],
            "aircraft": int(r["aircraft"]), "routes": int(r["routes"]),
            "segments": int(r["segments_year"]), "od_trips": int(r["od_trips_year"]),
            "transfer_od": int(r["transfer_od_year"]),
            "result_mln": margin,
            "result_per_aircraft_mln_diagnostic_only": margin / int(r["aircraft"]),
            "transfer_od_share": int(r["transfer_od_year"]) / int(r["od_trips_year"]),
            "result_over_revenue": margin / float(r["revenue_mln_year"]),
        })
result["capacity_scenarios_100_seats"] = [
    {"weeks": weeks, "frequency_each_way_week": f, "assumed_lf": lf,
     "segments_both_ways": 2 * weeks * f * 100 * lf,
     "kind": "illustrative capacity requirement, not demand or a launch LF gate"}
    for weeks, f, lf in [(52, 1, .8), (52, 2, .8), (52, 3, .8), (20, 2, .8)]
]
# A particular rail service is compared with the official local-airport bus time.
# Station access, terminal transfer and airline reporting buffer are scenario inputs.
rail_minutes = 299
local_bus_minutes = 40
assumed_station_access = 30
assumed_svx_terminal_transfer = 60
assumed_report_buffer = 120
via_svx = rail_minutes + assumed_station_access + assumed_svx_terminal_transfer + assumed_report_buffer
via_tjm = local_bus_minutes + assumed_report_buffer
delta = via_svx - via_tjm
result["ground_feed_example"] = {
    "observed_schedule_service": "809Е 17:10–22:09, November 2026 listing, not every train",
    "rail_minutes": rail_minutes, "tjm_official_bus_minutes": local_bus_minutes,
    "scenario_station_access_minutes": assumed_station_access,
    "scenario_svx_station_to_terminal_minutes": assumed_svx_terminal_transfer,
    "scenario_both_airports_report_buffer_minutes": assumed_report_buffer,
    "scenario_minutes_until_flight_svx": via_svx,
    "scenario_minutes_until_flight_tjm": via_tjm,
    "incremental_minutes": delta,
    "time_value_rub_scenarios": {str(v): delta / 60 * v for v in [500, 1500]},
    "warning": "No flight, wait for departure, fare or disruption risk difference included. Not a measured door-to-door trip.",
}
result["university_cohort_scenario"] = {
    "intake_2025": 4996, "published_nonlocal_share": .435,
    "intake_times_nonlocal_share_approx": 4996 * .435,
    "one_cohort_two_roundtrips_all_air_counterfactual_segments": 4996 * .435 * 4,
    "warning": "Share denominator not fully specified; not airport demand. Excludes other cohorts and universities; all-air is a counterfactual, not a forecast or market upper bound.",
}
result["tourism_summer_autumn_share_ratio"] = 29 / 21
manifest = json.loads((PACK / "input_manifest.json").read_text())
for entry in manifest:
    raw = (PACK / entry["path"]).read_bytes()
    assert len(raw) == entry["bytes"], entry["path"]
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]
result["pinned_manifest_check"] = {"entries": len(manifest), "mismatches": 0}
(HERE / "calculations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

if all((HERE / n).exists() for n in ["sources.csv", "claims.csv", "routes.csv", "features.csv", "decision.json"]):
    sources = read(HERE / "sources.csv")
    claims = read(HERE / "claims.csv")
    products = read(HERE / "routes.csv")
    features = read(HERE / "features.csv")
    source_ids = {x["source_id"] for x in sources}
    claim_ids = {x["claim_id"] for x in claims}
    expected_schemas = {
        "sources.csv": "source_id,title,organization,url,published_at,accessed_at,period,geography,metric,unit,source_type,access_status,limitations",
        "claims.csv": "claim_id,claim,evidence_status,source_ids,period,geography,value,unit,mechanism,decision_impact,uncertainty",
        "routes.csv": "origin,destination,product,season,competitors,frequency_evidence,demand_evidence,ground_alternative,rw_overlap,operating_constraints,assessment,source_ids,missing_fields",
        "features.csv": "feature_id,feature,evidence_ids,mechanism,affected_markets,magnitude_or_bound,counterevidence,decision_effect,unknowns",
    }
    for filename, schema in expected_schemas.items():
        assert list(read(HERE / filename)[0]) == schema.split(","), filename
    assert all(s.startswith("TJM-") for s in source_ids | claim_ids)
    assert all(r["value"] == "" for r in claims if r["evidence_status"] == "UNKNOWN")
    assert len(source_ids) == len(sources)
    assert len(claim_ids) == len(claims)
    for row in claims + products:
        for key in row["source_ids"].split(";"):
            assert key in source_ids, (key, row)
    for row in features:
        for key in row["evidence_ids"].split(";"):
            assert key in source_ids | claim_ids, (key, row)
    assert len({x["feature_id"] for x in features}) == len(features)
    for file in ["sources.csv", "claims.csv", "routes.csv", "features.csv"]:
        for row in read(HERE / file):
            assert None not in row, (file, row)
            assert all(v is not None for v in row.values()), (file, row)
    decisions = json.loads((HERE / "decision.json").read_text())
    assert {x["option"] for x in decisions["options"]} == {
        "localdirect", "existingbase", "newbase", "hub", "groundfeed", "noproject"}
    assert {"MOW", "LED", "MRV", "BTK", "KEJ", "TOF", "VOG", "GOJ", "NOZ", "BAX", "REN"}.issubset({r["destination"] for r in products})
    assert abs(local + transfer - segments) <= 1
    assert result["base_tjm_aggregation"]["flights_week_both_ways"] == 94
    selected = [r for r in routes if r["from"] == "TJM" or r["to"] == "TJM"
                or ("TJM" in r["variant"] and not r["variant"].startswith("Хаб"))]
    assert selected == read(HERE / "selected_model_routes.csv")
    check = {"status": "PASS", "offline_only": True,
             "sources": len(sources), "claims": len(claims), "routes": len(products),
             "features": len(features), "manifest_entries": len(manifest), "selected_model_rows": len(selected), "checks": [
                 "CSV schemas and row widths", "unique IDs", "source and feature references",
                 "six option coverage", "union of author's TJM destinations including triangles",
                 "base route arithmetic", "all pinned manifest sizes and hashes", "selected model row equality", "unknown value remains empty"],
             "not_checked": ["observed OD", "realised yields", "full incremental cost", "live booking checkout", "dispatch performance", "new network optimization"]}
    (HERE / "validation.json").write_text(json.dumps(check, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(check, ensure_ascii=False))
else:
    print(json.dumps(result, ensure_ascii=False, indent=2))
