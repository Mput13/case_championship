# Сырые данные Red Wings

Исследовательский checkpoint. Это данные и диагностические проверки, не утверждённый рейтинг городов или прогноз OD.

`source_registry.csv`, `dataset_manifest.json`, `coverage.csv` описывают источники и фактическое покрытие. `canonical_keys.csv` содержит версии ключей аэропортов, городов и регионов. `diagnostics/independent_checks.json` фиксирует проверенные соединения. `progress.md` сохраняет этапы и фактическое UTC.

В `branches/social_economy/` завершены социальные и экономические таблицы и два примера join. В `branches/operating_evidence/` завершается метаданные расписаний, субсидий и публичных расходов. Полнота источников ограничена; пропуск не равен нулю.

`publication_manifest.json` перечисляет локальные файлы, удержанные от Git, с абсолютными путями и SHA256. Они сохранены в этом worktree. Большие CSV дополнительно сжаты в `normalized/large_exports/`; команды получения и нормализации находятся в `collectors/` и подкаталогах ветвей.

Front Telegram: PARSER_CONTAMINATION/HOLD, полный reparse NOT_RUN. Опубликованный парк не является доступным ресурсом. Метки OBSERVED/DERIVED/MODEL_ESTIMATE/SCENARIO/UNKNOWN и статусы источников имеют разные значения.
