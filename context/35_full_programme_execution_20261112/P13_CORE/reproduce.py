"""Независимые синтетические сценарии для exact P06; стандартная библиотека.

Запуск: PYTHONDONTWRITEBYTECODE=1 python3 <P13_CORE>/reproduce.py
Входные fixtures построены здесь независимо. Авторские проверки запускаются
отдельно и не входят в число независимых сценариев. Реальных оценок RW нет.
"""
import copy
import hashlib
import importlib.util
import json
import math
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "subject"))
from engine import evaluate, compare, seal, scenario, combine
from engine.choice import apply_response
from engine.common import ContractError, digest, months
from engine.finance import funding

SHA = "982f13d9b6c378ed9581125ecc5c40f17dade6a3"
AID = "P13-A001"
CASES = []


def save(path, value):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def base(programme="P"):
    contract_path = ROOT / "subject/producer_contract.json"
    b = {
        "context": {
            "evaluation_id": programme + "-independent", "programme_id": programme,
            "programme_version": "P13-synthetic-v1", "fleet_scope_id": "P13-SJ",
            "external_scenario_id": "P13-synthetic", "delivery_calendar_id": "P13-resource",
            "market_version": "P13-potential", "choice_version": "P13-zero-coefficients",
            "cost_version": "P13-event-values", "response_policy_id": "P13-policy",
            "evaluation_mode": "fixed_programme", "decision_date": "2026-11-12",
            "information_set_id": "P13-information", "keep_evaluation_id": "KEEP-independent",
            "input_manifest_sha256": "", "period_start": "2027-01", "period_end": "2028-12",
            "cash_start": "2026-12", "price_year": 2027, "affected_scope_id": "P13-complete-toy",
        },
        "markets": [], "market_calendar": [], "products": [], "flights": [],
        "fleet_calendar": [], "assignments": [], "contracts": [], "economic_events": [],
        "cash_events": [], "opening_balances": [],
        "assumptions": [{
            "assumption_id": AID, "value": "Все искусственные числа, нули, даты и допуски в P13",
            "unit": "Указана в полях; RUB, journeys, seats, UTC, minutes, block hours",
            "selected_by": "Независимый reviewer P13-CORE",
            "basis": "Аналитические граничные примеры для проверки инвариантов",
            "approval_status": "SYNTHETIC_TEST_ONLY",
            "range_or_unknown": "Для Red Wings UNKNOWN; не оценка рынка или доверительный интервал",
            "affected_conclusions": "Только корректность ядра на exact subject",
            "sensitivity": "Изменение одного поля и парные сценарии в reproduce.py",
            "refinement": "Реальные значения требуют принятого P02/P03/P04/P05, здесь не подбираются",
        }],
        "input_manifest": [{"source_id": "P06-CONTRACT", "commit": SHA,
                            "path": "context/35_full_programme_execution_20261112/P06/producer_contract.json",
                            "sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest()}],
        "choice_model": {"price_per_rub": 0, "time_per_minute": 0, "log_frequency": 0,
                         "assumption_id": AID, "calibration_status": "SYNTHETIC_NOT_CALIBRATED"},
        "response_policy": {"response_policy_id": "P13-policy", "rules": [], "assumption_id": AID},
        "cost_coverage": {k: {"status": "not_applicable", "event_ids": [],
                               "rationale": "Явное отсутствие только в этом синтетическом примере",
                               "assumption_id": AID}
                          for k in ("variable_cost", "base", "aircraft_use", "reserve", "startup", "exit", "support")},
        "cash_coverage": {k: "explicit" for k in ("operating", "investing", "tax", "financing", "finance_interest")},
        "cash_policy": {"opening_cash": 0, "minimum_cash": 0, "project_opening_cash": 0,
                        "project_minimum_cash": 0, "assumption_id": AID},
        "resource_operators": [], "accounting_policy": "operating_aircraft_use_excludes_interest",
        "information_set": {"information_set_id": "P13-information",
                            "facts": [{"fact_id": "P13-known", "available_at": "2026-11-01"}]},
        "keep_policy": {"keep_policy_id": "P13-future-KEEP", "future_period": ["2027-01", "2028-12"],
                        "resource_policy": "same available tails", "existing_business": "all affected toy business",
                        "alternative_new_resource_use": "explicit KEEP", "excluded_unaffected_scope": "none",
                        "avoidable_cost_rules": "explicit events", "assumption_id": AID},
        "programme_target": {"branch": "mechanical_test", "rationale": "Не проектная сеть RW", "assumption_id": AID},
        "metric_adapter": None,
    }
    return seal(b)


def market(b, pool="X", m="2027-01", segment="all", demand=100):
    cal = next((c for c in b["market_calendar"] if (c["demand_pool_id"], c["customer_segment"]) == (pool, segment)), None)
    if cal is None:
        cal = {"demand_pool_id": pool, "customer_segment": segment,
               "zero_months": months("2027-01", "2028-12"), "unknown_months": [], "assumption_id": AID}
        b["market_calendar"].append(cal)
    cal["zero_months"].remove(m)
    b["markets"].append({"demand_pool_id": pool, "month": m, "customer_segment": segment,
                         "potential_journeys": demand, "market_basis": "potential_travel",
                         "mapping_to_potential": "Взаимно исключённый искусственный рынок",
                         "source_id": "P13-SYNTHETIC", "source_period": m, "as_of": "2026-11-12",
                         "coverage": "Одна заданная ячейка; прочие месяцы явно нулевые",
                         "status": "scenario", "assumption_id": AID})


def product(b, pid, pool="X", m="2027-01", segment="all", owner="RW", legs=None,
            fare=100, committed=0, contract_only=False, outside=False):
    legs = legs or []
    p = {"product_id": pid, "demand_pool_id": pool, "month": m, "customer_segment": segment,
         "kind": "outside" if outside else "air" if legs else "ground", "owner": owner,
         "gross_fare": 0 if outside else fare, "net_fare": 0 if outside else fare,
         "fare_unit": "RUB/journey", "duration_minutes": 120, "frequency": 1,
         "availability": True, "capacity": None if outside or legs else 1000,
         "legs": legs, "departure_date": m + "-10", "min_connection_minutes": 30,
         "max_connection_minutes": 180, "revenue_weights": [1 / len(legs)] * len(legs) if legs else [],
         "committed_sales": committed, "contract_only": contract_only,
         "cash_profile": [{"date": m + "-10", "fraction": 1}], "assumption_id": AID,
         "intercept": 0, "source_id": "P13-SYNTHETIC"}
    b["products"].append(p)
    return p


def flight(b, fid, origin="AAA", dest="BBB", dep="2027-01-10T08:00:00Z", arr="2027-01-10T10:00:00Z", seats=50):
    f = {"flight_instance_id": fid, "schedule_id": "P13-dated", "operator": "TEST",
         "flight_number": fid, "origin_airport": origin, "destination_airport": dest,
         "departure_utc": dep, "arrival_utc": arr, "aircraft_variant": "SSJ100_TEST_ANALOGUE",
         "seats": seats, "technical_blocked_seats": 0, "saleable_seats": seats,
         "physical_adjacent_leg": True, "scheduled_status": "proposed", "source_status": "scenario",
         "source_period": "2027-2028", "assumption_id": AID, "distance_km": 500, "project_network": True}
    b["flights"].append(f)
    return f


def tail(b, tid="T", location="AAA"):
    t = {"aircraft_id": tid, "variant": "SSJ100_TEST_ANALOGUE", "transfer_date": "2026-12-01T00:00:00Z",
         "service_entry_date": "2027-01-01T00:00:00Z", "available_from": "2027-01-01T00:00:00Z",
         "available_to": "2029-01-01T00:00:00Z", "initial_location": location, "turn_minutes": 40,
         "reserve_intervals": [], "maintenance_intervals": [],
         "crew_windows": [{"crew_id": "C-" + tid, "start": "2027-01-01T00:00:00Z", "end": "2029-01-01T00:00:00Z"}],
         "max_daily_block_hours": 8, "assumption_id": AID}
    b["fleet_calendar"].append(t)
    b["resource_operators"] = ["TEST"]
    return t


def assign(b, fid, tid="T"):
    b["assignments"].append({"flight_instance_id": fid, "aircraft_id": tid, "crew_id": "C-" + tid,
                             "action": "add", "assumption_id": AID})


def event(b, eid, category, amount, m="2027-01", payments=None, noncash=False):
    e = {"economic_event_id": eid, "owner": eid, "category": category, "scope": "affected_business",
         "driver_unit": "explicit_event", "quantity": 1, "rate": amount, "amount": amount,
         "currency": "RUB", "price_year": 2027, "fx_policy": "RUB_input", "accrual_month": m,
         "noncash": noncash, "avoidability": "synthetic", "shared_event_id": eid,
         "source_id": "P13-SYNTHETIC", "assumption_id": AID, "cash_plan_status": "explicit"}
    if payments is not None:
        e["payments"] = payments
    b["economic_events"].append(e)
    category = "base" if category == "operating_fixed" else category
    if category in b["cost_coverage"]:
        b["cost_coverage"][category].update(status="explicit", event_ids=[eid])
    return e


def cash(b, cid, amount, date, category="operating", eid=None, deposit=False):
    c = {"cash_event_id": cid, "economic_event_id": eid, "related_asset_or_contract_id": cid,
         "payment_date": date, "amount_signed": amount, "category": category, "currency": "RUB",
         "fx_at_payment": 1, "deposit_flag": deposit, "source_id": "P13-SYNTHETIC",
         "status": "scenario", "assumption_id": AID}
    b["cash_events"].append(c)
    return c


def close(actual, expected):
    assert actual is not None and math.isclose(actual, expected, abs_tol=1e-6), (actual, expected)


def reject(fn, text=""):
    try:
        fn()
    except ContractError as e:
        assert text.lower() in str(e).lower(), (str(e), text)
        return str(e)
    raise AssertionError("Ожидался отказ: " + text)


def test(cid):
    def deco(fn):
        CASES.append((cid, fn))
        return fn
    return deco


def dated():
    b = base(); market(b); flight(b, "L1"); tail(b); assign(b, "L1")
    product(b, "BOOKED", legs=["L1"], fare=120, committed=20, contract_only=True)
    product(b, "OUT", owner="OTHER", outside=True)
    return b


def adaptive(parent, decision="2027-02-01", actions=None):
    b = copy.deepcopy(parent)
    b["context"].update(evaluation_id="P-adaptive", evaluation_mode="feasible_adaptation_with_existing_commitments", decision_date=decision)
    b["adaptation"] = {"parent_evaluation_id": parent["context"]["evaluation_id"],
                       "parent_bundle_sha256": digest(parent), "actions": actions or [],
                       "preserved_commitment_ids": [e["economic_event_id"] for e in parent["economic_events"] if e.get("committed_at")],
                       "assumption_id": AID}
    return b


def action(table, rid, decision="2027-02-01", effective="2027-02-01", kind="replace"):
    return {"table": table, "record_id": rid, "action": kind, "decision_date": decision,
            "effective_date": effective, "based_on_fact_ids": ["P13-known"], "assumption_id": AID}


@test("I01_context_manifest_identifiers")
def i01():
    b = base(); b["context"]["input_manifest_sha256"] = "0" * 64
    e = reject(lambda: evaluate(b), "hash mismatch")
    p, k = base(), base("KEEP"); p["context"]["keep_evaluation_id"] = "wrong"
    return {"hash_error": e, "keep_error": reject(lambda: compare(p, k), "wrong pinned KEEP")}


@test("I02_24_month_missing_unknown_zero")
def i02():
    b = dated(); b["market_calendar"][0]["zero_months"].remove("2027-06")
    e = reject(lambda: evaluate(b), "24 months")
    b["market_calendar"][0]["unknown_months"] = ["2027-06"]
    u = evaluate(b); assert u["summary"]["journeys"] is None
    b["market_calendar"][0]["unknown_months"] = []; b["market_calendar"][0]["zero_months"].append("2027-06")
    z = evaluate(b); close(z["summary"]["journeys"], 20); assert len(z["results_monthly"]) == 24
    return {"missing": e, "unknown_journeys": u["summary"]["journeys"], "explicit_zero_other_months_journeys": 20}


@test("I03_shared_legs_one_fare_contract_hold")
def i03():
    b = base(); market(b, "LOCAL", demand=20); market(b, "THROUGH", demand=100)
    flight(b, "L1", seats=50); flight(b, "L2", "BBB", "CCC", "2027-01-10T11:00:00Z", "2027-01-10T13:00:00Z", 30)
    tail(b); assign(b, "L1"); assign(b, "L2")
    product(b, "FIXED", "LOCAL", legs=["L1"], fare=0, contract_only=True)
    product(b, "LOCAL_OUT", "LOCAL", owner="OTHER", outside=True)
    product(b, "CONNECTION", "THROUGH", legs=["L1", "L2"], fare=300)["intercept"] = 100
    product(b, "THROUGH_OUT", "THROUGH", owner="OTHER", outside=True)
    event(b, "BLOCK_PAYMENT", "revenue", 2000)["owner"] = "C1"
    b["contracts"] = [{"contract_id": "C1", "product_id": "FIXED", "reserved_seats": 25, "carried": 20,
                       "release_unused": False, "payment_mode": "block", "economic_event_id": "BLOCK_PAYMENT", "assumption_id": AID}]
    r = evaluate(b)
    close(r["summary"]["journeys"], 45); close(r["summary"]["passenger_segments"], 70); close(r["summary"]["revenue_net"], 9500)
    loads = r["allocation"]["seats"]; close(loads[0]["carried_segments"] + loads[0]["unfilled_contract_seats"], 50)
    close(sum(a["final_choice"] for a in r["allocation"]["allocations"]), 120)
    b["contracts"][0]["release_unused"] = True; released = evaluate(b); close(released["summary"]["journeys"], 50)
    return {"summary": r["summary"], "seats": loads, "released_journeys": 50, "conserved_total_choices": 120}


@test("I04_through_connection_and_inventory_identity")
def i04():
    b = dated(); dupe = copy.deepcopy(b["flights"][0]); dupe["flight_instance_id"] = "MARKETING_ALIAS"; b["flights"].append(dupe)
    e = reject(lambda: evaluate(b), "duplicate physical")
    b = dated(); b["flights"][0]["physical_adjacent_leg"] = False
    return {"alias_rejected": e, "unverified_physical_leg": reject(lambda: evaluate(b), "physical adjacency")}


@test("I05_proportional_recapture_and_order")
def i05():
    b = base(); market(b)
    a = product(b, "A"); a.update(intercept=math.log(4), capacity=10)
    product(b, "B", owner="OTHER").update(intercept=math.log(4), capacity=100)
    product(b, "OUT", owner="OTHER", outside=True).update(intercept=math.log(2))
    r = evaluate(b); aa = {a["product_id"]: a for a in r["allocation"]["allocations"]}
    close(aa["A"]["carried"], 10); close(aa["B"]["carried"], 60); close(aa["OUT"]["final_choice"], 30)
    b["products"].reverse(); reverse = evaluate(b)
    close(reverse["summary"]["journeys"], r["summary"]["journeys"])
    return {"A": 10, "B": 60, "outside": 30, "recaptured_B": aa["B"]["recaptured_in"], "order_invariant": True}


@test("I06_response_month_segment_common_policy")
def i06():
    k = base("KEEP")
    for m, segment, freq in [("2027-01", "leisure", 2), ("2027-02", "leisure", 50), ("2027-01", "business", 50)]:
        market(k, m=m, segment=segment)
        product(k, "RW-" + m + segment, m=m, segment=segment)["frequency"] = freq
        product(k, "COMP-" + m + segment, m=m, segment=segment, owner="OTHER")
        product(k, "OUT-" + m + segment, m=m, segment=segment, owner="OTHER", outside=True)
    target = "COMP-2027-01leisure"
    k["response_policy"]["rules"] = [{"demand_pool_id": "X", "month": "2027-01", "customer_segment": "leisure",
        "rw_frequency_at_least": 3, "target_product_ids": [target], "gross_fare_multiplier": 0.8,
        "frequency_multiplier": 1, "intercept_delta": 0, "assumption_id": AID}]
    k["choice_model"]["price_per_rub"] = -0.01
    p = copy.deepcopy(k); p["context"].update(programme_id="P", evaluation_id="P-independent")
    p["products"][0]["frequency"] = 3
    before = digest({"project": p, "keep": k}); r = compare(p, k)
    eff = lambda x: next(q["gross_fare"] for q in x["effective_products"] if q["product_id"] == target)
    close(eff(r["keep"]), 100); close(eff(r["project"]), 80)
    assert digest({"project": p, "keep": k}) == before
    assert r["delta_summary"]["journeys"] < 0
    return {"same_policy_hash": digest(p["response_policy"]), "KEEP_target_fare": 100,
            "P_target_fare": 80, "no_cross_month_or_segment_trigger": True,
            "delta_rw_journeys_due_to_response": r["delta_summary"]["journeys"], "no_mutation": True}


@test("I07_unknown_choice_and_seats")
def i07():
    b = dated(); b["products"][0]["availability"] = None; u = evaluate(b)
    assert u["summary"]["journeys"] is None and u["summary"]["revenue_net"] is None
    b = dated(); b["flights"][0]["saleable_seats"] = None; seats = evaluate(b)
    assert seats["allocation"] is None and seats["summary"]["journeys"] is None
    return {"unknown_availability": u["unknown_dependencies"], "unknown_inventory": seats["unknown_dependencies"]}


@test("I08_resource_entry_reserve_maintenance_move")
def i08():
    out = {}
    for name, change in [("entry", {"service_entry_date": "2027-02-01T00:00:00Z"}),
                         ("reserve", {"reserve_intervals": [["2027-01-10T07:00:00Z", "2027-01-10T12:00:00Z"]]}),
                         ("maintenance", {"maintenance_intervals": [["2027-01-10T09:00:00Z", "2027-01-10T10:00:00Z"]]}),
                         ("position", {"initial_location": "CCC"})]:
        b = dated(); b["fleet_calendar"][0].update(change); r = evaluate(b)
        assert r["status"] == "INFEASIBLE" and r["summary"]["revenue_net"] is None
        out[name] = r["operations"]["errors"]
    b = dated(); b["fleet_calendar"][0]["crew_windows"] = None; u = evaluate(b)
    assert u["operations"]["status"] == "CONDITIONAL" and u["operations"]["unknowns"]
    out["crew_UNKNOWN_explicit_condition"] = u["operations"]["unknowns"]
    return out


@test("I09_future_KEEP_donor_shared_cost")
def i09():
    k, p = base("KEEP"), base()
    for b in (k, p):
        market(b); product(b, "OUT", owner="OTHER", outside=True)
        t = tail(b); event(b, "LEASE", "aircraft_use", 15); event(b, "BASE", "operating_fixed", 5)
    product(k, "OLD", committed=40, contract_only=True, fare=10)
    product(p, "OLD", committed=25, contract_only=True, fare=10)
    product(p, "NEW", committed=30, contract_only=True, fare=10)
    event(k, "RUN", "variable_cost", 20); event(p, "RUN", "variable_cost", 25)
    r = compare(p, k)
    close(r["delta_summary"]["journeys"], 15); close(r["delta_summary"]["operating_result"], 145)
    assert r["donor_extra_deduction"] is False and r["project"]["operations"]["unused_aircraft"] == ["T"]
    return {"KEEP_result": 360, "P_result": 505, "delta": 145, "donor_counted_once": True, "idle_lease_retained": True}


@test("I10_accrual_cash_prelaunch_terminal_opening")
def i10():
    b = base(); b["cash_policy"].update(opening_cash=40, minimum_cash=10)
    event(b, "START", "startup", 60, "2026-12", [{"date": "2026-12-20", "fraction": 1}])
    event(b, "REV", "revenue", 100, "2027-01", [{"date": "2027-03-01", "fraction": 1}])
    event(b, "COST", "variable_cost", 30, "2027-01", [{"date": "2027-01-10", "fraction": 1}])
    event(b, "DA", "depreciation", 5, noncash=True)
    event(b, "OPEN_AP", "operating_fixed", 0)
    b["opening_balances"] = [{"economic_event_id": "OPEN_AP", "signed_balance": -15}]
    cash(b, "SETTLE_OPEN", -15, "2027-02-01", eid="OPEN_AP")
    event(b, "LATE", "revenue", 70, "2028-12", [{"date": "2029-02-01", "fraction": 1}])
    event(b, "EXIT", "exit", 20, "2029-02", [{"date": "2029-02-01", "fraction": 1}])
    cash(b, "DEP", -25, "2026-12-20", "investing", deposit=True)
    f = evaluate(b)["finance"]
    close(f["operating_result_including_prelaunch"], 75); close(f["accrual_cash_bridge"]["residual"], 0)
    close(f["funding"]["peak_month_end"], 100)
    close(next(r["signed_balance"] for r in f["terminal"]["balances"] if r["economic_event_id"] == "LATE"), 70)
    close(f["terminal"]["refundable_deposits"][0]["signed_asset_balance"], 25)
    assert len(f["terminal"]["future_cash_events"]) == 2
    return {"including_prelaunch": 75, "peak_month_end": 100, "late_receivable": 70,
            "deposit_asset": 25, "future_cash_events": 2, "cash_bridge": f["accrual_cash_bridge"]}


@test("I11_funding_interest_floor_financing_boundary")
def i11():
    b = base(); b["cash_policy"].update(opening_cash=25, minimum_cash=10)
    cash(b, "PAY", -60, "2027-01-03"); cash(b, "RECEIPT", 40, "2027-01-31")
    event(b, "INT", "interest", 7); cash(b, "INT_PAY", -7, "2027-01-03", eid="INT")
    cash(b, "DEBT", 1000, "2027-01-03", "financing")
    r = evaluate(b); f = r["finance"]
    close(r["summary"]["operating_result"], 0)
    close(f["funding"]["peak_month_end"], 12); close(f["funding"]["peak_dated_day_end"], 52)
    close(f["pre_interest_funding_diagnostic"]["peak_month_end"], 5)
    b["cash_coverage"]["finance_interest"] = "unknown"; u = evaluate(b)
    assert u["summary"]["cash_before_financing"] is None and u["finance"]["funding"]["peak_month_end"] is None
    close(u["finance"]["pre_interest_funding_diagnostic"]["peak_month_end"], 5)
    b["cash_coverage"]["finance_interest"] = "explicit"; b["cash_coverage"]["financing"] = "unknown"
    u = evaluate(b); close(u["finance"]["funding"]["peak_month_end"], 12); assert u["results_monthly"][0]["closing_cash"] is None
    floors = {m: 10 for m in months("2026-12", "2028-12")}; floors["2027-06"] = 90
    g = funding([], "2026-12", "2028-12", 25, floors); close(g["peak_month_end"], 65)
    return {"including_interest_month_end": 12, "day_end": 52, "pre_interest": 5,
            "unknown_interest_total_funding": None, "unknown_principal_prefinancing_need": 12, "rising_floor_without_payments": 65}


@test("I12_project_and_whole_company_funding")
def i12():
    p, k = base(), base("KEEP"); cash(p, "ADDED", -30, "2027-01-10")
    p["cash_policy"].update(project_opening_cash=5, project_minimum_cash=2)
    r = compare(p, k); close(r["project_incremental_funding"]["peak_month_end"], 27)
    assert r["whole_company_funding"] is None
    company = base(); cash(company, "EXISTING", -100, "2027-01-10")
    r = compare(p, k, {"keep_evaluation_id": "KEEP-independent", "scope": "whole_company_including_affected_keep",
                       "cash_events": company["cash_events"], "opening_cash": 20, "minimum_cash": 5})
    close(r["whole_company_funding"]["peak_month_end"], 115)
    return {"project_need": 27, "company_need_without_baseline": None, "company_need_with_baseline": 115}


@test("I13_F07_metric_adapter")
def i13():
    k, p = base("KEEP"), base()
    for b, q, den in [(k, 20, 200), (p, 30, 220)]:
        market(b); product(b, "BOOKED", committed=q, contract_only=True)
        product(b, "OUT", owner="OTHER", outside=True)
        b["metric_adapter"] = {"metric_definition_id": "P13-journey", "source_id": "P13-SYNTHETIC",
            "reporting_rule": "journeys", "carrier_vs_group": "carrier", "business_scope": "all toy",
            "denominator_policy": "endogenous_synthetic", "denominators": {"2027": {"year": 2027,
                "metric_definition_id": "P13-journey", "value": den, "denominator_id": "P13-den-" + str(den)}}, "assumption_id": AID}
    r = compare(p, k); close(r["delta_annual"][0]["delta_share_pp"], 100 * (30 / 220 - 20 / 200))
    assert r["delta_annual"][0]["rank_or_number2_date"] is None
    p["metric_adapter"]["business_scope"] = "international-only"
    error = reject(lambda: compare(p, k), "metric scope")
    b = dated(); assert evaluate(b)["results_annual"][0]["share"] is None
    return {"delta_share_pp": 100 * (30 / 220 - 20 / 200), "scope_mismatch": error, "missing_adapter_share": None}


@test("I14_adaptive_exact_parent_future_facts_lock")
def i14():
    p = dated(); event(p, "LEASE", "aircraft_use", 20)["committed_at"] = "2026-11-01"
    a = adaptive(p)
    no_parent = reject(lambda: evaluate(a), "exact parent")
    a["adaptation"]["parent_bundle_sha256"] = "f" * 64; wrong_hash = reject(lambda: evaluate(a, p), "parent hash")
    a = adaptive(p); a["information_set"]["facts"][0]["available_at"] = "2027-03-01"
    future = reject(lambda: evaluate(a, p), "future information")
    a = adaptive(p); a["economic_events"][0]["amount"] = 0
    locked = reject(lambda: evaluate(a, p), "prior commitment")
    return {"no_parent": no_parent, "hash": wrong_hash, "future_fact": future, "locked_event": locked}


@test("I15_adaptive_historical_product_reprice")
def i15():
    p = dated(); a = adaptive(p, actions=[action("products", "BOOKED")])
    a["products"][0]["net_fare"] = 1200
    before = evaluate(p); after = evaluate(a, p)
    close(before["summary"]["revenue_net"], 2400); close(after["summary"]["revenue_net"], 24000)
    save("reproducer_inputs/F01_historical_reprice.json", {"parent": p, "adaptive": a})
    save("results/F01_historical_reprice_actual.json", after)
    return {"finding_id": "P13-F01", "expected": "INVALID: переписан тариф уже выполненной и оплаченной поездки 10.01 на решении 01.02",
            "actual": {"status": after["status"], "revenue_before": 2400, "revenue_after": 24000,
                       "past_cash_before": before["results_monthly"][0]["operating_cash"],
                       "past_cash_after": after["results_monthly"][0]["operating_cash"]}}


@test("I16_adaptive_new_backdated_records")
def i16():
    p = base(); a = adaptive(p, actions=[action("cash_events", "PAST_RECEIPT", kind="add")])
    cash(a, "PAST_RECEIPT", 400, "2027-01-01")
    r = evaluate(a, p); close(r["results_monthly"][0]["operating_cash"], 400)
    save("reproducer_inputs/F01_backdated_add.json", {"parent": p, "adaptive": a})
    return {"finding_id": "P13-F01", "expected": "INVALID: новое действие после decision_date не может создать прошлый платёж",
            "actual": {"status": r["status"], "decision": "2027-02-01", "payment_date": "2027-01-01", "past_receipt": 400}}


@test("I17_adaptive_contract_passengers_disappear")
def i17():
    p = base(); market(p, m="2027-03", demand=50)
    flight(p, "MARCH", dep="2027-03-10T08:00:00Z", arr="2027-03-10T10:00:00Z")
    tail(p); assign(p, "MARCH")
    product(p, "CONTRACT", m="2027-03", legs=["MARCH"], fare=100, contract_only=True)
    product(p, "RETAIL", m="2027-03", legs=["MARCH"], fare=200)["intercept"] = 100
    product(p, "OUT", m="2027-03", owner="OTHER", outside=True)
    p["contracts"] = [{"contract_id": "SIGNED", "product_id": "CONTRACT", "reserved_seats": 30,
                       "carried": 30, "release_unused": False, "payment_mode": "per_passenger",
                       "economic_event_id": None, "assumption_id": AID, "committed_at": "2026-11-01"}]
    a = adaptive(p, actions=[action("contracts", "SIGNED", kind="remove")]); a["contracts"] = []
    before, after = evaluate(p), evaluate(a, p)
    close(before["summary"]["revenue_net"], 7000); close(after["summary"]["revenue_net"], 10000)
    save("reproducer_inputs/F02_contract_erasure.json", {"parent": p, "adaptive": a})
    save("results/F02_contract_erasure_actual.json", after)
    return {"finding_id": "P13-F02", "expected": "INVALID: 30 ранее законтрактованных поездок не удаляются без отмены/перебронирования",
            "actual": {"status": after["status"], "contract_passengers_before": 30, "contract_passengers_after": 0,
                       "retail_before": 20, "retail_after": 50, "revenue_before": 7000, "revenue_after": 10000}}


@test("I18_adaptive_existing_history_is_locked_control")
def i18():
    p = dated(); a = adaptive(p, actions=[action("flights", "L1")])
    a["flights"][0]["distance_km"] = 999
    return {"historical_flight_replacement_rejected": reject(lambda: evaluate(a, p), "historical flights")}


def main():
    records = []
    for cid, fn in CASES:
        try:
            detail = fn()
            records.append({"check_id": cid, "status": "FINDING" if "finding_id" in detail else "PASS", **detail})
        except Exception as exc:
            records.append({"check_id": cid, "status": "ERROR", "error": str(exc), "traceback": traceback.format_exc()})
    save("independent_results.json", {"subject_commit": SHA, "assumption_id": AID, "synthetic_only": True,
                                     "checks": records, "counts": {s: sum(r["status"] == s for r in records) for s in ("PASS", "FINDING", "ERROR")}})
    spec = importlib.util.spec_from_file_location("pinned_author_checks", ROOT / "subject/check_engine.py")
    author = importlib.util.module_from_spec(spec); spec.loader.exec_module(author)
    rerun = []
    for cid, fn in author.TESTS.items():
        if cid == "B18_pinned_adapters":
            rerun.append({"check_id": cid, "status": "NOT_RUN", "reason": "Не копируется полный чужой P02 fixture; адаптер прочитан, source export не admitted"})
            continue
        try:
            rerun.append({"check_id": cid, "status": "PASS", "actual": fn()})
        except Exception as exc:
            rerun.append({"check_id": cid, "status": "FAIL", "error": str(exc), "traceback": traceback.format_exc()})
    save("author_rerun_results.json", {"scope": "Авторские проверки отдельно от независимых примеров", "subject_commit": SHA,
                                       "checks": rerun, "counts": {s: sum(r["status"] == s for r in rerun) for s in ("PASS", "FAIL", "NOT_RUN")}})
    print(json.dumps({"independent": {s: sum(r["status"] == s for r in records) for s in ("PASS", "FINDING", "ERROR")},
                      "author": {s: sum(r["status"] == s for r in rerun) for s in ("PASS", "FAIL", "NOT_RUN")}}, ensure_ascii=False))
    for r in records:
        if r["status"] != "PASS":
            print(json.dumps(r, ensure_ascii=False))
    return any(r["status"] == "ERROR" for r in records) or any(r["status"] == "FAIL" for r in rerun)


if __name__ == "__main__":
    raise SystemExit(main())
