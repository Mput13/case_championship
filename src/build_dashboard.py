"""Собирает панель расчёта outputs/redwings_panel.html из таблиц проекта.

Берёт: data/processed/longlist.csv, kover_days.csv, data/raw/favt_posts.csv (помесячно),
       data/raw/ourairports_airports.csv (координаты), data/assumptions/longlist_weights.csv
Вписывает всё одним JSON в шаблон src/dashboard_template.html.
Запуск: python src/build_dashboard.py   (после build_longlist.py)
"""
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

spec = importlib.util.spec_from_file_location("kd", ROOT / "src" / "kover_days.py")
kd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kd)

REF = {"SVX": "Екатеринбург", "OVB": "Новосибирск", "SVO": "Шереметьево", "DME": "Домодедово",
       "VKO": "Внуково", "LED": "Санкт-Петербург", "KRR": "Краснодар"}
MEDUZA = {"KZN": 51, "AER": 70, "KGD": 1, "VVO": 0, "IKT": 0, "KHV": 0, "OVB": 0}
COMPETITOR_HUB = {"KJA": "группа «Аэрофлот», хаб (аэропорт, итоги 2025)",
                  "IKT": "S7, хаб (сайт S7)", "VVO": "«Аврора» и S7, базовые (аэропорт, итоги 2025)"}


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


def monthly(posts):
    p = posts.copy()
    p["text"] = p.text.fillna("")
    p = p[p.text.str.contains(kd.AIRPORT_MSG) & ~p.text.str.contains(kd.LIFTED)]
    p["day"] = p.dt_msk.str[:10]
    rows = []
    for r in p.itertuples():
        for i in kd.find_airports(r.text):
            rows.append((i, r.day))
    e = pd.DataFrame(rows, columns=["iata", "day"]).drop_duplicates()
    e["month"] = e.day.str[:7]
    months = sorted(e.month.unique())[-12:]
    m = e[e.month.isin(months)].groupby(["iata", "month"]).size()
    return months, {i: [int(m.get((i, mo), 0)) for mo in months] for i in e.iata.unique()}


def main():
    ll = pd.read_csv(P / "longlist.csv")
    kov = pd.read_csv(P / "kover_days.csv").set_index("iata")
    ap = pd.read_csv(ROOT / "data/raw/ourairports_airports.csv", keep_default_na=False)
    ap = ap[ap.iata_code != ""].drop_duplicates("iata_code").set_index("iata_code")
    posts = pd.read_csv(ROOT / "data/raw/favt_posts.csv")
    months, by_month = monthly(posts)
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
            "competitor_hub": 1 if r.iata in COMPETITOR_HUB else 0,
            "competitor_note": COMPETITOR_HUB.get(r.iata),
            "utair_mct": num(r.utair_mct_min),
        })
    ref = [{"iata": i, "name": n, "kov_365": int(kov.loc[i, "last365_days"]),
            "kov_h1_2026": int(kov.loc[i, "h1_2026_days"]),
            "kov_months": by_month.get(i, [0] * len(months))} for i, n in REF.items()]
    dests = load_dests()
    crit = json.loads((P / "criteria.json").read_text(encoding="utf-8"))
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
        "bases": {"MOW": [55.972, 37.415], "SVX": [56.743, 60.803]},
        "dests": dests, "geo": geo, "manifest": manifest,
        "criteria": crit["criteria"], "values": crit["values"],
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
