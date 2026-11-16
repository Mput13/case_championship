"""Собирает данные и автономный экран пошаговой анимации полётов хаба Омск (OMS).

Все частоты, дальности, блок-время и стартовое расписание берутся из таблиц проекта:
  data/assumptions/network.csv
  data/processed/network_routes.csv
  data/external/colleagues/oms_ramp_week_flights.csv
  data/processed/geo_map.json, data/processed/destinations.csv

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


def _rd(path):
    with open(ROOT / path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


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
        # Проверка циклического перехода Вс -> Пн (недельный цикл 10080 мин)
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
    used = {ac: set() for ac in ac_list}  # (day, wave)

    # Утренняя волна: 5 ежедневных стволов (35 оборотов) — по 1 вылету на каждый борт в сутки 05:00..05:40
    morning_spokes = sorted([k for k, v in trunk.items() if v["fs"] >= 7], key=lambda k: -trunk[k]["bh_min"])
    assert len(morning_spokes) == 5
    remaining = {k: v["fs"] - (7 if k in morning_spokes else 0) for k, v in trunk.items()}

    # Равномерное распределение утренних стволов (баланс по минимальному текущему налёту борта)
    rotations = []  # (day, wave, slot_in_wave, ac, spoke, bh_min)
    for day in range(7):
        order_ac = sorted(ac_list, key=lambda ac: (ac_bh[ac], ac))
        for idx, (ac, sp) in enumerate(zip(order_ac, morning_spokes)):
            bh = trunk[sp]["bh_min"]
            ac_bh[ac] += 2 * bh
            used[ac].add((day, "am"))
            rotations.append((day, "am", idx, ac, sp, bh))

    # Вечерняя волна: оставшиеся 15 оборотов (по 3 на каждый из 5 бортов, максимум 1 в вечер на борт)
    eve_pool = []
    for sp, cnt in remaining.items():
        eve_pool.extend([sp] * cnt)
    eve_pool.sort(key=lambda sp: (-trunk[sp]["bh_min"], sp))
    assert len(eve_pool) == 15

    eve_day_cnt = [0] * 7
    eve_ac_cnt = {ac: 0 for ac in ac_list}
    for sp in eve_pool:
        bh = trunk[sp]["bh_min"]
        # Свободные пары (day, ac) с учётом равномерности по дням и налёту <= 70 ч
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

    # Утренняя волна (7 лучей): 5 ежедневных магистралей + фидеры BAX/KJA (привозят трансфер в OMS)
    # Распределяем точно по слотам, сохраняя стыковочные волны:
    am_template = [
        # (spoke, ac_idx, base_min, req_fs_at_least)
        ("UUD", 0, 300, 7),
        ("IKT", 1, 330, 7),
        ("KJA", 2, 420, 7),  # фидер 07:00 -> возврат в OMS к 12:30 перед дневной западной волной
        ("BAX", 3, 510, 5),  # фидер 08:30 -> возврат в OMS к 12:30; на сб/вс BAX не летает (5/нед.)
        ("KUF", 4, 330, 5),  # часть дней (пн, ср, пт, сб, вс) сдвинута или чередуется
        ("GOJ", 5, 315, 7),
        ("VOG", 6, 300, 7),
    ]
    # Точная недельно-сбалансированная матрица из 64 оборотов для 7 бортов (проверена на отсутствие конфликтов):
    # Дневные/вечерние стыковочные обороты распределяются по свободным окнам после 13:50 (t >= d*1440 + 830)
    # 1. Фиксируем утренние ежедневные стволы (UUD, IKT, VOG, GOJ по 7; KJA по 7; KUF 5 утро + 2 день; BAX 5 утро)
    flights_meta = []  # (day, dep_min, ac, spoke, wave)
    rem = {k: v["fs"] for k, v in routes.items()}
    am_days = {
        "UUD": [0, 1, 2, 3, 4, 5, 6],
        "VOG": [0, 1, 2, 3, 4, 5, 6],
        "IKT": [0, 1, 2, 3, 4, 5, 6],
        "GOJ": [0, 1, 2, 3, 4, 5, 6],
        "KJA": [0, 1, 2, 3, 4, 5, 6],
        "KUF": [0, 2, 4, 5, 6],       # 5 утренних (пн,ср,пт,сб,вс) + 3 дневных
        "BAX": [0, 1, 3, 4],          # 4 утренних + 1 дневной (или 5 утренних пн..пт)
    }
    am_days["BAX"] = [0, 1, 3, 4]
    # Лучше BAX 5 раз утром (пн, вт, чт, пт, вс)? В прежней версии BAX летал днём 08:30 в пн, вт, чт, пт -> 4, а с KJA 9/нед.
    # Используем общую 2-волновую упаковку по суткам:
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

    # Оставшиеся обороты (вторая волна дня: западные стыковочные вылеты KUF/GSV/MOW/VOG/GOJ + доп. KJA/BAX/IKT/UUD)
    pm_list = []
    for sp, cnt in rem.items():
        pm_list.extend([sp] * cnt)
    # Сортируем от длинных к коротким и упаковываем с учётом стыковочного окна 13:55..16:00 и оборота >= 60 мин
    pm_list.sort(key=lambda sp: (-routes[sp]["bh_min"], sp))
    pm_used_day = {(d, ac): False for d in range(7) for ac in ac_list}
    pm_slot_day = [0] * 7
    for sp in pm_list:
        bh = routes[sp]["bh_min"]
        best = None
        for d in range(7):
            for ac in ac_list:
                if pm_used_day[(d, ac)]:
                    continue
                if ac_bh[ac] + 2 * bh > MAX_AC_WEEK_MIN:
                    continue
                earliest_dep = max(d * 1440 + 840 + pm_slot_day[d] * 10, day_end[(d, ac)] + TURN_MIN)
                # Не заезжаем на следующее утро позже 00:40+1 (чтобы до 05:00+1 осталось >= 260 мин ночной стоянки)
                arr_back = earliest_dep + 2 * bh + TURN_MIN
                if arr_back > d * 1440 + 1500:
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

    return {"map": geo_map, "pts": sub_pts, "names": sub_names, "modes": modes}


STANDALONE_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Омск (OMS): пошаговая анимация полётов Red Wings</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;700&family=Montserrat+Alternates:wght@500;700&display=swap">
<style>
:root{
  --paper:#F3F1EC; --paper-2:#E9E6DF; --white:#FFFFFF; --ink:#111318; --ink-3:#252A35;
  --steel:#8C96A6; --muted:#5E6675; --line:#D9D6CF; --red:#E32A2F; --red-d:#C0262B;
  --amber:#F5B841; --green:#3FA772; --sea:#E4EBF0; --land:#FBFAF7; --geo-line:#B9B5AC; --blue:#3E6E95;
  --red-bg:#FBE6E6; --green-bg:#E3F2E9; --amber-bg:#FDF2D9; --blue-bg:#E2ECF4;
  --f:"Onest",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
  --code:"Montserrat Alternates","Onest",system-ui,Arial,sans-serif;
  --mono:ui-monospace,Consolas,"Cascadia Mono",monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--f);font-size:14px;line-height:1.45}
.top{background:var(--ink);color:#F4F5F7;padding:10px 0}
.wrap{max-width:1360px;margin:0 auto;padding:0 16px}
.top .wrap{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-family:var(--code);font-weight:700;font-size:16px}
.brand small{font-family:var(--f);font-weight:400;color:var(--steel);font-size:13px}
.back{margin-left:auto;color:#F4F5F7;text-decoration:none;border:1px solid #2A2F3A;background:var(--ink-3);border-radius:999px;padding:5px 12px;font-size:13px}
.back:hover{border-color:#F4F5F7}
main{padding:18px 0 36px;display:flex;flex-direction:column;gap:14px}
.card{background:var(--white);border:1px solid var(--line);border-radius:16px;padding:16px 18px;min-width:0}
.hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:space-between;margin-bottom:8px}
h1{font-family:var(--code);font-size:20px;margin:0}
h2{font-size:15px;margin:0}
.sub{color:var(--muted);font-size:12.5px}
.seg{display:inline-flex;background:var(--paper-2);border-radius:10px;padding:3px;flex-wrap:wrap;gap:2px}
.seg button{border:0;background:none;padding:5px 10px;border-radius:8px;font-size:12.5px;color:var(--muted);cursor:pointer;font-family:inherit;font-weight:500}
.seg button.on{background:var(--white);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.btn{border:1px solid var(--line);background:var(--white);border-radius:8px;padding:5px 10px;font:inherit;font-size:12.5px;font-weight:500;cursor:pointer}
.btn:hover{border-color:var(--ink)}
.btn.red{background:var(--red);border-color:var(--red);color:#fff}
.btn.red:hover{background:var(--red-d)}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.clock{font-family:var(--mono);font-size:13px;font-weight:700;padding:4px 10px;border-radius:8px;background:var(--paper);border:1px solid var(--line)}
.scrub{display:flex;align-items:center;gap:10px;margin-top:8px}
.scrub input[type=range]{flex:1;accent-color:var(--red);cursor:pointer}
.mono{font-family:var(--mono);font-size:12px}
.strip{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;padding:8px 12px;border-radius:10px;background:var(--paper);border-left:3px solid var(--red);font-size:13px}
.strip.tr{background:var(--amber-bg);border-left-color:#B45309}
.map-box{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--sea)}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--muted);padding:8px 12px;background:var(--white);border-top:1px solid var(--line)}
.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:0}
.g-ticks{display:grid;grid-template-columns:86px 1fr;gap:8px;font-family:var(--mono);font-size:11px;color:var(--muted);margin-bottom:4px}
.g-ticks div{display:flex;justify-content:space-between}
.g-row{display:grid;grid-template-columns:86px 1fr;gap:8px;align-items:center;margin-bottom:5px}
.g-lbl{font-family:var(--mono);font-size:11.5px;font-weight:700;line-height:1.15}
.g-lbl small{display:block;font-weight:500;color:var(--muted);font-size:10.5px}
.g-track{position:relative;height:22px;background:var(--paper);border:1px solid var(--line);border-radius:6px;overflow:hidden}
.g-bar{position:absolute;top:2px;bottom:2px;border-radius:4px;color:#fff;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;cursor:pointer;opacity:.86;overflow:hidden;white-space:nowrap}
.g-bar:hover{opacity:1;outline:1.5px solid var(--ink);z-index:3}
.g-bar.on{opacity:1;outline:2px solid #fff;box-shadow:0 0 0 1.5px var(--ink);z-index:4}
.g-ph{position:absolute;top:0;bottom:0;width:2px;background:var(--red);z-index:5;pointer-events:none}
.tw{overflow-x:auto;max-height:220px;border:1px solid var(--line);border-radius:10px}
table{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}
th{position:sticky;top:0;background:var(--paper);color:var(--muted);font-size:11px;font-weight:500;text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);z-index:2}
td{padding:6px 9px;border-bottom:1px solid var(--paper-2);white-space:nowrap}
tr.click{cursor:pointer}tr.click:hover{background:var(--paper)}tr.act{background:var(--blue-bg)}
.tag{display:inline-block;font-size:11px;font-weight:500;padding:1px 7px;border-radius:999px}
.t-fly{background:var(--blue-bg);color:var(--blue)}.t-turn{background:var(--amber-bg);color:#8A6210}.t-ok{background:var(--green-bg);color:#23704A}.t-wait{background:var(--paper-2);color:var(--muted)}
</style>
</head>
<body>
<header class="top"><div class="wrap">
  <div class="brand"><svg width="24" height="24" viewBox="0 0 24 24"><path d="M21 15.5v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V8.5l-8 5v2l8-2.5V18l-2 1.5V21l3.5-1 3.5 1v-1.5L13 18v-5z" fill="#E32A2F"/></svg>Омск (OMS): анимация полётов <small>SJ-100 · Red Wings</small></div>
  <a class="back" href="redwings_panel.html#net">← Вернуться в панель «02 Сеть»</a>
</div></header>
<main class="wrap">
  <section class="card">
    <div class="hd">
      <div><h1>Пошаговое расписание хаба Омск (OMS)</h1><div class="sub" id="an-sub"></div></div>
      <div class="seg" id="an-mode">
        <button class="on" data-m="radial">Радиальная 5+1 ВС</button>
        <button data-m="full">Полная 7+1 ВС</button>
        <button data-m="start">Старт 2+1 ВС</button>
      </div>
    </div>
    <div class="hd" style="margin-bottom:0">
      <div class="seg" id="an-day"></div>
      <div class="row">
        <button class="btn" id="an-reset" title="В начало">⏮</button>
        <button class="btn" id="an-prev">◀ Шаг</button>
        <button class="btn red" id="an-play" style="min-width:86px">▶ Пуск</button>
        <button class="btn" id="an-next">Шаг ▶</button>
      </div>
      <div class="row">
        <div class="seg" id="an-spd">
          <button data-s="15">×15</button>
          <button class="on" data-s="60">×60</button>
          <button data-s="180">×180</button>
        </div>
        <span class="clock" id="an-clock">Пн 05:00 OMS</span>
      </div>
    </div>
    <div class="scrub">
      <span class="mono" id="an-min">00:00</span>
      <input type="range" id="an-scr" min="0" max="1440" value="300">
      <span class="mono" id="an-max">24:00</span>
    </div>
  </section>

  <div class="strip" id="an-strip">
    <span id="an-msg"></span>
    <span class="mono" id="an-step"></span>
  </div>

  <div class="map-box">
    <svg id="an-svg" viewBox="255 245 410 155" style="width:100%;height:300px;display:block" preserveAspectRatio="xMidYMid meet"></svg>
    <div class="legend">
      <span><i style="background:#E32A2F"></i>База OMS + резерв</span>
      <span><i style="background:#3FA772"></i>Прибыльный ствол</span>
      <span><i style="background:#D97706"></i>Фидер (BAX/KJA)</span>
      <span><i style="background:#3E6E95"></i>Стартовый луч (UFA/NOZ)</span>
      <span style="margin-left:auto" id="an-stat"></span>
    </div>
  </div>

  <section class="card">
    <div class="hd"><h2>Таймлайн ротации бортов (OMS UTC+6 · клик по рейсу = прыжок)</h2><span class="sub" id="an-ghint"></span></div>
    <div class="g-ticks"><span>Борт</span><div id="an-ticks"></div></div>
    <div id="an-gantt"></div>
  </section>

  <section class="card">
    <div class="hd"><h2>Табло рейсов (клик = перейти к вылету)</h2><span class="sub" id="an-bsum"></span></div>
    <div class="tw">
      <table>
        <thead><tr><th>Рейс</th><th>Борт</th><th>Маршрут</th><th>Вылет OMS</th><th>Прилёт OMS</th><th>БЧ</th><th>Статус</th></tr></thead>
        <tbody id="an-board"></tbody>
      </table>
    </div>
  </section>
</main>
<script>
const ANIM = __ANIM__;
const DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const COLORS = { 'AC-1': '#2563EB', 'AC-2': '#0D9488', 'AC-3': '#D97706', 'AC-4': '#E32A2F', 'AC-5': '#7C3AED', 'AC-6': '#0284C7', 'AC-7': '#16A34A', 'S1': '#2563EB', 'S2': '#E32A2F' };
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const ST = { mode: 'radial', day: 0, t: 390, playing: false, speed: 60, raf: null, lastTs: null };

function fmtTime(m) {
  m = Math.max(0, Math.round(m));
  const d = Math.floor(m / 1440), hh = String(Math.floor((m % 1440) / 60)).padStart(2, '0'), mm = String(m % 60).padStart(2, '0');
  return `${d < 7 ? DAYS[d] : 'Пн+'} ${hh}:${mm}`;
}
function fmtClock(m) {
  const msk = (Math.round(m) - 180 + 10080) % 10080;
  return `${fmtTime(m)} OMS (${String(Math.floor((msk % 1440) / 60)).padStart(2, '0')}:${String(msk % 60).padStart(2, '0')} MSK)`;
}
const curMode = () => ANIM.modes[ST.mode];
const winRange = () => ST.day === -1 ? [0, Math.max(10080, ...curMode().flights.map(f => f.t2)) + 20] : [ST.day * 1440, ST.day * 1440 + ((ST.mode === 'start' && ST.day === 6) ? 1530 : 1440)];
const winFlights = () => { const [w0, w1] = winRange(); return curMode().flights.filter(f => f.t2 >= w0 && f.t1 <= w1); };
const stepPoints = () => { const [w0, w1] = winRange(), s = new Set([w0]); winFlights().forEach(f => { if (f.t1 >= w0 && f.t1 <= w1) s.add(f.t1); if (f.t2 >= w0 && f.t2 <= w1) s.add(f.t2); }); return [...s].sort((a, b) => a - b); };
const routeColor = c => curMode().feeders.includes(c) ? '#D97706' : curMode().start_only.includes(c) ? '#3E6E95' : '#3FA772';
function bezier(p0, p1, u) {
  const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2 - Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * 0.16;
  const x = (1 - u) * (1 - u) * p0[0] + 2 * (1 - u) * u * mx + u * u * p1[0];
  const y = (1 - u) * (1 - u) * p0[1] + 2 * (1 - u) * u * my + u * u * p1[1];
  const dx = 2 * (1 - u) * (mx - p0[0]) + 2 * u * (p1[0] - mx), dy = 2 * (1 - u) * (my - p0[1]) + 2 * u * (p1[1] - my);
  return { x, y, ang: Math.atan2(dy, dx) * 180 / Math.PI };
}
function buildDays() {
  $('#an-day').innerHTML = DAYS.map((d, i) => `<button class="${ST.day === i ? 'on' : ''}" data-d="${i}">${d}</button>`).join('') + `<button class="${ST.day === -1 ? 'on' : ''}" data-d="-1">7 дн.</button>`;
  $$('#an-day button').forEach(b => b.onclick = () => { stop(); ST.day = +b.dataset.d; const [w0] = winRange(), fs = winFlights(); ST.t = fs.length ? Math.max(w0, fs[0].t1 - 15) : w0; renderAll(); });
}
function buildMap() {
  const P = ANIM.pts, o = P.OMS, m = curMode();
  let s = `<rect x="200" y="200" width="520" height="250" fill="var(--sea)"/><path d="${ANIM.map}" fill="var(--land)" stroke="var(--geo-line)" stroke-width="0.7"/><g id="an-arcs">`;
  m.spokes.forEach(c => {
    const p = P[c]; if (!p) return;
    const mx = (o[0] + p[0]) / 2, my = (o[1] + p[1]) / 2 - Math.hypot(p[0] - o[0], p[1] - o[1]) * 0.16;
    s += `<path id="an-arc-${c}" d="M${o[0]},${o[1]} Q${mx.toFixed(1)},${my.toFixed(1)} ${p[0]},${p[1]}" fill="none" stroke="${routeColor(c)}" stroke-width="1.4" stroke-opacity="0.3" stroke-linecap="round"/>`;
  });
  s += '</g>';
  if (P.SVX) s += `<circle cx="${P.SVX[0]}" cy="${P.SVX[1]}" r="2.2" fill="none" stroke="var(--muted)" stroke-width="0.9" stroke-dasharray="1.5 1.5"/><text x="${P.SVX[0]}" y="${P.SVX[1] - 4.5}" text-anchor="middle" style="font-size:6.5px;fill:var(--muted)">SVX (база)</text>`;
  m.spokes.forEach(c => {
    const p = P[c]; if (!p) return;
    const dx = c === 'UUD' ? 5 : c === 'GOJ' ? -4 : c === 'GSV' ? 4 : c === 'KUF' ? 4 : c === 'MOW' ? -4 : c === 'NOZ' ? 4 : 0;
    const dy = (c === 'UUD' || c === 'BAX' || c === 'KUF' || c === 'NOZ') ? 9 : -5;
    const anc = dx < 0 ? 'end' : dx > 0 ? 'start' : 'middle';
    s += `<circle cx="${p[0]}" cy="${p[1]}" r="3.2" fill="var(--white)" stroke="${routeColor(c)}" stroke-width="1.5"/><text x="${p[0] + dx}" y="${p[1] + dy}" text-anchor="${anc}" style="font-size:7.5px;font-weight:700;fill:var(--ink);paint-order:stroke;stroke:var(--land);stroke-width:2.2px">${c} · ${ANIM.names[c]}</text>`;
  });
  s += `<circle cx="${o[0]}" cy="${o[1]}" r="9" fill="none" stroke="#E32A2F" stroke-width="1.2" opacity="0.4"/><circle cx="${o[0]}" cy="${o[1]}" r="5.2" fill="#E32A2F" stroke="#fff" stroke-width="1.5"/><text x="${o[0]}" y="${o[1] + 14}" text-anchor="middle" style="font-size:8.5px;font-weight:700;fill:#C0262B;paint-order:stroke;stroke:var(--land);stroke-width:2.4px">OMS · Омск</text><g id="an-planes"></g>`;
  $('#an-svg').innerHTML = s;
}
function renderDyn() {
  const m = curMode(), [w0, w1] = winRange(), span = w1 - w0, fs = m.flights, wfs = winFlights();
  $('#an-sub').textContent = m.sub;
  $('#an-ghint').textContent = `Оборот ≥ ${m.stats.min_turn_min} мин · макс. ${m.stats.max_ac_bh.toFixed(1)} ч/нед. (лимит 70 ч)`;
  $('#an-clock').textContent = fmtClock(ST.t);
  const scr = $('#an-scr'); scr.min = w0; scr.max = w1; scr.value = Math.round(ST.t);
  $('#an-min').textContent = fmtTime(w0); $('#an-max').textContent = fmtTime(w1);
  const steps = stepPoints(); let sIdx = 0;
  for (let i = 0; i < steps.length; i++) if (steps[i] <= ST.t) sIdx = i;
  $('#an-step').textContent = `Событие ${sIdx + 1}/${steps.length}`;
  const active = fs.filter(f => ST.t >= f.t1 && ST.t < f.t2), actSp = new Set(active.map(f => f.o === 'OMS' ? f.d : f.o));
  $$('#an-arcs path').forEach(p => { const on = actSp.has(p.id.replace('an-arc-', '')); p.setAttribute('stroke-opacity', on ? '0.95' : '0.26'); p.setAttribute('stroke-width', on ? '2.4' : '1.3'); });
  $('#an-planes').innerHTML = active.map(f => {
    const p0 = ANIM.pts[f.o], p1 = ANIM.pts[f.d]; if (!p0 || !p1) return '';
    const u = Math.min(1, Math.max(0, (ST.t - f.t1) / (f.t2 - f.t1))), pt = bezier(p0, p1, u), col = COLORS[f.ac] || '#E32A2F';
    return `<g transform="translate(${pt.x.toFixed(1)},${pt.y.toFixed(1)})"><g transform="rotate(${pt.ang.toFixed(1)})"><path d="M7,0 L2,-1.6 L-3,-6.5 L-4.8,-6.5 L-2,-1.4 L-5.8,-1.1 L-7.2,-3.2 L-8.4,-3.2 L-7.4,0 L-8.4,3.2 L-7.2,3.2 L-5.8,1.1 L-2,1.4 L-4.8,6.5 L-3,6.5 L2,1.6 Z" fill="${col}" stroke="#fff" stroke-width="0.6"/></g><rect x="7" y="-11" width="44" height="10" rx="2.5" fill="#fff" fill-opacity="0.92" stroke="${col}" stroke-width="0.7"/><text x="9" y="-3.8" style="font-size:6.4px;font-weight:700;fill:#111318;font-family:var(--mono)">${f.ac} ${f.d} ${Math.round(u * 100)}%</text></g>`;
  }).join('');
  const stMap = m.aircraft.map(ac => {
    if (active.some(f => f.ac === ac)) return 'fly';
    const prev = [...fs].filter(f => f.ac === ac && f.t2 <= ST.t).pop();
    return (prev && prev.d !== 'OMS') ? 'out' : 'oms';
  });
  $('#an-stat').textContent = `В небе: ${active.length} · В Омске: ${stMap.filter(x => x === 'oms').length} + 1 рез. · На обороте: ${stMap.filter(x => x === 'out').length}`;
  const landedFeed = fs.filter(f => m.feeders.includes(f.o) && f.d === 'OMS' && ST.t >= f.t2 && ST.t <= f.t2 + 135);
  const upWest = fs.filter(f => f.o === 'OMS' && ['KUF', 'GOJ', 'VOG', 'GSV'].includes(f.d) && f.t1 > ST.t && f.t1 <= ST.t + 140);
  const exact = wfs.filter(f => f.t1 === Math.round(ST.t) || f.t2 === Math.round(ST.t));
  let msg = '', isTr = false;
  if (ST.mode === 'full' && landedFeed.length && upWest.length) {
    isTr = true;
    msg = `Стыковочное окно в OMS: фидеры ${[...new Set(landedFeed.map(f => f.o))].join('/')} -> западная волна (${[...new Set(upWest.map(f => f.d))].join(', ')})`;
  } else if (exact.length) {
    const dep = exact.filter(f => f.t1 === Math.round(ST.t)).map(f => `${f.ac} ${f.o}->${f.d}`);
    const arr = exact.filter(f => f.t2 === Math.round(ST.t)).map(f => `${f.ac} из ${f.o} в ${f.d}`);
    msg = [dep.length ? 'Вылет: ' + dep.join(', ') : '', arr.length ? 'Прилёт: ' + arr.join(', ') : ''].filter(Boolean).join(' · ');
  } else if (active.length) {
    msg = `В полёте (${active.length} ВС): ` + active.map(f => `${f.ac} ${f.o}->${f.d} (${Math.round((ST.t - f.t1) / (f.t2 - f.t1) * 100)}%)`).join(' · ');
  } else {
    const nxt = wfs.find(f => f.t1 > ST.t);
    msg = nxt ? `Стоянка в OMS · ближайший вылет: ${nxt.ac} ${nxt.o}->${nxt.d} в ${fmtTime(nxt.t1)}` : 'Завершение суточной программы · ночное ТО в Омске';
  }
  $('#an-strip').className = 'strip' + (isTr ? ' tr' : '');
  $('#an-msg').textContent = msg;
  $('#an-ticks').innerHTML = (ST.day === -1 ? DAYS : ['00:00', '06:00', '12:00', '18:00', span > 1440 ? '24:00+' : '24:00']).map(x => `<span>${x}</span>`).join('');
  const ph = ((ST.t - w0) / span) * 100;
  $('#an-gantt').innerHTML = m.aircraft.map(ac => {
    const bars = wfs.filter(f => f.ac === ac).map(f => {
      const l = Math.max(0, (f.t1 - w0) / span * 100), r = Math.min(100, (f.t2 - w0) / span * 100), w = Math.max(0.7, r - l);
      const sp = f.o === 'OMS' ? f.d : f.o, bg = m.feeders.includes(sp) ? '#D97706' : COLORS[ac], on = ST.t >= f.t1 && ST.t <= f.t2;
      return `<div class="g-bar${on ? ' on' : ''}" data-j="${f.t1}" title="${f.id} ${ac}: ${f.o}->${f.d} (${fmtTime(f.t1)}–${fmtTime(f.t2)})" style="left:${l.toFixed(2)}%;width:${w.toFixed(2)}%;background:${bg}">${w > 4 ? (f.o === 'OMS' ? '→' + f.d : f.o + '→') : ''}</div>`;
    }).join('');
    return `<div class="g-row"><div class="g-lbl"><span style="color:${COLORS[ac]}">${ac}</span><small>${m.stats.ac_bh[ac].toFixed(1)} ч/нед</small></div><div class="g-track">${bars}${ph >= 0 && ph <= 100 ? `<div class="g-ph" style="left:${ph.toFixed(2)}%"></div>` : ''}</div></div>`;
  }).join('') + `<div class="g-row"><div class="g-lbl"><span style="color:var(--muted)">${m.reserve}</span><small>резерв</small></div><div class="g-track" style="opacity:.7"><span class="sub" style="padding:2px 8px;display:inline-block">Горячий резерв в OMS (подмена / «Ковёр» / ТО)</span></div></div>`;
  $$('#an-gantt .g-bar').forEach(el => el.onclick = () => { stop(); ST.t = +el.dataset.j; renderDyn(); });
  const bRows = wfs.filter(f => ST.day !== -1 || (f.t2 >= ST.t - 180 && f.t1 <= ST.t + 720));
  $('#an-bsum').textContent = `Рейсов в окне: ${wfs.length} · в небе: ${active.length}`;
  $('#an-board').innerHTML = bRows.map(f => {
    const sp = f.o === 'OMS' ? f.d : f.o;
    const tag = ST.t >= f.t1 && ST.t < f.t2 ? `<span class="tag t-fly">В полёте ${Math.round((ST.t - f.t1) / (f.t2 - f.t1) * 100)}%</span>` : ST.t >= f.t2 ? '<span class="tag t-ok">Прибыл</span>' : f.t1 - ST.t <= 60 ? `<span class="tag t-turn">Через ${Math.round(f.t1 - ST.t)}м</span>` : '<span class="tag t-wait">По графику</span>';
    return `<tr class="click${ST.t >= f.t1 && ST.t < f.t2 ? ' act' : ''}" data-j="${f.t1}"><td class="mono">${f.id}</td><td class="mono"><b style="color:${COLORS[f.ac]}">${f.ac}</b></td><td><b>${f.o} → ${f.d}</b> <span class="sub">(${ANIM.names[sp]})</span></td><td class="mono">${fmtTime(f.t1)}</td><td class="mono">${fmtTime(f.t2)}</td><td class="mono">${(f.bh / 60).toFixed(1)}ч</td><td>${tag}</td></tr>`;
  }).join('');
  $$('#an-board tr').forEach(tr => tr.onclick = () => { stop(); ST.t = +tr.dataset.j; renderDyn(); });
}
function renderAll() { buildDays(); buildMap(); renderDyn(); }
function step(dir) {
  stop(); const pts = stepPoints();
  ST.t = dir > 0 ? (pts.find(x => x > ST.t + 0.5) ?? pts[0]) : ([...pts].reverse().find(x => x < ST.t - 0.5) ?? pts[pts.length - 1]);
  renderDyn();
}
function tick(ts) {
  if (!ST.playing) return;
  if (ST.lastTs !== null) { const [w0, w1] = winRange(); ST.t += (ts - ST.lastTs) / 1000 * ST.speed; if (ST.t >= w1) ST.t = w0; renderDyn(); }
  ST.lastTs = ts; ST.raf = requestAnimationFrame(tick);
}
function start() { if (!ST.playing) { ST.playing = true; ST.lastTs = null; $('#an-play').textContent = '⏸ Пауза'; ST.raf = requestAnimationFrame(tick); } }
function stop() { ST.playing = false; ST.lastTs = null; if (ST.raf) cancelAnimationFrame(ST.raf); ST.raf = null; $('#an-play').textContent = '▶ Пуск'; }
$$('#an-mode button').forEach(b => b.onclick = () => { stop(); $$('#an-mode button').forEach(x => x.classList.remove('on')); b.classList.add('on'); ST.mode = b.dataset.m; const [w0] = winRange(), fs = winFlights(); ST.t = fs.length ? Math.max(w0, fs[0].t1 + 60) : w0; renderAll(); });
$$('#an-spd button').forEach(b => b.onclick = () => { $$('#an-spd button').forEach(x => x.classList.remove('on')); b.classList.add('on'); ST.speed = +b.dataset.s; });
$('#an-play').onclick = () => ST.playing ? stop() : start();
$('#an-next').onclick = () => step(1);
$('#an-prev').onclick = () => step(-1);
$('#an-reset').onclick = () => { stop(); const [w0] = winRange(), fs = winFlights(); ST.t = fs.length ? Math.max(w0, fs[0].t1) : w0; renderDyn(); };
$('#an-scr').oninput = e => { stop(); ST.t = +e.target.value; renderDyn(); };
renderAll();
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
