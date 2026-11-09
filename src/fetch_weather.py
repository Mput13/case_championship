"""Погода в аэропортах: часовые наблюдения NOAA ISD-Lite за 2023–2024 годы (публичный архив NOAA на AWS).

Источник нашли агенты коллег (context/16_agent_research/alternative, модуль weather). NOAA сообщила,
что обновление ISD остановлено после 24.08.2025, поэтому берём два последних полных года.
Станции выбираются по ICAO аэропортов из data/processed/catchments.csv (src/longlist_data.py).

Выход: data/raw/weather/isd-history.csv, data/raw/weather/<USAF>-<WBAN>-<год>.gz, data/raw/weather/_files.csv
Запуск: python src/fetch_weather.py
"""
import csv
import gzip
import hashlib
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "weather"
BASE = "https://noaa-isd-pds.s3.amazonaws.com/"
YEARS = (2023, 2024)
UA = "Mozilla/5.0 (case-champ research script)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    hist = RAW / "isd-history.csv"
    hist.write_bytes(get(BASE + "isd-history.csv"))
    h = pd.read_csv(hist, dtype=str)
    cat = pd.read_csv(ROOT / "data/processed/catchments.csv").dropna(subset=["ident"])
    h = h[h.CTRY.isin(["RS", "RU"]) & (h.BEGIN <= f"{min(YEARS)}0101") & (h.END >= f"{max(YEARS)}0101")].copy()
    h["lat"], h["lon"] = pd.to_numeric(h.LAT, errors="coerce"), pd.to_numeric(h.LON, errors="coerce")
    # кандидаты для аэропорта: станция с его ICAO и все станции не дальше 25 км (у части станций нет ICAO);
    # обработка (src/catchment_extra.py) берёт станцию с самым полным рядом
    import numpy as np
    picks = []
    for a in cat.itertuples():
        la1, lo1 = np.radians(a.latitude_deg), np.radians(a.longitude_deg)
        la2, lo2 = np.radians(h.lat.values), np.radians(h.lon.values)
        d = 2 * 6371 * np.arcsin(np.sqrt(np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2))
        m = (h.ICAO.values == a.ident) | (np.nan_to_num(d, nan=1e9) <= 25)
        for (_, r), dist in zip(h[m].iterrows(), d[m]):
            r = r.copy()
            r["ICAO"] = a.ident
            r["STATION NAME"] = f"{r['STATION NAME']} ({dist:.0f} км)"
            picks.append(r)
    st = pd.DataFrame(picks)
    log = []
    for r in st.itertuples():
        for y in YEARS:
            name = f"{r.USAF}-{r.WBAN}-{y}.gz"
            try:
                data = get(f"{BASE}isd-lite/data/{y}/{name}")
                gzip.decompress(data)          # архив целый
                (RAW / name).write_bytes(data)
                log.append({"icao": r.ICAO, "station": getattr(r, "_3"), "usaf": r.USAF, "wban": r.WBAN, "year": y, "file": name,
                            "sha256": hashlib.sha256(data).hexdigest(), "status": "ok"})
            except Exception as e:  # noqa: BLE001 — сбой одной станции не останавливает остальные
                log.append({"icao": r.ICAO, "station": getattr(r, "_3"), "usaf": r.USAF, "wban": r.WBAN, "year": y, "file": name,
                            "sha256": "", "status": f"ошибка: {e}"})
    with (RAW / "_files.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]))
        w.writeheader()
        w.writerows(log)
    ok = sum(x["status"] == "ok" for x in log)
    print(f"станций {len(st)} из {len(cat)} аэропортов, файлов {ok} из {len(log)}")


if __name__ == "__main__":
    main()
