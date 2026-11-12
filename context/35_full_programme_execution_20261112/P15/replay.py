#!/usr/bin/env python3
"""Offline Stage A replay; optional exact Git P09 projection binding."""
import argparse,pathlib
from dataadapter import build
P=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--results-commit');p.add_argument('--results-path');a=p.parse_args()
build(str(P/'branch_intake.json'),a.results_commit,a.results_path,snapshot_only=True)
