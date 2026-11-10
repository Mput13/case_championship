"""Read exact Git blobs; write only this review package. No network or owner writes."""
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = {
    "late": "066d3e288b41859b9ac33a3e571456a22d877795",
    "previous": "14354571b90545cd0618548481a857bf6b388d4a",
    "baseline": "4a9763565f70b9ab1eddde2f5daca07687560948",
    "evidence": "38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b",
    "source_review": "13f7c373954cc16b33a53b7c46436ee3f15f753b",
    "methods": "5512f7d474a5db4bb658aae30b10f8b886629861",
    "assembly": "5101302f93c349268f4ba0ff26832ff261e1a9e7",
    "panel_review": "0cf4a64f",
}

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

late_paths = [
    "src/network_model.py", "src/rules.py", "src/demand_model.py", "src/airports_meta.py",
    "src/build_dashboard.py", "data/assumptions/network.csv", "data/assumptions/choice.csv",
    "data/assumptions/bases.csv", "data/assumptions/subsidy_cap_84_103.csv",
    "data/assumptions/subsidy_hub_airports.csv", "data/assumptions/siberia_fareast_regions.csv",
    "data/assumptions/range.csv", "data/assumptions/south_west_regions.csv",
    "data/assumptions/longlist_params.csv", "data/assumptions/resort_airports.csv", "data/assumptions/demand.csv",
    "data/manual/airport_names.csv", "data/manual/closed_airports.csv", "data/manual/rw_routes_now.csv",
    "data/manual/roadmap.csv", "data/manual/competitor_bases.csv", "data/manual/route_competitors.csv",
    "data/manual/route_competitors_todo.csv", "data/manual/carrier_names.csv",
    "data/raw/favt_subsidy_2026.csv", "data/processed/catchments.csv", "data/processed/od_fit.json",
    "data/processed/od_pairs.csv", "data/processed/demand_estimates.csv", "data/processed/network_summary.csv",
    "data/processed/network_routes.csv", "data/processed/fleet_ramp.csv", "data/processed/mandatory_routes_table.csv",
    "docs/24_hypotheses_comparison.md", "docs/26_steps_2_4_5.md", "docs/27_handoff_route_competitors.md", "docs/HANDOFF.md",
]
ep = "context/28_evening_run_20261110/evidence/"
paths = {"late": late_paths,
    "previous": ["src/network_model.py", "data/assumptions/network.csv", "data/processed/network_summary.csv", "docs/HANDOFF.md"],
    "baseline": ["src/network_model.py", "data/assumptions/network.csv", "data/processed/network_summary.csv"],
    "evidence": [ep + p for p in ["findings.md", "subsidy_controls.csv", "subsidy_cap_examples.csv", "subsidy_cap_84_103_seats.csv", "subsidy_special_fare_grid.csv", "subsidy_route_matches.csv", "subsidy_applicability.csv", "pair_registry.csv", "pair_hypothesis_join.csv", "weekly_service_context.csv", "dated_service_instances.csv", "dated_service_records.csv", "source_registry.csv", "alternative_timing_examples.csv", "raw/web/favt_regional_rules/text.txt", "raw/web/favt_regional_rules/receipt.json", "output_manifest.json"]],
    "source_review": ["context/28_evening_run_20261110/evidence_review/" + p for p in ["report.md", "verification.json", "input_manifest.json", "output_manifest.json"]],
    "methods": ["context/28_evening_run_20261110/methods/final_handoff.md", "context/28_evening_run_20261110/methods/inputs/audit_5905/replay/inputs/tochno_intercity.csv.gz"],
    "assembly": ["context/28_evening_run_20261110/dashboard_handoff/" + p for p in ["README.md", "passport_excerpt.md", "source_manifest.json", "source_index.csv"]],
    "panel_review": ["context/26_strategy_reset_20261110/nastya_panel_review/report.md", "context/26_strategy_reset_20261110/nastya_panel_review/evidence/replay.json"],
}

def main():
    manifest, missing = [], []
    for label, files in paths.items():
        sha = git("rev-parse", PINS[label] + "^{commit}").decode().strip()
        PINS[label] = sha
        for path in files:
            exists = subprocess.run(["git", "cat-file", "-e", f"{sha}:{path}"], cwd=ROOT, capture_output=True)
            if exists.returncode:
                missing.append({"pin": label, "path": path, "error": exists.stderr.decode()})
                continue
            data = git("show", f"{sha}:{path}")
            dest = HERE / "inputs" / label / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            manifest.append({"pin": label, "commit": sha, "source_path": path,
                             "git_blob": git("rev-parse", f"{sha}:{path}").decode().strip(),
                             "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                             "local_path": str(dest.relative_to(HERE))})
    compressed = HERE / "inputs/methods/context/28_evening_run_20261110/methods/inputs/audit_5905/replay/inputs/tochno_intercity.csv.gz"
    raw = gzip.decompress(compressed.read_bytes())
    dest = HERE / "runtime/data_intercity_connectivity_162_v20260629.csv"
    manifest.append({"pin": "methods_gzip_derivative", "source_path": str(compressed.relative_to(HERE)),
                     "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "local_path": str(dest.relative_to(HERE)),
                     "classification": "ephemeral derivative verified in memory; NOT a tracked blob of late commit; raw not delivered"})
    instructions = (ROOT / "AGENTS.md").read_bytes()
    insdest = HERE / "inputs/instructions/AGENTS.md"
    insdest.parent.mkdir(parents=True, exist_ok=True)
    insdest.write_bytes(instructions)
    manifest.append({"pin": "working_tree_instructions", "source_path": "AGENTS.md", "local_path": str(insdest.relative_to(HERE)),
                     "sha256": hashlib.sha256(instructions).hexdigest(), "bytes": len(instructions),
                     "classification": "local instructions read; not present in colleague commit"})
    (HERE / "source_manifest.json").write_text(json.dumps({"pins": PINS, "files": manifest, "missing": missing}, ensure_ascii=False, indent=2) + "\n")
    meta = {"pins": PINS, "branch_at_start": git("branch", "--show-current").decode().strip(),
            "review_base_head": git("rev-parse", "HEAD").decode().strip(),
            "origin_step1_observed": git("rev-parse", "origin/шаг-1").decode().strip(),
            "commits": {k: git("show", "-s", "--format=fuller", v).decode() for k, v in PINS.items()},
            "diff_name_status": git("diff", "--name-status", PINS["previous"], PINS["late"]).decode(),
            "between_commits": git("log", "--format=%H %an <%ae> %aI %s", PINS["previous"] + ".." + PINS["late"]).decode()}
    (HERE / "provenance.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"source_files": len(manifest), "total_bytes": sum(x["bytes"] for x in manifest), "missing": missing}, ensure_ascii=False))

if __name__ == "__main__":
    main()
