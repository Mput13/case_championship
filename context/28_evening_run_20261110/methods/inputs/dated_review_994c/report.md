# EV-MR03: датированные продажи, ретайминг и C31/C35

**APPROVE_SCOPED** для exact SUBJECT `f99d6cd52dcc06995bf984fddd2f057226243b06`, авторская ветка `research/evening-model-methods-20261110`. Открытых P1/P2/P3 в проверенных результатах этого subject не найдено. Исправления subject не требуются. Пакет пригоден как воспроизводимая условная арифметика с сохранением ограничений ниже.

Это свежая независимая проверка EV-MR03. Вердикт EV-MR02 `8cb5fde05c51ae05f7b72e3cb996f0cb4fa26550` остаётся только про `aa7779192d809558e38b1eb9bdfa25913a3afdc8`; промежуточный `3c87367` не был subject. Проверка не принимает рынок, свободный парк, фактические аэропорты/экипажи, award, полный P&L/cash или готовность общей стратегии. Неудача фиксированной банки не доказывает невозможность хаба.

Все ссылки на методы ниже относятся к указанному SUBJECT и префиксу `context/28_evening_run_20261110/methods/`. Входы Products прочитаны из закреплённой копии `inputs/products_3889/` и сверены с exact `388908b6da3539484cb8e2e03ada6ff5cb2204a4`. Его отдельный product review не ожидался и не подменял личные расчёты.

При read-only проверке опубликованных refs в 20:34 МСК ветка методов уже указывала на `9f0b5d25af720107e99e209e1c69b098497358be`. Этот новый SHA не проверялся и не наследует данный verdict. Scope остаётся exact `f99d6cd…`; наблюдение записано в [remote_refs_before_delivery.json](remote_refs_before_delivery.json).

## Происхождение и способ проверки

Лично проверены 446 output hashes и 313 receipt copies относительно указанных в них Git commits/blobs; отдельно 44 записи `source_manifest.json`. Из 156 записей предыдущего v2 manifest 154 побайтно сохранены; изменились только `handoff.json` и `requests.json`. Версии selection `48686…`, v2 `aa777…`, evidence `38f0…`, network `b471…`, products `388908…` не объединены в один исторический approval. Подробности: [provenance_results.json](provenance_results.json), [receipt_and_preservation_results.json](receipt_and_preservation_results.json), [source_manifest.json](source_manifest.json).

Oracle в [independent_checks.py](independent_checks.py) не вызывает авторские `solve_week`, `emit_day`, `revalue` или авторские PASS. Он заново считает локальные потоки/миграцию, годовые знаменатели, стоимость плеч, один трансферный тариф, временные стыковки и LP incidence matrix. Сохранённые частоты, геометрия и construction slots остаются входами. `model_kernel.load()` используется как ранее проверенный адаптер pinned demand bytes, без новой приёмки качества спроса. Отдельный LP собран с другим порядком строк/столбцов и решён `highs-ipm`.

Все четыре авторских модуля также отдельно исполнены в собственной disposable-копии. Все 19 CSV и четыре validation JSON семантически совпали, максимальная численная разница replay — ноль. 18 CSV совпали побайтно; порядок строк `annual_market_caps.csv` зависит от обхода set, его строки/значения совпали по ключам. Это дополнительная воспроизводимость, а не независимый oracle: [owner_replay_results.json](owner_replay_results.json).

## A. Целые даты и годовые продажи

Независимо пересчитаны все 96 вариантов, 5 088 недельных решений о программе и 2 298 недель с рейсами. Для каждого года проверены 365/366 уникальных дат, minimum daily working N(t), одна программа на неделю, частичные начальные/конечные недели и отсутствие recapture четырёх cautious weeks. Политика из `integer_year_sales.py:77–102` отличается от ежедневной экспозиции v2; старую прибыль на неё не переносили.

Субботний ввод 31.07.2027 не запускает программу посреди недели 26.07–01.08: минимум доступности равен нулю, выбран KEEP. На неделе 30.10.2028 DELAY6/base_sub/OMS ресурс равен `3,5,5,5,5,5,5`; сохранён cap4 с тремя рабочими бортами. Мутация на максимум недели ошибочно допускает cap6 с пятью. Примеры сохранены в [weekly_minimum_examples.json](weekly_minimum_examples.json).

Ресурс проверен по фактическим временным последовательностям: 70 block-hours/week, 14/day, 45-minute turn, непрерывность узлов. Личный полный годовой проход содержит 116 382 перехода, включая смены недельных программ; отдельно 1 156 переходов общей недели 27.12.2027–02.01.2028. В этой неделе выбранная программа совпадает с обеих сторон границы года, 70h сохраняются; подходящих MCT-связей через саму границу года нет. MOW остаётся неразрешённым городским узлом, логические хвосты не признаны реальными регистрациями.

Совместный LP заново ограничивает каждый датированный leg и каждый направленный OD. Фиксированные local seats сохраняются, за through journey начисляется один fare и расходуются два flight seats. Все 563 двунаправленные annual OD bounds совпали; дополнительно проверены 1 059 направленных market-case bounds против половины годового OD. Независимый максимальный primal/dual gap — `1.49e-8` руб.; максимальная разница с опубликованным недельным полем — `5.96e-8` руб.

Для OMS/PHASED/base_sub/2028 по всем 5 976 экспортированным рейсам независимо восстановлены timestamps, направления, хвосты, местные продажи/миграция и стоимость. Все 640 проданных itineraries имеют реальные inbound/outbound legs и MCT 60–180 минут UTC. Занято 54 767,228218 transfer seat-segments = дважды число journeys; transfer gain = 532 431 071,653622 руб. Ещё отдельно проверены 80 диагностических MCT/wait cases, 301 itinerary и 5 544 capacity rows из `connections_v1`.

Контрольные суммы, PHASED/base_sub, млн руб. contribution:

| Сеть/год | v2 active days | Целые кресла без MCT | Фиксированное расписание с MCT |
|---|---:|---:|---:|
| OMS 2027 | 54,924286 | 53,701219 | −227,712396 |
| KUF 2027 | 65,648362 | 63,868227 | −210,024363 |
| OMS 2028 | 280,772129 | 278,724080 | −2 646,596159 |
| KUF 2028 | 279,900443 | 276,829260 | −1 371,700343 |
| DIRECT 2028 | −178,491830 | −178,313560 | −178,313560 |

Числа readout совпали. DIRECT не получает трансферов. Это отрицательный результат конкретной конструкции расписания, а не глобальное опровержение хаба или перенос прежнего 92% порога в достигнутую реализацию (`dated_readout.md:21`). [Полные 96 сравнений](annual_oracle_values.json), [результаты oracle](independent_results_all.json).

Ограничение переноса: код выбирает минимум внутри year-case (`integer_year_sales.py:77–85`). В exact входах смены программы на границе года нет. Синтетический ввод 1 января с ресурсом `2,2,2,2,2,3,3`, исполненный через точный owner selection block, выбирает cap2 в декабрьской части и cap4 в январской. Поэтому approval относится к опубликованным календарям; при изменении N(t) на границе года нужно сначала выбирать программу на общей календарной неделе, затем разделять годовую отчётность. Это не изменение чисел проверенного subject и не открытый P2.

## B. Те же рейсы после ретайминга

Лично восстановлены все 152 исходных рейса OMS12/base_sub по flight IDs, семь рабочих хвостов, прежние block-hours, вместимость и local sales. Сдвигается весь дневной ряд хвоста; проверены 145 переходов и Sunday→Monday wrap при повторении недели. Вклад фиксированных local sales пересчитан с прежней миграцией/foregone один раз, одинаково для обеих сторон (`synchronised_alternative.py:17–25,77–84`).

В этой исходной OMS12-модели listed local migration равна нулю; это не утверждение об отсутствии внешних потерь. Синтетический опыт с ненулевой миграцией отдельно проверяет, что неизменённая local contribution сокращается в разности, а повторный вычет foregone ошибочен.

Отдельный LP дал 985,027816538 → 1 185,181356425 transfer journeys из 4 479,315729185 исходных. Независимо восстановлены потеря 7 возможных связей, появление 14 и восемь рынков с уменьшением продаж. Сумма **подписанных** market deltas × one-fare margins равна `+4 507 578,986112` руб./неделю. Выбор только положительных market deltas этот контроль не проходит.

Contribution меняется с `−67 699 033,108428` до `−63 191 454,122315` руб./неделю. Никакой positive-program claim нет. Сумма абсолютных сдвигов отдельных отправлений — 101 flight-hours, а не дополнительные block-hours. Проверены пять стоимостных проб и условие:

`Δ = 4 507 578,986112 − 101 × k_shift − K_fixed + D_external`.

Здесь D_external — подписанное изменение вклада прежней сети; если его записать как потерю L_external, соответствующий член будет `−L_external`. При нулевых K_fixed и D_external порог k_shift = 44 629,494912 руб./flight-hour. Нераскрытые crew/slots/ground/внешние связи остаются UNKNOWN. Annual projection = NOT_RUN; глобальная оптимальность ограниченного поиска не принята (`dated_readout.md:29`, `synchronised_alternative.py:43–55,88–91`).

## C. Общий календарь C31/C35

Проверка дат/часов выполнена по raw `inputs/products_3889/outputs/dated_flights.csv`, без owner assertions и без same-date prefilter. Новые C31 legs стоят **понедельник 5 июля и четверг 8 июля**, строки 362–365. C35 external feed начинает **вторник 6 июля**, затем 9/13/16/20/23/27/30 июля; на новых датах C31 его нет.

Личный пример 06.07: IJK–SVX прибывает `05:10 UTC` (10:10 SVX), прежний RW SVX–OMS отправляется `06:40 UTC` (11:40 SVX): 90 минут. Обратно RW OMS–SVX прибывает `11:10 UTC` (16:10 SVX), feed SVX–IJK отправляется `12:40 UTC` (17:40 SVX): 90 минут. Это строки 372–375 raw calendar. По всем датам найдено ровно 16 подходящих связей со старыми retimed RW и ноль с новыми C31; в том числе не найдено скрытых связей через соседнюю дату. [Календарные примеры и все связи](product_calendar_examples.json).

Период сравнения содержит ровно C31 week 05–11.07 плюс **весь** C35 contract 06–30.07. После 11 июля C31 остаётся KEEP. Блок C35 = 16 legs × 10 reserved seats = 160, оплата = 480 000 руб. независимо от проданных journeys. В cautious продаётся 46,332022 journeys, но платёж не уменьшается ни до sold seats, ни до 7/25 контракта.

По 40 capacity rows проверены защищённые 85 **all-market** старых продаж, отдельный SVX–OMS f4−f2 increment на четырёх новых legs и IJK–OMS through на тех же старых RW seats. При base через них идут 10 новых journeys/leg: `85+10=95≤100`. Это физическая условная проверка, не разрешение превысить commercial LF85/80 и не наблюдение 85 старых пассажиров.

Для обоих сценариев независимо посчитаны one-fare revenues, собственные расходы, old mission difference и все 18 joint frontiers. Base: C31 ceiling = `2 117 413,676057`, C35 contribution после полного partner block и однократного own loss = `587 392`; общий условный Tu all-in + K ceiling при L_Tu=0 = `2 704 805,676057` руб. Cautious ceiling = `2 661 296,545773` руб. Это потолки неизвестных расходов в указанной разности, не положительная прибыль.

В полном KEEP difference одинаковый старый MRV revenue сокращается один раз; прежнее задание Tu ZIA–TLV входит отдельным подписанным L_Tu. C35 base own loss 200 000 уже вычтен внутри C35 и не вычитается повторно как тот же внешний donor. Непоказанные прежние through markets и прочие donor/slot effects остаются UNKNOWN. Internal own-feed — отдельная альтернатива FINAL Products, к ней не приписывается внешний block payment (`joint_products.py:29–43`, `dated_readout.md:33–37`). [Независимые формулы/значения](product_oracle_values.json).

## Adversarial checks и удержанные выводы

[adversarial_results.json](adversarial_results.json) содержит 32 опыта: 16 формульных/ресурсных мутаций отвергнуты oracle, отдельно проверены допустимые границы и удержанные claims. Исходники/raw/frozen данные не менялись. Это не заявление, что owner verifier сам ловит все наши мутации. Точный owner solver/helper вызван только там, где это прямо отмечено.

Проверены UTC offsets с ложными wall-clock 90 минутами, разные даты с одинаковыми часами, MCT 59:59/60/180/180:01, реальная стыковка через 31.12, shared market при двух возможных itineraries, capacity каждого leg, двойной fare, weekly max вместо min, субботний ввод, partial-week ×7, 365 вместо 366, recapture закрытых дней, уход ретайминга через Monday/Sunday boundary, потерянные внутренние рынки, prorating блока, плата только за sold seats, повтор C31 на весь месяц, подмена old all-market маленьким endpoint, commercial LF против physical100, отсутствие старого Tu donor, двойной own loss и повторный MRV revenue. Генерализация year split и annualization новой банки оставлены отдельными held claims.

Полный список удержанных claims с exact SHA/file:line находится в [findings.json](findings.json). В частности: actual N(t)/free legacy fleet, SJ-100 costs beyond explicit SSJ analogue, MOW airport/crew/slots/MCT approval, реальные спрос/тарифы, права на поддержку и связанные fare ceilings, signed внешние эффекты, полный project/company P&L и cash, actual old-through inventories, partner/Tu availability. Исторический EV-LIMIT-01/OLD144 primary raw_hash сохраняется; новый receipt не исправляет прошлое происхождение. Условный отрицательный ideal-bank результат из отдельного network review относится к planning LF85/80; physical100 — отдельная чувствительность, которую этот review не объявляет невозможностью хаба.

NOT_RUN: live research, первичная повторная проверка evidence/network/products всего scope, новый поиск расписания/доказательство global optimum, market/fleet/award/full-P&L/cash acceptance, annual after-retime projection, UI/browser/Site, сообщения внешним людям, платежи, новые providers, рестарты, PR/merge/rebase. Дополнительные агенты/треды не запускались. Публикация ограничена собственной review-веткой.

## Воспроизведение

Из корня подготовленного репозитория, с уже установленными Python/numpy/pandas/scipy и локально доступными Git objects:

```sh
python3 -B context/28_evening_run_20261110/dated_comparison_review/prepare.py
python3 -B context/28_evening_run_20261110/dated_comparison_review/provenance_checks.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python3 -B context/28_evening_run_20261110/dated_comparison_review/independent_checks.py all
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python3 -B context/28_evening_run_20261110/dated_comparison_review/adversarial_checks.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python3 -B context/28_evening_run_20261110/dated_comparison_review/owner_replay.py
python3 -B context/28_evening_run_20261110/dated_comparison_review/cleanup.py
```

Все generated files/runtime остаются внутри разрешённого `dated_comparison_review/`. Новых зависимостей и серверов нет. До extraction проверен диск: около 5,1 GiB свободно; скопировано 35,4 MB необходимых исходников/входов без `.git` и зависимостей. Временная копия удалена после фиксации доказательств и проверки отсутствия работающих процессов/открытых файлов. Manifest сохраняет исходные blobs и итоговые артефакты.
