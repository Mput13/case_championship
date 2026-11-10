# MR14: допуск закреплённых входов и квалификации тезисов

Новый независимый Sol 6.1 xhigh. Subject **7e65c687e12cf45534852a3c47d6a5c8cf7dda07**, `context/23_night_run_20261110/methods/`. Входы только exact git show. Все writes только `context/23_night_run_20261110/input_admission_review/`; ветка `research/night-input-admission-review-20261110`. Срез до08:30МСК, общий предел10:00МСК10Nov. Один bounded review, без детей.

## Проверка нового кода

Лично прочитать admit_frozen_interaction.py, qualify_passport_methods.py, update_acceptance_v8.py и их receipts/outputs. Проверить ровно новую логику и семантику, а не повторять MR11/MR12/MR13 или основной паспортный review.

- Четыре входных файла должны быть побайтно равны exactf7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9. Проверить384 полных уникальных itinerary-ключа,12 unit summary groups, context/source-profile/network/scenario/recipe/period, joins со всеми flight/capacity IDs, один тариф, местные/трансферные расходования кресел и направленные D. Проверить, что семантика периода/времени не возвращает double-day дефект.
- Независимый oracle ровно160affectedrows из MR11 **ea2a9626aef75c121f2da7d778b47edce0d571b7**: ключи, quantities/fare/affected-count, SHA/receipt/commit, допустимые ограничения доверия. Не считать совпадение самой с собой независимой проверкой. Guard только для данных exactinputs; oldmain неизменён, новые данные автоматически не принимаются.
- Воспроизвести семь owner mutations и добавить собственные негативные примеры на значимые реальные ветви: duplicate/missing key, wrong context/endpoint, reversed OD or inconsistent D, capacity conflict, corrupted oracle/receipt. Разделить path through byte pin и прямой validator API. Не объявлять незаявленную универсальность дефектом exact-input guard; если обнаружен реальный обход заявленного admission, дать конкретный repro и минимальную правку.
- Убедиться, что output receipts не объявляют guard реализацией change admission для будущих источников. Не изменять старые результаты, не выполнять сетевые/платные запросы.

## Проекция паспортных квалификаций

Сверить26original requirements/33original claims с exactpassport **46fd52db073cffc46a598f44489d0761c6853410**,16method-addenda и новую qualification projection. Проверить сохранность original strings/исторических PENDING, явные source/review subjects, разные namespace passport_claim_id и frontier hypotheses. S03 насыщение не недостаток спроса; числа/local-first сохраняются, наLP не переносятся. City links кейса не автоматически physical airport pairs/operating acceptance.

Проверить перенос MR11/MR12/admission_v4 по exactsubjects и сохранение oldCHANGES/12clockholds/4delayHOLD; новые v8 функции не наследуют их pass. MR12-O01 — ровно две prose замены1786,197→1786,193 и542,443→542,444, численные CSV unchanged. Проверить398prior inputs/runs/analysis byte preservation и8newoutput deterministic в необходимом узком scope.

## Передача

report.md/findings.json (APPROVE_SCOPED/CHANGES, точные строки/minimalfix), independent checks/контрпримеры, source/output manifests, reproduce commands и handoff.json. Разделить personally run/доверенные upstream проверки. Source/market/actualresource/fullbudget/launch остаются UNKNOWN. Основной passport review идёт отдельно на46fd; MR13 был наc6ad. Их scope не расширять.

Не менять owners, Site/publicreport/dashboard, не создавать детей/треды/расписания, не поллить задачи, не писать коллегам, не менять провайдер/инфраструктуру, без платных источников. Commit/push своей папки без force/merge/rebase/PR, exactHEAD=remote. После пакета закончить без нового цикла.
