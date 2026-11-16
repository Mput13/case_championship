"""Собирает данные и интерактивный экран пошаговой анимации полётов хаба Омск (OMS).

Все частоты, дальности, блок-время, стартовое расписание, характеристики аэропортов,
конкуренты, тарифы и экономика лучей берутся из таблиц проекта:
  data/assumptions/network.csv
  data/processed/network_routes.csv, demand_estimates.csv, longlist.csv,
  data/processed/destinations.csv, kover_days.csv, airport_seasonality.csv, catchment_extra.csv
  data/manual/competitor_hubs.csv, airport_tech.csv, carrier_names.csv, rw_routes_now.csv
  data/raw/favt_subsidy_2026.csv
  data/external/colleagues/omsk_domestic_timetable_rows.csv, omsk_outbound_week_20261207.csv
  data/external/colleagues/route_product_cards.csv, p40_route_competitors_verified.csv
  data/external/colleagues/p39_omsk_prices.csv, oms_ramp_week_flights.csv, oms_ramp_connections.csv

Три режима в одном плеере:
  radial — радиальная сеть без убыточных фидеров KJA/BAX (7 стволов, 50 оборотов/нед., 5+1 ВС SJ-100)
  full   — полная хабовая сеть (9 лучей с фидерами BAX/KJA, 64 оборота/нед., 7+1 ВС SJ-100)
  start  — стартовая фаза из oms_ramp_week_flights.csv (6 направлений, 44 рейса/нед., 2+1 ВС SJ-100)

Запуск: python3 src/build_flight_animation.py
"""
import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OMS_TZ = timezone(timedelta(hours=6))
OMS_WEEK_ANCHOR = datetime(2027, 9, 6, 0, 0, tzinfo=OMS_TZ)
FEEDERS = ("BAX", "KJA")
TURN_MIN = 60
MAX_AC_WEEK_MIN = 70 * 60

TZ_OFFSET_H = {
    "MOW": 3, "VOG": 3, "GSV": 4, "GOJ": 3,
    "KUF": 4, "SVX": 5, "UFA": 5,
    "OMS": 6,
    "BAX": 7, "KJA": 7, "NOZ": 7,
    "IKT": 8, "UUD": 8,
}

IATA_CARRIER = {
    "SU": "Аэрофлот", "DP": "Победа", "FV": "Россия", "S7": "S7",
    "U6": "Уральские авиалинии", "UT": "Utair", "A4": "Азимут",
    "N4": "Nordwind", "EO": "Икар (Pegas Fly)", "RT": "ЮВТ Аэро",
    "IO": "ИрАэро", "YC": "Ямал", "Y7": "NordStar", "WZ": "Red Wings",
    "5N": "Smartavia", "KV": "КрасАвиа", "7R": "РусЛайн", "D2": "Северсталь",
    "6R": "Алроса", "I8": "Ижавиа",
}

TIMETABLE_CITY_IATA = {
    "Шереметьево": "MOW", "Домодедово": "MOW", "Внуково": "MOW", "Москва": "MOW",
    "Санкт-Петербург": "LED", "Екатеринбург": "SVX", "Иркутск": "IKT",
    "Красноярск": "KJA", "Новосибирск": "OVB", "Казань": "KZN",
    "Сочи": "AER", "Минеральные Воды": "MRV", "Сургут": "SGC",
    "Ханты-Мансийск": "HMA", "Нижневартовск": "NJC", "Новый Уренгой": "NUX",
    "Надым": "NYM", "Ноябрьск": "NOJ", "Салехард": "SLY", "Тобольск": "RMZ",
    "Краснодар": "KRR", "Норильск": "NSK", "Улан-Удэ": "UUD",
    "Барнаул": "BAX", "Уфа": "UFA", "Самара": "KUF",
    "Нижний Новгород": "GOJ", "Саратов": "GSV", "Волгоград": "VOG",
    "Новокузнецк": "NOZ",
}

SUBSIDY_CITY_IATA = {
    "Омск": "OMS", "Иркутск": "IKT", "Улан-Удэ": "UUD", "Волгоград": "VOG",
    "Москва": "MOW", "Саратов": "GSV", "Нижний Новгород": "GOJ",
    "Самара": "KUF", "Красноярск": "KJA", "Барнаул": "BAX",
    "Уфа": "UFA", "Новокузнецк": "NOZ", "Екатеринбург": "SVX",
}


def _rd(path):
    p = ROOT / path
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _opt_int(x):
    try:
        if x in ("", None):
            return None
        return int(round(float(x)))
    except (TypeError, ValueError):
        return None


def _opt_float(x, ndigits=1):
    try:
        if x in ("", None):
            return None
        return round(float(x), ndigits)
    except (TypeError, ValueError):
        return None


def _block_min(km, range_light, par):
    south = "юг" in (range_light or "").lower()
    rf = par["route_factor_south"] if south else par["route_factor"]
    bh_h = par["block_fixed_h"] + km * rf / par["block_speed_kmh"]
    return int(round(bh_h * 60 / 5) * 5)


def _verify_schedule(flights, expected_rotations, ac_list, min_turn=TURN_MIN, max_week_min=MAX_AC_WEEK_MIN):
    """Жёсткая проверка каждого собранного расписания: 0 наложений, оборот >= 60 мин, налёт <= 70 ч/нед."""
    assert len(flights) == sum(expected_rotations.values()) * 2, (len(flights), sum(expected_rotations.values()) * 2)
    counts = {}
    for f in flights:
        if f["o"] == "OMS":
            counts[f["d"]] = counts.get(f["d"], 0) + 1
    assert counts == expected_rotations, f"Несовпадение частот: {counts} != {expected_rotations}"

    min_gap = None
    ac_bh = {}
    for ac in ac_list:
        legs = sorted((f for f in flights if f["ac"] == ac), key=lambda x: (x["t1"], x["t2"]))
        assert legs, f"Борт {ac} не задействован"
        bh_sum = sum(f["bh"] for f in legs)
        assert bh_sum <= max_week_min, f"Превышен налёт {ac}: {bh_sum / 60:.1f} ч > {max_week_min / 60:.1f} ч"
        ac_bh[ac] = round(bh_sum / 60, 2)
        for a, b in zip(legs, legs[1:]):
            assert a["d"] == b["o"], f"Разрыв маршрута {ac}: {a['id']}->{b['id']}"
            gap = b["t1"] - a["t2"]
            assert gap >= min_turn, f"Нарушен оборот {ac} ({a['id']}->{b['id']}): {gap} мин < {min_turn}"
            min_gap = gap if min_gap is None else min(min_gap, gap)
        wrap_gap = (legs[0]["t1"] + 10080) - legs[-1]["t2"]
        assert wrap_gap >= min_turn, f"Нарушен недельный стык Вс->Пн {ac}: {wrap_gap} мин"
        min_gap = wrap_gap if min_gap is None else min(min_gap, wrap_gap)

    return {
        "total_rotations": len(flights) // 2,
        "total_legs": len(flights),
        "total_bh": round(sum(f["bh"] for f in flights) / 60, 1),
        "max_ac_bh": max(ac_bh.values()),
        "min_ac_bh": min(ac_bh.values()),
        "min_turn_min": min_gap if min_gap is not None else TURN_MIN,
        "ac_bh": ac_bh,
    }


def _build_start_schedule():
    rows = _rd("data/external/colleagues/oms_ramp_week_flights.csv")
    flights = []
    expected = {}
    for r in rows:
        dep = datetime.fromisoformat(r["departure_local"]).astimezone(OMS_TZ)
        arr = datetime.fromisoformat(r["arrival_local"]).astimezone(OMS_TZ)
        t1 = int(round((dep - OMS_WEEK_ANCHOR).total_seconds() / 60))
        t2 = int(round((arr - OMS_WEEK_ANCHOR).total_seconds() / 60))
        bh = int(r["block_min"])
        assert t2 - t1 == bh
        flights.append({
            "id": r["flight_id"],
            "ac": r["tail_slot"],
            "o": r["origin"],
            "d": r["destination"],
            "t1": t1,
            "t2": t2,
            "bh": bh,
            "wave": "start",
        })
        if r["origin"] == "OMS":
            expected[r["destination"]] = expected.get(r["destination"], 0) + 1
    flights.sort(key=lambda f: (f["t1"], f["ac"], f["id"]))
    stats = _verify_schedule(flights, expected, ["S1", "S2"])
    return flights, stats


def _emit_rotation(rid, ac, spoke, dep_t1, bh_min, wave):
    return [
        {"id": f"{rid}A", "ac": ac, "o": "OMS", "d": spoke, "t1": dep_t1, "t2": dep_t1 + bh_min, "bh": bh_min, "wave": wave},
        {"id": f"{rid}B", "ac": ac, "o": spoke, "d": "OMS", "t1": dep_t1 + bh_min + TURN_MIN, "t2": dep_t1 + 2 * bh_min + TURN_MIN, "bh": bh_min, "wave": wave},
    ]


def _build_radial_schedule(routes):
    """5 активных + 1 резерв SJ-100: 7 прибыльных стволов (50 оборотов = 100 рейсов/нед.), без фидеров KJA/BAX."""
    trunk = {k: v for k, v in routes.items() if k not in FEEDERS}
    ac_list = [f"AC-{i}" for i in range(1, 6)]
    ac_bh = {ac: 0 for ac in ac_list}
    used = {ac: set() for ac in ac_list}

    morning_spokes = sorted([k for k, v in trunk.items() if v["fs"] >= 7], key=lambda k: -trunk[k]["bh_min"])
    assert len(morning_spokes) == 5
    remaining = {k: v["fs"] - (7 if k in morning_spokes else 0) for k, v in trunk.items()}

    rotations = []
    for day in range(7):
        order_ac = sorted(ac_list, key=lambda ac: (ac_bh[ac], ac))
        for idx, (ac, sp) in enumerate(zip(order_ac, morning_spokes)):
            bh = trunk[sp]["bh_min"]
            ac_bh[ac] += 2 * bh
            used[ac].add((day, "am"))
            rotations.append((day, "am", idx, ac, sp, bh))

    eve_pool = []
    for sp, cnt in remaining.items():
        eve_pool.extend([sp] * cnt)
    eve_pool.sort(key=lambda sp: (-trunk[sp]["bh_min"], sp))
    assert len(eve_pool) == 15

    eve_day_cnt = [0] * 7
    eve_ac_cnt = {ac: 0 for ac in ac_list}
    for sp in eve_pool:
        bh = trunk[sp]["bh_min"]
        candidates = [
            (ac_bh[ac], eve_ac_cnt[ac], eve_day_cnt[day], day, ac)
            for day in range(7)
            for ac in ac_list
            if (day, "pm") not in used[ac] and eve_ac_cnt[ac] < 3 and ac_bh[ac] + 2 * bh <= MAX_AC_WEEK_MIN
        ]
        assert candidates, f"Не удалось разместить вечерний оборот {sp}"
        candidates.sort()
        _, _, _, day, ac = candidates[0]
        slot = eve_day_cnt[day]
        eve_day_cnt[day] += 1
        eve_ac_cnt[ac] += 1
        ac_bh[ac] += 2 * bh
        used[ac].add((day, "pm"))
        rotations.append((day, "pm", slot, ac, sp, bh))

    rotations.sort(key=lambda x: (x[0], 0 if x[1] == "am" else 1, x[2], x[3]))
    flights = []
    for idx, (day, wave, slot, ac, sp, bh) in enumerate(rotations, start=1):
        dep_min = (300 + slot * 10) if wave == "am" else (945 + slot * 15)
        flights.extend(_emit_rotation(f"P{idx:03d}", ac, sp, day * 1440 + dep_min, bh, wave))

    expected = {k: v["fs"] for k, v in trunk.items()}
    stats = _verify_schedule(flights, expected, ac_list)
    return flights, stats


def _build_full_schedule(routes):
    """7 активных + 1 резерв SJ-100: полная хабовая сеть (9 лучей, 64 оборота = 128 рейсов/нед.) с волнами стыковок."""
    ac_list = [f"AC-{i}" for i in range(1, 8)]
    ac_bh = {ac: 0 for ac in ac_list}
    day_end = {(d, ac): 0 for d in range(7) for ac in ac_list}

    flights_meta = []
    rem = {k: v["fs"] for k, v in routes.items()}
    am_map = [
        ("UUD", 0, 300, [0, 1, 2, 3, 4, 5, 6]),
        ("IKT", 1, 330, [0, 1, 2, 3, 4, 5, 6]),
        ("KJA", 2, 420, [0, 1, 2, 3, 4, 5, 6]),
        ("BAX", 3, 510, [0, 1, 3, 4]),
        ("KUF", 4, 330, [0, 2, 4, 5, 6]),
        ("GOJ", 5, 315, [0, 1, 2, 3, 4, 5, 6]),
        ("VOG", 6, 300, [0, 1, 2, 3, 4, 5, 6]),
    ]
    for sp, ac_i, dep_m, days in am_map:
        ac = ac_list[ac_i]
        bh = routes[sp]["bh_min"]
        for d in days:
            flights_meta.append((d, dep_m, ac, sp, "am"))
            rem[sp] -= 1
            ac_bh[ac] += 2 * bh
            day_end[(d, ac)] = d * 1440 + dep_m + 2 * bh + TURN_MIN

    pm_list = []
    for sp, cnt in rem.items():
        pm_list.extend([sp] * cnt)
    pm_list.sort(key=lambda sp: (-routes[sp]["bh_min"], sp))
    pm_used_day = {(d, ac): False for d in range(7) for ac in ac_list}
    pm_slot_day = [0] * 7
    for sp in pm_list:
        bh = routes[sp]["bh_min"]
        best = None
        for d in range(7):
            for ac in ac_list:
                if pm_used_day[(d, ac)] or ac_bh[ac] + 2 * bh > MAX_AC_WEEK_MIN:
                    continue
                earliest_dep = max(d * 1440 + 840 + pm_slot_day[d] * 10, day_end[(d, ac)] + TURN_MIN)
                if earliest_dep + 2 * bh + TURN_MIN > d * 1440 + 1500:
                    continue
                score = (ac_bh[ac], pm_slot_day[d], d, ac)
                if best is None or score < best[0]:
                    best = (score, d, ac, earliest_dep)
        assert best is not None, f"Не удалось разместить второй оборот {sp} в полной сети"
        _, d, ac, dep_abs = best
        pm_used_day[(d, ac)] = True
        pm_slot_day[d] += 1
        ac_bh[ac] += 2 * bh
        flights_meta.append((d, dep_abs - d * 1440, ac, sp, "pm"))

    flights_meta.sort(key=lambda x: (x[0], x[1], x[2]))
    flights = []
    for idx, (d, dep_m, ac, sp, wave) in enumerate(flights_meta, start=1):
        bh = routes[sp]["bh_min"]
        flights.extend(_emit_rotation(f"R{idx:03d}", ac, sp, d * 1440 + dep_m, bh, wave))

    expected = {k: v["fs"] for k, v in routes.items()}
    stats = _verify_schedule(flights, expected, ac_list)
    return flights, stats


def _load_geo_fallback():
    """Использует общую проекцию build_dashboard3.geo() при автономном запуске."""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    import build_dashboard3 as b3
    names = {}
    for r in _rd("data/processed/network_routes.csv"):
        if r["scenario"] == "base" and r["variant"] == "Хаб OMS":
            names.setdefault(r["to"], r["to_city"])
    names.setdefault("OMS", "Омск")
    mp, pts, _ = b3.geo(names)
    return pts, names, mp


def _parse_code_list(raw):
    if not raw or raw in ("[]", "nan"):
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
    except Exception:
        pass
    return [x.strip() for x in str(raw).replace(";", ",").split(",") if x.strip()]


def _build_intel(all_codes, names, par):
    """Собирает проверенные данные по аэропортам, конкурентам, субсидиям, тарифам и экономике лучей."""
    carrier_map = dict(IATA_CARRIER)
    for r in _rd("data/manual/carrier_names.csv"):
        carrier_map[r["raw"]] = r["name"]

    def norm_carrier(raw):
        return carrier_map.get(raw, raw)

    longlist = {r["iata"]: r for r in _rd("data/processed/longlist.csv")}
    tech = {r["iata"]: r for r in _rd("data/manual/airport_tech.csv")}
    kover = {r["iata"]: r for r in _rd("data/processed/kover_days.csv")}
    seas = {r["iata"]: [round(_num(r[f"m{i}"], 1.0), 3) for i in range(1, 13)] for r in _rd("data/processed/airport_seasonality.csv")}
    comp_hubs = {r["iata"]: r for r in _rd("data/manual/competitor_hubs.csv")}

    catch_extra = {}
    for path in ("data/processed/catchments.csv", "data/processed/catchment_extra.csv"):
        for r in _rd(path):
            if r.get("iata") in all_codes:
                catch_extra.setdefault(r["iata"], {}).update(r)

    dest_oms = {}
    for r in _rd("data/processed/destinations.csv"):
        if r["from"] == "OMS":
            dest_oms[r["to"]] = r

    # Расписание OMS (зима 2026/27): группировка по направлениям и перевозчикам
    tt_rows = _rd("data/external/colleagues/omsk_domestic_timetable_rows.csv")
    out_wk = _rd("data/external/colleagues/omsk_outbound_week_20261207.csv")
    wk_deps_by_carrier = {}
    for r in out_wk:
        c = norm_carrier(r["carrier_raw"])
        wk_deps_by_carrier[c] = wk_deps_by_carrier.get(c, 0) + 1

    oms_carrier_agg = {}
    oms_tt_by_iata = {}
    for r in tt_rows:
        c = norm_carrier(r["carrier_raw"])
        routing = r["routing_raw"]
        dst_codes = []
        for city_ru, code in TIMETABLE_CITY_IATA.items():
            if code != "OMS" and city_ru in routing and code not in dst_codes:
                dst_codes.append(code)
        ac_raw = r["aircraft_type_raw"].strip()
        flt = r["flight_numbers_raw"].strip()
        agg = oms_carrier_agg.setdefault(c, {"dests": set(), "aircrafts": set(), "flts": []})
        agg["dests"].update(dst_codes)
        if ac_raw:
            agg["aircrafts"].add(ac_raw)
        if flt and flt not in agg["flts"] and len(agg["flts"]) < 4:
            agg["flts"].append(flt)

        for dc in dst_codes:
            lst = oms_tt_by_iata.setdefault(dc, [])
            key = (c, flt, ac_raw, r["weekdays_raw"], r["omsk_arrival_local_raw"], r["omsk_departure_local_raw"])
            if not any(x["_k"] == key for x in lst):
                lst.append({
                    "_k": key,
                    "carrier": c,
                    "flt": flt,
                    "ac": ac_raw,
                    "wd": r["weekdays_raw"],
                    "arr": r["omsk_arrival_local_raw"],
                    "dep": r["omsk_departure_local_raw"],
                    "period": r["period_raw"],
                })

    oms_carriers_list = []
    for c, agg in oms_carrier_agg.items():
        oms_carriers_list.append({
            "carrier": c,
            "deps_wk": wk_deps_by_carrier.get(c, 0),
            "dests": sorted(agg["dests"]),
            "ac": sorted(agg["aircrafts"]),
            "flts": agg["flts"],
        })
    oms_carriers_list.sort(key=lambda x: (-x["deps_wk"], -len(x["dests"]), x["carrier"]))

    # Перевозчики из карточек маршрутов (route_product_cards.csv)
    rpc_by_airport = {}
    for r in _rd("data/external/colleagues/route_product_cards.csv"):
        c_raw = r["carrier"].strip()
        if not c_raw:
            continue
        c = norm_carrier(c_raw)
        o, d = r["origin"], r["destination"]
        for ap, other in ((o, d), (d, o)):
            if ap in all_codes:
                ent = rpc_by_airport.setdefault(ap, {}).setdefault(c, {"dests": set(), "ac": set(), "rw": r["own_RW"] == "true"})
                ent["dests"].add(other)
                if r["aircraft"].strip():
                    ent["ac"].add(r["aircraft"].strip())

    # Действующие рейсы Red Wings (rw_routes_now.csv)
    rw_by_ap = {}
    for r in _rd("data/manual/rw_routes_now.csv"):
        a, b = r["a"], r["b"]
        for ap, other in ((a, b), (b, a)):
            if ap in all_codes:
                rw_by_ap.setdefault(ap, []).append({
                    "pair": f"{a}–{b}",
                    "other": other,
                    "freq": _opt_float(r["freq_week_each_way"], 1),
                    "status": r["freq_status"],
                })

    # Субсидии Росавиации 2026 (favt_subsidy_2026.csv)
    sub_by_ap = {}
    sub_oms_spoke = {}
    for r in _rd("data/raw/favt_subsidy_2026.csv"):
        co, cd = r["origin"].strip(), r["destination"].strip()
        io, id_ = SUBSIDY_CITY_IATA.get(co), SUBSIDY_CITY_IATA.get(cd)
        airline = r["airline"].strip()
        for prefix in ("АО Авиакомпания ", "АО «Авиакомпания ", "АО «АТК ", "АО «АК ", "ПАО «Авиакомпания ", "ООО «Авиакомпания ", "ООО «Авиапредприятие ", "АО АК ", "АО ", "ПАО ", "ООО "):
            if airline.startswith(prefix):
                airline = airline[len(prefix):]
                break
        airline = airline.strip("«» ")
        rec = {
            "pair": f"{co} – {cd}",
            "airline": airline,
            "ac": r["aircraft"].strip(),
            "freq": r["flights_per_week"].strip(),
            "period": r["period"].strip(),
        }
        for code in (io, id_):
            if code and code in all_codes:
                lst = sub_by_ap.setdefault(code, [])
                if not any(x["pair"] == rec["pair"] and x["airline"] == rec["airline"] and x["freq"] == rec["freq"] for x in lst):
                    lst.append(rec)
        if io == "OMS" and id_ in all_codes:
            sub_oms_spoke.setdefault(id_, []).append(rec)
        elif id_ == "OMS" and io in all_codes:
            sub_oms_spoke.setdefault(io, []).append(rec)

    # Тарифы аэропорта Омск (p39_omsk_prices.csv)
    oms_tariffs = []
    wanted_tariffs = {
        "OMS-BASE-30–74.999 т", "OMS-PARK-H-30–74.999 т", "OMS-PARK-D-30–74.999 т",
        "OMS-CITYBUS", "OMS-ESCORT", "OMS-WH-11.19.1", "OMS-PASS-OUT",
    }
    for r in _rd("data/external/colleagues/p39_omsk_prices.csv"):
        if r["id"] in wanted_tariffs:
            oms_tariffs.append({
                "article": r["article"],
                "unit": r["unit"],
                "price": _opt_float(r["min"], 0),
                "page": r["page"],
            })

    # Проверенные конкуренты и тарифы p40 (p40_route_competitors_verified.csv)
    p40_oms = {}
    for r in _rd("data/external/colleagues/p40_route_competitors_verified.csv"):
        if r["a"] == "OMS":
            p40_oms[r["b"]] = r
        elif r["b"] == "OMS":
            p40_oms[r["a"]] = r

    # Спрос из demand_estimates.csv
    dest_est = {}
    for r in _rd("data/processed/demand_estimates.csv"):
        if r["a"] == "OMS" or r["b"] == "OMS":
            other = r["b"] if r["a"] == "OMS" else r["a"]
            dest_est[other] = r

    # Экономика лучей Хаба OMS (base и cautious)
    net_routes = {"base": {}, "cautious": {}}
    for r in _rd("data/processed/network_routes.csv"):
        if r["variant"] == "Хаб OMS" and r["scenario"] in ("base", "cautious"):
            net_routes[r["scenario"]].setdefault(r["to"], {
                "fs": int(_num(r["freq_week_each_way"])),
                "fw": int(_num(r["freq_week_winter"])),
                "local": int(_num(r["pax_year_local"])),
                "tr": int(_num(r["pax_year_transfer_seg"])),
                "seg": int(_num(r["pax_year_segments"])),
                "lf": round(_num(r["load_factor"]), 2),
                "spill": int(_num(r["pax_year_spilled"])),
                "rev": round(_num(r["revenue_mln_year"]), 1),
                "cost": round(_num(r["cost_mln_year"]), 1),
                "res": round(_num(r["result_mln_year"]), 1),
                "sub": round(_num(r["subsidy_mln_year"]), 1),
                "sub_rule": r["subsidy_rule"],
                "src": r["demand_source"],
                "light": r["range_light"],
            })

    # Сборка словаря airports
    airports = {}
    for c in all_codes:
        ll = longlist.get(c, {})
        tc = tech.get(c, {})
        kv = kover.get(c, {})
        ce = catch_extra.get(c, {})
        ch = comp_hubs.get(c, {})
        ds = dest_oms.get(c, {})

        rpc_list = []
        for carr, info in rpc_by_airport.get(c, {}).items():
            rpc_list.append({
                "carrier": carr,
                "dests": sorted(info["dests"]),
                "ac": sorted(info["ac"]),
                "rw": info["rw"],
            })
        rpc_list.sort(key=lambda x: (-len(x["dests"]), x["carrier"]))

        h24_raw = tc.get("h24") or ll.get("h24") or ""
        ssj_mro_raw = tc.get("ssj_mro") or ll.get("ssj_mro") or ""
        ssj_ops_raw = tc.get("ssj_ops") or ll.get("ssj_ops") or ""
        rw_sup_raw = tc.get("rw_support") or ll.get("rw_support") or ""

        is_chub = ch.get("competitor_hub") == "1"
        chub_carrier = ch.get("carrier") or ""
        if c == "SVX":
            chub_note = "База Red Wings и Уральских авиалиний"
        elif is_chub:
            chub_note = ch.get("evidence") or f"Хаб {chub_carrier}"
        else:
            chub_note = ch.get("evidence") or ll.get("base_carriers") or "Крупного базового хаба конкурентов не зафиксировано"

        airports[c] = {
            "code": c,
            "city": names.get(c, c),
            "icao": ll.get("icao") or "",
            "region": ll.get("region") or ds.get("to_region") or "",
            "fd": ll.get("fed_district") or "",
            "tz": TZ_OFFSET_H.get(c, 6),
            "pax_2025": _opt_int(ll.get("pax_2025")),
            "pax_qual": ll.get("pax_2025_qualifier") or "",
            "pop_2025": _opt_int(ll.get("catchment_pop_2025") or ce.get("catchment_pop_2025") or ds.get("pop")),
            "wage_2024": _opt_int(ll.get("wage_2024") or ce.get("wage_2024")),
            "runway_m": _opt_int(ll.get("runway_m")),
            "h24": "24ч" if h24_raw in ("1", "1.0") else "не проверено",
            "ssj_ops": "допуск SSJ" if ssj_ops_raw in ("1", "1.0") else "не подтверждено",
            "ssj_mro": "есть ТО SSJ" if ssj_mro_raw in ("1", "1.0") else ("косвенно" if ssj_mro_raw == "0.5" else "не найдено"),
            "rw_support": "опорный / база" if c == "SVX" else ("в списке опорных не числится" if rw_sup_raw in ("0", "0.0") else "проверить"),
            "kover_365": _opt_int(kv.get("last365_days") or ll.get("last365_days")),
            "kover_h1_26": _opt_int(kv.get("h1_2026_days") or ll.get("h1_2026_days")),
            "frost": _opt_float(ll.get("frost_days") or ce.get("frost_days"), 0),
            "wind": _opt_float(ll.get("wind_days") or ce.get("wind_days"), 0),
            "bad_wx": _opt_float(ll.get("bad_weather_days") or ce.get("bad_weather_days"), 0),
            "seas": seas.get(c, []),
            "comp_hub": is_chub,
            "comp_hub_carrier": chub_carrier,
            "comp_hub_note": chub_note,
            "oms_carriers": oms_carriers_list if c == "OMS" else [],
            "rpc_carriers": rpc_list[:8],
            "rw_now": rw_by_ap.get(c, [])[:8],
            "subs_2026": sub_by_ap.get(c, [])[:10],
            "tariffs": oms_tariffs if c == "OMS" else [],
        }

    # Сборка словаря spokes
    spokes = {}
    for c in all_codes:
        if c == "OMS":
            continue
        ds = dest_oms.get(c, {})
        est = dest_est.get(c, {})
        p40 = p40_oms.get(c, {})
        rb = net_routes["base"].get(c)
        rc = net_routes["cautious"].get(c)
        km = int(_num(ds.get("km") or est.get("km") or 0))
        light = (rb or {}).get("light") or ("зелёный" if km <= 2300 else "жёлтый")
        bh_min = _block_min(km, light, par) if km > 0 else None

        tt_clean = [{k: v for k, v in x.items() if k != "_k"} for x in oms_tt_by_iata.get(c, [])]
        spokes[c] = {
            "code": c,
            "city": names.get(c, c),
            "km": km,
            "rail_hr": _opt_float(ds.get("rail_hr"), 1),
            "direct_now": (ds.get("direct") == "True") or (est.get("direct_now") == "True") or bool(tt_clean),
            "bh_min": bh_min,
            "light": light,
            "fare_model": _opt_int(est.get("fare_ours_rub")),
            "base": rb,
            "cautious": rc,
            "est": {
                "seg_base": _opt_int(est.get("segments_base")),
                "od_base": _opt_int(est.get("od_base")),
                "od_caut": _opt_int(est.get("od_cautious")),
                "route_now": est.get("od_route_now") or "",
            } if est else None,
            "comp": {
                "direct": [norm_carrier(x) for x in _parse_code_list(p40.get("direct_competitors"))],
                "conn": [norm_carrier(x) for x in _parse_code_list(p40.get("connecting_competitors"))],
                "seats_day": _opt_float(p40.get("competitor_daily_seats"), 1),
                "fare_dir": _opt_int(p40.get("F_comp_direct_20kg")),
                "fare_tr": _opt_int(p40.get("F_comp_transfer_20kg")),
                "w_comp": _opt_float(p40.get("W_comp_2028"), 3),
                "tt": tt_clean,
            },
            "subs_2026": sub_oms_spoke.get(c, []),
        }

    # Валидные стыковки стартовой фазы (45-240 мин) из oms_ramp_connections.csv
    ramp_conns = []
    for r in _rd("data/external/colleagues/oms_ramp_connections.csv"):
        if r.get("arithmetic_status") == "WITHIN_SCENARIO_45_240":
            ramp_conns.append({
                "in_id": r["inbound_id"],
                "out_id": r["outbound_id"],
                "o": r["origin"],
                "d": r["destination"],
                "wait": _opt_int(r["wait_min"]),
                "note": r["airport_status"],
            })

    return {"airports": airports, "spokes": spokes, "ramp_conns": ramp_conns}


def build_animation_payload(pts=None, names=None, geo_map=None):
    """Формирует компактный JSON payload для Дашборда 3 и автономной страницы анимации."""
    if pts is None or names is None or geo_map is None:
        pts, names, geo_map = _load_geo_fallback()

    par = {r["parameter"]: _num(r["base"]) for r in _rd("data/assumptions/network.csv")}
    routes = {}
    for r in _rd("data/processed/network_routes.csv"):
        if r["scenario"] != "base" or r["variant"] != "Хаб OMS":
            continue
        to = r["to"]
        if to in routes:
            continue
        km = _num(r["km"])
        routes[to] = {
            "to": to,
            "city": r["to_city"],
            "km": int(km),
            "fs": int(_num(r["freq_week_each_way"])),
            "res": _num(r["result_mln_year"]),
            "bh_min": _block_min(km, r["range_light"], par),
        }

    radial_flights, radial_stats = _build_radial_schedule(routes)
    full_flights, full_stats = _build_full_schedule(routes)
    start_flights, start_stats = _build_start_schedule()

    all_codes = sorted({f["o"] for f in radial_flights + full_flights + start_flights} |
                       {f["d"] for f in radial_flights + full_flights + start_flights} | {"SVX"})
    sub_pts = {c: pts[c] for c in all_codes if c in pts}
    sub_names = {c: names.get(c, c) for c in all_codes}

    modes = {
        "radial": {
            "label": "Радиальная без фидеров (5+1 ВС · 7 лучей)",
            "sub": f"Радиальная сеть P40 без фидеров KJA/BAX: 5 активных + 1 резерв SJ-100 · 7 прибыльных стволов · {radial_stats['total_rotations']} оборотов ({radial_stats['total_legs']} рейсов/нед.) · макс. {radial_stats['max_ac_bh']:.1f} ч/нед. на борт",
            "aircraft": [f"AC-{i}" for i in range(1, 6)],
            "reserve": "AC-6 Рез.",
            "spokes": sorted(k for k in routes if k not in FEEDERS),
            "feeders": [],
            "start_only": [],
            "stats": radial_stats,
            "flights": radial_flights,
        },
        "full": {
            "label": "Полная хабовая (7+1 ВС · 9 лучей)",
            "sub": f"Полная хабовая сеть: 7 активных + 1 резерв SJ-100 · 9 лучей (7 стволов + фидеры BAX/KJA) · {full_stats['total_rotations']} оборотов ({full_stats['total_legs']} рейсов/нед.) · макс. {full_stats['max_ac_bh']:.1f} ч/нед. на борт",
            "aircraft": [f"AC-{i}" for i in range(1, 8)],
            "reserve": "AC-8 Рез.",
            "spokes": sorted(routes.keys()),
            "feeders": list(FEEDERS),
            "start_only": [],
            "stats": full_stats,
            "flights": full_flights,
        },
        "start": {
            "label": "Старт хаба (2+1 ВС · 44 рейса)",
            "sub": f"Стартовая фаза (oms_ramp_week_flights.csv): 2 активных + 1 резерв SJ-100 · 6 направлений · {start_stats['total_legs']} рейсов/нед. · {start_stats['max_ac_bh']:.1f} БЧ/нед. на борт",
            "aircraft": ["S1", "S2"],
            "reserve": "S3 Рез.",
            "spokes": sorted({f["d"] if f["o"] == "OMS" else f["o"] for f in start_flights}),
            "feeders": [],
            "start_only": ["UFA", "NOZ"],
            "stats": start_stats,
            "flights": start_flights,
        },
    }

    intel = _build_intel(all_codes, sub_names, par)
    return {
        "map": geo_map,
        "pts": sub_pts,
        "names": sub_names,
        "modes": modes,
        "airports": intel["airports"],
        "spokes": intel["spokes"],
        "ramp_conns": intel["ramp_conns"],
    }


PLAYER_CSS = """
.an-wrap{display:flex;flex-direction:column;gap:12px}
.an-ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:space-between}
.an-row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.an-clock{font-family:var(--mono);font-size:12.5px;font-weight:700;padding:4px 10px;border-radius:8px;background:var(--paper);border:1px solid var(--line)}
.an-scrub{display:flex;align-items:center;gap:10px}
.an-scrub input[type=range]{flex:1;accent-color:var(--red);cursor:pointer}
.an-strip{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;padding:8px 12px;border-radius:10px;background:var(--paper);border-left:3px solid var(--red);font-size:13px}
.an-strip.tr{background:var(--amber-bg);border-left-color:#B45309}
.an-split{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(350px,0.95fr);gap:14px;align-items:stretch}
@media(max-width:1060px){.an-split{grid-template-columns:minmax(0,1fr)}}
.an-mapbox{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--sea);display:flex;flex-direction:column;position:relative}
.an-mapbar{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap;padding:7px 10px;background:var(--white);border-bottom:1px solid var(--line);font-size:12px}
.an-stage{position:relative;flex:1;min-height:330px;background:var(--sea);user-select:none;overflow:hidden}
.an-stage svg{width:100%;height:100%;min-height:330px;display:block;cursor:grab}
.an-stage svg.panning{cursor:grabbing}
.an-zoom{position:absolute;top:10px;right:10px;display:flex;flex-direction:column;gap:4px;z-index:4}
.an-zoom button{width:28px;height:28px;border:1px solid var(--line);background:rgba(255,255,255,.94);border-radius:8px;font-weight:700;font-size:14px;line-height:1;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.08)}
.an-zoom button:hover{border-color:var(--ink);background:#fff}
.an-tip{position:absolute;pointer-events:none;z-index:10;background:rgba(17,19,24,.94);color:#F4F5F7;padding:8px 10px;border-radius:9px;font-size:12px;line-height:1.4;max-width:270px;box-shadow:0 8px 24px rgba(0,0,0,.22);display:none}
.an-tip b{color:#fff}
.an-tip small{color:#B8C0CE;display:block;margin-top:2px}
.an-chips{display:flex;gap:4px;flex-wrap:wrap;padding:7px 10px;background:var(--paper);border-top:1px solid var(--line)}
.an-chip{border:1px solid var(--line);background:var(--white);border-radius:999px;padding:2px 9px;font-size:11.5px;font-weight:500;cursor:pointer;color:var(--ink)}
.an-chip:hover{border-color:var(--ink)}
.an-chip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.an-chip.hub{border-color:#F0B9BA;color:var(--red-d)}
.an-chip.hub.on{background:var(--red);color:#fff;border-color:var(--red)}
.an-legend{display:flex;gap:10px;flex-wrap:wrap;font-size:11.5px;color:var(--muted);padding:7px 10px;background:var(--white);border-top:1px solid var(--line)}
.an-legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px;vertical-align:0}
.an-insp{border:1px solid var(--line);border-radius:14px;background:var(--white);display:flex;flex-direction:column;min-width:0;overflow:hidden}
.an-itabs{display:flex;gap:2px;background:var(--paper);border-bottom:1px solid var(--line);padding:6px 8px 0}
.an-itabs button{border:0;background:none;padding:7px 11px;font-size:12.5px;font-weight:500;color:var(--muted);border-bottom:2.5px solid transparent;cursor:pointer;border-radius:8px 8px 0 0}
.an-itabs button.on{background:var(--white);color:var(--ink);border-bottom-color:var(--red);font-weight:700}
.an-ibody{padding:12px 14px;overflow-y:auto;max-height:455px;display:flex;flex-direction:column;gap:10px;font-size:12.5px}
.an-ihead{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap;border-bottom:1px solid var(--paper-2);padding-bottom:8px}
.an-icode{font-family:var(--code);font-size:22px;font-weight:700;line-height:1}
.an-kgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
@media(max-width:520px){.an-kgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}
.an-kbox{background:var(--paper);border-radius:9px;padding:6px 8px}
.an-kbox b{display:block;font-size:10.5px;color:var(--muted);font-weight:500}
.an-kbox span{font-weight:700;font-size:13px;font-variant-numeric:tabular-nums}
.an-alert{padding:7px 10px;border-radius:9px;font-size:12px;background:var(--amber-bg);color:#7A5410;border-left:3px solid #D97706}
.an-alert.red{background:var(--red-bg);color:var(--red-d);border-left-color:var(--red)}
.an-alert.ok{background:var(--green-bg);color:#1E6B45;border-left-color:var(--green)}
.an-alert.blue{background:var(--blue-bg);color:var(--blue);border-left-color:var(--blue)}
.an-sec{border-top:1px solid var(--paper-2);padding-top:8px}
.an-sec h4{margin:0 0 6px;font-size:12.5px;font-weight:700;display:flex;align-items:center;justify-content:space-between;gap:6px}
.an-mini{width:100%;border-collapse:collapse;font-size:11.5px;font-variant-numeric:tabular-nums}
.an-mini th{text-align:left;color:var(--muted);font-weight:500;padding:4px 5px;border-bottom:1px solid var(--line);background:var(--paper);position:static}
.an-mini td{padding:4px 5px;border-bottom:1px solid var(--paper-2);vertical-align:top;white-space:normal}
.an-mini td.n,.an-mini th.n{text-align:right;white-space:nowrap}
.an-spark{display:flex;align-items:flex-end;gap:3px;height:36px;padding-top:4px}
.an-spark i{flex:1;background:var(--red);border-radius:2px 2px 0 0;min-height:2px;opacity:.85}
.an-spark-l{display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:2px}
.an-rot{display:flex;flex-wrap:wrap;gap:5px;align-items:center}
.an-leg{border:1px solid var(--line);background:var(--paper);border-radius:8px;padding:4px 8px;font-size:11.5px;cursor:pointer;text-align:left}
.an-leg:hover{border-color:var(--ink)}
.an-leg.on{border-color:var(--red);background:var(--red-bg);color:var(--red-d);font-weight:700}
.an-g-ticks,.an-g-row{display:grid;grid-template-columns:84px 1fr;gap:8px;align-items:center}
.an-g-ticks{font-family:var(--mono);font-size:11px;color:var(--muted);margin-bottom:4px}
.an-g-ticks div{display:flex;justify-content:space-between}
.an-g-row{margin-bottom:5px}
.an-g-lbl{font-family:var(--mono);font-size:11.5px;font-weight:700;line-height:1.15}
.an-g-lbl small{display:block;font-weight:500;color:var(--muted);font-size:10.5px}
.an-g-track{position:relative;height:22px;background:var(--paper);border:1px solid var(--line);border-radius:6px;overflow:hidden}
.an-g-bar{position:absolute;top:2px;bottom:2px;border-radius:4px;color:#fff;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;cursor:pointer;opacity:.85;overflow:hidden;white-space:nowrap}
.an-g-bar:hover{opacity:1;outline:1.5px solid var(--ink);z-index:3}
.an-g-bar.on{opacity:1;outline:2px solid #fff;box-shadow:0 0 0 1.5px var(--ink);z-index:4}
.an-g-bar.sel{outline:2px solid #111318;opacity:1;z-index:4}
.an-g-ph{position:absolute;top:0;bottom:0;width:2px;background:var(--red);z-index:5;pointer-events:none}
.an-pill{display:inline-block;padding:1px 6px;border-radius:999px;font-size:10.5px;font-weight:600;background:var(--paper-2);color:var(--ink)}
.an-pill.g{background:var(--green-bg);color:#23704A}
.an-pill.r{background:var(--red-bg);color:var(--red-d)}
.an-pill.y{background:var(--amber-bg);color:#8A6210}
.an-pill.b{background:var(--blue-bg);color:var(--blue)}
.an-ap-node{cursor:pointer}
.an-ap-node:hover .an-ap-ring{stroke-opacity:1;stroke-width:2}
.an-arc-hit{cursor:pointer}
.an-plane{cursor:pointer}
"""

PLAYER_HTML = """
<div class="an-wrap">
  <div class="an-ctl">
    <div class="seg an-day"></div>
    <div class="an-row">
      <button class="btn sm an-reset" title="В начало суток">⏮</button>
      <button class="btn sm an-prev">◀ Шаг</button>
      <button class="btn sm red an-play" style="min-width:82px">▶ Пуск</button>
      <button class="btn sm an-next">Шаг ▶</button>
    </div>
    <div class="an-row">
      <div class="seg an-spd">
        <button data-s="15">×15</button>
        <button class="on" data-s="60">×60</button>
        <button data-s="180">×180</button>
      </div>
      <span class="clock an-clock">Пн 06:30 OMS</span>
    </div>
  </div>
  <div class="an-scrub">
    <span class="mono an-min">00:00</span>
    <input type="range" class="an-scr" min="0" max="1440" value="390">
    <span class="mono an-max">24:00</span>
  </div>
  <div class="an-strip">
    <span class="an-msg"></span>
    <span class="mono an-step"></span>
  </div>
  <div class="an-split">
    <div class="an-mapbox">
      <div class="an-mapbar">
        <div class="an-row">
          <label style="display:inline-flex;align-items:center;gap:4px;cursor:pointer"><input type="checkbox" class="an-chk-hubs" checked> Хабы конкурентов и «Ковёр»</label>
          <label style="display:inline-flex;align-items:center;gap:4px;cursor:pointer"><input type="checkbox" class="an-chk-comp" checked> Прямые рейсы конкурентов из OMS</label>
        </div>
        <span class="sub an-stat"></span>
      </div>
      <div class="an-stage">
        <svg class="an-svg" viewBox="255 245 410 155" preserveAspectRatio="xMidYMid meet"></svg>
        <div class="an-zoom">
          <button type="button" class="an-zi" title="Приблизить">+</button>
          <button type="button" class="an-zo" title="Отдалить">−</button>
          <button type="button" class="an-zr" title="Сбросить масштаб" style="font-size:12px">⌖</button>
        </div>
        <div class="an-tip"></div>
      </div>
      <div class="an-chips"></div>
      <div class="an-legend">
        <span><i style="background:#E32A2F"></i>База OMS + резерв</span>
        <span><i style="background:#3FA772"></i>Прибыльный ствол</span>
        <span><i style="background:#D97706"></i>Фидер (BAX/KJA)</span>
        <span><i style="background:#3E6E95"></i>Старт (UFA/NOZ)</span>
        <span><i style="background:#7C3AED"></i>Хаб конкурента (S7/SU)</span>
        <span style="margin-left:auto">Клик по городу, дуге или борту открывает аналитику</span>
      </div>
    </div>
    <aside class="an-insp">
      <div class="an-itabs">
        <button type="button" class="on" data-it="airport">Аэропорт и конкуренты</button>
        <button type="button" data-it="flight">Рейс и луч</button>
        <button type="button" data-it="hub">Стыковки в OMS</button>
      </div>
      <div class="an-ibody"></div>
    </aside>
  </div>
  <div style="margin-top:4px">
    <div class="hd" style="margin-bottom:6px">
      <h3 style="margin:0">Таймлайн ротации бортов (OMS UTC+6 · клик по рейсу = переход и карточка)</h3>
      <span class="sub r an-ghint"></span>
    </div>
    <div class="an-g-ticks"><span>Борт</span><div class="an-ticks"></div></div>
    <div class="an-gantt"></div>
  </div>
  <div style="margin-top:4px">
    <div class="hd" style="margin-bottom:6px">
      <h3 style="margin:0">Табло рейсов (клик = перейти к вылету и разобрать рейс)</h3>
      <span class="sub r an-bsum"></span>
    </div>
    <div class="tw" style="max-height:210px">
      <table>
        <thead><tr><th>Рейс</th><th>Борт</th><th>Маршрут</th><th>Вылет OMS</th><th>Прилёт OMS</th><th>БЧ</th><th>Статус</th></tr></thead>
        <tbody class="an-board"></tbody>
      </table>
    </div>
  </div>
</div>
"""

PLAYER_JS = """
function mountOmsFlightPlayer(root, ANIM, opts) {
  opts = opts || {};
  const DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
  const MON = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  const COLORS = { 'AC-1': '#2563EB', 'AC-2': '#0D9488', 'AC-3': '#D97706', 'AC-4': '#E32A2F', 'AC-5': '#7C3AED', 'AC-6': '#0284C7', 'AC-7': '#16A34A', 'S1': '#2563EB', 'S2': '#E32A2F' };
  const BASE_VB = { x: 255, y: 245, w: 410, h: 155 };
  const $ = s => root.querySelector(s);
  const $$ = s => [...root.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = (n, d = 0) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('ru-RU', { minimumFractionDigits: d, maximumFractionDigits: d }).replace('-', '−');
  const sg = (n, d = 0) => (n == null || isNaN(n)) ? '—' : (n > 0 ? '+' : '') + fmt(n, d);

  const ST = {
    mode: opts.mode || 'radial',
    day: 0,
    t: 390,
    playing: false,
    speed: 60,
    raf: null,
    lastTs: null,
    selAirport: 'OMS',
    selSpoke: 'IKT',
    selFlightId: null,
    inspTab: 'airport',
    showHubs: true,
    showComp: true,
    vb: { ...BASE_VB },
    hubFilterAp: 'ALL',
  };

  const curMode = () => ANIM.modes[ST.mode];
  const winRange = () => ST.day === -1 ? [0, Math.max(10080, ...curMode().flights.map(f => f.t2)) + 20] : [ST.day * 1440, ST.day * 1440 + ((ST.mode === 'start' && ST.day === 6) ? 1530 : 1440)];
  const winFlights = () => { const [w0, w1] = winRange(); return curMode().flights.filter(f => f.t2 >= w0 && f.t1 <= w1); };
  const stepPoints = () => { const [w0, w1] = winRange(), s = new Set([w0]); winFlights().forEach(f => { if (f.t1 >= w0 && f.t1 <= w1) s.add(f.t1); if (f.t2 >= w0 && f.t2 <= w1) s.add(f.t2); }); return [...s].sort((a, b) => a - b); };
  const routeColor = c => curMode().feeders.includes(c) ? '#D97706' : curMode().start_only.includes(c) ? '#3E6E95' : '#3FA772';

  function fmtTime(m, tzOff) {
    const shift = tzOff == null ? 0 : (tzOff - 6) * 60;
    let mm = Math.round(m) + shift;
    mm = ((mm % 10080) + 10080) % 10080;
    const d = Math.floor(mm / 1440), hh = String(Math.floor((mm % 1440) / 60)).padStart(2, '0'), mi = String(mm % 60).padStart(2, '0');
    return `${d < 7 ? DAYS[d] : 'Пн+'} ${hh}:${mi}`;
  }
  function fmtHM(m, tzOff) {
    const shift = tzOff == null ? 0 : (tzOff - 6) * 60;
    let mm = ((Math.round(m) + shift) % 1440 + 1440) % 1440;
    return `${String(Math.floor(mm / 60)).padStart(2, '0')}:${String(mm % 60).padStart(2, '0')}`;
  }
  function fmtClock(m) {
    return `${fmtTime(m)} OMS (${fmtHM(m, 3)} MSK)`;
  }
  function bezier(p0, p1, u) {
    const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2 - Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * 0.16;
    const x = (1 - u) * (1 - u) * p0[0] + 2 * (1 - u) * u * mx + u * u * p1[0];
    const y = (1 - u) * (1 - u) * p0[1] + 2 * (1 - u) * u * my + u * u * p1[1];
    const dx = 2 * (1 - u) * (mx - p0[0]) + 2 * u * (p1[0] - mx), dy = 2 * (1 - u) * (my - p0[1]) + 2 * u * (p1[1] - my);
    return { x, y, ang: Math.atan2(dy, dx) * 180 / Math.PI };
  }

  function setViewBox() {
    const svg = $('.an-svg');
    if (svg) svg.setAttribute('viewBox', `${ST.vb.x.toFixed(1)} ${ST.vb.y.toFixed(1)} ${ST.vb.w.toFixed(1)} ${ST.vb.h.toFixed(1)}`);
  }
  function zoomBy(factor, cxRatio = 0.5, cyRatio = 0.5) {
    const nw = Math.max(120, Math.min(460, ST.vb.w * factor));
    const nh = nw * (BASE_VB.h / BASE_VB.w);
    const px = ST.vb.x + ST.vb.w * cxRatio, py = ST.vb.y + ST.vb.h * cyRatio;
    ST.vb.w = nw; ST.vb.h = nh;
    ST.vb.x = Math.max(195, Math.min(720 - nw, px - nw * cxRatio));
    ST.vb.y = Math.max(195, Math.min(450 - nh, py - nh * cyRatio));
    setViewBox();
  }
  function focusAirportOnMap(code) {
    const pt = ANIM.pts[code];
    if (!pt) return;
    if (ST.vb.w < 380) {
      ST.vb.x = Math.max(200, Math.min(720 - ST.vb.w, pt[0] - ST.vb.w / 2));
      ST.vb.y = Math.max(200, Math.min(450 - ST.vb.h, pt[1] - ST.vb.h / 2));
      setViewBox();
    }
  }

  function showTip(ev, html) {
    const st = $('.an-stage'), tip = $('.an-tip');
    if (!st || !tip) return;
    tip.innerHTML = html;
    tip.style.display = 'block';
    const r = st.getBoundingClientRect();
    const lx = ev.clientX - r.left, ly = ev.clientY - r.top;
    tip.style.left = Math.max(8, Math.min(r.width - tip.offsetWidth - 8, lx + 14)) + 'px';
    tip.style.top = Math.max(8, Math.min(r.height - tip.offsetHeight - 8, ly - 12)) + 'px';
  }
  function hideTip() { const tip = $('.an-tip'); if (tip) tip.style.display = 'none'; }

  function stop() {
    ST.playing = false; ST.lastTs = null;
    if (ST.raf) cancelAnimationFrame(ST.raf);
    ST.raf = null;
    const pb = $('.an-play'); if (pb) pb.textContent = '▶ Пуск';
  }
  function start() {
    if (!ST.playing) {
      ST.playing = true; ST.lastTs = null;
      const pb = $('.an-play'); if (pb) pb.textContent = '⏸ Пауза';
      ST.raf = requestAnimationFrame(tick);
    }
  }
  function tick(ts) {
    if (!ST.playing) return;
    if (ST.lastTs !== null) {
      const [w0, w1] = winRange();
      ST.t += (ts - ST.lastTs) / 1000 * ST.speed;
      if (ST.t >= w1) ST.t = w0;
      renderDyn();
    }
    ST.lastTs = ts;
    ST.raf = requestAnimationFrame(tick);
  }
  function step(dir) {
    stop();
    const pts = stepPoints();
    ST.t = dir > 0 ? (pts.find(x => x > ST.t + 0.5) ?? pts[0]) : ([...pts].reverse().find(x => x < ST.t - 0.5) ?? pts[pts.length - 1]);
    renderDyn();
  }

  function selectAirport(code, switchTab = true) {
    ST.selAirport = code;
    if (code !== 'OMS' && ANIM.spokes[code]) ST.selSpoke = code;
    if (switchTab) ST.inspTab = 'airport';
    focusAirportOnMap(code);
    renderMapHighlights();
    renderChips();
    renderInspector();
  }
  function selectSpoke(code, switchTab = true) {
    ST.selSpoke = code;
    ST.selAirport = code;
    if (switchTab) ST.inspTab = 'flight';
    const fs = winFlights().filter(f => f.o === code || f.d === code);
    const active = fs.find(f => ST.t >= f.t1 && ST.t < f.t2) || fs.find(f => f.t1 >= ST.t) || fs[0];
    if (active) ST.selFlightId = active.id;
    renderMapHighlights();
    renderChips();
    renderInspector();
  }
  function selectFlight(fid, jump = false) {
    const f = curMode().flights.find(x => x.id === fid);
    if (!f) return;
    ST.selFlightId = f.id;
    const sp = f.o === 'OMS' ? f.d : f.o;
    ST.selSpoke = sp;
    ST.selAirport = sp;
    ST.inspTab = 'flight';
    if (jump) {
      stop();
      if (ST.day !== -1) ST.day = Math.min(6, Math.floor(f.t1 / 1440));
      ST.t = f.t1;
    }
    renderAllDyn();
  }

  function buildDays() {
    const el = $('.an-day');
    el.innerHTML = DAYS.map((d, i) => `<button type="button" class="${ST.day === i ? 'on' : ''}" data-d="${i}">${d}</button>`).join('') + `<button type="button" class="${ST.day === -1 ? 'on' : ''}" data-d="-1">7 дн.</button>`;
    el.querySelectorAll('button').forEach(b => b.onclick = () => {
      stop();
      ST.day = +b.dataset.d;
      const [w0] = winRange(), fs = winFlights();
      ST.t = fs.length ? Math.max(w0, fs[0].t1 - 15) : w0;
      renderAllDyn();
    });
  }

  function renderChips() {
    const m = curMode();
    const list = ['OMS', ...m.spokes, ...(m.spokes.includes('SVX') ? [] : ['SVX'])];
    $('.an-chips').innerHTML = list.map(c => {
      const ap = ANIM.airports[c] || {};
      const badge = ap.comp_hub ? ` · ${ap.comp_hub_carrier === 'S7' ? 'S7' : 'SU'}` : '';
      const cls = `an-chip${c === 'OMS' ? ' hub' : ''}${ST.selAirport === c ? ' on' : ''}`;
      return `<button type="button" class="${cls}" data-ap="${c}">${c} ${esc(ANIM.names[c] || '')}${badge}</button>`;
    }).join('');
    $$('.an-chip').forEach(b => b.onclick = () => selectAirport(b.dataset.ap, true));
  }

  function renderMapHighlights() {
    const m = curMode();
    const active = curMode().flights.filter(f => ST.t >= f.t1 && ST.t < f.t2);
    const actSp = new Set(active.map(f => f.o === 'OMS' ? f.d : f.o));
    $$('.an-arc-vis').forEach(p => {
      const c = p.dataset.sp;
      const isAct = actSp.has(c);
      const isSel = ST.selSpoke === c || ST.selAirport === c;
      p.setAttribute('stroke-opacity', isSel ? '1' : (isAct ? '0.92' : '0.28'));
      p.setAttribute('stroke-width', isSel ? '3.0' : (isAct ? '2.2' : '1.3'));
    });
    $$('.an-ap-ring').forEach(c => {
      const on = c.dataset.ap === ST.selAirport;
      c.setAttribute('stroke-opacity', on ? '1' : '0');
    });
  }

  function buildMap() {
    const P = ANIM.pts, o = P.OMS, m = curMode();
    let s = `<rect x="195" y="195" width="530" height="260" fill="var(--sea)"/><path d="${ANIM.map}" fill="var(--land)" stroke="var(--geo-line)" stroke-width="0.7"/>`;
    if (ST.showComp) {
      s += '<g id="an-comp-arcs">';
      ['IKT', 'KJA', 'MOW', 'SVX'].forEach(c => {
        if (!P[c]) return;
        const mx = (o[0] + P[c][0]) / 2, my = (o[1] + P[c][1]) / 2 - Math.hypot(P[c][0] - o[0], P[c][1] - o[1]) * 0.22;
        s += `<path d="M${o[0]},${o[1]} Q${mx.toFixed(1)},${my.toFixed(1)} ${P[c][0]},${P[c][1]}" fill="none" stroke="#64748B" stroke-width="0.9" stroke-dasharray="2.5 2.5" stroke-opacity="0.48"/>`;
      });
      s += '</g>';
    }
    s += '<g class="an-arcs">';
    m.spokes.forEach(c => {
      const p = P[c]; if (!p) return;
      const mx = (o[0] + p[0]) / 2, my = (o[1] + p[1]) / 2 - Math.hypot(p[0] - o[0], p[1] - o[1]) * 0.16;
      const d = `M${o[0]},${o[1]} Q${mx.toFixed(1)},${my.toFixed(1)} ${p[0]},${p[1]}`;
      s += `<path class="an-arc-vis" data-sp="${c}" d="${d}" fill="none" stroke="${routeColor(c)}" stroke-width="1.4" stroke-opacity="0.3" stroke-linecap="round"/>`;
      s += `<path class="an-arc-hit" data-sp="${c}" d="${d}" fill="none" stroke="transparent" stroke-width="10"/>`;
    });
    s += '</g>';

    const nodes = [...new Set([...m.spokes, 'OMS', 'SVX'])];
    nodes.forEach(c => {
      const p = P[c]; if (!p) return;
      const ap = ANIM.airports[c] || {};
      const isOms = c === 'OMS', isSvx = c === 'SVX' && !m.spokes.includes('SVX');
      const dx = c === 'UUD' ? 6 : c === 'GOJ' ? -5 : c === 'GSV' ? 5 : c === 'KUF' ? 5 : c === 'MOW' ? -5 : c === 'NOZ' ? 5 : 0;
      const dy = isOms ? 14 : (c === 'UUD' || c === 'BAX' || c === 'KUF' || c === 'NOZ') ? 9.5 : -6;
      const anc = dx < 0 ? 'end' : dx > 0 ? 'start' : 'middle';
      const stroke = isOms ? '#E32A2F' : (ap.comp_hub && ST.showHubs ? '#7C3AED' : (isSvx ? '#5E6675' : routeColor(c)));
      const fill = isOms ? '#E32A2F' : 'var(--white)';
      const r = isOms ? 5.2 : (isSvx ? 2.6 : 3.4);
      let badge = '';
      if (ST.showHubs) {
        if (ap.comp_hub) {
          const lbl = ap.comp_hub_carrier === 'S7' ? 'S7 ХАБ' : 'SU ХАБ';
          badge += `<rect x="${(p[0] - 13).toFixed(1)}" y="${(p[1] + 5).toFixed(1)}" width="26" height="8" rx="2" fill="#7C3AED"/><text x="${p[0]}" y="${(p[1] + 10.7).toFixed(1)}" text-anchor="middle" style="font-size:5.3px;font-weight:700;fill:#fff">${lbl}</text>`;
        } else if ((ap.kover_365 || 0) >= 30 && !isOms) {
          badge += `<circle cx="${(p[0] + 4.2).toFixed(1)}" cy="${(p[1] - 3.5).toFixed(1)}" r="2.1" fill="#D97706" stroke="#fff" stroke-width="0.6"/>`;
        }
      }
      s += `<g class="an-ap-node" data-ap="${c}">`
        + (isOms ? `<circle cx="${p[0]}" cy="${p[1]}" r="9" fill="none" stroke="#E32A2F" stroke-width="1.2" opacity="0.35"/>` : '')
        + `<circle class="an-ap-ring" data-ap="${c}" cx="${p[0]}" cy="${p[1]}" r="${r + 4.2}" fill="none" stroke="#111318" stroke-width="1.6" stroke-dasharray="2 1.5" stroke-opacity="0"/>`
        + `<circle cx="${p[0]}" cy="${p[1]}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${isOms ? 1.5 : 1.6}"/>`
        + badge
        + `<text x="${p[0] + dx}" y="${p[1] + dy}" text-anchor="${anc}" style="font-size:${isOms ? 8.5 : (isSvx ? 6.5 : 7.5)}px;font-weight:700;fill:${isOms ? '#C0262B' : 'var(--ink)'};paint-order:stroke;stroke:var(--land);stroke-width:2.2px">${c}${isSvx ? ' (база RW)' : ' · ' + esc(ANIM.names[c] || '')}</text>`
        + `<circle cx="${p[0]}" cy="${p[1]}" r="10.5" fill="transparent"/>`
        + `</g>`;
    });
    s += '<g class="an-planes"></g>';
    const svg = $('.an-svg');
    svg.innerHTML = s;
    setViewBox();

    $$('.an-ap-node').forEach(g => {
      const c = g.dataset.ap;
      g.onmouseenter = ev => {
        const ap = ANIM.airports[c] || {}, sp = ANIM.spokes[c];
        const pax = ap.pax_2025 ? `${fmt(ap.pax_2025 / 1e6, 2)} млн пасс.` : 'пасс. н/д';
        const kov = ap.kover_365 != null ? `Ковёр: ${ap.kover_365} дн.` : '';
        const hub = ap.comp_hub ? `<br><b>⚠ ${esc(ap.comp_hub_note)}</b>` : '';
        const pnl = sp && sp.base ? `<br>Луч OMS–${c}: ${sp.base.fs}/${sp.base.fw} нед · итог ${sg(sp.base.res, 1)} млн ₽` : '';
        showTip(ev, `<b>${c} · ${esc(ap.city || c)}</b> (${esc(ap.region || '')})<br>${pax}${kov ? ' · ' + kov : ''}${hub}${pnl}<small>Клик — открыть карточку аэропорта</small>`);
      };
      g.onmouseleave = hideTip;
      g.onclick = ev => { if (svg._dragged) return; ev.stopPropagation(); selectAirport(c, true); };
    });

    $$('.an-arc-hit').forEach(p => {
      const c = p.dataset.sp;
      p.onmouseenter = ev => {
        const sp = ANIM.spokes[c];
        if (!sp) return;
        const b = sp.base;
        const comp = sp.comp && sp.comp.tt && sp.comp.tt.length ? sp.comp.tt.map(x => x.carrier).filter((v, i, a) => a.indexOf(v) === i).join(', ') : (sp.comp && sp.comp.direct && sp.comp.direct.length ? sp.comp.direct.join(', ') : 'прямых конкурентов нет');
        const eco = b ? `Частота: ${b.fs}/${b.fw} нед · LF ${Math.round(b.lf * 100)}% · Итог ${sg(b.res, 1)} млн ₽` : (sp.est ? `Спрос пары (база): ${fmt(sp.est.od_base)} поездок/год` : '');
        showTip(ev, `<b>Луч OMS ↔ ${c} (${esc(sp.city)})</b><br>${sp.km} км · БЧ ${sp.bh_min ? (sp.bh_min / 60).toFixed(1) + 'ч' : '—'}<br>${eco}<br>Конкуренты: ${esc(comp)}<small>Клик — разобрать луч и рейсы</small>`);
      };
      p.onmouseleave = hideTip;
      p.onclick = ev => { if (svg._dragged) return; ev.stopPropagation(); selectSpoke(c, true); };
    });
    renderMapHighlights();
  }

  function renderInspector() {
    $$('.an-itabs button').forEach(b => b.classList.toggle('on', b.dataset.it === ST.inspTab));
    const box = $('.an-ibody');
    if (ST.inspTab === 'airport') {
      const c = ST.selAirport || 'OMS';
      const ap = ANIM.airports[c];
      if (!ap) { box.innerHTML = '<div class="sub">Нет данных по аэропорту.</div>'; return; }
      const sp = c !== 'OMS' ? ANIM.spokes[c] : null;
      const mx = Math.max(...(ap.seas || [1]), 1);
      const seaHtml = (ap.seas && ap.seas.length)
        ? `<div class="an-sec"><h4>Сезонность пассажиропотока (12 мес.) <span class="sub">пик ${MON[ap.seas.indexOf(Math.max(...ap.seas))]}</span></h4><div class="an-spark">${ap.seas.map((v, i) => `<i style="height:${(v / mx * 100).toFixed(0)}%" title="${MON[i]}: ×${v.toFixed(2)}"></i>`).join('')}</div><div class="an-spark-l"><span>янв</span><span>апр</span><span>июл</span><span>окт</span><span>дек</span></div></div>`
        : '';

      let hubBanner = '';
      if (ap.comp_hub) hubBanner = `<div class="an-alert red"><b>Хаб конкурента (${esc(ap.comp_hub_carrier)}):</b> ${esc(ap.comp_hub_note)}</div>`;
      else if (c === 'SVX') hubBanner = `<div class="an-alert blue"><b>Действующая база Red Wings (Кольцово):</b> ${esc(ap.comp_hub_note)}</div>`;
      else if (c === 'OMS') hubBanner = `<div class="an-alert ok"><b>Кандидат в хаб Red Wings:</b> 13 авиакомпаний в зимнем расписании OMS, доминирующего хаба конкурентов нет · «Ковёр» 7 дн./год</div>`;

      let compHtml = '';
      if (c === 'OMS') {
        compHtml = `<div class="an-sec"><h4>Все авиакомпании в расписании OMS (зима 2026/27) <span class="an-pill">${ap.oms_carriers.length} а/к</span></h4>
          <table class="an-mini"><thead><tr><th>Перевозчик</th><th class="n">Выл./нед</th><th>Направления</th><th>ВС</th></tr></thead>
          <tbody>${ap.oms_carriers.map(x => `<tr><td><b>${esc(x.carrier)}</b><div class="sub mono" style="font-size:10px">${esc(x.flts.slice(0, 2).join(', '))}</div></td><td class="n">${x.deps_wk ? x.deps_wk : '<span class="sub">вне 7–13.12</span>'}</td><td>${esc(x.dests.join(', '))}</td><td class="mono">${esc(x.ac.join(', '))}</td></tr>`).join('')}</tbody></table></div>`;
        if (ap.tariffs && ap.tariffs.length) {
          compHtml += `<div class="an-sec"><h4>Ключевые тарифы аэропорта Омск <span class="sub">pdf 21.08.2026</span></h4>
            <table class="an-mini"><tbody>${ap.tariffs.map(t => `<tr><td>${esc(t.article)}</td><td class="n"><b>${fmt(t.price)} ₽</b><div class="sub">${esc(t.unit)}</div></td></tr>`).join('')}</tbody></table>
            <div class="sub" style="margin-top:4px">Примечание: справочно к базовой ставке наземного обслуживания 96 089 ₽/рейс без двойного счёта.</div></div>`;
        }
      } else {
        if (sp && sp.comp) {
          const tt = sp.comp.tt || [];
          const dir = sp.comp.direct || [];
          const tr = sp.comp.conn || [];
          compHtml += `<div class="an-sec"><h4>Конкуренция на линии OMS ↔ ${c}</h4>`;
          if (tt.length) {
            compHtml += `<table class="an-mini"><thead><tr><th>А/к и рейс</th><th>ВС</th><th>Дни</th><th>В OMS</th></tr></thead>
              <tbody>${tt.map(r => `<tr><td><b>${esc(r.carrier)}</b> <span class="mono">${esc(r.flt)}</span></td><td>${esc(r.ac)}</td><td>${esc(r.wd)}</td><td class="mono">${esc(r.arr)}–${esc(r.dep)}</td></tr>`).join('')}</tbody></table>`;
          } else {
            compHtml += `<div class="sub">В зимнем расписании Омска (2026/27) прямых регулярных рейсов на этом плече нет.</div>`;
          }
          compHtml += `<div class="an-kgrid" style="margin-top:6px">
            <div class="an-kbox"><b>Прямые а/к (p40)</b><span>${dir.length ? esc(dir.join(', ')) : 'нет'}</span></div>
            <div class="an-kbox"><b>С пересадкой (p40)</b><span>${tr.length ? esc(tr.join(', ')) : '—'}</span></div>
            <div class="an-kbox"><b>Тариф 20кг (прям/пер.)</b><span>${sp.comp.fare_dir ? fmt(sp.comp.fare_dir) + ' ₽' : '—'} / ${sp.comp.fare_tr ? fmt(sp.comp.fare_tr) + ' ₽' : '—'}</span></div>
          </div></div>`;
        }
        if (ap.rpc_carriers && ap.rpc_carriers.length) {
          compHtml += `<div class="an-sec"><h4>Присутствие перевозчиков в ${c} (7–13.12.2026)</h4>
            <table class="an-mini"><thead><tr><th>Авиакомпания</th><th>Направления выборки</th><th>ВС</th></tr></thead>
            <tbody>${ap.rpc_carriers.map(x => `<tr><td><b>${esc(x.carrier)}</b>${x.rw ? ' <span class="an-pill r">RW</span>' : ''}</td><td>${esc(x.dests.join(', '))}</td><td>${esc(x.ac.join(', ') || '—')}</td></tr>`).join('')}</tbody></table></div>`;
        }
      }

      const rwHtml = (ap.rw_now && ap.rw_now.length)
        ? `<div class="an-sec"><h4>Действующие маршруты Red Wings из ${c}</h4><div>${ap.rw_now.map(x => `<span class="an-pill" style="margin:2px 4px 2px 0">${esc(x.pair)} · ${x.freq ?? '?'}/нед (${esc(x.status)})</span>`).join('')}</div></div>`
        : '';
      const subHtml = (ap.subs_2026 && ap.subs_2026.length)
        ? `<div class="an-sec"><h4>Субсидии Росавиации 2026 (${ap.subs_2026.length})</h4>
            <table class="an-mini"><tbody>${ap.subs_2026.slice(0, 6).map(x => `<tr><td><b>${esc(x.pair)}</b></td><td>${esc(x.airline)}</td><td class="n">${esc(x.freq)}/нед · ${esc(x.ac)}</td></tr>`).join('')}</tbody></table></div>`
        : '';

      box.innerHTML = `
        <div class="an-ihead">
          <div>
            <div class="an-icode">${c} <span style="font-family:var(--f);font-size:17px">${esc(ap.city)}</span></div>
            <div class="sub">${esc(ap.region)}${ap.fd ? ' · ' + esc(ap.fd) : ''}${ap.icao ? ' · ICAO ' + ap.icao : ''} · UTC+${ap.tz}</div>
          </div>
          ${sp ? `<button type="button" class="btn sm red an-go-spoke" data-sp="${c}">Экономика луча →</button>` : ''}
        </div>
        ${hubBanner}
        <div class="an-kgrid">
          <div class="an-kbox"><b>Пасс. 2025</b><span>${ap.pax_2025 ? (ap.pax_qual + ' ' + fmt(ap.pax_2025 / 1e6, 2) + ' млн') : '—'}</span></div>
          <div class="an-kbox"><b>Охват (60 мин)</b><span>${ap.pop_2025 ? fmt(ap.pop_2025 / 1e3, 0) + ' тыс.' : '—'}</span></div>
          <div class="an-kbox"><b>Ср. зарплата ’24</b><span>${ap.wage_2024 ? fmt(ap.wage_2024) + ' ₽' : '—'}</span></div>
          <div class="an-kbox"><b>ВПП / Режим</b><span>${ap.runway_m ? fmt(ap.runway_m) + ' м' : '—'} · ${esc(ap.h24)}</span></div>
          <div class="an-kbox"><b>SSJ / ТО</b><span>${esc(ap.ssj_ops)} · ${esc(ap.ssj_mro)}</span></div>
          <div class="an-kbox"><b>«Ковёр» 365д / 1П26</b><span class="${(ap.kover_365 || 0) > 60 ? 'dn' : ''}">${ap.kover_365 ?? '—'} / ${ap.kover_h1_26 ?? '—'} дн.</span></div>
        </div>
        <div class="sub">Погода (год): мороз ${ap.frost ?? '—'} дн. · ветер ${ap.wind ?? '—'} дн. · сложная погода ${ap.bad_wx ?? '—'} дн. · Статус RW: ${esc(ap.rw_support)}</div>
        ${compHtml}
        ${rwHtml}
        ${subHtml}
        ${seaHtml}`;

      const goBtn = box.querySelector('.an-go-spoke');
      if (goBtn) goBtn.onclick = () => selectSpoke(goBtn.dataset.sp, true);
      return;
    }

    if (ST.inspTab === 'flight') {
      const m = curMode();
      let f = m.flights.find(x => x.id === ST.selFlightId);
      if (!f) f = m.flights.find(x => (x.o === ST.selSpoke || x.d === ST.selSpoke) && ST.t >= x.t1 && ST.t < x.t2) || m.flights.find(x => x.o === ST.selSpoke || x.d === ST.selSpoke) || m.flights[0];
      const spCode = f ? (f.o === 'OMS' ? f.d : f.o) : ST.selSpoke;
      const sp = ANIM.spokes[spCode];
      let fltHtml = '';
      if (f) {
        const col = COLORS[f.ac] || '#E32A2F';
        const tzO = (ANIM.airports[f.o] || {}).tz || 6, tzD = (ANIM.airports[f.d] || {}).tz || 6;
        const status = ST.t >= f.t1 && ST.t < f.t2 ? `В полёте · ${Math.round((ST.t - f.t1) / (f.t2 - f.t1) * 100)}%` : (ST.t >= f.t2 ? 'Прибыл' : 'По графику');
        const fDay = Math.floor(f.t1 / 1440);
        const dayLegs = m.flights.filter(x => x.ac === f.ac && Math.floor(x.t1 / 1440) === fDay).sort((a, b) => a.t1 - b.t1);
        const rotHtml = dayLegs.map((x, idx) => {
          const prev = dayLegs[idx - 1];
          const gap = prev ? `<span class="sub" style="font-size:10.5px">оборот ${x.t1 - prev.t2}м →</span>` : '';
          return `${gap}<button type="button" class="an-leg${x.id === f.id ? ' on' : ''}" data-fid="${x.id}">${x.id}: ${x.o}→${x.d} ${fmtHM(x.t1)}</button>`;
        }).join('');
        fltHtml = `
          <div class="an-ihead">
            <div>
              <div class="an-icode"><span style="color:${col}">${f.ac}</span> · ${f.o} → ${f.d}</div>
              <div class="sub">Рейс <b class="mono">${f.id}</b> · волна: ${f.wave === 'am' ? 'утро' : f.wave === 'pm' ? 'вечер' : 'старт'} · <span class="an-pill b">${status}</span></div>
            </div>
            <div class="an-row">
              <button type="button" class="btn sm an-jump-flt" data-fid="${f.id}">⏮ К вылету</button>
              <button type="button" class="btn sm an-open-ap" data-ap="${spCode}">Аэропорт ${spCode}</button>
            </div>
          </div>
          <div class="an-kgrid">
            <div class="an-kbox"><b>Вылет (${f.o} UTC+${tzO})</b><span>${fmtTime(f.t1, tzO)}</span><div class="sub">${fmtHM(f.t1)} OMS / ${fmtHM(f.t1, 3)} MSK</div></div>
            <div class="an-kbox"><b>Прилёт (${f.d} UTC+${tzD})</b><span>${fmtTime(f.t2, tzD)}</span><div class="sub">${fmtHM(f.t2)} OMS / ${fmtHM(f.t2, 3)} MSK</div></div>
            <div class="an-kbox"><b>Блок-время / Налёт ВС</b><span>${(f.bh / 60).toFixed(2)} ч</span><div class="sub">борта ${m.stats.ac_bh[f.ac].toFixed(1)} / 70.0 ч нед.</div></div>
          </div>
          <div class="an-sec"><h4>Суточная ротация ${f.ac} (${DAYS[Math.min(6, fDay)]})</h4><div class="an-rot">${rotHtml}</div></div>`;
      }

      let spHtml = '';
      if (sp) {
        const b = sp.base, c = sp.cautious;
        if (b) {
          spHtml += `<div class="an-sec"><h4>Экономика луча OMS ↔ ${sp.code} (${esc(sp.city)}, ${sp.km} км) <span class="an-pill ${b.res >= 0 ? 'g' : 'r'}">${sg(b.res, 1)} млн ₽</span></h4>
            <table class="an-mini"><thead><tr><th>Показатель</th><th class="n">Базовый</th><th class="n">Осторожный</th></tr></thead><tbody>
              <tr><td>Частота (лето / зима)</td><td class="n">${b.fs} / ${b.fw} нед</td><td class="n">${c ? `${c.fs} / ${c.fw} нед` : 'не вошёл в сеть'}</td></tr>
              <tr><td>Местные + трансфер пасс.</td><td class="n">${fmt(b.local)} + ${fmt(b.tr)}</td><td class="n">${c ? `${fmt(c.local)} + ${fmt(c.tr)}` : '—'}</td></tr>
              <tr><td>Загрузка LF / Spill</td><td class="n">${Math.round(b.lf * 100)}% / ${fmt(b.spill)}</td><td class="n">${c ? `${Math.round(c.lf * 100)}% / ${fmt(c.spill)}` : '—'}</td></tr>
              <tr><td>Выручка / Расходы, млн ₽</td><td class="n">${fmt(b.rev, 1)} / ${fmt(b.cost, 1)}</td><td class="n">${c ? `${fmt(c.rev, 1)} / ${fmt(c.cost, 1)}` : '—'}</td></tr>
              <tr><td><b>Итог луча, млн ₽/год</b></td><td class="n"><b class="${b.res >= 0 ? 'up' : 'dn'}">${sg(b.res, 1)}</b></td><td class="n">${c ? `<b class="${c.res >= 0 ? 'up' : 'dn'}">${sg(c.res, 1)}</b>` : '—'}</td></tr>
            </tbody></table>
            <div class="sub" style="margin-top:5px">Дальность: ${esc(b.light)} · Ж/д: ${sp.rail_hr ?? '—'} ч · Субсидия в модели: ${esc(b.sub_rule)}</div>
            <div class="sub" style="margin-top:3px">Источник спроса: ${esc(b.src)}</div></div>`;
        } else if (sp.est) {
          spHtml += `<div class="an-sec"><h4>Оценка спроса стартового луча OMS ↔ ${sp.code} (${sp.km} км)</h4>
            <div class="an-kgrid">
              <div class="an-kbox"><b>Сегментов (база)</b><span>${fmt(sp.est.seg_base)}</span></div>
              <div class="an-kbox"><b>OD поездок (база/ост.)</b><span>${fmt(sp.est.od_base)} / ${fmt(sp.est.od_caut)}</span></div>
              <div class="an-kbox"><b>Ж/д · сейчас маршрут</b><span>${sp.rail_hr ?? '—'} ч · ${esc(sp.est.route_now)}</span></div>
            </div></div>`;
        }

        const dirC = sp.comp && sp.comp.direct && sp.comp.direct.length ? sp.comp.direct.join(', ') : (sp.comp && sp.comp.tt && sp.comp.tt.length ? sp.comp.tt.map(x => x.carrier).filter((v, i, a) => a.indexOf(v) === i).join(', ') : 'нет');
        const trC = sp.comp && sp.comp.conn && sp.comp.conn.length ? sp.comp.conn.join(', ') : '—';
        spHtml += `<div class="an-sec"><h4>Тарифы, конкуренты и субсидии 2026 на OMS ↔ ${sp.code}</h4>
          <div class="an-kgrid">
            <div class="an-kbox"><b>Тариф модели / Прям. конк.</b><span>${sp.fare_model ? fmt(sp.fare_model) + ' ₽' : '—'} / ${sp.comp && sp.comp.fare_dir ? fmt(sp.comp.fare_dir) + ' ₽' : '—'}</span></div>
            <div class="an-kbox"><b>Пересад. конк. (20 кг)</b><span>${sp.comp && sp.comp.fare_tr ? fmt(sp.comp.fare_tr) + ' ₽' : '—'}</span></div>
            <div class="an-kbox"><b>Прямых кресел конк./дн.</b><span>${sp.comp && sp.comp.seats_day != null ? sp.comp.seats_day : '—'}</span></div>
          </div>
          <div class="sub" style="margin-top:4px">Прямые конкуренты: <b>${esc(dirC)}</b> · Стыковочные: ${esc(trC)}</div>
          ${sp.subs_2026 && sp.subs_2026.length ? `<div style="margin-top:4px">${sp.subs_2026.map(s => `<span class="an-pill y">Субсидия 2026: ${esc(s.airline)} · ${esc(s.freq)}/нед · ${esc(s.ac)}</span>`).join(' ')}</div>` : '<div class="sub">В перечне субсидий Росавиации 2026 эта пара с другими а/к не закреплена.</div>'}
        </div>`;
      }

      box.innerHTML = fltHtml + spHtml;
      box.querySelectorAll('.an-leg').forEach(b => b.onclick = () => selectFlight(b.dataset.fid, true));
      const jb = box.querySelector('.an-jump-flt');
      if (jb) jb.onclick = () => selectFlight(jb.dataset.fid, true);
      const ob = box.querySelector('.an-open-ap');
      if (ob) ob.onclick = () => selectAirport(ob.dataset.ap, true);
      return;
    }

    // Вкладка "Стыковки в OMS" (45..240 мин между прилётом в OMS и вылетом из OMS)
    const m = curMode();
    const wfs = winFlights();
    const ins = wfs.filter(f => f.d === 'OMS');
    const outs = wfs.filter(f => f.o === 'OMS');
    const conns = [];
    ins.forEach(inf => {
      outs.forEach(outf => {
        if (inf.o === outf.d) return;
        const w = outf.t1 - inf.t2;
        if (w >= 45 && w <= 240) {
          conns.push({ inf, outf, wait: w });
        }
      });
    });
    conns.sort((a, b) => a.inf.t2 - b.inf.t2 || a.wait - b.wait);
    const filtered = ST.hubFilterAp === 'ALL' ? conns : conns.filter(x => x.inf.o === ST.hubFilterAp || x.outf.d === ST.hubFilterAp);
    const apOpts = ['ALL', ...m.spokes];
    box.innerHTML = `
      <div class="an-ihead">
        <div>
          <div style="font-weight:700;font-size:14px">Волны стыковок через Омск (окно 45–240 мин)</div>
          <div class="sub">Показано: ${filtered.length} из ${conns.length} стыковок в окне ${ST.day === -1 ? 'недели' : DAYS[ST.day]}</div>
        </div>
        <select class="an-hfilt" style="font-size:12px;padding:3px 7px">${apOpts.map(c => `<option value="${c}" ${c === ST.hubFilterAp ? 'selected' : ''}>${c === 'ALL' ? 'Все лучи' : c + ' · ' + esc(ANIM.names[c] || '')}</option>`).join('')}</select>
      </div>
      ${ST.mode === 'start' && ANIM.ramp_conns && ANIM.ramp_conns.length ? `<div class="an-alert blue">В стартовой фазе проверены <b>${ANIM.ramp_conns.length}</b> стыковки в окне 45–240 мин (из oms_ramp_connections.csv), однако сквозной тариф/MCT требуют оформления на этапе запуска.</div>` : ''}
      ${filtered.length ? `<table class="an-mini"><thead><tr><th>Цепочка через OMS</th><th>Прилёт</th><th>Вылет</th><th class="n">Стык</th></tr></thead>
        <tbody>${filtered.slice(0, 60).map(x => `<tr class="click an-crow" data-t="${x.inf.t2}" data-fid="${x.outf.id}"><td><b>${x.inf.o} → OMS → ${x.outf.d}</b><div class="sub">${x.inf.ac} → ${x.outf.ac}</div></td><td class="mono">${fmtTime(x.inf.t2)}</td><td class="mono">${fmtTime(x.outf.t1)}</td><td class="n"><span class="an-pill ${x.wait <= 120 ? 'g' : 'y'}">${x.wait} м</span></td></tr>`).join('')}</tbody></table>`
        : '<div class="sub">В выбранном суточном окне нет пересадок с ожиданием 45–240 мин. Переключите день или выберите режим «Полная хабовая».</div>'}`;
    box.querySelector('.an-hfilt').onchange = e => { ST.hubFilterAp = e.target.value; renderInspector(); };
    box.querySelectorAll('.an-crow').forEach(tr => tr.onclick = () => {
      stop();
      ST.t = +tr.dataset.t;
      ST.selFlightId = tr.dataset.fid;
      renderAllDyn();
    });
  }

  function renderDyn() {
    const m = curMode(), [w0, w1] = winRange(), span = w1 - w0, fs = m.flights, wfs = winFlights();
    if (opts.onSub) opts.onSub(m.sub);
    $('.an-ghint').textContent = `Оборот ≥ ${m.stats.min_turn_min} мин · макс. ${m.stats.max_ac_bh.toFixed(1)} ч/нед. (лимит 70 ч)`;
    $('.an-clock').textContent = fmtClock(ST.t);
    const scr = $('.an-scr'); scr.min = w0; scr.max = w1; scr.value = Math.round(ST.t);
    $('.an-min').textContent = fmtTime(w0); $('.an-max').textContent = fmtTime(w1);
    const steps = stepPoints(); let sIdx = 0;
    for (let i = 0; i < steps.length; i++) if (steps[i] <= ST.t) sIdx = i;
    $('.an-step').textContent = `Событие ${sIdx + 1}/${steps.length}`;

    const active = fs.filter(f => ST.t >= f.t1 && ST.t < f.t2);
    renderMapHighlights();
    const planesG = $('.an-planes');
    planesG.innerHTML = active.map(f => {
      const p0 = ANIM.pts[f.o], p1 = ANIM.pts[f.d]; if (!p0 || !p1) return '';
      const u = Math.min(1, Math.max(0, (ST.t - f.t1) / (f.t2 - f.t1))), pt = bezier(p0, p1, u), col = COLORS[f.ac] || '#E32A2F';
      const isSel = f.id === ST.selFlightId;
      return `<g class="an-plane" data-fid="${f.id}" transform="translate(${pt.x.toFixed(1)},${pt.y.toFixed(1)})"><g transform="rotate(${pt.ang.toFixed(1)})"><path d="M7,0 L2,-1.6 L-3,-6.5 L-4.8,-6.5 L-2,-1.4 L-5.8,-1.1 L-7.2,-3.2 L-8.4,-3.2 L-7.4,0 L-8.4,3.2 L-7.2,3.2 L-5.8,1.1 L-2,1.4 L-4.8,6.5 L-3,6.5 L2,1.6 Z" fill="${col}" stroke="${isSel ? '#111318' : '#fff'}" stroke-width="${isSel ? 1.1 : 0.6}"/></g><rect x="7" y="-11" width="46" height="10" rx="2.5" fill="#fff" fill-opacity="0.94" stroke="${isSel ? '#111318' : col}" stroke-width="${isSel ? 1.2 : 0.7}"/><text x="9" y="-3.8" style="font-size:6.4px;font-weight:700;fill:#111318;font-family:var(--mono)">${f.ac} ${f.d} ${Math.round(u * 100)}%</text></g>`;
    }).join('');
    $$('.an-plane').forEach(g => {
      const fid = g.dataset.fid;
      g.onmouseenter = ev => {
        const f = fs.find(x => x.id === fid); if (!f) return;
        const pct = Math.round((ST.t - f.t1) / (f.t2 - f.t1) * 100);
        showTip(ev, `<b>${f.ac} · рейс ${f.id} (${f.o} → ${f.d})</b><br>Прогресс: ${pct}% · ${fmtTime(f.t1)} – ${fmtTime(f.t2)} OMS<small>Клик — разобрать рейс и ротацию</small>`);
      };
      g.onmouseleave = hideTip;
      g.onclick = ev => { ev.stopPropagation(); selectFlight(fid, false); };
    });

    const stMap = m.aircraft.map(ac => {
      if (active.some(f => f.ac === ac)) return 'fly';
      const prev = [...fs].filter(f => f.ac === ac && f.t2 <= ST.t).pop();
      return (prev && prev.d !== 'OMS') ? 'out' : 'oms';
    });
    $('.an-stat').textContent = `В небе: ${active.length} · В Омске: ${stMap.filter(x => x === 'oms').length} + 1 рез. · На обороте: ${stMap.filter(x => x === 'out').length}`;

    const landedFeed = fs.filter(f => m.feeders.includes(f.o) && f.d === 'OMS' && ST.t >= f.t2 && ST.t <= f.t2 + 135);
    const upWest = fs.filter(f => f.o === 'OMS' && ['KUF', 'GOJ', 'VOG', 'GSV'].includes(f.d) && f.t1 > ST.t && f.t1 <= ST.t + 140);
    const exact = wfs.filter(f => f.t1 === Math.round(ST.t) || f.t2 === Math.round(ST.t));
    let msg = '', isTr = false;
    if (ST.mode === 'full' && landedFeed.length && upWest.length) {
      isTr = true;
      msg = `Стыковочное окно в OMS: фидеры ${[...new Set(landedFeed.map(f => f.o))].join('/')} → западная волна (${[...new Set(upWest.map(f => f.d))].join(', ')})`;
    } else if (exact.length) {
      const dep = exact.filter(f => f.t1 === Math.round(ST.t)).map(f => `${f.ac} ${f.o}→${f.d}`);
      const arr = exact.filter(f => f.t2 === Math.round(ST.t)).map(f => `${f.ac} из ${f.o} в ${f.d}`);
      msg = [dep.length ? 'Вылет: ' + dep.join(', ') : '', arr.length ? 'Прилёт: ' + arr.join(', ') : ''].filter(Boolean).join(' · ');
    } else if (active.length) {
      msg = `В полёте (${active.length} ВС): ` + active.map(f => `${f.ac} ${f.o}→${f.d} (${Math.round((ST.t - f.t1) / (f.t2 - f.t1) * 100)}%)`).join(' · ');
    } else {
      const nxt = wfs.find(f => f.t1 > ST.t);
      msg = nxt ? `Стоянка в OMS · ближайший вылет: ${nxt.ac} ${nxt.o}→${nxt.d} в ${fmtTime(nxt.t1)}` : 'Завершение суточной программы · ночное ТО в Омске';
    }
    $('.an-strip').className = 'an-strip' + (isTr ? ' tr' : '');
    $('.an-msg').textContent = msg;

    $('.an-ticks').innerHTML = (ST.day === -1 ? DAYS : ['00:00', '06:00', '12:00', '18:00', span > 1440 ? '24:00+' : '24:00']).map(x => `<span>${x}</span>`).join('');
    const ph = ((ST.t - w0) / span) * 100;
    $('.an-gantt').innerHTML = m.aircraft.map(ac => {
      const bars = wfs.filter(f => f.ac === ac).map(f => {
        const l = Math.max(0, (f.t1 - w0) / span * 100), r = Math.min(100, (f.t2 - w0) / span * 100), w = Math.max(0.7, r - l);
        const sp = f.o === 'OMS' ? f.d : f.o, bg = m.feeders.includes(sp) ? '#D97706' : COLORS[ac];
        const on = ST.t >= f.t1 && ST.t <= f.t2, sel = f.id === ST.selFlightId;
        return `<div class="an-g-bar${on ? ' on' : ''}${sel ? ' sel' : ''}" data-fid="${f.id}" title="${f.id} ${ac}: ${f.o}→${f.d} (${fmtTime(f.t1)}–${fmtTime(f.t2)})" style="left:${l.toFixed(2)}%;width:${w.toFixed(2)}%;background:${bg}">${w > 4 ? (f.o === 'OMS' ? '→' + f.d : f.o + '→') : ''}</div>`;
      }).join('');
      return `<div class="an-g-row"><div class="an-g-lbl"><span style="color:${COLORS[ac]}">${ac}</span><small>${m.stats.ac_bh[ac].toFixed(1)} ч/нед</small></div><div class="an-g-track">${bars}${ph >= 0 && ph <= 100 ? `<div class="an-g-ph" style="left:${ph.toFixed(2)}%"></div>` : ''}</div></div>`;
    }).join('') + `<div class="an-g-row"><div class="an-g-lbl"><span style="color:var(--muted)">${esc(m.reserve)}</span><small>резерв</small></div><div class="an-g-track" style="opacity:.7"><span class="sub" style="padding:2px 8px;display:inline-block">Горячий резерв в OMS (подмена / «Ковёр» / ТО)</span></div></div>`;
    $$('.an-g-bar').forEach(el => el.onclick = () => selectFlight(el.dataset.fid, true));

    const bRows = wfs.filter(f => ST.day !== -1 || (f.t2 >= ST.t - 180 && f.t1 <= ST.t + 720));
    $('.an-bsum').textContent = `Рейсов в окне: ${wfs.length} · в небе: ${active.length}`;
    $('.an-board').innerHTML = bRows.map(f => {
      const sp = f.o === 'OMS' ? f.d : f.o;
      const tag = ST.t >= f.t1 && ST.t < f.t2 ? `<span class="tag t-model">В полёте ${Math.round((ST.t - f.t1) / (f.t2 - f.t1) * 100)}%</span>` : ST.t >= f.t2 ? '<span class="tag t-fact">Прибыл</span>' : f.t1 - ST.t <= 60 ? `<span class="tag t-asm">Через ${Math.round(f.t1 - ST.t)}м</span>` : '<span class="tag t-req">По графику</span>';
      const isAct = (ST.t >= f.t1 && ST.t < f.t2) || f.id === ST.selFlightId;
      return `<tr class="click${isAct ? ' sel' : ''}" data-fid="${f.id}"><td class="mono">${f.id}</td><td class="mono"><b style="color:${COLORS[f.ac]}">${f.ac}</b></td><td><b>${f.o} → ${f.d}</b> <span class="sub">(${esc(ANIM.names[sp] || sp)})</span></td><td class="mono">${fmtTime(f.t1)}</td><td class="mono">${fmtTime(f.t2)}</td><td class="mono">${(f.bh / 60).toFixed(1)}ч</td><td>${tag}</td></tr>`;
    }).join('');
    $$('.an-board tr').forEach(tr => tr.onclick = () => selectFlight(tr.dataset.fid, true));
  }

  function renderAllDyn() {
    buildDays();
    renderChips();
    renderDyn();
    renderInspector();
  }
  function renderAll() {
    buildDays();
    buildMap();
    renderChips();
    renderDyn();
    renderInspector();
  }

  // Обработчики управления
  $$('.an-spd button').forEach(b => b.onclick = () => { $$('.an-spd button').forEach(x => x.classList.remove('on')); b.classList.add('on'); ST.speed = +b.dataset.s; });
  $('.an-play').onclick = () => ST.playing ? stop() : start();
  $('.an-next').onclick = () => step(1);
  $('.an-prev').onclick = () => step(-1);
  $('.an-reset').onclick = () => { stop(); const [w0] = winRange(), fs = winFlights(); ST.t = fs.length ? Math.max(w0, fs[0].t1) : w0; renderDyn(); };
  $('.an-scr').oninput = e => { stop(); ST.t = +e.target.value; renderDyn(); };
  $('.an-chk-hubs').onchange = e => { ST.showHubs = e.target.checked; buildMap(); renderDyn(); };
  $('.an-chk-comp').onchange = e => { ST.showComp = e.target.checked; buildMap(); renderDyn(); };
  $$('.an-itabs button').forEach(b => b.onclick = () => { ST.inspTab = b.dataset.it; renderInspector(); });
  $('.an-zi').onclick = () => zoomBy(0.75);
  $('.an-zo').onclick = () => zoomBy(1.33);
  $('.an-zr').onclick = () => { ST.vb = { ...BASE_VB }; setViewBox(); };

  // Зум колесом и панорамирование мышью
  const svg = $('.an-svg');
  svg.addEventListener('wheel', ev => {
    ev.preventDefault();
    const r = svg.getBoundingClientRect();
    zoomBy(ev.deltaY > 0 ? 1.15 : 0.87, (ev.clientX - r.left) / r.width, (ev.clientY - r.top) / r.height);
  }, { passive: false });
  let pan = null;
  svg.addEventListener('pointerdown', ev => {
    if (ev.button !== 0) return;
    svg._dragged = false;
    pan = { sx: ev.clientX, sy: ev.clientY, vx: ST.vb.x, vy: ST.vb.y };
  });
  window.addEventListener('pointermove', ev => {
    if (!pan) return;
    const dx = ev.clientX - pan.sx, dy = ev.clientY - pan.sy;
    if (Math.hypot(dx, dy) > 4) { svg._dragged = true; svg.classList.add('panning'); }
    if (!svg._dragged) return;
    const r = svg.getBoundingClientRect();
    ST.vb.x = Math.max(195, Math.min(720 - ST.vb.w, pan.vx - dx * (ST.vb.w / r.width)));
    ST.vb.y = Math.max(195, Math.min(450 - ST.vb.h, pan.vy - dy * (ST.vb.h / r.height)));
    setViewBox();
  });
  window.addEventListener('pointerup', () => { pan = null; svg.classList.remove('panning'); setTimeout(() => { svg._dragged = false; }, 0); });

  renderAll();
  return {
    stop,
    setMode(m) {
      stop();
      ST.mode = m;
      const [w0] = winRange(), fs = winFlights();
      ST.t = fs.length ? Math.max(w0, fs[0].t1 + 60) : w0;
      ST.selFlightId = null;
      if (!curMode().spokes.includes(ST.selSpoke)) ST.selSpoke = curMode().spokes[0] || 'IKT';
      renderAll();
    },
    getState: () => ST,
  };
}
"""


STANDALONE_TEMPLATE = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Омск (OMS): интерактивная карта, аэропорты, конкуренты и рейсы Red Wings</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;700&family=Montserrat+Alternates:wght@500;700&display=swap">
<style>
:root{{
  --paper:#F3F1EC; --paper-2:#E9E6DF; --white:#FFFFFF; --ink:#111318; --ink-3:#252A35;
  --steel:#8C96A6; --muted:#5E6675; --line:#D9D6CF; --red:#E32A2F; --red-d:#C0262B;
  --amber:#F5B841; --green:#3FA772; --sea:#E4EBF0; --land:#FBFAF7; --geo-line:#B9B5AC; --blue:#3E6E95;
  --red-bg:#FBE6E6; --green-bg:#E3F2E9; --amber-bg:#FDF2D9; --blue-bg:#E2ECF4;
  --f:"Onest",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
  --code:"Montserrat Alternates","Onest",system-ui,Arial,sans-serif;
  --mono:ui-monospace,Consolas,"Cascadia Mono",monospace;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--f);font-size:14px;line-height:1.45}}
.top{{background:var(--ink);color:#F4F5F7;padding:10px 0}}
.wrap{{max-width:1380px;margin:0 auto;padding:0 16px}}
.top .wrap{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
.brand{{display:flex;align-items:center;gap:10px;font-family:var(--code);font-weight:700;font-size:16px}}
.brand small{{font-family:var(--f);font-weight:400;color:var(--steel);font-size:13px}}
.back{{margin-left:auto;color:#F4F5F7;text-decoration:none;border:1px solid #2A2F3A;background:var(--ink-3);border-radius:999px;padding:5px 12px;font-size:13px}}
.back:hover{{border-color:#F4F5F7}}
main{{padding:16px 0 36px;display:flex;flex-direction:column;gap:12px}}
.card{{background:var(--white);border:1px solid var(--line);border-radius:16px;padding:16px 18px;min-width:0}}
.hd{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:space-between;margin-bottom:8px}}
h1{{font-family:var(--code);font-size:20px;margin:0}}
h3{{font-size:14.5px;margin:0}}
.sub{{color:var(--muted);font-size:12.5px}}
.seg{{display:inline-flex;background:var(--paper-2);border-radius:10px;padding:3px;flex-wrap:wrap;gap:2px}}
.seg button{{border:0;background:none;padding:5px 10px;border-radius:8px;font-size:12.5px;color:var(--muted);cursor:pointer;font-family:inherit;font-weight:500}}
.seg button.on{{background:var(--white);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}}
.btn{{border:1px solid var(--line);background:var(--white);border-radius:8px;padding:5px 10px;font:inherit;font-size:12.5px;font-weight:500;cursor:pointer}}
.btn:hover{{border-color:var(--ink)}}
.btn.red{{background:var(--red);border-color:var(--red);color:#fff}}
.btn.red:hover{{background:var(--red-d)}}
.btn.sm{{padding:4px 9px;font-size:12px}}
.clock{{font-family:var(--mono);font-size:12.5px;font-weight:700;padding:4px 10px;border-radius:8px;background:var(--paper);border:1px solid var(--line)}}
.mono{{font-family:var(--mono);font-size:12px}}
.tw{{overflow-x:auto;border:1px solid var(--line);border-radius:10px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}}
th{{position:sticky;top:0;background:var(--paper);color:var(--muted);font-size:11px;font-weight:500;text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);z-index:2}}
td{{padding:6px 9px;border-bottom:1px solid var(--paper-2);white-space:nowrap}}
tr.click{{cursor:pointer}}tr.click:hover{{background:var(--paper)}}tr.sel{{background:var(--blue-bg)}}
.tag{{display:inline-block;font-size:11px;font-weight:500;padding:1px 7px;border-radius:999px}}
.t-model{{background:var(--blue-bg);color:var(--blue)}}.t-asm{{background:var(--amber-bg);color:#8A6210}}.t-fact{{background:var(--green-bg);color:#23704A}}.t-req{{background:var(--paper-2);color:var(--muted)}}
.up{{color:#23704A}}.dn{{color:var(--red-d)}}
{PLAYER_CSS}
</style>
</head>
<body>
<header class="top"><div class="wrap">
  <div class="brand"><svg width="24" height="24" viewBox="0 0 24 24"><path d="M21 15.5v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V8.5l-8 5v2l8-2.5V18l-2 1.5V21l3.5-1 3.5 1v-1.5L13 18v-5z" fill="#E32A2F"/></svg>Омск (OMS): интерактивная карта, аэропорты и рейсы <small>SJ-100 · Red Wings</small></div>
  <a class="back" href="redwings_panel.html#net">← Вернуться в панель «02 Сеть»</a>
</div></header>
<main class="wrap">
  <section class="card">
    <div class="hd">
      <div><h1>Интерактивная карта, аэропорты и расписание хаба Омск (OMS)</h1><div class="sub" id="an-sub"></div></div>
      <div class="seg" id="an-mode">
        <button class="on" data-m="radial">Радиальная 5+1 ВС</button>
        <button data-m="full">Полная 7+1 ВС</button>
        <button data-m="start">Старт 2+1 ВС</button>
      </div>
    </div>
    <div id="an-root">{PLAYER_HTML}</div>
  </section>
</main>
<script>
const ANIM = __ANIM__;
{PLAYER_JS}
const player = mountOmsFlightPlayer(document.getElementById('an-root'), ANIM, {{
  mode: 'radial',
  onSub: txt => {{ document.getElementById('an-sub').textContent = txt; }}
}});
document.querySelectorAll('#an-mode button').forEach(b => b.onclick = () => {{
  document.querySelectorAll('#an-mode button').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  player.setMode(b.dataset.m);
}});
</script>
</body>
</html>
"""


def main():
    payload = build_animation_payload()
    out = ROOT / "outputs/oms_flight_animation.html"
    html = STANDALONE_TEMPLATE.replace("__ANIM__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    out.write_text(html, encoding="utf-8")
    summary = ", ".join(
        f"{k}: {v['stats']['total_rotations']} обор./{v['stats']['total_legs']} рейс. (макс. {v['stats']['max_ac_bh']:.1f} ч)"
        for k, v in payload["modes"].items()
    )
    print(f"Анимация полётов: {out.relative_to(ROOT)}, {len(html) // 1024} КБ | {summary}")


if __name__ == "__main__":
    main()
