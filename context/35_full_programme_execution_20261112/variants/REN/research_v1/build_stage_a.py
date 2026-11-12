"""Локальный пакет REN. Пишет только рядом с этим скриптом; Git только read-only."""
from pathlib import Path
import csv, io, json, hashlib, subprocess, datetime as dt
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
AS_OF = '2026-11-12'
PREFIX = 'context/35_full_programme_execution_20261112/'
PINS = json.loads((ROOT/'input_pins.json').read_text())['pins']
PINS['PLAN'] = 'b4d2ddf690440eb5cd051839cc263cf16b364ca4'

def dump(name, obj):
    (ROOT/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def table(name, rows):
    assert rows, name
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/name).open('w', newline='') as f:
        w=csv.DictWriter(f, fields); w.writeheader(); w.writerows(rows)

def blob(pkg, path):
    b=subprocess.check_output(['git','show',PINS[pkg]+':'+path])
    return b, {'package':pkg,'commit':PINS[pkg], 'path':path,
        'git_blob':subprocess.check_output(['git','rev-parse',PINS[pkg]+':'+path],text=True).strip(),
        'file_sha256':hashlib.sha256(b).hexdigest()}

# Небольшие релевантные срезы с точными строками; без копирования чужих fixtures.
extra_pins=[]
for pkg,path,predicate,output in [
 ('BASE','data/processed/longlist.csv',lambda r:r.get('iata')=='REN','BASE_longlist_REN.subset.json'),
 ('PLAN', 'context/34_full_programme_plan_20261112/city_research_seed.csv',lambda r:r.get('iata')=='REN','PLAN_city_seed_REN.subset.json'),
 ('BASE','data/processed/network_routes.csv',lambda r:r.get('from')=='REN' or r.get('to')=='REN','BASE_network_REN.subset.json')]:
    b,pin=blob(pkg,path); rows=[]
    for n,r in enumerate(csv.DictReader(io.StringIO(b.decode())),2):
        if predicate(r):
            h=hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            rows.append({'source_row_line':n,'source_row_id':f'{path}:{n}', 'source_row_sha256_canonical_json':h,'row':r})
    dump(output,dict(pin,rows=rows)); extra_pins.append(pin)
for pkg,files in {'P00R':['contract_addendum.json'], 'P06':['producer_contract.json','README.md'],
                  'P04':['thresholds.csv','README.md'], 'P03':['README.txt'],
                  'PLAN':['variant_research_plan.json','common_spec.json']}.items():
    for f in files:
        path=(PREFIX+pkg+'/' if pkg!='PLAN' else 'context/34_full_programme_plan_20261112/')+f
        _,pin=blob(pkg,path); extra_pins.append(pin)
dump('additional_input_pins.json',{'pins':PINS,'files':extra_pins,
    'note':'Прочитано через git show; полные общие файлы не копировались. BASE network — авторская модель, не наблюдаемый спрос.'})
# Первый широкий текстовый фильтр зацепил строку GOJ с упоминанием Оренбурга.
bad=ROOT/'BASE_context_11_practical_screening_city_matrix.csv.subset.json'
if bad.exists():bad.unlink()

receipts={r['source_id']:r for r in json.loads((ROOT/'sources/fetch_receipts.json').read_text())}
source_meta={
 'REN-PAX25':('АО Аэропорт Оренбург','2026-01-15','2025','пассажирских обслуживаний; операций; направлений','аэропорт/год','published_history','Итог аэропорта; нет OD, carrier share, уникальных людей и помесячной структуры'),
 'REN-SCHEDULE-OUT':('АО Аэропорт Оренбург','UNKNOWN','ОЗП2026/27; отдельные интервалы таблицы','публикуемый рейс/день недели/локальное время','аэропорт-пара/направление/интервал','published_offer','Сезонные строки исходящих рейсов; year inferred с привязкой к релизу23.10.2026; inventory и исполнение UNKNOWN'),
 'REN-SCHEDULE-IN':('АО Аэропорт Оренбург','UNKNOWN','ОЗП2026/27; отдельные интервалы таблицы','публикуемый рейс/день недели/локальное время','аэропорт-пара/направление/интервал','published_offer','Входящие строки; не доказывают совпадение бортов; +1 и clock conflicts проверять отдельно'),
 'REN-WINTER26':('АО Аэропорт Оренбург','2026-10-23','2026-10-25/2027-03-27','направления; авиакомпании; частоты до N','аэропорт/сезон','published_offer','11 направлений/14 перевозчиков; AER и AYT есть в релизе, но нет строк в сохраненной детальной таблице'),
 'REN-TECH':('АО Аэропорт Оренбург','UNKNOWN','опубликованная карточка; снята12.11.2026','м; PCN; стоянки; часы','аэродром/тип ВС','published_technical_reference','RRJ95 в списке приема; SJ100/ПД8 и доступ RW к мощностям не установлены'),
 'REN-COORD':('АО Аэропорт Оренбург','UNKNOWN','действующая веб-страница на12.11.2026','рабочие дни до полета','запрос на согласование','published_process','Минимальный срок подачи не обещанный слот и не договор RW'),
 'REN-TERMINAL26':('АО Аэропорт Оренбург','2026-09-18','сентябрь2026; международный рост H1 2026','м2; пассажиров/час','терминал/релиз','published_infrastructure','Презентация нового терминала; 1000пасс/час не свободная пиковая мощность и не MCT'),
 'REN-WINTER-PREP':('АО Аэропорт Оренбург','2026-10-16','ОЗП2026/27','готовность оборудования/подготовки','аэропорт/сезон','published_operator_claim','Не статистика отмен и не тарифы противообледенения'),
 'REN-TARIFF26':('АО Аэропорт Оренбург / УК Аэропорты Регионов','UNKNOWN; редакция01.11.2026','reference2026; не ставка2027/28','руб без НДС/натуральный драйвер','услуга/дата редакции','published_reference_approval_header_incomplete','Шапка реквизитов утверждения пустая; часть регулируемых ставок с01.04.2024; нужен договор/инвойс/применимость'),
 'REN-FUEL26':('АО Аэропорт Оренбург','2026-10-30 подпись','с2026-11-01 до изменения','руб без НДС/т керосина; руб/кг жидкости','аэропорт/материал/дата','published_offer','Одна локальная цена; не оплаченная RW цена и не будущая граница'),
 'REN-DISCOUNT26':('УК Аэропорты Регионов','2026-08-12','с01.09.2026; разные даты окончания','процент скидки/услуга/условие','направление/перевозчик/период','published_conditional_terms','64% транзит до31.10.2026; 50% MRV до31.12.2026; нет будущей гарантии'),
 'REN-CONTRACT-TERMS':('АО Аэропорт Оренбург','UNKNOWN','снимок12.11.2026','условия договора','типовой договор','published_process','Предмет/цены/изменения/оплата/приостановление/ответственность; реальные условия RW UNKNOWN'),
 'RW-REN-EVN26':('АО Ред Вингс','2026-03-18','лето2026 с04.06','парных рейсов/неделю; минуты','airport pair/сезон','published_offer','1/нед четверг на SSJ100; даты последнего выполнения и фактические продажи UNKNOWN'),
 'REN-EVN-AIRPORT26':('АО Аэропорт Оренбург','2026-03-24','лето2026 с04.06','местные часы; минуты','REN–EVN/сезон','published_offer','REN11:10→EVN13:15;EVN14:05→REN17:45. Время185/160мин после учета UTC+5/+4; не фактическое исполнение'),
 'REN-GOJ-RGK26':('АО Аэропорт Оренбург','2026-05-04','лето2026 с03.05','рейсов/неделю; часы','пара/расписание','published_started_service','UVT GOJ и RGK вт/вс; не переносить на всю зиму'),
 'RW-B2-PRIMARY':('АО Ред Вингс','2026-09-02','с01.09.2026; срок окончания UNKNOWN','единый билет через SVX','ordered itinerary REN>SVX>MSQ','published_product','Есть совместный продукт; конкретные даты, MCT, багаж и места не подтверждены'),
 'RW-REN-PRODUCTS':('АО Ред Вингс','UNKNOWN','web snapshot12.11.2026','руб от/рекламное направление','origin-city/advertised product','advertised_not_dated_quote','Нельзя считать перечнем прямых рейсов. Дата поездки/lead/багаж/сборы UNKNOWN'),
 'RW-FARES':('АО Ред Вингс','UNKNOWN','web snapshot12.11.2026','кг/тарифный бренд','правила тарифов','published_rules','Стандарт20кг; Лайт без зарегистрированного багажа; цена конкретного бренда UNKNOWN'),
 'REN-SALT-RAIL':('АО Свердловская пригородная компания','UNKNOWN','с01.06 по07.09; год на странице UNKNOWN','км; сезонные дни','Оренбург>Илецк-1/продукт','published_product_year_unknown','Около70км; выходные; не действующее расписание2027/28 и не общий турпоток'),
 'REN-SALT-TOUR':('Туроператор Магазин Путешествий','UNKNOWN','страница продукта; даты уточнять','дней; маршрут','тур Оренбург/Соль-Илецк','advertised_product','3дня+ж/д или авиа. Наличие продукта не оплаченный RW блок'),
 'REN-SALT-STATS':('Оренбург Медиа со ссылкой на курорт','2025-09-11','лето2025','посещений/объявленных гостей','курорт/сезон','secondary_context_only','Заявлено более1.8млн; другие публикации1.6млн; входные посещения и уникальные туристы не разделены; в P05 не импортировать'),
 'REN-KUF-RAIL':('Яндекс Расписания / rasp.ru','UNKNOWN','датированные строки ноябрь2026','часы/поезд','station pair/day','aggregator_published_offer','Например031У28ноя12:05–17:49 местное,6ч44; не airport-to-airport transfer и не цена2027/28'),
 'REN-UFA-RAIL':('Яндекс Расписания','UNKNOWN','2026-09-05','часы/поезд','станция/дата','search_only_fetch404','В search6ч40 и05:15–11:55; HTTP404 при сохранении. Нужен свежий первичный/датированный источник, не норматив времени'),
 'REN-GROUND-BUS':('АО Аэропорт Оренбург','UNKNOWN','snapshot12.11.2026; будущий график UNKNOWN','руб/проезд; местные часы','вокзал–аэропорт/автобус101','published_offer','120руб; заявлено1ч20; прибытия10:00/17:10/19:50. Нельзя считать автобус доступным к каждому рейсу или тарифом2027/28'),
}
source_rows=[]
for sid,m in source_meta.items():
    r=receipts.get(sid,{})
    org,date,period,unit,grain,status,coverage=m
    source_rows.append(dict(source_id=sid,url=r.get('url','UNKNOWN'),organization=org,published_date=date,
        retrieved_at=r.get('retrieved_at',AS_OF),as_of=AS_OF,period=period,unit=unit,granularity=grain,status=status,
        coverage=coverage,http_status=r.get('http_status','UNKNOWN'),sha256_raw=r.get('sha256','UNKNOWN'),
        local_file='sources/'+sid+('.pdf' if (ROOT/'sources'/f'{sid}.pdf').exists() else '.html')))
table('sources.csv',source_rows)

evidence=[]
def fact(i, sid, statement, value='UNKNOWN',unit='описание',period=None,grain=None,status=None,coverage=None,locator='основной текст'):
    s=next(x for x in source_rows if x['source_id']==sid)
    evidence.append(dict(evidence_id=i,source_id=sid,statement_ru=statement,value=value,unit=unit,
        period=period or s['period'],granularity=grain or s['granularity'],status=status or s['status'],coverage=coverage or s['coverage'],
        source_locator=locator,url=s['url'],organization=s['organization'],published_date=s['published_date'],as_of=AS_OF,
        retrieved_at=s['retrieved_at'],source_sha256=s['sha256_raw']))

fact('E-REN-001','REN-PAX25','Обслужено более951тыс пассажиров; агрегат входящих и исходящих обслуживаний, не конечные OD.',951000,'пассажирских обслуживаний/год; строгая нижняя граница')
fact('E-REN-002','REN-PAX25','Внутренние885.5тыс, международные65.6тыс; самые популярные Москва/Санкт-Петербург.', '885500;65600','пассажирских обслуживаний/год')
fact('E-REN-003','REN-SCHEDULE-OUT','В зимней таблице RW продаваемое расписание REN–SVX; RRJ95LR. Принадлежность самолета, свободный парк и база не следуют из строки.', 'WZ5050','публикуемый рейс',locator='table0 rows6–13')
fact('E-REN-004','REN-SCHEDULE-IN','Между опубликованными arrival/departure:09:00/09:50 в среду,17:35/18:25 в понедельник,21:10/22:00 в пятницу —50мин. Принадлежность одному физическому борту UNKNOWN; это не технический минимум.',50,'мин запланированного station gap',locator='table0 rows6–13 + outbound rows6–13')
fact('E-REN-005','REN-SCHEDULE-IN','Особая входящая строка21ноя WZ901 отличается от выходящей20ноя WZ5050. Автоматическая пара рейсов не установлена.','UNKNOWN','связанная физическая ротация',coverage='Локальная clock/date/number anomaly; требуется P02/P03 сверка',locator='table0 row11')
fact('E-REN-006','RW-REN-EVN26','Свои сезонные продажи REN–EVN должны учитываться в будущем KEEP отдельной ветвью сохранения/снятия/переноса, а не быть забыты.',1,'парных рейсов/неделю')
fact('E-REN-007','RW-B2-PRIMARY','Заявлен единый билет Оренбург–Екатеринбург–Минск; маршрут существует как продукт через другой хаб. Необходима датированная проверка конкретного билета.','REN>SVX>MSQ','ordered itinerary')
fact('E-REN-008','REN-GOJ-RGK26','UVT с3мая обслуживала GOJ и RGK по вторникам и воскресеньям. Конкурент/летнее предложение нельзя считать нулем.',2,'рейсов в каждую сторону/неделю')
fact('E-REN-009','REN-WINTER26','Зимний релиз сохраняет AER, MRV, OVB, KZN, SVX, Москву, Петербург; международные ALA/GYD/AYT/SSH. Частичный детальный список не опровергает объявленный AER/AYT.','11;14','направлений; перевозчиков')
fact('E-REN-010','REN-TECH','Опубликованы ВПП2500×42м, PCN41/R/B/X/T, CATI, H24,22стоянки; в категории восьми мест RRJ95 вместе с другими типами. Это не22 свободных места или8 мест RW.','2500x42;41/R/B/X/T;22','м;PCN;физические места')
fact('E-REN-011','REN-TECH','SSJ100/RRJ95 в списке приема; допуск SJ100/ПД8 по конкретной массе/погоде/дате и линия ТО RW UNKNOWN.','RRJ95','опубликованный тип')
fact('E-REN-012','REN-COORD','Регулярные запросы не менее3 рабочих дней; услуга без договора может оказываться по публичной оферте. Это не готовая новая база.',3,'рабочих дней до полета')
fact('E-REN-013','REN-TERMINAL26','Новый терминал представлен18сентября: более24000м²,1000пасс/час и отдельная международная зона. MCT, маршруты transfer baggage, пик и договоры не установлены.','24000;1000','м2;пасс/час')
fact('E-REN-014','REN-WINTER-PREP','Оператор заявляет подготовку зимней техники, противогололедной обработки покрытий и персонала; это не гарантия dispatch reliability.','готовность по заявлению аэропорта','качественный факт')
for i,key,val,unit,page in [
 (15,'takeoff_landing',656,'руб без НДС/т МВМ',1),(16,'transport_security',806,'руб без НДС/т МВМ',1),
 (17,'excess_parking',5,'% сбора за взлет-посадку/час сверхнормативной стоянки',1),
 (18,'terminal_domestic',82,'руб без НДС/пассажир',2),(19,'pax_domestic',189,'руб без НДС/пассажир',2),
 (20,'terminal_international',110,'руб без НДС/пассажир',2),(21,'pax_international',273,'руб без НДС/пассажир',2),
 (22,'fuelling',2329,'руб без НДС/т',2),(23,'fuel_storage',2990,'руб без НДС/т',2),
 (24,'transit_pax_domestic',170.10,'руб без НДС/пассажир',3)]:
    fact(f'E-REN-{i:03}','REN-TARIFF26','Опубликованная reference ставка '+key+'; применимость, налог, база начисления и договор RW требуют P04.',val,unit,locator=f'PDF p{page}')
fact('E-REN-025','REN-FUEL26','Керосин141405руб/т безНДС с01.11.2026, подпись30.10.2026. Нельзя повторно добавить уже включенные заправку/хранение без спецификации.',141405,'руб без НДС/т керосина',locator='PDF p1; визуально проверено')
fact('E-REN-026','REN-FUEL26','Противоводокристаллизационная жидкость378.90руб/кг — иной материал, чем противообледенительная обработка ВС.',378.90,'руб без НДС/кг',locator='PDF p1; визуально проверено')
fact('E-REN-027','REN-DISCOUNT26','64% на новые транзитные рейсы МВМ45–50т при новом сегменте закончились31.10.2026; ветвь будущего продления UNKNOWN.',64,'% условной скидки',locator='PDF p3 п1.5; визуально проверено')
fact('E-REN-028','REN-DISCOUNT26','MRV:50% на восстановленное направление до31.12.2026 с исключениями топлива, заправки, ПОЖ и ряда услуг. Получатель RW не установлен.',50,'% условной скидки',locator='PDF p2 п1.2')
fact('E-REN-029','REN-CONTRACT-TERMS','Типовые условия включают порядок оплаты и право приостановления услуг. Фактический launch, collateral, exit и кассовые сроки RW UNKNOWN.','UNKNOWN','руб;дни;договор')
fact('E-REN-030','RW-REN-PRODUCTS','Сайт рекламирует дальние/региональные направления из REN, в том числе GOJ,OMS,NOZ,KEJ,BAX,MSQ. Они не являются доказательством прямых рейсов.','advertised products','направление/страница')
fact('E-REN-031','REN-SALT-TOUR','Есть трехдневный тур с ж/д или авиа; механизм inbound-продукта возможен, но объема/оплаты RW нет.',3,'дней наземной программы')
fact('E-REN-032','REN-SALT-RAIL','Сезонный поезд и наземный доступ отделяют туристический центр от аэропорта; время/цена трансфера REN–курорт требуют отдельного источника.',70,'км от Оренбурга по странице оператора')
fact('E-REN-033','REN-SALT-STATS','Крупная цифра посещений курорта имеет неодинаковые определения в публикациях; не уникальные авиа-OD.', 'UNKNOWN','уникальных авиа-поездок',status='not_admitted_to_demand',coverage='Контекст сезонности; нельзя умножать на произвольную долю перелета')
fact('E-REN-034','REN-KUF-RAIL','Наземная альтернатива Самара подтверждается датированной агрегаторской строкой031У28ноября; наземный конкурент не ноль.',404,'мин станция–станция',locator='строка031У 28ноя2026;12:05–17:49 local')
fact('E-REN-035','REN-GROUND-BUS','Автобус101 от вокзала:08:45→10:00,16:00→17:10,18:25→19:50;120руб. Рекламное время1ч20 отличается от конкретных интервалов70/75/85мин. Первая опубликованная подача не подходит к среднемуRWвылету09:50. Дом–вокзал/такси и будущий график UNKNOWN.','120;10:00;17:10;19:50','руб/проезд; часы прибытия в аэропорт')
table('evidence.csv',evidence)

# Конкуренты: дословные значения таблицы, без изобретенного числа кресел.
offers=[]
for side in ['OUT','IN']:
    for r in json.loads((ROOT/f'REN-SCHEDULE-{side}.rows.json').read_text()):
        c=r['cells']
        if len(c)!=8 or ':' not in c[0]:continue
        offers.append(dict(offer_id=f'REN-{side}-{r["row"]:03}',origin='REN' if side=='OUT' else c[7],
            destination=c[7] if side=='OUT' else 'REN',departure_local=c[0],arrival_local=c[1],weekdays=c[2],
            source_interval_without_year=c[3],carrier=c[4],flight_number=c[5],aircraft_label=c[6],
            seats='UNKNOWN',open_seats='UNKNOWN',sale_or_through_product='UNKNOWN',fare='UNKNOWN',baggage='UNKNOWN',booking_lead='UNKNOWN',
            source_id=f'REN-SCHEDULE-{side}',source_row_id=f'table0:row{r["row"]}',source_row_sha256=r['row_sha256_html_normalized'],
            unit='scheduled_service;local_clock',period='ОЗП2026/27 inferred; исходный интервал сохранен',as_of=AS_OF,
            coverage='один официальный schedule snapshot; не весь рынок; не physical-seat admission',status='published_offer',assumption_id='A-REN-01'))
table('competitor_offer_rows.csv',offers)

assumptions=[]
def assumption(i,val,unit,basis,interval,impact,sens,refinement):
    assumptions.append(dict(assumption_id=i,value=val,unit=unit,selected_by='исследователь REN, Sol6.1 xhigh',why_and_source=basis,
        range_or_unknown=interval,affected_conclusions=impact,sensitivity=sens,how_to_refine=refinement,
        period='2027-2028 если не указано иное',coverage='явное сценарное условие; не доверительный интервал',status='research_not_team_accepted'))
assumption('A-REN-01','winter2026/27','год сезона','РелизREN-WINTER26 датирует сезон; таблица опускает год.','Только25.10.2026–27.03.2027 по отдельным интервалам','Зимние частоты; будущий KEEP неизвестен','Не продлевать летние/декабрьские строки','P02 датированный экспорт и archive/seasons')
assumption('A-REN-02',3,'парных рейсов/неделю/пара','Диагностический календарь пн/ср/пт либо вт/чт/сб:2–3ночные поездки и точные7/14ночей; спрос из этого не следует.','Дискретные2/3/4; это варианты продукта, не рыночные границы','Программная мощность и calendar utility','Пересчитать выбор/кресла/ресурс для2 и4; не держать pax фиксированными','P05 цели/длительность/дни поездки и P03 слоты')
assumption('A-REN-03',60,'мин оборота','Диагностика относительно опубликованного50мин REN-SVX; запас10мин выбран исследователем, не норматив.','Проверки45/60/90; рабочие границы UNKNOWN','Ротации и длительность служебного дня','Все обороты45/90; банковские разрывы отдельно','SGHA + P03 тип/аэропорт/ground process')
assumption('A-REN-04',90,'мин bank/MCT test','Кандидат защищенной пересадки; MCT аэропорт/перевозчик UNKNOWN.','Тесты60/90/120; не утвержденный MCT','Соединения обеих сторон и пропущенные пересадки','При фактическом MCT>90 базовый bank непригоден без изменения расписания','RW/аэропорт: MCT, багаж, passenger process, protection contract')
assumption('A-REN-05',100,'кресел/абстрактный SSJ100 аналог','P03 RRJ95LR_100: страница семейства; конкретный салон/блокированные кресла неизвестны.','Салон RW UNKNOWN; 100 только счетчик условной мощности','Номинальная проектная емкость, не спрос/открытые кресла','P06 заменить на физический tail/cabin; пересчитать при другом салоне','P03 борт и cabin/tech blocks')
assumption('A-REN-06','RRJ95LR_100_analogue','вариант','Текущая таблица REN маркирует RRJ95LR; новые поставкиSJ100/PD8 проверяются отдельной ветвью P03.','SJ100/PD8:допуски/кресла/время/топливо/ТО UNKNOWN','Все прототипы расписаний — проверка аналога, не сертификацияSJ100','Повторить на параметрах SJ100 и на D0 без новых самолетов','P03 точный вариант/AFM/типовой допуск/ресурс')
assumption('A-REN-07','SVX95;GOJ105;MRV170;OMS150;REN-EVN185/EVN-REN160;SVX-GOJ120;SVX-MRV210','мин block/плечо','SVX95 и MRV165–170 из REN schedule; GOJ новость≈90, выбрано105; EVN185/160 из двух направлений REN-EVN-AIRPORT26 с часовыми поясами. OMS150 и control120/210 — исследовательский аналог до P03, не измерение.','GOJ90/105/120;MRV165/170;SVX90/95;OMS/controls UNKNOWN (±30мин только стресс, не bounds)','Часы, поворотные окна; без P03 нельзя заявлять выполнимость','Варьировать каждое плечо и асимметрию ветра/трассы; не оценивать по геодезии одну дальность','P03 dated route block + restrictions/payload + TO timetable')
assumption('A-REN-08','G1:1;G2:2','линейных абстрактных хвостов','Ресурс для парных опытов выбран из числа одновременных линий шаблона; это потребность, не наличие RW.','Доступ RW UNKNOWN; полная группа включает общий резерв, ТО, экипажи','Общие fleet_scope и alternative use','Простой или свободные часы остаются в KEEP/alternative programme','P03 назначить реальные хвосты, donor tasks, date-ready calendar')
assumption('A-REN-09','UNKNOWN','резервных хвостов/месяц','Нельзя объявлять модельные4+1 фактом. Нужны location/availability/response-time общего reserve pool.','UNKNOWN','Dispatch/cash/resource gate','Считать dedicated reserve1 как отдельный дорогой стресс, не принятую норму','P03 tails/coverage/disruption plan; P04 reserve charges')
assumption('A-REN-10','2027 pilot после accepted service_entry; не раньше2027H2','дата активации','Постановка кейса; конкретные N(t) и lag дает P03.','D0;partial;delay;phased, без вероятностей','Нет автоматических24месяцев полной мощности','До доступности сохранять KEEP; при partial R1/E1/D1 против H1','P03 delivery_calendar_id и end-to-end readiness')
assumption('A-REN-11','KEEP REN-SVX,REN-EVN(лето),REN-SVX-MSQ; остальные затронутые продажи RW сохранять','продажи/рейсы','Наблюдаемые или опубликованные свои продукты; точный будущий календарь отсутствует.','Объемы/договорные ограничения UNKNOWN; отсутствие в списке не ноль','Нельзя приписать весь проектный OD новым пассажирам','Отдельная ветвь replace требует flight IDs/выручку донора, cancellation/refund/alternative','P03 future KEEP + P05 own-sales inventory')
assumption('A-REN-12','50/64% не переносить','скидки','REN-DISCOUNT26 имеет явные даты/направления; продление2027/28 неизвестно.','Будущее продление/договор UNKNOWN; no-award branch обязательна','Порог доступного запуска/хаба','Пересчитать только после приемки условий; не на весь топливный чек','P04 eligibility owner/услуга/срок/договор')
assumption('A-REN-13','UNKNOWN','потенциальных конечных поездок/месяц/сегмент','Агрегат951тыс обслуживаний и авторские gravity estimates не маршрутные наблюдения.','UNKNOWN','Никаких экономических побед или долей','Общее P05: все OD/маршруты/конкуренты/ground/другие программы заново','P05 common potential-market and choice calibration')
assumption('A-REN-14','UNKNOWN','руб2027/28/услугу;расходы/пуск/выход','Местные тарифы2026 толькоreference; реальная ставка/индексация/НДС/договора нет.','UNKNOWN; историческая точка не lower/upper будущего','TH-OPTION/TH-FIXED/TH-FUNDING остаются symbolic','Совместный P04 диапазон либо порог; не сложение всех неизвестных по независимым максимумам','RW SGHA/MRO/base/fuel contracts; P04 driver mapping')
assumption('A-REN-15','UNKNOWN','реакция конкурента/месяц','Есть действующее предложениеA4/RT/S7/SU/FV/N4/5N. Свободные борта/бюджет реакции не найдены.','UNKNOWN','Частота и цена в P05, а не гарантированный захват','Нулевой ответ только отдельный сценарий; дополнительная частота требует resource provenance','P02 response policy с capacity/source; P05 price response break-even')
assumption('A-REN-16','UNKNOWN','уникальных air-tourists;оплаченных кресел','Турпродукт и посещения курорта сигнал сезонности; повторные входы и наземные гости не авиа-OD.','UNKNOWN','Туристическая гипотеза условна; договорной блок не выдуман','Без блока retail-choice; с договором один event и общие кресла','P05 residence/mode/month; туроператор lead/allotment/release/payment terms')
assumption('A-REN-17','0','новыхТу214 в maincase','Граница задания; SSJ/SJ maincase, международное расширение не требует новогоТу214.','Отдельная дополнительная ветвь только по P03','Не заменять Superjet широкофюзеляжным ресурсом','Повторить только в принятом mixed-fleet scope','P03 поставки/тип/KEEP для отдельного extension')
assumption('A-REN-18','Feb/Apr/Jul/Nov2028 по одной полной неделе','диагностические даты','Разделение зима/межсезонье/лето/осень; не статистически репрезентативная выборка года.','UNKNOWN для фактической сезонной программы2027/28','Механика и частотный календарь; годовые pax/деньги NOT_RUN','24месяца полного календаря после P05/P03; не умножать неделюна52','P03 accepted seasonal calendar + P05 monthly demand')
assumption('A-REN-19','R1/E1 местный вылет11:30; diagnostic predeparture90','местное время;мин','В текущем автобусном предложении первая подача в аэропорт10:00. Одинаковые часы onward рейсов R1/E1 устраняют календарный confound. 90мин выбранный запас, не правило check-in.','Фактическое закрытие check-in/изменения автобуса/такси UNKNOWN','Ground access и выбор между дневной/ранней деловой поездкой','Повторить ранний вариант с полной ценой такси/ожидания; R2 поздний OMS требует обратного ground доступа','P05 door-to-door basket + RW check-in + аэропорт ground timetable')
table('assumptions.csv',assumptions)

baseline={
 'period':'2027-01/2028-12','status':'FUTURE_KEEP_REQUIRED','source_years':'наблюдения/объявления2026, не готовый KEEP2028',
 'preserve':['REN-SVX опубликованные/проданные рейсы','летняя ветвь REN-EVN и ее контрактные обязательства',
 'REN>SVX>MSQ и другие затронутые RW-соединения','SVX-GOJ/SVX-MRV и общие исходящие продажи существующей базы',
 'весь остальной затронутый domestic/international/charter бизнес и платежи'],
 'own_sales_quantities':None,'donor_if_existing_aircraft':'Назвать хвост, прежние задания, продажи, расходы, обязательства; no-new не означает free',
 'new_aircraft_alternative':'CP-REN-D1 или принятый лучший общий проект на том же физическом ресурсе',
 'p02_admission':'source export, не открытые физические кресла', 'assumption_id':'A-REN-11'}

def prog(pid,title,role,group,pairs,changes,template,mechanism,needs):
    return dict(programme_id=pid,title_ru=title,role=role,resource_group_id=group,unique_project_airport_pairs=pairs,
        period='2027-01/2028-12; активация по P03; шаблоны2028',seasons='зима/лето/межсезонье раздельно; полный принятый календарь UNKNOWN',
        keep=baseline,market_changes=changes,rotation_template=template,mechanism=mechanism,
        fleet_variant='RRJ95LR_100_analogue; SJ100_PD8 отдельный непроверенный вариант',new_tu214=0,
        reserve='Общий принятый reserve pool UNKNOWN; не свободный нулевой резерв',
        monetary_result=None,market_share_result=None,admission='STAGE_A_DESIGN_ONLY',needs_shared_inputs=needs,
        assumption_ids=['A-REN-02','A-REN-03','A-REN-05','A-REN-06','A-REN-07','A-REN-08','A-REN-09','A-REN-10','A-REN-11','A-REN-13','A-REN-14'])

programmes=[
 prog('CP-REN-00','Сохранение REN–SVX и улучшение существующих пересадок','EXISTING_PRODUCT_PARTNER','G0',['REN-SVX'],
      'Рейсы не добавлять; сначала подобрать датированные REN-SVX-MSQ и дальние RW-продукты; retime только при учете потерянных связей.',
      'KEEP с отдельными разрешенными retime actions; никаких автоматических open seats',
      'Проверить улучшение продукта с текущим узлом SVX до нового узла REN.', ['P02 dated sale/through legs','P03 future KEEP','P05 connected itinerary utilities']),
 prog('CP-REN-R1','REN: дневные прямые GOJ и MRV с одной радиальной линией','NEW_RADIAL_BASE','G1',['GOJ-REN','MRV-REN'],
      'Новые RW REN-GOJ3/нед и REN-MRV3/нед сверх сохраненного KEEP. UVTлетоGOJ2/нед и A4MRV2/нед сохраняются как конкуренты.',
      'Пн/ср/пт REN-GOJ-REN;вт/чт/сб REN-MRV-REN; один хвост ночуетREN; воскресенье не занято проектом, но не подтверждено ТО.',
      'Прямые поездки без SVX; дневной MRV против опубликованного04:00, точные7/14ночей. Дополнительная база оправдана только общей дельтой после всех затрат.',
      ['P05 REN-GOJ/MRV/month/ground/own migration','P03 REN overnight/MRO/crew + reserve','P04 base/start/exit/fuel/handling']),
 prog('CP-REN-E1','Та же местная программа REN из существующей базы SVX','EXISTING_BASE_CHAIN','G1',['REN-SVX','GOJ-REN','MRV-REN'],
      'Те же6 onward roundtrips/нед; каждый полный оборот SVX-REN-X-REN-SVX. По умолчанию6 дополнительных парREN-SVX; замена существующих отдельно, после flight-ID mapping.',
      'Пн/ср/пт SVX-REN-GOJ-REN-SVX;вт/чт/сб SVX-REN-MRV-REN-SVX; один хвост возвращаетсяSVX.',
      'Контроль против R1: экономит новую overnight-базуREN, добавляет19ч block/нед. Все добавленные собственные продажи SVX учитываются совместно.',
      ['P03 actual SVX crew/MRO capacity and turn windows','P05 own cannibalization REN-SVX + onward itinerary','P04 differential handling/cycles/opportunity costs']),
 prog('CP-REN-D1','Новый ресурс на прямые SVX–GOJ и SVX–MRV','EXISTING_BASE_DIRECT_CONTROL','G1',['GOJ-SVX','MRV-SVX'],
      'REN сохраняетKEEP; дополнительный ресурс даетSVX-GOJ3/нед иSVX-MRV3/нед. Конкуренты и существующие продажи RW в SVX не обнулены.',
      'Пн/ср/пт SVX-GOJ-SVX;вт/чт/сб SVX-MRV-SVX.',
      'Альтернативное применение того же нового хвоста; результат по всему объединению затронутых OD, а не только местнымREN.',
      ['P03 actual dated SVX controls/block/donor','P05 full union of OD + incumbents','P04 accepted cost drivers']),
 prog('CP-REN-R2','Расширение радиальной линии REN до OMS','NEW_RADIAL_BASE_EXTENSION','G1',['GOJ-REN','MRV-REN','OMS-REN'],
      'R1 + REN-OMS3/нед на длинных дняхпн/ср/пт; не сложить независимо сR1. Текущий прямойREN-OMS не установлен; пересадки/иные периоды не ноль.',
      'REN-GOJ-REN-OMS-REN пн/ср/пт; REN-MRV-REN вт/чт/сб. Весь ресурс одного хвоста/нескольких экипажей подлежит P03.',
      'Проверить порог потребности во втором хвосте/экипажах до автоматического расширения хаба.',
      ['P05 latent REN-OMS + viaSVX/OVB/MOW','P03 OMS route block/crew split','P04 incremental cycle + staff/time costs']),
 prog('CP-REN-H1','Защищенная мини-волна REN между SVX/OMS и GOJ/MRV','TRANSFER_HUB','G2',['REN-SVX','OMS-REN','GOJ-REN','MRV-REN'],
      'По3/нед в обе стороны каждого луча, сверхKEEP. ЧерезREN:SVX-GOJ,SVX-MRV,OMS-GOJ,OMS-MRV; местныеREN-OD используют те же кресла.',
      'T1 SVX-REN-MRV-REN-SVX;T2 OMS-REN-GOJ-REN-OMS пн/ср/пт. Восточные arrivalsREN09:00UTC→west departures10:30; reverse arrivals17:10→east departures18:40. Turn at endpoints60; REN bank90.',
      'Календарь дает точный7/14ночный возврат и общие кресла; отличающий опыт retime same flights без банка сохраняет local supply. OMSночевка/база отдельныйUNKNOWN, RENнеобязательно overnight-база.',
      ['P05 four cross-OD + local shared inventory + existing direct/through RW','P03 OMS overnight, two long line-days, crews/MCT/TO/slots','P04 REN connection handling + OMS overnight + passenger protection']),
 prog('CP-REN-X1','Сохранение или сезонная перенастройка собственного REN–EVN','INTERNATIONAL_EXTENSION','G1_OPTION',['EVN-REN'],
      'Не новая заявленная с нуля линия:1/нед лето2026RW. Сравнить KEEP summer1/нед, stop с потерей продаж и retime; на тех же хвостах вместо другого задания.',
      'Летний четверг REN-EVN-REN; для SVX-based полного оборота добавитьSVX-REN иREN-SVX; конфликт сR1/E1MRVчетверг требует явной замены, не суммы.',
      'Реальное собственное международное происхождение и новый терминал; не доказательство роста всего рынка или допускаSJ100 вEVN.',
      ['P03 exact summer KEEP/permissions/variant/return rotation','P05 EVN demand/competitors/ground lead/baggage','P04 international rates/tax/FX/launch-exit'])]
dump('programme_candidates.json',{'schema':'REN-StageA-programme-1','programmes':programmes,
    'composition_rule':'R2 заменяетR1; R1/E1/D1 взаимоисключающие опытыG1; H1 заменяет местный набор при совместном расчете. X1 делит ресурс/кресла, не независимый денежный плюс.',
    'global_target':'8–12 уникальных airport pairs к концу2028 относится к общей проектной сети. REN-кандидаты дают2–4 пары; новые и уже существующие уникальные пары считаются один раз.',
    'engine_contract':{'commit':PINS['P06'],'path':PREFIX+'P06/producer_contract.json','status':'прочитан; complete bundle не собран; P06 evaluate NOT_RUN; independent acceptance pending'},
    'source_ids':['REN-SCHEDULE-OUT','REN-SCHEDULE-IN','REN-GOJ-RGK26','RW-REN-EVN26','RW-B2-PRIMARY']})

hyps=[]
def hyp(i,role,signal,sources,mech,cf,test,outcome,unknown,review,ancestors):
    hyps.append(dict(hypothesis_id=i,role=role,signal=signal,source=sources,mechanism=mech,counterfactual=cf,
        distinguishing_test=test,ancestorIDs=ancestors,outcome=outcome,blocking_unknown=unknown,reconsideration_condition=review,
        period='2027-2028',status='StageA_concluded_StageB_pending',coverage='REN и перечисленные затронутые рынки; не общероссийская рекомендация'))
hyp('H-REN-ROLE','Текущая роль RW','Действующая REN-SVX; летнийREN-EVN; продуктREN-SVX-MSQ',
    ['E-REN-003','E-REN-006','E-REN-007'],'Outstation и origin-market по источникам; существующая база/хабRW не доказаны.',
    'Нельзя присвоить новую базу с нулевой стоимостью или объявить чужую историюOrenair базойRW.',
    'Действующий договор базирования/overnight/MRO/crew и датированные хвостыRW вREN.',
    'оценена в указанной области: published_RW_market_outstation; base/hub UNKNOWN','RW actual base/overnight contracts','ДокументRW о базировании/подтвержденные ротации меняют классификацию.', ['PLAN:seed:REN','BASE:airport_tech:REN'])
hyp('H-REN-01','Радиальная дневная база','Действующие/летние рынки MRV и GOJ; ночью опубликованMRV; прямой продукт и короткие поездки.',
    ['E-REN-008','E-REN-009','E-REN-024'],'R1 сокращает технические плечи кSVX, но оплачивает новую базу. 3/нед выбран ради календаря, не от спроса.',
    'E1 те жеREN-OD и частоты; D1 тот же хвост наSVX; будущийKEEP сохраняет продажи.',
    'P06 joint compare R1/E1/D1 наG1 с полной базой, резервом и P05; порог TH-OPTION дляREN base.',
    'условна из-за конкретного неизвестного','ПотенциальныеOD и differential base/crew/MRO contracts','Выигрыш общей дельты после новой базы/запуска и финансирования; иначе изменить частоты/отказаться отR1.', ['AUTHOR:Хаб REN:GOJ','AUTHOR:Хаб REN:MRV','PLAN:seed:REN'])
hyp('H-REN-02','Прямые местные продукты изSVX','Реальная REN-SVX и опубликованный50мин turnaround; RENбаза не подтверждена.',
    ['E-REN-003','E-REN-004'],'E1 сохраняет ночевкуSVX; extra legs могут оказаться дороже новой базы.',
    'R1 те жеGOJ/MRV; D1 лучшее альтернативное использование, не zero task.',
    'Полные цепочки, две версии add и replace существующихREN-SVX, donor revenue и paid-cycle cost; crew legality.',
    'условна из-за конкретного неизвестного','Дополнительный crew/MRO slotSVX и каннибализация текущихRW пассажиров','При невыгодных дополнительных плечах пробовать overnightREN/более редкий календарь; не считать весьREN опровергнутым.', ['BASE:rw_routes_now:REN-SVX','PLAN:EXISTING_BASE_DIRECT'])
hyp('H-REN-03','Защищенная мини-волна','Авторская модель имеетREN transfer portfolio; на сайтахRW есть черезSVX продукт; терминал расширен.',
    ['E-REN-007','E-REN-013','BASE_network_REN.subset.json'],'H1 объединяет local и transfer pools на общих креслах четырех лучей; тариф конечной поездки начисляется один раз.',
    'Те жеH1flights с разнесенными банками + лучшие direct programs на двух тех же хвостах; будущийKEEP.',
    'Сперва H1vsunsync с одинаковой частотой/креслами; затем общий hub vs direct. MCT60/90/120, пропуски связей, roundtrip7/14ночей; не суммировать прежние captured flows.',
    'условна из-за конкретного неизвестного','Истинные cross-OD, продажаprotected transfer, MCT и два длинных дня с crew/ТО','Если полной базой/защитой невыполним H1, пересчитать инойbank/ресурс/плечи; один плохой шаблон не отказ городу.', ['AUTHOR:Хаб REN','PLAN:TRANSFER_HUB'])
hyp('H-REN-04','Подвоз и партнер черезSVX','Официальный единый билетREN-SVX-MSQ уже заявлен; дальниеRW продукты рекламируются.',
    ['E-REN-007','E-REN-030'],'Сначала проверить качество и дату существующих связей; возможен retime без нового борта.',
    'БудущийKEEP с текущими связями; новое расписание должно сохранить/оценить потерянные OD.',
    'Датированные outbound+return, единая тарификация/багаж, MCT и проданный inventory; вмешательствоretimevsKEEP.',
    'условна из-за конкретного неизвестного','Точныйдатированный basket и объем incremental journeys','При уже хороших связях отдельного эффекта retime может не быть; это не повод обнулить партнерский продукт.', ['P02:P02-bf48e86a0f5ae978','PLAN:EXISTING_PRODUCT_CHANGE'])
hyp('H-REN-05','Сезонный inbound-туризм','Курорт и туроператорский3дневный продукт с авиа/жд; сильная летняя сезонность.',
    ['E-REN-031','E-REN-032','E-REN-033'],'Наземный трансфер и accommodation могут сделать поездку удобной; выручка блока возникает только по договору.',
    'Retail на тех жеR1/R2 рейсах; поезд/автобус/автомобиль; независимые туристические гости не новый авиа-рынок.',
    'P05 residence/mode/month + matched tour basket; allotment/release/payment events и общие кресла; без договора только retail.',
    'условна из-за конкретного неизвестного','Уникальные air-OD и условия/наличие оплаченного блока','Отсутствие added air demand или проигрыш полного door-to-door basket снимает именнотуристическую надстройку.', ['PLAN:DATA_TO_HYPOTHESIS','PLAN:seed:REN'])
hyp('H-REN-06','Международное сезонное продолжение','СвойREN-EVN1/нед летом2026; зимойUVTALA иIOGYD; международная зона нового терминала.',
    ['E-REN-006','E-REN-009','E-REN-013'],'ВеткаX1 защищает/перенастраивает свои продажи; новые ALA/GYD конкурируют с реальными перевозчиками.',
    'EVNлетнийKEEP/изменение с потерей результата; domestic use того же хвоста; ноль новыхТу214.',
    'Датированные competitor baskets и permitted exact variant, полный оборот, FX/tax/права/пассажиры и ресурсные конфликты.',
    'условна из-за конкретного неизвестного','БудущиеEVN рейсы/обязательства/спрос и допускиSJ100','Восстановить/сохранить только при общей дельте и финансировании; не объявлять EVN полностью новымрынкомRW.', ['RW:REN-EVN:2026-03-18','PLAN:EXTENDED'])
hyp('H-REN-07','Короткий подвоз UFA/KUF/UUA','АвторскийREN-UUA363км; наземная Самара≈6ч44, Уфа search6ч40; сравнивать весьdoor-to-door.',
    ['E-REN-034','E-REN-035','BASE_network_REN.subset.json'],'Малое время полета может теряться на доступе/ожидании; подвоз также конкурирует за два кресла.',
    'Ground→существующаябаза или nonstop более длинного OD, плюс opportunity cost короткого SSJцикла.',
    'По месяцу/району residence сравнить total fare+access+calendar; не использовать500км как экономический порог.',
    'условна из-за конкретного неизвестного','Точные ground times/prices и доля catchment каждого аэропорта','Разделенные contract/connecting pools с доказанным временем/оплатой могут оправдать короткийspoke; сейчас самостоятельное число рейсов не выбрано.', ['AUTHOR:Хаб REN:UUA','PLAN:seed:REN'])
hyp('H-REN-08','Дальние восточные лучи NOZ/KEJ/BAX/TOF и региональные OMS/TJM','АвторскиеREN-MRV transfer89464 segments иREN-NOZ54672 — модельные estimates; RW уже рекламирует distant connecting products.',
    ['BASE_network_REN.subset.json','E-REN-030'],'Проверить новые local+cross конечныеOD и дальнейшее расширениеR2/H1; модельные суммы не независимы.',
    'Прямые ичерезSVX/OVB/MOW; собственные действующиеRW products; разные недопущенные оценки не складываются.',
    'P05 восстановить residence/destination/месяц/путь; затем P03 runway/payload/block/reserve для дальних лучей.',
    'условна из-за конкретного неизвестного','Наблюдаемый дальнийOD, diversion/payload и календарь/ресурс','Сильный подтвержденный OD/контракт меняет набор4лучей. Низкий старыйscore или отсутствиеотдельногорасчета не отказ.', ['AUTHOR:Хаб REN:NOZ','AUTHOR:Хаб REN:MRV','BASE:longlist:REN'])
dump('hypotheses.json',{'hypotheses':hyps,'no_economic_city_rejection':True,'history_policy':'Авторские frozen результаты сохранены отдельными строками; новый вывод не переписывает старые оценки.'})

market_rows=[]
for p in programmes:
    for pair in p['unique_project_airport_pairs']:
        rw=(pair=='REN-SVX')
        base='RW schedule4/нед в7–13.12.2026, по иным неделям иначе; futureKEEP UNKNOWN' if rw else ('RW summer2026 1/нед;futureKEEP UNKNOWN' if pair=='EVN-REN' else 'ПрямойRW вREN не установлен; own through sales UNKNOWN; futureKEEP требуется')
        if p['programme_id']=='CP-REN-00':delta='0 полетов; retime не задан'
        elif p['programme_id']=='CP-REN-X1':delta='KEEP1/нед либо явнаяперенастройка/снятие; новыйdelta UNKNOWN'
        elif pair=='REN-SVX' and p['programme_id']=='CP-REN-E1':delta='+6/нед add; replace отдельная ветвь'
        else:delta='+3/нед add на активныйсезон; baseline не обнулен'
        comp={'GOJ-REN':'UVTлето2026 вт/вс;зимние/2027-28 UNKNOWN', 'MRV-REN':'A4-6150/6149;зимаобычнопн/чт;RRJ95LR;2/нед',
              'OMS-REN':'прямойнеустановлен;проверитьviaSVX/OVB/SVO;otherperiod UNKNOWN','REN-SVX':'RW собственныйexistingproduct;другиеalternatives UNKNOWN',
              'EVN-REN':'RWsummer2026;другиедаты/черезMRV/SVO UNKNOWN', 'GOJ-SVX':'действующийRW и другиеперевозчикипоP02;необнулены',
              'MRV-SVX':'действующиеRW/конкурентыпоP02;необнулены'}[pair]
        market_rows.append(dict(programme_id=p['programme_id'],airport_pair=pair,direction='оба направления;точныеflightIDs в templates',
            baseline_rw=base,proposed_delta_rw=delta,competitor_baseline=comp,
            own_sales_keep_or_change='KEEP сохранен; P05 повторно распределяет собственныйпереток; replace запрещенбезdonorIDs',
            demand_pool='P05 единые конечныеOD/месяц; local и connecting делят кресла',
            response_resource='UNKNOWN; наличие2частотA4/RT не sparecapacity; price/frequency response должениметьsource/resource',
            period=p['period'],unit='парныхрейсов/неделю;негодовойpax',coverage='кандидат;неполныйсписокконкурентов;sharedOD',status='scenario_design',
            source_id='REN-SCHEDULE-OUT;REN-SCHEDULE-IN;REN-GOJ-RGK26;RW-REN-EVN26;P02_existing_base_controls.subset.json',
            assumption_id='A-REN-02;A-REN-10;A-REN-11;A-REN-13;A-REN-15'))
table('market_deltas.csv',market_rows)

requests=[
 ('CR-REN-01','P05','R1/E1/D1/R2/H1','Потенциальные конечныеOD по24месяцам:REN-GOJ/MRV/OMS/SVX;SVX-GOJ/MRV;OMS-GOJ/MRV;REN-EVN/MSQ изатронутыедальниеRW.', 'market_calendar, demand_pool_id,source_period/grain,residence/destination,segment,season,unique journey mapping','Не превращать951тыс обслуживаний/курортныевходы/gravity оценки вOD; own flows общие','A-REN-13','DENY_MONETARY_WIN'),
 ('CR-REN-02','P02/P05','all','Сопоставимые1ADT one-way+return baskets на конкретные даты:цена/багаж/сборы/пересадки/права/lead7/28/60дней.', 'booking_as_of+travel_date+return_date+timezone+carrier+legs+fare_brand+20kg/no_bag+fees+sellability','6500promoSVXREN изP02 привязанкreturn search02–04Dec,неquote инеполовина; рекламныеотцены не датированные','A-REN-13','QUOTE_GAP'),
 ('CR-REN-03','P03','G1/G2','Одинаковый физический ресурс/датыдоступности поD0/partial/delay/phased;variantRRJ95B/LRvsSJ100PD8,donor/KEEP,reserve,crew/ТО.', 'fleet_calendar_id,service_entry,tail,cabin,technical_blocks,variant,crew,maintenance,reserve_intervals,prior_tasks','Шаблонысчитаютнепересечениетолько; свободныйRWпаркUNKNOWN','A-REN-06;A-REN-08;A-REN-09;A-REN-10','OPERATIONS_GATE'),
 ('CR-REN-04','P04','R1vsE1vsD1','Принятьлокальныеreference656/806/82/189 иfuel141405; будущиедоговоры/индексация/НДС/платежиUNKNOWN.', 'rates unit+effective_date+VAT+quantity applicability+package overlap;SGHA/MRO/crew/base/start/exit/fuel/cash','Топливо/хранение/заправкунеудваивать; тариф170.1transitpax не automatic replacement всехpaxfees; incomplete approvalheader','A-REN-14','FINANCE_GATE'),
 ('CR-REN-05','P03/airport/RW','H1','MCT/защищенностьбилета/багаж/регистрация/пики2самолета/слоты/handling; еслиbank90неподходит–перепланировать.', 'domestic_MCT;protection agreement;airport/airline/type/date process;arrival/departurebankcapacity','Терминал1000пасс/час иaircraftacceptance не гарантииprotected connection','A-REN-04','TRANSFER_GATE'),
 ('CR-REN-06','P02/P03','all','Закрытьлокальнуюcalendarаномалию20–21NovWZ5050/WZ901;нестыковкуспискарелизаAER/AYTсдетальнойтаблицей;летниеGOJ/RGK/EVN.', 'dated two directions + physical adjacent legs + continuity + operated/marketing + capacity authority','Сохраненыисходныестроки/hash;неповышать277partial или REN3/28 доadmission','A-REN-01','CALENDAR_GAP'),
 ('CR-REN-07','P02/P05','R1/R2/H1','РеакцияA4MRV,RTGOJ/KZN/ALA,S7OVB,SU/FV/N4/5NSVO/LED:ресурс,база,кресла,срок.', 'response_policy_id with unit-source/resource bounds; fare/frequency joint response','Неизвестныйответненулевойи не гарантированные+1частота/-10%цена;посчитатьпорогсменырешения','A-REN-15','RESPONSE_GAP'),
 ('CR-REN-08','P05/local','H-REN-05/07','Ground/catchment: районы Оренбуржья, REN/UFA/KUF/OSW; доступ к аэропортам и Соль-Илецку; пересечение catchment.', 'door-to-door minutes+fare+calendar+residence/month; ground route provenance','Bus101:120руб, первая подача10:00; раннему рейсу нужен иной доступ. UFArail fetch404; Samara6ч44 stationpair не airporttransfer','A-REN-16;A-REN-19','GROUND_GAP'),
 ('CR-REN-09','P04/P06','R1vsE1','TH-OPTION,TH-FIXED,TH-LAUNCH,TH-MRO,TH-FUNDING наобщемscope:максимальнаяполнаястоимостьбазыRENипиковаяпотребностьвфинансировании.', 'full operating delta vs best existing + cash-before-financing path including prelaunch/exit/terminal liabilities','ПорогинаосновеобщегоP05;невыбиратьнеизвестныенезависимопоихмаксимумам;безплатежныхдатpeak UNKNOWN','A-REN-14','THRESHOLD_REQUEST'),
 ('CR-REN-10','P03/P05','X1','БудущийлетнийEVNKEEP/контрактыиalternate useчетверга;SJ100PD8допусквREN/EVNиальтернативныеinternationals0новыхТу214.', 'exact airport rights/variant/payload/date;own sales/retention;international fare/cost/cash','ИсторическоеSSJ100неявляетсяSJ100допуском;новаяinternationalzoneнеMCT','A-REN-06;A-REN-17','EXTENSION_GATE'),
 ('CR-REN-11','P07/P08/P09','joint','ВстроитьREN2–4парывобщуюсеть8–12уникальныхairportpairs;выбратьобщийG1/G2counterfactualпакет,неcложитьисторическиеpax/money.', 'versioned P/KEEP manifests with programme actions; shared markets; no duplicate flight inventories','ГотовностьStageAнеозначаетaccepted P06/финальныйпаспорт; independent engine acceptance pending','A-REN-11;A-REN-13','JOINT_RECOMPUTATION'),
 ('CR-REN-12','P05/P03','H-REN-08','NOZ/KEJ/BAX/TOF/TJM:сопоставитьавторскиеmodel estimates сobserved OD иexistingviaSVX/OVB;затемдорисоватьобоснованныелучи.', 'observed/estimated separated;monthlyOD/competitors;block/payload/full rotations','Осталисьусловными,неотсевпо500км/старомусчету/UNKNOWN','A-REN-07;A-REN-13','EXTENSION_INPUTS')]
table('comparison_requests.csv',[dict(request_id=a,owner=b,programmes=c,question_ru=d,required_fields=e,acceptance_boundary=f,assumption_id=g,status=h,
    unit='смrequired_fields',period='2027-01/2028-12',coverage='точечныезависимостипакетаREN',source_id='input_pins.json;additional_input_pins.json;sources.csv') for a,b,c,d,e,f,g,h in requests])

case=dict(city='Оренбург',airport='REN',stage='STAGE_A_COMPLETE_CONDITIONAL_DESIGNS',as_of=AS_OF,language='ru',
    current_rw_role={'confirmed':'published_RW_outstation_and_origin_market','not_confirmed':['existing_RW_base','RW_hub_in_REN','free_RW_tail','free_MRO_or_stands'],
        'source_ids':['REN-SCHEDULE-OUT','REN-SCHEDULE-IN','RW-REN-EVN26','RW-B2-PRIMARY']},
    principal_conclusion='Первым общим опытом сравнитьR1(ночевкаREN),E1(весьоборотSVX) иD1(лучшийдополнительныйпрямойресурсSVX) наG1. H1 отдельнаяпроверказащищеннойминиволнынаG2,необъявленныйпобедитель.',
    demand={'observed':'2025 airport>951000 services;domestic885500;international65600;direction shares UNKNOWN',
        'regional':'KZN/SVX/GOJ(лето);UFA/KUF наземныеальтернативы;другиепарыcoverage gaps',
        'long_distance':'MRV/AER/LED/SVO/OVB опубликованы;дальниеNOZ/KEJ/BAX/TOF модельные/черезSVX;неживойOD',
        'international':'summerRW-EVN;winterRT-ALA/IO-GYD + AYT/SSHcharters;MSQviaSVX/B2',
        'segments':'Туристическаясезонностьподдерживаетсяпродуктами. Business/VFR/corporate volume and contract UNKNOWN; промышленностьнепревращенавспрос.',
        'seasonality':'Неравномерныекалендари;GOJ/RGK/EVNлето;MRVзима;12месяцевOD/режим2027-28UNKNOWN'},
    operations={'runway':'2500x42;PCN41/R/B/X/T;CATI;H24published', 'parking':'22total;категория8местсRRJ95совместносдругимитипами;RWдоступUNKNOWN',
        'sj100_pd8':'допуск/нагрузка/ТО/crewUNKNOWN;отдельноотSSJ100SaM146','contracts':'SGHA/MRO/crew/stays/slots/fuel/launch/exitUNKNOWN',
        'winter':'заявленнаяподготовка2026невероятностьотказа;weather/Koverpublicationdaysнеhourslost',
        'bottlenecks':'MCT/багаж,peakground,two-long-line-daysH1,OMSovernight,actualreserve'},
    finance={'model':'толькообщееP06/P05/P04;локальнойденежноймоделинет','local_reference':'fuel141405rub/tбезVAT;handlingвevidence.csv;будущиеставкиUNKNOWN',
        'discount':'64%transitexpired2026-10-31;MRV50%ends2026-12-31;futureextensionUNKNOWN',
        'required_outputs':'переменныйвклад/полнаядельта/денежныепотоки/финансированиедоприбыли/условияостановки;сейчасNOT_RUN'},
    source_pins=PINS,shared_checkout={'git_mutations':False,'writes':'толькокаталогэтогопакета','colleague_fetch':'непроводился;общиевходыпользователязакрепленыпоexactSHA;неизменялисьобщиеupdates'},
    deliveries='P03D0/partial/delay/phased;активацияпослеoperationalready;SJ100нераньше2027H2поусловиюкейса;числопоставокненазначено',
    coverage='СамостоятельноеStageAлокальногоисследования;рыночная/ресурсная/финансоваяStageBнепройдена')
dump('case.json',case)

monthly=[]
for year in [2027,2028]:
    for m in range(1,13):
        monthly.append(dict(month=f'{year}-{m:02}',season='зима' if m in [12,1,2] else 'лето' if m in [6,7,8] else 'межсезонье',
            D0='KEEP;новыеборта0;retimeтолькопослеadmission',partial='G1кандидатпридоступности1line+acceptedreserve/crew',
            delay='KEEPдодоservice_entry;никакойвиртуальнойлетнейвыручки',
            phased='G1затемG2лишьеслиP03календарьдает2line+reserve/crew;необязательноеувеличение',
            earliest_new_sj100='нераньше2027-07' if year==2027 and m<7 else 'operational_ready UNKNOWN',
            demand='UNKNOWN',rate='UNKNOWN',status='scenario_activation_rule_not_accepted_calendar',
            unit='месяц;line-tails',period=f'{year}-{m:02}',coverage='все24месяца;непрогнозN(t)',source_id='P03;P05;условиекейса',assumption_id='A-REN-10;A-REN-18'))
table('monthly_activation_rules.csv',monthly)

dump('readiness.json',dict(stage_a='COMPLETE',stage_b='PENDING_SHARED_CALIBRATION_AND_ADMISSION',
    eligible_for='коммитпакетакоординатором;созданиесценариев/producerfragmentsпослеadmission',
    not_eligible_for=['экономическийвыборпобедителя','доказательство№2','годовыепассажиры/выручка/долярынка','livecapacity/договор/ресурс','выполнимыйсертифицированныйрасписанныйSJ100'],
    gates={'market':'P05notadmitted','cost':'local2026referencesonly;futurecontractunknown','operations':'diagnostictemplatesonly;reserve/crew/MRO/KEEPunknown',
        'engine':'P06implemented42authorchecksreported;independentacceptancepending;personalP06runNOT_RUN',
        'sources':'опубликованныедатированныепредложения;неполныепары/сезоны/ценыявноотмечены'},
    open_requests=[r[0] for r in requests],unresolved_hypotheses_not_rejected=[h['hypothesis_id'] for h in hyps if h['hypothesis_id']!='H-REN-ROLE']))

if __name__=='__main__':
    print('StageA artifacts built:',len(programmes),'programmes;',len(hyps),'hypotheses;',len(evidence),'evidence facts;',len(offers),'schedule rows')
