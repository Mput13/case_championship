#!/usr/bin/env python3
"""Readable decision note from the current frozen calculation exports."""
import csv,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'context/16_conditional_decision';M=P/'model'
def rows(n):return list(csv.DictReader((M/n).open()))
def main():
 comp=rows('comparison.csv');idx={(r['network'],r['scenario']):r for r in comp}
 route_rows=rows('routes.csv');direct_pairs=int(idx['D_case8','base']['physical_pairs']);direct_description='; '.join('–'.join(j['route'])+f" ({j['frequency']} вылет/сторону/нед.)"for j in json.loads((M/'selected_networks.json').read_text())['D_case8']['jobs'])
 names={'NO_LAUNCH':'Без нового запуска','D_pilot':'Прямой пилот SVX–MRV','D_case8':f'Новая прямая программа, {direct_pairs} пар','S_UFA_8_1':'Новая база UFA, 8 прямых без пересадок','H_UFA_8':'Хаб UFA, 8 лучей','H_GOJ_8':'Хаб GOJ, 8 лучей','H_CEK_8':'Хаб CEK, 8 лучей','H_TJM_8':'Хаб TJM, 8 лучей','B0_reference':'Б0 — исходный ориентир'}
 short=[];table=['| Вариант | Частота/сторону | Плечи / блок‑ч | Рабочие + резерв¹ | Вклад база / осторожный, млн ₽² |','|---|---:|---:|---:|---:|']
 for n,label in names.items():
  b,c=idx[n,'base'],idx[n,'cautious'];ff=sorted({int(r['departures_each_direction'])for r in route_rows if r['network']==n});f=0 if not ff else ff[0]if len(ff)==1 else f'{ff[0]}–{ff[-1]}'
  reserve=0 if n=='NO_LAUNCH'else 1;delta=float(b['contribution_before_base_fleet_opportunity'])/1e6;caut=float(c['contribution_before_base_fleet_opportunity'])/1e6
  table.append(f"| {label} | {f} | {b['weekly_legs']} / {float(b['weekly_block_hours']):.1f} | {b['active_allocated']} + {reserve} | {delta:.2f} / {caut:.2f} |")
  short.append(dict(network=n,label=label,frequency_each_direction=f,weekly_legs=b['weekly_legs'],weekly_block_hours=b['weekly_block_hours'],allocated_active=b['active_allocated'],reserve_condition=reserve,base_journeys=b['sold_journeys'],base_transfers=b['transfer_journeys'],base_incremental_revenue_RUB=b['incremental_revenue'],base_incremental_operating_cost_RUB=b['incremental_operating_cost'],base_contribution_RUB=b['contribution_before_base_fleet_opportunity'],cautious_contribution_RUB=c['contribution_before_base_fleet_opportunity']))
 with (P/'comparison_short.csv').open('w',newline='')as f:w=csv.DictWriter(f,short[0].keys(),lineterminator='\n');w.writeheader();w.writerows(short)
 gate=next(r for r in rows('pilot_booking_gate.csv')if r['scenario']=='base');threshold=float(gate['required_paid_pax_before_fixed']);paid=math.ceil(threshold*1.1);margin=float(gate['net_new_margin_per_booked']);fc=float(gate['flight_cost']);left=2*(paid*margin-fc)
 thresholds=rows('breakeven.csv');ratio=lambda n,par:float(next(r['breakeven_multiplier']for r in thresholds if r['network']==n and r['scenario']=='base'and r['parameter']==par and r['fixed_per_allocated_tail_week']=='0'))
 demand3=next(float(r['contribution'])/1e6 for r in rows('sensitivity.csv')if r['network']=='D_case8'and r['scenario']=='base'and r['parameter']=='demand'and r['value']=='3')
 mini=max([r for r in comp if r['scenario']=='base'and r['network'].startswith('H_')and r['network'].endswith('_4')],key=lambda r:float(r['contribution_before_base_fleet_opportunity']))
 hubgap=(float(idx['D_case8','base']['contribution_before_base_fleet_opportunity'])-float(idx['H_UFA_8','base']['contribution_before_base_fleet_opportunity']))/1e6
 note=f'''# Условная рекомендация команде — 9 ноября 2026

**Предлагаю сейчас не открывать новую базу и не запускать всю программу. Следующий шаг — проверка небольшого прямого пилота из Екатеринбурга. Уфу оставить первым кандидатом на полноценный хаб после подтверждения спроса и договорной экономики. Это предложение, решение команды не принято.**

## Сравнение после сокращения сетей

Одинаковый расчётный период: 7–13 декабря 2026. Общий верхний ресурс — 4 рабочих SSJ по 100 кресел и 1 резерв; фактическая доступность неизвестна. Прямая сеть построена независимо из ZIA/SVX: обороты/треугольники, 1–3 раза в неделю, удаление и замена слабых связок. Хабы сокращены до 4/6/8 лучей. Полный ограниченный перебор и его границы — в расчётных приложениях.

{chr(10).join(table)}

¹ Считаются все выделенные рабочие борта, а не только одновременный дневной пик. Один резерв в SVX не покрывает ZIA мгновенно. У новой радиальной базы нет пересадочного продукта; её редкие обороты распределены по неделе. ² До фиксированного парка, новой базы и альтернативной стоимости. Ноль — отсутствие добавочного проекта, а не нулевая прибыль RW. Б0 сохранена, но две её пары не проходят консервативный экран дальности и не допускаются в новую сеть.

**Улучшенная прямая программа ({direct_pairs} пар):** {direct_description}. Удалены слабые/дальностно спорные межрегиональные плечи; дополнительные частоты не оправдались. Программа всё ещё убыточна. При разрешённом отказе от слабых рейсов модель выбирает не добавлять программу. Это подтверждено отдельной проверкой каждой OD, но только при заданных предположениях.

**Полный условный хаб UFA:** GOJ, KUF, OMS, NJC, VOG, MRV, ARH, GSV, по 2 оборота/неделю с обратными стыковками на разных датах. Он лучше других проверенных восьмилучевых хабов в обоих сценариях, но хуже улучшенной прямой программы ещё до новой базы. Четырёхлучевой мини‑хаб тоже отрицателен: лучший базовый {mini['network'][2:5]} — {float(mini['contribution_before_base_fleet_opportunity'])/1e6:.2f} млн ₽/неделю. Он не заменяет требуемую кейсом сеть 8–12 направлений.

## Что известно, а что предполагаем

**Факты:** на UFA–MRV опубликованы [4 рейса Azimuth в каждую сторону](research/ufa_mrv_calendar.csv) целевой недели. На SVX–MRV есть [первичная страница Ural Airlines](https://www.uralairlines.ru/schedule/flight/SVX/MRV/U6-205/); точные декабрьские частоты/цены не подтверждены. RW [объявляла этот маршрут в 2021](https://flyredwings.com/press/news/red-wings-budet-letat-iz-ekaterinburga-v-mineralnye-vody/), что не доказывает собственные продажи 2026. Пилот может быть усилением/возобновлением, а не новой нишей. [Флот RW](https://flyredwings.com/about/park/) содержит 20 SSJ по 100 мест, но свободные борта неизвестны. Публичное топливо UFA — 136 300 ₽/т без НДС с 11 ноября; сетевой договор не установлен.

**Предположения:** фактических конечных OD, чистых тарифов, перетока, договорной базы и доступного парка не получено. Пересадка занимает два датированных рейса, тариф считается один раз, потерянная выручка RW вычитается. Кресла, загрузка и аэропортовый поток не использованы как доказательство спроса. Старые рейсы сохраняются; экономия их снятия не начисляется.

Пять решающих неизвестных — [таблица с основаниями и источниками](decision_parameters.csv):

| Параметр | Как ограничили неопределённость | Что меняет |
|---|---|---|
| Конечный OD и привлечение | Общая шкала OD ×0,5–3; отдельно рынки UFA/GOJ ×0,5–2 | Город, сеть, возможность вообще продавать рейс |
| Чистый доход за поездку | ×0,75–2; старый потерянный доход за поездку RW меняется так же | Знак вклада и ценность пересадок |
| Переменная стоимость, база/поддержка | Общие затраты ×0,7–1,3; signed бюджет базы; субсидия 0 без договора | Знак и преимущество новой базы |
| Переток RW | Неизвестный: до 20%/40%; опубликованная RW: отдельный сценарий 60%/80%, стресс до 100% | Может убрать почти весь прирост пилота |
| Свободные самолёты, резерв, ТО/слоты/MCT | Жёсткие условия допуска; фиксированные затраты считаются отдельно | Может запретить запуск независимо от рейтинга |

**Это арифметические стрессы, не эмпирические диапазоны.** Общая шкала расстояний и годовой сегментный аналог KUF–MRV дают лишь порядок величины. Половина/удвоение/утроение проверяют ошибку масштаба; вероятности неизвестны. Три задания Luna и ограниченная проверка первичных источников не дали закрытых OD, чистой выручки и договоров. Дальше нужны продажи и коммерческие предложения, а не общие новости. [Принятые сведения и ограничения](research/decision_evidence.csv).

## Предлагаемый порядок запуска

1. **Сейчас и до H1 2027 — без новой программы и без расходов на базу, пока условия не выполнены.** Проверить блоковый заказ/оплачиваемый спрос на SVX–MRV, зимних конкурентов, собственные продажи RW и действительно свободный самолёт с резервом. Ничего участникам или потенциальным заказчикам в рамках этой работы не отправлялось.
2. **Первый пилот — SVX–MRV, 1 оборот/неделю, только после прохождения порогов и при наличии свободного существующего SSJ.** При условных чистых 14 тыс. ₽ за поездку, перетоке не более 5% и стоимости плеча не выше {fc/1e6:.3f} млн ₽ нужно минимум **{math.ceil(threshold)} платящих пассажиров в каждую сторону** для покрытия переменных расходов. Для 10% запаса по этим расходам — **{paid} подтверждённых пассажира или эквивалентная гарантия оплаты**; это не целевая загрузка, выданная за спрос. После такого запаса остаётся лишь около {left/1e6:.2f} млн ₽/неделю на дополнительные фиксированные расходы и отвлечённый вклад. Если выделение борта и резерва стоит условный 1 млн ₽/неделю, при том же тарифе нужно 124 пассажира на 100 мест — **запуск не проходит**. В осторожном сценарии даже без fixed требуется 180 на плечо — тоже запрет. Эти условия не подтверждены договорами.
3. **Расширять прямую программу по одному положительному добавлению.** Переход 1→2→3 проверен отдельно; в базе каждое усиление ухудшает вклад. Сначала доказать прирост денег после перетока и всех добавочных расходов, затем добавлять частоту/пару. Не запускать все восемь ради формального масштаба.
4. **Вернуться к хабу UFA, если появится подтверждённый трансферный продукт и положительная полная экономика.** Сейчас полный хаб требует ещё примерно 11,48 млн ₽/неделю для нулевого переменного вклада, плюс базу/парк; для равенства с уже убыточной прямой программой — улучшение на {hubgap:.2f} млн ₽/неделю плюс цену базы. Новые SJ100 по условию кейса не раньше H2 2027; реальные поставки/выделение не обещаны и сами по себе эти деньги не создают. Расширение до 2028 — только после повторной проверки сезонности и полной экономики.

## Что перевернёт предложение

- При прежнем сценарном объёме пилоту нужен чистый доход за поездку примерно ×{ratio('D_pilot','yield_factor'):.2f} (около {14000*ratio('D_pilot','yield_factor')/1000:.1f} тыс. ₽), либо OD ×{ratio('D_pilot','demand'):.2f}, либо затраты ×{ratio('D_pilot','cost'):.2f} — **до fixed**. Рост цены здесь без эластичности: это порог, не прогноз продаж.
- При росте всех OD ×3 улучшенная прямая программа даёт {demand3:+.2f} млн ₽/неделю до fixed; при удвоении чистой выручки за поездку хаб UFA даёт +0,84 млн. Фиксированные расходы и альтернативную стоимость надо вычесть дополнительно; даже положительный отдельный сценарий не доказывает запуск.
- +50% к конечным рынкам GOJ меняет лидера восьмилучевых хабов UFA→GOJ; уменьшение рынков UFA вдвое выводит вперёд CEK. Во всех этих городских стрессах текущий запуск ещё не оправдан. Поэтому Уфа — **условный кандидат**, а не окончательный выбор.
- Подписанный блоковый спрос, реальные скидки/поддержка, меньший переток или освобождение пригодного борта способны изменить решение. Замена старых рейсов — отдельный расчёт с потерянными продажами и устранимыми затратами; сейчас её выгода не доказана.

[Сравнительная таблица](comparison_short.csv) · [полные деньги/пассажиры](model/comparison.csv) · [маршруты и частоты](model/routes.csv) · [пороги](model/breakeven.csv) · [чувствительность](model/switch_summary.csv) · [проверки](model/validation.json) · [расчётные ограничения](calculation_limits.md).

Воспроизведение без интернета: `python3 scripts/build_conditional_decision.py`. Полная доля RW до 2028 не установлена без совместимых исходной базы и знаменателя. Все общие параметры — [assumptions.json](assumptions.json), унаследованные источники включены в [манифест](model/input_manifest.json). Старые результаты сохранены. Стратегия кейса — **прямые поэтапно, хаб UFA как условный следующий этап**, а не обещание запустить сегодняшнюю убыточную восьмимаршрутную программу.
'''
 (P/'recommendation.md').write_text(note)
 brief_table=[table[0].replace('¹','').replace('²',''),table[1]]+[line for line in table[2:] if any(label in line for label in [names[k] for k in ['NO_LAUNCH','D_pilot','D_case8','S_UFA_8_1','H_UFA_8','H_GOJ_8']])]
 brief=f'''# Предложение к решению команды

**Сейчас новый хаб не открывать. Выбрать поэтапную прямую программу; первый пилот — Екатеринбург–Минеральные Воды раз в неделю, только после подтверждения оплаты и полной экономики. Уфу оставить условным первым кандидатом на будущий восьмилучевой хаб. Решение команды не принято.**

{chr(10).join(brief_table)}

Расчётная неделя 7–13 декабря 2026 — единый тест, не обещанная дата запуска. Вклад до фиксированного парка, базы и альтернативной стоимости. Общий потолок 4 рабочих по100 мест +1 резерв, доступность неизвестна. Загрузка — результат сценария, не доказательство спроса. Б0 сохранена только как исходный ориентир; новая прямая сеть собрана независимо и сокращена до восьми пар.

**Факты:** [на UFA–MRV опубликованы4рейса Azimuth/сторону](research/ufa_mrv_calendar.csv). Для SVX–MRV найдены предложение Ural и историческая программа RW2021; свободная новая ниша не доказана. Публичные20SSJ по100мест не означают свободный борт. Оплаченного OD, чистого дохода за поездку и договорных расходов в источниках нет.

**Пять неизвестных, которые меняют выбор:** конечный OD/привлечение; чистый доход за поездку; переменные затраты и стоимость базы/поддержка; переток с RW; свободный парк и условия ТО/слотов/MCT. [Обоснование и границы](decision_parameters.csv). Где нет фактов, проверены широкие арифметические стрессы: OD×0,5–3, чистая выручка×0,75–2, затраты×0,7–1,3, неизвестный переток до20%base/40%cautious; для опубликованной RW — отдельно60%/80%, стресс до100%. Это не эмпирические диапазоны или вероятности. Поиск остановлен; нужны продажи и коммерческие предложения.

**Предлагаемые этапы:**

1. До H1 2027 проверить оплачиваемый блок/OD, конкурентов, собственные продажи RW, реально свободный SSJ и резерв. Без подтверждений — не добавлять программу.
2. Для пилота при условных14тыс. ₽ чистого дохода/поездку, перетоке≤5% и расходах≤{fc/1e6:.3f}млн ₽/плечо нужны минимум{math.ceil(threshold)}платящих/сторону; с10% запасом к переменным расходам —{paid}или равная гарантия оплаты. Запас оставляет лишь≈{left/1e6:.2f}млн ₽/неделю на fixed/отвлечённый вклад. При дополнительных1млн ₽/неделю нужно124на100мест — запрет запуска. Осторожный сценарий не проходит даже без fixed.
3. Добавлять пары/частоты только с положительным приростом после перетока и всех расходов. Восьмимаршрутную программу сейчас целиком не запускать. К хабу UFA вернуться после подтверждения трансфера, реального парка/договора и положительной полной экономики; SJ100 не считать доступным раньше H2 2027 и не обещать поставку. Масштаб до2028 условен.

**Что меняет вывод:** пилоту до fixed нужны примерно+36%чистого дохода, +38%сценарного OD или−27%затрат. +50%конечных рынков GOJ меняет лидера хабов UFA→GOJ; это ещё не окупаемость. Даже положительный переменный вклад при благоприятном сценарии нужно заново уменьшить на базу/парк/альтернативную стоимость. Замена старых рейсов требует отдельной базовой линии.

[Полная рекомендация и сети](recommendation.md) · [таблица](comparison_short.csv) · [проверки](model/validation.json) · [источники](research/decision_evidence.csv). Пересчёт: `python3 scripts/build_conditional_decision.py`.
'''
 # Keep typography readable around figures in the short note.
 import re
 brief=re.sub(r'(?<=[А-Яа-яЁё%])(?=\d)|(?<=\d)(?=[А-Яа-яЁё])',' ',brief)
 brief=brief.replace('20SSJ','20 SSJ').replace('RW2021','RW 2021').replace('20%base/40%cautious','20% в базе / 40% в осторожном').replace('на fixed/отвлечённый вклад','на постоянные расходы / отвлечённый вклад').replace('до fixed','до постоянных расходов')
 (P/'brief.md').write_text(brief)
 data={sc:{n:round(float(idx[n,sc]['contribution_before_base_fleet_opportunity'])/1e6,3)for n in names if n!='B0_reference'}for sc in ['base','cautious']}
 html='''<!doctype html><html lang="ru"><meta charset="utf-8"><style>body{margin:0;font-family:var(--font-sans);color:var(--foreground)}p{margin:8px 0 12px}small{color:var(--muted-foreground)}select{font:inherit;background:var(--secondary);color:var(--foreground);border:1px solid var(--border);border-radius:var(--radius);padding:6px;max-width:100%;margin-bottom:10px}.row{display:grid;grid-template-columns:minmax(120px,210px) minmax(60px,1fr) 55px;gap:7px;align-items:center;margin:12px 0;font-size:13px}.track{position:relative;height:24px;border-right:1px solid var(--foreground);background:repeating-linear-gradient(to left,transparent,transparent calc(25% - 1px),var(--border) 25%)}.bar{position:absolute;right:0;height:24px;background:var(--chart-1);border-radius:3px 0 0 3px}.direct{background:var(--chart-2)}.radial{background:var(--chart-3)}.v{text-align:right;font-variant-numeric:tabular-nums}.axis{display:flex;justify-content:space-between;color:var(--muted-foreground);font-size:11px;margin:0 62px 12px 217px}@media(max-width:480px){.row{grid-template-columns:125px minmax(50px,1fr) 46px;gap:4px}.axis{margin-left:129px;margin-right:50px}}</style><p><strong>Улучшенная прямая сеть и сокращённые хабы</strong><br><small>Вклад до фиксированного парка, новой базы и альтернативной стоимости. Млн ₽ / сценарную неделю.</small></p><select id="sc" aria-label="Сценарий"><option value="base">Базовый</option><option value="cautious">Осторожный</option></select><div id="plot"></div><div class="axis"><span>−40</span><span>−30</span><span>−20</span><span>−10</span><span>0</span></div><p><small>Прямая D8: 8 пар по 1 обороту/неделю. Хабы: 8 лучей по 2. Радиальная UFA: 8 прямых по 1, без пересадок. Общий потолок 4 рабочих ×100 мест +1 резерв; фактический свободный парк неизвестен. OD и тарифы — сценарии.</small></p><script>const data=DATA,labels={D_pilot:'Пилот SVX–MRV · 1/нед.',D_case8:'Прямая D8 · 1/нед.',S_UFA_8_1:'База UFA без пересадок',H_UFA_8:'Хаб UFA · 2/нед.',H_GOJ_8:'Хаб GOJ · 2/нед.',H_CEK_8:'Хаб CEK · 2/нед.',H_TJM_8:'Хаб TJM · 2/нед.',NO_LAUNCH:'Без нового запуска'};function draw(){let d=data[document.getElementById('sc').value];document.getElementById('plot').innerHTML=Object.keys(labels).map(n=>`<div class="row"><span>${labels[n]}</span><div class="track"><div class="bar ${n.startsWith('D')?'direct':n.startsWith('S')?'radial':''}" style="width:${Math.abs(d[n])/40*100}%"></div></div><span class="v">${d[n].toFixed(2).replace('.',',')}</span></div>`).join('')}document.getElementById('sc').onchange=draw;draw();</script></html>'''.replace('DATA',json.dumps(data,ensure_ascii=False))
 (P/'comparison_chart.html').write_text(html)
 print('Decision note and chart updated')
if __name__=='__main__':main()
