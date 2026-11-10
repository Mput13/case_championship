# Проверка коррекции ROOT-DASH-01

**APPROVE_SCOPED** — коррекция в exact root `0f07ec43ad3cf515e3bafbb767ade9caa2ba984c` закрывает **только P2 ROOT-DASH-01**. Открытых замечаний в этой коррекции не обнаружено. Минимальное исправление выполнено: одна ложная запись отсутствия KUF–SVX заменена явной связью C33 с существующими свидетельствами. Новые наблюдения, экономические результаты и допуски не добавлены.

Исходная сборка `5101302f93c349268f4ba0ff26832ff261e1a9e7` остаётся прежним предметом с историческим CHANGES. Этот статус сообщён в задании; исходный reviewer не опрашивался, его финальный пакет не ожидался. Сам дефект независимо воспроизведён здесь по точным Git blobs. Настоящее заключение не является повторным review всей исходной сборки.

## Предмет и происхождение

| Вход | Точная версия | Использование |
|---|---|---|
| Коррекция | `0f07ec43ad3cf515e3bafbb767ade9caa2ba984c` | Все 8 файлов `integration/dashboard_context_correction/` |
| Исходная сборка | `5101302f93c349268f4ba0ff26832ff261e1a9e7` | Исходные JSON, 85 связей и Git objects сохранённого пакета |
| Evidence | `38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b` | Реестр пар, join, 34 точные строки контекста и frozen контроль публикаций |
| Программные строки C33 | `b47118a48b6d5480217077bf8699a63665c0eb7a` | 16 источников строк из исходного `program_changes.json`; без запуска модели |

Прочитан root AGENTS.md. Входы читались через `git show <exactSHA>:<path>`. `source_manifest.json` ревью содержит 22 прочитанных файла с commit, path, Git blob, SHA256 и размером. Все пять записей manifest коррекции проверены независимо против blobs; все пять перечисленных выходов совпадают с её output manifest. README и build.py дополнительно привязаны собственным manifest ревью.

## P2 и минимальное исправление

В [исходном build.py:229](https://github.com/Mput13/case_championship/blob/5101302f93c349268f4ba0ff26832ff261e1a9e7/context/28_evening_run_20261110/dashboard_handoff/build.py#L229) ключ `(hypothesis_id, route)` используется как условие глобального отсутствия пары; строки 232–235 создают `NOT_IN_EVIDENCE_PAIR_REGISTRY`. Для C33 это породило ложный `RC:calculation_pair_gap:PC:network:route_delta:254` ([исходный JSON:34674](https://github.com/Mput13/case_championship/blob/5101302f93c349268f4ba0ff26832ff261e1a9e7/context/28_evening_run_20261110/dashboard_handoff/route_context.json#L34674)).

При этом [Evidence pair_registry.csv:21](https://github.com/Mput13/case_championship/blob/38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b/context/28_evening_run_20261110/evidence/pair_registry.csv#L21) содержит KUF–SVX с `hypotheses=C03`. Исходный JSON уже содержит 34 соответствующих строки C03, а C33 — 16 программных строк этой пары. Недостаёт ассоциации, а не самой пары в реестре. Последствие P2: потребитель C33 теряет доступный конкурентный контекст и получает неверное объяснение пробела.

Минимальная коррекция реализована в [build.py:33](../integration/dashboard_context_correction/build.py#L33): проверка глобального реестра, явное основание по программным плечам, копирование существующей строки с сохранением её содержания, удаление одного ложного gap и замена ссылок C33. [Строки 55–60](../integration/dashboard_context_correction/build.py#L55) отделяют новый ID ассоциации от `original_evidence_record_id`; [context_patch.json:46](../integration/dashboard_context_correction/context_patch.json#L46) задаёт `CALCULATION_LEG_CONTEXT:C33:KUF-SVX`, а строки 51–268 содержат 16 programme IDs, их provenance, 34 исходных evidence IDs и границы переноса.

Дополнительное исправление владельцу не требуется. Никакой исходный файл или статус review нами не менялся.

## Независимые проверки

`verify.py` самостоятельно собрал ожидаемые `cards.json` и `route_context.json` из точных исходных JSON и Evidence. Для обеих исправленных JSON получено **полное побайтное совпадение**, включая порядок и метаданные. Эта реконструкция не вызывает и не импортирует `project()` владельца.

| Проверка | Независимый результат |
|---|---|
| Строки контекста | `639 − 1 + 34 = 672`: число связей выросло на 33; новых наблюдений 0 |
| Содержание 34 aliases | 1 pair_coverage + 4 weekly_service_summary + 26 published_departure + 2 fare + 1 gap |
| Источники aliases | Все 34 `source_fields` равны точной CSV-строке Evidence38f; source_row, commit, path, Git blob, SHA256, source_id, URL и locator проверены |
| Численные поля aliases | Сохранены все поля исходных строк; отдельно зафиксированы 129 численных leaf-значений, включая поля provenance |
| Программа C33 | Ровно 16 исходных записей KUF–SVX: 8 route_delta и 8 dated_flight; содержимое всех 16 CSV-источников проверено |
| Карточки | Все 164 metric cells десяти карточек совпадают целиком, включая единицы, период, сценарий, variant и accounting_boundary |
| Другие поля карточек | Девять карточек полностью неизменны; у C33 изменён только `route_context_ids`, 57 → 90; общие metadata неизменны |
| Внешние ключи | Каждый route_context ID уникален, существует и относится к той же гипотезе; ссылки карточки равны полному множеству её контекстных строк |
| Скрытый ложный gap | Старый gap ID отсутствует во всём corrected cards/context JSON; у C33 нет ни calculation_pair_gap, ни статуса NOT_IN_EVIDENCE_PAIR_REGISTRY |
| Реальные пробелы | TLV–ZIA и SVX–ZIA отсутствуют в данном реестре; обе исходные gap-строки C31 сохранены буквально |
| Уникальные свидетельства | Множество точных source locators неизменно: 382 → 382; уникальных published departures 215 → 215 |
| Исходная поставка | Все 71 Git blob исходного пакета совпадают с копией `integration/dashboard_handoff/5101302f/` в root; включая route_links.csv и legacy CSV/Markdown |

Новая ассоциация записана в `context_patch.json`; исходные 85 строк `route_links.csv` не расширены. Связи aliases внутри corrected JSON не являются новым evidence join upstream.

Проверяемые точки в corrected JSON: первая добавленная alias-строка — [route_context.json:34756](../integration/dashboard_context_correction/route_context.json#L34756), первая новая ссылка C33 — [cards.json:26752](../integration/dashboard_context_correction/cards.json#L26752), последняя — строка 26785. Сохранённые истинные gaps находятся в route_context.json на строках 34674 и 34715. Полное сравнение проверяет все строки, а не только эти примеры.

Пример сохранённого направления: `RC:fare:C03:3` остаётся тарифом **SVX → KUF, 4600 ₽**, а строка 8 — **KUF → SVX, 5100 ₽**. Неявный год, неизвестный багаж, `final_quote=False` и capture date остаются исходными. В опубликованном UT-282 07.12.2026 сохраняется конфликт `17:10 | 17:15`; в WZ-1034 — `10:40 | 10:45`. Ни alias, ни ассоциация не выбирают новое время. Годы, даты, направления, time_class, partial coverage и запрет автоматического переноса на 2027–2028 сохранены. Все economic/market/resource/full-PnL/team-acceptance поля карточек неизменны.

## Контрпримеры

1. **Недостающая ассоциация.** Независимая проверка глобального отсутствия отвергает исходный C33 gap, поскольку KUF–SVX уже есть в реестре. Исправленный набор проходит. Отдельный in-memory случай с удалёнными 34 supporting rows отвергается owner projection сообщением `('Known registry route without delivered context', 'KUF-SVX')`; контекст не придумывается.
2. **Настоящий пробел реестра.** TLV–ZIA и SVX–ZIA сохраняют исходные ID и содержание. Отсутствие пары в frozen реестре не трактуется как отсутствие реальных рейсов или конкурентов.
3. **Дубли ID.** Добавление точного дубликата исходной строки и отдельное дублирование нового alias отвергнуты owner projection и независимой проверкой уникальности. На baseline все 672 record IDs уникальны.
4. **Сложение aliases разных гипотез.** C03 и C33 вместе содержат 68 строк KUF–SVX, но только 34 исходных evidence IDs. Среди них 52 published-departure rows представляют 26 исходных вылетов. Сумма по новым record_id дала бы двойной счёт. Дедупликация по `original_evidence_record_id` (с fallback на record_id) или точному source locator возвращает исходное количество. Покрытие пары, недельные сводки и вылеты также не складываются между собой.
5. **Повторное применение.** Owner projection повторно применена к исправленным данным: JSON/card refs неизменны, новых associations 0, контекстных строк по-прежнему 672.

Frozen контроль Evidence остаётся `359 publications → 215 unique departures`, 144 схлопнутых публикации и 12 конфликтующих instances. Эти значения проверены в исходном `dated_checks.json`; новые aliases не изменяют их. Это проверка счётной семантики данной коррекции, а не универсальный валидатор произвольных наборов данных.

## Проверки владельца и границы вывода

Лично выполнен read-only `python3 -B .../integration/dashboard_context_correction/build.py --verify` после просмотра кода. Затем exact blob этого кода отдельно выполнен с `--verify` в памяти. Оба запуска дали PASS. Для второго запуска дополнительно проверены SHA256 всех восьми файлов коррекции до/после: записи не было. Проверки duplicate/idempotence выше используют отдельно помеченный owner-code replay; независимая реконструкция JSON, source-row проверки, численные инварианты и контрпример сложения выполнены собственным кодом.

Owner `checks.json` и его PENDING review status остаются историей exact root. Они не заменяют независимые assertions. Исторический CHANGES исходной сборки не переписан этим APPROVE_SCOPED.

[README коррекции:5](../integration/dashboard_context_correction/README.md#L5) прямо требует взять **две исправленные JSON**, а остальные файлы — из сохранённой исходной поставки. Та же строка предупреждает об исключении aliases при подсчёте рынка и объясняет отдельный patch при неизменных 85 links. [Строка 9](../integration/dashboard_context_correction/README.md#L9) сообщает, что UI Насти не менялся. Это соответствует diff exact root: восемь файлов коррекции, journal.md и status.json; UI-путей нет. Сохранённые CSV/Markdown являются исходными представлениями: исправленный C33 consumer должен использовать именно указанные JSON.

Приёмка распространяется только на этот frozen projection. Новая экономика, upstream solver, полнота рынка, парк, будущие субсидии, эксплуатационная готовность и фактическое подключение к UI не проверялись и не допускались. Browser/live-source/runtime/provider действий, детей, polling, PR, merge, rebase и force-push не было. Все собственные записи ограничены `dashboard_context_correction_review/`.

Воспроизведение и структура пакета описаны в [README.md](README.md). Итоговый точный commit и совпадение remote ref передаются в финальном handoff сообщения; SHA предмета review во всех артефактах остаётся `0f07ec43ad3cf515e3bafbb767ade9caa2ba984c`.
