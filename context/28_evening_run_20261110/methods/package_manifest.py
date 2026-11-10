import argparse,hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent
f=p/'output_manifest.json'
rows=[]
for x in sorted(p.rglob('*')):
 if not x.is_file() or x==f or any(t in ('.runtime','__pycache__') for t in x.relative_to(p).parts) or x.suffix=='.pyc':continue
 b=x.read_bytes();rows.append({'path':str(x.relative_to(p)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
if '--check' in __import__('sys').argv:
 assert rows==json.loads(f.read_text())['files'],'manifest mismatch'
else:f.write_text(json.dumps({'scope':'context/28_evening_run_20261110/methods/','files':rows},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'files':len(rows),'status':'PASS_HASHES' if '--check' in __import__('sys').argv else 'WRITTEN'}))
