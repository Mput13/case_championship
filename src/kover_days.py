"""Считает дни с ограничениями («Ковёр») по аэропортам из постов Росавиации.

Вход: data/raw/favt_posts.csv (src/fetch_kover.py).
Метод (как у Meduza 03.07.2026, «дни с ограничениями по данным Росавиации»):
  день = календарный день по Москве; день засчитывается аэропорту, если в этот день Росавиация
  выпустила типовое сообщение об этом аэропорте: «введены ограничения на прием и выпуск ВС»
  или «принимает и отправляет рейсы по согласованию». Посты о снятии ограничений день
  не добавляют; вариант «с учётом снятия» — колонки *_any.
Проверка: H1 2026 Сочи ≈ 70, Казань ≈ 51, Владивосток/Иркутск/Новосибирск/Хабаровск = 0,
  Калининград = 1 (Meduza).

Выход: data/processed/kover_days.csv
Запуск: python src/kover_days.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "raw" / "favt_posts.csv"
OUT = ROOT / "data" / "processed" / "kover_days.csv"

# IATA → как аэропорт пишут в постах (город или название аэропорта; заглавные/строчные не важны)
NAMES = {
    "KUF": ["самара", "курумоч"], "UFA": ["уфа"], "KZN": ["казань"],
    "GOJ": ["нижний новгород", "стригино"], "PEE": ["пермь", "большое савино"],
    "CEK": ["челябинск", "баландино"], "TJM": ["тюмень", "рощино"], "OMS": ["омск"],
    "MRV": ["минеральные воды", "минводы"], "AER": ["сочи"], "MCX": ["махачкала", "уйташ"],
    "KGD": ["калининград", "храброво"], "GSV": ["саратов", "гагарин"],
    "VOG": ["волгоград", "гумрак"], "REN": ["оренбург"], "KJA": ["красноярск", "емельяново"],
    "IKT": ["иркутск"], "VVO": ["владивосток", "кневичи"], "KHV": ["хабаровск"],
    "BAX": ["барнаул", "михайловка"],
    # для сравнения
    "SVX": ["екатеринбург", "кольцово"], "OVB": ["новосибирск", "толмачево", "толмачёво"],
    "SVO": ["шереметьево"], "DME": ["домодедово"], "VKO": ["внуково"], "LED": ["пулково"],
    "KRR": ["краснодар", "пашковский"], "ROV": ["ростов", "платов"],
}
# только типовые сообщения об аэропорте: «ограничения на прием и выпуск ВС» / «по согласованию»
# (без этого в счёт попадают посты о погоде, обходных трассах, рейсах из-за рубежа)
# + сводные посты «не принимают и не отправляют рейсы N аэропортов: ...»
AIRPORT_MSG = re.compile(r"при[её]м[а-я]*\s+и\s+выпуск|по\s+согласованию|"
                         r"не\s+принима[а-я]*\s+и\s+не\s+отправля", re.I)
LIFTED = re.compile(r"сняты|снято|отменены|возобновил|штатном режиме", re.I)

PERIODS = {
    "h1_2025": ("2025-01-01", "2025-06-30"),
    "h2_2025": ("2025-07-01", "2025-12-31"),
    "h1_2026": ("2026-01-01", "2026-06-30"),
    "jan_oct_2026": ("2026-01-01", "2026-10-31"),
    "last365": None,  # 365 дней до последнего поста
}


def find_airports(text):
    low = text.lower().replace("ё", "е")
    hits = set()
    for iata, keys in NAMES.items():
        for k in keys:
            k = k.replace("ё", "е")
            # «гагарин» встречается и вне Саратова — требуем рядом «саратов» или скобку
            if k == "гагарин" and "саратов" not in low:
                continue
            if re.search(r"(?<![а-я])" + re.escape(k), low):
                hits.add(iata)
                break
    return hits


def main():
    p = pd.read_csv(IN)
    p["day"] = pd.to_datetime(p.dt_msk.str[:10])
    p["text"] = p.text.fillna("")
    p["airport_msg"] = p.text.str.contains(AIRPORT_MSG)
    p["lift"] = p.text.str.contains(LIFTED)
    p["intro"] = p.airport_msg & ~p.lift
    p = p[p.airport_msg]
    rec = []
    for r in p.itertuples():
        for iata in find_airports(r.text):
            rec.append((iata, r.day, r.intro, r.lift))
    e = pd.DataFrame(rec, columns=["iata", "day", "intro", "lift"])
    last = p.day.max()
    first = p.day.min()
    out = []
    for iata in NAMES:
        x = e[e.iata == iata]
        row = {"iata": iata}
        for name, rng in PERIODS.items():
            lo, hi = (last - pd.Timedelta(days=364), last) if rng is None else map(pd.Timestamp, rng)
            covered = first <= lo
            xi = x[(x.day >= lo) & (x.day <= hi)]
            row[f"{name}_days"] = xi[xi.intro].day.nunique() if covered else None
            row[f"{name}_days_any"] = xi.day.nunique() if covered else None
        out.append(row)
    df = pd.DataFrame(out)
    df["source"] = (f"Росавиация, t.me/s/favt_info, посты {first:%d.%m.%Y}–{last:%d.%m.%Y}; "
                    "метод: число календарных дней (МСК) с постом о введении ограничений")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"посты: {len(p)}, с {first:%d.%m.%Y} по {last:%d.%m.%Y}")
    print(df.drop(columns="source").to_string())


if __name__ == "__main__":
    main()
