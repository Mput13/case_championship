"""Баллы лонглиста, топ-3, диапазон из-за пропусков и проверка устойчивости к весам.

Вход: data/processed/criteria.json (src/build_criteria.py) — все критерии, основные и подключаемые;
      data/processed/longlist.csv — названия городов и расстояния для фильтра;
      data/assumptions/longlist_params.csv (min_dist_bases_km), data/assumptions/weight_scenarios.csv.
Метод (тот же, что в панели):
  1. Каждый критерий переводим в шкалу 0–1 (min–max по городам в фильтре или фиксированная шкала lo–hi;
     «−» — переворачиваем). Пропуск: если задан fill — подставляем его до нормировки; иначе 0,5.
  2. Балл = сумма (вес × оценка) / сумма весов.
  3. Диапазон из-за пропусков (идея коллег, context/15_team_update/model/city_scores.csv):
     нижний балл — все неизвестные значения города худшие (0), верхний — лучшие (1).
     Лучшее возможное место: у города неизвестное лучшее, у остальных худшее; худшее место — наоборот.
     Доля веса на пропусках показывает, насколько балл держится на незнании.
  4. Устойчивость: (а) каждый вес по очереди ×0,5 и ×1,5; (б) 2000 случайных наборов весов (×0,5…1,5);
     (в) сценарии весов по группам критериев (рынок, география, эксплуатация, конкуренция).
Выход: data/processed/longlist_scores.csv и longlist_scores_min<N>.csv, longlist_sensitivity[_minN].csv,
       longlist_scenarios[_minN].csv
Запуск: python src/longlist_score.py               (оба варианта: все города и без ближних к базам)
        python src/longlist_score.py --min-dist 0  (только один вариант)
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
PAR = pd.read_csv(ROOT / "data/assumptions/longlist_params.csv").set_index("parameter").value


def normalize(iatas, crit, vals):
    """z — оценка 0–1 с подстановкой пропусков; miss — где значение неизвестно (и не задано fill)."""
    z, miss = pd.DataFrame(index=iatas), pd.DataFrame(index=iatas)
    for c in crit:
        x = pd.Series({i: vals[i][c["key"]]["v"] for i in iatas}, dtype=float)
        miss[c["key"]] = x.isna()
        if c.get("fill") is not None:
            x = x.fillna(c["fill"])
        lo = c["lo"] if c.get("lo") is not None else x.min()
        hi = c["hi"] if c.get("hi") is not None else x.max()
        v = (x - lo) / (hi - lo) if hi > lo else x * 0
        v = 1 - v if c["dir"] == "-" else v
        z[c["key"]] = v.fillna(0.5)
    return z, miss


def score(z, w):
    return (z * w).sum(axis=1) / (w.sum() or 1)


def ranks(s):
    return s.rank(ascending=False, method="min").astype(int)


def run(min_dist, crit, vals, ll, scen):
    iatas = [i for i in ll.index if ll.loc[i, "dist_bases_km"] >= min_dist]
    if min_dist:
        print(f"Фильтр: ближе {min_dist:.0f} км к базам — убраны {', '.join(ll.loc[~ll.index.isin(iatas), 'city'])}")
    z, miss = normalize(iatas, crit, vals)
    w = pd.Series({c["key"]: c["weight"] for c in crit}, dtype=float)
    s = score(z, w)
    lo_s, hi_s = score(z.mask(miss, 0.0), w), score(z.mask(miss, 1.0), w)
    best_rank, worst_rank = {}, {}
    for i in iatas:  # лучшее место: у города лучшее неизвестное, у остальных худшее; худшее — наоборот
        sb = lo_s.copy(); sb[i] = hi_s[i]
        sw = hi_s.copy(); sw[i] = lo_s[i]
        best_rank[i], worst_rank[i] = ranks(sb)[i], ranks(sw)[i]
    unk = (miss * w).sum(axis=1) / (w.sum() or 1)
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
    rng = np.random.default_rng(42)
    hits = pd.Series(0, index=iatas)
    for _ in range(2000):
        for i in score(z, w * rng.uniform(0.5, 1.5, len(w))).nlargest(3).index:
            hits[i] += 1
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
    out = pd.DataFrame({"city": ll.loc[iatas, "city"], "score": s.round(3),
                        "score_low": lo_s.round(3), "score_high": hi_s.round(3),
                        "rank_best": pd.Series(best_rank), "rank_worst": pd.Series(worst_rank),
                        "unknown_weight_share": unk.round(2),
                        "top3_share_random": (hits / 2000).round(2)})
    out = out.join(z.round(3)).sort_values("score", ascending=False)
    out.insert(0, "rank", range(1, len(out) + 1))
    sfx = f"_min{int(min_dist)}" if min_dist else ""
    out.to_csv(P / f"longlist_scores{sfx}.csv", index_label="iata", encoding="utf-8")
    pd.DataFrame(one).to_csv(P / f"longlist_sensitivity{sfx}.csv", index=False, encoding="utf-8")
    pd.DataFrame(sc_rows).to_csv(P / f"longlist_scenarios{sfx}.csv", index=False, encoding="utf-8")
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
    scen = pd.read_csv(ROOT / "data/assumptions/weight_scenarios.csv")
    dists = [a.min_dist] if a.min_dist is not None else [0.0, float(PAR["min_dist_bases_km"])]
    for d in dists:
        run(d, data["criteria"], data["values"], ll, scen)
        print()


if __name__ == "__main__":
    main()
