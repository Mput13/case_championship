#!/usr/bin/env python3
"""Offline extraction of this bounded pair from held airport timetable HTML."""
import csv
import datetime as dt
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent
START, END = dt.date(2026, 12, 7), dt.date(2026, 12, 13)
DAYS = {"пн": 1, "вт": 2, "ср": 3, "чт": 4, "пт": 5, "сб": 6, "вс": 7}


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return " ".join(" ".join(child.text() if isinstance(child, Node) else child for child in self.children).split())

    def all(self, class_name):
        found = []
        for child in self.children:
            if isinstance(child, Node):
                if class_name in child.attrs.get("class", "").split():
                    found.append(child)
                found.extend(child.all(class_name))
        return found


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def first(node, class_name):
    found = node.all(class_name)
    if not found:
        raise ValueError(f"Missing source field: {class_name}")
    return found[0]


def read_source(source_id):
    receipt = json.loads((BASE / "receipts" / f"{source_id}.json").read_text())
    raw = (BASE / receipt["raw_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == receipt["stored_sha256"]
    parser = Parser()
    parser.feed(raw.decode("utf-8"))
    return parser.root, receipt


def dates_in_window(valid_from, valid_to, weekdays):
    current = max(valid_from, START)
    while current <= min(valid_to, END):
        if current.isoweekday() in weekdays:
            yield current.isoformat()
        current += dt.timedelta(days=1)


def csv_write(filename, rows):
    with (BASE / filename).open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_rule(source_id, receipt, index, direction, role, flight, carrier, dep, arr, duration, dates, weekdays, aircraft="UNKNOWN", terminal="UNKNOWN"):
    valid_from, valid_to = (dt.datetime.strptime(dates[0], "%d.%m.%Y").date(), dt.datetime.strptime(dates[-1], "%d.%m.%Y").date())
    occurrences = list(dates_in_window(valid_from, valid_to, weekdays))
    if not occurrences:
        return None
    return {
        "rule_id": f"{source_id}_{index:03d}", "requested_pair_alias": "UFA-SGC", "direction_alias": direction,
        "alias_authority": "USER_TASK_INPUT_NOT_CANONICAL_IATA_MAPPING", "record_role": role,
        "origin_name": "Уфа" if direction == "UFA-SGC" else "Сургут", "destination_name": "Сургут" if direction == "UFA-SGC" else "Уфа",
        "origin_iata": "UNKNOWN", "destination_iata": "UNKNOWN", "flight_identifier_raw": flight,
        "carrier_display_raw": carrier, "carrier_role": "UNSPECIFIED_AIRPORT_TIMETABLE", "operating_carrier": "UNKNOWN", "marketing_carrier": "UNKNOWN",
        "valid_from": valid_from.isoformat(), "valid_to": valid_to.isoformat(), "weekday_iso": "|".join(map(str, weekdays)),
        "departure_clock_as_published": dep, "arrival_clock_as_published": arr, "clock_basis": "NOT_EXPLICIT_IN_CAPTURE",
        "origin_iana": "UNKNOWN", "destination_iana": "UNKNOWN", "published_duration": duration,
        "aircraft_as_published": aircraft, "terminal_at_ufa_as_published": terminal, "intermediate_stops": "UNKNOWN",
        "evidence_type": "PUBLISHED_SCHEDULE_RULE", "performed_status": "UNKNOWN", "open_sale_status": "UNKNOWN", "fare_quote_status": "NOT_REQUESTED",
        "target_window_departure_dates": "|".join(occurrences), "source_id": source_id, "source_url": receipt["url"],
        "capture_request_started_at_utc": receipt.get("request_started_at_utc", receipt.get("retrieved_at_utc")), "source_sha256": receipt["sha256"],
    }


def main():
    rules = []
    for source_id, direction in [("ufa_departures", "UFA-SGC"), ("ufa_schedule", "SGC-UFA")]:
        root, receipt = read_source(source_id)
        expected_id = "SCHEDULE_DIRECTION_TO" if direction == "UFA-SGC" else "SCHEDULE_DIRECTION_FROM"
        active = [node for node in root.all("active") if node.attrs.get("id", "").startswith("SCHEDULE_DIRECTION_")]
        assert len(active) == 1 and active[0].attrs["id"] == expected_id
        for index, card in enumerate(root.all("b-card-sez-card")):
            if "b-card-sez-card--caption" in card.attrs.get("class", "").split():
                continue
            field = lambda suffix: first(card, "b-card-sez-card__td_" + suffix).text()
            dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", field("period"))
            weekdays = [DAYS[node.text().lower()] for node in card.all("b-card-sez-card__td_day-week") if "_active" in node.attrs.get("class", "").split()]
            rule = make_rule(source_id, receipt, index, direction, "PRIMARY_PAIR_TIMETABLE_RULE", field("number").removeprefix("Номер рейса "), field("company"),
                             field("time--start").removeprefix("Вылет "), field("time--end").removeprefix("Прилет "), field("duration").removeprefix("Время в пути "),
                             dates, weekdays, field("flight").removeprefix("Тип судна "), field("terminal").removeprefix("Терминал "))
            if rule:
                rules.append(rule)
    root, receipt = read_source("surgut_schedule")
    groups = [group for group in root.all("schedule__flights") if first(group, "schedule__title").text() == "УФА"]
    assert len(groups) == 1
    for index, card in enumerate(groups[0].all("schedule__flight")):
        field = lambda suffix: first(first(card, "schedule__flight_" + suffix), "schedule__flight_value").text()
        dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", field("period"))
        days_node = first(card, "schedule__flight_days_row")
        weekdays = [DAYS[node.text().lower()] for node in days_node.all("active")]
        rule = make_rule("surgut_schedule", receipt, index, "SGC-UFA", "CORROBORATING_RULE_DO_NOT_ADD_TO_PRIMARY_COUNTS", field("num"), field("company"), field("departure"), field("arrival"), "UNKNOWN", dates, weekdays)
        if rule:
            rules.append(rule)
    csv_write("route_rules.csv", rules)
    occurrences = []
    for rule in rules:
        if rule["record_role"] != "PRIMARY_PAIR_TIMETABLE_RULE":
            continue
        for date in rule["target_window_departure_dates"].split("|"):
            occurrences.append({key: rule[key] for key in ["rule_id", "direction_alias", "flight_identifier_raw", "departure_clock_as_published", "arrival_clock_as_published", "source_id"]} | {
                "departure_date_as_published": date, "arrival_date": "UNKNOWN", "state": "SCHEDULE_DERIVED_NOT_PERFORMED", "open_sale_status": "UNKNOWN"})
    occurrences.sort(key=lambda row: (row["direction_alias"], row["departure_date_as_published"], row["departure_clock_as_published"]))
    keys = [(row["direction_alias"], row["flight_identifier_raw"], row["departure_date_as_published"], row["departure_clock_as_published"]) for row in occurrences]
    assert len(keys) == len(set(keys))
    csv_write("schedule_dates.csv", occurrences)
    factual = {"window": [START.isoformat(), END.isoformat()], "route_rules": rules,
               "corporate_source_extracts": [
                   {"source_id": "burintekh_contacts", "fact_paraphrase": "Официальная страница контактов БУРИНТЕХ указывает адрес: г. Уфа, ул. Юбилейная 4/1.", "publication_date": "UNKNOWN"},
                   {"source_id": "burintekh_sng_2006", "document_date": "2006-04-26", "fact_paraphrase": "Письмо Сургутнефтегаза с адресом в Сургуте подтверждает долгосрочные договорные отношения с БУРИНТЕХ и семь лет поставок буровых долот, бурголовок и фрезерного инструмента.", "present_relationship_status": "UNKNOWN", "travel_volume": "UNKNOWN"}],
               "personal_details_policy": "No names, signatures, individual contact details or employment records extracted"}
    (BASE / "safe_factual_extracts.json").write_text(json.dumps(factual, ensure_ascii=False, indent=2) + "\n")
    verification = {"verified_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "OFFLINE_EXTRACTION_VALIDATED",
                    "primary_rule_count": sum(rule["record_role"] == "PRIMARY_PAIR_TIMETABLE_RULE" for rule in rules), "corroborating_rule_count": sum(rule["record_role"] != "PRIMARY_PAIR_TIMETABLE_RULE" for rule in rules),
                    "primary_scheduled_occurrences": len(occurrences), "direction_counts": {direction: sum(row["direction_alias"] == direction for row in occurrences) for direction in ["UFA-SGC", "SGC-UFA"]},
                    "checks": ["Stored source bytes match stored_sha256", "Ufa active tab agrees with requested direction", "Only active weekday CSS classes used", "Dates constrained to both source validity and 2026-12-07/13", "No duplicate primary occurrence keys", "Surgut corroboration excluded from primary counts"],
                    "not_validated": ["Performed operations", "Open-sale availability", "Operator versus marketing carrier", "Timezone mapping", "Current corporate travel or OD demand"]}
    (BASE / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(verification, ensure_ascii=False))


if __name__ == "__main__":
    main()
