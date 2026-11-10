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

Выход: data/processed/longlist_computed.csv,
       data/processed/destinations.csv — по каждому кандидату: аэропорты в зоне SSJ и все текущие
       прямые рейсы, статус direct / rail (поезд ≤ 12 ч) / gap (ни того, ни другого)
Запуск: python src/longlist_data.py
"""
import re
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import pandas as pd

import rules

from airports_meta import CLOSED, NAME

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "longlist_computed.csv"
CITIES = ROOT / "context" / "07_verification" / "terra_cities_review" / "corrected_cities.csv"
TOCHNO = RAW / "tochno_intercity" / "data_intercity_connectivity_162_v20260629.csv"

from rules import GREEN, GREEN_SOUTH, SOUTH_WEST  # пороги и регионы — data/assumptions/range.csv, south_west_regions.csv
_PAR = pd.read_csv(ROOT / "data/assumptions/longlist_params.csv").set_index("parameter").value
RAIL_OK_HR = float(_PAR["rail_ok_hr"])      # поезд «нормальный», если ехать не дольше ночи
CATCH_KM = float(_PAR["catchment_km"])      # радиус зоны тяготения аэропорта


# аэропорты одного города считаем одним рынком: житель Подмосковья летит через любой из них
GROUP = {x: "MOW" for x in rules.MOW_AIRPORTS}


def grp(code):
    return GROUP.get(code, code)


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
    # зоны тяготения всех аэропортов — нужны модели спроса по парам (src/demand_model.py)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    catch.rename_axis("iata").to_csv(OUT.parent / "catchments.csv", encoding="utf-8")

    # прямые рейсы: пары аэропортов из комментария «UFA — IKT»
    air = t[(t.transport_type == "air") & t.distance_km.notna()]
    direct = set()
    for cm in air.comment.dropna():
        m = re.match(r"\s*([A-Z0-9]{3})\s*—\s*([A-Z0-9]{3})", cm)
        if m:
            direct.add((grp(m.group(1)), grp(m.group(2))))
            direct.add((grp(m.group(2)), grp(m.group(1))))
    rail = t[t.transport_type == "rail"].set_index(["city_from", "city_to"]).distance_hr

    cand = pd.read_csv(CITIES)
    apx_i = ap.set_index("iata_code")
    mow = [apx_i.loc[x] for x in ("SVO", "DME", "VKO")]   # до Москвы — до ближайшего из трёх аэропортов
    svx = apx_i.loc["SVX"]
    rows = []
    dests = []  # направления для карты: каждый аэропорт в зоне SSJ + все текущие прямые рейсы
    for c in cand.itertuples():
        i = c.iata
        if i not in catch.index:
            print("нет зоны тяготения для", i)
            continue
        a = catch.loc[i]
        reach_n = reach_pop = direct_n = gap_pop = gap_closed = gap_rail_unknown = 0
        for j, b in catch.iterrows():
            if j == i:
                continue
            km = hav(a.latitude_deg, a.longitude_deg, b.latitude_deg, b.longitude_deg)
            lim = GREEN_SOUTH if (a.region in SOUTH_WEST or b.region in SOUTH_WEST) else GREEN
            has_direct = (grp(i), grp(j)) in direct
            hr = rail.get((a.main_city, b.main_city))
            rail_ok = hr is not None and pd.notna(hr) and hr <= RAIL_OK_HR
            if km <= lim or has_direct:
                dests.append({"from": i, "to": j, "to_city": NAME.get(j, b.main_city), "to_region": b.region,
                              "lat": round(b.latitude_deg, 3), "lon": round(b.longitude_deg, 3),
                              "pop": int(b["pop"]), "km": round(km), "in_ssj": km <= lim,
                              "direct": has_direct, "rail_hr": None if hr is None or pd.isna(hr) else round(hr, 1),
                              "status": "closed" if j in CLOSED else "direct" if has_direct else ("rail" if rail_ok else "gap")})
            if km > lim:
                continue
            reach_n += 1
            reach_pop += b["pop"]
            direct_n += has_direct
            if j in CLOSED:  # закрытый аэропорт: сейчас туда не полететь, считаем отдельно
                gap_closed += b["pop"]
            elif not has_direct and not rail_ok:
                gap_pop += b["pop"]
                if hr is None or pd.isna(hr):  # в «Точно» поезд не найден (missing_reason) — не измеренное время
                    gap_rail_unknown += b["pop"]
        rows.append({
            "city": c.city, "iata": i, "icao": a.ident, "region": a.region,
            "catchment_pop": int(a["pop"]),
            "runway_m": round(runway.get(a.ident, float("nan"))),
            "dist_msk_km": round(min(hav(a.latitude_deg, a.longitude_deg, m.latitude_deg, m.longitude_deg) for m in mow)),
            "dist_ekb_km": round(hav(a.latitude_deg, a.longitude_deg, svx.latitude_deg, svx.longitude_deg)),
            "ssj_reach_airports": reach_n, "ssj_reach_pop": int(reach_pop),
            "direct_now": direct_n, "gap_pop": int(gap_pop), "gap_pop_closed": int(gap_closed),
            "gap_pop_rail_unknown": int(gap_rail_unknown),
            "source": "OurAirports (координаты, ВПП); «Если быть точным», транспортная связность "
                      "v2026-06-29, CC BY 4.0 (население ВПН-2021, поезд, прямые рейсы июнь–дек 2026); "
                      "пороги дальности docs/17",
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False, encoding="utf-8")
    pd.DataFrame(dests).to_csv(OUT.parent / "destinations.csv", index=False, encoding="utf-8")
    print(df.drop(columns="source").to_string())


if __name__ == "__main__":
    main()
