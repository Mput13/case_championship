#!/usr/bin/env python3
"""Read-only integrity/summary check after publication; not a new model audit.

Checks content rather than freezing HEAD, because research commits were authorized.
The original author verifier and independent-review artifacts remain unchanged.
"""
from pathlib import Path
import csv
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P32 = HERE.parent / '32_delay_cargo_research_20261112'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_hashes(base, mapping, label):
    mapping = {name: value['sha256'] if isinstance(value, dict) else value
               for name, value in mapping.items()}
    bad = [name for name, expected in mapping.items()
           if not (base / name).is_file() or sha(base / name) != expected]
    assert not bad, (label, bad[:5])
    return len(mapping)


def read(path):
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    counts = {}
    protected = json.loads((HERE / 'protected_tracked_files.json').read_text())
    assert len(protected) == 436
    counts['original_owner_files'] = check_hashes(ROOT, protected, 'owner')
    manifest = json.loads((HERE / 'networks/manifest.json').read_text())
    counts['network_inputs'] = check_hashes(HERE, manifest['inputs'], 'network inputs')
    counts['network_outputs'] = check_hashes(HERE / 'networks', manifest['outputs'], 'network outputs')
    manifest = json.loads((P32 / 'calculation/manifest.json').read_text())
    counts['delay_cargo_inputs'] = check_hashes(
        ROOT, {row['path']: row['sha256'] for row in manifest['input_files']}, 'delay inputs')
    for key in ('outputs', 'auxiliary_outputs', 'code', 'documentation'):
        counts['delay_cargo_' + key] = check_hashes(P32 / 'calculation', manifest[key], key)

    for path in (HERE / 'network_review/reviewed_summary.json', P32 / 'review/reviewed_summary.json'):
        assert json.loads(path.read_text())['verdict'] == 'ACCEPT_WITH_LIMITATIONS'
    summary = json.loads((HERE / 'SUMMARY_DATA.json').read_text())
    source_rows = read(HERE / 'networks/network_comparison.csv')
    selected = [row for row in source_rows if row['resource'] == 'E2/S0'
                and row['keep_case'] == 'CONTROL_2AER_2MRV_2OMS_REPLACED']
    assert len(selected) == 20
    assert summary['networks'] == [{key: row[key] for key in summary['network_fields']} for row in selected]
    assert summary['delay_cargo'] == read(P32 / 'calculation/route_summary.csv')
    assert summary['cargo_axes'] == [row for row in read(P32 / 'calculation/cargo_break_even.csv')
                                   if row['scenario'] == 'base'
                                   and row['return_potential_alpha'] in ('1.0', '0.25')
                                   and float(row['net_contribution_per_paid_kg_axis_RUB']) == 400]
    delay_fields = ['route', 'injection_min', 'first_KEEP_dep_delay_min', 'last_retained_arrival_delay_min']
    assert summary['delay_cases'] == [{key: row[key] for key in delay_fields}
        for row in read(P32 / 'calculation/delay_summary.csv')
        if row['layout'] == 'EQUAL_GAP_G390' and row['min_turn_scenario_min'] == '60'
        and row['injection_min'] in ('30', '60', '120')]
    html = (HERE / 'COMPARISON.html').read_text()
    inline = re.search(r'<script type="application/json" id="summary-data">(.*?)</script>', html, re.S)
    assert inline and json.loads(inline.group(1)) == summary

    for path in (HERE / 'RESULTS.md', P32 / 'RESULTS.md', P32 / 'README.md', HERE.parent / 'RESEARCH_CURRENT.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if '://' not in link and not link.startswith('#'):
                assert (path.parent / link.split('#')[0]).exists(), (str(path), link)
    print(json.dumps({'status': 'PASS_PUBLISHED_CONTENT_AND_SUMMARIES', 'counts': counts,
                      'network_summary_rows': len(selected), 'checks_source_truth': False,
                      'checks_actual_dispatch_approval': False, 'ignores_authorized_HEAD_changes': True},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
