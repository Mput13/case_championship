#!/usr/bin/env python3
"""Offline byte/provenance and known-primary-example checks; no event scores."""
import csv
import gzip
import hashlib
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
HEADERS = {"content-type", "content-length", "last-modified", "etag", "date", "cache-control", "retry-after"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((BASE / "dataset_manifest.json").read_text())
    coverage = json.loads((BASE / "coverage.json").read_text())
    original = BASE.parents[4] / "context/16_agent_research/alternative/raw/colleague/data/raw/favt_posts.csv"
    assert digest(original.read_bytes()) == manifest["original_sha256"] == coverage["original_sha256"]
    by_html_hash = {}
    for record in manifest["datasets"]:
        data = (BASE / record["raw_path"]).read_bytes()
        assert digest(data) == record["sha256"], record["raw_path"]
        assert len(data) == record["size_bytes"]
        html = gzip.decompress(data) if record["compression"] == "gzip" else data
        assert digest(html) == record["uncompressed_sha256"]
        by_html_hash[record["uncompressed_sha256"]] = html
    for field in ["normalized_files", "acquisition_diagnostics"]:
        for record in manifest.get(field, []):
            assert digest((BASE / record["path"]).read_bytes()) == record["sha256"], record["path"]
    rows = list(csv.DictReader((BASE / "normalized/main_posts.csv").open()))
    assert len(rows) == 8705 and len({r["id"] for r in rows}) == len(rows)
    assert min(int(r["id"]) for r in rows) == 575 and max(int(r["id"]) for r in rows) == 9279
    recovered = [r for r in rows if r["body_status"] == "MAIN_TEXT_RECOVERED"]
    for row in recovered:
        assert row["value_type"] == "OBSERVED" and row["text"] == row["main_text"]
        assert int(row["distinct_main_bodies"]) == 1
        assert f'data-post="favt_info/{row["id"]}"'.encode() in by_html_hash[row["source_page_sha256"]]
    unknown = [r for r in rows if r["body_status"] != "MAIN_TEXT_RECOVERED"]
    assert all(r["value_type"] == "UNKNOWN" and not r["text"] for r in unknown)
    selected = {r["id"]: r for r in rows if r["id"] in {"4685", "4687", "6503", "8772"}}
    for pid in ["4687", "6503"]:
        assert "СНЯТЫ" in selected[pid]["text"] and "ВВЕДЕНЫ" not in selected[pid]["text"]
        assert "ВВЕДЕНЫ" in selected[pid]["reply_preview_text"]
        assert selected[pid]["text"] != selected[pid]["reply_preview_text"]
    assert "сняты" in selected["4685"]["text"].lower() and "введены" in selected["4685"]["text"].lower()
    if "8772" in selected and selected["8772"]["body_status"] == "MAIN_TEXT_RECOVERED":
        assert selected["8772"]["main_body_count"] == "1" and selected["8772"]["nested_main_wrappers"] == "1"
    prohibited_fields = []

    def check(obj, file):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if re.fullmatch(r"set-cookie|cookie|authorization|proxy-authorization", key, re.I):
                    prohibited_fields.append(str(file.relative_to(BASE)))
                if key == "headers" and isinstance(value, dict):
                    assert set(k.lower() for k in value) <= HEADERS, file
                check(value, file)
        elif isinstance(obj, list):
            for value in obj:
                check(value, file)

    for file in (BASE / "raw").rglob("*.json"):
        check(json.loads(file.read_text()), file)
    for file in (BASE / "raw").rglob("*.headers"):
        for line in file.read_text().splitlines():
            if ":" in line and not line.startswith("HTTP/"):
                assert line.split(":", 1)[0].lower() in HEADERS, file
    assert not prohibited_fields, "forbidden header fields found; values intentionally omitted"
    result = {"status": "PASS", "scope": "offline bytes, key uniqueness, provenance and known main/reply examples; no event/downtime acceptance",
              "manifest_raw_files_checked": len(manifest["datasets"]), "recovered_main_rows": len(recovered),
              "unknown_or_unresolved_rows": len(unknown), "original_ids_recovered_main": sum(r["in_original_csv"] == "True" for r in recovered),
              "original_records": coverage["original_records"], "full_original_main_text_recovery": coverage["full_original_main_text_recovery"],
              "headers_whitelist": "PASS", "known_examples_4687_6503": "PASS", "mixed_4685_preserved": "PASS"}
    (BASE / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
