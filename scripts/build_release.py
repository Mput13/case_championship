"""Сборка из сохранённых данных, без обновления внешних источников."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
steps = [
    ["src/fetch_favt_airports.py", "--from-cache"],
    ["src/transfer_potential.py"], ["src/build_longlist.py"],
    ["src/build_criteria.py"], ["src/longlist_score.py"],
    ["src/network_model.py"], ["src/network_map.py"],
    ["src/build_workbook.py"], ["src/build_dashboard.py"],
    ["scripts/refresh_release_notes.py"],
    ["-m", "pytest", "tests", "-q"], ["scripts/check_release.py"],
]
for args in steps:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)
