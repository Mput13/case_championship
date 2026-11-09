#!/usr/bin/env python3
"""Normalize publisher dataGrid JSON and reconcile with the archived NSED mirror.

Read-only public acquisition is implemented in collect_tourism.py. Geography codes
are linked through exact, unique publisher area labels and the mirror's source
OKATO labels; no airport-city-name join or inferred geographic allocation occurs.
"""
import collections
import csv
import gzip
import hashlib
import html
import io
import json
import re
import sys
sys.dont_write_bytecode = True

from normalize_tourism import BASE, MONTH_IDS, METRICS, clean_value, write_csv

PERIOD_IDS = {"1540283":1,"1540294":2,"1540290":3,"1540285":4,"1540289":5,"1540288":6,
              "1540287":7,"1540284":8,"1540293":9,"1540292":10,"1540291":11,"1540286":12}


def main():
    areas=list(csv.DictReader((BASE/"normalized/areas.csv").open()))
    canonical={a["area_id"]:a for a in areas if a["in_disjoint_reference_panel"]=="True"}
    receipts=json.loads((BASE/"raw/primary_acquisition_receipts.json").read_text())["receipts"]
    receipts={x["path"]:x for x in receipts}
    mirror=list(csv.DictReader(io.StringIO(gzip.decompress(
        (BASE/"normalized/observations_long.csv.gz").read_bytes()).decode())))
    observations=[];reconciliation=[];passport_rows=[];manifest=[]
    all_primary={};all_mirror={}
    for indicator in MONTH_IDS:
        dataset=f"emiss_{indicator}"
        mirror_rows=[x for x in mirror if x["dataset_id"]==dataset]
        crosswalk={}
        for row in mirror_rows:
            if row["area_name"] in crosswalk:
                assert crosswalk[row["area_name"]]==row["area_id"]
            crosswalk[row["area_name"]]=row["area_id"]
        for row in mirror_rows:
            key=(indicator,row["area_id"],int(row["year"]),int(row["period_end_month"]))
            value,_=clean_value(row["value"])
            if value is not None: all_mirror[key]=value
        rel=f"raw/fedstat_{indicator}_data.json"
        body=(BASE/rel).read_bytes();source=json.loads(body)
        receipt=receipts[rel]
        sha=hashlib.sha256(body).hexdigest();assert sha==receipt["sha256"]
        source_html=(BASE/f"raw/fedstat_{indicator}.html").read_text()
        for field in ["methodologyFull","commentIndicatorFull"]:
            block=re.search(r'id="'+field+r'"[^>]*>(.*?)</div>',source_html,re.S)
            value=html.unescape(re.sub('<[^>]+>','',block.group(1))).strip() if block else ""
            passport_rows.append({"dataset_id":dataset,"field":field,"value":value,
                "raw_path":f"raw/fedstat_{indicator}.html","source_locator":f"element_id={field}"})
        last_update=re.search(r'Последнее обновление данных</div>\s*<p>(.*?)</p>',source_html,re.S)
        passport_rows.append({"dataset_id":dataset,"field":"publisher_last_update_label",
            "value":last_update.group(1).strip() if last_update else "UNKNOWN",
            "raw_path":f"raw/fedstat_{indicator}.html","source_locator":"passport:Последнее обновление данных"})
        for row_index,row in enumerate(source["results"]):
            area_name=row["dim57831"]
            assert area_name in crosswalk, f"Unmatched primary geography: {area_name}"
            area_id=crosswalk[area_name]
            for key,raw_value in row.items():
                match=re.fullmatch(r"dim(\d{4})_(\d+)_d\d+_i\d+",key)
                if not match:continue
                year,period_id=match.groups();month=PERIOD_IDS[period_id]
                value,missing=clean_value(raw_value)
                primary_key=(indicator,area_id,int(year),month)
                assert primary_key not in all_primary, f"Duplicate primary key: {primary_key}"
                if value is not None: all_primary[primary_key]=value
                observations.append({"dataset_id":dataset,"snapshot_id":f"fedstat_{indicator}:{sha[:16]}",
                    "area_id":area_id,"area_name":area_name,"year":int(year),"period_end_month":month,
                    "period_aggregation":"year_to_date","value":value,"unit":row["dim30611"],
                    "indicator_id":METRICS[indicator],"value_type":"OBSERVED" if value is not None else "UNKNOWN",
                    "missing_reason":missing,"raw_path":rel,"raw_json_locator":f"results[{row_index}].{key}",
                    "source_url":f"https://www.fedstat.ru/indicator/{indicator}",
                    "retrieved_at_utc":receipt["retrieved_at_utc"],"acquisition_status":"PARSED"})
        manifest.append({"dataset_id":f"fedstat_live_{indicator}","source_url":receipt["url"],
            "landing_url":f"https://www.fedstat.ru/indicator/{indicator}","raw_path":rel,"sha256":sha,
            "size_bytes":len(body),"retrieved_at_utc":receipt["retrieved_at_utc"],"publication_date":None,
            "publisher_last_update_label":last_update.group(1).strip() if last_update else None,
            "request_method":"POST (public read-only dataGrid)","request_body_receipt":"raw/primary_acquisition_receipts.json",
            "grain":"geographic row with YTD year×period cells","record_count":len(source["results"]),
            "geographic_coverage":f"{len(source['results'])} source geographies including overlaps",
            "temporal_coverage":"See primary_coverage.csv for last filled month by area/year",
            "acquisition_status":"PARSED","organisation":"Росстат / ЕМИСС","license":"UNKNOWN for primary API; NSED mirror declares CC BY",
            "collector_version":"tourism-v1-20261109","limitations":"YTD; no origin/mode; operational scope differs for sanatoria; 2026 accommodation methodology break; metadata ambiguity retained in passport_extract.csv"})
        years=sorted({key[2] for key in all_primary if key[0]==indicator} | {key[2] for key in all_mirror if key[0]==indicator})
        for year in years:
            pk={k:v for k,v in all_primary.items() if k[0]==indicator and k[2]==year}
            mk={k:v for k,v in all_mirror.items() if k[0]==indicator and k[2]==year}
            common=set(pk)&set(mk)
            reconciliation.append({"dataset_id":dataset,"year":year,"common_filled_cells":len(common),
                "equal_common_values":sum(pk[k]==mk[k] for k in common),
                "changed_common_values":sum(pk[k]!=mk[k] for k in common),
                "primary_only_filled_cells":len(set(pk)-set(mk)),"mirror_only_filled_cells":len(set(mk)-set(pk)),
                "interpretation":"same upstream lineage; agreement is reconciliation, not independent confirmation"})
    write_csv("normalized/primary_observations.csv.gz",observations)
    write_csv("normalized/passport_extract.csv",passport_rows)
    write_csv("normalized/primary_mirror_reconciliation.csv",reconciliation)
    monthly=[];coverage=[];profiles=[]
    for indicator in MONTH_IDS:
        years=sorted({x[2] for x in all_primary if x[0]==indicator})
        for area_id,area in sorted(canonical.items()):
            for year in years:
                vals=[];filled_months=[]
                for month in range(1,13):
                    curr=all_primary.get((indicator,area_id,year,month))
                    prev=0 if month==1 else all_primary.get((indicator,area_id,year,month-1))
                    if curr is not None:filled_months.append(month)
                    value=curr-prev if curr is not None and prev is not None else None
                    reason="" if value is not None else "primary_current_or_previous_ytd_missing"
                    if value is not None and value<0:value=None;reason="negative_ytd_increment"
                    vals.append(value)
                    monthly.append({"dataset_id":f"emiss_{indicator}","area_id":area_id,"area_name":area["area_name"],
                        "year":year,"month":month,"period":f"{year}-{month:02d}","ytd_value":curr,"monthly_increment":value,
                        "unit":"person" if indicator in {62073,62074} else "overnight_stay",
                        "value_type":"DERIVED" if value is not None else "UNKNOWN","missing_reason":reason,
                        "recipe":"YTD(m)-YTD(m-1); Jan=YTD(Jan)","raw_path":f"raw/fedstat_{indicator}_data.json"})
                complete=all(v is not None for v in vals);total=sum(vals) if complete else None
                profiles.append({"dataset_id":f"emiss_{indicator}","area_id":area_id,"area_name":area["area_name"],
                    "year":year,"complete_12_months":complete,"annual_ytd_total":total,
                    "summer_jun_aug_share":sum(vals[5:8])/total if complete and total else None,
                    "winter_dec_jan_feb_share":sum(vals[:2]+vals[11:])/total if complete and total else None,
                    "peak_to_mean_ratio":max(vals)/(total/12) if complete and total else None,
                    "peak_month":1+vals.index(max(vals)) if complete and total else None,
                    "value_type":"DERIVED" if complete else "UNKNOWN",
                    "missing_reason":"" if complete else "incomplete_12_month_profile_no_imputation",
                    "recipe_version":"tourism-profile-v1"})
                coverage.append({"dataset_id":f"emiss_{indicator}","area_id":area_id,"area_name":area["area_name"],
                    "year":year,"expected_months":12,"filled_ytd_months":len(filled_months),
                    "usable_increment_months":sum(v is not None for v in vals),
                    "last_filled_month":max(filled_months) if filled_months else None,
                    "reference_panel_size":len(canonical),"scope":"disjoint 85-area panel derived from published geography; not airport catchment"})
    write_csv("normalized/primary_monthly_increments.csv",monthly)
    write_csv("normalized/primary_seasonality_profiles.csv",profiles)
    write_csv("primary_coverage.csv",coverage)
    (BASE/"primary_dataset_manifest.json").write_text(json.dumps({"path_base":"context/16_agent_research/alternative/modules/tourism","datasets":manifest},ensure_ascii=False,indent=2),encoding="utf-8")
    summary={"source_observations":len(observations),"reference_areas":len(canonical),"monthly_rows_including_missing":len(monthly),
        "changed_common_mirror_values":sum(x["changed_common_values"] for x in reconciliation),
        "primary_only_filled_cells":sum(x["primary_only_filled_cells"] for x in reconciliation),
        "unmatched_primary_area_names":0,"duplicate_primary_keys":0,
        "negative_ytd_increments":sum(x["missing_reason"]=="negative_ytd_increment" for x in monthly)}
    (BASE/"normalized/primary_validation.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":main()
