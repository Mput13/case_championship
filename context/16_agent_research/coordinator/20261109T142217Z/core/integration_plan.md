# Интеграция пакета core

Все пути в общих манифестах разрешаются относительно `context/16_agent_research/core/`. Вложенные подробные manifests имеют собственную явную основу. SHA raw payload и сохранённого gzip различаются и хранятся отдельно. Хеш подтверждает байты; статус источника не повышается из-за успешного хеша, commit или push.

## Таблицы и ключи

- `canonical_keys.csv`: 1 845 source IDs OurAirports, 180 опубликованных городских ОКТМО, 343 Travelpayouts travel markets, 85 региональных ключей Rosstat/Tochno и 4 source-supported carrier aliases (WZ/RT/IO/A4). Пространства ID раздельны. Сроки валидности UNKNOWN, если источник их не даёт. Название и близость не являются доказательством административной идентичности. Carrier aliases основаны на подписи/префиксе рейса, не являются полным проверенным юридическим/IATA registry.
- `normalized/airport_version.csv`, `runway_version.csv`: кандидаты географии/физических ограничений. Closed/heliport не отбрасывать молча и не считать пригодными аэродромами; длина в метрах — DERIVED из футов, не технический допуск SSJ.
- `normalized/airport_timezone_join.csv`, `timezone_crosscheck.csv`: перед применением local date→UTC проверить уникальность кодов, coordinate review и timezone status. Конфликтные поля NULL. Ближайший город не назначает пояс автоматически. Не смешивать код города с кодом аэропорта.
- `normalized/city_version.csv`, `city_airport_candidate_links.csv`: переписные городские атрибуты и кандидаты связей ≤75 км по прямой. 255 связей не являются непересекающимися catchments; населения через них не суммировать без отдельного правила распределения.
- `normalized/access_alternative.csv.gz`: направленные пары/виды транспорта, версия рецепта и missing_reason. Все доступные времена MODEL_ESTIMATE; датированных цены/частоты нет. Это отдельный расчётный признак, не наблюдение поездки.
- `branches/social_economy/normalized/`: полные панели и выбранные индикаторы с годом, единицей, редакцией и причинами NULL. ОКТМО разных лет соединять только с историей границ. Не складывать вложенные территории и пересекающиеся варианты регионов. Подробные условия — в branch integration_plan.
- `branches/operating_evidence/normalized/`: schedule_rule, опубликованные даты/частоты, reported board instances, planned subsidy и cost_component. Не превращать endpoint itineraries в nonstop legs, не удваивать зеркальные таблицы, не присваивать строке отсутствующий год. Начать с OMS outbound week как датированного примера. Carrier labels требуют отдельного разрешения operating/marketing relationships.
- `normalized/market_observation.csv`, `svx_market_observation.csv`: опубликованные агрегаты с периодом, точностью и scope. План и бюджет имеют observation_kind, отличающий их от outturn. Доля RW требует общего знаменателя той же величины/географии/периода; годовой поток аэропорта не является OD.

## Воспроизведение без новых запросов

Сначала вернуть удержанные локальные файлы по `publication_manifest.json` либо получить их сборщиками и сверить исторический SHA. Большие CSV доступны как gzip в `normalized/large_exports/`; обратная распаковка должна дать `external_artifacts_manifest.json` SHA. Mutable endpoint может больше не отдавать исторические байты: такой повтор не считается тем же snapshot.

```sh
python3 context/16_agent_research/core/collectors/normalize_core.py
python3 context/16_agent_research/core/collectors/check_timezones.py
python3 context/16_agent_research/core/collectors/augment_keys.py
python3 context/16_agent_research/core/collectors/extract_market.py
python3 context/16_agent_research/core/collectors/normalize_svx_market.py
python3 context/16_agent_research/core/collectors/verify_core.py
python3 context/16_agent_research/core/collectors/archive_large.py
python3 context/16_agent_research/core/collectors/prepare_publication.py
python3 context/16_agent_research/core/collectors/finalize_core.py
```

Для социальных и операционных таблиц — их собственные команды в branch integration_plan; код перед запуском просмотреть. Нормализация не запускает финансовую модель и не определяет веса. Сводный финализатор читает manifests, проверяет байты и whitelist заголовков, считает CSV records, соединяет карточки источников. Для повторного получения публичных URL — acquisition collectors, с отдельным новым snapshot и сохранением старого.

Перед оценкой сети требуется отдельная версия airport→area/catchment и carrier identity, воспроизводимый общий период сравнения конкурентов, явные технические допуски и ресурс RW. После этого спрос/цены/выбор пассажира и сценарии записываются отдельными таблицами MODEL_ESTIMATE/SCENARIO с ссылкой на этот input manifest. Пропуск данных не превращается в ноль, оценку привлекательности или отсутствие конкурента.
