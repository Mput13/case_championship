# Повторение MR14

Из checkout, в котором доступны Git objects закреплённых commits:

```sh
python3 -B context/23_night_run_20261110/input_admission_review/verify.py
```

Python 3, только стандартная библиотека. Все предметные входы — `git show` exact SHA; moving folders и refs не читаются. Создаётся только собственный `.runtime` внутри review scope, удаляемый в `finally`. Перед запуском этот каталог должен отсутствовать. Никакие старые author/model `main` не выполняются. Временные файлы — только необходимые CSV, receipt и четыре Python-модуля; зависимостей и установки нет.

Команда воспроизводит восемь новых owner outputs дважды, сравнивает байты, выполняет собственные negative probes, отдельно испытывает предложенную правку в памяти и записывает evidence JSON. `PASS` отдельных checks означает совпадение с ожиданием эксперимента; подтверждённый receipt bypass сохраняется в `own_probes.json` и итоговом `CHANGES`.

`source_manifest.json` содержит commit/path/SHA256/bytes/grain всех прочитанных Git inputs. `output_manifest.json` содержит SHA256/bytes всех файлов итогового review package, кроме самого manifest. Для проверки передачи:

```sh
git rev-parse HEAD
git ls-remote origin refs/heads/research/night-input-admission-review-20261110
git status --short
```

Совпадение local HEAD и remote SHA проверяется после push; self commit не внедряется в хешируемые файлы. Никакого PR, merge, rebase или force push.
