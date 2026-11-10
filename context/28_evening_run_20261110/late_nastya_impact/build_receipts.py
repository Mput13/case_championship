"""Build bounded impact receipts from pinned snapshots; no HTTP, owner model or UI calls."""
import csv
import gzip
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EP = HERE / "inputs/evidence/context/28_evening_run_20261110/evidence"
LATE = HERE / "inputs/late"

def read_csv(path):
    return list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))

def write_csv(name, rows):
    with (HERE / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def main():
    manifest = json.loads((HERE / "source_manifest.json").read_text())
    checks = []
    for row in manifest["files"]:
        if row["pin"] == "methods_gzip_derivative":
            data = gzip.decompress((HERE / row["source_path"]).read_bytes())
        else:
            data = (HERE / row["local_path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"], row
        assert len(data) == row["bytes"]
        if "commit" in row:
            blob = subprocess.check_output(["git", "rev-parse", row["commit"] + ":" + row["source_path"]], cwd=ROOT).decode().strip()
            assert blob == row["git_blob"]
        checks.append({"local_path": row["local_path"], "sha256_verified": True, "bytes": len(data)})
    assert not manifest["missing"]
    # Old published economic tables are byte-identical to the frozen baseline.
    same = {}
    for path in ["src/network_model.py", "data/assumptions/network.csv", "data/processed/network_summary.csv"]:
        same[path] = (HERE / "inputs/previous" / path).read_bytes() == (HERE / "inputs/baseline" / path).read_bytes()
    assert all(same.values())
    diff = subprocess.check_output(["git", "diff", manifest["pins"]["previous"], manifest["pins"]["late"], "--",
        "src/network_model.py", "src/rules.py", "data/assumptions", "data/manual/roadmap.csv", "data/manual/competitor_bases.csv",
        "docs/24_hypotheses_comparison.md", "docs/26_steps_2_4_5.md", "docs/27_handoff_route_competitors.md", "docs/HANDOFF.md"], cwd=ROOT)
    (HERE / "author_diff.patch").write_bytes(diff)
    source_caps = read_csv(EP / "subsidy_cap_84_103_seats.csv")
    author_caps = read_csv(LATE / "data/assumptions/subsidy_cap_84_103.csv")
    assert [(r["min_km"], r["cap_rub_per_oneway_flight"]) for r in source_caps] == [(r["min_km"], r["cap_rub_per_oneway_flight"]) for r in author_caps]
    raw = read_csv(LATE / "data/raw/favt_subsidy_2026.csv")
    clean_num = lambda x: Decimal(x.replace(" ", "").replace("\xa0", "").replace(",", "."))
    planned_oneway_flights = sum(clean_num(r["round_trips_2026"]) * 2 for r in raw)
    probe = json.loads((HERE / "author_probe.json").read_text())
    selected = next(r for r in probe["caps"] if r["scenario"] == "base_sub" and r["cap"] == 6)
    fares = read_csv(EP / "subsidy_special_fare_grid.csv")
    counterexamples = []
    for leg in selected["legs"]:
        if leg["subsidy_rule"][0] == 0:
            continue
        grid = max((r for r in fares if float(r["min_km"]) <= leg["km"]), key=lambda r: float(r["min_km"]))
        ceiling = float(grid["base_special_fare_rub_including_vat"])
        gap = leg["fare_rub"] - ceiling
        counterexamples.append({"route": "OMS-" + leg["to"], "author_distance_km": leg["km"], "frequency_each_way_week": leg["frequency_each_way"],
            "author_formula_fare_rub": leg["fare_rub"], "base_special_fare_including_vat_rub": ceiling,
            "fare_excess_rub": gap, "fare_excess_pct": gap / ceiling * 100,
            "assumed_per_flight_rate_rub": 185228, "table_cap_rub": next(float(r["cap_rub_per_oneway_flight"]) for r in reversed(author_caps) if float(r["min_km"]) <= leg["km"]),
            "annual_smoothed_grant_author_rub": 2 * leg["frequency_each_way"] * 52 * leg["subsidy_rule"][0],
            "local_trips_year_author": leg["local_annual"],
            "fixed_volume_local_fare_reduction_all_year_rub": leg["local_annual"] * gap,
            "fixed_volume_local_fare_reduction_7_months_rub": leg["local_annual"] * gap * 7 / 12,
            "actual_RW_award": "UNKNOWN", "authorized_regional_fare_increase": "UNKNOWN_NOT_ASSUMED",
            "classification": "BASE_GRID_COUNTEREXAMPLE_IN_AUTHOR_FARE_UNITS; fixed network/volume; no new award; retail-to-net UNKNOWN"})
    write_csv("subsidy_counterexamples.csv", counterexamples)
    assert abs(sum(r["annual_smoothed_grant_author_rub"] for r in counterexamples) - selected["annual_subsidy_rub"]) < 1e-6
    money_receipt = {"old_raw_rows": len(raw), "old_raw_sha256": hashlib.sha256((LATE / "data/raw/favt_subsidy_2026.csv").read_bytes()).hexdigest(),
        "planned_oneway_flights_in_old_list": str(planned_oneway_flights),
        "7980000000_divided_by_planned_flights": float(Decimal(7980000000) / planned_oneway_flights),
        "author_input_rate": 185228, "caps_13_values_equal_evidence": True,
        "selected_author_annual_grant_rub": selected["annual_subsidy_rub"], "selected_author_result_rub": selected["annual_result_rub"],
        "local_only_7month_fare_gap_rub": sum(r["fixed_volume_local_fare_reduction_7_months_rub"] for r in counterexamples),
        "diagnostic_result_if_only_local_7month_fare_gap_subtracted": selected["annual_result_rub"] - sum(r["fixed_volume_local_fare_reduction_7_months_rub"] for r in counterexamples),
        "classification": "diagnostic mismatch, NOT corrected strategy PnL or legal award; transfer fare, demand response, dates and retail-to-net not solved"}
    (HERE / "subsidy_formula_receipt.json").write_text(json.dumps(money_receipt, ensure_ascii=False, indent=2) + "\n")
    old_summary = read_csv(HERE / "inputs/previous/data/processed/network_summary.csv")
    late_summary = read_csv(LATE / "data/processed/network_summary.csv")
    old_key = {(r["scenario"], r["hub"]): r for r in old_summary}
    deltas = []
    for r in late_summary:
        old = old_key.get((r["scenario"], r["hub"]))
        deltas.append({"scenario": r["scenario"], "hub": r["hub"], "variant": r["variant"], "newly_published_variant": old is None,
            "old_result_mln_year": old["result_mln_year"] if old else "NOT_IN_PREVIOUS",
            "late_result_mln_year": r["result_mln_year"], "old_routes": old["routes"] if old else "NOT_IN_PREVIOUS",
            "late_routes": r["routes"], "old_aircraft": old["aircraft"] if old else "NOT_IN_PREVIOUS", "late_aircraft": r["aircraft"],
            "late_subsidy_mln_year": r["subsidy_mln_year"], "verification": "PUBLISHED_OUTPUT_READ; only OMS base/base_sub replayed"})
    write_csv("published_summary_delta.csv", deltas)
    # Existing affected-pair universe plus the late OMS network only. Do not expand to all20-hub todo.
    pairs = read_csv(EP / "pair_registry.csv")
    registry = {r["route"]: r for r in pairs}
    routes = read_csv(LATE / "data/processed/network_routes.csv")
    late_oms = {"-".join(sorted((r["from"], r["to"]))) for r in routes if r["variant"] == "Хаб OMS" and r["scenario"] in ("base", "base_sub")}
    weekly = read_csv(EP / "weekly_service_context.csv")
    instances = read_csv(EP / "dated_service_instances.csv")
    records = read_csv(EP / "dated_service_records.csv")
    unique = {(r["origin"], r["destination"], r["date"], r["flight"]) for r in records}
    assert len(unique) == len(instances) == 215
    assert len(records) == 359
    services = []
    for r in weekly:
        matching_records = [x for x in records if x["origin"] == r["origin"] and x["destination"] == r["destination"]
                            and x["flight"] in r["flights"].split(";") and x["date"] in r["dates"].split(";")]
        urls = sorted({x["source_url"] for x in matching_records})
        assert matching_records
        services.append(dict(r, source_urls=";".join(urls), evidence_commit=manifest["pins"]["evidence"],
                             source_ids=";".join(sorted({x["source_id"] for x in matching_records})),
                             observation_ids=";".join(sorted({x["observation_id"] for x in matching_records})),
                             raw_sha256s=";".join(sorted({x["raw_sha256"] for x in matching_records if x["raw_sha256"]})),
                             missing_primary_raw_hash=any(not x["raw_sha256"] for x in matching_records),
                             interpretation="PUBLISHED_DIRECTIONAL_WINDOW; no symmetry or annual extension"))
    write_csv("competitor_services.csv", services)
    coverage = []
    for route in sorted(set(registry) | late_oms):
        r = registry.get(route, {})
        matching = [x for x in weekly if x["route"] == route]
        status = r.get("coverage_status", "GAP_NOT_ABSENCE")
        if "MOW" in route.split("-"):
            status = "PHYSICAL_AIRPORT_REQUIRED"
        coverage.append({"route": route, "late_OMS_base_or_sub": route in late_oms,
            "existing_hypotheses": r.get("hypotheses", ""), "coverage_status": status,
            "directional_weekly_rows": len(matching), "published_directional_departures": sum(int(x["oneway_departures"]) for x in matching),
            "published_records_in_registry": r.get("published_records", "UNKNOWN"), "program_2026_rows": r.get("official_2026_program_rows", "UNKNOWN"),
            "carriers_in_existing_evidence": r.get("named_carriers", ""),
            "directional_detail": ";".join(f'{x["origin"]}>{x["destination"]}:{x["carriers"]}:{x["oneway_departures"]}' for x in matching),
            "complete_market": "False", "competitor_absence_established": "False",
            "future_2027_2028": "NO_AUTOMATIC_EXTENSION", "fare_20kg_and_seats": "UNKNOWN",
            "next_action": "choose DME/ZIA/etc then exact airport join" if "MOW" in route.split("-") else "reuse positive publications; keep missing direction/operator/period fields unknown"})
    write_csv("competitor_coverage.csv", coverage)
    verify = {"input_files_verified": len(checks), "checks": checks, "baseline_equals_previous": same,
        "late_summary_rows": len(late_summary), "old_summary_rows": len(old_summary),
        "bounded_coverage_pairs": len(coverage), "late_OMS_union_pairs": sorted(late_oms), "reusable_directional_service_rows": len(services),
        "CSV_key_check_records": len(records), "CSV_key_check_unique_departures": len(unique),
        "CSV_key_check_duplicates": len(records) - len(unique), "source_review_not_repeated": "No fresh primary HTML/PDF extraction or whole-source re-audit",
        "not_run": ["live collection", "browser/UI", "all-hub rerun", "direct-network rerun", "owner modifications", "new broad model", "global optimization", "future rights/awards", "operational acceptance"]}
    (HERE / "verification.json").write_text(json.dumps(verify, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in verify.items() if k not in ("checks", "not_run")}, ensure_ascii=False))
    print(json.dumps(money_receipt, ensure_ascii=False))

if __name__ == "__main__":
    main()
