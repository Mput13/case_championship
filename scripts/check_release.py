"""Сверка HTML, CSV и Excel после сборки. Запуск: py -3.13 scripts/check_release.py."""
import json
import re
import zipfile
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"
html = (ROOT / "archive/dashboards/redwings_panel_v2.html").read_text(encoding="utf-8")
data = json.loads(re.search(r"const D = (.*);\n", html).group(1))
summary = pd.read_csv(P / "network_summary.csv")
embedded = pd.DataFrame(data["net"]["summary"])
keys = ["scenario", "variant"]
numeric = summary.select_dtypes("number").columns.tolist()
pd.testing.assert_frame_equal(summary.set_index(keys)[numeric].sort_index(),
                              embedded.set_index(keys)[numeric].sort_index(), check_dtype=False)
routes = pd.read_csv(P / "network_routes.csv")
assert len(data["net"]["routes"]) == len(routes)
for row, expected in zip(data["net"]["routes"], routes.to_dict("records")):
    for key in ("scenario", "variant", "from", "to", "pax_year_segments", "result_mln_year", "subsidy_mln_year"):
        assert row[key] == expected[key], (key, row, expected)
for name in ("longlist.xlsx", "redwings_model.xlsx"):
    path = ROOT / "outputs" / name
    wb = load_workbook(path)
    assert not [(ws.title, c.coordinate) for ws in wb for row in ws for c in row if c.data_type == "f" and c.value == "="]
    assert not [(ws.title, c.coordinate) for ws in wb for row in ws for c in row if c.data_type == "e"]
    with zipfile.ZipFile(path) as z:
        assert not [n for n in z.namelist() if n.endswith(".xml") and b"Calibri" in z.read(n)]
workbook = pd.read_excel(ROOT / "outputs/redwings_model.xlsx", sheet_name="Сравнение гипотез")
assert workbook["Результат до аренды самолётов, млн ₽/год"].tolist() == summary.result_mln_year.tolist()
full = pd.read_excel(ROOT / "outputs/redwings_model.xlsx", sheet_name="Маршруты всех сценариев")
assert len(full) == len(routes)
assert full.result_mln_year.tolist() == routes.result_mln_year.tolist()
assert "/*__DATA__*/null" not in html and "Calibri" not in html
print(f"PASS: {len(summary)} итогов, {len(routes)} строк маршрутов; HTML = CSV = Excel; форматы и шрифты проверены")
