#!/usr/bin/env python3
"""Offline delivery checks. No network or mutation of source values."""
import collections
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]


def read_csv(rel):
    with (BASE/rel).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))


def main():
    manifest=json.loads((BASE/"dataset_manifest.json").read_text())
    checked=0
    for ds in manifest["datasets"]:
        body=(BASE/ds["raw_path"]).read_bytes()
        assert hashlib.sha256(body).hexdigest()==ds["sha256"],ds["raw_path"]
        assert len(body)==ds["size_bytes"]
        if ds.get("uncompressed_sha256"):
            assert hashlib.sha256(gzip.decompress(body)).hexdigest()==ds["uncompressed_sha256"]
        checked+=1
    for kind in ["normalized_files","collector_files","raw_auxiliary_files"]:
        for ds in manifest[kind]:
            assert hashlib.sha256((BASE/ds["path"]).read_bytes()).hexdigest()==ds["sha256"],ds["path"]
    for filename in ["acquisition_receipts.json","primary_acquisition_receipts.json"]:
        receipts=json.loads((BASE/"raw"/filename).read_text())["receipts"]
        for item in receipts:
            assert set(k.lower() for k in item.get("response_headers",{})) <= {
                "content-type","content-length","last-modified","etag","date","cache-control"}
            if item.get("path"):
                assert hashlib.sha256((BASE/item["path"]).read_bytes()).hexdigest()==item["sha256"]
    primary=list(csv.DictReader(io.StringIO(gzip.decompress((BASE/"normalized/primary_observations.csv.gz").read_bytes()).decode())))
    key=lambda r:(r["dataset_id"],r["area_id"],r["year"],r["period_end_month"])
    assert len({key(r) for r in primary})==len(primary)
    # Independently re-read saved publisher JSON at every recorded source locator.
    caches={}
    for r in primary:
        if r["raw_path"] not in caches:caches[r["raw_path"]]=json.loads((BASE/r["raw_path"]).read_bytes())
        head,field=r["raw_json_locator"].split("].",1)
        row_index=int(head.split("[")[1])
        raw_value=caches[r["raw_path"]]["results"][row_index][field]
        assert float(raw_value)==float(r["value"])
    monthly=read_csv("normalized/primary_monthly_increments.csv")
    grouped=collections.defaultdict(list)
    for r in monthly:grouped[(r["dataset_id"],r["area_id"],r["year"])].append(r)
    profiles=read_csv("normalized/primary_seasonality_profiles.csv")
    count_complete=0
    for p in profiles:
        rows=grouped[(p["dataset_id"],p["area_id"],p["year"])]
        if p["complete_12_months"]=="True":
            assert len(rows)==12
            assert all(r["monthly_increment"]!="" for r in rows)
            assert sum(float(r["monthly_increment"]) for r in rows)==float(p["annual_ytd_total"])
            assert float(rows[-1]["ytd_value"])==float(p["annual_ytd_total"])
            count_complete+=1
        else:
            assert p["annual_ytd_total"]=="" and p["summer_jun_aug_share"]==""
    report={"status":"PASS","raw_datasets_checked":checked,"primary_source_values_traced":len(primary),
            "unique_primary_keys":len(primary),"complete_profiles_sum_to_ytd_december":count_complete,
            "headers_whitelist":"PASS","scope":"offline hashes, source locators, keys and arithmetic; not OD validation"}
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":main()
