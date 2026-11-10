"""Read-only delivery verification. --write-manifest seals all other package files."""
import argparse
import csv
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--staged", action="store_true", help="Also compare every delivered byte to Git index and enforce staged scope")
    args = parser.parse_args()
    source = json.loads((HERE / "source_manifest.json").read_text())
    for r in source["files"]:
        if r["pin"] == "methods_gzip_derivative":
            data = gzip.decompress((HERE / r["source_path"]).read_bytes())
        else:
            data = (HERE / r["local_path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == r["sha256"]
        if "commit" in r:
            original = subprocess.check_output(["git", "show", r["commit"] + ":" + r["source_path"]], cwd=ROOT)
            assert original == data, r["local_path"]
    probe = json.loads((HERE / "author_probe.json").read_text())
    assert len(probe["caps"]) == 8
    assert probe["selected"]["base"]["result_mln_year"] == -186
    assert probe["selected"]["base_sub"]["result_mln_year"] == -14
    assert probe["weeks_identity"]["annual_local_52"] == probe["weeks_identity"]["annual_local_48"] == 23351.5
    cautious = probe["cautious_cap3_boundary"]
    assert cautious[0]["routes"] == 8 and cautious[0]["hours_week"] <= 140
    assert cautious[0]["annual_result_rub"] > cautious[1]["annual_result_rub"]
    for name in ["impact_matrix.csv", "competitor_schema.csv", "competitor_coverage.csv", "competitor_services.csv", "subsidy_counterexamples.csv", "published_summary_delta.csv"]:
        rows = list(csv.DictReader((HERE / name).open()))
        assert rows and all(None not in r for r in rows), name
    coverage = list(csv.DictReader((HERE / "competitor_coverage.csv").open()))
    assert len(coverage) == 45
    assert sum(r["late_OMS_base_or_sub"] == "True" for r in coverage) == 10
    assert all(r["complete_market"] == "False" and r["competitor_absence_established"] == "False" for r in coverage)
    assembly = json.loads((HERE / "inputs/assembly/context/28_evening_run_20261110/dashboard_handoff/source_manifest.json").read_text())
    assert assembly["pins"]["methods_final"] == source["pins"]["methods"]
    assert source["pins"]["late"] not in json.dumps(assembly)
    assert not list(HERE.rglob("__pycache__"))
    assert not (HERE / "inputs/late/data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv").exists()
    manifest_path = HERE / "output_manifest.json"
    files = sorted(p for p in HERE.rglob("*") if p.is_file() and p != manifest_path)
    expected = {str(p.relative_to(HERE)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in files}
    if args.write_manifest:
        manifest_path.write_text(json.dumps({"schema": 1, "files": expected, "policy": "Exact package bytes; manifest excludes itself; review commit SHA is reported after commit"}, ensure_ascii=False, indent=2) + "\n")
    manifest = json.loads(manifest_path.read_text())
    assert manifest["files"] == expected
    if args.staged:
        staged_names = subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT).decode().split("\0")
        prefix = str(HERE.relative_to(ROOT)) + "/"
        assert all(not p or p.startswith(prefix) for p in staged_names)
        for path in [*files, manifest_path]:
            original = subprocess.check_output(["git", "show", ":" + str(path.relative_to(ROOT))], cwd=ROOT)
            assert original == path.read_bytes(), path
    print(json.dumps({"status": "PASS", "source_entries": len(source["files"]), "exact_git_blobs": sum("commit" in r for r in source["files"]),
        "package_files_without_manifest": len(expected), "package_bytes_without_manifest": sum(r["bytes"] for r in expected.values()),
        "OMS_base_and_sub_caps": len(probe["caps"]), "additional_cautious_caps": len(cautious),
        "frozen_assembly_references_methods5512": True, "late_input_not_in_frozen_assembly": True,
        "raw_runtime_removed": True, "staged_bytes_verified": args.staged, "owner_or_live_work": "NOT_RUN"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
