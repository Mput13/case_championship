"""Extract only the reviewed Git tree; never read a moving author directory."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
SHA = "82dffa795146ccc575db1bb45ba9391af44def00"
PREFIX = "context/23_night_run_20261110/screening/"

def git(*args):
    return subprocess.check_output(["git", *args])

def main():
    records = []
    for path in git("ls-tree", "-r", "--name-only", SHA, PREFIX).decode().splitlines():
        raw = git("show", f"{SHA}:{path}")
        rel = path[len(PREFIX):]
        dest = ROOT / ".frozen" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        records.append({"path": path, "snapshot_path": ".frozen/" + rel,
                        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                        "git_blob": git("rev-parse", f"{SHA}:{path}").decode().strip()})
    doc = {"reviewed_commit": SHA,
           "git_metadata": git("show", "--no-patch", "--format=%H%nAuthor: %an%nAuthorDate: %aI%nCommitter: %cn%nCommitDate: %cI%nSubject: %s", SHA).decode(),
           "files": records}
    (ROOT / "snapshot_manifest.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({"files": len(records), "bytes": sum(r["bytes"] for r in records)}))

if __name__ == "__main__":
    main()
