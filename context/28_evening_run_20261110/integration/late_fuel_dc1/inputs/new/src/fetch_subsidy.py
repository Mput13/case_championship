"""Перечень субсидируемых региональных маршрутов Росавиации на 2026 год → таблица.

Страница: https://favt.gov.ru/dejatelnost-vozdushnye-perevozki-subsidirovanie-regiony/
Каждая строка: перевозчик, аэропорт отправления и назначения, км, тип ВС, кресла, период,
частота в неделю, число парных рейсов (туда-обратно) в 2026 году.
Номер п/п объединён на несколько строк (rowspan) — такие строки дописываются к маршруту.

Провозная ёмкость пары за год (оба направления) = 2 × парные рейсы × кресла.
Это предложение кресел, а не спрос: пассажиров получаем умножением на загрузку (допущение
в data/assumptions/demand.csv), и используем как ориентир для калибровки модели спроса.

Выход: data/raw/favt_subsidy_2026.csv
Запуск: python src/fetch_subsidy.py
"""
import csv
import html
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://favt.gov.ru/dejatelnost-vozdushnye-perevozki-subsidirovanie-regiony/"
OUT = ROOT / "data" / "raw" / "favt_subsidy_2026.csv"
FIELDS = ["route_no", "airline", "origin", "destination", "km", "aircraft", "seats", "period",
          "flights_per_week", "round_trips_2026", "note"]


def clean(c):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())


def num(s):
    s = s.replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (case-champ research script)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        page = r.read().decode("utf-8", "replace")
    table = max(re.findall(r"<table.*?</table>", page, re.S), key=len)
    rows, last_no = [], ""
    for tr in re.findall(r"<tr.*?</tr>", table, re.S)[1:]:
        cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) == 11:
            last_no = cells[0]
            cells = cells[1:]
        if len(cells) != 10:
            continue
        rows.append(dict(zip(FIELDS, [last_no, *cells])))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    seats = sum((num(r["seats"]) or 0) * (num(r["round_trips_2026"]) or 0) * 2 for r in rows)
    print(f"строк {len(rows)}, маршрутов {len({r['route_no'] for r in rows})}, "
          f"кресел за 2026 в обе стороны ≈ {seats/1e6:.2f} млн → {OUT}")


if __name__ == "__main__":
    main()
