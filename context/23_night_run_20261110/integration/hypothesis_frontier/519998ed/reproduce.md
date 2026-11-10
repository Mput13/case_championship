# Воспроизведение

Рабочая папка: `context/23_night_run_20261110/hypothesis_frontier/`. Prepared base `f1774e1f66a9483fb618ca6003abd9dc4d8563e1`. Python3 standard library; сеть и новые зависимости не нужны. Авторский код коллег не импортируется и не исполняется.

Читать итог без перегенерации:

```sh
python3 -B context/23_night_run_20261110/hypothesis_frontier/verify_package.py
```

Повторить вычисления из сохранённых pinned inputs:

```sh
python3 -B context/23_night_run_20261110/hypothesis_frontier/build_inventory.py
python3 -B context/23_night_run_20261110/hypothesis_frontier/run_experiments.py
python3 -B context/23_night_run_20261110/hypothesis_frontier/self_check.py
python3 -B context/23_night_run_20261110/hypothesis_frontier/verify_package.py
```

Self-check дополнительно повторно читает56 exact Git blobs и сравнивает сохранённые байты; соответствующие Git objects должны быть доступны. `freeze_inputs.py` может заново извлечь их через `git show exactSHA:path` в ту же собственную `inputs/`. Ни одна moving branch в расчёт не читается. Копии входов — normalized tables/документы, не полный raw архив, не окружение и не auth.

`run_experiments.py` перегенерирует только собственные результаты; `self_check.py` повторяет их и сверяет побайтово. Код коллег, frozen originals, main report и Site не меняются. После изменения собственного кода/input manifest/контракта меняется run_id; это новый вычислительный результат, не молчаливая подмена исходного SHA. Сценарные точки зафиксированы в `test_contract.json` до первого расчёта. Исправление совместной верхней границы x в CSV и снятие недоказанного physical-seat claim C14 отражены в `change_log.md`; сохранённые новые значения повторены minute-grid oracle.

Для нового выпуска после содержательных правок: повторить self-check и **осознанно** пересобрать `seal_package.py`; он задаёт новую дату готовности и output manifest. После08:00 исходный finished package не перезапечатывать как якобы ранний: timestamp обязан оставаться честным. Обычное read-only review делает только `verify_package.py`; `seal_package.py` не нужен для приёмки и не является независимым review.

Проверка scope и точного опубликованного ref:

```sh
git diff --name-only f1774e1f66a9483fb618ca6003abd9dc4d8563e1 HEAD
git rev-parse HEAD
git ls-remote --heads origin research/night-hypothesis-frontier-20261110
```

Commit/push разрешены только для собственной папки в `research/night-hypothesis-frontier-20261110`, без force/merge/rebase/PR. Exact remote SHA передаётся после совпадения `HEAD` и `ls-remote`; SHA коммита, содержащего handoff, невозможно включить в сам этот handoff без циклической зависимости. Push не повышает acceptance.

36 PASS — собственные проверки, включая полный minute-grid C01 (9×47236 пар x/y), непрерывность всех модельных плеч, точные граничные минуты C07, даты/дедупликацию C14, один fare/каждое leg-seat, четыре mutation counterexamples и deterministic replay. Реальные продажи, source/market/operating acceptance и независимый review **PENDING / NOT_ESTABLISHED**.
