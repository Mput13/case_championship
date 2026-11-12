# API для следующего совместного расчёта

Использовать рабочую копию `/home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804`, не запускать `build()` старых пакетов. Код в `source_snapshot/` — свидетельство версии; импортировать оригиналы in-place: они используют соседние закреплённые P03/P04/P05/P06 и базовые таблицы. Хеши входов — `inputs_manifest.json`, импортируемых зависимостей — `dependency_receipt.json`. `python3 validate.py` проверяет доступность API без пересчёта всего исследования.

## Совместная экономика

`context/31_direct_growth_research_20261112/route_economics/calculate.py`:

```python
re.evaluate_combined_programme(
    patterns, scenario='base', keep_patterns=affected_keep_patterns,
    start='2027-02-01', end='2027-02-07',
    demand_overrides=directed_potential_for_this_horizon,
    donor_loss=None, omitted_F=None, existing_slots=1,
    delivery_scenario='S0', reserve_available=None,
    response='passive', extra_products=None,
    calendar_requests={'P': complete_P_request, 'KEEP': complete_KEEP_request})
```

`patterns`/`keep_patterns` обязательны; в calendar mode физические рейсы берутся из requests. `[]` означает явное отсутствие затронутых продуктов в данной области, не отсутствие старых клиентов компании. Включить одинаковые common OLD_RW markets, сохранённые и отложенные задания в обе сети. Донор внутри P−KEEP уже учтён: `donor_loss` только для потерь вне области. Сумма solo margins запрещена. `extra_products={'P': [...], 'KEEP': [...]}` может делить leg inventory между OD, но требует admission и исключения дублей. Треугольники получают только adjacent OD, никаких автоматических сквозных доходов.

Ключ override — `A>B/2027-02`, значение — потенциальные направленные journeys **за выбранный горизонт**, оно не prorate-ится. Без override prior делится на .6, берётся симметричная половина и месячный профиль, затем доля дней; это сценарий, не наблюдение. Fare API не имеет joint gross_override: `fare(a,b,scenario,gross_override=None)` отдельно существует, но для новых admitted fares нужен явный адаптер формирования joint products. Нельзя считать передачу tariff в screen() обновлением jointcalc.

**Обязательное исправление недельного адаптера:** в `choice_bundle()` частота сейчас `len(inventory)*7/calendar.monthrange(y,m)[1]`. Для горизонта 01–07Feb один вылет превращается в 0.25/week. Перед расчётом в новой области адаптировать знаменатель к длине принятого горизонта/explicit weekly exposure с одинаковой семантикой P и KEEP. Не менять P31. Не присваивать календарю Tue/Fri месячную частоту и не компенсировать ошибку умножением спроса. Месячные граничные окна и горизонты отдельно проверить. Новых денежных результатов этот handoff не выпускает.

Выход: `known_increment_P_minus_KEEP_before_F_donor`, `F_plus_donor_max_RUB`, `full_P_minus_KEEP` (nullable), `cash=None`, `resource_necessary_screen`, `ops_results`. `full_P_minus_KEEP` при переданных F/donor всё равно условен полнотой покрытия затрат; UNKNOWN не 0. Зафиксировать donor/tariff thresholds смены места, а не заполнять пятёрку UNKNOWN.

## Физический календарь

`context/31_direct_growth_research_20261112/ops_inputs/calendar_engine.py`: `generate(request)`.

Request: `tails[{id,type,initial_location,available_from,available_to,reserve,donor,...}]`, `blocks[{origin,destination,nominal_minutes,high_minutes,evidence,aircraft_variant}]`, `timezones{airport:IANA}`, `turn_minutes`, `patterns[{id,path,weekdays,frequency_per_week,start,end,departure_local,workingtailids,operating_weeks?,positioning_leg_indices?}]`. Полный пример — snapshot `ops_inputs/cli_example.json`. Выбранный directed block один на направление/вариант; nominal/high не выдумывать.

Здесь weekdays ISO **1..7** (Tue2/Fri5); geometry `patterns` API использует **0..6** (Tue1/Fri4). На Tue02Feb: SVX–A–B–SVX; Fri05Feb: SVX–B–A–SVX, всего6 секторов, один RT самой пары. Все сервисные соседние рынки занимают кресла; ferry платный и не продаётся. Если A=SVX — обычный RT, без нулевого плеча. Один рабочий существующий RRJ и отдельный условный резерв; variant/route/crew/slots/payload/MRO pending. SJ до01Jul2027 запрещён и в резерве.

8BH engine маркирует как `INFEASIBLE` диагностического envelope: это не запрет по FDP/дальности. При превышении открыть отдельный допустимый по фактам вариант; нельзя молча поднимать лимит и объявлять operational PASS. Геометрический режим без calendar_requests не ops plan.

## Задержки

`context/32_delay_cargo_research_20261112/calculation/calculate.py`: `flight(fid,origin,destination,departure,block,kind,source)` и `replay(flights,turn,shock=0,other_ready=None,initial_ready=None)`. departure — aware datetime UTC. Для AER/пятницы строить flights самостоятельно; `chain(route,layout)` ограничен SVX–OMS/KUF/GOJ и датой02Feb. `initial_ready` передать явно: default18:00 мешает сценарию AER14:00. Shock применяется только к fid `NEW-OUT`. Новый рейс в пятничном отдельном прогоне получает тот же id; в общей цепи нужна явная shock-target адаптация. max(plan,previous_actual+turn,other_ready,shock), без сброса в полночь. Это hold-сценарии, не вероятности задержек; crew/MRO UNKNOWN.

P33 original `KEEP_rotation.csv` сохранён. AER330/150 по UTC против claimed210/210; исправленная условная конструкция14SVX–15:30AER,16:30AER–22SVX (turn60). Следующий калькулятор обязан выпустить отдельный canonical CSV и проверить UTC независимо. В исходных P33 FOLLOW есть дополнительные ошибки: KUF подписан Asia/Yekaterinburg вместо Europe/Samara, нулевые turns, длительности235/160 вместо P32 направленных100/100. Не переносить эти строки: использовать контролируемые четыре FOLLOW P32, в одинаковом варианте P/KEEP. Реальный хвост, блоки и слоты всё равно UNKNOWN.

## Admission

Готовые P08/P09/P15 дают сохранение гипотез, provenance, условные программы/результаты. `VERIFIED` не заменяет проверку первичного текста, дат, coverage и собственных продаж. P09 `SCENARIO_NOT_IDENTIFIED`, full acceptance false; phased2027–28 не сравним с E1 target week. P15 binding OPEN. P08I отсутствует по реальным именам путей всех локальных origin refs (см. availability), это не отсутствие P08 и не доказательство отсутствия ещё не fetched пакета.

Внешние completed research A/B в этом этапе не читались. Следующий jointcalc принимает их после handoff, обновляет dated coverage/novelty и переводит confirmed RW nonstop в frequency comparison. Заявлять NO_DIRECT можно только для полного датированного покрытия. Текущий seed содержит12 UNKNOWN-кандидатов, не топ-5.
