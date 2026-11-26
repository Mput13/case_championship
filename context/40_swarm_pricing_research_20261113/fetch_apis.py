"""Fetch Yandex Rasp API schedules and Travelpayouts Data API v3 cached prices
for all 209 pairs / 22 hubs in P09 without printing or storing any API secrets.
"""
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = OUT_DIR / "routes_manifest_209.csv"
YANDEX_SECRET_PATH = Path("/Users/a/.t3/userdata/secrets/files/14f13315047c78683d81f59312fbad13")
TP_SECRET_PATH = Path("/Users/a/.t3/userdata/secrets/files/dbb3ec0969a3e2b97ef07dee9b6c8ae8")


def fetch_json(url, headers=None, retries=3, sleep_on_429=2.0):
    hdrs = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"}
    if headers:
        hdrs.update(headers)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(sleep_on_429 * (attempt + 1))
                continue
            return {"_http_error": e.code, "_reason": str(e.reason)}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.0)
                continue
            return {"_error": f"{type(e).__name__}: {e}"}
    return {"_error": "exhausted_retries"}


def run_yandex(ykey, rows):
    # 1) Station schedules for all 21 regional airports on 2026-12-08 (Tue) & 2026-12-11 (Fri)
    airports = sorted({r["a"] for r in rows} | {r["b"] for r in rows})
    airports = [a for a in airports if a not in ("MOW", "MOSCOW")]
    dates = ["2026-12-08", "2026-12-11"]
    hub_schedules = {}
    sched_rows = []
    calls = 0

    for st in airports:
        for dt in dates:
            params = {
                "apikey": ykey,
                "station": st,
                "system": "iata",
                "transport_types": "plane",
                "event": "departure",
                "date": dt,
                "limit": 200,
            }
            url = "https://api.rasp.yandex.net/v3.0/schedule/?" + urllib.parse.urlencode(params)
            data = fetch_json(url)
            calls += 1
            hub_schedules[f"{st}:{dt}"] = data
            for item in data.get("schedule", []):
                th = item.get("thread", {})
                car = th.get("carrier", {}) or {}
                codes = car.get("codes", {}) or {}
                sched_rows.append({
                    "station": st,
                    "date": dt,
                    "departure": item.get("departure"),
                    "flight_number": th.get("number"),
                    "title": th.get("title"),
                    "carrier_title": car.get("title"),
                    "carrier_iata": codes.get("iata"),
                    "carrier_sirena": codes.get("sirena"),
                    "vehicle": th.get("vehicle"),
                    "uid": th.get("uid"),
                })
            time.sleep(0.08)

    # 2) Direct + transfer /v3.0/search/ for the 44 spotlight pairs (a->b on 2026-12-08 & 2027-05-14)
    spotlight = [r for r in rows if r["spotlight44"] == "True"]
    search_results = {}
    pair_seg_rows = []
    for r in spotlight:
        for dt in ["2026-12-08", "2027-05-14"]:
            params = {
                "apikey": ykey,
                "from": r["a"],
                "to": r["b"],
                "system": "iata",
                "transport_types": "plane",
                "date": dt,
                "transfers": "true",
                "limit": 50,
            }
            url = "https://api.rasp.yandex.net/v3.0/search/?" + urllib.parse.urlencode(params)
            data = fetch_json(url)
            calls += 1
            search_results[f"{r['pair']}:{dt}"] = data
            for seg in data.get("segments", []):
                has_tr = bool(seg.get("has_transfers"))
                if has_tr:
                    details = seg.get("details", [])
                    carriers = [
                        ((d.get("thread") or {}).get("carrier") or {}).get("codes", {}).get("iata")
                        or ((d.get("thread") or {}).get("carrier") or {}).get("title")
                        for d in details if d.get("thread")
                    ]
                    vehicles = [(d.get("thread") or {}).get("vehicle") for d in details if d.get("thread")]
                    pair_seg_rows.append({
                        "pair": r["pair"],
                        "date": dt,
                        "has_transfers": True,
                        "transfers_count": len(carriers) - 1,
                        "carriers": ";".join(str(x or "") for x in carriers),
                        "vehicles": ";".join(str(x or "") for x in vehicles),
                        "duration_min": round((seg.get("duration") or 0) / 60, 1),
                        "departure": seg.get("departure"),
                        "arrival": seg.get("arrival"),
                        "tickets_info": json.dumps(seg.get("tickets_info"), ensure_ascii=False),
                    })
                else:
                    th = seg.get("thread", {}) or {}
                    car = th.get("carrier", {}) or {}
                    codes = car.get("codes", {}) or {}
                    pair_seg_rows.append({
                        "pair": r["pair"],
                        "date": dt,
                        "has_transfers": False,
                        "transfers_count": 0,
                        "carriers": codes.get("iata") or car.get("title") or "",
                        "vehicles": th.get("vehicle") or "",
                        "duration_min": round((seg.get("duration") or 0) / 60, 1),
                        "departure": seg.get("departure"),
                        "arrival": seg.get("arrival"),
                        "tickets_info": json.dumps(seg.get("tickets_info"), ensure_ascii=False),
                    })
            time.sleep(0.08)

    (OUT_DIR / "yandex_hub_schedules.json").write_text(json.dumps(hub_schedules, ensure_ascii=False))
    (OUT_DIR / "yandex_spotlight_search.json").write_text(json.dumps(search_results, ensure_ascii=False))
    if sched_rows:
        with (OUT_DIR / "yandex_hub_departures.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(sched_rows[0].keys()))
            w.writeheader()
            w.writerows(sched_rows)
    if pair_seg_rows:
        with (OUT_DIR / "yandex_spotlight_segments.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(pair_seg_rows[0].keys()))
            w.writeheader()
            w.writerows(pair_seg_rows)
    print(f"Yandex done: {calls} API calls, {len(sched_rows)} hub departures, {len(pair_seg_rows)} spotlight segments", flush=True)


def run_travelpayouts(tkey, rows):
    headers = {"X-Access-Token": tkey}
    tp_rows = []
    calls = 0
    errors = 0

    # Query ALL 209 pairs (both directions a->b and b->a for direct flights across any open future date,
    # plus monthly slices 2026-12 and 2027-07 for spotlight44 pairs and direct=false check).
    for i, r in enumerate(rows):
        a, b = r["a"], r["b"]
        # 1) All direct cached offers a->b and b->a (any date)
        for orig, dst in [(a, b), (b, a)]:
            params = {
                "origin": orig,
                "destination": dst,
                "currency": "rub",
                "one_way": "true",
                "direct": "true",
                "sorting": "price",
                "limit": 50,
            }
            url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates?" + urllib.parse.urlencode(params)
            data = fetch_json(url, headers=headers)
            calls += 1
            if not data.get("success"):
                errors += 1
            for d in data.get("data", []):
                tp_rows.append({
                    "pair": r["pair"],
                    "query_mode": "any_date_direct",
                    "query_month": "any",
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
            time.sleep(0.08)

        # 2) Also query connecting offers (direct=false) a->b (any date) so we see transfer competition!
        params_conn = {
            "origin": a,
            "destination": b,
            "currency": "rub",
            "one_way": "true",
            "direct": "false",
            "sorting": "price",
            "limit": 30,
        }
        url_c = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates?" + urllib.parse.urlencode(params_conn)
        data_c = fetch_json(url_c, headers=headers)
        calls += 1
        if not data_c.get("success"):
            errors += 1
        for d in data_c.get("data", []):
            tp_rows.append({
                "pair": r["pair"],
                "query_mode": "any_date_all",
                "query_month": "any",
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
        time.sleep(0.08)

        # 3) Seasonal slices (2026-12 winter, 2027-05 spring/may, 2027-07 summer) for the 44 spotlight pairs
        if r["spotlight44"] == "True":
            for ym in ["2026-12", "2027-05", "2027-07"]:
                params_s = {
                    "origin": a,
                    "destination": b,
                    "departure_at": ym,
                    "currency": "rub",
                    "one_way": "true",
                    "direct": "false",
                    "sorting": "price",
                    "limit": 30,
                }
                url_s = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates?" + urllib.parse.urlencode(params_s)
                data_s = fetch_json(url_s, headers=headers)
                calls += 1
                for d in data_s.get("data", []):
                    tp_rows.append({
                        "pair": r["pair"],
                        "query_mode": "seasonal_all",
                        "query_month": ym,
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
                time.sleep(0.08)

        if (i + 1) % 50 == 0:
            print(f"TP progress: {i+1}/{len(rows)} pairs, {len(tp_rows)} quotes", flush=True)

    if tp_rows:
        with (OUT_DIR / "travelpayouts_prices_209.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(tp_rows[0].keys()))
            w.writeheader()
            w.writerows(tp_rows)
    print(f"Travelpayouts done: {calls} API calls, errors={errors}, {len(tp_rows)} price rows", flush=True)


def main():
    rows = list(csv.DictReader(MANIFEST_PATH.open(encoding="utf-8")))
    ykey = YANDEX_SECRET_PATH.read_text().strip()
    tkey = TP_SECRET_PATH.read_text().strip()
    run_yandex(ykey, rows)
    run_travelpayouts(tkey, rows)


if __name__ == "__main__":
    main()
