#!/usr/bin/env python3
"""Bounded publication and output checks; does not push or inspect peer work."""
import csv
import hashlib
import json
import re
from pathlib import Path
import overlay as o

EXCLUDED = {'output_manifest.json', 'handoff.json', 'publication_checks.json'}
GRAINS = {
    'cost_parameters.csv': 'parameter x author scenario or airport tariff version',
    'parameter_provenance.csv': 'parameter_id x source locator',
    'unit_reconciliation.csv': 'specific unit/price-basis reconciliation',
    'range_registry.csv': 'parameter x kind of range; not statistical intervals',
    'budget_terms.csv': 'unknown contract/accrual/cash term',
    'affected_legs.csv': 'input_set x network x author scenario x overlay scenario x physical leg',
    'physical_leg_status.csv': 'input_set x network x author scenario x overlay scenario x physical leg',
    'affected_journeys.csv': 'input_set x network x author scenario x overlay scenario x original sales CSV line',
    'cost_cash_bridge.csv': 'network x author scenario x overlay scenario x relative cash event; net-of-tax stress only',
    'thresholds.csv': 'network x author scenario x overlay-only boundary; no general threshold synthesis',
    'scenario_summary.csv': 'input_set x network x author scenario x overlay scenario; no aggregation of alternatives',
    'author_flight_cost_components.csv': 'network x author scenario x physical leg x cost component',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest, violations = [], []
    rows = o.readcsv(o.ROOT / 'scenario_summary.csv')
    # Distinct economic status, not numeric zero, for unknown full budgets.
    assert all(r['full_budget_profit_rub'] == '' and r['actual_full_cash_peak_rub'] == '' for r in rows)
    assert all(r['independent_review'] == 'PENDING' for r in rows)
    assert len(rows) == 40
    assert len({(r['network'], r['author_scenario'], r['scenario_id']) for r in rows}) == 40
    assert json.loads((o.ROOT / 'checks.json').read_text())['result'] == 'PASS'
    params = o.readcsv(o.ROOT / 'cost_parameters.csv')
    ids = {r['parameter_id'] for r in params}
    assert len(ids) == len(params)
    assert ids == {r['parameter_id'] for r in o.readcsv(o.ROOT / 'parameter_provenance.csv')}
    assert all(r['value'] == '' and r['missing_reason'] for r in params if r['parameter_id'].startswith('UNKNOWN:'))
    source_by_file = {r['local_path']: r for r in json.loads((o.ROOT / 'source_manifest.json').read_text())['sources']}
    patterns = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                r'\bAKIA[0-9A-Z]{16}\b', r'\bgh[pousr]_[A-Za-z0-9]{30,}\b',
                r'(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._~-]{20,}',
                r'(?i)https?://[^/\s]+:[^/\s]+@',
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b']
    for p in sorted(o.ROOT.rglob('*')):
        rel = str(p.relative_to(o.ROOT))
        if not p.is_file() or any(x in {'raw_hold', '__pycache__'} for x in p.relative_to(o.ROOT).parts) or p.name in EXCLUDED:
            continue
        if p.suffix.lower() in {'.pdf', '.png', '.jpg', '.zip', '.gz', '.db', '.sqlite', '.env', '.log'}:
            violations.append(dict(file=rel, reason='binary/raw/runtime artifact in public payload'))
            continue
        data = p.read_bytes()
        text = data.decode('utf-8-sig')
        # Scan actual data and author source copies. The scanner's own regex
        # literals are code, not credentials or personal contact details.
        if p.name != 'verify_package.py':
            for pattern in patterns:
                if re.search(pattern, text):
                    violations.append(dict(file=rel, reason='potential credential or personal contact; manual resolution required', pattern=pattern))
        count = None
        if p.suffix == '.csv':
            count = len(o.readcsv(p))
        upstream = source_by_file.get(rel)
        manifest.append(dict(path=rel, sha256=sha(data), size_bytes=len(data), rows=count,
                             grain=GRAINS.get(p.name, upstream['grain'] if upstream and 'grain' in upstream else 'source/reference/code/document; see its schema'),
                             role='FROZEN_INPUT' if rel.startswith('inputs/') else 'CODE' if p.suffix == '.py' else 'OUTPUT_OR_DOCUMENT'))
    if violations:
        o.writejson(o.ROOT / 'publication_checks.json', dict(result='FAIL', violations=violations))
        raise ValueError(violations)
    o.writejson(o.ROOT / 'output_manifest.json', dict(version='MR02-payload-manifest-v1',
        scope='All safe payload files except output_manifest.json itself, handoff.json and publication_checks.json; no circular/self-referential hashes',
        excluded_local='raw_hold/ and __pycache__/', files=manifest,
        aggregate_sha256=sha('\n'.join(r['path'] + '\t' + r['sha256'] for r in manifest).encode()),
        independent_review='PENDING'))
    o.writejson(o.ROOT / 'publication_checks.json', dict(result='PASS', payload_files=len(manifest),
        payload_bytes=sum(r['size_bytes'] for r in manifest), full_primary_raw_published=False,
        no_auth_cookies_or_personal_contacts_detected=True, scan_scope='payload text, author copies and data; high-confidence pattern scan, plus scoped manual review',
        unknowns_not_zero=True, independent_review='PENDING', files_excluded_from_payload_hash=sorted(EXCLUDED),
        note='This is publication hygiene and self-checking, not independent economic/market acceptance'))
    print(json.dumps(dict(result='PASS', payload_files=len(manifest), payload_bytes=sum(r['size_bytes'] for r in manifest))))


if __name__ == '__main__':
    main()
