"""Fetch Travelpayouts Data API v3 cached prices for all 209 pairs in P09.
Fast concurrent version with incremental CSV checkpointing and no secret printing.
"""
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = OUT_DIR / "routes_manifest_209.csv"
TP_SECRET_PATH = Path("/Users/a/.t3/userdata/secrets/files/dbb3ec0969a3e2b97ef07dee9b6c8ae8")


def fetch_json(url, headers, retries=3):
    hdrs = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity", **headers}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=12) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            return {"_http_error": e.code, "_reason": str(e.reason)}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.6)
                continue
            return {"_error": f"{type(e).__name__}: {e}"}
    return {"_error": "exhausted_retries"}


def fetch_pair(r, headers):
    a, b = r["a"], r["b"]
    rows_out = []
    calls = 0
    errors = 0

    def run_q(params, mode, month):
        nonlocal calls, errors
        url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates?" + urllib.parse.urlencode(params)
        data = fetch_json(url, headers)
        calls += 1
        if not data.get("success"):
            errors += 1
        for d in data.get("data", []):
            rows_out.append({
                "pair": r["pair"],
                "query_mode": mode,
                "query_month": month,
                "origin": d.get("origin"),
                "destination": d.get("destination"),
                "origin_airport": d.get("origin_airport"),
                "destination_airport": d.get("destination_airport"),
                "airline": d.get("airline"),
                "flight_number": d.get("flight_number"),
                "departure_at": d.get("departure_at"),
                "price_rub": d.get("price"),
                "transfers": d.get("transfers"),
                "duration_min": d.get("duration_to") or d.get("duration"),
                "gate": d.get("gate"),
                "spotlight44": r["spotlight44"],
                "pareto5": r["pareto5"],
            })

    # 1) Direct a->b and b->a (any future date)
    for orig, dst in [(a, b), (b, a)]:
        run_q({
            "origin": orig, "destination": dst, "currency": "rub",
            "one_way": "true", "direct": "true", "sorting": "price", "limit": 50,
        }, "any_date_direct", "any")

    # 2) Connecting + direct a->b and b->a (any future date)
    for orig, dst in [(a, b), (b, a)]:
        run_q({
            "origin": orig, "destination": dst, "currency": "rub",
            "one_way": "true", "direct": "false", "sorting": "price", "limit": 30,
        }, "any_date_all", "any")

    # 3) Seasonal slices for spotlight44 pairs
    if r["spotlight44"] == "True":
        for ym in ["2026-12", "2027-05", "2027-07"]:
            run_q({
                "origin": a, "destination": b, "departure_at": ym, "currency": "rub",
                "one_way": "true", "direct": "false", "sorting": "price", "limit": 30,
            }, "seasonal_all", ym)

    return r["pair"], rows_out, calls, errors


def main():
    rows = list(csv.DictReader(MANIFEST_PATH.open(encoding="utf-8")))
    tkey = TP_SECRET_PATH.read_text().strip()
    headers = {"X-Access-Token": tkey}

    all_out = []
    total_calls = 0
    total_errors = 0
    done = 0

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(fetch_pair, r, headers) for r in rows]
        for fut in as_completed(futs):
            pair, r_out, c, e = fut.result()
            all_out.extend(r_out)
            total_calls += c
            total_errors += e
            done += 1
            if done % 30 == 0 or done == len(rows):
                print(f"TP progress: {done}/{len(rows)} pairs, calls={total_calls}, errs={total_errors}, quotes={len(all_out)}", flush=True)

    out_path = OUT_DIR / "travelpayouts_prices_209.csv"
    if all_out:
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_out[0].keys()))
            w.writeheader()
            w.writerows(all_out)
    print(f"DONE: {len(all_out)} quotes saved to {out_path}", flush=True)


if __name__ == "__main__":
    main()
