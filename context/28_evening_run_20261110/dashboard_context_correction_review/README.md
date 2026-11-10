# Воспроизведение review ROOT-DASH-01

Вердикт: **APPROVE_SCOPED**, только коррекция P2 ROOT-DASH-01 в `0f07ec43ad3cf515e3bafbb767ade9caa2ba984c`. Исходная сборка `5101302f93c349268f4ba0ff26832ff261e1a9e7` и её CHANGES сохраняются.

Из корня репозитория:

```sh
python3 -B context/28_evening_run_20261110/dashboard_context_correction_review/verify.py
```

Команда читает только точные Git objects и frozen файлы коррекции, повторяет независимую реконструкцию и отдельно помеченные owner replays, затем сравнивает сохранённые результаты ревью. Зависимости не нужны; используется Python standard library. Записи по умолчанию нет. Опция `--record` пересоздаёт только JSON-доказательства внутри этого каталога.

- `report.md`, `findings.json`, `handoff.json` — вердикт, P2 disposition, предмет и границы передачи.
- `checks.json`, `counterexamples.json` — результаты и конкретные отрицательные примеры.
- `card_invariants.json` — все 10 наборов метрик и единственное изменённое поле C33.
- `evidence_row_checks.json`, `programme_row_checks.json` — 34 evidence и 16 programme source locators.
- `numeric_alias_cells.json` — 129 сохранённых численных leaf-значений aliases.
- `retained_original_blobs.json`, `scope_checks.json` — сохранность 71 исходного файла и отсутствие UI-правок в root commit.
- `source_manifest.json` — 22 exact Git inputs, собственные SHA256/размер/Git blob.
- `output_manifest.json` — SHA256 и размеры всех файлов этого review-пакета, кроме самого manifest.

Для подключения потребителю нужны `cards.json` и `route_context.json` **из коррекции**, остальные файлы — из `integration/dashboard_handoff/5101302f/`, как указано в README владельца. Aliases являются повторными ссылками на существующие свидетельства. UI Насти не изменён и здесь не проверялся.

Новых задач после этого пакета не запускалось. Точный pushed SHA указан в финальном сообщении; предмет review всегда закреплён отдельным `root_commit` в handoff.
