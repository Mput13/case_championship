#!/usr/bin/env python3
from pathlib import Path
import datetime as dt
import hashlib
import json
import subprocess

BASE=Path(__file__).resolve().parent
SHA='9d9a874b1568c2cebec9cd3fc1f33ef76f37f450'
FILES=['src/demand_model.py','src/demand_summary.py','src/build_criteria.py','src/longlist_data.py','src/longlist_score.py','src/airports_meta.py','docs/23_demand_model.md','data/manual/known_flows.csv','data/processed/demand_fit.json','data/processed/demand_calibration.csv','data/processed/catchments.csv','data/processed/demand_pairs.csv','data/processed/demand_spokes.csv','data/processed/demand_by_candidate.csv','data/processed/destinations.csv','data/processed/longlist.csv','data/processed/criteria.json','data/assumptions/demand.csv','data/assumptions/longlist_weights.csv','data/raw/favt_subsidy_2026.csv','data/raw/_manifest.json']
def main():
    inputs=[]
    for path in FILES:
        b=subprocess.check_output(['git','show',SHA+':'+path]);p=BASE/'raw'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        inputs.append(dict(repo_path=path,local_path=str(p.relative_to(BASE)),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
    (BASE/'input_manifest.json').write_text(json.dumps(dict(author='kiruha355',input_sha=SHA,captured_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),execution_policy='git-show only; author code read, not executed/imported',files=inputs),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(files=len(inputs),bytes=sum(e['bytes'] for e in inputs))))
if __name__=='__main__':main()
