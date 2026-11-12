"""Цифры для презентации: берёт те же файлы, что панель, и пишет outputs/presentation/deck_data.json.

Запуск: py -3.13 src/deck/deck_data.py, затем node src/deck/build_deck.js
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import rules  # noqa: E402

P = ROOT / "data" / "processed"
A = ROOT / "data" / "assumptions"
OUT = ROOT / "outputs" / "presentation"
OUT.mkdir(parents=True, exist_ok=True)


def asm():
    a = pd.read_csv(A / "network.csv").set_index("parameter")
    return {k: [float(a.loc[k, "base"]), float(a.loc[k, "cautious"])] for k in a.index}


def main():
    AS = asm()
    sm = pd.read_csv(P / "network_summary.csv")
    rt = pd.read_csv(P / "network_routes.csv")
    ramp = pd.read_csv(P / "fleet_ramp.csv")
    choice = pd.read_csv(A / "choice.csv").set_index("parameter").value
    no2 = json.loads((ROOT / "data" / "manual" / "strategy_no2.json").read_text(encoding="utf-8"))
    comp = json.loads((ROOT / "context" / "13_competitors" / "competitors.json").read_text(encoding="utf-8"))
    H = choice["chosen_hub"]

    # лонглист: как на табло панели — без городов ближе MIN_DIST_KM к базам
    ll = pd.read_csv(P / "longlist.csv")
    sc = pd.read_csv(P / "longlist_scores.csv")[["iata", "score", "top3_share_random"]]
    ll = ll.merge(sc, on="iata")
    ll["dist_base"] = ll[["dist_msk_km", "dist_ekb_km"]].min(axis=1)
    out_filter = ll[ll.dist_base < rules.MIN_DIST_KM]
    board = ll[ll.dist_base >= rules.MIN_DIST_KM].sort_values("score", ascending=False)
    board_rows = [{"city": r.city, "iata": r.iata, "score": round(r.score * 100, 1), "kover": int(r.last365_days),
                   "pax": float(r.pax_2025), "dist": int(r.dist_base), "top3": float(r.top3_share_random)}
                  for r in board.itertuples()]

    def var(scen, key):
        if key == "DIRECT":
            r = sm[(sm.scenario == scen) & (sm.hub.isna())].iloc[0]
        else:
            r = sm[(sm.scenario == scen) & (sm.hub == key)].iloc[0]
        return {k: (v.item() if hasattr(v, "item") else v) for k, v in r.items() if k != "hub" or key != "DIRECT"}

    keys = [h for h in sm[(sm.scenario == "base") & (sm.main == True)].hub.dropna()] + ["DIRECT"]  # noqa: E712
    variants = {k: {s: var(s, k) for s in ["base", "base_sub", "cautious", "cautious_sub"]} for k in keys}
    allhubs = sm[(sm.scenario == "base") & sm.hub.notna()].sort_values("result_mln_year", ascending=False)
    ranks = [{"hub": r.hub, "variant": r.variant, "result": int(r.result_mln_year), "kover": int(r.kover_days_avg)}
             for r in allhubs.itertuples()]

    routes = rt[(rt.scenario == "base") & (rt.variant == f"Хаб {H}")]
    hub_routes = [{"to": r.to, "city": r.to_city, "km": int(r.km), "freq": int(r.freq_week_each_way),
                   "pax": int(r.pax_year_segments), "transfer": int(r.pax_year_transfer_seg), "lf": float(r.load_factor),
                   "result": float(r.result_mln_year), "revenue": float(r.revenue_mln_year), "cost": float(r.cost_mln_year),
                   "local": int(r.pax_year_local)}
                  for r in routes.itertuples()]

    ap = pd.read_csv(ROOT / "data" / "raw" / "ourairports_airports.csv", low_memory=False)
    codes = {H, "SVX", "SVO", *routes.to}
    ap = ap[ap.iata_code.isin(codes) & ap.type.str.contains("airport")]
    geo = {r.iata_code: [r.longitude_deg, r.latitude_deg] for r in ap.itertuples()}
    geo["MOW"] = geo.pop("SVO")

    # пример одного рейса: экономика по формулам модели (база)
    ex = routes.sort_values("pax_year_segments").iloc[len(routes) // 2] if False else routes[routes.to == "KUF"].iloc[0]
    flights = ex.freq_week_each_way * 2 * AS["weeks_per_year"][0]
    km = float(ex.km)
    bh = km * AS["route_factor"][0] / AS["block_speed_kmh"][0] + AS["block_fixed_h"][0]
    fuel_t = AS["fuel_t_per_hour"][0] * bh + AS["fuel_t_per_cycle"][0]
    pax_fl = ex.pax_year_segments / flights
    parts = {
        "fuel": fuel_t * (AS["fuel_rub_per_t"][0] - AS["fuel_compensation_rub_per_t"][0]),
        "mro": AS["mro_rub_per_hour"][0] * bh,
        "crew": AS["crew_rub_per_hour"][0] * bh,
        "nav": AS["navigation_rub_per_hour"][0] * bh,
        "ground": AS["ground_rub_per_flight"][0] + AS["deicing_rub_per_flight"][0],
        "pax": AS["pax_cost_rub"][0] * pax_fl,
    }
    example = {"from": H, "to": ex.to, "city": ex.to_city, "km": km, "block_h": bh, "fuel_t": fuel_t, "pax": pax_fl,
               "fare_local": AS["fare_fixed_rub"][0] + AS["fare_per_km_rub"][0] * km,
               "revenue": ex.revenue_mln_year * 1e6 / flights, "cost": ex.cost_mln_year * 1e6 / flights,
               "cost_formula": sum(parts.values()), "parts": parts, "flights_year": flights}

    cmp = {}
    for k, col in [("demand", "od_trips_year"), ("revenue", "revenue_mln_year")]:
        cmp[k] = variants[H]["cautious"][col] / variants[H]["base"][col]
    # общий ответ «хаб или прямые»: сколько хабов окупается и сколько треугольников прямой сети в плюсе
    hubs_base = sm[(sm.scenario == "base") & sm.hub.notna()]
    tri = rt[(rt.scenario == "base") & rt.variant.str.startswith("Прямые")].drop_duplicates("variant")
    llo = ll.set_index("iata").loc[H]
    tp = pd.read_csv(P / "transfer_potential.csv").set_index("iata").loc[H]
    general = {"hubs_total": int(len(hubs_base)), "hubs_positive": int((hubs_base.result_mln_year > 0).sum()),
               "triangles": int(len(tri)), "triangles_positive": int((tri.triangle_result_mln_year > 0).sum()),
               "hub_gap_pop": float(llo.gap_pop), "hub_transfer_pairs": int(tp.transfer_pairs),
               "hub_transfer_demand": float(tp.transfer_demand_base), "hub_direct_now": int(llo.direct_now)}
    # проверка коллег по неделе рейсов (P34, src/fetch_colleague_research.py): треугольник и челноки в Сочи из Екатеринбурга
    ctl = pd.read_csv(ROOT / "data/external/colleagues/p34_triangle_shuttle_controls.csv")
    general["tri_check"] = {r.programme: float(r.delta_vs_keep_mln_month) for r in ctl[ctl.scenario == "base"].itertuples()}
    data = {
        "general": general,
        "hub": H, "asm": AS, "variants": variants, "ranks": ranks, "board": board_rows,
        "board_out": out_filter.city.tolist(), "longlist_n": len(ll), "min_dist": rules.MIN_DIST_KM,
        "routes": hub_routes, "geo": geo, "example": example,
        "ramp": ramp[(ramp.scenario == "base") & (ramp.hub == H)].to_dict("records"),
        "ramp_when": dict(x.split(":", 1) for x in choice["ramp_when"].split(";")),
        "no2": no2, "competitors": comp,
        "od_fit": json.loads((P / "od_fit.json").read_text(encoding="utf-8")),
        "seg_fit": json.loads((P / "demand_fit.json").read_text(encoding="utf-8")),
    }
    (OUT / "deck_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("ok", OUT / "deck_data.json", "табло:", [(r["city"], r["score"]) for r in board_rows[:3]], "пример:", round(example["cost_formula"]), round(example["cost"]))


if __name__ == "__main__":
    main()
