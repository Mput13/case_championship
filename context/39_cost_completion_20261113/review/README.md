# P39 independent review — COMPLETED

**Verdict: ACCEPT_WITH_LIMITATIONS.** Существенных ошибок расчёта в проверенном scope не найдено. Один независимый проход, без субагентов, Git, пересчёта сети, оптимизации и правок чужих outputs. Запись только в review. TASK, pins и integration_contract прочитаны.

[check.py](check.py) самостоятельно читает CSV, выполняет арифметику и проверяет lineage. [check.log](check.log): PASS по 12 группам ниже; PASS7835 автора не принят как собственная проверка. build/verify прочитаны, их main не запускались. Только чистые scalar helpers извлечены через AST для проверки null/zero/negative rounding. [input_content.json](input_content.json) фиксирует SHA256 существующих P39 файлов перед проверкой; содержимое сохранилось, mtime не используется.

| Группа | Результат и предел |
|---|---|
| 1. Coverage | Все 117 исходных статусов и формулы перенесены в 546 уникальных строк, 39×14, без пропусков |
| 2. Existing amounts | Все строки сверены с annual_drivers; P38 excluded crew отдельно, included=0 не выдаётся за реальную бесплатность |
| 3. Lineage | Ссылки coverage/driver/source разрешаются, использованные code citations совпадают с pinned snapshot; snapshot hashes совпадают |
| 4. Exposure/fleet | owner totals/exposures согласованы; 6+1, 7+1, BASE_SUB8+1 и отдельные CAUT; 52/48 недель; OMS departures из airport breakdown; journey+transfer=segments |
| 5. Вычеты и корзины | Из pinned rates независимо пересчитаны BH/flight/segment proxies, gross fuel и credit; credit вычтен один раз; owner crew включён, P38 исключён; net revenue−cost=M без повторного tax/migration |
| 6. Unit×qty | Все normalized min/max пересчитаны; bag/desk по OMS departures; hotel по .01×transfer journeys/occupancy; численная нормировка не forecast |
| 7. Unknown/cash | Неизвестное×0 остаётся null; известный0 остаётся0; отдельны annual, expense, CAPEX, deposit, stock, advance, WC; полный budget UNKNOWN |
| 8. Overlap | Parking month/hour/day альтернативны; нет admitted ADD; новые услуги не прибавлены поверх ground/MRO; buy/lease/outsource и avoided cost требуют scope |
| 9. Headroom/stress | M/(12×alltails), working-only и historical rent независимо проверены; headroom условен до остальных costs; reserve уже включён; techreserve не сложен с MRO |
| 10. Источники | Основные единицы сверены с первичными материалами ниже и всеми их числовыми сценариями; PKC/tender/insured value не допущены в additions |
| 11. P38 | Датированные flights/BH/OMS и24 active working tail-months проверены; R−W/R−K заново получены из monthly KEEP/WITHOUT_NEW/REPLACE; standalone M не incremental |
| 12. Validation/preserve | Четыре output SHA256 совпали с validation; собственный content-before/after совпал. Историческая protection имеет неблокирующее ограничение, см. findings |

Первичные материалы проверены по сохранённым полным изображениям страниц и HTML, не только prices.csv:

| Источник / locator | Подтверждение и ограничения |
|---|---|
| omsk_price_recovery/renders/oms_20260821-02.png, PDF p2 §§2.3/2.8 | 1229.51/рабочее место для информирования, не DCS/check-in;3275/раздача, не цена еды |
| oms_20260821-03.png, PDF p3 §2.15 | 4450/дополнительное обслуживание по заявке; не kg/bag/pax и не каждая стыковка |
| oms_20260821-05.png, PDF p5 §§8.1/9.1.1 | 3430/начатый моточас;117100 и130200/месяц по MTOW, не годовые суммы |
| oms_20260821-06.png, PDF p6 §§9.2.1/9.3.1 | 1018/1140 за час;24432/27360 за сутки; альтернативы monthly |
| oms_20260821-10.png, PDF p10 §11.19 | 330/1000 за м²-месяц складского хранения; не аренда здания/офиса |
| oms_20260821-11.png, PDF p11 | 6.23/55.60 за телеграмму; заголовок кроме НДС и сноска не устанавливают численную ставку2027 |
| contract-08.png, PDF p8 §§6.1/6.7.1 | Заказчик, тариф на дату услуги,100% предоплата; generic условия, не signed RW budget |
| sources/flagman.html:272,298,307,318,338; excerpts/flagman.txt:82 | RO4100 single/4650 double за номер-сутки;01.02–31.12.2026. BB5050 даёт delta950, не standalone food quote. Occupancy и integer actual rooms обязательны |
| [СудАкт, акт15.04.2021 А08-2884/2015](https://sudact.ru/arbitral/doc/P6tWcgW0i6Jj/), §§11.1/11.2, абзацы106–114 | Прямо открыт известный legal mirror:7560000incl18% и отдельно2874480incl18% за каждый борт-месяц. Договор2015, remand; exVAT6406779.6610 и2436000 арифметически верны. Исторический stress без FX/индексации; не текущий quote и не окончательная правовая оценка |

Относительные имена PNG/HTML в таблице относятся к ../omsk_price_recovery/renders/ и ../omsk_price_recovery/sources/. Извлечения amendments прочитаны; новый поиск цен не выполнялся. Страховая стоимость и initial tender проверены как недопущенные входы, не как доказанные страховые премии. Полная правовая/market-truth приёмка не заявляется.

В [findings.csv](findings.csv) одна P3-группа: protection digest автора уже расходится с pre-review содержимым145 файлов; конкретный изменившийся файл UNKNOWN. Кроме того, verify.py:44 включает будущие review-файлы в baseline. Это ограничение воспроизводимости historical PASS, не найденная денежная ошибка. Координатору дан точечный fix; исправления не применялись и baseline не перезаписан. Отдельная проверка содержимого с начала этого review прошла.

Полный бюджет, фактические billed months, bag quantities/room-nights, signed scope ground/MRO, payroll, premium, текущая аренда и внешний donorD остаются UNKNOWN. Неизвестность не нулевой бюджет. Неравные парки и разный cost scope не доказывают оптимальность одной сети.

Completed handoff: calculation принимается с указанными ограничениями; обязательного денежного patch нет. Координатор может адресно исправить P3 provenance/check scope. Review завершён; новых входов и дополнительных проходов не ожидает. STOP.
