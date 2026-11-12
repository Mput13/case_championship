"""Хеши завершённого локального пакета, без Git операций изменения."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
items=[]
for f in sorted(ROOT.rglob('*')):
    if not f.is_file() or f.name=='output_manifest.json' or '__pycache__' in f.parts:continue
    b=f.read_bytes();items.append(dict(path=str(f.relative_to(ROOT)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),role='public_source' if 'evidence' in f.parts else 'visual_source_check' if 'qa' in f.parts else 'research_or_reproduction'))
out={'package_id':'KZN-research-v1','sealed_at_utc':datetime.now(timezone.utc).isoformat(),'write_root':str(ROOT),'status':'STAGE_A_COMPLETE_STAGE_B_NOT_RUN','manifest_excludes':['output_manifest.json (self hash supplied in coordinator message)','__pycache__ (removed task-local cache)'],'input_pins':json.loads((ROOT/'input_manifest.json').read_text())['pins'],'validation':'validation.json:13 self-checks PASS; not independent acceptance','file_count':len(items),'total_bytes':sum(x['bytes'] for x in items),'files':items,'reproduce':['python3 collect.py pins (read exact Git blobs; no mutation)','python3 parse_schedule.py','python3 build_bundle.py','python3 build_programmes.py','python3 polish.py','python3 validate.py','python3 seal.py'],'refetch_policy':'Публичные источники не загружаются повторно при воспроизведении. Новый fetch — новая версия evidence с receipt; не переписывать frozen результаты.'}
target=ROOT/'output_manifest.json';target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('files',len(items),'bytes',out['total_bytes'],'manifest_sha256',hashlib.sha256(target.read_bytes()).hexdigest())
