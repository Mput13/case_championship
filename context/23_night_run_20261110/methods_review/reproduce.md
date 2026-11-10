# Воспроизведение MR05

Из корня checkout, Python3 со стандартной библиотекой. Нужны доступные локально Git objects перечисленных SHA; сеть, установка зависимостей и live methods folder не нужны.

```sh
python3 context/23_night_run_20261110/methods_review/independent_review.py
python3 context/23_night_run_20261110/methods_review/probe_pinned_validator.py
python3 context/23_night_run_20261110/methods_review/check_review_package.py
```

Первый код заново вычисляет результаты из `git show 344f4425ba3fbb73b45a5cbcd223089e2ca7b5d4:path`, проверяет81 output hashes и62 upstream blob identities. Он не импортирует и не исполняет код авторских моделей. Выходы пишутся только рядом с этим файлом. Контракт и brief имеют отдельный контрольный SHA f39ac0726d5942106189e9dc59bfc09cad92441e.

Второй код отдельно исполняет AST-функцию main закреплённого `analyze_pinned.py`, сохраняет все его outputs только в памяти и подставляет явно изменённый CSV-reader. Main внутри себя исполняет три чистые авторские функции `capture/leg_share/fare`; этот probe отделён от независимого пересчёта первого скрипта. Сравниваются исходный case и два coverage probes. Исходные файлы, хеши и original не перезаписываются. Это демонстрация границ семантических проверок после byte-integrity layer, а не обход старого manifest для изменённого файла. Полный author pipeline не запускается.

Последняя команда только проверяет готовый пакет, включая точные file:line всех findings. Manifest обновляется **только при намеренном изменении review-пакета**:

```sh
python3 context/23_night_run_20261110/methods_review/check_review_package.py --write-manifest
```

Для публикации проверяется исключительно собственный scope:

```sh
git diff --check
git status --short
git diff --cached --name-only
git push origin HEAD:refs/heads/research/night-methods-review-20261110
git rev-parse HEAD
git ls-remote --heads origin refs/heads/research/night-methods-review-20261110
```

Commit допускается после проверки staged file list. Все staged пути должны начинаться с `context/23_night_run_20261110/methods_review/`. Совпадение двух SHA подтверждает публикацию; оно не меняет review verdict и acceptance scope.
