#!/usr/bin/env python3
"""Manifest exact P10 deliverables; excludes caches and manifest itself."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
v=json.loads((R/'verification.json').read_text())
assert v['status']=='PASS'
files=[]
for p in sorted(R.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts or p.name=='output_manifest.json':continue
 b=p.read_bytes();files.append({'path':str(p.relative_to(R)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
out={'package':'P10','version':'P10-1.0-20261112','status':'STAGE_A_RESEARCH_READY_STAGE_B_INTEGRATION_PENDING','write_scope':str(R),'git_operations':'none;coordinatorcommits','manifest_self_excluded':True,'files':files,'validation':{'path':'verification.json','sha256':hashlib.sha256((R/'verification.json').read_bytes()).hexdigest(),'author_pass':f'{v["passed"]}/{v["total"]}','independent_review':'PENDING'},'unknown_rule':'JSONnull;emptyactualnumericCSVfieldmeansUNKNOWNnotzero','not_run':v['not_run']}
(R/'output_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'files':len(files),'bytes':sum(x['bytes'] for x in files),'manifest_sha256':hashlib.sha256((R/'output_manifest.json').read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
