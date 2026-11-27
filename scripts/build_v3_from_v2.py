#!/usr/bin/env python3
"""Build Red_Wings_Логика_задачи_v3.pptx directly from v2.pptx, preserving its
visual theme (backgrounds, diagonal panels, plane icons, Unbounded/Manrope fonts,
and final Slide 9 -> Slide 8) while applying every user revision and de-AIing prose.
"""
from __future__ import annotations

import copy
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml import parse_xml
from pptx.util import Inches, Pt

V2_PPTX = Path(
    "/Users/a/.t3/userdata/attachments/"
    "cf2877c4-a2c1-40be-a4c2-f3db7fd63b1a-a6cbd8e6-94f0-4ae6-a922-698e4917df27-pptx.pptx"
)
LOGO_SRC = Path(
    "/Users/a/.t3/userdata/attachments/"
    "cf2877c4-a2c1-40be-a4c2-f3db7fd63b1a-17803a2f-e905-4d77-86fa-a2113a574427.jpg"
)
EXCEL_SRC = Path(
    "/Users/a/.t3/userdata/attachments/"
    "cf2877c4-a2c1-40be-a4c2-f3db7fd63b1a-e5967d19-f6bb-41ba-b1d3-2f732646a5b2.jpg"
)
OUT_DIR = Path(
    "/Users/a/agent-audit-2026-09/case_championship/context/57_presentation_for_lidiya_20261126"
)
OUT_PPTX = OUT_DIR / "Red_Wings_Логика_задачи_v3.pptx"

# Brand palette matching v2.pptx
INK = RGBColor(0x14, 0x1A, 0x24)
MUTED = RGBColor(0x52, 0x5B, 0x67)
RED = RGBColor(0xD6, 0x0E, 0x1E)
RED_SOFT = RGBColor(0xFA, 0xEA, 0xEC)
CARD_BG = RGBColor(0xF3, 0xF4, 0xF6)
LINE = RGBColor(0xD8, 0xDC, 0xE2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT_HEAD = "Unbounded"
FONT_BODY = "Manrope"


def make_transparent_white_logo(src: Path, dst: Path) -> Path:
    """Convert official Red Wings logo on white bg into crisp transparent PNG
    for dark background: dark gray text -> pure white, red W ribbon -> intact."""
    im = Image.open(src).convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            # Distance from pure white background
            whiteness = min(r, g, b)
            redness = r - max(g, b)
            if whiteness >= 242 and redness < 12:
                px[x, y] = (0, 0, 0, 0)
            elif redness >= 28:
                # Red wing W: preserve red tone, smooth alpha on light edges
                alpha = int(min(255, max(0, (255 - min(g, b)) * 1.25)))
                # Boost saturation slightly against dark bg
                px[x, y] = (min(255, int(r * 1.04)), int(g * 0.85), int(b * 0.85), alpha)
            else:
                # Neutral gray/dark letters -> crisp white with anti-aliased alpha
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                alpha = int(min(255, max(0, (245 - lum) * 1.45)))
                px[x, y] = (255, 255, 255, alpha)
    bbox = im.getbbox()
    if bbox:
        pad = 4
        im = im.crop((
            max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(w, bbox[2] + pad), min(h, bbox[3] + pad),
        ))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "PNG")
    return dst


def prepare_excel_crop(src: Path, dst: Path) -> Path:
    """Crop empty trailing whitespace on right/bottom of Excel screenshot."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    # Trim empty right columns (Excel columns E..N beyond text end ~86% width)
    crop_box = (0, 0, int(w * 0.96), h)
    im = im.crop(crop_box)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "PNG")
    return dst


def delete_slide(prs: Presentation, index: int) -> None:
    sldIdLst = prs.slides._sldIdLst
    sldId = list(sldIdLst)[index]
    rId = sldId.rId
    prs.part.drop_rel(rId)
    sldIdLst.remove(sldId)


def remove_shape(shape) -> None:
    el = shape._element
    el.getparent().remove(el)


def send_to_back(slide, shape) -> None:
    spTree = slide.shapes._spTree
    el = shape._element
    spTree.remove(el)
    spTree.insert(2, el)


def set_no_shadow(shape) -> None:
    spPr = shape._element.spPr
    for child in list(spPr):
        if child.tag.endswith("effectLst"):
            spPr.remove(child)
    spPr.append(parse_xml('<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/>'))


def add_rect(slide, left, top, width, height, fill_rgb: RGBColor, line_rgb: RGBColor | None = None, line_pt: float = 0.75):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill_rgb
    if line_rgb is not None:
        sh.line.color.rgb = line_rgb
        sh.line.width = Pt(line_pt)
    else:
        sh.line.fill.background()
    set_no_shadow(sh)
    return sh


def add_tb(slide, left, top, width, height, text: str, font: str = FONT_BODY, size: float = 12,
           bold: bool = False, color: RGBColor = INK, align=PP_ALIGN.LEFT, line_spacing: float = 1.2):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        r.font.name = font
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
    return tb


def set_text_preserving_style(shape, new_text: str, size_pt: float | None = None, bold: bool | None = None, color: RGBColor | None = None):
    tf = shape.text_frame
    tf.word_wrap = True
    # Capture style from first run
    ref_font = FONT_BODY
    ref_size = Pt(12)
    ref_bold = False
    ref_color = INK
    ref_align = PP_ALIGN.LEFT
    if tf.paragraphs:
        ref_align = tf.paragraphs[0].alignment
        if tf.paragraphs[0].runs:
            r0 = tf.paragraphs[0].runs[0]
            if r0.font.name:
                ref_font = r0.font.name
            if r0.font.size:
                ref_size = r0.font.size
            if r0.font.bold is not None:
                ref_bold = r0.font.bold
            if r0.font.color and r0.font.color.type == 1:
                ref_color = r0.font.color.rgb

    tf.clear()
    lines = new_text.split("\n")
    for idx, line in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = ref_align
        p.line_spacing = 1.22
        r = p.add_run()
        r.text = line
        r.font.name = ref_font
        r.font.size = Pt(size_pt) if size_pt is not None else ref_size
        r.font.bold = bold if bold is not None else ref_bold
        r.font.color.rgb = color if color is not None else ref_color


def extract_v2_assets(prs: Presentation, tmp_dir: Path) -> dict[str, Path]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    # Light textured background from Slide 2 (shape 25)
    s2 = prs.slides[1]
    bg_sh = s2.shapes[25]
    p_bg = tmp_dir / "v2_light_bg.png"
    p_bg.write_bytes(bg_sh.image.blob)
    out["light_bg"] = p_bg

    # Red plane icon from Slide 2 (shape 24)
    pl_sh = s2.shapes[24]
    p_pl = tmp_dir / "v2_red_plane.png"
    p_pl.write_bytes(pl_sh.image.blob)
    out["red_plane"] = p_pl

    # Black plane icon from Slide 3 (shape 1)
    s3 = prs.slides[2]
    bpl_sh = s3.shapes[1]
    p_bpl = tmp_dir / "v2_black_plane.png"
    p_bpl.write_bytes(bpl_sh.image.blob)
    out["black_plane"] = p_bpl

    # 48 orgs bar chart from Slide 3 (shape 5)
    bar_sh = s3.shapes[5]
    p_bar = tmp_dir / "v2_48_orgs_bar.png"
    p_bar.write_bytes(bar_sh.image.blob)
    out["orgs_bar"] = p_bar

    return out


def clear_slide_keep_bg_and_chrome(slide, keep_bg_path: Path, red_stripe_side: str = "right"):
    """Remove all shapes and rebuild clean v2 light slide canvas."""
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor(0xF8, 0xF8, 0xF9)
    for sh in list(slide.shapes):
        remove_shape(sh)
    bg = slide.shapes.add_picture(str(keep_bg_path), Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))
    send_to_back(slide, bg)
    if red_stripe_side == "left":
        add_rect(slide, 0, 0, 0.32, 7.5, RED)
    elif red_stripe_side == "right_top":
        add_rect(slide, 12.95, 0, 0.39, 2.35, RED)
    elif red_stripe_side == "right_full":
        add_rect(slide, 12.95, 0, 0.39, 7.5, RED)


def add_v2_header(slide, kicker: str, num: str, title: str, plane_path: Path | None = None, left_x: float = 0.72):
    add_tb(slide, left_x, 0.42, 6.5, 0.24, kicker, font=FONT_BODY, size=10, bold=True, color=RED)
    add_tb(slide, 11.80, 0.40, 0.81, 0.26, num, font=FONT_HEAD, size=11, bold=True, color=INK, align=PP_ALIGN.RIGHT)
    add_tb(slide, left_x, 0.84, 10.9, 0.50, title, font=FONT_HEAD, size=20, bold=True, color=INK, line_spacing=1.12)
    if plane_path is not None:
        slide.shapes.add_picture(str(plane_path), Inches(12.16), Inches(0.92), width=Inches(0.34), height=Inches(0.34))


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets_dir = OUT_DIR / "v3_assets"
    logo_png = make_transparent_white_logo(LOGO_SRC, assets_dir / "rw_official_white_logo.png")
    excel_png = prepare_excel_crop(EXCEL_SRC, assets_dir / "excel_model_overview.png")

    prs = Presentation(str(V2_PPTX))
    v2_assets = extract_v2_assets(prs, assets_dir)

    # =========================================================================
    # SLIDE 1: TITLE — official Red Wings logo, remove bottom clutter (image 4)
    # =========================================================================
    s1 = prs.slides[0]
    # Remove old logo icon [3], old "RED WINGS" text [4], subtitle [6], line [7],
    # bottom left [8], bottom right [9]
    for idx in sorted([3, 4, 6, 7, 8, 9], reverse=True):
        remove_shape(s1.shapes[idx])

    # Place official Red Wings logo (white letters + red W) cleanly at top-left
    # Original aspect ~680x266 (~2.55:1) -> width 2.75", height ~1.08"
    im_l = Image.open(logo_png)
    lw, lh = im_l.size
    logo_w = 2.65
    logo_h = logo_w * (lh / lw)
    s1.shapes.add_picture(str(logo_png), Inches(0.72), Inches(0.58), width=Inches(logo_w), height=Inches(logo_h))

    # Reposition main title cleanly vertically centered in the left column
    for sh in s1.shapes:
        if sh.has_text_frame and "Корпоративные" in sh.text_frame.text:
            sh.left = Inches(0.72)
            sh.top = Inches(2.45)
            sh.width = Inches(7.4)
            sh.height = Inches(2.85)
            set_text_preserving_style(
                sh,
                "Корпоративные\nпассажиропотоки\nвнутри России",
                size_pt=38, bold=True, color=WHITE
            )

    # Clean concise subtitle without AI boilerplate or bottom stats block
    add_tb(
        s1, 0.72, 5.45, 7.1, 0.65,
        "Поиск новых внутренних маршрутов для авиакомпании Red Wings",
        font=FONT_BODY, size=14, color=RGBColor(0xC6, 0xCC, 0xD6), line_spacing=1.25
    )

    # =========================================================================
    # SLIDE 2: TASK — strict formulation, remove 80/2/12 block, bullet limits
    # =========================================================================
    s2 = prs.slides[1]
    # Remove left divider [5] and 80 мест / 2 рейса / 12 мес [6..11]
    for idx in sorted([5, 6, 7, 8, 9, 10, 11], reverse=True):
        remove_shape(s2.shapes[idx])

    # Update left title & strict task text
    for sh in s2.shapes:
        if not sh.has_text_frame:
            continue
        txt = sh.text_frame.text
        if "Наложение корпоративных" in txt:
            sh.top = Inches(0.95)
            sh.height = Inches(1.20)
            set_text_preserving_style(sh, "Поиск новых\nвнутренних маршрутов", size_pt=22, bold=True, color=INK)
        elif "Одна компания редко" in txt:
            sh.top = Inches(2.38)
            sh.width = Inches(5.05)
            sh.height = Inches(3.80)
            tf = sh.text_frame
            tf.clear()
            p1 = tf.paragraphs[0]
            p1.line_spacing = 1.32
            p1.space_after = Pt(14)
            r1 = p1.add_run()
            r1.text = (
                "Необходимо найти новые, неиспользованные маршруты внутри страны — "
                "актуальные направления, которые связывают города с производственными и деловыми точками интереса."
            )
            r1.font.name = FONT_BODY
            r1.font.size = Pt(13.5)
            r1.font.bold = True
            r1.font.color.rgb = INK

            p2 = tf.add_paragraph()
            p2.line_spacing = 1.32
            p2.space_after = Pt(14)
            r2 = p2.add_run()
            r2.text = (
                "Если перелёты по одному направлению нужны сразу нескольким организациям, "
                "их поездки складываются в устойчивый спрос."
            )
            r2.font.name = FONT_BODY
            r2.font.size = Pt(13.0)
            r2.font.color.rgb = MUTED

            p3 = tf.add_paragraph()
            p3.line_spacing = 1.30
            r3 = p3.add_run()
            r3.text = (
                "Если расчёт покажет, что потока не хватает даже с учётом нескольких компаний, "
                "закрываем направление как неперспективное."
            )
            r3.font.name = FONT_BODY
            r3.font.size = Pt(11.5)
            r3.font.color.rgb = MUTED
        elif txt.strip() == "Кого и что ищем":
            set_text_preserving_style(sh, "Кого и что ищем", size_pt=12.5, bold=True, color=INK)
        elif "По каждой госкорпорации" in txt:
            set_text_preserving_style(
                sh,
                "По каждой госкорпорации, госкомпании и подрядчику определяем четыре параметра: "
                "площадки и места работы, пары городов и аэропортов, число пассажиров и частоту поездок.",
                size_pt=10.5, color=MUTED
            )
        elif txt.strip() == "География первой очереди":
            set_text_preserving_style(sh, "География первой очереди", size_pt=12.5, bold=True, color=RED)
        elif "Внутренние перелёты по России" in txt:
            set_text_preserving_style(
                sh,
                "Внутренние перелёты по России. В первую очередь смотрим межрегиональные связи "
                "вне Москвы и Санкт-Петербурга, где у нескольких организаций совпадают аэропорты вылета и прилёта.",
                size_pt=10.5, color=MUTED
            )
        elif txt.strip() == "Коммерческий формат Red Wings":
            set_text_preserving_style(sh, "Коммерческий формат Red Wings", size_pt=12.5, bold=True, color=INK)
        elif "Сопоставляем совокупный спрос" in txt:
            set_text_preserving_style(
                sh,
                "Смотрим три формата под найденный спрос: регулярный рейс на год, "
                "блок мест на период и отдельный чартер под вахтовую смену или делегацию.",
                size_pt=10.5, color=MUTED
            )
        elif "Рамки и критерий" in txt:
            set_text_preserving_style(sh, "Ограничения", size_pt=12.5, bold=True, color=INK)
        elif "На первом этапе флот" in txt:
            sh.height = Inches(1.22)
            set_text_preserving_style(
                sh,
                "На первом этапе не учитываем:\n"
                "— флот;\n"
                "— дальность полёта;\n"
                "— количество мест;\n"
                "— исключаем грузовые и туристические перевозки.",
                size_pt=10.3, color=MUTED
            )

    # =========================================================================
    # SLIDE 3: OBJECTS & SEGMENTS — 48 orgs bar + focus on first 5 GKs,
    #          4 trip groups WITHOUT 84/116/24/113 numbers
    # =========================================================================
    s3 = prs.slides[2]
    clear_slide_keep_bg_and_chrome(s3, v2_assets["light_bg"], red_stripe_side="right_top")
    add_v2_header(s3, "ЗАДАЧА · ОБЪЕКТЫ И СЕГМЕНТЫ", "03", "48 организаций и 4 группы корпоративных поездок", v2_assets["black_plane"])

    # Keep the clean 48-orgs horizontal distribution bar from v2
    s3.shapes.add_picture(str(v2_assets["orgs_bar"]), Inches(0.72), Inches(1.52), width=Inches(11.88), height=Inches(1.36))

    # Highlight first 5 state corporations explicitly (no raw link counts!)
    add_rect(s3, 0.72, 2.98, 11.88, 0.72, RED_SOFT, line_rgb=RGBColor(0xF0, 0xC2, 0xC7), line_pt=0.8)
    tb5 = s3.shapes.add_textbox(Inches(0.92), Inches(3.07), Inches(11.48), Inches(0.56))
    tf5 = tb5.text_frame
    tf5.word_wrap = True
    p = tf5.paragraphs[0]
    p.line_spacing = 1.25
    r1 = p.add_run()
    r1.text = "Первоочередная задача — разобрать первые 5 госкорпораций: "
    r1.font.name = FONT_BODY
    r1.font.size = Pt(11.5)
    r1.font.bold = True
    r1.font.color.rgb = RED
    r2 = p.add_run()
    r2.text = "Росатом, Ростех, Роскосмос, ВЭБ.РФ и АСВ."
    r2.font.name = FONT_BODY
    r2.font.size = Pt(11.5)
    r2.font.bold = True
    r2.font.color.rgb = INK
    p2 = tf5.add_paragraph()
    p2.line_spacing = 1.2
    r3 = p2.add_run()
    r3.text = "Смотрим не только головные офисы, но и дочерние заводы и филиалы: часто перелёты закупают отдельные площадки."
    r3.font.name = FONT_BODY
    r3.font.size = Pt(9.8)
    r3.font.color.rgb = MUTED

    # Divider
    add_rect(s3, 0.72, 3.92, 11.88, 0.015, LINE)
    add_tb(s3, 0.72, 4.08, 11.88, 0.30, "Объединили все типы поездок в 4 группы (без пересечений)", font=FONT_HEAD, size=12, bold=True, color=INK)

    groups_4 = [
        ("Вахты и техработы",
         "Смены на месторождениях и стройках, выезды ремонтных бригад (ППР на АЭС, монтаж и наладка оборудования). Запросы обычно идут группами под чартеры или блоки мест."),
        ("Деловые командировки",
         "Поездки руководителей, инженеров КБ, закупщиков и сервисных специалистов по кооперации, проверкам и испытаниям. Летят малыми группами круглый год, важно удобное расписание."),
        ("Обучение и кадры",
         "Выезды сотрудников с предприятий в учебные центры, корпоративные академии и на аттестации. График известен заранее, для заказчика важна цена билета."),
        ("Разовые мероприятия",
         "Федеральные форумы (ПМЭФ, ВЭФ, Иннопром), чемпионаты профмастерства, спартакиады и корпоративные слёты. Дают крупные разовые делегации под конкретные даты."),
    ]
    for i, (g_title, g_desc) in enumerate(groups_4):
        x = 0.72 + i * 3.04
        add_rect(s3, x, 4.52, 2.82, 2.38, WHITE, line_rgb=LINE, line_pt=0.75)
        add_rect(s3, x, 4.52, 2.82, 0.06, RED if i == 0 else INK)
        add_tb(s3, x + 0.16, 4.72, 2.50, 0.42, g_title, font=FONT_HEAD, size=11.0, bold=True, color=INK, line_spacing=1.15)
        add_tb(s3, x + 0.16, 5.22, 2.50, 1.56, g_desc, font=FONT_BODY, size=9.8, color=MUTED, line_spacing=1.24)

    # =========================================================================
    # SLIDE 4: PLAN OF WORK — exact 7 steps requested by user, NO 2 bottom boxes,
    #          single clear note about authenticity verification at every step
    # =========================================================================
    s4 = prs.slides[3]
    clear_slide_keep_bg_and_chrome(s4, v2_assets["light_bg"], red_stripe_side="left")
    add_v2_header(s4, "ПЛАН РАБОТЫ", "04", "Что планируем делать: семь этапов", v2_assets["red_plane"], left_x=0.78)

    plan_7 = [
        ("1", "Мировой опыт\nи чужие модели",
         "Изучаем, как устроены модели корпоративных перевозок в других странах и системах, и берём рабочие идеи для нашей задачи."),
        ("2", "Структура\nперсонала",
         "Разбираем штат организаций по категориям, чтобы понять, какая доля сотрудников ездит в командировки и на вахты."),
        ("3", "События\nи площадки",
         "Собираем список предприятий, удалённых мест работы, форумов, ремонтных кампаний и регулярных мероприятий."),
        ("4", "Связи, конкуренты,\nаэропорты и экономика",
         "Анализируем связи корпораций и их дочек, проверяем существующие рейсы и конкурентов, смотрим аэропорты и экономику направлений."),
        ("5", "Допущения и\nдостройка модели",
         "Там, где данных в открытых источниках нет, вводим аккуратные допущения и достраиваем расчётную модель."),
        ("6", "Наложения и\nновые маршруты",
         "Ищем направления, где сходятся поездки нескольких организаций, и собираем кандидатов на новые маршруты."),
        ("7", "Визуализация\nи интерфейс",
         "Делаем понятный интерактивный интерфейс с картой и карточками, чтобы проверять гипотезы и показывать результаты."),
    ]

    # Top row: steps 1..4 (4 cards across)
    for i in range(4):
        num, st_title, st_desc = plan_7[i]
        x = 0.78 + i * 2.98
        y = 1.62
        add_rect(s4, x, y, 2.78, 2.15, WHITE, line_rgb=LINE, line_pt=0.75)
        add_tb(s4, x + 0.16, y + 0.12, 0.55, 0.40, num, font=FONT_HEAD, size=20, bold=True, color=RED)
        add_tb(s4, x + 0.68, y + 0.14, 1.98, 0.54, st_title, font=FONT_HEAD, size=10.0, bold=True, color=INK, line_spacing=1.15)
        add_tb(s4, x + 0.16, y + 0.78, 2.46, 1.26, st_desc, font=FONT_BODY, size=9.6, color=MUTED, line_spacing=1.22)
        if i < 3:
            add_tb(s4, x + 2.77, y + 0.88, 0.22, 0.30, "→", font=FONT_BODY, size=14, bold=True, color=RED, align=PP_ALIGN.CENTER)

    # Bottom row: steps 5..7 (3 wider cards across)
    for i in range(3):
        num, st_title, st_desc = plan_7[4 + i]
        x = 0.78 + i * 4.00
        y = 4.02
        add_rect(s4, x, y, 3.74, 2.02, WHITE, line_rgb=LINE, line_pt=0.75)
        add_tb(s4, x + 0.18, y + 0.12, 0.55, 0.40, num, font=FONT_HEAD, size=20, bold=True, color=INK)
        add_tb(s4, x + 0.72, y + 0.14, 2.86, 0.50, st_title, font=FONT_HEAD, size=10.5, bold=True, color=INK, line_spacing=1.15)
        add_tb(s4, x + 0.18, y + 0.74, 3.38, 1.18, st_desc, font=FONT_BODY, size=9.8, color=MUTED, line_spacing=1.24)
        if i < 2:
            add_tb(s4, x + 3.74, y + 0.82, 0.26, 0.30, "→", font=FONT_BODY, size=14, bold=True, color=INK, align=PP_ALIGN.CENTER)

    # Single clean note on authenticity check (replacing the two removed boxes)
    add_rect(s4, 0.78, 6.26, 11.74, 0.62, CARD_BG, line_rgb=LINE, line_pt=0.75)
    add_tb(
        s4, 0.98, 6.40, 11.34, 0.36,
        "Проверка данных: на каждом этапе все сведения и источники проходят проверку на подлинность и актуальность.",
        font=FONT_BODY, size=11.0, bold=True, color=INK
    )

    # =========================================================================
    # REPLACE OLD RESULTS SLIDES (v2 Slides 5, 6, 7, 8 -> indices 4, 5, 6, 7)
    # Keep 3 slides for new Results (indices 4, 5, 6), delete index 7 so old Slide 9 becomes Slide 8!
    # =========================================================================
    delete_slide(prs, 7)  # deletes old Slide 8; now total slides = 8 (indices 0..7)

    # --- NEW SLIDE 5 (index 4): Excel screenshot of sheets / rows / files ---
    s5 = prs.slides[4]
    clear_slide_keep_bg_and_chrome(s5, v2_assets["light_bg"], red_stripe_side="right_top")
    add_v2_header(s5, "РЕЗУЛЬТАТЫ · СОСТАВ МОДЕЛИ", "05", "Рабочая книга Excel на 26 ноября", v2_assets["red_plane"])

    # Embed user's Excel screenshot crisp and large inside thin frame
    ex_im = Image.open(excel_png)
    ew, eh = ex_im.size
    pic_w = 11.88
    pic_h = pic_w * (eh / ew)
    if pic_h > 3.95:
        pic_h = 3.95
        pic_w = pic_h * (ew / eh)
    pic_x = 0.72 + (11.88 - pic_w) / 2
    add_rect(s5, pic_x - 0.04, 1.54, pic_w + 0.08, pic_h + 0.08, WHITE, line_rgb=LINE, line_pt=1.0)
    s5.shapes.add_picture(str(excel_png), Inches(pic_x), Inches(1.58), width=Inches(pic_w), height=Inches(pic_h))

    # 3 concise summary captions underneath
    y_bot = 1.58 + pic_h + 0.28
    bot_notes = [
        ("Справочники (4 листа)", "Организации, 937 площадок, места работы вне города регистрации и 330 городов с аэропортами."),
        ("Факты (8 листов)", "Связи поездок, события, участники событий, структура штата, подрядчики, закупки и экономика."),
        ("Итоги и исследования", "Сводки по группам и направлениям, пары городов, плечи маршрутов и 3 листа проверок. Пустая ячейка значит, что цифр в источниках нет."),
    ]
    for i, (bh, bt) in enumerate(bot_notes):
        x = 0.72 + i * 4.04
        add_rect(s5, x, y_bot, 3.80, 1.28, WHITE, line_rgb=LINE, line_pt=0.75)
        add_tb(s5, x + 0.14, y_bot + 0.12, 3.52, 0.28, bh, font=FONT_HEAD, size=10.0, bold=True, color=RED if i == 2 else INK)
        add_tb(s5, x + 0.14, y_bot + 0.44, 3.52, 0.78, bt, font=FONT_BODY, size=9.2, color=MUTED, line_spacing=1.22)

    # --- NEW SLIDE 6 (index 5): All columns in summary sheets + how we calculate demand & conclusions ---
    s6 = prs.slides[5]
    clear_slide_keep_bg_and_chrome(s6, v2_assets["light_bg"], red_stripe_side="right_top")
    add_v2_header(s6, "РЕЗУЛЬТАТЫ · РАСЧЁТ СПРОСА", "06", "Столбцы итоговых таблиц и логика расчёта спроса", v2_assets["black_plane"])

    # Left column: exact columns of both summary tables
    add_rect(s6, 0.72, 1.50, 5.88, 5.52, WHITE, line_rgb=LINE, line_pt=0.75)
    add_tb(s6, 0.92, 1.64, 5.50, 0.28, "Итог по направлениям (demand_estimate — 23 столбца)", font=FONT_HEAD, size=10.2, bold=True, color=RED)
    add_tb(
        s6, 0.92, 1.98, 5.50, 2.15,
        "Pair_ID  ·  Аэропорт A  ·  Аэропорт B  ·  Города A  ·  Города B  ·  Длина, км  ·  "
        "Org_IDs  ·  OD_IDs  ·  Основания  ·  Типы поездок  ·  Пассажиров в год  ·  "
        "Основание числа пассажиров  ·  Объём из источников  ·  Наибольшая группа за раз, чел.  ·  "
        "Группа от 80 чел.  ·  Периодичность  ·  Прямые рейсы сейчас  ·  Тариф, ₽  ·  "
        "Источник тарифа  ·  Потенциальная выручка от билетов, ₽ в год  ·  Лучший статус  ·  "
        "Актуальность  ·  Вывод",
        font=FONT_BODY, size=9.4, color=INK, line_spacing=1.30
    )

    add_rect(s6, 0.92, 4.24, 5.48, 0.015, LINE)
    add_tb(s6, 0.92, 4.38, 5.50, 0.28, "Итог по группам (summary_by_org — 18 столбцов)", font=FONT_HEAD, size=10.2, bold=True, color=INK)
    add_tb(
        s6, 0.92, 4.72, 5.50, 2.15,
        "Org_ID  ·  Организация  ·  Вид  ·  Численность группы  ·  Год численности  ·  "
        "Площадок  ·  Городов площадок  ·  Мест работы вне города регистрации  ·  "
        "Кто ездит: структура персонала  ·  Зачем ездят  ·  Направлений (пар аэропортов)  ·  "
        "Главные направления  ·  Известные объёмы  ·  Периодичность  ·  "
        "Закупок перевозок  ·  Крупнейшая закупка  ·  Вывод по группе  ·  Чего не хватает",
        font=FONT_BODY, size=9.4, color=INK, line_spacing=1.30
    )

    # Right column: how we calculate demand & build conclusions
    add_rect(s6, 6.84, 1.50, 5.76, 5.52, CARD_BG, line_rgb=LINE, line_pt=0.75)
    add_tb(s6, 7.06, 1.64, 5.32, 0.30, "Как считаем спрос и строим выводы", font=FONT_HEAD, size=11.0, bold=True, color=INK)

    calc_steps = [
        ("1. Отбор реальных поездок людей",
         "Берём подтверждённые связи и делегации на события между двумя разными аэропортами. Перевозки грузов без людей в расчёт не попадают."),
        ("2. Склейка в пару аэропортов A ↔ B",
         "Оба направления (туда и обратно) объединяем в одну строку и записываем все Org_ID, которые по ней летают. Так сразу видно наложение разных компаний."),
        ("3. Раздельный счёт объёмов без натягивания",
         "В «Пассажиров в год» идут только годовые цифры из источников. Разовые рейсы и месячные данные на год не умножаем, а рубли тендеров не делим на цену билета."),
        ("4. Сверка с рынком и выручка",
         "Подтягиваем действующие прямые рейсы конкурентов и наблюдённые тарифы. Выручку считаем только там, где на одной паре известны и годовой поток, и тариф."),
        ("5. Из чего складывается вывод",
         "Итоговый вывод по паре и организации строится на четырёх вещах: есть ли физический объём, актуальны ли данные (от 2024 года), сходятся ли на линии несколько групп и закрыт ли маршрут сейчас."),
    ]
    y_c = 2.04
    for title_c, body_c in calc_steps:
        add_tb(s6, 7.06, y_c, 5.34, 0.24, title_c, font=FONT_BODY, size=10.0, bold=True, color=RED if title_c.startswith("3.") or title_c.startswith("5.") else INK)
        add_tb(s6, 7.06, y_c + 0.24, 5.34, 0.68, body_c, font=FONT_BODY, size=9.1, color=MUTED, line_spacing=1.20)
        y_c += 0.96

    # --- NEW SLIDE 7 (index 6): All 15 base tables & key columns for calculation ---
    s7 = prs.slides[6]
    clear_slide_keep_bg_and_chrome(s7, v2_assets["light_bg"], red_stripe_side="right_top")
    add_v2_header(s7, "РЕЗУЛЬТАТЫ · ТАБЛИЦЫ МОДЕЛИ", "07", "15 таблиц модели: назначение и основные столбцы", v2_assets["red_plane"])

    tbl_rows = [
        ("Организации", "Головная корпорация, госкомпания или подрядчик", "Org_ID, Вид, Штаб-квартира, Численность, Площадка закупок"),
        ("Площадки", "Дочернее юрлицо, завод или филиал группы", "Site_ID, Org_ID, Функция площадки, Город, ИНН, Численность"),
        ("Места работы", "Удалённый объект (стройка, месторождение, АЭС)", "Location_ID, Site_ID, Аэропорт (IATA), Режим доступа, Пассажиров/год"),
        ("Аэропорты", "Город и ближайший аэропорт с координатами", "Город, Код ИАТА, Широта, Долгота, Расстояние км, Статус"),
        ("Связи", "Подтверждённая поездка между двумя точками", "Link_ID, Org_ID, Город откуда/куда, Тип связи, Кто ездит, Человек, Период, Год, Статус"),
        ("События", "Форум, выставка, чемпионат, ремонт или учёба", "Event_ID, Тип, Город, Даты, Периодичность, Участников"),
        ("Участники событий", "Конкретная организация или команда на событии", "Event_ID, Org_ID, Site_ID, Город отправления, Человек"),
        ("Закупки", "Тендер или контракт на билеты и чартеры", "Proc_ID, Org_ID, Вид закупки, Маршруты, Объём, НМЦ / Цена, Исполнитель"),
        ("Подрядчики", "Связка «подрядчик или поставщик → заказчик»", "Contract_ID, Org_ID подрядчика, Org_ID заказчика, Роль, Период"),
        ("Персонал групп", "Разбивка штата группы по 4 категориям", "Org_ID, Год, Руководители, ИТР, Служащие, Рабочие (чел. и %)"),
        ("Персонал площадок", "Та же разбивка штата по отдельной площадке", "Site_ID, Год, Руководители, ИТР, Служащие, Рабочие (чел. и %)"),
        ("Экономика", "Тарифы, рыночные показатели, субсидии и нормы", "Econ_ID, Тип, Показатель, Значение, Единица, Относится к, Период"),
        ("Пары", "Отобранная направленная пара городов A → B", "OD_ID, Аэропорт откуда/куда, Расстояние км, Org_IDs, Основания, Актуальность"),
        ("Плечи маршрутов", "Прямой рейс, пересадка, поезд или автотрансфер", "Leg_ID, OD_ID, Вид транспорта, Перевозчик, Рейсов/нед., Тариф ₽"),
        ("Итог по направлениям", "Сводка по паре аэропортов A ↔ B в обе стороны", "Pair_ID, Org_IDs, Пассажиров/год, Объём, Прямые рейсы, Тариф ₽, Вывод"),
    ]

    tshape = s7.shapes.add_table(16, 3, Inches(0.72), Inches(1.46), Inches(11.88), Inches(5.32))
    tbl = tshape.table
    tbl.columns[0].width = Inches(2.18)
    tbl.columns[1].width = Inches(4.02)
    tbl.columns[2].width = Inches(5.68)

    col_hdrs = ["Лист модели", "Что описывает одна строка", "Ключевые столбцы для расчёта"]
    for ci, ch in enumerate(col_hdrs):
        cell = tbl.cell(0, ci)
        cell.fill.solid()
        cell.fill.fore_color.rgb = INK
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)
        cell.margin_left = Inches(0.08)
        p = cell.text_frame.paragraphs[0]
        r = p.add_run()
        r.text = ch
        r.font.name = FONT_BODY
        r.font.size = Pt(8.6)
        r.font.bold = True
        r.font.color.rgb = WHITE

    for ri, (name, desc, cols) in enumerate(tbl_rows, 1):
        bg_row = WHITE if ri % 2 == 1 else CARD_BG
        is_calc = ri >= 13
        for ci, val in enumerate((name, desc, cols)):
            cell = tbl.cell(ri, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RED_SOFT if (ri == 15) else bg_row
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.06)
            p = cell.text_frame.paragraphs[0]
            p.line_spacing = 1.05
            r = p.add_run()
            r.text = val
            r.font.name = FONT_BODY
            r.font.size = Pt(8.0)
            r.font.bold = (ci == 0)
            r.font.color.rgb = RED if (ci == 0 and is_calc) else (INK if ci < 2 else MUTED)

    add_tb(
        s7, 0.72, 6.88, 11.88, 0.30,
        "Дополнительно лист «Итог по группам» (16-й лист) сводит те же таблицы по каждой из 48 организаций.",
        font=FONT_BODY, size=9.0, color=MUTED
    )

    # =========================================================================
    # SLIDE 8 (index 7): UNCHANGED original Slide 9 from v2 — only update 09 -> 08
    # =========================================================================
    s8 = prs.slides[7]
    for sh in s8.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip() == "09":
            set_text_preserving_style(sh, "08")

    prs.save(OUT_PPTX)
    print(f"Saved v3 PPTX: {OUT_PPTX} ({OUT_PPTX.stat().st_size / 1024:.1f} KB, {len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
