"""Build a bounded Stage A BAX package, never the shared choice or money model."""
import csv, datetime as dt, hashlib, io, json, math, subprocess
from pathlib import Path

R=Path(__file__).resolve().parent
BASE='context/35_full_programme_execution_20261112/'
NOW='2026-11-12'
def dump(name,x): (R/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def table(name,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (R/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:('UNKNOWN' if v is None else v) for k,v in row.items()} for row in rows])
def sha(path):return hashlib.sha256((R/path).read_bytes()).hexdigest()
def gitbytes(s,p):return subprocess.check_output(['git','show',s+':'+p])

pins=json.loads((R/'source_pins.json').read_text())
for s,p in [
 ('b7d74e67dd6c603db049b1915b1afec987e3b458',BASE+'P00R/contract_addendum.json'),
 ('b7d74e67dd6c603db049b1915b1afec987e3b458','context/34_full_programme_plan_20261112/variant_research_plan.json'),
 ('982f13d9b6c378ed9581125ecc5c40f17dade6a3',BASE+'P06/producer_contract.json'),
 ('982f13d9b6c378ed9581125ecc5c40f17dade6a3',BASE+'P06/README.md'),
 ('620a0ac4bb11763319c4227485f6a3996b91d367',BASE+'P04/cost_assumptions.json')]:
    b=gitbytes(s,p)
    if not any(q['sha']==s and q['path']==p for q in pins):
        pins.append({'sha':s,'path':p,'git_blob':subprocess.check_output(['git','rev-parse',s+':'+p],text=True).strip(),'sha256_full_blob':hashlib.sha256(b).hexdigest(),'use':'Прочитан контракт/структура; полный чужой fixture не копируется'})
dump('source_pins.json',pins)

for pin in pins:
    if pin.get('selected_file')=='inputs/P03_aircraft_type_parameters.csv':
        rows=list(csv.DictReader(io.StringIO(gitbytes(pin['sha'],pin['path']).decode())))
        selected=[]
        for n,row in enumerate(rows,2):
            if row['aircraft_type'] in ['RRJ95B','RRJ95LR_100','SJ100_PD8']:
                selected.append({'input_row_number':n,'input_row_sha256':hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),**row})
        table(pin['selected_file'],selected);pin['selected_rows']=len(selected)
dump('source_pins.json',pins)

# Exclude incidental mentions of BAX used as a proxy for unrelated pairs.
for pin in pins:
    if pin.get('selected_file')=='inputs/model_network_routes.csv':
        original=list(csv.DictReader(io.StringIO(gitbytes(pin['sha'],pin['path']).decode())))
        selected=[]
        for n,row in enumerate(original,2):
            if row.get('from')=='BAX' or row.get('to')=='BAX' or row.get('variant')=='Хаб BAX':
                selected.append({'input_row_number':n,'input_row_sha256':hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),**row})
        table(pin['selected_file'],selected);pin['selected_rows']=len(selected)
dump('source_pins.json',pins)

receipts=json.loads((R/'fetch_receipts.json').read_text())+json.loads((R/'fetch_supplement.json').read_text())
receipt={x['source_id']:x for x in receipts}
catalog={}
def source(s,org,published,period,grain,status,coverage,url=None,path=None):
    rec=receipt.get(s,{})
    catalog[s]={'source_id':s,'organization':org,'url':url or rec.get('url'),'publication_date':published,'source_period':period,'as_of':NOW,'retrieved_at':rec.get('retrieved_at',NOW),'grain':grain,'status':status,'coverage':coverage,'local_evidence':path or rec.get('text_path'),'raw_sha256':rec.get('sha256') if rec.get('text_status')!='bot_challenge_not_content' else None,'evidence_sha256':sha(path or rec['text_path']) if (path or rec.get('text_path')) else None}

source('RW-BOARD','АО «Ред Вингс»','Динамическое табло','2026-11-11/13','датированный станционный рейс; местные часы','PRIMARY_DATED_BOARD','Сохранён снимок 12.11; фактические и плановые статусы различаются; кресла и registration tail отсутствуют')
source('RW-WINTER','АО «Ред Вингс»','2026-10-27','зима 2026/27','названные опорные аэропорты','PRIMARY_PUBLISHED','Отсутствие BAX в перечне не доказывает отсутствие всех договоров/crew/базирования')
source('RW-BELAVIA','АО «Ред Вингс» / Belavia','2026-08-31; сверять метаданные страницы','с 01.09.2026','комбинированный маршрут BAX–SVX–MSQ','PRIMARY_PRODUCT_ANNOUNCEMENT','Продажа комбинированного продукта объявлена; quote/доступные места/договорные гарантии на дату не проверены')
source('BAX-HISTORY','AEX / Интерфакс со ссылкой на пресс-центр правительства Алтайского края','2026-01-12','2025','годовой аэропортовый/городской поток','SECONDARY_ATTRIBUTED_HISTORY','Округления; направления полёта, конечные OD и месяцы не разделены; MOW не аэропорт')
source('BAX-2025-FINAL','Вечерний Барнаул со ссылкой на аэропорт','2026-01-15','2025','годовой пассажиропоток аэропорта и вылеты','SECONDARY_REPORTED_TOTAL','792644 пассажирских обслуживания; не уникальные люди и не catchment спрос')
source('BAX-2025-APRIL','НИА-Алтай со ссылкой на Минтранс края / директора аэропорта','2026-04-03','2025; планы 2026','агрегат аэропорта; история поддержки','SECONDARY_ATTRIBUTED_HISTORY','Нельзя переносить агрегат краевой поддержки на один рейс или на 2027–2028')
source('BAX-YANDEX','Яндекс Расписания','Динамический снимок','зима 2026/27; отдельные строки весна 2027','правило расписания/датированный станционный продукт','SECONDARY_SCHEDULE','Год частично восстанавливается из текущего календаря; не inventory; список неполный')
source('BAX-KRASAVIA','АО «КрасАвиа»','Динамический снимок','2026-11-12','датированный рейс KV103/KV104','PRIMARY_DATED_BOARD','Красноярск назван городом; привязку KJA vs KCY перед physical binding подтвердить; места/тип в строке не извлечены')
source('BAX-GROUND','Туту / указанный перевозчик «Алтайский Перевозчик»','обновление 2026-07-01','опубликованное предложение 2026','автовокзал Барнаул–аэропорт Толмачёво','SECONDARY_GROUND_PRODUCT','Дни UNKNOWN; цена приблизительная; не датированная продажа/не гарантия стыковки')
source('BAX-GROUND-RETURN','Туту / Солгрибус; Лебедев С.Ю.','обновление 2026-04-05','опубликованное предложение 2026','Толмачёво–Барнаул','SECONDARY_GROUND_PRODUCT','Дни UNKNOWN; не текущая доступность кресел')
source('BAX-UTAIR','ПАО «Авиакомпания «ЮТэйр»','Динамическая витрина','31 октября; год в карточке не указан','недатированная относительно снимка витрина BAX–SGC','PRIMARY_STALE_OR_YEAR_UNBOUND_FARE','Нельзя использовать в сопоставимой тарифной корзине; baggage/fees/quote timestamp неизвестны')
source('BAX-N4-TRANSFER','Миндортранс Татарстана / пресс-служба аэропорта Казань','2026-05; точный день из страницы','лето 2026','объявленный трансфер BAX–KZN–IST','PRIMARY_ATTRIBUTED_PRODUCT','Зимняя продажа, багаж, сквозная защита и цена на дату UNKNOWN')
source('BAX-HTA-CLOCKCHECK','Страница с названием сайта аэропорта Чита на new.pskovavia.ru','Динамический снимок','2026-10/2027-03','правило расписания BAX–HTA','QUARANTINED_CLOCK_AND_DOMAIN','Домен и расхождение 04:00 vs 05:00; не источник окончательного flight time')
source('BAX-PROC2024','АО «Авиапредприятие «Алтай» / Новапорт','2024-07-17','2023 история; 2024 смешанный план/прогноз','аэропорт; месяц; описание инфраструктуры','PRIMARY_DOCUMENT_VIA_WEB_EXTRACT','HTTP bot challenge не обойден; сохранён native web extract PDF, страницы1 и7; 2024 не признан фактом',
 'https://airaltay.ru/upload/docs/arenda/Коммерческая аренда 4-2024 Запрос предложений.pdf','sources/native_web_receipts.json')
source('BAX-TARIFF2024','АО «Авиапредприятие «Алтай»','редакция с 2024-01-01','2024; не подтверждён текущий срок','позиция публичного прейскуранта','PRIMARY_INDEXED_EXCERPT_ONLY','Сохранён индекс native search; прямой HTTP возвращает bot challenge; raw PDF не получен',path='sources/native_web_receipts.json')
source('BAX-CONTRACT','АО «Авиапредприятие «Алтай»','UNKNOWN','типовой договор; не подписанный договор RW','приложение2 пункты1.1/1.4','PRIMARY_INDEXED_EXCERPT_ONLY','Стоянка/слоты по согласованию; оплата, выход, MRO, crew не установлены',path='sources/native_web_receipts.json')
source('BAX-TERMINAL','Администрация города Барнаула','2026-09-18','ввод 2026-09','пассажирский терминал','PRIMARY_MUNICIPAL_INDEXED_REPORT','Полный HTTP не получен (TLS); native search extract сохранён; 600pax/h не число свободных слотов',path='sources/supplement_search_receipt.json')
source('PIN-P02','Исследователь P02','2026-11-12','snapshot; история 2025; сценарий2027–2028','отфильтрованные строки с source row ID и hash','PINNED_SOURCE_EXPORT_NOT_PHYSICAL_ADMISSION','16 product rows; 54 directional market rows; 0 BAX comparable quotes; 0 BAX ordered physical itineraries',
 'git:d9486f113f074c185a94bcc5c0afeef12ea3574f:'+BASE+'P02/competitor_products.csv','inputs/P02_competitor_products.csv')
source('PIN-MODEL','Авторские model/panel; авторство конкретных расчётов отдельно не переопределено','commit dceadc9','история/авторские сценарии','BAX route row; не измеренный OD','PINNED_AUTHOR_SCENARIO','Сохранены строки, единицы и происхождение; деньги/захват не суммируются с P05/P06',
 'git:dceadc98f9a293d7530cb7bc50ca4411a95aa4b6:data/processed/network_routes.csv','inputs/model_network_routes.csv')
source('PIN-P03','Исследователь P03','2026-11-12','2026snapshot; 2027–2028 conditional','аэропорт и вариант самолёта','PINNED_CONSTRAINTS_WITH_GAPS','BAX MRO/crew/KEEP и SJ100/ПД8 admission UNKNOWN; diagnostic11–17Dec2028 не годовая сеть',
 'git:79dc698b99dfe866886d32376ed388e85bdd039c:'+BASE+'P03/airport_constraints.csv','inputs/P03_airport_constraints.csv')
source('PIN-P04','Исследователь P04','2026-11-12','reference; будущие цены UNKNOWN','cost driver / порог','PINNED_COST_CONTRACT','BAX LOCAL_RATE_NOT_EXTRACTED_IN_P04; местный тариф2024 только расширяет reference inventory',
 'git:620a0ac4bb11763319c4227485f6a3996b91d367:'+BASE+'P04/airport_coverage.csv','inputs/P04_airport_coverage.csv')
source('PIN-REASSESS','Пакет reassessment пяти городов; BAX строка авторского входа','commit c18f764','авторская матрица; даты внутренних источников различны','BAX catchment/погода/геометрия','PINNED_PROXY_NOT_DEMAND','630877 в старом catchment против1088356 обновлённого; пересечение/приведение неоднородны; 49.9 дней погодного proxy не downtime',
 'git:c18f7640ea36647a05b39089e5293f22dd009f63:context/33_five_city_reassessment_20261112/inputs/model/longlist.csv','inputs/reassessment_BAX_longlist.csv')
dump('source_catalog.json',list(catalog.values()))

evidence=[]
def ev(eid,s,claim,value=None,unit='качественный факт',period=None,grain=None,status=None,coverage=None,locator=None,impact='',assumption='BAX-A01'):
    c=catalog[s]
    evidence.append({'evidence_id':eid,'source_id':s,'claim':claim,'value':value,'unit':unit,'period':period or c['source_period'],'grain':grain or c['grain'],'organization':c['organization'],'url':c['url'],'publication_date':c['publication_date'],'retrieved_at':c['retrieved_at'],'as_of':NOW,'status':status or c['status'],'coverage':coverage or c['coverage'],'source_locator':locator,'source_evidence_sha256':c['evidence_sha256'],'assumption_id':assumption,'decision_impact':impact})

ev('E-BAX-01','RW-BOARD','BAX является действующей точкой RW: WZ5076 11.11 выполнен; на13.11 опубликованы UUD и SVX',impact='Положительные данные о действующей сети; базирование и хаб не установлены')
ev('E-BAX-02','RW-WINTER','BAX не назван среди семи опорных аэропортов; SVX и KUF названы',impact='Новый BAX base premium проверять против существующей базы; отсутствие названия не доказывает отсутствие договора')
ev('E-BAX-03','RW-BOARD','13.11: WZ5055 BAX05:00→UUD08:35; WZ5056 UUD09:35→BAX11:30; WZ5076 BAX12:20→SVX13:00',unit='местные часы',period='2026-11-13',locator='RW-BOARD.txt lines667–743',impact='Согласуемая цепочка; tail identity UNKNOWN; не создавать два WZ5076 в05:00 и12:20')
ev('E-BAX-04','PIN-P02','row1083 P02 BAX→SVX Fridays05:00 конфликтует с первичным табло13.11 и Yandex12:20',unit='конфликт source row',locator='input_row_number1083; product P02-basis in extract',impact='Quarantine прежнего времени до time binding; числа кресел не admitted')
ev('E-BAX-05','BAX-YANDEX','BAX→HTA WZ5085:16/23.11 и выборочные декабрь-март; BAX→UUD WZ5055:13/20/27.11 и последующие даты',unit='правило расписания',impact='Оба восточных продукта включить в futureKEEP; не считать полностью новыми рынками')
ev('E-BAX-06','RW-BELAVIA','BAX→MSQ черезSVX объявлен комбинированным код-шеринговым продуктом; плечоSVX–MSQ выполняетBelavia',impact='Международная ветвь без нового Ту214 и без нового BAX hub')
ev('E-BAX-07','BAX-N4-TRANSFER','Трансфер BAX→IST черезKZN объявлен в летней программеNordwind',impact='Международная конкуренция уже включает пересадочный продукт; зимняя продажа UNKNOWN')
ev('E-BAX-08','BAX-HISTORY','Москва: более433тыс. пассажирских обслуживаний/перелётов по опубликованному отчёту',433000,'пассажирских обслуживаний; нижняя округлённая граница',period='2025',grain='BAX–MOW city aggregate; направления не разделены',impact='MOW нельзя превратить в SVO/DME/VKO OD или уникальных людей',assumption='BAX-A02')
ev('E-BAX-09','BAX-HISTORY','Санкт-Петербург: почти66тыс.; не доказанный конечный OD',66000,'пассажирских обслуживаний; округлённый ориентир',period='2025',grain='BAX–LED; направления не разделены',assumption='BAX-A02')
ev('E-BAX-10','BAX-HISTORY','Сочи: поток сопоставим сLED; точное число не опубликовано в этой статье',None,'пассажирских обслуживаний',period='2025',grain='BAX–AER',impact='Не подставлять точное66000 из слова «сопоставимый»',assumption='BAX-A02')
ev('E-BAX-11','BAX-HISTORY','Новосибирск: около45тыс.; SVX иKZN каждый свыше30тыс.',45000,'пассажирских обслуживаний BAX–OVB; округление',period='2025',grain='направления аэропорта; OD behind OVB неизвестны',impact='Подвоз/конкуренция OVB существенны, но45тыс. не свободный transfer demand',assumption='BAX-A02')
ev('E-BAX-12','BAX-2025-FINAL','Годовой пассажиропоток аэропорта',792644,'пассажирских обслуживаний',period='2025',impact='Контекст масштаба; не делить автоматически пополам или на12',assumption='BAX-A02')
ev('E-BAX-13','BAX-2025-FINAL','Вылеты за2025',3453,'вылета',period='2025',impact='Не пара рейсов; не ресурсRW',assumption='BAX-A02')
ev('E-BAX-14','BAX-2025-APRIL','Округлённый итог792.6тыс. и рост1.5%; ранний отчёт790тыс./1.15% сохраняется отдельно',792600,'округлённых пассажирских обслуживаний',period='2025',impact='Не считать разницу новым ростом внутри2025; не смешивать редакции',assumption='BAX-A02')
ev('E-BAX-15','BAX-HISTORY','Историческая поддержка нескольких направлений агрегирована; будущая eligibility поP04',100000000,'RUB; агрегат поддержки не выручкаBAX–UUD',period='2025',grain='шесть названных направлений; бюджетный охват требует сверки',impact='Не прибавлять100млн каждому кандидату и не переносить в2027–2028',assumption='BAX-A12')
ev('E-BAX-16','BAX-PROC2024','Аэропорт сообщает круглосуточный режим и ВПП2850×50',2850,'m длины; ширина50m',period='описание в документе2024',locator='PDF page1 zero-based',impact='Пригодность сильнее старогоUNKNOWN; AIP/NOTAM/slots не подтверждены',assumption='BAX-A03')
ev('E-BAX-17','BAX-PROC2024','SSJ100 прямо включён в обслуживаемые типы',unit='тип самолёта',period='описание2024',locator='PDF page1 zero-based',impact='Не переносить на SJ100/ПД8 или все массы/даты',assumption='BAX-A03')
ev('E-BAX-18','BAX-TERMINAL','Муниципалитет сообщает ввод нового терминала; пропускная способность600пасс./час',600,'пассажиров/час терминальной мощности',period='2026-09-18',impact='Снимает предположение о старой терминальной мощности; не подтверждает transitzone, свободные stands илиMCT',assumption='BAX-A03')
ev('E-BAX-19','BAX-PROC2024','2023 помесячные числа дают706181, тогда как годовая строка723151; разница16970',16970,'пассажирских обслуживаний расхождения',period='2023',locator='PDF page7 zero-based; seasonal_audit.json',status='QUARANTINED_SUM_MISMATCH',impact='Не калибровать сезонностьP05 по этому ряду до сверки',assumption='BAX-A04')
ev('E-BAX-20','BAX-PROC2024','Таблица2024 размещена в июльском запросе и содержит будущие месяцы; это смешанный план/прогноз',unit='класс данных',period='2024',locator='PDF pages6–7 zero-based',status='FORECAST_NOT_OBSERVED_YEAR',impact='Будущие июль-декабрь нельзя выдать за факт2024',assumption='BAX-A04')
ev('E-BAX-21','BAX-TARIFF2024','Взлёт-посадка',980,'RUB/t MTOW безНДС',period='редакция с2024-01-01',locator='position1.1',impact='Исторический driver; будущая ставкаUNKNOWN',assumption='BAX-A05')
ev('E-BAX-22','BAX-TARIFF2024','Авиационная безопасность',727,'RUB/t MTOW безНДС',period='редакция с2024-01-01',locator='position1.2',assumption='BAX-A05')
ev('E-BAX-23','BAX-TARIFF2024','Сверхнормативная стоянка российских потребителей:5% landing charge зачас; первые3часа пассажирской стоянки включены',5,'% landing charge/extra h',period='редакция с2024-01-01',locator='positions1.1/1.3',impact='Длительная базовая стоянка отличается от оборота; не применять иностранные10%/сутки кRW',assumption='BAX-A05')
ev('E-BAX-24','BAX-TARIFF2024','Терминал ВВЛ взрослый90; обслуживание вылетающего209, варианты онлайн отдельно',90,'RUB/пассажир терминала безНДС',period='редакция с2024-01-01',locator='positions1.4/1.5.1',impact='Не забыть прибывающих/транзит и не сложить онлайн190 с209',assumption='BAX-A05')
ev('E-BAX-25','BAX-CONTRACT','Типовое приложение: сверхнормативная/временная стоянка согласуется; слоты выделяются по техническим возможностям',unit='публичное условие',locator='appendix2 1.1/1.4',impact='H24 не договор наночёвку и не гарантия узловой волны',assumption='BAX-A06')
ev('E-BAX-26','PIN-P03','Договор RW наТО, свободные мощности, crew, MCT/багаж BAX и SJ100/ПД8 admission неизвестны',impact='Открытые операционные зависимости; отсутствие информации не нулевые затраты',assumption='BAX-A06')
ev('E-BAX-27','BAX-YANDEX','Прямое предложение OVB S77002 ежедневно11:30; KZN N4758 пн/чт09:05; LED N4314 ср/вс08:50 и пт10:40',unit='местные часы/правило',impact='Датировать конкурентов; открытые места, платёжный тариф и тип не следуют из частоты',assumption='BAX-A01')
ev('E-BAX-28','BAX-KRASAVIA','KV10412.11 BAX06:30→Красноярск08:35, фактический вылет06:35; KV103 обратный рейс также присутствует',unit='датированный рейс/местные часы',impact='KJA-гипотеза имеет incumbent; точный destination-airport binding требуется',assumption='BAX-A01')
ev('E-BAX-29','BAX-YANDEX','BAX–SGC:UT214 по отдельным субботам22:20 и исключениям; не равномерный годовой ежедневный маршрут',unit='местные часы/правило',impact='Не выводить корпоративный гарантированный спрос из города назначения',assumption='BAX-A01')
ev('E-BAX-30','BAX-GROUND','Автовокзал21:20→аэропортТолмачёво02:20; примерно1495RUB; дни неустановлены',300,'минут наземного плеча',impact='Включить OVB catchment leakage и альтернативу авиаподвозу; продажа на датуUNKNOWN',assumption='BAX-A07')
ev('E-BAX-31','BAX-GROUND-RETURN','Обратные опубликованные варианты4ч30/5ч20; защищённость от опоздания самолёта неизвестна',unit='время наземной поездки',impact='Полный цикл поездки, а не только времяполёта',assumption='BAX-A07')
ev('E-BAX-32','BAX-UTAIR','Витрина от9460RUB31октября не является сопоставимой свежей ценойBAX–SGC',9460,'RUB/oneway витрины; в расчёт не допускается',status='STALE_OR_UNBOUND_QUOTE_EXCLUDED',impact='fare/20kg/fees/booking_lead UNKNOWN',assumption='BAX-A08')
ev('E-BAX-33','PIN-REASSESS','Старый и обновлённый catchment различаются630877 vs1088356; это моделируемый охват',unit='модельные жители; не поездки',impact='Не складывать с OVB/RGK и не превращать в билеты',assumption='BAX-A09')
ev('E-BAX-34','PIN-MODEL','Авторский BAX hub содержитKUF/KJA/UUD/PEE/TOF/CEK/IKT/NBC;transfer и деньги остаются авторским сценарием',impact='Сохранить происхождение; частоты6/5/5/4/3... не обязаны повторяться',assumption='BAX-A10')
ev('E-BAX-35','BAX-PROC2024','Аэропорт позиционирует близость к Белокурихе и курортам Горного Алтая',unit='географическая/туристическая мотивация',impact='Туристическая гипотеза обоснована как сегмент; доля туристов/ночёвки/договора UNKNOWN',assumption='BAX-A11')
ev('E-BAX-36','PIN-REASSESS','Авторский weather proxy49.9 плохих дней/год не измеряет закрытия, отмены или невыполненные кресла',49.9,'дней/год proxy; не downtime',impact='Зимний deicing/reroute нужен отдельно; не вычитать50полных дней из календаря',assumption='BAX-A13')
table('evidence.csv',evidence)

months=[47756,42241,46966,46357,63307,71200,76544,76142,69240,55514,54463,56451]
dump('seasonal_audit.json',{'source_id':'BAX-PROC2024','source_url':catalog['BAX-PROC2024']['url'],'source_period':2023,'grain':'аэропорт–месяц; не маршрут/OD','unit':'пассажирские обслуживания','month_values':dict(zip(range(1,13),months)),'computed_sum':sum(months),'printed_year_total':723151,'difference':723151-sum(months),'status':'QUARANTINED_NOT_P05_SEASONALITY','interpretation':'В документе есть летний пик, но ряд не годится для автоматической нормировки. Возможны опечатка, иной охват или ошибка извлечения; ни одна причина не установлена. Запросить месячный факт2025/2026 и сверить оригинальную таблицу.','year2024':'Смешанный план/прогноз из документа июля2024; не observed year','assumption_id':'BAX-A04'})

ass=[]
def a(i,quantity,point,range_,why,impact,test,refine,sourceids):
    ass.append({'assumption_id':'BAX-A'+str(i).zfill(2),'owner':'BAX исследователь, Sol6.1 xhigh; не решение команды','quantity_or_rule':quantity,'selected_value':point,'range_or_UNKNOWN':range_,'unit':'см. величину; сценарные числа не доверительные интервалы','period':'2027-01/2028-12 если отдельно не указано','source_id':sourceids,'why':why,'affected_conclusions':impact,'sensitivity':test,'refinement':refine,'approval_status':'аналитическое допущение/регистрация UNKNOWN; не подтверждённый параметрRW'})
a(1,'временная применимость текущего расписания','только source dates','UNKNOWN2027–2028','Изменяемая сеть; нельзя продолжать зимние правила на24месяца','KEEP и конкуренты','пересобрать зимний/летний/межсезонный календарь, конфликт05:00/12:20','carrier schedule и датированные inventory observations','RW-BOARD;BAX-YANDEX;PIN-P02')
a(2,'исторический аэропортовый поток','сохранять какreport; не OD','UNKNOWN доли конечных OD/направлений/стыковок','Числа отчёта не билеты с конечными пунктами','Все demand/market share выводы','P05 разложение конечныйOD vs segment и округления790000/792644','маршрутные отчёты аэропорта, Росавиация и anonymized coupons','BAX-HISTORY;BAX-2025-FINAL')
a(3,'местная пригодность','SSJ100/H24/ВПП только какpublished2024; terminal600 какreport2026','UNKNOWN AIP/NOTAM/PCN/допуски и будущие окна','Описание не операционный допуск','Все physical admission','полезная нагрузка, температура, wet/contaminated runway, BAX/KJA/IKT/PDM8 поотдельности','AIP,NOTAM,operator performance и аэропортовая служба','BAX-PROC2024;BAX-TERMINAL;PIN-P03')
a(4,'сезонность','ряд2023 заблокирован','UNKNOWN коэффициенты2025/2026','Сумма месяцев не равна итогу;2024частичноforecast','Объём2027–2028','зима/лето/межсезонье отдельно, не неделя×52','месячный фактический маршрутный ряд; проверка оригинала2023','BAX-PROC2024')
a(5,'стоимостьBAX','2024 reference rates только; будущие ставкиnull','UNKNOWN2027–2028 иRWскидки; число2024не lower/upper bound','Публичный старый индекс неinvoice','Hub/base fixed premium и cash need','P04 thresholds по каждой услуге; не индексировать придуманным процентом','действующийairport tariff,SGHA,fuel,MRO,crew contracts','BAX-TARIFF2024;PIN-P04')
a(6,'договора и ресурсBAX','UNKNOWN','UNKNOWN MRO/crew/slots/stand/MCT/reaccommodation/запуск/выход','Наличие провайдера неRWдоговор; базирование не доказано','Достижимость base/hub и reserve','base: signed/not; hub: acceptedMCT/not; различать SSJ100 иSJ100ПД8','подписанные договоры/прайс и FAP scope; capacity offer','BAX-CONTRACT;PIN-P03')
a(7,'OVB ground competition','5h outbound;4.5–5.33h return толькосправочно','UNKNOWN dated capacity/reliability/fare/baggage; не распределение','Есть реальный наземный продукт','Переток catchment и привлекательностьBAX','полное door-to-door; ночь/снег/большойбагаж; потерястыковки','датированные автобусные предложения и связанный авиапродукт','BAX-GROUND;BAX-GROUND-RETURN')
a(8,'цены/booking lead','нет admitted comparable quote','UNKNOWN;9460RUB excluded','Старыеfromцены не корзина1ADT20kg','Не вычислять willingness-to-pay/захват/денежного победителя','по датам13/16/27Nov2026,11Dec2026,15Jan2027,16Mar2027; летняядата приоткрытиипродажи; lead=date-as_of','P02/P05 quote grid:1ADT/ручнаякладь+20kg/сборы,oneway и return7/10/14ночей','PIN-P02;BAX-UTAIR')
a(9,'catchment weights','не выбрана ни одна численность какOD','UNKNOWN overlaps сOVB/RGK/NOZ ирежимдоезда','Авторские catchment версииразличаются','Общий demandpool; двойнойсчёт','P05 shared catchment choice и outsideoption; население нечастота поездок','geocoded zones, travel survey,actual coupons','PIN-REASSESS')
a(10,'авторские частоты/прибыль','только сохранённое происхождение','UNKNOWN реальный спрос/monetary validity','Полезный seed не новый независимый денежныйрезультат','Не суммировать модели и нефиксироватьпобедителя','joint P05/P06 sameKEEP recomputation','общий choice и единый cost ledger','PIN-MODEL')
a(11,'сегменты','туризм какмеханизм; corporate/VFR quantities UNKNOWN','UNKNOWN доли/тарифы/договорные объёмы','Источник связываетBAX скурортами, но не измеряетавиапоездки','Частоты и длительностьпоездки','7/10/14ночей leisure;3/4ночи толькокакcalendar test, не корпоративныйконтракт','опрос/купоны/туроператорский allotment толькоеслиподтверждён','BAX-PROC2024;BAX-HISTORY')
a(12,'субсидии','будущая eligibility UNKNOWN','UNKNOWN2027–2028; private/public contracts','Исторические100млн относятся кнесколькимлиниям','Деньги/сценарииno-support','P04 no-support и eligible received-support, дельта кKEEP, условия clawback','периодные решения/соглашения иreceipts черезP04','BAX-HISTORY;PIN-P04')
a(13,'зимние ограничения','нет фиксированного downtime deduction','UNKNOWN deicing frequency/cost/AOG recovery','Плохаяпогода не автоматическизакрытыйаэропорт','Пунктуальность иreserve cost','winter buffer vs summer; actual disruption histories','METAR+movement/NOTAM linked; airport deicing services','PIN-REASSESS;PIN-P03')
a(14,'частоты радиальнойпрограммы','2RT/week each KUF/IKT/KJA; понедельник/четверг и вторник/пятница,среда/воскресенье','исследовательская сетка1–3RT/week; не demandconfidenceinterval','2разнесённыхдня дают3/4ночи или7/10/14 приопределённомнаправлении; проверятьобапути','Не является опубликованнымпланомилиоптимальнойчастотой','choice utility зависит от реальныхдней иreturn; понизитьдо1/повыситьдо3 толькопослеP05','P05 спрос/тариф плюсP03календарь, crew иMRO','E-BAX-34;BAX-A11')
a(15,'SSJ100 диагностическое blocktime','неизвестныеплечи:ceil((distance/700*60+35)/5)*5min; BAX-UUD155 иобратно175 изтабло','скорость600–800km/h;overhead20–50min исследовательский диапазон; неinterval точности','Проверка грубой непротиворечивости; неflightplan','Только условный aircraft sequence; неSFJ/PД8 приемка','пересчитатьвесь оборот иночёвку накраях; P03 actual blocktime заменяетproxy','P03 airline blocktime,wind,ATC,тип/масса/навигация','RW-BOARD;inputs/geometry_airports.json')
a(16,'оборот иbank/MCT','turn60min; bank90min толькодиагностика','turn45–90min; bank/MCT45/60/90/120min условныеtestpoints, действующийMCT UNKNOWN','Полный оборот сбагажом иcrew ещёнепринят','Hub связи иresilience','первичныйcontract MCT,задержка30/60min,багаж,доступgate; никакихпродажprotected доadmission','аэропорт+RW MCT,SGHA иreaccommodation agreement','BAX-CONTRACT;PIN-P03')
a(17,'группафизическихресурсов','0/1/2 дополнительных commercially available tails какступенипотребности','непрогнозN(t);0<=available<=P03-monthly admitted','Числосертифицированных/переданных/свободныхбортовразличается','Сравниватьтожепомесячноедопущенноевремяtail;не4+1какфакт','поставкапофазам/часть/задержка/none; P03всеимяветвей; crew/ТО/reserveсверхtailtemplate','P03fleetcalendar иKEEP каждогоборта; existingtail donor илиnewtailalternative','PIN-P03')
a(18,'hub двеодночасовые волны','Пн/Чт KUF↔BAX↔UUD;2tails,4RT/week накаждойрадиали;two banks/day pattern','тонкийвариант1bankday/week; основной2bankdays/week; отсутствиезащитыablation','Сравнениепересадочногоэффекта приодинаковыхрейсах; weekly frequencies сгруппированы','4RT/week имеют2различныхдня,не4; плотностьоборачиваемостииcrewсущественны','ablationбезtransfers;sameflightswithcontract;frequencydispersion ииспользованиесвободныхдней','P05returnchoice,P03crew+maintenance+slots,P04fixedpremium','BAX-A14;BAX-A16;PIN-MODEL')
a(19,'reserve','не выделенфиктивный5йборт; reserveUNKNOWN','UNKNOWN sharedreserve access/response time/cost','Коммерческиготовыйtailнеполныйресурс','ВсеAOG/cancellation/cashboundaries','same reservecontract acrosspairs; BAX vsSVX recovery ferry effects','P03real reservecalendar; P04reserveevents','PIN-P03;PIN-P04')
a(20,'competitor response','no-response иresource-constrained response толькоbranches','UNKNOWN pricefloor/additionaltails/slots;невыбранапроцентнаяскидка','Действующийчастотныйпродукт даётмеханизмреакции,неполнуюэластичность','Необъявлятьнезанятый рынок илиforcedexit','P05repriceсуществующихмест;addcapacityтолькопридоказанномресурсе иslots','P02datedsupply+P03carrierresource+P05calibration','BAX-YANDEX;BAX-KRASAVIA;BAX-N4-TRANSFER')
a(21,'международная/Ту214ветвь','нет дополнительныхТу214вовсехBAXкандидатах','0newTu214явнаяветвь;Sj100internationalapprovalUNKNOWN','ИмеетсяпартнёрскийпутьMSQбезновогобортадальнеймагистрали','Не требуетизобретенияновогоowninternationalbase','partnerretained/withdrawn;rights,tariff,baggage иsettlementseparate','P05partnercontract иP03permissions, nationalflows поP03/P04','RW-BELAVIA')
table('assumptions.csv',ass)

market=[]
def md(mid,kind,from_,to,baseline,change,competition,need,sids,aid):
    market.append({'market_id':mid,'geography_kind':kind,'origin':from_,'destination':to,'period':'2027-01/2028-12 compared with same-period futureKEEP; historical source2025/current2026 separately','unit':'RT/week proposal; passenger journey vs flightsegment separately','baseline_own_sales':baseline,'proposed_change':change,'competitor_or_alternative':competition,'capacity_or_demand':None,'coverage':'частичное покрытие; список не исчерпывающий; UNKNOWN не0','status':'STAGE_A_SPECIFIED_STAGE_B_CONDITIONAL','source_id':sids,'assumption_id':aid,'required_common_input':need})
md('AIR:BAX:SVX','airport_pair','BAX','SVX','ДействующийRW; futureKEEP объём/частотыпоP03','Сохранять; DI1 добавляет2RT/week; ретаймтолькоотдельнымдельтарешением','СобственныепродажиипересадкичерезSVX;OVBground+air','P02clockrepair;P03tailKEEP;P05cannibal/choice','RW-BOARD;PIN-P02','BAX-A01;BAX-A17')
md('AIR:BAX:UUD','airport_pair','BAX','UUD','ДействующийWZ5055/5056; исторический субсидийныйпланнеcalendar','RAD1 сохраняетKEEP;HUB2 additive+4RT/week наMon/Thu, анеполностьюновыйпоток','СобственныйRWпрямойрейс;S7черезOVB требуетdatedsellability','P05oldticketmigration;P03timetabledtails;P04supportdelta','RW-BOARD;BAX-YANDEX;PIN-MODEL','BAX-A01;BAX-A12;BAX-A18')
md('AIR:BAX:HTA','airport_pair','BAX','HTA','RWисторическийитекущийдатированныйWZ5085/86','Сохранить; optionalретаймнеadditivesales; standaloneнеприбавлятькакновыймаршрут','Собственныйпрямой;OVBальтернативатолькосdatedproducts','P03время/цепочка;P05KEEPcoupons','PIN-P02;BAX-YANDEX','BAX-A01')
for dest,comp in [('KUF','СобственныйRWчерезSVX;черезOVB/KZNпоdatedsearch'),('IKT','S7черезOVB ивозможныепрямые/throughstopещёнепокрыты'),('KJA','КрасАвиаKV103/104 наблюдается;airportbindingKJAvsKCY уточнить')]:
    md('AIR:BAX:'+dest,'airport_pair','BAX',dest,'Старыймодельныйdirect_now/absenceнеобновлённыйinventory','RAD1+2RT/week;разнесённыедни;старыйKEEPнеудаляется',comp,'P05monthlyOD/tariff/choice;P02fullcarrierandbag;P03block/slots','PIN-MODEL;BAX-KRASAVIA;BAX-YANDEX','BAX-A08;BAX-A14;BAX-A20')
md('AIR:BAX:PEE','airport_pair','BAX','PEE','АвторскийBAXhubseed;текущийRWdirectUNKNOWN','ДополнительнаярадиальStageBкакзаменаKUFилирасширениеприподтверждённомресурсе','SVXconnection/RW owncapture иOVB:datedavailabilityUNKNOWN','СравнитьBAX-KUF vsBAX-PEE preservingresource, несложитьспрос','PIN-MODEL','BAX-A10;BAX-A17')
md('AIR:BAX:TOF','airport_pair','BAX','TOF','Авторскаякороткаяtransferрадиаль;локальныйспроснеизмерен','Условный2RT/weekfeederвзаменKJA,непараллельнаясвободнаяпрограмма','ground+OVB;даты/ценыавтоиждUNKNOWN','P05transferpool andgroundchoice;P03shortsectorcyclecost','PIN-MODEL','BAX-A07;BAX-A09;BAX-A14')
md('AIR:BAX:OVB','airport_pair','BAX','OVB','S77002ежедневно11:30какpublished;45kисториянеконечныйOD','НовыйRWairfeederневыбран;partner/groundкандидатбезновогоownaircraft','S7прямойплюсавтобусыдоOVB','Сопоставимыйdoor-to-door продукт;нетпартнёрствабезcontract','BAX-YANDEX;BAX-HISTORY;BAX-GROUND','BAX-A07;BAX-A09')
md('AIR:BAX:KZN','airport_pair','BAX','KZN','N4758пн/чт09:05 иистория>30k','Сохранитькакопцию/конкурента;RWentryпоканеотобран','Nordwind прямойипересадкичерезKZNвIST','P05capacityandresponse;поддержкаP04','BAX-YANDEX;BAX-N4-TRANSFER','BAX-A20')
md('AIR:BAX:SGC','airport_pair','BAX','SGC','UT214вдатированномзимнемправиле;спроссегментовUNKNOWN','ОтдельнаясевернаярадиальвStageBтолькоеслиOD/тарифоправдаетзаменуодногосуществующегокандидата','Utairdirect;годоваячастотанеустановлена','P05corporate/VFR=UNKNOWNuntilcoupons;P02quote','BAX-YANDEX;BAX-UTAIR','BAX-A08;BAX-A11')
for dest in ['LED','AER']:
    md('AIR:BAX:'+dest,'airport_pair','BAX',dest,'Поток2025есть;currentAERcalendarнепокрыт','Контекстпрямыхдальнихпродуктов;непереноситьвкороткийSSJmaincaseбезrange/payload','LEDNordwindнаблюдается;AERперевозчик/сезоннужен','P03range/payload;P05samefutureperiod','BAX-HISTORY;BAX-YANDEX','BAX-A02;BAX-A03')
md('CITY:BAX:MOW','city_pair_aggregate','BAX','MOW','433kгородскойагрегат;airportотдельно','Не включатьMOWвphysicalflights;SVO/DME/VKOвыделитьизновыхисточников','DP/S7/SU/U6каксправочноепредложение;airportbindingпроверить','P02airportresolution;P05ODdirectionandmonth','BAX-HISTORY;BAX-YANDEX','BAX-A02')
md('AIR:KUF:UUD','airport_pair','KUF','UUD','FutureKEEPpathsviaSVX/OVBиownsalesUNKNOWN','HUB2даётKUF-BAX-UUDвобоихнаправленияхMon/Thu;однаплатазапоездку','Прямойрынокипересадкинеполностьюисследованы;не0','P05sharedODpoolandchoice;throughfareweights;twoseatsconsumed','PIN-MODEL;RW-BOARD','BAX-A16;BAX-A18')
md('AIR:BAX:MSQ','airport_pair','BAX','MSQ','RW+BelaviaчерезSVXкакобъявленныйкомбинированныйпродукт','РазвиватьдоступностьчерезSVX;новыйBAXhubнеобязателен','OTHERViaKZN/OVBнужныdatedquotes;неприбавлятьсвободныеместаBelavia','P05partnercontract/fare/availability;P03connection','RW-BELAVIA','BAX-A21')
md('AIR:BAX:IST','airport_pair','BAX','IST','NordwindчерезKZNвлетнемобъявлении2026','Конкурентнаямеждународнаяальтернатива;ownBAX-ISTнепроектируетсябезrange/rights','N4transferчерезKZN','P02winterquote;P05substitutiontoRWMSQonlyifrealODsubstitutable','BAX-N4-TRANSFER','BAX-A01;BAX-A21')
md('AIR:BAX:CXR','airport_pair','BAX','CXR','Камраньназванпопулярныммеждународнымнаправлением2025;currentoperatorcalendarUNKNOWN','Отдельныймеждународныйтуристическийконтекст;неSSJ100дальностьпосвойствамгорода','Charter/tourpackage,неизвестныallocationsandfares','P05tourquotas;P03aircrafttype/rights;P04chartercosts;ветвь0Tu214','BAX-2025-FINAL;BAX-2025-APRIL','BAX-A02;BAX-A21')
table('market_deltas.csv',market)

common={
 'status':'CONDITIONAL_STAGE_A_PROGRAMME_NOT_ADMITTED',
 'period':{'main':'2027-01/2028-12','target':'конец2028; общийцелевойпроект8–12уникальныхairportpairs,не8–12изBAX','templates':'датированный2028calendardiagnostic; неyearlyOD/economy'},
 'keep_policy':'Сохранить futureKEEP всехзатронутыхRWпродаж/плеч, включаяBAX-SVX/UUD/HTA. Новыечастотыдобавочныетолькопослефизическойпривязки; не0старуюсеть.',
 'types':[{'variant':'SSJ100/RRJ-95','parameter_status':'наблюдаемыйтип/диагностическийаналог;tailcabin/MTOWпоP03','money':'P04reference+actualcontractneeded'}, {'variant':'SJ100/ПД8','parameter_status':'отдельныйкалендарь/admission/costs,никакогоунаследованногоacceptedSSJperformance','money':None}],
 'deliveries':'P03N(t)поэтапно/частично/задержка/нетновых;0/1/2ниже—порогресурсагруппы,непрогнозпоставкиRW',
 'reserve':'UNKNOWNadditional/sharedreserve;неincludedin1or2commercialtails;одинаковыйконтрактвпарномопыте,географияrecoveryразлична',
 'required_shared_inputs':['P02 datedsellableproductsandclockbinding','P03 all24monthsKEEP+fleet+crew+MRO+slots+ferry+reserve','P04eventdrivers/currentlocalrates/startup/exit/cash','P05 commonODchoice/calibration/cannibalisation/response','P06completeP+KEEPbundlesandacceptedinputs'],
 'no_new_tu214':True,
 'finance_status':'NOT_RUN_NO_P05_CALIBRATION_NO_FULL_KEEP',
 'source_id':['PIN-MODEL','PIN-P02','PIN-P03','PIN-P04','RW-BOARD'],
}
programmes=[]
def prog(pid,role,title,resources,flights,ods,changes,pair,distinguishing,extra=None):
    x={**common,'programme_id':pid,'role':role,'title':title,'resource_group':{'commercial_additional_tails_required':resources,'not_confirmed_free_RW_tails':True,'tail_calendar':'sameP03admittedtailmonths/availabilityascomparison','crew_maintenance_reserve':'UNKNOWN;добавляютсяотдельнымиadmission/events','existing_tail_case':'явныйdonorKEEPиутраченныйрезультат','new_tail_case':'альтернативноеприменениетогоженовогобортаплюсpositioning'},'flight_changes':flights,'target_ODs':ods,'own_sales_changes':changes,'comparison_programme_ids':pair,'distinguishing_test':distinguishing,'assumption_ids':['BAX-A01','BAX-A03','BAX-A06','BAX-A08','BAX-A14','BAX-A15','BAX-A16','BAX-A17','BAX-A19','BAX-A20']}
    if extra:x.update(extra)
    programmes.append(x)
def fc(a,b,n,days,action='ADD',season='зима/лето/межсезоньеотдельновP05;никакогоавтоматическогогодовогозаполнения'):
    return {'origin':a,'destination':b,'action':action,'round_trips_per_week':n,'weekdays_iso':days,'unit':'RT/week;каждыйRTдваadjacentleg','period':'2027–2028толькосadmittedresources;calendarproposal2028','season':season,'status':'PROPOSED_NOT_PUBLISHED','source_id':'BAX-A14;PIN-MODEL','frequency_basis':'Календарныйопытдлительностейпоездки;невыводизконтрактногоспроса'}
prog('P-BAX-KEEP','KEEP','Действующаясетьвтомжебудущемсценарии',0,[],['всеODзатронутыхRWпродаж'],'Необнулятьбилеты,ownconnections,субсидииидонорскиезадания',[], 'ПолныйP03/P05/P04KEEP;непродлениеоднойнедели×52',{'status':'BASELINE_BINDING_REQUIRED','required_observed_pairs':['BAX-SVX','BAX-UUD','BAX-HTA']})
prog('P-BAX-DI1','EXISTING_BASE_DIRECT','ПрямойпродуктSVX–BAXсальтернативнымииспользованиямитогожеборта',1,[fc('SVX','BAX',2,[1,4]),fc('SVX','IKT',2,[2,5]),fc('SVX','KJA',2,[3,7])],['SVX-BAX','SVX-IKT','SVX-KJA','доступныечерезSVXODтолькопопродуктномуadmission'],'KEEPсохранён;инкрементBAXможетканнибализироватьстарыеRWрейсы;IKT/KJAтожеcheckfutureKEEP',['P-BAX-RAD1','P-BAX-ALT1'],'Одинитотжеtailmonthиreserve. Неиспользованныедни/часыразрешеныобщемуoptimizer;корочефлигтнеравноfreeprofit')
prog('P-BAX-RAD1','NEW_RADIAL_BASE','РадиальнаяBAXбазабезобязательныхпересадочныхволн',1,[fc('BAX','KUF',2,[1,4]),fc('BAX','IKT',2,[2,5]),fc('BAX','KJA',2,[3,7])],['BAX-KUF','BAX-IKT','BAX-KJA'],'СтарыеSVX/UUD/HTAнеубираются;transferсегментыавторскогомоделянеприбавляютсяксобственномуспросу',['P-BAX-DI1','P-BAX-ALT1'],'2RT/weekкаждойпаре:return3/4/7/10/14ночейпроверятьпообоимнаправлениям. P05долженпокрытьместныйfixedpremiumпротивSVXбазы',{'local_requirements':['ночнаястоянка','crewpositioningandaccommodation','SSJ100lineMROorapprovedcoverage','AOGrecovery','startup/exitagreements'],'optional_replacements':[{'replace_pair':'BAX-KUF','with_pair':'BAX-PEE','not_additive':True,'reason':'АвторскаяPEEгипотеза;общаяresourceallocationипроверкаперетокаSVX'}, {'replace_pair':'BAX-KJA','with_pair':'BAX-TOF','not_additive':True,'reason':'КороткийfeederтолькоприP05transferandgroundevidence;500kmнеотсев'}]})
prog('P-BAX-ALT1','EXISTING_RESOURCE_ALTERNATIVE','ТотженовыйресурсвсуществующейSVXсетибездобавленияBAX',1,[fc('SVX','KUF',2,[1,4]),fc('SVX','IKT',2,[2,5]),fc('SVX','KJA',2,[3,7])],['SVX-KUF','SVX-IKT','SVX-KJA','сохранённыеfutureKEEPOD'],'BAXKEEPполностьюсохранён;этоalternateuse,необнулениеBAXрынка',['P-BAX-DI1','P-BAX-RAD1'],'Сопоставитьпредельныйэффектadditionalfrequencyпослесобственногоперетока;необъявлятьодинаковыйналётприидентичномчислебортов')
hubflights=[fc('BAX','KUF',4,[1,4]),fc('BAX','UUD',4,[1,4])]
prog('P-BAX-HUB2','NEW_PROTECTED_MINIHUB','ЗащищённыйпродуктKUF–BAX–UUDнадвухновыхкоммерческиххвостах',2,hubflights,['KUF-UUD','BAX-KUF','BAX-UUD'],'UUDпродаётсяRWуже;allincrementalfrequencies+4RTкfutureKEEP. РетаймсуществующегоUUDвместоadd—отдельнаяверсияпослеP03,неэкономияресурсапоумолчанию',['P-BAX-HUB2-LOCAL','P-BAX-EX2'],'Надвухbankdaysпо2RTнарадиаль:4RT/week,но2distinctdays. Дваtailутромоблетаютпротивоположныеспицы,приходятвBAX,меняютстороныпосле90min;обапути+return3/4/7/10/14ночей. ЦенаодинраззаOD,дваseatconsumption',{'connections':[{'path':['KUF','BAX','UUD'],'days':[1,4],'scheduled_bank_minutes':90,'protected_status':None,'revenue_allocation':'P05/P06normalizedweights;неудвоенныйthroughfare'}, {'path':['UUD','BAX','KUF'],'days':[1,4],'scheduled_bank_minutes':90,'protected_status':None}], 'thin_version':'1bankday/week;7/14ночейтолькопроверяемыерeturn;неbusinessdaily','crew_warning':'Длинныйежедневныйspan;единственныйcrewнепредполагается. Разделениеэкипажей/отдых/ротациисогласуетP03;tailsequencePASSнеcrewPASS.'})
prog('P-BAX-HUB2-LOCAL','RADIAL_ABLATION','ТежерейсыичасыдвухбортовBAXсместнымипродуктами',2,hubflights,['BAX-KUF','BAX-UUD'],'ТотжеfutureKEEP/кресла/плечи;нетдобавленныхсквозныхOD,нетплатыдважды',['P-BAX-HUB2'],'Изолироватьценностьprotectedconnections. P05допускаетвыборвнешнихпересадокинадёжность;нетискусственногозапретаконкурентам',{'ablation':'sameflightsandassignments,connectionsremoved;throughcontracteventsdifferent;неокончательныйлучшийradialcalendar'})
prog('P-BAX-EX2','EXISTING_BASE_MIX','ТежедвадополнительныхбортавSVXсBAX/KUF/UUDпродуктами',2,[fc('SVX','BAX',2,[1,4]),fc('SVX','KUF',2,[1,4]),fc('SVX','UUD',2,[2,5])],['BAX-KUF','BAX-UUD','KUF-UUD','локальныеSVXспицы'],'Сохраняетсявсясвоясеть;стыковочныесвоипродажичерезSVXнечужойновыйспрос',['P-BAX-HUB2'],'Существующийузелсравнитьсновымприодинаковыхtailmonths/reserve/externalconditions. ЧастотыразрешеноперераспределятьP06;нельзяценитьнеиспользованныечасыкак0opportunity',{'not_resource_completed':'P03строитwholefleetrotation;здесьтолькоmarketprogramme,неприемкаплотногорасписания'})
prog('P-BAX-PARTNER0','PARTNER_OR_GROUND','ПодвозисуществующиестыковкибезновогоBAXбазирования',0,[],['BAX-MSQчерезSVX','BAX-*черезOVBкаквнешняяальтернатива'],'СобственныйRWчерезSVXсохранён;S7/автобуснестановятсявыручкойRWбезсоглашения',['P-BAX-DI1','P-BAX-RAD1'],'Еслиновыхбортовнет,сравнитьреальныебилетыиcontractedpartnerdistribution;непокупатьблокместнеизобретатькомиссию',{'partner_admission':None,'own_extra_flights':0,'not_alliance_assumption':True})
dump('programme_candidates.json',{'schema_version':'BAX-stageA-v1','not_P06_ready_bundle':True,'programmes':programmes})

h=[]
def hyp(n,title,signal,sids,mechanism,cf,test,anc,outcome,revisit,pids):
    h.append({'hypothesis_id':'H-BAX-'+str(n).zfill(2),'title':title,'signal':signal,'source':sids,'mechanism':mechanism,'counterfactual':cf,'distinguishing_test':test,'ancestorIDs':anc,'outcome':outcome,'evidence_ids':[r['evidence_id'] for r in evidence if r['source_id'] in sids],'condition_for_reconsideration':revisit,'programme_ids':pids,'period':'2027–2028','units':'journeys,seats,tailmonths,RUB/cash separately','coverage':'StageA;экономическийисходconditional','assumption_ids':['BAX-A08','BAX-A17','BAX-A20']})
hyp(1,'РазвиватьдоступностьчерезсуществующийSVXузел','ПоложительнонаблюдаетсяRWсвязьBAX-SVX,собственныевосточныерейсыипартнёрскийMSQ',['RW-BOARD','RW-BELAVIA','PIN-P02'],'Частота/стыковкиулучшаютполныйпутьбезсозданияBAXbase','P-BAX-KEEPиP-BAX-ALT1стемжебортом','P05incrementaljourneysпослеownmigration;P03realreturncalendar',['C22','KIR_PAIR_D','EC_H02'],'CONDITIONAL_STAGE_B_PROGRAMME_SPECIFIED','ПродуктнепроходитеслиlostKEEP/alternativeuseбольшеинкрементаилинепродаютсяобапути',['P-BAX-DI1','P-BAX-PARTNER0'])
hyp(2,'НоваярадиальнаябазаBAX','ОперацииSSJ100допустимыпопубличномуописанию,новыйтерминал;авторскиерадиалиKUF/IKT/KJA',['BAX-PROC2024','BAX-TERMINAL','PIN-MODEL'],'СокращениегеографическогокрюкачерезSVX/OVB+локальныерынки;платаbase/crew/MROможетсъестьэффект','P-BAX-DI1иP-BAX-ALT1стемже1tailmonth','РеальныйобщийOD;ожидаемаяценностьчастоты;fixedpremiumthresholdP04',['AUTHOR:Хаб BAX@dceadc9'],'CONDITIONAL_STAGE_B_PROGRAMME_SPECIFIED','Отказотпостроеннойпрограммыприотсутствииadmissionилинедостаткеэкономическогоheadroom;неотказотвсегогорода',['P-BAX-RAD1'])
hyp(3,'ЗащищённаяминиволнаKUF–BAX–UUD','Географиязапад–восток;UUDужесвойRWпродукт;авторскийtransferhub',['PIN-MODEL','RW-BOARD'],'СквознойODможетповыситьзагрузкуобеихспиц,норасходуетдвафизическихкресла,конкурируетссуществующимиSVX/OVBпродуктами','Сначалаsameflightslocalablation,затемсуществующийSVXузелс2tailmonths','MCT/contract/reliability,returncalendar,сегментноеобщийdemandpoolиfulladdedresult',['AUTHOR:Хаб BAX@dceadc9','C22'],'CONDITIONAL_NOT_ADMITTED','Безподписаннойзащитыэтоradialаблация;отрицательныйрезультатоднойMon/ThuсхемынеопровергаетлюбойBAXhub',['P-BAX-HUB2','P-BAX-HUB2-LOCAL','P-BAX-EX2'])
hyp(4,'OVBавиаподвозvsназемныйпартнёр','45kисторическихобслуживанийBAX-OVB;S7ежедневно;есть5hbusдоаэропорта',['BAX-HISTORY','BAX-YANDEX','BAX-GROUND'],'Удобнаястыковкаилидоговорназемаэкономитновыйtail;catchmentутечкаограничиваетBAXlocalcapture','P-BAX-PARTNER0vsновыйRWfeederлиботажеёмкостьнадлиннойрадиали','Door-to-door,20kgbasket,опозданиеипоследнийобратныйавтобус;нечислонаселения',['AUTHOR:catchment/BAX@dceadc9'],'CONDITIONAL_ZERO_NEW_TAIL_BRANCH_SPECIFIED','Реальныеpartnertermsилиcouponsмогутобосноватьновыйairfeeder;конкурентсампосебенеотказ',['P-BAX-PARTNER0'])
hyp(5,'КороткиеKJA/TOFплечинеисключатьгеометрией','KJA653kmиTOF352kmвавторскомBAXhub;KrasaviaреальнолетаетвКрасноярск',['PIN-MODEL','BAX-KRASAVIA'],'Стыковочныепоездкимогутзагрузитькороткоеплечо;частыепосадкииincumbentснижаютпредельныйэффект','ЗаменаKJAнаTOFвRAD1стемжересурсом,ground/OVBнаружнаяопция','P05реальныйtransferpool+P03cycles+P04costdrivers;не500kmhardgate',['AUTHOR:BAX-KJA/BAX-TOF@dceadc9'],'CONDITIONAL_ALTERNATIVE_NOT_ECONOMIC_REJECTION','ЕслиOD/багаж/groundchoiceобоснуютfeeder—достроить;непокрытыеданныеостаютсяUNKNOWN',['P-BAX-RAD1'])
hyp(6,'МеждународныйпродуктчерезSVXснулёмновыхТу214','RWобъявляетBAX-SVX-MSQ;N4черезKZN-IST;CamRanhистория',['RW-BELAVIA','BAX-N4-TRANSFER','BAX-2025-FINAL'],'ПартнёрскиеплечидаютвыборбезновогоBAXдальнемагистральногопарка','НулевойnewTu214иKEEPсуществующихмеждународныхпродаж','Datedsellability,throughbaggage,settlement,rightsипотерясобственныхпродаж',['C22','AUTHOR:international_context'],'MERGED_WITH_H01_PRESERVING_PROVENANCE','OwninternationalBAXисследоватьтолькоприотдельномспросе/допусках/ресурсе;необъявленопроигравшим',['P-BAX-PARTNER0','P-BAX-DI1'])
hyp(7,'BAXужехаб/свободнаябазаRW','ЕстьнесколькопрямыхRWнаправлений,нонедоказаныbank/contracts/tails',['RW-BOARD','RW-WINTER','PIN-P03'],'Направлениянеравныбазированиюилизащищённымпересадкам','ФактическийрольoutstationснесколькимиRWпродуктами;free_resourceUNKNOWN','Base/crew/MRO/throughcontractиtailassignment',['C22'],'CLAIM_NOT_ESTABLISHED_CITY_NOT_REJECTED','Положительныйдоговор/crew/tailданныеменяютклассификацию;отсутствиеназваниявsupportlistнедостаточно',['P-BAX-KEEP'])
dump('hypotheses.json',{'status':'ALL_REGISTERED_LOCAL_HYPOTHESES_HAVE_EXPLAINED_OUTCOME','hypotheses':h,'not_closed_by_stageA':'Ниодналокальнаяэкономическаягипотезанеобъявленапобедителем/экономическиопровергнутойиз-занеполныхданных.'})

# Calendar/geometry is a deliberately limited offline diagnostic, not P06 acceptance.
geo=json.loads((R/'inputs/geometry_airports.json').read_text())
coords={x['iata']:(float(x['latitude_deg']),float(x['longitude_deg'])) for x in geo['selected_rows']}
def dist(a,b):
    u,v=coords[a],coords[b]; la,lb=map(math.radians,(u[0],v[0]));dlat=lb-la;dlon=math.radians(v[1]-u[1]);return 6371*2*math.asin(math.sqrt(math.sin(dlat/2)**2+math.cos(la)*math.cos(lb)*math.sin(dlon/2)**2))
def block(a,b,speed=700,overhead=35):
    if (a,b)==('BAX','UUD'):return 155
    if (a,b)==('UUD','BAX'):return 175
    return math.ceil((dist(a,b)/speed*60+overhead)/5)*5
fl=[]
def leg(pid,tail,orig,dest,start,date,seq):
    duration=block(orig,dest);arrival=start+dt.timedelta(minutes=duration)
    row={'programme_id':pid,'tail_template_id':tail,'flight_instance_id':f'{pid}-{date}-{tail}-{seq}','origin_airport':orig,'destination_airport':dest,'departure_utc':start.isoformat().replace('+00:00','Z'),'arrival_utc':arrival.isoformat().replace('+00:00','Z'),'block_minutes':duration,'great_circle_km':round(dist(orig,dest),1),'aircraft_variant':'SSJ100_PARAMETER_ANALOGUE_ONLY','seat_count':None,'period':'2028 dated diagnostic; условиедоступностиP03неустановлено','source_id':'geometry_airports.json;RW-BOARD','assumption_id':'BAX-A15;BAX-A16;BAX-A17','status':'PROPOSED_NOT_P03_ADMITTED','coverage':'неAIP/NOTAM/crew/ТО/KEEP/экономика'}
    fl.append(row);return arrival
for dayindex in range(366):
    date=dt.date(2028,1,1)+dt.timedelta(days=dayindex)
    dow=date.isoweekday()
    for pid in ['P-BAX-RAD1','P-BAX-DI1','P-BAX-ALT1']:
        pr=next(x for x in programmes if x['programme_id']==pid)
        for f in pr['flight_changes']:
            if dow in f['weekdays_iso']:
                # 08:00 local at BAX(UTC+7) or SVX(UTC+5).
                start=dt.datetime.combine(date,dt.time(1 if f['origin']=='BAX' else 3),tzinfo=dt.timezone.utc)
                arr=leg(pid,'T1',f['origin'],f['destination'],start,str(date),1)
                leg(pid,'T1',f['destination'],f['origin'],arr+dt.timedelta(minutes=60),str(date),2)
    if dow in [1,4]:
        bank=dt.datetime.combine(date,dt.time(7),tzinfo=dt.timezone.utc)
        for tail,first,second in [('T1','KUF','UUD'),('T2','UUD','KUF')]:
            start=bank-dt.timedelta(minutes=block('BAX',first)+60+block(first,'BAX'))
            x=leg('P-BAX-HUB2',tail,'BAX',first,start,str(date),1)
            x=leg('P-BAX-HUB2',tail,first,'BAX',x+dt.timedelta(minutes=60),str(date),2)
            x=leg('P-BAX-HUB2',tail,'BAX',second,x+dt.timedelta(minutes=90),str(date),3)
            leg('P-BAX-HUB2',tail,second,'BAX',x+dt.timedelta(minutes=60),str(date),4)
table('flight_templates_2028.csv',fl)
groups={}
for f in fl:groups.setdefault((f['programme_id'],f['tail_template_id']),[]).append(f)
diag=[]
for (pid,tail),fs in groups.items():
    fs.sort(key=lambda x:x['departure_utc']);bad=[];mingap=None
    for aa,bb in zip(fs,fs[1:]):
        gap=(dt.datetime.fromisoformat(bb['departure_utc'].replace('Z','+00:00'))-dt.datetime.fromisoformat(aa['arrival_utc'].replace('Z','+00:00'))).total_seconds()/60
        mingap=gap if mingap is None else min(gap,mingap)
        if aa['destination_airport']!=bb['origin_airport'] or gap<60:bad.append((aa['flight_instance_id'],bb['flight_instance_id'],gap))
    diag.append({'programme_id':pid,'tail_template_id':tail,'physical_template_flights':len(fs),'block_hours_2028_diagnostic':round(sum(x['block_minutes'] for x in fs)/60,2),'minimum_turn_minutes':mingap,'sequence_errors':bad,'status':'CONDITIONAL_SEQUENCE_ONLY_PASS' if not bad else 'FAIL','P03admission':'NOT_RUN','crew':'UNKNOWN','maintenance':'UNKNOWN','free_tail':'UNKNOWN','all_futureKEEP':'UNKNOWN','winter_performance':'UNKNOWN','finance':'NOT_RUN'})
dump('resource_diagnostic.json',{'status':'CONDITIONAL_GEOMETRY_SEQUENCE_ONLY','calendar':'2028-01-01..2028-12-31 exactdates;непереноснедели×52','type':'SSJ100_PARAMETER_ANALOGUE_ONLY;SJ100ПД8непроверен','seats':None,'results':diag,'hub_operating_span_hours_max':round(max((dt.datetime.fromisoformat(z[-1]['arrival_utc'].replace('Z','+00:00'))-dt.datetime.fromisoformat(z[0]['departure_utc'].replace('Z','+00:00'))).total_seconds()/3600 for key in ['T1','T2'] for date in ['2028-01-03'] if (z:=sorted([f for f in fl if f['programme_id']=='P-BAX-HUB2' and f['tail_template_id']==key and str(date) in f['flight_instance_id']],key=lambda x:x['departure_utc']))),2),'limits':'Провереныconnectedtailsequenceи60minbufferвдиагностике;неflightplan,неlegalcrew,неиспользованиестарогопаркаиНЕдоказательстводопустимогогодовогоресурса.'})

tz={'BAX':7,'SVX':5,'KUF':4,'IKT':8,'KJA':7,'UUD':8,'PEE':5,'TOF':7,'HTA':9}
def localdate(utc,iata):return (dt.datetime.fromisoformat(utc.replace('Z','+00:00'))+dt.timedelta(hours=tz[iata])).date()
direct_products=[]
for f in fl:
    if f['programme_id']=='P-BAX-RAD1':
        direct_products.append({'programme_id':f['programme_id'],'origin':f['origin_airport'],'destination':f['destination_airport'],'departure_date':localdate(f['departure_utc'],f['origin_airport']),'arrival_date':localdate(f['arrival_utc'],f['destination_airport']),'legs':[f['flight_instance_id']]})
hub_products=[]
hubdates=sorted({f['flight_instance_id'].split('-T')[0].split('P-BAX-HUB2-')[1] for f in fl if f['programme_id']=='P-BAX-HUB2'})
for date in hubdates:
    daylegs=[f for f in fl if f['programme_id']=='P-BAX-HUB2' and ('-'+date+'-T') in f['flight_instance_id']]
    for origin,dest in [('KUF','UUD'),('UUD','KUF')]:
        first=min((f for f in daylegs if f['origin_airport']==origin and f['destination_airport']=='BAX'),key=lambda f:f['arrival_utc'])
        second=min((f for f in daylegs if f['origin_airport']=='BAX' and f['destination_airport']==dest and f['departure_utc']>first['arrival_utc']),key=lambda f:f['departure_utc'])
        hub_products.append({'programme_id':'P-BAX-HUB2','origin':origin,'destination':dest,'departure_date':localdate(first['departure_utc'],origin),'arrival_date':localdate(second['arrival_utc'],dest),'legs':[first['flight_instance_id'],second['flight_instance_id']]})
returnrows=[]
for pid in ['P-BAX-RAD1','P-BAX-HUB2']:
    products=[x for x in direct_products+hub_products if x['programme_id']==pid]
    for origin,dest in sorted({(x['origin'],x['destination']) for x in products}):
        outbound=[x for x in products if x['origin']==origin and x['destination']==dest]
        backdates={x['departure_date'] for x in products if x['origin']==dest and x['destination']==origin}
        for nights in [3,4,7,10,14]:
            eligible=[x for x in outbound if x['arrival_date']+dt.timedelta(days=nights)<=dt.date(2028,12,31)]
            matched=[x for x in eligible if x['arrival_date']+dt.timedelta(days=nights) in backdates]
            returnrows.append({'programme_id':pid,'origin':origin,'destination':dest,'nights':nights,'outbound_dates_inside_return_window':len(eligible),'dates_with_scheduled_return':len(matched),'example_outbound':str(matched[0]['departure_date']) if matched else None,'example_return':str(matched[0]['arrival_date']+dt.timedelta(days=nights)) if matched else None,'unit':'даты вылета в условном календаре; не пассажиры и не вероятность','period':'2028; последние даты без полного окна возврата исключены из знаменателя','coverage':'Обе стороны; только календарный возврат. Inventory/цена/права/MCT/багаж не приняты.','source_id':'flight_templates_2028.csv','assumption_id':'BAX-A14;BAX-A15;BAX-A16;BAX-A18','status':'PROPOSED_CALENDAR_ONLY'})
table('return_calendar_diagnostic.csv',returnrows)
dump('connection_stress_diagnostic.json',{'programme_id':'P-BAX-HUB2','period':'предлагаемый календарь2028','unit':'min','scheduled_connection':90,'grid':[{'assumed_required_MCT':m,'inbound_delay':delay,'effective_connection':90-delay,'calendar_test_pass':90-delay>=m} for m in [45,60,90,120] for delay in [0,30,60]],'status':'ASSUMPTION_GRID_NOT_AIRPORT_MCT_OR_RELIABILITY_ESTIMATE','interpretation':'При требуемом MCT90 задержка30мин уже нарушает эту связь. Это основание проверить buffer и стоимость защиты, не вероятность срыва.','source_id':'flight_templates_2028.csv','assumption_id':'BAX-A16;BAX-A18'})

costs=[]
for cid,driver,val,unit,loc in [('takeoff_landing','mtow_t_per_billed_turn',980,'RUB/tMTOW','1.1'),('security','mtow_t_per_billed_turn',727,'RUB/tMTOW','1.2'),('parking','landing_charge_times_excess_hours',.05,'доляlandingcharge/extrah','1.3'),('terminal_domestic_adult','billable_arriving_departing_transit_adult_pax',90,'RUB/pax','1.4'),('pax_domestic_departing_adult','billable_departing_adult_pax',209,'RUB/pax','1.5.1')]:
    costs.append({'cost_id':'BAX-REF2024-'+cid,'driver':driver,'reference_value':val,'future_2027_2028_rate':None,'unit':unit,'currency':'RUB','price_year':2024,'tax_basis':'безНДС;recoverabilityподоговоруP04','period':'с01.01.2024;неподтверждёндействующийсрок','status':'HISTORICAL_INDEXED_REFERENCE_ONLY_NOT_RW_INVOICE','coverage':'Тольконазваннаяуслуга;неполныйhandling,fuel,crew,MRO,startup,exit','source_id':'BAX-TARIFF2024','source_url':catalog['BAX-TARIFF2024']['url'],'source_locator':loc,'assumption_id':'BAX-A05','P04_mapping':'передатьвevent_rate_map;ниоднойставкиавтоматическивбудущийcostledger','overlap_guard':'Стоянка3hвlanding;не billing дваждымеждународный/внутреннийилиonlinealternative;flight/throughfareдрайверыотдельно','threshold_request':'P04:max_affordable_rate=residual_headroom/driver_quantity;quantity0отдельнаяветвь;headroomтолькоP05/P06'})
table('local_cost_drivers.csv',costs)

requests=[]
def req(i,owner,priority,need,programmes_,test,deliverable,sourceids):
    requests.append({'request_id':'BAX-SB-'+str(i).zfill(2),'owner':owner,'priority':priority,'question_or_missing_field':need,'programme_ids':programmes_,'distinguishing_test':test,'deliverable':deliverable,'unit':'явныеединицывцелевомконтракте','period':'24месяца2027–2028;датыцен+as_of+lead','coverage':'StageBзависимость;неэкономическийотсев','status':'OPEN_NOT_RUN','source_id':sourceids,'assumption_id':'BAX-A01;BAX-A08;BAX-A17'})
req(1,'P02/P03','P0','WZ5076row1083Friday05:00vsRW13Nov12:20;sourceyear/throughstop/physicaladjacency/tail','KEEP;DI1;RAD1;HUB2','Сверитьдату13.11и11.12;одинрейсодинphysicalinstance;правилапонедельникапослеHTAтакжепроверить','CanonicaldatedlegIDs+clockdisposition+inventorycoverage','E-BAX-03;E-BAX-04')
req(2,'P03','P0','FutureKEEPсBAX-SVX/UUD/HTAиallothertailcommitments;actualfreecalendar','all','Неудалятьпрежниезадания/продажи;existingtaildonorvsnewtailalternative','24monthlyfleet/assignments+tailIDs+soldcommitments+phase/partial/delay/no-delivery','PIN-P03')
req(3,'P05/P02','P0','ПомесячныеendpointODBAX-KUF/IKT/KJA/PEE/UUD/HTA/OVB/SVXиKUF-UUD;общиеoutsideoptions','RAD1;HUB2;DI1;ALT1','Однапоездкаодинdemandpool;поток433kMOWи45kOVBнеравенконечномуOD;ownmigration','PinnedsharedOD/marketcalendar/calibratedchoice+unknowncoverage','E-BAX-08;E-BAX-11;E-BAX-34')
req(4,'P02/P05','P0','Сопоставимые1ADT20kgpricesвобонаправлениях+taxes+baggage+quoteas_of+booking_lead','all','Grid:13/16/27Nov,11Dec2026,15Jan/16Mar2027;летний/осеннийвылетприоткрытойпродаже;return3/4/7/10/14nights;неподменятьнедоступноценой0','Datedproductquotebasket,leadindays,sellability,fees,contractandcapacityseparate','PIN-P02;BAX-UTAIR;BAX-YANDEX')
req(5,'P03/airport','P0','BAXbase/SSJ100MROscope/freelinecapacity/crewrooms/overnightstands/slots/2027–2028NOTAM','RAD1;HUB2','ПубличныйSSJ/H24 и600pax/hнеRWдоговор;SJ100ПД8отдельно','Signedorconditionaloperationbundle+exactunknownfields;reserve/recoveryferry','E-BAX-16;E-BAX-17;E-BAX-18;E-BAX-25;E-BAX-26')
req(6,'P04','P0','CurrentBAXtariff/fuel/SGHA/MRO/basecrew/startup/deposit/exitandcashterms','RAD1;HUB2;DI1','2024refsнебудущийдиапазон;накапливатьуслугиодинраз;стоянкасверх3hпосоглашению','ratecatalog+eventdrivers+cashprofiles;maximumaffordablebasepremiumandfuel/parkingthresholds','local_cost_drivers.csv;PIN-P04')
req(7,'P03/P05/P06','P0','HUB2vsLOCALablationandEX2undertwoidenticaltailcalendars','HUB2;HUB2-LOCAL;EX2','Sameflightsablation;EX2samefleet+reservewithalternativeuseofidlehours;черезBAXvsSVX/OVBкоэфзахватанеизобретать','CompleteversionedP/KEEPbundles,operation/choice/financeacceptance,traffic/revenue/margin/cashseparate','programme_candidates.json;resource_diagnostic.json')
req(8,'P02/P05','P1','Competitorresponse:KVexistingKrasnoyarskservices,S7OVB,N4KZN/LED,UtairSGC','RAD1;HUB2','Priceonexistingseatsvsaddcapacityrequiringtail+slots;незаполнятьfreeaircraft0илиunlimited','Resource-constrainedresponsepolicieswithsourcecalibrationandno-responsebranch','E-BAX-27;E-BAX-28;E-BAX-29')
req(9,'P05/airport','P1','2025/2026monthlyrouteactuals;resolve2023sum706181vs723151','all','Сверкаоригинала/охвата;2024forecastnotactual;сезонныйшокпооднойнеделенеидентифицируется','Monthlydatawithreconciliationreceipt;winter/summer/shouldermodel','seasonal_audit.json')
req(10,'P02/P05','P1','GroundOVBbothdirectionsdatedfare/baggage/capacity/lastbus/winterreliability;catchmentoverlapRGK/NOZ','PARTNER0;RAD1','Samejourneyincludesaccess/egress/connectionrisk;S7+busнеRWrevenueбезcontract','Door-to-doorproductrows+exclusivepoolmapping','BAX-GROUND;BAX-GROUND-RETURN;PIN-REASSESS')
req(11,'P03/P05','P1','HUB2crewspan,turn45–90,MCT45/60/90/120anddelay30/60;allreturnlengths','HUB2','Имеющаясяsequenceарифметикаограничена;придлинномcrewdayнужнасмена/стоимость,аНеdeclaredpass','Legalcrew/MRO/positioningcalendars;datedjourneysbothdirections;unservedreturnlist','resource_diagnostic.json;BAX-A16')
req(12,'P04/P05','P1','BAXsupporteligibility2027–2028/deltaKEEP;partnerMSQsettlement/guarantee','PARTNER0;HUB2;RAD1','No-supportvsaccepted-support;100maggregateнекаждаялиния;Belaviaavailabilityнеfreecapacity','Support/cashreceiptscenarios+partnercontracts;0newTu214branch','E-BAX-06;E-BAX-15')
req(13,'P03/P05','P2','ЗаменыKUF→PEEиKJA→TOFвтойжегруппересурса','RAD1','Shortsectorcycles/ground/transferchoice;наличиеконкурента/500kmсамипосебенеreject','Pairedreallocationresults;выходкаждоймодификациисevidence','H-BAX-05;PIN-MODEL')
table('comparison_requests.csv',requests)

dump('case.json',{'case_id':'BAX-RESEARCH-V1','city':'Барнаул','airport':'BAX / UNBB','language':'ru','stage':'A','as_of':NOW,'status':'LOCAL_RESEARCH_AND_CANDIDATE_CONSTRUCTION_COMPLETE_STAGE_B_PENDING','current_RW_role':{'established':'Действующаяточка(outstation)снесколькимиRWпродуктами:SVX,UUD,HTA;дляHTAтекущееправилорасписания,дляUUD/SVXпервичноетабло','base':'UNKNOWN;неустановленоcrew/tailбазирование','protected_hub':'NOT_ESTABLISHED;контрактыMCT/сквознойбагаж/защитанеустановлены','free_aircraft':'UNKNOWN;не0','source_id':['RW-BOARD','RW-WINTER','PIN-P02','PIN-P03']},'decision':'ДопуститьBAXвобщееStageBсравнениекакoutstation/новуюрадиальнуюбазу/условныйзащищённыйминиhub;приоритетсравненияRAD1vsDI1/ALT1иHUB2vsLOCAL/EX2. Доказанногоэкономическогопобедителянет.','demand_geography':{'local_and_regional':'OVB/KJAнаблюдаемыепродукты;TOF/PEE/IKTнуженOD,неотсев','long_distance':'MOW433kгородскойагрегат,LED~66k,AERсопоставимый;2025не2028baseline','east':'СобственныеUUD/HTAсохранитьвKEEP','north':'SGCUtairдатированноепредложение,нетдоказанногокорпоративногоконтракта','international':'MSQчерезSVXpartner;ISTчерезKZNcompetitor;CXRисторияcharter/tourism,неSSJcore','segment_evidence':'Туристическиймеханизмподдержанописаниемкурортов ивнешниминаправлениями;corporate/business/VFR/medicalобъёмыUNKNOWN,необещания.'},'local_operability':'Публичный2024SSJ100/H24/2850x50подтверждаетобщуюпригодность. МестныйбазовыйMRO,crew,stands,slots,latestNOTAM,topfuelcurrentrates,SJ100ПД8допускUNKNOWN. Новыйтерминал2026неприёмкаtransfers.','strong_findings':['WZ5076timeconflictrepairedatlocalobservationlevel;P02timebindingownerrequired','historical2024localcostdriversfound;notfuturepaidrates','primary2023monthlysumdoesnotreconcile;blockedfromseasonalitycalibration','KEEPownsUUD/HTA/SVX;internationalpartnerMSQdoesnotrequireBAXhub'],'publication':'Локальныйпакет;неpublicSite/дашборд/внешнеесообщение','source_pins':'source_pins.json','evidence':'evidence.csv','shared_model_boundary':'Нетсобственногоcalibratedcaptureилиmoneyengine. P05общийспрос/choice;P06совместныйперерасчёт. conditionalgeometryнеoperationalorfinancialacceptance.'})

dump('readiness.json',{'stage_A':'COMPLETE_LOCAL_RESEARCH_CONSTRUCTION','stage_B':'PENDING_COMMON_INPUTS_AND_ACCEPTANCE','evidence_rows':len(evidence),'local_hypotheses':len(h),'programme_candidates':len(programmes),'market_deltas':len(market),'comparison_requests_open':len(requests),'independent_work_completed':['Pinnedinputsfilteredwithrowhashes','PrimaryRW13Novclockconflictcounterexample','Datedlocalcompetitorsandgroundproduct','Airport/terminal/contracts/costdriverlocalgaps','Seasonaldataqualitycounterexample','Programmeandresourcegroups/ownKEEPdeltas','366dayproposedSSJanaloguecalendartemplatesandsequencearithmetic'],'not_run':['P05monthlyODcalibration','Livepriced20kgbasket/bookinginventory','P03crew/MRO/slot/NOTAM/KEEP/resourceadmission','SJ100ПД8operationsandcostacceptance','P06completepairedRWbundles','Fulladdedprofit/cash/marketshare','Independentpackageacceptance'],'unknown_is_not_zero':True,'diagnostic_acceptance':'SEQUENCE_ONLY_CONDITIONAL;негодоваяготовностьпарка','economic_rejections':0,'safe_handoff':'Можноагрегироватьструктуры/requests,нельзяскладыватьавторскиеденьги/потокиилииспользоватьнеadmittedseats.'})

dump('handoff.json',{'package':'BAX research_v1','write_boundary':str(R),'status':'STAGE_A_COMPLETE_STAGE_B_PENDING','entry':'case.json','programme_input':'programme_candidates.json','hypotheses':'hypotheses.json','comparison_queue':'comparison_requests.csv','input_provenance':'source_pins.json + inputs/* source row IDs/hash','local_reference_rates':'local_cost_drivers.csv','clock_action':'P02/P03quarantineP02row1083Friday05:00;freshRW13Nov12:20withUUDturn;неудваиватьрейсы','season_action':'Неимпортироватьseasonal_audit2023рядвP05доreconciliation','minimum_common_integration':['BAX-SVX/UUD/HTAfutureKEEP','0/1/2availablecommercialtailsrequiresP03+reserve+crew+MRO','RAD1vsDI1vsALT1same1tailcalendar;HUB2vsLOCALvsEX2same2tailcalendar','P05sharedjourneys/datedfares/returnavailability/cannibal/response','P04currentBAXrates/basepremium/cashstartupandexit,oldreferenceonly','P06completeP/KEEPbundles;noeconomicwinnerfromofflinecalendar'],'strong_findings':['SSJ100/H24historicalprimaryairportdescription','Newterminal600pax/hmunicipalSep2026report','Local2024tariffdriversandstandslotconditions','Krasavia12NovdatedcompetitionandOVBgroundoption','Sourceclockandseasonalsumcounterexamples'],'files_to_commit':'Толькоэтоткаталогпоoutput_manifest.json;исполнительGitнеменял','coordinator_notes':'Авторскиеinputsсохраненысисторическимиограничениями;StageBприёмкавсяоткрытавreadiness,неопровергнутгородинеготовастратегия.'})

from editorial import edit
edit(R)

# Bounded verification: integrity and internal references, never market/model acceptance.
checks=[]
def ck(n,ok,scope):checks.append({'check':n,'pass':bool(ok),'scope':scope})
ck('requestedoutputs',all((R/x).exists() for x in ['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json']),'packagecompleteness')
ck('hypotheses_unique',len({x['hypothesis_id'] for x in h})==len(h),'IDs')
ck('programmes_unique',len({x['programme_id'] for x in programmes})==len(programmes),'IDs')
ck('every_hypothesis_has_outcome',all(x['outcome'] and x['condition_for_reconsideration'] and x['distinguishing_test'] for x in h),'noUNKNOWNaseconomicreject')
ck('no_sequence_overlap',all(not x['sequence_errors'] for x in diag),'diagnosticonly')
ck('seasonalmismatchpreserved',sum(months)!=723151,'counterexample')
ck('all_evidence_has_source_period_units_coverage',all(x['source_id'] and x['period'] and x['unit'] and x['coverage'] for x in evidence),'sourcegrain')
ck('price_not_fabricated',len(list(csv.DictReader((R/'inputs/P02_fare_panel.csv').open())))==0,'P02BAXadmittedquotecount0doesnotmeanzeroairfare')
for pin in pins:
    if pin.get('selected_file') and pin['selected_file'].endswith('.csv'):
        actual=list(csv.DictReader((R/pin['selected_file']).open())); original=list(csv.DictReader(io.StringIO(gitbytes(pin['sha'],pin['path']).decode())))
        ok=True
        for row in actual:
            ref=original[int(row['input_row_number'])-2]
            ok &= row['input_row_sha256']==hashlib.sha256(json.dumps(ref,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        ck('rowhash:'+pin['selected_file'],ok,'exactpinnedoriginalCSVrow')
dump('verification.json',{'status':'PASS' if all(x['pass'] for x in checks) else 'FAIL','authority':'проверкацелостностиавтором;неindependentacceptance','checks':checks,'limits':'НеclaimsоP05рынке/paidexecution/crew/fleet/финансах'})

manifest=[]
for f in sorted(R.rglob('*')):
    if f.is_file() and f.name!='output_manifest.json' and '__pycache__' not in f.parts:
        manifest.append({'path':str(f.relative_to(R)),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'role':'source_evidence' if '/sources/' in str(f) else 'pinned_extract' if '/inputs/' in str(f) else 'research_output_or_reproducer'})
dump('output_manifest.json',{'package_root':str(R),'manifest_version':'v1','status':'STAGE_A_COMPLETE_STAGE_B_PENDING','hash_algorithm':'SHA256exactfilebytes;manifestexcludedfromitsownlist','files':manifest,'write_boundary':'Толькоэтоткаталог;Gitбезизмененийисполнителя','not_include':['чужиеполныеfixtures','зависимости','__pycache__'],'independent_acceptance':'PENDING'})
print(json.dumps({'status':'built','evidence':len(evidence),'hypotheses':len(h),'programmes':len(programmes),'markets':len(market),'requests':len(requests),'flight_template_rows':len(fl),'checks_pass':all(x['pass'] for x in checks),'files':len(manifest)},ensure_ascii=False))
