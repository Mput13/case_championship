#!/usr/bin/env python3
"""Check artifact integrity, declared scope, privacy patterns and deterministic replay."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
EXCLUDED={'package_checks.json','output_manifest.json'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def files():
    return sorted(p for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in EXCLUDED)

def main():
    checks={}
    manifest=json.loads((OUT/'source_manifest.json').read_text())
    for entry in manifest['inputs']:assert sha(OUT/entry['local'])==entry['sha256'],entry['local']
    assert sha(OUT/manifest['coordinates']['path'])==manifest['coordinates']['sha256']
    expected_inputs={str(OUT/entry['local']) for entry in manifest['inputs']}|{str(OUT/manifest['coordinates']['path'])}
    assert {str(p) for p in (OUT/'inputs').rglob('*') if p.is_file()}==expected_inputs
    checks['frozen_input_hashes']='PASS_59'
    required=['report.md','source_manifest.json','comparison.csv','experiment_plan.md','experiment_results.md',
        'findings.csv','reproduction.py','validation.json','corrected_scores.csv','projection_corrections.json',
        'evidence_levels.json','case_source_check.json','radius_chart.html','handoff.md']
    assert all((OUT/p).is_file() for p in required)
    checks['required_outputs']='PASS'
    for path in files():
        assert not path.is_symlink(),path
        assert path.stat().st_size<1_000_000,path
        assert path.suffix.lower() in ['.csv','.md','.py','.json','.html',''] or path.name=='.gitignore',path
        if path.suffix=='.csv':
            with path.open(encoding='utf-8-sig',newline='') as f:
                rows=list(csv.DictReader(f));assert all(None not in row for row in rows),path
        if path.suffix=='.json':json.loads(path.read_text())
    checks['structure_csv_json_size_symlinks']='PASS'
    comp=list(csv.DictReader((OUT/'comparison.csv').open()))
    assert len(comp)==421
    assert len({(x['origin_model'],x['scenario']) for x in comp})==len(comp)
    assert all(x['origin_model'] and x['scenario'] and x['replay_status'] for x in comp)
    assert len([x for x in comp if x['origin_model']=='controlled_common_stage22'])==80
    assert len([x for x in comp if x['origin_model']=='tsiri_stage22'])==140
    assert len([x for x in comp if x['replay_status']=='MISMATCH_HISTORICAL_DERIVED'])==1
    checks['comparison_contract_and_historical_exception']='PASS'
    for name in ['report.md','report_template.md','experiment_results.md','handoff.md']:
        text=(OUT/name).read_text()
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in target or target.startswith('#'):continue
            if target in EXCLUDED:continue  # generated at the end of this check
            assert (OUT/target.split('#')[0]).is_file(),(name,target)
        if name!='report_template.md':assert '@@' not in text,name
    checks['local_document_links']='PASS'
    # Actual credential formats and contact details, not the occurrence of words
    # such as token/auth in methodological documents.
    patterns={
        'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'github_credential':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b',
        'session_header':r'(?im)^(?:Cookie|Set-Cookie|Authorization):\s*\S+',
        'bearer_value':r'\bBearer [A-Za-z0-9._\-]{20,}',
        'contact_email':r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
    }
    hits=[]
    for path in files():
        content=path.read_text()
        for label,pattern in patterns.items():
            if re.search(pattern,content):hits.append(dict(path=str(path.relative_to(OUT)),type=label))
    assert not hits,hits
    checks['credential_cookie_contact_pattern_scan']='PASS'
    # Enforce absence of raw containers and runtime payloads in the package.
    assert not any(p.suffix in ['.db','.sqlite','.sqlite3','.pdf','.xlsx','.gz','.zip','.har'] for p in files())
    assert not any('/raw/' in str(p.relative_to(OUT)) or 'raw_hold' in p.parts for p in files())
    checks['no_full_raw_auth_cookie_runtime_export']='PASS_STRUCTURAL_AND_MANUAL'
    before={str(p.relative_to(OUT)):sha(p) for p in files()}
    for name in ['reproduction.py','summarize_results.py','build_deliverables.py']:
        subprocess.run([sys.executable,str(OUT/name)],cwd=OUT,stdout=subprocess.DEVNULL,check=True)
    after={str(p.relative_to(OUT)):sha(p) for p in files()}
    assert before==after,{'changed':sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))}
    checks['deterministic_offline_rebuild']='PASS_IDENTICAL_ALL_PACKAGE_BYTES'
    validation=json.loads((OUT/'validation.json').read_text())
    assert validation['status']=='COMPLETE_WITH_HISTORICAL_MISMATCH'
    assert not validation['original_pipelines_executed'] and not validation['primary_sources_revalidated']
    checks['acceptance_boundaries']='PASS_EXPLICIT_NOT_RUN'
    result=dict(status='PASS_PACKAGE_WITH_DECLARED_HISTORICAL_EXCEPTION',checks=checks,
        worktree=str(ROOT),file_count=len(after),total_bytes=sum(p.stat().st_size for p in files()),
        primary_fact_quality_claim=False,manual_review='No private contact content or full raw datasets exported; public Git attribution retained as requested')
    (OUT/'package_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'output_manifest.json').write_text(json.dumps(dict(files=after,excludes=sorted(EXCLUDED)),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
