"""Баллы лонглиста, топ-3, диапазон мест из-за неизвестных и слабых значений, проверка устойчивости.

Вход: data/processed/criteria.json (src/build_criteria.py) — критерии и значения со ссылками;
      data/processed/longlist.csv — названия городов и расстояния для фильтра;
      data/assumptions/longlist_params.csv (min_dist_bases_km — решение команды 10.11.2026: 500 км),
      data/assumptions/weight_profiles.csv — наборы весов (основной — предложение коллег, сумма 100).
Метод (тот же, что в панели; правки по аудиту коллег context/22_stage1_audit учтены):
  1. Шкала критерия — фиксированная lo–hi или минимум–максимум по всем 20 городам лонглиста.
     Шкала не пересчитывается после фильтра 500 км, поэтому баллы в разных режимах сравнимы.
     «−» — шкалу переворачиваем.
  2. Неизвестное значение: центр — fill (если задан) или середина 0,5; диапазон — от 0 до 1.
     Слабое значение (чужой хаб по Википедии, косвенное ТО, «более N», «дыра» с неизвестным поездом):
     центр — само значение, диапазон — из его границ.
  3. Балл = сумма (вес × оценка) / сумма весов. Веса должны быть неотрицательными с положительной суммой.
  4. Места: сначала сортировка по полному баллу, потом округление; при точном равенстве — исходный
     порядок городов (как в панели). Лучшее место: у города верхний балл, у остальных нижний; худшее — наоборот.
  5. Устойчивость: каждый вес ×0,5 и ×1,5; 2000 случайных наборов весов ×0,5…1,5 — тот же генератор
     Mulberry32, что в панели; все наборы весов из weight_profiles.csv; режим «строго новый хаб»
     (без опорных аэропортов Red Wings по первичному источнику).
Выход: data/processed/longlist_scores.csv, longlist_scores_min<N>.csv, longlist_scores_min<N>_strict.csv,
       longlist_sensitivity[_minN].csv, longlist_profiles[_minN].csv
Запуск: python src/longlist_score.py
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
PAR = pd.read_csv(ROOT / "data/assumptions/longlist_params.csv").set_index("parameter").value


def scales(crit, vals):
    """Шкала каждого критерия по всем городам лонглиста, а не по прошедшим фильтр."""
    out = {}
    for c in crit:
        xs = []
        for i in vals:
            x = vals[i].get(c["key"], {})
            xs += [v for v in (x.get("v"), x.get("lo"), x.get("hi")) if v is not None]
        lo = c["lo"] if c.get("lo") is not None else (min(xs) if xs else 0.0)
        hi = c["hi"] if c.get("hi") is not None else (max(xs) if xs else 0.0)
        out[c["key"]] = (lo, hi)
    return out


def utility(v, lo, hi, d):
    if v is None or not hi > lo:
        return 0.5
    z = min(1.0, max(0.0, (v - lo) / (hi - lo)))
    return 1 - z if d == "-" else z


def tables(iatas, crit, vals, sc):
    """Центр, нижняя и верхняя оценка 0–1 и признаки «неизвестно» / «слабое» по каждой ячейке."""
    z, a, b, unk, weak = (pd.DataFrame(index=iatas, dtype=float) for _ in range(5))
    for c in crit:
        k, (lo, hi) = c["key"], sc[c["key"]]
        for i in iatas:
            x = vals[i].get(k, {})
            v = x.get("v")
            if v is None:
                u = utility(c["fill"], lo, hi, c["dir"]) if c.get("fill") is not None else 0.5
                ua, ub, un, wk = 0.0, 1.0, True, False
            else:
                u = utility(v, lo, hi, c["dir"])
                if x.get("lo") is not None:
                    p, q = utility(x["lo"], lo, hi, c["dir"]), utility(x["hi"], lo, hi, c["dir"])
                    ua, ub = min(p, q, u), max(p, q, u)
                else:
                    ua = ub = u
                un, wk = False, x.get("lo") is not None
            z.loc[i, k], a.loc[i, k], b.loc[i, k], unk.loc[i, k], weak.loc[i, k] = u, ua, ub, un, wk
    return z, a, b, unk.astype(bool), weak.astype(bool)


def score(z, w):
    if not np.isfinite(w.to_numpy()).all() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("Нужны конечные неотрицательные веса с положительной суммой")
    return (z[w.index] * w).sum(axis=1) / w.sum()


def mulberry32(seed=42):
    """Тот же генератор, что rng() в панели: одинаковые 2000 наборов весов в Python и JS."""
    m = 0xFFFFFFFF
    while True:
        seed = (seed + 0x6D2B79F5) & m
        t = ((seed ^ (seed >> 15)) * (1 | seed)) & m
        t = (t ^ ((t + (((t ^ (t >> 7)) * (61 | t)) & m)) & m)) & m
        yield ((t ^ (t >> 14)) & m) / 4294967296


def top3(s):
    """Три лучших по полному баллу; при равенстве — исходный порядок городов."""
    return list(s.iloc[np.argsort(-s.to_numpy(), kind="stable")].index[:3])


def run(min_dist, crit, vals, ll, profiles, sc, strict=False):
    rw = {i for i in vals if (vals[i].get("rw_support") or {}).get("v") == 1}
    iatas = [i for i in ll.index if ll.loc[i, "dist_bases_km"] >= min_dist and not (strict and i in rw)]
    z, a, b, unk, weak = tables(iatas, crit, vals, sc)
    w = pd.Series({c["key"]: c["weight"] for c in crit}, dtype=float)
    s, lo_s, hi_s = score(z, w), score(a, w), score(b, w)
    best = {i: 1 + sum(lo_s[j] > hi_s[i] or (lo_s[j] == hi_s[i] and iatas.index(j) < iatas.index(i)) for j in iatas if j != i) for i in iatas}
    worst = {i: 1 + sum(hi_s[j] > lo_s[i] or (hi_s[j] == lo_s[i] and iatas.index(j) < iatas.index(i)) for j in iatas if j != i) for i in iatas}
    base = set(top3(s))
    one = []
    for k in w.index:
        if w[k] == 0:
            continue
        for f in (0.5, 1.5):
            ww = w.copy()
            ww[k] *= f
            t = set(top3(score(z, ww)))
            one.append({"weight": k, "factor": f, "top3": ", ".join(sorted(t)), "same_as_base": t == base})
    g = mulberry32(42)
    hits = pd.Series(0, index=iatas)
    for _ in range(2000):
        ww = pd.Series([w[k] * (0.5 + next(g)) for k in w.index], index=w.index)
        for i in top3(score(z, ww)):
            hits[i] += 1
    prof = []
    for pid, gp in profiles.groupby("profile", sort=False):
        pw = gp.set_index("column").weight.reindex(w.index).fillna(0.0)
        t = top3(score(z, pw))
        prof.append({"profile": pid, "label": gp.label.iloc[0], "top3": ", ".join(ll.loc[t, "city"]),
                     "top3_iata": ", ".join(t), "same_as_base": set(t) == base})
    order = np.argsort(-s.to_numpy(), kind="stable")
    out = pd.DataFrame({"city": ll.loc[iatas, "city"], "score": s, "score_low": lo_s, "score_high": hi_s,
                        "rank_best": pd.Series(best), "rank_worst": pd.Series(worst),
                        "unknown_weight_share": (unk * w).sum(axis=1) / w.sum(),
                        "weak_weight_share": (weak * w).sum(axis=1) / w.sum(),
                        "top3_share_random": hits / 2000}).iloc[order]
    out = out.join(z.round(3))
    out.insert(0, "rank", range(1, len(out) + 1))
    for c in ("score", "score_low", "score_high"):
        out[c] = out[c].round(3)
    for c in ("unknown_weight_share", "weak_weight_share", "top3_share_random"):
        out[c] = out[c].round(2)
    sfx = (f"_min{int(min_dist)}" if min_dist else "") + ("_strict" if strict else "")
    out.to_csv(P / f"longlist_scores{sfx}.csv", index_label="iata", encoding="utf-8")
    if not strict:
        pd.DataFrame(one).to_csv(P / f"longlist_sensitivity{sfx}.csv", index=False, encoding="utf-8")
    pd.DataFrame(prof).to_csv(P / f"longlist_profiles{sfx}.csv", index=False, encoding="utf-8")
    head = f"Фильтр {int(min_dist)} км" if min_dist else "Все города"
    print(f"\n=== {head}{' · строго новый хаб (без опорных аэропортов Red Wings)' if strict else ''}")
    pd.set_option("display.width", 200)
    print(out[["rank", "city", "score", "score_low", "score_high", "rank_best", "rank_worst",
               "unknown_weight_share", "weak_weight_share", "top3_share_random"]].to_string())
    print(f"Топ-3: {', '.join(out.city.head(3))}; один вес ×0,5/×1,5 — тройка та же в "
          f"{sum(r['same_as_base'] for r in one)} из {len(one)}")
    for r in prof:
        print(f"  {r['label']}: {r['top3']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-dist", type=float, default=None)
    a = ap.parse_args()
    data = json.loads((P / "criteria.json").read_text(encoding="utf-8"))
    crit, vals = data["criteria"], data["values"]
    ll = pd.read_csv(P / "longlist.csv").set_index("iata")
    ll["dist_bases_km"] = ll[["dist_msk_km", "dist_ekb_km"]].min(axis=1)
    profiles = pd.read_csv(ROOT / "data/assumptions/weight_profiles.csv")
    sc = scales(crit, vals)
    main_d = float(PAR["min_dist_bases_km"])
    dists = [a.min_dist] if a.min_dist is not None else [main_d, 0.0]
    for d in dists:
        run(d, crit, vals, ll, profiles, sc)
    run(main_d, crit, vals, ll, profiles, sc, strict=True)


if __name__ == "__main__":
    main()
