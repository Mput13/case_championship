#!/usr/bin/env python3
"""Read-only pinned evidence extraction. Writes only this package directory."""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import re
from collections import Counter, defaultdict

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
REPO = BASE.parent.parent
PREFIX = str(BASE.relative_to(REPO))
PROJECT = '736859fdd08448c2564b7b9269b751abe00b5cbc'
EXPERT = 'b16c28c6fd2ba9ea509e8a618f5f3b7137f1985e'
EXPECTED = {'P09/manifest.json': '7b20a1a247ee4b3cf96d94648bb36d61482cb0a58eb7a296ada49a78c818d1fa', 'P15/output_manifest.json': 'e7a94a8569f466b91e6676347f3058d88c0aaaf32e777205f26aea1196a14b0e'}
READS = {}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def raw(path, commit=PROJECT):
    rel = PREFIX + '/' + path
    data = subprocess.check_output(['git', 'show', commit + ':' + rel], cwd=REPO)
    local = (REPO / rel).read_bytes()
    READS[(commit, rel)] = {'commit': commit, 'path': rel, 'sha256': sha(data), 'bytes': len(data), 'working_bytes_equal_pinned_blob': data == local, 'observed_working_sha256': sha(local)}
    return data

def obj(path, commit=PROJECT):
    return json.loads(raw(path, commit))

def csvrows(path):
    return list(csv.DictReader(raw(path).decode().splitlines()))

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def table(name, rows):
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def main():
    manifests = {}
    for path, expected in EXPECTED.items():
        data = raw(path)
        assert sha(data) == expected
        manifests[path.split('/')[0]] = json.loads(data)
    em = obj('P00/expert_inputs/manifest.json', EXPERT)
    expert = {}
    for f in em['files']:
        data = raw('P00/expert_inputs/' + f['path'], EXPERT)
        assert sha(data) == f['sha256'] and len(data) == f['bytes']
        expert[f['path']] = data.decode().splitlines()
    pins = obj('P09/input_pins.json')
    nested = []
    for p in pins:
        if p['source_id'] not in ['P03', 'P04']:
            continue
        data = raw('P09/' + p['local_path'])
        upstream = subprocess.check_output(['git', 'show', p['commit'] + ':' + p['path']], cwd=REPO)
        assert sha(data) == p['sha256'] and data == upstream
        nested.append({**p, 'sha_and_upstream_blob_verified': True})

    # All substantive texts/code inspected, not a README-only coverage claim.
    sources = [
        'P09/choice_report.md', 'P09/economics_report.md', 'P09/roadmap.json', 'P09/handoff.json',
        'P09/parameterledger.json', 'P09/programme_cards.json', 'P09/programmes.json', 'P09/scenario_overrides.json',
        'P09/programme_builder.py', 'P09/evaluate_programmes.py', 'P09/assemble.py',
        'P09/existing_ssj_transfer.py', 'P09/international_extension.py', 'P09/schedule_sensitivity.py',
        'P09/projection_contract.json', 'P09/canonical_finalists.py', 'P09/connection_value_controls.csv',
        'P09/sensitivity_response.csv', 'P09/sensitivity_schedule.csv', 'P09/daily_resource_limit_checks.csv',
        'P09/thresholds.csv', 'P09/threshold_driver_coefficients.csv', 'P09/cost_drivers_monthly.csv',
        'P09/subject/P06/engine/operations.py', 'P09/subject/P06/engine/choice.py', 'P09/subject/P06/engine/finance.py',
        'P09/subject/P05/model.py', 'P09/subject/P05/assumptions_register.json',
        'P10/report.md', 'P10/growth_bridge.json', 'P10/handoff.json', 'P10/output_manifest.json',
        'P10/growth_hypothesis_outcomes.csv', 'P10/competitor_scale.csv', 'P10/metric_dictionary.csv',
        'P10/roadmap.csv', 'P10/source_claims.csv', 'P10/financing_thresholds.json',
        'P11/handoff.json', 'P11/digital_effects.csv', 'P11/funnel_and_economics.json',
        'P11/digital_cards.json', 'P11/experiment_design.json', 'P11/validation_limits.json', 'P11/P09_integration_contract.json',
        'P15/ui_contract.json', 'P15/handoff.json', 'P15/presentation_route.json', 'P15/presentation_preset.json',
    ]
    for s in sources:
        raw(s)
    cards = obj('P09/programme_cards.json')
    canonical = csvrows('P09/canonical_summary.csv')
    ui = obj('P15/dashboard_data.json')
    fleet = obj('P09/fleet_calendar.json')
    save('observed_state.json', {
        'project_source': PROJECT, 'expert_source': EXPERT,
        'expert_line_counts': {k: len(v) for k, v in expert.items()},
        'literal_mail_matches': {k: [{'line': i, 'text': l} for i, l in enumerate(v, 1) if re.search(r'\bпочт(?:а|ы|е|у|ой|ою|ов[а-я]*)\b', l.lower())] for k, v in expert.items()},
        'mail_search_pattern': r'\bпочт(?:а|ы|е|у|ой|ою|ов[а-я]*)\b; excludes unrelated почти',
        'literal_speed_fuel_matches': {k: [{'line': i, 'text': l} for i, l in enumerate(v, 1) if any(t in l.lower() for t in ['скорост', 'топлив', 'расход керос'])] for k, v in expert.items()},
        'P15': {'evaluations_count': len(ui['evaluations']), 'programmes_count': len(ui['programmes']), 'strategy': ui['strategy'], 'result_package': ui['result_package'], 'integration': ui['integration']},
        'selected_programme_cards': [c for c in cards if c['programme_id'] in ['VOG_RADIAL', 'MRV_HYBRID', 'AER_HYBRID', 'VOG_BANK9']],
        'boundary': 'Source extraction and arithmetic only; no engine replay, dispatch, market or visual acceptance.'
    })

    # Reuse canonical values. Pairwise thresholds are arithmetic, not a new forecast.
    vv = {r['scenario']: r for r in canonical if r['programme_id'] == 'VOG_RADIAL'}
    pairwise = []
    for r in canonical:
        v = vv[r['scenario']]
        pairwise.append({
            'programme_id': r['programme_id'], 'scenario': r['scenario'], 'delivery': r['delivery'],
            'period': '2027-01..2028-12', 'price_year': '2026',
            'delta_journeys_vs_KEEP': r['delta_journeys'], 'delta_net_revenue_vs_KEEP_RUB': r['delta_revenue_net'],
            'H_vs_KEEP_RUB': r['missing_cost_headroom'],
            'H_vs_VOG_RADIAL_RUB': float(r['missing_cost_headroom']) - float(v['missing_cost_headroom']),
            'journeys_vs_VOG_RADIAL': float(r['delta_journeys']) - float(v['delta_journeys']),
            'criterion': 'P beats comparator iff residual_net_cost_difference <= H; unknown residuals may have either sign',
            'assumption_id': 'EFC-A01', 'full_result': 'UNKNOWN', 'source': PREFIX + '/P09/canonical_summary.csv',
            'source_full_result_sha256': r['source_full_result_sha256'],
        })
    table('decision_thresholds.csv', pairwise)
    subset = [r for r in csvrows('P09/scenario_results.csv') if r['programme_id'] in ['VOG_RADIAL', 'MRV_HYBRID', 'AER_HYBRID', 'VOG_BANK9', 'SVX_BANK9']]
    table('existing_scenario_extract.csv', subset)

    flights = csvrows('P09/dated_flights.csv')
    profile = []
    for pid in ['VOG_RADIAL', 'MRV_HYBRID', 'AER_HYBRID', 'VOG_BANK9', 'SVX_BANK9']:
        rows = [r for r in flights if r['programme_id'] == pid and r['delivery'] == 'phased']
        commercial = [r for r in rows if r['project_network'] == 'True']
        profile.append({'programme_id': pid, 'delivery': 'phased', 'all_flight_rows': len(rows),
                        'project_commercial_legs': len(commercial),
                        'reserve_N1_assigned_legs': sum(r['flight_instance_id'].startswith('N1:') for r in rows),
                        'project_roles': dict(Counter(r['role'] for r in commercial)),
                        'first_project_departure': min(r['departure_utc'] for r in commercial),
                        'last_project_arrival': max(r['arrival_utc'] for r in commercial),
                        'evidence': PREFIX + '/P09/dated_flights.csv',
                        'interpretation': 'No N1 assignments verifies exclusion from sales, not recovery ability.'})
    save('calendar_diagnostics.json', profile)

    for pid in ['VOG_RADIAL']:
        proj = obj('P09/ui/' + pid + '.json')
        for e in proj['evaluations']:
            encoded = json.dumps(e['result'], ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            assert sha(encoded) == e['projection_sha256']
        save('canonical_decision_extract.json', {
            'programme_id': pid, 'source_path': PREFIX + '/P09/ui/' + pid + '.json',
            'evaluations': [{'scenario': e['scenario_label'], 'source_full_result_sha256': e['source_full_result_sha256'],
                             'projection_sha256': e['projection_sha256'], 'projection_digest_verified': True,
                             'delta_summary': e['result']['delta_summary'], 'delta_annual': e['result']['delta_annual'],
                             'project_summary': e['result']['project']['summary'], 'keep_summary': e['result']['keep']['summary'],
                             'thresholds': e['result']['thresholds'],
                             'project_incremental_funding': e['result']['project_incremental_funding'],
                             'whole_company_funding': e['result']['whole_company_funding']} for e in proj['evaluations']],
            'full_canonical_gzip_replay': 'NOT_RUN; no claim to revalidate P06 engine'
        })

    # Verify hashes against the manifests for every actually consumed listed file.
    manifest_checks = []
    for package, manifest in manifests.items():
        entries = {f['path']: f for f in manifest['files']}
        for (commit, path), r in READS.items():
            start = PREFIX + '/' + package + '/'
            if commit == PROJECT and path.startswith(start):
                rel = path[len(start):]
                if rel in entries:
                    assert r['sha256'] == entries[rel]['sha256']
                    manifest_checks.append({'package': package, 'path': rel, 'sha256': r['sha256'], 'matches': True})
    save('input_manifest.json', {'project_commit': PROJECT, 'expert_commit': EXPERT,
                                 'expected_manifests': EXPECTED, 'expert_attachment_manifest': em,
                                 'files': list(READS.values()), 'P03_P04_pins': nested,
                                 'manifest_member_checks': manifest_checks,
                                 'scope': 'All consumed data read from exact immutable Git bytes; P03/P04 exact upstream blobs verified. Working-tree equality is observed metadata only: concurrent coordinator changes are outside this review. No all-files integrity verdict for unconsumed output files.'})
    print(json.dumps({'input_files': len(READS), 'nested_pins': len(nested), 'manifest_member_checks': len(manifest_checks), 'decision_threshold_rows': len(pairwise), 'scenario_rows': len(subset), 'ui_evaluations': len(ui['evaluations'])}))

if __name__ == '__main__':
    main()
