#!/usr/bin/env python3
"""Verify explicitly completed shared packages; never mutate producer artifacts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def verify(request):
    directory = (ROOT / request['path']).resolve()
    manifest = directory / request.get('manifest', 'output_manifest.json')
    raw = manifest.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != request['sha256']:
        raise ValueError(f'manifest hash {digest} != {request["sha256"]}')
    entries = json.loads(raw)['files']
    if isinstance(entries, dict):
        entries = [dict(path=k, **(v if isinstance(v, dict) else {'sha256': v})) for k, v in entries.items()]
    checked = []
    for item in entries:
        name = item.get('path', item.get('file', item.get('relative_path')))
        if name is None:
            raise ValueError(f'missing file path: {item}')
        candidates = [Path(name)] if Path(name).is_absolute() else [directory / name, ROOT / name]
        candidates = [p.resolve() for p in candidates if p.is_file()]
        candidates = [p for p in candidates if p.is_relative_to(directory)]
        if not candidates:
            raise ValueError(f'file absent or outside owned scope: {name}')
        path = candidates[0]
        content = path.read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        expected = item.get('sha256', item.get('hash'))
        if actual != expected:
            raise ValueError(f'file hash mismatch: {name}')
        size = item.get('bytes', item.get('size_bytes', item.get('size')))
        if size is not None and len(content) != int(size):
            raise ValueError(f'file size mismatch: {name}')
        checked.append(dict(path=str(path.relative_to(ROOT)), sha256=actual, bytes=len(content)))
    return dict(package=request['package'], path=request['path'], status='HASHES_AND_WRITE_SCOPE_VERIFIED',
                manifest_sha256=digest, files=len(checked), bytes=sum(p['bytes'] for p in checked),
                declared_complete=True, market_or_operations_acceptance=False)


def main():
    requests = json.loads((BASE / 'intake_requests.json').read_text())['packages']
    results = []
    for request in requests:
        try:
            result = verify(request)
        except Exception as exc:
            result = dict(package=request['package'], path=request['path'], status='INTAKE_FAILED', error=str(exc))
        results.append(result)
    report = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Artifact integrity and owned write scope only; not empirical, financial or operational acceptance.',
                  packages=results)
    (BASE / 'sealed_intake.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(results, ensure_ascii=False))
    if any(r['status'] == 'INTAKE_FAILED' for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
