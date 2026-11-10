"""Verify review artifact structure/scope and record hashes, no author execution."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
PREFIX = "context/23_night_run_20261110/screening_review/"

def main():
    paths = sorted(p for p in HERE.iterdir() if p.is_file() and p.name not in ("review_manifest.json", "package_checks.json"))
    for p in paths:
        assert not p.is_symlink()
        assert p.stat().st_size < 150_000
        text = p.read_text()
        assert not re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=]{20,}", text)
        assert not re.search(r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b", text)
        if p.suffix == ".json":
            json.loads(text)
        if p.suffix == ".md":
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if "://" not in link and not link.startswith("#"):
                    assert (HERE/link.split("#")[0]).is_file(), (p, link)
    status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"]).decode().splitlines()
    for r in status:
        assert r[3:].startswith(PREFIX), r
    before = json.loads((HERE/"snapshot_manifest.json").read_text())
    for r in before["files"]:
        assert hashlib.sha256((HERE/r["snapshot_path"]).read_bytes()).hexdigest() == r["sha256"]
    manifest = {"reviewed_commit": before["reviewed_commit"], "files": {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths}, "excluded_local_runtime": [".frozen/", "raw_public/", "__pycache__/"], "self_excluded": ["review_manifest.json", "package_checks.json"]}
    (HERE/"review_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    result = {"status": "PASS", "review_files_hashed": len(paths), "frozen_files_unchanged": len(before["files"]), "changed_paths_scope": PREFIX, "json_and_markdown_links": "PASS", "author_code_executed": False}
    (HERE/"package_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
