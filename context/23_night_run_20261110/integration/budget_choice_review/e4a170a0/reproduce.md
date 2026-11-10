# Повторение MR13

Из корня checkout, Python 3 и уже установленный SciPy 1.17.1. Сеть, установка зависимостей и live owner folders не нужны. Exact commit objects из source_manifest должны присутствовать в локальном Git.

Проверка сохранённого пакета:

```sh
python3 context/23_night_run_20261110/budget_choice_review/verify_package.py
```

Независимое повторение и сверка с запечатанными выходами без обновления manifest:

```sh
python3 context/23_night_run_20261110/budget_choice_review/independent_review.py
python3 context/23_night_run_20261110/budget_choice_review/verify_package.py
```

Первый скрипт читает содержательные входы только через `git show <exact SHA>:<path>`. Независимая часть использует стандартную библиотеку и Fraction, без owner imports/LP. Отдельный replay owner-кода использует уже имеющийся SciPy и создаёт только малый `_runtime` внутри review-папки; затем удаляет его в finally. Сохранённый Python/SciPy environment — execution_environment.json. Подмена SciPy может изменить выбранный owner witness и нарушить byte determinism, даже если геометрия не изменится.

`seal_package.py` — однократная сборка manifest перед commit. Для проверки не запускать: verifier не пересоздаёт и не подменяет контрольные хеши.

Не выполнять приведённые в owner reproduce команды в живой methods-папке. Изолированный replay уже встроен в independent_review.py. Эта команда не меняет owners, Site, отчёт или dashboard и не создаёт PR/дочерних агентов/расписаний.
