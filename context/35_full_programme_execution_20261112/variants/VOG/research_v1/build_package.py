#!/usr/bin/env python3
"""Воспроизводимая сборка локального Stage A; без денежных/choice-коэффициентов."""
import calendar
import csv
import hashlib
import importlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
ASOF = '2026-11-12'
PINS = json.loads((ROOT / 'source_pins.json').read_text())
def dump(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
def table(name, rows):
    assert rows, name
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (ROOT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows([{k: ('UNKNOWN' if v is None else v) for k,v in r.items()} for r in rows])
def sha(data):
    return hashlib.sha256(data).hexdigest()
def getblob(pin, path):
    return subprocess.check_output(['git', 'show', PINS['pins'][pin] + ':' + path])
def extract(pin, path, select, name):
    raw = getblob(pin, path)
    rows = []
    for i, r in enumerate(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))), 1):
        if select(r):
            rows.append({'source_data_row_1based': i, 'source_row_canonical_sha256': sha(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()), **r})
    table(name, rows)
    PINS['extracts'] = [x for x in PINS['extracts'] if x['local'] != name]
    PINS['extracts'].append({'pin': pin, 'commit': PINS['pins'][pin], 'path': path, 'source_sha256': sha(raw), 'local': name, 'selected_rows': len(rows), 'selection': 'Только строки, необходимые локальным опытам VOG'})
    return rows

AIRPORTS = {'VOG', 'SVX', 'KUF', 'MRV', 'AER', 'GSV', 'ASF', 'MCX', 'OMS', 'ZIA', 'SGC', 'CEK', 'LED', 'SVO', 'DME', 'OVB', 'KGD', 'GDZ', 'IAR'}
COORD_ROWS = extract('panel', 'data/processed/catchments.csv', lambda r: r['iata'] in AIRPORTS, 'inputs/airport_coordinates_selected.csv')
COORD = {r['iata']: (float(r['latitude_deg']), float(r['longitude_deg'])) for r in COORD_ROWS}
extract('P03', 'context/35_full_programme_execution_20261112/P03/assumptions_register.csv', lambda r: r['assumption_id'] in {'P03-A001','P03-A002','P03-A003','P03-A004','P03-A005','P03-A006'}, 'inputs/P03_proxy_assumptions.csv')
for file in ['common.py', 'operations.py']:
    path = 'context/35_full_programme_execution_20261112/P06/engine/' + file
    raw = getblob('P06', path)
    folder = ROOT / 'inputs' / 'p06_ops'
    folder.mkdir(exist_ok=True)
    (folder / file).write_bytes(raw)
    local = 'inputs/p06_ops/' + file
    PINS['extracts'] = [x for x in PINS['extracts'] if x['local'] != local]
    PINS['extracts'].append({'pin': 'P06', 'commit': PINS['pins']['P06'], 'path': path, 'source_sha256': sha(raw), 'local': local, 'selection': 'Два неизменённых модуля общей проверки ротаций; без toy fixtures'})
(ROOT / 'inputs' / 'p06_ops' / '__init__.py').write_text('')
sys.path.insert(0, str(ROOT / 'inputs'))
from p06_ops.operations import check_operations

SOURCES = [
 ('S-VOG-ANNUAL','Аэропорт Волгоград','https://t.me/airportvolgograd/287','2026-01-27','2025','пассажирские аэропортовые обслуживания; рейсы','airport/year','первичный опубликованный итог','sources/VOG_TG.html','Весь VOG; не конечные OD и не уникальные люди'),
 ('S-VOG-MONTH','Аэропорт Волгоград','https://airportvolgograd.ru/upload/temp/partners/Запрос предложений от 26.02.2026 с изм. 04.03.2026.pdf','2026-03-04','2025-01/2025-12','пассажирские аэропортовые обслуживания','airport/month/domestic-international','первичный документ через web text; локальный HTTP вернул JS-страницу','sources/web_tool_monthly.json','12 месяцев; отдельная строка ВВЛ-вылет; определения не равны OD'),
 ('S-VOG-WINTER','Аэропорт Волгоград','https://t.me/airportvolgograd/419','2026-10-26','2026-10-25/2027-03-27','опубликованное направление/перевозчик','airport/season/route','первичный анонс','sources/VOG_TG_CURRENT.html','Москва без аэропортовой разбивки; частоты/кресла/продажа UNKNOWN'),
 ('S-Y7-CS','NordStar','https://www.nordstar.ru/about/news/3357/','2024-01-09','2024 winter publication','оператор; тип ВС; дней/неделю','airport-pair/season','первичный исторический договорной анонс','sources/NORDSTAR_CODESHARE.html','SVX–VOG operator Y7 B737-800; будущие settlement/inventory UNKNOWN'),
 ('S-Y7-CS-EXT','NordStar','https://www.nordstar.ru/about/news/3624/','2024-07-08','2024 summer','оператор; дней/неделю','airport-pair/season','первичное историческое продолжение','sources/NORDSTAR_CODESHARE_EXT.html','Не подтверждает автоматическое действие договора в2027–2028'),
 ('S-RW-SUMMER','Red Wings','https://flyredwings.com/press/news/red-wings-budet-letat-iz-ekaterinburga-v-volgograd/','2026-06-10','2026 summer from2026-06-23','рейс/неделю; минут','airport-pair/season','индексированный первичный анонс; live HTTP410','sources/rw_summer_search_receipt.json','SVX–VOG SSJ100 1/нед,155мин; не подтверждение выполнения/зимы'),
 ('S-Y7-FARE','NordStar','https://www.nordstar.ru/passengers/conditions-fares/','UNKNOWN','as_of2026-11-12','кг; условия продукта','carrier/fare-brand','первичные текущие правила','sources/NORDSTAR_FARES.html','Эконом Выгодно без багажа; Легко23кг; не dated fare quote'),
 ('S-RW-SVX-BAG','Red Wings','https://flyredwings.com/koltsovo/','UNKNOWN','as_of2026-11-12','условия багажа','airport/transfer-rule','первичные правила','sources/RW_TRANSFER_SVX.html','Сквозная регистрация при условиях; не гарантия любого Y7/WZ interline/стыковки'),
 ('S-VOG-TECH','Минтранс РФ','https://mintrans.gov.ru/press-center/news/7546','2016-08-11','2016; часть работ planned for2018','м; мест стоянки','airport/project','первичный исторический источник','sources/web_tool_monthly.json','ВПП2800x45 получена;20стоянок тогда планировались, не текущая доступность RW'),
 ('S-VOG-LOCAL-RAIL','АО Волгоградтранспригород','https://volgogradtransprigorod.ru/press-centr/blog-kompanii/izmeneniya-v-raspisanii/izmenenie-raspisaniya-s-04-noyabrya-2026-g-po-03-dekabrya-2026-g-volgogradskaya-oblast','2026-10-26','2026-11-04/2026-12-03','местное время; минут','station-pair/dated-service','первичное расписание изменения','sources/VOG_GROUND_LOCAL.html','Аэропорт17:34→Волгоград1 18:06;32мин на одном поезде; не вся городская доступность'),
 ('S-VOG-ASF-RAIL','Приволжская ЖД/РЖД','https://t.me/priv_rzd_official/3185','2025-10-07','2025-10-18','опубликованные часы; поезд','station-pair/one-day excursion','первичный исторический турпродукт; не регулярный тариф','sources/VOG_GROUND_ASF.html','Волгоград05:58→Астрахань13:00; обратно18:00→23:09; часовой стандарт в посте не задан; длительность не вычислена'),
 ('S-VOG-GSV-RAIL','Яндекс Расписания','https://rasp.yandex.ru/train/volgograd--saratov','UNKNOWN','2026-11/2027-01','минут; дни следования','station-pair/dated-train','вторичный датированный timetable','sources/web_tool_batch_a.json','161С16/19/21ноября 409мин; это не VOG–GSV air time, не тариф'),
 ('S-VOG-TOURISM','Инвестиционный портал Волгоградской области','https://investvolga.volgograd.ru/territoriya-investitsiy/investitsionnye-nishi/','UNKNOWN','2025 context; read2026-11-12','описание сегмента; поездки','region/year/all-modes','официальный региональный контекст, не авиаOD','sources/VOG_TOURISM.html','Патриотический/семейный/автотуризм; источник не доказывает долю авиации или корпоративный блок'),
 ('S-VOG-H1','Интерфакс-Россия через АвиаПорт','https://www.aviaport.ru/news/passazhiropotok-aeroporta-volgograda-v-i-polugodii-snizilsya-na-12/','UNKNOWN','2026-01/2026-06','тыс аэропортовых пассажиров','airport/half-year','вторичный пересказ с арифметическим конфликтом','sources/web_tool_batch_e.json','652.1total против625.4dom+18.1intl=643.5; не принимать к demand calibration'),
 ('S-VOG-RW-HISTORY','Red Wings','https://flyredwings.com/autumn-sale-2025/','2025-09-16','2025-09-23/2026-03-28','доступное направление в акции','carrier/route/promotional-period','первичный исторический sales-list','sources/web_tool_batch_h.json','VOG–SGC иMCX–VOG; частоты/самолёт/выполнение не установлены'),
 ('S-VOG-BUS-HISTORY','Red Wings','https://flyredwings.com/flight-board/astana/','UNKNOWN','cached11September;2026 inferred from weekday/context','табло по двум направлениям; местные часы','airport-pair/dated-board','первичный cached board с временной неопределённостью','sources/web_tool_batch_g.json','WZ1649/1650 VOG–BUS; это не future route contract'),
 ('S-VOG-DISCOUNT','Аэропорт Волгоград','https://airportvolgograd.ru/upload/company_files/Положение по скидкам 2022 год.pdf','2021-12-28','положение2022; будущая применимость UNKNOWN','условия скидок','airport/policy','исторический документ; webread затем пустой; HTTP challenge','sources/web_tool_batch_d.json','Не использовать числовую скидку без действующей редакции/подписанного договора'),
 ('S-VOG-FARE-IND','Airports.ru','https://airports.ru/route/volgograd/','UNKNOWN','вылет2026-11-23 /2027-01-27 /2027-02-03; web as_of2026-11-12','RUB/пассажир/поездка, корзина UNKNOWN','airport-pair/date/displayed-from-price','вторичный кэшированный индикатор; не котировка inventory','sources/fare_search_receipt.json','Дата формирования цены и багаж UNKNOWN; не общий netfare'),
 ('S-PLAN','Общий план команды','git:982f13d9b6c378ed9581125ecc5c40f17dade6a3:context/34_full_programme_plan_20261112/variant_research_plan.json',ASOF,'план12.11.2026','гипотеза','hypothesis','закреплённый авторский вход','inputs/PLAN_VOG__variant_research_plan.json.json','C09,C19,C29 сохранены как происхождение, не очередь неизменных решений'),
]
source_rows=[]
for sid,org,url,pub,period,unit,grain,status,local,coverage in SOURCES:
    f=ROOT/local
    source_rows.append(dict(source_id=sid,organization=org,url=url,publication_date=pub,period=period,unit=unit,grain=grain,status=status,coverage=coverage,retrieved_at=ASOF,local_path=local,local_sha256=sha(f.read_bytes()) if f.exists() else 'UNKNOWN'))
for pin in ['panel','P00R','P02','P03','P04','P06']:
    source_rows.append(dict(source_id='S-'+pin,organization='Авторская модель команды' if pin=='panel' else 'Общий пакет '+pin,url='git:'+PINS['pins'][pin],publication_date=ASOF,period='Версия на exactSHA; исторические входы и диагностические сценарии разделены',unit='См. исходные таблицы',grain='pinned row; contract',status='pinned_input_not_live_acceptance',coverage='Только назначенные локальные extracts; source_pins.json',retrieved_at=ASOF,local_path='source_pins.json',local_sha256='manifest_with_per_blob_hashes'))
table('sources.csv',source_rows)

MONTH_SERIES={
 'domestic':[106511,92860,103715,114780,129698,145667,156187,153462,127246,110424,100103,94938],
 'international':[7404,5094,6644,7459,7024,11057,12212,12643,11518,12653,5831,5148],
 'domestic_departures':[55149,47258,51109,56444,65114,70461,76826,79353,64940,55546,50582,46090],
 'total':[113915,97954,110359,122239,136722,156724,168399,166105,138764,123077,105934,100086]}
monthly=[]
for kind,values in MONTH_SERIES.items():
    for m,v in enumerate(values,1):
        monthly.append(dict(row_id=f'VOG-2025-{m:02}-{kind}',metric=kind,value=v,unit='airport_passenger_movements' if kind!='domestic_departures' else 'departing_airport_passengers',period=f'2025-{m:02}',grain='VOG/month/'+kind,source_id='S-VOG-MONTH',source_locator='таблица пассажиропотока2025, строка '+kind,coverage='Все перевозчики VOG, не OD',status='published_history',days=calendar.monthrange(2025,m)[1],daily_mean=round(v/calendar.monthrange(2025,m)[1],3),not_for='Нельзя превращать в будущий спрос каждой пары или уникальных пассажиров RW'))
table('airport_monthly_2025.csv',monthly)
reconciliation={'monthly_sums':{k:sum(v) for k,v in MONTH_SERIES.items()},'press_release':{'total':1540280,'domestic':1435489,'international':104791},'source_document_totals':{'total':1540278,'domestic':1435591,'international':104687,'domestic_departures':718872},'rule':'Сохранить обе версии; для сезонной формы использовать полный месячный ряд без склейки с другими totals; P05 отдельно проверяет применимость к OD','h1_2026_secondary':{'claimed_total':652100,'domestic_plus_international':643500,'unreconciled_difference':8600,'admission':'Не использовать для калибровки спроса до первичной сверки'},'seasonal_daily_peak_trough_total':round(max(v/calendar.monthrange(2025,i)[1] for i,v in enumerate(MONTH_SERIES['total'],1))/min(v/calendar.monthrange(2025,i)[1] for i,v in enumerate(MONTH_SERIES['total'],1)),4),'source_ids':['S-VOG-MONTH','S-VOG-ANNUAL','S-VOG-H1'],'status':'Вычисление из опубликованных агрегатов; не прогноз2027–2028'}
dump('source_reconciliation.json',reconciliation)

ASSUMPTIONS=[]
def assumption(id,parameter,value,unit,basis,impact,sensitivity,refine,domain='UNKNOWN'):
    ASSUMPTIONS.append(dict(assumption_id=id,parameter=parameter,value=value,unit=unit,selected_by='Исследователь VOG/Sol6.1 xhigh',why=basis,range_or_unknown=domain,range_type='Явные точки/варианты сценария; не доверительный интервал',impact=impact,sensitivity=sensitivity,how_to_refine=refine,period='2027-2028 proposal',coverage='VOG local candidates',status='research_scenario_not_user_approved_numerical_input',source_id='S-P03' if id.startswith('A-VOG-BLOCK') else 'S-PLAN'))
assumption('A-VOG-BLOCK','Кинематическая длительность','0.5 + great_circle_km*k/750; k=1.1/1.2','block_h/flight','Точно повторён P03-A001/A003/A004/A005, исходник dceadc; координаты закреплены','Только необходимый ресурс и время шаблона','Обе точки k; daily limits6.5/8/10; реальные обходы могут выйти за них','P03 направленные типоспецифичные block times с ветром, маршрутом и запасными','Две диагностические точки, фактические границы UNKNOWN')
assumption('A-VOG-GEO','Геометрия','Haversine R=6371','km','Стандартная сферическая геометрия и pinned airport coordinates; не расстояние разрешённого трека','Сравнение обхода и длины плеч','Заменить на filed tracks; не выводить сертифицированную дальность','AIP/dispatch/P03')
assumption('A-VOG-FREQ','Дни/частоты пилота','см.programme_candidates иcalendar_monthly','RT/week/direction','1рейс/нед ограничивает возврат;2разнесённых рейса позволяют3/4ночи,3рейса уменьшают разрыв до2/3дней; не доказанный спрос','Количество рейсов/выбор продукта; нет договорного блока','P05 пересчитает1/2/3частоты на тех же рынках; изменить дни под нужный срок поездки','P05 date-preference/OD + реальные продажи', '1;2;3 — точки конструкции, не оценка оптимума')
assumption('A-VOG-SEASON','Сезонные режимы','winter Nov-Mar; shoulder Apr-May/Sep-Oct; peak Jun-Aug','calendar month','Месячный VOG2025 поддерживает летнюю неоднородность; роли месяцев — проектная группировка, не официальный сезон','Только условный календарь программы, не множитель спроса','Перестроить месяцы по OD; не переносить общий профиль механически','P05 airport-pair/month2025/2026 + forward bookings')
assumption('A-VOG-TURN','Разворот в диагностике',45,'minutes','Проверочный запас для последовательной ротации; норматив RW/тип/аэропорт неизвестен','Может сделать плотный шаблон невыполнимым','Проверка90мин и реальные минимумы отдельно','SGHA/типоспецифичная карта разворота','45;90 scenario points; verified bound UNKNOWN')
assumption('A-VOG-BANK','Окна защищённых стыковок','north arrive08:00Z;south depart09:30Z;return north15:30Z','UTC clock','Конструкция двух волн с90мин первым ожиданием; стыковочный норматив и договоры UNKNOWN','Позволяет проверить оба направления и пропущенную стыковку','MCT90/120 и позднее прибытие; требование к ночёвке при пропуске','RW airport/baggage/reprotection agreement','Не слот и не согласованный MCT')
assumption('A-VOG-RESOURCE','Рабочие самолёты','0/1/2 по кандидату; reserve separate','scenario tails','Ресурс, который запрашивает программа; не свободный парк RW','P03 должен применить одинаковые физические борта/даты ко всем альтернативам','P03 dedicated reserve1 и pooled reserve с измеренной реакцией; без повторного вычитания ТО','P03 tail-month, crew, MRO, резерв, донор/KEEP','Требование0/1/2; доступность UNKNOWN')
assumption('A-VOG-ENTRY','Ветви ресурса','действующий SSJ100 с донором; новый SJ100/ПД8 не раньше H2-2027; zero-new-Tu214','aircraft/date','Граница задания; service entry и количественный календарь только P03','Наш календарь — envelope, не обещание запуска; SJ доH2-2027 не активировать','План/частично/задержка/ноль новых; при нуле остаётся partner и отдельное решение о переносе SSJ','P03 fleet_calendar + commercial-entry evidence')
assumption('A-VOG-KEEP','Сохраняемые свои продажи','RW marketing Y7SVX; исторические MCX/SGC/BUS требуют actual2027KEEP','journeys/flight/settlement','Обнаруженная история и действующий published partner product; отсутствие в списке не обнуление','Запрет двойного учёта дохода, inventory и донорского ресурса','При new own SVX измерять вытеснение partner commission и своих пересадок','P02/P05/P04 dated booking and settlement ledger')
assumption('A-VOG-COST','Локальные цены/база/выход','UNKNOWN','RUB/service;RUB/base-month;cash dates','P04 localrate not extracted;2016rate и2022discount устарели; новая ставка не выдумана','Нет денежного победителя; передаются quantities и residual thresholds','P04 TH-OPTION, TH-FIXED, TH-LAUNCH, TH-FUNDING; совместный stress неизвестных','Действующие тарифы+RW SGHA, fuel, MRO, crew, запуск/выход/депозиты')
assumption('A-VOG-RESPONSE','Реакция конкурента','hold;restore_capacity;targeted_reprice;rebank — величины UNKNOWN','flights;gross RUB/journey','Y7 уже имеет SVX–VOG иcodeshare;S7/SU/DP/FV опубликованы, это основание тестировать реакцию, не прогноз её вероятности','Порядок вариантов может смениться','P02/P05 измеренный response family; не задавать безоснованный -10%','Исторические цены/частоты вокруг входов и общие флоты/слоты')
assumption('A-VOG-SEGMENT','Клиентские сегменты','туризм поддержан;корпоративный/деловой/VFR объём UNKNOWN','journeys/OD/month/segment','Туристический контекст регионального источника; промышленные предприятия не доказанный контракт','Нет долей захвата или гарантированного блока','Спрос по сроку поездки; доля наземных/непоездка; не двойной catchment','P05 surveys/ticketing + точные корпоративные обязательства')
assumption('A-VOG-LOC','Начальная позиция новой базы','SVX→VOG ferry в2027-01-01; exitVOG→SVX2028-12-31 для P30/P50','physical leg','Явное демонстрационное позиционирование, не реальные даты ввода','Две дополнительные рейсовые затраты; нельзя считать местную позицию бесплатной','Сдвинуть под фактический entry; учитывать возврат/депозиты при остановке','P03 same-tail positioning and donor calendar','Даты диагностики, не launch forecast')
assumption('A-VOG-CLOCK','Начало последовательной диагностической ротации','04:00UTC; первый setup ferry00:00UTC; exit после последнего прибытия + turn','UTC clock','04:00UTC даёт дневное начало на опорах SVX/VOG/ZIA; это нормализация шаблона, а не слот или измеренное предпочтение пассажиров','Время продажи, duty и доступность трансфера; особенно влияет на треугольники и ночёвку','Сдвиг окна и порядок плеч должен пересчитать P03/P05; проверка иных часов не выполнена','Датированные slots, crew/отдых и предпочтения дня поездки','Фактически допустимые часы UNKNOWN')
assumption('A-VOG-QUOTE','Год и lead публичной цены','23 ноября→2026 inferred; 27.01.2027/03.02.2027/19.01.2027 explicit; lead=departure−retrieval12.11.2026','year;calendar days','На экране ноябрьский день без года; год восстановлен из текущего контекста, даты2027 указаны явно','Это только календарный lead наблюдения; дата формирования цены и доступное место UNKNOWN','P02 должен повторить dated basket, меняя lead при одной дате поездки','Прямой quote с временем генерации, суммой багажа/сборов и source-specific year status','Не диапазон цены и не доверительный интервал')
table('assumptions.csv',ASSUMPTIONS)

E=[]
def evidence(id,claim,value,unit,period,grain,status,source_id,coverage,implication):
    E.append(dict(evidence_id=id,claim=claim,value=value,unit=unit,period=period,grain=grain,status=status,source_id=source_id,coverage=coverage,implication=implication,as_of=ASOF))
evidence('E-VOG-01','Общий аэропортовый поток2025',1540280,'airport_passenger_movements','2025','airport/year','published_history','S-VOG-ANNUAL','Все перевозчики; прибытие+вылет','Не уникальные поездки и не потенциальный спрос RW')
evidence('E-VOG-02','Полный месячный ряд2025',1540278,'airport_passenger_movements','2025','airport/month','published_history_conflict_preserved','S-VOG-MONTH','12месяцев, четыре метрики','Сезонный контекст; см.source_reconciliation.json, не самостоятельная P05 calibration')
evidence('E-VOG-03','Роль RW на VOG–SVX','partner-marketing;Y7 operating B737-800','role','2024 agreement;winter2026/27 corroboration','airport-pair/operating-vs-marketing','corroborated_published_not_contract_for2027','S-Y7-CS;S-Y7-CS-EXT;S-VOG-WINTER;S-P02','Не все продукты RW и не вся история VOG','Маркетинговое присутствие не SSJ ресурс и не RW база')
evidence('E-VOG-04','Анонс собственного SSJ100 RW летом2026','1/week from23June;155min','published_RT_frequency;minutes','summer2026','airport-pair/season','indexed_primary_live410','S-RW-SUMMER','Один сезон, не performance','Исторический опыт не нулевой; actual2026/inventory нужно запросить')
evidence('E-VOG-05','Зимняя опубликованная сеть','Moscow;LED;SVX;OVB;DXB;SSH','destinations','2026-10-25/2027-03-27','airport/season','published_offer_incomplete','S-VOG-WINTER','SU/S7/DP;FV/DP;Y7;S7;FZ;SM','Перечень не гарантирует отсутствие других рейсов; для Москвы нужны SVO/DME отдельные products')
evidence('E-VOG-06','Местная пригодность','ВПП2800x45 historical; currentSuperjet indexedboard; futureadmission UNKNOWN','m;aircraft type','2016;asof2026-11-12','airport/type','historical_and_partial_current','S-VOG-TECH;S-P03','20стоянок — проект2016, не свободные stands','Не доказаны SJ100/ПД8 допуск, RW MRO, ночью база, слоты или резерв')
evidence('E-VOG-07','Доступ из аэропорта по конкретному поезду',32,'minutes_station_to_station','2026-11-04/2026-12-03','dated_station_pair','published_offer','S-VOG-LOCAL-RAIL','6730/6729 17:34→18:06','Не подменять doorstep travel_time этим временем; длинный город/последний поезд влияют на выбор')
evidence('E-VOG-08','Наземная альтернатива Саратову',409,'minutes_station_to_station','16/19/21November2026 examples','dated_station_pair','secondary_published_timetable','S-VOG-GSV-RAIL','161С; местные UTC+3/+4 учтены','Короткий air-leg не автоматически не нужен; проверить доступ до GSV и travel date')
evidence('E-VOG-09','Туристический сегмент','историко-патриотический;семейный;автотуризм','segment_signal','2025 contextual','region/all_modes','source_supported_signal_not_air_demand','S-VOG-TOURISM','Нет OD/аэродоли/платёжеспособности','Для VOG inbound проверить3/4ночи и события; не придумывать contracted seats')
evidence('E-VOG-10','Прежние RW-продукты','VOG–SGC;MCX–VOG;VOG–BUS','historical sales/schedule signal','2025/early2026;cachedSep2026','airport-pair/product','historical_current_continuity_UNKNOWN','S-VOG-RW-HISTORY;S-VOG-BUS-HISTORY','Не подтверждает весь2026 или2027KEEP','Включить preservation/cannibalisation и север–юг/международную гипотезу')
evidence('E-VOG-11','Локальные коммерческие условия','UNKNOWN','contract/rate/slot','2027-2028','airport/RW/aircraft-variant','unknown','S-P03;S-P04;S-VOG-DISCOUNT','Fuel,handling,MRO,crew,stands,MCT,launch/exit','Параметризовать через P04 thresholds; не брать Уфу как ставкуVOG')
evidence('E-VOG-12','Сводка первого полугодия2026 не сходится',8600,'airport_passengers_unreconciled','2026-H1','airport/half-year','source_conflict','S-VOG-H1','652100 vs643500 component sum','Не нормировать2027спрос этим рядом')
table('evidence.csv',E)

H=[]
def hypothesis(n,title,signal,sources,mechanism,cf,test,ancestors,programmes,outcome,revisit):
    H.append(dict(hypothesis_id='H-VOG-'+n,title=title,signal=signal,source_ids=sources,mechanism=mechanism,counterfactual=cf,distinguishing_test=test,ancestorIDs=ancestors,programme_ids=programmes,outcome=outcome,evidence_scope='Stage A локальные источники/конструкция; общая экономика не принята',revisit_condition=revisit,assumption_ids=['A-VOG-KEEP','A-VOG-COST','A-VOG-RESOURCE','A-VOG-FREQ']))
hypothesis('01','Продажи через партнёра и узел SVX','Исторический codeshare подтверждён оператором; зимний airport анонс называетY7',['S-Y7-CS','S-VOG-WINTER','S-RW-SVX-BAG'],'Войти в локальный рынок без нового собственного борта; сравнить улучшение стыковокSVX и gross basket','Будущий KEEP с теми же partner products и новым ресурсом на иной программе','P00 vs P10: собственный RT должен покрыть потерю partner net settlement и альтернативный результат борта',['NEW_SOURCE_CS'],['P-VOG-00','P-VOG-10'],'условна из-за неизвестных settlement/inventory/protection; отправлена Stage B','RW/Y7 dated contract, fare basket и bookings')
hypothesis('02','Прямой рейс из SVX с сезонным расширением','Летний собственный анонс2026 и currentY7 предложение',['S-RW-SUMMER','S-P02'],'Добавить дни и прямой продукт с возвратом2/3/4ночи, не открывая VOG базу','P00 partner и лучший сопоставимый новый борт за пределамиVOG','Общий P05 pool; прирост конечных поездок/сегментов и P−KEEP, два gross baggage products',['AUTHOR_HUB_VOG','NEW_SOURCE_CS'],['P-VOG-10'],'сконструирована; рыночный исход условен','Seasonal route dates, own previous sales, entry calendar and opportunity set')
hypothesis('03','Радиальная база против W-оборота изSVX','ВПП и Superjet history поддерживают изучение, но RW-base не установлена',['S-VOG-TECH','S-P03'],'Те же плечи SVX–VOG иVOG–MRV с другим ночным местом дают иные часы и launch/fixed cost','P20:SVX–VOG–MRV–VOG–SVX с тем же одним рабочим tail','P30 противP20 при одинаковомtail/calendar/markets; учесть2ferry, crew,MRO,stand/reserve; TH-OPTION',['EC_H01','AUTHOR_HUB_VOG'],['P-VOG-20','P-VOG-30'],'условна из-за base/MRO/slot/demand полей; никакого отказа всему VOG','Подтверждённый доступ и положительный остаток до дополнительных затрат базы')
hypothesis('04','Защищённые пересадки вVOG без обязательной ночной базы','VOG географически соединяет часть Волги/Урала и южные плечи; ground/OD unknown',['S-PLAN','S-P03'],'Две согласованные ротации с северными входами и южными выходами продают cross-OD, каждое кресло одно','P41 прямые SVX–MRV иKUF–AER плюс локальныеVOG на тех же2tail иKEEP','P40/P41 +раскладка endpoint OD; MCT/защита/оба обратных направления; response; общий24month allocation',['C29','EC_H01','FRONT_GAP'],['P-VOG-40','P-VOG-41'],'сконструирована; геометрия/ротации условно проверены, спрос/договоры открыты','P05 connecting propensity, точные конкурентные стыковки, VOG transfer agreement')
hypothesis('05','Нижневолжский фидер против наземного подвоза','КороткиеVOG–GSV/ASF; поездVOG–Саратов6ч49 и отдельный экскурсионныйASF',['S-VOG-GSV-RAIL','S-VOG-ASF-RAIL','S-VOG-LOCAL-RAIL'],'Авиаподвоз может сокращать длинную комбинированную поездку, но локальная поездка конкурирует с поездом/авто','P50 airfeed против наземного feed и направления новогоtailP10/другойгород','Дверь–дверь с аэропортами; pool не удваивать междуGSV/ASF/VOG; цены/частоты/ночёвки',['C29','FRONT_GAP'],['P-VOG-50'],'условна;500км и наличие поезда не экономический отказ','Точный catchment itinerary/неттоцена, сезоны и общее распределение спроса')
hypothesis('06','Треугольник черезСамару','Уже зарегистрированC09; собственныйSVX–KUF нельзя вычеркнуть',['S-PLAN','S-panel'],'Один tail даёт KUF–VOG локальный продукт и трёхдневный возврат, оплачивая все3плеча','ПрямыеSVX–VOG/SVX–KUF изKEEP и альтернативаRTKUF–VOG','P60 Fri forward/Sun reverse; все6секторов/week и общие local/through demand pools',['C09','KIR_G4','EC_H02'],['P-VOG-60'],'сконструирована; не объявлена выгодной из-за одного дополнительного плеча','KEEP existing passenger commitments; directional airspace costs; local KUF–VOG demand')
hypothesis('07','Короткая поездкаVOG–MCX','Официальный historical sale list содержитMCX–VOG;C19 предлагаетZIAцепь',['S-VOG-RW-HISTORY','S-PLAN'],'ПродуктFri→Sun даёт2ночи вместо неудобного weekly возврата; не корпоративный блок','БудущийKEEP историческогоMCX продукта плюс прямой изMCX/другойбазы','P70 обеориентации треугольникаZIA–VOG–MCX; weekend clocks, range/airspace исвои продажи',['C19','KIR_PAIR_A','EC_H05'],['P-VOG-70'],'условна; точная действующаяMCX/VOGпродажа не найдена, не нулевой рынок','DatedMCX baseline and resource; compare independent directRT')
hypothesis('08','Север–юг черезVOG или прямойSGC–юг','RW2025/ранний2026продавалVOG–SGC, airportwinter2026это не подтверждает',['S-VOG-RW-HISTORY','S-VOG-WINTER'],'Проверить сохранениеVOG–SGC и сопряжение сMCX/MRV; нефтегазовый регион не гарантированный вахтовый контракт','Текущий/будущий собственный северныйKEEP и прямойSGC–MCX/MRV','Сначала datedbaseline/variant-range и monthlyOD, затем тотжересурс в P06; не складывать сP40',['NEW_HISTORY_SGC','C29:OMS>VOG>MCX'],[],'условна из-за конкретного missingbaseline/range; намеренно не изготовлен фиктивный executable schedule','ПодтверждённыеSGCдаты/типы/продажи и commonchoice; заменитьOMSфидер только отдельнойверсией')
hypothesis('09','МеждународныйVOG–BUS как добавочная ветвь','CachedRWboardWZ1649/50 и winterFZ/SM/летнийcharter конкурируют за leisure бюджет',['S-VOG-BUS-HISTORY','S-VOG-WINTER','S-VOG-ANNUAL'],'Сравнить восстановление локальногоBUS с темжеtail на domestic, включая зимнюю паузу и действующие свои продукты','ТотжеSSJ/SJресурс наP10/P20 либо международномKEEP; новыхTu214=0','P80 действительные права/track/тип/booking basket и baggage; экспорт package без притворной дальности',['NEW_SOURCE_BUS'],['P-VOG-80'],'условна; международнаяветвь не признана основнойстратегией','ТочныеBUSсезон/права/спрос/исходныйRWпродукт и range clearance')
dump('hypotheses.json',{'city':'VOG','hypotheses':H,'closure_rule':'У всех локальных гипотез объяснимый условный исход; missingStageB не означает rejection','unconditional_economic_rejections':[]})

PROGRAMMES=[]
def programme(id,title,role,resource,loops,ods,cf,anc,days,note):
    PROGRAMMES.append(dict(programme_id='P-VOG-'+id,title=title,role=role,status='STAGE_A_CONSTRUCTED_CONDITIONAL',period='2027-01/2028-12 nominal envelope; actualentry gating required',aircraft_branches=['existingSSJ100_with_donor','SJ100_PD8_separate_assumptions_after_P03_entry'],new_Tu214=0,working_tail_requirement=resource,reserve='Отдельный общий pool либо dedicated1 поP03; доступность/реакция UNKNOWN',rotation_templates=loops,endpoint_ODs=ods,counterfactual=cf,ancestorIDs=anc,frequency_rule=days,frequency_unit='departures_per_direction_per_week; triangle has1 per direction for Fri/Sun pair',sales_changes={'preserve':'Весь затронутый futureKEEP, включая own/partnerSVX, actualMCX/SGC/BUS и продажи донорского задания','add':'Только явно датированная дельта после reconciliation KEEP; proposed templates не доказанный прирост','move':'Физическийtail переносится только с donor opportunity/result; партнёрскийY7tail не переносится','reduce':'Ничего не сокращено по умолчанию; reduction требует конкретныхdatedKEEPflightIDs'},needed_shared_inputs=['P02 dated air/ground/connection basket, operator, dedup, slots','P03 same-tail availability/entry/donor/crew/MRO/range/reserve','P04 local rates/fullfixed/cash/exit/settlement; driver exports','P05 mutuallyexclusiveOD×month×travel-duration/choice/response','P06 accepted input bundle, inventory and futureKEEP','P09 best alternative outsideVOG, total8–12pair portfolio'],assumption_ids=['A-VOG-FREQ','A-VOG-SEASON','A-VOG-RESOURCE','A-VOG-ENTRY','A-VOG-KEEP','A-VOG-COST'],note=note))
programme('00','ПартнёрскийSVX и проверка стыковок','partner/outstation',0,[],['VOG–SVX;VOG–other viaSVX only ifsellable'],'KEEP partner unchanged vs ownflightP10',['H-VOG-01'],'ДействующиеY7Mon/Thu источникP02; никакихновыхчастотнеприсвоено','НовыеRWphysicaltails0 поопределению программы; marketingfee/cost UNKNOWN,не0. Защищённость конкретныхconnectionsUNKNOWN.')
programme('10','ПрямойSVX–VOG из существующегоузла','direct_existingbase',1,['SVX>VOG>SVX'],['VOG–SVX'],'P00 plus exactsame newtail opportunityset',['H-VOG-02'],'winter2:Tue/Fri;shoulder2:Tue/Fri;peak3:Tue/Fri/Sun','Дополнение/заменаpartner не решены; сравнить сохранениеpartner и cannibalisation.2/3частоты — пилот, не спрос.')
programme('20','W-оборот черезVOG без ночнойбазы','through/outstation',1,['SVX>VOG>MRV>VOG>SVX'],['SVX–VOG','VOG–MRV','SVX–MRV viaVOG ifprotected'],'P30 samelegs/tail; and directSVX–MRV plus localVOG under samefleet',['H-VOG-03'],'winter1:Fri;shoulder2:Tue/Fri;peak3:Tue/Fri/Sun','КаждыйRT сохраняетместоSVX; сквознаяпоездкаSVX–MRV не удваивает тариф. Сравнить с ужеимеющимсяdirect.')
programme('30','Одинрабочийtail с ночнойбазойVOG','radial_base',1,['VOG>SVX>VOG>MRV>VOG'],['VOG–SVX','VOG–MRV'],'P20, identical weeklysectors, plus positioning/launch differences',['H-VOG-03'],'КакP20','НочёвкапереведенавVOG; setup/exitferry explicit.Утренние часы отличаются; на одномtail не обещаныдвунаправленныестыковки.')
programme('40','ДвеволныVOG из двухсуществующихопор','protected_transfer_outstation',2,['SVX>VOG>MRV>VOG>SVX','KUF>VOG>AER>VOG>KUF'],['SVX–MRV','KUF–AER','SVX–AER','KUF–MRV','VOG–SVX/KUF/MRV/AER'],'P41 identicaltwo-tail/calendar and all affectedKEEP; other unuseddays remain opportunity',['H-VOG-04','C29'],'winter1:Sun;shoulder2:Wed/Sun;peak2:Wed/Sun','Северприбывает08:00Z,югвылет09:30Z,северназад15:30Z.ЧерезVOGпересадкаприусловииMCT/договора;свободныйKUFtailнеустановлен.')
programme('41','Прямыеюжныерейсы и локальныйVOG','matched_direct_control',2,['SVX>MRV>SVX (south days)','SVX>VOG>SVX (north days)','KUF>AER>KUF (south days)','KUF>VOG>KUF (north days)'],['SVX–MRV','KUF–AER','VOG–SVX','VOG–KUF'],'P40 on samephysicaltailavailability, responsepolicy and markets',['H-VOG-04'],'winter1:southSat/northSun;shoulder2:southTue/Sat,northWed/Sun;peaksame2','РазнесениеRTпоразнымдням устраняет искусственнотяжёлый8секторныйдень; более высокиеblockhours не скрыты.Объединённыекресла/ODпересчитать.')
programme('50','Опыт коротких фидеровНижнейВолги','radial_feeder_trial',1,['VOG>GSV>VOG>ASF>VOG'],['VOG–GSV','VOG–ASF','GSV–ASF viaVOG ifsellable; longerconnections separately'],'GroundviaVOG airport vsgrounddirect plus use same tailonP10/outsideVOG',['H-VOG-05','C29'],'winter0 plannedtrialclosed;shoulder1:Fri;peak2:Tue/Fri','Winter0 — решение толькоэтогопилота, не нулевойрынок.ДлялокальногоGSV–ASFгеометриянепроверяетготовностькпересадке; количествоспасённыхчасовбезdoor-to-doorUNKNOWN.')
programme('60','Самара–Волгоград: обратимаяцепь','triangle_existingbase',1,['Fri:SVX>KUF>VOG>SVX','Sun:SVX>VOG>KUF>SVX'],['SVX–KUF','KUF–VOG','VOG–SVX; through alternatives shareseats'],'KEEPdirectSVX–KUF andpartnerSVX–VOG plusdirectRTKUF–VOG alternative',['H-VOG-06','C09'],'Fri/Sun everyweek,1flightperdirectionperpair','Все6плеч/week;не называтьдвухчастотнымRTкаждойпары.Частота1длякаждогонаправленияможетнеподойтидатампоездки.')
programme('70','ДвухдневнаяпоездкаВолгоград–Дагестан','triangle_existingbase',1,['Fri:ZIA>VOG>MCX>ZIA','Sun:ZIA>MCX>VOG>ZIA'],['VOG–MCX weekend','ZIA–VOG','ZIA–MCX'],'FutureownMCX/VOGKEEP anddirectRTfromMCX withsamefleet',['H-VOG-07','C19'],'Fri/Sun everyweek,1flightperdirectionperpair','Сначалаpayload/airspace/ZIAcontracts;полнаяцепьусловная,включаетдлинноеZIA–MCX.Периодические2ночинеравныполномугодовомуспросу.')
programme('80','Батуми: дополнительныйсезонныйпродукт','international_extension',1,['HOST>VOG>BUS>VOG>HOST; HOST/positioning UNKNOWN'],['VOG–BUS'],'DomesticP10/P20 andactualinternationalKEEP, zero-new-Tu214',['H-VOG-09'],'peak2Tue/Fri;shoulder1Fri;winterclosed onlyasproposedpilot','Нет координат/типоспецифичногоblockдляBUSвназначенныхвходах,непридуман operationalfragment;launchrights/type/rangeUNKNOWN.Не выбранныйсамолёт/хост.')
dump('programme_candidates.json',{'city':'VOG','version':'research_v1','status':'StageA proposed components; NOT acceptedP06bundles','target':'Общаясеть8–12уникальныхairportpairs на конец2028;ниодинлокальныйпакетненазванобщейсетью','normalisation':'Одинаковыйдоступныйресурс,внешнийсценарий,marketversion,choice/cost/response иfutureKEEP;невыравниватьскрытофактическииспользованныеblockhours','delivery_scenarios':['P03planphased','P03partial','P03delay','P03nonew;partner0newtails andexplicitexistingSSJdonorbranch'],'programmes':PROGRAMMES})

def distance(a,b):
    la,lo=map(math.radians,COORD[a]);lb,lob=map(math.radians,COORD[b]);x=math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin((lob-lo)/2)**2
    return 6371*2*math.atan2(math.sqrt(x),math.sqrt(1-x))
def duration(a,b,k):
    return math.ceil((0.5+distance(a,b)*k/750)*60)
geos=[]
for a,b in [('SVX','MRV'),('KUF','AER'),('KUF','MRV'),('SVX','AER'),('GSV','ASF'),('OMS','MCX')]:
    direct=distance(a,b);via=distance(a,'VOG')+distance('VOG',b)
    geos.append(dict(origin=a,destination=b,via='VOG',great_circle_direct_km=round(direct,1),via_distance_km=round(via,1),geometric_detour_ratio=round(via/direct,4),unit='km;ratio',period='geometry;not operatingperiod',status='calculated_geometry_not_range_clearance',coverage='Airportcoordinates; noactualairspace',source_id='S-panel',assumption_id='A-VOG-GEO;A-VOG-BLOCK'))
table('geometric_diagnostics.csv',geos)

def season(m):return 'peak' if m in [6,7,8] else 'winter' if m in [11,12,1,2,3] else 'shoulder'
def loops_for(pid,dt):
    # ISO weekdays. Each tuple is (tail, airport chain, alignmentmode).
    dow=dt.isoweekday();ss=season(dt.month)
    if pid=='P-VOG-10':return [('T1',['SVX','VOG','SVX'],'sequential')] if dow in ([2,5,7] if ss=='peak' else [2,5]) else []
    if pid in ['P-VOG-20','P-VOG-30']:
        days=[5] if ss=='winter' else [2,5,7] if ss=='peak' else [2,5]
        chain=['SVX','VOG','MRV','VOG','SVX'] if pid.endswith('20') else ['VOG','SVX','VOG','MRV','VOG']
        return [('T1',chain,'sequential')] if dow in days and dt!=date(2027,1,1) else []
    if pid=='P-VOG-40':return [('T1',['SVX','VOG','MRV','VOG','SVX'],'bank'),('T2',['KUF','VOG','AER','VOG','KUF'],'bank')] if dow in ([7] if ss=='winter' else [3,7]) else []
    if pid=='P-VOG-41':
        north=[7] if ss=='winter' else [3,7];south=[6] if ss=='winter' else [2,6]
        if dow in north:return [('T1',['SVX','VOG','SVX'],'sequential'),('T2',['KUF','VOG','KUF'],'sequential')]
        if dow in south:return [('T1',['SVX','MRV','SVX'],'sequential'),('T2',['KUF','AER','KUF'],'sequential')]
        return []
    if pid=='P-VOG-50':return [('T1',['VOG','GSV','VOG','ASF','VOG'],'sequential')] if dow in ([] if ss=='winter' else [2,5] if ss=='peak' else [5]) else []
    if pid=='P-VOG-60':return [('T1',['SVX','KUF','VOG','SVX'] if dow==5 else ['SVX','VOG','KUF','SVX'],'sequential')] if dow in [5,7] else []
    if pid=='P-VOG-70':return [('T1',['ZIA','VOG','MCX','ZIA'] if dow==5 else ['ZIA','MCX','VOG','ZIA'],'sequential')] if dow in [5,7] else []
    return []
def z(dt):return dt.isoformat().replace('+00:00','Z')
def make_flights(pid,k,turn):
    rows=[];n=0
    def add(tid,a,b,start,end,action='proposed'):
        nonlocal n;n+=1
        rows.append(dict(flight_instance_id=f'{pid}:{n:05}',schedule_id=pid,operator='RW_SCENARIO',flight_number=f'PROP{n}',origin_airport=a,destination_airport=b,departure_utc=z(start),arrival_utc=z(end),aircraft_variant='SSJ100_ANALOGUE_UNCALIBRATED',seats=None,technical_blocked_seats=None,saleable_seats=None,physical_adjacent_leg=True,scheduled_status=action,source_status='scenario',source_period='2027-2028 nominalcalendar',assumption_id='A-VOG-BLOCK;A-VOG-FREQ;A-VOG-ENTRY;A-VOG-CLOCK',distance_km=round(distance(a,b),3),project_network=True,tail=tid))
    dt=date(2027,1,1)
    if pid in ['P-VOG-30','P-VOG-50']:
        start=datetime(2027,1,1,0,tzinfo=timezone.utc);add('T1','SVX','VOG',start,start+timedelta(minutes=duration('SVX','VOG',k)))
    while dt<=date(2028,12,31):
        for tid,chain,mode in loops_for(pid,dt):
            midnight=datetime.combine(dt,datetime.min.time(),timezone.utc)
            now=midnight+timedelta(hours=8)-timedelta(minutes=duration(chain[0],chain[1],k)) if mode=='bank' else midnight+timedelta(hours=4)
            for i,(a,b) in enumerate(zip(chain,chain[1:])):
                if mode=='bank' and i==1:now=max(now,midnight+timedelta(hours=9,minutes=30))
                if mode=='bank' and i==3:now=max(now,midnight+timedelta(hours=15,minutes=30))
                end=now+timedelta(minutes=duration(a,b,k));add(tid,a,b,now,end);now=end+timedelta(minutes=turn)
        dt+=timedelta(days=1)
    if pid in ['P-VOG-30','P-VOG-50']:
        last=max((datetime.fromisoformat(f['arrival_utc'].replace('Z','+00:00')) for f in rows if f['arrival_utc'].startswith('2028-12-31')),default=datetime(2028,12,31,4,tzinfo=timezone.utc))
        start=last+timedelta(minutes=turn);add('T1','VOG','SVX',start,start+timedelta(minutes=duration('VOG','SVX',k)))
    return rows

monthly_calendar=[];op_results=[];flights_export=[];driver_rows=[]
for p in PROGRAMMES:
    pid=p['programme_id']
    if pid in ['P-VOG-00','P-VOG-80']:continue
    nominal=make_flights(pid,1.1,45)
    for f in nominal:flights_export.append({'programme_id':pid,**f,'unit':'physical_proposed_leg;clockUTC;km','period':f['departure_utc'][:7],'coverage':'Календарь конструкторский;flightnot admitted;seatsUNKNOWN','status':'scenario_NOTinventory','source_id':'S-P03;S-panel'})
    for year in [2027,2028]:
        for m in range(1,13):
            month=f'{year}-{m:02}';fs=[f for f in nominal if f['departure_utc'].startswith(month)]
            bh=sum((datetime.fromisoformat(f['arrival_utc'].replace('Z','+00:00'))-datetime.fromisoformat(f['departure_utc'].replace('Z','+00:00'))).total_seconds()/3600 for f in fs)
            monthly_calendar.append(dict(programme_id=pid,month=month,season=season(m),proposed_physical_legs=len(fs),proxy_block_hours=round(bh,3),working_tails_requested=p['working_tail_requirement'],physical_available_tails='UNKNOWN',activated_leg_count='UNKNOWN',seats='UNKNOWN',passengers='UNKNOWN',unit='legs/month;block_h/month;tails',period=month,status='scenario_envelope_NOTannualforecast',coverage='Датированный подсчёт календаря, не weekly×52;SJentrymaskобязателен',source_id='S-P03;S-panel',assumption_id='A-VOG-FREQ;A-VOG-SEASON;A-VOG-ENTRY;A-VOG-BLOCK'))
            for airport in sorted({x for f in fs for x in [f['origin_airport'],f['destination_airport']]}):
                departures=[f for f in fs if f['origin_airport']==airport];arrivals=[f for f in fs if f['destination_airport']==airport]
                driver_rows.append(dict(programme_id=pid,month=month,airport=airport,aircraft_variant='SSJ100_ANALOGUE_UNCALIBRATED',departures=len(departures),arrivals=len(arrivals),departure_block_hours=round(sum((datetime.fromisoformat(f['arrival_utc'].replace('Z','+00:00'))-datetime.fromisoformat(f['departure_utc'].replace('Z','+00:00'))).total_seconds()/3600 for f in departures),3),MTOW_t='UNKNOWN',fuel_t='UNKNOWN',departing_local_pax='UNKNOWN',transfer_passengers='UNKNOWN',stand_hours='UNKNOWN',rate='UNKNOWN',unit='departures;arrivals;block_h;otherdriversUNKNOWN',period=month,status='scenario_quantities_only',coverage='P04drivercandidates;feeincidencerequiresP04mapping',source_id='S-P03;S-P04',assumption_id='A-VOG-COST;A-VOG-BLOCK'))
    for k in [1.1,1.2]:
        for turn in [45,90]:
            fs=make_flights(pid,k,turn)
            for limit in [6.5,8,10]:
                initials={'T1':'SVX','T2':'KUF'}
                if pid=='P-VOG-70':initials['T1']='ZIA'
                tails=[dict(aircraft_id=t,variant='SSJ100_ANALOGUE_UNCALIBRATED',transfer_date=None,service_entry_date=None,available_from=None,available_to=None,initial_location=initials[t],turn_minutes=turn,reserve_intervals=None,maintenance_intervals=None,crew_windows=None,max_daily_block_hours=limit,assumption_id='A-VOG-RESOURCE;A-VOG-ENTRY;A-VOG-TURN') for t in sorted({f['tail'] for f in fs})]
                bundle={'context':{'period_start':'2027-01','period_end':'2028-12'},'resource_operators':['RW_SCENARIO'],'flights':[{k:v for k,v in f.items() if k!='tail'} for f in fs],'fleet_calendar':tails,'assignments':[dict(flight_instance_id=f['flight_instance_id'],aircraft_id=f['tail'],crew_id=None,action='propose',assumption_id='A-VOG-RESOURCE') for f in fs]}
                result=check_operations(bundle)
                # No money/choice/full-engine call; collapse repeating unknowns, preserve all errors.
                op_results.append(dict(programme_id=pid,route_factor=k,turn_minutes=turn,max_daily_block_hours=limit,status=result['status'],errors=result['errors'],error_count=len(result['errors']),unknown_field_families=['seat_inventory','tail_transfer/service_entry/availability','crew','maintenance','reserve'],unknown_count=len(result['unknowns']),flight_count=len(fs),dispatch_ready=False,claim_scope='Только неизменённый P06.check_operations на полном24monthноминальномкалендаре;непровереныспрос,legaladmission,слоты,MCT,range,actualcrew/MRO',source_id='S-P06',assumption_ids=['A-VOG-BLOCK','A-VOG-TURN','A-VOG-RESOURCE','A-VOG-ENTRY']))
table('calendar_monthly.csv',monthly_calendar)
table('proposed_flight_calendar.csv',flights_export)
table('cost_driver_requests.csv',driver_rows)
dump('operations_checks.json',{'engine_commit':PINS['pins']['P06'],'function':'check_operations; NOT full evaluate/compare','independent_engine_acceptance':'pending; этаработанеобщийcodeaudit','calendar_scope':'2027-01-01..2028-12-31 constructed datedenvelope','results':op_results})

M=[]
for p in PROGRAMMES:
    pid=p['programme_id']
    pairset=set()
    if pid not in ['P-VOG-00','P-VOG-80']:
        for f in make_flights(pid,1.1,45):pairset.add(tuple(sorted([f['origin_airport'],f['destination_airport']])))
    if pid=='P-VOG-00':pairset.add(('SVX','VOG'))
    if pid=='P-VOG-80':pairset.add(('BUS','VOG'))
    for a,b in sorted(pairset):
        nominal=[f for f in flights_export if f['programme_id']==pid and {f['origin_airport'],f['destination_airport']}=={a,b}]
        M.append(dict(programme_id=pid,origin_airport=a,destination_airport=b,market_id='AIR:'+a+':'+b,pair_kind='unique_undirected_airport_pair;directedlegsindatedcalendar',published_baseline='Y7published+RWmarketing;RWsummerownhistory' if {a,b}=={'SVX','VOG'} else 'historicalRWsales;currentfrequencyUNKNOWN' if {a,b}=={'VOG','MCX'} else 'UNKNOWN;notzero',keep_flights='UNKNOWN_future_datedKEEP',proposed_legs_2027_2028=len(nominal) if nominal else 'UNKNOWN_notconstructed',actual_additions='UNKNOWN_untilKEEPbinding',preserve_own_sales='ALLaffectedfutureKEEP',reduced_own_sales='NONEauthorised;notassumedzero',source_id='S-P02;S-VOG-WINTER;S-VOG-RW-HISTORY;S-panel',unit='legs;uniquejourneys;passengersegments',period='2027-2028',coverage='Не competitorcomplete;futureKEEPpending',status='proposed_delta_requiresreconciliation',assumption_id='A-VOG-KEEP;A-VOG-FREQ',related_ODs=';'.join(p['endpoint_ODs'])))
table('market_deltas.csv',M)

REQUESTS=[
 ('R-VOG-01','P02/P05/P04','P00/P10','DatedY7/WZoperator/inventory/allotment,netsettlement,bag20/23kgprice,protectedSVXconnections','WZmarketing иY7physicalодинinventory;выручкупартнёранеприсваиватьRW','СохранятьpartnerKEEP;никакогоownfreeSSJ','S-Y7-CS;S-VOG-WINTER','НовыйownRTлучшеpartnerлишьпослепересчёта lostcommission/choice/fullcost'),
 ('R-VOG-02','P05','Все','airport-pair/month2025/2026potentialOD,datepreference,segmentation,ground/outside,catchmentdedup','СогласоватьairportmovementsсendpointOD;показатьmapping,notmultiplytraffic','Нетбезусловныхденег/загрузки/долирынка','S-VOG-MONTH;S-VOG-TOURISM','Можетсменитьчастотыиотбор;seasonalshapeнеавтоматическаядлякаждойпары'),
 ('R-VOG-03','P03','P20/P30/P40/P41/P50/P60/P70','samephysicaltailcalendar,donorflightIDs,entry,mro,crew,reserve,recovery,airspace/payload,typeadmission','SSJ100 иSJ100/ПД8раздельно;поставка/ввод/свободаресурса;plan/partial/delay/zero','Envelopeвключаетдоentryрейсытолькокаксценарнуюконструкцию','S-P03','Невыполнимыйшаблонисправить/сравнитьменьшиечастоты,неотвергатьгород'),
 ('R-VOG-04','P04','P30/P50','VOGSGHA,fuelrate,MTOWfee,standnight,crewaccommodation,baseMRO,startup/exit,deposits','Локальныеставкииинцидентность;обязательствапо24month/terminal;VATbasis','Тарифы2016 иdiscount2022 неприменятькак2027rate','S-P04;S-VOG-DISCOUNT','TH-OPTION=deltaheadroombase;TH-FIXED/LAUNCH/FUNDING;небратькаждыйunknownпооотдельномуmax'),
 ('R-VOG-05','P02/P03/P05','P40/P41','MCT/steriletransfer/baggage/reprotectionagreement;datedbothdirectionalternatives;competitorresponseresource','P40общие2tailvsP41;endpointODнеравенчислусегментов','Непроданнаястыковканедобавляетпоток;selftransferотдельныйproduct','S-RW-SVX-BAG;S-VOG-WINTER','Проверитьнеттопреимуществоbanksoverdirect,missedconnectioncashandrecovery'),
 ('R-VOG-06','P02/P05','P50/C29','VOG/GSV/ASF door-to-door rail/bus/car datefare,frequency,access,bags,overnights','Каждыйcitydemandpoolодин;airportchoicewithinpool;станциянетотжеаэропорт','Неназначатьgroundshare/valueoftimeбезP05','S-VOG-GSV-RAIL;S-VOG-ASF-RAIL;S-VOG-LOCAL-RAIL','КороткийfeederможетпройтидлядальнейODиотказатьсядляlocal;500кмнеправилоотказа'),
 ('R-VOG-07','P02/P03/P05','P60/C09','РеальныйSVX–KUFKEEP иVOG/KUFfare/return;alltrianglelegs','Тотжеборт/дни;grosschoiceprice/netjourneyfareonce','Неподменять6секторовстоимостью1новогоплеча','S-PLAN;S-panel','СравнитьсdirectRT испецифичнымипотеряннымипродажами'),
 ('R-VOG-08','P02/P03/P05','P70/C19;H08','DatedVOG–MCX/SGCownhistory/currentKEEP,type,ranges,exactFriday/Sundayreturn','Существующиепродажисохранить;нипроходящаяпосадканикартыбезdatesнефизическиеlegs','Историческийsale-listнеcurrentflight','S-VOG-RW-HISTORY','СеверныйфидерSGC/OMS сравнитьсdirectsouthпристандартныхcommoninputs'),
 ('R-VOG-09','P02/P03/P04/P05','P80','VOG–BUSrights,type/block/airspace,HOST/positioning,seasonalODandfare,existingRWcommitments','Zero-newTu214;comparisonagainstsameSSJ/SJresource','НеиспользоватьFZ/SMtotalкакBUSdemand','S-VOG-BUS-HISTORY;S-VOG-WINTER','Internationalдобавочнаяветвь,небезусловноеназначениеtail'),
 ('R-VOG-10','P09/P06','Все','Лучшийmatchedalternativeвнегорода;futureKEEP;8–12pairjointnetwork;marketshareadapter','Полныеbundleswithsameversions;совместныйrerun,cannibalisationinventorysingle','Не складыватьавторскиеденьгиилирезультатылокальныхгородов','S-P06;S-PLAN','Passengerjourneysvssegments,revenues,incrementalresult,cashfundingseparate'),
 ('R-VOG-11','P02/P05','monthlycalibration','Первичный2026H1airportreport иопределенияmonthly2025revision','652.1тыснеравно625.4+18.1;2025splitconflict','Сохранитьверсии;нетненазваннойправки','S-VOG-H1;S-VOG-ANNUAL;S-VOG-MONTH','Неиспользоватьконфликтдляроста/сниженияODпрогноза'),
]
table('comparison_requests.csv',[dict(request_id=id,owner=owner,programmes=programmes,required_input=inp,acceptance_test=test,interim_rule=rule,source_id=source,decision_impact=impact,unit='inputcontract;seespecificfield',period='2027-2028 withhistory2025/26',coverage='VOG/local→commoncomparison',status='StageB_required_not_cityrejection',assumption_id='A-VOG-KEEP;A-VOG-RESOURCE;A-VOG-COST') for id,owner,programmes,inp,test,rule,source,impact in REQUESTS])

dump('case.json',dict(city='Волгоград',airport='VOG',icao='URWW',language='ru',as_of=ASOF,stage='A_LOCAL_RESEARCH_AND_PROGRAMME_CONSTRUCTION_COMPLETE',current_role={'established':'Пункт сети и партнёрских продаж Red Wings; исторические собственные продукты и летний собственный анонс2026','not_established':['действующаябазаRW','защищённыйхабVOG','свободныйRWtail','текущийRWcontractMRO/stands/slots','SJ100/ПД8typeadmission'],'evidence':['E-VOG-03','E-VOG-04','E-VOG-10']},demand_basis={'available':'2025 airport-month и первичныйseasonaloffer;точечныеhistoricalsales','unknown':'OD×month,netfare,bookingprofile,corporate/VFRsplit,groundcapture','warning':'Суммаairportpax неuniquejourneys,catchmentpop1349515—авторскийproxy сUNKNOWNграницами,неairOD'},source_pins='source_pins.json',hypotheses='hypotheses.json',programmes='programme_candidates.json',comparisons='comparison_requests.csv',results_scope='Нетденежногопобедителяилидоказанногоростадоли;conditionaloperationsнеlegaldispatch',economic_method='ЕдиныйP05/P06;толькоP04drivers/thresholds',programme_priority=['P00/P10:partner-vs-own','P20/P30:base-vs-exactlegs','P40/P41:bank-vs-direct','P50:shortfeeder-vs-ground','P60/C09 andP70/C19;H08/H09asconditionalextensions'],priority_basis='Доступныепервичныеsignals иmatchedcontrols,аснедоказанныйнизкийscoreили500км'))

dump('readiness.json',dict(stage_a='COMPLETE_LOCAL_RESEARCH_AND_CONSTRUCTION',stage_b='PENDING_SHARED_INPUTS_AND_ACCEPTANCE',accepted_for_economic_ranking=False,local_operations='P06.check_operationsrun;conditional/infeasibleunderexplicitproxies;notdispatch',demand_calibration='P05_NOT_AVAILABLE',financial_results='NOT_RUN_noacceptedP05/fullcostKEEP',market_share='NOT_RUN_noacceptedmetricadapter',airport_admission='PARTIAL_HISTORY_ONLY;SJ100_PD8_UNKNOWN',competition='PartialdatedY7/seasonalofficialnetwork;notcompleteinventory',requirements_open=[r[0] for r in REQUESTS],hypotheses_count=len(H),programme_count=len(PROGRAMMES),annualisation='Нетweek×52;конструкторскийкалендарь24месяцевпосчитанподатам,непрогнозгодовойсети',scope='ПолезныйStageAзавершён;общийкейс/экономика/финальныйвыборнеобъявленызавершёнными'))
dump('handoff.json',dict(package='VOG/research_v1',status='StageA_complete_StageB_requests_explicit',write_boundary=str(ROOT),git_mutations='NONE',shared_inputs='exactgitshowpins;source_pins.json',usable_findings=['Y7operatesSVX–VOGhistoricalcodeshare,currentwintercorroboration;WZmarketingnotfreeSSJ','12month2025primaryairportserieswithversionconflict','9localhypotheses,10programmes,full24monthproposedenvelopesandP06operations','MatchedP20/P30 andP40/P41;shortfeeder/surface/C09/C19/SGC/BUSlineage'],do_not_infer=['RWVOGbase','availablefleet/reserve','currentbookinginventory','confirmedfutureSJ100PD8costs/admission','positiveprofit/payback/marketshare','currentSGC/MCX/BUScontinuityfromhistoricallist'],stage_b_requests='comparison_requests.csv',coordinator_actions=['Принятьsourcepins,свестиP02dedup/KEEP иP05calibration','P03наложитьполныйentry/donor/MRO/crewcalendar иlegalrange','P04оценитьdriversиjointthresholds,contractfees/cash/exit','P06собратьполныеacceptedP/KEEPbundles;P09общая8–12pairсетьиalternativeoutsideVOG'],manifest='output_manifest.json',reproduce='PYTHONDONTWRITEBYTECODE=1 python3 '+str(ROOT/'build_package.py')))
dump('source_pins.json',PINS)
print(json.dumps({'hypotheses':len(H),'programmes':len(PROGRAMMES),'proposed_flights':len(flights_export),'operation_cases':len(op_results),'infeasible_cases':sum(x['status']=='INFEASIBLE' for x in op_results),'conditional_cases':sum(x['status']=='CONDITIONAL' for x in op_results),'source_reconciliation':reconciliation},ensure_ascii=False))
import runpy
runpy.run_path(str(ROOT/'finish_package.py'),run_name='__main__')
