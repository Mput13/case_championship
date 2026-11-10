#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    with (ROOT/'runs/kover_demand_v1/interaction_deltas.csv').open()as f:
        rows=[r for r in csv.DictReader(f)if r['scenario']=='base'and r['policy']=='cancel_pretravel_no_protection']
    x=lambda v:130+(v+1.2)/2.4*500
    marks=[]
    for tick in [-1,-.5,0,.5,1]:
        marks.append(f'<line class="grid" x1="{x(tick)}" x2="{x(tick)}" y1="10" y2="210"/><text x="{x(tick)}" y="235" text-anchor="middle">{tick:+g}</text>')
    for i,r in enumerate(rows):
        y=35+i*100
        marks.append(f'<text x="0" y="{y+25}">{r["candidate"]}</text>')
        for j,(field,recipe)in enumerate([('C_delta','C'),('N_delta','N')],1):
            v=float(r[field])/1e6;yy=y+(j-1)*32
            marks.append(f'<line x1="{x(0)}" x2="{x(v)}" y1="{yy}" y2="{yy}" stroke="var(--chart-{j})" stroke-width="13"/><text x="{x(v)+(7 if v>=0 else -7)}" y="{yy+4}" text-anchor="{"start"if v>=0 else "end"}">{v:+.3f}</text>')
    html='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Отмена и рецепт спроса</title><style>:root{font-family:var(--font-sans,system-ui);color:var(--foreground);font-size:14px}body{margin:0}p{line-height:1.5;margin:8px 0}svg{width:100%;height:265px}svg text{font:12px var(--font-sans,system-ui);fill:var(--foreground)}.grid{stroke:var(--border)}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12px}.legend span{display:flex;gap:6px;align-items:center}i{width:18px;height:4px}.note{font-size:12px;color:var(--muted-foreground)}</style><body><p>Добавка отмены первой волны, млн ₽. Base, до неизвестных компенсаций и других расходов.</p><div class="legend"><span><i style="background:var(--chart-1)"></i>C: bands Цири</span><span><i style="background:var(--chart-2)"></i>N: годовой proxy ÷ 104</span></div><svg viewBox="0 0 700 255" role="img" aria-label="Смена знака денежной добавки отмены при другом сценарном спросе">'''+''.join(marks)+'''</svg><p class="note">Рейсы и расходы одинаковы; потерянная выручка пересчитана по каждому input set. Положительная добавка означает уменьшение модельного убытка при невыполненных поездках. Реальный OD и полный бюджет неизвестны; независимая проверка нового опыта pending.</p></body></html>'''
    (ROOT/'runs/kover_demand_v1/cancel_recipe_chart.html').write_text(html)


if __name__=='__main__':main()
