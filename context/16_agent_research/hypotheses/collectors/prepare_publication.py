#!/usr/bin/env python3
"""Preserve local originals and strip HTTP cookies/auth from publication copies."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
MARKER='[OMITTED_FROM_PUBLICATION]'
def clean(value):
    if isinstance(value,dict):
        return {k:MARKER if any(w in k.lower() for w in ['cookie','authorization','token']) else clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    return value
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def main():
    pairs=[('contributions/source_access/dataset_manifest.json','contributions/source_access/dataset_manifest_public.json'),('contributions/existing_map/review_evidence/front_audit_20261109/primary_manifest.json','contributions/existing_map/review_evidence/front_audit_20261109/primary_manifest_public.json')]
    for src,dst in pairs:
        raw=(ROOT/src).read_bytes();out=clean(json.loads(raw))
        if isinstance(out,dict):
            out['publication_transformation']={'original_local_path':src,'original_sha256':hashlib.sha256(raw).hexdigest(),'method':'recursive redaction of cookie/authorization/token keys; original unchanged'}
        write(ROOT/dst,out)
    receipts={p.name:clean(json.loads(p.read_text())) for p in (ROOT/'contributions/source_access/raw').glob('*.json')}
    write(ROOT/'contributions/source_access/public_receipts.json',receipts)
if __name__=='__main__':main()
