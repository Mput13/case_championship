"""Шаг 4. Книга Excel для заочной сдачи: все расчёты одним файлом, у каждой цифры источник.

Листы: Как читать · Сравнение гипотез · Маршруты (обязательная таблица) · Карты · Лонглист ·
Критерии и веса · Спрос по кандидатам · Спрос по парам · Известные потоки · Допущения сети ·
Допущения спроса · «Ковёр» · Источники данных.
Шрифт Arial во всей книге; после сборки XML проверяется на Calibri (src/build_longlist.set_font).

Выход: outputs/redwings_model.xlsx
Запуск: python src/build_workbook.py   (после src/network_model.py и src/network_map.py)
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

import rules
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill

from build_longlist import set_font

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
A = ROOT / "data" / "assumptions"
OUT = ROOT / "outputs" / "redwings_model.xlsx"


def sheets():
    s = {}
    fit = json.loads((P / "demand_fit.json").read_text(encoding="utf-8"))
    readme = [
        ("Что это", "Расчёт кейса Red Wings «Новый хаб или прямые рейсы?»: лонглист городов, спрос по парам, сравнение двух гипотез."),
        ("Сборка", datetime.now().strftime("%d.%m.%Y %H:%M")),
        ("Как пересчитать", "py -3.13 src/update.py --force (одна команда: загрузка данных, проверки, все расчёты, эта книга)"),
        ("Сценарии", "base — базовый, cautious — осторожный; все допущения на листах «Допущения сети» и «Допущения спроса»"),
        ("Сравнение гипотез", "итоги по вариантам: самолёты, пассажиры (сегменты и поездки), выручка, результат до аренды, доля рынка, «Ковёр»"),
        ("Маршруты", "обязательная таблица кейса: маршрут · пассажиров в год · рейсов в неделю · откуда спрос и частота · светофор дальности"),
        ("Лонглист", f"20 городов, баллы и устойчивость к весам (фильтр: не ближе {rules.MIN_DIST_KM:.0f} км к Москве и Екатеринбургу)"),
        ("Спрос", f"модель тяготения по {fit['n_fit']} известным потокам 2025 года; медианная ошибка «исключи по одному» "
                  f"{fit['loo_median_abs_error_pct_of_fact']:.0f}% от факта ({fit['loo_median_abs_error_pct']:.0f}% от прогноза) — поэтому два сценария"),
        ("Методы простым языком", "docs/22 (источники лонглиста), docs/23 (спрос по парам), docs/24 (сравнение гипотез)"),
        ("Шрифт", "Arial во всей книге"),
    ]
    s["Как читать"] = pd.DataFrame(readme, columns=["Раздел", "Пояснение"])

    sm = pd.read_csv(P / "network_summary.csv").drop(columns=["hub"])
    sm["scenario"] = sm.scenario.map({"base": "базовый", "cautious": "осторожный", "base_sub": "базовый с субсидией", "cautious_sub": "осторожный с субсидией"})
    s["Сравнение гипотез"] = sm.rename(columns={
        "scenario": "Сценарий", "variant": "Вариант", "routes": "Маршрутов", "aircraft": "Самолётов (с резервным)",
        "flights_week": "Рейсов в неделю", "segments_year": "Пассажиров в год (сегменты)",
        "od_trips_year": "Поездок в год (откуда — куда)", "transfer_od_year": "Из них с пересадкой",
        "revenue_mln_year": "Выручка, млн ₽/год", "var_cost_mln_year": "Расходы на рейсы, млн ₽/год",
        "result_mln_year": "Результат до аренды самолётов, млн ₽/год", "share_pp": "Прирост доли рынка, п. п. (только новые для Red Wings)",
        "rw_migrated_year": "Перешли со старых рейсов Red Wings, пасс./год", "rw_forgone_mln_year": "Потерянная выручка старых рейсов, млн ₽/год (вычтена)",
        "net_new_segments_year": "Новые для Red Wings пассажиры (сегменты)", "share_pp_gross": "Доля всех перевезённых, п. п.",
        "fare_up_to_breakeven_pct": "На сколько % поднять все тарифы, чтобы выйти в ноль", "subsidy_rub_per_trip": "Или доплата на поездку, ₽",
        "subsidy_mln_year": "Субсидия на рейсы в обход Москвы, млн ₽/год (входит в выручку)",
        "kover_days_avg": "Средние дни «Ковра» в аэропортах сети", "kover_coverage": "Доля концов рейсов с данными о «Ковре»",
        "check_segments_minus_od": "Проверка: сегменты − (местные + 2 × пересадочные), должно быть 0"})
    s["Маршруты"] = pd.read_csv(P / "mandatory_routes_table.csv")
    fr = pd.read_csv(P / "fleet_ramp.csv")
    fr["scenario"] = fr.scenario.map({"base": "базовый", "cautious": "осторожный", "base_sub": "базовый с субсидией", "cautious_sub": "осторожный с субсидией"})
    s["Рост сети хаба"] = fr.rename(columns={"scenario": "Сценарий", "hub": "Хаб", "fleet_cap": "Самолётов доступно", "aircraft": "Самолётов нужно (с резервным)",
        "routes": "Лучей", "segments_year": "Пассажиров в год (сегменты)", "transfer_od_year": "Поездок с пересадкой в год",
        "result_mln_year": "Итог до аренды самолётов, млн ₽/год", "subsidy_mln_year": "Субсидия, млн ₽/год",
        "share_pp": "Прирост доли рынка, п. п.", "spokes": "Лучи (коды аэропортов)"})
    s["Карты"] = pd.DataFrame([("Гипотеза 1, хаб (база)", "outputs/map_hub.png"),
                               ("Гипотеза 2, прямые рейсы (база)", "outputs/map_direct.png")], columns=["Карта", "Файл"])
    sc = pd.read_csv(P / "longlist_scores_min500.csv")
    ll = pd.read_csv(P / "longlist.csv")[["iata", "pax_2025", "pax_source_url", "last365_days", "gap_pop", "catchment_pop",
                                          "dist_msk_km", "dist_ekb_km", "base_carriers"]]
    s["Лонглист"] = sc[["rank", "iata", "city", "score", "top3_share_random"]].merge(ll, on="iata", how="left").rename(columns={
        "rank": "Место", "iata": "Код", "city": "Город", "score": "Балл 0–1", "top3_share_random": "В топ-3 при случайных весах",
        "pax_2025": "Пассажиропоток 2025", "pax_source_url": "Источник пассажиропотока", "last365_days": "Дни «Ковра» за год",
        "gap_pop": "«Дыра» в сообщении, чел.", "catchment_pop": "Население в 75 км", "dist_msk_km": "До Москвы, км",
        "dist_ekb_km": "До Екатеринбурга, км", "base_carriers": "Базовые перевозчики"})
    cj = json.loads((P / "criteria.json").read_text(encoding="utf-8"))
    s["Критерии и веса"] = pd.DataFrame(cj["criteria"])[["label", "key", "dir", "weight", "why", "origin"]].rename(columns={
        "label": "Критерий", "key": "Ключ", "dir": "Больше лучше (+) / меньше лучше (−)", "weight": "Вес",
        "why": "Зачем", "origin": "Откуда критерий"})
    s["Спрос по кандидатам"] = pd.read_csv(P / "demand_by_candidate.csv").rename(columns={
        "hub": "Код", "city": "Город", "spokes_in_ssj": "Аэропортов в зоне SSJ", "pax_all_base": "Спрос во все города зоны, пасс./год",
        "pax_no_direct_base": "Скрытый спрос (нет прямого рейса), база", "pax_no_direct_cautious": "Скрытый спрос, осторожно",
        "no_direct_spokes": "Направлений без прямого рейса", "pax_closed_airports_base": "Спрос в закрытые аэропорты (если откроют)",
        "top_no_direct": "Крупнейшие направления без прямого рейса"})
    dp = pd.read_csv(P / "demand_pairs.csv")
    s["Спрос по парам"] = dp.rename(columns={
        "a": "Код А", "b": "Код Б", "city_a": "Город А", "city_b": "Город Б", "closed": "Закрытый аэропорт", "km": "Км",
        "pop_a": "Население А", "pop_b": "Население Б", "direct_now": "Прямой рейс есть", "rail_hr": "Часов поездом",
        "pax_cautious": "Пассажиров в год, осторожно", "pax_base": "Пассажиров в год, база", "pax_optimistic": "Пассажиров в год, оптимистично",
        "observed": "Известный поток", "observed_coverage": "Охват известного потока", "observed_source": "Источник известного потока",
        "method": "Откуда цифра"})
    s["Известные потоки"] = pd.read_csv(P / "demand_calibration.csv")
    s["Допущения сети"] = pd.read_csv(A / "network.csv")
    s["Допущения спроса"] = pd.read_csv(A / "demand.csv")
    s["«Ковёр»"] = pd.read_csv(P / "kover_days.csv")
    man = json.loads((ROOT / "data/raw/_manifest.json").read_text(encoding="utf-8"))
    s["Источники данных"] = pd.DataFrame([{"Ключ": k, "Источник": v["name"], "Владелец": v["owner"], "Ссылка": v["url"],
                                           "Условия": v["license"], "Статус": v["status"], "Обновлён": v["fetched_at"],
                                           "Записей": v["rows"], "Питает": ", ".join(v.get("feeds", []))} for k, v in man.items()])
    return s


def main():
    OUT.parent.mkdir(exist_ok=True)
    with pd.ExcelWriter(OUT) as xw:
        for name, df in sheets().items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
    wb = load_workbook(OUT)
    head = PatternFill("solid", fgColor="111318")
    for ws in wb.worksheets:
        for c in ws[1]:
            c.font = Font(name="Arial", bold=True, color="FFFFFF")
            c.fill = head
            c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        for col in ws.columns:
            w = max(len(str(c.value or "")) for c in col[:60])
            ws.column_dimensions[col[0].column_letter].width = min(max(10, w * 0.9), 60)
    ws = wb["Карты"]
    for i, f in enumerate(["map_hub.png", "map_direct.png"]):
        img = XLImage(ROOT / "outputs" / f)
        img.width, img.height = img.width * 0.42, img.height * 0.42
        ws.add_image(img, f"A{4 + i * 42}")
    wb.save(OUT)
    set_font(OUT)  # Arial везде + проверка, что Calibri нет
    print("книга", OUT, "листов", len(wb.sheetnames))


if __name__ == "__main__":
    main()
