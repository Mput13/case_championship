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
    cols = ["scenario", "vkey", "variant", "from", "to", "km", "freq_week_each_way", "pax_year_segments",
            "pax_year_local", "pax_year_rw_migrated", "load_factor", "direct_now", "range_light", "demand_source", "subsidy_rule", "revenue_mln_year", "cost_mln_year", "result_mln_year"]
    if "triangle_result_mln_year" in rt.columns:
        cols.append("triangle_result_mln_year")
    # допущения расчёта — прямо из data/assumptions/network.csv, чтобы панель не расходилась с моделью
    na = pd.read_csv(ROOT / "data/assumptions/network.csv").set_index("parameter")
    asm = {k: [float(na.loc[k, "base"]), float(na.loc[k, "cautious"])] for k in
           ("seats", "lf_max", "fare_fixed_rub", "fare_per_km_rub", "subsidy_rub_per_flight", "subsidy_months", "subsidy_max_prior_pax", "fuel_rub_per_t", "fuel_compensation_rub_per_t", "min_freq_week", "max_freq_week", "capture_open",
            "capture_competitive", "capture_transfer", "transfer_fare_factor", "weeks_per_year", "fleet_cap",
            "spare_aircraft", "max_routes", "rw_existing_lf", "rw_pax_2025", "market_pax_2025",
            "min_routes", "direct_max_freq_week", "thin_route_pax_day")}
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
    cost1000 = [nmod.leg_cost(AS[k], 1000, False, 100 * AS[k]["lf_max"])[1] for k in ("base", "cautious")]
    cmp_ = {"demand": float(est.od_cautious.sum() / est.od_base.sum()), "fare": fare1000[1] / fare1000[0], "cost": cost1000[1] / cost1000[0]}
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
    steps = {"competitors": rd("data/manual/competitor_bases.csv"), "scale": scale, "ramp": ramp, "choice": choice,
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
        "range": {"ssj": rules.GREEN, "ssj_south": rules.GREEN_SOUTH, "tu204": rules.TU204, "tu214": rules.TU214, "rail_hr": rules.RAIL_OK_HR, "min_dist": rules.MIN_DIST_KM},
        "criteria": crit["criteria"], "values": crit["values"], "net": net, "spokes": spokes, "demand": demand, "profiles": profiles, "names": names, "steps": steps,
        "weights": [{"key": x.column, "label": x.criterion, "dir": x.direction,
                     "w": float(x.weight), "why": x.why} for x in w.itertuples()],
    }
    data = clean(data)
    tpl = (ROOT / "src/dashboard_template.html").read_text(encoding="utf-8")
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = ROOT / "outputs/redwings_panel.html"
    out.write_text(tpl.replace("/*__DATA__*/null", js), encoding="utf-8")
    print("ok", out, len(cities), "городов,", len(months), "мес.")


if __name__ == "__main__":
    main()
