"""Шаг 3. Сравнение гипотез: хаб в городе-кандидате против прямых рейсов из баз в Москве и Екатеринбурге.

Гипотеза 1 — хаб. Самолёты базируются в городе H и летают лучами H — X. На каждом луче:
  местные пассажиры H — X (спрос пары × доля захвата);
  пересадочные X — H — Y: пары без прямого рейса, путь через хаб длиннее прямой не больше чем на 35%,
  пары дальше 500 км (спрос пары × доля захвата пересадки). Пересадочный пассажир занимает кресло
  на двух рейсах, а платит один билет (× скидка за пересадку).
Гипотеза 2 — прямые рейсы. Самолёт с базы B (Москва или Екатеринбург) летает треугольником B — X — Y — B:
  продаёт пару X — Y (прямого рейса нет) и местных пассажиров на плечах B — X и Y — B.

Отбор маршрутов одинаковый для обеих гипотез: считаем вклад каждого маршрута (выручка минус
переменные расходы) на блок-час и набираем лучшие, пока хватает самолётов (fleet_cap) и не больше
max_routes маршрутов. Частота = сколько нужно рейсов, чтобы перевезти захваченных, от 3 до 14 в неделю;
доля захвата растёт с частотой: доля = максимум × (1 − exp(−частота / 3)).

Спрос пары — из модели шага 2 (data/processed/demand_pairs.csv или та же формула для остальных пар);
в базовом сценарии базовая оценка, в осторожном — осторожная. Все допущения — data/assumptions/network.csv.
Результат до расходов на аренду самолётов, базу и офис (как у коллег, context/12_network_economics).

Выход: data/processed/network_routes.csv (каждый маршрут), network_summary.csv (итоги по вариантам)
Запуск: python src/network_model.py
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import demand_model as dm
from airports_meta import CLOSED, NAME

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
SOUTH = {"AER", "MRV", "MCX", "KRR", "GDZ", "STW", "NAL", "OGZ", "GRV", "IGT", "ESL", "ASF", "VOG", "KGD"}


def load_assumptions():
    a = pd.read_csv(ROOT / "data/assumptions/network.csv")
    return {s: dict(zip(a.parameter, a[s].astype(float))) for s in ("base", "cautious")}


class Demand:
    """Спрос пары за год (оба направления): известный поток → таблица шага 2 → формула шага 2."""

    def __init__(self):
        self.n = dm.nodes()
        self.direct, self.rail = dm.links()
        fit = json.loads((P / "demand_fit.json").read_text(encoding="utf-8"))
        co = fit["coefficients"]
        self.beta = np.array([co["const"]] + [co[k] for k in dm.FEATS])
        self.f_lo, self.f_hi = fit["cautious_factor"], fit["optimistic_factor"]
        t = pd.read_csv(P / "demand_pairs.csv")
        self.tab = {}
        for r in t.itertuples():
            base = r.observed if pd.notna(r.observed) and r.observed_coverage != "airline_group" else r.pax_base
            v = {"base": float(base), "cautious": float(r.pax_cautious), "method": r.method}
            self.tab[(r.a, r.b)] = self.tab[(r.b, r.a)] = v
        self.cache = {}

    def get(self, a, b, scen):
        if (a, b) in self.tab:
            return self.tab[(a, b)][scen]
        key = (min(a, b), max(a, b))
        if key not in self.cache:
            f = dm.features(self.n, a, b, self.rail)
            self.cache[key] = float(np.exp(dm.predict(self.beta, np.array([[f[k] for k in dm.FEATS]]))[0]))
        v = self.cache[key]
        return v if scen == "base" else v * self.f_lo

    def method(self, a, b):
        return self.tab.get((a, b), {}).get("method", "модель тяготения (src/demand_model.py)")

    def km(self, a, b):
        A, B = self.n.loc[a], self.n.loc[b]
        return dm.hav(A.latitude_deg, A.longitude_deg, B.latitude_deg, B.longitude_deg)

    def has_direct(self, a, b):
        return (a, b) in self.direct


def leg_cost(A, km, south, pax):
    """Переменные расходы одного рейса и блок-время."""
    k = A["route_factor_south"] if south else A["route_factor"]
    bh = A["block_fixed_h"] + km * k / A["block_speed_kmh"]
    fuel = (A["fuel_t_per_hour"] * bh + A["fuel_t_per_cycle"]) * A["fuel_rub_per_t"]
    per_h = (A["mro_rub_per_hour"] + A["crew_rub_per_hour"] + A["navigation_rub_per_hour"]) * bh
    return bh, fuel + per_h + A["ground_rub_per_flight"] + A["deicing_rub_per_flight"] + pax * A["pax_cost_rub"]


def fare(A, km):
    return A["fare_fixed_rub"] + A["fare_per_km_rub"] * km


def capture(qmax, f, A):
    return qmax * (1 - math.exp(-f / A["capture_freq_scale"]))


def leg_share(L, f, A):
    """Доля Red Wings в спросе плеча при частоте f в неделю.
    Плечо короче transfer_min_km: местных не продаём (поезд и машина быстрее).
    Пара без прямого рейса: доля растёт с частотой до capture_open.
    Пара с прямым рейсом: доля по частотам (QSI, docs/06) = f / (f + рейсы конкурентов),
    рейсы конкурентов = сколько рейсов нужно на нынешний поток пары при загрузке 80%."""
    if L["km"] < A["transfer_min_km"]:
        return 0.0
    if L.get("competitive"):
        f_comp = L["dem"] / (A["seats"] * 0.8)
        return min(A["capture_competitive"], f / (f + f_comp)) if f_comp > 0 else 0.0
    return capture(A["capture_open"], f, A)


def freq_for(pax_week_dir, A):
    need = math.ceil(pax_week_dir / (A["seats"] * A["lf_max"])) if pax_week_dir > 0 else 0
    return int(min(A["max_freq_week"], max(A["min_freq_week"], need)))


def evaluate_legs(legs, A):
    """legs: список плеч {a,b,km,south,pax_dir_week(желаемые), rev_week}; считает частоту, расходы, загрузку."""
    hours = cost = flights = seg = 0.0
    for L in legs:
        f = freq_for(L["pax_dir_week"], A)
        cap = f * A["seats"] * A["lf_max"]
        carried = min(L["pax_dir_week"], cap)
        scale = carried / L["pax_dir_week"] if L["pax_dir_week"] else 0
        bh, c = leg_cost(A, L["km"], L["south"], carried / max(f, 1))
        L.update(freq=f, carried_dir_week=carried, scale=scale, block_h=bh, lf=carried / (f * A["seats"]) if f else 0)
        hours += 2 * f * bh
        cost += 2 * f * c
        flights += 2 * f
        seg += 2 * carried
    return hours, cost, flights, seg


def hub_network(H, D, A, scen, cand_nodes):
    W = A["weeks_per_year"]
    spokes = []
    for X in cand_nodes:
        if X == H or X in CLOSED:
            continue
        km = D.km(H, X)
        lim = 2150 if ({H, X} & SOUTH) else 2300
        if km > lim or km < 250:
            continue
        spokes.append(X)

    def build(S):
        legs, rev, od_local, od_transfer = {}, 0.0, 0.0, 0.0
        for X in S:
            km = D.km(H, X)
            loc = D.get(H, X, scen) / (2 * W)
            legs[X] = {"a": H, "b": X, "km": km, "south": bool({H, X} & SOUTH), "local": loc, "dem": loc,
                       "competitive": D.has_direct(H, X), "transfer": 0.0}
        trans = []
        for i, X in enumerate(S):
            for Y in S[i + 1:]:
                dxy = D.km(X, Y)
                if dxy < A["transfer_min_km"] or D.has_direct(X, Y) or X in CLOSED or Y in CLOSED:
                    continue
                if (D.km(H, X) + D.km(H, Y)) / dxy > A["transfer_max_circuity"]:
                    continue
                t = D.get(X, Y, scen) / (2 * W) * A["capture_transfer"]
                trans.append((X, Y, dxy, t))
                legs[X]["transfer"] += t
                legs[Y]["transfer"] += t
        # частота ↔ захват: две итерации
        for _ in range(2):
            for L in legs.values():
                f = L.get("freq", A["min_freq_week"])
                L["pax_dir_week"] = L["local"] * leg_share(L, f, A) + L["transfer"] * (1 - math.exp(-f / A["capture_freq_scale"]))
                L["freq"] = freq_for(L["pax_dir_week"], A)
        hours, cost, flights, seg = evaluate_legs(list(legs.values()), A)
        for L in legs.values():
            loc = L["local"] * leg_share(L, L["freq"], A) * L["scale"]
            L["local_carried"] = loc
            rev += 2 * loc * fare(A, L["km"])
            od_local += 2 * loc
        for X, Y, dxy, t in trans:
            s = min(legs[X]["scale"], legs[Y]["scale"])
            tf = t * (1 - math.exp(-min(legs[X]["freq"], legs[Y]["freq"]) / A["capture_freq_scale"])) * s
            rev += 2 * tf * fare(A, dxy) * A["transfer_fare_factor"]
            od_transfer += 2 * tf
        return legs, trans, hours, cost, rev, od_local, od_transfer, flights

    # жадный отбор лучей: вклад на блок-час, с учётом пересадок к уже выбранным
    chosen, best = [], None
    max_h = (A["fleet_cap"] - A["spare_aircraft"]) * A["block_h_per_day"] * 7
    while len(chosen) < A["max_routes"]:
        cand = None
        for X in spokes:
            if X in chosen:
                continue
            r = build(chosen + [X])
            if r[2] > max_h:
                continue
            gain = (r[4] - r[3]) - ((best[4] - best[3]) if best else 0)
            dh = r[2] - (best[2] if best else 0)
            score = gain / dh if dh > 0 else -1e18
            if cand is None or score > cand[0]:
                cand = (score, X, r)
        if cand is None or (cand[0] <= 0 and len(chosen) >= 8):
            break
        chosen.append(cand[1])
        best = cand[2]
    return chosen, best


def direct_network(D, A, scen, nodes_all):
    W = A["weeks_per_year"]
    bases = ["MOW", "SVX"]
    max_h = (A["fleet_cap"] - A["spare_aircraft"]) * A["block_h_per_day"] * 7
    tri = []
    open_nodes = [x for x in nodes_all if x not in CLOSED and x not in bases]
    for i, X in enumerate(open_nodes):
        for Y in open_nodes[i + 1:]:
            dxy = D.km(X, Y)
            if dxy < A["transfer_min_km"] or D.has_direct(X, Y):
                continue
            if dxy > (2150 if ({X, Y} & SOUTH) else 2300):
                continue
            for B in bases:
                d1, d2 = D.km(B, X), D.km(Y, B)
                if max(d1, d2) > 2300 or d1 + d2 > 2.2 * dxy + 1500:
                    continue
                legs = []
                for a, b, km, direct in ((B, X, d1, True), (X, Y, dxy, False), (Y, B, d2, True)):
                    legs.append({"a": a, "b": b, "km": km, "south": bool({a, b} & SOUTH),
                                 "competitive": D.has_direct(a, b), "dem": D.get(a, b, scen) / (2 * W)})
                tri.append((B, X, Y, legs))

    def tri_eval(B, X, Y, legs):
        # одна частота на весь треугольник: по самому загруженному плечу, от 3 до 7
        f = A["min_freq_week"]
        for _ in range(2):
            pax = [L["dem"] * leg_share(L, f, A) for L in legs]
            f = int(min(7, max(A["min_freq_week"], math.ceil(max(pax) / (A["seats"] * A["lf_max"])))))
        hours = cost = rev = seg = 0.0
        out = []
        for L, p in zip(legs, pax):
            carried = min(p, f * A["seats"] * A["lf_max"])
            bh, c = leg_cost(A, L["km"], L["south"], carried / f)
            hours += 2 * f * bh
            cost += 2 * f * c
            rev += 2 * carried * fare(A, L["km"])
            seg += 2 * carried
            out.append(dict(L, freq=f, carried_dir_week=carried, block_h=bh, lf=carried / (f * A["seats"])))
        return hours, cost, rev, seg, out

    scored = []
    for B, X, Y, legs in tri:
        h, c, r, s, out = tri_eval(B, X, Y, legs)
        scored.append(((r - c) / h, B, X, Y, h, c, r, s, out))
    scored.sort(key=lambda x: -x[0])
    chosen, used_pairs, H = [], set(), 0.0
    for sc in scored:
        _, B, X, Y, h, c, r, s, out = sc
        if (X, Y) in used_pairs or H + h > max_h:
            continue
        if sc[0] <= 0 and len(chosen) >= 8:
            break
        chosen.append(sc)
        used_pairs.add((X, Y))
        H += h
        if len(chosen) >= A["max_routes"]:
            break
    return chosen


def kover_map():
    """Дни «Ковра» за 365 дней по аэропортам; Москва — худший из трёх аэропортов."""
    k = pd.read_csv(P / "kover_days.csv").set_index("iata").last365_days
    m = k.to_dict()
    m["MOW"] = int(max(k.get(x, 0) for x in ("SVO", "DME", "VKO")))
    return m


def kover_avg(legs_freq, K):
    """Средние дни «Ковра» по концам рейсов, взвешенные числом рейсов; аэропорт без данных = 0."""
    tot = w = 0.0
    for a, b, f in legs_freq:
        tot += f * (K.get(a, 0) + K.get(b, 0)) / 2
        w += f
    return round(tot / w) if w else 0


def range_light(a, b, km):
    """Светофор дальности docs/17 для SSJ/SJ-100 по расстоянию по прямой."""
    south = bool({a, b} & SOUTH)
    green = 2150 if south else 2300
    if km <= green:
        return "зелёный" + (" (юг, порог 2 150 км)" if south else "")
    if km <= 2900:
        return "жёлтый: SSJ на пределе, нужен Ту-204/214"
    return "красный: только Ту-214"


FREQ_METHOD = ("расчёт: захваченные пассажиры в неделю / (100 кресел × загрузка 85%), "
               "не реже 3 и не чаще 14 рейсов в неделю (data/assumptions/network.csv)")


def main():
    AS = load_assumptions()
    D = Demand()
    K = kover_map()
    ll = pd.read_csv(P / "longlist.csv")
    nodes_all = [x for x in D.n.index]
    scores = pd.read_csv(P / "longlist_scores_min500.csv")
    hubs = list(scores.sort_values("rank").iata.head(3)) + ["GOJ", "UFA"]  # топ-3 лонглиста + варианты коллег
    routes, summary = [], []
    for scen, A in AS.items():
        W = A["weeks_per_year"]
        for H in hubs:
            chosen, r = hub_network(H, D, A, scen, nodes_all)
            legs, trans, hours, cost, rev, od_l, od_t, flights = r
            ac = math.ceil(hours / (A["block_h_per_day"] * 7)) + A["spare_aircraft"]
            seg = sum(2 * L["carried_dir_week"] for L in legs.values())
            summary.append({"scenario": scen, "variant": f"Хаб {ll.set_index('iata').city.get(H, H)}", "hub": H,
                            "routes": len(chosen), "aircraft": int(ac), "flights_week": int(flights),
                            "segments_year": round(seg * W), "od_trips_year": round((od_l + od_t) * W),
                            "transfer_od_year": round(od_t * W), "revenue_mln_year": round(rev * W / 1e6),
                            "var_cost_mln_year": round(cost * W / 1e6), "result_mln_year": round((rev - cost) * W / 1e6),
                            "share_pp": round(seg * W / A["market_pax_2025"] * 100, 2),
                            "kover_days_avg": kover_avg([(L["a"], L["b"], L["freq"]) for L in legs.values()], K)})
            for L in legs.values():
                routes.append({"scenario": scen, "variant": f"Хаб {H}", "from": H, "to": L["b"],
                               "to_city": NAME.get(L["b"], D.n.loc[L["b"], "main_city"]), "km": round(L["km"]),
                               "freq_week_each_way": L["freq"], "pax_year_local": round(2 * L["local_carried"] * W),
                               "pax_year_segments": round(2 * L["carried_dir_week"] * W), "load_factor": round(L["lf"], 2),
                               "demand_source": D.method(H, L["b"]), "direct_now": D.has_direct(H, L["b"]),
                               "range_light": range_light(H, L["b"], L["km"])})
        chosen = direct_network(D, A, scen, nodes_all)
        hours = sum(c[4] for c in chosen)
        cost = sum(c[5] for c in chosen)
        rev = sum(c[6] for c in chosen)
        seg = sum(c[7] for c in chosen)
        ac = math.ceil(hours / (A["block_h_per_day"] * 7)) + A["spare_aircraft"]
        flights = sum(2 * L["freq"] for c in chosen for L in c[8])
        summary.append({"scenario": scen, "variant": "Прямые рейсы из Москвы и Екатеринбурга", "hub": "",
                        "routes": len(chosen), "aircraft": int(ac), "flights_week": int(flights),
                        "segments_year": round(seg * W), "od_trips_year": round(seg * W), "transfer_od_year": 0,
                        "revenue_mln_year": round(rev * W / 1e6), "var_cost_mln_year": round(cost * W / 1e6),
                        "result_mln_year": round((rev - cost) * W / 1e6), "share_pp": round(seg * W / A["market_pax_2025"] * 100, 2),
                        "kover_days_avg": kover_avg([(L["a"], L["b"], L["freq"]) for c in chosen for L in c[8]], K)})
        for c in chosen:
            for L in c[8]:
                routes.append({"scenario": scen, "variant": f"Прямые {c[1]}-{c[2]}-{c[3]}", "from": L["a"], "to": L["b"],
                               "to_city": f"{NAME.get(L['a'], D.n.loc[L['a'], 'main_city'])} — {NAME.get(L['b'], D.n.loc[L['b'], 'main_city'])}",
                               "km": round(L["km"]), "freq_week_each_way": L["freq"], "pax_year_local": round(2 * L["carried_dir_week"] * W),
                               "pax_year_segments": round(2 * L["carried_dir_week"] * W), "load_factor": round(L["lf"], 2),
                               "demand_source": D.method(L["a"], L["b"]), "direct_now": D.has_direct(L["a"], L["b"]),
                               "range_light": range_light(L["a"], L["b"], L["km"])})
    sm = pd.DataFrame(summary)
    rt = pd.DataFrame(routes)
    rt.to_csv(P / "network_routes.csv", index=False, encoding="utf-8")
    # обязательная таблица кейса: маршрут · пассажиров в год · рейсов в неделю · источник
    b = rt[rt.scenario == "base"].copy()
    c = rt[rt.scenario == "cautious"].set_index(["variant", "from", "to"]).pax_year_segments
    b["pax_cautious"] = [c.get((r.variant, r["from"], r.to)) for _, r in b.iterrows()]
    b["route"] = [f"{NAME.get(r['from'], D.n.loc[r['from'], 'main_city'])} — {NAME.get(r.to, D.n.loc[r.to, 'main_city'])}"
                  for _, r in b.iterrows()]
    mt = b[["variant", "route", "km", "pax_year_segments", "pax_cautious", "freq_week_each_way", "load_factor",
            "direct_now", "range_light", "demand_source"]].rename(columns={"range_light": "Светофор дальности SSJ (docs/17)",
        "variant": "Вариант", "route": "Маршрут", "km": "Км", "pax_year_segments": "Пассажиров в год (база)",
        "pax_cautious": "Пассажиров в год (осторожно)", "freq_week_each_way": "Рейсов в неделю в одну сторону",
        "load_factor": "Загрузка", "direct_now": "Прямой рейс уже есть", "demand_source": "Откуда спрос пары"})
    mt["Откуда частота"] = FREQ_METHOD
    mt.to_csv(P / "mandatory_routes_table.csv", index=False, encoding="utf-8")
    sm.to_csv(P / "network_summary.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(sm.drop(columns=["hub"]).to_string(index=False))


if __name__ == "__main__":
    main()
