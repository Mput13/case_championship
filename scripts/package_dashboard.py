#!/usr/bin/env python3
"""Validate and package committed public outputs; never refresh research inputs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from html.parser import HTMLParser
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {'.html', '.png', '.xlsx', '.docx'}


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script':
            self.active = not attrs.get('src') and attrs.get('type', '') in ('', 'text/javascript', 'module')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def validate_html(data):
    text = data.decode('utf-8')
    if not re.search(r'<meta\s+charset=["\']utf-8["\']', text[:1024], re.I):
        raise ValueError('UTF-8 declaration must be in the first 1024 characters')
    if '<title>' not in text.lower():
        raise ValueError('HTML title missing')
    parser = Scripts()
    parser.feed(text)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / 'inline.js'
        source.write_text('\n'.join(parser.parts), encoding='utf-8')
        subprocess.run(['node', '--check', str(source)], check=True)
    return text


def package(root, revision, output):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Expected full Git commit SHA')
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', 'outputs'], cwd=root).decode().split('\0')
    files = {}
    for name in filter(None, tracked):
        path = root / name
        if path.suffix not in EXTENSIONS:
            continue
        if path.is_symlink():
            raise ValueError('Symlink in outputs: ' + name)
        data = path.read_bytes()
        if not data:
            raise ValueError('Empty public output: ' + name)
        if path.suffix == '.html':
            if name != 'outputs/redwings_panel.html' and not re.search(br'<meta\s+charset=', data[:1024], re.I):
                data = b'<meta charset="utf-8">\n' + data
            validate_html(data)
        if path.suffix in ('.xlsx', '.docx'):
            with zipfile.ZipFile(io.BytesIO(data)) as document:
                if document.testzip() is not None:
                    raise ValueError('Corrupt Office document: ' + name)
        files[name] = data
        # Root URLs and the original /outputs/... URLs both remain usable.
        files[str(Path(name).relative_to('outputs'))] = data
    panel = files.get('outputs/redwings_panel.html')
    if panel is None:
        raise ValueError('Dashboard output missing')
    text = panel.decode('utf-8')
    match = re.search(r'\bconst D\s*=\s*', text)
    if match is None:
        raise ValueError('Embedded dashboard data missing')
    payload, _ = json.JSONDecoder().raw_decode(text[match.end():])
    if not payload.get('cities'):
        raise ValueError('Dashboard city data is empty')
    files['index.html'] = panel
    files['release.json'] = (json.dumps({'commit': revision, 'files': {
        name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())
    }}, ensure_ascii=False, indent=2) + '\n').encode()
    with tarfile.open(output, 'w:gz') as archive:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    print(f'Validated {len(files)} public files; commit {revision}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--revision', required=True)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    package(ROOT, args.revision, args.output)
