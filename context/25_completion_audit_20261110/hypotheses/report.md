# Аудит завершённости 35 гипотез

10 ноября 2026. Новый конечный аудит на base `f8b94a5c8b28e51664c5fff4a11606fb8f41c4d6`. Проверенные pins: hypotheses `6ed8788882e7b4d07044b4f6e686ff71eadd8ac5`, frontier `519998ed8c97ce5499f356a6d0f81558c7f6ee14`, review `58a02028e062b1abd803d99e19f630b75ec80657`, methods frozen `a77e4cfbd14e560d26407479b7252cfcb15f4f41`. Это самостоятельный пакет проверки сохранённых результатов. Новые опыты, сбор источников, дети и продолжение ночного цикла не запускались.

**Вывод: закрыто выполнение ограниченных исследовательских заданий; конечное решение по 35 гипотезам не закрыто.** Найдено 0 документированных ранних отказов от целой карточки. Все 35 получили спецификации и геометрию; 9 выбраны для углубления, адресные опыты выполнены для 3: C01/C07/C14. Остальные 32 в проверенных пакетах не испытаны адресно. Для трёх есть частичная условная экономика, а реальная прибыль, доступный ресурс и полный P&L/cash остаются неизвестными. Доказательство невозможности отдельных временных/ёмкостных условий сохранено и не расширено до отказа от гипотезы.

Полная построчная ведомость — [disposition.csv](disposition.csv): ровно 35 уникальных C01–C35, original status/selection reason, geometry/calendar/demand/money/fleet, старые денежные результаты или аналоги, вывод, следующая проверка и допустимая сценарная экономика с источниками. Каждая evidence-ссылка содержит полный commit/path/line и локальную копию. Все записи относятся к namespace `hypotheses35`; одноимённые Cxx иных систем не соединялись.

## Что было сделано и что не было отвергнуто

В двух исторических coordinator snapshots 13:18/14:22 UTC содержимое `candidates.csv` побайтово совпало с hypotheses pin. Во всех 35 строках ранний статус `NOT_EVALUATED`, спрос/нетто-тариф/ресурс `UNKNOWN`. Ранние `evaluation_runs.jsonl` перечисляют 35 участников, `economics/demand_fit=NOT_RUN`, `rejected_candidates=[]`. У 26 карточек вне первой девятки дословная причина: «Сохранён в широком поиске; отсутствие в первой очереди не означает опровержения или низкого спроса». У 9 выбранных указана ценность разных механизмов, а не ранг прибыли. `stop_rule` — будущий критерий проверки, он не является зафиксированным наступившим отказом.

Лично пересчитаны 144 chord-leg строки из координат 50 аэропортов, 81 path и 324 screen строки. Максимальная погрешность округления менее 0,0005 км. Ни 2300 км, ни 500 км не стали основанием автоматического экономического отказа. Хорда не dispatch/track/block/payload. У C21 сохранены 214 буквальных arrival rules KHV: это опубликованное предложение, не demand, free fleet или complete return calendar. Исторические RW observations C11/C22 и сторонние корпоративные примеры прочитаны как контекст сохранённого источника, без новой внешней проверки.

Последующие frontier `BLOCKED_*` обозначают неизвестные/условия следующей проверки. Они не восстанавливают историческую причину раннего отсева. В ведомости все 35 имеют `documented_early_rejection=ABSENT`. Основной disposition: 3 `DEFERRED_UNKNOWN_WITH_PARTIAL_TESTS`,32 `NOT_EVALUATED_OUR_SCOPE`. Это не классификация 32 идей как бесперспективных.

| Состояние | Число | Что именно установлено |
|---|---:|---|
|Доказанный отказ от целой карточки|0|Такого завершённого доказательства в проверенных материалах нет|
|Условный отказ фиксированному случаю|Есть внутри 3 тестов|Например MCT90 C01, недостаточный advance C07, capacity fixture с K500 тыс.; это не отказ всей идее|
|Отложено из-за неизвестного после частичных тестов|3|C01/C07/C14: actual sales/cost/resource/product gates не закрыты|
|Адресно не оценено из-за нашего scope|32|26 вне девятки и 6 выбранных, не вошедших в трёхтестовый проход|

## Частичная экономика трёх опытов

Утверждение «никакой экономической оценки трёх нет» слишком сильное. Его точная формулировка дана в нынешнем поручении; дословная repo-строка родителя не установлена. В 6ed уже сохранены численные пороговые сценарии, состав затрат, ресурсы и коэффициенты. Корректная формулировка: **есть проверенные условные пороги и рецепты расчёта затрат, нет установленного реального денежного результата и полного бюджета**. [context/16_agent_research/hypotheses/experiment_v1/README.md:11](https://github.com/Mput13/case_championship/blob/6ed8788882e7b4d07044b4f6e686ff71eadd8ac5/context/16_agent_research/hypotheses/experiment_v1/README.md#L11), [context/16_agent_research/hypotheses/experiment_v1/README.md:44](https://github.com/Mput13/case_championship/blob/6ed8788882e7b4d07044b4f6e686ff71eadd8ac5/context/16_agent_research/hypotheses/experiment_v1/README.md#L44).

1. `conditional_thresholds_with_product_keys.csv` содержит 108 уникальных candidate×gap×fare×variable_cost комбинаций, по 36 на C01/C07/C14. Это 3×3×4×3, а не 108 проверок рынка. Разные run-версии и keyed projection повторяют тот же grid. Лично повторены целочисленная инверсия, одна through fare, endpoint journeys, boardings, margin at threshold и отрицательная предыдущая ступень. Расхождений нет. Результаты со source lines — [money_recalculation.csv](money_recalculation.csv).
2. Пример K=1 млн, F=8000 за one-way journey и v=500 даёт `q=ceil(1000000/(2×7500))=67` на направление. Это 134 one-way journeys, 1,072 млн билетной выручки и 5000 условного превышения маржи над K. У C01 — 268 boardings; у локальных OMS–KJA C07 и KVX–MRV C14 — 134. Реальные K/F/q/остаточные места неизвестны. У C14 в K остаются все 4 предложенных RW legs, хотя threshold относится к local KVX–MRV продукту.
3. В `residual_gap_accounting.csv` отдельно раскрыты 3 baseline. Для C01 одинаковые flight costs сокращаются только при действительно одинаковых затратах/контрактах, остаются retiming/base/overnight/local loss. C07 несёт все новые OMS–KJA legs/ground events и изменение обеих базовых продаж. C14 несёт полную SVX–KVX–MRV–KVX–SVX программу минус явно названные другие вклады. Нельзя второй раз вычитать ту же потерянную выручку как потерянную маржу.
4. В 9 публичных строках есть реальные опубликованные тарифные числа. Лично проверены суммы OMS911+947=1858 и UFA553+499=1052 руб./т MTOW при однократном выставлении каждого сбора. Это коэффициенты, не оплаченный бюджет и не нижняя граница: MTOW/modification, billing multiplicity, contract/discount/VAT и полный набор услуг неизвестны. UFA685 руб./час стоянки — опубликованная строка для группы SSJ, а применимость к нужным минутам/договору надо задавать отдельно. Coordinator 15:46 сохранил manifest этого cost_resource, не все его CSV; полные строки восстановлены именно из дерева 6ed.
5. Frontier добавил 4 mechanical fixtures. При 100 номинальных местах и 80 прежних остаётся 20; F−v=7500 даёт максимум 300 тыс. новой парной маржи. K300 тыс. требует 20 на направление и помещается; K500 тыс. требует 34 и перегружает каждое использованное плечо на 14. Положительные 10000 руб. арифметического остатка при q=34 не снимают capacity failure. Все 18 actual monetary difference terms frontier остались NULL.

Это уже полезная денежная работа. Она не является calibrated demand, received fare, actual availability, profitable network или financial acceptance.

## Границы C01/C07/C14

**C01, Уфа.** Проверялся NJC–UFA–MRV, не все три пути карточки. В фиксированном same-leg примере север прибывает 09:00 UTC/уходит 17:00, южный reference вылетает 08:00 и возвращается 13:45. Для неотрицательных сдвигов x/y условие существования стыковки `2M+T≤180`. Лично перебраны совместные clock inequalities для 9 M/T профилей и 54 return limits, независимо от owner/reviewer кода. M45/60 допускает решения; M90 с T30/45/60 — нет в заданном окне. Шесть feasible профилей дают 5/6 сочетаний выезда 7/11 декабря и 7/10/14 ночей; у 10 ночей после 7 декабря нет нужного 17 декабря в frozen Mon/Fri set. Это не observed demand. При M60/T45 x=y120 даёт 60/75 мин стыковок и 45 мин разворота; следующий ресурс/реальная no-new-base ротация/цена local sales неизвестны. Время не доказывает выгоду новой базы.

**C07, Екатеринбург–Омск–Красноярск.** Лично восстановлены 18 turn/slack границ и 54 advance gates. Против reference 205 мин полёта / 255 мин занятости цепочка имеет 475 мин полёта и 565/610/655 мин занятости при T30/45/60. Добавка 270 мин полёта и 310/355/400 мин занятости. `advance=max(0,220+3T−L)`, L уже net of next turn, не crew-duty limit. При T45/L180 нужно 175 мин опережения; 174 недостаточно. С прежним стартом и L0 прежний возврат невозможен. Это условный временной отказ; loop/ранний старт не доказывает available aircraft. OMS–KJA часы — proxy другой компании, donor/next assignment/crew/MRO и изменённые собственные продажи неизвестны. C04 Омск был сравнительным вопросом в очереди, отдельной экономики новой базы не получил.

**C14, Киров–Минводы.** Старые 21 UNKNOWN input001 не удалены. На 12 published dated flights input002 лично заново соединены 24 запроса =2 выезда×2 свойства×2 booked-date bases×3 срока и 96 tolerance-policy строк. Exact return есть у 12/24 property rows. При 0/1/2/3 дополнительных ночах получается 6/7/9/11 distinct date/stay совпадений из 12, property copies не пассажиры. Для checkout 25 декабря capture returns заканчивается 24 декабря: UNKNOWN, не no service. Ночное заселение, timezone/minimum/room inventory, полный dated transfer, customer willingness, airline seats/fare/rights и operating/nonstop неизвестны. Дата совпала — ещё не bookable package. PERSON_BED_DAY/PERSON_DAY нельзя умножать на nights без правил billing. A4 calendar не даёт RW выручку/кресла.

Сохранённое независимое review 58a02028 имеет APPROVE_SCOPED для calendar/arithmetic/conservation, не market/full-money/operating acceptance. Новый аудит не расширяет его scope. [context/23_night_run_20261110/hypothesis_frontier_review/report.md:11](https://github.com/Mput13/case_championship/blob/58a02028e062b1abd803d99e19f630b75ec80657/context/23_night_run_20261110/hypothesis_frontier_review/report.md#L11).

## Прежние деньги и пределы переноса

В context21 visual inputs сохранены 8 денежных строк и 42 порога. Их bytes совпали с upstream 93fa5cf `context/21_team_proposals/comparison.csv` и `context/18_unit_economics_audit/breakeven.csv`; проверена provenance в `inputs_manifest.json`. Для 8 сетевых строк лично пересчитана формула `gross−foregone−flight−new_pax+saved_pax`. Для 42 порогов использован отдельный route_ledger flight cost и margin, повторены threshold/at100/capacity; полный author model/solver не запускался. [historical_economics.csv](historical_economics.csv), [breakeven_recalculation.csv](breakeven_recalculation.csv).

| Context21 сеть | Base, млн RUB/неделю | Cautious, млн RUB/неделю |
|---|---:|---:|
|D_SVX8|−7,326331|−17,737274|
|D_previous_best8|−5,023171|−14,417665|
|H_UFA_4|−4,623004|−15,163157|
|H_UFA_8|−9,496920|−28,166230|

Это вклад до base/fleet/opportunity, условные additional flights, не доказанная замена действующего донора. Эти сети не равны C01/C07/C14. В historical stage16 pin сохранено 30 aggregate rows, включая NO_LAUNCH и пустую D_improved с нулевыми legs; их нули не прибыль авиакомпании. Агрегатная арифметика 30 строк также повторена. EC_H01–11 в ancestor registry имеют PROPOSED_NOT_ACCEPTED и UNKNOWN value, это семейства гипотез, не 11 результатов отказа.

У исторического SVX–MRV пилота bf564c7 лично повторены 4 инверсии: base 85 оплаченных на сторону до fixed, 94 при 10% запасе к flight cost, 124 при симметричном распределении 1 млн/неделю; cautious 180 до fixed. Эти числа не подставляются в новый продукт или фактический type swap C31. Поздний context21 SVX–MRV base threshold уже 83,429675≈84 до extra fixed при иной cost/margin версии; при 100 местах вклад+425857,35 руб./неделю до дополнительной нагрузки, при+500 тыс. —−74142,65. Версии не следует смешивать.

В `source_linked_scale_tests.csv` есть 48 сценариев SVX–MRV/SVX–AER, из них 20 положительных до extra fixed: 8 MRV и 12 AER, все base. Лично проверена их contribution arithmetic. Например SVX–MRV при endpoint_fraction=0,5 и winter_ratio=1 даёт условные 100 проданных/направление и+425857,35; AER при 0,25/0,5 также достигает nominal 100 и+200945,85. Это сценарии с долей endpoint и сезонностью, не наблюдённый OD/paid sales, не actual 100 payload и не полный бюджет. Положительные строки сохранены в [positive_historical_scenarios.csv](positive_historical_scenarios.csv), а не стёрты общим «всё отрицательно». [context/18_unit_economics_audit/source_linked_scale_tests.csv:7](https://github.com/Mput13/case_championship/blob/93fa5cf4a10ab67e05c93d19fc5375fc58ef9299/context/18_unit_economics_audit/source_linked_scale_tests.csv#L7).

Frozen methods дополнительно имеет 8 supply upper-bound строк. Лично повторена арифметика full_local_revenue−pax−flight, но не доказательство оптимизационного сертификата. Все 4 cautious upper bounds отрицательны в фиксированном enumerated-product universe даже при relaxed demand/no migration. Это условный отказ именно этому supply/fare/cost universe; он не запрещает иную цену, cost recipe, новый продукт, иной ресурс или сеть. FullPnL/peakCash frozen methods остаются NULL. [context/23_night_run_20261110/methods/handoff_compact.md:28](https://github.com/Mput13/case_championship/blob/a77e4cfbd14e560d26407479b7252cfcb15f4f41/context/23_night_run_20261110/methods/handoff_compact.md#L28).

## Что можно считать при UNKNOWN

Недостаток actual OD/fare/resource запрещает называть сценарий фактом. Он не требует вообще остановить расчёт. Для каждой строки ведомости дана отдельная допустимая постановка: что фиксируем, какой K/премию/гарантию/долю/ресурс варьируем и какой порог получаем. Новых численных money experiments этим аудитом не выполнено.

Общая инкрементальная форма: `ΔC=Σq_j(F_j−v_j)−K(q)`. q ограничен одним общим endpoint pool и каждым physical-leg residual seat; fare начисляется один раз. K включает только согласованные добавочные рейсы/ground/base/fleet/switch/opportunity/local-loss статьи без повторного списания. Unknown terms сохраняются. Если обоснованы интервалы F/v/K, при фиксированном допустимом q можно вывести `ΔC_min/ΔC_max`; при зависимом K(q), displacement или изменении capacity нужен полный joint расчёт, не формула с постоянным K. Полный cash требует датированных receipts/payments/депозитов/финансирования отдельно от P&L.

Уже имеющаяся численная опора неодинакова. Публичные airport rate coefficients привязаны к конкретным услугам/датам; это допустимые условные элементы cost recipe. Source-linked annual segment scale требует явно неизвестных endpoint fraction/seasonality/capture. Старые F6–12 тыс./v0–1000/K0–1 млн — происхождение author inversion stress, не эмпирические границы рынка. Сценарный nominal 100 или residual 20 — mechanical ceiling, не эксплуатационный факт. При отсутствии ценового диапазона полезен ответ «какая гарантированная оплата/маржа покрывает программу», а не выдуманный точечный тариф.

В частности: C03/C04/C06/new bases — границы B/F против действующей базы; C10/C12/C18/C20/C32 — guaranteed block/payment и асимметрия; C27/C28 — bus contract/protection против residual air seats; C31 — обе программы до/после type swap; C33 — новые и потерянные связи при тех же рейсах; C34 — avoided damage против своевременной доставки резерва без вероятности из постов; C30 — две ветви после наблюдаемого триггера без даты/вероятности. Это конкретные расчётные вопросы, а не причины не оценивать идеи.

## Кто ограничил исследования тремя тестами

Исходный coordinator brief требовал широкий первичный набор и 6–10 различающихся кандидатов для углубления. Девятка выполнила именно этот отбор; ранний brief не обещал полную экономику всех 35. [context/16_agent_research/briefs/hypotheses.md:28](https://github.com/Mput13/case_championship/blob/f8b94a5c8b28e51664c5fff4a11606fb8f41c4d6/context/16_agent_research/briefs/hypotheses.md#L28).

В сохранённом `phase2_brief.md:9,21` координатор назначил C14/C01/C07 как 3 основных опыта и предписал Astra начать experiment_v1 для них. Документ описывает просьбу пользователя о ещё 2 часах; исходная реплика пользователя с выбором именно 3 в проверенных артефактах не предъявлена. Следовательно, подтверждён владелец ограничения на уровне постановки — coordinator brief, а персональную волю пользователя о численном лимите не восстанавливаем. Git-коммит этого файла:f6366f888803c076dab6b47d497751ffe5a61566, author metadata Mput13,09.11.2026 17:14:07+03; Git-author не доказывает, кто сформулировал решение. [context/16_agent_research/phase2_brief.md:9](https://github.com/Mput13/case_championship/blob/f8b94a5c8b28e51664c5fff4a11606fb8f41c4d6/context/16_agent_research/phase2_brief.md#L9).

Ночной coordinator brief прямо потребовал«выбери до 3» по снижению неопределённости/охвату/входам. Конкретный исполнитель frontier выбрал те же C01/C07/C14 и зафиксировал причины Q01–Q03; 32 идеи сохранил как deferred. Это имело договорное основание для ограниченного task, но не заменило outcome по широкому поиску. Source of limit — brief, source of actual choice — executor queue/test_contract. Brief в base связан с f1774e1f66a9483fb618ca6003abd9dc4d8563e1. [context/23_night_run_20261110/briefs/hypothesis_frontier.md:18](https://github.com/Mput13/case_championship/blob/f8b94a5c8b28e51664c5fff4a11606fb8f41c4d6/context/23_night_run_20261110/briefs/hypothesis_frontier.md#L18).

Шесть исходно выбранных, но не выполненных E-first-wave:C02/E02, C10/E04, C17/E06, C21/E07, C27/E08, C31/E09. Их приоритет был объяснён, отмена по отрицательному результату не документирована. Эти шесть вместе с 26 вне первой девятки дают 32 адресно неиспытанных.

Task-completion:35specs+9queue; 3 ограниченных experiment_v1; 35-classification+3 frontier tests; scoped review. Outcome-completion: обоснованный hub/direct/mixed выбор, единый ресурс/спрос/полный бюджет, готовая 8–12-route программа, топ 3/≥10 городов и≥2 конкурента в согласованной постановке, годовые passengers/revenue/share иroadmap2028 — этим рядом пакетов не установлен. Сообщать первое как второе нельзя. Исторические корректные scoped approvals не отозваны; арифметических расхождений в лично пересчитанных строках нет.

## Личная проверка и передача

Все источники получены `git show exactSHA:path`; новые внешние страницы/тарифы/расписания не проверялись. Лично сверены 35unique/original status/отбор/ancestor keys, совпадение двух ранних snapshots, 144geometry legs/81paths/324screens, 108money cells и сохранённые их версии, 9rates/2sums, 4capacity fixtures, 18NULL money terms, границы и календарные joins описанных 3 тестов, 8+30aggregate money rows, 42break-even, 4 старых pilot inverses, 48source-linked scenario money rows, 8capacity-bound arithmetic rows. Счёт проверок в `checks.json` — технический receipt, не оценка качества/доказанности рынка.

Не выполнялись owner/reviewer code replay, полный solver/LP-certificate proof, live source audit, измерение demand/paid revenue, operational/dispatch/fleet acceptance, новый budget/cash run или полный новый эксперимент по 32 карточкам. Сохранённые source observations/independent review отмечены как supplied evidence; их прежние PASS не добавлены к моим личным checks. Пакет не меняет исходные модели/UI/документы.

Замечания и минимальные действия — [findings.json](findings.json). Команда воспроизведения: `PYTHONDONTWRITEBYTECODE=1 python3 context/25_completion_audit_20261110/hypotheses/build_audit.py`, затем `write_report.py` и `verify_package.py` в той же папке. [source_manifest.json](source_manifest.json) фиксирует exact blobs; [handoff.json](handoff.json) — границы передачи. Новая работа не запускается автоматически.

## Все 35 карточек

| ID | Карточка | Адресная работа сверх геометрии | Решение этого аудита |
|---|---|---|---|
|C01|Уфа: север–юг с защищённой мини-волной|Same-leg clock/calendar; 36 money inverses; K/resource/fixtures|Частично проверено; actual gates UNKNOWN|
|C02|Нижний Новгород: деловой календарь с возвратом|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C03|Самара: промышленная радиальная база|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C04|Омск: новая компактная база|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C05|Красноярск: проверка входа рядом с сильным хабом|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C06|Пермь: роль базы требует проверки истории|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C07|Цепочка Екатеринбург–Омск–Красноярск|Four-leg time/advance; 36 money inverses; K/resource/fixtures|Частично проверено; actual gates UNKNOWN|
|C08|Архивная цепочка Жуковский–Архангельск–Минводы|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C09|Треугольник через Самару и Волгоград|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C10|Сургут: асимметричный корпоративный блок|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C11|Новый Уренгой: улучшение уже существующего продукта|Исторические RW observations; dated improvement NOT_RUN|Не оценено в нашем scope; не отказ|
|C12|Череповец–Север: промышленный календарь|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C13|Тюмень–Ямал: семейный и сменный продукт|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C14|Киров–Минводы: санаторный календарь|Published calendar/stay/flex joins; 36 money inverses; full-chain K|Частично проверено; actual gates UNKNOWN|
|C15|Пермь–Минводы: семейное сопровождение|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C16|Самара–Минводы: калибровочный контроль|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C17|Пермь: разные зимний и летний продукты|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C18|Горно-Алтайск: спортивный групповой блок|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C19|Волгоград–Дагестан: короткая поездка|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C20|Томск–Хакасия: студенты и семьи|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C21|Хабаровск: отдельная дальневосточная база|214 inbound rules; product/economics NOT_RUN|Не оценено в нашем scope; не отказ|
|C22|Сибирь–Забайкалье: цепочка с реальными incumbents|Историческая RW BAX–HTA observation; новый цикл NOT_RUN|Не оценено в нашем scope; не отказ|
|C23|Якутск–Нерюнгри–Благовещенск: тонкий региональный узел|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C24|Сахалин–Камчатка: партнёрский календарь|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C25|Калининград–Поволжье: длинная семейная поездка|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C26|Коми–Архангельск–Мурманск: северные связи|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C27|Наземный подвоз вместо близкой новой базы|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C28|Нижний–Чебоксары–Саранск: выбор зоны доступа|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C29|Волгоград–Астрахань–Саратов: проверка наземного контроля|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C30|Изменение доступности южных аэропортов|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C31|Замена типа и высвобождение SSJ|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C32|Событийный блок вместо годовой линии|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C33|Перестановка уже существующей сети RW|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C34|Общий резерв и восстановление сети|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
|C35|Внутренний фидер партнёра через существующий узел|Спецификация/причина выбора; адресный run NOT_RUN|Не оценено в нашем scope; не отказ|
