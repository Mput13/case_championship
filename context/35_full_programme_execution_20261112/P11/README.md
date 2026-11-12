# P11: аудит цифровых путей

Начать с [handoff.md](handoff.md). Срез официального сайта — 12.11.2026; исторические наблюдения 10.11 хранятся отдельно. Stage A завершён, реальные операции и A/B не выполнялись. Рост пассажиров, прибыль и cash UNKNOWN.

Основные машинные выходы: `digital_cards.json`, `digital_effects.csv`, `funnel_and_economics.json`, `P09_integration_contract.json`, `assumptions_register.json/csv`, `validation_limits.json`, `handoff.json`. Источники: `source_manifest.json`, `source_claims.json`, `source_rows.csv`, `sources/`. Доказательства: `visual_evidence.json`, `audit_scenarios.json`, `evidence/`. Прежние денежные сценарии — только `historical_threshold_replay.csv`.

Офлайн-проверка: `python3 context/35_full_programme_execution_20261112/P11/validate_package.py`. Она не создаёт бронирований и не обращается к сети. `build_package.py` воспроизводит производные JSON/CSV из сохранённых входов. `capture_inputs.py` выполняет новый сбор и перезаписывает сохранённые источники: не использовать его как проверку frozen пакета; для следующей версии сначала сохранить этот manifest.

Обновление завершённого manifest после осознанной правки: `python3 context/35_full_programme_execution_20261112/P11/validate_package.py --seal`. SHA256 самого manifest сообщается отдельно, manifest не включает себя в список файлов. Внутренний `manifest_body_sha256` вычислен по JSON без этого поля, с `ensure_ascii=False, sort_keys=True, separators=(',',':')`.

Все пути записи ограничены P11. Git mutations не выполнялись. Координатор коммитит завершённый пакет по manifest. Авторский P11 не является независимым APPROVE общей модели.
