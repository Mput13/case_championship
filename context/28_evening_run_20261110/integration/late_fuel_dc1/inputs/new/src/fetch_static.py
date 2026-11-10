"""Скачивает открытые справочники, которые не требуют ключей.

- OurAirports airports.csv, runways.csv — координаты и полосы (Public Domain).
- «Если быть точным»: транспортная связность 180 городов, v2026-06-29 (CC BY 4.0) —
  время в пути авто / поезд / самолёт между парами городов.

Запуск: python src/fetch_static.py
"""
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = "Mozilla/5.0 (case-champ research script)"

FILES = {
    "ourairports_airports.csv": "https://davidmegginson.github.io/ourairports-data/airports.csv",
    "ourairports_runways.csv": "https://davidmegginson.github.io/ourairports-data/runways.csv",
    "tochno_intercity_csv.zip": "https://storage.yandexcloud.net/tochno-st-catalog/Geo/"
        "data_intercity_connectivity_162_v20260629/data_intercity_connectivity_162_v20260629_csv.zip",
    "tochno_intercity_description.pdf": "https://storage.yandexcloud.net/tochno-st-catalog/Geo/"
        "data_intercity_connectivity_162_v20260629/description_intercity_connectivity_162_v20260629.pdf",
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / name).write_bytes(r.read())
        print("ok", name, (RAW / name).stat().st_size)
    with zipfile.ZipFile(RAW / "tochno_intercity_csv.zip") as z:
        z.extractall(RAW / "tochno_intercity")
        print("распаковано:", z.namelist())


if __name__ == "__main__":
    main()
