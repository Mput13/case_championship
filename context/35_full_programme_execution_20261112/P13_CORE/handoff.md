# P13-CORE: review P06

**CHANGES — две находки S2** на `982f13d9b6c378ed9581125ecc5c40f17dade6a3`. SHA256 `P06/output_manifest.json`: `7d17d8db518669f0317bc9df4783a3bb035879b88edaf12d06c74870644bf057`, совпал.

1. **P13-F01, engine/core.py:241–245.** Действие после decision_date может изменить completed product или создать новый past cash event. Решение01.02 меняет январские20 поездок с тарифа120 на1200 RUB: revenue и январский operating cash2400→24000. Второй пример добавляет январский receipt400 RUB. Оба CONDITIONAL вместо INVALID.
2. **P13-F02, engine/core.py:237–240.** Защита committed_sales не охватывает contract carried/reserved. Удаление ранее заключённого SIGNED с30 пассажирами освобождает кресла: retail20→50, revenue7000→10000 RUB без отмены/возврата.

Полные причины, smallest fixes и acceptance — в `core_review.json`, краткая таблица — `findings.csv`. Для F01 достаточно запретить backdated actions и заморозить completed products/их производные начисления и cash; для F02 — не позволять стирать контрактные обязательства до появления поддержанной cancellation-модели. Строить такую модель для закрытия review не требуется.

18 независимых сценариев:15 PASS,3 counterexamples в двух findings,0 harness errors. Отдельный rerun авторских checks:41 PASS/0 FAIL/1 NOT_RUN(B18). Ранний P05 month/segment/common-policy сигнал закрыт в I06; это не принятие реального спроса.

Воспроизведение из любого cwd:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 /Users/a/agent-audit-2026-09/case_championship/context/35_full_programme_execution_20261112/P13_CORE/reproduce.py
```

Exit0 означает, что воспроизведение совпало с сохранёнными ожиданиями, включая принятые ошибочные случаи; он не означает APPROVE. Результаты: `independent_results.json`, `author_rerun_results.json`, `results/`; exact parent/adaptive inputs: `reproducer_inputs/`.

`source_pins.json` содержит commit/path/Git blob/SHA256 каждого материализованного файла; `source_verification.json` — личную сверку. `sources.csv` содержит владельца, git URI, дату, период, единицу, гранулярность, статус и coverage. Исходные row IDs контрпримеров — BOOKED/L1/PAST_RECEIPT/SIGNED/CONTRACT/RETAIL/MARCH; полные inputs сохранены без чужого полного fixture. P00R contract/schema прочитаны с `b7d74e67dd6c603db049b1915b1afec987e3b458`; остальные producer pins из задания остаются контекстом, не лично подтверждённым прогнозом.

Все искусственные величины имеют assumption_id `P13-A001`; реальный диапазон UNKNOWN, владелец/основание/чувствительность/способ уточнения — `assumptions_register.json`. Горизонт operating2027-01..2028-12, prelaunch cash с2026-12, moneyRUB/price_year2027; физические seats/segments отдельно от journeys. Разные programme evaluations делят одинаковый внешний рынок через отдельные экземпляры, а совместные продукты внутри evaluation делят кресла/спрос.

Stage A review завершён. Stage B: автор P06 исправляет F01/F02 в новой версии; координатор назначает fresh recheck exact нового SHA. Этот пакет не меняет subject, frozen данные и старые вердикты. Реальные P05/physical contracts/calibration, прогноз RW и UI вне review. Коммиты/пуш выполняет координатор только по `manifest.json`; исполнитель Git mutations не делал. Незавершённые producer inputs не объявлены экономическим отказом.
