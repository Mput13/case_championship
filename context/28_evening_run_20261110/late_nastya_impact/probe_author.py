"""Narrow real OMS fixture. Imports captured author blobs; never calls main/all-hub run."""
import csv
import gzip
import hashlib
import importlib
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUTHOR = HERE / "inputs/late"
sys.dont_write_bytecode = True
sys.path.insert(0, str(AUTHOR / "src"))

def main():
    started = time.time()
    nm = importlib.import_module("network_model")
    # Recreate one existing external input only for Demand.links(); remove it after loading.
    compressed = HERE / "inputs/methods/context/28_evening_run_20261110/methods/inputs/audit_5905/replay/inputs/tochno_intercity.csv.gz"
    raw_path = AUTHOR / "data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(gzip.decompress(compressed.read_bytes()))
    D = nm.Demand()
    raw_path.unlink()
    AS = nm.load_assumptions()
    nodes = list(D.n.index)
    out = {"python": sys.version, "platform": platform.platform(), "numpy": nm.np.__version__,
           "pandas": nm.pd.__version__, "network_model_sha256": hashlib.sha256((AUTHOR / "src/network_model.py").read_bytes()).hexdigest(),
           "scope": "OMS only, author full node universe, base/base_sub caps 4/6/8/10; no all-hub/direct rerun", "caps": []}
    for scenario in ("base", "base_sub"):
        A = AS[scenario]
        candidates = []
        for cap in nm.search_caps(A):
            t = time.time()
            ch, r = nm.hub_network("OMS", D, dict(A, fleet_cap=float(cap)), A["demand_scen"], nodes)
            legs, trans, hours, cost, rev, loc, tr, flights, migr, forgone, subs = r
            row = {"scenario": scenario, "cap": cap, "chosen": ch, "routes": len(ch), "hours_week": hours,
                   "aircraft_by_hours_plus_spare": math.ceil(hours / (7 * A["block_h_per_day"])) + A["spare_aircraft"],
                   "weekly_result_rub": rev - cost, "annual_result_rub": (rev - cost) * A["weeks_per_year"],
                   "annual_subsidy_rub": subs * A["weeks_per_year"], "runtime_s": round(time.time() - t, 3),
                   "annual_segments": 2 * sum(L["carried_dir_week"] for L in legs.values()) * A["weeks_per_year"],
                   "annual_local_od": loc * A["weeks_per_year"], "annual_transfer_od": tr * A["weeks_per_year"],
                   "legs": [{"to": x, "km": L["km"], "frequency_each_way": L["freq"],
                             "fare_rub": nm.fare(A, L["km"]), "subsidy_rule": nm.sub_rule(D, A, "OMS", x),
                             "annual_direct_segments_proxy": D.seg_tab.get(("OMS", x)), "direct_flag": D.has_direct("OMS", x),
                             "local_annual": 2 * L["local_carried"] * A["weeks_per_year"]} for x, L in legs.items()]}
            assert abs(row["annual_segments"] - row["annual_local_od"] - 2 * row["annual_transfer_od"]) < 1e-6
            out["caps"].append(row)
            candidates.append((len(ch), rev - cost, hours, ch, r))
            print(json.dumps({k: row[k] for k in ("scenario", "cap", "routes", "annual_result_rub", "runtime_s")}), flush=True)
        best = nm.best_of(candidates, A)
        assert best[1] >= candidates[0][1] and best[1] >= candidates[-1][1]
        saved = nm.pd.read_csv(AUTHOR / "data/processed/network_summary.csv")
        saved_row = saved[(saved.hub == "OMS") & (saved.scenario == scenario)].iloc[0].to_dict()
        expected = round(best[1] * A["weeks_per_year"] / 1e6)
        assert saved_row["result_mln_year"] == expected
        out.setdefault("selected", {})[scenario] = {"chosen": best[3], "result_mln_year": expected, "saved_output": saved_row,
                                                    "assertions": ["best_of >= cap4 and cap10", "saved rounded result equals narrow replay"]}
    # Eligibility and fare counterexamples use actual selected routes, not an invented award.
    A = AS["base_sub"]
    for a, b in [("OMS", x) for x in out["selected"]["base_sub"]["chosen"]]:
        km = D.km(a, b)
        out.setdefault("eligible_selected_pairs", []).append({"a": a, "b": b, "km": km, "formula_fare": nm.fare(A, km),
            "sub_rule": nm.sub_rule(D, A, a, b), "direct_flag": D.has_direct(a, b), "seg_proxy": D.seg_tab.get((a, b))})
    # Fixed-frequency algebra from the same real OMS-IKT demand, independent of annual output rounding.
    annual_demand = D.get("OMS", "IKT", "base")
    fixed_share = nm.leg_share({"km": D.km("OMS", "IKT"), "dem": annual_demand / 104,
                                "seg": D.seg("OMS", "IKT", "base") / 104,
                                "competitive": D.has_direct("OMS", "IKT")}, 7, AS["base"])
    out["weeks_identity"] = {"pair": "OMS-IKT", "annual_base_demand": annual_demand, "fixed_share": fixed_share,
        "annual_local_52": annual_demand / (2 * 52) * fixed_share * 2 * 52,
        "annual_local_48": annual_demand / (2 * 48) * fixed_share * 2 * 48,
        "classification": "fixed share/frequency diagnostic: W cancels, not cancellation loss"}
    # Existing published cap3 ramp is within the eight-route requirement in the cautious scenario.
    for cap in (3, 4):
        A = AS["cautious"]
        ch, r = nm.hub_network("OMS", D, dict(A, fleet_cap=float(cap)), "cautious", nodes)
        out.setdefault("cautious_cap3_boundary", []).append({"cap": cap, "routes": len(ch), "chosen": ch,
            "annual_result_rub": (r[4] - r[3]) * A["weeks_per_year"], "hours_week": r[2],
            "classification": "hour-budget feasibility only; not real operating acceptance"})
    out["runtime_s"] = round(time.time() - started, 3)
    (HERE / "author_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=lambda v: v.item()) + "\n")
    print("PASS: bounded OMS fixture and saved outputs", flush=True)

if __name__ == "__main__":
    main()
