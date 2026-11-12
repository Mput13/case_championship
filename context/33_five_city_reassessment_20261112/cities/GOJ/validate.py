#!/usr/bin/env python3
"""Validate this research package and reconcile only pinned/saved evidence."""
import ast
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[3]
SCHEMAS = {
    "sources.csv": "source_id,title,organization,url,published_at,accessed_at,period,geography,metric,unit,source_type,access_status,limitations",
    "claims.csv": "claim_id,claim,evidence_status,source_ids,period,geography,value,unit,mechanism,decision_impact,uncertainty",
    "routes.csv": "origin,destination,product,season,competitors,frequency_evidence,demand_evidence,ground_alternative,rw_overlap,operating_constraints,assessment,source_ids,missing_fields",
    "features.csv": "feature_id,feature,evidence_ids,mechanism,affected_markets,magnitude_or_bound,counterevidence,decision_effect,unknowns",
}


def read(n):
    with (P/n).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    data = {}
    checks = []
    for name, fields in SCHEMAS.items():
        data[name] = read(name)
        assert data[name], name
        assert list(data[name][0]) == fields.split(","), name
        assert all(None not in r and all(v is not None for v in r.values()) for r in data[name]), name
        checks.append(f"schema_and_row_width:{name}")
    source_ids = {r["source_id"] for r in data["sources.csv"]}
    claim_ids = {r["claim_id"] for r in data["claims.csv"]}
    feature_ids = {r["feature_id"] for r in data["features.csv"]}
    for name, key, ids in [("sources.csv","source_id",source_ids), ("claims.csv","claim_id",claim_ids), ("features.csv","feature_id",feature_ids)]:
        assert len(ids) == len(data[name]), name
        assert all(i.startswith("GOJ-") for i in ids)
    for name, col, valid in [("claims.csv","source_ids",source_ids), ("routes.csv","source_ids",source_ids), ("features.csv","evidence_ids",source_ids|claim_ids)]:
        for r in data[name]:
            assert set(r[col].split(";")) <= valid, (name, r[col])
    checks.append("unique_GOJ_ids_and_all_registry_references")
    for r in data["sources.csv"]:
        assert r["accessed_at"] == "2026-11-12"
        assert not r["published_at"] or r["published_at"] <= "2026-11-12", r["source_id"]
        assert r["url"] and r["period"] and r["geography"] and r["limitations"]
    for r in data["claims.csv"]:
        if r["evidence_status"] == "UNKNOWN":
            assert r["value"] == "", r["claim_id"]
        if r["value"]:
            float(r["value"])
    checks.append("source_metadata_dates_and_unknown_not_zero")
    model = read("model_route_diagnostics.csv")
    routes = data["routes.csv"]
    route_set = {r["destination"] for r in routes}
    assert all(r["origin"] == "GOJ" for r in routes)
    assert len(route_set) == len(routes)
    assert len(model) == 33 and len({r["destination"] for r in model}) == 13
    assert {r["destination"] for r in model} <= route_set
    for r in routes:
        assert all(r[k] for k in SCHEMAS["routes.csv"].split(",")), r["destination"]
    checks.append("all_33_model_rows_and_13_selected_markets_covered")
    d = json.loads((P/"decision.json").read_text())
    assert {r["mode"] for r in d["options"]} == {"localdirect","existingbase","newbase","hub","groundfeed","noproject"}
    for o in d["options"]:
        for k in ["outcome","strongest_for","strongest_against","condition","threshold_or_direction","missing_parameter_sources","change_action"]:
            assert o[k], (o["mode"],k)
        assert set(o["evidence_ids"]) <= claim_ids
    assert all(x["value"] is None and x["source"] and x["direction"] for x in d["critical_missing_fields"])
    assert d["funded_ramp_requirement"]["initial_loss_allowed"] is True
    checks.append("six_options_with_conditions_bounds_counterarguments_and_actions")
    c = json.loads((P/"calculations.json").read_text())
    assert all(x["matches_manifest"] for x in c["input_manifest_verified"])
    # Independent reconciliation against the selected summary, not the rounded route totals.
    summary = [r for r in read("../../inputs/model/network_summary.csv") if r["hub"] == "GOJ"]
    assert len(summary) == 4
    for r in summary:
        t=c["model_summaries_from_route_rows"][r["scenario"]]
        assert int(t["segments"]) == int(r["segments_year"])
        assert t["weekly_legs"] == int(r["flights_week"])
        assert abs(t["sum_rounded_route_variable_results_mln"]-float(r["result_mln_year"])) <= .51
        assert abs(t["segments"]-t["local"]-t["transfer_segments"]) <= 2
        assert abs(t["transfer_segments"]-2*float(r["transfer_od_year"])) <= 2
    for r in model:
        assert abs(float(r["model_total_segments"])-float(r["model_local_segments"])-float(r["model_transfer_segments"])) <= 1
    checks.append("pinned_summary_totals_and_explicit_rounding_reconciled")
    counts={(r["direction"],r["airport"],r["carrier"]):r["departures"] for r in c["schedule_counts"]}
    for direction in ["in","out"]:
        assert counts[(direction,"LED","Россия")]+counts[(direction,"LED","Smartavia")] == 17
        assert counts[(direction,"SVX","RED WINGS")] == 5
        assert counts[(direction,"KUF","RED WINGS")] == 2
        assert counts[(direction,"SVO","Россия")]+counts[(direction,"SVO","Аэрофлот")] == 22
    assert len(read("schedule_observations.csv")) == 77
    assert len(read("schedule_week.csv")) == 128
    checks.append("dated_week_counts_both_directions_no_annualization_as_current_frequency")
    subsidy_rows=read("listed_subsidies_2026.csv")
    assert len(subsidy_rows)==15
    assert len({(r["origin"],r["destination"]) for r in subsidy_rows})==9
    checks.append("nine_listed_subsidy_pairs_fifteen_period_rows_not_current_frequencies")
    f=next(r for r in c["partial_GOJ_airport_invoice_scenarios"] if r["mass_t_scenario"]==49.45 and r["billable_pax_scenario"]==70)
    assert abs(f["list_partial_rub_ex_vat"]-143006.85)<.001
    assert c["two_weekly_rotations_100_seats_52_weeks"]["seats_two_directions"] == 20800
    assert c["family_budget_scenario"]["return_tickets_rub"] == 64000
    checks.append("fee_capacity_and_household_scenario_arithmetic")
    dossier=(P/"dossier.md").read_text()
    refs=set(re.findall(r"GOJ-S\d{2}",dossier))
    assert refs <= source_ids, refs-source_ids
    assert "2026-11-16" in (P/"source_observations.json").read_text()
    assert "announcement_only_unreconciled" in next(r["assessment"] for r in routes if r["destination"]=="PEE") or "HOLD_CONFLICT" in next(r["assessment"] for r in routes if r["destination"]=="PEE")
    for n in ["calculate.py","validate.py"]:
        ast.parse((P/n).read_text())
    checks.append("dossier_references_future_tariff_exclusion_and_script_syntax")
    # All task changes must be inside GOJ. Read-only check; no reset/stash/checkout.
    status=subprocess.check_output(["git","status","--porcelain","--untracked-files=all"],cwd=P,text=True)
    paths=[line[3:] for line in status.splitlines()]
    prefix="context/33_five_city_reassessment_20261112/cities/GOJ/"
    outside=[x for x in paths if not x.startswith(prefix)]
    assert not outside, outside
    checks.append("git_changes_only_GOJ_directory")
    artifacts={str(x.relative_to(P)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(P.rglob("*"))
               if x.is_file() and x.name!="validation.json" and "_tmp" not in x.parts and x.name!="build_registry.py"}
    report={"status":"PASS_OFFLINE_RESEARCH_PACKAGE", "as_of":"2026-11-12", "checks":checks,
            "counts":{"sources":len(source_ids),"claims":len(claim_ids),"features":len(feature_ids),"route_products":len(routes),"author_rows":len(model),"author_markets":13,"schedule_period_rows":77,"schedule_dated_records":128,"manifest_files":34},
            "artifact_sha256":artifacts,
            "not_validated":["market OD or actual LF", "current ticket checkout fare", "financial profitability or receipts", "dispatch/crew/MCT", "source data accessible only in web index"],
            "source_QA":"Primary tables/PDFs read; local tariff01.11 pages1-2, discounts page22 and Volga scan visually checked; UUA document date2015 retained. No future tariff16.11 used."}
    (P/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"checks":len(checks),"counts":report["counts"]},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
