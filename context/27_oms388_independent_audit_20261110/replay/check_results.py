#!/usr/bin/env python3
"""Fast independent artifact/accounting check. Standard library only; no rerun or network."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = "d4a6eabb42671e5b16d44abedcdc6ceafb692528"


def rows(name):
    with (HERE / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_round2():
    """Saved addressed-round integrity, without re-running owner selectors."""
    r = json.loads((HERE / "round2/results.json").read_text())
    assert r["pass_check"] and r["source_sha"] == PIN
    assert r["protected_before"] == r["protected_after"] == {"files": 389, "mismatches": [], "pass": True}
    assert r["stopped_after_requested_checks"] and r["further_rounds"] == 0
    w = r["weeks"]
    assert w["source_sha"] == PIN and w["uncapped"] and not w["competitive"]
    full = w["annual_market_trips_both_directions"] * w["capture_share"]
    assert all(abs(x["sold_trips_year_both_directions"] - full) < 1e-7 for x in w["reference_vs_operating"])
    assert abs(w["no_rebooking_sold_trips_year"] + w["no_rebooking_lost_trips_year"] - full) < 1e-7
    s = r["shortlist"]
    candidates = rows("round2/candidate_ranks.csv")
    assert len(candidates) == s["universe_count"]
    assert len({x["candidate"] for x in candidates}) == len(candidates)
    n = s["shortlist_size"]
    raw = sorted(candidates, key=lambda x: -float(x["raw_score_rub_block_hour"]))
    joint = sorted(candidates, key=lambda x: -float(x["joint_initial_score_rub_block_hour"]))
    for ranking, field in ((raw, "raw_rank"), (joint, "joint_initial_rank")):
        assert [int(x[field]) for x in ranking] == list(range(1, len(candidates) + 1))
    raw_set, joint_set = ({x["candidate"] for x in ranking[:n]} for ranking in (raw, joint))
    assert len(raw_set & joint_set) == s["overlap"]
    assert len(raw_set - joint_set) == s["raw_only"] and len(joint_set - raw_set) == s["joint_only"]
    omitted = next(x for x in joint if x["candidate"] not in raw_set)
    assert omitted["candidate"] == s["best_omitted_under_joint_initial_objective"]["candidate"]
    for c in candidates:
        score = float(c["raw_score_rub_block_hour"]) + (float(c["support_rub_week"]) - float(c["foregone_rw_rub_week"])) / float(c["hours_week"])
        assert abs(score - float(c["joint_initial_score_rub_block_hour"])) < 1e-7
    p = r["rounding_patch"]
    assert p["pass_check"] and p["applied_in_disposable_copy"] and p["mismatches_fixed"] == 6
    assert p["zero_slider_all_rows"] and p["rows"] == 24 and p["patched_inline_script_syntax_checks"] > 0
    assert hashlib.sha256((HERE / "patches/001_authoritative_rounded_result.patch").read_bytes()).hexdigest() == p["patch_sha256"]
    for file, digest in r["publication"]["audit_script_sha256"].items():
        assert hashlib.sha256((HERE / file).read_bytes()).hexdigest() == digest, file
    assert not r["publication"]["head_equality_required"] and not r["publication"]["private_input_files_required"]
    addressed = rows("round2/addressed_findings.csv")
    assert {x["id"] for x in addressed} == {"M06", "M09", "RPL-05"}
    for finding in addressed:
        assert finding["source_sha"] == PIN
        assert all(finding[k] for k in ("priority", "file_line", "observation", "evidence", "impact_on_388_or_recommendation", "concrete_fix", "classification", "known_or_new", "reproduce_command"))
        for loc in finding["file_line"].split(";"):
            path, line = loc.strip().rsplit(":", 1)
            source = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{PIN}:{path}"]).decode()
            assert 0 < int(line) <= len(source.splitlines())
    assert all(v.startswith("UNKNOWN") for v in r["residual_unknowns"].values())
    assert (HERE / "round2/notes.md").is_file()
    return {"pass_check": True, "candidate_count": len(candidates), "top400_overlap": s["overlap"],
            "addressed_findings": len(addressed), "final_network_winner": "UNKNOWN"}


def main():
    v = json.loads((HERE / "validation.json").read_text())
    assert v["pass"] and v["pin"] == PIN
    # Audit-only commits may advance HEAD; source objects and owner bytes stay pinned.
    assert subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", f"{PIN}^{{commit}}"]).decode().strip() == PIN
    protected = json.loads((HERE.parent / "protected_owner_files.json").read_text())
    assert len(protected) == 389
    for p, h in protected.items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
    ledger = rows("ledger.csv")
    legs = [x for x in ledger if x["record_type"] == "leg"]
    ods = [x for x in ledger if x["record_type"].startswith("od_")]
    assert len(legs) == 12 and len(ods) == 36
    total = lambda rs, k: sum(float(x[k]) for x in rs)
    close = lambda a,b: abs(a-b) < 1e-4
    m = v["fixed_network"]["base_sub"]
    assert close(total(ods, "trips_year"), m["od_trips_year"])
    assert close(total(ods, "segments_year"), total(legs, "segments_year"))
    for k in ("ticket_gross_rub_year", "foregone_rw_rub_year", "ticket_after_migration_rub_year", "subsidy_rub_year"):
        assert close(total(ods, k), total(legs, k)) and close(total(ods, k), m[k]), k
    assert close(total(legs, "variable_cost_rub_year"), m["variable_cost_rub_year"])
    assert close(total(ods, "ticket_after_migration_rub_year") + total(ods, "subsidy_rub_year") - total(legs, "variable_cost_rub_year"), m["contribution_rub_year"])
    assert round(m["contribution_rub_year"] / 1e6) == 388
    assert m["full_pnl_rub_year"] is None
    components = ("fuel_rub_year", "mro_rub_year", "crew_rub_year", "navigation_rub_year", "ground_rub_year", "deicing_rub_year", "pax_variable_rub_year")
    for leg in legs:
        assert close(sum(float(leg[k]) for k in components), float(leg["variable_cost_rub_year"]))
    cf = {x["case"]: x for x in rows("counterfactuals.csv")}
    assert float(cf["base_sub12_support0"]["contribution_rub_year"]) < 0
    assert float(cf["base_sub12_support1"]["contribution_rub_year"]) > 0
    assert float(cf["base_sub12_one_payment_per_nonMOW_OD"]["contribution_rub_year"]) < 0
    br = rows("version_bridge.csv")
    assert close(sum(float(x["delta_rub_year"]) for x in br), float(br[-1]["contribution_rub_year"]) - float(br[0]["contribution_rub_year"]))
    findings = rows("findings.csv")
    assert len(findings) == len({x["id"] for x in findings}) == 11
    for x in findings:
        assert x["source_sha"] == PIN
        match = re.fullmatch(r"(.+):(\d+)", x["file_line"])
        assert match and (ROOT / match[1]).is_file()
        assert 0 < int(match[2]) <= len((ROOT / match[1]).read_text().splitlines())
        assert all(x[k] for k in ("classification", "concrete_correction", "evidence", "known_or_new"))
    coverage = rows("cost_coverage.csv")
    assert len(coverage) == 17
    assert close(sum(float(x["amount_rub_model_year"]) for x in coverage[:7]), m["variable_cost_rub_year"])
    patch = json.loads((HERE / "patches/validation.json").read_text())
    assert patch["pass"] and patch["sandbox_patch_applied"] and patch["fixes"] == 6
    # Source location for the suggested patch checked without touching the protected tree.
    subprocess.run(["git", "-C", str(ROOT), "apply", "--check", str(HERE / "patches/001_authoritative_rounded_result.patch")], check=True)
    round2 = check_round2()
    artifacts = {}
    for p in sorted(HERE.rglob("*")):
        if not p.is_file() or any(x.startswith(".") or x == "__pycache__" for x in p.relative_to(HERE).parts):
            continue
        if p.name in ("artifact_validation.json", "artifact_manifest.json", "run.log"):
            continue
        artifacts[str(p.relative_to(HERE))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (HERE / "artifact_manifest.json").write_text(json.dumps({"scope": "replay deliverables including round2; excludes artifact_manifest.json, artifact_validation.json, run.log, hidden env/temp and __pycache__", "sha256": artifacts}, ensure_ascii=False, indent=2) + "\n")
    result = dict(pass_check=True, protected_files=389, protected_changed=0, ledger_rows=48, leg_rows=12, od_rows=36,
                  findings=len(findings), cost_coverage_rows=len(coverage), suggested_patch_applies=True,
                  artifact_count=len(artifacts), pin=PIN, round2=round2,
                  scope="artifact and accounting integrity, no market/source/subsidy/operating/fullPnL acceptance")
    (HERE / "artifact_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
