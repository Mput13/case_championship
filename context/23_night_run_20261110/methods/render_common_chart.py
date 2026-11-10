#!/usr/bin/env python3
"""Render exact recipe-boundary curves as a standalone, server-free SVG/HTML."""
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent
NAMES={'D_SVX8':'D_SVX8','H_UFA_4':'H_UFA_4','H_UFA_8':'H_UFA_8'}


def main():
    with (ROOT/'runs/common_demand_v1/affine_regions.csv').open()as f:data=list(csv.DictReader(f))
    panels=[]
    for sc,title,low,high in [('base','Базовый сценарий',-10,0),('cautious','Осторожный сценарий',-30,-10)]:
        x=lambda a:55+float(a)*580
        y=lambda v:30+(high-v)/(high-low)*220
        marks=[]
        ticks=[-10,-8,-6,-4,-2,0]if sc=='base'else [-30,-25,-20,-15,-10]
        for tick in ticks:
            marks.append(f'<line class="grid" x1="55" x2="635" y1="{y(tick)}" y2="{y(tick)}"/><text x="43" y="{y(tick)+4}" text-anchor="end">{tick}</text>')
        for a in [0,.25,.5,.75,1]:marks.append(f'<text x="{x(a)}" y="271" text-anchor="middle">{a:g}</text>')
        for i,name in enumerate(NAMES,1):
            rr=[r for r in data if r['network']==name and r['scenario']==sc and r['recipe']=='C_TO_N_BLEND']
            points=[]
            for r in rr:
                for a in [float(r['left']),float(r['right'])]:
                    v=(float(r['contribution_intercept'])+a*float(r['contribution_slope']))/1e6
                    points.append(f'{x(a)},{y(v)}')
            marks.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="var(--chart-{i})" stroke-width="2.5"/>')
        if sc=='base':
            a=.6835090019901081;v=-3.168101767787288
            marks.append(f'<line x1="{x(a)}" x2="{x(a)}" y1="30" y2="250" stroke="var(--muted-foreground)" stroke-dasharray="3 4"/><circle cx="{x(a)}" cy="{y(v)}" r="4" fill="var(--foreground)"/><text x="{x(a)+8}" y="45">α = 0.684</text>')
        panels.append(f'<section><h3>{title}</h3><svg viewBox="0 0 680 290" role="img" aria-label="{title}: изменение вклада при смеси рецептов спроса">'+''.join(marks)+'</svg></section>')
    page='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Чувствительность к рецепту спроса</title><style>
:root{font-family:var(--font-sans,system-ui);color:var(--foreground);font-size:14px}body{margin:0}p{line-height:1.5;margin:8px 0}h3{font-size:15px;margin:12px 0 0}svg{width:100%;height:270px}svg text{font:12px var(--font-sans,system-ui);fill:var(--foreground)}.grid{stroke:var(--border)}.legend{display:flex;gap:18px;font-size:12px;flex-wrap:wrap}.legend span{display:flex;gap:6px;align-items:center}.line{height:3px;width:20px}.note{font-size:12px;color:var(--muted-foreground)}@media(max-width:480px){svg{height:220px}}</style><body>
<p>Вклад до базы и парка, млн ₽/неделю. Одни рейсы, тарифы и расходы; меняется только сценарный спрос.</p>
<div class="legend"><span><i class="line" style="background:var(--chart-1)"></i>D_SVX8</span><span><i class="line" style="background:var(--chart-2)"></i>H_UFA_4</span><span><i class="line" style="background:var(--chart-3)"></i>H_UFA_8</span></div>'''+''.join(panels)+'''<p class="note">По горизонтали α: 0 — bands Цири, 1 — годовой proxy Анастасии ÷ 104. Смесь D(α) = (1−α)C + αN. α не вероятность и не измеренная сезонность. Новый общий опыт — предложение; независимая проверка pending.</p></body></html>'''
    (ROOT/'runs/common_demand_v1/recipe_chart.html').write_text(page)


if __name__=='__main__':main()
