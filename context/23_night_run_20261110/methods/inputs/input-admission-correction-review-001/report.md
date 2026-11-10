# MR15: исправление привязки oracle receipt

**APPROVE в scope MR14-P2-01.** Для отдельной correction из exact root `4a89bf1c04b24224a6a85a6cb9b6ca1cad032ab0` дефект закрыт. Новых P1/P2/P3 в этой проверке нет. Исходный MR14 на owner `7e65c687e12cf45534852a3c47d6a5c8cf7dda07` сохраняет **CHANGES**; его код этим пакетом не исправляется. Новая приёмка записана отдельно в [findings.json](findings.json).

Проверка самостоятельная, Sol 6.1 xhigh. Прочитаны contract, MR15 brief, исходный guard, corrected-копия, root runner, receipt и три exact MR11 blobs. Все предметные входы извлечены через `git show <exact SHA>:<path>`; 33 пары commit/path с Git blob OID, SHA256, длиной и grain перечислены в [source_manifest.json](source_manifest.json). Исходный review: `f579eeb888a98554b901afeee628c30a85cc48bf`; независимый oracle: `ea2a9626aef75c121f2da7d778b47edce0d571b7`.

## Receipt и минимальная правка

В `input_admission_correction/admit_frozen_interaction.corrected.py:97–100` receipt читается как байты, его SHA256 проверяется **до разбора JSON**, затем выполняются прежние проверки файлов. Ожидание `8373a8085682cc9df3660433f8024a78a377f9b512c93d05ecaafbc9a71d2db6` лично получено из `7e65c687…:context/23_night_run_20261110/methods/inputs/integration-oracle-001/receipt.json`. Оно закрепляет весь receipt: `input_set_id`, общий и пофайловые source commits, точные source/local paths, полный список из трёх разных файлов, SHA256, длины и оговорку exact-input acceptance.

Для каждого файла receipt проверены source commit `ea2a9626…`, ожидаемый путь в `methods_integration_review/`, local path в `inputs/integration-oracle-001/`, длина и равенство owner-копии exact MR11. Список обязательных имён задан в моей проверке независимо от содержимого receipt.

| Exact MR11 файл | Байты | SHA256 |
| --- | ---: | --- |
| independent_affected_itinerary.csv | 17824 | `b08c0d68b7c3c2ae2b0421ffa7c67cc55d2d5129fc827e011ec3043462dfff86` |
| independent_cancellation16.csv | 3226 | `5487aec63c2818730504408ab804ae414e574c85b84ee3c72beda6fddf3b5935` |
| adversarial_probes.json | 4417 | `3738e2a41895876dddb2a761c4c7c6fb2e84065d01781cdebcd22a255d5f45e2` |

Охват файлов: 160 уникальных affected itinerary keys, 16 cancellation-policy rows, 17 сохранённых adversarial probes. Это проверка состава и происхождения upstream evidence; полный MR11 заново не исполнялся. [receipt_checks.json](receipt_checks.json) содержит полные пути и commits, а также проверку всех 16 записей root source manifest и восьми записей root output manifest.

[verified_minimal_diff.patch](verified_minimal_diff.patch) побайтно совпал с root `minimal_fix.patch` и предложением MR14 `suggested_fix.patch`. Единственная замена — одна строка загрузки receipt на три строки с проверкой его байтов. Остальной guard, формулы и его существующие отрицательные пробы неизменны.

## Воспроизведения

Root `verify_correction.py` исполнен из exact blob в моём временном каталоге. Переназначены только `HERE` и `REPO`, чтобы все его записи остались в review scope. Его 11 before/after случаев прошли; заново созданные `validation.json` и `source_manifest.json` побайтно совпали с root. Квитанция: [parent_runner_replay.json](parent_runner_replay.json); результаты: [parent_replay/validation.json](parent_replay/validation.json).

Отдельный [verify.py](verify.py) запускает неизменённые original/corrected **main в новых процессах Python**, с реальными `common_demand.rows/save` и Git comparisons. Перед каждым запуском восстанавливаются exact inputs и удаляются только собственные прошлые выходы. Каждый отказ оставил **ноль admission output files**, поэтому PASS не мог быть прочитан из предыдущего запуска. Полные изменения входов, хеши, exit codes и точные ошибки: [own_probes.json](own_probes.json).

Проверены 17 собственных main cases. Original принял девять provenance/coverage/byte подмен; corrected отверг все 17 с ожидаемыми кодами. Требуемые wrong receipt, empty coverage, oracle + self-updated receipt отвергнуты с `ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW`. При неизменном receipt подмена oracle отвергнута обоими main с `ORACLE_HASH_DRIFT`. Изменение количества oracle при self-updated receipt original по-прежнему отвергает с `INDEPENDENT_AFFECTED_ORACLE`; четыре основных byte pins также сохранены.

Два собственных содержательных контрпримера проверяют supporting evidence и покрытие:

- `own_fabricated_cancellation_evidence_self_receipted`: в первой из 16 строк заменены `delta: 255219.47168930015 → 123456789`, `full_budget: пусто → 0`, `actual_cash: пусто → 0`, затем пересчитан receipt. Original завершился успешно и сохранил прежнее указание MR11 в выходах; corrected отказал по receipt pin. Это демонстрация происхождения required support, без заявления о приёмке выдуманных финансовых величин самим main.
- `own_three_entries_but_duplicate_coverage_and_forged_support`: receipt содержит три копии записи affected oracle, исключая оба support-файла; cancellation evidence подменён теми же значениями. Original принимает, corrected отказывает. Сохранения одного числа `len(files)==3` было бы недостаточно для такого покрытия.

Дополнительно original принимает oracle, восстановленный из owner sales, с обратным порядком строк и маркером `REBUILT_FROM_OWNER_SALES_NOT_MR11`; corrected блокирует self-updated receipt. Четыре защищённых input-файла во всех этих bypass случаях остаются exact.

Original и corrected baseline оба завершились успешно. Три выхода в [baseline/](baseline/) побайтно совпали между собой и с опубликованными owner-выходами: `checks.json` (`a75d60e2…`, 391 байт), `input_receipt.json` (`40d3af9d…`, 1045), `mutation_checks.json` (`96ecf999…`, 842). Полные хеши — [checks.json](checks.json). Сохранены 384 itinerary, 12 групп, 160 affected rows и семь прежних отрицательных проб. Историческое поле `independent_review_of_new_guard=PENDING` в baseline намеренно сохранено; MR15 — отдельное событие приёмки.

## Граница приёмки

Фактическая правильность сохранённого oracle установлена прямым сравнением с MR11. Гарантия admission в corrected main отдельно подтверждена закреплением receipt и отказами на подменах. Приёмка относится только к corrected-копии и этому exact input set. Порча даже форматирования receipt требует новой проверки — это ожидаемая политика byte pin.

Старый owner guard и старый interaction не получают защиту автоматически; новые inputs не допускаются. Четыре delay HOLD и ограничения clock/source/market/full-budget/actual-fleet сохраняются. Full MR11/MR12/MR13, проекция и основной паспорт, новые экономические расчёты, фактические продажи, operating/launch acceptance и выбор команды — **NOT_RUN / OUTSIDE_SCOPE**.

Проверяемая correction, owner/integration originals, public report, Site и dashboard не менялись. Временный runtime удалён. Команда — [reproduce.md](reproduce.md). Все записи пакета находятся только в `context/23_night_run_20261110/input_admission_correction_review/`; продолжение цикла этим review не запускается.
