# MR12: распределение кресел и конечные наборы

**A — APPROVE_SCOPED. B — APPROVE_SCOPED. P1: 0; P2: 0.** Есть одно неблокирующее замечание P3 к точности текста, не к расчёту. Владелец не исправлялся.

Проверяемый subject: `ba9f6b85b4f8c9847948ae428ef3fbcfca9e2009:context/23_night_run_20261110/methods/`. Подготовленный root: `c43e58569f3fc561bb7d0dd0806995b718ef01a9`. Все входы прочитаны через exact `git show <commit>:<path>`; live-папки владельцев не использовались. Рабочая ветка: `research/night-allocation-variants-review-20261110`. Пакет завершён до среза 08:30 МСК 10.11.2026.

## Замечание

**MR12-O01, P3, неблокирующее.** `methods/decision_conditions.md:25` указывает 1786,197 сегмента и 542,443 трансферной поездки для UFA8/C/base при максимуме сегментов. Независимый расчёт и exact `methods/runs/allocation_v1/summary.csv:37` дают 1786,193148851081 сегмента и 542,4439973311994 трансферной поездки. До трёх знаков следует написать **1786,193** и **542,444**. Минимальная правка — только эти два числа. Оптимум, разности +56,304 и −90 087,03 RUB, ограничения и вывод о разных целях не меняются. Размер ошибки не обосновывает P1/P2 или удержание численных результатов.

## Независимый расчёт A

Восстановлены все 16 случаев: четыре программы C × base/cautious, три покрытые программы N × base/cautious и два отдельных C×3/base для H_UFA_4/H_UFA_8. N для D_previous_best8 не добавлен. Годовой proxy N пересчитан непосредственно из закреплённого `demand_pairs.csv` с выбором исходного поля и делением на 104; он не назван наблюдённым недельным OD.

Отдельный код [reproduce.py](reproduce.py) не импортирует модули владельца для независимых расчётов. Он использует source itinerary, flights, capacity, configuration и assumptions, восстанавливает порядок исходного local-first и присоединяет его по полным ключам. Результат: [case_register.csv](case_register.csv), [coefficients.csv](coefficients.csv), [constraint_matrix_sparse.csv](constraint_matrix_sparse.csv). В регистре сохранены candidate, source profile/network/commit, scenario/recipe/scale, input set, период, валюта и денежное определение.

Для offer i, направленного рынка m и физического плеча l:

`0 ≤ x_i ≤ u_i; Σ_(i использует l) x_i ≤ K_l; Σ_(i принадлежит m) x_i ≤ D_m`.

`u_i = D_m × peak × (1 − exp(−f_m/3)) × transfer_factor / f_m`.

Peak: 0,45/0,30 для base/cautious; transfer_factor: 0,65 для пересадки, 1 для прямого itinerary. Эти предпосылки проверены на pinned source replay, а не предложены как эмпирическая модель. Прямой и обратный OD имеют разные строки ограничений. Один itinerary содержит одну сквозную выручку; каждое его плечо расходует одно кресло. IDs проверены вместе с profile/network/scenario; состав и даты плеч, вместимость и переменные расходы не менялись.

Коэффициент денежной цели:

`w_i = fare_i − can_i × oldfare_i − nlegs_i × pax_cost + can_i × oldsegments_m × pax_cost`.

Издержки всех flown legs остаются постоянным вычитаемым `flight_cost`, в том числе при уменьшении продаж. Они независимо пересчитаны из source block_minutes и рецепта топлива/uplift/MRO/crew/navigation/airport/deicing. Опыт не разрешает снять рейс, освободить борт, изменить fare или desired quota.

### Migration gate

Для любого допустимого x выполняется `x_i ≤ min(u_i, K_l для всех l itinerary i)`. Поэтому `U_m = Σ_i min(u_i, leg bottleneck_i)` ограничивает продажи рынка **на всём feasible polytope**. Если известный положительный cap `K_old ≥ can × U_m`, он не может связать ни одно допустимое распределение. В этом случае migrated journeys расходуют один старый direct segment; saved old pax costs равны `can × x × pax_cost`.

В [migration_gate_checks.csv](migration_gate_checks.csv) независимо проверены все **376** directed market/case rows: 32 с положительным known direct cap и 344 UNKNOWN. На этих данных known zero не встречается. Для UNKNOWN, а также для отдельно проверенного synthetic known zero, direct migrated = 0, unverified migrated = can×x, saved old segments = 2×can×x согласно исходному сценарию. UNKNOWN не превращён в доказанное отсутствие собственной миграции.

[migration_kink_counterexample.json](migration_kink_counterexample.json) задаёт K_old=5, can=0,6 и допустимые продажи до 20: kink при x=8⅓ меняет наклон saved old segments с 0,6 на 1,2. Одним коэффициентом такую формулу описать нельзя. Дополнительный in-memory probe exact owner code уменьшил положительные source caps до 0,001; получил отказ:

`AssertionError: ('binding migration kink; LP held', 'D_SVX8|base|C|1.0', ('KUF', 'SVX'), 15.30730922901538, 0.001)`.

Исходные Git bytes не менялись. Отказ проверен фактическим запуском, а не только чтением assert.

### Первичные и вторичные сертификаты

Для каждой из трёх целей проверены опубликованный primal по offer, independently reconstructed objective, все OD/leg/upper/lower ограничения, неотрицательность shadows и reduced slacks. Проверена dual formula `bᵀy + uᵀμ` с **верхними границами offers**, условие `Aᵀy+μ ≥ c`, равенство primal/dual и абсолютная complementarity. Все **48** задач прошли. Оптимум проверен также отдельной сборкой LP через установленный `scipy.optimize.linprog(method='highs-ds')` с другой нумерацией столбцов. Это отдельный код и матрица, но тот же backend HiGHS; иной независимый solver implementation не заявляется.

Для **32** вторичных задач построена строка `−vᵀx ≤ −primary_optimum + 10⁻⁸`, проверены сохранение первой цели, primal и новая dual constraint, включая её shadow и RHS в dual value. Сертификаты для secondary созданы этим reviewer: владелец экспортирует итоговое secondary dual value, а не все secondary shadows. Собственные primary shadows также сохранены отдельно. Материалы: [primary_checks.csv](primary_checks.csv), [oracle_primary_constraint_duals.csv](oracle_primary_constraint_duals.csv), [oracle_primary_offer_certificates.csv](oracle_primary_offer_certificates.csv), [secondary_checks.csv](secondary_checks.csv), [secondary_constraint_duals.csv](secondary_constraint_duals.csv), [secondary_offer_certificates.csv](secondary_offer_certificates.csv).

Численная точность: абсолютная допустимая ошибка pax/row 2×10⁻⁶, денег 10⁻⁴ RUB, суммы абсолютных complementarity terms 5×10⁻⁴. Tie допускает отклонение первой цели на 10⁻⁸; при конечных денежных коэффициентах оно не должно ошибочно считаться точной алгебраической ничьей. Фактический максимальный primary gap ≈1,00004×10⁻⁸ единицы цели, secondary gap ≤3,73×10⁻⁹ RUB. Ошибка реконструированного contribution ≤1,12×10⁻⁸ RUB. Это существенно точнее опубликованных 0,001 поездки и 0,01 RUB; значения не округлялись перед проверкой. Полные residuals — [independent_checks.json](independent_checks.json).

### Reference и границы результата

Исходный local-first восстановлен на тех же inputs и проверен как feasible reference во всех 16 случаях. Для C/unit-scale дополнительно совпали все исходные itinerary sales и восемь source comparison results; known-direct и unverified migration сохранены раздельно. Денежный оптимум нигде не хуже reference в указанном допуске.

Supply bound MR07 проверен только на перечисленных source products exact profile/network/scenario: расслаблены demand/offer caps, own migration установлена в оптимистический ноль, физическая вместимость сохранена. Неотрицательные per-leg shadows покрывают margin каждого разрешённого itinerary; результат совпал с source bound и ограничил все 48 решений. Из этого не следует bound на произвольные новые продукты, цены, расписание или реальный рынок. Старые alpha/scale thresholds local-first на LP не переносились.

Ключевой пример, UFA8/C/base, из [key_counterexample.json](key_counterexample.json):

| Величина | Максимум вклада | Максимум сегментов, затем вклад |
|---|---:|---:|
| Конечные journeys | 1243,749152 | 1243,749152 |
| Passenger segments | 1729,888757 | 1786,193149 |
| Transfer journeys | 486,139606 | 542,443997 |
| Source own-migration | 62,187458 | 62,187458 |
| Из неё known direct | 0 | 0 |
| Из неё unverified | 62,187458 | 62,187458 |
| Net-new RW journeys | 1181,561694 | 1181,561694 |
| Contribution, RUB/model week | −9 425 307,433675 | −9 515 394,460040 |

Разности: **+56,3043914776 segments; −90 087,0263641 RUB; journeys без изменения** в машинной точности. Для C/base improvement UFA4 = 42 361,74601196 RUB, UFA8 = 71 612,45391840 RUB. Все 42 unit-scale решения C/N остаются отрицательными. C×3 — отдельные шесть objective cases; максимум вклада UFA4 +1 201 661,19 и UFA8 +442 817,78 RUB до исключённых расходов. Это сценарий, не измеренный спрос и не полный положительный бюджет. Выбор objective остаётся OPEN_DECISION.

## Конечные наборы и бюджет B

Все 15 непустых subsets четырёх source programs независимо построены из pinned context21 calendar flights, а не из опубликованного `unique_model_airport_pairs`. Дедупликация использует unordered airport-code endpoint pair; directed OD, частота и dated flight остаются разными единицами. Рабочие метки получены из уникальных aircraft labels каждого исходного календаря и сверены с `active_allocated`; суммирование компонентов не является новой совместной tail optimization.

[independent_unions.csv](independent_unions.csv), [independent_pair_members.csv](independent_pair_members.csv) и [independent_dated_legs.csv](independent_dated_legs.csv) подтверждают **204 pair-member rows**, все namespaced source flight IDs, source profile/network, даты и **640** вхождений dated legs во всех subsets. MOW не подставлен вместо аэропорта.

| Набор | Уникальные пары | Сумма рабочих меток | Необходимые совместные gates |
|---|---:|---:|---|
| D_SVX8 | 8 | 1 | PASS |
| D_previous_best8 | 8 | 2 | PASS |
| H_UFA_8 | 8 | 4 | PASS |
| D_SVX8 + H_UFA_4 | 12 | 3 | PASS |
| D_previous_best8 + H_UFA_4 | 12 | 4 | PASS |
| H_UFA_4 + H_UFA_8 | 8 | 6 | FAIL по рабочему потолку |

Итого ровно **пять** наборов проходят `8≤pairs≤12` и `working≤4`. У H4+H8 удалены четыре дублирующие пары, но дополнительные рейсы/кресла не удалены. Общий резерв один и база UFA одна — явные предпосылки. Реальный доступный ресурс, поставки и operating acceptance не установлены.

Все **90** строк budget_conditions однозначно присоединены к exact `portfolio_v2/summary.csv` по portfolio/scenario/capture_law. Source C совпал без изменения значения, money input set и периода `CIRI_NET_RUB_WEEK_20261207_13`; дополнительно проверено его денежное тождество из пяти ledger terms. Это сохраняет source local-first и три заданных capture laws, а не заменяет их новым LP.

`ΔPnL = C + D_external − F_incremental − B_incremental − S_excluded − L_recognized`.

В [independent_budget_conditions.csv](independent_budget_conditions.csv) подтверждены отрицательные C всех 90 вариантов, intercept `−C`, NULL full_PnL/peak_cash, условные n/b и money grain. Граница проверена с нулевыми и ненулевыми неотрицательными excluded costs при donor ниже, ровно на и выше порога. При D_external=0 и неотрицательных excluded costs ΔPnL строго отрицателен. Порог даёт ΔPnL=0 при равенстве, положительный результат требует его превышения. У D_previous_best8+H_UFA_4/base/COUNT_ALL_OFFERS intercept = **9 646 174,751268085 RUB/model week**, плюс excluded costs; подтверждённого donor gain нет.

D_external может содержать только именованное изменение **вне уже включённой** foregone RW revenue / saved old passenger cost. Повторно вычитать ту же старую выручку, её маржу или ту же потерю ресурса нельзя. Неизбежная фиксированная плата, одинаковая в KEEP и действии, имеет incremental delta 0. Признание разового запуска требует периода и политики, не бессрочной weekly charge. Депозиты, capex, финансирование и кассовый календарь рассматриваются отдельно от начисленной PnL; возвратный депозит не становится расходом автоматически. Иллюстрации сохранены в [budget_scope_probes.json](budget_scope_probes.json).

KEEPΔ0 — только разность с самим собой, не прибыль компании. Cash fixtures 1 млн / 1,8 млн / 6,078 млн не приняты как фактический резерв и здесь не пересчитывались как новый cancellation audit. Условие будущего рабочего парка не гарантирует поставку. Ни одного выбора сети, донорского дохода, вероятности спроса/«Ковра», full budget или launch approval этим review не добавлено.

## Сохранность и воспроизводимость

Лично сравнены **327** старых файлов exact v5 `f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9` с subject: 250 inputs + 70 runs = 320, плюс 7 analysis. Все bytes идентичны. [v5_preservation_checks.csv](v5_preservation_checks.csv) содержит каждый путь, SHA256 и размер; [source_origin_checks.json](source_origin_checks.json) отдельно связывает шесть ключевых numeric/calendar/config inputs с original `93fa5cf4a10ab67e05c93d19fc5375fc58ef9299`.

Временная копия только нужных source files внутри собственного scope использована для дополнительного replay владельца. Все **15** outputs (8 allocation, 4 final variants, 3 admission_v2) воспроизвелись побайтно: [owner_replay_checks.json](owner_replay_checks.json). Это дополнение к независимому расчёту, не его oracle. Зависимости не устанавливались; процессы replay завершены, временная копия удалена. UI/browser/Site не открывались и не менялись.

Предыдущие MR09/MR10 использованы лишь как обозначенные supplied scoped evidence в новой admission projection. Их substantive review не повторялся. В original admission_v1 остаются original CHANGES; four delay HOLD и clock holds не повышены. MR11 cancellation и frontier `519998…` не проверялись и не расширены; эти claims в decision_conditions.md:79–93 находятся вне данного APPROVE_SCOPED. Preservation/replay admission_v2 не означает принятия всех её inherited claims.

Пройденные ступени ограничены закреплёнными Git inputs: RAW_HASH_VERIFIED, JOIN_CHECKED для source IDs, AUTHOR_REPLAY_MATCHED для указанного replay, CONSERVATION_PASS и CONDITIONAL_ECONOMICS_CHECKED для условной LP/бюджетной алгебры. SOURCE_SUPPORTED как подтверждение реального спроса/ресурса не заявляется. Входы, ограничения и точные команды: [source_manifest.json](source_manifest.json), [commands.md](commands.md), [handoff.json](handoff.json).
