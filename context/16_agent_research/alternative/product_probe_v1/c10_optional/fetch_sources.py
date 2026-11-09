#!/usr/bin/env python3
"""Fetch five public sources without executing website code or sending credentials."""
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = {
    "ufa_departures": "https://www.airportufa.ru/schedule/surgut/?CITY_CODE=surgut&direction=TO&type=V",
    "ufa_schedule": "https://www.airportufa.ru/schedule/surgut/?CITY_CODE=surgut&direction=FROM&type=V",
    "surgut_schedule": "https://www.airport-surgut.ru/surgut/schedule/",
    "burintekh_contacts": "https://burintekh.ru/contacts/",
    "burintekh_sng_2006": "https://burintekh.ru/upload/iblock/4e4/h9e9ixyivzp567f5c6ao75s3dy7lj85g.pdf",
}
HEADERS = {"date", "content-type", "content-length", "etag", "last-modified", "cache-control", "content-encoding"}


def sanitize_html(body):
    text = body.decode("utf-8", errors="replace")
    text = re.sub(r'("(?:bitrix_sessid|sessid|csrf(?:_token)?|access_token|refresh_token)"\s*:\s*")[^"]*(")', r'\1[REDACTED]\2', text, flags=re.I)
    text = re.sub(r'(<input\b[^>]*\btype\s*=\s*[\"\x27]hidden[\"\x27][^>]*\bvalue\s*=\s*[\"\x27])[^\"\x27]*([\"\x27])', r'\1[REDACTED]\2', text, flags=re.I)
    return text.encode("utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=sorted(SOURCES), action="append", required=True)
    parser.add_argument("--output", type=Path, required=True, help="New snapshot directory; existing receipts are never overwritten")
    args = parser.parse_args()
    (args.output / "raw_hold").mkdir(parents=True, exist_ok=True)
    (args.output / "receipts").mkdir(parents=True, exist_ok=True)
    for source_id in args.source:
        receipt_path = args.output / "receipts" / f"{source_id}.json"
        if receipt_path.exists():
            raise SystemExit(f"Refusing to overwrite {receipt_path}")
        receipt = {
            "source_id": source_id, "url": SOURCES[source_id], "method": "GET",
            "request_started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "headers_policy": "seven-field-whitelist-no-cookie-auth",
            "raw_publication_status": "LOCAL_HOLD_IGNORED",
        }
        try:
            request = Request(SOURCES[source_id], headers={"User-Agent": "Case5 public-source research/1.0"})
            with urlopen(request, timeout=40) as response:
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise ValueError("Source exceeds the 4 MB bound")
                receipt.update({"http_status": response.status, "final_url": response.url,
                                "response_headers": {k.lower(): v for k, v in response.headers.items() if k.lower() in HEADERS}})
            stored = sanitize_html(body) if "text/html" in receipt["response_headers"].get("content-type", "") else body
            receipt.update({"retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "sha256": hashlib.sha256(body).hexdigest(), "size_bytes": len(body),
                            "raw_path": f"raw_hold/{source_id}.bin", "stored_sha256": hashlib.sha256(stored).hexdigest(),
                            "stored_size_bytes": len(stored),
                            "raw_storage_transform": "Redact known credential/session JSON fields and every hidden-input value for HTML; unchanged PDF held locally"})
            (args.output / receipt["raw_path"]).write_bytes(stored)
        except Exception as error:
            receipt.update({"status": "ACCESS_FAILED", "error_type": type(error).__name__, "error": str(error)})
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: receipt.get(k) for k in ("source_id", "http_status", "status", "sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
