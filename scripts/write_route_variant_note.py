#!/usr/bin/env python3
"""Write the current conditional route-review comparison from reproducible exports."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'context/17_aircraft_route_review';M=OUT/'model'
def rows(n):return list(csv.DictReader((M/n).open()))
def main():
 rr=rows('comparison.csv');idx={(r['profile'],r['network'],r['scenario']):r for r in rr};defs=json.load(open(M/'selected_networks.json'))
 profiles={'RELAXED_SAME_INPUTS_100':'Только снятие отсечки; прежние экономические входы','ROUTE_INPUTS_UPPER_100':'Плановые времена + неизвестные прокси; верхний тест100мест','RRJ95B_MASS_TEST':'B/B100: условный массовый бюджет','RRJ95LR_MASS_TEST':'LR: условный массовый бюджет','UNKNOWN_TIME_PLUS60_100':'Ещё60мин только на неизвестных плечах: стресс'}
 old=read_old=list(csv.DictReader(open(ROOT/'context/16_conditional_decision/model/comparison.csv')))
 old_d=next(r for r in old if r['network']=='D_case8'and r['scenario']=='base');old_h=next(r for r in old if r['network']=='H_UFA_8'and r['scenario']=='base')
 lines=['| Расчётный вариант | Прямая программа, база / осторожный | Хаб8 — лидер базы; его база / осторожный |','|---|---:|---:|'];short=[]
 lines.append(f"| Прежний этап16, историческая отсечка | {float(old_d['contribution_before_base_fleet_opportunity'])/1e6:.2f} / {float(next(r for r in old if r['network']=='D_case8'and r['scenario']=='cautious')['contribution_before_base_fleet_opportunity'])/1e6:.2f} | UFA: {float(old_h['contribution_before_base_fleet_opportunity'])/1e6:.2f} / {float(next(r for r in old if r['network']=='H_UFA_8'and r['scenario']=='cautious')['contribution_before_base_fleet_opportunity'])/1e6:.2f} |")
 for profile,label in profiles.items():
  d=idx[profile,'D_case','base'];dc=idx[profile,'D_case','cautious'];hh=[r for r in rr if r['profile']==profile and r['scenario']=='base'and r['network'].startswith('H_')and r['network'].endswith('_8')]
  h=max(hh,key=lambda r:float(r['contribution_before_base_fleet_opportunity']))if hh else None
  hc=idx[profile,h['network'],'cautious']if h else None
  hv=(f"{h['network'][2:5]}: {float(h['contribution_before_base_fleet_opportunity'])/1e6:.2f} / {float(hc['contribution_before_base_fleet_opportunity'])/1e6:.2f}")if h else'Волновая схема не уместилась в модель4 рабочих'
  lines.append(f"| {label} | {float(d['contribution_before_base_fleet_opportunity'])/1e6:.2f} / {float(dc['contribution_before_base_fleet_opportunity'])/1e6:.2f} | {hv} |")
  for r in [d,dc]+([h,hc]if h else[]):short.append({k:r[k]for k in ['profile','network','scenario','pairs','active_allocated','weekly_legs','weekly_block_hours','sold_journeys','transfer_journeys','incremental_revenue','incremental_operating_cost','contribution_before_base_fleet_opportunity','dispatch_status']})
 with (OUT/'comparison_short.csv').open('w',newline='')as f:w=csv.DictWriter(f,short[0].keys(),lineterminator='\n');w.writeheader();w.writerows(short)
 restored=rows('previously_excluded_review.csv');matrix=rows('route_variant_matrix.csv')
 examples=['| Пара | Плановые минуты туда / обратно | Массовый тест B, мест¹ | Массовый тест LR, мест¹ | Что известно |','|---|---|---|---|---|']
 for a,b in [('SVX','AER'),('SVX','KGD'),('SVX','IKT'),('ZIA','KJA'),('ARH','MRV'),('NJC','VOG')]:
  find=lambda x,y,v:next(r for r in matrix if r['origin']==x and r['destination']==y and r['variant']==v)
  f=find(a,b,'RRJ-95B');back=find(b,a,'RRJ-95B');lr=find(a,b,'RRJ-95LR-100');lrb=find(b,a,'RRJ-95LR-100')
  tm=lambda r:('не получено' if not r['published_block_min'] else f"{float(r['published_block_min']):.0f}" if r['published_block_min']==r['published_block_max'] else f"{float(r['published_block_min']):.0f}–{float(r['published_block_max']):.0f}")
  examples.append(f"| {a}–{b} | {tm(f)} / {tm(back)} | {f['mass_test_capacity_base_NOT_DISPATCH']} / {back['mass_test_capacity_base_NOT_DISPATCH']} | {lr['mass_test_capacity_base_NOT_DISPATCH']} / {lrb['mass_test_capacity_base_NOT_DISPATCH']} | {'плановые времена другого типа'if f['block_evidence']=='OTHER_JET_TIMETABLE_PROXY_NOT_SSJ_PERFORMANCE'else'нет подтверждённой трассы и нагрузки'} |")
 control=defs['RELAXED_SAME_INPUTS_100|D_case'];upper=defs['ROUTE_INPUTS_UPPER_100|D_case'];stress=defs['UNKNOWN_TIME_PLUS60_100|D_case']
 tjm_caut=float(idx['ROUTE_INPUTS_UPPER_100','H_TJM_8','cautious']['contribution_before_base_fleet_opportunity'])/1e6
 ufa_caut=float(idx['ROUTE_INPUTS_UPPER_100','H_UFA_8','cautious']['contribution_before_base_fleet_opportunity'])/1e6
 describe=lambda d:'; '.join('–'.join(j['route'])+f" ({j['frequency']} вылет/сторону/нед.)"for j in d['jobs'])
 note=f'''# Проверка модификаций и маршрутов — 9 ноября 2026

**Универсальный фильтр 2 300 км и поправка +20% сняты.** Вместо них — [матрица маршрут × модификация](model/route_variant_matrix.csv): опубликованные сведения, масса/топливо, недостающие данные и статус **«требует эксплуатационной проверки»**. Ни одной паре не выдан технический допуск и ни одна не объявлена невозможной только по радиусу.

**Результат:** состав условно лучших прямых сетей меняется, но безубыточного запуска не появилось. При прежних деньгах снятие отсечки улучшает базовый вклад прямой программы примерно на0,20млн ₽/неделю, зато осторожный результат хуже. Уфа остаётся условным лидером сравниваемых восьмилучевых хабов в базе; при обновлённых временах в осторожном сценарии немного выше Тюмень. Устойчивого выбора города нет. Рекомендация пока прежняя: не открывать базу и не запускать всю программу; сначала подтвердить спрос, чистую выручку и эксплуатационные условия конкретного пилота. Решение команды не принято.

## Что заменило старый фильтр

- **RRJ‑95B и RRJ‑95B‑100:** справочная MTOW45 880кг; у B100 другой вариант тяги, что не превращает его в LR.
- **RRJ‑95LR‑100:** справочная MTOW49 450кг при соответствующей модификации. Для обоих приведены MLW41 000кг и MZFW40 000кг; топливо в доступной карте —15 805л/12 327кг при плотности0,78. Это технические параметры, не располагаемая коммерческая нагрузка конкретного борта.
- Рекламные3 048/4 578км относятся к профилю98пассажиров; **не подтверждают100мест на нужной трассе зимой**. SJ100 с ПД‑8 не наследует автоматически характеристики SaM146.

Источники: [TCDS EASA, страницы10/12–15](https://www.easa.europa.eu/en/downloads/7268/en), [datasheet изготовителя](https://www.superjetinternational.com/wp-content/uploads/SSJ100_Datasheet.pdf), [данные изготовителя о B100](https://www.superjetinternational.com/uncategorized/new-ssj100-model-certified-by-easa-base-take-off-weight-with-increased-engine-thrust/), [карта Росавиации](https://favt.gov.ru/public/ododoc/%D0%93%D0%A1%D0%A1/%D0%9A%D0%94%D0%A1%D0%A2-%D0%A1%D0%A2-FATA-01020-%D0%B8%D0%B7%D0%B4.15.pdf). Доступный EASA PDF визуально помечен Suspended и используется как исторический инженерный источник, не как действующее разрешение. Полный российский PDF получить не удалось; данные изготовителя частично доступны только в индексе. Точная область проверки и SHA — [sources.json](evidence/sources.json).

Новая проверка должна установить по конкретному борту допустимую взлётную/посадочную массу, сухую эксплуатационную массу, фактическую нагрузку, топливо по разрешённой трассе с ветром/запасными/резервами, взлётные ограничения и состояние полос. **РЛЭ/WBM нужной конфигурации, актуальный OFP/NOTAM/AIRAC и фактические массы не получены.** Поэтому реальные пределы пассажиров оставлены NULL, а не равными100.

## Ранее исключённые пары

Все10 базовых пар возвращены в перебор, включая ZIA–BAX/KJA/IKT/KHV/VVO и SVX–AER/KGD/IKT/KHV/VVO. Отдельно пересмотрены ARH–MRV и NJC–VOG из Б0. [Все12 случаев и результат перебора](model/previously_excluded_review.csv). Длинные обороты получили варианты с ночёвкой; её дополнительные расходы, удалённое ТО и экипажи не подтверждены и в оптимистичном денежном тесте не начислены. Ночёвка не объявлена бесплатной.

Доступны390 датированных записей предложения и52 направленных времени. У [аэропорта Кольцово](https://ar-svx.ru/schedule/) SVX–AER занимает4:00–4:05, обратно3:35–3:40; SVX–KGD4:20, обратно3:55. Время другого типа самолёта — лишь маршрутный ориентир для экономики SSJ. Из него не вычислялась длина трассы. Каталожные2080км SVX–AER у RW не приняты за фактически пройденный путь. Историческое сообщение Azimuth ARH–MRV имеет остановку в Ярославле и не доказывает сегодняшний беспосадочный рейс.

{chr(10).join(examples)}

¹ Это **только иллюстрация массового бюджета** при условных DOW28,5т, остаточном/запасном топливе1т,100кг/человек, расходе из прежней модели и известных либо условных временах. Это не результат РЛЭ, не установленный интервал нагрузки и не допуск на указанное число пассажиров. Для B100 в этом тесте использован тот же массовый бюджет, но его характеристики разгона/тяги не признаны одинаковыми с B. Для осторожного сценария параметры и отдельные пределы есть в матрице.

## Пересчёт сетей

Млн ₽ за одну сценарную неделю7–13декабря2026, **до фиксированного парка, базы, альтернативной стоимости и неподтверждённых расходов ночёвок**. Общий потолок4рабочих ×100номинальных мест +1резерв; доступность модификаций неизвестна. OD/тариф/привлечение сохранены сценарными, спрос не выведен из кресел. Пересадка занимает два рейса, билет приносит один тариф; переток RW вычтен.

{chr(10).join(lines)}

В таблице сети выбраны по базовому сценарию, затем тот же состав проверен в осторожном. Для обновлённых времён осторожный результат Тюмени с8лучами составляет около {tjm_caut:.2f}млн ₽ против {ufa_caut:.2f}млн ₽ у Уфы; такая разница мала относительно неизвестных входов и не доказывает преимущества города. Все результаты условные. Полное сравнение, включая меньшие хабы и обе оценки прежних прямых сетей, — в [model/comparison.csv](model/comparison.csv).

Небольшая разница денежных результатов B/LR здесь в основном связана со сценарной аэропортовой платой по MTOW. Подтверждённого преимущества расхода топлива или лётной экономики модификации из неё не следует.

Верхний тест100мест намеренно допускает даже ещё не обоснованную такую ёмкость: это оптимистичная денежная проверка, **не признание выполнимости**. У неизвестных пар нет подтверждённого интервала времени: прямая/750км/ч +30мин — только оптимистичная прокси, а +60мин — отдельный стресс ошибки, не новая оценка трассы и не заменитель старых20%. Денежные изменения после обновления плановых времён и сценарного предложения нельзя приписывать сертифицированной дальности.

Сети для проверки:

- **После снятия отсечки при старых денежных входах:** {describe(control)}.
- **По обновлённым временам и оптимистичным прокси:** {describe(upper)}.
- **При +60мин только на неизвестных плечах:** {describe(stress)}.
- **Условный хаб UFA:** прежние8лучей GOJ/KUF/OMS/NJC/VOG/MRV/ARH/GSV, по2оборота/неделю. Не все возможные новые наборы лучей перебраны; результат не глобальный оптимум.

Одномаршрутный денежный лидер при оптимистичной прокси смещается к ZIA–MRV, **для которой не получено подтверждённого времени нужного рейса**; в стрессе неизвестного времени снова лидирует SVX–MRV. Такой смены недостаточно для выбора пилота. Прежний экономический порог94оплаченных пассажира не является подтверждением технической возможности перевезти их: нагрузка и положительная полная экономика должны быть проверены отдельно.

## Что нужно до запуска

От оператора нужны конкретные RA‑борта/модификации и доступный парк; актуальные AFM/WBM, массы экипажа/оборудования/груза; разрешённые трассы и NOTAM на дату, ветер и доступные запасные; расчёт топлива/резервов и взлётно‑посадочных ограничений; допустимая нагрузка по каждому направлению и стоимость ночёвок/удалённого ТО. Публичный AIS портал не удалось прочитать, точные утверждённые треки не получены. Эти пропуски не заменены универсальным процентом и не превращены в запрет маршрута.

[Короткая таблица](comparison_short.csv) · [все деньги/пассажиры](model/comparison.csv) · [проектные цепочки](model/flights.csv) · [ёмкости-сценарии по плечам](model/capacity.csv) · [входы](assumptions.json) · [проверки](model/validation.json).

Пересчёт без интернета: `python3 scripts/build_aircraft_route_review.py`. Прежние численные результаты сохранены. Исправлены центральное правило в CLAUDE.md и пометка в старой технической записке; исторический фильтр в прежних таблицах больше не служит допуском. Данные первоисточников заморожены с датой/областью проверки; это не обновляемый перед вылетом диспетчерский расчёт.
'''
 import re
 note=re.sub(r'(?<=[А-Яа-яЁё])(?=\d)|(?<=\d)(?=[А-Яа-яЁё])',' ',note)
 for token in ['MTOW','MLW','MZFW','DOW']:
  note=re.sub(r'\b'+token+r'(?=\d)',token+' ',note)
 (OUT/'README.md').write_text(note)
 data={p:{sc:{r['network']:round(float(r['contribution_before_base_fleet_opportunity'])/1e6,3)for r in rr if r['profile']==p and r['scenario']==sc}for sc in ['base','cautious']}for p in profiles}
 html='''<!doctype html><html lang="ru"><meta charset="utf-8"><style>body{margin:0;font-family:var(--font-sans);color:var(--foreground)}p{margin:8px 0 12px}small{color:var(--muted-foreground)}.controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}select{font:inherit;color:var(--foreground);background:var(--secondary);border:1px solid var(--border);border-radius:var(--radius);padding:6px;max-width:100%}.row{display:grid;grid-template-columns:minmax(100px,180px) minmax(60px,1fr) 62px;gap:7px;align-items:center;margin:12px 0;font-size:13px}.track{height:24px;position:relative;border-right:1px solid var(--foreground);background:repeating-linear-gradient(to left,transparent,transparent calc(25% - 1px),var(--border)25%)}.bar{position:absolute;right:0;height:24px;background:var(--chart-1);border-radius:3px 0 0 3px}.direct{background:var(--chart-2)}.value{text-align:right;font-variant-numeric:tabular-nums}.missing{font-size:11px;color:var(--muted-foreground)}@media(max-width:480px){.row{grid-template-columns:112px minmax(40px,1fr) 48px;gap:4px}}</style><p><strong>Сети после снятия географической отсечки</strong><br><small>Млн ₽/сценарную неделю, до базы, фиксированного парка и дополнительных расходов ночёвок.</small></p><div class="controls"><select id="p" aria-label="Технический сценарий"><option value="ROUTE_INPUTS_UPPER_100">Маршрутные времена · верхний тест100мест</option><option value="RELAXED_SAME_INPUTS_100">Снятие отсечки · прежние входы</option><option value="RRJ95B_MASS_TEST">B/B100 · условный массовый бюджет</option><option value="RRJ95LR_MASS_TEST">LR · условный массовый бюджет</option><option value="UNKNOWN_TIME_PLUS60_100">Неизвестные времена +60мин · стресс</option></select><select id="s" aria-label="Экономический сценарий"><option value="base">Базовый</option><option value="cautious">Осторожный</option></select></div><div id="plot"></div><p><small>Все маршруты требуют эксплуатационной проверки.100мест и массовые ограничения здесь — только сценарии, не подтверждённая нагрузка. Прямая программа пересобирается отдельно; сравниваемый хаб имеет8лучей. Нулевая строка — без добавочного запуска.</small></p><script>const data=DATA,labels={D_prev_case:'Прежняя прямая сеть',D_case:'Пересобранная прямая',H_UFA_8:'Хаб UFA · 8 лучей',H_GOJ_8:'Хаб GOJ · 8 лучей',H_CEK_8:'Хаб CEK · 8 лучей',H_TJM_8:'Хаб TJM · 8 лучей',NO_LAUNCH:'Без нового запуска'};function draw(){let d=data[document.getElementById('p').value][document.getElementById('s').value];document.getElementById('plot').innerHTML=Object.keys(labels).map(n=>d[n]===undefined?`<div class="row"><span>${labels[n]}</span><span class="missing">Не уместилось в проектную волну/4борта; это не технический запрет</span><span>—</span></div>`:`<div class="row"><span>${labels[n]}</span><div class="track"><div class="bar ${n.startsWith('D')?'direct':''}" style="width:${Math.min(100,Math.abs(d[n])/45*100)}%"></div></div><span class="value">${d[n].toFixed(2).replace('.',',')}</span></div>`).join('')}document.querySelectorAll('select').forEach(x=>x.onchange=draw);draw();</script></html>'''.replace('DATA',json.dumps(data,ensure_ascii=False))
 html=re.sub(r'(?<=[А-Яа-яЁё])(?=\d)|(?<=\d)(?=[А-Яа-яЁё])',' ',html)
 html=html.replace('проверки.100','проверки. 100')
 (OUT/'comparison_chart.html').write_text(html)
if __name__=='__main__':main()
