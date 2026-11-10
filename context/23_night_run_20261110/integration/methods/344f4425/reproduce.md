# Повторение расчётов

Из корня этой ветки, Python 3.11+, стандартная библиотека. Установка зависимостей, сеть и чужой checkout не нужны.

```sh
python3 context/23_night_run_20261110/methods/analyze_pinned.py
python3 context/23_night_run_20261110/methods/check_package.py
```

`freeze_inputs.py` — recipe первичной фиксации exact Git SHA; повторять для проверки не требуется. Он никогда не читает moving refs. Сохранённые `inputs/set001` не изменяются; несоответствие байтов останавливает capture. Новые пакеты поступают отдельным set.

`analyze_pinned.py` исполняет только три pure-функции `capture`, `leg_share`, `fare`, извлечённые AST из закреплённого авторского файла. Остальные проверки независимо пересчитывают экспортированные quantities, itinerary incidence, capacity, OD budget и money ledger. Он не вызывает author main/update, не загружает raw, не оптимизирует всю сеть. Округление annual CSV учитывается отдельно.

Артефакты: `analysis/set001/shared_pair_examples.csv`, `route_counts.csv`, `nastya_export_balances.csv`, `tsiri_money_reconciliation.csv`, `itinerary_example.json`, `product_threshold_example.json`, `checks.json`. Выходы из одного run не смешиваются с другими профилями.
