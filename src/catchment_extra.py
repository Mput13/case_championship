"""Новые признаки аэропортов из наборов, которые нашли коллеги: население всех населённых пунктов,
оценка населения на 2025 год, зарплата, погода.

Вход:
  data/raw/social/  (src/fetch_social.py), data/raw/weather/ (src/fetch_weather.py),
  data/processed/catchments.csv (src/longlist_data.py), data/raw/ourairports_airports.csv,
  data/assumptions/longlist_params.csv, data/assumptions/weather.csv
Метод:
  1. Зона тяготения: каждый населённый пункт (перепись 2021, «Если быть точным», все размеры)
     относится к ближайшему аэропорту с регулярными рейсами не дальше catchment_km.
     У 11% населения в наборе нет координат — им ставим координаты своего муниципалитета
     (среднее по населённым пунктам того же муниципалитета с координатами) [синтетика, доля помечена].
  2. Население на 01.01.2025: перепись 2021 × (население муниципалитета 2025 по Росстату /
     население муниципалитета по переписи). Муниципалитет — первые 8 знаков ОКТМО, у Росстата код
     ТЕРСОН-МО = ОКТМО + «00». Если муниципалитет не нашёлся (реформы 2021–2025) — коэффициент региона
     [синтетика, доля помечена].
  3. Зарплата: средняя начисленная зарплата 2024 года (январь–декабрь, крупные и средние предприятия)
     по муниципалитетам верхнего уровня (Росстат БДМО), средняя по зоне с весом населения.
  4. Погода 2023–2024 (NOAA ISD-Lite): среднее за год число дней, когда хотя бы в одном наблюдении
     мороз сильнее порога или ветер не слабее порога (пороги — data/assumptions/weather.csv, исследовательские).
Выход: data/processed/catchment_extra.csv
Запуск: python src/catchment_extra.py
"""
import gzip
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

import rules

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
P = ROOT / "data" / "processed"
PAR = pd.read_csv(ROOT / "data/assumptions/longlist_params.csv").set_index("parameter").value
WPAR = pd.read_csv(ROOT / "data/assumptions/weather.csv").set_index("parameter").value


def hav_np(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(np.radians, (la1, lo1, la2, lo2))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))


def settlements():
    s = pd.read_csv(RAW / "social/tochno_settlements/data_settlements_115_v20240326.csv", sep=";",
                    low_memory=False, dtype={"oktmo": str, "terson": str})
    s = s[s.pop_total.notna() & (s.pop_total > 0)].copy()
    s["mo8"] = s.oktmo.str.zfill(11).str[:8]
    s["coord_imputed"] = s.geo_lat.isna()
    cen = s[~s.coord_imputed].groupby("mo8")[["geo_lat", "geo_lon"]].mean()
    s.loc[s.coord_imputed, "geo_lat"] = s.loc[s.coord_imputed, "mo8"].map(cen.geo_lat)
    s.loc[s.coord_imputed, "geo_lon"] = s.loc[s.coord_imputed, "mo8"].map(cen.geo_lon)
    return s


def factor_2025(s):
    """Коэффициент 2025 / перепись: муниципалитет, иначе регион."""
    r = pd.read_excel(RAW / "social/rosstat_mo_2025.xlsx", sheet_name="Численность_по_МО", header=None, dtype={0: str})
    r = r[r[0].astype(str).str.fullmatch(r"\d{10}")].copy()
    r["pop25"] = pd.to_numeric(r[2], errors="coerce")
    mo = r.groupby(r[0].str[:8]).pop25.first()
    rr = r[r[0].str.endswith("00000000")]                                    # строки субъектов
    reg = rr.groupby(rr[0].str[:2]).pop25.max()   # у области с автономным округом берём строку всей области
    s21_mo = s.groupby("mo8").pop_total.sum()
    s["reg2"] = s.mo8.str[:2]
    s21_reg = s.groupby("reg2").pop_total.sum()
    f_mo = (mo / s21_mo).dropna()
    f_mo = f_mo[(f_mo > 0.5) & (f_mo < 2)]          # грубые несовпадения границ отбрасываем
    f_reg = (reg / s21_reg).dropna()
    s["f25"] = s.mo8.map(f_mo)
    s["f25_method"] = np.where(s.f25.notna(), "муниципалитет", "регион")
    s["f25"] = s.f25.fillna(s.reg2.map(f_reg)).fillna(1.0)
    s.loc[s.f25_method.eq("регион") & ~s.reg2.isin(f_reg.index), "f25_method"] = "нет данных (×1)"
    return s


def wages():
    w = pd.read_csv(RAW / "social/bdmo_wages/data_Y48213002_112_v20260928.csv", sep=";", low_memory=False,
                    dtype={"oktmo": str})
    w = w[(w.year == 2024) & (w.indicator_period == "Январь-декабрь") &
          (w.mun_level == "Муниципальное образование верхнего уровня")]
    w["mo8"] = w.oktmo.str.zfill(8)
    return w.groupby("mo8").indicator_value.mean()


def weather_counts(rows, t_lim, w_lim):
    """Valid daily denominators; all-sentinel day is UNKNOWN.

    Combined event needs at least one valid t and w on that day. This does not
    establish complete hourly coverage or aircraft operating limits.
    """
    d = pd.DataFrame(rows, columns=['day','t','w'])
    if d.empty:
        return dict(frost=0, wind=0, either=0, valid_temp_days=0, valid_wind_days=0,
                    valid_joint_days=0, record_days=0, observations=0)
    d['valid_t'] = d.t.notna() & d.t.ne(-9999)
    d['valid_w'] = d.w.notna() & d.w.ne(-9999)
    d['frost'] = d.valid_t & (d.t/10 <= t_lim)
    d['wind'] = d.valid_w & (d.w/10 >= w_lim)
    g = d.groupby('day')[['valid_t','valid_w','frost','wind']].any()
    joint = g.valid_t & g.valid_w
    return dict(frost=int(g.frost.sum()), wind=int(g.wind.sum()),
                either=int(((g.frost | g.wind) & joint).sum()),
                valid_temp_days=int(g.valid_t.sum()), valid_wind_days=int(g.valid_w.sum()),
                valid_joint_days=int(joint.sum()), record_days=len(g), observations=len(d))


def weather():
    """Select station by valid joint days, never count sentinel rows as fair weather."""
    files = pd.read_csv(RAW / 'weather/_files.csv')
    files = files[files.status == 'ok']
    t_lim, w_lim = float(WPAR['frost_c']), float(WPAR['wind_ms'])
    min_days = float(WPAR['min_observed_days'])
    cache, out = {}, {}
    for icao, g in files.groupby('icao'):
        best = None
        for st, gs in g.groupby('station'):
            total = None
            for f in gs.file:
                path = RAW/'weather'/f
                if not path.exists():
                    continue
                if f not in cache:
                    rows = []
                    with gzip.open(path, 'rt') as fh:
                        for line in fh:
                            q = line.split()
                            rows.append((f'{int(q[0]):04d}-{int(q[1]):02d}-{int(q[2]):02d}', int(q[4]), int(q[8])))
                    cache[f] = weather_counts(rows,t_lim,w_lim)
                counts = cache[f]
                if total is None: total = {k:0 for k in counts}
                for k,v in counts.items(): total[k] += v
            if total is None: continue
            years = len(gs)
            if best is None or total['valid_joint_days'] > best[1]['valid_joint_days']:
                best = (st,total,years)
        if best is None:
            out[icao] = dict(bad_weather_days=None,weather_status='UNKNOWN_missing_local_archives')
            continue
        st,t,years = best
        def rate(event,denom):
            n=t[denom]
            return round(t[event]/n*365,1) if n and n/years >= min_days else None
        out[icao] = dict(frost_days=rate('frost','valid_temp_days'), wind_days=rate('wind','valid_wind_days'),
            bad_weather_days=rate('either','valid_joint_days'),weather_days_observed=round(t['valid_joint_days']/years),
            weather_station=st,weather_years=years,**t,
            weather_status='valid_daily_fields_only_hourly_coverage_unverified')
    return out


def main():
    cat = pd.read_csv(P / "catchments.csv")
    ap = pd.read_csv(RAW / "ourairports_airports.csv", keep_default_na=False)
    ap = ap[(ap.iso_country == "RU") & ap.type.isin(["large_airport", "medium_airport"]) &
            (ap.iata_code != "") & (ap.scheduled_service == "yes")]
    s = factor_2025(settlements())
    s = s[s.geo_lat.notna()]
    # ближайший аэропорт с регулярными рейсами в пределах радиуса
    D = hav_np(s.geo_lat.values[:, None], s.geo_lon.values[:, None],
               ap.latitude_deg.values[None, :], ap.longitude_deg.values[None, :])
    # как в src/longlist_data.py: если в радиусе есть крупный аэропорт — берём его (Емельяново, а не Черемшанка)
    R = float(PAR["catchment_km"])
    large = (ap.type == "large_airport").values[None, :]
    Dl = np.where(large, D, np.inf)
    jl, ja = Dl.argmin(axis=1), D.argmin(axis=1)
    rows_i = np.arange(len(s))
    use_large = Dl[rows_i, jl] <= R
    j = np.where(use_large, jl, ja)
    s["iata"] = np.where(D[rows_i, j] <= R, ap.iata_code.values[j], None)
    s = s[s.iata.notna()].copy()
    s["pop25"] = s.pop_total * s.f25
    wg = wages()
    s["wage"] = s.mo8.map(wg)
    W = weather()
    rows = []
    for i in cat.iata:
        g = s[s.iata == i]
        if not len(g):
            rows.append({"iata": i})
            continue
        ww = g[g.wage.notna()]
        rows.append({
            "iata": i,
            "catchment_pop_all_2021": int(g.pop_total.sum()),
            "catchment_pop_2025": int(g.pop25.sum()),
            "pop_coord_imputed_share": round(g.loc[g.coord_imputed, "pop_total"].sum() / g.pop_total.sum(), 3),
            "pop25_region_factor_share": round(g.loc[g.f25_method != "муниципалитет", "pop_total"].sum() / g.pop_total.sum(), 3),
            "wage_2024": round(float(np.average(ww.wage, weights=ww.pop25))) if len(ww) else None,
            "wage_pop_coverage": round(ww.pop25.sum() / g.pop25.sum(), 3) if len(g) else None,
        } | W.get(cat.set_index("iata").ident.get(i), {}))
    out = pd.DataFrame(rows)
    out["source"] = ("«Если быть точным»: населённые пункты (ВПН-2021) v20240326 и БДМО v20260928 (зарплата 2024); "
                     "Росстат, население МО на 01.01.2025 (копия Internet Archive); NOAA ISD-Lite 2023–2024")
    out.to_csv(P / "catchment_extra.csv", index=False, encoding="utf-8")
    ll = pd.read_csv(rules.CITIES)[["iata", "city"]]
    show = ll.merge(out, on="iata", how="left").merge(cat[["iata", "pop"]], on="iata", how="left")
    pd.set_option("display.width", 250)
    print(show.drop(columns="source").to_string(index=False))


if __name__ == "__main__":
    main()
