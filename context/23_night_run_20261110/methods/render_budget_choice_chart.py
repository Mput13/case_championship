#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    data=list(csv.DictReader((ROOT/'runs/budget_choice_v1/candidate_domains.csv').open()))
    colors={'D_previous_best8':1,'D_SVX8':2,'H_UFA_8':3,'D_SVX8+H_UFA_4':4}
    labels={'D_previous_best8':'D_previous_best8','D_SVX8':'D_SVX8','H_UFA_8':'UFA8','D_SVX8+H_UFA_4':'D_SVX8 + UFA4'}
    marks=[];x=lambda value:155+value/5.5*465
    rows=[('base','FINAL_MODEL_PAIR_COUNT_8_12','Base: 8–12'),('base','FINAL_MODEL_PAIR_COUNT_8_12_AND_NEW_UFA_BASE','Base: + новая база'),('cautious','FINAL_MODEL_PAIR_COUNT_8_12','Cautious: 8–12'),('cautious','FINAL_MODEL_PAIR_COUNT_8_12_AND_NEW_UFA_BASE','Cautious: + база')]
    for tick in range(6):
        marks.append(f'<line class="grid" x1="{x(tick)}" x2="{x(tick)}" y1="0" y2="230"/><text x="{x(tick)}" y="252" text-anchor="middle">{tick}</text>')
    for i,(sc,domain,label)in enumerate(rows):
        active=[r for r in data if r['capture_law']=='COUNT_ALL_OFFERS'and r['scenario']==sc and r['choice_domain']==domain and r['witness_F']!='']
        assert len(active)==2
        a,b=sorted(active,key=lambda r:-float(r['C']))
        assert a['b']==b['b']
        threshold=(float(a['C'])-float(b['C']))/(int(a['n'])-int(b['n']))/1e6
        y=25+i*58
        marks.append(f'<text x="0" y="{y+4}">{label}</text>')
        for l,r,candidate in [(0,threshold,a['candidate']),(threshold,5.5,b['candidate'])]:
            marks.append(f'<line x1="{x(l)}" x2="{x(r)}" y1="{y}" y2="{y}" stroke="var(--chart-{colors[candidate]})" stroke-width="12"/>')
        marks.append(f'<text x="{x(threshold)}" y="{y+25}" text-anchor="middle">{threshold:.3f}</text>')
    legend=''.join(f'<span><i style="background:var(--chart-{v})"></i>{labels[k]}</span>'for k,v in colors.items())
    html='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Условия состава сети</title><style>:root{font-family:var(--font-sans,system-ui);color:var(--foreground);font-size:14px}body{margin:0}p{line-height:1.5;margin:8px 0}svg{width:100%;height:280px}svg text{font:12px var(--font-sans,system-ui);fill:var(--foreground)}.grid{stroke:var(--border)}.legend{display:flex;gap:9px 20px;flex-wrap:wrap;font-size:12px}.legend span{display:flex;gap:6px;align-items:center}i{width:18px;height:4px;margin-top:6px}.note{font-size:12px;color:var(--muted-foreground)}</style><body><p>Условный лучший вариант из допустимых действий</p><div class="legend">'''+legend+'''</div><svg viewBox="0 0 660 270" role="img" aria-label="Границы по дополнительной недельной плате за борт, при разных условиях состава">'''+''.join(marks)+'''</svg><p>F: добавочная плата за борт, млн ₽ за модельную неделю</p><p class="note">Исходный C, local-first, четыре рабочих метки максимум. Прочие исключённые статьи равны; новая база — отдельное условие выбора. Показанный диапазон F не оценка реальных ставок. Все J отрицательны; count gate не operating acceptance. Новый условный расчёт: независимая проверка pending.</p></body></html>'''
    (ROOT/'runs/budget_choice_v1/budget_choice_chart.html').write_text(html)


if __name__=='__main__':main()
