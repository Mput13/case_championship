#!/usr/bin/env python3
"""Check package scope, CSV shape, references and hashes without writing by default."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def inventory():
    return [p for p in sorted(ROOT.rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and p.suffix!='.pyc'
            and p.name!='output_manifest.json']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--write-manifest',action='store_true')
    args=parser.parse_args()
    required=['comparison_spec.md','model_inventory.csv','decisions.json','requests.json',
              'source_manifest.json','progress.md','reproduce.md','handoff.json','analysis/set001/checks.json']
    for name in required:
        assert (ROOT/name).is_file(),name
    files=inventory()
    for p in files:
        if p.suffix=='.json':
            json.loads(p.read_text())
        if p.suffix=='.csv':
            with p.open(encoding='utf-8-sig',newline='') as stream:
                reader=csv.reader(stream)
                header=next(reader)
                for n,row in enumerate(reader,2):
                    assert len(row)==len(header),(str(p),n,len(row),len(header))
    sources=json.loads((ROOT/'source_manifest.json').read_text())
    for r in sources['files']:
        assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
        assert r['grain'] and len(r['source_commit'])==40
    decisions=json.loads((ROOT/'decisions.json').read_text())['decisions']
    assert not any(d['status']=='TEAM_ACCEPTED' for d in decisions)
    check=json.loads((ROOT/'analysis/set001/checks.json').read_text())
    assert check['status']=='PASS_SCOPED'
    manifest_path=ROOT/'output_manifest.json'
    if args.write_manifest:
        records=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,
                      grain='pinned source; see source_manifest' if 'inputs' in p.relative_to(ROOT).parts else
                            'methodology document, row-level calculation or machine-readable decision; see comparison_spec and reproduce')for p in files]
        manifest_path.write_text(json.dumps(dict(package='methods-spec-v1',independent_review='PENDING',files=records),ensure_ascii=False,indent=2)+'\n')
    else:
        saved=json.loads(manifest_path.read_text())
        assert set(r['path']for r in saved['files'])==set(str(p.relative_to(ROOT))for p in files),'manifest file set'
        for r in saved['files']:
            assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
    print(json.dumps(dict(status='PASS_SCOPED',files=len(files),source_blobs=len(sources['files']),
                         independent_review='PENDING',full_pipeline_replay='NOT_RUN')))


if __name__=='__main__':
    main()
