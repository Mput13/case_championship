"""Проверить и запечатать только пакет expert_brief; не приёмка модели."""
from pathlib import Path
import csv
import hashlib
import io
import json
import re

OUT = Path(__file__).resolve().parent


def digest(b):
    return hashlib.sha256(b).hexdigest()


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


q = (OUT / "questions.md").read_text()
rows = json.loads((OUT / "source_rows.json").read_text())
inputs = json.loads((OUT / "input_manifest.json").read_text())
control = list(csv.DictReader(io.StringIO((OUT / "control_pair.csv").read_text())))
checks = {
    "questions_word_count_lte400_whitespace": {"passed": len(q.split()) <= 400, "count": len(q.split())},
    "seven_questions": {"passed": re.findall(r"^(\d)\. ", q, flags=re.M) == list("1234567")},
    "three_priorities_named": {"passed": "вопросы 1–3" in q},
    "profile_shift_cargo_present": {"passed": all(x in q for x in ["узел", "ресурсе", "почта", "специальная компоновка"])},
    "no_invented_cargo_money": {"passed": all(x in (OUT / "rationale.md").read_text() for x in ["Все три суммы сейчас UNKNOWN", "грузового KEEP", "не увеличивают пассажирскую метрику"])},
    "required_files": {"passed": all((OUT / x).is_file() for x in ["questions.md", "rationale.md", "show_materials.md", "handoff.md", "input_manifest.json", "source_rows.json", "control_pair.csv", "source_register.csv", "assumptions.csv"])},
    "selected_rows_have_source_hash_and_id": {"passed": all(x["source_row_id"] and len(x["source_file_sha256"]) == len(x["canonical_source_row_sha256"]) == 64 for x in rows["rows"]), "count": len(rows["rows"])},
    "sealed_binding_not_git_acceptance": {"passed": all(x.get("commit") is None for x in inputs["inputs"] if x["path"].split("/")[-2] in ["P10"] or "P09/early/" in x["path"])},
    "UFA_pair_control_arithmetic": {"passed": next(x for x in control if x["field"] == "physical_departures_week")["UFA-P04-BANK-EW"] == next(x for x in control if x["field"] == "physical_departures_week")["UFA-P05-DIRECT2"] == "24"},
}
assert all(v["passed"] for v in checks.values()), checks
save("validation.json", {
    "status": "PASS_PACKAGE_CONSISTENCY_ONLY", "checks": checks,
    "seal_payload_verification": "build_evidence.py asserted both user-supplied manifest hashes and every consumed sealed file hash",
    "not_run": ["RW demand calibration", "P06 model/economics", "P09 programme evaluation", "operational acceptance", "cargo adapter or cargo profit/funding", "external outreach", "HTML/browser UI QA; HTML not created"],
    "independent_review": "NOT_RUN; preparation package checked by its author",
})
files = []
for p in sorted(OUT.iterdir()):
    if p.name == "output_manifest.json" or not p.is_file():
        continue
    b = p.read_bytes()
    files.append({"path": p.name, "sha256": digest(b), "bytes": len(b)})
save("output_manifest.json", {
    "package": "expert_brief", "version": "EB-20261112-v2-network-cargo", "status": "READY_FOR_USER_FORWARDING_NOT_STAGE_B_ACCEPTANCE",
    "write_scope": "context/35_full_programme_execution_20261112/expert_brief/", "manifest_self_excluded": True,
    "files": files, "total_payload_bytes": sum(x["bytes"] for x in files),
    "git_operations": "NONE; coordinator commits the listed completed package and manifest",
})
print(json.dumps({"words": len(q.split()), "checks": len(checks), "payload_files": len(files), "bytes": sum(x["bytes"] for x in files), "manifest_sha256": digest((OUT / "output_manifest.json").read_bytes())}, ensure_ascii=False))
