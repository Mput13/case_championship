"""Отчёты и ссылки на конкретные численные артефакты; не изменяет результаты P06."""
import json,csv,hashlib,sys
from pathlib import Path
import programme_builder as b
P=b.ROOT
def j(path):return json.loads((P/path).read_text())
def sha(path):return hashlib.sha256((P/path).read_bytes()).hexdigest()
def text(name,s):(P/name).write_text(s.strip()+'\n')
def main():
    ps=j('programmes.json')['programmes'];bs=j('build_summary.json');canonical=[]
    for ref in j('ui/index.json')['packages']:
        for ev in j(ref['path'])['evaluations']:
            r=ev['result'];c=r['project']['context'];canonical.append(dict(programme_id=c['programme_id'],scenario=c['external_scenario_id'],delivery='phased',period_start=c['period_start'],period_end=c['period_end'],price_year=c['price_year'],delta_journeys=r['delta_summary']['journeys'],delta_revenue_net=r['delta_summary']['revenue_net'],missing_cost_headroom=r['thresholds']['net_missing_operating_cost_break_even'],full_delta_result=r['delta_summary']['operating_result'],source_full_result_sha256=ev['source_full_result_sha256'],source_path=ev['source_full_result_path'],result_mode=ev['result_mode']))
    b.csvwrite(P/'canonical_summary.csv',canonical)
    ledger=j('parameterledger.json');known_ids={a['assumption_id'] for a in ledger}
    template_files=['input_pins.json','root_pin_promotion.json','root_intake_6a6326c.json','local_rate_corrections.json','competition_row_lineage.json','parameterledger.json','programme_builder.py','evaluate_programmes.py']
    template=dict(template_id='P09-COMMON-INPUT-v1',files=[dict(path=f,sha256=sha(f)) for f in template_files],engine_pin='982f13d9b6c378ed9581125ecc5c40f17dade6a3',P05_pin='a63a047bc6559df8bac3b2dde5c6464c3c9e6a0b',source_research_pin='6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1',source_acceptance='SOURCE_RESEARCH_ONLY',prices='constant2026 RUB; reference not future contract',demand='SCENARIO_NOT_IDENTIFIED',unknown_affected_remainder='Не равен нулю; полная дельта функция недостающих собственного бизнеса/затрат/перетока')
    b.dump(P/'common_input_template.json',template)
    overrides=dict(delivery={d:b.fleet(d) for d in ['phased','partial','delayed','none']},demand={'base':'Pinned P05 coefficients/base OD','cautious':'Pinned P05 cautious coefficients/OD','bad_season':'P05 cautious for6–8; P05 base othermonths, basecost'},response={'passive':'no response rule','response10':'P05-A13 residualincumbent fare−10%, same OD/date conditional on RW frequency>=1'},support={'value':0,'status':'EXPLICIT_NO_SUPPORT_SCENARIO_NOT_OBSERVED_ABSENCE'},assumption_ids=['P09-RESOURCE','P09-ENTRY','P09-RESPONSE','P09-SEASON','P09-SUPPORT'])
    b.dump(P/'scenario_overrides.json',overrides);byid={p['programme_id']:p for p in ps}
    with (P/'evaluation_input_manifests.jsonl').open('w') as f:
        for path in sorted((P/'evaluations').glob('*.json')):
            r=json.loads(path.read_text());row=dict(evaluation_path=str(path.relative_to(P)),evaluation_sha256=sha(path.relative_to(P)),common_template='common_input_template.json',common_template_sha256=sha('common_input_template.json'),programme_jsonpath='$.programmes[programme_id='+r['programme_id']+']',programme_sha256=b.digest(byid[r['programme_id']]),overrides={k:r[k] for k in ['delivery','scenario','response']},overrides_source_sha256=sha('scenario_overrides.json'),result_mode='P06_DISJOINT_DATE_COMPONENTS_WITH_ADDITIVE_P06_FINANCE',replay=f"python3 replay.py --programme {r['programme_id']} --delivery {r['delivery']} --scenario {r['scenario']} --response {r['response']} --mode overview")
            f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    cards=[]
    for p in ps:
        pid=p['programme_id'];r=j('evaluations/'+pid+'__phased__base__passive.json');s=j('evaluations/'+pid+'__phased__cautious__passive.json')
        cards.append(dict(programme_id=pid,label=p['label'],family=p.get('family','KEEP'),city=p.get('city','SVX'),source_programme_ids=p.get('source_programme_ids',[]),source_manifest=p.get('source_city_manifest'),programme_sha256=b.digest(p),before='Условный будущий KEEP: E1 занят; те же новые working tails усиливают шесть маршрутов SVX; полный фактический RW KEEP не установлен.',after=dict(working_slots=p['working_slots'],transfers=p.get('transfers',True),peak_sunday=p.get('peak_sunday',False),end2028_pairs=r.get('end2028_pairs'),projected_unique_pairs=r.get('unique_pairs_end2028')),resource='phased/partial/delayed/none; один новый SJ100 резерв N1; рабочиеN2–N4; E1 SSJ100 сохранён',value_mechanism='Беспересадочная поездка и выбранная частота; для hub дополнительно совместный transfer product с двумя расходами кресел. Own migration не идентифицирована.',competition=dict(rows='competition/*.csv',lineage='competition_row_lineage.json',choice='Общий P05 outside composite и адресный response10; не подтверждённая будущая ёмкость конкурента',absence_of_found_service='UNKNOWN, не нулевой рынок'),result_refs=[f'evaluations/{pid}__phased__{sc}__passive.json' for sc in ['base','cautious']],status_base=r['status'],status_cautious=s['status'],change_choice=['Реальный OD/тариф/ownsales меняют сравнительные поездки и выручку','База/start/exit/добавочный fixedcrew/MRO выше остаточного порога меняют выбор','AFM/маршрут/crew/ТО могут требовать иной календарь','Новый международный/through opportunity меняет альтернативное применение'],individual_author_recipe_status='Смотреть candidate_dispositions.csv; общий городской вариант не закрывает неисполненный рецепт',source_network_status='PROPOSED_SCENARIO_NOT_PUBLISHED',dispatch_ready=False,global_optimum=False))
    b.dump(P/'programme_cards.json',cards)
    ssj=j('existing_ssj/summary.json')
    b.dump(P/'data_contract.json',dict(version='P09-delivery-v1',language='ru',source_root_pin=template['source_research_pin'],UI=dict(index='ui/index.json',projection='projection_contract.json',mode='P06_FIXED_COMPARE_CANONICAL_EXACT_FIELD_PROJECTION',acceptance='PENDING_COORDINATOR_ACCEPTANCE',do_not_replace_with='overview CSV or recalculated UI totals',preserves='Exact JSON numbers, null, units, period, statuses, context; no revenue reaggregation'),overview=dict(results='scenario_results.csv',monthly='results_monthly.csv',input_manifests='evaluation_input_manifests.jsonl',result_mode='P06_DISJOINT_DATE_COMPONENTS_WITH_ADDITIVE_P06_FINANCE',csv_null='UNKNOWN text; not0. This CSV convention is not the JSON projection.',numeric_equivalence='canonical_equivalence_checks.json; no equal bytes claim',programme_additivity='ALTERNATIVES; never sum different programme rows as launched network'),geometry=dict(flights='dated_flights.csv',assignments='assignments.csv',fleet='fleet_calendar.json',monthly='resource_monthly.csv',UI_sidecar='ui_resource_monthly.json',network='network_end2028.csv',scope='9finalists ×4resourcebranches, proposed calendar; all others deterministic builder'),existing_ssj=dict(path='existing_ssj/',mode='EXISTING_SSJ100_TRANSFER_NO_NEW_SEPARATE_RESOURCE_GROUP',programmes=ssj['programmes'],evaluations=ssj['evaluations']),international=dict(path='international/',mode='OPPORTUNITY_THRESHOLD_WITH_FOREIGN_REVENUE_SYMBOLIC',new_Tu214=0),claims=dict(full_profit=None,whole_company_funding=None,reported_market_share=None,rank2_date=None,global_optimum=False)))
    lines=['| Программа | Сценарий | Δ поездок | Δ выручки, руб. 2026 | Порог непокрытых расходов, руб. 2026 |','|---|---|---:|---:|---:|']
    for r in canonical:lines.append(f"| {r['programme_id']} | {r['scenario']} | {r['delta_journeys']} | {r['delta_revenue_net']} | {r['missing_cost_headroom']} |")
    text('choice_report.md','''# Сравнение сетевых программ Red Wings на 2027–2028 годы

Получен вычислимый сравнительный пакет на едином P05 и неизменённом P06 982f13d. В основной матрице 178 альтернатив и 11 сценариев: 1715 условных расчётов и 243 случая невыполнимости конкретного построенного календаря. Это не совместный запуск всех городов. В каждом опыте общий спрос и кресла распределяются совместно; результаты независимых программ не складываются.

## Самостоятельный CASE_SJ и ресурс

Действующий SSJ100/SaM146 и будущий SJ100/ПД-8 имеют разные идентификаторы. Параметры нового самолёта — явно отмеченный аналог SSJ, а не подтверждённая характеристика ПД-8. В основном сравнении E1 сохраняет условную старую сеть SVX–UFA/OMS/REN/GOJ/PEE/MCX. Новые рабочие борта в KEEP усиливают эти направления. Поступление не объявлено графиком Red Wings: передача за 30 дней до ввода; phased — N1 01.08.2027, N2 01.11.2027, N3 01.04.2028, N4 01.09.2028. N1 резервный, коммерчески работают N2–N4. Partial ограничен N1/N2; delayed вводит N1 01.07.2028 и N2 01.11.2028; none не получает новых бортов. Одинаковые переданные борта и неизвестные платежи за них присутствуют в P и KEEP, включая простаивающий резерв.

Отдельная ветвь `existing_ssj/` сравнивает 21 малую программу переноса занятого E1 с сохранением его прежней работы: 84 опыта base/cautious × passive/response10. Новых SJ100 и Ту214 в ней нет. Перегон и потерянные продажи старой сети пересчитаны вместе; повторное вычитание «донора» не применяется. Три пары — промежуточная ступень на одном действующем самолёте, а не исполнение целевой сети 8–12 пар. Резерв, доступность и экипаж E1 не доказаны. Числа этой ветви не сопоставляются с основной матрицей как будто ресурс одинаков.

## Построение сети и проверка гипотез

Каталог сохраняет 223 авторских рецепта, 169 локальных гипотез и происхождение 35 исторических формулировок. `candidate_dispositions.csv` различает выполненную привязку исходных московских ordered paths, общий парный screen и неисполненный индивидуальный Stage B. 57 московских рецептов привязаны с сохранением последовательности плеч и дней недели, но с условным ресурсом/KEEP P09. Для 30 есть условная экономика с работающим новым бортом; 27 нарушают конкретный календарь, их экономика NOT_RUN. Нулевой запуск в ветви none не считается испытанием авторского пути. Непривязанный рецепт остаётся OPEN. Ни расстояние 500 км, ни наличие конкурента, ни низкий прежний score не использованы как экономический отказ.

Для каждой из 20 городских областей и SVX построены прямые и волновые конструкции; добавлены смешанные сети, одинаковые рейсы без продажи пересадок, полные девятилучевые банки для подходящих коротких плеч и сезонные частоты. Предварительный один оборот 03.04.2028 служит правилом выбора конструкции, а не годовой экономикой. Полный расчёт использует все 731 даты и помесячный P05. Диагностическая неделя P03 11–17.12.2028 не умножается на 52 и не объявляется годовой сетью. MRV принят позднее: авторские рецепты внесены в происхождение и остаются индивидуально OPEN; уже рассчитанная конструкция MRV выбрана из общего P05 prior, её нельзя объявлять точным исполнением позднего авторского рецепта.

`programmes.json` содержит частотные структуры; `programme_cards.json` — before/after, ресурс, конкурентную трактовку и условия смены выбора. `dated_flights.csv`, `assignments.csv`, `fleet_calendar.json` содержат полный календарь девяти финалистов во всех четырёх ресурсных ветвях. Радиальная программа обычно имеет 2 оборота на пару в неделю; банк — 4 при допустимом времени. На конец 2028 года финалисты имеют 8–9 уникальных проектных airport pairs, включая отдельный контроль развития существующего хаба SVX_BANK9. Существующая сеть E1 добавляется отдельно и не обнуляется. Кодшер WZ на чужом операторе, в том числе NordStar/VOG, не создаёт собственный SSJ.

## Спрос, продукты и конкуренция

P05 содержит 39840 месячных строк, 830 направлений и два сценария. Его OD/choice статус SCENARIO_NOT_IDENTIFIED сохраняется. По каждой дате P05 строит поездки и тарифы; P06 совместно распределяет спрос и места на физических плечах. Сквозной тариф начисляется поездке один раз. Два плеча пересадки расходуют два кресла. Изменение суммарных собственных продаж наблюдается в модельной дельте, но индивидуальные переходы old→new не идентифицированы: это не измеренная каннибализация.

Для P и KEEP используется объединение OD/date и одна outside/response policy. Конкуренты отражены P05 outside composite. Отдельно выполнен адресный response10 из P05-A13: −10% условной цены представителя существующего воздушного предложения в затронутом OD/date. Это не утверждение о будущих рейсах и креслах конкретной авиакомпании. В `competition/` сохранены относящиеся к 154 парам строки P02; происхождение в `competition_row_lineage.json`. SOURCEEXPORT, through label и опубликованная цепочка не являются принятой физической ёмкостью. Не найденный рейс означает пробел покрытия.

Цены предложенных продуктов имеют as_of 12.11.2026 и booking lead 30 дней как сценарий. Они не являются предложениями на будущую продажу. P01_MONTHLY используется как контекст: 133 segment-наблюдения, 86 airport-month; 36 UT carrier-month включают 9 вертолётных. Подтверждённых endpoint OD нет. Нельзя суммировать overlap groups, устранять различия определений KJA или объявлять общую месячную сезонность валидацией маршрутного OD.

## Условное множество решений

Pareto frontier построен без весов и вероятностей по минимуму base/cautious для Δ поездок и Δ известного операционного subtotal. В него вошли VOG_RADIAL, MRV_HYBRID, AER_HYBRID, VOG_HYBRID, AER_SEASONAL. Дополнительно сохранены KUF_RADIAL, SVX_RADIAL, SVX_BANK9 и VOG_BANK9 как контроль существующей базы, существующего хаба и новой волновой базы. Это лучшие найденные конструкции в данной области, не глобальный оптимум и не рыночная рекомендация открыть базу.

Ниже точные поля канонического P06, без округления. Положительный порог означает допустимую суммарную разницу ещё не покрытых расходов при фиксированных остальных неизвестных; отрицательный требует дополнительного дохода/экономии. Полная прибыль во всех строках неизвестна.

'''+ '\n'.join(lines)+'''

## Чувствительность и пересмотр

`connection_value_controls.csv` отделяет эффект продажи пересадок на тех же рейсах от эффекта числа рейсов. Первичные HUB с длинными лучами местами переходят в радиальную ступень; это записано в open_work, а не скрыто под названием хаба. Полные BANK9 проверяют отдельную волновую конструкцию. `sensitivity_response.csv`, `sensitivity_schedule.csv` и `daily_resource_limit_checks.csv` показывают ответ конкурента и ограничения ресурса. Из 36 опытов с множителями трассы 1.10/1.20 условно посчитаны 22, ещё 14 нарушают построенный календарь. Точки взяты из P03 как чувствительность, не доверительный интервал. План с геодезическим временем не даёт dispatch PASS.

Выбор меняют реальные месячные OD/ownsales, полная цена базы и перехода, доступный ресурс crew/ТО, разрешённые трассы/нагрузка, локальные цены и результат альтернативного международного применения. Часть ранних ступеней может ухудшать результат; решение требует финансируемой траектории и условий остановки, а не обязательной прибыли первого месяца.

Отчётные пассажиры пока не вычисляются. Новый P10 требует один пассажирский учёт на reporting flight, совместимый boarding group и carrier/group definition; proposed physical flight_id сам по себе не такой адаптер. Journeys и passenger segments показаны отдельно. Reported share, общий объём Red Wings и дата достижения №2 UNKNOWN.

## Дополнительные ветви

`international/` резервирует два оборота в неделю под SVX–URC и KUF–IST и пересчитывает потерю внутренних продаж общим P05/P06. Получены 384 месячных порога международной net revenue минус недостающие расходы. Международный OD, SPA, иностранные ставки/FX, полезная нагрузка и доступ не установлены; полная международная выручка UNKNOWN. Новых Ту214 — 0; существующий международный/чартерный бизнес не объявляется нулевым. Другие международные рецепты остаются OPEN.

P11 digital uplift и H-EXPERT-NET-CARGO-01 не прибавлены к базовой выручке. Для cargo/mail неизвестны поток, договор, полезная нагрузка и себестоимость. Нужен отдельный совместный расчёт пассажиров/груза, если источники подтвердят гипотезу.
''')
    text('economics_report.md','''# Экономика, денежные потоки и неизвестные

Численные результаты являются условным сравнением сетей на одном ресурсе. Известный subtotal включает выбранные P04 reference-компоненты и явные аналоги. Он не является переменным вкладом с полным покрытием, прибылью Red Wings или полным бюджетом запуска. В P06 поля полного variable contribution, operating result и финансирования сохранены null.

## Что рассчитано

По фактическим датам предложенного календаря рассчитаны блок-часы, циклы, условный расход топлива, почасовые crew/MRO/navigation, движения самолёта и пассажирские сборы. P04 points base/cautious: 1.55/1.9 т топлива на час плюс 0.20/0.25 т на цикл; UFA 136300 руб./т; MRO 35000/55000, crew 15000/22000, navigation 6000/8000 руб./час. Это исторические/аналитические reference-параметры с точными источниками в P04 и parameterledger. Полёт SJ100/ПД-8 на этих параметрах — отдельный перенос по аналогу, не ставка будущего борта. Дальность/время/100 кресел/MTOW49.45 также сценарные профили.

Для аэропортов применены закреплённые ставки P04 и локальные corrections: AER, GSV, KJA, KZN при подходящих RUB/t и price_year2026. Старые BAX2024, IKT2022, MCX2025 остались контекстом и не смешаны молча с ценами2026. Недостающий местный компонент использует помеченный UFA-аналог. Ставка 2026 не является инвойсом Red Wings2028; инфляционная индексация, договорные скидки и часть услуг остаются неизвестными. Общий HIST pax500/650 не добавлен поверх терминальных ставок из-за неизвестного пересечения покрытия.

Поддержка принята равной нулю только в явной ветви «без поддержки». SK Discount не начислен как автоматическое право; истёкшие REN/AER и неподходящие условия ≥150/110 кресел либо 5 tails/300 departures не применены. Ненайденная субсидия не объявляется доказанным отсутствием будущей поддержки.

## Полная дельта как функция

Для каждого опыта `thresholds.csv` сохраняет H = Δ known_operating_subtotal. При одинаковой трактовке доходов:

`Δ полный результат = H − Δ недостающих расходов + Δ иных неизвестных доходов`.

В недостающие расходы входят residual базовые расходы, запуск/выход, невключённый fixedcrew/MRO, необходимый дополнительный резерв и результат затронутого, но не описанного собственного бизнеса. Остаточные части должны быть непересекающимися: одинаковый расход нельзя вновь добавить поверх почасового аналога. Положительный H не доказывает приемлемый полный результат. Отрицательный H не означает отказ всем возможным расписаниям города.

`max_extra_station_cost_per_month` — H, разделённый на число месяцев коммерческого этапа в конкретном сценарии, при фиксации всех остальных неизвестных. Это одиночный порог, не одновременный бюджет базы, экипажей и запуска. Максимальная единичная цена запуска аналогично равна H только при нулевой разнице прочих остаточных компонентов. Без обоснованного диапазона не подставляется произвольное ±процент.

`threshold_driver_coefficients.csv` дополнительно задаёт коэффициент Δ блок-часов для неизвестной остаточной ставки crew/MRO сверх уже включённого аналога. При отрицательном коэффициенте неравенство даёт нижний, при положительном — верхний порог; при нулевом ставка сокращается. Это одиночная условная чувствительность, не подтверждённый бюджет.

Одинаковые committed tails во всех основных P/KEEP сохраняют неизвестные aircraft-use события, даже если резерв или рабочий борт простаивает. Коэффициент одинаковой общей ставки tail-month в P−KEEP равен 0, но сама ставка UNKNOWN. Отличающиеся лизинговые условия, penalties, расходы перегона/переноса и residue автоматически не сокращаются. Перегон включён в известные драйверы; неизвестный договорный остаток сохраняется. `investment_no_acquisition.csv` отдельно сравнивает наличие новых бортов с отсутствием приобретения: там цена tail-month уже не сокращается. Это отдельная инвестиционная ветвь, её нельзя использовать как сравнение на одинаковом парке. Lease и depreciation не складываются.

## Будущий KEEP и сохранение бизнеса

Внутренняя базовая сеть E1 и применение новых бортов в KEEP — объяснимый сценарный контрфакт, не восстановление всего фактического бизнеса. Спрос P и KEEP совместный. Сохранённые направления не продаются повторно в независимых городских моделях. В ветви переноса действующего SSJ удаление старых рейсов проявляется в общем изменении продаж и затрат; отдельный повторный donor deduction равен нулю по правилу недопущения двойного счёта, а не потому что прежний бизнес бесплатен.

Пустой фрагмент P03 не использован как пустая авиакомпания. Неизменный остаток бизнеса сокращается только при явно принятой неизменности; затронутые международные own/through продажи и альтернативное использование остаются переменными. Если этот остаток материально отличается, текущий порядок вариантов может измениться. Полный исходный KEEP/coupon/contract roster нужен для финального решения.

## Денежные потоки

Сценарный лаг получения билета — 30 дней до полёта, известных переменных инвойсов — 30 дней после конца месяца начисления. Начало cash horizon — декабрь2026, последний месяц полётов — декабрь2028; платежи после горизонта и opening/terminal obligations остаются в полном P06. Неизвестные prelaunch, депозиты, capex, exit/возвраты, налоги и проценты не заменены нулями. Начальный unrestricted cash и minimum cash неизвестны. Известный диагностический пик при opening=mincash=0 не равен потребности компании в финансировании.

При известном календаре недостающих платежей полный incremental funding до финансирования задаётся функцией:

`F = max(0, max_t[minimum_cash(t) − opening_cash − cumulative_known_delta_cash(t) + cumulative_missing_net_outflows(t) + interest_cash(t)])`.

Разбиение должно исключать двойной счёт процентов. Необходимо отдельно учитывать дневной/внутридневной минимум; P06 day-end — нижняя граница при неизвестном внутридневном порядке. Данные companyKEEPcash отсутствуют: whole_company_funding UNKNOWN, нельзя прибавить delta к выдуманному остатку. `project_incremental_funding` и `project_pre_interest_funding_diagnostic` различаются и сохраняют статусы ядра. Полная прибыль/окупаемость и дата выхода на неё не установлены.

## Что уточнить для решения

Нужны договоры tail lease/передачи/ввода и действующие задания; crew roster и фиксированная часть оплаты; резервы ТО и типовые ставки SJ100/ПД-8; базовые договоры/запуск/выход; реальные airport/fuel/handling invoices по каждой станции; opening balances, deposits, future обязательства и cashlags; билеты/купоны для полного собственного перетока; international SPA и альтернативное применение. Регистр `parameterledger.json` задаёт источник, выбранное значение, диапазон либо UNKNOWN, влияние, чувствительность и путь уточнения. Это Stage B входы, а не доказательства отрицательной экономики.
''')
    text('README.md','''# P09: сравнение программ 2027–2028

Законченный пакет условного вычислительного сравнения; независимая приёмка, рыночная калибровка и полная экономика остаются открытыми.

- `choice_report.md` — результат выбора конструкций, before/after, ресурс, спрос, конкуренты и ограничения.
- `economics_report.md` — известные компоненты, полный результат как функция, пороги и финансирование.
- `programmes.json`, `programme_cards.json`, `candidate_dispositions.csv` — рассчитанные конструкции и отдельные исходы авторских рецептов.
- `scenario_results.csv`, `results_monthly.csv`, `thresholds.csv` — обзор основной матрицы; `canonical_summary.csv` — точные поля канонических финалистов.
- `dated_flights.csv`, `assignments.csv`, `fleet_calendar.json`, `resource_monthly.csv` — 24-месячные календари финалистов во всех ресурсных ветвях.
- `ui_resource_monthly.json` — подготовленные месячные сценарные числа переданных/введённых/резервных бортов; фактическая project_available остаётся null.
- `existing_ssj/` — отдельное применение действующего SSJ100 без новых самолётов; `international/` — международные opportunity thresholds с 0 новых Ту214.
- `ui/index.json`, `projection_contract.json`, `data_contract.json` — P12/P15 интерфейс. ACCEPTANCE PENDING; исходные fullcompare в `ui_results/*.canonical.json.gz`.
- `common_input_template.json`, `evaluation_input_manifests.jsonl`, `root_pin_promotion.json`, `input_pins.json`, `sources.csv` — pins, hashes и происхождение.
- `roadmap.json`, `handoff.json`, `validation.json`, `manifest.json` — действия, проверки и границы передачи.

## Воспроизведение

Из каталога P09, Python3 без сторонних зависимостей:

```sh
python3 replay.py --programme VOG_RADIAL --mode overview
python3 replay.py --programme VOG_RADIAL --mode canonical
python3 replay.py --programme SSJ_VOG_RADIAL --delivery none --existing-ssj --mode overview
python3 validate_package.py
```

По умолчанию replay сохраняет только proof, собственную временную копию удаляет после проверки SHA. `--save` оставляет копию в `replay_runs/`. Проверяются закреплённые subject bytes, движущиеся P05/P06 не читаются. Режим canonical доступен для сохранённых канонических контролей; остальные вычисляются overview и имеют детерминированный input manifest. Не запускайте capture/construct как команду проверки опубликованного пакета: они создают новую версию каталога, тогда требуется отдельный release и impact assessment.

`early/` неизменён. Известная ошибка раннего общего ferry generator исправлена в основном builder; двухдневный early control остаётся историческим результатом своей версии. Более поздняя basename-collision при копировании P01 обнаружена сравнением exact Git bytes и исправлена до численного использования; `capture_corrections.json` сохраняет историю. P01 не изменял спрос P05.

Все программы альтернативные. Сценарные значения не доверительные интервалы. CSV использует UNKNOWN для null только как формат экспорта; UI JSON сохраняет настоящий null и точные числа. P06 PASS исполнения не равен market/dispatch/finance acceptance.
''')
    open_items=[dict(id='P09-B01',status='OPEN',work='Привязать неисполненные авторские рецепты индивидуально или доказательно объединить/отклонить',artifact='candidate_dispositions.csv',owner='Координатор + городские Stage B'),dict(id='P09-B02',status='OPEN',work='Полный фактический futureKEEP/ownsales/affected international/through; coupon migration',owner='P03/P05 + RW'),dict(id='P09-B03',status='OPEN',work='AFM/OFP, slot/access, crew/MRO и доступный ресурс по хвостам; исправить конкретные infeasible calendars',owner='P03 + города'),dict(id='P09-B04',status='OPEN',work='Локальные OD/тарифы и внешние альтернативы для эмпирической идентификации P05',owner='P05 + города'),dict(id='P09-B05',status='OPEN',work='Договорные цены/база/start/exit/reserve/fixedcrew; opening/mincash/interest/prelaunch/terminal',owner='P04 + RW'),dict(id='P09-B06',status='OPEN',work='Совместимый P10 reported passenger adapter + carrier/group scope + fullcompany denominator',owner='P10'),dict(id='P09-B07',status='OPEN',work='Независимо принять исполнение, source applicability и полные выводы; перевести UI marker только после gates',owner='Координатор/P13/P15'),dict(id='P09-B08',status='OPEN',work='Остальные международные гипотезы, foreign OD/SPA/FX/access/payload и own alternative',owner='P02I/P05/P03/P04'),dict(id='P09-B09',status='PROPOSED_NOT_APPLIED',work='Экспертный cargo/mail и P11 causal uplift; без добавки в базовую выручку',owner='Эксперт/P11')]
    b.dump(P/'handoff.json',dict(status='COMPLETED_CONDITIONAL_COMPARISON_PACKAGE',source_research_admitted=True,market_operations_financial_acceptance=False,engine_pin=template['engine_pin'],source_root_pin=template['source_research_pin'],main=bs,existing_ssj=ssj,UI=dict(index='ui/index.json',projection_contract='projection_contract.json',canonical_comparisons=18,acceptance='PENDING_COORDINATOR_ACCEPTANCE',coordinator_action='Проверить manifest, закоммитить только P09 и создать отдельный accepted envelope с exact commit/manifest; не переписывать canonical result'),independent_acceptance='PENDING',open_stage_B=open_items,new_Tu214=0,children=0,git_mutations=False,external_services=False))
    text('handoff.md','''# Передача P09 координатору

Выполнена общая численная матрица: 178 программ, 1958 опытов, 41160 месячных строк; 1715 условных расчётов, 243 отклонения конкретного календаря. Дополнительно рассчитаны 21 программа переноса существующего SSJ100 в 84 опытах, международные 384 месячных порога и чувствительность расписания. 223 исходных рецепта, 169 локальных и 35 исторических гипотез сохранены отдельно с происхождением и явным OPEN там, где индивидуальный расчёт не выполнен.

Для 9 основных финалистов/архитектурных контролей сохранены 18 полных P06.compare gzip mtime0 и точные проекции P12/P15. Ещё 2 canonical compare контролируют лучшую найденную малую программу существующего SSJ. Исходный P06 — 982f13d; адаптивные исправления координатора сюда не подмешаны. Общий root source intake — 6a6326c. Источниковая приёмка не финансовая.

Координатору: проверить `manifest.json`, `validation.json`, replay proofs и `p12_structure_checks.json`; закоммитить собственную область P09, затем создать отдельно принятый UI envelope с actual commit/manifest. Пакеты сейчас намеренно PENDING. Точные numbers/null/status/context не менять; обзорные CSV не подставлять вместо canonical projection. Браузерная интеграционная проверка и финальная приёмка принадлежат P15/координатору.

Незавершённая обязательная работа перечислена в `handoff.json/open_stage_B`. Этот пакет завершает условный расчёт данного исследованного множества, но не всю стратегию, не все индивидуальные городские Stage B и не доказательство №2. Ни одна открытая ветвь не превращена в экономический отказ. Git-операций, детей, новых платных сервисов, бронирований, внешних сообщений или изменений чужих областей не выполнялось. Авторизованные сообщения координатору и P15 переданы через T3.
''')
    print('reports and contracts written')
if __name__=='__main__':main()
