#!/usr/bin/env python3
"""Документированный исход Stage A и открытые запросы Stage B."""
from pathlib import Path
from collections import Counter
import csv, hashlib, json, math, re

R=Path(__file__).resolve().parent
def load(p):return json.loads((R/p).read_text())
def rows(p):return list(csv.DictReader((R/p).open()))
def js(p,o):(R/p).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def out(p,rr):
 with (R/p).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)

sources=load('sources_registry.json');S={s['source_id']:s for s in sources}
review=[]
for s in sources:
 text=(R/s['saved_path']).read_text() if s.get('saved_path') else ''
 review.append(dict(source_id=s['source_id'],url=s['url'],organization=s['organization'],publication_date=s['publication_date'],period=s['period'],granularity=s['granularity'],unit=s['unit'],retrieved_at=s['retrieved_at'],status='СОХРАНЁН_ТЕКСТ_ГРАНИЦЫ_ПРИМЕНЕНИЯ_НИЖЕ' if text else 'НЕ_ПОЛУЧЕН_НЕ_ДОКАЗЫВАЕТ_ОТСУТСТВИЕ',coverage=s['coverage'],saved_text_sha256=s.get('saved_text_sha256'),source_content_present=bool(text),evidence_type='архивное объявление/справка' if any(y in s['publication_date'] for y in ['2022','2023','2025']) else 'текущая справка/объявление2026; проверить период конкретной строки',year2027_2028_admission=False,open_seat_admission=False,quantity_limits='Ни from fare, ни общий пассажиропоток, ни тип семейства не заменяет OD/борт/кресла/тариф на дату.'))
js('sources_review.json',review)

airports=[
 dict(airport='ZIA',name='Жуковский / Раменское',base_status='исторически базовый RW: первичный источник02.02.2023; объявленные операции зима26/27 и событие21.09.2026',operating_status='RW: регулярный BUS рейс21.09.2026 подтверждён событием; зима26/27 TBS ежедневно, BUS вт/пт/вс опубликованы, mixed SSJ100/Ту204/214; ZIA–TLV объявлен наТу214',marketing_status='собственные продажи RW из физического ZIA по перечисленным источникам; иной WZ код всё равно требует legal operator/contract binding',SSJ_support='история собственного ангара/ФАП285/A-check; две позиции, C-check был планом; current capacity/certificates/contracts UNKNOWN',free_project_SSJ='UNKNOWN',future_SJ100_PD8_support='UNKNOWN; старый SSJ certificate не переносится',source_ids='MOW-S01;MOW-S02;MOW-S03;MOW-S06;MOW-S25',as_of='2026-11-12',coverage='история инфраструктуры + определённые опубликованные/событийные продукты; не весьKEEP/park',assumption_ids='MOW-A01;MOW-A02;MOW-A07;MOW-A12;MOW-A17;MOW-A18'),
 dict(airport='DME',name='Домодедово',base_status='исторически назван базовым вRW02.02.2023; представительство24/7 на текущей странице',operating_status='собственные RW воздушные суда наDME–CXR подтверждены аэропортом летом2026; широкофюзеляжный charter описанRW2025; DME–KGD объявление2025 не current SSJ tail',marketing_status='DME–KGD есть в справочной карточке; текущая продажа/места/оператор/тип/date UNKNOWN',SSJ_support='контракт ТО и свободная мощность/борт на дату UNKNOWN',free_project_SSJ='UNKNOWN',future_SJ100_PD8_support='UNKNOWN',source_ids='MOW-S01;MOW-S04;MOW-S05;MOW-S06;MOW-S13;MOW-S16',as_of='2026-11-12',coverage='не смешивать widebody/SSJ/партнёрские charter commitments; DMEcontrol отдельно отZIA',assumption_ids='MOW-A01;MOW-A02;MOW-A07;MOW-A12;MOW-A17;MOW-A18'),
 dict(airport='VKO',name='Внуково',base_status='P03 сохраняет AOC2025 VKO/DME; это не свободная база2027/28',operating_status='для данной задачи текущие собственные SSJ missions/tails не подтверждены; WZ label не достаточен',marketing_status='MOW aggregated offers не разрешены доVKO; отдельные WZ offers требуютoperator/contract proof',SSJ_support='UNKNOWN',free_project_SSJ='UNKNOWN',future_SJ100_PD8_support='UNKNOWN',source_ids='P03_airport_constraints.csv;MOW-S09',as_of='2026-11-12',coverage='только указанная реестровая provenance; отсутствие полного наблюдения не факт отсутствия RW',assumption_ids='MOW-A01;MOW-A17;MOW-A18'),
 dict(airport='SVO',name='Шереметьево',base_status='UNKNOWN; в прочитанных inputs доказательство свободной RW базы отсутствует',operating_status='SU/FV и прочие source offers конкурентов вP02; они не паркRW',marketing_status='MOW aggregated demand/offer не назначается автоматически SVO или RW',SSJ_support='UNKNOWN дляRW',free_project_SSJ='UNKNOWN',future_SJ100_PD8_support='UNKNOWN',source_ids='P03_airport_constraints.csv;P02_competitor_products.csv',as_of='2026-11-12',coverage='не утверждается, что RW отсутствует; не создаётся четвёртая свободная база',assumption_ids='MOW-A01;MOW-A17;MOW-A18')]
out('airport_status.csv',airports)

keep=[
 dict(keep_item_id='KEEP-ZIA-BUS',physical_airports='ZIA;BUS',period='winter2026/27 starting26Oct2026; future2027/28 UNKNOWN',frequency='Tue/Fri/Sun published',type='SSJ100/Tu204/214 mixed announcement; tail-date UNKNOWN',commercial_role='RW own regular product; preserve affected sales',source_ids='MOW-S02;MOW-S25',source_url=S['MOW-S02']['url'],future_baseline_status='источник для будущегоKEEP, не сам futureKEEP; нужны продления, парк и договоры'),
 dict(keep_item_id='KEEP-ZIA-TBS',physical_airports='ZIA;TBS',period='winter2026/27; future2027/28 UNKNOWN',frequency='daily published',type='SSJ100/Tu204/214 mixed announcement; exact type/date UNKNOWN',commercial_role='RW own regular product; preserve affected sales',source_ids='MOW-S02',source_url=S['MOW-S02']['url'],future_baseline_status='не использовать пятничное08:00 окно как свободное при опубликованномBUS08:10; нужен конкретный tail KEEP'),
 dict(keep_item_id='KEEP-ZIA-TLV',physical_airports='ZIA;TLV',period='announcement from17Apr2026; future2027/28 UNKNOWN',frequency='daily published',type='Tu214; SSJ pool separate',commercial_role='own international RW product',source_ids='MOW-S03',source_url=S['MOW-S03']['url'],future_baseline_status='не снимать Tu рейсы ради SSJ без отдельного изменения целого бизнеса'),
 dict(keep_item_id='KEEP-DME-CXR',physical_airports='DME;CXR',period='summer2026 airport confirmation; charter2025 company announcement',frequency='UNKNOWN',type='widebody charter; exact tail/date UNKNOWN',commercial_role='RW + tour operator charter obligations; commission/block terms UNKNOWN',source_ids='MOW-S05;MOW-S16',source_url=S['MOW-S16']['url'],future_baseline_status='не SSJ inventory; revenue/commitment KEEP сохраняются'),
 dict(keep_item_id='KEEP-DME-KGD-HISTORY',physical_airports='DME;KGD',period='from25Jul2025; from8Sep2025 Fri/Sat/Sun; current continuation UNKNOWN',frequency='7 then3/week published in2025',type='UNKNOWN exact flight type; not inferred from family fleet paragraph',commercial_role='historical RW own direct sales; origin of optional DME control',source_ids='MOW-S04;MOW-S13',source_url=S['MOW-S04']['url'],future_baseline_status='2h50 announcement vs2h05 reference card conflict; not accepted flight clock or free SSJ'),
 dict(keep_item_id='KEEP-VOG-MCX-HISTORY',physical_airports='VOG;MCX',period='RW autumnsale2025 for23Sep2025–28Mar2026; Nov2025 sale from18Nov2025',frequency='UNKNOWN from primary sale pages; weeklyWed is secondary announced2025 plan',type='UNKNOWN current tail/date',commercial_role='historical RW same-market own sales; cannot count entire programme revenue as new',source_ids='MOW-S10;MOW-S11;MOW-S24',source_url=S['MOW-S10']['url'],future_baseline_status='нужны текущие/будущие flight_ids, block/marketing contracts, sold seats и no-project product'),
 dict(keep_item_id='KEEP-MARKETING-PARTNER',physical_airports='конкретные пары/операторы по договору; не разрешать MOW автоматически',period='contract dates UNKNOWN; example B2/RW from1Sep2026',frequency='UNKNOWN as full Moscow affected scope',type='партнёрский aircraft отдельно отRW; WZ marketing не physical tail',commercial_role='marketing net revenue/commission/seat blocks и commitments сохраняются',source_ids='MOW-S08;MOW-S09',source_url=S['MOW-S08']['url'],future_baseline_status='примерB2 внеМосквы объясняет правило; не доказательство московского flight inventory')]
out('KEEP_evidence.csv',keep)

ground=[
 dict(market='VOG–MCX / city journey',source_ids='MOW-S18;MOW-S22;MOW-S23;MOW-S26;MOW-S27',source_url='https://www.avtovokzaly.ru/avtobus/volgograd-mahachkala',organization='ГБУ ВО Вокзал-Авто / Автовокзалы.ру(агент)',as_of='2026-11-12',departure_date='dated query13Nov2026 returnedHTTP400; actual row dates in source if present',return_date='dated query16Nov2026 returnedHTTP400',evidence='Первичный вокзал показывает транзитный маршрут10154 Махачкала–Москва(Саларьево)05:30 по нечётным; это не полная пара VOG–MCX. Агентский общий источник показывает автобусный рынок; актуальная RT корзина не подтверждена.',full_journey_minutes='UNKNOWN',comparable_RT_price_rub='UNKNOWN',booking_lead_days='UNKNOWN',coverage='PARTIAL_GROUND_CONTEXT; direct/return duration/fare/fees/станции/багаж/места unadmitted',decision='Не считать короткое расстояние доказательством доминирования авто/поезда; запросMOW-D04',assumption_ids='MOW-A14;MOW-A15;MOW-A16'),
 dict(market='KGD–GOJ/KUF / city journey',source_ids='MOW-S19',source_url=S['MOW-S19']['url'],organization=S['MOW-S19']['organization'],as_of='2026-11-12',departure_date='UNKNOWN',return_date='UNKNOWN',evidence='Официальный туринфоцентр описывает железнодорожные направления и транзитные документы; это ограничение доступности для отдельных групп, а не отсутствие ground. Точные нормы/поезда/цены2027/28 отдельно.',full_journey_minutes='UNKNOWN',comparable_RT_price_rub='UNKNOWN',booking_lead_days='UNKNOWN',coverage='PARTIAL_ACCESS_CONTEXT; route-specific door-to-door/RT fare not observed',decision='Сравнить прямойN4, черезDME/ZIA/SVO/VKO/LED, rail иавто для одного срока7–14ночей; запросMOW-D05',assumption_ids='MOW-A01;MOW-A14;MOW-A15;MOW-A16'),
 dict(market='ARH–MRV / city journey',source_ids='MOW-S12;P02',source_url=S['MOW-S12']['url'],organization='Азимут / сохранённыйP02',as_of='2026-11-12',departure_date='исторический старт30Mar2022; текущие даты UNKNOWN',return_date='UNKNOWN',evidence='Исторический авиационный конкурентMRV–IAR–ARH с посадкой; текущие direct/via/ground RT не получены. Не применять generic train/auto time к2300km по прямой.',full_journey_minutes='UNKNOWN',comparable_RT_price_rub='UNKNOWN',booking_lead_days='UNKNOWN',coverage='UNCOVERED_CURRENT_GROUND; не0рынок',decision='P05 сравнивает северную отпускную поездку7–14ночей и собственный переток черезSVX/MOW; запросMOW-D06',assumption_ids='MOW-A14;MOW-A15;MOW-A16'),
 dict(market='московский доступ кZIA vs другие аэропорты',source_ids='MOW-S17;P02_ground',source_url=S['MOW-S17']['url'],organization='Red Wings / P02',as_of='2026-11-12',departure_date='UNKNOWN project dates',return_date='UNKNOWN',evidence='ZIA: автобус441 отКотельников и rail/МЦД3+шаттлОтдых. Способ доступа доказан, конкретный адрес/час/семья/багаж/затраты UNKNOWN. MOW не один терминал.',full_journey_minutes='UNKNOWN',comparable_RT_price_rub='UNKNOWN',booking_lead_days='UNKNOWN',coverage='PARTIAL_ACCESS_CONTEXT; published averages не цена и время семьи до двери',decision='Потребуется P05 split catchment/access, а не автоматический перенос спросаMOW вZIA',assumption_ids='MOW-A01;MOW-A14;MOW-A16')]
out('ground_evidence.csv',ground)

# Направленные реальные строки общего агентского source export. Никакого booking POST.
gp=[]
for sid,a,z,carrier,departure,arrival,minutes,flo,fhi,start,end in [
 ('MOW-S26','Volgograd_Central_bus','Makhachkala_North_bus','ООО Дагтуртранс','2026-11-14 16:30','2026-11-15 10:52',1102,3708,3708,140,165),
 ('MOW-S26','Volgograd_Central_bus','Makhachkala_North_bus','ООО Новый автобусный парк','2026-11-13 16:30','2026-11-14 10:52',1102,3708,3708,167,188),
 ('MOW-S26','Volgograd_Central_bus','Makhachkala_North_bus','ООО Новый автобусный парк','2026-11-15 16:30','2026-11-16 10:52',1102,3708,3708,167,188),
 ('MOW-S27','Makhachkala_North_bus','Volgograd_Central_bus','ООО Дагтуртранс','2026-11-14 16:00','2026-11-15 07:30',930,3905,3959,161,184),
 ('MOW-S27','Makhachkala_North_bus','Volgograd_Central_bus','ООО Новый автобусный парк','2026-11-13 16:00','2026-11-14 07:30',930,3959,3959,185,207),
 ('MOW-S27','Makhachkala_North_bus','Volgograd_Central_bus','ООО Новый автобусный парк','2026-11-15 16:00','2026-11-16 07:30',930,3959,3959,185,207),
 ('MOW-S27','Makhachkala_North_bus','Volgograd_Central_bus','ООО Победа (автобусный перевозчик, не DP)','2026-11-14 12:15','2026-11-15 05:15',1020,4066,4066,107,138)]:
 text=(R/S[sid]['saved_path']).read_text().splitlines();extract='\n'.join(text[start-1:end])
 gp.append(dict(ground_product_id='MOW-GP'+str(len(gp)+1).zfill(2),source_id=sid,source_url=S[sid]['url'],organization=S[sid]['organization'],source_saved_text_sha256=S[sid]['saved_text_sha256'],source_line_start=start,source_line_end=end,source_extract_sha256=hashlib.sha256(extract.encode()).hexdigest(),origin_station=a,destination_station=z,origin_destination_unit='конкретные автобусные станции, не аэропорты',carrier_label=carrier,departure_local=departure,arrival_local=arrival,elapsed_min=minutes,fare_display_lower_rub=flo,fare_display_upper_rub=fhi,fare_range_meaning='диапазон отображения агентом, не доверительный интервал/прогноз',fare_unit='RUB/person/one-way; net yield UNKNOWN',as_of=S[sid]['retrieved_at'],booking_lead_days=(__import__('datetime').date.fromisoformat(departure[:10])-__import__('datetime').date(2026,11,12)).days,baggage='UNKNOWN',fees='UNKNOWN',comparable_RT_basket=False,open_seats='UNKNOWN',status='SOURCE_EXPORT_NOT_INVENTORY; год2026 подтверждён контекстом страницы, не2027/28',coverage='следующие даты страницы; matched RT3–4ночи на той же корзине не получен',assumption_ids='MOW-A14;MOW-A15;MOW-A16'))
out('ground_products.csv',gp)
issues=[
 dict(issue_id='MOW-I01',source_ids='MOW-S04;MOW-S13',issue='DME–KGD2ч50 в объявлении2025 против2ч05 в справочной карточке.',handling='Для выбранного reference используется170min с отдельным assumption; карточка не flight clock; actual route/block UNKNOWN.',affected='C25/DME/ZIA KGD templates',resolution='P03 approved dated blocks, обе стороны/варианты.'),
 dict(issue_id='MOW-I02',source_ids='MOW-S12',issue='Архивный return: ARH17:15→IAR18:50, затем IAR15:20→MRV23:10 без day-offset. Хронология одной даты противоречива.',handling='Сохранён только факт опубликованного ordered MRV–IAR–ARH; обратное расписание не допущено. Не превращать в current nonstop.',affected='C08 historical comparator',resolution='Исходный dated flight plan/расписание с day-offset; current source отдельно.'),
 dict(issue_id='MOW-I03',source_ids='P02_competitor_products.csv',issue='Две сохранённые строки N4 могут быть повторной фиксацией одного station product, не двумя physical aircraft.',handling='Продукты/ID/хеши сохранены; не суммируются в общую вместимость. WZ/operator и B737 nominal не open seats.',affected='вся market panel',resolution='P02 physical flight/operator ID + P05 contract/inventory binding.'),
 dict(issue_id='MOW-I04',source_ids='MOW-S22;MOW-S23;MOW-S26;MOW-S27',issue='Dated queries HTTP400; общий агентский текст содержит отдельные13–15Nov2026 строки.',handling='7 направленных dated source rows выделены с line hashes; полной одинаковой RT корзины/багажа/fees нет. Цена автобуса не net air yield.',affected='C19 ground choice',resolution='P05 matched departure/return3–4ночи; operator/fee/baggage/party/lead.'),
]
out('source_issues.csv',issues)

js('tool_receipts.json',dict(no_browser_used=True,no_paid_services=True,no_external_messages_except_authorized_coordinator=True,no_git_mutations=True,no_shared_files_written=True,text_fallbacks=[
 dict(tool='web.open',url='https://ar-goj.ru/schedule/?type=arr',error='URL https://ar-goj.ru/schedule/?type=arr is not accessible via this tool.',fallback='публичный HTTP GET MOW-S21; P02 exact source rows остаются исходным сравнением',why='Текстовое чтение конкретного известногоURL; браузер не нужен.'),
 dict(tool='web.open',url='https://vokzal-avto.ru/tshmarshrut/',error='Failed to fetch https://vokzal-avto.ru/tshmarshrut/: (403) Forbidden',fallback='публичный HTTP GET MOW-S18 успешно сохранил текст; прочитан как ограниченный source export',why='Различие ответа сайта текстовым клиентам; не доказательство доступного билета.'),
 dict(tool='web.open',url='https://favt.gov.ru/dejatelnost-vozdushnye-perevozki-subsidirovanie-regiony/',error='Failed to fetch https://favt.gov.ru/dejatelnost-vozdushnye-perevozki-subsidirovanie-regiony/: (400) Timeout fetching',fallback='не использовать новый live claim; P04 exact thresholds/rules и source rows P02 сохраняются',why='Не требуется менять браузер/сервисы ради нормативной страницы.')],child_policy='Дети не запускались: прямое указание текущего задания работать самостоятельно без детей.',runtime_recovery='Не запускались процессы восстановления, не менялись сессии/профили/вкладки. HTTP ошибки сохранены в sources_registry, status не absence.'))

programmes=load('programme_candidates.json')['programmes'];F=load('dated_templates/flights.json')
example_fl={f['template_flight_id']:f for f in F}
sensitivity=[]
for p in programmes:
 for k in [1.1,1.2]:
  for turn in [30,45,60]:
   for kgd_extra in [0,30,60]:
    day=[];elapsed=[];missing=False
    for path in p['ordered_paths_iso_weekday'].values():
     minutes=[]
     for a,z in zip(path,path[1:]):
      f=next(f for f in F if f['programme_id']==p['programme_id'] and f['origin_airport']==a and f['destination_airport']==z)
      if f['block_reference_min'] is None:missing=True;break
      minutes.append(f['block_reference_min']+kgd_extra if 'KGD' in [a,z] else math.ceil((30+60*k*f['great_circle_km']/750)/5)*5)
     if not missing:day.append(sum(minutes)/60);elapsed.append((sum(minutes)+turn*(len(path)-2))/60)
    mx=max(day) if day and not missing else None
    sensitivity.append(dict(programme_id=p['programme_id'],route_factor_test=k,turn_test_min=turn,KGD_extra_per_leg_test_min=kgd_extra,max_day_block_h=round(mx,4) if mx is not None else 'UNKNOWN',max_mission_elapsed_h=round(max(elapsed),4) if elapsed and not missing else 'UNKNOWN',u8_pass=mx<=8 if mx is not None else 'UNKNOWN',u10_pass=mx<=10 if mx is not None else 'UNKNOWN',economic_rejection=False,status='диагностические точки; не confidence range, не фактический dispatch/crew',assumption_ids='MOW-A04;MOW-A06;MOW-A08;MOW-A09'))
out('sensitivity_checks.csv',sensitivity)

selected=[p for p in programmes if p['legacy_id'] in ['C08','C19','C25-GOJ','C25-KUF']]
table='\n'.join('| '+p['programme_id']+' | '+str(round(p['weekly_reference_block_h'],2) if p['weekly_reference_block_h'] is not None else 'UNKNOWN')+' | '+str(round(p['max_daily_reference_block_h'],2) if p['max_daily_reference_block_h'] is not None else 'UNKNOWN')+' | '+('выходит за10h' if p['max_daily_reference_block_h'] is not None and p['max_daily_reference_block_h']>10 else 'внутри10h, остальные допуски UNKNOWN')+' |' for p in selected)
legacy='\n'.join('- '+r['recipe_id']+': '+r['legacy_id']+'; исходные строки/hash в `recipes.json`.' for r in load('recipes.json') if r['legacy_id'].startswith('Прямые'))
text=f'''# Московские прямые и цепочечные программы Red Wings

Пакет P08-MOW-A, research_v1. Срез источников — 12 ноября 2026 года. Исследовательская часть Stage A закончена: 19 рецептов, 57 альтернативных программ, их физические аэропорты, ordered legs, частоты, полный условный оборот, календарные примеры и происхождение входов. Финальная экономика и операционный допуск Stage B **не выполнены**: нужны входы P03/P04/P05 и совместное сравнение P06/P09. Все 57 программ остаются условными; победитель не назначен.

## Физические аэропорты и KEEP

Для основных шаблонов выбран **ZIA** как конкретный исторический узел SSJ100 RW с первично подтверждённой базой A-check. Источник 2023 года не устанавливает свободную мощность или сертификат будущего SJ100/ПД-8. В текущем опубликованном зимнем расписании RW из ZIA есть Грузия, причём SSJ100 и Ту-204/214 названы вместе. Поэтому даже близость пятничного проектного вылета08:00 к опубликованному BUS08:10 требует проверки конкретного борта, а не предположения о свободном времени. Событие21.09.2026 подтверждает регулярный рейс RW ZIA–BUS, без указания физического борта. [RW: зима в Грузию]({S['MOW-S02']['url']}), [ангар ZIA]({S['MOW-S01']['url']}), [событие21.09.2026]({S['MOW-S25']['url']}).

DME — отдельный исторический базовый аэропорт с текущим представительством и подтверждённой работой RW на дальнемагистральном чартерном направлении CXR летом2026. Это не ресурс SSJ. Объявление DME–KGD от26.06.2025 сохранено как исторический источник: 25 июля — ежедневно, с8 сентября — пятница/суббота/воскресенье; конкретный тип/борт на дату не назван. Программа DME-CONTROL показывает чувствительность выбора аэропорта для C25, не наличие второй свободной группы самолётов. [DME: лето2026]({S['MOW-S16']['url']}), [RW: DME–KGD2025]({S['MOW-S04']['url']}).

VKO/SVO не получают бесплатных ресурсов. P03 сохраняет реестровую историю VKO/DME2025; текущий собственный SSJ для проекта из неё не следует. Доказательство свободной RW базы SVO не найдено в изученных входах; это не утверждение отсутствия RW. Поля `airport_status.csv` разделяют базовый, операционный, маркетинговый и технический статус.

`KEEP_evidence.csv` сохраняет опубликованные и исторические продажи ZIA–BUS/TBS/TLV, DME–CXR/KGD, VOG–MCX и правило учёта партнёра. WZ-номер сам по себе не доказывает собственный борт. Официальное определение код-шеринга и пример RW/Belavia подтверждают необходимость разделять фактического и маркетингового перевозчика; пример B2 не приписан московскому inventory. Доход маркетинговых продаж и обязательства по чартерам остаются в будущем KEEP. [Правила RW]({S['MOW-S09']['url']}), [RW/Belavia]({S['MOW-S08']['url']}).

## Равный ресурс и три формы расписания

Внутри каждого рецепта T/C/O имеют одну физическую базу, тот же условный рабочий борт и тот же выделенный резервный борт того же варианта. Это 14 календарных tail-days за неделю в выбранном эксперименте, а не установленный свободный парк RW. Все реальные IDs, готовность, экипажи, ТО, reserve commitments, слоты и сохранённый KEEP — UNKNOWN. Использование общего резерва возможно только после отдельного договора и проверки одновременных требований. Сравнение DME с ZIA требует полного пересчёта инфраструктуры и доступа пассажиров.

Для базы B и конечной пары X–Y формы заданы так:

- **T**: пятница B–X–Y–B, понедельник B–Y–X–B. Каждая из трёх пар имеет один рейс каждого направления за неделю.
- **C**: понедельник и пятница B–X–Y–X–B. Две пары, по два рейса каждого направления. Отдельного прямого B–Y нет; возможный сквозной продукт использует два физических кресла и один тариф.
- **O**: обычные возвратные рейсы B–X–B и B–Y–B. В пятницу X первым, в понедельник Y первым. Каждая базовая пара получает по два рейса каждого направления; X–Y обслуживается через B, если стыковка реально продаётся и соблюдён MCT.

Одинаковый парк не означает одинаковый налёт или качество поездки. Остаток времени у T/C/O сохраняется для KEEP/альтернативной работы; его экономическая ценность неизвестна. Программы являются взаимоисключающими альтернативами, их ресурс и деньги не складываются.

Без KGD используется диагностический авторский аналог `ceil5(30 + 60×1.2×great_circle_km/750)` минут. Параметры1.1/1.2, фиксированные0.5h и750km/h имеют происхождение в dceadc9. Их применимость к конкретной трассе не доказана. Для KGD сохранены отдельные ориентиры: DME–KGD170min из объявления2025; KGD–GOJ190min и KUF–KGD225min из местных часов P02 с учётом разницы времени. Перенос DME на ZIA и на обратное направление — явное допущение, не наблюдение. AER–KGD остаётся UNKNOWN. Для будущего SJ100/ПД-8 ни этот расход, ни кресла, ни блоки не приняты как факты.

В `dated_templates/flights.json` есть10032 предлагаемых плеча, в `rotations.csv` —2736 полных или явно неполных оборотов. Это восемь сезонных опорных окон двух лет и несколько повторений для проверки возвратов; они не считаются опубликованными рейсами или физическими креслами. `monthly_calendar.csv` отдельно перечисляет точные понедельники/пятницы всех24месяцев2027–2028, календарные количества year-round и сезонного предложения. Никакая неделя не умножается на52 для пассажиров/денег. За пределами проектного сезона добавления нет, но рынок и KEEP продолжаются.

## C19: Волгоград–Махачкала

Историческая продажа MCX–VOG подтверждается двумя собственными страницами акций RW2025. Поэтому спрос и доход этого рынка не могут целиком считаться новым результатом московского проекта. Текущая частота, operator/tail, block/marketing terms и будущий KEEP по паре не установлены. Вторичное сообщение о старте18.06.2025 со средами сохранено только как исторический план, не как доказательство актуального исполнения. [Осенняя акция RW]({S['MOW-S10']['url']}), [ноябрьская акция RW]({S['MOW-S11']['url']}).

На датах14–17июля2028 форма T даёт VOG→MCX в пятницу с возвратом в понедельник —3ночи. Для жителей MCX обратный рынок имеет понедельник→пятницу —4ночи, но **пятницы→понедельника нет**. Форма C `ZIA–VOG–MCX–VOG–ZIA` даёт пятницу→понедельник жителям обоих городов и сохраняет замкнутый оборот. O имеет ту же асимметрию дней, что T, и условное перелётное время через ZIA345min против100min прямого плеча в выбранном аналоге. Все эти минуты — сценарные, не расписание перевозчика или door-to-door.

Разница T/C/O — полезный предмет P05: сколько пассажиров оплачивает именно короткий уикенд, VFR или длинную поездку, с каким RT net yield. Полезный календарь не доказывает спрос. Датированные RT запросы автобусному агенту получили HTTP400, но общий текст удалось получить: `ground_products.csv` содержит7 направленных строк13–15ноября2026 с точными станциями/перевозчиком/часами и line hashes. Например, опубликовано Волгоград Центральный→Махачкала Северный13ноября16:30–14ноября10:52,18ч22м,3708руб.; обратно15ноября16:00–16ноября07:30,15ч30м,3959руб., ООО «Новый автобусный парк». Такая пара даёт одну ночь в Махачкале и не заменяет котировку на3–4ночи. Багаж/сборы/остатки неизвестны; это не сравнимый RT net fare. Первичная страница автовокзала содержит только транзитный маршрут Махачкала–Москва. Нельзя объявлять авто/поезд победителем по расстоянию или считать ground отсутствующим. [Агент: VOG→MCX]({S['MOW-S26']['url']}), [обратно]({S['MOW-S27']['url']}).

## C08: Архангельск–Минеральные Воды

Исходная ZIA–ARH–MRV–ZIA в архиве — предложенная география. Отдельный первичный источник Азимута2022 описывает **MRV–IAR–ARH**, с посадкой в Ярославле. Номер рейса до ARH не превращён в nonstop, а2022 не продлён в2026/2028. Текущие direct/connecting конкуренты и ground RT остаются непокрыты. [Азимут: старт через Ярославль]({S['MOW-S12']['url']}).

Для отпускного срока7–14ночей T даёт примеры10/11ночей в разных направлениях. C даёт7ночей, но выбранная цепочка превышает диагностический бюджет10block h/день; T и O в данной точке внутри него. Это ограничение конкретного расписания/аналога, не экономический отказ от ARH, хабов или всех цепочек. В архивном источнике Азимута также есть противоречивый обратный clock: прилёт в Ярославль18:50 и следующий вылет15:20 без day-offset; этот return не принят как itinerary. P03 должен подтвердить реальные трассы, reserve fuel/alternate и полезную нагрузку отдельно для RRJ95B/LR и будущего SJ. P05 требуется оплачиваемый северный отпускной/санаторный OD и собственный переток через MOW/SVX; запросыMOW-D02/MOW-D06.

## C25: Калининград–Поволжье

СрезP02 exactd9486f1 сохраняет Nordwind: GOJ→KGD N4-860 вторник/суббота07:40–09:50, период27.10.2026–27.03.2027; KGD→GOJ N4-859 понедельник/пятница10:35–14:40 до25.12.2026. KUF→KGD N4-856 вторник/суббота17:25–19:10 в зимнем периоде. Это направленные станционные предложения; точные source rows иSHA256 находятся вP02 extract и `programme_pairs.csv`. Физический operator, total/open seats и обратный KGD–KUF этим не установлены. [Стригино: расписание]({S['MOW-S21']['url']}), [Курумоч: расписание]({S['MOW-S20']['url']}).

Цель — VFR/семейный отдых7–14ночей. T и O дают примеры10/11ночей; C —7ночей. Цепочки C через KGD в выбранном reference выходят за10block h/день; для них нужны иное расписание/дни/ресурс, либо иной подтверждённый блок. Существующий прямой конкурент сам по себе не экономический отказ; цена, удобные даты, доступ к терминалам и ответ конкурента должны войти в единый выбор P05.

Для наземной альтернативы официальный туринфоцентр описывает железнодорожное сообщение и транзитные документы. Это условие для сравнения доступности по группам пассажиров, а не основание удалить ground из выбора. Конкретные правила/поезда/тарифы2027–2028 нужно обновить на дату решения. Great-circle не используется как доказанная трасса над Балтикой. [Туринфоцентр: железнодорожный доступ]({S['MOW-S19']['url']}).

## Часы выбранной точки сценария

Числа ниже сопоставляют конструкции, а не прогнозируют экономику. Экипаж, ТО, слоты, ресурс после KEEP и dispatch у всех UNKNOWN. Дневные бюджеты8/10h и стресс-параметры лежат в `sensitivity_checks.csv`; это точки эксперимента, не доверительные интервалы.

| Программа | block h/нед | max block h/день | Диагностическая граница |
| --- | ---: | ---: | --- |
{table}

## Авторские московские треугольники

По exactdceadc9 найдены14 различных названий московских треугольников в96 строках сценариев base/base_sub/cautious/cautious_sub. Некоторые рецепты есть только в отдельных сценариях. Все14 сохранены, разрешены в конкретный ZIA для нашей постановки и получают T/C/O; source rows/hash и сценарное происхождение сохранены. Эти конструкции не приписываются заново исследователю.

{legacy}

Полезная часть авторской модели уже объединяет одинаковые физические пары внутри `direct_network.joint`, распределяя общий спрос между треугольниками. Это решение сохранено с provenance, старое замечание о двойном спросе не перенесено как новый дефект. Однако для нового сравнения всё равно требуются physical airport/date IDs, единые P05 demand pools, конкуренция, futureKEEP и общий P09 расчёт. Старые годовые суммы не складываются с новыми программами.

## Поставки, экономика и Stage B

`delivery_branches.json` разделяет существующий SSJ с именованным донором, новый SJ с поступлением не ранееH2 2027, partial, delay и0новыхSJ. Количество/ready dates RW неизвестны; собственного прогноза поставок здесь нет. Ввод равен позднейшему из передачи+подготовки, готовности экипажа/ТО и разрешений. При0новых действующий KEEP не исчезает. Во всех основных ветвях0новыхТу214; действующий Tu-бизнес KEEP сохраняется.

`economics_contract.json` использует P04/P05/P06, не отдельную денежную/захватную модель. P04 пороги TH-FARE, TH-FIXED, TH-LAUNCH, TH-MRO, TH-SUPPORT, TH-COFINANCE, TH-FUNDING и TH-OPTION переданы по exact620a0ac. Они требуют полного набора остальных термов; при изменении тарифа спрос пересчитывается. Будущая поддержка имеет явную no_award ветвь0, фактическое присуждение UNKNOWN. Неизвестные расходы и потерянный бизнес нулём не заполнены. Во всех программах passengers/revenue/full result/cash остаются JSONnull, statusNOT_RUN.

Для приоритетного следующего сравнения предложены C19 T/C/O, C25-GOJ/KUF T/O плюс пересмотр C, C08 T/O плюс пересмотр C. Причина приоритета — обнаруженное влияние календаря, доказанная историческая продажа или текущий опубликованный конкурент и конкретные ограничения формы. Прочие14 авторских рецептов остаются открыты и имеют программы, а не искусственные причины отказа. `hypothesis_dispositions.csv` содержит исходы C08/C19/C25 и каждой авторской географии; `dependency_requests.csv` перечисляет10конкретных запросов Stage B.

Полный outcome требует принятия входов, коммерческого спроса, реального расписания/ресурса и общего результата относительно отсутствия проекта в том же будущем периоде. Сеть8–12уникальныхairportpairs относится к общей maincase сети конца2028, а не к каждому московскому модулю. P09 соединяет хабы и прямые программы общим пересчётом; результат Stage A не является доказательством прибыльности или достижения№2.

## Файлы и воспроизведение

- `direct_candidates.csv`, `programme_candidates.json`, `programme_pairs.csv`, `recipes.json` — определения и происхождение программ.
- `dated_templates/` — предлагаемые физические плечи, полные обороты, полезные RT окна. JSONnull всегда означает UNKNOWN.
- `monthly_calendar.csv`, `delivery_branches.json`, `business_changes.csv` — календарь и действия по бизнесу; не общий годовой forecast.
- `airport_status.csv`, `KEEP_evidence.csv`, `market_evidence.csv`, `ground_evidence.csv`, `sources_registry.json`, `sources_review.json`, `input_manifest.json` — доказательства, единицы, периоды, coverage и hashes.
- `assumptions.csv/json`, `dependency_requests.csv`, `economics_contract.json`, `hypothesis_dispositions.csv` — допущения, исходы и Stage B.
- `verification.json`, `manifest.json`, `handoff.json` — локальная проверка и пакет координатору. Manifest не хеширует себя.

Воспроизведение без сети: `python3 build_package.py`, `python3 complete_notes.py`, `python3 verify_package.py`, `python3 seal_package.py` из этого каталога. `acquire_inputs.py` повторно читает только exactSHA Git blobs и пишет сюда; `acquire_sources.py` — новое сетевое получение, оно может дать другой снимок и не требуется для frozen проверки. Никаких Git mutations, записей в общие файлы, браузера, новых платных сервисов или внешних сообщений кроме разрешённой передачи координатору не было. Временных зависимостей/сборок не создано.
'''
text=re.sub(r'(?<=[А-Яа-яЁё])(?=\d)|(?<=\d)(?=[А-Яа-яЁё])',' ',text)
text=re.sub(r'(?<=[а-яё])(?=[A-Z])|(?<=[A-Z])(?=[а-яё])',' ',text)
text=re.sub(r'(?<=\d)(?=min\b|block\b|km\b|h\b)',' ',text)
text=text.replace('RW202','RW 202').replace('exactd9486f1','exact d9486f1').replace('exact620a0ac','exact 620a0ac').replace('exactdceadc9','exact dceadc9')
(R/'handoff.md').write_text(text)
print(json.dumps(dict(source_records=len(sources),sources_saved=sum(bool(s.get('saved_path')) for s in sources),airport_records=len(airports),keep_records=len(keep),sensitivity_cases=len(sensitivity)),ensure_ascii=False))
