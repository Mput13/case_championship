# P09: сравнение программ 2027–2028

Законченный пакет условного вычислительного сравнения; независимая приёмка, рыночная калибровка и полная экономика остаются открытыми.

- `choice_report.md` — результат выбора конструкций, before/after, ресурс, спрос, конкуренты и ограничения.
- `economics_report.md` — известные компоненты, полный результат как функция, пороги и финансирование.
- `programmes.json`, `programme_cards.json`, `candidate_dispositions.csv` — рассчитанные конструкции и отдельные исходы авторских рецептов.
- `scenario_results.csv`, `results_monthly.csv`, `thresholds.csv` — обзор основной матрицы; `canonical_summary.csv` — точные поля канонических финалистов.
- `dated_flights.csv`, `assignments.csv`, `fleet_calendar.json`, `resource_monthly.csv` — 24-месячные календари финалистов во всех ресурсных ветвях.
- `ui_resource_monthly.json` — подготовленные месячные сценарные числа переданных/введённых/резервных бортов; фактическая project_available остаётся null.
- `existing_ssj/` — отдельное применение действующего SSJ100 без новых самолётов; `international/` — международные opportunity thresholds с 0 новых Ту214.
- `ui/index.json`, `projection_contract.json`, `data_contract.json` — P12/P15 интерфейс. ACCEPTANCE PENDING; исходные fullcompare в `ui_results/*.canonical.json.gz`.
- `common_input_template.json`, `evaluation_input_manifests.jsonl`, `root_pin_promotion.json`, `input_pins.json`, `sources.csv` — pins, hashes и происхождение.
- `roadmap.json`, `handoff.json`, `validation.json`, `manifest.json` — действия, проверки и границы передачи.

## Воспроизведение

Из каталога P09, Python3 без сторонних зависимостей:

```sh
python3 replay.py --programme VOG_RADIAL --mode overview
python3 replay.py --programme VOG_RADIAL --mode canonical
python3 replay.py --programme SSJ_VOG_RADIAL --delivery none --existing-ssj --mode overview
python3 validate_package.py
```

По умолчанию replay сохраняет только proof, собственную временную копию удаляет после проверки SHA. `--save` оставляет копию в `replay_runs/`. Проверяются закреплённые subject bytes, движущиеся P05/P06 не читаются. Режим canonical доступен для сохранённых канонических контролей; остальные вычисляются overview и имеют детерминированный input manifest. Не запускайте capture/construct как команду проверки опубликованного пакета: они создают новую версию каталога, тогда требуется отдельный release и impact assessment.

`early/` неизменён. Известная ошибка раннего общего ferry generator исправлена в основном builder; двухдневный early control остаётся историческим результатом своей версии. Более поздняя basename-collision при копировании P01 обнаружена сравнением exact Git bytes и исправлена до численного использования; `capture_corrections.json` сохраняет историю. P01 не изменял спрос P05.

Все программы альтернативные. Сценарные значения не доверительные интервалы. CSV использует UNKNOWN для null только как формат экспорта; UI JSON сохраняет настоящий null и точные числа. P06 PASS исполнения не равен market/dispatch/finance acceptance.
