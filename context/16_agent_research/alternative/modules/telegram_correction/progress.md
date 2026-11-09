# Исправление исторических тел Telegram

9 ноября 2026. Прочитаны critic/front_audit/audit.md и findings.csv. Исходный favt_posts.csv не изменялся: SHA256 3ef101d50e394b58ce10ac21dfb2b7b0790d25c7fdf461d313017b20bce5512b, 8318 строк, min ID 575, max ID 9279. Байты совпадают с Git 71b493d0051dc3acf2a7619801e5b0eb022bddd3:data/raw/favt_posts.csv.

Свободное место перед восстановлением: 11 GiB. Ожидаемый объём около 420–450 HTML-страниц, порядка 60 MiB несжатых и 10–20 MiB gzip; установки зависимостей нет. Используется собственный HTMLParser стандартной библиотеки, точное членство классов js-message_text и js-message_reply_text.

Первыми GET получены /s/favt_info/4687 и /6503. Полные HTML сохранены без изменения байтов; заголовки сразу приведены к whitelist, исключённые значения не выводились. Две страницы содержат 42 уникальных основных тела. У 19 исходный CSV равен reply-preview после нормализации пробелов; у всех 19 основное тело отличается. Это целевая выборка, экстраполяция не выполняется. Точные 4687/6503 и mixed 4685 сохранены в reproduction.json.

Следующий этап: четыре независимые нисходящие цепочки source before-ссылок, не более четырёх одновременных HTTP reads. Все ответы сохраняются gzip с SHA исходных и сжатых байтов и receipt. При rate limit или ошибке разбора работа останавливается. Никакого fallback на загрязнённый original text, классификации событий или пересчёта дней в этом модуле нет.

Совместимая выходная схема normalized/main_posts.csv: id, dt_utc, dt_msk, text (только основной body), body_status, source_page_url, source_page_sha256; дополнительно main_text, reply_preview_text, reply_href, provenance и coverage. Строки всех 8705 ID интервала представлены, даже если ID отсутствует в original. Невосстановленные тела имеют NULL, не пустое наблюдение и не цитату. original-only coverage считается отдельно.

## Финальный ограниченный срез

2026-11-09T12:40:49.113372+00:00 — остановка по максимуму 120 уникальных страниц. Получено 2337/8318 original main; full_original_main_text_recovery=false. 5981 original ID пока unresolved; диапазон включает дополнительно387 ID вне original. Проверки byte hashes/keys/source provenance/4687/6503/mixed4685/headers — PASS. GET-процессы завершены, следующая команда только в resume.json.
