"""Separate accrual ownership, settlement dates and funding boundaries (RUB).

Cash need is computed BEFORE financing. Null propagates; a known subtotal is not
labelled a complete operating result. Economic event balances retain receivables,
payables and advances; post-horizon payments and obligations are never discarded.
"""
import copy
from collections import defaultdict
from .common import EPS, dated, difference, fields, month, months, number, require, total, unique

SIGNS = {"revenue": 1, "support": 1, "variable_cost": -1, "operating_fixed": -1,
         "aircraft_use": -1, "startup": -1, "exit": -1, "depreciation": -1,
         "investing": 0, "tax": 0, "financing": 0, "interest": 0}
VARIABLE = {"revenue", "support", "variable_cost"}
COVERAGE = ("variable_cost", "base", "aircraft_use", "reserve", "startup", "exit", "support")


def materialize_events(bundle, allocations, products):
    events = copy.deepcopy(bundle["economic_events"])
    cash = copy.deepcopy(bundle["cash_events"])
    amounts = {a["product_id"]: a["carried"] for a in allocations} if allocations is not None else {}
    products_by_id = {p["product_id"]: p for p in products}
    flights = {f["flight_instance_id"]: f for f in bundle["flights"]}
    for e in events:
        if "driver" in e:
            d = e["driver"]
            kind = d["kind"]
            if kind == "journeys":
                q = total(amounts.get(pid) for pid in d["product_ids"])
            elif kind == "segments":
                q = total(None if amounts.get(pid) is None else amounts[pid] * len(products_by_id[pid]["legs"]) for pid in d["product_ids"])
            elif kind == "flights":
                require(all(fid in flights for fid in d["flight_ids"]), "cost driver absent flight")
                q = len(d["flight_ids"])
            elif kind == "block_hours":
                from .common import utc
                q = sum((utc(flights[fid]["arrival_utc"]) - utc(flights[fid]["departure_utc"])).total_seconds() / 3600 for fid in d["flight_ids"])
            else:
                raise ValueError(f"Unsupported driver {kind}; use explicit sourced quantity")
            e["quantity"] = q
            e["amount"] = None if q is None or e["rate"] is None else q * e["rate"]
    for p in products:
        if p["owner"] != "RW" or p["kind"] == "outside":
            continue
        pid = p["product_id"]
        q = amounts.get(pid)
        amount = None if q is None or p["net_fare"] is None else q * p["net_fare"]
        eid = "journey_revenue:" + pid
        events.append({"economic_event_id": eid, "owner": pid, "category": "revenue", "scope": "affected_business", "driver_unit": "journey", "quantity": q, "rate": p["net_fare"], "amount": amount, "currency": "RUB", "price_year": bundle["context"]["price_year"], "fx_policy": "RUB_input", "accrual_month": p["month"], "noncash": False, "avoidability": "per_carried_journey", "shared_event_id": eid, "source_id": p.get("source_id", "SCENARIO"), "assumption_id": p["assumption_id"], "cash_plan_status": "unknown" if p["cash_profile"] is None else "explicit"})
        if p["cash_profile"] is not None:
            require(abs(sum(x["fraction"] for x in p["cash_profile"]) - 1) < EPS, f"{pid}: cash fractions must sum to 1")
            for i, payment in enumerate(p["cash_profile"]):
                number(payment["fraction"], "cash fraction", 0)
                cash.append({"cash_event_id": f"{eid}:payment:{i}", "economic_event_id": eid, "related_asset_or_contract_id": pid, "payment_date": payment["date"], "amount_signed": None if amount is None else amount * payment["fraction"], "category": "operating", "currency": "RUB", "fx_at_payment": 1, "deposit_flag": False, "source_id": p.get("source_id", "SCENARIO"), "status": "scenario", "assumption_id": p["assumption_id"]})
    # Explicit fractions on cost/support events allow rates to change without stale cash.
    for e in events:
        if "payments" in e:
            require(abs(sum(x["fraction"] for x in e["payments"]) - 1) < EPS, f"{e['economic_event_id']}: settlement fractions")
            sign = SIGNS[e["category"]]
            require(sign != 0, "non-operating automatic settlements need explicit signed cash")
            for i, p in enumerate(e["payments"]):
                number(p["fraction"], "payment fraction", 0)
                cash.append({"cash_event_id": f"{e['economic_event_id']}:payment:{i}", "economic_event_id": e["economic_event_id"], "related_asset_or_contract_id": e["owner"], "payment_date": p["date"], "amount_signed": None if e["amount"] is None else sign * e["amount"] * p["fraction"], "category": "operating", "currency": "RUB", "fx_at_payment": 1, "deposit_flag": False, "source_id": e["source_id"], "status": "scenario", "assumption_id": e["assumption_id"]})
    return events, cash


def funding(cash, start, end, opening, minimum_cash):
    number(opening, "opening cash", 0, nullable=True)
    number(minimum_cash, "minimum cash", 0, nullable=True)
    rows, cumulative, peak, closing = [], 0.0, 0.0, opening
    bymonth = defaultdict(list)
    for e in cash:
        if start <= month(e["payment_date"]) <= end:
            bymonth[month(e["payment_date"])].append(e)
    complete = opening is not None and minimum_cash is not None
    for m in months(start, end):
        row = {"month": m}
        for c in ("operating", "investing", "tax", "financing"):
            row[c + "_cash"] = total(e["amount_signed"] for e in bymonth[m] if e["category"] == c)
        before = total(row[c + "_cash"] for c in ("operating", "investing", "tax"))
        row["cash_before_financing"] = before
        cumulative = total([cumulative, before])
        row["cumulative_cash_before_financing"] = cumulative
        need = None if not complete or cumulative is None else max(0.0, minimum_cash - opening - cumulative)
        peak = None if peak is None or need is None else max(peak, need)
        closing = total([closing, before, row["financing_cash"]])
        row.update(funding_before_financing=need, peak_funding_to_date=peak, closing_cash=closing, minimum_cash=minimum_cash)
        rows.append(row)
    # Daily balances. Equal-day receipts/payments are netted; intraday unknown.
    daycash = defaultdict(list)
    for e in cash:
        if start <= month(e["payment_date"]) <= end and e["category"] != "financing":
            daycash[dated(e["payment_date"])].append(e["amount_signed"])
    cum, daily_peak = 0.0, (max(0.0, minimum_cash - opening) if complete else None)
    for d in sorted(daycash):
        cum = total([cum, total(daycash[d])])
        daily_peak = None if daily_peak is None or cum is None else max(daily_peak, minimum_cash - opening - cum)
    return {"monthly": rows, "peak_month_end": peak, "peak_dated_day_end": daily_peak,
            "timing_status": "MONTH_END_LOWER_BOUND" if any(len(e["payment_date"]) == 7 for e in cash) else "DAY_END_LOWER_BOUND_INTRADAY_UNKNOWN",
            "opening_unrestricted_cash": opening, "minimum_cash": minimum_cash, "horizon": [start, end]}


def finance(bundle, allocations, products):
    c = bundle["context"]
    events, cash = materialize_events(bundle, allocations, products)
    es = unique(events, "economic_event_id", "economic_events")
    unique(events, "shared_event_id", "shared economic ownership")
    unique(cash, "cash_event_id", "cash_events")
    unknowns = []
    for e in events:
        fields(e, "owner category scope driver_unit quantity rate amount currency price_year fx_policy accrual_month noncash avoidability shared_event_id source_id assumption_id cash_plan_status", e["economic_event_id"])
        require(e["category"] in SIGNS, "Unsupported economic category (donor deduction is not an event)")
        require(e["scope"] == "affected_business", "use one affected-business boundary; company funding is a separate bridge")
        require(e["currency"] == "RUB" and e["price_year"] == c["price_year"], "normalize currency/price basis explicitly upstream")
        number(e["amount"], e["economic_event_id"], 0, nullable=True)
        number(e["quantity"], "quantity", 0, nullable=True)
        number(e["rate"], "rate", 0, nullable=True)
        if e["quantity"] is not None and e["rate"] is not None and e["amount"] is not None:
            require(abs(e["quantity"] * e["rate"] - e["amount"]) <= 1e-6 * max(1, e["amount"]), "quantity/rate amount bridge")
        if e["amount"] is None:
            unknowns.append(f"{e['economic_event_id']}.amount")
        require(month(e["accrual_month"]) >= c["cash_start"], "accrual before cash_start: extend evaluation boundary")
        if not e["noncash"] and e["cash_plan_status"] == "unknown":
            unknowns.append(f"{e['economic_event_id']}.cash_plan")
    for e in cash:
        fields(e, "economic_event_id related_asset_or_contract_id payment_date amount_signed category currency fx_at_payment deposit_flag source_id status assumption_id", e["cash_event_id"])
        require(e["category"] in ("operating", "investing", "tax", "financing"), "invalid cash category")
        require(e["currency"] == "RUB" and e["fx_at_payment"] == 1, "cash must contain explicit normalized RUB at payment FX")
        dated(e["payment_date"])
        require(month(e["payment_date"]) >= c["cash_start"], "prelaunch payment excluded by cash_start")
        number(e["amount_signed"], e["cash_event_id"], nullable=True)
        if e["economic_event_id"] is not None:
            require(e["economic_event_id"] in es, "payment refers to missing economic event")
            require(not es[e["economic_event_id"]]["noncash"], "noncash event must not also settle in cash")
    coverage = bundle["cost_coverage"]
    for k in COVERAGE:
        require(k in coverage, f"missing cost coverage: {k}")
        fields(coverage[k], "status event_ids rationale assumption_id", "cost_coverage." + k)
        require(coverage[k]["status"] in ("explicit", "not_applicable", "unknown"), "coverage status")
        require(all(e in es for e in coverage[k]["event_ids"]), "cost coverage references absent event")
        if coverage[k]["status"] == "unknown":
            unknowns.append("cost_coverage." + k)
        elif coverage[k]["status"] == "explicit":
            require(bool(coverage[k]["event_ids"]), f"{k}: explicit cost coverage needs events (including explicit zero)")
        else:
            require(bool(coverage[k]["rationale"]), f"{k}: not_applicable needs rationale")
    require(bundle["accounting_policy"] == "operating_aircraft_use_excludes_interest", "choose one operating aircraft-use convention")
    # Same underlying lease charge cannot appear both as rent and depreciation.
    lease = defaultdict(set)
    for e in events:
        if e.get("lease_asset_id"):
            lease[e["lease_asset_id"]].add(e["category"])
    require(not any("aircraft_use" in s and "depreciation" in s for s in lease.values()), "lease rent/depreciation double count")
    # One support scheme must use gross-cost + support or net-cost alone.
    for e in events:
        if e.get("net_of_support_scheme_id"):
            require(not any(x.get("support_scheme_id") == e["net_of_support_scheme_id"] for x in events), "fuel/support double recognition")
    op_unknown = any(x.startswith("cost_coverage.") for x in unknowns)
    variable_unknown = any(coverage[k]["status"] == "unknown" for k in ("variable_cost", "support"))
    cash_unknown = any(x.endswith(".cash_plan") for x in unknowns)
    for k in ("operating", "investing", "tax", "financing"):
        require(k in bundle["cash_coverage"], "cash coverage must explicitly include all categories")
        if bundle["cash_coverage"][k] == "unknown":
            cash_unknown = True
            unknowns.append("cash_coverage." + k)
    ledger = funding(cash, c["cash_start"], c["period_end"], bundle["cash_policy"]["opening_cash"], bundle["cash_policy"]["minimum_cash"])
    if cash_unknown:
        # Do not manufacture dates/amounts for omitted payments. Keep known subtotal.
        ledger["known_schedule_peak_month_end"] = ledger["peak_month_end"]
        ledger["peak_month_end"] = ledger["peak_dated_day_end"] = None
        for r in ledger["monthly"]:
            r["known_cash_before_financing"] = r["cash_before_financing"]
            r["cash_before_financing"] = r["cumulative_cash_before_financing"] = r["funding_before_financing"] = r["peak_funding_to_date"] = r["closing_cash"] = None
    results = []
    for m in months(c["period_start"], c["period_end"]):
        ee = [e for e in events if e["accrual_month"] == m]
        r = next(dict(r) for r in ledger["monthly"] if r["month"] == m)
        r["revenue_net"] = total(e["amount"] for e in ee if e["category"] == "revenue")
        r["recognized_support"] = total(e["amount"] for e in ee if e["category"] == "support")
        r["variable_contribution"] = None if variable_unknown else total(None if e["amount"] is None else SIGNS[e["category"]] * e["amount"] for e in ee if e["category"] in VARIABLE)
        signed = [None if e["amount"] is None else SIGNS[e["category"]] * e["amount"] for e in ee if SIGNS[e["category"]]]
        r["known_operating_subtotal"] = sum(x for x in signed if x is not None)
        r["operating_result"] = None if op_unknown else total(signed)
        r["interest_accrued"] = total(e["amount"] for e in ee if e["category"] == "interest")
        r["tax_accrued"] = total(e["amount"] for e in ee if e["category"] == "tax")
        results.append(r)
    balances = []
    opening = unique(bundle["opening_balances"], "economic_event_id", "opening_balances")
    for eid, e in es.items():
        if e["noncash"] or SIGNS[e["category"]] == 0:
            continue
        accrual = 0 if e["accrual_month"] > c["period_end"] else (None if e["amount"] is None else SIGNS[e["category"]] * e["amount"])
        settled = total(x["amount_signed"] for x in cash if x["economic_event_id"] == eid and month(x["payment_date"]) <= c["period_end"])
        balance = total([opening.get(eid, {}).get("signed_balance", 0), accrual, None if settled is None else -settled])
        balances.append({"economic_event_id": eid, "signed_balance": balance, "positive_means": "receivable_or_prepaid_cost", "negative_means": "payable_or_customer_advance", "accrual_signed": accrual, "settled_signed": settled})
    require(set(opening).issubset(es), "opening balance needs corresponding economic event")
    deposit_assets = defaultdict(list)
    for x in cash:
        if x["deposit_flag"] and month(x["payment_date"]) <= c["period_end"]:
            deposit_assets[x["related_asset_or_contract_id"]].append(None if x["amount_signed"] is None else -x["amount_signed"])
    full_signed = [None if e["amount"] is None else SIGNS[e["category"]] * e["amount"] for e in events if SIGNS[e["category"]] and e["accrual_month"] <= c["period_end"]]
    return {"economic_events": events, "cash_events": cash, "results_monthly": results, "funding": ledger,
            "operating_result_including_prelaunch": None if op_unknown else total(full_signed),
            "known_operating_subtotal_including_prelaunch": sum(x for x in full_signed if x is not None),
            "prelaunch_economic_events": [e for e in events if e["accrual_month"] < c["period_start"]],
            "terminal": {"balances": balances, "refundable_deposits": [{"asset_id": k, "signed_asset_balance": total(v)} for k, v in deposit_assets.items()], "future_economic_obligations": [e for e in events if e["accrual_month"] > c["period_end"]], "future_cash_events": [e for e in cash if month(e["payment_date"]) > c["period_end"]]},
            "unknown_dependencies": sorted(set(unknowns)), "cash_complete": not cash_unknown}
