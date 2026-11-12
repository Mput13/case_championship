#!/usr/bin/env python3
"""Draw the independently reproduced city screening; not a profitability ranking."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

OUT=Path(__file__).resolve().parent
rows=list(csv.DictReader((OUT/'screening_scores.csv').open()))[:8]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12})
fig,ax=plt.subplots(figsize=(8.2,4.7),layout='constrained')
colors=['#acb5bd' if not r['rank_500'] else '#316987' for r in rows]
ax.barh(range(8),[float(r['score'])*100 for r in rows],color=colors,height=.61)
ax.set_yticks(range(8),[r['city'] for r in rows]);ax.invert_yaxis()
ax.set_xlim(0,86);ax.set_xticks([0,20,40,60,80]);ax.set_xlabel('Взвешенный балл из 100 · одинаковые веса и шкалы')
for i,r in enumerate(rows):
    score=float(r['score'])*100
    suffix=f"  → №{r['rank_500']}" if r['rank_500'] else '  → исключён'
    ax.text(score+.7,i,f'{score:.1f}'.replace('.',',')+suffix,va='center',fontsize=10)
ax.set_title('Рейтинг всех городов и действие фильтра 500 км',loc='left',pad=31,fontsize=14)
ax.legend(handles=[Patch(color='#316987',label='Проходит фильтр'),Patch(color='#acb5bd',label='Исключён фильтром')],
          loc='lower left',bbox_to_anchor=(0,1.005),frameon=False,ncol=2,fontsize=10,borderaxespad=0)
ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0)
ax.spines['bottom'].set_color('#c5cbd0');ax.set_axisbelow(True);ax.grid(axis='x',color='#e6e9eb',linewidth=.7)
fig.savefig(OUT/'screening.png',dpi=180)
fig.savefig(OUT/'screening.svg')
svg=OUT/'screening.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
