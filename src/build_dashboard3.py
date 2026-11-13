"""Собирает Дашборд 3 (outputs/redwings_panel.html, главная страница сайта): панель для аналитиков Red Wings.

Все числа берутся из таблиц проекта; в шаблоне src/dashboard3_template.html цифр модели нет.
Вкладки: загрузка данных (проверка по правилам, разница, быстрая оценка, согласование),
сеть хаба, как считается, данные.

Входы:
  data/assumptions/network.csv, data/assumptions/choice.csv      — допущения и выбранный хаб
  data/processed/network_routes.csv, network_summary.csv        — результат network_model.py
  data/processed/airport_seasonality.csv                        — профили месяцев
  data/processed/destinations.csv, longlist.csv, geo_map.json   — координаты и карта
  data/processed/criteria.json, longlist_scores.csv             — рейтинг городов
  data/processed/demand_estimates.csv                           — прежние значения пар для сравнения
  data/manual/known_flows.csv, upload_rules.csv, dashboard3_demo.json
  data/raw/_manifest.json                                       — каталог источников
Запуск: py src/build_dashboard3.py (входит в py src/update.py)
"""
import csv
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"


def rd(path):
    with open(ROOT / path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def assumptions():
    rows = rd("data/assumptions/network.csv")
    asm = [{"k": r["parameter"], "b": r["base"], "c": r["cautious"], "u": r["unit"], "s": r["source"]} for r in rows]
    par = {sc: {r["parameter"]: num(r[sc]) for r in rows} for sc in ("base", "cautious")}
    return asm, par


def seasonality():
    return {r["iata"]: [num(r[f"m{i}"], 1.0) for i in range(1, 13)] for r in rd("data/processed/airport_seasonality.csv")}


def ray(r, A, seas):
    """Луч хаба: спрос, частоты, деньги и разбивка затрат по ставкам допущений, сведённая к итогу модели."""
    km = num(r["km"])
    south = "юг" in r["range_light"]
    bh = A["block_fixed_h"] + km * (A["route_factor_south"] if south else A["route_factor"]) / A["block_speed_kmh"]
    fs, fw = int(num(r["freq_week_each_way"])), int(num(r["freq_week_winter"]))
    w = A["weeks_per_year"]
    flights = 2 * (fs * w * 7 / 12 + fw * w * 5 / 12)
    seg = num(r["pax_year_segments"])
    cc = {"fuel": flights * (A["fuel_t_per_hour"] * bh + A["fuel_t_per_cycle"]) * A["fuel_rub_per_t"],
          "mro": flights * bh * A["mro_rub_per_hour"], "crew": flights * bh * A["crew_rub_per_hour"],
          "nav": flights * bh * A["navigation_rub_per_hour"], "ground": flights * A["ground_rub_per_flight"],
          "deice": flights * A["deicing_rub_per_flight"], "pax": seg * A["pax_cost_rub"]}
    tot = sum(cc.values()) or 1
    cost = num(r["cost_mln_year"])
    a, b = r["from"], r["to"]
    prof = [(x + y) / 2 for x, y in zip(seas.get(a, [1] * 12), seas.get(b, [1] * 12))]
    m = sum(prof) / 12
    return {"to": b, "city": r["to_city"], "km": int(km), "fs": fs, "fw": fw, "bh": round(bh, 2), "flights": round(flights),
            "local": int(num(r["pax_year_local"])), "tr": int(num(r["pax_year_transfer_seg"])), "seg": int(seg),
            "lf": num(r["load_factor"]), "spill": int(num(r["pax_year_spilled"])), "src": r["demand_source"],
            "direct": r["direct_now"] == "True", "sub": r["subsidy_rule"], "rev": num(r["revenue_mln_year"]),
            "subsidy": num(r["subsidy_mln_year"]), "cost": cost, "res": num(r["result_mln_year"]), "light": r["range_light"],
            "cc": {k: round(v / tot * cost, 2) for k, v in cc.items()}, "prof": [round(v / m, 3) for v in prof]}


def network(par, seas):
    out = {}
    for sc in ("base", "cautious"):
        seen, hubs = set(), {}
        for r in rd("data/processed/network_routes.csv"):
            if r["scenario"] != sc or not r["variant"].startswith("Хаб "):
                continue
            h = r["variant"][4:]
            key = (h, r["from"], r["to"])
            if key in seen:
                continue
            seen.add(key)
            hubs.setdefault(h, []).append(ray(r, par[sc], seas))
        out[sc] = hubs
    keys = ["hub", "variant", "routes", "aircraft", "flights_week", "segments_year", "od_trips_year", "transfer_od_year",
            "revenue_mln_year", "subsidy_mln_year", "var_cost_mln_year", "result_mln_year", "share_pp",
            "fare_up_to_breakeven_pct", "kover_days_avg", "check_segments_minus_od"]
    summ = [{"scenario": r["scenario"], **{k: (r[k] if k in ("hub", "variant") else num(r[k])) for k in keys}}
            for r in rd("data/processed/network_summary.csv") if r["scenario"] in ("base", "cautious") and r["hub"]]
    return out, summ


def geo(names):
    lon0, lat0 = 80, 60

    def pj(lon, lat):
        if lon < 0:
            lon += 360
        return (lon - lon0) * math.cos(math.radians(lat0)) * 10 + 500, (lat0 - lat) * 10 + 250

    g = json.loads((P / "geo_map.json").read_text(encoding="utf-8"))
    rus = next(x for x in g["countries"] if x["properties"].get("ADM0_A3") == "RUS")
    paths = []
    for poly in rus["geometry"]["coordinates"]:
        if len(poly[0]) < 30:
            continue
        pts = [pj(*p) for p in poly[0]]
        simp = [pts[0]]
        for p in pts[1:]:
            if math.dist(p, simp[-1]) > 3:
                simp.append(p)
        if len(simp) >= 8:
            paths.append("M" + "L".join(f"{x:.0f},{y:.0f}" for x, y in simp) + "Z")
    pts = {}
    for r in rd("data/processed/destinations.csv"):
        x, y = pj(num(r["lon"]), num(r["lat"]))
        pts[r["to"]] = [round(x, 1), round(y, 1)]
        names.setdefault(r["to"], r["to_city"])
    # коды городов с несколькими аэропортами нет в destinations.csv; координаты центра города (Википедия)
    for code, (lon, lat) in {"MOW": (37.62, 55.75), "LED": (30.31, 59.94)}.items():
        if code not in pts:
            x, y = pj(lon, lat)
            pts[code] = [round(x, 1), round(y, 1)]
    for r in rd("data/processed/longlist.csv"):
        names.setdefault(r["iata"], r["city"])
    return " ".join(paths), pts, g.get("source", "")


def rating():
    crit = json.loads((P / "criteria.json").read_text(encoding="utf-8"))
    keys = [c["key"] for c in crit["criteria"]]
    sc = rd("data/processed/longlist_scores.csv")
    names = {}
    cards = {}
    for r in sc:
        rows = []
        for c in crit["criteria"]:
            v = crit["values"].get(r["iata"], {}).get(c["key"], {})
            v = v if isinstance(v, dict) else {"v": v}
            names[c["key"]] = c.get("name") or c.get("label") or c.get("short")
            rows.append({"raw": v.get("v"), "t": v.get("t"), "src": v.get("s") or "", "weak": v.get("weak") or ""})
        cards[r["iata"]] = {"lo": num(r["score_low"]), "hi": num(r["score_high"]), "rows": rows}
    cr = [{"k": c["key"], "n": c.get("short"), "full": names[c["key"]], "dir": c.get("dir"), "w": c.get("weight") or 0,
           "unit": c.get("unit") or ""} for c in crit["criteria"]]
    far = {r["iata"]: int(r["rank"]) for r in rd("data/processed/longlist_scores_min500.csv")}
    rt = [{"iata": r["iata"], "rank": int(r["rank"]), "rank_far": far.get(r["iata"]), "city": r["city"], "score": num(r["score"]),
           "n": [(num(r[k]) if r.get(k) not in ("", None) else None) for k in keys]} for r in sorted(sc, key=lambda r: int(r["rank"]))]
    return cr, rt, cards


def pairs():
    out = {}
    for r in rd("data/processed/demand_estimates.csv"):
        a, b = sorted([r["a"], r["b"]])
        kind = "f" if r["observed"] else ("e" if r["uncertain"] == "True" else "m")
        out[f"{a}-{b}"] = [int(num(r["segments_base"])), kind, round(num(r["estimates_ratio"], 1), 2)]
    return out


def transfers(hubs):
    """Куда сейчас пересаживаются: пары с городом-хабом без прямого рейса, где сегодня летят через чужой аэропорт."""
    sys.path.insert(0, str(ROOT / "src"))
    import demand_model as dm
    import rules
    reg = dm.nodes().region.to_dict()
    out = {h: [] for h in hubs}
    for r in rd("data/processed/demand_estimates.csv"):
        now = r.get("od_route_now") or ""
        od = num(r.get("od_base"))
        if not now.startswith("с пересадкой: ") or r.get("closed") == "True" or od <= 0:
            continue
        km = num(r["km"])
        for c, o, oc in ((r["a"], r["b"], r["city_b"]), (r["b"], r["a"], r["city_a"])):
            if c in out:
                out[c].append({"to": o, "city": oc, "via": now[len("с пересадкой: "):], "od": round(od),
                               "ssj": km <= rules.green_limit(reg.get(c), reg.get(o)), "unc": r.get("uncertain") == "True"})
    for c in out:
        out[c].sort(key=lambda x: -x["od"])
    return out


def hub_info(hubs, seas, cards, crit):
    """Поля посадочного талона хаба: регион, пассажиропоток аэропорта, дни «Ковра», месяцы."""
    ll = {r["iata"]: r for r in rd("data/processed/longlist.csv")}
    ki = next((i for i, c in enumerate(crit) if c["k"] == "last365_days"), None)
    out = {}
    for h in hubs:
        r = ll.get(h, {})
        kov = cards.get(h, {}).get("rows", [{}] * (ki + 1))[ki].get("raw") if ki is not None and h in cards else None
        out[h] = {"region": r.get("region", ""), "fd": r.get("fed_district", ""), "pax": num(r.get("pax_2025"), None),
                  "pax_src": r.get("pax_source_url", ""), "kover": kov, "prof": seas.get(h)}
    return out


def checks(H, summ, rays_base, kf, asm):
    s = {(x["scenario"], x["hub"]): x for x in summ}
    b, c = s[("base", H)], s[("cautious", H)]
    rs = rays_base[H]
    out = [
        ["ok" if abs(b["check_segments_minus_od"]) < 1 else "bad", "Сегменты = поездки + пересадки", f"разница {b['check_segments_minus_od']:.0f} пассажиров"],
        ["ok" if max(r["lf"] for r in rs) <= 0.95 else "bad", "Загрузка не выше 0,95", f"наибольшая за год {max(r['lf'] for r in rs):.2f}".replace(".", ",")],
        ["ok" if all(r["light"].startswith("зелёный") for r in rs) else "warn", "Все лучи в зелёной зоне дальности", "SSJ до 2 300 км, юг и запад до 2 150 км"],
        ["ok" if all(x["s"].strip() for x in asm) and all(x["source"].strip() for x in kf) else "bad", "У каждой входной цифры есть источник", "колонка source в допущениях и известных потоках"],
        ["ok" if b["result_mln_year"] >= c["result_mln_year"] else "bad", "Базовый сценарий не хуже осторожного", f"{b['result_mln_year']:+.0f} против {c['result_mln_year']:+.0f}".replace("-", "−")],
    ]
    unc = [r["city"] for r in rs if "неуверенно" in r["src"]]
    if unc:
        out.append(["warn", "Спрос оценён неуверенно: " + ", ".join(unc), "методы оценки расходятся; нужен отчёт аэропорта о потоке пары"])
    neg = [r["city"] for r in rs if r["res"] < 0]
    if neg:
        out.append(["warn", "Лучи в минусе: " + ", ".join(neg), "модель оставляет их ради пересадок на другие лучи"])
    return out


def main():
    asm, par = assumptions()
    seas = seasonality()
    rays, summ = network(par, seas)
    H = next(r["value"] for r in rd("data/assumptions/choice.csv") if r["parameter"] == "chosen_hub")
    names = {}
    for sc in rays.values():
        for h, rs in sc.items():
            for r in rs:
                names.setdefault(r["to"], r["city"])
    for x in summ:
        names.setdefault(x["hub"], x["variant"].replace("Хаб ", ""))
    mp, pts, map_src = geo(names)
    cr, rt, cards = rating()
    kf = rd("data/manual/known_flows.csv")
    manifest = json.loads((ROOT / "data/raw/_manifest.json").read_text(encoding="utf-8"))
    src = [{"id": k, "name": v["name"], "owner": v["owner"], "url": v["url"], "kind": v["kind"], "role": v["role"],
            "feeds": v.get("feeds", []), "rows": v.get("rows"), "fetched": (v.get("fetched_at") or "")[:10], "license": v.get("license", "")}
           for k, v in manifest.items()]
    rules = rd("data/manual/upload_rules.csv")
    demo = json.loads((ROOT / "data/manual/dashboard3_demo.json").read_text(encoding="utf-8"))
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        commit = ""
    D = {"meta": {"built": datetime.now().strftime("%d.%m.%Y %H:%M"), "commit": commit, "hub": H, "map_src": map_src},
         "asm": asm, "hubs": summ, "rays": rays, "names": names, "pts": pts, "map": mp,
         "crit": cr, "rating": rt, "cards": cards, "src": src, "kf": kf, "kf_head": list(kf[0].keys()),
         "pairs": pairs(), "rules": rules, "demo": demo, "checks": checks(H, summ, rays["base"], kf, asm),
         "transfers": transfers(list(rays["base"])), "hubinfo": hub_info(list(rays["base"]), seas, cards, cr)}
    tpl = (ROOT / "src/dashboard3_template.html").read_text(encoding="utf-8")
    html = tpl.replace("__DATA__", json.dumps(D, ensure_ascii=False, separators=(",", ":")))
    out = ROOT / "outputs/redwings_panel.html"
    out.write_text(html, encoding="utf-8")
    print(f"Дашборд 3: {out.relative_to(ROOT)}, {len(html) // 1024} КБ, хабов {len(rays['base'])}, пар {len(D['pairs'])}")


if __name__ == "__main__":
    main()
