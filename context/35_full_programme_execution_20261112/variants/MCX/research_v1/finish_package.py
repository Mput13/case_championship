"""Readable handoff text and final integrity checks. Run after build_package.py."""
import pathlib,json,csv,hashlib,datetime
D=pathlib.Path(__file__).resolve().parent
def read(n):return json.loads((D/n).read_text())
def write(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def rows(n):return list(csv.DictReader((D/n).open()))
def table(n,rs):
    keys=list(dict.fromkeys(k for r in rs for k in r))
    with (D/n).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rs)

c=read('case.json')
c['stage']='Stage A: локальное исследование и конструирование завершены'
c['stage_b_status']='NOT_RUN: нужны общие принятые входы и совместные расчёты'
c['decision']='Сохранить MCX в общем сравнении как существующий опорный узел. Первый опыт — радиальная программа против тех же прямых пар в полных оборотах из SVX. Защищённая волна — отдельный условный опыт. Экономический победитель не определён.'
c['role']={'historical':'Базирование RW с 25.04.2022 по официальному аэропорту. В ноябре 2022 сама RW называла аэропорт базовым.',
    'current':'Опорный аэропорт по заявлению RW от 27.10.2026; собственные предложения присутствуют в местном расписании.',
    'protected_hub':'UNKNOWN','free_tails':'UNKNOWN','crew_mro_contracts':'UNKNOWN','not_zero_start':True}
c['flows']={'local':'Конечные поездки в Дагестан и из него; catchment не равен населению внутри произвольного радиуса.',
    'regional':'PEE–MCX имеет маршрутное наблюдение за 2025 год. KUF/SVX — опубликованные собственные рынки. CEK/UFA — сравниваемые кандидаты; текущая полнота предложения UNKNOWN.',
    'longer_domestic':'NJC/TJM/NUX — предложения RW; SGC — предложения конкурентов; NNM — собственная летняя цепочка 2026 года.',
    'international':'RW: TAS/BHK/NMA/UGC/DYU/BSZ в снимке. Международные 355441 движения MCX за 2024 год не распределены по OD или RW.',
    'segments':'Туризм подтверждён. Доли business/corporate/VFR/смен/паломничества UNKNOWN. Не выводятся из этнического состава или наличия рейса.',
    'seasonality':'Лето, межсезонье и зима отдельно. Отмены туров весной 2026 года не равны падению всего авиационного спроса на 30%.'}
c['competition']['fare']='Индикативное предложение Туту MCX–PEE 3544 RUB на 27.11.2026; snapshot 12.11.2026. Итоговая корзина, багаж и инвентарь UNKNOWN. В доходах не использовано.'
c['competition']['p02_saved_outbound_coverage']='4 partial и 26 uncovered из 30 исходящих рынков. Новый локальный снимок расширяет источники, без автоматического admission.'
c['competition']['coverage_holes']=['Лето 2026/2027','Полные обратные датированные рейсы','Конкуренты CEK/UFA','Прямые PEE/CEK–AER','Продаваемые пересадки и сквозные тарифы','Сопоставимые цена/багаж/сборы/lead','Наземные альтернативы на дату']
c['operations']={'new_runway':'Ввод сообщён 11.11.2026; длина3200м по федеральному Минтрансу. Прочая реконструкция продолжается.',
    'stands':'Восемь стоянок — проект реконструкции; свободные и ночные стоянки RW UNKNOWN.',
    'slots':'UNKNOWN','mro':'Опубликован reference norm-hour; допуск по типу, договор RW и свободная мощность UNKNOWN.',
    'crew':'UNKNOWN','sj100_pd8':'Проверяется отдельно от SSJ100/SaM146: допуски, расходы, performance, экипажи и ТО.',
    'local_contracts':'Договоры не заключались; подписанные документы RW не представлены.'}
c['new_signal']='Местный условный топливный порог >=6 международных направлений может связывать стоимость всей программы. Действующий договор и единица порога UNKNOWN. Экономия KEEP сохраняется в обоих evaluation.'
c['numeric_boundaries']='Все выбранные частоты, прокси и пороги имеют assumption_id. Это сценарии; нет доверительных интервалов, собственной денежной модели или безусловной победы.'
c['scope']='Только назначенный каталог. Нет Git-мутаций, публикации, броней, платежей, внешних сообщений контрагентам или перезапусков.'
write('case.json',c)

h=read('hypotheses.json')
descriptions=[
('PEE–MCX: 36865 пассажирских движений в 2025 году, incumbent вт/пт; MCX уже опорный аэропорт RW.',
 'Сравнить расходы радиальной базы MCX с дополнительными плечами полных оборотов из SVX на тех же MCX-парах.',
 'Одинаковый tail-week и четыре ветви поставок. Общий P05: terminal increment, собственный переток, полезные дни возврата. P04/P06: полный результат и cash.',
 'Stage A: две программы построены. Лучший вариант не выбран. CEK/UFA не объявлены пустыми новыми рынками.',
 'P05-калибровка и подписанные условия базы/crew/ТО/слотов. При слабом спросе проверить частоты и сезон; не исключать город целиком.'),
('У MCX есть северо-южный собственный продукт. Синхронизация может добавить ценность терминальным плечам.',
 'Защищённые PEE/CEK–MCX–AER с одним сквозным тарифом и общими креслами всех плеч.',
 'Заморозить парк, пары и число рейсов. Сравнить WAVE с WAVE-UNSYNC и прямыми альтернативами; учесть retiming старых продаж. Проверить MCT, задержку60мин и возвраты3/4/7/10/14ночей.',
 'Номинальные окна условного шаблона посчитаны; полный парк, экипажи, MCT и рынок UNKNOWN. Прибыльность хаба NOT_RUN.',
 'Принятые MCT/багажный договор, misconnect/reaccommodation, P05 и прямые альтернативы. Провал этой волны не отвергает радиальную роль.'),
('RW объявила NNM–MCX–AER на лето 2026 года.',
 'Две частоты вместо одной могут улучшить короткие возвраты; оценивается вся цепочка и собственный KEEP.',
 'Подтвердить обратные рейсы и тип. Сравнить одну/две частоты, прямой контроль NNM–AER, местные и сквозные поездки с общими креслами.',
 'Не допускается только автоматический симметричный same-day шаблон на одном борту при cap10ч:740мин>600. Рынок и цепочка не отклонены.',
 'Другая группа бортов, overnight, crew calendar или фактическое одностороннее назначение. Обратный рейс не следует из пресс-релиза.'),
('Опубликована условная местная скидка для базы с >=6 международных направлений; шесть RW station-pairs видны в снимке.',
 'Оценить связанную стоимость всей MCX-программы; не изолированную прибыль отдельного луча.',
 'Уточнить единицу порога и подписанный договор. P04: eligible uplift и даты. В P/KEEP одинаковое право; экономия неизменённого KEEP не добавочная.',
 'Сильный условный вход общего сведения. Подтверждённой скидки RW и денежной победы нет.',
 'Утверждённая редакция, подписанное допсоглашение, scope, сроки, termination/clawback и реальная выполненная программа.'),
('Туристический terminal-поток и наземное продолжение к местам отдыха в Дагестане.',
 'Партнёрский подвоз может изменить door-to-door choice без новых самолётов на том же авиационном pool.',
 'Одинаковые даты/спрос: самостоятельный трансфер против названного партнёра, полная цена, время и надёжность; учесть пересечение catchment.',
 'Условный кандидат. Договор, SLA, ставки и airport access UNKNOWN. Недостающая работа передана в Stage B; это не отсев.',
 'Проверяемый поставщик и договор, P05 willingness to pay. При отсутствии добавочной ценности подвоз не покупать.'),
('Старый восьмилучевой шаблон MCX имел неблагоприятные авторские модельные результаты.',
 'Сохранить исторический результат версии и проверить иные роли/расписания с общими современными входами.',
 'Старые MOW/capture/annualization не допускать как P05. Пересчитать будущий KEEP, собственные продажи, рынок и общие ресурсы.',
 'Объединена с H-MCX-01 и H-MCX-02 с сохранением происхождения. Старые отрицательные деньги не отвергают город.',
 'Принятые P05/P06 и общие входы могут подтвердить или изменить выводы новых локальных вариантов.')]
for x,d in zip(h['hypotheses'],descriptions):
    x.update(signal=d[0],mechanism=d[1],distinguishing_test=d[2],outcome=d[3],condition_for_revision=d[4],
        status='Условна из-за перечисленных неизвестных; не экономический отсев',period='2027–2028',
        unit='программная гипотеза',coverage='Локальный Stage A; Stage B в comparison_requests.csv')
    if isinstance(x['source_ids'],str):x['source_ids']=[x['source_ids']]
    if x['hypothesis_id']=='H-MCX-06':x['status']='Объединена с сохранением происхождения'
evidence_map={r['evidence_id']:r['source_id'].split(';') for r in rows('evidence.csv')}
for x in h['hypotheses']:
    evidence_ids=[v for v in x['source_ids'] if v.startswith('E-MCX-')]
    if evidence_ids:
        x['evidence_ids']=evidence_ids
        x['source_ids']=sorted({s for e in evidence_ids for s in evidence_map[e]} | {s for s in x['source_ids'] if not s.startswith('E-MCX-')})
write('hypotheses.json',h)

p=read('programme_candidates.json')
common=p['common_contract']
common.update(target_role='Локальный фрагмент общей сети8–12 уникальных airport pairs на конец2028; не самостоятельное доказательство места№2.',
    status='Stage A сконструирован; экономика и полный ресурс Stage B NOT_RUN',
    aircraft_branches=['SSJ100/SaM146: подтверждённое окно или названный донор.',
        'SJ100/ПД-8: отдельные расходы/performance/crew/ТО; service entry из P03, не ранее H2 2027.',
        'Новых SJ0: KEEP или доказанное retiming/перенос с учётом донора.', 'Новых Ту-2140: основные опыты сохраняются.'],
    fleet_calendar='Одинаковый P03 delivery/availability/reserve/KEEP в каждой паре. Нельзя использовать долю физического самолёта.',
    delivery_branches=['Поэтапно из P03','Частично из P03','Задержка из P03','0 новых бортов в2027–2028'],
    preserved_business='Сохраняются проданные затронутые северные, международные, чартерные и базовые продукты RW до явного действия.',
    economic_method='Только общий P05 choice/demand +P06 +P04. Локальной захватной или денежной модели нет.',
    season_definition='A-MCX-SEASON: месячные объёмы UNKNOWN. Сезоны ставок/поддержки определяются отдельно.',
    needed_common_inputs=['P02: датированные продукты, цены, багаж и физический инвентарь.',
        'P03: KEEP, хвосты, crew/ТО/слоты/ввод.', 'P04: принятые ставки, events, cash и местные договоры.',
        'P05: непересекающиеся месячные поездки и калиброванный choice.', 'P06: общий пересчёт и независимая приёмка.'])
mechanisms={
 'P-MCX-RADIAL':'Те же три MCX-пары с базированием одного активного борта в MCX. PEE имеет маршрутное наблюдение, другие лучи требуют проверки. Дни выбираются для коротких/недельных возвратов; спрос не придуман.',
 'P-MCX-DIRECT':'Те же прямые MCX-продукты полными четырёхплечевыми оборотами из SVX. Нет новой ночной базы MCX; оплачиваются дополнительные плечи. Их собственный спрос и наземная конкуренция оцениваются общим P05.',
 'P-MCX-WAVE':'Сравнить добавочную ценность синхронизации при тех же физическом ресурсе, парах и числе рейсов. Проверить прямых конкурентов, terminal displacement и стоимость ожидания/защиты.',
 'P-MCX-NNM':'Собственная история NNM–MCX–AER входит в KEEP. Сравнение одной/двух частот требует обеих сторон расписания, полной группы бортов и прямой альтернативы.',
 'P-MCX-CONTRACT':'Проверить местную цену eligible fuel и услуг всей действующей программы с подписанным договором и без него. Экономия, принадлежащая KEEP, не добавочный результат.',
 'P-MCX-GROUND':'Сравнить стоимость и полезность наземного продолжения той же авиационной поездки без новых самолётов. Нужен названный платный партнёр и SLA.'}
for x in p['candidates']:
    for k,v in common.items():x[k]=v
    pid=x['programme_id'];x['selection_mechanism']=mechanisms[pid]
    x['own_sales_changes']='Никаких автоматических отмен старых продаж. Для add/retime/reduce нужны datеd KEEP и явные действия P06. Переток собственного терминального/сквозного спроса входит в общий P−KEEP один раз.'
    x['stage_sequence']=['2027: связать KEEP и договоры; новый SJ вводится только по принятому P03.',
        '2028: оценить месячные сезонные программы, спрос, ресурс, результат и финансирование.',
        'Порог остановки/даты решения берутся из принятого бюджета и information set. Уже проданные поездки не удаляются.']
    x['readiness']='Программный кандидат Stage A; готовый bundle P06 не заявлен.'
    if pid=='P-MCX-WAVE':
        x['counterfactual']=['P-MCX-WAVE-UNSYNC: те же пары, два борта и6плеч на операционный день, короткие последовательные развороты.',
            'Прямые PEE–AER/CEK–AER вместе с terminal MCX на общем ресурсе.', 'Будущий KEEP.']
        x['mct_test']='Проектный MCT90мин: номинальные окна проходят. Обратное окно105мин после задержки60мин становится45мин и не проходит90мин. Утверждённый RW MCT UNKNOWN.'
        x['international_extension']='Не добавлена автоматически. Текущие международные рейсы сохраняются в KEEP. Border/visa/baggage/MCT/rights UNKNOWN.'
    if pid=='P-MCX-NNM':x['resource']['restriction']='Гипотетический симметричный возврат:740мин блок-времени,12ч20мин до разворотов; не проходит условный cap10ч. Это не фактический обещанный источником оборот.'
    if pid=='P-MCX-DIRECT':x['safety_of_comparison']='Одинаковый доступный tail-week. Остаток времени имеет сопоставимое альтернативное задание или видимый оплачиваемый простой. Продажи дополнительных плеч не гарантированы.'
    if pid=='P-MCX-CONTRACT':x['bounds']='Нет принятого действующего договора. A-MCX-DISCOUNT/A-MCX-DISC6; основной контроль без льготы. Новых Ту-2140.'
write('programme_candidates.json',p)

rs=rows('market_deltas.csv')
for r in rs:
    r.update(future_keep_frequency='UNKNOWN: нужен датированный будущий KEEP P03',
        published_baseline='competition_summary.csv и точные авторские строки; история/субсидии не равны текущей частоте',
        delta_frequency='UNKNOWN до binding KEEP; предложенная частота не равна приросту',
        retained_rw_sales='Все проданные терминальные/сквозные/чартерные поездки сохраняются до явного действия; количество UNKNOWN',
        lost_or_migrated_sales='UNKNOWN; общий P05 на непересекающихся pool',status='Предложено Stage A; денежная и рыночная дельта не рассчитана')
table('market_deltas.csv',rs)

rq=rows('comparison_requests.csv')
fields=[
 'Месячные поездки PEE/CEK/UFA/NNM/AER/MCX: направление, цель, длительность, booking date, net fare, outside/ground и choice coefficients.',
 'Датированный текущий RW KEEP и конкуренты MCX: оба направления, through continuity, физический inventory и подтверждённый год.',
 'Прямые PEE–AER/CEK–AER, продаваемые пересадки через конкретные аэропорты, through stops, багаж/возвратность/lead/итоговая цена.',
 'Общий календарь хвостов24месяца: B/LR или ПД-8, KEEP, донор, crew/ТО, резерв, слоты и ночные стоянки MCX/PEE/CEK, performance.',
 'MCX: fixed base, launch/exit, депозиты, crew rooms, стоянки и договор ТО/мощности. Сопоставимые добавочные затраты существующей SVX базы.',
 'Применимость local_cost_references.csv в2027–2028, обновлённые rates, uplift/burn, VAT, shared event IDs, начисления и платежи, подтверждённая поддержка.',
 'Утверждённая редакция скидок и подписанное допсоглашение RW; единица порога6, eligible fuel, nonstacking, сроки, notice/exit/clawback.',
 'RW MCT в MCX, терминальный путь/багаж, retiming проданных мест, misconnect/reaccommodation, обратный календарь и duty экипажа.',
 'Общая политика реакции конкурентов: repricing и отдельное обоснование освобождённого борта/crew/слота для добавочной частоты.',
 'Обратная цепочка NNM, точный B/LR и dispatch, сезонные даты, полный4-плечевой оборот/overnight и длительность пребывания.',
 'Датированный наземный доступ MCX–Каспийск/Дербент, поставщик/SLA/страхование/лицензия, цена/время/надёжность, overlap GRV/OGZ/rail.',
 'Принятые версии P02/P03/P04/P05, producer manifest, flights/products/fleet/commitments, cost/cash coverage и независимая приёмка P06.']
acceptance=[
 '36865 airport movements не превращать в доступный RW спрос или равные месяцы. Нет повторных OD и нулей вместо неизвестного.',
 'Правила DD.MM не physical seats. Не считать неделю годом и не переносить старые продажи на другой рейс без явного действия.',
 'Неполный список не нулевая конкуренция. Одинаковые корзины и даты; SVO/VKO/DME не заменяются MOW.',
 'Одинаковые поэтапная/частичная/задержка/нулевая ветви. Позиционирование и резерв явные;1/2tail в пакете лишь условные задания.',
 'Полные разностные события и TH-OPTION/TH-FIXED/TH-FUNDING. Нормо-час не block-hour; неизвестные затраты не0.',
 'TH-FARE/TH-LAUNCH/TH-FUNDING при общей калибровке. Поздние замещающие тарифы не складывать со старыми; cash не равен начислению.',
 'Титул ред15 не заполнен; направления/полёты неоднозначны. Экономия одинакового KEEP не прирост. Обязательна ветвь без льготы и0новыхТу.',
 'Номинальные90мин проходят;105−60=45мин не проходит. Без договора защищённый продукт не admitted; один тариф, кресло на каждом плече.',
 'Размер реакции UNKNOWN до общей калибровки. Дополнительная частота не появляется без реального/явно сценарного ресурса.',
 '370мин одной цепочки не означает готовый симметричный740мин single-tail day. Полный ресурс/обратные продажи обязательны.',
 'Ошибки TLS и web TimeoutError сохранены. Поисковый фрагмент не точный access time/catchment. Авиаинкремент0 не делает наземный продукт бесплатным.',
 'Общий P−KEEP и8–12уникальных пар на конец2028; локальные прибыли не суммируются. Авторские42checks не независимая приёмка.']
for r,f,a in zip(rq,fields,acceptance):
    r.update(required_fields=f,acceptance_condition=a,status='Stage B не выполнено; не экономический отказ',
        period='Каждый месяц2027–2028; история2025/2026 отдельно',unit='См. required_fields',coverage='Единые принятые входы обоих evaluation')
table('comparison_requests.csv',rq)

# Source aliases used by consumers; exact pins remain the authority.
source_rows=rows('sources.csv')
for row in list(source_rows):
    if row['source_id'].startswith('PIN-P0'):
        alias=dict(row);alias['source_id']=row['source_id'][4:];source_rows.append(alias)
source_rows=list({r['source_id']:r for r in source_rows}.values())
table('sources.csv',source_rows)

# A separate MCT counterexample table, with no passenger or financial claim.
table('connection_diagnostics.csv',[
 {'programme_id':pid,'direction':direction,'connection_minutes':minutes,'required_mct_minutes':90,
  'passes_nominal_scenario':minutes>=90,'source_id':'rotation_diagnostics.csv','assumption_id':'A-MCX-MCT;A-MCX-BLOCK',
  'unit':'min','period':'diagnostic operating day, Tue/Fri in two saved weeks','coverage':'Only timetable window; actual MCT/contract UNKNOWN','status':'Условная арифметика'}
 for pid,direction,minutes in [('P-MCX-WAVE','PEE→MCX→AER',130),('P-MCX-WAVE','CEK→MCX→AER',133),
     ('P-MCX-WAVE','AER→MCX→PEE/CEK',105),('P-MCX-WAVE','AER delayed60min',45),
     ('P-MCX-WAVE-UNSYNC','PEE→MCX→AER',45),('P-MCX-WAVE-UNSYNC','AER→MCX→PEE',45)]])

v=read('validation.json')
v['checks']=[r for r in v['checks'] if r['check']!='local_inputs_pinned' and not r['check'].startswith('same_wave_flights:')]
v['checks'].append({'check':'local_inputs_pinned','pass':all(x.get('git_commit') and x.get('source_sha256') and x.get('blob_id') for x in read('input_manifest.json')),
    'scope':'Все извлечённые общие входы имеют exact commit/blob/hash; исходники коллег не изменены.'})
flights=rows('rotation_diagnostics.csv')
for week in ['2028-07-03','2028-12-11']:
    def signature(pid):
        return sorted((r['tail_group'],r['day_iso'],r['origin'],r['destination'],r['block_minutes']) for r in flights if r['programme_id']==pid and r['week_start']==week)
    v['checks'].append({'check':'same_wave_flights:'+week,'pass':signature('P-MCX-WAVE')==signature('P-MCX-WAVE-UNSYNC'),
        'scope':'Волна и контроль имеют одинаковые борта, дни, пары, число плеч и block-minutes; времена различаются.'})
v['status']='PASS_LOCAL_STRUCTURE_AND_CONDITIONAL_ARITHMETIC' if all(x['pass'] for x in v['checks']) else 'CHANGES'
v['not_checked']=['Калибровка рынка','Реальная доступность ресурса','Легальность crew duty','Dispatch','Будущие договоры','Независимая приёмка P06','Финансовый успех']
write('validation.json',v)
r=read('readiness.json');r['diagnostic_physical_legs']=len(flights);r['unsynchronised_control']='P-MCX-WAVE-UNSYNC: те же рейсы и борта; независимая приёмка NOT_RUN'
r['ready_for']=['Сравнение ролей MCX','Новые source rows с hashes','Парные программные кандидаты','Два условных календарных шаблона и контроль без синхронизации','Исторические местные ставки для P04','Конкретные запросы Stage B']
r['not_admitted']=['Спрос/yield/capture2027–2028','Полный KEEP и свободный парк','Crew/ТО/слоты/performance','Защищённые пересадки','Будущие расходы и полный cash','Скидка RW','Готовый P06 bundle и финальный экономический выбор']
r['remaining_work_owner']='P02/P03/P04/P05/P06 и координатор; comparison_requests.csv'
write('readiness.json',r)
hf=read('handoff.json');hf['what_to_integrate']=['RADIAL против DIRECT: одинаковый1tail-week и общий KEEP.',
 'WAVE против WAVE-UNSYNC: те же рейсы, два борта, иная синхронизация; прямые альтернативы обязательны.',
 'Собственный NNM through-продукт сохраняется в KEEP.', 'Условный MCX договорный порог и контроль без льготы.',
 'Исторические местные ставки для дальнейшей проверки P04.', 'GROUND:0 новых самолётов, оплачиваемый наземный договор UNKNOWN.'];write('handoff.json',hf)

manifest={'package_id':'MCX-research-v1','write_root':str(D),'as_of':'2026-11-12','status':'Stage A COMPLETE; Stage B NOT_RUN',
 'hash_algorithm':'sha256','self_excluded':True,'git_mutation':False,'input_pins':c['pins'],
 'input_row_hash_method':'SHA256 нормализованного JSON исходной строки с sort_keys=True; source_line — номер записи CSV с заголовком. Product IDs и airport row IDs сохранены.',
 'files':[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
   for p in sorted(D.rglob('*')) if p.is_file() and p.name!='output_manifest.json' and '__pycache__' not in p.parts]}
write('output_manifest.json',manifest)
print(json.dumps({'status':v['status'],'files':len(manifest['files']),'bytes':sum(x['bytes'] for x in manifest['files']),'checks':len(v['checks']),'failed':[x['check'] for x in v['checks'] if not x['pass']]},ensure_ascii=False))
