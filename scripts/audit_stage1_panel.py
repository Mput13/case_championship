#!/usr/bin/env python3
"""Bounded, offline stage-1 audit. No downloads, optimizer, Excel, or steps 2–4 rebuild.

Run from any directory: python /absolute/repo/scripts/audit_stage1_panel.py
The default manifest explicitly retains baseline inputs. Final-round research ingestion
requires --config with accepted_csvs entries {path, accepted:true}; CSV columns:
iata,criterion,value,evidence_status,source (FACT / INDIRECT / UNKNOWN).
weights_csv, if set, is an explicit {path, accepted:true}, with column,weight.
Methodology files are explicit accepted entries; rules_json supports criteria_overrides.
Nothing is inferred from source counts, filenames, or findings of other agents.
"""
import argparse
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "context/22_stage1_audit"
BASE = AUDIT / "baseline"
OUT = AUDIT / "model_outputs"
sys.path.insert(0, str(ROOT / "src"))
import longlist_score as ls


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(path):
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError(f"Input must be inside repository: {path}")
    return p


def module(name, source, no_excel=False):
    # All source logic is executed unchanged except removing baseline workbook output.
    tree = ast.parse(source.read_text(encoding="utf-8"))
    if no_excel:
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        stop = next(i for i, n in enumerate(main.body) if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "sources" for t in n.targets))
        main.body = main.body[:stop]
    spec = importlib.util.spec_from_loader(name, loader=None)
    m = importlib.util.module_from_spec(spec)
    m.__file__ = str(source)
    exec(compile(tree, str(source), "exec"), m.__dict__)
    return m


def panel_data(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"const D = (.*?);\n", text)
    if not match:
        raise ValueError(f"No embedded JSON in {path}")
    return json.loads(match.group(1)), text


def js_compute(path, cases, data=None):
    d, text = panel_data(path)
    if data is not None:
        d = data
    functions = text[text.index("const CR=D.criteria;"):text.index("\nconst DSTAT=")]
    formatting = text[text.index("function fmtv("):text.index("const COLS=")]
    # Run actual panel calculation and formatting, without a browser or external scripts.
    js = "const D=" + json.dumps(d) + ";\n" + functions + "\n" + formatting
    js += "\nconst cases=" + json.dumps(cases) + ";\n"
    js += """
const result=cases.map(c=>{MIN=c.min;W={...DEFAULT_W,...(c.weights||{})};
  const q=compute();return {min:MIN,rows:q.rows.map(x=>({iata:x.c.iata,
    score:x.score,share:x.share,lo:x.lo,hi:x.hi,best:x.best,worst:x.worst,unk:x.unk,z:x.z})),
    same:q.same,total:q.total};});
const g=rng(42);const draws=Array.from({length:100},()=>g());
let zeroWeightsRejected=false,negativeWeightsRejected=false;
try{scoreAll(normalize(D.cities),Object.fromEntries(CR.map(w=>[w.key,0])));}catch(e){zeroWeightsRejected=true;}
try{scoreAll(normalize(D.cities),{...DEFAULT_W,[CR[0].key]:-1});}catch(e){negativeWeightsRejected=true;}
console.log(JSON.stringify({result,draws,mro:fmtv(.5,'level',false,'ssj_mro'),zeroWeightsRejected,negativeWeightsRejected}));
"""
    p = subprocess.run(["node"], input=js, cwd=ROOT, text=True, capture_output=True, check=True)
    return json.loads(p.stdout)


def protected_hashes():
    mutable = {"longlist.csv", "criteria.json"}
    paths = list((ROOT / "data/raw").rglob("*"))
    paths += [p for p in (ROOT / "data/processed").iterdir()
              if p.name not in mutable and not p.name.startswith(("longlist_scores", "longlist_sensitivity", "longlist_scenarios"))]
    paths += list((ROOT / "outputs").glob("*.xlsx"))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths) if p.is_file()}


def reproduce_baseline():
    manifest = json.loads((BASE / "manifest.json").read_text())
    for rel, h in manifest["files"].items():
        assert sha(BASE / rel) == h["sha256"], f"Immutable baseline changed: {rel}"
    # Data-only sandbox: links to frozen upstream files, all generated outputs isolated.
    with tempfile.TemporaryDirectory(prefix="rw-stage1-offline-") as temp:
        sandbox = Path(temp)
        (sandbox / "data/processed").mkdir(parents=True)
        (sandbox / "outputs").mkdir()
        for rel in ["data/manual", "data/assumptions", "data/criteria", "context"]:
            (sandbox / rel).parent.mkdir(parents=True, exist_ok=True)
            (sandbox / rel).symlink_to(BASE / rel, target_is_directory=True)
        (sandbox / "src").symlink_to(BASE / "src", target_is_directory=True)
        generated = {"longlist.csv", "criteria.json"}
        for p in (BASE / "data/processed").iterdir():
            if p.name not in generated:
                (sandbox / "data/processed" / p.name).symlink_to(p)
        # Remove score output links; baseline run may only write inside sandbox.
        for p in (sandbox / "data/processed").glob("longlist_*.csv"):
            if p.name.startswith(("longlist_scores", "longlist_sensitivity", "longlist_scenarios")):
                p.unlink()
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            b = module("baseline_longlist", BASE / "src/build_longlist.py", no_excel=True)
            b.ROOT, b.P = sandbox, sandbox / "data/processed"
            b.main()
            bc = module("baseline_criteria", BASE / "src/build_criteria.py")
            bc.ROOT, bc.P, bc.OUT = sandbox, b.P, b.P / "criteria.json"
            bc.main()
            old = module("baseline_score", BASE / "src/longlist_score.py")
            old.P = b.P
            d = json.loads(bc.OUT.read_text())
            ll = pd.read_csv(b.P / "longlist.csv").set_index("iata")
            ll["dist_bases_km"] = ll[["dist_msk_km", "dist_ekb_km"]].min(axis=1)
            scen = pd.read_csv(BASE / "data/assumptions/weight_scenarios.csv")
            for distance in [0, 500]:
                old.run(distance, d["criteria"], d["values"], ll, scen)
            # Full historical builder requires raw files absent from this checkout.
            # Replay only stage 1 against the pinned embedded other-step payload.
            (sandbox / "outputs/redwings_panel.html").write_bytes((BASE / "outputs/redwings_panel.html").read_bytes())
            dash = module("audit_dashboard", ROOT / "src/build_dashboard.py")
            dash.ROOT, dash.P = sandbox, b.P
            dash.stage1_only()
        matches = {}
        for name in ["longlist.csv", "criteria.json"] + [
            f"longlist_{kind}{suffix}.csv" for kind in ["scores", "sensitivity", "scenarios"] for suffix in ["", "_min500"]
        ]:
            a, bpath = b.P / name, BASE / "data/processed" / name
            if name.endswith("json"):
                matches[name] = json.loads(a.read_text()) == json.loads(bpath.read_text())
            else:
                matches[name] = pd.read_csv(a).equals(pd.read_csv(bpath))
            (BASE / "reproduced" / name).write_bytes(a.read_bytes())
        old_d, _ = panel_data(BASE / "outputs/redwings_panel.html")
        new_d, _ = panel_data(sandbox / "outputs/redwings_panel.html")
        new_d["meta"]["built"] = old_d["meta"]["built"]
        matches["panel_stage1_payload_except_build_time"] = new_d == old_d
        (BASE / "reproduced/chain.log").write_text(log.getvalue(), encoding="utf-8")
    assert all(matches.values()), matches
    return matches


def load_inputs(config):
    d = json.loads((ROOT / "data/processed/criteria.json").read_text())
    if config["status"].startswith("BASELINE_ONLY"):
        assert d == json.loads((BASE / "data/processed/criteria.json").read_text()), "Current inputs changed: baseline-only label would be false"
    ll = pd.read_csv(ROOT / "data/processed/longlist.csv").set_index("iata")
    ll["dist_bases_km"] = ll[["dist_msk_km", "dist_ekb_km"]].min(axis=1, skipna=False)
    assert ll.index.is_unique and np.isfinite(ll.dist_bases_km).all()
    rules = json.loads(local(config["rules_json"]).read_text())
    assert rules["primary_min_dist_km"] == 500, "Change primary 500 km only after an explicit accepted decision"
    assert rules["unknown_normalized_interval"] == [0, 1]
    assert rules["random_samples"] == 2000 and rules["seed"] == 42
    keys = {c["key"] for c in d["criteria"]}
    assert len(keys) == len(d["criteria"])
    assert set(rules.get("criteria_overrides", {})) <= keys
    imported, used = [], []
    for entry in config.get("methodology_files", []):
        assert entry["accepted"] is True
        path = local(entry["path"]); used.append({"path":entry["path"], "sha256":sha(path)})
    overridden = set()
    for entry in config["accepted_csvs"]:
        assert entry["accepted"] is True, "Unaccepted research must not enter calculations"
        path = local(entry["path"])
        used.append({"path":entry["path"], "sha256":sha(path)})
        for row in pd.read_csv(path, dtype=str).fillna("").to_dict("records"):
            i, k, status = row["iata"], row["criterion"], row["evidence_status"]
            assert i in ll.index and k in keys and status in {"FACT", "INDIRECT", "UNKNOWN"}
            assert (i, k) not in overridden, f"Conflicting accepted values: {i}/{k}"
            overridden.add((i, k))
            v = None if status == "UNKNOWN" else float(row["value"])
            assert v is None or (math.isfinite(v) and bool(row["source"]))
            d["values"][i][k] = {"v":v, "t":row.get("text") or None,
                                  "s":row["source"], "evidence_status":status}
            imported.append({"iata":i, "criterion":k, "status":status, "path":entry["path"]})
    weights_entry = config.get("weights_csv")
    if weights_entry:
        assert weights_entry["accepted"] is True
        path = local(weights_entry["path"])
        weights = pd.read_csv(path).set_index("column").weight
        assert weights.index.is_unique and set(weights.index) == keys, "Provide all criteria weights explicitly"
        used.append({"path":weights_entry["path"], "sha256":sha(path)})
        for c in d["criteria"]:
            c["weight"] = float(weights[c["key"]])
    for c in d["criteria"]:
        override = rules.get("criteria_overrides", {}).get(c["key"], {})
        assert set(override) <= {"dir", "lo", "hi", "fill"}
        c.update(override)
        assert c["dir"] in {"+", "-"}
        assert math.isfinite(c["weight"]) and c["weight"] >= 0
        if c.get("lo") is not None and c.get("hi") is not None:
            assert c["hi"] > c["lo"]
    assert sum(c["weight"] for c in d["criteria"]) > 0
    scen = pd.read_csv(local(rules["profiles_csv"]))
    assert scen.scenario.is_unique and (scen.multiplier > 0).all()
    return d, ll, rules, scen, imported, used


def calculate(iatas, criteria, vals, ll, weights, profile, distance, scope):
    z, miss = ls.normalize(iatas, criteria, vals)
    assert np.isfinite(z.to_numpy()).all() and ((z >= 0) & (z <= 1)).all().all()
    s = ls.score(z, weights)
    low, high = ls.score(z.mask(miss, 0), weights), ls.score(z.mask(miss, 1), weights)
    assert ((low <= s + 1e-12) & (s <= high + 1e-12)).all()
    # Independent direct weighted sum and bounds checks, outside score().
    direct = np.array([sum(float(z.loc[i,k]) * weights[k] for k in weights.index) / weights.sum() for i in iatas])
    assert np.max(np.abs(s.to_numpy()-direct)) < 1e-12
    hits = ls.random_top3_hits(z, weights)
    assert hits.sum() == min(3, len(iatas)) * 2000
    out = pd.DataFrame({"city":ll.loc[iatas,"city"], "score":s, "score_low":low, "score_high":high,
                        "unknown_weight_share":(miss*weights).sum(axis=1)/weights.sum(),
                        "top3_share_random":hits/2000})
    order = {i:k for k,i in enumerate(iatas)}
    out["rank_best"] = [1 + sum(low[j] > high[i] or (low[j] == high[i] and order[j] < order[i]) for j in iatas if j != i) for i in iatas]
    out["rank_worst"] = [1 + sum(high[j] > low[i] or (high[j] == low[i] and order[j] < order[i]) for j in iatas if j != i) for i in iatas]
    out = out.sort_values("score", ascending=False, kind="stable")
    out.insert(0, "rank", range(1,len(out)+1))
    assert ((out.rank_best <= out["rank"]) & (out["rank"] <= out.rank_worst)).all()
    # Ties use original city order consistently in top3 and interval ranks.
    unknown = []
    for i in iatas:
        for c in criteria:
            k = c["key"]
            if miss.loc[i,k]:
                unknown.append({"scope":scope,"min_dist_km":distance,"profile":profile,"iata":i,
                    "criterion":k,"raw_value":None,"midpoint":z.loc[i,k],"normalized_low":0,
                    "normalized_high":1,"effective_weight":weights[k]/weights.sum(),
                    "score_interval_width":weights[k]/weights.sum(),"evidence_status":"UNKNOWN"})
    return out, z, miss, unknown


def validate_panel(path, criteria, vals, ll):
    d, _ = panel_data(path)
    assert d["criteria"] == criteria and d["values"] == vals
    weights = pd.Series({c["key"]:c["weight"] for c in criteria}, dtype=float)
    # Baseline, several filter thresholds, an existing profile, and a legitimate zero-weight criterion.
    operations = {c["key"]:c["weight"]*(2 if c["group"] == "эксплуатация" else 1) for c in criteria}
    tied = {c["key"]:float(c["key"] == "ssj_ops") for c in criteria}
    cases = [{"min":m} for m in [0,300,500,800]] + [{"min":500,"weights":operations},
             {"min":500,"weights":{"gap_pop":0}}, {"min":500,"weights":tied}]
    result = js_compute(path, cases)
    errors = {"score":0.,"share":0.,"bounds":0.,"normalized":0.,"unknown_weight":0.}
    rows_count = 0
    for case, actual in zip(cases,result["result"]):
        w = weights.copy()
        for k,v in case.get("weights",{}).items(): w[k]=v
        iatas = list(ll.index[ll.dist_bases_km >= case["min"]])
        py, z, miss, _ = calculate(iatas,criteria,vals,ll,w,"validation",case["min"],"validation")
        assert list(py.index) == [x["iata"] for x in actual["rows"]]
        base = set(py.index[:3]); same=total=0
        for k in w.index:
            if not w[k]: continue
            for f in [.5,1.5]:
                ww=w.copy(); ww[k]*=f; total+=1
                same += set(ls.score(z,ww).nlargest(3).index) == base
        assert (same,total) == (actual["same"],actual["total"])
        for x in actual["rows"]:
            i=x["iata"]; q=py.loc[i]; rows_count+=1
            errors["score"]=max(errors["score"],abs(x["score"]-q.score))
            errors["share"]=max(errors["share"],abs(x["share"]-q.top3_share_random))
            errors["bounds"]=max(errors["bounds"],abs(x["lo"]-q.score_low),abs(x["hi"]-q.score_high))
            errors["unknown_weight"]=max(errors["unknown_weight"],abs(x["unk"]-q.unknown_weight_share))
            errors["normalized"]=max(errors["normalized"],max(abs(x["z"][k]-z.loc[i,k]) for k in w.index))
            assert (x["best"],x["worst"]) == (q.rank_best,q.rank_worst)
        if not case.get("weights") and case["min"] in [0,500]:
            suffix="_min500" if case["min"] else ""
            exported=pd.read_csv(ROOT/f"data/processed/longlist_scores{suffix}.csv").set_index("iata")
            expected=py.copy()
            expected[["score","score_low","score_high"]]=expected[["score","score_low","score_high"]].round(3)
            expected[["unknown_weight_share","top3_share_random"]]=expected[["unknown_weight_share","top3_share_random"]].round(2)
            expected=expected.join(z.round(3))[exported.columns]
            pd.testing.assert_frame_equal(expected,exported,check_names=False,check_dtype=False,atol=1e-12,rtol=0)
    g=ls.random_uniform(); assert result["draws"] == [next(g) for _ in range(100)]
    assert result["mro"] == "косвенно"
    assert result["zeroWeightsRejected"] and result["negativeWeightsRejected"]
    assert all(v<1e-12 for v in errors.values()), errors
    return {"cases":len(cases),"city_comparisons":rows_count,"max_abs_errors":errors,
            "rng_first_100_equal":True,"indirect_mro_label":"косвенно","invalid_js_weights_rejected":True,
            "exported_score_csvs_validated":2}


def invariants(criteria, vals, ll):
    w=pd.Series({c["key"]:c["weight"] for c in criteria},dtype=float)
    z,miss=ls.normalize(list(ll.index),criteria,vals)
    for c in criteria:
        k=c["key"]; items=[(vals[i][k]["v"],z.loc[i,k]) for i in ll.index if vals[i][k]["v"] is not None]
        items.sort()
        diff=np.diff([v for _,v in items])
        assert (diff>=-1e-12).all() if c["dir"]=="+" else (diff<=1e-12).all()
    # Missing rows/keys, all-missing, constant, fixed-scale direction, invalid weights.
    test=[{"key":"a","dir":"+","fill":None},{"key":"b","dir":"-","fill":None,"lo":0,"hi":1}]
    tz,tm=ls.normalize(["X","Y"],test,{"X":{"a":{"v":7},"b":{"v":0}},"Y":{"a":{"v":7}}})
    assert tz.a.tolist()==[0,0] and tz.b.tolist()==[1,.5] and tm.b.tolist()==[False,True]
    az,am=ls.normalize(["X","Y"],[test[0]],{})
    assert az.a.tolist()==[.5,.5] and am.a.all()
    for bad in [w*0, w.copy().set_axis(w.index)]:
        if bad.sum():bad.iloc[0]=-1
        try:ls.score(z,bad)
        except ValueError:pass
        else:raise AssertionError("invalid weights accepted")
    assert abs((w/w.sum()).sum()-1)<1e-12
    decorated=copy.deepcopy(vals)
    for row in decorated.values():
        for value in row.values():value["s"]="source count 999; irrelevant annotation"
    zz,mm=ls.normalize(list(ll.index),criteria,decorated)
    assert zz.equals(z) and mm.equals(miss)
    return {"criteria":len(criteria),"positive_weights":int((w>0).sum()),"weight_sum":float(w.sum()),
            "normalized_weight_sum":float((w/w.sum()).sum()),"direction_missing_constant_and_denominator_checks":True,
            "source_annotations_do_not_affect_scores":True,
            "filled_unknown_cells":sum(int(miss[c["key"]].sum()) for c in criteria if c.get("fill") is not None)}


def edge_cases():
    """Execute old and fixed production scoring on explicitly synthetic tiny inputs."""
    old=module("baseline_edge_score",BASE/"src/longlist_score.py")
    ll=pd.DataFrame({"iata":list("ABCDE"),"city":list("ABCDE"),"dist_bases_km":[1000]*5}).set_index("iata")
    crit=[{"key":"fixture","dir":"+","weight":1,"group":"fixture","lo":0,"hi":1}]
    vals={i:{"fixture":{"v":v}} for i,v in zip(ll.index,[1,.8,.50041,.50049,0])}
    scen=pd.DataFrame([{"scenario":"base","label":"synthetic","group":"все","multiplier":1}])
    with tempfile.TemporaryDirectory(prefix="rw-stage1-fixture-") as t:
        p=Path(t); original=ls.P
        try:
            results=[]
            for scorer in [old,ls]:
                scorer.P=p
                with contextlib.redirect_stdout(io.StringIO()):scorer.run(0,crit,vals,ll,scen)
                results.append(pd.read_csv(p/"longlist_scores.csv").iata.head(3).tolist())
        finally:ls.P=original
    assert results==[["A","B","C"],["A","B","D"]],results
    tied=pd.Series([1.,1.,1.],index=list("ABC"))
    assert old.ranks(tied).tolist()==[1,1,1] and ls.ranks(tied).tolist()==[1,2,3]
    result={"synthetic_not_research":True,"round_before_sort_old_top3":results[0],
            "round_after_sort_fixed_top3":results[1],"full_scores":[1,.8,.50041,.50049,0],
            "tie_interval_old":[1,1,1],"tie_interval_fixed":[1,2,3],
            "baseline_top3_changes_from_code_fixes":[]}
    dump(AUDIT/"code_edge_cases.json",result)
    return result


def baseline_panel_differences():
    old=module("baseline_diff_score",BASE/"src/longlist_score.py")
    d=json.loads((BASE/"data/processed/criteria.json").read_text())
    ll=pd.read_csv(BASE/"data/processed/longlist.csv").set_index("iata")
    ll["dist_bases_km"]=ll[["dist_msk_km","dist_ekb_km"]].min(axis=1)
    js=js_compute(BASE/"outputs/redwings_panel.html",[{"min":0},{"min":500}])
    weights=pd.Series({c["key"]:c["weight"] for c in d["criteria"]},dtype=float)
    diffs=[]
    for result in js["result"]:
        distance=result["min"];iatas=list(ll.index[ll.dist_bases_km>=distance])
        z,miss=old.normalize(iatas,d["criteria"],d["values"])
        s=old.score(z,weights)
        rng=np.random.default_rng(42)
        random_weights=rng.uniform(.5,1.5,(2000,len(weights)))*weights.to_numpy()
        scores=z[weights.index].to_numpy()@random_weights.T/random_weights.sum(axis=1)
        hits=np.bincount(np.argsort(-scores,axis=0,kind="stable")[:3].ravel(),minlength=len(z))/2000
        shares=dict(zip(iatas,hits))
        for x in result["rows"]:
            i=x["iata"]
            diffs.append({"min_dist_km":distance,"iata":i,"python_score":s[i],"panel_score":x["score"],
                          "score_delta":x["score"]-s[i],"python_share_exact":shares[i],
                          "panel_share_exact":x["share"],"share_delta_pp":100*(x["share"]-shares[i])})
    pd.DataFrame(diffs).to_csv(AUDIT/"code_panel_differences.csv",index=False)
    # The first-pass changes may alter stability percentages, not actual baseline scores/ranks.
    unchanged=None
    current=json.loads((ROOT/"data/processed/criteria.json").read_text())
    if current==d:
        for suffix in ["","_min500"]:
            a=pd.read_csv(BASE/f"data/processed/longlist_scores{suffix}.csv")
            b=pd.read_csv(ROOT/f"data/processed/longlist_scores{suffix}.csv")
            assert a.drop(columns="top3_share_random").equals(b.drop(columns="top3_share_random"))
        unchanged=True
    return {"max_baseline_share_delta_pp":max(abs(r["share_delta_pp"]) for r in diffs),
            "baseline_score_rank_and_unknown_columns_unchanged":unchanged}


def main():
    if (AUDIT/'accepted_model_inputs.json').exists():
        from finalize_stage1_audit import main as final_main
        final_main()
        return
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config",type=Path,default=AUDIT/"model_inputs.json")
    a=ap.parse_args()
    # Explicit offline guard for all in-process Python modules. No downloader is invoked.
    def offline(*args,**kwargs):raise RuntimeError("Network disabled for stage-1 audit")
    socket.socket.connect=offline
    OUT.mkdir(parents=True,exist_ok=True)
    before=protected_hashes()
    config=json.loads(a.config.read_text()); baseline=reproduce_baseline()
    d,ll,rules,scen,imported,used=load_inputs(config)
    criteria,vals=d["criteria"],d["values"]
    weight=pd.Series({c["key"]:c["weight"] for c in criteria},dtype=float)
    checks=invariants(criteria,vals,ll)
    edges=edge_cases()
    baseline_differences=baseline_panel_differences()
    effective_weights=[]
    for profile in scen.itertuples():
        pw={c["key"]:c["weight"]*(profile.multiplier if profile.group==c["group"] else 1) for c in criteria}
        total=sum(pw.values())
        for c in criteria:effective_weights.append({"profile":profile.scenario,"criterion":c["key"],
            "direction":c["dir"],"weight":pw[c["key"]],"normalized_weight":pw[c["key"]]/total,"denominator":total})
    pd.DataFrame(effective_weights).to_csv(OUT/"effective_weights.csv",index=False)
    summary,unknown,all_rows=[],[],[]
    for distance in rules["min_distances_km"]:
        for scope,excluded in rules["scope_exclusions"].items():
            iatas=[i for i in ll.index if ll.loc[i,"dist_bases_km"]>=distance and i not in excluded]
            assert iatas
            for profile in scen.itertuples():
                w=weight.copy()
                if profile.group!="все":
                    for c in criteria:
                        if c["group"]==profile.group:w[c["key"]]*=profile.multiplier
                scores,z,miss,unk=calculate(iatas,criteria,vals,ll,w,profile.scenario,distance,scope)
                name=f"{scope}_min{distance}_{profile.scenario}"
                scores.to_csv(OUT/f"scores_{name}.csv",index_label="iata")
                z.to_csv(OUT/f"normalized_{name}.csv",index_label="iata")
                unknown.extend(unk)
                frame=scores.reset_index();frame.insert(0,"scope",scope);frame.insert(1,"min_dist_km",distance);frame.insert(2,"profile",profile.scenario)
                all_rows.extend(frame.to_dict("records"))
                summary.append({"scope":scope,"min_dist_km":distance,"profile":profile.scenario,
                    "n":len(iatas),"top3":", ".join(scores.index[:3]),"top3_cities":", ".join(scores.city.head(3)),
                    "weight_sum":float(w.sum()),"input_status":config["status"]})
    pd.DataFrame(summary).to_csv(OUT/"scenario_summary.csv",index=False)
    pd.DataFrame(all_rows).to_csv(OUT/"all_scores.csv",index=False)
    pd.DataFrame(unknown).to_csv(OUT/"unknown_intervals.csv",index=False)
    dump(OUT/"effective_inputs.json",{"status":config["status"],"config":config,"rules":rules,
        "criteria":criteria,"values":vals,"accepted_imports":imported,"accepted_input_hashes":used})
    inventory=[]
    for i in ll.index:
        for c in criteria:
            k=c["key"]; value=vals[i][k]; v=value.get("v"); source=value.get("s") or ""
            status=value.get("evidence_status")
            if not status:
                status="UNKNOWN" if v is None else ("INDIRECT_BASELINE" if
                    "косвенно" in source.lower() or "википед" in source.lower() or (k=="ssj_mro" and v==.5)
                    else "BASELINE_STATED_UNREVIEWED")
            inventory.append({"iata":i,"criterion":k,"value":v,"weight":c["weight"],
                "evidence_status":status,"source":source,"note":"Baseline labels are not independent primary-source validation"})
    pd.DataFrame(inventory).to_csv(OUT/"evidence_inventory.csv",index=False)
    # Panel retains baseline only in first pass; accepted diagnostic overlays must not be silently published.
    live=json.loads((ROOT/"data/processed/criteria.json").read_text())
    panel=validate_panel(ROOT/"outputs/redwings_panel.html",live["criteria"],live["values"],ll)
    assert before==protected_hashes(),"Raw inputs, steps 2–4, or Excel changed"
    old_data,_=panel_data(BASE/"outputs/redwings_panel.html");new_data,_=panel_data(ROOT/"outputs/redwings_panel.html")
    nonstage=[k for k in old_data if k not in {"criteria","values","weights","meta","cities"}]
    assert all(old_data[k]==new_data[k] for k in nonstage),"Other panel steps changed"
    dump(AUDIT/"validation.json",{"status":"PASS","input_status":config["status"],"source_commit":config["source_commit"],
        "offline":True,"baseline_reproduction":baseline,"invariants":checks,"panel":panel,
        "original_panel_differences":baseline_differences,
        "edge_cases":edges,"full_dashboard_builder_status":"NOT_REPRODUCIBLE_OFFLINE_MISSING_RAW_OURAIRPORTS",
        "dashboard_mode":"stage1_only_preserving_pinned_other_steps",
        "scenario_count":len(summary),"protected_files":before,"nonstage_panel_payload_unchanged":True,
        "accepted_import_count":len(imported),"python":sys.version,"pandas":pd.__version__,"numpy":np.__version__})
    validation=json.loads((AUDIT/"validation.json").read_text())
    validation["implementation_sha256"]={str(p.relative_to(ROOT)):sha(p) for p in
        [ROOT/"src/longlist_score.py",ROOT/"src/build_longlist.py",ROOT/"src/build_dashboard.py",
         ROOT/"src/dashboard_template.html",ROOT/"scripts/audit_stage1_panel.py"]}
    validation["configuration_sha256"]={str(a.config.resolve().relative_to(ROOT)):sha(a.config),
        config["rules_json"]:sha(local(config["rules_json"])),rules["profiles_csv"]:sha(local(rules["profiles_csv"]))}
    dump(AUDIT/"validation.json",validation)
    print(json.dumps({"status":"PASS","input_status":config["status"],"scenarios":len(summary),
                      "primary":[s for s in summary if s["scope"]=="samara_included" and s["min_dist_km"]==500 and s["profile"]=="base"],
                      "panel":panel},ensure_ascii=False))


if __name__=="__main__":
    main()
