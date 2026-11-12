# Условная очередь P34 — полный февраль 2027

Первая пара для проверки: **SVX-KJA**, только условно. qualified_new_routes = **0**. Это конечное сравнение 12 seed, не исчерпывающий максимум, не доказанная прибыль и не принятое решение.

**Прямой рейс** — перелёт пассажира без пересадки между двумя городами. **Треугольный оборот** — цепочка работы борта из3секторов; каждый соседний пассажирский рынок может быть прямым, но проезд через третий город не становится nonstop. Основная задача — новые пары и прямые продукты в том числе в треугольных оборотах. Челночные AER1/AER2 — только отдельные контроли, не замена всей прямой стратегии.

TOP5_CONDITIONAL_CANDIDATES ранжированы по BASE P−KEEP без неподтверждённой выручки соседних плеч; основной prior со смежной выручкой и cautious стоят рядом в CSV. Все денежные числа ниже — вклад до внешних потерь старых RW, F/резерва/setup/lease и прочих пропусков, RUB постоянных цен2026. Отрицательная граница не повод запускать пилот ради меньшего убытка.

|Условный порядок|Пара|Класс|BASE без adjacent, млн₽/месяц|CAUTIOUS, млн₽/месяц|
|---:|---|---|---:|---:|
|1|SVX-KJA|TYPE_B_RW_UNCHECKED|5.519|-0.920|
|2|SVX-IKT|TYPE_B_RW_UNCHECKED|4.781|-4.176|
|3|TJM-MRV|TYPE_B_RW_UNCHECKED|-3.089|-5.166|
|4|OMS-PEE|TYPE_A_UNCONFIRMED|-3.164|-5.059|
|5|CEK-MRV|TYPE_B_RW_UNCHECKED|-3.250|-4.497|

Четыре GOJ–KJA/GOJ–TOF/KUF–TOF/OMS–PEE остаются UNKNOWN: тип A не подтверждён. Шесть TJM–MRV/CEK–MRV/SVX–KJA/SVX–IKT/SVX–VVO/SVX–KHV имеют COMPETITOR_NONSTOP_RW_NOT_CONFIRMED: тип B с непроверенным собственным RW. PEE–TOF/OMS–REN сохранены в low evidence queue. Подтверждённых частотных comparator из этих12 нет: при подтверждении собственного nonstop перевести туда. История SVX–KJA его не исключает; relaunch unresolved.

Период **01–28Feb2027**, Tue02/09/16/23 и Fri05/12/19/26. Месяц и /4 — единственные агрегации; без 52/48. P31 choice_bundle на реальном7day fixture даёт0.25/week для1вылета;4вылета за полный28day февраль дают1/week. Спрос prorate ровно один раз. Это ограниченный workaround, частичные месяцы и переходы границ новый расчёт отвергает.

S1 KEEP: один условно высвобождаемый действующий RRJ-95B E1 в SVX,100 сценарных кресел, отдельно R1 без плановых рейсов. Tue OMS18:00SVX→20:40OMS;21:40OMS→22:25SVX. Fri KUF18:00SVX→18:45KUF;19:45KUF→22:25SVX. Все часы SCENARIO. После каждого окна — одинаковые4 FOLLOW из P32 SVX-OMS/EQUAL_BUFFER_B30/KEEP: KUF23:55SVX→00:40KUF;01:40KUF→04:20SVX; OMS05:35SVX→08:15OMS;09:15OMS→10:00SVX. Пятничный шаблон сдвинут на3дня, затем повторён на7дней. В P/KEEP эти даты/времена совпадают. Actual KEEP/Dactual/регистрация/резерв-release неизвестны.

P−KEEP содержит потерю донорской net revenue и избегаемые P04 fuel/cycle/MRO/blockcrew/navigation/ground/deice один раз. programme_ledger.csv разделяет donor/retained/newpair/adjacent по обеим сетям. Неизбежная lease/fixedcrew не вычитается как избегаемый донор. Реальные избегаемость/ставки UNKNOWN. Внешний donor/F/собственные through/partner продажи остаются NULL и отдельными порогами. KEEP−KEEP=0, бизнес KEEP не нулевой.

Вне SVX обе ориентации SVX–A–B–SVX Tue / SVX–B–A–SVX Fri дают6 проектных секторов и1 RT самой пары в неделю. К ним добавляются8 FOLLOW секторов. Для SVX–X — TueRT, FriKEEP и те же8FOLLOW. Никаких бесплатных новых баз/самолёто-дней или обрезки плеч. Короткие SVX–CEK/TJM/PEE — платные ferry с0выручкой в main; noadj stress выключает и остальную недоказанную project adjacent выручку, сохраняя каждый расход. Услуги остаются scenario, позиционирование E1 к исходной SVX/ночёвка/crew вне явной цепи требуют отдельного F; их фактическая цена NULL.

Полный календарь выдаёт диагностику8BH. Новый cost_only_calendar пропускает в совместную экономику только календари, где единственный класс ошибок — эта диагностика; все исходные ошибки и полные рейсы сохранены, resource screen остаётся failed/ops queue. Порог8BH не поднят; это не FDP и не допуск. Пересечение с FOLLOW/отрицательный turn/позиция дают NULLэкономику и INVALID_D0, а потери дополнительно снятых retained заданий UNKNOWN. SVX–VVO/KHV не получают бесплатный перенос FOLLOW/дополнительный день.

Три конкретные программы для предметной проверки (geometry/block сценарии, не «выполнимо»):

- **SVX-KJA**: SVX 2027-02-02T07:00:00+05:00 → KJA 2027-02-02T12:20:00+07:00 (200min); KJA 2027-02-02T13:20:00+07:00 → SVX 2027-02-02T14:40:00+05:00 (200min). UTC, полные даты и все FOLLOW — flights.csv. Пассажир — только гипотеза endpoint VFR/business, MRV также лечение/отдых; наблюдений цели/объёма нет.
- **SVX-IKT**: SVX 2027-02-02T07:00:00+05:00 → IKT 2027-02-02T14:37:00+08:00 (277min); IKT 2027-02-02T15:37:00+08:00 → SVX 2027-02-02T17:14:00+05:00 (277min). UTC, полные даты и все FOLLOW — flights.csv. Пассажир — только гипотеза endpoint VFR/business, MRV также лечение/отдых; наблюдений цели/объёма нет.
- **TJM-MRV**: SVX 2027-02-02T07:00:00+05:00 → TJM 2027-02-02T07:55:00+05:00 (55min); TJM 2027-02-02T08:55:00+05:00 → MRV 2027-02-02T10:31:00+03:00 (216min); MRV 2027-02-02T11:31:00+03:00 → SVX 2027-02-02T16:45:00+05:00 (194min); SVX 2027-02-05T07:00:00+05:00 → MRV 2027-02-05T08:14:00+03:00 (194min); MRV 2027-02-05T09:14:00+03:00 → TJM 2027-02-05T14:50:00+05:00 (216min); TJM 2027-02-05T15:50:00+05:00 → SVX 2027-02-05T16:45:00+05:00 (55min). UTC, полные даты и все FOLLOW — flights.csv. Пассажир — только гипотеза endpoint VFR/business, MRV также лечение/отдых; наблюдений цели/объёма нет.

Для треугольных программ shock30/60/120 на NEW_PAIR Tue и Fri раздельно. В SVXRT/AER1 новый RT только Tue, поэтому FridayNEWPAIR отсутствует: пятничный shock отдельно помечен FRI_KEEP_DONOR_CONTROL_NO_NEW_PAIR и относится к сохранённому донору, не выдуманному новому плечу. delay_events.csv явно называет target_id/target_group и адаптацию к P32 NEW-OUT, содержит D0 и план/факт UTC/local. Оба направления каждого нового RT/треугольника проверены раздельно. Полночь не сбрасывает задержку. Поздние FOLLOW перечислены в model_checks.json; AIRCRAFT_ONLY_ABSORB120 в break_even.csv даёт буфер/maxremainingblock. Удержание на земле не добавлено к blockhourcost. Вероятность, рубль/минута, автоотмена, crewremaining и extraресурс UNKNOWN; R1 не бесплатная capacity.

AER завершение P33: 1TueRT+FriKEEP и2RT на том же E1/R1. Main14:00SVX→15:30AER,16:30AER→22:00SVX,210/210+60; UTC09:00→12:30/13:30→17:00. Исходный P33давал330/150, его FOLLOW не использованы. Это исправленная каноническая scenario-таблица в flights.csv, не observed block/dispatch. AER_window_comparison.csv:07/14/21SVX, следующая KEEP и0/30/60/120. 21:00не помещается, D0 INVALID. Удобство/неудобство и слоты по источникам UNKNOWN. Максимальный дисконт — только подписанная модельная граница P05 при фиксированных q/cost, отрицательное значение требует повышения net; expert5000 не прогноз, actualquoteddiscount NULL.

Дополнительно ровно один готовый AER-треугольник P31: **TRI:SVX-AER-MRV** из route_economics/patterns.json. Tue SVX–AER–MRV–SVX, Fri SVX–MRV–AER–SVX, старт07:00SVX, все6секторов, те же E1/R1, оба донора и8FOLLOW. Это единственный AER-треугольник в готовом P31 наборе: KUF/UFA не изобретались. Все три adjacentOD имеют P05prior/costscreen, pairedblock/вариант не доказаны. Обратная ориентация и новые даты/часы явно SCENARIO; исходные деньги не перенесены. programme_comparison.csv сравнивает base/cautious и стресс без SVX-adjacent выручки, AER_triangle_admission.json объясняет admission. Эта программа не входит в12илиtop5 и не объявлена лучше.

Полная исходная author triangle reference сохранена отдельно: **author_triangle_reference.csv** содержит все96 directed строк двух составов base/cautious, по8треугольников в каждом. **author_reference_status.json** сохраняет исходный author resource (8бортов BASE,7 CAUTIOUS из network_summary), полный объём204/144сектора/неделю и отдельный P03 hours-only proxy9/8рабочих+условный резерв. Эти ресурсные оценки имеют разные определения; фактические хвосты/crew/MRO и даты UNKNOWN. Никакой обрезки подE1 или переноса годовых авторских денег вS1 нет; исходные годовые суммы — только подписанная historical scenario reference. Недостающие taildays/retained lossbudget UNKNOWN. Основная сеть автора сохранена, челночный AER её не подменяет.

Экономические границы в break_even.csv — совместная прямая n_a*q_a+n_b*q_b=K, симметричная точка помечена, дополнительно q_a|q_b и обратные оси. Netfare threshold фиксирует q/прочие costs и не предсказывает эластичность. Реальный jointfareoverride проверен: gross/net actualproducts меняются на0.9 и choice пересчитывается; screen(gross_override) не используется. BASE явное насыщение: число saturated_flights в programme_comparison.csv и ограничения P06; это не доказательство спроса. OMS–PEE использует gravity extrapolation, остальные — P05 prior, не прогнозы.

Общие directed cityOD monthly pools и физические seats P06 не дублируются. Retained OLD_RW включены одинаково и их сдвиг учтён joint. Уникальные новые клиенты RW не равны новым посадкам. Неизмеренные own through/partner клиенты не равны0: Loutside0/25/50% — только отдельная диагностика, исключает уже включённые donor/retained потери. Cleanqnew: n*qnew = K+Σm*(oldnet−newnet), qnew+m≤seats; oldnet в диагностике=P05 newnet, actual NULL, backfill отсутствует. Нельзя вычитать этих же доноров снова или считать migrated новыми клиентами.

Grossquote≠net: P05 gross/(1+VAT)*(1-distribution), BASE VAT0 только допустимый regional scenario и3%, cautious10%/8%. Fees/VAT повторно не вычитаются. 500/650 только подписанный nonoverlap stress на разность occupiedsegments; подтверждение непересечения invoice-level необходимо. Mainfuel/routesupport/cargo0. Cargo — необходимый денежный netcontribution без подтверждённых заказов/ставок/остатка payload. FactualF/setup/lease/reserve/cash/fullPnL NULL; сравнить фактическую прибыльность нельзя.

Порог смены места/KEEP в donor_rank_flip.csv: внешний donor/F, netyield, migration, adjacent, period, BH и payload. Это одноосные границы при фиксированных остальных элементах, не вероятности. Общие неизменные пропуски не переворачивают ранг, различающиеся могут. Даже положительный scoped вклад не является основанием запуска без admission gates.

Функции и области: P31 route_economics.evaluate_combined_programme пересчитывает P и KEEP совместно; P05 annual/prior/monthly_profile/fare/choice задают сценарный спрос/цену; P06 engine.choice.allocate распределяет одни directed city pools по products с общей physical seat capacity. P31 ops_inputs.calendar_engine.generate строит полный датированный календарь/UTC turns/позицию/cycles/BH; новый cost_only_calendar сохраняет sole8BH fail для стоимостной диагностики. P32 flight/replay распространяет один hold по max(plan,ready,othergate,shock); новый delay_rows явно связывает target. thresholds выводит линейные оси, не rerun choice. Ни одна функция не доказывает observed OD, прибыль или dispatch.

P08 доступен, P08I по реальным именам не найден. P08/P09 не калибруют observedOD/netyield. Свежие rw_routes_now/network побайтно равны P31. Canonical input admission и исходники с локаторами: admission.csv и соседние source_recovery_*; сырые research_* исключены. Не требуется новый внешний поиск.

Воспроизведение и meaningful checks одной командой из корня:
```sh
python3 -B context/34_new_direct_top5_20261112/calculation/verify.py
```
verify запускает calculate.py реально дважды, проверяет байты outputs, frequency fixture, полную физику/cycles/две стороны/UTC, OD/seat, налоги/fees, jointfare, donoronce/migration, nullable неизвестные, D0/shocks и1190protected содержательно. HEAD не фиксируется, trackedtotal может превышать1190. Никаких legacy build/git/сети/записи вне calculation. После поставки STOP до отдельного независимого review.
