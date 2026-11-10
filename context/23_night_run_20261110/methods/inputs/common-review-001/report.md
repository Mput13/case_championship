# MR08: независимая проверка общего сравнения

**APPROVE_SCOPED** для demand recipe, арифметики affine-границ и qualified adapter на exact methods `abb1c76254d2d4e3cf9edd5c345b9cdb224f6abe`. Новых P1/P2 в этом объёме не обнаружено. **Primary source lineage остаётся HOLD** по `SJR-P2-001`: 129 SVX publication rows / 28 cards / 58 addendum mappings. SOURCE_SUPPORTED, наблюдённый OD, полный бюджет, выбор стратегии и разрешение запуска этим review не принимаются.

Проверка выполнена новым Sol 6.1 xhigh в prepared checkout на root `f1774e1f66a9483fb618ca6003abd9dc4d8563e1`. Все исходники и данные получены через `git show exactSHA:path`. Рабочая версия methods не использовалась. Frozen originals сохранены. Предыдущие MR05, MR07 и model_repair review прочитаны только для границ приёмки; их verdict и scope не изменены.

## Что проверено

Самостоятельный allocator в [independent_review.py](independent_review.py) воспроизводит frequency capture, local-first, общий направленный рынок, расход каждого плеча, собственную миграцию и пять денежных статей. Авторские demand/boundary функции и main/check_package не исполнялись. Для проверки заявленных мутаций отдельно AST-загружены только `key`, `near`, `qualify_flight_money`, `validate_tables` из exact adapter; это явно отмечено в machine evidence и не служит независимым численным oracle.

| Объём | Независимая проверка |
|---|---|
| 8 context21 baseline | Все доступные численные summary-поля; максимум расхождения 1.12×10⁻⁸ RUB |
| 224 baseline sales | Продажи, сегменты, обе категории миграции, тариф и деньги; численные значения совпали |
| 160 flight-scenario rows | Полные множества IDs, уникальность, block time, отдельная формула стоимости и сумма |
| 72 demand mappings | C и выбранный годовой N-field, /104, coverage, period и method |
| 84 common summary | Все доступные численные поля и фиксированная контекстная метаинформация; максимум численного расхождения 3.73×10⁻⁹ |
| 384 unit-scale itineraries | C/N по трём программам и двум сценариям; значения совпали |
| 18 кривых / 151 affine-участок | Собственная декомпозиция, значения, наклоны, экстремумы, первые нули, обе стороны границ и насыщенный хвост |
| 160 qualified money rows | Единственный full leg-key и summary; заполнение metadata, сохранность amounts и остальных строк |
| 4 mutation probes + 2 anchor probes | Все ожидаемые отклонения воспроизведены |
| 176 publication joins | Incidence по реально экспортированным направленным OD; source HOLD сохранён |

Всего — 36 593 численных и семантических assertion checks; это число проверок, не оценка качества или вероятность корректности. 66 прочитанных immutable Git blobs перечислены с SHA256 и grain в [source_manifest.json](source_manifest.json). Хеши доказывают тождество байтов этих входов. Численные выводы основаны на собственных расчётах. Результаты проверок — [independent_results.json](independent_results.json).

## Рецепты спроса и неизменность остальных входов

`C` — исходные направленные недельные bands context21. `N` — выбранный численный annual pair scale из frozen `demand_pairs.csv` Анастасии@`2f03b693a62c219e9475fcd1e26295039f6a49d7`, делённый на 2 направления и 52 недели **в обоих сценариях**. В base берётся `observed`, если он задан и coverage не `airline_group`, иначе `pax_base`; в cautious — `pax_cautious`. Это соответствует выбору в `src/network_model.py:56` исходного автора. Конверсия /104 явно сценарная: авторские 48 недель cautious не импортируются.

Годовой масштаб остаётся сегментным/модельным proxy с исходной неопределённостью охвата; он не превращён в наблюдённый конечный OD зимней недели. Годовые деньги Анастасии не смешиваются с недельным вкладом Цири. C/N, нормативный выбор рецепта и все closed parameters сохраняют статус AGENT_PROPOSAL / OPEN_DECISION.

Байтово сопоставлены с upstream exact93fa исходные comparison, sales, capacity, flights и configuration, а с exact2f03 — demand_pairs и network_model. Проверены все 72 изменённых demand input; численное расхождение с опубликованным mapping равно нулю. Все остальные расчётные входы одинаковы: dated support 7–13 декабря 2026, тарифы, costs, номинальные кресла, migration shares/caps и local-first. `D_previous_best8` исключён только из C/N опыта из-за шести отсутствующих ZIA-пар. MOW→ZIA не выполнено; отсутствующий спрос не заменён нулём. Список — [independent_exclusions.json](independent_exclusions.json).

Ресурсный потолок остаётся 4 working + 1 reserve. Фактическая модельная аллокация различается и сохранена: D_SVX8 — 1 working, D_previous_best8 — 2, H_UFA_4 — 2, H_UFA_8 — 4. Использование всего потолка не навязано. [independent_resource_scope.csv](independent_resource_scope.csv) хранит часы и распределение. Это модельный календарь, без dispatch/resource clearance.

Независимый replay сначала рассчитывает желаемый capture `D·q/f`, затем берёт минимум с остатком каждого плеча, затем расходует кресла и направленный migration cap. Одна пересадочная поездка расходует два кресло-сегмента, тариф начисляется один раз. Известная прямая миграция ограничивается собственным направленным инвентарём; остаток остаётся unverified connecting scenario, экономится соответствующее число старых пассажиро-сегментов. Продажи всех продуктов данного OD ограничены одним D. Между альтернативами кресла и migration не переносятся; это взаимоисключающие программы, их продажи не суммируются как совместная сеть.

Ссылки в exact methods: `common_demand.py:46` (подготовка), `common_demand.py:68` (allocation и migration), `common_demand.py:141` (пропуски ZIA), `common_demand.py:148` (N-field и /104). В frozen author `build_team_comparison.py:313` явно заданы bands, `old_rw_segments=2`, transfer competition factor .65; `build_conditional_decision.py:22` задаёт общий band experiment и local peak. Эти правила здесь проверены как заданные предпосылки, без эмпирической приёмки.

## Affine-границы

Собственный алгоритм выбирает внутреннюю точку интервала, записывает каждое неравенство выбранной ветви `min`, пересекает их и получает область действия полного пути allocation. Затем покрывает оставшиеся промежутки. Это даёт независимый сертификат всех 151 участков, а не повторение авторского обхода от левой границы. На каждом участке независимо проверены значения и наклоны; выполнены численные проверки концов, середины, детерминированной случайной точки и обеих сторон breakpoints. Дополнительно каждый авторский участок проверен в пяти точках и на пересечениях с собственными сертифицированными участками.

Получено `α=0.6835090019901104` и вклад D_SVX8/H_UFA_4 соответственно `−3 168 101.7677872814` / `−3 168 101.7677872833 RUB/неделю`. Численная бисекция и affine-root согласуются; расхождение с опубликованной alpha около 2.33×10⁻¹⁵. На alpha±10⁻⁷ разность D−H меняет знак: −0.25569261 / +0.25569262 RUB. В cautious пересечения нет: разность отрицательна на обоих концах каждого из четырёх общих affine-интервалов. α — координата между двумя сценарными входами, без вероятностного смысла.

| Base-программа | Первый ноль при t·C | Первый ноль при t·N | Насыщенный вклад, RUB/неделю |
|---|---:|---:|---:|
| D_SVX8 | Не достигается | Не достигается | −449 822.70 |
| H_UFA_4 | 2.4617708804 | 2.2064414956 | +3 174 557.80 |
| H_UFA_8 | 2.9194370052 | 2.0116807077 | +5 643 496.10 |

Все четыре первые нуля проверены численной симуляцией слева/справа; более ранних нулей нет на сертифицированном домене. Насыщенный хвост проверен при 1.01×, 2× и 1000× конца домена: все локальные кресла заполнены, transfer=0, вклад постоянен. В cautious насыщенные значения D/H4/H8 — `−11 241 985.28`, `−6 786 521.28`, `−12 896 078.56 RUB/неделю`. Полные budgets неизвестны, положительные значения base не являются доступными деньгами или прибылью компании.

Численный контроль affine-значений имеет максимум расхождения 3.92×10⁻⁸. Проверки уже округлённого tie до копеек и координат нулей до 10 знаков отдельно допускают остатки округления; они не включены в эту величину.

Контрпримеры нарушенных предпосылок сохранены в [assumption_counterexamples.json](assumption_counterexamples.json):

- При насыщении D_SVX8 и **сохранённой** миграции вклад −449 822.70; при migration=0 он +4 120 177.30. Утверждение о недостижимости нуля нельзя переносить на другое migration rule. Это объясняет отличие от оптимистической бюджетной границы MR07, без повторного LP-review.
- При 3·C base H4 даёт +1 118 414.38 с local-first и −1 089 222.77 с transfer-first; H8 — +302 900.88 и −3 052 001.00. Нули и границы применимы только к фиксированному приоритету. Большее число transfer journeys само по себе не означает лучший вклад.

## Qualified adapter и деньги

Проверены полные множества flight/capacity IDs в каждом из восьми source cases; used legs разрешаются, incidence согласована с capacity allocation, пути связны и времена последовательны. Стоимость каждого из 160 flight-scenario rows заново рассчитана по fuel cycle/hour, hourly maintenance/crew/navigation, airport basket и deicing; сумма сверена по каждому case. Номинальные 100 кресел не объявляются разрешённой эксплуатационной загрузкой.

В `build_comparison_adapter.py:34` квалификация действительно проходит только по единственному совпадению `model_id+source_commit+candidate_id+profile+scenario_id+physical_leg_id`, затем по единственному полному контекстному summary. Мой отдельный join восстановил те же поля во всех 160 строках. Amount, signs, itinerary/leg IDs и 896 остальных денежных строк сохранены. Missing/ambiguous anchor отвергаются. Первоначальный money_ledger не переписан.

В ledger ровно пять первичных статей с проверенными знаками: `+gross_revenue −foregone_RW_revenue −new_pax_variable +saved_old_pax_variable −flight_variable_cost`. Incremental revenue, operating cost и contribution — производные, повторно в сумму не входят. Flight cost записан один раз на физический рейс; пассажирские затраты — на сегменты. Поскольку это additive baseline с существующими рейсами, экономия отменённых старых рейсов не приписана. Проверенные суммы — [independent_money_reconciliation.csv](independent_money_reconciliation.csv). Base/fleet/opportunity, donor и cash ledger этим расчётом не определены.

Все четыре заявленные порчи (missing leg, duplicate leg, +1 млн к стоимости плеча, duplicate flight-cost entry) отвергнуты и независимым gate, и exact author validator. Это ограниченная проверка указанных свойств текущего адаптера; универсальная приёмка любого возможного импорта не заявляется.

Context21/224 и historical conditional16/860 сверены отдельно. Совпадение имени H_UFA_4 не использовано как join: context21 leaves GSV/MRV/NJC/OMS отличаются от RELAXED с GOJ вместо MRV. Namespace включает model/source SHA/input_set/run/profile/candidate/scenario; mapping отдельно сохраняет variant. Исходные годовые aggregates Анастасии остаются отдельным несовместимым денежным горизонтом.

## Primary context и обязательный HOLD

Здесь повторена арифметика incidence join по экспортированным OD, а не широкий raw/source review. Coverage bytes совпали с primary@`17b4f348f15ea8695688d9435933cb4965568408`; receipt не заменён derivative координатора.

| Программа / роль | Направленных экспортированных рынков | С положительной публикацией |
|---|---:|---:|
| D_SVX8 local | 16 | 16 |
| D_previous_best8 local | 16 | 2 |
| H_UFA_4 local | 8 | 4 |
| H_UFA_4 transfer endpoint | 8 | 1 |
| H_UFA_8 local | 16 | 6 |
| H_UFA_8 transfer endpoint | 24 | 3 |

H4=8/H8=24 — правильные знаменатели **фактически экспортированных transfer OD**. Полные комбинации листьев 12/56 отвечают другому вопросу. Числители в таблице — числа из frozen incidence, с сохранённым source HOLD; ими нельзя измерять конкурентные кресла, реальное предложение или demand coverage. Отсутствие положительной карточки — UNKNOWN. Во всех 176 строках `observed_endpoint_D` пуст, `demand_or_capacity_changed=False`; публикации не повысили спрос или ёмкость.

**Унаследованное P2 `SJR-P2-001` остаётся открытым для source acceptance.** Exact source/join review `944b16ac2dcde846e29dac2d47e11e5143f9fc2b` сообщает: registry receipts ссылаются на предыдущий SVX snapshot, тогда как 129 dated rows/28 cards/58 addendum mappings используют другой raw hash/capture. Locator: primary@17b `source_registry.csv:47`, `source_registry.csv:48`, `dated_evidence.csv:2` и `:75`; подробная finding — source_join_review@944 `findings.json:10`. В MR08 заново прочитаны verdict/объём из exact review и проверено, что methods потребляет старый coverage. Полная raw-линия повторно не разбиралась.

Минимальная необходимая коррекция остаётся прежней: привязать строки/карточки к `context/17_aircraft_route_review/evidence/sources.json`@exact93fa через source_id+raw_hash+capture_date; context12 snapshot оставить отдельным; rebuild registry/locks и dependent receipts новым пакетом. Frozen originals и часы не менять. Derivative координатора требует отдельной новой независимой проверки; MR08 его приёмку не наследует. Удерживается именно SOURCE_SUPPORTED затронутой lineage, без утверждения, что численная ошибка спроса или экономики установлена.

Также сохранены 12 KUF↔SVX clock conflicts, назначенный по контексту год части winter publications, planned≠performed и UNKNOWN seats/fares/observed OD. [source_hold.json](source_hold.json) фиксирует эти границы машинно.

## Передача результата

Можно использовать проверенную арифметику demand experiment, перечисленные boundaries и qualified adapter на **exact abb1** с указанными условиями. Не переносить это APPROVE на live methods, иной набор датированных продуктов, другую очередь распределения или исправленную source derivative.

MR05@b0b остаётся CHANGES на exact344f; MR07@2278 остаётся APPROVE_SCOPED на exact2a74; model_repair_review@445 остаётся APPROVE в прежнем scope. Их содержательные проверки здесь не расширены. Owner self-checks и coordinator hashes не названы independent/source/market acceptance.

NOT_RUN / OUTSIDE_SCOPE: широкий source/raw re-audit, budget-v2 LP, полные author pipelines, empirical demand/seasonality/capture validation, совместная оптимизация сетей, реальный donor/full strategy budget/cash schedule, эксплуатационная приёмка, продажи, выбор нормативных recipes/weights/radius, team acceptance и launch. Новых командных решений review не принимает.

Воспроизведение — [reproduce.md](reproduce.md). Машинный verdict — [findings.json](findings.json); передача и remote receipt — [handoff.json](handoff.json). Изменения ограничены `context/23_night_run_20261110/common_comparison_review/`. Сеть использована только для разрешённого Git fetch/push; live источники, браузер, Site/dashboard, инфраструктура, покупки, сообщения коллегам, дети и новые треды не использовались.
