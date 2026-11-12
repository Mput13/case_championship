"""Build the bounded MCX Stage A package; no network, Git mutation or monetary model."""
import csv, json, pathlib, hashlib, math, re, datetime, collections

D = pathlib.Path(__file__).resolve().parent
ASOF = '2026-11-12'
def write(name, obj):
    (D/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
def table(name, rows):
    assert rows, name
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (D/name).open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=keys);w.writeheader();w.writerows(rows)
def load(name): return json.loads((D/name).read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

pins = {'panel':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',
        'five_city':'c18f7640ea36647a05b39089e5293f22dd009f63',
        'plan':'65cab12d2eae49dc91d1f77dd4860bc9bd7e20d2',
        'P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458',
        'P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f',
        'P03':'79dc698b99dfe866886d32376ed388e85bdd039c',
        'P04':'620a0ac4bb11763319c4227485f6a3996b91d367',
        'P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}

assumptions=[]
def assumption(id, value, unit, why, source, sensitivity, refine, bounds='UNKNOWN'):
    assumptions.append(dict(assumption_id=id,value=value,unit=unit,period='2027–2028, если не оговорено иначе',
        selected_by='исследователь MCX / Sol6.1 xhigh',basis=why,source_id=source,
        range_or_unknown=bounds,status='исследовательский сценарий; не решение команды',
        coverage='локальный Stage A; не калибровка P05',affected_conclusions=sensitivity,
        sensitivity=sensitivity,refinement=refine))
assumption('A-MCX-YEAR','2026-10…2027-03','календарь','В строках аэропорта есть DD.MM без года; текущая зимняя интерпретация нужна только для диагностики.','MCX-SCHEDULE;P02-A07','Без подтверждения года датированные места не допускаются. Лето и 2028 не экстраполируются.','Подтвердить год у аэропорта/перевозчика.')
assumption('A-MCX-FREQ','2 оборота на пару в неделю','roundtrip/week','Разные дни позволяют 2/5 или 3/4 ночи и недельные возвраты. Это дизайн теста, не оптимум из спроса.','MCX-SCHEDULE;DAG-TOUR2026','Проверить 1/2/3 оборота, 2/3/4/5/7/10/14 ночей; 1 оборот не даёт короткий отдых.','P05: месячный спрос, willingness to pay и календарь поездок.','конечные опыты 1,2,3; экономически допустимый диапазон UNKNOWN')
assumption('A-MCX-BLOCK','0.5 + ортодромия/750; PEE–MCX=170min; MCX–AER=105min','block_h / min','Формула времени сохранена из авторской network.csv; PEE наблюдается 10:00–14:50 UTC+3/+5 у продавца, AER=1:45 опубликовано RW. Остальные времена только прокси.','PIN-PANEL;MCX-PEE-PRICE;RW-NNM-AER','Номинальная выполнимость меняется при длинной трассе/ветре; повторить блок-время ×1.2. Точность прокси UNKNOWN.','P03: датированные UTC, тип/MTOW/багаж/ветер/трасса; не использовать для топлива.')
assumption('A-MCX-TURN','45','min','Явный промежуточный разворот в условном шаблоне; не норма аэропорта или RW.','P03','Повторить 30/45/60min; MRO и реальные turn constraints могут отменить шаблон.','Договор handling, task cards и утверждённый turn по типу.','сценарии 30/45/60; эмпирический диапазон UNKNOWN')
assumption('A-MCX-CAP','10','block_h/tail/day','Сохраняется авторский planning cap для сопоставимого диагностического теста. Не норма рабочего времени экипажа.','PIN-PANEL','Проверить 8/10h; duty elapsed, crew rest проверяются независимо.','P03: AFM/crew roster/flight-duty calendar.','сценарии 8 и10; эксплуатационный предел UNKNOWN')
assumption('A-MCX-SEATS','100','nominal seats/flight','Одинаковый аналог из авторской модели нужен только для отчёта геометрической ёмкости; не салон будущего SJ.','P03;RW-BASE2022','Заменить на точный tail cabin/blocked seats. Продажи не равны этим местам.','P03: конфигурация каждого борта, ПД-8 отдельно.')
assumption('A-MCX-MCT','90; stress 60/120; max 240','min','Проектный порог для внутренней волны; опубликованный RW MCT в MCX не найден. Максимум ожидания — спецификация теста.','P03;MCX-SCHEDULE','При задержке60min обратное окно105min превращается45min и не проходит90min.','Утверждённые MCT, terminal/baggage path, misconnect и reaccommodation.','конечные тесты; юридический/операционный MCT UNKNOWN')
assumption('A-MCX-RESOURCE','1 активный борт: radial/direct; 2: wave; резерв отдельно','tail group','Полные замкнутые недельные обороты требуют группы, а не одного рекламируемого плеча. Это дополнительные задания общему парку.','P03;P06','Необеспеченный резерв, crew или donor переводят запуск в NOT_ADMITTED.','P03: хвосты/даты/KEEP/ТО/crew/резерв; P04: цены занятых и резервных tail-months.')
assumption('A-MCX-KEEP','весь затронутый бизнес и проданные места сохраняются до явного действия','journey/flight/tail','Текущие северные, международные и базовые рейсы RW не обнуляются при добавлении лучей.','P00R;P06;MCX-SCHEDULE','Дельта считается после собственного перетока; потеря донора входит в P−KEEP один раз.','P03 KEEP по датам; P05 existing sales и shared pool.','UNKNOWN по количествам; не 0')
assumption('A-MCX-DELIVERY','P03: поэтапно / частично / задержка / 0','service-ready tail/date','Новых самостоятельных дат поставок MCX не создаём; запуски зависят от общего календаря.','P03','Без новых SJ в2027–28 только KEEP/retiming с доказанным свободным окном или передача SSJ с донором.','Общий P03 accepted delivery/service-entry календарь; не ранее H2 2027 для новых SJ.')
assumption('A-MCX-SEASON','лето: июнь–сентябрь; shoulder: апрель–май/октябрь; зима: ноябрь–март','месяц','Разделение экспериментов для туристического продукта; месячные веса не назначены. Даты скидочного сезона отличаются и хранятся отдельно.','DAG-TOUR2026','Весенний шок2026 нельзя превращать в ровный ежегодный рост; месячные объёмы UNKNOWN.','P05:2025/26 по месяцам, периоду и сегменту.')
assumption('A-MCX-RATES','только опубликованные 2025/2026 reference rates','RUB2025/2026','Ни один прейскурант не принят автоматически как будущий договор. НДС и cash через P04.','MCX-TARIFF2025;MCX-HANDLING2025;MCX-FUEL2026;P04','База, ТО/crew, launch/exit и будущие тарифы UNKNOWN; новый приказ2026 может менять регулируемые ставки.','P04 применимость/обновление/индексация/возмещаемый НДС/условия платежей.')
assumption('A-MCX-DISCOUNT','без скидки как контроль; отдельная договорная ветвь','coefficient','Ред15 опубликована, но титул приказа не заполнен, подписанный договор RW не представлен; скидки не складываются.','MCX-DISCOUNT15','PEE обслуживает конкурент: не новое направление по критерию365 дней всех перевозчиков. RW не новый перевозчик.','Действующая утверждённая редакция, допсоглашение RW, база начисления, срок/termination/clawback.','право и фактическая ставка UNKNOWN')
assumption('A-MCX-DISC6','6 направлений в тексте; «6 полетов» в таблице','threshold unit UNKNOWN','Существующие шесть intl station-pairs позволяют проверить экономическую связанность программы, но единица ступени неоднозначна.','MCX-DISCOUNT15;MCX-SCHEDULE','При льготе одинаковой в P иKEEP общая экономия не добавочный результат проекта. Новый рейс ради скидки может ухудшить итог.','Письменное определение порога/eligible fuel/decade; сверить фактически выполняемые направления.')
assumption('A-MCX-RESPONSE','сохранение предложения / переоценка билетов / допоборот при доказанном ресурсе','response scenario','Не присваиваем произвольный ответный процент или свободные борта конкуренту.','MCX-SCHEDULE;P02','На PEE incumbent SSJ может менять цену без нового хвоста. Рост частот требует отдельного tail/slot/crew.','P02 accepted response policy + P05 price/frequency elasticity.','UNKNOWN по размерам реакции')
assumption('A-MCX-FARE','3544 RUB, вылет2026-11-27, найдено продавцом за предыдущие48h','RUB/one-way indicative','HTTP-копия Туту 12.11 отличается от поискового кэша. Сохранён конкретный снимок; цена не проверена в корзине.','MCX-PEE-PRICE','Lead от retrieval15дней; от истинной котировки15–17дней. Багаж/сборы/инвентарь UNKNOWN; yield не калибруется.','P02: live dated comparable basket, суммарная цена + багаж + refunds + party size.','не ценовой диапазон; actual paid fare UNKNOWN')
assumption('A-MCX-GROUND','partner/подвоз без новых самолётов','product','MCX обслуживает регион с наземным продолжением до Дербента/Каспийска; это часть той же поездки, не отдельный aviation OD.','MCX-ABOUT;DERBENT-GROUND','Airport access, ночной трансфер, задержки и цена могут изменить short-break choice. Договор RW отсутствует.','Расписание/лицензия/страхование/цена и SLA наземного перевозчика.','UNKNOWN по объёму/ставке/времени')
table('assumptions.csv', assumptions)

# Turn the airport snapshot into reproducible, deduplicated rule observations.
from acquire import clean
s=(D/'sources/MCX-SCHEDULE.html').read_text()
parts=re.split(r'<div class="c-flight-board__item" data-id="(\d+)">', s)
rules=[]
airport_map={'Нижневартовск':'NJC','С-Петербург (LED)':'LED','Душанбе':'DYU','Новый Уренгой':'NUX',
    'Москва (Внуково)':'VKO','Сочи':'AER','Дубай':'DXB','Минеральные Воды':'MRV','Джидда':'JED',
    'Тюмень (Рощино)':'TJM','Наманган':'NMA','Екатеринбург (SVX)':'SVX','Бухара':'BHK',
    'Москва (Шереметьево)':'SVO','Пермь (Большое Савино)':'PEE','Дубай (Аль-Мактум)':'DWC',
    'Самара (Курумоч)':'KUF','Ташкент':'TAS','Стамбул':'UNKNOWN_IST_OR_SAW','Новосибирск (Толмачево)':'OVB',
    'Казань':'KZN','Сургут':'SGC','Калининград (Храброво)':'KGD','Москва (Домодедово)':'DME',
    'Бишкек (Манас)':'BSZ','Ургенч':'UGC','Москва (Жуковский)':'ZIA','Медина':'MED','Амман (Марка)':'ADJ'}
for i in range(1,len(parts),2):
    rowid=parts[i]; chunk=parts[i+1]
    # Hash only the matching row chunk; the full source hash also remains pinned.
    flight=re.search(r'c-board-info__link">(.*?)</span>',chunk)
    if not flight: continue
    fields={clean(k).strip():' '.join(clean(v).split()) for k,v in re.findall(r'<h3 class="c-board-info__title">(.*?)</h3>\s*<p class="c-board-info__text">(.*?)</p>',chunk,re.S)}
    dest=fields.get('Направление','UNKNOWN'); time=fields.get('Время вылета','UNKNOWN')
    rules.append(dict(row_id=rowid,row_sha256=hashlib.sha256(chunk.encode()).hexdigest(),
        flight=clean(flight[1]).strip(),origin='MCX',destination=airport_map.get(dest,'UNKNOWN'),
        destination_label=dest,departure=time,aircraft=fields.get('Воздушное судно','UNKNOWN'),
        routing_label=fields.get('Пересадки','UNKNOWN'),schedule=fields.get('График','UNKNOWN'),
        carrier=fields.get('Авиакомпания','UNKNOWN'),source_id='MCX-SCHEDULE',status='опубликованное правило; год явно не указан',
        unit='station-pair schedule rule',period='DD.MM в источнике',coverage='вылеты; неполный источник рынка',
        as_of=ASOF,fare_rub='UNKNOWN',baggage='UNKNOWN',booking_lead_days='не котировка',
        physical_inventory_id='UNKNOWN',assumption_id='A-MCX-YEAR'))
table('local_schedule_rules.csv',rules)
summary=[]
groups=collections.defaultdict(list)
for r in rules:groups[(r['destination'],r['carrier'],r['flight'])].append(r)
for (dst,carrier,flight),rr in sorted(groups.items()):
    summary.append(dict(origin='MCX',destination=dst,carrier=carrier,flight=flight,
        rule_count=len(rr),rule_ids=';'.join(r['row_id'] for r in rr),
        aircraft=';'.join(sorted(set(r['aircraft'] for r in rr))),
        observed_rules=' | '.join(r['schedule']+'; '+r['departure'] for r in rr),
        source_id='MCX-SCHEDULE',status='опубликовано; не частота за год и не физический инвентарь',
        unit='правила расписания',period='зимний снимок DD.MM, предположение2026/27',coverage='одна сторона, один источник',as_of=ASOF))
table('competition_summary.csv', summary)

def year_date(text):
    day,month=map(int,text.split('.'));return datetime.date(2026 if month>=10 else 2027,month,day)
weekdays={'пн':0,'вт':1,'ср':2,'чт':3,'пт':4,'сб':5,'вс':6}
dated=[]
for r in rules:
    match=re.search(r'(.*?)период (\d{2}\.\d{2})\s*[–-]\s*(\d{2}\.\d{2})',r['schedule'])
    if not match:continue
    start,end=year_date(match[2]),year_date(match[3])
    if end<start:continue # summer rule year ambiguous, no inference
    days=set(range(7)) if 'Ежедневно' in match[1] else {v for k,v in weekdays.items() if k in match[1]}
    for window in [('2026-12-11','2026-12-17'),('2027-01-08','2027-01-14')]:
        date=datetime.date.fromisoformat(window[0]); stop=datetime.date.fromisoformat(window[1])
        while date<=stop:
            if start<=date<=end and date.weekday() in days:
                dated.append(dict(window='/'.join(window),date=date.isoformat(),origin='MCX',destination=r['destination'],
                    carrier=r['carrier'],flight=r['flight'],departure_local=r['departure'].rsplit(' ',1)[-1],
                    source_row_id=r['row_id'],source_row_sha256=r['row_sha256'],source_id='MCX-SCHEDULE',
                    status='условная календарная развёртка; не admission',unit='предложение на дату',
                    period=date.isoformat(),coverage='исходный год/physical inventory UNKNOWN',assumption_id='A-MCX-YEAR'))
            date += datetime.timedelta(days=1)
table('schedule_date_diagnostic.csv', dated)

receipts=load('fetch_receipts.json')
org={'RW':'АО «Ред Вингс»','MCX':'АО «Аэропорт Махачкала»','DAG':'Правительство Республики Дагестан',
     'AZ':'АО «Авиакомпания Азимут»','DERBENT':'туристический портал Дербента'}
dates={'RW-WINTER':'2026-10-27','RW-BASE2022':'2022-11-14','RW-NNM-AER':'2026-02-20',
    'MCX-STATS2024':'2025-01-09','MCX-STATS2025':'2026-03-20','MCX-STATS2026':'2026-11-11',
    'DAG-TOUR2026':'2026-10-26','MCX-PEE-HISTORY':'2026-02-02','MCX-FUEL2026':'действует с2026-01-01',
    'MCX-TARIFF2025':'действует с2025-03-05','MCX-HANDLING2025':'действует с2025-07-23',
    'MCX-DISCOUNT15':'2025; номер/дата утверждающего приказа не заполнены'}
sources=[]
for r in receipts:
    sid=r['source_id']; prefix=sid.split('-')[0]
    organization=org.get(prefix,'см. URL')
    if sid=='MCX-STATS2026' or sid=='MCX-RECONPLAN':organization='Минтранс Республики Дагестан'
    if sid=='MCX-RECON2026':organization='Минтранс Российской Федерации'
    if sid=='MCX-STATS2025':organization='Финмаркет / сообщение министра транспорта Дагестана'
    if sid=='MCX-PEE-HISTORY':organization='В курсе.ру / сообщение краевого Минтранса'
    if sid=='MCX-PEE-PRICE':organization='Туту, продавец / ранее найденные предложения пользователей'
    sources.append(dict(source_id=sid,url=r['url'],organization=organization,publication_date=dates.get(sid,'UNKNOWN; дата снимка отдельно'),
        retrieved_at=r['retrieved_at'],as_of=ASOF,period=dates.get(sid,'текущий снимок2026-11-12; не прогноз2027–28'),
        unit='зависит от claim; см. evidence.csv / local_cost_references.csv',grain='документ / airport / опубликованное правило',
        status='HTTP200 сохранено' if r.get('http_status')==200 else 'не получено: '+r.get('error','UNKNOWN'),
        coverage='локальная публикация, не полный рынок/договор RW',sha256=r.get('sha256','UNKNOWN')))
for k,v in pins.items():
    sources.append(dict(source_id='PIN-'+k.upper(),url='git:'+v,organization='авторский пакет команды / '+k,
        publication_date='по commit',retrieved_at=ASOF,as_of=ASOF,period='точная версия входа',unit='blob/строка',grain='закреплённый вход',
        status='прочитанные blob указаны в input_manifest.json' if k!='five_city' else 'контекст происхождения; MCX не входил в пять городов',
        coverage='только MCX и необходимые сравнительные рынки/контракты',sha256='см. input_manifest.json'))
table('sources.csv', sources)

evidence=[]
def ev(id,src,claim,val,unit,period,coverage,limitation,status='подтверждено публикацией; границы см. coverage',locator='см. сохранённый источник'):
    evidence.append(dict(evidence_id=id,source_id=src,claim=claim,value=val,unit=unit,period=period,coverage=coverage,
        status=status,as_of=ASOF,locator=locator,limitation=limitation))
ev('E-MCX-ROLE-HISTORY','MCX-ABOUT','RW стала базовой компанией25.04.2022','2022-04-25','дата','история2022','аэропорт прямо называет историческую базу','Не число текущих хвостов, не текущий MRO/crew договор.')
ev('E-MCX-ROLE-CURRENT','RW-WINTER','MCX — опорный аэропорт RW','опорный','роль','зима2026/27','официальное заявление перевозчика27.10.2026','Не доказан защищённый transfer hub или свободный парк.')
ev('E-MCX-ROLE-PRIMARY','RW-BASE2022','RW сама называла MCX базовым аэропортом','базовый','роль','2022-11','исторический первичный источник','Не переносится автоматически на базовую мощность2028.')
ev('E-MCX-PAX24','MCX-STATS2024','Пассажиропоток MCX2024; international часть','2898731;355441','airport passenger movements/year','2024','прибывшие+убывшие, все перевозчики','Не уникальные поездки, не RW, не OD. Domestic=2543290 арифметически, без распределения по рынкам.')
ev('E-MCX-PAX25','MCX-STATS2025','Пассажиропоток2025 около2.8млн','2800000','airport passenger movements/year, округлено','2025','весь аэропорт, вторичное сообщение министра','Не экстраполировать как рост или спрос на луч.')
ev('E-MCX-PAX26','MCX-STATS2026','Январь–сентябрь2026','2071000','airport passenger movements/9months','2026-01/09','весь аэропорт','Неполный год; нельзя умножать на12/9 для прогноза без сезонности.')
ev('E-MCX-PEE25','MCX-PEE-HISTORY;PIN-P02','PEE–MCX36865 пассажиров2025','36865','airport route passenger movements/year','2025','пара аэропортов, оба направления по контексту списка; метод учёта уточнить','Не monthly demand и не объём доступный RW; явная потребность в grain adapter.',locator='P02 historical_demand_context.csv:14; новый HTTP В курсе.ру строка80')
ev('E-MCX-SEGMENTS','MCX-STATS2024;DAG-TOUR2026;RW-NNM-AER','Обоснован туристический сегмент: внутренний отдых, морской отдых и сезонные отмены','туризм','тип поездки','2024–2026','сегмент подтверждён, доли/OD неизвестны','Корпоративные, сменные, этнические/VFR и паломнические доли не установлены; география рейса не доказывает мотив.')
ev('E-MCX-SHOCK','DAG-TOUR2026','Отмены туров апрель–июнь доходили до30%; восстановление к августу','до30%','доля отменённых туров по данным туроператоров','2026-04/06;2026-08','по сообщению правительства; не все авиапассажиры','Не падение авиаOD на30%; отдельный joint shock scenario без коэффициента спроса из этой цифры.')
ev('E-MCX-COMP','MCX-SCHEDULE','PEE Азимут вт/пт, AER Азимут пн/чт, SGC Победа ежедневно+Nordwind','см. competition_summary.csv','опубликованные правила','DD.MM, условная зима2026/27','carrier/airport-pair; одна сторона','Не полный список; места/продажа/черезпродукты/год UNKNOWN.',locator='airport data-id и HTML-chunk SHA256 в local_schedule_rules.csv')
ev('E-MCX-INTL','MCX-SCHEDULE','У RW опубликованы TAS/BHK/NMA/UGC/DYU/BSZ','6','уникальных station-pairs','снимок2026-11-12','не число ежедневно работающих направлений','Не достаточное доказательство порога скидки или наличия кресел; DYU и BSZ могут иметь ограничения по типу/трассе.')
ev('E-MCX-NNM','RW-NNM-AER','Летний NNM→MCX→AER: вт, с28апреля, SSJ100;4:25+1:45','265;105','min per published leg','лето2026','объявленные продажи; багажи10+10кг','Не подтверждение2027/28. Четырёхплечевой возврат того же борта дал бы740block min до разворотов; он не обещан источником.')
ev('E-MCX-RECON','MCX-STATS2026;MCX-RECON2026','К11.11 сообщён ввод новой ВПП; реконструкция остальных объектов продолжается','3200','m, по МинтрансуРФ','сентябрь/ноябрь2026','статусы инфраструктуры во времени','В сентябре ждали разрешения; в ноябре сообщён ввод. Не конфликт одинаковой даты и не допуск SJ/ПД8;8 стоянок — проект, не свободные места RW.')
ev('E-MCX-OPS','PIN-P03;MCX-TECH500;MCX-HOTEL','Текущий RW ТО/crew/слоты/ночноестоянки/MCT не подтверждены','UNKNOWN','договор/слот/тип/смена','2026-11;2027–28','сайты технических сведений/гостиницы не дали содержательных условий','Опубликованный тариф нормочаса или мойкиSSJ не сертификат типа и не договорRW. UNKNOWN не0.')
ev('E-MCX-FARE','MCX-PEE-PRICE','Туту показывает3544₽ с вылетом27.11; история предложений за48h','3544','RUB/one-way indicative','departure2026-11-27;retrieval2026-11-12','маршрут+перевозчик, не итоговая корзина','Lead отretrieval15дней; baggage/fees/booking time UNKNOWN; поисковый кэш5785₽/17.11 отличается и не подменяет снимок.')
ev('E-MCX-BAG','AZ-BAGGAGE','Азимут: Light без checked bag, Flexible23kg; cabin5kg','0;23;5','kg, по brand','текущий снимок2026-11-12','условия брендов; не бренд котировки3544₽','Нельзя автоматически прибавить/назначить багаж котировке.')
ev('E-MCX-BASE-CONTRACT','MCX-DISCOUNT15','Опубликованы условные коэффициенты и договорная процедура','0.8 winter;0.9 summer','coefficient, regional services','ред15,2025;действиеUNKNOWN','применимость после заявки+допсоглашения; исключены московские аэропорты иLED','Приказ на титуле не заполнен; P04 принимает после проверки. Новое направление —365дней отсутствия у всех перевозчиков, RW не новый перевозчик.')
ev('E-MCX-FUEL-THRESHOLD','MCX-DISCOUNT15','Понижение топлива при базировании и >=6 международных направлений','0.95…0.90','coefficient; table6…11 ступени','ред15,2025;действиеUNKNOWN','текст говорит направления, таблица полёты','Нельзя автоматом считать6 частот/дней; одна льгота на eligible топливо, не сумма с другими скидками.',locator='section3.8; таблица8 в sources/MCX-DISCOUNT15.tables.json')
ev('E-MCX-GROUND','DERBENT-GROUND','Наземное продолжение до Дербента; у города нет своего аэропорта','UNKNOWN','door-to-door min/RUB','период страницыUNKNOWN','первичный туристический портал найден поиском','HTTP TLS certificate verify failed; web open TimeoutError. Числа119/253/313км из search-only не приняты как точный airport access или catchment.','найденный первичный источник; содержимое полностью не получено')
ev('E-MCX-OLDMODEL','PIN-PANEL','Старый MCX hub — конкретный шаблон, не опровержение города','8 routes в прежнем сценарии','авторские модельные направления','версияdceadc98,2028 условно','точные MCX rows сохранены','MOW агрегат не аэропорт, 52-недельная annualization, demand и own sales не калиброваны общимP05; старые деньги не складываются.')
table('evidence.csv',evidence)

costs=[]
def cost(id,label,rate,unit,src,loc,why):
    costs.append(dict(cost_reference_id=id,airport='MCX',component=label,rate=rate,unit=unit,
        currency='RUB',price_year='2026' if 'FUEL' in src else '2025',vat_basis='без НДС',
        period='с2026-01-01' if 'FUEL' in src else 'с2025-07-23' if 'HANDLING' in src else 'с2025-03-05',
        source_id=src,locator=loc,as_of=ASOF,status='историческая опубликованная ставка; будущая NOT_ADMITTED',
        coverage=why,driver_required='точное количество P06 + MTOW/тип/units/договор и даты P04',
        assumption_id='A-MCX-RATES',avoid_double_count='один shared_event_id; новые услуги не складывать с заменённой старой строкой'))
cost('MCX-C01','взлёт-посадка',310,'RUB/t MTOW','MCX-TARIFF2025','p1 row1.1','Не складывать альтернативный тариф307 за исключение отдельныхопераций; коэффициенты по группе ВС p7.')
cost('MCX-C02','транспортная безопасность',192,'RUB/t MTOW','MCX-TARIFF2025','p1 row1.3','Группа самолётов>12t: коэффициент1 по примечаниюp7; будущий тариф проверить.')
cost('MCX-C03','аэровокзал, domestic adult',42.12,'RUB/departing adult passenger','MCX-TARIFF2025','p1 row1.5 + p7','Для детей2–12лет50%, до2лет0 согласно источнику; нужен passenger mix.')
cost('MCX-C04','пассажирское обслуживание domestic adult',95,'RUB/departing adult passenger','MCX-TARIFF2025','p1 row2.1 + p7','Детские коэффициенты поp7; не все занятые сегменты равны adult departures.')
cost('MCX-C05','аэровокзал international adult',77,'RUB/departing adult passenger','MCX-TARIFF2025','p1 row1.5','Отдельно от domestic; eligibility по договору.')
cost('MCX-C06','пассажирское обслуживание international adult',225,'RUB/departing adult passenger','MCX-TARIFF2025','p1 row2.1','Выделить собственный терминал/погранконтроль, не присвоить MCT.')
cost('MCX-C07','трап',9782.27,'RUB/unit','MCX-HANDLING2025','p1 row1','Более поздняя опубликованная строка вместо6521.51 из05.03; единица не автоматически1наоборот.')
cost('MCX-C08','автобус',9429.52,'RUB/unit','MCX-HANDLING2025','p1 row2','Замещает6286.35; нужно числорейсов/автобусов, не числоflight legs.')
cost('MCX-C09','буксировка',18102.69,'RUB/service','MCX-HANDLING2025','p1 row3','Замещает9051.35; контракт на условия каждого использованияUNKNOWN.')
cost('MCX-C10','приём/выпуск ВС>40до80t',17035.32,'RUB/service','MCX-TARIFF2025','p3 row4.2','Точный MTOW каждого SSJ/SJ требуется; не ставка техобслуживания двигателя.')
cost('MCX-C11','временная стоянка ВС>40до80t',3150.66,'RUB/aircraft/day','MCX-TARIFF2025','p3 row3.3','Отдельная услуга; сверхнормативная стоянка5%/h изp1 не прибавляется автоматически.')
cost('MCX-C12','оперативное ТО',3073.81,'RUB/norm-hour','MCX-TARIFF2025','p3 row4.1','Не1block-hour! Объём работ/материалы/типовой допуск/свободная мощностьRWUNKNOWN.')
cost('MCX-C13','обеспечение заправки',1077,'RUB/t uplift','MCX-TARIFF2025','p3 row3.1','Проверить входитли в цену fuel contract; не умножать на всё сгоревшее топливо если uplift в других аэропортах.')
cost('MCX-C14','ТС-1',91000,'RUB/t uplift','MCX-FUEL2026','p1','Полная опубликованная сумма111020RUB/t сНДС22%; cashVAT через P04. Не net fuel после акциза.')
table('local_cost_references.csv',costs)

# Two explicit paired diagnostic weeks; not a 52-week or paid market model.
coords={}
for p in (D/'inputs').glob('*airports*.local.json'):
    for r in load(str(p.relative_to(D))):
        a=r['row'];coords[a['iata_code']]=(float(a['latitude_deg']),float(a['longitude_deg']))
def hav(a,b):
    p,q=coords[a],coords[b];a1,a2=map(math.radians,p);b1,b2=map(math.radians,q)
    return 6371*2*math.asin(math.sqrt(math.sin((b1-a1)/2)**2+math.cos(a1)*math.cos(b1)*math.sin((b2-a2)/2)**2))
old=load('inputs/dceadc98_network_routes.csv.extract.json')
dist={}
for x in old:
    r=x['row'];
    if r['from']=='MCX' and r['to'] in ['PEE','CEK','UFA']:dist[r['to']]=float(r['km'])
blocks={frozenset(('MCX',a)):round((.5+d/750)*60) for a,d in dist.items()}
blocks[frozenset(('MCX','PEE'))]=170
blocks[frozenset(('MCX','AER'))]=105
for a in ['PEE','CEK','UFA']:blocks[frozenset(('SVX',a))]=round((.5+hav('SVX',a)/750)*60)
def block(a,b):return blocks[frozenset((a,b))]
rot=[]
def rotation(candidate,week,weekday,tail,route,start):
    base=datetime.datetime.fromisoformat(week+'T00:00:00+00:00')+datetime.timedelta(days=weekday,minutes=start)
    for index,(a,b) in enumerate(zip(route,route[1:])):
        end=base+datetime.timedelta(minutes=block(a,b))
        rot.append(dict(programme_id=candidate,week_start=week,day_iso=weekday+1,tail_group=tail,
            draft_leg_id=f'{candidate}:{week}:{weekday}:{index}',origin=a,destination=b,
            departure_utc=base.isoformat(),arrival_utc=end.isoformat(),block_minutes=block(a,b),
            flight_action='условное добавочное задание; продажи/донор требуют binding',nominal_seats=100,
            aircraft_variant='SSJ100_SaM146_ANALOGUE; SJ100_PD8 отдельный повтор',
            source_id='PIN-PANEL;P03;MCX-PEE-PRICE;RW-NNM-AER',
            assumption_id='A-MCX-BLOCK;A-MCX-TURN;A-MCX-SEATS;A-MCX-RESOURCE',
            status='геометрический диагностический шаблон; не разрешённый flight schedule',
            period='одна неделя; не год',unit='dated physical draft leg',coverage='нет slots/crew/ТО/KEEP binding'))
        base=end+datetime.timedelta(minutes=45)
for week in ['2028-07-03','2028-12-11']:
    for dst,days in [('UFA',[1,3]),('CEK',[2,5]),('PEE',[4,6])]:
        for day in days:
            rotation('P-MCX-RADIAL',week,day,'T-MCX-1',['MCX',dst,'MCX'],360)
            rotation('P-MCX-DIRECT',week,day,'T-SVX-1',['SVX',dst,'MCX',dst,'SVX'],240)
    for day in [1,4]:
        # The control has the same routes, tails and flight counts but short ground turns.
        # It saves dwell time; it must not be assigned zero old sales by the common model.
        rotation('P-MCX-WAVE-UNSYNC',week,day,'T-WAVE-1',['PEE','MCX','AER','MCX','PEE'],420)
        rotation('P-MCX-WAVE-UNSYNC',week,day,'T-WAVE-2',['CEK','MCX','CEK'],420)
        # Tail1 based at PEE for this operating day, rights/contracts UNKNOWN.
        base=datetime.datetime.fromisoformat(week+'T00:00:00+00:00')+datetime.timedelta(days=day)
        for tail,legs in [('T-WAVE-1',[('PEE','MCX',420),('MCX','AER',720),('AER','MCX',870),('MCX','PEE',1080)]),
                          ('T-WAVE-2',[('CEK','MCX',420),('MCX','CEK',1080)])]:
            for idx,(a,b,start) in enumerate(legs):
                begin=base+datetime.timedelta(minutes=start);end=begin+datetime.timedelta(minutes=block(a,b))
                rot.append(dict(programme_id='P-MCX-WAVE',week_start=week,day_iso=day+1,tail_group=tail,
                    draft_leg_id=f'P-MCX-WAVE:{week}:{day}:{tail}:{idx}',origin=a,destination=b,
                    departure_utc=begin.isoformat(),arrival_utc=end.isoformat(),block_minutes=block(a,b),
                    flight_action='условная волна; full KEEP до явного изменения',nominal_seats=100,
                    aircraft_variant='SSJ100_SaM146_ANALOGUE; SJ100_PD8 отдельный повтор',source_id='PIN-PANEL;P03;MCX-PEE-PRICE;RW-NNM-AER',
                    assumption_id='A-MCX-BLOCK;A-MCX-TURN;A-MCX-MCT;A-MCX-RESOURCE;A-MCX-SEATS',
                    status='диагностический шаблон; не admission',period='одна неделя; не год',unit='dated physical draft leg',coverage='crew/overnight/MCT/слоты/KEEP UNKNOWN'))
table('rotation_diagnostics.csv',rot)
resource=[]
for (pid,week),rows in __import__('itertools').groupby(sorted(rot,key=lambda r:(r['programme_id'],r['week_start'])),lambda r:(r['programme_id'],r['week_start'])):
    rows=list(rows);pairs={tuple(sorted((r['origin'],r['destination']))) for r in rows};daily=collections.defaultdict(int)
    for r in rows:daily[(r['tail_group'],r['day_iso'])]+=r['block_minutes']
    resource.append(dict(programme_id=pid,week_start=week,active_tail_groups=len({r['tail_group'] for r in rows}),
        physical_legs=len(rows),unique_airport_pairs=len(pairs),block_minutes=sum(r['block_minutes'] for r in rows),
        max_daily_tail_block_minutes=max(daily.values()),over_10h_days=sum(v>600 for v in daily.values()),
        over_8h_days=sum(v>480 for v in daily.values()),
        reserve='UNKNOWN; общая группа резерваP03 отдельно, не0',crew_mro_keep_admission='UNKNOWN',
        status='рассчитано только время/позиции при условных блоках',unit='tail/week;min/week',period=week+'/7дней',coverage='две диагностические недели, без годовой экстраполяции',source_id='rotation_diagnostics.csv',assumption_id='A-MCX-BLOCK;A-MCX-CAP;A-MCX-RESOURCE'))
table('resource_summary.csv',resource)

common={'horizon':['2027-01','2028-12'],'target_role':'локальный фрагмент общей сети8–12пар кконцу2028, не самостоятельная стратегия№2',
    'status':'сконструирован Stage A; экономика/полный ресурс Stage B NOT_RUN',
    'source_ids':['PIN-PANEL','PIN-P00R','PIN-P02','PIN-P03','PIN-P04','PIN-P06','MCX-SCHEDULE'],
    'aircraft_branches':['существующийSSJ100/SaM146 с названным донором или подтверждённым окном',
        'новыйSJ100/ПД8: отдельныеperformance/cost/crew/MRO inputs, service_entry изP03',
        'новыхSJ0: KEEP либо доказанное retiming; без выдуманного свободного хвоста','новыхТу2140: все основные опыты сохраняются'],
    'fleet_calendar':'один и тот же P03 delivery/availability/reserve/KEEP в каждой паре; fractional tail недопустим',
    'delivery_branches':['поэтапно поP03','частично поP03','задержка поP03','0 в2027–28'],
    'preserved_business':'все фактически проданные затронутые северные/международные/чартерные/базовые продуктыRW, без автоматической отмены',
    'economic_method':'только общийP05 choice/demand +P06 +P04; здесь нет собственной денежной или захватной модели',
    'season_definition':'A-MCX-SEASON; monthly demand UNKNOWN, сезонные тарифы/субсидии отдельно',
    'cost_thresholds':['P04 TH-OPTION','TH-FIXED','TH-FARE','TH-FUNDING','TH-LAUNCH'],
    'needed_common_inputs':['P02 dated complete competitor baskets + physical inventories','P03 exact KEEP/tails/crew/MRO/slots/entry','P04 accepted events+cash+local contract','P05 non-overlapping monthly journeys+choice','P06 accepted common runs+independent acceptance'],
    'assumption_ids':[a['assumption_id'] for a in assumptions]}
programmes=[]
def programme(id,role,hypotheses,flights,ods,counterfactual,resource,why,changes,stages,extra=None):
    p=dict(common);p.update(programme_id=id,role=role,hypothesis_ids=hypotheses,flights=flights,journey_ods=ods,
        counterfactual=counterfactual,resource=resource,selection_mechanism=why,own_sales_changes=changes,
        stage_sequence=stages,readiness='конкретный research candidate, не engine-ready bundle')
    if extra:p.update(extra)
    programmes.append(p)
baseflights=[{'pair':'MCX-'+dst,'roundtrips_per_week':2,'weekdays_iso':days,'seasons':['лето','межсезонье','зима — отдельная проверка'],
    'action':'только после проверки existingRW; add или явный retiming/upgrade, не автоматически новый рынок',
    'unit':'roundtrip/week','period':'активные месяцы2027–28 после service_entry','coverage':'предложение для теста','source_id':'MCX-SCHEDULE;PIN-PANEL','assumption_id':'A-MCX-FREQ'}
    for dst,days in [('PEE',[5,7]),('CEK',[3,6]),('UFA',[2,4])]]
programme('P-MCX-RADIAL','развитие существующего опорного узла как радиальной базы',['H-MCX-01'],baseflights,
    ['MCX–PEE','MCX–CEK','MCX–UFA'],['P-MCX-DIRECT','KEEP с тем же новым ресурсом на лучшем альтернативном заданииP03'],
    {'active_tails':1,'initial_final_location':'MCX','reserve':'общая группаP03 UNKNOWN','cycles_week':12,
     'diagnostic':'resource_summary.csv','base_months':'только реальные месяцы базирования; договорное minimum/pay-or-use UNKNOWN'},
    'PEE даёт наблюдавшийся маршрутный поток, воскресенье дополняет вт/пт incumbent; CEK/UFA сравнительные радиальные кандидаты с происхождением в авторской модели, спрос ещё не доказан.',
    'PEE/CEK могли быть собственными историческими рынкамиRW; отделить возврат/переток от gross new. SVX/KUF/NJC/TJM/NUX иintl не сокращать молча.',
    ['2027: KEEP и сбор условий; запуск при получении service-ready ресурса не раньшеH2 дляновогоSJ',
     '2028: сезонный пилот по подтверждённым месяцам; зимняяветвь послеP05/P04','остановка новых продаж до предельного бюджета ликвидности; проданные места обслужить/перебронировать поP06 actions'])
directflights=[dict(pair='SVX-'+dst+'-MCX-'+dst+'-SVX',roundtrips_of_MCX_pair_per_week=2,weekdays_iso=days,
    action='полный четырёхплечевой оборот; продажа short legs отдельно занимает те же физические кресла',
    source_id='PIN-PANEL;P03',assumption_id='A-MCX-FREQ;A-MCX-BLOCK;A-MCX-KEEP',unit='закрытый оборот/week',period='те же активные месяцы чтоRADIAL',coverage='все4плеча')
    for dst,days in [('PEE',[5,7]),('CEK',[3,6]),('UFA',[2,4])]]
programme('P-MCX-DIRECT','прямые MCX-продукты полным оборотом из существующей базыSVX',['H-MCX-01'],directflights,
    ['MCX–PEE','MCX–CEK','MCX–UFA','SVX–PEE/CEK/UFA — отдельный общий pool, не бесплатный доход'],
    ['P-MCX-RADIAL','KEEP со всеми теми же доступными tail-weeks'],
    {'active_tails':1,'initial_final_location':'SVX','reserve':'общая группаP03 UNKNOWN','cycles_week':24,'diagnostic':'resource_summary.csv'},
    'Позволяет сравнить те же три прямые парыMCX с отсутствием новой ночной базыMCX. Экономия базы оплачивается дополнительными плечами и временем, при этом short legs могут иметь свои продажи/наземную конкуренцию.',
    'Существующие продажиSVX-short иMCX не назначаются twice. Сдвиг прямогоSVX–MCX и loss donor полностью вKEEP/P. При нехватке duty сокращать только явным вариантом.',
    ['тот же календарьввода и внешнего сценария','сопоставить1/2/3оборота ипереносдней; максимум общейценности ресурса, не result/flight'],
    {'safety_of_comparison':'TAIL-WEEK одинаков; block-hours не обязаны быть равны. Остаток времени обеих программ получает общее альтернативное задание либо отражается неиспользованным с оплатой. Разные доступные продажи учитываетP05.'})
programme('P-MCX-WAVE','защищённая внутренняя миниволна черезMCX',['H-MCX-02'],
    [{'pair':p,'roundtrips_per_week':2,'weekdays_iso':[2,5],'action':'взаимосвязанные плечи/датированные inventory; гарантированнаяпересадка только при договоре',
      'unit':'roundtrip/week','period':'каждый сезон отдельно2027–28','coverage':'всяволна','source_id':'MCX-SCHEDULE;PIN-P03','assumption_id':'A-MCX-MCT;A-MCX-FREQ'} for p in ['PEE-MCX','CEK-MCX','MCX-AER']],
    ['PEE–MCX','CEK–MCX','MCX–AER','PEE–AER черезMCX','CEK–AER черезMCX'],
    ['те же6плечнаоперационныйдень безсинхронизации/безtransfer-product','прямыеPEE–AER/CEK–AER +MCX-terminal на томжепарке','KEEP'],
    {'active_tails':2,'initial_final_location':'T1 PEE;T2 CEK наоперационныйдень','reserve':'общий отдельно UNKNOWN',
     'overnight_support':'PEE/CEK rights/crew/MRO UNKNOWN, не доказывается названиемhubMCX','diagnostic':'rotation_diagnostics.csv;resource_summary.csv',
     'main_wave':'север приходит09:47/09:50Z; MCX→AER12:00Z; AER→MCX14:30Z приходит16:15Z; MCX→север18:00Z'},
    'Проверить добавочную ценность синхронизации при тех же физических рейсах. Полезность должна пережить прямые альтернативы и вытеснение terminal пассажиров.',
    'Занятые местнымиMCX иtransfer кресла общие. Сквозной тарифPEE/CEK–AER одинраз. Перенос днейMCX-продуктов меняет старые продажи; не обнулять.',
    ['сначалаterminal/capacity+MCT/багажныйдоговор','затемразрешённыедатывозврата3/4/7/10/14ночей','сезоннаяоценкаиmisconnectstress; приотсутствиизащиты убратьtransferproduct, сохранитьсамиплечаеслиполезны'],
    {'mct_test':'при90min номинальнаяволнапроходит; при60min задержки обратныйзапас45min не проходит90; это только вычисленное окно, не операционный MCT',
     'international_extension':'не присоединенаавтоматически. ТекущиеMCX international сохраняютсявKEEP; transfer border/visa/baggage/MCT/rights UNKNOWN.'})
programme('P-MCX-NNM','сохранение/изменение существующего through-продуктаNNM–MCX–AER',['H-MCX-03'],
    [{'path':'NNM>MCX>AER','observed':'вт, лето2026;4:25+1:45;10+10кг','test':'сравнить1вт с2вт/пт в активных месяцах, обратные рейсы отдельны',
      'unit':'one-way leg/min;roundtrip programme UNKNOWN','period':'2026история;2027–28 сценарий','coverage':'односторонне объявленная цепочка','source_id':'RW-NNM-AER','assumption_id':'A-MCX-FREQ;A-MCX-KEEP'}],
    ['NNM–MCX','MCX–AER','NNM–AER черезMCX'],
    ['сохранениеfutureKEEP того же продукта','NNM–AERdirect на общем ресурсе, dispatch/диапазон отдельно','безновогоборта: не обещатьвторуючастоту'],
    {'active_tails':'UNKNOWN; не1 автоматически','published_one_way_block_min':370,
     'hypothetical_symmetric_4leg_block_min':740,'restriction':'12h20blockдо3разворотов; >10h diagnostic cap; нужен overnight/split/2tail дизайнP03',
     'reserve':'UNKNOWN','aircraft':'NNM/South маршрутныйdispatch иBvsLR отдельны; SJ/ПД8 неследуетизSSJисточника'},
    'Это собственный продуктRW, который меняет counterfactual MCX. Разреженнаячастота позволяет недельные отпуска;2частоты могут дать3/4ночи, но рынок/цена иобратныйкалендарьнеизвестны.',
    'СохранятьдоходстарогоNNM–AERчерезMCX. Не продатьNNM–MCX исквознойпоездке одно место независимо.',
    ['сначалаподтвердитьобратнуюцепочкуидатированныйKEEP','проверитьполные24месяца/сезоныP03/P05','неприниматьсимметричныйоднодневныйsingle-tail шаблонкакготовоерасписание'])
programme('P-MCX-CONTRACT','общий договорный режим существующейMCX domestic+international программы',['H-MCX-04'],
    [{'pairs':['MCX-TAS','MCX-BHK','MCX-NMA','MCX-UGC','MCX-DYU','MCX-BSZ'],'action':'сохранитьилиявноизменитьтекущиезадания; новыхнаправленийрадипорога не назначено',
      'unit':'направление/полет по подтверждённому контрактному определению','period':'2027–28;по декадам еслиправилоподтверждено','coverage':'единыйbusinessRW','source_id':'MCX-DISCOUNT15;MCX-SCHEDULE','assumption_id':'A-MCX-DISC6'}],
    ['существующиеMCX international terminal journeys; transfer demand UNKNOWN'],
    ['тотжеflight programmeбезльготы','P/KEEP с одинаковымправомнаскидку','сохранитьшестоймаршрутvsегоальтернативноеприменениересурса'],
    {'incremental_tails':'0 дляпроверкидоговоратойжесети; не утверждение0затрат','international_resource':'общийP03KEEPвключаетфизическиезадания','new_tu214':0},
    'Можетизменитьnet local cost есливыполненыусловия; изменениеценынаeligible fuel требуетвсейпрограммы, ане отдельнойгородскойприбыли.',
    'Поддержкаиэкономия, ужепринадлежащиеKEEP, не добавочныйэффект. Текущиеintl рейсысохраняютсяссобственнымипассажирами.',
    ['подтвердитьподписанныйдоговор/редакцию/порог','P04построитодновременныеeventsP/KEEPиcash','оцениватьсохранениемаршрутаеслиегоnet contribution+действительнодобавочнаяэкономиялучшеальтернативы'],
    {'bounds':'A-MCX-RATES/A-MCX-DISCOUNT; местныеставки reference-only; новыхТу0 обязателен и достаточен для этой проверки'})
programme('P-MCX-GROUND','подвоз/partner к существующимрейсам безновогоавиабазирования',['H-MCX-05'],
    [{'pair':'KEEP aviation unchanged','ground_path':'MCX→Каспийск/Дербент','action':'условныйзащищённыйназемныйпродукт, несоздаётновыйавиаOD','unit':'journey with ground segment','period':'активныедаты2027–28','coverage':'last-milecontractUNKNOWN','source_id':'MCX-ABOUT;DERBENT-GROUND','assumption_id':'A-MCX-GROUND'}],
    ['тежеединыеавиапоездкиспродолжениемвДагестане'],['KEEPсамостоятельныйтрансфер','P-MCX-RADIALпри0новыхSJ'],
    {'incremental_aircraft':0,'ground_vehicle_crew_and_contract':'UNKNOWN, не0','reserve':'обязательстваKEEPсохраняются'},
    'Снижениесуммарноготренияпутешествиябезновыхсамолётов; полезностьиценадолжныбытьподтверждены, бесплатныйподвознепредполагается.',
    'Авиа+наземноепродолжениенеувеличиваетчислопоездокдважды; перетокмеждуMCX/GRV/OGZ/railсчитаетсявP05.',
    ['проверитьпоставщика/даты/задержки/SLA/платежи','сравнитьdoor-to-doorchoiceнатомжеpool','пилотпослеподтверждениядоговора; контрактысейчасне заключались'])
write('programme_candidates.json',{'stage':'A','common_contract':common,'candidates':programmes})

hypotheses=[]
def hyp(id,signal,src,mechanism,cf,test,anc,outcome,revision):
    hypotheses.append(dict(hypothesis_id=id,signal=signal,source_ids=src,mechanism=mechanism,counterfactual=cf,
        distinguishing_test=test,ancestorIDs=anc,outcome=outcome,condition_for_revision=revision,
        status='условна из-за конкретных неизвестных; не экономический отсев',period='2027–2028',unit='проверяемый программный вариант',coverage='Stage A локальная конструкция; Stage B в comparison_requests.csv'))
hyp('H-MCX-01','PEE–MCX наблюдавшийся поток36865в2025; incumbentвт/пт; MCXужеопорныйRW',
    ['E-MCX-PEE25','E-MCX-COMP','E-MCX-ROLE-CURRENT'],'РадиальнаябазаскороткимвозвратомvsтажеMCXпаравполномоборотеизSVX; расходыбазыпротивдобавочныхплеч',
    ['P-MCX-DIRECT','KEEPalternative'],'Одинаковыйtail-week, четыреdeliveryветви, общиеP05; terminalincrement, owncannibalization, fullcost/cash, полезныеночи.',
    ['C06','C19','T16_HUB_OTHERS','авторскийХабMCXdceadc98'],'StageA вариантысобраны; лучшийневыбран. CEK/UFAнеобъявленыновымипустымирынками.',
    'P05калибровка, подписаннаябаза/ТО/crew/слоты; принизкомспросе уменьшитьчастоты/сезон, сохранитьгородвдругойроли.')
hyp('H-MCX-02','MCXсевер–юг имеетисториюцепочки; возможностьдобавитьprotectedconnectionкterminalплечам',
    ['E-MCX-NNM','E-MCX-COMP'],'СинхронизацияPEE/CEK–MCX–AERоднимthroughfareприобщихкреслах',
    ['тежефизическиерейсыбезсинхронизации','прямыеконкурентыPEE/CEK–AER','KEEP'],
    'Впервомопыте заморозитьпарк/числорейсов; менятьтольковремена+защищённыйпродукт. MCT90,delay60, возвраты3/4/7/10/14; cabinshared.',
    ['C01','EC_H04','авторскийХабMCXdceadc98'],'Номинальныеноминальныеокнаусловногопримерапосчитаны; экипажи/прямыеконкуренты/МCTещёUNKNOWN. ВыводоприбыльномhubNOT_RUN.',
    'ПодтверждённыеMCT/baggage, расценкаmisconnect, P05OD/прямыеальтернативы. Неуспехэтойволнынеотвергаетradial.')
hyp('H-MCX-03','ОбъявленнаяRWNNM–MCX–AERлетом2026','RW-NNM-AER',
    'Частота1→2можетулучшитькороткиевозвраты; полнаяцепочкатребуетресурсаиKEEP',
    ['futureKEEPтойжепрограммы','directNNM–AER'],
    'Сначалаобратныйкалендарь/тип; сравнитьпарыднейиобаплеча; раздельноNNMterminal/through иMCXterminal.',
    ['EC_H02','существующийпродуктRWлето2026'],'Отклонёнтолькоавтоматическийчетырёхплечевойsame-dayone-tailшаблонприcap10h:740blockmin>600. Самрынок/цепочканеотклонены.',
    'Другойovernight/tailgroup/crewcalendarилифактическоеодностороннееназначение; обратныйрейсневыводитсяизпрессрелиза.')
hyp('H-MCX-04','Условнаяместнаяскидка топливадлябазыи>=6международныхнаправлений;6RWпубликуются',
    ['E-MCX-INTL','E-MCX-FUEL-THRESHOLD'],'СвязаннаястоимостьвсейMCXпрограммывместоизолированнойэкономикилуча',
    ['flightprogrammeбезльготы','льготавравноймеревP/KEEP','альтернативноеиспользованиересурса6-гомаршрута'],
    'Подтвердитьединицупорога/договор; P04eventsпонадлежащимeligibleuplift. Еслиобаevaluationимеютправо, deltaльготы=0длянеизменённоготоплива.',
    ['новаялокальнаянаходкаMCX-DISCOUNT15'],'Сильныйусловныйвходобщегосведения; нетподтверждённойскидкиRWилиденежнойпобеды.',
    'Утверждённаяредакцияиподписанноедопсоглашение; подтвердитьscopeиclawback.')
hyp('H-MCX-05','ТерминальныйтурпотокиудалённыеместаназначениявДагестане',
    ['E-MCX-SEGMENTS','E-MCX-GROUND'],'Partnerlast-mileможетизменитьdoor-to-doorchoiceбезновогобортапообщемуавиаpool',
    ['самостоятельныйтрансфервKEEP','авиарасширениепритехжеограниченияхресурса'],
    'Натехжедатахиспросесравнитьtotalfare/time/reliabilityсназваннымпартнёром; airportcatchmentsпересекаются.',
    ['новаярольизлокальноготуристическогосигнала'],'Условныйкандидат; текущийSLA/ставки/airportaccessнеполучены. ЭтообозначеннаяStageBзадача, неотсев.',
    'Поставщик/лицензия/страхование/SLA иP05готовностьплатить; еслинетценности–непокупатьподвоз.')
hyp('H-MCX-06','Старый8-лучевойMCXhubимелнеблагоприятныемодельныерезультаты',
    ['E-MCX-OLDMODEL'],'Сохранитьисторическийрезультатконкретнойверсии; пересмотретьролииминимальнуюсеткуизактуальныхданных',
    ['новаяradial','условнаяmini-wave','directсобщимресурсом'],
    'НеиспользоватьстарыеMOW/capture/annualizationкакпринятыйP05. ПересчитатьполныйбудущийKEEPиальтернативы.',
    ['авторскийХабMCXdceadc98'],'ОбъединенаH-MCX-01/H-MCX-02ссохранениемпроисхождения; старыеотрицательныеденьгинеотвергаютвесьгород.',
    'ОбщиеP05/P06иacceptedinputsмогутподтвердитьилиизменитьлокальныеварианты.')
write('hypotheses.json',{'hypotheses':hypotheses,'no_unevaluated_as_rejection':True})

deltas=[]
for p in programmes:
    for fl in p['flights']:
        pair=fl.get('pair') or fl.get('path') or ';'.join(fl.get('pairs',[]))
        deltas.append(dict(programme_id=p['programme_id'],market_or_path=pair,
            future_keep_frequency='UNKNOWN: bindingP03KEEPrequired',published_baseline='см.competition_summary.csv; старыйRWextractсисторией/субсидиямиотдельно',
            proposed_frequency=fl.get('roundtrips_per_week',fl.get('roundtrips_of_MCX_pair_per_week',fl.get('test','безавтоматическойдобавки'))),
            delta_frequency='UNKNOWN_until_KEEP; предложеннаяfrequencyнеравнаincrement',action=fl.get('action','переработкасобственногопродукта'),
            retained_rw_sales='всепроданныеплеча/through/charterсохранятьдоexplicitaction; количествоUNKNOWN',
            lost_or_migrated_sales='UNKNOWN; P05choiceнаобщемpool',period=fl['period'],unit=fl['unit'],coverage=fl['coverage'],
            source_id=fl['source_id'],assumption_id=fl['assumption_id'],status='предложеноStageA; дельтанепосчитана'))
table('market_deltas.csv',deltas)

requests=[]
def request(id,owner,programmes,fields,comparison,acceptance,priority='высокий'):
    requests.append(dict(request_id=id,owner=owner,programme_ids=programmes,required_fields=fields,comparison=comparison,
        acceptance_condition=acceptance,priority=priority,status='StageBне выполнено; не экономическийотказ',
        period='каждыймесяц2027–2028 +история2025/26',unit='см.required_fields',coverage='единыевходыдляобоихevaluation',source_id='case.json;programme_candidates.json'))
request('MCX-B01','P05','RADIAL;DIRECT;WAVE;NNM','PEE/CEK/UFA/NNM/AER/MCX monthlyjourneys; направление;период;цель;длительность;bookingdate;netfare;outside/ground;choicecoefficients',
    'terminalvsdirectvsprotectedwave','36865PEEairportmovementsнепревращатьвпотенциалRW/12; ниповторныхОДниобнулённыхunknown; sensitivityпоadmittedP05')
request('MCX-B02','P02','все','currentdatedRWKEEP; действующиеконкурентынаMCX–PEE/CEK/UFA/KUF/SVX/NJC/TJM/NUX/AER/NNM; оба направления; physicalthrough/inventory',
    'completefutureexternaloffersvsnewprogramme','DD.MMyearподтверждён;13дек/11янвнеценитькак365дней; physicalseatIDs/openinventoryневыводитьизrulecounts')
request('MCX-B03','P02;P05','WAVE','прямыеPEE–AER,CEK–AER пообеимсторонам/датам; продажичерезSVO/VKO/DME/KZN/MRV; throughstops, baggage/refunds/lead;connection protection',
    'wavevsdirect и soldconnections','Неполныйсписокненулеваяконкуренция;идентичныйbasket/period;SVOнеMOW')
request('MCX-B04','P03','все','exacttailcalendar 24months;B/LRvsPD8;freeafterKEEP;donor;MRO;reserve;crew-duty;slots/overnightsMCX+PEE+CEK;handling;MTOW/performance',
    'одинаковыйпарк/поставка/внешнийсценарий','1tailradial/directи2tailwaveтолькоусловны;allpositioningdated;нулевая/задержка/частичная/поэтапнаяветвь;нет0длянеизвестных')
request('MCX-B05','P03;P04','RADIAL;DIRECT','MCXbasefixed/launch/exit/deposits/crewrooms/parking/MROcontractcapabilityandcapacity;existingbaseincrementalcosts',
    'basevsfullchainSVX','полныйразностныйcostevent; TH-OPTION/TH-FIXED+TH-FUNDING;неподставитьlocalnormhourкакblockhour;не0дляновойбазы')
request('MCX-B06','P04','все','применимостьlocal_cost_references.csv;тариф2026/27;upliftvsburn;VAT;shared_event_id;invoice/paymentdates;supportawards',
    'полныйдобавочныйрезультатиликвидность','P04TH-FARE/TH-LAUNCH/TH-FUNDING;published2025referencesнебудущийдоговор;не применятьвместеустаревшиеиreplacementстроки')
request('MCX-B07','P04;P03','CONTRACT','signedapproveddiscountedition/RWaddendum;>=6definition;eligiblefuel;nonstacking;regionalextension;notice/exit/clawback',
    'contract/no-contract иsymmetricalP/KEEP','титулред15незаполнен;6направленийвтекстевs6полетоввтаблице;экономиянаunchangedKEEPнеincremental;branch0новыхТу214')
request('MCX-B08','P03;P06;P05','WAVE','RWdomesticMCX MCT;терминал/багаж;retimedcommittedsales;misconnectprobability+reaccommodation/cash;twowayreturncalendar',
    'тотжеinventory безsync,сsync,delay60','Nominal90проходит,105−60=45непроходит;нетзащищённогопродуктабездоговора;samefare1раз/2seats;доляпоездок≠segments')
request('MCX-B09','P02;P05','все','единаяresponsepolicy:repricingincumbent;releasedtail/crew/slotsдляextrafrequency',
    'base/cautious иresponseветви','новуючастотуконкурентане создаватьбезресурса;размерответаUNKNOWNдокалибровки')
request('MCX-B10','P03;P05','NNM','обратнаяцепочка2026/current;NNM/LRdispatch;seasondates;4legrotation/overnight;времяпребывания',
    '1втvs2вт/птvsNNM–AERdirect','370minonewayне740minготовыйsingle-tailday;условныйшаблон>10hисправитьполнойгруппой,невыброситьгород')
request('MCX-B11','координатор;P05;P04','GROUND','datedairportaccessMCX/Каспийск/Дербент;поставщик+SLA/страховка/лицензия;price/time/reliability;overlapGRV/OGZ/rail',
    'groundpartner наKEEPvsсамостоятельно','TLS/webtimeoutсохранены;неinfer119кмвминутыилиновыйспрос;новыхсамолётов0,groundcostUNKNOWN','средний')
request('MCX-B12','P06;независимаяприёмка','все','acceptedP02/P03/P04/P05versions;producermanifest;datedflights/products/fleet/commitments;costandcashcoverage',
    'совместноесведениеобщейцелевойсети8–12парконец2028','общийрезультатP−KEEP;нетсложенияавтономныхгородскихприбылей;автор42checksнеindependentacceptance;localStageAнефинальнаястратегия')
table('comparison_requests.csv',requests)

case={'case_id':'MCX-research-v1','city':'Махачкала','airport':'MCX / URML','language':'ru','as_of':ASOF,
    'stage':'A локальноеисследование/конструирование завершено','stage_b_status':'NOT_RUN;см.comparison_requests.csv',
    'decision':'ОставитьMCXвобщемсравнениикаксуществующийопорныйузел. Основнойлокальныйпарныйопыт —RADIALvsDIRECT; waveотдельныйусловныйтест. Финальныйэкономическийвыборнеполучен.',
    'role':{'historical':'базаRWс25.04.2022поаэропорту,подтвержденасловом«базовый»усамойRWвноябре2022',
        'current':'опорныйаэропортRWпозаявлению27.10.2026,актуальныесобственныепредложенияврасписании',
        'protected_hub':'UNKNOWN','station_support':'количества/договоры/физическиесвободныехвостыUNKNOWN',
        'not_zero_start':True},
    'flows':{'local':'входящий/исходящийterminalMCX;catchmentнеравеннаселениюпо75км',
        'regional':'PEEнаблюдавшийсяairportmarket2025;KUF/SVXсвоипубликуемые;UFA/CEKкандидаты,полнотапредложениянеустановлена',
        'longer_domestic':'NJC/TJM/NUXврасписанииRW;SGCсильныеконкуренты;NNMсобственнаялетняяцепочка2026',
        'international':'TAS/BHK/NMA/UGC/DYU/BSZуRWвснимке;DXB/DWC/Стамбул/СаудовскаяАравиясконкурентами. Исторический2024airportintl355441,неOD.',
        'segments':'туризмподтверждён;business/corporate/VFR/смены/паломничестводолиUNKNOWN. Семейнаямотивировкапоэтничности/рейсуневыводится.',
        'seasonality':'лето/shoulder/зимаотдельно;весна2026шокотментуров,немеханический−30%aviationdemand'},
    'competition':{'new_local_rules':len(rules),'published_current_rw_destinations':sorted({r['destination'] for r in rules if r['carrier']=='Ред Вингс'}),
        'p02_saved_outbound_coverage':'4partial/26uncoveredиз30;новыйsnapshotрасширяетsourcecoverage,неadmission',
        'fare':'однаindicativequote3544RUBMCX–PEE27.11.26;truebasketUNKNOWN;неиспользованавдоходах',
        'coverage_holes':['лето2026/2027','полныедатированныеобратныерейсы','CEK/UFAконкуренты','прямыеPEE/CEK–AER','soldtransfers/throughfare','багаж/сборывкотировках','airportaccess/railпоконкретнымдатам']},
    'operations':{'new_runway':'вводсообщён11.11.2026;3200mпофедеральномуМинтрансу;остальнаяреконструкцияпродолжается',
        'stands':'8 —планреконструкции,свободные/overnightRWUNKNOWN','slots':'UNKNOWN','mro':'publishednormhourreferenceесть,typedapproval/RWcontract/capacityUNKNOWN',
        'crew':'UNKNOWN','sj100_pd8':'неполучаетдопуск/расходыотSSJ100','local_contracts':'не заключались,копииRWнепредставлены'},
    'new_signal':'условныйместныйтопливныйпорог>=6intlможетсвязыватьстоимостьвсейпрограммы;effectivecontractUNKNOWN,экономиявKEEPсохраняетсясимметрично',
    'pins':pins,'numeric_boundaries':'всеизбранныеproxy/частоты/пороги —assumptions.csv;нетдоверительныхинтервалов/доходноймодели/безусловнойпобеды',
    'engine_admission':False,'financial_evaluation':'NOT_RUN','free_rw_aircraft':'UNKNOWN','new_tu214_required':False,
    'scope':'тольконазначенныйкаталог,безGitизменений/публикаций/броней/сообщенийвнешнимконтрагентам/оплаты/перезапусков'}
write('case.json',case)
write('readiness.json',{'stage_a':'COMPLETE_LOCAL_RESEARCH_AND_CANDIDATE_DESIGN','stage_b':'NOT_RUN_PENDING_COMMON_ACCEPTED_INPUTS',
    'hypotheses':len(hypotheses),'candidates':len(programmes),'dated_rules':len(dated),'new_schedule_rules':len(rules),
    'ready_for':['сравнение ролей','новыеsource-rowсhash','парныепрограммныекандидаты','двадиагностическихкалендарныхшаблона','историческиеместныеставкиP04','конкретныеStageBrequests'],
    'not_admitted':['2027–28demand/yield/capture','fullKEEP/свободныйпарк','crew/MRO/slotperformance','защищённыйtransferproduct','futurecost/fullcash','скидкаRW','готовыйP06bundle/финальныйэкономическийвыбор'],
    'remaining_work_owner':'P02/P03/P04/P05/P06+координатор;см.comparison_requests.csv','unknown_not_zero':True,
    'independent_acceptance':'NOT_RUN','engine_checks':'P06author42PASS suppliedhistory,незапускалисьздесь'})
write('handoff.json',{'package_id':'MCX-research-v1','write_root':str(D),'status':'STAGE_A_COMPLETE_STAGE_B_PENDING',
    'primary_entrypoints':['case.json','programme_candidates.json','hypotheses.json','comparison_requests.csv','README.txt'],
    'usable_tranches_sent_to':'91bc9ad6-4e9f-4954-8714-1e4366064b78','sourcepins':'input_manifest.json;fetch_receipts.json;sources.csv',
    'what_to_integrate':['RADIALvsDIRECTодинаковый1tail-week,общийKEEP','WAVEсинхронизацияvsтежефизическиерейсыбезнеё','собственныйNNMthroughвKEEP',
        'MCXdiscountдоговорныйпорогиветкабезльготы','P04местныесправочныеставки','GROUNDветвь0новыхсамолётов'],
    'do_not_integrate_as_accepted':['старуюсложеннуюMCXприбыль','257schedule rulesкак257рейсовилисвободныекресла','100seatsкакSJcabinfact','10hcapкакcrewлегальность','скидкуизunsignedред15какфакт','airportaggregatesкакновыйспросRW'],
    'stage_b_request_ids':[r['request_id'] for r in requests],'git_operations':'NONE;координаторкоммититпакетпослеreviewmanifest',
    'publication':'NONE','new_payments':'NONE','artifacts_review':'см.validation.json;никакихфинансовыхPASSздесь'})

# Local structural and arithmetic checks, not acceptance tests for the common engine.
checks=[]
def check(name,result,detail):checks.append({'check':name,'pass':bool(result),'scope':detail})
check('required_outputs',all((D/n).exists() for n in ['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json']),'форматпакета')
check('unique_rule_ids',len({r['row_id'] for r in rules})==len(rules),'snapshotrules,неphysicalseatIDs')
check('hypotheses_have_outcomes',all(h['outcome'] and h['condition_for_revision'] for h in hypotheses),'ниоднаUNKNOWNневыданазаотсев')
check('assumptions_registered',len({a['assumption_id'] for a in assumptions})==len(assumptions),'всеизбранныесценарныепараметрыимеютID')
for key,rs in __import__('itertools').groupby(sorted(rot,key=lambda r:(r['programme_id'],r['week_start'],r['tail_group'],r['day_iso'],r['departure_utc'])),lambda r:(r['programme_id'],r['week_start'],r['tail_group'],r['day_iso'])):
    rs=list(rs);valid=True
    for a,b in zip(rs,rs[1:]):
        valid &= a['destination']==b['origin'] and datetime.datetime.fromisoformat(b['departure_utc'])>=datetime.datetime.fromisoformat(a['arrival_utc'])+datetime.timedelta(minutes=45)
    valid &= rs[-1]['destination']==rs[0]['origin']
    check('position_turn_closed:'+str(key),valid,'условныйшаблонпроверенполнойцепочкой;crew/KEEPнепроверены')
check('nnm_one_tail_counterexample',2*(265+105)==740 and 740>600,'недопускодногошаблона,нерыночныйотказ')
check('fare_lead', (datetime.date(2026,11,27)-datetime.date(2026,11,12)).days==15,'retrievallead;truequotelead15–17')
check('later_handling_rates',9782.27>6521.51 and 9429.52>6286.35 and 18102.69>9051.35,'заменапозднимистроками,несложение')
check('fuel_vat_arithmetic',round(91000*1.22,2)==111020,'точнокаквисточнике,неутверждениебудущейставкиналога')
write('validation.json',{'status':'PASS_LOCAL_STRUCTURE_AND_CONDITIONAL_ARITHMETIC' if all(c['pass'] for c in checks) else 'CHANGES','checks':checks,
    'not_checked':['marketcalibration','realresourceavailability','crewlegality','dispatch','futurecontracts','P06engineacceptance','financialsuccess']})

# Seal every deliverable/source; manifest is excluded from its own hash recursion.
manifest={'package_id':'MCX-research-v1','scope':str(D),'as_of':ASOF,'git_mutation':False,
    'hash_algorithm':'sha256','exclusion':'output_manifest.jsonсамсебянехеширует;bytecodeкешнеявляетсяартефактом',
    'files':[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(D.rglob('*')) if p.is_file() and p.name!='output_manifest.json' and '__pycache__' not in p.parts]}
write('output_manifest.json',manifest)
print(json.dumps({'validation':load('validation.json')['status'],'hypotheses':len(hypotheses),'programmes':len(programmes),'source_rules':len(rules),'diagnostic_legs':len(rot),'files':len(manifest['files'])},ensure_ascii=False))
