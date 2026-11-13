"""Count existing ML evidence without fitting models or changing their inputs.

Run from any directory with Python 3; standard library only. Reads pinned Git
objects and writes audit.json next to this file. No network calls.
"""
import collections
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PINS = {
    "research": "cd04921fe5dd14dbf5c469b7f15a5efc203abc7b",
    "author": "c11eb8c15d32add540d89d086f62487a5b2d424e",
    "direct_followup": "56400c5f",
    "late_cost_followup": "423fd3f33425ae3c307568cdc295efe7cfa61c9c",
}
PINS = {
    k: subprocess.check_output(["git", "rev-parse", v], cwd=ROOT, text=True).strip()
    for k, v in PINS.items()
}
FILES = {}


def blob(pin, path):
    raw = subprocess.check_output(["git", "show", PINS[pin] + ":" + path], cwd=ROOT)
    FILES[pin + ":" + path] = {
        "commit": PINS[pin], "path": path,
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
    }
    return raw


def rows(pin, path, encoding="utf-8", delimiter=","):
    return list(csv.DictReader(io.StringIO(blob(pin, path).decode(encoding)), delimiter=delimiter))


def counts(rs, key):
    return dict(sorted(collections.Counter(r[key] for r in rs).items()))


p05 = "context/35_full_programme_execution_20261112/P09/subject/P05/"
known = rows("author", "data/manual/known_flows.csv")
train = [r for r in known if r["use"] == "fit"]
fit = json.loads(blob("author", "data/processed/demand_fit.json"))
od_fit = json.loads(blob("author", "data/processed/od_fit.json"))
od = rows("research", p05 + "od_monthly.csv")
history = rows("research", p05 + "aviation_monthly_history.csv")
fares = rows("research", "context/35_full_programme_execution_20261112/P09/competition/fare_panel.csv")
old = rows("author", "data/raw/favt_airports_2007_2020.csv", "cp1251", ";")
name, year, *columns = old[0].keys()
months = columns[:12]
old_valid = [r for r in old if (r[year] or "").isdigit()]


def number(s):
    s = (s or "").strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


cells = [number(r[m]) for r in old_valid for m in months]
complete = [r for r in old_valid if all(number(r[m]) is not None for m in months)]
serials = collections.defaultdict(list)
for r in old_valid:
    if int(r[year]) < 2020:
        for i, month in enumerate(months):
            if number(r[month]) is not None:
                serials[r[name]].append(int(r[year]) * 12 + i)
longest = {}
for airport, periods in serials.items():
    run = best = 0
    previous = None
    for period in sorted(periods):
        run = run + 1 if previous is not None and period == previous + 1 else 1
        best = max(best, run)
        previous = period
    longest[airport] = best
annual_conflicts = []
for r in complete:
    annual = number(r[columns[12]])
    total = sum(number(r[m]) for m in months)
    if annual is not None and abs(total - annual) > 0.01:
        annual_conflicts.append({"name": r[name], "year": r[year], "monthly_sum": total, "published_annual": annual})
monthly = rows("research", "context/35_full_programme_execution_20261112/P09/historical_validation_context.csv")
new_evidence = rows("direct_followup", "context/38_direct_strategy_20261113/market_admission/monthly_evidence.csv")
new_fares = rows("direct_followup", "context/38_direct_strategy_20261113/market_admission/canonical_fares.csv")
blob("late_cost_followup", "context/39_cost_completion_20261113/README.md")
result = {
    "date": "2026-11-13",
    "scope": "ML feasibility audit; no training, forecast backtest, network replay or demonstrated accuracy gain",
    "pins": PINS,
    "author_segment_regression": {
        "known_rows": len(known), "fit_rows": len(train),
        "fit_origin_counts": counts(train, "from_iata"),
        "fit_annual_factor_counts": counts(train, "annual_factor"),
        "features": ["lnPP", "lnRail", "mow", "resort"],
        "reported_loo_median_absolute_percentage_error_of_fact": fit["loo_median_abs_error_pct_of_fact"],
        "reported_loo_share_within_factor_two": fit["loo_share_within_x2"],
        "reported_od_reconstruction_loo_median_absolute_percentage_error_of_fact": od_fit["loo_median_abs_error_pct_of_fact"],
        "metrics_status": "Read existing author metrics, not independently rerun; no observed endpoint OD accuracy claim",
    },
    "p05_monthly_scenarios": {
        "rows": len(od), "directional_markets": len({r["demand_pool_id"] for r in od}),
        "unordered_city_pairs": len({tuple(sorted((r["origin_market"], r["destination_market"]))) for r in od}),
        "months": len({r["month"] for r in od}), "status": counts(od, "status"),
        "scenarios": counts(od, "external_scenario_id"),
        "observed_endpoint_labels_in_this_table": sum(r["status"] == "observed" for r in od),
    },
    "fare_quotes": {
        "rows": len(fares), "markets": counts(fares, "market_id"),
        "as_of": counts(fares, "as_of"), "departure_dates": counts(fares, "departure_date"),
        "lead_days": counts(fares, "booking_lead_days"),
        "basket_comparability": counts(fares, "comparable_basket"),
        "target": "published offers, not realized net fares, choices or elasticity labels",
    },
    "recent_aggregate_aviation_history": {
        "rows": len(history), "unique_months": len({r["month"] for r in history}),
        "start": min(r["month"] for r in history), "end": max(r["month"] for r in history),
        "entity_metric_series": len({(r["entity"], r["metric"]) for r in history}),
        "definition": "carrier aggregates; metrics and parent group overlap; not independent OD observations",
    },
    "historical_airport_panel": {
        "bytes": FILES["author:data/raw/favt_airports_2007_2020.csv"]["bytes"],
        "csv_rows": len(old), "year_rows": len(old_valid), "airport_name_strings": len({r[name] for r in old_valid}),
        "years": counts(old_valid, year), "monthly_cells_total": len(cells),
        "numeric_monthly_cells": sum(v is not None for v in cells),
        "zero_monthly_cells": sum(v == 0 for v in cells),
        "missing_monthly_cells": sum(v is None for v in cells),
        "complete_12month_rows": len(complete),
        "names_with_numeric_months": len({r[name] for r in old_valid if any(number(r[m]) is not None for m in months)}),
        "names_with_at_least_120_contiguous_numeric_months_before_2020": sum(n >= 120 for n in longest.values()),
        "names_with_complete_2007_2019_numeric_history": sum(n == 156 for n in longest.values()),
        "annual_sum_conflicts_in_complete_rows": annual_conflicts,
        "measurement_direction_and_transit_definition": "UNKNOWN in raw CSV; inspect official metadata before application",
        "duplicate_exact_name_year_keys": len(old_valid) - len({(r[name], r[year]) for r in old_valid}),
        "caveats": ["Name strings are not harmonized airport identifiers", "Missing markers are not zero", "Annual totals are not extra monthly labels", "Airport traffic is not endpoint OD", "Historical backtests do not validate post-2020 transfer or 2027-2028 forecasts"],
    },
    "recent_segment_context": {"rows": len(monthly), "comparability": counts(monthly, "comparability")},
    "latest_direct_followup": {
        "monthly_evidence_rows": len(new_evidence), "status": counts(new_evidence, "status"),
        "qualified_fare_rows": len(new_fares),
        "scope": "Latest published additions inspected separately; no merge; not a full re-audit of that research",
    },
    "late_cost_followup": {
        "scope": "Read published README and closure; changes add a cost research package and do not change the inspected demand/price inputs",
        "effect_on_ml_recommendation": "Unit prices, coverage and unknown contract terms support direct cost accounting; no new ML training labels established by this scoped read",
    },
    "files": FILES,
}
(OUT / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "files"}, ensure_ascii=False, indent=2))
