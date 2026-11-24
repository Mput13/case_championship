#!/usr/bin/env python3
"""Build the nine-sheet expert workbook from the published Wave 3 registry."""

import csv
import json
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as column
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.workbook.properties import CalcProperties

from economics_engine import ASSUMPTIONS_SHEET

ROOT = Path(__file__).resolve().parent
W1 = ROOT.parent / "49_corporate_screening_20261124"
W2 = ROOT.parent / "50_corporate_wave2_20261124"
W3_REGISTRY = ROOT / "model_inputs_registry.json"
OUTPUT = ROOT / "redwings_corporate_model.xlsx"
SHEETS = (
    "0_Executive_Summary", ASSUMPTIONS_SHEET, "2_Pilot1_UFA_NUX",
    "3_Pilot2_Atom_SVX", "4_Pilot3_Innoprom_LED", "5_Fleet_Distance_53",
    "6_Hubs_9_Nodes", "7_Orgs_68_Screening", "8_RW_Questions_5",
)
DIRECTIONS = ("outbound", "inbound", "round_trip")
QUESTION_PRIORITIES = ("P0", "P0", "P1", "P1", "P2")
DATA_PRIORITIES = (
    ("P0", "Себестоимость и исполнение", "DOC и аэропортовые расходы по плечам, ПОО, перегон, резерв, "
     "доступность типов ВС, зимняя нагрузка и запасные, экономика блока по классам и датам "
     "(LF, net yield, доступная квота, release)."),
    ("P1", "Каналы продаж и спрос", "Действующие корпоративные программы, договоры и ТМС, плательщики, "
     "политика замены ФИО, рынки и сезонные окна; требуемый J и возможности 2-классной компоновки."),
    ("P2", "Приоритет следующей итерации", "Горизонт и формат оценки, типы ВС к проверке и уровень "
     "детализации пилотных предложений."),
)
METRICS = {
    "pax": "Летящие пассажиры",
    "offered_price_rub": "Предложенный тариф Y, ₽",
    "quota_seats": "Выделенная квота, мест",
    "j_share_pct": "Доля группы с запросом J, %",
    "payload_seat_haircut_pct": "Зимнее снижение ёмкости, %",
    "displacement_lf_pct": "Вероятность вытеснения Y, %",
    "j_passengers": "Пассажиры с запросом J",
    "allow_y_in_j_seats": "Допуск рассадки Y в J (0 / 1)",
    "effective_seats_per_aircraft": "Эффективная ёмкость на борт, мест",
    "j_cap": "Ёмкость класса J, мест",
    "y_cap_base": "Ёмкость класса Y, мест",
    "j_fits": "Группа J помещается (1 = да)",
    "y_fits": "Группа Y помещается (1 = да)",
    "client_cash_tct_rub": "Клиент · денежный бюджет, ₽/пасс.",
    "client_lost_work_h": "Клиент · потерянное рабочее время, ч/пасс.",
    "client_time_value_rub": "Клиент · стоимость рабочего времени, ₽/пасс.",
    "client_total_tct_rub": "Клиент · суммарный TCT, ₽/пасс.",
    "client_door_to_door_h": "Клиент · время от двери до двери, ч",
    "client_alt_cash_tct_rub": "Альтернатива · денежный бюджет, ₽/пасс.",
    "client_alt_lost_work_h": "Альтернатива · потерянные рабочие часы, ч/пасс.",
    "client_alt_time_value_rub": "Альтернатива · стоимость времени, ₽/пасс.",
    "client_alt_total_tct_rub": "Альтернатива · суммарный TCT, ₽/пасс.",
    "client_alt_door_to_door_h": "Альтернатива · от двери до двери, ч",
    "alt_duration_h": "Альтернатива · время в пути без доплечий, ч",
    "client_max_unit_contract_price_rub": "Клиент · предельная цена места по TCT, ₽",
    "client_tct_savings_vs_alt_rub": "Клиент · экономия против альтернативы, ₽/пасс.",
    "rw_net_revenue_rub": "RW · чистая выручка за окно, ₽",
    "rw_net_contribution_rub": "RW · чистый вклад за окно, ₽",
    "rw_total_flight_cost_rub": "RW · полные затраты на чартер за окно, ₽",
    "rw_break_even_charter_price_rub": "RW · цена безубыточности чартера, ₽",
    "rw_break_even_seat_price_rub": "Безубыт. ср. цена места, ₽",
    "rw_break_even_y_price_rub": "Безубыт. тариф Y, ₽",
    "rw_target_price_per_seat_rub": "RW · цена места с целевой маржой, ₽",
    "rw_doc_max_rub_per_block_h": "RW · DOC_max, ₽/блок-ч",
    "rw_expected_displaced_seats": "RW · ожидаемое вытеснение, мест",
    "rw_displacement_cost_rub": "RW · упущенный вклад от вытеснения, ₽",
    "rw_block_net_contribution_after_displacement_rub": "RW · вклад блока с учётом вытеснения, ₽",
    "operational_screen_pass": "Фильтр ёмкости, класса, дробления и дальности (1 = проходит)",
}
HEAD = PatternFill("solid", fgColor="24374F")
INPUT = PatternFill("solid", fgColor="E3F0FC")
PALE = PatternFill("solid", fgColor="F1F5FA")
NEGATIVE = Font(color="9B352A")
NA = "н/п"
MISSING = "[NEEDS-RW-DATA]"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def load_registry():
    return json.loads(W3_REGISTRY.read_text(encoding="utf-8"))


def council_scores():
    def read_scores(path):
        rows = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("| **"):
                fields = line.split("|")
                member = fields[1].strip().strip("*")
                if member in {"Strategist", "Skeptic", "Quant", "Minimalist"}:
                    rows[member] = re.findall(r"\b\d+/10\b", fields[4])
        return rows

    r0 = read_scores(W1 / "round_0_ledger.md")
    r1 = read_scores(W2 / "round_1_ledger.md")
    if len(r0) != 4 or set(r0) != set(r1) or any(r1[k][0] != v[0] for k, v in r0.items()):
        raise ValueError("Расхождение оценок Консула в журналах R0/R1")
    return [(member, score[0], r1[member][1], "Ожидается после ревью") for member, score in r0.items()]


def ref(sheet, address):
    return f"'{sheet}'!{address}"


def header(ws, values):
    ws.append(values)
    for cell in ws[ws.max_row]:
        cell.fill = HEAD
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
    ws.row_dimensions[ws.max_row].height = 33
    return ws.max_row


def title(ws, text, last_col):
    row = ws.max_row + 1 if ws["A1"].value is not None else 1
    ws.cell(row, 1, text).font = Font(name="Calibri", bold=True, size=15, color="172C46")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    ws.row_dimensions[row].height = 26
    return row


def note(ws, text, last_col, height=36):
    ws.append([text])
    ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=last_col)
    ws.row_dimensions[ws.max_row].height = height


def polish(ws, widths, freeze):
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = freeze
    ws.sheet_view.zoomScale = 90
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3 if len(widths) > 10 else ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[column(i)].width = width
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                cell.alignment = Alignment(vertical="center", wrap_text=True, horizontal=(
                    "left" if isinstance(cell.value, str) and cell.data_type != "f" else "general"
                ))
    ws.sheet_format.defaultRowHeight = 19


def tag(value):
    return {"NEEDS_RW_DATA": "[NEEDS-RW-DATA]", "SCENARIO_MODEL": "[SCENARIO_MODEL]"}.get(value, "")


def metric_format(key):
    if key.endswith("_pct"):
        return '0.0"%"'
    if key.endswith("_rub") or "_rub_per_" in key:
        return '#,##0.00;[Red](#,##0.00);0.00'
    if key.endswith("_h") or "expected_displaced" in key or "distance" in key:
        return "#,##0.00"
    return "#,##0"


def write_assumptions(ws, registry):
    title(ws, "Параметры и источники", 9)
    note(ws, "Голубые ячейки — сценарные входы. Доли заданы в процентных пунктах. "
         "Диапазоны служат для калибровки. Блок-время по геометрии связано с листом флота.", 9)
    first = header(ws, ("param_id", "Параметр", "Единица", "База", "Min", "Max", "source_tag",
                        "evidence_ids", "Ограничение"))
    cells = {}
    binary = DataValidation(type="whole", operator="between", formula1=0, formula2=1, showErrorMessage=True,
                            errorTitle="Допуск рассадки Y в J", error="Введите 0 или 1.")
    ws.add_data_validation(binary)
    for item in registry["assumptions"]:
        key = item["param_id"]
        source_tag = item["source_tag"]
        annotation = " ".join(filter(None, [tag(source_tag), item.get("note_ru")]))
        ws.append([key, item["label_ru"], item["unit"], item["base_value"], item["min_value"],
                   item["max_value"], source_tag, "; ".join(item["evidence_ids"]), annotation])
        row = ws.max_row
        ws.row_dimensions[row].height = 42 if len(key) > 104 or len(annotation) > 119 else 31
        for cell in ws[row][3:6]:
            cell.number_format = '0.0"%"' if item["unit"] == "%" else "#,##0.00"
        if source_tag in {"SCENARIO_MODEL", "NEEDS_RW_DATA"} and not key.endswith(".est_block_time_h"):
            ws[f"D{row}"].fill = INPUT
        if source_tag == "NEEDS_RW_DATA":
            ws[f"G{row}"].font = Font(color="855714")
        address = f"D{row}"
        if item["excel_cell_hint"] != ref(ws.title, address):
            raise ValueError(f"Адрес {key} в реестре: {item['excel_cell_hint']}, в книге: {ref(ws.title, address)}")
        cells[key] = ref(ws.title, f"$D${row}")
        if key.rsplit(".", 1)[-1] == "allow_y_in_j_seats":
            binary.add(address)
    ws.auto_filter.ref = f"A{first}:I{ws.max_row}"
    ws.print_title_rows = f"{first}:{first}"
    polish(ws, [62, 52, 19, 16, 16, 16, 24, 40, 62], "D4")
    return cells


def write_fleet(ws, registry, inputs):
    fleet = registry["fleet_matrix"]
    spec = fleet["distance_spec"]
    pairs = fleet["pairs"]
    req = fleet["fleet_requirements"]
    title(ws, "Дальность и парк", 16)
    note(ws, spec["periods_of_flight_ru"] + " " + spec["notes_ru"], 16)
    pair_first = header(ws, ("Ранг", "Пара аэропортов", "Вылет", "Прилёт", "Городская пара", "Ортодромия, км",
                             "Маршрут × 1,10, км", "Блок, ч", "Группа дальности", "SSJ-95B 100Y",
                             "SJ-100 / ПД-8", "Ту-214", "Дальний тип", "Класс J", "Кластеры", "Условия"))
    pair_cells = {}
    ssj = spec["ssj95b_100y_gc_km"]
    sj = spec["sj100_pd8_gc_km"]["study_envelope_max"]
    tu = spec["tu214_route_km"]["study_envelope_max"]
    for pair in pairs:
        r = ws.max_row + 1
        ortho, route = f"F{r}", f"G{r}"
        ws.append([
            f"=ROWS(F${pair_first + 1}:F{r})", pair["airport_pair"], pair["from_iata"], pair["to_iata"],
            pair["city_pair_id"], pair["gc_distance_km"], f"=ROUND({ortho}*1.10,2)",
            f"=ROUND(0.45+{route}/760,2)",
            f'=IF({ortho}<=900,"LE_900",IF({ortho}<={ssj["fit_max"]},"901_2250",'
            f'IF({ortho}<={ssj["borderline_max"]},"2251_2450",IF({ortho}<=5000,"2451_5000","GT_5000"))))',
            f'=IF({ortho}<={ssj["fit_max"]},"FIT",IF({ortho}<={ssj["borderline_max"]},'
            '"BORDERLINE_PAYLOAD_CHECK","OUT_OF_RANGE"))',
            f'=IF({ortho}<={sj},"CANDIDATE_PERFORMANCE_CHECK","OUT_OF_RANGE")',
            f'=IF({route}<={tu},"CANDIDATE_PERFORMANCE_CHECK","OUTSIDE_STUDY_ENVELOPE")',
            f'=IF({route}>{tu},"SCREEN_WIDEBODY_IF_DEMAND_VALIDATED","NOT_REQUIRED_BY_DISTANCE_SCREEN")',
            pair["j_class_constraint_note"], pair["primary_cluster_context"], pair["fleet_decision_note"],
        ])
        ws.row_dimensions[r].height = 58
        for letter in "FGH":
            ws[f"{letter}{r}"].number_format = "#,##0.00"
        pair_cells[pair["airport_pair"]] = r
    ws.auto_filter.ref = f"A{pair_first}:P{ws.max_row}"
    ws.print_title_rows = f"{pair_first}:{pair_first}"

    title(ws, "Условные потребности при 0, 1, 3 и 5 подтверждённых программах", 16)
    note(ws, req["interpretation_ru"], 16)
    header(ws, ("Программ", "Тип ВС", "Пример пары", "Кресел", "Продукт", "Оборотов в неделю",
                "Окна", "Блок-ч в неделю", "Часы занятости", "Пик ВС", "Активных ВС",
                "С базовым резервом", "С резервом 15%", "С резервом 20%",
                "Доля общего резерва 15%, ВС", "Доля общего резерва 20%, ВС"))
    program_cells = []
    for item in req["program_scenarios"]:
        r = ws.max_row + 1
        plane, route, product = (item[key] for key in ("aircraft_type", "example_airport_pair", "product"))
        block_h = f"H${pair_cells[route]}"
        ground_h = inputs["fleet_ground_times_h"]
        if plane.startswith("Ту-214"):
            ground_h += "+" + inputs["vankor_rfi_min_excess_parking"]
        rotations = inputs.get({"CHARTER": "fleet_charter_rotations_per_week",
                                "REGULAR_ROTATION": "fleet_regular_rotations_per_week"}.get(product), "0")
        ws.append([item["programs_confirmed_assumption"], plane, route, item["nominal_seats_per_aircraft"],
                   product, f"={rotations}", item["window_plan"], f"=A{r}*F{r}*2*{block_h}",
                   f"=A{r}*F{r}*(2*{block_h}+{ground_h})",
                   f'=IF(F{r}=0,0,IF(G{r}="STAGGERED",MIN(1,A{r}),A{r}))',
                   f"=MAX(J{r},ROUNDUP(H{r}/{inputs['fleet_weekly_available_block_h']},0),"
                   f"ROUNDUP(I{r}/{inputs['fleet_weekly_aircraft_occupancy_h']},0))",
                   f"=ROUNDUP(K{r}/(1-{inputs['fleet_reserve_pct']}/100),0)",
                   f"=ROUNDUP(K{r}/0.85,0)", f"=ROUNDUP(K{r}/0.80,0)",
                   f"=ROUND(K{r}/0.85-K{r},2)", f"=ROUND(K{r}/0.80-K{r},2)"])
        ws.row_dimensions[r].height = 31
        for letter in "HIOP":
            ws[f"{letter}{r}"].number_format = "#,##0.00"
        program_cells.append(r)
    polish(ws, [14, 21, 14, 12, 25, 16, 17, 17, 19, 24, 25, 25, 26, 48, 32, 58], "C4")
    return pair_cells, program_cells


def expression(formula, names):
    return re.sub(r"\b[a-z][a-z0-9_]*\b", lambda match: names[match[0]], formula)


def case_code(case):
    return case["case_id"].split("_", 1)[0]


def moment_rows(ws, registry, cases, inputs):
    title(ws, "Двусторонняя экономика", 12)
    rail_note = {
        "P1": " ЖД Уфа → Новый Уренгой — 45 ч 33 мин в пути по срезу EV-W2T1-020. Доплечья считаются отдельно.",
        "P2": " Ориентир 18 ч в пути относится к обратному поезду 049М. Доплечья считаются отдельно.",
    }
    note(ws, "Денежный бюджет и рабочее время клиента показаны на пассажира, вклад RW — за окно или оборот. "
         "Очистка обязательного входа помечает итог плеча и оборота [NEEDS-RW-DATA]. "
         "«н/п» означает, что метрика неприменима к продукту. Все варианты — [SCENARIO_MODEL]."
         + rail_note.get(cases[0]["cluster_id"], ""), 12, height=57)
    first = header(ws, ("Ветка и вариант", "Пара", "Продукт", "Тип ВС", "J вылет / возврат",
                        "Ёмкость · вылет / возврат", "Cash TCT, ₽/пасс. · оборот",
                        "Lost Work, ч/пасс. · оборот", "Вклад RW, ₽ · оборот",
                        "Безубыт. место · вылет", "Безубыт. место · возврат", "Фильтр · вылет / возврат"))
    count = sum(len(c["variants"]) for c in cases)
    for _ in range(count):
        ws.append([" "])
    ws.auto_filter.ref = f"A{first}:L{first + count}"
    ws.print_title_rows = f"{first}:{first}"
    summary = first + 1
    addresses = {}
    for case in cases:
        code = case_code(case)
        title(ws, f"{code} · {case['title_ru']}", 12)
        case_row = ws.max_row + 1
        ws.append(["Статус", case["decision"], "Основание", case["demand_basis"], None, None,
                   "Подтверждённые пассажиры", None, None,
                   "UNKNOWN" if case["confirmed_pax"] is None else case["confirmed_pax"]])
        ws.row_dimensions[case_row].height = 33
        ws.merge_cells(start_row=case_row, start_column=4, end_row=case_row, end_column=6)
        ws.merge_cells(start_row=case_row, start_column=7, end_row=case_row, end_column=9)
        for variant in case["variants"]:
            v_id, mode = variant["variant_id"], variant["mode"]
            start = title(ws, f"{code} · {v_id} · {variant['aircraft_type']}", 12)
            note(ws, variant["condition_ru"], 12)
            note(ws, "Источники · " + "; ".join(variant["evidence_ids"]), 12, height=32)
            header(ws, ("Показатель", "Вылет " + variant["direction_labels"]["outbound"],
                        "Возврат " + variant["direction_labels"]["inbound"], "Оборот",
                        "Идентификатор показателя"))
            guard_row = ws.max_row + 1
            ws.cell(guard_row, 1, "Обязательные входы")
            base = ws.max_row
            direction_spec = registry["formulas_spec"]["directional"][mode]
            input_keys = list(variant["input_param_ids"]["outbound"])
            output_keys = [v["output_id"] for v in direction_spec]
            all_keys = list(dict.fromkeys([k for k in METRICS if k in input_keys or k in output_keys]
                                          + output_keys + input_keys))
            rows = {key: row for row, key in enumerate(all_keys, base + 1)}
            formulas = {v["output_id"]: v["excel_formula"] for v in direction_spec}
            cycle_spec = registry["formulas_spec"]["round_trip"]
            cycle_keys = set(cycle_spec["sum_outputs"][mode])
            precision = registry["formulas_spec"]["precision"]["published_decimals"]
            cycle_ready = f"AND(B{guard_row}=1,C{guard_row}=1)"
            for letter in "BC":
                refs = ",".join(f"{letter}{rows[key]}" for key in input_keys)
                ws[f"{letter}{guard_row}"] = f'=IF(COUNT({refs})={len(input_keys)},1,"{MISSING}")'
            for key in all_keys:
                r = rows[key]
                label = METRICS.get(key)
                if not label and key in input_keys:
                    label = key
                ws.cell(r, 1, label or key)
                ws.cell(r, 5, key)
                for direction, letter in zip(DIRECTIONS[:2], "BC"):
                    if key in formulas:
                        cell_formula = expression(formulas[key], {k: f"{letter}{n}" for k, n in rows.items()})
                        cell_formula = f'=IF({letter}${guard_row}=1,{cell_formula[1:]},"{MISSING}")'
                    else:
                        addr = inputs[variant["input_param_ids"][direction][key]]
                        cell_formula = f'=IF(ISNUMBER({addr}),{addr},"{MISSING}")'
                    ws[f"{letter}{r}"] = cell_formula
                    ws[f"{letter}{r}"].number_format = metric_format(key)
                if key in cycle_keys:
                    ws[f"D{r}"] = f'=IF({cycle_ready},ROUND(SUM(B{r}:C{r}),{precision}),"{MISSING}")'
                elif key == "rw_doc_max_rub_per_block_h":
                    cycle_names = {k: f"B{n}:C{n}" for k, n in rows.items()}
                    cycle_names["target_margin_pct"] = f"B{rows['target_margin_pct']}"
                    cycle_formula = expression(cycle_spec[key], cycle_names)
                    margin = rows["target_margin_pct"]
                    ws[f"D{r}"] = (f'=IF({cycle_ready},IF(B{margin}=C{margin},ROUND({cycle_formula},{precision}),'
                                   f'"Маржа различается"),"{MISSING}")')
                ws[f"D{r}"].number_format = metric_format(key)
                if key in METRICS:
                    ws.row_dimensions[r].height = 29
                    ws[f"A{r}"].fill = PALE
            addresses[(code, v_id)] = (rows, case_row, summary)
            ws[f"A{summary}"] = f"{code} · {v_id}"
            ws[f"A{summary}"].hyperlink = Hyperlink(ref=f"A{summary}", location=ref(ws.title, f"A{start}"))
            ws[f"A{summary}"].font = Font(color="2355A9", underline="single")
            ws[f"B{summary}"] = variant["airport_pair"]
            ws[f"C{summary}"] = mode
            ws[f"D{summary}"] = variant["aircraft_type"]

            def pair_value(key, suffix=""):
                if key not in rows:
                    return NA
                r = rows[key]
                return f'=IF({cycle_ready},B{r}&" / "&C{r}&"{suffix}","{MISSING}")'

            ws[f"E{summary}"] = pair_value("j_share_pct", "%")
            ws[f"F{summary}"] = pair_value("effective_seats_per_aircraft")
            ws[f"L{summary}"] = pair_value("operational_screen_pass")
            for letter, key, leg in (
                ("G", "client_cash_tct_rub", "D"), ("H", "client_lost_work_h", "D"),
                ("I", "rw_net_contribution_rub", "D"), ("J", "rw_break_even_seat_price_rub", "B"),
                ("K", "rw_break_even_seat_price_rub", "C"),
            ):
                ws[f"{letter}{summary}"] = f"={leg}{rows[key]}" if key in rows else NA
                ws[f"{letter}{summary}"].number_format = metric_format(key)
            ws.row_dimensions[summary].height = 42
            summary += 1
    ws.conditional_formatting.add(f"I{first + 1}:I{first + count}",
                                  CellIsRule(operator="lessThan", formula=["0"], font=NEGATIVE))
    polish(ws, [49, 23, 23, 23, 38, 17, 18, 20, 19, 22, 22, 19], "B4")
    return addresses


def write_summary(ws, registry, cases, layouts, fleet_programs):
    title(ws, "Корпоративный спрос Red Wings", 10)
    note(ws, "Срез на 24.11.2026. Публичные сведения подтверждают отдельные связи, исторические запросы "
         "и срезы предложения. Текущий объём в заданном окне и условия контракта требуют подтверждения.", 10)
    header(ws, ("Go на открытых данных", "Порог пар по R0", "Выделенный парк · база, ВС", "Пары с объёмом",
                "Городские пары", "Организации", "Источники", "Кластеры", "Ветки", "Варианты"))
    first, last = 7, 6 + len(cases)
    fleet_base = ref(SHEETS[5], f"L{fleet_programs[0]}")
    variant_counts = [
        f"COUNTA({ref(sheet.title, f'A4:A{3 + count}')})"
        for sheet, _, count in (layouts[name] for name in ("P1", "P2", "P3"))
    ]
    ws.append([f'=COUNTIF(D{first}:D{last},"Go")&"/"&B4&" Go"', registry["meta"]["round0_threshold_pairs"],
               f"={fleet_base}", registry["meta"]["pairs_quantified"],
               len({r["pair_id"] for r in read_csv(W2 / "opportunities.csv") if r["pair_id"]}),
               f"=COUNTA({ref(SHEETS[7], 'A4:A71')})", len(registry["evidence"]),
               registry["meta"]["modeled_clusters"], f"=COUNTA(A{first}:A{last})",
               f"=SUM({','.join(variant_counts)})"])
    ws.row_dimensions[4].height = 26
    note(ws, "Сначала проверить плательщика, число летящих, окно и предложение отдельно по вылету и возврату.", 10)
    header(ws, ("Кластер", "Ветка", "Пара", "Статус", "Продукт", "Cash TCT · оборот",
                "Lost Work · оборот", "Вклад RW · оборот", "Безубыт. место · вылет", "Безубыт. место · возврат"))
    for case in cases:
        sheet, positions, _ = layouts[case["cluster_id"]]
        key = case_code(case), case["default_variant_id"]
        _, status, row = positions[key]
        ws.append([case["cluster_id"], *[f"={ref(sheet.title, address)}" for address in
                   (f"A{row}", f"B{row}", f"B{status}", f"C{row}", f"G{row}", f"H{row}",
                    f"I{row}", f"J{row}", f"K{row}")]])
        ws.row_dimensions[ws.max_row].height = 35
        link = ws[f"B{ws.max_row}"]
        link.hyperlink = Hyperlink(ref=link.coordinate, location=ref(sheet.title, f"A{row}"))
        link.font = Font(color="2355A9", underline="single")
        for letter in "FGHIJ":
            ws[f"{letter}{ws.max_row}"].number_format = "#,##0.00;[Red](#,##0.00);0.00"
    ws.auto_filter.ref = f"A6:J{last}"
    title(ws, "Оценки Консула", 10)
    header(ws, ("Участник", "Раунд 0", "Раунд 1", "Раунд 2"))
    for scores in council_scores():
        ws.append(scores)
    note(ws, "Оценки информационные. Для решений о продукте применяются предикаты и доказательства.", 10)
    polish(ws, [23, 39, 24, 26, 18, 20, 21, 20, 23, 23], "C7")


def write_hubs(ws, registry):
    title(ws, "Девять узлов · регулярный и событийный срезы", 15)
    note(ws, "Геометрия считает пары при перепробеге ≤25% и ≤35%. Наблюдение обоих плеч по разным датам "
         "не подтверждает стыковку под окно или квоту. «Неизвестно» сохраняет отсутствие объёма.", 15)
    first = header(ws, ("Аэропорт", "Город", "Тип недели", "Основание", "Геометрия ≤25%", "Геометрия ≤35%",
                        "Оба плеча ≤25%", "Оба плеча ≤35%", "Связные пары", "Локальные pax · Base",
                        "Транзит 25% · Base", "Транзит 35% · Base", "Событийные pax · Base",
                        "Совместимый пул", "Плательщики"))
    keys = ("hub_iata", "city_name", "week_type", "demand_basis_scope", "geometry_pairs_25",
            "geometry_pairs_35", "observed_transit_pairs_25", "observed_transit_pairs_35",
            "connected_geometry_pairs", "local_od_pax_base", "transit_od_pax_detour25_base",
            "transit_od_pax_detour35_base", "event_peak_od_pax_base", "compatible_pooling_groups",
            "distinct_payers_count")
    for node in registry["hubs_summary"]:
        ws.append([node[k] if node[k] is not None else "Неизвестно" for k in keys])
    ws.auto_filter.ref = f"A{first}:O{ws.max_row}"
    ws.print_title_rows = f"{first}:{first}"
    polish(ws, [12, 24, 18, 28, *[18] * 11], "C4")


def write_organizations(ws, orgs):
    title(ws, "Скрининг 68 организаций", 9)
    note(ws, "Одна строка — одно юрлицо. Статус организации относится к доступной информации "
         "о ней. Сектора и роли сохранены из реестра Волны 2.", 9)
    keys = list(orgs[0])
    first = header(ws, keys)
    status = column(keys.index("status") + 1)
    sector = column(keys.index("sector") + 1)
    for org in orgs:
        ws.append([org[key] for key in keys])
        ws.row_dimensions[ws.max_row].height = 61
    last = ws.max_row
    ws.auto_filter.ref = f"A{first}:{column(len(keys))}{last}"
    ws.print_title_rows = f"{first}:{first}"
    title(ws, "Количество организаций по статусам и секторам", 9)
    header(ws, ("Статус", "Количество", "Сектор", "Количество"))
    buckets = sorted(set(org["sector"] for org in orgs))
    statuses = sorted({org["status"] for org in orgs} | {"Go", "No-Go"})
    for index, value in enumerate(buckets):
        row = ws.max_row + 1
        ws.append([statuses[index] if index < len(statuses) else None,
                   f"=COUNTIF({status}${first + 1}:{status}${last},A{row})" if index < len(statuses) else None,
                   value, f"=COUNTIF({sector}${first + 1}:{sector}${last},C{row})"])
    polish(ws, [29, 16, 49, 29, 25, 23, 18, 29, 23, 24, 20, 20, 24, 23, 25, 23, 61, 61, 46], "D4")


def write_questions(ws, registry):
    title(ws, "Вопросы к встрече 26–27 ноября", 5)
    header(ws, ("Приоритет", "Вопросы Red Wings", "Статус исходных данных"))
    for priority, question in zip(QUESTION_PRIORITIES, registry["rw_5_questions"], strict=True):
        ws.append([priority, question, "[NEEDS-RW-DATA]"])
        ws.row_dimensions[ws.max_row].height = 45
    ws.auto_filter.ref = "A2:C7"
    title(ws, "Приоритеты запроса данных", 5)
    header(ws, ("Приоритет", "Пакет", "Данные RW"))
    for priority, topic, details in DATA_PRIORITIES:
        ws.append([priority, topic, details])
        ws.row_dimensions[ws.max_row].height = 78
    title(ws, "Обезличенный запрос заказчикам", 5)
    note(ws, registry["anonymized_customer_request"], 5, 109)
    polish(ws, [17, 84, 72, 13, 13], "B3")


def build_workbook(registry):
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True)
    executive, assumptions, p1, p2, later, fleet, hubs, org, questions = (
        workbook.create_sheet(name) for name in SHEETS
    )
    inputs = write_assumptions(assumptions, registry)
    pair_cells, program_cells = write_fleet(fleet, registry, inputs)
    for key, address in inputs.items():
        if key.endswith(".est_block_time_h"):
            r = pair_cells[key.split(".")[0]]
            base = assumptions[address.split("!")[-1].replace("$", "")]
            base.value = f"={ref(fleet.title, f'H{r}')}"
            base.comment = Comment("Базовое блок-время связано с ортодромией флот-матрицы.", "Red Wings")
    cases = registry["pilots_and_clusters"]
    by_cluster = {}
    for sheet, clusters in ((p1, ("P1",)), (p2, ("P2",)), (later, ("P3", "C4", "C5"))):
        selected = [case for case in cases if case["cluster_id"] in clusters]
        positions = moment_rows(sheet, registry, selected, inputs)
        layout = (sheet, positions, len(positions))
        for cluster in clusters:
            by_cluster[cluster] = layout
    write_hubs(hubs, registry)
    write_organizations(org, registry["organizations"])
    write_questions(questions, registry)
    write_summary(executive, registry, cases, by_cluster, program_cells)
    return workbook, by_cluster, pair_cells, program_cells


if __name__ == "__main__":
    workbook, *_ = build_workbook(load_registry())
    workbook.save(OUTPUT)
    print(OUTPUT)
