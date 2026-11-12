"""Assemble this review's evidence and hash manifest; writes only beside itself."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PREFIX = "context/35_full_programme_execution_20261112/"
SUBJECT = "bb378f1e8bd3c621e83ccf50086f9ce15c6bb9ec"


def read(name):
    return json.loads((ROOT / name).read_text())


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


r = read("results.json")
assert r["counts"] == {"PASS": 25, "FAIL": 3}
assert {x["check_id"] for x in r["checks"] if x["status"] == "FAIL"} == {
    "derived_same_month_dated_accrual_indirect", "derived_same_month_monthly_accrual_indirect", "derived_same_month_flown_revenue"}
verification = read("source_verification.json")
finding = {
    "finding_id": "P13_CORE_RECHECK/F01-R1", "parent_finding": "P13_CORE/F01", "severity": "S2",
    "status": "OPEN", "title": "Прошлые производные начисления внутри месяца решения остаются изменяемыми",
    "subject_commit": SUBJECT, "file": PREFIX + "P06/engine/core.py", "line_start": 306, "line_end": 307,
    "related_locations": [PREFIX + "P06/engine/core.py:312", PREFIX + "P06/engine/finance.py:42", PREFIX + "P06/engine/finance.py:51"],
    "cause": "historical_ledger отбирает accrual_month < decision[:7], исключая весь текущий месяц. Неизменённый event может изменить quantity/amount через изменённый будущий driver, минуя affected_dates для самого event.",
    "smallest_reproducer": {
        "input": "inputs/derived_same_month_dated_accrual_indirect.json",
        "command": "PYTHONDONTWRITEBYTECODE=1 python3 context/35_full_programme_execution_20261112/P13_CORE_RECHECK/recheck.py",
        "parent": "Один TEST-рейс MARCH 10.03.2027 08:00–10:00 UTC; одно unchanged economic_event PAST_DERIVED: accrual_date=10.02.2027, accrual_month=2027-02, driver=block_hours(MARCH), rate=10, payment=10.04.2027. Продуктов/рынков/контрактов нет.",
        "action": "Решение 15.02.2027, effective_date=01.03.2027; единственное действие replace flights/MARCH с arrival_utc 10:00→11:00. Сам event не изменяется.",
        "expected": "ContractError: неизменяемое начисление 10.02 не может получить новую сумму по решению 15.02.",
        "actual": "CONDITIONAL: quantity 2→3, amount 20→30 RUB на accrual_date=10.02.2027; operating_result -20→-30. Апрельский производный платёж -20→-30.",
        "actual_result": "results/derived_same_month_dated_accrual_indirect_adaptive.json",
        "paired_fixed_diagnostic": "results/derived_same_month_dated_accrual_indirect_fixed_ledgers.json"
    },
    "corroborating_reproducers": [
        {"input": "inputs/derived_same_month_monthly_accrual_indirect.json", "actual": "Тот же обход без accrual_date; согласно adaptive_fix monthly date означает 1-е число, но февральское начисление тоже пропускается."},
        {"input": "inputs/derived_same_month_flown_revenue.json", "actual": "Рейс RW 10.02, решение 15.02 добавляет альтернативу 20.02 в тот же monthly pool. При оплате RW 28.02 новая защита принимает пересчёт уже выполненного рейса: 50→33.3333 поездки, earned revenue 6000→4000 RUB. Это не требование новой калибровки, а нарушение сохранения прошлого."}
    ],
    "smallest_fix": "Внутри historical_ledger выбирать исторические начисления по доступной дате относительно полного decision_date: явный accrual_date, для generated journey_revenue дата исходного продукта/первого физического плеча, при действительно только monthly дате — объявленное консервативное 1-е число. Сравнивать те же quantity/amount. Не замораживать все будущие датированные начисления текущего месяца.",
    "acceptance": [
        "Все три сохранённых residual-воспроизводителя получают ContractError.",
        "future_same_month_dated_accrual (20.02 при решении 15.02) и future_same_month_product_reprice остаются допустимыми.",
        "Исходные три воспроизводителя, B21, I03 и fixed regression сохраняют текущий результат."
    ]
}
review = {
    "package": "P13_CORE_RECHECK", "verdict": "CHANGES", "reviewer": "Independent narrow review sub-agent; not P06 author or root fix author",
    "subject_commit": SUBJECT, "subject_prefix": PREFIX + "P06/", "source_version": "P06-1.0.1-adaptive",
    "subject_manifest_sha256": verification["P06"]["manifest_sha256"], "subject_payload_files": 101,
    "frozen_review": {"path": PREFIX + "P13_CORE/", "base_commit": "982f13d9b6c378ed9581125ecc5c40f17dade6a3",
                      "manifest_sha256": verification["frozen_P13_CORE"]["manifest_sha256"], "payload_files": 45, "unchanged": True},
    "scope": "Closure исходных F01/F02 и непосредственно затронутые historical derived cash/accrual, будущие допустимые действия, fixed comparisons и очевидные ложные отказы в заявленном контракте.",
    "closure": {
        "P13_CORE/F01": {"status": "PARTIAL_NOT_CLOSED", "literal_original_reproducers": "2/2 REJECTED", "residual": "F01-R1: current-month past derived accruals"},
        "P13_CORE/F02": {"status": "CLOSED_FOR_TESTED_SCOPE", "literal_original_reproducer": "REJECTED", "boundaries": "carried/reserved/unknown commitment/contract rebind/bound product защищены; no-op, unbound future product и zero future-uncommitted contract removal допустимы"}
    },
    "findings": [finding], "personal_checks": {"counts": r["counts"], "total": 28,
        "independently_constructed_boundary_checks": 23, "frozen_original_reproducers_rerun": 3,
        "author_B21_rerun_separately": 1, "frozen_I03_control_rerun_separately": 1,
        "failures_are_three_reproducers_of_one_finding": True,
        "all_source_reads": "git show exact commit:path; verified manifests and read_set.json; in-memory modules",
        "historical_generated_payments": "Indirect block-hours payment and customer advance through added competitor both rejected",
        "fixed_regression": "Exact base-vs-candidate evaluate/compare/scenario output equality, recursively excluding only engine_version",
        "root_42_pass_claim_used_as_acceptance": False, "author_42_suite_rerun": False,
        "subject_edits": False, "frozen_review_edits": False, "git_mutations": False, "children": False,
        "external_or_paid_calls": False, "publication": False},
    "limits": ["Все числа синтетические и проверяют исполняемый контракт.", "Рынок, калибровка, полный KEEP, реальные договоры и приёмка всей программы вне scope.",
               "Не проверялись все 42 CE/boundary, CLI/API identity и полноценная отмена/возврат.", "APPROVE F02 относится только к перечисленным проверенным границам; общий verdict CHANGES относится только к этому патчу."],
    "results": "results.json", "coverage_and_limits": "coverage_and_limits.md", "source_verification": "source_verification.json"
}
save("review.json", review)

snippets = []
for path, start, end in [("P06/engine/core.py", 230, 245), ("P06/engine/core.py", 277, 285),
                         ("P06/engine/core.py", 296, 313), ("P06/engine/finance.py", 27, 43), ("P06/engine/finance.py", 44, 56)]:
    b = subprocess.check_output(["git", "show", SUBJECT + ":" + PREFIX + path], cwd=REPO)
    lines = b.decode().splitlines()
    snippets.append({"commit": SUBJECT, "path": PREFIX + path, "blob_sha256": hashlib.sha256(b).hexdigest(),
                     "line_start": start, "line_end": end, "lines": [{"line": n, "text": lines[n-1]} for n in range(start, end+1)]})
save("source_snippets.json", snippets)
with (ROOT / "coverage.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=["check_id", "origin", "status"])
    writer.writeheader()
    writer.writerows({k: x[k] for k in writer.fieldnames} for x in r["checks"])

(ROOT / "coverage_and_limits.md").write_text("""# Границы перепроверки

Закреплённый subject: `bb378f1e8bd3c621e83ccf50086f9ce15c6bb9ec`, P06-1.0.1-adaptive. Проверены все 101 payload P06 и все 45 payload frozen P13_CORE, их SHA256 и точное покрытие git tree. Исходники импортированы из `git show` в память; shared moving files не использованы как вход. Чужие fixture-деревья, зависимости и runtime-копии не создавались.

28 проверок: 25 PASS, 3 FAIL. Три FAIL воспроизводят один остаточный S2 в F01. Из 28 проверок 23 — независимо построенные границы, 3 — неизменённые исходные воспроизводители, 1 — отдельный повтор авторского B21, 1 — повтор frozen I03. Полные 42 авторские проверки и CLI/API identity заново не выполнялись и не засчитывались как независимые.

Исходные F01 reprice/backdated add и F02 erasure отвергнуты. Отдельно проверены косвенное изменение прошлого производного платежа и клиентского аванса; оба отвергнуты. Защита contract carried/reserved, сокращения, release_unused, перепривязки и связанного продукта работает в перечисленных примерах. Неизвестный committed_at не разрешает стирание контракта. Сохранённый контракт, сохранённая история, изменение несвязанного будущего продукта, удаление явно будущего нулевого незаключённого контракта и будущие действия внутри месяца принимаются. Консервативный отказ для unknown commitment соответствует adaptive_fix, а не объявлен новым дефектом.

Fixed evaluate, compare и scenario на exact P06 examples совпадают с base 982f13d9b6c378ed9581125ecc5c40f17dade6a3 после рекурсивного удаления только engine_version. Сохранённые historical result artifacts не переобъявляются текущими результатами; сравнение сделано новым исполнением обоих exact sources.

Найденная граница: historical_ledger игнорирует прошлые начисления в текущем месяце решения. Одно unchanged начисление с 10.02.2027 меняется по решению 15.02 через будущий driver. Вторая форма использует только monthly accrual, третья — выручку уже выполненного физического рейса и будущую альтернативу в том же monthly pool. Положительные dated-future controls оставлены для проверки минимальной правки: нельзя закрывать пробел замораживанием всего текущего месяца.

Все входы синтетические. Калибровка рынка, полнота KEEP и реальных договоров, параметры Red Wings, всеобщая корректность ядра и полная стратегия вне scope. Новых gates по ним не добавлено. Отмена/возврат не реализовывались. Нет изменений P06/frozen P13_CORE, Git mutations, дочерних агентов, платных/внешних вызовов или публикаций.

Воспроизведение из корня репозитория: `PYTHONDONTWRITEBYTECODE=1 python3 context/35_full_programme_execution_20261112/P13_CORE_RECHECK/recheck.py`, затем `python3 context/35_full_programme_execution_20261112/P13_CORE_RECHECK/assemble.py`. Первый процесс сохраняет FAIL как результат review и завершается кодом 0 при завершённом прогоне; не следует трактовать exit 0 как отсутствие findings. JSON inputs и actual accepted/rejected results сохранены рядом; повтор не меняет subject.
""")
(ROOT / "handoff.md").write_text("""# Перепроверка P06 adaptive

**CHANGES** на exact `bb378f1e8bd3c621e83ccf50086f9ce15c6bb9ec`, manifest `74b37e90d6221957e56e26e559b85d07bc58e3138458354c51db9fda568b67b1` (101 payload), P06-1.0.1-adaptive. Frozen P13_CORE проверен и не изменён.

Исходные 3 воспроизводителя отклонены; F02 закрыт в проверенном scope. F01 закрыт частично: **S2 F01-R1**, `P06/engine/core.py:306–307`. Отбор `accrual_month < decision[:7]` пропускает уже прошлые начисления месяца решения. Минимальный input: `inputs/derived_same_month_dated_accrual_indirect.json`. Решение 15.02 меняет длительность рейса 10.03; неизменённое начисление с accrual_date 10.02 меняется 20→30 RUB и принимается как CONDITIONAL. Expected: ContractError. Две дополнительные формы — monthly-only accrual и выручка выполненного 10.02 рейса (6000→4000 RUB) после добавления будущей альтернативы 20.02.

Минимальная правка: отбирать прошлые derived accruals по полной доступной дате, сохраняя консервативный monthly fallback; для generated journey revenue использовать дату продукта/первого плеча. Положительные действия 20.02 при решении 15.02 должны оставаться допустимыми.

28 проверок: **25 PASS, 3 FAIL одного S2**. B21 и I03 PASS; прошлые производные cash и аванс защищены; fixed evaluate/compare/scenario совпали с base после исключения только engine_version. Рыночная калибровка, полный KEEP и реальные договоры не были gates этого review. Код/inputs/results, coverage и hashes: review.json, recheck.py, coverage_and_limits.md, output_manifest.json.
""")
save("handoff.json", {"verdict": "CHANGES", "subject_commit": SUBJECT, "review": "review.json", "handoff": "handoff.md",
                      "severity": "S2", "finding": "P13_CORE_RECHECK/F01-R1", "F01": "PARTIAL_NOT_CLOSED", "F02": "CLOSED_FOR_TESTED_SCOPE", "checks": r["counts"],
                      "coordinator_thread": "91bc9ad6-4e9f-4954-8714-1e4366064b78", "coordinator_environment": "d463a92a-a497-4213-aeb8-69f0a1470b87", "delivery_mode": "auto"})
payload = [x for x in ROOT.rglob("*") if x.is_file() and x.name not in ("output_manifest.json", "package_validation.json")]
for p in payload:
    if p.suffix == ".json":
        json.loads(p.read_text())
save("package_validation.json", {"all_json_parse": True, "expected_counts_match": True, "one_S2_three_reproducers": True,
                                 "only_review_output_path_written": True, "full_fixture_or_dependency_copies": False})
files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "output_manifest.json")
assert not any("__pycache__" in p.parts or p.suffix == ".pyc" for p in files)
save("output_manifest.json", {"package": "P13_CORE_RECHECK", "subject_commit": SUBJECT, "verdict": "CHANGES",
                              "manifest_excludes": ["output_manifest.json"], "files": [
                                  {"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in files]})
print(json.dumps({"verdict": "CHANGES", "payload_files": len(files), "manifest_sha256": hashlib.sha256((ROOT / "output_manifest.json").read_bytes()).hexdigest()}))
