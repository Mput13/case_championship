# Контракт проекции P09 для P15

Версия: `P15-import-v3-root20-Q-P09-UI01`. Решение root Q-P09-UI01 принято; P12 pin `06207b1650bd1c83e0f0761b25d063f2c395ace7` и исходный контракт сохранены в `inputs/P12/ui_contract.json`.

Контракт P09 с SHA256 `d721896cdc4193b9e2a70bd54a25baaedd00db0e967a711c5a359d424b0c1e7d` сохраняет P12 JSONpaths. Проверены canonical hash и null на непринятом producer образце; это не quantitative acceptance. Pending index содержит 9 пакетов по две оценки. В финансовые селекторы они не подключены.

Root передаёт точный artifact commit/path envelope с `dataset_kind=RED_WINGS`, `synthetic=false`, `coordinator_acceptance=ACCEPTED_FOR_UI`, producer `commit`, `manifest_sha256`, `evaluations`. Envelope может содержать несколько принятых программ: это список оценок, их деньги не складываются. Для каждой оценки уже имеющихся `source_full_result_sha256`, `source_full_result_path`, `projection_sha256`, `audit_receipt`, `source_refs`, `result_mode` достаточно. Адаптер читает contract и receipt из того же Git commit, проверяет SHA256 canonical result и full links, копирует receipt.input_manifest/full и contract.audit_script/replay в display metadata. Повторные input_pins/audit/replay поля не требуются от производителя. Полный gzip для финалистов/основных выводов остаётся отдельным артефактом; старый sealed early не меняется.

Числа, null, статусы, единицы, периоды, индексы массивов и evaluation links копируются точно. Крупные allocation/events остаются вне UI. Числа overview не используются. `known_operating_subtotal` не заменяет `operating_result`; полная прибыль/финансирование/доля UNKNOWN остаются UNKNOWN. Спрос SCENARIO_NOT_IDENTIFIED отображается как условие. Денежных/choice агрегатов в JS нет. Сетевые изменения и ротации —16строк на страницу, полный массив сохраняется.

Контекст P06-1.0 сохраняет programme/version/fleet/external/delivery/response/mode, market/choice/cost versions, дату и information set, affected scope, price_year/cash_start, KEEP и24месяца. KEEP имеет тот же ресурс, внешний сценарий, поставки, ответ конкурентов и горизонт. Конечные поездки, физические сегменты и отчётная метрика различаются. Годовые и24месячные итоги приходят готовыми от производителя.

Открыто: exact accepted quantitative root envelope/pin/manifest, список допущенных программ/сценариев/compared groups, P10 reported metric bridge/F07, принятый preset финалиста и P16 actual120s rehearsal. Текущий Stage A root20 pin сам по себе не разрешает quantitative binding.
