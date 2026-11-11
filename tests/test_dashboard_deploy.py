"""Deployment failure must preserve the old website; archives cannot escape staging."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

if os.name != "posix":
    raise unittest.SkipTest("Deployment receiver uses POSIX locking; tested on Linux in CI")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('receiver', ROOT / 'deploy/dashboard_receiver.py')
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)
SHA = 'a' * 40


def archive(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        for name, data in files.items():
            item = tarfile.TarInfo(name)
            item.size = len(data)
            tar.addfile(item, io.BytesIO(data))
    buffer.seek(0)
    return buffer


class DeployTests(unittest.TestCase):
    def test_valid_release_checks_manifest(self):
        html = b'<meta charset="utf-8"><title>test</title>'
        manifest = json.dumps({'commit': SHA, 'files': {'index.html': hashlib.sha256(html).hexdigest()}}).encode()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receiver.unpack(archive({'index.html': html, 'release.json': manifest}), root, SHA)
            self.assertEqual((root / 'index.html').read_bytes(), html)

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                receiver.unpack(archive({'../escaped.html': b'bad'}), Path(tmp), SHA)

    def test_corrupt_file_rejected(self):
        manifest = json.dumps({'commit': SHA, 'files': {'index.html': '0' * 64}}).encode()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'checksum'):
                receiver.unpack(archive({'index.html': b'changed', 'release.json': manifest}), Path(tmp), SHA)

    def test_failed_healthcheck_restores_previous_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old, new = base / 'old', base / 'new'
            old.mkdir()
            new.mkdir()
            (base / 'current').symlink_to(old)
            def fail():
                raise RuntimeError('site unavailable')
            with self.assertRaises(RuntimeError):
                receiver.activate(base, new, fail)
            self.assertEqual((base / 'current').resolve(), old.resolve())

    def test_success_records_rollback_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old, new = base / 'old', base / 'new'
            old.mkdir()
            new.mkdir()
            (base / 'current').symlink_to(old)
            receiver.activate(base, new, lambda: None)
            self.assertEqual((base / 'current').resolve(), new.resolve())
            self.assertEqual((base / 'previous').resolve(), old.resolve())


if __name__ == '__main__':
    unittest.main()
