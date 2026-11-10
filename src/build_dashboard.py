"""Собирает панель расчёта outputs/redwings_panel.html из таблиц проекта.

Берёт: data/processed/longlist.csv, kover_days.csv, data/raw/favt_posts.csv (помесячно),
       data/raw/ourairports_airports.csv (координаты), data/assumptions/longlist_weights.csv
Вписывает всё одним JSON в шаблон src/dashboard_template.html.
Запуск: python src/build_dashboard.py   (после build_longlist.py)
"""
import json
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


MOW = {"SVO", "DME", "VKO", "ZIA"}


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
            "pax_year_local", "load_factor", "direct_now", "range_light", "demand_source"]
    return {"summary": json.loads(sm.drop(columns=["hub"]).to_json(orient="records", force_ascii=False)),
            "routes": json.loads(rt[cols].to_json(orient="records", force_ascii=False)), "nodes": nodes}


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
    p = posts.copy()
    data = {
        "meta": {"built": datetime.now().strftime("%d.%m.%Y %H:%M"), "posts": int(len(posts)),
                 "posts_from": p.dt_msk.min()[:10], "posts_to": p.dt_msk.max()[:10],
                 "months": months},
        "cities": cities, "ref": ref, "meduza": meduza,
        "bases": {b: [float(ap.loc[x, "latitude_deg"]), float(ap.loc[x, "longitude_deg"])] for b, x in (("MOW", "SVO"), ("SVX", "SVX"))},
        "dests": dests, "geo": geo, "manifest": manifest,
        "range": {"ssj": rules.GREEN, "ssj_south": rules.GREEN_SOUTH, "tu204": rules.TU204, "tu214": rules.TU214},
        "criteria": crit["criteria"], "values": crit["values"], "net": net, "spokes": spokes, "demand": demand, "profiles": profiles, "names": names,
        "weights": [{"key": x.column, "label": x.criterion, "dir": x.direction,
                     "w": float(x.weight), "why": x.why} for x in w.itertuples()],
    }
    tpl = (ROOT / "src/dashboard_template.html").read_text(encoding="utf-8")
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = ROOT / "outputs/redwings_panel.html"
    out.write_text(tpl.replace("/*__DATA__*/null", js), encoding="utf-8")
    print("ok", out, len(cities), "городов,", len(months), "мес.")


if __name__ == "__main__":
    main()
