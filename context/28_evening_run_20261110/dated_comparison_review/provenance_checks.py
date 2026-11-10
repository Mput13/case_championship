"""Verify receipt bytes and v2 preservation against exact Git objects."""
import hashlib,json
from pathlib import PurePosixPath
from prepare import HERE,PREFIX,SUBJECT,blob,git

files=git('ls-tree','-rz','--name-only',SUBJECT,PREFIX).decode().split('\0')
count=0;groups=[]
for path in files:
    if not path.endswith('/receipt.json'):continue
    receipt=json.loads(blob(path));commit=receipt.get('commit',receipt.get('source_commit'))
    if not commit or 'files' not in receipt:continue
    verified=0
    for r in receipt['files']:
        source=blob(r['source_path'],r.get('source_commit',commit))
        dest=str(PurePosixPath(path).parent/r['path']) if receipt.get('commit') else PREFIX+r['path']
        actual=blob(dest)
        assert actual==source and hashlib.sha256(actual).hexdigest()==r['sha256'],dest
        assert len(actual)==r['bytes'],dest
        if 'git_blob' in r:assert git('rev-parse',f"{r.get('source_commit',commit)}:{r['source_path']}").decode().strip()==r['git_blob'],dest
        verified+=1
    groups.append(dict(receipt=path,subject=commit,verified_copies=verified));count+=verified
previous='aa7779192d809558e38b1eb9bdfa25913a3afdc8'
v2=json.loads(blob(PREFIX+'output_manifest.json',previous))['files'];same=[];changed=[]
for r in v2:
    old=blob(PREFIX+r['path'],previous);actual=blob(PREFIX+r['path'])
    assert hashlib.sha256(old).hexdigest()==r['sha256']
    (same if old==actual else changed).append(r['path'])
assert len(v2)==156 and len(same)==154 and set(changed)=={'handoff.json','requests.json'}
assert count==313
result=dict(subject=SUBJECT,all_receipt_copies_verified=count,receipts=groups,previous_subject=previous,previous_manifest_files=len(v2),byte_identical=len(same),changed=changed,scope='Byte identity only; historical verdicts and limits retained separately')
(HERE/'receipt_and_preservation_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='receipts'}))
