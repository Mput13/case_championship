#!/usr/bin/env python3
"""Admit an exact independent review without extending its subject."""
import hashlib, json, math, subprocess
from pathlib import Path
SHA='bd2c27d2157d29d04fa1b3201e01392786fb035f'
SUBJECT='48686bf2276c435d7a260f4de6741c9b65d26e32'
ROOT='context/28_evening_run_20261110/selection_review/'
def blob(s,p): return subprocess.check_output(['git','show',s+':'+p])
def obj(p): return json.loads(blob(SHA,ROOT+p))
out=obj('output_manifest.json');source=obj('source_manifest.json');handoff=obj('handoff.json');findings=obj('findings.json')
assert all(x['subjectSHA']==SUBJECT for x in (out,source,handoff,findings))
for r in out['files']:
 b=blob(SHA,ROOT+r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
for r in source['files']:
 b=blob(SUBJECT,r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
 assert subprocess.check_output(['git','rev-parse',SUBJECT+':'+r['path']]).decode().strip()==r['git_blob']
assert handoff['verdict']==findings['verdict']=='APPROVE_SCOPED' and not findings['blocking_findings']
fixture=obj('evidence/calendar_fixture.json')
original=11250*.5*(1-math.exp(-1))
assert math.isclose(original,fixture['original_48_concentration_sold_year'])
assert math.isclose(original*48/52,fixture['lost4_no_recapture_sold_year'])
assert fixture['actual_calendar_acceptance'] is False and handoff['newer_remote_subject_accepted'] is False
result={'review_sha':SHA,'subject_sha':SUBJECT,'status':'APPROVE_SCOPED_RECEIPT_ADMITTED','checks':{'review_output_hashes':len(out['files']),'subject_blob_hashes_and_ids':len(source['files']),'independent_calendar_example':'11250*0.5*(1-exp(-1))*48/52'},'accepted_scope':'v1 selection arithmetic, incumbent preservation and separate gate/calendar experiments only','not_accepted':['methods aa777 v2','actual market and free fleet','future subsidy award','full PnL/cash','global optimum','19-pair diagnostic as final8-12network'],'review_reexecuted_by_root':False}
Path(__file__).with_name('selection_review_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
