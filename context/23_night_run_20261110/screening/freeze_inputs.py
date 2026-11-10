#!/usr/bin/env python3
"""Read exact Git blobs and specified parent handoffs; write only this package.
No author code is imported or executed. No network or full raw export.
"""
import hashlib
import json
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PARENT = Path('/Users/a/agent-audit-2026-09/case_championship')
PINS = {
    'nastya': '2f03b693a62c219e9475fcd1e26295039f6a49d7',
    'front_historical': '2272e9fac19cdebf68086a46f7ddc48c0fb2d9c8',
    'tsiri_stage22': '6ec84a7d2a6eb50b547a61df82fc5a424f48f146',
    'tsiri_economics': '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
    'tsiri_historical': '91fdbe10e4454c94a20aeca6db38ffc68633ea48',
    'coordinator': '730cde9351ff3407369828ce47c1624b97266a01',
    'core_coordinates': '505e24663e5952bae9b9540bb9a5a622663bfc2a',
    'our_hypotheses': '6ed8788882e7b4d07044b4f6e686ff71eadd8ac5',
}
FILES = {
    'nastya': ['src/longlist_score.py', 'src/build_criteria.py', 'src/longlist_data.py',
        'data/processed/criteria.json', 'data/processed/longlist.csv',
        'data/processed/longlist_scores.csv', 'data/processed/longlist_scores_min500.csv',
        'data/processed/longlist_scenarios.csv', 'data/processed/longlist_scenarios_min500.csv',
        'data/assumptions/longlist_weights.csv', 'data/assumptions/longlist_params.csv',
        'data/assumptions/weight_scenarios.csv', 'docs/25_step1_open_questions.md',
        'data/manual/airport_tech.csv', 'data/manual/competitor_hubs.csv'],
    'front_historical': ['src/longlist_score.py', 'data/processed/criteria.json',
        'data/processed/longlist.csv', 'data/processed/longlist_scores.csv',
        'data/processed/longlist_scores_min500.csv', 'data/assumptions/longlist_weights.csv'],
    'tsiri_stage22': ['src/longlist_score.py', 'scripts/finalize_stage1_audit.py',
        'src/stage1_audit_rules.py', 'data/processed/criteria.json',
        'data/processed/longlist.csv', 'context/22_stage1_audit/rules.json',
        'context/22_stage1_audit/model_rules.json', 'context/22_stage1_audit/weight_profiles.json',
        'context/22_stage1_audit/recommended_weights.csv',
        'context/22_stage1_audit/final_scores.csv', 'context/22_stage1_audit/final_comparison.csv',
        'context/22_stage1_audit/attribution.csv', 'context/22_stage1_audit/accepted_research.csv',
        'context/22_stage1_audit/main_source_checks.md', 'context/22_stage1_audit/integration_decisions.md'],
    'tsiri_historical': ['scripts/build_practical_screening.py', 'scripts/build_network_economics.py',
        'context/11_practical_screening/inputs.json', 'context/11_practical_screening/coordinates.json',
        'context/11_practical_screening/ranking.csv', 'context/11_practical_screening/sources.json',
        'context/12_network_economics/city_ranking_update.csv',
        'context/12_network_economics/city_ranking_update_full.csv'],
    'tsiri_economics': ['context/21_team_proposals/comparison.csv', 'context/21_team_proposals/README.md',
        'context/20_strategy_scope/README.md'],
    'coordinator': ['context/00_brief/case5_requirements.md', 'context/01_primary/README.md',
        'context/19_report_update_20261110/team_update_manifest.json',
        'context/14_synthesis/contributor_guide.md', 'context/18_team_sync/step1_review/report.md',
        'context/18_team_sync/step1_review/findings.json', 'context/18_team_sync/night_workflow_proposal.md'],
}

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def main():
    manifest = {'schema_version': 1, 'as_of_utc': '2026-11-10',
        'actual_worktree': str(ROOT), 'base_head': PINS['coordinator'],
        'attribution': {
            'nastya': 'Настя / kiruha355, explicit user attribution',
            'tsiri_stage22': 'Цири / mput, explicit user attribution',
            'tsiri_historical': 'Цири / mput, historical model lineage, not Konstantin',
            'tsiri_economics': 'Цири / mput, earlier economics',
            'coordinator': 'Михаил / Mput13, explicit user attribution',
            'konstantin': 'Константин, separate contributor; no independent city top3 found in inspected author catalogue',
            'stale_catalog_warning': 'context14 merges mput/Mput13; superseded by explicit user identity clarification and context19 catalogue'},
        'instructions': {'checkout_AGENTS_md': 'ABSENT (checked own directory and ancestors)',
            'source': 'AGENTS instructions supplied in conversation; narrow screening scope'},
        'declared_git_refs': {'nastya': 'origin/шаг-1',
            'tsiri_stage22': 'origin/research/stage1-panel-audit-20261110',
            'front_historical': 'historical_only',
            'ref_policy': 'User pins authoritative; no branch merge/rebase or fresh fetch; local object bytes read by exact SHA'},
        'commits': {}, 'inputs': []}
    for role,sha in PINS.items():
        fields = git('show', '-s', '--format=%H%n%an%n%aI%n%cn%n%cI%n%s', sha).decode().splitlines()
        manifest['commits'][role] = dict(zip(['sha','author','author_date','committer','commit_date','subject'], fields))
    for role, paths in FILES.items():
        sha = PINS[role]
        for path in paths:
            content = git('show', f'{sha}:{path}')
            target = OUT/'inputs'/role/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            manifest['inputs'].append(dict(role=role,commit=sha,path=path,
                local=str(target.relative_to(OUT)),bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),
                git_blob=git('rev-parse',f'{sha}:{path}').decode().strip(),
                level='derived_author_snapshot' if path.endswith(('.csv','.json')) else 'code_or_document',
                url=f'https://github.com/Mput13/case_championship/blob/{sha}/{path}'))
    for path in ['context/19_report_update_20261110/changed_claims.md',
        'context/19_report_update_20261110/handoff.md',
        'context/21_visual_explainer_draft_20261110/inputs_manifest.json',
        'context/21_visual_explainer_draft_20261110/source_references.json']:
        content = (PARENT/path).read_bytes()
        target = OUT/'inputs/parent_readonly'/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        manifest['inputs'].append(dict(role='parent_readonly',commit=None,path=str(PARENT/path),
            local=str(target.relative_to(OUT)),bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),
            level='parent_handoff_not_raw',url=None))
    # Public airport coordinates only, select 24 rows in later reproduction; no full raw copy.
    coord_path = 'context/16_agent_research/core/normalized/airport_version.csv'
    coord_sha = PINS['core_coordinates']
    raw = git('show', f'{coord_sha}:{coord_path}')
    import csv, io
    ids = set(json.loads((OUT/'inputs/nastya/data/processed/criteria.json').read_text())['values']) | {'SVO','DME','VKO','ZIA','SVX'}
    rows = [dict(iata=r['iata_code'],lat=r['latitude_deg'],lon=r['longitude_deg'],ident=r['ident'])
        for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))) if r['iata_code'] in ids]
    assert len(rows) == len(ids) and len({r['iata'] for r in rows}) == len(ids)
    target = OUT/'inputs/airport_coordinates.csv'
    with target.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    manifest['coordinates'] = dict(source_commit=coord_sha,source_path=coord_path,
        source_blob=git('rev-parse', f'{coord_sha}:{coord_path}').decode().strip(),
        source_sha256=hashlib.sha256(raw).hexdigest(),source_total_bytes=len(raw),
        projection='iata_code,latitude_deg,longitude_deg,ident; candidate20 + reference5',
        projected_rows=len(rows),path=str(target.relative_to(OUT)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        raw_revalidated=False,author_raw_available=False,
        note='Author data/raw/ourairports_airports.csv not tracked at pinned SHA; use parent21 pinned core coordinate table. Compare rounded distances before sensitivity.')
    # Count the coordinator hypothesis catalogue without exporting its full rows.
    path='context/16_agent_research/hypotheses/candidates.csv'
    b=git('show',f"{PINS['our_hypotheses']}:{path}")
    rr=list(csv.DictReader(io.StringIO(b.decode())))
    manifest['our_catalogue']=dict(commit=PINS['our_hypotheses'],path=path,sha256=hashlib.sha256(b).hexdigest(),
        rows=len(rr),columns=list(rr[0]),claim='hypothesis catalogue, not independent city ranking')
    (OUT/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status='FROZEN',files=len(manifest['inputs']),coordinates=len(rows),catalogue_rows=len(rr))))

if __name__=='__main__': main()
