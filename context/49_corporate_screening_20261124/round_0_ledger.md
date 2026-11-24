# Раунд 0 Консула — Pick-and-Graft, Finding Ledger и Frozen ТЗ Волны 1

Дата: **24.11.2026**. Ветка: `research/corporate-demand-20261124`.

## 1. Оценки Консула (Раунд 0 — до старта Волны 1)

| Член Консула | Модель и режим | Линза | Оценка | Главный вклад |
|---|---|---|---|---|
| **Strategist** | `codex/gpt-6.2-astra` (`xhigh`) | Domain Architect | **7/10** | Разделение юрлиц / плательщиков / возможностей; EPC-подрядчики «Газстройпром»/СТНГ (АП086548); «Атомтехэнерго»; спад Alliance/BHP (23→7 рейсов/нед); Флорида FPL; пропуск `Conditional` с `decision_changing_fact` в Раунд 1. |
| **Skeptic** | `antigravity/claude-opus-5-5` (`high`) | Evidence Critic | **6/10** | Закрытие ЕИС по **ПП РФ № 301** (visibility bias Ростеха/ОПК); калибровка по **ТЗ ТМС**; 4 статуса скрининга (`Insufficient-Evidence`); 5 тестов фальсификации `T1–T5`; исправление тезиса по НДС 0%; запрет на саморевью `sol` по `sol`. |
| **Quant** | `codex/gpt-6.2-sol` (`xhigh`) | Feasibility & Math | **6/10** | Жёсткие CSV-схемы до старта Волны 1; запрет превращать недельные суммы в кресла без направления/окна/класса; уточнение дальности SSJ-95B (~2 355 км ортодромии при `k=1,10`); формула обратного порога `DOC_max`; закрытие даты РН40302710 (`12.03.2024` / `22.03.2024`); автоматические предикаты. |
| **Minimalist** | `antigravity/gemini-4-neon` (`high`) | Pragmatist | **6/10** | Снятие субъективного порога `≥8.5/10` как условия `SHIP`; узаконивание `[EXTERNAL-BLOCKED]` в предикатах; двухуровневый скрининг (Tier-1 / Tier-2); фокус экономики Среза 1 на 2–3 контрастных пилотах; сокращение избыточных слоёв ревью. |

---

## 2. Lead Judgment: `Act On` (5 решений) и `Dismissed`

### `Act On` (принято в работу)
1. **Четыре статуса скрининга и разделение сущностей:** в Волне 1 применяются статусы `Candidate | Conditional | No-Go | Insufficient-Evidence` (финальный `Go` присваивается только после Волны 2 по 4 условиям `a–d` + тестам `T1–T5`). `Conditional` с заполненным `decision_changing_fact` проходят в Раунд 1. В реестре разделены `org_id` (по ИНН), `payer_channel` и `strategic_access` (акционерная близость Ростеха не влияет на оценку спроса).
2. **Карта доступности данных (ПП РФ № 301) и исправление факта НДС 0%:**
   - Закупки санкционных заказчиков (Ростех, часть дочек Росатома/ОПК) в ЕИС закрыты → 1 проверка → `[UNAVAILABLE]`, не сжигать ресерчеров и не путать отсутствие в ЕИС с отсутствием спроса.
   - Приоритетный источник физических единиц и доли бизнес-класса — **открытые ТЗ на услуги ТМС, вахту и фрахт** (ЭТП ГПБ, `zakupki.rosatom.ru`, ТЭК-Торг, РЖД, РусГидро, площадки EPC-подрядчиков вроде «Газстройпрома»).
   - **НДС 0% (пп. 4.3 п. 1 ст. 164 НК РФ, письмо Минфина № 03-07-11/104555):** распространяется и на пассажирский чартер вне Москвы/МО — не подавать как преимущество регулярки над чартером.
3. **Зафиксированные до старта CSV-контракты (Волна 1):** все 5 пачек `gpt-6.1-terra xhigh` сдают данные строго по единым заголовкам (`organizations_screening.csv`, `events_calendar_2026_2027.csv`, `benchmarks_cases.csv`, `evidence.csv`) с едиными перечислениями, локаторами источников и раздельной кодировкой `UNKNOWN` vs пустое число.
4. **Пять пачек ресерчеров + единый сборщик + независимое кросс-ревью:** 5 непересекающихся пачек `terra` (Секторы 1–2; Секторы 3 и 5; Секторы 4/6/7 + события + Issue #5; Трек B РФ; Трек B Мир) → `W1-Merge` (`sol`) + скрипт `validate_wave1.py` → кросс-модельное ревью `gemini-4-neon high` (чтобы `sol` не проверял сам себя).
5. **Исправление DoD и критерий честного отрицательного результата:**
   - Выпуск Среза 1 определяется бинарными предикатами `P1–P7` и **0 открытыми `blocker`** (оценки `/10` информационные).
   - `[EXTERNAL-BLOCKED]` после 1 проверенной попытки засчитывается в предикате как валидный `UNKNOWN / [NEEDS-RW-DATA]`.
   - **Заранее фиксируемый порог «есть спрос» для Волны 2:** пара проходит в финальный `Go`, только если выполнены (a) свидетельство в физических единицах/площадочной кооперации, (b) доказанный GAP по актуальному расписанию и ЖД (`T1–T2`), (c) определённый плательщик/канал (`T3–T4`), (d) Base-оценка на конкретном окне не ниже минимального порога блока (≥15–20 кресел на рейс для блока мест, либо ≥70–80 кресел/рейс для выделенного SSJ100 / ≥120+ для Ту-214). Если <3 пар проходят `a–d`, честный вывод для RW: *«для отдельной новой программы спроса недостаточно; коммерчески обоснованы только корпоративные тарифы/ТМС и точечные блоки/событийные чартеры»*.

### `Dismissed` (отклонено с обоснованием)
- *Отмена Раунда 1 Консула (Minimalist):* **отклонено** — Консул должен сам отобрать `Candidate + приоритетные Conditional` после Волны 1; экономим токены за счёт 1 кросс-модельного ревью (`neon`) + автовалидатора на Волне 1 вместо двойного прогона.
- *Полный отказ от Excel-книги и JSON-экспорта в Срезе 1 (Minimalist):* **отклонено** — формат «HTML-досье + XLSX + Memo» согласован с пользователем; делаем XLSX компактным на 2–3 контрастных пилотах с теми же входами, что в HTML.
- *Превентивное отключение `claude-opus-5-5` (Minimalist):* **отклонено** — пользователь явно указал держать Opus до лимита, и в Раунде 0 он дал ключевые замечания (ПП 301, ТЗ ТМС, T1–T5).
- *26-колоночная `opportunities.csv` уже в Волне 1 (Astra):* **перенесено в Волну 2** — в Волне 1 собираем юрлица, события и бенчмарки; детальные возможности по парам и окнам строим в Волне 2 только по отобранному шорт-листу.
- *Отдельный приоритет для Екатеринбурга (`SVX`) сверх остальных узлов (из старого `methodology.md`):* **исправлено по Opus + Sol** — `SVX` проверяется в Волне 2 ровно теми же графовыми метриками, что и все остальные узлы.

---

## 3. Замороженные схемы CSV для Волны 1 (обязательны для всех пачек `terra`)

Все файлы: UTF-8, запятая, стандартное экранирование, точка в числах, даты `YYYY-MM-DD`. У перечислений неизвестное = `UNKNOWN`, у чисел = пустая ячейка (никогда `0`!).

### A. `organizations_screening.csv`
```csv
org_id,inn,legal_name,parent_org_id,sector,scope_role,tier,anchor_org_id,geography,cooperation,own_air_coverage,market_coverage,payer_channel,strategic_access,status,no_go_proof_type,decision_reason,decision_changing_fact,evidence_ids
```
- `sector`: `DEFENCE_INDUSTRY | ENERGY | OIL_GAS | INFRA_TRANSPORT | MINING_MATERIALS | FINANCE_DEV | TECH_SCIENCE`
- `scope_role`: `STATE_GROUP | STATE_COMPANY | SUBSIDIARY | EPC_CONTRACTOR | EXTERNAL_SUPPLIER | EVENT_AGGREGATOR`
- `tier`: `TIER1_DEEP | TIER2_FAST` (Tier-2 допустим для очевидных `No-Go` / событийных `Conditional` вроде банков, Гознака, Почты, институтов развития)
- 6 критериев (`geography, cooperation, own_air_coverage, market_coverage, payer_channel, strategic_access`): `SUPPORTS | MIXED | LIMITS | UNKNOWN` (причём `strategic_access` — **информационный**, не даёт `Candidate` сам по себе!)
- `status`: `Candidate | Conditional | No-Go | Insufficient-Evidence`
- `no_go_proof_type`: для `No-Go` обязательно одно из `OWN_FLEET | MARKET_COVERED | GROUND_ALT | LOW_MOBILITY | FRAGMENTED_PAYER`; иначе пусто.
- `decision_changing_fact`: обязательно для `Conditional` и `Insufficient-Evidence` (какой 1 конкретный факт/ответ откроет или закроет кейс).

### B. `events_calendar_2026_2027.csv`
```csv
event_id,event_or_project,series_id,event_year,event_name,event_type,host_city,nearest_airport_iata,date_status,start_date,end_date,phase_or_decline_trigger,target_orgs_summary,payer_or_organizer,evidence_ids
```
- `event_or_project`: `EVENT | PROJECT`
- `event_type`: `FORUM | CONFERENCE | EXHIBITION | INDUSTRIAL_LAUNCH | INFRA_BUILD | OTHER`
- `date_status`: `CONFIRMED | PROVISIONAL | TBD | HISTORICAL_REF`

### C. `benchmarks_cases.csv`
```csv
case_id,case_name,country,buyer,operator,product,use_case,stage,outcome,key_terms,capacity_risk_owner,disruption_risk_owner,metric_code,metric_value,metric_unit,metric_period,currency,tax_basis,rf_transferable_term,rf_limit,evidence_ids
```
- `country`: ISO-2 (`RU`, `AU`, `EU`, `US`, `CA`, `DK` и др.)
- `product`: `CORPORATE_FARE | SEAT_BLOCK | CHARTER | SHUTTLE | REVENUE_GUARANTEE | TMC`
- `use_case`: `REGULAR | ROTATION | EVENT_ADHOC | EMERGENCY_ADHOC`
- `stage`: `OFFER | RFI | TENDER | AWARDED | OPERATED | PAID`
- `outcome`: `ONGOING | COMPLETED | CURTAILED | CANCELLED | NO_AWARD | UNKNOWN`
- `metric_code`: `UNIQUE_PAX | ROUND_TRIPS | PAX_SEGMENTS | LEGS | SEATS_PER_LEG | PAX_PER_LEG | BLOCK_HOURS | EXTRA_BAGGAGE_PER_LEG | ASK_AMOUNT | CONTRACT_AMOUNT | PAID_AMOUNT` (или пусто, если нет однозначной единицы; «80 рейсов» оставлять текстом в `key_terms`).

### D. `evidence.csv` (журнал первоисточников — свой файл на пачку, потом объединяется)
```csv
evidence_id,source_url,issuer,document_date,checked_on,source_locator,supported_claim,evidence_level,limitation
```
- `evidence_level`: `PRIMARY_CONTRACT | PRIMARY_TENDER | PRIMARY_REPORT | PRIMARY_SCHEDULE_TARIFF | SECONDARY_MEDIA | UNAVAILABLE_PP301 | UNAVAILABLE_TECH`
