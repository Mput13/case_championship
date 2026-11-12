"""Refresh reviewable schemas/examples and bounded implementation handoff."""
import csv
import inspect
import json
from pathlib import Path
from engine import compare, evaluate, scenario, seal
from engine.common import digest
from engine.core import CONTEXT, TABLES
from engine.fixtures import demo, blank, TOY
from engine.adapters import csv_rows, p02_evidence, p04_rate_catalog

ROOT = Path(__file__).resolve().parent


def write(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def table(name, rows):
    with (ROOT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in r.items()} for r in rows)


b = demo()
write("examples/demo_bundle.json", b)
r = compare(b["project"], b["keep"])
write("examples/demo_result.json", r)
for subject in ("project", "keep"):
    write("examples/" + subject + "_drivers.json", {"context": r[subject]["context"], **r[subject]["cost_driver_exports"]})
write("examples/evaluate_bundle.json", b["project"])
parent = b["project"]
adapt = json.loads(json.dumps(parent))
adapt["context"].update(evaluation_id="P-adaptive-toy", evaluation_mode="feasible_adaptation_with_existing_commitments", programme_version="synthetic-adaptive-v1")
adapt["adaptation"] = {"parent_evaluation_id": "P-toy", "parent_bundle_sha256": digest(parent), "actions": [], "preserved_commitment_ids": ["T1-use-Jan"], "assumption_id": TOY}
write("examples/scenario_bundle.json", {"bundles": [parent, adapt], "parents": {"P-toy": parent}})
write("examples/scenario_result.json", scenario([parent, adapt], {"P-toy": parent}))

checks = json.loads((ROOT / "mechanical_checks.json").read_text())
assert checks["fail"] == 0
sources = json.loads((ROOT / "input_manifest.json").read_text())
corrections = json.loads((ROOT / "correction_lineage.json").read_text())
corrections[0]["new_pinned_delta"] = {"subject": "68d74d2036e41abefd96a150dd557fdca67f6913", "envelope": "d9486f113f074c185a94bcc5c0afeef12ea3574f"}
corrections[0]["status"] = "v2 source exports pinned; physical/commercial admission still UNKNOWN"
write("correction_lineage.json", corrections)
adapted = p02_evidence(csv_rows(ROOT / "inputs/P02v2_calendar_inventory.csv"), csv_rows(ROOT / "inputs/P02v2_alternatives_contract.csv"), corrections)
adapted["P03"] = {"input_commit": "eb4a6020451f66070ec91e26a47e002ec0019f52", "monthly_cohort_rows": len(csv_rows(ROOT / "inputs/P03_fleet_calendar.csv")), "admitted_dated_assignments": 0, "reason": "monthly resource screen is not dated physical assignment or free fleet"}
rates = p04_rate_catalog(csv_rows(ROOT / "inputs/P04_cost_ranges.csv"))
adapted["P04"] = {"input_commit": "620a0ac4bb11763319c4227485f6a3996b91d367", "rate_rows": len(rates), "future_rates_automatically_admitted": 0, "unknown_reference_values": sum(x["reference_value"] is None for x in rates), "support_eligibility": "no-support / seasonal-supported / exception-year-round conditional; P04-Q002 legal applicability unresolved", "missing": "accepted quantities, future applicability, contracts, cash dates and interest terms"}
write("adapter_checks.json", adapted)
write("adapters_P04_rate_catalog.json", rates)

schema = {
    "version": "P06-1.0", "status": "EXECUTABLE_CONDITIONAL_ENGINE",
    "validation_authority": ["engine/core.py:validate", "engine/operations.py:check_operations/check_itineraries", "engine/choice.py:allocate", "engine/finance.py:finance"],
    "encoding": "UTF-8 JSON; null is UNKNOWN; monthly results 2027-01..2028-12; cash_start includes prelaunch",
    "context_required": CONTEXT.split(), "bundle_required": TABLES.split(),
    "canonical_manifest_hash": "SHA256 json.dumps(input_manifest,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode(); engine.seal returns a copy",
    "owners": {"P03": ["flights", "fleet_calendar", "assignments", "keep_policy"], "P05": ["markets", "market_calendar", "products", "contracts", "choice_model", "response_policy"], "P04": ["economic_events", "cash_events", "opening_balances", "cost_coverage", "cash_coverage", "cash_policy", "accounting_policy"], "P07/P08/P09": ["versioned complete P/KEEP bundles", "programmes/actions", "joint recomputation", "input acceptance and exact manifests"]},
    "record_templates": {key: values[0] for key, values in b["project"].items() if isinstance(values, list) and values},
    "object_templates": {key: value for key, value in b["project"].items() if isinstance(value, dict)},
    "contract_template": {"contract_id": "CONTRACT_ID", "product_id": "CONTRACT_ONLY_PRODUCT", "reserved_seats": 40, "carried": 30, "release_unused": False, "payment_mode": "block", "economic_event_id": "OWNED_BLOCK_REVENUE_EVENT", "assumption_id": "SYNTHETIC_EXAMPLE_REPLACE"},
    "response_rule_template": {"demand_pool_id": "POOL", "month": "2027-01", "customer_segment": "SEGMENT", "rw_frequency_at_least": 3, "target_product_ids": ["COMPETITOR"], "gross_fare_multiplier": 0.9, "frequency_multiplier": 1, "intercept_delta": 0, "assumption_id": "SYNTHETIC_EXAMPLE_REPLACE"},
    "adaptation_template": adapt["adaptation"],
    "adaptive_action_fields": ["table", "record_id", "action:add/remove/replace", "decision_date", "effective_date", "based_on_fact_ids", "assumption_id"],
    "money_categories": {"operating": ["revenue", "support", "variable_cost", "operating_fixed", "aircraft_use", "startup", "exit", "depreciation", "operating_credit"], "excluded_operating_result": ["interest", "tax", "investing", "financing"], "cash": ["operating", "investing", "tax", "financing"], "cash_interest": "operating + subcategory finance_interest; mandatory explicit/unknown finance_interest coverage"},
    "cash_floor": "minimum_cash and project_minimum_cash: nonnegative number, null, or complete {YYYY-MM: value_or_null} across cash_start..2028-12",
    "driver_kinds": ["journeys/product_ids", "segments/product_ids", "flights/flight_ids", "block_hours/flight_ids", "explicit quantity for accepted tail/base months, fuel tonnes and other units"],
    "outputs": ["results_monthly", "results_annual", "allocation.allocations", "allocation.seats", "operations.rotations", "economic_events", "cash_events", "terminal balances/obligations", "accrual_cash_bridge", "project incremental / whole company funding", "pre_interest_funding_diagnostic", "cost_driver_exports"],
    "required_notes": ["all examples are synthetic, including every coefficient/price/zero", "each physical tail count=1; no cohort automatic expansion", "market_calendar explicitly lists zero/unknown months; all 24 months covered", "gross fare drives choice; net fare earned once; yield needs explicit distance basis", "cash before financing includes interest under declared P04 presentation convention", "unknown financing principal affects closing cash, not pre-financing need", "parent hash/actions/information facts/commitments required for adaptive run", "source export != accepted future market/capacity/rate"]
}
write("producer_contract.json", schema)

method_rows = [
    ("P06-M01", "conditional logit", "exp(intercept + beta_price*gross_fare + beta_time*duration + beta_frequency*log(frequency))", "dimensionless utility; explicit RUB/minute coefficients", "A simple executable scenario response satisfying SP03; no fitted RW coefficients", "CE07/08/10; B01/B10", "Fit/validate segment-specific coefficients on compatible observed choice data"),
    ("P06-M02", "capacity allocation", "simultaneous proportional bottleneck rationing, then recapture remaining demand", "expected fractional journeys", "Deterministic common-pool conservation without hidden sales priority; not revenue optimum", "CE05/07; B02/B09", "Compare to explicit reservation/recapture data or justified inventory policy"),
    ("P06-M03", "cash timing", "month-end and dated-day-end minima; same-day cash netted", "RUB", "SP11 and CE18; no intraday ordering without timestamps", "CE13/18; B06/B22", "Actual dated large invoices, settlements and liquidity floor"),
    ("P06-M04", "date flexibility", "products in one monthly pool compete unless producer partitions pool by travel-date needs", "pool/month/segment", "No demand for specific dates inferred from monthly total", "CE04/17; market_calendar", "P05 partition mutually exclusive date-sensitive pools and eligible products"),
    ("P06-M05", "accounting", "operating result excludes interest/tax; paid interest in operating cash; separate pre-interest diagnostic", "RUB normalized declared price basis", "P04-A-SP10-INTEREST analytical convention; actual RW policy unknown", "B11/B12/B20", "Contract/accounting mapping and actual interest terms"),
    ("P06-M06", "threshold", "known P-minus-KEEP subtotal minus net missing cost difference", "RUB", "Conditional algebraic threshold, no invented range", "CE15", "P04 accepted missing revenue/support/cost terms"),
    ("P06-M07", "network count", "unique unordered physical airport pairs with project flights in December2028", "pairs", "End-stage schedule count diagnostic; smaller labelled branches allowed", "SP13; no economic selection inferred", "P09 accepted end-2028 programme validity/season definition"),
    ("P06-M08", "numeric tolerance", "1e-8 allocation tolerance, 1e-6 conservation checks, floating expected flows", "journeys/RUB as applicable", "Avoid numerical residues; not a money-precision or inventory guarantee", "all mechanical checks", "Use integer ticket accounting if transaction-level application is required"),
    ("P06-M09", "adaptive scope", "explicit candidate changes and exact parent/hash; no future facts or erased commitments", "versioned events/actions", "SP01/SP08 feasible_adaptation contract; no optimizer or perfect foresight", "CE02; B08/B13/B21", "Candidate generation by programme owners; booking cancellation/refund model if needed"),
]
register = []
for aid, title, value, unit, basis, sens, refine in method_rows:
    register.append({"assumption_id": aid, "subject_version": "P06-1.0", "kind": "implementation_method", "value": value, "unit": unit, "selected_by": "P06 implementation agent / gpt-6-astra xhigh", "basis": basis, "approval_status": "routine_implementation_choice_not_user_approval_of_RW_parameters", "range_or_unknown": "UNKNOWN empirical applicability; algorithm stated exactly", "affected_conclusions": title, "sensitivity": sens, "refinement": refine})
toy = dict(blank()["assumptions"][0])
toy["value"] = {"fixture_files": ["examples/demo_bundle.json", "engine/fixtures.py", "check_engine.py"], "all_demo_values": {k: v for k, v in b["project"].items() if k not in ("assumptions", "input_manifest")}, "additional_boundary_cases": [x["check_id"] for x in checks["checks"] if x["check_id"].startswith("B")]}
register.append(toy)
for a in json.loads((ROOT / "inputs/P00R_assumptions_register.json").read_text()):
    if a["assumption_id"].startswith("P00R-CE"):
        register.append({**a, "range_or_unknown": "UNKNOWN real RW; synthetic fixture only", "refinement": a["refinement_method"]})
write("assumptions_register.json", register)
table("assumptions_register.csv", register)
changes = [{"assumption_id": a["assumption_id"], "change": "reference_preserved" if a["assumption_id"].startswith("P00R-") else "added", "reason": a.get("basis", "synthetic fixture"), "used_in_actual_RW_forecast": False} for a in register]
table("assumption_changes.csv", changes)
write("assumption_usage.json", {"used_engine_ids": [x[0] for x in method_rows], "used_fixture_ids": [TOY] + [f"P00R-CE{x:02d}" for x in range(1, 21)], "P04_reference_only_ids": sorted({x["assumption_id"] for x in rates}), "P04_interest_convention_reference": "P04-A-SP10-INTEREST", "future_RW_parameter_ids_admitted": [], "approval": "no routine per-parameter user approval requested; no factual/contract/legal unknown resolved by model choice"})

patches = list(csv.DictReader((ROOT / "inputs/P00R_schema_patch.csv").open()))
code = {"SP01": "core.validate/compare/scenario/check_adaptation", "SP02": "core.validate market_calendar; choice.allocate", "SP03": "choice.utility/apply_response/allocate", "SP04": "operations.check_operations", "SP05": "operations.check_itineraries; core.cost_driver_exports", "SP06": "choice.allocate", "SP07": "operations.check_operations", "SP08": "core.compare/check_adaptation", "SP09": "finance.materialize_events/finance", "SP10": "finance.finance/funding", "SP11": "finance.funding; core.compare", "SP12": "core.annual_metrics/compare", "SP13": "core.validate/evaluate; market_calendar"}
coverage = [{"patch_id": p["patch_id"], "finding_id": p["finding_id"], "implementation": code[p["patch_id"]], "case_ids": p["acceptance_cases"], "status": "IMPLEMENTED_AUTHOR_CHECKED", "acceptance_boundary": "independent/source/producer acceptance not established by author checks"} for p in patches]
table("engine_check_coverage.csv", coverage)
write("engine_check_coverage.json", {"patches": coverage, "checks_file": "mechanical_checks.json", "checks": checks["pass"], "not_implemented_or_not_validated": ["empirical RW market calibration and out-of-sample fit", "automatic airline schedule generation/global optimization", "all legal crew duty/rest rules, airport slots/access, MEL/payload-range and recovery dispatch", "booked itinerary cancellation/reaccommodation optimization", "foreign currency/tax legal applicability inference", "integer seat-ticket transactions", "intraday payment ordering", "official carrier reporting metric/number2 forecast", "automatic cohort to free-tail conversion", "automatic published station-pair to physical inventory conversion"]})

requests = [
    {"request_id": "P06-D01", "owner": "P05", "fields": "disjoint potential demand pools + explicit 24-month market_calendar; product gross/net fares/time/frequency/bookability; coefficients/source or scenarios; ordered flight IDs", "without": "no numerical integrated RW demand/revenue; synthetic mechanics only", "interface": "producer_contract.json; examples/demo_bundle.json"},
    {"request_id": "P06-D02", "owner": "P03/P07/P08", "fields": "dated physical adjacent flights + tails/entry/position/reserve/maintenance/crew windows + assignments; same P/KEEP resource policy; airport/aircraft restrictions", "without": "no actual RW operational feasibility; monthly cohorts remain evidence", "interface": "producer_contract.json; examples/project_drivers.json"},
    {"request_id": "P06-D03", "owner": "P04", "fields": "accepted driver quantities/rates + currency/price/tax basis; cost coverage; owned accrual/payment events; cash_start/opening/minimum floor/interest/terminal obligations", "without": "complete result/funding UNKNOWN; explicit conditional threshold permitted", "interface": "examples/project_drivers.json; examples/keep_drivers.json; engine/adapters.py:p04_event"},
    {"request_id": "P06-D04", "owner": "P09", "fields": "same-scenario complete affected-business P and future KEEP + programme target/end-stage validity + source manifests", "without": "no programme recommendation; no sums of independent money", "interface": "compare; combine then evaluate"},
    {"request_id": "P06-D05", "owner": "P10", "fields": "compatible official carrier reporting rule and whole numerator/denominator scope/year; full-company KEEP cash", "without": "share/rank/whole-company funding UNKNOWN; OD and segments still separate", "interface": "metric_adapter; compare(company_keep_cash=...)"},
]
table("dependency_requests.csv", requests)
write("variant_proposals.json", {"proposals": [], "reason": "P06 provides calculation mechanisms; no new calibrated programme finding to justify a city/route proposal. Historical variants are lineage, not a closed search set."})
write("reuse_decisions.json", {"author_baseline": "dceadc98f9a293d7530cb7bc50ca4411a95aa4b6", "five_city": "c18f7640ea36647a05b39089e5293f22dd009f63", "preserved": "original source/output blobs untouched; ordered journey legs, single fare, capacity conservation and candidate-generation ideas retained", "not_imported_as_new_programme_money": ["legacy weekly*52 money", "frequency-only capture ignoring competitor price", "deduct old revenue then deduct donor again", "hours-only fleet screen", "source offer as seat inventory"], "reason_for_small_new_kernel": "dated common choice/inventory, scenario identity, actual tail assignment and accrual/cash/KEEP contracts absent from legacy weekly calculator; stdlib functions only, no product platform"})
write("handoff.json", {"package": "P06", "role": "calculation_engine", "status": "IMPLEMENTATION_COMPLETE_CONDITIONAL_ENGINE", "implementation_author": "gpt-6-astra xhigh", "early_usable_commit": "bc70308fe091c5767dbf26b02d06a7d750a65614", "final_commit": "resolve containing commit with git rev-parse; manifest seals payload without self-reference", "manifest": "output_manifest.json", "interfaces": ["evaluate(bundle,parent=None)", "compare(project,keep,company_keep_cash=None,parents=None)", "scenario(bundles,parents=None)", "combine(base,components,context)", "python3 -m engine evaluate|compare|scenario INPUT --out OUTPUT [--tables DIR]"], "checks": {"passed": checks["pass"], "failed": checks["fail"], "source_fingerprint": checks["source_fingerprint"], "scope": "actual engine functions; CE01-20 plus addressed boundary cases; author checks, not independent acceptance"}, "mechanical_finding_status": {f"F{x:02d}": "implemented and author-checked; independent reviewer decides closure" for x in range(1, 7)}, "F07": "adapter gate implemented; no compatible real metric admitted", "primary_sources": "pinned producer source evidence and plan/P00R; no new web collection or invented producer results", "analytical_result": "NO_INTEGRATED_RW_MARKET_OR_MONEY_CONCLUSION", "remaining_fields": requests, "independence": {"authored": ["P06"], "cannot_independently_review": ["P06", "P13 author-excluded check", "P14 author-excluded check"]}, "publication": "own branch only; no Site/dashboard/external messages/payments/restarts", "temporary_dependencies_installed": False})
print("Handoff built; checks", checks["pass"], "PASS")
