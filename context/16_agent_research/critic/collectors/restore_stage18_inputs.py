#!/usr/bin/env python3
"""Restore exact pinned Git blobs for stage18 replay, verifying recorded hashes."""
from pathlib import Path
import hashlib
import json
import subprocess

BASE=Path(__file__).resolve().parents[1]/'stage18_audit'
def main():
    m=json.loads((BASE/'input_manifest.json').read_text())
    for e in m['files']:
        p=BASE/e['local_path'];p.resolve().relative_to(BASE.resolve())
        b=subprocess.check_output(['git','show',m['input_sha']+':'+e['repo_path']])
        assert hashlib.sha256(b).hexdigest()==e['sha256'],e['repo_path']
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    print(json.dumps({'restored_git_files':len(m['files']),'input_sha':m['input_sha']}))
if __name__=='__main__':main()
