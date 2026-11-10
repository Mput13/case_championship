#!/usr/bin/env python3
"""Receive coordinator-provided immutable files into a new named input set."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input-set',required=True)
    p.add_argument('--commit',required=True)
    p.add_argument('--scope',required=True)
    p.add_argument('--file',action='append',required=True)
    p.add_argument('--acceptance',required=True)
    a=p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',a.input_set)
    assert re.fullmatch('[0-9a-f]{40}',a.commit)
    records=[]
    for file in a.file:
        relative=Path(file)
        assert not relative.is_absolute() and '..' not in relative.parts
        source=a.scope.rstrip('/')+'/'+file
        content=subprocess.check_output(['git','show',a.commit+':'+source],cwd=ROOT.parents[2])
        target=ROOT/'inputs'/a.input_set/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            assert target.read_bytes()==content,'immutable input mismatch: '+str(target)
        else:
            target.write_bytes(content)
        records.append(dict(path=str(target.relative_to(ROOT)),source_path=source,source_commit=a.commit,
                            sha256=hashlib.sha256(content).hexdigest(),bytes=len(content),
                            grain='coordinator-delivered package document or table; source-specific grain retained'))
    manifest=dict(input_set_id=a.input_set,source_commit=a.commit,files=records,acceptance=a.acceptance,
                  promotion='Only the explicitly stated scope; previous frozen sets unchanged')
    target=ROOT/'inputs'/a.input_set/'receipt.json'
    serialized=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    if target.exists():assert target.read_text()==serialized
    else:target.write_text(serialized)
    print(json.dumps(dict(input_set_id=a.input_set,source_commit=a.commit,files=len(records))))


if __name__=='__main__':main()
