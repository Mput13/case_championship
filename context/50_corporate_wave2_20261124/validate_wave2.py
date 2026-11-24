#!/usr/bin/env python3
"""Validate the frozen Wave 2 tables and recompute the nine-node comparison offline."""

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
P1, P2, P3, P4 = "P1_SCREENING_V2", "P2_BENCHMARKS_V2", "P3_EVENTS_2027", "P4_DEMAND_GAP"
HUBS = dict(SVX="Екатеринбург", TJM="Тюмень", OVB="Новосибирск", KJA="Красноярск",
            LED="Санкт-Петербург", SVO="Москва (Шереметьево)", DME="Москва (Домодедово)",
            VKO="Москва (Внуково)", ZIA="Жуковский")
MOSCOW = {"SVO", "DME", "VKO", "ZIA"}
SCOPES = {"CONFIRMED_UNIT", "STRUCTURAL_HYPOTHESIS"}
SERIES = set("PMEF EEF INNOPROM CIPR SPIGF TNF REW KIF TRANSPORT".split())
SECTORS = set("DEFENCE_INDUSTRY ENERGY OIL_GAS INFRA_TRANSPORT MINING_MATERIALS FINANCE_DEV TECH_SCIENCE".split())
CRITERIA = "geography cooperation own_air_coverage market_coverage payer_channel strategic_access".split()
TESTS = "t1_gap t2_ground t3_payer t4_incumbent t5_durability".split()
QUANTITIES = ("mobile_travellers trips_per_traveller_period od_share round_trips_started "
              "one_way_od_pax required_seats_same_aircraft extra_baggage_kg").split()
DECISIONS = ("Go", "Conditional", "No-Go", "Insufficient-Evidence")
MONEY = {"ASK_AMOUNT", "CONTRACT_AMOUNT", "PAID_AMOUNT"}
STAGES = ("OFFER", "RFI", "TENDER", "AWARDED", "OPERATED", "PAID")
BUCKETS = ("FUTURE_CONFIRMED", "FUTURE_PROVISIONAL", "FUTURE_TBD", "HISTORICAL_PAST", "PROJECT_HORIZON")
PROOFS = {"MARKET_COVERED": "t1_gap", "GROUND_ALT": "t2_ground", "FRAGMENTED_PAYER": "t3_payer",
          "OWN_FLEET": "t4_incumbent", "LOW_MOBILITY": "t5_durability"}
UNKNOWN = {"", "UNKNOWN"}
BANNED = re.compile(r"\bMOW\b", re.IGNORECASE)
CLUSTER = re.compile(r"^W2-C(0[1-9]|1[01])-")
EVIDENCE_TYPES = set("IDENTITY AFFILIATION DEMAND_UNIT GAP PAYER INCUMBENT EVENT_DATE BENCHMARK".split())
S7_REQUIREMENTS = {
    "EV-W13-001": ("РН40302710", "RU-INN-2465142996"),
    "EV-W13-003": ("32616450256", "RU-INN-8904095427"),
}

SCHEMAS = {
    "evidence_wave2.csv": ("evidence_id",
        "evidence_id,source_url,issuer,document_date,checked_on,source_locator,claim_type,supported_claim,"
        "evidence_level,limitation"),
    "organizations_screening_v2.csv": ("org_id",
        "org_id,inn,legal_name,parent_org_id,sector,scope_role,tier,anchor_org_id,geography,cooperation,"
        "own_air_coverage,market_coverage,payer_channel,strategic_access,status,no_go_proof_type,decision_reason,"
        "decision_changing_fact,evidence_ids"),
    "benchmarks_cases_v2.csv": ("case_id",
        "case_id,case_name,country,buyer,operator,product,use_case,stage,outcome,key_terms,capacity_risk_owner,"
        "disruption_risk_owner,metric_code,metric_value,metric_unit,metric_period,currency,tax_basis,"
        "rf_transferable_term,rf_limit,evidence_ids,benchmark_role,qualifying_evidence_ids,qualification_reason"),
    "events_calendar_2027.csv": ("event_id",
        "event_id,event_or_project,series_id,event_year,event_name,event_type,host_city,nearest_airport_iata,"
        "date_status,start_date,end_date,phase_or_decline_trigger,target_orgs_summary,payer_or_organizer,"
        "evidence_ids,horizon_bucket"),
    "sites_and_links_graph.csv": ("row_id",
        "row_id,row_type,site_id,site_name,site_kind,org_id,city_id,lat_deg,lon_deg,timezone,to_site_id,"
        "terminal_id,access_mode,access_km,access_min,link_type,supplier_tier,anchor_org_id,flow_type,event_id,"
        "active_from,active_to,peak_from,peak_to,decline_on,decline_trigger,evidence_status,evidence_ids,"
        "open_question"),
    "supply_gap_pairs.csv": ("supply_id",
        "supply_id,opportunity_id,pair_id,gc_distance_km,probe_id,travel_date_local,checked_at,season_from,"
        "season_to,market_scope,mode,probe_status,origin_terminal_id,dest_terminal_id,via_arr_terminal_id,"
        "via_dep_terminal_id,operator_1,service_no_1,dep_at_1,arr_at_1,operator_2,service_no_2,dep_at_2,arr_at_2,"
        "connection_type,min_connection_min,weekly_freq_physical,origin_access_min,dest_access_min,"
        "predeparture_buffer_min,door_to_door_min,extra_nights,lost_work_min,offered_cabin,equipment,"
        "checked_party_size,public_inventory_status,guaranteed_seats,guarantee_status,bag_allowance_kg,"
        "extra_bag_capacity_kg,fare_rub,fare_basis,fare_terms,evidence_ids,limitation"),
    "opportunities.csv": ("opportunity_id",
        "opportunity_id,pair_id,from_site_id,to_site_id,from_iata,to_iata,gc_distance_km,graph_link_id,flow_type,"
        "event_id,period_from,period_to,beneficiary_org_id,organizer_org_id,buyer_org_id,payer_org_id,"
        "payer_status,procurement_channel,procurement_ref,demand_basis,demand_stage,as_of,"
        "requires_guaranteed_block,rail_acceptable,max_door_to_door_min,max_overnights,gap_status,gap_codes,"
        "t1_gap,t2_ground,t3_payer,t4_incumbent,t5_durability,decision,no_go_proof_type,recommended_product,"
        "decision_changing_fact,demand_evidence_ids,payer_evidence_ids,gap_evidence_ids"),
    "cohort_demand_scenarios.csv": ("row_id",
        "row_id,row_type,opportunity_id,pair_id,cohort_id,population_id,cohort_type,cabin_requirement,scenario,"
        "period_from,period_to,calendar_coverage,window_id,depart_not_before,depart_not_after,arrive_not_after,"
        "demand_basis,quantity_status,mobile_travellers,trips_per_traveller_period,od_share,round_trips_started,"
        "one_way_od_pax,required_seats_same_aircraft,extra_baggage_kg,split_allowed,evidence_ids,"
        "assumption_or_unknown"),
    "pooling_and_nodes.csv": ("allocation_id",
        "plan_id,allocation_id,leg_no,demand_window_row_id,option_type,hub_iata,supply_id,flight_instance_id,"
        "from_iata,to_iata,dep_at,arr_at,cabin,allocated_od_pax,payer_org_id,demand_basis,capacity_status,"
        "allocation_status,evidence_ids,limitation"),
    "hubs_and_nodes_summary.csv": ("hub_iata",
        "hub_iata,city_name,week_type,local_od_pax_base,connected_od_pairs_count,transit_od_pax_detour25_base,"
        "transit_od_pax_detour35_base,roundtrip_feasible_share_pct,compatible_pooling_groups,"
        "distinct_payers_count,event_peak_od_pax_base,demand_basis_scope,notes"),
}
NUMERIC = set(QUANTITIES) | set(
    "metric_value gc_distance_km access_km access_min max_door_to_door_min max_overnights event_year leg_no "
    "weekly_freq_physical min_connection_min origin_access_min dest_access_min predeparture_buffer_min "
    "door_to_door_min extra_nights lost_work_min checked_party_size guaranteed_seats bag_allowance_kg "
    "extra_bag_capacity_kg fare_rub allocated_od_pax local_od_pax_base connected_od_pairs_count "
    "transit_od_pax_detour25_base transit_od_pax_detour35_base roundtrip_feasible_share_pct "
    "compatible_pooling_groups distinct_payers_count event_peak_od_pax_base".split()
)


def require(condition, errors, message):
    if not condition:
        errors.append(message)


def split(value):
    return value.split(";") if value else []


def number(value):
    try:
        result = Decimal(value)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def iso_date(value):
    try:
        return date.fromisoformat(value) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None
    except ValueError:
        return None


def iso_time(value):
    try:
        result = datetime.fromisoformat(value)
        return result if result.utcoffset() is not None else None
    except ValueError:
        return None


def read_tables(root, errors):
    tables = {name: [] for name in SCHEMAS}
    paths = {p.name: p for p in root.glob("*.csv")}
    for name in SCHEMAS.keys() - paths.keys():
        errors.append(f"Missing {name}")
    for name, path in sorted(paths.items()):
        expected = SCHEMAS[name][1].split(",") if name in SCHEMAS else None
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.reader(stream, strict=True)
                header = next(reader, [])
                schema_ok = (expected is None or header == expected) and len(header) == len(set(header))
                require(header and schema_ok, errors, f"{name}: unexpected CSV header")
                require(not any(BANNED.search(value) for value in header), errors, f"{name}: banned airport code in header")
                for values in reader:
                    label = f"{name}:{reader.line_num}"
                    require(not any(BANNED.search(value) for value in values), errors, f"{label}: banned airport code")
                    if len(values) != len(header):
                        errors.append(f"{label}: expected {len(header)} fields, found {len(values)}")
                    elif name in tables and schema_ok:
                        tables[name].append(dict(zip(header, values)))
        except (OSError, UnicodeError, csv.Error) as exc:
            errors.append(f"{name}: {exc}")
    return tables


def check_integrity(tables, errors):
    keys = {}
    for name, rows in tables.items():
        field = SCHEMAS[name][0]
        seen = set()
        for row in rows:
            key = row[field]
            if name == "hubs_and_nodes_summary.csv":
                key = (row[field], row["week_type"], row["demand_basis_scope"])
            require(row[field] not in UNKNOWN and row[field].strip() == row[field] and key not in seen,
                    errors, f"{name}: invalid or duplicate key {key!r}")
            seen.add(key)
            for column in NUMERIC & row.keys():
                value = row[column]
                if not value:
                    continue
                n = number(value)
                allows_zero = (column == "weekly_freq_physical" and row.get("probe_status") == "NO_SERVICE")
                require(n is not None and (n > 0 or allows_zero and n == 0),
                        errors, f"{key}: invalid numeric value in {column}: {value!r}")
        keys[name] = seen

    graph = tables["sites_and_links_graph.csv"]
    site_ids = [r["site_id"] for r in graph if r["row_type"] == "SITE"]
    terminal_ids = set(site_ids) | {r["terminal_id"] for r in graph if r["row_type"] == "SITE"}
    require(len(set(site_ids)) == len(site_ids), errors, "Duplicate SITE site_id")
    require(all(site_id not in UNKNOWN for site_id in site_ids), errors, "Missing SITE site_id")
    targets = {
        "event_id": keys["events_calendar_2027.csv"],
        "opportunity_id": keys["opportunities.csv"],
        "supply_id": keys["supply_gap_pairs.csv"],
        "demand_window_row_id": keys["cohort_demand_scenarios.csv"],
        "graph_link_id": {r["row_id"] for r in graph if r["row_type"] == "LINK"},
        **dict.fromkeys(("site_id", "from_site_id", "to_site_id"), set(site_ids)),
    }
    for name, rows in tables.items():
        primary_key = SCHEMAS[name][0]
        for row in rows:
            label = row[primary_key]
            for field, value in row.items():
                if field.endswith("evidence_ids"):
                    refs = split(value)
                    require(len(refs) == len(set(refs)) and set(refs) <= keys["evidence_wave2.csv"],
                            errors, f"{label}: duplicate or unresolved {field} {value!r}")
                elif value not in UNKNOWN:
                    target = keys["organizations_screening_v2.csv"] if field.endswith("org_id") else targets.get(field)
                    if target is not None and field != primary_key:
                        require(value in target, errors, f"{label}: unresolved {field} {value!r}")
                    if field.endswith("terminal_id") and not value.startswith("CITY:"):
                        require(value in terminal_ids,
                                errors, f"{label}: unresolved terminal reference {value!r}")
    return keys


def usable_url(value):
    try:
        parsed = urlsplit(value)
        return bool(parsed.scheme in {"https", "http"} and parsed.hostname and "." in parsed.hostname
                    and not parsed.username and not re.search(r"[\s<>]", value))
    except ValueError:
        return False


def primary(refs, evidence, claim=None, *, fresh=False, horizon=None):
    for key in split(refs):
        record = evidence.get(key)
        if not record or not record["evidence_level"].startswith("PRIMARY_"):
            continue
        if claim and record["claim_type"] != claim:
            continue
        doc = iso_date(record["document_date"])
        dated_contract = (
            record["evidence_level"] == "PRIMARY_CONTRACT"
            and horizon is not None and horizon[0] is not None and horizon[1] is not None
            and horizon[0].year <= 2027 <= horizon[1].year
            and re.search(r"\b2027\b", record["supported_claim"])
        )
        if not fresh or doc and doc >= date(2025, 1, 1) or dated_contract:
            return True
    return False


def check_screening(rows, evidence, registry, errors):
    inns = set()
    sectors = {row["sector"] for row in rows}
    for row in rows:
        oid, inn = row["org_id"], row["inn"]
        if re.fullmatch(r"[0-9]{10}", inn):
            checksum = sum(int(digit) * weight for digit, weight in zip(inn, (2,4,10,3,5,9,4,6,8))) % 11 % 10
            require(checksum == int(inn[-1]), errors, f"{oid}: invalid INN checksum")
        else:
            errors.append(f"{oid}: invalid INN {inn!r}")
        require(inn not in inns and oid == f"RU-INN-{inn}", errors, f"{oid}: duplicate or inconsistent INN")
        inns.add(inn)
        criteria = [row[field] for field in CRITERIA]
        require(all(value in {"UNKNOWN", "SUPPORTS", "LIMITS", "MIXED"} for value in criteria),
                errors, f"{oid}: invalid screening criteria")
        status, proof = row["status"], row["no_go_proof_type"]
        require(status in {*DECISIONS, "Candidate"}, errors, f"{oid}: invalid screening status {status!r}")
        require(row["legal_name"] and row["decision_reason"], errors, f"{oid}: missing identity or decision reason")
        require(bool(split(row["evidence_ids"])), errors, f"{oid}: missing URL evidence")
        if status in {"Candidate", "Go"}:
            require(any(value != "UNKNOWN" for value in criteria), errors, f"{oid}: {status} with 6/6 UNKNOWN")
            require(primary(row["evidence_ids"], evidence, "DEMAND_UNIT", fresh=True), errors,
                    f"{oid}: {status} requires fresh primary demand-unit evidence")
        if status == "Go":
            for claim in ("GAP", "PAYER"):
                require(primary(row["evidence_ids"], evidence, claim), errors, f"{oid}: Go missing primary {claim}")
        if status == "No-Go":
            require(proof in PROOFS and oid in registry, errors, f"{oid}: No-Go missing documented proof")
        else:
            require(not proof, errors, f"{oid}: no_go_proof_type is only for No-Go")
        if status in {"Conditional", "Insufficient-Evidence"}:
            require(row["decision_changing_fact"] not in UNKNOWN, errors, f"{oid}: missing decision-changing fact")
    require(len(inns) >= 50 and sectors == SECTORS, errors, "Need ≥50 unique organizations across the 7 sectors")


def check_benchmarks(rows, evidence, errors):
    by_stage = {"RU": Counter(), "Global": Counter()}
    qualified = []
    for row in rows:
        label = row["case_id"]
        role = row["benchmark_role"]
        qualifiers = row["qualifying_evidence_ids"]
        code, value, unit, currency = (row[col] for col in ("metric_code", "metric_value", "metric_unit", "currency"))
        require(role in {"QUALIFIED", "COMPARATOR", "CONTEXT"}, errors, f"{label}: invalid benchmark role")
        require(row["stage"] in STAGES and re.fullmatch(r"[A-Z]{2}", row["country"]), errors, f"{label}: invalid stage or country")
        require(bool(code) == bool(value) == bool(unit), errors, f"{label}: metric code, value and unit travel together")
        if value and code in MONEY:
            require(re.fullmatch(r"[A-Z]{3}", currency), errors, f"{label}: monetary metric needs currency")
        else:
            require(not currency, errors, f"{label}: currency without monetary metric")
        if role != "QUALIFIED":
            require(not qualifiers, errors, f"{label}: only QUALIFIED may have qualifying_evidence_ids")
            continue
        if not primary(qualifiers, evidence) or not set(split(qualifiers)) <= set(split(row["evidence_ids"])):
            errors.append(f"{label}: qualifying evidence must include primary evidence and belong to evidence_ids")
            continue
        qualified.append(row)
        by_stage["RU" if row["country"] == "RU" else "Global"][row["stage"]] += 1
    for geography, counts in by_stage.items():
        require(sum(counts.values()) >= 4, errors, f"Need ≥4 qualified {geography} benchmarks")
    require(any(r["outcome"] in {"CURTAILED", "CANCELLED"} for r in qualified), errors,
            "Need a qualified curtailed or cancelled benchmark")
    require(any(r["use_case"] in {"EMERGENCY_ADHOC", "EVENT_ADHOC"} for r in qualified), errors,
            "Need a qualified emergency or event ad-hoc benchmark")
    return {region: {stage: counts[stage] for stage in STAGES} for region, counts in by_stage.items()}


def check_calendar(rows, airports, evidence, errors):
    future_series = set()
    for row in rows:
        eid, bucket = row["event_id"], row["horizon_bucket"]
        start, end = iso_date(row["start_date"]), iso_date(row["end_date"])
        require(bucket in BUCKETS and row["evidence_ids"], errors, f"{eid}: invalid calendar bucket or missing sources")
        require(all(not row[key] or iso_date(row[key]) is not None for key in ("start_date", "end_date")),
                errors, f"{eid}: invalid date")
        if start and end:
            require(start <= end, errors, f"{eid}: dates out of order")
        if bucket.startswith("FUTURE_"):
            require(row["event_year"] == "2027" and row["event_or_project"] == "EVENT", errors, f"{eid}: invalid 2027 event")
            future_series.add(row["series_id"])
        if bucket == "FUTURE_CONFIRMED":
            require(start and end and start.year == end.year == 2027 and row["date_status"] == "CONFIRMED"
                    and primary(row["evidence_ids"], evidence, "EVENT_DATE"), errors, f"{eid}: confirmed 2027 dates require primary evidence")
        if bucket == "FUTURE_TBD":
            require(not start and not end and row["date_status"] == "TBD", errors, f"{eid}: TBD event has fixed dates")
        iatas = set(split(row["nearest_airport_iata"])) - UNKNOWN
        require(all(re.fullmatch(r"[A-Z]{3}", a) for a in iatas), errors, f"{eid}: invalid airport code")
        if bucket.startswith("FUTURE_"):
            require(iatas <= airports.keys(), errors, f"{eid}: airport missing from graph")
        if row["host_city"] == "Москва" and bucket != "HISTORICAL_PAST":
            require(iatas == MOSCOW, errors, f"{eid}: keep all four Moscow airports separate")
    require(SERIES <= future_series and len(future_series) >= 10, errors, "Need ≥10 future editions including the nine registered forum series")
    require(not any(r["series_id"] == "ARMY" and r["horizon_bucket"].startswith("FUTURE_") for r in rows),
            errors, "Excluded ARMY event may not enter future projections")


def airport_coordinates(graph):
    airports = {}
    for row in graph:
        if row["row_type"] == "SITE" and row["site_id"].startswith("AIR:"):
            lat, lon = number(row["lat_deg"]), number(row["lon_deg"])
            if lat is not None and lon is not None and abs(lat) <= 90 and abs(lon) <= 180:
                airports[row["site_id"][4:]] = (float(lat), float(lon))
    return airports


def distance(airports, a, b):
    lat_a, lon_a = map(math.radians, airports[a])
    lat_b, lon_b = map(math.radians, airports[b])
    hav = (math.sin((lat_b - lat_a) / 2) ** 2
           + math.cos(lat_a) * math.cos(lat_b) * math.sin((lon_b - lon_a) / 2) ** 2)
    return 2 * 6371.0088 * math.asin(math.sqrt(min(1, hav)))


def check_opportunities(rows, graph, supply, evidence, calendar, orgs, errors):
    airports = airport_coordinates(graph)
    links = {r["row_id"]: r for r in graph if r["row_type"] == "LINK"}
    cities = {r["site_id"][4:]: r["city_id"] for r in graph
              if r["row_type"] == "SITE" and r["site_id"].startswith("AIR:")}
    clusters = set()
    found_s7 = set()
    refs_by_procurement = Counter(r["procurement_ref"] for r in rows if r["procurement_ref"])
    require(refs_by_procurement["АП086548"] == 1 and refs_by_procurement["АП086346"] == 1,
            errors, "СТНГ must have one charter procedure and a separate TMC procedure")
    for row in rows:
        oid = row["opportunity_id"]
        match = CLUSTER.match(oid)
        require(match, errors, f"{oid}: missing preregistered cluster number")
        if match:
            clusters.add(match[1])
        require(row["decision"] in DECISIONS and row["demand_basis"] in SCOPES
                and row["flow_type"] in {"REGULAR", "PROJECT", "EVENT"}, errors, f"{oid}: invalid opportunity classification")
        tests = [row[key] for key in TESTS]
        require(all(value in {"PASS", "FAIL", "UNKNOWN", "EXTERNAL_BLOCKED"} for value in tests),
                errors, f"{oid}: invalid T1–T5 status")
        require(row["decision_changing_fact"] not in UNKNOWN and row["demand_evidence_ids"],
                errors, f"{oid}: missing basis or decision-changing fact")
        require(iso_date(row["as_of"]) is not None, errors, f"{oid}: invalid as_of")
        horizon = tuple(iso_date(row[field]) for field in ("period_from", "period_to"))
        require((not row["period_from"] and not row["period_to"]) or
                (all(horizon) and horizon[0] <= horizon[1]), errors, f"{oid}: invalid period")
        a,b = row["from_iata"],row["to_iata"]
        for endpoint in (a,b):
            require(endpoint == "UNKNOWN" or endpoint in airports, errors, f"{oid}: unknown IATA {endpoint}")
        if a in airports and b in airports:
            gc = number(row["gc_distance_km"])
            require(a != b and gc is not None and gc == Decimal(f"{distance(airports, a, b):.2f}"),
                    errors, f"{oid}: missing or incorrect airport orthodromy")
            require(row["pair_id"] == "-".join(sorted((cities[a], cities[b]))),
                    errors, f"{oid}: pair_id does not match IATA cities")
        else:
            require(not row["gc_distance_km"], errors, f"{oid}: geometry without both airports")
        link = links.get(row["graph_link_id"])
        if link is not None:
            require((link["site_id"], link["to_site_id"]) == (f"AIR:{a}",f"AIR:{b}"),
                    errors, f"{oid}: graph link direction mismatch")
        if row["flow_type"] == "EVENT":
            require(calendar.get(row["event_id"], {}).get("horizon_bucket", "").startswith("FUTURE_"),
                    errors, f"{oid}: event flow needs a future event")
        if row["procurement_ref"] in {"АП086548", "АП086346"}:
            require(row["beneficiary_org_id"] == "RU-INN-7714572888"
                    and row["organizer_org_id"] == "RU-INN-7842155505"
                    and row["payer_org_id"] != row["organizer_org_id"],
                    errors, f"{oid}: keep the beneficiary and organizer distinct from the payer")
        if row["procurement_ref"] == "АП086346":
            require(row["gap_status"] == "MARKET_COVERED" and row["recommended_product"] == "CORPORATE_FARE",
                    errors, f"{oid}: TMC lot defaults to covered corporate fare")
        for key, (procurement, org) in S7_REQUIREMENTS.items():
            if row["procurement_ref"] == procurement and row["beneficiary_org_id"] == org:
                if key in split(row["payer_evidence_ids"]) or key in split(row["demand_evidence_ids"]):
                    found_s7.add(key)
        if row["decision"] == "Go":
            org = orgs.get(row["beneficiary_org_id"])
            require(org is not None and any(org[field] != "UNKNOWN" for field in CRITERIA), errors,
                    f"{oid}: Go requires a beneficiary with evidence on at least one screening criterion")
            require(row["demand_basis"] == "CONFIRMED_UNIT" and tests == ["PASS"] * len(TESTS),
                    errors, f"{oid}: Go requires a confirmed unit and all T1–T5")
            require(primary(row["demand_evidence_ids"], evidence, "DEMAND_UNIT", fresh=True, horizon=horizon),
                    errors, f"{oid}: Go missing fresh primary demand-unit proof")
            require(primary(row["gap_evidence_ids"], evidence, "GAP"), errors, f"{oid}: Go missing primary gap proof")
            require(row["payer_status"] == "CONFIRMED" and row["payer_org_id"] not in UNKNOWN
                    and row["procurement_channel"] not in UNKNOWN
                    and primary(row["payer_evidence_ids"], evidence, "PAYER"), errors, f"{oid}: Go requires a documented payer and channel")
        proof = row["no_go_proof_type"]
        if row["decision"] == "No-Go":
            require(proof in PROOFS and row["gap_status"] == proof and row.get(PROOFS.get(proof)) == "FAIL",
                    errors, f"{oid}: No-Go needs a demonstrated K1–K6 failure")
            claim = {"OWN_FLEET": "INCUMBENT", "FRAGMENTED_PAYER": "PAYER", "LOW_MOBILITY": "DEMAND_UNIT"}.get(proof, "GAP")
            refs = ";".join(row[k] for k in ("demand_evidence_ids", "payer_evidence_ids", "gap_evidence_ids"))
            require(primary(refs, evidence, claim), errors, f"{oid}: No-Go must cite primary {claim} proof")
        else:
            require(not proof, errors, f"{oid}: proof type applies only to No-Go")
    require(len(clusters) == 11, errors, f"Covered {len(clusters)}/11 preregistered clusters")
    require(found_s7 == S7_REQUIREMENTS.keys(), errors, f"S7 procurement evidence missing: {sorted(S7_REQUIREMENTS.keys() - found_s7)}")
    opportunity_pairs = {row["opportunity_id"]: row["pair_id"] for row in rows}
    for probe in supply:
        if probe["opportunity_id"] in opportunity_pairs:
            require(probe["pair_id"] == opportunity_pairs[probe["opportunity_id"]], errors,
                    f"{probe['supply_id']}: supply and opportunity pair IDs differ")
    supply_pairs = {row["pair_id"] for row in supply}
    screened = {row["pair_id"] for row in rows} - UNKNOWN
    geometric = {row["pair_id"] for row in rows if row["gc_distance_km"] and row["pair_id"]}
    require(len(geometric) >= 22 and len(geometric & supply_pairs) >= 20, errors,
            "Need ≥22 geometric city pairs, ≥20 with a supply probe")
    require(supply_pairs <= screened, errors, f"Supply pairs missing from opportunities: {sorted(supply_pairs - screened)}")
    return screened, geometric, supply_pairs


def check_cohorts(rows, opportunities, evidence, errors):
    scenarios = defaultdict(list)
    quantified = set()
    cap_by_op = defaultdict(list)
    for row in rows:
        rid = row["row_id"]
        o = opportunities.get(row["opportunity_id"])
        require(o is not None, errors, f"{rid}: missing opportunity")
        if o is None:
            continue
        require((row["pair_id"], row["demand_basis"]) == (o["pair_id"], o["demand_basis"]),
                errors, f"{rid}: incompatible pair or demand basis")
        require(row["row_type"] in {"PERIOD", "WINDOW"}
                and row["cohort_type"] in {"EXECUTIVE", "LINE_MANAGEMENT", "ENGINEERING", "ROTATION", "DELEGATION"}
                and row["cabin_requirement"] in {"Y", "J_REQUIRED", "J_PREFERRED", "UNKNOWN"},
                errors, f"{rid}: invalid cohort")
        window = row["window_id"]
        require(bool(window) == (row["row_type"] == "WINDOW"), errors, f"{rid}: invalid window key")
        require(row["population_id"] and row["cohort_id"] and row["assumption_or_unknown"] and row["evidence_ids"],
                errors, f"{rid}: missing population, cohort, sources or assumptions")
        bounds = ("depart_not_before", "depart_not_after", "arrive_not_after")
        times = [iso_time(row[key]) for key in bounds]
        require(all(not row[key] or t is not None for key, t in zip(bounds, times)),
                errors, f"{rid}: window timestamps need offsets")
        require(not all(times[:2]) or times[0] <= times[1], errors, f"{rid}: reversed window")
        start, end = iso_date(row["period_from"]), iso_date(row["period_to"])
        require((row["period_from"], row["period_to"]) == (o["period_from"], o["period_to"]),
                errors, f"{rid}: mismatched opportunity period")
        require(not any(times) or (start and end and all(start <= t.date() <= end for t in times if t)),
                errors, f"{rid}: window outside period")
        scenarios[(row["opportunity_id"], row["cohort_id"], row["row_type"])].append(row["scenario"])
        qty = row["quantity_status"]
        require(qty in {"UNKNOWN", "EXTERNAL_BLOCKED", "HISTORICAL_REQUEST", "CONFIRMED", "MODELED"},
                errors, f"{rid}: invalid quantity status")
        if qty in {"UNKNOWN", "EXTERNAL_BLOCKED"}:
            require(not any(row[field] for field in QUANTITIES), errors,
                    f"{rid}: unknown or blocked quantities must remain empty")
        if qty == "HISTORICAL_REQUEST":
            require(not any(row[field] for field in QUANTITIES[:5]), errors, f"{rid}: historical ask may only specify capacity constraints")
        if qty == "CONFIRMED":
            require(row["demand_basis"] == "CONFIRMED_UNIT" and primary(row["evidence_ids"], evidence, "DEMAND_UNIT"),
                    errors, f"{rid}: confirmed quantities lack primary demand-unit evidence")
        if row["od_share"]:
            share = number(row["od_share"])
            require(share is not None and 0 < share <= 1, errors, f"{rid}: OD share outside (0, 1]")
        if row["row_type"] == "WINDOW" and row["scenario"] == "BASE" and qty == "CONFIRMED":
            if (n := number(row["one_way_od_pax"])) is not None:
                quantified.add(row["pair_id"])
                if all(times[:2]):
                    same_aircraft = number(row["required_seats_same_aircraft"])
                    cap_by_op[row["opportunity_id"]].append((n, same_aircraft))
    for key, group in scenarios.items():
        require(sorted(group) == ["BASE", "MAX", "MIN"], errors, f"{key}: expected exactly MIN/BASE/MAX")
    covered = defaultdict(set)
    for opportunity_id, cohort_id, row_type in scenarios:
        covered[opportunity_id, cohort_id].add(row_type)
    for key, row_types in covered.items():
        require(row_types == {"PERIOD", "WINDOW"}, errors, f"{key}: missing PERIOD or WINDOW")
    require({key[0] for key in covered} == opportunities.keys(), errors, "Every opportunity needs cohort scenarios")
    for o in opportunities.values():
        if o["decision"] == "Go":
            threshold = {"CORPORATE_FARE": 15, "SEAT_BLOCK": 15, "CHARTER": 70, "DEDICATED_PROGRAM": 70}.get(o["recommended_product"])
            qualifying_window = any(
                n >= (120 if same_aircraft is not None and same_aircraft >= 150 else threshold)
                for n, same_aircraft in cap_by_op[o["opportunity_id"]]
            ) if threshold is not None else False
            require(qualifying_window, errors, f"{o['opportunity_id']}: Go needs documented Base volume in a dated window")
    return quantified - UNKNOWN


def check_pooling(rows, cohorts, opportunities, supply, airports, errors):
    signatures = defaultdict(set)
    confirmed_allocations = set()
    seats_by_flight = Counter()
    expected_pooling = {
        "YAMAL": {(origin, "NUX") for origin in ("UFA", "TJM", "OMS", "LED")},
        "URAL": {(origin, "SVX") for origin in ("ULY", "UFA", "KZN")},
        "INNOPROM": {(origin, "SVX") for origin in (*MOSCOW, "LED")},
    }
    found = defaultdict(set)
    for row in rows:
        aid = row["allocation_id"]
        w = cohorts.get(row["demand_window_row_id"])
        require(w is not None and w["row_type"] == "WINDOW" and w["scenario"] == "BASE",
                errors, f"{aid}: pooling requires a Base window")
        if w is None:
            continue
        o = opportunities.get(w["opportunity_id"])
        if o is None:
            continue
        a, b = row["from_iata"], row["to_iata"]
        found[row["plan_id"].split("-")[0]].add((a, b))
        require(a in airports and b in airports and a != b, errors, f"{aid}: invalid leg IATA")
        require((row["cabin"], row["demand_basis"], row["payer_org_id"])
                == (w["cabin_requirement"], w["demand_basis"], o["payer_org_id"]),
                errors, f"{aid}: pooling cannot mix cabin, basis or payer labels")
        require(row["option_type"] == "DIRECT" and row["leg_no"] == "1" and row["hub_iata"] == ""
                and (a,b) == (o["from_iata"],o["to_iata"]), errors, f"{aid}: invalid direct proposal")
        candidate = supply.get(row["supply_id"])
        if candidate:
            require((candidate["origin_terminal_id"], candidate["dest_terminal_id"]) == (f"AIR:{a}",f"AIR:{b}"),
                    errors, f"{aid}: supply probe does not match the direction")
        signatures[row["plan_id"]].add((a,b,w["window_id"],w["depart_not_before"],w["depart_not_after"],
                                        w["arrive_not_after"],row["cabin"],row["demand_basis"]))
        status = row["allocation_status"]
        require(status in {"PROVISIONAL", "UNKNOWN", "CONFIRMED"}, errors, f"{aid}: invalid allocation status")
        if status in {"PROVISIONAL", "UNKNOWN"}:
            require(not row["allocated_od_pax"] and not row["flight_instance_id"],
                    errors, f"{aid}: provisional proposal cannot claim allocated pax or a flight instance")
        if status == "CONFIRMED":
            seats = number(row["allocated_od_pax"])
            volume = number(w["one_way_od_pax"])
            key = (w["population_id"], a, b, w["window_id"])
            guarantee = number(candidate["guaranteed_seats"]) if candidate else None
            require(guarantee is not None and seats is not None and volume is not None and seats <= min(volume, guarantee)
                    and candidate["guarantee_status"] == "CONFIRMED" and row["flight_instance_id"]
                    and w["depart_not_before"] and w["depart_not_after"]
                    and iso_time(row["dep_at"]) and iso_time(row["arr_at"]) and key not in confirmed_allocations,
                    errors, f"{aid}: missing guaranteed inventory/window, or duplicate allocation")
            confirmed_allocations.add(key)
            if seats is not None and guarantee is not None:
                flight = (row["flight_instance_id"], row["cabin"])
                seats_by_flight[flight] += seats
                require(seats_by_flight[flight] <= guarantee, errors, f"{aid}: total allocation exceeds the cabin guarantee")
    for kind, routes in expected_pooling.items():
        require(routes <= found[kind], errors, f"{kind}: missing directional pooling candidates {sorted(routes - found[kind])}")
    for plan_id, values in signatures.items():
        require(len(values) == 1, errors, f"{plan_id}: incompatible directions, windows, classes or evidence scopes")


def compute_hubs(opportunities, cohorts, pooling, graph, supply):
    """Compare the same screened directional options per week/basis at every airport."""
    airports = airport_coordinates(graph)
    cities = {r["site_id"][4:]: r["city_id"] for r in graph
              if r["row_type"] == "SITE" and r["site_id"].startswith("AIR:")}
    direct = {(r["origin_terminal_id"][4:], r["dest_terminal_id"][4:])
              for r in supply if r["mode"] == "AIR_DIRECT" and r["probe_status"] == "FOUND"
              and r["origin_terminal_id"].startswith("AIR:") and r["dest_terminal_id"].startswith("AIR:")}
    sampled = defaultdict(set)
    opportunity_map = {o["opportunity_id"]: o for o in opportunities}
    for o in opportunities:
        a,b = o["from_iata"],o["to_iata"]
        if a in airports and b in airports and a != b:
            week = "EVENT_PEAK" if o["flow_type"] == "EVENT" else "REGULAR"
            sampled[week, o["demand_basis"]].add((o["pair_id"], a, b))
    windows = {row["row_id"]: row for row in cohorts if row["row_type"] == "WINDOW"}
    plans = defaultdict(list)
    for row in pooling:
        plans[row["plan_id"]].append(row)

    for hub, city_name in HUBS.items():
        if hub not in airports:
            continue
        for week in ("REGULAR", "EVENT_PEAK"):
            for basis in ("CONFIRMED_UNIT", "STRUCTURAL_HYPOTHESIS"):
                local, observed_local = set(), set()
                detour25, detour35, observed25, observed35 = set(), set(), set(), set()
                for pair, a, b in sampled[week, basis]:
                    if hub in (a, b):
                        local.add(pair)
                        if (a,b) in direct:
                            observed_local.add(pair)
                        continue
                    if cities[hub] in {cities[a], cities[b]}:
                        continue
                    direct_km = distance(airports, a, b)
                    detour = (distance(airports, a, hub) + distance(airports, hub, b)) / direct_km - 1
                    observed = (a,hub) in direct and (hub,b) in direct
                    if detour <= .25:
                        detour25.add(pair)
                        if observed:
                            observed25.add(pair)
                    if detour <= .35:
                        detour35.add(pair)
                        if observed:
                            observed35.add(pair)
                provisional, compatible, payers = set(), set(), set()
                for plan_id, allocations in plans.items():
                    first = allocations[0]
                    w = windows.get(first["demand_window_row_id"])
                    o = opportunity_map.get(w["opportunity_id"]) if w else None
                    if not o or (o["flow_type"] == "EVENT") != (week == "EVENT_PEAK"):
                        continue
                    if first["demand_basis"] != basis or hub not in (first["from_iata"],first["to_iata"]):
                        continue
                    if len({windows.get(r["demand_window_row_id"], {}).get("population_id") for r in allocations}) < 2:
                        continue
                    provisional.add(plan_id)
                    if all(r["allocation_status"] == "CONFIRMED" for r in allocations):
                        compatible.add(plan_id)
                        payers.update(r["payer_org_id"] for r in allocations if r["payer_org_id"])
                connected = observed_local | observed35
                notes = (
                    f"Пар в срезе={len({pair for pair, _, _ in sampled[week, basis]})}. "
                    f"Локальные пары={len(local)}, с наблюдением={len(observed_local)}. "
                    f"Геометрия транзита ≤25%/≤35%={len(detour25)}/{len(detour35)}, "
                    f"оба плеча наблюдались={len(observed25)}/{len(observed35)}. "
                    f"Связные пары={len(connected)}. Группы пулинга с ≥2 когортами (сценарий)={len(provisional)}. "
                    "Наблюдения включают маршрутные справочники и разнодатные срезы. "
                    "Для недельных объёмов, стыковки туда и обратно и квот нужен согласованный календарь и проверка мест."
                )
                yield {
                    "hub_iata": hub, "city_name": city_name, "week_type": week, "local_od_pax_base": "",
                    "connected_od_pairs_count": str(len(connected)) if connected else "",
                    "transit_od_pax_detour25_base": "", "transit_od_pax_detour35_base": "",
                    "roundtrip_feasible_share_pct": "",
                    "compatible_pooling_groups": str(len(compatible)) if compatible else "",
                    "distinct_payers_count": str(len(payers)) if payers else "",
                    "event_peak_od_pax_base": "", "demand_basis_scope": basis, "notes": notes,
                }


def validate(root=ROOT):
    errors = {name: [] for name in ("INTEGRITY", P1, P2, P3, P4)}
    integrity = errors["INTEGRITY"]
    tables = read_tables(root, integrity)
    check_integrity(tables, integrity)

    def table(name):
        return tables[f"{name}.csv"]

    def indexed(name, key):
        return {row[key]: row for row in table(name)}

    evidence = indexed("evidence_wave2", "evidence_id")
    for eid, record in evidence.items():
        require(re.fullmatch(r"EV-[A-Z0-9]+-\d+", eid) and usable_url(record["source_url"])
                and record["claim_type"] in EVIDENCE_TYPES, integrity, f"{eid}: invalid evidence identity, URL or type")
    orgs = indexed("organizations_screening_v2", "org_id")
    events = indexed("events_calendar_2027", "event_id")
    opportunities = indexed("opportunities", "opportunity_id")
    graph, supply = table("sites_and_links_graph"), table("supply_gap_pairs")
    cohorts, pooling = table("cohort_demand_scenarios"), table("pooling_and_nodes")
    try:
        registry = (root / "why_not_registry_v2.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors[P1].append(str(exc))
        registry = ""
    check_screening(orgs.values(), evidence, registry, errors[P1])
    by_stage = check_benchmarks(table("benchmarks_cases_v2"), evidence, errors[P2])
    airports = airport_coordinates(graph)
    check_calendar(events.values(), airports, evidence, errors[P3])
    require(HUBS.keys() <= airports.keys(), errors[P4], "Missing candidate hub coordinates")
    screened, geometric, supply_pairs = check_opportunities(
        opportunities.values(), graph, supply, evidence, events, orgs, errors[P4]
    )
    required_sites = {r["org_id"] for r in graph if r["row_type"] == "SITE"}
    require(all(org["status"] != "Go" or oid in required_sites for oid, org in orgs.items()),
            errors[P3], "Go organization is missing a graph site")
    quantified = check_cohorts(cohorts, opportunities, evidence, errors[P4])
    check_pooling(pooling, indexed("cohort_demand_scenarios", "row_id"), opportunities,
                  indexed("supply_gap_pairs", "supply_id"), airports, errors[P4])
    summary = list(compute_hubs(opportunities.values(), cohorts, pooling, graph, supply))
    actual = table("hubs_and_nodes_summary")
    key = lambda row: (row["hub_iata"], row["week_type"], row["demand_basis_scope"])
    require(len(summary) == 36 and sorted(actual, key=key) == sorted(summary, key=key),
            errors[P4], "The 9 × 2 × 2 hub summary must match the reproducible calculation")
    decided = {r["pair_id"] for r in opportunities.values() if r["decision"] == "Go"
               or r["decision"] == "No-Go" and r["no_go_proof_type"] in {"MARKET_COVERED", "GROUND_ALT"}}
    blocked = {r["pair_id"] for r in opportunities.values() if any(r[field] == "EXTERNAL_BLOCKED" for field in TESTS)}
    decisions = Counter(r["decision"] for r in opportunities.values())
    go_clusters = {r["opportunity_id"].split("-")[1] for r in opportunities.values() if r["decision"] == "Go" and CLUSTER.match(r["opportunity_id"])}
    all_buckets = Counter(r["horizon_bucket"] for r in events.values())
    buckets_2027 = Counter(r["horizon_bucket"] for r in events.values() if r["event_year"] == "2027")
    return {
        "overall_verdict": "FAIL" if any(errors.values()) else "PASS",
        **{name: "FAIL" if errors[name] or integrity else "PASS" for name in (P1, P2, P3, P4)},
        "organizations": len(orgs),
        "evidence_records": len(evidence),
        "pairs_screened": len(screened),
        "pairs_with_airport_geometry": len(geometric),
        "pairs_with_supply_probe": len(screened & supply_pairs),
        "pairs_quantified": len(quantified),
        "pairs_with_decided_gap": len(decided - UNKNOWN),
        "pairs_external_blocked": len(blocked - UNKNOWN),
        "opportunities_by_decision": {status: decisions[status] for status in DECISIONS},
        "go_clusters": len(go_clusters),
        "qualified_by_stage": by_stage,
        "events_2027_by_bucket": {bucket: buckets_2027[bucket] for bucket in BUCKETS},
        "calendar_by_bucket": {bucket: all_buckets[bucket] for bucket in BUCKETS},
        "warnings": [">70% of clusters are Go: check for overfitting"] if len(go_clusters) / 11 > .70 else [],
        "errors": {name: items for name, items in errors.items() if items},
    }


if __name__ == "__main__":
    report = validate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["overall_verdict"] == "PASS" else 1)
