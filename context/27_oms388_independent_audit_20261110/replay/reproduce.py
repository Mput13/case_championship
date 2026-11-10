#!/usr/bin/env python3
"""Offline audit. Reads git objects and a hash-verified compressed public input.

No checkout, network, city-ranking computation or writes outside replay/.
Owner source files are copied byte-for-byte into disposable, non-git sandboxes.
Fixed-network probes compile the original nested build() AST without its selector.
Amounts are RUB per model year; flows are both directions, unless a column says otherwise.
"""
import argparse
import ast
import contextlib
import csv
import gzip
import hashlib
import importlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = "d4a6eabb42671e5b16d44abedcdc6ceafb692528"
OLD = "1654110dfdc3f6737aebce95e46dd993d631be5b"
LATE = "4a9763565f70b9ab1eddde2f5daca07687560948"
RAW = "data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv"
RAW_SHA = "aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53"
FILES = ["src/network_model.py", "src/demand_model.py", "src/rules.py", "src/airports_meta.py",
         "src/build_dashboard.py", "src/dashboard_template.html", "data/external/colleagues/night_common_comparison.csv"]
PREFIXES = ["data/assumptions/", "data/manual/", "data/processed/"]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def sha(b):
    return hashlib.sha256(b).hexdigest()


def verify_source_pin():
    """The pin identifies source objects; an audit-only descendant HEAD is valid."""
    assert git("rev-parse", f"{PIN}^{{commit}}").decode().strip() == PIN


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def rows_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def protected():
    manifest = json.loads((HERE.parent / "protected_owner_files.json").read_text())
    changed = [p for p, h in manifest.items() if not (ROOT / p).is_file() or sha((ROOT / p).read_bytes()) != h]
    return {"files": len(manifest), "mismatches": changed, "pass": not changed}


def prepare(sb, ref, raw):
    names = git("ls-tree", "-r", "--name-only", ref).decode().splitlines()
    selected = [p for p in names if p in FILES or any(p.startswith(x) for x in PREFIXES)]
    for p in selected:
        dest = sb / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(git("show", f"{ref}:{p}"))
    (sb / RAW).parent.mkdir(parents=True, exist_ok=True)
    (sb / RAW).write_bytes(raw)
    return {p: sha((sb / p).read_bytes()) for p in selected}


def load_module(sb):
    for name in ("network_model", "demand_model", "airports_meta", "rules", "build_dashboard"):
        sys.modules.pop(name, None)
    sys.path.insert(0, str(sb / "src"))
    return importlib.import_module("network_model")


def fixed_builder(nm):
    tree = ast.parse((nm.ROOT / "src/network_model.py").read_text())
    hub = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "hub_network")
    build = next(x for x in hub.body if isinstance(x, ast.FunctionDef) and x.name == "build")
    wrapper = ast.parse("def fixed(H,D,A,scen,S):\n W=A['weeks_per_year']\n return build(S)\n")
    wrapper.body[0].body.insert(1, build)
    ast.fix_missing_locations(wrapper)
    ns = dict(nm.__dict__)
    exec(compile(wrapper, str(nm.ROOT / "src/network_model.py") + ":original_build_AST", "exec"), ns)
    return ns["fixed"], ns, sha(ast.dump(build, include_attributes=False).encode())


@contextlib.contextmanager
def no_migration(ns):
    orig = ns.get("rw_pax_week")
    ns["rw_pax_week"] = lambda *args: 0.0
    try:
        yield
    finally:
        if orig is not None:
            ns["rw_pax_week"] = orig


def metrics(nm, r, A):
    W = A["weeks_per_year"]
    legs, trans, hours, cost, rev, local, transfer, flights = r[:8]
    migr, forgone, subs = r[8:] if len(r) == 11 else (0.0, 0.0, 0.0)
    seg = sum(2 * L["carried_dir_week"] for L in legs.values())
    return dict(ticket_gross_rub_year=(rev + forgone - subs) * W,
                foregone_rw_rub_year=forgone * W, ticket_after_migration_rub_year=(rev - subs) * W,
                subsidy_rub_year=subs * W, total_revenue_rub_year=rev * W,
                variable_cost_rub_year=cost * W, contribution_rub_year=(rev - cost) * W,
                segments_year=seg * W, local_trips_year=local * W, transfer_trips_year=transfer * W,
                od_trips_year=(local + transfer) * W, migrated_year=migr * W,
                block_hours_year=hours * W, flights_year=flights * W,
                aircraft=int(math.ceil(hours / (A["block_h_per_day"] * 7)) + A["spare_aircraft"]),
                routes=len(legs), full_pnl_rub_year=None)


def ledger(nm, r, A):
    W = A["weeks_per_year"]
    legs, trans = r[:2]
    rows = []
    # OD rows carry ticket revenue once; cost and a transparent revenue allocation live on leg rows.
    for x, L in legs.items():
        n = 2 * W * L["local_carried"]
        mg = 2 * W * L["migrated"]
        f = nm.fare(A, L["km"])
        rows.append(dict(record_type="od_local", a="OMS", via="", b=x, trips_year=n, segments_year=n,
                         fare_rub_per_trip=f, ticket_gross_rub_year=n * f, migrated_year=mg,
                         foregone_rw_rub_year=mg * f, ticket_after_migration_rub_year=(n - mg) * f,
                         eligible_segments_year=n - mg if x != "MOW" else 0,
                         subsidy_rub_year=(n - mg) * nm.sub(A, "OMS", x)))
    for x, y, d, t in trans:
        n = 2 * W * t
        f = nm.fare(A, d) * A["transfer_fare_factor"]
        rows.append(dict(record_type="od_transfer", a=x, via="OMS", b=y, trips_year=n, segments_year=2 * n,
                         fare_rub_per_trip=f, ticket_gross_rub_year=n * f, migrated_year=0.0,
                         foregone_rw_rub_year=0.0, ticket_after_migration_rub_year=n * f,
                         eligible_segments_year=n * (int(x != "MOW") + int(y != "MOW")),
                         subsidy_rub_year=n * (nm.sub(A, "OMS", x) + nm.sub(A, "OMS", y))))
    for x, L in legs.items():
        flown = 2 * L["freq"] * W
        bh = L["block_h"]
        seg = 2 * L["carried_dir_week"] * W
        fuel = flown * (A["fuel_t_per_hour"] * bh + A["fuel_t_per_cycle"]) * A["fuel_rub_per_t"]
        mro, crew, nav = [flown * bh * A[k] for k in ("mro_rub_per_hour", "crew_rub_per_hour", "navigation_rub_per_hour")]
        ground = flown * A["ground_rub_per_flight"]
        deice = flown * A["deicing_rub_per_flight"]
        paxcost = seg * A["pax_cost_rub"]
        odrows = [row for row in rows if row["record_type"].startswith("od_") and x in (row["a"], row["b"])]
        # Local 100%, transfer 50/50: accounting allocation only, not a second ticket sale.
        gross = sum(row["ticket_gross_rub_year"] * (0.5 if row["record_type"] == "od_transfer" else 1) for row in odrows)
        forgone = sum(row["foregone_rw_rub_year"] for row in odrows)
        eligible = seg - 2 * W * L["migrated"] if x != "MOW" else 0.0
        subsidy = eligible * A["subsidy_rub_per_pax"] * A["use_subsidy"]
        cost = fuel + mro + crew + nav + ground + deice + paxcost
        rows.append(dict(record_type="leg", a="OMS", via="", b=x, trips_year="", segments_year=seg,
                         freq_week_each_way=L["freq"], flights_year=flown, block_hours_year=flown * bh,
                         km=L["km"], ticket_gross_rub_year=gross, foregone_rw_rub_year=forgone,
                         ticket_after_migration_rub_year=gross - forgone, subsidy_rub_year=subsidy,
                         eligible_segments_year=eligible, migrated_year=2 * W * L["migrated"],
                         fuel_rub_year=fuel, mro_rub_year=mro, crew_rub_year=crew, navigation_rub_year=nav,
                         ground_rub_year=ground, deicing_rub_year=deice, pax_variable_rub_year=paxcost,
                         flight_variable_rub_year=cost - paxcost, variable_cost_rub_year=cost,
                         allocated_contribution_rub_year=gross - forgone + subsidy - cost))
    for row in rows:
        row.update(source_sha=PIN, scenario="base_sub", period="model_year_52_weeks_2028_proxy", geography="OMS_network")
    return rows


def compare_csv(published, actual):
    import pandas as pd
    a, b = pd.read_csv(published), pd.read_csv(actual)
    try:
        pd.testing.assert_frame_equal(a, b, check_dtype=False, check_exact=False, rtol=0, atol=1e-6)
        return {"pass": True, "rows": len(a), "byte_equal": published.read_bytes() == actual.read_bytes()}
    except AssertionError as e:
        return {"pass": False, "rows": len(a), "error": str(e)[:1400]}


def run_worker(sb, out, label):
    import numpy as np
    import pandas as pd
    nm = load_module(sb)
    direct_runs = []
    original_direct = nm.direct_network
    def capture_direct(D, A, scenario, nodes):
        result = original_direct(D, A, scenario, nodes)
        direct_runs.append((A, scenario, result))
        return result
    nm.direct_network = capture_direct  # observe the return; execute original owner function exactly once/call
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        nm.main()  # Real, unmodified owner calculation. Writes only disposable sandbox.
    (out / "owner_run.txt").write_text(log.getvalue())
    checks = {}
    for f in ("network_summary.csv", "network_routes.csv", "mandatory_routes_table.csv", "fleet_ramp.csv"):
        if not (nm.P / f).exists():
            continue  # fleet_ramp was introduced after owner165.
        # Published bytes were saved separately by parent before main overwrites its copy.
        if (out / ("published_" + f)).exists():
            checks[f] = compare_csv(out / ("published_" + f), nm.P / f)
        shutil.copyfile(nm.P / f, out / ("replayed_" + f))
    fixed, ns, ast_sha = fixed_builder(nm)
    D = nm.Demand()
    AS = nm.load_assumptions()
    A = AS["base"]
    routes = pd.read_csv(nm.P / "network_routes.csv")
    base = routes[(routes.scenario == "base") & (routes.variant == "Хаб OMS")].to.tolist()
    b = fixed("OMS", D, A, "base", base)
    data = {"label": label, "python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
            "csv_checks": checks, "base_spokes": base, "base": metrics(nm, b, A), "build_ast_sha256": ast_sha}
    if "base_sub" in AS:
        S = routes[(routes.scenario == "base_sub") & (routes.variant == "Хаб OMS")].to.tolist()
        Ab = AS["base_sub"]
        r = fixed("OMS", D, Ab, "base", S)
        data["base_sub_spokes"] = S
        data["base_sub"] = metrics(nm, r, Ab)
        lr = ledger(nm, r, Ab)
        rows_csv(out / "ledger.csv", lr)
        data["transfer_rw_existing_pairs"] = [{"a": x, "b": y, "trips_year": 2 * Ab["weeks_per_year"] * t}
                                             for x, y, _, t in r[1] if nm.RW_FREQ.get(frozenset((x, y)), 0) > 0]
        cfs = []
        for network, spoke in (("base8", base), ("base_sub12", S)):
            for subsidy in (0.0, 1.0):
                Ac = dict(A, use_subsidy=subsidy)
                rr = fixed("OMS", D, Ac, "base", spoke)
                m = metrics(nm, rr, Ac)
                cfs.append(dict(case=f"{network}_support{int(subsidy)}", network=network, source_sha=PIN,
                                subsidy_policy="current_per_nonMOW_new_segment", support_fraction=subsidy,
                                frequency="owner_build_fixed_point_unchanged_by_support", **m))
        eligible_od = sum(row["trips_year"] for row in lr if row["record_type"].startswith("od_") and row["a"] != "MOW" and row["b"] != "MOW")
        m = metrics(nm, r, Ab)
        alt_sub = eligible_od * Ab["subsidy_rub_per_pax"]
        cfs.append(dict(case="base_sub12_one_payment_per_nonMOW_OD", network="base_sub12", source_sha=PIN,
                        subsidy_policy="scenario_one_payment_per_OD_both_endpoints_nonMOW", support_fraction="",
                        frequency="exact_same_flights_and_sales", **dict(m, subsidy_rub_year=alt_sub,
                        total_revenue_rub_year=m["ticket_after_migration_rub_year"] + alt_sub,
                        contribution_rub_year=m["ticket_after_migration_rub_year"] + alt_sub - m["variable_cost_rub_year"])))
        cfs.append(dict(case="base_sub12_after_known_costs_unknown_fullPnL", network="base_sub12", source_sha=PIN,
                        subsidy_policy="current", **dict(m, contribution_rub_year=m["contribution_rub_year"]),
                        omitted_costs_rub_year="UNKNOWN", old_network_delta_rub_year="UNKNOWN"))
        rows_csv(out / "counterfactuals.csv", cfs)
        legs = [row for row in lr if row["record_type"] == "leg"]
        ods = [row for row in lr if row["record_type"].startswith("od_")]
        eps = 1e-4
        data["ledger_checks"] = {
            "leg_count": len(legs), "od_count": len(ods),
            "ticket_od_vs_leg": abs(sum(x["ticket_gross_rub_year"] for x in ods) - sum(x["ticket_gross_rub_year"] for x in legs)) < eps,
            "subsidy_od_vs_leg": abs(sum(x["subsidy_rub_year"] for x in ods) - sum(x["subsidy_rub_year"] for x in legs)) < eps,
            "cost_vs_model": abs(sum(x["variable_cost_rub_year"] for x in legs) - m["variable_cost_rub_year"]) < eps,
            "revenue_vs_model": abs(sum(x["ticket_after_migration_rub_year"] + x["subsidy_rub_year"] for x in ods) - m["total_revenue_rub_year"]) < eps,
            "contribution_vs_model": abs(sum(x["allocated_contribution_rub_year"] for x in legs) - m["contribution_rub_year"]) < eps,
            "segment_identity": abs(m["segments_year"] - m["od_trips_year"] - m["transfer_trips_year"]) < eps,
            "capacity": all(L["lf"] <= Ab["lf_max"] + 1e-12 for L in r[0].values())}
        data["thresholds"] = dict(eligible_od_for_OD_scenario=eligible_od,
            subsidy_eligible_segments=m["subsidy_rub_year"] / Ab["subsidy_rub_per_pax"],
            support_fraction_for_zero=(m["variable_cost_rub_year"] - m["ticket_after_migration_rub_year"]) / m["subsidy_rub_year"],
            rub_per_eligible_segment_for_zero=(m["variable_cost_rub_year"] - m["ticket_after_migration_rub_year"]) / (m["subsidy_rub_year"] / Ab["subsidy_rub_per_pax"]),
            max_omitted_cost_if_old_delta_zero_rub_year=m["contribution_rub_year"],
            max_omitted_cost_per_aircraft_month_rub=m["contribution_rub_year"] / m["aircraft"] / 12,
            ticket_receipt_fraction_for_zero=(m["variable_cost_rub_year"] - m["subsidy_rub_year"]) / m["ticket_after_migration_rub_year"])
        # Network section only: invoke same projection that builds the HTML data.
        bd = importlib.import_module("build_dashboard")
        net = bd.load_network()
        dump(out / "replayed_net.json", net)
        # Physical pair aggregation diagnostic: 8 programs is not 8 endpoint pairs.
        direct = []
        for sc, g in routes[routes.variant.str.startswith("Прямые")].groupby("scenario", sort=False):
            direct.append(dict(scenario=sc, programs=int(g.variant.nunique()), leg_rows=len(g),
                unique_city_pairs=len({tuple(sorted((x["from"], x["to"]))) for x in g.to_dict("records")}),
                sum_rounded_segments=int(g.pax_year_segments.sum()),
                duplicated_pair_demand="pooled_once_in_owner_joint; not_independent_sales"))
        data["direct_counts"] = direct
        pair_probes = []
        for Aa, scenario, result in direct_runs:
            agg = {}
            for triangle in result:
                for L in triangle[8]:
                    g = agg.setdefault(tuple(sorted((L["a"], L["b"]))), {"L": L, "F": 0, "carried": 0.0, "migrated": 0.0})
                    g["F"] += L["freq"]
                    g["carried"] += L["carried_dir_week"]
                    g["migrated"] += L["migrated"]
            max_error = max_migration_error = 0.0
            for pair, g in agg.items():
                L, F = g["L"], g["F"]
                expected = min(L["dem"] * nm.leg_share(L, F, Aa), F * Aa["seats"] * Aa["lf_max"])
                max_error = max(max_error, abs(expected - g["carried"]))
                max_migration_error = max(max_migration_error, abs(min(expected, L["rw_now"]) - g["migrated"]))
            pair_probes.append(dict(scenario=scenario, support=Aa["use_subsidy"], physical_pairs=len(agg),
                max_week_direction_pax_residual=max_error, max_migration_residual=max_migration_error,
                pass_check=max_error < 1e-9 and max_migration_error < 1e-9))
        data["direct_pair_checks"] = pair_probes
        data["fixed_support_checks"] = []
        for network in ("base8", "base_sub12"):
            r0, r1 = [next(row for row in cfs if row["case"] == network + "_support" + str(k)) for k in (0, 1)]
            invariant = ("ticket_gross_rub_year", "foregone_rw_rub_year", "variable_cost_rub_year", "segments_year", "block_hours_year", "flights_year", "aircraft")
            unchanged = all(abs(r0[k] - r1[k]) < 1e-5 for k in invariant)
            residual = r1["contribution_rub_year"] - r0["contribution_rub_year"] - r1["subsidy_rub_year"]
            data["fixed_support_checks"].append(dict(network=network, flights_sales_costs_unchanged=unchanged,
                subsidy_effect_residual_rub=residual, pass_check=unchanged and abs(residual) < 1e-5))
        # One-scenario selected programs already aggregate physical demand in joint(); no old B3 recurrence.
        caut = routes[(routes.scenario == "cautious_sub") & (routes.variant == "Хаб OMS")].to.tolist()
        Ar = AS["cautious_sub"]
        cr = fixed("OMS", D, Ar, "cautious", caut)
        data["cautious_sub"] = metrics(nm, cr, Ar)
    dump(out / "metrics.json", data)


def bridge(sb_new, sb_old, old_spokes, base_spokes, sub_spokes):
    # Old demand object remains bound to old module globals after current imports.
    old = load_module(sb_old)
    Do = old.Demand()
    new = load_module(sb_new)
    Dn = new.Demand()
    f, ns, _ = fixed_builder(new)
    A = new.load_assumptions()["base"]
    # OLD.seg did not exist: pre-change competitive capture used that same endpoint/segment get().
    Do.seg = lambda a, b, sc: Do.get(a, b, sc)
    class View:
        def __init__(self, get_obj, seg_obj):
            self.get_obj, self.seg_obj = get_obj, seg_obj
        def __getattr__(self, name):
            return getattr(self.get_obj, name)
        def seg(self, a, b, sc):
            return self.seg_obj.get(a, b, sc)
    stages = [
        ("165_in_current_build_equivalent", Do, old_spokes, False, 0, "old demand/capture; same fares/costs; no migration/support"),
        ("new_endpoint_demand_on_old8", View(Dn, Do), old_spokes, False, 0, "endpoint demand + endogenous frequencies/capacity; old competitive segment basis"),
        ("new_competitor_segments_on_old8", Dn, old_spokes, False, 0, "competitive frequency denominator to measured/modelled segment table; frequencies recalc"),
        ("migration_on_old8", Dn, old_spokes, True, 0, "current local own-RW migration deduction; same topology"),
        ("current_base8_no_support", Dn, base_spokes, True, 0, "topology and resulting frequencies old8 to current base8; no support"),
        ("current_sub12_no_support", Dn, sub_spokes, True, 0, "topology and resulting frequencies base8 to sub12; no support"),
        ("current_sub12_support", Dn, sub_spokes, True, 1, "support only; same sub12 flights/sales/costs"),
    ]
    rows, prev = [], None
    for i, (name, D, S, migration, subsidy, note) in enumerate(stages):
        Ac = dict(A, use_subsidy=float(subsidy))
        with (contextlib.nullcontext() if migration else no_migration(ns)):
            m = metrics(new, f("OMS", D, Ac, "base", S), Ac)
        row = dict(order=i, stage=name, source_sha=OLD if i == 0 else PIN, execution_source_sha=PIN, period="model_year_52_weeks",
                   geography="OMS_network", note=note, attribution="sequential_path_not_Shapley; topology_fixed_per_stage_frequencies_endogenous",
                   delta_rub_year=0.0 if prev is None else m["contribution_rub_year"] - prev, spokes=";".join(S), **m)
        rows.append(row)
        prev = m["contribution_rub_year"]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, help="Bootstrap only: exact existing public input, stored gzip in replay/inputs")
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--worker-out", type=Path)
    parser.add_argument("--label")
    args = parser.parse_args()
    if args.worker:
        run_worker(args.worker, args.worker_out, args.label)
        return
    before = protected()
    assert before["pass"], before
    verify_source_pin()  # protected() above still requires all owner bytes unchanged.
    gz = HERE / "inputs/tochno_intercity.csv.gz"
    if args.raw:
        raw = args.raw.read_bytes()
        assert sha(raw) == RAW_SHA
        gz.parent.mkdir(exist_ok=True)
        gz.write_bytes(gzip.compress(raw, mtime=0))
    raw = gzip.decompress(gz.read_bytes())
    assert sha(raw) == RAW_SHA
    (HERE / ".tmp").mkdir(exist_ok=True)
    outputs = HERE / "runs"
    outputs.mkdir(exist_ok=True)
    manifests = {}
    with tempfile.TemporaryDirectory(dir=HERE / ".tmp", prefix="replay-") as tmp:
        tmp = Path(tmp)
        for label, ref in (("owner165", OLD), ("owner4a976", LATE), ("pin", PIN)):
            sb, out = tmp / label, outputs / label
            out.mkdir(exist_ok=True)
            manifests[label] = {"ref": ref, "inputs": prepare(sb, ref, raw)}
            for name in ("network_summary.csv", "network_routes.csv", "mandatory_routes_table.csv", "fleet_ramp.csv"):
                if (sb / "data/processed" / name).exists():
                    shutil.copyfile(sb / "data/processed" / name, out / ("published_" + name))
            print(f"Running original {label}", flush=True)
            subprocess.run([sys.executable, str(__file__), "--worker", str(sb), "--worker-out", str(out), "--label", label], check=True,
                           env={**__import__('os').environ, "PYTHONDONTWRITEBYTECODE": "1"})
        old = json.loads((outputs / "owner165/metrics.json").read_text())
        pin = json.loads((outputs / "pin/metrics.json").read_text())
        late = json.loads((outputs / "owner4a976/metrics.json").read_text())
        br = bridge(tmp / "pin", tmp / "owner165", old["base_spokes"], pin["base_spokes"], pin["base_sub_spokes"])
        br.append(dict(order=7, stage="4a976_to_d4a", source_sha=PIN, note="model and inputs identical; template-only change",
                       delta_rub_year=pin["base_sub"]["contribution_rub_year"] - late["base_sub"]["contribution_rub_year"],
                       **pin["base_sub"]))
        rows_csv(HERE / "version_bridge.csv", br)
        # Exact fare/cost parameter equality, independent of bridge attribution ordering.
        import pandas as pd
        ao = pd.read_csv(tmp / "owner165/data/assumptions/network.csv").set_index("parameter")
        an = pd.read_csv(tmp / "pin/data/assumptions/network.csv").set_index("parameter")
        shared = ao.index.intersection(an.index)
        assumption_changes = [k for k in shared if any(float(ao.loc[k, sc]) != float(an.loc[k, sc]) for sc in ("base", "cautious"))]
        h = git("show", f"{PIN}:outputs/redwings_panel.html").decode()
        pos = h.index("const D = ") + len("const D = ")
        embedded, _ = json.JSONDecoder().raw_decode(h[pos:])
        net = json.loads((outputs / "pin/replayed_net.json").read_text())
        panel_checks = {key: {"pass": embedded["net"][key] == net[key], "rows": len(net[key])} for key in ("summary", "routes", "asm", "check", "nodes")}
        ui_deltas = []
        for row in net["summary"]:
            shown = row["revenue_mln_year"] - row["var_cost_mln_year"]
            if shown != row["result_mln_year"]:
                ui_deltas.append(dict(scenario=row["scenario"], vkey=row["vkey"], result_mln_year=row["result_mln_year"],
                                      bar_result_mln_year=shown, delta_mln=shown - row["result_mln_year"]))
        dump(HERE / "panel_validation.json", dict(scope="embedded net data and extracted arithmetic only; no DOM/browser/full UI acceptance",
             sections=panel_checks, rounded_bar_differences=ui_deltas,
             pin_oms_base_sub=next(x for x in net["summary"] if x["scenario"] == "base_sub" and x["vkey"] == "OMS")))
        # Proven small bug: zero-slider result must use authoritative independently rounded result.
        template = (tmp / "pin/src/dashboard_template.html").read_text()
        orig = "const res=(r,kk)=>(r.revenue_mln_year-r.subsidy_mln_year)*(1+kk)+r.subsidy_mln_year-r.var_cost_mln_year;"
        replacement = "const res=(r,kk)=>r.result_mln_year+(r.revenue_mln_year-r.subsidy_mln_year)*kk;"
        assert template.count(orig) == 1
        patched = template.replace(orig, replacement)
        (tmp / "pin/src/dashboard_template.html").write_text(patched)
        import difflib
        patch = "".join(difflib.unified_diff(template.splitlines(True), patched.splitlines(True),
                        fromfile="a/src/dashboard_template.html", tofile="b/src/dashboard_template.html"))
        (HERE / "patches").mkdir(exist_ok=True)
        (HERE / "patches/001_authoritative_rounded_result.patch").write_text(patch)
        (tmp / "pin/src/dashboard_template.html").write_text(template)
        subprocess.run(["patch", "-p1", "-i", str(HERE / "patches/001_authoritative_rounded_result.patch")],
                       cwd=tmp / "pin", check=True, capture_output=True)
        assert (tmp / "pin/src/dashboard_template.html").read_text() == patched
        fixture = json.dumps(net["summary"], ensure_ascii=False)
        js = "const rows=" + fixture + ";" + replacement + "if(rows.some(r=>res(r,0)!==r.result_mln_year))process.exit(1); console.log(JSON.stringify({pass:true,rows:rows.length,zeroSliderUsesAuthoritativeResult:true}));"
        patch_check = json.loads(subprocess.check_output(["node", "-e", js]))
        patch_check.update(scope="arithmetic only; slope still uses rounded net ticket millions", model_effect_rub_year=0,
                           fixes=len(ui_deltas), sandbox_patch_applied=True, original_template_sha256=sha(template.encode()))
        dump(HERE / "patches/validation.json", patch_check)
        shutil.copyfile(outputs / "pin/ledger.csv", HERE / "ledger.csv")
        shutil.copyfile(outputs / "pin/counterfactuals.csv", HERE / "counterfactuals.csv")
        # Tax-net proceeds, old-network changes, subsidy entitlement, dispatch and full PnL remain unknown.
        validation = dict(pin=PIN, protected_before=before, protected_after=protected(),
                          source_inputs=manifests, raw_sha256=sha(raw), raw_matches_owner_manifest=True,
                          csv_replays={k: json.loads((outputs / k / "metrics.json").read_text())["csv_checks"] for k in manifests},
                          ledger=pin["ledger_checks"], fixed_network=pin,
                          panel=panel_checks, patch=patch_check,
                          version_bridge=dict(shared_assumption_changes=assumption_changes,
                              current_build_old_input_residual_rub=br[0]["contribution_rub_year"] - old["base"]["contribution_rub_year"],
                              telescoping_residual_rub=sum(x["delta_rub_year"] for x in br) - (pin["base_sub"]["contribution_rub_year"] - old["base"]["contribution_rub_year"])),
                          limitations=["one principal replay pass, no external research", "annual model, not recorded sales or future operating acceptance",
                              "ticket_after_migration is not tax/commission net yield", "all subsidy entitlement and old-network/cost omissions remain UNKNOWN",
                              "old C/N weekly model is not annualized or causally spliced into this bridge",
                              "cited methods/README.md absent at a77e4cf; read handoff_compact.md/common_comparison_readout.md instead"])
        validation["pass"] = (validation["protected_after"]["pass"] and all(v["pass"] for k in validation["csv_replays"].values() for v in k.values())
             and all(v["pass"] for v in panel_checks.values()) and all(v for k,v in pin["ledger_checks"].items() if isinstance(v,bool))
             and abs(validation["version_bridge"]["current_build_old_input_residual_rub"]) < 1e-3
             and abs(validation["version_bridge"]["telescoping_residual_rub"]) < 1e-3 and patch_check["pass"]
             and all(x["pass_check"] for x in pin["direct_pair_checks"] + pin["fixed_support_checks"]))
        dump(HERE / "validation.json", validation)
        assert validation["pass"], "Replay checks failed; inspect validation.json"
        subprocess.run([sys.executable, str(HERE / "build_report.py")], check=True)
        subprocess.run([sys.executable, str(HERE / "check_results.py")], check=True)
        print(json.dumps({"pass": validation["pass"], "base_sub": pin["base_sub"], "thresholds": pin["thresholds"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
