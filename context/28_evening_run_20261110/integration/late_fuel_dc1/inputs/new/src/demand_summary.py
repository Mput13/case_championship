"""Сводка спроса по кандидатам в хаб: сколько пассажиров в год даёт каждое направление из города.

Для каждого кандидата берём все аэропорты в зоне SSJ (data/processed/destinations.csv) и оценку
спроса по паре (data/processed/demand_pairs.csv). Делим на:
  есть прямой рейс  — рынок, где придётся отбирать пассажиров у тех, кто уже летает;
  нет прямого рейса — оценка масштаба рынка пары по модели (люди едут поездом, с пересадкой или не едут).
Аэропорты Москвы сведены в один узел MOW.

Выход: data/processed/demand_by_candidate.csv (итог по городу)
       data/processed/demand_spokes.csv (каждое направление: оценка, осторожно/оптимистично, источник)
Запуск: python src/demand_summary.py   (после src/demand_model.py)
"""
from pathlib import Path

import pandas as pd

import rules

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
MOW = rules.MOW_AIRPORTS


def main():
    pairs = pd.read_csv(P / "demand_pairs.csv")
    both = pd.concat([pairs, pairs.rename(columns={"a": "b", "b": "a", "city_a": "city_b", "city_b": "city_a",
                                                    "pop_a": "pop_b", "pop_b": "pop_a"})])
    both = both.set_index(["a", "b"])
    dest = pd.read_csv(P / "destinations.csv")
    dest["to"] = dest["to"].where(~dest["to"].isin(MOW), "MOW")
    dest = dest.sort_values("direct", ascending=False).drop_duplicates(["from", "to"])
    dest = dest[dest.in_ssj]
    ll = pd.read_csv(ROOT / "context/07_verification/terra_cities_review/corrected_cities.csv").set_index("iata")
    spokes = []
    for r in dest.itertuples():
        if (r._1, r.to) not in both.index:
            continue
        p = both.loc[(r._1, r.to)]
        best = p.observed if pd.notna(p.observed) and p.observed_coverage != "airline_group" else p.pax_base
        spokes.append({"hub": r._1, "hub_city": ll.loc[r._1, "city"], "to": r.to, "to_city": p.city_b,
                       "km": int(p.km), "direct_now": bool(r.direct), "status": r.status,
                       "pax_cautious": int(p.pax_cautious), "pax_base": int(p.pax_base),
                       "pax_optimistic": int(p.pax_optimistic), "pax_best": int(best), "method": p.method,
                       "source": p.observed_source if pd.notna(p.observed_source) else "модель тяготения (src/demand_model.py)"})
    sp = pd.DataFrame(spokes)
    sp.to_csv(P / "demand_spokes.csv", index=False, encoding="utf-8")
    rows = []
    for hub, g in sp.groupby("hub"):
        closed = g[g.status == "closed"]
        gap = g[~g.direct_now & (g.status != "closed")].sort_values("pax_base", ascending=False)
        rows.append({"hub": hub, "city": g.hub_city.iloc[0], "spokes_in_ssj": len(g),
                     "pax_all_base": int(g[g.status != "closed"].pax_best.sum()),
                     "pax_no_direct_base": int(gap.pax_base.sum()),
                     "pax_no_direct_cautious": int(gap.pax_cautious.sum()),
                     "no_direct_spokes": len(gap),
                     "pax_closed_airports_base": int(closed.pax_base.sum()),
                     "top_no_direct": "; ".join(f"{r.to_city} {r.pax_base/1000:.0f} тыс." for r in gap.head(5).itertuples())})
    out = pd.DataFrame(rows).sort_values("pax_no_direct_base", ascending=False)
    out.to_csv(P / "demand_by_candidate.csv", index=False, encoding="utf-8")
    # подключаемый критерий лонглиста (появится на пульте весов сам, вес 0 — решает команда)
    crit = out[["hub", "pax_no_direct_base"]].rename(columns={"hub": "iata", "pax_no_direct_base": "value"})
    crit["source"] = "Модель спроса: оценка рынка пар с городами зоны SSJ, куда нет прямого рейса"
    crit = crit.assign(label="Спрос без прямых рейсов (оценка модели)", short="Спрос без рейса", direction="+",
                       weight=0, fmt="mln", board=0,
                       why="оценка масштаба рынка пар, где прямого рейса нет; модель обучена на сегментах, поэтому это не измеренный спрос (аудит критика)")
    (ROOT / "data" / "criteria").mkdir(parents=True, exist_ok=True)
    crit.to_csv(ROOT / "data" / "criteria" / "demand_gap.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(out[["city", "pax_all_base", "pax_no_direct_base", "pax_no_direct_cautious", "pax_closed_airports_base", "top_no_direct"]].to_string(index=False))


if __name__ == "__main__":
    main()
