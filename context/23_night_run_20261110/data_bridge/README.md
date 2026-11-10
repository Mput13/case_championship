# Соединение данных и адаптеры

Вход для координатора: `handoff.json`, затем `findings.md`. Пакет пишет только свою папку. Исходники, веса и дашборд Анастасии, исходные опыты и публичный Site не менялись.

## Воспроизведение

Python 3.11+, стандартная библиотека, локальные Git objects закреплённых коммитов. Никаких установок, серверов или новых загрузок. Из корня этого checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 context/23_night_run_20261110/data_bridge/adapters/build.py
PYTHONDONTWRITEBYTECODE=1 python3 context/23_night_run_20261110/data_bridge/adapters/check_raw.py
PYTHONDONTWRITEBYTECODE=1 python3 context/23_night_run_20261110/data_bridge/adapters/package.py
PYTHONDONTWRITEBYTECODE=1 python3 context/23_night_run_20261110/data_bridge/adapters/verify.py
```

`build.py` воспроизводит joins/адаптацию опубликованных выходов и формулу скоринга по сохранённым значениям критериев. Он не исполняет чужие модели и не заявляет полный AUTHOR_REPLAY_MATCHED. `check_raw.py` выборочно читает held raw по путям из родительского `context/16_agent_research/threads.json`, сверяет закреплённые хеши и повторяет указанные извлечения. Raw остаются на месте. На машине без этих raw стадия RAW — недоступна, а не PASS; Git-таблицы и joins воспроизводимы отдельно.

`package.py` оформляет выводы и handoff; `verify.py` отдельно пересчитывает связи и ограничения по готовым нормализованным таблицам, проверяет scoped diff, sanitizer и выпускает `outputs_manifest.json`. Проверка автора пакета не заменяет независимый review координатора.

## Таблицы

- `source_manifest.csv`, `input_manifest.json`: Git SHA, SHA256, автор пакета, последний Git-автор файла, зерно/единицы входа. `primary_source_registry.csv` и `checks/raw_receipts.csv`: исходные издатели, URL, raw и границы лично проверенной выборки.
- `normalized/candidate_register.csv`, `candidate_airport_link.csv`, `product_path_template.csv`: город, маршрутный набор и пассажирский продукт с разными `model_id` и статусами. Авторская петля с возвратом не превращается автоматически в одну продаваемую поездку.
- `route_program.csv`, `line_flow_context.csv`: недатированные годовые агрегаты Анастасии. `itinerary`, `itinerary_leg`, `physical_leg`, `capacity_allocation`, `market_pool`, `money_ledger`, `resource_ledger`, `evaluation_summary`: адаптированные сценарные программы с явными пределами.
- `entity_resolution`, `published_dated_evidence`, `airport_weather_month`, `gateway_region_crosswalk`, `candidate_regional_tourism`: действительные соединения по ключам. `quarantine_preserved` сохраняет frozen-карантин. Таблица источника и held-ключи не получают повышенный допуск от совпадения имени города.
- `coverage.csv`: охват по каждому кандидату и его конечным точкам. `coverage_summary.csv` суммирует количество покрытых объектов, а не пассажиров. Нулевой счёт строк означает отсутствие допустимого совпадения в данном наборе; он не означает нулевой рынок/погоду/туризм.
- `model_input_usage.csv`, `feature_fitness.csv`, `feature_effects.csv`: фактическая вычислительная зависимость, допуск и on/off-чувствительность. `parameter_registry.csv` сохраняет отдельный класс значения и авторские веса.
- `adapters/mapping.csv`, `compatibility.csv`, `units_dictionary.csv`, `field_dictionary.csv`: интерфейс, несовместимость, единицы и правила NULL/класса поля. В CSV пустая бизнес-ячейка — NULL; строковый статус объясняет причину, а не заменяет неизвестное число нулём.
- `findings.csv`, `normalized/decision_ledger.csv`, `requests.csv`: ограничения, авторство решений и адресные потребности. Исторический `historical_findings.csv` — материал critic по его прежним входным SHA, не перечень новых дефектов текущих моделей.

## Правила чтения

Период, направление, `market_unit`, модель, сценарий и граница приёмки входят в смысл значения. Альтернативные сети Цири не складываются: один общий сценарный OD-пул ограничивает каждую взаимно исключающую стратегию. Выручка хранится на itinerary; после join на два плеча её нельзя суммировать дважды. В `money_ledger` account `incremental_revenue` уже равен `gross_revenue − foregone_RW_revenue`; эти три account не суммируют вместе.

Региональный контекст и погода размножаются по отношениям «кандидат использует аэропорт». Это incidence-связь. Для исходных региональных чисел используется уникальный `(canonical_region_id, indicator_code, year)`, для архива станции — `(station_id, month)`. Складывать повторённые значения по кандидатам/продуктам нельзя.

Новая версия источника требует нового `input_set_id` и impact review. Публикация ветки не повышает приёмку до SOURCE_SUPPORTED, фактических продаж, прибыли или разрешения на запуск.
