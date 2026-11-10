# Передача в общий пакет

Основные выходы: `existing_hypotheses.csv`, `candidates.csv`, `candidate_schema.json`, `data_requests.csv`, `methods.md`, `experiments_queue.csv`. Начать с `findings.md`, затем смотреть конкретный ID кандидата/эксперимента. Новая объяснялка не создавалась.

`dataset_manifest.json` — общий индекс с путями относительно hypotheses/. Вложенные manifests сохраняются для исходного происхождения; копии источников не независимые свидетельства. `source_registry.csv` различает фактический источник, документ коллег и reviewer evidence. `normalized/` содержит координаты, геометрию, буквальные правила прилёта KHV и повтор четырёх сценарных порогов. Остальные planned outputs полного оценщика отсутствуют, а не заполнены нулями.

Правила интеграции:

1. `candidate_id + candidate_version` — ключ карточки; `ancestor_ids` соединяется с `existing_hypotheses.id`. Отделять семейство, программу и модуль. Все предложенные цепочки должны получить полный датированный manifest перед оценкой.
2. Географию соединять по идентификаторам аэропортов/версиям, не только municipality. Наш `city_scope.csv` содержит 50 airport anchors; это не 50 проверенных новых баз. Список не заменяет общий лонглист/рейтинг/топ-3 кейса.
3. Хабаровские правила — только таблица прилётов. Сохранить `carrier_code_raw`, не объявлять marketing code operating carrier. Не суммировать её строки как частоту/кресла, пока не разобраны периоды/дни/исключения/кодшер. Факт исполнения UNKNOWN.
4. SAO-карточки и корпоративные/санаторные наблюдения подключать к evidence/локальным модулям. Ни один из них не превращать в observed OD для C01–C35.
5. Новые данные core/alternative принимать по зафиксированному manifest/status; текущие snapshots их progress сохранены как координационные входы. Мы не изменяли их файлы и не объявляли их завершёнными.
6. Аудит front вводит HOLD на загрязнённые Telegram тексты и производные числа; этот HOLD не распространяется автоматически на погоду, координаты, исходные транспортные файлы или корпоративные источники.
7. При изменении evaluator/scenario повторить все затронутые программы. Датированный протокол критика хранится рядом с контрактом. Отсутствие полного расчёта обозначать NOT_EVALUATED, не нулевой вклад.

Raw OurAirports в `raw/external/ourairports_global.csv.gz` исключён из Git: 3,8 MB с сохранёнными хешами сжатых и исходных байтов. Он физически находится в этом worktree; для интеграции перенести именно файл и проверить manifest. Интернет-команда получает новый snapshot и не гарантирует прежний хеш. Полные внешние HTML/text и исходные HTTP receipts также LOCAL_ONLY: лицензия перепубликации не подтверждена, Set-Cookie не публикуются. Их список/размеры/SHA256 — `publication_review.json`; очищенные receipts сохранены отдельно. Коллегиальные Git snapshots включены с атрибуцией. Для offline replay исходный глобальный gzip не нужен: используется зафиксированный `normalized/airports_ru.csv`, но исходник сохранён для аудита фильтра.

Воспроизведение из корня checkout без сети:

```sh
python3 context/16_agent_research/hypotheses/collectors/extend_map.py
python3 context/16_agent_research/hypotheses/collectors/build_candidates.py
python3 context/16_agent_research/hypotheses/collectors/build_schema_and_requests.py
python3 context/16_agent_research/hypotheses/collectors/screen_candidates.py
python3 context/16_agent_research/hypotheses/collectors/prepare_publication.py
python3 context/16_agent_research/hypotheses/collectors/package.py
python3 context/16_agent_research/hypotheses/collectors/validate.py
```

`build_*`/`screen_candidates` меняют только собственные производные. `package.py` создаёт общий индекс. `validate.py` использует установленный jsonschema для полной проверки schema и стандартную библиотеку для хешей/соединений/геометрии. Новые зависимости не устанавливались. Сборщики с HTTP не входят в offline replay: повторный GET создаст новый срез. Перед любой перезагрузкой сохранить старый snapshot.

Для полного offline replay и проверки raw-хешей сначала подключить локальные исходники по `publication_review.json`. Чистый Git checkout содержит извлечения и сборщики, но не является полным архивом raw. Повторный HTTP-сбор не гарантирует исходный временной срез.
