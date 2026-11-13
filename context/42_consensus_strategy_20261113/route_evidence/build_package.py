#!/usr/bin/env python3
"""Read exact Git blobs; write only this evidence package. No model execution/network."""
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
P = 'context/35_full_programme_execution_20261112/'
AUTHOR = 'f20000e72d5ca934f45f3aaaca4c320750ebccff'
RESEARCH = '6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1'
P02 = 'd9486f113f074c185a94bcc5c0afeef12ea3574f'
P03 = '79dc698b99dfe866886d32376ed388e85bdd039c'
P04 = '620a0ac4bb11763319c4227485f6a3996b91d367'
P09 = '736859fdd08448c2564b7b9269b751abe00b5cbc'
P09_MANIFEST = '7b20a1a247ee4b3cf96d94648bb36d61482cb0a58eb7a296ada49a78c818d1fa'
ENGINE = '982f13d9b6c378ed9581125ecc5c40f17dade6a3'
ACCEPTANCE_PIN = '48bec00db0f0995a9b02a18309be2544cb3528de'
FILES, BLOBS, EVIDENCE = {}, {}, {}

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def source(sid, commit, path, kind, use):
    b = git('show', commit + ':' + path)
    BLOBS[sid] = b
    FILES[sid] = dict(source_id=sid, commit=commit, path=path,
        git_blob=git('rev-parse', commit + ':' + path).decode().strip(),
        sha256=sha(b), bytes=len(b), acquisition='git_show_exact_blob',
        data_type=kind, allowed_use=use, selected_evidence_ids=[])
    return b.decode('utf-8-sig')

def csvrows(sid):
    stream = io.StringIO(BLOBS[sid].decode('utf-8-sig'))
    reader = csv.DictReader(stream)
    rows = []
    last = 1
    for n, row in enumerate(reader, 1):
        rows.append((n, last + 1, reader.line_num, row))
        last = reader.line_num
    FILES[sid]['csv_headers'] = reader.fieldnames
    FILES[sid]['csv_data_record_count'] = len(rows)
    return rows

def evrow(sid, rowtuple, kind=None):
    n, lo, hi, row = rowtuple
    eid = sid + ':record:' + str(n)
    EVIDENCE[eid] = dict(evidence_id=eid, source_id=sid,
        csv_data_record_1based=n, physical_line_start=lo, physical_line_end=hi,
        source_fields=list(row), row_sha256=sha(canon(row)),
        hash_scope='UTF8 canonical JSON: sorted keys, ensure_ascii=false, compact separators',
        data_type=kind or FILES[sid]['data_type'], original_row=row)
    if eid not in FILES[sid]['selected_evidence_ids']:
        FILES[sid]['selected_evidence_ids'].append(eid)
    return eid

def evtext(sid, lo, hi, kind=None, pointer=None, value=None):
    lines = BLOBS[sid].decode('utf-8-sig').splitlines()
    eid = sid + (':' + pointer if pointer else ':lines:' + str(lo) + '-' + str(hi))
    obj = dict(evidence_id=eid, source_id=sid, physical_line_start=lo,
        physical_line_end=hi, data_type=kind or FILES[sid]['data_type'])
    if pointer:
        obj.update(json_pointer=pointer, extracted_value=value, extraction_sha256=sha(canon(value)))
    else:
        obj.update(excerpt='\n'.join(lines[lo-1:hi]))
    EVIDENCE[eid] = obj
    if eid not in FILES[sid]['selected_evidence_ids']:
        FILES[sid]['selected_evidence_ids'].append(eid)
    return eid

HTML = source('AUTHOR_HTML', AUTHOR, 'outputs/redwings_panel.html', 'AUTHOR_MODEL_OUTPUT',
    'Отдельная авторская модель kiruha355; frozen reference, не общий прогноз.')
D = json.JSONDecoder().raw_decode(HTML.split('const D = ', 1)[1])[0]
HTML_LINE = next(i for i, line in enumerate(HTML.splitlines(), 1) if line.startswith('const D = '))
source('AUTHOR_ROUTES', AUTHOR, 'data/processed/network_routes.csv', 'AUTHOR_MODEL_OUTPUT', 'Годовая строка пары в обе стороны, внутри своего варианта.')
source('AUTHOR_DEMAND', AUTHOR, 'data/processed/demand_estimates.csv', 'AUTHOR_DEMAND_SCENARIO', 'Исторические/модельные оценки различать; od_base не observed endpoint OD.')
source('AUTHOR_ASSUMPTIONS', AUTHOR, 'data/assumptions/network.csv', 'AUTHOR_ASSUMPTION', 'Параметры аналога SSJ, не утверждённые SJ-100/ПД-8 и не прогноз поставок.')
source('AUTHOR_CODE', AUTHOR, 'src/network_model.py', 'MODEL_DEFINITION', 'Проверка grain, годового масштаба, включённых расходов и округления; не запуск.')
source('AUTHOR_BUILD', AUTHOR, 'src/build_dashboard.py', 'PROJECTION_DEFINITION', 'Проверка переноса CSV в D.net.routes.')
source('P02_PRODUCTS', P02, P + 'P02/competitor_products.csv', 'PUBLISHED_PRODUCT', 'Датированные публикации/правила/ground; не исполнение и не свободные кресла.')
source('P03_README', P03, P + 'P03/README.txt', 'RESOURCE_CONTRACT', 'Поставки/ввод/crew/ТО/резерв и physical airports — отдельные gates.')
source('P04_README', P04, P + 'P04/README.md', 'COST_CONTRACT', 'Полная прибыль/финансирование неизвестны; локальные ставки требуют применения.')
source('P01_KNOWN', RESEARCH, P + 'P01_MONTHLY/inputs/BASE_known_flows.csv', 'HISTORICAL_SEGMENT_CONTEXT', 'Поток опубликованного направления 2025; не конечный OD и не RW share.')
source('P01_OD', RESEARCH, P + 'P01_MONTHLY/endpoint_od_observations.csv', 'OBSERVATION_COVERAGE', 'Ноль подтверждённых строк в этом пакете; не нулевой спрос.')
source('P01_PAIRS', RESEARCH, P + 'P01_MONTHLY/airport_pair_segment_observations.csv', 'AIRPORT_PAIR_SEGMENT_OBSERVATION', 'Отдельный сегментный grain; не доказательство конечной поездки.')
source('P01_MONTHLY', RESEARCH, P + 'P01_MONTHLY/airport_monthly.csv', 'AIRPORT_MONTHLY_OBSERVATION', 'Аэропортовый сезонный контекст; не профиль 12 конечных OD.')
source('P01_SUMMARY', RESEARCH, P + 'P01_MONTHLY/monthly_summary.json', 'OBSERVATION_COVERAGE', 'Квалификация наблюдений и пробелов.')
source('VERIFIED_SOURCES', RESEARCH, P + 'P01_MONTHLY/inputs/verified_sources.csv', 'VERIFIED_SOURCE_REGISTRY', 'Реестр источников с границами; доступность источника не даёт route OD.')
source('P09_MANIFEST', P09, P + 'P09/manifest.json', 'SEALED_MANIFEST', 'Только pin и неизменность P09, без переноса результатов на консенсус.')
source('P09_HANDOFF', P09, P + 'P09/handoff.json', 'JOINT_MODEL_BOUNDARY', 'Совместный OD/capacity, SCENARIO_NOT_IDENTIFIED; не общий optimum.')
source('P09_ACCEPTANCE', ACCEPTANCE_PIN, P + 'P00/p09_acceptance.json', 'SCOPED_ACCEPTANCE', 'Разрешение условного показа, не market/dispatch/investment acceptance.')
CITY = {}
for city in ['OMS', 'AER', 'VOG', 'GSV', 'MRV', 'IKT', 'GOJ', 'KUF']:
    sid = city + '_EVIDENCE'
    source(sid, RESEARCH, P + 'variants/' + city + '/research_v1/evidence.csv',
        'CITY_EVIDENCE_MIXED', 'Сохранённый местный dossier: исходный status/period/limitation обязательны.')
    CITY[city] = {r[3]['evidence_id']: r for r in csvrows(sid)}
source('GSV_README', RESEARCH, P + 'variants/GSV/research_v1/README.md', 'CITY_RESEARCH_SYNTHESIS', 'Собственные международные продажи и текущая частичная конкуренция.')
source('VOG_SOURCES', RESEARCH, P + 'variants/VOG/research_v1/sources.csv', 'CITY_SOURCE_REGISTRY', 'URL и локаторы для VOG claims.')

CONTRACT_REFS = [evtext('AUTHOR_CODE', 270, 277), evtext('AUTHOR_CODE', 284, 307),
    evtext('AUTHOR_CODE', 635, 676), evtext('AUTHOR_CODE', 782, 797),
    evtext('AUTHOR_BUILD', 317, 334), evtext('P03_README', 1, 16),
    evtext('P04_README', 1, 7), evtext('P01_OD', 1, 1),
    evtext('P09_HANDOFF', 1, len(BLOBS['P09_HANDOFF'].decode().splitlines())),
    evtext('P09_ACCEPTANCE', 1, len(BLOBS['P09_ACCEPTANCE'].decode().splitlines()))]
for r in csvrows('VERIFIED_SOURCES'):
    if r[3]['id'] in ['S04', 'S05', 'S10', 'S13']:
        CONTRACT_REFS.append(evrow('VERIFIED_SOURCES', r))

def ce(city, *ids):
    return [evrow(city + '_EVIDENCE', CITY[city][key]) for key in ids]

# Text is deliberately separate from author values. Market purposes are hypotheses.
CARDS = [
dict(pair='MOW-AER', name='Москва — Сочи', group='T1', stage='московский треугольник; календарь не утверждён',
 why='Большой существующий московско-сочинский рынок и первый участок замкнутого оборота T1.',
 payer='Отдых, семейные и деловые поездки: платит пассажир либо работодатель. Наличие курортного потока подтверждено; доли целей и корпоративные договоры не установлены.',
 competition='Автор фиксирует прямое сообщение, но не даёт полного списка перевозчиков на выбранном московском аэропорту. Полный датированный конкурентный продукт здесь не установлен.',
 own='В AER есть опубликованные собственные RW внутренние и международные продукты, включая отдельные московские строки; их продажи и ресурс надо сохранить в KEEP. Не считать весь поток новым.',
 role='Заводит самолёт из Москвы в AER перед AER–VOG; сквозную перевозку MOW–VOG через AER автоматически не предполагаем.',
 stop='Не запускать без выбора физического московского аэропорта, слотов и сравнения с существующими собственными продажами; положительный маршрутный вклад не покрывает автоматически базу и финансирование.',
 pitch='Москва — Сочи нужна как рынок поездок и первое плечо замкнутого треугольника. Исторический поток велик, но он относится ко всем перевозчикам и московским аэропортам. Автор получает плюс 51,7 миллиона в год при своих допущениях. Мы не обещаем эту прибыль: сначала выбираем аэропорт, проверяем конкурентов, собственные продажи и весь оборот.',
 refs=ce('AER','E-AER-001','E-AER-009','E-AER-016')),
dict(pair='AER-VOG', name='Сочи — Волгоград', group='T1', stage='московский треугольник; календарь не утверждён',
 why='Прямая региональная поездка к курорту без московской пересадки; соединяет южные вершины T1.',
 payer='Индивидуальные и семейные курортные поездки; обратный поток в Волгоград — отдельная гипотеза. Оплаченные турблоки и их размер неизвестны.',
 competition='Есть исторический первичный анонс Nordwind/Икар: среда и суббота, лето 2025. Пустой фильтр AER–VOG 12.11.2026 не доказывает отсутствия перевозки или будущего конкурента.',
 own='Отдельно учитывать RW marketing/codeshare на VOG–SVX с Y7 и исторические продукты VOG–MCX/SGC/BUS. Код WZ не доказывает собственный самолёт; роли и периоды проверяются для каждого продукта.',
 role='Коммерчески продаваемое межрегиональное плечо AER–VOG, затем самолёт возвращается в Москву.',
 stop='Не запускать по одному старому признаку no_direct: обновить календарь конкуренции и спрос. Не считать 90% авторской загрузки наблюдением или гарантией и не оставлять зимний спрос равным летнему.',
 pitch='Сочи — Волгоград продаёт прямую поездку к курорту и связывает два плеча треугольника. У автора это плюс 41,8 миллиона в год, но спрос здесь модельный. Нельзя говорить, что конкурентов нет: сохранён летний анонс Nordwind и Икара. Перед открытием нужны актуальный сезонный календарь, цена с багажом и проверка собственных продаж.',
 refs=ce('AER','E-AER-011','E-AER-014')+ce('VOG','E-VOG-03','E-VOG-09','E-VOG-10')),
dict(pair='VOG-MOW', name='Волгоград — Москва', group='T1', stage='московский треугольник; календарь не утверждён',
 why='Самостоятельный московский рынок Волгограда и возврат самолёта в исходный московский аэропорт.',
 payer='Деловые, семейные и личные поездки в столицу; inbound-туризм Волгограда — дополнительная проверяемая гипотеза. Доли и гарантированные продажи неизвестны.',
 competition='Зимний анонс VOG перечисляет SU/S7/DP на Москве; конкретные аэропорты и даты нужно развести. Неполный список не является оценкой общей ёмкости.',
 own='Сверить собственные/партнёрские продукты VOG через SVX и другие пункты. Нулевой migrated в авторской строке не доказывает нулевой собственный переток.',
 role='Замыкает T1. Участок у автора отрицателен; его целесообразность проверяется совместно с выгодой остальных участков и альтернативным возвратом.',
 stop='Не открывать как автономно прибыльную линию. Если общий оборот после KEEP, полного бюджета и ресурсов не выдерживает условия запуска/остановки, отрицательное плечо нельзя оправдать одним названием треугольника.',
 pitch='Волгоград — Москва замыкает первый оборот и продаёт собственный столичный рынок. Это слабое плечо: у автора минус 21,1 миллиона в год, хотя весь треугольник даёт плюс 72,4. Поэтому мы защищаем только совместную конструкцию. До запуска проверяем московский аэропорт, SU, S7, Победу и полные затраты; отдельной прибыли линии не обещаем.',
 refs=ce('VOG','E-VOG-05','E-VOG-03','E-VOG-09','E-VOG-10')),
dict(pair='MOW-GSV', name='Москва — Саратов', group='T2', stage='московский треугольник; календарь не утверждён',
 why='Вход самолёта в саратовскую вершину T2 и существующий рынок столица — регион.',
 payer='Личные, семейные и деловые поездки; корпоративные блоки не подтверждены. Короткое воздушное плечо требует сравнения всей поездки с наземным вариантом.',
 competition='P02 сохраняет SU и DP на SVO в сезонных правилах, а местный dossier также называет московские SVO/VKO и «Россию». Число правил нельзя сложить как недельную частоту.',
 own='В GSV уже есть RW–SVX, анонс TBS с 23.12.2026, история BUS летом 2026 и NUX в 2025. Их выручка и использование ресурса не равны нулю.',
 role='Подводит самолёт к GSV–MRV; закрывает путь MOW–GSV–MRV–MOW. Это отрицательное, а не самостоятельно окупаемое плечо авторской модели.',
 stop='Не запускать ради формального замыкания: подтвердить спрос, физический московский аэропорт, доступ к ресурсу и совместный результат после действующих продаж и полного бюджета.',
 pitch='Москва — Саратов подводит самолёт ко второму треугольнику и продаёт столичный рынок. У автора это минус 14,1 миллиона в год; прибыльной отдельной линией мы её не называем. Конкуренция уже есть, включая SU и Победу. Открытие допустимо только после проверки целого оборота, аэропорта Москвы и сохранения собственных саратовских продаж.',
 refs=ce('GSV','E-GSV-07','E-GSV-08','E-GSV-09','E-GSV-10')+[evtext('GSV_README',5,25)]),
dict(pair='GSV-MRV', name='Саратов — Минеральные Воды', group='T2', stage='московский треугольник; календарь не утверждён',
 why='Прямая связь Поволжья с Кавказскими Минеральными Водами; коммерческое среднее плечо T2.',
 payer='Санаторные и оздоровительные заезды, отдых, личные поездки. Платит путешественник, при договоре — туроператор/организация; контрактный объём не установлен.',
 competition='Полного датированного прямого предложения именно GSV–MRV в выбранных P02 строках нет. Это пробел покрытия. Альтернативы через другие узлы и наземный путь требуют сопоставимой даты; авторское «через Сочи» — модель.',
 own='Проверить замену собственных GSV–SVX/международных продуктов и затронутых собственных продаж в MRV. Санаторный поток всего края не добавлять к уже учтённому OD.',
 role='Соединяет Саратов с MRV перед возвратом в Москву; самостоятельная продажа пары, а не автоматически защищённый трансфер.',
 stop='Не открывать по туристическому итогу края или предположению свободной субсидии. Нужны конечные заявки, сезон заездов, датированный ресурс и экономика целого T2; субсидия строки base равна нулю.',
 pitch='Саратов — Минеральные Воды проверяем как прямой продукт для санаторных заездов и отдыха. Это главное положительное плечо второго треугольника у автора: плюс 44,7 миллиона в год. Но это модельный спрос, не договоры санаториев. Нужны конкретные даты заездов, конкурентные альтернативы и цена; субсидию или весь туристический поток края мы не присваиваем.',
 refs=ce('MRV','MRV-E13','MRV-E18','MRV-E19')+ce('GSV','E-GSV-08','E-GSV-09')),
dict(pair='MRV-MOW', name='Минеральные Воды — Москва', group='T2', stage='московский треугольник; календарь не утверждён',
 why='Возврат самолёта в Москву с продажей существующего курортного и столичного рынка.',
 payer='Санаторные, отпускные, личные и деловые поездки. Наличие рынка курортов поддержано источниками; распределение покупателей на этой паре неизвестно.',
 competition='Авторский direct_now=true показывает старую классификацию рынка. Полный датированный список перевозчиков и частот на выбранном московском аэропорту в этом пакете не подтверждён; свободную нишу не заявляем.',
 own='Восстановить существующие и продаваемые с пересадкой RW поездки из MRV и их потерянный вклад; отсутствие MRV в списке опорных аэропортов RW не означает отсутствия продаж.',
 role='Замыкает T2 в том же физическом московском аэропорту; запасы времени, ТО и смены экипажа отдельно.',
 stop='Не открывать на основании небольшого положительного вклада +9,8: он не доказывает покрытие полной базы, лизинга, финансирования и изменения тарифа под ответ конкурента.',
 pitch='Минеральные Воды — Москва возвращает самолёт в исходный аэропорт и продаёт курортный рынок. Авторский плюс здесь небольшой: 9,8 миллиона в год при включённых переменных расходах. Мы не называем это полной прибылью. Решение зависит от всего второго треугольника, выбранного аэропорта, конкурентного расписания и сохранения действующих собственных продаж.',
 refs=ce('MRV','MRV-E08','MRV-E18','MRV-E19')),
dict(pair='OMS-MOW', name='Омск — Москва', group='OMS', stage='предложение первой стабильной группы; даты/частоты не утверждены',
 why='Местная опора омской базы на крупном исторически наблюдаемом направлении; спрос не должен целиком зависеть от пересадок.',
 payer='Столичные личные, семейные и деловые поездки; платит пассажир либо организация. Источник не раскрывает цели и корпоративные доли.',
 competition='P02: опубликованные OMS–DME/SVO с U6, S7, FV, SU, DP на неделе 7–13.12.2026. Это выборка исходящих офферов, не текущая полная ёмкость в обе стороны.',
 own='Сохранить RW OMS–SVX и будущий KEEP. Новая прямая Москва может перетянуть собственные поездки через SVX; авторское migrated=0 это не опровергает.',
 role='Базовый вылет из OMS и возврат к OMS для дальнейшей работы. Общие волны с IKT/GOJ/VOG возможны только после подтверждения защищённой пересадки.',
 stop='Не открывать до выбора физического московского аэропорта и понятного преимущества по полной цене/времени поездки. 674175 — исторический поток направления всех перевозчиков, не продажи RW.',
 pitch='Омск — Москва предлагаем в первой стабильной группе как опору на существующий местный рынок. Аэропорт сообщил 674175 пассажиров направления за 2025 год, но это все перевозчики, не наши продажи. В сохранённом расписании уже есть несколько конкурентов. До запуска нужны физический аэропорт Москвы, понятный продукт и проверка перетока с собственных рейсов через Екатеринбург.',
 refs=ce('OMS','EV-OMS-S01','EV-OMS-S04','EV-OMS-S07','EV-OMS-S09')),
dict(pair='OMS-IKT', name='Омск — Иркутск', group='OMS', stage='предложение первой стабильной группы; даты/частоты не утверждены',
 why='Восточная линия омской базы с существующим прямым предложением; потенциальная опора для поездок запад — восток.',
 payer='Межрегиональные личные/семейные/рабочие поездки; туризм к Байкалу — гипотеза отдельного сезона, а не весь спрос пары. Контрактные объёмы неизвестны.',
 competition='S7 6452 OMS–IKT опубликован на 08 и 11.12.2026; сохранена также отдельная железнодорожная поездка. Это не отсутствие конкуренции; рейтинг S7 по всему IKT не доля на OMS–IKT.',
 own='Сверить собственные варианты через SVX и продажи других омских плеч. История RW NOZ–IKT и представитель в IKT не доказывают свободный борт или текущую частоту OMS–IKT.',
 role='Восточная оконечность OMS-ротаций; возможный стык с западными споками проверяется по конечным поездкам, не через сложение пассажиров плеч.',
 stop='Не назначать высокую частоту по среднему моделей: оценки автора расходятся в 9,84 раза. Нужны даты, цена, реакция S7 и зимняя регулярность; общий туристический итог IKT не замена OD.',
 pitch='Омск — Иркутск даёт восточное направление омской базы, но мы выходим на существующий рынок S7. В сохранённой декабрьской неделе опубликованы два её вылета. Авторские оценки спроса расходятся почти в десять раз, поэтому высокую частоту пока не утверждаем. Проверяем местные поездки, возможные стыки, цену и зимнюю регулярность до открытия линии.',
 refs=ce('OMS','EV-OMS-S07','EV-OMS-S17')+ce('IKT','E01','E03','E07','E08')),
dict(pair='OMS-GOJ', name='Омск — Нижний Новгород', group='OMS', stage='предложение первой стабильной группы; даты/частоты не утверждены',
 why='Прямая связь Омска с Нижним Новгородом вместо длинной поездки или пересадки; западный спок омской базы.',
 payer='Деловые, личные и семейные поездки; промышленный/IT/событийный рынок — механизм поиска покупателей, не доказанный блок мест. ЦИПР сам по себе не обосновывает круглогодичный рейс.',
 competition='Есть сохранённый датированный железнодорожный продукт. Отсутствие прямой авиастроки этой пары в P02 не доказывает отсутствие конкурента; сравнить пересадки через действующие узлы.',
 own='Маркетинговая страница RW уже перечисляет GOJ–OMS: прямой рейс, защищённость, даты и инвентарь из неё не следуют. Возможные собственные продажи через SVX включить в KEEP.',
 role='Западный вылет из OMS с возвратом в OMS. Пересадки на IKT возможны лишь после общего OD/capacity и достаточного наземного времени.',
 stop='Не открывать только под ЦИПР 31.05–03.06.2027 с новыми SJ-100 из H2: даты несовместимы. Для стабильной линии подтвердить обычные недели, цену и переток с собственного продукта.',
 pitch='Омск — Нижний Новгород предлагаем как западную межрегиональную линию базы. Деловые и семейные поездки здесь проверяем отдельно; модель не даёт наблюдаемого конечного спроса. Red Wings уже рекламирует эту пару, поэтому нельзя считать все продажи новыми. Сначала подтверждаем обычные недели, цену и собственный переток; один ЦИПР круглогодичную линию не обосновывает.',
 refs=ce('GOJ','GOJ-E10','GOJ-E18','GOJ-E20','GOJ-E36')),
dict(pair='OMS-VOG', name='Омск — Волгоград', group='OMS', stage='предложение первой стабильной группы; даты/частоты не утверждены',
 why='Прямая связь Сибири с Волгоградом без московского обхода; юго-западный спок омской базы.',
 payer='Личные/семейные поездки, inbound историко-патриотический туризм и рабочие поездки — проверяемые сегменты без установленных долей и договоров.',
 competition='Полной датированной прямой конкуренции пары в P02 нет; это неизвестность. Авторское «с пересадкой через Екатеринбург» — восстановленная модель маршрутизации, не наблюдение всех покупок.',
 own='У VOG есть RW marketing на Y7–SVX и история собственных/маркетинговых южных продуктов. Переход на прямую OMS–VOG может заменить собственные билеты и затронуть московские треугольники.',
 role='Юго-западное плечо OMS-ротации. VOG общий пункт с T1; это не доказательство согласованного интерлайна или бесплатного самолёта.',
 stop='Не открывать по одному авторскому положительному вкладу девятиспоковой сети. Проверить общий спрос, конкуренцию/кодшеринг, южную трассу и payload; авторский зелёный порог 2150 км не AFM-допуск.',
 pitch='Омск — Волгоград связывает Сибирь с юго-западом и входит в предлагаемую первую группу. Спрос пока восстановлен моделью, а не наблюдаемыми билетами. В Волгограде уже есть собственные и партнёрские продукты Red Wings, их нужно учесть. Перед открытием проверяем конкурентов, переток, южную трассу и загрузку; положительная строка старой сети решения не заменяет.',
 refs=ce('VOG','E-VOG-03','E-VOG-09','E-VOG-10','E-VOG-11')),
dict(pair='OMS-KUF', name='Омск — Самара', group='OMS', stage='предложение расширения после подтверждения ресурса; даты/частоты не утверждены',
 why='Связь Омска с Поволжьем и существующим опорным пунктом RW KUF; расширение после устойчивой первой группы.',
 payer='Межрегиональные личные, семейные и рабочие поездки. Промышленная география не равна договору; корпоративный спрос требует заявок/TMC.',
 competition='В P02 сохранён поезд 211Ы на 10.11.2026; местный dossier указывает 33,7 часа для этого примера. Нет полного покрытия прямых и пересадочных авиапредложений пары.',
 own='KUF — опорный пункт RW со своими продажами; прямой OMS–KUF может заменить варианты через SVX. Есть анонс кодшеринга RW/«Белавиа»: единый билет KUF–MCX–MSQ и прямой KUF–MSQ. Это существующий коммерческий контекст, не свободный ресурс SJ-100.',
 role='Дополнительный западный вылет OMS с возвратом; возможную совместимость с KUF-программами доказать календарём, не добавлением их лучших результатов.',
 stop='Не расширять до подтверждения самолёта, crew/ТО/резерва и сохранения стабильности первых четырёх пар. Коэффициент приоритета OMS в скидочном документе KUF не спрос и не гарантированная поддержка.',
 pitch='Омск — Самара предлагаем после подтверждения ресурса первой группы. Это связь с Поволжьем и действующим опорным пунктом Red Wings. Сохранённый пример поезда занимает 33,7 часа, но он не измеряет готовность платить за самолёт. Перед расширением нужны заявки, сопоставимая цена, учёт собственных пересадок и отдельный подтверждённый ресурс экипажей и обслуживания.',
 refs=ce('KUF','E-KUF-20','E-KUF-25','E-KUF-RAIL')+ce('OMS','EV-OMS-S07')),
dict(pair='OMS-GSV', name='Омск — Саратов', group='OMS', stage='предложение расширения после подтверждения ресурса; даты/частоты не утверждены',
 why='Прямая сибирско-волжская связь с меньшей модельной местной опорой; логичный кандидат второй группы, когда первая работает устойчиво.',
 payer='Личные, семейные и деловые поездки между Сибирью и Саратовом. Не называем весь поток вахтовым; оплаченные блоки и цель каждой поездки не установлены.',
 competition='Нет полного датированного покрытия прямой пары; старое направление через SVX — модель. Конкурентные хабы, наземный доступ до GSV и сезонную частоту надо проверить перед запуском.',
 own='GSV уже обслуживается RW: SVX, анонс TBS, история BUS и NUX. Эти продажи и общий ресурс могут пересекаться с T2 и OMS; не считать их новыми или складывать автономные результаты.',
 role='Дополнительный западный спок OMS. GSV общий пункт с T2, но стыковки и сквозной билет требуют отдельного календаря и договора.',
 stop='Не открывать без отдельного ресурса и проверки конечного спроса: в старой OMS-строке большая часть сегментов зависит от сетевых связей. Сеть из шести споков эту подпитку ещё не доказала.',
 pitch='Омск — Саратов оставляем во второй группе после подтверждения ресурса. Линия связывает Сибирь с Поволжьем, но её местная опора пока только модельная, а значительная часть старого результата зависит от сети. В Саратове уже есть продажи Red Wings. До открытия нужны конечный спрос, общий календарь с треугольником и сохранение существующего бизнеса.',
 refs=ce('GSV','E-GSV-08','E-GSV-09','E-GSV-10')+[evtext('GSV_README',5,25)]),
]

def pairkey(a, b):
    return frozenset((a, b))

ROUTES = csvrows('AUTHOR_ROUTES')
DEMAND = csvrows('AUTHOR_DEMAND')
PRODUCTS = csvrows('P02_PRODUCTS')
KNOWN = csvrows('P01_KNOWN')
MOS = {'MOW','SVO','DME','VKO','ZIA'}
def norm(code):
    return 'MOW' if code in MOS else code

VOG_REGISTRY = {r[3]['source_id']:r for r in csvrows('VOG_SOURCES')}
for card in CARDS:
    underlying = []
    for eid in card['refs']:
        if eid.startswith('VOG_EVIDENCE:'):
            for sid in EVIDENCE[eid]['original_row']['source_id'].split(';'):
                if sid in VOG_REGISTRY:
                    underlying.append(evrow('VOG_SOURCES',VOG_REGISTRY[sid]))
    card['refs'] = list(dict.fromkeys(card['refs']+underlying))

ASSUMPTIONS = []
for r in csvrows('AUTHOR_ASSUMPTIONS'):
    if r[3]['parameter'] in ['seats','capture_open','capture_competitive','capture_transfer','capture_freq_scale',
        'weeks_per_year','fare_fixed_rub','fare_per_km_rub','fuel_rub_per_t','fuel_compensation_rub_per_t',
        'season_on','season_amplitude','lf_peak_max','route_factor_south','spare_aircraft','fleet_cap']:
        ASSUMPTIONS.append(evrow('AUTHOR_ASSUMPTIONS', r))

passports, arithmetic, checks = [], [], []
for order, card in enumerate(CARDS, 1):
    a,b = card['pair'].split('-'); key=pairkey(a,b)
    variant = 'Хаб OMS' if card['group']=='OMS' else 'Прямые MOW-AER-VOG' if card['group']=='T1' else 'Прямые MOW-GSV-MRV'
    art = next(r for r in ROUTES if r[3]['scenario']=='base' and r[3]['variant']==variant and pairkey(r[3]['from'], r[3]['to'])==key)
    raw = art[3]
    hi, hr = next((i,r) for i,r in enumerate(D['net']['routes']) if r['scenario']=='base' and r['variant']==variant and pairkey(r['from'],r['to'])==key)
    csv_ev = evrow('AUTHOR_ROUTES', art)
    html_ev = evtext('AUTHOR_HTML', HTML_LINE, HTML_LINE, pointer='/D/net/routes/'+str(hi), value=hr)
    equal = all(str(raw[k]).lower()==str(hr[k]).lower() for k in ['from','to','scenario','variant','demand_source'])
    equal &= all(Decimal(raw[k])==Decimal(str(hr[k])) for k in ['revenue_mln_year','cost_mln_year','result_mln_year','freq_week_each_way','freq_week_winter','pax_year_local','pax_year_segments'])
    checks.append(dict(check='html_csv_projection:'+card['pair'], passed=equal))
    demand_row = next(r for r in DEMAND if pairkey(r[3]['a'],r[3]['b'])==key)
    demand_ev=evrow('AUTHOR_DEMAND',demand_row)
    pr=[r for r in PRODUCTS if pairkey(norm(r[3]['origin']),norm(r[3]['destination']))==key]
    # Preserve every matched primary record, including rail, instead of manufacturing frequencies.
    product_evs=[evrow('P02_PRODUCTS', r, 'GROUND_PUBLISHED_PRODUCT' if r[3]['physical_leg_status']=='ground_not_air' else 'PUBLISHED_PRODUCT') for r in pr]
    known=[evrow('P01_KNOWN',r) for r in KNOWN if pairkey(r[3]['from_iata'],r[3]['to_iata'])==key]
    refs=list(dict.fromkeys([csv_ev,html_ev,demand_ev]+card['refs']+product_evs+known))
    delta=Decimal(raw['revenue_mln_year'])-Decimal(raw['cost_mln_year'])-Decimal(raw['result_mln_year'])
    arithmetic.append(dict(pair=card['pair'], display_revenue=raw['revenue_mln_year'], display_cost=raw['cost_mln_year'],
        display_result=raw['result_mln_year'], revenue_minus_cost_minus_result_mln=str(delta),
        within_independent_0_1_rounding=abs(delta)<=Decimal('0.15')))
    wordcount=len(re.findall(r'[\w]+(?:[–—-][\w]+)*',card['pitch']))
    sec=round(wordcount/130*60,1)
    checks.append(dict(check='pitch_20_30s_at_130wpm:'+card['pair'],passed=20<=sec<=30,words=wordcount,estimated_seconds=sec))
    am=dict(hr)
    am.update(metric='Условный годовой вклад после включённых переменных расходов, не полная прибыль',
        period='Модельный сезонный год без конкретной датированной привязки к 2027 или 2028; base weeks_per_year=52',
        grain='Одна неориентированная пара, оба направления; from/to — подпись, не односторонний итог',
        source_evidence_ids=[csv_ev,html_ev], deployment_status='NOT_DISPATCH_READY_NOT_PILOT',
        transferability='OMS: контекст всей авторской девятиспоковой сети; T1/T2: внутри авторской прямой сети. Не прогноз консенсуса.',
        full_profit_mln_year=None, funding_need_rub=None, frequency_approved=False)
    dem = dict(demand_row[3])
    typed={k:(float(dem[k]) if dem[k] else None) for k in ['observed','segments_base','segments_cautious','od_base','od_cautious','own_trips_share','estimates_ratio','fare_ours_rub']}
    passports.append(dict(order=order,pair_id=card['pair'],city_pair_name=card['name'],group=card['group'],
        origin_label=a,destination_label=b,route_grain='unique_undirected_city_airport_pair',
        physical_moscow_airport=None if 'MOW' in key else 'NOT_APPLICABLE',
        stage_proposal=card['stage'],stage_is_approved_calendar=False,why=card['why'],
        payer_market=dict(text=card['payer'],data_type='ANALYST_MARKET_HYPOTHESIS',shares=None,contracted_volume=None,
            note='Источник подтверждает контекст/предложение, не цель каждого билета, платёжеспособность или гарантированный покупатель.'),
        competition=dict(text=card['competition'],coverage='INCOMPLETE_NOT_PROVEN_ABSENT',p02_matched_records=len(pr),
            dated_outbound_air_records=sum(r[3]['row_grain']=='dated_published_service' and r[3]['physical_leg_status']!='ground_not_air' for r in pr),
            evidence_ids=product_evs,matched_records_do_not_equal_unique_flights=True),
        own_sales=dict(text=card['own'],future_KEEP='UNKNOWN_NOT_ZERO',cannibalisation_observed=False),
        demand=dict(source_text_verbatim=raw['demand_source'],source_evidence_ids=[demand_ev]+known,
            author_values=typed,author_raw_fields=dem,
            observed_field_interpretation='Исторический сегментный поток всего рынка, если заполнен; не observed endpoint OD.',
            own_trips_share_interpretation='Модельная доля поездок с конечными пунктами этой пары в сегментном потоке; не доля рынка RW и не доля собственных продаж RW.',
            endpoint_od_observed=None,p05_status='SCENARIO_NOT_IDENTIFIED',
            fare_interpretation='fare_ours_rub — авторская параметрическая net-revenue оценка; не наблюдаемая котировка/цена клиента.',
            no_direct_interpretation='Старый source/model label сохранён буквально для происхождения; не утверждение отсутствия текущего конкурента.'),
        author_reference=am,rotation_role=card['role'],when_not_to_open=card['stop'],
        common_launch_gates=['physical_airports_and_slots','dated_tail_crew_MRO_reserve','same_period_future_KEEP',
            'endpoint_OD_and_choice_with_competitors','full_incremental_cost_cash_and_stop_conditions'],
        short_reply_20_30_seconds=card['pitch'],reply_words=wordcount,reply_seconds_at_130wpm=sec,
        reply_duration_status='ESTIMATE_NOT_AUDIO_MEASUREMENT',evidence_ids=refs))

def write_json(name, obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def showref(eid):
    e=EVIDENCE[eid];f=FILES[e['source_id']]
    r=' '+e.get('json_pointer','')
    return f"{f['commit'][:8]}:{f['path']}:{e['physical_line_start']}"+r

def number(n):
    return f'{n:,.0f}'.replace(',',' ')

def main():
    is_seal='--seal' in sys.argv
    expected_pairs={c['pair'] for c in CARDS}
    checks.extend([
        dict(check='12_unique_pairs',passed=len(passports)==len(expected_pairs)==12),
        dict(check='six_triangular_six_omsk',passed=sum(p['group']=='OMS' for p in passports)==6),
        dict(check='P09_exact_manifest',passed=FILES['P09_MANIFEST']['sha256']==P09_MANIFEST),
        dict(check='P09_engine_pin',passed=json.loads(BLOBS['P09_HANDOFF'])['engine_pin']==ENGINE),
        dict(check='P01_no_confirmed_endpoint_OD',passed=len(csvrows('P01_OD'))==0),
        dict(check='MOW_not_resolved_silently',passed=all(p['physical_moscow_airport'] is None for p in passports if 'MOW' in p['pair_id'])),
        dict(check='negative_legs_retained',passed=next(p for p in passports if p['pair_id']=='VOG-MOW')['author_reference']['result_mln_year']==-21.1 and next(p for p in passports if p['pair_id']=='MOW-GSV')['author_reference']['result_mln_year']==-14.1),
        dict(check='rounded_route_arithmetic',passed=all(x['within_independent_0_1_rounding'] for x in arithmetic)),
        dict(check='no_invented_market_purpose_shares',passed=all(p['payer_market']['shares'] is None and p['payer_market']['contracted_volume'] is None for p in passports)),
        dict(check='no_approved_frequencies_or_calendar',passed=all(not p['stage_is_approved_calendar'] and not p['author_reference']['frequency_approved'] for p in passports)),
        dict(check='six_triangle_rows_base_subsidy_zero_frequency_seven',passed=all(p['author_reference']['subsidy_mln_year']==0 and p['author_reference']['freq_week_each_way']==7 and p['author_reference']['freq_week_winter']==7 for p in passports if p['group']!='OMS')),
    ])
    tri=[]
    for group,wanted in [('T1','72.4'),('T2','40.4')]:
        ps=[p for p in passports if p['group']==group]
        actual=sum(Decimal(str(p['author_reference']['result_mln_year'])) for p in ps)
        ok=actual==Decimal(wanted) and all(Decimal(str(p['author_reference']['triangle_result_mln_year']))==Decimal(wanted) for p in ps)
        tri.append(dict(group=group,display_sum_mln_year=str(actual),author_triangle_mln_year=wanted,passed=ok))
        checks.append(dict(check='triangle_display_arithmetic:'+group,passed=ok))
    pp=csvrows('P01_PAIRS'); monthly=csvrows('P01_MONTHLY')
    matching_pairs=[r for r in pp if pairkey(r[3]['origin_code'],r[3]['destination_code']) in {pairkey(*s.split('-')) for s in expected_pairs}]
    checks.append(dict(check='P01_segment_coverage_not_endpoint',passed=not matching_pairs))
    evidence_refs=set(e for p in passports for e in p['evidence_ids'])|set(CONTRACT_REFS)|set(ASSUMPTIONS)
    checks.append(dict(check='all_evidence_resolves',passed=all(e in EVIDENCE for e in evidence_refs)))
    checks.append(dict(check='no_computed_network_forecast',passed=all(p['author_reference']['full_profit_mln_year'] is None for p in passports)))
    missing=[c for c in checks if not c['passed']]
    if missing:
        print(json.dumps(dict(status='DRAFT_CHECKS_FAILED',failures=missing),ensure_ascii=False,indent=2))
        if is_seal:
            raise SystemExit('Refuse seal: failed checks')
    limitations=[
        '12 пар — командный консенсус, не новый доказанный optimum; город не переоткрывается.',
        'MOW остаётся city aggregate; физический аэропорт, доступ, частоты и даты не утверждены.',
        'Первые OMS–MOW/IKT/GOJ/VOG и затем OMS–KUF/GSV — предложение последовательности root, не календарь и не подтверждение ресурсов.',
        'P01_MONTHLY: 0 подтверждённых endpoint_OD; 133 сегментные записи по другим парам и 86 месячных аэропортовых строк VVO/KJA не калибруют эти 12 OD.',
        'Цели поездок и плательщики — гипотезы, где нет сегментной выборки/договора. Ни долей, ни новых котировок не присвоено.',
        'Авторская модель f20000e7 сохранена отдельно от P09 fixed982/payload736859fd. P05 SCENARIO_NOT_IDENTIFIED.',
        'Авторские параметры: 100-местный SSJ-аналог, не подтверждённые будущие SJ-100/ПД-8 расходы/полётные характеристики.',
        'Результат строки = включённая чистая выручка (с поправками модели) минус переменные расходы; не full profit, не инвестиционный бюджет, не пилот.',
        'Топливо модели уменьшено на сценарную компенсацию; право, получение и кассовый срок возврата не подтверждены для будущих рейсов.',
        'Резерв, supply branches, ввод, crews/MRO, futureKEEP, полная база/лизинг/start/exit/cash требуют отдельного принятия P03/P04/P05/P06.',
        'Нельзя суммировать T1/T2 с OMS или P09. Ни прогноз общей сети, ни новая P&L здесь не создаются.',
        'Отсутствие строки/пустой фильтр/no_direct не доказывают отсутствия перевозки; WZ marketing и Y7 operating различаются.',
    ]
    payload=dict(schema_version='1.0',package='route_evidence',language='ru',as_of='2026-11-13',
        subject='Командный консенсус: T1 MOW–AER–VOG–MOW; T2 MOW–GSV–MRV–MOW; база OMS',
        card_count=12,limits=limitations,shared_contract_evidence_ids=CONTRACT_REFS,
        author_assumption_evidence_ids=ASSUMPTIONS,routes=passports,
        field_types=dict(pair_id='string;unique undirected pair label',physical_moscow_airport='string|null;null=UNKNOWN',
            author_reference='object;numbers are copied historical model outputs',
            demand_author_values='number|null;model value or historical aggregate as explicitly qualified',
            original_rows='string-valued source CSV records;empty preserved',
            payer_market='hypothesis;shares and contracted_volume null',
            evidence_ids='array[string];resolve against source_manifest.json.evidence',
            reply_seconds='number;estimated at 130 words/min, not observed'))
    write_json('route_passports.json',payload)
    fields=['pair_id','city_pair_name','group','stage_proposal','physical_moscow_airport_status','why','payer_market',
        'competition','own_sales','demand_source_verbatim','demand_value_types','author_segments_base','author_segments_cautious',
        'author_od_base','author_od_cautious','author_fare_model_rub','author_result_mln_year','author_freq_summer_each_way',
        'author_freq_winter_each_way','author_period_grain','rotation_role','when_not_to_open','short_reply_20_30_seconds','source_refs']
    with (OUT/'route_passports.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in passports:
            v=r['demand']['author_values'];a=r['author_reference']
            refs=[dict(evidence_id=eid,commit=FILES[EVIDENCE[eid]['source_id']]['commit'],path=FILES[EVIDENCE[eid]['source_id']]['path'],
                line_start=EVIDENCE[eid]['physical_line_start'],line_end=EVIDENCE[eid]['physical_line_end'],
                csv_data_record_1based=EVIDENCE[eid].get('csv_data_record_1based'),json_pointer=EVIDENCE[eid].get('json_pointer'),
                data_type=EVIDENCE[eid]['data_type']) for eid in r['evidence_ids']]
            w.writerow(dict(pair_id=r['pair_id'],city_pair_name=r['city_pair_name'],group=r['group'],stage_proposal=r['stage_proposal'],
                physical_moscow_airport_status='UNKNOWN' if r['physical_moscow_airport'] is None else 'NOT_APPLICABLE',why=r['why'],
                payer_market=r['payer_market']['text'],competition=r['competition']['text'],own_sales=r['own_sales']['text'],
                demand_source_verbatim=r['demand']['source_text_verbatim'],demand_value_types='AUTHOR_SCENARIO; observed=historical_segment_context_not_endpointOD; payer=HYPOTHESIS',
                author_segments_base=v['segments_base'],author_segments_cautious=v['segments_cautious'],author_od_base=v['od_base'],
                author_od_cautious=v['od_cautious'],author_fare_model_rub=v['fare_ours_rub'],author_result_mln_year=a['result_mln_year'],
                author_freq_summer_each_way=a['freq_week_each_way'],author_freq_winter_each_way=a['freq_week_winter'],
                author_period_grain=a['period']+'; '+a['grain'],rotation_role=r['rotation_role'],when_not_to_open=r['when_not_to_open'],
                short_reply_20_30_seconds=r['short_reply_20_30_seconds'],source_refs=json.dumps(refs,ensure_ascii=False,separators=(',',':'))))
    # Attach source registry rows for VOG evidence whose compact claims lack URLs.
    vog_source_ids=set(s for r in passports for e in r['evidence_ids'] if e.startswith('VOG_EVIDENCE:') for s in EVIDENCE[e]['original_row']['source_id'].split(';'))
    for r in csvrows('VOG_SOURCES'):
        if r[3].get('source_id') in vog_source_ids:evrow('VOG_SOURCES',r)
    write_json('source_manifest.json',dict(schema_version='1.0',acquisition='Only local exact Git blobs; no HTTP/browser/network collection',
        author_attribution='kiruha355 / Анастасия; exact f20000e7 as a separate author model',
        pins=dict(author=AUTHOR,city_and_P01=RESEARCH,P02v2=P02,P03v2=P03,P04final=P04,P09_payload=P09,P09_manifest_sha256=P09_MANIFEST,P09_engine=ENGINE,acceptance_envelope=ACCEPTANCE_PIN),
        files=list(FILES.values()),evidence=EVIDENCE,
        csv_line_convention='physical_line_start/end count actual newline-delimited lines; csv_data_record_1based excludes header, supports multiline fields',
        source_replay='git show <commit>:<path>; compare raw UTF8 byte SHA256; use saved record number/JSON pointer',
        observation_coverage=dict(endpoint_od_rows=len(csvrows('P01_OD')),airport_monthly_rows=len(monthly),
            airport_monthly_airports=sorted(set(r[3]['airport_iata'] for r in monthly)),
            segment_observations=len(pp),segment_matches_to_consensus_12=len(matching_pairs)),
        moscow_evidence_rule='SVO/DME/VKO/ZIA may be grouped as MOW only to locate city-market competitor evidence; original airports stay in records. No selected physical project airport inferred.',
        inclusion_note='Raw excerpts/records retained with original types/status and source URLs. URLs are provenance; no live refresh performed.'))

    intro='''# 12 линий: ответы экспертам

Закреплённый консенсус команды: **MOW–AER–VOG–MOW**, **MOW–GSV–MRV–MOW** и **база Омск**. Город не пересматриваем. MOW — пока совокупность московских аэропортов; физический аэропорт, частоты и даты не подтверждены. Для замкнутого оборота нужен возврат в тот же физический аэропорт, подтверждённые самолёты, экипажи, ТО и резерв.

Предложение последовательности по Омску: сначала стабильные OMS–MOW/IKT/GOJ/VOG; OMS–KUF/GSV — после подтверждения ресурса. Это последовательность для обсуждения, не утверждённый календарь и не новый optimum. При частичных/задержанных/нулевых поставках состав этапов проверяется заново; новые SJ-100 не назначаем раньше H2 2027. Действующий SSJ100 и будущий SJ-100/ПД-8 различаем.

**Как отвечать про деньги.** Авторская версия kiruha355 `f20000e7`, `D.net.routes`, `scenario=base`: T1 = **+51,7 +41,8 −21,1 = +72,4 млн ₽/модельный год**; T2 = **−14,1 +44,7 +9,8 = +40,4**. На каждом из шести участков — 7 рейсов **в каждую сторону** в неделю и летом, и зимой. Это исходные модельные частоты, не предложение пилота. Строки учитывают оба направления. «Замкнутый» описывает последовательность городов; датированные ротации этим не доказаны.

Деньги — выручка минус **включённые переменные расходы**: топливо с модельным вычетом компенсации, часовые ТО/экипаж/навигация, ground, deicing и пассажирские расходы. Полный лизинг, база, запуск/выход и финансирование этими плюсами не доказаны; выплаты компенсации тоже не подтверждены. В шести строках base субсидия = 0. Округлённые выручка и расходы могут расходиться с округлённым итогом на 0,1 млн: VOG–MOW 409,6−430,8=−21,2, при исходном результате −21,1; это сохранённое независимое округление, не исправление модели.

**Как отвечать про спрос.** В P01_MONTHLY нет подтверждённых конечных OD; годовой аэропортовый поток, места в расписании, восстановленные поездки и продажи RW — разные данные. Цели поездок ниже — гипотезы без выдуманных долей, цен и контрактов. Полные конкуренты/инвентарь 2027–2028 неизвестны. `no_direct` и пустой фильтр не означают отсутствия перевозчика. Полные исходные значения, периоды, типы, SHA256, номера записей/строк и URL — в JSON/CSV и source_manifest.

P09 — отдельная совместная модель OD/capacity: payload `736859fd`, engine `982f13d9`, manifest `7b20a1a…`, P05 `SCENARIO_NOT_IDENTIFIED`. Она допущена к условному показу, без принятия рынка/dispatch/инвестиций. **Результаты T1/T2 не складываем с Омском или P09.** Омские числа автора относятся к прежней сети из девяти споков; выбранные шесть не наследуют весь её спрос и результат. Новая общая сеть/P&L здесь не рассчитана.

'''
    source_text=(OUT/'source_manifest.json').read_text()
    source_lines=source_text.splitlines()
    evidence_line={eid:next(i for i,line in enumerate(source_lines,1) if line.startswith('    '+json.dumps(eid)+': {')) for eid in EVIDENCE}
    parts=[intro]
    parts.append(f"[Карточки JSON]({OUT/'route_passports.json'}) · [Таблица CSV]({OUT/'route_passports.csv'}) · [Источники и контрольные суммы]({OUT/'source_manifest.json'}) · [Проверки]({OUT/'verification.json'})\n\n")
    for r in passports:
        a=r['author_reference'];v=r['demand']['author_values'];sg='+' if a['result_mln_year']>=0 else ''
        parts.append(f"## {r['order']}. {r['city_pair_name']} ({r['pair_id']})\n\n")
        parts.append(f"**Зачем и кто платит.** {r['why']} {r['payer_market']['text']}\n\n")
        parts.append(f"**Рынок и свои продажи.** {r['competition']['text']} {r['own_sales']['text']}\n\n")
        if r['group']!='OMS':
            result=f"{sg}{a['result_mln_year']:.1f}".replace('.',',')
            parts.append(f"**Числа автора.** {result} млн ₽/модельный год; {number(a['pax_year_segments'])} сегментов в обе стороны; загрузка {a['load_factor']:.0%}. Это расчёт, не наблюдение. ")
        else:
            parts.append('**Основание спроса.** ')
        if v['observed'] is not None:
            parts.append(f"Историческое направление 2025: {number(v['observed'])} сегментных обслуживаний всего рынка; модельная доля конечных поездок — допущение.\n\n")
        else:
            parts.append(f"Старая оценка сегментного масштаба пары: база {number(v['segments_base'])}, осторожно {number(v['segments_cautious'])} в год; не наблюдаемый конечный OD. ")
            if r['pair_id']=='OMS-IKT':parts.append('Оценки расходятся в 9,84 раза; авторская годовая оценка по одной зимней неделе не принимается за наблюдение. ')
            if r['pair_id']=='AER-VOG':parts.append('Исходный label «авиамаршрута нет» не доказывает отсутствие перевозки; летний конкурент отдельно сохранён. ')
            parts.append('\n\n')
        parts.append(f"**Оборот и граница запуска.** {r['rotation_role']} {r['when_not_to_open']}\n\n")
        parts.append(f"**Реплика, около 20–30 секунд.** «{r['short_reply_20_30_seconds']}»\n\n")
        refs=[r['evidence_ids'][0],r['demand']['source_evidence_ids'][0]]
        cityrefs=[e for e in r['evidence_ids'] if '_EVIDENCE:' in e]
        refs+=cityrefs[:2]
        parts.append('Источники: '+ '; '.join(f"[{EVIDENCE[e]['source_id']}, запись {EVIDENCE[e].get('csv_data_record_1based','JSON')}]({OUT/'source_manifest.json'}:{evidence_line[e]})" for e in refs)+'.\n\n')
    parts.append('## Что запросить при подготовке запуска\n\n')
    parts.append('Физический аэропорт Москвы и слоты; датированные борта/экипажи/ТО/резерв при четырёх ветвях поставок; будущий KEEP и продажи по купонам; конечные заявки и одинаковая тарифная корзина конкурентов; договорные расходы, cash и условия остановки. Допустимый начальный убыток требует согласованного финансирования и проверяемого механизма улучшения. Нехватка этих данных означает условность запуска, а не экономическое опровержение линии.\n\n')
    parts.append('Пакет подготовлен только по локальным закреплённым источникам. Он служит подготовке к вопросам экспертов; рынок, новый общий результат и готовность рейсов не объявлены доказанными.\n')
    (OUT/'README.md').write_text(''.join(parts),encoding='utf-8')
    verification=dict(status='PASS' if not missing else 'DRAFT_CHECKS_FAILED',scope='Source integrity, projection equality, displayed arithmetic, completeness and declared limits only',
        checks=checks,checks_passed=sum(c['passed'] for c in checks),checks_total=len(checks),route_arithmetic=arithmetic,
        triangle_arithmetic=tri,rounding_note='Each revenue/cost/result independently rounded to0.1m; abs error<=0.15m is compatible with independent rounding, not independent market validation.',
        p09_manifest_sha256_actual=FILES['P09_MANIFEST']['sha256'],
        independent_new_market_audit='NOT_RUN_NOT_REQUESTED',model_execution='NOT_RUN',
        no_forecast_or_PnL_generated=True,external_effects=dict(git_writes=0,children=0,paid_calls=0,messages=0,bookings=0,servers=0,restarts=0,web_search=0),
        reply_timing='130 words/min estimate; no audio measurement',sealed=is_seal and not missing)
    write_json('verification.json',verification)
    handoff=dict(status='SEALED_STOP' if is_seal and not missing else 'DRAFT',created_at_utc=datetime.now(timezone.utc).isoformat(),
        entrypoint='README.md',route_count=12,groups=dict(T1=['MOW-AER','AER-VOG','VOG-MOW'],T2=['MOW-GSV','GSV-MRV','MRV-MOW'],
            OMS_first_proposed=['OMS-MOW','OMS-IKT','OMS-GOJ','OMS-VOG'],OMS_resource_gated_proposed=['OMS-KUF','OMS-GSV']),
        intended_use='Конечный компактный evidence/reply пакет для вопросов экспертов.',
        headline_findings=['VOG–MOW −21.1 и MOW–GSV −14.1 не автономно прибыльны; T1 +72.4/T2 +40.4 — отдельные авторские условные годовые результаты.',
            'AER–VOG: исторический Nordwind/Икар S25 против старого no_direct; W26/27 UNKNOWN. VOG–SVX marketing WZ/operatingY7 — другая пара; не считать WZ собственным SSJ.',
            'GSV: существующие/объявленные RW международные TBS/BUS и SVX/NUX история учитываются в ownsales; не свободный рынок/ресурс.',
            'OMS–MOW: 674175 сегментных обслуживаний направления в2025 не RW/OD; OMS–IKT конкурент S7 и расхождение оценок9.84×.',
            'OMS–GOJ: собственная маркетинговая пара уже есть; новые самолётыH2необслуживаютЦИПРMay/Jun2027.',
            'P01_OD0; P09_SCENARIO_NOT_IDENTIFIED. Frequencies/MOWphysical/datedresources/fullprofit remain UNKNOWN.'],
        limitations=limitations,author_arithmetic='verification.json',source_of_truth='source_manifest.json',
        coordinator_questions_nonblocking=['Какой физический московский аэропорт и какие частоты будут закреплены? Карточки оставляют UNKNOWN; это не блокирует данный пакет.'],
        no_next_audit=True,stop_after_sealing=True,git_writes=0,children=0,write_boundary=str(OUT),
        reproduction='PYTHONDONTWRITEBYTECODE=1 python3 '+str(OUT/'build_package.py')+' --seal')
    write_json('handoff.json',handoff)
    files=[]
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name!='output_manifest.json':
            b=path.read_bytes();files.append(dict(path=path.name,bytes=len(b),sha256=sha(b)))
    write_json('output_manifest.json',dict(package='route_evidence',status=handoff['status'],path_base=str(OUT),
        files=files,file_count=len(files),bytes=sum(f['bytes'] for f in files),
        excludes=['output_manifest.json (self-reference avoided)'],
        payload_sha256=sha(canon(files)),write_scope='Only this directory; git writes0; children0',
        checks='verification.json; provenance/arithmetic only; not market or dispatch acceptance'))
    print(json.dumps(dict(status=handoff['status'],routes=len(passports),files=len(files)+1,
        checks_passed=verification['checks_passed'],checks_total=len(checks),failures=missing,
        bytes=sum(f['bytes'] for f in files),manifest_sha256=sha((OUT/'output_manifest.json').read_bytes())),ensure_ascii=False))

if __name__=='__main__':main()
