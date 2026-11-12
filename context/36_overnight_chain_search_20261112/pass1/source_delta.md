# Свежая дельта и допуск pass1

Team `cd04921fe5dd14dbf5c469b7f15a5efc203abc7b`, шаг1 `6cbe817320f75db9823984e7c4eeb6091fd7d996`. Минимальные P36 snapshots сверены с manifest; дополнительные точечные blobs лежат в inputs/ и source_manifest.json. Старые builders/verify не запускались. Local bb6e933 и published3010698 имеют одинаковое дерево; история не исправлялась.

P08/SVX/research_v1/HANDOFF.md: Stage A, U1/U12/U123/U1234 и RET; Stage B NOT_RUN, свободный парк UNKNOWN. Опубликованные own anchors GOJ/OMS/KUF/UFA реально найдены в `SVX_primary_schedule_products.csv`; recurrence, замкнутые возвраты и назначение хвостов в B2 — SCENARIO. UFA2 — параметр выбранного полного недельного сценария, не утверждение отмены реальных рейсов.

P08/MOSCOW/research_v1: KEEP_evidence и airport_status сохраняют ZIA BUS/TBS mixed-type и Tu TLV, DME CXR widebody, KGD historical. Ничто из этого не создаёт свободный RRJ; D international UNKNOWN. Исторический ангар ZIA не free capacity. Есть физические ZIA и DME, один MOW OD.

Название P08I проверено по реальным именам дерева: самостоятельного корня с таким именем нет, сам P08 существует (SVX и MOSCOW); international составляющая реально находится в P02I и P09/international. Прочитаны international_market_cards.csv, programmes.json и assumptions.json: не присваиваем международным заданиям domestic RUB formula.

P09/handoff.json: 178 конструкций/1958 evaluations, demand SCENARIO_NOT_IDENTIFIED, acceptance false; E1 существующего SSJ — отдельный несопоставимый subgroup. P15/integration_coverage.json и handoff.md связывают условные результаты/панель, не дают market/ops/финансовую истинность. P15 не изменялся.

Fresh шаг1 rw_routes_now совпадает по прочитанным CSV rows с P31 frozen input: **True**. Fresh network сохранён как provenance, его legacy настройки не заменяют P31/P34 P04/P05 и запрет PD8=RRJ. Основной численный prior — уже готовые1334пары/P31, не Wikipedia.

Все46старых P34 PUBLISHED_PATTERN_ONLY rows сохранены в inputs/p34_positive_service_preserved.csv с исходными датами/source IDs; положительный факт не обнуляется последующим UNKNOWN. Новые research-пакеты не читались. User completed-input gate: recovery COMPLETE/verify PASS по реальному пути P36/market_recovery/, numeric OD/netyield/resource updates0. WZ901 Sep24 ZIA–KGD secondary historical only, QUARANTINED для текущего RRJ/донора; P36-WEB1 на UNKNOWN других пар не source fact. BUS — IATA Батуми, не автобус. Root открыл official RW Georgia: ZIA–Batumi Tue/Fri/Sun08:10 mixed Tu/SSJ, exact tail UNKNOWN. Ops COMPLETE numeric updates0, не доказывает free tail/cheap overnight. Root admissions market_recovery_admission.md и operations_cost_admission.md — completed входы pass2, без ожидания и нового поиска.
