#!/usr/bin/env python3
"""Build a 100% clean-from-scratch 8-slide OOXML presentation:
  Red_Wings_Logic_v3.pptx + Red_Wings_Logic_v3.pdf

No slide deletion, no dangling rels/notes, ASCII filename safe for Telegram/macOS/PowerPoint/Keynote.
Preserves the exact v2 visual design (dark/light textured backgrounds, red diagonal panels,
plane icons, Unbounded/Manrope typography, official white Red Wings logo, and Slide 8 verbatim from v2 Slide 9).
"""
from __future__ import annotations

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
OUT_PPTX = OUT_DIR / "Red_Wings_Logic_v3.pptx"

DARK_BG = RGBColor(0x13, 0x18, 0x22)
DARK_CARD = RGBColor(0x1E, 0x26, 0x35)
DARK_STRIPE = RGBColor(0x2F, 0x36, 0x45)
LIGHT_BG = RGBColor(0xF8, 0xF8, 0xF9)
INK = RGBColor(0x14, 0x1A, 0x24)
MUTED = RGBColor(0x52, 0x5B, 0x67)
LIGHT_MUTED = RGBColor(0xB8, 0xC0, 0xCC)
RED = RGBColor(0xD6, 0x0E, 0x1E)
RED_SOFT = RGBColor(0xFA, 0xEA, 0xEC)
CARD_BG = RGBColor(0xF3, 0xF4, 0xF6)
LINE = RGBColor(0xD8, 0xDC, 0xE2)
DARK_LINE = RGBColor(0x2C, 0x34, 0x44)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT_HEAD = "Unbounded"
FONT_BODY = "Manrope"


def make_transparent_white_logo(src: Path, dst: Path) -> Path:
    im = Image.open(src).convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            whiteness = min(r, g, b)
            redness = r - max(g, b)
            if whiteness >= 242 and redness < 12:
                px[x, y] = (0, 0, 0, 0)
            elif redness >= 28:
                alpha = int(min(255, max(0, (255 - min(g, b)) * 1.25)))
                px[x, y] = (min(255, int(r * 1.04)), int(g * 0.85), int(b * 0.85), alpha)
            else:
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                alpha = int(min(255, max(0, (245 - lum) * 1.45)))
                px[x, y] = (255, 255, 255, alpha)
    bbox = im.getbbox()
    if bbox:
        pad = 4
        im = im.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(w, bbox[2] + pad), min(h, bbox[3] + pad)))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "PNG")
    return dst


def prepare_excel_crop(src: Path, dst: Path) -> Path:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im = im.crop((0, 0, int(w * 0.96), h))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "PNG")
    return dst


def extract_assets(tmp_dir: Path) -> dict[str, Path]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    v2 = Presentation(str(V2_PPTX))
    out = {}
    # Slide 1 dark texture + white plane
    s1 = v2.slides[0]
    (tmp_dir / "v2_dark_bg.png").write_bytes(s1.shapes[10].image.blob)
    (tmp_dir / "v2_white_plane.png").write_bytes(s1.shapes[2].image.blob)
    out["dark_bg"] = tmp_dir / "v2_dark_bg.png"
    out["white_plane"] = tmp_dir / "v2_white_plane.png"

    # Slide 2 light texture + red plane
    s2 = v2.slides[1]
    (tmp_dir / "v2_light_bg.png").write_bytes(s2.shapes[25].image.blob)
    (tmp_dir / "v2_red_plane.png").write_bytes(s2.shapes[24].image.blob)
    out["light_bg"] = tmp_dir / "v2_light_bg.png"
    out["red_plane"] = tmp_dir / "v2_red_plane.png"

    # Slide 3 black plane + 48-orgs bar
    s3 = v2.slides[2]
    (tmp_dir / "v2_black_plane.png").write_bytes(s3.shapes[1].image.blob)
    (tmp_dir / "v2_48_orgs_bar.png").write_bytes(s3.shapes[5].image.blob)
    out["black_plane"] = tmp_dir / "v2_black_plane.png"
    out["orgs_bar"] = tmp_dir / "v2_48_orgs_bar.png"

    out["logo"] = make_transparent_white_logo(LOGO_SRC, tmp_dir / "rw_official_white_logo.png")
    out["excel"] = prepare_excel_crop(EXCEL_SRC, tmp_dir / "excel_model_overview.png")
    return out


def set_no_shadow(shape) -> None:
    spPr = shape._element.spPr
    for child in list(spPr):
        if child.tag.endswith("effectLst"):
            spPr.remove(child)
    spPr.append(parse_xml('<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/>'))


def add_rect(slide, left, top, width, height, fill_rgb: RGBColor, line_rgb: RGBColor | None = None, line_pt: float = 0.75, rotation: float = 0.0):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill_rgb
    if line_rgb is not None:
        sh.line.color.rgb = line_rgb
        sh.line.width = Pt(line_pt)
    else:
        sh.line.fill.background()
    if rotation:
        sh.rotation = rotation
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


def init_light_slide(prs: Presentation, bg_png: Path, stripe: str = "right_top"):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = LIGHT_BG
    s.shapes.add_picture(str(bg_png), Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))
    if stripe == "left":
        add_rect(s, 0, 0, 0.32, 7.5, RED)
    elif stripe == "right_top":
        add_rect(s, 12.95, 0, 0.39, 2.35, RED)
    elif stripe == "right_full":
        add_rect(s, 12.95, 0, 0.39, 7.5, RED)
    return s


def add_header(slide, kicker: str, num: str, title: str, plane_path: Path | None = None, left_x: float = 0.72):
    add_tb(slide, left_x, 0.42, 6.5, 0.24, kicker, font=FONT_BODY, size=10, bold=True, color=RED)
    add_tb(slide, 11.80, 0.40, 0.81, 0.26, num, font=FONT_HEAD, size=11, bold=True, color=INK, align=PP_ALIGN.RIGHT)
    add_tb(slide, left_x, 0.84, 10.9, 0.50, title, font=FONT_HEAD, size=20, bold=True, color=INK, line_spacing=1.12)
    if plane_path is not None:
        slide.shapes.add_picture(str(plane_path), Inches(12.16), Inches(0.92), width=Inches(0.34), height=Inches(0.34))


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets = extract_assets(OUT_DIR / "v3_assets")

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # =========================================================================
    # SLIDE 1: TITLE (clean dark canvas + official white Red Wings logo)
    # =========================================================================
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    s1.background.fill.solid()
    s1.background.fill.fore_color.rgb = DARK_BG
    s1.shapes.add_picture(str(assets["dark_bg"]), Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))
    add_rect(s1, 8.38, -0.4, 0.30, 8.3, DARK_STRIPE)
    # Slanted red right wing panel matching v2
    red_panel = s1.shapes.add_shape(MSO_SHAPE.PARALLELOGRAM, Inches(9.20), Inches(-0.3), Inches(4.85), Inches(8.1))
    red_panel.adjustments[0] = 0.22
    red_panel.fill.solid()
    red_panel.fill.fore_color.rgb = RED
    red_panel.line.fill.background()
    set_no_shadow(red_panel)
    s1.shapes.add_picture(str(assets["white_plane"]), Inches(10.65), Inches(1.35), width=Inches(1.35), height=Inches(1.35))

    im_l = Image.open(assets["logo"])
    lw, lh = im_l.size
    logo_w = 2.65
    s1.shapes.add_picture(str(assets["logo"]), Inches(0.72), Inches(0.58), width=Inches(logo_w), height=Inches(logo_w * lh / lw))

    add_tb(s1, 0.72, 2.38, 7.45, 2.85, "Корпоративные\nпассажиропотоки\nвнутри России", font=FONT_HEAD, size=36, bold=True, color=WHITE, line_spacing=1.18)
    add_tb(s1, 0.72, 5.42, 7.1, 0.65, "Поиск новых внутренних маршрутов для авиакомпании Red Wings", font=FONT_BODY, size=14, color=LIGHT_MUTED)

    # =========================================================================
    # SLIDE 2: TASK
    # =========================================================================
    s2 = init_light_slide(prs, assets["light_bg"], stripe="right_full")
    add_tb(s2, 0.72, 0.44, 4.5, 0.24, "ЗАДАЧА", font=FONT_BODY, size=10, bold=True, color=RED)
    add_tb(s2, 11.80, 0.42, 0.81, 0.26, "02", font=FONT_HEAD, size=11, bold=True, color=INK, align=PP_ALIGN.RIGHT)
    add_tb(s2, 0.72, 0.95, 5.15, 1.25, "Поиск новых\nвнутренних маршрутов", font=FONT_HEAD, size=22, bold=True, color=INK, line_spacing=1.18)

    tb_task = s2.shapes.add_textbox(Inches(0.72), Inches(2.42), Inches(5.05), Inches(3.85))
    tf = tb_task.text_frame
    tf.word_wrap = True
    p1 = tf.paragraphs[0]
    p1.line_spacing = 1.32
    p1.space_after = Pt(14)
    r1 = p1.add_run()
    r1.text = "Необходимо найти новые, неиспользованные маршруты внутри страны — актуальные направления, которые связывают города с производственными и деловыми точками интереса."
    r1.font.name = FONT_BODY
    r1.font.size = Pt(13.2)
    r1.font.bold = True
    r1.font.color.rgb = INK

    p2 = tf.add_paragraph()
    p2.line_spacing = 1.32
    p2.space_after = Pt(14)
    r2 = p2.add_run()
    r2.text = "Если перелёты по одному направлению нужны сразу нескольким организациям, их поездки складываются в устойчивый спрос."
    r2.font.name = FONT_BODY
    r2.font.size = Pt(12.8)
    r2.font.color.rgb = MUTED

    p3 = tf.add_paragraph()
    p3.line_spacing = 1.28
    r3 = p3.add_run()
    r3.text = "Если расчёт покажет, что потока не хватает даже с учётом нескольких компаний, закрываем направление как неперспективное."
    r3.font.name = FONT_BODY
    r3.font.size = Pt(11.2)
    r3.font.color.rgb = MUTED

    s2.shapes.add_picture(str(assets["red_plane"]), Inches(5.42), Inches(6.62), width=Inches(0.34), height=Inches(0.34))

    # Right structured card
    add_rect(s2, 6.18, 0.95, 6.22, 6.00, CARD_BG, line_rgb=LINE, line_pt=0.75)
    blocks_s2 = [
        ("Кого и что ищем", INK,
         "По каждой госкорпорации, госкомпании и подрядчику определяем четыре параметра: площадки и места работы, пары городов и аэропортов, число пассажиров и частоту поездок."),
        ("География первой очереди", RED,
         "Внутренние перелёты по России. В первую очередь смотрим межрегиональные связи вне Москвы и Санкт-Петербурга, где у нескольких организаций совпадают аэропорты вылета и прилёта."),
        ("Коммерческий формат Red Wings", INK,
         "Смотрим три формата под найденный спрос: регулярный рейс на год, блок мест на период и отдельный чартер под вахтовую смену или делегацию."),
        ("Ограничения", INK,
         "На первом этапе не учитываем:\n— флот;\n— дальность полёта;\n— количество мест;\n— исключаем грузовые и туристические перевозки."),
    ]
    ys = [1.16, 2.56, 3.96, 5.34]
    for i, ((bh, bc, bt), y) in enumerate(zip(blocks_s2, ys)):
        add_tb(s2, 6.50, y, 5.58, 0.28, bh, font=FONT_HEAD, size=11.5, bold=True, color=bc)
        add_tb(s2, 6.50, y + 0.30, 5.58, 1.22 if i == 3 else 0.96, bt, font=FONT_BODY, size=10.2, color=MUTED, line_spacing=1.22)
        if i < 3:
            add_rect(s2, 6.50, y + 1.28, 5.58, 0.012, LINE)

    # =========================================================================
    # SLIDE 3: OBJECTS & SEGMENTS (48 orgs bar, focus on 5 GKs, 4 groups NO numbers)
    # =========================================================================
    s3 = init_light_slide(prs, assets["light_bg"], stripe="right_top")
    add_header(s3, "ЗАДАЧА · ОБЪЕКТЫ И СЕГМЕНТЫ", "03", "48 организаций и 4 группы корпоративных поездок", assets["black_plane"])
    s3.shapes.add_picture(str(assets["orgs_bar"]), Inches(0.72), Inches(1.52), width=Inches(11.88), height=Inches(1.36))

    add_rect(s3, 0.72, 2.98, 11.88, 0.74, RED_SOFT, line_rgb=RGBColor(0xF0, 0xC2, 0xC7), line_pt=0.8)
    tb5 = s3.shapes.add_textbox(Inches(0.92), Inches(3.07), Inches(11.48), Inches(0.58))
    tf5 = tb5.text_frame
    tf5.word_wrap = True
    p = tf5.paragraphs[0]
    p.line_spacing = 1.24
    for txt, col in [("Первоочередная задача — разобрать первые 5 госкорпораций: ", RED), ("Росатом, Ростех, Роскосмос, ВЭБ.РФ и АСВ.", INK)]:
        r = p.add_run()
        r.text = txt
        r.font.name = FONT_BODY
        r.font.size = Pt(11.4)
        r.font.bold = True
        r.font.color.rgb = col
    p2 = tf5.add_paragraph()
    p2.line_spacing = 1.2
    r3 = p2.add_run()
    r3.text = "Смотрим не только головные офисы, но и дочерние заводы и филиалы: часто перелёты закупают отдельные площадки."
    r3.font.name = FONT_BODY
    r3.font.size = Pt(9.8)
    r3.font.color.rgb = MUTED

    add_rect(s3, 0.72, 3.92, 11.88, 0.015, LINE)
    add_tb(s3, 0.72, 4.08, 11.88, 0.30, "Объединили все типы поездок в 4 группы (без пересечений)", font=FONT_HEAD, size=11.5, bold=True, color=INK)

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
    for i, (gt, gd) in enumerate(groups_4):
        x = 0.72 + i * 3.04
        add_rect(s3, x, 4.52, 2.82, 2.38, WHITE, line_rgb=LINE, line_pt=0.75)
        add_rect(s3, x, 4.52, 2.82, 0.06, RED if i == 0 else INK)
        add_tb(s3, x + 0.16, 4.72, 2.50, 0.42, gt, font=FONT_HEAD, size=10.8, bold=True, color=INK, line_spacing=1.15)
        add_tb(s3, x + 0.16, 5.22, 2.50, 1.56, gd, font=FONT_BODY, size=9.8, color=MUTED, line_spacing=1.24)

    # =========================================================================
    # SLIDE 4: PLAN OF WORK (7 steps + authenticity note)
    # =========================================================================
    s4 = init_light_slide(prs, assets["light_bg"], stripe="left")
    add_header(s4, "ПЛАН РАБОТЫ", "04", "Что планируем делать: семь этапов", assets["red_plane"], left_x=0.78)

    plan_7 = [
        ("1", "Мировой опыт\nи чужие модели", "Изучаем, как устроены модели корпоративных перевозок в других странах и системах, и берём рабочие идеи для нашей задачи."),
        ("2", "Структура\nперсонала", "Разбираем штат организаций по категориям, чтобы понять, какая доля сотрудников ездит в командировки и на вахты."),
        ("3", "События\nи площадки", "Собираем список предприятий, удалённых мест работы, форумов, ремонтных кампаний и регулярных мероприятий."),
        ("4", "Связи, конкуренты,\nаэропорты и экономика", "Анализируем связи корпораций и их дочек, проверяем существующие рейсы и конкурентов, смотрим аэропорты и экономику направлений."),
        ("5", "Допущения и\nдостройка модели", "Там, где данных в открытых источниках нет, вводим аккуратные допущения и достраиваем расчётную модель."),
        ("6", "Наложения и\nновые маршруты", "Ищем направления, где сходятся поездки нескольких организаций, и собираем кандидатов на новые маршруты."),
        ("7", "Визуализация\nи интерфейс", "Делаем понятный интерактивный интерфейс с картой и карточками, чтобы проверять гипотезы и показывать результаты."),
    ]
    for i in range(4):
        num, st_t, st_d = plan_7[i]
        x, y = 0.78 + i * 2.98, 1.62
        add_rect(s4, x, y, 2.78, 2.15, WHITE, line_rgb=LINE, line_pt=0.75)
        add_tb(s4, x + 0.16, y + 0.12, 0.55, 0.40, num, font=FONT_HEAD, size=20, bold=True, color=RED)
        add_tb(s4, x + 0.68, y + 0.14, 1.98, 0.54, st_t, font=FONT_HEAD, size=9.8, bold=True, color=INK, line_spacing=1.15)
        add_tb(s4, x + 0.16, y + 0.78, 2.46, 1.26, st_d, font=FONT_BODY, size=9.6, color=MUTED, line_spacing=1.22)
        if i < 3:
            add_tb(s4, x + 2.77, y + 0.88, 0.22, 0.30, "→", font=FONT_BODY, size=14, bold=True, color=RED, align=PP_ALIGN.CENTER)

    for i in range(3):
        num, st_t, st_d = plan_7[4 + i]
        x, y = 0.78 + i * 4.00, 4.02
        add_rect(s4, x, y, 3.74, 2.02, WHITE, line_rgb=LINE, line_pt=0.75)
        add_tb(s4, x + 0.18, y + 0.12, 0.55, 0.40, num, font=FONT_HEAD, size=20, bold=True, color=INK)
        add_tb(s4, x + 0.72, y + 0.14, 2.86, 0.50, st_t, font=FONT_HEAD, size=10.2, bold=True, color=INK, line_spacing=1.15)
        add_tb(s4, x + 0.18, y + 0.74, 3.38, 1.18, st_d, font=FONT_BODY, size=9.8, color=MUTED, line_spacing=1.24)
        if i < 2:
            add_tb(s4, x + 3.74, y + 0.82, 0.26, 0.30, "→", font=FONT_BODY, size=14, bold=True, color=INK, align=PP_ALIGN.CENTER)

    add_rect(s4, 0.78, 6.26, 11.74, 0.62, CARD_BG, line_rgb=LINE, line_pt=0.75)
    add_tb(s4, 0.98, 6.40, 11.34, 0.36, "Проверка данных: на каждом этапе все сведения и источники проходят проверку на подлинность и актуальность.", font=FONT_BODY, size=10.8, bold=True, color=INK)

    # =========================================================================
    # SLIDE 5: RESULTS — EXCEL SCREENSHOT
    # =========================================================================
    s5 = init_light_slide(prs, assets["light_bg"], stripe="right_top")
    add_header(s5, "РЕЗУЛЬТАТЫ · СОСТАВ МОДЕЛИ", "05", "Рабочая книга Excel на 26 ноября", assets["red_plane"])

    ex_im = Image.open(assets["excel"])
    ew, eh = ex_im.size
    pic_w = 11.88
    pic_h = min(3.92, pic_w * (eh / ew))
    pic_w = pic_h * (ew / eh)
    pic_x = 0.72 + (11.88 - pic_w) / 2
    add_rect(s5, pic_x - 0.04, 1.54, pic_w + 0.08, pic_h + 0.08, WHITE, line_rgb=LINE, line_pt=1.0)
    s5.shapes.add_picture(str(assets["excel"]), Inches(pic_x), Inches(1.58), width=Inches(pic_w), height=Inches(pic_h))

    y_bot = 1.58 + pic_h + 0.28
    bot_notes = [
        ("Справочники (4 листа)", "Организации, 937 площадок, места работы вне города регистрации и 330 городов с аэропортами."),
        ("Факты (8 листов)", "Связи поездок, события, участники событий, структура штата, подрядчики, закупки и экономика."),
        ("Итоги и исследования", "Сводки по группам и направлениям, пары городов, плечи маршрутов и 3 листа проверок. Пустая ячейка значит, что цифр в источниках нет."),
    ]
    for i, (bh, bt) in enumerate(bot_notes):
        x = 0.72 + i * 4.04
        add_rect(s5, x, y_bot, 3.80, 1.28, WHITE, line_rgb=LINE, line_pt=0.75)
        add_tb(s5, x + 0.14, y_bot + 0.12, 3.52, 0.28, bh, font=FONT_HEAD, size=9.8, bold=True, color=RED if i == 2 else INK)
        add_tb(s5, x + 0.14, y_bot + 0.44, 3.52, 0.78, bt, font=FONT_BODY, size=9.2, color=MUTED, line_spacing=1.22)

    # =========================================================================
    # SLIDE 6: RESULTS — SUMMARY COLUMNS & DEMAND CALCULATION LOGIC
    # =========================================================================
    s6 = init_light_slide(prs, assets["light_bg"], stripe="right_top")
    add_header(s6, "РЕЗУЛЬТАТЫ · РАСЧЁТ СПРОСА", "06", "Столбцы итоговых таблиц и логика расчёта спроса", assets["black_plane"])

    add_rect(s6, 0.72, 1.50, 5.88, 5.52, WHITE, line_rgb=LINE, line_pt=0.75)
    add_tb(s6, 0.92, 1.64, 5.50, 0.28, "Итог по направлениям (demand_estimate — 23 столбца)", font=FONT_HEAD, size=9.8, bold=True, color=RED)
    add_tb(
        s6, 0.92, 1.98, 5.50, 2.15,
        "Pair_ID  ·  Аэропорт A  ·  Аэропорт B  ·  Города A  ·  Города B  ·  Длина, км  ·  "
        "Org_IDs  ·  OD_IDs  ·  Основания  ·  Типы поездок  ·  Пассажиров в год  ·  "
        "Основание числа пассажиров  ·  Объём из источников  ·  Наибольшая группа за раз, чел.  ·  "
        "Группа от 80 чел.  ·  Периодичность  ·  Прямые рейсы сейчас  ·  Тариф, ₽  ·  "
        "Источник тарифа  ·  Потенциальная выручка от билетов, ₽ в год  ·  Лучший статус  ·  "
        "Актуальность  ·  Вывод",
        font=FONT_BODY, size=9.3, color=INK, line_spacing=1.30
    )
    add_rect(s6, 0.92, 4.24, 5.48, 0.015, LINE)
    add_tb(s6, 0.92, 4.38, 5.50, 0.28, "Итог по группам (summary_by_org — 18 столбцов)", font=FONT_HEAD, size=9.8, bold=True, color=INK)
    add_tb(
        s6, 0.92, 4.72, 5.50, 2.15,
        "Org_ID  ·  Организация  ·  Вид  ·  Численность группы  ·  Год численности  ·  "
        "Площадок  ·  Городов площадок  ·  Мест работы вне города регистрации  ·  "
        "Кто ездит: структура персонала  ·  Зачем ездят  ·  Направлений (пар аэропортов)  ·  "
        "Главные направления  ·  Известные объёмы  ·  Периодичность  ·  "
        "Закупок перевозок  ·  Крупнейшая закупка  ·  Вывод по группе  ·  Чего не хватает",
        font=FONT_BODY, size=9.3, color=INK, line_spacing=1.30
    )

    add_rect(s6, 6.84, 1.50, 5.76, 5.52, CARD_BG, line_rgb=LINE, line_pt=0.75)
    add_tb(s6, 7.06, 1.64, 5.32, 0.30, "Как считаем спрос и строим выводы", font=FONT_HEAD, size=10.6, bold=True, color=INK)
    calc_steps = [
        ("1. Отбор реальных поездок людей", "Берём подтверждённые связи и делегации на события между двумя разными аэропортами. Перевозки грузов без людей в расчёт не попадают."),
        ("2. Склейка в пару аэропортов A ↔ B", "Оба направления (туда и обратно) объединяем в одну строку и записываем все Org_ID, которые по ней летают. Так сразу видно наложение разных компаний."),
        ("3. Раздельный счёт объёмов без натягивания", "В «Пассажиров в год» идут только годовые цифры из источников. Разовые рейсы и месячные данные на год не умножаем, а рубли тендеров не делим на цену билета."),
        ("4. Сверка с рынком и выручка", "Подтягиваем действующие прямые рейсы конкурентов и наблюдённые тарифы. Выручку считаем только там, где на одной паре известны и годовой поток, и тариф."),
        ("5. Из чего складывается вывод", "Итоговый вывод по паре и организации строится на четырёх вещах: есть ли физический объём, актуальны ли данные (от 2024 года), сходятся ли на линии несколько групп и закрыт ли маршрут сейчас."),
    ]
    y_c = 2.04
    for title_c, body_c in calc_steps:
        add_tb(s6, 7.06, y_c, 5.34, 0.24, title_c, font=FONT_BODY, size=10.0, bold=True, color=RED if title_c.startswith(("3.", "5.")) else INK)
        add_tb(s6, 7.06, y_c + 0.24, 5.34, 0.68, body_c, font=FONT_BODY, size=9.1, color=MUTED, line_spacing=1.20)
        y_c += 0.96

    # =========================================================================
    # SLIDE 7: RESULTS — ALL 15 TABLES & KEY COLUMNS
    # =========================================================================
    s7 = init_light_slide(prs, assets["light_bg"], stripe="right_top")
    add_header(s7, "РЕЗУЛЬТАТЫ · ТАБЛИЦЫ МОДЕЛИ", "07", "15 таблиц модели: назначение и основные столбцы", assets["red_plane"])

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
    tshape = s7.shapes.add_table(16, 3, Inches(0.72), Inches(1.46), Inches(11.88), Inches(5.30))
    tbl = tshape.table
    tbl.columns[0].width = Inches(2.18)
    tbl.columns[1].width = Inches(4.02)
    tbl.columns[2].width = Inches(5.68)

    for ci, ch in enumerate(["Лист модели", "Что описывает одна строка", "Ключевые столбцы для расчёта"]):
        cell = tbl.cell(0, ci)
        cell.fill.solid()
        cell.fill.fore_color.rgb = INK
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)
        cell.margin_left = Inches(0.08)
        r = cell.text_frame.paragraphs[0].add_run()
        r.text = ch
        r.font.name = FONT_BODY
        r.font.size = Pt(8.6)
        r.font.bold = True
        r.font.color.rgb = WHITE

    for ri, (name, desc, cols) in enumerate(tbl_rows, 1):
        bg_row = RED_SOFT if ri == 15 else (WHITE if ri % 2 == 1 else CARD_BG)
        for ci, val in enumerate((name, desc, cols)):
            cell = tbl.cell(ri, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg_row
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
            r.font.color.rgb = RED if (ci == 0 and ri >= 13) else (INK if ci < 2 else MUTED)

    add_tb(s7, 0.72, 6.88, 11.88, 0.30, "Дополнительно лист «Итог по группам» (16-й лист) сводит те же таблицы по каждой из 48 организаций.", font=FONT_BODY, size=9.0, color=MUTED)

    # =========================================================================
    # SLIDE 8: RESULTS — WHAT IS ALREADY DONE & FOUND AS OF NOV 26
    # =========================================================================
    s8_res = init_light_slide(prs, assets["light_bg"], stripe="right_top")
    add_header(s8_res, "РЕЗУЛЬТАТЫ · СДЕЛАНО НА 26 НОЯБРЯ", "08", "Что уже собрано и найдено на сегодняшний день", assets["black_plane"])

    # Top 5 metric cards (real verified numbers)
    done_kpis = [
        ("48", "организаций разобрано", "36 с ЭТП · 30 со штатом\n22 профиля специфики", RED),
        ("937 / 32", "площадок и объектов", "910 с городом · 783 с ИНН\n419 с функцией площадки", INK),
        ("252 / 71", "связей и закупок", "113 событий · 117 делегаций\n15 связок подряда", INK),
        ("184 (118)", "пар аэропортов", "118 пар вне Москвы и СПб\n157 проверенных плеч", RED),
        ("621", "новых источников URL", "плюс базовый реестр Zotero\nвсе факты проверяемы", INK),
    ]
    for i, (val, ttl, sub, col) in enumerate(done_kpis):
        x = 0.72 + i * 2.41
        add_rect(s8_res, x, 1.48, 2.24, 1.32, WHITE, line_rgb=LINE, line_pt=0.75)
        add_rect(s8_res, x, 1.48, 2.24, 0.05, col)
        add_tb(s8_res, x + 0.12, 1.58, 2.00, 0.42, val, font=FONT_HEAD, size=16.5, bold=True, color=col)
        add_tb(s8_res, x + 0.12, 2.02, 2.00, 0.24, ttl, font=FONT_BODY, size=8.8, bold=True, color=INK)
        add_tb(s8_res, x + 0.12, 2.27, 2.00, 0.46, sub, font=FONT_BODY, size=8.0, color=MUTED, line_spacing=1.18)

    # Left big card: Concrete findings already uncovered
    add_rect(s8_res, 0.72, 3.00, 6.32, 4.02, WHITE, line_rgb=LINE, line_pt=0.75)
    add_tb(s8_res, 0.94, 3.14, 5.88, 0.28, "Первые подтверждённые находки", font=FONT_HEAD, size=11.0, bold=True, color=INK)

    findings_left = [
        ("Крупнейшие региональные узлы площадок (вне Москвы и СПб)",
         "Екатеринбург (SVX: 29 площ. / 13 корп.), Самара (KUF: 27 / 12), Н. Новгород (GOJ: 24 / 11), Уфа (UFA: 14 / 7), Новосибирск (OVB: 12 / 8) и Хабаровск (KHV: 11 / 9)."),
        ("5 региональных пар, где уже сходятся 2–3 корпорации",
         "Новый Уренгой ↔ Уфа (Газпром + Роснефть + СТНГ; отбор АП126926 на 1,22 млрд ₽ + рейс RW), Красноярск ↔ Екатеринбург (Росатом + Роснефть), Иркутск ↔ Талакан, Благовещенск ↔ Тюмень, Благовещенск ↔ Н. Новгород."),
        ("Специфика 22 компаний: барьеры и живые точки входа",
         "Учтены ведомственные авиакомпании («Газпром авиа», АК «АЛРОСА», «Северсталь Авиа»), допуск Сабетты и закрытые ЭТП ГОЗ. Найдены рабочие входы: тендер СТНГ, внутригрупповой канал Ростеха (ЕПоЗ 6.6.2(51)), рейсы RW на ПАТЭС Певек и ТМС «Аэроклуб» у СИБУРа."),
    ]
    yf = 3.54
    for fh, fb in findings_left:
        add_tb(s8_res, 0.94, yf, 5.88, 0.24, fh, font=FONT_BODY, size=9.8, bold=True, color=RED if "5 региональных" in fh else INK)
        add_tb(s8_res, 0.94, yf + 0.24, 5.88, 0.84, fb, font=FONT_BODY, size=9.0, color=MUTED, line_spacing=1.20)
        yf += 1.14

    # Right big card: Working artifacts + honest gaps motivating next step
    add_rect(s8_res, 7.26, 3.00, 5.34, 4.02, CARD_BG, line_rgb=LINE, line_pt=0.75)
    add_tb(s8_res, 7.48, 3.14, 4.90, 0.28, "Готовые инструменты и текущие пробелы", font=FONT_HEAD, size=10.6, bold=True, color=INK)

    findings_right = [
        ("Собрана единая Excel-модель и автоскрипт пересчёта",
         "Все 16 таблиц связаны ключами; сводки по группам и направлениям пересчитываются автоматически, каждый факт привязан к источнику."),
        ("Сделано интерактивное веб-досье по всем 48 клиентам",
         "С картой России, узлами пересечения компаний, карточкой каждого заказчика, закупками, барьерами и предложениями для Red Wings."),
        ("Честно зафиксирован потолок открытых данных",
         "Разбивка штата по категориям нашлась у 13 из 48 групп и лишь у 1,2% отдельных заводов (11/937). Годовой поток раскрыт по 8 парам из 184, рублёвый тариф — по 15. Поэтому следующий шаг — расчётный слой допущений и кластеры 5 госкорпораций."),
    ]
    yr = 3.54
    for rh, rb in findings_right:
        add_tb(s8_res, 7.48, yr, 4.90, 0.24, rh, font=FONT_BODY, size=9.8, bold=True, color=RED if "потолок" in rh else INK)
        add_tb(s8_res, 7.48, yr + 0.24, 4.90, 0.88, rb, font=FONT_BODY, size=9.0, color=MUTED, line_spacing=1.20)
        yr += 1.14

    # =========================================================================
    # SLIDE 9: NEXT STEP BY DEC 3 (exact content & layout of v2 Slide 9)
    # =========================================================================
    s8 = prs.slides.add_slide(prs.slide_layouts[6])
    s8.background.fill.solid()
    s8.background.fill.fore_color.rgb = DARK_BG
    s8.shapes.add_picture(str(assets["dark_bg"]), Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))
    red8 = s8.shapes.add_shape(MSO_SHAPE.PARALLELOGRAM, Inches(10.85), Inches(-0.3), Inches(3.25), Inches(8.1))
    red8.adjustments[0] = 0.20
    red8.fill.solid()
    red8.fill.fore_color.rgb = RED
    red8.line.fill.background()
    set_no_shadow(red8)
    s8.shapes.add_picture(str(assets["white_plane"]), Inches(11.45), Inches(5.55), width=Inches(1.05), height=Inches(1.05))

    add_tb(s8, 0.72, 0.44, 4.50, 0.24, "СЛЕДУЮЩИЙ ШАГ · К 3 ДЕКАБРЯ", font=FONT_BODY, size=10, bold=True, color=LIGHT_MUTED)
    add_tb(s8, 11.80, 0.42, 0.81, 0.26, "09", font=FONT_HEAD, size=11, bold=True, color=WHITE, align=PP_ALIGN.RIGHT)
    add_tb(s8, 0.72, 0.96, 9.45, 0.96, "К 3 декабря проверяем гипотезу\nна ядре из пяти госкорпораций", font=FONT_HEAD, size=24, bold=True, color=WHITE, line_spacing=1.18)

    items_s8 = [
        ("Фокус на пяти госкорпорациях",
         "Росатом, Ростех, Роскосмос, ВЭБ.РФ и АСВ. Проверяем гипотезу на крупнейшем ядре (354 площадки), чтобы понять, собирается ли дополнительный региональный поток."),
        ("Локализация вокруг региональных аэропортов",
         "Выделяем узлы вне Москвы и Санкт-Петербурга с высокой концентрацией площадок разных корпораций, отсекаем малолюдные точки и проверяем перекрёстные пары."),
        ("Структура персонала и слой допущений",
         "Добираем данные из реестров юрлиц, сборников Росстата, ЕМИСС и отраслевых ЭТП; строим расчётный слой допущений по оргструктурам и отраслевым аналогам."),
    ]
    ys8 = [2.29, 3.47, 4.65]
    for idx, ((ih, ib), y) in enumerate(zip(items_s8, ys8)):
        add_rect(s8, 0.72, y + 0.11, 0.42, 0.06, RED)
        add_tb(s8, 1.38, y, 8.42, 0.32, ih, font=FONT_HEAD, size=12.0, bold=True, color=WHITE)
        add_tb(s8, 1.38, y + 0.35, 8.42, 0.66, ib, font=FONT_BODY, size=10.4, color=LIGHT_MUTED, line_spacing=1.24)
        if idx < 2:
            add_rect(s8, 0.72, y + 1.03, 9.10, 0.012, DARK_LINE)

    add_rect(s8, 0.72, 5.86, 9.10, 1.06, DARK_CARD, line_rgb=DARK_LINE, line_pt=0.75)
    add_tb(s8, 1.00, 6.00, 8.55, 0.28, "Итог к встрече 3 декабря", font=FONT_HEAD, size=11.0, bold=True, color=RED)
    add_tb(s8, 1.00, 6.32, 8.55, 0.56, "Короткий список перспективных межрегиональных узлов и пар с диапазонной оценкой потока — либо обоснованное закрытие гипотезы по направлениям без достаточного спроса.", font=FONT_BODY, size=10.4, color=WHITE, line_spacing=1.22)

    prs.save(OUT_PPTX)
    print(f"Saved clean PPTX: {OUT_PPTX} ({OUT_PPTX.stat().st_size / 1024:.1f} KB, {len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
