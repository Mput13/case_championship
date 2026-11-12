#!/usr/bin/env python3
"""Пересобрать только этот пакет из сохранённых источников. Не делает сетевых/Git mutations."""
from pathlib import Path
import subprocess,sys
p=Path(__file__).resolve().parent
for name in ['build_monthly.py','finalize_qualification.py','extend_kja.py','finalize_package.py','annotate_overlap.py','validate.py','write_manifest.py']:
 result=subprocess.run([sys.executable,str(p/name)],capture_output=True,text=True)
 print(name+': '+result.stdout.strip()[-1500:])
 if result.stderr:print(result.stderr,file=sys.stderr)
 result.check_returncode()
