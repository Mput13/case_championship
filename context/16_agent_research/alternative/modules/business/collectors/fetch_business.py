#!/usr/bin/env python3
"""Refresh public HTML using curl with certificate validation enabled.

No package install, browser, credentials or paid API. Current frozen raw files
are never overwritten. Download estimate < 1 MiB. Search evidence requires the
documented native web search query, since this program has no search API key.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SOURCES = {
    "sibur_geography": "https://sibur.ru/ru/about/geo/",
    "gazprom_hr_2024": "https://sustainability.gazpromreport.ru/2024/gazprom-groups-people/hr-management/",
    "case5_page": "https://mai-way.ru/tasks/red-wings/"}
HEADER_WHITELIST = {"content-type", "content-length", "last-modified", "etag", "date", "cache-control"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="otherwise only print source list")
    ap.add_argument("--output-dir", help="relative to module; must not already exist")
    args = ap.parse_args()
    if not args.download:
        print(json.dumps(SOURCES, ensure_ascii=False, indent=2))
        return
    now = datetime.now(timezone.utc)
    dest = BASE / (args.output_dir or "raw/refresh_" + now.strftime("%Y%m%dT%H%M%SZ"))
    dest = dest.resolve()
    assert dest.is_relative_to(BASE), "Write only inside assigned module"
    dest.mkdir(parents=True, exist_ok=False)
    log = []
    for source, url in SOURCES.items():
        raw = dest / (source + ".html")
        cmd = ["curl", "-sS", "-L", "--fail", "--max-time", "40", "--max-filesize", "2000000",
               "-D", "-", "-o", str(raw), url]
        r = subprocess.run(cmd, capture_output=True, text=True)
        # curl headers remain in memory until filtered. Never persist cookies,
        # authorization or session response fields, including redirect hops.
        safe_headers = [line for line in r.stdout.splitlines() if line.startswith("HTTP/")
                        or (":" in line and line.split(":", 1)[0].lower() in HEADER_WHITELIST)]
        (dest / (source + ".headers")).write_text("\n".join(safe_headers) + "\n")
        row = {"source_url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
               "command": cmd, "returncode": r.returncode, "stderr": r.stderr,
               "tls_verification": "enabled", "status": "ACQUIRED_RAW" if r.returncode == 0 else "ACCESS_FAILED"}
        if raw.exists():
            row.update(raw_path=str(raw.relative_to(BASE)), size_bytes=raw.stat().st_size,
                       sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
        log.append(row)
    (dest / "acquisition_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"output_dir": str(dest), "source_statuses": [x["status"] for x in log]}))


if __name__ == "__main__":
    main()
