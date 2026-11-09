# Расписания и аэропортовые расходы

Первичный сбор выполнен 2026-11-09 10:52–11:02 UTC по сохранённым acquisition timestamps. Прежний незавершённый progress описывал только этот начальный этап. После перезапуска T3 работа восстановлена из сохранённых байтов: профильных команд сбора не обнаружено, повторных HTTP-загрузок при финализации не выполнялось.

## Завершённый пакет

Стабильный срез: 2026-11-09T13:42:20.011476+00:00.

- 28 зарегистрированных raw/dependency/diagnostic файлов, 16 568 359 байт; все размеры и SHA256 совпали. 4 исторических Telegram CSV ограничены RESTRICTED_USE / PARSER_CONTAMINATION и не использованы как route/event facts.
- UVT153 уникальных направленных правил; IrAero1 730 endpoint itineraries из6 origin снимков; SVX482 правила/80RW; Azimuth185 строк табло/81 reported-arrived; PP1242446 строк/306 номерных групп.
- Омский PDF:76 отечественных правил/13 перевозчиков+1 exception; раскрыта одна неделя98 вылетов из OMS/21 carrier-destination группа с pinned airport keys/поясами.
- 30 тарифных строк UFA/OMS сверены с сохранёнными полными PDF-страницами. source_status=VALIDATED ограничен validation_scope выбранной строки. Публичный тариф не договор RW.
- Пример UVT+Omsk соединения совпал по RT/flight651/периоду/04:30→11:15; отдельный PDF сохраняет путь через Тобольск. Endpoint Kazan–Omsk не превращён в nonstop.

## Проверки

Offline replay normalize.py + supplement.py повторён без сети: байты CSV/JSON выходов идентичны; raw не изменились. Независимый HTMLParser насчитал447 строк первой subsidy table (header+446 данных). Ключи153UVT/98OMS уникальны; keys/timezones для OMS не пропущены.

У IrAero часовая база не установлена; исправлена прежняя неподтверждённая формулировка local time на UNKNOWN, исходные часы сохранены. У Azimuth clock basis UNKNOWN, у SVX year UNKNOWN. 2UVT arrival conflicts,1IrAero self-loop,9 нелатинских кодов и304 multi-endpoint групп удержаны отдельно.

Источник, покрытия, ограничения и reproducible commands: source_registry.csv, dataset_manifest.json, normalized_manifest.json, coverage.csv, integration_plan.md, findings.md, rejected_or_unavailable.csv и debt.csv. Все headers по whitelist6safe; исходные payload не менялись.

Контракт прочитан; pinned front71b493d и team-updatebf564c7 учтены. Финальное обновление refs и публикация checkpoint остаются у ведущего. Коммит/push/merge субагентом не выполнялись.
