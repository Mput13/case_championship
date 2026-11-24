#!/usr/bin/env python3
"""Validate the Wave 1 package offline against the frozen CSV schemas."""

import csv
import json
import re
import sys
from datetime import date
from decimal import Decimal
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
HEADERS = {
    "evidence.csv": (
        "evidence_id,source_url,issuer,document_date,checked_on,source_locator,"
        "supported_claim,evidence_level,limitation"
    ),
    "organizations_screening.csv": (
        "org_id,inn,legal_name,parent_org_id,sector,scope_role,tier,anchor_org_id,"
        "geography,cooperation,own_air_coverage,market_coverage,payer_channel,"
        "strategic_access,status,no_go_proof_type,decision_reason,decision_changing_fact,evidence_ids"
    ),
    "events_calendar_2026_2027.csv": (
        "event_id,event_or_project,series_id,event_year,event_name,event_type,host_city,"
        "nearest_airport_iata,date_status,start_date,end_date,phase_or_decline_trigger,"
        "target_orgs_summary,payer_or_organizer,evidence_ids"
    ),
    "benchmarks_cases.csv": (
        "case_id,case_name,country,buyer,operator,product,use_case,stage,outcome,key_terms,"
        "capacity_risk_owner,disruption_risk_owner,metric_code,metric_value,metric_unit,"
        "metric_period,currency,tax_basis,rf_transferable_term,rf_limit,evidence_ids"
    ),
}

SECTORS = set(
    "DEFENCE_INDUSTRY ENERGY OIL_GAS INFRA_TRANSPORT MINING_MATERIALS FINANCE_DEV TECH_SCIENCE".split()
)
CRITERIA = "geography cooperation own_air_coverage market_coverage payer_channel strategic_access".split()
CRITERION_VALUES = set("SUPPORTS MIXED LIMITS UNKNOWN".split())
ORG_ENUMS = {
    "sector": SECTORS,
    "scope_role": set("STATE_GROUP STATE_COMPANY SUBSIDIARY EPC_CONTRACTOR EXTERNAL_SUPPLIER EVENT_AGGREGATOR".split()),
    "tier": {"TIER1_DEEP", "TIER2_FAST"},
    "status": set("Candidate Conditional No-Go Insufficient-Evidence".split()),
    **dict.fromkeys(CRITERIA, CRITERION_VALUES),
}
NO_GO_PROOFS = set("OWN_FLEET MARKET_COVERED GROUND_ALT LOW_MOBILITY FRAGMENTED_PAYER".split())
EVENT_ENUMS = {
    "event_or_project": {"EVENT", "PROJECT"},
    "event_type": set("FORUM CONFERENCE EXHIBITION INDUSTRIAL_LAUNCH INFRA_BUILD OTHER".split()),
    "date_status": set("CONFIRMED PROVISIONAL TBD HISTORICAL_REF".split()),
}
UNAVAILABLE = {"UNAVAILABLE_PP301", "UNAVAILABLE_TECH"}
EVIDENCE_LEVELS = UNAVAILABLE | set(
    "PRIMARY_CONTRACT PRIMARY_TENDER PRIMARY_REPORT PRIMARY_SCHEDULE_TARIFF SECONDARY_MEDIA".split()
)
DOWNSIDES = {"CURTAILED", "CANCELLED"}
ADHOC = {"EMERGENCY_ADHOC", "EVENT_ADHOC"}
AMOUNT_METRICS = {"ASK_AMOUNT", "CONTRACT_AMOUNT", "PAID_AMOUNT"}
CASE_ENUMS = {
    "product": set("CORPORATE_FARE SEAT_BLOCK CHARTER SHUTTLE REVENUE_GUARANTEE TMC".split()),
    "use_case": ADHOC | {"REGULAR", "ROTATION"},
    "stage": set("OFFER RFI TENDER AWARDED OPERATED PAID".split()),
    "outcome": DOWNSIDES | set("ONGOING COMPLETED NO_AWARD UNKNOWN".split()),
    "metric_code": AMOUNT_METRICS | set(
        "UNIQUE_PAX ROUND_TRIPS PAX_SEGMENTS LEGS SEATS_PER_LEG PAX_PER_LEG BLOCK_HOURS EXTRA_BAGGAGE_PER_LEG".split()
    ) | {""},
    # The ledger does not specify other tax codes. The five batches document no tax basis.
    "tax_basis": {"UNKNOWN"},
}

# These rows are retained for context. The RFI specification and the forum's
# product terms are unavailable, so neither is counted as a qualified case.
CONTEXT_ONLY_CASES = {"W14-05", "W14-06"}
EVIDENCE_ID = re.compile(r"EV-[A-Z0-9]+-[0-9]+")
NUMBER = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")


def require(condition, errors, message):
    if not condition:
        errors.append(message)


def read_csv(path, errors):
    columns = HEADERS[path.name].split(",")
    rows = []
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            if next(reader, None) != columns:
                errors.append(f"{path.name}: header differs from the frozen schema")
                return []
            for values in reader:
                if len(values) != len(columns):
                    errors.append(f"{path.name}:{reader.line_num}: expected {len(columns)} columns, got {len(values)}")
                    continue
                rows.append(dict(zip(columns, values)))
    except (OSError, UnicodeError, csv.Error) as exc:
        errors.append(f"{path.name}: {exc}")
    return rows


def check_unique(rows, field, errors):
    seen = set()
    for position, row in enumerate(rows, 2):
        value = row[field]
        require(value and value == value.strip(), errors, f"Row {position}: invalid {field} {value!r}")
        require(value not in seen, errors, f"Duplicate {field}: {value!r}")
        seen.add(value)
    return seen


def check_enums(row, enums, label, errors):
    for field, allowed in enums.items():
        require(row[field] in allowed, errors, f"{label}: invalid {field} {row[field]!r}")


def parse_date(value, field, label, errors):
    try:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return date.fromisoformat(value)
    except ValueError:
        pass
    errors.append(f"{label}: invalid {field} {value!r}")
    return None


def valid_url(value):
    if re.search(r'[\s\x00-\x1f\x7f<>"{}|\\^\x60]|%(?![0-9a-fA-F]{2})', value):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None:
            return False
        if not re.fullmatch(r"(?:\[[^][]+\]|[^:[\]]+)(?::[0-9]+)?", parsed.netloc) or parsed.port == 0:
            return False
        host = parsed.hostname.removesuffix(".")
        if ":" in host:
            return bool(ip_address(host))
        host = host.encode("idna").decode("ascii")
    except (ValueError, UnicodeError):
        return False
    return len(host) <= 253 and all(
        re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", part)
        for part in host.split(".")
    )


def check_evidence(rows, errors):
    check_unique(rows, "evidence_id", errors)
    for row in rows:
        label = row["evidence_id"]
        require(EVIDENCE_ID.fullmatch(label), errors, f"Invalid evidence_id: {label!r}")
        require(valid_url(row["source_url"]), errors, f"{label}: invalid source_url {row['source_url']!r}")
        level = row["evidence_level"]
        require(level in EVIDENCE_LEVELS, errors, f"{label}: invalid evidence_level {level!r}")
        for field in ("issuer", "source_locator", "supported_claim"):
            require(row[field].strip(), errors, f"{label}: missing {field}")
        checked_on = parse_date(row["checked_on"], "checked_on", label, errors)
        if row["document_date"]:
            document_date = parse_date(row["document_date"], "document_date", label, errors)
            if checked_on and document_date:
                require(document_date <= checked_on, errors, f"{label}: document_date after checked_on")
        if level in UNAVAILABLE:
            require(row["limitation"].strip(), errors, f"{label}: missing reason for unavailability")
    return {row["evidence_id"]: row for row in rows}


def evidence_refs(row, label, evidence, errors):
    ids = row["evidence_ids"].split(";")
    if not all(EVIDENCE_ID.fullmatch(ref) for ref in ids):
        errors.append(f"{label}: use nonempty evidence IDs separated by ';' without whitespace")
        return []
    require(len(set(ids)) == len(ids), errors, f"{label}: duplicate evidence_ids")
    unresolved = set(ids) - evidence.keys()
    require(not unresolved, errors, f"{label}: unresolved evidence_ids {sorted(unresolved)}")
    return [evidence[ref] for ref in ids if ref in evidence]


def valid_inn(inn):
    if not re.fullmatch(r"[0-9]{10}", inn):
        return False
    weights = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    checksum = sum(int(digit) * weight for digit, weight in zip(inn, weights)) % 11 % 10
    return checksum == int(inn[-1])


def check_organizations(rows, evidence, root, errors):
    org_ids = check_unique(rows, "org_id", errors)
    inns = check_unique(rows, "inn", errors)
    sectors = {row["sector"] for row in rows}
    require(len(inns) >= 50, errors, f"Need at least 50 unique organizations, found {len(inns)}")
    require(sectors == SECTORS, errors, f"Need all 7 frozen sectors, missing {sorted(SECTORS - sectors)}")

    no_go_ids = []
    for row in rows:
        label = row["org_id"]
        check_enums(row, ORG_ENUMS, label, errors)
        refs = evidence_refs(row, label, evidence, errors)
        inn = row["inn"]
        require(valid_inn(inn) and label == f"RU-INN-{inn}", errors, f"{label}: invalid INN or derived org_id")
        for field in ("legal_name", "decision_reason"):
            require(row[field].strip(), errors, f"{label}: missing {field}")
        for field in ("anchor_org_id", "parent_org_id"):
            target = row[field]
            require(target in {"", "UNKNOWN"} or target in org_ids - {label}, errors, f"{label}: invalid {field} {target!r}")
        status = row["status"]
        proof_type = row["no_go_proof_type"]
        if status == "No-Go":
            no_go_ids.append(label)
            require(proof_type in NO_GO_PROOFS, errors, f"{label}: invalid no_go_proof_type {proof_type!r}")
            require(any(ref["evidence_level"] not in UNAVAILABLE for ref in refs), errors, f"{label}: No-Go needs available evidence")
        else:
            require(not proof_type, errors, f"{label}: no_go_proof_type applies only to No-Go")
        if status in {"Conditional", "Insufficient-Evidence"}:
            fact = row["decision_changing_fact"].strip()
            require(fact and fact != "UNKNOWN", errors, f"{label}: missing decision_changing_fact")
    if no_go_ids:
        try:
            registry = (root / "why_not_registry.md").read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"why_not_registry.md: {exc}")
        else:
            for org_id in no_go_ids:
                require(org_id in registry, errors, f"{org_id}: No-Go missing from why_not_registry.md")
    return len(sectors)


def check_cases(rows, evidence, errors):
    check_unique(rows, "case_id", errors)
    qualified = []
    for row in rows:
        previous_errors = len(errors)
        label = row["case_id"]
        check_enums(row, CASE_ENUMS, label, errors)
        refs = evidence_refs(row, label, evidence, errors)
        require(re.fullmatch(r"[A-Z]{2}", row["country"]), errors, f"{label}: invalid country code")
        for field in ("case_name", "buyer", "operator", "key_terms", "rf_transferable_term", "rf_limit"):
            require(row[field].strip(), errors, f"{label}: missing {field}")
        code, value, unit = (row[field] for field in ("metric_code", "metric_value", "metric_unit"))
        require(bool(code) == bool(value) == bool(unit.strip()), errors, f"{label}: provide metric_code, metric_value and metric_unit together")
        if value:
            require(NUMBER.fullmatch(value), errors, f"{label}: invalid metric_value {value!r}")
        if code in AMOUNT_METRICS:
            require(re.fullmatch(r"[A-Z]{3}", row["currency"]), errors, f"{label}: monetary metric needs a currency")
        available = any(ref["evidence_level"] not in UNAVAILABLE for ref in refs)
        if len(errors) == previous_errors and available and label not in CONTEXT_ONLY_CASES:
            qualified.append(row)

    counts = {
        "qualified_ru": sum(row["country"] == "RU" for row in qualified),
        "qualified_global": sum(row["country"] != "RU" for row in qualified),
        "qualified_downsides": sum(row["outcome"] in DOWNSIDES for row in qualified),
        "qualified_adhoc": sum(row["use_case"] in ADHOC for row in qualified),
    }
    require(len(qualified) >= 8, errors, f"Need at least 8 qualified benchmarks, found {len(qualified)}")
    require(counts["qualified_ru"] >= 4, errors, "Need at least 4 qualified Russian benchmarks")
    require(counts["qualified_global"] >= 4, errors, "Need at least 4 qualified international benchmarks")
    require(counts["qualified_downsides"] >= 1, errors, "Need a qualified CURTAILED or CANCELLED benchmark")
    require(counts["qualified_adhoc"] >= 1, errors, "Need a qualified EMERGENCY_ADHOC or EVENT_ADHOC benchmark")
    return counts


def check_events(rows, evidence, errors):
    check_unique(rows, "event_id", errors)
    dated_or_tbd = 0
    mow_count = 0
    for row in rows:
        previous_errors = len(errors)
        label = row["event_id"]
        check_enums(row, EVENT_ENUMS, label, errors)
        refs = evidence_refs(row, label, evidence, errors)
        require(row["event_name"].strip(), errors, f"{label}: missing event_name")
        year = row["event_year"]
        require(re.fullmatch(r"[1-9][0-9]{3}", year), errors, f"{label}: invalid event_year {year!r}")
        airport = row["nearest_airport_iata"]
        require(airport == "UNKNOWN" or re.fullmatch(r"[A-Z]{3}", airport), errors, f"{label}: invalid airport {airport!r}")
        mow = len(re.findall(r"\bMOW\b", airport, re.IGNORECASE))
        require(mow == 0, errors, f"{label}: MOW is a city code, use a specific airport")
        mow_count += mow

        start = parse_date(row["start_date"], "start_date", label, errors) if row["start_date"] else None
        end = parse_date(row["end_date"], "end_date", label, errors) if row["end_date"] else None
        if start:
            require(str(start.year) == year, errors, f"{label}: start_date disagrees with event_year")
        if end:
            require(start and start <= end, errors, f"{label}: end_date needs a start_date on or before it")
        status = row["date_status"]
        if status == "CONFIRMED":
            require(start, errors, f"{label}: confirmed start_date is missing")
        if status == "TBD":
            require(not (row["start_date"] or row["end_date"]), errors, f"{label}: TBD cannot have exact dates")
        if (
            len(errors) == previous_errors
            and refs
            and row["event_or_project"] == "EVENT"
            and year in {"2026", "2027"}
            and (status == "TBD" or (status in {"CONFIRMED", "PROVISIONAL"} and start))
        ):
            dated_or_tbd += 1
    require(dated_or_tbd >= 10, errors, f"Need at least 10 events with dates or TBD in 2026–2027, found {dated_or_tbd}")
    return dated_or_tbd, mow_count


def count_numeric_zeros(rows, field, label, errors):
    count = 0
    for row in rows:
        value = row[field]
        if NUMBER.fullmatch(value) and Decimal(value) == 0:
            errors.append(f"{row[label]}: numeric zero in {field}, use a blank for an unknown measurement")
            count += 1
    return count


def validate(root):
    errors = {key: [] for key in ("EVIDENCE", "P1_SCREENING", "P2_BENCHMARKS", "P3_EVENTS_PART")}
    sources = read_csv(root / "evidence.csv", errors["EVIDENCE"])
    orgs = read_csv(root / "organizations_screening.csv", errors["P1_SCREENING"])
    cases = read_csv(root / "benchmarks_cases.csv", errors["P2_BENCHMARKS"])
    events = read_csv(root / "events_calendar_2026_2027.csv", errors["P3_EVENTS_PART"])

    evidence = check_evidence(sources, errors["EVIDENCE"])
    sectors = check_organizations(orgs, evidence, root, errors["P1_SCREENING"])
    case_counts = check_cases(cases, evidence, errors["P2_BENCHMARKS"])
    dated_or_tbd, mow_count = check_events(events, evidence, errors["P3_EVENTS_PART"])
    zeros = (
        count_numeric_zeros(orgs, "inn", "org_id", errors["P1_SCREENING"])
        + count_numeric_zeros(cases, "metric_value", "case_id", errors["P2_BENCHMARKS"])
        + count_numeric_zeros(events, "event_year", "event_id", errors["P3_EVENTS_PART"])
    )

    return {
        "status": "FAIL" if any(errors.values()) else "PASS",
        "predicates": {
            key: "FAIL" if errors[key] or errors["EVIDENCE"] else "PASS"
            for key in ("P1_SCREENING", "P2_BENCHMARKS", "P3_EVENTS_PART")
        },
        "counts": {
            "evidence": len(sources),
            "organizations": len(orgs),
            "sectors": sectors,
            "benchmarks": len(cases),
            **case_counts,
            "calendar_rows": len(events),
            "dated_or_tbd_events_2026_2027": dated_or_tbd,
            "mow_airports": mow_count,
            "numeric_zeros": zeros,
        },
        "errors": [f"{group}: {message}" for group, messages in errors.items() for message in messages],
    }


if __name__ == "__main__":
    result = validate(ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "PASS" else 1)
