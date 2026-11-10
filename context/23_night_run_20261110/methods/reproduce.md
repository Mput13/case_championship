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
