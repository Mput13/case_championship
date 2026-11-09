# case_championship — кейс Red Wings

Кейс-чемпионат МАИ «Связанность территорий», кейс Red Wings: «Новый хаб или прямые рейсы?»

## Ресёрч и ТЗ на расчёт (docs/)
- `docs/00_index_and_ideas.md` — **начать отсюда**: карта документов, решения, все идеи, ТЗ на расчёт, чек-лист сдачи
- `docs/01–19` — условия кейса, ресёрч по темам, сводка работы
- `tools/dist.py` — расстояния между аэропортами и «светофор» дальности (`python3 tools/dist.py`)
- `START_PROMPT.md` — стартовый промпт для чата с расчётами
- `materials/` — исходные материалы организаторов (хранятся локально, в git не входят)
- `CLAUDE.md` — контекст для Claude Code

## Расчёт: лонглист городов (src/)
Откуда какие данные — `docs/22_data_sources_longlist.md`. Нужен Python 3.13 с pandas и openpyxl.
```
py -3.13 src/fetch_static.py                      # OurAirports и «Если быть точным»
py -3.13 src/fetch_kover.py --since 2024-11-01    # канал Росавиации об ограничениях, ~25 мин
py -3.13 src/kover_days.py                        # дни «Ковра» по аэропортам
py -3.13 src/longlist_data.py                     # население, дальность SSJ, прямые рейсы, поезда
py -3.13 src/build_longlist.py                    # data/processed/longlist.csv и outputs/longlist.xlsx
```
Ручные данные со ссылками — `data/manual/longlist_manual.csv`.

## Командный пакет (context/)
[Объяснялка: контекст, решения и ближайшие задачи](explain.html) — непрерывный документ со схемами, реальными примерами данных и двумя интерактивными расчётами. [Решения D01–D12](context/10_decision_guide/decisions.csv) и [задачи T01–T10](context/10_decision_guide/tasks.csv) пока предложены для обсуждения, а не приняты командой.

[Контекст кейса №5](context/README.md): требования чемпионата, разбор NotebookLM, источники, данные, города, конкуренты и идеи. Срез — 7 ноября 2026 года.

Быстрые входы: [каталог данных](context/05_datasets/README.md), [проверки Terra](context/07_verification/README.md), [идеи](context/06_ideas/README.md), [дополнительное исследование](context/09_additional_research/README.md).

Исходные документы, полный Telegram, DOM авторизованных страниц и технические сведения сессий хранятся только в локальной рабочей папке и исключены из Git.

Сводный каталог: `python3 scripts/build_source_registry.py`. Проверка файлов: `python3 scripts/check_context.py`.
