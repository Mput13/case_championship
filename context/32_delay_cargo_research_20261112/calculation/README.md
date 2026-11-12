# Задержки и обратный груз RW: три условных расчётных кейса

**SCOPE COMPLETE / HANDOFF READY / STOP.** Рассчитаны SVX–OMS, SVX–KUF и отдельный сценарный SVX–GOJ. Код реально исполнен; `validation.json` — PASS, две пересборки важных outputs побайтно одинаковы. Это воспроизводимое исследование порогов, а не эксплуатационный допуск, прогноз задержек или доказанная прибыль RW. Все записи — только в этой `calculation/`. Исходные пакеты, панель, context30/31 и пользовательские attachments не редактировались. Сеть, установки, новые бронирования, внешние сообщения и Git-операции не использовались.

## Три ответа пользователю

**1. Кому сильнее вредит каскад?** В одинаковом контрольном окне G390 минут у условного GOJ130/130 остаётся меньше запаса, поэтому каскад сильнее. При +120 минут к вылету нового рейса, MinTurn60: первый последующий вылет позднее на110 минут против55 у OMS и KUF; на последнем возвращении остаток95 против40 минут. Но **это вывод о заданных blocks и окне**, а не установленная эксплуатационная слабость GOJ: его exact blocks UNKNOWN. При одинаковом запасе30 минут сверх MinTurn60 перед следующим заданием все три пары дают одинаковые90 минут на первом последующем вылете. Денежный ущерб от реального срыва сравнить нельзя без affected KEEP, прав пассажиров/грузов, действительно избегаемых затрат, донора и цены восстановления. В заданных пассажирских сценариях сам дополнительный оборот ещё не имеет положительного P−KEEP до этих неизвестных затрат.

**2. Где груз может изменить launch?** Только там, где **чистый дополнительный вклад груза перекрывает дефицит всего P−KEEP**, включая собственный переток, F, внешний donor и delay, и груз проходит фактические ограничения загрузки/приёмки. Среди трёх BASE α=.25 сценариев наименьший дефицит у KUF: около713тыс.RUB/добавленный оборот, затем GOJ762тыс. и OMS897тыс. Это условный порядок конечной выборки, не рейтинг доходности RW; exact GOJ blocks и все направленные заказы/ставки неизвестны. При диагностической чистой ставке400RUB/оплачиваемый кг до неизвестных затрат нужны соответственно1781/1905/2243 оплачиваемых кг. Эти числа не заказы, не тарифы и не физические кг. В CAUTIOUS α=.25 нужны уже примерно1.66–1.98млн.RUB дополнительного чистого вклада на оборот. Ни один пакет не доказывает фактический положительный результат с грузом.

**3. Какие поля RW нужны первыми?** Сначала датированные хвост/KEEP/донор, crew и MRO: они определяют, существует ли окно и какая следующая работа действительно под угрозой. Затем направленные пассажиры/netyield/собственный переток для полного affected P−KEEP. Для проверки грузового решения параллельно нужны подтверждённые заказы и net quote/AWB, loadsheet/DOW/dispatch fuel, распределение багажа/почты/COMAT и контрактные cutoffs. Подробный приоритет ниже. Аэропортовые тонны, общий cargo channel и опубликованный парк не закрывают эти поля.

## Почему выбраны эти пары и какие источники допущены

Выбор сохранён из обоих завершённых пакетов: [schedule_data](../schedule_data/README.md) даёт направленные ориентиры OMS/KUF и отдельный конфликт GOJ; [cargo_data](../cargo_data/README.md) описывает каналы, ограничения и отсутствие направленных заказов/ставок для всех трёх. Это обоснованная данными выборка операционных кейсов, а не утверждённый top margin. TOF не включён: более сильной датированной цепочки в переданных сведениях нет; отсутствие обслуживания не заявляется. Перехода на иной маршрут и нового широкого research не было.

Прочитаны TASKS, EXPERT_PRACTICE, обе полные пользовательские ASR-расшифровки и transcript_manifest; bytes/SHA проверены. «Аэрофлот» — атрибуция пользователя и качественная практика совместного планирования/приёмки груза. Из распознавания речи не извлекались численные нормы, рейсы или параметры RW.

Применены completed [common_contract](../../31_direct_growth_research_20261112/audit/common_contract.json), [ops_inputs](../../31_direct_growth_research_20261112/ops_inputs/README.md), [source_review](../../31_direct_growth_research_20261112/source_review/README.md) и завершённый [route_economics API](../../31_direct_growth_research_20261112/route_economics/APIhandoff.json). Последний импортирован, а не переписан. Ограничения source-review не повышены до фактов спроса/допуска.

Исправления допусков отражены в `source_admission.csv`:

- Проверены все18 строк/все даты исходного paired calendar. У12 строк SVX→SVX/нулевой block — пустые placeholders, исключённые из числа рейсов. У3 физических строк UTC elapsed не равен объявленному block: KUF outbound165 вместо105, GOJ outbound250 вместо130, GOJ return10 вместо130. Часы пересобраны через IANA `zoneinfo`, исходники сохранены.
- KUF: 22:45 SVX(+5)→23:30 KUF(+4) =105 минут. Для действующего **RRJ‑95B** обратное опубликованное 08:00KUF→10:40SVX =100 минут (`svx_arr:391–395`). Отдельное LR-предложение до10:45 даёт105 минут; оно не стало B-параметром. Основной кейс и последующая цепочка B105/100. OMS B100/105 (`svx_dep:317`, `svx_arr:342`). Это аналоги опубликованного предложения, не flown и не утверждённые blocks2027.
- GOJ exact blocks оставлены UNKNOWN. Значения130/130 — только явная аналитическая точка. Слабые corrected board127/103 и конфликтующая airport extraction не получили статуса точных будущих blocks.
- Cargo S06 `ar-rmz.ru` quarantined из часов SVX: другой аэропорт/неподтверждённая идентификация. S05 Кольцово24h — контекст терминала, не RW acceptance cutoff/договор/цена. Часы Ремезова не перенесены.
- Двусмысленная исходная формула capacity заменена единым однократным учётом noncargo. B-пределы из старой копии EASA TCDS — только вариантная граница. Actual DOW/fuel/геометрия неизвестны; LR не получает нулевую ёмкость из-за пробела данных.

## Контроль задержек и физическая цепочка

Неделя01–07.02.2027 — сценарная. S1 — условный **существующий RRJ‑95B**, не регистрация и не доказанный высвобождённый самолёт. Во всех альтернативных программах тот же ресурсный контур и исходная позицияSVX. В KEEP нет новой частоты, но сохранены те же четыре последующих физических сектора с теми же UTC-временами. **G — controlled gap, не actual idle**: фактические donor/release/KEEP неизвестны. ДоH22027 новые SJ100 не используются ни рабочими, ни резервными.

Во всех основных кейсах новый вылет02.02 в18:00SVX, сценарный плановый оборот в пункте60 минут. Местные даты/offset приведены полностью в `control_flights.csv`:

| Новая пара | Новый outbound, местные часы02.02 | Новый return, местные часы02.02 | Минуты blocks |
|---|---|---|---|
| SVX–OMS | 18:00SVX(+5)→20:40OMS(+6) | 21:40OMS(+6)→22:25SVX(+5) |100/105|
| SVX–KUF | 18:00SVX(+5)→18:45KUF(+4) | 19:45KUF(+4)→22:25SVX(+5) |105/100 B|
| SVX–GOJ | 18:00SVX(+5)→18:10GOJ(+3) | 19:10GOJ(+3)→23:20SVX(+5) |130/130 **scenario**|

Основной `EQUAL_GAP_G390` фиксирует следующее задание в00:30SVX03.02, то есть через390 минут после нового вылета. Четыре последующих задания:

| Сектор | Плановые местные часы03.02 | Block | Источниковый аналог |
|---|---|---|---|
| SVX→KUF |00:30SVX→01:15KUF|105|WZ‑1033, `svx_dep:375–379`|
| KUF→SVX |02:15KUF→04:55SVX|100|WZ‑1034 B, `svx_arr:391–395`|
| SVX→OMS |06:10SVX→08:50OMS|100|WZ‑5071, `svx_dep:317`|
| OMS→SVX |09:50OMS→10:35SVX|105|WZ‑5072, `svx_arr:342`|

Flight IDs здесь ссылаются на источниковые аналоги. **Все предложенные часы и единое назначение на S1 — сценарий**, не реальная ротация WZ. После каждого замкнутого RT хвост снова вSVX; бесплатного перегона нет. Опубликованные разно-дневные строки не доказывают same tail/crew. Следующая работа SVX–REN из старого кейса не потребовалась: двусторонние KUF/OMS лучше покрыты источниками и замыкают позицию без выдуманного обратного REN block.

`EQUAL_BUFFER_B30` ставит первое KEEP задание через90 минут после планового возвращения нового RT. При MinTurn60 это одинаковый запас30 минут у всех пар; абсолютные часы между route cases различаются. При MinTurn45 запас45 минут, плюс15 на away-turn. `END_OF_DAY_NEXT0900` оставляет первое следующее задание на09:00SVX03.02. В каждом варианте P и KEEP имеют одинаковые последующие задания. Эти три разных control calendars не объявляются одним фактическим расписанием. Перенос уже обязательного00:30 на09:00 потребовал бы согласованного retiming и оценки потерянного вклада; это не бесплатная отмена задержки.

В P инъекция0/30/60/120 минут — **изолированный hold вылета NEW‑OUT**. В KEEP тот же контрольный эксперимент без нового рейса и без hold. Общая погода не моделируется. Алгоритм для каждого следующего физического сектора:

```
actual_dep = max(planned_dep,
                 previous_actual_arrival + minimum_turn,
                 known_other_ready_gate,
                 injected_hold_until_for_NEW_OUT_only)
actual_arr = actual_dep + admitted_or_explicit_scenario_block
```

Известных численных crew/MRO/slot gates нет; они остаются UNKNOWN, а не считаются эксплуатационно разрешёнными. MinTurn45/60 — диагностикаP03. 8BH/day — отдельный необходимый screen, **не FDP**. На полуночи задержка не обнуляется. Replay продолжается по всем четырём секторам до поглощения/горизонта; последний положительный остаток явно сохранён. Плановая граница горизонта — возвращение вSVX10:35; фактическая граница сдвигается вместе с остатком. При положительном остатке не заявлено дальнейшее поглощение.

| G390, MinTurn60 | Первый KEEP при+30 | при+60 | при+120 | Поздних KEEP вылетов при+120 | Последний остаток при+120 |
|---|---:|---:|---:|---:|---:|
|OMS|0|0|55|4|40|
|KUF B|0|0|55|4|40|
|GOJ130/130 scenario|20|50|110|4|95|

Все значения — минуты, не вероятности и не денежная оценка. При MinTurn45/+120 первый/последний остаток: OMS25/0, KUF25/0, GOJ80/20. Равный буфер даёт при MinTurn60/+120 у всех первый90, последний75. End-of-day/09:00 поглощает все три инъекции до первого KEEP во всех трёх случаях; crew/rest/MRO следующего утра всё равно требуют проверки.

## Восстановление, экипаж и границы

Численно доступный запас перед первым KEEP при MinTurn60: OMS/KUF65 минут, GOJ10. Чтобы полностью защитить первый KEEP от +120, нужны ещё55/55/110 минут. Их можно получить более ранним новым RT **только при реальной более ранней готовности S1/crew и допустимых слотах**; либо добавить время до последующей работы с явным retiming/донорской ценой. Ранее18:00 свободный ресурс не предполагается.

`recovery_options.csv` сравнивает324 строки альтернатив buffer, earlier new, retime following, end-of-day, reserve tail и swap crew. Нулевой остаток после retiming/end-of-day относится к **пересогласованным часам**, а не исчезновению опоздания перед прежними пассажирами. Для резерва нужен отдельный обслуженный совместимый существующий RRJ95B и квалифицированный crew вSVX. Он должен быть **flight-ready к00:30SVX03.02 =19:30UTC02.02** для исходного G390. Момент включает требуемую подготовку; нормы report/briefing не придуманы. R1 условно выполняет все четыре последующих сектора, возвращаетсяSVX, S1 остаётсяSVX; R1 не назначен одновременно на другую задачу. Наличие R1/смены фактически UNKNOWN. Для другого control calendar времена readiness пересчитаны в CSV.

Смена экипажа сама по себе не делает задержанный самолёт готовым раньше. Если aircraft — binding gate, его задержка сохраняется. При +120/MinTurn60 новый RT требует дополнительных120 минут до его планового crew release; crew на первом последующем KUF RT —55/55/110, на следующем OMS RT —40/40/95. При неизменных report/release offsets:

```
extra_required_duty = max(0, observed_release_extension - actual_remaining_duty)
extra_required_rest_window = max(0, release_delay - actual_rest_surplus)
```

`actual_remaining_duty`, `minimum_rest`, report/release и rest surplus неизвестны. Например, задержка release нового RT120 минут потребует120 дополнительных минут окна при rest surplus0, либо60 при surplus60 — это сценарные условия, не юридическая норма. Разные RT не объявлены одним допустимым crew duty.

Подтверждённый hard cutoff отсутствует, поэтому `max_injection_before_confirmed_cutoff_min=NULL`. Для иллюстрации задан **отдельный гипотетический cutoff первого KEEP = plan+30мин**. MinTurn60 допускает до95 минут исходной инъекции OMS/KUF или40 GOJ до этой гипотетической границы. Её пересечение означает потребность в восстановлении/новом разрешении. Отмена зависит от настоящего cutoff и отсутствия всех допустимых ресурсов; «при120 всегда отмена» не выводится.

Стоимость минуты задержки, `C_swap`, `C_cancel`, lost donor, цена буфера, APU/дополнительная стоянка и фактически избегаемые затраты UNKNOWN. Ground delay **не добавляет block hours**: fuel/MRO/crew block/hour за120 минут стоянки не начисляются. Это не утверждение бесплатной задержки: дополнительные ground/crew/APU затраты входят в неизвестный `C_delay` по своим драйверам.

Порог выбора резерва: `C_swap + C_position + C_donor_reserve <= L_avoided`. `L_avoided` — действительно предотвращённая потеря сценарного вклада после избегаемых расходов и дополнительных обязательств; она не равна всей выручке отменённого рейса. Для предварительного вложения в resilience: `p_BE=C_resilience/L_avoided` при `L_avoided>0`; допустимая цена при известномp — `p*L_avoided`. Здесь p и L UNKNOWN, поэтому ни ожидаемой суммы, ни численной «экономии отмены» нет.

## Пассажирский P−KEEP и пороги груза

API `evaluate_combined_programme` получает полные явные календари, не его default geometry clocks. Экономика — **весь февраль01–28.02.2027**, четыре одинаковые сценарные недели; это согласует месячный P05 pool с частотным драйвером API. Использование только первой недели при нормировке частоты на28 дней искусственно уменьшило бы частоту; поэтому месячный результат делится на4 добавленных RT. Задержки replay относятся к первой неделе, а не к четырём независимым вероятностным событиям.

KEEP каждую неделю содержит один OLD‑TARGET RT в понедельник09:00SVX и два последующих RT KUF/OMS в среду. P сохраняет их и добавляет один вторничный TARGET RT18:00. Итого32 физических сектора P и24 KEEP за месяц; **один дополнительный RT/неделю**. Если target=KUF илиOMS, их последующий RT также входит в общий target OD pool. Это явно заданные frequency/control cases, не наблюдённая частота RW. Реальные другие affected RW products/connections/донор/неизбежные платежи UNKNOWN; actual company KEEP не равен этому локальному календарю.

Один directed cityOD×month pool, общие seats, P05 prior/monthly profile/gross→net/choice и P06 allocation пересчитываются совместно в P и KEEP. Симметричная α=1 — исходный сценарий P05, не наблюдённая симметрия. α=.5/.25/0 умножает **потенциальный спрос return направления одинаково P/KEEP**, outbound остаётся тем же. Это не назначенная загрузка, не факт слабого возврата и не объявление самолёта непроданным. Собственный переток не считается новым клиентом.

P04/P05 drivers те же, что в completed API: block hours×расход топлива/MRO/crew/navigation, cycle fuel и aggregate ground/deicing на каждое физическое плечо. Это explicit historical-to-network сценарный перенос постоянных RUB2026; не контракты2027. Топливо здесь — **burn cost driver**, не departure fuel для нагрузки. NS: route support=0 и fuel credit=0 как counterfactual, не утверждение о полученных субсидиях. VAT/distribution учитываются в P05 net один раз. Непрозрачный pax cost500/650 остаётся **в F**, потому что может пересекаться с distribution; бесплатное обслуживание пассажиров не предполагается.

`passenger_turn_ledger.csv` содержит все1368 sector/comparison rows и позволяет сверить:

```
M_month = (P_net_revenue - KEEP_net_revenue) - (P_known_cost - KEEP_known_cost)
M_per_added_RT = M_month / 4
              = allocated_new_RT_contribution - retained_own_revenue_loss_per_added_RT
full_increment = M_per_added_RT + q_paid*r - F_net - D_external - C_delay - C_AWB
```

`D_external` — только donor вне already affected KEEP; включённый в KEEP донор повторно не вычитается. F — net incremental aircraft-use/base/reserve/startup/exit/непересекающийся pax cost/tax и прочие пропуски; неизвестные savings могут иметь знак. Оставшиеся обязательства нельзя автоматически считать избегаемыми. Полный финансовый результат/actual funding NULL.

Результаты на **один добавленный оборот**, BASE/α1, до F/донора/delay/fixed AWB:

| Пара | Убыток allocated return, тыс.RUB | Весь P−KEEP, тыс.RUB | Оплачиваемые кг для return при оси r100 | Для всего launch при r100 |
|---|---:|---:|---:|---:|
|OMS|266.7|−717.2|2666.7|7172.3|
|KUF B|24.5|−418.3|245.0|4183.5|
|GOJ scenario|58.5|−351.1|584.9|3511.2|

Например, «починить» allocated обратный KUF за24.5тыс.RUB **не значит** закрыть418.3тыс.RUB P−KEEP. В этом кейсе около337.1тыс.RUB/оборот — сценарная потеря выручки retained own flights; наивное суммирование новых sector margins её пропустило бы.

Слабый return α=.25, та же постановка:

| Пара | BASE дефицит whole turn, тыс.RUB | CAUTIOUS дефицит, тыс.RUB | Чистая ставка для **2000 оплачиваемых кг**, BASE / CAUTIOUS, RUB/kg |
|---|---:|---:|---:|
|OMS|897.3|1688.6|448.66 / 844.30|
|KUF B|712.6|1661.9|356.29 / 830.95|
|GOJ scenario|762.0|1978.4|381.02 / 989.19|

2000 paid kg — диагностический объём, не наличие заказов и не доказанная ёмкость. BASE/CAUTIOUS — совместные стресс-точки priors/yield/cost, не вероятности или доверительный интервал. Все24 cases в этой конечной выборке имеют отрицательный M; это не доказательство убыточности всех прямых рейсов/реальных частот RW.

Два разных порога, `r>0`:

```
kg_paid_BE_back = (allocated_back_loss + extra_back_fixed/nonoverlap_cost) / r
kg_paid_BE_launch = max(0, F_net + D_external + C_delay + C_AWB - M_per_added_RT) / r
```

В CSV отдельно показана граница **до неизвестных F/D/delay/AWB**, а actual required kg остаётсяNULL. При r≤0 положительный дефицит не закрывается. При положительном whole turn отрицательный allocated back сам по себе не делает груз поворотом launch; этот защитный случай проверен тестом. Все ставки25/50/100/200/400RUB/paid kg — **диагностические оси, не цены/спрос**. Net r уже после VAT, agent, переменного handling, дополнительного топлива и вытесненного вклада пассажиров/багажа; fixed AWB/cargo contract расход — отдельно один раз. Если груз меняет пассажирскую программу/собственный переток, нужно пересчитать joint passenger ledger, а не сохранить прежние пассажирские продажи.

## Масса, объём и оплачиваемые кг

Остаточная **реальная** ёмкость во всех cases NULL. Нужны actual aircraft DOW/configuration, dispatch departure fuel **с резервами**, arrival fuel, пассажиры/весь багаж/почта/COMAT, approved compartment floor/contour/door/distribution и ограничения конкретного рейса. Passport OEW не заменяет DOW; trip burn из P04 не заменяет departure fuel. B45880MTOW/41000MLW/40000MZFW из копии EASA issue03 не операционный допуск LR. RW4200kg/20.15m³ — маркетинговые максимумы, не свободная загрузка.

Согласованные определения:

```
Pnoncargo = cabin passenger body mass + cabin bags(if not already in standard)
           + checked bags + mail + COMAT not already in DOW
mass_ceiling = min(MZFW - DOW - Pnoncargo,
                   MTOW - DOW - FuelDep - Pnoncargo,
                   MLW - DOW - FuelArr - Pnoncargo)
hold_mass_ceiling = hold_max - checked_bags - mail_in_hold - extra_COMAT_in_hold
volume_ceiling_kg = (hold_volume - actual_bag/mail/COMAT_volume) * cargo_density
cargo_upper = max(0,min(mass_ceiling,hold_mass_ceiling,volume_ceiling_kg,
                       approved_floor_limit,geometry/distribution_limit))
```

Cabin passenger mass участвует в total mass, но не вычитается из hold4200. Cabin bags учтены один раз. Если standard mass уже включает cabin baggage, отдельный cabin term убирается; если COMAT включён в DOW, второй массы COMAT не возникает. Неизвестные floor/geometry не превращаются в безусловно неограниченные. Объём и кг не складываются.

`cargo_capacity_frontier.csv` даёт1491 строку:1008 parameter-grid,480 linked paid-BE frontiers и3 явные LR_UNKNOWN_NOT_ZERO. Это условные неравенства **для максимально допустимого DOW**, без незарегистрированной DOW точки:

```
DOW_actual <= min(40000-Pnoncargo-q_physical,
                  45880-FuelDep-Pnoncargo-q_physical,
                  41000-FuelArr-Pnoncargo-q_physical)
FuelDep_actual <= 45880-DOW_actual-Pnoncargo-q_physical
```

Оси: N25/50/75/100, тело75+cabin10kg, checked10/20kg, mail/extraCOMAT0; bag density200kg/m³, cargo100/250kg/m³; FuelDep3000/4500/6000kg уже с резервами, FuelArr1500kg. Это произвольные диагностические параметры, не нормативы RW, фактические passengers/loads/fuel или гарантии минимального резерва. Linked frontiers используют N50/100, checked20, FuelDep4500/FuelArr1500. При неизвестных действительных полях actual/approved residual остаётсяNULL даже если показанные неравенства проходят.

Пример: N100, body75+cabin10, checked20, без почты/COMAT → total noncargo10500kg, hold noncargo2000kg. Условные hold bounds —2200kg и10.15m³; при плотности груза100kg/m³ объём даёт1015 **физических** кг до всех ограничений общей массы/пола. Для1000kg физического груза и FuelDep4500/FuelArr1500 условие DOW≤28000kg; это **порог**, не оценка настоящего DOW.

Физические kg не равны paid kg. Нужны фактические packed dimensions, AWB divisor, AWB grouping, rounding, minimum charge. Только диагностическая continuous single-AWB ось:

```
q_paid = max(q_physical, volume_m3 * 1_000_000 / divisor_cm3_per_kg)
```

При divisor6000 и плотности100kg/m³ 1000 физических кг/10m³ соответствуют1666.7 оплачиваемым кг; при плотности250 те же1000kg/4m³ —1000 оплачиваемых кг. Реальный договор UNKNOWN; rounding/minimum в этой оси отсутствуют, но отдельно проверяются функцией. Ни4200×тариф, ни подмена m³ на kg не использованы.

Иллюстрация совместного порога: KUF BASE/α.25/r400 требует1781.45paid kg до пропусков. При divisor6000/плотности100 это1068.87physical kg и10.69m³. Для N100/checked20 указанная volume граница10.15m³ уже не проходит; для N50 volume15.15m³ проходит, но нужны DOW≤33181.13kg при заданном fuel, floor/geometry/приёмка/заказ и все неизвестные затраты. Это условная граница возможного решения, а не положительный результат с грузом.

## Поля RW и порядок следующего сбора

1. **Физическое окно и цена KEEP.** Даты/UTC/local, регистрации/точная модификация, все predecessor/following flight IDs и task IDs, начальная/конечная позиция, настоящее release donor, retained revenue/cost/неизбежные платежи, paid ferry и альтернативная работа. По GOJ — прежде всего согласованные направленные blocks/слоты/трасса. Fleet stock и часы «свободно на панели» недостаточны.
2. **Crew/MRO/recovery.** Crew IDs/квалификации/report/release/remaining duty/minrest/кумулятивные пределы; operator minimum turns; MRO/MEL release/windows. Где и когда flight-ready отдельный reserve/смена, на какие другие задачи он уже назначен, цена позиционирования/поддержания. Настоящие аэропортовые, slot и договорные hard cutoffs с исключениями. Это даст фактический max delay и условие отмены.
3. **Пассажирский P−KEEP.** Directed OD×дата/сезон, booked/expected paid pax/net realized yield/component bridge, затронутые own products/connections и перенос между ними; nonoverlap pax-cost500/650, реальные airport/fuel/crew/MRO agreements и aircraft-use/base/startup/exit F. Одинаковый полный future affected KEEP в P и KEEP, донор один раз.
4. **Договорный груз.** Направленные OMS/KUF/GOJ→SVX заявки по датам/регулярности/гарантиям, packed physical kg/m³/габариты/товар, AWB divisor/grouping/rounding/minimum, gross→net taxes/agent/handling/fuel/displacement/fixed fee bridge; cargo acceptance/cutoff и station/RW contract. Канал связи с RW не покупатель.
5. **Loadsheet и конечная физическая проверка.** Actual DOW, approved variant limits, passenger mass definition/cabin bags, checked baggage/mail/COMAT массы и объёмы/размещение, fuel dep с резервами и arrival, floor/door/contour/distribution. Затем пересчитать paid thresholds и всю passenger программу, если груз что-то вытесняет. Вероятности и денежные последствия срывов нужны для выбора ожидаемой resilience цены; без них остаются сценарные пороги.

## Файлы, единицы и повтор

| Файл | Назначение |
|---|---|
|`route_summary.csv`|3 выбранных route cases, границы выводов и ключевые P−KEEP/delay показатели|
|`control_flights.csv`|90 физических plan UTC/local строк, P/KEEP и3 calendars|
|`delay_events.csv`|720 событий, max gates, buffer/incoming/outgoing delay, неизменные cycles/BH|
|`delay_summary.csv`|72 paired эксперимента, перенос через ночь, terminal residual, crew окна/cutoff условия|
|`recovery_options.csv`|324 условных альтернативы, station/readiness/exclusivity/cost thresholds|
|`passenger_turn_ledger.csv`|1368 физических sector и paired turn строк, общий allocation P−KEEP|
|`cargo_break_even.csv`|120 порогов paidkg: return отдельно отwhole launch, rate grid явно diagnostic|
|`cargo_capacity_frontier.csv`|1491 условная граница массы/объёма/paid mapping, actual residualNULL|
|`decision_thresholds.csv`|48 строк whole-turn/resilience условий, неизвестные F/D/delay/цены|
|`assumptions.csv`,`source_admission.csv`|23 явных допущения и33 допуска/исправления/карантина|
|`api_requests.json`,`economic_cases.json`|точные явные месячные calendar requests и24 итоговых economic cases|
|`calculate.py`,`verify.py`|stdlib расчёт и независимые смысловые инварианты/две пересборки|
|`manifest.json`,`validation.json`|SHA256 входов/важных outputs/code/README и результат проверок|

`NULL` — неизвестное или неприменимое поле, не ноль. Деньги — постоянные RUB2026; thresholds на добавленный RT, если не указано monthly. `P_net_revenue_RUB`, `KEEP_net_revenue_RUB`, `P_known_cost_RUB`, `KEEP_known_cost_RUB` в economic cases — месячные totals; per-turn M/allocated contributions/own loss/BE — уже делённые на4. В sector ledger — одна физическая операция. Времена — elapsed minutes UTC, ISO local с offset/date отдельно; billing paidkg, physicalkg иm³ разделены.

Из workdir `/home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 context/32_delay_cargo_research_20261112/calculation/calculate.py
PYTHONDONTWRITEBYTECODE=1 python3 context/32_delay_cargo_research_20261112/calculation/verify.py
```

Стандартной библиотеки достаточно; импортируется завершённый stdlib API context31 и его pinned P05/P06. `verify.py` дважды строит все11CSV, два вспомогательных JSON иmanifest, проверяет byte-identical hashes и неизменность430 входных файлов. Проверяются18 исходных календарных строк, UTC/local/date, P/KEEP location/closed cycles, max recurrence, monotonicity/buffers/turn sensitivity, overnight residual, одинаковый buffer, conditional cutoff edge/known other gate/recovery, monthly directed pool/inventory, revenue/cost/perturn units/own donor once, отсутствие pax-cost/distribution overlap, paidkg отдельно отphysicalkg/m³, total mass/cabin/hold once, floors иLR_UNKNOWN. Произвольный DOW появляется только как **внутренняя тестовая fixture**, не как операционный input/output.

PASS означает корректность этих воспроизводимых проверок. Actual schedule/crew legality/capacity/orders/netrate/full incremental profit и финансирование не установлены. Работа расчётной роли завершена; следующая роль — отдельный независимый review, без дальнейших изменений исходных пакетов.
