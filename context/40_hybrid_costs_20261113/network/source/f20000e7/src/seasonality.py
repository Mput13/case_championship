"""Сезонность спроса по аэропортам: помесячный индекс для каждого узла модели.

Как авиакомпании: год делится на два сезона расписания IATA (лето — с конца марта по конец октября,
зима — остальное), частоты задаются на сезон, а пик внутри сезона закрывается более высокой загрузкой.
Для этого модели нужен спрос по месяцам. Открытых помесячных данных по маршрутам нет, поэтому:

1. Профиль аэропорта — пассажиропоток по месяцам из открытых данных Росавиации за 2017–2019 годы
   (data/raw/favt_airports_2007_2020.csv; последние годы до ковида и ограничений).
   Индекс месяца = пассажиры месяца / среднее за месяц того же года, затем среднее по годам.
2. В данных аэропорта есть международные рейсы, их летние чартеры раздувают пик. Поправка:
   размах профиля аэропорта умножается на k — наклон регрессии профиля внутренних перевозок
   группы «Аэрофлот» на профиль всех аэропортов России в те же годы (data/processed/aeroflot_traffic_monthly.csv).
3. Узел без данных Росавиации получает профиль внутренних перевозок «Аэрофлота» 2023–2025.
4. Профиль маршрута A — B в модели — среднее профилей двух концов (допущение, src/network_model.py).

Выход: data/processed/airport_seasonality.csv (iata, m1..m12, source), data/processed/seasonality_calibration.json
Запуск: py -3.13 src/seasonality.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import demand_model as dm

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
M = [f"m{i}" for i in range(1, 13)]
YEARS = [2017, 2018, 2019]


def favt():
    d = pd.read_csv(ROOT / "data/raw/favt_airports_2007_2020.csv", sep=";", encoding="cp1251")
    d = d.dropna(subset=[d.columns[1]])
    d.columns = ["airport", "year"] + M + ["total"]
    d["year"] = d.year.astype(int)
    for c in M:   # «***» — значение скрыто Росавиацией
        d[c] = pd.to_numeric(d[c].astype(str).str.replace(r"\s", "", regex=True), errors="coerce")
    return d[d.year.isin(YEARS)]


def aeroflot_domestic():
    t = pd.read_csv(P / "aeroflot_traffic_monthly.csv")
    return t[(t.entity == "group") & (t.metric == "passengers") & (t.scope == "domestic")]


def year_index(v):
    v = np.asarray(v, dtype=float)
    return v / v.mean()


def main():
    d = favt()
    afl = aeroflot_domestic()
    # поправка на международные рейсы: k по каждому году, затем среднее
    ks = {}
    for y in YEARS:
        allp = year_index(d[d.year == y][M].sum().values)
        dom = year_index(afl[afl.month.str.startswith(str(y))].sort_values("month").value.values)
        ks[y] = float(np.polyfit(allp - 1, dom - 1, 1)[0])
    k = float(np.mean(list(ks.values())))
    fb = np.mean([year_index(afl[afl.month.str.startswith(str(y))].sort_values("month").value.values)
                  for y in (2023, 2024, 2025)], axis=0)

    names = pd.read_csv(ROOT / "data/manual/favt_airport_names.csv")
    names = {r.iata: (r.favt_names.split(";"), r.combine) for r in names.itertuples()}
    rows = []
    for iata in dm.nodes().index:
        prof, years_used = [], []
        if iata in names:
            nm, how = names[iata]
            for y in YEARS:
                dy = d[d.year == y].set_index("airport")
                got = [dy.loc[n, M].values.astype(float) for n in nm if n in dy.index and dy.loc[n, M].notna().all()]
                if not got:
                    continue
                v = np.sum(got, axis=0) if how == "sum" else got[0]
                if (v > 0).all():
                    prof.append(year_index(v))
                    years_used.append(y)
        if prof:
            raw = np.mean(prof, axis=0)
            idx = 1 + k * (raw - 1)
            src = f"Росавиация, пассажиропоток аэропорта по месяцам {', '.join(map(str, years_used))}; размах × {k:.2f} (поправка на международные рейсы)"
        else:
            raw, idx = fb, fb
            src = "нет помесячных данных Росавиации: профиль внутренних перевозок группы «Аэрофлот» 2023–2025"
        rows.append({"iata": iata, **{m: round(float(v), 4) for m, v in zip(M, idx)},
                     "peak": round(float(idx.max()), 3), "trough": round(float(idx.min()), 3),
                     "raw_peak": round(float(raw.max()), 3), "source": src})
    out = pd.DataFrame(rows)
    out.to_csv(P / "airport_seasonality.csv", index=False, encoding="utf-8")
    (P / "seasonality_calibration.json").write_text(json.dumps(
        {"k_domestic": round(k, 4), "k_by_year": {str(y): round(v, 4) for y, v in ks.items()},
         "fallback_profile_aeroflot_domestic_2023_2025": [round(float(v), 4) for v in fb],
         "method": "k — наклон регрессии (индекс внутренних перевозок «Аэрофлота» − 1) на (индекс всех аэропортов России − 1)"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    n_fb = int(out.source.str.startswith("нет").sum())
    print(f"ok {len(out)} узлов, по данным Росавиации {len(out) - n_fb}, по профилю «Аэрофлота» {n_fb}; k = {k:.3f}")


if __name__ == "__main__":
    main()
