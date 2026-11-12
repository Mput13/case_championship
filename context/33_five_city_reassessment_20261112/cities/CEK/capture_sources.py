#!/usr/bin/env python3
"""Recheck selected public sources; retain hashes and factual probes, not full texts."""
import concurrent.futures
import datetime
import hashlib
import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKS = [
    ("CEK-S06", "https://t.me/s/novaport_holding/425", ["2,16", "279", "2045"]),
    ("CEK-S07", "https://cekport.ru/", ["noindex, noarchive", "setup_utm"]),
    ("CEK-S10", "https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/", ["27 октября 2026", "опорных аэропортов"]),
    ("CEK-S11", "https://flyredwings.com/directions/chelyabinsk/", ["CEKKUF", "CEKSVX", "CEKTOF"]),
    ("CEK-S12", "https://flyredwings.com/flight-board/", ["5050", "Челябинск", "Кемерово", "Барнаул"]),
    ("CEK-S13", "https://t.me/s/flyredwings/60", ["2022-04-19", "Челябинске", "Омске"]),
    ("CEK-S15", "https://uvtaero.ru/raspisanie", ["Челябинск", "25.10.26-27.12.26", "05.11.26-31.12.26"]),
    ("CEK-S16", "https://azimuth.ru/ru/schedule", ["Челябинск", "6024"]),
    ("CEK-S19", "https://cdn.flysmartavia.com/news/20261029/", ["Челябинск", "Калининград", "27 марта 2027"]),
    ("CEK-S40", "https://ar-kuf.ru/schedule/", ["Челябинск"]),
    ("CEK-S44", "https://centrum-air.ru/ru/news", ["Челябинск", "4 декабря 2026", "C6957", "C6958"]),
]


def fetch(item):
    sid, url, probes = item
    out = {"source_id": sid, "url": url, "accessed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(url, timeout=22) as response:
            raw = response.read()
            out.update(http_status=response.status, final_url=response.url,
                       bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        content = raw.decode("utf-8", "replace")
        out["factual_token_probes"] = {p: p in content for p in probes}
        out["interpretation"] = "Token presence verifies receipt only; it does not establish commercial service, demand or future performance."
        if sid == "CEK-S15":
            # Compact schedule facts only, preserving row context as a limitation in dossier.
            rows = re.findall(r"<tr\b[^>]*>.*?</tr>", content, re.S | re.I)
            out["CEK_schedule_rows"] = [re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", row)).strip()
                                        for row in rows if "Челябинск" in row]
        if sid == "CEK-S07":
            out["interpretation"] = "HTTP200 JS/interstitial body; not an airport schedule or rate card."
    except Exception as exc:
        out.update(error_type=type(exc).__name__, exact_error=str(exc))
    return out


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(fetch, CHECKS))
    (HERE / "http_receipts.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps([{k:r[k] for k in ("source_id", "http_status", "bytes", "exact_error") if k in r}
                      for r in receipts], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
