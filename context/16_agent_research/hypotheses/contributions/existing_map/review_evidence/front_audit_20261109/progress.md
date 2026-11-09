# Аудит front

Завершён первый независимый срез. Вход front 71b493d0051dc3acf2a7619801e5b0eb022bddd3, предыдущий источник 5e896e8ea5bb97136c71c49562a345b8f210bf11. Просмотрен код до исполнения.

Существенная находка: Telegram TEXT_RE берёт reply preview вместо body. В трёх целевых страницах44 уникальных поста,19 с reply и19 несовпадений. Выборка целевая; полный пересчёт NOT_RUN. Частичная коррекция44 тел при прежнем счётчике убрала2 ложных intro-дня VOG. Дополнительно: смешанные события поста, неизвестные конкуренты, единицы gap_pop, рассчитанное время поезда и причинные границы post-days.

NULL rail:31/489 gap-пар, до8.68% gap_pop. Исключение31пар сохраняет все20 рангов и обе top3; старый сильный тезис о смене победителя не подтверждён на этом SHA. scan_news AVIA-фильтр и MOW-группировка уже присутствуют.

Выходы: audit.md, findings.csv, reproduction.json, partial_day_impact.json, input_manifest.json, primary_manifest.json, native_access_diagnostic.json. Native web.open Telegram access failure диагностирован безопасным текстовым HTTP: exact URLs200 text/html без redirect; причина инструмента UNKNOWN. Процессы/профили не менялись; зависимостей не установлено.
