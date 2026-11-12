"""Inventory competitor use and join preserved publications; no model rerun."""
import csv
import hashlib
import io
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PIN = "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6"
RESEARCH = "f9eafa804d2a90fa16f0b9521c2c48a48731614d"
INSTANCES = "context/28_evening_run_20261110/integration/dashboard_handoff/5101302f/evidence/dated_service_instances.json"


def blob(path, pin=PIN):
    return subprocess.check_output(["git", "show", f"{pin}:{path}"], cwd=ROOT)


def rows(path):
    return list(csv.DictReader(io.StringIO(blob(path).decode("utf-8-sig"))))


def save_csv(name, records):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)


def group_airport(a):
    # Follow the author model's analytical MOW grouping; keep physical IATA elsewhere.
    return "MOW" if a in ("DME", "SVO", "VKO") else a


def main():
    routes = [r for r in rows("data/processed/network_routes.csv")
              if r["scenario"] == "base" and r["variant"] == "Хаб OMS"]
    summary = next(r for r in rows("data/processed/network_summary.csv")
                   if r["scenario"] == "base" and r["hub"] == "OMS")
    demand = {frozenset((r["a"], r["b"])): r for r in rows("data/processed/demand_estimates.csv")}
    params = {r["parameter"]: float(r["base"]) for r in rows("data/assumptions/network.csv")}
    detailed = [r["values"] for r in json.loads(blob(INSTANCES, RESEARCH))["rows"]]
    oms = rows("data/external/colleagues/omsk_outbound_week_20261207.csv")
    airport_rows = {str(r["source_text_line"]): r for r in rows("data/external/colleagues/omsk_domestic_timetable_rows.csv")}
    canonical = {"Сибирь": "S7", "ЮТэйр": "UT", "Utair": "UT", "Ural airlines": "U6",
                 "Уральские а/л": "U6", "RED WINGS": "WZ", "РедВингс": "WZ",
                 "Россия": "FV", "Аэрофлот": "SU", "Победа": "DP", "Азимут": "A4",
                 "РусЛайн": "7R", "ЮВТ АЭРО": "RT", "ЮВТаэро": "RT",
                 "Северный Ветер": "N4", "ИКАР": "EO", "Ямал": "YC"}
    observations = []
    for r in detailed:
        observations.append(dict(origin=r["origin"], destination=r["destination"],
                                 date=r["date"], flight=r["flight"],
                                 carrier_raw=r["carriers"], carrier=canonical.get(r["carriers"], r["carriers"]),
                                 aircraft=r["aircraft"], source="preserved_dated_instances",
                                 publication_only=True, complete_market=False))
    for r in oms:
        # Preserve this source's unresolved Tobolsk alias; not part of the selected 12 legs.
        observations.append(dict(origin=r["origin_airport_iata"], destination=r["destination_airport_iata"],
                                 date=r["departure_date_local"], flight=r["outbound_flight_numeric"],
                                 carrier_raw=r["carrier_raw"], carrier=canonical.get(r["carrier_raw"], r["carrier_raw"]),
                                 aircraft=airport_rows.get(r["source_text_line"], {}).get("aircraft_type_raw", ""),
                                 source="pinned_omsk_outbound", publication_only=True, complete_market=False))
    # Deduplicate flights seen in both sources by carrier and numeric flight code.
    import re
    unique = {}
    for r in observations:
        raw_code = r["flight"].strip().upper()
        # S7-2566 and U6-388 include a digit in the airline prefix.
        # Dropping all non-digits would invent numbers 72566 and 6388.
        if len(raw_code) >= 2 and any(c.isalpha() for c in raw_code[:2]):
            raw_code = re.sub(r"^[A-Z0-9]{2}[-\s]?", "", raw_code)
        number = re.sub(r"\D", "", raw_code)
        r["flight_number_normalized"] = number
        r["flight_labels"] = r["flight"]
        key = (r["origin"], r["destination"], r["date"], r["carrier"], number)
        if key in unique:
            unique[key]["source"] = ";".join(sorted(set(unique[key]["source"].split(";")) | {r["source"]}))
            unique[key]["flight_labels"] = ";".join(sorted(set(unique[key]["flight_labels"].split(";")) | {r["flight"]}))
            unique[key]["aircraft"] = ";".join(sorted(set(unique[key]["aircraft"].split(";")) | {r["aircraft"]}))
        else:
            unique[key] = dict(r)
    joined = []
    diagnostics = []
    for r in routes:
        pair = frozenset((r["from"], r["to"]))
        obs = [v for v in unique.values()
               if frozenset((group_airport(v["origin"]), group_airport(v["destination"]))) == pair]
        rival = [v for v in obs if v["carrier"] != "WZ"]
        outbound = [v for v in rival if v["origin"] == "OMS"]
        inbound = [v for v in rival if v["destination"] == "OMS"]
        e = demand[pair]
        proxy = float(e["segments_base"]) / (2 * 52 * params["seats"] * params["competitor_lf"])
        freq = float(r["freq_week_each_way"])
        current_share = min(params["capture_competitive"], freq / (freq + proxy)) if r["direct_now"] == "True" else params["capture_open"] * (1 - math.exp(-freq / params["capture_freq_scale"]))
        seg = float(r["pax_year_segments"])
        transfer = float(r["pax_year_transfer_seg"])
        joined.append(dict(origin=r["from"], destination=r["to"], scenario="base", variant="Хаб OMS",
                           model_direct_now=r["direct_now"], rw_proposed_week_each_direction=freq,
                           model_local_pax_year=r["pax_year_local"], model_transfer_segments_year=transfer,
                           model_total_segments_year=seg, transfer_segment_share=round(transfer / seg, 6),
                           model_f_comp_proxy=round(proxy, 6) if r["direct_now"] == "True" else "NOT_USED",
                           model_local_capture_share=round(current_share, 6),
                           found_competitor_outbound_departures=len(outbound) if outbound else "UNKNOWN",
                           found_competitor_inbound_departures=len(inbound) if inbound else "UNKNOWN",
                           found_competitor_carriers=";".join(sorted({v["carrier"] for v in rival})),
                           found_airport_pairs=";".join(sorted({v["origin"] + ">" + v["destination"] for v in rival})),
                           publication_period="2026-12-07/2026-12-13", market_complete=False,
                           no_competitor_established=False, financial_recalculation="NOT_RUN"))
        if outbound and r["direct_now"] == "True":
            trial = min(params["capture_competitive"], freq / (freq + len(outbound)))
            diagnostics.append(dict(pair=r["from"] + "-" + r["to"], proposed_RW_frequency=freq,
                                    current_proxy=round(proxy, 6), found_outbound=len(outbound),
                                    current_capped_share=round(current_share, 6),
                                    trial_capped_share_if_found_count_were_complete=round(trial, 6),
                                    status="ILLUSTRATION_NOT_ADMITTED_INPUT",
                                    limitation="Different year/period, aircraft sizes, partial market and no passenger choice calibration; no demand or money rerun."))
    physical = sorted(unique.values(), key=lambda r: (r["origin"], r["destination"], r["date"], r["carrier"], r["flight"]))
    save_csv("selected_route_competition.csv", joined)
    save_csv("frequency_proxy_diagnostic.csv", diagnostics)
    save_csv("preserved_service_join.csv", physical)
    result = dict(model_commit=PIN, research_baseline=RESEARCH,
                  source_period="Published schedules for 2026-12-07 through 2026-12-13; no execution proof",
                  oms_base=summary,
                  transfer_trip_share=float(summary["transfer_od_year"]) / float(summary["od_trips_year"]),
                  transfer_segment_share=sum(float(r["pax_year_transfer_seg"]) for r in routes) / sum(float(r["pax_year_segments"]) for r in routes),
                  selected_routes=len(routes),
                  selected_routes_with_positive_dated_competitor_evidence=sum(bool(r["found_competitor_carriers"]) for r in joined),
                  selected_routes_without_positive_dated_competitor_evidence=sum(not bool(r["found_competitor_carriers"]) for r in joined),
                  selected_routes_with_complete_market=0,
                  detailed_input_rows=len(detailed), omsk_input_rows=len(oms),
                  unique_joined_publications=len(physical),
                  joined_carrier_counts=dict(Counter(r["carrier"] for r in physical)),
                  route_competitor_rows=len(rows("data/manual/route_competitors.csv")),
                  route_competitor_todo_rows=len(rows("data/manual/route_competitors_todo.csv")),
                  competitor_base_cases=len(rows("data/manual/competitor_bases.csv")),
                  competitor_hub_flags=dict(Counter(r["competitor_hub"] for r in rows("data/manual/competitor_hubs.csv"))),
                  route_diagnostics=diagnostics,
                  scope="Joins and arithmetic on saved inputs only; no full model run, price inference, new schedules or API calls.")
    (OUT / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    paths = ["src/network_model.py", "src/od_model.py", "src/build_dashboard.py", "src/build_criteria.py",
             "data/manual/competitor_bases.csv", "data/manual/competitor_hubs.csv",
             "data/external/colleagues/route_product_cards.csv", "data/external/colleagues/omsk_outbound_week_20261207.csv",
             "data/processed/network_routes.csv", "data/processed/network_summary.csv"]
    lock = dict(model_commit=PIN, research_baseline=RESEARCH,
                model_blob_sha256={p: hashlib.sha256(blob(p)).hexdigest() for p in paths},
                dated_instances_sha256=hashlib.sha256(blob(INSTANCES, RESEARCH)).hexdigest())
    (OUT / "source_lock.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("oms_base", "joined_carrier_counts")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
