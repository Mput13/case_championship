# Воспроизведение MR08

Из корня prepared checkout, Python 3.11+ и стандартная библиотека. Зависимости, сервер, браузер, сеть для расчёта и live methods не нужны. Все необходимые commits должны присутствовать в локальном object store.

```sh
python3 context/23_night_run_20261110/common_comparison_review/independent_review.py
python3 context/23_night_run_20261110/common_comparison_review/verify_package.py
```

Первая команда читает только `git show exactSHA:path`, создаёт независимые outputs в своём scope и завершается с `PASS`. Вторая заново проверяет output/source hashes, ширину CSV, source HOLD и write scope относительно root base `f1774e1f66a9483fb618ca6003abd9dc4d8563e1`. Она не повышает численную, источниковую или рыночную приёмку.

Основные pins:

- methods — `abb1c76254d2d4e3cf9edd5c345b9cdb224f6abe`;
- source Цири — `93fa5cf4a10ab67e05c93d19fc5375fc58ef9299`;
- source Анастасии — `2f03b693a62c219e9475fcd1e26295039f6a49d7`;
- model_repair — `27740ffea0821aa404ecd1013d1bb141613261f3`;
- data_bridge — `abc09bbb8e62d3513749b60b252d4521997acfc3`;
- primary — `17b4f348f15ea8695688d9435933cb4965568408`;
- source/join review — `944b16ac2dcde846e29dac2d47e11e5143f9fc2b`.

Ни `common_demand.py`, ни `common_boundaries.py`, ни авторские pipeline/check_package не импортируются и не запускаются. Четыре чистые adapter helper functions AST-загружаются отдельно для сравнения поведения mutation probes; независимый allocator, branch certificates и собственный adapter gate написаны в reviewer scope.

`independent_affine_regions.csv` содержит собственные branch-validity intervals. `independent_boundary_sides.csv` хранит численные значения у границ. `independent_rank_intervals.csv` подтверждает знак/ноль разности на всех общих интервалах. `independent_summary.csv` и `independent_unit_itineraries.csv` содержат пересчёт всех доступных общих итогов и unit-scale строк.

После осознанного изменения **собственного** пакета манифест формируется отдельной командой. Обычная проверка его не переписывает:

```sh
python3 context/23_night_run_20261110/common_comparison_review/verify_package.py --refresh-manifest
python3 context/23_night_run_20261110/common_comparison_review/verify_package.py
git diff --check
git status --short
```

`output_manifest.json` не хеширует сам себя. Доставка не помещает self-referential commit SHA внутрь его же tree: handoff после первого push фиксирует exact payload/remote SHA; окончательный handoff-only commit и remote head сообщаются в автоматическом завершении. Проверка remote:

```sh
git ls-remote --heads origin refs/heads/research/night-common-comparison-review-20261110
git log -1 --format=%H -- context/23_night_run_20261110/common_comparison_review/handoff.json
```

Новые входы или live refs автоматически не подставляются. Для проверки иной source derivative нужен новый immutable review scope.
