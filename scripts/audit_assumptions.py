"""Инвентаризация объявленных входов и слабых критериев; без изменения модели."""
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/audit_20261111"
OUT.mkdir(exist_ok=True)

def write(name, rows):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def classification(path, source):
    s = source.lower()
    if path.stem in ("longlist_weights", "weight_profiles", "choice", "evidence_ladder"):
        return "решение / предпочтение команды"
    if "требование кейса" in s:
        return "условие кейса"
    if path.stem.startswith("subsidy_"):
        return "нормативная таблица; применимость требует проверки"
    if any(x in s for x in ("допущен", "оценка:", "подбор", "рассужден", "синтет")):
        return "допущение / расчётная оценка"
    if path.stem in ("range", "south_west_regions", "transfer_hubs", "resort_airports", "aircraft_seats"):
        return "аналитическое правило / перенесённый справочник"
    if not source.strip() or source.strip().lower() in ("то же", "то же: шаг перебора"):
        return "нет самостоятельного обоснования строки"
    return "заявлен источник; первичная сверка в этом аудите не выполнена"

files, register, manual = [], [], []
for folder in ("data/assumptions", "data/manual"):
    for p in sorted((ROOT / folder).glob("*.csv")):
        with p.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            rows = list(reader)
        source_fields = [k for k in fields if re.search(r"source|evidence|quote|why|status", k)]
        files.append({"file": p.relative_to(ROOT).as_posix(), "records": len(rows),
                      "fields": "; ".join(fields), "source_fields": "; ".join(source_fields),
                      "rows_without_source_text": sum(not any(r.get(k, "").strip() for k in source_fields) for r in rows),
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                      "scope": "входной справочник; наличие ссылки не равно проверке значения"})
        if folder != "data/assumptions":
            for line, row in enumerate(rows, 2):
                manual.append({"file": p.relative_to(ROOT).as_posix(), "csv_record": line,
                               "values": json.dumps({k: v for k, v in row.items() if k not in source_fields}, ensure_ascii=False),
                               "source_text": " | ".join(row.get(k, "") for k in source_fields if row.get(k, "")),
                               "verification": "первичная сверка строки не выполнена; слабые критерии отдельно в weak_criteria.csv"})
            continue
        for line, row in enumerate(rows, 2):
            key_field = next((k for k in ("parameter", "column", "iata", "type_raw", "region", "distance_band", "min_km", "value") if k in row), fields[0])
            key = row[key_field]
            if row.get("profile"):
                key = row["profile"] + ":" + key
            source = " | ".join(row.get(k, "") for k in source_fields if row.get(k, ""))
            cols = [k for k in fields if k not in source_fields and k != key_field]
            if "base" in row:
                value_cols = ["base", "cautious"]
            elif "value" in row and key_field != "value":
                value_cols = ["value"]
            elif "weight" in row:
                value_cols = ["weight"]
            else:
                value_cols = cols
            for col in value_cols:
                register.append({"file": p.relative_to(ROOT).as_posix(), "csv_record": line,
                                 "key": key, "field": col, "value": row[col], "unit": row.get("unit", ""),
                                 "classification": classification(p, source), "source_text": source,
                                 "verification": "классификация по содержимому файла; внешняя верификация значения не выполнена"})

criteria = json.loads((ROOT / "data/processed/criteria.json").read_text(encoding="utf-8"))
weights = {c["key"]: c["weight"] for c in criteria["criteria"]}
weak = []
for city, values in criteria["values"].items():
    for key, row in values.items():
        if row.get("v") is None or row.get("weak"):
            weak.append({"iata": city, "criterion": key, "weight": weights.get(key, 0), "value": row.get("v"),
                         "low": row.get("lo"), "high": row.get("hi"),
                         "reason": row.get("weak") or "значение отсутствует",
                         "source": row.get("s")})

write("input_files.csv", files)
write("assumptions.csv", register)
write("manual_records.csv", manual)
write("weak_criteria.csv", weak)
claims = []
def leaves(value, key):
    if isinstance(value, dict):
        for k, v in value.items():
            leaves(v, key + "." + k)
    elif isinstance(value, list):
        for k, v in enumerate(value):
            leaves(v, key + f"[{k}]")
    else:
        claims.append({"file": "data/manual/strategy_no2.json", "key": key, "value": value,
                       "verification": "текст стратегии; проверять источник и дату каждого утверждения отдельно"})
leaves(json.loads((ROOT / "data/manual/strategy_no2.json").read_text(encoding="utf-8")), "strategy")
write("strategy_claims.csv", claims)
report = ROOT / "docs/33_case_readiness_audit.md"
if report.exists():
    lines = report.read_text(encoding="utf-8").splitlines()
    findings = []
    requirements = []
    for line in lines:
        if re.match(r"\| A\d\d \|", line):
            values = [v.strip() for v in line.strip("|").split("|")]
            findings.append(dict(zip(["id", "priority", "observation", "impact", "next_action"], values)))
    start = lines.index("| Требование | Статус | Что есть | Что нужно закрыть |") + 2
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        requirements.append(dict(zip(["requirement", "status", "evidence", "remaining_work"],
                                     [v.strip() for v in line.strip("|").split("|")])))
    assert len(findings) == 24 and len(requirements) == 8
    write("findings.csv", findings)
    write("requirements.csv", requirements)
summary = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
           "input_files": len(files), "assumption_values": len(register), "manual_records": len(manual),
           "classification_counts": dict(Counter(x["classification"] for x in register)),
           "weak_or_missing_criteria": len(weak),
           "positive_weight_weak_or_missing": sum(float(x["weight"]) > 0 for x in weak),
           "limits": "Все CSV assumptions/manual инвентаризированы. Архив context и внешние URL построчно не переверифицированы. Структурные допущения разобраны вручную в docs/33_case_readiness_audit.md."}
(OUT / "metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
