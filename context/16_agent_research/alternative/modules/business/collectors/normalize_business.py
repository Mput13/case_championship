#!/usr/bin/env python3
"""Normalize frozen public source bytes; Python standard library, no network.

Run from repository root:
python3 context/16_agent_research/alternative/modules/business/collectors/normalize_business.py
"""
import csv
import hashlib
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
VERSION = "business-v1"


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def write_csv(path, rows, fields=None):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def filemeta(name):
    p = BASE / "raw" / name
    meta_path = p.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    assert not meta.get("sha256") or meta["sha256"] == sha, "Frozen raw bytes changed"
    return {"sha256": sha, "size_bytes": p.stat().st_size,
            "retrieved_at_utc": meta.get("retrieved_at_utc") or datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()}


def sibur():
    s = (BASE / "raw/sibur_geography.html").read_text()
    m = json.loads((BASE / "raw/sibur_geography.meta.json").read_text())
    buttons = list(re.finditer(r'<button\b[^>]*data-dots="([^\"]*)"[^>]*>(.*?)</button>', s, re.S))
    assert buttons, "No marker arrays: source layout changed"
    all_markers = json.loads(html.unescape(buttons[0].group(1)))
    counts = Counter(x["id"] for x in all_markers)
    byid = {x["id"]: x for x in all_markers if x["id"] and counts[x["id"]] == 1}
    categories = {}
    for b in buttons[1:]:
        label = clean(b.group(2))
        for x in json.loads(html.unescape(b.group(1))):
            if x["id"]:
                categories.setdefault(x["id"], []).append(label)
    blocks = list(re.finditer(
        r'<div class="modal\s+redesign" id="([^\"]*)".*?'
        r'<h2 class="[^"]*modal-map__title">(.*?)</h2>.*?'
        r'<p class="[^"]*modal-map__description">(.*?)</p>', s, re.S))
    assert len(blocks) == s.count('modal-map__title') == len(all_markers), "Lost a modal or marker"
    curated = list(csv.DictReader((BASE / "collectors/sibur_area_map.csv").open()))
    assert len(curated) == len(blocks), "Review and extend explicit area map after source changes"
    sites = []
    for n, (b, area) in enumerate(zip(blocks, curated), 1):
        source_id, title, address = b.group(1), clean(b.group(2)), clean(b.group(3))
        assert area["source_modal_id"] == source_id and int(area["ordinal"]) == n
        assert area["site_name"] == title, (n, title, area["site_name"])
        point = byid.get(source_id)
        # Generic corporate telephone/email are not needed in normalized address.
        address = re.split(r"(?:,?\s*тел\s*:|,?\s*email\s*:)", address, flags=re.I)[0].strip()
        sites.append({
            "dataset_id": "sibur_geography_20261109", "snapshot_id": m["sha256"][:16],
            "site_id": "sibur:" + (source_id or f"modal-ordinal-{n:03d}"),
            "source_modal_id": source_id, "source_ordinal": n,
            "group_id": "SIBUR", "relationship": "listed_on_group_geography_page",
            "site_name": title, "address_source": address,
            "product_category_source": ";".join(categories.get(source_id, [])),
            "joint_venture_label_source": "СП" in title,
            "stage_source": "investment_project_label" if "инвестиционный проект" in title else "UNKNOWN",
            "country_iso_curated": area["country_iso"], "region_iso_curated": area["region_iso"],
            "locality_label_curated": area["locality_label"],
            "area_join_status": "region_mapped_from_address_locality_needs_canonical_core_id",
            "latitude_source": point["coords"][0] if point else None,
            "longitude_source": point["coords"][1] if point else None,
            "coordinate_join_status": "unique_source_modal_id" if point else "missing_or_duplicate_source_id",
            "value_type": "OBSERVED", "derived_fields": "curated_country_region_locality; source_coordinates_not_geocoded",
            "observed_at_utc": m["retrieved_at_utc"], "effective_from": None,
            "publication_date": None, "source_url": m["source_url"],
            "source_locator": f"modal occurrence {n}; id={source_id or '(empty)'}; h2.modal-map__title + p.modal-map__description",
            "limitations": "Legal/postal address and publisher map point may differ from actual production entrance; no headcount, travel OD, ownership proof or airport catchment inferred"})
    assert len({x["site_id"] for x in sites}) == len(sites)
    write_csv(BASE / "normalized/sibur_sites.csv", sites)
    markers = [{"ordinal": n, "source_modal_id": x["id"], "latitude_source": x["coords"][0],
                "longitude_source": x["coords"][1], "source_color": x["color"],
                "id_occurrences": counts[x["id"]], "value_type": "OBSERVED"} for n, x in enumerate(all_markers, 1)]
    write_csv(BASE / "normalized/sibur_map_markers.csv", markers)
    # This is group -> site membership. Do not manufacture a complete site -> site OD graph.
    edges = [{"group_id": x["group_id"], "site_id": x["site_id"], "relationship": x["relationship"],
              "snapshot_id": x["snapshot_id"], "value_type": "OBSERVED", "source_locator": x["source_locator"]} for x in sites]
    write_csv(BASE / "normalized/group_site_membership.csv", edges)
    return sites


def gazprom():
    s = (BASE / "raw/gazprom_hr_2024.html").read_text()
    m = json.loads((BASE / "raw/gazprom_hr_2024.meta.json").read_text())
    t = [t for t in re.findall(r'<table\b.*?</table>', s, re.S) if "Численность вахтового персонала" in t]
    assert len(t) == 1
    cells = [[clean(c) for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', r, re.S)]
             for r in re.findall(r'<tr\b.*?</tr>', t[0], re.S)]
    assert len(cells) == 5 and all(len(x) == 5 for x in cells)
    definitions = [
        ("employer_group_employees_at_shift_using_companies", "thousand persons"),
        ("shift_personnel", "thousand persons"),
        ("shift_personnel_far_north_and_equivalent", "thousand persons"),
        ("shift_share_at_shift_using_companies", "percent")]
    rows = []
    for n, (c, (metric, unit)) in enumerate(zip(cells[1:], definitions), 1):
        for i, year in enumerate([2022, 2023, 2024], 1):
            rows.append({"dataset_id": "gazprom_shift_2024_report", "snapshot_id": m["sha256"][:16],
                         "organisation_id": "GAZPROM_GROUP", "indicator_id": metric, "period": year,
                         "value": float(c[i].replace(",", ".")), "unit": unit,
                         "value_type": "OBSERVED", "geography": "Group operations; no municipality breakdown",
                         "source_period_header": cells[0][i],
                         "source_metric_label": c[0],
                         "definition_caveat": "Table headers say 31 December; adjacent note says average headcount. Preserve ambiguity; no worker trips/frequency conversion.",
                         "publication_date": None, "observed_at_utc": m["retrieved_at_utc"],
                         "source_url": m["source_url"], "source_locator": f"third HTML table, data row {n}, year column {i}"})
    write_csv(BASE / "normalized/gazprom_shift_observations.csv", rows)
    return rows


def historical_vankor():
    s = (BASE / "raw/rosneft_vankor_2017_search.txt").read_text()
    # Extract only first indexed primary-source result, not other search hits.
    first = s.split("--------------------------------------------------------------------------------", 1)[0]
    required = ["Красноярск, Томск, Уфа, Ижевск, Москва", "12 тыс. работников", "27 Февраль 2017"]
    assert all(x in first for x in required), "Indexed evidence no longer contains required historical facts"
    source = "https://rosneft.ru/press/news/item/185797/"
    meta = filemeta("rosneft_vankor_2017_search.txt")
    origins = [("Красноярск", "RU-KYA", "KJA"), ("Томск", "RU-TOM", "TOF"),
               ("Уфа", "RU-BA", "UFA"), ("Ижевск", "RU-UD", "IJK"), ("Москва", "RU-MOW", "MOW")]
    rows = []
    for city, region, code in origins:
        rows.append({"evidence_id": "RN_VANKOR_20170227:" + code + "-IAA",
                     "origin_city_source": city, "origin_region_iso_curated": region,
                     "destination_city_source": "Игарка", "destination_region_iso_curated": "RU-KYA",
                     "city_airport_hint_origin": code, "city_airport_hint_destination": "IAA",
                     "airport_hint_status": "curated_hint_not_source_airport_code_not_for_automatic_join",
                     "service_type_source": "charter_shift_transport",
                     "traveller_purpose": "RN-Vankor and contractor shift workers to Vankor cluster",
                     "annual_passengers": None, "weekly_flights": None, "current_service_status": "UNKNOWN",
                     "publication_date": "2017-02-27", "reference_period": "publication-current 2017; exact observation dates UNKNOWN",
                     "value_type": "OBSERVED", "source_status": "PARSED", "acquisition_method": "search-indexed primary-source statement; full source HTML ACCESS_FAILED",
                     "source_url": source, "source_locator": "first search result; Spravka paragraph starting Vахты в Игарку",
                     "raw_sha256": meta["sha256"], "observed_at_utc": meta["retrieved_at_utc"],
                     "limitations": "Historical carrier statement, no route-specific passenger count; no 2026 currency, airport choice or free-market availability established"})
    write_csv(BASE / "normalized/historical_vankor_routes.csv", rows)
    aggregate = [{"evidence_id": "RN_VANKOR_20170227:IAA-workers-month", "location_source": "airport of Igarka",
                  "indicator": "workers_of_RN_Vankor_and_contractors_through_airport_per_month",
                  "value": 12000, "unit": "reported workers per month", "value_type": "OBSERVED",
                  "publication_date": "2017-02-27", "exact_measurement_period": None,
                  "source_url": source, "source_locator": "first search result; Spravka paragraph after airport-of-Igarka sentence",
                  "definition_caveat": "Source does not establish unique workers vs passenger handlings, arrivals vs departures, route split or seasonality. Do not multiply into annual OD.",
                  "acquisition_method": "search-indexed primary-source statement; full HTML not acquired"}]
    write_csv(BASE / "normalized/historical_vankor_aggregate.csv", aggregate)
    return rows


def manifests(sites, gaz, vankor):
    specs = [
        ("sibur_geography_20261109", "https://sibur.ru/ru/about/geo/", "sibur_geography.html", "SIBUR", "organisation site × snapshot", "Russia and foreign sites explicitly listed by one group", "2026-11-09 snapshot; undated source effective state", len(sites), "PARSED", "Corporate site list; no headcount/travel OD; two empty marker IDs kept unmatched"),
        ("gazprom_shift_2024_report", "https://sustainability.gazpromreport.ru/2024/gazprom-groups-people/hr-management/", "gazprom_hr_2024.html", "Gazprom", "group indicator × reporting year", "Group operations; no regional allocation", "2022–2024", len(gaz), "PARSED", "No origins/destinations; average-vs-year-end definition ambiguous in source"),
        ("rosneft_vankor_historical_2017_search", "https://rosneft.ru/press/news/item/185797/", "rosneft_vankor_2017_search.txt", "Rosneft via web search index", "historical route statement and airport monthly worker aggregate", "5 origin cities and Igarka", "publication 2017-02-27; current 2026 status UNKNOWN", len(vankor)+1, "PARSED", "Search response bytes only; full primary HTML ACCESS_FAILED; historical statement must not calibrate current OD"),
        ("case5_requirements_page", "https://mai-way.ru/tasks/red-wings/", "case5_page.html", "MAI Way", "case web page", "case requirements", "2026-11-09 snapshot", 1, "ACQUIRED_RAW", "Context source only; no demand observation")]
    registry, manifest = [], []
    measures = {
        "sibur_geography_20261109": ("listed site; latitude/longitude degrees; publisher product category", "group_id;site_id;snapshot_id", "curl -L --fail --max-time 35 -D raw/sibur_geography.headers -o raw/sibur_geography.html https://sibur.ru/ru/about/geo/", "public HTML, TLS curl succeeded"),
        "gazprom_shift_2024_report": ("thousand persons; percent", "organisation_id;indicator_id;period;snapshot_id", "curl -sS -L --fail --max-time 40 -D raw/gazprom_hr_2024.headers -o raw/gazprom_hr_2024.html https://sustainability.gazpromreport.ru/2024/gazprom-groups-people/hr-management/", "public HTML"),
        "rosneft_vankor_historical_2017_search": ("historical directed route statement; reported workers/month with undefined handling basis", "evidence_id;publication_date;source_url", 'native web search: site.rosneft.ru/press/news/item/185797/ "Вахты в Игарку"; response_length=long', "indexed primary statement available; full HTML ACCESS_FAILED"),
        "case5_requirements_page": ("case web page", "source_url;snapshot_id", "python3 urllib.request.urlopen('https://mai-way.ru/tasks/red-wings/', timeout=30).read(2000000)", "public HTML")}
    for did, url, fn, owner, grain, geo, period, count, status, lim in specs:
        meta = filemeta(fn)
        published = "2017-02-27" if "vankor" in did else None
        units, keys, acquisition_command, availability = measures[did]
        record = {"dataset_id": did, "source_url": url, "organisation": owner,
                  "raw_path": "raw/"+fn, **meta, "publication_date": published,
                  "grain": grain, "geographic_coverage": geo, "temporal_coverage": period,
                  "record_count": count, "acquisition_status": status, "value_type": "OBSERVED",
                  "units": units, "key_fields": keys, "availability": availability,
                  "acquisition_command": acquisition_command,
                  "license": "UNKNOWN", "use_limitations": "Public website availability is not an open-data redistribution licence; source attribution retained",
                  "limitations": lim, "collector_version": VERSION,
                  "reproduce_command": "python3 context/16_agent_research/alternative/modules/business/collectors/normalize_business.py",
                  "update_command": "python3 context/16_agent_research/alternative/modules/business/collectors/fetch_business.py --download",
                  "join_keys": keys}
        registry.append(record)
        manifest.append(record)
    (BASE/"dataset_manifest.json").write_text(json.dumps({"schema_version": "1.0", "path_base": "directory containing this manifest", "collector_version": VERSION,
        "datasets": manifest}, ensure_ascii=False, indent=2)+"\n")
    artifacts = [{"path": str(p.relative_to(BASE)), "size_bytes": p.stat().st_size,
                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                  "role": "frozen source bytes or acquisition support; see source_registry for source-level grain"}
                 for p in sorted((BASE/"raw").glob("*")) if p.is_file()]
    (BASE/"raw_artifact_inventory.json").write_text(json.dumps(artifacts, ensure_ascii=False, indent=2)+"\n")
    write_csv(BASE / "source_registry.csv", registry)
    coverage = [
        {"dataset_id": "sibur_geography_20261109", "universe": "all geography modals in frozen publisher page", "denominator": len(sites), "covered": len(sites), "unit": "listed sites", "status": "PARSED", "missingness": "One company, not all Russian businesses; unlisted city UNKNOWN, not zero"},
        {"dataset_id": "sibur_geography_20261109", "universe": "same listed sites with unique nonempty marker ID", "denominator": len(sites), "covered": sum(x["latitude_source"] is not None for x in sites), "unit": "sites with joinable publisher coordinates", "status": "PARSED", "missingness": "Two foreign site modals have empty duplicated IDs; coordinates not assigned by position"},
        {"dataset_id": "sibur_geography_20261109", "universe": "same listed sites whose explicit address is in Russia", "denominator": len(sites), "covered": sum(x["country_iso_curated"] == "RU" for x in sites), "unit": "Russian site entries", "status": "PARSED", "missingness": "Geographic coverage denominator is source list, not all cities in Russia"},
        {"dataset_id": "gazprom_shift_2024_report", "universe": "4 selected indicators × 3 published years", "denominator": 12, "covered": len(gaz), "unit": "indicator-year observations", "status": "PARSED", "missingness": "Municipality OD and paid air journeys absent for every observation"},
        {"dataset_id": "rosneft_vankor_historical_2017_search", "universe": "origin city list explicitly stated in indexed 2017 press release", "denominator": 5, "covered": len(vankor), "unit": "historical origin–destination statements", "status": "PARSED", "missingness": "Search-only acquisition; current status and volume absent"}]
    write_csv(BASE / "coverage.csv", coverage)
    checks = {"collector_version": VERSION, "sibur_site_rows": len(sites), "sibur_unique_site_ids": len({x['site_id'] for x in sites}),
              "sibur_russian_entries": sum(x["country_iso_curated"] == "RU" for x in sites),
              "sibur_russian_locality_labels": len({(x['region_iso_curated'],x['locality_label_curated']) for x in sites if x['country_iso_curated']=='RU'}),
              "gazprom_observations": len(gaz), "historical_route_statements": len(vankor),
              "notes": "Parser assertions and source byte hashes verify extraction only; no live OD or commercial acceptance", "status": "PASSED_EXTRACTION_CHECKS"}
    (BASE / "validation.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    manifests(sibur(), gazprom(), historical_vankor())
