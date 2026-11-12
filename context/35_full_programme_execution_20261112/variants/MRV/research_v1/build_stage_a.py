"""Собрать исследовательский Stage A MRV; запись только рядом с этим файлом.

Это спецификация исследования и условных программ, не денежная/choice-модель.
Общие входы читаются исключительно через git show exact SHA.
"""
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREFIX = 'context/35_full_programme_execution_20261112/'
ASOF = '2026-11-12'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def write_json(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def write_csv(name, rows, fields=None):
    if fields is None:
        fields = list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT / name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(name):
    return list(csv.DictReader((ROOT / name).open()))


pins = json.loads((ROOT / 'source_pins.json').read_text())
pins['pins']['P05'] = subprocess.check_output(['git', 'rev-parse', 'a63a047'], text=True).strip()
pins['continuation_policy'] = 'Ранее сохранённые sources/receipts/usable_tranche_01 не изменены. Дополнение Stage A; никаких операций изменения Git.'


def pinned(tag, path, outfile=None, predicate=None):
    commit = pins['pins'][tag]
    raw = subprocess.check_output(['git', 'show', commit + ':' + path])
    rec = {'input_id': tag + ':' + path, 'commit_sha': commit, 'path': path,
           'git_blob_sha': subprocess.check_output(['git', 'rev-parse', commit + ':' + path], text=True).strip(),
           'sha256': sha(raw), 'bytes': len(raw)}
    existing = next((r for r in pins['files'] if r['input_id'] == rec['input_id']), None)
    if existing:
        assert existing['sha256'] == rec['sha256'], rec['input_id']
    else:
        pins['files'].append(rec)
    if predicate is not None:
        records = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        selected = [{'source_file': path, 'source_commit': commit, 'source_row_number': i,
                     'source_row_sha256': sha(canonical(r)), **r}
                    for i, r in enumerate(records, 2) if predicate(r)]
        if outfile:
            write_csv(outfile, selected)
        pins.setdefault('continuation_selected', {})[rec['input_id']] = {
            'source_rows': len(records), 'selected_rows': len(selected), 'extract': outfile}
        return selected
    if outfile:
        (ROOT / outfile).write_bytes(raw)
    return raw


# Повторная привязка сохранённых исходных файлов, без копирования всего архива.
for old in list(pins['files']):
    raw = subprocess.check_output(['git', 'show', old['commit_sha'] + ':' + old['path']])
    assert sha(raw) == old['sha256'], old['input_id']

SPOKES = ['KUF', 'GOJ', 'PEE', 'CEK', 'UFA', 'KZN', 'SVX', 'OMS']
od = pinned('P05', PREFIX + 'P05/od_monthly.csv', 'inputs/P05_od_monthly_MRV_target8.csv',
            lambda r: (r['origin_market'] == 'MRV' and r['destination_market'] in SPOKES)
            or (r['destination_market'] == 'MRV' and r['origin_market'] in SPOKES))
pinned('P05', PREFIX + 'P05/net_yield.csv', 'inputs/P05_net_yield_MRV.csv',
       lambda r: 'MRV' in r['demand_pool_id'])
for name in ['choice_model.json', 'handoff.json', 'assumptions_register.csv']:
    pinned('P05', PREFIX + 'P05/' + name, 'inputs/P05_' + name)
for name in ['producer_contract.json', 'README.md']:
    pinned('P06', PREFIX + 'P06/' + name, 'inputs/P06_' + name)
pinned('P03', PREFIX + 'P03/aircraft_type_parameters.csv', 'inputs/P03_superjet_parameters.csv',
       lambda r: r['aircraft_type'] in ['RRJ95B', 'RRJ95LR_100', 'SJ100_PD8'])
pinned('P04', PREFIX + 'P04/thresholds.csv', 'inputs/P04_thresholds.csv', lambda r: True)
pinned('P04', PREFIX + 'P04/cost_ranges.csv', 'inputs/P04_required_unknown_costs.csv',
       lambda r: r['status'] == 'unknown' and r['aircraft_type'] in ['specified_type_required','SSJ100_SaM146','SJ100_PD8']
       and r['key'] in ['fuel_contract_future','fuel_burn_SJ100_PD8','mro_hour','mro_cycle','mro_calendar',
       'crew_payroll','crew_variable','crew_hotel','navigation','lease','owned_depreciation','insurance',
       'base_operations','base_MRO_capacity','reserve_aircraft','entry_expense','induction_expense',
       'launch_capex','security_deposit','exit_penalty','redelivery','ferry','distribution_payment',
       'passenger_other','disruption','foreign_handling','foreign_fuel','fx','international_access',
       'interest','VAT','donor_lost_contribution','new_tail_opportunity','ticket_collection',
       'supplier_payment','support_payment'])
write_json('source_pins.json', pins)

# Нормализация только однозначного имени Уфы; исходные UNKNOWN остальных имён сохранены.
board = read_csv('local_dated_competitors.csv')
for r in board:
    r['parent_source_row_sha256'] = r['source_row_sha256']
    r['normalization_assumption_id'] = 'A-MRV-NAMES'
    for field, name in [('origin', 'departure_ap_name'), ('destination', 'arrival_ap_name')]:
        if r[field] == 'UNKNOWN' and r[name] == 'Уфа Терминал 1':
            r[field] = 'UFA'
    r['nominal_seats'] = 'UNKNOWN'
    r['open_seats'] = 'UNKNOWN'
    r['physical_adjacent_leg_status'] = 'UNKNOWN'
    r['seat_inventory_usable'] = 'false'
write_csv('dated_competitors_normalized.csv', board)

receipts = {}
source_rows = []
org = {'AZ': 'АО «АЗИМУТ»', 'RW': 'АО «Ред Вингс»', 'S7': 'S7 Technics',
       'FAVT': 'Росавиация', 'MRV_2025': 'АвиаПорт / Финмаркет со ссылкой на аэропорт',
       'MRV_ORDER': 'ФАС России; вторичная публикация правовой базы',
       'MRV_RATES': 'Финмаркет', 'MRV_COMPANY': 'АвиаПорт',
       'KMV_TOURISM': 'Коммерсантъ: интервью с региональным министром туризма',
       'PLAZA': 'Плаза СПА Кисловодск', 'PERM': 'В курсе.ру', 'MINVODY': 'МинводыЭКСПО',
       'KMV_CAPACITY': 'Правительство Ставропольского края', 'MRV_HOME': 'Аэропорт Минеральные Воды'}
pubdates = {'MRV_2025': '2026-01-20', 'FAVT_TERMINAL': '2025-05-14',
            'RW_WINTER': '2026-10-27', 'RW_EVN_MARCH2026': '2026-03-18',
            'RW_MRV_GEORGIA': '2024-10-24', 'PERM_FLOW_2025': '2026-02-02',
            'S7_MRO_RATES_2026': '2026-01 revision', 'MRV_RATES_NEWS': '2025-11-08',
            'KMV_TOURISM_INTERVIEW': '2026-03-27', 'AZ_PROMO_NOV11': '2026-11-11'}
pubdates['AZ_WINTER'] = '2026-07-03'
for f in sorted((ROOT / 'sources').glob('*.receipt.json')):
    d = json.loads(f.read_text())
    sid = d['source_id']
    receipts[sid] = d
    publisher = next((v for k, v in sorted(org.items(), key=lambda x: -len(x[0])) if sid.startswith(k)), 'UNKNOWN')
    rawfile = d.get('raw_file')
    if not rawfile:
        rawfile = next((sid + ext for ext in ['.html', '.pdf'] if (ROOT / 'sources' / (sid + ext)).exists()), '')
    if rawfile and 'sha256' in d:
        assert sha((ROOT / 'sources' / rawfile).read_bytes()) == d['sha256'], sid
    source_rows.append({'source_id': sid, 'url': d['url'], 'organization': publisher,
        'publication_date': pubdates.get(sid, 'UNKNOWN'), 'retrieved_at': d['retrieved_at'],
        'as_of': ASOF, 'period': 'См. evidence.csv; дата страницы не переносится на 2027–2028',
        'unit': 'исходный документ', 'granularity': 'страница/документ/трёхдневное табло',
        'status': 'FETCH_ERROR' if 'error' in d else ('EMPTY_OR_CHALLENGE' if sid in ['MRV_HOME', 'MINVODY_EXPO'] else 'SAVED_DOCUMENT'),
        'coverage': 'Только прочитанный документ; не полная карта рынка/договоров',
        'raw_path': ('sources/' + rawfile) if rawfile else 'UNKNOWN',
        'raw_sha256': d.get('sha256', 'UNKNOWN'), 'receipt_path': 'sources/' + f.name,
        'error': d.get('error', ''), 'current_refresh': '2026-11-12 web open: S7_SERVICES/AZ_ABOUT/RW_WINTER; FAVT TimeoutError' if sid in ['S7_SERVICES', 'AZ_ABOUT', 'RW_WINTER', 'FAVT_TERMINAL'] else 'Сохранённый receipt предыдущего запуска, текущая дата та же'})
write_csv('sources.csv', source_rows)

evidence = []


def fact(eid, sid, claim, period, unit, grain, status, coverage, use, locator, assumption='A-MRV-EVIDENCE'):
    d = receipts[sid]
    evidence.append({'evidence_id': eid, 'source_id': sid, 'url': d['url'],
        'organization': next(r['organization'] for r in source_rows if r['source_id'] == sid),
        'publication_date': pubdates.get(sid, 'UNKNOWN'), 'as_of': ASOF, 'period': period,
        'unit': unit, 'granularity': grain, 'status': status, 'coverage': coverage,
        'claim': claim, 'decision_use': use, 'source_locator': locator,
        'source_raw_sha256': d.get('sha256', 'UNKNOWN'), 'assumption_id': assumption})


fact('MRV-E01', 'S7_SERVICES', 'Провайдер перечисляет линейное и базовое ТО SSJ-100 в MRV.',
     'Страница на 12.11.2026', 'тип × станция ТО', 'MRV; SSJ-100', 'PRIMARY_PROVIDER_OFFER',
     'Нет договора RW, свободных слотов, SLA, запасов и области SJ100/ПД8.', 'Уточняет MRO_provider/type_scope P03; цена базы не обнуляется.', 'S7_SERVICES.txt:281–283')
fact('MRV-E02', 'S7_MRO_RATES_2026', 'Прейскурант: линейное ТО 6790; базовое ТО 6170 рублей за нормочас, без налогов и расходных материалов.',
     'Ревизия январь 2026', 'RUB/нормочас', 'прайс провайдера для резидентов РФ', 'PRIMARY_REFERENCE_PRICE',
     'Не RUB/block-hour, не стоимость формы ТО, не цена RW 2027–2028.', 'P04 должен связать трудоёмкость/календарь/детали; не умножать на лётные часы.', 'S7_MRO_RATES_2026.txt:23–34;43–51', 'A-MRV-MRO')
fact('MRV-E03', 'MRV_ORDER_MIRROR', 'Приказ 777/25 относится к ОАО «Международный аэропорт Минеральные Воды»: в зеркале 520 RUB/т МВМ за взлёт-посадку, 320 RUB/т МВМ безопасность, 1135 RUB/т обеспечение заправки; стоянка после 3 ч — 5% взлёт-посадки за час.',
     'Приказ 08.10.2025; актуальность/счёт RW требует приёмки P04', 'RUB/т МВМ; RUB/т; %/час', 'оператор × услуга', 'SECONDARY_LEGAL_TEXT_NOT_PRIMARY_ACCEPTED',
     'Официальный портал TLS EOF; НДС, база начисления, редакция/льготы и договор не подтверждены.', 'Не смешивать с 778/25; не цена всего оборота.', 'MRV_ORDER_MIRROR.txt:77–159', 'A-MRV-AIRPORT-RATES')
fact('MRV-E04', 'MRV_ORDER_778_LEGALACTS', 'Приказ 778/25 относится к ООО «Кредитинвест»: 2027 безопасность 195, терминал ВВЛ 496/МВЛ 398, пассажир ВВЛ 665/МВЛ 333; 2028 — 203, 515/407, 680/337. Хранение топлива 1500 RUB/т.',
     '2027 и 2028, приложения 3/4 приказа 08.10.2025', 'RUB/пассажир; RUB/т', 'оператор × год × услуга × ВВЛ/МВЛ', 'SECONDARY_LEGAL_TEXT_NOT_PRIMARY_ACCEPTED',
     'Официальный PDF не получен; отдельно установить начисление на transfer/транзит/младенцев и НДС. Это предельные опубликованные ставки, не фактический платёж RW.', 'Запрос P04 на локальную тарификацию; 777 и 778 не альтернативные версии одной услуги.', 'MRV_ORDER_778_LEGALACTS.txt:218–321', 'A-MRV-AIRPORT-RATES')
fact('MRV-E05', 'MRV_RATES_NEWS', 'Ранний tranche относил пассажирские ставки к 777/25 по поисковому указателю. Прочитанное зеркало 778/25 связывает их с ООО «Кредитинвест».',
     'Сопоставление 12.11.2026', 'происхождение ставки', 'два юридических оператора', 'CORRECTION_OF_EARLY_LOCATOR',
     'Старый tranche сохранён; юридическая приёмка чисел не завершена.', 'Использовать E04 как вторичную привязку, а не старый указатель tranche01.', 'usable_tranche_01.json + MRV_ORDER_778_LEGALACTS.txt', 'A-MRV-AIRPORT-RATES')
fact('MRV-E06', 'RW_MRV_GEORGIA', 'RW опубликовала SSJ100 MRV–TBS и MRV–BUS по 2 рейса в неделю после расширения.',
     'Релиз 24.10.2024, историческая программа', 'частота/неделю', 'маршрут RW', 'PRIMARY_HISTORICAL_PUBLICATION',
     'Не текущий календарь и не свободная база.', 'В KEEP не обнулять историческое присутствие RW; уточнить продолжение и продажи.', 'RW_MRV_GEORGIA.txt:основной текст')
fact('MRV-E07', 'RW_EVN_MARCH2026', 'В релизе RW 18.03.2026 MRV перечислен среди городов прямых полётов в EVN; также AER/KUF/GOJ/KZN/CEK.',
     '18.03.2026', 'наличие опубликованного прямого продукта', 'перечень аэропортов/городов', 'PRIMARY_PUBLISHED_ROLE',
     'Без датированной частоты MRV–EVN и без подтверждения зимнего исполнения.', 'Новый MRV–EVN может быть изменением своего продукта; прямые альтернативы RW нельзя считать нулём.', 'RW_EVN_MARCH2026.txt:65–69')
fact('MRV-E08', 'RW_WINTER', 'Релиз зимы RW перечисляет опорные аэропорты KUF/SVX/KZN/AER/MCX и Москва/Санкт-Петербург; MRV в этом перечне отсутствует.',
     '27.10.2026–27.03.2027', 'перечень опорных аэропортов', 'частичный сетевой релиз', 'PRIMARY_INCOMPLETE_ROLE_LIST',
     'Отсутствие в перечне не доказывает отсутствие рейсов/базы/договора; MOW не аэропорт.', 'Новая радиальная база MRV против действующих опорных KUF/SVX; их свободный ресурс всё равно UNKNOWN.', 'RW_WINTER.txt:65–69')
fact('MRV-E09', 'AZ_ABOUT', 'Азимут прямо называет MRV своей базой; опубликован парк 19 SSJ100.',
     'Страница на 12.11.2026; состав на каждую будущую дату неизвестен', 'база; воздушные суда', 'другая авиакомпания, весь парк', 'PRIMARY_COMPETITOR_CONTEXT',
     '19 бортов — не MRV-инвентарь, не 19 доступных бортов, не RW ресурс.', 'Конкурентное преимущество инфраструктуры/расписания — проверяемая альтернатива новой базе RW.', 'AZ_ABOUT.txt:266;275–276')
fact('MRV-E10', 'AZ_BOARD', 'Сохранены 86 записей табло Азимута с MRV; группа 11–13 ноября содержит вылет MRV–KUF 14.11. Даты извлечены из полей рейса, а не имени группы.',
     'Даты записей 11–14.11.2026; группы табло 11–13.11', 'датированная запись рейса', 'один перевозчик, три группы табло', 'PRIMARY_BOARD_SOURCE_EXPORT',
     'План/сообщённый факт; не проверены продажа, кресла и физическая непрерывность. UNKNOWN имена не исправлены догадками.', 'Подтверждает конкурирующие продукты, не полный рынок и не частоты года.', 'dated_competitors_normalized.csv; parent hashes', 'A-MRV-BOARD-DATE')
fact('MRV-E11', 'AZ_WINTER', 'Азимут объявил ранние продажи зимы 2026/27 из MRV, включая UFA/IJK, TBS/IST/ALA/TAS и ряд других городов; промоцены относятся к условиям релиза.',
     'Зима 2026–2027', 'объявление продукта и цена «от»', 'неполный набор направлений', 'PRIMARY_SALES_ANNOUNCEMENT',
     'Цены «от» не датированная корзина с багажом. EVN отдельно доказан табло E10.', 'Нет пустого рынка MRV; точные цены запросить P02 по дате+as_of+lead.', 'AZ_WINTER.txt:268–293')
fact('MRV-E12', 'AZ_MULTIMODAL', 'Азимут публикует сервис Trip&Fly для поиска/оформления составных маршрутов разными видами транспорта.',
     'Страница на 12.11.2026', 'описание сервиса', 'общий сервис конкурента', 'PRIMARY_SERVICE_DESCRIPTION',
     'Не доказан конкретный MRV маршрут, защищённая пересадка RW, сквозной багаж или гарантированное размещение.', 'Сравнивать сервис RW с уже существующими средствами планирования; договор партнёра UNKNOWN.', 'AZ_MULTIMODAL.txt:265–271')
fact('MRV-E13', 'PLAZA_TRANSFER', 'Плаза СПА предлагает встречу в аэропорту MRV и трансфер к санаторию; запрашивает число людей, багаж и детей.',
     'Страница на 12.11.2026', 'наличие услуги', 'один санаторий Кисловодска', 'PRIMARY_SERVICE_OFFER',
     'Нет опубликованной в прочитанном фрагменте цены/гарантированной мощности/договора RW.', 'Наземный участок — самостоятельная услуга и стоимость, а не бесплатная прибавка спроса.', 'PLAZA_TRANSFER.txt:14–29')
fact('MRV-E14', 'MRV_2025', 'Аэропорт сообщил через Интерфакс: 2025 около 4,6 млн пассажирских обслуживаний, −4,6%; международные около 1,2 млн, +8,6%.',
     'Календарный 2025', 'пассажирские обслуживания аэропорта/год', 'весь аэропорт', 'SECONDARY_ATTRIBUTED_AIRPORT_REPORT',
     'Не уникальные туристы, не конечный OD пары, не доля RW, округлённые данные.', 'Опровергает автоматический рост всех рынков из популярности курорта; не знаменатель доли рынка RW России.', 'MRV_2025.txt:18–26')
fact('MRV-E15', 'MRV_2025', 'В сообщении упомянут план реконструкции ВПП в 2026–2028 и международного терминала.',
     'План на 2026–2028, публикация 20.01.2026', 'план инфраструктуры', 'аэропорт', 'SECONDARY_PLAN_NOT_DATED_RESTRICTIONS',
     'Не даты закрытия/слоты/NOTAM и не доказанная потеря выручки.', 'P03 получить AIP/NOTAM/фазы работ; доступность не устанавливать как 100%.', 'MRV_2025.txt:25–26')
fact('MRV-E16', 'FAVT_TERMINAL', 'Росавиация: новый внутренний терминал введён в 2025; площадь 28,5 тыс. м², свыше 3,2 млн пассажиров/год, 1000/час.',
     'Ввод март 2025, публикация 14.05.2025', 'проектная пропускная способность', 'терминал ВВЛ', 'PRIMARY_INFRASTRUCTURE_CONTEXT',
     'Не остаточная мощность в волне, не объём спроса и не подтверждение трансферной технологии. Текущий web open TimeoutError; используется сохранённый HTTP200 receipt.', 'Терминал допускает исследование, не автоматический допуск хаба.', 'FAVT_TERMINAL.txt:145–165')
fact('MRV-E17', 'PERM_FLOW_2025', 'В рейтинге направлений «из Перми» статья указывает 22 579 пассажиров MRV за 2025; сообщённая средняя загрузка линии94,5%.',
     '2025', 'пассажиры линии/год; загрузка %', 'опубликованный рейтинг вылетов из PEE; точную статистическую базу уточнить', 'SECONDARY_ATTRIBUTED_REGIONAL_MINTRANS_CONTEXT',
     'Статья описывает вылеты, поэтому22579 нельзя напрямую сравнивать с both-directions prior. Исходная методика, охват трансфера и месяцы не прочитаны; высокая загрузка не свободный объём RW.', 'Сверить направление/сегменты/OD/охват P05, без собственной коррекции или механического удвоения.', 'PERM_FLOW_2025.txt:71–85')
fact('MRV-E18', 'KMV_TOURISM_INTERVIEW', 'В интервью министра: 8,4 млн посетителей края в 2025 включают 4,1 млн однодневных экскурсантов; санаторный сектор — отдельный сегмент.',
     '2025, интервью 27.03.2026', 'уникальные посетители края/год', 'Ставропольский край, не MRV OD', 'ATTRIBUTED_PRIMARY_INTERVIEW',
     'Нельзя умножать всех посетителей на авиадолю и добавлять к уже учтённому OD; сезон/цель/платёжеспособность отдельных пар неизвестны.', 'Основание теста санаторного календаря, не оценка проданных кресел.', 'KMV_TOURISM_page38.txt:8–12;28–38')
fact('MRV-E19', 'KMV_TOURISM_INTERVIEW', 'На соседней странице участники санаторного рынка описывают спрос за пределами одного пика.',
     'Интервью/комментарии март 2026', 'качественное описание сезонности', 'выборка участников санаторного рынка', 'QUALITATIVE_COUNTEREVIDENCE_TO_SUMMER_ONLY',
     'Нет месячных OD, загрузки всех санаториев или гарантированных контрактных блоков RW.', 'Не навязывать летнюю сезонность; тестировать зимние и межсезонные заезды через P05.', 'KMV_TOURISM_page40.txt:52–73')
for sid in ['MRV_ORDER_777_OFFICIAL', 'MRV_ORDER_777_SCAN', 'MRV_ORDER_778_SCAN', 'KMV_CAPACITY', 'MINVODY_EXPO']:
    fact('MRV-ACCESS-' + sid, sid, receipts[sid].get('error', 'Текст EMPTY_OR_CHALLENGE; содержательная информация не извлечена.'),
         'Попытка 12.11.2026', 'результат доступа', 'один URL', 'ACCESS_LIMITATION',
         'Ошибка доступа не опровергает существование услуги, нормы или рынка.', 'Сохранить точную ошибку; поиск/официальная приёмка следующему владельцу.', 'sources/' + sid + '.receipt.json')
write_csv('evidence.csv', evidence)

# Предыдущие выводы сохраняются как история; новые формулировки — отдельные гипотезы.
assumptions = []


def assumption(aid, value, unit, basis, bounds, impact, sensitivity, refine):
    assumptions.append({'assumption_id': aid, 'value': value, 'unit': unit,
        'selected_by': 'Исследователь MRV Sol6.1 xhigh; не решение команды/не согласие RW',
        'why': basis, 'range_or_unknown': bounds, 'approval_status': 'RESEARCH_DESIGN_ONLY_NOT_RW_ADMISSION',
        'affected_conclusions': impact, 'sensitivity': sensitivity, 'refinement': refine,
        'confidence_interval': 'Нет; проектные альтернативы/стресс-точки не доверительные интервалы'})


assumption('A-MRV-EVIDENCE', 'История/публикация/план/предложение разделены', 'статус источника', 'Прямые границы доказательства каждого документа.', 'UNKNOWN текущая полнота рынка', 'Все гипотезы', 'Новый первичный документ меняет только затронутую строку', 'P02/P03/P04 актуальные датированные источники')
assumption('A-MRV-NAMES', 'Уфа Терминал 1 → UFA; остальные прежние UNKNOWN сохранены', 'ключ аэропорта', 'Однозначное имя Уфы в табло; не исправлять IAR/IWA догадкой.', 'Неоднозначные имена UNKNOWN', 'Локальное покрытие конкурентов', 'Проверить исходный текст/справочник', 'P02 нормализация юридического/аэропортового ключа')
assumption('A-MRV-BOARD-DATE', 'Дата из поля вылета/прилёта; год 2026 по as_of', 'дата рейса', 'Группа табло содержит пересечение календарной границы; MRV–KUF вылет 14.11.', 'Истинная дата при отсутствии day/month UNKNOWN', 'Стыковка, частота и block-time', 'Не назначать всем строкам дату группы', 'Полный датированный календарь P02')
assumption('A-MRV-R2', 2, 'условных физических борта, каждый count=1', 'Минимальный исследуемый двухпоточный бюджет для сравнения восьми пар; не оценка свободного парка.', 'Ветки 0, 1, 2; реальный свободный ресурс UNKNOWN', 'Допуск R8/H8/E8/M8/P8/X8', 'Один борт → R4/E4; ноль → KEEP и контрактный доступ без новых рейсов', 'P03 tail IDs, прежние задания, crews/ТО/reserve и альтернативное применение')
assumption('A-MRV-R1', 1, 'условный борт', 'Промежуточная малая программа при частичной доступности.', 'Ветки 0/1/2 не прогноз', 'R4/E4', 'Сравнить вариант не запускать и иной KEEP', 'P03 тот же реальный ресурс и полный affected KEEP')
assumption('A-MRV-CABIN', 100, 'номинальных кресел/проектный рейс', 'P03 RRJ95 family page даёт 100; используем один аналог для равного сравнения.', 'Tail cabin/blocked/saleable и SJ100/ПД8 UNKNOWN', 'Только номинальная ёмкость шаблонов', 'P06 заменить фактическими saleable seats; не считать 100 открытыми местами', 'P03 точная кабина/загрузка/ограничения по каждому tail')
assumption('A-MRV-TURN', 60, 'минут наземного оборота', 'Один RT на борт в день; условная проектная пауза для P03, не норматив аэропорта.', 'Допустимый фактический минимум UNKNOWN; проверить 45/60/90/120 как варианты', 'Ротации, затраты и удобство', 'Поменять общий параметр одновременно во всех сравниваемых программах', 'P03 handling/ТО/заправка/багаж/crew по станции и типу')
assumption('A-MRV-MCT', 90, 'минут между рейсами', 'Исследовательское окно; не опубликованный MCT RW MRV.', 'Approved domestic/international MCT UNKNOWN; стресс 60/90/120/180 минут', 'Хабовые продукты пока непродаваемы', 'Сравнить хаб без пересадок и пересчитать точные возвраты', 'Аэропорт+RW договор, багаж, погранконтроль и recovery')
assumption('A-MRV-HUB-PERIOD', 'H8A/XH8A: во второй неделе обменять утренние/поздние spokes между T1/T2', '14-дневный период расписания', 'Первый фиксированный H8 имеет возврат6/8 ночей; отдельный исправленный дизайн проверяет7 ночей при тех же рейсах/частотах/ресурсе.', 'Продаваемость/реальный MCT UNKNOWN; 10/14 ночей отдельно', 'Полезность пересадки зависит от полного возврата; улучшение одного календаря не доказывает экономику', 'Повторить exact return и local departure preference в P05/P06', 'P03 датированный календарь, P05 disjoint date cohorts и реальный санаторный заезд')
assumption('A-MRV-DAILY', 8, 'block-hours/борт/сутки планировочный предел', 'Проектное ограничение: один RT по выбранным плечам; не AFM/crew certification.', 'Фактический предел смены/налёта UNKNOWN', 'Только локальная календарная проверка', 'Проверить полную duty с positioning/briefing; crew ≠ tail', 'P03 утверждённый roster и нормативы')
assumption('A-MRV-RESERVE', 'Воскресенье без проектных рейсов; отдельный резерв и ТО UNKNOWN', 'планировочный календарь', 'Оставить окно; отсутствие назначений не равно доступному резерву.', 'Число резервных бортов/SLA/длительность ТО UNKNOWN', 'Dispatch/funding не приняты', 'AOG в полётный день; возврат экипажа; отсутствие заменяющего борта', 'P03 реальный резерв/ТО; P04 цена recovery и задержек')
assumption('A-MRV-FREQUENCY', 'R8: KUF/GOJ/PEE/CEK 2 RT/нед; UFA/KZN/SVX/OMS 1; R4: KUF/GOJ 2, PEE/CEK 1', 'RT/неделю в шаблоне', 'Ресурсный дизайн из доказанных/проверяемых рынков. Не получен из измеренного неудовлетворённого спроса.', 'Выборочная ступень, не оптимум и не прогноз частот', '8 уникальных пар в полном дизайне; 4 в дефицитной ступени', 'P05 месячные продажи и response; 7/10/14 ночей; сокращение без выдуманного экономического отказа', 'P02 полный рынок, P05 выбор, P06 совместная программа')
assumption('A-MRV-SEASONS', 'Два 14-дневных окна на каждый сезонный тип в 2027/2028; месяцы маски календаря', 'даты и месяцы', 'Покрыть зиму/межсезонье/лето, не годовое умножение недели.', 'Месячная частота/дни спроса UNKNOWN', 'Никаких годовых пассажиров/денег из этих шаблонов', 'Stage B развернуть все даты 24 месяцев, учесть праздники/заезды', 'P05 местная сезонность и реальные турпакеты; P03 полный календарь')
assumption('A-MRV-DELIVERY', 'N(t) 0/1/2, даты transfer и entry раздельно', 'борта × дата', 'Два борта — размер сравниваемого дизайна. H2 2027 — граница задания; выбранные месяцы лишь сценарные проверки.', 'Фактический график Red Wings UNKNOWN; лаг ввода 31 день — иллюстративная точка, не подтверждённый срок', 'Различать staged/partial/delay/zero; SSJ без новых SJ отдельная ветвь', 'Сдвиги entry и отсутствующий второй борт; лаг ввода уточнить отдельно', 'P03 поставщик+RW: передача/подготовка/готовность/свободный ресурс')
assumption('A-MRV-KEEP', 'Будущий KEEP всех затронутых продаж и заданий; суммы UNKNOWN', 'affected business 2027–2028', 'RW уже публиковала MRV–EVN/TBS/BUS и прямые международные рейсы из KUF/GOJ/KZN/CEK.', 'Хвосты/датированные продукты/committed_sales/net contribution UNKNOWN', 'Нельзя принять net-new сегменты/долю рынка/полный добавочный результат', 'Пересчёт своих AER/MCX/MRV/EVN продуктов, donor и rebooking', 'P03/P05 прежние задания и продажи; P06 одна общая аллокация')
assumption('A-MRV-P05', 'P05 a63a047 без собственной замены коэффициентов', 'общая сценарная модель', 'Одна система спроса и выбора; prior не observed endpoint OD.', 'P05 base/cautious не CI; own-migration UNKNOWN', 'Все экономические/рыночные выводы только Stage B', 'Локальный PEE/KUF scale check + альтернативная сезонность через владельца P05', 'P05 endpoint basis, holdout и согласованный driver contract P06final')
assumption('A-MRV-MRO', '6790/6170 reference RUB/нормочас 2026', 'цена нормочаса', 'Первичный S7 прайс; формы по картам оператора, расходы на материалы отдельно.', 'Фактическая будущая ставка, трудоёмкость, слот и SJ100/ПД8 UNKNOWN', 'Потолок допустимого пакета ТО; не экономия базы по умолчанию', 'Расценка × labour-hours + parts + calendar + SLA; не block-hours', 'P04/P03 договор RW и capability конкретного варианта')
assumption('A-MRV-AIRPORT-RATES', '777/25 и 778/25 раздельно, вторичные тексты', 'ставка × оператор × услуга × год', 'Официальный TLS fail сохранён; зеркала — направление проверки, не подтверждённый счёт.', 'НДС/льготы/начисление/редакция/договор UNKNOWN', 'Нельзя обнулить тарифы или автоматически получить хабовую льготу', 'P04 отдельные сценарии transfer/terminal billing без двойной услуги', 'Официальный приказ, прейскурант, SGHA и invoices RW')
assumption('A-MRV-PARTNER', 'Защита стыковки/блок мест/трансфер только при явном контракте', 'пассажирский продукт/кресла', 'Предложения Trip&Fly/санатория не подтверждают контракт RW.', 'Квота/цена/release_unused/recovery/cash UNKNOWN', 'P8/G0 условны; партнёрские кресла не новые физические места', 'Без контракта → R8; без квоты → текущее предложение в outside P05', 'P02/P05 договор, inventory binding, оплачиваемый покупатель и даты')
assumption('A-MRV-THRESHOLD', 'TH-OPTION/TH-FIXED/TH-LAUNCH/TH-FARE/TH-FUNDING из P04', 'порог в соответствующих единицах', 'Нет обоснованного локального общего бюджета; показывать совместный остаток после остальных затрат.', 'Численный порог UNKNOWN до accepted P05/P03/P04', 'Нет выдуманной прибыли/окупаемости; допускается убыточная ступень с финансированием и механизмом улучшения', 'Изменение тарифа требует повторного choice; неизвестные нельзя одновременно ставить в отдельные максимумы', 'P06 полный проект–KEEP, cash до и после запуска; решение команды о финансировании')

# Block-time — сценарный аналог наблюдённого расписания; не параметры SJ100/ПД8.
blocks = {'KUF': (165, 'P02 160/165; AZ_BOARD outbound155', '155–165 наблюдённые точки, не эксплуатационные границы'),
          'GOJ': (205, 'P02 N4 185/205; FIVE GOJ 205', '185–205 опубликованные точки, не будущий интервал'),
          'PEE': (215, 'AZ_BOARD-flight-109 MRV01:20–PEE06:55, UTC+3/+5', '215 один outbound; обратное/будущее UNKNOWN'),
          'CEK': (195, 'AZ_BOARD-flight-003/107:195/190', '190–195 outbound, не будущее ограничение'),
          'UFA': (210, 'P02 месячные опубликованные времена 135…210; исторический контекст ноябрь 200–210', 'Сохранённый разброс требует date-specific проверки; не CI'),
          'KZN': (205, 'Геометрия P05 1340 км близка GOJ1336; взят GOJ205 как явный аналог', 'Реальный KZN block UNKNOWN; не применять геометрический аналог как admission'),
          'SVX': (215, 'P02 опубликованные 195/200/210/215', '195–215 точки разных дат; не гарантия будущей трассы'),
          'OMS': (225, 'AZ_BOARD-flight-108 MRV01:15–OMS08:00 UTC+3/+6', '225 один outbound; запас/трасса/полезная нагрузка UNKNOWN'),
          'TBS': (75, 'AZ_BOARD-flight-023 75 и flight-128 40', '40/75 конфликтующие периоды/трассы; выбран75, требуется сверка'),
          'EVN': (90, 'AZ_BOARD MRV–EVN70/80/90', '70–90 опубликованные точки, не SJ100/ПД8 предел')}
for airport, (minutes, basis, bounds) in blocks.items():
    assumption('A-MRV-BLOCK-' + airport, minutes, 'минут/плечо в обе стороны шаблона', basis + '; симметрия — проектный аналог, не факт.', bounds,
               'Ресурс/стыковки/driver block_hours только условны', 'P03 заменить каждым направлением/датой/типом, проверить дальность и нагрузку', 'P02 расписание; P03 route dispatch и fuel; SJ100/ПД8 отдельно')
write_csv('assumptions.csv', assumptions)

patterns = {
    'R8': [('T1', 0, ['MRV','KUF','MRV']), ('T2', 0, ['MRV','GOJ','MRV']),
           ('T1', 1, ['MRV','GOJ','MRV']), ('T2', 1, ['MRV','KUF','MRV']),
           ('T1', 2, ['MRV','PEE','MRV']), ('T2', 2, ['MRV','CEK','MRV']),
           ('T1', 3, ['MRV','CEK','MRV']), ('T2', 3, ['MRV','PEE','MRV']),
           ('T1', 4, ['MRV','UFA','MRV']), ('T2', 4, ['MRV','SVX','MRV']),
           ('T1', 5, ['MRV','KZN','MRV']), ('T2', 5, ['MRV','OMS','MRV'])],
    'R4': [('T1', i, ['MRV', a, 'MRV']) for i, a in enumerate(['KUF','GOJ','PEE','KUF','GOJ','CEK'])],
    'E8': [('T1', i, route) for i, route in enumerate([
        ['KUF','MRV','GOJ'],['GOJ','MRV','KUF'],['KUF','MRV','UFA'],['UFA','MRV','KUF'],['KUF','MRV','KZN'],['KZN','MRV','KUF']])]
        + [('T2', i, route) for i, route in enumerate([
        ['SVX','MRV','PEE'],['PEE','MRV','SVX'],['SVX','MRV','CEK'],['CEK','MRV','SVX'],['SVX','MRV','OMS'],['OMS','MRV','SVX']])],
    'E4': [('T1', i, route) for i, route in enumerate([
        ['KUF','MRV','GOJ'],['GOJ','MRV','KUF'],['KUF','MRV','PEE'],['PEE','MRV','KUF'],['KUF','MRV','CEK'],['CEK','MRV','KUF']])],
}
patterns['M8'] = [('T1', i, ['MRV', a, 'MRV']) for i, a in enumerate(['KUF','GOJ','UFA','KUF','GOJ','KZN'])] + [r for r in patterns['E8'] if r[0]=='T2']
patterns['H8'] = patterns['R8']
patterns['H8A'] = patterns['R8']
patterns['P8'] = patterns['R8']
patterns['XR8'] = [(t, d, ['TBS' if a=='UFA' else 'EVN' if a=='KZN' else a for a in route]) for t,d,route in patterns['R8']]
patterns['XH8'] = patterns['XR8']
patterns['XH8A'] = patterns['XR8']
programmes = []
specs = [
 ('R8','RADIAL_BASE','Новая радиальная база MRV: восемь внутренних пар','BUDGET2','MRV-H8;MRV-E8;MRV-M8','Местный курортный/VFR спрос без обязательной пересадки'),
 ('H8','TRANSFER_HUB','Та же сеть MRV с условными пересадочными окнами','BUDGET2','MRV-R8','Чистый эффект времени и защиты стыковки при тех же рейсах; не обещание удобного возврата'),
 ('H8A','TRANSFER_HUB_CALENDAR_REVISION','Та же сеть MRV с чередованием окон через неделю','BUDGET2','MRV-R8;MRV-H8','Отдельный проектный ответ на возврат6/8 ночей в H8: проверить7 ночей без добавления кресел'),
 ('E8','EXISTING_BASE_DIRECT','Цепочки KUF/SVX через MRV с ночёвкой на конечной станции','BUDGET2','MRV-R8;MRV-M8','Сравнить затраты базы MRV с дополнительными позиционированием/ночёвками и неравными частотами'),
 ('M8','MIXED','Один борт в MRV и один в цепочках SVX','BUDGET2','MRV-R8;MRV-E8','Частичное базирование при общей конкуренции за кресла/спрос'),
 ('R4','RADIAL_BASE','Малая радиальная ступень MRV: четыре пары','BUDGET1','MRV-E4','Частичная доступность одного борта; не выдавать за полную целевую сеть'),
 ('E4','EXISTING_BASE_DIRECT','Малая ступень через KUF без базы MRV','BUDGET1','MRV-R4','Альтернатива новой базе на том же одном борту'),
 ('P8','PARTNER_FEEDER','R8 с санаторным подвозом и отдельно условным партнёрским продуктом','BUDGET2','MRV-R8','Тот же физический RW календарь; продаваемый пакет только с договором и квотой'),
 ('XR8','EXTENDED_RADIAL','Восемь пар: шесть внутренних и TBS/EVN как конечные продукты','BUDGET2','MRV-XH8','Дополнительная международная ветвь без новых Ту-214'),
 ('XH8','EXTENDED_TRANSFER','Та же международная сеть с условной мини-волной','BUDGET2','MRV-XR8','Сопоставить пересадки с собственными прямыми EVN/TBS и действующим Азимутом'),
 ('XH8A','EXTENDED_TRANSFER_CALENDAR_REVISION','Международная сеть с чередованием окон через неделю','BUDGET2','MRV-XR8;MRV-XH8','Та же физическая сеть; отдельная проверка7-ночного возврата вместо признания любого окна продуктом')]
for pid, family, title, budget, controls, mechanism in specs:
    pattern = patterns[pid]
    legs = [(a,b) for _,_,route in pattern for a,b in zip(route,route[1:])]
    counts = Counter(tuple(sorted((a,b))) for a,b in legs)
    legs_week = len(legs)
    bh = sum(blocks[b if a=='MRV' else a][0] for a,b in legs) / 60
    programmes.append({'programme_id':'MRV-'+pid, 'version':'stage_a_v1', 'title':title,
        'family':family, 'scope':'EXTENDED_INTERNATIONAL' if pid.startswith('X') else 'CASE_SJ_DOMESTIC',
        'mechanism':mechanism, 'paired_controls':controls.split(';'), 'resource_budget_id':budget,
        'conditional_physical_tails':1 if budget=='BUDGET1' else 2, 'new_tu214':0,
        'aircraft_variants_separate':['RRJ95B_or_RRJ95LR_100_exact_tail_REQUIRED','SJ100_PD8_SEPARATE_ANALOGUE_NOT_DISPATCH_ADMITTED'],
        'unique_airport_pairs':[list(k) for k in sorted(counts)], 'unique_pair_count':len(counts),
        'weekly_pattern_leg_count':legs_week, 'weekly_pattern_block_hours_analogue':round(bh,4),
        'frequency_each_way_per_pattern_week':{'-'.join(k):v/2 for k,v in sorted(counts.items())},
        'pattern': [{'tail_role':t,'weekday_iso':d+1,'airports':route} for t,d,route in pattern],
        'pattern_period_days':14 if pid in ['H8A','XH8A'] else 7,
        'second_week_rule':'Обменять маршруты T1/T2 каждого дня, оставив T1 ранним, T2 поздним' if pid in ['H8A','XH8A'] else 'Повторить первую неделю',
        'dated_templates':'dated_flight_templates.csv: programme_id',
        'monthly_applicability':'monthly_stage_requests.csv: programme_id; not a full admitted flight calendar',
        'keep':'MRV-KEEP; unchanged products retained; affected scope and exact flight IDs require P03/P05',
        'before_after':'market_deltas.csv: programme_id; add vs replace cannot be decided from an incomplete timetable',
        'base_and_crew':'MRV new base costs for R8/H8/H8A/R4/P8/XR8/XH8/XH8A; M8 mixed; E8/E4 KUF/SVX plus spoke overnights; actual contracts/crew UNKNOWN',
        'counterevidence':'Хаб на редких частотах может не дать 7/10/14 ночей; MRV геометрически удлиняет часть северо-северных поездок. Действующие прямые продукты и свои продажи сохраняются.',
        'cost_test':'P04 TH-OPTION and joint base/launch/MRO/turn/recovery cost boundary; no stand-alone money/choice calculation',
        'status':'STAGE_A_SPECIFIED_STAGE_B_CONDITIONAL', 'economic_result':None,
        'demand_allocation':None, 'dispatch_admission':None,
        'assumption_ids':['A-MRV-R1' if budget=='BUDGET1' else 'A-MRV-R2','A-MRV-CABIN','A-MRV-TURN','A-MRV-FREQUENCY','A-MRV-SEASONS','A-MRV-KEEP','A-MRV-P05','A-MRV-RESERVE'] + (['A-MRV-MCT'] if pid in ['H8','H8A','XH8','XH8A','P8'] else []) + (['A-MRV-HUB-PERIOD'] if pid in ['H8A','XH8A'] else [])})
programmes += [
 {'programme_id':'MRV-KEEP','version':'stage_a_v1','family':'KEEP','title':'Будущая затронутая сеть без проекта при том же ресурсе',
  'status':'REQUIRED_UNBOUND_FUTURE_KEEP','dated_physical_flights':None,'affected_existing_sales':None,'new_tu214':0,
  'preserve_evidence_ids':['MRV-E06','MRV-E07','MRV-E08'],'assumption_ids':['A-MRV-KEEP'],
  'rule':'Не пустая сеть. При существующем SSJ указать donor; при новом SJ сравнить альтернативное применение без выдуманного донора.'},
 {'programme_id':'MRV-G0','version':'stage_a_v1','family':'PARTNER_OR_GROUND_ACCESS','title':'Доступ к КМВ через текущее предложение и договорный подвоз без новых рейсов RW',
  'status':'CONTRACT_AND_INVENTORY_CONDITIONAL','incremental_rw_flights':0,'incremental_rw_physical_tails':0,
  'available_common_budget':'BUDGET0/1/2; неиспользуемые проектом борта сохраняют альтернативное применение KEEP',
  'pair_with':'MRV-P8; общая доступность ресурса и полное альтернативное применение сохраняются',
  'gross_journeys':None,'rw_incremental_segments':None,'contract_terms':None,'new_tu214':0,
  'rule':'Партнёрские маркетинговые коды не добавляют физические кресла; защищённость/продажи/выручка RW требуют договора.',
  'assumption_ids':['A-MRV-PARTNER','A-MRV-KEEP']}]
write_json('programme_candidates.json', {'version':'MRV-stage_a-v1','programmes':programmes,
    'comparison_key':['fleet_scope_id','delivery_calendar_id','external_scenario_id','period','input_version','affected_scope_id'],
    'equal_resource_rule':'Одинаковые физические tail IDs, готовность, начальная локация, доступность, crew/ТО/reserve и капитал. Использование может различаться; ferry/ночёвка/прежние задания/свои продажи входят в P/KEEP. Не требуется равенство выдуманной прибыли или налёта.',
    'selection_rule':'Нет общего балла/победителя. Stage B сравнивает пассажиров, доход, полный добавочный результат, финансирование и устойчивость; убыточная ступень допустима при расчётной траектории и условиях остановки.'})

months = [f'{y}-{m:02}' for y in [2027,2028] for m in range(1,13)]
delivery = {
 'SJ_PHASED': [('N1','2027-07-01','2027-08-01'),('N2','2027-10-01','2027-11-01')],
 'SJ_PARTIAL': [('N1','2027-10-01','2027-11-01')],
 'SJ_DELAY': [('N1','2028-04-01','2028-05-01'),('N2','2028-07-01','2028-08-01')],
 'SJ_ZERO': []}
delivery_rows=[]
for sid, tails in delivery.items():
    for month in months:
        month_end = date(int(month[:4])+(month[5:]=='12'), int(month[5:])%12+1,1)-timedelta(days=1)
        delivery_rows.append({'scenario_id':sid,'month':month,'aircraft_variant':'SJ100_PD8',
            'transferred_by_month_end':sum(date.fromisoformat(t)<=month_end for _,t,_ in tails),
            'commercial_ready_assumed_by_month_end':sum(date.fromisoformat(e)<=month_end for _,_,e in tails),
            'free_for_project':'UNKNOWN','events':json.dumps(tails,ensure_ascii=False),
            'assumption_id':'A-MRV-DELIVERY','status':'RESEARCH_SCENARIO_NOT_RW_DELIVERY_FORECAST'})
write_csv('delivery_scenarios.csv',delivery_rows)
monthly=[]
for p in programmes:
    if p['programme_id'] in ['MRV-KEEP','MRV-G0']: continue
    for month in months:
        m=int(month[-2:]); season='winter' if m in [12,1,2] else 'summer' if m in [6,7,8,9] else 'shoulder'
        monthly.append({'programme_id':p['programme_id'],'month':month,'season':season,
            'resource_budget_id':p['resource_budget_id'],'SSJ_existing_resource':'UNKNOWN: P03 donor and KEEP required',
            'SJ_delivery_gate':'SJ_PHASED/PARTIAL/DELAY/ZERO from delivery_scenarios.csv; transferred != ready != free',
            'full_flight_calendar':'UNKNOWN_NOT_EXPANDED_FOR_ANNUAL_CLAIMS',
            'frequency_and_sale_dates':'Паттерн — начальная гипотеза; месячный спрос/заезды/слоты должны выбрать даты',
            'assumption_id':'A-MRV-SEASONS;A-MRV-DELIVERY;A-MRV-FREQUENCY'})
write_csv('monthly_stage_requests.csv',monthly)

windows = [('2027-W','2027-02-01','winter'),('2027-SH','2027-05-03','shoulder'),('2027-S','2027-08-02','summer'),
           ('2028-W','2028-02-07','winter'),('2028-SH','2028-05-01','shoulder'),('2028-S','2028-08-07','summer')]
flights=[]
for p in programmes:
    pid=p['programme_id'].removeprefix('MRV-')
    if pid not in patterns: continue
    for wid, start, season in windows:
        for week in range(2):
            active_pattern=patterns[pid]
            if pid in ['H8A','XH8A'] and week==1:
                active_pattern=[(t,d,next(rt for tt,dd,rt in patterns[pid] if dd==d and tt!=t)) for t,d,_ in patterns[pid]]
            for tail, weekday, route in active_pattern:
                day=date.fromisoformat(start)+timedelta(days=week*7+weekday)
                dep=datetime.combine(day,datetime.min.time())+timedelta(hours=5)
                # Один направленный connection window: ранний RT T1, поздний RT T2.
                # Его слабый возвратный календарь регистрируется, а не скрывается.
                if pid in ['H8','H8A','XH8','XH8A'] and tail=='T1': dep-=timedelta(hours=1)
                if pid in ['H8','H8A','XH8','XH8A'] and tail=='T2':
                    early=next(rt for tt,dd,rt in active_pattern if tt=='T1' and dd==weekday)
                    early_block=blocks[early[1]][0]
                    dep=datetime.combine(day,datetime.min.time())+timedelta(hours=4,minutes=2*early_block+60+90)
                for k,(a,b) in enumerate(zip(route,route[1:]),1):
                    spoke=b if a=='MRV' else a
                    arr=dep+timedelta(minutes=blocks[spoke][0])
                    flights.append({'flight_template_id':f'MRV-{pid}:{wid}:{day}:{tail}:{k}',
                        'programme_id':'MRV-'+pid,'window_id':wid,'season':season,'tail_role':tail,
                        'origin_airport':a,'destination_airport':b,'departure_utc':dep.isoformat()+'Z',
                        'arrival_utc':arr.isoformat()+'Z','block_minutes_analogue':blocks[spoke][0],
                        'aircraft_variant':'RRJ95_100_SCENARIO_ANALOGUE_NOT_EXACT_TAIL','nominal_seats':100,
                        'saleable_seats':'UNKNOWN','physical_adjacent_leg':True,
                        'status':'PROPOSED_DATED_TEMPLATE_NOT_PUBLISHED_NOT_DISPATCH_ADMITTED',
                        'SJ100_PD8_use':'Separate dispatch/fuel/seats/capability required; not actual SJ flight',
                        'assumption_ids':'A-MRV-CABIN;A-MRV-TURN;A-MRV-SEASONS;A-MRV-BLOCK-'+spoke})
                    dep=arr+timedelta(minutes=60)
write_csv('dated_flight_templates.csv',flights)

# Явный before/after каждой программы. Численная дельта UNKNOWN, существующие продажи не нули.
deltas=[]
for p in programmes:
    if 'unique_airport_pairs' not in p: continue
    for a,b in p['unique_airport_pairs']:
        other=b if a=='MRV' else a
        source_products=[r for r in read_csv('inputs/P02_competitor_products_MRV.csv') if {r['origin'],r['destination']}=={a,b}]
        local=[r for r in board if {r['origin'],r['destination']}=={a,b}]
        carriers=sorted(set(r['carrier'] for r in source_products)|({'A4'} if local else set()))
        own='RW исторический/публикуемый продукт; текущие даты и продажи UNKNOWN' if other in ['TBS','EVN'] else 'RW прямой/стыковочный affected KEEP UNKNOWN; отсутствие строки не отсутствие продукта'
        deltas.append({'programme_id':p['programme_id'],'origin_airport':a,'destination_airport':b,
            'before_period':'2027–2028 same-scenario KEEP; observed2025/published2026 context only',
            'before_RW':own,'before_competitors':';'.join(carriers) or 'UNKNOWN_COMPLETE_LIST',
            'P02_source_product_ids':';'.join(r['product_id'] for r in source_products),
            'P02_source_row_hashes':';'.join(r['source_row_sha256'] for r in source_products),
            'new_local_source_row_ids':';'.join(r['source_row_id'] for r in local),
            'new_local_source_row_hashes':';'.join(r['parent_source_row_sha256'] for r in local),
            'after_action':'PROPOSED_ADD_OR_RETIME_OR_REPLACE_PENDING_KEEP_BINDING',
            'after_frequency_each_way_pattern':p['frequency_each_way_per_pattern_week']['-'.join((a,b))],
            'preserve':'KEEP products and committed_sales retained unless exact action+rebooking accepted',
            'reduce_or_shift':'UNKNOWN exact existing flight IDs; no authorised silent deletion',
            'donor_or_alternative_use':'Existing SSJ: donor required; new SJ: alternative new resource use, no fictional donor',
            'net_new_journeys':'UNKNOWN','net_new_RW_segments':'UNKNOWN','net_revenue_delta_RUB':'UNKNOWN',
            'competitive_response':'P05 response policy + complete date-specific competitor products; response not zero',
            'coverage':'source_export_incomplete_not_physical_seat_admission','assumption_ids':'A-MRV-KEEP;A-MRV-P05;A-MRV-FREQUENCY'})
write_csv('market_deltas.csv',deltas)

hypotheses=[]
hs=[
 ('H01',['C16','C03'],'MRV-E14;MRV-E17;MRV-E18','Местные поездки КМВ поддерживают малую прямую программу, а новая база может окупить свой дополнительный расход только при достаточном net contribution.','R4/E4 и R8/E8/M8 на общем ресурсе; P04 TH-OPTION.','Существующий Азимут/свои рейсы обслуживают спрос; прирост RW может быть перетоком без роста общего рынка.','OBSERVED_SIGNAL_TO_CONDITIONAL_TEST'),
 ('H02',['C01','C29'],'MRV-E09;MRV-E10','Синхронизация тех же восьми внутренних пар улучшит часть поездок через MRV достаточно для расходов на стыковку.','H8/H8A против R8; исходный контрпример6/8ночей и отдельный14-дневный паттерн с7-ночным возвратом; P05 reassignment.','Редкая недельная частота и южный крюк делают хаб хуже прямых или существующих узлов.','CONDITIONAL_WITH_RETURN_CALENDAR_COUNTEREXAMPLE_AND_REVISION'),
 ('H03',['C15','C14'],'MRV-E13;MRV-E17;MRV-E18;MRV-E19','Санаторный календарь и подвоз увеличат ценность поездки при той же физической ёмкости RW.','P8 против R8 и G0: одинаковые рейсы, контрактная цена/квота/заезды и платёжный календарь.','Спрос уже летает конкурентами/ездит поездом; услуга увеличивает стоимость, а не net-new спрос.','CONTRACT_CONDITIONAL'),
 ('H04',['C06','C33'],'MRV-E07;MRV-E08','Развитие через KUF/SVX может дать лучший полный результат за счёт существующей инфраструктуры даже с ночёвками вне базы.','E8/M8 против R8 при одинаковых tail IDs и первоначальной локации; ferry и crew overnight включить.','Экономия базы меньше потерь качества, своего revenue и логистики ночёвок.','CONDITIONAL_AFFECTED_KEEP_REQUIRED'),
 ('H05',['C31'],'MRV-E01;MRV-E02','Публичное ТО SSJ100 в MRV уменьшает один барьер запуска по сравнению с отсутствием провайдера.','P03 capability/слот/SLA+P04 формы/нормочасы; отдельно RRJ95 и SJ100/ПД8.','Предложение недоступно RW или не покрывает вариант/части/слоты; новый SJ имеет иной ремонтный контур.','PARTIAL_TECHNICAL_EVIDENCE_NOT_ECONOMIC_ADMISSION'),
 ('H06',['C08','C33'],'MRV-E06;MRV-E07;MRV-E10','Международная мини-волна MRV может быть полезна отдельным OD при худших прямых альтернативах.','XH8 против XR8 и собственных прямых KUF/GOJ/KZN/CEK–EVN/TBS; P02I, rights, MCT, P05 international.','RW и Азимут уже имеют прямые продукты; MRV теряет собственные продажи и добавляет плечо.','INTERNATIONAL_STAGE_B_SEPARATE_NO_NEW_TU214'),
 ('H07',['C31'],'MRV-E15','Поэтапный запуск R4/E4 затем R8/E8/M8 устойчивее полного обязательства на два борта при частичной/поздней поставке.','Одинаковая N(t) у всех программ, fixed и feasible adaptive; сохранять ранние обязательства и sold journeys.','Стоимость малого запуска и последующей смены базы превышает ценность ожидания.','CONDITIONAL_DELIVERY_AND_FINANCING'),
 ('H08',['C29'],'MRV-E10;MRV-E12','Партнёрский/наземный доступ без новых рейсов RW может оказаться рациональнее при нуле новых бортов.','G0 против сохранения текущих отдельных услуг; paid block/продажи RW/защита/выручка по договору.','Партнёр не отдаёт места/маржу; единый заказ уже существует у конкурента.','CONTRACT_CONDITIONAL_NOT_FREE_FEED')]
for hid, parents, ev, claim, test, counter, status in hs:
    hypotheses.append({'hypothesis_id':'MRV-'+hid,'version':1,'parent_ids':parents,
        'city_or_markets':'MRV; см. programme_candidates.json','observed_signal_and_source_ids':ev.split(';'),
        'claim_and_mechanism':claim,'counterfactual':'MRV-KEEP и указанные парные программы на том же ресурсе',
        'competing_explanation':counter,'distinguishing_test':test,
        'critical_unknowns_and_assumption_ids':['A-MRV-KEEP','A-MRV-P05','A-MRV-RESERVE','A-MRV-THRESHOLD'],
        'owner_task_id':'MRV/research_v1','input_versions':pins['pins'],'status':status,
        'result_scope':'Stage A: сформулирован проверяемый механизм и различающий опыт; количественная экономика Stage B не выполнена.',
        'revision_reason':'Старые 35 формулировок пересматриваются по локальным данным; ни нехватка данных, ни конкуренция не экономический отказ.',
        'successor_ids':[],'revisit_condition':'Новый датированный рынок/KEEP/контракт/поставка или исход совместного расчёта'})
write_json('hypotheses.json',{'hypotheses':hypotheses,'legacy_dispositions':[
    {'ancestor_id':r['candidate_id'],'status':'MERGED_WITH_LINEAGE_FOR_MRV_SCOPE' if r['candidate_id'] not in ['C08','C14','C29'] else 'CROSS_CITY_BRANCH_NOT_CLOSED_BY_MRV',
     'scope':r['author_paths'],'reason':'MRV-часть сведена к общим тестам; самостоятельный город/маршрут не отклонён этим пакетом.'}
    for r in json.loads((ROOT/'inputs/PLAN_MRV_legacy_lineage.json').read_text())['rows']],
    'historical_author_result':{'source':'dceadc98: data/processed/network_summary.csv','preserved_extract':'inputs/BASE_processed_network_summary_MRV.csv',
    'base':'12 routes, 6 aircraft, 98 flights/week, 388388 segments/year, result285 million RUB/year',
    'cautious':'8 routes, 4 aircraft, 48 flights/week, 141871 segments/year, result−2024 million RUB/year',
    'disposition':'FROZEN_AUTHOR_SCENARIO_NOT_COMPARABLE_CURRENT_DECISION; ресурс и исходный KEEP отличаются, rw_migrated=0 не принимается за факт. Не переписан и не суммируется с новыми программами.'}})

requests=[]


def request(rid, owner, programmes_, fields, why, acceptance, priority='MATERIAL_STAGE_B'):
    requests.append({'request_id':'MRV-'+rid,'owner':owner,'programme_ids':programmes_,
        'source_pins':';'.join(k+':'+v for k,v in pins['pins'].items()),'required_fields_or_test':fields,
        'decision_impact':why,'acceptance_boundary':acceptance,'status':'REQUESTED_NOT_RUN',
        'priority':priority,'continue_without_answer':'Stage A спецификации и локальные источники завершены; общий расчёт не подменён догадкой.'})


request('B01','P03;P05;P06','ALL','Будущий affected KEEP 2027–2028: физические flights/tails/committed_sales, own products MRV–EVN/TBS/BUS, KUF/GOJ/KZN/CEK–EVN/TBS, AER/MCX и донорские задания.',
        'Net-new RW, свои продажи, потерянный вклад и сравнение баз.','KEEP не пустой; одинаковая N(t)/external scenario; старые продажи и новые альтернативы пересчитываются один раз.','CRITICAL_FOR_ANY_NET_DELTA')
request('B02','P03','MRV-R8;H8;E8;M8;R4;E4','Tail IDs × day/month; RRJ95 exact variant/cabin/пейлоад/реальная трасса; начальная локация/ferry, crew duty/ночёвки, ТО/reserve, slots/SGHA.',
        'Реальность двух/одного борта, расходы базы против цепочки.','Датированные шаблоны этого пакета — не dispatch admission; KUF/SVX опорные не значит свободные.','CRITICAL_FOR_OPERATIONS')
request('B03','P02','ALL','Полный конкурирующий календарь и comparable gross fare на выбранные даты всех 8 пар + прямые/пересадки: date/as_of/lead/багаж/fees/refund; физические legs/operator/inventory binding.',
        'Неполный P02 857 рынков не пустой рынок и не admission кресел.','P02_SOURCE_EXPORT и локальное табло сохраняются; UNKNOWN seats/continuity/sale не превращаются в ноль или100.')
request('B04','P05','ALL','MRV target8 monthly endpoints: сверить PEE both-direction prior129436 с рейтингом «из Перми»22579 (в статье также LF94,5%), KUF prior183486 с коллегиальной строкой47000; сначала определить направление/сегменты/OD/период/coverage; сохранить старый prior.',
        'Крупное различие порядка величины может изменить масштаб программы.','Это запрос basis/calibration, не утверждение ошибки всех рядов и не собственная замена P05. Base/cautious не CI.','CRITICAL_FOR_MARKET_SCALE')
request('B05','P05;P06','MRV-H8;H8A;XH8;XH8A','R8/H8/H8A и XR8/XH8/XH8A: оценить exact outbound+return7/10/14 ночей, MCT60/90/120/180, detour/time/own-migration и response; север–север не считать удобным из геометрии.',
        'Определяет, нужен ли хаб и какие окна менять.','Одинаковые физические рейсы при сравнении R/H; изменение календаря — отдельная версия. 6/8 ночей из шаблона не подменять7/14.')
request('B06','P04','ALL','Принять локальные строки ФАС777/25 ОАО аэропорт и778/25 ООО Кредитинвест: официальный текст/редакция, billing pax/transfer/НДС; топливо/хранение/заправка и скидки по отдельным услугам.',
        'Исправляет locator tranche01 и не даёт автоматически начислить хабовые льготы.','Два оператора не сливаются. Secondary rate до приёмки не фактическая будущая цена RW.','CRITICAL_LOCAL_COST_EXTENSION')
request('B07','P03;P04','MRV-R8;H8;M8;R4;P8;XR8;XH8','S7 MRV SSJ100: RW contract/slot/SLA/parts и трудоёмкость форм; 6790/6170 RUB/нормочас2026; capability SJ100/ПД8 отдельно.',
        'Публичное ТО снимает UNKNOWN provider, не UNKNOWN availability/base cost.','Нормочас не лётный час; материалы/налоги/календарные формы и восстановление отдельно.')
request('B08','P04;P06','ALL','TH-OPTION/TH-FIXED/TH-LAUNCH/TH-MRO/TH-FARE/TH-FUNDING: полная совместная граница базы/launch/MRO/recovery с monthly accrual и cash, prelaunch/exit/terminal obligations.',
        'Финансируемая траектория улучшения допускается без прибыли на первой ступени.','Численный порог при известных остальных термах; при материальном UNKNOWN оставить null. Изменённый тариф → повторить choice, не делить затраты при фиксированном спросе как прогноз.')
request('B09','P05;P02;P04','MRV-P8;G0','Санатории/подвоз/партнёр: заезды7/10/14, seats per dated flight, paid block/release_unused/protection/baggage/SLA, кто платит и когда; реестр зарезервированных мест.',
        'Дополнительная ценность сервиса и альтернатива без новых рейсов.','Нет договора → доступный G0/R8 без гарантированного блока; существующий local/transfer спрос не обнулять.')
request('B10','P03;P06','ALL','Одинаковые N(t): phased/partial/delay/zero; передан/готов/свободен; lag entry, 1tail step; отдельно ветвь без новых Ту214. Fixed vs feasible adaptive с commitments.',
        'Не переоценить поставки; сравнить ожидание/малый запуск/переход.','Числа этого пакета — исследовательские точки от размера дизайна, не прогноз Red Wings; actual fleet остаётся UNKNOWN.')
request('B11','P02I;P05;P03;P04','MRV-XR8;XH8','Международные OD/prices/rights/foreign station/FX/baggage/MCT; текущие RW direct EVN/TBS; 0 новых Tu214; SJ100/ПД8 отдельная международная эксплуатация.',
        'Дополнительная ветвь не вытесняет внутренний CASE_SJ.','P05 a63a047 внутренний: не переносить его domestic pool/налоги на международные рынки.')
request('B12','P03','ALL','MRV реконструкция2026–2028: AIP/NOTAM/этапы/declared distances/слоты/терминал/стоянка; не выводить длительность закрытия из новости.',
        'Доступность по сезону и recovery при работах.','Проектная мощность1000pax/hour не свободная волна; новость о плане не датированное ограничение.')
request('B13','P06;координатор','ALL','Принять P05 a63a047 в P06final982f13d, сформировать полные P/KEEP bundles с contract schema, совместный mix и marketshare compatible period/denominator.',
        'Общие деньги/choice и финальное сравнение вместо суммирования самостоятельных результатов.','P0642 авторских checks не независимая приёмка. Этот пакет движок не запускал и real RW acceptance не заявляет.','CRITICAL_COMMON_ENGINE_INTEGRATION')
write_csv('comparison_requests.csv',requests)

# Локальная механическая проверка спецификаций: только то, что действительно задано.
errors=[]
grouped=defaultdict(list)
for f in flights:
    grouped[(f['programme_id'],f['window_id'],f['tail_role'])].append(f)
daily=defaultdict(int)
for key, fs in grouped.items():
    fs.sort(key=lambda x:x['departure_utc'])
    for prev,nxt in zip(fs,fs[1:]):
        if prev['destination_airport'] != nxt['origin_airport']:
            errors.append(['location_continuity',key,prev['flight_template_id'],nxt['flight_template_id']])
        gap=(datetime.fromisoformat(nxt['departure_utc'].replace('Z','+00:00'))-datetime.fromisoformat(prev['arrival_utc'].replace('Z','+00:00'))).total_seconds()/60
        if gap<60: errors.append(['gap_under60',key,gap])
    if fs[0]['origin_airport'] != fs[-1]['destination_airport']:
        errors.append(['window_does_not_close',key])
    for f in fs:daily[(f['programme_id'],f['tail_role'],f['departure_utc'][:10])]+=int(f['block_minutes_analogue'])
if max(daily.values())>480:errors.append(['planning_daily_block_exceeded',max(daily.values())])
assert not errors,errors

# Доказательный контрпример календаря H8, без самостоятельной модели спроса.
connections=[]
for pid in ['MRV-H8','MRV-H8A','MRV-XH8','MRV-XH8A']:
    fs=[f for f in flights if f['programme_id']==pid and f['window_id']=='2028-S']
    for a in fs:
        if a['destination_airport']!='MRV':continue
        at=datetime.fromisoformat(a['arrival_utc'].removesuffix('Z'))
        for b in fs:
            if b['origin_airport']!='MRV' or b['destination_airport']==a['origin_airport']:continue
            bt=datetime.fromisoformat(b['departure_utc'].removesuffix('Z')); gap=(bt-at).total_seconds()/60
            if 60<=gap<=180:
                connections.append({'programme_id':pid,'origin':a['origin_airport'],'via':'MRV','destination':b['destination_airport'],
                    'first_flight_id':a['flight_template_id'],'second_flight_id':b['flight_template_id'],
                    'first_departure_utc':a['departure_utc'],'final_arrival_utc':b['arrival_utc'],
                    'connection_minutes':gap,'status':'CLOCK_ONLY_NOT_SALEABLE_NOT_APPROVED_MCT','assumption_id':'A-MRV-MCT'})
write_csv('connection_clock_diagnostic.csv',connections)
returns=[]
for c in connections:
    available=[x for x in connections if x['programme_id']==c['programme_id'] and x['origin']==c['destination'] and x['destination']==c['origin']]
    arrive=datetime.fromisoformat(c['final_arrival_utc'].removesuffix('Z')).date()
    for nights in [7,10,14]:
        matches=[x for x in available if (datetime.fromisoformat(x['first_departure_utc'].removesuffix('Z')).date()-arrive).days==nights]
        inside=arrive+timedelta(days=nights)<=date(2028,8,20)
        returns.append({'programme_id':c['programme_id'],'outbound_first_flight_id':c['first_flight_id'],'origin':c['origin'],
            'destination':c['destination'],'stay_nights':nights,'return_clock_match_count':len(matches) if inside else 'UNKNOWN_OUTSIDE_CAPTURE',
            'status':'CLOCK_TEST_ONLY_NOT_END_TO_END_PRODUCT','assumption_id':'A-MRV-MCT;A-MRV-SEASONS'})
write_csv('return_clock_diagnostic.csv',returns)

validation={'status':'LOCAL_STAGE_A_MECHANICAL_CHECKS_PASS','checks':{
    'pinned_input_file_hashes_rechecked':len(pins['files']), 'source_receipt_raw_hashes_rechecked':sum('sha256' in d for d in receipts.values()),
    'programme_specs':len(programmes),'dated_template_rows':len(flights),'tail_window_groups_checked':len(grouped),
    'continuous_tail_locations':True,'minimum_60min_turn_in_templates':True,'closed_14day_tail_windows':True,
    'max_daily_block_minutes_analogue':max(daily.values()),'daily_planning_limit_minutes':480,
    'full_domestic_designs_eight_unique_pairs':all(p['unique_pair_count']==8 for p in programmes if p.get('programme_id') in ['MRV-R8','MRV-H8','MRV-E8','MRV-M8','MRV-P8']),
    'all_24_months_in_applicability_requests':len(monthly)==24*len(patterns),
    'P05_target_rows':len(od),'distinct_P05_scenarios':sorted(set(r['external_scenario_id'] for r in od)),
    'no_annualisation_from_template':True,'no_independent_money_or_choice_model':True},
    'errors':errors,'limits':'Это локальная механика проектного аналога. Нет crew/ТО/slots/payload/approved MCT/reserve/продаж/future KEEP/P06 economic acceptance.',
    'independent_review':'NOT_RUN'}
write_json('validation.json',validation)

readiness={'airport':'MRV','version':'research_v1','as_of':ASOF,
    'stage_a':'COMPLETE_RESEARCH_SPECIFICATION_WITH_TRACEABLE_CONDITIONS',
    'stage_a_meaning':'Источники/данные/гипотезы/парные программы/условные шаблоны/пороговая постановка/адресные Stage B requests завершены.',
    'stage_b':'NOT_RUN_PENDING_ACCEPTED_COMMON_INPUTS', 'economic_admission':'CONDITIONAL_NOT_ACCEPTED',
    'dispatch_admission':'CONDITIONAL_NOT_ACCEPTED','choice_calibration':'P05_SCENARIO_NOT_IDENTIFIED',
    'profitable_strategy_proven':False,'RW_rank2_proven':False,'market_share_delta':None,'funding_required':None,
    'candidate_outcome':'MRV сохранён для сравнения; конкретная новая база/хаб/частота не выбраны.',
    'strong_findings':['MRV-E01','MRV-E02','MRV-E04','MRV-E05','MRV-E07','MRV-E10'],
    'critical_request_ids':['MRV-B01','MRV-B02','MRV-B04','MRV-B06','MRV-B13'],
    'prohibited_conclusions':['Нет конкурента из UNCOVERED','100 номинальных =100 открытых кресел','S7 offer = договор/мощность RW','RRJ95 analogue = SJ100/ПД8 допуск','Сумма stand-alone money = mix','Clock pass = продаваемая поездка','Stage A = окончательная экономика'],
    'validation':'validation.json','independent_acceptance':'NOT_RUN'}
write_json('readiness.json',readiness)
case={'case_id':'MRV','airport':'MRV','city':'Минеральные Воды / курорты КМВ','language':'ru',
    'purpose':'Распределение одинакового ограниченного ресурса между новой MRV базой, хабом, KUF/SVX цепочками, смешанным и контрактным доступом.',
    'period':['2027-01','2028-12'],'history':'2025 и доступный2026 отдельно от будущего same-scenario KEEP',
    'main_case':'CASE_SJ_DOMESTIC; RRJ95 и SJ100_PD8 раздельно','extension':'Международная XR8/XH8/G0; новых Ту214=0',
    'end_2028_design_target':'8–12 уникальных airport pairs; полные R8/H8/E8/M8/P8 содержат8; R4/E4 промежуточные4',
    'source_pins':'source_pins.json','data_to_hypothesis':'evidence.csv → hypotheses.json → programme_candidates.json → comparison_requests.csv',
    'model_ownership':'Авторская panel/model dceadc98 сохранена; P05 a63a047 единственная общая choice/demand основа; P06final982f13d общее ядро. Независимая экономика здесь не создана.',
    'support_policy':'Никаких автоматических хабовых льгот/премий за500км; отсутствие подписанной поддержки — не гарантированная будущая выплата и не экономический отказ.',
    'write_boundary':str(ROOT),'git_mutations':0,'children':0,'bookings_payments_external_messages':0,
    'continuation':'Предыдущий provider transport terminal Connection failed: error sending request — по brief координатора; новые provider transport errors не наблюдались. Старые receipts/tranche сохранены.',
    'completion_scope':'Stage A package only; финальная стратегия и совместная экономика требуют Stage B.'}
write_json('case.json',case)

prior={r['origin_market']:r['annual_both_directions_prior'] for r in od if r['destination_market']=='MRV' and r['month']=='2028-01' and r['external_scenario_id']=='base'}
write_csv('P05_local_scale_questions.csv',[
 {'airport_pair':'PEE-MRV','historical_route_flow_2025':22579,'historical_source_id':'MRV-E17; статья описывает вылеты «из Перми»; reported LF94.5%; не both-directions без методики','P05_annual_both_directions_prior':prior['PEE'],
  'P05_source':'a63a047; inputs/P05_od_monthly_MRV_target8.csv','comparison_status':'DIFFERENT_BASIS_MUST_RECONCILE_NOT_AUTOMATIC_ERROR','request_id':'MRV-B04'},
 {'airport_pair':'KUF-MRV','historical_route_flow_2025':47000,'historical_source_id':'inputs/BASE_known_flows_MRV.csv: source_row32; colleague-only47000',
  'P05_annual_both_directions_prior':prior['KUF'],'P05_source':'a63a047; inputs/P05_od_monthly_MRV_target8.csv',
  'comparison_status':'COLLEAGUE_HISTORICAL_SCOPE_AND_PRIOR_BASIS_UNRESOLVED','request_id':'MRV-B04'}])

report = '''# Минеральные Воды: исследовательский пакет Stage A

MRV остаётся кандидатом для общего сравнения. Подготовлены проверяемые гипотезы и конкретные программы на одном и двух условных бортах. Выбора новой базы или хаба, доказанной прибыли, прироста доли рынка и потребности в финансировании пока нет. Эти результаты требуют общего Stage B в P05/P06 с принятыми рынками, ресурсом и будущим KEEP.

## Данные и границы

Исходные авторские результаты dceadc98, reassessment c18f764 и P00R/P02v2/P03v2/P04final/P05/P06final закреплены в `source_pins.json`: commit, путь, Git blob и SHA256. Выборки содержат исходный номер CSV-записи и hash канонического JSON строки. Полные чужие архивы и fixtures не скопированы. Сохранённые источники, receipts и `usable_tranche_01.json` предыдущего запуска сохранены. Таблицы `sources.csv` и `evidence.csv` дают URL, организацию, дату, период, единицу, гранулярность, статус и покрытие.

Публичная карта услуг S7 Technics прямо включает линейное и базовое ТО SSJ100 в MRV. Прайс ревизии января2026 даёт6790/6170 RUB за нормочас линейного/базового ТО без налогов и материалов. Это сильнее прежней косвенной ссылки на базирование Азимута. Договор RW, свободная мощность, сроки восстановления, части и SJ100/ПД8 остаются неизвестны. Нормочас нельзя умножать на лётные часы как готовую стоимость ТО. Источники: [S7 услуги](https://www.s7technics.ru/services/) и сохранённый прайс `sources/S7_MRO_RATES_2026.pdf`, E01/E02.

Локальные сборы требуют двух операторов. Прочитанное зеркало777/25 относится к ОАО «Международный аэропорт Минеральные Воды» и содержит аэродромные/заправочные услуги. Зеркало778/25 относится к ООО «Кредитинвест» и содержит терминал, обслуживание/безопасность пассажиров и хранение топлива, включая отдельные2027/2028. В раннем tranche01 ссылка на777/25 рядом с пассажирскими ставками была неточной: источник привязки уточнён в E04/E05, старый файл не переписан. Официальные TLS EOF сохранены; НДС, редакция, начисление на transfer и реальные условия RW не приняты. Никакая льгота хаба автоматически не начислена. Вторичные тексты: [777/25](https://legalacts.ru/doc/prikaz-fas-rossii-ot-08102025-n-77725-ob-utverzhdenii/), [778/25](https://legalacts.ru/doc/prikaz-fas-rossii-ot-08102025-n-77825-ob-utverzhdenii/).

RW уже присутствовала в MRV: опубликованы TBS/BUS в2024 и MRV среди городов прямых EVN в марте2026. Текущий рейсовый KEEP не получен; существующие продажи нельзя объявить нулевыми. [Зимний релиз RW](https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/) называет KUF/SVX опорными аэропортами; отсутствие MRV в неполном перечне не доказывает отсутствие базы. E06–E08.

[Азимут](https://azimuth.ru/ru/about/azimuth) прямо называет MRV базой и публикует парк19 SSJ100. Это парк конкурента, а не число свободных бортов в MRV. Сохранённое табло даёт86 записей MRV, включая CEK/PEE/KUF/OMS/EVN/TBS/IST. Имя группы11–13 ноября не равно дате каждого вылета: последняя запись KUF отправляется14 ноября. План/сообщённый факт не доказывает продажу, физическую непрерывность и открытые кресла. Исходные row IDs/hashes сохранены, UNKNOWN не заменены местами самолёта. P02 содержит также N4 на GOJ и SU/U6 на SVX; перечень остаётся неполным. E09–E11 и `market_deltas.csv`.

## Спрос и сезон

Курортная роль MRV — основание отдельного продукта, но не оценка неудовлетворённого спроса. Сообщение аэропорта о2025 даёт округлённо4,6млн пассажирских обслуживаний и снижение4,6%; международные1,2млн с ростом8,6%. В интервью регионального министра8,4млн посетителей края включают4,1млн однодневных экскурсантов. Ни один агрегат не является конечным OD, уникальными авиапассажирами или знаменателем доли RW. Первичный ввод нового терминала и1000пасс./час не означают свободную мощность волны. E14–E19.

Пермская статистика22579 на линии MRV за2025 и коллегиальная строка Самары47000 сохранены раздельно с их покрытием. Статья о Перми описывает рейтинг направлений «из Перми» и сообщает загрузку линии94,5%: сначала необходимо установить направление и статистическую базу. P05 a63a047 использует both-directions prior129436 для PEE–MRV и183486 для KUF–MRV. Прямое сравнение или механическое удвоение22579 преждевременно. Определения и охват могут различаться; здесь не объявлена ошибка P05 и не построена конкурирующая модель. Запрос B04 требует сверить основания до выбора масштаба. Сценарная сезонность P05 основана на более широком авиааналоге; интервью санаториев указывает на спрос вне одного летнего пика. Нужен местный помесячный разрез и календарь заездов. Все768 строк P05 выбранных восьми пар сохранены с row hash; base/cautious — сценарии, а не доверительные интервалы.

## Проверяемые гипотезы

`hypotheses.json` регистрирует восемь механизмов: местный курортный продукт; добавочная ценность хаба; санаторный календарь и подвоз; цепочки через KUF/SVX; доступность ТО; международная мини-волна; поэтапный запуск при поставках; партнёрский доступ без новых рейсов. Для каждого есть происхождение, конкурирующее объяснение, различающий опыт, неизвестные и условие пересмотра. Наличие Азимута,500км, старый score и неполные данные не используются как экономический отказ.

Авторская MRV-модель сохранена отдельно: base12маршрутов/6бортов/98рейсов в неделю,388388сегментов в год и285млн RUB результата; cautious8/4/48,141871 и−2024млн. Это исторические сценарные результаты автора при другом ресурсе и границах. Их нельзя сопоставить с новой программой как готовые денежные дельты; прежнее rw_migrated=0 не принято как отсутствие своих продаж. Файлы автора и frozen результаты не изменены.

## Парные программы

Полный внутренний дизайн имеет8уникальных airport pairs: MRV–KUF/GOJ/PEE/CEK/UFA/KZN/SVX/OMS. Это ресурсная начальная спецификация для проверки, а не оптимальная сеть. KUF/GOJ/PEE/CEK получают по2RT/неделю, остальные по1. Два условных борта выполняют по одному RT или двухплечевой цепочке в день с понедельника по субботу. Кресла100 — номинальный аналог семейства; фактическая кабина, blocked и saleable неизвестны.

| Программа | Сравнение на общем ресурсе | Что различает опыт |
|---|---|---|
|R8: радиальная база MRV|H8/E8/M8, два борта|Местные поездки и полная цена новой базы|
|H8: те же8пар и те же частоты|R8, те же два борта|Время окон/защита/трансфер против местного расписания|
|H8A: чередование окон через неделю|R8/H8, те же два борта|7-ночный возврат как отдельное изменение проектного календаря|
|E8: цепочки из KUF и SVX через MRV|R8/M8, те же два борта|Существующая база против ночёвок в GOJ/UFA/KZN/PEE/CEK/OMS; частоты эндогенно отличаются|
|M8: один MRV-борт и SVX-цепочки|R8/E8, те же два борта|Смешанное размещение и общий счёт затрат/спроса|
|R4 против E4|Один одинаковый борт|Малая новая база против цепочек KUF;4пары как промежуточная ступень|
|P8 против R8 и G0|Те же физические рейсы/общий доступный ресурс|Договорный подвоз/санаторные блоки/партнёр; без договора нет гарантированного продукта|
|XR8 против XH8/XH8A|Два борта,8пар, UFA/KZN заменены TBS/EVN|Дополнительная международная ветвь: конечные продукты против мини-волны и её календарной ревизии; новых Ту214=0|

E8 не получает бесплатное сохранение базы: расходы KUF/SVX, экипажные ночёвки, reposition, ТО и прежние задания входят в полный расчёт. Новая база MRV тоже не объявляется неподъёмной заранее. Общий ресурс означает одинаковые реальные tails/готовность/crew/ТО/reserve/начальную локацию/финансирование; расход часов и число использованных кресел могут различаться. Непотраченный ресурс остаётся в альтернативном KEEP.

## Датированные шаблоны и возврат

`dated_flight_templates.csv` содержит конкретные UTC-плечи в14-дневных окнах зимы, межсезонья и лета каждого из2027/2028. Оборот60минут и MCT90 — явные исследовательские параметры. Block-time опирается на опубликованные точки, для KZN применён отдельно маркированный аналог GOJ. Направления/даты/тип должны заменить эти аналоги в Stage B. SJ100/ПД8 не получил характеристики SSJ как подтверждённые.

Локально проверены непрерывность расположения каждого tail role, закрытие14-дневного окна, пауза не менее60минут и планировочный налёт не более8часов за день. Это не проверка duty экипажа, ТО, резерва, дальности/нагрузки, NOTAM, слотов или продаваемости. Воскресенье без назначений не является отдельным резервным самолётом.

H8 создаёт односторонние окна: утренний возврат первого борта и вылет второго через90минут. При редких частотах обратный подходящий рейс даёт6/8ночей вместо7/14. Этот исход сохранён. Отдельные H8A/XH8A меняют утренние и поздние направления во второй неделе, чтобы проверить7-ночный возврат при тех же частотах и креслах. `connection_clock_diagnostic.csv` и `return_clock_diagnostic.csv` хранят оба дизайна, включая UNKNOWN за границей14-дневного захвата. Часовая стыковка и её улучшение не объявлены продаваемым продуктом. 10/14ночей и предпочтения местных пассажиров остаются отдельным тестом; недостаток H8 не доказывает невозможности всех хабов.

## Будущий KEEP и изменения сети

`market_deltas.csv` содержит before/after каждой затронутой пары и программы, source product IDs/row hashes конкурентов, условные частоты и действие add/retime/replace. Исходное RW предложение, точные сокращения и committed sales остаются UNKNOWN до привязки к будущему KEEP. Вся незатронутая сеть сохраняется. Нельзя складывать местные и пересадочные поездки независимо или продавать одни кресла нескольким программам. При существующем SSJ нужен донор с потерянным результатом; при новом SJ — альтернативное применение того же нового ресурса, без выдуманного донора.

## Поставки и24месяца

`monthly_stage_requests.csv` покрывает каждый месяц2027–2028 для одиннадцати лётных программ. `delivery_scenarios.csv` содержит четыре исследовательские ветви N(t): поэтапно два борта, только один, задержка, ноль. В phased transfer1июля/1октября2027 и условный entry1августа/1ноября; partial — один с entry1ноября2027; delay — entry1мая/1августа2028; zero —0. Число2объясняется размером парного опыта, а месяцы и лаг ввода — иллюстративные точки чувствительности, не подтверждённый график Red Wings. Поставка раньше H2 2027 не введена. Передан, готов к коммерческой работе и свободен для проекта — разные поля; последнее UNKNOWN. Ветка действующего SSJ отдельно требует реального донора и может обходиться без новых SJ.

Шесть14-дневных окон не являются годовой сетью. Полный датированный календарь, сезонные частоты и спрос каждого месяца — обязательная работа Stage B. Годовые пассажиры, выручка и доля рынка из этих недель не вычислены.

## Экономика порогами

Общий P05 a63a047 — сценарная основа спроса/выбора; международные OD требуют отдельного P02I/P05. P06final982f13d — условный реализованный движок; его42авторских проверки и примеры не доказывают реальную экономику RW или независимую приёмку. Здесь нет собственной денежной/choice-модели и нет запуска P06 на неполном пакете.

P04 TH-OPTION сравнивает остаток результата новой и существующей базы до ещё не посчитанных различающихся расходов. TH-FIXED/TH-LAUNCH задают допустимую совместную границу постоянных/пусковых расходов; TH-MRO требует правильного драйвера и отдельных форм; TH-FARE относится к уникальной поездке и при изменении цены требует нового выбора пассажира. TH-FUNDING требует событийного cash с предзапуском, восстановлением/выходом, процентами и обязательствами после2028. Численная граница неизвестна до принятых прочих слагаемых. Нельзя одновременно объявить каждый неизвестный расход допустимым по его отдельному максимуму.

Стратегия может иметь отрицательный первый этап. Stage B должен показать механизм улучшения по конкретным месяцам, финансирование до него и условие остановки. Снижение убытка не доказывает рост перевозок, прибыльность всего бизнеса или достижение№2. Неподписанная субсидия/скидка не считается поступившими деньгами; отдельная ветвь без получения поддержки сохраняется.

## Передача Stage B

`comparison_requests.csv` содержит13адресных запросов с полями и границей приёмки. Критичны: будущий affected KEEP и свои продажи(B01); реальный ресурс/dispatch/crew/ТО(B02); сверка масштаба P05 с локальной историей(B04); приёмка двух операторов тарифов(B06); полная интеграция accepted P/KEEP в P06final(B13). Остальные закрывают полный рынок, возвратные окна, MRO, пороги/финансирование, партнёров, поставки, международную ветвь и реконструкцию.

Stage A завершён как исследовательская спецификация. MRV не отклонён по конкуренции или неизвестным полям; готовый к запуску хаб и экономически выбранная сеть не заявлены. `readiness.json` хранит эти границы машинно; `validation.json` — только фактически выполненные локальные проверки; `output_manifest.json` — полный перечень файлов, байты и SHA256. Координатору передаётся весь назначенный каталог, без Git-операций исполнителя и правок общих входов.
'''
report = re.sub(r'([А-Яа-яЁё])([0-9])', r'\1 \2', report)
report = re.sub(r'([0-9])([А-Яа-яЁё])', r'\1 \2', report)
report = re.sub(r'([0-9])(RUB|RT|пасс)', r'\1 \2', report)
(ROOT/'report.md').write_text(report)

write_json('usable_tranche_02.json', {'status':'STAGE_A_COMPLETE_LOCAL_FINDINGS_NOT_STAGE_B_ADMISSION','as_of':ASOF,
    'findings':[
      {'id':'MRV-RATES-OPERATOR-CORRECTION','finding':'Пассажирские ставки2027/2028 привязаны вторичным текстом к778/25 ООО Кредитинвест;777/25 — другой оператор/аэродромные услуги. Tranche01 locator уточнён, не переписан.',
       'evidence_ids':['MRV-E03','MRV-E04','MRV-E05'],'source_sha256':receipts['MRV_ORDER_778_LEGALACTS']['sha256'],'request':'MRV-B06'},
      {'id':'MRV-P05-SCALE','finding':'PEE both-direction prior129436 vs статья с рейтингом «из Перми»22579 и LF94,5%; KUF183486 vs коллегиальная47000. Сначала direction/basis/coverage: прямое сравнение и автоматическое удвоение не приняты. Нужна сверка P05, это не объявление ошибки и не новая модель.',
       'input_sha256':sha((ROOT/'inputs/P05_od_monthly_MRV_target8.csv').read_bytes()),'request':'MRV-B04'},
      {'id':'MRV-HUB-RETURN','finding':'H8 имеет условные односторонние90мин окна; редкий обратный календарь не доказывает7/10/14 ночей. Контрпример относится к текущему шаблону.',
       'diagnostic_sha256':sha((ROOT/'return_clock_diagnostic.csv').read_bytes()),'request':'MRV-B05'}],
    'stage_a_programmes':[p['programme_id'] for p in programmes], 'stage_b_requests':'comparison_requests.csv'})

write_json('handoff.json', {'package':'MRV/research_v1','status':readiness['stage_a'],'write_scope':str(ROOT),
    'source_pins':'source_pins.json','entrypoint':'report.md','readiness':'readiness.json',
    'outputs':['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','report.md'],
    'programme_count':len(programmes),'stage_b_requests':len(requests),'manifest':'output_manifest.json',
    'manifest_hash_note':'Manifest исключает только себя во избежание цикла; включает handoff и все остальные файлы.',
    'coordinator_commit':'Коммитит координатор только назначенный каталог по manifest; исполнитель не менял индекс/ветки/root inputs.',
    'stage_b_not_done':['actual economic/choice allocation','full future KEEP','dispatch/crew/ТО/reserve admission','full24month flight calendar','partner contract acceptance','independent P06 acceptance'],
    'new_provider_transport_error':None,'prior_error_from_brief':'Connection failed: error sending request',
    'source_access_failures':'sources.csv and sources/*.receipt.json; no service restart or browser intervention',
    'reproduce':'python3 '+str(ROOT/'build_stage_a.py'), 'children':0,'git_mutations':0,'external_messages_bookings_payments':0})

files=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.name=='output_manifest.json' or '__pycache__' in p.parts:continue
    raw=p.read_bytes();files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
write_json('output_manifest.json',{'package':'MRV/research_v1','version':'stage_a_v1','as_of':ASOF,
    'root':str(ROOT),'file_count':len(files),'files':files,'files_canonical_sha256':sha(canonical(files)),
    'source_pins_sha256':sha((ROOT/'source_pins.json').read_bytes()),
    'status':'SEALED_STAGE_A_NOT_STAGE_B_ACCEPTANCE','self_exclusion':'Only output_manifest.json excluded to avoid recursive self-hash'})
print(json.dumps({'status':readiness['stage_a'],'files':len(files),'programmes':len(programmes),
                  'templates':len(flights),'requests':len(requests),'manifest_sha256':sha((ROOT/'output_manifest.json').read_bytes())},ensure_ascii=False))
