#!/usr/bin/env python3
"""Acquire public EMISS mirrors; preserve source bytes and retrieval receipts.

No credentials, browser, installations, or private API. Python standard library.
"""
import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parents[1]
IDS = (62073, 62074, 62301, 62302, 42102, 42103)
VERSION = "tourism-v1-20261109"
HEADER_WHITELIST = {"content-type", "content-length", "last-modified", "etag", "date", "cache-control"}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def acquire(url, rel, method="GET", data=None):
    started = now()
    request = urllib.request.Request(url, method=method, data=data,
                                     headers={"User-Agent": "case5-public-research/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read()
        # Public source bodies are preserved; cookie/session/auth headers are never retained.
        info = {k:v for k,v in response.headers.items() if k.lower() in HEADER_WHITELIST}
        status = response.status
        final_url = response.url
    path = BASE / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if method != "HEAD":
        path.write_bytes(body)
    return {"url": url, "final_url": final_url, "retrieved_at_utc": started,
            "http_status": status, "response_headers": info,
            "path": rel if method != "HEAD" else None,
            "sha256": hashlib.sha256(body).hexdigest() if method != "HEAD" else None,
            "size_bytes": len(body) if method != "HEAD" else None,
            "request_method": method,
            "request_body_utf8": data.decode() if data else None,
            "tls_verified": True}


def fetch():
    receipts = []
    for indicator in IDS:
        url = "https://repository.nsedc.ru/api/3/action/package_show?" + urllib.parse.urlencode(
            {"id": f"emiss_{indicator}"})
        receipts.append(acquire(url, f"raw/nsedc_package_{indicator}.json"))
        package = json.loads((BASE / receipts[-1]["path"]).read_bytes())["result"]
        resource = next(x for x in package["resources"] if x["format"] == "csv.gz")
        head = acquire(resource["url"], f"raw/{indicator}.head", method="HEAD")
        receipts.append(head)
        content_length = int(head["response_headers"].get("Content-Length", "0"))
        if content_length > 10_000_000:
            raise ValueError(f"Review acquisition size before downloading: {content_length}")
        receipts.append(acquire(resource["url"], f"raw/emiss_{indicator}.csv.gz"))
        print(indicator, receipts[-1]["size_bytes"], receipts[-1]["sha256"])
        (BASE / "raw/acquisition_receipts.json").write_text(
            json.dumps({"collector_version": VERSION, "receipts": receipts},
                       ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_primary():
    """Public read-only POST matches the dataGrid request in publisher's FGrid.js.

    No fetched JavaScript is executed; only numeric dimension IDs are parsed.
    """
    receipts = []
    for indicator in IDS[:4]:
        url = f"https://www.fedstat.ru/indicator/{indicator}"
        receipts.append(acquire(url, f"raw/fedstat_{indicator}.html"))
        html = (BASE / receipts[-1]["path"]).read_text()
        filter_text = html.split("filters: {", 1)[1].split("left_columns:", 1)[0]
        pieces = re.split(r"\n {28}(\d+): \{", filter_text)
        selections = []
        dimensions = []
        for i in range(1, len(pieces), 2):
            owner, block = pieces[i], pieces[i+1]
            dimensions.append(owner)
            selections.extend(("selectedFilterIds", f"{owner}_{v}")
                              for v in re.findall(r"\n {36}(\d+): \{", block))
        left = re.search(r"left_columns: \[([^\]]*)\]", html).group(1)
        top = re.search(r"top_columns: \[([^\]]*)\]", html).group(1)
        left_ids = re.findall(r"\d+", left)
        top_ids = re.findall(r"\d+", top)
        line_ids = [d for d in dimensions if d not in top_ids]
        params = [("lineObjectIds", d) for d in line_ids]
        params += [("columnObjectIds", d) for d in top_ids] + selections
        data = urllib.parse.urlencode(params).encode()
        receipts.append(acquire(f"https://www.fedstat.ru/indicator/dataGrid.do?id={indicator}",
                                f"raw/fedstat_{indicator}_data.json", method="POST", data=data))
        obj = json.loads((BASE / receipts[-1]["path"]).read_bytes())
        print(indicator, receipts[-1]["size_bytes"], "results", len(obj.get("results", [])))
        (BASE / "raw/primary_acquisition_receipts.json").write_text(
            json.dumps({"collector_version": VERSION, "receipts": receipts},
                       ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--fetch-primary", action="store_true")
    args = parser.parse_args()
    if args.fetch:
        fetch()
    if args.fetch_primary:
        fetch_primary()
