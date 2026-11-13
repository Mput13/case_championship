# Непокрытые расходы выбранного гибрида — условная смета

После выбранных recurring-добавок центральный остаток: **OMS 353.589 млн, DIRECT2 89.322 млн, HYBRID (11 бортов) 443.512 млн руб./модельный год**. Это steady-state после полного ввода сети, не полный 2027 год и не фактическая прибыль. Покупка/лизинг исключены из MAIN по указанию пользователя; страховка и все неподтверждённые количества — сценарии.

Одна таблица: млн руб.; low/base/high — отдельные сметы при неизменном рыночном base. Последний столбец — рыночный cautious при центральной смете; сохранён базовый парк и 12 месяцев фиксированных услуг.

| Контур | Бортов | До добавок base | Recurring base | До страховки base | Остаток low | Остаток base | Остаток high | cautious / смета base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OMS | 7 | 454.971 | 101.382 | 409.589 | 416.225 | 353.589 | 43.215 | -2 858.228 |
| GSV_MRV | 3 | 65.171 | 36.313 | 52.857 | 55.549 | 28.857 | -80.251 | -571.498 |
| AER_VOG | 3 | 78.152 | 36.497 | 65.655 | 68.519 | 41.655 | -69.203 | -566.888 |
| DIRECT2 | 4 | 143.323 | 54.000 | 121.322 | 130.068 | 89.322 | -103.833 | -1 119.575 |
| HYBRID | 11 | 598.294 | 154.782 | 531.512 | 546.533 | 443.512 | -59.179 | -3 977.204 |
| DIRECT2_10 | 3 | 177.829 | 41.713 | 160.117 | 167.718 | 136.117 | -17.616 | — |
| HYBRID10 | 10 | 632.801 | 142.495 | 570.306 | 584.184 | 490.306 | 27.039 | — |

GSV_MRV = MOW–GSV–MRV–MOW; AER_VOG = MOW–AER–VOG–MOW. Их standalone-парк по 3 борта **не складывается**: DIRECT2 пересчитан с общими MOW-ресурсами на 4 борта. Гибрид пересчитывает уникальные станции и депозит один раз. 113/568 млн из презентации — атрибуция внутри полной direct-сети; 143,323/598,294 млн здесь — только две выбранные цепочки, без произвольной замены чисел.

В центральных **154.782 млн** HYBRID: станция OMS 10.761; страховка 88.000; OMS basing 9.836; MOW parking-аналог 5.621; SLA 3.000; callout 0.201; DCS 0.155; MOW координация 0.484; допбагаж 0.133; repdesk 0.000; IRROPS пассажиров 31.880; дополнительный crew travel 4.712.

Сметные единицы и границы:

- Low: lean BoQ с дробными FTE; base: lean с ceil отдельно manager/coordinator/local_ops; high: expanded с ceil этих групп. ИТ остаётся подрядными часами. Количества BoQ — сценарии; зарплата, офис и ИТ — плановые ставки, heated storage — primary OMS за м²-месяц. Фактический штат и покрытие UNKNOWN. Полное сравнение lean/expanded и поправки — station.csv.
- Base lean: 2/2/2 FTE вместо 1,190/1,738/1,738; 400 outsourced IT часов × 801.428571 руб./ч. Поправка округления **2.372 млн/год**. High expanded: 2/6/4 FTE, 1000 IT часов; выбранный офис15/15/25 м² и storage5/5/10 м² по BoQ.
- Страховка3/8/20 млн руб./tail-year — выбранный stress, НЕ quote/рыночный диапазон. Retained7/3/3/4/11, резервы включены, при cautious не высвобождаются автоматически. Ошибочная ранняя строка budget coverage «7+3=10» заменена проверенной физикой11.
- OMS basing: 117100 ×7×12 =9,8364 млн/год исключительно как неоплаченная часть сверх ground. Месячная и часовая/суточная стоянка — альтернативы для одного tail-time; второй корзины нет. MOW тариф UNKNOWN: выбран0/1×/2× OMS-аналог на3 standalone или4 combined борта; в HYBRID10 —3. Это не тариф Москвы.
- SLA: уникальные nonbase станции ×12 месяцев: OMS8, DIRECT2 — 4, HYBRID10; MOW уже база. Ставки10/25/60 тыс./station-month. Callout300/700/1500 руб. только на0/5/20% nonbase departures. DCS10/30/80 только на0/50/100% всех departures. MOW100/300/600 только на0/100/100% новых MOW departures; фактический scope UNKNOWN.
- Допбагаж4450/service —0/1/5% OMS departures как дополнительные заказы, не пассажир/кг/мешок/каждый transfer. Repdesk1229,51/workplace-service —0/0/100% OMS departures только при дополнительном заказе, не check-in.
- IRROPS: transfer affected0,2/1/3%, local/direct0,1/0,5/1,5% — непересекающиеся поездки. Overnight25/50/100%, nights1/1/2, meals1/2/3, rebook25/50/100% из budget. RO4100 за single room-night =person-night; еда500/800/1200, rebook3000/8000/15000 — лишь incremental differential, исходная выручка снова не возвращается.
- Только OMS event-scope: transfers +50% местных OMS affected, группы40 человек; bus0/2/2 started hours и distribution0/1/1 service на ожидаемую группу, ×3430/3275. Direct-only OMS-тарифами не тарифицируется. Дробные ожидания не инвойсы; invoice_event_example.json показывает отдельное округление43 человек:2 группы,4 started hours,2 distributions; комнаты single43 при одной ночи.
- Crew stress4 человека:0/1/5% закрытых circuits (OMS departures/2 +direct departures/3): каждому1 room-night,1 person-day,2 positioning person-segments; группе2 road trips. Только дополнительные услуги сверх сохранённого BHcrew15/22 тыс.; фактического roster нет. Setup отдельно0/1/2 таких deployments на рабочий борт единожды.
- Полные ground/pax/MRO/crew не добавлены повторно. Налоговые scope сохранены: OMS primary exVAT, hotel как опубликовано, остальное planning. Никакого автоматического20/22%; дополнительный невозмещаемый налог уменьшает остаток рубль в рубль.

Launch cash и P&L (млн руб., центральная смета, base рынок):

- OMS: oneoff expense **2.004**, CAPEX **0.640**, refundable deposits **5.018**, working capital **0.514**; всего выбранный launch cash **8.176**. Steady остаток с CAPEX/3year stress **353.376**.
- DIRECT2: oneoff expense **0.719**, CAPEX **0.000**, refundable deposits **5.000**, working capital **0.302**; всего выбранный launch cash **6.022**. Steady остаток с CAPEX/3year stress **89.322**.
- HYBRID: oneoff expense **2.483**, CAPEX **0.640**, refundable deposits **5.018**, working capital **0.792**; всего выбранный launch cash **8.933**. Steady остаток с CAPEX/3year stress **443.298**.
- HYBRID10: oneoff expense **2.377**, CAPEX **0.640**, refundable deposits **5.018**, working capital **0.730**; всего выбранный launch cash **8.764**. Steady остаток с CAPEX/3year stress **490.093**.

- Launch IT:50/100/200 часов на уникальный nonOMS market × фактическая конверсия budget FTE-month×12/productivefund:583,333/801,429/1184,615 руб./час. Треугольники — по 3 market, DIRECT2 — 5, HYBRID — 11; OMS-собственный setup уже в BoQ, общие MOW/GSV/VOG один раз. Recurring IT часы не setup. MOW условно один физический аэропорт.
- Один pool security2/5/12 млн на совместный network, плюс OMS office deposit по BoQ; owned initial stock не выбран (exchange-pool design). Working capital0/15/30 дней только выбранных уже начисленных service cash, не повторный расход. Launch не вычитается ежегодно; CAPEX/3 — отдельный выбранный accounting stress, не закон. Type rating, fleet acquisition и фактический cash ramp UNKNOWN.

Ограниченный вариант10: OMS7 +MOW2working+1reserve. Перебрано625 комбинаций3..7 для двух цепочек ×двух сезонов, допустимо361; joint direct пересчитан нелинейно из source model, common OD пуст. Лучший central base: GSV_MRV summer/winter **5/5**, AER_VOG **6/6** в неделю **в каждой ориентации**. DIRECT2 BH summer/winter **137.512/137.512 ≤140**. Остаток HYBRID10 **490.306 млн**, разница к11 **46.794 млн**. Direct до добавок вырос с143,323 до177,829 млн: новый расчёт capture/spill снижает затраты быстрее выручки, а не масштабирует прежнюю прибыль. Это лучший только в заданном диапазоне и по этому критерию, не глобальный оптимум и не подтверждение расписания. Полные7/7 обеих цепочек требуют174,811 BH/нед и не помещаются в два рабочих борта.

Fuelcredit32930→3024 руб./т на ТОМ ЖЕ base physical schedule: вычитается только fuel_t×29906 из base остатка, cautious сюда не подставляется:

- OMS: burn 29940.487 т; ухудшение **895.400 млн**; остаток **-541.811 млн**.
- DIRECT2: burn 14963.331 т; ухудшение **447.493 млн**; остаток **-358.171 млн**.
- HYBRID: burn 44903.818 т; ухудшение **1 342.894 млн**; остаток **-899.382 млн**.
- HYBRID10: burn 41710.388 т; ухудшение **1 247.391 млн**; остаток **-757.085 млн**.

Финансирование — отдельные выбранные пороги0/2/4/6 млн руб./tail-month, не quotes. Для центрального HYBRID: 0 → 443.512, 2 → 179.512, 4 → -84.488, 6 → -348.488 млн остатка. Break-even финансирование **3.360 млн/tail-month**, страховая премия при прочих base-допущениях **48.319 млн/tail-year**. В thresholds.csv есть также индивидуальный порог MOW parking и запас на прочие ежегодные непокрытые расходы/невозмещаемый налог.

Файлы: results.csv —36 годовых комбинаций (30 основных +6 bounded); seasonal_results.csv — лето/зима; quantities.csv — компактные годовые unit quantities; seasonal_quantities.csv — периодные единицы; launch.csv, station.csv, included.csv, sensitivities.csv, thresholds.csv; policy.json — все выбранные правила; bounded10.json; input_manifest.json — явные зависимости, без .venv и whole-P40 hash.

Точный локальный повтор из корня worktree:

```bash
cd /home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804
context/40_hybrid_costs_20261113/network/.venv/bin/python3 -B context/40_hybrid_costs_20261113/calculation/build.py
context/40_hybrid_costs_20261113/network/.venv/bin/python3 -B context/40_hybrid_costs_20261113/calculation/verify.py
```

Проверки и их фактический итог — validation.json: денежные тождества, API convergence, отсутствие двойных станций/пассажиров, единицы, сохранённые входные хеши и byte-identical повтор в новом процессе Python3. Source/network/budget/P39/панель/презентация не изменяются. UNKNOWN actual profit/contracts сохраняется.
