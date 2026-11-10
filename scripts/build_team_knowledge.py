#!/usr/bin/env python3
"""Build the editorial data packet from pinned, reviewed local inputs; no network."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'context/14_synthesis'
I = B / 'inputs'


def read_json(path):
    return json.loads(path.read_text())


def rows(path, numbers=False):
    result = list(csv.DictReader(path.read_text().splitlines()))
    if numbers:
        for row in result:
            for key, value in row.items():
                try:
                    row[key] = float(value) if '.' in value or 'e' in value.lower() else int(value)
                except (ValueError, TypeError):
                    pass
    return result


audits = {p.parent.name: read_json(p) for p in (B / 'contributions').glob('*/findings.json')}
assert set(audits) == {'kiruha', 'city_screening', 'network_economics', 'existing_context', 'user_network_report'}
economic_inputs = read_json(I / 'inputs.json')
screening_inputs = read_json(I / 'screening_inputs.json')
network = rows(I / 'network_comparison.csv', True)
base = {r['network']: r for r in network if r['scenario'] == 'base'}
delta = base['A']['contribution_before_base_and_fleet'] - base['B0']['contribution_before_base_and_fleet']
thresholds = [r for r in rows(I / 'capture_transfer_thresholds.csv', True)
              if r['scenario'] == 'base' and r['reference'] == 'best_direct']
for row in thresholds:
    row.pop('max_transfer_pax', None)  # Endpoint is not a proven maximum; see NE-02.

data_needs = [
    ('OD-спрос', 'направленные A→B × месяц/дата × цель', 'Наблюдаемых рядов нет; сценарии 31 пары', 'RW, аэропорты, разрешённые агрегаты продаж; покрытие MIDT проверять', 'Конечная поездка не равна сегменту или аэропортовому потоку'),
    ('Календарь', 'рейс × дата × направление × перевозчик', 'Датированные строки есть; UNKNOWN сохранены', 'Первичные расписания аэропортов/перевозчиков', 'IANA-пояс + местная дата → UTC; обе стороны и период действия'),
    ('Цена', 'предложение × дата поиска × дата поездки × багаж', '18 рекламных минимумов; сопоставимой панели нет', 'Одинаковые даты, багаж и сборы на сайтах перевозчиков', 'Цена от не средняя полученная выручка'),
    ('Население', 'город/ОКТМО/зона тяготения × год', 'Городские числа есть; зона тяготения не построена', 'Росстат/БДМО; Точно как каталог с проверкой версии', 'Город не агломерация; согласовать границы и год'),
    ('Доход и занятость', 'территория × месяц/год × показатель', 'Сопоставимой панели нет', 'Росстат/ЕМИСС с проверенным паспортом', 'Региональный доход не платёжеспособность каждого пассажира'),
    ('Деловые и вахтовые связи', 'работодатель/отрасль × OD × график', 'Гипотезы без подтверждённых блоков мест', 'Региональные данные и разрешённые агрегаты работодателей', 'Ночной вылет не доказательство вахты; учитывать асимметрию'),
    ('Социальные связи', 'миграция/студенты/возраст × территория × период', 'Кандидаты признаков; модель не оценена', 'Росстат/муниципальные/образовательные агрегаты', 'Признак связи не количество авиапоездок'),
    ('Туризм', 'размещения/ночёвки × месяц × территория', 'Сопоставимой помесячной панели нет', 'Росстат, официальные региональные органы', 'Размещения не уникальные туристы; отделять местных и способ прибытия'),
    ('Наземная альтернатива', 'OD × дата × вид транспорта', 'Есть зацепки, нет полной матрицы', 'РЖД/ФПК/автобусы; Точно intercity_connectivity как прокси', 'Дверь–дверь, багаж, ожидание, пересадки и возврат; средняя скорость не расписание'),
    ('Аэропорт и ТО', 'аэропорт × работа/тип × дата действия', 'Часть допусков и публичных цен проверена', 'Операторы аэропортов и сертифицированные организации ТО', 'Допуск не свободная мощность и не договорная цена'),
    ('Парк/экипажи', 'борт × дата × обязательства/ТО/позиция', 'Опубликованный состав есть; свободный ресурс неизвестен', 'RW и эксплуатационные данные', 'Разделить рабочие борта/резерв/недоступность; не вычитать простой дважды'),
    ('Поддержка/финансы', 'маршрут/база × договор × период', 'Есть ориентиры, будущая поддержка неизвестна', 'Действующее решение и договор, предложения аэропортов', 'Общий бюджет не ставка каждой линии; учитывать cash flow и выход'),
    ('Сбои/погода', 'рейс/аэропорт × время × событие', 'Есть сценарии, ряд сбоев не откалиброван', 'Операционные агрегаты/погода с датой и покрытием', 'ADS-B не число пассажиров; пропуск не нулевая задержка'),
]

hypothesis_groups = [
    ('Сеть', 'Новый узел, прямые из нынешних баз, мини-волна, цепочки, смешанная сеть, прямые сейчас/хаб позже.', 'Одинаково определить парк и деньги, но не добавлять рейсы только ради равного налёта; новая база экипажей меняет смысл Б.', ['K057','K058','K059','K060','K066']),
    ('Поездка и спрос', 'Неудобство конкурента, наземная альтернатива, индуцированные поездки, вахта, социальные связи и сезонность.', 'Для каждого OD нужны даты, цена, цель и проверяемый объём; ночной вылет/население/рост туризма не являются продажами.', ['K028','K054','K055','K063','K065','K075']),
    ('Метод выбора', 'Аналоги/гравитация, QSI/logit, частота, spill, outside option.', 'Калибровка и ёмкость; не усреднять несовместимые оценки и не выдавать условный share за факт.', ['K024','K025','K051','K063']),
    ('Города', 'Зона тяготения, конкуренты, география, условия базы, техническая пригодность и устойчивость рейтинга.', 'Жёсткий запрет не компенсируется баллами, пропуск не ноль, техническая изученность не готовность.', ['K061','K070']),
    ('Деньги', 'Внутренний переток, замена старых рейсов, тариф/затраты, база, субсидии и условия выхода.', 'Чистый прирост всей RW, одна выручка за поездку; относительное преимущество не прибыль.', ['K062','K066','K074','K082']),
    ('Эксплуатация', 'Реальный доступный парк, ТО, дальность, часы, резерв, сбои и открытие аэропортов.', 'Побортовые цепочки; опубликованный состав не ресурс; карта по прямой не разрешение на полёт.', ['K038','K041','K042','K048','K049','K056','K068']),
    ('Партнёрский продукт', 'Защищённые/самостоятельные пересадки, автобус, турпакет/круиз, лояльность, корпоративные блоки.', 'Договор, багаж и ответственность; цена пакета не доход авиакомпании.', ['K008','K011','K055','K067']),
    ('Развитие парка и международная опция', 'Ту высвобождает SSJ; SJ-100 поэтапно; внутренний фидер международных линий и B777 отдельно.', 'Иные ресурсы, допуски/права и условия, без обещаний поставки и автоматической экономии.', ['K023','K046','K047','K064']),
    ('Риск, измерение и дополнительные эффекты', 'Пилот/ликвидность, исторические неудачи, доля и два счётчика, экология.', 'Не объявлять причинность по каталогу провалов; не оптимизировать бумажные сегменты; CO₂ зависит от расхода/загрузки.', ['K032','K036','K052','K053','K080']),
]

packet = {
    'schema': 'case5_team_knowledge_v1', 'as_of': '2026-11-09',
    'status': 'PARENT_CURATED_EVIDENCE_AND_EXPLICIT_SCENARIOS',
    'precedence': ['analysis.md', 'knowledge.json', 'contributions reports with their statuses', 'pinned artifacts'],
    'requirements': {'source': 'https://mai-way.ru/tasks/red-wings/', 'rechecked': '2026-11-09',
                     'submission': '10 ноября 2026, 23:59 (отдельно часовой пояс не указан)', 'defence': '13 ноября 2026',
                     'passport_pages': '1–2', 'cities_min': 10, 'top': 3, 'regional_competitors_min': 2,
                     'scenarios': ['base','cautious'], 'selected_network_routes': '8–12', 'slides':'5–8', 'speech_minutes_max':5,
                     'roadmap_to':2028, 'status':'STRATEGY_NOT_SELECTED; NOT_SUBMITTED'},
    'fleet_snapshot': {'source':'https://flyredwings.com/about/park/', 'checked':'2026-11-09',
                       'status':'WEBSITE_COMPOSITION_NOT_AVAILABLE_FLEET', 'types':[
                           {'type':'SSJ100','count':20,'seats':100}, {'type':'Ту-214','count':3,'seats':194},
                           {'type':'Ту-204-100B','count':2,'seats':210}, {'type':'B777-200ER','count':3,'seats':412}],
                       'sum':28, 'free_project_aircraft':None},
    'leadership': {'name':'Роман Чуев','announced':'2026-10-30','source':'https://flyredwings.com/press/news/roman-chuev-stal-generalnym-direktorom-red-wings/'},
    'hypothesis_groups': [dict(zip(['theme','ideas','decision_test','kiruha_audit_refs'], x)) for x in hypothesis_groups],
    'screening_hypotheses': audits['city_screening']['hypotheses'],
    'existing_hypothesis_cards': audits['existing_context']['hypothesis_cards'],
    'kiruha_ideas_and_checks': [{k:x.get(k) for k in ['id','category','disposition','status','title','assessment','provenance','source_urls']}
                              for x in audits['kiruha']['findings']],
    'data_needs': [dict(zip(['topic','grain','availability','candidate_source','transformation_or_limit'], x)) for x in data_needs],
    'cities': rows(I/'screening_city_matrix.csv'),
    'city_population_scope': 'City proper 2025-01-01, secondary; not agglomeration/catchment',
    'city_weights': screening_inputs['weights'],
    'ranking_updated': rows(I/'city_ranking_update_full.csv', True),
    'ranking_sensitivity': rows(I/'city_ranking_update.csv', True),
    'city_data_inventory': rows(I/'city_data_inventory.csv'),
    'city_overrides': {'UFA':'RRJ-95 admission confirmed in stage12; free MRO/base terms unknown',
                       'CEK':'2166689 includes 6268 transit; 2160421 excludes transit',
                       'KUF_KZN':'Excluded only under NEW_SUPPORT_NODE analytical rule; support airport does not prove physical base',
                       'intervals':'Do not use historic non-base ranking intervals; they erroneously repeat base-weight bounds'},
    'competitors': read_json(ROOT/'context/13_competitors/competitors.json'),
    'network_definitions': {
        'A': {'name':'Новый хаб GOJ','hub':'GOJ','spokes':['OMS','KUF','MMK','UFA','AER','VOG','ARH','MRV'], 'departures_each_direction_week':6,'working_aircraft_scenario':4},
        'B0': {'name':'Прямые из существующих баз','triangles':[['ZIA','ARH','MRV','ZIA'],['ZIA','GSV','AER','ZIA'],['SVX','OMS','KUF','SVX'],['SVX','NJC','VOG','SVX']], 'departures_each_direction_week':3,'working_aircraft_scenario':4},
        'B': {'name':'Б0 с усилениями','extra_roundtrips_week':{'GSV-AER':4,'SVX-OMS':6}, 'working_aircraft_scenario':4,'operational_status':'4 days exceed selected 10 block-hour rule'}},
    'model_scope': {'week':economic_inputs['model_week'], 'source_commit':'91fdbe10e4454c94a20aeca6db38ffc68633ea48',
                    'seats':100,'status':'SCENARIO_NOT_FORECAST', 'excluded_costs':['new hub/base','fixed fleet financing/leasing','full central overhead'],
                    'base_action':'Add flights to existing RW; substitution needs another scenario', 'annualisation':'52 identical weeks is annual-equivalent, never annual forecast'},
    'model_inputs':economic_inputs, 'network_results':network, 'block_times':rows(I/'block_times.csv'),
    'competition':rows(I/'competition.csv'), 'operational_stress':rows(I/'operational_stress.csv'),
    'rotations_reassigned':rows(I/'hub_reassignment.csv'),
    'relative_thresholds': {'weekly_A_minus_B0_base_rub':delta,'annual_equivalent_base_cost_for_equality_rub':delta*52,
                            'capture_fixed_OD':thresholds, 'warning':'Relative equality between negative alternatives, not breakeven; max_transfer omitted'},
    'real_csv_examples':[x for x in read_json(I/'manifest.json') if x.get('sample_rows')],
    'qsi_example':{'status':'SYNTHETIC_UNCALIBRATED','direct_frequency':4,'transit_frequency':14,'direct_hours':2.5,'transit_hours':6.5,
                   'beta':2,'stop_coefficient':0.3,'q_direct':27.04,'q_transit':4.2,'share_direct':27.04/(27.04+4.2),'weekly_direct_capacity':400},
    'spill_example':{'status':'SYNTHETIC','demand_states':[40,120],'probabilities':[.5,.5],'mean_demand':80,
                     'capacity100':{'mean_carried':70,'mean_spill':10,'load':.7},'capacity180':{'mean_carried':80,'mean_spill':0,'load':80/180},'profit':None},
    'prior_decisions':rows(ROOT/'context/10_decision_guide/decisions.csv'),
    'prior_tasks':rows(ROOT/'context/10_decision_guide/tasks.csv'),
    'supplementary_proposals':audits['existing_context']['supplementary_proposals'],
    'full_audits':{k:f'contributions/{k}/report.md' for k in sorted(audits)},
    'source_manifest':'inputs/manifest.json', 'inventory':'inventory.json',
    'limits':['No accepted common strategy or named assignees','Some branch-local decisions exist; common approval not established',
              'Published schedule is planned supply, not sales','No complete economic/social/demographic catchment panel',
              'Do not double count Aeroflot group','No profitability claim from relative score']}

assert len(packet['cities']) == 10 and len(network) == 6
assert abs(delta - 2787555.3715588823) < .001
assert all('max_transfer_pax' not in x for x in thresholds)
(B/'knowledge.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n')
print(f'Built knowledge.json: {len(audits)} audited bundles, 10 cities, 6 scenarios, 13 data groups.')
