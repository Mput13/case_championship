#!/usr/bin/env python3
"""Simulate how P40 market competition + recomputed P09 outputs shift the exact ratings in origin/шаг-1 dashboard."""
import copy
import io
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/a/agent-audit-2026-09/case_championship")
BASE = ROOT / "context" / "40_swarm_pricing_research_20261113"
OUT = BASE / "colleague_bridge"
OUT.mkdir(parents=True, exist_ok=True)


def gshow(path: str) -> str:
    return subprocess.check_output(["git", "show", f"origin/шаг-1:{path}"], cwd=ROOT).decode("utf-8")


# --- 1. Simulate dashboard function p09() exact city Top-12 ---
p9_old = pd.read_csv(io.StringIO(gshow("data/external/colleagues/p09_programmes.csv")))
p9_old["city"] = p9_old["programme_id"].str.split("_").str[0]
old_base = (
    p9_old[p9_old["scenario"] == "base"]
    .sort_values("delta_known_operating_subtotal", ascending=False)
    .groupby("city", as_index=False)
    .first()
)
old_cau_map = p9_old[p9_old["scenario"] == "cautious"].set_index("programme_id")["delta_known_operating_subtotal"].to_dict()
old_base["old_cautious_mln"] = (old_base["programme_id"].map(old_cau_map) / 1e6).round(1)
old_base["old_base_mln"] = (old_base["delta_known_operating_subtotal"] / 1e6).round(1)
old_top = old_base.sort_values("delta_known_operating_subtotal", ascending=False).reset_index(drop=True)
old_top["old_rank"] = old_top.index + 1

rps = pd.read_csv(BASE / "recomputed_programmes_summary.csv")
rps["city"] = rps["programme_id"].str.split("_").str[0]
new_base = (
    rps[rps["config"] == "comp_market_base"]
    .sort_values("delta_known_operating_subtotal", ascending=False)
    .groupby("city", as_index=False)
    .first()
)
new_cau_map = rps[rps["config"] == "comp_market_cautious"].set_index("programme_id")["delta_known_operating_subtotal"].to_dict()
new_exp_map = rps[rps["config"] == "comp_expansion_stress_2028"].set_index("programme_id")["delta_known_operating_subtotal"].to_dict()
new_base["new_base_mln"] = (new_base["delta_known_operating_subtotal"] / 1e6).round(1)
new_base["new_cautious_mln"] = (new_base["programme_id"].map(new_cau_map) / 1e6).round(1)
new_base["new_exp2028_mln"] = (new_base["programme_id"].map(new_exp_map) / 1e6).round(1)
new_top = new_base.sort_values("delta_known_operating_subtotal", ascending=False).reset_index(drop=True)
new_top["new_rank_base"] = new_top.index + 1

# Also rank cities by best programme in cautious
cau_best = (
    rps[rps["config"] == "comp_market_cautious"]
    .sort_values("delta_known_operating_subtotal", ascending=False)
    .groupby("city", as_index=False)
    .first()
)
cau_best = cau_best[cau_best["city"] != "KEEP"].sort_values("delta_known_operating_subtotal", ascending=False).reset_index(drop=True)
cau_best["rank_cautious"] = cau_best.index + 1
cau_best["best_cautious_mln"] = (cau_best["delta_known_operating_subtotal"] / 1e6).round(1)

p09_shift = new_top.merge(
    old_top[["city", "old_rank", "programme_id", "old_base_mln", "old_cautious_mln"]],
    on="city",
    suffixes=("_new", "_old"),
).merge(cau_best[["city", "rank_cautious", "programme_id", "best_cautious_mln"]].rename(columns={"programme_id": "best_cautious_prog"}), on="city", how="left")
p09_shift["rank_change_base"] = p09_shift["old_rank"] - p09_shift["new_rank_base"]
p09_shift = p09_shift[
    [
        "new_rank_base", "old_rank", "rank_change_base", "rank_cautious", "city",
        "programme_id_old", "programme_id_new", "old_base_mln", "new_base_mln",
        "old_cautious_mln", "new_cautious_mln", "new_exp2028_mln",
        "best_cautious_prog", "best_cautious_mln",
    ]
]
p09_shift.to_csv(OUT / "dashboard_p09_top12_shift.csv", index=False)

# --- 2. Simulate 20-city longlist scores (longlist_score.py exact formula) ---
cj = json.loads(gshow("data/processed/criteria.json"))
hw = pd.read_csv(BASE / "hub_weights_22.csv").set_index("hub")
ll = pd.read_csv(io.StringIO(gshow("data/processed/longlist.csv")))
iatas = ll["iata"].tolist()
cities = ll.set_index("iata")["city"].to_dict()
dist = {i: cj["values"][i]["dist_bases_km"]["v"] for i in iatas}


def utility(v, lo, hi, d):
    if v is None or not hi > lo:
        return 0.5
    z = min(1.0, max(0.0, (v - lo) / (hi - lo)))
    return 1 - z if d == "-" else z


def run_longlist(crit, vals, w_override=None):
    sc = {}
    for c in crit:
        xs = [v for i in vals for v in (vals[i].get(c["key"], {}).get("v"), vals[i].get(c["key"], {}).get("lo"), vals[i].get(c["key"], {}).get("hi")) if v is not None]
        lo = c["lo"] if c.get("lo") is not None else min(xs)
        hi = c["hi"] if c.get("hi") is not None else max(xs)
        sc[c["key"]] = (lo, hi)
    z = pd.DataFrame(index=iatas, dtype=float)
    for c in crit:
        k, (lo, hi) = c["key"], sc[c["key"]]
        for i in iatas:
            v = vals[i].get(k, {}).get("v")
            z.loc[i, k] = utility(c["fill"], lo, hi, c["dir"]) if v is None and c.get("fill") is not None else (0.5 if v is None else utility(v, lo, hi, c["dir"]))
    w = pd.Series({c["key"]: (w_override.get(c["key"], c["weight"]) if w_override else c["weight"]) for c in crit})
    s = (z[w.index] * w).sum(axis=1) / w.sum()
    df = pd.DataFrame({"iata": iatas, "city": [cities[i] for i in iatas], "dist_km": [dist[i] for i in iatas], "score": s.values})
    df = df.sort_values("score", ascending=False, kind="mergesort").reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


df_base = run_longlist(cj["criteria"], cj["values"])

w28_vals = hw.loc[iatas, "W_comp_2028"]
w28_norm = (w28_vals - w28_vals.min()) / (w28_vals.max() - w28_vals.min())

vals_blend = copy.deepcopy(cj["values"])
vals_w28 = copy.deepcopy(cj["values"])
crit_w28 = copy.deepcopy(cj["criteria"])
for c in crit_w28:
    if c["key"] == "competitor_hub":
        c["lo"], c["hi"] = None, None
for i in iatas:
    old_ch = float(cj["values"][i]["competitor_hub"]["v"])
    vals_blend[i]["competitor_hub"] = {"v": 0.5 * old_ch + 0.5 * float(w28_norm.loc[i])}
    vals_w28[i]["competitor_hub"] = {"v": float(w28_vals.loc[i])}

df_blend7 = run_longlist(cj["criteria"], vals_blend)
df_blend14 = run_longlist(cj["criteria"], vals_blend, w_override={"competitor_hub": 14.0})
df_w28_7 = run_longlist(crit_w28, vals_w28)

ll_m = (
    df_base.rename(columns={"score": "score_shag1", "rank": "rank_shag1"})
    .merge(df_blend7[["iata", "score", "rank"]].rename(columns={"score": "score_blend7", "rank": "rank_blend7"}), on="iata")
    .merge(df_blend14[["iata", "score", "rank"]].rename(columns={"score": "score_blend14", "rank": "rank_blend14"}), on="iata")
    .merge(df_w28_7[["iata", "score", "rank"]].rename(columns={"score": "score_w28_7", "rank": "rank_w28_7"}), on="iata")
)
ll_m["old_competitor_hub"] = [cj["values"][i]["competitor_hub"]["v"] for i in ll_m["iata"]]
ll_m["W_comp_2028"] = ll_m["iata"].map(hw["W_comp_2028"]).round(3)
ll_m["rank_shift_blend7"] = ll_m["rank_shag1"] - ll_m["rank_blend7"]
ll_m["rank_shift_w28_7"] = ll_m["rank_shag1"] - ll_m["rank_w28_7"]
for col in ["score_shag1", "score_blend7", "score_blend14", "score_w28_7"]:
    ll_m[col] = (ll_m[col] * 100).round(1)
# add >= 500 km ranks
for src_col, dst_col in [("rank_shag1", "r500_shag1"), ("rank_blend7", "r500_blend7"), ("rank_w28_7", "r500_w28_7")]:
    sub = ll_m[ll_m["dist_km"] >= 500].copy()
    sub[dst_col] = sub[src_col].rank().astype(int)
    ll_m = ll_m.merge(sub[["iata", dst_col]], on="iata", how="left")

ll_m.to_csv(OUT / "dashboard_longlist_rank_shift.csv", index=False)
print("Saved dashboard_p09_top12_shift.csv and dashboard_longlist_rank_shift.csv")
print(p09_shift.head(14).to_string(index=False))
