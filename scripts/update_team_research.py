#!/usr/bin/env python3
"""Rebuild the team update offline without overwriting historical/team outputs."""
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
for script in ['collect_team_context.py','build_team_comparison.py','verify_team_update.py']:
    subprocess.run([sys.executable,str(root/'scripts'/script)],cwd=root,check=True)
