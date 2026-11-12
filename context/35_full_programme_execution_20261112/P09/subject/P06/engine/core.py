"""Public evaluate / compare / scenario interfaces. Inputs are immutable copies."""
import copy
from .common import VERSION, ContractError, UnknownInput, digest, difference, fields, month, months, number, pool_key, require, total, unique, utc
from .operations import check_itineraries, check_operations
from .choice import allocate, apply_response
from .finance import finance, funding

CONTEXT = "evaluation_id programme_id programme_version fleet_scope_id external_scenario_id delivery_calendar_id market_version choice_version cost_version response_policy_id evaluation_mode decision_date information_set_id keep_evaluation_id input_manifest_sha256 period_start period_end cash_start price_year affected_scope_id"
TABLES = "markets market_calendar products flights fleet_calendar assignments contracts economic_events cash_events opening_balances assumptions input_manifest choice_model response_policy cost_coverage cash_coverage cash_policy resource_operators accounting_policy information_set keep_policy programme_target metric_adapter"
COMMON = "fleet_scope_id external_scenario_id delivery_calendar_id market_version choice_version cost_version response_policy_id evaluation_mode decision_date information_set_id period_start period_end cash_start price_year affected_scope_id"


def seal(bundle):
    """Return a copy with the canonical manifest hash; never accepts a live branch."""
    b = copy.deepcopy(bundle)
    b["context"]["input_manifest_sha256"] = digest(b["input_manifest"])
    return b


def validate(bundle):
    fields(bundle, "context " + TABLES, "bundle")
    c = bundle["context"]
    fields(c, CONTEXT, "context")
    require(all(c[k] is not None and c[k] != "" for k in CONTEXT.split()), "context identifiers required")
    require(c["period_start"] == "2027-01" and c["period_end"] == "2028-12", "operating horizon must be 24 months 2027–2028")
    require(c["cash_start"] <= c["period_start"], "cash_start must include prelaunch")
    require(c["evaluation_mode"] in ("fixed_programme", "feasible_adaptation_with_existing_commitments"), "evaluation_mode")
    require(c["input_manifest_sha256"] == digest(bundle["input_manifest"]), "input manifest hash mismatch")
    for item in bundle["input_manifest"]:
        fields(item, "source_id commit path sha256", "input manifest")
        require(len(item["commit"]) == 40 and all(x in "0123456789abcdef" for x in item["commit"]), "immutable commit required")
        require(len(item["sha256"]) == 64, "input content SHA256 required")
    assumptions = unique(bundle["assumptions"], "assumption_id", "assumptions")
    for aid, a in assumptions.items():
        fields(a, "value unit selected_by basis approval_status range_or_unknown affected_conclusions sensitivity refinement", aid)
    used = set()
    def walk(x):
        if isinstance(x, dict):
            if "assumption_id" in x:
                used.add(x["assumption_id"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk({k: v for k, v in bundle.items() if k != "assumptions"})
    require(used <= set(assumptions), f"unregistered assumptions {used - set(assumptions)}")
    require(bundle["response_policy"]["response_policy_id"] == c["response_policy_id"], "response policy version mismatch")
    for m in bundle["markets"]:
        require(c["period_start"] <= m["month"] <= c["period_end"], "market outside forecast horizon")
        require(m["status"] in ("scenario", "estimated"), "historical/observed/published market cannot be future potential demand without adapter")
    calendars = {(r["demand_pool_id"], r["customer_segment"]): r for r in bundle["market_calendar"]}
    require(len(calendars) == len(bundle["market_calendar"]), "duplicate market calendar")
    scope = {(r["demand_pool_id"], r["customer_segment"]) for r in bundle["markets"]}
    require(scope <= set(calendars), "market calendar missing; absent months are not zero")
    for key, cal in calendars.items():
        fields(cal, "zero_months unknown_months assumption_id", "market_calendar")
        present = [r["month"] for r in bundle["markets"] if (r["demand_pool_id"], r["customer_segment"]) == key]
        declared = present + cal["zero_months"] + cal["unknown_months"]
        require(len(declared) == len(set(declared)), "duplicate demand pool or overlapping month coverage")
        require(set(declared) == set(months(c["period_start"], c["period_end"])), "market calendar must cover all 24 months explicitly")
    info = bundle["information_set"]
    require(info["information_set_id"] == c["information_set_id"], "information set identity")
    for fact in info["facts"]:
        require(fact["available_at"] <= c["decision_date"], f"future information at decision date: {fact['fact_id']}")
    if c["evaluation_mode"] == "feasible_adaptation_with_existing_commitments":
        fields(bundle, "adaptation", "adaptive bundle")
        ad = bundle["adaptation"]
        fields(ad, "parent_evaluation_id parent_bundle_sha256 actions preserved_commitment_ids assumption_id", "adaptation")
        facts = {f["fact_id"] for f in info["facts"]}
        for a in ad["actions"]:
            fields(a, "table record_id action effective_date decision_date based_on_fact_ids assumption_id", "adaptive action")
            require(a["decision_date"] == c["decision_date"], "adaptation action decision date")
            require(a["effective_date"] >= c["decision_date"], "adaptive action before decision")
            require(set(a["based_on_fact_ids"]) <= facts, "adaptive action uses unavailable information")
    fields(bundle["keep_policy"], "keep_policy_id future_period resource_policy existing_business alternative_new_resource_use excluded_unaffected_scope avoidable_cost_rules assumption_id", "keep_policy")
    require(bundle["keep_policy"]["future_period"] == [c["period_start"], c["period_end"]], "KEEP future period")
    if c["programme_id"] == "KEEP":
        require(c["keep_evaluation_id"] == c["evaluation_id"], "KEEP must bind itself")
    return sorted(used)


def traffic(bundle, allocations, products):
    c = bundle["context"]
    ps = {p["product_id"]: p for p in products}
    fs = {f["flight_instance_id"]: f for f in bundle["flights"]}
    rows = []
    for m in months(c["period_start"], c["period_end"]):
        aa = None if allocations is None else [a for a in allocations if a["month"] == m and a["owner"] == "RW" and a["kind"] != "outside"]
        journeys = None if aa is None else sum(a["carried"] for a in aa)
        segments = None if aa is None else sum(a["carried"] * len(ps[a["product_id"]]["legs"]) for a in aa)
        rpk = None if aa is None else total(None if any(fs[f]["distance_km"] is None for f in ps[a["product_id"]]["legs"]) else a["carried"] * sum(fs[f]["distance_km"] for f in ps[a["product_id"]]["legs"]) for a in aa)
        ff = [f for f in fs.values() if f["departure_utc"][:7] == m and f["operator"] in bundle["resource_operators"]]
        ask = total(None if f["saleable_seats"] is None or f["distance_km"] is None else f["saleable_seats"] * f["distance_km"] for f in ff)
        # Segments/RPK here belong to the journey departure cohort. Cross-month legs
        # have their actual service month in flight tables; do not imply flown-month LF.
        rows.append({"month": m, "journeys": journeys, "passenger_segments": segments, "RPK_journey_cohort": rpk, "ASK_flight_month": ask, "load_factor": None, "load_factor_status": "use flight_inventory by actual departure date", "compatible_carried_passengers": None})
    return rows


def annual_metrics(bundle, monthly):
    adapter = bundle["metric_adapter"]
    out = []
    for year in (2027, 2028):
        rs = [r for r in monthly if r["month"].startswith(str(year))]
        r = {"year": year, "journeys": total(x["journeys"] for x in rs), "passenger_segments": total(x["passenger_segments"] for x in rs), "compatible_carried_passengers": None, "share": None, "metric_status": "UNKNOWN_REPORTING_ADAPTER", "denominator_id": None}
        if adapter is not None:
            fields(adapter, "metric_definition_id source_id reporting_rule carrier_vs_group business_scope denominator_policy denominators assumption_id", "metric_adapter")
            require(adapter["reporting_rule"] in ("journeys", "passenger_segments"), "provide compatible reporting adapter; arbitrary reported passengers not inferred")
            numerator = r[adapter["reporting_rule"]]
            denrow = adapter["denominators"].get(str(year))
            r.update(metric_definition_id=adapter["metric_definition_id"], compatible_carried_passengers=numerator, metric_status="CONDITIONAL_ON_DOCUMENTED_ADAPTER")
            if denrow is not None:
                require(denrow["year"] == year and denrow["metric_definition_id"] == adapter["metric_definition_id"], "incompatible share denominator")
                den = number(denrow["value"], "denominator", 0, nullable=True)
                require(den is None or den > 0, "zero denominator")
                r.update(denominator=den, denominator_id=denrow["denominator_id"], share=None if den is None or numerator is None else numerator / den)
        out.append(r)
    return out


def evaluate(bundle, parent=None):
    b = copy.deepcopy(bundle)
    used = validate(b)
    if b["context"]["evaluation_mode"] == "feasible_adaptation_with_existing_commitments":
        parent = parent or b.get("adaptation", {}).get("parent_bundle")
        require(parent is not None, "adaptive evaluate requires exact parent bundle")
        check_adaptation(b, parent)
    ops = check_operations(b)
    itinerary_unknowns = check_itineraries(b)
    itinerary_unknowns += [f"{r['demand_pool_id']}: forecast months UNKNOWN {r['unknown_months']}" for r in b["market_calendar"] if r["unknown_months"]]
    try:
        products = apply_response(b)
    except UnknownInput as exc:
        products = b["products"]
        itinerary_unknowns.append(str(exc))
    allocation = None
    choice_errors = []
    if not ops["errors"] and not itinerary_unknowns:
        try:
            allocation = allocate(b, products)
        except UnknownInput as exc:
            choice_errors.append(str(exc))
    fin = finance(b, None if allocation is None else allocation["allocations"], products)
    t = traffic(b, None if allocation is None else allocation["allocations"], products)
    rows = []
    for money, tr in zip(fin["results_monthly"], t):
        rows.append({**money, **tr, "evaluation_id": b["context"]["evaluation_id"], "programme_version": b["context"]["programme_version"], "evaluation_mode": b["context"]["evaluation_mode"]})
    unknowns = sorted(set(ops["unknowns"] + itinerary_unknowns + choice_errors + fin["unknown_dependencies"]))
    for r in rows:
        r["unknown_dependencies"] = unknowns
    pairs = sorted({tuple(sorted((f["origin_airport"], f["destination_airport"]))) for f in b["flights"] if f["departure_utc"].startswith("2028-12") and f.get("project_network", False) and f["scheduled_status"] != "cancelled"})
    target = b["programme_target"]
    target_result = {"unique_airport_pairs_end2028": len(pairs), "pairs": pairs, "status": "WITHIN_8_12" if 8 <= len(pairs) <= 12 else "OUTSIDE_TARGET", "branch": target["branch"], "rationale": target["rationale"]}
    if target["branch"] != "main":
        target_result["status"] = "LABELLED_STAGE_OR_RESOURCE_SHORTFALL"
    summary = {k: total(r[k] for r in rows) for k in ("journeys", "passenger_segments", "revenue_net", "variable_contribution", "operating_result", "cash_before_financing")}
    summary["operating_result_including_prelaunch"] = fin["operating_result_including_prelaunch"]
    return {"engine_version": VERSION, "context": b["context"], "bundle_sha256": digest(b), "status": "INFEASIBLE" if ops["errors"] else "CONDITIONAL", "input_acceptance": "producer acceptance remains coordinator-owned", "operations": ops, "allocation": allocation, "effective_products": products, "results_monthly": rows, "results_annual": annual_metrics(b, rows), "summary": summary, "finance": fin, "network_target": target_result, "unknown_dependencies": unknowns, "used_assumption_ids": used, "choice_calibration": b["choice_model"]["calibration_status"], "global_optimality": False, "own_migration_transition_matrix": None, "own_migration_status": "NOT_IDENTIFIED; net P-KEEP journeys is not a measured passenger transition matrix", "cost_driver_exports": cost_driver_exports(b, allocation, products)}


def compare(project, keep, company_keep_cash=None, parents=None):
    """Compare complete bundles, not standalone headline money outputs."""
    for k in COMMON.split():
        require(project["context"][k] == keep["context"][k], f"P/KEEP mismatch: {k}")
    require(keep["context"]["programme_id"] == "KEEP", "counterfactual must be KEEP")
    require(project["context"]["keep_evaluation_id"] == keep["context"]["evaluation_id"], "wrong pinned KEEP evaluation_id")
    require(project["context"]["evaluation_id"] != keep["context"]["evaluation_id"], "P/KEEP evaluation id collision")
    # Both evaluations get independent allocations of the same external market and
    # resource envelope. Project-specific response comes from the same rule object.
    for k in ("markets", "market_calendar", "choice_model", "response_policy", "fleet_calendar", "keep_policy", "information_set"):
        require(digest(project[k]) == digest(keep[k]), f"P/KEEP common input mismatch: {k}")
    if project["metric_adapter"] is not None and keep["metric_adapter"] is not None:
        for field in ("metric_definition_id", "reporting_rule", "carrier_vs_group", "business_scope", "denominator_policy"):
            require(project["metric_adapter"][field] == keep["metric_adapter"][field], "incompatible reported metric scope/policy")
    parents = parents or {}
    p, k = evaluate(project, parents.get(project.get("adaptation", {}).get("parent_evaluation_id"))), evaluate(keep, parents.get(keep.get("adaptation", {}).get("parent_evaluation_id")))
    delta = []
    keys = ("journeys", "passenger_segments", "revenue_net", "variable_contribution", "operating_result", "operating_cash", "investing_cash", "tax_cash", "financing_cash", "cash_before_financing")
    for a, b in zip(p["results_monthly"], k["results_monthly"]):
        delta.append({"month": a["month"], **{"delta_" + f: difference(a[f], b[f]) for f in keys}})
    delta_cash = [dict(e, cash_event_id="P:" + e["cash_event_id"]) for e in p["finance"]["cash_events"]]
    delta_cash += [dict(e, cash_event_id="KEEP:" + e["cash_event_id"], amount_signed=None if e["amount_signed"] is None else -e["amount_signed"]) for e in k["finance"]["cash_events"]]
    c = project["context"]
    policy = project["cash_policy"]
    project_funding = funding(delta_cash, c["cash_start"], c["period_end"], policy["project_opening_cash"], policy["project_minimum_cash"])
    project_pre_interest = funding([x for x in delta_cash if x.get("subcategory") != "finance_interest"], c["cash_start"], c["period_end"], policy["project_opening_cash"], policy["project_minimum_cash"])
    if not p["finance"]["pre_interest_cash_complete"] or not k["finance"]["pre_interest_cash_complete"]:
        project_pre_interest["peak_month_end"] = project_pre_interest["peak_dated_day_end"] = None
    if not p["finance"]["cash_complete"] or not k["finance"]["cash_complete"]:
        project_funding["peak_month_end"] = project_funding["peak_dated_day_end"] = None
        project_funding["status"] = "UNKNOWN_CASH_DEPENDENCIES"
    company_funding = None
    if company_keep_cash is not None:
        require(company_keep_cash["keep_evaluation_id"] == c["keep_evaluation_id"], "company KEEP binding")
        require(company_keep_cash["scope"] == "whole_company_including_affected_keep", "company baseline must include affected KEEP")
        company_funding = funding(company_keep_cash["cash_events"] + delta_cash, c["cash_start"], c["period_end"], company_keep_cash["opening_cash"], company_keep_cash["minimum_cash"])
        if not p["finance"]["cash_complete"] or not k["finance"]["cash_complete"]:
            company_funding["peak_month_end"] = company_funding["peak_dated_day_end"] = None
    annual = []
    for a, b in zip(p["results_annual"], k["results_annual"]):
        compatible = a.get("metric_definition_id") == b.get("metric_definition_id") and a.get("metric_definition_id") is not None
        d = difference(a["share"], b["share"]) if compatible else None
        annual.append({"year": a["year"], "net_new_RW_journeys": difference(a["journeys"], b["journeys"]), "delta_passenger_segments": difference(a["passenger_segments"], b["passenger_segments"]), "delta_share_pp": None if d is None else 100 * d, "rank_or_number2_date": None})
    # Missing operating cost thresholds: only meaningful as a conditional aggregate
    # headroom, never silently imputing an unknown component to zero.
    headroom = difference(p["finance"]["known_operating_subtotal_including_prelaunch"], k["finance"]["known_operating_subtotal_including_prelaunch"])
    return {"engine_version": VERSION, "project": p, "keep": k, "delta_monthly": delta, "delta_annual": annual, "delta_summary": {f: difference(p["summary"][f], k["summary"][f]) for f in p["summary"]}, "project_incremental_funding": project_funding, "project_pre_interest_funding_diagnostic": project_pre_interest, "whole_company_funding": company_funding, "whole_company_funding_status": "UNKNOWN_KEEP_COMPANY_CASH" if company_funding is None else "CONDITIONAL_ON_FULL_COMPANY_CASH", "thresholds": {"net_missing_operating_cost_break_even": headroom, "equation": "delta_full_including_prelaunch = known_P_minus_KEEP_subtotal - net_missing_cost_P_minus_KEEP", "condition": "all other unknown revenue/support/cost terms fixed or included in net_missing_cost; not an empirical bound"}, "donor_extra_deduction": False, "network_changes": network_changes(project, keep)}


def network_changes(project, keep):
    p = {f["flight_instance_id"]: f for f in project["flights"]}
    k = {f["flight_instance_id"]: f for f in keep["flights"]}
    return [{"flight_instance_id": fid, "action": "add" if fid not in k else "cut" if fid not in p else "keep" if p[fid] == k[fid] else "move_or_change", "project": p.get(fid), "keep": k.get(fid)} for fid in sorted(set(p) | set(k))]


def check_adaptation(bundle, parent):
    require(bundle["adaptation"]["parent_evaluation_id"] == parent["context"]["evaluation_id"], "adaptive parent binding")
    require(bundle["adaptation"]["parent_bundle_sha256"] == digest(parent), "adaptive parent hash mismatch")
    decision = bundle["context"]["decision_date"]
    locked = set()
    new = {e["economic_event_id"]: e for e in bundle["economic_events"]}
    for e in parent["economic_events"]:
        if e.get("committed_at") and e["committed_at"] <= decision:
            locked.add(e["economic_event_id"])
            require(e["economic_event_id"] in new and new[e["economic_event_id"]] == e, "adaptation erases/changes prior commitment")
    require(locked <= set(bundle["adaptation"]["preserved_commitment_ids"]), "incomplete commitment preservation declaration")
    actions = {(a["table"], a["record_id"]): a for a in bundle["adaptation"]["actions"]}
    require(len(actions) == len(bundle["adaptation"]["actions"]), "duplicate adaptive actions")
    for table, key in (("products", "product_id"), ("flights", "flight_instance_id"), ("assignments", "flight_instance_id"), ("contracts", "contract_id"), ("economic_events", "economic_event_id"), ("cash_events", "cash_event_id")):
        old, new = {r[key]: r for r in parent[table]}, {r[key]: r for r in bundle[table]}
        for rid in set(old) | set(new):
            if old.get(rid) != new.get(rid):
                require((table, rid) in actions, f"adaptive change lacks action and information provenance: {table}/{rid}")
                action = "add" if rid not in old else "remove" if rid not in new else "replace"
                require(actions[table, rid]["action"] == action, "adaptive action does not match actual change")
        if table == "products":
            for rid, p in old.items():
                if p["committed_sales"] > 0:
                    require(rid in new and new[rid]["committed_sales"] >= p["committed_sales"], "adaptation erases booked journeys; explicit cancellation/refund model required")
    for table, key, datekey in (("flights", "flight_instance_id", "departure_utc"), ("cash_events", "cash_event_id", "payment_date")):
        later = {r[key]: r for r in bundle[table]}
        for row in parent[table]:
            if row[datekey][:10] < decision:
                require(later.get(row[key]) == row, f"adaptation rewrites historical {table}")


def scenario(bundles, parents=None):
    """Evaluate explicit complete variants; no hidden parameter overwrite/search."""
    unique([b["context"] for b in bundles], "evaluation_id", "scenario evaluations")
    parents = parents or {}
    out = []
    for b in bundles:
        if b["context"]["evaluation_mode"] == "feasible_adaptation_with_existing_commitments":
            pid = b["adaptation"]["parent_evaluation_id"]
            require(pid in parents, "adaptive evaluation requires exact parent bundle")
            check_adaptation(b, parents[pid])
        out.append(evaluate(b, parents.get(b.get("adaptation", {}).get("parent_evaluation_id"))))
    return {"evaluations": out, "search_scope": "explicit caller-provided candidates only", "global_optimality": False, "scenario_points_are_confidence_bounds": False}


def combine(base, components, context):
    """Union declared programme inputs; shared identical events once, conflicts fail.

    Base carries all KEEP/affected business. Components must explicitly supply the
    intended removals; this function never infers a donor or combines money results.
    """
    b = copy.deepcopy(base)
    tables = {"products": "product_id", "flights": "flight_instance_id", "assignments": "flight_instance_id", "contracts": "contract_id", "economic_events": "economic_event_id", "cash_events": "cash_event_id"}
    for part in components:
        require(part["base_bundle_sha256"] == digest(base), "component base version mismatch")
        for name, key in tables.items():
            rows = {r[key]: r for r in b[name]}
            for rid in part.get("remove", {}).get(name, []):
                require(rid in rows, f"removal of absent {name} {rid}")
                del rows[rid]
            for r in part.get(name, []):
                require(r[key] not in rows or rows[r[key]] == r, f"conflicting common {name} {r[key]}")
                rows[r[key]] = copy.deepcopy(r)
            b[name] = list(rows.values())
    b["context"] = copy.deepcopy(context)
    return seal(b)


def cost_driver_exports(bundle, allocation, products):
    """Physical service-month quantities for P04; no inferred charge or fuel burn."""
    seat = {} if allocation is None else {r["flight_instance_id"]: r for r in allocation["seats"]}
    ps = {p["product_id"]: p for p in products}
    aa = {} if allocation is None else {a["product_id"]: a for a in allocation["allocations"]}
    leg_revenue = {f["flight_instance_id"]: [] for f in bundle["flights"]}
    for pid, p in ps.items():
        if p["owner"] == "RW":
            q = aa.get(pid, {}).get("carried")
            for fid, w in zip(p["legs"], p["revenue_weights"]):
                leg_revenue[fid].append(None if q is None or p["net_fare"] is None else q * p["net_fare"] * w)
    fs = []
    for f in bundle["flights"]:
        fid = f["flight_instance_id"]
        fs.append({"flight_instance_id": fid, "month": f["departure_utc"][:7], "origin_airport": f["origin_airport"], "destination_airport": f["destination_airport"], "aircraft_variant": f["aircraft_variant"], "operator": f["operator"], "block_hours": (utc(f["arrival_utc"]) - utc(f["departure_utc"])).total_seconds() / 3600, "cycles": 1, "occupied_segments": seat.get(fid, {}).get("carried_segments"), "saleable_seats": f["saleable_seats"], "allocated_journey_revenue": total(leg_revenue[fid]), "revenue_allocation_is_not_extra_revenue": True, "load_factor": None if allocation is None or not f["saleable_seats"] else seat[fid]["carried_segments"] / f["saleable_seats"]})
    return {"physical_flights": fs, "journeys": [] if allocation is None else allocation["allocations"], "tail_resource_calendar": bundle["fleet_calendar"], "base_calendar": bundle.get("base_calendar"), "base_calendar_status": "UNKNOWN" if "base_calendar" not in bundle else "EXPLICIT_PRODUCER_INPUT", "invoice_cash_events": bundle["cash_events"], "quantity_policy": "fleet availability is not billed tail/base-month quantity; derive billing from identified contracts; no inferred fuel tonnes or MTOW"}
