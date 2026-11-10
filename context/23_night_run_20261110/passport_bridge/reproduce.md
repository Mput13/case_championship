# Воспроизведение пакета

Работать из корня этого repository с имеющимся Python 3 standard library. Новые зависимости, серверы, браузеры и расчётные модели не нужны.

```sh
python3 -B context/23_night_run_20261110/passport_bridge/build_package.py
python3 -B context/23_night_run_20261110/passport_bridge/finalize.py
python3 -B context/23_night_run_20261110/passport_bridge/verify_package.py --write-checks
python3 -B context/23_night_run_20261110/passport_bridge/finalize.py
python3 -B context/23_night_run_20261110/passport_bridge/verify_package.py
git diff --check
```

`build_package.py` читает источники исключительно `git show <full SHA>:<path>` через `read_sources.py`; список pins задан в коде и `input_pins.json`. Он собирает CSV, requirement paraphrases и реестры. Это перенос/синтез результатов, **не новый экономический расчёт**. `finalize.py` формирует Markdown тезисов из CSV, manifests и handoff. Содержательные Markdown находок, плана и приложения являются редакционными артефактами. Timestamp повторной сборки может отличаться; формулировки/перенесённые числа и входные blobs сохраняются. Все writes скриптов ограничены своей папкой.

Первый finalize нужен для проверки всех итоговых файлов/ссылок; после записи `checks.json` второй finalize включает его и итоговый статус в manifest/handoff. Последняя проверка read-only сверяет также весь output manifest.

Для чтения конкретного immutable доказательства, например:

```sh
git show 6a038b9bcd2d5476e931885e68fe3b17ef121d5e:context/23_night_run_20261110/screening_review/report.md
git show 944b16ac2dcde846e29dac2d47e11e5143f9fc2b:context/23_night_run_20261110/source_join_review/report.md
git show d8634187d452343a369f7cec63be50511bb70020:context/23_night_run_20261110/cost_kover_review/findings.json
```

В этом запуске официальная страница `https://mai-way.ru/tasks/red-wings/` проверена отдельным текстовым GET. Нативный web open вернул точную ошибку `URL https://mai-way.ru/tasks/red-wings/ is not accessible via this tool.` Обычный HTTPS GET дал 200 и SHA256 `3fd55465168339d63835e063eee1c188ca19e8c9feb728694b7cd5c63d7242d9` — тот же, что в pinned исторической receipt E32. Сохранены URL, время, размер, hash и краткие requirement paraphrases; полный HTML/текст не включён. Дети для диагностики не создавались по прямому запрету пользователя. Сбой fetch не был основанием вмешиваться в UI/инфраструктуру.

Обычная воспроизводимость пакета **offline** использует сохранённую receipt и exact Git objects. Повторный HTTP запрос может дать новую версию: такой результат требует новой receipt/input set и не подменяет текущий срез. Ссылки на первичные страницы в competitor CSV — сохранённые указатели; массовая live-проверка их доступности не проводилась. `verify_package.py` проверяет синтаксис URL и точные Git locators, а не текущую доступность всех сайтов.

Проверка не исполняет foreign scripts, replay моделей или upstream review. Она сверяет IDs, допустимые группы, перенесённые числа/карточки/веса, наличие явно удержанных состояний, manifests и область diff. Это meaningful package check, а не доказательство рыночной/финансовой истины.

Публикация производится только для своей ветки и своей папки, без force/merge/rebase/PR. Чтобы проверить конечную remote версию после push:

```sh
git rev-parse HEAD
git ls-remote --heads origin refs/heads/research/night-passport-bridge-20261110
git diff --name-only 77343ca9dccc14d60c51d4559485646219ecd1cd HEAD
```

SHA payload и конечная remote equality проверяются отдельной delivery receipt и финальным сообщением. Невозможно вписать SHA содержащего себя коммита в тот же хешируемый файл; это не заменяется выдуманным self-SHA.
