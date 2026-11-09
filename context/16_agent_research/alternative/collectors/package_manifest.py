#!/usr/bin/env python3
"""Build the role-level source inventory from preserved bytes and module manifests.

Offline. Paths are relative to alternative/. Module originals remain untouched.
Dataset entries identify acquisitions, not statistically independent sources.
"""
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "alternative-package-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    if path.name.endswith(".csv.gz"):
        import io
        return list(csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode("utf-8"))))
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(path, records, fields=None):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def run():
    datasets, module_refs = [], []
    initial = json.loads((ROOT / "raw/initial_access.json").read_text())
    initial += [json.loads((ROOT / "raw/case5_page.access.json").read_text())]
    for i, rec in enumerate(initial):
        source = rec.get("source_url") or rec.get("url")
        path = rec.get("raw_path")
        if not path and rec.get("url") == "https://mai-way.ru/tasks/red-wings/":
            path = "raw/case5_page.html"
        name = rec.get("dataset_id") or "case5_page"
        is_history = name == "noaa_isd_history"
        datasets.append({"dataset_id": name, "source_url": source, "raw_path": path,
                         "sha256": sha(ROOT / path) if path else None,
                         "size_bytes": (ROOT / path).stat().st_size if path else None,
                         "retrieved_at_utc": rec.get("retrieved_at_utc"),
                         "publication_date": "UNKNOWN", "organisation": "NOAA" if name.startswith("noaa") else "Rosaviatsia" if "favt" in name else "MAI Way",
                         "grain": "station metadata" if is_history else "source document / diagnostic page",
                         "geographic_coverage": "World metadata" if is_history else "source-specific; not a demand table",
                         "temporal_coverage": "ISD metadata archive ended 2025-08-24" if is_history else "snapshot at retrieval",
                         "record_count": len(rows(ROOT / path)) if is_history else 1 if path else None,
                         "acquisition_status": "ACQUIRED_RAW" if path else "ACCESS_FAILED",
                         "value_status": "OBSERVED" if is_history else "UNKNOWN",
                         "license": "UNKNOWN", "key_fields": "USAF;WBAN" if is_history else "source_url;snapshot",
                         "units": "station; coordinates deg" if is_history else "document",
                         "limitations": "NOAA archive not updated after Aug 2025; station coverage must be checked" if is_history else "Context/format/access evidence only; no passenger observation",
                         "collector_version": VERSION, "command": "python3 context/16_agent_research/alternative/collectors/snapshot_inputs.py --fetch-support"})
    for rec in json.loads((ROOT / "raw/weather/acquisition_receipts.json").read_text()):
        datasets.append({**rec, "organisation": "NOAA NCEI / NODD", "grain": "station-hour rounded archived record",
                         "geographic_coverage": "NOAA CTRY=RS station " + rec["icao"],
                         "temporal_coverage": "2024 calendar year; station-specific gaps retained",
                         "record_count": rec.get("record_count"), "raw_path": rec.get("raw_path"), "sha256": rec.get("sha256"),
                         "acquisition_status": "PARSED" if rec["acquisition_status"] == "ACQUIRED_RAW" else rec["acquisition_status"],
                         "value_status": "OBSERVED", "license": "UNKNOWN (public NOAA archive; no specific licence text captured)",
                         "key_fields": "USAF;WBAN;UTC year,month,day,hour", "units": "temperature 0.1 degC; wind 0.1 m/s in raw",
                         "publication_date": "UNKNOWN",
                         "limitations": "ISD-Lite omits QC flags, visibility and gusts; irregular observation cadence; missing -9999 is not zero; no cancellation causation",
                         "collector_version": "weather-v1", "command": "python3 context/16_agent_research/alternative/collectors/weather.py --fetch"})
    ordinary = json.loads((ROOT / "raw/ordinary_airports.source.json").read_text())
    datasets.append({**ordinary, "dataset_id": "ordinary_airports_reused_core", "sha256": ordinary["compressed_sha256"],
                     "uncompressed_sha256": ordinary["sha256"], "size_bytes": ordinary["compressed_size_bytes"],
                     "value_status": "OBSERVED", "acquisition_status": "ACQUIRED_RAW",
                     "limitations": ordinary["limitations"] + "; reused byte-identical from core; our independent join validates codes/cardinality only"})
    for n, item in enumerate(json.loads((ROOT / "colleague_manifest.json").read_text())):
        git_source = item["git_source"]
        commit, git_path = git_source.split(":", 1)
        contaminated = git_path == "data/raw/favt_posts.csv"
        datasets.append({"dataset_id": "colleague_" + str(n) + "_" + Path(git_path).stem,
                         "source_url": "https://github.com/Mput13/case_championship/blob/" + commit + "/" + git_path,
                         "raw_path": item["path"], "sha256": item["sha256"], "size_bytes": item["size_bytes"],
                         "retrieved_at_utc": item["retrieved_at_utc"], "publication_date": "UNKNOWN",
                         "organisation": "case team; original upstream as named in file",
                         "grain": "colleague snapshot; " + ("post" if contaminated else "document/code/derived table"),
                         "geographic_coverage": "as specified in pinned team source",
                         "temporal_coverage": "2024-11-01/2026-11-09 publication snapshot" if contaminated else "pinned git object " + commit,
                         "record_count": len(rows(ROOT / item["path"])) if git_path.endswith(".csv") else 1,
                         "acquisition_status": "RESTRICTED_USE" if contaminated else "ACQUIRED_RAW",
                         "value_status": "UNKNOWN", "key_fields": "git_sha;path", "units": "source-specific",
                         "license": "UNKNOWN; upstream licences in source registry",
                         "condition": "PARSER_CONTAMINATION" if contaminated else "COLLEAGUE_INPUT_NOT_ACCEPTANCE",
                         "limitations": "Reply preview may replace main body. Original preserved; all old events quarantined. Never use as trusted event text or guaranteed lower bound." if contaminated else "Team statements/derivatives preserved for comparison; not new observations or independent confirmations",
                         "collector_version": VERSION, "command": "python3 context/16_agent_research/alternative/collectors/snapshot_inputs.py --git-only"})
    for module in ["business", "tourism", "telegram_correction"]:
        folder = ROOT / "modules" / module
        manifest = folder / "dataset_manifest.json"
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text())
        module_refs.append({"module": module, "path": str(manifest.relative_to(ROOT)), "sha256": sha(manifest),
                            "acceptance": "independently inspect module validation and limitations; manifest existence is not acceptance"})
        for original in data.get("datasets", []):
            entry = dict(original)
            if entry.get("raw_path") and not Path(entry["raw_path"]).is_absolute():
                entry["raw_path"] = str((folder / entry["raw_path"]).relative_to(ROOT))
            entry["module"] = module
            entry["module_manifest"] = str(manifest.relative_to(ROOT))
            entry.setdefault("value_status", entry.get("value_type", "OBSERVED"))
            entry.setdefault("publication_date", "UNKNOWN")
            entry.setdefault("organisation", "Rosaviatsiya via public Telegram HTML" if module == "telegram_correction" else "UNKNOWN")
            entry.setdefault("collector_version", data.get("collector_version") or data.get("parser_version") or "UNKNOWN")
            entry.setdefault("command", entry.get("reproduce_command") or entry.get("reproduce_offline") or
                             ("python3 context/16_agent_research/alternative/modules/telegram_correction/collectors/repair_telegram.py" if module == "telegram_correction" else "UNKNOWN"))
            if module == "tourism":
                indicator = entry["dataset_id"].rsplit("_", 1)[-1]
                entry.setdefault("units", "count of registered accommodation persons" if indicator in {"62073", "62074", "42102"}
                                 else "count of registered nights; metadata conflict retained for62302" if indicator == "62302" else "count of registered nights")
            if module == "telegram_correction":
                entry.setdefault("units", "public HTML page; extracted publication main/reply bodies, not operating events")
                entry.setdefault("key_fields", "post_id;source_page_sha256;parser_version")
            datasets.append(entry)
        existing = {r.get("raw_path") for r in datasets}
        for auxiliary in data.get("raw_auxiliary_files", []):
            path = str((folder / auxiliary["path"]).relative_to(ROOT))
            if path in existing or not auxiliary.get("source_url"):
                continue
            entry = dict(auxiliary)
            entry.update(dataset_id=module + "_support_" + Path(path).stem, module=module,
                         raw_path=path, module_manifest=str(manifest.relative_to(ROOT)), value_status="UNKNOWN",
                         collector_version=data.get("collector_version"),
                         command="python3 context/16_agent_research/alternative/modules/tourism/collectors/collect_tourism.py --fetch")
            datasets.append(entry)
    normalized = []
    for p in sorted((ROOT / "normalized").glob("*")):
        if p.is_file():
            normalized.append({"path": str(p.relative_to(ROOT)), "sha256": sha(p), "size_bytes": p.stat().st_size,
                               "record_count": len(rows(p)) if p.suffix == ".csv" else None})
    manifest = {"schema_version": "alternative-v1", "path_base": "directory containing dataset_manifest.json",
                "collector_version": VERSION, "datasets": datasets, "module_manifests": module_refs,
                "normalized_files": normalized, "input_refs": "input_refs.json", "updates": "input_refs_updates.json",
                "quarantine": "quarantine/parser_contamination_v0; untrusted original extraction, never active input",
                "source_independence": "NSED/EMISS mirrors and publisher primary share lineage. Colleague copies are not extra independent evidence."}
    (ROOT / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    fields = ["dataset_id", "module", "organisation", "source_url", "raw_path", "sha256", "size_bytes", "record_count",
              "retrieved_at_utc", "publication_date", "grain", "geographic_coverage", "temporal_coverage",
              "acquisition_status", "condition", "value_status", "key_fields", "units", "license", "limitations", "collector_version", "command"]
    write(ROOT / "source_registry.csv", [{k: r.get(k, r.get("value_type") if k == "value_status" else r.get("unit") if k == "units" else None) for k in fields} for r in datasets], fields)
    print(json.dumps({"source_entries": len(datasets), "modules": [r["module"] for r in module_refs], "normalized_files": len(normalized)}))


if __name__ == "__main__":
    run()
