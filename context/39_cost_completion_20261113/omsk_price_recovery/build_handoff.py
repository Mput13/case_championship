from pathlib import Path
import csv,json,hashlib
P=Path('/home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/39_cost_completion_20261113/omsk_price_recovery')
OMS='https://www.aeroomsk.ru/aviakompaniyam/stavki-i-tarify/2026/tarifs_rus_20260821.pdf'
rows=[]
fields='id article classification unit min max currency tax effective source access page provenance overlap quantity payer free_window treatment excerpt'.split()
def add(i,a,u,v,page,cl='DIRECT_OMS',q='UNKNOWN',note='',src=OMS,tax='кроме того НДС; ставка/освобождение по законодательству, численный НДС UNKNOWN',date='2026-08-21',free='не указано; UNKNOWN',treat='per use',prov='первичный PDF; визуальная сверка скана',ex='excerpts/oms_tables.txt'):
 lo,hi=(v,v) if not isinstance(v,tuple) else v
 rows.append(dict(zip(fields,[i,a,cl,u,lo,hi,'RUB',tax,date,src,'2026-11-13',page,prov,'Не добавлять к ground 96089/115307 RUB/flight до itemization; '+note,q,'Заказчик услуги; для OMS см. договор p8 §6.1; конкретный договор RW UNKNOWN',free,treat,ex])))
add('OMS-RACK','Аренда стойки представителя авиакомпании/турфирмы (информирование), не DCS check-in','рабочее место на 1 рейс или обслуживание',1229.51,'2 §2.3',q='число заказанных рабочих мест × обслуживаний UNKNOWN')
add('OMS-BAG','Перегрузка/снятие/погрузка груза, почты и багажа с/на ВС или между ВС по заявке авиакомпании при задержках или иных причинах, включая повторные операции','обслуживание',4450,'3 §2.15',q='число дополнительных заказанных обслуживаний UNKNOWN',note='Прямая OMS цена вместо PKC; это НЕ тариф за кг и не безусловная надбавка за каждый трансферный чемодан')
add('OMS-MEAL-DISTR','Раздача бортпитания пассажирам в аэровокзале с отметкой в билете','обслуживание',3275,'2 §2.8',q='число заказанных обслуживаний UNKNOWN',note='Не стоимость еды; отдельно от цены рациона')
for i,a,v,sec in [('PASS-PERM','Личный постоянный пропуск работника организации на территории аэропорта',696.72,'5.2.1'),('PASS-OUT','Постоянный входной пропуск работника сторонней организации',696.72,'5.2.2'),('PASS-ONCE','Разовый входной пропуск сторонней организации',209.02,'5.2.3')]:
 add('OMS-'+i,a,'штука',v,'4 §'+sec,q='количество оформляемых пропусков UNKNOWN',treat='разовый при выдаче; постоянный до 5 лет' if i!='PASS-ONCE' else 'per entry/pass')
add('OMS-ESCORT','Сопровождение и контроль транспорта и работников сторонних организаций по территории и к ВС','обслуживание',4050,'4 §5.3',q='число заказанных сопровождений UNKNOWN')
add('OMS-CITYBUS','Предоставление автобуса по городу','моточас за каждый начинающийся час',3430,'5 §8.1',q='сумма оплачиваемых начатых моточасов UNKNOWN',note='Локальная прямая услуга, не маршрутная закупка аэропорт–отель; вместимость/подача/минимум UNKNOWN')
for band,monthly,hour,daily in [('30–74.999 т',117100,1018,24432),('75–99.999 т',130200,1140,27360)]:
 add('OMS-BASE-'+band,'Базирование на асфальтобетоне, МВМ '+band,'ВС/месяц',monthly,'5 §9.1.1',q='число ВС соответствующей группы × месяцев базирования UNKNOWN',note='Выбор договора базирования и проверка пересечения со стоянкой обязательны',treat='monthly')
 add('OMS-PARK-H-'+band,'Временная стоянка на асфальтобетоне №0–23, МВМ '+band,'ВС/час',hour,'6 §9.2.1',q='оплачиваемые часы UNKNOWN',note='Не суммировать автоматически с §1.1.3, суточной стоянкой и базированием')
 add('OMS-PARK-D-'+band,'Временная стоянка на асфальтобетоне №0–23, МВМ '+band,'ВС/сутки',daily,'6 §9.3.1',q='оплачиваемые сутки UNKNOWN',note='Альтернатива почасовой схеме после согласования, не дополнительный слой',treat='per day')
for heat,v,sec in [('неотапливаемом',330,'11.19.1'),('отапливаемом',1000,'11.19.2')]:
 add('OMS-WH-'+sec,'Складское хранение имущества в '+heat+' помещении','м²/месяц',v,'10 §'+sec,q='площадь м² × месяцы UNKNOWN',note='Услуга хранения имущества, не доказанная аренда офиса или самостоятельного склада',treat='monthly')
add('OMS-IT-TEL','Телефонная связь','договор/тариф Ростелекома','UNKNOWN','11 §14.2',cl='UNKNOWN',q='линии/трафик UNKNOWN',note='Источник отсылает к тарифам Ростелекома; это не интернет/DCS quote')
add('OMS-IT-TGM-IN','Обработка поступающей абоненту телеграммы','телеграмма',6.23,'11 §14.3',note='Не DCS/интернет')
add('OMS-IT-TGM-AV','Авиационная наземная сеть передачи данных и телеграфной связи','телеграмма',55.60,'11 §14.4',note='Не подменять тарифом стоимость DCS или широкополосного канала')
for i,a,unit,v,sec in [('LAND','Взлет-посадка','т МВМ',911,'1.1.1'),('SEC','Транспортная безопасность','т МВМ',947,'1.1.2'),('PAX','Обслуживание взрослого пассажира ВВЛ','пассажир',200,'2.1')]:
 add('REF-'+i,a,unit,v,'1 §'+sec,cl='REFERENCE_ONLY',note='ТОЛЬКО СВЕРКА, не новая добавка')
add('REF-PARK-EXCESS','Сверхнормативная стоянка: 5% сбора взлет-посадка за 1 час','0.05 × применимый сбор взлет-посадка/час','UNKNOWN','1 §1.1.3',cl='REFERENCE_ONLY',q='сверхнормативные часы UNKNOWN',note='Нормативное бесплатное окно в просмотренном прайсе не определено; не ставить 3/6 часов по памяти')
for i,a in [('OFFICE','Аренда офиса'),('DCS','DCS, регистрационные стойки с системой и лицензии'),('IT','Интернет/каналы/установка/поддержка'),('GSE','Покупка GSE/оборудования наземной станции')]:
 add('UNKNOWN-'+i,a,'договор/спецификация','UNKNOWN','1–11 (полный прайс просмотрен)',cl='UNKNOWN',q='площадь/линии/оборудование UNKNOWN',note='Не найдена самостоятельная численная строка; quote и scope required; покупка и outsourcing той же функции взаимоисключающие')
add('UNKNOWN-SALARY','Station/passenger agent gross salary OMS','сотрудник/месяц','UNKNOWN','официальная страница вакансий',cl='UNKNOWN',q='FTE=Σ(посты × часы покрытия за период)/эффективный фонд часов сотрудника; все входы UNKNOWN',src='https://www.aeroomsk.ru/ob-aeroporte/vakansii/',tax='gross/net и взносы UNKNOWN',date='дата публикации UNKNOWN; access 2026-11-13',prov='первичная страница просмотрена; пригодный station gross rate не установлен',ex='excerpts/nonprice_sources.txt',note='Вилка 42000–50000 из предыдущего агрегатора не допущена')
FLAG='https://hotelflagman.ru/ru/preyskurant-cen'
for i,a,v in [('HOTEL-SINGLE','Флагман стандарт RO, одноместное',4100),('HOTEL-DOUBLE','Флагман стандарт RO, двухместное',4650)]:
 add('ANALOG-'+i,a,'номер/сутки',v,'HTML таблица строки 1',cl='ANALOGUE_LOCAL_UNIT',src=FLAG,tax='UNKNOWN; НДС на странице не раскрыт',date='2026-02-01–2026-12-31',prov='первичный прайс поставщика; HTML bytes saved',ex='excerpts/flagman.txt',q='число фактически оплачиваемых номеров × ночей UNKNOWN',note='Не airline distressed-passenger quote и не частота нарушений',free='не указано',treat='per room night')
add('ANALOG-MEAL-DELTA','Флагман: разница BB−RO для одноместного стандарта = 5050−4100','завтрак в пакете/чел',950,'HTML строки 1–2',cl='ANALOGUE_DERIVED',src=FLAG,tax='UNKNOWN',date='2026-02-01–2026-12-31',prov='инженерное вычитание двух первичных тарифов; не отдельная цена завтрака',ex='excerpts/flagman.txt',q='завтраки UNKNOWN',note='Нельзя добавлять к цене номера BB; meal purchase quote UNKNOWN')
add('ANALOG-AERO-BREAKFAST','Гостиница Аэро, завтрак при безналичном бронировании','чел/завтрак',430,'HTML indexed snippet',cl='ANALOGUE_INDEX_ONLY',src='https://www.wm-3.ru/index.php/pitanie',tax='UNKNOWN',date='UNKNOWN',prov='только поисковый индекс первичного сайта; web timeout и direct TLS expired; bytes не получены',ex='excerpts/index_only.txt',q='количество завтраков UNKNOWN',note='Не fully primary-byte-verified; не применять как заключенный airline contract')
add('ANALOG-BUS','Автобус1, Нефаз 5299, 44 места, минимум 4 часа, от','автобус/час',(3000,'UNKNOWN'),'HTML Нефаз 5299',cl='ANALOGUE_LOCAL_UNIT',src='https://omsk.avtobus1.ru/uslugi/transfer',tax='UNKNOWN',date='UNKNOWN; observed 2026-11-13',prov='первичная страница поставщика; HTML bytes saved',ex='excerpts/bus.txt',q='число заказов × max(4; оплачиваемые часы) UNKNOWN',note='Минимум от 12000 RUB/заказ = 3000×4; не цена на пассажира и не маршрутный airline contract',free='нет; минимум заказа 4 часа')
PKC='https://pkc.aero/upload/iblock/4ef/l9aevzf4ka9oq29xig8g0fdtr10w6p8t/Preyskurant-na-uslugi-i-tvary-AO-MAPKE-dlya-rossiyskikh-potrebiteley-uslug-po-sostoyaniyu-01.03.2025.pdf'
add('PKC-1690-AUDIT','Перегрузка багажа с борта одного ВС на борт другого по заявке авиакомпании','кг',16.90,'поисковый индекс, строка между supervisor и additional departing services; PDF page UNKNOWN',cl='ANALOGUE_INDEX_ONLY',src=PKC,tax='без НДС по заголовку индексированной таблицы',date='2025-01-01',prov='Индекс первичного PDF подтверждает формулировку; оригинал и одна альтернатива HTTP404. Проверки первичных bytes/page нет',ex='excerpts/index_only.txt',q='кг дополнительной перегрузки UNKNOWN',note='Не почта/не обычная обработка по индексированной строке; но прежний PASS отозван как недоказанный; использовать прямую OMS §2.15 с иной единицей')
with (P/'prices.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
(P/'excerpts/oms_tables.txt').write_text('''Manual transcription from rendered scans; page numbers are PDF pages (1-based). Price column throughout: «Ставка сбора, тариф, цена, кроме того НДС*». All prices RUB. Effective 21.08.2026, appendix 1 to order №452 dated 06.08.2026.
p2 §2.3 Аренда стойки (рабочего места) для представителя турфирмы или авиакомпании (информац. обеспечение пассажиров и прочее - на 1 рейс или 1 обслуживание): рабоч. место — 1 229,51.
p2 §2.8 Раздача пассажирам бортового питания в здании аэровокзала с отметкой в билете, за 1 обслуживание: единица — 3 275,00.
p3 §2.15 Перегрузка/снятие/погрузка груза, почты и багажа с/на ВС или между ВС (по заявке авиакомпании при задержках или по иным причинам, в том числе повторное снятие или погрузка), за 1 обслуживание: единица — 4 450,00.
p4 §5.2.1 Личный пропуск для работников организаций, расположенных на территории аэропорта (постоян. до 5-и лет): штука — 696,72.
p4 §5.2.2 для входа на территорию аэропорта лиц сторонних организаций (постоянный до 5-и лет): штука — 696,72.
p4 §5.2.3 для входа на территорию аэропорта лиц сторонних организаций (разовый): штука — 209,02.
p4 §5.3 Сопровождение и контроль транспортных средств и работников сторонних организаций по территории аэропорта и к ВС, за 1 обслуживание: единица — 4 050,00.
p5 §8.1 Предоставление автобуса по городу (стоимость одного моточаса за начинающийся час): час — 3 430,00.
p5 §9.1.1 Базирование (на асфальтобетоне): МВМ от 30 до 74,999 тн — мес — 117 100,00; от 75 до 99,999 тн — мес — 130 200,00.
p6 §9.2.1 Временная стоянка на аэродроме (на асфальтобетоне: стоянки с №0 по №23): МВМ 30–74,999 тн — час — 1 018,00; 75–99,999 тн — час — 1 140,00.
p6 §9.3.1 то же: МВМ 30–74,999 тн — сутки — 24 432,00; 75–99,999 тн — сутки — 27 360,00.
p10 §11.19 Складское хранение имущества: §11.19.1 в неотапливаемом помещении — 1 кв.м. — месяц — 330,00; §11.19.2 в отапливаемом помещении — 1 кв.м. — месяц — 1 000,00.
p11 §14.2 Услуги телефонной связи — по тарифам ПАО «Ростелеком».
p11 §14.3 Обработка поступающей в адрес абонента телеграммы — единица — 6,23.
p11 §14.4 Услуги авиационной наземной сети передачи данных и телеграфной связи (за 1 телеграмму) — единица — 55,60.
p11 footnote: «начисление НДС - в соответствии с действующим законодательством, услуги 7.1 и 7.2 - не облагаются НДС в соответствии с пп. 2 п. 2 ст. 149 НК РФ.» Numeric VAT rate is NOT supplied by this price list; do not silently apply 20% or 22%.
p1 reference only: §1.1.1 взлет-посадка — тн — 911***; §1.1.2 транспортная безопасность — тн — 947***; §1.1.3 стоянка сверхнормативная — 5% от сбора за взлет-посадку за 1 ч.; §2.1 обслуживание пассажиров ВВЛ взрослые — 200,00. No free parking window stated here. *** coefficients p11: aircraft up to 5.7t .25; >5.7 to12t .5; aircraft >12t 1; helicopters >12t .5.
No standalone office, DCS, broadband or station-GSE purchase quote identified in all eleven visually inspected pages. Warehouse service is not a self-contained property lease.
''')
(P/'excerpts/amendments.txt').write_text('''Visual transcription; each amendment 1 PDF page.
Order №568, 30.09.2026, effective 10.10.2026: §13.1 fluid type I Aviaflo EG 211000 RUB/tonne, besides VAT; §13.2 type IV Aviaflight EG, Green Flo 246 RUB/litre, besides VAT; §10.1.3 departure AN-2/MI-8 and other 2–9.999t aircraft 1875 RUB/unit besides VAT. None changes the admitted narrow-scope ground launch rows. Fluid costs not added (other role scope).
Order №610, 14.10.2026, effective 15.10.2026: §2.9.2 VIP service departure/arrival conditional on >1000 business lounge users in preceding month now 5740 RUB/person besides VAT. None changes narrow-scope rows.
''')
(P/'excerpts/contract_verified.txt').write_text('''Downloaded primary generic contract ano-2026.pdf; 24 scanned pages. Visually inspected pages 5–8, not a full contract audit.
p5 §4.2.8 customer pays for provided services, work and transferred goods under section 6.
p6 §5.2 additional services upon customer request and subject to technical capability; list is in published price list. §5.6 standard baggage responsibility spans acceptance to aircraft loading for departing baggage and unloading to delivery for arrivals: do not assume every transfer constitutes an incremental §2.15 service.
p8 §6.1 customer pays prices/tariffs effective at date of aircraft service. §6.2 registered/published rates; other prices approved by airport; price list published at aeroomsk.ru. §6.4 RUB settlements. §6.7.1 regular and off-schedule flights 100% prepayment of flight service volume before handling starts, with unused difference credited to future prepayment. This is working capital, not a second expense/deposit annual charge. Customer-specific signed RW scope, standing window and discounts UNKNOWN.
''')
(P/'excerpts/index_only.txt').write_text('''Captured from web search 2026-11-13; not a local copy of the primary PDF/page.
PKC original index result: table header «Размер тарифа без НДС»; row «Тариф за перегрузку багажа с борта одного ВС на борт другого ВС»; «руб./ кг»; «01.01.2025»; «16,90»; «(по заявке авиакомпании)». Alternative January 2025 PDF search result has the same row. Both direct PDF URLs HTTP404 with HTML bodies. Thus original assertion is lexically corroborated by primary-site search index, but primary-PDF page validation remains incomplete. Never label PASS.
Aero hotel official food page indexed text: «Дополнительные услуги (оплачиваются отдельно): - завтрак - 430 руб/чел *; * при бронировании номера по безналичному расчету». Web open timeout; direct TLS certificate expired. Effective date and VAT unspecified. Index-only confidence, not raw HTML verified.
Aero standard room search result showed 3800 single/4800 double/5900 triple per day; web 502/direct TLS failed. These room prices are not admitted; one local alternative Flagman obtained instead.
''')
(P/'excerpts/nonprice_sources.txt').write_text('''Official OMS tenant page https://www.aeroomsk.ru/partneram/arendatoram/ web opened 2026-11-13: commercial retail spaces on terminal first/public and second/sterile floors; availability by inquiry. No numeric rent. Stop after airport primary page; no office price invented.
Official vacancy page https://www.aeroomsk.ru/ob-aeroporte/vakansii/ web opened 2026-11-13: published engineering and maintenance occupations with salary figures, but no admitted station/passenger agent gross rate. Publication date and gross/net not established. Do not substitute unrelated engineer salaries or previous secondary 42000–50000 salary for RW station payroll. FTE UNKNOWN; engineering formula Σ(posts × coverage hours)/effective employee hours over same period, inputs all UNKNOWN.
Correct index spelling: /stavki-i-tarify/ opens, user/prior /stavki-i-taryfy/ fails. Index links Russian tariff effective 21.08.2026 and changes 10.10/15.10.2026.
''')
# Remove misleading extensions on saved 404 HTML responses.
for n in ['pkc','pkc_alt']:
 f=P/'sources'/f'{n}.pdf'
 if f.exists() and not f.read_bytes().startswith(b'%PDF'):f.rename(P/'sources'/f'{n}_http404.html')
manifest=[]
for f in sorted((P/'sources').iterdir()):
 b=f.read_bytes();manifest.append(dict(file=str(f.relative_to(P)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),pdf_magic=b.startswith(b'%PDF')))
(P/'sources_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
with (P/'validation.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['id','check','result','refs','limitation'])
 for r in rows:
  result='VISUALLY_VERIFIED_PRICE_ONLY' if r['classification'] in ['DIRECT_OMS','REFERENCE_ONLY'] else ('UNKNOWN' if r['classification']=='UNKNOWN' else 'INDEX_ONLY_NOT_PDF_VERIFIED' if 'INDEX_ONLY' in r['classification'] else 'LOCAL_VENDOR_UNIT_ONLY')
  w.writerow([r['id'],'source/page/unit/classification/overlap/quantity',result,r['source']+' | '+r['page']+' | '+r['excerpt'],r['quantity']+'; '+r['tax']])
 w.writerow(['AMENDMENTS','both changes read','VERIFIED_SCOPE_UNCHANGED','sources/oms_amend_1010.pdf p1; sources/oms_amend_1015.pdf p1; excerpts/amendments.txt','not a complete annual budget'])
print('rows',len(rows),'primary files',len(manifest))
