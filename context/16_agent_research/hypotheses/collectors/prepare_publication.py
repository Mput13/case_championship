#!/usr/bin/env python3
"""Preserve local originals and strip HTTP cookies/auth from publication copies."""
from pathlib import Path
import hashlib,json
from publication_headers import clean_public_metadata, PUBLIC_HEADERS
ROOT=Path(__file__).resolve().parents[1]
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def fingerprint(path):return {'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def main():
    transformations=[]
    pairs=[('contributions/source_access/dataset_manifest.json','contributions/source_access/dataset_manifest_public.json'),('contributions/existing_map/review_evidence/front_audit_20261109/primary_manifest.json','contributions/existing_map/review_evidence/front_audit_20261109/primary_manifest_public.json')]
    for src,dst in pairs:
        raw=(ROOT/src).read_bytes();out=clean_public_metadata(json.loads(raw))
        if isinstance(out,dict):
            out['publication_transformation']={'original_local_path':src,'original_sha256':hashlib.sha256(raw).hexdigest(),'method':'remove forbidden keys; HTTP header whitelist; original unchanged'}
        write(ROOT/dst,out)
        transformations.append({'originals':[fingerprint(ROOT/src)],'stored':fingerprint(ROOT/dst)})
    originals=sorted((ROOT/'contributions/source_access/raw').glob('*.json'))
    receipts={p.name:clean_public_metadata(json.loads(p.read_text())) for p in originals}
    destination=ROOT/'contributions/source_access/public_receipts.json';write(destination,receipts)
    transformations.append({'originals':[fingerprint(p) for p in originals],'stored':fingerprint(destination)})
    write(ROOT/'publication_transforms.json',{'method':'remove forbidden keys; HTTP header whitelist; no raw modification','allowed_headers':sorted(PUBLIC_HEADERS),'transformations':transformations})
if __name__=='__main__':main()
