#!/usr/bin/env python3
"""Offline, loss-aware normalization of pinned public EMISS mirror CSV bytes."""
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parents[1]
IDS = (62073, 62074, 62301, 62302, 42102, 42103)
MONTH_IDS = IDS[:4]
MONTHS = {"115": 1, "M01_02": 2, "122": 3, "117": 4, "121": 5,
          "120": 6, "119": 7, "116": 8, "125": 9, "124": 10,
          "123": 11, "118": 12}
METRICS = {62073: "accommodated_persons_all_facilities_operational",
           62074: "accommodated_persons_sanatoria_operational",
           62301: "overnight_stays_all_facilities_operational",
           62302: "overnight_stays_sanatoria_operational",
           42102: "accommodated_persons_sanatoria_annual_or_quarterly",
           42103: "overnight_stays_sanatoria_annual_or_quarterly"}


def write_csv(rel, rows):
    path = BASE / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No data for {rel}")
    if str(path).endswith(".gz"):
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        path.write_bytes(gzip.compress(buffer.getvalue().encode("utf-8"), mtime=0))
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def clean_value(raw):
    if raw == "":
        return None, "blank_source_cell"
    text = raw.replace(" ", "").replace("\u00a0", "").replace(",", ".")
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        num = float(text)
        return int(num) if num.is_integer() else num, ""
    return None, "source_non_numeric_marker:" + raw


def main():
    receipts = json.loads((BASE / "raw/acquisition_receipts.json").read_text())["receipts"]
    by_path = {r["path"]: r for r in receipts if r.get("path")}
    observations = []
    dimensions = {}
    input_stats = {}
    manifest = []
    registry = []
    raw_geo_sets = {}
    for indicator in IDS:
        rel = f"raw/emiss_{indicator}.csv.gz"
        raw_bytes = (BASE / rel).read_bytes()
        plain_bytes = gzip.decompress(raw_bytes)
        source_rows = list(csv.DictReader(io.StringIO(plain_bytes.decode("utf-8-sig"))))
        package = json.loads((BASE / f"raw/nsedc_package_{indicator}.json").read_text())["result"]
        receipt = by_path[rel]
        sha = hashlib.sha256(raw_bytes).hexdigest()
        assert sha == receipt["sha256"]
        snapshot = f"emiss_{indicator}:{sha[:16]}"
        geos = set()
        numeric_years = [x for x in source_rows[0] if re.fullmatch(r"\d{4}", x)]
        n_numeric = 0
        for row_n, row in enumerate(source_rows, 2):
            geo_raw = row[next(iter(row))]
            code, name = geo_raw.strip().split(" ", 1)
            area_id = ("OKATO:" if len(code) == 11 and code.isdigit() else "EMISS_AGG:") + code
            level = "region_or_component" if area_id.startswith("OKATO:") else "aggregate"
            geos.add(area_id)
            dimensions[area_id] = {"area_id": area_id, "area_code_raw": code,
                                   "area_name": name, "geographic_level": level,
                                   "code_system": "OKATO_as_published_by_EMISS",
                                   "overlap_warning": "parent_includes_autonomous_okrugs" if code in
                                   {"11000000000", "71000000000"} else ""}
            period_code, period_name = row["Период"].split(" ", 1)
            for year in numeric_years:
                value, missing = clean_value(row[year])
                n_numeric += value is not None
                observations.append({"dataset_id": f"emiss_{indicator}", "snapshot_id": snapshot,
                    "area_id": area_id, "area_name": name, "indicator_id": METRICS[indicator],
                    "year": int(year), "source_period_code": period_code,
                    "source_period_name": period_name,
                    "period_end_month": MONTHS.get(period_code),
                    "period_aggregation": "calendar_year" if period_code == "1558883" else "year_to_date",
                    "value": value, "unit_raw": row["Единица измерения"],
                    "metric_interpretation": "persons" if indicator in {62073,62074,42102} else "overnight_stays_count",
                    "value_type": "OBSERVED" if value is not None else "UNKNOWN",
                    "missing_reason": missing, "source_url": f"https://www.fedstat.ru/indicator/{indicator}",
                    "raw_path": rel, "source_row": row_n, "source_column": year,
                    "retrieved_at_utc": receipt["retrieved_at_utc"],
                    "known_available_at": receipt["retrieved_at_utc"],
                    "known_available_at_basis": "retrieval_only_not_original_publication",
                    "acquisition_status": "PARSED"})
        raw_geo_sets[indicator] = geos
        input_stats[indicator] = {"source_rows": len(source_rows), "numeric_cells": n_numeric,
            "all_cells": len(source_rows)*len(numeric_years), "year_columns": numeric_years,
            "areas": len(geos)}
        limitations = ("Mirror of EMISS, not an independent source. YTD periods must be differenced; blanks not zero. "
            "Regional aggregates do not identify origin or air mode. Regional hierarchy overlaps. "
            "Metadata years include future/empty cells. Retrieval is not historical publication time. "
            "Sanatoria operational data exclude small businesses; preserve scope from source passport. "
            "Nights source unit is count 642; do not apply 1000 multiplier from erroneous mirror title. "
            "62302 official methodology text describes persons despite nights title; conflict retained.")
        manifest.append({"dataset_id":f"emiss_{indicator}", "source_url":receipt["url"],
            "primary_source_url":f"https://www.fedstat.ru/indicator/{indicator}", "organisation":"Росстат / ЕМИСС; зеркало НЦСЭД",
            "raw_path":rel,"sha256":sha,"size_bytes":len(raw_bytes),
            "uncompressed_sha256":hashlib.sha256(plain_bytes).hexdigest(),"uncompressed_size_bytes":len(plain_bytes),
            "retrieved_at_utc":receipt["retrieved_at_utc"],"publication_date":None,
            "mirror_object_last_modified":receipt["response_headers"].get("Last-Modified"),
            "catalog_metadata_modified":package.get("metadata_modified"),
            "grain":"published_area × unit × YTD_period × year (wide source)",
            "geographic_coverage":f"{len(geos)} source geographic rows including overlapping aggregates; see coverage.csv",
            "temporal_coverage":{"schema_years":numeric_years,"filled_values_checked_in":"coverage.csv"},
            "record_count":len(source_rows),"parsed_value_count":n_numeric,"acquisition_status":"PARSED",
            "license":package.get("license_title","UNKNOWN"),"license_url":package.get("license_url"),
            "license_as_declared_by":"НЦСЭД каталог; не независимая правовая проверка",
            "key_fields":["geography_raw","unit_raw","period_raw","year"],
            "collector_version":"tourism-v1-20261109",
            "command":"python3 context/16_agent_research/alternative/modules/tourism/collectors/collect_tourism.py --fetch",
            "transform_command":"python3 context/16_agent_research/alternative/modules/tourism/collectors/normalize_tourism.py",
            "limitations":limitations})
        registry.append({"source_id":f"emiss_{indicator}","source_url":f"https://www.fedstat.ru/indicator/{indicator}",
            "mirror_catalog_url":f"https://repository.nsedc.ru/dataset/emiss_{indicator}",
            "organisation":"Росстат / ЕМИСС; зеркало НЦСЭД","source_title":package["title"],
            "acquisition_status":"PARSED","retrieved_at_utc":receipt["retrieved_at_utc"],
            "publication_date":"UNKNOWN","period":";".join(numeric_years),"grain":"area × period × year",
            "units":"792 persons" if indicator in {62073,62074,42102} else "642 unit (night count)",
            "license":package.get("license_title","UNKNOWN"),"limitations":limitations})
    keys = [(x["dataset_id"],x["area_id"],x["year"],x["source_period_code"],x["unit_raw"]) for x in observations]
    assert len(keys) == len(set(keys)), "Duplicate raw cell key"
    write_csv("normalized/observations_long.csv.gz", observations)
    old_uncompressed = BASE / "normalized/observations_long.csv"
    if old_uncompressed.exists():
        old_uncompressed.unlink()  # Only this collector's reproducible previous output.
    # Canonical contemporary panel: 85 mutually exclusive published area components.
    # Drop parent totals of Arkhangelsk/Tyumen and retain their autonomous components.
    canonical = {a for a in raw_geo_sets[62073] if a.startswith("OKATO:") and a not in
                 {"OKATO:11000000000", "OKATO:71000000000"}}
    for area in dimensions.values():
        area["in_disjoint_reference_panel"] = area["area_id"] in canonical
        area["reference_panel_basis"] = "62073 geography; exclude 2 overlapping parent totals; preserve children and oblast excluding AOs"
    write_csv("normalized/areas.csv", sorted(dimensions.values(), key=lambda x:x["area_id"]))
    lookup = {(x["dataset_id"],x["area_id"],x["year"],x["period_end_month"]):x
              for x in observations if x["dataset_id"] in {f"emiss_{i}" for i in MONTH_IDS}}
    monthly=[]
    coverage=[]
    for indicator in MONTH_IDS:
        dataset=f"emiss_{indicator}"
        years=[int(y) for y in input_stats[indicator]["year_columns"]]
        for area in sorted(canonical):
            for year in years:
                filled=derived=0
                for month in range(1,13):
                    current=lookup.get((dataset,area,year,month))
                    previous=lookup.get((dataset,area,year,month-1))
                    current_value=current["value"] if current else None
                    previous_value=0 if month==1 else previous["value"] if previous else None
                    filled+=current_value is not None
                    if current_value is None:
                        value=None; reason=current["missing_reason"] if current else "source_geography_period_row_absent"
                    elif previous_value is None:
                        value=None;reason="previous_ytd_value_missing"
                    else:
                        value=current_value-previous_value;reason="negative_ytd_increment" if value<0 else ""
                        if value<0: value=None
                    derived+=value is not None
                    monthly.append({"dataset_id":dataset,"area_id":area,"area_name":dimensions[area]["area_name"],
                        "year":year,"month":month,"period":f"{year}-{month:02d}",
                        "ytd_value":current_value,"monthly_increment":value,
                        "value_type":"DERIVED" if value is not None else "UNKNOWN",
                        "unit_raw":current["unit_raw"] if current else ("792 человек" if indicator in {62073,62074} else "642 единица"),
                        "missing_reason":reason,"derivation":"YTD(month)-YTD(month-1); January=YTD(January)",
                        "source_row_current":current["source_row"] if current else None,
                        "source_row_previous":previous["source_row"] if previous else None,
                        "raw_path":f"raw/emiss_{indicator}.csv.gz"})
                coverage.append({"dataset_id":dataset,"area_id":area,"area_name":dimensions[area]["area_name"],
                    "year":year,"expected_months":12,"filled_ytd_months":filled,"usable_increment_months":derived,
                    "missing_ytd_months":12-filled,"reference_panel_size":len(canonical),
                    "coverage_basis":"disjoint geography reference panel; all 12 calendar months including not-yet-published months"})
    write_csv("normalized/monthly_increments.csv.gz",monthly)
    old_monthly = BASE / "normalized/monthly_increments.csv"
    if old_monthly.exists(): old_monthly.unlink()
    write_csv("coverage.csv",coverage)
    # Full-year seasonality only for complete profiles. No annualization of 2026.
    grouped=collections.defaultdict(list)
    for x in monthly: grouped[(x["dataset_id"],x["area_id"],x["year"])].append(x)
    profiles=[]
    for (dataset,area,year),rows in sorted(grouped.items()):
        vals=[x["monthly_increment"] for x in rows]
        complete=all(v is not None for v in vals)
        total=sum(vals) if complete else None
        summer=sum(vals[5:8]) if complete else None
        winter=sum(vals[:2]+vals[11:]) if complete else None
        profiles.append({"dataset_id":dataset,"area_id":area,"area_name":dimensions[area]["area_name"],
            "year":year,"complete_12_months":complete,"annual_ytd_total":total,
            "summer_jun_aug_share":summer/total if total and complete else None,
            "winter_dec_jan_feb_share":winter/total if total and complete else None,
            "peak_to_mean_ratio":max(vals)/(total/12) if total and complete else None,
            "peak_month":1+vals.index(max(vals)) if complete and total else None,
            "value_type":"DERIVED" if complete else "UNKNOWN",
            "missing_reason":"" if complete else "incomplete_12_month_profile_no_imputation",
            "unit":"share or dimensionless ratio; annual_ytd_total in original source units",
            "recipe_version":"tourism-profile-v1"})
    write_csv("normalized/seasonality_profiles.csv.gz",profiles)
    old_profiles = BASE / "normalized/seasonality_profiles.csv"
    if old_profiles.exists(): old_profiles.unlink()
    write_csv("source_registry.csv",registry)
    output_manifest={"path_base":"context/16_agent_research/alternative/modules/tourism",
        "collector_version":"tourism-v1-20261109","datasets":manifest,
        "source_status_note":"PARSED means schema/key/byte checks passed; does not certify completeness or OD applicability",
        "raw_auxiliary_files":[{"path":str(p.relative_to(BASE)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
            "size_bytes":p.stat().st_size} for p in sorted((BASE/"raw").iterdir()) if p.is_file() and p.suffix!=".gz"]}
    (BASE/"dataset_manifest.json").write_text(json.dumps(output_manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    summary={"input_stats":input_stats,"normalized_observation_cells":len(observations),
        "canonical_disjoint_areas":len(canonical),"monthly_rows_including_unknowns":len(monthly),
        "complete_seasonality_profiles":sum(x["complete_12_months"] for x in profiles),
        "negative_monthly_increments_rejected":sum(x["missing_reason"]=="negative_ytd_increment" for x in monthly),
        "duplicate_observation_keys":len(keys)-len(set(keys))}
    (BASE/"normalized/validation.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":
    main()
