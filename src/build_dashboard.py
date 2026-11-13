"""Собирает панель расчёта outputs/redwings_panel.html из таблиц проекта.

Берёт: data/processed/longlist.csv, kover_days.csv, data/raw/favt_posts.csv (помесячно),
       data/raw/ourairports_airports.csv (координаты), data/assumptions/longlist_weights.csv
Вписывает всё одним JSON в шаблон src/dashboard_template.html.
Запуск: python src/build_dashboard.py   (после build_longlist.py)
"""
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import rules  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

REF = {"SVX": "Екатеринбург", "OVB": "Новосибирск", "SVO": "Шереметьево", "DME": "Домодедово",
       "VKO": "Внуково", "LED": "Санкт-Петербург", "KRR": "Краснодар"}
MEDUZA = dict(pd.read_csv(ROOT / "data/manual/kover_validation_meduza.csv")[["iata", "h1_2026_days"]].values)
_C = pd.read_csv(ROOT / "data/manual/competitor_hubs.csv")
COMPETITOR_HUB = {r.iata: f"{r.carrier}: {r.evidence}" for r in _C.itertuples() if r.competitor_hub == 1}


def num(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def txt(v):
    return None if v is None or (isinstance(v, float) and v != v) else str(v)


def case_answer(names):
    """Выбор первого хаба: почему — Омск и порядок расширения.
    Тексты — data/manual/case_answer.json, числа — из готовых таблиц расчёта (без пересчёта)."""
    cfg = json.loads((ROOT / "data/manual/case_answer.json").read_text(encoding="utf-8"))
    sm = pd.read_csv(P / "network_summary.csv")
    b = sm[sm.scenario == "base"]
    hb = b[b.hub.notna()].set_index("hub")
    d0 = b[b.hub.isna()].iloc[0]
    ll = pd.read_csv(P / "longlist.csv").set_index("iata")
    dist = ll[["dist_msk_km", "dist_ekb_km"]].min(axis=1)
    kov = ll.last365_days
    r0 = pd.read_csv(rules.scores_file(0.0)).set_index("iata")
    r5 = pd.read_csv(rules.scores_file(rules.FILTER_OPTION_KM)).set_index("iata")
    ramp = pd.read_csv(P / "fleet_ramp.csv")
    H = str(pd.read_csv(ROOT / "data/assumptions/choice.csv").set_index("parameter").value["chosen_hub"])
    ramp = ramp[(ramp.scenario == "base") & (ramp.hub == H)].sort_values("fleet_cap")
    ch = pd.read_csv(ROOT / "data/manual/competitor_hubs.csv").set_index(pd.read_csv(ROOT / "data/manual/competitor_hubs.csv").columns[0])
    rt = pd.read_csv(P / "network_routes.csv")
    tri = (rt[(rt.scenario == "base") & rt.variant.str.startswith("Прямые")].groupby("variant")
           .triangle_result_mln_year.first().sort_values(ascending=False))
    nm = lambda i: names.get(i, i)
    n_ = lambda v: f"{v:,.0f}".replace(",", " ")
    sg = lambda v: ("+" if v >= 0 else "−") + n_(abs(v))
    sc = lambda i: f"{float(r0.loc[i, 'score']) * 100:.1f}".replace(".", ",") if "score" in r0.columns else ""
    rank0 = r0["rank"].astype(int)
    top3 = list(r0.sort_values("rank").index[:3])
    # города вдали от баз и без сильного «Ковра» (порог — медиана «Ковра» по лонглисту)
    far = [i for i in hb.index if i in dist.index and dist[i] >= rules.FILTER_OPTION_KM and kov.get(i, 999) <= kov.median()]
    far_best = max(far, key=lambda i: hb.loc[i, "result_mln_year"]) if far else H
    near = ["CEK", "TJM", "PEE", "UFA"]
    km = lambda i: n_(dist[i])
    cmp_kov = ", ".join(f"{nm(i)} {int(kov[i])}" for i in ["CEK", "TJM", "PEE", "UFA", "KUF", "AER"] if i in kov.index)
    steps_ = []
    prev = set()
    for r in ramp.itertuples():
        sp = r.spokes.split(";")
        new = [x for x in sp if x not in prev]
        steps_.append(f"{int(r.aircraft)} самолёта: {sg(r.result_mln_year)} млн ₽" if r.aircraft < 5 else f"{int(r.aircraft)} самолётов: {sg(r.result_mln_year)} млн ₽")
        prev = set(sp)
    first = ramp.iloc[0].spokes.split(";")
    full = ramp.iloc[-1].spokes.split(";")
    hyb = set(cfg.get("hybrid_triangles", []))
    pos_tri = [(v, x) for v, x in tri.items() if x > 0 and (not hyb or v.replace("Прямые ", "") in hyb)]
    n_pos = int((tri > 0).sum())
    tri_txt = "; ".join(f"{' — '.join(nm(c) for c in v.replace('Прямые ', '').split('-'))} ({sg(x)})" for v, x in pos_tri)
    comp = lambda i: (str(ch.loc[i].iloc[1]) if i in ch.index and isinstance(ch.loc[i].iloc[1], str) else "")
    fill = {
        "why_rank": f"{int(rank0[H])}-е место из {len(r0)} в рейтинге городов без фильтра и {int(r5.loc[H, 'rank'])}-е среди городов дальше {int(rules.FILTER_OPTION_KM)} км от Москвы и Екатеринбурга (балл {sc(H)}). Веса критериев в рейтинге учтены.",
        "why_dist": f"До ближайшей базы Red Wings {km(H)} км: его пассажиры — новые для компании. У сильных соседей по рейтингу базы рядом: " + ", ".join(f"{nm(i)} {km(i)} км" for i in near) + " до Екатеринбурга.",
        "why_kover": f"{int(kov[H])} дней ограничений за последний год — меньше, чем у всех сильных кандидатов: {cmp_kov}.",
        "why_money": f"{sg(hb.loc[H, 'result_mln_year'])} млн ₽ в год на {int(hb.loc[H, 'aircraft'])} самолётах с учётом сезонности — "
                     + ("больше всех городов вдали от наших баз без сильного «Ковра»" if far_best == H else f"второй результат вдали от баз после {nm(far_best)}")
                     + f". Больше, чем у Уфы ({sg(hb.loc['UFA', 'result_mln_year'])} на {int(hb.loc['UFA', 'aircraft'])}) и Перми ({sg(hb.loc['PEE', 'result_mln_year'])} на {int(hb.loc['PEE', 'aircraft'])}).",
        "why_ramp": "Сеть добавляет лучи по мере поставок и на каждом шаге в плюсе: " + "; ".join(steps_) + f". У Уфы сеть упирается в {int(hb.loc['UFA', 'aircraft'])} самолётов и {sg(hb.loc['UFA', 'result_mln_year'])} млн ₽.",
        "why_comp": f"В Омске нет базы конкурента; ближайший чужой хаб — S7 в Новосибирске, через него сейчас летает часть пассажиров с пересадкой. В Челябинске опорные рейсы конкурентов ({comp('CEK')}), в Тюмени — база {comp('TJM')}.",
        "honest_rank": f"выше Омска {', '.join(f'{nm(i)} ({sc(i)})' for i in top3)}: это крупные города с большим пассажиропотоком.",
        "honest_money": f"выше Омска {nm('CEK')} ({sg(hb.loc['CEK', 'result_mln_year'])} млн ₽ на {int(hb.loc['CEK', 'aircraft'])} самолётах: пересадки из Сибири на юг, один луч в Минеральные Воды даёт около 40% итога) и Сочи ({sg(hb.loc['AER', 'result_mln_year'])}, но {int(kov['AER'])} дня «Ковра» за год).",
        "ord_oms": f"Первые SJ-100: лучи {', '.join(nm(x) for x in first)}; к полной сети ({int(ramp.iloc[-1].aircraft)} самолётов) добавляются {', '.join(nm(x) for x in full if x not in first)}. Итог {sg(hb.loc[H, 'result_mln_year'])} млн ₽ в год.",
        "ord_direct": (f"Из {len(tri)} треугольников модели окупаются {n_pos}; в гибрид берём {len(pos_tri)}: {tri_txt} млн ₽. Москва — Самара — Омск повторяет лучи хаба, Москва — Курган — Минеральные Воды почти в нуле. Вся прямая сеть — {sg(d0.result_mln_year)} млн ₽ на {int(d0.aircraft)} самолётах, поэтому запускаем только окупаемые, по одному." if pos_tri else "Треугольники при нынешних допущениях не окупаются."),
        "ord_cek": f"Лучший итог сети: {sg(hb.loc['CEK', 'result_mln_year'])} млн ₽ на {int(hb.loc['CEK', 'aircraft'])} самолётах, {int(kov['CEK'])} дней «Ковра». Условие: {km('CEK')} км до Екатеринбурга, поэтому по данным бронирований сначала проверить, сколько его пассажиров уже летают Red Wings из Кольцово.",
        "ord_tjm": f"{sg(hb.loc['TJM', 'result_mln_year'])} млн ₽ на {int(hb.loc['TJM', 'aircraft'])} самолётах, {int(kov['TJM'])} дней «Ковра». Условие то же: {km('TJM')} км до Екатеринбурга; в Тюмени база Utair.",
        "ord_ufa": f"Первые места рейтинга без фильтра, но сети слабее: Уфа {sg(hb.loc['UFA', 'result_mln_year'])}, Пермь {sg(hb.loc['PEE', 'result_mln_year'])} млн ₽ при {int(kov['UFA'])} и {int(kov['PEE'])} днях «Ковра». Подходят для прямых рейсов и как точки сетей Омска и Челябинска.",
    }

    def fmt(o):
        if isinstance(o, str):
            return o.format(**fill) if "{" in o else o
        if isinstance(o, list):
            return [fmt(x) for x in o]
        if isinstance(o, dict):
            return {k: fmt(v) for k, v in o.items()}
        return o
    out = fmt({k: v for k, v in cfg.items() if k != "source"})
    out["hub"] = H
    return out


def season_window(a):
    """Окно «Сезонность»: помесячный спрос и кресла сети каждого хаба (docs/37_seasonality.md).
    Спрос месяца = (перевезённые + потерянные за год) / 12 × профиль пары; кресла — по частоте сезона."""
    import network_model as nm
    sp = P / "airport_seasonality.csv"
    if not sp.exists() or "season_on" not in a.index:
        return {}
    rt = pd.read_csv(P / "network_routes.csv")
    if "freq_week_winter" not in rt.columns:
        return {}
    summer = set(nm.SEASON_MONTHS["summer"])
    nets = {}
    for (sc, v), g in rt[rt.scenario.isin(["base", "cautious"]) & rt.variant.str.startswith("Хаб ")].groupby(["scenario", "variant"]):
        j = 0 if sc == "base" else 1
        A = {"season_amplitude": float(a.loc["season_amplitude"].iloc[j])}
        W, seats, lfp = float(a.loc["weeks_per_year"].iloc[j]), float(a.loc["seats"].iloc[j]), float(a.loc["lf_peak_max"].iloc[j])
        dem, cap, car = [0.0] * 12, [0.0] * 12, [0.0] * 12
        for r in g.itertuples():
            prof = nm.pair_profile(getattr(r, "_3"), r.to, A)
            want = r.pax_year_segments + r.pax_year_spilled
            for m in range(12):
                f = r.freq_week_each_way if m in summer else r.freq_week_winter
                d_, c_ = want / 12 * prof[m], 2 * f * seats * W / 12
                dem[m] += d_
                cap[m] += c_
                car[m] += min(d_, c_ * lfp)
        nets.setdefault(v.replace("Хаб ", ""), {})[sc] = {
            "dem": [round(x) for x in dem], "seats": [round(x) for x in cap], "carried": [round(x) for x in car],
            "spilled": int(g.pax_year_spilled.sum()), "segments": int(g.pax_year_segments.sum()),
            "f_summer": int(2 * g.freq_week_each_way.sum()), "f_winter": int(2 * g.freq_week_winter.sum())}
    s = pd.read_csv(sp).set_index("iata")
    M = [f"m{i}" for i in range(1, 13)]
    prof = {k: [round(float(x), 3) for x in s.loc[k, M]] for k in ("OMS", "SVX", "AER", "MOW", "KUF", "CEK", "TJM") if k in s.index}
    cal = json.loads((P / "seasonality_calibration.json").read_text(encoding="utf-8"))
    prof["AFL"] = [round(float(x), 3) for x in cal["fallback_profile_aeroflot_domestic_2023_2025"]]
    return {"nets": nets, "prof": prof, "k": cal["k_domestic"]}


def market_window():
    """Окно «Рынок»: факты о рынке (data/manual/market_facts.csv) и внутренние перевозки группы «Аэрофлот»
    по месяцам 2025 и 2026 годов (data/processed/aeroflot_traffic_monthly.csv)."""
    out = {}
    mf = ROOT / "data/manual/market_facts.csv"
    if mf.exists():
        f = pd.read_csv(mf)
        out["facts"] = [{"metric": r.metric, "text": r.text, "source_name": r.source_name, "source": r.source} for r in f.itertuples()]
        a = f.set_index("id")
        if "afl_dom_10m_2026" in a.index:
            out["afl_dom_10m"] = float(a.loc["afl_dom_10m_2026", "value"]) / 100
    tp = P / "aeroflot_traffic_monthly.csv"
    if tp.exists():
        t = pd.read_csv(tp)
        t = t[(t.entity == "group") & (t.metric == "passengers") & (t.scope == "domestic")].set_index("month").value / 1000
        rows = []
        for m in range(1, 13):
            a5, a6 = t.get(f"2025-{m:02d}"), t.get(f"2026-{m:02d}")
            rows.append({"y2025": round(float(a5), 3) if a5 is not None else None,
                         "y2026": round(float(a6), 3) if a6 is not None else None,
                         "chg": round(float(a6 / a5 - 1), 4) if a5 is not None and a6 is not None else None})
        out["months"] = rows
    return out


def lease_window(C):
    """Окно «Сколько аренды выдерживает сеть» (P39 коллег, 13.11): итог сети до аренды / (12 × самолёты).
    Считаем из нашего network_summary.csv, ориентир аренды — исторический договор SSJ100 из P39."""
    sm = pd.read_csv(P / "network_summary.csv")
    sm = sm[sm.scenario == "base"]
    rows = [{"name": r.variant.replace("Хаб ", ""), "hub": r.hub if isinstance(r.hub, str) else "DIRECT",
             "aircraft": int(r.aircraft), "result": float(r.result_mln_year),
             "per_ac_month": round(float(r.result_mln_year) / (12 * r.aircraft), 3)} for r in sm.itertuples()]
    out = {"rows": rows}
    lb = C / "p39_lease_benchmarks.csv"
    if lb.exists():
        h = pd.read_csv(lb).set_index("id")
        if "LEASE-HIST-RUB" in h.index:
            v = float(h.loc["LEASE-HIST-RUB", "exact_amount"])
            out["hist_rub"] = round(v / 1e6, 3)                      # с НДС 18% по договору 2015 года
            out["hist_rub_ex_vat"] = round(v / 1.18 / 1e6, 3)
            out["hist_src"] = h.loc["LEASE-HIST-RUB", "source"]
    op = C / "p39_omsk_prices.csv"
    if op.exists():
        o = pd.read_csv(op).set_index("id")
        if "OMS-BASE-30–74.999 т" in o.index:
            out["oms_basing"] = float(o.loc["OMS-BASE-30–74.999 т", "min"])
    return out


def research(nodes):
    """Окна второй версии панели: топливо сетей, неделя оборотов, пересчёты коллег, заметки эксперта.

    Таблицы коллег — data/external/colleagues/ (src/fetch_colleague_research.py, коммиты в research_manifest.json).
    """
    C = ROOT / "data/external/colleagues"
    a = pd.read_csv(ROOT / "data/assumptions/network.csv").set_index("parameter")
    rt = pd.read_csv(P / "network_routes.csv")

    def tons(g, j):
        """Тонны керосина сети в год по тем же формулам, что leg_cost в network_model."""
        t = 0.0
        for r in g.itertuples():
            fa, ta = getattr(r, "_3"), r.to
            south = any(x in nodes.index and rules.is_south(nodes.loc[x, "region"]) for x in (fa, ta))
            k = a.loc["route_factor_south"].iloc[j] if south else a.loc["route_factor"].iloc[j]
            bh = a.loc["block_fixed_h"].iloc[j] + r.km * k / a.loc["block_speed_kmh"].iloc[j]
            # рейсов в неделю в среднем за год: лето (7 месяцев) и зима (5 месяцев) — см. docs/37_seasonality.md
            fw = getattr(r, "freq_week_winter", r.freq_week_each_way)
            f_year = (7 * r.freq_week_each_way + 5 * fw) / 12 if pd.notna(fw) else r.freq_week_each_way
            t += (a.loc["fuel_t_per_hour"].iloc[j] * bh + a.loc["fuel_t_per_cycle"].iloc[j]) * f_year * 2 * a.loc["weeks_per_year"].iloc[j]
        return t
    fuel = {}
    for (sc, v), g in rt.groupby(["scenario", "variant"]):
        key = v.replace("Хаб ", "") if v.startswith("Хаб ") else "DIRECT"
        fuel.setdefault(sc, {}).setdefault(key, 0.0)
        fuel[sc][key] += tons(g, 0 if sc.startswith("base") else 1)
    out = {"fuel_t": {s: {k: round(v, 1) for k, v in d.items()} for s, d in fuel.items()}}
    if (C / "oms_ramp_week_flights.csv").exists():
        wk = pd.read_csv(C / "oms_ramp_week_flights.csv")
        out["week"] = [{"id": r.flight_id, "tail": r.tail_slot, "from": r.origin, "to": r.destination,
                        "dep": r.departure_utc, "arr": r.arrival_utc, "block": int(r.block_min), "hi": int(r.scenario_block_high_min)}
                       for r in wk.itertuples()]
        cn = pd.read_csv(C / "oms_ramp_connections.csv")
        ok = cn.arithmetic_status.astype(str).str.startswith("WITHIN")
        out["week_conn"] = {"total": int(len(cn)), "ok": int(ok.sum()),
                            "pairs": [{"from": r.origin, "to": r.destination, "wait": float(r.wait_min)} for r in cn[ok].itertuples()]}
    if (C / "five_city_budget.csv").exists():
        out["five_city"] = [{"network": r.network, "aircraft_budget": int(r.aircraft_budget),
                             "result_mln_year": None if pd.isna(r.result_mln_year) else float(r.result_mln_year)}
                            for r in pd.read_csv(C / "five_city_budget.csv").itertuples()]
    if (C / "p09_programmes.csv").exists():
        p9 = pd.read_csv(C / "p09_programmes.csv")
        out["p09"] = [{"id": r.programme_id, "label": r.label, "scen": r.scenario, "dj": float(r.delta_journeys),
                       "drev": float(r.delta_revenue_net) / 1e6, "dop": float(r.delta_known_operating_subtotal) / 1e6}
                      for r in p9.itertuples()]
    if (C / "p10_type_productivity.csv").exists():
        pr = pd.read_csv(C / "p10_type_productivity.csv")
        out["prod"] = [{"type": r.aircraft_type, "cond": r.condition, "seats": int(r.seats),
                        "pax_tail": float(r.annual_occupied_segment_equivalents_per_tail)} for r in pr.itertuples()]
        th = pd.read_csv(C / "p10_threshold_scenarios.csv")
        out["thr"] = [{"case": r.competition_scenario_id, "year": int(r.year), "pax": float(r.threshold_reported_pax),
                       "carrier": r.threshold_carrier_under_condition, "growth": float(r.market_annual_growth_condition)}
                      for r in th.itertuples()]
    if (C / "p34_triangle_shuttle_controls.csv").exists():
        # v — итог против KEEP (новые рейсы и снятие старых), n — только новые рейсы (R−W)
        out["tri_ctl"] = [{"id": r.programme, "label": r.label, "scen": r.scenario, "v": float(r.delta_vs_keep_mln_month),
                           "n": float(r.new_flights_mln_month)}
                          for r in pd.read_csv(C / "p34_triangle_shuttle_controls.csv").itertuples()]
    if (C / "p36_new_pairs.csv").exists():
        out["new_pairs"] = [{"pair": r.pair, "path": r.path, "base": float(r.base_mln_month), "cau": float(r.cautious_mln_month),
                             "comp": r.competitor} for r in pd.read_csv(C / "p36_new_pairs.csv").itertuples()]
        out["p36_prog"] = [{"name": r.programme, "scen": r.scenario, "new": float(r.new_flights_only)}
                           for r in pd.read_csv(C / "p36_programmes.csv").itertuples()]
    if (C / "p38_top5_pairs.csv").exists():
        out["p38_top5"] = [{"rank": int(r.rank), "pair": r.pair, "path": r.chain, "comp": r.competitor, "base": float(r.base_new_mln_feb),
                            "cau": float(r.cautious_new_mln_feb)} for r in pd.read_csv(C / "p38_top5_pairs.csv").itertuples()]
        out["p38_pilots"] = [{"id": r.candidate, "scen": r.scenario, "tickets": int(r.integer_equal_tickets_vs_KEEP_same_W),
                              "seats": int(r.seat_capacity)} for r in pd.read_csv(C / "p38_pilots.csv").itertuples()]
        out["p38_months"] = [{"scen": r.scenario, "progs": int(r.programmes), "months": int(r.months), "rows": int(r.rows),
                              "neg": int(r.new_negative), "pos": int(r.new_positive)}
                             for r in pd.read_csv(C / "p38_programme_months.csv").itertuples()]
    out["season"] = season_window(a)
    out["lease"] = lease_window(C)
    out["market"] = market_window()
    ex = ROOT / "data/manual/expert_notes.json"
    if ex.exists():
        out["expert"] = json.loads(ex.read_text(encoding="utf-8"))
    return out


MOW = rules.MOW_AIRPORTS


def load_dests():
    """Направления по кандидатам; аэропорты Москвы сводим в одну точку «Москва»."""
    d = pd.read_csv(P / "destinations.csv")
    out = {}
    for frm, g in d.groupby("from"):
        rows = []
        m = g[g["to"].isin(MOW)]
        if len(m):
            best = "direct" if (m.status == "direct").any() else ("rail" if (m.status == "rail").any() else "gap")
            svo = m[m["to"] == "SVO"].iloc[0] if (m["to"] == "SVO").any() else m.iloc[0]
            rows.append({"to": "MOW", "city": "Москва", "lat": float(svo.lat), "lon": float(svo.lon),
                         "pop": int(m["pop"].sum()), "km": int(m.km.min()), "in_ssj": bool(m.in_ssj.any()),
                         "rail_hr": None if pd.isna(svo.rail_hr) else float(svo.rail_hr), "status": best})
        for r in g[~g["to"].isin(MOW)].itertuples():
            rows.append({"to": r.to, "city": r.to_city, "lat": float(r.lat), "lon": float(r.lon),
                         "pop": int(r.pop), "km": int(r.km), "in_ssj": bool(r.in_ssj),
                         "rail_hr": None if pd.isna(r.rail_hr) else float(r.rail_hr), "status": r.status})
        out[frm] = sorted(rows, key=lambda x: -x["pop"])
    return out


def load_network():
    """Шаг 3–4: итоги вариантов, маршруты обоих сценариев и координаты концов маршрутов."""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    import demand_model as dm
    from airports_meta import NAME
    sm = pd.read_csv(P / "network_summary.csv")
    sm["vkey"] = sm.hub.fillna("").replace("", "DIRECT")
    rt = pd.read_csv(P / "network_routes.csv")
    rt["vkey"] = rt.variant.map(lambda v: v.replace("Хаб ", "") if v.startswith("Хаб ") else "DIRECT")
    n = dm.nodes()
    ends = set(rt["from"]) | set(rt["to"])
    nodes = {i: [round(float(n.loc[i, "latitude_deg"]), 3), round(float(n.loc[i, "longitude_deg"]), 3),
                 NAME.get(i, n.loc[i, "main_city"])] for i in ends if i in n.index}
    cols = ["scenario", "vkey", "variant", "from", "to", "km", "freq_week_each_way", "freq_week_winter", "pax_year_spilled", "pax_year_segments",
            "pax_year_local", "pax_year_rw_migrated", "load_factor", "direct_now", "range_light", "demand_source", "subsidy_rule", "subsidy_mln_year", "revenue_mln_year", "cost_mln_year", "result_mln_year"]
    if "triangle_result_mln_year" in rt.columns:
        cols.append("triangle_result_mln_year")
    # допущения расчёта — прямо из data/assumptions/network.csv, чтобы панель не расходилась с моделью
    na = pd.read_csv(ROOT / "data/assumptions/network.csv").set_index("parameter")
    asm = {k: [float(na.loc[k, "base"]), float(na.loc[k, "cautious"])] for k in
           ("seats", "lf_max", "fare_fixed_rub", "fare_per_km_rub", "subsidy_rub_per_flight", "subsidy_months", "subsidy_max_prior_pax", "fuel_rub_per_t", "fuel_compensation_rub_per_t", "min_freq_week", "max_freq_week", "capture_open",
            "capture_competitive", "capture_transfer", "transfer_fare_factor", "weeks_per_year", "fleet_cap",
            "spare_aircraft", "max_routes", "rw_existing_lf", "rw_pax_2025", "market_pax_2025",
            "min_routes", "direct_max_freq_week", "thin_route_pax_day", "season_on", "season_amplitude", "lf_peak_max", "market_pax_domestic_2025",
            # для окна «один рейс» (формулы leg_cost и fare в network_model)
            "block_fixed_h", "route_factor", "route_factor_south", "block_speed_kmh", "fuel_t_per_hour", "fuel_t_per_cycle",
            "mro_rub_per_hour", "crew_rub_per_hour", "navigation_rub_per_hour", "ground_rub_per_flight", "deicing_rub_per_flight", "pax_cost_rub")}
    # вторая модель: неделя 7–13.12.2026 по опубликованному расписанию (data/external/colleagues)
    cc = pd.read_csv(ROOT / "data/external/colleagues/night_common_comparison.csv")
    check = []
    for (net_, sc), g in cc.groupby(["network", "scenario"]):
        ctr = g.contribution_before_base_fleet_opportunity / 1e6
        be = -g.contribution_before_base_fleet_opportunity / g.incremental_revenue * 100
        check.append({"network": net_, "scenario": sc, "aircraft": int(g.active_allocated.max()),
                      "lo": round(float(ctr.min()), 1), "hi": round(float(ctr.max()), 1),
                      "be_lo": round(float(be.min())), "be_hi": round(float(be.max())),
                      "pax_lo": round(float(g.segment_pax.min())), "pax_hi": round(float(g.segment_pax.max()))})
    # как сравнивать сценарии словами: отношение осторожного к базовому по спросу, тарифу и расходам рейса на 1000 км
    est = pd.read_csv(P / "demand_estimates.csv")
    import network_model as nmod
    AS = nmod.load_assumptions()
    fare1000 = [nmod.fare(AS[k], 1000) for k in ("base", "cautious")]
    cost1000 = [nmod.leg_cost(AS[k], 1000, False, 80)[1] for k in ("base", "cautious")]
    cmp_ = {"demand": float(est.od_cautious.sum() / est.od_base.sum()), "fare": fare1000[1] / fare1000[0], "cost": cost1000[1] / cost1000[0],
            "fare1000": fare1000, "cost1000": cost1000}
    # доля внутреннего рынка: те же новые пассажиры, делённые на внутренние перевозки 2025 года (market_facts.csv)
    dom = float(pd.read_csv(ROOT / "data/assumptions/network.csv").set_index("parameter").loc["market_pax_domestic_2025", "base"])
    sm = sm.assign(share_pp_dom=(sm.net_new_segments_year / dom * 100).round(2))
    return {"summary": json.loads(sm.drop(columns=["hub"]).to_json(orient="records", force_ascii=False)),
            "routes": json.loads(rt[cols].to_json(orient="records", force_ascii=False)), "nodes": nodes,
            "asm": asm, "check": check, "cmp": cmp_, "now": route_now(rt)}


def route_now(rt):
    """Как летят сейчас по каждой паре сети и кто там летает: расписание недели 7–13.12.2026 (карточки маршрутов,
    вылеты из Омска) и ручной файл data/manual/route_competitors.csv. Пустой ответ — данных о перевозчиках нет."""
    norm = pd.read_csv(ROOT / "data/manual/carrier_names.csv").set_index("raw").name.to_dict()
    key = lambda a, b: "-".join(sorted((a, b)))
    g = lambda x: "MOW" if x in MOW else x
    car = {}
    def add(a, b, c, f, src):
        if not isinstance(c, str) or not c.strip():
            return
        d = car.setdefault(key(g(a), g(b)), {})
        n = norm.get(c.strip(), c.strip())
        d[n] = (max(d.get(n, (0, ""))[0], float(f or 0)), src)
    cards = pd.read_csv(ROOT / "data/external/colleagues/route_product_cards.csv")
    for r in cards.itertuples():
        if pd.isna(r.via_airports):
            add(r.origin, r.destination, r.carrier, r.one_way_departures, "расписание 7–13.12.2026")
    om = pd.read_csv(ROOT / "data/external/colleagues/omsk_outbound_week_20261207.csv")
    for (dst, c), n in om.groupby(["destination_airport_iata", "carrier_raw"]).size().items():
        add("OMS", dst, c, n, "расписание аэропорта Омск 7–13.12.2026")
    man = pd.read_csv(ROOT / "data/manual/route_competitors.csv")
    for r in man.itertuples():
        add(r.a, r.b, r.carrier, r.flights_week_each_way, str(r.source_url))
    od = pd.read_csv(P / "od_pairs.csv").set_index(["a", "b"]).route.to_dict()
    out = {}
    for a, b in {tuple(sorted((r["from"], r["to"]))) for _, r in rt.iterrows()}:
        now = od.get((a, b)) or od.get((b, a)) or "сейчас авиамаршрута нет"
        c = car.get(key(a, b), {})
        out[key(a, b)] = {"now": now, "car": sorted([[n, round(f, 1), s_] for n, (f, s_) in c.items()], key=lambda x: -x[1])}
    # список пар, где перевозчики ещё не собраны, — задание на сбор данных (docs/27)
    from airports_meta import NAME
    import demand_model as dm
    _n = dm.nodes()
    nm = lambda x: NAME.get(x, _n.loc[x, "main_city"] if x in _n.index else x)
    todo = [{"a": a, "b": b, "city_a": nm(a), "city_b": nm(b), "now": v["now"]}
            for k, v in sorted(out.items()) if not v["car"] for a, b in [k.split("-")]]
    pd.DataFrame(todo).to_csv(ROOT / "data/manual/route_competitors_todo.csv", index=False, encoding="utf-8")
    return out


def load_spokes():
    """Шаг 2: топ-10 направлений по оценке спроса для каждого кандидата."""
    sp = pd.read_csv(P / "demand_spokes.csv")
    sp = sp[sp.status != "closed"].sort_values("pax_base", ascending=False)
    out = {}
    for hub, g in sp.groupby("hub"):
        g = g.assign(best=g.pax_best).sort_values("best", ascending=False)
        out[hub] = [{"city": r.to_city, "km": int(r.km), "base": int(r.best),
                     "cautious": int(r.best) if r.method.startswith("отчёт") else int(r.pax_cautious),
                     "direct": bool(r.direct_now), "src": r.method} for r in g.head(10).itertuples()]
    return out


def load_demand(n_regions):
    """Шаг 2: все пары с городом-кандидатом — оценки в двух мерах, метод, сезонность, сверка с коллегами."""
    d = pd.read_csv(P / "demand_estimates.csv")
    s = json.loads((P / "demand_estimates.json").read_text(encoding="utf-8"))
    cand = set(pd.read_csv(P / "longlist.csv").iata)
    out = {}
    num_ = lambda v: None if v is None or (isinstance(v, float) and v != v) else float(v)
    for r in d.itertuples():
        for c, o, oc in ((r.a, r.b, r.city_b), (r.b, r.a, r.city_a)):
            if c not in cand:
                continue
            g = rules.green_limit(n_regions.get(c), n_regions.get(o))
            out.setdefault(c, []).append({
                "to": o, "city": oc, "km": int(r.km), "ssj": bool(r.km <= g), "closed": bool(r.closed),
                "now": "прямой рейс" if r.direct_now else (r.od_route_now if isinstance(r.od_route_now, str) else "нет рейса"),
                "seg": num_(r.segments_base), "seg_lo": num_(r.segments_cautious), "od": num_(r.od_base), "od_lo": num_(r.od_cautious),
                "share": num_(r.own_trips_share), "unc": bool(r.uncertain), "how": r.segments_method, "od_how": r.od_method,
                "m": num_(r.seg_model), "an": num_(r.seg_analog) if r.direct_now else None, "sch": num_(r.seg_schedule), "sch_lo": num_(r.seg_schedule_lower),
                "obs": num_(r.observed), "col": num_(r.colleagues_od_base) if not (r.colleagues_zia_only is True) else None,
                "sum": num_(r.summer_factor), "win": num_(r.winter_factor)})
    for c in out:
        out[c].sort(key=lambda x: -(x["seg"] or 0))
    return {"pairs": out, "summary": s}


# Панель — материал проекта: служебные пометки (пути к файлам, ссылки на ветки и аудит, статусы
# согласования) убираем из показываемого текста; ссылки на первоисточники оставляем.
_TECH = re.compile(r"src/|data/|context/|docs/|research/|\.py\b|\.csv\b|\.json\b|коллег|аудит|критик|черновик|"
                   r"не утвержд|утверждён|предложени|cities_matrix|-TECH|UNKNOWN|proxy", re.I)
_REPL = [("калибровка по data/manual/known_flows.csv", "калибровка по отчётам аэропортов"),
         ("модель src/demand_model.py:", "модель спроса:"), ("модель тяготения (src/demand_model.py)", "модель тяготения")]


def clean_text(t):
    for a_, b_ in _REPL:
        t = t.replace(a_, b_)
    t2 = re.sub(r"\bdocs/[\w./-]+:?\s*", "", t)   # «docs/04: транзитной зоны нет…» → «Транзитной зоны нет…»
    if t2 != t:
        t = t2[:1].upper() + t2[1:]
    if not _TECH.search(t):
        return t

    def par(m):
        inner = m.group(1)
        if not _TECH.search(inner):
            return m.group(0)
        urls = re.findall(r"https?://[^\s;,)]+", inner)
        return f"({'; '.join(urls)})" if urls else ""
    t = re.sub(r"\(([^()]*)\)", par, t)
    parts = [x for x in re.split(r";\s*|\s·\s", t)]
    keep = []
    for x in parts:
        if _TECH.search(x):
            urls = re.findall(r"https?://[^\s;,)]+", x)
            keep += urls
        else:
            keep.append(x)
    t = "; ".join(x.strip() for x in keep if x.strip())
    return re.sub(r"\s{2,}", " ", t).strip(" ;·,")


SKIP_KEYS = {"key", "fmt", "dir", "id", "iata", "to", "from", "vkey", "group", "origin", "status_code"}


def clean(o, k=None):
    if isinstance(o, dict):
        return {kk: (vv if kk in SKIP_KEYS else clean(vv, kk)) for kk, vv in o.items()}
    if isinstance(o, list):
        return [clean(x, k) for x in o]
    if isinstance(o, str) and k not in ("geo",):
        return clean_text(o)
    return o


def monthly():
    """Дни «Ковра» по месяцам: те же события, что в data/processed/kover_days.csv (src/kover_days.py)."""
    e = pd.read_csv(P / "kover_events.csv")
    e["month"] = e.day.str[:7]
    months = sorted(e.month.unique())[-12:]
    m = e[e.month.isin(months)].groupby(["iata", "month"]).day.nunique()
    return months, {i: [int(m.get((i, mo), 0)) for mo in months] for i in e.iata.unique()}


def main():
    ll = pd.read_csv(P / "longlist.csv")
    kov = pd.read_csv(P / "kover_days.csv").set_index("iata")
    ap = pd.read_csv(ROOT / "data/raw/ourairports_airports.csv", keep_default_na=False)
    ap = ap[ap.iata_code != ""].drop_duplicates("iata_code").set_index("iata_code")
    posts = pd.read_csv(ROOT / "data/raw/favt_posts.csv")
    months, by_month = monthly()
    w = pd.read_csv(ROOT / "data/assumptions/longlist_weights.csv")

    cities = []
    for r in ll.itertuples():
        k = kov.loc[r.iata]
        cities.append({
            "city": r.city, "iata": r.iata, "region": r.region, "fd": r.fed_district,
            "lat": float(ap.loc[r.iata, "latitude_deg"]), "lon": float(ap.loc[r.iata, "longitude_deg"]),
            "pax": num(r.pax_2025), "pax_q": txt(r.pax_2025_qualifier), "pax_src": txt(r.pax_source_url),
            "catchment_pop": num(r.catchment_pop), "runway_m": num(r.runway_m),
            "dist_msk_km": num(r.dist_msk_km), "dist_ekb_km": num(r.dist_ekb_km),
            "ssj_reach_airports": num(r.ssj_reach_airports), "ssj_reach_pop": num(r.ssj_reach_pop),
            "direct_now": num(r.direct_now), "gap_pop": num(r.gap_pop),
            "kov_h1_2025": int(k.h1_2025_days), "kov_h1_2026": int(k.h1_2026_days),
            "kov_365": int(k.last365_days), "kov_months": by_month.get(r.iata, [0] * len(months)),
            "strategy_region": num(r.strategy_region),
            "transfer_zone": num(r.transfer_zone), "transfer_src": txt(r.transfer_source),
            "rostec_link": num(r.rostec_link), "rostec_note": txt(r.rostec_note), "rostec_src": txt(r.rostec_source),
            "base_carriers": txt(r.base_carriers), "base_src": txt(r.base_source),
            "competitor_hub": 1 if r.iata in COMPETITOR_HUB else None,  # нет сведений — неизвестно, а не «нет»
            "competitor_note": COMPETITOR_HUB.get(r.iata),
            "utair_mct": num(r.utair_mct_min),
        })
    ref = [{"iata": i, "name": n, "kov_365": int(kov.loc[i, "last365_days"]),
            "kov_h1_2026": int(kov.loc[i, "h1_2026_days"]),
            "kov_months": by_month.get(i, [0] * len(months))} for i, n in REF.items()]
    dests = load_dests()
    crit = json.loads((P / "criteria.json").read_text(encoding="utf-8"))
    net = load_network()
    spokes = load_spokes()
    pr = pd.read_csv(ROOT / "data/assumptions/weight_profiles.csv")
    profiles = [{"id": k, "label": g.label.iloc[0], "weights": {r.column: float(r.weight) for r in g.itertuples()}}
                for k, g in pr.groupby("profile", sort=False)]
    import demand_model as dm  # noqa: E402
    _n = dm.nodes()
    demand = load_demand(_n.region.to_dict())
    from airports_meta import NAME as _NAME
    names = {i: _NAME.get(i, _n.loc[i, "main_city"]) for i in _n.index}
    geo = json.loads((P / "geo_map.json").read_text(encoding="utf-8"))
    man_p = ROOT / "data/raw/_manifest.json"
    manifest = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {}
    inbox_p = ROOT / "data/inbox/candidates.csv"
    inbox = pd.read_csv(inbox_p, dtype=str).fillna("").head(80).to_dict("records") if inbox_p.exists() else []
    meduza = [{"iata": i, "ours": int(kov.loc[i, "h1_2026_days"]), "meduza": v} for i, v in MEDUZA.items()]
    # источники, которые не скачиваются конвейером, но входят в расчёт (для табло данных)
    soc = ROOT / "data/raw/social"
    if soc.exists() and "rosstat_mo" in manifest:
        manifest["rosstat_mo"].update(status="ok", message="копия файла Росстата из Internet Archive",
                                      fetched_at=datetime.fromtimestamp(max(f.stat().st_mtime for f in soc.iterdir())).isoformat())
    extra = [("noaa", "NOAA: погода по аэропортам 2023–2024", "http_file", ROOT / "data/raw/weather", None),
             ("rw_routes", "Нынешние рейсы Red Wings (расписание и перечень субсидий)", "manual", ROOT / "data/manual/rw_routes_now.csv", None),
             ("schedule_dec", "Расписание на 7–13 декабря 2026 года (карточки маршрутов)", "manual", ROOT / "data/external/colleagues/route_product_cards.csv", None),
             ("check_model", "Вторая модель сети: неделя декабря 2026", "manual", ROOT / "data/external/colleagues/night_common_comparison.csv", None),
             ("subsidy_budget", "Бюджет субсидий 2026 (Т—Ж, РБК) и пассажиры (Росавиация, «Профиль»)", "manual", None, "https://t-j.ru/news/minus-gospodderjka-mejreg-perevozok/"),
             ("competitors", "Конкуренты: итоги 2025 и базы", "manual", ROOT / "data/manual/competitor_bases.csv", None)]
    for k, name, kind, path, url in extra:
        if k in manifest:
            continue
        rows = None
        if path is not None and path.exists():
            rows = len(list(path.iterdir())) if path.is_dir() else max(len(pd.read_csv(path)), 0)
        t = datetime.fromtimestamp((path if path is not None and path.exists() else ROOT / "data/assumptions/network.csv").stat().st_mtime)
        manifest[k] = {"name": name, "kind": kind, "status": "manual" if kind == "manual" else "ok", "rows": rows,
                       "url": url or "", "fetched_at": t.isoformat(), "role": "data"}
    # шаги 2, 4, 5: конкуренты, выбор и рост сети, дорожная карта и риски.
    # Числа в текстах карточек — подстановки {…} из расчёта, чтобы тексты не расходились с моделью.
    choice = pd.read_csv(ROOT / "data/assumptions/choice.csv").set_index("parameter").value.to_dict()
    ramp_df = pd.read_csv(P / "fleet_ramp.csv")
    sm_df = pd.read_csv(P / "network_summary.csv")
    H = choice["chosen_hub"]
    rb = ramp_df[(ramp_df.scenario == "base_sub") & (ramp_df.hub == H)].drop_duplicates("aircraft")
    r0 = ramp_df[(ramp_df.scenario == "base") & (ramp_df.hub == H)]
    nm_ = lambda codes: ", ".join(names.get(x, x) for x in codes)
    est = pd.read_csv(P / "demand_estimates.csv")
    hp = est[((est.a == H) | (est.b == H)) & ~est.closed.astype(bool)]
    via_ovb = hp[hp.od_route_now.astype(str).str.endswith("Новосибирск")].od_base.sum()
    na_ = pd.read_csv(ROOT / "data/assumptions/network.csv").set_index("parameter")
    pct_ = lambda v: f"{float(v) * 100:.0f}%"
    hub_rows = sm_df[(sm_df.hub == H)]
    dir_rows = sm_df[sm_df.hub.isna() | (sm_df.hub == "")]
    rng_ = lambda xs: f"{min(xs):.0f}–{max(xs):.0f}" if min(xs) != max(xs) else f"{min(xs):.0f}"
    z4 = r0.sort_values("result_mln_year", ascending=False).iloc[0] if len(r0) else None
    fill = {"via_ovb": f"{via_ovb / 1000:.0f} тыс.",
            "ramp_routes": f"от {rb.routes.min()} до {rb.routes.max()} лучей",
            "ramp_first": "; ".join(f"на {a} самолётах {r} лучей" for a, r in zip(rb.aircraft.head(2), rb.routes.head(2))),
            "ramp_full": f"{rng_(rb.routes.tail(2))} лучей на {rng_(rb.aircraft.tail(2))} самолётах",
            "ramp_fleet_first": rng_(rb.aircraft.head(2)), "ramp_fleet_full": rng_(rb.aircraft.tail(2)),
            "pilot_spokes": nm_(str(rb.iloc[0].spokes).split(";")[:3]) if len(rb) else "",
            "kover_hub": rng_(hub_rows.kover_days_avg[hub_rows.scenario.str.startswith("base")]),
            "kover_direct": rng_(dir_rows.kover_days_avg[dir_rows.scenario.str.startswith("base")]),
            "nosub_fleet": str(int(z4.aircraft)) if z4 is not None else "", "nosub_loss": f"{abs(z4.result_mln_year):.0f}" if z4 is not None else "",
            "nosub_res": (("+" if z4.result_mln_year >= 0 else "−") + f"{abs(z4.result_mln_year):.0f}") if z4 is not None else "",
            "cap_comp_b": pct_(na_.loc["capture_competitive", "base"]), "cap_comp_c": pct_(na_.loc["capture_competitive", "cautious"])}
    def rd(f):
        recs = pd.read_csv(ROOT / f, dtype=str).fillna("").to_dict("records")
        return [{k: (v.format(**fill) if isinstance(v, str) and "{" in v else v) for k, v in r.items()} for r in recs]
    cj = json.loads((ROOT / "context/13_competitors/competitors.json").read_text(encoding="utf-8"))
    scale = [{"name": c["name"], "pax": c["pax_million"], "rw": c["id"] == "rw"} for c in cj["carriers"]]
    ramp = ramp_df.to_dict("records")
    # цель №2: тексты — data/manual/strategy_no2.json, числа — из расчёта сети
    sb_ = sm_df[(sm_df.scenario == "base_sub") & (sm_df.hub == H)].iloc[0]
    s0_ = sm_df[(sm_df.scenario == "base") & (sm_df.hub == H)].iloc[0]
    rt_ = pd.read_csv(P / "network_routes.csv")
    tri = (rt_[(rt_.scenario == "base") & rt_.variant.str.startswith("Прямые")]
           .groupby("variant").agg(res=("triangle_result_mln_year", "first")).sort_values("res", ascending=False))
    pos_tri = [(v, r.res) for v, r in tri.iterrows() if r.res > 0]
    tri_name = lambda v: " — ".join(names.get(x, x) for x in v.replace("Прямые ", "").split("-")[1:])
    sg = lambda v: ("+" if v >= 0 else "−") + f"{abs(v):,.0f}".replace(",", " ")
    fill.update({
        "hub_line": f"Хаб в городе {names.get(H, H)}: {sg(sb_.result_mln_year)} млн ₽ в год при доступной поддержке ({sg(s0_.result_mln_year)} без неё), "
                    f"{int(sb_.aircraft)} самолётов, +{sb_.share_pp:.2f} п. п. доли рынка.".replace(".", ",", 1).replace("п, п,", "п. п."),
        "direct_line": ("Плюс к хабу — прямые рейсы, которые окупаются сами: " + "; ".join(f"{tri_name(v)} ({sg(x)} млн ₽)" for v, x in pos_tri[:4]) + ".")
                       if pos_tri else "Прямые рейсы по отдельности не окупаются при нынешних допущениях."})
    no2 = json.loads((ROOT / "data/manual/strategy_no2.json").read_text(encoding="utf-8"))
    def fmt_(o):
        if isinstance(o, str):
            return o.format(**fill) if "{" in o else o
        if isinstance(o, list):
            return [fmt_(x) for x in o]
        if isinstance(o, dict):
            return {k: fmt_(v) for k, v in o.items()}
        return o
    no2 = fmt_(no2)
    no2["hub_pax"] = float(s0_.segments_year) / 1e6
    steps = {"case": case_answer(names), "no2": no2, "competitors": rd("data/manual/competitor_bases.csv"), "scale": scale, "ramp": ramp, "choice": choice,
             "roadmap": rd("data/manual/roadmap.csv"), "risks": rd("data/manual/risks.csv"),
             "rw_share_2025": float(na_.loc["rw_pax_2025", "base"]) / float(na_.loc["market_pax_2025", "base"]) * 100}
    p = posts.copy()
    data = {
        "meta": {"built": datetime.now().strftime("%d.%m.%Y %H:%M"), "posts": int(len(posts)),
                 "posts_from": p.dt_msk.min()[:10], "posts_to": p.dt_msk.max()[:10],
                 "months": months},
        "cities": cities, "ref": ref, "meduza": meduza,
        "bases": {b: [float(ap.loc[x, "latitude_deg"]), float(ap.loc[x, "longitude_deg"])] for b, x in (("MOW", "SVO"), ("SVX", "SVX"))},
        "dests": dests, "geo": geo, "manifest": manifest,
        "range": {"ssj": rules.GREEN, "ssj_south": rules.GREEN_SOUTH, "tu204": rules.TU204, "tu214": rules.TU214, "rail_hr": rules.RAIL_OK_HR, "min_dist": rules.MIN_DIST_KM, "filter_km": rules.FILTER_OPTION_KM},
        "criteria": crit["criteria"], "values": crit["values"], "net": net, "spokes": spokes, "demand": demand, "profiles": profiles, "names": names, "steps": steps,
        "weights": [{"key": x.column, "label": x.criterion, "dir": x.direction,
                     "w": float(x.weight), "why": x.why} for x in w.itertuples()],
        "research": research(_n),
    }
    data = clean(data)
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    ai = (ROOT / "src/dashboard_ai_workflow.html").read_text(encoding="utf-8")
    # Дашборды 1 и 2 — архив (archive/dashboards); главная страница сайта — Дашборд 3 (src/build_dashboard3.py)
    (ROOT / "archive/dashboards").mkdir(parents=True, exist_ok=True)
    for tpl_name, out_name in (("dashboard_template.html", "redwings_panel_v2.html"), ("dashboard_template_v1.html", "redwings_panel_v1.html")):
        tpl = (ROOT / "src" / tpl_name).read_text(encoding="utf-8").replace("<!--__AI_WORKFLOW__-->", ai)
        out = ROOT / "archive/dashboards" / out_name
        out.write_text(tpl.replace("/*__DATA__*/null", js), encoding="utf-8")
        print("ok", out, len(cities), "городов,", len(months), "мес.")


if __name__ == "__main__":
    main()
