"""Stage-1 scoring with frozen anchors, neutral UNKNOWN and persistent bounds.

Accepted round-2 snapshot: context/22_stage1_audit/accepted_model_inputs.json.
Full offline reproduction: python scripts/finalize_stage1_audit.py.
With accepted criteria, this CLI exports all five profiles and both eligibility modes.
Random-weight top-3 frequencies are diagnostics, never outcome probabilities.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
PAR = pd.read_csv(ROOT / "data/assumptions/longlist_params.csv").set_index("parameter").value


def utility_tables(iatas, crit, vals):
    """Fixed anchors and persistent accepted utility bounds; legacy inputs still supported."""
    z, low, high, unknown, indirect = (pd.DataFrame(index=iatas) for _ in range(5))
    for c in crit:
        k = c['key']
        raw = [vals.get(i, {}).get(k, {}).get('v') for i in iatas]
        observed = [v for v in raw if v is not None and np.isfinite(v)]
        lo = c.get('lo') if c.get('lo') is not None else min(observed, default=0)
        hi = c.get('hi') if c.get('hi') is not None else max(observed, default=0)
        for i, v in zip(iatas, raw):
            x = vals.get(i, {}).get(k, {})
            if 'u' in x:
                u, a, b = x['u'], x['u_low'], x['u_high']
            else:
                u = .5 if v is None or c.get('constant') or hi <= lo else max(0., min(1., (v-lo)/(hi-lo)))
                if v is not None and not c.get('constant') and hi > lo and c['dir'] == '-': u = 1-u
                a, b = (0., 1.) if v is None else (u, u)
            z.loc[i,k], low.loc[i,k], high.loc[i,k] = u, a, b
            unknown.loc[i,k] = x.get('unknown', v is None)
            indirect.loc[i,k] = x.get('indirect', False)
    return z, low, high, unknown.astype(bool), indirect.astype(bool)


def normalize(iatas, crit, vals):
    z, low, high, unknown, indirect = utility_tables(iatas, crit, vals)
    return z, (high > low)


def score(z, w):
    if set(z.columns) != set(w.index) or not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("Нужны конечные неотрицательные веса всех критериев с положительной суммой")
    if not np.isfinite(z.to_numpy()).all():
        raise ValueError("Нормированные оценки должны быть конечными")
    return (z * w).sum(axis=1) / w.sum()


def random_uniform(seed=42):
    """Mulberry32, побитно как rng() в панели; порядок критериев тоже одинаковый."""
    mask = 0xFFFFFFFF
    while True:
        seed = (seed + 0x6D2B79F5) & mask
        t = ((seed ^ (seed >> 15)) * (1 | seed)) & mask
        t = (t ^ ((t + (((t ^ (t >> 7)) * (61 | t)) & mask)) & mask)) & mask
        yield ((t ^ (t >> 14)) & mask) / 4294967296


def random_top3_hits(z, w, samples=2000, seed=42):
    """Те же 2000 наборов и стабильное разрешение равенств, что в JS."""
    draws = random_uniform(seed)
    factors = np.array([[0.5 + next(draws) for _ in w] for _ in range(samples)])
    weights = factors * w.to_numpy()
    scores = z[w.index].to_numpy() @ weights.T / weights.sum(axis=1)
    top = np.argsort(-scores, axis=0, kind="stable")[:3]
    return pd.Series(np.bincount(top.ravel(), minlength=len(z)), index=z.index)


def ranks(s):
    # При точном равенстве используем исходный порядок городов, как top3() в JS.
    return s.rank(ascending=False, method="first").astype(int)


def run(min_dist, crit, vals, ll, scen):
    iatas = [i for i in ll.index if ll.loc[i, "dist_bases_km"] >= min_dist]
    if min_dist:
        print(f"Фильтр: ближе {min_dist:.0f} км к базам — убраны {', '.join(ll.loc[~ll.index.isin(iatas), 'city'])}")
    z, low, high, unknown, indirect = utility_tables(iatas, crit, vals)
    miss = high > low
    w = pd.Series({c["key"]: c["weight"] for c in crit}, dtype=float)
    s = score(z, w)
    lo_s, hi_s = score(low, w), score(high, w)
    best_rank = {i:1+sum(lo_s[j] > hi_s[i] for j in iatas if j != i) for i in iatas}
    worst_rank = {i:1+sum(hi_s[j] > lo_s[i] for j in iatas if j != i) for i in iatas}
    unk = (unknown * w).sum(axis=1) / (w.sum() or 1)
    base = set(s.nlargest(3).index)

    one = []
    for k in w.index:
        if w[k] == 0:
            continue
        for f in (0.5, 1.5):
            ww = w.copy()
            ww[k] *= f
            t = set(score(z, ww).nlargest(3).index)
            one.append({"weight": k, "factor": f, "top3": ", ".join(sorted(t)), "same_as_base": t == base})
    hits = random_top3_hits(z, w)
    group = {c["key"]: c.get("group", "прочее") for c in crit}
    sc_rows = []
    for r in scen.itertuples():
        ww = w.copy()
        if r.group != "все":
            ww[[k for k in w.index if group[k] == r.group]] *= r.multiplier
        ss = score(z, ww)
        top = list(ss.nlargest(3).index)
        sc_rows.append({"scenario": r.scenario, "label": r.label, "top3": ", ".join(ll.loc[top, "city"]),
                        "top3_iata": ", ".join(top), "same_as_base": set(top) == base})
    # Сначала сортируем по полному баллу, затем округляем только экспорт.
    out = pd.DataFrame({"city": ll.loc[iatas, "city"], "score": s,
                        "score_low": lo_s.round(3), "score_high": hi_s.round(3),
                        "rank_best": pd.Series(best_rank), "rank_worst": pd.Series(worst_rank),
                        "unknown_weight_share": unk.round(2),
                        "indirect_weight_share": ((indirect*w).sum(axis=1)/w.sum()).round(2),
                        "uncertain_weight_share": ((miss*w).sum(axis=1)/w.sum()).round(2),
                        "top3_share_random": (hits / 2000).round(2)})
    out = out.join(z.round(3)).sort_values("score", ascending=False, kind="stable")
    out["score"] = out["score"].round(3)
    out.insert(0, "rank", range(1, len(out) + 1))
    sfx = f"_min{int(min_dist)}" if min_dist else ""
    out.to_csv(P / f"longlist_scores{sfx}.csv", index_label="iata", encoding="utf-8", lineterminator="\r\n")
    pd.DataFrame(one).to_csv(P / f"longlist_sensitivity{sfx}.csv", index=False, encoding="utf-8", lineterminator="\r\n")
    pd.DataFrame(sc_rows).to_csv(P / f"longlist_scenarios{sfx}.csv", index=False, encoding="utf-8", lineterminator="\r\n")
    pd.set_option("display.width", 200)
    print(out[["rank", "city", "score", "score_low", "score_high", "rank_best", "rank_worst",
               "unknown_weight_share", "top3_share_random"]].to_string())
    same = sum(r["same_as_base"] for r in one)
    print(f"\nТоп-3: {', '.join(out.city.head(3))}")
    print(f"Один вес ×0,5 или ×1,5: топ-3 тот же в {same} из {len(one)} вариантов")
    for r in sc_rows:
        print(f"  {r['label']}: {r['top3']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-dist", type=float, default=None)
    a = ap.parse_args()
    data = json.loads((P / "criteria.json").read_text(encoding="utf-8"))
    ll = pd.read_csv(P / "longlist.csv").set_index("iata")
    ll["dist_bases_km"] = ll[["dist_msk_km", "dist_ekb_km"]].min(axis=1)
    if 'stage1' in data:
        import sys
        sys.path.insert(0, str(ROOT/'scripts'))
        from finalize_stage1_audit import calculate, write_csv
        dists = [a.min_dist] if a.min_dist is not None else [0,500]
        for distance in dists:
            rows=[]
            for mode in ['expansion_allowed','strict_new']:
                for p in data['stage1']['profiles']:
                    out,z=calculate(data,ll,p['weights'],distance,mode)
                    rows.append(dict(profile=p['id'],mode=mode,min_dist_km=distance,top3=' / '.join(out.index[:3])))
                    if mode=='expansion_allowed' and p['id']=='balanced':
                        suffix=f'_min{int(distance)}' if distance else ''
                        out.join(z).to_csv(P/f'longlist_scores{suffix}.csv',index_label='iata')
            suffix=f'_min{int(distance)}' if distance else ''
            write_csv(P/f'longlist_scenarios{suffix}.csv',rows)
        return
    scen = pd.read_csv(ROOT / "data/assumptions/weight_scenarios.csv")
    dists = [a.min_dist] if a.min_dist is not None else [0.0, float(PAR["min_dist_bases_km"])]
    for d in dists:
        run(d, data["criteria"], data["values"], ll, scen)
        print()


if __name__ == "__main__":
    main()
