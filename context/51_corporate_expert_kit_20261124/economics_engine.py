#!/usr/bin/env python3
"""Reproduce Wave 3 economics from the frozen Wave 2 sources, using only Python's stdlib."""

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
W2 = ROOT.parent / "50_corporate_wave2_20261124"
W1 = ROOT.parent / "49_corporate_screening_20261124"
BRIEF = ROOT.parent / "48_corporate_demand_task_20261124"
SIZES = {
    "organizations_screening_v2": (68, "org_id"),
    "benchmarks_cases_v2": (18, "case_id"),
    "events_calendar_2027": (29, "event_id"),
    "evidence_wave2": (352, "evidence_id"),
    "sites_and_links_graph": (222, "row_id"),
    "supply_gap_pairs": (147, "supply_id"),
    "opportunities": (180, "opportunity_id"),
    "hubs_and_nodes_summary": (36, None),
}
FORECAST = {"FUTURE_CONFIRMED": 4, "FUTURE_PROVISIONAL": 1, "FUTURE_TBD": 6}
LEVELS = set(
    "PRIMARY_REPORT SECONDARY_MEDIA UNAVAILABLE_PP301 UNAVAILABLE_TECH PRIMARY_TENDER "
    "PRIMARY_SCHEDULE_TARIFF PRIMARY_REGISTRY SECONDARY_AGGREGATOR SECONDARY_LEGAL "
    "PRIMARY_SCHEDULE PRIMARY_EVENT PRIMARY_POLICY SECONDARY_SCHEDULE PRIMARY_OFFICIAL".split()
)
OBS, HIST, SCEN, RW = "OBSERVED_OPEN", "HISTORICAL_RFI", "SCENARIO_MODEL", "NEEDS_RW_DATA"
SSJ, SJ, TU = "SSJ100 100Y", "SJ-100 2-class", "Ту-214 2-class"
FLEET_FIELDS = (
    "rank airport_pair from_iata to_iata city_pair_id gc_distance_km route_distance_km_k110 "
    "est_block_time_h distance_band ssj95b_100y_fit sj100_pd8_fit tu214_2class_fit "
    "longhaul_fit j_class_constraint_note primary_cluster_context fleet_decision_note"
).split()


def check(condition, detail):
    if not condition:
        raise ValueError(detail)


def ids(text):
    return re.findall(r"EV-[A-Z0-9]+-\d+", text)


def distance(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    hav = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(hav)))


def load_sources():
    tables = {}
    for name, (count, key) in SIZES.items():
        with (W2 / f"{name}.csv").open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        check(len(rows) == count and all(None not in row and None not in row.values() for row in rows), name)
        if key:
            check(len({row[key] for row in rows if row[key]}) == count, f"{name}: {key}")
        tables[name] = rows

    evidence = {row["evidence_id"]: row for row in tables["evidence_wave2"]}
    for name, rows in tables.items():
        for row in rows:
            for field, value in row.items():
                if field.endswith("evidence_ids"):
                    check(set(filter(None, value.split(";"))) <= evidence.keys(), f"{name}: {value}")
    check(all(e["evidence_level"] in LEVELS and e["claim_type"] in {
        "IDENTITY", "AFFILIATION", "GAP", "PAYER", "INCUMBENT", "EVENT_DATE", "BENCHMARK"
    } for e in evidence.values()), "Словарь доказательств или изменился срез объёма")
    organizations = tables["organizations_screening_v2"]
    check(len({o["inn"] for o in organizations if o["inn"].isdigit()}) == 68, "ИНН")
    check(all(o["decision_changing_fact"] and o["decision_reason"] and o["evidence_ids"]
              for o in organizations if o["status"] == "Conditional"), "Пустой Conditional по юрлицу")
    future = [e for e in tables["events_calendar_2027"] if e["horizon_bucket"].startswith("FUTURE_")]
    check(Counter(r["horizon_bucket"] for r in future) == FORECAST, "Состав будущих событий")
    check(all(r["event_year"] == "2027" and r["series_id"] != "ARMY" for r in future), "Периметр событий")
    for row in future:
        check(row["date_status"] == row["horizon_bucket"].removeprefix("FUTURE_")
              and ((not row["start_date"] and not row["end_date"]) if row["date_status"] == "TBD"
                   else date.fromisoformat(row["start_date"]) <= date.fromisoformat(row["end_date"])),
              row["event_id"])
    qualified = [b for b in tables["benchmarks_cases_v2"] if b["benchmark_role"] == "QUALIFIED"]
    check(len(qualified) == 13 and all(b["qualifying_evidence_ids"] and b["qualification_reason"] for b in qualified),
          "Отбор бенчмарков")
    check(evidence["EV-W13-001"]["supported_claim"].startswith("РН40302710")
          and evidence["EV-W13-003"]["supported_claim"].startswith("Севернефтегазпром"),
          "W2-R2: привязка закупок")
    check(Counter(o["decision"] for o in tables["opportunities"]) ==
          {"Conditional": 104, "Insufficient-Evidence": 76}, "Статусы возможностей")
    gaps = {"UNKNOWN", "MARKET_COVERED", "GROUND_ALT", "OWN_FLEET", "FRAGMENTED_PAYER", "LOW_MOBILITY"}
    tests = ("t1_gap", "t2_ground", "t3_payer", "t4_incumbent", "t5_durability")
    conditional_comparators = []
    for o in tables["opportunities"]:
        check(o["demand_basis"] == "STRUCTURAL_HYPOTHESIS" and o["gap_status"] in gaps
              and all(o[t] in {"UNKNOWN", "EXTERNAL_BLOCKED"} for t in tests), o["opportunity_id"])
        if o["decision"] == "Conditional":
            check(o["decision_changing_fact"].strip() and (o["demand_evidence_ids"] or o["gap_evidence_ids"]),
                  o["opportunity_id"])
            if all(o[t] == "UNKNOWN" for t in ("gap_status", *tests)) and o["recommended_product"] == "UNKNOWN":
                conditional_comparators.append(o["opportunity_id"])
    check(conditional_comparators == ["W2-C05-ATE-RAIL"], "Необоснованный Conditional без продукта")
    return tables, evidence, future, qualified


def make_fleet(tables):
    airports = {}
    for row in tables["sites_and_links_graph"]:
        if row["row_type"] == "SITE" and row["site_kind"] == "AIRPORT":
            code = row["site_id"].removeprefix("AIR:")
            lat, lon = float(row["lat_deg"]), float(row["lon_deg"])
            check(re.fullmatch(r"[A-Z]{3}", code) and code not in airports
                  and abs(lat) <= 90 and abs(lon) <= 180, row["site_id"])
            airports[code] = ((lat, lon), row["city_id"])
    check(len(airports) == 29, "Реестр аэропортов")
    pairs = {}
    for s in tables["supply_gap_pairs"]:
        check(s["mode"] in {"AIR_DIRECT", "AIR_CONNECT", "RAIL", "ROAD"}
              and s["probe_status"] in {"FOUND", "UNAVAILABLE"}
              and s["connection_type"] in {"DIRECT", "UNKNOWN", "STOP_SAME_AIRCRAFT"}
              and s["market_scope"] == "PUBLIC_SCHEDULED"
              and s["public_inventory_status"] == s["guarantee_status"] == "UNKNOWN", s["supply_id"])
        for i in (1, 2):
            dep, arr = s[f"dep_at_{i}"], s[f"arr_at_{i}"]
            check(bool(dep) == bool(arr), s["supply_id"])
            if dep:
                start, end = datetime.fromisoformat(dep), datetime.fromisoformat(arr)
                check(start.tzinfo and end.tzinfo and start < end, s["supply_id"])
        if s["extra_nights"]:
            check(s["extra_nights"].isdigit() and s["probe_status"] == "FOUND"
                  and s["dep_at_1"] and s["arr_at_1"] and s["door_to_door_min"], s["supply_id"])
        for field in ("fare_rub", "door_to_door_min", "guaranteed_seats", "weekly_freq_physical"):
            check(not s[field] or (math.isfinite(float(s[field])) and float(s[field]) > 0),
                  f"{s['supply_id']}: {field}")
        endpoints = s["origin_terminal_id"], s["dest_terminal_id"]
        if not all(x.startswith("AIR:") for x in endpoints):
            check(not s["gc_distance_km"], s["supply_id"])
            continue
        a, b = sorted(t.removeprefix("AIR:") for t in endpoints)
        coordinates, cities = zip(airports[a], airports[b])
        km = round(distance(*coordinates), 2)
        check(a != b and s["gc_distance_km"] and float(s["gc_distance_km"]) == km
              and s["pair_id"] == "-".join(sorted(cities)), s["supply_id"])
        pairs[a, b] = (km, s["pair_id"])

    expected = {
        ("LED", "NUX"): 2379.56, ("NUX", "VKO"): 2370.23, ("DME", "NUX"): 2356.12,
        ("NUX", "SVO"): 2334.46, ("NUX", "ZIA"): 2333.89, ("NUX", "UFA"): 1695.98,
        ("IKT", "PEE"): 3071.72, ("KJA", "VVO"): 3124.58, ("DME", "VVO"): 6410.51,
        ("SVO", "VVO"): 6405.92, ("VKO", "VVO"): 6434.79, ("VVO", "ZIA"): 6389.09,
        ("LED", "SVX"): 1801.01, ("IKT", "MJZ"): 1276.45, ("ABA", "KCY"): 280.99,
        ("SVX", "UFA"): 393.12, ("KZN", "SVX"): 723.52, ("SVX", "ULY"): 796.99,
    }
    check(len(pairs) == 44, "Аэропортовые пары в срезах предложения")
    contexts = defaultdict(set)
    for o in tables["opportunities"]:
        key = tuple(sorted((o["from_iata"], o["to_iata"])))
        if o["from_iata"] in airports and o["to_iata"] in airports and key[0] != key[1]:
            coordinates, cities = zip(*(airports[iata] for iata in key))
            km = round(distance(*coordinates), 2)
            check(o["gc_distance_km"] and float(o["gc_distance_km"]) == km
                  and o["pair_id"] == "-".join(sorted(cities)), o["opportunity_id"])
            pairs[key] = (km, o["pair_id"])
            contexts[key].add(o["opportunity_id"].split("-")[1])
        else:
            check(not o["gc_distance_km"], o["opportunity_id"])
    check(len(pairs) == 53 and all(pairs[p][0] == km for p, km in expected.items()), "Контрольные ортодромии")

    cluster_names = dict(zip(
        (f"C{i:02}" for i in range(1, 12)),
        ["СТНГ", "Газпром нефть", "Севернефтегазпром", "РН-Ванкор", "Атомная кооперация",
         "ОАК / ОДК / ВСМПО", "РусГидро", "РЖД / Почта России", "Ямбург / АЛРОСА / Россети",
         "Форумы", "Банки / ГТЛК / ВЭБ.РФ"],
    ))
    matrix = []
    for rank, ((a, b), (km, city_pair)) in enumerate(sorted(pairs.items(), key=lambda p: (-p[1][0], p[0])), 1):
        route = round(km * 1.10, 2)
        band = next((label for upper, label in (
            (900, "LE_900"), (2250, "901_2250"), (2450, "2251_2450"), (5000, "2451_5000")
        ) if km <= upper), "GT_5000")
        ssj_fit = ("FIT" if km <= 2250 else
                   "BORDERLINE_PAYLOAD_CHECK" if km <= 2450 else "OUT_OF_RANGE")
        sj_fit = "CANDIDATE_PERFORMANCE_CHECK" if km <= 2450 else "OUT_OF_RANGE"
        tu_fit = "CANDIDATE_PERFORMANCE_CHECK" if route <= 5000 else "OUTSIDE_STUDY_ENVELOPE"
        note = "[MODEL-ESTIMATE] Время прямого плеча. [NEEDS-RW-DATA] Доступность борта, аэродром, масса, запасной, ветер."
        if (a, b) == ("LED", "NUX"):
            note += " +24,56 км к ориентиру SSJ-95B 2 355 км по ортодромии. Запросить зимний профиль ЯНАО, МВМ, багаж и запасной."
        if (a, b) == ("KHV", "TYD"):
            note += " Наблюдалась посадка BQS. Для оборота отдельно считать KHV–BQS и BQS–TYD."
        matrix.append(dict(zip(FLEET_FIELDS, (
            rank, f"{a}-{b}", a, b, city_pair, km, route, round(0.45 + route / 760.0, 2), band,
            ssj_fit, sj_fit, tu_fit,
            "SCREEN_WIDEBODY_IF_DEMAND_VALIDATED" if route > 5000 else "NOT_REQUIRED_BY_DISTANCE_SCREEN",
            "100Y без J. Свободное соседнее Y-кресло расходует место и допустимо при согласии клиента. "
            "Компоновку и число J-кресел SJ-100 / Ту-214 запросить [NEEDS-RW-DATA].",
            " / ".join(cluster_names[c] for c in sorted(contexts[a, b])) or "Срез предложения Волны 2", note,
        ))))
    return matrix, airports


def hubs_summary(tables, airports):
    rows = tables["hubs_and_nodes_summary"]
    hubs = {"SVX", "TJM", "OVB", "KJA", "LED", "SVO", "DME", "VKO", "ZIA"}
    check({(r["hub_iata"], r["week_type"], r["demand_basis_scope"]) for r in rows} == {
        (hub, week, basis) for hub in hubs for week in ("REGULAR", "EVENT_PEAK")
        for basis in ("CONFIRMED_UNIT", "STRUCTURAL_HYPOTHESIS")
    }, "Ключи 36 срезов узлов")
    direct = {(s["origin_terminal_id"][4:], s["dest_terminal_id"][4:])
              for s in tables["supply_gap_pairs"] if s["mode"] == "AIR_DIRECT" and s["probe_status"] == "FOUND"}
    sample = defaultdict(set)
    for o in tables["opportunities"]:
        a, b = o["from_iata"], o["to_iata"]
        if a in airports and b in airports and a != b:
            week = "EVENT_PEAK" if o["flow_type"] == "EVENT" else "REGULAR"
            sample[week, o["demand_basis"]].add((o["pair_id"], a, b))
    result = []
    for row in rows:
        h = row["hub_iata"]
        local, geometry25, geometry35, observed25, observed35 = (set() for _ in range(5))
        for city_pair, a, b in sample[row["week_type"], row["demand_basis_scope"]]:
            if h in (a, b):
                if (a, b) in direct:
                    local.add(city_pair)
                continue
            if airports[h][1] in {airports[a][1], airports[b][1]}:
                continue
            p, q, r = (airports[x][0] for x in (a, b, h))
            detour = (distance(p, r) + distance(r, q)) / distance(p, q) - 1
            observed = (a, h) in direct and (h, b) in direct
            for limit, geometry, flown in ((0.25, geometry25, observed25), (0.35, geometry35, observed35)):
                if detour <= limit:
                    geometry.add(city_pair)
                    if observed:
                        flown.add(city_pair)
        connected = len(local | observed35)
        check(connected == int(row["connected_od_pairs_count"] or "0"), f"Связные пары {h}")
        entry = {k: (None if v == "" else v) for k, v in row.items() if k != "notes"}
        entry.update(geometry_pairs_25=len(geometry25), geometry_pairs_35=len(geometry35),
                     observed_transit_pairs_25=len(observed25), observed_transit_pairs_35=len(observed35),
                     connected_geometry_pairs=connected)
        result.append(entry)
    regular = {x["hub_iata"]: x for x in result
               if x["week_type"] == "REGULAR" and x["demand_basis_scope"] == "STRUCTURAL_HYPOTHESIS"}
    keys = ("geometry_pairs_25", "geometry_pairs_35", "observed_transit_pairs_25", "observed_transit_pairs_35")
    check(tuple(regular["SVX"][k] for k in keys) == tuple(regular["TJM"][k] for k in keys) == (3, 4, 0, 0)
          and regular["SVO"]["connected_geometry_pairs"] == 3, "W2-R6: сопоставимость узлов")
    return result


# Expressions have the same identifiers and arithmetic in Python, Excel and JS.
# Keep rounding at publication, except discrete inventory and geometry calculations.
COMMON = [
    ("j_passengers", "ROUNDUP(pax * j_share_pct / 100, 0)"),
    ("y_passengers", "pax - j_passengers"),
    ("saleable_seats_per_aircraft", "ROUNDDOWN(aircraft_seats * (1 - payload_seat_haircut_pct / 100), 0)"),
    ("effective_seats_per_aircraft", "saleable_seats_per_aircraft - ROUNDUP(j_passengers / aircraft_count, 0) * euro_seats_per_j"),
    ("capacity_passengers", "MIN(effective_seats_per_aircraft, effective_sellable_limit_per_aircraft) * aircraft_count"),
    ("capacity_fit", "IF(pax <= capacity_passengers, 1, 0)"),
    ("j_policy_fit", "IF(j_passengers <= j_seats_per_aircraft * aircraft_count, 1, IF(j_required + IF(euro_seats_per_j <= 0, 1, 0) > 0, 0, 1))"),
    ("split_fit", "IF(aircraft_count <= 1, 1, split_allowed)"),
    ("client_cash_excl_fare_rub", "bag_rub + transfer_rub + overnight_rub + disruption_probability_pct / 100 * disruption_cash_rub"),
    ("client_alt_cash_tct_rub", "alt_fare_rub + alt_bag_rub + alt_transfer_rub + alt_overnight_rub + alt_disruption_probability_pct / 100 * alt_disruption_cash_rub"),
    ("client_door_to_door_h", "block_h + access_buffer_h + destination_transfer_h"),
    ("client_alt_door_to_door_h", "alt_duration_h + alt_access_buffer_h"),
    ("client_lost_work_h", "client_door_to_door_h * work_overlap_pct / 100 + disruption_probability_pct / 100 * disruption_work_h"),
    ("client_alt_lost_work_h", "client_alt_door_to_door_h * alt_work_overlap_pct / 100 + alt_disruption_probability_pct / 100 * alt_disruption_work_h"),
    ("client_time_value_rub", "client_lost_work_h * loaded_hour_rub"),
    ("client_alt_time_value_rub", "client_alt_lost_work_h * loaded_hour_rub"),
    ("client_blended_offer_per_paid_seat_rub", "offered_price_rub * (1 + j_passengers / pax * j_fare_premium_pct / 100)"),
    ("client_alt_total_tct_rub", "client_alt_cash_tct_rub + client_alt_time_value_rub"),
    ("client_max_offer_per_pax_rub", "client_alt_total_tct_rub - client_cash_excl_fare_rub - client_time_value_rub"),
]

CHARTER = [
    ("operational_screen_pass", "capacity_fit * j_policy_fit * split_fit"),
    ("rw_aircraft_equivalent_cycles", "aircraft_count * (1 + ferry_factor)"),
    ("rw_billable_block_h", "block_h * rw_aircraft_equivalent_cycles"),
    ("rw_flight_non_doc_cost_rub", "rw_aircraft_equivalent_cycles * (fixed_per_departure_rub + airport_per_departure_rub) + aircraft_count * airport_per_departure_rub * parking_icing_pct / 100"),
    ("rw_total_flight_cost_rub", "rw_billable_block_h * doc_per_block_h_rub + rw_flight_non_doc_cost_rub"),
    ("rw_net_revenue_rub", "pax * client_blended_offer_per_paid_seat_rub * net_revenue_pct / 100"),
    ("rw_net_contribution_rub", "rw_net_revenue_rub - rw_total_flight_cost_rub"),
    ("rw_break_even_charter_price_rub", "rw_total_flight_cost_rub / (net_revenue_pct / 100)"),
    ("rw_break_even_seat_price_rub", "rw_break_even_charter_price_rub / pax"),
    ("rw_target_price_per_seat_rub", "rw_break_even_seat_price_rub / (1 - target_margin_pct / 100)"),
    ("rw_doc_max_rub_per_block_h", "(rw_net_revenue_rub * (1 - target_margin_pct / 100) - rw_flight_non_doc_cost_rub) / rw_billable_block_h"),
    ("client_fare_per_flown_pax_rub", "client_blended_offer_per_paid_seat_rub"),
    ("client_max_unit_contract_price_rub", "client_max_offer_per_pax_rub"),
]

BLOCK = [
    ("rw_paid_seats", "MAX(MIN(pax, quota_seats), ROUNDUP(quota_seats * minimum_take_pct / 100, 0))"),
    ("rw_released_seats", "quota_seats - rw_paid_seats"),
    ("rw_unavailable_y_seats", "j_passengers * euro_seats_per_j"),
    ("rw_inventory_screen_pass", "IF(quota_seats <= capacity_passengers, IF(pax <= quota_seats, 1, 0), 0)"),
    ("operational_screen_pass", "capacity_fit * j_policy_fit * split_fit * rw_inventory_screen_pass"),
    ("rw_held_j_seats", "IF(euro_seats_per_j > 0, 0, MIN(j_passengers, rw_paid_seats))"),
    ("rw_expected_displaced_j_seats", "rw_held_j_seats * j_displacement_lf_pct / 100"),
    ("rw_expected_displaced_y_seats", "(rw_paid_seats - rw_held_j_seats + rw_unavailable_y_seats + rw_released_seats * release_spoilage_pct / 100) * displacement_lf_pct / 100"),
    ("rw_expected_displaced_seats", "rw_expected_displaced_y_seats + rw_expected_displaced_j_seats"),
    ("rw_displacement_cost_rub", "rw_expected_displaced_y_seats * market_net_yield_rub + rw_expected_displaced_j_seats * market_j_net_yield_rub"),
    ("rw_incremental_service_cost_rub", "pax * marginal_service_per_pax_rub + block_admin_rub"),
    ("rw_net_revenue_rub", "rw_paid_seats * client_blended_offer_per_paid_seat_rub * net_revenue_pct / 100"),
    ("rw_block_net_contribution_after_displacement_rub", "rw_net_revenue_rub - rw_incremental_service_cost_rub - rw_displacement_cost_rub"),
    ("rw_net_contribution_rub", "rw_block_net_contribution_after_displacement_rub"),
    ("rw_break_even_seat_price_rub", "(rw_incremental_service_cost_rub + rw_displacement_cost_rub) / (rw_paid_seats * net_revenue_pct / 100)"),
    ("rw_target_price_per_seat_rub", "rw_break_even_seat_price_rub / (1 - target_margin_pct / 100)"),
    ("client_fare_per_flown_pax_rub", "client_blended_offer_per_paid_seat_rub * rw_paid_seats / pax"),
    ("client_max_unit_contract_price_rub", "client_max_offer_per_pax_rub * pax / rw_paid_seats"),
]

CLIENT_TOTALS = [
    ("client_cash_tct_rub", "client_fare_per_flown_pax_rub + client_cash_excl_fare_rub"),
    ("client_total_tct_rub", "client_cash_tct_rub + client_time_value_rub"),
    ("client_tct_savings_vs_alt_rub", "client_alt_total_tct_rub - client_total_tct_rub"),
]

SUM_ROUND_TRIP = (
    "client_cash_tct_rub", "client_time_value_rub", "client_total_tct_rub",
    "client_alt_cash_tct_rub", "client_alt_time_value_rub", "client_alt_total_tct_rub",
    "client_lost_work_h", "client_alt_lost_work_h", "client_tct_savings_vs_alt_rub",
)
CHARTER_SUM = (
    "rw_net_contribution_rub", "rw_billable_block_h", "rw_net_revenue_rub", "rw_total_flight_cost_rub",
    "rw_flight_non_doc_cost_rub", "rw_break_even_charter_price_rub",
)
BLOCK_SUM = ("rw_net_contribution_rub", "rw_displacement_cost_rub", "rw_incremental_service_cost_rub",
             "rw_block_net_contribution_after_displacement_rub")
TICKET = [
    ("client_fare_per_flown_pax_rub", "client_blended_offer_per_paid_seat_rub"),
    ("client_max_unit_contract_price_rub", "client_max_offer_per_pax_rub"),
]
FORMULAS = {"CHARTER": [*COMMON, *CHARTER, *CLIENT_TOTALS],
            "BLOCK": [*COMMON, *BLOCK, *CLIENT_TOTALS],
            "TICKET": [*(item for item in COMMON if item[0].startswith("client_")), *TICKET, *CLIENT_TOTALS]}
# Ticket comparators are paid per traveller and require no reserved inventory or aircraft commitments.
FORMULAS["TICKET"].insert(0, COMMON[0])
CYCLE_OUTPUTS = {"CHARTER": SUM_ROUND_TRIP + CHARTER_SUM,
                 "BLOCK": SUM_ROUND_TRIP + BLOCK_SUM, "TICKET": SUM_ROUND_TRIP}


def round_excel(x, digits):
    scale = 10 ** digits
    return math.copysign(math.floor(abs(x) * scale + 0.500000001) / scale, x)


def roundup(x, digits):
    return math.copysign(math.ceil(abs(x) * 10 ** digits - 1e-10) / 10 ** digits, x)


def rounddown(x, digits):
    return math.copysign(math.floor(abs(x) * 10 ** digits + 1e-10) / 10 ** digits, x)


FUNCTIONS = {"ROUNDUP": roundup, "ROUNDDOWN": rounddown, "MAX": max, "MIN": min,
             "IF": lambda flag, yes, no: yes if flag else no}
COMPILED = {mode: [(name, compile(expr, name, "eval")) for name, expr in spec] for mode, spec in FORMULAS.items()}


def calculate(mode, inputs, *, publish=True):
    values = dict(inputs)
    check(inputs["pax"] > 0, "Группа должна быть больше нуля")
    if mode != "TICKET":
        check(0 < inputs["net_revenue_pct"] <= 100 and 0 <= inputs["target_margin_pct"] < 100,
              "Недопустимый знаменатель или маржа")
    if mode == "BLOCK":
        check(inputs["quota_seats"] > 0, "Квота должна быть больше нуля")
    for key, expression in COMPILED[mode]:
        result = eval(expression, {"__builtins__": {}}, FUNCTIONS | values)
        check(math.isfinite(result), key)
        values[key] = result
    return {key: (int(values[key]) if key.endswith(("_pass", "_fit"))
                  else round_excel(values[key], 2) if publish else values[key]) for key, _ in COMPILED[mode]}


def round_trip(mode, outbound, inbound, margin_pct):
    keys = CYCLE_OUTPUTS[mode]
    raw = {key: outbound[key] + inbound[key] for key in keys}
    result = {key: round_excel(value, 2) for key, value in raw.items()}
    # Derive the cycle threshold from independently priced, unrounded legs.
    if mode == "CHARTER":
        result["rw_doc_max_rub_per_block_h"] = round_excel(
            (raw["rw_net_revenue_rub"] * (1 - margin_pct / 100) - raw["rw_flight_non_doc_cost_rub"])
            / raw["rw_billable_block_h"], 2
        )
    return result


# base, minimum, maximum, step
PARAMS = {
    "pax": ("Летящие пассажиры на плече", "pax", SCEN, 30, 1, 180, 1),
    "aircraft_seats": ("Номинальная кресельная ёмкость одного ВС", "seat", RW, 100, 80, 210, 1),
    "aircraft_count": ("Число ВС на одно направленное окно", "aircraft", SCEN, 1, 1, 2, 1),
    "effective_sellable_limit_per_aircraft": ("Предел мест к продаже по ограничениям загрузки", "seat", RW, 210, 50, 210, 1),
    "payload_seat_haircut_pct": ("Сценарное уменьшение пассажирской ёмкости из-за нагрузки", "%", RW, 0, 0, 25, 5),
    "j_seats_per_aircraft": ("Подтверждаемые кресла настоящего J на одном борту", "seat", RW, 0, 0, 24, 1),
    "j_share_pct": ("Сценарная доля пассажиров группы с запросом J", "%", SCEN, 0, 0, 15, 1),
    "j_required": ("Политика клиента требует полноценный J", "0/1", SCEN, 0, 0, 1, 1),
    "euro_seats_per_j": ("Соседних кресел Y блокируется на одного пассажира с запросом J", "seat/J pax", SCEN, 0, 0, 1, 1),
    "split_allowed": ("Клиент допустил разбивку группы в данном сценарии", "0/1", SCEN, 0, 0, 1, 1),
    "bag_rub": ("Багаж и экипировка в предложенном сценарии на пассажира", "RUB/pax", SCEN, 1200, 0, 5500, 100),
    "transfer_rub": ("Доплечья по воздуху и земле на пассажира", "RUB/pax", SCEN, 2300, 500, 10000, 100),
    "overnight_rub": ("Запланированная ночёвка на пассажира", "RUB/pax", SCEN, 0, 0, 14000, 500),
    "disruption_probability_pct": ("Сценарная вероятность нарушения окна", "%", SCEN, 8, 0, 30, 1),
    "disruption_cash_rub": ("Допрасход на пассажира при нарушении окна", "RUB/pax", SCEN, 7500, 1000, 30000, 500),
    "disruption_work_h": ("Дополнительные рабочие часы при сбое", "h/pax", SCEN, 5, 0, 24, 1),
    "alt_fare_rub": ("Билет сравниваемой альтернативы на пассажира", "RUB/pax", SCEN, 10000, 1500, 50000, 500),
    "alt_bag_rub": ("Багаж альтернативы на пассажира", "RUB/pax", SCEN, 1000, 0, 5500, 100),
    "alt_transfer_rub": ("Доплечья альтернативы на пассажира", "RUB/pax", SCEN, 2200, 500, 10000, 100),
    "alt_overnight_rub": ("Плановая ночёвка альтернативы на пассажира", "RUB/pax", SCEN, 0, 0, 14000, 500),
    "alt_disruption_probability_pct": ("Вероятность сбоя альтернативы", "%", SCEN, 10, 0, 30, 1),
    "alt_disruption_cash_rub": ("Допрасход альтернативы при сбое", "RUB/pax", SCEN, 8500, 1000, 30000, 500),
    "alt_disruption_work_h": ("Рабочие часы при сбое альтернативы", "h/pax", SCEN, 6, 0, 24, 1),
    "block_h": ("Оценка блок-времени прямого плеча", "h", SCEN, 1.5, 0.5, 11, 0.1),
    "access_buffer_h": ("Доплечья и время до отправления", "h", SCEN, 2.5, 0.5, 10, 0.25),
    "destination_transfer_h": ("Отдельно учтённый трансфер до города", "h", SCEN, 0, 0, 4, 0.25),
    "alt_duration_h": ("Время в движении альтернативы", "h", SCEN, 4.5, 0.5, 55, 0.25),
    "alt_access_buffer_h": ("Доплечья и время до отправления альтернативы", "h", SCEN, 2.5, 0.5, 10, 0.25),
    "work_overlap_pct": ("Доля времени в пути, вытесняющая рабочие часы", "%", SCEN, 55, 0, 100, 5),
    "alt_work_overlap_pct": ("Доля времени альтернативы, вытесняющая рабочие часы", "%", SCEN, 55, 0, 100, 5),
    "loaded_hour_rub": ("Полная стоимость рабочего часа", "RUB/h", SCEN, 1550, 500, 4500, 100),
    "offered_price_rub": ("Сценарная цена клиенту за Y-кресло или долю чартера", "RUB/paid seat", SCEN, 12500, 3500, 50000, 500),
    "j_fare_premium_pct": ("Надбавка к цене для пассажира с запросом J", "%", SCEN, 0, 0, 200, 5),
    "net_revenue_pct": ("Доля цены, поступающая RW после налоговых и канальных удержаний", "%", RW, 95, 85, 100, 1),
    "target_margin_pct": ("Целевой вклад в долях чистой выручки RW", "%", RW, 12, 0, 25, 1),
    "ferry_factor": ("Дополнительные перегонные блок-часы и эквивалент циклов к коммерческим", "ratio", RW, 0, 0, 0.5, 0.05),
    "fixed_per_departure_rub": ("Распределённые постоянные затраты и резерв на цикл", "RUB/cycle", RW, 105000, 50000, 270000, 5000),
    "airport_per_departure_rub": ("Базовые аэропортовые расходы сверх DOC на цикл", "RUB/cycle", RW, 125000, 50000, 280000, 5000),
    "parking_icing_pct": ("Надбавка стоянки, продления регламента и ПОО к базе аэропортовых расходов", "%", RW, 0, 0, 65, 5),
    "doc_per_block_h_rub": ("Переменные расходы блок-часа: топливо, ТО, экипаж, навигация", "RUB/h", RW, 255000, 170000, 580000, 5000),
    "quota_seats": ("Резервируемая квота на данном рейсе", "seat", RW, 30, 15, 100, 1),
    "minimum_take_pct": ("Минимальный гарантированный выкуп квоты", "%", RW, 85, 65, 100, 5),
    "release_spoilage_pct": ("Доля возвращённых мест, высвобожденных слишком поздно для перепродажи", "%", RW, 10, 0, 85, 5),
    "displacement_lf_pct": ("Вероятность вытеснения обычной продажи для удержанного места", "%", RW, 55, 15, 98, 5),
    "market_net_yield_rub": ("Чистый упущенный вклад обычной продажи места после её переменных затрат", "RUB/seat", RW, 11000, 4500, 30000, 500),
    "j_displacement_lf_pct": ("Вероятность вытеснения обычной продажи для занятого J-места", "%", RW, 40, 5, 95, 5),
    "market_j_net_yield_rub": ("Чистый упущенный вклад обычной продажи J после её переменных затрат", "RUB/seat", RW, 21000, 7500, 52000, 500),
    "marginal_service_per_pax_rub": ("Дополнительное обслуживание пассажира блока", "RUB/pax", RW, 700, 100, 2600, 100),
    "block_admin_rub": ("Поддержка и оформление блока на одно плечо", "RUB/leg", RW, 12000, 2000, 50000, 1000),
}
BLOCK_ONLY = {"quota_seats", "minimum_take_pct", "release_spoilage_pct", "displacement_lf_pct",
              "market_net_yield_rub", "j_displacement_lf_pct", "market_j_net_yield_rub",
              "marginal_service_per_pax_rub", "block_admin_rub"}
CHARTER_ONLY = {"ferry_factor", "fixed_per_departure_rub", "airport_per_departure_rub",
                "parking_icing_pct", "doc_per_block_h_rub"}
FLEET_AND_CONTRACT = {
    "aircraft_seats", "aircraft_count", "effective_sellable_limit_per_aircraft", "payload_seat_haircut_pct",
    "j_seats_per_aircraft", "j_required", "euro_seats_per_j", "split_allowed", "net_revenue_pct", "target_margin_pct",
}
MODE_EXCLUDED = {"CHARTER": BLOCK_ONLY, "BLOCK": CHARTER_ONLY,
                 "TICKET": CHARTER_ONLY | BLOCK_ONLY | FLEET_AND_CONTRACT}


class Registry:
    def __init__(self, evidence):
        self.params = {}
        self.evidence = evidence

    def add(self, key, label, unit, tag, value, minimum, maximum, step, evidence=(), **extra):
        check(set(evidence) <= self.evidence.keys() and key not in self.params, key)
        check(minimum <= value <= maximum and step >= 0 and all(map(math.isfinite, (value, minimum, maximum, step))), key)
        self.params[key] = dict(
            param_id=key, label_ru=label, unit=unit, base_value=value,
            min_value=minimum, max_value=maximum, step=step, source_tag=tag, evidence_ids=list(evidence),
            excel_cell_hint=f"'Параметры'!D{len(self.params) + 2}", **extra,
        )
        return key

    def bind(self, scope, mode, override):
        active = PARAMS.keys() - MODE_EXCLUDED[mode]
        check(override.keys() <= active, f"{scope}: {override.keys() - active}")
        values, binding = {}, {}
        for name, (label, unit, tag, default, lo, hi, step) in PARAMS.items():
            if name not in active:
                continue
            value = override.get(name, default)
            if isinstance(value, str):
                param_id = value
                value = self.params[param_id]["base_value"]
            elif value == default:
                param_id = name
                if param_id not in self.params:
                    self.add(param_id, label, unit, tag, value, lo, hi, step)
            else:
                param_id = f"{scope}.{name}"
                self.add(param_id, label, unit, tag, value, min(value, lo), max(value, hi), step)
            values[name] = value
            binding[name] = param_id
        return values, binding


def make_observations(reg, tables):
    supply = {s["supply_id"]: s for s in tables["supply_gap_pairs"]}
    notes = (W2 / "raw/w2_t2_demand_notes.md").read_text(encoding="utf-8")
    for expected in ("в пути 18 ч", "3 827 ₽", "7 626 ₽", "049М"):
        check(expected in notes, expected)
    history = (ROOT.parent / "46_corporate_pilot_ufa_nux.md").read_text(encoding="utf-8")
    for expected in ("РН40302710", "150 мест", "700 кг", "10 ч"):
        check(expected in history, expected)
    for supply_id, fare, source_id in (
        ("W2T1-SUP-001", 13994, "EV-W2T1-012"),
        ("W2T1-SUP-016", 4133, "EV-W2T1-020"),
        ("W2T1-SUP-009", 18200, "EV-W2T1-015"),
        ("W2T1-SUP-013", 15000, "EV-W2T1-018"),
    ):
        source = supply[supply_id]
        check(float(source["fare_rub"]) == fare and source_id in ids(source["evidence_ids"]), supply_id)
    check("2733 мин" in supply["W2T1-SUP-016"]["fare_terms"] and
          supply["W2T1-SUP-009"]["service_no_1"] == "YC846" and
          supply["W2T1-SUP-010"]["service_no_1"] == "YC845", "Контрольные рейсы и поезд")

    def fixed(key, label, unit, value, evidence, note, tag=OBS):
        reg.add(key, label, unit, tag, value, value, value, 0, evidence, note_ru=note)

    fixed("ufa_nux_air_from", "UFA → NUX, ориентир авиабилета от", "RUB/pax", 13994, ["EV-W2T1-012"],
          "Срез W2T1-SUP-001. Цена на группу, рейс и багаж подлежит проверке.")
    fixed("ufa_nux_rail_from", "Уфа → Новый Уренгой, плацкарт от", "RUB/pax", 4133, ["EV-W2T1-020"],
          "Срез W2T1-SUP-016. Тариф на дату и доступность не установлены.")
    fixed("ufa_nux_rail_h", "Уфа → Новый Уренгой, время поезда", "h", 2733 / 60, ["EV-W2T1-020"],
          "45 ч 33 мин между вокзалами. Наблюдение не распространяется на обратное направление.")
    fixed("dimitrovgrad_049m_rail_h", "Димитровград → Москва, поезд 049М", "h", 18, ["EV-W2T2-039"],
          "Обратное направление, 18:15 → 11:15 местного времени. Сверено с W2T2 notes. "
          "EV-W2T2-017 описывает отдельную выдачу с пересадками.")
    fixed("uly_dimitrovgrad_access_h", "ULY → Димитровград, такси до города", "h", 100 / 60, ["EV-W2T2-015"],
          "100 мин до города. Условия подъезда к объекту и обратное время подлежат проверке.")
    fixed("svx_ufa_air_from", "SVX ↔ UFA, эконом от", "RUB/pax", 3827, ["EV-W2T2-022", "EV-W2T2-023"],
          "Срез страницы в raw/w2_t2_demand_notes.md. Нижняя публичная цена на маршрут, рейс и место не гарантированы.")
    fixed("svx_kzn_air_from", "SVX ↔ KZN, эконом от", "RUB/pax", 7626, ["EV-W2T2-024", "EV-W2T2-025"],
          "Срез страницы в raw/w2_t2_demand_notes.md. Нижняя публичная цена на маршрут, рейс и место не гарантированы.")
    fixed("led_nux_air_sample", "LED → NUX, авиабилет в срезе", "RUB/pax", 18200, ["EV-W2T1-015"],
          "W2T1-SUP-009, YC846 на 25.11.2026. Цена обратного YC845 неизвестна.")
    fixed("ikt_mjz_air_sample", "IKT → MJZ, авиабилет в срезе", "RUB/pax", 15000, ["EV-W2T1-018"],
          "W2T1-SUP-013. Публичная цена в одном направлении.")
    for key, label, supply_id, evidence_id in (
        ("ufa_nux_yc188_h", "UFA → NUX, расписание YC188", "W2T1-SUP-001", "EV-W2T1-012"),
        ("led_nux_yc846_h", "LED → NUX, расписание YC846", "W2T1-SUP-009", "EV-W2T1-015"),
        ("nux_led_yc845_h", "NUX → LED, расписание YC845", "W2T1-SUP-010", "EV-W2T1-011"),
        ("ikt_mjz_io9587_h", "IKT → MJZ, расписание IO9587", "W2T1-SUP-013", "EV-W2T1-018"),
        ("mjz_ikt_6r571_h", "MJZ → IKT, расписание 6R571", "W2T1-SUP-015", "EV-W2T1-019"),
        ("kja_vvo_fv5751_h", "KJA → VVO, расписание FV5751", "W2T3-SUP-008", "EV-W2T3-018"),
        ("vvo_kja_fv5752_h", "VVO → KJA, расписание FV5752", "W2T3-SUP-009", "EV-W2T3-019"),
        ("kcy_aba_ek101_h", "KCY → ABA, расписание ЭК101", "W2T3-SUP-003", "EV-W2T3-014"),
        ("aba_kcy_ek102_h", "ABA → KCY, расписание ЭК102", "W2T3-SUP-004", "EV-W2T3-014"),
    ):
        source = supply[supply_id]
        hours = (datetime.fromisoformat(source["arr_at_1"]) -
                 datetime.fromisoformat(source["dep_at_1"])).total_seconds() / 3600
        check(evidence_id in ids(source["evidence_ids"]), supply_id)
        fixed(key, label, "h", hours, [evidence_id],
              f"{supply_id}, время между опубликованными временами вылета и прилёта с учётом UTC.")
    fixed("j_aeroclub_share_pct", "Доля J в выборке Аэроклуба за I кв. 2025", "%", 4, ["EV-W14-09"],
          "Рыночный ориентир ограничен клиентами ТМС. Доля целевой когорты неизвестна.")
    fixed("vankor_rfi_min_seats", "РН-Ванкор, историческое требование к одному ВС", "seat/aircraft", 150, ["EV-W13-001"],
          "РН40302710. Ранее сверенные версии ТЗ, актуальная группа неизвестна.", HIST)
    fixed("vankor_rfi_min_extra_baggage", "РН-Ванкор, исторический багаж / груз на рейс", "kg/leg", 700, ["EV-W13-001"],
          "Физическая единица из ранее сверенной версии ТЗ, проверка нагрузки с багажом обязательна.", HIST)
    fixed("vankor_rfi_min_excess_parking", "РН-Ванкор, сверхнормативная стоянка в НУР", "h", 10, ["EV-W13-001"],
          "Нижний предел исторического ТЗ. Затраты на стоянку и ПОО необходимо подтвердить.", HIST)


AIRCRAFT = {
    SSJ: {"aircraft_seats": 100, "j_seats_per_aircraft": 0, "doc_per_block_h_rub": 255000,
          "fixed_per_departure_rub": 105000, "airport_per_departure_rub": 125000},
    SJ: {"aircraft_seats": 100, "j_seats_per_aircraft": 12, "doc_per_block_h_rub": 285000,
         "fixed_per_departure_rub": 122000, "airport_per_departure_rub": 140000},
    TU: {"aircraft_seats": 164, "j_seats_per_aircraft": 16, "doc_per_block_h_rub": 395000,
         "fixed_per_departure_rub": 155000, "airport_per_departure_rub": 190000},
}


def variant(variant_id, mode, pair, aircraft, common=None, outbound=None, inbound=None, **details):
    return dict(variant_id=variant_id, mode=mode, airport_pair=pair, aircraft_type=aircraft,
                common=common or {}, outbound=outbound or {}, inbound=inbound or {}, **details)


def case(case_id, cluster_id, title, beneficiary, evidence_ids, variants, **details):
    return dict(case_id=case_id, scenario_id=case_id, cluster_id=cluster_id, title_ru=title,
                beneficiary_ru=beneficiary, evidence_ids=evidence_ids, variants=variants,
                decision="Conditional", demand_basis="STRUCTURAL_HYPOTHESIS",
                confirmed_pax=None, payer_org_id=None, **details)


def build_cases(reg, matrix, future):
    fleet = {(r["from_iata"], r["to_iata"]): r for r in matrix}
    p1_market = ["EV-W2T1-012", "EV-W2T1-020"]
    rail_ufa = dict(alt_bag_rub=500, alt_transfer_rub=3200,
                    alt_work_overlap_pct=45, alt_access_buffer_h=2)
    rail_ufa_out = dict(alt_fare_rub="ufa_nux_rail_from", alt_duration_h="ufa_nux_rail_h")
    rail_ufa_back = dict(alt_fare_rub=5000, alt_duration_h=46)
    p1a = variant("TU214_CHARTER", "CHARTER", "UFA-NUX", TU,
                  rail_ufa | dict(pax="vankor_rfi_min_seats", bag_rub=0, offered_price_rub=13500,
                                  work_overlap_pct=65, access_buffer_h=4),
                  rail_ufa_out | dict(parking_icing_pct=25, transfer_rub=4700),
                  rail_ufa_back | dict(offered_price_rub=13000, transfer_rub=4200),
                  contract_requirements={"extra_baggage_param_id": "vankor_rfi_min_extra_baggage",
                                         "parking_param_id": "vankor_rfi_min_excess_parking",
                                         "one_aircraft": True, "regulation_extension_required": True},
                  condition_ru="700 кг и 150 человек на одном борту требуют совместной проверки загрузки. "
                               "25% к базовым аэропортовым расходам применяется один раз в НУР за оборот.")
    p1b = variant("BLOCK_30", "BLOCK", "UFA-NUX", SSJ,
                  rail_ufa | dict(quota_seats=30, minimum_take_pct=100, offered_price_rub=13000,
                                  access_buffer_h=4),
                  rail_ufa_out | dict(pax=30, transfer_rub=4700, displacement_lf_pct=55),
                  rail_ufa_back | dict(pax=26, offered_price_rub=12000, transfer_rub=4200, displacement_lf_pct=45),
                  condition_ru="Отдельная малая группа. Публичный рейс Ямала не удостоверяет рейс, квоту или блок RW.")
    p1b_public = variant("PUBLIC_FARE_VS_RAIL", "TICKET", "UFA-NUX", SSJ,
                         rail_ufa | dict(access_buffer_h=4),
                         rail_ufa_out | dict(pax=30, offered_price_rub="ufa_nux_air_from", transfer_rub=4700,
                                             block_h="ufa_nux_yc188_h"),
                         rail_ufa_back | dict(pax=30, offered_price_rub=15000, transfer_rub=4200),
                         condition_ru="Публичная цена для клиентского сравнения. Цена возвращения сценарная. "
                                      "Цена учитывается за каждого летящего пассажира.")
    p1c = variant("TWO_SSJ_SPLIT_YES", "CHARTER", "UFA-NUX", SSJ,
                  rail_ufa | dict(pax=150, aircraft_count=2, split_allowed=1,
                                  offered_price_rub=13500, bag_rub=0, access_buffer_h=5, work_overlap_pct=65),
                  rail_ufa_out | dict(parking_icing_pct=25, transfer_rub=5500),
                  rail_ufa_back | dict(offered_price_rub=13000, transfer_rub=5000),
                  condition_ru="75 пассажиров на борт при симметричном разделении каждого направления. "
                               "Нужны письменное разрешение клиента и два окна передачи на вертолёт "
                               "или одно окно с подтверждённой ёмкостью для обеих групп.")
    p1c_nosplit = p1c | {"variant_id": "TWO_SSJ_SPLIT_NO", "common": p1c["common"] | {"split_allowed": 0},
                         "condition_ru": "Дробление запрещено. Расчёт сравнивает стоимость, но состав ВС не проходит условие."}

    p2a_variants = []
    for to, transfer_out, transfer_back in (("ULY", 1950, 2100), ("ULV", 2250, 2450), ("KUF", 3400, 3500)):
        access_out, access_back = ({"ULY": (1.8, 3.75), "ULV": (3.9, 4.05),
                                    "KUF": (4.65, 4.85)})[to]
        details = {"evidence_ids": ["EV-W2T2-015"]} if to == "ULY" else {}
        p2a_variants.append(variant(f"SVO_{to}_BLOCK_20", "BLOCK", f"SVO-{to}", SSJ,
            dict(quota_seats=20, offered_price_rub=9500, alt_bag_rub=300, alt_transfer_rub=1700,
                 alt_access_buffer_h=1.65, alt_work_overlap_pct=32, work_overlap_pct=48),
            dict(pax=20, transfer_rub=transfer_out, access_buffer_h=access_out, alt_duration_h=18, alt_fare_rub=6000,
                 destination_transfer_h="uly_dimitrovgrad_access_h" if to == "ULY" else 0),
            dict(pax=17, transfer_rub=transfer_back, access_buffer_h=access_back, alt_duration_h="dimitrovgrad_049m_rail_h",
                 offered_price_rub=8700, alt_fare_rub=6500, displacement_lf_pct=50),
            market_tariff_status=f"{SCEN} / {RW}",
            condition_ru=("ULY: 100 мин до города плюс 108 мин на доступ/буфер в SVO. "
                          "Путь от города до проходной уточняется. " if to == "ULY" else
                          "Время доплечья от аэропорта сценарное. ") +
                         "18 ч наблюдались на обратном 049М. Прямой ночной поезд туда и тарифы проверяются на дату.",
            **details))

    p2b_variants = []
    for to, alt, ask, access in (("UFA", "svx_ufa_air_from", 6300, 3.7),
                                 ("KZN", "svx_kzn_air_from", 8500, 3.9), ("ULY", 9500, 9200, 4.2)):
        for j_share in ("j_aeroclub_share_pct", 10, 15):
            pct = reg.params[j_share]["base_value"] if isinstance(j_share, str) else j_share
            for plane, code, euro, premium in ((SSJ, "EURO_100Y", 1, 35), (SJ, "SJ100_J", 0, 80), (TU, "TU214_J", 0, 80)):
                p2b_variants.append(variant(f"SVX_{to}_{code}_J{pct}", "BLOCK", f"SVX-{to}", plane,
                    dict(quota_seats=40, minimum_take_pct=95, j_share_pct=j_share,
                         euro_seats_per_j=euro, j_fare_premium_pct=premium, access_buffer_h=access,
                         alt_access_buffer_h=access, offered_price_rub=ask, alt_fare_rub=alt,
                         market_net_yield_rub=6500 if to == "UFA" else 9000),
                    dict(pax=40, displacement_lf_pct=62),
                    dict(pax=36, displacement_lf_pct=53, offered_price_rub=ask - 250),
                    condition_ru="Порог 4% относится к выборке Аэроклуба. 10–15% — стресс для целевой группы. "
                                 "Политика Трансинжстроя иллюстрирует допуск по должности и не задаёт долю J. "
                                 "Евробизнес годится только для J_PREFERRED."))
    p2b_variants.append(variant("SVX_UFA_EURO_100Y_J15_REQUIRED", "BLOCK", "SVX-UFA", SSJ,
        p2b_variants[6]["common"] | {"j_required": 1},
        p2b_variants[6]["outbound"], p2b_variants[6]["inbound"],
        condition_ru="J_REQUIRED. Проверка класса отклоняет 100Y независимо от цены."))

    event = next(x for x in future if x["event_id"] == "EV27-INNOPROM")
    event_arrival = (date.fromisoformat(event["start_date"]) - timedelta(days=1)).isoformat()
    event_departure = (date.fromisoformat(event["end_date"]) + timedelta(days=1)).isoformat()
    p3a = variant("FORUM_BLOCK_30_T21", "BLOCK", "LED-SVX", SSJ,
                  dict(quota_seats=30, minimum_take_pct=80, release_spoilage_pct=35,
                       displacement_lf_pct=85, market_net_yield_rub=17200, alt_fare_rub=21200,
                       offered_price_rub=16300),
                  dict(pax=27, alt_fare_rub=22500),
                  dict(pax=23, offered_price_rub=15700, release_spoilage_pct=50, market_net_yield_rub=18000),
                  market_tariff_status=f"{SCEN} / {RW}", release_days_before=21, free_name_changes=True,
                  direction_dates={"outbound": event_arrival, "inbound": event_departure},
                  condition_ru="Запрос блока на пик форума. Даты мероприятия объявлены. Плательщики, квота, тарифы пика, "
                               "возврат мест T−21 и бесплатная замена ФИО требуют согласования.")
    p3b_variants = []
    for model_id, plane, haircut in (("SSJ_WINTER_20", SSJ, 20), ("SSJ_WINTER_15", SSJ, 15),
                                    ("SSJ_WINTER_25", SSJ, 25), ("SJ100_NO_HAIRCUT_SCENARIO", SJ, 0),
                                    ("TU214_NO_HAIRCUT_SCENARIO", TU, 0)):
        p3b_variants.append(variant(model_id, "CHARTER", "LED-NUX", plane,
            dict(payload_seat_haircut_pct=haircut, offered_price_rub=20900, access_buffer_h=4.2),
            dict(pax=80, parking_icing_pct=20, alt_fare_rub="led_nux_air_sample", alt_duration_h="led_nux_yc846_h"),
            dict(pax=76, offered_price_rub=20000, alt_fare_rub=19000, ferry_factor=0.1, alt_duration_h="nux_led_yc845_h"),
            condition_ru="Ортодромия 2 379,56 км, на 24,56 км выше ориентира 2 355 км для SSJ-95B. "
                         "Запросить массу, ветер, запасной аэродром ЯНАО и профиль. Багаж проверяется отдельно. "
                         "Для SJ-100 и Ту-214 в сценарии не применено уменьшение ёмкости, "
                         "фактическую допустимую нагрузку должен подтвердить RW."))
    c4_charter = variant("STNG_100Y_CHARTER", "CHARTER", "IKT-MJZ", SSJ,
                         dict(pax=80, offered_price_rub=14800, access_buffer_h=4.5),
                         dict(alt_fare_rub="ikt_mjz_air_sample", alt_duration_h="ikt_mjz_io9587_h", ferry_factor=0.1),
                         dict(pax=72, offered_price_rub=14300, alt_fare_rub=16000, alt_duration_h="mjz_ikt_6r571_h"),
                         condition_ru="Сценарное плечо. АП086548 указывает бенефициара СТНГ, организатора Газстройпром. "
                                      "Нужны договорный ИНН, плечи и датированные группы.")
    c4_block = variant("STNG_BLOCK_30", "BLOCK", "IKT-MJZ", SSJ,
                       dict(pax=30, quota_seats=30, offered_price_rub=12700, access_buffer_h=4.5),
                       dict(alt_fare_rub="ikt_mjz_air_sample", alt_duration_h="ikt_mjz_io9587_h", displacement_lf_pct=60),
                       dict(pax=26, offered_price_rub=12200, alt_fare_rub=16000, alt_duration_h="mjz_ikt_6r571_h"),
                       condition_ru="Отдельная малая группа; АП086346 относится к оформлению билетов через ТМС. "
                                    "Единицы ТМС не измеряют спрос на чартер.")
    c5_block = variant("TU214_2CLASS_BLOCK", "BLOCK", "KJA-VVO", TU,
                       dict(pax=24, quota_seats=25, j_share_pct=10, j_fare_premium_pct=80,
                            offered_price_rub=17800, market_net_yield_rub=17000, alt_fare_rub=19500),
                       dict(displacement_lf_pct=70, alt_duration_h="kja_vvo_fv5751_h"),
                       dict(pax=20, offered_price_rub=16600, alt_fare_rub=18000, displacement_lf_pct=60,
                            alt_duration_h="vvo_kja_fv5752_h"),
                       condition_ru="Срез FV5751/5752 доказывает наблюдаемое предложение России. "
                                    "Блок на Ту-214 условен наличием оператора и квоты. Для малой группы проверить ТМС.")
    c5_tmc = variant("TMC_ON_OBSERVED_MARKET", "TICKET", "KJA-VVO", "Наблюдаемый A319",
                     dict(pax=10, offered_price_rub=19500, alt_fare_rub=19500),
                     dict(block_h="kja_vvo_fv5751_h", alt_duration_h="kja_vvo_fv5751_h"),
                     dict(pax=8, offered_price_rub=18500, alt_fare_rub=18000, block_h="vvo_kja_fv5752_h",
                          alt_duration_h="vvo_kja_fv5752_h"),
                     condition_ru="ТМС-тариф на наблюдаемом предложении. Цена сценарная, расчёт ведётся на покупателя.")
    c5_contrast = variant("KCY_ABA_REGIONAL_MARKET", "TICKET", "KCY-ABA", "Наблюдаемый ATR42-500",
                          dict(pax=8, offered_price_rub=7000, alt_fare_rub=3500, alt_duration_h=9,
                               alt_work_overlap_pct=40),
                          dict(block_h="kcy_aba_ek101_h"), dict(block_h="aba_kcy_ek102_h"),
                          condition_ru="Контраст короткого плеча через KCY. Автобус до Саяногорска около 9 ч до доплечий. "
                                       "Цены, адреса и окна сценарные.")

    return [
        case("P1A_VANKOR_CHARTER_164", "P1", "Исторический стресс-тест РН40302710", "РН-Ванкор",
             ["EV-W13-001", *p1_market], [p1a], historical_reference="РН40302710",
             historical_flights_literal="80 рейсов за шесть месяцев с подписания. Единица рейса сохранена."),
        case("P1B_UFA_NUX_BLOCK_30", "P1", "Малая группа на существующем предложении", "Требует отдельного подтверждения",
             p1_market, [p1b, p1b_public], excluded_as_demand_evidence=[
                 {"evidence_id": "EV-W13-003", "beneficiary_ru": "Севернефтегазпром", "procurement_ref": "32616450256",
                  "note_ru": "Отдельная закупка билетов. Связь с авиационным плечом и квотой не установлена."}]),
        case("P1C_UFA_NUX_2X_SSJ100", "P1", "Два SSJ100 при разбивке группы", "РН-Ванкор",
             ["EV-W13-001", *p1_market], [p1c, p1c_nosplit], split_allowed="YES_ONLY_IF_CUSTOMER_CONFIRMS"),
        case("P2A_ATOM_DIMITROVGRAD_BLOCK", "P2", "Блок для инженеров в Димитровград", "Атомтехэнерго",
             ["EV-W2T2-001", "EV-W2T2-002", "EV-W2T2-015", "EV-W2T2-017", "EV-W2T2-039"], p2a_variants, beneficiary_org_id="RU-INN-5029106714"),
        case("P2B_ROSTEC_SVX_COOP_JCLASS", "P2", "Кооперация ОДК / ВСМПО и бизнес-класс", "ОДК / ВСМПО-АВИСМА",
             ["EV-W2T2-010", "EV-W2T2-022", "EV-W2T2-023", "EV-W2T2-024", "EV-W2T2-025",
              "EV-W2T2-036", "EV-W14-09", "EV-W2T4-009"],
             p2b_variants),
        case("P3A_INNOPROM_LED_SVX_BLOCK", "P3", "Событийный блок ИННОПРОМ-2027", "Делегации, плательщики уточняются",
             [*ids(event["evidence_ids"]), "EV-W2T4-057", "EV-W2T4-058"], [p3a], event_id=event["event_id"], event_start=event["start_date"],
             event_end=event["end_date"]),
        case("P3B_GPN_LED_NUX_LONGHAUL", "P3", "Зимний профиль LED ↔ NUX", "Газпромнефть-Снабжение",
             ["EV-W2T1-004", "EV-W2T1-005", "EV-W2T1-015", "EV-W2T1-011"], p3b_variants,
             project_from_year=2027, project_to_year=2029, observed_flights=["YC846", "YC845"]),
        case("C4_STNG_EPC_IKT_MJZ", "C4", "СТНГ: проектный чартер и блок", "СТНГ",
             ["EV-W2T1-001", "EV-W2T1-002", "EV-W2T1-003", "EV-W2T1-018", "EV-W2T1-019"],
             [c4_charter, c4_block], procurement_dedup_key=["АП086548", "7714572888"], separate_tmc_ref="АП086346"),
        case("C5_RUSHYDRO_KJA_VVO", "C5", "РусГидро: блок KJA ↔ VVO и короткое плечо", "РусГидро",
             ["EV-W11-017", "EV-W2T3-012", "EV-W2T3-013", "EV-W2T3-014", "EV-W2T3-018", "EV-W2T3-019"], [c5_block, c5_tmc, c5_contrast]),
    ], fleet


def sensitivity(reg, mode, inputs, binding):
    x, y = (
        ("doc_per_block_h_rub", "ferry_factor") if mode == "CHARTER"
        else ("displacement_lf_pct", "release_spoilage_pct")
    )
    fields = ["rw_break_even_seat_price_rub", "rw_net_contribution_rub"]
    if mode == "CHARTER":
        fields.extend(["rw_break_even_charter_price_rub", "rw_doc_max_rub_per_block_h"])
    table = []
    for x_scenario in ("min", "base", "max"):
        for y_scenario in ("min", "base", "max"):
            x_value = reg.params[binding[x]][f"{x_scenario}_value"]
            y_value = reg.params[binding[y]][f"{y_scenario}_value"]
            output = calculate(mode, inputs | {x: x_value, y: y_value})
            table.append({
                "x_scenario": x_scenario.upper(), "y_scenario": y_scenario.upper(),
                "x": x_value, "y": y_value, "expected_outputs": {f: output[f] for f in fields},
            })
    return {"x_param": x, "y_param": y, "rows": table}


def publish(x):
    return {k: round_excel(v, 2) if isinstance(v, float) else v for k, v in x.items()}


def evaluate_cases(cases, reg, fleet):
    for case_row in cases:
        case_id = case_row["case_id"]
        check(set(case_row["evidence_ids"]) <= reg.evidence.keys(), case_id)
        for index, setup in enumerate(case_row["variants"]):
            mode, pair, plane = setup["mode"], setup["airport_pair"], setup["aircraft_type"]
            a, b = pair.split("-")
            matrix = fleet[tuple(sorted((a, b)))]
            block_id = f"{matrix['airport_pair']}.est_block_time_h"
            if block_id not in reg.params:
                h = matrix["est_block_time_h"]
                reg.add(block_id, PARAMS["block_h"][0], "h", SCEN, h, h, h, 0,
                        ["EV-W2S1-001"], estimate_tag="MODEL_ESTIMATE")
            aircraft = {key: value for key, value in AIRCRAFT.get(plane, {}).items()
                        if key not in MODE_EXCLUDED[mode]}
            common = aircraft | {"block_h": block_id} | setup.pop("common")
            setup.update(gc_distance_km=matrix["gc_distance_km"], route_distance_km_k110=matrix["route_distance_km_k110"])
            inputs, parameter_ids, output, linked_evidence = {}, {}, {}, {}
            raw = {}
            for name, origin, dest in (("outbound", a, b), ("inbound", b, a)):
                tag = f"{case_id}.{setup['variant_id']}.{name}"
                inputs[name], parameter_ids[name] = reg.bind(tag, mode, common | setup.pop(name))
                linked_evidence[name] = sorted(set(case_row["evidence_ids"]) | set(setup.get("evidence_ids", [])) |
                    {source_id for param_id in parameter_ids[name].values() for source_id in reg.params[param_id]["evidence_ids"]})
                raw[name] = calculate(mode, inputs[name], publish=False)
                output[name] = publish(raw[name])
                if index == 0:
                    setup.setdefault("sensitivity", {})[name] = sensitivity(reg, mode, inputs[name], parameter_ids[name])
            margin = inputs["outbound"].get("target_margin_pct")
            check(margin == inputs["inbound"].get("target_margin_pct"), f"{case_id}: Маржа оборота")
            output["round_trip"] = round_trip(mode, raw["outbound"], raw["inbound"], margin)
            setup.update(
                direction_labels={"outbound": f"{a}-{b}", "inbound": f"{b}-{a}"},
                inputs=inputs, input_param_ids=parameter_ids, expected_outputs=output,
                evidence_ids=sorted(set(linked_evidence["outbound"]) | set(linked_evidence["inbound"])),
                evidence_ids_by_direction=linked_evidence,
            )
        default = case_row["variants"][0]
        for key in ("mode", "airport_pair", "aircraft_type", "direction_labels", "inputs", "input_param_ids",
                    "expected_outputs", "sensitivity", "gc_distance_km"):
            case_row[key] = default[key]
        case_row["default_variant_id"] = default["variant_id"]
        case_row["evidence_ids"] = sorted(set(case_row["evidence_ids"]) |
                                         {ev for spec in case_row["variants"] for ev in spec["evidence_ids"]})

    one_board, two_boards = cases[0], cases[2]
    delta = {d: round_excel(two_boards["expected_outputs"][d]["rw_break_even_seat_price_rub"] -
                            one_board["expected_outputs"][d]["rw_break_even_seat_price_rub"], 2)
             for d in ("outbound", "inbound")}
    check(all(v > 0 for v in delta.values()), "Два SSJ дороже в историческом стресс-сценарии")
    two_boards["comparison_vs_p1a_break_even_delta_rub_per_pax"] = delta

    check(len(cases) == 9 and len({c["cluster_id"] for c in cases}) == 5, "P5_FLEET_ECON")
    check(all(c["confirmed_pax"] is None and c["decision"] == "Conditional" for c in cases), "Статус пилота")
    check(all("EV-W13-003" not in c["evidence_ids"] for c in cases), "Заявки Уфа–Новый Уренгой")
    check(cases[2]["variants"][1]["expected_outputs"]["outbound"]["operational_screen_pass"] == 0,
          "Дробление запрещено")
    check(cases[4]["variants"][-1]["expected_outputs"]["outbound"]["j_policy_fit"] == 0, "Настоящий J")
    check(cases[6]["variants"][2]["expected_outputs"]["outbound"]["capacity_fit"] == 0, "Зима 25%")
    return cases


def fleet_capacity(reg, matrix, go_count):
    for key, label, unit, tag, base, lo, hi, step in (
        ("fleet_weekly_available_block_h", "Доступные блок-часы на активное ВС за неделю", "h/aircraft/week", RW, 44, 30, 60, 1),
        ("fleet_reserve_pct", "Доля резервных ВС от парка с резервом", "%", RW, 17.5, 15, 20, 0.5),
        ("fleet_charter_rotations_per_week", "Чартерные обороты на программу в неделю", "round trips/week", SCEN, 1, 1, 4, 1),
        ("fleet_regular_rotations_per_week", "Регулярные обороты на программу в неделю", "round trips/week", SCEN, 4, 1, 7, 1),
        ("fleet_ground_times_h", "Оценка наземного времени на оборот", "h/round trip", SCEN, 2, 1, 16, 0.25),
        ("fleet_weekly_aircraft_occupancy_h", "Доступные часы занятости борта с наземным временем", "h/aircraft/week", RW, 60, 40, 100, 1),
    ):
        reg.add(key, label, unit, tag, base, lo, hi, step)
    rows = []
    fleets = ((SSJ, "IKT-MJZ"), (SJ, "LED-NUX"), (TU, "NUX-UFA"))
    distance_rows = {r["airport_pair"]: r for r in matrix}
    for n in (0, 1, 3, 5):
        for plane, route in fleets:
            for product, rotation_key in (("BLOCK", None), ("CHARTER", "fleet_charter_rotations_per_week"),
                                          ("REGULAR_ROTATION", "fleet_regular_rotations_per_week")):
                rotations = reg.params[rotation_key]["base_value"] if rotation_key else 0
                block_h = distance_rows[route]["est_block_time_h"]
                ground_h = reg.params["fleet_ground_times_h"]["base_value"]
                if plane == TU:
                    ground_h = reg.params["vankor_rfi_min_excess_parking"]["base_value"] + ground_h
                hours = n * rotations * 2 * block_h
                occupied_h = n * rotations * (2 * block_h + ground_h)
                # Base assumes compatible staggered windows. The coincident case exposes the peak.
                for window_plan, peaks in (("STAGGERED", min(1, n)), ("COINCIDENT", n)):
                    concurrency = peaks if rotations else 0
                    active = max(concurrency, math.ceil(hours / reg.params["fleet_weekly_available_block_h"]["base_value"]),
                                 math.ceil(occupied_h / reg.params["fleet_weekly_aircraft_occupancy_h"]["base_value"]))
                    reserve15, reserve20 = (math.ceil(active / (1 - pct / 100)) for pct in (15, 20))
                    rows.append({
                        "programs_confirmed_assumption": n, "aircraft_type": plane, "example_airport_pair": route,
                        "nominal_seats_per_aircraft": AIRCRAFT[plane]["aircraft_seats"], "product": product,
                        "rotations_per_program_per_week": rotations, "window_plan": window_plan,
                        "weekly_block_h": round_excel(hours, 2), "weekly_aircraft_occupied_h": round_excel(occupied_h, 2),
                        "max_simultaneous_aircraft": concurrency, "active_aircraft": active,
                        "fleet_with_reserve_base": math.ceil(active / (1 - reg.params["fleet_reserve_pct"]["base_value"] / 100)),
                        "fleet_with_reserve_15_pct": reserve15, "fleet_with_reserve_20_pct": reserve20,
                        "reserve_pool_equivalent_aircraft_at_15_pct": round_excel(active / 0.85 - active, 2),
                        "reserve_pool_equivalent_aircraft_at_20_pct": round_excel(active / 0.80 - active, 2),
                    })
    return {
        "base_dedicated_aircraft_open_sources": go_count,
        "source_tag": SCEN, "confirmation_status": RW,
        "parameter_ids": [p for p in reg.params if p.startswith("fleet_")],
        "formula_spec": {
            "weekly_block_h": "programs * rotations_per_program_per_week * 2 * block_h",
            "weekly_aircraft_occupied_h": "programs * rotations_per_program_per_week * (2 * block_h + ground_h)",
            "max_simultaneous_aircraft": "0 для блока, MIN(1, programs) при разнесённых окнах, programs при одновременных",
            "active_aircraft": "MAX(max_simultaneous_aircraft, ROUNDUP(weekly_block_h / fleet_weekly_available_block_h, 0), ROUNDUP(weekly_aircraft_occupied_h / fleet_weekly_aircraft_occupancy_h, 0))",
            "fleet_with_reserve": "ROUNDUP(active_aircraft / (1 - reserve_pct / 100), 0)",
        },
        "interpretation_ru": "Блок использует инвентарь существующего рейса, поэтому выделенный парк равен нулю. "
                             "Ротация содержит два раздельных направленных окна. Парк суммируется по типам после подтверждения "
                             "календаря и доступности. Целый резерв предполагает выделенные ВС. Дробный эквивалент "
                             "показывает долю общего резерва после подтверждения доступности подмены.",
        "program_scenarios": rows,
    }


def read_packets(qualified):
    playbook = (W1 / "track_b_rf_adaptation_and_playbooks.md").read_text(encoding="utf-8")
    corrections = playbook.split("## Шесть поправок для РФ\n", 1)[1].split("\n## ", 1)[0]
    adaptations = []
    for line in corrections.splitlines():
        if not line.startswith("| ") or line.startswith("| Поправка"):
            continue
        title, terms = [x.strip() for x in line.strip("|").split("|")]
        adaptations.append({"title_ru": title, "terms_ru": terms, "evidence_ids": ids(terms)})
    sheets = playbook.split("## Рабочие термшиты\n", 1)[1].split("\n## ", 1)[0]
    term_sheets = []
    for term_id, title, body in re.findall(r"^### (\d)\. ([^\n]+)\n(.*?)(?=^### |\Z)", sheets, re.M | re.S):
        term_sheets.append({"term_sheet_id": f"TS{term_id}", "title_ru": title,
                            "terms_ru": [line.removeprefix("- ") for line in body.splitlines() if line.startswith("- ")],
                            "evidence_ids": ids(body)})
    check(len(adaptations) == 6 and len(term_sheets) == 5, "РФ и термшиты")

    barrier_md = (W2 / "why_not_registry_v2.md").read_text(encoding="utf-8")
    barriers = []
    section = None
    for line in barrier_md.splitlines():
        if line.startswith("## "):
            section = {"## Барьеры с положительными свидетельствами": "POSITIVE_EVIDENCE",
                       "## Другие проверенные сценарии": "CHECKED_SCENARIO"}.get(line)
        if section and line.startswith("| ") and not line.startswith(("| Организация,", "| Сценарий |")):
            scenario, observation, *condition = (x.strip() for x in line.strip("|").split("|"))
            text = observation + " " + " ".join(condition)
            barriers.append({
                "section": section, "scenario_ru": scenario.replace("**", ""), "observation_ru": observation,
                "decision_condition_ru": condition[0] if condition else None,
                "evidence_ids": ids(text), "formal_no_go": False,
                "rule_ids": sorted(set(re.findall(r"\bK[1-7]\b", text))),
            })
    check(Counter(b["section"] for b in barriers) == {"POSITIVE_EVIDENCE": 7, "CHECKED_SCENARIO": 13},
          "Покрытие реестра барьеров")
    prior_rules = {
        "K1": "Минимум два прямых рейса в день с местами для группы в нужном аэропорту, классе и окне.",
        "K2": "Наземный маршрут до объекта с доплечьями укладывается в подходящее окно.",
        "K3": "Ведомственная программа покрывает конкретную группу на целевую дату.",
        "K4": "Плательщики отдельных групп подтверждены, единое платёжное обязательство отсутствует.",
        "K5": "Исторический сигнал требует актуального подтверждения плеча, окна и объёма.",
        "K6": "Доказанный Base меньше 15 мест на целевом плече.",
        "K7": "Численность, сумма закупки и услуги ТМС не переводятся в кресла.",
    }
    rw_document = (BRIEF / "rw_data_request.md").read_text(encoding="utf-8")
    questions = [
        re.sub(r"\*\*", "", question)
        for question in re.findall(r"^[1-5]\. (.*\?)$", rw_document.split("## Как задать эти вопросы", 1)[1], re.M)
    ]
    check(len(questions) == 5, "Пять вопросов RW")
    handoff = (W2 / "wave2_handoff_to_wave3.md").read_text(encoding="utf-8")
    request = re.search(r"^> (По каждому платящему .+)", handoff, re.M).group(1)
    ledger = (W2 / "wave2_review_ledger.md").read_text(encoding="utf-8")
    check(all(x in ledger for x in ("d212399e", "W2-R1", "W2-R2", "W2-R3", "W2-R4", "W2-R5..R7",
                                    "Обязательные условия старта Волны 3")), "Журнал ревью")
    return {
        "benchmarks_and_playbooks": {"qualified_cases": qualified, "term_sheets": term_sheets,
                                    "rf_adaptations": adaptations},
        "why_not_barriers": {"formal_no_go_count": 0, "rules": prior_rules, "entries": barriers},
        "rw_5_questions": questions,
        "anonymized_customer_request": request,
    }


FORMULA_SPEC = {
    "units": {"client": "RUB per passenger (после разнесения выкупленной квоты на летящих)",
              "rw": "RUB per directed flight window or aircraft set, unless output suffix changes unit",
              "round_trip": "Сумма денежных показателей или времени двух направлений, без сложения вместимости"},
    "precision": {"published_decimals": 2, "allowed_rub_residual": 1, "intermediate_rounding": "NONE",
                  "geometry_rounding": "Геометрия и блок-время фиксированы по флот-матрице. Не пересчитывать при смене тарифа."},
    "functions": {"ROUNDUP": "От нуля", "ROUNDDOWN": "К нулю", "IF": "Если условие, взять второй аргумент, иначе третий",
                  "MIN": "Минимум", "MAX": "Максимум"},
    "directional": {
        mode: [{"output_id": key, "expression": expr, "excel_formula": "=" + expr}
               for key, expr in formulas] for mode, formulas in FORMULAS.items()
    },
    "round_trip": {
        "sum_outputs": CYCLE_OUTPUTS,
        "rw_doc_max_rub_per_block_h": "(SUM(rw_net_revenue_rub) * (1 - target_margin_pct / 100) - SUM(rw_flight_non_doc_cost_rub)) / SUM(rw_billable_block_h)",
        "sum_definition": "SUM по двум направленным значениям без округления, затем ROUND до двух знаков. "
                          "Целевая маржа применяется одинаково к обоим направлениям оборота.",
    },
    "not_applicable": {"BLOCK": ["rw_total_flight_cost_rub", "rw_break_even_charter_price_rub", "rw_doc_max_rub_per_block_h"],
                       "TICKET": ["Все выходы RW, поскольку сравнивается TCT покупки билетов."]},
    "interpretations_ru": {
        "client_cash_tct_rub": "Приведённая цена, багаж, доплечья, плановые ночёвки и ожидаемые прямые расходы при сбое.",
        "client_time_value_rub": "Доля дверного времени в рабочих часах плюс ожидаемая потеря часов при сбое, "
                                 "умноженные на полную стоимость часа.",
        "client_total_tct_rub": "Cash Budget плюс денежная оценка Lost Work Time. Денежный бюджет не включает стоимость времени.",
        "client_max_unit_contract_price_rub": "Паритет TCT с заданной альтернативой на выкупленное место или на "
                                             "пассажирскую долю чартера. Отрицательное значение исключает ценовой паритет.",
        "rw_total_flight_cost_rub": "DOC покрывает топливо, ТО, экипаж и навигацию. Базовые расходы аэропортов, "
                                   "распределённый фикс и резерв добавляются за эквивалент циклов. "
                                   "Стоянка/ПОО начисляется на базу аэропорта по указанному плечу.",
        "ferry_factor": "Один коэффициент масштабирует блок-часы и эквивалентные циклы. После получения программы "
                        "считать точные маршруты, часы и дискретные циклы перегонов.",
        "rw_break_even_charter_price_rub": "Полная цена клиенту при нулевом вкладе RW, за все борта направленного окна.",
        "rw_break_even_seat_price_rub": "Чартер: цена на пассажира в данном окне. Блок: цена выкупленного места с "
                                      "покрытием обслуживания и вытеснения.",
        "rw_doc_max_rub_per_block_h": "Максимальный переменный расход блок-часа при заданной цене, "
                                     "нетто-выручке и целевой марже. Для блоков на существующих рейсах неприменим.",
        "rw_block_net_contribution_after_displacement_rub": "Нетто-выручка минус приращённые расходы и упущенный вклад. "
            "Изъяты платные места, соседние Y-кресла евробизнеса и ожидаемая доля поздно возвращённых мест. "
            "Для настоящего J отдельные вероятность вытеснения и упущенный вклад. "
            "Размещение J и политика возврата требуют согласования.",
        "rw_inventory_screen_pass": "Проверка чисел квоты и ёмкости из сценария. Реальный инвентарь запрашивается отдельно.",
        "operational_screen_pass": "Модельная проверка вместимости, допустимости дробления и класса; "
                                   "фактические масса, слоты, запасной, аэродром и экипажи требуют проверки RW.",
    },
}
CSV_OUTPUTS = (
    "client_cash_tct_rub", "client_lost_work_h", "client_time_value_rub", "client_total_tct_rub",
    "client_alt_cash_tct_rub", "client_alt_lost_work_h", "client_alt_time_value_rub", "client_alt_total_tct_rub",
    "client_max_unit_contract_price_rub", "rw_net_contribution_rub", "rw_total_flight_cost_rub",
    "rw_break_even_charter_price_rub", "rw_break_even_seat_price_rub", "rw_doc_max_rub_per_block_h",
    "rw_expected_displaced_seats", "rw_displacement_cost_rub", "rw_paid_seats", "rw_released_seats",
    "rw_block_net_contribution_after_displacement_rub", "j_passengers", "effective_seats_per_aircraft", "operational_screen_pass",
)


def csv_pilots(cases):
    for case_row in cases:
        row = {k: case_row[k] for k in ("case_id", "cluster_id", "title_ru", "beneficiary_ru",
                                       "decision", "demand_basis", "confirmed_pax",
                                       "airport_pair", "gc_distance_km", "mode", "aircraft_type", "default_variant_id")}
        row.update(source_tag=SCEN, confirmation_status=RW, evidence_ids=";".join(case_row["evidence_ids"]),
                   condition_ru=case_row["variants"][0]["condition_ru"])
        for direction in ("outbound", "inbound"):
            row[f"{direction}_airport_pair"] = case_row["direction_labels"][direction]
            row[f"{direction}_scenario_pax"] = case_row["inputs"][direction]["pax"]
            row[f"{direction}_scenario_quote_per_seat_rub"] = case_row["inputs"][direction]["offered_price_rub"]
            for field in CSV_OUTPUTS:
                row[f"{direction}_{field}"] = case_row["expected_outputs"][direction].get(field)
        trip = case_row["expected_outputs"]["round_trip"]
        for field in dict.fromkeys((*SUM_ROUND_TRIP, *CHARTER_SUM, *BLOCK_SUM, "rw_doc_max_rub_per_block_h")):
            row[f"round_trip_{field}"] = trip.get(field)
        row["variant_controls_json"] = json.dumps([
            {**{k: alt[k] for k in ("variant_id", "mode", "airport_pair", "aircraft_type", "gc_distance_km")},
             "expected_outputs": {direction: {k: v for k, v in metrics.items() if k in CSV_OUTPUTS}
                                  for direction, metrics in alt["expected_outputs"].items()}}
            for alt in case_row["variants"][1:]
        ], ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        yield row


def write_csv(name, rows, fields):
    with (ROOT / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    tables, evidence, future, qualified = load_sources()
    matrix, airport_coordinates = make_fleet(tables)
    registry = Registry(evidence)
    make_observations(registry, tables)
    cases, lookup = build_cases(registry, matrix, future)
    evaluate_cases(cases, registry, lookup)
    packets = read_packets(qualified)
    go_count = sum(row["decision"] == "Go" for row in tables["opportunities"])
    result = {
        "meta": {
            "schema_version": 1, "as_of": "2026-11-24", "wave2_commit": "d212399e",
            "open_source_go_count": go_count, "pairs_quantified": 0, "round0_threshold_pairs": 3,
            "honest_verdict_ru": "0/3 Go на открытых данных. Сценарные пороги применимы после подтверждения "
                                 "количества пассажиров, окна, плательщика и предложения на каждом плече.",
            "modeled_clusters": 5, "pilot_and_cluster_rows": len(cases),
            "model_status": SCEN, "confirmation_status": RW,
            "measured_tct_and_contract_status": "UNKNOWN",
            "source_corrections": [
                {"input": "Уфа → Новый Уренгой, поезд от 4 133 ₽ и 45 ч 33 мин",
                 "evidence_id": "EV-W2T1-020", "supply_id": "W2T1-SUP-016",
                 "reason_ru": "EV-W2T1-016 относится к рейсу KJA–IAA."},
                {"input": "18 200 ₽ LED → NUX, YC846", "evidence_id": "EV-W2T1-015", "supply_id": "W2T1-SUP-009",
                 "reason_ru": "EV-W2T1-019 относится к рейсу MJZ–IKT."},
            ],
            "review_constraints": {
                "W2-R1": "Цитировать срезы по ID источника. Перед переводом в Go сверить классификацию claim_type.",
                "W2-R2": {"EV-W13-001": "РН-Ванкор / РН40302710", "EV-W13-003": "Севернефтегазпром / 32616450256"},
                "W2-R3": "Проверены ортодромии, порядок дат, enum и содержательная причина Conditional. "
                         "Нулевые extra_nights в источнике допустимы только с подтверждённым маршрутом. "
                         "W2-C05-ATE-RAIL с 6/6 UNKNOWN используется только как контроль наземной альтернативы.",
                "W2-R4": "Три ориентира из заметок T2 перенесены в OBSERVED_OPEN. Тарифы LED–SVX и "
                         "московских аэропортов до ULY/ULV/KUF сценарные.",
                "W2-R5": "Сферическая ортодромия сверена с координатами для каждой аэропортовой строки.",
                "W2-R6": "SVX и TJM имеют регулярный паритет 3/4 по геометрии и 0/0 по наблюдениям. "
                         "У SVO три регулярные связные пары. Вывод об узле отсутствует.",
                "W2-R7": "События выбраны только по началу поля horizon_bucket FUTURE_.",
            },
            "round0_seat_thresholds": {"block": [15, 20], "ssj_charter": [70, 80], "midsize_charter_at_least": 120},
        },
        "formulas_spec": FORMULA_SPEC,
        "pilots_and_clusters": cases,
        "fleet_matrix": {
            "pairs": matrix,
            "distance_spec": {
                "ortho": "Гаверсинус, R=6371.0088 км. Для сортировки и экранов дальности используется ортодромия.",
                "route_distance_km_k110": "round(gc_distance_km * 1.10, 2)",
                "est_block_time_h": "round(0.45 + route_distance_km_k110 / 760.0, 2)",
                "source_tag": "MODEL_ESTIMATE",
                "periods_of_flight_ru": "0,45 ч — руление, набор и снижение. 760 км/ч — средняя крейсерская путевая.",
                "ssj95b_100y_gc_km": {"fit_max": 2250, "borderline_max": 2450, "conservative_reference": 2355},
                "sj100_pd8_gc_km": {"study_envelope_max": 2450, "source_tag": RW},
                "tu214_route_km": {"study_envelope_max": 5000, "source_tag": RW},
                "notes_ru": "Границы — фильтр исследования. Для SJ-100 и Ту-214 требуется подтверждение AW/OPS "
                            "по массе, запасным и погоде. Дальние пары свыше 6 389 км рассматриваются отдельно.",
            },
            "fleet_requirements": fleet_capacity(registry, matrix, go_count),
        },
        "hubs_summary": hubs_summary(tables, airport_coordinates),
        "organizations": tables["organizations_screening_v2"],
        "events_2027_future": future,
        "assumptions": list(registry.params.values()),
        "evidence": evidence,
        **packets,
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    check(not re.search(r"\b" + "MO" + r"W\b", encoded, re.I)
          and "net" + "work.csv" not in encoded, "Запрещённый архивный маркер")
    summaries = list(csv_pilots(cases))
    write_csv("fleet_and_distance_matrix.csv", matrix, FLEET_FIELDS)
    write_csv("pilot_economics_summary.csv", summaries, list(summaries[0]))
    (ROOT / "model_inputs_registry.json").write_text(encoded, encoding="utf-8")
    print(f"P5_FLEET_ECON: {len(matrix)} пар, {len(cases)} веток, 5 кластеров, "
          f"{len(future)} будущих событий, {len(result['organizations'])} организаций, {go_count}/3 Go")


if __name__ == "__main__":
    main()
