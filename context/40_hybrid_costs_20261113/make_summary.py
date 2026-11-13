#!/usr/bin/env python3
"""Create the compact chart from the accepted central-budget CSV; stdlib only."""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
with (HERE / 'calculation/results.csv').open(encoding='utf-8-sig', newline='') as f:
    data = {r['case_id']: r for r in csv.DictReader(f)
            if r['market'] == 'base' and r['budget'] == 'base'}
labels = [('OMS', 'Омск · 7 бортов'),
          ('DIRECT2', 'Два московских треугольника · 4 борта'),
          ('HYBRID', 'Гибрид · 11 бортов')]
maximum = max(float(data[k]['network_subtotal_rub']) for k, _ in labels)
sections = []
for key, title in labels:
    r = data[key]
    before = float(r['network_subtotal_rub'])
    additional = float(r['annual_or_period_recurring_rub'])
    after = float(r['residual_after_recurring_rub'])
    assert abs(before - additional - after) < .01
    sections.append(f'''<section>
      <div class="line"><strong>{title}</strong><span>{before/1e6:.0f} − {additional/1e6:.0f} = <b>{after/1e6:.0f}</b></span></div>
      <div class="track" aria-label="{title}: до сметы {before/1e6:.1f}, дополнительные расходы {additional/1e6:.1f}, остаток {after/1e6:.1f} млн рублей">
        <div class="bar" style="width:{100*before/maximum:.6f}%">
          <div class="remaining" style="width:{100*after/before:.6f}%"></div>
          <div class="cost" style="width:{100*additional/before:.6f}%"></div>
        </div>
      </div>
    </section>''')
html = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color-scheme:light dark}*{box-sizing:border-box}body{margin:0;font-family:var(--font-sans,system-ui);color:var(--foreground)}
h3{font-size:18px;margin:0 0 8px}p{font-size:13px;line-height:1.5;margin:0 0 12px;color:var(--muted-foreground,var(--foreground))}
section{margin:18px 0}.line{display:flex;justify-content:space-between;gap:12px;font-size:14px;line-height:1.5;margin-bottom:7px}
.line span{white-space:nowrap;font-variant-numeric:tabular-nums}.track{height:25px;background:var(--secondary);border-radius:4px}.bar{height:100%;display:flex;overflow:hidden;border-radius:4px}
.remaining{background:var(--chart-1,#3b82f6)}.cost{background:var(--chart-2,#f59e0b)}
.legend{display:flex;gap:20px;flex-wrap:wrap;font-size:12px;margin:15px 0}.dot{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
.note{padding:12px;border-radius:var(--radius,8px);background:var(--secondary);font-size:13px;line-height:1.5}
@media(max-width:500px){.line{display:block}.line span{display:block}.line strong{font-size:13px}}
</style>
<h3>Остаток после дополнительной сметы</h3>
<p>Млн ₽ за модельный год после полного ввода. Базовый рынок, центральная смета. Не фактическая прибыль.</p>
''' + ''.join(sections) + '''
<div class="legend"><span><i class="dot remaining"></i>Остаток</span><span><i class="dot cost"></i>Дополнительные ежегодные расходы</span></div>
<div class="note">В смете — расходы базы и сценарное страхование. Покупка и лизинг самолётов не включены. Цены договоров и право на топливный зачёт требуют подтверждения. Старые числа в презентации автоматически не заменены.</div>
</html>'''
(HERE / 'summary.html').write_text(html, encoding='utf-8')
print('summary.html generated from calculation/results.csv')
