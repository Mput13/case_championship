#!/usr/bin/env python3
"""Owner integrity receipt, not independent acceptance. --verify is read-only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

B=Path(__file__).resolve().parent
AUTHOR="4a9763565f70b9ab1eddde2f5daca07687560948"
ROOT="4a9971beeacbc40559943eae05b9004c90165917"
old="context/16_agent_research/coordinator/20261109T154615Z/hypotheses/c14_products/3906edd033f75bc6/flight_hotel_calendar.csv"
sha=lambda b:hashlib.sha256(b).hexdigest()
items=[]
for p in sorted((B/"inputs").rglob("*")):
    if not p.is_file():continue
    r=str(p.relative_to(B)); raw=p.read_bytes()
    row=dict(path=r,bytes=len(raw),sha256=sha(raw))
    if r.startswith("inputs/nastya/"):
        source=r.removeprefix("inputs/nastya/"); commit=AUTHOR
    elif p.name=="c14_old_flight_hotel.csv": source=old;commit=ROOT
    elif p.name=="ourairports_ru.csv": source="context/07_verification/terra_data/samples/ourairports_ru.csv";commit=AUTHOR
    elif r.startswith("inputs/evidence_06cb721b/") and p.name not in ["pin_manifest.json","reextracted.txt","page14.png","page15.png"]:
        source="context/28_evening_run_20261110/evidence/"+r.removeprefix("inputs/evidence_06cb721b/");commit="06cb721b3e8e4eb8710c065c7b02078a112626a9"
    elif r.startswith("inputs/evidence_38f0f7ae/") and p.name!="pin_manifest.json":
        source="context/28_evening_run_20261110/evidence/"+r.removeprefix("inputs/evidence_38f0f7ae/");commit="38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b"
    else:source=None;commit=None
    if source:
        exact=subprocess.check_output(["git","show",commit+":"+source],cwd=B)
        if exact!=raw:raise SystemExit("Pin mismatch: "+r)
        row.update(commit=commit,source_path=source,evidence="EXACT_GIT_BLOB")
    else:row.update(evidence="HTTP_CAPTURE_OR_DERIVED_EXTRACTION",receipt="inputs/web/fetch_receipts.json")
    items.append(row)
for name in ["parameters.json","calculate.py","extensions.py","validate.py","source_addendum.py"]:
    raw=(B/name).read_bytes();items.append(dict(path=name,bytes=len(raw),sha256=sha(raw),evidence="OWNER_SCENARIO_OR_CODE_NOT_MARKET_FACT"))
payload={"root_commit":ROOT,"author_commit":AUTHOR,"owner_integrity_only":True,"files":items}
target=B/"input_manifest.json"
if "--verify" in sys.argv:
    saved=json.loads(target.read_text())
    if payload!=saved:raise SystemExit("Input manifest mismatch")
    for row in json.loads((B/"outputs/manifest.json").read_text()):
        if sha((B/row['path']).read_bytes())!=row['sha256']:raise SystemExit("Output mismatch: "+row['path'])
    delivery=B/"delivery_manifest.json"
    if delivery.exists():
        records=json.loads(delivery.read_text())['files']
        current={str(p.relative_to(B)) for p in B.rglob('*') if p.is_file() and p.name!='delivery_manifest.json'}
        if current!={r['path'] for r in records}:raise SystemExit('Delivery file set mismatch')
        for r in records:
            if sha((B/r['path']).read_bytes())!=r['sha256']:raise SystemExit('Delivery hash mismatch: '+r['path'])
    print("Pinned inputs, output and delivery hashes verified")
else:
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print("Wrote input manifest for",len(items),"files")
    if '--seal' in sys.argv:
        files=[]
        for p in sorted(B.rglob('*')):
            if p.is_file() and p.name!='delivery_manifest.json':
                raw=p.read_bytes();files.append(dict(path=str(p.relative_to(B)),bytes=len(raw),sha256=sha(raw)))
        (B/'delivery_manifest.json').write_text(json.dumps(dict(owner_integrity_only=True,first_slice_commit='a39165528ceaa80f026210d0aaae9e2b541e6f51',evidence_final_commit='38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b',files=files),ensure_ascii=False,indent=2)+'\n')
        print('Sealed',len(files),'delivery files')
