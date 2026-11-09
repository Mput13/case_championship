#!/usr/bin/env python3
"""Join historical station weather to an independently captured airport identity.

Exact ICAO only. Keep all NOAA rows; do not assign by city name or nearest point.
The ordinary source is a pinned OurAirports byte snapshot reused from core.
"""
import csv
import gzip
import hashlib
import io
import json
import math
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def haversine(a, b, c, d):
    a, b, c, d = map(math.radians, map(float, [a, b, c, d]))
    q = math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(min(1, q)))


def write(name, rows):
    with (ROOT / "normalized" / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def run():
    source = json.loads((ROOT / "raw/ordinary_airports.source.json").read_text())
    raw = (ROOT / source["raw_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == source["compressed_sha256"]
    uncompressed = gzip.decompress(raw)
    assert hashlib.sha256(uncompressed).hexdigest() == source["sha256"]
    airports = list(csv.DictReader(io.StringIO(uncompressed.decode("utf-8"))))
    assert len(airports) == source["record_count"]
    assert len({a["id"] for a in airports}) == len(airports)
    ru = [a for a in airports if a["iso_country"] == "RU"]
    index = defaultdict(list)
    for airport in ru:
        if airport["icao_code"]:
            index[airport["icao_code"]].append(airport)
    weather = list(csv.DictReader((ROOT / "normalized/weather_monthly_2024.csv").open()))
    assert len({(r["station_id"], r["month"]) for r in weather}) == len(weather)
    assert len({(r["icao"], r["month"]) for r in weather}) == len(weather)
    joined, mappings = [], {}
    for row in weather:
        matches = index.get(row["icao"], [])
        if len(matches) == 1:
            a = matches[0]
            distance = haversine(row["latitude"], row["longitude"], a["latitude_deg"], a["longitude_deg"])
            status = "EXACT_ICAO_COORD_WITHIN25KM" if distance <= 25 else "EXACT_ICAO_COORD_GT25KM_REVIEW"
        else:
            a, distance = {}, None
            status = "NO_ICAO_MATCH" if not matches else "DUPLICATE_AIRPORT_ICAO_REVIEW"
        mapping = {"station_id": row["station_id"], "icao": row["icao"], "station_name": row["station_name"],
                   "airport_id": a.get("id"), "airport_ident": a.get("ident"),
                   "iata": a.get("iata_code") or None, "municipality": a.get("municipality") or None,
                   "iso_region": a.get("iso_region"), "airport_type": a.get("type"),
                   "airport_name": a.get("name"), "station_airport_distance_km": round(distance, 3) if distance is not None else None,
                   "mapping_status": status, "mapping_value_status": "DERIVED",
                   "airport_snapshot_id": source["compressed_sha256"]}
        mappings[row["icao"]] = mapping
        joined.append({**mapping, "weather_month": row["month"],
                       "temperature_mean_c": row["temperature_mean_c"] or None,
                       "temperature_observations": row["temperature_observations"],
                       "wind_observations": row["wind_observations"],
                       "observed_days": row["observed_days"], "calendar_days": row["calendar_days"],
                       "temperature_below_minus20_count": row["temperature_below_minus20_count"] or None,
                       "wind_ge12_ms_count": row["wind_ge12_ms_count"] or None,
                       "weather_source_id": row["source_id"],
                       "timing_limit": "historical 2024 weather joined to 2026 airport identity snapshot; no current operational clearance or OD inference"})
    assert len(joined) == len(weather)
    write("join_airport_station_mapping.csv", list(mappings.values()))
    write("join_airport_weather_month.csv", joined)
    summary = {"version": "join-demo-v1", "left_monthly_rows": len(weather), "joined_rows": len(joined),
               "left_key_unique": True, "right_airport_ids_unique": True,
               "join_multiplication": 0, "station_count": len(mappings),
               "station_mapping_statuses": dict(Counter(x["mapping_status"] for x in mappings.values())),
               "right_ru_airports": len(ru),
               "right_duplicate_icao_codes": {k: [x["id"] for x in v] for k, v in index.items() if len(v) > 1},
               "join_rule": "NOAA ICAO == OurAirports icao_code; source country subsets; ambiguous/unmatched kept NULL",
               "ordinary_raw_compressed_sha256": source["compressed_sha256"],
               "unmatched_or_review": [x for x in mappings.values() if x["mapping_status"] != "EXACT_ICAO_COORD_WITHIN25KM"]}
    (ROOT / "normalized/join_validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ["unmatched_or_review", "right_duplicate_icao_codes"]}, ensure_ascii=False))


if __name__ == "__main__":
    run()
