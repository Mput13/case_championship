#!/usr/bin/env python3
"""Root-owned forced SSH command, running as the unprivileged site deploy user."""
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

BASE = Path('/var/www/redwings')
MAX_ARCHIVE = 40 * 1024 * 1024
MAX_EXPANDED = 150 * 1024 * 1024


def unpack(stream, destination, revision):
    """No archive paths, symlinks or unchecked files may escape the release."""
    with tempfile.TemporaryFile() as buffer:
        remaining = MAX_ARCHIVE + 1
        while remaining:
            part = stream.read(min(1024 * 1024, remaining))
            if not part:
                break
            buffer.write(part)
            remaining -= len(part)
        if remaining == 0:
            raise ValueError('Archive exceeds size limit')
        buffer.seek(0)
        with tarfile.open(fileobj=buffer, mode='r:gz') as archive:
            members = archive.getmembers()
            if len(members) > 1000 or sum(m.size for m in members) > MAX_EXPANDED:
                raise ValueError('Expanded archive exceeds limits')
            names = set()
            for member in members:
                path = PurePosixPath(member.name)
                if (not member.isfile() or path.is_absolute() or '..' in path.parts
                        or any(p.startswith('.') for p in path.parts)
                        or str(path) != member.name or member.name in names
                        or path.suffix not in {'.html', '.png', '.xlsx', '.docx', '.json'}):
                    raise ValueError('Unsafe archive member: ' + member.name)
                names.add(member.name)
                target = destination / member.name
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                with target.open('wb') as output:
                    shutil.copyfileobj(archive.extractfile(member), output)
                target.chmod(0o644)
    manifest = json.loads((destination / 'release.json').read_text())
    if manifest['commit'] != revision:
        raise ValueError('Release revision mismatch')
    if names != set(manifest['files']) | {'release.json'}:
        raise ValueError('Unexpected or missing release files')
    for name, digest in manifest['files'].items():
        if hashlib.sha256((destination / name).read_bytes()).hexdigest() != digest:
            raise ValueError('File checksum mismatch: ' + name)
    if 'index.html' not in names or '<meta charset="utf-8">' not in (destination / 'index.html').read_text()[:1024].lower():
        raise ValueError('Invalid dashboard entry point')


def switch(base, release):
    temporary = base / '.current-next'
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(release)
    temporary.replace(base / 'current')


def activate(base, release, healthcheck):
    current = base / 'current'
    previous = current.resolve() if current.is_symlink() else None
    switch(base, release)
    try:
        healthcheck()
    except Exception:
        if previous:
            switch(base, previous)
        else:
            current.unlink(missing_ok=True)
        raise
    if previous and previous != release:
        marker = base / '.previous-next'
        marker.unlink(missing_ok=True)
        marker.symlink_to(previous)
        marker.replace(base / 'previous')


def main():
    command = os.environ.get('SSH_ORIGINAL_COMMAND', '')
    match = re.fullmatch(r'(deploy|rollback) ([0-9a-f]{40})', command)
    if not match:
        raise ValueError('Only deploy/rollback <full-commit-sha> is permitted')
    action, revision = match.groups()
    with (BASE / '.deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        releases = BASE / 'releases'
        release = releases / revision
        if action == 'deploy':
            staging = Path(tempfile.mkdtemp(prefix='.incoming-', dir=releases))
            try:
                unpack(sys.stdin.buffer, staging, revision)
                staging.chmod(0o755)
                if release.exists():
                    if (release / 'release.json').read_bytes() != (staging / 'release.json').read_bytes():
                        raise ValueError('Commit already exists with different files')
                    shutil.rmtree(staging)
                else:
                    staging.rename(release)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
        elif not release.is_dir():
            raise ValueError('Rollback release not found')

        def healthcheck():
            data = subprocess.check_output([
                '/usr/bin/curl', '--fail', '--silent', '--show-error', '--max-time', '15',
                '--resolve', 'redwings.altair.ad:443:127.0.0.1',
                'https://redwings.altair.ad/release.json'])
            if json.loads(data)['commit'] != revision:
                raise ValueError('Served release does not match requested commit')
            subprocess.run([
                '/usr/bin/curl', '--fail', '--silent', '--show-error', '--max-time', '15',
                '--resolve', 'redwings.altair.ad:443:127.0.0.1',
                '--output', '/dev/null', 'https://redwings.altair.ad/'], check=True)

        activate(BASE, release, healthcheck)
        print(f'{action}: {revision}; HTTPS health check passed')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Deployment failed: {error}', file=sys.stderr)
        sys.exit(1)
