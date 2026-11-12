# Проверенные исходники

Exact subject: `b51a47cf93cc01ca899d18d2ef94d9340261963f`. Все номера строк относятся к этому Git blob.

## engine/core.py

SHA256: `cfa9ec5ab3606e65bbba50bff00a0896aaf87817dfc62f2e27baee2a12697d82`.

```text
296:     def historical_ledger(source):
297:         # Recompute in fixed mode only to compare realised ledgers, without
298:         # recursively entering adaptation. This also covers generated payments:
299:         # changing a future competitor must not rewrite a past customer advance.
300:         fixed = copy.deepcopy(source)
301:         fixed["context"]["evaluation_mode"] = "fixed_programme"
302:         result = evaluate(fixed)
303:         money = result["finance"]
304:         products = {p["product_id"]: p for p in source["products"]}
305:         flights = {f["flight_instance_id"]: f for f in source["flights"]}
306:         def accrual_date(event):
307:             if event.get("accrual_date"):
308:                 return date_floor(event["accrual_date"])
309:             pid = event["owner"]
310:             if event["economic_event_id"] == "journey_revenue:" + pid and pid in products:
311:                 product = products[pid]
312:                 if product.get("departure_date"):
313:                     return date_floor(product["departure_date"])
314:                 if product["legs"]:
315:                     return date_floor(flights[product["legs"][0]]["departure_utc"])
316:             return event["accrual_month"] + "-01"
317:         def rounded(value):
318:             return round(value, 8) if isinstance(value, float) else value
319:         accruals = {e["economic_event_id"]: (accrual_date(e), e["owner"], e["category"], rounded(e["quantity"]), rounded(e["amount"]))
320:                     for e in money["economic_events"] if accrual_date(e) < decision}
321:         cash = {e["cash_event_id"]: (e["payment_date"], e["economic_event_id"], e["category"], rounded(e["amount_signed"]))
322:                 for e in money["cash_events"] if date_floor(e["payment_date"]) < decision}
323:         return accruals, cash
324: 
325:     require(historical_ledger(bundle) == historical_ledger(parent),
326:             "adaptation rewrites historical derived accruals or cash")
```

## engine/operations.py

SHA256: `cfa43be7e01666c670e65c15e4e903c9eda379fee8a2887cca50d29e53736616`.

```text
106:     return {"status": "INFEASIBLE" if errors else "CONDITIONAL" if unknowns else "FEASIBLE_WITHIN_EXPLICIT_CONSTRAINTS", "errors": errors, "unknowns": sorted(set(unknowns)), "rotations": rotations, "unused_aircraft": sorted(set(tails) - {a["aircraft_id"] for a in assignments.values()}), "dispatch_ready": False}
107: 
108: 
109: def check_itineraries(bundle):
110:     flights = {f["flight_instance_id"]: f for f in bundle["flights"]}
111:     unknowns = []
112:     for p in bundle["products"]:
113:         fields(p, "product_id demand_pool_id month customer_segment kind owner gross_fare net_fare fare_unit duration_minutes frequency availability capacity legs departure_date min_connection_minutes max_connection_minutes revenue_weights committed_sales contract_only cash_profile assumption_id", "products")
114:         pid = p["product_id"]
115:         require(p["kind"] in ("air", "ground", "outside"), f"{pid}: invalid kind")
116:         require(p["fare_unit"] == "RUB/journey", f"{pid}: convert yield to journey fare explicitly")
117:         require(p["departure_date"][:7] == p["month"], f"{pid}: month/departure date mismatch")
118:         require(p["availability"] in (True, False, None), f"{pid}: availability needs boolean/null")
119:         for k in ("gross_fare", "net_fare", "duration_minutes", "frequency", "capacity", "committed_sales"):
120:             number(p[k], f"{pid}.{k}", 0, nullable=k != "committed_sales")
121:         if p["availability"] is None:
122:             unknowns.append(f"{pid}: commercial availability UNKNOWN")
123:         if p["kind"] == "air":
124:             require(p["legs"], f"{pid}: air journey requires dated physical legs")
125:         require(len(p["legs"]) == len(set(p["legs"])), f"{pid}: duplicate leg")
126:         if p["legs"]:
127:             require(len(p["revenue_weights"]) == len(p["legs"]), f"{pid}: revenue weights count")
128:             require(all(number(w, pid, 0) is not None for w in p["revenue_weights"]), pid)
129:             require(abs(sum(p["revenue_weights"]) - 1) < EPS, f"{pid}: revenue weights must sum to one")
130:         for i, fid in enumerate(p["legs"]):
131:             require(fid in flights, f"{pid}: absent dated leg {fid}")
132:             f = flights[fid]
133:             if i == 0:
134:                 require(f["departure_utc"][:10] == p["departure_date"], f"{pid}: first UTC departure date mismatch")
```

## engine/finance.py

SHA256: `687b596fd85fbfe3f57eda396367f05e45021a3b0dcf31473ef083982101bd6c`.

```text
18: def materialize_events(bundle, allocations, products):
19:     events = copy.deepcopy(bundle["economic_events"])
20:     cash = copy.deepcopy(bundle["cash_events"])
21:     amounts = {a["product_id"]: a["carried"] for a in allocations} if allocations is not None else {}
22:     products_by_id = {p["product_id"]: p for p in products}
23:     flights = {f["flight_instance_id"]: f for f in bundle["flights"]}
24:     for e in events:
25:         if e["category"] == "revenue" and e["owner"] in products_by_id:
26:             require(e.get("revenue_role") == "separate_ancillary", "manual ticket revenue duplicates generated journey fare")
27:         if "driver" in e:
28:             d = e["driver"]
29:             kind = d["kind"]
30:             if kind == "journeys":
31:                 q = total(amounts.get(pid) for pid in d["product_ids"])
32:             elif kind == "segments":
33:                 q = total(None if amounts.get(pid) is None else amounts[pid] * len(products_by_id[pid]["legs"]) for pid in d["product_ids"])
34:             elif kind == "flights":
35:                 require(all(fid in flights for fid in d["flight_ids"]), "cost driver absent flight")
36:                 q = len(d["flight_ids"])
37:             elif kind == "block_hours":
38:                 from .common import utc
39:                 q = sum((utc(flights[fid]["arrival_utc"]) - utc(flights[fid]["departure_utc"])).total_seconds() / 3600 for fid in d["flight_ids"])
40:             else:
41:                 raise ValueError(f"Unsupported driver {kind}; use explicit sourced quantity")
42:             e["quantity"] = q
43:             e["amount"] = None if q is None or e["rate"] is None else q * e["rate"]
44:     for p in products:
45:         if p["owner"] != "RW" or p["kind"] == "outside":
46:             continue
47:         pid = p["product_id"]
48:         q = amounts.get(pid)
49:         amount = None if q is None or p["net_fare"] is None else q * p["net_fare"]
50:         eid = "journey_revenue:" + pid
51:         events.append({"economic_event_id": eid, "owner": pid, "category": "revenue", "scope": "affected_business", "driver_unit": "journey", "quantity": q, "rate": p["net_fare"], "amount": amount, "currency": "RUB", "price_year": bundle["context"]["price_year"], "fx_policy": "RUB_input", "accrual_month": p["month"], "noncash": False, "avoidability": "per_carried_journey", "shared_event_id": eid, "source_id": p.get("source_id", "SCENARIO"), "assumption_id": p["assumption_id"], "cash_plan_status": "unknown" if p["cash_profile"] is None else "explicit"})
52:         if p["cash_profile"] is not None:
53:             require(abs(sum(x["fraction"] for x in p["cash_profile"]) - 1) < EPS, f"{pid}: cash fractions must sum to 1")
54:             for i, payment in enumerate(p["cash_profile"]):
55:                 number(payment["fraction"], "cash fraction", 0)
56:                 cash.append({"cash_event_id": f"{eid}:payment:{i}", "economic_event_id": eid, "related_asset_or_contract_id": pid, "payment_date": payment["date"], "amount_signed": None if amount is None else amount * payment["fraction"], "category": "operating", "currency": "RUB", "fx_at_payment": 1, "deposit_flag": False, "source_id": p.get("source_id", "SCENARIO"), "status": "scenario", "assumption_id": p["assumption_id"]})
57:     # Explicit fractions on cost/support events allow rates to change without stale cash.
58:     for e in events:
59:         if "payments" in e:
60:             require(abs(sum(x["fraction"] for x in e["payments"]) - 1) < EPS, f"{e['economic_event_id']}: settlement fractions")
61:             sign = SIGNS[e["category"]]
62:             require(sign != 0, "non-operating automatic settlements need explicit signed cash")
63:             for i, p in enumerate(e["payments"]):
64:                 number(p["fraction"], "payment fraction", 0)
65:                 cash.append({"cash_event_id": f"{e['economic_event_id']}:payment:{i}", "economic_event_id": e["economic_event_id"], "related_asset_or_contract_id": e["owner"], "payment_date": p["date"], "amount_signed": None if e["amount"] is None else sign * e["amount"] * p["fraction"], "category": "operating", "currency": "RUB", "fx_at_payment": 1, "deposit_flag": False, "source_id": e["source_id"], "status": "scenario", "assumption_id": e["assumption_id"]})
```

## engine/common.py

SHA256: `950c4dc82acc379075e07f91e9a9bfc0fefc35b23081c5b3302fa186d0c35e5d`.

```text
7: 
8: VERSION = "P06-1.0.2-adaptive"
```
