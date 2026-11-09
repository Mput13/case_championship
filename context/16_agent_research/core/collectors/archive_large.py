#!/usr/bin/env python3
"""Keep large local evidence outside Git; make deterministic compressed exports."""
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    records=[];ignore=['# Large evidence retained locally, SHA and collectors in external_artifacts_manifest.json','**/__pycache__/']
    for f in sorted(ROOT.rglob('*')):
        if not f.is_file() or f.stat().st_size<=5_000_000:continue
        rel=f.relative_to(ROOT)
        if 'raw' not in rel.parts and 'normalized' not in rel.parts:continue
        b=f.read_bytes();r=dict(path=rel.as_posix(),absolute_local_path=str(f),size_bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),
            storage='RETAINED_LOCAL_IGNORED_BY_GIT',reproduction='See dataset_manifest.json and source collector; verify historical SHA after re-fetch')
        ignore.append('/'+rel.as_posix())
        if f.suffix=='.csv':
            export=ROOT/'normalized/large_exports'/(f.parent.parent.name+'__'+f.name+'.gz');export.parent.mkdir(parents=True,exist_ok=True)
            cb=gzip.compress(b,mtime=0);export.write_bytes(cb)
            r.update(compressed_export_path=str(export.relative_to(ROOT)),compressed_sha256=hashlib.sha256(cb).hexdigest(),compressed_size_bytes=len(cb))
        records.append(r)
    (ROOT/'.gitignore').write_text('\n'.join(ignore)+'\n')
    (ROOT/'external_artifacts_manifest.json').write_text(json.dumps(dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        note='Actual local bytes retained; no deletion. Copy these files from the source worktree when integrating, or use collectors then verify SHA. Large CSVs additionally supplied as deterministic gzip exports.',artifacts=records),ensure_ascii=False,indent=2)+'\n')
    print('local ignored artifacts',len(records),'bytes',sum(r['size_bytes'] for r in records))
if __name__=='__main__':main()
