#!/usr/bin/env python3
"""Parse corrected main-body favt snapshot; reject contaminated colleague text.

The paired difference is between PUBLICATION timestamps. It is not downtime.
Repeated starts, absent lifts, conditional operation and missing effective dates
stay explicit. No interruption probability or continuous duration is estimated.
"""
import csv
import argparse
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "restriction-events-v2-main-only"
ALIASES = {
    "SVO": r"шереметьев", "DME": r"домодедов", "VKO": r"внуков",
    "ZIA": r"жуковск|раменское", "LED": r"пулков|санкт.петербург",
    "GOJ": r"нижни[йем]+\s+новгород|стригино", "KUF": r"самар|курумоч",
    "UFA": r"\bуф[аеуы]?\b", "KZN": r"казан", "NBC": r"бегишев|нижнекамск",
    "ULV": r"баратаев", "CSY": r"чебоксар", "SKX": r"саранск",
    "PEZ": r"пенз", "GSV": r"саратов|гагарин", "VOG": r"волгоград|гумрак",
    "ASF": r"астрахан|нариманов", "GRV": r"грозн", "IGT": r"магас",
    "OGZ": r"владикавказ|беслан", "MCX": r"махачкал|уйташ", "STW": r"ставропол",
    "MRV": r"минеральны[ех]\s+вод", "AER": r"сочи|адлер", "KRR": r"краснодар|пашковск",
    "GDZ": r"геленджик", "AAQ": r"анап", "EGO": r"белгород", "URS": r"курск",
    "BZK": r"брянск", "VOZ": r"воронеж", "LPK": r"липецк", "TBW": r"тамбов|донское",
    "KLF": r"калуг|грабцев", "IWA": r"иванов", "IAR": r"ярославл|туношн",
    "CEE": r"черепов", "PKV": r"псков", "PES": r"петрозаводск|бесовец",
    "MMK": r"мурманск", "ARH": r"архангельск|талаги", "KGD": r"калининград|храброво",
    "PEE": r"перм|большое\s+савино", "SVX": r"екатеринбург|кольцов",
    "CEK": r"челябинск|баландино", "TJM": r"тюмен|рощин", "REN": r"оренбург",
    "OSW": r"орск", "UUA": r"бугульм", "JOK": r"йошкар.ол", "IJK": r"ижевск",
    "KVX": r"киров|победилов", "NJC": r"нижневартовск", "SGC": r"сургут",
    "OMS": r"омск", "OVB": r"новосибирск|толмачев", "KJA": r"красноярск|емельянов",
    "IKT": r"иркутск", "UUD": r"улан.удэ|байкал", "HTA": r"чита|кадал",
    "VVO": r"владивосток|кневич", "KHV": r"хабаровск", "UUS": r"южно.сахалинск",
    "PKC": r"петропавловск|елизов", "GDX": r"магадан", "YKS": r"якутск",
}


def write(name, rows, fields=None):
    p = ROOT / "normalized" / name
    p.parent.mkdir(exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def run(input_path):
    raw_path = Path(input_path)
    if raw_path.resolve() == (ROOT / "raw/colleague/data/raw/favt_posts.csv").resolve():
        raise ValueError("PARSER_CONTAMINATION: original front text may be a reply preview; supply corrected main-body CSV")
    input_rows = list(csv.DictReader(raw_path.open(encoding="utf-8")))
    assert len({p["id"] for p in input_rows}) == len(input_rows)
    if not input_rows or "body_status" not in input_rows[0]:
        raise ValueError("Corrected input must carry explicit main body_status")
    posts = [p for p in input_rows if p["body_status"] == "MAIN_TEXT_RECOVERED"]
    if not posts or any(not p["text"] or not p["dt_utc"] for p in posts):
        raise ValueError("Recovered main body and publication time are required")
    events, unmatched, excluded, mixed = [], [], [], []
    for post in posts:
        text = post["text"].lower().replace("ё", "е")
        end = re.search(r"\bсняты\b|\bснято\b|\bснята\b", text)
        start = re.search(r"\bвведены\b|\bвведено\b|\bвведена\b", text)
        conditional = re.search(r"принима[ею]т\s+и\s+отправля[ею]т\s+рейс.{0,12}по\s+согласованию", text)
        if not (end or start or conditional) or "ограничен" not in text:
            continue
        if end and start:
            mixed.append({"post_id": post["id"], "published_at_utc": post["dt_utc"],
                          "status": "UNKNOWN_MIXED_ACTIONS_REQUIRES_CLAUSE_AIRPORT_REVIEW",
                          "source_url": "https://t.me/favt_info/" + post["id"], "main_body": post["text"]})
            continue
        # End messages often say "ограничения вводились" later; end wins.
        kind = "LIFT_ANNOUNCED" if end else "START_ANNOUNCED" if start else "CONDITIONAL_OPERATION"
        action = end or start or conditional
        preceding = text[max(0, action.start() - 35):action.start()]
        if action.start() > 500 or re.search(r"(?:будут|будет|не|могут\s+быть)\s*$", preceding):
            excluded.append({"post_id": post["id"], "reason": "narrative_or_future_or_negated_action",
                             "source_url": "https://t.me/favt_info/" + post["id"]})
            continue
        # Airport list is confined to the action preamble; exclude diversions,
        # destination lists and historical explanatory paragraphs.
        preamble = re.split(r"ограничения\s+(?:вводил|необходим)|в\s+период\s+действия|экипаж|говорит\s+росавиация", text)[0]
        preamble = preamble[:action.end() + 350]
        airports = [code for code, pattern in ALIASES.items() if re.search(pattern, preamble)]
        if not airports:
            unmatched.append({"post_id": post["id"], "published_at_utc": post["dt_utc"],
                              "kind": kind, "reason": "no unique mapped airport in action preamble",
                              "source_url": "https://t.me/favt_info/" + post["id"],
                              "preamble": preamble[:800]})
        clocks = re.findall(r"\b[всc]\s+(\d{1,2}[:.]\d{2})\s*мск", preamble)
        for airport in airports:
            events.append({"event_id": f'favt:{post["id"]}:{airport}', "airport_id": airport,
                           "post_id": post["id"], "event_type": kind,
                           "published_at_utc": post["dt_utc"],
                           "reported_clock_msk": ";".join(clocks),
                           "effective_start_utc": None, "effective_end_utc": None,
                           "value_status": "OBSERVED", "source_status": "PARSED",
                           "extraction_status": "RULE_EXTRACTED_NOT_FULLY_MANUALLY_VALIDATED",
                           "source_url": "https://t.me/favt_info/" + post["id"],
                           "raw_locator": f"{raw_path.name} id={post['id']}",
                           "main_body_page_sha256": post.get("source_page_sha256") or post.get("page_sha256"),
                           "recipe_version": VERSION})
    events.sort(key=lambda x: (x["published_at_utc"], int(x["post_id"]), x["airport_id"]))
    by_airport = defaultdict(list)
    for event in events:
        by_airport[event["airport_id"]].append(event)
    intervals, summaries = [], []
    for airport, airport_events in sorted(by_airport.items()):
        pending = []
        paired = ambiguous = missing_start = 0
        for event in airport_events:
            if event["event_type"] == "START_ANNOUNCED":
                pending.append(event)
                continue
            if event["event_type"] != "LIFT_ANNOUNCED":
                continue
            if not pending:
                missing_start += 1
                intervals.append({"airport_id": airport, "start_post_ids": "", "lift_post_id": event["post_id"],
                                  "first_start_publication_utc": None, "last_start_publication_utc": None,
                                  "lift_publication_utc": event["published_at_utc"],
                                  "announcement_elapsed_hours": None, "operating_duration_hours": None,
                                  "pair_status": "MISSING_START", "value_status": "UNKNOWN"})
                continue
            first, last = pending[0], pending[-1]
            elapsed = (dt.datetime.fromisoformat(event["published_at_utc"]) -
                       dt.datetime.fromisoformat(first["published_at_utc"])).total_seconds() / 3600
            status = "SINGLE_ANNOUNCEMENT_PAIR" if len(pending) == 1 and elapsed <= 24 else "AMBIGUOUS_REPEATS_OR_LONG_GAP"
            paired += status == "SINGLE_ANNOUNCEMENT_PAIR"
            ambiguous += status != "SINGLE_ANNOUNCEMENT_PAIR"
            intervals.append({"airport_id": airport, "start_post_ids": ";".join(e["post_id"] for e in pending),
                              "lift_post_id": event["post_id"], "first_start_publication_utc": first["published_at_utc"],
                              "last_start_publication_utc": last["published_at_utc"],
                              "lift_publication_utc": event["published_at_utc"],
                              "announcement_elapsed_hours": round(elapsed, 6) if status == "SINGLE_ANNOUNCEMENT_PAIR" else None,
                              "operating_duration_hours": None, "pair_status": status,
                              "value_status": "DERIVED" if status == "SINGLE_ANNOUNCEMENT_PAIR" else "UNKNOWN"})
            pending = []
        if pending:
            intervals.append({"airport_id": airport, "start_post_ids": ";".join(e["post_id"] for e in pending),
                              "lift_post_id": "", "first_start_publication_utc": pending[0]["published_at_utc"],
                              "last_start_publication_utc": pending[-1]["published_at_utc"],
                              "lift_publication_utc": None, "announcement_elapsed_hours": None,
                              "operating_duration_hours": None, "pair_status": "MISSING_LIFT", "value_status": "UNKNOWN"})
        counts = Counter(e["event_type"] for e in airport_events)
        summaries.append({"airport_id": airport, "start_announcements": counts["START_ANNOUNCED"],
                          "lift_announcements": counts["LIFT_ANNOUNCED"],
                          "conditional_announcements": counts["CONDITIONAL_OPERATION"],
                          "single_publication_pairs": paired, "ambiguous_closed_groups": ambiguous,
                          "missing_start_groups": missing_start, "unpaired_start_announcements_at_end": len(pending),
                          "operating_duration_hours": None, "risk_probability": None,
                          "absence_meaning": "not observed in this partial channel extraction; no zero-risk inference"})
    write("restriction_announcements.csv", events)
    write("restriction_interval_candidates.csv", intervals)
    write("restriction_airport_coverage.csv", summaries)
    write("restriction_unmapped.csv", unmatched,
          ["post_id", "published_at_utc", "kind", "reason", "source_url", "preamble"])
    write("restriction_excluded_narratives.csv", excluded, ["post_id", "reason", "source_url"])
    write("restriction_mixed_action_review.csv", mixed,
          ["post_id", "published_at_utc", "status", "source_url", "main_body"])
    audit = {"version": VERSION, "input_rows": len(input_rows),
             "input_body_statuses": dict(Counter(p["body_status"] for p in input_rows)),
             "raw_posts": len(posts), "raw_id_min": min(int(x["id"]) for x in posts),
             "raw_id_max": max(int(x["id"]) for x in posts),
             "raw_time_min": min(x["dt_utc"] for x in posts), "raw_time_max": max(x["dt_utc"] for x in posts),
             "airport_announcement_rows": len(events), "airport_count": len(by_airport),
             "announcement_types": dict(Counter(e["event_type"] for e in events)),
             "interval_candidate_status": dict(Counter(x["pair_status"] for x in intervals)),
             "unmapped_qualifying_posts": len(unmatched),
             "excluded_narratives": len(excluded),
             "mixed_action_posts_unknown": len(mixed),
             "all_operating_durations_unknown": all(x["operating_duration_hours"] is None for x in intervals),
             "scope": "publication events and explicitly uncertain pairings; not a closed-airport history",
             "source_snapshot": str(raw_path),
             "source_time_limit": "re-fetched main bodies at current snapshot; no historical edit audit"}
    (ROOT / "normalized/restriction_validation.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="corrected primary main-body CSV; original contaminated source refused")
    run(parser.parse_args().input)
