"""python -m engine evaluate|compare|scenario INPUT.json --out OUTPUT.json"""
import argparse
import csv
import json
from pathlib import Path
from .core import evaluate, compare, scenario
from .common import ContractError


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["evaluate", "compare", "scenario"])
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--tables", type=Path)
    args = ap.parse_args()
    b = json.loads(args.input.read_text())
    try:
        if args.command == "evaluate":
            result = evaluate(b)
        elif args.command == "compare":
            result = compare(b["project"], b["keep"], b.get("company_keep_cash"), b.get("parents"))
        else:
            result = scenario(b["bundles"], b.get("parents"))
    except (ContractError, KeyError, ValueError) as exc:
        result = {"status": "INVALID", "error": str(exc), "error_type": type(exc).__name__}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        raise SystemExit(2)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    if args.tables:
        args.tables.mkdir(parents=True, exist_ok=True)
        evaluations = result.get("evaluations", [result["project"], result["keep"]] if "project" in result else [result])
        for e in evaluations:
            prefix = e["context"]["evaluation_id"].replace("/", "_")
            tables = {"results_monthly": e["results_monthly"], "results_annual": e["results_annual"], "economic_events": e["finance"]["economic_events"], "cash_events": e["finance"]["cash_events"], "rotations": e["operations"]["rotations"], "allocations": [] if e["allocation"] is None else e["allocation"]["allocations"], "flight_inventory": [] if e["allocation"] is None else e["allocation"]["seats"]}
            for name, rows in tables.items():
                if not rows:
                    continue
                with (args.tables / (prefix + "_" + name + ".csv")).open("w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
                    w.writeheader()
                    w.writerows({k: "UNKNOWN" if v is None else json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()} for row in rows)


if __name__ == "__main__":
    main()
