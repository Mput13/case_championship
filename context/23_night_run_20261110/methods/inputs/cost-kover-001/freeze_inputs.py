#!/usr/bin/env python3
"""Freeze only the inputs explicitly authorised by MR02; no network calls."""
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PARENT = Path('/Users/a/agent-audit-2026-09/case_championship')
RECOVERY = PARENT / 'context/17_research_report/network_recovery'
COMMITS = {
    'methods': '344f4425ba3fbb73b45a5cbcd223089e2ca7b5d4',
    'nastya': '2f03b693a62c219e9475fcd1e26295039f6a49d7',
    'tsiri': '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
    'core': '505e24663e5952bae9b9540bb9a5a622663bfc2a',
    'critic': 'fd086bad2ae30c46e95d6e38954dc99a18627902',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main():
    if (ROOT / 'source_manifest.json').exists():
        # Frozen package is a reusable input set. Do not silently re-read a
        # moving parent folder or upgrade a snapshot on a subsequent run.
        checked = 0
        for name in ['source_manifest.json', 'reference_input_manifest.json']:
            manifest = json.loads((ROOT / name).read_text())
            for r in manifest['sources']:
                path = ROOT / r['local_path']
                if r.get('publication') == 'LOCAL_IGNORED_ONLY' and not path.exists():
                    continue
                if digest(path.read_bytes()) != r['sha256']:
                    raise ValueError('Frozen input changed: ' + str(path))
                checked += 1
        print(json.dumps(dict(frozen_inputs_reused=True, checked=checked, parent_reread=False)))
        return
    sources = []
    inp = ROOT / 'inputs'
    inp.mkdir(exist_ok=True)
    specs = {
        'methods': [('context/23_night_run_20261110/methods/' + n, 'methods_' + n, 'methodological contract') for n in ['comparison_spec.md', 'decisions.json', 'requests.json']],
        'nastya': [('data/assumptions/network.csv', 'nastya_network.csv', 'author parameter x scenario'), ('src/network_model.py', 'nastya_network_model.py', 'author function source')],
        'tsiri': [
            *[('context/17_aircraft_route_review/model/' + n, 'tsiri_' + n, 'author export; alternatives must not be pooled') for n in ['flights.csv', 'sales.csv', 'capacity.csv', 'comparison.csv']],
            ('context/12_network_economics/inputs.json', 'tsiri_inputs.json', 'author original cost assumptions and market scenarios'),
            ('context/15_team_update/model/overrides.json', 'tsiri_overrides.json', 'author amendments; base fuel 136300'),
            ('context/16_conditional_decision/assumptions.json', 'tsiri_stage16_assumptions.json', 'author resource and illustrative fixed cost scenarios'),
            ('context/17_aircraft_route_review/assumptions.json', 'tsiri_stage17_assumptions.json', 'author route/payload scenario assumptions'),
            ('context/18_unit_economics_audit/input_registry.csv', 'tsiri_cost_registry.csv', 'author parameter provenance'),
            ('scripts/build_team_comparison.py', 'tsiri_core_model.py', 'source for bounded flight_cost function replay only'),
            ('scripts/build_aircraft_route_review.py', 'tsiri_route_model.py', 'source for bounded flight_cost override replay only'),
            ('context/21_team_proposals/comparison.csv', 'tsiri_proposals.csv', 'author proposal comparison'),
        ],
        'core': [('context/16_agent_research/core/branches/operating_evidence/normalized/airport_cost_selected_verified.csv', 'primary_ufa_oms.csv', 'selected published service rate x unit x date'), ('context/16_agent_research/core/branches/operating_evidence/source_registry.csv', 'core_registry.csv', 'source receipt x snapshot')],
        'critic': [('context/16_agent_research/critic/normalized/ufa_fuel_manual_transcription.json', 'critic_ufa_fuel.json', 'selected inherited visual fuel-price transcription')],
    }
    for owner, files in specs.items():
        for source_path, name, grain in files:
            data = subprocess.check_output(['git', 'show', f'{COMMITS[owner]}:{source_path}'], cwd=REPO)
            dest = inp / name
            dest.write_bytes(data)
            sources.append(dict(id=name, owner=owner, source_commit=COMMITS[owner], source_path=source_path, local_path=str(dest.relative_to(ROOT)), sha256=digest(data), size_bytes=len(data), grain=grain, byte_preserved=True, acquisition='git show exact commit:path', raw_hash_scope='git blob bytes, not referenced primary PDF'))

    # Freeze the authorised parent folder once, with a file hash separate from HEAD.
    parent_head = subprocess.check_output(['git', '-C', str(PARENT), 'rev-parse', 'HEAD'], text=True).strip()
    parent_files = ['parsed/khv_cost_components.csv', 'parsed/khv_revision_differences.csv', 'receipts/khv_tariff_202611.json', 'receipts/khv_tariff_current.json', 'receipts/khv_tariff_index.json']
    for rel in parent_files:
        source = RECOVERY / rel
        data = source.read_bytes()
        dest = inp / ('khv_' + source.name if not source.name.startswith('khv_') else source.name)
        dest.write_bytes(data)
        tracked = subprocess.run(['git', '-C', str(PARENT), 'ls-files', '--error-unmatch', str(source.relative_to(PARENT))], capture_output=True).returncode == 0
        sources.append(dict(id=dest.name, owner='authorised_parent_recovery', source_commit=None, parent_git_head_context_only=parent_head, parent_file_tracked=tracked, source_path=str(source), local_path=str(dest.relative_to(ROOT)), sha256=digest(data), size_bytes=len(data), grain='selected tariff rows or acquisition receipt', byte_preserved=True, acquisition='read-only authorised parent snapshot', raw_hash_scope='file bytes; parent HEAD does not identify this snapshot'))
    raw = ROOT / 'raw_hold'
    raw.mkdir(exist_ok=True)
    for name in ['khv_tariff_202611', 'khv_tariff_current']:
        source = RECOVERY / 'raw_hold' / (name + '.bin')
        data = source.read_bytes()
        receipt = json.loads((inp / (name + '.json')).read_text())
        assert digest(data) == receipt['sha256'], name
        dest = raw / (name + '.pdf')
        dest.write_bytes(data)
        sources.append(dict(id=name + '_raw', owner='authorised_parent_recovery', source_commit=None, source_path=str(source), local_path=str(dest.relative_to(ROOT)), sha256=digest(data), size_bytes=len(data), grain='primary public PDF bytes', publication='LOCAL_IGNORED_ONLY', acquisition='read-only authorised parent copy; no new GET', source_url=receipt['source_url'], retrieved_at_utc=receipt['completed_at_utc'], recipe=f"Download public URL in receipt and verify SHA256 {digest(data)}; historical bytes may differ on refetch", raw_hash_scope='primary PDF actually hashed in this run'))
    write_json(ROOT / 'source_manifest.json', dict(version='MR02-input-set-001', pinned_commits=COMMITS, sources=sources, no_live_peer_sources=True, no_external_requests=True))
    # User-supplied update is a separate reference input set, never a replacement
    # for the immutable author baseline above.
    refs = []
    refdir = inp / 'reference_set002'
    refdir.mkdir(exist_ok=True)
    for commit, paths in [
        ('2a74b05179d3619c03fdab3b038fbe7587d85eca', [
            'context/23_night_run_20261110/methods/budget_readout.md',
            'context/23_night_run_20261110/methods/budget_contract.json',
        ]),
        ('27740ffea0821aa404ecd1013d1bb141613261f3', [
            'context/23_night_run_20261110/model_repair/ciri/block_metadata_summary.csv',
            'context/23_night_run_20261110/model_repair/ciri/block_metadata_audit.csv',
            'context/23_night_run_20261110/model_repair/ciri/replay_validation.json',
            'context/23_night_run_20261110/model_repair/ciri/principal_calendar.csv',
            'context/23_night_run_20261110/model_repair/ciri/flight_capacity.csv',
            'context/23_night_run_20261110/model_repair/ciri/itinerary_sales.csv',
            'context/23_night_run_20261110/model_repair/proposed_common_view/status.json',
        ]),
    ]:
        for path in paths:
            data = subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=REPO)
            dest = refdir / Path(path).name
            dest.write_bytes(data)
            refs.append(dict(source_commit=commit, source_path=path, local_path=str(dest.relative_to(ROOT)), sha256=digest(data), size_bytes=len(data), purpose='reference and impact review only; baseline set001 unchanged'))
    write_json(ROOT / 'reference_input_manifest.json', dict(input_set_id='MR02-reference-set-002', payload_commit='dc5c65d12e0236f5aaa6182ca83bda0d52c10f57', supersedes_baseline=False, independent_review='PENDING', sources=refs))
    print(json.dumps(dict(input_files=len(sources), primary_pdfs_local_ignored=2, total_bytes=sum(r['size_bytes'] for r in sources))))


if __name__ == '__main__':
    main()
