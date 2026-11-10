# Воспроизведение review

Из корня checkout, Python 3 standard library, без новых зависимостей:

```sh
python3 context/23_night_run_20261110/screening_review/freeze_snapshot.py
python3 context/23_night_run_20261110/screening_review/independent_check.py
python3 context/23_night_run_20261110/screening_review/check_restriction_lineage.py
```

`freeze_snapshot.py` получает 104 файла через `git show 82dffa795146ccc575db1bb45ba9391af44def00:path` в игнорируемую локальную `.frozen/`. Авторская папка не читается как текущий вход и не изменяется. `independent_check.py` не импортирует авторский код. Для точного offline replay нужны Git objects исходных SHA, перечисленных в `verified_source_manifest.json`; не меняйте их на новые головы веток.

`check_restriction_lineage.py` читает 6,1 МБ сохранённого публичного корпуса непосредственно из исходного Git object, не экспортирует полный корпус. Он проверяет только BAX/KUF и две sample-публикации, не является общим raw-to-derived pipeline.

Необязательная отдельная актуализация четырёх первичных страниц (сеть, создаёт новый набор receipts):

```sh
python3 context/23_night_run_20261110/screening_review/fetch_primary.py
```

Полный публичный HTML сохраняется только в игнорируемом `raw_public/`; в Git передаются hashes и небольшие extracts. Повторная загрузка может изменить HTML-хеш из-за динамического содержимого. Старые receipts в опубликованном review остаются доказательством конкретного доступа.

Check scope: AUTHOR_REPLAY_MATCHED для указанных производных scores, JOIN/HASH для байтовых проекций, SOURCE_SUPPORTED только для явно ограниченных строк пяти source checks. Не выдавать эти статусы за принятую экономику, измеренный OD или live E2E.
