"""Conditional logit and simultaneous proportional capacity rationing.

Expected (fractional) journeys, not individual reservations. Every iteration moves
remaining demand; it never adds recaptured demand to the original market again.
The allocation is deterministic but is not a revenue-optimal inventory policy.
"""
import copy
import math
from .common import EPS, ContractError, UnknownInput, fields, number, pool_key, require, unique


def apply_response(bundle):
    products = copy.deepcopy(bundle["products"])
    for rule in bundle["response_policy"]["rules"]:
        fields(rule, "demand_pool_id month customer_segment rw_frequency_at_least target_product_ids gross_fare_multiplier frequency_multiplier intercept_delta assumption_id", "response rule")
        key = (rule["demand_pool_id"], rule["month"], rule["customer_segment"])
        rw = [p for p in products if p["owner"] == "RW" and pool_key(p) == key and p["availability"] is True]
        if any(p["frequency"] is None for p in rw):
            raise UnknownInput("competitor response trigger frequency UNKNOWN")
        rw_frequency = sum(p["frequency"] for p in rw)
        require(set(rule["target_product_ids"]) <= {p["product_id"] for p in products if pool_key(p) == key and p["owner"] != "RW"}, "response target outside pool/month/segment or not competitor")
        if rw_frequency >= rule["rw_frequency_at_least"]:
            for p in products:
                if p["product_id"] in rule["target_product_ids"]:
                    if p["gross_fare"] is not None:
                        p["gross_fare"] *= number(rule["gross_fare_multiplier"], "response fare multiplier", 0)
                    if p["frequency"] is not None:
                        p["frequency"] *= number(rule["frequency_multiplier"], "response frequency multiplier", 0)
                    p["intercept"] += number(rule["intercept_delta"], "response intercept")
    return products


def utility(product, coefficients):
    if product["availability"] is False or product["contract_only"]:
        return None
    if product["availability"] is None:
        raise UnknownInput(f"{product['product_id']}: unknown commercial availability")
    fields(product, "intercept", product["product_id"])
    if product["kind"] == "outside":
        return number(product["intercept"], "outside intercept")
    for k in ("gross_fare", "duration_minutes", "frequency"):
        if product[k] is None:
            raise UnknownInput(f"{product['product_id']}: unknown choice input {k}")
    if product["frequency"] <= 0:
        return None
    return (number(product["intercept"], "intercept")
            + coefficients["price_per_rub"] * product["gross_fare"]
            + coefficients["time_per_minute"] * product["duration_minutes"]
            + coefficients["log_frequency"] * math.log(product["frequency"]))


def allocate(bundle, products):
    markets = {}
    for m in bundle["markets"]:
        fields(m, "demand_pool_id month customer_segment potential_journeys market_basis mapping_to_potential source_id source_period as_of coverage status assumption_id", "market")
        k = pool_key(m)
        require(k not in markets, f"duplicate demand pool {k}")
        if m["potential_journeys"] is None:
            raise UnknownInput(f"{k}: potential demand UNKNOWN")
        number(m["potential_journeys"], str(k), 0)
        require(m["market_basis"] == "potential_travel", f"{k}: realized air demand needs explicit upstream potential mapping")
        markets[k] = m
    ps = unique(products, "product_id", "products")
    coeff = bundle["choice_model"]
    fields(coeff, "price_per_rub time_per_minute log_frequency assumption_id calibration_status", "choice_model")
    for k in ("price_per_rub", "time_per_minute", "log_frequency"):
        number(coeff[k], k)
    require(coeff["price_per_rub"] <= 0 and coeff["time_per_minute"] <= 0 and coeff["log_frequency"] >= 0, "choice coefficient signs")
    capacity = {}
    for f in bundle["flights"]:
        if f["saleable_seats"] is None:
            raise UnknownInput(f"{f['flight_instance_id']}: saleable seats UNKNOWN")
        capacity["flight:" + f["flight_instance_id"]] = number(f["saleable_seats"], "physical seats", 0)
    resources, u, assigned, initial, requested, committed = {}, {}, {}, {}, {}, {}
    remaining = {k: m["potential_journeys"] for k, m in markets.items()}
    for pid, p in ps.items():
        require(pool_key(p) in markets, f"{pid}: no shared demand pool")
        resources[pid] = ["flight:" + f for f in p["legs"]]
        if p["capacity"] is not None:
            capacity["product:" + pid] = p["capacity"]
            resources[pid].append("product:" + pid)
        elif p["kind"] != "outside" and not p["legs"]:
            raise UnknownInput(f"{pid}: unknown capacity; explicit scenario or physical inventory required")
        u[pid] = utility(p, coeff)
        assigned[pid] = initial[pid] = requested[pid] = 0.0
        committed[pid] = p["committed_sales"]
    # Contract passengers belong to the same pool and consume their legs once.
    contracts = unique(bundle["contracts"], "contract_id", "contracts")
    reserves = {k: 0.0 for k in capacity}
    contract_carried = {pid: 0.0 for pid in ps}
    block_products = set()
    for cid, c in contracts.items():
        fields(c, "product_id reserved_seats carried release_unused payment_mode economic_event_id assumption_id", cid)
        pid = c["product_id"]
        require(pid in ps, f"{cid}: absent contract product")
        p = ps[pid]
        require(p["contract_only"] and p["committed_sales"] == 0, f"{cid}: contract product must not also carry retail commitments")
        require(c["payment_mode"] in ("block", "per_passenger"), f"{cid}: invalid payment mode")
        number(c["reserved_seats"], cid, 0)
        number(c["carried"], cid, 0)
        require(c["carried"] <= c["reserved_seats"] and isinstance(c["release_unused"], bool), f"{cid}: contract reserve bridge")
        if c["payment_mode"] == "block":
            require(p["net_fare"] == 0, f"{cid}: block payment plus ticket revenue would duplicate revenue")
            ev = next((e for e in bundle["economic_events"] if e["economic_event_id"] == c["economic_event_id"]), None)
            require(ev is not None and ev["category"] == "revenue" and ev["owner"] == cid, f"{cid}: missing owned block payment economic event")
            block_products.add(pid)
        contract_carried[pid] += c["carried"]
        held = 0 if c["release_unused"] else c["reserved_seats"] - c["carried"]
        for r in resources[pid]:
            reserves[r] += held
    for pid, p in ps.items():
        q = committed[pid] + contract_carried[pid]
        require(q <= EPS or p["availability"] is True, f"{pid}: committed travel unavailable")
        assigned[pid] = q
        remaining[pool_key(p)] -= q
        for r in resources[pid]:
            capacity[r] -= q
    for r in capacity:
        capacity[r] -= reserves[r]
        require(capacity[r] >= -EPS, f"{r}: committed sales/reserves exceed inventory")
        capacity[r] = max(0, capacity[r])
    require(all(v >= -EPS for v in remaining.values()), "committed journeys exceed common demand pool")
    # At least one constrained resource is exhausted per constrained round.
    iteration = 0
    while any(v > EPS for v in remaining.values()):
        proposal = {}
        for k, rem in remaining.items():
            if rem <= EPS:
                continue
            eligible = [pid for pid, p in ps.items() if pool_key(p) == k and u[pid] is not None and all(capacity[r] > EPS for r in resources[pid])]
            require(eligible, f"{k}: no outside/unserved alternative remains")
            mx = max(u[pid] for pid in eligible)
            weights = {pid: math.exp(u[pid] - mx) for pid in eligible}
            den = sum(weights.values())
            for pid in eligible:
                proposal[pid] = rem * weights[pid] / den
        load = {r: sum(q for pid, q in proposal.items() if r in resources[pid]) for r in capacity}
        accepted = {}
        for pid, q in proposal.items():
            ratio = min([1.0] + [capacity[r] / load[r] for r in resources[pid] if load[r] > EPS])
            accepted[pid] = q * ratio
        progress = sum(accepted.values())
        require(progress > EPS, "allocation did not progress")
        for pid, q in accepted.items():
            assigned[pid] += q
            remaining[pool_key(ps[pid])] = max(0, remaining[pool_key(ps[pid])] - q)
            if iteration == 0:
                requested[pid], initial[pid] = proposal[pid], q
        for r in capacity:
            capacity[r] = max(0, capacity[r] - sum(q for pid, q in accepted.items() if r in resources[pid]))
        iteration += 1
        require(iteration <= len(capacity) + 3, "capacity iteration invariant failed")
    allocations = []
    for pid, p in ps.items():
        q = assigned[pid]
        allocations.append({"product_id": pid, "demand_pool_id": p["demand_pool_id"], "month": p["month"], "customer_segment": p["customer_segment"], "owner": p["owner"], "kind": p["kind"], "requested": requested[pid] + committed[pid] + contract_carried[pid], "carried": q if p["kind"] != "outside" else 0, "final_choice": q, "spilled": max(0, requested[pid] - initial[pid]), "recaptured_in": max(0, q - initial[pid] - committed[pid] - contract_carried[pid]), "recaptured_out": max(0, requested[pid] - initial[pid]), "outside_or_other": q if p["owner"] != "RW" else 0, "committed_sales": committed[pid], "contract_carried": contract_carried[pid], "block_paid": pid in block_products, "assumption_id": p["assumption_id"]})
    for k, m in markets.items():
        require(abs(sum(a["final_choice"] for a in allocations if pool_key(a) == k) - m["potential_journeys"]) < 1e-6, f"{k}: demand conservation")
    seats = []
    for f in bundle["flights"]:
        fid = f["flight_instance_id"]
        load = sum(assigned[pid] for pid, p in ps.items() if fid in p["legs"])
        held = reserves["flight:" + fid]
        require(load + held <= f["saleable_seats"] + 1e-6, f"{fid}: seat conservation")
        seats.append({"flight_instance_id": fid, "saleable_seats": f["saleable_seats"], "carried_segments": load, "unfilled_contract_seats": held, "unsold_seats": max(0, f["saleable_seats"] - load - held)})
    return {"allocations": allocations, "seats": seats, "iterations": iteration, "choice_method": "conditional_logit_simultaneous_proportional_recapture", "optimal": False}
