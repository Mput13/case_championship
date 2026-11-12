"""Собрать review-артефакты из сохранённых проверок; только каталог P13_CORE."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMIT = "982f13d9b6c378ed9581125ecc5c40f17dade6a3"
PREFIX = "context/35_full_programme_execution_20261112/P06/"
CREATED = "2026-11-12T13:17:36Z"


def write_json(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def write_csv(name, rows):
    with (ROOT / name).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    independent = json.loads((ROOT / "independent_results.json").read_text())
    author = json.loads((ROOT / "author_rerun_results.json").read_text())
    pins = json.loads((ROOT / "source_pins.json").read_text())
    findings = [
        {
            "finding_id": "P13-F01", "severity": "S2", "status": "OPEN", "commit": COMMIT,
            "file": PREFIX + "engine/core.py", "line_start": 241, "line_end": 245,
            "related_locations": [PREFIX + "engine/core.py:72", PREFIX + "engine/core.py:230", PREFIX + "engine/finance.py:44"],
            "title": "Adaptive может пересчитать прошлые поездки и добавить прошлый платёж",
            "trigger": "Решение 01.02.2027; action.effective_date=01.02.2027; изменение продукта уже выполненной поездки 10.01.2027 или добавление нового cash_event за январь.",
            "cause": "Защита исторических записей обходит только parent flights/cash_events. Продукты и автоматически генерируемые cash/accrual не заморожены; новые записи отсутствуют в parent-цикле. effective_date проверена относительно decision_date, но не связана с датой затронутой записи.",
            "expected": "ContractError/CLI INVALID: запрет изменения выполненного продукта/его заработанного тарифа и запрет backdated add в adaptive-действии.",
            "actual": "evaluate принимает CONDITIONAL: 20 январских поездок × 120 RUB превращаются в 20 × 1200; revenue и январский operating cash 2400→24000 RUB. Второй пример создаёт +400 RUB cash 01.01 решением 01.02.",
            "impact": "Недопустимое улучшение исторической выручки, cash и финансирования при сравнении adaptive-кандидатов. Fixed-режим этим примером не опровергнут.",
            "smallest_fix": "В check_adaptation запретить add с фактической датой записи раньше decision_date; для changed/removed records связать effective_date с периодом действия. Заморозить выполненные products и их тариф/cash_profile, а также прошлые начисления и производные платежи. Корректировку фактов отделять от feasible adaptation, если она понадобится; для закрытия этой находки новый механизм корректировок не требуется.",
            "checks": ["I15_adaptive_historical_product_reprice", "I16_adaptive_new_backdated_records"],
            "input_files": ["reproducer_inputs/F01_historical_reprice.json", "reproducer_inputs/F01_backdated_add.json"],
            "actual_result": "results/F01_historical_reprice_actual.json",
            "acceptance": "Оба сохранённых примера отвергнуты; контроль I18 остаётся отвергнут, документированное изменение будущего продукта в авторском B21 остаётся допустимо.",
        },
        {
            "finding_id": "P13-F02", "severity": "S2", "status": "OPEN", "commit": COMMIT,
            "file": PREFIX + "engine/core.py", "line_start": 237, "line_end": 240,
            "related_locations": [PREFIX + "engine/choice.py:107", PREFIX + "engine/choice.py:112"],
            "title": "Adaptive удаляет контрактных пассажиров и повторно продаёт их кресла",
            "trigger": "В parent есть заключённый контракт SIGNED: 30 reserved/carried на будущем рейсе 10.03.2027. Решением 01.02.2027 передан action remove contracts/SIGNED без модели отмены, возврата или переноса.",
            "cause": "Охраняются economic_events с committed_at и product.committed_sales. Контрактные carried/reserved не входят в эту проверку; наличие документированного action само по себе разрешает удалить обязательство.",
            "expected": "ContractError/CLI INVALID: сохранение законтрактованных поездок/невысвобождённого блока либо явная поддержанная модель отмены; её реализация не нужна для запрета текущего обхода.",
            "actual": "evaluate принимает CONDITIONAL: contract passengers 30→0, retail 20→50 на тех же 50 креслах, revenue 7000→10000 RUB, без refund/cancellation event.",
            "impact": "Ранее закреплённый спрос и ресурс освобождаются без цены обязательства; adaptive-программа получает недопустимую выручку и инвентарь.",
            "smallest_fix": "В check_adaptation переносить защиту booked journeys на parent contracts: запретить удаление/сокращение ранее закреплённых carried и невысвобождённого reserved inventory или изменение их привязки к продукту/legs. До появления модели отмены такие изменения отвергать. Если контрактный статус остаётся неизвестен, не принимать его стирание как feasible adaptation.",
            "checks": ["I17_adaptive_contract_passengers_disappear"],
            "input_files": ["reproducer_inputs/F02_contract_erasure.json"],
            "actual_result": "results/F02_contract_erasure_actual.json",
            "acceptance": "Сохранённое удаление SIGNED отвергнуто. Fixed allocation I03 с явно заданным release_unused продолжает сохранять спрос и кресла.",
        },
    ]
    coverage = [
        ("C01", "Идентификаторы, manifest, immutable inputs", "I01;I06", "PASS_SCOPED", "core.py:20;core.py:162", "24 закреплённых blob; 21 материализованная запись subject сверена с output_manifest; полный upstream архив не хешировался"),
        ("C02", "24 месяца и UNKNOWN/0", "I02;I07", "PASS_SCOPED", "core.py:49;core.py:129", "2027-01..2028-12; отсутствующий месяц INVALID; UNKNOWN сохраняет null"),
        ("C03", "Общие датированные кресла и физические IDs", "I03;I04", "PASS_SCOPED", "operations.py:6;choice.py:69", "Два физических SSJ100 analogue legs; marketing alias не создаёт кресла; реальные P02 кресла не admitted"),
        ("C04", "Контракты, один тариф, through и recapture", "I03;I05", "PASS_FIXED_SCOPE", "choice.py:87;finance.py:44", "45 поездок/70 сегментов/9500 RUB при held5; release даёт50; отдельная находка adaptive F02"),
        ("C05", "Реакция конкурента и ранний сигнал P05", "I06", "PASS_SCOPED_SIGNAL_CLOSED", "choice.py:12;core.py:171", "Одна политика P/KEEP; Jan leisure freq2→3 включает скидку100→80; Feb и business не активируют январскую leisure-ветку"),
        ("C06", "Ввод, резерв, ТО, позиция, crew UNKNOWN", "I08;I09", "PASS_SCOPED", "operations.py:37", "Невыполнимый ввод/позиция/ТО/резерв блокируют allocation; crew UNKNOWN явно conditional; полного dispatcher нет"),
        ("C07", "Будущий KEEP, донор, общие затраты, P−KEEP", "I09", "PASS_SCOPED", "core.py:162;finance.py:113", "KEEP360/P505/дельта145 RUB, own migration учтён один раз; idle lease сохранён событием producer"),
        ("C08", "Accrual/cash, предзапуск, лаг, terminal/deposit", "I10", "PASS_SCOPED", "finance.py:113;finance.py:231", "Ненулевой opening payable; bridge residual0; receivable70, deposit25 и будущие payments сохранены"),
        ("C09", "Opening cash, minimum cash, interest/preinterest", "I11", "PASS_SCOPED", "finance.py:69;finance.py:175", "Opening25/floor10; month need12/day52/preinterest5; UNKNOWN interest скрывает полный need, UNKNOWN principal не стирает need"),
        ("C10", "Project/company funding boundary", "I12", "PASS_SCOPED", "core.py:182", "Project27 RUB; company UNKNOWN без baseline и115 RUB с явно полным synthetic KEEP cash"),
        ("C11", "Adaptive parent/hash/information/commitments", "I14;I15;I16;I17;I18", "CHANGES_F01_F02", "core.py:217", "Parent/hash/future facts/locked econ/history flight controls PASS; past generated cash и contracts bypass подтверждены"),
        ("C12", "F07 metric adapter", "I13", "PASS_SCOPED", "core.py:101;core.py:173", "Journey shares с явной endogenous denominator policy; несовместимый business_scope отвергнут; без адаптера share/rank null"),
        ("C13", "Сценарии и совместный пересчёт", "Авторские CE02;B09", "AUTHOR_RERUN_PASS_CODE_READ", "core.py:248;core.py:262", "Ранее сохранённые standalone деньги не складываются; численная независимость по этому helper не заявлена"),
        ("C14", "P02/P04 evidence adapters", "Чтение adapters.py; B18 NOT_RUN", "CODE_READ_BOUNDARY", "adapters.py:22;adapters.py:30", "Source export не physical admission; future rates null. Полные P02 таблицы и реальные контракты не проверялись"),
        ("C15", "Реальная сеть RW, калибровка, прогноз, UI", "За пределами задания", "NOT_ASSESSED", "README.md", "Нет реального P05/полных contracts/company KEEP; это заявленные границы, а не дополнительные findings ядра"),
    ]
    write_csv("coverage.csv", [dict(zip(["coverage_id", "area", "checks", "status", "subject_locations", "limit"], row)) for row in coverage])
    write_csv("findings.csv", [{
        "finding_id": f["finding_id"], "severity": f["severity"], "status": f["status"], "commit": f["commit"],
        "file": f["file"], "line_start": f["line_start"], "line_end": f["line_end"], "title": f["title"],
        "expected": f["expected"], "actual": f["actual"], "impact": f["impact"], "smallest_fix": f["smallest_fix"],
        "checks": ";".join(f["checks"]), "reproducer_inputs": ";".join(f["input_files"])
    } for f in findings])
    source_rows = []
    for i, pin in enumerate(pins["files"], 1):
        source_rows.append({"source_id": "P13-SRC-%02d" % i,
            "url": "https://github.com/Mput13/case_championship/blob/" + pin["commit"] + "/" + pin["path"],
            "git_uri": "git:" + pin["commit"] + ":" + pin["path"],
            "organization_or_owner": "P06 gpt-6-astra xhigh" if "/P06/" in pin["path"] else "P00R upstream contract",
            "retrieved_date": "2026-11-12", "source_date": "2026-11-12, закреплённый commit",
            "period": "Код/контракт; модельный горизонт2027-01..2028-12, cash с2026-12 в fixtures",
            "unit": "Исходный код/JSON/CSV; денежные значения синтетические RUB",
            "granularity": "Exact git blob", "status": "PINNED_PERSONALLY_READ_OR_RUNTIME_DEPENDENCY",
            "coverage": "Только указанный файл и версия; не внешнее подтверждение рынка",
            "commit": pin["commit"], "path": pin["path"], "sha256": pin["sha256"], "git_blob": pin["git_blob"]})
    write_csv("sources.csv", source_rows)
    write_json("assumptions_register.json", {
        "assumptions": [{"assumption_id": "P13-A001", "selected_by": "Независимый reviewer P13-CORE",
            "value": "Все числа/даты/веса/пороги и explicit zero в reproduce.py — искусственные граничные примеры",
            "unit": "RUB, journeys, passenger segments, seats, minutes, UTC, hours; frequency — единый toy-unit внутри каждого теста",
            "basis": "Простая проверяемая арифметика; значения выбраны для изоляции инвариантов, а не для имитации RW",
            "range_or_unknown": "UNKNOWN для настоящих параметров RW. Эти точки не доверительные интервалы",
            "sensitivity": "I02 missing/unknown/zero; I03 held/released; I05 reversed order; I06 frequencies2/3 and other cells50; I08 resource one-field perturbations; I11 interest/principal coverage; I15 fare120/1200; I17 delete contract30",
            "numerical_tolerance": "math.isclose abs_tol=1e-6 и стандартный rel_tol=1e-9, только арифметика тестов",
            "affected_conclusions": "Верность реализации и два контрпримера adaptive; не спрос/экономика/сеть RW",
            "refinement": "Не требуется калибровка для инвариантов; реальные расчёты требуют принятия producer inputs координатором"}],
        "real_RW_parameter_selection": False,
    })
    review = {
        "package": "P13_CORE", "role": "Независимый review фактического ядра P06", "reviewer": "fresh Sol6.1 xhigh",
        "created_at": CREATED, "verdict": "CHANGES", "subject_commit": COMMIT,
        "subject_manifest_sha256": pins["actual_manifest_sha256"], "manifest_match": True,
        "severity_definition": "S2: существенная ошибка допустимости adaptive-кандидата с неверным численным результатом; локализована, не общий отказ fixed-арифметики",
        "findings": findings,
        "personal_checks": {"actual_code_read": ["engine/core.py", "engine/choice.py", "engine/operations.py", "engine/finance.py", "engine/common.py", "engine/adapters.py", "engine/fixtures.py", "engine/__main__.py"],
                            "independent": independent["counts"], "independent_total": len(independent["checks"]),
                            "author_rerun_separate": author["counts"], "source_verification": "source_verification.json",
                            "independent_fixture_origin": "reproduce.py; авторские fixtures используются только в отдельном rerun",
                            "no_subject_modification": True, "no_children": True, "no_git_mutations": True},
        "P05_early_signal": {"status": "CLOSED_FOR_TESTED_CASE", "check_id": "I06_response_month_segment_common_policy",
            "code": [PREFIX + "engine/choice.py:16", PREFIX + "engine/core.py:171"],
            "evidence": "Единый response_policy; разные активации P/KEEP без суммирования месяцев/сегментов. Коэффициенты синтетические; реальный P05 не admitted."},
        "scope": "Исполняемая корректность conditional engine на exact subject. Не прогноз RW, не проверка652 сетей, не UI, не глобальный optimum",
        "not_claimed": ["APPROVE всего ядра", "Рабочая годовая RW сеть", "Калибровка P05", "Принятие реальных P02 кресел/P03 ресурса/P04 будущих ставок", "Ранг№2 или дата окупаемости", "Независимое воспроизведение42/42 авторских checks"],
        "limits_file": "coverage_and_limits.md", "next_owner": "Координатор",
        "stage_B": ["Автору P06 исправить только F01/F02 в новой версии; текущий subject не изменён",
                    "Координатору назначить fresh recheck изменённого exact SHA; этот вердикт frozen",
                    "Принятие real P05/physical contracts/калибровки и совместного P/KEEP остаётся интеграцией producer inputs, не новой обязанностью review ядра"],
    }
    write_json("core_review.json", review)
    (ROOT / "coverage_and_limits.md").write_text("""# Покрытие и границы P13-CORE

Вердикт **CHANGES** относится к P06 `982f13d9b6c378ed9581125ecc5c40f17dade6a3`. Две находки S2 затрагивают feasible adaptation: недопустимое изменение прошлой выручки/cash и стирание контрактных пассажиров. Отдельный вердикт всей fixed-ветке не выдаётся; её перечисленные механизмы прошли указанные проверки.

Лично прочитаны фактические модули core, choice, operations, finance, common, adapters, fixtures и CLI. До сборки handoff CLI прочитан отдельно. Manifest SHA256 совпал с заданным; материализованные модули/документы сверены с его записями. Все чтения выполнены через exact Git blobs, рабочая P06 не импортировалась.

В `reproduce.py` независимо построены 18 сценариев: 15 PASS и 3 подтверждённых контрпримера, сгруппированных в 2 находки; ошибок harness нет. Примеры не используют авторские fixtures. Это проверка инвариантов с ожидаемыми дробными поездками; числа не параметры RW. В отдельной серии лично повторена 41 авторская проверка, все PASS. B18 не запускалась: она требует копирования полных P02 таблиц; это не независимое подтверждение author42/42. Код адаптера прочитан; source export не повышен до physical inventory, P04 references не повышены до будущих ставок.

Ранний сигнал P05 о межмесячном/межсегментном суммировании закрыт в проверенном случае I06. Одна и та же политика применена в двух программах: KEEP frequency2 не включает ответ, P frequency3 включает снижение конкурентного gross fare100→80. Частоты50 другого месяца и другого сегмента не срабатывают в этой ячейке. Никакие materialized response_rules не передавались как разные политики. Реальные коэффициенты и единицы требуют принятия P05.

Проверены общий demand, dated seats, held/released contract inventory, through revenue, recapture, ресурсные запреты, crew UNKNOWN, будущий KEEP и донор, общие затраты, accrual/cash с ненулевыми opening cash и payable, prelaunch, лаг получения, terminal balances/deposits, interest и preinterest, календарный minimum cash, project/company funding, metric adapter F07. Таблица `coverage.csv` указывает проверку, код и границу по каждому направлению.

Кресла, рынки и ресурс здесь искусственные. В реальном использовании P02v2 остаётся SOURCE_EXPORT; P03v2 — датированный diagnostic11–17.12.2028, не год и не свободный парк; P04 reference costs не ставки будущего SJ-100/ПД-8; accepted P05/real contracts/calibration не проверены. SSJ100_TEST_ANALOGUE не объявлен SJ-100 с ПД-8. Отсутствие этих producers не включено в findings ядра.

Не оценивались все старые сети, выбор лучшей программы, реальный бюджет компании, судебная/налоговая применимость, dispatcher/crew-duty/slots/payload-range, живой UI, Site или dashboard. UNKNOWN не заменялся нулём; явные toy zero относятся только к своим сценариям. Сценарные точки не являются доверительными интервалами.

После завершения Stage A остаётся адресный Stage B: исправление двух обходов автором P06 и новый назначенный координатором review другого SHA. Интеграция принятых P05/P03/P04 и real contracts — отдельная работа координатора; ожидание этих входов не требуется для завершения данного review. Frozen subject и прежние вердикты не изменены. Дети, внешние сообщения за пределами согласованного сообщения координатору, платные сервисы, перезапуски и Git mutations не использовались. Зависимости не устанавливались; временные runtime/build каталоги не создавались.
""", encoding="utf-8")
    (ROOT / "handoff.md").write_text("""# P13-CORE: review P06

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
""", encoding="utf-8")
    write_json("handoff.json", {
        "package": "P13_CORE", "status": "REVIEW_COMPLETE_CHANGES", "verdict": "CHANGES", "subject_commit": COMMIT,
        "subject_manifest_sha256": pins["actual_manifest_sha256"], "findings": ["P13-F01", "P13-F02"],
        "independent_counts": independent["counts"], "author_rerun_counts": author["counts"],
        "manifest": "manifest.json", "details": "core_review.json", "human_handoff": "handoff.md",
        "coverage": "coverage.csv", "limits": "coverage_and_limits.md", "source_pins": "source_pins.json",
        "assumptions": "assumptions_register.json", "writing_boundary": str(ROOT),
        "git_mutations": False, "subject_mutation": False, "new_agents": False,
        "frozen_verdict": True, "remaining_owner": "Координатор: авторская правка P06 и новое независимое recheck-задание на новый exact SHA",
    })
    print("Собраны core_review.json, findings.csv, coverage, sources, assumptions, handoff")


if __name__ == "__main__":
    main()
