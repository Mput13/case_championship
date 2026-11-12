"""Assemble the narrow review and hash every output. Writes only this package."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
PREFIX = "context/35_full_programme_execution_20261112/"
SUBJECT = "b51a47cf93cc01ca899d18d2ef94d9340261963f"


def read(name):
    return json.loads((OUT / name).read_text())


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


results = read("results.json")
assert results["subject_commit"] == SUBJECT
assert results["counts"] == {"PASS": 41, "FAIL": 0}
verification = read("source_verification.json")
assert verification["subject_commit"] == SUBJECT
for package, count in [("P06", 101), ("P13_CORE_RECHECK", 30), ("P13_CORE", 45)]:
    assert verification["packages"][package]["payload_count"] == count
    assert verification["packages"][package]["tree_coverage_exact"]

limits = [
    "Все входы и суммы синтетические; это не RW forecast, оценка спроса или приёмка стратегии.",
    "Проверены F01-R1 и непосредственно затронутые даты. Рынок, полный KEEP, реальные договоры, транзакционная отмена/возврат и всеобщая корректность ядра вне scope.",
    "Дата решения имеет точность дня. Условие историчности строго date < decision_date; сам день решения не заморожен. UTC timestamps приводятся к UTC date, intraday не моделируется.",
    "Monthly-only дата для adaptive guard означает 1-е число. Это консервативная граница допустимости изменения, а не установленная фактическая дата начисления или платежа. Финансовое month-end размещение monthly платежей этим review не меняется.",
    "Ветка generated revenue без departure_date проверена на пяти точных AST helper-примерах. Публичный itinerary API требует departure_date и отклоняет отсутствующее поле до historical_ledger. First-leg fallback не заявлен как поддержка такого публичного входа.",
    "B21 — лично исполненный авторский код отдельного control; это не независимо спроектированный тест. I03 — лично повторённый frozen control. Авторские 11 regression, 42 suite и 3 CLI/API + invalid-manifest не засчитаны как независимая приёмка и полностью не перезапускались.",
    "F02 не переоткрыт и не получил новых gates; повторены только исходный erasure-воспроизводитель и frozen I03.",
    "Утверждение APPROVE ограничено exact subject b51a47cf93cc01ca899d18d2ef94d9340261963f / P06-1.0.2-adaptive.",
]
review = {
    "package": "P13_CORE_R2", "verdict": "APPROVE", "reviewer_role": "Independent narrow review sub-agent; no children",
    "subject_commit": SUBJECT, "subject_prefix": PREFIX + "P06/", "source_version": "P06-1.0.2-adaptive",
    "subject_manifest_sha256": "c8d1f7a6463e44b6072820c59ccecb8746cf0151f69fc06f4ed2f0f3c06d301d",
    "subject_payload_files": 101,
    "frozen_review_pins": {
        "P13_CORE_RECHECK": {"manifest_sha256": "a418149e30d1b70a4234e1674dc3cb74676e0e415f595b33a107425505267f6c", "payload_files": 30, "previous_verdict": "CHANGES", "unchanged": True},
        "P13_CORE": {"manifest_sha256": "85c2c9fc9ee9f5b548252671d597dd17ace6fc57523f822c18a9e66d859111a7", "payload_files": 45, "previous_verdict": "CHANGES", "unchanged": True},
    },
    "scope": "Close P13_CORE_RECHECK/F01-R1; check changed accrual date boundaries and requested frozen regression controls only.",
    "closure": {
        "P13_CORE_RECHECK/F01-R1": {
            "status": "CLOSED_FOR_TESTED_SCOPE", "original_severity": "S2",
            "reason": "Все три frozen residual-входа отвергнуты конкретным historical derived accruals or cash guard; будущие датированные начисления и reprice того же месяца сохранены.",
            "source_location": {"path": PREFIX + "P06/engine/core.py", "line_start": 296, "line_end": 326},
            "mandatory_residual_rejections": ["derived_same_month_dated_accrual_indirect", "derived_same_month_monthly_accrual_indirect", "derived_same_month_flown_revenue"],
            "mandatory_future_acceptance": ["future_same_month_dated_accrual", "future_same_month_product_reprice"],
        },
        "P13_CORE/F01": {"status": "CLOSED_FOR_TESTED_SCOPE", "basis": "Original two reproducers rejected; residual F01-R1 closed above. No claim of all possible adaptive histories."},
        "P13_CORE/F02": {"status": "PRIOR_CLOSURE_PRESERVED_FOR_TESTED_SCOPE", "basis": "Original erasure input and frozen I03 pass; no new contract gates."},
    },
    "findings": [],
    "personal_checks": {
        "counts": results["counts"], "total": 41,
        "frozen_original_reproducers": 3, "frozen_recheck_inputs": 8,
        "independent_adaptive_date_and_noop_checks": 16,
        "exact_AST_date_helper_checks": 5, "public_API_required_field_check": 1,
        "paired_fixed_comparisons": 6,
        "author_B21_code_independently_executed": 1, "frozen_I03_independently_executed": 1,
        "frozen_11_inputs": {"ContractError": 9, "accepted_CONDITIONAL": 2},
        "fixed_equality": {"reference_commits": ["982f13d9b6c378ed9581125ecc5c40f17dade6a3", "bb378f1e8bd3c621e83ccf50086f9ce15c6bb9ec"],
                           "interfaces": ["evaluate", "compare", "scenario"], "excluded_fields": ["engine_version recursively"], "all_other_fields_equal": True},
        "manifest_payloads_verified": 176, "tree_coverage_exact": True,
        "subject_inputs": "git show exact SHA:path; source modules executed in memory, no moving shared inputs accepted",
        "author_results_used_as_acceptance": False,
        "subject_or_frozen_edits": False, "git_mutations": False, "children": False,
        "external_or_paid_calls": False, "publications": False, "restarts": False, "dependencies_installed": False,
    },
    "limits": limits,
    "artifacts": {"results": "results.json", "runner": "reproduce.py", "coverage": "coverage.csv", "limits": "coverage_and_limits.md",
                  "source_verification": "source_verification.json", "source_read_set": "read_set.json", "source_inspection": "source_inspection.md", "helper_source": "source_snippets.json"},
}
save("review.json", review)

with (OUT / "coverage.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=["check_id", "origin", "expected", "status", "input", "results"])
    writer.writeheader()
    for row in results["checks"]:
        cid = row["check_id"]
        writer.writerow({k: row[k] for k in ("check_id", "origin", "expected", "status")} | {
            "input": "inputs/" + cid + ".json" if (OUT / "inputs" / (cid + ".json")).is_file() else "exact pinned code/example; see read_set.json",
            "results": "results/" + cid + "_adaptive.json" if (OUT / "results" / (cid + "_adaptive.json")).is_file() else "results.json#" + cid})

coverage = """# Границы перепроверки F01-R1

Вердикт **APPROVE** относится только к `b51a47cf93cc01ca899d18d2ef94d9340261963f`, P06-1.0.2-adaptive. Frozen-вердикты P13_CORE и P13_CORE_RECHECK не переписаны.

Проверены SHA256, bytes и точное покрытие Git tree для 101 payload P06, 30 payload P13_CORE_RECHECK и 45 payload P13_CORE. Ожидаемые SHA256 всех трёх manifest совпали. Все входы прочитаны через `git show exactSHA:path`. Исходники загружены в память; полные fixture-деревья и зависимости не копировались. Локальные snapshots в inputs содержат только выбранные обязательные и дополнительные малые входы. Выбранные исходники и их hashes доступны в read_set.json и source_inspection.md.

41 PASS, 0 FAIL: 3 неизменённых исходных воспроизводителя; 8 неизменённых frozen-входов предыдущей перепроверки; 16 самостоятельно построенных датированных adaptive/no-op границ; 5 прямых проверок точных AST helper-узлов; 1 проверка публичного обязательного поля; 6 парных fixed-сравнений; отдельные повторения B21 и I03. Каждый вид evidence указан в coverage.csv. B21 остаётся авторским тестовым кодом, хотя исполнен reviewer лично; I03 — прежним frozen control.

Три residual-входа получают ContractError с сообщением `adaptation rewrites historical derived accruals or cash`. Диагностический fixed-прогон показывает изменяемые до защиты величины: dated/monthly indirect cost 20→30 RUB и выручку выполненного рейса 6000→4000 RUB. Этот диагностический режим намеренно обходит adaptive-проверку и не является допустимым адаптивным результатом. Два future-входа принимаются: датированное начисление 20.02 при решении 15.02 и reprice будущего продукта, с выручкой 6000→7500 RUB. Всего обязательные 11 входов дают 9 ContractError и 2 ACCEPTED CONDITIONAL.

Для явного accrual_date проверены день до решения, сам день и день после; первое число; monthly-строка в accrual_date; timestamp с переносом в предыдущую UTC-дату и timestamp текущего UTC-дня. Для отсутствующей явной даты начисления проверены monthly 01.02 при решениях 01.02 и 02.02, а также будущий март. Generated revenue через дату продукта проверена на 14/15/16 февраля при решении 15 февраля; исторический no-op принимается. Все adaptive-прогоны проверяют отсутствие мутации входов.

Условие строго `< decision_date`: точная дата 15.02 остаётся допустимой 15.02, дата 14.02 историческая. При monthly-only `2027-02` guard использует 01.02: допускает изменение в этот день и запрещает со 02.02. Это граница точности дня и консервативного monthly guard, не утверждение о фактическом времени операции. Intraday не моделируется. Explicit future date 20.02 имеет приоритет над accrual_month=2027-02 и не замораживается.

Ветка generated revenue без departure_date получает дату первого физического плеча в прямых exact-AST helper-примерах на 14/15/16.02. При отсутствии обеих дат helper возвращает 01.02; explicit accrual_date имеет приоритет над продуктом/плечом. Однако `operations.py:108–134` требует departure_date и сверяет его с первым плечом. Публичный evaluate при отсутствующем поле получает ContractError `products: missing ['departure_date']` до historical_ledger. Следовательно, helper подтверждён отдельно, а публичная поддержка продуктов без departure_date не подтверждалась и не заявляется. Обязательный формат не расширялся ради этой проверки.

На exact примерах evaluate/compare/scenario все возвращаемые поля совпали с заново исполненными exact sources как 982f13d, так и bb378f1, после рекурсивного удаления только engine_version. Сохранённые author example results не использованы как oracle. Совпавшие нормализованные hashes записаны в results.json.

""" + "\n".join("- " + limit for limit in limits) + "\n"
(OUT / "coverage_and_limits.md").write_text(coverage)

handoff = """# Перепроверка F01-R1

**APPROVE** для exact subject `b51a47cf93cc01ca899d18d2ef94d9340261963f`, P06-1.0.2-adaptive. Остаточный `P13_CORE_RECHECK/F01-R1` закрыт в проверенном scope; новых findings нет.

Лично выполнено **41 PASS, 0 FAIL**. Все три frozen residual-входа теперь получают ContractError по historical derived accruals/cash. Оба будущих изменения внутри месяца допускаются. Прошлые derived cash/customer advance, исходные три reproducer, B21 и I03 сохраняют ожидаемое поведение. Fixed evaluate/compare/scenario совпали с заново исполненными 982f13d и bb378f1, исключён только engine_version. Все 176 payload трёх pinned manifest проверены по hashes/bytes и покрытию tree.

Датированная граница — строго раньше дня решения; сам день не заморожен. Monthly-only guard берёт первое число. Fallback generated revenue на первое плечо проверен напрямую на точных AST-узлах. Публичный API требует departure_date и отклоняет его отсутствие до этой ветви: это ограничение покрытия, не новая поддержка входа без даты.

Авторские 11 regression / 42 suite / 3 CLI/API + invalid-manifest — отдельные свидетельства автора; они не переобъявлены моей независимой приёмкой. Синтетические проверки не RW forecast. Рынок, полный KEEP, новые договорные gates и транзакционная отмена/возврат вне scope.

Воспроизведение из корня репозитория:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 context/35_full_programme_execution_20261112/P13_CORE_R2/reproduce.py
PYTHONDONTWRITEBYTECODE=1 python3 context/35_full_programme_execution_20261112/P13_CORE_R2/assemble.py
```

Результаты: review.json, results.json, coverage.csv, coverage_and_limits.md. Exact входы и подробные adaptive/fixed diagnostics сохранены в inputs/ и results/. Source pins: source_verification.json, read_set.json, source_inspection.md. Все payload перечислены с SHA256/bytes в output_manifest.json; manifest исключает только себя.

Запись ограничена P13_CORE_R2. Subject и frozen reviews не изменялись; Git mutations, дети, установки, внешние/платные вызовы, публикации и перезапуски не выполнялись.
"""
(OUT / "handoff.md").write_text(handoff)

# Preserve exact inspected lines with source hashes; never link a moving file as
# final evidence for a pinned conclusion.
reads = read("read_set.json")
inspection = ["# Проверенные исходники\n", "Exact subject: `" + SUBJECT + "`. Все номера строк относятся к этому Git blob.\n"]
for path, start, end in [("engine/core.py", 296, 326), ("engine/operations.py", 106, 134), ("engine/finance.py", 18, 65), ("engine/common.py", 7, 8)]:
    full = PREFIX + "P06/" + path
    raw = subprocess.check_output(["git", "show", SUBJECT + ":" + full], cwd=REPO)
    digest = hashlib.sha256(raw).hexdigest()
    assert reads[SUBJECT + ":" + full]["sha256"] == digest
    selected = raw.decode().splitlines()[start - 1:end]
    inspection += ["## " + path + "\n", "SHA256: `" + digest + "`.\n", "```text\n" + "\n".join(f"{i}: {line}" for i, line in enumerate(selected, start)) + "\n```\n"]
(OUT / "source_inspection.md").write_text("\n".join(inspection))

files = []
for path in sorted(OUT.rglob("*")):
    if not path.is_file() or path.name == "output_manifest.json":
        continue
    raw = path.read_bytes()
    files.append({"path": str(path.relative_to(OUT)), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
manifest = {"package": "P13_CORE_R2", "subject_commit": SUBJECT, "verdict": "APPROVE", "manifest_excludes": ["output_manifest.json"], "files": files}
save("output_manifest.json", manifest)
print(json.dumps({"verdict": review["verdict"], "checks": results["counts"], "payload_files": len(files),
                  "output_manifest_sha256": hashlib.sha256((OUT / "output_manifest.json").read_bytes()).hexdigest()}))
