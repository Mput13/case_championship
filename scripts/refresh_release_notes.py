"""Обновляет таблицу итогов и точечные формулировки после сетевого расчёта."""
from pathlib import Path
import re
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
s = pd.read_csv(ROOT / "data/processed/network_summary.csv")
fmt = lambda x: f"{abs(int(x)):,}".replace(",", " ")
signed = lambda x: ("+" if x >= 0 else "−") + fmt(x)
p = ROOT / "docs/24_hypotheses_comparison.md"
t = p.read_text(encoding="utf-8")
for row in s[s.scenario.eq("cautious_sub")].itertuples():
    variant = "Прямые рейсы" if pd.isna(row.hub) else row.variant
    pattern = r"(?m)^(\| \d+ \| " + re.escape(variant) + r" \|[^\n]*\| )[^|]+ \|$"
    t = re.sub(pattern, lambda m: m.group(1) + signed(row.result_mln_year) + " |", t)
t = t.replace("спрос втрое ниже", "нижняя оценка спроса")
t = t.replace("Хабы: тройка лонглиста", "Хабы: все 20 городов лонглиста; на основном табло тройка лонглиста")
t = t.split("\n## Проверка итоговой сборки\n")[0]
t += "\n## Проверка итоговой сборки\n\nДоступная субсидия теперь сравнивается также с сохранённой сетью без поддержки. Это устраняет ухудшение результата из-за жадного отбора. Потерянная выручка прежних рейсов вычитается полностью и при специальном тарифе. Выплата включена в выручку; её величина отличается от изменения результата сети.\n\nПроверки: `py -3.13 -m pytest tests -q`, `py -3.13 scripts/check_release.py`, `py -3.13 tests/check_panel_browser.py`. Последняя команда требует Playwright и установленный Chrome.\n\nРасчёт поддержки использует среднюю ставку и упрощённое сезонное применение специального тарифа, включая пропорциональную корректировку выручки пересадочных билетов. Право на конкретную выплату и условия будущего конкурса требуют отдельной проверки.\n"
p.write_text(t, encoding="utf-8")
p = ROOT / "docs/29_passport.md"
t = p.read_text(encoding="utf-8").replace("спрос втрое ниже средней оценки", "нижняя оценка спроса")
p.write_text(t, encoding="utf-8")
doc = next((ROOT / "outputs/passport").glob("*.docx"))
with zipfile.ZipFile(doc) as z:
    members = [(item, z.read(item.filename)) for item in z.infolist()]
with zipfile.ZipFile(doc, "w") as z:
    for item, value in members:
        if item.filename == "word/document.xml":
            value = value.decode("utf-8").replace("спрос втрое ниже средней оценки", "нижняя оценка спроса").encode("utf-8")
        z.writestr(item, value)
print("Обновлены пояснения сценариев и таблица итогов")
