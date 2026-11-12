#!/usr/bin/env python3
"""Build the bounded P00R review; standard library, pinned Git reads only."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PLAN = 'b4d2ddf690440eb5cd051839cc263cf16b364ca4'
AUTHOR = 'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6'
FIVE = 'c18f7640ea36647a05b39089e5293f22dd009f63'
PP = 'context/34_full_programme_plan_20261112/'
STAMP = '2026-11-12T11:56:54Z'

def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def table(name, rows):
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in row.items()})

def blob(sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path], cwd=ROOT)

sources = []
def source(sid, uri, date, grain, statement, applicability, kind='reused_pinned', locator=''):
    sources.append(dict(source_id=sid, uri=uri, source_date=date, retrieved_at=STAMP,
                        status='read', collection=kind, granularity=grain, locator=locator,
                        verified_statement=statement, applicability=applicability))

source('PLAN', f'git:{PLAN}:{PP}common_spec.json', '2026-11-12', 'contract',
       'Приняты четыре раздела; одинаковый будущий KEEP, общие поездки/кресла, один тариф, cash и четыре ветви поставок.',
       'Проверяемая спецификация, не реализация.', locator='metric_policy; tables; modelling_rules; scenario_axes')
source('REQ', f'git:{PLAN}:{PP}requirements.csv', '2026-11-12', 'requirement_id',
       'R03/R09–R12 требуют совместную сеть, ресурс, будущий KEEP, деньги и совместимые метрики.', 'Постановка программы.')
source('METHOD', f'git:{PLAN}:{PP}method_map.csv', '2026-11-12', 'method_id',
       'M01–M06 описывают связи прогноза, конкурентного продукта, расписания и сетевой вместимости.',
       'Карта методов не заменяет формулы, калибровку и исполняемые проверки.')
source('BASELINE', f'git:{AUTHOR}:src/network_model.py', '2026-11-12 pinned', 'function',
       'leg_share использует частотный прокси без цены конкурента; money получает выручку уже за вычетом миграции и делит прирост на market_pax_2025; годовые суммы получаются через W.',
       'Доказательство свойств указанного кода, без нового полного прогона и без переноса ошибки на ещё не написанный P06.',
       locator='127–141; 261–298; 340–415; 553–612; 650–668')
source('FIVE', f'git:{FIVE}:context/33_five_city_reassessment_20261112/common_economics/report.md',
       '2026-11-12', 'saved_model_report',
       'Отчёт ограничивает результат переменным вкладом, формальный KEEP — отсутствием дополнительной программы; календарь, полный cash и совместная hub+direct отмечены NOT_RUN.',
       'Сохранённые границы прежней проверки, не проверка новых входов и не новый прогон.', locator='21–29; Проверки, пределы и воспроизведение')
source('USER_ROUTE', 'current-task:user-message:Q-P00R-001-confirmed', '2026-11-12', 'requirement',
       '8–12 уникальных аэропортовых пар — целевая проектная сеть к концу 2028 основного сценария; промежуточные и ресурсно ограниченные ветви могут быть меньше.',
       'USER_CONFIRMED; передано координатором в текущую задачу.', 'new_user_instruction')
source('USER_MONEY', 'current-task:user-message:P04-Q001-confirmed', '2026-11-12', 'requirement',
       'Полный добавочный операционный результат; инвестиции, финансирование и налоги отдельно. Стоимость использования самолёта и запуска учитывается.',
       'USER_CONFIRMED; передано координатором. Сроки/суммы выплат не установлены этим решением.', 'new_user_instruction')
source('USER_SEASON', 'current-task:user-message:annual-seasonal-coverage', '2026-11-12', 'coverage_requirement',
       'Нужны годовой цикл/сезонные шаблоны, месячная история 2025 и доступный 2026, W26/27/S27 и тарифные срезы; прогноз 2027–2028 отдельно.',
       'Требование к P02/P05; результаты этих пакетов P00R не получал и не проверял.', 'new_user_instruction')
web_sources = [
 ('IATA','https://www.iata.org/en/training/courses/route-profitability/alc024veen01/en/','publication date UNKNOWN; read 2026-11-12','course description',
  'Структура анализа связывает спрос, расписание, затраты и влияние новых маршрутов на существующую сеть.',
  'Программа курса; не получена закрытая методика, калибровка или сертификация.', 'About the course'),
 ('MIT_SCHEDULE','https://www.ocw.mit.edu/courses/16-75j-airline-management-spring-2006/a28aa07c64a983ce2cd475b9f7e32f16_lect5.pdf','2006-02-22','lecture pages',
  'Маршрут пассажира состоит из физических плеч; назначение флота требует вместимости, баланса, разворотов и ограничений парка.',
  'Методические определения и связи. Числа американских примеров не параметры RW.', 'pages 5, 9–10, 13, 16–18 (1-based)'),
 ('MIT_NETWORK','https://dspace.mit.edu/entities/publication/26180a78-33ef-49e0-8a2a-2033b823a349','2002','thesis abstract',
  'Перегрузка одного плеча влияет на весь пересадочный путь; spill и recapture взаимозависимы.',
  'Прочитаны описание и abstract, не полный текст диссертации. Размер экономии не переносится.', 'Abstract'),
 ('MITRE','https://www.mitre.org/news-insights/publication/building-timetable-bottom-demand-micro-econometric-approach','2003-05-01','research publication description',
  'Аэропортовые агрегаты не определяют рост отдельных маршрутов; OD и выбор пути связываются с расписанием.',
  'Аргумент о гранулярности, не российская оценка спроса.', 'description paragraphs'),
 ('MIT_COURSE','https://ocw.mit.edu/courses/1-206j-airline-schedule-planning-spring-2003/','2003 spring','course description',
  'Планирование расписания, парка, обслуживания, экипажей и пассажирского состава — связанные задачи.',
  'Нужны совместимые проверки; промышленный оптимизатор не требуется.', 'Course Description'),
 ('IAS7','https://www.ifrs.org/issued-standards/list-of-standards/ias-7-statement-of-cash-flows.html/','current overview read 2026-11-12','official standard overview',
  'Начисленный результат и cash различаются; некэшевые статьи, сроки расчётов, инвестиционные и финансовые потоки сверяются отдельно.',
  'Основание денежного моста. Это управленческий сценарный расчёт, не утверждение соответствия финансовой отчётности IFRS.', 'About')
]
for sid, url, date, grain, statement, scope, loc in web_sources:
    source(sid,url,date,grain,statement,scope,'new_web_read_of_existing_reference' if sid!='IAS7' else 'new_web_reference',loc)
table('sources.csv',sources)

cases=[]
def case(cid, finding, title, inputs, expected, bad, equation, explanation, sources_, unit, change):
    cases.append(dict(case_id=cid,finding_id=finding,title=title,assumption_id='P00R-'+cid,
                      source_ids=sources_,status='synthetic_counterexample',period='fictional unless explicit in inputs',
                      unit=unit,inputs=inputs,expected=expected,incorrect_result=bad,equation=equation,
                      conclusion=explanation,affected_recheck=change))

case('CE01','F02','Будущий KEEP',{'historical':100,'keep_future':120,'project_future':130},
     {'delta':10},{'historical_delta':30},'130 - 120 = 10',
     'Рост без проекта нельзя приписывать проекту.', ['PLAN','IATA'],'поездки/одинаковый будущий год','KEEP period or external scenario')
case('CE02','F01','Коллизия режима оценки',{'fixed':100,'adapted':125,'old_key':['CASE_SJ','P','base','2028-01']},
     {'distinct_records':2},{'old_key_distinct_records':1},'key includes evaluation_id -> 2 rows',
     'results_monthly без режима/версии оценки не различает fixed и adaptation.', ['PLAN'],'строк','evaluation identifiers')
case('CE03','F02','Самолёт нельзя назначить двум одновременным рейсам',
     {'available':2,'reserve':1,'block_limit':8,'flights':[[8,10],[8.5,10.5]]},
     {'total_block_hours':4,'active_required':2,'active_available':1,'feasible':False},
     {'hours_only_feasible':True},'4 <= 8, but 2 simultaneous assignments > 1 active tail',
     'Часы — необходимое, но недостаточное условие; резерв не выполняет одновременно плановый рейс.', ['PLAN','MIT_SCHEDULE'],'ВС; UTC-часы','tail intervals or reserve policy')
case('CE04','F01','Ссылка на датированное плечо',
     {'arrive':'2028-01-02T10:00:00+00:00','depart':'2028-01-03T11:00:00+00:00','min_connection_min':45,'max_connection_min':180},
     {'connection_min':1500,'bookable':False},{'same_clock_connection_min':60},
     '(dated departure - dated arrival) / minute',
     'Номер рейса/время суток без даты создаёт ложную стыковку. Пороги здесь учебные.', ['PLAN','MIT_SCHEDULE'],'минуты','itinerary leg reference or MCT')
case('CE05','F04','Локальные и пересадочные продажи делят одно плечо',
     {'seats_ab':100,'seats_bc':100,'committed_local_ab':70,'through_requests':50,'local_fare':4000,'through_fare':9000},
     {'through_carried':30,'ab_load':100,'bc_load':30,'journeys':100,'segments':130,'revenue':550000},
     {'ab_load':120},'through=min(50,100-70,100); R=70*4000+30*9000',
     'При зафиксированных 70 локальных бронированиях допустимы 30 сквозных. Это не доказательство оптимальности такого sales mix.', ['PLAN','MIT_NETWORK'],'поездки; сегменты; RUB','shared seat allocation')
case('CE06','F04','Сквозной тариф учитывается один раз',{'journeys':10,'legs':2,'fare':9000},
     {'revenue':90000,'segments':20},{'revenue':180000},'R=10*9000; segments=10*2',
     'Разнесение дохода по плечам возможно только с весами, сумма которых равна 1.', ['PLAN','MIT_SCHEDULE'],'RUB; сегменты','fare ownership')
case('CE07','F04','Сумма отдельных программ превышает рынок',
     {'market':100,'standalone_rw_weight':6,'competitor_weight':4,'joint_rw_weights':[6,6]},
     {'standalone_each':60,'joint_rw':75,'joint_other':25,'sum_standalone':120},
     {'joint_rw':120},'standalone=100*6/(6+4); joint=100*(6+6)/(6+6+4)',
     'Сравниваемые альтернативные программы получают отдельные копии рынка; совместно выбранные программы делят один рынок. Веса — только учебная функция.', ['PLAN','MIT_NETWORK'],'поездки','joint product set')
case('CE08','F03','Ответ на изменение конкурента',{'market':100,'rw_weight':4,'competitor_before':4,'competitor_after':8,'outside_weight':2},
     {'rw_before':40,'rw_after':200/7}, {'rw_after_frozen':40},
     '100*4/(4+4+2)=40; 100*4/(4+8+2)=200/7',
     'Изменение привлекательности конкурента должно проходить через выбор, не только через подпись. Коэффициенты не оценены по рынку.', ['PLAN','BASELINE','MITRE'],'поездки','competitor price/capacity/product or response policy')
case('CE09','F07','Собственный переток и единицы роста',{'same_rw_journeys':50,'old_legs':1,'new_legs':2},
     {'net_new_journeys':0,'delta_segments':50},{'net_new_journeys':50},
     'delta journeys=50-50; delta segments=50*2-50*1',
     'Дополнительный сегмент не доказывает нового клиента. Отчётная метрика перевозчика требует отдельного адаптера.', ['PLAN','REQ'],'поездки; сегменты','metric mapping or own migration')
case('CE10','F03','Соседние аэропорты делят городской рынок',{'city_demand':100,'airport_a':60,'airport_b':40},
     {'total_allocated':100},{'separate_full_markets':200},'60+40=100',
     'Дублирующиеся зоны тяготения не независимые рынки; альтернатива аэропорта входит в выбор единого demand_pool_id.', ['PLAN','MITRE'],'поездки','catchment allocation')
case('CE11','F05','Донор учитывается один раз',{'keep_revenue':100,'keep_cost':60,'project_old_revenue':70,'project_old_cost':50,'project_new_revenue':80,'project_new_cost':40},
     {'keep_result':40,'project_result':60,'delta_result':20,'lost_donor_contribution':20},
     {'double_deduction_delta':0,'deduct_old_revenue_only_delta':10},
     '(70+80-50-40)-(100-60)=20; new contribution 40 minus donor contribution 20 = 20',
     'Полная разность P−KEEP уже содержит переток и сэкономленные затраты; ещё один вычет донора ошибочен.', ['PLAN','BASELINE','IATA'],'RUB условного масштаба','affected-business scope or cost avoidability')
case('CE12','F04','Совместная фиксированная стоимость',{'revenue_a':80,'revenue_b':70,'flight_cost_a':40,'flight_cost_b':40,'shared_base_cost':30},
     {'sum_standalone_result':10,'joint_result':40},{'joint_result':10},
     'joint=80+70-40-40-30; standalone sum=(80-40-30)+(70-40-30)',
     'Даже при непересекающемся спросе общий запуск базы начисляется один раз; автономные суммы не равны совместному результату.', ['PLAN'],'RUB условного масштаба','cost event ownership')
case('CE13','F06','Прибыль, денежный поток и пиковое финансирование',
     {'revenue':100,'support':30,'variable_cost':60,'fixed_cost':20,'startup_expense':30,'depreciation':10,'capex':60,'deposit':50,'ticket_cash_m1':80,'ticket_cash_m2':20,'support_cash_m3':30,'deposit_refund_m3':50,'opening_cash':0,'minimum_cash':0,'tax_cash':[0,0,0,0],'interest_cash':[0,0,0,0],'financing_cash':[0,0,0,0]},
     {'operating_result':10,'cash_before_financing':[-110,-30,20,80],'cumulative_cash':[-110,-140,-120,-40],'peak_funding_month_end':140,'terminal_shortfall':40,'cash_from_profit_bridge':-40},
     {'profit_as_cash':10,'funding_from_terminal_only':40},
     'op=100+30-60-20-30-10; cash=[-60-50,80-60-20-30,20,30+50]; F=max(0,-min(cumsum))',
     'Положительный операционный результат совместим с потребностью 140. Ссуда не выручка; CAPEX и депозит не текущие расходы. Налоги/проценты равны нулю только в этом явно искусственном примере.', ['USER_MONEY','IAS7'],'RUB условного масштаба; месяцы m0..m3','accrual/cash event or funding boundary')
case('CE14','F06','Компенсация топлива не учитывается дважды',{'gross_fuel':100,'fuel_support':20},
     {'net_expense':80,'cash_m1':-100,'cash_m3':20},
     {'net_expense_after_double_support':60},'economic=100-20; cash dates remain -100 then +20',
     'Выбрать gross fuel + support либо net fuel без второго support; в cash восстановить валовой платёж и дату возмещения.', ['PLAN','BASELINE','IAS7'],'RUB условного масштаба','support recognition or payment lag')
case('CE15','F05','Неизвестный расход и порог',{'known_delta_before_missing_cost':20,'missing_cost':None},
     {'full_delta':None,'break_even_missing_cost':20}, {'full_delta_assuming_zero':20},
     'delta=20-X; sign positive iff X<20',
     'Порог помогает принять решение без выдуманного диапазона; неизвестное поле не превращается в ноль.', ['PLAN'],'RUB условного масштаба','missing cost estimate')
case('CE16','F07','Изменившийся знаменатель доли',{'keep_rw':10,'keep_market':100,'project_rw':20,'project_market':110},
     {'delta_share_pp':100*(20/110-10/100)}, {'delta_share_pp_fixed_denominator':10},
     '100*(20/110-10/100)',
     'Если проект привлекает поездки из других видов транспорта, общий авиационный рынок может измениться. Фиксированный знаменатель допустим лишь как подписанное допущение.', ['PLAN','REQ'],'процентные пункты','denominator policy')
case('CE17','F01','Сезонная неделя не год',{'summer_weeks':10,'summer_pax_week':100,'other_weeks':42,'other_pax_week':20},
     {'annual_pax':1840}, {'annual_pax_peak_times_52':5200},
     '10*100+42*20=1840',
     'Недельные шаблоны требуют покрытия сезона и календарного развёртывания. В рабочей модели используются даты и 24 месяца, не учебные 52 недели.', ['USER_SEASON','BASELINE'],'поездки/условный год','season/calendar profile')
case('CE18','I01','Помесячный пик — нижняя граница внутримесячного',{'prelaunch_cash':-110,'month1_payments_first':-110,'month1_receipts_last':80},
     {'month_end_funding':140,'event_order_funding':220}, {'sufficient_liquidity_claim':140},
     'month-end deficit=110+110-80; interim deficit=110+110',
     'Можно выпустить помесячный результат с явной границей; для обещания достаточной ликвидности нужны даты крупных выплат или запас.', ['IAS7','USER_MONEY'],'RUB условного масштаба','large cash event timing')
case('CE19','I02','Монотонность требует неизменной стоимости ресурса',{'candidate_contribution':100,'new_committed_idle_lease':20},
     {'larger_feasible_set_keeps_candidate':True,'new_result_after_extra_commitment':80}, {'must_be_at_least':100},
     '100-20=80',
     'Дополнительная доступность сохраняет старую допустимую программу, но рост обязательных платежей может уменьшить её результат. Не применять тест монотонности прибыли к изменившемуся сценарию затрат.', ['PLAN'],'RUB условного масштаба','resource envelope or committed costs')
case('CE20','F07','Yield и средний доход на поездку',{'yield_rub_per_pax_km':2,'journeys':10,'distance_km':1000},
     {'revenue':20000}, {'revenue_without_distance':20}, '2*10*1000=20000',
     'Различать RUB/поездку и RUB/пасс.км. Для маршрута с пересадкой заранее закрепить базу расстояния и состав дохода.', ['REQ'],'RUB','net fare/yield unit')
dump('counterexample_inputs.json',cases)
table('minimal_counterexamples.csv',cases)

patches=[]
def patch(pid, finding, target, key, fields, rule, check, owner):
    patches.append(dict(patch_id=pid,finding_id=finding,target=target,primary_key=key,required_fields=fields,
                        invariant=rule,acceptance_cases=check,owner=owner,status='PROPOSED_FOR_COORDINATOR_INTEGRATION'))
patch('SP01','F01','evaluation_context','evaluation_id',
      'programme_id; programme_version; fleet_scope_id; external_scenario_id; delivery_calendar_id; market_version; choice_version; cost_version; response_policy_id; evaluation_mode; decision_date; information_set_id; keep_evaluation_id; input_manifest_sha256',
      'Сравнение = два evaluation_id с одинаковым внешним миром, временным горизонтом и заданной ресурсной политикой. Альтернативы не расходуют рынок друг друга. Совместная программа — один evaluation_id. Независимые forecast/scenario версии не перезаписывают факты.', 'CE01;CE02','P00/P06')
patch('SP02','F01','markets','market_version,external_scenario_id,demand_pool_id,month,customer_segment',
      'origin_market; destination_market; direction; market_basis; potential_journeys; lower; upper; range_basis; source_id; source_period; as_of; coverage; status; assumption_id',
      'Явно различать potential travel (включает no-travel) и realized air OD. Месяцы 2027-01..2028-12; история 2025/2026 и published offers хранятся отдельно. Пересечение catchment устранено на уровне demand_pool_id.', 'CE10;CE17','P02/P05')
patch('SP03','F03','alternatives','offer_set_id,demand_pool_id,travel_date_or_period,customer_segment,product_id',
      'carrier; operator; airport_pair; gross_fare; net_fare; currency; fare_basis; baggage; duration; frequency; sellable_capacity; travel_period; observed_at; booking_lead_days; sales_channel; coverage; availability_status; response_policy_id; assumption_id',
      'Цена/время/частота/доступность входят в выбор либо остаются явными сценарными входами. Пробел покрытия не отсутствие конкурента. KEEP и проект используют одну политику ответа, зависящую от предложения, не обязательно одинаковый фактический ответ.', 'CE08;CE10','P02/P05/P06')
patch('SP04','F01','flights','schedule_id,flight_instance_id',
      'operator; flight_number; origin_airport; destination_airport; departure_utc; arrival_utc; local_time_zone; aircraft_variant; seats; saleable_seats; technical_blocked_seats; scheduled_status; source_status; source_period; assumption_id',
      'flight_instance_id однозначно идентифицирует оператор+дату+направление+вылет. saleable_seats = seats - technical_blocked_seats, до коммерческого распределения контрактов. proposed — статус расписания, scenario/observed/published_offer — отдельный статус данных. Не подставлять MOW вместо аэропорта.', 'CE03;CE04;CE05','P03/P06')
patch('SP05','F04','itineraries + itinerary_legs','evaluation_id,itinerary_id / evaluation_id,itinerary_id,leg_sequence',
      'demand_pool_id; departure_date; product_id; net_journey_fare; currency; commercial_status; min_connection; max_connection; schedule_id; flight_instance_id; revenue_allocation_weight; assumption_id',
      'Каждый leg ссылается на датированный физический рейс. Условия стыковки и доступность билета проверены либо unknown/conditional. Один journey_fare; сумма весов дохода=1. Дальнейший leg может иметь другую дату.', 'CE04;CE06','P05/P06')
patch('SP06','F04','allocations (can be nested engine output)','evaluation_id,demand_pool_id,month,customer_segment,product_id',
      'requested; carried; spilled; recaptured_in; recaptured_out; outside_or_other; committed_sales; assumption_id',
      'Сумма конечных выборов=единый demand pool; внутри физического рейса retail carried + contract carried + unfilled nonreleased contract seats <= saleable_seats. Занятое контрактное место не считать второй раз в блоке. Recapture переносит, а не создаёт поездки. Законтрактованные места исключены из свободного розничного инвентаря; block payment и билетная выручка одного места не дублируются.', 'CE05;CE07;CE12','P05/P06')
patch('SP07','F02','fleet_calendar + assignments','resource_scenario_id,aircraft_or_cohort_id,date / evaluation_id,flight_instance_id',
      'variant; count; transfer_date; service_entry_date; maintenance; crew_available; reserve_role; location; availability_interval; donor_task_id; committed_payment_id; action_keep_add_cut_move; opportunity_reference_id; assumption_id',
      'Одна доступная сценарная группа эквивалентна числу физических бортов; reserve/maintenance не прибавляются к активным. Проверяются перекрытие, позиция, разворот и ввод. Общий ресурсный потолок не обязывает использовать все борта; остаток и его реальные платежи видны.', 'CE03;CE19','P03/P06')
patch('SP08','F02','KEEP policy','keep_policy_id,fleet_scope_id,external_scenario_id',
      'future_period; committed_fleet_calendar_id; existing_flights_version; alternative_new_resource_use; excluded_unaffected_scope; competitor_response_policy_id; fixed_or_adaptive; decision_date; avoidable_cost_rules; assumption_id',
      'Основное сравнение условно на одинаково доступном/уже обязательном парке. KEEP сохраняет будущее действующее дело и заданное альтернативное применение; нельзя автоматически считать все новые борта бесплатными/свободными. Решение купить дополнительный борт при отсутствии проекта — отдельная investment/no-acquisition ветвь. Не вычитать opportunity cost повторно после P−KEEP.', 'CE01;CE11;CE19','P00/P03/P06/P09')
patch('SP09','F05','economic_events','evaluation_id,economic_event_id',
      'owner_asset_or_flight_or_journey_or_base; category; scope; driver_unit; quantity; rate; amount; currency; price_year; fx_policy; accrual_month; noncash_flag; avoidability; shared_event_id; source_id; assumption_id',
      'Учитывать net journey revenue, variable operating expense, incremental operating fixed/base/aircraft-use/startup/exit expenses и support по одному выбранному правилу. Δoperating_result = operating_P − operating_KEEP. CAPEX, financing и taxes отдельны; стоимость использования капитала не исчезает. Нельзя одновременно полную аренду и те же lease depreciation/interest без выбранной конвенции.', 'CE11;CE12;CE14;CE15','P04/P06')
patch('SP10','F06','cash_events','evaluation_id,cash_event_id',
      'economic_event_id nullable; related_asset_or_contract_id; payment_date_or_month; amount_signed; category operating/investing/tax/financing; currency; fx_at_payment; receivable_or_payable_change; deposit_flag; source_id; status; assumption_id',
      'Один экономический event может иметь несколько платежей, а CAPEX/депозит не иметь текущего операционного расхода. Сверить открывающиеся/закрывающиеся receivables, advances, payables. Support отдельно начислен/получен, financing не revenue. Перед запуском включить реальные предоплаты; после 2028 сохранить обязательства/дебиторку/условия выхода.', 'CE13;CE14;CE18','P04/P06')
patch('SP11','F06','results_monthly','evaluation_id,month',
      'journeys; passenger_segments; compatible_carried_passengers; revenue_net; variable_contribution; operating_result; delta_operating_result; investing_cash; tax_cash; cash_before_financing; funding_before_financing; financing_cash; closing_cash; minimum_cash; metric_definition_id; denominator_id; unknown_dependencies',
      'cash_before_financing = operating cash + investing cash + tax cash; delta и абсолютный поток не смешивать. Funding = max_t(0, minimum_cash_t − opening_cash − cumulative_cash_before_financing_t). Отдельно project incremental funding и whole-business funding, если KEEP cash известен. При неизвестном KEEP cash полный бюджет компании UNKNOWN.', 'CE13;CE16;CE18','P04/P06/P09')
patch('SP12','F07','metric_definitions + results_annual','metric_definition_id / evaluation_id,year,metric_definition_id',
      'journey_definition; segment_definition; carrier_reporting_rule; carrier_vs_group; business_scope; numerator; denominator; denominator_policy; unit; source_period; source_id; assumption_id',
      'Annual passengers для рейтинга только через документированную совместимую методику источника; не автоматически OD или flight segments. Считать P и KEEP, затем разность долей. Отдельно own migration и new-to-RW journeys. Нет удвоения одной поездки при цифровой/сетевой инициативе.', 'CE09;CE16;CE20','P05/P06/P10')
patch('SP13','F01','season_coverage + programme_target','coverage_id / programme_id,programme_version,target_date',
      'observation_period; schedule_season; months_covered; day_of_week; booking_lead; history_or_offer_or_forecast; gaps; forecast_month; target_pair_count; target_count_status; source_id; assumption_id',
      'Не экстраполировать декабрьскую неделю на год. Наблюдения 2025/2026, W26/27/S27 и прогноз 2027–2028 различимы. 8–12 уникальных физических аэропортовых пар у целевой проектной сети на конец 2028 основного сценария; меньшие этапы и дефицитные ветви разрешены и подписаны.', 'CE17;Q-P00R-001','P02/P05/P09')
table('schema_patch.csv',patches)

findings=[]
def finding(fid, severity, title, evidence, impact, fix, cases_, owners, gate):
    findings.append(dict(finding_id=fid,severity=severity,title=title,evidence=evidence,
                         defect_type='contract_operationalization_gap' if fid!='F03' else 'contract_gap_and_demonstrated_legacy_limit',
                         impact=impact,minimum_fix=fix,counterexample_ids=cases_,owners=owners,
                         blocks=gate,status='OPEN_FOR_INTEGRATION_NOT_AN_IMPLEMENTATION_FAILURE'))
finding('F01','S1','Закрепить контекст оценки, даты и сезонность',
        [f'{PLAN}:{PP}common_spec.json:153–205,248–251',f'{AUTHOR}:src/network_model.py:650–668','USER_SEASON'],
        'Ключи markets/alternatives/flights и results_monthly не кодируют все версии, расписание и fixed/adaptive; годовой прогноз можно смешать с предложением.',
        ['SP01','SP02','SP04','SP05','SP13'],['CE02','CE04','CE17'],['P00','P02','P05','P06'],['integrated_run'])
finding('F02','S1','Определить будущий KEEP и одинаковый ресурсный предел',
        [f'{PLAN}:{PP}common_spec.json:253–264',f'{FIVE}:context/33_five_city_reassessment_20261112/common_economics/report.md:23'],
        'Исторический формальный ноль KEEP и агрегатные часы не устанавливают контрфактический бизнес, реальные ограничения и альтернативное использование борта.',
        ['SP07','SP08'],['CE01','CE03','CE11','CE19'],['P00','P03','P06','P09'],['integrated_run'])
finding('F03','S1','Определить общий рынок и реакцию выбора на продукт конкурента',
        [f'{PLAN}:{PP}method_map.csv:3',f'{AUTHOR}:src/network_model.py:280–298'],
        'Частотный прокси baseline не меняется с ценой конкурента. Разные аэропорты и наземные варианты могут дважды использовать один городской спрос; realized-air OD нельзя без объяснения считать всем potential travel.',
        ['SP02','SP03','SP06'],['CE08','CE10'],['P02','P05','P06'],['market_claims_in_integrated_run'])
finding('F04','S1','Записывать совместное распределение поездок, кресел и затрат',
        [f'{PLAN}:{PP}common_spec.json:165–175,253–264',f'{PLAN}:{PP}method_map.csv:5','MIT_NETWORK'],
        'Принцип задан верно, но нет выходного объекта allocation и точных leg references; сумма независимых сетей может нарушить кресла, спрос и владение расходом.',
        ['SP05','SP06','SP09'],['CE05','CE06','CE07','CE12'],['P05','P06'],['integrated_run'])
finding('F05','S1','Разделить операционный результат и разность всего затронутого бизнеса',
        [f'{AUTHOR}:src/network_model.py:127–141,382–415,650–668','USER_MONEY'],
        'Legacy revenue уже содержит forgone revenue. Повторное вычитание или сохранение только вычета старой выручки теряет сэкономленные расходы и искажает P−KEEP.',
        ['SP08','SP09','SP11'],['CE11','CE12','CE14','CE15'],['P04','P06'],['financial_conclusions'])
finding('F06','S1','Сделать начисления, cash и финансирование сверяемыми',
        [f'{PLAN}:{PP}common_spec.json:183–205','USER_MONEY','IAS7'],
        'Таблица ставок и месячный итог без payment events не объясняют депозиты, лаги, запуск, выплаты поддержки и пиковый дефицит. Чистый операционный плюс не означает достаточные деньги.',
        ['SP10','SP11'],['CE13','CE14','CE18'],['P04','P06','P09'],['funding_or_full_economy_conclusions'])
finding('F07','S1_SCOPED','Указать адаптер отчётных пассажиров и знаменатель доли',
        [f'{PLAN}:{PP}common_spec.json:26–42',f'{AUTHOR}:src/network_model.py:657–668'],
        'primary_growth определён условием совместимости, но сама отчётная единица ещё не задана. +1 сегмент пересадки может не быть +1 новым пассажиром для RW; исторический знаменатель не будущая доля.',
        ['SP12'],['CE09','CE16','CE20'],['P05','P06','P10'],['market_share_and_number2_claims_only'])

unknowns=[
 {'id':'U01','field':'OD level; customer segments; price/time/frequency coefficients; airport overlap','owner':'P02/P05','treatment':'Сценарные предпосылки и пороги смены решения; вневыборочная проверка только при независимых опорах. Структурные 0..1 вероятности не эмпирический доверительный интервал.','blocks':'Безусловный прогноз рынка; не каркас или условный сценарий.'},
 {'id':'U02','field':'variant-specific available tails by date; donor task; reserve; crew/MRO','owner':'P03','treatment':'Четыре сценария N(t), явный ввод и аналог по типу. Не использовать batch announcement как парк.','blocks':'Заявление фактической выполнимости; сценарный расчёт возможен.'},
 {'id':'U03','field':'base/startup/exit/lease or aircraft-use incremental expense and payment schedule','owner':'P04','treatment':'Источники диапазона либо UNKNOWN и break-even threshold; один согласованный способ учёта использования борта.','blocks':'Полный численный результат без условности.'},
 {'id':'U04','field':'support entitlement, caps, accrual/payment lag, taxes, financing terms','owner':'P04','treatment':'Условия конкретной схемы, отдельные ветви с/без поддержки; налоги/финансирование отдельно; UNKNOWN не 0.','blocks':'Подтверждённая величина финансирования.'},
 {'id':'U05','field':'official carrier passenger definition and future denominator','owner':'P10','treatment':'Сначала сопоставимый справочник метрик и периодов; до него journeys/segments отдельно, rank/share UNKNOWN.','blocks':'Доля и №2; не seat arithmetic.'},
 {'id':'U06','field':'international access and currency/cost/contract terms','owner':'P02I/P08I','treatment':'Условные международные ветви отдельно; не задерживать самостоятельный CASE_SJ.','blocks':'Соответствующая международная рекомендация.'},
 {'id':'U07','field':'opening unrestricted company cash; existing business cash; minimum cash policy','owner':'P04/P10','treatment':'Выдать добавочную потребность с явно заданным boundary; весь бизнес UNKNOWN, если KEEP cash неизвестен.','blocks':'Полный бюджет компании; не расчёт добавочной программы.'}
]

register=[]
def assumption(aid, kind, value, unit, basis, affects, sensitivity, refine, approval='REVIEWER_PROPOSED_NOT_USER_APPROVED', lower='UNKNOWN', upper='UNKNOWN'):
    register.append(dict(assumption_id=aid,subject_version='P00R-v1',kind=kind,value=value,unit=unit,
                         selected_by='Пользователь; подтверждение передано координатором' if approval=='USER_CONFIRMED' else 'P00R methods_review / gpt-6-astra xhigh',basis=basis,approval_status=approval,
                         lower=lower,upper=upper,range_basis='Не эмпирический диапазон; синтетические значения проверяют тождество.' if kind=='synthetic_fixture' else 'Точная область указана в basis; неподтверждённые границы UNKNOWN.',
                         affected_conclusions=affects,sensitivity=sensitivity,refinement_method=refine,
                         admissible_use='method_check_only' if kind=='synthetic_fixture' else 'explicit_conditional_or_confirmed_rule'))
for c in cases:
    assumption(c['assumption_id'],'synthetic_fixture',c['inputs'],c['unit'],
               'Числа выбраны проверяющим для минимального контрпримера, не оценка RW; источники принципа: '+','.join(c['source_ids']),
               c['case_id']+'; '+c['finding_id'],c['equation'],
               'В P06 повторить тот же механизм на закреплённых рабочих входах; toy rates/weights не импортировать.')
assumption('P00R-M01','method_choice','Изолированный evaluation_id, общие immutable источники и отдельное allocation внутри каждой альтернативы','правило','PLAN; SP01','F01/F04','CE02/CE07; переоценка только затронутого evaluation','Координатор закрепляет версии; P06 реализует scoped IDs.')
assumption('P00R-M02','method_choice','Одинаковый доступный/обязательный ресурсный потолок; не обязательное равенство использования','правило','PLAN; SP07/SP08','F02','CE03/CE19; отдельно committed versus avoidable resource','Уточнить альтернативное применение и договорные обязательства по каждому борту.')
assumption('P00R-M03','method_choice','Прямой cash ledger и сверка с операционными начислениями','правило','IAS7; USER_MONEY; SP09–SP11','F05/F06','CE11/CE13/CE14','P04 передаёт драйверы/даты/неизвестные; P06 сохраняет оба моста.')
assumption('P00R-M04','requirement_resolution','8–12 уникальных аэропортовых пар у целевой проектной сети к концу 2028 основного сценария','пар','USER_ROUTE; Q-P00R-001','R05/R07/R13','Меньшие этапы допустимы; target_count_met отдельно','Ответ получен; новой пользовательской проверки не нужно.','USER_CONFIRMED',8,12)
assumption('P00R-M05','requirement_resolution','Полный добавочный операционный результат; инвестиции, финансирование и налоги отдельно','RUB; cash','USER_MONEY; P04-Q001','R11/F05/F06','Стоимость использования ВС и запуска должна оставаться в соответствующем учёте','Выбор конкретной аренда/амортизация конвенции P04 с явным составом.','USER_CONFIRMED')
assumption('P00R-M06','method_boundary','Помесячный peak funding — нижняя граница при неизвестном внутримесячном порядке платежей','RUB','IAS7; CE18','F06/I01','140 против 220 в CE18 при одном месячном нетто','Даты крупных предоплат или обоснованный liquidity buffer; не требовать ежедневной модели всей компании.')
assumption('P00R-M07','method_boundary','Геометрическая/агрегатная проверка не равна коммерческой и операционной готовности','статус','MIT_SCHEDULE; MIT_COURSE','F02/F04','CE03/CE04','Уровни checks: algebraic; calendar_feasible; operationally_confirmed; commercially_supported.')
for u in unknowns:
    assumption('P00R-'+u['id'],'material_missing_field','UNKNOWN',u['field'],u['treatment'],u['blocks'],
               'Порог или условные сценарии у владельца; диапазон без опоры не назначен.',u['owner']+': '+u['field'])
dump('assumptions_register.json',register)
table('assumptions_register.csv',register)
table('assumption_changes.csv',[dict(assumption_id=r['assumption_id'],action='ADD_PACKAGE_SCOPED',value=r['value'],approval_status=r['approval_status'],reason=r['basis']) for r in register])

clarifications=[dict(question_id='Q-P00R-001',source=f'{PLAN}:{PP}requirements.csv:R05; R07; R13',
                    quote='Итоговая сеть 8–12 маршрутов',interpretations=['A: целевая проектная сеть конец 2028 в основном сценарии','B: каждый сценарий и этап','C: вся сеть RW'],
                    temporary_recommendation='A',affected_conclusions='Меню кандидатов; статус R05; этапы/ветви дефицита ресурса.',
                    continuing_work='Все минимальные проверки KEEP/units/seats/choice/cash.',status='USER_CONFIRMED',
                    resolution='A; размер меньших этапов и выполнение целевой конфигурации показывать явно.',
                    resolution_source='USER_ROUTE: сообщение координатора в текущем треде 12.11.2026',assumption_id='P00R-M04'),
                dict(question_id='P04-Q001',source='USER_MONEY',quote='полный добавочный операционный результат, отдельно связанные инвестиции/финансирование/налоги',
                    interpretations=['Операционный результат + отдельные инвестиции/налоги/финансирование','Смешение всех денежных статей в profit'],
                    temporary_recommendation='Подтверждённый операционный показатель',affected_conclusions='SP09–SP11; денежный мост; funding_before_financing.',
                    continuing_work='Формализация событий и проверка CE13/CE14.',status='USER_CONFIRMED',
                    resolution='Стоимость использования самолёта и запуска сохраняется; funding_before_financing и financing_cash раздельны.',
                    resolution_source='USER_MONEY: сообщение координатора в текущем треде 12.11.2026',assumption_id='P00R-M05')]
table('clarification_requests.csv',clarifications)

rules={
 'scope':'Предложение для принятия координатором; общие файлы не изменены. Можно использовать и как нормализованные CSV, и как эквивалентные структуры существующего engine.',
 'evaluation_context':{k:'required' for k in patches[0]['required_fields'].split('; ')},
 'demand_conservation':'For each evaluation,pool,month,segment: sum(final product choices incl outside/unserved) = potential demand. If air-only observed demand is used, document mapping to potential demand; do not subtract no-travel twice.',
 'capacity':'For each dated physical flight: sum(carried journeys using leg) + reserved unallocated contractual seats <= saleable seats. Contractual passengers included in carried are not added twice.',
 'revenue':'sum_j carried_j * net_journey_fare_j + separately owned ancillary/contract revenue. One economic event per earned amount; weights to legs sum to 1.',
 'own_migration':'old and new RW products participate in the same choice. Delta is total affected business P minus KEEP. Passenger origin transitions, if not identifiable, remain scenario assumptions; do not infer measured own migration from min(current passengers,new passengers).',
 'resource':'Same availability/commitment scenario for P and KEEP, optional unused resources disclosed. Assignment intervals include turn/position/maintenance/crew restrictions. An aggregate-hours screen alone cannot pass operational feasibility.',
 'operating_result':'net earned revenue + recognized support - variable operating expense - other operating expense (base, aircraft use, startup, exit under chosen policy). Report variable contribution separately. P−KEEP contains donor effects once.',
 'cash_bridge':'cash_before_financing = operating_cash + investing_cash + tax_cash. Financing cash contains equity/debt flows separately. cash_close_t = cash_open_t + cash_before_financing_t + financing_cash_t.',
 'funding_before_financing':'max over t including prelaunch of max(0, minimum_cash_t - opening_unrestricted_cash - sum_{u<=t} cash_before_financing_u). Report horizon, boundary and excluded unknowns. Month-end estimate is a lower bound without event timing/buffer.',
 'two_funding_boundaries':'Incremental project cash = affected P cash - affected KEEP cash. Whole-business cash adds KEEP company cash. Unknown latter implies UNKNOWN whole-company funding, not zero.',
 'terminal':'24 monthly operating outputs 2027–2028 plus prelaunch cash and explicit terminal receivables/payables/refundable deposits/exit commitments beyond horizon. Do not infer profitability or payback date after horizon.',
 'season':'Historical months 2025 and available2026, published W26/27/S27 and projected 24 months remain separate versioned datasets. Every sampling/season extrapolation has coverage and assumption_id.',
 'metric':'Journey, segment, compatible reported passenger are separate. Growth = P−KEEP within metric. Share change = share_P−share_KEEP, with compatible period/scope/denominator. No inferred №2 date.',
 'optimization':'Compare nondominated growth/funding/risk options when budget unknown. Keep prior feasible candidates with unchanged feasibility. Global optimum only with appropriate proof; heuristic is best-found. Adaptive changes respect information available at decision_date and sunk commitments.',
 'gate':'Research, source collection, UI skeleton, engine implementation proceed now. Before consequential integrated results, instantiate F01–F06 and run corresponding cases in actual P06. F07 gates share/ranking only. Conditional outputs with exact unknowns are allowed.',
 'not_required':['Новый промышленный оптимизатор','Покупка OD базы','Полный ежедневный cash всей компании','Новый повтор всего исторического корпуса','Пользовательское согласование каждого рутинного коэффициента','Ожидание международных расширений для CASE_SJ']
}
dump('contract_addendum.json',rules)
review=dict(package='P00R',version='v1',role='methods_review',model='gpt-6-astra',effort='xhigh',
            reviewed_at=STAMP,reviewed_plan_commit=PLAN,author_baseline_commit=AUTHOR,five_city_commit=FIVE,
            verdict='CHANGES',verdict_scope='Операционализация контракта перед содержательным общим расчётом. Принципы постановки приняты, реализация P06 ещё не проверялась.',
            package_status='METHOD_REVIEW_COMPLETE',programme_status='NOT_ASSESSED_NOT_COMPLETE',
            may_proceed=['Сбор и квалификация данных','Каркас UI','Реализация P06 по конкретным схемам и примерам','Условные сценарии и пороги по неизвестным'],
            must_precede_consequential_run=['Принять SP01–SP11/SP13 или эквивалентные структуры с теми же инвариантами','Повторить затронутые CE в P06 на exact SHA; P00R toy PASS не является PASS движка'],
            findings=findings,acceptable_unknowns=unknowns,
            improvements=[dict(id='I01',title='Внутримесячные выплаты',severity='nonblocking_for_labelled_monthly_estimate',action='CE18; показывать нижнюю границу или даты крупных выплат/резерв.'),
                          dict(id='I02',title='Область теста монотонности',severity='nonblocking_contract_clarification',action='CE19; сравнивать при неизменных costs/obligations и разрешённом unused resource.'),
                          dict(id='I03',title='Методическая карта',severity='nonblocking',action='Добавить к M01–M06 связи SP/CE и отдельный M07 cash bridge (IAS7 + USER_MONEY); источники дают методы, не российские коэффициенты.')],
            independence=dict(authored_packages_in_current_task=['P00R'],plan_required_must_not_be_author_of=[],
                              source=f'{PLAN}:{PP}work_packages.json:P00R.independence',
                              did_not_author_reviewed_plan_or_legacy_models_in_this_task=True,
                              limitations='Личное авторство прошлых анонимных agent сессий не устанавливалось; нет заявлений о независимой проверке собственного P06.'),
            used_assumption_ids=[x['assumption_id'] for x in register],
            historical_assumptions_referenced_not_adopted=['NET-capture_freq_scale','NET-capture_open','NET-capture_competitive','NET-competitor_lf','NET-rw_existing_lf','NET-weeks_per_year','NET-market_pax_2025','NET-fuel_compensation_rub_per_t','OPEN-BASE_SETUP','OPEN-LEASE','OPEN-SJ100_TRANSFER'],
            source_read_boundary='Новые web чтения пяти методических источников из source_lock и одного IAS7; локальные источники только git show закреплённых SHA. Новые данные маршрутов/тарифов/парка не собирались.',
            not_run=['Полная сеть','Повтор 652 исторических сетей','Текущие пакеты P02/P03/P04/P05/P06/P09','Рыночная калибровка','Реальная эксплуатационная проверка','Достаточность полного финансирования RW','UI/браузерная проверка'],
            exact_next_requests=[dict(owner='P00/coordinator',request='Принять либо адресно скорректировать SP01–SP13; закрепить входы и confirmations без нового круга общего планирования.'),
                                 dict(owner='P03',request='Датированный available/committed/reserve ресурс и конкретные прежние задания/альтернативы.'),
                                 dict(owner='P04',request='События начислений/платежей, операционная конвенция стоимости ВС, депозиты/поддержка/налоги/финансирование и unknown поля.'),
                                 dict(owner='P05',request='Demand pool/basis, продуктовый выбор, сезонное покрытие и диапазоны/пороги без ложной калибровки.'),
                                 dict(owner='P06',request='Реализовать инварианты; предоставить exact SHA+manifest и результаты адресных CE. Не импортировать toy значения как параметры RW.'),
                                 dict(owner='P10',request='Совместимая отчётная единица перевозок и знаменатель/конкурентный порог №2.')])
dump('method_review.json',review)

inputs=[]
for sha, paths in [(PLAN,[PP+x for x in ['common_spec.json','requirements.csv','method_map.csv','source_lock.json','work_packages.json','assumptions_register.csv','reuse_map.csv']]+['context/00_brief/case5_requirements.md']),
                   (AUTHOR,['src/network_model.py','data/assumptions/network.csv']),
                   (FIVE,['context/33_five_city_reassessment_20261112/common_economics/report.md'])]:
    for p in paths:
        b=blob(sha,p)
        inputs.append(dict(commit=sha,path=p,git_blob=subprocess.check_output(['git','rev-parse',sha+':'+p],cwd=ROOT,text=True).strip(),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),use='pinned review evidence'))
dump('input_manifest.json',dict(version=1,inputs=inputs,source_registry='sources.csv',
                              external_source_hash_policy='Web tool text inspected; raw HTTP bodies not archived or hash-claimed. URLs, access date, granularity and precise applicability retained.',
                              producer_packages_received=[],live_branches_used_as_inputs=False))
print(json.dumps(dict(cases=len(cases),findings=len(findings),patches=len(patches),assumptions=len(register),inputs=len(inputs)),ensure_ascii=False))
