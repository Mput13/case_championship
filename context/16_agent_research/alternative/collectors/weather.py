#!/usr/bin/env python3
"""Collect frozen NOAA ISD-Lite 2024, then normalize with stdlib only.

No 2025 annual comparison: ISD stops 2025-08-24 (NOAA notice).
Usage: python3 context/16_agent_research/alternative/collectors/weather.py [--fetch]
Selection is all station-history CTRY=RS rows with a reported ICAO, BEGIN<=20240101
and END>=20241231. This is a station archive universe, not a city longlist.
"""
import argparse
import calendar
import csv
import datetime as dt
import gzip
import hashlib
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw/weather"
YEAR = 2024
VERSION = "weather-v1"
BASE = "https://noaa-isd-pds.s3.amazonaws.com/isd-lite/data/2024/"


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def selected():
    with (ROOT / "raw/noaa_isd_history.csv").open() as f:
        return [r for r in csv.DictReader(f) if r["CTRY"] == "RS" and r["ICAO"]
                and r["BEGIN"] <= "20240101" and r["END"] >= "20241231"]


def fetch_one(r):
    name = f'{r["USAF"]}-{r["WBAN"]}-{YEAR}.gz'
    path = RAW / name
    url = BASE + name
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "case5-public-research/1"})
        with urllib.request.urlopen(request, timeout=40) as response:
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError("file exceeds 2MB per-station guard")
            last_modified = response.headers.get("Last-Modified")
        if not data.startswith(b"\x1f\x8b"):
            raise ValueError("response is not gzip")
        gzip.decompress(data)  # confirm complete archive before writing
        path.write_bytes(data)
        return {"dataset_id": "noaa_lite_" + name[:-3], "source_url": url,
                "raw_path": str(path.relative_to(ROOT)), "retrieved_at_utc": stamp,
                "http_last_modified": last_modified, "publication_date": "UNKNOWN",
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data), "uncompressed_sha256": hashlib.sha256(gzip.decompress(data)).hexdigest(),
                "acquisition_status": "ACQUIRED_RAW", "icao": r["ICAO"]}
    except Exception as e:
        return {"dataset_id": "noaa_lite_" + name[:-3], "source_url": url,
                "retrieved_at_utc": stamp, "acquisition_status": "ACCESS_FAILED",
                "icao": r["ICAO"], "error": f"{type(e).__name__}: {e}"}


def run(fetch=False):
    RAW.mkdir(parents=True, exist_ok=True)
    stations = selected()
    write_csv(ROOT / "normalized/weather_station_selection.csv", stations)
    if fetch:
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(fetch_one, stations))
        (RAW / "acquisition_receipts.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2))
    receipts = json.loads((RAW / "acquisition_receipts.json").read_text())
    # HTTP object modification time is not a known first publication date.
    for receipt in receipts:
        if "published_at" in receipt:
            receipt["http_last_modified"] = receipt.pop("published_at")
        receipt["publication_date"] = "UNKNOWN"
    by_icao = {r["icao"]: r for r in receipts}
    months, coverage, failures = [], [], []
    for station in stations:
        icao = station["ICAO"]
        receipt = by_icao[icao]
        if receipt["acquisition_status"] != "ACQUIRED_RAW":
            failures.append(receipt)
            continue
        data = gzip.decompress((ROOT / receipt["raw_path"]).read_bytes())
        receipt["record_count"] = len(data.splitlines())
        buckets = defaultdict(list)
        keys = set()
        for line_no, line in enumerate(data.decode("ascii").splitlines(), 1):
            values = [int(v) for v in line.split()]
            if len(values) != 12:
                raise ValueError(f"{icao}:{line_no}: {len(values)} fields instead of 12")
            year, month, day, hour = values[:4]
            dt.datetime(year, month, day, hour)
            key = (year, month, day, hour)
            if key in keys:
                raise ValueError(f"duplicate station-hour: {icao} {key}")
            keys.add(key)
            buckets[month].append((day, hour, values[4], values[8]))
        for month in range(1, 13):
            obs = buckets[month]
            temps = [x[2] / 10 for x in obs if x[2] != -9999]
            winds = [x[3] / 10 for x in obs if x[3] != -9999]
            days_in_month = calendar.monthrange(YEAR, month)[1]
            row = {"station_id": f'{station["USAF"]}-{station["WBAN"]}', "icao": icao,
                   "station_name": station["STATION NAME"], "latitude": station["LAT"],
                   "longitude": station["LON"], "month": f"{YEAR}-{month:02d}",
                   "observed_hours": len(obs), "calendar_hours": days_in_month * 24,
                   "observed_days": len({x[0] for x in obs}), "calendar_days": days_in_month,
                   "temperature_observations": len(temps), "wind_observations": len(winds),
                   "temperature_mean_c": round(sum(temps) / len(temps), 3) if temps else None,
                   "temperature_min_c": min(temps) if temps else None,
                   "temperature_below_minus20_count": sum(x < -20 for x in temps) if temps else None,
                   "wind_ge12_ms_count": sum(x >= 12 for x in winds) if winds else None,
                   "wind_max_ms": max(winds) if winds else None,
                   "value_status": "DERIVED", "raw_value_status": "OBSERVED",
                   "source_id": receipt["dataset_id"], "raw_path": receipt["raw_path"],
                   "recipe_version": VERSION,
                   "limitation": "sampled hourly records; archive omissions and synoptic cadence; thresholds exploratory, not dispatch limits or cancellation probabilities"}
            months.append(row)
        coverage.append({"icao": icao, "station_id": f'{station["USAF"]}-{station["WBAN"]}',
                         "archive_rows": len(keys), "months_with_records": sum(bool(v) for v in buckets.values()),
                         "observed_days": len({k[:3] for k in keys}), "calendar_days": 366,
                         "status": "PARSED", "raw_path": receipt["raw_path"]})
    write_csv(ROOT / "normalized/weather_monthly_2024.csv", months)
    write_csv(ROOT / "normalized/weather_coverage_2024.csv", coverage)
    (RAW / "acquisition_receipts.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2))
    result = {"version": VERSION, "selected_stations": len(stations), "downloaded_stations": len(coverage),
              "failed_stations": len(failures), "monthly_rows": len(months),
              "raw_observations": sum(r["archive_rows"] for r in coverage),
              "selection": "CTRY=RS; reported ICAO; BEGIN<=20240101; END>=20241231; no attractiveness selection",
              "unit": "station-hour archived observation; temperature degC, wind m/s",
              "failure_details": failures}
    (ROOT / "normalized/weather_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "failure_details"}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    run(parser.parse_args().fetch)
