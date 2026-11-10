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

Спрос пары — поездки «откуда — куда» из шага 2 (гипотеза Н1, docs/19): сначала сводная оценка
data/processed/demand_estimates.csv, затем data/processed/od_pairs.csv, для пар без нынешнего авиамаршрута —
та же формула поездок (src/od_model.py). Сегменты на рейсе (с пересадочными чужих сетей) нужны только чтобы
оценить частоту конкурентов. В базовом сценарии базовая оценка, в осторожном — осторожная.
Нынешние пассажиры Red Wings на паре (data/manual/rw_routes_now.csv) — не новые: они пересаживаются со старого
рейса Red Wings на новый. Их выручку вычитаем, в прирост доли рынка они не входят (как у коллег, context/12).
Все допущения — data/assumptions/network.csv.
Результат до расходов на аренду самолётов, базу и офис (как у коллег, context/12_network_economics).

Выход: data/processed/network_routes.csv (каждый маршрут), network_summary.csv (итоги по вариантам)
Запуск: python src/network_model.py
"""
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import demand_model as dm
import rules
from airports_meta import CLOSED, NAME

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"


def load_assumptions():
    """Четыре сценария: база и осторожно, каждый без субсидии и с субсидией (сеть набирается заново)."""
    a = pd.read_csv(ROOT / "data/assumptions/network.csv")
    out = {}
    for s in ("base", "cautious"):
        A = dict(zip(a.parameter, a[s].astype(float)))
        out[s] = dict(A, use_subsidy=0.0, demand_scen=s)
        out[s + "_sub"] = dict(A, use_subsidy=1.0, demand_scen=s)
    return out


SUB_HUBS = set(pd.read_csv(ROOT / "data/assumptions/subsidy_hub_airports.csv").iata)
_SFE = pd.read_csv(ROOT / "data/assumptions/siberia_fareast_regions.csv")
SIB_FE, FAR_EAST = set(_SFE.region), set(_SFE[_SFE.district == "Дальневосточный"].region)
SUB_CAP = pd.read_csv(ROOT / "data/assumptions/subsidy_cap_84_103.csv").sort_values("min_km")
_fs = pd.read_csv(ROOT / "data/raw/favt_subsidy_2026.csv", dtype=str)
_SUB_HELD = {}   # пара → перевозчики, за которыми маршрут закреплён в перечне 2026


def _load_held(D):
    if _SUB_HELD:
        return
    c2i = {}
    for i, r in D.n.iterrows():
        c2i.setdefault(str(r.main_city), i)
    for i, nm_ in NAME.items():
        c2i.setdefault(nm_, i)
    for r in _fs.itertuples():
        a, b = c2i.get(r.origin), c2i.get(r.destination)
        if a and b:
            _SUB_HELD.setdefault(frozenset((a, b)), set()).add(str(r.airline))


def sub_rule(D, A, a, b):
    """Подходит ли пара под программу межрегиональных перевозок (решение Росавиации № 22-64160-00191-Р)
    и сколько платят за рейс. Пустая строка причины — подходит.
    Правила: не Москва; один конец — узловой аэропорт, другой — нет; дальность до 1 500 км (Сибирь и
    Дальний Восток — до 3 000); поток пары за прошлый год не больше 8 тыс. (Дальний Восток — 10 тыс.),
    поэтому сценарий описывает первый год новой пары; маршрут не закреплён за другим перевозчиком.
    Ставка — средняя по программе за рейс, не выше потолка по дальности; только 7 месяцев (без мая — сентября)."""
    _load_held(D)
    if "MOW" in (a, b):
        return 0.0, "Москва"
    if (a in SUB_HUBS) == (b in SUB_HUBS):
        return 0.0, "нужен один узловой аэропорт"
    ra, rb = D.n.loc[a, "region"], D.n.loc[b, "region"]
    km = D.km(a, b)
    lim = A["subsidy_max_km_sib"] if (ra in SIB_FE or rb in SIB_FE) else A["subsidy_max_km"]
    if km > lim:
        return 0.0, f"дальше {lim:.0f} км"
    prior = D.seg_tab.get((a, b), 0.0) if D.has_direct(a, b) else 0.0
    thr = A["subsidy_max_prior_pax_fe"] if (ra in FAR_EAST or rb in FAR_EAST) else A["subsidy_max_prior_pax"]
    if prior > thr:
        return 0.0, f"поток пары больше {thr:.0f} пасс. в год"
    held = {x for x in _SUB_HELD.get(frozenset((a, b)), set()) if "Ред Вингс" not in x and "Red Wings" not in x}
    if held:
        return 0.0, "закреплён за другим перевозчиком"
    cap = float(SUB_CAP[SUB_CAP.min_km <= km].iloc[-1].cap_rub_per_oneway_flight)
    return min(A["subsidy_rub_per_flight"], cap) * A["subsidy_months"] / 12, ""


def sub(D, A, a, b):
    """Субсидия за один рейс плеча в среднем за год (с учётом месяцев без субсидии); 0, если не подходит."""
    if not A["use_subsidy"]:
        return 0.0
    return sub_rule(D, A, a, b)[0]


class Demand:
    """Спрос пары за год, оба направления, в поездках «откуда — куда» (шаг 2)."""

    def __init__(self):
        self.n = dm.nodes()
        self.direct, self.rail = dm.links()
        fit = json.loads((P / "od_fit.json").read_text(encoding="utf-8"))
        co = fit["coefficients"]
        self.feats = [k for k in co if k != "const"]
        self.beta = np.array([co["const"]] + [co[k] for k in self.feats])
        self.f_lo = fit["cautious_factor"]
        self.tab, self.seg_tab = {}, {}
        od = pd.read_csv(P / "od_pairs.csv")
        for r in od.itertuples():
            v = {"base": float(r.od_base), "cautious": float(r.od_cautious),
                 "method": ("Модель поездок по потокам на рейсах" + ("" if r.route == "прямой рейс" else ", сейчас " + r.route.replace("с пересадкой:", "с пересадкой в городе")))}
            self.tab[(r.a, r.b)] = self.tab[(r.b, r.a)] = v
            if pd.notna(r.segments_on_link):
                self.seg_tab[(r.a, r.b)] = self.seg_tab[(r.b, r.a)] = float(r.segments_on_link)
        # сводная оценка шага 2 (пять оценок, сверка с аэропортами и расписанием) — главнее
        est = pd.read_csv(P / "demand_estimates.csv")
        for r in est[est.od_base.notna()].itertuples():
            v = {"base": float(r.od_base), "cautious": float(r.od_cautious), "method": self.describe(r)}
            self.tab[(r.a, r.b)] = self.tab[(r.b, r.a)] = v
            if bool(r.direct_now) and pd.notna(r.segments_base):
                self.seg_tab[(r.a, r.b)] = self.seg_tab[(r.b, r.a)] = float(r.segments_base)
        self.cache = {}

    def describe(self, r):
        """Понятная запись, откуда взят спрос пары (обязательное требование кейса)."""
        nz = lambda v: v is not None and v == v
        if nz(r.observed):
            seg = "отчёт аэропорта о потоке пары за 2025 год"
        else:
            parts = []
            if nz(r.seg_model):
                parts.append("модель тяготения")
            if nz(r.seg_analog):
                cn = lambda c: NAME.get(c, self.n.loc[c, "main_city"] if c in self.n.index else c)
                ap = re.sub(r"[A-Z]{3}", lambda m: cn(m.group(0)), r.analog_pairs) if isinstance(r.analog_pairs, str) else ""
                parts.append(f"похожие пары ({ap})" if ap else "похожие пары")
            if nz(r.seg_schedule):
                parts.append("кресла в расписании 7–13.12.2026")
            seg = ("среднее оценок: " if len(parts) > 1 else "") + ", ".join(parts)
            if bool(r.uncertain):
                seg += f"; оценки расходятся в {str(round(float(r.estimates_ratio), 1)).replace('.', ',')} раза — неуверенно"
        if bool(r.direct_now):
            share = f" × доля своих поездок {round(float(r.own_trips_share) * 100)}%" if nz(r.own_trips_share) else ""
            t = f"{seg}{share}"
            return t[0].upper() + t[1:] if seg else "Модель поездок"
        via = str(r.od_route_now).replace("с пересадкой: ", "") if isinstance(r.od_route_now, str) else ""
        return (f"Поездки, которые сейчас идут с пересадкой в городе {via}: модель поездок по потокам на рейсах"
                if via and via != "nan" else "Модель поездок по потокам на рейсах")

    def _formula(self, a, b):
        key = (min(a, b), max(a, b))
        if key not in self.cache:
            f = dm.features(self.n, a, b, self.rail)
            self.cache[key] = float(np.exp(self.beta[0] + sum(c * f[k] for c, k in zip(self.beta[1:], self.feats))))
        return self.cache[key]

    def get(self, a, b, scen):
        if (a, b) in self.tab:
            return self.tab[(a, b)][scen]
        v = self._formula(a, b)
        return v if scen == "base" else v * self.f_lo

    def seg(self, a, b, scen):
        """Сегменты на нынешнем прямом рейсе (для частоты конкурентов); без данных — поездки пары."""
        s_ = self.seg_tab.get((a, b))
        if s_ is None:
            return self.get(a, b, scen)
        return s_ if scen == "base" else s_ * self.get(a, b, "cautious") / max(self.get(a, b, "base"), 1)

    def method(self, a, b):
        return self.tab.get((a, b), {}).get(
            "method", "Формула спроса из модели поездок: сейчас авиамаршрута между городами нет")

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


RW_NOW = pd.read_csv(ROOT / "data/manual/rw_routes_now.csv")
RW_FREQ = {frozenset((r.a, r.b)): float(r.freq_week_each_way) for r in RW_NOW.itertuples()}


def rw_pax_week(a, b, A):
    """Пассажиров Red Wings на паре сейчас, в неделю в одну сторону: рейсы × кресла × загрузка Red Wings."""
    return RW_FREQ.get(frozenset((a, b)), 0.0) * A["seats"] * A["rw_existing_lf"]


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
        f_comp = L.get("seg", L["dem"]) / (A["seats"] * A["competitor_lf"])
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
                       "seg": D.seg(H, X, scen) / (2 * W), "competitive": D.has_direct(H, X),
                       "rw_now": rw_pax_week(H, X, A)}
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
        hours = cost = flights = rev = migr = forgone = subs = 0.0
        for X in S:
            L = legs[X]
            bh, c = leg_cost(A, L["km"], L["south"], carried[X] / f[X])
            mg = min(loc_c[X], L["rw_now"])             # свои пассажиры Red Wings со старого рейса
            L.update(freq=f[X], local_carried=loc_c[X], transfer_carried=carried[X] - loc_c[X],
                     carried_dir_week=carried[X], block_h=bh, lf=carried[X] / (f[X] * A["seats"]), migrated=mg)
            hours += 2 * f[X] * bh
            cost += 2 * f[X] * c
            flights += 2 * f[X]
            rev += 2 * loc_c[X] * fare(A, L["km"])
            migr += 2 * mg
            forgone += 2 * mg * fare(A, L["km"])
            subs += 2 * f[X] * sub(D, A, H, X)              # платят за выполненный рейс (п. 6 решения)
        for X, Y, dxy, t in tr_c:
            rev += 2 * t * fare(A, dxy) * A["transfer_fare_factor"]
        od_local = 2 * sum(loc_c.values())            # поездок в неделю, оба направления
        od_transfer = 2 * sum(t for *_, t in tr_c)
        seg = 2 * sum(carried.values())               # сегментов в неделю, оба направления
        assert abs(seg - (od_local + 2 * od_transfer)) < 1e-6, "сегменты не сходятся с поездками"
        # выручка — чистая: доход, который Red Wings теряет на старом рейсе, вычтен
        return legs, tr_c, hours, cost, rev - forgone + subs, od_local, od_transfer, flights, migr, forgone, subs

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


def search_caps(A):
    """Лимиты самолётов для перебора (проверка 1 Миши, 10.11.2026): жадный отбор при большом лимите может
    собрать сеть хуже, чем при меньшем. Считаем сеть при каждом лимите и берём лучшую из тех, где маршрутов
    не меньше минимума."""
    lo, step, hi = int(A["fleet_search_min"]), max(int(A["fleet_search_step"]), 1), int(A["fleet_cap"])
    return sorted(set(range(min(lo, hi), hi + 1, step)) | {hi})


def best_of(results, A):
    ok = [r for r in results if r[0] >= A["min_routes"]]
    pool = ok or results
    return max(pool, key=lambda r: (r[1], -r[2]))


def hub_best(H, D, A, scen, nodes_all):
    res = []
    for cap in search_caps(A):
        ch, r = hub_network(H, D, dict(A, fleet_cap=float(cap)), scen, nodes_all)
        res.append((len(ch), (r[4] - r[3]), r[2], ch, r))
    b = best_of(res, A)
    return b[3], b[4]


def direct_best(D, A, scen, nodes_all):
    res = []
    for cap in search_caps(A):
        ch = direct_network(D, dict(A, fleet_cap=float(cap)), scen, nodes_all)
        res.append((len(ch), sum(c[6] - c[5] for c in ch), sum(c[4] for c in ch), ch))
    return best_of(res, A)[3]


def direct_network(D, A, scen, nodes_all):
    W = A["weeks_per_year"]
    bases = rules.BASES
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
                                 "competitive": D.has_direct(a, b), "dem": D.get(a, b, scen) / (2 * W),
                                 "seg": D.seg(a, b, scen) / (2 * W), "rw_now": rw_pax_week(a, b, A)})
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

    # Общий спрос физической пары (аудит коллег, B3 в context/18_team_sync/step1_review): если пара
    # Москва — Омск входит в несколько треугольников, доля рынка считается один раз от суммы их частот,
    # а перевезённые делятся между треугольниками пропорционально частотам.
    def joint(sel):
        agg = {}
        for t, (B, X, Y, f, legs) in enumerate(sel):
            for n, L in enumerate(legs):
                g = agg.setdefault(frozenset((L["a"], L["b"])), {"L": L, "F": 0, "members": []})
                g["F"] += f
                g["members"].append((t, n, f))
        carried, migrated = {}, {}
        for g in agg.values():
            L, F = g["L"], g["F"]
            tot = min(L["dem"] * leg_share(L, F, A), F * A["seats"] * A["lf_max"])
            mg = min(tot, L["rw_now"])                  # свои пассажиры Red Wings один раз на пару
            for t, n, f in g["members"]:
                carried[(t, n)] = tot * f / F
                migrated[(t, n)] = mg * f / F
        res = []
        for t, (B, X, Y, f, legs) in enumerate(sel):
            hours = cost = rev = seg = migr = forgone = subs = 0.0
            out = []
            for n, L in enumerate(legs):
                c_ = carried[(t, n)]
                mg = migrated[(t, n)]
                bh, c = leg_cost(A, L["km"], L["south"], c_ / f)
                hours += 2 * f * bh
                cost += 2 * f * c
                rev += 2 * (c_ - mg) * fare(A, L["km"])
                seg += 2 * c_
                migr += 2 * mg
                forgone += 2 * mg * fare(A, L["km"])
                s_ = 2 * f * sub(D, A, L["a"], L["b"])   # за выполненный рейс
                subs += s_
                rev += s_
                out.append(dict(L, freq=f, carried_dir_week=c_, block_h=bh, lf=c_ / (f * A["seats"]), migrated=mg))
            res.append(((rev - cost) / hours if hours else 0, B, X, Y, hours, cost, rev, seg, out, migr, forgone, subs))
        return res

    def totals(res):
        return sum(r[6] - r[5] for r in res), sum(r[4] for r in res)

    # кандидаты: лучшие треугольники по отдельной оценке; дальше жадный отбор по приросту всей сети
    pre = []
    for B, X, Y, legs in tri:
        h, c, r, s_, out = tri_eval(B, X, Y, legs)
        pre.append(((r - c) / h, B, X, Y, out[0]["freq"], legs))
    pre.sort(key=lambda x: -x[0])
    pre = pre[:int(A["direct_candidates"])]
    sel, used_pairs, cur = [], set(), (0.0, 0.0)
    while len(sel) < A["max_routes"]:
        best = None
        for sc, B, X, Y, f, legs in pre:
            if (X, Y) in used_pairs:
                continue
            res = joint(sel + [(B, X, Y, f, legs)])
            m, h = totals(res)
            if h > max_h:
                continue
            gain, dh = m - cur[0], h - cur[1]
            score = gain / dh if dh > 0 else -1e18
            if best is None or score > best[0]:
                best = (score, (B, X, Y, f, legs), (m, h))
        if best is None or (best[0] <= 0 and len(sel) >= A["min_routes"]):
            break
        sel.append(best[1])
        used_pairs.add((best[1][1], best[1][2]))
        cur = best[2]
    return joint(sel)


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


def money(rev, cost, forgone, migr, seg, od, W, A, subs=0.0):
    """Деньги и доля за год. rev — чистая выручка (доход старых рейсов Red Wings уже вычтен).
    Прирост доли — только новые для Red Wings пассажиры (сегменты минус перешедшие со старых рейсов).
    Безубыточность: на сколько процентов выше должны быть все тарифы или какая доплата нужна на поездку,
    чтобы покрыть переменные расходы (без аренды самолётов и базы)."""
    gap = cost - rev
    fare_rev = rev - subs                               # выручка от билетов без субсидии
    return {"revenue_mln_year": round(rev * W / 1e6), "subsidy_mln_year": round(subs * W / 1e6), "var_cost_mln_year": round(cost * W / 1e6),
            "result_mln_year": round((rev - cost) * W / 1e6), "rw_migrated_year": round(migr * W),
            "rw_forgone_mln_year": round(forgone * W / 1e6), "net_new_segments_year": round((seg - migr) * W),
            "share_pp": round((seg - migr) * W / A["market_pax_2025"] * 100, 2),
            "share_pp_gross": round(seg * W / A["market_pax_2025"] * 100, 2),
            "fare_up_to_breakeven_pct": round((cost - subs) / fare_rev * 100 - 100) if fare_rev > 0 else None,
            "subsidy_rub_per_trip": round(gap / od) if od > 0 and gap > 0 else 0}


def main():
    AS = load_assumptions()
    D = Demand()
    K = kover_map()
    ll = pd.read_csv(P / "longlist.csv")
    nodes_all = [x for x in D.n.index]
    scores = pd.read_csv(P / "longlist_scores_min500.csv")
    extra = pd.read_csv(ROOT / "data/assumptions/hub_candidates_extra.csv").iata.tolist()
    main_hubs = list(dict.fromkeys(list(scores.sort_values("rank").iata.head(3)) + extra))  # топ-3 + варианты команды
    # сеть хаба считается для каждого города лонглиста: на панели её видно для города, выбранного на табло
    hubs = list(dict.fromkeys(main_hubs + [x for x in ll.iata if x in D.n.index and x not in CLOSED]))
    routes, summary = [], []
    for scen, A in AS.items():
        W = A["weeks_per_year"]
        for H in hubs:
            t0 = time.time()
            chosen, r = hub_best(H, D, A, A["demand_scen"], nodes_all)
            print(f"{scen} {H}: {time.time() - t0:.1f} с", file=sys.stderr, flush=True)
            legs, trans, hours, cost, rev, od_l, od_t, flights, migr, forgone, subs = r
            ac = math.ceil(hours / (A["block_h_per_day"] * 7)) + A["spare_aircraft"]
            seg = sum(2 * L["carried_dir_week"] for L in legs.values())
            kv, kcov = kover_avg([(L["a"], L["b"], L["freq"]) for L in legs.values()], K)
            summary.append({"scenario": scen, "variant": f"Хаб {ll.set_index('iata').city.get(H, H)}", "hub": H, "main": H in main_hubs,
                            "routes": len(chosen), "aircraft": int(ac), "flights_week": int(flights),
                            "segments_year": round(seg * W), "od_trips_year": round((od_l + od_t) * W),
                            "transfer_od_year": round(od_t * W), **money(rev, cost, forgone, migr, seg, od_l + od_t, W, A, subs),
                            "kover_days_avg": kv, "kover_coverage": kcov,
                            "check_segments_minus_od": round((seg - (od_l + 2 * od_t)) * W, 6)})
            for L in legs.values():
                routes.append({"scenario": scen, "variant": f"Хаб {H}", "from": H, "to": L["b"],
                               "to_city": NAME.get(L["b"], D.n.loc[L["b"], "main_city"]), "km": round(L["km"]),
                               "freq_week_each_way": L["freq"], "pax_year_local": round(2 * L["local_carried"] * W),
                               "pax_year_transfer_seg": round(2 * L["transfer_carried"] * W),
                               "pax_year_segments": round(2 * L["carried_dir_week"] * W), "load_factor": round(L["lf"], 2),
                               "pax_year_rw_migrated": round(2 * L["migrated"] * W),
                               "demand_source": D.method(H, L["b"]), "direct_now": D.has_direct(H, L["b"]),
                               "subsidy_rule": sub_rule(D, A, H, L["b"])[1] or "подходит",
                               "range_light": range_light(D, H, L["b"], L["km"])})
        chosen = direct_best(D, A, A["demand_scen"], nodes_all)
        hours = sum(c[4] for c in chosen)
        cost = sum(c[5] for c in chosen)
        rev = sum(c[6] for c in chosen)
        seg = sum(c[7] for c in chosen)
        migr = sum(c[9] for c in chosen)
        forgone = sum(c[10] for c in chosen)
        subs = sum(c[11] for c in chosen)
        ac = math.ceil(hours / (A["block_h_per_day"] * 7)) + A["spare_aircraft"]
        flights = sum(2 * L["freq"] for c in chosen for L in c[8])
        kv, kcov = kover_avg([(L["a"], L["b"], L["freq"]) for c in chosen for L in c[8]], K)
        summary.append({"scenario": scen, "variant": "Прямые рейсы из Москвы и Екатеринбурга", "hub": "", "main": True,
                        "routes": len(chosen), "aircraft": int(ac), "flights_week": int(flights),
                        "segments_year": round(seg * W), "od_trips_year": round(seg * W), "transfer_od_year": 0,
                        **money(rev, cost, forgone, migr, seg, seg, W, A, subs),
                        "kover_days_avg": kv, "kover_coverage": kcov, "check_segments_minus_od": 0.0})
        for c in chosen:
            for L in c[8]:
                routes.append({"scenario": scen, "variant": f"Прямые {c[1]}-{c[2]}-{c[3]}", "from": L["a"], "to": L["b"],
                               "to_city": f"{NAME.get(L['a'], D.n.loc[L['a'], 'main_city'])} — {NAME.get(L['b'], D.n.loc[L['b'], 'main_city'])}",
                               "km": round(L["km"]), "freq_week_each_way": L["freq"], "pax_year_local": round(2 * L["carried_dir_week"] * W),
                               "pax_year_segments": round(2 * L["carried_dir_week"] * W), "load_factor": round(L["lf"], 2),
                               "pax_year_rw_migrated": round(2 * L["migrated"] * W),
                               "demand_source": D.method(L["a"], L["b"]), "direct_now": D.has_direct(L["a"], L["b"]),
                               "subsidy_rule": sub_rule(D, A, L["a"], L["b"])[1] or "подходит",
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
    # Шаг 4: как сеть выбранного хаба растёт по мере поставок самолётов (data/assumptions/choice.csv)
    ch = pd.read_csv(ROOT / "data/assumptions/choice.csv").set_index("parameter").value
    H = ch["chosen_hub"]
    ramp = []
    for scen, A0 in AS.items():
        for cap in [int(x) for x in str(ch["ramp_fleet"]).split(";")]:
            A = dict(A0, fleet_cap=float(cap))
            chosen, r = hub_network(H, D, A, A["demand_scen"], nodes_all)
            legs, trans, hours, cost, rev, od_l, od_t, flights, migr, forgone, subs = r
            W = A["weeks_per_year"]
            seg = sum(2 * L["carried_dir_week"] for L in legs.values())
            ramp.append({"scenario": scen, "hub": H, "fleet_cap": cap,
                         "aircraft": int(math.ceil(hours / (A["block_h_per_day"] * 7)) + A["spare_aircraft"]),
                         "routes": len(chosen), "segments_year": round(seg * W), "transfer_od_year": round(od_t * W),
                         "result_mln_year": round((rev - cost) * W / 1e6), "subsidy_mln_year": round(subs * W / 1e6),
                         "share_pp": round((seg - migr) * W / A["market_pax_2025"] * 100, 2),
                         "spokes": ";".join(chosen)})
    pd.DataFrame(ramp).to_csv(P / "fleet_ramp.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(sm.drop(columns=["hub"]).to_string(index=False))


if __name__ == "__main__":
    main()
