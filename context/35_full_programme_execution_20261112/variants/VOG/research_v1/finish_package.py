"""Локальные дополнения, контроль происхождения и manifest без Git-операций."""
import csv
import hashlib
import json
import re
import io
import subprocess
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

R = Path(__file__).resolve().parent
def read(name): return json.loads((R/name).read_text())
def rows(name): return list(csv.DictReader((R/name).open()))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,obj): (R/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def table(name,data):
    keys=list(dict.fromkeys(k for row in data for k in row))
    with (R/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(data)

source_rows=rows('sources.csv')
source_rows.append(dict(source_id='S-FZ-PRODUCT',organization='flydubai',url='https://www.flydubai.com/ru-ru/cheap-flights/flights-from-volgograd-to-dubai/',publication_date='UNKNOWN',period='2026-11 published week; 2026/27 displayed monthly from-prices',unit='RUB/journey;local clocks;minutes',grain='airport-pair/month/displayed product',status='Первичный публичный продукт; не dated basket quote',coverage='VOG–DXB FZ962/FZ961; дни выполнения в текстовой сетке не различены',retrieved_at='2026-11-12',local_path='sources/web_competition.json',local_sha256=sha(R/'sources/web_competition.json')))
source_rows.append(dict(source_id='S-VOG-DISRUPTION',organization='Аэропорт Волгоград',url='https://t.me/airportvolgograd/417',publication_date='2026-10-23',period='2026-10-23',unit='Сообщение об изменении расписания',grain='airport/day/disruption notice',status='Первичный факт внешнего нарушения расписания',coverage='Ограничения московского узла повлияли на VOG; не доказательство закрытия VOG/числа часов',retrieved_at='2026-11-12',local_path='sources/VOG_TG_CURRENT.html',local_sha256=sha(R/'sources/VOG_TG_CURRENT.html')))
table('sources.csv',source_rows)

offers=[]
def offer(id,org,o,d,period,freq,flight,typ,clock,src,coverage,baggage='UNKNOWN',operator='UNKNOWN'):
    offers.append(dict(offer_id=id,carrier_label=org,operator=operator,origin_airport=o,destination_airport=d,period=period,as_of='2026-11-12',published_frequency=freq,flight=flight,aircraft=typ,clock_local=clock,physical_seats='UNKNOWN',open_seats='UNKNOWN',bag_policy=baggage,dated_fare_RUB='UNKNOWN',booking_lead='UNKNOWN',unit='departures/direction/week;clock_local;seats;RUB/journey',grain='airport_pair/explicit_source_interval',status='published_offer_not_inventory',coverage=coverage,source_id=src,assumption_id='A-VOG-KEEP;A-VOG-RESPONSE'))
offer('VOG-O01','Y7/WZ marketing','SVX','VOG','2026-10-26/2026-12-28 source year inferred by P02','2 Mon/Thu','Y7951;historical WZ codeshare','B737','17:15→17:55','S-P02;S-Y7-CS;S-VOG-WINTER','P02 product P02-ca16cee95fe21745; source table row62; exact legal operator/current settlement needs confirmation','Действующая корзина по тарифу; historic23kg не универсальная норма2026','NordStar: primary2024; currentseason independently corroborated')
offer('VOG-O02','Y7/WZ marketing','VOG','SVX','2026-10-26/2026-12-28 source year inferred by P02','2 Mon/Thu','Y7952;historical WZ codeshare','B737','19:25→23:50','S-P02;S-Y7-CS;S-VOG-WINTER','P02 product P02-6e0e3830c8c02244; source table row70;145min with UTC+3/+5','Эконом Выгодно:без багажа;Легко23kg, current fare amount unknown','NordStar: primary2024; currentseason independently corroborated')
offer('VOG-O03','Red Wings','SVX','VOG','с23.06.2026 летний сезон','1 Tue','UNKNOWN','SSJ100','11:40→UNKNOWN;return15:35local','S-RW-SUMMER','Официальный индексированный анонс155min,live410; не выполнение/план2027','UNKNOWN','Red Wings announced own')
for n,(o,d,carrier) in enumerate([('VOG','MOW_UNRESOLVED','Аэрофлот;S7;Победа'),('VOG','LED','Россия;Победа'),('VOG','OVB','S7'),('VOG','DXB','flydubai'),('VOG','SSH','Air Cairo')],4):
    offer(f'VOG-O{n:02}',carrier,o,d,'2026-10-25/2027-03-27','UNKNOWN','UNKNOWN','UNKNOWN','UNKNOWN','S-VOG-WINTER','Seasonal airport announcement; MOW unresolved запрещён как физический аэропорт, для инвентаря нужны отдельные SVO/DME; маршруты не полный список','UNKNOWN',carrier)
offer('VOG-O09','URAL AIRLINES/FUN&SUN','VOG','AYT','летняя программа2026 с24.05','3 Tue/Thu/Sun','UNKNOWN','A321 up to220','UNKNOWN','S-VOG-ANNUAL','TG284 от26.01.2026 в том же сохранённом канале;220номинальных мест — максимум типа в анонсе, не свободные места','UNKNOWN','URAL AIRLINES announced')
offer('VOG-O10','flydubai','VOG','DXB','неделя09–15.11;год2026 по календарю страницы','UNKNOWN from weekly text','FZ962','UNKNOWN','23:10→05:35+1;reported325min','S-FZ-PRODUCT','Grid lists all weekday headings, active days not inferred; цена monthlyfrom не датированная продажа','UNKNOWN','flydubai published')
table('competitor_offers.csv',offers)

fare=[]
for fid,d,flight,price,dep,elapsed in [('VOG-F01','SVX','Y7952',4213,'2026-11-23',145),('VOG-F02','MOW_UNRESOLVED','DP6966',1696,'2027-01-27',115),('VOG-F03','LED','DP518',2189,'2027-02-03',155),('VOG-F04','KZN','DP6966 firstleg',3572,'2027-01-19',710)]:
    fare.append(dict(fare_id=fid,origin_airport='VOG',destination_airport=d,flight_label=flight,departure_date=dep,as_of='2026-11-12 retrieval',price_generated_at='UNKNOWN',displayed_from_RUB=price,booking_lead_calendar_days=(date.fromisoformat(dep)-date(2026,11,12)).days,booking_lead_meaning='Разность дат наблюдения/вылета; реальный lead формирования цены UNKNOWN',elapsed_reported_minutes=elapsed,baggage='UNKNOWN',basket_comparable=False,party_size='1adult economy in page form;quote-specific guarantee UNKNOWN',through_ticket='UNKNOWN',connections='KZN product явно не прямой; firstlegcode не весь itinerary' if d=='KZN' else 'UNKNOWN/not asserted',gross_net_bridge='UNKNOWN',unit='RUB/journey;days;minutes',period=dep,status='cached_display_not_inventory_or_netfare',coverage='Один публичный индикатор цены; не спрос, не тариф2027-2028, не confidencebound',source_id='S-VOG-FARE-IND',assumption_id='A-VOG-KEEP'))
fare.append(dict(fare_id='VOG-F05',origin_airport='VOG',destination_airport='DXB',flight_label='FZ962',departure_date='UNKNOWN',as_of='2026-11-12 retrieval',price_generated_at='UNKNOWN',displayed_from_RUB=38626,booking_lead_calendar_days='UNKNOWN',booking_lead_meaning='Месячный минимум, дата не раскрыта',elapsed_reported_minutes='UNKNOWN',baggage='UNKNOWN',basket_comparable=False,party_size='UNKNOWN',through_ticket='UNKNOWN',connections='Direct route published; no selected booking',gross_net_bridge='UNKNOWN',unit='RUB/journey',period='2026-11/12 displayed months; year inferred',status='primary_monthly_fromprice_not_datedquote',coverage='Не использовать для P05 fare calibration без конкретной корзины',source_id='S-FZ-PRODUCT',assumption_id='A-VOG-KEEP'))
for f in fare:
    f['departure_year_status']='2026 inferred from retrieval context' if f['fare_id']=='VOG-F01' else 'SOURCE_EXPLICIT_2027' if f['fare_id'] in ['VOG-F02','VOG-F03','VOG-F04'] else 'UNKNOWN_exact_departure'
    f['assumption_id']='A-VOG-KEEP;A-VOG-QUOTE'
table('fare_observations.csv',fare)

constraints=[]
for id,field,value,status,src,impact,refine in [
 ('VOG-L01','ВПП','2800x45м в сообщении2016','historical_primary','S-VOG-TECH','Не допуск на конкретной массе/ветре/дате','Текущие AIP declared distances,PCN,NOTAM,P03 payload/alternate'),
 ('VOG-L02','Стойки и стоянки','20мест были запланированы в2016;текущая свободная ёмкость UNKNOWN','planned_history_not_capacity','S-VOG-TECH','Число из проекта нельзя выделить RW или объявить ночной базой','Актуальная stand chart и согласованные overnight позиции/тарифы'),
 ('VOG-L03','SSJ100 и SJ100/ПД8','SSJ история/анонс есть;SJ100/ПД8 допуск UNKNOWN','variant_specific_unknown','S-RW-SUMMER;S-P03','Новый самолёт не сертифицируется по историческому SSJ','Airport admission+operations manual по варианту/массе/году'),
 ('VOG-L04','MRO/запчасти/инструмент','RW contract,approved type,staff/capacity UNKNOWN','unknown','S-P03','VOG база может требовать запуск станции или перевозку специалистов; время AOG не0','P03/RW dispatch,MROprovider certificate,currentcontract,capacity guarantee'),
 ('VOG-L05','Экипажи и гостиница','Количества/ставки/комнаты RW UNKNOWN','unknown','S-P03;S-P04','Длинный bank-duty не принят; гостиница в аэропорту не блок комнат RW','Roster по дням, отдых/перелёт экипажей, hotel contract, reserve response'),
 ('VOG-L06','Слоты/время работы/handling','Договоры/доступ к нужным окнам UNKNOWN','unknown','S-P03','Удобные UTC08/09:30/15:30 не согласованные слоты','Airport coordination и SGHA,security/border windows,transfer process'),
 ('VOG-L07','Стоимость разворота/топлива/базы','Текущая локальная ставка2026 и будущая RW2027/28 UNKNOWN','unknown','S-P04;S-VOG-DISCOUNT','Референсы другого аэропорта/ставки2016/скидка2022 не являются paidVOGcost','Действующий прейскурант с incidence,VAT,minimum;fuelagreement;priceescalator'),
 ('VOG-L08','Сезон/сбои','Airport зимняя подготовка опубликована; часы локальных закрытий UNKNOWN','partial_primary','S-VOG-WINTER;S-VOG-DISRUPTION','Сбой московского узла23.10.26 затронул VOG; не приписывать его VOG closure','P03 NOTAM/METAR/actual movements с отменами; replay bank/recovery'),
 ('VOG-L09','Пересадки/багаж/защита','VOG RW MCT,interline,baggage,reprotection UNKNOWN','unknown','S-P03;S-RW-SVX-BAG','Правила SVX не переносятся на VOG; отдельно self-transfer и protected','Airport/RW product contracts and datedbookable PNR itinerary без покупки'),
 ('VOG-L10','Запуск и выход','Noticeperiod,deposits,minimum term,refundability,severance UNKNOWN','unknown','S-P04','У малой частоты база всё равно может нести полные обязательства24months/после2028','P04 cash events с датами,terminal liabilities,committed orders;TH-FUNDING'),
]:constraints.append(dict(constraint_id=id,field=field,value=value,status=status,source_id=src,decision_impact=impact,how_to_refine=refine,unit='См.поле;неизвестные контрактные значения не0',period='История/as_of2026-11-12;будущий2027–2028 отдельно',coverage='VOG/RW/aircraftvariant only',assumption_id='A-VOG-COST;A-VOG-RESOURCE;A-VOG-ENTRY'))
table('airport_constraints_local.csv',constraints)

fl=rows('proposed_flight_calendar.csv');summary=[]
for pid in sorted({f['programme_id'] for f in fl}):
    group=[f for f in fl if f['programme_id']==pid];daily=defaultdict(float)
    for f in group:
        t=(datetime.fromisoformat(f['arrival_utc'].replace('Z','+00:00'))-datetime.fromisoformat(f['departure_utc'].replace('Z','+00:00'))).total_seconds()/3600
        daily[(f['tail'],f['departure_utc'][:10])]+=t
    pairs={tuple(sorted([f['origin_airport'],f['destination_airport']])) for f in group}
    summary.append(dict(programme_id=pid,unique_pairs_including_ferry=len(pairs),legs_24month_envelope=len(group),block_hours_24month_proxy=round(sum(daily.values()),3),max_tail_daily_block_h=round(max(daily.values()),3),unit='unique airportpairs;legs;block_h',period='2027-01/2028-12',coverage='Только сценарная конструкцияk1.1,turn45; не dispatch/fleet acceptance',status='calculated_scenario',source_id='S-panel;S-P03;S-P06',assumption_id='A-VOG-BLOCK;A-VOG-FREQ;A-VOG-TURN;A-VOG-ENTRY'))
table('programme_resource_summary.csv',summary)

# A readable two-wave sample also checks physical same-day return connectivity.
sample=[f for f in fl if f['programme_id']=='P-VOG-40' and f['departure_utc'].startswith('2028-07-02')]
table('bank_example_20280702.csv',sample)
inbounds={f['origin_airport']:f for f in sample if f['destination_airport']=='VOG'}
outbounds={f['destination_airport']:f for f in sample if f['origin_airport']=='VOG'}
con=[]
for o in ['SVX','KUF','MRV','AER']:
    for d in ['SVX','KUF','MRV','AER']:
        if o==d or ((o in ['SVX','KUF'])==(d in ['SVX','KUF'])):continue
        a=inbounds[o];b=outbounds[d]
        wait=(datetime.fromisoformat(b['departure_utc'].replace('Z','+00:00'))-datetime.fromisoformat(a['arrival_utc'].replace('Z','+00:00'))).total_seconds()/60
        con.append(dict(origin=o,destination=d,via='VOG',inbound_leg_id=a['flight_instance_id'],outbound_leg_id=b['flight_instance_id'],wait_minutes=wait,nonnegative_wait=wait>=0,protected='UNKNOWN',protection_status='UNKNOWN;MCT/baggage/reprotectioncontract required',unit='minutes',period='2028-07-02 onlyexample',status='constructed_datetime_join_not_sale',coverage='8directedconnections;onecalendardate;notdemand',source_id='S-P03;S-P06',assumption_id='A-VOG-BANK;A-VOG-TURN'))
table('bank_connections_example.csv',con)
assert len(con)==8 and all(x['wait_minutes']>=90 for x in con)

# Pin the initial board observation honestly: this is an analyst record, not a downloaded response.
dump('sources/first_board_observation.json',{'url':'https://airportvolgograd.ru/','observed_at':'2026-11-12 initial nativeweb read','observation':'Первый ответ web.open показал на12.11 WZ6951/Y7951 arrival17:55 иWZ6952/Y7952 departure19:25, B737; одинаковые часы/тип в каждой паре','capture_status':'Запись наблюдения исследователя. Полный первый tool response не сохранён. Последующие webopen пустые; HTTP200 возвращает JS-страницу вместо табло. Не трактовать localhash как hash первоначального ответа','use':'Только corroboration. Основное основание для marketing-vs-operator — primaryNordStar3357/3624 +winterTG419 +pinnedP02. Нет currentinventory acceptance.'})
early=read('early_tranche.json');early['findings'][2]['source_raw']='sources/first_board_observation.json'
for x in early['findings']:x['local_sha256']=sha(R/x['source_raw'])
dump('early_tranche.json',early)

report='''# Волгоград в сети Red Wings

Локальное исследование Stage A завершено. Для общего расчёта подготовлены десять программных компонентов, девять гипотез и конкретные запросы Stage B. Денежного победителя пока нет: для VOG не приняты спрос P05, будущий KEEP, ресурс P03 и местные договорные расходы P04.

## Роль города и сохраняемый бизнес

VOG — подтверждённый пункт маршрутной сети и партнёрских продаж Red Wings. Действующая база Red Wings или защищённый пересадочный хаб в Волгограде не установлены. Это неизвестный статус, а не доказанное отсутствие базы.

Наиболее существенная находка — [сообщение NordStar от9 января2024](https://www.nordstar.ru/about/news/3357/): SVX–VOG выполняет NordStar на B737-800, Red Wings участвует в код-шеринге. [Продолжение от8 июля2024](https://www.nordstar.ru/about/news/3624/) сохраняет это распределение. В [зимнем сообщении аэропорта от26 октября2026](https://t.me/airportvolgograd/419) перевозчиком на Екатеринбург назван NordStar. В P02 закреплены Y7951/952 по понедельникам и четвергам с частичной временной атрибуцией. Нельзя превращать маркетинговый номер WZ в собственный SSJ или удваивать кресла Y7/WZ. Текущие allotment, комиссия и договор на2027–2028 неизвестны.

Отдельный [летний анонс Red Wings от10 июня2026](https://flyredwings.com/press/news/red-wings-budet-letat-iz-ekaterinburga-v-volgograd/) обещал собственный SSJ100 с23 июня один раз в неделю: SVX11:40, обратный VOG15:35, в пути155минут. Текст доступен в индексе search; сам URL сейчас отвечает410. Это не подтверждение фактического выполнения, зимней программы или свободного самолёта. Исторические VOG–SGC и MCX–VOG есть в официальном списке акции2025 с перевозкой до28.03.2026; VOG–BUS найден в кэшированном табло Red Wings. Их текущую непрерывность нельзя ни предполагать, ни обнулить при построении KEEP.

## Потоки и сезоны

[Пресс-служба аэропорта](https://t.me/airportvolgograd/287) сообщает1 540 280 аэропортовых пассажирских обслуживаний за2025:1 435 489 на внутренних и104 791 на международных линиях. Это прибытия/вылеты всех перевозчиков, а не уникальные поездки и не OD Red Wings. Наиболее заметные рынки после Москвы и Петербурга — Екатеринбург, Анталья и Новосибирск.

В официальном коммерческом документе аэропорта от26.02.2026 с изменением04.03.2026 найдены все12месяцев2025 по четырём метрикам: внутренние, международные, внутренний вылет и общий поток. Сумма общего ряда1 540 278; внутреннего1 435 591; международного104 687. Расхождение с пресс-релизом сохранено в `source_reconciliation.json`. Месячные суммы сходятся с собственными годовыми итогами документа. Отношение максимального к минимальному среднесуточному общему потоку около1,68. Это сигнал сезонной неоднородности, а не коэффициент спроса каждой новой пары.

Региональный инвестиционный портал подтверждает историко-патриотический, семейный и автомобильный туризм; он не даёт авиационной доли, городов происхождения или гарантированного блока. Корпоративные, деловые, семейные визиты и вахта как количественные сегменты остаются UNKNOWN. Промышленный профиль города и существование северного рейса не заменяют контракт или OD-наблюдение.

Вторичный пересказ первого полугодия2026 содержит конфликт:652,1тыс. общего потока против625,4+18,1=643,5тыс. компонент. Его нельзя применять для прогноза роста/снижения спроса без первичной сверки.

## Конкуренция и наземные альтернативы

Официальный зимний перечень2026/27 содержит Москву (Аэрофлот/S7/Победа), Петербург (Россия/Победа), SVX (NordStar), OVB (S7), DXB (flydubai), SSH (Air Cairo). Это опубликованные продукты, не полный датированный инвентарь. Москва в этом источнике не разбита на аэропорты; в физических расписаниях нужен SVO/DME по отдельности. Отсутствие другой пары в перечне не означает отсутствие конкурента.

Цены в `fare_observations.csv` имеют дату вылета, дату извлечения и календарный lead. Например, вторичный публичный экран показывает Y7952 на23.11.2026 от4 213₽; дата формирования цены и багаж неизвестны. Это индикатор поиска, не сопоставимый тариф, не netfare и не гарантированное место. Действующие правила NordStar различают экономический тариф без багажа и тариф с23кг; историческую норму из анонса2024 нельзя переносить на любую покупку2026. Продукт flydubai подтверждён первичным сайтом, но месячный минимум без выбранной даты не служит датированной котировкой. Продажа конкретных сквозных/through-stop продуктов остаётся неизвестной. Физическая близость рейсов или один номер не доказывают защиту пересадки.

Для GSV найден датированный железнодорожный пример Волгоград-1–Саратов-1:161С,6ч49мин в указанные ноябрьские дни2026. Нужно дополнить доступом до аэропорта GSV и сравнением дверь–дверь. По Астрахани первичный пост РЖД оказался экскурсионным продуктом18.10.2025, а не регулярным предложением2026; год восстановлен по datetime поста3185. Время поездки из его часов не рассчитано: стандарт времени не обозначен. Для доступа к VOG есть первичное расписание поезда аэропорт17:34→Волгоград-118:06 на04.11–03.12.2026. Эти32минуты не равны полному времени до дома и не описывают весь протяжённый Волгоград/Волжский.

Реакция конкурентов задана механизмами, без выдуманных вероятностей и процентов: Y7 может менять цену/частоту/условия код-шеринга на уже обслуживаемом SVX; SU/S7/DP/FV — цены и стыковки на своих опубликованных сетях. Для добавления частоты нужны доступные самолёты и слоты. В P05 следует сравнить сохранение текущего предложения, адресное изменение цены, возврат ёмкости и изменение банков только с явным основанием/сценарным ID.

## Парные программы

| Компоненты | Что различает опыт | Ресурс, запрашиваемый у P03 |
|---|---|---|
| P00 против P10 | Партнёрский SVX против собственного прямого RT из SVX; сохранить partner sales в KEEP |0 новых собственных хвостов у P00;1 рабочий у P10, одинаковый новый ресурс в общей альтернативе |
| P20 против P30 | SVX–VOG–MRV–VOG–SVX против VOG–SVX–VOG–MRV–VOG: те же коммерческие плечи, другое место ночёвки/часы |1 рабочий; P30 дополнительно два позиционирования, база/crew/MRO/exit |
| P40 против P41 | Две волны через VOG против прямых SVX–MRV/KUF–AER и локальных SVX/KUF–VOG |Те же2 рабочих хвоста и календарь доступности; разное использование дней и блок-часов видно |
| P50 против ground и P10 | VOG–GSV–VOG–ASF–VOG против наземного подвоза/прямой наземной поездки и иного применения хвоста |1 рабочий; зимняя пауза — только решение этого пилота |
| P60/C09 | Пятница SVX–KUF–VOG–SVX, воскресенье обратная ориентация |1 рабочий; оплачиваются все6секторов в неделю;1 рейс в каждом направлении каждой пары |
| P70/C19 | Пятница ZIA–VOG–MCX–ZIA и воскресенье обратная ориентация;2ночи в Дагестане |1 рабочий; сохранить прежний MCX продукт, проверить длинное ZIA–MCX и альтернативный прямой RT |
| H08 и P80 | Северный SGC/OMS фидер и международный BUS как отдельные продолжения |Нет фиктивного northern/BUS dispatch; нужен исходный рейс, дальность, тип, календарь, права |

Частоты1/2/3 — точки конструкции. Два разнесённых рейса позволяют3/4ночи, три уменьшают разрыв до2/3дней; недельный одиночный рейс часто не даёт нужного возврата. Это обоснование сравнить продукты по сроку поездки, а не измеренный спрос. Все частоты, сезоны и числовые прокси зарегистрированы в `assumptions.csv`; их статистические интервалы не заявлены.

Геометрия даёт новое основание для опыта P40: через VOG длина KUF–AER увеличивается примерно на0,07%, SVX–AER на0,64%, KUF–MRV на2,26%, SVX–MRV на3,50% против дуг большого круга. VOG находится почти на части север–юг коридоров. Но дополнительная посадка, ожидание, обходы воздушного пространства и расходы остаются. Для GSV–ASF обход через VOG около20%, OMS–MCX около22%; эти фидеры требуют отдельного объяснения, а не копирования удачной геометрии KUF–AER.

P40 допускает пересадочный пункт без постоянной ночной базы VOG. В примере02.07.2028 северные SVX/KUF прибывают08:00UTC, южные MRV/AER вылетают09:30UTC; обратный юг прибывает до отправления севера15:30UTC. В файле примера соединены восемь направленных поездок с неотрицательным ожиданием не менее90минут. Они не названы защищёнными: MCT, багаж, reprotection и продажа неизвестны. Для P30/P50 на одном хвосте такая двунаправленная связность не обещана.

## Эксплуатация и стоимость

Первичный Минтранс2016 подтверждает полученную ВПП2800×45м. Число20стоянок в том же сообщении относилось к будущему проекту. Оно не подтверждает современные свободные позиции или доступ Red Wings. Отдельно открыты действующие AIP/NOTAM/PCN, допуск SJ100/ПД8, слоты, handling, линия ТО с нужным сертификатом и мощностью, запасные части, экипажи, отдых/гостиница, резерв и время его прибытия. Публичное существование гостиницы или терминала не даёт договорного ресурса RW.

Текущий местный прейскурант и будущая цена RW не получены. Старые раскрытия2016 и положение о скидках2022 зарегистрированы как исторические; никакая скидка или цена не перенесена на2027. HTTP-загрузка нескольких страниц/документов аэропорта вернула одинаковую JS-страницу с200 вместо содержания; сохранены receipts и hashes. Для исследования использованы доступные текстовые ответы web и официальный Telegram. Браузерные сессии не трогались.

Расходы передаются в P04 через `cost_driver_requests.csv`: рейсы, аэропорт, тип-аналога, блок-часы и явные неизвестные MTOW/топливо/пассажиры/стоянки. Результат до расходов новой базы сравнивается по TH-OPTION; остаток задаёт максимально допустимые дополнительные расходы базы. TH-FIXED/LAUNCH/FUNDING применяются совместно, с одинаковыми P05/P06 и обязательствами самолёта/резерва. Нельзя одновременно поставить каждую неизвестную статью на её отдельный максимум. Пик финансирования неизвестен до дат депозитов, поступлений, отсрочек, выхода и остаточных обязательств.

## Проверка ресурса и границы

Сформированы6 258 предложенных физических плеч в восьми номинальных календарях2027–2028. Месяцы в каждой программе перечислены отдельно в `calendar_monthly.csv`. Счёт выполнен по датам, без умножения недели на52. Это envelope программы при ещё неизвестном выделении самолётов; до ввода нового SJ100 рейсы не активируются. SSJ100 с переносом требует донора; новый SJ100/ПД8 требует самостоятельных технических и стоимостных входов. Новых Ту214 в основной и дополнительной ветвях0.

Вызван неизменённый `P06.check_operations` из commit982f13d9 на всех24месяцах для8программ ×2route-factors ×2turn-times ×3daily-limits =96проверок.74 вернули CONDITIONAL и22 INFEASIBLE в пределах выбранных прокси. Ни одна не является dispatch-ready: реальные tail availability,crew,MRO,reserve и кресла оставлены UNKNOWN. Полный evaluate/compare и спрос/деньги не запускались. Это не независимая общая приёмка движка P06.

При k1,1 и45мин развороте максимальный рабочий день P20/P30 около7,70блок-часа: лимит6,5 нарушается,8 проходит только как условный сценарий. При k1,2 день превышает8часов. Перестановка ночёвки не устраняет это ограничение: нужны другое расписание, меньшая частота/другая группировка дней либо дополнительный ресурс, который также должен получить альтернативу в KEEP. У P40 концентрация на двух волнах тоже требует проверки этого ограничения; прямой контроль P41 намеренно разнесён по разным дням, чтобы не создавать заведомо перегруженный контрольный день. Более высокий общий налёт P41 сохранён, свободные дни P40 не оценены в ноль.

## Что определит Stage B

Сначала следует связать Y7/WZ с единым физическим inventory и восстановить будущие собственные/партнёрские продажи. Затем P05 передаёт совместимые OD×month×срок поездки, наземные варианты и выбор между аэропортами; P03 накладывает ввод, донора, crew/MRO/резерв и допуск; P04 добавляет местные расходы и события cash. После этого P06 совместно пересчитывает P и KEEP с одинаковыми версиями и ресурсом, а P09 включает лучшие VOG-компоненты в общую сеть8–12пар и сравнивает с применением ресурса вне города.

Решение в пользу базы изменится, если польза её часов не покрывает launch/fixed/exit или если нет доступа ТО/crew/стоянкам. Решение в пользу пересадок изменится, если прямые/наземные продукты удобнее, пассажир не принимает ожидание либо нет гарантированной обработки/восстановления. Решение в пользу собственного SVX изменится, если вытесняемая партнёрская маржа и альтернативный результат борта выше дополнительного вклада. Неполные данные не превращены в экономический отказ; один слабый шаблон не закрывает город. Все девять гипотез имеют условный исход и адресное условие пересмотра в `hypotheses.json`.
'''
report=re.sub(r'(?<=[А-Яа-яЁё])(?=\d)|(?<=\d)(?=[А-Яа-яЁё])',' ',report)
report=report.replace('161 С','161С').replace('Волгоград-118:06','Волгоград-1 18:06').replace('конфликт:652','конфликт: 652').replace('за 2025:1','за 2025: 1')
(R/'report.md').write_text(report)

programmes=read('programme_candidates.json')
titles={
 '00':'Партнёрские продажи SVX и проверка стыковок',
 '10':'Прямой SVX–VOG из существующего узла',
 '20':'W-оборот через VOG без ночной базы',
 '30':'Один рабочий самолёт с ночной базой VOG',
 '40':'Две пересадочные волны VOG из двух опор сети',
 '41':'Прямые южные рейсы и локальные рейсы в VOG',
 '50':'Короткие фидеры Нижней Волги',
 '60':'Самара–Волгоград: цепь с обратной ориентацией',
 '70':'Двухдневная поездка Волгоград–Дагестан',
 '80':'Батуми: дополнительный сезонный продукт'}
for p in programmes['programmes']:
    p['title']=titles[p['programme_id'][-2:]]
    p['release_rule']='Это конструкторский календарь, а не выделенные самолёты или открытая продажа. P03 должен наложить ввод/доступность и сохранить донора/KEEP; P05/P04 — спрос, цены и расходы. Непринятые поля остаются UNKNOWN.'
    p['reserve_rule']='Рабочий самолёт и резерв раздельны. Dedicated1 — диагностическая политика P03, не свободный борт. Общий резерв требует доказанного покрытия VOG и времени восстановления.'
dump('programme_candidates.json',programmes)
hh=read('hypotheses.json')
for h in hh['hypotheses']:
    if h['hypothesis_id'] in ['H-VOG-03','H-VOG-04']:
        h['local_test_outcome']='Оценена только сценарная ротация: при k1.1 рабочий день северной цепи около7.70блок-часа; лимит6.5 нарушается. При k1.2 нарушается также8часов. Это исход конкретного шаблона, не отказ базе/пересадкам/городу.'
    elif h['hypothesis_id']=='H-VOG-05':
        h['local_test_outcome']='Геометрия GSV–ASF через VOG увеличивает путь примерно20%; локальный фидер сопоставлен с источниками наземного контроля. Доказанного экономического отказа нет; door-to-door и OD неизвестны.'
    else:h['local_test_outcome']='Локальные факты, контроль и программа/условие продолжения зарегистрированы; отсутствие общих входов не объявлено отрицательным экономическим результатом.'
dump('hypotheses.json',hh)

# Cross-file integrity, not tests of the author's modelling assumptions.
required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json']
checks=[]
for f in required:checks.append({'check':'required:'+f,'pass':(R/f).exists() and (R/f).stat().st_size>0})
sourceids={x['source_id'] for x in source_rows};assids={x['assumption_id'] for x in rows('assumptions.csv')}
for filename in ['evidence.csv','market_deltas.csv','comparison_requests.csv','competitor_offers.csv','fare_observations.csv','airport_constraints_local.csv','calendar_monthly.csv','cost_driver_requests.csv']:
    data=rows(filename)
    for i,row in enumerate(data,1):
        assert all(row.get(k) for k in ['unit','period','coverage','status','source_id']), (filename,i,'metadata')
        assert set(row['source_id'].split(';'))<=sourceids,(filename,i,'source')
        if row.get('assumption_id'):assert set(row['assumption_id'].split(';'))<=assids,(filename,i,'assumption')
    checks.append({'check':filename+':units_period_coverage_status_source_ids','pass':True,'rows':len(data)})
for pid in {x['programme_id'] for x in fl}:
    assert len([x for x in rows('calendar_monthly.csv') if x['programme_id']==pid])==24
    assert all(x['origin_airport']!='MOW' and x['destination_airport']!='MOW' for x in fl)
    assert all(x['seats']=='UNKNOWN' for x in fl)
checks.append({'check':'8nominal_calendars_24months;unknownseats;noMOWphysicalairport','pass':True})
checks.append({'check':'8directed_bank_joins_wait_atleast90_example_only','pass':True})
source_rows_verified=0
for entry in read('source_pins.json')['extracts']:
    path=R/entry['local'];assert path.exists(),entry
    if entry['local'].startswith('inputs/p06_ops/'):assert sha(path)==entry['source_sha256']
    if path.suffix=='.csv':
        data=rows(entry['local'])
        if data and 'source_data_row_1based' in data[0]:
            raw=subprocess.check_output(['git','show',entry['commit']+':'+entry['path']])
            assert hashlib.sha256(raw).hexdigest()==entry['source_sha256']
            original=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
            for row in data:
                old=original[int(row['source_data_row_1based'])-1]
                ch=hashlib.sha256(json.dumps(old,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                assert ch==row['source_row_canonical_sha256']
                assert all(row[k]==v for k,v in old.items())
                source_rows_verified+=1
    entry['extract_sha256']=sha(path)
checks.append({'check':'exact_git_blobs_and_selected_original_rows_unchanged','pass':True,'rows_verified':source_rows_verified})
pin=read('source_pins.json')
for entry in pin['extracts']:entry['extract_sha256']=sha(R/entry['local'])
dump('source_pins.json',pin)
for row in source_rows:
    if row['local_path']=='source_pins.json':row['local_sha256']=sha(R/'source_pins.json')
table('sources.csv',source_rows)
dump('validation.json',{'status':'PASS_package_integrity_only','checks':checks,'not_validated':['Рыночный спрос и P05 calibration','Действительный свободный ресурс/crew/MRO/slots/range','Полная P06 независимая code acceptance','P−KEEP деньги/cash/финансирование/доля рынка'],'git_write_operations':'NONE'})
manifest=[]
for p in sorted(R.rglob('*')):
    if p.is_file() and p.name!='output_manifest.json' and '__pycache__' not in p.parts:
        manifest.append({'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p),'role':'source' if 'sources' in p.parts else 'pinned_extract' if 'inputs' in p.parts else 'output_or_reproducer'})
dump('output_manifest.json',{'package':'VOG/research_v1','manifest_hash_scope':'Все файлы пакета кроме самого output_manifest.json; неизменность доказывает hash, не source/market acceptance','status':'StageA_complete_StageB_pending','files':manifest,'file_count':len(manifest),'total_bytes':sum(x['bytes'] for x in manifest)})
print(json.dumps({'integrity':'PASS','file_count':len(manifest),'bytes':sum(x['bytes'] for x in manifest),'bank_joins':len(con),'stage_b':'PENDING'},ensure_ascii=False))
