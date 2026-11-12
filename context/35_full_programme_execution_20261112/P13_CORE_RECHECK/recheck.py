"""Offline recheck: all subject inputs come from git show, never shared files.

Run: PYTHONDONTWRITEBYTECODE=1 python3 context/35_full_programme_execution_20261112/P13_CORE_RECHECK/recheck.py
Only writes beneath this script's directory. No installation/network/Git mutations.
"""
import copy
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import traceback

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
PREFIX = "context/35_full_programme_execution_20261112/"
SUBJECT = "bb378f1e8bd3c621e83ccf50086f9ce15c6bb9ec"
BASE = "982f13d9b6c378ed9581125ecc5c40f17dade6a3"
EXPECTED = "74b37e90d6221957e56e26e559b85d07bc58e3138458354c51db9fda568b67b1"
FROZEN_EXPECTED = "85c2c9fc9ee9f5b548252671d597dd17ace6fc57523f822c18a9e66d859111a7"
CACHE = {}
READS = {}


def blob(path, ref=SUBJECT):
    key = (ref, path)
    if key not in CACHE:
        CACHE[key] = subprocess.check_output(["git", "show", ref + ":" + PREFIX + path], cwd=REPO)
    b = CACHE[key]
    READS[ref + ":" + PREFIX + path] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
    return b


def data(path, ref=SUBJECT):
    return json.loads(blob(path, ref))


def save(path, value):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


VIRTUAL = Path("/__P13_RECHECK_PINNED_GIT__")
original_read_bytes = Path.read_bytes


def pinned_read_bytes(path):
    try:
        parts = path.relative_to(VIRTUAL).parts
    except ValueError:
        return original_read_bytes(path)
    return blob("/".join(parts[1:]), parts[0])


class GitModules(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    ref = SUBJECT

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "engine" or fullname.startswith("engine."):
            return importlib.util.spec_from_loader(fullname, self, is_package=fullname == "engine")

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        name = module.__name__
        rel = "P06/engine/__init__.py" if name == "engine" else "P06/" + name.replace(".", "/") + ".py"
        module.__file__ = str(VIRTUAL / self.ref / rel)
        if name == "engine":
            module.__path__ = [str(VIRTUAL / self.ref / "P06/engine")]
        exec(compile(blob(rel, self.ref), module.__file__, "exec"), module.__dict__)


LOADER = GitModules()
sys.meta_path.insert(0, LOADER)
Path.read_bytes = pinned_read_bytes


def engine(ref=SUBJECT):
    for key in list(sys.modules):
        if key == "engine" or key.startswith("engine."):
            del sys.modules[key]
    LOADER.ref = ref
    import engine as module
    return module


def author_checks():
    ns = {"__name__": "pinned_author_checks", "__file__": str(VIRTUAL / SUBJECT / "P06/check_engine.py")}
    exec(compile(blob("P06/check_engine.py"), ns["__file__"], "exec"), ns)
    return ns


def original(name):
    return data("P13_CORE/reproducer_inputs/" + name + ".json")


def adaptation(p, changes=(), decision="2027-02-15", effective="2027-02-15"):
    from engine.common import digest
    a = copy.deepcopy(p)
    a["context"].update(evaluation_id="P13-recheck-adaptive", evaluation_mode="feasible_adaptation_with_existing_commitments", decision_date=decision)
    aid = p["assumptions"][0]["assumption_id"]
    a["adaptation"] = {"parent_evaluation_id": p["context"]["evaluation_id"], "parent_bundle_sha256": digest(p),
                       "actions": [{"table": t, "record_id": r, "action": k, "decision_date": decision,
                                    "effective_date": effective, "based_on_fact_ids": [p["information_set"]["facts"][0]["fact_id"]],
                                    "assumption_id": aid} for t, r, k in changes],
                       "preserved_commitment_ids": [e["economic_event_id"] for e in p["economic_events"] if e.get("committed_at")],
                       "assumption_id": aid}
    return a


def normalized(x):
    if isinstance(x, dict):
        return {k: normalized(v) for k, v in x.items() if k != "engine_version"}
    if isinstance(x, list):
        return [normalized(v) for v in x]
    return x


def digest_json(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def ledgers(r):
    return {"status": r["status"], "summary": r["summary"], "economic_events": r["finance"]["economic_events"],
            "cash_events": r["finance"]["cash_events"], "allocation": r["allocation"]}


CHECKS = []


def check(cid, fn, origin="independent"):
    try:
        details = fn()
        rec = {"check_id": cid, "origin": origin, "status": "PASS", **details}
    except Exception as exc:
        rec = {"check_id": cid, "origin": origin, "status": "FAIL", "error": str(exc), "traceback": traceback.format_exc()}
    CHECKS.append(rec)
    print(cid, rec["status"], rec.get("error", ""))
    return rec


def reject_pair(pair):
    from engine import evaluate
    from engine.common import ContractError
    before = evaluate(pair["parent"])
    try:
        after = evaluate(pair["adaptive"], pair["parent"])
    except ContractError as exc:
        return {"rejected": True, "error": str(exc), "parent_status": before["status"]}
    raise AssertionError("Expected ContractError; accepted " + after["status"] + "; summary=" + json.dumps(after["summary"]))


def verify_package(package, manifest, expected):
    raw = blob(package + "/" + manifest)
    assert hashlib.sha256(raw).hexdigest() == expected
    files = json.loads(raw)["files"]
    records = []
    for item in files:
        b = blob(package + "/" + item["path"])
        actual = hashlib.sha256(b).hexdigest()
        assert actual == item["sha256"] and len(b) == item["bytes"], item["path"]
        records.append({"path": item["path"], "sha256": actual, "bytes": len(b), "match": True})
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", SUBJECT, "--", PREFIX + package + "/"], cwd=REPO).decode().splitlines()
    actual_paths = {x.removeprefix(PREFIX + package + "/") for x in paths}
    assert actual_paths == {x["path"] for x in files} | {manifest}
    return {"manifest_sha256": expected, "payload_count": len(files), "tree_coverage_exact": True, "files": records}


def make_derived(accrual="2027-01", accrual_date=None, payment="2027-04-10"):
    p = original("F01_backdated_add")["parent"]
    p["flights"] = original("F02_contract_erasure")["parent"]["flights"]
    aid = p["assumptions"][0]["assumption_id"]
    ev = {"economic_event_id": "PAST_DERIVED", "owner": "PAST_DERIVED", "category": "variable_cost", "scope": "affected_business",
          "driver_unit": "block_hour", "quantity": 2, "rate": 10, "amount": 20, "currency": "RUB", "price_year": 2027,
          "fx_policy": "RUB_input", "accrual_month": accrual, "noncash": False, "avoidability": "explicit_scenario",
          "shared_event_id": "PAST_DERIVED", "source_id": "P13-SYNTHETIC", "assumption_id": aid,
          "cash_plan_status": "explicit", "driver": {"kind": "block_hours", "flight_ids": ["MARCH"]},
          "payments": [{"date": payment, "fraction": 1}]}
    if accrual_date is not None:
        ev["accrual_date"] = accrual_date
    p["economic_events"] = [ev]
    p["cost_coverage"]["variable_cost"].update(status="explicit", event_ids=["PAST_DERIVED"])
    a = adaptation(p, [("flights", "MARCH", "replace")], effective="2027-03-01")
    a["flights"][0]["arrival_utc"] = "2027-03-10T11:00:00Z"
    return {"parent": p, "adaptive": a}


def same_month_revenue():
    p = original("F01_historical_reprice")["parent"]
    p["markets"][0]["month"] = "2027-02"
    p["market_calendar"][0]["zero_months"].remove("2027-02")
    p["market_calendar"][0]["zero_months"].append("2027-01")
    for pr in p["products"]:
        pr.update(month="2027-02", departure_date="2027-02-10", cash_profile=[{"date": "2027-02-28", "fraction": 1}])
    p["products"][0].update(committed_sales=0, contract_only=False)
    p["flights"][0].update(departure_utc="2027-02-10T08:00:00Z", arrival_utc="2027-02-10T10:00:00Z")
    a = adaptation(p, [("products", "FUTURE_COMPETITOR", "add")])
    competitor = copy.deepcopy(p["products"][1])
    competitor.update(product_id="FUTURE_COMPETITOR", kind="ground", capacity=100, departure_date="2027-02-20", cash_profile=[])
    a["products"].append(competitor)
    return {"parent": p, "adaptive": a}


def accept_pair(pair):
    from engine import evaluate
    before = evaluate(pair["parent"])
    after = evaluate(pair["adaptive"], pair["parent"])
    assert after["status"] == "CONDITIONAL"
    return {"accepted": True, "parent_summary": before["summary"], "adaptive_summary": after["summary"]}


def future_same_month_reprice():
    p = same_month_revenue()["parent"]
    for pr in p["products"]:
        pr["departure_date"] = "2027-02-20"
    p["flights"][0].update(departure_utc="2027-02-20T08:00:00Z", arrival_utc="2027-02-20T10:00:00Z")
    a = adaptation(p, [("products", "BOOKED", "replace")])
    a["products"][0]["net_fare"] = 150
    return {"parent": p, "adaptive": a}


def run():
    package = verify_package("P06", "output_manifest.json", EXPECTED)
    assert package["payload_count"] == 101
    frozen = verify_package("P13_CORE", "manifest.json", FROZEN_EXPECTED)
    save("source_verification.json", {"subject_commit": SUBJECT, "P06": package, "frozen_P13_CORE": frozen})
    current = engine()
    from engine.common import ContractError
    for name in ["F01_historical_reprice", "F01_backdated_add", "F02_contract_erasure"]:
        pair = original(name)
        check(name, lambda pair=pair: reject_pair(pair), "frozen_original_reproducer")
    # Exact author B21: called directly, not its writing main().
    author = author_checks()
    check("B21_future_action", author["b21"], "author_test_independently_rerun")

    # Run the original independent fixed contract allocation/release control only.
    frozen_ns = {"__name__": "pinned_frozen_controls", "__file__": str(VIRTUAL / SUBJECT / "P13_CORE/reproduce.py")}
    exec(compile(blob("P13_CORE/reproduce.py"), frozen_ns["__file__"], "exec"), frozen_ns)
    check("I03_fixed_contract_release", frozen_ns["i03"], "frozen_control_independently_rerun")

    contract_parent = original("F02_contract_erasure")["parent"]
    check("F02_preserved_contract_noop", lambda: accept_pair({"parent": contract_parent, "adaptive": adaptation(contract_parent)}))
    for variant in ["reserved_only", "carried_without_committed_at", "zero_unknown_commitment"]:
        p = copy.deepcopy(contract_parent)
        if variant == "reserved_only":
            p["contracts"][0]["carried"] = 0
        if variant == "carried_without_committed_at":
            p["contracts"][0].pop("committed_at")
        if variant == "zero_unknown_commitment":
            p["contracts"][0].pop("committed_at")
            p["contracts"][0].update(reserved_seats=0, carried=0)
        a = adaptation(p, [("contracts", "SIGNED", "remove")])
        a["contracts"] = []
        check("F02_" + variant, lambda p=p, a=a: reject_pair({"parent": p, "adaptive": a}))
    for variant in ["shrink_carried", "release_reserved", "rebind_product", "bound_product_fare", "bound_product_legs"]:
        p = copy.deepcopy(contract_parent)
        if variant == "release_reserved":
            p["contracts"][0]["carried"] = 0
        table, rid = ("products", "CONTRACT") if variant.startswith("bound_product") else ("contracts", "SIGNED")
        a = adaptation(p, [(table, rid, "replace")])
        if variant == "shrink_carried": a["contracts"][0]["carried"] = 10
        if variant == "release_reserved": a["contracts"][0]["release_unused"] = True
        if variant == "rebind_product": a["contracts"][0]["product_id"] = "RETAIL"
        if variant == "bound_product_fare": a["products"][0]["net_fare"] = 999
        if variant == "bound_product_legs": a["products"][0]["legs"] = []
        check("F02_" + variant, lambda p=p, a=a: reject_pair({"parent": p, "adaptive": a}))
    p = copy.deepcopy(contract_parent)
    p["contracts"][0].update(carried=0, reserved_seats=0, committed_at="2027-03-01")
    a = adaptation(p, [("contracts", "SIGNED", "remove")], effective="2027-03-01")
    a["contracts"] = []
    check("F02_future_uncommitted_zero_contract_removable", lambda: accept_pair({"parent": p, "adaptive": a}))
    p = copy.deepcopy(contract_parent)
    a = adaptation(p, [("products", "RETAIL", "replace")])
    a["products"][1]["net_fare"] = 220
    check("F02_unbound_future_product_change", lambda: accept_pair({"parent": p, "adaptive": a}))
    p = original("F01_historical_reprice")["parent"]
    check("F01_preserved_history_noop", lambda: accept_pair({"parent": p, "adaptive": adaptation(p)}))
    for cid, pair in [("future_same_month_dated_accrual", make_derived("2027-02", "2027-02-20")),
                      ("future_same_month_product_reprice", future_same_month_reprice())]:
        save("inputs/" + cid + ".json", pair)
        check(cid, lambda pair=pair: accept_pair(pair))
    past_advance = same_month_revenue()
    for b in [past_advance["parent"], past_advance["adaptive"]]:
        for pr in b["products"]:
            if pr["product_id"] != "FUTURE_COMPETITOR":
                pr.update(departure_date="2027-02-20", cash_profile=[{"date": "2027-02-10", "fraction": 1}])
        b["flights"][0].update(departure_utc="2027-02-20T08:00:00Z", arrival_utc="2027-02-20T10:00:00Z")
    from engine.common import digest
    past_advance["adaptive"]["adaptation"]["parent_bundle_sha256"] = digest(past_advance["parent"])
    save("inputs/past_customer_advance_indirect_competitor.json", past_advance)
    check("past_customer_advance_indirect_competitor", lambda: reject_pair(past_advance))

    for cid, pair in [("derived_past_cash_indirect", make_derived("2027-03", payment="2027-01-10")),
                      ("derived_prior_month_accrual_indirect", make_derived("2027-01")),
                      ("derived_same_month_dated_accrual_indirect", make_derived("2027-02", "2027-02-10")),
                      ("derived_same_month_monthly_accrual_indirect", make_derived("2027-02")),
                      ("derived_same_month_flown_revenue", same_month_revenue())]:
        save("inputs/" + cid + ".json", pair)
        before = current.evaluate(pair["parent"])
        fixed = copy.deepcopy(pair["adaptive"])
        fixed["context"]["evaluation_mode"] = "fixed_programme"
        after_fixed = current.evaluate(fixed)
        save("results/" + cid + "_fixed_ledgers.json", {"parent": ledgers(before), "candidate_fixed_diagnostic": ledgers(after_fixed)})
        try:
            actual = current.evaluate(pair["adaptive"], pair["parent"])
            outcome = {"outcome": "ACCEPTED", "result": ledgers(actual)}
        except ContractError as exc:
            outcome = {"outcome": "REJECTED", "exception": "ContractError", "message": str(exc)}
        save("results/" + cid + "_adaptive.json", outcome)
        check(cid, lambda pair=pair: reject_pair(pair))

    # Paired fixed-mode compatibility on exact saved examples and original reproducers.
    inputs = {name: data("P06/examples/" + name + ".json") for name in ["demo_bundle", "evaluate_bundle", "scenario_bundle"]}
    def evaluate_examples(e):
        return {"demo_bundle": e.compare(**inputs["demo_bundle"]), "evaluate_bundle": e.evaluate(inputs["evaluate_bundle"]),
                "scenario_bundle": e.scenario(**inputs["scenario_bundle"])}
    old = engine(BASE)
    previous = evaluate_examples(old)
    current = engine()
    present = evaluate_examples(current)
    for name in inputs:
        def compare_results(name=name):
            a, b = normalized(previous[name]), normalized(present[name])
            assert a == b, name
            return {"equal_except_engine_version": True, "normalized_result_sha256": digest_json(a), "base_engine_version": "P06-1.0", "candidate_engine_version": "P06-1.0.1-adaptive"}
        check("fixed_regression_" + name, compare_results)
    save("results.json", {"subject_commit": SUBJECT, "checks": CHECKS,
                          "counts": {s: sum(x["status"] == s for x in CHECKS) for s in ["PASS", "FAIL"]}})
    save("read_set.json", READS)


if __name__ == "__main__":
    run()
