# P39 — готовый расчёт недостающих расходов, 13.11.2026

**Новых обоснованных additions нет; это не значит бюджет 0.** Основной реестр — [COST_TABLE.csv](COST_TABLE.csv): 546 строк =39 статей×14 неизменённых вариантов. Все117 исходных статусов покрытия воспроизведены; полнота модельной формулы не доказывает полноту фактического счёта. Полный годовой бюджет, full PnL, cash и стоимость запуска остаются **UNKNOWN**.

Численно оценены опубликованные единицы и условные коэффициенты услуги. Они отделены от `annual_addition_* = UNKNOWN`; **цена всей услуги по аналогу не равна добавке сверх модели**. Разрешение `REPLACE`/`DO_NOT_ADD`/`CONDITIONAL[_ADD]` и адресный запрос RW есть в каждой строке. Принятых безусловных `ADD` нет.

## Запуск и годовой остаток

| Мера | Принятая сумма | Что требуется |
|---|---:|---|
| Разовый expense запуска | UNKNOWN | BoQ, ввод/обучение/интеграции, объём и уже оплаченный scope |
| CAPEX | UNKNOWN | Собственность, GSE/инструменты/IT, сроки и амортизация |
| Возвратный депозит | UNKNOWN | Договор, сумма, возвратность/зачёт |
| Предоплата | UNKNOWN | Generic OMS §6.7.1:100% объёма обслуживания; signed RW график неизвестен |
| Первоначальный stock ЗИП | UNKNOWN | SKU/количество/цены/собственность; потребление отдельно |
| Peak working capital | UNKNOWN | Даты оплаты/выручки/возвратов и возмещения топлива |
| Новые принятые годовые additions | Нет новых обоснованных additions | Пустая допущенная часть не равна полному бюджету0 |
| Условные сценарии услуги | Числа ниже и в CSV | Нельзя суммировать взаимоисключающие/пересекающиеся функции |
| Оставшаяся неучтённая годовая нагрузка | UNKNOWN | Rent, premium, payroll, MRO scope, F/C/D, сбои и station volumes |

## Экспозиция и точный порог нагрузки

M — неокруглённый subtotal из current replay, уже после модельных вычетов. Порог всей дополнительной экономической нагрузки L: `M−L=0`, то есть L*=M. Для условного годового начисления12 месяцев на каждый объявленный борт: `r*all=M/[12×(working+1)]`; `r*work=M/(12×working)` только при нулевой иной нагрузке и отдельно обеспеченном резерве. Отрицательный порог означает, что положительной допустимой добавки уже нет. Расчёт хранится без округления входной M в [workings.json](workings.json); в таблице ₽/борт-месяц округлены до копеек.

| Вариант | Working+R | Период | Flights / OMS dep | BH | Journeys / segments | L*=M, млн₽ | r*all / r*work, ₽/борт-мес |
|---|---:|---|---:|---:|---:|---:|---:|
| OWNER OMS BASE | 6+1 | 52 model weeks | 7176 / 3588 | 21 396.42 | 388 610.11 / 577 427.28 | 503.022235 | 5 988 359.94 / 6 986 419.93 |
| OWNER DIRECT BASE | 7+1 | 52 model weeks | 10608 / 624 | 25 305.35 | 730 269.90 / 730 269.90 | 44.088100 | 459 251.04 / 524 858.33 |
| OWNER OMS BASE_SUB | 6+1 | 52 model weeks | 7176 / 3588 | 21 396.42 | 388 610.11 / 577 427.28 | 503.022235 | 5 988 359.94 / 6 986 419.93 |
| OWNER DIRECT BASE_SUB | 8+1 | 52 model weeks | 10608 / 624 | 25 680.28 | 729 554.17 / 729 554.17 | 115.317320 | 1 067 752.96 / 1 201 222.08 |
| OWNER OMS CAUTIOUS | 2+1 | 48 model weeks | 2304 / 1152 | 6 710.74 | 63 842.50 / 78 210.48 | -2 345.016394 | -65 139 344.27 / -97 709 016.41 |
| OWNER DIRECT CAUTIOUS | 6+1 | 48 model weeks | 6912 / 864 | 17 763.45 | 363 569.32 / 363 569.32 | -5 281.880988 | -62 879 535.57 / -73 359 458.17 |
| OWNER OMS CAUTIOUS_SUB | 2+1 | 48 model weeks | 2304 / 1152 | 6 710.74 | 63 842.50 / 78 210.48 | -2 264.982186 | -62 916 171.83 / -94 374 257.75 |
| OWNER DIRECT CAUTIOUS_SUB | 5+1 | 48 model weeks | 6912 / 576 | 16 599.13 | 366 054.97 / 366 054.97 | -4 744.470278 | -65 895 420.53 / -79 074 504.64 |
| P38 C0121723 BASE | 2+1 | 2027,365дн | 1356 / 0 | 3 692.02 | 125 005.63 / 125 005.63 | 403.595761 | 11 210 993.36 / 16 816 490.04 |
| P38 C0121723 CAUTIOUS | 2+1 | 2027,365дн | 1356 / 0 | 3 692.02 | 78 160.35 / 78 160.35 | -703.797996 | -19 549 944.33 / -29 324 916.50 |
| P38 W7324… BASE | 2+1 | 2027,365дн | 2192 / 105 | 4 854.77 | 160 860.12 / 160 860.12 | 154.502515 | 4 291 736.53 / 6 437 604.80 |
| P38 W7324… CAUTIOUS | 2+1 | 2027,365дн | 2192 / 105 | 4 854.77 | 85 453.75 / 85 453.75 | -1 296.147878 | -36 004 107.72 / -54 006 161.57 |
| P38 Wa177… BASE | 2+1 | 2027,365дн | 1983 / 105 | 4 450.67 | 138 340.78 / 138 340.78 | 53.131580 | 1 475 877.22 / 2 213 815.83 |
| P38 Wa177… CAUTIOUS | 2+1 | 2027,365дн | 1983 / 105 | 4 450.67 | 45 631.04 / 45 631.04 | -1 590.010814 | -44 166 967.06 / -66 250 450.59 |

Owner52/48 — модельные недели, не365 дней и не основание сократить неизбежную аренду/зарплату на48/52. Фактоплачиваемые борт-месяцы **UNKNOWN**. В P38 датированный completed plan даёт24 активных working tail-months, отдельно1R1; 36 оплачиваемых месяцев — условие удержания всего ресурса весь год. Сети имеют разный парк и состав расходов; это учётные строки, **не рейтинг равночисленного парка**.

Для P38 M выше — standalone REPLACE subtotal. Проектный incremental counterfactual иной:

| P38 | ΔR−W, млн₽ | ΔR−K, млн₽ | r*ΔR−W / r*ΔR−K при всех36 НОВЫХ борт-мес, ₽ |
|---|---:|---:|---:|
| P38 C0121723 BASE | 368.577594 | 557.597923 | 10 238 266.51 / 15 488 831.20 |
| P38 C0121723 CAUTIOUS | -276.451239 | 406.264887 | -7 679 201.07 / 11 285 135.76 |
| P38 W7324… BASE | 308.504677 | 308.504677 | 8 569 574.37 / 8 569 574.37 |
| P38 W7324… CAUTIOUS | -186.084994 | -186.084994 | -5 169 027.62 / -5 169 027.62 |
| P38 Wa177… BASE | 131.286349 | 207.133742 | 3 646 843.03 / 5 753 715.07 |
| P38 Wa177… CAUTIOUS | -647.535368 | -479.947931 | -17 987 093.56 / -13 331 886.97 |

Incremental rent cash существующего борта может быть0 **только** после подтверждения одинакового уже оплаченного графика и отсутствия новых хвостов/продления/endorsement во всех альтернативах; сейчас UNKNOWN. Full-PnL allocation остаётся по договору/учётной политике. Внешний упущенный вклад D — отдельная неденежная поправка, после уже включённых internal old-product deltas. Owner forgone — мигрировавшая выручка, не полный donor contribution. Для finance lease нельзя сложить все платежи, амортизацию и проценты повторно.

## Сопоставимые условные коэффициенты

OMS2026 цены «кроме того НДС», численная текущая ставка/вычет UNKNOWN. Это preVAT sensitivities, не договор2027. HOTEL — опубликованные RUB2026 с неизвестным налогом; его нельзя механически суммировать с exVAT. Нулевая transfer-экспозиция DIRECT/P38 относится только к transfer product; общий риск сбоев UNKNOWN.

| Вариант | 1 extra bag service / OMS dep, ₽ preVAT | 1 пост информирования / OMS dep, ₽ preVAT | 1п.п. transfer journeys ×1ночь single / double, ₽ published |
|---|---:|---:|---:|
| OWNER OMS BASE | 15 966 600.00 | 4 411 481.88 | 7 741 503.89 / 4 389 999.16 |
| OWNER DIRECT BASE | 2 776 800.00 | 767 214.24 | 0.00 / 0.00 |
| OWNER OMS BASE_SUB | 15 966 600.00 | 4 411 481.88 | 7 741 503.89 / 4 389 999.16 |
| OWNER DIRECT BASE_SUB | 2 776 800.00 | 767 214.24 | 0.00 / 0.00 |
| OWNER OMS CAUTIOUS | 5 126 400.00 | 1 416 395.52 | 589 086.93 / 334 055.39 |
| OWNER DIRECT CAUTIOUS | 3 844 800.00 | 1 062 296.64 | 0.00 / 0.00 |
| OWNER OMS CAUTIOUS_SUB | 5 126 400.00 | 1 416 395.52 | 589 086.93 / 334 055.39 |
| OWNER DIRECT CAUTIOUS_SUB | 2 563 200.00 | 708 197.76 | 0.00 / 0.00 |
| P38 C0121723 BASE | 0.00 | 0.00 | 0.00 / 0.00 |
| P38 C0121723 CAUTIOUS | 0.00 | 0.00 | 0.00 / 0.00 |
| P38 W7324… BASE | 467 250.00 | 129 098.55 | 0.00 / 0.00 |
| P38 W7324… CAUTIOUS | 467 250.00 | 129 098.55 | 0.00 / 0.00 |
| P38 Wa177… BASE | 467 250.00 | 129 098.55 | 0.00 / 0.00 |
| P38 Wa177… CAUTIOUS | 467 250.00 | 129 098.55 | 0.00 / 0.00 |

- Багаж4450/дополнительное обслуживание по заявке; не RUB/kg, не на каждого пассажира/стыковку. Условие таблицы — ровно1 заказ на каждый OMS departure. Сценарий отражает всю услугу; добавка UNKNOWN до itemization ground96089/115307 и pax500/650.
- Стойка1229.51/рабочее место на рейс — информирование; DCS/check-in UNKNOWN. Все сетевые departures вместо OMS departures дали бы неверный объём.
- Flagman single4100/room-night; double4650/room-night при2чел. Коэффициент `.01×transfer_journeys×1ночь/occupancy`, не вероятность срыва. Трансфер — одна journey с двумя boarded segments. Для реальных броней нужны целые комнаты по событиям. Breakfast950 — разница пакетов, не standalone рацион.
- На10м² хранения имущества ×12мес: **39 600 /120 000 ₽ preVAT** для unheated/heated; это не здание/ангар и не весь station overhead.
- Автобус3430/начатый моточас; маршрут, вместимость и количество UNKNOWN; цены per-pax нет. Раздача питания3275/обслуживание не включает доказанную стоимость еды.
- Parking:30–74.999т117100/мес,1018/час,24432/сутки;75–99.999т130200/мес,1140/час,27360/сутки. MTOW/договор выбирать условием; **monthly/hour/day альтернативны**. На1год одного оплачиваемого борта месячно1 405 200 /1 562 400 ₽ preVAT. OMS BASE working6×12:8 431 200 /9 374 400; если подтверждено базирование уже существующего R1 там же, весь парк7×12:9 836 400 /10 936 800. Реальные billing months/free window/ground overlap UNKNOWN.
- На1 постоянный пропуск до5лет696.72; разовый209.02; сопровождение4050/обслуживание, preVAT. Телеграммы6.23/55.60 за штуку не заменяют broadband/DCS. Никакой из коэффициентов не задаёт реальный объём заказа.

## Только stress аренды: «2015 RUB номинальный benchmark, без индексации»

`7 560 000/1.18=6 406 779.66101695 ₽ exVAT18/борт-месяц`. Это историческая сухая субаренда другого оператора в судебном пересказе; не текущая цена RW и не основной бюджет. Самолётные месяцы ниже = объявленные working×12 плюс УЖЕ имеющийся1reserve×12 при условии годового удержания. Actual billed months UNKNOWN; USD180000 не конвертирован без доказанного FX.

| Вариант | Working / R / total борт-мес в stress | Full allocation аренды, млн₽ exVAT18 | M минус ТОЛЬКО этот stress, млн₽ |
|---|---:|---:|---:|
| OWNER OMS BASE | 72 / 12 / 84 | 538.169492 | -35.147256 |
| OWNER DIRECT BASE | 84 / 12 / 96 | 615.050847 | -570.962748 |
| OWNER OMS BASE_SUB | 72 / 12 / 84 | 538.169492 | -35.147256 |
| OWNER DIRECT BASE_SUB | 96 / 12 / 108 | 691.932203 | -576.614883 |
| OWNER OMS CAUTIOUS | 24 / 12 / 36 | 230.644068 | -2 575.660462 |
| OWNER DIRECT CAUTIOUS | 72 / 12 / 84 | 538.169492 | -5 820.050480 |
| OWNER OMS CAUTIOUS_SUB | 24 / 12 / 36 | 230.644068 | -2 495.626254 |
| OWNER DIRECT CAUTIOUS_SUB | 60 / 12 / 72 | 461.288136 | -5 205.758414 |
| P38 C0121723 BASE | 24 / 12 / 36 | 230.644068 | 172.951693 |
| P38 C0121723 CAUTIOUS | 24 / 12 / 36 | 230.644068 | -934.442064 |
| P38 W7324… BASE | 24 / 12 / 36 | 230.644068 | -76.141553 |
| P38 W7324… CAUTIOUS | 24 / 12 / 36 | 230.644068 | -1 526.791946 |
| P38 Wa177… BASE | 24 / 12 / 36 | 230.644068 | -177.512488 |
| P38 Wa177… CAUTIOUS | 24 / 12 / 36 | 230.644068 | -1 820.654882 |

**Это остаток после одной гипотезы, не full PnL.** Технический резерв2015 отдельно:2 874 480inclVAT18 =2 436 000exVAT18/борт-мес. Его полный stress есть один раз в MRO_HEAVY CSV и workings; добавка UNKNOWN. Scope/возвратность не раскрыты: не прибавлять поверх MRO35000/55000BH и не называть депозитом/ценой engine repair. Исторический USD и S7USD2023 не стали RUB2027 quote. Страховая стоимость78B и initial tender premium исключены.

## Все39 статей: читаемый указатель основной таблицы

F=полностью учтена указанная модельная формула; P=частично; A=нет в формуле; U=нераскрытая корзина. Все отсутствующие денежные суммы UNKNOWN. Для каждой строки/варианта CSV содержит точный code/table:line, существующий annual amount, actual exposure, цену/дату/налог, полную стоимость нормировки, gate добавки, cash classes, source/reliability и точный запрос RW.

| Статья | OMS / DIRECT / P38 | Цена или коэффициент недостающей части | Действие |
|---|---|---|---|
| FUEL: Топливо: модельное сжигание | F / F / F | UNKNOWN; +1₽/t×burn tonnes; заменить landed/burn | REPLACE |
| UPLIFT: Хранение/терминал/заправка | U / U / U | UNKNOWN; +1₽/t×burn, received/uplift объём отдельно | CONDITIONAL |
| CREDIT: Демпфер и обратный акциз в формуле | F / F / A | Owner32930/3024 уже вычтен; P38MAIN0, eligible UNKNOWN | DO_NOT_ADD |
| CREDIT_CASH: Право/объём/срок возмещения топлива | P / P / A | UNKNOWN; eligible tonnes×credit и cash dates | CONDITIONAL |
| VAT: Входной НДС и сопоставимость net затрат | P / P / P | UNKNOWN; unrecoverableVAT и recovery lag отдельно | CONDITIONAL |
| GROUND: Аэропорт/ground: общая корзина | U / U / U | 96089/115307×all network flights уже в модели; новая корзина не добавка | CONDITIONAL |
| GROUND_DETAIL: Взлёт/посадка, АБ, терминал, обслуживание pax/bags | U / U / U | OMS911/947 perMTOW и200/pax только reference; billable MTOW/turn/pax UNKNOWN | CONDITIONAL |
| PAX: Переменные расходы на пассажира | U / U / U | Owner500/650×segments уже учтено; P38MAIN0; новый scope UNKNOWN | CONDITIONAL |
| MRO_PROXY: Почасовая модельная корзина ТО | F / F / F | 35000/55000×actualBH уже учтено | REPLACE |
| MRO_LINE: Линейное ТО и инженерная смена | U / U / U | UNKNOWN; S7USD2023 только historical, +1₽/BH коэффициент | CONDITIONAL |
| MRO_HEAVY: Тяжёлые формы ТО/плановые проверки | U / U / U | UNKNOWN; due list; техрезерв2015 отдельно с overlap gate | CONDITIONAL |
| ENGINE: Двигатель/SaM146, LLP, shop visits | U / U / U | UNKNOWN; PBH/LLP/SaM146; PD8 не рассчитан | CONDITIONAL |
| SPARES_USE: ЗИП: потребление, ремонт, обменный фонд | U / U / U | UNKNOWN; +1₽/BH; pool/consumption отдельно | CONDITIONAL |
| SPARES_STOCK: Первоначальный запас деталей/депозит пула | A / A / A | UNKNOWN; SKU×quote; stock/deposit не расход года | CONDITIONAL_ADD |
| NAV: Аэронавигация: proxy | F / F / F | 6000/8000×BH уже учтено | REPLACE |
| DEICE: Противообледенительная обработка | F / F / F | 15000/40000×flight allowance уже учтено | REPLACE |
| CREW_PROXY: Почасовой crew proxy / исключённый fixed crew | F / F / A | Owner15000/22000×BH учтено; P38 исключено ровно1раз | DO_NOT_ADD |
| CREW_FIXED: Постоянный штат и зарплата | P / P / A | UNKNOWN; FTE coverage/effective hours и loaded payroll | CONDITIONAL |
| CREW_TRAIN: Найм, допуски, обучение, ввод | P / P / A | UNKNOWN; entry×course и refresher отдельно | CONDITIONAL |
| CREW_POSITION: Ротации, билеты/трансфер экипажей | P / P / A | UNKNOWN; roster/trips;3430/begun bus-hour coefficient | CONDITIONAL |
| LEASE_WORK: Аренда рабочего парка | A / A / A | Текущая UNKNOWN; исторический rent stress working×12 | CONDITIONAL_ADD |
| LEASE_RES: Аренда/готовность отдельного резерва | A / A / A | Текущая UNKNOWN;1R1 уже есть; stress12мес | CONDITIONAL_ADD |
| CAPITAL: Покупка ВС, финансирование/возвратный депозит | A / A / A | UNKNOWN; ownbuy/lease альтернативы, finance/deposit отдельно | CONDITIONAL_ADD |
| FERRY: Платные перегоны/позиционирование самолёта | A / A / P | OwnerUNKNOWN; P38 dated ferry0; +BH/flight scope | CONDITIONAL_ADD |
| PARKING: Стоянка/ночёвки самолёта | U / U / U | OMSmonthly/hour/day альтернативны, billing UNKNOWN | CONDITIONAL |
| CREW_HOTEL: Гостиницы, отдых и суточные | P / P / A | На1room-night4100single/4650double; roster UNKNOWN | CONDITIONAL |
| INSURANCE: Страхование ВС/ответственности | A / A / A | PremiumUNKNOWN; signed period/tail/endorsement | CONDITIONAL_ADD |
| OVERHEAD: База, офис, административные/IT расходы | A / A / A | На10м²39600/120000; пост×OMSdep; полный overhead UNKNOWN | CONDITIONAL_ADD |
| DISTRIBUTION: Продажи/GDS/эквайринг/комиссии | U / U / P | UNKNOWN; net bridge уже есть; blanket commission не добавлять | DO_NOT_ADD |
| TICKET_VAT: НДС билетной выручки | U / U / P | UNKNOWN; повторно net yield не делить | DO_NOT_ADD |
| REFUNDS: Возвраты/компенсации пассажирам | A / A / A | UNKNOWN; affected tickets×residual liability, без двойного lost revenue | CONDITIONAL_ADD |
| DISRUPT: Сбои, защита стыковок, recovery | P / P / P | 1п.п.transfer×night hotel; bus/food отдельно; incidence UNKNOWN | CONDITIONAL |
| OMS_SETUP: Запуск OMS/станции: помещения, оборудование, договоры | A / A / A | На1pass696.72/209.02, escort4050; BoQ/capexUNKNOWN | CONDITIONAL_ADD |
| TRANSFER: Сервис стыковок и трансферного багажа | P / P / A | 4450×extra ordered services; на1extra/OMSdep выше | CONDITIONAL |
| CANCEL_OLD: Отмена старых обязательств: штрафы/неизбежные платежи | A / A / A | UNKNOWN; signed action penalties/avoidable costs | CONDITIONAL_ADD |
| DONOR: Упущенный вклад донорского самолёта | P / P / P | UNKNOWN; uncovered external contributionD, noncash | CONDITIONAL |
| MIGRATION: Переток собственных пассажиров/внутренний старый продукт | P / P / P | Уже учтённый forgone/joint old delta; остатокUNKNOWN | DO_NOT_ADD |
| GRANT: Маршрутная поддержка/возмещения не топливо | P / P / P | Owner modelgrant один раз; P38MAIN0; entitlementUNKNOWN | CONDITIONAL |
| DEPOSITS: Запуск: рабочий капитал/возвратные депозиты | A / A / A | UNKNOWN; dated advances/deposits/WC; не annual expense | CONDITIONAL_ADD |

## Передача

Готово, ожиданий входов нет. Для допуска сумм RW нужны прежде всего: tail rent/insurance schedules2027 и existing-vs-new obligations; itemization ground/MRO/pax; paid crew roster; station BoQ/ownership; hotel/disruption quantities; договорный cash calendar и внешний donorD. Запросы по каждой статье уже в CSV.

Источники с относительными путями и правилами допуска: [ASSUMPTIONS.md](ASSUMPTIONS.md); базовый [coverage117](../model_audit/coverage.csv), [exposures476](../model_audit/exposures.csv), [owner current replay](../model_audit/owner_network_totals.csv), [P38 replay](../model_audit/p38_network_totals.csv), [OMS34](../omsk_price_recovery/prices.csv), [fleet recovery5](../fleet_price_recovery/prices.csv), [координатор](../coordinator/source_admission.md). P30/P38 переиспользованы через completed audit; новый поиск/оптимизация не выполнялись.

Офлайн Python3, из любого cwd (абсолютные пути):

```bash
python3 -B /home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/39_cost_completion_20261113/calculation/build_cost_table.py
python3 -B /home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/39_cost_completion_20261113/calculation/verify.py
```

Сборка и verify исполнены дважды; хеши выходов совпали. [validation.json](validation.json) фиксирует units/tax/annual formulas/UNKNOWN/exclusivity/source refs/coverage и неизменность исходных tracked bytes+индекса без вызова Git. Запись только calculation; панель/старые inputs не изменены.
