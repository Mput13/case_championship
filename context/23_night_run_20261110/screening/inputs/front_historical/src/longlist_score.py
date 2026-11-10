"""Баллы лонглиста, топ-3 и проверка устойчивости к весам.

Вход: data/processed/criteria.json (src/build_criteria.py) — все критерии, основные и подключаемые;
      data/processed/longlist.csv — названия городов и расстояния для фильтра.
Метод (тот же, что в панели):
  1. Каждый критерий переводим в шкалу 0–1 (min–max по городам в фильтре; «−» — переворачиваем).
     Пропуск: если у критерия задан fill — подставляем это сырое значение до нормировки;
     иначе после нормировки ставим нейтральные 0,5.
  2. Балл = сумма (вес × оценка) / сумма весов.
  3. Устойчивость: (а) каждый вес по очереди ×0,5 и ×1,5; (б) 2000 случайных наборов весов (×0,5…1,5).
Выход: data/processed/longlist_scores[_minN].csv, longlist_sensitivity[_minN].csv
Запуск: python src/longlist_score.py               (все 20 городов)
        python src/longlist_score.py --min-dist 500 (без городов ближе 500 км к Москве/Екатеринбургу)
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"


def zscores(iatas, crit, vals):
    z = pd.DataFrame(index=iatas)
    for c in crit:
        x = pd.Series({i: vals[i][c["key"]]["v"] for i in iatas}, dtype=float)
        if c.get("fill") is not None:
            x = x.fillna(c["fill"])
        lo, hi = x.min(), x.max()
        v = (x - lo) / (hi - lo) if hi > lo else x * 0
        v = 1 - v if c["dir"] == "-" else v
        z[c["key"]] = v.fillna(0.5)
    return z


def score(z, w):
    return (z * w).sum(axis=1) / (w.sum() or 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-dist", type=float, default=0)
    a = ap.parse_args()
    data = json.loads((P / "criteria.json").read_text(encoding="utf-8"))
    crit, vals = data["criteria"], data["values"]
    ll = pd.read_csv(P / "longlist.csv").set_index("iata")
    ll["dist_bases_km"] = ll[["dist_msk_km", "dist_ekb_km"]].min(axis=1)
    iatas = [i for i in ll.index if ll.loc[i, "dist_bases_km"] >= a.min_dist]
    if a.min_dist:
        print(f"Фильтр: ближе {a.min_dist:.0f} км к базам — убраны {', '.join(ll.loc[~ll.index.isin(iatas), 'city'])}")
    z = zscores(iatas, crit, vals)
    w = pd.Series({c["key"]: c["weight"] for c in crit}, dtype=float)
    s = score(z, w)
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

    out = pd.DataFrame({"city": ll.loc[iatas, "city"], "score": s.round(3), "top3_share_random": (hits / 2000).round(2)})
    out = out.join(z.round(3)).sort_values("score", ascending=False)
    out.insert(0, "rank", range(1, len(out) + 1))
    sfx = f"_min{int(a.min_dist)}" if a.min_dist else ""
    out.to_csv(P / f"longlist_scores{sfx}.csv", index_label="iata", encoding="utf-8")
    pd.DataFrame(one).to_csv(P / f"longlist_sensitivity{sfx}.csv", index=False, encoding="utf-8")
    print(out[["rank", "city", "score", "top3_share_random"]].to_string())
    same = sum(r["same_as_base"] for r in one)
    print(f"\nТоп-3: {', '.join(out.city.head(3))}")
    print(f"Один вес ×0,5 или ×1,5: топ-3 тот же в {same} из {len(one)} вариантов")


if __name__ == "__main__":
    main()
