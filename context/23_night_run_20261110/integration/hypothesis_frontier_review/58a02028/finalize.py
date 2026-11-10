#!/usr/bin/env python3
"""Seal this review's files only; --verify is read-only. No Git mutation."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'output_manifest.json'


def entries():
    result = []
    for path in sorted(ROOT.iterdir()):
        if path.name == MANIFEST.name:
            continue
        assert path.is_file() and not path.is_symlink(), str(path)
        data = path.read_bytes()
        result.append(dict(path=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                           rows=len(list(csv.DictReader(io.StringIO(data.decode())))) if path.suffix == '.csv' else None))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    checks = json.loads((ROOT / 'checks.json').read_text())
    findings = json.loads((ROOT / 'findings.json').read_text())
    handoff = json.loads((ROOT / 'handoff.json').read_text())
    assert checks['fail_count'] == 0, checks['failed_checks']
    assert findings['verdict'] == handoff['verdict'] == 'APPROVE_SCOPED'
    assert findings['review_id'] == handoff['review_id'] == 'FRONTIER_REVIEW'
    assert findings['reviewed_commit'] == handoff['reviewed_commit'] == checks['input_commit']
    assert handoff['personal_checks_passed'] == checks['pass_count']
    result = entries()
    if args.verify:
        sealed = json.loads(MANIFEST.read_text())
        assert sealed['files'] == result, 'Changed, missing or extra review output'
    else:
        MANIFEST.write_text(json.dumps(dict(review_id='FRONTIER_REVIEW',
          reviewed_commit=checks['input_commit'], self_excluded='output_manifest.json',
          files=result, bytes=sum(r['bytes'] for r in result), raw_copied=False,
          acceptance_scope='Review-package byte integrity only; no source/market/full-budget upgrade'),
          ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(mode='verify' if args.verify else 'seal', files=len(result),
                          bytes=sum(r['bytes'] for r in result), verdict=findings['verdict'],
                          personal_checks=checks['pass_count'])))


if __name__ == '__main__':
    main()
