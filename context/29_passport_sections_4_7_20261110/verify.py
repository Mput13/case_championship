"""Addressed editorial checks; no optimizer replay, downloads or source mutation."""
from pathlib import Path
import csv
import hashlib
import io
import json
import subprocess

ROOT = Path(__file__).resolve().parent
AUTHOR = ROOT / "sources/author"


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


manifest = json.loads((ROOT / "source_manifest.json").read_text())
for entry in manifest["files"]:
    data = (ROOT / entry["saved_path"]).read_bytes()
    assert len(data) == entry["bytes"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]

summary = rows(AUTHOR / "data/processed/network_summary.csv")
routes = rows(AUTHOR / "data/processed/network_routes.csv")
base = {r["hub"]: r for r in summary if r["scenario"] == "base"}
oms = base["OMS"]
assert int(oms["segments_year"]) == int(oms["od_trips_year"]) + int(oms["transfer_od_year"])
assert int(oms["net_new_segments_year"]) == int(oms["segments_year"]) - int(oms["rw_migrated_year"])
assert round(int(oms["net_new_segments_year"]) / 108850000 * 100, 2) == float(oms["share_pp"])
assert max((r for r in base.values() if r["hub"]), key=lambda r: int(r["result_mln_year"]))["hub"] == "AER"
base_sub = next(r for r in summary if r["scenario"] == "base_sub" and r["hub"] == "OMS")
assert all(base_sub[k] == oms[k] for k in oms if k != "scenario")

oms_routes = [r for r in routes if r["scenario"] == "base" and r["variant"] == "Хаб OMS"]
assert len(oms_routes) == 12
assert sum(int(r["freq_week_each_way"]) for r in oms_routes) * 2 == int(oms["flights_week"])
assert abs(sum(int(r["pax_year_segments"]) for r in oms_routes) - int(oms["segments_year"])) <= len(oms_routes) / 2
assert abs(sum(float(r["result_mln_year"]) for r in oms_routes) - int(oms["result_mln_year"])) <= 1.1

direct = [r for r in routes if r["scenario"] == "base" and r["variant"].startswith("Прямые")]
assert len(set(r["variant"] for r in direct)) == 8
assert len(direct) == 24
assert len({tuple(sorted((r["from"], r["to"]))) for r in direct}) == 19

weights = rows(AUTHOR / "data/assumptions/longlist_weights.csv")
assert sum(float(r["weight"]) > 0 for r in weights) == 10
assert sum(float(r["weight"]) for r in weights) == 100
assert len(rows(AUTHOR / "data/processed/longlist_scores_min500.csv")) == 15
profiles = rows(AUTHOR / "data/processed/longlist_profiles_min500.csv")
assert sum(r["top3_iata"].split(",")[0].strip() == "OMS" for r in profiles) == 4

# The earlier fixed-network fuel calculation is used only after checking that
# the current base OMS rows and money stayed the same as its author snapshot.
old_sha = "dc1eb38d4c6b7c18386b3db4b1750166bb010ffd"
old_blob = subprocess.check_output(["git", "show", old_sha + ":data/processed/network_routes.csv"], cwd=ROOT)
old_rows = list(csv.DictReader(io.StringIO(old_blob.decode())))
old_oms = [r for r in old_rows if r["scenario"] == "base" and r["variant"] == "Хаб OMS"]
fields = ["from", "to", "freq_week_each_way", "pax_year_segments", "revenue_mln_year", "cost_mln_year", "result_mln_year"]
project = lambda rs: sorted(tuple(r[k] for k in fields) for r in rs)
assert project(old_oms) == project(oms_routes)
fuel = {float(r["credit_rub_per_t"]): r for r in rows(ROOT / "sources/fuel_sensitivity.csv") if r["network"] == "fixed_new_network"}
assert round(float(fuel[32930]["contribution_rub"]) / 1e6) == int(oms["result_mln_year"])
assert round(float(fuel[0]["contribution_rub"]) / 1e6) == -636
q = float(fuel[0]["fuel_tonnes_year"])
assert abs(float(fuel[32930]["contribution_rub"]) - float(fuel[0]["contribution_rub"]) - q * 32930) < 0.01
assert abs(-float(fuel[0]["contribution_rub"]) / q - float(fuel[0]["credit_breakeven_rub_per_t"])) < 1e-6

# Corpus metadata, from the pinned source; do not copy the entire message corpus.
posts_blob = subprocess.check_output(["git", "show", manifest["author_sha"] + ":data/raw/favt_posts.csv"], cwd=ROOT)
posts = list(csv.DictReader(io.StringIO(posts_blob.decode())))
dates = [r["dt_msk"] for r in posts]
assert len(posts) == 8329
assert sum(d.startswith("2026") for d in dates) == 5981

receipt = {
    "status": "PASS",
    "scope": "Source hashes, exported arithmetic, units, city counts, profile counts, unchanged base OMS route export, fixed-network fuel identity, corpus dates",
    "not_run": ["full optimizer replay", "new independent model review", "UI audit", "live airline pilot", "future cash flow"],
    "author_sha": manifest["author_sha"],
    "verified_source_files": len(manifest["files"]),
    "oms_base": oms,
    "fuel_zero_mln": float(fuel[0]["contribution_rub"]) / 1e6,
    "fuel_threshold_rub_per_t": float(fuel[0]["credit_breakeven_rub_per_t"]),
    "previous_base_route_fields_equal": fields,
    "previous_author_sha": old_sha,
    "favt_posts": {"count": len(posts), "count_2026": 5981, "min_dt_msk": min(dates), "max_dt_msk": max(dates), "sha256": hashlib.sha256(posts_blob).hexdigest()},
}
(ROOT / "verification.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "sources": receipt["verified_source_files"], "full_optimizer": "NOT_RUN"}))
