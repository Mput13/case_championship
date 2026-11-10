#!/usr/bin/env python3
"""Self-contained chart from exact budget outputs; no server or external assets."""
import csv
import html
from pathlib import Path

ROOT=Path(__file__).resolve().parent
NAMES={'D_SVX8':'SVX · 8 пар','D_previous_best8':'ZIA/SVX · 8 пар','H_UFA_4':'UFA · 4 луча','H_UFA_8':'UFA · 8 лучей'}


def main():
    with (ROOT/'runs/budget_v1/supply_upper_bounds.csv').open()as f:data=list(csv.DictReader(f))
    panels=[]
    for scenario,title in [('base','Базовый сценарий'),('cautious','Осторожный сценарий')]:
        rs=[r for r in data if r['scenario']==scenario]
        def x(v):return 175+(v+30)/38*470
        marks=[]
        for tick in [-30,-20,-10,0]:
            marks.append(f'<line x1="{x(tick)}" y1="20" x2="{x(tick)}" y2="210" class="grid {"zero"if tick==0 else ""}"/><text x="{x(tick)}" y="233" text-anchor="middle">{tick}</text>')
        for i,r in enumerate(rs):
            y=42+i*48;a=float(r['current_contribution'])/1e6;b=float(r['optimistic_contribution_upper'])/1e6
            marks.append(f'<text x="0" y="{y+4}" class="label">{html.escape(NAMES[r["network"]])}</text><line x1="{x(a)}" y1="{y}" x2="{x(b)}" y2="{y}" class="span"/><circle cx="{x(a)}" cy="{y}" r="5" class="actual"/><circle cx="{x(b)}" cy="{y}" r="5" class="bound"/><text x="{x(a)}" y="{y+20}" text-anchor="middle" class="value">{a:.2f}</text><text x="{x(b)}" y="{y-11}" text-anchor="middle" class="value">{b:+.2f}</text>')
        panels.append(f'<section><h3>{title}</h3><svg viewBox="0 0 700 246" role="img" aria-label="{title}: вклад авторской программы и верхний предел при продаже всех местных кресел">'+''.join(marks)+'</svg></section>')
    page='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Границы вклада фиксированных программ</title><style>
:root{font-family:var(--font-sans,system-ui);color:var(--foreground);font-size:14px}body{margin:0}h3{font-size:15px;margin:12px 0 2px;font-weight:600}p{margin:8px 0;line-height:1.5}.muted,.value{color:var(--muted-foreground);fill:var(--muted-foreground)}.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px}.legend span{display:inline-flex;align-items:center;gap:6px}.dot{width:9px;height:9px;border-radius:50%;display:inline-block}.dot.a,.actual{background:var(--chart-1);fill:var(--chart-1)}.dot.b,.bound{background:var(--chart-2);fill:var(--chart-2)}svg{width:100%;height:260px;overflow:visible}svg text{font:12px var(--font-sans,system-ui);fill:var(--foreground)}svg text.label{font-weight:500}.grid{stroke:var(--border);stroke-width:1}.zero{stroke:var(--foreground);stroke-dasharray:3 4;opacity:.5}.span{stroke:var(--muted-foreground);stroke-width:2;opacity:.5}.note{font-size:12px;color:var(--muted-foreground)}@media(max-width:480px){svg{height:220px}svg text{font-size:13px}}</style><body>
<p>Вклад до неизвестных дополнительных расходов, млн ₽ за 7–13 декабря 2026.</p><div class="legend"><span><i class="dot a"></i>Авторские продажи и переток</span><span><i class="dot b"></i>Все местные кресла, без перетока</span></div>'''+''.join(panels)+'''<p class="note">Верхний предел снимает ограничения спроса, сохраняя рейсы, тарифы и затраты Цири @93fa5cf. Номинальные 100 мест — сценарий. Положительный предел не подтверждает продажи; независимая проверка нового расчёта pending.</p></body></html>'''
    target=ROOT/'runs/budget_v1/budget_chart.html';target.write_text(page)
    print(target)


if __name__=='__main__':main()
