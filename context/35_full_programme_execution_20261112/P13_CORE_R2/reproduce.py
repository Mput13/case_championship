"""Narrow independent offline review of b51a47c; standard library only.

Run from any cwd: PYTHONDONTWRITEBYTECODE=1 python3 <this file>
Reads subject data only with git show <exact SHA>:<path>. Writes only here.
No Git mutation, networking, installs, full fixture copies or author suite run.
"""
import ast
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
SUBJECT = "b51a47cf93cc01ca899d18d2ef94d9340261963f"
PREVIOUS = "bb378f1e8bd3c621e83ccf50086f9ce15c6bb9ec"
BASE = "982f13d9b6c378ed9581125ecc5c40f17dade6a3"
VERSION = "P06-1.0.2-adaptive"
PINS = [
    ("P06", "output_manifest.json", "c8d1f7a6463e44b6072820c59ccecb8746cf0151f69fc06f4ed2f0f3c06d301d", 101),
    ("P13_CORE_RECHECK", "output_manifest.json", "a418149e30d1b70a4234e1674dc3cb74676e0e415f595b33a107425505267f6c", 30),
    ("P13_CORE", "manifest.json", "85c2c9fc9ee9f5b548252671d597dd17ace6fc57523f822c18a9e66d859111a7", 45),
]
READS = {}
CHECKS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(path, ref=SUBJECT):
    raw = subprocess.check_output(["git", "show", ref + ":" + PREFIX + path], cwd=REPO)
    READS[ref + ":" + PREFIX + path] = {"sha256": sha(raw), "bytes": len(raw)}
    return raw


def data(path, ref=SUBJECT):
    return json.loads(blob(path, ref))


def save(path, value):
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def save_raw(path, raw):
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items() if k != "engine_version"}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def json_hash(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode())


def verify_package(package, manifest, expected, count):
    raw = blob(package + "/" + manifest)
    assert sha(raw) == expected, (package, sha(raw), expected)
    rows = json.loads(raw)["files"]
    assert len(rows) == count
    verified = []
    for row in rows:
        content = blob(package + "/" + row["path"])
        actual = {"sha256": sha(content), "bytes": len(content)}
        assert actual == {k: row[k] for k in actual}, row["path"]
        verified.append({"path": row["path"], **actual, "match": True})
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", SUBJECT, "--", PREFIX + package + "/"], cwd=REPO).decode().splitlines()
    actual_paths = {p.removeprefix(PREFIX + package + "/") for p in paths}
    assert actual_paths == {r["path"] for r in rows} | {manifest}
    return {"manifest_sha256": sha(raw), "payload_count": len(rows), "tree_coverage_exact": True, "files": verified}


VIRTUAL = Path("/__P13_R2_PINNED_GIT__")
REAL_READ_BYTES = Path.read_bytes


def pinned_read_bytes(path):
    try:
        parts = path.relative_to(VIRTUAL).parts
    except ValueError:
        return REAL_READ_BYTES(path)
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
    import engine as loaded
    return loaded


def check(cid, fn, origin, expected):
    try:
        result = fn()
        row = {"check_id": cid, "origin": origin, "expected": expected, "status": "PASS", "actual": result}
    except Exception as exc:
        row = {"check_id": cid, "origin": origin, "expected": expected, "status": "FAIL", "error": repr(exc), "traceback": traceback.format_exc()}
    CHECKS.append(row)
    print(cid, row["status"], row.get("error", ""))


def rebind(pair, decision=None):
    from engine.common import digest
    a = pair["adaptive"]
    if decision is not None:
        a["context"]["decision_date"] = decision
        for action in a["adaptation"]["actions"]:
            action["decision_date"] = decision
            action["effective_date"] = max(action["effective_date"], decision)
    a["adaptation"]["parent_bundle_sha256"] = digest(pair["parent"])
    return pair


def ledger_view(result):
    return {"status": result["status"], "summary": result["summary"],
            "economic_events": result["finance"]["economic_events"],
            "cash_events": result["finance"]["cash_events"],
            "allocations": result["allocation"], "unknown_dependencies": result["unknown_dependencies"]}


def run_pair(cid, pair, reject, fragment=None, frozen_path=None):
    from engine import evaluate
    from engine.common import ContractError
    if frozen_path:
        save_raw("inputs/" + cid + ".json", blob(frozen_path))
    else:
        save("inputs/" + cid + ".json", pair)
    parent_before = copy.deepcopy(pair)
    parent = evaluate(pair["parent"])
    assert parent["status"] == "CONDITIONAL", parent["status"]
    fixed = copy.deepcopy(pair["adaptive"])
    fixed["context"]["evaluation_mode"] = "fixed_programme"
    diagnostic = evaluate(fixed)
    assert diagnostic["status"] == "CONDITIONAL", diagnostic["status"]
    save("results/" + cid + "_fixed_ledgers.json", {"parent": ledger_view(parent), "candidate_fixed_diagnostic": ledger_view(diagnostic),
         "meaning": "Diagnostic only: candidate is deliberately evaluated in fixed mode without adaptation guards."})
    try:
        result = evaluate(pair["adaptive"], pair["parent"])
        actual = {"outcome": "ACCEPTED", "result": ledger_view(result)}
    except ContractError as exc:
        actual = {"outcome": "REJECTED", "exception": type(exc).__name__, "message": str(exc)}
    assert parent_before == pair, "engine mutated input"
    save("results/" + cid + "_adaptive.json", actual)
    assert (actual["outcome"] == "REJECTED") == reject, actual
    if reject and fragment:
        assert fragment in actual["message"], actual
    if not reject:
        assert actual["result"]["status"] == "CONDITIONAL"
    return {k: v for k, v in actual.items() if k != "result"} | {"parent_status": parent["status"],
            "diagnostic_revenue_before": parent["summary"]["revenue_net"],
            "diagnostic_revenue_after": diagnostic["summary"]["revenue_net"],
            "input_unchanged": True, "input": "inputs/" + cid + ".json"}


def author_b21():
    ns = {"__name__": "pinned_author_b21", "__file__": str(VIRTUAL / SUBJECT / "P06/check_engine.py")}
    exec(compile(blob("P06/check_engine.py"), ns["__file__"], "exec"), ns)
    return ns["b21"]()


def frozen_i03():
    ns = {"__name__": "pinned_frozen_i03", "__file__": str(VIRTUAL / SUBJECT / "P13_CORE/reproduce.py")}
    exec(compile(blob("P13_CORE/reproduce.py"), ns["__file__"], "exec"), ns)
    return ns["i03"]()


def exact_date_helpers():
    """Extract unchanged AST nodes, not a reimplementation or patched engine.

    The public itinerary contract requires departure_date. The first-leg fallback
    is therefore checked here directly, with its API reachability recorded apart.
    """
    from engine.common import month, utc, dated
    source = blob("P06/engine/core.py").decode()
    tree = ast.parse(source)
    adaptation = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "check_adaptation")
    historical = next(n for n in adaptation.body if isinstance(n, ast.FunctionDef) and n.name == "historical_ledger")
    floor = next(n for n in adaptation.body if isinstance(n, ast.FunctionDef) and n.name == "date_floor")
    accrual = next(n for n in historical.body if isinstance(n, ast.FunctionDef) and n.name == "accrual_date")
    ns = {"month": month, "utc": utc, "dated": dated, "products": {}, "flights": {}}
    exec(compile(ast.Module(body=[floor, accrual], type_ignores=[]), "pinned-exact-helper-nodes", "exec"), ns)
    save("source_snippets.json", {"commit": SUBJECT, "path": PREFIX + "P06/engine/core.py", "source_sha256": sha(source.encode()),
        "nodes": [{"name": n.name, "line_start": n.lineno, "line_end": n.end_lineno,
                   "source": ast.get_source_segment(source, n)} for n in (floor, accrual)],
        "method": "Exact parsed AST nodes executed without source edits. This is a helper check, not public API acceptance."})
    return ns


def helper_case(ns, cid, product, flights, event, expected):
    value = {"product": product, "flights": flights, "event": event}
    save("inputs/" + cid + ".json", value)
    ns["products"] = {product["product_id"]: product}
    ns["flights"] = {f["flight_instance_id"]: f for f in flights}
    actual = ns["accrual_date"](event)
    assert actual == expected, (actual, expected)
    return {"date": actual, "direct_exact_AST_helper_only": True, "input": "inputs/" + cid + ".json"}


def missing_date_api(pair, cid):
    from engine import evaluate
    from engine.common import ContractError
    pair = copy.deepcopy(pair)
    for b in pair.values():
        b["products"][0].pop("departure_date")
    rebind(pair)
    save("inputs/" + cid + ".json", pair)
    try:
        evaluate(pair["parent"])
    except ContractError as exc:
        assert "missing ['departure_date']" in str(exc), str(exc)
        return {"exception": "ContractError", "message": str(exc), "first_leg_fallback_reachable_via_public_API": False,
                "meaning": "Required field is missing; no claim of valid adaptive acceptance for this malformed bundle."}
    raise AssertionError("Required itinerary departure_date unexpectedly optional")


def run():
    packages = {p: verify_package(p, m, h, n) for p, m, h, n in PINS}
    assert data("P13_CORE_RECHECK/review.json")["findings"][0]["finding_id"] == "P13_CORE_RECHECK/F01-R1"
    save("source_verification.json", {"subject_commit": SUBJECT, "packages": packages})
    current = engine()
    from engine.common import VERSION as actual_version
    assert actual_version == VERSION
    original_ids = ["F01_historical_reprice", "F01_backdated_add", "F02_contract_erasure"]
    for cid in original_ids:
        path = "P13_CORE/reproducer_inputs/" + cid + ".json"
        pair = data(path)
        check(cid, lambda cid=cid, pair=pair, path=path: run_pair(cid, pair, True, frozen_path=path),
              "frozen_original_reproducer_unchanged", "ContractError")
    recheck_ids = ["derived_past_cash_indirect", "derived_prior_month_accrual_indirect",
                   "derived_same_month_dated_accrual_indirect", "derived_same_month_monthly_accrual_indirect",
                   "derived_same_month_flown_revenue", "past_customer_advance_indirect_competitor",
                   "future_same_month_dated_accrual", "future_same_month_product_reprice"]
    frozen = {}
    for cid in recheck_ids:
        path = "P13_CORE_RECHECK/inputs/" + cid + ".json"
        pair = frozen[cid] = data(path)
        reject = not cid.startswith("future_")
        check(cid, lambda cid=cid, pair=pair, reject=reject, path=path: run_pair(cid, pair, reject,
              "historical derived accruals or cash" if reject else None, path),
              "frozen_recheck_input_unchanged", "ContractError" if reject else "ACCEPTED CONDITIONAL")
    check("B21_valid_future_action", author_b21, "author_B21_code_independently_executed_not_author_result", "valid documented future action accepted")
    check("I03_fixed_contract_release", frozen_i03, "frozen_I03_control_independently_executed", "fixed allocation/release control unchanged")

    # Independent pairs differ only in the event's dating; the unchanged driver
    # changes quantity 2 -> 3 and amount 20 -> 30, with future settlement.
    dated_template = frozen["derived_same_month_dated_accrual_indirect"]
    for date_value, decision, reject, label in [
        ("2027-02-14", "2027-02-15", True, "dated_day_before"),
        ("2027-02-15", "2027-02-15", False, "dated_on_decision"),
        ("2027-02-16", "2027-02-15", False, "dated_day_after"),
        ("2027-02-01", "2027-02-01", False, "dated_first_on_decision"),
        ("2027-02-01", "2027-02-02", True, "dated_first_before_decision"),
        ("2027-02", "2027-02-15", True, "explicit_month_only_before_decision"),
        ("2027-02", "2027-02-01", False, "explicit_month_only_on_first"),
        ("2027-02-15T01:00:00+03:00", "2027-02-15", True, "timestamp_prior_UTC_day"),
        ("2027-02-15T01:00:00Z", "2027-02-15", False, "timestamp_same_UTC_day"),
    ]:
        pair = copy.deepcopy(dated_template)
        for b in pair.values():
            b["economic_events"][0]["accrual_date"] = date_value
        rebind(pair, decision)
        cid = "boundary_" + label
        check(cid, lambda pair=pair, reject=reject, cid=cid: run_pair(cid, pair, reject,
              "historical derived accruals or cash" if reject else None),
              "independent_dated_boundary", "ContractError" if reject else "ACCEPTED CONDITIONAL")
    for month_value, decision, reject, label in [
        ("2027-02", "2027-02-01", False, "monthly_on_first"),
        ("2027-02", "2027-02-02", True, "monthly_after_first"),
        ("2027-03", "2027-02-15", False, "future_month_only"),
    ]:
        pair = copy.deepcopy(frozen["derived_same_month_monthly_accrual_indirect"])
        for b in pair.values():
            b["economic_events"][0]["accrual_month"] = month_value
        rebind(pair, decision)
        cid = "boundary_" + label
        check(cid, lambda pair=pair, reject=reject, cid=cid: run_pair(cid, pair, reject,
              "historical derived accruals or cash" if reject else None),
              "independent_month_only_boundary", "ContractError" if reject else "ACCEPTED CONDITIONAL")

    # The product remains unchanged; an added future competitor changes generated
    # RW revenue, making the historical-ledger guard (not affected_dates) decisive.
    revenue_template = frozen["derived_same_month_flown_revenue"]
    for day, reject in [(14, True), (15, False), (16, False)]:
        pair = copy.deepcopy(revenue_template)
        for b in pair.values():
            for product in b["products"]:
                if product["product_id"] != "FUTURE_COMPETITOR":
                    product["departure_date"] = f"2027-02-{day:02d}"
            b["flights"][0].update(departure_utc=f"2027-02-{day:02d}T08:00:00Z", arrival_utc=f"2027-02-{day:02d}T10:00:00Z")
        rebind(pair)
        cid = "boundary_generated_product_day_" + str(day)
        check(cid, lambda pair=pair, cid=cid, reject=reject: run_pair(cid, pair, reject,
              "historical derived accruals or cash" if reject else None),
              "independent_generated_revenue_boundary", "ContractError" if reject else "ACCEPTED CONDITIONAL")
    pair = copy.deepcopy(revenue_template)
    pair["adaptive"] = copy.deepcopy(pair["parent"])
    pair["adaptive"]["context"].update(evaluation_id="P13-R2-noop", evaluation_mode="feasible_adaptation_with_existing_commitments", decision_date="2027-02-15")
    pair["adaptive"]["adaptation"] = copy.deepcopy(revenue_template["adaptive"]["adaptation"])
    pair["adaptive"]["adaptation"]["actions"] = []
    rebind(pair)
    check("boundary_historical_revenue_noop", lambda: run_pair("boundary_historical_revenue_noop", pair, False),
          "independent_preserved_history_control", "ACCEPTED CONDITIONAL")

    ns = exact_date_helpers()
    event = {"economic_event_id": "journey_revenue:BOOKED", "owner": "BOOKED", "accrual_month": "2027-02"}
    for day in (14, 15, 16):
        cid = "helper_no_departure_first_leg_" + str(day)
        p = {"product_id": "BOOKED", "legs": ["L1"]}
        f = [{"flight_instance_id": "L1", "departure_utc": f"2027-02-{day:02d}T08:00:00Z"}]
        check(cid, lambda cid=cid, p=p, f=f, day=day: helper_case(ns, cid, p, f, event, f"2027-02-{day:02d}"),
              "independent_exact_AST_helper", f"2027-02-{day:02d}; first leg overrides monthly fallback")
    cid = "helper_generated_truly_month_only"
    check(cid, lambda: helper_case(ns, cid, {"product_id": "BOOKED", "legs": []}, [], event, "2027-02-01"),
          "independent_exact_AST_helper", "2027-02-01")
    cid = "helper_explicit_accrual_precedes_product_and_leg"
    check(cid, lambda: helper_case(ns, cid, {"product_id": "BOOKED", "departure_date": "2027-02-20", "legs": ["L1"]},
          [{"flight_instance_id": "L1", "departure_utc": "2027-02-10T08:00:00Z"}], dict(event, accrual_date="2027-02-18"), "2027-02-18"),
          "independent_exact_AST_helper", "2027-02-18")
    check("missing_departure_date_public_contract", lambda: missing_date_api(revenue_template, "missing_departure_date_public_contract"),
          "independent_API_reachability_limit", "ContractError: departure_date is a required itinerary field")

    # Execute both exact versions anew, then compare every returned field other
    # than engine_version. Saved example result JSON is not an oracle.
    examples = {name: data("P06/examples/" + name + ".json") for name in ("evaluate_bundle", "demo_bundle", "scenario_bundle")}
    def examples_result(module):
        return {"evaluate_bundle": module.evaluate(examples["evaluate_bundle"]),
                "demo_bundle": module.compare(**examples["demo_bundle"]),
                "scenario_bundle": module.scenario(**examples["scenario_bundle"])}
    present = examples_result(current)
    for ref in (BASE, PREVIOUS):
        previous = examples_result(engine(ref))
        for name in examples:
            def fixed_check(name=name, previous=previous, ref=ref):
                a, b = normalize(previous[name]), normalize(present[name])
                assert a == b, name
                return {"reference_commit": ref, "subject_commit": SUBJECT, "equal_except_engine_version": True,
                        "normalized_reference_sha256": json_hash(a), "normalized_subject_sha256": json_hash(b)}
            check("fixed_" + ref[:7] + "_" + name, fixed_check, "independent_paired_fixed_execution", "exact equality excluding only engine_version recursively")
    engine()
    save("results.json", {"subject_commit": SUBJECT, "version": VERSION, "checks": CHECKS,
         "counts": {s: sum(r["status"] == s for r in CHECKS) for s in ("PASS", "FAIL")},
         "author_evidence_used_as_independent_acceptance": False})
    save("read_set.json", READS)
    assert all(r["status"] == "PASS" for r in CHECKS), "Review check failures; inspect results.json"


if __name__ == "__main__":
    run()
