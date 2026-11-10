#!/usr/bin/env python3
"""Add explicit policy metadata/provenance and hash the deliverable; no replay."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCES={
    'anastasia':'2f03b693a62c219e9475fcd1e26295039f6a49d7',
    'stage22':'6ec84a7d2a6eb50b547a61df82fc5a424f48f146',
    'ciri':'93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
    'methods':'344f4425ba3fbb73b45a5cbcd223089e2ca7b5d4'}


def js(path,v):path.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))


def table(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        fields=list(dict.fromkeys(k for r in rows for k in r))
        w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)


def policy(mode):
    return dict(
        actual_capture_law='independent_author_claims' if mode=='AUTHOR_REPLAY' else
            ('market_bound_only' if mode=='CORRECTED_MARKET_BOUND_ONLY' else 'author_at_total_frequency'),
        actual_allocation='independent_author_claims' if mode=='AUTHOR_REPLAY' else
            ('standalone_claim' if mode in ('CORRECTED_CLAIM_ALLOCATION','CORRECTED_MARKET_BOUND_ONLY') else 'frequency'),
        capture_policy_status='AUTHOR_PROPOSAL' if mode=='AUTHOR_REPLAY' else 'AGENT_PROPOSAL',
        mode='AUTHOR_REPLAY' if mode=='AUTHOR_REPLAY' else 'CORRECTED_REPLAY',
        source_grain='UNDATED_SYMMETRIC_PAIR_AGGREGATE_NOT_PHYSICAL_FLIGHT',
        entire_D_exceedance_in_saved_selection=False)


def main():
    provenance=[]
    for role,sha in SOURCES.items():
        raw=subprocess.check_output(['git','show','-s','--format=%H%x00%an%x00%ae%x00%aI%x00%cn%x00%cI',sha],cwd=ROOT,text=True).strip().split('\0')
        provenance.append(dict(role=role,commit=raw[0],git_author=raw[1],
                               authored_at=raw[3],git_committer=raw[4],committed_at=raw[5]))
    js(ROOT/'provenance.json',dict(sources=provenance,implementation_author='Codex / Sol 6.1 xhigh',
        person_attribution_basis='direct user contract: Анастасия/kiruha355; Цири/mput; Михаил/Mput13',
        raw_restore='public_restore_receipt.json; extraction_validation.json',
        methods_independent_review='PENDING',implementation_independent_review='PENDING'))
    for dest in (ROOT/'outputs').iterdir():
        if dest.is_dir():js(dest/'policy.json',dict(policy(dest.name),frequency_policy='AUTHOR_STANDALONE_FIXED',
            note='shared D/seat guard mandatory; pooled Q(F) is not uniquely mandated by the saved defect'))
    for path in (ROOT/'ledgers').rglob('market_pool.csv'):
        rows=read(path)
        if rows:
            mode=path.relative_to(ROOT/'ledgers').parts[0]
            rows=[dict(r,**policy(mode),comparison_budget_law=r.get('capture_law','author_at_total_frequency'),
                       allocation=policy(mode)['actual_allocation']) for r in rows]
            table(path,rows)
    for path in (ROOT/'evaluation_summary.csv',ROOT/'market_bound_only_summary.csv'):
        rows=read(path);table(path,[dict(r,**policy(r['run_id'])) for r in rows])
    for path in (ROOT/'author_export_comparison.csv',):
        rows=read(path)
        for r in rows:r['byte_difference_reason']=r['byte_difference_reason'].replace('Linux LF','runtime LF')
        table(path,rows)
    validation=json.loads((ROOT/'replay_validation.json').read_text())
    for r in validation['author_exports']:
        r['byte_difference_reason']=r['byte_difference_reason'].replace('Linux LF','runtime LF')
    validation.update(methods_commit=SOURCES['methods'],methods_independent_review='PENDING',
        shared_pair_saved_entire_D_exceeded=False,
        pooled_curve_status='AGENT_PROPOSAL_NOT_UNIQUE_OBJECTIVE_CORRECTION',
        market_bound_only='separate extension; preserved frozen financial baseline; no new author replay',
        MR06='1372 frozen leg values match; 1072 metadata corrected; zero time changes')
    js(ROOT/'replay_validation.json',validation)
    # Verify all archived source bytes, independent of generated CSVs.
    manifest=json.loads((ROOT/'source_manifest.json').read_text())
    for item in manifest['inputs']:
        data=(ROOT/item['local_path']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==item['sha256'],item['local_path']
    for item in json.loads((ROOT/'ciri/source_manifest.json').read_text()):
        data=(ROOT/item['local_path']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==item['sha256'],item['local_path']
    (ROOT/'proposed_common_view/source_manifest.json').write_text(json.dumps(dict(
        source_manifests=['../source_manifest.json','../ciri/source_manifest.json','../ciri/block_audit_source_manifest.json',
                          '../methods_spec/source_manifest.json'],source_provenance='../provenance.json',
        mapping='../field_mapping.csv',common_comparison='NOT_RUN'),ensure_ascii=False,indent=2)+'\n')
    for name in ('findings.json','decision_ledger.json'):
        # These are exact package records, not decisions invented by the adapter.
        (ROOT/'proposed_common_view'/name).write_bytes((ROOT/name).read_bytes())
    artifacts=[]
    for path in sorted(ROOT.rglob('*')):
        rel=path.relative_to(ROOT)
        if not path.is_file() or rel.parts[0]=='raw' or '__pycache__' in rel.parts:continue
        if path.suffix=='.pyc' or path.name in ('artifact_manifest.json','handoff.json'):continue
        data=path.read_bytes()
        if rel.parts[0]=='author':grain='pinned author source/input or initial author runtime output; source_manifest gives precise origin'
        elif rel.parts[0]=='frozen_exports':grain='immutable author CSV export'
        elif rel.parts[0]=='ledgers':grain='network/scenario; itinerary, incidence, annual money or UNDATED aggregate pair capacity; never dated physical flight'
        elif rel.parts[0]=='ciri':grain='pinned Ciri source/input or profile/network/scenario dated model output; see ciri manifests'
        elif rel.parts[0]=='proposed_common_view':grain='proposed adapter; explicit units and compatibility flags; no harmonised comparison'
        elif rel.parts[0]=='outputs':grain='separate author/corrected run; source CSV schema and policy.json'
        elif path.suffix=='.py':grain='implementation or reproducible check source'
        else:grain='package metadata, evidence table or human report; units explicit within artifact'
        artifacts.append(dict(path=str(rel),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),grain=grain))
    js(ROOT/'artifact_manifest.json',dict(status='HASHED',artifacts=artifacts,
        bytes=sum(x['bytes'] for x in artifacts),excluded=['raw/','__pycache__/','artifact_manifest.json (self)','handoff.json (commit receipt)'],
        source_commits=SOURCES,independent_review='PENDING'))
    print(json.dumps(dict(status='PASS',hashed_files=len(artifacts),bytes=sum(x['bytes'] for x in artifacts),source_bytes_verified=True)))


if __name__=='__main__':main()
