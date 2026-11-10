"""Orchestrate the supplied read-only/source-isolated audit checks; no new model."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import subprocess
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--financial-python', default=sys.executable)
    parser.add_argument('--full-replay', action='store_true')
    args = parser.parse_args()
    protected = json.loads((AUDIT / 'protected_owner_files.json').read_text())
    changed = [p for p, h in protected.items() if not (ROOT / p).is_file()
               or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    if changed:
        raise SystemExit('Source changed: ' + ', '.join(changed))
    tables = 0
    for path in AUDIT.rglob('*.csv'):
        with path.open(encoding='utf-8', newline='') as handle:
            rows = list(csv.reader(handle, strict=True))
        assert rows and all(len(r) == len(rows[0]) for r in rows), path
        assert len(rows[0]) == len(set(rows[0])), path
        tables += 1
    commands = []
    if args.full_replay:
        commands.append((args.financial_python, 'replay/reproduce.py', []))
    commands += [
        (args.financial_python, 'replay/round2/checks.py', ['--verify']),
        (args.financial_python, 'replay/check_results.py', []),
        (sys.executable, 'methods/verify.py', []),
        (sys.executable, 'acceptance/verify.py', []),
    ]
    checks = []
    for python, script, extra in commands:
        result = subprocess.run([python, str(AUDIT / script), *extra], cwd=ROOT,
                                capture_output=True, text=True)
        checks.append({'script': script, 'exit_code': result.returncode,
                       'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()})
        if result.returncode:
            print(json.dumps(checks, ensure_ascii=False, indent=2))
            raise SystemExit(result.returncode)
    print(json.dumps({'status': 'PASS', 'scope': 'integrity and bounded audit checks; '
                      'not market/subsidy/operating/fullPnL acceptance',
                      'source_files_unchanged': len(protected), 'csv_tables': tables,
                      'full_replay_requested': args.full_replay,
                      'checks_passed': len(checks)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
