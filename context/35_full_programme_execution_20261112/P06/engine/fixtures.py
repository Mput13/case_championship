"""Synthetic fixtures ONLY. None of these values are Red Wings estimates."""
import copy
import math
from .core import seal
from .finance import COVERAGE

TOY = "P06-TOY"


def blank(programme="P", eid=None):
    b = {
        "context": {"evaluation_id": eid or programme + "-toy", "programme_id": programme, "programme_version": "synthetic-v1", "fleet_scope_id": "CASE_SJ", "external_scenario_id": "toy-base", "delivery_calendar_id": "toy-phased", "market_version": "toy-potential-v1", "choice_version": "toy-logit-v1", "cost_version": "toy-events-v1", "response_policy_id": "toy-no-response", "evaluation_mode": "fixed_programme", "decision_date": "2026-11-12", "information_set_id": "toy-information", "keep_evaluation_id": "KEEP-toy", "input_manifest_sha256": "", "period_start": "2027-01", "period_end": "2028-12", "cash_start": "2026-12", "price_year": 2027, "affected_scope_id": "all-toy-affected"},
        "input_manifest": [{"source_id": "SYNTHETIC_TEST_ONLY", "commit": "b7d74e67dd6c603db049b1915b1afec987e3b458", "path": "P00R/counterexample_inputs.json", "sha256": "0" * 64}],
        "markets": [], "products": [], "flights": [], "fleet_calendar": [], "assignments": [], "contracts": [], "economic_events": [], "cash_events": [], "opening_balances": [],
        "assumptions": [{"assumption_id": TOY, "value": "all numeric values and explicit zero/inapplicability in synthetic bundle", "unit": "see each field", "selected_by": "P06 implementation agent", "basis": "P00R minimal counterexamples and independently constructed boundary checks; not market calibration", "approval_status": "synthetic_test_not_user_approved_RW_parameter", "range_or_unknown": "UNKNOWN for real RW", "affected_conclusions": "software invariants only", "sensitivity": "specific CE perturbations", "refinement": "replace with pinned P02/P03/P04/P05 inputs and source-specific assumption IDs"}],
        "choice_model": {"price_per_rub": 0, "time_per_minute": 0, "log_frequency": 0, "assumption_id": TOY, "calibration_status": "SYNTHETIC_NOT_CALIBRATED"},
        "response_policy": {"response_policy_id": "toy-no-response", "rules": [], "assumption_id": TOY},
        "cost_coverage": {k: {"status": "not_applicable", "event_ids": [], "rationale": "explicit zero ONLY in isolated synthetic test", "assumption_id": TOY} for k in COVERAGE},
        "cash_coverage": {k: "explicit" for k in ("operating", "investing", "tax", "financing")},
        "cash_policy": {"opening_cash": 0, "minimum_cash": 0, "project_opening_cash": 0, "project_minimum_cash": 0, "assumption_id": TOY},
        "resource_operators": [], "accounting_policy": "operating_aircraft_use_excludes_interest",
        "information_set": {"information_set_id": "toy-information", "facts": [{"fact_id": "toy-observation", "available_at": "2026-11-01"}]},
        "keep_policy": {"keep_policy_id": "toy-future-KEEP", "future_period": ["2027-01", "2028-12"], "resource_policy": "same committed availability", "existing_business": "explicit whole affected toy set", "alternative_new_resource_use": "explicit KEEP products", "excluded_unaffected_scope": "none in toy", "avoidable_cost_rules": "events in each bundle", "assumption_id": TOY},
        "programme_target": {"branch": "mechanical_test", "rationale": "small fixture not candidate network", "assumption_id": TOY}, "metric_adapter": None,
    }
    return seal(b)


def market(b, pool="AB", demand=100, m="2027-01"):
    b["markets"].append({"demand_pool_id": pool, "month": m, "customer_segment": "all", "potential_journeys": demand, "market_basis": "potential_travel", "mapping_to_potential": "synthetic mutually exclusive demand", "source_id": "SYNTHETIC", "source_period": m, "as_of": "2026-11-12", "coverage": "toy only", "status": "scenario", "assumption_id": TOY})
    return b


def flight(b, fid="AB1", origin="AAA", dest="BBB", dep="2027-01-02T08:00:00Z", arr="2027-01-02T10:00:00Z", seats=100):
    f = {"flight_instance_id": fid, "schedule_id": "toy", "operator": "TEST", "flight_number": fid, "origin_airport": origin, "destination_airport": dest, "departure_utc": dep, "arrival_utc": arr, "aircraft_variant": "SSJ100_analogue_TEST_ONLY", "seats": seats, "technical_blocked_seats": 0, "saleable_seats": seats, "physical_adjacent_leg": True, "scheduled_status": "proposed", "source_status": "scenario", "source_period": "2027-2028", "assumption_id": TOY, "distance_km": 1000, "project_network": True}
    b["flights"].append(f)
    return f


def product(b, pid="RW", pool="AB", owner="RW", legs=None, fare=100, weight=1, committed=0, capacity=None, m="2027-01", contract_only=False):
    legs = [] if legs is None else legs
    p = {"product_id": pid, "demand_pool_id": pool, "month": m, "customer_segment": "all", "kind": "air" if legs else "ground", "owner": owner, "gross_fare": fare, "net_fare": fare, "fare_unit": "RUB/journey", "duration_minutes": 120, "frequency": 1, "availability": True, "capacity": capacity, "legs": legs, "departure_date": m + "-02", "min_connection_minutes": 45, "max_connection_minutes": 180, "revenue_weights": ([1 / len(legs)] * len(legs) if legs else []), "committed_sales": committed, "contract_only": contract_only, "cash_profile": [{"date": m + "-02", "fraction": 1}], "assumption_id": TOY, "intercept": math.log(weight), "source_id": "SYNTHETIC"}
    b["products"].append(p)
    return p


def outside(b, pool="AB", weight=1, m="2027-01"):
    p = product(b, "outside:" + pool + ":" + m, pool, "OTHER", fare=0, weight=weight, m=m)
    p["kind"] = "outside"
    return p


def event(b, eid, category, amount, m="2027-01", payments=None, noncash=False):
    e = {"economic_event_id": eid, "owner": eid, "category": category, "scope": "affected_business", "driver_unit": "explicit_event", "quantity": 1, "rate": amount, "amount": amount, "currency": "RUB", "price_year": 2027, "fx_policy": "RUB_input", "accrual_month": m, "noncash": noncash, "avoidability": "explicit_scenario", "shared_event_id": eid, "source_id": "SYNTHETIC", "assumption_id": TOY, "cash_plan_status": "explicit"}
    if payments is not None:
        e["payments"] = payments
    b["economic_events"].append(e)
    key = "base" if category == "operating_fixed" else category
    if key in b["cost_coverage"]:
        b["cost_coverage"][key].update(status="explicit", rationale="toy event")
        b["cost_coverage"][key]["event_ids"].append(eid)
    return e


def cash(b, cid, amount, date, category="operating", eid=None, deposit=False, asset=None):
    e = {"cash_event_id": cid, "economic_event_id": eid, "related_asset_or_contract_id": asset or cid, "payment_date": date, "amount_signed": amount, "category": category, "currency": "RUB", "fx_at_payment": 1, "deposit_flag": deposit, "source_id": "SYNTHETIC", "status": "scenario", "assumption_id": TOY}
    b["cash_events"].append(e)
    return e


def tail(b, tid="T1", location="AAA"):
    t = {"aircraft_id": tid, "variant": "SSJ100_analogue_TEST_ONLY", "transfer_date": "2026-12-01T00:00:00Z", "service_entry_date": "2027-01-01T00:00:00Z", "available_from": "2027-01-01T00:00:00Z", "available_to": "2029-01-01T00:00:00Z", "initial_location": location, "turn_minutes": 30, "reserve_intervals": [], "maintenance_intervals": [], "crew_windows": [{"crew_id": "crew:" + tid, "start": "2027-01-01T00:00:00Z", "end": "2029-01-01T00:00:00Z"}], "max_daily_block_hours": 8, "assumption_id": TOY}
    b["fleet_calendar"].append(t)
    b["resource_operators"] = ["TEST"]
    return t


def assignment(b, fid, tid="T1"):
    b["assignments"].append({"flight_instance_id": fid, "aircraft_id": tid, "crew_id": "crew:" + tid, "action": "add", "assumption_id": TOY})


def demo():
    k = blank("KEEP")
    market(k, demand=200)
    market(k, "AC", 100)
    outside(k)
    outside(k, "AC")
    flight(k)
    tail(k)
    assignment(k, "AB1")
    product(k, legs=["AB1"], fare=4000, weight=4)
    event(k, "T1-use-Jan", "aircraft_use", 80000, payments=[{"date": "2027-01-01", "fraction": 1}])["committed_at"] = "2026-11-01"
    event(k, "flight-AB", "variable_cost", 100000, payments=[{"date": "2027-01-02", "fraction": 1}])
    k["choice_model"].update(price_per_rub=-0.0001, time_per_minute=-0.001, log_frequency=0.5)
    p = copy.deepcopy(k)
    p["context"].update(evaluation_id="P-toy", programme_id="P")
    flight(p, "BC1", "BBB", "CCC", "2027-01-02T11:00:00Z", "2027-01-02T13:00:00Z")
    assignment(p, "BC1")
    product(p, "THROUGH", "AC", legs=["AB1", "BC1"], fare=6500, weight=4)["duration_minutes"] = 300
    event(p, "flight-BC", "variable_cost", 100000, payments=[{"date": "2027-01-02", "fraction": 1}])
    event(p, "startup", "startup", 50000, "2026-12", [{"date": "2026-12-15", "fraction": 1}])
    cash(p, "deposit", -20000, "2026-12-15", "investing", deposit=True, asset="launch-deposit")
    cash(p, "deposit-return", 20000, "2029-01-15", "investing", deposit=True, asset="launch-deposit")
    return {"project": seal(p), "keep": seal(k)}
