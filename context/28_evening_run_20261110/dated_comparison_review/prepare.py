"""Extract only exact-subject inputs into review-owned disposable runtime."""
import hashlib,json,subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SUBJECT='f99d6cd52dcc06995bf984fddd2f057226243b06'
PREFIX='context/28_evening_run_20261110/methods/'
SNAP=HERE/'_runtime/methods'

def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args])

def blob(path,commit=SUBJECT):
    return git('show',f'{commit}:{path}')

def required(p):
    return ('/' not in p or p.startswith(('runs/','inputs/nastya_4a976/','inputs/products_3889/'))
            or p=='inputs/audit_5905/replay/inputs/tochno_intercity.csv.gz')

def main():
    entries=[]; copied=[]
    for rec in git('ls-tree','-rz',SUBJECT,PREFIX).split(b'\0'):
        if not rec:continue
        meta,p=rec.split(b'\t');mode,kind,oid=meta.decode().split();path=p.decode();rel=path[len(PREFIX):]
        data=blob(path)
        row=dict(path=path,git_blob=oid,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
        entries.append(row)
        if required(rel):
            target=SNAP/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);copied.append(rel)
    index={r['path'][len(PREFIX):]:r for r in entries}
    manifest=json.loads(blob(PREFIX+'output_manifest.json'))
    hashes=[]
    for r in manifest['files']:
        actual=index[r['path']]
        assert actual['sha256']==r['sha256'] and actual['bytes']==r['bytes'],r['path']
        hashes.append(r['path'])
    receipts=[]
    src=json.loads(blob(PREFIX+'source_manifest.json'))
    for r in src['files']:
        data=blob(r['source_path'],r['source_commit'])
        target=blob(PREFIX+r['path'])
        assert data==target and hashlib.sha256(data).hexdigest()==r['sha256'],r['path']
        if 'git_blob' in r:assert git('rev-parse',f"{r['source_commit']}:{r['source_path']}").decode().strip()==r['git_blob']
        receipts.append(r['path'])
    (HERE/'source_manifest.json').write_text(json.dumps(dict(subject=SUBJECT,files=entries),indent=2)+'\n')
    result=dict(subject=SUBJECT,output_hashes_verified=len(hashes),source_receipt_copies_verified=len(receipts),copied_files=len(copied),copied_bytes=sum(index[p]['bytes'] for p in copied),runtime_excludes='No .git/dependencies; only root modules, runs, owner arithmetic inputs, final products and compressed demand input')
    (HERE/'provenance_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
