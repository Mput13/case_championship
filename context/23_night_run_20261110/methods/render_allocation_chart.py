#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    data=list(csv.DictReader((ROOT/'runs/allocation_v1/summary.csv').open()))
    marks=[];x=lambda v:155+v*1.6
    for tick in [0,50,100,150,200,250]:
        marks.append(f'<line class="grid" x1="{x(tick)}" x2="{x(tick)}" y1="5" y2="195"/><text x="{x(tick)}" y="218" text-anchor="middle">{tick}</text>')
    for i,(n,recipe)in enumerate([('H_UFA_4','C'),('H_UFA_8','C'),('H_UFA_4','N'),('H_UFA_8','N')]):
        r=next(r for r in data if(r['candidate'],r['recipe'],r['scenario'],r['scale'],r['objective'])==(n,recipe,'base','1.0','CONTRIBUTION'))
        y=25+i*45;gain=float(r['contribution_delta_vs_local_first'])/1000
        marks.append(f'<text x="0" y="{y+4}">{n}, {recipe}</text><line x1="{x(0)}" x2="{x(gain)}" y1="{y}" y2="{y}" stroke="var(--chart-{1 if recipe=="C"else 2})" stroke-width="13"/><text x="{x(gain)+8}" y="{y+4}">+{gain:.1f}</text>')
    html='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Распределение кресел</title><style>:root{font-family:var(--font-sans,system-ui);color:var(--foreground);font-size:14px}body{margin:0}p{line-height:1.5;margin:8px 0}svg{width:100%;height:240px}svg text{font:12px var(--font-sans,system-ui);fill:var(--foreground)}.grid{stroke:var(--border)}.note{font-size:12px;color:var(--muted-foreground)}</style><body><p>Улучшение недельного вклада при распределении тех же мест, тыс. ₽</p><svg viewBox="0 0 660 235" role="img" aria-label="Добавка от максимизации вклада по сравнению с local-first, C и N demand recipes">'''+''.join(marks)+'''</svg><p class="note">Base. C — исходные bands; N — годовой proxy ÷104. Все четыре результата после улучшения остаются отрицательными. Спрос, тарифы, рейсы и индивидуальные квоты предложений сохранены. Проверка владельца; независимый review нового опыта pending.</p></body></html>'''
    (ROOT/'runs/allocation_v1/allocation_chart.html').write_text(html)


if __name__=='__main__':main()
