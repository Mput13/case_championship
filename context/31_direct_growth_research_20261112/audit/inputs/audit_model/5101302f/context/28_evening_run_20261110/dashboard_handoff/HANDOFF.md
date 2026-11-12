# Передача immutable пакета

Один bounded пакет в `context/28_evening_run_20261110/dashboard_handoff/`. Основной вход — [README.md](README.md), карточки — [cards.md](cards.md), ранние тезисы — [passport_excerpt.md](passport_excerpt.md). CSV/JSON содержат exact provenance, независимую границу и неполное покрытие без подстановки нулей. UI/Site/root HTML и авторские файлы не менялись; browser/UI QA, сервисы, новый research, экономика/allocator, платные вызовы и внешние сообщения не выполнялись. Детей и других задач нет.

Зафиксированы networkb471+reviewcccc, products388908+review6cc8, evidence38f+review13f7, digitald48+review1046, rootcb6D03correction. f99 имеет отдельный EV-MR03review994c: условная арифметика 96datedannual/2298weeklyLP, same-flight retime и C31oneweek/fullC35contract. v4 exact9f0 сериализован отдельно, **APPROVE_SCOPED EV-MR04 exact934a**, без наследования старых verdict. Исторические PENDING сохранены в acceptance_events.json; текущая квалификация записана отдельными exact review событиями. Root может добавить поздний immutable receipt/addendum.

H11 для следующего расчёта: при текущем N(t) одна программа согласована по обе стороны недели 27.12.2027–02.01.2028. Если появятся новые Jan1deliveries, сначала выбрать общую недельную программу, затем делить по годам. Не навязывать эту техническую деталь интерфейсу.

`python3 context/28_evening_run_20261110/dashboard_handoff/build.py --verify` проверяет bytes/ключи/foreignkeys/источники и не пишет файлы. [verification.json](verification.json) — только личная проверка сериализации, не независимый review сборки и не market/fleet/award/fullPnL/cash acceptance. Root запускает независимую проверку отдельно.

Публикация: один commit и push только своей ветки `t3/dashboard-handoff-package`, без PR/merge/rebase/force. Итоговый commit и результат `git ls-remote` передаются в финальном ответе; внутри этого же коммита его SHA не записывается как самоссылка. Срок первого полезного пакета — 20:55, своей сборки — 21:05; общий срок 22:00 не продлевается.

Финальная упаковка методики закреплена на `5512f7d474a5db4bb658aae30b10f8b886629861`: [final_handoff](methods_final/final_handoff.md), [freeze](methods_final/freeze.json), [текущие восемь subject→review](methods_final/final_acceptance.csv). Owner freeze — 20:47:39 МСК; общий input cutoff root — 21:15, срок результата — 22:00. Аналитические числа продолжают ссылаться на прежние exact subjects. Исторический PENDING в strategy/acceptance_register.csv сохранён; текущая квалификация — acceptance.csv и acceptance_events.json.

Owner replay допускается только в disposable copy. Для f99 annual_market_caps.csv возможен иной set-derived порядок строк при тех же keyed values; побайтная воспроизводимость всех rerun CSV не обещается, frozen файлы не перезаписываются. Побайтный verify этой сборки относится только к сериализации уже сохранённых exact blobs.
