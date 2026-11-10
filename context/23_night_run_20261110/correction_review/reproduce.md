# Воспроизведение MR10

Из корня repository, Python 3.11+ со стандартной библиотекой и IANA timezone data:

```sh
python3 context/23_night_run_20261110/correction_review/independent_checks.py
python3 context/23_night_run_20261110/correction_review/package_manifest.py
git diff --name-only 47de3dfb3d20c29232396f5a28c664a97630b3d9 -- . ':(exclude)context/23_night_run_20261110/correction_review/**'
```

Первая команда читает только exact Git blobs. Все создаваемые файлы — в папке самого скрипта. Ни один author main или correction build целиком не исполняется. В отдельном bounded replay исполняются определения original overlay, извлечённая `corrected_instant` и вызовы apply/hits; filesystem-read parameters заменены pinned JSON из памяти. Независимый oracle, joins и conservation не используют авторские вычисления.

Ожидание: 83 PASS, 0 FAIL, exit 0. Последняя команда должна вывести пустой список. Нужны все commits из `source_manifest.json`; отсутствующий exact object разрешено получить fetch, но нельзя заменять новым branch head. Данные не скачиваются из внешних сайтов.

Ключевые артефакты: `independent_lineage_join.csv`, `lineage_receipts.json`, `held_clock_mappings.csv`, `independent_timestamps.csv`, `independent_rotation_conflicts.csv`, `independent_conservation.csv`, `bounded_day1_replay.csv`, `no_kover_input_preservation.json`, `counterexamples.json`.

`output_manifest.json` включает все файлы пакета, кроме самого себя. `handoff.json` включён в manifest; hash manifest не записывается обратно в handoff, чтобы избежать self-reference. Canonical delivery identity — Git commit и exact `ls-remote` ветки, приведённые в финальном handoff-сообщении.
