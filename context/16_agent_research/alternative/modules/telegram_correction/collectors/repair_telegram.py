#!/usr/bin/env python3
"""Repair historical Telegram bodies with exact class tokens, standard library.

No event classification. Original CSV is read-only. HTML is retained verbatim
inside gzip. HTTP headers are filtered in memory before any persistence.
"""
import argparse
import csv
import gzip
import hashlib
import json
import re
import subprocess
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
from urllib.error import HTTPError

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[4]
ORIGINAL = REPO / "context/16_agent_research/alternative/raw/colleague/data/raw/favt_posts.csv"
VERSION = "telegram-main-exact-v2"
ALLOWED_HEADERS = {"content-type", "content-length", "last-modified", "etag", "date", "cache-control", "retry-after"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def normalize_whitespace(s):
    return re.sub(r"\s+", " ", s.replace('\\n', '\n')).strip()


class MainReplyParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.current = None
        self.message_depth = None
        self.capture = None
        self.posts = []
        self.before = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = set(a.get("class", "").split())
        if tag == "br":
            if self.capture:
                self.capture[2].append("\n")
            return
        if tag not in VOID:
            self.stack.append(tag)
        depth = len(self.stack)
        if tag == "a" and "js-messages_more" in classes and a.get("data-before"):
            self.before.append(int(a["data-before"]))
        if tag == "div" and "js-widget_message" in classes and a.get("data-post", "").startswith("favt_info/"):
            if self.current:
                raise ValueError("Nested message blocks; source structure needs review")
            self.current = {"id": int(a["data-post"].split("/")[-1]), "main_bodies": [], "reply_bodies": [],
                            "nested_main_wrappers": 0,
                            "dt_utc": None, "media_present": False, "reply_href": None}
            self.message_depth = depth
        if self.current:
            if tag == "time" and a.get("datetime"):
                self.current["dt_utc"] = a["datetime"]
            if any(c.startswith("tgme_widget_message_photo") or c.startswith("tgme_widget_message_video")
                   or c.startswith("tgme_widget_message_document") for c in classes):
                self.current["media_present"] = True
            if tag == "a" and "tgme_widget_message_reply" in classes:
                self.current["reply_href"] = a.get("href")
            if tag == "div" and "tgme_widget_message_text" in classes:
                if "js-message_text" in classes and "js-message_reply_text" not in classes:
                    if self.capture:
                        # Observed post 8772 has an empty outer main wrapper
                        # enclosing another main div. Capture its text once at
                        # the outer scope; never turn a reply into the body.
                        if self.capture[0] != "main_bodies":
                            raise ValueError("Main body nested inside reply capture")
                        self.current["nested_main_wrappers"] += 1
                    else:
                        self.capture = ["main_bodies", depth, []]
                elif "js-message_reply_text" in classes:
                    if self.capture:
                        raise ValueError("Nested reply captures")
                    self.capture = ["reply_bodies", depth, []]

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.capture:
            self.capture[2].append(data)

    def handle_endtag(self, tag):
        if tag in VOID or tag not in self.stack:
            return
        # HTMLParser does not build a tree; close only the matching tag scope.
        index = len(self.stack) - 1 - self.stack[::-1].index(tag)
        closing_depth = index + 1
        if self.capture and closing_depth <= self.capture[1]:
            kind, depth, parts = self.capture
            self.current[kind].append("".join(parts).strip())
            self.capture = None
        if self.current and closing_depth <= self.message_depth:
            self.posts.append(self.current)
            self.current = None
            self.message_depth = None
        self.stack = self.stack[:index]


def parse(data):
    p = MainReplyParser()
    p.feed(data.decode("utf-8"))
    p.close()
    if p.current or p.capture:
        raise ValueError("Unclosed message/body; refuse partial extraction")
    return p.posts, min(p.before) if p.before else None


def safe_headers(stdout):
    result = []
    current = None
    for line in stdout.decode("utf-8", errors="replace").splitlines():
        if line.startswith("HTTP/"):
            current = {"status_line": line, "headers": {}}
            result.append(current)
        elif current is not None and ":" in line:
            k, v = line.split(":", 1)
            if k.lower() in ALLOWED_HEADERS:
                current["headers"][k.lower()] = v.strip()
    return result


def fetch(url, name, stop, transport="curl"):
    folder = BASE / "raw/pages"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (name + ".html.gz")
    receipt_path = folder / (name + ".receipt.json")
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text())
        if previous.get("status") != "PARSED":
            preserved_failure = folder / (name + ".failure_first.json")
            # Exactly one retry for a connection-level SSL_ERROR_SYSCALL only.
            # Never retry a rate limit or modify TLS/certificate settings.
            changing_to_urllib = transport == "urllib" and previous.get("transport", "curl") == "curl"
            urllib_transient = (transport == "urllib" and previous.get("transport") == "urllib"
                                and previous.get("status") == "ACCESS_FAILED"
                                and "UNEXPECTED_EOF_WHILE_READING" in previous.get("stderr", ""))
            if changing_to_urllib and not previous.get("rate_limited"):
                (folder / (name + ".failure_curl_final.json")).write_bytes(receipt_path.read_bytes())
            elif urllib_transient and not previous.get("rate_limited") and not (folder / (name + ".failure_urllib_once.json")).exists():
                (folder / (name + ".failure_urllib_once.json")).write_bytes(receipt_path.read_bytes())
            elif previous.get("rate_limited") or previous.get("curl_returncode") != 35 or preserved_failure.exists():
                stop.set()
                return previous, [], None
            else:
                preserved_failure.write_bytes(receipt_path.read_bytes())
    if receipt_path.exists() and target.exists() and json.loads(receipt_path.read_text()).get("status") == "PARSED":
        receipt = json.loads(receipt_path.read_text())
        data = gzip.decompress(target.read_bytes())
        assert sha(data) == receipt["html_sha256"]
        posts, before = parse(data)
        return receipt, posts, before
    if stop.is_set():
        return None, [], None
    started = now()
    if transport == "curl":
        tmp = folder / (name + ".download")
        cmd = ["curl", "-sS", "-L", "--max-time", "40", "--max-filesize", "2000000",
               "-D", "-", "-o", str(tmp), url]
        run = subprocess.run(cmd, capture_output=True)
        # Full headers exist only in process memory. Persist explicit whitelist.
        headers = safe_headers(run.stdout)
        code = int(headers[-1]["status_line"].split()[1]) if headers else None
        data = tmp.read_bytes() if tmp.exists() else b""
        if tmp.exists():
            tmp.unlink()
        returncode = run.returncode
        error = run.stderr.decode("utf-8", errors="replace")
    else:
        # Default HTTPS context: certificate and hostname verification stay on.
        # No cookies/session headers, custom auth, profile, or proxy modification.
        headers, code, data, error, returncode = [], None, b"", "", 0
        try:
            try:
                response = urlopen(url, timeout=40)
            except HTTPError as e:
                response = e
            with response:
                code = response.status
                headers = [{"status_line": f"HTTP {code} (urllib)",
                            "headers": {k.lower(): v for k, v in response.headers.items() if k.lower() in ALLOWED_HEADERS}}]
                data = response.read(2000001)
                if len(data) > 2000000:
                    raise ValueError("Source page exceeds 2 MB bounded read")
        except Exception as e:
            returncode = None
            error = f"{type(e).__name__}: {e}"
    rate_limited = code == 429 or any("retry-after" in x["headers"] for x in headers) or b"Too many requests" in data[:3000]
    if rate_limited:
        stop.set()
    receipt = {"source_url": url, "retrieved_at_utc": started, "completed_at_utc": now(),
               "http_status": code, "transport": transport, "curl_returncode": returncode if transport == "curl" else None,
               "transport_returncode": returncode, "stderr": error, "headers_whitelist": headers,
               "header_policy": sorted(ALLOWED_HEADERS), "rate_limited": rate_limited,
               "html_sha256": sha(data), "uncompressed_bytes": len(data), "parser_version": VERSION}
    if data:
        blob = gzip.compress(data, mtime=0)
        target.write_bytes(blob)
        receipt.update(raw_path=str(target.relative_to(BASE)), gzip_sha256=sha(blob), gzip_bytes=len(blob))
    posts, before = [], None
    if code == 200 and returncode == 0 and not rate_limited:
        try:
            posts, before = parse(data)
            if not posts:
                raise ValueError("HTTP200 but no Telegram message blocks")
            receipt["status"] = "PARSED"
            receipt["post_count"] = len(posts)
            receipt["min_id"] = min(x["id"] for x in posts)
            receipt["max_id"] = max(x["id"] for x in posts)
            receipt["next_before"] = before
        except Exception as e:
            receipt["status"] = "PARSE_FAILED"
            receipt["parse_error"] = str(e)
            stop.set()
    else:
        receipt["status"] = "ACCESS_FAILED"
        stop.set()
    dump(receipt_path, receipt)
    return receipt, posts, before


def seed_receipts():
    for ident in (4687, 6503):
        path = BASE / f"raw/{ident}.html"
        if not path.exists():
            continue
        data = path.read_bytes()
        receipt_path = BASE / f"raw/{ident}.receipt.json"
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            assert receipt["html_sha256"] == sha(data)
            continue
        posts, before = parse(data)
        dump(receipt_path, {"source_url": f"https://t.me/s/favt_info/{ident}", "raw_path": f"raw/{ident}.html",
                            "retrieved_at_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                            "http_status": 200, "html_sha256": sha(data), "uncompressed_bytes": len(data),
                            "status": "PARSED", "post_count": len(posts), "min_id": min(x["id"] for x in posts),
                            "max_id": max(x["id"] for x in posts), "next_before": before,
                            "header_policy": "HTTP status + whitelist; sanitized before analysis", "parser_version": VERSION})


def all_sources():
    for rp in sorted((BASE / "raw").glob("*.receipt.json")) + sorted((BASE / "raw/pages").glob("*.receipt.json")):
        r = json.loads(rp.read_text())
        if r.get("status") != "PARSED":
            continue
        raw = BASE / r["raw_path"]
        data = gzip.decompress(raw.read_bytes()) if raw.suffix == ".gz" else raw.read_bytes()
        assert sha(data) == r["html_sha256"], raw
        posts, _ = parse(data)
        for post in posts:
            yield post, r


def export():
    originals = list(csv.DictReader(ORIGINAL.open()))
    original = {int(x["id"]): x for x in originals}
    assert len(original) == len(originals), "Duplicate original ID"
    candidates = defaultdict(list)
    receipts = {}
    for post, r in all_sources():
        candidates[post["id"]].append((post, r))
        receipts[r["raw_path"]] = r
    output, replies, comparison, absent = [], [], [], []
    for ident in range(575, 9280):
        found = candidates.get(ident, [])
        found.sort(key=lambda x: (x[1]["retrieved_at_utc"], x[1]["raw_path"]))
        good = [x for x in found if len(x[0]["main_bodies"]) == 1]
        bodies = {x[0]["main_bodies"][0] for x in good}
        chosen = good[0] if good else (found[0] if found else None)
        post, r = chosen if chosen else ({}, {})
        status = "MAIN_TEXT_RECOVERED" if len(bodies) == 1 else "CONFLICTING_MAIN_BODIES" if len(bodies) > 1 else "NO_MAIN_TEXT_HTML" if found and all(len(x[0]["main_bodies"]) == 0 for x in found) else "AMBIGUOUS_MAIN_TEXT" if found else "NOT_OBSERVED_IN_RETRIEVED_HTML"
        body = next(iter(bodies)) if len(bodies) == 1 else None
        timestamp = post.get("dt_utc")
        dt_msk = datetime.fromisoformat(timestamp).astimezone(timezone(timedelta(hours=3))).isoformat() if timestamp else None
        row = {"id": ident, "in_original_csv": ident in original, "body_status": status,
               "dt_utc": timestamp, "dt_msk": dt_msk, "text": body,
               "dt_utc_source": timestamp, "main_text": body,
               "reply_preview_text": "\n\n".join(post.get("reply_bodies", [])) or None,
               "reply_href": post.get("reply_href"), "main_body_count": len(post.get("main_bodies", [])) if found else None,
               "reply_body_count": len(post.get("reply_bodies", [])) if found else None,
               "nested_main_wrappers": post.get("nested_main_wrappers") if found else None,
               "media_present": post.get("media_present") if found else None,
               "source_page_url": r.get("source_url"), "source_page_sha256": r.get("html_sha256"),
               "source_raw_path": r.get("raw_path"), "retrieved_at_utc": r.get("retrieved_at_utc"),
               "source_page_candidates": len(found), "distinct_main_bodies": len(bodies),
               "parser_version": VERSION, "value_type": "OBSERVED" if status == "MAIN_TEXT_RECOVERED" else "UNKNOWN",
               "limitations": "Current public HTML repair of historical IDs; edits/deletions since original snapshot possible; no event classification"}
        output.append(row)
        if status != "MAIN_TEXT_RECOVERED":
            absent.append({"id": ident, "in_original_csv": ident in original, "body_status": status,
                           "source_page_candidates": len(found), "reason": "A missing main body does not prove deletion or absence of a historical event"})
        if found:
            for k, reply in enumerate(post.get("reply_bodies", []), 1):
                replies.append({"post_id": ident, "reply_ordinal": k, "reply_preview_text": reply,
                                "reply_href": post.get("reply_href"), "source_page_url": r["source_url"],
                                "source_page_sha256": r["html_sha256"], "parser_version": VERSION})
        if ident in original:
            old = normalize_whitespace(original[ident]["text"])
            corrected = normalize_whitespace(body) if body is not None else None
            reply = normalize_whitespace(row["reply_preview_text"] or "")
            comparison.append({"id": ident, "body_status": status, "original_text": original[ident]["text"],
                               "corrected_main_text": body, "reply_preview_text": row["reply_preview_text"],
                               "original_equals_corrected_whitespace_normalized": old == corrected if corrected is not None else None,
                               "original_equals_reply_whitespace_normalized": old == reply if reply else None,
                               "original_dt_utc": original[ident]["dt_utc"], "corrected_dt_utc": post.get("dt_utc"),
                               "date_matches": original[ident]["dt_utc"].replace("+00:00", "+00:00") == post.get("dt_utc") if found else None,
                               "source_page_url": r.get("source_url"), "source_page_sha256": r.get("html_sha256")})
    write_csv(BASE / "normalized/main_posts.csv", output)
    write_csv(BASE / "normalized/reply_previews.csv", replies)
    write_csv(BASE / "normalized/comparison_original_corrected.csv", comparison)
    write_csv(BASE / "normalized/missing_or_unresolved_ids.csv", absent)
    selected = {str(ident): next(x for x in output if x["id"] == ident) for ident in (4685, 4687, 6503)}
    for ident in ("4687", "6503"):
        s = selected[ident]
        s["original_text"] = original[int(ident)]["text"]
        s["original_equals_reply_normalized"] = normalize_whitespace(s["original_text"]) == normalize_whitespace(s["reply_preview_text"] or "")
        s["original_equals_main_normalized"] = normalize_whitespace(s["original_text"]) == normalize_whitespace(s["main_text"] or "")
    status_counts = dict(Counter(x["body_status"] for x in output))
    coverage = {"parser_version": VERSION, "original_sha256": sha(ORIGINAL.read_bytes()), "original_records": len(original),
                "requested_id_min": 575, "requested_id_max": 9279, "requested_id_count": 8705,
                "original_ids_recovered_main": sum(x["id"] in original and x["body_status"] == "MAIN_TEXT_RECOVERED" for x in output),
                "original_ids_observed_in_html": sum(x["id"] in original and x["source_page_candidates"] > 0 for x in output),
                "original_ids_no_main_text_html": sum(x["id"] in original and x["body_status"] == "NO_MAIN_TEXT_HTML" for x in output),
                "original_ids_conflicting_main_bodies": sum(x["id"] in original and x["body_status"] == "CONFLICTING_MAIN_BODIES" for x in output),
                "original_ids_ambiguous_main_text": sum(x["id"] in original and x["body_status"] == "AMBIGUOUS_MAIN_TEXT" for x in output),
                "full_original_id_observation": all(x["source_page_candidates"] > 0 for x in output if x["id"] in original),
                "all_range_body_status_counts": status_counts,
                "original_comparison_changed_normalized": sum(x["original_equals_corrected_whitespace_normalized"] is False for x in comparison),
                "original_matches_reply_normalized": sum(x["original_equals_reply_whitespace_normalized"] is True for x in comparison),
                "parsed_source_pages": len(receipts), "full_original_main_text_recovery": all(x["body_status"] == "MAIN_TEXT_RECOVERED" for x in output if x["id"] in original),
                "coverage_status": "FULL_ORIGINAL_ID_MAIN_TEXT_RECOVERY" if all(x["body_status"] == "MAIN_TEXT_RECOVERED" for x in output if x["id"] in original) else "PARTIAL_MAIN_TEXT_RECOVERY",
                "limitations": "Present-day public HTML, not immutable historical source; no event classification. Counts from full recovered set only; no sample extrapolation."}
    dump(BASE / "reproduction.json", {"verified_examples": selected, "coverage": coverage})
    dump(BASE / "coverage.json", coverage)
    dump(BASE / "dataset_manifest.json", {"schema_version": "1.0", "path_base": "module directory", "parser_version": VERSION,
        "source_origin": "Telegram public channel preview", "original_sha256": coverage["original_sha256"],
        "snapshot_warning": "New retrieval repairs body attribution but may include source edits since original CSV",
        "datasets": [{"dataset_id": "favt_main_repair:"+r["html_sha256"][:16], "source_url": r["source_url"],
                      "raw_path": r["raw_path"], "sha256": r.get("gzip_sha256") or r["html_sha256"],
                      "uncompressed_sha256": r["html_sha256"],
                      "size_bytes": r.get("gzip_bytes") or r["uncompressed_bytes"],
                      "compression": "gzip" if r.get("gzip_sha256") else "none",
                      "retrieved_at_utc": r["retrieved_at_utc"], "publication_date": "post timestamps inside preserved HTML; no edit history",
                      "grain": "public channel post inside paginated HTML page", "geographic_coverage": "Russia; scope of Rosaviatsiya public channel",
                      "units": "post text; ISO8601 timestamp UTC", "key_fields": "source_page_sha256;post_id",
                      "collector_version": VERSION,
                      "command": "python3 context/16_agent_research/alternative/modules/telegram_correction/collectors/repair_telegram.py --historical --workers 4 --transport urllib --max-total-pages 120 --max-seconds 480",
                      "temporal_coverage": f"post IDs {r['min_id']}..{r['max_id']}", "record_count": r["post_count"],
                      "acquisition_status": "PARSED", "limitations": coverage["limitations"],
                      "uncompressed_bytes": r["uncompressed_bytes"], "gzip_sha256": r.get("gzip_sha256"), "gzip_bytes": r.get("gzip_bytes"),
                      "license": "UNKNOWN; publicly readable publisher messages; retain attribution"} for r in receipts.values()],
        "normalized_files": [{"path": str(p.relative_to(BASE)), "sha256": sha(p.read_bytes()), "size_bytes": p.stat().st_size}
                             for p in sorted((BASE / "normalized").glob("*.csv"))],
        "acquisition_diagnostics": [{"path": str(p.relative_to(BASE)), "sha256": sha(p.read_bytes())}
                                    for p in sorted((BASE / "raw").rglob("*.json"))]})
    print(json.dumps(coverage, ensure_ascii=False))


def historical(workers, transport, max_total_pages, max_seconds):
    # Independent contiguous ID partitions; each follows source's own before link.
    # Four reads maximum. Stop every chain on rate-limit or parser/access failure.
    stop = threading.Event()
    reservation_lock = threading.Lock()
    deadline = time.monotonic() + max_seconds
    reserved_urls = set()
    for rp in list((BASE / "raw").glob("*.receipt.json")) + list((BASE / "raw/pages").glob("*.receipt.json")):
        old = json.loads(rp.read_text())
        if old.get("status") == "PARSED":
            reserved_urls.add(old["source_url"])
    partitions = [(9280, 7104), (7104, 4928), (4928, 2752), (2752, 575)]

    def chain(start, floor):
        before, seen, pages = start, set(), 0
        while before > floor and not stop.is_set():
            if time.monotonic() >= deadline - 45:
                stop.set()
                return {"start": start, "floor": floor, "pages": pages, "status": "BOUNDED_TIME_BUDGET", "before": before}
            if before in seen:
                stop.set()
                return {"start": start, "floor": floor, "pages": pages, "status": "PAGINATION_LOOP", "before": before}
            seen.add(before)
            url = f"https://t.me/s/favt_info?before={before}"
            with reservation_lock:
                if url not in reserved_urls:
                    if len(reserved_urls) >= max_total_pages:
                        stop.set()
                        return {"start": start, "floor": floor, "pages": pages, "status": "BOUNDED_PAGE_BUDGET", "before": before}
                    reserved_urls.add(url)
            r, posts, next_before = fetch(url, f"before_{before}", stop, transport)
            if not r or r.get("status") != "PARSED":
                return {"start": start, "floor": floor, "pages": pages, "status": "STOPPED_ACCESS_OR_PARSE", "before": before}
            pages += 1
            minimum = min(x["id"] for x in posts)
            if minimum <= floor:
                return {"start": start, "floor": floor, "pages": pages, "status": "REACHED_PARTITION_FLOOR", "minimum_id": minimum}
            if next_before is None or next_before >= before:
                stop.set()
                return {"start": start, "floor": floor, "pages": pages, "status": "NO_DECREASING_PAGINATION", "before": before}
            before = next_before
            time.sleep(0.15)
        return {"start": start, "floor": floor, "pages": pages, "status": "STOPPED_GLOBAL"}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        result = list(pool.map(lambda pair: chain(*pair), partitions))
    dump(BASE / "pagination_receipt.json", {"completed_at_utc": now(), "max_parallel_reads": workers,
         "stop_on_rate_limit": True, "transport": transport, "partitions": result, "parser_version": VERSION,
         "max_total_unique_pages": max_total_pages, "max_seconds": max_seconds, "reserved_unique_urls": len(reserved_urls)})
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--historical", action="store_true")
    ap.add_argument("--workers", type=int, choices=[1, 2, 3, 4], default=4)
    ap.add_argument("--probe-before", type=int)
    ap.add_argument("--transport", choices=["curl", "urllib"], default="curl")
    ap.add_argument("--max-total-pages", type=int, default=120)
    ap.add_argument("--max-seconds", type=int, default=480)
    args = ap.parse_args()
    seed_receipts()
    if args.probe_before:
        r, posts, before = fetch(f"https://t.me/s/favt_info?before={args.probe_before}", f"before_{args.probe_before}", threading.Event(), args.transport)
        print(json.dumps({k: r.get(k) for k in ["source_url", "status", "http_status", "curl_returncode", "stderr", "post_count", "rate_limited"]}))
    if args.historical:
        print(json.dumps(historical(args.workers, args.transport, args.max_total_pages, args.max_seconds)))
    export()


if __name__ == "__main__":
    main()
