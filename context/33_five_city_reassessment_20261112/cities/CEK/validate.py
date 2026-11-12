#!/usr/bin/env python3
"""Schema, provenance links, model coverage and arithmetic. Not commercial acceptance."""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
SCHEMAS = {
    "sources.csv": "source_id,title,organization,url,published_at,accessed_at,period,geography,metric,unit,source_type,access_status,limitations",
    "claims.csv": "claim_id,claim,evidence_status,source_ids,period,geography,value,unit,mechanism,decision_impact,uncertainty",
    "routes.csv": "origin,destination,product,season,competitors,frequency_evidence,demand_evidence,ground_alternative,rw_overlap,operating_constraints,assessment,source_ids,missing_fields",
    "features.csv": "feature_id,feature,evidence_ids,mechanism,affected_markets,magnitude_or_bound,counterevidence,decision_effect,unknowns",
}


def main():
    tables = {}
    for name, schema in SCHEMAS.items():
        with (HERE/name).open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == schema.split(","), (name, reader.fieldnames)
            rows = list(reader)
        assert rows and all(None not in r and all(v is not None for v in r.values()) for r in rows), name
        tables[name] = rows
    sources = {r["source_id"] for r in tables["sources.csv"]}
    claims = {r["claim_id"] for r in tables["claims.csv"]}
    features = {r["feature_id"] for r in tables["features.csv"]}
    for name, key, ids, prefix in (
        ("sources.csv", "source_id", sources, "CEK-S"),
        ("claims.csv", "claim_id", claims, "CEK-C"),
        ("features.csv", "feature_id", features, "CEK-F"),
    ):
        assert len(ids) == len(tables[name])
        assert all(x.startswith(prefix) for x in ids)
    for name in ("claims.csv", "routes.csv"):
        for r in tables[name]:
            assert r["source_ids"]
            assert set(r["source_ids"].split(";")) <= sources, (name, r)
    for r in tables["features.csv"]:
        assert set(r["evidence_ids"].split(";")) <= claims
        assert all(r[k] for k in SCHEMAS["features.csv"].split(","))
    for r in tables["claims.csv"]:
        assert r["claim"] and r["period"] and r["geography"] and r["uncertainty"]
        if r["evidence_status"] == "unknown":
            assert r["value"] == "", r
    routes = tables["routes.csv"]
    assert all(r["origin"] == "CEK" for r in routes)
    assert len({(r["origin"], r["destination"]) for r in routes}) == len(routes)
    model = list(csv.DictReader((PACKAGE/"inputs/model/network_routes.csv").open()))
    targets = {r["to"] if r["from"] == "CEK" else r["from"] for r in model if "CEK" in (r["from"], r["to"])}
    covered = {r["destination"] for r in routes}
    assert targets <= covered, targets-covered
    decision = json.loads((HERE/"decision.json").read_text())
    assert {a["id"] for a in decision["alternatives"]} == {"localdirect", "existingbase", "newbase", "hub", "groundfeed", "noproject"}
    assert decision["city"]["iata"] == "CEK"
    assert all(a["strongest_for"] and a["strongest_against"] and a["choice_condition"] and a["parameter_source"]
               and a["action_if_condition_fails"] for a in decision["alternatives"])
    subprocess.run(["python3", str(HERE/"calculate.py")], check=True, capture_output=True)
    calc = json.loads((HERE/"calculations.json").read_text())
    assert calc["CEK_base_route_sums"]["pax_year_segments"] == 388456
    assert calc["CEK_base_route_sums"]["pax_year_local"] == 180362
    assert calc["CEK_base_route_sums"]["pax_year_transfer_seg"] == 208094
    assert calc["CEK_base_one_way_flights_per_week"] == 92
    assert calc["CEK_base_scenario_seat_legs"] == 478400
    assert calc["two_weekly_round_trips_100_seats_52_weeks"]["seat_legs"] == 20800
    assert calc["groundfeed_example_scenario"]["minimum_before_flight_from_bus_departure_minutes"] == 288
    dossier = (HERE/"dossier.md").read_text()
    cited = set(re.findall(r"CEK-[SCF]\d{2}", dossier))
    assert cited <= sources | claims | features, cited-(sources|claims|features)
    # Pin the actual inputs; sibling research files can legitimately be dirty.
    manifest = json.loads((PACKAGE / "input_manifest.json").read_text())
    for entry in manifest:
        raw = (PACKAGE / entry["path"]).read_bytes()
        assert len(raw) == entry["bytes"], entry["path"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]
    out = {
        "status": "PASS", "scope": "schema_references_coverage_arithmetic_pinned_inputs_only",
        "table_rows": {k:len(v) for k,v in tables.items()},
        "model_destinations_covered": sorted(targets), "model_CEK_rows_extracted": calc["CEK_model_rows"],
        "all_six_alternatives": True, "unknown_values_not_zero_filled": True,
        "pinned_manifest_files_verified": len(manifest),
        "known_rounding": "104047 transfer OD from rounded leg sum vs104046 summary; not source modification",
        "not_proven": ["observed OD demand", "profit", "operable future fleet", "current MRO/base readiness", "subsidy award2027", "complete competitor census"],
        "sha256": {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir())
                   if p.is_file() and p.name != "validation.json"},
    }
    (HERE/"validation.json").write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({k:out[k] for k in ("status", "table_rows", "model_CEK_rows_extracted", "pinned_manifest_files_verified")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
