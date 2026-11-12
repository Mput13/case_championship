"""Собирает лонглист: одна строка на город, все критерии, у каждого — источник.

Вход:
  data/manual/longlist_cities.csv — пассажиропоток 2025 (команда)
  data/processed/longlist_computed.csv — src/longlist_data.py
  data/processed/kover_days.csv        — src/kover_days.py
  data/manual/longlist_manual.csv      — ручные данные со ссылками
Выход:
  data/processed/longlist.csv, outputs/longlist.xlsx (листы longlist и sources)
Запуск: python src/build_longlist.py
"""
from pathlib import Path

import pandas as pd

import rules

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"


FONT = "Arial"  # Calibri запрещён (правило пользователя); openpyxl ставит его по умолчанию


def set_font(path):
    """Меняет шрифт по умолчанию и шрифт всех ячеек, затем проверяет XML на Calibri."""
    import zipfile
    from copy import copy

    from openpyxl import load_workbook
    wb = load_workbook(path)
    normal = next(s for s in wb._named_styles if s.name == "Normal")
    normal.font = copy(normal.font)
    normal.font.name = FONT
    for f in wb._fonts:  # шрифты, уже записанные в styles.xml
        f.name = FONT
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                ft = copy(cell.font)
                ft.name = FONT
                cell.font = ft
        for col in ws.columns:
            dim = ws.column_dimensions[col[0].column_letter]
            if dim.width == 13:
                dim.width = 16
    if wb.loaded_theme:  # тема оформления тоже ссылается на Calibri
        wb.loaded_theme = wb.loaded_theme.replace(b"Calibri Light", FONT.encode()) \
                                         .replace(b"Calibri", FONT.encode())
    wb.save(path)
    with zipfile.ZipFile(path) as z:
        bad = [n for n in z.namelist() if b"Calibri" in z.read(n)]
    if bad:
        raise SystemExit(f"Calibri остался в {bad}")


def main():
    c = pd.read_csv(rules.CITIES)
    c = c[["city", "iata", "pax_2025", "pax_2025_qualifier", "pax_source_url"]].copy()
    # в источнике только «более N» — берём N как нижнюю границу (data/manual/pax_2025_overrides.csv)
    for r in pd.read_csv(ROOT / "data/manual/pax_2025_overrides.csv").itertuples():
        m = (c.iata == r.iata) & c.pax_2025.isna()
        c.loc[m, "pax_2025"] = r.pax_2025
        c.loc[m, "pax_2025_qualifier"] = r.qualifier
    comp = pd.read_csv(P / "longlist_computed.csv").drop(columns=["city", "source"])
    kov = pd.read_csv(P / "kover_days.csv")
    kov_src = kov.source.iloc[0]
    kov = kov[["iata", "h1_2026_days", "jan_oct_2026_days", "last365_days"]]
    man = pd.read_csv(ROOT / "data/manual/longlist_manual.csv").drop(columns=["city"])

    extra = pd.read_csv(P / "catchment_extra.csv").drop(columns=["source"])          # src/catchment_extra.py
    tp = pd.read_csv(P / "transfer_potential.csv")                                   # src/transfer_potential.py
    tech = pd.read_csv(ROOT / "data/manual/airport_tech.csv").drop(columns=["city"])  # ручные сведения со ссылками
    df = c.merge(comp, on="iata", how="left").merge(kov, on="iata", how="left") \
          .merge(man, on="iata", how="left").merge(extra, on="iata", how="left") \
          .merge(tp, on="iata", how="left").merge(tech, on="iata", how="left")
    df.to_csv(P / "longlist.csv", index=False, encoding="utf-8")

    sources = pd.DataFrame([
        ("pax_2025", "Пассажиропоток аэропорта 2025, чел.", "пресс-релизы аэропортов, ссылка в pax_source_url (сверка Terra)"),
        ("catchment_pop", "Население городов >100 тыс. в 75 км от аэропорта (ВПН-2021)", "«Если быть точным», связность городов v2026-06-29, CC BY 4.0"),
        ("runway_m", "Самая длинная ВПП, м", "OurAirports runways.csv"),
        ("dist_msk_km / dist_ekb_km", "По прямой до SVO / SVX, км", "OurAirports, формула гаверсинуса"),
        ("ssj_reach_airports / ssj_reach_pop", "Аэропорты и люди в «зелёной» зоне SSJ", "OurAirports + «Точно»; пороги 2300/2150 км — docs/17"),
        ("direct_now", "Из них уже есть прямой рейс", "«Точно»: маршруты июнь–дек 2026 (Aviastats) и субсидии Росавиации"),
        ("gap_pop", "Люди в зоне SSJ без прямого рейса и без поезда ≤12 ч", "«Точно»: время поездом (СберИндекс), прямые рейсы"),
        ("h1_2026_days / jan_oct_2026_days / last365_days", "Дни с ограничениями («Ковёр»)", kov_src),
        ("strategy_region", "Регион в приоритетах акционеров (Урал, ДФО, СКФО, ЮФО)", "docs/00"),
        ("transfer_zone", "Зона трансфера: 1 есть, 0 нет", "сайты аэропортов, ссылка в transfer_source"),
        ("rostec_link", "Ростех: 2 — завод/ТО по парку RW, 1 — авиапредприятие не по парку", "ссылка в rostec_source"),
        ("base_carriers", "Базовые перевозчики", "ссылка в base_source; доля — после ключа API Яндекс Расписаний"),
        ("utair_mct_min", "Мин. время стыковки у Ютэйр, мин (справочно)", "utair.ru, таблица трансфера багажа"),
        ("catchment_pop_2025", "Население всех населённых пунктов в 75 км, оценка на 01.01.2025", "«Точно»: населённые пункты (ВПН-2021) × коэффициент муниципалитета Росстат 2025 / перепись; src/catchment_extra.py"),
        ("wage_2024", "Средняя начисленная зарплата 2024 в зоне, руб./мес.", "Росстат БДМО через «Если быть точным»; src/catchment_extra.py"),
        ("bad_weather_days", "Дни с морозом ≤ −20 °C или ветром ≥ 12 м/с, в год", "NOAA ISD-Lite 2023–2024; src/catchment_extra.py"),
        ("transfer_demand_base", "Спрос пар без прямого рейса, которые соединяются через город с крюком ≤ 35%", "модель шага 2; src/transfer_potential.py"),
        ("ssj_ops / ssj_mro / h24 / rw_support", "SSJ летает · ТО SSJ · круглосуточно · опорный аэропорт Red Wings", "data/manual/airport_tech.csv, ссылки в колонках *_source"),
    ], columns=["column", "meaning", "source"])

    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    xlsx = out / "longlist.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="longlist", index=False)
        # Literal qualifier equals sign is text, never an empty Excel formula.
        for col_index, column in enumerate(df.columns, 1):
            for row_index, value in enumerate(df[column], 2):
                if isinstance(value, str) and value == "=":
                    xw.book["longlist"].cell(row_index, col_index).data_type = "s"
        sources.to_excel(xw, sheet_name="sources", index=False)
    set_font(xlsx)
    print(df[["city", "pax_2025", "catchment_pop", "ssj_reach_pop", "direct_now", "gap_pop",
              "h1_2026_days", "last365_days", "transfer_zone", "rostec_link",
              "strategy_region"]].to_string())


if __name__ == "__main__":
    main()
