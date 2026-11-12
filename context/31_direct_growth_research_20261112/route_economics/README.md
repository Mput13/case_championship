# route_economics — завершённый условный экран и API assembler

Подготовлен воспроизводимый вход для отдельной роли сборки сетей: **1 317 seed-пар сохранены, всего 1 334 городские пары, 26 980 строк fastscreen, shortlist 16 пар**. Числа — сценарный переменный результат относительно сценарного affected KEEP до неизвестных F и донора, в постоянных RUB 2026. **Полная дополнительная прибыль RW, actual cash и запуск не доказаны.** Новых observed OD, реализованных netyield и договоров — 0. Три итоговые сети здесь не собирались; глобальный оптимум не заявлен.

Область записи — только `route_economics/`. `calculate.py` импортирует закреплённый P05 для prior/профиля/тарифа/choice и P06 `allocate` для совместного распределения, а также завершённый `ops_inputs/calendar_engine.py` для переданного настоящего календарного запроса. Исходные модули не изменены. Сетевых запросов, установки пакетов, контактов, бронирований, коммитов и публикаций не было.

## Что передать assembler

- `APIhandoff.json` (также `API_handoff.json`) — интерфейс, параметры, ограничения и список таблиц.
- `route_universe.csv` — городские пары, оба направления, география, исходный пакет/сезон и физические варианты DME/ZIA. Включены 1 324 domestic, 9 supplemental international и один unresolved endpoint.
- `fastscreen.csv` — все domestic × физические альтернативы × 1/2/3/4/7 парных оборотов/неделю × BASE/CAUTIOUS × 2027/2028. Supplemental не получает выдуманной прибыли; для него отдельные threshold-only строки. Закрытые/остановленные метки прежнего snapshot сохранены отдельно от будущего разрешения.
- `shortlist.csv`, `candidate_score.csv` — 16 пар с обеими стресс-точками, break-even, перетоком, F/donor-порогами и UNKNOWN-блоками. `screen_priority` — порядок конечной выборки для проверки, не рейтинг доказанной прибыли.
- `directed_route_cases.csv` — восемь пар, направленные доли .20/.35/.50/.65/.80 и разные направленные сценарные gross-тарифы с повторным choice; равное число оплаченных физических плеч сохраняется.
- `frequency_increment_cases.csv` — старые + новые частоты, общий OD, вся выручка RW в P и KEEP, собственный переток отдельно.
- `patterns.json`, `route_patterns.csv` — 24 обычных return-pattern и 6 замкнутых треугольников; статус `pending_ops`. Дни 0=Mon…6=Sun **в этом адаптере**; у `ops_inputs` ISO 1…7, конверсию не угадывать.
- `pattern_calendar_cases.csv` — 48 фактически рассчитанных июльских сценариев spread/weekday/weekend для восьми пар. Частота и число оборотов отличаются явно. Наблюдённого DOW нет; преимущества дня недели не приписаны.
- `monthly_route_cases.csv` — оба направления по месяцам для этих восьми пар. Профиль — P05 carrier-season analogue, не OD наблюдение.
- `triangle_cases.csv` — 6 направленных замкнутых циклов × 2 сценария за июль. Все три плеча оплачены; каждое продаёт только свой adjacent OD. `KEEP=[]` здесь явный сценарий, а фактические affected RW/донор неизвестны. Обратный цикл не подразумевается бесплатно.
- `mechanism_thresholds.csv`, `support_cases.csv`, `competition_cases.csv`, `supplemental_thresholds.csv`, `ranges.csv` — количественные пороги и отдельные условные механизмы.
- `block_admission.csv` — все 13 направленных аналогов ops, без молчаливой перезаписи разных источников/модификаций; `ops_analogue_cost_cases.csv` — 20 парных cost-threshold случаев и одна строка missing reverse same variant. Это не dispatch blocks.
- `source_admission.csv`, `assumptions.csv`, `manifest.json`, `validation.json` — допуски, допущения, exact input/output SHA256 и проверки.

## Как читать лучшие условные строки

Таблица ниже — **млн RUB за 2027, до F, неизвестной фактической донорской работы и эксплуатационных gates**, NS. Для существующей пары учитывается вся совместная программа RW минус affected KEEP; для отсутствующей в старом snapshot пары нулевая старая частота — только явный сценарий, не доказанное отсутствие RW. Требуемые пассажиры — дополнительный платный объём сверх KEEP в расчёте на добавленное плечо при равном net. Они не подменяют общий endpoint OD и не задают LF.

| Пара | Добавлено пар/нед. | BASE условный Δ | CAUTIOUS та же частота | BE pax/добавленное плечо | Дополнительный блок |
|---|---:|---:|---:|---:|---|
| AER–SVX | 7 | 320.1 | −350.0 | 71.4 | ops, OD/yield, KEEP, F UNKNOWN |
| MRV–SVX | 7 | 285.8 | −420.6 | 72.1 | ops, OD/yield, KEEP, F UNKNOWN |
| SVX–VVO | 3 | 272.6 | −748.8 | 67.8 | 8h same-tail cost-screen превышен; тип/трасса/payload |
| KHV–SVX | 2 | 95.2 | −500.0 | 68.0 | 8h screen превышен; тип/трасса/payload |
| KJA–SVX | 2 | 53.5 | −226.5 | 71.9 | разные модификации blocks не объединены |
| IKT–SVX | 2 | 48.7 | −317.3 | 69.9 | 8h screen превышен; тип/трасса/payload |
| AER–VVO | 7 | 1095.8 | −929.0 | 67.0 | дальний costscreen; не готовый CaseSJ; base/positioning UNKNOWN |
| AER–KHV | 7 | 1074.2 | −1582.5 | 67.1 | дальний costscreen; не готовый CaseSJ; base/positioning UNKNOWN |
| MRV–VVO | 7 | 1055.7 | −1200.0 | 67.1 | дальний costscreen; не готовый CaseSJ; base/positioning UNKNOWN |
| KHV–MRV | 7 | 1035.5 | −1749.8 | 67.1 | дальний costscreen; не готовый CaseSJ; base/positioning UNKNOWN |
| GOJ–KUF | 1 | −18.8 | −66.9 | 82.6 | существующие 2/нед. только historical transfer scenario |
| GOJ–SVX | 1 | −21.1 | −96.8 | 76.1 | будущие частоты/переток UNKNOWN |
| CEK–MRV | 7 | 275.6 | −529.2 | 72.3 | конкурентный календарь UNKNOWN, не пустой рынок |
| MRV–TJM | 7 | 324.7 | −760.6 | 71.4 | Yamal target week/партнёрский контракт UNKNOWN |
| OMS–UFA | 1 | −12.2 | −82.0 | 75.6 | OD/yield, positioning, donor UNKNOWN |
| SVX–TJM | 1 | −4.7 | −46.5 | 76.1 | ground alternatives/OD/собственный переток UNKNOWN |

Выборка содержит 6 лучших условных строк с SVX, 4 вне SVX и 6 evidence-sensitive пар из completed-пакетов. Дальние строки намеренно показывают, где высокий сценарный тариф и prior дают привлекательный costscreen, но он ещё не имеет права войти в выполнимую сеть. Для них не установлена пригодная модификация/маршрут/payload/дневной оборот. Условия 8 BH — общая диагностическая ось, не экипажный закон и не запрет маршрута. Необходимы многодневный вариант/иная структура и подтверждённый тип; автоматически назначать новый Tu-214 нельзя.

У всех 16 строк та же частота отрицательна в CAUTIOUS. Причины меняются совместно: меньший P05 OD prior с годовым стрессом .962, сценарные VAT/distribution, расход топлива, ставки MRO/экипажа/навигации и аэропортовая корзина. Это демонстрация чувствительности недоказанных входов. **Это не вывод о неспособности всех прямых рейсов работать** и не вероятность исхода: stress points не калиброваны как прогноз или доверительный интервал.

Пример различия пассажиров и перетока: GOJ–KUF, +1 парный оборот/неделю, BASE — 5 320 дополнительных RW journeys/год, около 2 062 старых пассажиров перемещаются на новые сектора. Перетёкшие не объявлены новыми клиентами; одна старая выручка вычтена один раз. При net около 5 746 RUB нужно примерно 8 591 дополнительных journeys/год до F/донора. Уже известный условный Δ равен −18.8 млн: положительной допустимой потери донора при этих входах нет. Это не фактическая оценка текущей маршрутной прибыли RW.

## Учёт, спрос и единицы

`SnapshotDemand` меняет только путь P05 inputs на exact dceadc98 blobs audit. P05 prior/gravity, monthly profile, gross_fare, net_fare и коэффициенты переиспользованы. Городской годовой OD — prior, не пассажиры сегмента; potential = prior / .6. Направления .5 и месячная сезонность — отдельные P05-A02/A03 сценарии. Доля .6 здесь mapping/reference outside mass, **не универсальный захват RW**. RW choice зависит от тарифа, времени и частоты; новая аналитическая ось weekly frequency/reference3 зафиксирована RE-A03. OTHER_AIR — некалиброванный неограниченный composite, не выдуманные рейсы/кресла конкурентов. `price_match10` — отдельная условная ценовая среда, одинаковая в P/KEEP; это не оценка причинной реакции конкурента.

Fastscreen использует точный capped single-product частный случай P06. Финальный совместный API всегда вызывает P06 allocate на **одном направленном cityOD × month × scenario pool**, перераспределяя пассажиров между всеми датированными предложениями и общими physical seats. Обе московские альтернативы DME и ZIA получают один MOW pool. Старую MOW-частоту нельзя назначить целиком каждому аэропорту: solo MOW Δ оставлен UNKNOWN, а условный subtotal и максимальная сумма F+donor+неразмещённая старая RW-потеря раскрыты отдельно.

Gross P05: max(5200, 5200+6.3×(km−393)), 20kg one-way basket. Net: gross/(1+VAT)×(1−distribution). BASE regional VAT0 только условный eligibility сценарий, MOW и CAUTIOUS VAT .10; distribution .03/.08. Это не налоговое заключение и не реализованный yield. Legacy net-формула не используется и VAT/distribution второй раз не списываются.

Драйверы: block hours × P04 HIST fuel/MRO/crew/navigation + cycle fuel + aggregate ground/deicing на физическое плечо. BASE цена топлива — локальный published UFA136300 + uplift1696, перенесённые на сеть **явным RE-COST01/AUDIT-COST01 сценарием**, не реальные контракты 2027/28. CAUTIOUS161696 и ground96089/115307, deice15000/40000 — отдельные перенесённые stress points. Published UFA fee components не добавляются поверх aggregate ground. Fuel storage не добавлен автоматически. Расходы — ex-VAT references; фактическая возмещаемость/ставка/timing UNKNOWN и остаются в F. Месячная фиксированная payroll не прибавлена поверх исторического crew aggregate.

Непрозрачный `pax_cost`500/650 исключён из главного subtotal: его distribution/acquiring может уже находиться в P05 net. Это **не бесплатное обслуживание пассажиров**. `F_pax_max_RUB_per_incremental_pax` — доступный порог для непересекающегося остатка; `nonoverlap_pax_cost_stress_increment` отдельно показывает гипотезу, что вся корзина500/650 действительно дополнительна и не пересекается с net. Полный результат требует компонентного моста и реальных договоров.

`known_increment = (P_net_revenue−KEEP_net_revenue)−additional_known_cost`. Неизвестные aircraft-use/reserve/lease/base/startup/exit/positioning/дополнительный pax-cost/tax входят в **net incremental F**, а не подставляются нулями в full result. Максимальная совокупная сумма F+потеря донора равна этому условному subtotal; отрицательная величина не допускает неотрицательных новых затрат/потерь при данных входах. Донор за пределами affected KEEP учитывается один раз. Уже включённый в KEEP донор нельзя вычитать повторно. Невозвратные/неизбежные обязательства должны оставаться в обеих программах; платёжные даты и full company KEEP cash отсутствуют. Поэтому cash/funding/payback = UNKNOWN. Порог на оборот есть; фактические занятые борто-дни UNKNOWN, отдельная величина block-hours/8 подписана только как эквивалент.

Fastscreen датирует grid weekdays и число парных вылетов, но время 0.5+1.1×km/750 — **только геометрия затрат**, не эксплуатационный block и не готовый dispatch schedule. Оба направления и все обратные плечи оплачены. В календарных ops-requests геометрическая подстановка отсутствует; accepted minutes берутся только из переданного directed block. Published/historical analogue minutes остаются требует ops-check. Для SJ100/PD8 нет автоматического переноса SaM146 costs/допуска.

## Source admission после completed-input gate

Применены `source_review/README.md`, все R01–R27, findings и шесть `canonical_*.csv`; исходные Luna metadata superseded. S07 zia.aero не подтверждает SVX–TBS или тип на нём; reverse WZ1403 UNKNOWN. KUF–GOJ Mon/Fri — вторичный listing с исключениями 27/30 ноября и отдельной строкой30 декабря; March2027 позже December2026. Локальные часы18:20 UTC4→18:40 UTC3 дают80мин, не конфликт расписания. SVX–TBS9/week относится только к summer2026, KUF–TAS2/week — историческому2025/26. Yamal TJM–MRV target weeks UNKNOWN. SVX–BRU identity/country unresolved: domestic и численный маршрут не допущены, замена аэропорта догадкой не выполнена.

Ops analogue use отделён от общего costscreen: 398 исходных строк не свёрнуты в перезаписываемый dict по паре. Например, KJA→SVX RRJ-95LR и SVX→KJA RRJ-95B не образуют подтверждённый двусторонний LR или B оборот. Это missing block gate. Аэропортовые ограничения/закрытый snapshot, модификация, payload и фактическая трасса независимы. Ни500км от базы, ни конкурент, ни generic2300 не удаляют пару. Нет факта будущего закрытия из одного старого флага.

Raw TOCHNO в `context/30.../latest/...csv` существует и имеет SHA256 `aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53`. Это прежний audit snapshot, не Git-primary и не новый OD fact. Окружение context/28 с numpy/pandas доступно; здесь повтор использует стандартную библиотеку без pip/сети. Полный старый product pipeline и старые +44/+503/+388 здесь не заявлены повторёнными и не смешаны.

## Механизмы вне главного NS

NS: и маршрутная поддержка, и fuel credit =0 как намеренный counterfactual. CM оставлен UNKNOWN до operator/date/agreement/eligible flight volume/special fare/cofunding и fuel-taxpayer/volume/payment условий. Тариф при гранте должен пересчитываться вместе с choice/netyield. Fuel credit уменьшает fuel cost один раз, grant отдельно. Диагностики3024/32930 показаны отдельно от CM;185228 не принят как подписанный grant, среднее2026 не прогноз2027/28.

Партнёрский block: q20, sell-through10/16/20 — только конечные иллюстративные оси, не договор/продажи. `cmax=(s×netretail−other_cost−target)/q`, s≤q. q×c покупается один раз. RW agent page подтверждает продажу блоков RW, не право покупать/перепродавать Yamal; partner operating PAX не RW operating PAX. Другая часть расходов/гарантий UNKNOWN.

Cargo:100/300/500kg — оси threshold, не доступный остаток. Нужен принятый кг в пределах и payload, и объёма после пассажиров/багажа. `required net RUB/kg=(deficit+handling+extra fuel+displacement+target)/accepted kg`.4200kg/20.15m³ — опубликованный отсек, не residual; сделка и спрос UNKNOWN. Cargo не спасает слабое плечо автоматически.

Международные supplemental имеют количественные оси all-in paired cost1/1.5/2млн и net8/12/20тыс: это **иллюстративные координаты порога, не оценки цены/затрат данного маршрута**. Нужны FX/права/foreign tax/реальная трасса/тип/доступность борта/спрос. BRU даже в эти маршрутные оси не допущен. Новые Tu-214 не обязательны и не назначены CaseSJ.

## Вызов API

```python
import sys
sys.path.insert(0, '/home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/31_direct_growth_research_20261112/route_economics')
from calculate import evaluate_combined_programme

old = [dict(pattern_id='old', airports=['SVX','KUF','SVX'],
            weekdays=[0,4], departure_hour_utc=6)]  # явно выбранный сценарий
new = dict(pattern_id='add', airports=['SVX','KUF','SVX'],
           weekdays=[2], departure_hour_utc=6)
r = evaluate_combined_programme(
    old+[new], 'base', keep_patterns=old,
    start='2027-01-01', end='2028-12-31',
    existing_slots=1, delivery_scenario='S0', reserve_available=None)
```

`keep_patterns` обязателен. `[]` явно утверждает пустой affected own-flight scope только для этого сценария, не компанию без бизнеса. P должен включать все сохраняемые affected old patterns. MOW физически запрещён: выбрать DME/ZIA. Повтор pattern id/физического движения и незамкнутый цикл отклоняются. Перегоны должны стать отдельными оплачиваемыми legs; неизвестное positioning остаётся gate, а не бесплатным ресурсом.

Для интеграции ops передать `calendar_requests={'P': project_request, 'KEEP': keep_request}` и пустые pattern lists. Запросы `ops_inputs.calendar_engine` должны иметь одинаковый tail/resource calendar, общий block-case/turn scenario, согласованные directed blocks и выбранную модификацию. Multiple-source entries сначала явно отобрать по направлению/модификации/допуску; wrapper отклоняет silent overwrite. Если полный календарь не проходит, вернётся `INFEASIBLE_CALENDAR_COMPOSITION_NOT_TRIMMED` и UNKNOWN economics, без дохода от оставшихся плеч. Даже успешный календарь только CONDITIONAL: crew/MRO/dispatch UNKNOWN.

`demand_overrides`: ключ `SVX>KUF/2027-07` → potential journeys, одинаковый в P и KEEP. `extra_products` может связать один и тот же physical flight с несколькими cityOD/itinerary; P06 совместно сохраняет seats, а net journey fare учитывается один раз. Его источник/cohort/itinerary admission обеспечивает assembler. Через `donor_loss` и `omitted_F` можно получить условный полный Δ при явно заданных расходах; без любого из них full result =null. Кэш/финансирование этим не становятся известны.

E0/E1/E2, S0/S1/S1D6 и entry dates точно из общего audit-контракта; доH22027 новых SJ100 нет ни в какой роли. Published existing fleet не свободен. Нужны реальный donor и отдельный reserve. Часовой/назначенный-tail screen в API необходимый, не достаточный; сравниваются и P, и KEEP. Финальная сборка обязана дополнить P03 tail/crew/rest/MRO/location и P04 полный cost/cash ledger, а затем применить full P06 producer contract. Суммировать solo маржи запрещено.

## Проверка и повтор

Из папки исследования:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/28_end_to_end_audit_20261110/code/sandbox/venv/bin/python route_economics/calculate.py
PYTHONDONTWRITEBYTECODE=1 /home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/28_end_to_end_audit_20261110/code/sandbox/venv/bin/python route_economics/verify.py
```

`verify.py` проверяет money/tonnes/hours/roundtrip costs, fast-path против P06 с binding caps, DOW и leap year, частичный горизонт, общий MOW OD, own migration, несколько продуктов на общих креслах, P−KEEP/donor один раз, duplicate/незамкнутые patterns, E/S/reserve/раннийSJ, canonical gates, отсутствие ops block fallback, целостность источников и защиту436 tracked +146 файлов context/30. Две независимые пересборки важных outputs должны быть byte-identical; SHA256 в `validation.json`. PASS проверяет механизм и воспроизводимость, не спрос/допуск/прибыль.

**HANDOFF READY / STOP.** Дальнейшая роль — отдельный network assembler на общих входах. Новых исследований и финальных сетей здесь нет.
