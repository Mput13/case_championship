"""Stdlib independent review. Reads git-show snapshot, never imports author code."""
import copy
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
P = HERE / ".frozen"
TOL = 2e-12
RESULT = {}

def js(path):
    return json.loads((P / path).read_text())

def rows(path):
    with (P / path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def near(a, b, tol=TOL):
    assert abs(float(a) - float(b)) <= tol, (a, b)

def dot(v, w):
    return math.fsum(v[k] * w[k] for k in w) / math.fsum(w.values())

def ranking(v, w):
    s = {i: dot(x, w) for i, x in v.items()}
    return sorted(s, key=lambda i: -s[i]), s

def hkm(a, b):
    a, b = [tuple(map(math.radians, x)) for x in (a, b)]
    x = math.sin((b[0]-a[0])/2)**2 + math.cos(a[0])*math.cos(b[0])*math.sin((b[1]-a[1])/2)**2
    return 2 * 6371 * math.atan2(math.sqrt(x), math.sqrt(max(0, 1-x)))

def util(v, c):
    if v is None or c.get("constant") or c["hi"] <= c["lo"]:
        return .5
    u = max(0, min(1, (v-c["lo"])/(c["hi"]-c["lo"])))
    return u if c["dir"] == "+" else 1-u

def verify_hashes():
    m = js("source_manifest.json")
    source = []
    for role, meta in m["commits"].items():
        author = subprocess.check_output(["git", "show", "-s", "--format=%an", meta["sha"]]).decode().strip()
        assert author == meta["author"], (role, author)
    for r in m["inputs"]:
        raw = (P/r["local"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == r["sha256"]
        if r.get("commit"):
            original = subprocess.check_output(["git", "show", r["commit"]+":"+r["path"]])
            assert original == raw
        source.append({"source_commit": r.get("commit"), "source_path": r["path"],
                       "snapshot_path": r["local"], "sha256": r["sha256"],
                       "level": r["level"], "git_object_matched": bool(r.get("commit"))})
    c = m["coordinates"]
    raw = subprocess.check_output(["git", "show", c["source_commit"]+":"+c["source_path"]])
    assert hashlib.sha256(raw).hexdigest() == c["source_sha256"]
    original = {r["iata_code"]: r for r in csv.DictReader(raw.decode().splitlines()) if r["iata_code"]}
    for r in rows(c["path"]):
        near(r["lat"], original[r["iata"]]["latitude_deg"])
        near(r["lon"], original[r["iata"]]["longitude_deg"])
    out = js("output_manifest.json")["files"]
    for path, rec in out.items():
        expected = rec["sha256"] if isinstance(rec, dict) else rec
        assert hashlib.sha256((P/path).read_bytes()).hexdigest() == expected, path
    (HERE/"verified_source_manifest.json").write_text(json.dumps({"reviewed_commit": "82dffa795146ccc575db1bb45ba9391af44def00", "commits_author_verified": m["commits"], "attribution_scope": "Git author verified; human attribution from explicit user clarification, not inferred from Git", "inputs": source, "coordinates": c, "output_hashes_verified": len(out)}, ensure_ascii=False, indent=2)+"\n")
    RESULT["hashes"] = {"inputs": len(source), "git_objects_matched": sum(r["git_object_matched"] for r in source), "coordinates_rows": 25, "outputs": len(out)}

def stage_values(d, ids, field="u"):
    return {i: {c["key"]: d["values"][i][c["key"]][field] for c in d["criteria"]} for i in ids}

def check_stage(d, ids, w, saved):
    order, scores = ranking(stage_values(d, ids), w)
    low = {i: dot(v,w) for i,v in stage_values(d, ids, "u_low").items()}
    high = {i: dot(v,w) for i,v in stage_values(d, ids, "u_high").items()}
    assert order == [r["iata"] for r in saved]
    for r in saved:
        i = r["iata"]
        for field, key in [("u", "score"), ("u_low", "score_low"), ("u_high", "score_high")]:
            near(dot(stage_values(d, [i], field)[i], w), r[key])
        for field, key in [("unknown", "unknown_weight_share"), ("indirect", "indirect_weight_share")]:
            near(dot(stage_values(d, [i], field)[i], w), r[key])
        uncertain = {k: d["values"][i][k]["u_high"] > d["values"][i][k]["u_low"] for k in w}
        near(dot(uncertain, w), r["uncertain_weight_share"])
        for key, expected in {
            "central_rank_min": 1+sum(scores[j]>scores[i]+1e-12 for j in ids if j!=i),
            "central_rank_max": 1+sum(scores[j]>=scores[i]-1e-12 for j in ids if j!=i),
            "rank_best": 1+sum(low[j]>high[i]+1e-12 for j in ids if j!=i),
            "rank_worst_inclusive": 1+sum(high[j]>=low[i]-1e-12 for j in ids if j!=i),
            "author_rank_best": 1+sum(low[j]>high[i]+1e-12 for j in ids if j!=i),
            "author_rank_worst": 1+sum(high[j]>low[i]+1e-12 for j in ids if j!=i),
        }.items():
            if key in r:
                assert int(r[key]) == expected, (i, key, r[key], expected)
        if "rank_worst_inclusive" not in r:
            assert int(r["rank_worst"]) == 1+sum(high[j]>low[i]+1e-12 for j in ids if j!=i)
    return order, scores

def modern_checks():
    d = js("inputs/tsiri_stage22/data/processed/criteria.json")
    ll = rows("inputs/tsiri_stage22/data/processed/longlist.csv")
    ids = [r["iata"] for r in ll]
    dist = {r["iata"]: min(float(r["dist_msk_km"]), float(r["dist_ekb_km"])) for r in ll}
    profiles = {r["id"]: r["weights"] for r in d["stage1"]["profiles"]}
    cs = {c["key"]: c for c in d["criteria"]}
    for w in profiles.values():
        near(sum(w.values()), 100)
        assert min(w.values()) >= 0
    for r in rows("profiles.csv"):
        near(r["weight"], profiles[r["profile"]][r["criterion"]])
    for r in rows("inputs/tsiri_stage22/context/22_stage1_audit/recommended_weights.csv"):
        c = cs[r["column"]]
        near(c["weight"], r["weight"])
        assert c["dir"] == r["direction"]
        near(c["lo"], r["lo"])
        near(c["hi"], r["hi"])
    for i in ids:
        for k, c in cs.items():
            x = d["values"][i][k]
            u = util(x["v"], c)
            if k == "gap_pop":
                u = (util(x["raw_low"], c)+util(x["raw_high"], c))/2
            if k == "pax_2025" and x["v"] is None and x.get("raw_low") is not None:
                u = util(x["approximate_derived"], c) if i == "REN" else (util(x["raw_low"], c)+1)/2
            near(u, x["u"])
            assert 0 <= x["u_low"] <= x["u"] <= x["u_high"] <= 1
    groups = {}
    for r in rows("inputs/tsiri_stage22/context/22_stage1_audit/final_scores.csv"):
        groups.setdefault((r["stress"], int(r["min_dist_km"]), r["mode"], r["profile"]), []).append(r)
    for (stress, radius, mode, profile), saved in groups.items():
        dd = copy.deepcopy(d)
        for i, v in dd["values"].items():
            if stress == "common_neutral":
                for k in ("competitor_hub", "ssj_mro", "transfer_zone"):
                    v[k].update(u=.5, u_low=.5, u_high=.5)
            if stress == "intro_only":
                u = util(d["stage1"]["intro_only"][i], cs["last365_days"])
                v["last365_days"].update(u=u, u_low=u, u_high=u)
            if stress in ("transfer_low", "transfer_high"):
                v["transfer_demand_base"]["u"] = int(stress == "transfer_high")
            if i == "REN" and stress == "ren_lower":
                v["pax_2025"]["u"] = util(951000, cs["pax_2025"])
            if i == "REN" and stress == "ren_extreme":
                v["pax_2025"].update(u=1, u_high=1)
        keep = [i for i in ids if dist[i] >= radius and not (mode == "strict_new" and i in d["stage1"]["strict_excluded"])]
        check_stage(dd, keep, profiles[profile], saved)
    coordinates = {r["iata"]: (float(r["lat"]), float(r["lon"])) for r in rows("inputs/airport_coordinates.csv")}
    refs = {"historical_SVO_DME_VKO_SVX": ["SVO", "DME", "VKO", "SVX"], "case_ZIA_SVX": ["ZIA", "SVX"]}
    controlled = {}
    for r in rows("controlled_scores.csv"):
        controlled.setdefault(r["scenario"], []).append(r)
    summaries = []
    for name, saved in controlled.items():
        ref, rad, mode, profile = name.split("|")
        keep = [i for i in ids if min(hkm(coordinates[i], coordinates[b]) for b in refs[ref]) >= int(rad) and not (mode == "strict_new" and i in d["stage1"]["strict_excluded"])]
        order, _ = check_stage(d, keep, profiles[profile], saved)
        summaries.append({"scenario": name, "n": len(keep), "top3": order[:3]})
    factors = rows("one_factor_deltas.csv")
    for r in factors:
        before, after = controlled[r["before"]], controlled[r["after"]]
        aa, bb = ({x["iata"]: float(x["score"]) for x in rr} for rr in (before, after))
        common = set(aa)&set(bb)
        near(max(abs(aa[i]-bb[i]) for i in common), r["common_score_max_delta"])
        assert set(filter(None, r["excluded"].split(" / "))) == set(aa)-set(bb)
        assert set(filter(None, r["added"].split(" / "))) == set(bb)-set(aa)
        assert sum(x!=y for x,y in zip(r["before"].split("|"),r["after"].split("|"))) == 1
    # Full LOO and family-drop summaries, independently renormalizing retained weights.
    loo_changed = loo_count = family_count = 0
    for r in rows("robustness.csv"):
        rad, profile, kind, drop = r["scenario"].split("|")
        keep = [i for i in ids if dist[i] >= int(rad)]
        omitted = ["gap_pop", "pax_2025", "catchment_pop_2025", "transfer_demand_base", "wage_2024"] if kind == "omit_proxy_family" else [drop]
        w = {k: v for k, v in profiles[profile].items() if k not in omitted}
        order, score = ranking(stage_values(d, keep), w)
        assert " / ".join(order[:3]) == r["top3"]
        for n in range(3):
            near(score[order[n]], r["score"+str(n+1)])
        base, _ = ranking(stage_values(d, keep), profiles[profile])
        unchanged = set(base[:3]) == set(order[:3])
        assert str(unchanged) == r["same_top3"]
        loo_changed += kind == "leave_one_out" and not unchanged
        loo_count += kind == "leave_one_out"
        family_count += kind == "omit_proxy_family"
    weather_error = 0
    for w in profiles.values():
        order, s = ranking(stage_values(d, ids), w)
        nw = {k: v for k, v in w.items() if k != "bad_weather_days"}
        order2, s2 = ranking(stage_values(d, ids), nw)
        assert order == order2
        a = w["bad_weather_days"]/sum(w.values())
        for i in ids:
            near(d["values"][i]["bad_weather_days"]["u"], .5)
            assert d["values"][i]["bad_weather_days"]["unknown"]
            weather_error = max(weather_error, abs(s2[i]-(s[i]-a/2)/(1-a)))
    w = profiles["balanced"]
    _, scores = ranking(stage_values(d, ids), w)
    gap = scores["BAX"]-scores["KUF"]
    contributions = {}
    for r in rows("bax_kuf_gap.csv"):
        k = r["criterion"]
        v = w[k]*(d["values"]["BAX"][k]["u"]-d["values"]["KUF"][k]["u"])/sum(w.values())
        near(v, r["BAX_minus_KUF_contribution"])
        contributions[k] = v
    near(gap, sum(contributions.values()))
    corrected = {}
    for r in rows("corrected_scores.csv"):
        if r["origin_model"] == "tsiri_stage22":
            corrected.setdefault(r["scenario"], []).append(r)
    # The base corrected projection is checked against independent interval positions.
    corrected_rows = 0
    for scenario, saved in corrected.items():
        if scenario.startswith("base|"):
            _, rad, mode, profile = scenario.split("|")
            keep = [i for i in ids if dist[i]>=int(rad) and not(mode=="strict_new" and i in d["stage1"]["strict_excluded"])]
            check_stage(d, keep, profiles[profile], saved)
            corrected_rows += len(saved)
    RESULT["modern"] = {"accepted_cells": len(ids)*len(cs), "stage22_configs": len(groups), "stage22_rows": sum(map(len, groups.values())), "controlled_configs": len(controlled), "controlled_rows": sum(map(len, controlled.values())), "one_factor_pairs": len(factors), "corrected_base_rows": corrected_rows, "loo_configs": loo_count, "loo_top3_set_changes": loo_changed, "family_drops": family_count, "weather_max_identity_error": weather_error, "BAX_minus_KUF": gap, "one_BAX_day_delta": -.22/218, "BAX_minus_KUF_after_one_scenario_day": gap-.22/218, "gap_contributions": contributions, "controlled": summaries}
    return d, ids, dist

def legacy_checks():
    out = []
    for role in ("nastya", "front_historical"):
        d = js(f"inputs/{role}/data/processed/criteria.json")
        ll = rows(f"inputs/{role}/data/processed/longlist.csv")
        for radius in (0, 500):
            ids = [r["iata"] for r in ll if min(float(r["dist_msk_km"]), float(r["dist_ekb_km"])) >= radius]
            v, lo, hi = ({i: {} for i in ids} for _ in range(3))
            w = {c["key"]: c["weight"] for c in d["criteria"]}
            for c in d["criteria"]:
                k = c["key"]
                filled = {i: d["values"][i][k]["v"] if d["values"][i][k]["v"] is not None else c.get("fill") for i in ids}
                observed = [x for x in filled.values() if x is not None]
                lower = c.get("lo") if role == "nastya" else None
                upper = c.get("hi") if role == "nastya" else None
                lower = min(observed, default=0) if lower is None else lower
                upper = max(observed, default=0) if upper is None else upper
                for i, x in filled.items():
                    u = .5 if x is None else (x-lower)/(upper-lower) if upper > lower else 0
                    if x is not None and c["dir"] == "-":
                        u = 1-u
                    v[i][k] = u
                    missing = d["values"][i][k]["v"] is None
                    lo[i][k], hi[i][k] = (0, 1) if missing else (u, u)
            order, s = ranking(v, w)
            saved = rows(f"inputs/{role}/data/processed/longlist_scores{'_min500' if radius else ''}.csv")
            err = max(abs(s[r["iata"]]-float(r["score"])) for r in saved)
            assert order[:3] == [r["iata"] for r in saved[:3]]
            if role == "nastya" or radius == 0:
                assert err <= .0005+TOL
            else:
                assert err > .0005
            if role == "nastya":
                for r in saved:
                    near(round(dot(lo[r["iata"]], w), 3), r["score_low"])
                    near(round(dot(hi[r["iata"]], w), 3), r["score_high"])
            out.append({"role": role, "radius": radius, "n": len(ids), "weight_sum": sum(w.values()), "active": sum(x>0 for x in w.values()), "top3": order[:3], "top3_scores": [s[i] for i in order[:3]], "max_rounded_export_delta": err})
    RESULT["legacy"] = out

def historical_checks():
    pref = "inputs/tsiri_historical/context/11_practical_screening/"
    d = js(pref+"inputs.json")
    xy = {r["iata"]: (r["lat"], r["lon"]) for r in js(pref+"coordinates.json")}
    g = d["geography"]
    pairs = list(itertools.product(g["north"], g["south"])) + list(itertools.product(g["east"], g["east_south"]))
    vals = {}
    for city in d["cities"]:
        i = city["iata"]
        coverage = []
        for a, b in pairs:
            x, y = hkm(xy[a], xy[i]), hkm(xy[i], xy[b])
            detour = (x+y)/hkm(xy[a], xy[b])
            coverage.append(max(0, min(1, (g["detour_ceiling"]-detour)/(g["detour_ceiling"]-1))) if g["min_leg_km"] <= x <= g["max_leg_km"] and g["min_leg_km"] <= y <= g["max_leg_km"] else 0)
        vals[i] = {"market": max(0, min(100, (city["population_thousands"]-500)/10)), "competition": sum(city["competition_interval"])/2, "technical": sum(city["technical_interval"])/2, "basing": sum(city["basing_interval"])/2, "geography": 75*sum(coverage)/len(coverage)+25*min(1, min(hkm(xy[i], xy[b]) for b in ("DME", "SVX"))/g["distance_scale_km"])}
    groups = {}
    for r in rows(pref+"ranking.csv"):
        groups.setdefault((r["weights"], r["scope"]), []).append(r)
    for (profile, scope), saved in groups.items():
        keep = [c["iata"] for c in d["cities"] if scope == "all" or c["new_node"]]
        order, s = ranking({i: vals[i] for i in keep}, d["weights"][profile])
        assert order == [r["iata"] for r in saved]
        for r in saved:
            near(round(s[r["iata"]], 4), r["score"])
    updates = {}
    for r in rows("inputs/tsiri_historical/context/12_network_economics/city_ranking_update_full.csv"):
        updates.setdefault((r["case"], r["weights"]), []).append(r)
    rounded = {r["iata"]: {k: float(r[k]) for k in d["weights"]["base"]} for r in groups["base", "new_node"]}
    for (case, profile), saved in updates.items():
        v, w = copy.deepcopy(rounded), d["weights"][profile].copy()
        v["UFA"]["technical"] = 75
        if case.startswith("all_technical") or case.startswith("equal_technical"):
            for x in v.values():
                x["technical"] = 100
        if case == "equal_technical_UFA_basing_80_scenario":
            v["UFA"]["basing"] = 80
        if case == "omit_technical_weight":
            w["technical"] = 0
        order, s = ranking(v, w)
        assert order == [r["iata"] for r in saved]
        for r in saved:
            near(s[r["iata"]], r["score"])
    RESULT["historical"] = {"stage11_configs": len(groups), "stage12_configs": len(updates), "new_node_n": len(rounded), "base_top3": [r["iata"] for r in groups["base", "new_node"][:3]], "pairs": len(pairs), "market": "city_proper_not_catchment", "stage12_input_precision": "rounded_stage11_components"}

def tie_checks():
    # Exhaustive endpoint rankings including arbitrary tie permutations for tiny boxes.
    for box in [[(.5,.5)]*3, [(0,.5),(.5,1),(.5,.5)], [(0,1),(.2,.4),(.8,1)]]:
        positions = [set() for _ in box]
        for values in itertools.product(*[sorted(set(x)) for x in box]):
            for perm in itertools.permutations(range(len(box))):
                if all(values[perm[j]] >= values[perm[j+1]] for j in range(len(box)-1)):
                    for n, i in enumerate(perm, 1):
                        positions[i].add(n)
        for i, (low, high) in enumerate(box):
            best = 1+sum(l>high for j,(l,h) in enumerate(box) if j!=i)
            worst = 1+sum(h>=low for j,(l,h) in enumerate(box) if j!=i)
            assert (best, worst) == (min(positions[i]), max(positions[i]))
    n = 20
    fixture = js("tie_fixture.json")
    assert fixture["n"] == n
    assert len(fixture["rows"]) == n
    for r in fixture["rows"]:
        assert [r["central_rank_min"],r["central_rank_max"]] == [1,n]
        assert [r["rank_best"],r["rank_worst_inclusive"]] == [1,n]
        assert [r["author_rank_best"],r["author_rank_worst"]] == [1,1]
    RESULT["ties"] = {"fixed_equal_n": n, "author_strict_bounds": [1,1], "tie_inclusive_position_bounds": [1,n], "small_boxes_exhaustively_verified": 3, "scope": "independently_variable_interval_box_and_arbitrary_tie_positions"}

def main():
    verify_hashes()
    modern_checks()
    legacy_checks()
    historical_checks()
    tie_checks()
    (HERE/"independent_results.json").write_text(json.dumps({"status": "PASS_WITH_KNOWN_HISTORICAL_MISMATCH", **RESULT}, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({k: {kk: vv for kk,vv in v.items() if kk != "controlled"} if isinstance(v,dict) else v for k,v in RESULT.items()}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
