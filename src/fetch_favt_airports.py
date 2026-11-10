"""Пассажиропоток аэропортов за 2019 год (до ковида и ограничений) из открытых данных Росавиации.

Набор: «Статистические показатели по объемам перевозок пассажиров через аэропорты России»,
https://favt.gov.ru/opendata/7714549744-statperevaeroportpas/ (обновлялся до декабря 2020).
Часть аэропортов Росавиация скрыла звёздочками (***) — такие значения остаются пустыми.

Выход: data/criteria/pax_2019.csv — подключаемый критерий (см. data/criteria/README.md).
Запуск: python src/fetch_favt_airports.py
"""
import csv
import argparse
import io
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "http://favt.gov.ru/opendata/7714549744-statperevaeroportpas/data-20210201-structure-20181102.csv"
PAGE = "https://favt.gov.ru/opendata/7714549744-statperevaeroportpas/"
OUT = ROOT / "data" / "criteria" / "pax_2019.csv"
RAW = ROOT / "data" / "raw" / "favt_airports_2007_2020.csv"
# как аэропорт назван в наборе Росавиации → код IATA
NAMES = {"Самара(Курумоч)": "KUF", "Уфа": "UFA", "Казань": "KZN", "Нижний Новгород(Стригино)": "GOJ",
         "Пермь(Большое Савино)": "PEE", "Челябинск(Баландино)": "CEK", "Тюмень(Рощино)": "TJM",
         "Омск(Центральный)": "OMS", "Минеральные Воды": "MRV", "Сочи": "AER", "Махачкала(Уйташ)": "MCX",
         "Калининград(Храброво)": "KGD", "Саратов(Гагарин)": "GSV", "Волгоград(Гумрак)": "VOG",
         "Оренбург(Центральный)": "REN", "Красноярск": "KJA", "Иркутск": "IKT", "Владивосток(Кневичи)": "VVO",
         "Хабаровск(Новый)": "KHV", "Барнаул(Имени Г.С.Титова)": "BAX"}
META = {"label": "Пассажиропоток 2019 (до ограничений)", "short": "Пасс. 2019", "direction": "+",
        "weight": "0", "fmt": "mln", "board": "0",
        "why": "размер рынка до ковида и «Ковра»; вес 0, пока команда не решит его учитывать"}


def parse_raw(raw):
    """Replay CP1251 official bytes; Central is a separate historical facility."""
    rows = list(csv.reader(io.StringIO(raw.decode("cp1251")), delimiter=";"))
    found, history = {}, []
    for r in rows[1:]:
        if len(r) > 2 and r[1] == "2019":
            value = r[-1].replace(" ", "").replace("\xa0", "")
            if r[0] == "Саратов(Центральный)":
                history.append(dict(facility="Саратов(Центральный)", historical_iata="",
                                    year="2019", value=value, scope="Central only; not GSV or city annual total",
                                    source=PAGE))
            if r[0] in NAMES:
                found[NAMES[r[0]]] = (r[0], value)
    return found, history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-cache", action="store_true")
    args = ap.parse_args()
    if args.from_cache:
        raw = RAW.read_bytes()
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (case-champ research script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_bytes(raw)
    found, history = parse_raw(raw)
    history_path = ROOT / "data" / "external" / "favt_saratov_central_2019.csv"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["facility", "historical_iata", "year", "value", "scope", "source"])
        w.writeheader()
        w.writerows(history)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["iata", "value", "text", "source", *META])
        w.writeheader()
        for iata in NAMES.values():
            name, v = found.get(iata, ("", ""))
            hidden = v == "***" or v == ""
            w.writerow({"iata": iata, "value": "" if hidden else v,
                        "text": "скрыто Росавиацией" if hidden else "",
                        "source": f"Росавиация, открытые данные, «{name}», 2019: {PAGE}", **META})
    ok = sum(1 for _, v in found.values() if v not in ("***", ""))
    print(f"pax_2019: {ok} из {len(NAMES)} аэропортов с цифрой → {OUT}")


if __name__ == "__main__":
    main()
