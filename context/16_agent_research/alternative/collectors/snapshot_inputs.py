#!/usr/bin/env python3
"""Recreate pinned colleague files, or refresh support pages into a new directory.

Default --git-only exactly replays Git bytes. --fetch-support never overwrites the
frozen evidence; it writes a dated refresh directory. No untrusted code executes.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WHITELIST = {"content-type", "content-length", "last-modified", "etag", "date", "cache-control"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-only", action="store_true")
    parser.add_argument("--fetch-support", action="store_true")
    args = parser.parse_args()
    records = json.loads((ROOT / "colleague_manifest.json").read_text())
    for item in records:
        data = subprocess.check_output(["git", "show", item["git_source"]])
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("pinned object byte mismatch: " + item["git_source"])
        path = ROOT / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        elif path.read_bytes() != data:
            raise ValueError("preserve existing evidence; file differs: " + str(path))
    if args.fetch_support:
        output = ROOT / "raw" / ("support_refresh_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        output.mkdir(exist_ok=False)
        urls = {"case5_page.html": "https://mai-way.ru/tasks/red-wings/",
                "noaa_isd_history.csv": "https://noaa-isd-pds.s3.amazonaws.com/isd-history.csv",
                "noaa_lite_format.txt": "https://noaa-isd-pds.s3.amazonaws.com/isd-lite/isd-lite-format.txt",
                "noaa_service_notice.html": "https://www.nesdis.noaa.gov/news/service-location-change-integrated-surface-data-global-hourly"}
        receipts = []
        for name, url in urls.items():
            rec = {"source_url": url, "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
            try:
                with urllib.request.urlopen(url, timeout=40) as response:
                    data = response.read(5_000_001)
                    if len(data) > 5_000_000:
                        raise ValueError("5MB support file limit")
                    rec["response_headers"] = {k: v for k, v in response.headers.items() if k.lower() in WHITELIST}
                    rec["http_status"] = response.status
                (output / name).write_bytes(data)
                rec.update(path=str((output / name).relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {e}"
            receipts.append(rec)
        (output / "access.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2))
    print(json.dumps({"pinned_git_inputs_checked": len(records), "support_refreshed": args.fetch_support}))


if __name__ == "__main__":
    main()
