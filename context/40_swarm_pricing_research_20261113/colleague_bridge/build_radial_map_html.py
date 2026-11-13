"""Генерирует HTML-объяснялку RADIAL vs HYBRID vs HUB с картами в стиле слайдов презентации."""
import json
import math
from pathlib import Path
import pandas as pd

WORKTREE = Path("/Users/a/agent-audit-2026-09/case_championship/.worktrees/p40-dashboard-competition")
CONTEXT = Path("/Users/a/agent-audit-2026-09/case_championship/context")
OUT = CONTEXT / "40_swarm_pricing_research_20261113" / "colleague_bridge" / "radial_map_explainer.html"

# Та же коническая проекция Ламберта, что и в src/deck/maps.py
LAT1, LAT2, LAT0, LON0 = math.radians(50), math.radians(64), math.radians(55), 70.0
N_ = math.log(math.cos(LAT1) / math.cos(LAT2)) / math.log(
    math.tan(math.pi / 4 + LAT2 / 2) / math.tan(math.pi / 4 + LAT1 / 2)
)
F_ = math.cos(LAT1) * math.tan(math.pi / 4 + LAT1 / 2) ** N_ / N_
R0 = F_ / math.tan(math.pi / 4 + LAT0 / 2) ** N_


def proj(lon, lat):
    r = F_ / math.tan(math.pi / 4 + math.radians(lat) / 2) ** N_
    t = N_ * math.radians(lon - LON0)
    return r * math.sin(t), R0 - r * math.cos(t)


def rings(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


def build_svg_map(geo, coords, ext, width, height, hub, slots, hybrid_svx_spokes=None, labels_ru=None, offsets=None, badge=""):
    # ext = (lon_min, lon_max, lat_min, lat_max)
    xs = [proj(lo, la)[0] for lo in (ext[0], ext[1]) for la in (ext[2], ext[3])]
    ys = [proj(lo, la)[1] for lo in (ext[0], ext[1]) for la in (ext[2], ext[3])]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    aspect = width / height
    w, h = x1 - x0, y1 - y0
    if w / h > aspect:
        c = (y0 + y1) / 2
        h = w / aspect
        y0, y1 = c - h / 2, c + h / 2
    else:
        c = (x0 + x1) / 2
        w = h * aspect
        x0, x1 = c - w / 2, c + w / 2

    def sx(px):
        return (px - x0) / (x1 - x0) * width

    def sy(py):
        return height - (py - y0) / (y1 - y0) * height

    def pt_xy(iata):
        lo, la = coords[iata]
        px, py = proj(lo, la)
        return sx(px), sy(py)

    def ring_in_ext(pts):
        xs_ = [p[0] for p in pts]
        ys_ = [p[1] for p in pts]
        return not (max(xs_) < ext[0] - 8 or min(xs_) > ext[1] + 8 or max(ys_) < ext[2] - 6 or min(ys_) > ext[3] + 6)

    def ring_d(pts):
        if not ring_in_ext(pts):
            return ""
        step = max(1, len(pts) // 80)
        sub = pts[::step]
        if sub[-1] != pts[-1]:
            sub.append(pts[-1])
        out = []
        for idx, (lx, ly) in enumerate(sub):
            px, py = proj(lx, ly)
            out.append(f"{'M' if idx == 0 else 'L'}{sx(px):.1f},{sy(py):.1f}")
        return "".join(out) + "Z"

    def arc_d(a_code, b_code, bend=0.11):
        ax, ay = pt_xy(a_code)
        bx, by = pt_xy(b_code)
        mx, my = (ax + bx) / 2, (ay + by) / 2
        dx, dy = bx - ax, by - ay
        cx, cy = mx - dy * bend, my + dx * bend
        return f"M{ax:.1f},{ay:.1f} Q{cx:.1f},{cy:.1f} {bx:.1f},{by:.1f}"

    svg = [
        f'<svg viewBox="0 0 {width} {height}" style="width:100%;height:{height}px;display:block;background:#E3ECF2;border-radius:6px" role="img">',
    ]
    # Фоновые страны и Россия
    for f in geo["countries"]:
        is_rus = f["properties"].get("ADM0_A3") == "RUS"
        fill = "#ECE6DA" if is_rus else "#F4F1EA"
        for r in rings(f["geometry"]):
            d = ring_d(r)
            if d:
                svg.append(f'<path d="{d}" fill="{fill}" stroke="#D9D3C7" stroke-width="0.6"/>')
    for f in geo["regions"]:
        for r in rings(f["geometry"]):
            d = ring_d(r)
            if d:
                svg.append(f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="0.5"/>')
    for f in geo["lakes"]:
        for r in rings(f["geometry"]):
            d = ring_d(r)
            if d:
                svg.append(f'<path d="{d}" fill="#E3ECF2" stroke="none"/>')

    # Цвета по слотам (как самолёты 1, 2, 3)
    slot_colors = ["#E32A2F", "#2563EB", "#2F9E6A"]
    all_spokes = []
    for idx, sp_list in enumerate(slots):
        col = slot_colors[idx % len(slot_colors)]
        dash = ' stroke-dasharray="4 3"' if idx == 2 and hybrid_svx_spokes else ""
        op = "0.65" if idx == 2 and hybrid_svx_spokes else "0.88"
        for i_sp, sp in enumerate(sp_list):
            all_spokes.append((sp, idx))
            bend = 0.09 if i_sp % 2 == 0 else -0.09
            svg.append(f'<path d="{arc_d(hub, sp, bend)}" fill="none" stroke="{col}" stroke-width="2.1" stroke-opacity="{op}" stroke-linecap="round"{dash}/>')

    # Если показан HYBRID-конфликт (Борт 3 уходит в SVX)
    if hybrid_svx_spokes:
        for i_sp, sp in enumerate(hybrid_svx_spokes):
            bend = -0.15 if i_sp % 2 == 0 else 0.14
            svg.append(f'<path d="{arc_d("SVX", sp, bend)}" fill="none" stroke="#D97706" stroke-width="2.4" stroke-dasharray="5 3" stroke-linecap="round"/>')

    # Узлы-лучи
    seen = set()
    for sp, idx in all_spokes:
        if sp in seen or sp == hub:
            continue
        seen.add(sp)
        x, y = pt_xy(sp)
        col = slot_colors[idx % len(slot_colors)]
        is_svx = sp == "SVX"
        r_dot = 5.2 if is_svx else 3.8
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_dot}" fill="#FFFFFF" stroke="{col}" stroke-width="2"/>')
        dx, dy, anchor = (offsets or {}).get(sp, (6, 3, "start"))
        lbl = (labels_ru or {}).get(sp, sp)
        svg.append(
            f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" font-size="9.5" font-weight="600" '
            f'fill="#1F2937" paint-order="stroke" stroke="#FFFFFF" stroke-width="2.6">{lbl}</text>'
        )

    # SVX маркер, если он не в слотах, а как база HYBRID
    if hybrid_svx_spokes:
        sx0, sy0 = pt_xy("SVX")
        svg.append(f'<rect x="{sx0-4.5:.1f}" y="{sy0-4.5:.1f}" width="9" height="9" rx="2" fill="#D97706" stroke="#FFFFFF" stroke-width="1.5"/>')
        if "SVX" not in seen:
            svg.append(f'<text x="{sx0-7:.1f}" y="{sy0-7:.1f}" text-anchor="end" font-size="9.5" font-weight="700" fill="#B45309" paint-order="stroke" stroke="#FFFFFF" stroke-width="2.6">SVX (Борт 3 в HYBRID)</text>')

    # Хаб в центре
    hx, hy = pt_xy(hub)
    svg.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="8" fill="#FFFFFF" stroke="#E32A2F" stroke-width="2.8"/>')
    svg.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="3.4" fill="#E32A2F"/>')
    h_dx, h_dy, h_anc = (offsets or {}).get(hub, (0, -12, "middle"))
    svg.append(
        f'<text x="{hx + h_dx:.1f}" y="{hy + h_dy:.1f}" text-anchor="{h_anc}" font-size="11.5" font-weight="700" '
        f'fill="#C0262B" paint-order="stroke" stroke="#FFFFFF" stroke-width="3.2">{(labels_ru or {}).get(hub, hub)}</text>'
    )

    if badge:
        svg.append(f'<rect x="8" y="8" width="{len(badge)*5.6 + 14:.0f}" height="20" rx="4" fill="#FFFFFF" fill-opacity="0.92" stroke="#D1D5DB"/>')
        svg.append(f'<text x="15" y="21.5" font-size="10" font-weight="700" fill="#111827">{badge}</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def main():
    geo = json.loads((WORKTREE / "data/processed/geo_map.json").read_text(encoding="utf-8"))
    ap = pd.read_csv(CONTEXT / "21_visual_explainer_draft_20261110/inputs/airports.csv", low_memory=False)
    ap = ap[ap["iata_code"].notna()].drop_duplicates("iata_code").set_index("iata_code")
    coords = {}
    for c in ["OMS", "SVX", "VOG", "KUF", "MRV", "AER", "LED", "ZIA", "OVB", "RMZ", "BAX", "TOF", "GSV", "GOJ", "ASF", "CEK", "UFA", "KJA", "PEE", "TJM", "IAR", "KZN", "CSY"]:
        r = ap.loc[c]
        coords[c] = (float(r["longitude_deg"]), float(r["latitude_deg"]))

    labels_ru = {
        "OMS": "Омск (OMS)", "VOG": "Волгоград (VOG)", "SVX": "SVX",
        "AER": "Сочи", "LED": "LED", "MRV": "Минводы", "KUF": "Самара",
        "OVB": "OVB", "RMZ": "Тобольск", "BAX": "Барнаул", "TOF": "Томск",
        "ZIA": "ZIA (Жуковский)", "GSV": "Саратов", "GOJ": "Н.Новгород",
        "ASF": "Астрахань", "CEK": "Челябинск",
    }

    off_oms = {
        "OMS": (-6, 17, "end"),
        "LED": (6, 3, "start"),
        "AER": (-7, 4, "end"),
        "MRV": (7, 8, "start"),
        "KUF": (-6, -4, "end"),
        "SVX": (-7, -5, "end"),
        "OVB": (-6, 8, "end"),
        "RMZ": (0, -9, "middle"),
        "BAX": (7, 10, "start"),
        "TOF": (7, -4, "start"),
    }
    svg_oms = build_svg_map(
        geo, coords, (28, 92, 41, 61.5), 350, 232,
        hub="OMS",
        slots=[["AER", "LED", "MRV"], ["KUF", "OVB", "SVX"], ["RMZ", "BAX", "TOF"]],
        hybrid_svx_spokes=["AER", "MRV", "LED"],
        labels_ru=labels_ru,
        offsets=off_oms,
        badge="OMS_RADIAL vs OMS_HYBRID",
    )

    off_vog = {
        "VOG": (-10, 4, "end"),
        "LED": (7, 4, "start"),
        "ZIA": (-6, -5, "end"),
        "AER": (-7, 6, "end"),
        "MRV": (0, 14, "middle"),
        "KUF": (6, -3, "start"),
        "GSV": (-7, -3, "end"),
        "GOJ": (7, -2, "start"),
        "ASF": (7, 4, "start"),
        "CEK": (0, 14, "middle"),
        "SVX": (0, -9, "middle"),
    }
    svg_vog = build_svg_map(
        geo, coords, (27, 65, 41.5, 61.5), 350, 232,
        hub="VOG",
        slots=[["LED", "ZIA", "AER"], ["MRV", "KUF", "GSV"], ["GOJ", "ASF", "CEK"]],
        hybrid_svx_spokes=["AER", "MRV", "LED"],
        labels_ru=labels_ru,
        offsets=off_vog,
        badge="VOG_RADIAL vs VOG_HYBRID",
    )

    # Табличные данные прямо из recomputed_programmes_summary.csv
    df = pd.read_csv(CONTEXT / "40_swarm_pricing_research_20261113/recomputed_programmes_summary.csv")

    def val(pid, cfg, scen, col="delta_known_operating_subtotal"):
        r = df[(df["programme_id"] == pid) & (df["config"] == cfg) & (df["scenario"] == scen)]
        return float(r[col].iloc[0])

    rows_spec = [
        ("OMS_RADIAL", "Омск · RADIAL (без волн)", "9 лучей из OMS, 1 об./день", "136.7 / 140.0"),
        ("OMS_HYBRID", "Омск · HYBRID (2 волны + SVX)", "Борт 3 в SVX ↔ AER/MRV/LED", "317.1 / 336.5"),
        ("OMS_HUB", "Омск · HUB (стыков. волны)", "Короткие плечи 2 об./день", "444.0 / 447.2"),
        ("OMS_BANK9", "Омск · BANK9 (жёсткий банк)", "9 коротких сиб. лучей ×2", "862.2 / 861.7"),
        ("VOG_RADIAL", "Волгоград · RADIAL (лидер стресса)", "Компактные 9 лучей, 141 дн. Ковра", "0.0 / 0.0"),
        ("VOG_HYBRID", "Волгоград · HYBRID (волны + SVX)", "Борт 3 в SVX ломает экономику", "86.3 / 107.8"),
        ("KUF_RADIAL", "Самара · RADIAL (137 дн. Ковра)", "9 лучей из KUF без волн", "0.0 / 0.0"),
        ("MRV_SEASONAL", "Минводы · SEASONAL (+лето Вс)", "Курортный RADIAL, риск 2028", "0.0 / 0.0"),
        ("AER_SEASONAL", "Сочи · SEASONAL (+лето Вс)", "−450M от учёта рынка уже в Базе", "0.0 / 0.0"),
        ("SVX_RADIAL", "Екатеринбург · RADIAL (база)", "Кластер SU (W28=0.339), без ухода KEEP", "0.0 / 0.1"),
    ]

    tr_html = []
    for pid, name, arch, peak in rows_spec:
        old_b = val(pid, "p09_legacy_check", "base") / 1e6
        base = val(pid, "comp_market_base", "base") / 1e6
        caut = val(pid, "comp_market_cautious", "cautious") / 1e6
        exp28 = val(pid, "comp_expansion_stress_2028", "cautious") / 1e6
        lf_b = val(pid, "comp_market_base", "base", "flight_load_factor") * 100
        flt = val(pid, "comp_market_base", "base", "calendar_flights")

        def fmt_v(x):
            cls = "pos" if x > 15 else ("neg" if x < -15 else "warn")
            s = f"+{x:.1f}" if x > 0 else f"{x:.1f}".replace("-", "−")
            return f'<td class="num {cls}">{s}</td>'

        hi_row = ' style="background:color-mix(in srgb, var(--primary) 7%, transparent)"' if pid in ("OMS_RADIAL", "VOG_RADIAL") else ""
        tr_html.append(
            f"<tr{hi_row}><td><b>{name}</b><div class='muted'>{arch}</div></td>"
            f"<td class='num muted'>{flt:.0f} · {lf_b:.0f}%</td>"
            f"{fmt_v(old_b)}{fmt_v(base)}{fmt_v(caut)}{fmt_v(exp28)}"
            f"<td class='num muted'>{peak}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<style>
  :root {{ font-family: var(--font-sans); }}
  body {{ margin: 0; color: var(--foreground); font-size: 12px; line-height: 1.4; }}
  h3 {{ margin: 0 0 3px 0; font-size: 13.5px; font-weight: 700; color: var(--foreground); }}
  .sub {{ margin: 0 0 10px 0; font-size: 11.2px; color: var(--muted-foreground); }}
  .grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }}
  .box {{ border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 12px; background: var(--card); }}
  .map-box {{ border: 1px solid var(--border); border-radius: var(--radius); padding: 8px; background: var(--card); }}
  .tag {{ display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-bottom: 4px; }}
  .t-ok {{ background: color-mix(in srgb, var(--success) 16%, transparent); color: var(--success); }}
  .t-bad {{ background: var(--destructive-surface); color: var(--destructive); }}
  .t-warn {{ background: var(--warning-surface); color: var(--warning); }}
  .muted {{ color: var(--muted-foreground); font-size: 10.5px; }}
  .pos {{ color: var(--success); font-weight: 600; }}
  .warn {{ color: var(--warning); font-weight: 600; }}
  .neg {{ color: var(--destructive); font-weight: 600; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 10px; font-size: 10.5px; color: var(--muted-foreground); margin: 6px 0 2px 0; }}
  .li {{ display: inline-flex; align-items: center; gap: 5px; }}
  .sw {{ width: 12px; height: 3px; border-radius: 2px; display: inline-block; }}
  .krow {{ display: flex; justify-content: space-between; gap: 6px; margin-top: 6px; font-size: 10.8px; border-top: 1px solid var(--border); padding-top: 6px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  th, td {{ text-align: left; padding: 4px 5px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  th {{ color: var(--muted-foreground); font-weight: 600; font-size: 10.3px; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .takeaways {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px; }}
  .tk {{ border-left: 3px solid var(--primary); padding: 4px 8px; background: color-mix(in srgb, var(--card) 70%, transparent); font-size: 11px; }}
  svg text {{ font-family: var(--font-sans); }}
</style>
</head>
<body>
  <h3>Что такое RADIAL и что он меняет для Red Wings (3 режима на 4 новых бортах: 1 резерв + 3 в небе)</h3>
  <p class="sub">В модели P09→P40 <b>E1 остаётся в SVX</b>, а новые борта N2–N4 (+ N1 резерв) летают 9 лучей по одной из 3 архитектур. При учёте живых конкурентов и тарифов <b>побеждает чистый RADIAL</b> — и вот почему это видно на карте.</p>

  <div class="grid3">
    <div class="box">
      <span class="tag t-ok">RADIAL · 1 об./день</span>
      <div><b>Чистые радиалы (bank=False)</b></div>
      <div class="muted">Все 3 борта сидят в новом хабе. Каждый день борт делает <b>1 рейс туда-обратно</b> (2 р/нед на каждый из 9 лучей). Без надуманных стыковок и лишних взлётов.</div>
      <div style="margin-top:5px;font-size:11px">Омск База: <span class="pos">+540.1M</span> · VOG: <span class="pos">+545.2M</span></div>
    </div>
    <div class="box">
      <span class="tag t-bad">HUB / BANK9 · волны</span>
      <div><b>Принудительные волны (bank=True)</b></div>
      <div class="muted">Короткие лучи (≤10 ч/день) гоняют <b>2 раза в день</b> ради волны 11:00→12:00. Рейсов на +19…+53% больше, керосин и сборы жгутся, а спрос не растёт.</div>
      <div style="margin-top:5px;font-size:11px">OMS_HUB: <span class="warn">+282.0M</span> · BANK9: <span class="neg">−745.4M</span></div>
    </div>
    <div class="box">
      <span class="tag t-warn">HYBRID · 2 волны + SVX</span>
      <div><b>Старый фаворит сломался рынком</b></div>
      <div class="muted">Борты 1–2 на волнах в новом хабе, а <b>Борт 3 уходит в SVX</b> на стволы SVX↔AER/MRV/LED. Без конкурентов был +723M, на рынке бьётся об U6/SU/DP.</div>
      <div style="margin-top:5px;font-size:11px">OMS_HYB Стресс: <span class="neg">−452.5M</span> (vs <span class="warn">−195.5M</span>)</div>
    </div>
  </div>

  <div class="grid2">
    <div class="map-box">
      {svg_oms}
      <div class="legend">
        <span class="li"><span class="sw" style="background:#E32A2F"></span>Борт 1: AER/LED/MRV</span>
        <span class="li"><span class="sw" style="background:#2563EB"></span>Борт 2: KUF/OVB/SVX</span>
        <span class="li"><span class="sw" style="background:#2F9E6A;opacity:.75"></span>Борт 3 (в RADIAL): RMZ/BAX/TOF</span>
        <span class="li"><span class="sw" style="background:#D97706"></span>Уход Борта 3 в SVX (HYBRID)</span>
      </div>
      <div class="krow">
        <span><b>OMS_RADIAL:</b> 2 662 рейса · LF 50%</span>
        <span>База <b class="pos">+540M</b> · 2028 <b class="neg">−196M</b></span>
      </div>
    </div>
    <div class="map-box">
      {svg_vog}
      <div class="legend">
        <span class="li"><span class="sw" style="background:#E32A2F"></span>Борт 1: LED/ZIA/AER</span>
        <span class="li"><span class="sw" style="background:#2563EB"></span>Борт 2: MRV/KUF/GSV</span>
        <span class="li"><span class="sw" style="background:#2F9E6A;opacity:.75"></span>Борт 3 (в RADIAL): GOJ/ASF/CEK</span>
        <span class="li"><span class="sw" style="background:#D97706"></span>Уход Борта 3 в SVX (HYBRID)</span>
      </div>
      <div class="krow">
        <span><b>VOG_RADIAL:</b> 141 дн. «Ковра» · ZIA≠MOW</span>
        <span>База <b class="pos">+545M</b> · 2028 <b class="pos">+294M</b></span>
      </div>
    </div>
  </div>

  <div class="box" style="padding:8px 10px">
    <table>
      <thead>
        <tr>
          <th>Программа (24 мес., Δ к KEEP, RW_SUPPORT_NEW = 0)</th>
          <th class="num">Рейсов · LF</th>
          <th class="num">Старый P09</th>
          <th class="num">P40 База</th>
          <th class="num">Осторожн.</th>
          <th class="num">Стресс 2028</th>
          <th class="num">Пик кассы О/28</th>
        </tr>
      </thead>
      <tbody>
        {"".join(tr_html)}
      </tbody>
    </table>
    <div class="takeaways">
      <div class="tk"><b>1. Что меняет отказ от HYBRID/HUB:</b> у Омска убирает провал <b>−257M</b> в стрессе 2028 (и <b>+64M</b> в Базе), режет пик оборотной дыры с <b>337M до 140M</b> и не лезет в перегруженные стволы SVX↔AER/LED.</div>
      <div class="tk"><b>2. Почему VOG обгоняет OMS в стрессе:</b> короткие европейские лучи Волгограда жгут меньше топлива на круг (+294M vs −196M в 2028), но цена этого — <b>141 день «Ковра»</b> (против 7–24 у OMS) и ставка на Жуковский (ZIA).</div>
      <div class="tk"><b>3. Важная поправка про базу KEEP:</b> у всех не-SVX программ <b>+678M</b> (База) и <b>+1 040M</b> (Остор.) даёт сам уход N2–N4 со старых убыточных рейсов SVX. Плюс в расчёте нет лизинга/открытия базы (UNKNOWN).</div>
    </div>
  </div>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print("Wrote", OUT, "bytes:", len(html))


if __name__ == "__main__":
    main()
