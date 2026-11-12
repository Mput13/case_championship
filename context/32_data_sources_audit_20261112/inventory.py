"""Read pinned Git blobs; do not refresh or modify the author model."""
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PIN = "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6"


def blob(path):
    return subprocess.check_output(["git", "show", f"{PIN}:{path}"], cwd=ROOT)


def rows(path):
    return list(csv.DictReader(io.StringIO(blob(path).decode("utf-8-sig"))))


def main():
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", PIN, "data", "src", "docs"], cwd=ROOT
    ).decode().splitlines()
    tables = []
    for path in paths:
        if path.endswith(".csv") and path.startswith(("data/manual/", "data/assumptions/", "data/criteria/", "data/external/")):
            raw = blob(path)
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            records = list(reader)
            tables.append({"path": path, "records": len(records), "fields": reader.fieldnames,
                           "sha256": hashlib.sha256(raw).hexdigest()})
    pairs = rows("data/processed/demand_pairs.csv")
    estimates = rows("data/processed/demand_estimates.csv")
    known = rows("data/manual/known_flows.csv")
    rw = rows("data/manual/rw_routes_now.csv")
    longlist = rows("data/processed/longlist.csv")
    toml = blob("data/sources.toml").decode("utf-8-sig")
    sections = re.findall(r"^\[([^]]+)\]", toml, re.M)
    manifest = json.loads(blob("data/raw/_manifest.json"))
    examples = {
        "known_flow": known[0],
        "estimated_pair": next(r for r in pairs if r["a"] == "OMS" and r["b"] == "VOG") if any(r["a"] == "OMS" and r["b"] == "VOG" for r in pairs) else pairs[0],
        "rail_spotcheck": rows("data/manual/rail_schedule_spotchecks.csv")[0],
        "fare_spotcheck": rows("data/manual/fare_offer_spotchecks.csv")[0],
        "omsk": next(r for r in longlist if r["iata"] == "OMS"),
        "colleague_od": rows("data/external/colleagues/od_registry.csv")[0],
    }
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "subject_commit": PIN,
        "subject_author": subprocess.check_output(["git", "show", "-s", "--format=%an", PIN], cwd=ROOT).decode().strip(),
        "subject_committed_at": subprocess.check_output(["git", "show", "-s", "--format=%cI", PIN], cwd=ROOT).decode().strip(),
        "scope": "Tracked blobs only. This inventory is not a source truth audit, new demand fit, or live API test.",
        "counts": {
            "pairs": len(pairs),
            "rail_imputed_96h": sum(r["rail_imputed_96h"].lower() in ("true", "1", "1.0") for r in pairs),
            "known_flow_records": len(known), "known_fit_records": sum(r["use"] == "fit" for r in known),
            "known_lower_bound_records": sum(r["use"] == "lower" for r in known),
            "known_annualized_records": sum(r["annual_factor"] != "1" for r in known),
            "pairs_with_observed_segments": sum(bool(r["observed"]) for r in estimates),
            "pairs_with_schedule_estimate": sum(bool(r["seg_schedule"]) for r in estimates),
            "pairs_with_schedule_lower_bound": sum(bool(r["seg_schedule_lower"]) for r in estimates),
            "uncertain_pairs": sum(r["uncertain"].lower() == "true" for r in estimates),
            "pairs_with_rw_seats": sum(bool(r["rw_seats_week_each_way"]) for r in estimates),
            "route_competitor_records": len(rows("data/manual/route_competitors.csv")),
            "route_competitor_todo_records": len(rows("data/manual/route_competitors_todo.csv")),
            "rw_route_records": len(rw),
            "rw_frequency_origins": dict(Counter(r["freq_status"] for r in rw)),
            "registered_sources": len(sections),
            "manifest_sources": len(manifest),
            "manual_csv_files": sum(t["path"].startswith("data/manual/") for t in tables),
            "assumption_csv_files": sum(t["path"].startswith("data/assumptions/") for t in tables),
        },
        "registered_without_manifest_entry": sorted(set(sections) - set(manifest)),
        "manifest_summary": {k: {x: v.get(x) for x in ("status", "rows", "fetched_at", "checked_at")}
                             for k, v in manifest.items()},
        "known_flow_publishers": dict(Counter(r["source"] for r in known)),
        "tables": tables, "examples": examples,
        "demand_fit": json.loads(blob("data/processed/demand_fit.json")),
        "od_fit": json.loads(blob("data/processed/od_fit.json")),
        "network_parameters": rows("data/assumptions/network.csv"),
    }
    (OUT / "audit_facts.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"subject_commit": PIN, "counts": result["counts"],
                      "registered_without_manifest_entry": result["registered_without_manifest_entry"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
