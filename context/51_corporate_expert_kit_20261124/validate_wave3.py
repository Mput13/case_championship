#!/usr/bin/env python3
"""Validate the Wave 3 fleet, economics and expert kit against the source registry."""

import json
import math
import re
import subprocess
import sys
import tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
from openpyxl import load_workbook

from build_dossier_html import SECTIONS
from build_xlsx import DIRECTIONS, ROOT, SHEETS, W2, build_workbook, case_code, council_scores, load_registry, read_csv
from economics_engine import calculate, round_trip

SOFFICE = Path("/opt/homebrew/bin/soffice")
XLSX = "redwings_corporate_model.xlsx"
HTML = "redwings_corporate_dossier.html"
MEMO = "briefing_memo.md"
REQUIRED = (
    "economics_engine.py", "model_inputs_registry.json", "fleet_and_distance_matrix.csv",
    "pilot_economics_summary.csv", "build_xlsx.py", XLSX, "build_dossier_html.py", HTML, MEMO, "validate_wave3.py",
)
EVENTS = {"FUTURE_CONFIRMED": 4, "FUTURE_PROVISIONAL": 1, "FUTURE_TBD": 6}
FLEET_PROGRAM_FIELDS = (
    "rotations_per_program_per_week", "weekly_block_h", "weekly_aircraft_occupied_h", "max_simultaneous_aircraft",
    "active_aircraft", "fleet_with_reserve_base", "fleet_with_reserve_15_pct", "fleet_with_reserve_20_pct",
    "reserve_pool_equivalent_aircraft_at_15_pct", "reserve_pool_equivalent_aircraft_at_20_pct",
)
EXCEL_ERRORS = re.compile(r"^(?:#REF!|#DIV/0!|#VALUE!|#NAME\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!|Err:)")
BANNED_TOKEN = re.compile(r"\b(?:" + "|".join(("MO" + "W", "636" + "8", "19660" + "5")) + r")\b")


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


class Dossier(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self.chapters = []
        self.network_assets = []
        self.script = None
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.script = (attrs, [])
        if tag == "section":
            self.chapters.append(attrs.get("id"))
        for key in ("src", "srcset"):
            if key in attrs:
                self.network_assets.append(attrs[key])
        if tag == "link" and "href" in attrs:
            self.network_assets.append(attrs["href"])

    def handle_data(self, data):
        if self.script is not None:
            self.script[1].append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.scripts.append((self.script[0], "".join(self.script[1])))
            self.script = None

    def payload(self):
        scripts = [code for attrs, code in self.scripts if attrs.get("id") == "registry"
                   and attrs.get("type") == "application/json"]
        require(len(scripts) == 1, "Одно встроенное JSON-хранилище")
        return json.loads(scripts[0])

    def javascript(self):
        return "\n".join(code for attrs, code in self.scripts if attrs.get("type") != "application/json")


class Parity:
    def __init__(self):
        self.comparisons = 0
        self.max_rub = 0.0
        self.max_other = 0.0

    def check(self, reference, actual, context, key):
        if isinstance(reference, (int, float)):
            require(isinstance(actual, (int, float)) and math.isfinite(actual),
                    f"{context}.{key}: ожидалось число, получено {actual!r}")
            rub = "_rub" in key
            diff = abs(reference - actual)
            require(diff <= (1.0 if rub else 0.01) + 1e-9,
                    f"{context}.{key}: {actual} вместо {reference}, разница {diff}")
            if rub:
                self.max_rub = max(self.max_rub, diff)
            else:
                self.max_other = max(self.max_other, diff)
        else:
            require(reference == actual, f"{context}.{key}: {actual!r} вместо {reference!r}")
        self.comparisons += 1

    def report(self):
        return {"checks": self.comparisons, "max_abs_diff_rub": round(self.max_rub, 8),
                "max_abs_diff_other": round(self.max_other, 8)}


def verify_events(events):
    require(Counter(row["horizon_bucket"] for row in events) == EVENTS, "Состав календаря FUTURE_*")
    require(all(row["event_year"] == "2027" and row["series_id"] != "ARMY"
                and "ARMY-2027" not in row["event_id"] for row in events), "Периметр событий 2027")
    pmgf = [row for row in events if row["event_name"].startswith("ПМГФ")]
    require(len(pmgf) == 1 and (pmgf[0]["start_date"], pmgf[0]["end_date"]) == ("2027-04-20", "2027-04-23"),
            "Перенос ПМГФ")


def verify_sources(registry):
    cases = registry["pilots_and_clusters"]
    require([case_code(c) for c in cases] == ["P1A", "P1B", "P1C", "P2A", "P2B", "P3A", "P3B", "C4", "C5"],
            "Девять веток")
    require(registry["meta"]["open_source_go_count"] == 0 and registry["meta"]["pairs_quantified"] == 0
            and registry["meta"]["round0_threshold_pairs"] == 3
            and registry["fleet_matrix"]["fleet_requirements"]["base_dedicated_aircraft_open_sources"] == 0,
            "Утверждение об объёме или выделенном парке")
    require(all(case["decision"] == "Conditional" and case["demand_basis"] == "STRUCTURAL_HYPOTHESIS"
                and case["confirmed_pax"] is None for case in cases), "Исходные статусы / объём")
    sources = read_csv(W2 / "evidence_wave2.csv")
    require(len(sources) == 352 and registry["evidence"] == {e["evidence_id"]: e for e in sources},
            "Записи доказательств должны совпадать с CSV Волны 2")
    require(registry["organizations"] == read_csv(W2 / "organizations_screening_v2.csv") and
            Counter(o["status"] for o in registry["organizations"]) == {"Conditional": 28, "Insufficient-Evidence": 40},
            "Скрининг 68 организаций")
    opportunities = read_csv(W2 / "opportunities.csv")
    require(len({o["pair_id"] for o in opportunities if o["pair_id"]}) == 30 and
            Counter(o["decision"] for o in opportunities) == {"Conditional": 104, "Insufficient-Evidence": 76} and
            all(o["demand_basis"] == "STRUCTURAL_HYPOTHESIS" for o in opportunities), "Срез возможностей Волны 2")
    actual_hubs = {r["hub_iata"] for r in registry["hubs_summary"]}
    require(actual_hubs == {"SVX", "TJM", "OVB", "KJA", "LED", "SVO", "DME", "VKO", "ZIA"}
            and len(registry["hubs_summary"]) == 36, "Сравнение девяти узлов")
    volume_keys = ("local_od_pax_base", "transit_od_pax_detour25_base", "transit_od_pax_detour35_base",
                   "event_peak_od_pax_base")
    require(all(all(row[k] is None for k in volume_keys) for row in registry["hubs_summary"]), "Объём узлов")
    confirm = [h for h in registry["hubs_summary"] if h["demand_basis_scope"] == "CONFIRMED_UNIT"]
    structural = [h for h in registry["hubs_summary"] if h["demand_basis_scope"] == "STRUCTURAL_HYPOTHESIS"]
    require(len(confirm) == len(structural) == 18 and all(not any(row[k] for k in (
        "geometry_pairs_25", "geometry_pairs_35", "observed_transit_pairs_25", "observed_transit_pairs_35"))
        for row in confirm), "Смешение геометрии гипотез с подтверждёнными единицами спроса")
    verify_events(registry["events_2027_future"])
    require(registry["events_2027_future"] == [r for r in read_csv(W2 / "events_calendar_2027.csv")
            if r["horizon_bucket"].startswith("FUTURE_")], "События из FUTURE_*")
    playbook = registry["benchmarks_and_playbooks"]
    require({key: len(value) for key, value in playbook.items()} ==
            {"qualified_cases": 13, "rf_adaptations": 6, "term_sheets": 5}, "Трек B")
    return cases


def verify_csvs(registry, cases):
    parity = Parity()
    pairs = registry["fleet_matrix"]["pairs"]
    rows = read_csv(ROOT / "fleet_and_distance_matrix.csv")
    require(len(pairs) == len(rows) == 53 and len({p["airport_pair"] for p in pairs}) == 53, "53 пары")
    for expected, row in zip(pairs, rows, strict=True):
        for key, value in expected.items():
            actual = float(row[key]) if isinstance(value, (int, float)) else row[key]
            parity.check(value, actual, row["airport_pair"], key)
    rows = read_csv(ROOT / "pilot_economics_summary.csv")
    for case, row in zip(cases, rows, strict=True):
        require(row["case_id"] == case["case_id"] and row["decision"] == "Conditional"
                and row["demand_basis"] == "STRUCTURAL_HYPOTHESIS" and row["confirmed_pax"] == "",
                f"{row['case_id']}: классификация")
        expected = case["expected_outputs"]
        for direction in DIRECTIONS:
            for key, value in expected[direction].items():
                field = f"{direction}_{key}"
                if field in row:
                    parity.check(value, float(row[field]), row["case_id"], field)
    return parity.report()


def recalculate(workdir, *workbooks):
    profiles = (workdir / "lo-profile").as_uri()
    converted = workdir / "converted"
    converted.mkdir(exist_ok=True)
    result = subprocess.run([
        str(SOFFICE), f"-env:UserInstallation={profiles}", "--headless", "--convert-to", "xlsx",
        "--outdir", str(converted), *(str(w) for w in workbooks),
    ], text=True, capture_output=True, check=True, timeout=100)
    files = [converted / w.name for w in workbooks]
    require(all(f.is_file() for f in files), f"LibreOffice не создал результат. {result.stdout} {result.stderr}")
    return files


def errors(workbook):
    return [f"{ws.title}!{c.coordinate}:{c.value}" for ws in workbook for row in ws for c in row
            if c.data_type == "e" or isinstance(c.value, str) and EXCEL_ERRORS.search(c.value)]


def live_cell(workbook, calculated, sheet, cell):
    original = workbook[sheet][cell]
    require(original.data_type == "f" and original.value.startswith("="), f"Статическая ячейка {sheet}!{cell}")
    return calculated[sheet][cell].value


def verify_xlsx(registry, cases, workdir):
    workbook = load_workbook(ROOT / XLSX)
    require(tuple(workbook.sheetnames) == SHEETS, "Девять листов в заданном порядке")
    require(all(ws.freeze_panes and ws.auto_filter.ref and ws.page_setup.orientation == "landscape"
                for ws in workbook), "Навигация, фильтры и печать листов")
    for ws in workbook:
        for row in ws:
            for cell in row:
                if isinstance(cell.value, str):
                    require(not BANNED_TOKEN.search(cell.value), f"Устаревший токен {ws.title}!{cell.coordinate}")
    _, layouts, pair_rows, program_rows = build_workbook(registry)
    # Also exercise a change to an editable input and its via-formula executive link.
    test_case = cases[0]
    variant = test_case["variants"][0]
    sheet, layout, _ = layouts[test_case["cluster_id"]]
    test_positions, _, _ = layout[(case_code(test_case), variant["variant_id"])]
    changed_xlsx = workdir / "expert_edit.xlsx"
    edit_key = "doc_per_block_h_rub"
    assumptions = workbook[SHEETS[1]]
    param = variant["input_param_ids"]["outbound"][edit_key]
    change_row = next(r for r in range(4, assumptions.max_row + 1) if assumptions[f"A{r}"].value == param)
    base_doc = assumptions[f"D{change_row}"].value
    edited_value = base_doc + 10000
    assumptions[f"D{change_row}"] = edited_value
    workbook.save(changed_xlsx)
    assumptions[f"D{change_row}"] = base_doc
    original, edited = recalculate(workdir, ROOT / XLSX, changed_xlsx)
    calculated = load_workbook(original, data_only=True)
    inputs_after_edit = load_workbook(edited, data_only=True)
    error_cells = errors(calculated) + errors(inputs_after_edit)
    require(not error_cells, f"Ошибки формул Excel: {error_cells[:20]}")
    parity = Parity()
    values = {}
    for index, case in enumerate(cases, 7):
        code = case_code(case)
        sheet, layout, _ = layouts[case["cluster_id"]]
        for variant in case["variants"]:
            variant_id = variant["variant_id"]
            positions, status_row, _ = layout[(code, variant_id)]
            require(calculated[sheet.title][f"B{status_row}"].value == case["decision"] and
                    calculated[sheet.title][f"D{status_row}"].value == case["demand_basis"] and
                    calculated[sheet.title][f"J{status_row}"].value == "UNKNOWN", f"{code}: подписи основания")
            key = code, variant_id
            values[key] = {}
            for direction, column in zip(DIRECTIONS, "BCD", strict=True):
                metrics = {}
                for field, value in variant["expected_outputs"][direction].items():
                    raw = live_cell(workbook, calculated, sheet.title, f"{column}{positions[field]}")
                    parity.check(value, raw, f"{code}.{variant_id}.{direction}", field)
                    metrics[field] = raw
                values[key][direction] = metrics
            for direction, column in zip(DIRECTIONS[:2], "BC", strict=True):
                for field, value in variant["inputs"][direction].items():
                    raw = live_cell(workbook, calculated, sheet.title, f"{column}{positions[field]}")
                    parity.check(value, raw, f"Вход {code}.{variant_id}.{direction}", field)
        for col in "BCDEFGHIJ":
            require(workbook[SHEETS[0]][f"{col}{index}"].data_type == "f", f"Статическая ссылка сводки {col}{index}")
    t1_variant = test_case["variants"][0]
    variant_inputs = t1_variant["inputs"]["outbound"] | {edit_key: edited_value}
    expected_edit = calculate("CHARTER", variant_inputs)["rw_total_flight_cost_rub"]
    edit_metric = f"B{test_positions['rw_total_flight_cost_rub']}"
    test_sheet = layouts[test_case["cluster_id"]][0].title
    parity.check(expected_edit, inputs_after_edit[test_sheet][edit_metric].value, "Изменение DOC", "cost_rub")
    changed_directions = {"outbound": calculate("CHARTER", variant_inputs, publish=False)}
    param_in = t1_variant["input_param_ids"]["inbound"][edit_key]
    changed_directions["inbound"] = calculate("CHARTER", t1_variant["inputs"]["inbound"] |
                                               ({edit_key: edited_value} if param_in == param else {}), publish=False)
    edit_cycle = round_trip("CHARTER", **changed_directions, margin_pct=variant_inputs["target_margin_pct"])
    parity.check(edit_cycle["rw_net_contribution_rub"], inputs_after_edit[SHEETS[0]]["H7"].value,
                 "Сводка после изменения DOC", "contribution_rub")
    executive = calculated[SHEETS[0]]
    require([executive[x].value for x in ("A4", "C4", "D4", "E4", "F4", "G4", "H4", "I4", "J4")] ==
            ["0/3 Go", 0, 0, 30, 68, 352, 5, 9, 47], "Сводные показатели")
    for item, r in zip(registry["assumptions"], range(4, assumptions.max_row + 1), strict=True):
        params = calculated[SHEETS[1]]
        require(params[f"A{r}"].value == item["param_id"] and params[f"G{r}"].value == item["source_tag"]
                and (params[f"H{r}"].value or "") == "; ".join(item["evidence_ids"]), f"Параметр {r}")
        for column, key in (("D", "base_value"), ("E", "min_value"), ("F", "max_value")):
            parity.check(item[key], calculated[SHEETS[1]][f"{column}{r}"].value, item["param_id"], key)
    for pair in registry["fleet_matrix"]["pairs"]:
        r = pair_rows[pair["airport_pair"]]
        require(calculated[SHEETS[5]][f"B{r}"].value == pair["airport_pair"], "Идентичность аэропортовой пары")
        for col, field in zip("AGHIJKLM", ("rank", "route_distance_km_k110", "est_block_time_h", "distance_band",
                                         "ssj95b_100y_fit", "sj100_pd8_fit", "tu214_2class_fit", "longhaul_fit"), strict=True):
            parity.check(pair[field], live_cell(workbook, calculated, SHEETS[5], f"{col}{r}"),
                         pair["airport_pair"], field)
    fleet_programs = registry["fleet_matrix"]["fleet_requirements"]["program_scenarios"]
    for program, r in zip(fleet_programs, program_rows, strict=True):
        for col, field in zip("FHIJKLMNOP", FLEET_PROGRAM_FIELDS, strict=True):
            parity.check(program[field], live_cell(workbook, calculated, SHEETS[5], f"{col}{r}"), f"Парк.{r}", field)
    require(sum(c.data_type == "f" for row in workbook[SHEETS[7]] for c in row) >= 4,
            "COUNTIF скрининга")
    count = sum(c.data_type == "f" for ws in workbook for row in ws for c in row)
    return values, {"formula_errors": 0, "live_formulas": count, "edit_recalculated": True, **parity.report()}


def verify_html(dossier, registry, cases, xlsx_values, workdir):
    require(dossier.chapters == [key for key, _ in SECTIONS], "Порядок глав DID")
    require(not dossier.network_assets, f"Зависимости офлайн-досье: {dossier.network_assets}")
    data = dossier.payload()
    require(data["evidence"] == registry["evidence"] and data["organizations"] == registry["organizations"]
            and data["hubs"] == registry["hubs_summary"] and data["fleet"] == registry["fleet_matrix"]
            and data["barriers"] == registry["why_not_barriers"]
            and data["playbooks"] == registry["benchmarks_and_playbooks"] and data["city_pairs"] == 30
            and data["scores"] == [list(s) for s in council_scores()], "Источники досье")
    require(data["events"] == registry["events_2027_future"], "Календарь досье")
    verify_events(data["events"])
    require([question for _, question in data["questions"]] == registry["rw_5_questions"] and
            data["customer_request"] == registry["anonymized_customer_request"], "Пакет вопросов RW")
    path = workdir / "dossier.cjs"
    path.write_text(dossier.javascript(), encoding="utf-8")
    subprocess.run(["node", "--check", str(path)], check=True, capture_output=True, text=True, timeout=20)
    rows = []
    prepared = registry["pilots_and_clusters"][0]["variants"][0]
    delta = {"outbound": {"doc_per_block_h_rub": prepared["inputs"]["outbound"]["doc_per_block_h_rub"] + 10000}}
    for case, embedded in zip(cases, data["cases"], strict=True):
        require(all(embedded[k] == case[k] for k in ("case_id", "demand_basis", "decision", "confirmed_pax")) and
                embedded["code"] == case_code(case), "Доказательность сценариев в досье")
        for v, scenario in zip(case["variants"], embedded["variants"], strict=True):
            require(all(v[k] == scenario[k] for k in ("variant_id", "mode", "inputs", "input_param_ids")),
                    f"{v['variant_id']}: входы встроенного расчёта")
            rows.append((embedded["code"], v, scenario))
    node_code = (
        "const {calculateScenario}=require(process.argv[1]);"
        "const {variants,edited,delta}=JSON.parse(require('node:fs').readFileSync(0,'utf8'));"
        "console.log(JSON.stringify({base:variants.map(v=>calculateScenario(v)),edited:calculateScenario(edited,delta)}));"
    )
    result = subprocess.run(["node", "-e", node_code, str(path)], check=True, capture_output=True, text=True, timeout=20,
                            input=json.dumps({"variants": [s for _, _, s in rows], "edited": rows[0][2], "delta": delta}))
    node_result = json.loads(result.stdout)
    parity = Parity()
    for (code, v, _), outputs in zip(rows, node_result["base"], strict=True):
        for direction in DIRECTIONS:
            xlsx = xlsx_values[code, v["variant_id"]][direction]
            expected = v["expected_outputs"][direction]
            actual = outputs[direction]
            require(actual.keys() == expected.keys(), f"Выходы JS {code}.{v['variant_id']}.{direction}")
            for key, value in expected.items():
                context = f"JS.{code}.{v['variant_id']}.{direction}"
                parity.check(value, actual[key], context, key)
                parity.check(xlsx[key], actual[key], context + ".vsXLSX", key)
    inputs = {direction: prepared["inputs"][direction] | delta.get(direction, {}) for direction in DIRECTIONS[:2]}
    sides = {d: calculate("CHARTER", i, publish=False) for d, i in inputs.items()}
    cycle = round_trip("CHARTER", **sides, margin_pct=inputs["outbound"]["target_margin_pct"])
    for d, expected in {**sides, "round_trip": cycle}.items():
        for key, value in expected.items():
            parity.check(value, node_result["edited"][d][key], f"Правка JS.{d}", key)
    return {"node_check": "PASS", "offline": True, "base_cases": len(cases),
            "variants": len(rows), "edit_recalculated": True, **parity.report()}


def verify_memo():
    memo = (ROOT / MEMO).read_text(encoding="utf-8")
    headings = re.split(r"^## (.+)$", memo, flags=re.M)
    sections = dict(zip(headings[1::2], headings[2::2], strict=True))
    barriers = sections["Где спроса для отдельной программы нет и главные барьеры"]
    share = len(barriers.split()) / len(memo.split())
    require(75 <= len(memo.splitlines()) <= 115 and share >= 0.30, "Объём меморандума и доля барьеров")
    require(all(code in barriers for code in ("GROUND_ALT", "OWN_FLEET", "ТМС ≠ GAP", "85%", "2 379,56", "150")),
            "Обязательные барьеры меморандума")
    require(len(re.findall(r"^\d\. ", sections["Четыре вывода"], re.M)) == 4 and
            len(re.findall(r"^\d\. ", sections["Две гипотезы к обсуждению"], re.M)) == 2, "Рамка встречи в меморандуме")
    questions = sections["Пять вопросов Red Wings"]
    require(re.findall(r"^(\d)\. \*\*P[012]\.\*\*", questions, re.M) == list("12345") and
            questions.count("?") == 5, "Пять целевых вопросов")
    require("file://" not in memo, "Локальная URI в меморандуме")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", memo)
    require(bool(links), "В меморандуме нужны относительные ссылки")
    for link in links:
        url = urlsplit(link)
        path = unquote(url.path)
        require(not (url.scheme or url.netloc or path.startswith("/")) and (ROOT / path).is_file(),
                f"Неразрешимая относительная ссылка {link}")
    for row in council_scores():
        require("| " + " | ".join(row) + " |" in sections["Оценки Консула"], f"Оценки {row[0]}")
    return {"lines": len(memo.splitlines()), "barriers_pct": round(share * 100, 2),
            "questions": 5, "relative_links": len(links)}


def main():
    report = {"overall_verdict": "FAIL", "P5_FLEET_ECON": "FAIL", "P7_EXPERT_KIT": "FAIL"}
    try:
        require(all((ROOT / name).is_file() for name in REQUIRED), "Отсутствуют файлы Волны 3")
        require(SOFFICE.is_file(), f"LibreOffice недоступен по пути {SOFFICE}")
        for name in REQUIRED:
            if name.endswith(".xlsx"):
                continue
            require(not BANNED_TOKEN.search((ROOT / name).read_text(encoding="utf-8")), f"{name}: устаревший токен")
        registry = load_registry()
        cases = verify_sources(registry)
        report["source_csv"] = verify_csvs(registry, cases)
        with tempfile.TemporaryDirectory(prefix="rw_xlsx_check_") as tmp:
            workdir = Path(tmp)
            values, report["xlsx"] = verify_xlsx(registry, cases, workdir)
            report["P5_FLEET_ECON"] = "PASS"
            dossier = Dossier((ROOT / HTML).read_text(encoding="utf-8"))
            report["html"] = verify_html(dossier, registry, cases, values, workdir)
        report["memo"] = verify_memo()
        report["P7_EXPERT_KIT"] = "PASS"
        report["overall_verdict"] = "PASS"
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            report["stderr"] = error.stderr.strip()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["overall_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
