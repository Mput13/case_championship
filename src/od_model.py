"""Шаг 2, мера «поездки откуда — куда» (гипотеза Н1, docs/19).

Проблема: аэропорты публикуют поток на рейсе (сегменты). В нём сидят и те, кто летит только A — B,
и те, кто пересаживается в A или B. Опубликованной доли пересадок по аэропортам России нет
(искали для Шереметьево, Кольцово, Толмачёво, Красноярска 10.11.2026 — не нашли).

Метод — восстановление матрицы поездок по наблюдаемым потокам на рейсах (стандартная задача
транспортного моделирования, OD matrix estimation from link counts):
  1. Поездки «откуда — куда» между всеми парами аэропортов задаются той же формулой тяготения,
     что и в src/demand_model.py: ln T = a + b1·ln(PopA·PopB) + b2·ln(часы поездом) + Москва + курорт.
  2. Каждая поездка идёт по сети прямых рейсов июня–декабря 2026 («Если быть точным»): напрямую,
     если рейс есть; иначе с одной пересадкой в узле перевозчика (data/assumptions/transfer_hubs.csv),
     который даёт самый короткий путь,
     если путь длиннее прямой не больше od_max_circuity раз; иначе поездка не авиационная.
  3. Поток на рейсе = сумма всех поездок, которые по нему идут. Коэффициенты подбираются так,
     чтобы поток на 31 рейсе с известным годовым потоком (data/manual/known_flows.csv) совпал
     с отчётами (метод наименьших квадратов в логарифмах, итерации Левенберга — Марквардта).
  4. Точность — «исключи по одному», как у сегментной модели.
Ограничения: только одна пересадка, путь — самый короткий, международные пересадки (через Москву
за границу) не моделируются и оседают в поездках до Москвы; новые прямые рейсы обычно поднимают
спрос пары (здесь не учтено).

Выход: data/processed/od_pairs.csv (поездки и маршрут для каждой пары), data/processed/od_fit.json
Запуск: python src/od_model.py   (после src/demand_model.py)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import demand_model as dm
from airports_meta import CLOSED, NAME

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
A = pd.read_csv(ROOT / "data/assumptions/demand.csv").set_index("parameter").value


def build():
    n = dm.nodes()
    direct, rail = dm.links()
    ids = [i for i in n.index]
    lat, lon = n.latitude_deg.values, n.longitude_deg.values
    la, lo = np.radians(lat), np.radians(lon)
    D = 2 * 6371 * np.arcsin(np.sqrt(np.sin((la[:, None] - la[None, :]) / 2) ** 2 +
                                      np.cos(la[:, None]) * np.cos(la[None, :]) * np.sin((lo[:, None] - lo[None, :]) / 2) ** 2))
    k = {x: i for i, x in enumerate(ids)}
    adj = np.zeros((len(ids), len(ids)), bool)
    for a, b in direct:
        if a in k and b in k:
            adj[k[a], k[b]] = adj[k[b], k[a]] = True
    # пересадка — только в узлах перевозчиков (data/assumptions/transfer_hubs.csv): по кратчайшему пути
    # через любой аэропорт слишком много поездок шло через Казань и Новосибирск
    hubs = set(pd.read_csv(ROOT / "data/assumptions/transfer_hubs.csv").iata)
    is_hub = np.array([x in hubs for x in ids])
    pairs, X, route = [], [], []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if D[i, j] < A["min_pair_km"]:
                continue
            f = dm.features(n, a, b, rail)
            if adj[i, j]:
                via = None
            else:
                ok = adj[i] & adj[j] & is_hub
                ok[[i, j]] = False
                if not ok.any():
                    continue
                det = np.where(ok, D[i] + D[j], np.inf)
                h = int(det.argmin())
                if det[h] / D[i, j] > A["od_max_circuity"]:
                    continue
                via = ids[h]
            pairs.append((a, b))
            X.append([f[c] for c in dm.FEATS])
            route.append(via)
    X = np.column_stack([np.ones(len(X)), np.array(X)])
    # матрица «рейс × поездка»: какие поездки идут по рейсу
    links = {}
    for p, ((a, b), via) in enumerate(zip(pairs, route)):
        legs = [(a, b)] if via is None else [(a, via), (via, b)]
        for x, y in legs:
            links.setdefault(frozenset((x, y)), []).append(p)
    return n, pairs, X, route, links, D, k


def fit_lm(X, M, y, beta0, iters=200):
    """Левенберг — Марквардт: ln(M @ exp(Xβ)) ≈ y."""
    beta, lam = beta0.copy(), 1e-2

    def resid(b):
        t = np.exp(X @ b)
        s = M @ t
        return y - np.log(s), t, s

    r, t, s = resid(beta)
    cost = (r ** 2).sum()
    for _ in range(iters):
        J = (M @ (t[:, None] * X)) / s[:, None]          # d ln s / d beta
        g = J.T @ r
        H = J.T @ J
        step = np.linalg.solve(H + lam * np.diag(np.diag(H) + 1e-9), g)
        nb = beta + step
        nr, nt, ns = resid(nb)
        nc = (nr ** 2).sum()
        if nc < cost:
            beta, r, t, s, cost, lam = nb, nr, nt, ns, nc, lam / 3
            if np.abs(step).max() < 1e-7:
                break
        else:
            lam *= 4
    return beta


def main():
    n, pairs, X, route, links, D, k = build()
    kf = pd.read_csv(ROOT / "data/manual/known_flows.csv")
    kf = kf[(kf.use == "fit") & kf.from_iata.isin(n.index) & kf.to_iata.isin(n.index)].copy()
    kf["pax_year"] = kf.pax * kf.annual_factor
    rows = [links.get(frozenset((r.from_iata, r.to_iata))) for r in kf.itertuples()]
    keep = [i for i, r in enumerate(rows) if r]
    kf, rows = kf.iloc[keep], [rows[i] for i in keep]
    M = np.zeros((len(kf), len(pairs)))
    for i, ps in enumerate(rows):
        M[i, ps] = 1.0
    y = np.log(kf.pax_year.values)
    seg = json.loads((P / "demand_fit.json").read_text(encoding="utf-8"))["coefficients"]
    beta0 = np.array([seg["const"]] + [seg[c] for c in dm.FEATS])
    beta = fit_lm(X, M, y, beta0)
    pred = np.log(M @ np.exp(X @ beta))
    loo = []
    for i in range(len(y)):
        m = np.ones(len(y), bool)
        m[i] = False
        b = fit_lm(X, M[m], y[m], beta)
        loo.append(y[i] - np.log(M[i] @ np.exp(X @ b)))
    loo = np.array(loo)
    seg_fit = json.loads((P / "demand_fit.json").read_text(encoding="utf-8"))
    q_lo, q_hi = np.quantile(loo, A["cautious_quantile"]), np.quantile(loo, A["optimistic_quantile"])
    T = np.exp(X @ beta)
    # поток на каждом рейсе и доля «своих» поездок в нём
    seg_on = {}
    for key, ps in links.items():
        seg_on[key] = T[ps].sum()
    out = []
    for p, ((a, b), via) in enumerate(zip(pairs, route)):
        s = seg_on.get(frozenset((a, b))) if via is None else None
        out.append({"a": a, "b": b, "city_a": NAME.get(a, n.loc[a, "main_city"]), "city_b": NAME.get(b, n.loc[b, "main_city"]),
                    "km": round(float(D[k[a], k[b]])), "closed": bool({a, b} & set(CLOSED)),
                    "route": "прямой рейс" if via is None else f"с пересадкой в {NAME.get(via, n.loc[via, 'main_city'])}",
                    "via": via, "od_base": round(T[p]), "od_cautious": round(T[p] * np.exp(q_lo)),
                    "od_optimistic": round(T[p] * np.exp(q_hi)),
                    "segments_on_link": round(s) if s is not None else None,
                    "od_share_of_link": round(T[p] / s, 3) if s else None})
    od = pd.DataFrame(out)
    od.to_csv(P / "od_pairs.csv", index=False, encoding="utf-8")
    ape_fact = np.abs(np.exp(-loo) - 1)
    rep = {"method": "восстановление поездок по потокам на рейсах; одна пересадка, кратчайший путь",
           "n_links_fit": int(len(y)), "pairs_air": int(len(pairs)),
           "pairs_direct": int(sum(v is None for v in route)), "pairs_one_stop": int(sum(v is not None for v in route)),
           "coefficients": dict(zip(["const"] + dm.FEATS, [round(float(x), 3) for x in beta])),
           "fit_r2_log": round(float(1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()), 3),
           "loo_median_abs_error_pct_of_fact": round(float(np.median(ape_fact) * 100), 1),
           "loo_share_within_x2": round(float(np.mean(np.abs(loo) <= np.log(2))), 2),
           "segment_model_loo_error_pct_of_fact": seg_fit.get("loo_median_abs_error_pct_of_fact"),
           "cautious_factor": round(float(np.exp(q_lo)), 2), "optimistic_factor": round(float(np.exp(q_hi)), 2),
           "od_total_air_trips_year": round(float(T.sum())),
           "segments_total_on_links_year": round(float(sum(seg_on.values()))),
           "known_links": [{"pair": f"{r.from_iata}-{r.to_iata}", "fact": int(r.pax_year),
                            "model_segments": int(round(np.exp(pv))),
                            "own_trips_share": round(float(T[pairs.index((r.from_iata, r.to_iata))] / np.exp(pv)), 2)
                            if (r.from_iata, r.to_iata) in pairs else
                            round(float(T[pairs.index((r.to_iata, r.from_iata))] / np.exp(pv)), 2)
                            if (r.to_iata, r.from_iata) in pairs else None}
                           for r, pv in zip(kf.itertuples(), pred)]}
    (P / "od_fit.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k2: v for k2, v in rep.items() if k2 != "known_links"}, ensure_ascii=False, indent=1))
    kl = pd.DataFrame(rep["known_links"])
    print(kl.to_string(index=False))


if __name__ == "__main__":
    main()
