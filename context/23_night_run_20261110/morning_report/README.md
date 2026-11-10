# Утренний отчёт Red Wings

Открыть `morning-report.html` как локальный HTML: все данные, география, CSS и JS inline. Сервер, интернет и зависимости не нужны. Это отчёт, публичные страницы и owner dashboard не изменены.

Воспроизведение из корня репозитория:

```sh
python3 context/23_night_run_20261110/morning_report/build_report.py
python3 context/23_night_run_20261110/morning_report/verify_report.py
```

Сборщик читает immutable Git objects exact root d8ea350a0388d35f5b559f65a57109d862d2eb85 и methods a77e4cfbd14e560d26407479b7252cfcb15f4f41. Late appendix читает exact60109f632e7f2edd05d1b1e202ce83f404457c3b. Нужны эти локальные Git objects; сеть при сборке не используется. Все writes ограничены этой папкой. Повтор сборки восстанавливает QA views, verify добавляет к qa-map интерактивные assertions.

В `sources_manifest.json` exact SHA/hash входов и ссылки, `report_data.json` точные 12 common rows, 35 спецификаций, 15 конечных сетевых составов, паспорт и конкуренты. `checks.json` — статические, арифметические и JS проверки; `native_qa.json` — native html_preview 1200/390 и deep views. `qa-map.html` и `qa-deep.html` — воспроизводимые вырезки глубокой главы с теми же стилями/рендерером; они нужны для визуальной проверки и не заменяют основной HTML.

Основные главы видимы при прокрутке. Оглавление sticky; на узком экране открывается кнопкой. Каталог содержит карты и текст всех35 программ. География Natural Earth/реальные координаты из frozen assets; исходные57 карт доступны в selector, добавлены5 model-gated составов. MOW не имеет координат и не трактуется физическим аэропортом. Таблицы и увеличенные карты прокручиваются горизонтально с клавиатуры/тачем. Встроены zoom controls.

Лично проверены: входные asset hashes, exact a77 handoff,35 IDs, география62 карт, компиляция JS,12 денежных тождеств, отсутствие внешнего runtime/локальных путей/PII email, native визуальные ширины и62 переключения, TOC, zoom, отсутствие outer overflow. Независимое review отчёта запускает root. Экономический replay, новый source research и реальная эксплуатация NOT_RUN. Upstream scoped reviews унаследованы из freeze. Скриншоты просмотрены через native html_preview, отдельный PNG-архив не создавался.

Поздняя версия Анастасии/kiruha355 b91 показана отдельно: OWNER_EXPORT_UNREVIEWED как состояние на freeze и SCOPED_IMPACT_CHECKED в late appendix. Полная приёмка b91 не заявлена, frozen2f и общие C/N не заменены. Raw report с контактами не копируется в HTML; используются безопасные claims/CSV и attribution по имени/handle.
