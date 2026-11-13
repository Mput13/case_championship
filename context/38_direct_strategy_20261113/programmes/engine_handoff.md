# Weekly engine handoff — completed

Принимать programme_specs.json schema P38_WEEKLY_PROGRAMMES_1 и catalogue. В нём 420 financial classes / 436 календарных вариантов, legacy reference map всех60 и130 периодных supply evidence rows. Финальный месячный assembler выбирает несколько вариантов только после совместной аллокации; **не суммировать solo margins и не называть этот shortlist optimum**. Canonical primary cohort K1=11 T1 oldjobs, K2=15 B2, K3=same15+T3(D3UNKNOWN).

## Как восстановить состояния

resources[cohort].old_jobs задаёт точный KEEP bank. Для каждого programme.variants[]:
1. Применить action_map один раз по old stable ID: REMOVE исключает, SHIFT переносит все dep/arr job на shift_minutes, SWAP меняет tail всего job. RETAIN оставляет.
2. Это WITHOUT_NEW. Для REPLACE добавить chain_options[option_ids].jobs ровно один раз. Старые jobs и их изменения у W/R тождественны.
3. Генерировать ISO recurrence на реальных Monday dates с предыдущими/следующими repetitions, не range(4) и не ready0. Минуты dep/arr относятся к условному Monday UTC codec; могут быть <0/>10080. Локальные дни/блоки/overnight уже закодированы, IANA в timezones.
4. Dated key = flight_id@actual_Monday. Физическая capacity одна; SERVICE100 scenario seats, PAID_FERRY0 seats/revenue, расходы не удалять.
5. Передавать states/tails следующему joint engine; contract/month_adapter.py: evaluate_month — существующий адрес API, здесь он НЕ вызывался. Verify использует только calendar_events.

Catalogue показывает3states physical checks отдельно от8BH. calendar_checks — 1308 циклических proofs; representative_calendars — только3 witnesses, без всех шаблонов×месяцы. Начальная periodic position/ready может включать IN_AIR на UTC boundary; actual ready/release UNKNOWN. Type existing RRJ only. SJ/PD8 future entry не получает RRJ economics.

## Joint financial seam

Primary DIRECT_ONLY. Строить все retained/new directed products совместно: один cityOD/month pool, DME/ZIA физически разные и в choice один MOW. Endpoint tariffonce, shared leg seats once; through только отдельный явно условный rerun по полному calendar. Известное own RW TOF/GOJ не равно0: supply_evidence сохраняет positive periods, но не доказывает полный замкнутый KEEP на actual tail. Неполные clock/return/period inventory закрывать условным gate, не выдуманной ротацией.

Для каждого cohort/menu общий world/OD/profile/response/cost/tax definition во всех K/W/R. R−W = new incremental after joint own recapture; W−K = oldchanges; R−K = total. Общий cancellationC W/R не входит в newmargin; при разных change sets он различается. Донор/own shift, уже представленный retained/removed product delta, второй раз не вычитать. Непокрытая external own/interline loss остаётся UNKNOWN. F/D/newcrew/overnight/parking/R1/launch не0. All actual rubles/fullPnL/cash=NULL.

financial_template_key — bounded direct-only equivalence: directed physical airport/tail/kind/local weekday inventory, grouped closed path topology, actual overnight quantities, exact old action map, один cohort. Для каждого calendar variant отдельная физическая проверка. Этот key НЕ использовать как календарный или through cache. Полный cache включает timestamps/ready/resources/actions/initial positions/cost/tax/OD/profile/response/source hashes.

## Следующий хвост и pilot product

nested_allocations содержит 8 paired K2→K3 plans: master15 identical; lower ID и upper exact variant, same old action map, explicit C rule и UNKNOWN outsideD/fixed/R1 differences. Это реальные allocations, не оптимальные рубли. Требуется jointoptimum(k+1)−jointoptimum(k) в общем мире после differential resource costs.

K1→K2 core_constraint: master15 содержит4 T2 obligations вне canonical K1; фиксированные часы15 на1tail конфликтуют. Нужен самостоятельный nested lower allocation со всеми обязательствами и явными remove/retime/C/D; от raw primary cohort totals marginal value не получать. Ни одно значение marginalvalue здесь не придумано.

Проверенный mixed witness включает обе ориентации GOJ–KJA по2 commercial departures/direction/week; single1RT controls сохранены. Дальнейший pilot budget/q/net/exit/slots/crew — задача общего engine по контракту, никакой рекомендации запуска здесь нет.

## Границы поиска и проверки

search_coverage.json — exactattempts,117 source path records (103 P36 +14 required), все25 seed reasons, fixed caps, physical rejection counts и честный NOTsearched. Beam28 options/tail,14 packs/tail(6single+8mixed),40 fleet states с квотой по числу paths, максимум2 paths/tail. Focused overlays пробуют second local10/20, 7rotations и2discrete offsets. Minimalclosure union строится по всей смеси; донорское удаление oldjob не дублируется.

P36 optimistic bounds только подписанный старый scenario context; экономического pruning по фактическим рублям нет. Слабые рынки сохранены как family controls и не навязываются портфелю. Необходимые futurefinalist specs: delay30/60/120 и turn90 с carryover;294 прежних tests не повторялись. Crew/rest/FDP/slot/MRO/payload/PD8 permission actualUNKNOWN.

Sourceguard: input_manifest.json фиксирует1621protected, completedP36/P37 и readinput hashes. Не guard mutablemetadata и новые чужие outputs. verify.py реально проверяет all60/180states, allvariants3states, old uniqueness, 1/2/3+R1, real localUTC durations, weekwrap/overlap/turn, no phantom/ferry sales, UNKNOWN, reverse/truecycle/concat, financialeq≠calendarproof, nestedconstraints,27datedcalendar receipts и deterministic byte repeat. Проверять validation.json; семантика actual external market/release этим не доказывается.

Completed handoff, запись только programmes/. STOP, без ожидания других агентов.
