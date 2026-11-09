"""Собирает «расчётные» критерии лонглиста из открытых справочников.

Вход (скачивает src/fetch_static.py):
  data/raw/ourairports_airports.csv, ourairports_runways.csv  — OurAirports, Public Domain
  data/raw/tochno_intercity/*.csv  — «Если быть точным», транспортная связность 180 городов,
                                     v2026-06-29, CC BY 4.0
  context/07_verification/terra_cities_review/corrected_cities.csv — лонглист команды (20 городов)

Что считает по каждому городу-кандидату:
  catchment_pop      — население городов >100 тыс. из списка «Точно» в радиусе 75 км от аэропорта
                       (перепись 2021; это нижняя граница зоны тяготения)
  runway_m           — самая длинная полоса аэропорта
  dist_msk_km, dist_ekb_km — по прямой до Шереметьево / Кольцово
  ssj_reach_airports, ssj_reach_pop — сколько аэропортов (и сколько людей вокруг них) SSJ достаёт
                       «зелёным» (≤2300 км, на юг и на запад ≤2150 км, docs/17)
  direct_now         — сколько из этих аэропортов уже связаны с городом прямым рейсом
                       (фактические маршруты июнь–декабрь 2026 по Aviastats + субсидии Росавиации,
                       как их собрал «Точно»)
  gap_pop            — сколько людей живёт у аэропортов в зоне SSJ, куда из города нет прямого рейса
                       и нет поезда быстрее 12 часов. Это «недообслуженный» спрос, который мог бы
                       забрать хаб.

Выход: data/processed/longlist_computed.csv
Запуск: python src/longlist_data.py
"""
import re
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "longlist_computed.csv"
CITIES = ROOT / "context" / "07_verification" / "terra_cities_review" / "corrected_cities.csv"
TOCHNO = RAW / "tochno_intercity" / "data_intercity_connectivity_162_v20260629.csv"

GREEN = 2300          # SSJ, км по прямой, обычные трассы (k=1,10)
GREEN_SOUTH = 2150    # SSJ, юг и западные границы (k=1,20), docs/17
RAIL_OK_HR = 12       # поезд «нормальный», если ехать не дольше ночи
CATCH_KM = 75         # радиус зоны тяготения аэропорта (так же делает «Точно»)

# Регионы, полёты в/из которых идут с обходами (docs/17, раздел 4)
SOUTH_WEST = {
    "Краснодарский край", "Республика Адыгея", "Ставропольский край", "Ростовская область",
    "Республика Дагестан", "Чеченская Республика", "Республика Ингушетия",
    "Кабардино-Балкарская Республика", "Карачаево-Черкесская Республика",
    "Республика Северная Осетия — Алания", "Республика Калмыкия", "Астраханская область",
    "Волгоградская область", "Республика Крым", "Севастополь", "Калининградская область",
    "Белгородская область", "Курская область", "Брянская область",
}


def hav(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(radians, (la1, lo1, la2, lo2))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def main():
    ap = pd.read_csv(RAW / "ourairports_airports.csv", keep_default_na=False)
    ap = ap[(ap.iso_country == "RU") & ap.type.isin(["large_airport", "medium_airport"])
            & (ap.iata_code != "")]
    ap = ap[["ident", "iata_code", "name", "type", "latitude_deg", "longitude_deg", "scheduled_service"]]
    rw = pd.read_csv(RAW / "ourairports_runways.csv", keep_default_na=False)
    rw["len_m"] = pd.to_numeric(rw.length_ft, errors="coerce") * 0.3048
    runway = rw.groupby("airport_ident").len_m.max()

    t = pd.read_csv(TOCHNO, sep=";")
    city = (t.drop_duplicates("city_from")[["city_from", "region_from", "population_from",
                                            "lat_from", "lon_from"]]
            .rename(columns=lambda c: c.replace("_from", "")))

    # каждому городу из 180 — ближайший аэропорт с регулярными рейсами в пределах 75 км
    # (если в радиусе несколько — берём крупный аэропорт: Емельяново, а не Черемшанку)
    apx = ap[ap.scheduled_service == "yes"].copy()
    apx["rank"] = (apx.type != "large_airport").astype(int)
    near = []
    for c in city.itertuples():
        dd = apx.apply(lambda a: hav(c.lat, c.lon, a.latitude_deg, a.longitude_deg), axis=1)
        ok = apx[dd <= CATCH_KM].assign(km=dd[dd <= CATCH_KM]).sort_values(["rank", "km"])
        if len(ok):
            near.append((c.city, ok.iloc[0].iata_code))
    city = city.merge(pd.DataFrame(near, columns=["city", "iata"]), on="city", how="left")
    catch = (city.dropna(subset=["iata"]).groupby("iata")
             .agg(pop=("population", "sum"), main_city=("city", "first"),
                  region=("region", "first")))
    # главный город зоны — самый крупный
    main = city.dropna(subset=["iata"]).sort_values("population", ascending=False) \
               .drop_duplicates("iata").set_index("iata")
    catch["main_city"] = main.city
    catch["region"] = main.region
    catch = catch.join(ap.set_index("iata_code")[["latitude_deg", "longitude_deg", "ident"]])

    # прямые рейсы: пары аэропортов из комментария «UFA — IKT»
    air = t[(t.transport_type == "air") & t.distance_km.notna()]
    direct = set()
    for cm in air.comment.dropna():
        m = re.match(r"\s*([A-Z0-9]{3})\s*—\s*([A-Z0-9]{3})", cm)
        if m:
            direct.add((m.group(1), m.group(2)))
            direct.add((m.group(2), m.group(1)))
    rail = t[t.transport_type == "rail"].set_index(["city_from", "city_to"]).distance_hr

    cand = pd.read_csv(CITIES)
    svo = ap.set_index("iata_code").loc["SVO"]
    svx = ap.set_index("iata_code").loc["SVX"]
    rows = []
    for c in cand.itertuples():
        i = c.iata
        if i not in catch.index:
            print("нет зоны тяготения для", i)
            continue
        a = catch.loc[i]
        reach_n = reach_pop = direct_n = gap_pop = 0
        for j, b in catch.iterrows():
            if j == i:
                continue
            km = hav(a.latitude_deg, a.longitude_deg, b.latitude_deg, b.longitude_deg)
            lim = GREEN_SOUTH if (a.region in SOUTH_WEST or b.region in SOUTH_WEST) else GREEN
            if km > lim:
                continue
            reach_n += 1
            reach_pop += b["pop"]
            has_direct = (i, j) in direct
            direct_n += has_direct
            hr = rail.get((a.main_city, b.main_city))
            rail_ok = hr is not None and pd.notna(hr) and hr <= RAIL_OK_HR
            if not has_direct and not rail_ok:
                gap_pop += b["pop"]
        rows.append({
            "city": c.city, "iata": i, "icao": a.ident, "region": a.region,
            "catchment_pop": int(a["pop"]),
            "runway_m": round(runway.get(a.ident, float("nan"))),
            "dist_msk_km": round(hav(a.latitude_deg, a.longitude_deg, svo.latitude_deg, svo.longitude_deg)),
            "dist_ekb_km": round(hav(a.latitude_deg, a.longitude_deg, svx.latitude_deg, svx.longitude_deg)),
            "ssj_reach_airports": reach_n, "ssj_reach_pop": int(reach_pop),
            "direct_now": direct_n, "gap_pop": int(gap_pop),
            "source": "OurAirports (координаты, ВПП); «Если быть точным», транспортная связность "
                      "v2026-06-29, CC BY 4.0 (население ВПН-2021, поезд, прямые рейсы июнь–дек 2026); "
                      "пороги дальности docs/17",
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(df.drop(columns="source").to_string())


if __name__ == "__main__":
    main()
