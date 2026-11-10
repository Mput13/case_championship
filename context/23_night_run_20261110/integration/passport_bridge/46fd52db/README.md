# Материалы для паспорта Red Wings

Пакет связывает требования организаторов с уже полученными результатами. Это исследовательская основа для паспорта, а не выбранная стратегия и не новый расчёт сети. Входы ограничены точными SHA из brief на `77343ca9dccc14d60c51d4559485646219ecd1cd`; более поздние ветки и результаты сюда не подмешивались.

Начать с [выводов](findings.md), затем открыть [матрицу требований](requirements_evidence.csv) и [готовые формулировки](passport_claims.md). [Конкуренты и Екатеринбург](competitor_and_svx_gaps.csv) содержат конкретные примеры, [развилки](decision_options.csv) — вопросы для решения команды, [план](next_day_plan.md) — проверяемые выходы до сдачи. [Приложение об ИИ](agent_method_appendix.md) объясняет фактический процесс и его ограничения.

Каждый тезис имеет claim ID, evidence IDs и область приёмки. Полные immutable ссылки, SHA256, grain и локаторы приведены в [evidence_index.csv](evidence_index.csv); [source_manifest.json](source_manifest.json) и [personal_readings.json](personal_readings.json) перечисляют лично полученные Git blobs. Чтение чужого review здесь не означает его повторное выполнение. [author_weights.csv](author_weights.csv) сохраняет исходные веса, [screening_variants.md](screening_variants.md) — авторские тройки и отдельную чувствительность, без утверждения нового профиля.

В [official_case_receipt.json](official_case_receipt.json) записана разрешённая текстовая проверка страницы кейса. Её raw hash совпал с исторической receipt на exact `f1774e1f…`; полный HTML и полный текст страницы не публикуются. [official_requirements.json](official_requirements.json) содержит краткую проверенную переформулировку требований с номерами разделов. Локальные PDF, DOCX, DOM и moving context22 не читались как новые источники.

Проверка пакета: `python3 -B context/23_night_run_20261110/passport_bridge/verify_package.py`. Рецепт и границы — в [reproduce.md](reproduce.md). Отдельной независимой приёмки этого синтеза не было: статус `SELF_CHECKED_SYNTHESIS; INDEPENDENT_REVIEW_NOT_RUN`. Push не меняет его приёмку.
