# Пакет сетевой модели

Начните с [report.md](report.md). Независимая проверка **PENDING**. Исходные author outputs, исправления и proposed adapter раздельны. Общий лимит D обязателен; Q при суммарной частоте — **AGENT_PROPOSAL**, не единственное объективное исправление. Реальные исходные повторы не превышают весь D.

| Файл / папка | Содержание |
|---|---|
| `frozen_exports/`, `author/` | Неизменённые экспорты и минимальные исходники Анастасии @2f03 |
| `author_export_comparison.csv` | 128/12/64 строк, 0 differing cells; различия байтов объяснены |
| `corrected_model.py` | Исполняемые общие D/seat caps, варианты capture и allocation, marginal selection |
| `outputs/AUTHOR_REPLAY/` | Полный replay автора |
| `outputs/CORRECTED_*/` | Предложенный Q(F), фиксированный и повторно отобранный состав |
| `market_bound_only_summary.csv` | Только общий D cap: текущий baseline без денежного изменения |
| `before_after.csv`, `shared_pair_example.json` | Точные, неокруглённые delta и MOW–OMS |
| `common_market_bounds.csv` | Различие entire-D и сценарного pooled-capture ограничения |
| `ledgers/` | Принятые поездки, incidence, агрегированные места и деньги |
| `ciri/` | Цири @93fa: отдельный replay, исходные/новые metadata block, датированный календарь |
| `proposed_common_view/`, `field_mapping.csv` | Mapping; общий экономический прогон не выполнен |
| `checks.json`, `counterexamples.csv` | Реальные строки и контрпримеры; original defect отвергается |
| `findings.json`, `decision_ledger.json` | Ошибка, выбор метода и ограничения раздельно |
| `source_manifest.json`, `provenance.json`, `artifact_manifest.json` | SHA, авторство, grain, reproducibility |

Полный повтор уже поставленного пакета без сети, из корня checkout (использованы существующие Python 3.11.9, numpy 2.4.3, pandas 2.3.3; установки не нужны):

```sh
python3 context/23_night_run_20261110/model_repair/prepare.py
python3 context/23_night_run_20261110/model_repair/replay.py
python3 context/23_night_run_20261110/model_repair/ciri_replay.py
python3 context/23_night_run_20261110/model_repair/methods_extension.py
python3 context/23_night_run_20261110/model_repair/build_adapter.py
python3 context/23_night_run_20261110/model_repair/check.py
python3 context/23_night_run_20261110/model_repair/finalize_package.py
```

Для проверки уже замороженного пакета достаточно последних двух команд: они читают результаты и не повторяют финансовый replay. Проверку data mapping включает `check.py`; finalize только добавляет provenance/metadata и считает хеши.

Опциональное восстановление полного raw по закреплённому публичному URL: `python3 context/23_night_run_20261110/model_repair/prepare.py --restore-public`. Оно требует сети, сверяет raw SHA и не повышает версию входов. Для обычного offline повтора оно не нужно: проекция уже в Git. Полный raw, зависимости и кеши в пакет не включаются.

`AUTHOR_REPLAY_MATCHED` здесь означает совпадение перечисленных CSV. `CONSERVATION_PASS` Анастасии — только недатированные агрегаты. У Цири проверен сценарный календарь. Эти уровни не означают observed OD, реальные продажи, dispatch clearance, прибыль или разрешение запуска.
