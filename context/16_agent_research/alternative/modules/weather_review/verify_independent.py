#!/usr/bin/env python3
"""Offline check of frozen raw, independently of the parent collectors.

Run from any directory. Writes checks.json only in this review directory.
Uses fixed-width ISD-Lite fields, not the collector's whitespace reader.
"""
import calendar
import collections
import csv
import datetime as dt
import gzip
import hashlib
import html
import io
import json
import math
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nullable(value):
    return "" if value is None else str(value)


def expected_month(rows, year, month):
    t = [v[4] / 10 for v in rows if v[4] != -9999]
    w = [v[8] / 10 for v in rows if v[8] != -9999]
    return {
        "observed_hours": len(rows),
        "calendar_hours": calendar.monthrange(year, month)[1] * 24,
        "observed_days": len({v[2] for v in rows}),
        "calendar_days": calendar.monthrange(year, month)[1],
        "temperature_observations": len(t),
        "wind_observations": len(w),
        "temperature_mean_c": round(sum(t) / len(t), 3) if t else None,
        "temperature_min_c": min(t) if t else None,
        "temperature_below_minus20_count": sum(x < -20 for x in t) if t else None,
        "wind_ge12_ms_count": sum(x >= 12 for x in w) if w else None,
        "wind_max_ms": max(w) if w else None,
    }


def distance_km(a, b):
    # Great-circle distance from cosine law, independent of parent haversine.
    lat1, lon1 = map(math.radians, map(float, a))
    lat2, lon2 = map(math.radians, map(float, b))
    q = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    return 6371 * math.acos(max(-1, min(1, q)))


def run():
    checks, sources, samples = {}, [], []
    source_paths = [
        "collectors/weather.py", "collectors/join_demo.py", "collectors/package_manifest.py",
        "raw/noaa_isd_history.csv", "raw/noaa_lite_format.txt",
        "raw/noaa_service_notice.html", "raw/weather/acquisition_receipts.json",
        "raw/ordinary_airports.source.json", "raw/ordinary_airports.csv.gz",
        "normalized/weather_station_selection.csv", "normalized/weather_monthly_2024.csv",
        "normalized/weather_coverage_2024.csv", "normalized/weather_validation.json",
        "normalized/join_airport_station_mapping.csv", "normalized/join_airport_weather_month.csv",
        "normalized/join_validation.json",
    ]
    for name in source_paths:
        path = ROOT / name
        sources.append({"path": name, "sha256": digest(path), "size_bytes": path.stat().st_size})

    history = read_csv(ROOT / "raw/noaa_isd_history.csv")
    selected = [v for v in history if v["CTRY"] == "RS" and v["ICAO"] != ""
                and v["BEGIN"] <= "20240101" <= "20241231" <= v["END"]]
    assert selected == read_csv(ROOT / "normalized/weather_station_selection.csv")
    assert len(selected) == len({v["ICAO"] for v in selected}) == 84
    assert len({(v["USAF"], v["WBAN"]) for v in selected}) == 84
    checks["station_selection"] = {"status": "PASS", "selected": len(selected), "unique_icao": True,
        "universe": "station-history CTRY=RS with ICAO and BEGIN<=20240101, END>=20241231; not all Russian airports"}
    receipts = json.loads((ROOT / "raw/weather/acquisition_receipts.json").read_text())
    assert len(receipts) == len({r["icao"] for r in receipts}) == 84
    assert {r["icao"] for r in receipts} == {r["ICAO"] for r in selected}
    failed = [r for r in receipts if r["acquisition_status"] != "ACQUIRED_RAW"]
    assert len(failed) == 1 and failed[0]["icao"] == "USDD" and "404" in failed[0]["error"]
    monthly = read_csv(ROOT / "normalized/weather_monthly_2024.csv")
    assert len(monthly) == len({(r["station_id"], r["month"]) for r in monthly}) == 996
    index = {(r["station_id"], r["month"]): r for r in monthly}
    coverage = {r["icao"]: r for r in read_csv(ROOT / "normalized/weather_coverage_2024.csv")}
    total, missing_t, missing_w, nonempty_months, duplicate_hours = 0, 0, 0, 0, 0
    missing_months = []
    year_values = set()
    for receipt in receipts:
        if receipt["acquisition_status"] != "ACQUIRED_RAW":
            continue
        path = ROOT / receipt["raw_path"]
        assert digest(path) == receipt["sha256"]
        plain = gzip.decompress(path.read_bytes())
        assert hashlib.sha256(plain).hexdigest() == receipt["uncompressed_sha256"]
        sources.append({"path": receipt["raw_path"], "sha256": digest(path), "uncompressed_sha256": receipt["uncompressed_sha256"], "size_bytes": path.stat().st_size})
        rows = []
        for line_no, line in enumerate(plain.decode("ascii").splitlines(), 1):
            assert len(line) == 61
            vals = [int(line[a:b]) for a, b in [(0,4),(5,7),(8,10),(11,13),(13,19),(19,25),
                    (25,31),(31,37),(37,43),(43,49),(49,55),(55,61)]]
            assert vals == [int(v) for v in line.split()]
            assert vals[0] == 2024
            dt.datetime(*vals[:4])
            year_values.add(vals[0])
            rows.append(vals)
            missing_t += vals[4] == -9999
            missing_w += vals[8] == -9999
            if receipt["icao"] in ["UEEE", "ULMM", "URMM"] and line_no == 1:
                samples.append({"path": receipt["raw_path"], "line_1_based": line_no, "raw": line,
                    "temperature_c": None if vals[4] == -9999 else vals[4]/10,
                    "wind_ms": None if vals[8] == -9999 else vals[8]/10})
        unique_hours = {tuple(v[:4]) for v in rows}
        duplicate_hours += len(rows) - len(unique_hours)
        assert len(rows) == len(unique_hours) == receipt["record_count"]
        by_month = {m: [v for v in rows if v[1] == m] for m in range(1,13)}
        station_id = path.name[:-8]
        for month, obs in by_month.items():
            result = index[(station_id, f"2024-{month:02d}")]
            expected = expected_month(obs, 2024, month)
            for key, val in expected.items():
                assert result[key] == nullable(val), (station_id,month,key,result[key],val)
            if obs:
                nonempty_months += 1
            else:
                missing_months.append({"station_id": station_id, "icao": receipt["icao"], "month": f"2024-{month:02d}"})
                assert result["observed_hours"] == "0" and result["temperature_mean_c"] == ""
                assert result["wind_ge12_ms_count"] == "" and result["temperature_below_minus20_count"] == ""
        cover = coverage[receipt["icao"]]
        assert int(cover["archive_rows"]) == len(rows)
        assert int(cover["months_with_records"]) == sum(bool(v) for v in by_month.values())
        assert int(cover["observed_days"]) == len({tuple(v[:3]) for v in rows})
        total += len(rows)
    assert total == 519366 and duplicate_hours == 0
    assert nonempty_months == 992 and len(missing_months) == 4
    checks["raw_and_monthly_recompute"] = {"status": "PASS", "files_sha_and_gzip_verified": 83,
        "records": total, "distinct_station_hours": total, "duplicate_station_hours": duplicate_hours,
        "years": sorted(year_values), "fixed_width_matches_whitespace_parser": True,
        "all_monthly_metrics_recomputed_rows": 996, "months_with_records": nonempty_months,
        "empty_months_kept_with_null_weather_metrics": missing_months,
        "missing_temperature_records": missing_t, "missing_wind_records": missing_w,
        "stations_with_at_least_350_observed_days": sum(int(v["observed_days"]) >= 350 for v in coverage.values()),
        "months_with_records_distribution": dict(collections.Counter(int(v["months_with_records"]) for v in coverage.values()))}
    checks["acquisition"] = {"status":"PASS_OFFLINE_RECEIPT", "selected":84,"acquired":83,
        "failed":[{"icao":v["icao"],"status":v["acquisition_status"],"error":v["error"]} for v in failed],
        "current_source_availability":"NOT_RUN: no network in independent review"}
    source = json.loads((ROOT / "raw/ordinary_airports.source.json").read_text())
    archive = (ROOT / source["raw_path"]).read_bytes()
    assert hashlib.sha256(archive).hexdigest() == source["compressed_sha256"]
    plain = gzip.decompress(archive)
    assert hashlib.sha256(plain).hexdigest() == source["sha256"]
    airports = list(csv.DictReader(io.StringIO(plain.decode("utf-8"))))
    assert len(airports) == len({v["id"] for v in airports}) == source["record_count"] == 86350
    ru = [v for v in airports if v["iso_country"] == "RU"]
    codes = collections.defaultdict(list)
    for v in ru:
        if v["icao_code"]:
            codes[v["icao_code"]].append(v)
    assert len(ru) == 1845
    duplicates = {k:[v["id"] for v in a] for k,a in codes.items() if len(a)>1}
    assert not duplicates
    mapping = read_csv(ROOT / "normalized/join_airport_station_mapping.csv")
    assert len(mapping) == len({v["station_id"] for v in mapping}) == len(coverage) == 83
    mapping_idx = {v["station_id"]:v for v in mapping}
    joined = read_csv(ROOT / "normalized/join_airport_weather_month.csv")
    assert len(joined) == len({(v["station_id"],v["weather_month"]) for v in joined}) == len(monthly)
    for row in monthly:
        result = mapping_idx[row["station_id"]]
        match = codes.get(row["icao"],[])
        if match:
            assert len(match) == 1
            a = match[0]
            assert result["airport_id"] == a["id"]
            km = distance_km((row["latitude"],row["longitude"]),(a["latitude_deg"],a["longitude_deg"]))
            assert abs(float(result["station_airport_distance_km"]) - km) <= 0.00051
            expected_status = "EXACT_ICAO_COORD_WITHIN25KM" if km<=25 else "EXACT_ICAO_COORD_GT25KM_REVIEW"
            assert result["mapping_status"] == expected_status
            for k, v in {"airport_ident":"ident","iata":"iata_code","municipality":"municipality","iso_region":"iso_region","airport_type":"type","airport_name":"name"}.items():
                assert result[k] == a[v]
        else:
            assert result["mapping_status"] == "NO_ICAO_MATCH"
            assert all(result[k] == "" for k in ["airport_id","airport_ident","iata","municipality","iso_region","airport_type","airport_name","station_airport_distance_km"])
    for row in joined:
        original = index[(row["station_id"],row["weather_month"])]
        assert row["icao"] == original["icao"]
        for key in ["temperature_mean_c","temperature_observations","wind_observations","observed_days","calendar_days","temperature_below_minus20_count","wind_ge12_ms_count"]:
            assert row[key] == original[key]
        for key,val in mapping_idx[row["station_id"]].items():
            assert row[key] == val
    checks["join"] = {"status":"PASS", "right_world_airports":len(airports), "right_ru_airports":len(ru),
        "duplicate_nonempty_ru_icao":duplicates, "left_rows":len(monthly),"joined_rows":len(joined),
        "join_multiplication":0,"all_weather_metrics_preserved":True,
        "station_mapping_statuses":dict(collections.Counter(v["mapping_status"] for v in mapping)),
        "largest_matched_distance_km":max(float(v["station_airport_distance_km"]) for v in mapping if v["station_airport_distance_km"]),
        "unmatched_icao":[v["icao"] for v in mapping if v["mapping_status"]=="NO_ICAO_MATCH"]}
    text = (ROOT / "raw/noaa_service_notice.html").read_text()
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", text, flags=re.S|re.I)
    text = " ".join(html.unescape(re.sub(r"<[^>]+>"," ",text)).split())
    excerpt = "This product has been superseded, with no update beyond 08/24/2025."
    assert excerpt in text and "GHCNh" in text
    checks["service_notice"] = {"status":"PASS_FROZEN_TEXT", "path":"raw/noaa_service_notice.html",
        "supporting_excerpt":excerpt,"interpretation":"2024 is historical common year. ISD does not provide current post-2025-08-24 updates; live GHCNh acquisition NOT_RUN."}
    weather_code = (ROOT / "collectors/weather.py").read_text()
    manifest_code = (ROOT / "collectors/package_manifest.py").read_text()
    date_issue = '"published_at": last_modified' in weather_code or '"publication_date": rec.get("published_at")' in manifest_code
    checks["date_semantics"] = {"status":"OPEN_MINOR_FINDING" if date_issue else "FIXED_SOURCE_REVIEW",
        "finding":"HTTP Last-Modified is not a publisher-supplied publication date.",
        "evidence_at_initial_review":["collectors/weather.py:55,62","collectors/package_manifest.py:70"],
        "smallest_fix":"Preserve HTTP date as http_last_modified; set publication_date UNKNOWN. No raw gzip changes necessary."}
    result = {"review_version":"weather-independent-v1","checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "root":str(ROOT),"scope":"offline frozen-byte and transformation verification; no parent collector executed or modified",
        "overall":"PASS_WITH_LIMITATIONS", "checks":checks,"sample_raw_locators":samples,
        "input_manifest":sources,
        "not_run":["new HTTP acquisition","QC flag recovery from full ISD/GHCNh","multi-year climatology","cancellation/dispatch modelling","operational approval and airport current service verification"]}
    (OUT / "checks.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"overall":result["overall"],"station_selection":checks["station_selection"]["selected"],
        "raw_records":total,"monthly_rows":len(monthly),"months_with_records":nonempty_months,
        "join":checks["join"]["station_mapping_statuses"]},ensure_ascii=False))


if __name__ == "__main__":
    run()
