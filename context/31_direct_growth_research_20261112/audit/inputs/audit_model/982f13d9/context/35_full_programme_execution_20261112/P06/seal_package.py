"""Seal this package's files; manifest excludes itself and Python bytecode."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = []
for p in sorted(ROOT.rglob("*")):
    if not p.is_file() or "__pycache__" in p.parts or p.suffix == ".pyc" or p.name == "output_manifest.json":
        continue
    data = p.read_bytes()
    rows.append({"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
(ROOT / "output_manifest.json").write_text(json.dumps({"package": "P06", "manifest_excludes": ["output_manifest.json", "__pycache__", "*.pyc"], "files": rows}, ensure_ascii=False, indent=2) + "\n")
print(hashlib.sha256((ROOT / "output_manifest.json").read_bytes()).hexdigest())
