"""Шаг 2. Спрос по парам городов: сколько пассажиров в год летает (или полетело бы) между двумя аэропортами.

Метод — модель тяготения (гравитационная), стандартный способ оценки спроса между городами:
    ln(поток) = a + b1·ln(население А × население Б) + b2·ln(часы поездом между городами)
                + поправки: Москва на одном конце, курорт (Сочи, Минводы) на одном конце
Часы поездом вместо расстояния: чем дольше и неудобнее поезд, тем больше людей летит (docs/11).
Коэффициенты подбираются по известным потокам 2025 года, которые публикуют аэропорты
(data/manual/known_flows.csv, у каждой строки ссылка). Точность проверяется «исключи по одному»:
каждую известную пару убираем, подбираем формулу без неё и сравниваем прогноз с фактом.

Что даёт модель: годовой поток на прямой линии между аэропортами, оба направления, как публикуют
аэропорты. Для пар без прямого рейса это скрытый спрос — сколько полетело бы при прямом рейсе.
Три оценки: осторожная (20-й процентиль ошибки), базовая, оптимистичная (80-й).
Если поток пары известен из отчёта аэропорта, в таблицу идёт он, а модель — для сверки.

Проверка на независимых данных: провозная ёмкость субсидируемых маршрутов 2026 (data/raw/favt_subsidy_2026.csv)
× загрузка (data/assumptions/demand.csv).

Вход: data/processed/catchments.csv (src/longlist_data.py), data/manual/known_flows.csv,
      data/raw/favt_subsidy_2026.csv (src/fetch_subsidy.py), «Если быть точным» (прямые рейсы, поезда),
      data/assumptions/demand.csv
Выход: data/processed/demand_pairs.csv, data/processed/demand_fit.json
Запуск: python src/demand_model.py
"""
import json
import re
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

from airports_meta import CLOSED, NAME

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
TOCHNO = ROOT / "data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv"
MOW = {"SVO", "DME", "VKO", "ZIA"}
RESORT = {"AER", "MRV"}
BASES = {"MOW", "SVX"}
# выбрано сравнением вариантов «исключи по одному»: время поездом точнее расстояния (ошибка 56% против 66%)
FEATS = ["lnPP", "lnRail", "mow", "resort"]
NO_RAIL_HR = 96  # нет поезда (Калининград, Дальний Восток) = как 4 суток в пути


def hav(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(radians, (la1, lo1, la2, lo2))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def nodes():
    c = pd.read_csv(P / "catchments.csv")
    m = c[c.iata.isin(MOW)]
    svo = c[c.iata == "SVO"].iloc[0]
    mow = pd.DataFrame([{"iata": "MOW", "pop": m["pop"].sum(), "main_city": "Москва", "region": "Москва",
                         "latitude_deg": svo.latitude_deg, "longitude_deg": svo.longitude_deg}])
    c = pd.concat([c[~c.iata.isin(MOW)], mow], ignore_index=True)
    return c.set_index("iata")


def grp(x):
    return "MOW" if x in MOW else x


def links():
    """Прямые рейсы и время поездом из набора «Если быть точным»."""
    t = pd.read_csv(TOCHNO, sep=";")
    direct = set()
    for cm in t[(t.transport_type == "air") & t.distance_km.notna()].comment.dropna():
        m = re.match(r"\s*([A-Z0-9]{3})\s*—\s*([A-Z0-9]{3})", cm)
        if m:
            a, b = grp(m.group(1)), grp(m.group(2))
            direct |= {(a, b), (b, a)}
    rail = t[t.transport_type == "rail"].set_index(["city_from", "city_to"]).distance_hr
    return direct, rail


def features(n, a, b, rail):
    A, B = n.loc[a], n.loc[b]
    d = hav(A.latitude_deg, A.longitude_deg, B.latitude_deg, B.longitude_deg)
    hr = rail.get((A.main_city, B.main_city))
    hr = NO_RAIL_HR if hr is None or pd.isna(hr) else float(hr)
    return {"lnPP": np.log(A["pop"]) + np.log(B["pop"]), "lnD": np.log(d), "lnRail": np.log(hr), "rail_hr": hr, "km": d,
            "mow": float("MOW" in (a, b)), "led": float("LED" in (a, b)), "resort": float(bool(RESORT & {a, b}))}


def fit(X, y):
    Xc = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    return beta


def predict(beta, X):
    return np.column_stack([np.ones(len(X)), X]) @ beta


def main():
    n = nodes()
    direct, rail = links()
    a_csv = pd.read_csv(ROOT / "data/assumptions/demand.csv").set_index("parameter").value
    kf = pd.read_csv(ROOT / "data/manual/known_flows.csv")
    kf = kf[kf.from_iata.isin(n.index) & kf.to_iata.isin(n.index)].copy()
    kf["pax_year"] = kf.pax * kf.annual_factor
    rows = [features(n, r.from_iata, r.to_iata, rail) | {"y": np.log(r.pax_year)} for r in kf.itertuples()]
    F = pd.DataFrame(rows, index=kf.index)
    train = kf.use == "fit"
    X, y = F.loc[train, FEATS].values, F.loc[train, "y"].values
    beta = fit(X, y)
    resid = y - predict(beta, X)
    # «исключи по одному»
    loo = []
    for i in range(len(y)):
        m = np.ones(len(y), bool)
        m[i] = False
        b_i = fit(X[m], y[m])
        loo.append(y[i] - predict(b_i, X[i:i + 1])[0])
    loo = np.array(loo)
    q_lo, q_hi = np.quantile(loo, a_csv["cautious_quantile"]), np.quantile(loo, a_csv["optimistic_quantile"])
    r2 = 1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum()
    ape = np.abs(np.exp(loo) - 1)
    kf.loc[train, "model"] = np.exp(predict(beta, X)).round()
    kf.loc[train, "loo_error_pct"] = ((np.exp(-loo) - 1) * 100).round(0)
    low = ~train
    kf.loc[low, "model"] = np.exp(predict(beta, F.loc[low, FEATS].values)).round()

    # все пары, где на одном конце кандидат в хаб или база
    cand = set(pd.read_csv(P / "longlist.csv").iata) | BASES
    known = {(r.from_iata, r.to_iata): r for r in kf.itertuples()}
    known.update({(b, a): r for (a, b), r in list(known.items())})
    out = []
    ids = list(n.index)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if not ({a, b} & cand):
                continue
            f = features(n, a, b, rail)
            if f["km"] < 250:
                continue
            mu = predict(beta, np.array([[f[k] for k in FEATS]]))[0]
            hr = rail.get((n.loc[a, "main_city"], n.loc[b, "main_city"]))
            k = known.get((a, b))
            obs = k.pax_year if k is not None else None
            out.append({
                "a": a, "b": b, "city_a": NAME.get(a, n.loc[a, "main_city"]), "city_b": NAME.get(b, n.loc[b, "main_city"]),
                "closed": bool({a, b} & set(CLOSED)),
                "km": round(f["km"]), "pop_a": int(n.loc[a, "pop"]), "pop_b": int(n.loc[b, "pop"]),
                "direct_now": (a, b) in direct, "rail_hr": None if hr is None or pd.isna(hr) else round(float(hr), 1),
                "pax_cautious": round(np.exp(mu + q_lo)), "pax_base": round(np.exp(mu)), "pax_optimistic": round(np.exp(mu + q_hi)),
                "observed": obs, "observed_coverage": k.coverage if k is not None else None,
                "observed_source": k.source if k is not None else None,
                "method": ("отчёт аэропорта" if k is not None and k.coverage != "airline_group" else
                           "модель тяготения (нижняя граница по отчёту группы «Аэрофлот»)" if k is not None else
                           "модель тяготения, калибровка по data/manual/known_flows.csv"),
            })
    pairs = pd.DataFrame(out)

    # независимая сверка: субсидируемые маршруты 2026
    sub = pd.read_csv(ROOT / "data/raw/favt_subsidy_2026.csv", dtype=str)
    num = lambda s: pd.to_numeric(s.str.replace(r"[\s\xa0]", "", regex=True).str.replace(",", "."), errors="coerce")
    sub["cap"] = 2 * num(sub.round_trips_2026) * num(sub.seats)
    city2iata = {v: k for k, v in n.main_city.items()}
    sub["a"], sub["b"] = sub.origin.map(city2iata), sub.destination.map(city2iata)
    s = sub.dropna(subset=["a", "b"]).groupby(["a", "b"]).cap.sum().reset_index()
    s["pax_subsidy"] = s.cap * a_csv["subsidy_load_factor"]
    chk = []
    for r in s.itertuples():
        if r.a == r.b:
            continue
        f = features(n, r.a, r.b, rail)
        chk.append({"a": r.a, "b": r.b, "pax_subsidy": r.pax_subsidy,
                    "model": float(np.exp(predict(beta, np.array([[f[k] for k in FEATS]]))[0]))})
    chk = pd.DataFrame(chk)
    ratio = (chk.model / chk.pax_subsidy) if len(chk) else pd.Series(dtype=float)

    report = {
        "n_fit": int(train.sum()), "r2": round(float(r2), 3),
        "coefficients": dict(zip(["const"] + FEATS, [round(float(x), 3) for x in beta])),
        "loo_median_abs_error_pct": round(float(np.median(ape) * 100), 1),
        "loo_share_within_x2": round(float(np.mean(np.abs(loo) <= np.log(2))), 2),
        "cautious_factor": round(float(np.exp(q_lo)), 2), "optimistic_factor": round(float(np.exp(q_hi)), 2),
        "subsidy_check_pairs": int(len(chk)),
        "subsidy_check_median_model_to_capacity": round(float(ratio.median()), 2) if len(ratio) else None,
        "lower_bound_checks": [{"pair": f"{r.from_iata}-{r.to_iata}", "lower_bound": int(r.pax_year), "model": int(r.model)}
                               for r in kf[low].itertuples()],
    }
    pairs.to_csv(P / "demand_pairs.csv", index=False, encoding="utf-8")
    kf.to_csv(P / "demand_calibration.csv", index=False, encoding="utf-8")
    (P / "demand_fit.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"пар в таблице: {len(pairs)}")


if __name__ == "__main__":
    main()
