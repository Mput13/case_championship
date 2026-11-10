# MR14: допуск входов и квалификации паспорта

**CHANGES — одна P2 в закреплении oracle receipt.** Subject: `7e65c687e12cf45534852a3c47d6a5c8cf7dda07`. Остальные проверенные части нового scope — **APPROVE_SCOPED**: фактические exact-входы, сохранность данных, воспроизведение восьми выходов и отдельная проекция квалификаций. Находка удерживает утверждение о том, что новый guard сам обеспечивает immutable provenance независимого oracle. Она не отменяет MR11/MR12 и не устанавливает ошибку в сохранённых числах.

Проверка выполнена самостоятельно в checkout с исходным HEAD `5c7f0ea561bdf387c7abe476ca68eaf78aa791bd`. Все предметные входы прочитаны через `git show <exactSHA>:<path>`. Три новых скрипта прочитаны и исполнены в собственном краткоживущем каталоге; исходный `common_demand.py` использован для его реальных `rows/save`, без вызова его `main`. Новые зависимости, браузер, платные источники и сетевые исследовательские запросы не использовались.

## P2 MR14-P2-01: receipt oracle не закреплён

Точное место в subject: `methods/admit_frozen_interaction.py:95–98`, с ошибочно безусловным `independent_oracle_commit` в строке 130. Полный префикс: `context/23_night_run_20261110/`.

Четыре основных файла сравниваются с exact `f7a` через Git. Для oracle код читает текущий локальный receipt и проверяет только перечисленные в нём хеши. Сам receipt, его `source_commit`, обязательный набор файлов и coverage не сравниваются с immutable ожиданием. При `files=[]` цикл проверки хешей не выполняется. При замене oracle и обновлении его хеша receipt подтверждает собственную замену. Тем не менее выход продолжает сообщать `ea2a9626aef75c121f2da7d778b47edce0d571b7`.

Личные воспроизведения в [own_probes.json](own_probes.json):

- `oracle_receipt_wrong_source_commit`: заменить source commit на 40 нулей — `main()` завершает PASS и сообщает MR11.
- `oracle_receipt_empty_file_list`: заменить `files` на пустой список — тот же результат.
- `changed_oracle_bytes_plus_self_updated_receipt`: добавить перевод строки к oracle, пересчитать локальный receipt — проходит, хотя байты уже не равны exact MR11.
- `same_owner_reconstructed_oracle_plus_empty_receipt`: построить количества/тарифы из самих защищённых sales, изменить порядок и добавить поле `OWNER_SALES_RECONSTRUCTION`, удалить coverage receipt — проходит как независимый MR11 oracle. Четыре защищённых входа остаются неизменными. Это демонстрирует принятие проверки по тому же источнику вместо закреплённого независимого файла.

Отрицательный контроль: неверный хеш в непустом receipt отвергается как `ORACLE_HASH_DRIFT`. Несовпадающие с sales quantities, fare или affected count отвергает численная проверка. Обход относится к заявленной независимой provenance, а не к возможности незаметно изменить четыре защищённых файла или получить новые экономические результаты. В immutable subject передан **правильный** oracle: его действительное совпадение с MR11 установлено отдельно ниже.

Минимальная правка для этого exact-only guard: до разбора receipt сравнить SHA256 его байтов с независимо проверенным `8373a8085682cc9df3660433f8024a78a377f9b512c93d05ecaafbc9a71d2db6`. Затем сохранить существующие проверки файлов. Этот фикс закрепляет одновременно commit/path/coverage/hash receipt и не добавляет универсальную семантику новых входов. Альтернатива — сравнивать oracle непосредственно с `git show ea2a9626…:context/23_night_run_20261110/methods_integration_review/independent_affected_itinerary.csv` и отдельно закрепить контракт receipt.

[suggested_fix.patch](suggested_fix.patch) — предложение внутри review scope, **owner-код не изменён**. Кандидат исполнен только в памяти: три baseline-выхода побайтно сохранены, четыре receipt/oracle порчи отвергнуты; [candidate_fix_check.json](candidate_fix_check.json). Это не re-review будущего owner commit.

## Закреплённые входы и семантика

Лично подтверждены следующие свойства; расчёты находятся в [independent_inputs.json](independent_inputs.json), происхождение — в [receipt_checks.json](receipt_checks.json) и [source_manifest.json](source_manifest.json).

- Четыре файла побайтно равны `f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9`: 384 itinerary rows, 84 summary rows, 1372 source flights и 2744 capacity rows. Отдельно испробована порча байтов каждого из четырёх файлов: `main()` отказывает до validator API.
- 384 полных уникальных ключа с experiment/source commit/variant/profile/network/input set/period/price/tax, scenario/recipe/multiplier, направленным OD и упорядоченными flight IDs; 12 уникальных unit summary groups. Все контексты согласованы с группами.
- Полные множества flight/capacity IDs, уникальность join, направленные endpoints, связность и capacity metadata проверены независимо от validator. 256 local и 128 transfer строк: один сквозной тариф, одно место каждого использованного плеча, корректные transfer quantities, migration parts, общий направленный D, количество и деньги сводных групп, стоимость каждого рейса в сумме один раз.
- Время интерпретировано как `period_start epoch + absolute UTC minutes` один раз. Дата, day и block duration каждого выбранного плеча согласованы с исходной неделей 7–13 декабря. Сохранён свидетель day 2: `2026-12-08T05:00Z`; ошибочное повторное прибавление дня даёт `2026-12-09T05:00Z`. **Day-1 affected set сам по себе не различает double-day ошибку**, поэтому совпадение 160 строк не выдано за достаточный тест всей временной семантики. Исторический interaction-код побайтно неизменён относительно MR11.
- Oracle имеет ровно 160 уникальных affected keys. Копии всех трёх oracle-файлов и MR11 review receipt проверены по source path, exact commit, SHA256 и длине. Каждый affected key, journeys, fare_once, lost_fare_once и affected_leg_count независимо сопоставлен с защищёнными sales/dated flights. Это не сравнение файла с самим собой: одна сторона вычислена из четырёх входов, другая взята из отдельного exact review commit. MR11 stdlib oracle прочитан как upstream evidence; весь MR11 заново не запускался.

Семь owner mutations лично повторены при выполнении неизменённого нового `main()`; коды отказа и выходные байты совпали: [replay.json](replay.json). Добавлены 23 собственных случая: 13 отказов прямого validator API, 5 отказов `main`, 4 подтверждения обхода receipt и 1 ограничение API. Duplicate/missing key, wrong period context, reversed OD, physical endpoint, conflicting/insufficient directed D, capacity conflict, oracle quantity/fare/affected-count/missing/duplicate key отвергаются.

Ограничение API не объявлено дефектом: замена только origin в capacity metadata проходит прямой `validate()`, но изменяет закреплённые байты; `main()` такую замену не допускает. `validate()` не заявлен универсальным валидатором будущих источников. Старый interaction `main` не переподключён и не исполнен; он не наследует новый guard автоматически.

## Проекция квалификаций

**APPROVE_SCOPED** для новой проекции, а не для основного паспорта. Exact passport: `46fd52db073cffc46a598f44489d0761c6853410`. [qualification_checks.json](qualification_checks.json) фиксирует:

- 26 original requirements, 33 original claims и 16 method-addenda. Четыре переданных исходных passport-файла равны upstream exact-байтам. Все проецируемые original strings, группы и acceptance scope сохранены; исходные файлы целиком доступны отдельно. Ни один addendum не ставит fully satisfied; все строки сохраняют passport independent review `PENDING`.
- C12 остаётся исходным as-of pending тезисом; новые события записаны отдельно. Используется `passport_claim_id`; join с frontier hypothesis по короткому Cxx отсутствует.
- S03 исправляет смысл насыщения: при прежних fares/cost/migration/local-first отрицательный предел D_SVX8 не объясняется нехваткой спроса после заполнения мест. `−449 822,70` сохранено; UFA C thresholds `2,4617708804/2,9194370052` имеют прежнюю область применения. S01/S04 и S03 не переносят alpha/scale/budget bounds на LP.
- R11/R12/R13 и X01 различают model airport-pair counts, связи городов, working labels, фактически доступный парк, выбранную operating network и полный бюджет. Пять model gates/два 12-pair mix не превращены в закрытое требование кейса или launch acceptance.

Лично сверены переносы MR11 (`ea2a…` на `f7a…`) и MR12 (`5e9b…` на `ba9f…`) с exact receipts/findings. Остальные прежние строки admission_v3 сохранены, кроме явно предусмотренного обновления MR13 subject. MR13 остаётся `MR13_RUNNING_EXACT_c6ad`, паспорт — `OWNER_SYNTHESIS_INDEPENDENT_PENDING`, v8 — `OWNER_CHECKS_ONLY_INDEPENDENT_PENDING`. Исторические primary `CHANGES`, cost `CHANGES`, 12 clock holds и 4 delay HOLD сохранены. Это проверка переноса статусов, а не повтор приёмки экономических результатов MR11/MR12/MR13.

## Воспроизведение и сохранность

[replay.json](replay.json): все восемь новых output-файлов после двух исполнений трёх новых scripts совпали побайтно с exact subject и между собой. [preservation.json](preservation.json): все 398 прежних файлов в `inputs/`, `runs/`, `analysis/` равны exact parent `c6ad…`; сохранён их полный список SHA256. Старые расчётные программы, проверенные в новом scope, неизменны.

MR12-O01 закрыт ровно заменами в `decision_conditions.md:25`: `1786,197→1786,193` и `542,443→542,444`. Вся строка и остальной документ отличаются только этими двумя заменами. Старые численные CSV сохранены; money, delta и вывод не пересчитывались. [owner_manifest_check.json](owner_manifest_check.json) сверяет manifest нового узкого scope; общий package review не возобновлялся.

Команда воспроизведения — в [reproduce.md](reproduce.md). `check_counts.json:PASS` означает успешное выполнение проверок и ожидаемых контрпримеров, включая обнаруженный обход, а не вердикт APPROVE. Временный runtime удалён; пакет не содержит зависимостей или копии owner-стенда.

Source/market/observed OD/actual resource/full budget/launch остаются **UNKNOWN** в части, выходящей за исторические scoped passes. Полные MR11/MR12/MR13, основной passport review, новые источники, реальные продажи, operating feasibility и выбор команды — **NOT_RUN / OUTSIDE_SCOPE**. Owner folders, public report, Site и dashboard не менялись. Пакет один; дальнейший цикл этим review не запущен.
