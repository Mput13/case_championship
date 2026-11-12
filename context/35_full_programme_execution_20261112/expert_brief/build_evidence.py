"""Прочитать exact Git blobs / sealed hashes, сохранить только выбранные строки.

Запуск из корня репозитория: python3 context/35_full_programme_execution_20261112/expert_brief/build_evidence.py
Git не изменяет; пишет только в каталоге скрипта. Это сборка provenance, не модель RW.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import subprocess
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PREFIX = "context/35_full_programme_execution_20261112/"
PINS = {
    "P05": "a63a047bc6559df8bac3b2dde5c6464c3c9e6a0b",
    "P03": "79dc698b99dfe866886d32376ed388e85bdd039c",
    "P04": "620a0ac4bb11763319c4227485f6a3996b91d367",
    "P12": "06207b1650bd1c83e0f0761b25d063f2c395ace7",
    "CITY": "0fe215c6bf36a38667b8f780a8ec2af167b060be",
}
SEALED = {
    "P10": ("output_manifest.json", "5bf0be3d7e0c5a9796329e4784ebc816cb4228f3f97314d40c0e941425129426"),
    "P09": ("early/manifest.json", "d39186add31208d2d175ae38795240e630392c32460fd901dd756a727f0abc43"),
}
inputs = []
excerpts = []
seal_entries = {}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def write_json(name, x):
    (OUT / name).write_text(json.dumps(x, ensure_ascii=False, indent=2) + "\n")


def add_input(path, b, **kw):
    package = path.split("/")[0]
    if package == "variants":
        org = "Городской исследовательский пакет " + path.split("/")[1] + " общей программы Red Wings"
        period, unit, grain = "История 2025/доступный 2026; условный проект 2027–2028", "Программа/оборот/плечо/борт/час либо открытый запрос", "Город / programme_id / сценарный шаблон / request_id"
    else:
        org = "Исследовательский пакет " + package + " общей программы Red Wings"
        period = "История 2025/доступный 2026; постановка 2027–2028"
        unit = "Определение/метод/условный параметр/диагностика; точная единица в выбранной строке"
        grain = "Пакет / файл / выбранный объект или строка; не подтверждённый физический инвентарь"
    inputs.append({"input_id": path, "path": PREFIX + path, "sha256": sha(b), "bytes": len(b),
                   "organization": org, "url": "NOT_APPLICABLE_INTERNAL_ARTIFACT; см. artifact_path и binding",
                   "artifact_path": str(ROOT / PREFIX / path), "publication_date": "2026-11-12; дата исследовательского пакета",
                   "as_of": "2026-11-12", "period": period, "unit": unit, "granularity": grain,
                   "status": "PINNED_INTERNAL_INPUT_FOR_EXPERT_BRIEF_NOT_INDEPENDENT_ACCEPTANCE",
                   "coverage": "Только указанный файл/выбранные строки; UNKNOWN и условные поля сохраняются", **kw})
    return b.decode("utf-8-sig")


def gitread(pin_key, path):
    pin = PINS[pin_key]
    spec = pin + ":" + PREFIX + path
    b = subprocess.check_output(["git", "show", spec], cwd=ROOT)
    blob = subprocess.check_output(["git", "rev-parse", spec], cwd=ROOT, text=True).strip()
    return add_input(path, b, binding="EXACT_GIT_BLOB", commit=pin, git_blob=blob,
                     read_method="git show", acceptance="Вход для подготовки вопросов; не приёмка экономики")


def sealread(package, path):
    mf, expected = SEALED[package]
    if package not in seal_entries:
        b = (ROOT / PREFIX / package / mf).read_bytes()
        assert sha(b) == expected, (package, "manifest hash mismatch")
        seal_entries[package] = {x["path"]: x for x in json.loads(b)["files"]}
        add_input(package + "/" + mf, b, binding="USER_SUPPLIED_SEALED_MANIFEST_SHA256",
                  manifest_sha256=expected, commit=None,
                  acceptance="Проверен seal; root Git commit и экономическая приёмка этим не установлены")
    b = (ROOT / PREFIX / package / path).read_bytes()
    entry = seal_entries[package][path]
    assert sha(b) == entry["sha256"], (package, path, "payload hash mismatch")
    if "bytes" in entry:
        assert len(b) == entry["bytes"]
    return add_input(package + "/" + path, b, binding="PAYLOAD_SHA256_IN_USER_PINNED_SEALED_MANIFEST",
                     manifest_path=PREFIX + package + "/" + mf,
                     manifest_sha256=expected, commit=None,
                     acceptance="Хеш payload совпал; не ACCEPTED_FOR_UI и не принятая экономика")


def record(path, row_id, row, keys=None, note=""):
    ref = next(x for x in inputs if x["input_id"] == path)
    excerpts.append({
        "source_path": PREFIX + path,
        "binding": ref["binding"], "commit": ref.get("commit"),
        "manifest_sha256": ref.get("manifest_sha256"),
        "source_file_sha256": ref["sha256"],
        "source_row_id": row_id,
        "canonical_source_row_sha256": sha(canonical(row)),
        "hash_definition": "SHA256 UTF-8 JSON sort_keys=True ensure_ascii=False separators=(',',':') полного выбранного объекта; не upstream raw-row hash",
        "projection": row if keys is None else {k: row[k] for k in keys if k in row},
        "note": note,
    })


def csvrows(text):
    return list(csv.DictReader(io.StringIO(text)))


def savecsv(name, rows):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# P05: авторские статусы отдельно от независимой проверки.
gitread("P05", "P05/report.md")
v = json.loads(gitread("P05", "P05/validation.json"))
record("P05/validation.json", "empirical", v["empirical"], note="Авторская диагностика, не независимая приёмка")
for k in ["status", "calibration_status", "independent_review", "source_coverage"]:
    record("P05/validation.json", k, {k: v[k]})
a = csvrows(gitread("P05", "P05/assumptions_register.csv"))
for row in a:
    if row["assumption_id"] in ["P05-A01", "P05-A03", "P05-A06", "P05-A07", "P05-A08", "P05-A11", "P05-A12", "P05-A13"]:
        record("P05/assumptions_register.csv", row["assumption_id"], row)

for key in ["P03", "P04"]:
    path = key + "/handoff.json"
    j = json.loads(gitread(key, path))
    for k in ["status", "bounds", "findings", "remaining_fields"]:
        if k in j:
            record(path, k, {k: j[k]})
cash = json.loads(gitread("P04", "P04/cash_rules.json"))
record("P04/cash_rules.json", "keys", {"available_sections": list(cash)}, note="Полный источник прочитан; денежная модель не запускалась")

ui = json.loads(gitread("P12", "P12/ui_contract.json"))
record("P12/ui_contract.json", "acceptance_boundary", {k: ui[k] for k in ["sections", "acceptance_boundary"]})
record("P12/ui_contract.json", "result_import.gates", ui["result_import"], keys=["gates", "no_computation", "number2_gate", "trust_boundary"])

# Городские пакеты: только выбранные programmes и requests, без копии fixtures.
city_programmes = {}
for city in ["UFA", "GOJ", "TJM"]:
    path = f"variants/{city}/research_v1/programme_candidates.json"
    j = json.loads(gitread("CITY", path))
    arr = j["programmes"]
    city_programmes[city] = {x["programme_id"]: x for x in arr}
    selected = {
        "UFA": ["UFA-P00-KEEP", "UFA-P04-BANK-EW", "UFA-P05-DIRECT2"],
        "GOJ": ["GOJ-P01", "GOJ-P02", "GOJ-P03", "GOJ-P04"],
        "TJM": ["TJM-P03", "TJM-P04"],
    }[city]
    for row in arr:
        if row["programme_id"] in selected:
            record(path, row["programme_id"], row, keys=[
                "programme_id", "title", "name", "name_ru", "role", "status", "period",
                "period_start", "period_end", "additional_working_tail_requirement", "minimum_working_tails",
                "reserve_requirement", "route_changes", "keep_sales_and_actions", "resource",
                "matched_resource_proof", "connections", "assumption_ids", "basing_gate", "own_changes",
            ])
    reqpath = f"variants/{city}/research_v1/comparison_requests.csv"
    requests = csvrows(gitread("CITY", reqpath))
    keep = {"UFA": ["UFA-B02", "UFA-B06", "UFA-B12"], "GOJ": ["GOJ-B02", "GOJ-B03", "GOJ-B07"], "TJM": ["CMP-TJM-01", "CMP-TJM-02"]}[city]
    for row in requests:
        if row["request_id"] in keep:
            record(reqpath, row["request_id"], row)

tpath = "variants/TJM/research_v1/resource_diagnostics.csv"
trows = csvrows(gitread("CITY", tpath))
tchecks = {}
for pid in ["TJM-P03", "TJM-P04"]:
    rows = [x for x in trows if x["programme_id"] == pid]
    for row in rows:
        record(tpath, "/".join(row[k] for k in ["programme_id", "resource_group", "weekday_iso", "chain"]), row)
    tchecks[pid] = {"rows": len(rows), "legs_per_design_week": sum(int(x["legs_per_day"]) for x in rows),
                    "sum_block_h_inherited_k11": round(sum(float(x["block_h_inherited_k11"]) for x in rows), 6),
                    "sum_block_h_inherited_k12": round(sum(float(x["block_h_inherited_k12"]) for x in rows), 6),
                    "status": "Геометрический screen; не годовая экономика, не операционный pass",
                    "assumption_ids": ["TJM-A07", "TJM-A08"]}

# Запечатанные общие пакеты: root pin не выдумывается.
sealread("P10", "report.md")
for row in csvrows(sealread("P10", "metric_dictionary.csv")):
    if row["metric_id"] in ["reported_passengers", "OD_journeys", "passenger_segments", "market_share", "full_incremental_operating_result", "peak_funding"]:
        record("P10/metric_dictionary.csv", row["metric_id"], row)
for row in csvrows(sealread("P10", "metric_bridge_examples.csv")):
    if row["example_id"] in ["EX1", "EX2"]:
        record("P10/metric_bridge_examples.csv", row["example_id"], row, note="Условная арифметика определения; не наблюдение RW")
bridge = json.loads(sealread("P10", "growth_bridge.json"))
record("P10/growth_bridge.json", "status/metric/pending", bridge,
       keys=["status", "primary_metric", "first_stage", "number2_deadline", "outputs_pending", "required_checks"])
api = json.loads(sealread("P09", "early/api_contract.json"))
record("P09/early/api_contract.json", "api_contract", api)
sealread("P09", "early/interface_v1.py")

sources = []
for row in csvrows(sealread("P10", "sources.csv")):
    if row["source_id"] in ["FAVT_METHOD_HIST", "STAT17"]:
        record("P10/sources.csv", row["source_id"], row)
        sources.append({
            "source_id": row["source_id"], "organization": row["organization"], "url": row["url"],
            "publication_date": row["publication_date"], "period": row["period"],
            "unit": "Правило статистического учёта пассажиров; не кг груза",
            "granularity": row["granularity"], "as_of": row["as_of"],
            "status": "Унаследованный источник P10; актуальная применимая редакция UNKNOWN",
            "coverage": row["coverage"], "retrieved_at": row["retrieved_at"],
            "source_body_sha256": row["body_sha256"] or "UNKNOWN", "binding": "P10 sealed manifest + selected source row",
        })

sources.extend([
    {"source_id": "EB-WEB-ROSSIYA-CARGO", "organization": "АО Авиакомпания Россия",
     "url": "https://www.rossiya-airlines.ru/additional-services/cargo/", "publication_date": "UNKNOWN; недатированная действующая страница",
     "period": "Состояние страницы при чтении 12.11.2026; не прогноз 2027–2028",
     "unit": "Наличие описания услуги/справочника; коммерческие кг и доход не установлены",
     "granularity": "Пассажирские рейсы, справочник типов, включая RRJ-95", "as_of": "2026-11-12",
     "status": "PRIMARY_WEB_READ; применимость к конкретному RW-рейсу UNKNOWN",
     "coverage": "Груз/почта на пассажирских регулярных/чартерных рейсах; БГО справочно; грузовая ёмкость RW и ПД-8, цены, договоры и потоки не подтверждены",
     "retrieved_at": "2026-11-12; web open", "source_body_sha256": "UNKNOWN; web tool response, raw body not archived",
     "binding": "URL + web text read; не immutable upstream blob"},
    {"source_id": "EB-WEB-AEROFLOT-CARGO", "organization": "ПАО Аэрофлот",
     "url": "https://www.aeroflot.ru/products/cargo/", "publication_date": "UNKNOWN; страница содержит отдельные датированные изменения",
     "period": "Состояние страницы при чтении 12.11.2026; не подтверждение будущих условий UFA",
     "unit": "Процедура/типовое ограничение; не оценка yield",
     "granularity": "Категория груза / тип ВС / аэропортовая процедура", "as_of": "2026-11-12",
     "status": "PRIMARY_WEB_READ; без переноса численных норм на RW",
     "coverage": "Ограничения грузов, обработка, БГО и сроки приёмки; загрузка конкретного RW-рейса и прибыль UNKNOWN",
     "retrieved_at": "2026-11-12; web open", "source_body_sha256": "UNKNOWN; web tool response, raw body not archived",
     "binding": "URL + web text read; не immutable upstream blob"},
])
savecsv("source_register.csv", sources)

# Контрольная таблица из UFA; размер кабины не придуман.
u = city_programmes["UFA"]
H = u["UFA-P04-BANK-EW"]
D = u["UFA-P05-DIRECT2"]
legs = lambda x: sum(2 * row["round_trips_per_week"] for row in x["route_changes"])
assert H["additional_working_tail_requirement"] == D["additional_working_tail_requirement"] == 2
assert legs(H) == legs(D) == 24
control = []
for field, h, d, unit, aid in [
    ("airport_pairs", ";".join(x["origin_airport"] + "-" + x["destination_airport"] for x in H["route_changes"]), ";".join(x["origin_airport"] + "-" + x["destination_airport"] for x in D["route_changes"]), "Уникальная физическая airport pair", "UFA-A09;UFA-A06;UFA-A18"),
    ("round_trips_each_pair", "3", "3", "Оборот туда-обратно/нед, условный дизайн", "UFA-A09;UFA-A18"),
    ("physical_departures_week", str(legs(H)), str(legs(D)), "Физическое плечо/нед, 4*3*2; не годовой результат", "UFA-A09;UFA-A18"),
    ("working_tail_requirement", "2", "2", "Заявленная потребность в рабочих бортах; допуск UNKNOWN", "UFA-A12;UFA-A13;UFA-A14"),
    ("offered_seat_stages", "24*S", "24*S", "Только при общей принятой компоновке S; S и доступный инвентарь UNKNOWN", "EB-A02"),
    ("future_KEEP", "UNKNOWN; собственные SVX/NUX сохраняются", "UNKNOWN; действующие лучи и продажи сохраняются", "Все затронутые обязательства и продажи 2027–2028", "UFA-A12;UFA-A13;UFA-A14;UFA-A24"),
    ("crew_MRO_reserve", "UNKNOWN", "UNKNOWN", "Календарь/география/допуски/стоимость", "UFA-A12;UFA-A13;UFA-A14"),
    ("full_passenger_result_P_minus_KEEP", "UNKNOWN", "UNKNOWN", "RUB установленного года цен / общий период", "P04-A-METRIC-A;P04-A-COUNTERFACTUAL"),
    ("cargo_or_mail_net_contribution", "UNKNOWN", "UNKNOWN", "Дополнительный чистый вклад с вытеснением и расходами; не готовый вход P06", "EB-CARGO-01;EB-CARGO-02;EB-CARGO-03;EB-CARGO-04;EB-CARGO-05;EB-CARGO-06"),
    ("peak_funding", "UNKNOWN", "UNKNOWN", "Совместный датированный cash KEEP и проекта; не сумма отдельных пиков", "P10-CASH"),
]:
    control.append({"field": field, "UFA-P04-BANK-EW": h, "UFA-P05-DIRECT2": d, "unit": unit,
                    "period": "2027-01..2028-12; сезонность и фактические даты требуют допуска",
                    "source_rows": "UFA-P04-BANK-EW;UFA-P05-DIRECT2", "source_commit": PINS["CITY"],
                    "assumption_ids": aid, "status": "STAGE_A_DESIGN_NOT_ADMITTED_TO_ECONOMICS"})
savecsv("control_pair.csv", control)

assumptions = [
    {"assumption_id": "EB-A01", "value": "Первые три вопроса: узел, общий ресурс, груз/почта; всего семь",
     "selected_by": "Пользователь, уточнение профиля эксперта 12.11.2026; формулировки исследовательского агента",
     "basis": "Опыт эксперта: сеть/хабы Аэрофлота и пассажиро-грузовая эффективность",
     "range_or_UNKNOWN": "Не численный вес и не допущение модели; применимость экспертизы по типам UNKNOWN",
     "impact": "Порядок разговора; при ином профиле нужны профильные коллеги для followups", "sensitivity_or_refinement": "Уточнить типы ВС, масштаб сети и личную функцию эксперта"},
    {"assumption_id": "EB-A02", "value": "Символьная общая компоновка S, кресло-этапы 24*S в обеих программах",
     "selected_by": "Исследовательский агент expert_brief", "basis": "UFA P04/P05: 4 пары*3RT*2 направления; численные кресла не назначены",
     "range_or_UNKNOWN": "S, реально продаваемые кресла и физическая допустимость UNKNOWN",
     "impact": "Контроль предложения без подмены бортов свободным ресурсом",
     "sensitivity_or_refinement": "P03: вариант/кабина/даты/инвентарь; если типы или блоки мест различаются, сравнение обновить"},
]
for aid, value, basis, impact, refine in [
    ("EB-CARGO-01", "БГО обычного пассажирского ВС или спецкомпоновка UNKNOWN", "Уточнение пользователя; эксперт должен описать собственный пример", "Тип и потеря пассажирских мест могут поменять всю программу", "Тип/вариант/компоновка, допуски оператора; ПД-8 отдельно"),
    ("EB-CARGO-02", "Свободные кг/м3 и payload по каждому рейсу UNKNOWN", "Номинальный объём БГО не равен доступной коммерческой ёмкости", "Багаж/топливо/центровка/дальность/крейсерский режим могут ограничить груз", "AFM/РПП и загрузка по дате/маршруту; не переносить справочник России на RW"),
    ("EB-CARGO-03", "Датированный физический поток каждого направления и его устойчивость UNKNOWN", "Нет почтового/грузового спроса или договора RW в принятом входе", "Односторонность/сезонность/дедлайны могут убрать вклад или изменить частоты", "Обезличенный поток/обязательства по дате и направлению; контрактный гарантированный минимум отдельно от потенциала"),
    ("EB-CARGO-04", "Чистая ставка, оплачиваемый вес, гарантия и денежные даты UNKNOWN", "Не присваиваем чужой договор; физический и оплачиваемый вес различаются", "Размер выручки, кредитный риск и потребность в ликвидности", "Тариф/единица/период/налоги/комиссии/минимум/платёж/расторжение; обоснованный порядок с областью применимости"),
    ("EB-CARGO-05", "Дополнительные расходы и операционный эффект UNKNOWN", "Обработка и сроки не бесплатны; P04/P03 уже содержат часть базовых расходов", "Turn/crew/стыковки/досмотр/вытеснение/штрафы могут перевернуть выбор", "Смета по экономическим событиям; расходы один раз; операционный и денежный пересчёт P03/P05/P06"),
    ("EB-CARGO-06", "Граница ΔΠpass+B_H−B_D=0; численный порог UNKNOWN", "Алгебра сравнения общих полных результатов; не новая модель спроса или денег", "Груз меняет выбор только при достаточной разности чистых вкладов и допустимом ресурсе", "P06 совместно пересчитывает программы после входов; cash отдельно; при изменении пассажирской программы не держать её результат фиксированным"),
]:
    assumptions.append({"assumption_id": aid, "value": value, "selected_by": "Исследовательский агент; гипотеза по явному запросу пользователя",
                        "basis": basis, "range_or_UNKNOWN": "Эмпирический диапазон UNKNOWN; сценарные числа не назначены",
                        "impact": impact, "sensitivity_or_refinement": refine})
savecsv("assumptions.csv", assumptions)
write_json("source_rows.json", {"version": "EB-20261112-v2", "purpose": "Выбранные строки для вопросов; не полный fixture и не приёмка результата", "rows": excerpts,
                                "TJM_geometry_diagnostic": tchecks})
write_json("input_manifest.json", {
    "version": "EB-20261112-v2", "source_date": "2026-11-12", "inputs": inputs,
    "binding_rule": "Городские/P03/P04/P05/P12: git show exact SHA. P10/P09: пользовательский sealed manifest SHA256 + payload hash; root Git commit пока UNKNOWN.",
    "discarded_as_acceptance": "e6f9054e checkpoint читался при поиске источников; не root pin и не основание приёмки. Нужные P10/P09 повторно прочитаны через пользовательские seal/hash.",
    "source_coverage": "Только выбранные города UFA/GOJ/TJM и договорённые общие пакеты; не перепроверка всех 20 городов/35 гипотез",
    "external_sources": "source_register.csv; две cargo-страницы прочитаны web search/open; raw body hash UNKNOWN, не маскируется под Git pin",
    "writes": "Только expert_brief/; Git и общие входы не изменяются",
})
print(json.dumps({"input_files": len(inputs), "selected_rows": len(excerpts), "source_register_rows": len(sources),
                  "control_rows": len(control), "assumptions": len(assumptions), "sealed_manifests_verified": list(SEALED)}, ensure_ascii=False))
