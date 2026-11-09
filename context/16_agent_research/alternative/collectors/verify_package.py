#!/usr/bin/env python3
"""Offline release checks: bytes, compression, keys, coverage and safe headers.

Run only after child collectors have settled and package_manifest.py is rebuilt.
No network, no source rewriting, no semantic acceptance of demand proxies.
"""
import csv
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"content-type", "content-length", "last-modified", "etag", "date", "cache-control"}
DENIED = {"set-cookie", "cookie", "authorization", "proxy-authorization"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return list(csv.DictReader((ROOT / name).open(encoding="utf-8", newline="")))


def main():
    manifest=json.loads((ROOT/"dataset_manifest.json").read_text())
    required={"dataset_id","source_url","raw_path","sha256","retrieved_at_utc","grain",
              "geographic_coverage","temporal_coverage","record_count","acquisition_status","limitations"}
    checked, compressed, failures=0,0,0
    for ds in manifest["datasets"]:
        assert required <= set(ds), (ds.get("dataset_id"), sorted(required-set(ds)))
        if not ds.get("raw_path"):
            assert ds["acquisition_status"]=="ACCESS_FAILED", ds["dataset_id"]
            failures+=1
            continue
        p=ROOT/ds["raw_path"]
        assert p.is_file() and p.resolve().is_relative_to(ROOT.resolve()),ds["raw_path"]
        assert sha(p)==ds["sha256"],ds["raw_path"]
        if ds.get("size_bytes") is not None:
            assert p.stat().st_size==ds["size_bytes"],ds["raw_path"]
        if ds.get("uncompressed_sha256"):
            body=p.read_bytes()
            plain=gzip.decompress(body) if body.startswith(b"\x1f\x8b") else body
            assert hashlib.sha256(plain).hexdigest()==ds["uncompressed_sha256"],ds["raw_path"]
            compressed+=body.startswith(b"\x1f\x8b")
        checked+=1
    for ref in manifest["module_manifests"]:
        assert sha(ROOT/ref["path"])==ref["sha256"],ref["path"]
    for f in manifest["normalized_files"]:
        assert sha(ROOT/f["path"])==f["sha256"],f["path"]
    def json_headers(obj, path):
        if isinstance(obj,dict):
            for k,v in obj.items():
                assert not(k.lower() in DENIED and v),f"prohibited header name in {path}"
                if k.lower() in {"headers","response_headers","http_headers"} and isinstance(v,dict):
                    assert {s.lower() for s in v}<=ALLOWED,f"header whitelist in {path}"
                json_headers(v,path)
        elif isinstance(obj,list):
            for v in obj:json_headers(v,path)
    json_files=header_files=0
    for p in ROOT.rglob("*"):
        if p.suffix==".json":
            try:obj=json.loads(p.read_text())
            except (ValueError,UnicodeError):continue
            json_headers(obj,str(p.relative_to(ROOT)))
            json_files+=1
        if p.suffix==".headers":
            names={line.partition(":")[0].strip().lower() for line in p.read_text().splitlines() if ":" in line}
            assert names<=ALLOWED,f"header file whitelist in {p.relative_to(ROOT)}"
            header_files+=1
    weather=read("normalized/weather_monthly_2024.csv")
    joined=read("normalized/join_airport_weather_month.csv")
    assert len(weather)==len({(r["station_id"],r["month"]) for r in weather})==len(joined)==996
    assert len({(r["station_id"],r["weather_month"]) for r in joined})==996
    assert sum(int(r["observed_hours"])>0 for r in weather)==992
    assert sum(int(r["observed_hours"]) for r in weather)==519366
    assert all(r["temperature_mean_c"]==r["wind_max_ms"]=="" for r in weather if r["observed_hours"]=="0")
    # Last-Modified is retained as object metadata, never a known publication date.
    receipts=json.loads((ROOT/"raw/weather/acquisition_receipts.json").read_text())
    assert all(r.get("publication_date")=="UNKNOWN" and "published_at" not in r for r in receipts)
    assert all(d.get("publication_date")=="UNKNOWN" for d in manifest["datasets"] if d["dataset_id"].startswith("noaa_lite_"))
    old=ROOT/"raw/colleague/data/raw/favt_posts.csv"
    assert sha(old)=="3ef101d50e394b58ce10ac21dfb2b7b0790d25c7fdf461d313017b20bce5512b"
    originals=[d for d in manifest["datasets"] if d.get("raw_path")==str(old.relative_to(ROOT))]
    assert len(originals)==1 and originals[0]["condition"]=="PARSER_CONTAMINATION"
    assert originals[0]["acquisition_status"]=="RESTRICTED_USE"
    # Old derived counts may be retained only as revoked history.
    assert not list((ROOT/"normalized").glob("restriction_*")), "Event recalc is not accepted in this delivery; use corrected texts only"
    report={"checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"PASS_OFFLINE_WITH_LIMITATIONS",
            "raw_source_entries_hashed":checked,"access_failures_retained":failures,
            "gzip_uncompressed_hashes_checked":compressed,"json_files_scanned_for_header_values":json_files,
            "header_files_checked":header_files,"headers_whitelist":"PASS",
            "weather_rows":len(weather),"weather_nonempty_months":992,"join_rows":len(joined),
            "original_telegram_preserved_and_restricted":True,
            "operating_event_recalculation":"NOT_RUN_IN_THIS_SLICE",
            "not_validated":["observed OD","predictive value above baseline","licence interpretation beyond captured statements",
                             "current aircraft or airport dispatch limits","complete Telegram correction"]}
    (ROOT/"verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    # Complete artifact inventory has no self-reference and preserves all raw hashes.
    skip={"file_inventory.json","verification.json"}
    files=[{"path":str(p.relative_to(ROOT)),"sha256":sha(p),"size_bytes":p.stat().st_size}
           for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name not in skip and "__pycache__" not in p.parts]
    (ROOT/"file_inventory.json").write_text(json.dumps({"path_base":"alternative/","excluded_self_referential_files":sorted(skip),
        "files":files},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
