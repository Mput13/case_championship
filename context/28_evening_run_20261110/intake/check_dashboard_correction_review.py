import hashlib,json,subprocess
from pathlib import Path
SHA='bb80c5902461fc7861d16c53aae13eca98a2d94f'
P='context/28_evening_run_20261110/dashboard_context_correction_review/'
def blob(s,p):return subprocess.check_output(['git','show',s+':'+p])
def obj(p):return json.loads(blob(SHA,P+p))
outputs=obj('output_manifest.json');inputs=obj('source_manifest.json')
for r in outputs:
 b=blob(SHA,P+r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
for r in inputs:
 b=blob(r['commit'],r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
h=obj('handoff.json');assert h['verdict']=='APPROVE_SCOPED' and h['root_commit']=='0f07ec43ad3cf515e3bafbb767ade9caa2ba984c'
root='context/28_evening_run_20261110/integration/dashboard_context_correction/'
d=json.loads(blob(h['root_commit'],root+'route_context.json'))
aliases=[r for r in d['rows'] if r.get('association_id')=='CALCULATION_LEG_CONTEXT:C33:KUF-SVX']
assert len(aliases)==34 and all(r['route']=='KUF-SVX' and r['hypothesis_id']=='C33' for r in aliases)
assert not any(r['route']=='KUF-SVX' and r['hypothesis_id']=='C33' and r['record_type']=='calculation_pair_gap' for r in d['rows'])
original=json.loads(blob(h['original_assembly_commit'],'context/28_evening_run_20261110/dashboard_handoff/route_context.json'))
byid={r['record_id']:r for r in original['rows']}
for r in aliases:
 source=byid[r['original_evidence_record_id']]
 assert r['source_fields']==source['source_fields'] and r['provenance']==source['provenance']
result=dict(review_sha=SHA,subject_sha=h['root_commit'],verdict=h['verdict'],review_output_hashes=len(outputs),source_hashes=len(inputs),aliases_rechecked=34,original_verdict='CHANGES_RETAINED_EXACT5101302',scope='Only ROOT-DASH-01 corrected projection; no economic/market/fleet/award/UI acceptance')
Path(__file__).with_name('dashboard_correction_review_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
