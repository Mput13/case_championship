"""Manifest локального завершённого пакета; Git mutations отсутствуют."""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
files=[]
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or p.name in ['manifest.json','manifest.sha256'] or '__pycache__' in p.parts:continue
 b=p.read_bytes()
 files.append({'path':str(p.relative_to(ROOT)),'repository_path':str(p.relative_to(ROOT.parents[4])),
  'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
manifest={'package_id':'P08-SVX-A','stage':'A','stage_A_status':'COMPLETE_RESEARCH_PACKAGE','stage_B_status':'NOT_RUN_P05_P06_PENDING',
 'sealed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'write_boundary':'context/35_full_programme_execution_20261112/P08/SVX/research_v1/',
 'hash_algorithm':'SHA256 bytes; manifest and its digest excluded to avoid self reference',
 'total_files':len(files),'total_bytes':sum(x['bytes'] for x in files),'files':files,
 'review_entrypoints':['HANDOFF.md','direct_candidates.csv','programme_candidates.json','hypothesis_dispositions.csv','comparison_requests.csv','verification.json'],
 'publication':'Координатор может коммитить только этот список; исследователь не выполнял Git mutations, публикацию или внешние сообщения кроме разрешённого координатора'}
raw=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
(ROOT/'manifest.json').write_bytes(raw)
digest=hashlib.sha256(raw).hexdigest()
(ROOT/'manifest.sha256').write_text(digest+'  manifest.json\n')
print(json.dumps({'files':len(files),'bytes':manifest['total_bytes'],'manifest_sha256':digest}))
