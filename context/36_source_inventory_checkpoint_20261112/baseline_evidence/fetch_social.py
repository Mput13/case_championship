"""Скачивает открытые социально-экономические наборы (их нашли агенты коллег, context/16_agent_research/core).

- Росстат: численность населения по муниципальным образованиям на 01.01.2025 (Chisl_MO_01-01-2025.xlsx).
  Сайт Росстата закрыт от программ, поэтому берём копию файла в Internet Archive (коллекция rosstat-november-2025).
  Это зеркало: SHA-256 файла пишется в журнал, сверку с сайтом Росстата делает человек.
- «Если быть точным»: населённые пункты России (перепись 2021, координаты, все размеры), v20240326, CC BY 4.0.
- «Если быть точным» / Росстат БДМО: средняя зарплата и среднегодовое население по муниципалитетам, v20260928.
- «Если быть точным» / Росстат «Регионы России»: туризм (06) и уровень жизни (03), v20260313.

Выход: data/raw/social/ (zip распакованы в одноимённые папки), data/raw/social/_sha256.csv
Запуск: python src/fetch_social.py
"""
import csv
import hashlib
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "social"
UA = "Mozilla/5.0 (case-champ research script)"
T = "https://storage.yandexcloud.net/tochno-st-catalog/Rosstat/"
FILES = {
    "rosstat_mo_2025.xlsx": "https://archive.org/download/rosstat-november-2025/%D0%A1hisl_MO_01-01-2025.xlsx",
    "tochno_settlements.zip": T + "data_settlements_115_v20240326/data_settlements_115_v20240326_csv.zip",
    "bdmo_wages.zip": T + "data_bdmo_118_v20260928/indicators/section41/data_Y48213002_112_v20260928.zip",
    "bdmo_population.zip": T + "data_bdmo_118_v20260928/indicators/section41/data_Y48112013_112_v20260928.zip",
    "regions_tourism.zip": T + "data_regions_collection_102_v20260313/data_06_socio_economic_102_v20260313.zip",
    "regions_living.zip": T + "data_regions_collection_102_v20260313/data_03_socio_economic_102_v20260313.zip",
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    log = []
    for name, url in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
        (RAW / name).write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        log.append({"file": name, "url": url, "bytes": len(data), "sha256": sha,
                    "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        print("ok", name, len(data))
        if name.endswith(".zip"):
            with zipfile.ZipFile(RAW / name) as z:
                z.extractall(RAW / name[:-4])
                print("   распаковано:", z.namelist()[:6])
    with (RAW / "_sha256.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]))
        w.writeheader()
        w.writerows(log)


if __name__ == "__main__":
    main()
