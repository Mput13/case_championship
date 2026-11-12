"""Проверка и manifest только собственного готового review-пакета."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    pins = json.loads((ROOT / "source_pins.json").read_text())
    verified = []
    for pin in pins["files"]:
        p = Path(pin["local_path"])
        # Source paths stored relative to repo; verification also works from any cwd.
        relative = pin["local_path"].split("/P13_CORE/", 1)[1]
        p = ROOT / relative
        assert hashlib.sha256(p.read_bytes()).hexdigest() == pin["sha256"], relative
        verified.append(relative)
    parsed_json = []
    for p in ROOT.rglob("*.json"):
        if p.name != "manifest.json":
            json.loads(p.read_text()); parsed_json.append(str(p.relative_to(ROOT)))
    for filename in ["findings.csv", "coverage.csv", "sources.csv"]:
        with (ROOT / filename).open(newline="") as f:
            assert list(csv.DictReader(f)), filename
    review = json.loads((ROOT / "core_review.json").read_text())
    assert review["verdict"] == "CHANGES" and len(review["findings"]) == 2
    for finding in review["findings"]:
        for filename in finding["input_files"] + [finding["actual_result"]]:
            assert (ROOT / filename).is_file(), filename
    independent = json.loads((ROOT / "independent_results.json").read_text())
    assert independent["counts"] == {"PASS": 15, "FINDING": 3, "ERROR": 0}
    author = json.loads((ROOT / "author_rerun_results.json").read_text())
    assert author["counts"] == {"PASS": 41, "FAIL": 0, "NOT_RUN": 1}
    assert not list(ROOT.rglob("*.pyc"))
    validation = {"status": "PASS", "checks": ["Все materialized sources совпадают с pinned SHA256",
        "JSON/CSV читаются", "Findings ссылаются на существующие inputs/results",
        "Личные18 и отдельные author41/1 totals согласованы", "Нет .pyc/deps/build"],
        "verified_pinned_files": len(verified), "parsed_json_files_excluding_manifest": len(parsed_json),
        "meaning": "Согласованность review-пакета; не APPROVE ядра"}
    (ROOT / "package_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n")
    files = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            data = p.read_bytes()
            files.append({"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    manifest = {"package": "P13_CORE", "subject_commit": pins["subject_commit"],
                "subject_manifest_sha256": pins["actual_manifest_sha256"], "verdict": "CHANGES",
                "manifest_excludes": ["manifest.json"], "files": files,
                "file_count": len(files), "total_bytes_excluding_manifest": sum(p["bytes"] for p in files),
                "coordinator_action": "Коммитить только этот каталог по manifest; subject/ — минимальные exact blobs для воспроизведения, не правки P06"}
    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    (ROOT / "manifest.json").write_bytes(data)
    for record in files:
        assert hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
    print(json.dumps({"validation": "PASS", "files": len(files), "bytes": manifest["total_bytes_excluding_manifest"],
                      "manifest_sha256": hashlib.sha256(data).hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
