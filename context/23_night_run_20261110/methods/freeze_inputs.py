#!/usr/bin/env python3
"""Capture explicitly pinned, small code/derived inputs; never read moving branches."""
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
PARENT = Path('/Users/a/agent-audit-2026-09/case_championship')
REFS = {
    'nastya_2f03': '2f03b693a62c219e9475fcd1e26295039f6a49d7',
    'tsiri_93fa': '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
    'tsiri_stage22': '6ec84a7d2a6eb50b547a61df82fc5a424f48f146',
    'hypotheses_6ed8': '6ed8788882e7b4d07044b4f6e686ff71eadd8ac5',
    'screening_82df': '82dffa795146ccc575db1bb45ba9391af44def00',
}
FILES = {
    'nastya_2f03': [
        'src/network_model.py', 'src/demand_model.py', 'src/rules.py', 'src/airports_meta.py',
        'data/assumptions/network.csv', 'data/assumptions/demand.csv',
        'data/assumptions/resort_airports.csv', 'data/assumptions/hub_candidates_extra.csv',
        'data/processed/network_routes.csv', 'data/processed/network_summary.csv',
        'data/processed/demand_pairs.csv', 'data/processed/demand_fit.json',
        'data/processed/catchments.csv', 'data/manual/known_flows.csv',
        'data/processed/longlist_scores_min500.csv', 'docs/23_demand_model.md',
        'docs/24_hypotheses_comparison.md',
    ],
    'tsiri_93fa': [
        'scripts/build_aircraft_route_review.py', 'scripts/build_team_comparison.py',
        'scripts/build_conditional_decision.py', 'scripts/build_team_proposals.py',
        'scripts/audit_route_economics.py',
        'context/12_network_economics/inputs.json',
        'context/15_team_update/model/configuration.json',
        'context/15_team_update/model/overrides.json',
        'context/16_conditional_decision/assumptions.json',
        'context/17_aircraft_route_review/assumptions.json',
        'context/17_aircraft_route_review/model/selected_networks.json',
        'context/17_aircraft_route_review/model/comparison.csv',
        'context/17_aircraft_route_review/model/sales.csv',
        'context/17_aircraft_route_review/model/capacity.csv',
        'context/17_aircraft_route_review/model/flights.csv',
        'context/17_aircraft_route_review/evidence/directional_blocks.csv',
        'context/18_unit_economics_audit/assumptions.json',
        'context/18_unit_economics_audit/breakeven.csv',
        'context/18_unit_economics_audit/hub_transfer_optimistic_bound.csv',
        'context/20_strategy_scope/README.md',
        'context/21_team_proposals/comparison.csv', 'context/21_team_proposals/routes.csv',
        'context/21_team_proposals/README.md', 'context/21_team_proposals/validation.json',
    ],
    'tsiri_stage22': ['context/22_stage1_audit/model_rules.json',
                      'context/22_stage1_audit/final_comparison.csv'],
    'hypotheses_6ed8': [
        'context/16_agent_research/hypotheses/candidates.csv',
        'context/16_agent_research/hypotheses/experiments_queue.csv',
        'context/16_agent_research/hypotheses/experiment_v1/README.md',
        'context/16_agent_research/hypotheses/experiment_v1/scenario_programs.json',
        'context/16_agent_research/hypotheses/experiment_v1/runs/c26661067277af20/summary.json',
        'context/16_agent_research/hypotheses/experiment_v1/runs/c26661067277af20/acceptance.csv',
        'context/16_agent_research/hypotheses/experiment_v1/runs/c26661067277af20/conditional_thresholds.csv',
        'context/16_agent_research/hypotheses/experiment_v1/runs/c26661067277af20/physical_legs.csv',
        'context/16_agent_research/hypotheses/experiment_v1/runs/c26661067277af20/c07_comparison.csv',
        'context/16_agent_research/hypotheses/experiment_v1/cost_resource/6cf441ef38e2c6c5/conditional_tariff_coefficients.csv',
        'context/16_agent_research/hypotheses/experiment_v1/cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv',
    ],
    'screening_82df': [f'context/23_night_run_20261110/screening/{p}' for p in [
        'handoff.md', 'findings.csv', 'report_facts.json', 'evidence_levels.json',
        'comparison.csv', 'bax_kuf_gap.csv', 'source_manifest.json', 'package_checks.json',
    ]],
}

GRAINS = {
    'network_routes.csv':'scenario x author program x undirected route leg, annualized symmetric demand',
    'network_summary.csv':'scenario x author network, annualized synthetic week',
    'network.csv':'assumption parameter x author base/cautious columns',
    'demand_pairs.csv':'unordered city/airport pair, annual segment-scale observation or gravity proxy',
    'known_flows.csv':'source-specific flow observation with period and coverage',
    'sales.csv':'profile x network x scenario x directional dated itinerary',
    'capacity.csv':'profile x network x scenario x physical flight id',
    'flights.csv':'profile x network x dated physical flight id',
    'comparison.csv':'source-specific scenario x network or city screening variant; see columns and model_inventory',
    'breakeven.csv':'route x scenario x frequency x selected extra burden',
    'hub_transfer_optimistic_bound.csv':'network x scenario with fixed locals and relaxed transfer demand',
    'physical_legs.csv':'experiment candidate x dated scenario physical movement',
    'conditional_thresholds.csv':'candidate x residual gap x fare x passenger cost per paired cohort',
    'conditional_thresholds_with_product_keys.csv':'candidate product template x residual gap x fare x passenger cost per paired cohort',
    'candidates.csv':'product hypothesis specification',
    'experiments_queue.csv':'proposed product experiment and acceptance boundary',
}


def capture():
    records = []
    for label, paths in FILES.items():
        for source in paths:
            data = subprocess.check_output(['git', 'show', f'{REFS[label]}:{source}'], cwd=REPO)
            target = OUT / 'inputs' / 'set001' / label / source
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == data, f'immutable input changed: {target}'
            else:
                target.write_bytes(data)
            row = dict(input_set_id='set001', model_id=label, source_commit=REFS[label],
                       source_path=source, path=str(target.relative_to(OUT)),
                       sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                       acceptance_scope='RAW_HASH_VERIFIED_GIT_BLOB_ONLY',
                       grain=GRAINS.get(Path(source).name,'source-specific code, document, parameter or metadata record; preserved without aggregation'))
            if source.endswith('.csv'):
                parsed = list(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
                row.update(rows=max(0, len(parsed)-1), columns=parsed[0])
            records.append(row)
    context_manifest=json.loads((OUT.parent/'input_manifest.json').read_text())
    parent_receipts=[]
    for r in context_manifest['local_context']:
        actual=hashlib.sha256((PARENT/r['workspace_path']).read_bytes()).hexdigest()
        assert actual==r['sha256'], f"parent frozen context drift: {r['workspace_path']}"
        parent_receipts.append(dict(**r,observed_sha256=actual,access='READ_ONLY_RECEIPT_NO_SOURCE_WRITE',
                                    grain='research context document or manifest; not numeric model acceptance'))
    manifest = dict(input_set_id='set001', refs=REFS, files=records,parent_context_receipts=parent_receipts,
                    note='Derived inputs and code; hashes do not verify source claims. Independent review pending.')
    target = OUT / 'source_manifest.json'
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'files': len(records), 'bytes': sum(r['bytes'] for r in records)}))


if __name__ == '__main__':
    capture()
