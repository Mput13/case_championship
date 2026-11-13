# P40 budget — completed handoff, 13.11.2026

Готов модуль авторского бюджета недостающих операционных расходов: 17 единичных параметров, два OMS station BoQ, запуск/capital/working capital и правила неттинга. Это расчёт planning scenario, НЕ фактический PnL и НЕ team-approved ставки. Сеть не менялась: сезонный OMS9 + MOW–GSV–MRV–MOW и MOW–AER–VOG–MOW; deck7+3=10 бортов — исходная рамка, не пересчитанная здесь физика. Покупка/лизинг/финансирование ВС вне MAIN по последнему указанию пользователя.

Прочитаны P40 TASK/pins/deck и completed P39 README, COST_TABLE, 34 OMS prices, research_fleet, fleet_price_recovery, model_audit coverage. P04 cost_ranges содержит127 строк: MRO35/55k BH и crew15/22k BH — сценарии, а payroll/insurance/lease/launch blank — UNKNOWN, готовых цен оттуда не взято. Хеши локальных входов в sources/local_inputs.json.

## Какой бюджет уже посчитан

station_totals.csv: только собственная OMS station при сохранении12 месяцев, сверх выбранного outsourced handling:

| Вариант | low млн ₽/год | base | high | base FTE |
|---|---:|---:|---:|---:|
| lean_outsource | 5.859 | 8.388 | 12.504 | 4.905 |
| expanded | 11.704 | 16.411 | 24.180 | 10.476 |

Внутри: руководитель станции, transfer coordinator, airline local ops, часть IT, офисные лицензии, связь, маленькое рабочее помещение, хранение и офисные материалы. Ground96 089/115 307 ₽/flight сохраняется один раз. Не раскрыто, какая доля этой корзины действительно оплачивает конкретную услугу; таблица не выдаёт сценарный handler scope за подписанный договор.

Lean: руководитель1×8ч×250дней, coordinator1×8×365, localops1×8×365, IT400ч/год; expanded: руководитель тот же, coordinator2×12×365, localops1×16×365, IT1000ч. Покрытие — авторская проектная раскладка до roster. FTE=post-hours/effective-hours; фонд1800/1680/1560ч low/base/high. FTE — непрерывный эквивалент, не обещание собрать целочисленный сменный график. Если реален неполный аутсорс/совмещение, нужны подтверждённые доступные часы; если штатные сотрудники нанимаются целиком, округлять по группам совместимости смен и проверять roster. Руководитель не заменяет ночного дежурного. Допначисления25/32/40% уже в loaded payroll, это сценарий, не юридическая ставка; повторно не добавлять.

Handling по выбранному дизайну покупает обычную регистрацию/обслуживание пассажиров, загрузку/багаж, ramp/GPU/трапы/бусы. Свои посты — контроль договоров/решения по стыковкам/эскалация сверх handler. При включённом handler coordinator сначала убрать совпадающие часы из BoQ. Полный аэропортовый штат, лётный штат, своё GSE и стройка ангара/терминала не добавлены. MRO потребление остаётся35/55k BH, а crew15/22k BH — уже включены.

launch_totals.csv (получен из oneoff_cash.csv) отделяет CAPEX, oneoff expense, refundable deposits. Для lean low/base/high выбранный launch cash2.698/6.304/14.456млн, expanded3.060/6.840/15.280млн. Это только показанный модуль станции с общим pool-deposit2/5/12млн, не общий бюджет запуска авиакомпании. В base lean: CAPEX0.640млн, разовый расход0.646млн, депозиты5.018млн. Pool deposit — авторский cash buffer с неподтверждёнными договорными условиями возврата, не годовой ремонт. Первичный свой stock не выбран в outsource/pool-дизайне; нулевая строка означает выбор схемы, а не нулевую цену ЗИП. Схемы lean/expanded альтернативны, общий pool берётся единожды.

## Как подключить физику

budget_api.py не содержит сетевых частот или новых пассажиров. evaluate(exposures, scenario, variant, residual_before) принимает единицы за нужный период; все ключи количества перечислены в колонке qty cost_parameters.csv плюс oms_retained_months. Значения покрытых услуг должны быть scope-net: не весь объём рейсов, если услуга уже оплачена. Пропущенные количества явно перечисляются missing_exposures, поэтому частичный расчёт не называется полным. Явный0 допустим лишь как подтверждённое отсутствие/покрытие либо явно названный тест.

```python
# Импорт через sys.path из абсолютного budget-каталога; Python3 -B.
from budget_api import evaluate
result = evaluate(exposures, 'base', 'lean_outsource', residual_before=audited_residual_RUB)
```

Для CLI: `python3 -B /home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/40_hybrid_costs_20261113/budget/budget_api.py --exposures /absolute/path/exposures.json --scenario base --variant lean_outsource --residual <RUB>`.

OMS: retained months — календарное содержание станции, не недельные частоты рейсов. Зимнее сокращение полётов не делает фиксированную зарплату/помещение бесплатно. Для года передать суммы сезонных физических единиц; фиксированную станцию считать один раз. Если меняются часы смен по сезонам, заменить post-hours соответствующими периодами, а не автоматически умножать весь BoQ на долю вылетов. Direct: существующая MOW база не строится заново; дополнительная мощность только параметром mow_extra. GSV/MRV/AER/VOG — четыре уникальные станции; если OMS и direct используют GSV/VOG, фиксированный station-month нельзя списать дважды. Инкрементальную станцию можно распределить между сетями, сумма распределений должна равняться фактически оплаченному уникальному объёму.

Страхование входит в MAIN как отдельный **авторский** параметр3/8/20млн ₽/aircraft-year (при10 полных tail-years30/80/200млн). Актуальная RW premium UNKNOWN, market corridor не найден; выбранные числа — широкие бюджетные уровни для проверки доступности, не оценка актуарной достаточности. RW insured value78bn и начальный тендер без периода не премия; историческая аренда SSJ2015 не используется. Рабочие и резервные tail-time включить один раз. Не добавлять новый резерв сверх deck7+3 без отдельного обоснования.

## Лучшие нормировки и пороги

- station_totals.csv и station_BoQ.csv: perstation-year, perpost-hours, perFTE-month; все rate×qty×frequency воспроизводимы.
- normalizations.csv: DCS на1000 **непокрытых** вылетов10/30/80тыс ₽; outstation callout300/700/1500тыс; station SLA120/300/720тыс за12 station-month. Callout и readiness имеют разные scope, совместный договор неттировать.
- OMS parking117100/aircraft-month — первичный тариф, не автоматическая добавка; за12 непокрытых месяцев1.4052млн/борт, за84месяца9.8364млн. Месячную/почасовую/суточную схемы не складывать.
- Extra bag4450/**service по заявке**, desk1229.51/**workplace-flight/service**: считать дополнительные заказы, не весь transfer pax и не количество FTE; desk не DCS. Нулевое число extra orders в обычной работе допустимо, цена услуги не ноль.
- Hotel4100 single и4650 double — room-night RO аналог2026. Одна crew aircraft-night не даёт число людей/номеров. assigned_rooms группирует по дате/событию/совместимости, округляет double до целого внутри группы; одно person-night нельзя разместить одновременно single и double. Для MOW/курортов эта цена лишь локальный аналог OMS, нужен договор города.
- irrops_normalization.csv: на100 affected journeys227500/765000/2680000₽ без транспорта/раздачи; это авторская смесь исходов (2275/7650/26800 заaffected journey), не частота. Допущение affected share0.2/1/3% и ночи/питание/rebook отдельно в assumptions. Каждое можно заменить фактом. Bus3430/started-hour; food закупка отдельно от операции раздачи3275/service. Не умножать автобус на всех людей, не удваивать уже купленную доставку.
- insurance_sweep.csv: нормированный reference headroom100млн,10tail-years, только station base и insurance; это unit test, не принятый бюджет и не остаток deck568млн. Строка0insurance — математический край свипа. unknown_sweeps.csv — дополнительные свипы цены зарплаты одного поста и DCS, также с нормированным headroom.
- API для каждого неизвестного тарифа возвращает точный порог `maximum_rate=(residual_before - other_selected_costs)/quantity`; в station_rate_thresholds аналогично для loaded salary, лицензий и помещений. Отрицательный порог означает, что остаток уже исчерпан прочими выбранными расходами; qty0 → null, не бесконечный бесплатный лимит. Для вероятности affected journey порог `remaining_headroom / (transfer_journeys * cost_per_affected_journey)`; нужно заранее зафиксировать event mix, транспорт и остальные затраты.

## Достоверность и налоги

sources/priceclass.csv классифицирует PRIMARY / ANALOGUE / ANALYST_SELECTED_PLACEHOLDER / UNKNOWN. hh первичный список: Top Avia Standard(Kazan)65–70k net, M-X-M(Moscow)from84k net, Omsk IT Academy40k gross. Это не предложения RW в Омске. Карточки недоступны, publication date UNKNOWN; дата доступа13.11.2026 не выдаётся за дату вакансии. Авторские gross75–115k operational и100–170k manager не получены точным налоговым преобразованием net; ответственность/география/будущая комплектация оправдывают широкий сценарий. Источники/точные вызовы/ошибки сохранены в sources; сторонние резюме/персональные контакты не публикуются.

IT Astra: первичный источник подтверждает месячное сопровождение, численной цены не дал. DCS10/30/80 и офисные лицензии3/5/8k заseat-month — только авторские малые предельные бюджеты сверх существующей системы, не стоимость создания всей PSS. Ноутбуки65/85/110k/device округлены от розничных офисных аналогов, airport DCS принтеры/стойки не закупаются повторно. Связь, office rent, training/setup и depot allowance — явные placeholders с раздельными единицами.

OMS тарифы «кроме того НДС», численная ставка/возмещаемость не подтверждены. Прайсовые суммы сохранены exVAT, hotel/retail как опубликовано с неизвестным tax scope. Итоги — бюджет без полной invoice tax bridge. invoice_cash_bridge требует явных VAT/recovery допущений, не имеет налогового процента по умолчанию. Только невозмещаемая часть увеличит расход; возмещаемый НДС — cash timing. Типовой OMS100%prepayment из P39 означает working-capital на уже начисленный ground, а не повторный ground expense: extra_working_capital(daily_cash, prepay_days).

## Проверка и границы передачи

Два финальных запуска verify.py pass1/pass2: по222 проверки PASS. Проверены CSV, обязательные metadata, evidence IDs, единицы/умножения, FTE, монотонность low≤base≤high, уникальность групп/отсутствие явных crew/MRO/GSE дублей, stock/deposit против annual, округление номеров, algebraic thresholds, period scaling, недопустимые входы, неизменность прочитанных source hashes. Контрактное отсутствие пересечений код доказать не может: coverage_netting_rules.csv — обязательный gate перед применением.

Повтор из абсолютного workdir: `python3 -B /home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/40_hybrid_costs_20261113/budget/verify.py pass1`, затем тот же pass2. build_budget.py строит основные таблицы, finish.py — provenance/launch/handoff; внешняя сеть для повторения не нужна.

Запись только в budget/. Git mutations/commit/push и общая модель не затронуты. Без субагентов. Поиск остановлен на8queries/12opens-clicks, включая ошибки/повторы; никаких контактов и бронирований. Готовый completed handoff в handoff.json. Root получает параметры и сам присоединяет сезонную физику/проверенный общий остаток; продолжение исследования этим исполнителем не требуется.
