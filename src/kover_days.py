"""Считает дни с ограничениями («Ковёр») по аэропортам из постов Росавиации.

Вход: data/raw/favt_posts.csv (src/fetch_kover.py).
Метод (как у Meduza 03.07.2026, «дни с ограничениями по данным Росавиации»):
  Статус определяется для каждого аэропорта поста отдельно (airport_events): в одном посте бывают
  снятие для одного аэропорта и введение для другого (аудит критика команды, 09.11.2026).
  Текст поста — только основной, без цитаты (src/fetch_telegram.py, парсер версии 2).
  день = календарный день по Москве; день засчитывается аэропорту, если в этот день Росавиация
  выпустила о нём типовое сообщение: «введены ограничения на прием и выпуск ВС»,
  «принимает и отправляет рейсы по согласованию» или «СНЯТЫ ограничения на прием и выпуск»
  (ограничения действовали в этот день — обычно с ночи). Так совпадает с Meduza: H1 2026
  Сочи 69 (Meduza 70), Казань 51 (51), Калининград 1 (1). Только дни с введением — колонки *_intro
  (нижняя граница).
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

# IATA → как аэропорт пишут в постах. Ручные названия (аэропорт, второй город) —
# data/manual/kover_aliases.csv; для всех остальных аэропортов зон тяготения (src/longlist_data.py)
# добавляется главный город зоны. Раньше список был зашит в код на 28 аэропортов, и в модели сети
# остальные аэропорты получали 0 дней «Ковра».
SKIP_CITY = {"москва", "балашиха", "одинцово", "подольск"}  # аэропорты Москвы — только по названию аэропорта


def load_names():
    names = {}
    al = pd.read_csv(ROOT / "data/manual/kover_aliases.csv")
    for r in al.itertuples():
        names[r.iata] = [x.strip() for x in r.aliases.split(";") if x.strip()]
    cat = ROOT / "data/processed/catchments.csv"
    if cat.exists():
        for r in pd.read_csv(cat).itertuples():
            city = str(r.main_city).lower()
            if r.iata in names or city in SKIP_CITY:
                continue
            names[r.iata] = [city]
    return names


NAMES = load_names()
# только типовые сообщения об аэропорте: «ограничения на прием и выпуск ВС» / «по согласованию»
# (без этого в счёт попадают посты о погоде, обходных трассах, рейсах из-за рубежа)
# + сводные посты «не принимают и не отправляют рейсы N аэропортов: ...»
AIRPORT_MSG = re.compile(r"при[её]м[а-я]*\s+и\s+выпуск|по\s+согласованию|"
                         r"не\s+принима[а-я]*\s+и\s+не\s+отправля", re.I)
LIFTED = re.compile(r"сняты|снято|отменены|возобновил|штатном режиме", re.I)
# статус для каждого аэропорта поста отдельно: в одном посте бывает «Внуково — сняты, Нижний — введены»
LIFT_KW = re.compile(r"сняты|снято|сняли|отменены|возобновил\w*|штатном\s+режиме", re.I)
INTRO_KW = re.compile(r"введен\w*|введён\w*|ввели|по\s+согласованию|не\s+принима\w*\s+и\s+не\s+отправля", re.I)

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
            if re.search(r"(?<![а-я])" + re.escape(k) + r"(?![а-я])", low):
                hits.add(iata)
                break
    return hits


def airport_positions(text):
    """[(позиция, IATA)] — где в тексте упомянут аэропорт."""
    low = text.lower().replace("ё", "е")
    out = []
    for iata, keys in NAMES.items():
        for k in keys:
            k = k.replace("ё", "е")
            if k == "гагарин" and "саратов" not in low:
                continue
            m = re.search(r"(?<![а-я])" + re.escape(k) + r"(?![а-я])", low)
            if m:
                out.append((m.start(), iata))
                break
    return sorted(out)


def airport_events(text):
    """{IATA: 'intro' | 'lift'} — статус для каждого аэропорта поста.

    1. Своя пометка: слово-статус между названием аэропорта и следующим аэропортом на той же строке
       («САМАРА (Курумоч) ограничения сняты около 06:00» относится только к Самаре).
    2. Иначе — первое слово-статус после названия, кроме чужих личных пометок: так общий статус
       списка («— НИЖНИЙ НОВГОРОД / — САМАРА … сняты / — ЧЕБОКСАРЫ / ВВЕДЕНЫ») достаётся Нижнему
       и Чебоксарам (пост 6495 от 25.07.2026, замечание аудита коллег).
    3. Если после названия статуса нет (сводки «не принимают рейсы аэропорты: …»), — ближайший до него."""
    kws = sorted([(m.start(), "lift") for m in LIFT_KW.finditer(text)] +
                 [(m.start(), "intro") for m in INTRO_KW.finditer(text)])
    aps = airport_positions(text)
    line = lambda pos: text.count(chr(10), 0, pos)  # номер строки поста
    own, personal = {}, set()
    for n, (pos, iata) in enumerate(aps):
        nxt = aps[n + 1][0] if n + 1 < len(aps) else len(text)
        mine = [k for k in kws if pos < k[0] < nxt and line(k[0]) == line(pos)]
        if mine:
            own[iata] = mine[0][1]
            alone = not any(line(p2) == line(pos) for p2, i2 in aps if i2 != iata)
            if alone:
                personal.add(mine[0][0])
    ev = {}
    for pos, iata in aps:
        if iata in own:
            ev[iata] = own[iata]
            continue
        after = [k for k in kws if k[0] > pos and k[0] not in personal]
        before = [k for k in kws if k[0] < pos and k[0] not in personal]
        st = after[0][1] if after else (before[-1][1] if before else None)
        if st:
            ev[iata] = st
    return ev


def main():
    p = pd.read_csv(IN)
    p["day"] = pd.to_datetime(p.dt_msk.str[:10])
    p["text"] = p.text.fillna("")
    p["airport_msg"] = p.text.str.contains(AIRPORT_MSG)
    p = p[p.airport_msg]  # только типовые посты: «прием и выпуск», «по согласованию», сводки
    rec = []
    for r in p.itertuples():
        for iata, st in airport_events(r.text).items():
            rec.append((iata, r.day, st == "intro", st == "lift"))
    e = pd.DataFrame(rec, columns=["iata", "day", "intro", "lift"])
    # события по дням — их же читает панель (тепловая карта по месяцам), чтобы метод был один
    ev = e.groupby(["iata", "day"]).agg(intro=("intro", "max"), lift=("lift", "max")).reset_index()
    ev["day"] = ev.day.dt.strftime("%Y-%m-%d")
    ev.to_csv(OUT.parent / "kover_events.csv", index=False, encoding="utf-8")
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
            row[f"{name}_days"] = xi.day.nunique() if covered else None
            row[f"{name}_days_intro"] = xi[xi.intro].day.nunique() if covered else None
        out.append(row)
    df = pd.DataFrame(out)
    df["source"] = (f"Росавиация, t.me/s/favt_info, посты {first:%d.%m.%Y}–{last:%d.%m.%Y}; "
                    "метод: число календарных дней (МСК) с типовым постом о введении или снятии ограничений")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"посты: {len(p)}, с {first:%d.%m.%Y} по {last:%d.%m.%Y}")
    print(df.drop(columns="source").to_string())


if __name__ == "__main__":
    main()
