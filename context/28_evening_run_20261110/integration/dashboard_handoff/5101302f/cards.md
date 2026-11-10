# Карточки десяти гипотез

As of 2026-11-10T20:50:14+03:00. Это условные расчётные опыты; решение команды о сети и запуске не принято. Числа ниже сохраняют исходные периоды и не образуют общего рейтинга. 25 резервных гипотез не отклонены экономически.

## C01 — Уфа: согласование северного и южного плеча

Оценена условно: сдвиг и полный бюджет — разные сравнения.

**Механизм.** Те же четыре гипотетических плеча согласуются для одной поездки NJC–UFA–MRV. Один сквозной тариф, два занятых кресла; местные продажи могут вытесняться.

**Было / KEEP.** Несогласованные NJC–UFA–MRV–UFA–NJC; это модельный KEEP тех же рейсов, а не доказанная действующая программа RW.

**Изменение.** Стыковка 60 минут в обе стороны вместо −60/195 минут. Дельта синхронизации и бюджет всей новой программы показаны отдельно.

**Кто едет.** Конечная поездка NJC–MRV и местные пассажиры NJC–UFA/UFA–MRV; действующий прямой конкурентный продукт не исключён.

**Пары, частоты и период.** NJC–UFA и UFA–MRV по 2 RT в диагностические 7–13.12.2026, полёты 7/11 декабря. Это прокси будущей программы, не прогноз декабря и не опубликованные рейсы 2027–2028.

**Тип и рабочий ресурс.** SSJ100/RRJ95, аналог 100 кресел; два стартовых положения NJC/UFA, 19,667 block-hours суммарно. Это не два найденных свободных борта; SJ100/ПД-8 требует своих параметров.

**Откуда самолёт и прежнее задание.** Нужен подтверждённый ресурс в обоих стартовых пунктах. У существующих бортов прежнее задание и потерянный вклад UNKNOWN; у новых — альтернативное применение. Название sync не делает программу безресурсной.

**Конкуренты и альтернативы.** UT152 NJC→UFA 12.12 прибывает 03:00, A46122 UFA→MRV отправляется 15:50: 12ч50 ожидания. Это Utair/Азимут. Альтернатива NJC→SVX→MRV 10.12: 220 минут ожидания, 545 минут поездки; билет/остатки/защита UNKNOWN.

**Результат и его граница.** При timing-loss=0 дельта +1,696/+0,897 млн ₽ за диагностические 7 дней; вся синхронизированная программа +0,299/−5,877 млн ₽ до K. Base 151,27 сквозной поездки, 528,73 всех поездок и 680 сегментов. Это разные показатели, не company growth.

**Неучтённые расходы и порог.** Для сдвига K_retiming и signed D_other; для новой программы полный K базы/ресурса и донор. Base при потере 5% дополнительные 500 тыс. ₽ требуют 37,74 сквозной поездки. +1,696 млн нельзя использовать как бюджет создания базы.

**Денежные потоки.** NOT_CALCULATED: сроки оплаты, депозиты, запуск, возвраты и cash-K неизвестны. Вклад не равен cash.

**Условие продолжения.** Подтверждены оба стартовых положения, остатки кресел, защищённый билет и MCT≤60; новые расходы/потери укладываются в соответствующий Kmax.

**Отказ и пересмотр.** MCT90 закрывает этот продукт. При новом ресурсе проверять весь бюджет, в осторожной ветви он отрицателен ещё до K.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| delta_contribution_rub_week | base; network=UFA_same_legs_sync, local_loss_fraction_south=0 | 1695505.7500616387 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| contribution_sync_rub_week | base; network=UFA_same_legs_sync, local_loss_fraction_south=0 | 298765.19275470264 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| Kmax_full_base_rub_week | base; network=UFA_same_legs_sync, local_loss_fraction_south=0 | 298765.19275470264 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| new_through_journeys_week | base; network=UFA_same_legs_sync, local_loss_fraction_south=0 | 151.26586959201282 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| segments_week | base; network=UFA_same_legs_sync, local_loss_fraction_south=0 | 680.0 | passenger segments/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| delta_contribution_rub_week | cautious; network=UFA_same_legs_sync, local_loss_fraction_south=0 | 897307.7104317499 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| contribution_sync_rub_week | cautious; network=UFA_same_legs_sync, local_loss_fraction_south=0 | -5877140.375475809 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| Kmax_full_base_rub_week | cautious; network=UFA_same_legs_sync, local_loss_fraction_south=0 | -5877140.375475809 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| new_through_journeys_week | cautious; network=UFA_same_legs_sync, local_loss_fraction_south=0 | 81.44274543822945 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |
| segments_week | cautious; network=UFA_same_legs_sync, local_loss_fraction_south=0 | 470.60813005361405 | passenger segments/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C01_synchronization.csv) |

**Независимая проверка.** Conditional C01/C03/C04/C07/C33 diagnostic arithmetic/calendar and upper bounds; exact subject only. Не приняты: market/free tails/launch/year strategy/fullPnL/cash. [cccc728b40:context/28_evening_run_20261110/network_review/report.md:L27](https://github.com/Mput13/case_championship/blob/cccc728b401d3a1234045220f42496ac48e0d475/context/28_evening_run_20261110/network_review/report.md#L27).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C03 — Самара: расширение опорного аэропорта

Оценена условно; исходный local-only рецепт отрицателен.

**Механизм.** Сравнить дополнительные прямые рейсы из уже используемой Самары с недельным выездом того же борта из SVX; выделить экономию доставки.

**Было / KEEP.** Будущий KEEP сохраняет прежние рейсы RW, включая международные и KUF–SVX. Их ресурс не присвоен программе.

**Изменение.** Диагностический KUF4: ARH/OMS/NJC/MRV по 2 RT; отдельный вариант выезда SVX–KUF–SVX с двумя ferry.

**Кто едет.** Местные конечные поездки по четырём парам; KUF4 — диагностическая ступень, не авторские 12 лучей.

**Пары, частоты и период.** KUF–ARH/OMS/NJC/MRV по 2 RT в диагностическую неделю 7–13.12.2026; выезд с 6 декабря. Будущее исполнение 2027–2028 не подтверждено.

**Тип и рабочий ресурс.** Один модельный рабочий SSJ100/RRJ95 100 кресел, 42,486 block-hours/неделю. Резерв общий и не выделен повторно каждой альтернативе.

**Откуда самолёт и прежнее задание.** Свободный борт/экипаж/дополнительная мощность KUF UNKNOWN. При отсутствии нового борта нужен донор с прежним заданием; выезд включает ferry, размещение и альтернативную работу отдельно.

**Конкуренты и альтернативы.** Азимут KUF–NJC 9/12.12 и KUF–MRV по вт/ср/сб опубликованы. KUF–ARH/OMS не покрыты полной датированной выборкой; путь через SVX — отдельная альтернатива C33, не отсутствие конкурента.

**Результат и его граница.** Местный вклад KUF4 −4,847/−16,435 млн ₽ за диагностические 7 дней до K; отрицательный результат сохранён. Выезд добавляет расходы ferry 1,136/1,664 млн ₽.

**Неучтённые расходы и порог.** Добавочная стоимость KUF-базы минус размещение выездного борта должна быть ≤1,136/1,664 млн ₽ за неделю для экономии против доставки. Это не закрывает отрицательный вклад программы. База, резерв, запуск, ресурс и прежние задания отдельно.

**Денежные потоки.** NOT_CALCULATED: договорные сроки, депозиты и запуск неизвестны; поддержка не признана.

**Условие продолжения.** Подтверждены ресурс и будущие продажи/тариф, устранён отрицательный вклад; разница бюджета базы и выезда ниже порога.

**Отказ и пересмотр.** При исходных OD/ценах и без поддержки/нового продукта K≥0 усиливает убыток. Не объявлять KUF победителем по одному local-only сравнению с OMS4.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| contribution_rub_week | base; network=KUF4 | -4847183.6991582755 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| block_hours_week | base; network=KUF4 | 42.48577805390893 | block-hours/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| local_journeys_week | base; network=KUF4 | 800.4215967934703 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ticket_revenue_rub_week | base; network=KUF4 | 9024622.220615515 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| contribution_rub_week | cautious; network=KUF4 | -16434886.976119602 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| block_hours_week | cautious; network=KUF4 | 42.48577805390893 | block-hours/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| local_journeys_week | cautious; network=KUF4 | 443.75010841544224 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ticket_revenue_rub_week | cautious; network=KUF4 | 3649120.4285219256 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ideal_bank_contribution_rub_week | base; network=KUF4 | -4847183.6991582755 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv) |
| ideal_bank_contribution_rub_week | cautious; network=KUF4 | -16434886.9761196 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv) |
| Kmax_extra_KUF_base_minus_deployment_lodging_rub_week | base; network=KUF4 | 1136182.3759248164 | RUB/diagnostic 7 days | 2026-12-06/2026-12-13 deployment comparator | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C03_base_comparison.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C03_base_comparison.csv) |
| Kmax_extra_KUF_base_minus_deployment_lodging_rub_week | cautious; network=KUF4 | 1663976.3302454636 | RUB/diagnostic 7 days | 2026-12-06/2026-12-13 deployment comparator | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C03_base_comparison.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C03_base_comparison.csv) |

**Независимая проверка.** Conditional C01/C03/C04/C07/C33 diagnostic arithmetic/calendar and upper bounds; exact subject only. Не приняты: market/free tails/launch/year strategy/fullPnL/cash. [cccc728b40:context/28_evening_run_20261110/network_review/report.md:L43](https://github.com/Mput13/case_championship/blob/cccc728b401d3a1234045220f42496ac48e0d475/context/28_evening_run_20261110/network_review/report.md#L43).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C04 — Омск: ступени OMS1, OMS4 и OMS8

Оценена; отрицательный исход конкретных ступеней без поддержки.

**Механизм.** Проверить компактную прямую программу и рост числа лучей; отдельно ограничить возможный эффект идеальной пересадочной банки.

**Было / KEEP.** Будущий KEEP без добавлений; действующие рейсы и продажи не объявлены свободным ресурсом.

**Изменение.** OMS1: KJA; OMS4: KJA/KUF/GOJ/NOZ; OMS8: ещё GSV/UFA/TOF/VOG. Идеальная банка — отдельная верхняя граница без принятого расписания.

**Кто едет.** Местные поездки и отдельно допустимые сквозные OD. Это диагностические ступени, не авторская 12-лучевая сеть и не её +388 млн.

**Пары, частоты и период.** Каждая пара по 2 RT в диагностические 7–13.12.2026. Не год и не опубликованная будущая сеть.

**Тип и рабочий ресурс.** SSJ100/RRJ95 100 кресел; OMS1/OMS4 по одному рабочему борту, OMS8 два. OMS1 9 block-hours; остальные точные ресурсы в fixed_programs. Резерв и новый SJ100 отдельно.

**Откуда самолёт и прежнее задание.** Новый борт только после фактического ввода/выделения; иначе существующий донор и его потерянная работа UNKNOWN. Нет бесплатного второго борта при OMS8.

**Конкуренты и альтернативы.** Россия FV6845/6846 KJA–OMS по пн/сб, SSJ100 в зимнем PDF. Перечень поддержки называет Аэрофлот как получателя: это другой объект наблюдения. Остальные пары имеют отдельные статусы покрытия.

**Результат и его граница.** Местный вклад OMS1 −2,301/−3,921; OMS4 −6,482/−17,248; OMS8 −12,841/−35,317 млн ₽/диагностические 7 дней. Идеальная банка OMS4 −1,254/−15,694, OMS8 −1,260/−31,153 млн при LF85/80.

**Неучтённые расходы и порог.** Даже идеальная граница LF85/80 отрицательна до базы/ресурса/запуска/альтернативной работы. Полная физическая загрузка100% — иной sensitivity, не этот вывод. Пропущенные OD исключены явным правилом 500км/1,35, а не занулены.

**Денежные потоки.** NOT_CALCULATED; listing2026 и потолки ставок не award и не cash2027.

**Условие продолжения.** Другой подтверждённый yield/спрос/частота или совместимый режим тарифа и поддержки меняют границу; требуется отдельная выполнимая банка.

**Отказ и пересмотр.** В исходном наборе/частотах/LF85/80 без поддержки рецепт отрицателен. Это не отказ от любого хаба или от всей авторской модели.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| contribution_rub_week | base; network=OMS1 | -2301485.957639549 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| block_hours_week | base; network=OMS1 | 9.0 | block-hours/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| local_journeys_week | base; network=OMS1 | 69.12231371761398 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ticket_revenue_rub_week | base; network=OMS1 | 671147.199219258 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| contribution_rub_week | base; network=OMS4 | -6482489.569446083 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-4](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| block_hours_week | base; network=OMS4 | 39.86570219904357 | block-hours/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-4](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| local_journeys_week | base; network=OMS4 | 570.0593896735605 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-4](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ticket_revenue_rub_week | base; network=OMS4 | 6579582.482492518 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-4](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| contribution_rub_week | base; network=OMS8 | -12841455.532602016 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| block_hours_week | base; network=OMS8 | 82.9499859020773 | block-hours/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| local_journeys_week | base; network=OMS8 | 1211.9650618515961 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ticket_revenue_rub_week | base; network=OMS8 | 14171821.621122371 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| contribution_rub_week | cautious; network=OMS1 | -3921159.0693621086 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-7](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| block_hours_week | cautious; network=OMS1 | 9.0 | block-hours/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-7](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| local_journeys_week | cautious; network=OMS1 | 57.911538461538456 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-7](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ticket_revenue_rub_week | cautious; network=OMS1 | 429409.030637891 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-7](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| contribution_rub_week | cautious; network=OMS4 | -17247868.421327986 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-8](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| block_hours_week | cautious; network=OMS4 | 39.86570219904357 | block-hours/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-8](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| local_journeys_week | cautious; network=OMS4 | 193.08332705797486 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-8](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ticket_revenue_rub_week | cautious; network=OMS4 | 1645553.135453844 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-8](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| contribution_rub_week | cautious; network=OMS8 | -35316573.97142186 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-9](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| block_hours_week | cautious; network=OMS8 | 82.9499859020773 | block-hours/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-9](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| local_journeys_week | cautious; network=OMS8 | 447.16887242482267 | one-way OD journeys/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-9](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ticket_revenue_rub_week | cautious; network=OMS8 | 3772320.346133198 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv:CSV-record-9](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/fixed_programs.csv) |
| ideal_bank_contribution_rub_week | base; network=OMS1 | -2301485.957639549 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv) |
| ideal_bank_contribution_rub_week | base; network=OMS4 | -1254350.7739814054 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv:CSV-record-4](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv) |
| ideal_bank_contribution_rub_week | base; network=OMS8 | -1260241.8924380206 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv) |
| ideal_bank_contribution_rub_week | cautious; network=OMS1 | -3921159.0693621086 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv:CSV-record-7](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv) |
| ideal_bank_contribution_rub_week | cautious; network=OMS4 | -15694367.209675321 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv:CSV-record-8](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv) |
| ideal_bank_contribution_rub_week | cautious; network=OMS8 | -31152536.40708345 | RUB/diagnostic 7 days | 2026-12-07/2026-12-13 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv:CSV-record-9](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/bank_upper_bound.csv) |

**Независимая проверка.** Conditional C01/C03/C04/C07/C33 diagnostic arithmetic/calendar and upper bounds; exact subject only. Не приняты: market/free tails/launch/year strategy/fullPnL/cash. [cccc728b40:context/28_evening_run_20261110/network_review/report.md:L43](https://github.com/Mput13/case_championship/blob/cccc728b401d3a1234045220f42496ac48e0d475/context/28_evening_run_20261110/network_review/report.md#L43).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C07 — Екатеринбург—Омск: продление оборота до Красноярска

Оценена; исходное продление отрицательно.

**Механизм.** Добавить OMS–KJA–OMS внутри оборота SVX–OMS–SVX, совместно продавать местные и сквозные поездки на тех же креслах.

**Было / KEEP.** WZ5071 8/11.12 SVX21:20→OMS00:00+1; WZ5072 9/12.12 OMS00:50→SVX01:35. KEEP205 минут блока/оборот.

**Изменение.** SVX–OMS–KJA–OMS–SVX, 475 минут блока; +9 block-hours за неделю, возврат позже на310/355/400 минут при turn30/45/60.

**Кто едет.** Местный OMS–KJA и сквозной SVX–KJA; прежние местные SVX–OMS сохранены модельно.

**Пары, частоты и период.** 2 RT OMS–KJA добавлены на диагностических датах 9/12.12.2026; варианты turn30/45/60 альтернативны.

**Тип и рабочий ресурс.** Существующий SSJ100/RRJ95 100 кресел, тот же условный хвост. Готовность к следующему вылету SVX07:15/08:15/09:15, crew duty и хвост UNKNOWN.

**Откуда самолёт и прежнее задание.** Донор — окно после WZ5072, но его следующее назначение не принято. Возможный WZ5049 SVX–REN07:25 проходит лишь turn30 с запасом10мин; turn45/60 опаздывают50/110мин. Потеря следующего задания не включена в числа.

**Конкуренты и альтернативы.** Россия SVX–KJA: 7 направленных отправлений в закреплённой неделе; OMS–KJA FV6845/6846. Наличие частот не равно остаткам мест/доказанному захвату.

**Результат и его граница.** Дельта к KEEP −1,754/−3,755 млн ₽ за диагностические7дней до K/потери следующего задания. Base69,12 новых местных и46,29 сквозных поездки. Для нуля нужно129,79 местной поездки на сторону/неделю против всего рынка82,73.

**Неучтённые расходы и порог.** 100% только местного рынка дают base−0,867млн. Предельный захват обоих endpoint-рынков +1,006/−2,057млн: это верхняя диагностическая граница, не прогноз. K_extension, L_next_assignment и signed D_other отдельно.

**Денежные потоки.** NOT_CALCULATED; без гипотетической поддержки.

**Условие продолжения.** Новая цена/рынок/расписание закрывают дефицит и подтверждено следующее задание, экипажи и кресла.

**Отказ и пересмотр.** Cautious не проходит даже предельный захват обоих рынков при исходных параметрах. Не складывать с C33: общие WZ5071/5072.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| delta_contribution_rub_week | base; network=SVX_OMS_KJA_OMS_SVX, turn_minutes=45 | -1754011.114649373 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv) |
| extra_block_hours_week | base; network=SVX_OMS_KJA_OMS_SVX, turn_minutes=45 | 9.0 | block-hours/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv) |
| new_local_OMS_KJA_week | base; network=SVX_OMS_KJA_OMS_SVX, turn_minutes=45 | 69.12231371761398 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv) |
| new_through_SVX_KJA_week | base; network=SVX_OMS_KJA_OMS_SVX, turn_minutes=45 | 46.28707147658526 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv) |
| delta_contribution_rub_week | cautious; network=SVX_OMS_KJA_OMS_SVX, turn_minutes=45 | -3755185.580875518 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv) |
| extra_block_hours_week | cautious; network=SVX_OMS_KJA_OMS_SVX, turn_minutes=45 | 9.0 | block-hours/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv) |
| new_local_OMS_KJA_week | cautious; network=SVX_OMS_KJA_OMS_SVX, turn_minutes=45 | 57.911538461538456 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv) |
| new_through_SVX_KJA_week | cautious; network=SVX_OMS_KJA_OMS_SVX, turn_minutes=45 | 20.922128145288987 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv:CSV-record-6](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C07_extension.csv) |

**Независимая проверка.** Conditional C01/C03/C04/C07/C33 diagnostic arithmetic/calendar and upper bounds; exact subject only. Не приняты: market/free tails/launch/year strategy/fullPnL/cash. [cccc728b40:context/28_evening_run_20261110/network_review/report.md:L62](https://github.com/Mput13/case_championship/blob/cccc728b401d3a1234045220f42496ac48e0d475/context/28_evening_run_20261110/network_review/report.md#L62).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C10 — Уфа—Сургут: гарантированный корпоративный блок

Оценена условно: численный договорный порог.

**Механизм.** Заказчик гарантирует оплату 28-дневных смен и пустых встречных плеч; цена договора сравнивается с обычной продажей тех же рейсов.

**Было / KEEP.** Обычная продажа тех же рейсов и отдельный будущий KEEP ресурса; найденный публичный механизм групповой перевозки не означает найденного клиента.

**Изменение.** Закрытый launch включает доставку первой смены и возврат последней; steady28 — другой цикл. Сценарии 1/2/4 группы не складываются.

**Кто едет.** Сотрудники на 28-дневную смену: 80/60 человек в группе base/cautious. Остальной розничный спрос — сценарий.

**Пары, частоты и период.** UFA–SGC. Launch1: 04.01 и 01.02.2027, два RT на 80/60 различных сотрудников. Launch2/4 добавляют смены каждые 28 дней; steady28 — один RT на смену. Точные даты в program_changes.

**Тип и рабочий ресурс.** SSJ100/RRJ95, 100 кресел, один продуктовый слот. Один RT требует 4,737 block-hours; launch1 — два RT. Подтверждения свободного UFA-борта нет.

**Откуда самолёт и прежнее задание.** Январь 2027 раньше любой новой поставки H2: необходим существующий донор и потерянная работа либо перенос контракта. Donor UNKNOWN, не ноль.

**Конкуренты и альтернативы.** Датированное покрытие UFA–SGC и альтернативы даны отдельно в route_context; полный рынок/цена 20 кг/остатки не установлены. Корпоративное предложение требует живого заказчика.

**Результат и его граница.** Launch n1 при K=0: минимум 32083/71565 ₽ за человека туда-обратно; steady — 16542/36433 ₽ с округлением вверх. Это договорные пороги, не рыночная цена и не прибыль.

**Неучтённые расходы и порог.** Порог полного бюджета использует K_block, сравнение с ordinary — только K_block−K_ordinary. Совпадающий ресурс/донор сокращается. Гарантия должна покрывать неиспользованный блок, отмены и обеспечение.

**Денежные потоки.** При полной предоплате break-even-гарантии за 14 дней launch n1 имеет нулевой дневной financing lower bound. Штрафы/обеспечение/возвраты/cash-K UNKNOWN; дневное netting не внутридневная ликвидность.

**Условие продолжения.** Заказчик гарантирует полный launch-цикл и оплату, найден ресурс и оба K, цена не ниже соответствующего порога.

**Отказ и пересмотр.** Нельзя заменить launch steady-ценой; при неподтверждённом доноре январь не разрешён сценариями новых поставок.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| minimum_guarantee_return_per_person | base; phase=steady28, cohorts=1, K_probe=0 | 16541.296477333333 | RUB/person round-trip | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| minimum_guarantee_to_beat_ordinary_return_per_person | base; phase=steady28, cohorts=1, K_probe=0 | 11900.930633301172 | RUB/person round-trip | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| roundtrips | base; phase=steady28, cohorts=1, K_probe=0 | 1.0 | round trips/programme | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| minimum_guarantee_return_per_person | base; phase=launch_closed, cohorts=1, K_probe=0 | 32082.592954666667 | RUB/person round-trip | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| minimum_guarantee_to_beat_ordinary_return_per_person | base; phase=launch_closed, cohorts=1, K_probe=0 | 21719.826613340632 | RUB/person round-trip | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| roundtrips | base; phase=launch_closed, cohorts=1, K_probe=0 | 2.0 | round trips/programme | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| minimum_guarantee_return_per_person | cautious; phase=steady28, cohorts=1, K_probe=0 | 36432.187616 | RUB/person round-trip | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-20](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| minimum_guarantee_to_beat_ordinary_return_per_person | cautious; phase=steady28, cohorts=1, K_probe=0 | 2582.173605407967 | RUB/person round-trip | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-20](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| roundtrips | cautious; phase=steady28, cohorts=1, K_probe=0 | 1.0 | round trips/programme | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-20](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| minimum_guarantee_return_per_person | cautious; phase=launch_closed, cohorts=1, K_probe=0 | 71564.375232 | RUB/person round-trip | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-23](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| minimum_guarantee_to_beat_ordinary_return_per_person | cautious; phase=launch_closed, cohorts=1, K_probe=0 | 3592.815719196174 | RUB/person round-trip | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-23](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |
| roundtrips | cautious; phase=launch_closed, cohorts=1, K_probe=0 | 2.0 | round trips/programme | launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle | [388908b6da:context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv:CSV-record-23](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C10_contract_thresholds.csv) |

**Независимая проверка.** Conditional money/calendar/treasury fixtures/readiness truncation/own KEEP/support constraints. Не приняты: market/actual resource/contracts/award/full company budget/cash. [6cc8c37e23:context/28_evening_run_20261110/products_review/report.md:L24](https://github.com/Mput13/case_championship/blob/6cc8c37e23c89488f3113efd96952d13f253f274/context/28_evening_run_20261110/products_review/report.md#L24).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C14 — Киров—Минводы: 14-ночный санаторный пакет

Оценена условно: полный цикл и цена договора.

**Механизм.** Шесть групп с 14 ночами образуют 8 рабочих понедельников; авиационная гарантия и полный пакет включают разные расходы и участников cash.

**Было / KEEP.** KEEP без нового пакета и без бесплатного базирования KVX; обычные рейсы/другой блок — отдельные альтернативы.

**Изменение.** SVX–KVX–MRV–KVX–SVX на восьми датах: 16 коммерческих и 16 ferry-плеч. Возврат каждой группы через 14 ночей.

**Кто едет.** 360/240 различных клиентов за шесть групп по 60/40 человек; каждый использует два коммерческих кресла. Максимум 120/80 коек и 5040/3360 bed-days.

**Пары, частоты и период.** Заезды 01.11–06.12.2027, последние возвраты 20.12.2027. KVX–MRV — восемь RT, плюс восемь ferry RT SVX–KVX; это полный цикл, не частота ×52.

**Тип и рабочий ресурс.** Один условный SSJ100/RRJ95 на 100 кресел и восемь рабочих дат, 74,750 block-hours. День длиннее 13 часов при 9,34 block-hours не допускает crew duty автоматически.

**Откуда самолёт и прежнее задание.** Доставка из SVX включена; прежняя работа/свободный ресурс UNKNOWN. KVX-база занимает 50 дней, 42 выходных требуют стоянки/альтернативы. База не бесплатна.

**Конкуренты и альтернативы.** Азимут KVX–MRV в перечне 2026 — не подтверждённый зимний билет 2027/контракт и не award RW. Цена блока другого перевозчика сравнима лишь при одинаковом пакете.

**Результат и его граница.** K=0: авиагарантия 57688/143659₽ на клиента туда-обратно; весь пакет 169128/267863₽ с округлением вверх. Прайс отеля 7760 ₽/сутки 2026 — ориентир, cautious+10% допущение.

**Неучтённые расходы и порог.** Избегаемые ferry 8,740/12,795 млн ₽ — предел добавочной базы, размещения, потерь прежней работы и выхода против доставки. Отель/питание не начислены дважды, гарантия не fullPnL.

**Денежные потоки.** Airline и tour_operator разделены. У TO financing lower bound 9,778/7,170 млн ₽ при выбранных авансах; нулевой дневной airline financing не исключает 498260 ₽ intraday base. Cash-параметры — условия переговоров.

**Условие продолжения.** Договорены 14 оплачиваемых дней, квота 120/80 коек, гарантия, предоплата, ресурс и crew duty. При готовности 30.11 остаётся одна группа/два RT с доставкой и base-авиагарантией 86032 ₽ до K.

**Отказ и пересмотр.** Нельзя убрать 16 ferry без бюджета базы/доставки. При ресурсе только в 2028 или без нового ресурса исходная программа 2027 не запускается; обязательства отмены не нулевые.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| minimum_air_guarantee_return_per_person | base; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 57687.37459674075 | RUB/person round-trip | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| minimum_package_price_per_person | base; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 169127.37459674076 | RUB/person full 14-night package | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| distinct_return_customers | base; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 360 | distinct return customers/programme | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| peak_beds | base; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 120 | simultaneous beds | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| block_hours | base; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 74.74986666666666 | block-hours/programme | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| minimum_air_guarantee_return_per_person | cautious; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 143658.78376533333 | RUB/person round-trip | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| minimum_package_price_per_person | cautious; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 267862.78376533336 | RUB/person full 14-night package | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| distinct_return_customers | cautious; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 240 | distinct return customers/programme | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| peak_beds | cautious; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 80 | simultaneous beds | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |
| block_hours | cautious; program=SVX_KVX_MRV_full_chain, cohorts=6, K_probe=0 | 74.74986666666666 | block-hours/programme | departures2027-11-01/2027-12-06; returns through2027-12-20 | [388908b6da:context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C14_full_package_thresholds.csv) |

**Независимая проверка.** Conditional money/calendar/treasury fixtures/readiness truncation/own KEEP/support constraints. Не приняты: market/actual resource/contracts/award/full company budget/cash. [6cc8c37e23:context/28_evening_run_20261110/products_review/report.md:L34](https://github.com/Mput13/case_championship/blob/6cc8c37e23c89488f3113efd96952d13f253f274/context/28_evening_run_20261110/products_review/report.md#L34).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C17 — Пермь: зимний Мурманск и летний Горно-Алтайск

Оценена; исходный несубсидируемый рецепт отклонён по физическому порогу.

**Механизм.** Один сезонный слот меняет направление зимой и летом; месячный OD применяется лишь к выполняемым датам.

**Было / KEEP.** KEEP ресурса либо другая зимняя работа. Summer-only и year-round RGK — самостоятельные альтернативы; снятие зимней программы не делает ресурс бесплатным.

**Изменение.** В каждом 2027 и 2028 году 35 зимних RT PEE–MMK и 35 летних RT PEE–RGK с доставкой. Старое число 34 в README исправлено владельцем без изменения денег.

**Кто едет.** Зимние местные поездки PEE–MMK и летний туризм PEE–RGK. В авторской OD-таблице RGK нет: спрос UNKNOWN, посчитан порог, а не нулевой спрос.

**Пары, частоты и период.** Два RT в неделю внутри заданных сезонов; в каждом году 70 RT и 6 доставочных плеч в точном календаре 2027/2028. Это сезонный расчёт, без умножения одной недели на 52.

**Тип и рабочий ресурс.** Один условный SSJ100/RRJ95, 100 кресел; 409,121 block-hours в 2027 при полном цикле. Ввод слота ограничивает реальные даты и соответствующий месячный спрос.

**Откуда самолёт и прежнее задание.** Свободный существующий борт и зимний донор UNKNOWN. Новый слот доступен лишь после ввода; company N(t), ТО и резерв задаются отдельно. Альтернативная работа зимой не занулена.

**Конкуренты и альтернативы.** ЮВТ уже предлагает RGK не только летом. Датированные строки и неизвестные цены/остатки сохранены в route_context; летняя уникальность не заявлена.

**Результат и его граница.** Зима 2027: 719,65/194,20 платящих сегмента и вклад −55,358/−92,384 млн ₽. Для покрытия всего выбранного 2027 нужно 163,94/290,62 платящего на каждое летнее плечо при 100 креслах и K=0. Исходный несубсидируемый рецепт не проходит.

**Неучтённые расходы и порог.** База, ресурс, резерв, запуск, донор и выход остаются в K. Поддержка одновременно ограничивает тариф и eligible flights. Условный support probe p100/2027 даёт base +7,234 млн до K и cautious −66,422 млн ₽; это не award и не принятый запуск.

**Денежные потоки.** Датированный operating cash посчитан без авансовой поддержки. Выплата после выполнения не финансирует вылет заранее; реальный company cash UNKNOWN.

**Условие продолжения.** Подтверждены иной зимний контракт, yield, ресурс либо применимая поддержка с тарифом, ставкой, сезоном, award и оплатой; летом подтверждён спрос.

**Отказ и пересмотр.** Отклоняется исходное сочетание OD, тарифов, затрат и сезонов без поддержки. Это не отказ от всех сезонных идей. Весь annual OD нельзя переносить в оставшиеся недели.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| minimum_summer_paid_people_each_leg | base; year=2027, K_probe=0, summer_people_each_leg_probe=40 | 163.9406638094946 | paying passengers/summer one-way flight | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_paid_segments | base; year=2027, K_probe=0, summer_people_each_leg_probe=40 | 719.6541927928316 | passenger segments/year winter dates | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_variable_contribution | base; year=2027, K_probe=0, summer_people_each_leg_probe=40 | -55357802.029111974 | RUB/year winter dates | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_roundtrips | base; year=2027, K_probe=0, summer_people_each_leg_probe=40 | 35 | round trips/year winter | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| summer_roundtrips | base; year=2027, K_probe=0, summer_people_each_leg_probe=40 | 35 | round trips/year summer | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| minimum_summer_paid_people_each_leg | cautious; year=2027, K_probe=0, summer_people_each_leg_probe=40 | 290.6178420705488 | paying passengers/summer one-way flight | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-14](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_paid_segments | cautious; year=2027, K_probe=0, summer_people_each_leg_probe=40 | 194.20423345824105 | passenger segments/year winter dates | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-14](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_variable_contribution | cautious; year=2027, K_probe=0, summer_people_each_leg_probe=40 | -92384293.61750945 | RUB/year winter dates | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-14](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_roundtrips | cautious; year=2027, K_probe=0, summer_people_each_leg_probe=40 | 35 | round trips/year winter | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-14](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| summer_roundtrips | cautious; year=2027, K_probe=0, summer_people_each_leg_probe=40 | 35 | round trips/year summer | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-14](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| minimum_summer_paid_people_each_leg | base; year=2028, K_probe=0, summer_people_each_leg_probe=40 | 163.8747867150325 | paying passengers/summer one-way flight | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-26](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_paid_segments | base; year=2028, K_probe=0, summer_people_each_leg_probe=40 | 723.662485695495 | passenger segments/year winter dates | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-26](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_variable_contribution | base; year=2028, K_probe=0, summer_people_each_leg_probe=40 | -55309599.100323126 | RUB/year winter dates | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-26](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_roundtrips | base; year=2028, K_probe=0, summer_people_each_leg_probe=40 | 35 | round trips/year winter | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-26](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| summer_roundtrips | base; year=2028, K_probe=0, summer_people_each_leg_probe=40 | 35 | round trips/year summer | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-26](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| minimum_summer_paid_people_each_leg | cautious; year=2028, K_probe=0, summer_people_each_leg_probe=40 | 290.6029032242227 | paying passengers/summer one-way flight | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-38](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_paid_segments | cautious; year=2028, K_probe=0, summer_people_each_leg_probe=40 | 195.28590220752872 | passenger segments/year winter dates | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-38](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_variable_contribution | cautious; year=2028, K_probe=0, summer_people_each_leg_probe=40 | -92374664.94843729 | RUB/year winter dates | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-38](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| winter_roundtrips | cautious; year=2028, K_probe=0, summer_people_each_leg_probe=40 | 35 | round trips/year winter | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-38](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |
| summer_roundtrips | cautious; year=2028, K_probe=0, summer_people_each_leg_probe=40 | 35 | round trips/year summer | row year2027 or2028; fixed source seasonal calendar | [388908b6da:context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv:CSV-record-38](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C17_seasonal_thresholds.csv) |

**Независимая проверка.** Conditional money/calendar/treasury fixtures/readiness truncation/own KEEP/support constraints. Не приняты: market/actual resource/contracts/award/full company budget/cash. [6cc8c37e23:context/28_evening_run_20261110/products_review/report.md:L44](https://github.com/Mput13/case_championship/blob/6cc8c37e23c89488f3113efd96952d13f253f274/context/28_evening_run_20261110/products_review/report.md#L44).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C31 — Замена SSJ на Ту с двумя прежними заданиями

Оценена условно; ресурсная приёмка HOLD.

**Механизм.** Ту выполняет прежний SSJ-оборот SVX–MRV, освобождая SSJ для OMS. Потеря старой работы Ту ZIA–TLV учитывается отдельно; сохраняемый MRV-доход сокращается в разности.

**Было / KEEP.** Четыре KEEP-плеча SSJ SVX–MRV и четыре снимаемых KEEP-плеча Ту ZIA–TLV. Старые пассажиры f2 не продаются повторно как новые.

**Изменение.** Новые OMS-обороты 05/08.07.2027, понедельник/четверг; замена MRV на Ту и два Tu-ferry. Это другие даты, чем C35 feed во вторник/пятницу.

**Кто едет.** Дополнительные местные OMS-поездки от f4−f2. Новые MRV-продажи — явная ось 0/30/60, а не автоматический эффект ёмкости. Иной чистый transfer-вклад H требует общего allocator.

**Пары, частоты и период.** Контрольная неделя 05–11.07.2027: два RT SVX–OMS, два RT SVX–MRV заменяются, два RT ZIA–TLV снимаются; два Tu-ferry. Точные даты и роли — в program_changes.

**Тип и рабочий ресурс.** Два существующих типа: SSJ100 на 100 мест и опубликованный Tu-214 на 194 места. Один TLV RT освобождает 11,5 часа против первых 19,2 часа новой работы; два дают 23 часа. Block-only баланс не даёт tail/crew/ТО допуск.

**Откуда самолёт и прежнее задание.** Оба прежних задания названы: SSJ–MRV и Tu–TLV. Конкретный Ту, воскресное окно доставки, all-in cost и потеря TLV UNKNOWN. L=0 — probe, а не установленное отсутствие потерь.

**Конкуренты и альтернативы.** OMS-рынок и контекст MRV/TLV разделены. Новый местный OMS-прирост 5,8235/2,7786 сегмента в неделю получен из annual OD×(capture(f4)−capture(f2))×7/365; это не весь трансферный рынок.

**Результат и его граница.** При нуле новых MRV-продаж предел Tu_new_allin + lost_TLV + K равен 2,117/3,045 млн ₽ за неделю. При lost_TLV=3 млн base-предел собственно Tu+K становится −0,883 млн ₽. Это граница, а не прибыль Ту.

**Неучтённые расходы и порог.** Нераскрытые прежние сквозные продажи, слоты и иные донорские эффекты входят в signed K без повторного вычета TLV. Подтверждённый чистый H может повысить предел; чужая сквозная выручка отдельно не прибавляется.

**Денежные потоки.** Incremental KEEP probe при L=0 и счёте Ту ровно на потолке требует bridge 2,117/3,045 млн ₽. Возвраты TLV, обязательства и реальные сроки UNKNOWN; это не Treasury budget компании.

**Условие продолжения.** Подтверждены конкретные Ту/SSJ, экипажи, ТО и ferry-окно; Tu+lost_TLV+K ниже границы. Дополнительный H допускается лишь после общего allocator.

**Отказ и пересмотр.** SSJ и Ту не считаются свободными; расходы SSJ не становятся фактами о Ту. C31/C35 самостоятельно не складываются; feed C35 отсутствует на датах новых рейсов.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| maximum_tu_new_allin_cost_plus_K | base; demand_layer=nastya_primary, additional_mrv_paid_each_leg_probe=0, foregone_tu_old_mission_contribution_probe=0 | 2117413.6760571776 | RUB/one week; Tu all-in + lost TLV + K ceiling at L0 representation | 2027-07-05/2027-07-11 | [388908b6da:context/28_evening_run_20261110/products/outputs/C31_replacement_frontier.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C31_replacement_frontier.csv) |
| additional_oms_paid_segments | base; demand_layer=nastya_primary, additional_mrv_paid_each_leg_probe=0, foregone_tu_old_mission_contribution_probe=0 | 5.823543308578489 | new passenger segments/one week | 2027-07-05/2027-07-11 | [388908b6da:context/28_evening_run_20261110/products/outputs/C31_replacement_frontier.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C31_replacement_frontier.csv) |
| maximum_tu_new_allin_cost_plus_K | cautious; demand_layer=nastya_primary, additional_mrv_paid_each_leg_probe=0, foregone_tu_old_mission_contribution_probe=0 | 3045419.376058144 | RUB/one week; Tu all-in + lost TLV + K ceiling at L0 representation | 2027-07-05/2027-07-11 | [388908b6da:context/28_evening_run_20261110/products/outputs/C31_replacement_frontier.csv:CSV-record-74](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C31_replacement_frontier.csv) |
| additional_oms_paid_segments | cautious; demand_layer=nastya_primary, additional_mrv_paid_each_leg_probe=0, foregone_tu_old_mission_contribution_probe=0 | 2.7785799603538424 | new passenger segments/one week | 2027-07-05/2027-07-11 | [388908b6da:context/28_evening_run_20261110/products/outputs/C31_replacement_frontier.csv:CSV-record-74](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C31_replacement_frontier.csv) |

**Независимая проверка.** Conditional money/calendar/treasury fixtures/readiness truncation/own KEEP/support constraints. Не приняты: market/actual resource/contracts/award/full company budget/cash. [6cc8c37e23:context/28_evening_run_20261110/products_review/report.md:L52](https://github.com/Mput13/case_championship/blob/6cc8c37e23c89488f3113efd96952d13f253f274/context/28_evening_run_20261110/products_review/report.md#L52).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C33 — Самара—Екатеринбург—Омск: сдвиг тех же рейсов

Оценена условно: знак зависит от реальных остатков и следующей работы.

**Механизм.** Сохранить номера, даты и число WZ1034/5071/5072/1033; изменить часы OMS ради короткой пересадки и вычесть потерянные местные и иные продажи.

**Было / KEEP.** 8/11 декабря WZ1034 KUF08:00→SVX10:45 и WZ5071; 9/12 декабря WZ5072 и WZ1033 SVX22:45→KUF23:30. Ожидания 635/1270 минут.

**Изменение.** WZ5071 отправляется SVX12:00, WZ5072 — OMS20:55; ожидания 75/65 минут. Стоянка OMS растёт с 50 до 1815 минут; 415 минут блока на ротацию сохраняются.

**Кто едет.** KUF–OMS — одна конечная поездка, два кресла и один тариф. Местные и прочие прежние продажи разделены через occupied states.

**Пары, частоты и период.** Восемь точных опубликованных KEEP-рейсов 8/9/11/12.12.2026. Retime — предложение на тех же датах; автоматического переноса на 2027/2028 нет.

**Тип и рабочий ресурс.** SSJ100/RRJ95, 100 кресел, тот же модельный хвост и ноль дополнительных block-hours. Готовность в SVX меняется с 02:20 на 22:25; занятость внутри периода не даёт бесплатного сдвига.

**Откуда самолёт и прежнее задание.** Возможный WZ5049 SVX–REN07:25 теряется при таком назначении. Tail assignment UNKNOWN; потерянный net-вклад L_changed_slots и ночёвка отдельно. Следующий KUF08:00 не доказывает отдых экипажа.

**Конкуренты и альтернативы.** Для KUF–SVX сохранены 12 конфликтов публикаций 10:40/10:45; выбрано позднее 10:45. Новая стыковка 75–80 минут проходит MCT60, но не MCT90. Полный рынок и остатки неизвестны.

**Результат и его граница.** При 15% потери местных: local-only +1,458/+0,219 млн ₽ за неделю; при исходно проданных 85/80% и разрешении до 100% физической ёмкости +0,556/+0,219 млн ₽; при всех 100 занятых креслах −0,0097/−0,0055 млн ₽. Это отдельные состояния остатков.

**Неучтённые расходы и порог.** K_overnight_retiming + L_changed_slots должны быть не больше выбранного Kmax. При 100% занятых и нулевой потере оптимальная дельта нулевая. Прочие прежние пассажиры не считаются свободными; extra_aircraft=0 в CSV относится к локальному block-only сравнению.

**Денежные потоки.** NOT_CALCULATED: outstation, слоты, экипажи, claims и IT-платежи не занулены.

**Условие продолжения.** Есть остатки по конкретным рейсам, слоты, защита, MCT и tail assignment; все расходы/потери помещаются в Kmax выбранного состояния.

**Отказ и пересмотр.** C07 делит WZ5071/5072, а C33/KUF4/OMS4/OMS8 — рынок KUF–OMS. Независимое сложение дельт и предположение о свободном полном борте недопустимы.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| delta_contribution_rub_week | base; network=KUF_SVX_OMS_same_flights, occupied_state=local_only, local_loss_fraction_trunk=0.15 | 1458193.5834190338 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-4](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| new_through_journeys_week | base; network=KUF_SVX_OMS_same_flights, occupied_state=local_only, local_loss_fraction_trunk=0.15 | 156.61699333876533 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-4](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| delta_contribution_rub_week | base; network=KUF_SVX_OMS_same_flights, occupied_state=planning_lf_already_sold, local_loss_fraction_trunk=0.15 | -9687.602301231294 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-7](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| new_through_journeys_week | base; network=KUF_SVX_OMS_same_flights, occupied_state=planning_lf_already_sold, local_loss_fraction_trunk=0.15 | 2.6544734866580217 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-7](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| delta_contribution_rub_week | base; network=KUF_SVX_OMS_same_flights, occupied_state=planning_lf_sold_allow100, local_loss_fraction_trunk=0.15 | 555719.0707868015 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-10](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| new_through_journeys_week | base; network=KUF_SVX_OMS_same_flights, occupied_state=planning_lf_sold_allow100, local_loss_fraction_trunk=0.15 | 62.65447348665805 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-10](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| delta_contribution_rub_week | base; network=KUF_SVX_OMS_same_flights, occupied_state=all_physical_seats_sold, local_loss_fraction_trunk=0.15 | -9687.602301231294 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-13](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| new_through_journeys_week | base; network=KUF_SVX_OMS_same_flights, occupied_state=all_physical_seats_sold, local_loss_fraction_trunk=0.15 | 2.6544734866580217 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-13](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| delta_contribution_rub_week | cautious; network=KUF_SVX_OMS_same_flights, occupied_state=local_only, local_loss_fraction_trunk=0.15 | 219364.53094170074 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-16](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| new_through_journeys_week | cautious; network=KUF_SVX_OMS_same_flights, occupied_state=local_only, local_loss_fraction_trunk=0.15 | 36.62565489220253 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-16](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| delta_contribution_rub_week | cautious; network=KUF_SVX_OMS_same_flights, occupied_state=planning_lf_already_sold, local_loss_fraction_trunk=0.15 | -5459.707466015185 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-19](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| new_through_journeys_week | cautious; network=KUF_SVX_OMS_same_flights, occupied_state=planning_lf_already_sold, local_loss_fraction_trunk=0.15 | 1.6729326923076933 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-19](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| delta_contribution_rub_week | cautious; network=KUF_SVX_OMS_same_flights, occupied_state=planning_lf_sold_allow100, local_loss_fraction_trunk=0.15 | 219364.53094170074 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-22](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| new_through_journeys_week | cautious; network=KUF_SVX_OMS_same_flights, occupied_state=planning_lf_sold_allow100, local_loss_fraction_trunk=0.15 | 36.62565489220253 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-22](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| delta_contribution_rub_week | cautious; network=KUF_SVX_OMS_same_flights, occupied_state=all_physical_seats_sold, local_loss_fraction_trunk=0.15 | -5459.707466015185 | RUB/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-25](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |
| new_through_journeys_week | cautious; network=KUF_SVX_OMS_same_flights, occupied_state=all_physical_seats_sold, local_loss_fraction_trunk=0.15 | 1.6729326923076933 | one-way OD journeys/diagnostic 7 days | 2026-12-08/2026-12-12 diagnostic proxy | [b47118a48b:context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv:CSV-record-25](https://github.com/Mput13/case_championship/blob/b47118a48b6d5480217077bf8699a63665c0eb7a/context/28_evening_run_20261110/network/v2/outputs/C33_retiming.csv) |

**Независимая проверка.** Conditional C01/C03/C04/C07/C33 diagnostic arithmetic/calendar and upper bounds; exact subject only. Не приняты: market/free tails/launch/year strategy/fullPnL/cash. [cccc728b40:context/28_evening_run_20261110/network_review/report.md:L72](https://github.com/Mput13/case_championship/blob/cccc728b401d3a1234045220f42496ac48e0d475/context/28_evening_run_20261110/network_review/report.md#L72).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.

## C35 — Ижевск—Екатеринбург—Омск: внешний блок или собственный KEEP

Оценены две альтернативы условно; компания growth не установлен.

**Механизм.** Одна защищённая поездка IJK–OMS. Внешний блок и интеграция двух собственных KEEP-линий — альтернативные режимы общего спроса и кресел.

**Было / KEEP.** Будущий KEEP, старые продажи и остатки мест должны быть подтверждены. Временный RW на IJK–SVX не является внешним партнёром.

**Изменение.** External: купить 160 seat-segments за 480 тыс. ₽, включая непроданные. Own: оба рейса входят в один KEEP, нет новых рейсов и платежа партнёру; один тариф и два per-pax cost.

**Кто едет.** 160 base / 46,332 cautious односторонних поездки за 25 дней. Каждый занимает два кресла. 85 местных + 10 защищённых ≤100 — условная физика, а не фактические остатки.

**Пары, частоты и период.** 06–30.07.2027, вторник/пятница, восемь RT каждого оператора и по 10 защищённых мест на плече. Own-расписание 2027 условно; перечень RW за ноябрь–декабрь 2026 — отдельный источник.

**Тип и рабочий ресурс.** 100-местный SSJ-аналог RW и условный feed. Добавочный борт не требуется лишь если оба рейса уже входят в KEEP. При хотя бы одном новом рейсе own-экономика неприменима.

**Откуда самолёт и прежнее задание.** Внешний оператор, права и блок UNKNOWN. Own требует остатков на обоих рейсах; переток и потеря прежнего вклада заданы probe. Старые RW-сегменты перетёкших поездок UNKNOWN.

**Конкуренты и альтернативы.** RW IJK–SVX за ноябрь–декабрь 2026 официально перечислен; это не award, слоты или продажи 2027. Полный тариф с 20кг, единый билет, MCT, защита и инвентарь UNKNOWN.

**Результат и его граница.** External K=0: предел цены 6671,20/599,23 ₽ за зарезервированное место. Own: предел integration K 0,987/0,066 млн ₽ за 25 дней; reference-сумма авиатарифов 8382 ₽ снижает base до 0,893 млн ₽. Это границы договора, а не прибыль.

**Неучтённые расходы и порог.** Внешний блок 480 тыс. ₽ оплачивается полностью. Own IT, retime, claims и cash старых продаж не считаются нулевыми. Extra-flight grant нет. External и own не складываются; company growth UNKNOWN без старых RW-сегментов.

**Денежные потоки.** External base cash end 787392 ₽ до K, economic delta 587392 ₽ после потери старого вклада 200 тыс. ₽. У own нет внешнего платежа, но финансирование интеграции NOT_ESTIMATED.

**Условие продолжения.** Подписан партнёрский блок либо подтверждены оба own KEEP, остатки, единый билет, защита, переток и бюджет ниже Kmax.

**Отказ и пересмотр.** Cautious внешний блок при 3000 ₽/место не проходит: требуется 231,96 поездки при 160 местах. Новые C31 рейсы 05/08.07 не дают feed C35 во вторник/пятницу.

| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |
|---|---|---:|---|---|---|
| maximum_partner_price_per_reserved_seat | base; program=IJK_SVX_OMS_external_feed_conditional, K_probe=0 | 6671.2 | RUB/reserved seat-segment | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv) |
| through_oneway_journeys | base; program=IJK_SVX_OMS_external_feed_conditional, K_probe=0 | 160 | one-way OD journeys/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv) |
| variable_incremental_contribution_at_block_probe | base; program=IJK_SVX_OMS_external_feed_conditional, K_probe=0 | 587392.0 | RUB/25-day contract after lost own contribution; before K | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv) |
| maximum_partner_price_per_reserved_seat | cautious; program=IJK_SVX_OMS_external_feed_conditional, K_probe=0 | 599.2323107155457 | RUB/reserved seat-segment | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv) |
| through_oneway_journeys | cautious; program=IJK_SVX_OMS_external_feed_conditional, K_probe=0 | 46.332021994581545 | one-way OD journeys/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv) |
| variable_incremental_contribution_at_block_probe | cautious; program=IJK_SVX_OMS_external_feed_conditional, K_probe=0 | -384122.83028551267 | RUB/25-day contract after lost own contribution; before K | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv:CSV-record-5](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/C35_partner_thresholds.csv) |
| maximum_integration_retime_risk_K | base; fare_case=original_no_support_fare, K_probe=0.0 | 987392.0 | RUB/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv) |
| through_oneway_journeys | base; fare_case=original_no_support_fare, K_probe=0.0 | 160.0 | one-way OD journeys/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv:CSV-record-2](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv) |
| maximum_integration_retime_risk_K | base; fare_case=raw_special_tariff_sum_reference_no_new_grant, K_probe=0.0 | 893120.0 | RUB/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv) |
| through_oneway_journeys | base; fare_case=raw_special_tariff_sum_reference_no_new_grant, K_probe=0.0 | 160.0 | one-way OD journeys/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv:CSV-record-3](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv) |
| maximum_integration_retime_risk_K | cautious; fare_case=original_no_support_fare, K_probe=0.0 | 65761.35541800929 | RUB/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv:CSV-record-8](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv) |
| through_oneway_journeys | cautious; fare_case=original_no_support_fare, K_probe=0.0 | 46.332021994581545 | one-way OD journeys/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv:CSV-record-8](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv) |
| maximum_integration_retime_risk_K | cautious; fare_case=raw_special_tariff_sum_reference_no_new_grant, K_probe=0.0 | 65761.35541800929 | RUB/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv:CSV-record-9](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv) |
| through_oneway_journeys | cautious; fare_case=raw_special_tariff_sum_reference_no_new_grant, K_probe=0.0 | 46.332021994581545 | one-way OD journeys/25-day contract | 2027-07-06/2027-07-30 | [388908b6da:context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv:CSV-record-9](https://github.com/Mput13/case_championship/blob/388908b6da3539484cb8e2e03ada6ff5cb2204a4/context/28_evening_run_20261110/products/outputs/addendum_C35_internal_KEEP.csv) |

**Независимая проверка.** Conditional money/calendar/treasury fixtures/readiness truncation/own KEEP/support constraints. Не приняты: market/actual resource/contracts/award/full company budget/cash. [6cc8c37e23:context/28_evening_run_20261110/products_review/report.md:L64](https://github.com/Mput13/case_championship/blob/6cc8c37e23c89488f3113efd96952d13f253f274/context/28_evening_run_20261110/products_review/report.md#L64).

Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.
