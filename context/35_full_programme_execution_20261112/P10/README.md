# P10. Рост пассажирского бизнеса Red Wings

Версия `P10-1.0-20261112`. Завершён исследовательский Stage A. Это пакет масштаба, определений, ресурсных условий и постановки совместного расчёта. Он не является принятым прогнозом спроса, полной экономикой Red Wings или подтверждением №2. Итоговые P09/P11 значения, cash KEEP и будущая дельта доли остаются UNKNOWN.

- [report.md](report.md) — основной разбор всего пассажирского бизнеса, ресурсов, конкуренции и финансирования.
- [handoff.md](handoff.md) и [handoff.json](handoff.json) — передача координатору и Stage B.
- [growth_cases.csv](growth_cases.csv) — 128 условных сочетаний; actual поля пусты по правилу UNKNOWN.
- [competitor_scale.csv](competitor_scale.csv), [threshold_scenarios.csv](threshold_scenarios.csv), [competitor_trajectories.csv](competitor_trajectories.csv) — исторические отдельные АК, группы отдельно, растущий порог.
- [metric_dictionary.csv](metric_dictionary.csv), [metric_bridge_examples.csv](metric_bridge_examples.csv) — рейс, этап, поездка и отчётный пассажир.
- [type_productivity.csv](type_productivity.csv), [resource_calendar_monthly.csv](resource_calendar_monthly.csv), [required_resources_by_type.csv](required_resources_by_type.csv), [resource_frontier.csv](resource_frontier.csv) — ёмкость по отдельным типам, даты ввода, варианты ресурса.
- [aircraft_constraints.csv](aircraft_constraints.csv) — exact строки P03 по вариантам, креслам, рекламной дальности и неизвестным полям топлива/ТО/нагрузки; source row IDs и hashes сохранены.
- [growth_bridge.json](growth_bridge.json) — версионная связь P09/P11/P06 и исключение двойного счёта; месячные ожидающие поля — [growth_bridge_monthly_pending.csv](growth_bridge_monthly_pending.csv).
- [funding_exposure_drivers.csv](funding_exposure_drivers.csv), [financing_thresholds.json](financing_thresholds.json) — драйверы и пороги денег без выдуманных ставок или бюджета.
- [roadmap.csv](roadmap.csv), [dependency_requests.csv](dependency_requests.csv), [growth_hypothesis_outcomes.csv](growth_hypothesis_outcomes.csv) — сигналы, действия и оставшиеся проверки.
- [assumptions_register.csv](assumptions_register.csv), [lineage_and_assumption_changes.csv](lineage_and_assumption_changes.csv) — авторство условий, неизвестные диапазоны и отличие от прежних версий.
- [sources.csv](sources.csv), [source_claims.csv](source_claims.csv), [source_coverage.csv](source_coverage.csv), `fetch_receipts*.json`, `sources/` — URL, организация, дата, период, единица, гранулярность, статус, coverage, исходные строки и хеши. Failed/indexed/republication не смешаны с успешно скачанными первичными страницами.
- [input_manifest.json](input_manifest.json) — exact Git SHA/blob/SHA256; [output_manifest.json](output_manifest.json) — полный конечный список файлов для коммита координатором.
- [scale_chart.html](scale_chart.html) — отдельная иллюстрация масштаба; дашборд команды не менялся.

В CSV пустое **числовое** actual-поле означает UNKNOWN, не ноль. В JSON используется `null`. Явный ноль новых самолётов — заданная ветвь; он не обнуляет текущий бизнес. Числа сценариев и условия производительности не являются доверительными интервалами. Поля `conditional_*` действуют лишь при описанных условиях; они не допущены вместо реальных результатов P09/P06.

Воспроизведение по сохранённым данным без сети, без зависимостей и без Git-изменений:

```bash
python3 context/35_full_programme_execution_20261112/P10/build_package.py
python3 context/35_full_programme_execution_20261112/P10/write_supporting.py
python3 context/35_full_programme_execution_20261112/P10/polish_tables.py
python3 context/35_full_programme_execution_20261112/P10/verify_package.py
python3 context/35_full_programme_execution_20261112/P10/seal_package.py
```

`collect_sources.py` — отдельный сбор нового среза с сетью, он не нужен для воспроизведения. Его повтор меняет evidence snapshot и требует новой версии/приёмки, а не молчаливого обновления frozen входов.

Авторская проверка: **41/41 PASS**, подробности — [verification.json](verification.json). Это проверки данных, exactpins и арифметических тождеств. Независимая проверка, реальная годовая модель P09/P06, операционная готовность, digital causal acceptance и полный cash **не выполнены этим пакетом**.
