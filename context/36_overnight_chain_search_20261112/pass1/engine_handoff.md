# Handoff pass1 → pass2

Пакет завершён локально. Следующий проход должен прочитать completed admission новых research, затем объединение представителей категорий, а не весь thin screen. Свежий WZ901 snippet quarantined и не источник борта/донора. Старые positive P34 primary/dated rows остаются фактами с исходными scope/date.

Входы: shortlist.csv, shortlist_requests.json, shortlist_full_schedules.csv (KEEP/WITHOUT_NEW/REPLACE), action_map.csv, graph_edges.csv, economics_screen.csv, baseline_definitions.json, contracts.json, source_manifest.json. request задаёт целые closed weekly jobs с UTC минутами от2027-02-01T00Z; ISO weekdays преобразуются в P31 weekdays0..6 ровно один раз.

API существующий: P31 route_economics.calculate.evaluate_combined_programme и choice_bundle; P03 ops_inputs.calendar_engine.generate ISO1..7. Не вызывать старые build/verify. P34 keep_patterns / retained_patterns дают исправленный P32 FOLLOW. Сам full-month P31 старый short-horizon bug не исправлен глобально: требовать Feb01–28 и freq=dated departures*7/28,4повтора.

Для лидеров собрать три одинаковые оболочки флота: KEEP; те же removal/retiming/swap без новых; REPLACE. Выполнить совместный P05/P06 monthly direct+own/through/contract пересчёт на общем cityOD/dated seats, не суммировать solo margin и не вычитать donor второй раз. three_state_screen уже finite-pool-aware, но analytic preliminary без dated-seat и through: не выдавать за producer acceptance.

Ranking критерий нового: REPLACE minus WITHOUT_NEW с той же отменойC. Даже если WITHOUT_NEW выиграл уKEEP, это самостоятельная альтернатива. Старые потери move/swap, unknown занятость/D, station/overnight/setup/reserve_F и cancellation vsKEEP не нули. Москва — conditional existing RRJ, внешний internationalD UNKNOWN; CXR B777/Tu и старый ангар не ресурс. Для регионов только closed origins и платные ferry, не новая база.

Из shortlist взять union по SVX/Moscow, RT/triangle/4+/multiday,0/1/multiple removals/real swap/move, с фокусом UTC-consistent ≤8BH. RESOURCE_8BH_QUEUE и отрицательные category comparators не победители; отсутствие нужного физического класса объясняется shortlist_category_coverage/rejection_counts. Пределы поиска в search_space, оптимума нет.

Дальше stress turn90, holds30/60/120 по каждому плечу и следующему заданию; actual crew/rest/MRO/slot/AFM gates. Реальные netfare/demand/fuel/airport avoidability вместо сценариев только с допущенными completed источниками. Costscreen full100_cap/fuel_price_break_even_full100/netfare_break_even_full100 — потолок/пороги, не спрос. Класс с отрицательным осторожным full100_cap не спасает более широкий поиск при тех же cost/fare; менять можно только доказанные input/threshold assumptions.

S0/S1 Aug/Nov2027 entry и S1D6 Feb/May2028 — только resource cases, не обещанные поставки. Нельзя SJ до H22027/entry, нельзя переносить RRJ операционные характеристики на PD8. Main fullmonthFeb4weeks, другие месяцы по действительному календарю.

Права: запись только pass1 до этого handoff; далее STOP. NO commit/push/merge/reset/checkout.1418 protected неизменны. Research in-progress не читались; никаких внешних поисков, субагентов и панели.
