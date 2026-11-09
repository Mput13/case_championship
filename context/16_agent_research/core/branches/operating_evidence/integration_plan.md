# Интеграция расписаний и тарифов

Пути разрешаются относительно этой папки. Исходные acquisition snapshots — список `dataset_manifest.json`; нормализованные артефакты и SHA — `normalized_manifest.json`. Закреплённые Git-входы и справочник — `input_refs.json` и `normalized/canonical_dependency.json`. Коммиты, push и объединение выполняет ведущий; этот сборщик не меняет общие таблицы.

| Общая таблица | Вход | Правило интеграции и ограничение |
|---|---|---|
| `source_snapshot` | `dataset_manifest.json` | Сохранить source_url, retrieval UTC, raw hash, license, статус и ограничения. Telegram restricted записи HOLD. Разные origin URLs IrAero — срезы одного издателя, не независимые проверки. |
| `service_rule` | `uvt_schedule_rules_unique.csv`, `svx_published_schedule_rules.csv`, `omsk_domestic_timetable_rows.csv` | Ключи publisher/carrier label/flight/airports/validity/weekdays/snapshot. Направления разделять. У SVX год UNKNOWN. UVT и OMS сохраняют промежуточные точки и source exceptions; нельзя автоматически называть endpoint nonstop. |
| `flight_instance` | `omsk_outbound_week_20261207.csv` | Только вылет OMS имеет однозначную привязку к местной дате в этом раскрытии. IATA aliases и pinned keys явны; UTC вылета DERIVED из OMS local. Полёт остаётся PUBLISHED, не EXECUTED. |
| `flight_instance` | `azimuth_flight_instances.csv` | План/сообщённый факт раздельно. `Прибыл` — утверждение табло перевозчика. Clock basis и промежуточные посадки UNKNOWN; UTC и блок-часы не вводить. |
| `access_alternative` | `iraero_published_itineraries.csv` | Published endpoint itinerary с возможными посадками, не отдельный flight leg. UNKNOWN clock basis, проблемные коды и self-loop отдельно. Несколько конечных пунктов одного flight/date не суммировать как кресла. |
| `subsidy_record` | `favt_subsidy_2026_full.csv` | Стадия PROGRAMME_PLAN. Пары/периоды/кресла/частоты хранить в исходных единицах. Award и paid amount NULL. Rowspan inheritance сохранён. |
| `cost_component` | `airport_cost_selected_verified.csv` | Ключ airport/item/effective_from/unit/scope/source. Значения OBSERVED опубликованного тарифа, не контракт RW. `validation_scope` ограничивает визуальную проверку выбранной строкой; НДС, исключения и пакетность сохраняются. |
| `carrier_version` | `carrier_source_aliases.csv` | Источниковые соответствия для четырёх перевозчиков; юридическая идентичность и официальный IATA registry отдельно UNKNOWN. Не расширять алиасы по одному похожему имени. |

Проверки до каждого join: уникальность ключа обеих сторон, unmatched, возможное размножение, одинаковый период и направление. Для примера UVT/OMS ключ дополнительно включает RT/ЮВ, flight651, конечные точки и пересечение срока; совпадают времена, но OMS раскрывает Tobolsk stop. Сохранить это как ограничение типа связи.

Для сравнения конкуренции применять сопоставимую неделю и operating flight inventory. Омский календарь даёт 98 предложенных вылетов/21 carrier-destination группу, но исключённая/неизвестная запись не равна нулевому конкуренту. Не суммировать зеркальные UVT строки, маркетинговые коды и endpoint предложения IrAero как независимую ёмкость.

В пакет оценки передавать только подтверждённый смысл поля. Наблюдений OD, свободного парка, заключённых контрактов или net realised yield этот пакет не добавляет. Исторические сценарии disruption не обновляются загрязнённым Telegram-счётчиком. Изменение порогов, весов и demand coefficients — отдельная версия оценщика для всех кандидатов.
