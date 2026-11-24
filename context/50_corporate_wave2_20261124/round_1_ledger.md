# Раунд 1 Консула — Pick-and-Graft, операционные правила `T1–T5` и замороженное ТЗ Волны 2

Дата: **24.11.2026**. Ветка: `research/corporate-demand-20261124`. База аудита: коммит `71e73d69` ([журнал ревью Волны 1](../49_corporate_screening_20261124/wave1_review_ledger.md)).

## 1. Оценки Консула (Раунд 1 — по итогам Волны 1 и Трека B)

| Член Консула | Модель и режим | Линза | Оценка R0 → R1 | Главный вклад в Раунде 1 |
|---|---|---|---|---|
| **Strategist** | `codex/gpt-6.2-astra` (`xhigh`) | Domain Architect | `7/10 → 7/10` | Приоритет №1 СТНГ (дедупликация с Газстройпромом), №2 Газпромнефть-Снабжение 2027–2029; позитивные `No-Go` на уровне `орг × когорта × окно × продукт`; три контрастных пилота; жёсткое правило пулинга (встречные потоки улучшают оборот, но не складываются в загрузку одного плеча). |
| **Skeptic** | `antigravity/claude-opus-5-5` (`high`) | Evidence Critic | `6/10 → 6/10` | Скрытые риски сверх `S1–S7`: открытый тендер ТМС по умолчанию `MARKET_COVERED`, а не GAP; формализация ранее не определённого `T5` и kill-правил `K1–K7`; поле `claim_type` + правило свежести (`≥2025-01-01` или контракт на 2027); строгое разделение `CONFIRMED_UNIT` и `STRUCTURAL_HYPOTHESIS` (потолок `Conditional`, без суммирования). |
| **Quant** | `codex/gpt-6.2-sol` (`xhigh`) | Feasibility & Math | `6/10 → 7/10` | Полные CSV-схемы Волны 2 (`sites_and_links_graph`, `opportunities`, `supply_gap_pairs`, `cohort_demand_scenarios`, `pooling_and_nodes`); единая методика сравнения естественных узлов (`SVX/TJM/OVB/KJA/LED/SVO/DME/VKO/ZIA`, перепробег 25%/35%); первичные даты 2027 по ЦИПР, ИННОПРОМ, ПМГФ, TNF; точная спецификация исправлений `S3–S5`. |
| **Minimalist** | `antigravity/gemini-4-neon` (`high`) | Pragmatist | `6/10 → 6/10` | Ноль отдельных фикс-раундов Волны 1 (закрытие `S1–S7` внутри Волны 2, сохраняя `49_*` неизменным); сбор тарифов-ориентиров, ЖД и ортодромий сразу в Волне 2, чтобы Волна 3 шла без нового ресерча; ограничение до 4 пачек `terra` + 2 воркеров `sol` + 1 кросс-модельного ревьюера. |

---

## 2. Lead Judgment: `Act On` (5 решений) и `Dismissed`

### `Act On` (принято в работу для Волны 2)
1. **Заморозка операционных правил `T1–T5`, `K1–K7`, `claim_type` и правила свежести до первого запроса Волны 2.**
   - **`T1` (SCHEDULE_GAP):** в окне когорты (±1 день для регулярки/проекта или точное окно заезда/выезда для вахты/форума) нет прямого рейса или рабочей стыковки в пределах допустимого времени «дверь-до-объекта» из нужного аэропорта (`SVO/DME/VKO/ZIA` строго раздельно), либо доказан дефицит гарантированных мест/класса/единовременной ёмкости.
   - **`T2` (GROUND_ALT):** если поезд или авто «дверь-до-объекта» укладывается в ≤8–10 часов либо есть ночной поезд с прибытием к началу рабочего дня/смены и без срыва программы, гипотеза авиационного GAP снимается (`GROUND_ALT`), если не доказано иное ограничение (багаж/безопасность/срочность).
   - **`T3` (PAYER):** ИНН конечного плательщика и закупочный канал подтверждены первичным документом; организатор закупки или форума (`Газстройпром`, `Росконгресс`) плательщиком не считается. Одна процедура = одна единица спроса по ключу `(procurement_ref, payer_inn)`.
   - **`T4` (INCUMBENT):** ведомственный или связанный перевозчик (`Газпром авиа`, `АЛРОСА`, `Северсталь Авиа`, `ЮВТ` и др.) не закрывает это окно и эту когорту действующей программой до 2027 года (подрядчики вне ведомственной программы проверяются отдельно).
   - **`T5` (DURABILITY + THRESHOLD):** поток устойчив ≥12 месяцев от даты старта или имеет явную дату/триггер спада, а `Base`-оценка на конкретном окне не ниже порога Раунда 0 (`≥15–20` кресел/рейс для блока, `≥70–80` кресел/рейс для выделенного SSJ100, `≥120+` для среднемагистрального ВС ≥150 кресел).
   - **Kill-правила фальсификации (`K1–K7`):**
     - `K1`: ≥2 прямых рейсов в день в окне из нужного аэропорта со свободными местами на проверяемую группу → `MARKET_COVERED`.
     - `K2`: поезд/авто ≤8–10 ч «дверь-до-объекта» или удобный ночной поезд → `GROUND_ALT`.
     - `K3`: ведомственный перевозчик покрывает заявленную группу в окне → `OWN_FLEET`.
     - `K4`: нет единого ИНН плательщика (только организатор/агрегатор) → `FRAGMENTED_PAYER`.
     - `K5`: последнее доказательство спроса старше `2025-01-01` и нет договора/процедуры на 2027 год → статус не выше `Conditional` / `Insufficient-Evidence` (экстраполировать в `Go` запрещено).
     - `K6`: `Base` на окне ниже минимального порога блока (`<15` кресел/рейс) → отдельная программа не нужна.
     - `K7`: единственный источник числа — ТЗ ТМС, рубли НМЦК, общая численность персонала или зарубежный аналог → число в `CONFIRMED_UNIT` не попадает.
   - **Колонка `claim_type` в `evidence_wave2.csv`:** `IDENTITY | AFFILIATION | DEMAND_UNIT | GAP | PAYER | INCUMBENT | EVENT_DATE | BENCHMARK`. Финальный `Go` требует ≥1 `PRIMARY_*` записи с `claim_type=DEMAND_UNIT` (дата `≥2025-01-01` или контракт на 2027) и ≥1 `PRIMARY_*` записи с `claim_type=GAP`.
   - **Разделение контуров (`demand_basis`):** `CONFIRMED_UNIT` (документированные физические единицы) vs `STRUCTURAL_HYPOTHESIS` (кооперация закрытых по ПП № 301 заказчиков — Ростех/ОАК/ОДК/ВР/ВСМПО, потолок статуса `Conditional`, `[NEEDS-RW-DATA]`). **Складывать их в одну сумму в таблицах, HTML и XLSX запрещено.**

2. **Шорт-лист 11 кластеров, 22 городские пары (с запасом к `P4 ≥ 20`) и 7 целевых проверок позитивного `No-Go` (`S6`).**
   - Выбираем 11 фокусных кластеров (ядро: 12 организаций + 7 целевых `No-Go` на уровне `орг × когорта × окно × продукт`), не раздувая Волну 2 на оставшиеся ~50 юрлиц из `organizations_screening.csv`.
   - Заранее регистрируем ожидаемый честный исход по каждому из 11 кластеров до начала сбора (см. Раздел 3). Если >70% кластеров получат `Go`, запускается обязательная проверка на подгонку.

3. **Закрытие `S1–S7` пакетом внутри Волны 2 (без отдельного фикс-раунда Волны 1):**
   - `context/49_corporate_screening_20261124/` остаётся неизменным архивом Волны 1.
   - В `context/50_corporate_wave2_20261124/` воркеры `W2-S1` и `W2-S2` выпускают обновлённые канонические реестры (`organizations_screening_v2.csv`, `benchmarks_cases_v2.csv`, `events_calendar_2027.csv`, `why_not_registry_v2.md`):
     - `S1`: понижение `ПАО ФСК — Россети` (`RU-INN-4716016979`) из `Candidate` в `Conditional` + проверка типа ВС (вертолёт/МВЛ vs самолёт RW) по лоту Южного ПМЭС.
     - `S2`: добавление 2027-выпусков по 9 ежегодным сериям (`ПМЭФ`, `ВЭФ`, `ИННОПРОМ`, `ЦИПР`, `ПМГФ`, `TNF`, `РЭН`, `КИФ`, `Транспорт России`) с разделением на `future_confirmed / future_provisional / future_tbd / historical` (`as_of=2026-11-24`).
     - `S3`: добавление `benchmark_role=QUALIFIED|COMPARATOR|CONTEXT`, переклассификация `W14-07` (`ADHOC_UNSPECIFIED`) и `W14-08` (`PUBLIC_SCHEDULED / COMPARATOR`), атрибуция двух релизов FPL (`140` вылет + WPTV чартер vs `>120` возврат), вывод `qualified_by_stage` отдельно по РФ и миру.
     - `S4`: заполнение `anchor_org_id` для 13 дочек `W1-1` (5 Ростех, 2 Роскосмос, 6 Росатом), исправление секторов (`ТМХ → INFRA_TRANSPORT`, `ТМК/ОМК → MINING_MATERIALS`), перевод `Сургутнефтегаз/НОВАТЭК` в `PRIVATE_CONTROL`, понижение пустых `Conditional` (6/6 `UNKNOWN` вне шорт-листа) в `Insufficient-Evidence`.
     - `S5`: расширенный `validate_wave2.py` без хардкода `CONTEXT_ONLY_CASES`, с проверкой `\bMOW\b` по всем структурированным полям, проверкой `currency` только при заполненной денежной метрике, строгой проверкой `Candidate/Go` и раздельной сводкой `pairs_screened / pairs_quantified / pairs_with_decided_gap / pairs_external_blocked`.
     - `S6`: 6–7 доказательных `No-Go` на уровне `орг × когорта × окно × продукт` по всем 5 кодам `no_go_proof_type`.
     - `S7`: раздельные 4 аэропорта Москвы (`SVO/DME/VKO/ZIA`) для всех московских форумов и пар + привязка `EV-W13-001` и `EV-W13-003`.

4. **Полевые данные для Волны 3 собираются полностью в Волне 2 (ноль новых поисков в Волне 3).**
   - Ресерчеры `W2-T1..T4` сразу фиксируют по каждой паре актуальные прямые и стыковочные авиарейсы (с дедупликацией код-шеринга, 4 аэропорта Москвы раздельно), ориентиры тарифов `fare_rub`, время/тариф ЖД и «последнюю милю» `access_min`, наличие бизнес-класса, багажные лимиты и 2–3 открытых ТЗ ТМС для калибровки доли бизнес-класса (`J_REQUIRED` / `J_PREFERRED`).
   - Воркер `W2-S1` считает точные ортодромии `gc_distance_km` по координатам IATA; воркер `W2-S2` строит пулинг строго по совместимым `(from_iata, to_iata, date/window, cabin)` и считает рейтинг естественных узлов (`SVX`, `TJM`, `OVB`, `KJA`, `LED`, `SVO`, `DME`, `VKO`, `ZIA`) по единым метрикам с перепробегом 25% и 35%.

5. **Закрепление 3 контрастных пилотов для глубокой экономики Волны 3 и верхнего блока HTML-досье:**
   - **Пилот 1 (Вахтовый чартер/пулинг + лимит вместимости SSJ100 100Y):** `UFA ↔ NUX` (`РН-Ванкор` + пулинг-контур `СТНГ` / `Севернефтегазпром`).
   - **Пилот 2 (Инженерно-промышленная кооперация + наземная альтернатива + бизнес-класс + тест узла `SVX`):** `Атомтехэнерго` (Димитровград через `ULY/KUF`) + кооперационная ветка `ОДК / ВСМПО-АВИСМА` (`SVX ↔ ULY / UFA / KZN`, где закрытый контур Ростеха строго помечен `STRUCTURAL_HYPOTHESIS`).
   - **Пилот 3 (Событийный блок vs регулярка + дальнее плечо вне SSJ100):** `ИННОПРОМ-2027` (`LED ↔ SVX`, гарантированный блок с возвратом квоты и обменом имён) + сравнение с длинным плечом `LED ↔ NUX` (`Газпромнефть-Снабжение 2027–2029`, >2 600 км — вне консервативной дальности SSJ-95B ~2 355 км).

### `Dismissed` (отклонено с обоснованием)
- *Отдельный фикс-раунд Волны 1 и повторное ревью (частично implied `S1–S5`):* **отклонено** — 0 открытых `blocker`, все 7 правок закрываются внутри `W2-T3/T4` и `W2-S1/S2` без лишнего цикла.
- *Глубокий поиск по всем 67 организациям или дереву поставщиков 2–3 уровня (расширение скоупа):* **отклонено** — фокусируемся на 11 кластерах (22 пары), оставляя остальные ~50 юрлиц в `organizations_screening_v2.csv` со своими `decision_changing_fact`.
- *Повторный скрейпинг закрытых лотов ЕИС (ПП № 301) или битого архива `РН40302710` (Issue #5):* **отклонено** — фиксируем `UNAVAILABLE_PP301` / `UNAVAILABLE_TECH` с журналом проверенных зеркал и переносим в обезличенный пакет запросов (`rw_data_request.md`).
- *Новый сбор российских кейсов Трека B (`S3`):* **отклонено** — достаточно переклассифицировать `W14-07/08` и добавить `benchmark_role` + `qualified_by_stage`.
- *Присвоение фиксированного числа `No-Go` без первичного доказательства:* **отклонено** — целевые `No-Go` получают отказ только при подтверждении критерия на уровне `орг × когорта × окно × продукт`; иначе остаются `Conditional` или `Insufficient-Evidence`.

---

## 3. Заранее зарегистрированный прогноз исходов по 11 кластерам (защита от подгонки)

| # | Кластер / организация | Первичный фокус проверки | Ожидаемый честный исход до сбора (pre-registered) |
|---|---|---|---|
| 1 | **СТНГ** (организатор Газстройпром дедуплицирован) | АП086548 (чартеры) vs АП086346 (ТМС); Ковыкта/Тас-Юрях/Амурский ГПЗ, горизонт 2027 | ТМС-часть → `NO-GAP (MARKET_COVERED)`. Чартерная часть → `Conditional` или `Go` только после `T1/T4/T5`. |
| 2 | **Газпром нефть / Газпромнефть-Снабжение** | Процедура `01-3027015-523-2026` (2027–2029): самолёт vs вертолёт, плечи `LED/TJM/OMS ↔ NUX` | `Conditional` до получения первичного ТЗ; при подтверждении самолётной вахты `LED↔NUX` — сигнал на ВС >2 355 км. |
| 3 | **Севернефтегазпром** | Лот `32616450256` (2026): маршруты, пересечение с Газпром авиа (`T4`) | `Conditional` или `No-Go (OWN_FLEET)`, если окно закрыто Газпром авиа. |
| 4 | **РН-Ванкор** (`UFA↔NUX`, `KJA↔IAA`) | Актуальный цикл 2026–2027, условие ≥150 мест в одном ВС и ≥700 кг багажа | Спрос подтверждён исторически, но по `K5` (2024 без нового ТЗ) потолок `Conditional`; 100Y SSJ100 не закрывает лот ≥150 мест целиком. |
| 5 | **Атомтехэнерго / Росэнергоатом / АЭМ-технологии** | Инженеры Димитровград (`ULY/KUF`), цепочка `ТМК-ИНОКС → ЗиО → БРЕСТ`; контроль `T2` на Курской-2 / Смоленской-2 / ЛАЭС-2 | Инженерный поток на удалённые АЭС → `Conditional`; Курская-2 / Смоленская-2 / ЛАЭС-2 → вероятный `No-Go (GROUND_ALT)`. |
| 6 | **Авиационный кластер Ростеха (`ОАК`, `ОДК`, `ВР`) + `ВСМПО-АВИСМА`** | Открытые гражданские площадки (`PEE↔IKT`, `SVX↔ULY/UFA/KZN`), бизнес-класс, тест узла `SVX`, заготовка обезличенного запроса | Строго `STRUCTURAL_HYPOTHESIS`, потолок `Conditional` + `[NEEDS-RW-DATA]`. |
| 7 | **РусГидро** (СШГЭС + штаб `KJA` / ДВ) | `KJA↔ABA` (проверка `T2` авто/ЖД), `KJA↔VVO` (дальность >3 000 км, частота) | `KJA↔ABA` вероятный `No-Go (GROUND_ALT)` или малый поток; `KJA↔VVO` — проверка `MARKET_COVERED` vs блок. |
| 8 | **РЖД (подрядчик Восточного полигона)** + **Почта России ХМАО** | 1 стройобъект (`KHV↔TYD`) с датой спада; приложение к `SBR035-260005476100908` (`SGC↔TJM`) | `Conditional` (проектный спад / малый объём) или `No-Go (GROUND_ALT / K6)`. |
| 9 | **Ведомственный флот и МВЛ (`Газпром добыча Ямбург`, `АЛРОСА`, `ФСК — Россети` Южное ПМЭС)** | Позитивная проверка `T4 (OWN_FLEET)` и несоответствия типа ВС (вертолёт/МВЛ) | `No-Go (OWN_FLEET)` на базовых программах Ямбурга и АЛРОСА (`OVB↔MJZ`); `ФСК` понижен до `Conditional` / отказ по самолётному чартеру Южного ПМЭС. |
| 10 | **Форумы 2027 (`ПМЭФ`, `ВЭФ`, `ИННОПРОМ`, `ЦИПР`, `ПМГФ`, `TNF`, `РЭН`, `КИФ`, `Транспорт России`)** | Даты 2027, 4 аэропорта Москвы раздельно, пиковое предложение vs обычный день, плательщик делегации | `ПМЭФ` (`MOW-LED`) и `ЦИПР` (`MOW-GOJ`) → `No-Go (MARKET_COVERED / GROUND_ALT)`; `Росконгресс` → `No-Go (FRAGMENTED_PAYER)`; `ИННОПРОМ-2027` (`LED↔SVX`) и `TNF` → `Conditional` на гарантированный блок. |
| 11 | **Финансовый сектор и институты развития (`Сбербанк`, `ВТБ`, `ГТЛК`, `ВЭБ.РФ`)** | Позитивные проверки `MARKET_COVERED`, `GROUND_ALT`, `LOW_MOBILITY`, `FRAGMENTED_PAYER` | `No-Go` по конкретным сценариям (дополнительный борт на ПМЭФ / делегация в СПб / лизинговый офис ГТЛК / общий блок КИФ). |

---

## 4. Замороженные схемы CSV Волны 2 (каталог `context/50_corporate_wave2_20261124/`)

Общий контракт: UTF-8, запятая, десятичная точка, даты `YYYY-MM-DD`, время с часовым поясом ISO-8601 (`YYYY-MM-DDTHH:MM+03:00`). Неизвестное число = **пустая ячейка** (никогда `0`, кроме доказанного нулевого наблюдения `0` рейсов при `probe_status=NO_SERVICE`); неизвестное перечисление = `UNKNOWN`. Разделитель в `evidence_ids` = `;`. **Запрещён код `MOW` во всех полях** (`SVO`, `DME`, `VKO`, `ZIA` всегда отдельно).

### A. `sites_and_links_graph.csv` (`SITE | ACCESS | LINK`)
```csv
row_id,row_type,site_id,site_name,site_kind,org_id,city_id,lat_deg,lon_deg,timezone,to_site_id,terminal_id,access_mode,access_km,access_min,link_type,supplier_tier,anchor_org_id,flow_type,event_id,active_from,active_to,peak_from,peak_to,decline_on,decline_trigger,evidence_status,evidence_ids,open_question
```

### B. `opportunities.csv` (направленные возможности по парам площадок)
```csv
opportunity_id,pair_id,from_site_id,to_site_id,from_iata,to_iata,gc_distance_km,graph_link_id,flow_type,event_id,period_from,period_to,beneficiary_org_id,organizer_org_id,buyer_org_id,payer_org_id,payer_status,procurement_channel,procurement_ref,demand_basis,demand_stage,as_of,requires_guaranteed_block,rail_acceptable,max_door_to_door_min,max_overnights,gap_status,gap_codes,t1_gap,t2_ground,t3_payer,t4_incumbent,t5_durability,decision,no_go_proof_type,recommended_product,decision_changing_fact,demand_evidence_ids,payer_evidence_ids,gap_evidence_ids
```
- `demand_basis`: `CONFIRMED_UNIT | STRUCTURAL_HYPOTHESIS`
- `t1_gap..t5_durability`: `PASS | FAIL | UNKNOWN | EXTERNAL_BLOCKED`
- `decision`: `Go | Conditional | No-Go | Insufficient-Evidence`
- `recommended_product`: `CORPORATE_FARE | SEAT_BLOCK | CHARTER | DEDICATED_PROGRAM | NONE | UNKNOWN`

### C. `supply_gap_pairs.csv` (датированные срезы расписания, ЖД, тарифов и последней мили)
```csv
supply_id,opportunity_id,pair_id,probe_id,travel_date_local,checked_at,season_from,season_to,market_scope,mode,probe_status,origin_terminal_id,dest_terminal_id,via_arr_terminal_id,via_dep_terminal_id,operator_1,service_no_1,dep_at_1,arr_at_1,operator_2,service_no_2,dep_at_2,arr_at_2,connection_type,min_connection_min,weekly_freq_physical,origin_access_min,dest_access_min,predeparture_buffer_min,door_to_door_min,extra_nights,lost_work_min,offered_cabin,equipment,checked_party_size,public_inventory_status,guaranteed_seats,guarantee_status,bag_allowance_kg,extra_bag_capacity_kg,fare_rub,fare_basis,fare_terms,evidence_ids,limitation
```

### D. `cohort_demand_scenarios.csv` (`PERIOD | WINDOW`, раздельные когорты и классы)
```csv
row_id,row_type,opportunity_id,pair_id,cohort_id,population_id,cohort_type,cabin_requirement,scenario,period_from,period_to,calendar_coverage,window_id,depart_not_before,depart_not_after,arrive_not_after,demand_basis,quantity_status,mobile_travellers,trips_per_traveller_period,od_share,round_trips_started,one_way_od_pax,required_seats_same_aircraft,extra_baggage_kg,split_allowed,evidence_ids,assumption_or_unknown
```
- `cohort_type`: `EXECUTIVE | LINE_MANAGEMENT | ENGINEERING | ROTATION | DELEGATION`
- `cabin_requirement`: `Y | J_REQUIRED | J_PREFERRED | UNKNOWN`
- `demand_basis`: `CONFIRMED_UNIT | STRUCTURAL_HYPOTHESIS`

### E. `pooling_and_nodes.csv` + `hubs_and_nodes_summary.csv`
```csv
plan_id,allocation_id,leg_no,demand_window_row_id,option_type,hub_iata,supply_id,flight_instance_id,from_iata,to_iata,dep_at,arr_at,cabin,allocated_od_pax,payer_org_id,demand_basis,capacity_status,allocation_status,evidence_ids,limitation
```
И сводка узлов `hubs_and_nodes_summary.csv` (единая методика для `SVX`, `TJM`, `OVB`, `KJA`, `LED`, `SVO`, `DME`, `VKO`, `ZIA`):
```csv
hub_iata,city_name,week_type,local_od_pax_base,connected_od_pairs_count,transit_od_pax_detour25_base,transit_od_pax_detour35_base,roundtrip_feasible_share_pct,compatible_pooling_groups,distinct_payers_count,event_peak_od_pax_base,demand_basis_scope,notes
```

### F. `evidence_wave2.csv` (дополнение к `evidence.csv` с обязательным `claim_type`)
```csv
evidence_id,source_url,issuer,document_date,checked_on,source_locator,claim_type,supported_claim,evidence_level,limitation
```
- `claim_type`: `IDENTITY | AFFILIATION | DEMAND_UNIT | GAP | PAYER | INCUMBENT | EVENT_DATE | BENCHMARK`

---

## 5. План исполнения Волны 2 (4 параллельных ресерчера → 2 последовательных воркера → 1 кросс-ревью)

### Этап А — 4 параллельные пачки `codex/gpt-6.1-terra` (`reasoningEffort: "xhigh"`)
Все сырые файлы пишутся в `context/50_corporate_wave2_20261124/raw/` с непересекающимися префиксами:

| Пачка | Зона ответственности | Пары (22 уникальные городские пары) | Выходные файлы |
|---|---|---|---|
| **`W2-T1`** | **Нефтегаз и EPC:** СТНГ (+ Газстройпром дедуплицирован), Газпромнефть-Снабжение (`01-3027015-523-2026`), Севернефтегазпром (`32616450256`), РН-Ванкор (`РН40302710`) + позитивный `No-Go (OWN_FLEET)` для Газпром добыча Ямбург. | `UFA↔NUX`, `TJM↔NUX`, `OMS↔NUX`, `LED↔NUX`, `KJA↔IAA`, `IKT↔MJZ` (+ наземный доступ Ковыкты/Жигалово) — **6 пар**. | `raw/w2_t1_sites.csv`, `raw/w2_t1_supply.csv`, `raw/w2_t1_demand_notes.md`, `raw/w2_t1_evidence.csv` |
| **`W2-T2`** | **Росатом и промышленная кооперация Ростеха:** Атомтехэнерго (Димитровград), Росэнергоатом (АЭС), АЭМ-технологии (`ЗиО-Подольск` / `ТМК-ИНОКС → БРЕСТ`), Ростех (`ОАК`, `ОДК`, `ВР`) + `ВСМПО-АВИСМА` (`STRUCTURAL_HYPOTHESIS` + журнал проверенных зеркал ПП № 301) + позитивный `No-Go (GROUND_ALT)` Курская АЭС-2 / Смоленская АЭС-2 / ЛАЭС-2. | `Москва(4 а/п)↔ULY/KUF`, `PEE↔IKT`, `SVX↔ULY`, `SVX↔UFA`, `SVX↔KZN`, `Москва(4 а/п)↔Курчатов/Десногорск` (+ `LED↔Сосновый Бор`) — **6 пар**. | `raw/w2_t2_sites.csv`, `raw/w2_t2_supply.csv`, `raw/w2_t2_demand_notes.md`, `raw/w2_t2_evidence.csv` |
| **`W2-T3`** | **Энергетика, транспорт, ведомственный флот и `No-Go`:** РусГидро (СШГЭС + ДВ штаб `KJA`), РЖД (1 подрядчик Восточного полигона со сроком спада), Почта России ХМАО (`SBR035-260005476100908`), ФСК — Россети Южное ПМЭС (проверка типа ВС для `S1`), позитивные `No-Go`: АЛРОСА (`OVB↔MJZ`, `OWN_FLEET`) и ГТЛК (`LOW_MOBILITY`). | `OVB↔MJZ`, `KJA↔ABA`, `KJA↔VVO`, `KHV↔TYD`, `SGC↔TJM` — **5 пар**. | `raw/w2_t3_sites.csv`, `raw/w2_t3_supply.csv`, `raw/w2_t3_nogo_and_notes.md`, `raw/w2_t3_evidence.csv` |
| **`W2-T4`** | **Календарь 2027 (`S2`), 4 аэропорта Москвы (`S7`), бизнес-класс по ТЗ ТМС и финсектор `No-Go`:** 9 ежегодных серий на 2027 год (вкл. проверку первичных ссылок ЦИПР/ИННОПРОМ/ПМГФ/TNF + ПМЭФ/ВЭФ/РЭН/КИФ/Транспорт России); 2–3 открытых ТЗ ТМС для калибровки доли `J`; позитивные `No-Go`: Сбербанк/ВТБ на ПМЭФ (`MARKET_COVERED`/`GROUND_ALT`), Росконгресс и ВЭБ.РФ (`FRAGMENTED_PAYER`). | `Москва(4 а/п)↔NUX`, `Москва(4 а/п)↔SVX`, `Москва(4 а/п)↔VVO`, `Москва(4 а/п)↔LED`, `LED↔SVX` (+ `Москва(4 а/п)↔GOJ` ЦИПР) — **5–6 пар**. | `raw/w2_t4_events_2027.csv`, `raw/w2_t4_supply.csv`, `raw/w2_t4_tmc_biz_and_nogo.md`, `raw/w2_t4_evidence.csv` |

### Этап Б — 2 последовательных воркера `codex/gpt-6.2-sol` (`reasoningEffort: "xhigh"`)
1. **`W2-S1` (Сборка графа, Supply Gap и патчи `S1/S2/S3/S4/S6/S7`):** читает `raw/w2_t1..t4` и `context/49_*`, вычисляет точные ортодромии `gc_distance_km` по координатам IATA, применяет патчи `S1/S2/S3/S4/S6/S7`, выпускает `organizations_screening_v2.csv`, `benchmarks_cases_v2.csv`, `events_calendar_2027.csv`, `why_not_registry_v2.md`, `sites_and_links_graph.csv`, `supply_gap_pairs.csv`, `evidence_wave2.csv`.
2. **`W2-S2` (Возможности, когорты, пулинг, естественные узлы и валидатор `S5`):** строит `opportunities.csv`, `cohort_demand_scenarios.csv`, `pooling_and_nodes.csv`, `hubs_and_nodes_summary.csv`, `validate_wave2.py` (закрывая `S5`, `P3`, `P4` и сверку с pre-registered исходами) и `wave2_handoff_to_wave3.md` (включая обезличенный блок запросов по закрытому контуру Ростеха для `rw_data_request.md`).

### Этап В — Независимое кросс-модельное ревью Волны 2
- Свежий делегат `antigravity/gemini-4-neon` (`thought_level: high`, read-only) после коммита `W2-S2`. Максимум 1 проход фиксов только на `blocker`, затем переход к Волне 3.
