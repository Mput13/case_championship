"""Document legacy and current input sources without rerunning the model."""
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6"
P = ROOT / "context/35_full_programme_execution_20261112"


def git(path):
    return subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)


def write_csv(name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


old = json.loads((ROOT / "context/32_data_sources_audit_20261112/source_catalog.json").read_text())
facts = json.loads((ROOT / "context/32_data_sources_audit_20261112/audit_facts.json").read_text())
rows = []
for r in old:
    rows.append(dict(id=r["id"], source=r["name"], scope="AUTHOR_BASELINE_" + BASE,
                     status=r["status"], period=r["period"], what=r["purpose"],
                     caveat=r["assessment"], urls=" | ".join(x[1] for x in r["links"]),
                     files=" | ".join(r["paths"]), current_use="Historical source use; current P09 role must be read separately below."))

new = [
    ("N01", "Операционная статистика группы и АК «Аэрофлот»", "XLS: помесячные перевозки 2025 и январь–октябрь 2026; carrier/group и domestic/international отдельно", "Сезонный профиль P05 и агрегатная проверка; не маршрутный OD", "https://ir.aeroflot.ru/fileadmin/user_upload/files/rus/reports/oper_stat/2025/traffic_figures_december.xls | https://ir.aeroflot.ru/fileadmin/user_upload/files/rus/reports/oper_stat/2026/traffic_figures_2026_october.xls", "P09/subject/P05/report.md", "USED_IN_P05_SEASONAL_PRIOR"),
    ("N02", "Официальные аэропортовые и carrier-релизы, извлечённые в P01_MONTHLY", "86 airport-month строк, 36 UT carrier-month строк (9 helicopter), 133 segment observations; периоды/overlap/version в каждой строке", "Контекст и проверка масштаба. Не полный monthly OD; не все эти строки включены в параметры уже закреплённого P05", "https://ar-kuf.ru/about/news/itogi-raboty-v-novogodnie-prazdnik/ | https://www.kja.aero/press/news/mezhdunarodnyy-aeroport-krasnoyarsk-podvel-itogi-raboty-za-2025-god-/", "P01_MONTHLY/sources.csv | P01_MONTHLY/airport_monthly.csv | P01_MONTHLY/airport_pair_segment_observations.csv", "RESEARCH_CONTEXT_AND_QUALIFICATION"),
    ("N03", "Официальные расписания аэропортов и авиакомпаний", "2 274 опубликованных продукта/правила P02; даты, часы, carrier label, период и ordered itinerary", "Конкурентные досье и проверка существующих продуктов. Физический будущий inventory не установлен; численный P05 использует composite outside", "https://www.uvtaero.ru/raspisanie | https://ar-svx.ru/schedule/ | https://ar-goj.ru/schedule/", "P09/competition/competitor_products.csv | P09/competition_row_lineage.json", "SOURCE_EXPORT_AND_COMPETITOR_CONTEXT"),
    ("N04", "Датированные предложения покупки билетов", "Цена, тарифное семейство, дата вылета/наблюдения, booking lead, багаж; 34 fare-family строки P02v2 с разной сопоставимостью", "Опоры сценарной цены и отдельные проверки. Не средний realised yield и не полная сезонная ценовая панель", "https://flyredwings.com/ | https://www.utair.ru/", "P09/subject/P05/model.py | P09/subject/P05/report.md", "PRICE_REFERENCE_NOT_REALIZED_SALES"),
    ("N05", "Локальные прейскуранты аэропортов, топлива и обслуживания", "PDF/HTML/DOCX: отдельные ставки с единицами, НДС, датой и оператором. P04:127 строк reference/unknown, не127 готовых будущих цен", "Драйверы стоимости и пороговые функции; перенос в2027–28 явно сценарный", "https://www.airportufa.ru/partners/airlines/rates/ | https://ar-kuf.ru/partners/airlines/pricelists/ | https://mcx.aero/info/skidochnaya_sistema/", "P09/local_rate_corrections.json | P09/parameterledger.json | P09/economics_report.md", "REFERENCE_RATES_AND_EXPLICIT_UNKNOWN_COSTS"),
    ("N06", "Региональная поддержка и правила денежных сроков", "Сохранённый документ Росавиации: eligibility, лимиты, специальные тарифы, отбор и cash events", "В основном P09 — no-support; остальные схемы условны, не автоматическая выплата7/12", "https://favt.gov.ru/public/materials/4/3/a/7/5/43a7517a25306f513bba1b901c38eeee.pdf", "P09/economics_report.md | P09/subject/P04/cash_rules.json", "RULES_AND_NO_SUPPORT_BASELINE"),
    ("N07", "Парк RW, аэропорты, ТО и экипажные правила", "Типы/инфраструктура/границы договоров; датированные первичные документы и публикации", "Ограничения и N(t)-сценарии. Наличие самолёта или ТО не доказывает свободный ресурс RW", "https://flyredwings.com/about/park/ | https://ar-goj.ru/about/news/volga-avia-nachala-provodit-tekhnicheskoe-obsluzhivanie-samo/ | http://publication.pravo.gov.ru/document/0001202511280038", "P09/parameterledger.json | P09/fleet_calendar.json | P09/choice_report.md", "EVIDENCE_PLUS_SCENARIO_RESOURCE"),
    ("N08", "Росавиация и публичная отчётность перевозчиков", "Перевозки отдельных авиакомпаний и групп, определения рейса/этапа; исторические и накопленные периоды отдельно", "Масштаб цели№2; реальный reporting adapter и доля всей RW не установлены", "https://www.favt.gov.ru/novosti-novosti?id=17763&version=print | https://rosstat.gov.ru/free_doc/new_site/business/trans-sv/metod-transp.pdf", "P10/metric_dictionary.csv | P10/competitor_scale.csv | P10/report.md", "STRATEGY_SCALE_NOT_ACCEPTED_SHARE_FORECAST"),
    ("N09", "Официальные страницы цифровых сервисов RW", "Правила багажа, возвратов, регистрации и наблюдавшиеся этапы покупки; сохранённые экраны", "Аудит механизма и гипотез улучшения. Эффект на продажи/экономию не измерен", "https://flyredwings.com/", "P11/digital_cards.json | P11/digital_effects.csv | P11/handoff.md", "QUALITATIVE_PRODUCT_AUDIT"),
    ("N10", "Консультация эксперта Аэрофлота", "Две расшифровки одной консультации; структурированный пересказ отделён от речи и шумного ASR", "Сверка процесса, условий эксплуатации и защиты. Не независимые две проверки и не внутренние данные RW", "USER_SUPPLIED_ATTACHMENTS", "P00/expert_inputs/manifest.json | expert_final_coverage/coverage.csv", "QUALITATIVE_EXPERT_EVIDENCE"),
]
for ident, title, what, caveat, urls, files, status in new:
    rows.append(dict(id=ident, source=title, scope="CURRENT_RESEARCH_20261112", status=status,
                     period="См. период каждой записи/сохранённой версии", what=what, caveat=caveat,
                     urls=urls, files=files, current_use=status))
write_csv("source_families.csv", rows)

inventory = []
for r in facts["tables"]:
    inventory.append(dict(commit=BASE, path=r["path"], rows=r.get("records"),
                          fields=" | ".join(r.get("fields", [])), sha256=r.get("sha256"),
                          kind="MANUAL_OR_ASSUMPTION_OR_PROCESSED; see source_families.csv"))
write_csv("baseline_tables.csv", inventory)

# Extract URL evidence without calling every mention a directly used model input.
links = {}
def add(url, path, scope):
    for value in re.findall(r"https?://[^\s<>\"']+", str(url)):
        value = value.rstrip(").,;]}")
        links.setdefault((value, scope), set()).add(path)
for r in rows:
    add(r["urls"], r["files"], r["scope"])
known = list(csv.DictReader(io.StringIO(git("data/manual/known_flows.csv").decode("utf-8-sig"))))
for r in known: add(r.get("source", ""), "BASE:data/manual/known_flows.csv", "LEGACY_OBSERVED_FLOW_REFERENCE")
paths = [P / "P09/sources.csv", P / "P01_MONTHLY/sources.csv"]
for city in sorted((P / "variants").iterdir()):
    q = city / "research_v1/evidence.csv"
    if q.is_file(): paths.append(q)
for path in paths:
    if not path.is_file(): continue
    with path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            for k, value in r.items():
                if k and any(x in k.lower() for x in ["url", "source", "link"]):
                    add(value, str(path.relative_to(ROOT)), "RESEARCH_EVIDENCE_NOT_AUTOMATIC_NUMERIC_USE")
write_csv("source_urls.csv", [dict(url=url, usage_scope=scope, evidence_files=" | ".join(sorted(paths)))
                              for (url, scope), paths in sorted(links.items())])

sample_dir = HERE / "baseline_evidence"
sample_dir.mkdir(exist_ok=True)
for path in ["data/raw/SOURCES.md", "data/raw/_manifest.json", "data/manual/known_flows.csv", "src/fetch_social.py", "src/fetch_weather.py"]:
    (sample_dir / Path(path).name).write_bytes(git(path))

manifest = []
for path in sorted(HERE.rglob("*")):
    if path.is_file() and path.name != "manifest.json" and "__pycache__" not in path.parts:
        raw = path.read_bytes()
        manifest.append(dict(path=str(path.relative_to(HERE)), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
(HERE / "manifest.json").write_text(json.dumps(dict(baseline_commit=BASE,
    source_family_rows=len(rows), url_scope_rows=len(links), files=manifest,
    boundaries="Evidence inventory, not admission of every URL or independent model calibration."), ensure_ascii=False, indent=2) + "\n")
print(json.dumps(dict(source_families=len(rows), baseline_tables=len(inventory), url_scope_rows=len(links))))
