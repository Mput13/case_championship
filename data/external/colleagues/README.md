# Файлы коллег, взятые в расчёт как есть

Скопированы командой `git show` из веток коллег 10.11.2026 (pull не делали). Это входные данные для проверки, а не подтверждённые факты.

| Файл | Ветка и коммит | Путь в ветке | Что это |
|---|---|---|---|
| omsk_outbound_week_20261207.csv | research/case5-raw-core-20261109 @ 505e246 | context/16_agent_research/core/branches/operating_evidence/normalized/ | вылеты из Омска на неделю 7–13.12.2026 по зимнему расписанию аэропорта |
| omsk_domestic_timetable_rows.csv | то же | то же | строки расписания аэропорта Омск с типом самолёта (aeroomsk.ru, w26-20261105.pdf) |
| od_registry.csv | research/red-wings-team-update-20261109 @ 93fa5cf | context/15_team_update/model/ | сценарии поездок по 73 парам и тарифы за поездку (допущения аналитика, не измерения) |
| primary_monthly_increments.csv | то же | то же | то же по месяцам |
| night_common_comparison.csv | research/night-morning-report-20261110 | context/23_night_run_20261110/checkpoint_0800/ | общее сравнение трёх сетей на неделю 7–13.12.2026 (вторая модель для проверки шага 3) |
| oms_ramp_week_flights.csv | research/direct-growth-delay-cargo-20261112 @ ffcc78d | context/30_defense_research_20261111/model_schedule/proposed_initial_flights.csv | сценарная неделя 6–12.09.2027: 44 рейса шести лучей Омска на двух самолётах и резерве (окно «Неделя двух самолётов») |
| oms_ramp_connections.csv | то же | …/model_schedule/connection_checks.csv | 110 стыковок в Омске той же недели и окно 45–240 минут |
| five_city_budget.csv | research/five-cities-distance-rule-20261112 @ e2bd5db | context/33_five_city_reassessment_20261112/common_economics/report.md | вклад сети шести городов при парке 2–7 самолётов (таблица отчёта, разобрана скриптом) |
| p09_programmes.csv | docs/case5-team-synthesis-20261109 @ b16c28c | context/35_full_programme_execution_20261112/P09/scenario_results.csv | вторая модель коллег на 24 месяца: прирост поездок и известной части результата по программам (поставки phased) |
| p10_type_productivity.csv, p10_threshold_scenarios.csv | то же | …/P10/ | пассажиров в год на один самолёт по типам и порог №2 по годам и сценариям рынка |
| p34_triangle_shuttle_controls.csv | research/direct-growth-delay-cargo-20261112 @ 4b8dc86 | context/34_new_direct_top5_20261112/final/CONTROLS.csv | треугольник Екатеринбург — Сочи — Минводы против челноков в Сочи и снятия старых рейсов, млн ₽ за февраль 2027 к тому же расписанию (соседние продажи по P05) |
| p36_new_pairs.csv, p36_programmes.csv | то же | context/36_overnight_chain_search_20261112/RESULTS.md (таблицы) | недельный перебор цепочек из Екатеринбурга: пять новых пар и три программы, млн ₽ за февраль 2027; аренда, база и полная прибыль не входят |

Последние пять файлов обновляет `py -3.13 src/fetch_colleague_research.py` (коммиты закреплены в скрипте и в research_manifest.json).
