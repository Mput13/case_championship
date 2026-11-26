#!/usr/bin/env python3
"""Build 7-slide executive presentation (PPTX + PDF) for Lidiya Shadrina (Red Wings).

Covers the 4 requested sections from 26.11.2026:
  1) Task & success criteria
  2) Step-by-step plan / research logic
  3) Current verified results as of 26.11.2026 (facts, regional clusters excl. MOW/LED, ranking)
  4) Next step by 03.12.2026 (high-level, without excessive detail)
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

MODEL_DIR = Path(
    "/Users/a/.t3/userdata/providers/antigravity/"
    "ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/"
    "antigravity-acp/brain/0e170297-505d-4a90-975e-911871c12ad1/scratch/rew_wings"
)
GEOJSON = Path(
    "/Users/a/agent-audit-2026-09/case_championship/"
    "context/56_corporate_clients_dossier_20261126/russia_ne110m.geojson"
)
OUT_DIR = Path(
    "/Users/a/agent-audit-2026-09/case_championship/"
    "context/57_presentation_for_lidiya_20261126"
)
OUT_PPTX = OUT_DIR / "Red_Wings_Corporate_Demand_Logic_20261126.pptx"

# Palette (clean editorial Red Wings)
BG = RGBColor(0xF8, 0xF7, 0xF4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x17, 0x21, 0x2B)
MUTED = RGBColor(0x55, 0x62, 0x70)
LINE = RGBColor(0xDC, 0xD6, 0xCA)
RW_RED = RGBColor(0xC8, 0x37, 0x2D)
RW_RED_SOFT = RGBColor(0xFD, 0xF0, 0xEF)
BLUE = RGBColor(0x1E, 0x4F, 0x8A)
BLUE_SOFT = RGBColor(0xEE, 0xF4, 0xFC)
GREEN = RGBColor(0x15, 0x7A, 0x4C)
GREEN_SOFT = RGBColor(0xEB, 0xF7, 0xF1)
AMBER = RGBColor(0xB4, 0x53, 0x09)
AMBER_SOFT = RGBColor(0xFD, 0xF6, 0xE7)
DARK_SLATE = RGBColor(0x1F, 0x2A, 0x37)

FONT = "DejaVu Sans"

# Albers projection for Russia
_PHI1, _PHI2, _PHI0, _LAM0 = (
    math.radians(52.0), math.radians(64.0), math.radians(58.0), math.radians(100.0)
)
_N = 0.5 * (math.sin(_PHI1) + math.sin(_PHI2))
_C = math.cos(_PHI1) ** 2 + 2.0 * _N * math.sin(_PHI1)
_RHO0 = math.sqrt(_C - 2.0 * _N * math.sin(_PHI0)) / _N


def albers(lat: float, lon: float) -> tuple[float, float]:
    if lon < -100.0:
        lon += 360.0
    phi, lam = math.radians(lat), math.radians(lon)
    theta = _N * (lam - _LAM0)
    rho = math.sqrt(max(1e-9, _C - 2.0 * _N * math.sin(phi))) / _N
    return rho * math.sin(theta), _RHO0 - rho * math.cos(theta)


def load_csv(rel: str) -> list[dict[str, str]]:
    with (MODEL_DIR / rel).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_charts(assets_dir: Path) -> tuple[Path, Path, Path]:
    assets_dir.mkdir(parents=True, exist_ok=True)

    # --- Chart 1: Data coverage & open-data ceiling ---
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(6.4, 3.65), dpi=260)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    labels = [
        "Площадки: город (910/937)",
        "Организации: ЭТП (36/48)",
        "Организации: штат (30/48)",
        "Площадки: функция (419/937)",
        "Структура штата групп (13/48)",
        "Пары: прямые рейсы (21/184)",
        "Пары: рублёвый тариф (15/184)",
        "Пары: годовой поток (8/184)",
        "Структура штата заводов (11/937)",
    ][::-1]
    vals = [97.1, 75.0, 62.5, 44.7, 27.1, 11.4, 8.2, 4.3, 1.2][::-1]
    colors = [
        "#C8372D", "#C8372D", "#D97706", "#D97706",
        "#1E4F8A", "#1E4F8A", "#157A4C", "#157A4C", "#157A4C"
    ]

    bars = ax.barh(labels, vals, color=colors, height=0.62, edgecolor="none")
    ax.set_xlim(0, 114)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#DCD6CA")
    ax.spines["bottom"].set_color("#DCD6CA")
    ax.xaxis.grid(True, linestyle="--", alpha=0.35, color="#9AA4B0")
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelsize=8.6, colors="#17212B")
    ax.tick_params(axis="x", labelsize=8.0, colors="#556270")
    ax.set_xlabel("Доля заполненных записей в открытых источниках, %", fontsize=8.3, color="#556270")

    for bar, v in zip(bars, vals):
        ax.text(
            v + 1.8, bar.get_y() + bar.get_height() / 2,
            f"{v:.1f}%", va="center", ha="left", fontsize=8.4, fontweight="bold", color="#17212B"
        )

    plt.tight_layout(pad=0.6)
    c1_path = assets_dir / "chart_coverage.png"
    fig.savefig(c1_path, dpi=260)
    plt.close(fig)

    # --- Chart 2A (separate): Russia regional clusters map (excl. MOW & LED) ---
    air = load_csv("data/model/fact_airports.csv")
    city_to_iata = {}
    iata_coord = {}
    for r in air:
        city = r["Город"].strip()
        code = r["Код ИАТА"].strip()
        if city and code:
            city_to_iata[city] = code
        if code and r["Широта"] and r["Долгота"] and code not in iata_coord:
            iata_coord[code] = (float(r["Широта"].replace(",", ".")), float(r["Долгота"].replace(",", ".")))

    sites = load_csv("data/model/dim_sites.csv")
    iata_sites = Counter()
    iata_orgs = defaultdict(set)
    for s in sites:
        c = s["Город"].strip()
        code = city_to_iata.get(c, "")
        if code in ("SVO", "DME", "VKO", "ZIA") or c == "Москва":
            continue
        if code == "LED" or c == "Санкт-Петербург":
            continue
        if code and code in iata_coord:
            iata_sites[code] += 1
            iata_orgs[code].add(s["Org_ID"].strip())

    fig, ax_m = plt.subplots(figsize=(5.1, 3.85), dpi=260)
    fig.patch.set_facecolor("#FFFFFF")
    ax_m.set_facecolor("#EEF3F8")
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    polys = geo["geometry"]["coordinates"]
    all_x, all_y = [], []
    for poly in polys:
        for ring in poly:
            if len(ring) < 3:
                continue
            pts = [albers(lat, lon) for lon, lat in ring]
            if any(abs(pts[i][0] - pts[i - 1][0]) > 0.35 for i in range(1, len(pts))):
                continue
            all_x.extend(p[0] for p in pts)
            all_y.extend(p[1] for p in pts)
            ax_m.add_patch(Polygon(pts, closed=True, facecolor="#FDFCF9", edgecolor="#B8C2CC", linewidth=0.6))

    ax_m.set_xlim(min(all_x) - 0.04, max(all_x) + 0.05)
    ax_m.set_ylim(min(all_y) - 0.07, max(all_y) + 0.05)
    ax_m.set_aspect("equal")
    ax_m.axis("off")

    multi_pairs = [
        ("NUX", "UFA", "#C8372D", 2.0),
        ("KJA", "SVX", "#C8372D", 1.8),
        ("IKT", "TLK", "#1E4F8A", 1.5),
        ("BQS", "TJM", "#1E4F8A", 1.5),
        ("BQS", "GOJ", "#1E4F8A", 1.4),
    ]
    for a, b, col, lw in multi_pairs:
        if a in iata_coord and b in iata_coord:
            xa, ya = albers(*iata_coord[a])
            xb, yb = albers(*iata_coord[b])
            ax_m.plot([xa, xb], [ya, yb], color=col, linewidth=lw, alpha=0.82, zorder=3)

    for code, _ in iata_sites.most_common(45):
        x, y = albers(*iata_coord[code])
        cnt = iata_sites[code]
        norg = len(iata_orgs[code])
        col = "#C8372D" if norg >= 9 else ("#1E4F8A" if norg >= 5 else "#6B7885")
        ax_m.scatter([x], [y], s=18 + cnt * 6.0, c=col, alpha=0.84, edgecolors="#FFFFFF", linewidths=0.8, zorder=4)

    # Carefully placed non-overlapping callouts with leader arrows where dense
    callouts = [
        ("GOJ", (-0.06, 0.11), "GOJ Н.Новг (24)", "left"),
        ("KUF", (-0.11, -0.09), "KUF Самара (27)", "left"),
        ("SVX", (0.02, 0.09), "SVX Екб (29)", "left"),
        ("UFA", (0.05, -0.09), "UFA Уфа (14)", "left"),
        ("NUX", (0.03, 0.05), "NUX Н.Уренг (8)", "left"),
        ("OVB", (-0.01, -0.09), "OVB Новосиб (12)", "center"),
        ("KJA", (-0.01, 0.11), "KJA Красн (10)", "center"),
        ("IKT", (0.01, -0.09), "IKT Иркутск (8)", "center"),
        ("KHV", (-0.01, 0.10), "KHV Хаб (11)", "center"),
        ("VVO", (-0.05, -0.07), "VVO Влад (11)", "right"),
    ]
    for code, (dx, dy), txt, ha in callouts:
        if code in iata_coord:
            x, y = albers(*iata_coord[code])
            ax_m.annotate(
                txt, xy=(x, y), xytext=(x + dx, y + dy),
                ha=ha, va="center", fontsize=6.8, fontweight="bold", color="#17212B",
                bbox=dict(boxstyle="round,pad=0.16", fc="#FFFFFF", ec="#D5D0C5", lw=0.5, alpha=0.92),
                arrowprops=dict(arrowstyle="-", color="#7A8694", lw=0.65),
                zorder=5
            )
    ax_m.set_title("География площадок вне Москвы и СПб", fontsize=9.5, fontweight="bold", color="#17212B", pad=6)
    plt.tight_layout(pad=0.3)
    c2_map_path = assets_dir / "chart_map_ru.png"
    fig.savefig(c2_map_path, dpi=260)
    plt.close(fig)

    # --- Chart 2B (separate): Top-10 operational regional hubs ---
    fig, ax_b = plt.subplots(figsize=(3.55, 3.85), dpi=260)
    fig.patch.set_facecolor("#FFFFFF")
    ax_b.set_facecolor("#FFFFFF")
    top10 = [
        ("SVX · Екб", 29, 13),
        ("KUF · Самара", 27, 12),
        ("GOJ · Н.Новг", 24, 11),
        ("KLF · Калуга", 18, 9),
        ("UFA · Уфа", 14, 7),
        ("KGD · Калин.", 14, 8),
        ("PEE · Пермь", 14, 5),
        ("OVB · Новосиб.", 12, 8),
        ("KHV · Хабар.", 11, 9),
        ("KJA · Красн.", 10, 7),
    ][::-1]
    yl = [t[0] for t in top10]
    ys = [t[1] for t in top10]
    yo = [t[2] for t in top10]
    bcols = ["#C8372D" if o >= 10 else "#1E4F8A" for o in yo]
    bars = ax_b.barh(yl, ys, color=bcols, height=0.60)
    ax_b.set_xlim(0, 42)
    ax_b.spines["top"].set_visible(False)
    ax_b.spines["right"].set_visible(False)
    ax_b.spines["left"].set_color("#DCD6CA")
    ax_b.spines["bottom"].set_color("#DCD6CA")
    ax_b.tick_params(axis="y", labelsize=8.0, colors="#17212B")
    ax_b.tick_params(axis="x", labelsize=7.4, colors="#556270")
    ax_b.set_title("Топ-10 аэропортов (площ. / корп.)", fontsize=8.8, fontweight="bold", color="#17212B", pad=6)
    for bar, s_cnt, o_cnt in zip(bars, ys, yo):
        ax_b.text(
            s_cnt + 0.8, bar.get_y() + bar.get_height() / 2,
            f"{s_cnt} / {o_cnt} к.", va="center", ha="left", fontsize=7.6, fontweight="bold", color="#17212B"
        )
    plt.tight_layout(pad=0.35)
    c2_bar_path = assets_dir / "chart_top10_hubs.png"
    fig.savefig(c2_bar_path, dpi=260)
    plt.close(fig)

    return c1_path, c2_map_path, c2_bar_path


# --- PPTX helper utilities ---
def set_slide_bg(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, fill_rgb: RGBColor, line_rgb: RGBColor | None = None, line_pt: float = 0.75, radius: bool = True):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape_type, Inches(left), Inches(top), Inches(width), Inches(height))
    if radius and len(sh.adjustments) > 0:
        sh.adjustments[0] = 0.04
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill_rgb
    if line_rgb is not None:
        sh.line.color.rgb = line_rgb
        sh.line.width = Pt(line_pt)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def add_text(slide, left, top, width, height, text: str, size: float = 12, bold: bool = False, color: RGBColor = INK, align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP, line_spacing: float = 1.18):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = line_spacing
    run = p.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb


def add_bullets(slide, left, top, width, height, items: list[tuple[str, str]], size: float = 11, space_after: float = 6, bullet_color: RGBColor = RW_RED):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    for idx, (lead, body) in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        p.line_spacing = 1.16
        r0 = p.add_run()
        r0.text = "▪  "
        r0.font.name = FONT
        r0.font.size = Pt(size)
        r0.font.bold = True
        r0.font.color.rgb = bullet_color
        if lead:
            r1 = p.add_run()
            r1.text = lead + " "
            r1.font.name = FONT
            r1.font.size = Pt(size)
            r1.font.bold = True
            r1.font.color.rgb = INK
        r2 = p.add_run()
        r2.text = body
        r2.font.name = FONT
        r2.font.size = Pt(size)
        r2.font.color.rgb = INK
    return tb


def add_header(slide, section_tag: str, title: str, slide_num: int, total_slides: int = 7):
    # Top subtle accent bar
    add_rect(slide, 0, 0, 13.333, 0.08, RW_RED, radius=False)
    # Section pill
    pill = add_rect(slide, 0.55, 0.28, 2.95, 0.28, RW_RED_SOFT, line_rgb=RGBColor(0xF0, 0xC2, 0xBE), line_pt=0.7)
    tf = pill.text_frame
    tf.margin_left = Inches(0.1)
    tf.margin_top = Inches(0.02)
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = section_tag.upper()
    r.font.name = FONT
    r.font.size = Pt(8.5)
    r.font.bold = True
    r.font.color.rgb = RW_RED

    add_text(slide, 0.55, 0.64, 12.23, 0.46, title, size=18.5, bold=True, color=INK)
    # Divider line
    add_rect(slide, 0.55, 1.16, 12.23, 0.015, LINE, radius=False)
    # Footer
    add_text(slide, 0.55, 7.12, 9.5, 0.28, "Red Wings · Исследование корпоративного пассажиропотока госкорпораций · 26.11.2026", size=8.5, color=MUTED)
    add_text(slide, 11.8, 7.12, 0.98, 0.28, f"{slide_num} / {total_slides}", size=8.5, bold=True, color=MUTED, align=PP_ALIGN.RIGHT)


def build_presentation() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c1_path, c2_map_path, c2_bar_path = build_charts(OUT_DIR / "assets")

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: TITLE
    # =========================================================================
    s1 = prs.slides.add_slide(blank)
    set_slide_bg(s1, BG)
    add_rect(s1, 0, 0, 13.333, 0.14, RW_RED, radius=False)
    add_rect(s1, 0, 0.14, 0.24, 7.36, DARK_SLATE, radius=False)

    add_text(s1, 0.85, 0.85, 10.5, 0.35, "RED WINGS  ·  СВЕРКА ПОСТАНОВКИ ЗАДАЧИ И ПЛАНА РАБОТ", size=11, bold=True, color=RW_RED)
    add_text(
        s1, 0.85, 1.38, 11.4, 1.45,
        "Поиск дополнительного корпоративного\nпассажиропотока госкорпораций",
        size=34, bold=True, color=INK, line_spacing=1.12
    )
    add_text(
        s1, 0.85, 2.95, 10.8, 0.85,
        "Логика задачи, этапы исследования, результаты фактологической базы на 26.11.2026\nи план следующего шага к контрольной точке 3 декабря 2026 года",
        size=15, color=MUTED, line_spacing=1.3
    )

    # 4 roadmap blocks along bottom
    cards = [
        ("01", "Задача и критерии", "Проверка гипотезы нового регионального потока вне Москвы и СПб", RW_RED),
        ("02", "Логика работы", "5 шагов: компании → аэропорты → структура штата → типы поездок → оценка", BLUE),
        ("03", "Результаты на 26.11", "База 48 групп, 937 площадок, 184 пары, первые региональные кластеры", GREEN),
        ("04", "Шаг к 3 декабря", "Отраслевой слой структуры штата + кластеризация аэропортов (ядро 5 ГК)", AMBER),
    ]
    for i, (num, hdr, desc, col) in enumerate(cards):
        x = 0.85 + i * 2.98
        add_rect(s1, x, 4.35, 2.78, 2.1, WHITE, line_rgb=LINE)
        add_rect(s1, x, 4.35, 2.78, 0.08, col, radius=False)
        add_text(s1, x + 0.18, 4.55, 0.8, 0.4, num, size=20, bold=True, color=col)
        add_text(s1, x + 0.18, 5.02, 2.42, 0.4, hdr, size=13, bold=True, color=INK)
        add_text(s1, x + 0.18, 5.45, 2.42, 0.9, desc, size=10.2, color=MUTED, line_spacing=1.22)

    add_text(s1, 0.85, 6.88, 11.5, 0.3, "Подготовлено по итогам рабочей встречи 26 ноября 2026 г.", size=10, color=MUTED)

    # =========================================================================
    # SLIDE 2: 1) TASK & SUCCESS CRITERIA
    # =========================================================================
    s2 = prs.slides.add_slide(blank)
    set_slide_bg(s2, BG)
    add_header(s2, "1. Постановка задачи", "Задача: проверить гипотезу дополнительного регионального потока", 2)

    # Top main formulation card
    add_rect(s2, 0.55, 1.35, 12.23, 1.48, WHITE, line_rgb=LINE)
    add_rect(s2, 0.55, 1.35, 0.1, 1.48, RW_RED, radius=False)
    add_text(s2, 0.82, 1.44, 11.7, 0.26, "ЦЕЛЬ ИССЛЕДОВАНИЯ ДЛЯ АВИАКОМПАНИИ", size=9.2, bold=True, color=RW_RED)
    add_text(
        s2, 0.82, 1.72, 11.7, 1.02,
        "Определить, существует ли у российских госкорпораций, компаний с госучастием и их внутренних цепочек поставщиков "
        "дополнительный, не закрытый текущим рынком пассажиропоток, который позволяет Red Wings открыть новые регулярные маршруты "
        "(прежде всего в обход Москвы и Санкт-Петербурга) либо предложить корпоративные блоки и чартеры.",
        size=12.0, bold=False, color=INK, line_spacing=1.24
    )

    # 3 columns below: Mechanism, Route Criteria, Honest Outcome
    col_specs = [
        (
            "Механизм: наложение потоков",
            BLUE, BLUE_SOFT,
            [
                ("Не одна компания, а кластер:", "отдельная корпорация редко заполняет регулярный рейс сама по себе."),
                ("Фокус вне MOW и LED:", "потоки в Москву и СПб уже плотно закрыты конкурентами — ищем межрегиональные связи (например, Урал ↔ Сибирь, Поволжье ↔ ЯНАО)."),
                ("Внутренняя кооперация:", "из-за импортозамещения цепочки поставщиков в авиа-, судостроении и энергетике локализованы внутри РФ."),
            ]
        ),
        (
            "Критерий «хорошего маршрута»",
            GREEN, GREEN_SOFT,
            [
                ("Круглогодичная регулярность:", "ровный поток без резкой сезонности ценнее для флота, чем разовый пик с простоем ВС."),
                ("Ориентир частоты:", "идеал — до 2 рейсов в день (от ~200 пасс./день); минимальный порог регулярки — от 2 раз в неделю (проверяется по экономике)."),
                ("Отсечка малых объёмов:", "200–300 человек в год или единичная поездка отдельный регулярный маршрут не формируют."),
            ]
        ),
        (
            "Границы и приемлемый результат",
            AMBER, AMBER_SOFT,
            [
                ("Сначала спрос, потом флот:", "на этапе поиска ниш не отсекаем маршруты текущей сетью и дальностью SSJ100; привязка к аэропортам — главное ограничение."),
                ("Отрицательный вывод равноценен:", "если глубокий расчёт покажет, что дополнительный поток не набирается, фиксируем это честно («идея не прошла»)."),
                ("Продуктовая развилка:", "новый регулярный маршрут → блок мест (пулинг 2–3 компаний) → вахтовый/событийный чартер → No-Go."),
            ]
        ),
    ]
    for i, (hdr, col, soft, bullets) in enumerate(col_specs):
        x = 0.55 + i * 4.16
        add_rect(s2, x, 3.02, 3.92, 3.86, WHITE, line_rgb=LINE)
        add_rect(s2, x, 3.02, 3.92, 0.44, soft, radius=False)
        add_text(s2, x + 0.16, 3.11, 3.6, 0.28, hdr, size=11.0, bold=True, color=col)
        add_bullets(s2, x + 0.14, 3.58, 3.64, 3.2, bullets, size=10.1, space_after=7, bullet_color=col)

    # =========================================================================
    # SLIDE 3: 2) RESEARCH LOGIC BY STEPS
    # =========================================================================
    s3 = prs.slides.add_slide(blank)
    set_slide_bg(s3, BG)
    add_header(s3, "2. Логика и план по пунктам", "Как мы решаем задачу: пять последовательных этапов", 3)

    steps = [
        ("Шаг 1", "Контур корпораций\nи цепочек поставок",
         "Начинаем с ядра из 5 ключевых госкорпораций (+ связанные ПАО и подрядчики). Раскладываем до заводов, филиалов, КБ и удалённых объектов.",
         "Выход: справочники организаций, площадок и связей кооперации", BLUE),
        ("Шаг 2", "Локализация вокруг\nрегиональных аэропортов",
         "Привязываем все площадки к ближайшим аэропортам. Исключаем Москву и СПб, отсекаем «пустые» точки, выделяем кластеры с высокой концентрацией разных корпораций.",
         "Выход: карта региональных узлов притяжения и пар аэропортов", RW_RED),
        ("Шаг 3", "Структура персонала\n(факт + слой допущений)",
         "Разделяем штат по функциям (руководство, закупки/продажи, инженеры, рабочие/вахта). Пробелы закрываем российскими и мировыми отраслевыми аналогами в отдельном слое.",
         "Выход: расчётная доля мобильных сотрудников по типам площадок", GREEN),
        ("Шаг 4", "Укрупнённая типология\nцелей поездок",
         "Сводим 12 дробных категорий к 4 непересекающимся типам: командировки · вахты/стройки/техраб · обучение · разовые мероприятия (разные требования к цене и сервису).",
         "Выход: чистая классификация спроса без двойного счёта", AMBER),
        ("Шаг 5", "Оценка наложения,\nбарьеров и вердикт",
         "Складываем потоки разных корпораций на региональных парах, сверяем с текущим расписанием, собственным флотом заказчиков и ЭТП. Выносим итоговый вердикт.",
         "Выход: список перспективных маршрутов/клиентов или обоснованный No-Go", DARK_SLATE),
    ]

    for i, (st, title, desc, out_txt, col) in enumerate(steps):
        x = 0.55 + i * 2.48
        add_rect(s3, x, 1.48, 2.32, 4.35, WHITE, line_rgb=LINE)
        add_rect(s3, x, 1.48, 2.32, 0.38, col, radius=False)
        add_text(s3, x + 0.12, 1.54, 2.08, 0.28, st, size=11, bold=True, color=WHITE)
        add_text(s3, x + 0.12, 1.98, 2.08, 0.65, title, size=11.5, bold=True, color=INK, line_spacing=1.15)
        add_text(s3, x + 0.12, 2.72, 2.08, 2.1, desc, size=9.6, color=INK, line_spacing=1.22)
        add_rect(s3, x + 0.1, 4.92, 2.12, 0.8, BG, line_rgb=LINE)
        add_text(s3, x + 0.16, 4.98, 2.0, 0.7, out_txt, size=8.6, bold=True, color=col, line_spacing=1.16)
        if i < 4:
            add_text(s3, x + 2.31, 3.3, 0.18, 0.35, "→", size=16, bold=True, color=MUTED, align=PP_ALIGN.CENTER)

    # Bottom governance note
    add_rect(s3, 0.55, 6.02, 12.23, 0.88, BLUE_SOFT, line_rgb=RGBColor(0xBD, 0xD3, 0xEE))
    add_text(
        s3, 0.75, 6.12, 11.85, 0.7,
        "Принцип чистоты данных: фактологическая база (подтверждённые отчёты, тендеры, расписания) и расчётный слой "
        "(отраслевые допущения по структуре персонала и частоте командировок) хранятся раздельно. Неизвестные параметры не заменяются нулями, "
        "а рубли тендеров не переводятся в кресла без маршрутной спецификации.",
        size=10.3, color=INK, line_spacing=1.25
    )

    # =========================================================================
    # SLIDE 4: 3) CURRENT RESULTS — FACT BASE & OPEN-DATA CEILING
    # =========================================================================
    s4 = prs.slides.add_slide(blank)
    set_slide_bg(s4, BG)
    add_header(s4, "3. Результаты на 26.11.2026", "Фактологическая база модели: заполненность и потолок открытых данных", 4)

    # Top KPI strip (6 tiles)
    kpis = [
        ("48", "организаций\n36 с ЭТП · 22 профиля", BLUE),
        ("937 + 32", "площадок (910 с гор.)\nи удалённых объектов", BLUE),
        ("252", "подтверждённых связей\nпоездок (без грузов)", GREEN),
        ("113 / 117", "событий и делегаций\n(форумы, ППР, учёба)", GREEN),
        ("71", "закупка авиаперевозок\n+ 15 связок подряда", AMBER),
        ("184 (118)", "пар аэропортов\n(118 вне Москвы/СПб)", RW_RED),
    ]
    for i, (val, lbl, col) in enumerate(kpis):
        x = 0.55 + i * 2.06
        add_rect(s4, x, 1.38, 1.93, 1.08, WHITE, line_rgb=LINE)
        add_rect(s4, x, 1.38, 1.93, 0.06, col, radius=False)
        add_text(s4, x + 0.1, 1.50, 1.73, 0.42, val, size=19, bold=True, color=col)
        add_text(s4, x + 0.1, 1.95, 1.73, 0.45, lbl, size=8.6, color=MUTED, line_spacing=1.15)

    # Left: Chart 1
    add_rect(s4, 0.55, 2.62, 6.75, 4.25, WHITE, line_rgb=LINE)
    add_text(s4, 0.72, 2.72, 6.4, 0.3, "Заполненность ключевых полей модели из открытых источников", size=11.5, bold=True, color=INK)
    s4.shapes.add_picture(str(c1_path), Inches(0.68), Inches(3.05), width=Inches(6.48))

    # Right: Key diagnostic findings
    add_rect(s4, 7.50, 2.62, 5.28, 4.25, WHITE, line_rgb=LINE)
    add_text(s4, 7.68, 2.74, 4.9, 0.3, "Что показала фактологическая база сегодня", size=12, bold=True, color=INK)
    add_bullets(
        s4, 7.68, 3.12, 4.92, 3.65,
        [
            ("География и каналы закупок закрыты хорошо:", "известны города для 97% площадок, функции для 419/937, ЭТП для 36/48 организаций, проверены 157 плеч маршрутов и 621 источник с URL."),
            ("Главный пробел — структура штата по заводам:", "разбивка на руководителей / ИТР / служащих / рабочих найдена у 13 из 48 групп, но лишь у 1,2% (11/937) отдельных площадок."),
            ("Объёмы перевозок почти не публикуются:", "точный годовой пассажиропоток раскрыт только по 8 из 184 пар (в основном архив до 2024 г.); по 100 актуальным парам поездки подтверждены, но число билетов закрыто."),
            ("Вывод этапа:", "продолжать искать открытые числа «в лоб» малоэффективно — нужен расчётный слой допущений по структуре персонала + кластеризация аэропортов."),
        ],
        size=10.0, space_after=9, bullet_color=RW_RED
    )

    # =========================================================================
    # SLIDE 5: 3) CURRENT RESULTS — REGIONAL CLUSTERS MAP (EXCL. MOW & LED)
    # =========================================================================
    s5 = prs.slides.add_slide(blank)
    set_slide_bg(s5, BG)
    add_header(s5, "3. Результаты на 26.11.2026", "Региональные кластеры площадок вокруг аэропортов (вне MOW и LED)", 5)

    # Left: Two separate crisp images (map + top-10 bar) with zero overlap
    add_rect(s5, 0.55, 1.38, 8.28, 5.5, WHITE, line_rgb=LINE)
    s5.shapes.add_picture(str(c2_map_path), Inches(0.64), Inches(1.48), width=Inches(4.85))
    s5.shapes.add_picture(str(c2_bar_path), Inches(5.55), Inches(1.48), width=Inches(3.20))
    add_text(
        s5, 0.72, 6.26, 7.95, 0.52,
        "Примечание: Краснодар (KRR: 24 площадки, 9 корпораций) исключён из топ-10 действующих узлов из-за закрытого аэропорта. "
        "Красным выделены узлы с концентрацией 9+ разных корпораций и 5 выявленных межрегиональных пар с наложением.",
        size=8.2, color=MUTED, line_spacing=1.16
    )

    # Right: 5 confirmed multi-org non-capital corridors + insight
    add_rect(s5, 9.02, 1.38, 3.76, 5.5, WHITE, line_rgb=LINE)
    add_text(s5, 9.18, 1.50, 3.45, 0.42, "Уже найденные межрегиональные пары с наложением (вне MOW/LED)", size=11, bold=True, color=INK)

    corridors = [
        ("NUX ↔ UFA", "1 696 км · 3 корп.", "Газпром + Роснефть + СТНГ. Есть рейс RW 2/нед. + живой тендер СТНГ 1,22 млрд ₽.", RW_RED),
        ("KJA ↔ SVX", "1 930 км · 2 корп.", "Росатом (Железногорск) + Роснефть (Ачинск) ↔ Екатеринбург (база RW).", BLUE),
        ("IKT ↔ TLK", "940 км · 2 корп.", "Роснефть + Сургутнефтегаз (вахтовый узел Талакан ↔ Иркутск).", BLUE),
        ("BQS ↔ TJM", "3 999 км · 2 корп.", "Газстройпром + СИБУР (Амурский ГПЗ/ГХК Свободный ↔ Тюмень).", BLUE),
        ("BQS ↔ GOJ", "5 243 км · 2 корп.", "Роскосмос (Восточный) + Алмаз-Антей ↔ Нижний Новгород.", BLUE),
    ]
    for i, (pair, meta, desc, col) in enumerate(corridors):
        y = 2.02 + i * 0.86
        add_rect(s5, 9.16, y, 3.48, 0.78, BG, line_rgb=LINE)
        add_rect(s5, 9.16, y, 0.07, 0.78, col, radius=False)
        add_text(s5, 9.30, y + 0.05, 1.55, 0.25, pair, size=10.2, bold=True, color=col)
        add_text(s5, 10.82, y + 0.06, 1.75, 0.24, meta, size=8.5, bold=True, color=MUTED, align=PP_ALIGN.RIGHT)
        add_text(s5, 9.30, y + 0.30, 3.26, 0.44, desc, size=8.4, color=INK, line_spacing=1.12)

    add_rect(s5, 9.16, 6.32, 3.48, 0.46, GREEN_SOFT, line_rgb=RGBColor(0xB7, 0xE2, 0xCC))
    add_text(s5, 9.26, 6.38, 3.30, 0.35, "118 из 184 пар в базе уже лежат вне MOW/LED — это рабочая основа для шага 2.", size=8.6, bold=True, color=GREEN, line_spacing=1.15)

    # =========================================================================
    # SLIDE 6: 3) CURRENT RESULTS — CLIENT RANKING & BARRIERS
    # =========================================================================
    s6 = prs.slides.add_slide(blank)
    set_slide_bg(s6, BG)
    add_header(s6, "3. Результаты на 26.11.2026", "Ранжирование 48 клиентов по перспективности и барьерам входа", 6)

    # Left: Echelon 1 table (Top-6)
    add_rect(s6, 0.55, 1.38, 8.35, 5.5, WHITE, line_rgb=LINE)
    add_text(s6, 0.72, 1.48, 8.0, 0.30, "Эшелон 1 · 6 приоритетных клиентов для старта", size=11.5, bold=True, color=GREEN)

    tbl_shape = s6.shapes.add_table(7, 4, Inches(0.70), Inches(1.88), Inches(8.05), Inches(4.80))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(1.85)
    tbl.columns[1].width = Inches(1.45)
    tbl.columns[2].width = Inches(2.25)
    tbl.columns[3].width = Inches(2.50)

    headers = ["Клиент", "Масштаб в базе", "Точка входа / специфика", "Что может предложить RW"]
    rows_data = [
        ("#1 СТНГ (K6)", "5 зак. (до 1,83 млрд)\n4 удал. объекта", "Живой отбор АП126926 (1,22 млрд ₽) + рейс RW UFA–NUX", "Чартер/субподряд по АП126926 + блок 15–35 мест на WZ-1081"),
        ("#2 Ростех (A2)", "232 площадки\n10 пар · 2 зак.", "Материнская ГК; прямой канал по ЕПоЗ 6.6.2(51)", "Внутригрупповой тариф + блоки ОАК/ОДК/ВР/КРЭТ через SVX"),
        ("#3 Росатом (A1)", "90 площадок\n24 пары · 8 зак.", "Есть прецедент рейсов RW на ПАТЭС (Певек, 303 вахт.)", "Продление чартера ПАТЭС + блоки 10–30 мест под ППР АЭС"),
        ("#4 Газпром (D2)", "60 площ. · 40 пар\n9 закупок", "Часть закрывает «Газпром авиа»; открытые тендеры дочек", "Допёмкость вне «Газпром авиа» + блоки UFA–NUX + чартеры"),
        ("#5 СИБУР (K9)", "Без своего флота\nАмур. ГХК/Тобольск", "Единый канал командировок и групп через OBT «Аэроклуб»", "Интеграция корп. тарифов в «Аэроклуб» + проектные блоки"),
        ("#6 РЖД (D1)", "72 площадки\n18 пар · 3 зак.", "Без пасс. флота; групповая выписка в закупках дочек", "Корп. тарифы + групповые квоты на плечах >12–16 ч поездом"),
    ]

    for c_idx, h in enumerate(headers):
        cell = tbl.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = DARK_SLATE
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        r = p.add_run()
        r.text = h
        r.font.name = FONT
        r.font.size = Pt(8.8)
        r.font.bold = True
        r.font.color.rgb = WHITE

    for r_idx, rdata in enumerate(rows_data, 1):
        bg_c = WHITE if r_idx % 2 == 1 else BG
        for c_idx, val in enumerate(rdata):
            cell = tbl.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg_c
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.line_spacing = 1.12
            r = p.add_run()
            r.text = val
            r.font.name = FONT
            r.font.size = Pt(8.4)
            r.font.bold = (c_idx == 0)
            r.font.color.rgb = INK

    # Right: Echelons 2-4 summary + Market barriers
    add_rect(s6, 9.08, 1.38, 3.70, 2.55, WHITE, line_rgb=LINE)
    add_text(s6, 9.24, 1.48, 3.4, 0.3, "Распределение всех 48 организаций", size=11, bold=True, color=INK)
    add_bullets(
        s6, 9.24, 1.85, 3.4, 2.0,
        [
            ("Эшелон 1 (6):", "приоритет для старта (таблица слева)."),
            ("Эшелон 2 (11):", "точечный вход при снятии барьера (Роснефть, РусГидро, Транснефть, Роскосмос, Россети, Алмаз-Антей, ОСК, НОВАТЭК, Алроса, Сургутнефтегаз, ГСП)."),
            ("Эшелон 3 (14):", "проверить объём и OBT-канал."),
            ("Эшелон 4 (17):", "нет поездок / свой флот — пока No-Go."),
        ],
        size=8.9, space_after=5, bullet_color=BLUE
    )

    add_rect(s6, 9.08, 4.10, 3.70, 2.78, RW_RED_SOFT, line_rgb=RGBColor(0xF0, 0xC2, 0xBE))
    add_text(s6, 9.24, 4.20, 3.4, 0.3, "Выявленные барьеры (22 профиля)", size=11, bold=True, color=RW_RED)
    add_bullets(
        s6, 9.24, 4.55, 3.4, 2.25,
        [
            ("Собственный флот:", "«Газпром авиа», АК «АЛРОСА», «Северсталь Авиа» закрывают базу — туда идём только на пики и допёмкость."),
            ("Режим и допуски:", "проектный допуск Сабетты (НОВАТЭК), закрытые ЭТП ГОЗ (ОСК Севмаш)."),
            ("Рынок OBT 2026:", "16,7% деловых билетов меняются, 64% покупаются за ≤7 дней, бизнес-класс — 3% (критично для SSJ100 100Y)."),
        ],
        size=8.8, space_after=6, bullet_color=RW_RED
    )

    # =========================================================================
    # SLIDE 7: 4) NEXT STEP BY DECEMBER 3 (HIGH-LEVEL)
    # =========================================================================
    s7 = prs.slides.add_slide(blank)
    set_slide_bg(s7, BG)
    add_header(s7, "4. Следующий шаг (к 3 декабря)", "Следующая итерация: структура персонала и региональные кластеры", 7)

    next_blocks = [
        (
            "01", "Структура персонала и слой допущений", BLUE, BLUE_SOFT,
            [
                ("Дособрать данные компаний:", "дополнить численность и связи филиалов по агрегаторам Росстата / ЕГРЮЛ и кадровым источникам."),
                ("Отраслевые аналоги (РФ и мир):", "для авиастроения, атомной отрасли, энергетики, нефтегаза и судостроения определить типовую структуру штата (руководство, закупки/продажи, инженеры, производство)."),
                ("Отдельный расчётный слой:", "оценить долю потенциально летающих сотрудников на предприятии, не смешивая допущения с первичными фактами."),
            ]
        ),
        (
            "02", "Локализация вокруг аэропортов (без MOW и LED)", RW_RED, RW_RED_SOFT,
            [
                ("Фокус на ядре 5 госкорпораций:", "структурировать анализ сначала на 5 крупнейших ГК (+ ключевые внутренние поставщики), чтобы избежать распыления."),
                ("Кластеризация по аэропортам:", "сопоставить все площадки с зонами тяготения региональных аэропортов и отсечь точки с единичными объектами."),
                ("Поиск наложения:", "выявить неочевидные межрегиональные пары (типа Иркутск ↔ Красноярск, Урал ↔ Сибирь), где сходятся интересы разных корпораций."),
            ]
        ),
        (
            "03", "Укрупнение типологии поездок", AMBER, AMBER_SOFT,
            [
                ("4 непересекающиеся категории:", "свести 12 текущих типов в чёткие группы: регулярные командировки · вахты/стройки/техраб · обучение · разовые мероприятия."),
                ("Привязка к профилю пассажира:", "разделить ценовые и сервисные требования (например, молодёжный слёт против командировки среднего менеджмента)."),
            ]
        ),
        (
            "04", "Итог к встрече 3 декабря 2026 г.", GREEN, GREEN_SOFT,
            [
                ("Карта приоритетных региональных пар:", "ранжированный шорт-лист межрегиональных направлений вне MOW/LED с наложением корпораций."),
                ("Первая оценка потенциала потока:", "понимание, по каким парам реально набирается круглогодичный поток, а где гипотеза не подтверждается."),
            ]
        ),
    ]

    positions = [
        (0.55, 1.40, 5.95, 2.55),
        (6.83, 1.40, 5.95, 2.55),
        (0.55, 4.12, 5.95, 1.85),
        (6.83, 4.12, 5.95, 1.85),
    ]
    for (num, hdr, col, soft, items), (x, y, w, h) in zip(next_blocks, positions):
        add_rect(s7, x, y, w, h, WHITE, line_rgb=LINE)
        add_rect(s7, x, y, w, 0.42, soft, radius=False)
        add_text(s7, x + 0.14, y + 0.08, 0.45, 0.28, num, size=11.5, bold=True, color=col)
        add_text(s7, x + 0.56, y + 0.08, w - 0.7, 0.28, hdr, size=11.5, bold=True, color=INK)
        add_bullets(s7, x + 0.14, y + 0.52, w - 0.28, h - 0.6, items, size=9.6, space_after=6, bullet_color=col)

    # Bottom alignment confirmation bar
    add_rect(s7, 0.55, 6.14, 12.23, 0.80, DARK_SLATE, radius=True)
    add_text(s7, 0.78, 6.23, 2.4, 0.25, "СВЕРКА ПОНИМАНИЯ", size=9.2, bold=True, color=RGBColor(0xF8, 0xB4, 0xB4))
    add_text(
        s7, 0.78, 6.46, 11.8, 0.42,
        "1) Приоритет — новые межрегиональные маршруты вне Москвы и СПб за счёт наложения корпораций  ·  "
        "2) Добавляем отдельный слой отраслевых допущений по структуре персонала  ·  "
        "3) Стартуем с ядра 5 госкорпораций к 3 декабря.",
        size=9.8, color=WHITE, line_spacing=1.18
    )

    prs.save(OUT_PPTX)
    print(f"Saved PPTX: {OUT_PPTX} ({OUT_PPTX.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build_presentation()
