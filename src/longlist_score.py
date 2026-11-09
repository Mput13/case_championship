"""Баллы лонглиста, топ-3 и проверка устойчивости к весам.

Вход: data/processed/longlist.csv, data/assumptions/longlist_weights.csv
Метод:
  1. Каждый критерий переводим в шкалу 0–1 (min–max по 20 городам; «−» — переворачиваем).
     Пропуски: transfer_zone неизвестно → 0,5; rostec_link неизвестно → 0 (пометка в выводе).
  2. Балл = сумма (вес × значение) / сумма весов.
  3. Устойчивость: (а) каждый вес по очереди ×0,5 и ×1,5; (б) 2000 случайных наборов весов
     (каждый вес умножаем на случайное число от 0,5 до 1,5). Считаем, как часто город в топ-3.
Выход: data/processed/longlist_scores.csv, data/processed/longlist_sensitivity.csv
Запуск: python src/longlist_score.py               (все 20 городов)
        python src/longlist_score.py --min-dist 500 (без городов ближе 500 км к Москве/Екатеринбургу)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

# временно, до доли перевозчиков по расписанию: хаб конкурента по его собственному заявлению
COMPETITOR_HUB = {"KJA": "группа «Аэрофлот» (аэропорт KJA, итоги 2025)",
                  "IKT": "S7 (сайт S7)", "VVO": "«Аврора» и S7 (аэропорт VVO, итоги 2025)"}


def prepare(df):
    df = df.copy()
    df["competitor_hub"] = df.iata.map(lambda i: 1 if i in COMPETITOR_HUB else 0)
    df["dist_bases_km"] = df[["dist_msk_km", "dist_ekb_km"]].min(axis=1)
    df["transfer_zone"] = pd.to_numeric(df.transfer_zone, errors="coerce").fillna(0.5)
    df["rostec_link"] = pd.to_numeric(df.rostec_link, errors="coerce").fillna(0)
    return df


def normalize(df, w):
    z = pd.DataFrame(index=df.index)
    for r in w.itertuples():
        x = pd.to_numeric(df[r.column], errors="coerce")
        span = x.max() - x.min()
        v = (x - x.min()) / span if span else x * 0
        z[r.column] = 1 - v if r.direction == "-" else v
    return z


def score(z, weights):
    return (z * weights).sum(axis=1) / weights.sum()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-dist", type=float, default=0,
                    help="отсеять города ближе N км к Москве или Екатеринбургу (базам Red Wings)")
    args = ap.parse_args()
    df = prepare(pd.read_csv(P / "longlist.csv"))
    if args.min_dist:
        drop = df[df.dist_bases_km < args.min_dist].city.tolist()
        print(f"Фильтр: ближе {args.min_dist:.0f} км к базам — убраны {', '.join(drop)}")
        df = df[df.dist_bases_km >= args.min_dist].reset_index(drop=True)
    w = pd.read_csv(ROOT / "data/assumptions/longlist_weights.csv")
    z = normalize(df, w)
    base_w = pd.Series(w.weight.values, index=w.column, dtype=float)
    df["score"] = score(z, base_w).round(3)
    df["rank"] = df.score.rank(ascending=False, method="min").astype(int)
    top3 = set(df.nsmallest(3, "rank").iata)

    # (а) один вес ×0,5 / ×1,5
    one = []
    for col in base_w.index:
        for k in (0.5, 1.5):
            ww = base_w.copy()
            ww[col] *= k
            s = score(z, ww)
            t = set(df.loc[s.nlargest(3).index, "iata"])
            one.append({"weight": col, "factor": k, "top3": ", ".join(sorted(t)),
                        "same_as_base": t == top3})
    # (б) случайные веса
    rng = np.random.default_rng(42)
    hits = pd.Series(0, index=df.iata)
    N = 2000
    for _ in range(N):
        ww = base_w * rng.uniform(0.5, 1.5, len(base_w))
        s = score(z, ww)
        for i in df.loc[s.nlargest(3).index, "iata"]:
            hits[i] += 1
    df["top3_share_random"] = df.iata.map(hits / N).round(2)

    cols = ["rank", "city", "iata", "score", "top3_share_random"] + list(base_w.index)
    out = df.sort_values("rank")[cols]
    sfx = f"_min{int(args.min_dist)}" if args.min_dist else ""
    out.to_csv(P / f"longlist_scores{sfx}.csv", index=False, encoding="utf-8")
    pd.DataFrame(one).to_csv(P / f"longlist_sensitivity{sfx}.csv", index=False, encoding="utf-8")
    print(out.to_string(index=False))
    same = sum(r["same_as_base"] for r in one)
    print(f"\nТоп-3: {', '.join(df.nsmallest(3, 'rank').city)}")
    print(f"Один вес ×0,5 или ×1,5: топ-3 тот же в {same} из {len(one)} вариантов")
    for r in one:
        if not r["same_as_base"]:
            print(f"  меняется: {r['weight']} ×{r['factor']} → {r['top3']}")


if __name__ == "__main__":
    main()
