"""Шаг 2, сборка: несколько оценок спроса по каждой паре, итог в двух мерах, сезонность, сверка с коллегами.

Оценки (метод ТЗ, docs/19, раздел 1):
  1. Модель тяготения по сегментам — src/demand_model.py (pax_base, осторожно/оптимистично).
  2. Отчёт аэропорта — если поток пары опубликован (data/manual/known_flows.csv).
  3. По аналогам — 3 ближайшие известные пары по населению и расстоянию, поток пересчитан
     пропорционально произведению населения (классическая гравитация).
  4. По расписанию — только Омск: вылеты на неделю 7–13.12.2026 из зимнего расписания аэропорта
     (собрали коллеги) × кресла типа самолёта × средняя загрузка по стране 89,5% × 2 направления × 52.
  5. Поездки «откуда — куда» — src/od_model.py: доля своих поездок в потоке рейса и поездки
     по парам без прямого рейса (люди, которые сейчас летят с пересадкой).
  6. Сценарии коллег — context/15_team_update/model/od_registry.csv (допущения аналитика, поездки).
Правило docs/19: оценки в сегментах (1, 3, 4) расходятся меньше чем в disagreement_ratio раз —
база = среднее геометрическое, осторожно = минимум; больше — пара «неуверенная». Отчёт аэропорта,
если есть, заменяет оценки.
Сезонность: помесячная доля размещённых в гостиницах и санаториях (ЕМИСС, коллеги) в регионах обоих
концов пары; летняя (июнь–август) и зимняя (декабрь–февраль) неделя относительно средней.

Выход: data/processed/demand_estimates.csv, data/processed/demand_estimates.json (сводка для панели)
Запуск: python src/demand_compare.py   (после src/demand_model.py и src/od_model.py)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import demand_model as dm

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
ALPHA = 1.0  # размах сезонности, задаётся в main()
EXT = ROOT / "data" / "external" / "colleagues"
A = pd.read_csv(ROOT / "data/assumptions/demand.csv").set_index("parameter").value


def key(a, b):
    return tuple(sorted((a, b)))


def analog(pairs, n):
    """Оценка по аналогам и её точность «исключи по одному» на известных парах."""
    kf = pd.read_csv(ROOT / "data/manual/known_flows.csv")
    kf = kf[(kf.use == "fit") & kf.from_iata.isin(n.index) & kf.to_iata.isin(n.index)].copy()
    kf["pax_year"] = kf.pax * kf.annual_factor
    kf["lnPP"] = [np.log(n.loc[r.from_iata, "pop"] * n.loc[r.to_iata, "pop"]) for r in kf.itertuples()]
    kf["lnD"] = [np.log(dm.hav(n.loc[r.from_iata, "latitude_deg"], n.loc[r.from_iata, "longitude_deg"],
                               n.loc[r.to_iata, "latitude_deg"], n.loc[r.to_iata, "longitude_deg"])) for r in kf.itertuples()]
    kf["mow"] = [float("MOW" in (r.from_iata, r.to_iata)) for r in kf.itertuples()]
    kf["key"] = [key(r.from_iata, r.to_iata) for r in kf.itertuples()]
    sd = kf[["lnPP", "lnD"]].std()
    kk = int(A["analog_k"])

    def est(lnPP, lnD, mow, excl=None):
        c = kf[(kf.mow == mow) & (kf.key != excl)]
        if len(c) < kk:
            c = kf[kf.key != excl]
        d = np.sqrt(((c.lnPP - lnPP) / sd.lnPP) ** 2 + ((c.lnD - lnD) / sd.lnD) ** 2)
        nb = c.loc[d.nsmallest(kk).index]
        return float(np.exp(np.mean(np.log(nb.pax_year) + (lnPP - nb.lnPP)))), ", ".join(f"{a}–{b}" for a, b in nb.key)

    loo = [np.log(r.pax_year) - np.log(est(r.lnPP, r.lnD, r.mow, r.key)[0]) for r in kf.itertuples()]
    loo = np.array(loo)
    out = {}
    for r in pairs.itertuples():
        lnPP = np.log(r.pop_a * r.pop_b)
        v, nb = est(lnPP, np.log(max(r.km, 1)), float("MOW" in (r.a, r.b)))
        out[key(r.a, r.b)] = (v, nb)
    return out, {"loo_median_abs_error_pct_of_fact": round(float(np.median(np.abs(np.exp(-loo) - 1)) * 100), 1),
                 "loo_share_within_x2": round(float(np.mean(np.abs(loo) <= np.log(2))), 2)}


CARRIER = {"RED WINGS": "Red Wings", "РедВингс": "Red Wings", "NORD WIND": "Nordwind", "Nordwind Airlines": "Nordwind",
           "ЮТэйр": "Utair", "Utair": "Utair"}


def correct_omsk_tobolsk(w):
    """Рейс RT 652 зимой 2026/27: Ремезов, а не старый аэродром Тобольск.

    Источник: https://travel.yandex.ru/avia/flights/RT-652/ ; исправление
    относится только к этой записи расписания, общий TOX = RMZ неверен.
    """
    w = w.copy()
    affected = ((w.destination_airport_iata == "TOX") & (w.next_airport_name == "Тобольск") &
                (pd.to_numeric(w.outbound_flight_numeric, errors="coerce") == 652) &
                (w.carrier_raw == "ЮВТаэро"))
    w.loc[affected, "destination_airport_iata"] = "RMZ"
    return w


def schedule():
    """Годовой поток пар по расписанию: вылеты недели × кресла типа самолёта × загрузка 89,5% × 52.

    1. Омск — все вылеты из зимнего расписания аэропорта (коллеги, core); обратное направление = прямому.
    2. Остальные пары — карточки маршрутов коллег на 7–13.12.2026 (night-primary-evidence: расписания
       Кольцово, Уфы, Курумоча, Чкалова и др.). Один рейс в нескольких источниках не складываем:
       по каждому перевозчику и направлению берём источник с наибольшим числом вылетов.
    """
    seats = pd.read_csv(ROOT / "data/assumptions/aircraft_seats.csv").drop_duplicates("type_raw").set_index("type_raw").seats
    lf = A["national_load_factor_2025"]
    out = {}
    w = correct_omsk_tobolsk(pd.read_csv(EXT / "omsk_outbound_week_20261207.csv"))
    t = pd.read_csv(EXT / "omsk_domestic_timetable_rows.csv")[["source_text_line", "aircraft_type_raw"]]
    w = w.merge(t, on="source_text_line", how="left")
    w["seats"] = w.aircraft_type_raw.map(seats)
    w["dest"] = w.destination_airport_iata.map(lambda x: "MOW" if x in dm.MOW else x)
    for d_, g in w.groupby("dest"):
        out[key("OMS", d_)] = (float(g.seats.sum() * lf * 2 * 52), "расписание аэропорта Омск, неделя 7–13.12.2026")
    c = pd.read_csv(EXT / "route_product_cards.csv")
    c = c[(c.product_type == "AIR_PUBLISHED_SERVICE") & c.one_way_departures.notna()].copy()
    c["carrier_n"] = c.carrier.map(lambda x: CARRIER.get(x, x))
    c["seats_w"] = c.one_way_departures * c.aircraft.map(seats)
    c["o"] = c.origin.map(lambda x: "MOW" if x in dm.MOW else x)
    c["d"] = c.destination.map(lambda x: "MOW" if x in dm.MOW else x)
    per_src = c.groupby(["o", "d", "carrier_n", "source_ids"]).seats_w.sum().reset_index()
    per_car = per_src.groupby(["o", "d", "carrier_n"]).seats_w.max().reset_index()
    per_dir = per_car.groupby(["o", "d"]).seats_w.sum()
    for (o, d_), v in per_dir.items():
        k = key(o, d_)
        if k in out and out[k][1].startswith("расписание аэропорта Омск"):
            continue
        back = per_dir.get((d_, o))
        week = v + (back if back is not None else v)
        out[k] = (float(week * lf * 52), "карточки маршрутов коллег, неделя 7–13.12.2026" +
                  ("" if back is not None else "; обратное направление = прямому"))
    return out


def seasonality(n):
    m = pd.read_csv(EXT / "primary_monthly_increments.csv")
    m = m[(m.dataset_id == "emiss_62073") & (m.year == 2024)]
    piv = m.pivot_table(index="area_name", columns="month", values="monthly_increment", aggfunc="sum")
    piv = piv[piv.notna().all(axis=1)]
    sh = piv.div(piv.sum(axis=1), axis=0) * 12          # индекс месяца, среднее = 1
    alias = {"Москва": "г. Москва", "Санкт-Петербург": "г. Санкт-Петербург"}
    reg = {}
    for i, r in n.iterrows():
        nm = alias.get(r.region, r.region)
        if nm in sh.index:
            reg[i] = sh.loc[nm]
    return reg


def main():
    pairs = pd.read_csv(P / "demand_pairs.csv")
    od = pd.read_csv(P / "od_pairs.csv")
    od = {key(r.a, r.b): r for r in od.itertuples()}
    n = dm.nodes()
    an, an_q = analog(pairs, n)
    sch = schedule()
    reg = seasonality(n)
    col = pd.read_csv(EXT / "od_registry.csv")
    colmap = {}
    for r in col.itertuples():
        a, b = r.pair.split("-")
        a, b = ("MOW" if a in dm.MOW else a), ("MOW" if b in dm.MOW else b)
        colmap[key(a, b)] = (r.scenario_OD_cautious * 2 * 52, r.scenario_OD_base * 2 * 52, r.net_fare_base_RUB_journey, r.capture_group,
                             "ZIA" in r.pair, r.known_RW_direct_seats_A_to_B)
    NA = pd.read_csv(ROOT / "data/assumptions/network.csv").set_index("parameter").base
    # размах сезонности: гостиницы колеблются сильнее авиаперевозок. Летний индекс авиаперевозок по стране
    # 2025 = (янв–авг − янв–май) / 3 мес. / (год / 12); размах гостиничного профиля сжимаем до него
    global ALPHA
    nat_summer = ((A["carrier_pax_2025_jan_aug"] - A["carrier_pax_2025_jan_may"]) / 3) / (A["carrier_pax_2025_year"] / 12)
    hs, ws = [], []
    for r in pairs.itertuples():
        sa, sb = reg.get(r.a), reg.get(r.b)
        if sa is not None and sb is not None:
            hs.append(float(((sa + sb) / 2).loc[[6, 7, 8]].mean()))
            ws.append(r.pax_base)
    hotel_summer = float(np.average(hs, weights=ws))
    ALPHA = (nat_summer - 1) / (hotel_summer - 1)
    rows = []
    for r in pairs.itertuples():
        k = key(r.a, r.b)
        a_v, a_nb = an[k]
        s_v, s_src = sch.get(k, (None, None))
        # карточки коллег покрывают не всех перевозчиков пары — это нижняя граница, в среднее не идёт
        s_lb = None
        if s_src is not None and not s_src.startswith("расписание аэропорта Омск"):
            s_lb, s_v = s_v, None
        # аналоги — только для пар с прямым рейсом: все известные потоки сняты с прямых рейсов,
        # для пар без рейса такие аналоги завышают в разы
        ests = [x for x in (r.pax_base, a_v if r.direct_now else None, s_v) if x is not None and x > 0]
        ratio = max(ests) / min(ests)
        obs = r.observed if pd.notna(r.observed) and r.observed_coverage != "airline_group" else None
        if obs is not None:
            seg_base, seg_lo, how = obs, obs, "отчёт аэропорта"
        else:
            seg_base = float(np.exp(np.mean(np.log(ests))))
            seg_lo = min(min(ests), r.pax_cautious)
            if len(ests) == 1:
                how = "одна оценка: модель тяготения"
            elif ratio <= A["disagreement_ratio"]:
                how = f"среднее {len(ests)} оценок (расхождение {ratio:.1f} раза)"
            else:
                how = f"неуверенная: оценки расходятся в {ratio:.1f} раза"
        o = od.get(k)
        if o is not None and pd.notna(o.od_share_of_link):
            share = float(o.od_share_of_link)
            od_base, od_how = seg_base * share, f"сегменты × доля своих поездок {share:.0%} (src/od_model.py)"
            od_lo = seg_lo * share
        elif o is not None:
            share = None
            od_base, od_how = float(o.od_base), f"сейчас летят {o.route} (src/od_model.py); при прямом рейсе рынок ближе к сегментной оценке"
            od_lo = float(o.od_cautious)
        else:
            share, od_base, od_how, od_lo = None, None, "нет авиамаршрута с одной пересадкой через узел", None
        sa, sb = reg.get(r.a), reg.get(r.b)
        prof = (sa + sb) / 2 if sa is not None and sb is not None else (sa if sa is not None else sb)
        cm = colmap.get(k)
        rows.append({
            "a": r.a, "b": r.b, "city_a": r.city_a, "city_b": r.city_b, "km": r.km, "closed": r.closed,
            "direct_now": r.direct_now, "observed": obs,
            "seg_model": r.pax_base, "seg_model_cautious": r.pax_cautious, "seg_analog": round(a_v), "analog_pairs": a_nb,
            "seg_schedule": round(s_v) if s_v else None, "seg_schedule_lower": round(s_lb) if s_lb else None,
            "schedule_source": s_src,
            "estimates_ratio": round(ratio, 2), "uncertain": obs is None and ratio > A["disagreement_ratio"],
            "segments_base": round(seg_base), "segments_cautious": round(seg_lo), "segments_method": how,
            "own_trips_share": share, "od_base": round(od_base) if od_base is not None else None,
            "od_cautious": round(od_lo) if od_lo is not None else None, "od_method": od_how,
            "od_route_now": o.route if o is not None else None,
            "summer_factor": round(1 + ALPHA * (float(prof.loc[[6, 7, 8]].mean()) - 1), 2) if prof is not None else None,
            "winter_factor": round(1 + ALPHA * (float(prof.loc[[12, 1, 2]].mean()) - 1), 2) if prof is not None else None,
            "peak_month": int(prof.idxmax()) if prof is not None else None,
            "colleagues_od_cautious": cm[0] if cm else None, "colleagues_od_base": cm[1] if cm else None,
            "colleagues_fare_rub": cm[2] if cm else None, "colleagues_capture": cm[3] if cm else None,
            "colleagues_zia_only": cm[4] if cm else None,
            "rw_seats_week_each_way": cm[5] if cm and pd.notna(cm[5]) else None,
            "fare_ours_rub": round(NA["fare_fixed_rub"] + NA["fare_per_km_rub"] * r.km),
        })
    d = pd.DataFrame(rows)
    d.to_csv(P / "demand_estimates.csv", index=False, encoding="utf-8")
    seg_fit = json.loads((P / "demand_fit.json").read_text(encoding="utf-8"))
    od_fit = json.loads((P / "od_fit.json").read_text(encoding="utf-8"))
    # проверка расписанием: пары, где есть и расписание, и отчёт аэропорта
    chk = [{"pair": f"{r.a}-{r.b}", "fact_2025": int(r.observed), "schedule_dec2026": int(r.seg_schedule)}
           for r in d[d.observed.notna() & d.seg_schedule.notna()].itertuples()]
    chk_lb = [{"pair": f"{r.a}-{r.b}", "fact_2025": int(r.observed), "schedule_lower_dec2026": int(r.seg_schedule_lower)}
              for r in d[d.observed.notna() & d.seg_schedule_lower.notna()].itertuples()]
    cc = d[d.colleagues_od_base.notna() & ~d.colleagues_zia_only.fillna(False).astype(bool)]
    summary = {
        "pairs": int(len(d)), "observed": int(d.observed.notna().sum()), "uncertain": int(d.uncertain.sum()),
        "with_schedule": int(d.seg_schedule.notna().sum()), "with_colleagues": int(len(cc)),
        "seg_model": {k2: seg_fit[k2] for k2 in ("n_fit", "loo_median_abs_error_pct_of_fact", "loo_share_within_x2")},
        "analog": an_q,
        "od_model": {k2: od_fit[k2] for k2 in ("loo_median_abs_error_pct_of_fact", "loo_share_within_x2",
                                                 "od_total_air_trips_year", "segments_total_on_links_year")},
        "schedule_check": chk, "schedule_lower_check": chk_lb, "with_schedule_lower": int(d.seg_schedule_lower.notna().sum()),
        "fare_colleagues_to_ours_median": round(float((d.colleagues_fare_rub / d.fare_ours_rub).median()), 2),
        "seasonality": {"national_summer_index_2025": round(float(nat_summer), 2), "hotel_summer_index": round(hotel_summer, 2),
                        "amplitude_alpha": round(float(ALPHA), 2)},
        "colleagues_vs_ours_median_ratio": round(float((cc.od_base.astype(float) / cc.colleagues_od_base).median()), 2) if len(cc) else None,
    }
    (P / "demand_estimates.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
