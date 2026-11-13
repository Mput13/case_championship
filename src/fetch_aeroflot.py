"""Операционная статистика группы «Аэрофлот» с сайта для инвесторов ir.aeroflot.ru.

Что делает:
1. Находит на странице «Операционная статистика» самый свежий файл traffic_figures*.xls
   (в нём все месяцы с января 2014 года) и скачивает его в data/raw/aeroflot/.
2. Скачивает годовой отчёт 2025 года (PDF) туда же: из него вручную взяты факты
   в data/manual/aeroflot_report_facts.csv.
3. Раскладывает лист с абсолютными месячными значениями в длинную таблицу
   data/processed/aeroflot_traffic_monthly.csv: группа и авиакомпания «Аэрофлот»,
   13 показателей, всего / международные / внутренние линии.
4. Считает сезонность внутренних перевозок группы: data/processed/aeroflot_domestic_seasonality.csv.

Запуск: py -3.13 src/fetch_aeroflot.py   (нужен пакет xlrd для формата .xls)
"""
import re
import urllib.request
from pathlib import Path

import pandas as pd
import xlrd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "aeroflot"
PROC = ROOT / "data" / "processed"
UA = "Mozilla/5.0 (case-champ research script)"
SITE = "https://ir.aeroflot.ru"
STAT_PAGE = SITE + "/ru/reporting/traffic-statistics/"
ANNUAL_REPORT = SITE + "/fileadmin/user_upload/files/rus/common_info/gosa_doc_2026/Aeroflot_AR2025_RUS.pdf"

# английские названия строк файла → короткие коды показателей
METRICS = {
    "Revenue Passenger Kilometers": ("rpk", "млн пкм"),
    "Revenue Tonne  Kilometers": ("rtk", "млн ткм"),
    "Passengers carried": ("passengers", "тыс. чел."),
    "Mail carried": ("mail", "т"),
    "Cargo carried": ("cargo", "т"),
    "Cargo and mail carried": ("cargo_mail", "т"),
    "Revenue Load Factor": ("revenue_load_factor", "доля"),
    "Passenger Load Factor": ("passenger_load_factor", "доля"),
    "Flight hours for fleet": ("flight_hours", "ч"),
    "Available Tonne Kilometers": ("atk", "млн ткм"),
    "Available Seat  Kilometers": ("ask", "млн ккм"),
    "Revenue Cargo Tonne Kilometers": ("cargo_tkm", "млн ткм"),
    "Revenue flights": ("flights", "рейсов"),
}
ENTITY = {"Aeroflot Group": "group", "Aeroflot Airline": "aeroflot_airline"}
MONTHS = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                          "August", "September", "October", "November", "December"])}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def latest_xls_url():
    """Первая ссылка на traffic_figures*.xls на странице — самый свежий год."""
    html = get(STAT_PAGE).decode("utf-8", errors="replace")
    links = re.findall(r'href="([^"]*traffic_figures[^"]*\.xls)"', html)
    if not links:
        raise SystemExit("на странице операционной статистики не найден файл traffic_figures*.xls")
    u = links[0]
    return u if u.startswith("http") else SITE + "/" + u.lstrip("/")


def month_key(label):
    """'March \\n2014' → '2014-03'."""
    parts = str(label).split()
    return f"{int(parts[-1])}-{MONTHS[parts[0]]:02d}"


def parse_sheet(sh):
    """Первый блок листа: абсолютные значения по месяцам (до блока «Y-O-Y Change»)."""
    hdr = [(c, sh.cell_value(1, c)) for c in range(4, sh.ncols)]
    cols = [(c, month_key(v)) for c, v in hdr if str(v).strip() and str(v).split()[0] in MONTHS]
    rows, metric = [], None
    for r in range(2, sh.nrows):
        if "Y-O-Y" in str(sh.cell_value(r, 1)):
            break
        name = str(sh.cell_value(r, 2)).strip()
        if not name:
            continue
        if sh.cell_value(r, 1):
            metric = METRICS[name]
            scope = "total"
        else:
            scope = "international" if "International" in name else "domestic"
        for c, m in cols:
            v = sh.cell_value(r, c)
            if v == "" or v is None:
                continue
            rows.append({"month": m, "metric": metric[0], "scope": scope, "value": float(v), "unit": metric[1]})
    return rows


def seasonality(df):
    """Индекс месяца = значение / среднее за месяц того же года; среднее по полным годам 2023–2025."""
    d = df[(df.entity == "group") & (df.scope == "domestic") & df.metric.isin(["passengers", "cargo", "flights", "passenger_load_factor"])].copy()
    d["year"] = d.month.str[:4].astype(int)
    d["m"] = d.month.str[5:].astype(int)
    out = []
    for met, g in d.groupby("metric"):
        full = g[g.year.isin([2023, 2024, 2025])]
        if met == "passenger_load_factor":
            piv = full.pivot(index="m", columns="year", values="value")
        else:
            piv = full.pivot(index="m", columns="year", values="value")
            piv = piv / piv.mean()
        for m, r in piv.iterrows():
            row = {"metric": met, "month": int(m), **{f"y{y}": round(float(v), 4) for y, v in r.items()},
                   "mean_2023_2025": round(float(r.mean()), 4)}
            # 2026: изменение к тому же месяцу 2025 года (рынок 2026 года)
            v26 = g[(g.year == 2026) & (g.m == m)].value
            v25 = g[(g.year == 2025) & (g.m == m)].value
            if len(v26) and len(v25):
                row["change_2026_vs_2025"] = round(float(v26.iloc[0] - v25.iloc[0]) if met == "passenger_load_factor"
                                                   else float(v26.iloc[0] / v25.iloc[0] - 1), 4)
            out.append(row)
    return pd.DataFrame(out)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    url = latest_xls_url()
    xls = RAW / "traffic_figures.xls"
    xls.write_bytes(get(url))
    (RAW / "traffic_figures_url.txt").write_text(url + "\n", encoding="utf-8")
    pdf = RAW / "Aeroflot_AR2025_RUS.pdf"
    if not pdf.exists():
        pdf.write_bytes(get(ANNUAL_REPORT))

    book = xlrd.open_workbook(str(xls))
    rows = []
    for sh in book.sheets():
        ent = ENTITY.get(sh.name)
        if ent:
            rows += [{"entity": ent, **r} for r in parse_sheet(sh)]
    df = pd.DataFrame(rows)
    df["source"] = url
    PROC.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROC / "aeroflot_traffic_monthly.csv", index=False, encoding="utf-8")
    s = seasonality(df)
    s["source"] = "расчёт по data/processed/aeroflot_traffic_monthly.csv (" + url + ")"
    s.to_csv(PROC / "aeroflot_domestic_seasonality.csv", index=False, encoding="utf-8")
    print("ok", url, len(df), "значений;", df.month.min(), "—", df.month.max())


if __name__ == "__main__":
    main()
