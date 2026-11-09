#!/usr/bin/env python3
"""One bounded fetch and immutable ref comparison; never merges or executes inputs."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'context/16_agent_research'


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True,
                          capture_output=True, text=True, timeout=120).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    now = datetime.now(timezone.utc).isoformat()
    previous = json.loads((BASE / 'colleague_refs.json').read_text())
    if args.fetch:
        git('fetch', 'origin')  # Fail without advancing last-successful snapshot.
    refs = {}
    for line in git('for-each-ref', '--format=%(refname:short)\t%(objectname)\t%(symref)',
                    'refs/remotes/origin').splitlines():
        ref, sha, symref = line.split('\t')
        if not symref:
            refs[ref] = sha
    changes = []
    for ref, sha in refs.items():
        old = previous['refs'].get(ref)
        if old == sha:
            continue
        files = git('diff', '--name-status', old, sha) if old else git(
            'diff-tree', '--root', '--no-commit-id', '--name-status', '-r', sha)
        changes.append({'ref': ref, 'old_sha': old, 'new_sha': sha,
                        'head_summary': git('show', '-s', '--format=%aI | %an | %s', sha).strip(),
                        'files': files.splitlines(), 'review_status': 'NOT_REVIEWED'})
    removed = [ref for ref in previous['refs'] if ref not in refs and ref != 'origin']
    event = {'checked_at_utc': now, 'fetched': args.fetch, 'changes': changes,
             'removed_refs': removed}
    with (BASE / 'updates.jsonl').open('a') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
    (BASE / 'colleague_refs.json').write_text(json.dumps(
        {'checked_at_utc': now, 'refs': refs}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(event, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
