"""Read-only integrity check for this transfer pack; no model or network calls."""
from pathlib import Path
import argparse
import csv
import hashlib
import json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-protected', action='store_true',
                        help='Also require the historical owner baseline unchanged.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_text())
    errors = []
    for name, expected in manifest['files'].items():
        target = (root / name).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            errors.append('missing/unsafe package file: ' + name)
        elif digest(target) != expected:
            errors.append('package hash: ' + name)
    counts = {}
    for path in sorted(root.glob('*.csv')):
        data = path.read_bytes()
        if b'\r' in data:
            errors.append('non-LF CSV: ' + path.name)
        with path.open(encoding='utf-8', newline='') as handle:
            reader = csv.reader(handle, strict=True)
            rows = list(reader)
        if not rows or len(rows[0]) != len(set(rows[0])):
            errors.append('empty/duplicate header: ' + path.name)
        elif any(len(row) != len(rows[0]) for row in rows[1:]):
            errors.append('CSV field count: ' + path.name)
        counts[path.name] = max(0, len(rows) - 1)
    baseline = json.loads((root / 'protected_owner_files.json').read_text())
    repo = root.parent.parent
    changed = [name for name, sha in baseline.items()
               if not (repo / name).is_file() or digest(repo / name) != sha]
    if args.check_protected and changed:
        errors.append('historical owner baseline changed: ' + str(len(changed)))
    # Default mode is portable to the newer owner checkout; changed owner files
    # are reported, not treated as corruption of this additive package.
    result = {'status': 'PASS' if not errors else 'FAIL',
              'scope': 'package hashes and CSV shape; not source truth/model acceptance',
              'package_files': len(manifest['files']), 'csv_rows': counts,
              'historical_owner_files': len(baseline),
              'historical_owner_changed_or_missing': len(changed),
              'protected_check_required': args.check_protected, 'errors': errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
