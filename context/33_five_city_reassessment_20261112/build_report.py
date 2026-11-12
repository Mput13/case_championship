"""Build the Russian research report from pinned tables and reviewed synthesis."""
from pathlib import Path
import csv
import hashlib
import html
import json
import re

from synthesis_content import CITY_NAMES, CITY_ORDER, CITY_SECTIONS, ROUTE_NOTES

ROOT = Path(__file__).resolve().parent


def esc(value):
    return html.escape(str(value), quote=True)


def rows(path):
    with (ROOT / path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def link(url, label):
    return f'<a href="{esc(url)}">{esc(label)}</a>'


def para(text, css=""):
    return f'<p class="{css}">{esc(text)}</p>'


def table(headers, data, caption=""):
    body = ''.join('<tr>' + ''.join(f'<td>{esc(value)}</td>' for value in row) + '</tr>' for row in data)
    return (f'<div class="table-scroll"><table><caption>{esc(caption)}</caption><thead><tr>'
            + ''.join(f'<th scope="col">{esc(h)}</th>' for h in headers)
            + f'</tr></thead><tbody>{body}</tbody></table></div>')


def source_link(source):
    url = source["url"]
    if url.startswith("git:"):
        parts = url.split(":", 2)
        if len(parts) == 3 and re.fullmatch(r"[a-f0-9]{7,40}", parts[1]):
            url = f'https://github.com/Mput13/case_championship/blob/{parts[1]}/{parts[2]}'
        else:
            url = f'cities/{source["source_id"].split("-")[0]}/sources.csv'
    elif not url.startswith(("https://", "http://")):
        url = f'cities/{source["source_id"].split("-")[0]}/sources.csv'
    return link(url, source["title"])


def cite(ids, sources):
    if not ids:
        return ""
    return '<p class="source">' + ' · '.join(source_link(sources[i]) for i in ids) + '</p>'


def section(anchor, title, body):
    return f'<section id="{anchor}"><h2>{esc(title)}</h2>{body}</section>'


CSS = '''
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--foreground,#202c35);font:17px/1.65 var(--font-sans,system-ui,sans-serif)}
a{color:var(--primary,#156e8a);text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid var(--ring,#c48118);outline-offset:4px}
.layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:36px;max-width:1280px;margin:auto}
nav{position:sticky;top:16px;align-self:start;max-height:720px;overflow:auto;font-size:14px;line-height:1.45;padding-top:24px}
nav a{display:block;margin:0 0 12px;text-decoration:none}main{min-width:0;padding-bottom:60px}h1{font-size:36px;line-height:1.15;margin:20px 0}h2{font-size:27px;line-height:1.25;margin:48px 0 18px}h3{font-size:20px;line-height:1.4;margin:25px 0 8px}
p{margin:10px 0 16px}.lead{font-size:20px;line-height:1.55}.source,.meta{font-size:13px;color:var(--muted-foreground,#5e6a73)}.source a{overflow-wrap:anywhere}
section{scroll-margin-top:20px;border-top:1px solid var(--border,#ced7dc)}section:first-of-type{border-top:0}.table-scroll{overflow-x:auto;margin:16px 0 24px}
table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.5}th,td{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--border,#ced7dc)}th{font-weight:650;background:var(--secondary,#edf2f4)}caption{text-align:left;font-size:13px;margin-bottom:8px;color:var(--muted-foreground,#5e6a73)}
.route-table td{min-width:150px}.route-table td:first-child{min-width:70px}.callout{border-left:3px solid var(--primary,#156e8a);padding:4px 0 4px 18px;margin:20px 0}.metric{font-variant-numeric:tabular-nums}.bar-row{display:grid;grid-template-columns:150px minmax(90px,1fr) 65px;gap:12px;align-items:center;margin:10px 0;font-size:14px}.bar-track{height:18px;background:var(--secondary,#e2e9ec);border-radius:3px;overflow:hidden}.bar-fill{height:18px;background:var(--chart-1,#217f99)}
.mobile-toc{display:none}.columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}.full-link{font-size:14px}code{font:14px var(--font-mono,monospace);overflow-wrap:anywhere}ul{padding-left:22px}li{margin:8px 0}.summary{max-width:900px}.summary h2{font-size:22px;margin:22px 0 12px}.summary .bar-row{grid-template-columns:130px minmax(80px,1fr) 60px}
@media(max-width:900px){.layout{display:block}nav{display:none}.mobile-toc{display:block;position:sticky;top:0;z-index:2;background:var(--card,#f7fafb);padding:8px 12px;border-bottom:1px solid var(--border,#ced7dc);font-size:14px}.mobile-toc a{display:block;margin:7px 0}.mobile-toc[open]{max-height:500px;overflow:auto}h1{font-size:29px}h2{font-size:25px}.columns{display:block}}
@media(max-width:480px){body{font-size:16px}h1{font-size:27px}.bar-row,.summary .bar-row{grid-template-columns:112px minmax(70px,1fr) 53px;gap:8px;font-size:12px}th,td{padding:8px}h2{font-size:23px}.lead{font-size:18px}}
@media print{nav,.mobile-toc{display:none}.layout{display:block}body{font-size:11pt}h2{break-after:avoid}tr{break-inside:avoid}a{color:inherit}}
'''


def document(title, body, toc=None):
    if toc:
        links = ''.join(link('#'+anchor, label) for anchor, label in toc)
        body = (f'<details class="mobile-toc"><summary>Содержание</summary>{links}</details>'
                f'<div class="layout"><nav aria-label="Содержание">{links}</nav><main>{body}</main></div>')
    return f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head><body>{body}</body></html>'


def baseline_tables():
    summaries = [r for r in rows('inputs/model/network_summary.csv') if r['scenario'] == 'base' and r['hub'] in CITY_NAMES]
    by_city = {r['hub']: r for r in summaries}
    scores = {r['iata']: r for r in rows('inputs/distance_audit/screening_scores.csv')}
    order = CITY_ORDER + ['OMS']
    data = []
    bars = ''
    for city in order:
        r, score = by_city[city], scores[city]
        share = 200 * int(r['transfer_od_year']) / int(r['segments_year'])
        data.append([CITY_NAMES[city], score['rank_without_filter'],
                     f'{float(score["distance_to_bases_km"]):.0f}', r['aircraft'], r['routes'],
                     f'{int(r["result_mln_year"]):+,}', f'{share:.1f}%'])
        bars += (f'<div class="bar-row"><span>{esc(CITY_NAMES[city])}</span><div class="bar-track">'
                 f'<div class="bar-fill" style="width:{share:.4f}%"></div></div><span class="metric">{share:.1f}%</span></div>')
    return table(['Город', 'Место без фильтра', 'Км по прямой', 'Бортов с резервом', 'Лучей', 'Вклад, млн ₽/год', 'Пересадочные сегменты'], data,
                 'Авторский base, dceadc98. Прежние оценки спроса и расходов; топливная компенсация учтена, маршрутная субсидия — нет. Разные размеры парка. Не полная прибыль.'), bars


def city_section(code, sources):
    content = CITY_SECTIONS[code]
    body = para(content['conclusion'], 'lead')
    for heading, text, ids in content['paragraphs']:
        body += f'<h3>{esc(heading)}</h3>' + para(text) + cite(ids, sources)
    selected = ROUTE_NOTES[code]
    available = {r['destination'] for r in rows(f'cities/{code}/routes.csv')}
    assert all(row[0] in available for row in selected), code
    body += '<h3>Маршруты, меняющие выбор</h3><div class="route-table">'
    body += table(['Пара', 'Что известно', 'Что меняет выбор'],
                  [[code+'—'+destination, known, implication] for destination, known, implication in selected],
                  'Выборка из полного маршрутного реестра. Даты и статус предложения сохранены в строках; отсутствие записи не равно отсутствию рейса.') + '</div>'
    body += '<h3>Условие выбора</h3>' + para(content['choice'])
    body += para('Решающие неизвестные: '+content['decisive_unknown'], 'callout')
    body += '<p class="full-link">' + ' · '.join([
        link(f'cities/{code}/dossier.md', 'Полное досье'),
        link(f'cities/{code}/routes.csv', 'Все направления'),
        link(f'cities/{code}/features.csv', 'Особенности и контраргументы'),
        link(f'cities/{code}/decision.json', 'Условия шести вариантов'),
        link(f'cities/{code}/sources.csv', 'Источники и ограничения доступа')]) + '</p>'
    return section(code.lower(), CITY_NAMES[code], body)


def opening():
    body = '<h1>Пять городов после проверки правила 500 км</h1>'
    body += para('Уфа · Пермь · Челябинск · Тюмень · Нижний Новгород. Исследование 12 ноября 2026 года; решения для 2027–2028 годов.', 'meta')
    body += para('Универсального основания исключать эти города по расстоянию не найдено. Их следует вернуть в сравнение. Это решение о допуске к анализу; выбор нового хаба требует спроса, расписания, полного бюджета и преимущества перед другим использованием самолётов.', 'lead')
    body += para('Для каждого города проверены территория, транспортные альтернативы, конкуренты, возможные продукты, инфраструктура и условия экономики. Особенности выявлялись по источникам. Общие механизмы сохранены даже там, где выводы городов похожи. Исследование не назначает городу обязательную уникальную роль.')
    body += para('Главное практическое изменение — сравнивать небольшую программу прямых рейсов, использование существующей станции или базы, новый хаб, наземный доступ и отсутствие нового проекта. Один город может требовать разных решений для разных конечных направлений.')
    return body


def method_section():
    body = para('Единица сравнения — одна конечная поездка: от конкретной зоны проживания до конечного пункта, в определённые даты, с целью поездки и плательщиком. Она может пройти через местный аэропорт, соседнюю базу, чужой хаб, поезд или автомобиль. Одинаковый пассажир не продаётся независимо нескольким программам.')
    body += table(['Вопрос', 'Что сравниваем', 'Как влияет на решение'], [
        ['Доступность', 'Дорога до терминала, полный чек, время, день вылета, ночёвка и риск срыва', 'Километры заменяются конкретным выбором продукта; единого нового радиуса нет'],
        ['Спрос', 'Конечный OD, цель поездки, оплачиваемый объём, сезонность', 'Население, оборот аэропорта и кресла остаются разными показателями'],
        ['Конкуренция', 'Оператор, дата, частота, тип, открытые кресла, цена и защищённость пересадки', 'Рейс с 30 открытыми местами отличается от полного розничного самолёта'],
        ['Собственный переток', 'Какие клиенты и какой вклад RW уйдут из прежней программы; можно ли перепродать место', 'Валовый поток новой линии не равен приросту компании'],
        ['Ресурс и экономика', 'Одинаковый календарь парка, резерв, альтернативное применение; все добавочные расходы и деньги', 'Суммы программ с разными самолётами не становятся рейтингом эффективности'],
    ])
    body += para('Выбор местного аэропорта можно оценивать по полной стоимости поездки: денежный чек плюс ценность времени и ожидаемые потери от неудобного расписания и ненадёжности. Коэффициенты следует оценивать по наблюдаемому выбору и продажам, отдельно по типам поездок, а затем проверять на других городах и периодах. При недостатке данных используются диапазоны и пороги решения с источником, а не произвольный балл «сибирской специфики».')
    body += para('У такого направления анализа есть практический образец: британская CAA сопоставляла зоны аэропортов по времени доступа и фактическому происхождению пассажиров, отдельно учитывая цель поездки и совпадение направлений. Для России пригоден принцип проверки выбора; британские пороги времени и доли населения нельзя переносить без местных наблюдений.')
    body += '<p class="source">' + link('https://www.caa.co.uk/media/meog3vta/heathrowmarketpowerassessment.pdf', 'CAA, Heathrow Market Power Assessment, февраль 2012, §§3.123–3.130') + '</p>'
    body += para('Новая база должна окупать собственную добавку: улучшение расписания и экономию позиционирования против экипажей, ТО, резерва, запуска и обязательств. Хаб дополнительно требует конкурентных конечных поездок и банков стыковок. Стратегия может иметь убыточный первый этап, если рассчитаны его финансирование, механизм улучшения и условие остановки; фиксированная дата окупаемости без расчёта не назначается.')
    return section('method', 'Как сравнивать варианты', body)


def assumptions_section():
    body = para('Отмена 500 км исправляет один механизм отбора. Сохранение остальных допущений может сильнее влиять на результат, чем само расстояние.')
    body += table(['Допущение текущей модели', 'Почему существенно', 'Требуемая проверка'], [
        ['75 км зоны населения и разные годы/охваты', 'Меняются и размер рынка, и распределение одной территории между аэропортами', 'Одинаковые зоны доступа, наблюдаемый выбор аэропорта; не складывать административные агрегаты'],
        ['Бинарный direct_now и общая доля захвата', 'Не различает редкий чартер, ежедневный рейс и предложение с пересадкой', 'Датированные частоты, открытая ёмкость, тарифные корзины и ответ конкурентов'],
        ['Реконструкция OD по 31 потоку', 'Поток плеча не идентифицирует все конечные поездки и будущие стыковки', 'Независимые конечные бронирования; отдельная проверка городов и периодов'],
        ['Единые расходы и топливная компенсация', 'Даже знак вклада зависит от цены, налогового режима, применимости и размера поддержки', 'Локальные договорные корзины; раздельные сценарии топлива, поддержки и полных затрат'],
        ['Учёт перетока по точной паре аэропортов', 'Пропускает смену аэропорта жителем той же зоны и смену собственного хаба', 'Совместное распределение конечного спроса и потерянного/перепроданного вклада'],
        ['Минимум 8 направлений и разные единицы прямой сети', 'Может вынуждать слабые лучи и смешивать 8 лучей с 8 треугольниками', 'Показывать физические плечи и ресурс; отдельно малая программа'],
        ['Год как 52/48 одинаковых недель', 'Не учитывает ввод борта во второй половине года, сезон и календарь рейсов', 'Помесячный парк, поэтапная/частичная/задержанная поставка и отсутствие новых бортов'],
        ['Вес ограничений «Ковёр» и геометрия пересадки', 'Дни публикаций не равны часам простоя, а близость на карте не гарантирует стыковку', 'Интервалы ограничений, банки, минимальные времена и стоимость восстановления'],
    ])
    body += para('Существующий SSJ100 и будущий SJ-100 с ПД-8 разделяются. Переданный самолёт, введённый в коммерческую эксплуатацию и свободный для проекта самолёт — разные состояния. Если используется действующий борт, в сравнении сохраняется его прежнее задание и потерянный результат; для нового борта учитывается лучшее альтернативное применение.')
    return section('assumptions', 'Другие допущения, меняющие результат', body)


def provenance_section():
    counts = []
    for code in CITY_ORDER:
        counts.append([CITY_NAMES[code]] + [len(rows(f'cities/{code}/{name}.csv')) for name in ['sources', 'claims', 'routes', 'features']])
    body = para('Основание — точные файлы модели Насти/kiruha355 dceadc98 от 11 ноября, предыдущий аудит расстояний ce10c1f и аудит источников f9eafa8. Копии выбранных входов сохраняются побайтно, с SHA256, исходным путём и commit. Новые городские сведения не подставлены скрыто в авторскую модель; общий расчёт отдельно показывает контролируемые изменения.')
    body += table(['Город', 'Записей источников', 'Утверждений', 'Маршрутных строк', 'Особенностей'], counts,
                  'Это объём реестра, а не оценка качества и не число независимых наблюдений. Повторные публикации могут иметь один первоисточник.')
    body += para('Координатор повторно выполнил городские проверки и выборочно перечитал первичные сообщения: продукты RW, характеристики Уфы, корпоративный чартер Братска, ангар «Ямала», историческую базу CEK и присутствие RW в Перми. Проверка схем и арифметики не подтверждает конечный спрос, получение поддержки, коммерческую готовность борта или прибыльность запуска.')
    body += '<p>' + ' · '.join([link('input_manifest.json', '34 закреплённых входа'), link('coordinator_checks.json', 'Проверки координатора'), link('research_brief.md', 'Общая методика'), link('validation.json', 'Итоговая проверка пакета')]) + '</p>'
    body += para('Полнота конкурентов, внутренние конечные бронирования, получаемая чистая выручка, договорные расходы, свободный парк и будущие выплаты поддержки остаются ограничениями решения. Доступ к отдельным страницам ограничен; статус чтения сохранён по каждому источнику. Закрытых баз, платных данных и сообщений третьим лицам в исследовании не было. Дашборд Насти и публичный Site не изменялись.')
    return section('evidence', 'Источники и границы доказательства', body)


def main():
    missing = set(CITY_ORDER) - set(CITY_SECTIONS)
    if missing:
        raise SystemExit('Cannot publish before city synthesis is complete: '+','.join(sorted(missing)))
    sources = {r['source_id']: r for code in CITY_ORDER for r in rows(f'cities/{code}/sources.csv')}
    baseline, bars = baseline_tables()
    body = opening()
    gate_body = para('Городской фильтр исключал весь вариант, если ближайший из SVO/DME/VKO/SVX находился ближе 500 км по прямой. Без него при прежних весах Уфа, Пермь и Челябинск занимают первые три места, Омск — четвёртое. Тюмень оказывается пятой, Нижний Новгород — седьмым. Это изменение рейтинга критериев; экономическая модель уже содержала все двадцать городов.')
    gate_body += para('Отдельные ограничения той же величины обнуляют местные продажи на коротком плече и исключают короткие конечные поездки с пересадкой. Переключение городского фильтра на панели не отменяет их. Поэтому «убрать 500 км» — несколько разных экспериментов.') + baseline
    gate_body += '<h3>Насколько авторские хабы зависят от пересадок</h3>' + bars
    gate_body += para('Доля относится к пассажирским сегментам: одна пересадочная поездка расходует два плеча. Вычислено как 2 × пересадочные поездки / все сегменты из опубликованного base. Это модельная структура, не наблюдённый трансфер аэропорта. У Омска зависимость также велика, поэтому проверка не должна ограничиваться возвращёнными городами.', 'source')
    body += section('rule', 'Что меняется после снятия фильтра', gate_body)
    body += method_section()
    for code in CITY_ORDER:
        body += city_section(code, sources)
    # The common calculation is integrated after its independently delivered result.
    common_path = ROOT / 'common_synthesis.html'
    if not common_path.exists():
        raise SystemExit('Cannot publish before common economic synthesis is complete')
    body += common_path.read_text(encoding='utf-8')
    body += assumptions_section() + provenance_section()
    toc = [('rule','Правило и прежний рейтинг'),('method','Метод сравнения')]
    toc += [(code.lower(),CITY_NAMES[code]) for code in CITY_ORDER]
    toc += [('economics','Общий расчёт'),('decision','Условия выбора'),('assumptions','Другие допущения'),('evidence','Источники и проверка')]
    output = document('Повторная оценка пяти городов Red Wings', body, toc)
    (ROOT / 'report.html').write_text(output, encoding='utf-8')
    print(json.dumps({'report_bytes':len(output.encode()),'cities':CITY_ORDER,'sha256':hashlib.sha256(output.encode()).hexdigest()},ensure_ascii=False))


if __name__ == '__main__':
    main()
