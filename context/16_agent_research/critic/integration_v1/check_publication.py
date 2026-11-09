#!/usr/bin/env python3
"""Scoped checkpoint checks; all emitted files stay in integration_v1."""
import ast
import datetime as dt
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

BASE=Path(__file__).resolve().parent
HELPERS=runpy.run_path(str(BASE.parent/'collectors/check_publication.py'))
REPO=HELPERS['REPO'];PREFIX=BASE.relative_to(REPO).as_posix()+'/'

def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
def main():
    paths=[x for x in git('diff','--cached','--name-only','--diff-filter=ACMR','-z').decode().split('\0')if x]
    issues=[];sizes=[]
    for path in paths:
        if not path.startswith(PREFIX):issues.append(dict(path=path,kind='OUTSIDE_PHASE2_ROLE_SCOPE'));continue
        if '/raw/'in path or Path(path).suffix in {'.html','.pdf','.png','.gz','.zip','.pyc'}:issues.append(dict(path=path,kind='HELD_RAW_OR_BINARY'))
        data=git('show',':'+path);sizes.append(len(data));text=data.decode()
        for label,pattern in HELPERS['PATTERNS'].items():
            if pattern.search(text):issues.append(dict(path=path,kind=label))
        if path.endswith('.json'):issues.extend(HELPERS['forbidden_keys'](json.loads(text),path))
        if path.endswith('.py'):ast.parse(text)
    raw=[]
    for path in sorted((BASE/'raw').rglob('*')):
        if path.is_file():
            data=path.read_bytes();raw.append(dict(path=path.relative_to(BASE).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),storage='LOCAL_IGNORED_PRESERVED'))
    (BASE/'local_raw_manifest.json').write_text(json.dumps(dict(files=raw,total_bytes=sum(x['bytes']for x in raw)),indent=2)+'\n')
    result=dict(checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),staged_paths=len(paths),issues=issues,largest_bytes=max(sizes,default=0),local_raw_files=len(raw),local_raw_bytes=sum(x['bytes']for x in raw),licence_policy='Copied frozen inputs kept local ignored; own numerical checks/metadata and project contract only published',acceptance_change='NONE; arithmetic separate from market/operations')
    (BASE/'publication_check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not issues

if __name__=='__main__':main()
