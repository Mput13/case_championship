# Передача дополнительных сигналов

Все пути ниже относительно `alternative/`. Общие таблицы и evaluator не изменены. Это предложение соединения, а не утверждённый новый вес города.

| Вход | Общая таблица | Ключ и условие | Что нельзя переносить |
|---|---|---|---|
| `modules/tourism/normalized/primary_observations.csv.gz` | `area_observation` | `area_id` OKATO, indicator, year, YTD month, raw snapshot | Сумму YTD как годовой итог; родительские регионы поверх AO |
| `modules/tourism/normalized/primary_monthly_increments.csv` | `feature_observation` | Тот же area и ряд, DERIVED; полный профиль для seasonal shares | Региональное размещение как аэропортовый OD; масштаб ×1000 |
| `modules/business/normalized/sibur_sites.csv` | Отдельный `organisation_site` модуль | publisher `site_id`, snapshot, исходный адрес; curated region — отдельное производное поле | Все пары площадок как наблюдённые связи; ближайший аэропорт без модели доступа |
| `modules/business/normalized/group_site_membership.csv` | Связь группы и площадки | `group_id, site_id, snapshot_id` уникальны | Численность и частоту поездки |
| `modules/business/normalized/gazprom_shift_observations.csv` | Групповой контекст | Organisation, indicator, year, snapshot | Один национальный запас работников всем городам |
| `modules/business/normalized/historical_vankor_routes.csv` | Исторические evidence assertions | Направленная пара, дата публикации, метод search-index; коды аэропортов только подсказки | Современную программу и свободный коммерческий поток |
| `normalized/weather_monthly_2024.csv` | Исторический `feature_observation` станции | station_id, UTC month, snapshot; unit degC/m/s | Риск отмены или actual closure hours |
| `normalized/join_airport_weather_month.csv` | Демонстрация `feature_observation` аэропорта | station→airport точный ICAO, right ID уникален, 9 unmatched NULL | Автоматическое ближайшее совпадение и актуальный допуск |
| `modules/telegram_correction/normalized/main_posts.csv` | Staging для `operating_event` | Только MAIN_TEXT_RECOVERED; source_page hash; затем action-clause/airport review | Original contaminated text; полный календарь ограничений из partial |

`source_snapshot` получает URL, source lineage, retrieval, SHA, source status и лицензию из `dataset_manifest.json`. Модули содержат свои манифесты и поддержку; root `file_inventory.json` фиксирует все артефакты без самоссылки. SHA сохранённых gzip и распакованных байтов различаются. HTTP Last-Modified не дата первой публикации. Headers только whitelist из `headers_policy.json`.

Исторический тест должен использовать доступность данных на дату решения. Снимки 2026 нельзя объявлять известными в 2024. OurAirports snapshot 2026 используется здесь только для демонстрации идентичности кодов. До расчёта маршрута требуется общий версионный airport/area crosswalk и отдельное правило аэропортовой зоны доступа; региональные totals не копируются каждому аэропорту как спрос.

## Проверка добавочной полезности

Предлагаемые эксперименты ниже не запускались; статуса эмпирически полезного признака нет.

1. При одинаковом калиброванном годовом OD и бюджете сравнить плоский календарь и форму размещения 62073. Для санаторных целей — 62074, только на пересечении заполненных регионов и одинакового охвата. Train/holdout по времени, сначала 2023–2024 → 2025 внутри методики; 2026 отделить. Отдельно удалить 62302 и весь блок ночёвок.
2. СИБУР использовать для генерации конкретных целей и проверки contracts, затем проверить фактические взаимодействия. Исключение корпоративного признака должно сохранять население/доступность/обычный поток. Отсутствующий город — UNKNOWN; редкий модуль не пополняет универсальный рейтинг нулями. Проверка по прошлым открытиям/закрытиям требует независимых меток, сейчас NOT_RUN.
3. Погодные описания сопоставить с независимыми фактическими задержками и типом ВС при контроле частоты наблюдений. Проверить другой год, аэропортовые минимумы, видимость/QC и погодонезависимые отмены. Без этого коэффициент отмены не оценивать.
4. Telegram использовать только после исправления атрибуции тела. Для событий нужны независимые проверки mixed actions, аэропортов, эффективных дат и пробелов. Ни count, ни announcement elapsed не заменяют действовавший интервал.

До этих проверок не менять существующий evaluator ради победы кандидата. Сезонный календарь не подтверждает масштаб OD; сценарный объём и наблюдённые региональные значения сохраняются раздельно. Предложение RW должно отдельно пройти парк/расписание, продажи конкретного продукта, нетто-выручку, добавочные затраты, каннибализацию и выход из программы.

## Воспроизведение без сети

Команды из корня checkout; stdlib Python, установки не нужны:

```sh
python3 context/16_agent_research/alternative/collectors/snapshot_inputs.py --git-only
python3 context/16_agent_research/alternative/collectors/weather.py
python3 context/16_agent_research/alternative/collectors/join_demo.py
python3 context/16_agent_research/alternative/modules/business/collectors/normalize_business.py
python3 context/16_agent_research/alternative/modules/tourism/collectors/verify_tourism.py
python3 context/16_agent_research/alternative/modules/weather_review/verify_independent.py
python3 context/16_agent_research/alternative/collectors/consolidate.py
python3 context/16_agent_research/alternative/collectors/package_manifest.py
python3 context/16_agent_research/alternative/collectors/verify_package.py
```

Полный пересчёт туристического модуля описан в его `dataset_manifest.json.reproduce_offline`; простая проверка выше не повторяет сетевые запросы. Повторный repair Telegram без `--historical` перепарсит кеш; ограниченное продолжение с сетью — по модульному README и сохранённому receipt, без параллельного общего сборщика. Проверять отсутствие активного ремонта перед повтором. Старые quarantine-выходы не активировать.
