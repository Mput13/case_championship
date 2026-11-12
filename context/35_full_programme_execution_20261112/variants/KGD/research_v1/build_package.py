#!/usr/bin/env python3
"""Сборка локального Stage A. Только stdlib; запись только рядом со скриптом."""
import csv
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import subprocess
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent
ASOF = '2026-11-12'
OWNER = 'исследователь KGD, Sol 6.1 xhigh'

def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def write_csv(name, rows):
    assert rows, name
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

class Extract(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip = 0; self.text = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip = max(0, self.skip - 1)
    def handle_data(self, data):
        if not self.skip and data.strip(): self.text.append(data.strip())

receipts = json.loads((ROOT / 'sources/receipts.json').read_text())
for r in receipts:
    p = ROOT / 'sources' / (r['source_id'] + '.html')
    if p.exists() and r['status'] == 'FETCHED':
        parser = Extract(); parser.feed(p.read_text())
        text = '\n'.join(parser.text)
        (p.with_suffix('.txt')).write_text(text)
        if len(text) < 100:
            r['status'] = 'NO_SUBSTANTIVE_TEXT'; r['limitation'] = 'HTTP 200 не подтверждает получение содержимого'
write_json('sources/receipts.json', receipts)

# Убираются только созданные этим пакетом пустые extracts и дубли soft block.
pins = json.loads((ROOT / 'source_pins.json').read_text())
for r in pins['files']:
    if r.get('selected_rows') == 0 and r.get('local_path'):
        (ROOT / r.pop('local_path')).unlink(missing_ok=True)
        r['selection_result'] = 'Нет KGD-строк; это пробел покрытия, не нулевой рынок'
for r in receipts:
    if r['status'] == 'ANTI_BOT_HTML_NO_CONTENT':
        for ext in ('.html', '.txt'):
            (ROOT / 'sources' / (r['source_id'] + ext)).unlink(missing_ok=True)
        r['raw_retained'] = False
        r['limitation'] = 'Получен один и тот же JS/anti-bot HTML вместо страницы/PDF; сохранён receipt/hash, чисел из него нет'
write_json('sources/receipts.json', receipts)
lineage = json.loads((ROOT / 'inputs/PLAN_KGD_lineage.json').read_text())
pins['files'].append({'source_id':'PIN-PLAN-lineage','commit':lineage['commit'],'path':lineage['path'],'sha256':lineage['sha256'],'local_path':'inputs/PLAN_KGD_lineage.json','selection':'только C25 и исторический треугольник с KGD'})
write_json('source_pins.json', pins)
for local in ('P00R_local_context.json','FIVE_local_context.json'):
    q=ROOT/'inputs'/local
    if q.exists():
        item=json.loads(q.read_text())
        pins['files'].append({k:item[k] for k in ('source_id','commit','path','sha256')} | {'local_path':'inputs/'+local,'selection':'выбранные строки с исходными номерами; см. selected_lines'})

sources = []
def source(sid, url, org, date, period, grain, unit, coverage, status='ПРОЧИТАНО', locator='', note=''):
    rr = next((x for x in receipts if x['source_id'] == sid), {})
    sources.append(dict(source_id=sid, url=url, organisation=org, publication_date=date,
        source_period=period, as_of=ASOF, retrieved_at=rr.get('retrieved_at', ASOF),
        granularity=grain, units=unit, coverage=coverage, status=status,
        retrieval_status=rr.get('status','web search/open: текст прочитан; raw PDF не получен'),
        raw_sha256=rr.get('sha256','UNKNOWN'), source_locator=locator, limitation=note))

source('RW_DME2025','https://flyredwings.com/press/news/red-wings-otkryla-ezhednevnye-rejsy-iz-moskvy-v-kaliningrad/', 'АО Ред Вингс','2025-06-26','с 2025-07-25; смена 2025-09-08','публикация о маршруте DME–KGD','рейсы/неделю; минуты','история одного направления',locator='абзацы после даты; сохранён HTML',note='Это анонс 2025, не исполнение всех дат и не KEEP 2027–2028; тип на конкретном рейсе не указан')
source('RW_BOARD','https://flyredwings.com/flight-board/?target=form','АО Ред Вингс',ASOF,'2026-11-12','табло; отдельный рейс/дата','местные часы; статус','выбранные KGD-рейсы одной даты',locator='WZ 901; WZ 4591; время обновления 15:55',note='Без регистрации борта/номера физического leg; тот же номер на другой дате не отождествлять')
source('RW_KGD','https://flyredwings.com/directions/kaliningrad/','АО Ред Вингс','UNKNOWN',ASOF,'динамическая витрина направлений','RUB/поездку, от','снимок страницы; не полная сеть',locator='сохранён raw: Санкт-Петербург от 3870 RUB',note='Web-cache показывал ZIA от11230, поисковый фрагмент SVX от11595, raw LED от3870. Разные срезы; ни один не принят как датированная цена/полнота сети')
source('KGD_SUMMER2025','https://kgdavia.ru/mediacenter/news/5306981/','АО Аэропорт Храброво','2025-03-31','2025-03-30/2025-10-25','летняя программа; перевозчик/направление','направления; рейсы/день','план лето2025; прямые и пересадочные продукты различены',locator='web open строки54–67',note='Raw HTTP anti-bot; факты прочитаны через web open. Не продлено на2026/2028')
source('KGD_HOME','https://kgdavia.ru/','АО Аэропорт Храброво',ASOF,'2026-11-12','онлайн-табло','рейс/дата/тип','часть табло на момент чтения',locator='web open FV6334/SU6334; FV6662/SU6662; SM926',note='Коды SU/FV одной даты/времени не два физических рейса; Superjet обозначен семейством, не ПД8')
source('KGD_TECH',next(r['url'] for r in receipts if r['source_id']=='KGD_TECH'),'АО Аэропорт Храброво','UNKNOWN','публичное описание; дата редакции UNKNOWN','аэропорт/инфраструктура','m; пассажиры/час; минуты','физические характеристики/описание возможностей',locator='web PDF text строки0–43',note='В тексте CATII, в таблице ICAO1; требуются актуальные AIP/NOTAM. Все типы ВС в буклете не допуск конкретного варианта/веса')
source('KGD_FORM2023',next(r['url'] for r in receipts if r['source_id']=='KGD_FORM2023'),'АО Аэропорт Храброво','UNKNOWN','2023-03-26/2023-10-28','форма9в-1; аэропорт','операции/час; пассажиры/час; PCN','исторические нормативы',locator='web PDF text таблицы1–2',note='Не свободная ёмкость/стоянки на дату2026; описание PCN не заменяет расчёт нагрузок')
source('KGD_TARIFF_INDEX','https://kgdavia.ru/partners/airlines/services/','АО Аэропорт Храброво','UNKNOWN','выпуск с 2026-08-01','индекс прайс-листов/скидок','дата действия; наличие документа','найден действующий по индексу выпуск для РФ',locator='web open строки34–41,149',note='Индекс прочитан; ставки и условия скидок не прочитаны и остаются UNKNOWN')
source('KGD_TARIFF202608',next(r['url'] for r in receipts if r['source_id']=='KGD_TARIFF202608'),'АО Аэропорт Храброво','UNKNOWN','с 2026-08-01','прайс; содержимое не получено','UNKNOWN','имя/URL выпуска','НАЙДЕН_НЕ_ПРОЧИТАН',note='HTTP200 с anti-bot HTML. Не использован старый2022 прайс как современная ставка; будущие ставки UNKNOWN')
source('KGD_DOCS','https://kgdavia.ru/partners/airlines/Docs/','АО Аэропорт Храброво','UNKNOWN',ASOF,'индекс типовых договоров','документ','типовой АиНО; не подписанный RW договор',locator='web open строки34–36',note='Наличие оферты не контракт/доступ RW; содержание docx не прочитано')
source('KGD_TG_JUN2025','https://t.me/kgdavia/753','АО Аэропорт Храброво','2025-07-08','2025-06; январь–июнь2025','агрегат аэропорта/месяц','обслуженные пассажиры','все перевозчики; прибытия/отправления; не OD',locator='sources/KGD_TG_JUL2025.html data-post kgdavia/753',note='Компоненты июня расходятся с итогом на200; компоненты полугодия с итогом на90; до исправления не calibration')
source('KGD_TG_JUL2025','https://t.me/kgdavia/764','АО Аэропорт Храброво','2025-08-08','2025-07; январь–июль2025','агрегат аэропорта/месяц','обслуженные пассажиры','все перевозчики; не уникальные поездки',locator='sources/KGD_TG_JUL2025.html data-post kgdavia/764',note='Июль 641908 сходится по компонентам; июльское накопление минус июньское не равно июлю на90')
source('KGD_ANNUAL_MILESTONE',next(r['url'] for r in receipts if r['source_id']=='KGD_ANNUAL_MILESTONE'),'Новый Калининград со ссылкой на пресс-службу аэропорта','2025-12-29','2025-01-01/2025-12-29','накопленный рубеж; не итог года','пассажиры аэропорта','5000000-й пассажир к29декабря',locator='заголовок и основной текст',note='Нижняя граница накопленного, не точный итог2025 и не5000000 потенциальных поездок')
source('KGD_TOUR_ATOR2025',next(r['url'] for r in receipts if r['source_id']=='KGD_TOUR_ATOR2025'),'Ассоциация туроператоров России','2025-03-26','лето2025','наблюдения опрошенных туроператоров/отелей','сезон; ночи тура','организованный пляжный/экскурсионный отдых',locator='основной текст',note='Выборка не весь авиарынок и не гарантированные RW группы; цены размещения не авиатарiff')
source('ROSSTAT_TOUR','https://39.rosstat.gov.ru/publications_2/document/292082','Калининградстат','2026-10; день UNKNOWN','2025','региональные турфирмы; отправленные клиенты','человек; турпакеты','91.8тыс зарубежных клиентов турфирм, не airportOD','ПОИСКОВЫЙ_ФРАГМЕНТ',locator='web search: Деятельность туристических фирм в2025',note='Полная страница недоступна (timeout/SSL EOF); ограниченный сигнал для P08I, не размер доступного RW спроса')
source('KGD_TOUR_2026',next(r['url'] for r in receipts if r['source_id']=='KGD_TOUR_2026'),'Интерфакс Россия; слова руководителя ТИЦ','2026-07-22; обновлено2026-07-23','первое полугодие2026','сообщённое изменение обращений/турпотока','проценты год-к-году','цитата ТИЦ; охват общей оценки не установлен','ПРОЧИТАНО_WEB',note='Не превращать -11% консультаций/индикатора в -11% всех конечных авиапоездок. Прямой HTTP дал JS-страницу')
source('KGD_TOUR_RAIL',next(r['url'] for r in receipts if r['source_id']=='KGD_TOUR_RAIL'),'Региональный туристический информационный центр','UNKNOWN',ASOF,'справка о ж/д поездке/транзите','документы; сроки','наземная альтернатива с транзитными условиями',locator='раздел про УПД ЖД',note='Не актуальный полный билет/время/вся международная правовая экспертиза. Положения2027–2028 обновить')
source('SMART_KGD','https://flysmartavia.com/destinations-daily/?origin=KGD','Smartavia','динамическая страница',ASOF,'витрина направления/дата/минимальная цена','RUB/человек/одно направление','10 продуктов на витрине; прямота/багаж не установлены',locator='raw HTML и извлечённый текст',note='Цены ориентировочные, включая сборы, не оферта; ограниченные места; web-cache и raw различаются. Год даты вылета не отображён')
source('KGD_MRO_PLAN2021',next(r['url'] for r in receipts if r['source_id']=='KGD_MRO_PLAN2021'),'РБК; заявления Новапорта','2021-02-19','план2021','план центра обслуживания SSJ','план объекта','историческое намерение',locator='основной текст',note='Никакого подтверждения ввода/сертификата/доступности RW2026 или SJ100/ПД8; сумму2021 не переносить в запуск2027')
write_json('sources.json', {'as_of':ASOF,'sources':sources,'boundary':'Факт из web open с недоступным raw помечен отдельно. Ненайденное и недоступное не равно отсутствию.'})
SM = {r['source_id']:r for r in sources}

evidence=[]
def ev(eid,sid,claim,value='UNKNOWN',units='текст',period=None,grain=None,status='ПОДТВЕРЖДЕНО_В_ОБЛАСТИ_ИСТОЧНИКА',limit=''):
    s=SM.get(sid,{})
    evidence.append(dict(evidence_id=eid,source_id=sid,claim=claim,value=value,units=units,period=period or s.get('source_period','2027–2028'),granularity=grain or s.get('granularity','строка закреплённого входа'),coverage=s.get('coverage','KGD-only extract; исходное ограничение сохранено'),status=status,url=s.get('url','git:'+sid),organisation=s.get('organisation','закреплённые входы команды'),source_date=s.get('publication_date',ASOF),as_of=ASOF,source_locator=s.get('source_locator','source_pins.json; inputs/'),limitation=limit or s.get('limitation','')))

ev('E-KGD-01','RW_DME2025','Объявлен DME–KGD: ежедневно с25июля, пт/сб/вс с8сентября2025', '7→3','рейсы/неделю в каждом направлении')
ev('E-KGD-02','RW_DME2025','Опубликована продолжительность прямого рейса','170','минут')
ev('E-KGD-03','RW_BOARD','12ноября WZ901 LED→KGD показан выполненным; план LED08:55, факт09:09→KGD09:52','1','наблюдение рейса','2026-11-12')
ev('E-KGD-04','RW_BOARD','12ноября WZ4591 KGD→SVO показан выполненным; KGD11:32→SVO14:39','1','наблюдение рейса','2026-11-12')
ev('E-KGD-05','RW_KGD','Raw витрина KGD показывает LED от3870; дата вылета/багаж отсутствуют','3870','RUB/поездку, рекламный минимум',status='ВИТРИНА_НЕ_ДАТИРОВАННЫЙ_ЧЕК')
ev('E-KGD-06','KGD_SUMMER2025','Nordwind назван базовым перевозчиком Храброво; это не утверждение о базе RW','Nordwind','роль перевозчика')
ev('E-KGD-07','KGD_SUMMER2025','Опубликованы пересадки Nordwind через KZN в BAX/UUD/MCX/OMS/KJA/KEJ/DYU','7','пересадочных направлений из перечня')
ev('E-KGD-08','KGD_SUMMER2025','Планируется12 перевозчиков,29 направлений,3 международных','12;29;3','перевозчики; направления')
ev('E-KGD-09','KGD_SUMMER2025','Москва разделена на VKO/DME/SVO; до28 рейсов/день суммарно, LED до15','28;15','плановые рейсы/день',limit='Это максимум плана сезона2025, не фактический/проданный объём; MOW нельзя подставлять как аэропорт')
ev('E-KGD-10','KGD_SUMMER2025','Опубликованы Минск, Хургада, Шарм-эш-Шейх','MSQ;HRG;SSH','международные endpoints')
ev('E-KGD-11','KGD_HOME','Табло KGD показывает Superjet у России на LED/SVO; SU/FV совпадающих времени не суммировать','Superjet','семейство ВС/рейс/дата',period='2026-11-12',limit='Подтверждение отображённого типа; не точная модификация/ёмкость и не ПД8')
ev('E-KGD-12','KGD_TECH','Опубликованы размеры ВПП','3350×45','m')
ev('E-KGD-13','KGD_TECH','Опубликована часовая терминальная способность:850 внутренних+400 международных','1250','пассажиры/час',limit='Норматив/описание; не свободные места в пике/слоты2028')
ev('E-KGD-14','KGD_TECH','Багажная система описана как способная обрабатывать трансферный багаж','да','возможность инфраструктуры',limit='Не MCT/through-check/защита стыковки RW или соглашение с партнёром')
ev('E-KGD-15','KGD_TECH','Описание заявляет разворот от30мин для большинства ВС','30','минут; нижняя опубликованная точка',limit='Не нормированный turn конкретного SSJ/SJ/RW; в рабочих кандидатах не принят как гарантированный')
ev('E-KGD-16','KGD_TECH','CATII в тексте и ICAO1 в таблице не согласованы','UNKNOWN','актуальная категория','редакция UNKNOWN',status='КОНФЛИКТ_ИСТОЧНИКА')
ev('E-KGD-17','KGD_FORM2023','Историческая форма9в-1: ВПП16 операций/час; терминал1250пасс/час','16;1250','операции/час; пассажиры/час',limit='Данные2023 не свободная ёмкость2028; поле29 у перрона не доступные RW стоянки')
ev('E-KGD-18','KGD_TARIFF_INDEX','В индексе тарифов выпуск РФ с01.08.2026 и положение о скидках','2026-08-01','дата выпуска')
ev('E-KGD-19','KGD_TARIFF202608','Ставки сбора/стоянки/базирования/топлива не извлечены','UNKNOWN','RUB/драйвер',status='ДОКУМЕНТ_НЕ_ПОЛУЧЕН')
ev('E-KGD-20','KGD_DOCS','Опубликован типовой договор АиНО; подписанный RW договор не установлен','UNKNOWN','доступ RW',status='ТИПОВОЙ_ДОГОВОР_НЕ_КОНТРАКТ_RW')
ev('E-KGD-21','KGD_TG_JUN2025','Июнь: итог542375; внутренние532180; международные10395','542375;532180;10395','пассажиры аэропорта',status='НАБЛЮДЕНИЕ_С_АРИФМЕТИЧЕСКИМ_КОНФЛИКТОМ')
ev('E-KGD-22','KGD_TG_JUL2025','Июль: итог641908=631249+10659','641908','пассажиры аэропорта')
ev('E-KGD-23','KGD_ANNUAL_MILESTONE','К29декабря2025 обслужен5000000-й пассажир','5000000','накопленный рубеж аэропорта',status='НИЖНЯЯ_ГРАНИЦА_НАКОПЛЕНИЯ_НЕ_ИТОГ_ГОДА')
ev('E-KGD-24','KGD_TOUR_ATOR2025','Туроператоры подтверждают пляжный/экскурсионный продукт и короткий купальный сезон, середина июля–конец августа','UNKNOWN','месячная OD',status='КАЧЕСТВЕННЫЙ_СЕЗОННЫЙ_СИГНАЛ')
ev('E-KGD-25','ROSSTAT_TOUR','Фрагмент Калининградстата:91.8тыс зарубежных клиентов турфирм; Египет45.8тыс,Турция25.1тыс','91800;45800;25100','отправленные турфирмами клиенты за2025',status='ФРАГМЕНТ_НЕ_ПРИНЯТ_КАК_OD')
ev('E-KGD-26','KGD_TOUR_2026','ТИЦ сообщил о снижении показателя первого полугодия2026 примерно на11%','-11','проценты год-к-году',status='ОГРАНИЧЕННЫЙ_ИНДИКАТОР_НЕ_ОБЩИЙ_СПРОС')
ev('E-KGD-27','KGD_TOUR_RAIL','Ж/д альтернатива требует отдельного транзитного документа/условий; это не обычный внутренний поезд','UNKNOWN','обобщённая стоимость/время поездки',limit='Актуальные полная цена, длительность и правила по гражданству/дате требуют обновления; железная дорога не исключена из choice')
ev('E-KGD-28','KGD_MRO_PLAN2021','В2021 объявлялся план базы обслуживания SSJ; ввод2026 и контракт RW не подтверждены','UNKNOWN','введённая мощность/контракт',status='ИСТОРИЧЕСКИЙ_ПЛАН_НЕ_ФАКТ_ВВОДА')
ev('E-KGD-29','PIN-BASE-known_flows','Сохранён PEE–KGD36363 пассажира2025; первичный airportOD/месячная разбивка не получены','36363','пассажиры пары/2025',period='2025',limit='Сохранённая строка с URL v-kurse.ru; направление/сумма двух направлений и метод учёта нуждаются в первичном уточнении; не делить на12')
ev('E-KGD-30','PIN-P02-city_coverage','Из24 требуемых исходящих рынков KGD частично покрыты2; непокрыты22','2/24','рынки покрытия',period='P02v2 по exactSHA',limit='Не2 существующих рынка; покрытие P02 не admission физических кресел')
ev('E-KGD-31','PIN-BASE-network_routes','Авторская base-сеть KGD имела8 спиц AER/MRV/KUF/VOG/MMK/CSY/GOJ/GSV','8','пары авторской модели',period='исторический модельный baseline dceadc9',status='СОХРАНЁННАЯ_АВТОРСКАЯ_МОДЕЛЬ',limit='Не наблюдаемая сеть RW; старые прибыль/захват/годовая частота не приняты в P06')
ev('E-KGD-32','PIN-PLAN-lineage','C25 предполагал цепи ZIA–KGD–GOJ–ZIA и ZIA–KGD–KUF–ZIA','C25','историческая гипотеза',period='план12ноября',status='ПРОИСХОЖДЕНИЕ_НЕ_ПРОВЕРЕННАЯ_ПРОГРАММА',limit='В этом пакете пересобрана в прямые/мобильные ротации; треугольник не обязателен')
write_csv('evidence.csv', evidence)

assumptions=[]
def ass(aid, item, selected, unit, reason, sensitivity, refine, source_ids='', period='2027–2028', bounds='UNKNOWN'):
    assumptions.append(dict(assumption_id=aid,parameter=item,selected_value=selected,units=unit,period=period,coverage='KGD локальная ветвь; не общий принятый коэффициент',status='ПРОЕКТНОЕ_УСЛОВИЕ_НЕ_ПРОГНОЗ',selected_by=OWNER,basis=reason,range_or_unknown=bounds,affected_conclusion=sensitivity,sensitivity=sensitivity,refinement=refine,source_id=source_ids))
ass('KGD-A01','состав рабочей программы','KUF;GOJ;MMK','airport pairs','KUF/GOJ имеют опубликованные локальные рейсы и дают контроль существующей базы; MMK — северный рынок, присутствует в плане2025 и витрине Smartavia','Менять спицу при слабом конечном спросе/плохой трассе; выбор не закрывает PEE/VOG/юг','P05 месячная OD и choice; P03 трасса/нагрузка','KGD_SUMMER2025;SMART_KGD;PIN-P02-competitor_products')
ass('KGD-A02','частоты peak/shoulder/winter','3/2/2;2/2/1;2/1/1','пар рейсов/неделю KUF/GOJ/MMK','Сетка пробует поездки3/4ночей на2/нед,2/3ночи на3/нед;1/нед подходит7/14ночам. Это варианты дизайна, не оценка платёжеспособного спроса','Альтернативы1,2,3/нед на рынок; проверять избыток кресел и приемлемость дат в P05','датированные продукты и сегменты P05','KGD_TOUR_ATOR2025;PIN-P02-competitor_products',bounds='дискретные проверяемые дизайны1/2/3 в неделю; не доверительный интервал')
ass('KGD-A03','сезоны для дизайна','июль–август peak;май–июнь,сентябрь shoulder;прочие winter','месяцы','Сезон отдыха подтверждён; границы операционного дизайна выбраны агентом, данные2026/месячный OD не приняты','Сдвиг границ/продажа праздников отдельно; использовать весь24месячный календарь без52-недельной экстраполяции','P05 monthly calendar; аэропорт/ТКП2025–2026','KGD_TOUR_ATOR2025;KGD_TG_JUL2025',bounds='UNKNOWN для реальных долей спроса по месяцам')
ass('KGD-A04','рабочий самолёт','1 условно выделенный физический борт','tail count','Минимальный модуль для честного парного опыта; ни один RW борт не назван свободным','Проверить один доступный+выделенный резерв и общий резерв; без admission доступности запуск запрещён','P03 индивидуальный хвост/ввод/назначения/донор; одинаковый ресурс в P и KEEP','PIN-P03-aircraft_type_parameters',bounds='1рабочий в конструкции; доступное RW число UNKNOWN')
ass('KGD-A05','резерв','UNKNOWN;ветви общий резерв/ещё1выделенный','tails;стоимость;время восстановления','Резерв нельзя считать бесплатным; удалённость требует восстановления с перегоном по реальной трассе','В ветви выделенного резерва бюджет2физических хвоста у P и альтернативы; доступность обоих UNKNOWN','P03 SLA/география/ТО/crew; P04 стоимость','PIN-P03-airport_constraints')
ass('KGD-A06','варианты ВС','SSJ100/SaM146 отдельно;SJ100/ПД8 отдельно','variant','Наблюдение Superjet подтверждает семейство; не SJ100; параметры будущего самолёта не копируются','Отдельный payload-range/fuel/MRO и срок ввода для каждого варианта;0новыхТу214','PIN-P03-aircraft_type_parameters;диспетчерский расчёт','KGD_HOME;PIN-P03-aircraft_type_parameters')
ass('KGD-A07','блок-время KUF/GOJ','KUF→KGD225;GOJ→KGD190;KGD→GOJ185;KGD→KUF UNKNOWN','минуты','Первые3значения вычислены из локальных часов опубликованного P02 с UTC offset; обратный KUF не зеркалится автоматически','Изменение фактической трассы/ветра меняет ресурс, топливо, duty; не переводить расстояние по прямой в block','P03 подтверждённые часы/трасса/ветер/NOTAM в сезонах','PIN-P02-competitor_products',period='зима2026/27 как аналог;будущееUNKNOWN')
ass('KGD-A08','разворот/служебное окно','UNKNOWN','минуты','30мин буклета — не гарантированный RW turn; нет придуманных MCT/слота/crew duty','Определяет возможность W-оборотов и утренних/вечерних продуктов','P03 ground contract и типовой норматив по типу','KGD_TECH')
ass('KGD-A09','конкурентный ответ','сохранение предложения;переоценка;частота/ёмкость по подтверждённому ресурсу','response policy','Nordwind назван базовым, у него прямые/трансферные продукты; снижение цен возможно без нового борта, но коэффициент не измерен','P05 должен найти break-even ответа, а не применять произвольные-10% ко всем рынкам','P02/P05 same-basket чеки и календарь борта конкурента','KGD_SUMMER2025;SMART_KGD')
ass('KGD-A10','местные расходы/скидки/поддержка','UNKNOWN','RUB/драйвер','Найден тарифный выпуск2026; договор и ставки не прочитаны. Поддержка2027–2028 не обещана','Полный результат и funding UNKNOWN до P04 либо порогов; ветвь без поддержки — отдельная сценарная политика','P04 запрос актуального прайса/контракта; base/launch/exit/reserve; eligibility','KGD_TARIFF_INDEX;KGD_TARIFF202608;PIN-P04-thresholds')
ass('KGD-A11','собственные продажи/KEEP','UNKNOWN','поездки;сегменты;RUB;датированные места','Исторический DME и текущие LED/SVO не обнулять; миграция из KUF/SVX/других программ общая','Компенсации, потерянный донор и вытеснение местного спроса могут поменять выбор','P03 KEEP+P05committed_sales на same demand pools','RW_DME2025;RW_BOARD')
ass('KGD-A12','защищённая стыковка/partner','UNKNOWN','MCT;RUB/поездку;багаж;договор','Инфраструктура багажа и опубликованный MSQ не обеспечивают договор RW/Belavia или допуск','Без договора показывать раздельные билеты с риском, не защищённый продукт; не присваивать чужую выручку','P02 sellable itinerary; P03 MCT; P04 interline clearing/платежи','KGD_TECH;KGD_SUMMER2025')
ass('KGD-A13','доставка/запуск','плановая поэтапная;частичная;задержка;0новых','ветвь N(t)','Сроки/числа только из общего P03; никаких новых локальных обещаний','При0новых: сохранять KEEP; перенос действующего только с донором; partner не бесплатен','общий календарь P03 и адаптивные действия P06','PIN-P03-aircraft_type_parameters')
ass('KGD-A14','MMK/юг/дальние block/payload','UNKNOWN','минуты;kg;km трассы','Есть рынки, но нет диспетчерского бюджета; старый цвет/2150км не экономический отказ','Невыполнимый вариант самолёта исключается только в проверенном сезоне/нагрузке, город остаётся','P03 route-specific AFM/трасса/багаж/запасной','KGD_SUMMER2025;PIN-P03-aircraft_type_parameters')
ass('KGD-A15','роль хаба','не присвоена;проверяемые transfer OD отдельно','роль','Русские east–east трансферы через западный KGD могут проигрывать прямому/другому узлу; величина detour не измерена','Тестировать лишь конкретные OD; провал KUF–GOJ через KGD не отказ всех хабов','P05 journey duration/цена; P03 фактическая трасса','KGD_SUMMER2025;PIN-PLAN-lineage')
ass('KGD-A16','цены витрин: год/lead','2026-11/12 предполагается по as_of;другие датыUNKNOWN','дата;дни','Год не показан; витрина не checkout. Чеки без багажа/прямоты не сравнивать','Ни один минимум не стал yield; lead рассчитан только при явной календарной интерпретации','P02 dated total price с ручной кладью/багажом/возвратом/всеми legs','SMART_KGD;RW_KGD')
write_csv('assumptions.csv',assumptions)

# Витрина содержит возможные стыковки: никаких выдуманных прямых leg/capacity.
fare_rows=[]
smart_text=re.sub(r'\s+',' ',(ROOT/'sources/SMART_KGD.txt').read_text())
pat=r'([А-ЯЁ][А-Яа-яё -]+?) ([A-Z]{3}) из Калининграда из Калининграда KGD от ([\d ]+) ₽ В одну сторону, (\d{2}) ([а-я]+)'
monthmap={'ноября':11,'декабря':12,'января':1,'февраля':2}
for i,m in enumerate(re.finditer(pat,smart_text),1):
    city,code,price,day,month=m.groups();year=2026 if monthmap.get(month,0)>=11 else None
    date=dt.date(year,monthmap[month],int(day)) if year else None
    fare_rows.append(dict(offer_id=f'KGD-SM-{i:02}',source_id='SMART_KGD',origin='KGD',destination=code,departure_date=date.isoformat() if date else 'UNKNOWN',departure_date_display=f'{day} {month}',date_year_status='условный текущий2026;KGD-A16' if year else 'годUNKNOWN',as_of=ASOF,booking_lead_days=(date-dt.date.fromisoformat(ASOF)).days if date else 'UNKNOWN',fare_rub=int(price.replace(' ','')),units='RUB/взрослый/одно направление',period='витрина на'+ASOF,coverage='выбранные витринные продукты;не все рейсы',status='РЕКЛАМНЫЙ_МИНИМУМ_НЕ_ОФЕРТА',physical_legs='UNKNOWN',baggage='UNKNOWN',fare_basis='минимальный;сборы включены;возврат/обменUNKNOWN',sellability='не проверена в checkout',open_seats='UNKNOWN',assumption_id='KGD-A16'))
write_csv('offer_observations.csv',fare_rows)

checks=[dict(check_id='DQ01',source_id='KGD_TG_JUN2025',expression='532180+10395-542375',value=532180+10395-542375,units='пассажиры',period='2025-06',status='CONFLICT',coverage='компоненты июня vs total; не исправлять молча'),dict(check_id='DQ02',source_id='KGD_TG_JUN2025',expression='2193279+55820-2249009',value=2193279+55820-2249009,units='пассажиры',period='2025-01/2025-06',status='CONFLICT',coverage='накопленные компоненты vs total'),dict(check_id='DQ03',source_id='KGD_TG_JUL2025',expression='2824528+66479-2891007',value=2824528+66479-2891007,units='пассажиры',period='2025-01/2025-07',status='PASS',coverage='июльское накопление'),dict(check_id='DQ04',source_id='KGD_TG_JUL2025;KGD_TG_JUN2025',expression='2891007-2249009-641908',value=2891007-2249009-641908,units='пассажиры',period='2025-06/2025-07',status='CONFLICT',coverage='разность накоплений не равна месяцу')]
write_csv('source_conflicts.csv',checks)

# Непрерывные цепочки одного физического самолёта, пока без дат UTC и неизвестных времен.
peak_radial=[('KGD','KUF'),('KUF','KGD'),('KGD','GOJ'),('GOJ','KGD'),('KGD','MMK'),('MMK','KGD'),('KGD','KUF'),('KUF','KGD'),('KGD','GOJ'),('GOJ','KGD'),('KGD','KUF'),('KUF','KGD'),('KGD','MMK'),('MMK','KGD')]
peak_mobile=[('KUF','KGD'),('KGD','GOJ'),('GOJ','KGD'),('KGD','MMK'),('MMK','KGD'),('KGD','KUF'),('KUF','KGD'),('KGD','GOJ'),('GOJ','KGD'),('KGD','MMK'),('MMK','KGD'),('KGD','KUF'),('KUF','KGD'),('KGD','KUF')]
def leg_rules(chain):
    duration={('KUF','KGD'):225,('GOJ','KGD'):190,('KGD','GOJ'):185}
    return [dict(template_leg_id=f'L{i+1:02}',iso_day=i//2+1,sequence_in_day=i%2+1,origin_airport=a,destination_airport=b,departure_utc=None,arrival_utc=None,block_time_reference_minutes=duration.get((a,b)),physical_adjacent_leg=True,seats=None,source_id='PIN-P02-competitor_products' if (a,b) in duration else 'KGD_SUMMER2025',status='ПРОЕКТНЫЙ_ШАБЛОН_БЕЗ_ADMISSION',assumption_ids=['KGD-A02','KGD-A07','KGD-A08','KGD-A14']) for i,(a,b) in enumerate(chain)]

common=dict(period=['2027-01','2028-12'],status='КАНДИДАТ_STAGE_A;ПОЛНЫЙ_P06_RUN_NOT_RUN',units='рейсы/неделю в каждом направлении;физические борта;UTC после P03',coverage='локальный модуль общей8–12пар;не самостоятельное доказательство№2',fleet_scope='общий кейс Superjet;ветви SaM146 и ПД8 раздельно',resource_group='KGD-G1:одинаковый индивидуальный tail-calendar в каждой паре P/KEEP',new_tu214=0,existing_rw_sales='KEEP сохранён на затронутых рынках;точные ID/квотыUNKNOWN,не0',money_result=None,needs=['P03:dated flights/aircraft/crew/ТО/резерв/KEEP/трасса','P05:monthly demand pools/choice/цена/переток/ответ','P04:cost events/cash/startup/exit/налоги/поддержка','P06:совместный полныйP−KEEP'],source_ids=['RW_BOARD','KGD_SUMMER2025','PIN-P02-competitor_products'],assumption_ids=['KGD-A01','KGD-A02','KGD-A03','KGD-A04','KGD-A05','KGD-A06','KGD-A10','KGD-A11','KGD-A13'])
candidates=[]
def candidate(cid,title,role,markets,flights,resource,comparison,reason,**extra):
    d=dict(common);d.update(programme_id=cid,title=title,role=role,markets=markets,flight_rules=flights,resource=resource,paired_counterfactual=comparison,design_basis=reason,**extra);candidates.append(d)
candidate('P-KGD-00','Будущий KEEP и альтернативное использование ресурса','KEEP', ['KGD–LED','KGD–SVO','историческийKGD–DME:проверитьпродолжение','своиKUF/SVX продукты'],[],{'working_tails':'тот же принятый календарь P03','resource_not_used_by_KGD':'сохраняется на альтернативных заданиях/с обязательствами, не исчезает','reserve':'одинаковый ресурс в P/KEEP'},'каждый новый кандидат','История2025 не baseline2028; модель обязана сохранить актуальные собственные обязательства и использовать новые борта альтернативно',admission='НЕ_ГОТОВ_БЕЗ_P03_KEEP')
candidate('P-KGD-01','Прямой сезонный KUF–KGD из существующей базы','прямой продукт', ['KUF↔KGD'],[{'origin':'KUF','destination':'KGD','return':True,'peak_each_way_per_week':3,'shoulder':2,'winter':2,'iso_days_peak':[1,4,7],'block_minutes':{'outbound_reference':225,'return':None},'changed_service':'добавленный/перенесённый ресурс;не весь старыйKEEP','assumption_id':'KGD-A02'}],{'working_tails':1,'initial_base':'KUF;подтвердитьP03','week_use':'6projectlegs peak;остальные часы/дни в общем alternative-use KEEP','reserve':'UNKNOWN'},'P-KGD-00 и сопоставимая новая радиальная база','Два/три вылета дают разные сроки поездки и используют существующую базу; наличие Nordwind требует доказать захват при цене/качестве',own_sales_action='Сохранить LED/SVO и прочие собственные связки; перераспределение спроса совместно P05')
season_freq={'peak':{'KUF':3,'GOJ':2,'MMK':2},'shoulder':{'KUF':2,'GOJ':2,'MMK':1},'winter':{'KUF':2,'GOJ':1,'MMK':1}}
candidate('P-KGD-02','Радиальная база KGD на одном рабочем самолёте','новая/временная радиальная база', ['KGD↔KUF','KGD↔GOJ','KGD↔MMK'],leg_rules(peak_radial),{'working_tails':1,'initial_location':'KGD после оплаченного/занимающего ресурс перегона из исходной позиции P03','overnights_peak':'KGD все7ночей','reserve':'общий с измеренным SLA либо дополнительный1tail;контрактUNKNOWN','calendar_admission':'плановый нижний count1 не доказательство выполнимости duty/slots/range'},'P-KGD-03 и P-KGD-00 при том же индивидуальном календаре','Проверка ценности локальной базы и лучшего расположения времени; никаких самостоятельных transfer-объёмов в radial',season_frequencies=season_freq,season_iso_days={'peak':{'KUF':[1,4,6],'GOJ':[2,5],'MMK':[3,7]},'shoulder':{'KUF':[1,5],'GOJ':[2,6],'MMK':[4]},'winter':{'KUF':[1,5],'GOJ':[3],'MMK':[7]}},own_sales_action='Ни один свой рейс автоматически не сокращён; новые продажи берутся из общих pools после fixed/committed sales; при переносеtail прежнийдонор сохраняется в KEEP')
candidate('P-KGD-03','Мобильная цепочка из KUF с ночёвками GOJ/MMK','прямые продукты из существующей базы', ['KGD↔KUF','KGD↔GOJ','KGD↔MMK'],leg_rules(peak_mobile),{'working_tails':1,'initial_location':'KUF','end_of_week_location':'KUF','overnights_peak':['GOJ','MMK','KUF','GOJ','MMK','KUF','KUF'],'reserve':'тот же общий/выделенный резерв,что у P-KGD-02','crew':'смены/гостиницы/доставка экипажей UNKNOWN'},'P-KGD-02;тот же tail-budget;те же14legs/3пары peak','Выполняет те же направления и недельное количество каждого плеча, но не требует формальной ночной базы KGD. Меняются часы/дни и расходы outstation; это содержательная альтернатива базе',season_frequencies=season_freq,nonpeak_rules='Снять полные возвратные циклы по season_frequencies; заново построить непрерывную недельную ротациюP03,не просто удалитьпроизвольныеlegs',own_sales_action='Те же demand pools и сохранённые своипродажи,что radial; один конец поездки не продаётся вторично как трансфер')
candidate('P-KGD-04','Подвоз из KGD в существующий узел KUF','подвоз/смешанная программа', ['KGD↔KUF','KGD↔TJM черезKUF','KGD↔NUX черезKUF','KGD↔MCX черезKUF'],candidates[1]['flight_rules'],{'working_tails':1,'extra_connector_tails':'0 только если изменённые существующие рейсы KUF имеют принятые свободные dated seats;иначеUNKNOWN','capacity':'долямест наKUFspokes одна с local/другими программами','reserve':'общийпринятый'},'P-KGD-01:те же рейсыKGD–KUF беззащищённыхconnections;иKEEP','RW board показывает KUF–TJM/NUX/MCX в ближайшем календаре; тестируем ценность стыковки в существующей базе вместо нового KGD-хаба',connection_status='MCT/багаж/общий билет/расписание/защитаUNKNOWN;не объявлен продаваемым',additional_source_ids=['RW_BOARD'],own_sales_action='Перенос времени собственных KUFspokes требует всех старых клиентов и sold itineraries; нельзя добавить дешёвый подвоз, потеряв доходдругихрынков безучёта')
candidate('P-KGD-05','Ограниченный защищённый трансфер через KGD','гипотеза хаба', ['KUF↔GOJ черезKGD','GOJ↔MMK черезKGD'],leg_rules(peak_mobile),{'working_tails':1,'added_legs_vs_direct':'0 в первом paired test','banks':'стыкуемые последовательные legs шаблона;обратнаясторона/срокпоездки проверяетсяP03','extra_tails_for_bidirectional_banks':'UNKNOWN;если нужен2йtail,парасравнения тоже получает2'},'P-KGD-03:те же legs, local продажи,беззащищённыхthrough products','Изолировать пользу/ущерб защиты на тех же креслах; сравнить detour и displacedlocal sales с прямымKUF–GOJ/другимиузлами. Нет заявленного спроса наbacktracking',admission='УСЛОВНО_ДО_P05_DURATIONS_AND_P03_MCT;не аргумент в пользу общегохаба',own_sales_action='Сквозной тариф поездкеодинраз;двакресла списываются;местнаявыручкавытесненныхклиентов учитываетсяобщимвыбором')
candidate('P-KGD-06','KGD–MSQ: партнёрский продукт против собственного рейса','partner/международная дополнительная ветвь', ['KGD↔MSQ','KGD↔страны черезMSQ приподтвержденииправ/договора'],[{'origin':'KGD','destination':'MSQ','return':True,'own_flight_test_each_way_per_week':2,'partner_frequency':'UNKNOWN;не присвоено расписание2025','active_months':'поacceptedP03calendar;0новыхТу214','status':'предложенная проверка;не объявленный RW рейс','assumption_ids':['KGD-A02','KGD-A12']}],{'own_branch':'1условновыделенныйSJ/SSJ хвост;неиспользованныйресурсостаётсявобщемalternative-use','partner_branch':'тотжесамолётвKEEP/другомпродукте;неисчезаетстоимостьегообязательств','inventory':'договорныеместапартнёраUNKNOWN','reserve':'дляownветвитотжепринятый'},'ownKGD–MSQ vs partnerKGD–MSQ+тотжесамолётвальтернативнойпрограмме vsKEEP','MSQ опубликован влето2025;турфирмы дают слабый сигнал outboundinternational. Отделить собственныйвылет от продажи чужихмест; Egypt/Turkey неподтверждаютспросименночерезMSQ',admission='условнодоговором/правами/продажей/коммерческимclearing;никакихновыхТу214',own_sales_action='Выручка чужого рейса не RWоборот:учитыватьтолькоRWпризнанныйтариф/комиссиюпообщимправиламP04')
candidate('P-KGD-07','Южный сезонный прямой продукт KGD–MRV','дополнительный прямой продукт', ['KGD↔MRV'],[{'origin':'MRV','destination':'KGD','return':True,'peak_each_way_per_week':2,'winter':0,'season':'май–сентябрь какпроверяемыйдизайн;прочиемесяцыресурсвKEEP','block_minutes':None,'changed_service':'проектное дополнение;сохраняется собственныйKEEP','assumption_ids':['KGD-A02','KGD-A03','KGD-A14']}],{'working_tails':1,'operating_base':'существующаяP03базаилиmobileцепь;неустановленаавтоматическиMRVбазаRW','route':'фактическийоблёт/полезнаянагрузка/багажUNKNOWN','reserve':'UNKNOWN'},'тотжесамолётнаKGD–KUF либо инойпринятыйP03alternative;новаябазаKGDне обязательна','Сохранённаяавторскаяспица и опубликованныйлетнийрынок;югснужнойдальностьюможетотличатьсяотповолжского. Невыполнимыйодинтип/сезоннеотказгорода',admission='сначалаP03dispatchдляSaM146иPD8раздельно,затемP05choice;нетбезусловногоприоритета',own_sales_action='ВозможныйперетоксAER/другихтуристическихпрограммRWвP05;летний0внепрограммыэто0новыхрейсов,не0спроса')
write_json('programme_candidates.json',{'schema':'KGD-StageA-design-v1;это НЕ готовый P06 bundle','programmes':candidates,'calendar_policy':'24месяца2027–2028; активизация после конкретного service_entry,поставочныйсценарийвнешний;частичные/0поставкинеприравниваютсякцелевомуконцу2028','supply_branches':['плановаяпоэтапная','частичная','задержка','0новыхSJ','0новыхТу214 во всех основных сравнениях'],'fixed_then_adaptive':'сначала фиксированный дизайн подветвью;затем выполнимый перенос/сокращение скомпенсациями и сохранённымиобязательствами,не заднимчислом','not_proved':['датированнаявыполнимость','свободныйпаркRW','спрос/выручка/прибыль/funding','достижение№2','глобальнаялучшаясеть']})

monthly=[]
for year in (2027,2028):
    for month in range(1,13):
        season='peak' if month in (7,8) else 'shoulder' if month in (5,6,9) else 'winter'
        monthly.append(dict(month=f'{year}-{month:02}',programme_ids='P-KGD-02;P-KGD-03',season=season,
            KUF_each_way_per_week=season_freq[season]['KUF'],GOJ_each_way_per_week=season_freq[season]['GOJ'],MMK_each_way_per_week=season_freq[season]['MMK'],
            actual_project_flights='UNKNOWN;даты только после service_entry/KEEP admission',
            new_sj100_branch='НЕ РАНЬШЕ ВТОРОГО ПОЛУГОДИЯ 2027; в этом месяце новые SJ не запускаются' if year==2027 and month<7 else 'по принятому P03 N(t)/service_entry; число/дата UNKNOWN',
            existing_ssj_branch='только при выделенном доноре и полном учёте его потерянного результата',
            period=f'{year}-{month:02}',units='пар рейсов/неделю; проектные частоты, не годовые пассажиры',coverage='полный 24-месячный дизайн, не принятый лётный календарь',status='CONDITIONAL_DESIGN_NOT_SCHEDULE',source_id='KGD_TOUR_ATOR2025;PIN-P03-aircraft_type_parameters',assumption_ids='KGD-A02;KGD-A03;KGD-A04;KGD-A13'))
write_csv('monthly_design_calendar.csv',monthly)

rh=[]
def hyp(hid,title,signal,source_ids,mechanism,counterfactual,test,outcome,condition,ancestors,programmes):
    rh.append(dict(hypothesis_id=hid,version='1.0',title=title,signal=signal,source_ids=source_ids,mechanism=mechanism,counterfactual=counterfactual,distinguishing_test=test,ancestorIDs=ancestors,programme_ids=programmes,period='2027–2028',units='поездки;сегменты;RUB;борта;см.тест',coverage='локальнаяветвьKGD',status=outcome,result_scope='StageA:исследование/конструкция;P06 численнаяоценкаNOT_RUN',revisit_condition=condition,assumption_ids=['KGD-A01','KGD-A02','KGD-A04','KGD-A09','KGD-A10','KGD-A11']))
hyp('H-KGD-01','Сезонный endpoint из KUF','опубликованконкурентKUF–KGD;авторские4/неднеприняты',['KGD_SUMMER2025','PIN-P02-competitor_products'],'3/нед peak/2вдругиесезоныулучшаютвыбордатбезновойбазы','KEEP и альтернативноеиспользованиетогожеtail','P05samebasket+частоты/ownmigration;P03рейсы;P04полнаядельта','УСЛОВНА_КОНКРЕТНЫМИ_ОБЩИМИ_ВХОДАМИ','припринятомOD/payload/KEEP пересчитать;недостатокданныхнеотказ',['C25','KIR_PAIR_E','EC_H05','BASE:KUF–KGD'],['P-KGD-01'])
hyp('H-KGD-02','Радиальная KGD база против мобильнойцепочки','3локальныхспицывместовоспроизведения8авторских',['KGD_SUMMER2025','KGD_TECH','PIN-BASE-network_routes'],'экономияночёвок/позиционированияиболееполезныечасывылетамогутпокрытьместнуюбазу','одинtail;тежеpeak3пары/14legsуmobileизKUF','P02часовыепродукты+P05jointallocation;P04TH-OPTION/TH-FIXED приполномP03календаре','СФОРМИРОВАН_ПАРНЫЙ_ОПЫТ;ЭКОНОМИКА_УСЛОВНА','новыйMRO/станцияилициклэкипажейменяетрезультат;порогбазывычислитьвP06',['C25','BASE:Хаб KGD'],['P-KGD-02','P-KGD-03'])
hyp('H-KGD-03','Подвоз к KUF вместо KGD-хаба','уNordwindужеестьпересадкичерезKZN;RWлетаетKUF–TJM/NUX/MCX',['KGD_SUMMER2025','RW_BOARD'],'новоеплечоKGD–KUFпродаётнесколькоконечныхODприобщихdatedseats','тежеKGD–KUFрейсыбезсквозныхпродуктов;KZNконкурент;KEEP','продаваемыйобщийбилет/MCT/багаж+OD/month;убрать/добавитьconnectionsнаоднихlegs','УСЛОВНА_ДОГОВОРОМ_И_ИНВЕНТАРЁМ','доступныесмежныеlegs,защита и положительнаядельтапослевытеснения',['C25','NEW:KGD evidence Nordwind KZN'],['P-KGD-04','P-KGD-01'])
hyp('H-KGD-04','Защищённый трансфер в KGD','багажнаяинфраструктураесть;подтвержденияtransferdemandRWнет',['KGD_TECH','KGD_SUMMER2025'],'защитаобщегобилетаможетиметьценность,ноdetour/displacedlocalспросмогутеёперекрыть','тежеKGDlegsбезtransferпродукта;прямые/другиеузлы','отдельноKUF–GOJ иGOJ–MMK:время/ценапоездки,обакресла,локальноевытеснение;недетурscore','УСЛОВНА_КОНКРЕТНЫМИ_OD;ОБЩИЙ_ХАБ_НЕ_ДОКАЗАН','достаточныйODилиноваямеждународнаяветвьможетизменитьвыбор;плохойодинODнезакрываетхаб',['BASE:Хаб KGD'],['P-KGD-05'])
hyp('H-KGD-05','Короткий leisure/calendar продукт вместо произвольнойчастоты','пляжныйсезонкороткий;естьэкскурсионныйотдых',['KGD_TOUR_ATOR2025','KGD_TG_JUL2025'],'2/недсоответствуют3/4или7ночам;частотанужнакаккалендарныйпродукт','1/нед и3/неднаэтомжересурсе+альтернативапрочихдней','одинаковыемесячныеpools;сегментысдопустимымидатами,праздникиотдельно','СЕЗОННЫЙ_СИГНАЛ_ЕСТЬ;ЧИСЛЕННАЯ_ПРОВЕРКА_STAGE_B','реальныемесячныебронирования/датапоездки;другойпрофильснимаетвыбранныепериоды',['C25'],['P-KGD-01','P-KGD-02','P-KGD-03'])
hyp('H-KGD-06','Партнёрский MSQ против собственного рейса','MSQопубликован;зарубежныеклиентытурфирмне airportOD',['KGD_SUMMER2025','ROSSTAT_TOUR'],'партнёрствосберегаетaircraftbudgetдлядругойпрограммы,ноимеетплату/лимиты','собственный2/недSSJилиSJ;тотжеtailвальтернативномзаданииуpartner','договорныеместа/throughfare/права/clearing;доходнеприсваиваетсяRWполностью','УСЛОВНА_ДОГОВОРОМ/ПРАВАМИ;ДОПОЛНИТЕЛЬНАЯ_ВЕТВЬ','приacceptedMSQпродуктеиобщейденежнойдельте;0новыхТу214ветвьсохранена',['NEW:KGD international evidence'],['P-KGD-06'])
hyp('H-KGD-07','Использовать готовую SSJ базу в Храброво','найденплан2021;не найдено подтвержденияввода/доступа',['KGD_MRO_PLAN2021','PIN-P03-airport_constraints'],'готоваямощностьмоглабыуменьшитьstartup/downtime','строить/договариватьсяосвоенииснулялибоmobile','сертификат/приложениесадресомKGD,типом,видамиТО;RWконтракт/SLA/мощность','УСЛОВНА;ПРЕДПОСЫЛКА_ГОТОВОЙ_БАЗЫ_НЕ_ПРИНЯТА','источникфактическоговводаменяетзатраты;непринимать1.5млрд2021какценузапуска',['BASE:airport_tech KGD ssj_mro UNKNOWN'],['P-KGD-02'])
hyp('H-KGD-08','Южный прямой продукт на Superjet','KGD–MRVестьвисториипредложения/авторскойсети',['KGD_SUMMER2025','PIN-BASE-network_routes'],'сезоннаяпрямаяпоездкаможетбытьполезнеепересадокбезновойбазы','тотжеtailнаKUF–KGD/иномпринятомрынке;KEEP','сначалаpayload/fuel/actualrouteдляобоихтипов,затемP05;нельзяотказатьиз-за2150кмцвета','УСЛОВНА_DISPATCH;НЕ_ЭКОНОМИЧЕСКИЙ_ОТКАЗ','подтверждённыйвариант/сезон/нагрузкаилидртипмогутснятьограничение',['BASE:KGD–MRV','historical:Прямые MOW-AER-KGD'],['P-KGD-07'])
hyp('H-KGD-09','Отклонить KGD из-за старогоscore/конкурента','старыйrank6/0.506 иналичиеNordwindне критерийэкономики',['PIN-BASE-longlist_scores_min500','KGD_SUMMER2025'],'такойscreenнеизмеряетдобавочныесвоипродажи/полнуюдельту','всеKGDвариантыпроходяттежеP05/P06условия','сопоставимыйsame-resourceP−KEEP,не взвешенныйстарыйбалл','ОТКЛОНЁН_ИМЕННО_КРИТЕРИЙ_ОТСЕВА','новыйдоказанныйресурсный/экономическийкритерийможетдатьадресныйотказ;городнеотклонён',['BASE:longlist KGD'],[])
write_json('hypotheses.json',{'hypotheses':rh,'lineage_policy':'C25 переформулирован с сохранением происхождения; историческая8спицнепринятакакобязательнаясеть; UNRESOLVED не раннийотсев','unfinished_economics':'все явно указанныеStageBневыдаватьзазавершённуюэкономическуюоценку'})

market=[]
for cid,other,act,od in [
 ('P-KGD-01','KUF','добавить/изменитьпрямойпродукт;действующийRWэтойпарыUNKNOWN','KUF↔KGD'),
 ('P-KGD-02','KUF','радиальнаябаза;частотаизseason_frequencies','KUF↔KGD'),('P-KGD-02','GOJ','радиальнаябаза;новыепроектныерейсы','GOJ↔KGD'),('P-KGD-02','MMK','радиальнаябаза;новыепроектныерейсы','MMK↔KGD'),
 ('P-KGD-03','KUF','мобильнаяцепь;3peakвозвратныхэквивалента','KUF↔KGD'),('P-KGD-03','GOJ','мобильнаяцепь;2peakвозвратныхэквивалента','GOJ↔KGD'),('P-KGD-03','MMK','мобильнаяцепь;2peakвозвратныхэквивалента','MMK↔KGD'),
 ('P-KGD-04','KUF','ретаймKGD–KUF/согласоватьspokes;неудвоитьместа','KGD↔TJM/NUX/MCXчерезKUF'),('P-KGD-05','GOJ','толькоthroughпродукты;общиесуществующиеprojectlegs','KUF↔GOJ;GOJ↔MMKчерезKGD'),
 ('P-KGD-06','MSQ','own2/недтестиличужойinventoryпоcontract','KGD↔MSQ/дальше'),('P-KGD-07','MRV','2/недвсезонеприdispatchgate','KGD↔MRV')]:
    market.append(dict(delta_id=f'D-KGD-{len(market)+1:02}',programme_id=cid,airport_pair='KGD–'+other,od=od,action=act,own_keep_flights='UNKNOWN;сохранитьдоявногорешенияP03',own_preserved_sales='UNKNOWN;не0',own_removed_sales='UNKNOWN;не0',own_transferred_sales='UNKNOWN;не0',proposed_incremental_sales='UNKNOWN;P05',competitor='N4дляKUF/GOJ;5NвитринаMMK;другиенеисключены' if other in ['KUF','GOJ','MMK'] else 'UNKNOWN;публикации2025неполны',period='2027–2028 помесячно',units='рейсы;поездки;сегменты;RUBраздельно',coverage='затронутыепары;этоНЕпринятыйKEEP',status='PROJECT_DELTA_PENDING_COMMON_INPUTS',source_id='KGD_SUMMER2025;RW_BOARD;PIN-P02-competitor_products',assumption_ids='KGD-A01;KGD-A02;KGD-A11'))
for pair in ['KGD–LED','KGD–SVO','KGD–DME']:
    market.append(dict(delta_id=f'D-KGD-{len(market)+1:02}',programme_id='ALL',airport_pair=pair,od=pair,action='сохранение/продолжение/периодUNKNOWN;нельзяисключитьизKEEP',own_keep_flights='P03required',own_preserved_sales='UNKNOWN;не0',own_removed_sales='толькосподтверждённымдействием',own_transferred_sales='P05общийpool',proposed_incremental_sales='UNKNOWN',competitor='конкретныйаэропорт;MOWнесклеивать',period='2027–2028',units='датированныерейсы;поездки;RUB',coverage='LED/SVOтекущийсрез;DMEистория2025',status='OWN_SALES_GUARD',source_id='RW_BOARD;RW_DME2025',assumption_ids='KGD-A11'))
write_csv('market_deltas.csv',market)

requests=[]
def req(rid,owner,programmes,question,fields,effect,sources_,priority='КРИТИЧНО_ДЛЯ_STAGE_B'):
    requests.append(dict(request_id=rid,owner=owner,programme_ids=programmes,request=question,required_fields=fields,period='2027-01/2028-12;история2025/доступный2026',units='каквrequired_fields',coverage='KGD и общиезатронутыерынки',status='ОТКРЫТО_STAGE_B;НЕ_ОТКЛОНЕНИЕ',priority=priority,decision_impact=effect,source_id=sources_))
req('CR-KGD-01','P05','ALL','Принятьвзаимноисключённыепотенциальныепоездки;необъявлятьairporttotalsOD','pool_id×month×segment;OD/цель/плательщик/срок;общийcatchment;outside','Спрос/переток/цены иобщийвыбор,безэтогонетmoneywinner','KGD_TG_JUL2025;PIN-P02-historical_demand_context')
req('CR-KGD-02','P02/P05','P-KGD-01/02/03/04','ЗакрытьдатированныеофферыKUF/GOJ/MMK;отдельноSVX/PEE/LED/SVO/DME/VKO','flightdate;operating/marketing;physicallegs;seats/inventory;gross/net;багаж;refund;as_of/booking_lead','Сравнитьпрямые/пересадки/ответ;витрина5Nнепрямойinventory','SMART_KGD;PIN-P02-competitor_products')
req('CR-KGD-03','P03','ALL','Одинаковыйресурс и будущийKEEPсвыделеннымдонором/альтернативойновогоборта','индивидуальныйtail_id,count1;service_entry;24months;crew;ТО;reserve;contracts;existingsolditineraries','Честныйsame-resourcecounterfactual;0новых/частичная/задержка','RW_BOARD;PIN-P03-airport_constraints')
req('CR-KGD-04','P03','P-KGD-01/02/03/07','Проверитьоблёт/полезнуюнагрузкукаждогоплечапосезону','actualroute;block;fuel;alternate/reserve;bag;SaM146variant;ПД8variant;NOTAM;runway','SSJ/SJпригодность;южныйрынокнеотклонён500км/цветом','PIN-P02-historical_route_context;KGD_TECH')
req('CR-KGD-05','P03/местнаяэксплуатация','P-KGD-02/03','ПроверитьтекущийAIP/слоты/ночныестоянки/handling/ТО/crew','AIP/NOTAM;PCN;standallocation;turn;crew-duty/rest/hotel;MROapproval/SLA/доступRW','Радиальнаябазапротивmobile;буклет/план2021нефактическийдоступ','KGD_TECH;KGD_FORM2023;KGD_MRO_PLAN2021')
req('CR-KGD-06','P04','ALL','ПолучитьKGDпрайсс01.08.2026/редакциииRWконтракт;будущеетолькосadmission','landing/securityMTOW;terminal/pax;handlingturn;fueltonnes/uplift;overnight/base-month;minima;discount;effective/priceyear/tax/payment','Локальныйполныйresult/cash;неborrowчужиеставки','KGD_TARIFF_INDEX;KGD_TARIFF202608;PIN-P04-event_rate_map')
req('CR-KGD-07','P04/P06','P-KGD-02 vs03','ВывестиTH-OPTIONиTH-FIXEDнаполныхпрограммах','netearnedfare_once;variable/base/aircraft/reserve/startup/exit;avoidable/common;cashdates;financing','МаксимумдобавочнойстоимостибазыприравенствеP−KEEP иfunding;денегпоканет','PIN-P04-thresholds;PIN-P06-producer_contract')
req('CR-KGD-08','P05/P02','ALL','РеакцияNordwind/Smartaviaтолькопоконкретнымрынкам','samebasketquote;spare/dedicatedtailcalendar;retiming;frequency;price;response_id','Найтипорогреакциивместопроизвольного%-дисконта','KGD_SUMMER2025;SMART_KGD')
req('CR-KGD-09','P02/P03/P04/P05','P-KGD-04/05/06','Принятьпродаваемыеprotected/partnerстыковки','orderedlegs;MCT;throughcheckbag;connectionprotection;fare/clearing;blockedseats;legalrights','Безэтогонетзащищённогохаба/partner;самосборотдельнымпродуктом','KGD_TECH;KGD_SUMMER2025')
req('CR-KGD-10','P05/первичныеданные','ALL','УточнитьPEE–KGD36363 и месячнуюисториюаэропорта','направленностьpairpax;обаendpoints;month;arrival/departuredefinition;June/Julyconflicts','Неудвоитьспрос/неразделитьневерныйитогна12;неподменитьтуристами','PIN-BASE-known_flows;KGD_TG_JUN2025;KGD_TG_JUL2025')
req('CR-KGD-11','P05','ALL','Сохранитьназемныеальтернативыиcatchment без500кмuniformradius','accessfromKGD/Зеленоградск/Светлогорск;bus/taxi;railviaLTtime/fare/doc;citizenship;none/ofscope','Подвижностьиgeneralisedcost;существованиеж/днеобычныйвнутреннийgroundchoice','KGD_TOUR_RAIL')
req('CR-KGD-12','P08I/P04/P05','P-KGD-06','Уточнитьлокальныйinternationalспрос иpartnerбизнес','турфирмы≠airportOD;Egypt/Turkey/MSQпоmonth/отправлению;договор/clearing;0новыхТу214','Неувестиmaincaseвнеподтверждённыймеждународныйбизнес','ROSSTAT_TOUR;KGD_SUMMER2025','ДОПОЛНИТЕЛЬНАЯ_ВЕТВЬ')
req('CR-KGD-13','P06/координатор','P-KGD-02/03','Включитьмодуливсеть8–12airportpairsвконце2028','fullbundles/manifest;sameN(t);sharespools;datedseats;nooverallwinnerwithoutcalibration','3местныепарыне8–12 и не№2;деньгинезависимыхмоделейнесуммировать','PIN-P06-producer_contract')
write_csv('comparison_requests.csv',requests)

# Проверяются только факты конструкции, не будущая эксплуатационная/экономическая приёмка.
from collections import Counter
def stats(chain):
    directed=Counter(chain)
    return {'leg_count':len(chain),'unique_airport_pairs':len({tuple(sorted(x)) for x in chain}),
            'directed_counts':{'>'.join(k):v for k,v in sorted(directed.items())},
            'continuous':all(chain[i][1]==chain[i+1][0] for i in range(len(chain)-1)),
            'cyclic':chain[-1][1]==chain[0][0]}
a,b=stats(peak_radial),stats(peak_mobile)
assert a['directed_counts']==b['directed_counts'] and a['continuous'] and b['continuous'] and a['cyclic'] and b['cyclic']
assert len({r['hypothesis_id'] for r in rh})==len(rh)
assert {s for r in evidence for s in [r['source_id']] if not s.startswith('PIN-')} <= set(SM)
assert len(fare_rows)>=8
write_json('construction_checks.json',{'status':'PASS_ТОЛЬКО_КОНСТРУКЦИЯ','radial_peak':a,'mobile_peak':b,'same_directed_leg_counts':True,'nominal_working_tail_budget_each':1,'same_available_resource_required':True,'counts_not_calendar_feasibility':True,'complete_dated_feasibility':'NOT_RUN;blockMMK/KGD→KUF/crew/slots/reserve/KEEPUNKNOWN','money/choice_engine':'NOT_RUN','source_arithmetic_conflicts_preserved':3,'offer_rows':len(fare_rows),'hypotheses':len(rh),'programmes':len(candidates)})

case={'case_id':'KGD-research-v1','city':'Калининград','airport':'KGD/UMKK,Храброво','as_of':ASOF,
 'status':'STAGE_A_ЗАВЕРШЁН;STAGE_B_ОТКРЫТ','purpose':'Выбрать применимую рольKGD и передатьобщемуядрупроверяемыепрограммы;невычислятьсвоюзахватную/денежнуюмодель',
 'finding':'KGD — подтверждённый рынокRW сдатированнымнаблюдениемрейса;изэтогонеустановленабаза/хабRW. Приоритетсравнения:прямыеизсуществующейбазы,радиальнаябаза,мобильнаяцепьиподвозкKUF;хаб/partner/югусловныотдельнымивходами.',
 'rw_role':{'market/outstation':'подтверждено:WZ901LED→KGD иWZ4591KGD→SVO12.11.2026;неполныйсрез','historical':'DME–KGDобъявленлетом2025,7→3/нед','base':'UNKNOWN;отсутствиевспискеопорныхаэропортовнеотсутствиебазы','hub':'UNKNOWN;нетпринятогонабораRWprotectedconnections','free_aircraft':'UNKNOWN','mro_contract':'UNKNOWN','historical_mro_plan':'2021нефактввода2026','source_ids':['RW_BOARD','RW_DME2025','KGD_MRO_PLAN2021']},
 'demand':{'local':'калининградскийcatchment/побережье;доступaccessпоmunicipalityUNKNOWN','regional':'GOJ/KUF/PEE/MMK ит.д.:опубликованное/историческоепредложение,неизмеренныйнеудовлетворённыйOD','long_distance':'изKGDопубликованытрансферычерезKZNвСибирь/Дальнийсегмент;необъявленопрямымSuperjetплечом','international':'MSQ/HRG/SSHопубликованы2025;сигналтурфирм2025неairportOD;0новыхТу214сохранён','segments':{'tourism':'пляжный/экскурсионныйсопоройнаАТОР;будущийобъёмUNKNOWN','VFR/family':'правдоподобно,нонетпринятойколичественнойлокальнойопоры;UNKNOWN','business/corporate':'UNKNOWN;неконструируетсяконтрактРостехаизсамогофактапринадлежностиRW','mandatory_travel':'UNKNOWN'},'seasonality':'естьлетнийсигнал2025;сезонныедолинеоценены;2026индикаторспадаТИЦнепоказательвсехпоездок','data_limits':'airporttotalsнеOD;прибывшийиулетевшийтуристнеобязательноуникальныелюди;36363PEEтребуетgrainvalidation'},
 'competition':{'observed':'N4GOJ/KUFвP02;U6SVXвP02;5Nвитринамногихпродуктов;SU/FV/DP/S7потекущемутablo','protected_transfer':'N4черезKZNопубликованвлето2025;2026sellability/датыUNKNOWN','response':'базовыйстатусNordwindделаетреакциюсущественной;паркдляновыхчастотнеподтверждён;ценоваяреакциябезновогобортатестируетсяP05','coverage':'неполныйсписок;непрочитанныестрокинеотсутствиеперевозчика'},
 'operations':{'published_infrastructure':'3350×45m;1250пасс/час;багажнаяtransferвозможность','capacity_limit':'пиковаясвободнаямощность/стоянки/слотыUNKNOWN;норматив2023неavailablecapacity','approach_conflict':'CATIIвтексте/CATIвтаблицебуклета;AIPrequired','runway/dispatch':'конкретныеварианты/веса/сезоны2027–2028неподтверждены','fuel':'естьиндекспоставщика,нетпринятойместнойцены/договора','crew/MRO':'местнаямощность/допуск/контрактRW/ПД8UNKNOWN','launch/exit':'нужныhandling/base/crewroom/запчасти/депозиты/сроки/termination/refund/salvage;UNKNOWNне0'},
 'economics':{'engine':'толькоP06exact982f13d;егоавторскиепроверкинеприёмкаданныхKGD','costs':'P04drivers/TH-OPTION/TH-FIXED/TH-FUEL;никакихчужихаэропортовыхставок/старойприбыли','threshold':'ДобавочнаяполнаястоимостьKGDbase+startup+exitдолжнанепревышатьразностьполныхрезультатовдоэтихдобавочныхзатратмеждуradial/mobileпрификсированныхпрочихвходах. ПорогUNKNOWNдоP05/P03/P04. Fundingотдельнопокалендарюплатежей/процентам.','market_share':'UNKNOWN;числитель/знаменатель/периоднеприняты'},
 'old_hypotheses':'C25неэкономическиопровергнута;переформулированавH-KGD-01/02/03/05. Авторская8спицсохраненасSHA/rowhash;неперенесеновобщуюэкономику.',
 'stage_b_decision_changes':['платёжеспособныйконечныйOD/датыичистыйтарифпослеответаN4/5N','фактическийоблёт/payload/fuelSaM146/ПД8','стоимостьновойбазыпротивmobile/альтернативыбоpта','доступрезерва/слотов/crew/ТО','договорнаястыковкаивытеснениесвоихпродаж','задержка/частичная/0поставка;стоимостьвыхода'],
 'not_claimed':['прибыльностьс2027','свободныйпарк','готовыйRWхаб','подтверждённыйSJ100/ПД8допуск','проверенныйгодовойкалендарь','полныйконкурентныйсписок','выборKGDдля№2','результатыP05доихполучения']}
write_json('case.json',case)

readiness={'package':'KGD-research-v1','as_of':ASOF,'stage_a':'COMPLETE_LOCAL_RESEARCH_AND_DESIGN','stage_b':'OPEN_REQUIRED','joint_final_acceptance':'NOT_READY','not_economic_rejection':True,
 'completed':['exactSHAвходы+KGDrowIDs/hash','текущаярольRWсграницами','новыеместныепервичные/вторичныеисточники+ошибкиполучения','конкурентныесвязки/витрина/сезонность/эксплуатационныеграницы','8кандидатов,9объяснимыхисходовгипотез,13адресныхStageBrequests','проверкасвязности/равенстванаправленныхpeaklegsвпареradial/mobile'],
 'unknown':['monthlypotentialOD/choice','датированныекресла/полныйсоставконкурентов','ownKEEP/sales/donor','поставочныйservice-entry/physicaltails/crew/MRO/reserve/slots','прайс/контракт/ставки2027–2028','market/cash/полнаяэкономика/financing','MCT/багаж/partnercontracts'],
 'acceptance_gates':['сопоставимыйP/KEEPресурс и внешнийсценарий','admissionP02/P03/P04/P05поисточникуипериоду','P06jointrecompute и независимаяприёмка','общее8–12airportpairs кконцу2028толькоmaincase;малыйлокальныймодульдопустим'],
 'limits':'NOT_RUN экономиканеотсев. StageAзавершёнтольковобластиразведки/конструкции;открытаявыполнимостьиэкономикаотданыкоординатору.'}
write_json('readiness.json',readiness)
handoff={'package_id':'KGD-research-v1','write_scope':str(ROOT),'author':OWNER,'completed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'ГОТОВ_К_КОММИТУ_КООРДИНАТОРОМ_STAGE_A','git_mutations_performed':False,'child_agents_spawned':False,'common_files_edited':False,'source_pins':'source_pins.json','entrypoints':['case.json','programme_candidates.json','hypotheses.json','readiness.json','comparison_requests.csv'],'strong_findings':['N4базовый+KZNtransfer—реальныйконтрфактуал','RWcurrentmarketнеподтверждённаяKGDбаза','техническийбуклет/планMROнеоперационнаяприёмка','неполныеP02рынкиненулевыерынки','парныеradial/mobile14legs3пары1номинальныйtail;неcalendarfeasibility'],
 'integration_instructions':['Необъединятьстарые53строкиденежныхрезультатовBASEсновымP06;ониlineageonly','P-KGD-02/03сначалаcommonP03datedschedule;припринятииединогоtailcalendarсравнитьобщимP05/P06','P-KGD-04независимаяизменяемаяценностьconnectionsнакKGD–KUF;собственныеспицытребуютquota','P-KGD-05необщийвыводохабах;проверкаконкретныхOD','0новыхпоставокнеостанавливаетисследование;KEEP/переноссдонором/partnerотдельно','Разрешённыевеса/прокситолькоassumptions.csv;нетскрытойлокальнойденежной/захватноймодели'],
 'stage_b_requests':'comparison_requests.csv','independent_acceptance':'NOT_RUN;нужнановаязадачакоординатора','external_messages':'толькоавторизованныевнутренниеhandoffкоординатору;третьимлицамничегонеотправлено','paid_services/bookings/payments/restarts/site_changes':False,'output_manifest':'output_manifest.json'}
write_json('handoff.json',handoff)
(ROOT/'README.txt').write_text('Калининград: исследование и варианты, Stage A\n\nЧитать case.json, затем programme_candidates.json и hypotheses.json.\nStage A завершён в области локальных источников и конструирования. Stage B: спрос, датированная эксплуатация, экономика и funding открыты; адресаты в comparison_requests.csv.\n\nПарный опыт P-KGD-02/P-KGD-03 имеет по одному номинальному рабочему самолёту, те же 14 направленных плеч и 3 пары в пиковую неделю. Связность проверена, но это не допуск парка/crew/ТО/слотов и не годовая сеть. Вне пика используются отдельные сезонные частоты; 24-месячный календарь строится после P03.\n\nРоль RW подтверждена как рынок/outstation с рейсами на конкретную дату. База, хаб, свободные борта и доступное ТО UNKNOWN. Nordwind в официальном плане 2025 назван базовым и предлагает пересадки через Казань.\n\nВ sources.json и sources/receipts.json различены прочитанный текст, поисковый фрагмент, anti-bot HTML и фактический документ. Старые аэропортовые ставки, рекламные минимумы и авторская прибыль не стали будущими ставками/чеками/денежным результатом. Все общие входы закреплены exact SHA; extracts содержат source row IDs и canonical hashes.\n\nВоспроизведение сборки: python3 '+str(ROOT/'build_package.py')+'\nСборка не делает сетевых/Git-модифицирующих вызовов. Источники фиксированы в пакете.\n')

# Сборка повторно не наращивает manifest и не переписывает исходные raw facts.
seen=set(); unique=[]
for x in pins['files']:
    key=(x['source_id'],x['path'])
    if key not in seen: unique.append(x); seen.add(key)
pins['files']=unique
pins['row_hash_convention']='source_csv_line — порядковый номер разобранной CSV-записи + 1 (заголовок); при переносах внутри поля не физическая строка текста. Hash — canonical JSON оригинальных колонок до добавления полей provenance.'
write_json('source_pins.json',pins)
files=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.name=='output_manifest.json' or '__pycache__' in p.parts: continue
    files.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
write_json('output_manifest.json',{'package_id':'KGD-research-v1','base_path':str(ROOT),'status':'STAGE_A_COMPLETE_STAGE_B_OPEN','files':files,'self_hash':'исключён во избежание рекурсивного hash','source_pin_file':'source_pins.json','commit_scope':'только перечисленные файлы назначенного каталога; coordinator commits','total_bytes':sum(x['bytes'] for x in files)})
print(json.dumps({'files':len(files),'bytes':sum(x['bytes'] for x in files),'evidence':len(evidence),'hypotheses':len(rh),'programmes':len(candidates),'requests':len(requests),'construction':'PASS','economics':'NOT_RUN'},ensure_ascii=False))
