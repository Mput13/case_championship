# Независимая финальная приёмка P38: CHANGES

Денежной ошибки, меняющей MAIN ranking, в исполненных проверках не найдено. Приёмка полного запрошенного пакета пока **CHANGES**: отсутствует требуемая ветка распространения задержек при turn90. Это локальная ошибка покрытия вычислений, а не требование нового исследования или пересборки стратегии. Остальные существенные риски отделены в findings.csv как uncertainty.

Один reviewer, без субагентов. Запись только review/. Старые builders/verify/exporters не запускались; использованы чистые API и собственные проверки. Git, commit/push, панель, контакты и брони не затрагивались. Handoff, STOP.

Ошибка: economics/calculate.py:608 фиксирует ready=arrival+60; delay_details и delay_summary не содержат turn_minutes. Отдельный обычный календарный тест90 не заменяет hold30/60/120 при90. Все три финалиста уже имеют CONTINUOUS_TURN_FAIL при90, и это корректно раскрыто в operational_gates. Следовательно, нельзя просто добавить30мин к результатам и назвать их допустимым восстановлением. Нужны отдельные baseline/shock trajectories с carry-in, новый/retained trigger и границы месяца/года; baseline failure должен оставаться явным отказом.

Независимая диагностическая рекурсия совпала со всеми144 сохранёнными примерами при60. При90 от того же начального trigger изменились144/144: C0121723, NEW-ISO7/L1@2027-02-22, hold30 — задержка следующего плеча30→60мин; retained OWN-WZ-5029-ISO3/L1@2027-02-08 — максимум распространения30→99мин. Это контрпримеры переносимости опубликованных buffers, не actual recovery/slot/FDP прогноз и не самостоятельная полноценная turn90 baseline simulation. Рублёвого эффекта без actual recovery costs установить нельзя. Файл delay_comparison.json сохраняет примеры; патч не применялся.

Исполнено 12 групп независимых проверок, все PASS в собственной области:

- 25seed,19 дополнительных template-пар,2 112 direction/month/scenario строк; 420 financial classes/436 variants. Старый top5 сохранён. CEK–SVX/SVX–TJM в seed — positioning; коммерческие предложения не создаются.
- Все31 608 месячных скаляров: revenue−cost, W−K, R−W, R−K. Для1 874 годовых строк восстановлены суммы месяцев. У5 232 CAUT programme-month R−W отрицателен; ближайший к нулю −1 147 080,45₽. Это множество436×12, не global proof и не доказательство против произвольных through portfolios.
- Самостоятельное восстановление action_map/old bank/options трёх primary cohorts;9 fullP06 сравнений KEEP/W/REPLACE в феврале/июле BASE/CAUT, плюс MOW с retail rechoice. Физическая capacity и расход топлива сверены; fixedcrew исключён один раз. Это old KEEP и mixed в каждой когорте; отдельного legacy-new K1/K3 в60 P36 нет.
- Все36 monthly calendars финалистов сверены с годовым whole-job ledger и432 frequency rows. R1 не летает. Все12 переходов выбранных K1/K2/K3 BASE policies независимо разложены по первому вылету job; суммы stitched annual воспроизведены. Проверены Jan/Dec и сентябрьский seam, не12×Feb. Through отдельно:12 продуктов с оплатой journey один раз и capacity обоих плеч; peak weights сохраняют один месячный pool.
- 72 monthly/6 annual resource frontier scalar identities и192 nested identities; все8 точных nested pairs дополнительно пересчитаны для июляCAUT с одинаковой action_map. Полный frontier поиск не повторялся; global optimum не заявлен.
- Один directed inverse независимо найден бисаекцией по независимо решаемой capacity allocation: OMS→MOW, январьCAUT,3044,215436087 potential journeys; прочие OD фиксированы. KJA integer KEEP BEP69/115 воспроизведён отдельно.

Точные границы независимости по12 блокам — coverage_table.csv. В частности, не повторены все238 edge ceilings, весь frontier search, все pilot stress rankings и весь dated-entry generator. Чужие validation/repeatability receipts прочитаны как provenance; собственные PASS не взяты из их значков.

Для ближайших пилотов выбор сейчас — **сохранить текущие обязательства до подтверждения условий; пилот не одобрять**. KEEP здесь означает отсутствие обоснования нового действия, а не доказанную прибыльность существующей работы. Альтернативный AER/removal menu также не следует исполнять автоматически: его C/старые обязательства неизвестны.

| Четыре недели февраля | Билетов на каждый новый service departure против KEEP/same-W, BASE / CAUT | Против лучшего конечного menu, BASE / CAUT | BASE net при100 билетах против KEEP/same-W |
|---|---:|---:|---:|
| SVX–KJA,1RT/нед |69 /115|482 /768|9 883,342₽|
| SVX–IKT,1RT/нед |67 /112|368 /588|13 154,4791₽|
| GOJ–KJA mixed, обе дирекции2/нед |73 /117|132 /202|10 707,15896₽|

IKT/GOJ значения прочитаны из delivered pilots; независимый integer rerun выполнен для KJA. GOJ-граница относится ко всем новым плечам замкнутой mixed-программы, не только GOJ–KJA. Это билеты по каждому датированному плечу, не уникальные люди. Все CAUT integer bounds превышают100. Число482 у KJA — равномерный ticket diagnostic всего пилота против полной иной программы со снятием старых jobs; это **не482 для самоокупаемости маршрута**. KEEP69 отдельно. Выручка при full100 — граница, не прогноз продаж.

BASE opportunity gaps против выбранной альтернативы: KJA44,632105млн₽; IKT45,215876млн₽; GOJ mixed34,390107млн₽ за4недели до differential C/D/F/R1. Actual cancellation differences могут менять выбор. Одобренный бюджет NULL. Для запуска требуется observed directed OD/net плюс положительный результат после совместного вычета C/D/F/R1/exit против действительно допустимой альтернативы; либо явно оплаченный полезный эксперимент с утверждённым полным cash budget. Не выбирать бюджет по размеру модельного убытка. Stop — потеря ops/resources, нарушение q/net gate или утверждённого полного бюджета с exit. Expand — только observed invoices/sales/ops и положительный добавочный joint результат против альтернативы в конкурентном мире.

Точные RW-запросы остаются в economics/RW_data_request.csv: route-month endpoint OD и settlement, собственные connecting потери, полные15 обязательств и released tails/R1, cancellation charges, invoice component overlap/tax, dated costs/setup/exit/payment calendar, FDP/slots/MRO/payload. Отсутствие этих данных не ошибка арифметики и не нулевой спрос/расход. Требование8–12 доказанных новых маршрутов не закрыто; данный пакет — исследование прямого варианта. Actual profit/cash и SJ margin NULL. SJ только H2 2027 AND entry; RRJ envelope не PD8 cost. 2028 OD/cost/calendar — явный scope gap, условие отдельного пересчёта, не бесконечного поиска.

Источники: независимо повторно прочитаны сохранённые HTML HTTP1 (TOF=Томск, WZ5003, периоды до19декабря/26ноября), HTTP4 (GOJ–MRV N4805, пн/пт21:20–00:45+1 до26марта), выборка rows WZ5029 до декабря. Это не live-переоткрытие сайтов и не свидетельство будущего выполнения. Декабрь не продлён в февраль/лето. WZ5030 conflict gate сохранён в programme_specs:24179. Остальные old excerpts/130 evidence rows не все семантически проверены заново; сохранение bytes не доказывает истинность источников.

По PDF-skill заново отрендерены и визуально прочитаны страницы1–2 сохранённого SVX PDF:610/370₽ за т максимальной взлётной массы и84/285₽ за пассажира ВВЛ; заголовок «без учёта НДС», дата начала25.07.2026, изменения01.11.2026. Это компоненты, не полный RW invoice. MRO/GPU/parking/cargo и второй PDF в этой приёмке визуально повторно не проверены; их ограничения приняты как ограниченные completed-source claims, не самостоятельный semantic PASS. Никаких numeric invoice replacements.

Контроль сохранности:190 файлов пяти completed пакетов не изменились относительно начала приёмки; registry1621 содержит1614 immutable с совпавшими SHA256 и7 явно исключённых mutable orchestration metadata. Проверены и hashes расчётных входов. Собственные receipts: checks.py, actual_run.log, validation.json. Команда воспроизведения из корня:

```bash
context/28_end_to_end_audit_20261110/code/sandbox/venv/bin/python -B context/38_direct_strategy_20261113/review/checks.py > context/38_direct_strategy_20261113/review/actual_run.log 2>&1
```

Условие закрытия CHANGES: адресно исправить turn90 delay dimension/baseline handling и независимо подтвердить конкретные новые receipts. Полный420×12 rerun ради этого не нужен; если денежные входы не изменились, нынешняя scoped денежная сверка остаётся действительной. Root решает финальную публикацию после исправления и приёмки; reviewer ничего не публикует.
