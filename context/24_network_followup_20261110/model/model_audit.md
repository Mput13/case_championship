# Проверка фиксированного baseline

Статус **BASELINE_ONLY / PASS_SCOPED**. Research-файлы этого прохода не интегрированы и их готовность не опрашивалась. Следующий раунд — единственная адресная интеграция по `integration_contract.json` и `integrate_once.py`. Все выводы относятся к трём зафиксированным сетям, а не к оптимальному выбору маршрутов или городской оценке.

## Что воспроизведено

Exact methods `a77e4cfbd14e560d26407479b7252cfcb15f4f41` получен через `mcp__codex_apps__github_fetch`, не через отсутствующий локальный Git object. Все MCP bytes совпали с Git blob SHA из переданных exact tree indexes; SHA-256 и пути в `source_manifest.json`. Старые ledger inputs выгружены `git show 93fa5cf4a10ab67e05c93d19fc5375fc58ef9299:<path>` без checkout. Импортированы только чистые функции methods; upstream `main`, генераторы сети, ranking и owner optimizer не запускались.

Повторены 8 исходных context21 итогов и 224 маршрута продажи с миграцией; затем 12 C/N × base/cautious строк на одинаковых D_SVX8/H_UFA_4/H_UFA_8. Сверены точные summary, itinerary и 12 строк morning report; максимальное расхождение 1.49011611938e-08. Проверены 72 C/N mapping rows против exact старой матрицы N и weekly C, формула затрат каждого используемого leg, места на общих плечах, D-cap, один through fare и вычитание own-RW migration. Это **fixed-ledger replay**, не полное воспроизведение генерации сети, проверка действительного спроса/нетто-доходности/эксплуатации или полного бюджета. Ночной Git object не объявляется доступным.

`baseline_comparison.csv` сохраняет все исходные денежные статьи и метаданные. Все 12 вкладов отрицательны до fleet/base/opportunity. Контрольные base суммы совпали с supplied exact rows (не с округлёнными prose числами).

## Supply и единицы

`dated_legs.csv` и `frequencies.csv` фиксируют все 64 dated legs: D_SVX8 — 16 legs/1 модельный рабочий борт, H_UFA_4 — 16/2, H_UFA_8 — 32/4, условный резерв 1 на вариант. Тип — авторский 100-кресельный SSJ-class сценарий; реальные регистрационные борта, payload/range/crew/MRO и парк UNKNOWN. D_SVX8 летит 7–12 декабря; две UFA программы сжаты на 7–8 декабря внутри целевой недели 7–13 декабря 2026. Это не равномерная частота и не утверждение опубликованного/исполненного расписания. UTC-minute уже абсолютный от 07.12 00:00Z: второй раз day не прибавляется. H_UFA_4 выбран из ROUTE_INPUTS_UPPER_100 с MRV, а не из другого profile с GOJ. Никаких новых сетей не подбиралось.

C — недельный endpoint-сценарий Цири. N — годовой scale proxy exact 2f03, делённый на 104 = 2 направления × 52 недели **в обоих** общих сценариях. Поля N/period/coverage сохраняются в exact mapping; airport flow, airline group lower bound и модельные route segments не становятся наблюдённым winter endpoint OD. Из нового owner OD module входы не заимствуются. Розничное предложение — не net yield; опубликованные рейсы/кресла — offer, не paid demand. Airport total, route segments, endpoint journeys и transfer journeys — разные единицы. Для этих одно-/двухплечевых продуктов `segment_pax = sold_journeys + transfer_journeys`; прирост RW поездок — sold минус own-RW migration. Through fare начислен один раз, кресло занято на каждом плече.

Тариф `CIRI_NET_SCENARIO_FARE`; налоговая база `EX_RECOVERABLE_VAT_AS_AUTHOR_SCENARIO` — авторский сценарий, не доказательство применимости вычета или achieved yield. У базового керосина Цири 136300 + 1696 RUB/t; у текущего owner 134896 уже объединены в одном параметре. Их нельзя смешивать или добавлять uplift дважды. Корзина handling и deicing учтены один раз на каждый flown leg. Новые затраты меняются симметрично на всех flown legs с отдельным admission периода/единиц/налогов; субсидия требует собственной applicable scope и не включена автоматически.

## Два адресных порога

1. **α = 0.683509001990**: D_pair(α)=(1−α)C_pair+αN_pair для **каждого endpoint-рынка** при base и неизменных supply, тарифах, capture, migration/caps, local-first + исходной внутригрупповой сортировке. Это равенство contribution D_SVX8 и H_UFA_4: -3.168101768 млн RUB/нед. у обоих. При меньшем α меньше теряет UFA4, при большем D_SVX8; это не прибыль, вероятность, оценённая сезонность или доля пересадок. Fixed/base/external donor различия отсутствуют из объекта порога; при их изменении равенство меняется. На LP, иной allocator/offer universe и cautious порог не переносится.

2. **C/base H_UFA_4: общий множитель спроса 2.4617708804** даёт нулевой author contribution при исходных seats/fare/capture/local-first/migration/затратах. Это одновременное масштабирование всех C endpoint D, не рост «пассажиров аэропорта» и не утверждение, что рынок выдержит цены. Положительные исключённые расходы повышают порог полного PnL; фактические F/B неизвестны. В `fixed_rule_bounds.csv` проверены все исходные конечные curves, но они не расширяют universe и не являются глобальными network bounds. В cautious даже максимумы этих трёх fixed local-first программ отрицательны; рост только D не закрывает вклад в этом объекте, не запрещая иных продуктов/цен/сетей.

Exact piecewise curves проверены в 453 точках, включая границы и середины интервалов; за saturation дополнительно сверено постоянное хвостовое значение. Числа получены кодом, без подгонки к положительному результату.

## Текущий owner: отдельный контур

Пять exact файлов `54cddfa6a9ac6c58bf8ed87eda9c3765edd674b6` сохранены в `../owner_snapshot/`, blob-хеши сверены. Owner не запускался. В assumptions явно 52 base и 48 cautious модельных недель; 12 из 12 annual summary вкладов отрицательны. `owner_snapshot_checks.csv` проверяет только экспортированные годовые segment/OD/transfer и money тождества с допуском округления (до одного пассажира/миллиона RUB), а не подтверждает генерацию/весь owner набор. Годовые суммы и другой состав нельзя подставить вместо недельных common C/N. Owner fleet cap 10 и более частые сети также не подменяют common ceiling 4 и dated legs. Отрицательные условные OMS/REN не назначают реальные донорские борта.

## Admission и оставшиеся gates

`input_admission.csv` описывает текущие model inputs и разрешённые способы изменения. `input_admission_template.csv` — по одной строке на **каждую** находку трёх research agents, с отдельными source, source period, unit, tax basis, reliability, pair/flight и admission: direct_input / proxy / scenario_only / rejected_missing_scope. Наличие доказательства предложения или общей годовой статистики не даёт direct_input paid winter OD. Immutable source bytes должны быть привязаны SHA-256. Незавершённые результаты не импортируются.

C01 NJC>UFA>MRV: нужны конкретные protected product, MCT/turn, исходная dated rotation и цена изменения местных продаж. Это отдельный gate, не автоматически H_UFA_4. C07 SVX>OMS>KJA>OMS>SVX: next assignment, датированная цепочка, эксплуатация/спрос — отдельный gate; не принятая программа. Closed OD, contracts, free aircraft, achieved net yield остаются UNKNOWN.

Полный incremental budget: `contribution + external_donor_delta − incremental_F − incremental_B − support − start_recognized − exit_recognized − other_excluded`. Никакая неизвестная статья не превращена в ноль. Legacy own-RW foregone revenue уже внутри contribution: не вычитать повторно и не добавлять fictitious cancelled-flight savings. Реальные donor KEEP/CANCEL/REPLACE требуют именованных обязательств; full PnL/peak cash NULL. Cash — отдельные dated gross receipts/payments, депозиты, capex/финансирование. Условное нулевое исключение используется только в математическом объекте порога, не как установленный бюджет.

Список пробелов — `gap_map.csv`; передача owner — `owner_handoff.csv`. Фактические параметры owner не изменены. Scope финального адаптера ограничен фиксированными сетями, недельным endpoint D, net fare once, разделёнными fuel/uplift/hourly costs и passenger cost; все unsupported changes отклоняются, review round не расширяет обзор.

## Воспроизведение и целостность

Из корня реальной копии: `python3 context/24_network_followup_20261110/model/build_baseline.py`. Сеть не требуется. Собственный код только в `OUT/model/*.py`; historical code snapshots — evidence, не изменённые original scripts. Все 7 protected_city_stage хешей совпали, HEAD/base и ветка проверены. Commit/push, checkout/reset/worktree, правки stage1/ranking/weights/dashboard/src и сообщения другим не выполнялись.
