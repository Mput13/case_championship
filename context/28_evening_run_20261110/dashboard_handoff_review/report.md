# EV-DASHBOARD: независимая проверка сборки

**CHANGES — одно замечание P2.** Проверен только subject `5101302f93c349268f4ba0ff26832ff261e1a9e7`, пакет `context/28_evening_run_20261110/dashboard_handoff/`, ветка источника `t3/dashboard-handoff-package`. Результат не переносится на последующие исправления. Авторские численные оригиналы и проверенный пакет не менялись.

## EV-DASH-01 / ROOT-DASH-01 — ложное отсутствие KUF–SVX в реестре и потеря контекста C33

**P2, требуется исправление перед подключением этой проекции.** В `dashboard_handoff/build.py:228–238`, непосредственно `229–235`, наличие покрытия определяется по `(hypothesis_id, route)`. Отсутствие этой комбинации превращается в глобальную метку `NOT_IN_EVIDENCE_PAIR_REGISTRY`. Отсутствующая связь гипотезы с парой не доказывает отсутствия самой пары.

Независимое воспроизведение на exact blobs:

- `38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b:context/28_evening_run_20261110/evidence/pair_registry.csv`, логическая CSV-запись **21**: `route=KUF-SVX`, `hypotheses=C03`, `roles=alternative_path_leg`, `coverage_status=PARTIAL_POSITIVE_EVIDENCE`, `published_records=64`. `complete_market=False` и неизвестные остатки сохранены.
- В собранном контексте KUF–SVX имеет **34 строки C03**: 1 pair coverage, 4 weekly summaries, 26 published departures, 2 fare observations, 1 gap. Это разные виды свидетельств; их нельзя складывать как рейсы.
- Для **C33** той же пары оставлена только `RC:calculation_pair_gap:PC:network:route_delta:254`: `route_context.csv:638` (логическая запись с заголовком), `route_context.json:34674–34712`, ошибочная метка на строке **34694**. При этом C33 имеет **16** записей `program_changes` по KUF–SVX, включая альтернативные дельты/рейсы.
- `cards.json` связывает контекст по `hypothesis_id` (`build.py:358–369`). Поэтому открытие C33 по предусмотренному контракту получает ложную метку отсутствия в реестре и не получает 34 уже известных строки контекста KUF–SVX. Само `complete_market=False` не превращается в доказательство пустого рынка; дефект именно в происхождении/доступности контекста пары.

**Минимальное исправление:** отдельно проверять наличие `route` в глобальном pair registry и наличие связи `(hypothesis, route)`. Для KUF–SVX добавить явную связь вычислительного плеча C33 с существующим контекстом и его exact provenance либо явно представить недостающую связь и ссылку на известную пару. Не выдавать её за отсутствующую пару. Сохранить исходные 85 associations без переписывания; дополнительные calculation-leg links маркировать отдельно. Пересобрать только проекцию и затронутые manifests/ссылки карточки. Новое число строк не следует насильно удерживать равным 639.

TLV–ZIA и SVX–ZIA действительно отсутствуют в проверенном реестре 45 пар: два других calculation gaps не являются этим дефектом. Их `source_fields` специально выведены из расчётного плеча, поэтому несовпадение с буквальной строкой исходного flight CSV само по себе не замечание. Все 636 недеривативных context rows имеют точные исходные `source_fields`.

Наблюдение ROOT-DASH-01 было передано в задании. Здесь оно заново установлено прямым чтением exact CSV и сравнением output rows; готовые проверки другого ребёнка не переиспользовались. Координатор уведомлён до завершения пакета. Исправление владельца не выполнялось.

## Что проверено лично

`check_projection.py` не импортирует сборщик, solver или upstream runtime. Он читает exact Git blobs, независимо вычисляет Git blob SHA1/SHA256/размер, проверяет все выбранные исходные поля и нормализованные связи. Итог: **831 assertion, 830 PASS, 1 FAIL** — указанное замечание. Это количество технических утверждений, а не число независимых экономических опытов.

| Объект | Независимый результат |
|---|---|
| Output manifest | 70 hashes/размеров совпали; вместе с самим manifest ровно 71 tracked file, без пропуска/лишнего файла |
| Источники | Все 129 exact source blobs: commit/path, Git blob, SHA256, bytes и source ID совпали; source index согласован |
| Provenance | 4393 provenance objects в JSON: идентичность источника, допустимые CSV records/text lines; применимые JSON pointers разрешены |
| Карточки | Ровно C01/C03/C04/C07/C10/C14/C17/C31/C33/C35; 164/164 selected metric cells равны указанному исходному полю, scenario и variant согласованы с той же строкой |
| Метаданные показателей | Проверены единицы, периоды, named probes и границы учёта; cash имеет entity/kind и не становится contribution. Для каждого из десяти опытов сохранены отдельные base/cautious примеры в `source_examples.json` |
| Программа | 816 rows = 268 route deltas + 146 network flights + 402 product flights; все исходные строки присутствуют ровно один раз в своём классе |
| Связь delta→flight | Все 268 имеют ровно один exact network/variant/flight_id target; calendar_common не считается третьим денежным сценарием |
| Контекст | 639 rows, из них 636 буквальных source rows и 3 derived gaps; published departures, weekly summaries, fares и альтернативы остаются разными типами; замечание выше |
| Evidence | 45 пар/85 исходных links, 22 GAP_NOT_ABSENCE; 359 publications/215 unique departures, 144 publication duplicates и 12 conflicts сохранены. Это проверка проекции сохранённого источника |
| Варианты | 24 unique options/205 route rows/144 readiness rows: исходные поля, FK и option/branch/year grain совпали; уникальные пары каждой сети согласованы с declared pair count |
| Годовые ряды | Все 96 annual rows f99 равны exact source rows, с отдельным subject/review; не объединены с 52/48 author model year v4 |
| Приложения | 14/14 PNG побайтно равны exact d48, SHA256 совпали; изображения не открывались и не оценивались визуально |
| Requirements | 24 исходных требования сохранены; статус относится к scoped handoff. R13 «не выполнено»; условные рынок/физический ресурс/fullPnL/доля/roadmap не объявлены завершёнными |

После чтения всех 631 строк сборщика отдельно запущен разрешённый `build.py --verify`: **PASS, 71 delivered files / 129 exact source blobs**. Это личный запуск owner serializer для byte replay, отдельно от независимого script. Скрипт не пишет файлы в режиме verify; совпадение рабочих bytes с exact subject и Git diff подтверждено отдельно. Зелёный verify не обнаруживает EV-DASH-01 и не даёт сам по себе независимой семантической приёмки.

## Реальные примеры и проверки опасных соединений

Полные записи и provenance сохранены в `metric_cells.json` и `source_examples.json`; ниже — значения из лично прочитанных exact rows, без нового экономического replay.

- **C01:** base delta `1695505.7500616387` ₽/диагностические 7 дней и whole-program contribution `298765.19275470264` имеют разные границы. Cautious whole-program `-5877140.375475809` не заменён дельтой. Период 07–13.12.2026 остаётся diagnostic proxy.
- **C03/C04:** KUF4/OMS1/OMS4/OMS8 и ideal bank не смешаны. Например OMS4 base local `-6482489.569446083`, ideal-bank `-1254350.7739814054` ₽/диагностические 7 дней — разные строки и конструкции. У deployment comparator C03 свой период 06–13.12.
- **C07/C33:** turn45 и occupied_state/15% local-loss сохранены в variant. C33 base `local_only=1458193.5834190338`, `planning_lf_sold_allow100=555719.0707868015`, `all_physical_seats_sold=-9687.602301231294` ₽/диагностический период не усредняются. Совместное использование WZ5071/5072 запрещено в dictionary/README.
- **C10/C14:** C10 launch `32082.592954666667` и steady `16541.296477333333` ₽/человека туда-обратно различаются phase. C14 base air guarantee `57687.37459674075` и package `169127.37459674076` ₽ имеют разные единицы. В паспорт они перенесены с округлением вверх; финансирование TO `9777600.0` ₽ не становится дефицитом airline.
- **C17:** 2027/2028 сохранены в variant; base summer threshold `163.9406638094946` против `163.8747867150325` платящих/летнее плечо не выдаётся за один год. 35 winter + 35 summer RT сохранены. Сценарный support требует одновременно тарифного ограничения/eligible flights; award income не заявлен.
- **C31:** base weekly cap `2117413.6760571776` ₽ — лимит Tu all-in + lost TLV + K при L0 probe, только локальный OMS прирост `5.823543308578489` сегмента. Это не полный чистый transfer эффект и не подтверждённый свободный Ту.
- **C35:** external cap `6671.2` ₽/reserved seat-segment отделён от own KEEP base K `987392.0` ₽/25 дней и fare-case sensitivity. Cash end `787392.0` ₽ не объявлен economic delta `587392.0` ₽: потерянные 200000 ₽ вклада отражены отдельно. Own и partner feed не суммируются.
- **Adversarial join:** один `C01_NORTH_20261207T0630_NJC_UFA` присутствует в `sync` и `unsync`. Join по одному flight_id создаёт неоднозначность. Проверенная delta→flight связь с network+variant+flight_id выбирает один target. Сами base/cautious delta rows не превращаются в новые вылеты.
- **C31 против C35:** ADD_SSJ_OMS датирован 05/08.07.2027; C35 начинается 06/09.07 и продолжается по Tue/Fri до 30.07. Общего service date нет. Простая общая пара/местное время не дают feeder C35 из C31.
- **MOW:** единственная строка координат MOW имеет пустые latitude/longitude и CITY_AGGREGATE_UNRESOLVED. Статус unresolved применён к вариантам, действительно содержащим MOW; варианты без него остаются MODEL_IATA_ONLY_NO_DATED_DISPATCH. DME/SVO не подставлены вместо города.
- **Контекст/альтернативы:** 397 projected published-departure context rows — fanout по гипотезам, а не 397 distinct departures. 16 alternative paths и 6 timing examples — контекст поездки с UNKNOWN для защиты/остатков/цены, не ACTION flights. Уникальных публикационных departure instances в source 215. Неполное покрытие не даёт отсутствия конкурента.

## Исторические и текущие вердикты

Лично сопоставлены handoff receipts network/products/evidence/digital/f99/v4: каждый текущий APPROVE_SCOPED ссылается на соответствующий exact subject и review commit. Это **проверка верного переноса чужих вердиктов**, не повторение их научной работы. Их объёмы экономических/источниковых проверок не включены в мои 831 assertion.

Исторические PENDING_EV_MR03/PENDING_EV_MR04 остаются отдельными historical events; exact approvals — отдельными fresh events. Исторический `strategy/acceptance_register` не переписан. `5512f7d474a5db4bb658aae30b10f8b886629861` — packaging-only envelope: три файла равны его exact bytes, восемь subject→review mappings согласованы; новый blanket review аналитики из этого не следует. D03 root-correction и её independent correction review NOT_RUN сохранены отдельно от исходного digital scoped review.

README/HANDOFF/паспорт сохраняют цель №2 без срока, этап 2027–2028, границы whole-company/segments/journeys, 25 reserve как неотклонённые, различие SSJ analog/SJ100, условный N(t), отсутствие TEAM_ACCEPTED сети/полного PnL и неприсуждённую поддержку. Исторический масштаб 2025 не выдан за прогноз 2028. H11 сохраняется как техническое условие для общей недели 27.12.2027–02.01.2028. Самостоятельно 2298 weekly LP, N(t), pricing, full treasury и исходные экономические модели не воспроизводились.

## Передача и граница

Разрешённая запись — только `dashboard_handoff_review/`. `source_manifest.json` содержит 71 subject file и 129 upstream inputs с независимо проверенными hashes; `output_manifest.json` покрывает файлы этого review, исключая себя. Проверка завершена одним пакетом до 21:30 МСК; новых задач/детей нет.

Воспроизведение: `python3 context/28_evening_run_20261110/dashboard_handoff_review/check_projection.py` пишет только review receipts. Допустимый дополнительный byte replay: `python3 context/28_evening_run_20261110/dashboard_handoff/build.py --verify`.

Не выполнены UI/browser/visual QA, live search/fetch, действия над runtime/server, экономический replay upstream, допуск рынка/физического парка/award/fullPnL/cash/будущей доли и стратегии. Новый exact root fix требует отдельного scoped receipt; этот **CHANGES** остаётся историческим вердиктом для `5101302`.
