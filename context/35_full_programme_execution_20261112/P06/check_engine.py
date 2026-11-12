"""Addressed counterexamples through actual engine functions; no review calculator.

Run from any cwd: python3 <P06>/check_engine.py [CE01 ...]. Full first run; after a
finding pass affected IDs only. Records preserve which selection actually ran.
"""
import copy
import json
import math
import hashlib
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path
from engine import evaluate, compare, scenario, combine, seal
from engine.common import ContractError, digest
from engine.fixtures import blank, market, flight, product, outside, event, cash, tail, assignment, demo, TOY
from engine.finance import funding

ROOT = Path(__file__).resolve().parent
TESTS = {}


def test(name):
    def bind(fn):
        TESTS[name] = fn
        return fn
    return bind


def close(actual, expected):
    assert actual is not None and math.isclose(actual, expected, abs_tol=1e-6, rel_tol=1e-9), (actual, expected)


def rejects(fn, fragment):
    try:
        fn()
    except (ContractError, ValueError) as e:
        assert fragment.lower() in str(e).lower(), str(e)
        return {"rejected": True, "error": str(e)}
    raise AssertionError("Expected rejection: " + fragment)


def carried(q=50, legs=1, fare=100, programme="P"):
    b = blank(programme)
    market(b, demand=200)
    outside(b)
    ids = []
    for i in range(legs):
        fid = "leg" + str(i)
        flight(b, fid, ["AAA", "BBB", "CCC"][i], ["BBB", "CCC", "DDD"][i], f"2027-01-02T{8+i*3:02d}:00:00Z", f"2027-01-02T{10+i*3:02d}:00:00Z", seats=500)
        ids.append(fid)
    product(b, legs=ids, fare=fare, committed=q, contract_only=True)
    return b


@test("CE01")
def ce01():
    k, p = carried(120, programme="KEEP"), carried(130)
    r = compare(p, k)
    close(r["delta_summary"]["journeys"], 10)
    return {"delta": r["delta_summary"]["journeys"], "historical_input_not_used": 100}


@test("CE02")
def ce02():
    p = blank(); a = copy.deepcopy(p)
    a["context"].update(evaluation_id="P-adapted", evaluation_mode="feasible_adaptation_with_existing_commitments")
    a["adaptation"] = {"parent_evaluation_id": "P-toy", "parent_bundle_sha256": digest(p), "actions": [], "preserved_commitment_ids": [], "assumption_id": TOY}
    r = scenario([p, a], {"P-toy": p})
    assert len({e["context"]["evaluation_id"] for e in r["evaluations"]}) == 2
    return {"distinct_records": 2, "rows": sum(len(e["results_monthly"]) for e in r["evaluations"])}


@test("CE03")
def ce03():
    b = blank(); flight(b); flight(b, "other", "AAA", "CCC", "2027-01-02T08:30:00Z", "2027-01-02T10:30:00Z")
    tail(b); t2 = tail(b, "RESERVE"); t2["reserve_intervals"] = [["2027-01-01T00:00:00Z", "2029-01-01T00:00:00Z"]]
    assignment(b, "AB1"); assignment(b, "other")
    r = evaluate(b)
    assert r["status"] == "INFEASIBLE" and any("overlapping" in s for s in r["operations"]["errors"])
    return {"feasible": False, "errors": r["operations"]["errors"]}


@test("CE04")
def ce04():
    b = carried(10, 2)
    b["flights"][1]["departure_utc"] = "2027-01-03T11:00:00Z"
    b["flights"][1]["arrival_utc"] = "2027-01-03T13:00:00Z"
    return rejects(lambda: evaluate(b), "1500")


@test("CE05")
def ce05():
    b = blank(); market(b, demand=70); market(b, "AC", 50)
    outside(b); out = outside(b, "AC"); out["intercept"] = -1000
    flight(b); flight(b, "BC1", "BBB", "CCC", "2027-01-02T11:00:00Z", "2027-01-02T13:00:00Z")
    product(b, "local", legs=["AB1"], fare=4000, committed=70, contract_only=True)
    product(b, "through", "AC", legs=["AB1", "BC1"], fare=9000)
    r = evaluate(b); loads = {s["flight_instance_id"]: s["carried_segments"] for s in r["allocation"]["seats"]}
    close(loads["AB1"], 100); close(loads["BC1"], 30)
    close(r["summary"]["journeys"], 100); close(r["summary"]["passenger_segments"], 130); close(r["summary"]["revenue_net"], 550000)
    return {"ab_load": loads["AB1"], "bc_load": loads["BC1"], **r["summary"]}


@test("CE06")
def ce06():
    r = evaluate(carried(10, 2, 9000))
    close(r["summary"]["revenue_net"], 90000); close(r["summary"]["passenger_segments"], 20)
    return r["summary"]


def weighted(weights):
    b = blank(); market(b)
    for i, (owner, w) in enumerate(weights):
        product(b, str(i), owner=owner, weight=w, capacity=100)
    return b


@test("CE07")
def ce07():
    one = evaluate(weighted([("RW", 6), ("OTHER", 4)]))
    joint = evaluate(weighted([("RW", 6), ("RW", 6), ("OTHER", 4)]))
    close(one["summary"]["journeys"], 60); close(joint["summary"]["journeys"], 75)
    return {"standalone_each": one["summary"]["journeys"], "sum_standalone": 2 * one["summary"]["journeys"], "joint_rw": joint["summary"]["journeys"]}


@test("CE08")
def ce08():
    b = weighted([("RW", 4), ("OTHER", 4)]); outside(b, weight=2)
    before = evaluate(b)["summary"]["journeys"]
    b["products"][1]["intercept"] = math.log(8)
    after = evaluate(b)["summary"]["journeys"]
    close(before, 40); close(after, 200 / 7)
    return {"rw_before": before, "rw_after": after}


@test("CE09")
def ce09():
    r = compare(carried(50, 2), carried(50, 1, programme="KEEP"))
    close(r["delta_summary"]["journeys"], 0); close(r["delta_summary"]["passenger_segments"], 50)
    assert r["delta_annual"][0]["delta_share_pp"] is None
    return r["delta_annual"][0]


@test("CE10")
def ce10():
    b = weighted([("RW", 6), ("RW", 4)])
    r = evaluate(b)
    close(r["summary"]["journeys"], 100)
    q = [a["carried"] for a in r["allocation"]["allocations"]]
    close(q[0], 60); close(q[1], 40)
    b["markets"].append(copy.deepcopy(b["markets"][0]))
    rejects(lambda: evaluate(b), "duplicate demand")
    return {"total_allocated": sum(q), "allocations": q, "duplicate_pool_rejected": True}


@test("CE11")
def ce11():
    k, p = blank("KEEP"), blank()
    event(k, "old-revenue", "revenue", 100); event(k, "old-cost", "variable_cost", 60)
    event(p, "old-revenue", "revenue", 70); event(p, "old-cost", "variable_cost", 50)
    event(p, "new-revenue", "revenue", 80); event(p, "new-cost", "variable_cost", 40)
    r = compare(p, k)
    close(r["delta_summary"]["operating_result"], 20)
    return {"keep_result": r["keep"]["summary"]["operating_result"], "project_result": r["project"]["summary"]["operating_result"], "delta_result": r["delta_summary"]["operating_result"]}


@test("CE12")
def ce12():
    b = blank()
    for eid, cat, amount in [("a", "revenue", 80), ("b", "revenue", 70), ("ca", "variable_cost", 40), ("cb", "variable_cost", 40), ("base", "operating_fixed", 30)]:
        event(b, eid, cat, amount)
    r = evaluate(b); close(r["summary"]["operating_result"], 40)
    b["economic_events"].append(dict(b["economic_events"][-1], economic_event_id="base-copy"))
    rejects(lambda: evaluate(b), "duplicate")
    return {"joint_result": r["summary"]["operating_result"], "duplicate_shared_event_rejected": True}


def cash_example():
    b = blank()
    for eid, cat, amount, noncash in [("ticket", "revenue", 100, False), ("support", "support", 30, False), ("fuel", "variable_cost", 60, False), ("base", "operating_fixed", 20, False), ("startup", "startup", 30, False), ("depreciation", "depreciation", 10, True)]:
        event(b, eid, cat, amount, noncash=noncash)
    cash(b, "capex", -60, "2026-12-01", "investing")
    cash(b, "deposit", -50, "2026-12-01", "investing", deposit=True, asset="deposit")
    cash(b, "ticket1", 80, "2027-01-31", eid="ticket")
    cash(b, "fuel", -60, "2027-01-01", eid="fuel")
    cash(b, "base", -20, "2027-01-01", eid="base")
    cash(b, "startup", -30, "2027-01-01", eid="startup")
    cash(b, "ticket2", 20, "2027-02-28", eid="ticket")
    cash(b, "support", 30, "2027-03-31", eid="support")
    cash(b, "deposit-return", 50, "2027-03-31", "investing", deposit=True, asset="deposit")
    return b


@test("CE13")
def ce13():
    r = evaluate(cash_example()); f = r["finance"]["funding"]
    close(r["summary"]["operating_result"], 10)
    assert [x["cash_before_financing"] for x in f["monthly"][:4]] == [-110, -30, 20, 80]
    close(f["peak_month_end"], 140)
    close(f["monthly"][3]["cumulative_cash_before_financing"], -40)
    assert all(x["signed_balance"] == 0 for x in r["finance"]["terminal"]["balances"])
    return {"operating_result": 10, "cash_before_financing": [x["cash_before_financing"] for x in f["monthly"][:4]], "peak_funding_month_end": f["peak_month_end"], "terminal_shortfall": 40}


@test("CE14")
def ce14():
    b = blank(); fuel = event(b, "fuel", "variable_cost", 100, payments=[{"date": "2027-01-01", "fraction": 1}])
    support = event(b, "support", "support", 20, payments=[{"date": "2027-03-01", "fraction": 1}]); support["support_scheme_id"] = "S"
    r = evaluate(b); close(r["summary"]["operating_result"], -80)
    assert r["results_monthly"][0]["operating_cash"] == -100 and r["results_monthly"][2]["operating_cash"] == 20
    fuel["net_of_support_scheme_id"] = "S"
    rejects(lambda: evaluate(b), "double recognition")
    return {"net_expense": 80, "cash_m1": -100, "cash_m3": 20, "double_support_rejected": True}


@test("CE15")
def ce15():
    k, p = blank("KEEP"), blank()
    event(p, "known", "revenue", 20); event(p, "missing", "operating_fixed", None)
    r = compare(p, k)
    assert r["delta_summary"]["operating_result"] is None
    close(r["thresholds"]["net_missing_operating_cost_break_even"], 20)
    return {"full_delta": None, "break_even_missing_cost": r["thresholds"]["net_missing_operating_cost_break_even"]}


@test("CE16")
def ce16():
    k, p = carried(10, programme="KEEP"), carried(20)
    for b, den in [(k, 100), (p, 110)]:
        b["metric_adapter"] = {"metric_definition_id": "toy-journey", "source_id": "SYNTHETIC", "reporting_rule": "journeys", "carrier_vs_group": "carrier", "business_scope": "toy all", "denominator_policy": "endogenous_project_market", "denominators": {"2027": {"year": 2027, "metric_definition_id": "toy-journey", "value": den, "denominator_id": str(den)}}, "assumption_id": TOY}
    r = compare(p, k); close(r["delta_annual"][0]["delta_share_pp"], 100 * (20 / 110 - 10 / 100))
    return r["delta_annual"][0]


@test("CE17")
def ce17():
    b = blank(); q = {}
    for week in range(52):
        d = date(2027, 1, 4) + timedelta(days=7 * week)
        q[d.strftime("%Y-%m")] = q.get(d.strftime("%Y-%m"), 0) + (100 if week < 10 else 20)
    for m, n in q.items():
        market(b, demand=n, m=m); outside(b, m=m)
        product(b, "p:" + m, capacity=n, committed=n, contract_only=True, m=m)
    r = evaluate(b); close(r["results_annual"][0]["journeys"], 1840)
    assert len(r["results_monthly"]) == 24
    return {"annual_pax": r["results_annual"][0]["journeys"], "explicit_monthly_journeys": q}


@test("CE18")
def ce18():
    r = evaluate(cash_example())["finance"]["funding"]
    close(r["peak_month_end"], 140); close(r["peak_dated_day_end"], 220)
    return {"month_end_funding": r["peak_month_end"], "event_order_funding": r["peak_dated_day_end"], "precision": r["timing_status"]}


@test("CE19")
def ce19():
    b = blank(); event(b, "contribution", "revenue", 100)
    before = evaluate(b)
    tail(b, "unused"); event(b, "committed-idle-lease", "aircraft_use", 20)
    after = evaluate(b)
    assert after["operations"]["unused_aircraft"] == ["unused"]
    close(after["summary"]["operating_result"], 80)
    return {"larger_feasible_set_keeps_candidate": not after["operations"]["errors"], "new_result_after_extra_commitment": after["summary"]["operating_result"], "previous": before["summary"]["operating_result"]}


@test("CE20")
def ce20():
    from engine.adapters import yield_to_fare
    fare = yield_to_fare(2, 1000, "journey_distance_km")
    r = evaluate(carried(10, 1, fare)); close(r["summary"]["revenue_net"], 20000)
    b = carried(); b["products"][-1]["fare_unit"] = "RUB/pax-km"
    rejects(lambda: evaluate(b), "convert yield")
    return {"revenue": r["summary"]["revenue_net"], "unconverted_yield_rejected": True}


@test("B01_price_time_frequency_availability")
def b01():
    b = weighted([("RW", 4), ("OTHER", 4)]); outside(b, weight=2)
    b["choice_model"].update(price_per_rub=-0.01, time_per_minute=-0.01, log_frequency=1)
    base = evaluate(b)["summary"]["journeys"]
    values = {}
    for key, value in [("gross_fare", 200), ("duration_minutes", 240), ("frequency", 0.5), ("availability", False)]:
        a = copy.deepcopy(b); a["products"][0][key] = value
        values[key] = evaluate(a)["summary"]["journeys"]
        assert values[key] < base
    return {"base": base, "perturbations": values}


@test("B02_contract_block_and_release")
def b02():
    b = blank(); market(b, demand=120); outside(b)["intercept"] = -1000; flight(b)
    product(b, "retail", legs=["AB1"], fare=10)
    product(b, "contract", legs=["AB1"], fare=0, contract_only=True)
    ev = event(b, "block-payment", "revenue", 500); ev["owner"] = "C"
    b["contracts"] = [{"contract_id": "C", "product_id": "contract", "reserved_seats": 40, "carried": 30, "release_unused": False, "payment_mode": "block", "economic_event_id": "block-payment", "assumption_id": TOY}]
    r = evaluate(b); close(r["summary"]["journeys"], 90); close(r["summary"]["revenue_net"], 1100)
    close(r["allocation"]["seats"][0]["unfilled_contract_seats"], 10)
    b["contracts"][0]["release_unused"] = True
    rr = evaluate(b); close(rr["summary"]["journeys"], 100); close(rr["summary"]["revenue_net"], 1200)
    b["products"][-1]["net_fare"] = 10
    rejects(lambda: evaluate(b), "duplicate revenue")
    return {"held_journeys": 90, "released_journeys": 100, "block_duplicate_rejected": True}


@test("B03_resource_entry_reserve_position_crew")
def b03():
    b = blank(); flight(b); tail(b); assignment(b, "AB1")
    results = {}
    for name, change in [("entry", {"service_entry_date": "2027-02-01T00:00:00Z"}), ("position", {"initial_location": "CCC"}), ("reserve", {"reserve_intervals": [["2027-01-01T00:00:00Z", "2027-02-01T00:00:00Z"]]}), ("maintenance", {"maintenance_intervals": [["2027-01-02T09:00:00Z", "2027-01-02T10:00:00Z"]]}), ("crew", {"crew_windows": []})]:
        a = copy.deepcopy(b); a["fleet_calendar"][0].update(change)
        r = evaluate(a); assert r["status"] == "INFEASIBLE"; results[name] = r["operations"]["errors"]
    return results


@test("B04_immutable_context")
def b04():
    b = demo(); before = digest(b)
    compare(b["project"], b["keep"]); assert digest(b) == before
    b["project"]["context"]["external_scenario_id"] = "different"
    rejects(lambda: compare(b["project"], b["keep"]), "mismatch")
    b["project"]["context"]["input_manifest_sha256"] = "wrong"
    rejects(lambda: evaluate(b["project"]), "hash mismatch")
    return {"no_mutation": True, "mismatched_context_rejected": True}


@test("B05_unknown_money_and_company")
def b05():
    b = demo(); b["project"]["economic_events"][0]["rate"] = None; b["project"]["economic_events"][0]["amount"] = None
    r = compare(b["project"], b["keep"])
    assert r["delta_summary"]["operating_result"] is None and r["project_incremental_funding"]["peak_month_end"] is None
    assert r["whole_company_funding"] is None
    return {"delta": None, "funding": None, "company_funding": None}


@test("B06_opening_minimum_financing")
def b06():
    b = blank(); b["cash_policy"].update(opening_cash=20, minimum_cash=15)
    cash(b, "pay", -50, "2026-12-01"); cash(b, "loan", 1000, "2026-12-01", "financing")
    r = evaluate(b); close(r["finance"]["funding"]["peak_month_end"], 45); close(r["finance"]["funding"]["monthly"][0]["closing_cash"], 970)
    close(r["summary"]["revenue_net"], 0)
    return {"need_before_financing": 45, "close_after_financing": 970, "loan_not_revenue": True}


@test("B07_terminal_and_prelaunch")
def b07():
    b = blank(); event(b, "startup", "startup", 30, "2026-12", [{"date": "2026-12-01", "fraction": 1}])
    event(b, "late-revenue", "revenue", 50, "2028-12", [{"date": "2029-02-01", "fraction": 1}])
    event(b, "exit-obligation", "exit", 70, "2029-01", [{"date": "2029-01-31", "fraction": 1}])
    r = evaluate(b); close(r["summary"]["operating_result"], 50); close(r["summary"]["operating_result_including_prelaunch"], 20)
    term = r["finance"]["terminal"]
    close(next(x["signed_balance"] for x in term["balances"] if x["economic_event_id"] == "late-revenue"), 50)
    assert len(term["future_cash_events"]) == 2 and len(term["future_economic_obligations"]) == 1
    return {"period_result": 50, "including_prelaunch": 20, "receivable": 50, "future_obligation": 70}


@test("B08_adaptation_no_future_or_erased_commitments")
def b08():
    p = blank(); event(p, "lease", "aircraft_use", 20)["committed_at"] = "2026-11-01"
    a = copy.deepcopy(p); a["context"].update(evaluation_id="adaptive", evaluation_mode="feasible_adaptation_with_existing_commitments")
    a["adaptation"] = {"parent_evaluation_id": "P-toy", "parent_bundle_sha256": digest(p), "actions": [], "preserved_commitment_ids": ["lease"], "assumption_id": TOY}
    scenario([a], {"P-toy": p})
    a["economic_events"] = []
    rejects(lambda: scenario([a], {"P-toy": p}), "commitment")
    a = copy.deepcopy(p); a["information_set"]["facts"][0]["available_at"] = "2028-01-01"
    rejects(lambda: evaluate(a), "future information")
    return {"feasible_adaptation_runs": True, "commitment_deletion_rejected": True, "future_information_rejected": True}


@test("B09_joint_combine_recompute")
def b09():
    b = weighted([("OTHER", 4)])
    add = blank(); product(add, "a", weight=6, capacity=100)
    add2 = blank(); product(add2, "b", weight=6, capacity=100)
    combined = combine(b, [{"base_bundle_sha256": digest(b), "products": add["products"]}, {"base_bundle_sha256": digest(b), "products": add2["products"]}], dict(b["context"], evaluation_id="joint"))
    r = evaluate(combined); close(r["summary"]["journeys"], 75)
    return {"joint_rw": r["summary"]["journeys"]}


@test("B10_response_policy_is_executed")
def b10():
    b = weighted([("RW", 4), ("OTHER", 4)]); outside(b, weight=2)
    b["choice_model"]["price_per_rub"] = -0.01
    before = evaluate(b)["summary"]["journeys"]
    b["response_policy"]["rules"] = [{"demand_pool_id": "AB", "month": "2027-01", "customer_segment": "all", "rw_frequency_at_least": 1, "target_product_ids": ["1"], "gross_fare_multiplier": 0.5, "frequency_multiplier": 1, "intercept_delta": 0, "assumption_id": TOY}]
    after = evaluate(b)["summary"]["journeys"]
    assert after < before
    return {"before_response": before, "after_competitor_price_cut": after}


@test("B11_interest_and_preinterest")
def b11():
    b = blank(); event(b, "op", "revenue", 100, payments=[{"date": "2027-01-01", "fraction": 1}])
    event(b, "interest", "interest", 30)
    cash(b, "interest", -30, "2027-01-01", eid="interest")
    r = evaluate(b); close(r["summary"]["operating_result"], 100)
    row = r["results_monthly"][0]
    close(row["cash_before_financing"], 70); close(row["pre_interest_cash_diagnostic"], 100); close(row["finance_interest_cash"], -30)
    b["cash_coverage"]["finance_interest"] = "unknown"
    u = evaluate(b)
    assert u["summary"]["cash_before_financing"] is None and u["finance"]["funding"]["peak_month_end"] is None
    close(u["results_monthly"][0]["pre_interest_cash_diagnostic"], 100)
    return {"operating_result": 100, "cash_including_interest": 70, "pre_interest_cash": 100, "unknown_interest_full_cash": None}


@test("B12_unknown_financing_does_not_erase_prefinancing_cash")
def b12():
    b = blank(); cash(b, "pay", -50, "2027-01-01")
    b["cash_coverage"]["financing"] = "unknown"
    r = evaluate(b)
    close(r["results_monthly"][0]["cash_before_financing"], -50)
    close(r["finance"]["funding"]["peak_month_end"], 50)
    assert r["results_monthly"][0]["closing_cash"] is None
    return {"cash_before_financing": -50, "funding_before_financing": 50, "closing_cash": None}


@test("B13_adaptive_direct_bypass_rejected")
def b13():
    p = blank(); a = copy.deepcopy(p)
    a["context"].update(evaluation_id="adaptive", evaluation_mode="feasible_adaptation_with_existing_commitments")
    a["adaptation"] = {"parent_evaluation_id": "P-toy", "parent_bundle_sha256": digest(p), "actions": [], "preserved_commitment_ids": [], "assumption_id": TOY}
    return rejects(lambda: evaluate(a), "exact parent")


@test("B14_revenue_by_leg_and_actual_service_month")
def b14():
    b = carried(10, 2, 9000)
    r = evaluate(b)
    d = r["cost_driver_exports"]["physical_flights"]
    close(sum(x["allocated_journey_revenue"] for x in d), 90000)
    close(sum(x["occupied_segments"] for x in d), 20)
    return {"leg_revenues": [x["allocated_journey_revenue"] for x in d], "total_journey_revenue": r["summary"]["revenue_net"]}


@test("B15_unknown_choice_not_zero")
def b15():
    b = carried(); b["products"][-1]["availability"] = None
    r = evaluate(b)
    assert r["summary"]["journeys"] is None and r["summary"]["revenue_net"] is None
    assert r["unknown_dependencies"]
    return {"journeys": None, "revenue": None, "unknowns": r["unknown_dependencies"]}


@test("B16_committed_excess_and_malformed_inventory")
def b16():
    b = carried(150); b["flights"][0].update(seats=100, saleable_seats=100)
    rejects(lambda: evaluate(b), "exceed inventory")
    b = carried(); b["flights"][0]["physical_adjacent_leg"] = False
    rejects(lambda: evaluate(b), "physical adjacency")
    b = carried(); b["flights"][0]["origin_airport"] = "MOW"
    rejects(lambda: evaluate(b), "MOW")
    return {"excess_committed_rejected": True, "marketing_pair_rejected": True, "MOW_rejected": True}


@test("B17_company_boundary")
def b17():
    p, k = blank(), blank("KEEP")
    cash(p, "cost", -20, "2027-01-01")
    bk = blank(); cash(bk, "existing", -100, "2027-01-01")
    company = {"keep_evaluation_id": "KEEP-toy", "scope": "whole_company_including_affected_keep", "cash_events": bk["cash_events"], "opening_cash": 10, "minimum_cash": 5}
    r = compare(p, k, company)
    close(r["project_incremental_funding"]["peak_month_end"], 20); close(r["whole_company_funding"]["peak_month_end"], 115)
    return {"project_funding": 20, "company_funding": 115}


@test("B18_pinned_adapters")
def b18():
    from engine.adapters import csv_rows, p02_evidence, p04_rate_catalog
    rows = csv_rows(ROOT / "inputs/P02_calendar_inventory.csv")
    r = p02_evidence(rows, csv_rows(ROOT / "inputs/P02_competitor_products.csv"), json.loads((ROOT / "correction_lineage.json").read_text()))
    assert len(r["clock_conflicts"]) == 30 and r["unknown_physical_inventory_count"] == len(rows) and not r["admitted_engine_flights"]
    rates = p04_rate_catalog(csv_rows(ROOT / "inputs/P04_cost_ranges.csv"))
    assert len(rates) == 127 and all(x["future_rate"] is None for x in rates)
    v2 = p02_evidence(csv_rows(ROOT / "inputs/P02v2_calendar_inventory.csv"), csv_rows(ROOT / "inputs/P02v2_alternatives_contract.csv"), r["correction_lineage"])
    assert not v2["admitted_engine_flights"] and len(v2["clock_conflicts"]) == 30
    return {"clock_conflicts_preserved_v1_and_v2": 30, "physical_arcs_admitted": 0, "v2_source_instances": v2["source_rows"], "p04_rates": len(rates), "automatic_future_rates": 0}


@test("B19_month_coverage_and_nan")
def b19():
    b = carried(); b["market_calendar"][0]["zero_months"].remove("2027-02")
    rejects(lambda: evaluate(b), "24 months")
    b["market_calendar"][0]["unknown_months"] = ["2027-02"]
    assert evaluate(b)["summary"]["journeys"] is None
    b = carried(); b["markets"][0]["potential_journeys"] = float("nan")
    rejects(lambda: evaluate(b), "finite number")
    return {"missing_month_rejected": True, "unknown_month_preserved": True, "NaN_invalid_not_unknown": True}


@test("B20_cash_bridge_and_duplicate_ticket")
def b20():
    r = evaluate(cash_example())
    bridge = r["finance"]["accrual_cash_bridge"]
    close(bridge["operating_cash_from_accrual"], 20); close(bridge["residual"], 0)
    b = carried(); event(b, "duplicate", "revenue", 5000)["owner"] = "RW"
    rejects(lambda: evaluate(b), "duplicates generated")
    return {"bridge": bridge, "manual_duplicate_fare_rejected": True}


@test("B21_adaptation_actual_action_binding")
def b21():
    p = carried(); a = copy.deepcopy(p)
    a["context"].update(evaluation_id="adaptive", evaluation_mode="feasible_adaptation_with_existing_commitments")
    a["adaptation"] = {"parent_evaluation_id": "P-toy", "parent_bundle_sha256": digest(p), "actions": [], "preserved_commitment_ids": [], "assumption_id": TOY}
    a["products"][-1]["gross_fare"] = 110
    rejects(lambda: evaluate(a, p), "lacks action")
    a["adaptation"]["actions"] = [{"table": "products", "record_id": "RW", "action": "replace", "decision_date": "2026-11-12", "effective_date": "2027-01-02", "based_on_fact_ids": ["toy-observation"], "assumption_id": TOY}]
    evaluate(a, p)
    altered = copy.deepcopy(p); altered["products"][-1]["net_fare"] = 999
    rejects(lambda: evaluate(a, altered), "parent hash")
    return {"unexplained_change_rejected": True, "documented_change_evaluated": True, "parent_substitution_rejected": True}


@test("B22_dated_minimum_cash")
def b22():
    from engine.common import months
    b = blank(); b["cash_policy"]["opening_cash"] = 20
    floors = {m: 5 for m in months("2026-12", "2028-12")}; floors["2027-06"] = 75
    b["cash_policy"]["minimum_cash"] = floors
    r = evaluate(b)
    close(r["finance"]["funding"]["peak_month_end"], 55); close(r["finance"]["funding"]["peak_dated_day_end"], 55)
    return {"no_payments_month_with_higher_floor_detected": True, "funding": 55}


def main():
    selection = sys.argv[1:] or list(TESTS)
    previous = ROOT / "mechanical_checks.json"
    old = json.loads(previous.read_text()) if previous.exists() else {}
    records = {x["check_id"]: x for x in old.get("checks", [])}
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "engine").glob("*.py"))}
    source_hashes["check_engine.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for name in selection:
        try:
            actual = TESTS[name]()
            record = {"check_id": name, "status": "PASS", "actual": actual}
        except Exception as e:
            record = {"check_id": name, "status": "FAIL", "error": str(e), "traceback": traceback.format_exc()}
        records[name] = record
        record["source_fingerprint"] = digest(source_hashes)
        print(name, record["status"], record.get("error", ""))
    payload = {"scope": "author mechanical checks through actual P06 engine; not independent acceptance", "synthetic_parameters_not_RW": True, "last_run_selection": selection, "source_hashes": source_hashes, "source_fingerprint": digest(source_hashes), "checks": list(records.values()), "pass": sum(r["status"] == "PASS" for r in records.values()), "fail": sum(r["status"] == "FAIL" for r in records.values()), "not_run": [k for k in TESTS if k not in records], "market_forecast_acceptance": "NOT_ASSESSED", "dispatch_acceptance": "NOT_ASSESSED"}
    previous.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    raise SystemExit(bool(payload["fail"]))


if __name__ == "__main__":
    main()
