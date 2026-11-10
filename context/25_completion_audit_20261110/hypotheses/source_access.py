"""Read exact Git blobs for this finite audit; write only inside this package."""
from pathlib import Path
import csv
import hashlib
import io
import json
import subprocess

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
PINS = {
    "base": "f8b94a5c8b28e51664c5fff4a11606fb8f41c4d6",
    "hypotheses": "6ed8788882e7b4d07044b4f6e686ff71eadd8ac5",
    "frontier": "519998ed8c97ce5499f356a6d0f81558c7f6ee14",
    "review": "58a02028e062b1abd803d99e19f630b75ec80657",
    "methods": "a77e4cfbd14e560d26407479b7252cfcb15f4f41",
    "economics21": "93fa5cf4a10ab67e05c93d19fc5375fc58ef9299",
}
H = "context/16_agent_research/hypotheses/"
F = "context/23_night_run_20261110/hypothesis_frontier/"
R = "context/23_night_run_20261110/hypothesis_frontier_review/"
M = "context/23_night_run_20261110/methods/"


def source(label, path):
    blob = subprocess.check_output(["git", "show", f"{PINS[label]}:{path}"], cwd=REPO)
    local = OUT / "sources" / label / path
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(blob)
    return blob.decode("utf-8-sig")


def rows(label, path):
    return list(csv.DictReader(io.StringIO(source(label, path))))


def obj(label, path):
    return json.loads(source(label, path))


def evidence(label, path, line, end=None):
    text = source(label, path)
    assert 1 <= line <= (end or line) <= len(text.splitlines())
    return {"commit": PINS[label], "path": path, "line": line,
            "line_end": end or line,
            "local_path": str((Path("sources") / label / path).as_posix())}


def at(label, path, needle):
    lines = source(label, path).splitlines()
    line = next(i for i, value in enumerate(lines, 1) if needle in value)
    return evidence(label, path, line)


def write_csv(name, values):
    assert values
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                      allow_nan=False) + "\n", encoding="utf-8")


def seal_sources():
    values = []
    for file in sorted((OUT / "sources").rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(OUT / "sources")
        label, *parts = relative.parts
        path = "/".join(parts)
        blob = file.read_bytes()
        expected = subprocess.check_output(["git", "show", f"{PINS[label]}:{path}"], cwd=REPO)
        assert blob == expected, (label, path)
        values.append({"commit": PINS[label], "path": path,
                       "local_path": str(file.relative_to(OUT)),
                       "sha256": hashlib.sha256(blob).hexdigest(),
                       "bytes": len(blob), "lines": len(blob.splitlines()),
                       "verification": "EXACT_GIT_BYTES; not external source validation"})
    dump("source_manifest.json", {"pins": PINS, "files": values})
    return values
