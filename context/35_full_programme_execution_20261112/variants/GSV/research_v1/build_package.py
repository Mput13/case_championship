"""Сборка локального Stage A GSV. Запись ограничена каталогом этого файла; Git только read-only."""
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent
ASOF = '2026-11-12'
PINS = {
    'author': 'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',
    'five_city': 'c18f7640ea36647a05b39089e5293f22dd009f63',
    'plan': 'b4d2ddf690440eb5cd051839cc263cf16b364ca4',
    'P00R': 'b7d74e67dd6c603db049b1915b1afec987e3b458',
    'P02': 'd9486f113f074c185a94bcc5c0afeef12ea3574f',
    'P03': '79dc698b99dfe866886d32376ed388e85bdd039c',
    'P04': '620a0ac4bb11763319c4227485f6a3996b91d367',
    'P06': '982f13d9b6c378ed9581125ecc5c40f17dade6a3',
}

def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(b):
    return hashlib.sha256(b).hexdigest()

def write_json(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def write_csv(name, rows):
    assert rows, name
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (ROOT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def git(sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path])

receipts = {x['source_id']: x for x in json.loads((ROOT / 'fetch_receipts.json').read_text())}
source_pins = json.loads((ROOT / 'source_pins.json').read_text())
rows = json.loads((ROOT / 'pinned_gsv_rows.json').read_text())

def pin_control(key, path):
    b = git(PINS[key], path)
    rec = dict(pin_id='PIN-' + key + '-' + Path(path).stem, commit=PINS[key], path=path,
               git_blob=subprocess.check_output(['git', 'rev-parse', PINS[key] + ':' + path], text=True).strip(),
               sha256=digest(b), retention='Только pin; полный чужой файл не копируется')
    global source_pins
    source_pins = [x for x in source_pins if x['pin_id'] != rec['pin_id']] + [rec]
    return json.loads(b) if path.endswith('.json') else b.decode('utf-8-sig')

contract = pin_control('P06', 'context/35_full_programme_execution_20261112/P06/producer_contract.json')
rules = pin_control('P03', 'context/35_full_programme_execution_20261112/P03/operating_rules.json')
pin_control('P00R', 'context/35_full_programme_execution_20261112/P00R/contract_addendum.json')
plan = pin_control('plan', 'context/34_full_programme_plan_20261112/variant_research_plan.json')
pin_control('P04', 'context/35_full_programme_execution_20261112/P04/event_rate_map.csv')
pin_control('P03', 'context/35_full_programme_execution_20261112/P03/aircraft_type_parameters.csv')
p02sources = pin_control('P02', 'context/35_full_programme_execution_20261112/P02/sources.json')

# Координаты - только пункты реально предложенных опытов, с указанием исходных строк.
coordpath = 'data/processed/catchments.csv'
b = git(PINS['author'], coordpath)
cr = list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
needed = {'GSV', 'SVX', 'TJM', 'MRV', 'MCX', 'KUF', 'KZN', 'VOG', 'NUX', 'SGC', 'OVB', 'AER', 'GOJ', 'PEE', 'OMS', 'KGD'}
coords = []
for i, r in enumerate(cr, 1):
    if r['iata'] in needed:
        coords.append(dict(source_row_ordinal=i, row=r, canonical_row_sha256=digest(canon(r))))
write_json('coordinate_rows.json', dict(commit=PINS['author'], path=coordpath, source_file_sha256=digest(b), rows=coords))
cd = {x['row']['iata']: (float(x['row']['latitude_deg']), float(x['row']['longitude_deg'])) for x in coords}

def distance(a, b):
    a1, o1 = map(math.radians, cd[a]); a2, o2 = map(math.radians, cd[b])
    h = math.sin((a2-a1)/2)**2 + math.cos(a1)*math.cos(a2)*math.sin((o2-o1)/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))

geo = []
for b in sorted(needed - {'GSV'}):
    if b not in cd: continue
    geo.append(dict(origin='GSV', destination=b, value=round(distance('GSV', b), 1), unit='km_great_circle', period='геометрия; координаты pinned 2026-11-11',
                    status='DERIVED_NOT_FLIGHT_PLAN', coverage='Центры аэропортов; без трасс, закрытий, ветра, нагрузки', source_id='PIN-dceadc98-catchments', assumption_id='A-GSV-GEO'))
write_csv('geometry.csv', geo)

# Полные строки конкретного расписания, а не наличие пункта в выпадающем списке.
class TimetableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.inrow=False; self.incell=False; self.cells=[]; self.current=''; self.rows=[]; self.city=None; self.rownum=0
    def handle_starttag(self, tag, attrs):
        if tag=='tr': self.inrow=True; self.cells=[]; self.rownum += 1
        if tag=='td' and self.inrow: self.incell=True; self.current=''
    def handle_data(self, s):
        if self.incell: self.current += ' ' + s
    def handle_endtag(self, tag):
        if tag=='td' and self.incell: self.cells.append(' '.join(self.current.split())); self.incell=False
        if tag=='tr' and self.inrow:
            if len(self.cells)==1: self.city=self.cells[0]
            elif len(self.cells)==8: self.rows.append((self.rownum, self.city, self.cells.copy()))
            self.inrow=False

new_schedule=[]
for sid, direction in [('GSV-TIMETABLE', 'outbound'), ('GSV-TIMETABLE-DECJAN', 'outbound'), ('GSV-ARR-DECJAN', 'inbound')]:
    parser=TimetableParser(); parser.feed((ROOT / receipts[sid]['local_path']).read_text())
    for ordinal, city, cells in parser.rows:
        dep,arr,week,period,carrier,flight,aircraft,iata=cells
        rec=dict(observation_id=f'{sid}-TR{ordinal:03}', source_id=sid, source_url=receipts[sid]['requested_url'], source_sha256=receipts[sid]['sha256'],
                 source_row_id=f'HTML tr {ordinal}', source_row_sha256=digest(canon(cells)), origin='GSV' if direction=='outbound' else iata,
                 destination=iata if direction=='outbound' else 'GSV', city_label=city, departure_local=dep, arrival_local=arr, weekdays=week,
                 period=period, year_status='Год в строке не указан; год окна в URL/hidden input и объявление TBS согласованы', carrier=carrier,
                 flight=flight, aircraft=aircraft, unit='published_schedule_rule; local_clock', status='PUBLISHED_NOT_SEATS_OR_TAIL_BINDING',
                 coverage='Только выбранное окно и направление; не полная история', open_seats='UNKNOWN', fare_RUB='UNKNOWN', baggage='UNKNOWN', booking_lead_days='NOT_A_FARE_QUOTE')
        new_schedule.append(rec)
write_csv('schedule_observations.csv', new_schedule)

evidence=[]
def ev(eid, sid, claim, value=None, unit='качественный факт', period='снимок 2026-11-12', status='PUBLISHED_PRIMARY', coverage='GSV; локальный первичный источник', limit='', locator='Основной текст страницы'):
    r=receipts.get(sid)
    ps=next((p for p in source_pins if p['pin_id']==sid), None)
    evidence.append(dict(evidence_id=eid, source_id=sid, organisation='АО «СарАэро-Инвест» / УК «Аэропорты Регионов»' if r and sid.startswith('GSV-') and sid not in {'GSV-MK2025','GSV-RAILSVX','GSV-AVV-NEWS','GSV-AVVBUS'} else 'См. источник и происхождение pinned таблицы',
                         url=r['requested_url'] if r else ('git:'+ps['commit']+':'+ps['path'] if ps else 'см. source_pins.json'),
                         retrieved_at=r['retrieved_at'] if r else ASOF, publication_date={'GSV-TBS':'2026-11-09','GSV-BUS':'2026-06-09; текст называет первый рейс 10 июня','GSV-NUX2025':'2025-05-05','GSV-PAX2025':'2026-02-04','GSV-H12026':'2026-07-15','GSV-SUMMER2026':'2026-03-24','GSV-WINTER':'2026-10-21','GSV-IST2025':'2025-05-23','GSV-MK2025':'2026-02-12','GSV-AVV-NEWS':'2026-10-31','GSV-DISCOUNTS-2026':'утверждено 2026-07-13; введено 2026-08-01'}.get(sid,'UNKNOWN; указана дата снимка/версии'),
                         period=period, unit=unit, granularity=coverage, value='UNKNOWN' if value is None else value, status=status, coverage=coverage,
                         claim=claim, limitation=limit, source_locator=locator, source_sha256=r['sha256'] if r else (ps['sha256'] if ps else 'см. source_pins.json')))

ev('E-GSV-01','GSV-PAX2025','За 2025 год аэропорт обслужил 1 064 000 пассажиров, сеть включала 14 направлений.',1064000,'airport_passenger_events/year','2025-01/2025-12',limit='Аэропортовый итог прилёт+вылет; не число уникальных поездок, не RW, не OD и не будущий рынок.')
ev('E-GSV-02','GSV-H12026','За первое полугодие 2026 обслужено более 490 тысяч пассажиров; доступны 11 направлений.','>490000','airport_passenger_events/half_year','2026-01/2026-06',limit='Нельзя умножать на два или сравнивать с годовым итогом как темп роста.')
ev('E-GSV-03','GSV-H12026','Международный поток первого полугодия превысил 22 тысячи; источник сообщает рост в 1,4 раза к тому же периоду 2025.','>22000; ratio 1.4','airport_international_passenger_events; ratio','H1 2026 vs H1 2025',limit='Направления Анталья/Ереван/Батуми/Хургада; разбивки по маршрутам, перевозчикам и целям нет.')
ev('E-GSV-04','GSV-MK2025','По ответу областного Минтранса изданию, международный поток 2025 составил 44,6 тыс., Ереван — 12,1 тыс.','44600;12100','airport_route_passenger_events/year','2025',status='SECONDARY_REPORT_OF_MINISTRY_REPLY',coverage='Аэропорт/международный агрегат и маршрут GSV–EVN',limit='Оригинал ответа не получен; не загрузка Shirak и не прогноз TBS. Использовать как контекст с более слабым происхождением.')
ev('E-GSV-05','GSV-SUMMER2026','Летом опубликованы GSV–Москва, LED, AER, SVX, MCX, OVB, KGD, KZN, SGC; отдельные зарубежные и чартерные программы.',13,'published_destinations','2026-03-29/2026-10-24',limit='Это предложение аэропорта, не полётные факты и не фактический спрос.')
ev('E-GSV-06','GSV-SUMMER2026','В летнем объявлении Москва — до 7 рейсов в день; DP LED до 2 в день; AER с июня ежедневно.','7/day;2/day;1/day','published_frequency','summer 2026',limit='Максимумы и сезонные правила, аэропорты Москвы различаются: SVO и VKO; частоты не суммировать с зимними строками.')
ev('E-GSV-07','GSV-WINTER','На зиму опубликованы 10 направлений и 9 перевозчиков; Москва до 5 в день, DP LED ежедневно и AER до 4 в неделю.','10;9;5/day;1/day;4/week','published_offer','объявление от 2026-10-21',limit='В тексте ошибочно стоит конец 27.03.2026 после начала 25.10.2026. Исходную ошибку сохраняем; вывод о сезоне 2026/27 сверяем по датированным строкам, не исправляем источник молча.')
ev('E-GSV-08','GSV-TBS','RW объявила GSV–TBS с 23 декабря по средам на SSJ100; продажи объявлены открытыми.',1,'roundtrips/week','с 2026-12-23; конечный срок объявления UNKNOWN',limit='Продажи объявлены; фактическая цена, доступное кресло, единый билет и сквозной багаж не проверены.')
ev('E-GSV-09','GSV-BUS','Первичный источник сообщает о начале RW GSV–BUS в июне 2026, раз в неделю по средам на SSJ100.','1/week;150min','roundtrips/week;flight_minutes','summer 2026',limit='Дата публикации 9 июня, текст говорит «сегодня, 10 июня». Разницу не скрываем; точный день события требует журнала. Не переносим на зиму или 2027/28.')
ev('E-GSV-10','GSV-NUX2025','RW начала GSV–NUX 3 мая 2025; в весенне-летней программе до двух раз в неделю, среда и суббота, SSJ100.',2,'up_to_roundtrips/week','spring/summer 2025',limit='История эксплуатации, без объёма, загрузки, корпоративного договора и подтверждения непрерывности в 2026.')
ev('E-GSV-11','GSV-IST2025','На лето 2025 ИрАэро объявила GSV–Стамбул раз в неделю на SSJ100, с 25 июня.',1,'roundtrips/week','summer 2025',limit='Аэропорт Стамбула в объявлении не указан; IST нельзя подставлять автоматически. Текущая непрерывность UNKNOWN.')
ev('E-GSV-12','GSV-TECH','Опубликованы ВПП 3000×45 м, PCN 50/R/B/W/T, RRJ-95 в перечне допускаемых типов; работа H24.','3000x45;50/R/B/W/T;H24','m;PCN;hours','снимок 2026-11-12',limit='Не AFM/NOTAM/фактический свободный слот и не допуск SJ100/ПД8 по конкретному оператору.')
ev('E-GSV-13','GSV-TECH','Опубликована 21 стоянка.',21,'parking_positions','снимок 2026-11-12',limit='Нет распределения, режима зимнего хранения, свободной ночной стоянки RW и договора базы.')
ev('E-GSV-14','GSV-TERMINAL-CORRECT','Терминал: 23 054 м², опубликованная пропускная способность 1 млн в год, 3 телетрапа, 9 выходов, 13 стоек регистрации.','23054;1000000;3;9;13','m2;passenger_events/year;equipment_counts','снимок 2026-11-12',limit='Справочная годовая мощность ниже фактического итога 2025; не доказывает ни невозможность развития, ни запас мощности для одновременного банка. Нужны почасовые потоки.')
ev('E-GSV-15','GSV-FUEL','Аэропорт указывает одного топливозаправочного оператора — Газпромнефть-Аэро, филиал «Энгельс», участок «Саратов».',1,'published_fuel_operator','снимок 2026-11-12',limit='Цена топлива, гарантированная поставка, условия RW и резервная логистика UNKNOWN.')
ev('E-GSV-16','GSV-SLOTS-CORRECT','Запросы на рейсы/изменения направляются координатору; при отсутствии договора действует публичная оферта.','порядок согласования','airport_process','снимок 2026-11-12',limit='Публичная оферта не предоставляет слот, overnight базу, лимит кредита или готовые экипажи.')
ev('E-GSV-17','GSV-CONTACTS','Опубликованы контакты планирования, перронного обслуживания и заключения SGHA.','поставщики функций','airport_process','снимок 2026-11-12',limit='Наземное обслуживание и осмотр при приёме/выпуске не равны сертифицированному ТО RRJ95 и тем более SJ100/ПД8. Договор и доступная мощность RW UNKNOWN.')
ev('E-GSV-18','GSV-SUPPORT','Аэропорт предлагает участие в планировании и поддержку новых направлений.','возможный источник переговорных данных','airport_support_offer','снимок 2026-11-12',limit='Ни спрос аэропорта, ни скидка, ни риск-шэринг RW договором не подтверждены.')
ev('E-GSV-19','GSV-DISCOUNTS-2026','Фактический PDF утверждён 13.07.2026 и введён с 01.08.2026; подпись ссылки на странице называет другую дату.','2026-08-01','effective_date','2026-08-01/дальнейшая версия UNKNOWN',limit='Для обычных скидок нужны SGHA, дополнительное соглашение, определённая закупка услуг и отсутствие просроченного долга; не переносить в 2027/28 автоматически.',locator='PDF стр.2,7–8,13; пп.2.3–2.4,4.1–4.4')
ev('E-GSV-20','GSV-TARIFF-20261101','Опубликованный набор базовых сборов GSV извлечён в local_cost_drivers.csv.','см. local_cost_drivers.csv','RUB_2026_exVAT/physical_driver','версия с 2026-11-01',limit='Только справочная часть расходов; нужны применимость, MTOW, биллинг, льготы и будущая индексация. Не складывать стоянку I.3 и услугу II.17 без проверки договора.',locator='PDF стр.1–3,5,9,11,14')
ev('E-GSV-21','GSV-TARIFF-20261116','На 12 ноября уже опубликована отдельная версия с изменениями с 16 ноября.','2026-11-16','future_effective_date','с 2026-11-16',limit='Не подменяет действующие ставки 12 ноября. Не ставка 2027/28.')
ev('E-GSV-22','GSV-TARIFF-20261101','Услуга оформления посадочного талона на второй/последующий сегмент стоит 64,03 руб. без НДС; льгота 100% в текущем документе заканчивается 31.12.2026.',64.03,'RUB_2026_exVAT/boarding_pass','тариф с 2026-06-06; льгота до 2026-12-31',limit='Не 100% скидка на рейс. Для 2027 неизвестно продление; транзитный тариф также не равен тарифу пересадки автоматически.',locator='PDF стр.8 п.37.17 и стр.14 п.2.3')
ev('E-GSV-23','GSV-GROUND-BUS','Аэропорт публикует автобус 101Э: 80 минут, 114,40 руб.; пригородный экспресс: 46 минут, 115 руб.','80;114.4;46;115','minutes;RUB_advertised','снимок 2026-11-12',limit='Нужны дата, подход к платформе и ожидание. Это не полный door-to-door; речную навигацию не переносим на зиму.')
ev('E-GSV-24','GSV-AVV-NEWS','Перевозчик с 1 ноября публикует автобус 101Э из автовокзала с 06:45 до 21:10; из аэропорта с 08:40 до 23:20.','окна 06:45–21:10 / 08:40–23:20','local_clock','с 2026-11-01',coverage='АО «Саратовское объединение автовокзалов и автостанций»; маршрут 101Э',limit='Ранний прилёт и ночной рейс требуют проверки такси/персонала/подвоза. Нет оснований считать доступность всего региона одинаковой.')
ev('E-GSV-25','GSV-RAILSVX','Открытая расписательная страница показывает поезд Саратов–Екатеринбург от примерно 30 часов.','~30h minimum','published_rail_elapsed_hours','снимок 2026-11-12',status='SECONDARY_PUBLIC_SCHEDULE',coverage='Яндекс Расписания; станция-станция, не аэропорт-аэропорт',limit='Не замер реальной поездки и не билет на заданную дату с сопоставимой корзиной; используется как сигнал различия модальностей, не как точный выбор P05.')
ev('E-GSV-26','PIN-dceadc98-catchments','Авторский catchment содержит население 1 126 789 для GSV.',1126789,'census_population_proxy','ВПН-2021 / модель на dceadc98',status='PINNED_AUTHOR_PROXY',coverage='GSV catchment; авторский способ объединения',limit='Это население, не авиационный спрос. Не прогноз 2028, не число платежеспособных клиентов; общий catchment с соседними аэропортами не удваивать.')
ev('E-GSV-27','PIN-dceadc98-primary_seasonality_profiles','Сохранённый профиль EMISS62073 по Саратовской области за 2025: сумма 676 856; лето 47,09%, декабрь–февраль 15,13%; пик июль.','676856;0.470886;0.151341','regional_accommodation_profile;shares','2025',status='PINNED_DERIVED_CONTEXT_NOT_OD',coverage='Саратовская область; региональный ряд коллективного размещения, выбранные строки',limit='Без распределения происхождения/авиационной доли. Не переносить профиль на GSV–NUX, TBS или все OD. В 2026 полный год в pinned профиле UNKNOWN.')
ev('E-GSV-28','PIN-d9486f11-city_coverage','P02 для GSV: 31 обязательный исходящий рынок, 10 частично освещены, 21 не покрыт.','31;10;21','outbound_market_counts','P02v2 2026-11-12',status='PINNED_COVERAGE_NOT_CAPACITY',coverage='Конечный список P02, не все возможные рынки',limit='Uncovered не означает отсутствие рейса, конкурента или спроса. TBS и NUX исследованы отдельно, за пределами исходного покрытия.')
ev('E-GSV-29','PIN-dceadc98-rw_routes_now','В авторском входе SVX–GSV стоит 145 годовых круговых рейсов /52 =2,79 как усреднение плана субсидий.','145;2.79','planned_roundtrips/year;derived_average/week','2026 subsidy plan',status='PINNED_PLAN_NOT_EXECUTED_CALENDAR',coverage='Один маршрут; исходная логическая строка 32',limit='2,79 нельзя сделать каждой неделей или считать фактической частотой. Датированные расписания и будущая поддержка проверяются отдельно.')
ev('E-GSV-30','GSV-ARR-DECJAN','В среду с 23 декабря опубликован SVX–GSV WZ5047 07:50→08:45, RRJ95LR; TBS–GSV WZ1752 15:05→17:30.','08:45;17:30','local_arrival_clock','2026-12-23/2027-03-24',limit='Год в строках частично выведен из окна и согласован с объявлением. Номер/тип не доказывает идентичность борта.')
ev('E-GSV-31','GSV-TIMETABLE-DECJAN','В том же окне GSV–TBS WZ1751 11:40→14:15; GSV–SVX WZ5048 20:10→23:10.','11:40;20:10','local_departure_clock','2026-12-23/2027-03-24',limit='Опубликованная календарная совместимость, не наличие protected itinerary и не допуск инвентаря.')
ev('E-GSV-32','GSV-TIMETABLE','Название NUX в селекторе расписания не сопровождается строкой рейса в выбранном окне.','UNKNOWN current NUX offer','coverage_result','2026-11-12/2026-12-12',status='COVERAGE_GAP_NOT_NO_SERVICE',limit='Селектор не рейс; отсутствие строки в окне не экономическое опровержение северного рынка.')
write_csv('evidence.csv', evidence)

# Выводы из четырёх согласованных времён: отдельно от tail/crew acceptance.
clock_check = dict(status='DATED_CLOCK_DIAGNOSTIC_ONLY', source_ids=['GSV-ARR-DECJAN','GSV-TIMETABLE-DECJAN','GSV-TBS'],
    period='Wednesdays 2026-12-23/2027-03-24', assumption_ids=['A-GSV-CLOCK','A-GSV-CREW','A-GSV-SALE'],
    outbound_connection_min=175, inbound_connection_min=160,
    proposed_same_tail_sequence=['SVX>GSV','GSV>TBS','TBS>GSV','GSV>SVX'],
    scheduled_block_min=[115,155,145,120], total_scheduled_block_min=535,
    local_timezone_offsets={'SVX':5,'GSV':4,'TBS':4},
    same_tail_elapsed_span_min=920, turn_at_TBS_min=50,
    ordinary_single_uninterrupted_crew_duty_limit_4_landings_min=630,
    ordinary_single_crew_diagnostic='920 > 630 даже до pre/postflight; одна обычная непрерывная смена не подходит',
    crew_conclusion='Нужны раздельные смены/ротации и проверка отдыха по P03. Это не утверждение нарушения реального расписания: экипажи и tail не наблюдались.',
    physical_continuity='UNKNOWN', commercial_protection='UNKNOWN', inventory='UNKNOWN', legal_MCT='UNKNOWN',
    comparison_with_prior_clock='Прежнее прибытие в среду 19:30 нельзя совмещать с новым TBS11:40: даты действия различаются.')
write_json('corridor_clock_check.json', clock_check)

assumptions=[]
def ass(i, item, value, why, impact, refine, bounds='UNKNOWN', owner='Исследователь GSV; подтверждает соответствующий P03/P04/P05'):
    assumptions.append(dict(assumption_id=i, item=item, chosen_value=value, unit='см. параметр', period='2027-01/2028-12, если не указан иной', status='SCENARIO_OR_UNKNOWN_NOT_CONFIDENCE_INTERVAL', coverage='GSV и затронутые рынки', source_id='evidence.csv; source_pins.json', owner=owner, rationale=why, justified_range_or_UNKNOWN=bounds, impact_sensitivity=impact, how_to_refine=refine))
ass('A-GSV-GEO','Геометрия','R=6371.0088 km; haversine','Стандартная средняя сфера; координаты закреплены в авторской таблице.','Геометрия не заменяет трассу, дальность с полезной нагрузкой и коммерческую пригодность.','P03: реальные трассы и полётные задания.','Детерминированная формула, не сценарный диапазон')
ass('A-GSV-CLOCK','Часы и календарь','SVX UTC+5; GSV/TBS UTC+4; окно Dec2026–Mar2027','Местные часы источника; объявление TBS и датированный запрос согласованы.','Замена старой строки среды новым окном меняет допустимость стыковки.','P02/P03: датированный двунаправленный календарь, timezone и day-offset каждого рейса.','Только выбранные даты; без автоматического продолжения')
ass('A-GSV-SALE','Сквозная продажа и багаж','UNKNOWN','Совпадение часов и общий перевозчик не доказывают единый билет и защиту.','Если KEEP уже продаёт такой продукт, нельзя приписать весь трансферный поток проекту; если не продаёт — нужны цена и затраты защиты.','P05: чтение конкретного shopping результата без платежа, правила/багаж/MCT/квоты/дата/lead.')
ass('A-GSV-CREW','Экипажи и ТО','UNKNOWN; для 4 плеч не предполагается одна непрерывная обычная смена','Расчётный span 15h20 превышает обычный предел P03 для 4 посадок.','Потребность в дополнительных сменах/отдыхе/подвозе может снять выгоду однобортной цепочки.','P03: crew IDs, report/release/rest, ground/positioning, программа ТО и договоры.')
ass('A-GSV-FREQ','Частоты кандидатов','SVX add2/w; radial3+2+2 RT/w; bank4/w на4спицах; NUX2/w; TBS/BUS add1/w','3 рейса Пн/Ср/Пт дают интервалы 2/2/3 дня; 2 Пн/Чт или Вт/Сб — 3/4 ночи. Это дизайн проверяемого продукта с историческим опытом 1–2/w, а не рассчитанный оптимум.','P05 должен проверить 2/3/4/w и изменение спроса из-за расписания; высокая частота без спроса не улучшение.','Календарь целей поездок, ежедневный OD и выбор P05; частоту разрешено уменьшить.','Опытные варианты2/3/4; эмпирический оптимум UNKNOWN')
ass('A-GSV-SEASON','Сезоны','core все месяцы; дополнительные NUX/BUS/TBS сезоны как варианты, не прогноз','История NUX весна-лето, BUS лето, TBS старт зимой; общего коэффициента сезонности нет.','Проверять зиму, лето и межсезонье раздельно.','P05 месяцы/направления/цели, полётная история и продажи.','UNKNOWN; параметры сезонных частот не доверительные интервалы')
ass('A-GSV-RESOURCE','Доступный самолёт','UNKNOWN; проектные запросы1 или2 рабочих хвоста; резерв отдельно','Это группы запрашиваемого ресурса, не свободный RW парк и не доказанная достаточность.','Резерв, ввод, ТО, crew и KEEP могут сделать кандидат недоступным; не делить один tail между несовместимыми программами.','P03: ready_by_tail_date, reserve, donor/alternative, delivery phased/partial/delay/no_new.','UNKNOWN')
ass('A-GSV-TYPES','Типы','RRJ95B и RRJ95LR отдельно; SJ100_PD8 отдельная ветвь','Публичный допуск и прошлые RRJ95 операции не удостоверяют будущий SJ100/ПД8.','Не переносить кресла/топливо/MTOW/стоимость/надёжность без чувствительности; новый SJ не ранее H2 2027 плюс ввод.','P03: AFM/payload-range, конкретные борта, регистрация/допуски, запчасти/двигатель; P04 rates.','UNKNOWN для будущего RW')
ass('A-GSV-BASE','База, слоты, ночная стоянка','UNKNOWN','21 общая стоянка и H24 не равны базе RW.','Добавочные fixed/start/exit и восстановление после AOG могут изменить сравнение базы с outstation.','P03/P04: SGHA/base agreement, night stand, смены, инструменты, MRO, crew rooms и termination terms.')
ass('A-GSV-COST-MAP','Местные ставки','11 базовых строк + дополнительные строки local_cost_drivers.csv','Референс 01.11.2026 безНДС; сохраняется physical driver и область биллинга.','Полный добавочный результат требует всех P04 drivers; fuel и future escalator UNKNOWN; не начислять дважды услуги и общую стоянку.','P04: тип/MTOW, quantity/event binding, future contract, скидки, НДС и cash terms.')
ass('A-GSV-DISCOUNT','Скидки','UNKNOWN entitlement; показано условие без дисконтирования как контроль','Реальное положение 01.08.2026 требует SGHA/допсоглашения и иных условий; ссылка содержит старую дату.','Победа, возникающая только после неподтверждённой скидки, условна; boarding-pass waiver кончается2026.','P04: договор RW, eligibility, дата начала/конца, счёт/акт/применимый пул и подтверждение отсутствия задолженности.','UNKNOWN; отсутствие льготы — сценарий, не факт о RW')
ass('A-GSV-DEMAND','OD, тариф, контракт','UNKNOWN; исторические 200/600 и прочие author OD не приняты','Сценарии авторов не измеренный платёжеспособный спрос; airport events и население не OD.','Без общей P05 калибровки денежный победитель/доля рынка/окупаемость UNKNOWN.','P05: O&D month/direction, realised fares и retail baskets, purpose/stay, собственный переток.','UNKNOWN')
ass('A-GSV-RESPONSE','Ответ конкурентов','UNKNOWN magnitude; preserve/price-response/frequency-response ветви','У DP/S7/UT/5G опубликован ресурс действующих продуктов, но свободный tail и эластичность неизвестны.','Сохранять ограничения ресурса конкурента; не предполагать снижение цены или увеличение частоты бесплатно.','P02/P05: наблюдавшиеся датированные ответы, свободные окна и единый choice response policy.')
ass('A-GSV-GROUND','Catchment и подвоз','80min автобус/46min поезд как опубликованные звенья; door-to-door UNKNOWN','Это подтверждённые компоненты, ожидание, первая/последняя миля и соседние аэропорты не измерены.','На коротких GSV–KUF/VOG/GOJ наземная альтернатива может доминировать; не автоматический отсев500km.','P02/P05: поезд/автобус/авто по датам и границам catchment, стоимость и полное время.')
ass('A-GSV-KEEP','Сохранение своих продаж','Все затронутые будущие обязательства/продажи KEEP сохраняются либо меняются явно','Нынешние SVX и анонс TBS, история BUS/NUX не означают ни обязательное продолжение, ни нулевые продажи.','Упущенная выручка и displaced local/connecting должны входить в delta к тому же будущему миру.','P03 KEEP inventory; P05 свои OD/yield/booking; P04 avoidability/commitments.')
ass('A-GSV-BANK','Окно пересадки','C=max(airport/airline MCT, accepted buffer); значение UNKNOWN','Для нового внутреннего банка нет права перенести 175/160 минут наблюдаемого коридора как норматив.','Изменяет часы, число tail/crews, вытеснение местных и надёжность.','P03/P05: MCT, багаж, пропускная способность по часам и disruption policy.')
ass('A-GSV-CALENDAR','Месячная техническая мощность','Счёт датированных дней недели по каждому месяцу; не52 недели','2028 високосный; все 24 месяца считаются явно. Числа показывают только потенциальное число рейсов шаблона.','Числа не годовой прогноз: реальные даты готовности/ввод/сезон/слоты/ТО ещё не применены.','P03 применяет календарь ready_by_tail_date и сохранённые KEEP назначения.')
write_csv('assumptions.csv', assumptions)

common=dict(period_start='2027-01-01', period_end='2028-12-31', status='STAGE_A_CONSTRUCTED_STAGE_B_CONDITIONAL',
            new_Tu214_count=0,
            units='roundtrips/week per airport_pair; physical tails; journey OD separate from flown segments',
            aircraft_branches=['RRJ95B_SaM146','RRJ95LR_SaM146','SJ100_PD8_separate_ready_gate'],
            keep_policy='Будущий KEEP + тот же ресурс/внешний сценарий. Не удалять собственную сеть, TBS/BUS/NUX проверять по сезону/дате. При переносе старого борта нужен donor с потерянными продажами; у нового — лучшая доступная альтернатива.',
            reserve_policy='Совместимый резерв закрепляет P03; запрошенные1/2 рабочих tail не содержат бесплатный резерв. Группа поддержки может потребовать дополнительные tail, crews и деньги.',
            delivery_branches=['phased','partial','delayed','no_new'],
            no_new_branch='Новые SJ не выделяются. Варианты на действующем RRJ требуют доказанного высвобождения; оптимизация уже опубликованных продуктов/подвоза остаётся проверяемой без обещания лишнего tail.',
            operational_acceptance='UNKNOWN: нет принятого полного датированного tail/crew/MRO/KEEP bundle',
            finance_acceptance='NOT_RUN: нет общей P05 калибровки и принятого P04 полного будущего cost/cash binding',
            required_common_inputs=['P02 датированные продаваемые альтернативы и багаж','P03 fleet/crew/MRO/KEEP/датированные блоки','P05 единый OD/choice/response','P04 event_rate_map+cash и местные уточнения','P06 принятие полноты/сравнение с KEEP'])

def route(a,b,n,days,change='ADD',season='core_12_months', role='local_OD'):
    return dict(origin=a,destination=b,roundtrips_week=n,weekdays_iso=days,change=change,season=season,market_role=role,source_id='evidence.csv; programme design',assumption_ids=['A-GSV-FREQ','A-GSV-SEASON','A-GSV-KEEP'])
def programme(pid, title, hypotheses, resource, routes, sequences, why, compare, **extra):
    d=dict(common,programme_id=pid,title=title,hypothesis_ids=hypotheses,resource_request=resource,routes=routes,rotation_templates=sequences,mechanism=why,counterfactual_ids=compare,**extra)
    return d

programmes=[]
programmes.append(programme('PG-GSV-00','Сквозной продукт SVX–GSV–TBS на опубликованном коридоре',['H-GSV-01'],
    dict(incremental_working_tails=0,meaning='Ноль дополнительных бортов только в изолированном опыте изменения продукта на тех же уже назначенных рейсах; существующие tail/crews не бесплатны и ещё не связаны.',physical_group='Привязать реальную группу SVX/KEEP; при отсутствии назначения потребность UNKNOWN',reserve='из общего KEEP, договор и доступность UNKNOWN'),
    [route('SVX','GSV',1,[3],'KEEP_PUBLISHED_CORRIDOR','winter_published_only'),route('GSV','TBS',1,[3],'KEEP_PUBLISHED_CORRIDOR','winter_published_only')],
    [['SVX','GSV','TBS','GSV','SVX']],
    'Отдельно проверить, продаётся ли уже единая поездка; затем сравнить защиту/багаж/тариф при тех же физически назначенных четырёх плечах. Не приписывать весь существующий поток новому проекту.',
    ['KEEP-same-published-flights','PG-GSV-06'],
    affected_OD=['SVX>TBS','TBS>SVX','SVX>GSV','GSV>SVX','GSV>TBS','TBS>GSV'],
    price_policy='P05: один gross/net fare на конечную поездку, два кресла; локальные продажи на обоих плечах конкурируют за тот же inventory.',
    clock_evidence='corridor_clock_check.json; только Dec23–Mar24. Реальные даты2027/28 получить отдельно.',
    seasons={'winter':'первый продуктовый опыт на опубликованном коридоре, не продолжение в2028 по умолчанию','summer':'BUS/TBS по подтверждённому KEEP и сезону','shoulder':'неизвестный OD; отдельный спрос, не среднее зимы и лета'},
    assumption_ids=['A-GSV-CLOCK','A-GSV-SALE','A-GSV-CREW','A-GSV-KEEP']))
programmes.append(programme('PG-GSV-01','Дополнительные прямые SVX–GSV из существующего опорного аэропорта',['H-GSV-02'],
    dict(working_tail_allocation_request=1,share_of_compatible_pool='UNKNOWN;2RT/week не означает эксклюзивный tail',base='SVX',sufficiency='UNKNOWN; сохранить другие задания/ТО/резерв'),
    [route('SVX','GSV',2,[1,4])],[['SVX','GSV','SVX']],
    'Пн/Чт добавляют интервалы для поездок2–4ночи к опубликованной ср/пт; будущая итоговая частота только после join KEEP. Проверить пользу частоты и дневного окна без открытия базы GSV.',
    ['PG-GSV-02','KEEP-best-existing-base-use'],affected_OD=['SVX>GSV','GSV>SVX','SVX>TBS via GSV if sellable'],
    own_sales_changes='Сохранять датированные WZ5047/5048 и TBS; эти2RT дополнительные, не замена нынешним2. Годовой план145/52 не исходное расписание.',assumption_ids=['A-GSV-FREQ','A-GSV-RESOURCE','A-GSV-KEEP']))
programmes.append(programme('PG-GSV-02','Один рабочий борт в радиальной базе GSV',['H-GSV-02'],
    dict(working_tail_allocation_request=1,base='GSV',minimum_physical_tails_lower_bound=1,sufficiency='UNKNOWN; отдельно ввод/crew/ТО/резерв/ночная стоянка; это не свободный действующий RW tail'),
    [route('GSV','SVX',3,[1,3,5]),route('GSV','MRV',2,[2,6]),route('GSV','MCX',2,[4,7])],
    [['GSV','SVX','GSV'],['GSV','MRV','GSV'],['GSV','MCX','GSV']],
    'Проверить локальные восточный и южные рынки на3/2/2частотах и затраты новой базы. Каждый день одинRT; свободные часы не названы резервом/ТО автоматически.',
    ['PG-GSV-01','KEEP-best-one-tail-existing-base-use'],
    affected_OD=['GSV>SVX','GSV>MRV','GSV>MCX','обратные OD','существующие RW connecting OD с перетоком'],
    own_sales_changes='SVX3/w — добавочная частота. KEEP сохраняется отдельным ресурсом; если P03 переносит действующие рейсы на этот tail, это отдельная версия с released donor и вычитаемыми обязательствами.',
    seasonal_alternative='Летом проверить замену части MCX2/w на AER2/w против DP daily; это взаимоисключающий опыт на том же tail, не суммируемая выручка.',assumption_ids=['A-GSV-FREQ','A-GSV-RESOURCE','A-GSV-BASE','A-GSV-DEMAND']))
bankroutes=[route('GSV',b,4,[1,2,4,5],role='local_and_transfer') for b in ['SVX','TJM','MRV','MCX']]
bankseq=[dict(tail_slot='T1',days=[1,4],path=['GSV','SVX','GSV','MRV','GSV']),dict(tail_slot='T2',days=[1,4],path=['GSV','TJM','GSV','MCX','GSV']),
         dict(tail_slot='T1',days=[2,5],path=['GSV','MRV','GSV','SVX','GSV']),dict(tail_slot='T2',days=[2,5],path=['GSV','MCX','GSV','TJM','GSV'])]
programmes.append(programme('PG-GSV-03','Внутренний пересадочный банк GSV',['H-GSV-03'],
    dict(working_tail_allocation_request=2,base='GSV',sufficiency='UNKNOWN;2 одновременные ротации, резерв/смены/ТО отдельно'),bankroutes,bankseq,
    'Проверить смесь местных и восток–юг OD; обратное направление банка на следующий день. Один и тот же рейс и кресло нельзя продавать независимо локально и транзитом.',
    ['PG-GSV-03U','PG-GSV-04'],
    affected_OD=['GSV<->SVX/TJM/MRV/MCX','SVX<->MRV/MCX','TJM<->MRV/MCX'],
    clock_design={'hub_arrival_bank_B':'переменная оптимизации по слотам','outbound_bank':'B+C','C':'max(подтверждённыйMCT, принятыйбуфер);UNKNOWN','aircraft_edges':'Для каждого tail связать первый outbound, возврат кB, следующий вылетB+C, возврат и overnight. Реальные block/turn/P03 обязательны.'},
    stress='Закрытие GSV срывает все4спицы; рассчитать коррелированные потери пересадок, возвраты, размещение, запасные аэропорты и cash. Kover publication days не часы простоя.',
    assumption_ids=['A-GSV-BANK','A-GSV-FREQ','A-GSV-RESOURCE','A-GSV-BASE','A-GSV-RESPONSE']))
programmes.append(programme('PG-GSV-03U','Контроль банка: те же рейсы GSV без защищённых стыковок',['H-GSV-03'],
    dict(working_tail_allocation_request=2,base='GSV',sufficiency='Такое же ограничение, как PG-GSV-03; дополнительных бесплатных tail нет'),bankroutes,bankseq,
    'С теми же flight IDs/capacity/costs сначала выключить только transfer products; затем отдельным опытом разрешить оптимизацию часов под местные OD. Это отделяет вклад защиты и расписания от эффекта количества рейсов.',
    ['PG-GSV-03'],affected_OD=['тот же universe, что PG-GSV-03'],control_rule='Не назначать разные коэффициенты захвата. Capacity и demand pools общие, в каждом evaluation своя allocation.',assumption_ids=['A-GSV-BANK','A-GSV-SALE','A-GSV-DEMAND']))
programmes.append(programme('PG-GSV-04','Два тех же борта в опорном SVX: прямые продукты',['H-GSV-03'],
    dict(working_tail_allocation_request=2,base='SVX',sufficiency='UNKNOWN; та же type/delivery/reserve availability, а не равенство искусственно выбранных block-hours'),
    [route('SVX',b,4,[1,2,4,5]) for b in ['GSV','MRV','MCX','NUX']],
    [['SVX','GSV','SVX','MRV','SVX'],['SVX','MCX','SVX','NUX','SVX']],
    'Альтернативное применение того же нового ресурса в существующем опорном аэропорту. Целевые OD и стоимость базы отличаются; сравнение на объединении рынков с одинаковым outside option и KEEP.',
    ['PG-GSV-03','KEEP-best-two-tail-existing-base-use'],
    affected_OD=['объединение PG-GSV-03 и SVX<->GSV/MRV/MCX/NUX; TJM сохраняется в universe даже если проект его не обслуживает'],
    own_sales_changes='На MRV/MCX/NUX дополнение может перетечь из собственного KEEP: нужен разбор product IDs, не все продажи новые.',
    optimisation_rule='Явный стартовый конкурент, не доказанная лучшая альтернатива: общий solver может улучшить часы/набор маршрутов в том же ресурсе и заранее заданном universe.',
    assumption_ids=['A-GSV-FREQ','A-GSV-RESOURCE','A-GSV-KEEP','A-GSV-DEMAND']))
programmes.append(programme('PG-GSV-05','Северная ротация SVX–GSV–NUX с историей RW',['H-GSV-04'],
    dict(working_tail_allocation_request=1,base='SVX_or_common_pool',sufficiency='UNKNOWN;4 плеча/день требуют block, crew и проверки дальности/нагрузки; база GSV не обязательна'),
    [route('SVX','GSV',2,[2,6],season='spring_summer_probe'),route('GSV','NUX',2,[2,6],season='spring_summer_probe')],[['SVX','GSV','NUX','GSV','SVX']],
    'История запуска RW подтверждает предшествующий продукт. Проверить локальный GSV–NUX, частоту2/w и дополнительные SVX–GSV кресла без придуманного корпоративного блока.',
    ['KEEP-north-current-products','SVX-NUX-direct-same-tail-time','PG-GSV-02'],
    affected_OD=['GSV<->NUX','SVX<->GSV','SVX<->NUX','GSV<->SGC и пересадки как конкурирующие альтернативы'],
    own_sales_changes='Сначала установить, сохранился ли GSV–NUX в будущемKEEP. При сохранении это частота/retime, при отсутствии — восстановление; статус нельзя выбрать по пустому окну таблицы.',
    comparison_rule='Сравнить и с остановкой в GSV, и с прямым SVX–NUX на том же tail/calendar; не приписать два тарифа одной сквозной поездке.',
    seasons={'spring_summer':'2/w как исторически наблюдавшийся дизайн','winter':'отдельная UNKNOWN-demand ветвь; не годовое продолжение','shoulder':'отдельная проверка целей/длительности поездки'},
    assumption_ids=['A-GSV-FREQ','A-GSV-SEASON','A-GSV-DEMAND','A-GSV-RESOURCE','A-GSV-CREW']))
programmes.append(programme('PG-GSV-06','Дополнительная международная частота с опорой на SVX',['H-GSV-05'],
    dict(working_tail_allocation_request=1,base='SVX',share_of_pool='UNKNOWN;4leg international day',sufficiency='UNKNOWN;extra crew shifts likely needed in candidate, quote/approval pending'),
    [route('SVX','GSV',1,[6]),route('GSV','TBS',1,[6],season='winter_probe'),route('GSV','BUS',1,[6],season='summer_ALTERNATIVE_to_TBS_not_additive')],
    [['SVX','GSV','TBS','GSV','SVX'],['SVX','GSV','BUS','GSV','SVX']],
    'Вторая частота позволяет поездку3–4ночи вместо только7ночей. BUS и TBS — разные OD и сезонные альтернативы использования субботнего окна; будущую разрешённую сеть проверить.',
    ['PG-GSV-00','SVX-TBS_or_BUS-direct-same-resource','KEEP-best-one-tail-existing-base-use'],
    affected_OD=['GSV<->TBS/BUS','SVX<->TBS/BUS','SVX<->GSV','переток с собственных direct и через другие базы'],
    gates=['No-new-Tu214: во всех вариантах0новыхТу214','Действующий RRJ95 или отдельно допущенный SJ100_PD8','international rights/handling/passport and baggage','Защита/retail P05 и полная P04 economics'],
    assumption_ids=['A-GSV-FREQ','A-GSV-SEASON','A-GSV-TYPES','A-GSV-CREW','A-GSV-KEEP']))
programmes.append(programme('PG-GSV-07','Подвоз к GSV и партнёрский продукт без новой авиабазы',['H-GSV-06'],
    dict(incremental_aircraft=0,ground_capacity='UNKNOWN;договор и автомобили не считаются бесплатными'),[],[],
    'Проверить согласованный автобус/электропоезд к выбранным рейсам и единый информационный/багажный процесс. Catchment и авиационный спрос P05 общие; не дублировать жителей Саратова/Энгельса и соседних аэропортов.',
    ['KEEP-current-ground','GSV-KUF_or_VOG-short-air-feeder-if-supported'],
    affected_OD=['ground origins Саратов/Энгельс/область -> GSV -> обслуживаемый airport OD','короткий авиаподвоз GSV–KUF/VOG как отдельный альтернативный опыт'],
    ground_example='Опубликованный101Э от автовокзала06:45 с80min даёт8:05уGSV: к11:40есть215min до вылета до регистрации/прочихпереходов. Это только clock arithmetic, не guaranteed protected connection.',
    commercial_rule='Partner airline/ground block agreement UNKNOWN; не считать партнёрский сегмент собственной RW перевозкой и не начислять чужую выручку.',
    assumption_ids=['A-GSV-GROUND','A-GSV-SALE','A-GSV-DEMAND']))
write_json('programme_candidates.json', dict(version='GSV-StageA-v1', programmes=programmes,
    combination_policy='Кандидаты — альтернативные allocations/продуктовые опыты. Не складывать их пассажиров/деньги. Совместимость только после общего join tail, dated flight, demand_pool, shared_event и KEEP.',
    target_8_12='GSV даёт части общей сети. Локальные3/4пары не объявлены готовым общим решением8–12; стадийные дефицитные ветви могут иметь меньше.',
    value_of_existing_work='Авторские OD и scenario scores сохранены с provenance в pinned_gsv_rows, но не подменяют новую общую калибровку.'))

hypotheses=[]
def hyp(i, title, signal, sources, mechanism, cf, test, programmes, ancestors, outcome='CONDITIONAL_SPECIFIC_UNKNOWNS', reopen='После получения перечисленных входов Stage B; критерии ниже'):
    hypotheses.append(dict(hypothesis_id=i,title=title,signal=signal,source_ids=sources,mechanism=mechanism,counterfactual=cf,distinguishing_test=test,programme_ids=programmes,ancestorIDs=ancestors,
                           outcome=outcome,outcome_explanation='Stage A исследование и конструирование закончены; экономический исход условен по указанным измерениям, не ранний отсев города.',reconsideration_condition=reopen,
                           period='2027–2028; источники history2025/as_of2026 раздельны',units='конечные поездки, сегменты, датированные кресла, tail, RUB/cash по общему ядру',coverage='GSV и объединение затронутых рынков',assumption_ids=['A-GSV-DEMAND','A-GSV-KEEP','A-GSV-RESOURCE']))
hyp('H-GSV-01','Существующий коридор SVX–GSV–TBS как кандидат защищённого продукта','В согласованном окне четыре RW плеча дают175/160min стыковки; отдельная базаGSV не следует из этого.',
    ['E-GSV-08','E-GSV-30','E-GSV-31'], 'При том же inventory единый продукт может привлечь дополнительные OD; защита создаёт расходы и вытесняет local seats.',
    'Те же рейсы в будущейKEEP с фактическим текущим состоянием сквозной продажи; прямойSVX–TBS на том же ресурсе.',
    'P05 доказывает наличие/отсутствие продажи сейчас, строит gross/net fare once и seat limits на2плечах; P03 проверяетtail/crew; сравнить Δполного результата/cash/долю и spill.', ['PG-GSV-00'], ['P02_NEW_GSV_OUT','P03_SP04_SP07','NEW_GSV_TBS_20261109'])
hyp('H-GSV-02','Радиальная база GSV против дополнительных прямых из SVX','Есть местный аэропортовый поток и опубликованныйSVX, южные направления/сезонность; нет доказанного свободного RW ресурса и договора базы.',
    ['E-GSV-01','E-GSV-05','E-GSV-12','E-GSV-14','E-GSV-28'], 'База позволяет выбирать местные часы и несколько прямых OD, но добавляет fixed/MRO/crew/exit и альтернативную стоимость хвоста.',
    'PG01 и наилучшее доступное применение одного такого же tail в существующем опорном аэропорту; будущийKEEP сохраняется.',
    'На общих P05 рынках сравнить3/2/2radial с direct control, сезоны и отсутствие субсидии/скидки; вывести пороги покрытия базы и финансирование без подгона к плюсу.', ['PG-GSV-01','PG-GSV-02'], ['SEED20_GSV','C29','AUTHOR_SVX_GSV'])
hyp('H-GSV-03','Внутренний банк восток–юг через GSV','GSV географически связывает восточные и южные пункты; есть local markets, но защищённые внутренние пересадки и почасовые мощности не установлены.',
    ['E-GSV-12','E-GSV-14','E-GSV-27','E-GSV-28'], 'Совместные local+transfer могут заполнить одни и те же рейсы; лишний сегмент, ожидание, поломкистыковок и продажи direct создают потери.',
    'Те же4спицы/2tail без transfer products (03U), затем их местная оптимизация; отдельно2tail вSVX с прямыми продуктами(04).',
    'Общий solver на unionOD и P03 ресурсах; посчитать прирост по конечным поездкам, displacedlocal/RWdirect, connection failure cash; один плохой банк не опровергает весь город.', ['PG-GSV-03','PG-GSV-03U','PG-GSV-04'], ['C29','AUTHOR_H_UFA_8_ENDPOINT_GSV','SEED20_GSV'])
hyp('H-GSV-04','Северная программа GSV–NUX без нового хаба','Исторический первичный запускRW03May2025до2/w; текущая непрерывность/контрактUNKNOWN.',
    ['E-GSV-10','E-GSV-32'], 'Прямой локальный продукт и общий SVX-tail могут иметь смысл при платёжеспособном OD; нефтегазовый контракт из географии не следует.',
    'Текущий northKEEP/UTSGC/черезSVO илиOVB/прямойSVX–NUX с тем же tail ресурсом.',
    'Восстановить own2025/2026 monthly sales/yield и будущийKEEP; сравнить черезGSV и прямой с расходом4 vs2плеч, turnaround/crew, без blockcontract; отдельно зима.', ['PG-GSV-05'], ['NEW_RW_GSV_NUX_20250503','SEED20_GSV'])
hyp('H-GSV-05','Вторая недельная частота Грузии как местный и сквозной продукт','RWBUSлетом и TBSзимой подтверждены первичным источником;1/w ограничивает длительность поездки.',
    ['E-GSV-08','E-GSV-09','E-GSV-03','E-GSV-11'], 'Дополнительная суббота открывает3–4ночи и может объединить локальные/сквозные продажи; рынкиBUS/TBSи сезоны разные.',
    'KEEP1/w и дополнительный прямой изSVX на тот же ресурс; не переносить рынокEVN/турпоток наTBS.',
    'P05stay distribution, full quote+bag+lead и собственнаяканнибализация; P03международныйdispatch/допуск/crew; P04полныеcash. Во всех опытах0новыхТу214.', ['PG-GSV-06'], ['NEW_GSV_TBS_20261109','NEW_GSV_BUS_202606','C30'])
hyp('H-GSV-06','Наземный подвоз и партнёр вместо нового короткого авиаплеча','Опубликованы80minbus/46minrail, часы раннего/позднего подвоза ограничены; соседние аэропорты имеют общийcatchment.',
    ['E-GSV-23','E-GSV-24','E-GSV-26'], 'Снижение полного времени/риска доступа к уже имеющимсяGSVрейсам может быть дешевле нового feeder; это нужно измерить.',
    'Текущийподвоз и отдельно короткийавиаfeeder GSV–KUF/VOG с тем жеобщимOD; отсутствиеairserviceнеподтверждено.',
    'Date-specificdoor-to-door, первая/последняямиля, стоимость/договор/потери; partnerpax неRWsegments.500kmнеэкономическийотказ.', ['PG-GSV-07'], ['C29','SEED20_GSV'])
hyp('H-GSV-07','Договорная поддержка аэропорта меняет порог открытия','Естьположение01Aug2026 с направленческимикоэффициентами и условиямискидок; местные ставки доступны.',
    ['E-GSV-18','E-GSV-19','E-GSV-20','E-GSV-22'], 'Скидка уменьшает частьairportbill, но не fuel/aircraft/MRO и не создаётпассажиров; expiredwaiver может увеличить2027unitcost.',
    'Один и тот же принятыйbundle: безскидки vs документально применимаяскидка на конкретные события.',
    'P04применимость, SGHA/актсверки/допсоглашение, billeddrivers/cash; вывести минимальнонужнуюподдержку и проверить правдоподобие; futureUNKNOWN остаётсяусловным.', ['PG-GSV-02','PG-GSV-03','PG-GSV-05','PG-GSV-06'], ['P04_GSV_LOCAL_RATE_NOT_EXTRACTED','NEW_GSV_LOCAL_TARIFF'])
hyp('H-GSV-08','GSV нельзя назвать подтверждённой существующей базой/хабом RW','Источники показываютобслуживаемыйаэропорт и маршруты; ни21стоянка,ниH24,ниSSJдопускнеподтверждаютбазирование.',
    ['E-GSV-12','E-GSV-13','E-GSV-17','E-GSV-30','E-GSV-31'], 'Корректнаяклассификация предотвращаетбесплатныестоянки/crew/ТО и ошибочноесравнение с новойбазой.',
    'Проверяемаямодельoutstation/throughstop; рольбазы как новыйпредлагаемыйпроект.',
    'Получитьдоговорбазирования/официальноезаявление/постоянныеночёвкиtail+crew+MRO. Доэтого статуссуществующейбазыUNKNOWN,аэкономикагородаостаётсяоткрытой.', [], ['P03_GSV_airport_constraints','SEED20_GSV'], outcome='CURRENT_ROLE_PARTIALLY_ESTABLISHED', reopen='Документы/наблюдения о базировании и постоянном ресурсе; классификация не экономический отказ GSV.')
write_json('hypotheses.json',dict(version='GSV-StageA-v1',hypotheses=hypotheses,registry_policy='Все8локальных гипотез имеют исход и условие проверки. Ни конкуренция, ни500km, ниUNKNOWNне обозначены экономическим отказом.'))

# Дельты - действия на конкретных рынках, с отделением исходного предложения от принятого будущего KEEP.
deltas=[]
def delta(pid, a, b, action, freq, source, coverage, own, season='2027–2028;сезоны по кандидату', notes=''):
    deltas.append(dict(delta_id=f'MD-GSV-{len(deltas)+1:03}',programme_id=pid,origin=a,destination=b,action=action,proposed_incremental_roundtrips_week=freq,unit='roundtrips/week;OD journeys separate',period=season,source_id=source,status='PROPOSED_CONDITIONAL_NOT_ADMITTED',coverage=coverage,baseline_future_KEEP='UNKNOWN;bind P03/P05 same-period',own_sales_treatment=own,notes=notes))
delta('PG-GSV-00','SVX','TBS','ADD_OR_RETAIN_THROUGH_PRODUCT_ON_EXISTING_LEGS','0 extra flights','E-GSV-30;E-GSV-31','ДатированныеSVX–GSVиGSV–TBS;currentprotectionUNKNOWN','LocalSVX–GSV/GSV–TBSпродаютсявтомжеinventory','winter_published2026/27;future refresh','Не добавлять рейсSVX–TBSкак физическоеплечо; тариф один/двасегмента.')
delta('PG-GSV-01','SVX','GSV','ADD',2,'E-GSV-29;E-GSV-30','СуществуютpublishedWed/Fri;годовойпланнефактическийкалендарь','СохранитьKEEP;lostdonorеслипереноситсястарыйtail')
for b,n in [('SVX',3),('MRV',2),('MCX',2)]:delta('PG-GSV-02','GSV',b,'ADD',n,'E-GSV-05;E-GSV-28','Местныерынки;MCXлетнийpublished,MRVcurrentofferUNKNOWN','KEEPнеобнуляется;наSVXэтоещё3RT,еслинеоформленаотдельнаяконсолидация')
for b in ['SVX','TJM','MRV','MCX']:delta('PG-GSV-03','GSV',b,'ADD_AND_BANK',4,'E-GSV-12;E-GSV-28','TJM/MRVdirectcoverageUNKNOWN;конкурентычерезSVO/OVB/SVXнеобнулены','СохранитьKEEPиучестьпотерисобственныхdirect/connectingOD')
for b in ['SVX','TJM','MRV','MCX']:delta('PG-GSV-03U','GSV',b,'SAME_FLIGHTS_DISABLE_TRANSFERS',4,'PG-GSV-03','Идентичныйdatedinventoryконтроля','В первомопытеотличаютсятолькоtransferproducts;потомотдельноretime')
for b in ['GSV','MRV','MCX','NUX']:delta('PG-GSV-04','SVX',b,'ADD_DIRECT_CONTROL',4,'PG-GSV-04;A-GSV-KEEP','Тотже2tailресурс;currentownfrequenciesUNKNOWN','СобственныепрямыепродажиKEEPисегментысохранить;частьновыхможетбытьперетоком')
delta('PG-GSV-05','GSV','NUX','RESTORE_OR_INCREASE_PENDING_KEEP',2,'E-GSV-10;E-GSV-32','История2025до2/w;2026continuityUNKNOWN','Сначалаопределитьдействующиепродажи;неприсваиватьвсеисторическиепассажирыкакновых','spring/summerprobe;winterseparate')
delta('PG-GSV-05','SVX','GSV','ADD_OR_BIND_EXISTING_LEGS',2,'PG-GSV-05','Вт/Сбротация;доказаннойстыковкибортанет','Не складывать с темжеflightIDвPG01/KEEP')
delta('PG-GSV-06','GSV','TBS','ADD_SECOND_WEEKLY',1,'E-GSV-08;E-GSV-31','Текущийанонс1/w;будущийKEEPUNKNOWN','Сохранитьбазовыйрейс;каннибализациюсобственногоSVXTBSвычесть','winterprobe')
delta('PG-GSV-06','GSV','BUS','SEASONAL_ALTERNATIVE_TO_TBS',1,'E-GSV-09','Summerhistory1/w;будущийKEEPUNKNOWN','BUSиTBSнеодновременнаяприбавкавсубботу','summerprobe','СначалапроверитьсобственныебудущиепродажиBUS')
delta('PG-GSV-06','SVX','GSV','ADD_OR_BIND_INTERNATIONAL_FEEDER',1,'PG-GSV-06;E-GSV-30;E-GSV-31','Дополнительное субботнее окно коридора; существующая среда сохраняется','Один физический feeder на весь коридор; не дублировать с PG01/PG05 или KEEP','Вместе с зимним TBS либо летним BUS, по готовности и принятым правам')
delta('PG-GSV-07','Saratov_ground','GSV','GROUND_COORDINATION','0 aircraft','E-GSV-23;E-GSV-24','Подвозкselecteddatedflights;остатокcatchmentUNKNOWN','СамподвознепассажирскийсегментRWи нечужаяавиавыручка')
write_csv('market_deltas.csv',deltas)

requests=[]
def req(i, owner, pids, question, experiment, outputs, sources, gate, priority='P1'):
    requests.append(dict(request_id=i,owner=owner,programme_ids=';'.join(pids),priority=priority,question=question,paired_experiment=experiment,required_outputs=outputs,source_id=sources,unit='см.required_outputs',period='24месяца2027–2028;hist2025/available2026отдельно',coverage='Unionaffectedmarkets;own/competitor/ground',status='STAGE_B_REQUIRED',acceptance_gate=gate))
req('CR-GSV-01','P02/P05',['PG-GSV-00'],'Продаётся ли уже единыйSVX–GSV–TBS с защитой/багажом?','Теже4плеча:реальныйKEEPproductvsноваязащита;необъявлятьсуществующийпродуктновым.','Date+as_of+booking_lead+party+grossfare+netfare+bag+rules+MCT+inventory;physicallegIDs','E-GSV-30;E-GSV-31','Безплатежа;запроспринимаетсятолькокакquote,неbookedcapacity','P0')
req('CR-GSV-02','P03',['PG-GSV-00','PG-GSV-06'],'Можно ли назначитьtail/экипажи на опубликованнуюцепочку?','Существующие4плечаvsпрямойSVX–TBS на тойжеtype/delivery/crewavailability.','Taildatedassignment,535scheduledblockmin/920minspan,crewreport/rest/positioning,50minTBSturn,maintenance/reserve','corridor_clock_check.json;P03operating_rules','Ни4рейсаоднимобычнымcrewниодинаковыйномертипанеозначаютPASS','P0')
req('CR-GSV-03','P03/P05',['PG-GSV-01','PG-GSV-02'],'БазаGSVили дополнительныеSVXdirect?','Одинreadytailсодинаковойподдержкой/reserve:radial3+2+2vsSVXreinforcement+оптимальноеостальноеиспользование.','MonthlyODjourneys/segments/ownspill/revenue/fullsunk&avoidableΔ/cashneed+exit;comparetail-days','E-GSV-05;E-GSV-28;market_deltas.csv','KEEPsales/capacityиальтернативныезаданиясохранены;неравенствоприблизительныхblockhoursнеисправлятьфальшивымресурсом')
req('CR-GSV-04','P05/P06',['PG-GSV-03','PG-GSV-03U','PG-GSV-04'],'Есть лиценностьвнутреннегобанкапослевытесненияdirect/local?','03vs03U:тежеflightsandcostsвыключитьtransfer;потом03vsлучший2tailSVXdirectнаunionOD.','Acceptedchoice/price+baggage;monthlyjourneys/segmentseats/bindinglegs;owncannibalisation;routeandprogrammeeconomics','programme_candidates.json;P06contract','НедублируемOD иместа;одинgross/netfareнаjourney,банкнеавтоматическиймаркетшэр')
req('CR-GSV-05','P02/P05',['PG-GSV-05'],'ЧтоосталосьотGSV–NUXи каковысеверныеOD/тарифы?','ViaGSV4legcircuitvsSVX–NUXdirect;GSVMARKETvsUTSGC/соединенияиground;wintervssummer.','2025/2026monthdirectionpax/realisednetyield/currentoffer/lead+bag;contractstatusUNKNOWNнеблок','E-GSV-10;E-GSV-32','Историческийрейснеизмерениепотока/свободногоконтракта','P0')
req('CR-GSV-06','P05',['PG-GSV-06'],'Втораячастотапривлекаетновыепоездкиилипереезжаетсобственнаявыручка?','1/wKEEPvs2/w;TBSwinterиBUSsummerраздельно;SVXdirectальтернатива.','Monthlystaylength/purpose/pricechoice;incrementalODversusownretention;notshareofairportaggregate','E-GSV-03;E-GSV-04;E-GSV-08;E-GSV-09','EVN/международныйитогнетариф/спросTBS;международныйпассажирнеавтоматическирост№2')
req('CR-GSV-07','P04',['PG-GSV-02','PG-GSV-03','PG-GSV-05','PG-GSV-06'],'ПрименимыеfutureставкиGSV,база,топливо,ТОизапуск/выход?','Принятыйprogrammebundle:безскидкиvsподтверждённыедоговоры;SJ_PD8отдельноотRRJ.','eventrates/exVAT/VAT,MTOW,billedpax/transit,oneeventonecharge,fueltonnes,staff,MRO,stands,startup,exit,payment/advance/deposit','local_cost_drivers.csv;E-GSV-15;E-GSV-19;E-GSV-22','Справочникнебудущаяставка;I.3parkingиII.17неудваивать;terminals/paxeligibleнеавтоматическиодинпул','P0')
req('CR-GSV-08','P03/P04',['PG-GSV-02','PG-GSV-03'],'Существуетлипригодныйдоговорбазирования/смен/ТО?','OutstationпоSGHAvsночнаябаза;2tailbankvs1tailradial.','AirportapprovalRRJ/SJ_PD8,Part145scope/provider/slots,nightstands,tools/spares,AOG,crewtransfer/rooms,termination','E-GSV-12;E-GSV-13;E-GSV-14;E-GSV-16;E-GSV-17','НаличиеприёмаRRJи21стоянкинепринимаетbaseaccess')
req('CR-GSV-09','P03/P05/P06',['PG-GSV-03'],'Почасоваявместимостьитерминальныепроцедурыбанка?','Bankedvsunbanked;stressодновременных2RRJиexistingSU/DPflights.','Gate/bus/check-in/security/bagflows,MCT,slotletter,misconnect,disruption/recoverycash','E-GSV-14;E-GSV-16','Опубликованный1млнcapacityнеостатокслотов;реальный2025итог1064тыснеподтверждаетbankcapacity')
req('CR-GSV-10','P02/P05',['PG-GSV-01','PG-GSV-02','PG-GSV-03','PG-GSV-05'],'Сопоставимыеконкуренты/цены/багаж/реакция?','DP/SU/5G/S7/UTpublishedholdvsдоказаннаяprice/frequencyresponse;MRV/MCX/TJM/NUXuncoveredзаполнить.','Датированныйair+throughstop+single-ticketconnections+groundpanel;operatingcarrier;physicaladjacentlegs;fare/bag/lead','schedule_observations.csv;PIN-d9486f11-competitor_products','Нефиктивныекреслаизэкспортированныхстрок;ответимеетресурс,ценуиоснование')
req('CR-GSV-11','P02/P05/P04',['PG-GSV-07'],'Подвоз/соседниеаэропортыулучшаютполноевремя?','CurrentgroundvsкоординацияподGSV;отдельныйairfeederKUF/VOGприподтвержденииOD.','Door-to-door/date/first-last-mile/price/contract+netincrementalairjourneys;overlapcatchment','E-GSV-23;E-GSV-24;geometry.csv','Неумножатьнаселениенапроизвольныйcapture;500kmнеотсев')
req('CR-GSV-12','P03/P06',['PG-GSV-01','PG-GSV-02','PG-GSV-03','PG-GSV-04','PG-GSV-05','PG-GSV-06'],'Какменяютсядоступностьиёмкостьпо24месяцам?','Phased/partial/delayed/no_newSJ;везде0newTu214;existingRRJreleasedvsnewallocationотдельно.','Readybytaildate,acceptedKEEP,induction/crew/MRO/reserve,datedflightmonths,same-fleetcomparisons','monthly_design_footprint.csv;A-GSV-CALENDAR;P03operating_rules','Шаблонныечисларейсовнеannualforecast;доH22027новыйSJнепринимается')
req('CR-GSV-13','P04/P05/P06',['PG-GSV-02','PG-GSV-03','PG-GSV-05','PG-GSV-06'],'Какаяэкономическаяграницаменяетрешение?','CommonODnetfare/cost/fleet/responsegridsсверх/нижеbreakeven;некалиброватьспросподплюс.','Variablecontribution/fullincrementalresult/monthlycash/prelaunchandexit/fundinguntilprofit;stateknown/scenario/UNKNOWN','P04drivers;P06contract','ПорогΔ netrevenue >= additionalcost+ownlostcontribution+alternativeuse;одновременнориск/cashconstraints.ДатаокупаемостиUNKNOWNеслинеткорня.')
write_csv('comparison_requests.csv',requests)

# Календарный размер шаблонов: ни одного коэффициента annualisation52.
footprint=[]
for prog in programmes:
    for year in [2027,2028]:
        for month in range(1,13):
            start=dt.date(year,month,1); end=dt.date(year+int(month==12),month%12+1,1)
            days=[start+dt.timedelta(days=i) for i in range((end-start).days)]
            for route_i,r in enumerate(prog['routes'],1):
                season=r['season']
                active=True
                if season=='spring_summer_probe': active=month in range(4,11)
                if season=='winter_probe': active=month in [11,12,1,2,3]
                if season=='winter_published_only': active=month in [11,12,1,2,3]
                if season=='summer_ALTERNATIVE_to_TBS_not_additive': active=month in [4,5,6,7,8,9,10]
                count=sum(d.isoweekday() in r['weekdays_iso'] for d in days) if active else 0
                footprint.append(dict(programme_id=prog['programme_id'],route_index=route_i,origin=r['origin'],destination=r['destination'],month=start.strftime('%Y-%m'),
                    conditional_template_roundtrips=count,conditional_template_oneway_segments=2*count,unit='dated_template_count/month',period=start.strftime('%Y-%m'),
                    status='TECHNICAL_PATTERN_NOT_APPROVED_FLIGHTS',coverage='Полныймесяцшаблона;ready/induction/KEEP/seasonalcalibrationнеприменены',source_id='programme_candidates.json;calendar',
                    assumption_id='A-GSV-CALENDAR;A-GSV-SEASON;A-GSV-RESOURCE',new_SJ_earliest_case_gate='INELIGIBLE_PRE_H2_2027' if year==2027 and month<7 else 'READY_DATE_UNKNOWN',
                    RRJ_released_gate='UNKNOWN_donor_required',admitted_flights='UNKNOWN',season_active=str(active).lower()))
write_csv('monthly_design_footprint.csv', footprint)

case=dict(case_id='GSV-research-v1',airport='GSV',city='Саратов',as_of=ASOF,language='ru',pins=PINS,
    stage_A='COMPLETE_LOCAL_RESEARCH_AND_PROGRAMME_DESIGN',stage_B='REQUIRED_NOT_ECONOMIC_ACCEPTANCE',
    conclusion='По доступным источникам GSV — обслуживаемый RW аэропорт с действующим/анонсированным и историческим маршрутным присутствием. База/хаб, постоянный свободный tail, crew и ТО RW не подтверждены. Наиболее конкретный первый опыт — опубликованный коридор SVX–GSV–TBS; север GSV–NUX имеет реальную историю. Новая радиальная база и внутренний банк остаются отдельными экономическими альтернативами.',
    current_role=dict(confirmed=['published RW service SVX–GSV','announced and dated GSV–TBS','historical GSV–BUS2026','historical GSV–NUX2025'],classification='OUTSTATION_OR_THROUGH_ROUTING_CANDIDATE',
        rw_base='UNKNOWN',rw_hub='UNKNOWN',free_tail='UNKNOWN',rw_base_contract='UNKNOWN',rw_MRO_access='UNKNOWN',protected_transfer='UNKNOWN',status_explanation='Outstation — рабочее описание присутствия; не исключает неизвестное базирование. Коридор — опубликованные часы, не доказанный same-tail/защищённый продукт.'),
    demand=dict(local='Аэропортовый итог2025 1.064млн и catchmentproxy дают масштаб; airport events неOD и неравныприростуRW.',regional='КороткиеGSV–KUF/VOG/GOJиподвозобласти требуютgroundcontrol;неотсеяныпо500km.',
        long_distance='SVX/OVB/SGCpublished;NUXhistoryRW;TJM/OMS/PEEиotherODнеобнуленыиз-заcoveragegap.',international='EVN/BUS/TBSиAYT/HRGраздельно;чартерныйпродуктнестандартныйretail.НетпереносамеждународногоагрегатанаспросTBS.',
        seasonality='Прямойисточниклето/зимапоказываетизменениепредложения;региональныйEMISSпрофильконтекст,неairlineODshape.',segments={'tourism':'Подтверждаютсякурортныенаправления/чартеры,региональныйпрофильразмещения;маршрутныедолитуристовUNKNOWN.','business':'Фактическийкорпоративный/деловойODUNKNOWN;3/4wдизайнпоездокпроверяетсяP05.','family':'ДоляVFR/семейныхпоездокUNKNOWN;EVN/TBSгеографияэтогонедоказывает.','contract':'Ниодногообещанногоблокакресел,договораилиминимальногоплатежаневведено.'}),
    competitors=dict(published_current=['SU/РоссияSVO','DP SVO/VKO/LED/AER','S7 OVB','UT SGC/KZN source-specific rules','Shirak EVN','Nesma HRG','Southwind AYT seasonal'],
        source='P02selectedrows+schedule_observations.csv+summer/winter primary releases',
        connection_products='ЧерезSVO/OVB/SVX иotherhubsтребуютsellabledate-specificпроверки;картаcarrierhubненулевойthroughquote.',
        price='ЕдинственныйP02advertisedSVX–GSVот4000 — promotion/return-linkedsearch,нефинальный20kgquote;непринятвP05какодностороннийnetyield.',
        response='Существующиепродуктыподтверждаютприсутствиересурсаконкурента,носвободныйtail/величинареакцииUNKNOWN.ПрименитьобщийP05responsepolicy.'),
    operations=dict(airport='RRJ95reception/H24/3000x45/21standsопубликованы;SJ_PD8/availablebase/slots/crew/MRO/NOTAMseasonalwindowsUNKNOWN',
        local_gaps=['certified MRO type/engine/site scope and RW contract','night stands and available slots','crew rooms/ground transfer/shift roster','fuel contract and supply resilience','hourly terminal and baggage bank capacity','startup deposits and exit liabilities'],
        local_costs='local_cost_drivers.csv даёт справочныеphysicaldrivers, не totalflightcost.',
        disruption='Сетьбанказависитотодногоаэропорта;точныеNOTAM/длительность/деньгиUNKNOWN.НепереводитьпубликацииКовёрвчасыпростоя.'),
    comparison_priority=['CR-GSV-01/02:коридорссамымточнымвременнымвходом','CR-GSV-05:севернаяисторияRWиcurrentKEEP','CR-GSV-03/04:новаябаза/банкпротивexisting-basealternatives','CR-GSV-07/08/09:localcontractsиcapacityдлялюбогофиналиста'],
    priority_reason='Это порядок информационной готовности и стоимости проверки, не экономический рейтинг/победитель.',
    stopping_and_revisit='Реальныйоперационныйдопуск—gate.Денежно:полнаясопоставимаядельта,финансированиеиобязательствадоexit,непервыйплюс.Порогиприбыльностирассчитатьобщимядром;безOD/ratesдатаокупаемостиUNKNOWN.Еслиодиншаблонплох,перестраиваемчастоты/часывнутриресурса,городнеотбрасываем.',
    national_work_boundary='Поставки/налоги/законы не исследуются повторно: P03/P04 pinned. Maincase SSJ vsSJ_PD8 раздельно;0новыхТу214. ПубличныйSite/панельавторанеизменены;Gitнеизменён.')
write_json('case.json',case)

readiness=dict(package_id='GSV-research-v1',as_of=ASOF,stage_A='COMPLETE',stage_A_scope='Локальныеисточники,рольRW,конкурентноепредложение/пробелы,местнаяэксплуатация/тарифы,8объяснимыхгипотез,9программныхкандидатов/контролей,помесячныйразмершаблоновипарныеStageBзапросы',
    stage_B='REQUIRED',economic_winner='UNKNOWN',paid_OD_calibration='NOT_AVAILABLE_FROM_PINNED_INPUTS',full_aircraft_schedule='NOT_ACCEPTED',crew_MRO_reserve='UNKNOWN',free_RW_fleet='UNKNOWN',
    actual_current_fare_baskets='NOT_OBSERVED;невыдаютсяза0',physical_competitor_seats='NOT_ADMITTED',P06_run='NOT_RUN;producer_contractпрочитан,полногоbundleнет',
    independent_acceptance='NOT_RUN',future_KEEP='BIND_REQUIRED',annual_market_share='NOT_CALCULATED',profitability_date='UNKNOWN',
    completed_independent_of_P05=['Местныеprimarysources/history','Датированныеcorridorclockchecks','Airporttechиlocaltariffdrivers','Гипотезы/программыиальтернативныеallocations','Sourcesrowhashesиoutputmanifest'],
    not_done_and_not_rejected=['Live20kgfarequotesпоwinter/summer/shoulderиownretailthroughprotection','Accepted2027/28ODchoicecalibration','Fulltail/crew/MRO/KEEP/calendaradmission','Datedbase/fuel/discount/start/exitcontracts','P06полнаяeconomics/cash/commoncomparison'],
    blockers_are_not_city_rejection=True,write_boundary=str(ROOT),external_effects='Толькооткрытыйsearch/HTTPиразрешённыйhandoffкоординатору;сообщенийтретьимлицам/брони/платежей/перезапусковнет')
write_json('readiness.json',readiness)
write_json('source_pins.json',source_pins)
write_json('handoff.json',dict(package_id='GSV-research-v1',status='STAGE_A_COMPLETE_STAGE_B_REQUIRED',path=str(ROOT),git_operations='READ_ONLY_ONLY;координаторкоммитит',
    entrypoints=['case.json','programme_candidates.json','comparison_requests.csv','readiness.json','output_manifest.json'],
    early_usable_findings=['ОпубликованныйкоридорSVX–GSV–TBSс23Dec;175/160min.Неsame-tail/sellabilityproof.','535minscheduledblock/920minspan:однаобычнаянепрерывнаяcrewсменанеобоснована.','ИсторияRWGSV–NUX2025до2/w;текущаяпрограмма/спросUNKNOWN.','ПроверенныеGSVcostdriversверсии01Nov;future16Novотдельно;скидкисусловиями иwaiverдо31Dec2026.'],
    source_of_truth='URL+fetch_receipts+source_pins+row IDs/hashes;большиечужиеархивынекопировались',
    integration_contract=['Приниматьпрограммыкаккандидатыдляодногоконтролируемогоопыта,несуммироватьпассажиров/деньги.','СоединитьP02/P03/P05/P04вP06поdatedflight/demandpool/sharedcost/KEEP.','ПервымзакрытьCR01/02/05/07.','НеобъявлятьStageAфинальнойпровереннойэкономикой/решением№2.'],
    finance='Ничегонеподогнанокплюсу;финансовыйпобедитель,инвестициииокупаемостьUNKNOWNдоStageB',
    evidence_boundaries=readiness['not_done_and_not_rejected'],assumption_register='assumptions.csv',manifest='output_manifest.json'))

# Сохраняем источник рекламного тарифа и winter bases только как компактные metadata, без чужого fixture.
write_json('pinned_source_metadata.json', [s for s in p02sources if s.get('source_id') in ['NEW_RW_SALE','NEW_RW_WINTER','NEW_GSV_OUT']])
from polish_package import polish
polish(ROOT)
print(json.dumps(dict(evidence=len(evidence),hypotheses=len(hypotheses),programmes=len(programmes),deltas=len(deltas),comparison_requests=len(requests),assumptions=len(assumptions),schedule_rules=len(new_schedule),monthly_footprints=len(footprint)),ensure_ascii=False))
