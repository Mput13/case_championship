# Воспроизведение FRONTIER_REVIEW

Python3 со стандартной библиотекой и системной IANA tzdata; сеть, дополнительные зависимости и авторский код не нужны. Нужны exact Git objects из `source_manifest.json`. Текущая ветка/содержимое moving folders на входы не влияют.

Из корня репозитория:

```sh
python3 -B context/23_night_run_20261110/hypothesis_frontier_review/review.py
python3 -B context/23_night_run_20261110/hypothesis_frontier_review/finalize.py --verify
```

Первая команда перегенерирует только собственные derived CSV/JSON через exact `git show`; exit0 означает, что личные проверки совпали. Повтор не заменяет независимость автора review. Вторая команда read-only сверяет состав, SHA256, байты и число CSV rows с собственным output manifest. Она не повторяет арифметику и не повышает source/market acceptance.

Для намеренно изменённого review-пакета seal выполняется отдельно, после содержательной проверки:

```sh
python3 -B context/23_night_run_20261110/hypothesis_frontier_review/finalize.py
```

Не запускать scripts из reviewed package: их outputs и upstream bytes читаются через exact SHA. Полные raw, caches и окружения не копируются. `table_dictionary.csv` задаёт ключи и единицы каждого derived CSV. В CSV пустое числовое поле означает NULL с причиной из отчёта/claim_scope, не ноль.

Проверка scope и опубликованного ref:

```sh
git diff --name-only 77343ca9dccc14d60c51d4559485646219ecd1cd HEAD
git rev-parse HEAD
git ls-remote --heads origin research/night-hypothesis-frontier-review-20261110
```

HEAD должен совпасть с exact SHA remote branch. Commit, содержащий handoff, нельзя вписать в этот же handoff без циклической зависимости; SHA передаётся в финальном ответе после проверки remote. Push не изменяет scope приёмки. Force, merge, rebase и PR не используются.
