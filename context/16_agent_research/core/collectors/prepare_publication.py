#!/usr/bin/env python3
"""Hold large/uncleared raw locally; publish numeric facts and collectors.

This is a conservative checkpoint policy, not a legal conclusion about the source.
No local evidence is deleted or rewritten. Headers are checked by finalize_core.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALLOW={
 'raw/public/ourairports_airports.csv.gz','raw/public/ourairports_runways.csv',
 'raw/public/tochno_intercity_zip.zip','raw/public/geonames_cities15000.zip',
}
def main():
    hold=[];ignores=['# Publication holds; original local evidence retained. See publication_manifest.json.','**/__pycache__/']
    for f in sorted(ROOT.rglob('*')):
        if not f.is_file() or '__pycache__' in f.parts:continue
        rel=f.relative_to(ROOT).as_posix();parts=f.relative_to(ROOT).parts;reason=None
        if 'raw' in parts:
            if rel not in ALLOW:
                if rel.startswith('branches/social_economy/raw/tochno_') and f.suffix=='.zip':pass
                else:reason='Raw/support republication clearance pending; source may contain official names, signatures, public contacts or full copyrighted text'
        if 'normalized' in parts and f.suffix in {'.png','.txt'}:reason='Full-source text/render retained locally; numeric extraction published separately'
        if rel=='normalized/telegram_main_favt_ru.csv':reason='Full public-message text retained locally; selected numeric claims published separately'
        if f.stat().st_size>5_000_000:reason='Large artifact retained locally; compressed CSV export where available'
        if reason:
            ignores.append('/'+rel);hold.append(dict(path=rel,absolute_local_path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),size_bytes=f.stat().st_size,reason=reason))
    (ROOT/'.gitignore').write_text('\n'.join(ignores)+'\n')
    (ROOT/'publication_manifest.json').write_text(json.dumps(dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),status='CHECKPOINT_POLICY',
        note='Ignored original bytes remain on disk. Missing in Git is not source unavailability. No acceptance promotion from publication.',
        excluded_local_files=hold),ensure_ascii=False,indent=2)+'\n')
    print('Publication holds',len(hold),'local bytes',sum(r['size_bytes'] for r in hold))
if __name__=='__main__':main()
