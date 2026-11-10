# Повторение расчётов

Из корня этой ветки, Python 3.11+, стандартная библиотека. Установка зависимостей, сеть и чужой checkout не нужны.

```sh
python3 context/23_night_run_20261110/methods/analyze_pinned.py
python3 context/23_night_run_20261110/methods/budget_thresholds.py
python3 context/23_night_run_20261110/methods/render_budget_chart.py
python3 context/23_night_run_20261110/methods/check_package.py
```

`freeze_inputs.py` — recipe первичной фиксации exact Git SHA; повторять для проверки не требуется. Он никогда не читает moving refs. Сохранённые `inputs/set001` не изменяются; несоответствие байтов останавливает capture. Новые пакеты поступают отдельным set.

`analyze_pinned.py` исполняет только три pure-функции `capture`, `leg_share`, `fare`, извлечённые AST из закреплённого авторского файла. Остальные проверки независимо пересчитывают экспортированные quantities, itinerary incidence, capacity, OD budget и money ledger. Он не вызывает author main/update, не загружает raw, не оптимизирует всю сеть. Округление annual CSV учитывается отдельно.

Артефакты: `analysis/set001/shared_pair_examples.csv`, `route_counts.csv`, `nastya_export_balances.csv`, `tsiri_money_reconciliation.csv`, `itinerary_example.json`, `product_threshold_example.json`, `checks.json`. Выходы из одного run не смешиваются с другими профилями.

Бюджетный модуль использует те же frozen source inputs, новый заранее записанный `budget_contract.json` и standard library. `runs/budget_v1/supply_dual_certificates.csv` содержит достаточные неравенства для аналитического верхнего предела; `validation.json` фиксирует scope. `verify_budget_lp.py` — дополнительный повтор той же задачи через уже установленный SciPy 1.17.1/HiGHS, без импорта основного модуля. Для обязательного аналитического повторения SciPy не нужен; новая установка не выполнялась. Эта альтернативная проверка тем же владельцем не названа независимым review.

`receive_input.py` вызывается только для переданного координатором exact SHA и явного списка файлов; receipt каждого нового set хранится рядом с ними. Он не опрашивает moving branches или чужие папки.

### Общий опыт v3

```sh
python3 context/23_night_run_20261110/methods/build_comparison_adapter.py
python3 context/23_night_run_20261110/methods/common_demand.py
python3 context/23_night_run_20261110/methods/common_boundaries.py
python3 context/23_night_run_20261110/methods/render_common_chart.py
python3 context/23_night_run_20261110/methods/check_package.py
```

Стандартная библиотека Python; никаких новых зависимостей, сети или авторских файлов вне inputs не требуется.

### Стратегии v4 и диагностический P2

```sh
python3 context/23_night_run_20261110/methods/portfolio_comparison.py
python3 context/23_night_run_20261110/methods/resource_comparison.py
python3 context/23_night_run_20261110/methods/product_accounting_bridge.py
python3 -B context/23_night_run_20261110/methods/probe_kover_timebase.py
```

Последняя команда импортирует pinned overlay без main и без записи pycache; толькоinstant заменяется в памяти дляконтрпримера. Исходный код и frozeninput не редактируются.

### Интеграция v5

```sh
python3 context/23_night_run_20261110/methods/integrate_kover_accounting.py
python3 context/23_night_run_20261110/methods/kover_demand_interaction.py
python3 context/23_night_run_20261110/methods/portfolio_guard_comparison.py
python3 context/23_night_run_20261110/methods/qualify_review_inputs.py
python3 context/23_night_run_20261110/methods/render_kover_chart.py
```

Текущий portfolio_comparison.py пишет отдельныйportfolio_v1_replay с отсортированнымиtailrows; историческийportfolio_v1 не перезаписывается. `replay_equivalence.json` показывает allvaluesmatch.

## v6

Из корня checkout; SciPy1.17.1 уже установлен, установки не требуются.

```sh
python3 context/23_night_run_20261110/methods/allocation_diagnostic.py
python3 context/23_night_run_20261110/methods/final_variant_synthesis.py
python3 context/23_night_run_20261110/methods/update_acceptance_v6.py
python3 context/23_night_run_20261110/methods/render_allocation_chart.py
python3 context/23_night_run_20261110/methods/check_package.py
```

allocation primary/secondary primal-dual checks выполняются внутри скрипта. Это owner verification, независимый review новогоscopePENDING. Старыеv3/v4/v5runs не перезаписываются.

## v7

```sh
python3 context/23_night_run_20261110/methods/budget_choice_domains.py
python3 context/23_night_run_20261110/methods/final_model_projection.py
python3 context/23_night_run_20261110/methods/update_acceptance_v7.py
python3 context/23_night_run_20261110/methods/render_budget_choice_chart.py
python3 context/23_night_run_20261110/methods/check_package.py
```

Первый скрипт сравнивает inputbytes сexactba9 и проверяет все408 inequalities; inactive candidates имеют direct dominance proof. Это условное сравнение старогоlocal-first, не новый LP allocation или фактическая ценаF/B.

## v8

```sh
python3 context/23_night_run_20261110/methods/admit_frozen_interaction.py
python3 context/23_night_run_20261110/methods/update_acceptance_v8.py
python3 context/23_night_run_20261110/methods/qualify_passport_methods.py
python3 context/23_night_run_20261110/methods/check_package.py
```

Guard запускается отдельным первым шагом перед повторным использованием interaction-ветви. Он допускает толькостарыеexactf7a data; oldinteractionmain не модифицирован исамостоятельно не становитсяуниверсальнымвалидатором. Новыеinputs требуютnewmanifest/key/oracle review. Все7порчвпамяти;CSVне меняются.
