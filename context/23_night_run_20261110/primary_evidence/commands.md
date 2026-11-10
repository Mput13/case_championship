# Воспроизведение

Из корня checkout, существующий Python3 с lxml. Установка зависимостей не нужна. Все записи ограничены папкой пакета.

```sh
python3 context/23_night_run_20261110/primary_evidence/build_package.py
python3 context/23_night_run_20261110/primary_evidence/check_and_summarize.py
python3 context/23_night_run_20261110/primary_evidence/curate.py
python3 context/23_night_run_20261110/primary_evidence/finalize.py
```

`build_package.py` читает точные Git blobs из source_lock, локальные ignored raw и уже закреплённые parent receipts. Повторный запуск не перечитывает меняющийся parent context. `check_and_summarize.py` формирует validation, source identity/конфликты и отмечает HOLD в карточках. `curate.py` воспроизводит краткие исследовательские интерпретации. `finalize.py` проверяет состав, границы и хеширует доставляемый пакет. Это личные проверки исполнителя, не независимое ревью.

Raw намеренно не доставляются через Git. На этом Mac сохранены в `primary_evidence/raw/`; source_registry/http_receipts дают их SHA256. Без raw можно проверить хеши поставляемых артефактов и закреплённых Git blobs, но нельзя объявлять повторное извлечение из первичного HTML выполненным. Отдельно попросить координатора передать нужные допустимые raw через его локальный evidence path либо выполнить новый публичный захват как новый input_set.

Для первоначального ограниченного GET использован `acquire.py` с явным списком source_id. Уже существующие receipts не перезаписываются и повторно не запрашиваются; исторические ошибки остаются. Новая версия публичной страницы требует нового source_id и отдельного input_set, не удаления старого receipt. На каждый ответ установлен лимит2,5МБ. Заголовки, cookies, auth и личные данные не сохраняются. Source URL и точная команда доступны через source_id в acquire.py.

```sh
python3 context/23_night_run_20261110/primary_evidence/acquire.py kuf_mro_favt svx_results_2025
```

Команда выше на существующем локальном evidence возвращает старые receipts, а не делает «актуальную повторную проверку». Это специально защищает frozen входы.

Структура NULL: пустая числовая ячейка = UNKNOWN, а не0. 0 в coverage означает число найденных положительных строк в ограниченных входах, не частоту рынка. Короткие русские периоды KUF/GSV не содержат год; year_basis явно задаёт зимний сезон2026/27. `service_identity.csv` нормализует flight designator и не складывает копии одного опубликованного обслуживания. Часы при CONFLICT_HOLD не использовать для точного join стыковок. Код не подставляет места по типу самолёта и не выводит конечный спрос из частоты/пассажиропотока.

Сборка и push выполняются без PR и без force только в `research/night-primary-evidence-20261110`. Commit SHA берётся из Git после коммита; manifest не содержит рекурсивного самохеша/собственного commit SHA.
