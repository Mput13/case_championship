#!/usr/bin/env python3
"""One bounded, offline addressed round; never calls owner main()/selectors.

Run with the Python from replay/requirements.txt. --verify recomputes the narrow
diagnostics and compares saved results instead of rewriting them. All temporary
copies and outputs are confined to round2/. No browser/network/private inputs.
"""
import argparse
import ast
import copy
import csv
import gzip
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPLAY = HERE.parent
spec = importlib.util.spec_from_file_location("oms388_replay", REPLAY / "reproduce.py")
rep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rep)
PIN = rep.PIN


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-7), (a, b)


def direct_parts(nm):
    """Original universe + tri_eval + joint, stopping before pre/greedy loops."""
    tree = ast.parse(rep.git("show", f"{PIN}:src/network_model.py").decode())
    fn = copy.deepcopy(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "direct_network"))
    cutoff = next(i for i, n in enumerate(fn.body) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "pre" for t in n.targets))
    fn.body = fn.body[:cutoff] + ast.parse("return tri, tri_eval, joint, max_h").body
    fn.name = "addressed_direct_parts"
    module = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(module)
    ns = dict(nm.__dict__)
    exec(compile(module, "pin:src/network_model.py:309-398", "exec"), ns)
    original = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "direct_network")
    return ns[fn.name], {n.name: rep.sha(ast.dump(n, include_attributes=False).encode())
                          for n in original.body if isinstance(n, ast.FunctionDef)}


def source_row(nm, a, b, value, scen):
    # Demand.__init__ lets demand_estimates override od_pairs.
    for filename in ("demand_estimates.csv", "od_pairs.csv"):
        with (nm.P / filename).open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if {row["a"], row["b"]} == {a, b}:
                    field = "od_" + scen
                    if row.get(field) and math.isclose(float(row[field]), value, rel_tol=1e-12):
                        return f"data/processed/{filename}:{reader.line_num}"
    raise AssertionError("fixture must use an identified real input row")


def weeks_fixture(nm, D, assumptions):
    A = assumptions["cautious"]  # actual cautious capture/cost/demand settings
    reference = assumptions["base"]["weeks_per_year"]
    operated = A["weeks_per_year"]
    assert (reference, operated) == (52, 48)
    with (REPLAY / "runs/pin/published_network_routes.csv").open(encoding="utf-8") as f:
        spokes = [r["to"] for r in csv.DictReader(f)
                  if r["scenario"] == "base_sub" and r["variant"] == "Хаб OMS"]
    f = int(A["min_freq_week"])
    fixture = None
    for x in spokes:
        annual = D.get("OMS", x, "cautious")
        L = dict(km=D.km("OMS", x), competitive=D.has_direct("OMS", x),
                 dem=annual / (2 * operated), seg=D.seg("OMS", x, "cautious") / (2 * operated))
        share = nm.leg_share(L, f, A)
        cap = f * A["seats"] * A["lf_max"]
        if not L["competitive"] and share > 0 and annual / (2 * operated) * share < cap:
            fixture = (x, annual, L, share, cap)
            break
    assert fixture is not None
    x, annual, L, q, cap = fixture
    comparisons = []
    for W in (reference, operated):
        Li = dict(L, dem=annual / (2 * W), seg=D.seg("OMS", x, "cautious") / (2 * W))
        qi = nm.leg_share(Li, f, A)
        close(qi, q)
        weekly = min(Li["dem"] * qi, cap)
        comparisons.append(dict(weeks=W, market_trips_week_direction=Li["dem"],
                                sold_trips_week_direction=weekly, capacity_week_direction=cap,
                                sold_trips_year_both_directions=weekly * 2 * W))
    ref_sold, op_sold = [r["sold_trips_year_both_directions"] for r in comparisons]
    close(ref_sold, annual * q)
    close(op_sold, ref_sold)
    cancelled_sold = annual * q * operated / reference
    cancelled_lost = annual * q * (reference - operated) / reference
    close(cancelled_sold + cancelled_lost, ref_sold)
    return dict(pass_check=True, source_sha=PIN, pair=["OMS", x],
                source_locations=["src/network_model.py:215", "src/network_model.py:227",
                                  "src/network_model.py:468", "data/assumptions/network.csv:32",
                                  source_row(nm, "OMS", x, annual, "cautious")],
                demand_method=D.method("OMS", x), demand_scenario="cautious",
                annual_market_trips_both_directions=annual, reference_weeks=reference,
                operating_weeks=operated, freq_week_each_way=f, capture_share=q,
                competitive=False, uncapped=True, reference_vs_operating=comparisons,
                full_rebooking_sold_trips_year=op_sold,
                no_rebooking_sold_trips_year=cancelled_sold,
                no_rebooking_lost_trips_year=cancelled_lost,
                algebra="D/(2W)*q*2W=D*q; cancellation uniform-reference case: D*q*48/52; partial rebooking: D*q*(48+alpha*(52-48))/52, 0<=alpha<=1, subject to seats",
                interpretation="Current formula concentrates annual demand; cancellation example assumes uniform reference-week demand and fixed noncompetitive capture, not observed seasonality/recovery.",
                limits="Fixed frequency algebra on an existing selected OMS leg, not a new network or cautious full-network rerun. Competitive share, frequency feedback and capacity can change totals. Actual alpha/calendar/cost of recovery UNKNOWN.",
                owner_base388_effect_rub=0)


def shortlist_diagnostic(nm, D, assumptions):
    A = assumptions["base_sub"]
    extractor, ast_hashes = direct_parts(nm)
    universe, evaluate, joint, max_h = extractor(D, A, A["demand_scen"], list(D.n.index))
    rows = []
    for B, X, Y, legs in universe:
        hours, cost, gross, _, out = evaluate(B, X, Y, legs)
        f = out[0]["freq"]
        r = joint([(B, X, Y, f, legs)])[0]
        close(hours, r[4]); close(cost, r[5])
        close(r[6], gross - r[10] + r[11])
        rows.append(dict(candidate="/".join((B, X, Y)), base=B, x=X, y=Y, freq_week_each_way=f,
                         hours_week=hours, flight_and_pax_cost_rub_week=cost,
                         gross_ticket_rub_week=gross, foregone_rw_rub_week=r[10],
                         support_rub_week=r[11], migrated_segments_week=r[9],
                         raw_score_rub_block_hour=(gross - cost) / hours,
                         joint_initial_score_rub_block_hour=r[0],
                         joint_initial_contribution_rub_year=(r[6] - r[5]) * A["weeks_per_year"],
                         passes_initial_fleet_hours=hours <= max_h))
    # Stable ordering exactly as pre.sort: no new tie break or different frequency.
    raw = sorted(rows, key=lambda r: -r["raw_score_rub_block_hour"])
    objective = sorted(rows, key=lambda r: -r["joint_initial_score_rub_block_hour"])
    N = int(A["direct_candidates"])
    assert len(rows) >= N
    for rank, r in enumerate(raw, 1):
        r["raw_rank"] = rank
    for rank, r in enumerate(objective, 1):
        r["joint_initial_rank"] = rank
    raw_set = {r["candidate"] for r in raw[:N]}
    joint_set = {r["candidate"] for r in objective[:N]}
    entering = [r for r in objective[:N] if r["candidate"] not in raw_set]
    leaving = [r for r in raw[:N] if r["candidate"] not in joint_set]
    omitted = next(r for r in objective if r["candidate"] not in raw_set)
    # A real inverted pair crossing the cutoff: no fabricated objective values.
    excluded = omitted
    included = max(leaving, key=lambda r: r["raw_score_rub_block_hour"]) if leaving else None
    inversion = None
    if included is not None:
        assert included["raw_rank"] < excluded["raw_rank"]
        assert included["joint_initial_score_rub_block_hour"] < excluded["joint_initial_score_rub_block_hour"]
        inversion = dict(raw_preferred=included, joint_initial_preferred=excluded)
    feasible = [r for r in rows if r["passes_initial_fleet_hours"]]
    assert len(feasible) == len(rows), "report fleet filtering separately if it binds"
    result = dict(pass_check=True, source_sha=PIN, scenario="base_sub", demand_scenario="base",
                  source_locations=["src/network_model.py:314", "src/network_model.py:335",
                                    "src/network_model.py:362", "src/network_model.py:387",
                                    "src/network_model.py:391", "src/network_model.py:404",
                                    "src/network_model.py:406", "src/network_model.py:418",
                                    "data/assumptions/network.csv:41"],
                  scope="All original admissible triangles, one tri_eval and one singleton joint each. Empty sel objective gain/dh equals joint singleton score; no greedy selection or new frequency optimization.",
                  universe_count=len(rows), universe_sha256=rep.sha(json.dumps(
                      [[r["candidate"], r["freq_week_each_way"]] for r in rows]).encode()),
                  extracted_original_functions_ast_sha256=ast_hashes,
                  all_candidates_pass_initial_fleet_cap=True, shortlist_size=N,
                  overlap=len(raw_set & joint_set), raw_only=len(raw_set - joint_set),
                  joint_only=len(joint_set - raw_set), top400_changes=raw_set != joint_set,
                  raw_cutoff=raw[N - 1], joint_cutoff=objective[N - 1],
                  best_omitted_under_joint_initial_objective=omitted,
                  entering_candidates=[r["candidate"] for r in entering],
                  leaving_candidates=[r["candidate"] for r in leaving],
                  cutoff_rank_inversion=inversion,
                  score_identity="joint0 = raw - foregone_rw/h + support/h; initial greedy gain/dh = joint0",
                  owner_base388_effect_rub=0,
                  winner_change="UNKNOWN; no comparable full selector/network run; later joint scores depend on shared markets and sel",
                  global_optimality="UNKNOWN; greedy and forced min_routes remain heuristic")
    return result, raw


def patch_diagnostic(sb):
    path = REPLAY / "patches/001_authoritative_rounded_result.patch"
    subprocess.run(["patch", "--dry-run", "-p1", "-i", str(path)], cwd=sb, check=True, capture_output=True)
    subprocess.run(["patch", "-p1", "-i", str(path)], cwd=sb, check=True, capture_output=True)
    original = rep.git("show", f"{PIN}:src/dashboard_template.html").decode()
    patched = (sb / "src/dashboard_template.html").read_text()
    old = "const res=(r,kk)=>(r.revenue_mln_year-r.subsidy_mln_year)*(1+kk)+r.subsidy_mln_year-r.var_cost_mln_year;"
    new = "const res=(r,kk)=>r.result_mln_year+(r.revenue_mln_year-r.subsidy_mln_year)*kk;"
    assert patched == original.replace(old, new) and original.count(old) == 1
    scripts = re.findall(r"<script\b[^>]*>([\s\S]*?)</script>", patched, flags=re.I)
    parsed = 0
    for script in scripts:
        if script.strip():
            subprocess.run(["node", "--check"], input=script, text=True, check=True, capture_output=True)
            parsed += 1
    # Use the published pin HTML itself, not a prior replay control JSON.
    panel = rep.git("show", f"{PIN}:outputs/redwings_panel.html").decode()
    data, _ = json.JSONDecoder().raw_decode(panel.split("const D = ", 1)[1])
    rows = data["net"]["summary"]
    js = "const rows=" + json.dumps(rows) + ";" + new + """
const orig=(r,k)=>(r.revenue_mln_year-r.subsidy_mln_year)*(1+k)+r.subsidy_mln_year-r.var_cost_mln_year;
const mismatches=rows.filter(r=>orig(r,0)!==r.result_mln_year).map(r=>({scenario:r.scenario,vkey:r.vkey,old:orig(r,0),correct:r.result_mln_year}));
if(rows.some(r=>res(r,0)!==r.result_mln_year))throw Error('zero slider mismatch');
const fs=require('fs'), html=fs.readFileSync(0,'utf8');
const attrs=html.match(/id="ldk"[^>]+/)[0];
const attr=k=>Number(attrs.match(new RegExp(k+'="([^"]+)"'))[1]);
const min=attr('min'),max=attr('max'),step=attr('step');
let checked=0;
for(let v=min;v<=max;v+=step) for(const r of rows){const k=v/100;const expected=(r.revenue_mln_year-r.subsidy_mln_year)*k;
 if(Math.abs((res(r,k)-res(r,0))-expected)>1e-9)throw Error('slope mismatch'); checked++;}
console.log(JSON.stringify({pass_check:true,rows:rows.length,zero_slider_all_rows:true,mismatches_fixed:mismatches.length,mismatches,slider:{min,max,step},slider_evaluations:checked}));
"""
    proc = subprocess.run(["node", "-e", js], input=patched, text=True, check=True, capture_output=True)
    result = json.loads(proc.stdout)
    assert result["rows"] == 24 and result["mismatches_fixed"] == 6
    result.update(source_sha=PIN, source_locations=["src/dashboard_template.html:723", "src/network_model.py:468", "src/network_model.py:469"],
                  patch_sha256=rep.sha(path.read_bytes()), applied_in_disposable_copy=True,
                  patched_inline_script_syntax_checks=parsed, owner_model_effect_rub=0,
                  limits="Executable patch and extracted JS arithmetic only. No DOM/browser acceptance; nonzero slider slope still uses rounded ticket millions, not exact monetary model.")
    return result


def publication_checks():
    rep.verify_source_pin()
    calls = []
    original_git = rep.git
    def fake_git(*args):
        calls.append(list(args))
        assert "HEAD" not in args, "post-audit HEAD is deliberately not the source pin"
        return (PIN + "\n").encode()
    try:
        rep.git = fake_git
        rep.verify_source_pin()
    finally:
        rep.git = original_git
    files = [REPLAY / "reproduce.py", REPLAY / "check_results.py"]
    for p in files:
        tree = ast.parse(p.read_text())
        assert not any(isinstance(n, ast.Constant) and n.value == "HEAD" for n in ast.walk(tree)), p
        assert ".local.json" not in p.read_text()
    return dict(pass_check=True, source_pin=PIN, head_equality_required=False,
                mocked_nonpin_HEAD_guard_calls=calls, protected_owner_bytes_still_required=389,
                private_input_files_required=False,
                inputs="Pinned git objects plus included hash-verified public gzip and protected_owner_files.json; no .local.json, external services or private paths",
                audit_script_sha256={str(p.relative_to(REPLAY)): rep.sha(p.read_bytes()) for p in files + [Path(__file__)]},
                limits="No audit commit created. Nonpin HEAD guard tested and HEAD equality removed; full main replay deliberately not rerun.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    before = rep.protected()
    assert before["pass"] and before["files"] == 389
    publication = publication_checks()
    raw = gzip.decompress((REPLAY / "inputs/tochno_intercity.csv.gz").read_bytes())
    assert rep.sha(raw) == rep.RAW_SHA
    with tempfile.TemporaryDirectory(prefix=".fixture-", dir=HERE) as tmp:
        sb = Path(tmp)
        inputs = rep.prepare(sb, PIN, raw)
        assert not any(p.endswith(".local.json") for p in inputs)
        nm = rep.load_module(sb)
        D, assumptions = nm.Demand(), nm.load_assumptions()
        weeks = weeks_fixture(nm, D, assumptions)
        shortlist, ranks = shortlist_diagnostic(nm, D, assumptions)
        patch = patch_diagnostic(sb)
    after = rep.protected()
    assert after == before
    result = dict(pass_check=True, source_sha=PIN, round="single_final_addressed_round",
                  scope="M06, M09, executable rounding patch and audit publication preflight only; no owner main/optimizer/strategy change",
                  units="Trip demand annual both directions; weekly scores RUB/block-hour; contribution RUB/model year. Modelled future horizon, not observed sales.",
                  input_raw_sha256=rep.sha(raw), protected_before=before, protected_after=after,
                  weeks=weeks, shortlist=shortlist, rounding_patch=patch, publication=publication,
                  residual_unknowns=dict(rebooking_and_cancelled_demand="UNKNOWN", seasonality_and_dated_recovery="UNKNOWN",
                                         changed_shortlist_final_network_or_winner="UNKNOWN", global_optimality="UNKNOWN",
                                         support_entitlement_and_net_yield="UNKNOWN", excluded_costs_fullPnL_cash_and_dispatch="UNKNOWN"),
                  stopped_after_requested_checks=True, further_rounds=0)
    if args.verify:
        saved = json.loads((HERE / "results.json").read_text())
        assert saved == result, "saved results differ from narrow recomputation"
        with (HERE / "candidate_ranks.csv").open(encoding="utf-8") as f:
            saved_ranks = list(csv.DictReader(f))
        assert len(saved_ranks) == len(ranks)
        for saved_row, computed in zip(saved_ranks, ranks):
            assert saved_row == {k: str(v) for k, v in computed.items()}
    else:
        rep.dump(HERE / "results.json", result)
        rep.rows_csv(HERE / "candidate_ranks.csv", ranks)
    print(json.dumps(dict(pass_check=True, source_sha=PIN, protected_files=after["files"],
                          candidate_count=shortlist["universe_count"], top400_overlap=shortlist["overlap"],
                          rounding_fixes=patch["mismatches_fixed"], final_network_winner="UNKNOWN"), ensure_ascii=False))


if __name__ == "__main__":
    main()
