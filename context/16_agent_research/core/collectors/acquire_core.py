#!/usr/bin/env python3
"""Acquire public snapshots using standard HTTPS, retaining exact bytes and metadata.

Derived tables are built by normalize_core.py. No credentials or browser automation.
Re-running does not overwrite snapshots: use --refresh to create a dated subfolder.
"""
import argparse
import concurrent.futures
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = "core-acquire-v1"
SAFE_HEADERS = {"content-type", "content-length", "last-modified", "etag", "date", "cache-control"}
SOURCES = [
    dict(dataset_id="ourairports_airports", name="OurAirports airports", organization="OurAirports community", url="https://davidmegginson.github.io/ourairports-data/airports.csv", suffix="csv", grain="airport", geographic_coverage="World; RU subset normalized separately", temporal_coverage="Mutable community snapshot at retrieval", key_fields="id;ident", units="latitude/longitude degrees; elevation feet", license="Public Domain per https://ourairports.com/data/", decision_use="Airport identity, coordinates and geography; not operational clearance or current schedule", limitations="Community maintained; ISO borders follow publisher; scheduled_service is not proof of operating flight"),
    dict(dataset_id="ourairports_runways", name="OurAirports runways", organization="OurAirports community", url="https://davidmegginson.github.io/ourairports-data/runways.csv", suffix="csv", grain="runway", geographic_coverage="World; RU subset normalized separately", temporal_coverage="Mutable community snapshot at retrieval", key_fields="id;airport_ref", units="length/width feet; heading degrees", license="Public Domain per https://ourairports.com/data/", decision_use="Preliminary runway screening, with closed/surface flags; confirm dispatch suitability separately", limitations="Published physical length is not aircraft operational approval or available declared distance"),
    dict(dataset_id="travelpayouts_airports", name="Travelpayouts airport directory", organization="Travelpayouts", url="https://api.travelpayouts.com/data/ru/airports.json", suffix="json", grain="airport or station code", geographic_coverage="World; RU matched by city directory", temporal_coverage="Mutable directory at retrieval", key_fields="code;city_code", units="latitude/longitude degrees; IANA time_zone", license="UNKNOWN; https://support.travelpayouts.com/", decision_use="Independent code and timezone crosswalk; verify code collisions and city vs airport distinction", limitations="Commercial travel directory contains non-airport stations; time_zone may be missing or outdated"),
    dict(dataset_id="travelpayouts_cities", name="Travelpayouts city directory", organization="Travelpayouts", url="https://api.travelpayouts.com/data/ru/cities.json", suffix="json", grain="travel city code", geographic_coverage="World; RU filtered separately", temporal_coverage="Mutable directory at retrieval", key_fields="code;country_code", units="latitude/longitude degrees; IANA time_zone", license="UNKNOWN; https://support.travelpayouts.com/", decision_use="Canonical travel-market names/codes and city timezone crosswalk", limitations="Travel market is not administrative municipality, metropolitan population or catchment"),
    dict(dataset_id="tochno_intercity_zip", name="Intercity connectivity 162 v20260629 CSV archive", organization="Если быть точным", url="https://storage.yandexcloud.net/tochno-st-catalog/Geo/data_intercity_connectivity_162_v20260629/data_intercity_connectivity_162_v20260629_csv.zip", suffix="zip", grain="directed city pair x transport mode", geographic_coverage="Publisher selected Russian cities; verify count after parsing", temporal_coverage="Publisher version 2026-06-29; population census 2021; transport reference dates in documentation", key_fields="city_from;region_from;city_to;region_to;transport_type", units="persons; km; hours (some estimated by publisher)", license="CC BY 4.0 per publisher; attribution required", decision_use="Wide land-alternative and connectivity proxy; explicitly not observed passenger OD", limitations="Selected large cities only; transport availability and durations require method and period review; no sales or direction-level frequency"),
    dict(dataset_id="tochno_intercity_method", name="Intercity connectivity methodology", organization="Если быть точным", url="https://storage.yandexcloud.net/tochno-st-catalog/Geo/data_intercity_connectivity_162_v20260629/description_intercity_connectivity_162_v20260629.pdf", suffix="pdf", grain="documentation", geographic_coverage="Dataset coverage", temporal_coverage="Version 2026-06-29", key_fields="N/A", units="N/A", license="CC BY 4.0 per publisher", decision_use="Classify provider estimates and interpret NULL, dates, selection and source lineage", limitations="Documentation does not independently verify underlying transport database"),
    dict(dataset_id="case5_live_brief", name="Case 5 Red Wings task", organization="МАИ × Т1 × RWB", url="https://mai-way.ru/tasks/red-wings/", suffix="html", grain="task page", geographic_coverage="Case requirements", temporal_coverage="Live version at retrieval", key_fields="N/A", units="N/A", license="UNKNOWN", decision_use="Exact case requirements, definitions and fleet constraints", limitations="Industry background is not audited airline disclosure"),
    dict(dataset_id="ourairports_terms", name="OurAirports data download and terms", organization="OurAirports", url="https://ourairports.com/data/", suffix="html", grain="documentation", geographic_coverage="World", temporal_coverage="Live page at retrieval", key_fields="N/A", units="N/A", license="Public Domain per publisher", decision_use="License and field provenance", limitations="No warranty of accuracy"),
]

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha(b):
    return hashlib.sha256(b).hexdigest()

def acquire(s, destination):
    entry = dict(s)
    entry["source_url"] = s["url"]
    entry["collector_version"] = VERSION
    entry["command"] = "python3 context/16_agent_research/core/collectors/acquire_core.py"
    entry["publication_date"] = "UNKNOWN"
    entry["retrieved_at_utc"] = now()
    try:
        req = urllib.request.Request(s["url"], headers={"User-Agent":"RedWingsCase5-public-research/1.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read(40_000_001)
            entry["http_status"] = r.status
            entry["final_url"] = r.geturl()
            entry["response_headers"] = {k:v for k,v in r.headers.items() if k.lower() in SAFE_HEADERS}
        if len(body) > 40_000_000:
            raise ValueError("40 MB per-file research limit exceeded; no partial artifact published")
        dest = destination / (s["dataset_id"]+"."+s["suffix"])
        if len(body)>5_000_000:
            # Retain exact bytes through lossless gzip. Hash of original remains separate.
            packed = gzip.compress(body, mtime=0)
            dest = dest.with_suffix(dest.suffix+".gz")
            dest.write_bytes(packed)
            entry["compression"]="gzip"
            entry["compressed_sha256"]=sha(packed)
            entry["compressed_size_bytes"]=len(packed)
        else:
            dest.write_bytes(body)
            entry["compression"]="none"
        entry["sha256"]=sha(body)
        entry["size_bytes"]=len(body)
        entry["raw_path"]=str(dest.relative_to(ROOT))
        if s["suffix"]=="csv":
            rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
            entry["record_count"]=len(rows)
            entry["columns"]=list(rows[0]) if rows else []
        elif s["suffix"]=="json":
            obj=json.loads(body)
            entry["record_count"]=len(obj) if isinstance(obj,list) else None
        else:
            entry["record_count"]=None
        entry["acquisition_status"]="ACQUIRED_RAW"
    except Exception as e:
        entry["acquisition_status"]="ACCESS_FAILED"
        entry["error"]=type(e).__name__+": "+str(e)
        entry["record_count"]=None
        entry["raw_path"]=None
        entry["sha256"]=None
    return entry

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--refresh",action="store_true");args=ap.parse_args()
    dest=ROOT/"raw"/"public"
    metadata=ROOT/"acquisition_manifest.json"
    if metadata.exists() and not args.refresh:
        print("Existing acquisition_manifest.json retained; --refresh required for another snapshot")
        return
    if args.refresh:
        dest=dest/dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        metadata=dest/"acquisition_manifest.json"
    dest.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        entries=list(pool.map(lambda s:acquire(s,dest),SOURCES))
    metadata.write_text(json.dumps({"created_at_utc":now(),"collector_version":VERSION,"datasets":entries},ensure_ascii=False,indent=2)+"\n")
    for e in entries:print(e["dataset_id"],e["acquisition_status"],e.get("size_bytes"),e.get("record_count"),e.get("error",""),flush=True)

if __name__=="__main__": main()
