#!/usr/bin/env python3
"""Reproduce the frozen MR02 package offline; no new dependencies or sources."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for name in ['freeze_inputs.py', 'overlay.py', 'build_registry.py', 'reference_impact.py', 'checks.py', 'verify_package.py']:
    subprocess.run([sys.executable, '-B', str(ROOT / name)], cwd=ROOT,
                   env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, check=True)
