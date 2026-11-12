"""Materialize exact selected Git inputs without changing an author's checkout."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "model": (
        "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6",
        [
            "data/processed/longlist.csv", "data/processed/longlist_scores.csv",
            "data/processed/network_summary.csv", "data/processed/network_routes.csv",
            "data/processed/catchments.csv", "data/processed/demand_fit.json",
            "data/processed/od_fit.json", "data/manual/rw_routes_now.csv",
            "data/manual/route_competitors.csv", "data/manual/route_competitors_todo.csv",
            "data/manual/known_flows.csv", "data/manual/rail_schedule_spotchecks.csv",
            "data/manual/fare_offer_spotchecks.csv", "data/manual/airport_tech.csv",
            "data/assumptions/network.csv", "data/assumptions/longlist_params.csv",
            "data/assumptions/longlist_weights.csv", "data/assumptions/bases.csv",
            "data/sources.toml", "docs/32_current_model_results.md",
            "docs/33_case_readiness_audit.md", "docs/34_data_and_formula_audit.md",
            "docs/35_population_transport_fares_subsidies.md",
        ],
    ),
    "distance_audit": (
        "ce10c1f4b7273905b78c3394a12912ecf5a814f1",
        ["context/31_distance_rule_audit_20261112/" + name for name in [
            "findings.json", "screening_scores.csv", "network_reselection.json",
            "fuel_fixed_network.json", "transfer_gate.json", "runtime_manifest.json",
        ]],
    ),
    "source_audit": (
        "f9eafa804d2a90fa16f0b9521c2c48a48731614d",
        ["context/32_data_sources_audit_20261112/" + name for name in [
            "source_catalog.json", "gaps.csv", "audit_facts.json",
            "live_source_checks.json", "source_lock.json",
        ]],
    ),
}


def main():
    manifest = []
    for group, (commit, paths) in SOURCES.items():
        for source_path in paths:
            data = subprocess.check_output(["git", "show", f"{commit}:{source_path}"])
            relative = Path("inputs") / group / Path(source_path).name
            destination = ROOT / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            manifest.append({"path": str(relative), "commit": commit,
                             "source_path": source_path, "bytes": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
    (ROOT / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Snapshotted {len(manifest)} exact Git inputs; {sum(r['bytes'] for r in manifest):,} bytes")


if __name__ == "__main__":
    main()
