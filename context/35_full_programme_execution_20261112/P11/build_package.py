#!/usr/bin/env python3
"""Build the P11 research handoff from saved evidence, without network or Git mutations."""
import csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist

ROOT=Path(__file__).resolve().parent
ASOF='2026-11-12'

def hashb(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def write(name,obj):
    (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def table(name,rows):
    if not rows: return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader()
        for r in rows:
            w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else ('UNKNOWN' if v is None else v) for k,v in r.items()})

def main():
    registry=json.loads((ROOT/'sources/registry.json').read_text())
    pins=json.loads((ROOT/'input_manifest.json').read_text())['pins']
    source_by={r['source_id']:r for r in registry}
    claims=[]; selected=[]
    def claim(cid,sid,start,end,fact,limit):
        source=source_by[sid]
        lines=(ROOT/source['text_path']).read_text().splitlines()
        ids=[]
        for n in range(start,end+1):
            raw=lines[n-1].split('\t',1)[1]
            rid=f'{sid}:L{n:04d}'
            ids.append(rid)
            selected.append(dict(source_row_id=rid,source_id=sid,row_number=n,row_sha256=hashb(raw.encode()),text=raw,
                                 source_sha256=source['sha256'],text_file_sha256=source['text_sha256'],
                                 url=source['url'],retrieved_at_utc=source['retrieved_at_utc'],
                                 organization=source['organization'],publication_date=source['publication_date'],
                                 period=source['period'],unit=source['unit'],granularity='строка сохранённого публичного текста',
                                 status='published_condition',coverage=source['coverage']))
        claims.append(dict(claim_id=cid,source_id=sid,source_row_ids=ids,fact=fact,limit=limit,
                           source_sha256=source['sha256'],status='PUBLISHED_NOT_FULFILMENT_ACCEPTANCE'))
    claim('C01','RW_HOW',64,79,'Опубликован путь покупки с допуслугами и оплатой; сайт предупреждает о бронировании до оплаты.',
          'Публичная инструкция не устанавливает точный технический endpoint появления PNR. В P11 fare-select-button не нажат.')
    claim('C02','RW_BAGGAGE',64,91,'Для регулярных рейсов таблица разделяет оформление более/менее 24 часов до вылета.',
          'Ровно 24 часа не определено; от-цены не гарантируют live quote и не распространяются автоматически на чартер.')
    claim('C03','RW_BAGGAGE',74,123,'Внутри РФ до 10 кг: от 1700/2500; 10–23 кг: от 2700/3500; на пересадках оплата за каждый участок.',
          'Сопоставление двух таблиц, не подтверждённый средний тариф/маржа; более24ч цены также в C02.')
    claim('C04','RW_BAGFAQ',63,67,'Покупка багажа уже есть при покупке и после неё; FAQ советует три и более часов для выгодной цены.',
          'Это расхождение с 24-часовым ценовым переходом, а не доказательство запрета продажи за три часа.')
    claim('C05','RW_REFUND',100,110,'Самостоятельные добровольный возврат и обмен сайт указывает для приобретённых на сайте билетов; Лайт назван невозвратным.',
          'PNR и правила конкретного билета не проверены; отсутствие ссылки на возвратность не означает отказ в услуге.')
    claim('C06','RW_RETURNABILITY',64,75,'Возвратность уже продаётся: прямые международные рейсы, добавление во время покупки, особые сроки и исключения.',
          'Возвращается тариф с вычетом использованной части по условиям; стоимость услуги, таксы и сборы исключены. Чартерная применимость UNKNOWN.')
    claim('C07','RW_FAQ',64,81,'FAQ различает чек и маршрутную квитанцию, даёт существующий сервис управления и канал поддержки.',
          'Повторная выдача реальной квитанции/чека и доступность конкретного заказа NOT_RUN.')
    claim('C08','RW_CHECKIN',63,71,'Общая инструкция: онлайн-регистрация открывается за24ч, заканчивается за3ч, собственные рейсы RW.',
          'Не является проверкой cutoff на реальном рейсе; ограничения маршрутов далее на странице.')
    claim('C09','RW_PREP',67,68,'FAQ: онлайн-регистрация заканчивается за3ч, с оговоркой за6ч в Москве.',
          'Не определён аэропорт MOW; фактические правила DME/ZIA и конкретного рейса UNKNOWN.')
    claim('C10','RW_SERVICES',62,90,'Существует каталог допуслуг; не требуется заново создавать продажу места, багажа или возвратности.',
          'Каталог не доказывает доступность каждой услуги в любом аэропорту/тарифе/типе самолёта.')
    claim('C11','RW_REFUND',66,90,'Публичная инструкция различает вынужденный возврат, уведомление и документальное подтверждение; есть отдельный канал.',
          'Ничего не отправлялось; сроки исполнения, статус дела и законность конкретного отказа не оценены.')
    browser_claims=[
        ('CB01','V02_search','WZ5071 SVX→OMS20.11.2026:21:20→00:00nextday,SSJ100,1adult,5830RUB;поиск работает','RUB/1взрослый/1направление','2026-11-20; as_of2026-11-12;lead8calendar_days'),
        ('CB02','V03_fares','Раскрытие предложения:Стандарт5930RUB,Лайт5830RUB;fare-select-button не нажат','RUB/1взрослый/1направление','2026-11-20;as_of2026-11-12;lead8calendar_days'),
        ('CB03','V09_manage_booking','Форма фамилия+билет/код достигнута; поля оставлены пустыми','вход пользовательского пути','2026-11-12'),
        ('CB04','V10_faq_receipt','Поиск чек выдаёт ответ; ответ раскрыт, обращений нет','один запрос FAQ','2026-11-12'),
    ]
    for cid,eid,fact,unit,period in browser_claims:
        path=ROOT/'evidence/browser'/(eid+'.json');data=json.loads(path.read_text())
        val=data['tool_result']['value']
        claims.append(dict(claim_id=cid,source_id=eid,source_row_ids=[eid+':observation'],fact=fact,
                           limit='Один desktop пример; не проверка оплаты/исполнения и не статистическая оценка.',
                           source_sha256=hashb(path.read_bytes()),status='CURRENT_NATIVE_BROWSER_OBSERVATION'))
        selected.append(dict(source_row_id=eid+':observation',source_id=eid,row_number='observation',row_sha256=hashb(canonical(val)),text=fact,
                             source_sha256=hashb(path.read_bytes()),text_file_sha256=None,url=val['url'],
                             retrieved_at_utc=data['observed_at_utc'],organization='АО «Ред Вингс»',publication_date=None,
                             period=period,unit=unit,granularity='один анонимный desktop UI-сценарий',
                             status='observed',coverage='Только данный сценарий; число оставшихся билетов не принято за физический inventory.'))
    write('source_claims.json',claims)
    selected=list({r['source_row_id']:r for r in selected}.values())
    table('source_rows.csv',selected)
    write('source_manifest.json',dict(as_of=ASOF,official_pages=registry,git_pins=pins,
          selected_rows_file='source_rows.csv',selected_rows_sha256=hashb((ROOT/'source_rows.csv').read_bytes()),
          selection='Только информационные страницы и цифровые наблюдения; городские таблицы P02/P03 не использовались.',
          not_imported=['Весь старый fixture/архив','Рынок2025 из historical_parameters как оценка цифрового эффекта','P06 toy как данные RW'],
          date_limit='Дата получения известна; дата публикации большинства информационных страниц не указана. Last-Modified не приравнен к дате вступления условия в силу.'))

    assumptions=[]
    def A(aid,value,unit,basis,affected,sensitivity,refine,range_=None,status='UNKNOWN',selector='P11 исследовательский агент'):
        assumptions.append(dict(assumption_id=aid,value=value,unit=unit,selected_by=selector,basis=basis,
            approval_status='Не отдельное согласование пользователя; метод/неизвестное для исследовательского пакета',
            status=status,range_or_unknown=range_ if range_ is not None else 'UNKNOWN',
            affected_conclusions=affected,sensitivity=sensitivity,how_to_refine=refine))
        return aid
    A('P11-SCOPE','2027-01..2028-12','24 месяца','Текущая задача пользователя','Все денежные и сетевые сравнения',
      'Не умножать наблюдённую неделю/день на год','Даты запуска и экспозиции по месяцам',status='USER_REQUIREMENT')
    A('P11-AUDIT','SVX→OMS 2026-11-20, 1 взрослый; desktop1280×800','сценарий UI',
      'Повтор доступного старого примера для сравнения пути; не репрезентативная выборка',
      'Наблюдение поиска/тарифов','Один маршрут, один экран, lead примерно8дней; сезон/распродажа влияют на цену',
      'Расширить разрешённые пути на mobile, другие периоды/аэропорты, только до брони',status='AUDIT_DESIGN')
    A('P11-CUTOFF',None,'точный момент/аэропорт/правило','Публичные источники не разрешают границу24ч для багажа и3/6ч для Москвы',
      'D02,D04 и тестовые ожидаемые ответы','Неверная граница меняет цену/доступность действия',
      'Владелец правил RW: airport_iata,flight_instance_id,timezone,valid_from/to,cutoff_reference,comparison_operator; B2B contract engine')
    for aid,unit,basis,affected,refine in [
        ('P11-N','подходящие уникальные посетители/заказы/дела по месяцам','Трафик и исходные конверсии RW не получены','Все пороги на экспозицию','Веб-аналитика и OMS: denominator, bot removal, visitors, channels, cohorts,month'),
        ('P11-EFFECT','абсолютная разность вероятностей/средних','Никакого A/B в RW не проводилось','D01..D04, знак эффекта','Рандомизированный опыт после инструментирования'),
        ('P11-MARGIN','RUB на добавочную исполненную поездку/услугу','Нет net fare, переменных издержек и перетока','D01,D02,capacity constrained effect','Финконтроль P04/P06 + P05/P09: совместное приращение продаж и переменных затрат'),
        ('P11-COST','RUB по дате платежа/месяцу начисления','Нет сметы владельца движка/контракта поддержки; старые planning caps не подтверждены','D01..D04, funding','Разбивка RW/поставщика: лицензия, внедрение, QA, аналитика, контент, сопровождение, налоги, платёжный график'),
        ('P11-LOSS','RUB полного затронутого бизнеса','Не получены потеря допуслуг, поздних продаж, каналов и замещение','D01,D02,D03','Все каналы по order_id/product_id/flight_instance_id до вылета и после возврата'),
        ('P11-TIME','минуты на выполненное дело','Нет case-level данных об обработке и повторах','D03,D04, ресурс','Логи contact centre: case_id, touches, active_minutes, queue, resolution, reopens'),
        ('P11-RATE','RUB/устранимый оплаченный час','Нет marginal ставки контракта/сверхурочных; средняя зарплата не marginal cash rate','D03,D04, support cash','Контракт и связь сокращённых оплачиваемых часов с расходом'),
        ('P11-CASHSHARE','доля0..1 подтверждённого устранимого расхода','Освобождение времени не доказывает уменьшение payroll;0/1 только логические границы','D03,D04, cash','Контракт аутсорсинга/сверхурочные/план найма и подписанный план сокращения расхода',),
        ('P11-HORIZON','даты окончания исходов','Возврат/чарджбэк и поздняя продажа не ограничены14днями','Все causal измерения','Установить окна по lead и фактическому циклу возврата, держать censored cohort отдельной'),
        ('P11-NETWORK','общая dated capacity/choice KEEP и P','Ни P02 export, ни неделя P03 не являются принятой годовой RW сетью','Пассажиры, доля рынка, D01 эффект','P09 complete same-resource P/KEEP; P05 choice; P06 exact accepted manifests'),
        ('P11-FISCAL','RUB и выбранный год цен/НДС/FX','Публичная gross цена не net revenue RW; партнёрские gross платежи не комиссия RW','Полный денежный мост','P04 договоры/налоги/FX и даты recognition; не переводить2026цены в2027молча'),
        ('P11-ROUTING','версия правил по типу билета/продавцу','Публичный текст не доказывает статус реальной заявки или наличие кабинета статусов','D03,D04','Владелец продукта: voluntary/involuntary, fare, purchase channel, service, route kind, airport, deadlines'),
        ('P11-ERROR-TOLERANCE','допуск некритичных ошибок','Нет согласованного business noninferiority margin','A/B guardrails','Владелец сервиса определяет предел после baseline; критически неверные права/цены отдельный immediate stop'),
    ]:
        A(aid,None,unit,basis,affected,'Показатель остаётся неизвестным; порог пересчитывается по формуле, UNKNOWN не ноль',refine,
          range_='[0,1] как логические границы, не эмпирический диапазон' if aid=='P11-CASHSHARE' else None)
    A('P11-EXPERIMENT',dict(alpha_two_sided=0.05,power=0.8,allocation='1:1'),
      'параметры проектирования статистического испытания','Порог ошибки и мощности выбран исследователем для планирования; не оценка результата RW',
      'experiment_design.json','Четыре подтверждающих опыта требуют коррекции множественных проверок или иерархии; MDE и baseline неизвестны',
      'До запуска выбрать один primary economic endpoint, один тест/семейство, variance, practical MDE и длительность',
      range_='Настройки можно изменить; не доверительный интервал цифрового эффекта',status='DESIGN_CHOICE')
    A('P11-STOP','Подтверждённая ошибка прав/цены/срока→немедленная остановка изменённого пути; экономический порог0',
      'операционное правило / RUB incremental contribution','Не сохранять ошибочное содержание как контроль и не выпускать заведомо отрицательную интеграцию',
      'D01..D04','Нулевая граница вклада не означает доказанную окупаемость; нужны mature outcomes и стоимость риска',
      'Назначить владельца инцидента и согласовать MDE/бюджет/устранимые затраты',status='DESIGN_CHOICE')
    A('P11-JOINT','Один общий контроль или факторный тест; не суммировать независимые оценки','правило причинной оценки',
      'Одни и те же посетители, заказ, багаж и обращения пересекаются',
      'Суммарный эффект','Взаимодействие D01×D02 и D03×D04 может изменить знак',
      'Единая группа контроля, ledger event_id и scope_id',status='ACCOUNTING_RULE')

    common_stop=['Подтверждённый неверный срок/цена/право/маршрутизация→остановить изменённую ветку и исправить.',
                 'Не расширять дорогую интеграцию, если верхняя обоснованная граница будущего добавочного вклада не покрывает оставшиеся устранимые затраты.',
                 'При недостаточном трафике/дозревании исходов результат UNKNOWN, а не нулевой или отрицательный эффект.']
    cards=[
      dict(card_id='D01',title='Явный отказ от выбора места',area='Поиск и покупка билета',
        outcome='УСЛОВНА: найдено историческое трение, новый проход остановлен до выбора тарифа',
        observed=['12.11 поиск SVX→OMS и раскрытие тарифов доступны: Лайт5830/Стандарт5930 RUB, один взрослый, вылет20.11, WZ5071 SSJ100.',
                  'Календарь цен и сравнение тарифов уже работают.',
                  '10.11 автор наблюдал дополнительное подтверждение пропуска выбора места; после отказа итог остался5830. Это не доказательство платной навязанной услуги.'],
        already_exists=['Поиск билетов','Календарь ориентировочных цен','Онлайн-покупка','Сравнение тарифов','Самостоятельный выбор места'],
        problem='Повторное окно при осознанном отказе от места подтверждено только историческим проходом10.11. Сбой покупки не установлен.',
        change='На существующем шаге дать явное действие «Продолжить без выбора места»; вариант без повторного убеждающего окна проверить в разрешённом стенде и затем опытом.',
        mechanism='Меньше остановок для отказавшихся→больше завершений; возможная встречная потеря маржи мест/других услуг.',
        metric='Добавочный net contribution всего затронутого бизнеса на подходящего рандомизированного посетителя; paid conversion только secondary.',
        effect_unit='RUB/посетитель; оплаченные заказы/посетитель; добавочные поездки только из P09',
        execution=['Владелец существующего booking engine','Проверка подтверждённого отказа','События показа/отказа/ошибок/оплаты/возврата','Общий all-channel ledger'],
        implementation_cost=dict(status='UNKNOWN',assumption_id='P11-COST',scope='Изменение существующего шага, договор поставщика, QA, аналитика, сопровождение. Старая оценка не смета.'),
        net_contribution='N*delta_paid*m - L - I - O; m не полная цена билета. Для финального решения использовать совместную delta contribution P09/P06.',
        breakeven='delta_paid*=(I+O+L)/(N*m), только N>0,m>0; при m<=0 увеличение числа заказов не обосновывает запуск.',
        required_inputs=['P11-N','P11-EFFECT','P11-MARGIN','P11-COST','P11-LOSS','P11-HORIZON','P11-NETWORK'],
        experiment='Сначала повтор в стенде без реальной брони; затем visitor-level рандомизация по airport pair, dated flight/lead, устройству, тарифу. Оба варианта продают услуги и сохраняют корректный итог. Считать все каналы до закрытия исходов.',
        stop_threshold=common_stop+['Рост paid conversion при падении совокупного вклада не является успехом.'],
        facts=['C01','CB01','CB02'],evidence=['V02_search','V03_fares','HIST_OBS','HIST_D01_MODAL','HIST_D01_BOUNDARY'],
        assumption_ids=['P11-AUDIT','P11-EXPERIMENT','P11-STOP','P11-JOINT']),
      dict(card_id='D02',title='Согласованные сроки и цена багажа',area='Дополнительные услуги',
        outcome='ОЦЕНЕНА как исправление информации; коммерческая интеграция УСЛОВНА',
        observed=['Публичная подробная таблица делит цены по24ч, FAQ советует3+ч.',
                  'Для регулярного внутреннего рейса10–23кг опубликованы минимумы2700/3500 RUB; два сегмента оплачиваются отдельно.',
                  'Добавление багажа при покупке и после неё уже заявлено. Реальное оформление после покупки NOT_RUN.'],
        already_exists=['Продажа багажа на сайте','Мои бронирования','Каталог допуслуг'],
        problem='Слово «выгоднее» не предупреждает о более раннем24-часовом переходе цены. Ровно24ч и last sale cutoff не установлены.',
        change='После подтверждения policy owner синхронизировать FAQ/таблицу/заказ через одно версионированное правило. Для уже существующей продажи показывать включённую норму, действующую цену и срок по каждому плечу; сначала проверить доступную часть в стенде.',
        mechanism='Меньше ошибочных ожиданий/поддержки; возможен новый багаж, но и перенос дорогой поздней продажи в дешёвую раннюю.',
        metric='Net contribution багажа на подходящий заказ по всем каналам до вылета и после возвратов; attach/time-to-purchase вторичны.',
        effect_unit='RUB/подходящий заказ; услуги/заказ; минуты/дело отдельно',
        execution=['Владелец тарифных правил и границ времени','Редактор FAQ/CMS','Booking engine: fare allowance и leg pricing','Аналитик услуг и финконтроль'],
        implementation_cost=dict(status='UNKNOWN',assumption_id='P11-COST',scope='Исправление текста отдельно от общей policy-интеграции; договор, QA границ, EMD fulfilment и сопровождение.'),
        net_contribution='N*delta_attach*m_bag - L_earlylate - L_channels - I - O; не price*все ранние продажи. Переменный вес/топливо/handling/EMD/refunds входят один раз.',
        breakeven='delta_attach*=(I+O+L_earlylate+L_channels)/(N*m_bag), только N>0,m_bag>0.',
        required_inputs=['P11-CUTOFF','P11-N','P11-EFFECT','P11-MARGIN','P11-COST','P11-LOSS','P11-FISCAL','P11-ROUTING'],
        experiment='Неверное/неполное правило исправить всем; A/B только двух корректных представлений. Страты lead относительно24ч, аэропорт, тип рейса, сегмент/стыковка, тариф, канал. Итоговая маржа, а не только early attach.',
        stop_threshold=common_stop+['Не считать успехом рост ранней выручки при падении полной маржи багажа.'],
        facts=['C02','C03','C04'],evidence=['V05_baggage','V06_baggage_faq','V13_baggage_before24','V14_baggage_after24'],
        assumption_ids=['P11-CUTOFF','P11-EXPERIMENT','P11-STOP','P11-JOINT']),
      dict(card_id='D03',title='Понятные условия обмена и возврата',area='После покупки',
        outcome='ОЦЕНЕНА как исправление информационной развилки; исполнение NOT_RUN',
        observed=['Общая инструкция Лайт невозвратен не связывает его с уже продающейся возвратностью прямого международного билета.',
                  'Сайт указывает самостоятельные добровольные возвраты/обмены для собственных онлайн-продаж; вынужденный возврат направляет в другой канал.',
                  'Форма Мои бронирования достигнута; фамилия и номер билета/код оставлены пустыми.'],
        already_exists=['Онлайн-обмен','Самостоятельный добровольный возврат по условиям','Платная возвратность','Контактный центр и форма связи'],
        problem='Общее описание без нужной развилки может направить владельца приобретённой услуги к неверному ожиданию. Частота ошибочных обращений UNKNOWN.',
        change='Связать существующую инструкцию с условиями услуги; короткая развилка причина/продавец/тариф/наличие услуги/тип маршрута/время. Не обещать полного возврата цены, новой услуги или отсутствующего статуса дела.',
        mechanism='Меньше неправильно направленных/повторных контактов и потерянного времени; возврат клиенту не экономия RW.',
        metric='Верно выбранный следующий шаг и время до него; далее cash-устранимые затраты поддержки на исходное дело, повторные контакты/дело.',
        effect_unit='минуты/исходное дело; контакты/дело; RUB только подтверждённых устранимых затрат',
        execution=['Владелец продукта возвратности','Владелец правил тарифов/обмена','Контент и контакты поддержки','QA правил и событий; без нового чат-бота'],
        implementation_cost=dict(status='UNKNOWN',assumption_id='P11-COST',scope='Текст/ссылки отдельно; дерево правил/аналитика/интеграция отдельно; смета не получена.'),
        net_contribution='Saved_cash + verified_other_incremental_contribution - I - O. Freed_hours=N*delta_contacts*t/60; Saved_cash=f*Freed_hours*w. Время и cash не суммируются.',
        breakeven='delta_contacts* =60*(I+O-verified_other_incremental_contribution)/(N*t*w*f), при N,t,w,f>0. Если f=0, support-cash экономия0; польза времени остаётся отдельной.',
        required_inputs=['P11-ROUTING','P11-N','P11-EFFECT','P11-TIME','P11-RATE','P11-CASHSHARE','P11-COST','P11-HORIZON'],
        experiment='После общего исправления правил сравнить две корректные подачи на обезличенных задачах с эталоном владельца; затем при разрешении visitor/case-level A/B. Объединять повторные контакты в исходное дело, дожидаться его закрытия; не проводить реальные возвраты ради теста.',
        stop_threshold=common_stop+['Любое неверное обещание возврата такс/сборов/стоимости услуги или применимости к чартеру без правила→исправление до выпуска.'],
        facts=['C05','C06','C11','CB03'],evidence=['V07_refund','V08_returnability','V09_manage_booking','V15_refund_light'],
        assumption_ids=['P11-ROUTING','P11-EXPERIMENT','P11-STOP','P11-JOINT']),
      dict(card_id='D04',title='Точный срок онлайн-регистрации по аэропорту',area='Основные вопросы и подготовка к вылету',
        outcome='ОЦЕНЕНА как новое найденное расхождение; действующее правило УСЛОВНО',
        observed=['Поиск FAQ «чек» находит ответ и раскрывает действующий канал помощи; дефект этого поискового пути не выявлен.',
                  'check-in-rules: закрытие онлайн за3ч; FAQ подготовки:3ч, в Москве6ч. Аэропорт не назван.',
                  'Реальная регистрация без билета NOT_RUN.'],
        already_exists=['Поиск FAQ','Категории и раскрывающиеся ответы','Онлайн-регистрация','Существующий вход по билету'],
        problem='Два опубликованных описания срока не согласованы; агрегат Москва не указывает DME/ZIA.',
        change='Владелец операций задаёт срок по airport_iata/flight/date/local timezone и valid_from/to; обе статьи получают одно правило с явными исключениями. Если конкретный аэропорт не выбран, не подставлять универсальный срок.',
        mechanism='Меньше неверно выбранного времени/неподходящих попыток и контактов; снижение пропущенных рейсов не доказано.',
        metric='Доля верно определённого крайнего срока в заданиях по аэропортам; минуты до ответа; обращения/исходное дело. Cash только подтверждённые избегаемые расходы.',
        effect_unit='верные ответы/задания; минуты/дело; RUB устранимых расходов отдельно',
        execution=['Операционный владелец online check-in','Airport-specific конфигурация поставщика','Редакторы двух статей','QA временных зон и границ'],
        implementation_cost=dict(status='UNKNOWN',assumption_id='P11-COST',scope='Согласование фактического правила и контент отдельно; персонализированная интеграция только после оценки поставщика.'),
        net_contribution='Verified_avoidable_cash - I - O; предотвращённые опоздания/возвраты UNKNOWN, не включать как экономию без причинного подтверждения.',
        breakeven='Saved_cash >= I+O; для поддержки тот же threshold D03, с отдельной непересекающейся либо совместно измеренной когортой.',
        required_inputs=['P11-CUTOFF','P11-ROUTING','P11-TIME','P11-RATE','P11-CASHSHARE','P11-N','P11-COST','P11-EFFECT'],
        experiment='Сначала авторитетная таблица правил и сценарные задания DME/ZIA/иной аэропорт, own/partner, 24ч/6ч/3ч±граница. Исправить всем. После — сравнение двух корректных формулировок; не сохранять ошибочный срок в контроле.',
        stop_threshold=common_stop+['Пока истинный airport-specific срок UNKNOWN, автоматизированная персональная инструкция не допускается как достоверная. Это не экономический отказ от проверки.'],
        facts=['C07','C08','C09','CB04'],evidence=['V10_faq_receipt','V11_checkin_rules','V12_checkin_faq'],
        assumption_ids=['P11-CUTOFF','P11-EXPERIMENT','P11-STOP','P11-JOINT'])
    ]
    for c in cards:
        c['threshold_feasibility']='Для прироста вероятности threshold<=1-baseline; для снижения вероятности threshold<=baseline. Для числа контактов на дело верхняя граница определяется наблюдённым baseline count, не вероятностью. Невыполнимый порог отвергает лишь данный сценарий затрат/маржи.'
        c['economic_cost_definition']='В формулах I и O — затраты, признанные за выбранный горизонт, с амортизацией при применимой капитализации. I_cash и O_cash — отдельные выплаты по датам. Смета и учётная политика UNKNOWN; прибыль не равна остатку бюджета.'
        c['disjoint_terms']='m содержит только вклад до отдельно перечисленных L. Если используется joint all-channel contribution, уже включённые потери/услуги не вычитать и не добавлять повторно.'
    cards[2]['net_contribution']='Economic: ΔC_support_E + verified_other_ΔC_E - I_E - O_E. Cash: avoided_support_payments - I_cash - O_cash с отдельным календарём. Freed_hours=N*delta_contacts*t/60; avoided_support_payments=f*Freed_hours*w только при подтверждённой устранимости.'
    cards[2]['breakeven']='Cash test: delta_contacts*=60*(I_cash+O_cash-other_verified_cash)/(N*t*w*f), N,t,w,f>0. Economic threshold использует устранимые начисленные затраты и I_E/O_E. f=0 не даёт cash-экономии времени; реальный f UNKNOWN.'
    cards[3]['net_contribution']='Economic: verified_avoidable_expense_E - I_E - O_E. Cash: verified_avoided_payments - I_cash - O_cash. Предотвращённые опоздания/возвраты UNKNOWN; не включать их без причинной оценки.'
    cards[3]['breakeven']='Отдельно: avoided_expense_E >= I_E+O_E; avoided_cash >= I_cash+O_cash. Для поддержки формула D03 с собственной непересекающейся либо совместно измеренной когортой.'
    write('digital_cards.json',dict(as_of=ASOF,stage_a='COMPLETE_WITH_EXPLICIT_BOUNDARIES',stage_b='NOT_RUN',cards=cards,
      recommendation='Сначала подтвердить и согласовать опубликованные правила D02/D03/D04; D01 — ограниченный эксперимент после повторения в разрешённом стенде. Бюджет дорогих интеграций не утверждён.',
      forecast=dict(passengers=None,revenue=None,incremental_full_profit=None,cash=None),
      no_new_product=['Не создавать заново онлайн-поиск/продажу/FAQ/кабинет/возвратность','Не предлагать AI как самостоятельное доказательство эффекта']))

    effects=[]
    for c in cards:
        effects.append(dict(card_id=c['card_id'],area=c['area'],status=c['outcome'],primary_metric=c['metric'],unit=c['effect_unit'],
          horizon='2027-2028, по месяцу запуска/экспозиции; наблюдение UI2026-11-12',
          mechanism=c['mechanism'],net_contribution_formula=c['net_contribution'],breakeven=c['breakeven'],
          actual_N=None,measured_effect=None,implementation_rub=None,operating_rub=None,
          incremental_profit_rub=None,incremental_passengers=None,capacity_owner='P09/P05/P06',
          cash_status='NOT_ESTIMATED',assumption_ids=c['required_inputs']+c['assumption_ids'],claim_ids=c['facts'],
          stop_threshold=c['stop_threshold'],scope='Затронутый цифровой путь всего бизнеса RW; связь с проектной сетью8-12пар только после отдельного joint run'))
    table('digital_effects.csv',effects)

    hist=json.loads((ROOT/'inputs/historical_parameters.json').read_text())['digital_scenarios']
    historical=[]
    for r in hist:
        aids=[]
        for k,v in r.items():
            if k in ('id','scenario','metric'): continue
            aid=f"P11-HIST-{r['id']}-{r['scenario']}-{k}"
            A(aid,v,'сохранённая единица поля '+k,'Точный старый параметр из d48b4a4f; не данные/смета RW и не выбранная новая оценка',
              'Только historical_threshold_replay.csv','Годовой чувствительный пример; не интервал доверия и не прогноз2027/2028',
              'Заменить по полю на подтверждённые analytics/finance/procurement inputs',status='HISTORICAL_DIAGNOSTIC_NOT_ADMITTED',selector='Автор historical digital_growth10.11; P11 только воспроизводит')
            aids.append(aid)
        n=r['eligible_events']; d=r['uplift_absolute']; m=r['unit_contribution_rub']
        loss=r['cannibalized_contribution_rub']; impl=r['implementation_cash_rub']; op=r['annual_support_cash_rub']
        threshold=(loss+impl+op)/(n*m)
        historical.append(dict(card_id=r['id'],historical_scenario=r['scenario'],status='FROZEN_INPUT_REPLAY_NOT_RW_FORECAST',
            eligible_events=n,assumed_absolute_delta=d,unit_contribution_rub=m,cannibalized_contribution_rub=loss,
            implementation_rub=impl,annual_support_rub=op,first_year_resource_equivalent_rub=n*d*m-loss-impl-op,
            breakeven_absolute_delta=threshold,breakeven_percentage_points=100*threshold,
            cash_effect_rub=None,assumption_ids=aids,scope='Старый условный один год; не календарь2027-2028',
            source_row_id=f"HIST_PARAMS:{r['id']}:{r['scenario']}",source_row_sha256=hashb(canonical(r)),
            source_file_sha256=hashb((ROOT/'inputs/historical_parameters.json').read_bytes()),
            metric_adapter='D03: прежняя вероятность повтора за7дней и планируемые контакты/дело — разные единицы. Автоматический перенос запрещён.' if r['id']=='D03' else 'Оплата/посетитель либо покупка багажа/предложение только в старом условном расчёте; единица новой когорты требует проверки.',
            interpretation='D03: эквивалент ресурса, не денежная прибыль; D01/D02: условная арифметика, не принятое P09/P06 приращение'))
    table('historical_threshold_replay.csv',historical)

    # Explicit schema and formulas: no new passenger capture or money model is implemented here.
    months=[f'{y}-{m:02d}' for y in (2027,2028) for m in range(1,13)]
    funnel=dict(as_of=ASOF,method='Контракт измерения причинного эффекта и пороги; НЕ автономная модель спроса/денег',
      units={'visitor':'рандомизационная единица; не пассажир','session':'технический визит; повторные визиты нельзя считать разными покупателями',
             'order':'может иметь несколько пассажиров/поездок и услуг','journey':'одна конечная поездка','segment':'занятое кресло физического датированного плеча',
             'service':'EMD/исполненная услуга, с event_id; у багажа на пересадке правила по участкам','case':'исходное дело поддержки со всеми повторами'},
      stages=[dict(event=x,unit=u) for x,u in [('eligible_visitor','посетитель'),('search_submitted','поиск'),('search_returned','поиск'),
        ('fare_view','предложение'),('fare_confirmed','действие до потенциальной брони'),('optional_service_offer','order/leg/service'),
        ('passenger_form','заказ'),('booking_created','PNR/OMS заказ'),('paid','оплата'),('ticketed','билет'),('flown','passenger segment'),
        ('service_fulfilled','EMD/услуга'),('refund_settled','денежный event'),('case_resolved','исходное дело')]],
      unobserved=['booking_created','paid','ticketed','flown','service_fulfilled','refund_settled','case_resolved'],
      primary_estimator='Разность среднего зрелого вклада по intent-to-treat посетителям/делам; не условно среди выживших оплативших.',
      calendar=[dict(month=m,eligible_exposures=None,launch_date=None,keep_contribution=None,project_contribution=None,cash_delta=None,status='UNKNOWN') for m in months],
      identities=dict(variable_contribution='net earned fare + net earned ancillary commission/revenue - incremental passenger/service/flight variable costs',
        full_incremental_result='joint_project_contribution - same-resource_future_KEEP_contribution - unique incremental fixed/startup/depreciation events',
        cash='dated receipts - settlements/refunds - operating/investment/tax/finance payments with opening/terminal obligations; not recognized profit',
        support_time='N_cases * delta_contacts_per_case * active_minutes_per_contact /60; add change of active time once, not twice',
        support_cash='Only contractually avoided outsourcing/overtime/payroll or documented avoided hire. Fixed payroll and freed minutes→no inferred cash saving.'),
      threshold_variable_definitions={'N':'Уникальная подходящая экспозиция выбранной когорты и горизонта; visitors/orders/cases не смешивать',
        'delta':'Абсолютная разность вероятностей либо контактов/дело по указанной метрике; не относительный процент',
        'm':'Net marginal contribution до явно отдельных L; в подтверждённом joint результате decomposition не добавляется вторично',
        'I_E/O_E':'Признанные за горизонт экономические затраты; капитализация/амортизация по P04',
        'I_cash/O_cash':'Датированные выплаты; для funding отдельны от I_E/O_E',
        't':'Активные минуты на устранённый контакт; изменение времени оставшихся контактов считается один раз',
        'w':'Применимая marginal ставка на оплачиваемый час; не автоматически средняя зарплата',
        'f':'Доля высвобождённых часов, которая реально исключается из оплаты; логические0..1, фактическое значениеUNKNOWN'},
      capacity_constraint='D01 additional paid orders do not create seats. P09 jointly reallocates P05 demand across dated physical legs in P06, preserves KEEP sold demand and displaced/alternative traffic.',
      channel_constraint='Сайт↔агентство может менять distribution expense, но не общий спрос; агентские комиссии и веб-расходы учитываются по all-channel delta один раз.',
      cross_sell='Внешний отель/трансфер/eSIM: валовой чек партнёра не выручка RW; нужна исполненная комиссия/договор. В этот пакет денежные эффекты не включены.',
      ancillary_retiming='Ранняя покупка вместо поздней: считать полную delta net margin по всем каналам; не только incremental attach раннего окна.',
      connection_rule='Одна поездка получает тариф один раз, каждый physical leg расходует кресло. Багаж: соблюсти опубликованную оплату по участкам и уникальный EMD event.',
      aircraft_rule='Видимый SSJ100 в поиске не калибрует расходы будущего SJ100/ПД8; fulfilment costs получают aircraft_variant и источник P04.',
      double_count_controls=['Единый visitor/order/case ledger','Один event_id на доход/расход/возврат','D01,D02,D03,D04 не суммируются из независимых тестов','Время поддержки не добавлять к cash повторно'],
      assumption_ids=['P11-SCOPE','P11-N','P11-HORIZON','P11-NETWORK','P11-JOINT','P11-FISCAL'])
    write('funnel_and_economics.json',funnel)
    write('P09_integration_contract.json',dict(status='PROPOSED_MEASUREMENT_ADAPTER_NOT_IMPLEMENTED_OR_ADMITTED',
      consumer='P09 joint comparison using P05/P06',producer_contract_pin='982f13d9b6c378ed9581125ecc5c40f17dade6a3',
      context_required=['evaluation_id','programme_id','programme_version','fleet_scope_id','external_scenario_id','delivery_calendar_id',
        'market_version','choice_version','cost_version','keep_evaluation_id','input_manifest_sha256','affected_scope_id','price_year'],
      input_columns=['digital_change_id','experiment_id','cohort_id','randomization_unit','month','airport_pair','flight_instance_id','product_id','channel',
        'eligible_denominator','effect_status','effect_estimator','uncertainty_method','net_margin_scope','cash_avoidable_status','source_id','assumption_id','sha256'],
      route=['D01: измеренный all-channel treatment effect передаётся P05/P09 для совместного распределения; P11 не меняет intercept/logit и не задаёт процент роста спроса.',
             'D02: только принятое joint число реально исполненных услуг и net unit rate; признание дохода/расхода и денежные события у P04/P06.',
             'D03/D04: только подтверждённый avoids cost как уникальный economic/cash event; освободившееся время отдельно.',
             'Внедрение и сопровождение: уникальные startup/operating_fixed events с владельцем, accrual_month, payment plan; не списывать бюджет и амортизацию дважды.'],
      acceptance_gates=['Эксперимент измерен и дозрел','Все4изменения имеют joint контроль/дедупликацию',
        'Принятая dated physical capacity и same-resource KEEP','P05 choice согласована','P04 net rates/cost/tax/cash accepted',
        'P06 required context and full manifests accepted; авторские42checks не независимая приёмка RW'],
      output_gates=['Нет доступных кресел→никакого обещания добавочных пассажиров','8–12пар project scope отдельно от whole_business',
        'Zero-new-Tu214 branch не отменяет digital, но digital не создаёт новые самолёты','Все неизвестные величины null/UNKNOWN, не0']))

    experiments=[]
    for c in cards:
        experiments.append(dict(card_id=c['card_id'],plan=c['experiment'],primary=c['metric'],randomization='Посетитель либо исходное дело; не повторный контакт',
          measured_baseline=None,practical_mde=None,variance=None,estimated_sample_size=None,actual_start=None,
          power_status='NOT_COMPUTABLE_WITHOUT_BASELINE_VARIANCE_TRAFFIC_AND_COST',
          sample_size_rule='Для бинарной secondary метрики: n/arm=[z(1-alpha/2)*sqrt(2*pbar*(1-pbar))+z(power)*sqrt(p0*(1-p0)+p1*(1-p1))]^2/(p1-p0)^2; normal approximation. Primary economic endpoint требует своей variance/cluster-aware power.',
          completion='Покрыть lead, device, сезон, аэропорт/тип рейса, завершённые/возвращённые исходы; один день или месяц не гарантируют достаточную мощность.',
          stop=c['stop_threshold'],assumption_ids=['P11-EXPERIMENT','P11-STOP','P11-HORIZON','P11-ERROR-TOLERANCE','P11-JOINT']))
    write('experiment_design.json',dict(status='DESIGN_ONLY_NOT_RUN',experiments=experiments,
      multiple_testing='Выбрать один primary подтверждающий пакетный тест либо заранее учесть семейство тестов; мощность normal approximation не доказывает качество RW.'))

    qa=[
      ('Q01','FAQ чек','Найти чек без билета','Поиск находит ответ, спам→контактный центр/форма','OBSERVED','C07','V10_faq_receipt'),
      ('Q02','Нет маршрутной квитанции','Есть идентификатор','Существующее Мои бронирования; выполнение NOT_RUN','PUBLIC_CONDITION_ONLY','C07','V09_manage_booking'),
      ('Q03','Лайт без возвратности','Добровольно; билет сайта','Общее правило невозвратности/обмен по условиям; исполнение NOT_RUN','PUBLIC_CONDITION_ONLY','C05','V15_refund_light'),
      ('Q04','Прямой международный билет','Есть приобретённая возвратность; до вылета>24ч','Показать условия возврата тарифа с исключениями; не обещать всю цену','PUBLIC_CONDITION_ONLY','C06','V08_returnability'),
      ('Q05','Внутренний рейс/чартер','Запросить возвратность как универсальную опцию','Внутренний не входит в опубликованную область; charter eligibility UNKNOWN','PUBLIC_CONDITION_ONLY','C06','V08_returnability'),
      ('Q06','Багаж','>24ч, внутренний регулярный,10–23кг','Опубликован минимум2700; live quote UNKNOWN','PUBLIC_CONDITION_ONLY','C02','V13_baggage_before24'),
      ('Q07','Багаж','<24ч, внутренний регулярный,10–23кг','Опубликован минимум3500; last sale cutoff UNKNOWN','PUBLIC_CONDITION_ONLY','C03','V14_baggage_after24'),
      ('Q08','Багаж','Ровно24ч','Правило границы UNKNOWN→проверить owner, не назначать цену','OWNER_RULE_REQUIRED','C02','V13_baggage_before24'),
      ('Q09','Багаж','Два плеча','Каждый участок оплачивается; реальное EMD/fulfilment NOT_RUN','PUBLIC_CONDITION_ONLY','C03','V14_baggage_after24'),
      ('Q10','Онлайн-регистрация','DME vs ZIA;3/6ч и границы','Единого подтверждённого airport-specific правила нет; запрос owner','OWNER_RULE_REQUIRED','C08,C09','V11_checkin_rules,V12_checkin_faq'),
      ('Q11','Вынужденный возврат','Болезнь; билет сайта','Уведомление/документы/канал по опубликованным условиям; не имитировать заявку','PUBLIC_CONDITION_ONLY','C11','V07_refund'),
      ('Q12','Куплено у агента','Изменение/возврат','Маршрутизация по месту покупки; не выдавать сайт за универсальный процесс','PUBLIC_CONDITION_ONLY','C05,C11','V07_refund'),
    ]
    table('verification_scenarios.csv',[dict(scenario_id=a,path=b,condition=c,expected_public_behavior=d,status=e,claim_ids=f,evidence_ids=g,actual_transaction='NOT_RUN') for a,b,c,d,e,f,g in qa])

    evidence=[]
    for f in sorted((ROOT/'evidence').rglob('*.png')):
        rel=str(f.relative_to(ROOT));stem=f.stem;side=f.with_suffix('.json')
        meta=json.loads(side.read_text()) if side.exists() else {}
        data=meta.get('tool_result',{}).get('value',{})
        if not isinstance(data,dict): data={}
        url=data.get('url',meta.get('snapshot',{}).get('url'))
        if stem=='V01_home': url='https://flyredwings.com/'
        if 'historical' in rel:
            date='2026-11-10 19:11–19:23 МСК (исторический пакет)';status='HISTORICAL_EXACT_BLOB'
        else:
            date=meta.get('observed_at_utc','2026-11-12, точное время PNG не записано');status='CURRENT_NATIVE_T3_SCREENSHOT'
            if stem=='V05_baggage': date='2026-11-12; JSON time относится к тексту; уточняющий PNG сделан позже в том же проходе, точное время PNG не записано'
        evidence.append(dict(evidence_id=stem,file=rel,sha256=hashb(f.read_bytes()),date=date,url=url,
           viewport_css='1280×800; PNG2560×1600 при DPR2',status=status,
           coverage='Один desktop viewport; screenshot не доказывает выполнение оплаты/возврата',
           image_note='Некоторые raw PNG имеют прозрачный фон; смотреть на белом фоне. Альфа не интерпретируется как дефект контраста сайта.'))
    write('visual_evidence.json',dict(evidence=evidence,own_tabs=['tab_3_638ba922-a69c-49ec-94da-bd549ba209fc','tab_4_638ba922-a69c-49ec-94da-bd549ba209fc','tab_6_638ba922-a69c-49ec-94da-bd549ba209fc'],
      own_tabs_closed=True,other_tabs_touched=False,profile_changed=False,secret_values_saved=False,
      native_limit='Одна попытка fill с selector input[name=departure_0] дала strict mode violation: resolved to2elements. Исправлено selector:visible; браузер не заменялся. preview_snapshot использовался для PNG; DOM читался native preview_evaluate.',
      historical_boundary='Старый автор отмечал анонимную shopping session и отсутствие PNR/билета; P11 не переквалифицирует её как новый успешный transaction.'))
    audit=[
      dict(path='Поиск/предложение',date=ASOF,status='OBSERVED_TO_FARE_VIEW',scenario='SVX→OMS20.11.2026,1adult,oneway',
           fact='Результат и2тарифа доступны; кнопки выбора тарифа не нажаты',evidence=['V02_search','V03_fares']),
      dict(path='Покупка/место/багаж/пассажир/оплата',date=ASOF,status='NOT_RUN_AFTER_FARE_VIEW',
           scenario='Граница без создания заказа/брони',fact='Как купить билет предупреждает о брони до оплаты; повторение старого skip-modal не выполнялось',evidence=['V04_how','HIST_OBS']),
      dict(path='Допуслуги',date=ASOF,status='PUBLIC_RULES_OBSERVED_PURCHASE_NOT_RUN',scenario='Багаж и возвратность',
           fact='Работающий каталог/публичные правила; замечания D02/D03',evidence=['V06_baggage_faq','V08_returnability','V13_baggage_before24','V14_baggage_after24']),
      dict(path='Основные вопросы',date=ASOF,status='SEARCH_AND_ACCORDION_OBSERVED',scenario='Поиск чек, раскрытие ответа; подготовка к полёту',
           fact='Поиск работает; сроки check-in расходятся',evidence=['V10_faq_receipt','V11_checkin_rules','V12_checkin_faq']),
      dict(path='После покупки',date=ASOF,status='ENTRY_OBSERVED_TRANSACTION_NOT_RUN',scenario='Вход Мои бронирования без данных',
           fact='Пустая форма фамилия+билет/код; статусы и исполнения реального дела UNKNOWN',evidence=['V09_manage_booking','V15_refund_light'])]
    write('audit_scenarios.json',audit)

    limits=dict(stage_a='COMPLETE: заданные4области разобраны, доступные пути/правила и пороги зафиксированы',
      stage_b='Не выполнен живой коммерческий/постбилетный эксперимент; не является экономическим отказом',
      known=['13публичных страниц текущего среза','Результат поиска и раскрытие тарифа','FAQ query и ответ','Публичная форма управления','3информационные находки; историческое трение D01'],
      not_run=['Создание заказа/PNR','Ввод личных/чужих данных','Оплата/билет/реальная квитанция','EMD purchase/fulfilment/refund','Реальный обмен/возврат','Заявка/сообщение поддержке','Онлайн-регистрация реального пассажира','A/B и измерение конверсии/маржи','Mobile/все маршруты/все сезоны'],
      unknown=['Реальная конверсия, трафик и объём обращений RW','Цены/сметы движка и ставки поддержки','Денежная устранимость времени','Возвратность на конкретном чартерном продукте','Фактические cutoff24ч и Москва3/6ч','Статус реального дела за идентификатором'],
      prohibitions=['Не считать функцию новой, если она уже существует','Не переносить old hypothetical profits в общий результат','Не суммировать4эффекта','Не обещать прирост пассажиров/№2 без joint network run','Не публиковать Site/менять продукт RW'],
      handoff_dependencies=[
        dict(id='B01',owner='RW policy/operations',fields=['airport_iata','flight_instance_id','valid_from/to','timezone','cutoff_reference','exact comparator'],purpose='Разрешить D02/D04 границы',blocks='Автоматическое обещание точного срока; не source audit'),
        dict(id='B02',owner='RW booking engine',fields=['sandbox','stage creates PNR','optional skip behavior','price/EMD policy'],purpose='Повторить D01 в разрешённом стенде',blocks='Текущая неисправность/эффект D01'),
        dict(id='B03',owner='RW analytics/contactcentre',fields=['eligible cohorts','funnel events','case linkage','active time','all-channel fulfilled margin','mature refunds'],purpose='Рассчитать baseline,power и causal эффект',blocks='Вывод о приросте/экономии'),
        dict(id='B04',owner='RW procurement/P04',fields=['implementation quote','supplier support','avoidability plan','tax/FX','accrual and payment calendar'],purpose='Получить бюджет и денежный мост',blocks='Численная окупаемость/funding'),
        dict(id='B05',owner='P09/P05/P06',fields=['accepted P/KEEP dated24monthnetwork','common capacity/choice','scope/event IDs'],purpose='Связать digital с общей сетью',blocks='Добавочные пассажиры/доля рынка и полная экономика')],
      independent_review='NOT_RUN; сохранены происхождение и границы прежнего независимого review; этот P11 авторский пакет, не APPROVE общего решения')
    write('validation_limits.json',limits)
    write('assumptions_register.json',assumptions);table('assumptions_register.csv',assumptions)
    write('assumption_changes.json',dict(change_type='Новые выводы и новая проверка официальных страниц; frozen прежний пакет не изменён',
      added=['D04: опубликованные3/6часов без аэропорта','Текущий stop доfare-select-button ввиду предупреждения о pre-payment booking'],
      retained=['Публичные информационные расхождения D02/D03 повторно подтверждены','Существующие онлайн-функции признаны существующими'],
      not_promoted=['Старые costs,uplifts,traffic,margins → только historical replay; не доверительные границы и не RW прогноз'],
      old_correction='EV-DIGITAL-N01: не добавлять слово регулярный к возвратности; charter applicability остаётся UNKNOWN'))

    write('counterexamples.json',dict(status='ACCOUNTING_COUNTEREXAMPLES_NOT_RW_ESTIMATES',assumption_ids=['P11-JOINT','P11-NETWORK','P11-CASHSHARE'],cases=[
      dict(id='CE01',case='Заказ пришёл на сайт вместо агентства',web_conversion='выше',company_journeys='без изменения',conclusion='Считать только net distribution cost difference; не полный билет/добавочного пассажира.'),
      dict(id='CE02',case='Рейс был полон; новый ранний покупатель вытеснил прежнего',web_conversion='выше',company_segments='без изменения',conclusion='Прирост спроса не равен приросту перевозки; revenue mix может улучшиться/ухудшиться.'),
      dict(id='CE03',case='Та же услуга багажа куплена раньше вместо поздней',attach_in_early_window='выше',total_service_count='без изменения',conclusion='Опубликованные минимумы2700 и3500 различаются на800RUB; это сравнение минимумов, не гарантированная реальная потеря маржи.'),
      dict(id='CE04',case='Контактов меньше; тот же оплаченный штат/контракт',time='высвобождено',cash_saving='Не следует из времени; при неизменной оплате0',conclusion='Отдельно показать операционную пользу и стоимость изменений.'),
      dict(id='CE05',case='D01 увеличил оплаты, D02 изменил багаж в том же заказе',conclusion='Нельзя прибавить две независимые оценки вклада, уже включающие тот же багаж.'),
      dict(id='CE06',case='Пассажиру вернули уплаченную сумму',cash='отток',conclusion='Возврат не экономия; высвобождение места и последствия продаж пересчитываются отдельно общим ядром.')]))

    write('handoff.json',dict(package='P11',state='STAGE_A_COMPLETE_STAGE_B_EXPLICIT',language='ru',as_of=ASOF,
      write_scope='context/35_full_programme_execution_20261112/P11/',git_mutations=False,children_started=False,
      entrypoints=['handoff.md','digital_cards.json','digital_effects.csv','funnel_and_economics.json'],
      source_pins=pins,source_manifest='source_manifest.json',source_row_ids='source_rows.csv',visual_evidence='visual_evidence.json',
      units='RUB/посетитель, RUB/заказ, минуты/дело отдельно; поездки/сегменты только P09; gross опубликованные цены2026 не net ставки2027',
      period='2027-2028 целевой календарь; новый audit12.11.2026; historical10.11.2026 отдельно',
      coverage='13officialpublicpages;1desktopoffer;FAQquery;manageentry;реальныеtransactionsNOT_RUN',
      assumptions='assumptions_register.json/csv',remaining='validation_limits.json:B01-B05',
      numerical_results='Фактический uplift, прибыль, cash и пассажиры UNKNOWN. Конкретные исторические thresholds — только frozen diagnostic replay.',
      coordinator_action='Проверить integrity, коммитить только файлы output_manifest; P11 не делал git mutations и не ждёт другие пакеты. Source corpus не импортировать как model inputs.',
      core_boundary='P06 conditional engine not accepted RW forecast; P02 source export not physical seats; P03 dated week not annual/free fleet.',
      hashes='Все файлы output_manifest.json; source rows individually hashed; JSON canonical row hash documented in validate_package.py'))
    print(json.dumps(dict(cards=len(cards),claims=len(claims),selected_source_rows=len(selected),assumptions=len(assumptions),screenshots=len(evidence)),ensure_ascii=False))

if __name__=='__main__':main()
