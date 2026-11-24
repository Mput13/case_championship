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
from build_xlsx import DIRECTIONS, MISSING, NA, ROOT, SHEETS, build_workbook, case_code, council_scores, load_registry, read_csv
from economics_engine import CSV_OUTPUTS, calculate, load_sources, make_fleet, round_trip

SOFFICE = Path("/opt/homebrew/bin/soffice")
XLSX = "redwings_corporate_model.xlsx"
HTML = "redwings_corporate_dossier.html"
MEMO = "briefing_memo.md"
REQUIRED = (
    "economics_engine.py", "model_inputs_registry.json", "fleet_and_distance_matrix.csv",
    "pilot_economics_summary.csv", "build_xlsx.py", XLSX, "build_dossier_html.py", HTML, MEMO, "validate_wave3.py",
)
EVENTS = {"FUTURE_CONFIRMED": 4, "FUTURE_PROVISIONAL": 1, "FUTURE_TBD": 6}
P1A_NO_Y_IN_J = "TU214_CHARTER_NO_Y_IN_J"
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
    tables, evidence, future, _ = load_sources()
    matrix, _ = make_fleet(tables)
    require(matrix == registry["fleet_matrix"]["pairs"], "Флот-матрица из исходных данных")
    cases = registry["pilots_and_clusters"]
    require([case_code(c) for c in cases] == ["P1A", "P1B", "P1C", "P2A", "P2B", "P3A", "P3B", "C4", "C5"],
            "Девять веток")
    require(registry["meta"]["open_source_go_count"] == 0 and registry["meta"]["pairs_quantified"] == 0
            and registry["meta"]["round0_threshold_pairs"] == 3
            and registry["fleet_matrix"]["fleet_requirements"]["base_dedicated_aircraft_open_sources"] == 0,
            "Утверждение об объёме или выделенном парке")
    require(all(case["decision"] == "Conditional" and case["demand_basis"] == "STRUCTURAL_HYPOTHESIS"
                and case["confirmed_pax"] is None for case in cases), "Исходные статусы / объём")
    require(len(evidence) == 352 and registry["evidence"] == evidence,
            "Записи доказательств должны совпадать с CSV Волны 2")
    require(registry["organizations"] == tables["organizations_screening_v2"] and
            Counter(o["status"] for o in registry["organizations"]) == {"Conditional": 28, "Insufficient-Evidence": 40},
            "Скрининг 68 организаций")
    opportunities = tables["opportunities"]
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
    require(registry["events_2027_future"] == future, "События из FUTURE_*")
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
    variant_count = 0
    for case, row in zip(cases, rows, strict=True):
        require(row["case_id"] == case["case_id"] and row["decision"] == "Conditional"
                and row["demand_basis"] == "STRUCTURAL_HYPOTHESIS" and row["confirmed_pax"] == ""
                and row["source_tag"] == registry["meta"]["model_status"]
                and row["confirmation_status"] == registry["meta"]["confirmation_status"],
                f"{row['case_id']}: классификация")
        evidence = row["evidence_ids"].split(";")
        require(evidence == case["evidence_ids"] and set(evidence) <= registry["evidence"].keys(),
                f"{row['case_id']}: доказательства CSV")
        if case_code(case) == "P1B":
            require("EV-W13-003" not in evidence, "P1B: ошибочная привязка EV-W13-003")
        variants = json.loads(row["variant_controls_json"])
        require(isinstance(variants, list) and len(variants) == len(case["variants"]) - 1,
                f"{row['case_id']}: варианты CSV")
        for saved, variant in zip(variants, case["variants"][1:], strict=True):
            keys = ("variant_id", "mode", "airport_pair", "aircraft_type", "gc_distance_km")
            outputs = {d: {k: v for k, v in metrics.items() if k in CSV_OUTPUTS}
                       for d, metrics in variant["expected_outputs"].items()}
            require(saved == {**{k: variant[k] for k in keys}, "expected_outputs": outputs},
                    f"{row['case_id']}.{variant['variant_id']}: содержимое вариантов CSV")
            variant_count += 1
        expected = case["expected_outputs"]
        for direction in DIRECTIONS:
            for key, value in expected[direction].items():
                field = f"{direction}_{key}"
                if field in row:
                    parity.check(value, float(row[field]), row["case_id"], field)
    return {"load_sources": "PASS", "make_fleet": "PASS", "pilot_tags_and_evidence": "PASS",
            "csv_variants_checked": variant_count, **parity.report()}


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
    assumptions = workbook[SHEETS[1]]
    input_cells = {row[0].value: row[3] for row in assumptions.iter_rows(min_row=4, max_col=4)}
    require(len(input_cells) == assumptions.max_row - 3 == len(registry["assumptions"]), "Число строк параметров")
    cases_by_code = {case_code(case): case for case in cases}
    executive_rows = {case_code(case): row for row, case in enumerate(cases, 7)}

    def model_cells(code, variant_id=None):
        case = cases_by_code[code]
        variant_id = variant_id or case["default_variant_id"]
        variant = next(v for v in case["variants"] if v["variant_id"] == variant_id)
        sheet, layout, _ = layouts[case["cluster_id"]]
        positions, _, summary = layout[(code, variant_id)]
        return variant, sheet.title, positions, summary

    def input_address(code, key, direction="outbound", variant_id=None):
        variant, *_ = model_cells(code, variant_id)
        return variant["input_param_ids"][direction][key]

    def save_edit(name, changes):
        path = workdir / (name + ".xlsx")
        previous = {param: input_cells[param].value for param in changes}
        for param, value in changes.items():
            input_cells[param].value = value
        workbook.save(path)
        for param, value in previous.items():
            input_cells[param].value = value
        return path

    def result(book, code, metric, leg="B", variant_id=None):
        _, sheet, positions, _ = model_cells(code, variant_id)
        return live_cell(workbook, book, sheet, f"{leg}{positions[metric]}")

    edit_key = "doc_per_block_h_rub"
    param = input_address("P1A", edit_key)
    edited_value = input_cells[param].value + 10000
    changed_xlsx = save_edit("expert_edit", {param: edited_value})
    displacement = input_address("P3A", "displacement_lf_pct")
    require(displacement != input_address("P3A", "displacement_lf_pct", "inbound"), "Независимые входы плеч P3A")
    # Copy only the workbook, and exercise missing inputs for each product and fleet table.
    blank_xlsx = save_edit("missing_inputs", {displacement: None, param: None,
        input_address("P1B", "offered_price_rub", variant_id="PUBLIC_FARE_VS_RAIL"): None,
        "fleet_charter_rotations_per_week": None})
    fleet_denom_xlsx = save_edit("missing_fleet_denom", {"fleet_weekly_available_block_h": None})
    y_thresholds = {}
    for code in ("P2B", "C5"):
        variant, *_ = model_cells(code)
        for direction in DIRECTIONS[:2]:
            threshold = variant["expected_outputs"][direction]["rw_break_even_y_price_rub"]
            y_thresholds[input_address(code, "offered_price_rub", direction)] = threshold
    p2b_sj_quota = input_address("P2B", "quota_seats", variant_id="SVX_UFA_SJ100_J_J4")
    screen_edit = {displacement: 0, input_address("P1A", "allow_y_in_j_seats"): 0,
                   input_address("P3B", "screen_distance_limit_km"): 2355, p2b_sj_quota: 100}
    screen_xlsx = save_edit("zero_and_filters", screen_edit | y_thresholds)
    original, edited, blank, fleet_denom, screen = recalculate(
        workdir, ROOT / XLSX, changed_xlsx, blank_xlsx, fleet_denom_xlsx, screen_xlsx)
    calculated = load_workbook(original, data_only=True)
    inputs_after_edit = load_workbook(edited, data_only=True)
    cleared = load_workbook(blank, data_only=True)
    cleared_denom = load_workbook(fleet_denom, data_only=True)
    screening = load_workbook(screen, data_only=True)
    error_cells = [error for book in (calculated, inputs_after_edit, cleared, cleared_denom, screening) for error in errors(book)]
    require(not error_cells, f"Ошибки формул Excel: {error_cells[:20]}")
    fleet_charter_row = next(r for program, r in zip(registry["fleet_matrix"]["fleet_requirements"]["program_scenarios"],
                                                     program_rows, strict=True)
                             if program["programs_confirmed_assumption"] == 1 and program["product"] == "CHARTER")
    require(all(cleared[SHEETS[5]][f"{col}{fleet_charter_row}"].value == MISSING for col in "FHIJKLMNOP"),
            "R2-P0-2: пустой вход оборотов парка не должен давать 0 ВС")
    require(all(cleared_denom[SHEETS[5]][f"{col}{fleet_charter_row}"].value == MISSING for col in "KLMNOP"),
            "R2-P0-2: пустой знаменатель блок-часов парка не должен давать #DIV/0!")
    blank_fields = ("rw_net_contribution_rub", "rw_break_even_seat_price_rub", "client_total_tct_rub")
    for code in ("P3A", "P1A"):
        for field in blank_fields:
            require(result(cleared, code, field) == MISSING, f"{code}: пустой вход в {field}")
        for field in ("rw_net_contribution_rub", "client_total_tct_rub"):
            require(result(cleared, code, field, "D") == MISSING, f"{code}: пустой вход в обороте {field}")
        _, sheet, _, summary = model_cells(code)
        require(all(cleared[sheet][f"{col}{summary}"].value == MISSING for col in "EFGHIJL"),
                f"{code}: сводка пилота при пустом входе")
        require(all(cleared[SHEETS[0]][f"{col}{executive_rows[code]}"].value == MISSING for col in "FGHI"),
                f"{code}: общая сводка при пустом входе")
    for leg in "BD":
        require(result(cleared, "P1A", "rw_doc_max_rub_per_block_h", leg) == MISSING, "Пустой DOC на чартере")
        require(result(cleared, "P1B", "client_total_tct_rub", leg, "PUBLIC_FARE_VS_RAIL") == MISSING,
                "Пустой тариф TICKET")
    p3a, _, _, _ = model_cells("P3A")
    intact = p3a["expected_outputs"]["inbound"]["rw_net_contribution_rub"]
    require(round(result(cleared, "P3A", "rw_net_contribution_rub", "C"), 2) == intact,
            "У P3A пустой вылет блокирует независимый возврат")
    explicit_zero = calculate("BLOCK", p3a["inputs"]["outbound"] | {"displacement_lf_pct": 0})
    zero_contribution = round(result(screening, "P3A", "rw_net_contribution_rub"), 2)
    require(zero_contribution == explicit_zero["rw_net_contribution_rub"] > 0, "P3A: явный ноль вытеснения")

    allowed, _, _, _ = model_cells("P1A")
    disallowed, _, _, _ = model_cells("P1A", P1A_NO_Y_IN_J)
    for direction, leg in zip(DIRECTIONS[:2], "BC", strict=True):
        for option, flag in ((allowed, 1), (disallowed, 0)):
            inputs = option["inputs"][direction]
            require((inputs["pax"], inputs["aircraft_seats"], inputs["j_seats_per_aircraft"],
                     inputs["j_share_pct"], inputs["allow_y_in_j_seats"]) == (150, 164, 16, 0, flag), "Параметры P1A")
            calculated_leg = calculate("CHARTER", inputs)
            require((calculated_leg["y_cap_base"], calculated_leg["y_passengers"], calculated_leg["j_fits"],
                     calculated_leg["y_fits"], calculated_leg["operational_screen_pass"]) == (148, 150, 1, flag, flag),
                    f"Python: поклассовый фильтр P1A {direction}")
            require(result(calculated, "P1A", "operational_screen_pass", leg, option["variant_id"]) == flag,
                    f"Excel: поклассовый фильтр P1A {direction}")
    require(result(screening, "P1A", "operational_screen_pass") == 0
            and result(screening, "P1A", "operational_screen_pass", "C") == 1,
            "Excel: переключение допуска Y в J")
    require(result(screening, "P3B", "distance_fit") == result(screening, "P3B", "operational_screen_pass") == 0,
            "Excel: фильтр дальности")
    p2b_sj, _, _, _ = model_cells("P2B", "SVX_UFA_SJ100_J_J4")
    p2b_sj_overflow = calculate("BLOCK", p2b_sj["inputs"]["outbound"] | {"quota_seats": 100})
    require(p2b_sj_overflow["rw_inventory_screen_pass"] == p2b_sj_overflow["operational_screen_pass"] == 0,
            "Python: R2-P0-1 квота блока по классу Y")
    require(result(screening, "P2B", "rw_inventory_screen_pass", "B", "SVX_UFA_SJ100_J_J4") == 0
            and result(screening, "P2B", "operational_screen_pass", "B", "SVX_UFA_SJ100_J_J4") == 0,
            "Excel: R2-P0-1 квота блока по классу Y")
    for code in ("P2B", "C5"):
        require(all(result(screening, code, "rw_net_contribution_rub", leg) == 0 for leg in "BCD"),
                f"Excel: вклад {code} при безубыточном тарифе Y")
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
        for col, direction, field in (
            ("F", "round_trip", "client_cash_tct_rub"), ("G", "round_trip", "client_lost_work_h"),
            ("H", "round_trip", "rw_net_contribution_rub"), ("I", "outbound", "rw_break_even_seat_price_rub"),
            ("J", "inbound", "rw_break_even_seat_price_rub"),
        ):
            parity.check(case["expected_outputs"][direction].get(field, NA), calculated[SHEETS[0]][f"{col}{index}"].value,
                         f"Сводка {code}.{direction}", field)
    variant_inputs = allowed["inputs"]["outbound"] | {edit_key: edited_value}
    expected_edit = calculate("CHARTER", variant_inputs)["rw_total_flight_cost_rub"]
    parity.check(expected_edit, result(inputs_after_edit, "P1A", "rw_total_flight_cost_rub"), "Изменение DOC", "cost_rub")
    changed_directions = {"outbound": calculate("CHARTER", variant_inputs, publish=False)}
    param_in = input_address("P1A", edit_key, "inbound")
    changed_directions["inbound"] = calculate("CHARTER", allowed["inputs"]["inbound"] |
                                               ({edit_key: edited_value} if param_in == param else {}), publish=False)
    edit_cycle = round_trip("CHARTER", **changed_directions, margin_pct=variant_inputs["target_margin_pct"])
    parity.check(edit_cycle["rw_net_contribution_rub"], inputs_after_edit[SHEETS[0]]["H7"].value,
                 "Сводка после изменения DOC", "contribution_rub")
    executive = calculated[SHEETS[0]]
    require([executive[x].value for x in ("A4", "C4", "D4", "E4", "F4", "G4", "H4", "I4", "J4")] ==
            ["0/3 Go", 0, 0, 30, 68, 352, 5, 9, sum(len(c["variants"]) for c in cases)], "Сводные показатели")
    require([executive[x].value for x in ("I6", "J6")] == ["Безубыт. место · вылет", "Безубыт. место · возврат"],
            "Безубыточные цены в сводке Excel")
    params = calculated[SHEETS[1]]
    for item, r in zip(registry["assumptions"], range(4, assumptions.max_row + 1), strict=True):
        require(params[f"A{r}"].value == item["param_id"] and params[f"G{r}"].value == item["source_tag"]
                and (params[f"H{r}"].value or "") == "; ".join(item["evidence_ids"]), f"Параметр {r}")
        actual = input_cells[item["param_id"]]
        require(item["excel_cell_hint"] == f"'{assumptions.title}'!{actual.coordinate}",
                f"Несовпадение excel_cell_hint для {item['param_id']}")
        for column, key in (("D", "base_value"), ("E", "min_value"), ("F", "max_value")):
            parity.check(item[key], params[f"{column}{r}"].value, item["param_id"], key)
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
    return values, {"formula_errors": 0, "live_formulas": count, "edit_recalculated": True,
                    "excel_cell_hints_checked": len(input_cells), "excel_cell_hints_match_pct": 100,
                    "blank_required_inputs": "PASS", "p3a_blank_contribution": MISSING,
                    "p3a_blank_executive_contribution": MISSING, "p3a_explicit_zero_contribution_rub": zero_contribution,
                    "p1a_class_screen_python_and_excel": {"allow_y_in_j_0": 0, "allow_y_in_j_1": 1},
                    "range_screen": "PASS", "mixed_block_break_even_y": "PASS", **parity.report()}


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
    defaults = {}
    for case, embedded in zip(cases, data["cases"], strict=True):
        require(all(embedded[k] == case[k] for k in ("case_id", "demand_basis", "decision", "confirmed_pax")) and
                embedded["code"] == case_code(case), "Доказательность сценариев в досье")
        defaults[embedded["code"]] = embedded["variants"][0]
        for v, scenario in zip(case["variants"], embedded["variants"], strict=True):
            require(all(v[k] == scenario[k] for k in ("variant_id", "mode", "inputs", "input_param_ids")),
                    f"{v['variant_id']}: входы встроенного расчёта")
            rows.append((embedded["code"], v, scenario))
    p1a, p3a, p3b = (defaults[code] for code in ("P1A", "P3A", "P3B"))
    p2b_sj_html = next(s for code, _, s in rows if code == "P2B" and s["variant_id"] == "SVX_UFA_SJ100_J_J4")
    edits = {
        "doc": (p1a, {"outbound": {"doc_per_block_h_rub": p1a["inputs"]["outbound"]["doc_per_block_h_rub"] + 10000}}),
        "ferry": (p1a, {"outbound": {"ferry_factor": 0.25}}),
        "y_in_j": (p1a, {"outbound": {"allow_y_in_j_seats": 0}}),
        "range": (p3b, {"outbound": {"screen_distance_limit_km": 2355}}),
        "price": (p3a, {"outbound": {"offered_price_rub": 20000}}),
        "yield": (p3a, {"outbound": {"market_net_yield_rub": 15000}}),
        "quota_y_overflow": (p2b_sj_html, {"outbound": {"quota_seats": 100}}),
    }
    for case in cases:
        code = case_code(case)
        if code in ("P2B", "C5"):
            edits[code] = (defaults[code], {d: {"offered_price_rub": case["expected_outputs"][d]["rw_break_even_y_price_rub"]}
                                          for d in DIRECTIONS[:2]})
    node_code = (
        "const {calculateScenario}=require(process.argv[1]);"
        "const {variants,edits}=JSON.parse(require('node:fs').readFileSync(0,'utf8'));"
        "const edited=Object.fromEntries(Object.entries(edits).map(([label,[v,delta]])=>[label,calculateScenario(v,delta)]));"
        "console.log(JSON.stringify({base:variants.map(v=>calculateScenario(v)),edited}));"
    )
    result = subprocess.run(["node", "-e", node_code, str(path)], check=True, capture_output=True, text=True, timeout=20,
                            input=json.dumps({"variants": [s for _, _, s in rows], "edits": edits}))
    node_result = json.loads(result.stdout)
    parity = Parity()
    for (code, v, _), outputs in zip(rows, node_result["base"], strict=True):
        if code == "P1A":
            flag = 0 if v["variant_id"] == P1A_NO_Y_IN_J else 1
            require(all((outputs[d]["y_cap_base"], outputs[d]["y_passengers"], outputs[d]["j_fits"],
                         outputs[d]["y_fits"], outputs[d]["operational_screen_pass"]) == (148, 150, 1, flag, flag)
                        for d in DIRECTIONS[:2]), f"JS: поклассовый фильтр {v['variant_id']}")
        for direction in DIRECTIONS:
            xlsx = xlsx_values[code, v["variant_id"]][direction]
            expected = v["expected_outputs"][direction]
            actual = outputs[direction]
            require(actual.keys() == expected.keys(), f"Выходы JS {code}.{v['variant_id']}.{direction}")
            for key, value in expected.items():
                context = f"JS.{code}.{v['variant_id']}.{direction}"
                parity.check(value, actual[key], context, key)
                parity.check(xlsx[key], actual[key], context + ".vsXLSX", key)
    edited = node_result["edited"]
    for label, (variant, delta) in edits.items():
        mode = variant["mode"]
        inputs = {d: variant["inputs"][d] | delta.get(d, {}) for d in DIRECTIONS[:2]}
        sides = {d: calculate(mode, i, publish=False) for d, i in inputs.items()}
        cycle = round_trip(mode, **sides, margin_pct=inputs["outbound"]["target_margin_pct"])
        for d, expected in {**sides, "round_trip": cycle}.items():
            for key, value in expected.items():
                parity.check(value, edited[label][d][key], f"Правка JS.{label}.{d}", key)
        if label in ("P2B", "C5"):
            require(all(edited[label][d]["rw_net_contribution_rub"] == 0 for d in DIRECTIONS)
                    and all(side["rw_net_contribution_rub"] == 0 for side in sides.values()),
                    f"Python и JS: вклад {label} при безубыточном Y")
    require(edited["y_in_j"]["outbound"]["operational_screen_pass"] == 0
            and edited["y_in_j"]["inbound"]["operational_screen_pass"] == 1, "JS: переключение допуска Y в J")
    require(edited["range"]["outbound"]["operational_screen_pass"] == 0, "JS: фильтр дальности")
    require(edited["quota_y_overflow"]["outbound"]["rw_inventory_screen_pass"] == 0
            and edited["quota_y_overflow"]["outbound"]["operational_screen_pass"] == 0,
            "JS: R2-P0-1 квота блока по классу Y")
    forum_base = next(c for c in cases if case_code(c) == "P3A")["expected_outputs"]["outbound"]
    new_contribution = edited["price"]["outbound"]["rw_net_contribution_rub"]
    require(forum_base["rw_net_contribution_rub"] < 0 < new_contribution, "JS: изменение знака вклада P3A при цене 20 000")
    require(edited["yield"]["outbound"]["rw_displacement_cost_rub"] < forum_base["rw_displacement_cost_rub"],
            "JS: сценарная стоимость вытеснения P3A")
    return {"node_check": "PASS", "offline": True, "base_cases": len(cases),
            "variants": len(rows), "edit_recalculated": True,
            "p1a_class_screen_js": {"allow_y_in_j_0": 0, "allow_y_in_j_1": 1}, "range_screen": "PASS",
            "mixed_block_break_even_y": "PASS", "p3a_contribution_at_y_price_20000_rub": new_contribution,
            "market_net_yield_and_ferry_edits": "PASS", **parity.report()}


def verify_memo(registry, cases):
    memo = (ROOT / MEMO).read_text(encoding="utf-8")
    headings = re.split(r"^## (.+)$", memo, flags=re.M)
    sections = dict(zip(headings[1::2], headings[2::2], strict=True))
    barriers = sections["Где спроса для отдельной программы нет и главные барьеры"]
    share = len(barriers.split()) / len(memo.split())
    require(75 <= len(memo.splitlines()) <= 115 and share >= 0.30, "Объём меморандума и доля барьеров")
    require(all(code in barriers for code in ("GROUND_ALT", "OWN_FLEET", "ТМС ≠ GAP", "150")),
            "Обязательные барьеры меморандума")
    def display(value, digits=0):
        return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",").replace("-", "−")

    p3a = next(c for c in cases if case_code(c) == "P3A")
    forum = next(block for block in barriers.split("\n- ") if block.startswith("**Блок ИННОПРОМ"))
    numeric_text = r"−?\d+(?: \d{3})*(?:,\d+)?"
    expected = [display(p3a["inputs"]["outbound"]["displacement_lf_pct"])]
    for field in ("rw_net_contribution_rub", "rw_break_even_seat_price_rub"):
        expected.extend(display(p3a["expected_outputs"][d][field]) for d in DIRECTIONS[:2])
    require(re.findall(numeric_text, forum) == expected, f"Цифры ИННОПРОМ в меморандуме: {expected}")
    led_nux = next(pair for pair in registry["fleet_matrix"]["pairs"] if pair["airport_pair"] == "LED-NUX")
    led_barrier = next(block for block in barriers.split("\n- ") if block.startswith("**LED ↔ NUX"))
    require(f"Ортодромия {display(led_nux['gc_distance_km'], 2)} км" in led_barrier, "Ортодромия LED–NUX в меморандуме")
    meta = registry["meta"]
    verdict = f"{meta['open_source_go_count']}/{meta['round0_threshold_pairs']} Go"
    require(sections["Четыре вывода"].lstrip().startswith(f"1. **{verdict} "), "Go в меморандуме")
    charter = next(block for block in barriers.split("\n- ") if block.startswith("**SSJ100 100Y"))
    require(all(value in charter for value in ("≥150 мест", "≥700 кг", "../46_corporate_pilot_ufa_nux.md", "EV-W13-001",
                                               "карточку запроса", "ТЗ был недоступен", "повторной сверки")),
            "Атрибуция архивного ТЗ в меморандуме")
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
            "questions": 5, "relative_links": len(links), "key_values_checked": len(expected) + 2,
            "archived_tender_attribution": "PASS"}


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
        report["memo"] = verify_memo(registry, cases)
        report["P7_EXPERT_KIT"] = "PASS"
        report["overall_verdict"] = "PASS"
    except (ValueError, OSError, KeyError, StopIteration, subprocess.SubprocessError) as error:
        report["error"] = str(error)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            report["stderr"] = error.stderr.strip()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["overall_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
