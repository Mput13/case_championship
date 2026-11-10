# Воспроизведение проверки

Запуск из корня checkout; Python 3 со стандартной библиотекой. Зависимости, сервер, browser и платные API не нужны. Проверка читает Git objects по полным SHA, не папки владельцев. Все записи идут рядом со скриптами в `passport_review/`.

```sh
python3 -B context/23_night_run_20261110/passport_review/review.py
python3 -B context/23_night_run_20261110/passport_review/compile_review.py
python3 -B context/23_night_run_20261110/passport_review/verify_package.py --write-manifest
python3 -B context/23_night_run_20261110/passport_review/verify_package.py
```

Первый скрипт должен завершиться с `failed: []`; ошибки дают ненулевой exit code. Второй сохраняет явно написанные семантические оценки всех строк, а не выводит их из числа assertion checks. Повторная сборка меняет время handoff; численные результаты остаются теми же. Manifest следует обновлять только после осознанной повторной сборки; обычная проверка его не меняет.

`official_receipt.json` — лично полученный разрешённый text HTTP receipt. Обычный запуск использует сохранённый receipt и не обращается в сеть. Для отдельного явно нужного обновления существует `review.py --capture-official`; это создаёт новый capture и требует повторного impact review, а не молча заменяет frozen источник. Полный HTML/текст не сохраняется и не публикуется. Нативный web-open вернул точную ошибку `URL https://mai-way.ru/tasks/red-wings/ is not accessible via this tool.` Поэтому использован доступный `urllib.request` GET без auth/cookies. Диагностический агент не запускался ввиду прямого запрета детей в brief.

Собственные численные выходы: `independent_screening.csv`, `independent_weights.csv`, `independent_bax_kuf.csv`, `independent_common_cases.csv`, `independent_boundaries.json`, `independent_upper_bounds.csv`, `independent_original_D_pools.csv`, `independent_route_pairs.csv`, `independent_cash.csv`, `independent_concurrency.csv`, `independent_shifted_flight_intervals.csv`, `independent_card_dates.csv`, `independent_rule_calendars.csv`, `independent_coverage.csv`. Формулы и scope каждого семейства указаны в `review.py`, `checks.json` и `report.md`.

`source_manifest.json` хранит exact ref, Git blob, SHA256, размер и grain реально полученных inputs. Он не означает повторной приёмки каждого исходного raw или всех экономических pipelines. Проверки байтов subject и его inputs вынесены в `subject_manifest_verification.json` и `upstream_manifest_verification.json`. `receipt_sample.json` отдельно отмечает отсутствие raw bodies в pinned Git-наборе. Семантические таблицы и addendum различают личные проверки и прочитанные upstream verdicts.

Контроль безопасного изменения и доставка выполняются отдельно:

```sh
git diff --check
git diff --cached --check
git diff --cached --name-only
git push --set-upstream origin research/night-passport-review-20261110
git rev-parse HEAD
git ls-remote --heads origin refs/heads/research/night-passport-review-20261110
```

Push разрешён только для собственной ветки без force, merge, rebase и PR. Последние две команды должны вернуть один полный SHA. Он сообщается в результате доставки, без циклического self-SHA внутри коммита. Содержательная работа заканчивается одним пакетом.
