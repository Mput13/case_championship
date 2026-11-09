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
import rules
from airports_meta import CLOSED, NAME

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"


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

    def south(self, a, b):
        """Пара с обходами (k_трассы 1,20): хотя бы один конец в регионе юга/запада (docs/17)."""
        return rules.is_south(self.n.loc[a, "region"]) or rules.is_south(self.n.loc[b, "region"])

    def green(self, a, b):
        return rules.green_limit(self.n.loc[a, "region"], self.n.loc[b, "region"])


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
        f_comp = L["dem"] / (A["seats"] * A["competitor_lf"])
        return min(A["capture_competitive"], f / (f + f_comp)) if f_comp > 0 else 0.0
    return capture(A["capture_open"], f, A)


def freq_for(pax_week_dir, A):
    need = math.ceil(pax_week_dir / (A["seats"] * A["lf_max"])) if pax_week_dir > 0 else 0
    return int(min(A["max_freq_week"], max(A["min_freq_week"], need)))


def hub_network(H, D, A, scen, cand_nodes):
    """Сеть из хаба H. Потоки считаются один раз из общей таблицы поездок (местные и пересадочные),
    чтобы выполнялось тождество: сегменты = местные поездки + 2 × пересадочные (аудит критика front2272)."""
    W = A["weeks_per_year"]
    spokes = []
    for X in cand_nodes:
        if X == H or X in CLOSED:
            continue
        km = D.km(H, X)
        if km > D.green(H, X) or km < A["spoke_min_km"]:
            continue
        spokes.append(X)

    def build(S):
        legs = {}
        for X in S:
            km = D.km(H, X)
            loc = D.get(H, X, scen) / (2 * W)          # поездок в неделю в одну сторону, весь рынок пары
            legs[X] = {"a": H, "b": X, "km": km, "south": D.south(H, X), "local": loc, "dem": loc,
                       "competitive": D.has_direct(H, X)}
        trans = []                                      # пересадочные пары X — H — Y
        for i, X in enumerate(S):
            for Y in S[i + 1:]:
                dxy = D.km(X, Y)
                if dxy < A["transfer_min_km"] or D.has_direct(X, Y) or X in CLOSED or Y in CLOSED:
                    continue
                if (D.km(H, X) + D.km(H, Y)) / dxy > A["transfer_max_circuity"]:
                    continue
                trans.append((X, Y, dxy, D.get(X, Y, scen) / (2 * W) * A["capture_transfer"]))

        def flows(f):
            loc = {X: legs[X]["local"] * leg_share(legs[X], f[X], A) for X in S}
            tr = [(X, Y, dxy, t * (1 - math.exp(-min(f[X], f[Y]) / A["capture_freq_scale"])))
                  for X, Y, dxy, t in trans]
            return loc, tr

        # частоты: неподвижная точка. Спрос растёт с частотой, частота — со спросом, поэтому
        # последовательность от минимальной частоты не убывает и останавливается не позже max_freq_week
        f = {X: int(A["min_freq_week"]) for X in S}
        for _ in range(100):
            loc, tr = flows(f)
            want = dict(loc)
            for X, Y, _, t in tr:
                want[X] += t
                want[Y] += t
            nf = {X: freq_for(want[X], A) for X in S}
            if nf == f:
                break
            f = nf
        # финальные потоки при итоговых частотах; ограничение кресел — на общие поездки:
        # пересадочная поездка урезается по самому загруженному из двух своих плеч
        loc, tr = flows(f)
        load = dict(loc)
        for X, Y, _, t in tr:
            load[X] += t
            load[Y] += t
        sc = {X: min(1.0, f[X] * A["seats"] * A["lf_max"] / load[X]) if load[X] > 0 else 1.0 for X in S}
        loc_c = {X: loc[X] * sc[X] for X in S}
        tr_c = [(X, Y, dxy, t * min(sc[X], sc[Y])) for X, Y, dxy, t in tr]
        carried = dict(loc_c)
        for X, Y, _, t in tr_c:
            carried[X] += t
            carried[Y] += t
        hours = cost = flights = rev = 0.0
        for X in S:
            L = legs[X]
            bh, c = leg_cost(A, L["km"], L["south"], carried[X] / f[X])
            L.update(freq=f[X], local_carried=loc_c[X], transfer_carried=carried[X] - loc_c[X],
                     carried_dir_week=carried[X], block_h=bh, lf=carried[X] / (f[X] * A["seats"]))
            hours += 2 * f[X] * bh
            cost += 2 * f[X] * c
            flights += 2 * f[X]
            rev += 2 * loc_c[X] * fare(A, L["km"])
        for X, Y, dxy, t in tr_c:
            rev += 2 * t * fare(A, dxy) * A["transfer_fare_factor"]
        od_local = 2 * sum(loc_c.values())            # поездок в неделю, оба направления
        od_transfer = 2 * sum(t for *_, t in tr_c)
        seg = 2 * sum(carried.values())               # сегментов в неделю, оба направления
        assert abs(seg - (od_local + 2 * od_transfer)) < 1e-6, "сегменты не сходятся с поездками"
        return legs, tr_c, hours, cost, rev, od_local, od_transfer, flights

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
        if cand is None or (cand[0] <= 0 and len(chosen) >= A["min_routes"]):
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
            if dxy > D.green(X, Y):
                continue
            for B in bases:
                d1, d2 = D.km(B, X), D.km(Y, B)
                if d1 > D.green(B, X) or d2 > D.green(Y, B):
                    continue
                if d1 + d2 > A["triangle_detour_factor"] * dxy + A["triangle_detour_add_km"]:
                    continue
                legs = []
                for a, b, km in ((B, X, d1), (X, Y, dxy), (Y, B, d2)):
                    legs.append({"a": a, "b": b, "km": km, "south": D.south(a, b),
                                 "competitive": D.has_direct(a, b), "dem": D.get(a, b, scen) / (2 * W)})
                tri.append((B, X, Y, legs))

    def tri_eval(B, X, Y, legs):
        # одна частота на весь треугольник по самому загруженному плечу; неподвижная точка,
        # затем спрос плеч пересчитывается при итоговой частоте (тот же дефект, что был в хабе)
        f = int(A["min_freq_week"])
        for _ in range(100):
            pax = [L["dem"] * leg_share(L, f, A) for L in legs]
            nf = int(min(A["direct_max_freq_week"],
                         max(A["min_freq_week"], math.ceil(max(pax) / (A["seats"] * A["lf_max"])))))
            if nf == f:
                break
            f = nf
        pax = [L["dem"] * leg_share(L, f, A) for L in legs]
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
        if sc[0] <= 0 and len(chosen) >= A["min_routes"]:
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
    """Средние дни «Ковра» по концам рейсов, взвешенные числом рейсов. Аэропорты без данных в среднее
    не входят (раньше считались как 0 — занижение); доля концов рейсов с данными возвращается отдельно."""
    tot = w = w_all = 0.0
    for a, b, f in legs_freq:
        for x in (a, b):
            w_all += f
            if x in K and pd.notna(K[x]):
                tot += f * K[x]
                w += f
    return (round(tot / w) if w else None), (round(w / w_all, 2) if w_all else None)


def range_light(D, a, b, km):
    """Светофор дальности docs/17 (src/rules.py)."""
    return rules.light(D.n.loc[a, "region"], D.n.loc[b, "region"], km)


def freq_method(A):
    return (f"расчёт: захваченные пассажиры в неделю / ({int(A['seats'])} кресел × загрузка {A['lf_max']:.0%}), "
            f"не реже {int(A['min_freq_week'])} и не чаще {int(A['max_freq_week'])} рейсов в неделю "
            "(data/assumptions/network.csv)")


def main():
    AS = load_assumptions()
    D = Demand()
    K = kover_map()
    ll = pd.read_csv(P / "longlist.csv")
    nodes_all = [x for x in D.n.index]
    scores = pd.read_csv(P / "longlist_scores_min500.csv")
    extra = pd.read_csv(ROOT / "data/assumptions/hub_candidates_extra.csv").iata.tolist()
    hubs = list(dict.fromkeys(list(scores.sort_values("rank").iata.head(3)) + extra))  # топ-3 + варианты команды
    routes, summary = [], []
    for scen, A in AS.items():
        W = A["weeks_per_year"]
        for H in hubs:
            chosen, r = hub_network(H, D, A, scen, nodes_all)
            legs, trans, hours, cost, rev, od_l, od_t, flights = r
            ac = math.ceil(hours / (A["block_h_per_day"] * 7)) + A["spare_aircraft"]
            seg = sum(2 * L["carried_dir_week"] for L in legs.values())
            kv, kcov = kover_avg([(L["a"], L["b"], L["freq"]) for L in legs.values()], K)
            summary.append({"scenario": scen, "variant": f"Хаб {ll.set_index('iata').city.get(H, H)}", "hub": H,
                            "routes": len(chosen), "aircraft": int(ac), "flights_week": int(flights),
                            "segments_year": round(seg * W), "od_trips_year": round((od_l + od_t) * W),
                            "transfer_od_year": round(od_t * W), "revenue_mln_year": round(rev * W / 1e6),
                            "var_cost_mln_year": round(cost * W / 1e6), "result_mln_year": round((rev - cost) * W / 1e6),
                            "share_pp": round(seg * W / A["market_pax_2025"] * 100, 2),
                            "kover_days_avg": kv, "kover_coverage": kcov,
                            "check_segments_minus_od": round((seg - (od_l + 2 * od_t)) * W, 6)})
            for L in legs.values():
                routes.append({"scenario": scen, "variant": f"Хаб {H}", "from": H, "to": L["b"],
                               "to_city": NAME.get(L["b"], D.n.loc[L["b"], "main_city"]), "km": round(L["km"]),
                               "freq_week_each_way": L["freq"], "pax_year_local": round(2 * L["local_carried"] * W),
                               "pax_year_transfer_seg": round(2 * L["transfer_carried"] * W),
                               "pax_year_segments": round(2 * L["carried_dir_week"] * W), "load_factor": round(L["lf"], 2),
                               "demand_source": D.method(H, L["b"]), "direct_now": D.has_direct(H, L["b"]),
                               "range_light": range_light(D, H, L["b"], L["km"])})
        chosen = direct_network(D, A, scen, nodes_all)
        hours = sum(c[4] for c in chosen)
        cost = sum(c[5] for c in chosen)
        rev = sum(c[6] for c in chosen)
        seg = sum(c[7] for c in chosen)
        ac = math.ceil(hours / (A["block_h_per_day"] * 7)) + A["spare_aircraft"]
        flights = sum(2 * L["freq"] for c in chosen for L in c[8])
        kv, kcov = kover_avg([(L["a"], L["b"], L["freq"]) for c in chosen for L in c[8]], K)
        summary.append({"scenario": scen, "variant": "Прямые рейсы из Москвы и Екатеринбурга", "hub": "",
                        "routes": len(chosen), "aircraft": int(ac), "flights_week": int(flights),
                        "segments_year": round(seg * W), "od_trips_year": round(seg * W), "transfer_od_year": 0,
                        "revenue_mln_year": round(rev * W / 1e6), "var_cost_mln_year": round(cost * W / 1e6),
                        "result_mln_year": round((rev - cost) * W / 1e6), "share_pp": round(seg * W / A["market_pax_2025"] * 100, 2),
                        "kover_days_avg": kv, "kover_coverage": kcov, "check_segments_minus_od": 0.0})
        for c in chosen:
            for L in c[8]:
                routes.append({"scenario": scen, "variant": f"Прямые {c[1]}-{c[2]}-{c[3]}", "from": L["a"], "to": L["b"],
                               "to_city": f"{NAME.get(L['a'], D.n.loc[L['a'], 'main_city'])} — {NAME.get(L['b'], D.n.loc[L['b'], 'main_city'])}",
                               "km": round(L["km"]), "freq_week_each_way": L["freq"], "pax_year_local": round(2 * L["carried_dir_week"] * W),
                               "pax_year_segments": round(2 * L["carried_dir_week"] * W), "load_factor": round(L["lf"], 2),
                               "demand_source": D.method(L["a"], L["b"]), "direct_now": D.has_direct(L["a"], L["b"]),
                               "range_light": range_light(D, L["a"], L["b"], L["km"])})
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
    mt["Откуда частота"] = freq_method(AS["base"])
    mt.to_csv(P / "mandatory_routes_table.csv", index=False, encoding="utf-8")
    sm.to_csv(P / "network_summary.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(sm.drop(columns=["hub"]).to_string(index=False))


if __name__ == "__main__":
    main()
