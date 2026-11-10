# MR10: независимая проверка двух исправленных пакетов

**A — APPROVE_SCOPED. B — APPROVE_SCOPED.** Новых P1/P2 в пределах brief не установлено. Это два отдельных решения по производным, а не одобрение первичных источников, рынка или выполнимого расписания.

Проверка завершена 10.11.2026 до 08:00 МСК. Prepared root: `47de3dfb3d20c29232396f5a28c664a97630b3d9`. Проектные входы читались только через `git show <exact SHA>:<path>`, без moving owner folders, загрузки raw, обращений к коллегам и повторного полного MR02 cost/source review.

## A. Происхождение снимков SVX

Проверенный correction root — `f1774e1f66a9483fb618ca6003abd9dc4d8563e1`, папка `context/23_night_run_20261110/primary_lineage_correction/`. Далее пути A отсчитываются от этой папки.

Исходное SJR-P2-001 воспроизведено лично: все 129 SVX dated rows из primary `17b4f348f15ea8695688d9435933cb4965568408` имели hash, отличный от hash registry с тем же source_id. Идентичность URL/source_id не различает снимки 08.11 и 09.11. Закреплённый первичный receipt: `93fa5cf4a10ab67e05c93d19fc5375fc58ef9299:context/17_aircraft_route_review/evidence/sources.json`.

Для `svx_schedule` receipt на строках 77–84 содержит `accessed=2026-11-09`, HTTP 200, `PRIMARY_WINTER_TIMETABLE_PARSED`, SHA256 `7dd62cd41ba1b2bd340ba7bed3007a1e768f34c977f6e7da16b8a5f7542b7155`. Для `svx_schedule_arr` строки 87–94 содержат ту же дату/status и SHA256 `7400ae30f2519a29f47cb858814c134120fbdd14eaab21f2638c43fb24255350`. Это literal receipts, а не заключение по внешнему виду hash. Они записаны вместе с примерами строк в `lineage_receipts.json`.

Лично проверено:

- `source_registry.csv:47` и `:48` ссылаются на эти context17 receipts, полные raw hashes, дату и HTTP 200. `access_status=REUSED_SOURCE_HASH_FROM_MANIFEST` и `claim_status=PLANNED_NOT_EXECUTED` сохранены. В receipts нет `bytes`; новые `bytes` — NULL, старые 391938/411500 не перенесены.
- `historical_snapshot_registry.csv:2` и `:3` сохраняют context12 снимки 08.11 с отдельными полными snapshot IDs, размерами и `HISTORICAL_SNAPSHOT_NOT_SUPPORT_FOR_CONTEXT17_ROWS`. Среди 48 current и 2 historical snapshots нет дубликатов идентификаторов.
- Все 4180 исходных клеток 209 dated rows и 13124 исходных клетки 386 mapping rows совпадают строка в строку, включая времена, source-row locators, статусы и UNKNOWN. Потерь, новых строк и смены порядка нет.
- Каждая из 209 dated rows имеет FK `source_id@sha256:<полный hash>`, совпадающий с current registry. Все 129 затронутых строк независимо соединены по исходному `source_row` с context17 `published_service_facts.csv`; проверены literal endpoints, даты, local times, carrier/flight/aircraft, duration, URL, hash, evidence kind и capture date. 65 строк отправления и 64 прибытия.
- Ровно 28 исходных cards имеют по одному binding без выдуманных source IDs. Ровно 58 mapping rows соединены с ними по card ID, source ID и полному hash. Сохранены 42 `CONTEXT_CANDIDATE_ONLY`, 10 `NO_BASELINE_ENDPOINT_MATCH`, 6 `HOLD_EXACT_CLOCK; SUPPLY_CONTEXT_ONLY`.
- Все 6 HOLD находятся в correction mapping на строках 64, 65, 70, 71, 137, 138. Seats, observed final OD и net fare остались NULL; `numerical_uplift=NONE`, `model_input_changed=False`. Context/no-match не стали допуском supply или спроса.

Новые dated columns — `source_snapshot_id`, `original_csv_line`, `lineage_correction_status`. Новые mapping columns — `original_mapping_csv_line`, `source_snapshot_id`, `lineage_projection_status`; у незатронутых mappings snapshot FK пуст, их происхождение этой correction не проверялось заново. Registry добавляет receipt commit/path и snapshot ID. Это provenance, а не изменение содержательных клеток.

**SJR-P2-001 закрывается для metadata этой производной.** Историческое `CHANGES` для original17b не переписывается. Raw bodies не перепарсены; содержание источников, выполненные рейсы, юридическая вместимость, year/clock/OD, продажи и источник спроса не получают нового принятия. Граница `SOURCE_SUPPORTED` этим review не повышается.

## B. Временная ось и зависимые результаты

Проверенный correction root — `87ee52de15c2bdf396d9c06ba600fd413d5ab4a8`, папка `context/23_night_run_20261110/cost_kover_timebase_correction/`. Далее пути B отсчитываются от этой папки. Original overlay — `afadee35ebeefe54a05bdfc5b3e224a370f90e0a`.

Авторская временная ось установлена по `93fa5cf4a10ab67e05c93d19fc5375fc58ef9299:scripts/build_team_comparison.py:28` и `:363–365`: минуты уже содержат `(day-1)*1440`; epoch — `2026-12-07T00:00Z`. Correction `build.py:61–64` прибавляет минуты к этому epoch. Воспроизведено исходное повторное прибавление дня в original `overlay.py:65–66`.

Лично проверено независимым oracle на epoch seconds и Decimal minutes:

- 66 уникальных legs, 132 departure/arrival events, обе даты. Все corrected timestamps совпали; 70 исходных событий/35 legs были неверны. В original physical table ошибка повторялась в 350 строках; проверены все 660 пар corrected UTC в производной.
- `H_UFA_8_028`, row date `2026-12-08`, minute 1885: `2026-12-08T07:25:00+00:00`, не 9 декабря. Correction `timestamp_projection.csv:126` содержит departure, `:127` — arrival. Окно второго дня `[2026-12-08T00:00Z, 2026-12-09T00:00Z)` даёт 16 UFA8 legs вместо исходных 0, с проверкой exact ID set.
- Проверены оба конца half-open interval, departure/arrival именно в ограниченном аэропорту, отсутствие эффекта для другого аэропорта, отрицательный interval, переход 1435→1495 через UTC-полночь без modulo. Эквивалентное окно с `+05:00` даёт те же ID; 07:25Z = 12:25 Уфа и 13:25 Омск. Local clock не подменяет UTC в модели.
- Из exact correction build извлечена только `corrected_instant`, без выполнения build. Её результат совпал с отдельным oracle на offsets -1, 0, 1435, 1440, 1495, 1885, 2879, 2880, 10079, 10080, 10081 даже при заведомо иной metadata row date. Horizon guard исходного apply с этой функцией принимает arrival за минуту до 14.12 00:00Z и отклоняет arrival ровно на границе и позже. Все реальные выбранные legs внутри недели, их durations сохранены.
- Независимо повторена смежная проверка тех же planning labels после сдвига day1 на +1440. Exact conflict sets совпали: 23 UFA8 и 11 UFA4 для каждого base/cautious, всего 68 строк в correction. H1–H4/H1–H2 сохранены; actual tails NULL. Прямые D_pilot/D_case имеют 0 этих конфликтов.

23/11 — конфликты конкретного смежного шаблона на закреплённых labels и 45-minute turn. Это не доказательство невозможности всех альтернативных ротаций, замены planning labels или восстановления другими бортами. Реальные ресурсы восстановления не установлены.

## B. Admission и сохранность арифметики

Четыре случая UFA8/UFA4 × base/cautious удержаны. `scenario_summary.csv:5`, `:10`, `:15`, `:20` имеют `HOLD_DELAY_COMPLETION_UNRESOLVED_ROTATION`. Remaining endpoint journeys, unserved journeys/segments, итоговый contribution, overlay delta и admitted cash peak — NULL. Прежние числа сохранены только в `hypothetical_*_if_recovered`. Код gating — `build.py:135–150`.

Таблицы проверены совместно:

- `affected_journeys.csv:58` показывает NULL для served/unserved и retained fare, с отдельными hypothetical columns. Все связанные строки четырёх случаев имеют HOLD.
- `physical_leg_status.csv:98` и все остальные physical rows этих случаев имеют HOLD, conditional timestamps и исходные planning labels. Числовые `remaining_capacity/remaining_occupied` описывают кандидатное распределение мест; статус удерживает их от принятия как перевозки. Capacity conservation отдельно проверена на этом распределении.
- `cash_fixture.csv:11` и связанные cash rows имеют `HYPOTHETICAL_COMPLETION_CASH_NOT_AVAILABLE_SCHEDULE`. Числа в них — условная algebra fixture; отдельных admitted cash columns в файле нет. При чтении этого файла нужен `value_status`. Admitted summary peak остаётся NULL, `actual_full_cash_peak_rub` также NULL. Review не принимает нулевой денежный разрыв как доступный план восстановления.
- Во всех 40 summary rows `usable_as_served_schedule=False`, `actual_operational_readiness=UNKNOWN`, full-budget profit NULL. Unaffected direct programmes не получили ложного HOLD.

Независимо восстановлены affected itinerary unions по flight IDs, расход мест каждого itinerary-leg, endpoint/segment conservation, исходные journey IDs и source-line FKs для всех 40 scenario groups, 660 physical rows и 240 affected journey rows. Применение денежной модели к конфликтному расписанию не принято этим conservation check.

Отдельно выполнен **bounded author replay**, отмеченный так в checks: exact original `overlay.apply` с извлечённой correction-функцией времени и pinned JSON inputs, без author main. Все числовые поля 40 исходных day1 arithmetic rows совпали до admission gating, затем — с corrected либо hypothetical полями. Проверены неизменённые исходные клетки остальных столбцов во всех четырёх таблицах; untouched day1 cancellation и no-kover summary values сохранены. Это проверка дельты времени, а не повтор полной проверки cost/tariff/raw.

Шесть no-kover inputs (flights, sales, capacity, comparison, inputs JSON, overrides JSON) байтово совпали с закреплёнными author exports и original input manifest; correction ссылается на те же hashes и не содержит замен исходников. В производной UTC columns исправлены, run/provenance/status columns изменены явно. Исходные файлы original package не менялись.

`source_commit=93fa...` остаётся авторским источником, `source_overlay_commit=afadee...` — original overlay. Во всех summary/physical/journey/cash rows заданы отдельные `input_set_id=MR02-TIMEBASE-CORRECTION:afadee35`, `run_id=MR02-timebase-correction-v1` и `parent_input_set_id=MR02-input-set-001`. Поле `timebase_correction_source_commit` также обозначает вход original overlay; exact identity correction — проверенный root `87ee52...` и манифест этого review. Его нельзя трактовать как SHA новой correction.

**B принят только как исправленная временная проекция с удержанием зависимых результатов.** Историческое original MR02 `CHANGES` и отдельная cost/source оценка не заменены этим решением. Full dispatch, фактический fleet, crew/slots/MCT, восстановление, контракты и recovery economics — UNKNOWN.

## Проверки, supplied claims и границы

Итог независимого скрипта — **83 PASS, 0 FAIL**. Полный перечень, точные pins и hashes находятся в `checks.json` и `source_manifest.json`; hashes подтверждают идентичность blobs, не рынок или операцию. Манифесты обоих corrections и входные locks проверены.

Предоставленные objections прочитаны отдельно: SJR findings из `944b16ac2dcde846e29dac2d47e11e5143f9fc2b` и original CKR findings из exact payload `af96da977becc161eac132f587e1fd3c4d6918a3`. Их выводы использованы как вопросы к проверке. Перечисленные выше joins, timestamps, affected sets, конфликты, gating и сохранность воспроизведены лично. Прочие CKR claims о raw/tariffs/budget/cash economics здесь не перепроверялись и не наследовались как новое принятие.

Новые P1/P2 и требуемые owner fixes отсутствуют. Публичный Site/report/dashboard, raw и папки владельцев без изменений. Работа закончена одним bounded пакетом; дальнейшего автоматического цикла нет.
