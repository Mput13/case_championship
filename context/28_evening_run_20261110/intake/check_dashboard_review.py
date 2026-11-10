import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

SHA='c39511430b7578f1f80a71eb77bea512b0afc6a4'
P='context/28_evening_run_20261110/dashboard_handoff_review/'
def blob(sha,path): return subprocess.check_output(['git','show',sha+':'+path])
def obj(path): return json.loads(blob(SHA,P+path))
outputs=obj('output_manifest.json')['outputs']
for r in outputs:
    b=blob(SHA,P+r['path']); assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
inputs=obj('source_manifest.json')['inputs']
for r in inputs:
    b=blob(r['commit'],r['path']); assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
finding=obj('findings.json')['findings'][0]
assert finding['severity']=='P2' and finding['id']=='EV-DASH-01'
counter=finding['source_counterexample']
rows=list(csv.DictReader(io.StringIO(blob(counter['commit'],counter['path']).decode())))
row=rows[counter['csv_logical_record_including_header']-2]
assert row['route']=='KUF-SVX' and row['hypotheses']=='C03' and row['coverage_status']=='PARTIAL_POSITIVE_EVIDENCE'
handoff=obj('handoff.json');assert handoff['verdict']=='CHANGES' and handoff['subject_sha']=='5101302f93c349268f4ba0ff26832ff261e1a9e7'
result=dict(review_sha=SHA,subject_sha=handoff['subject_sha'],verdict='CHANGES',review_output_hashes=len(outputs),source_blob_hashes=len(inputs),counterexample_rechecked=True,correction_sha='0f07ec43ad3cf515e3bafbb767ade9caa2ba984c',correction_review='PENDING_SEPARATE',no_acceptance_of=['market','fleet','award','fullPnL','cash','TEAM_ACCEPTED'])
Path(__file__).with_name('dashboard_review_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result))
