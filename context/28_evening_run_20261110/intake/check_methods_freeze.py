#!/usr/bin/env python3
"""Metadata-only admission of the final methods envelope; no new analytical verdict."""
import csv,hashlib,io,json,subprocess
from functools import lru_cache
from pathlib import Path
FINAL='5512f7d474a5db4bb658aae30b10f8b886629861'
PRIOR='9f0b5d25af720107e99e209e1c69b098497358be'
NIGHT='a77e4cfbd14e560d26407479b7252cfcb15f4f41'
P='context/28_evening_run_20261110/methods/'
@lru_cache(maxsize=None)
def blob(s,p):return subprocess.check_output(['git','show',s+':'+p])
def obj(p):return json.loads(blob(FINAL,P+p))
manifest=obj('output_manifest.json')['files']
assert len(manifest)==len({r['path'] for r in manifest})==496
for r in manifest:
    b=blob(FINAL,P+r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
old=json.loads(blob(PRIOR,P+'output_manifest.json'))['files']
changed=[];preserved=[]
for r in old:
    (preserved if blob(FINAL,P+r['path'])==blob(PRIOR,P+r['path']) else changed).append(r['path'])
assert len(preserved)==478 and set(changed)=={'README.md','handoff.json'}
assert 'strategy/acceptance_register.csv' in preserved
assert all(r['path'] in preserved for r in old if r['path'].endswith('.py') or r['path'].startswith('runs/'))
new_receipts=0
for folder in ['inputs/dated_review_994c','inputs/synthesis_review_934a']:
    receipt=obj(folder+'/receipt.json')
    for r in receipt['files']:
        b=blob(FINAL,P+folder+'/'+r['path'])
        assert b==blob(receipt['commit'],r['source_path'])
        assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
        new_receipts+=1
assert new_receipts==8
freeze=obj('freeze.json')
acceptance=list(csv.DictReader(io.StringIO(blob(FINAL,P+'final_acceptance.csv').decode())))
root=Path(__file__).resolve().parents[1]
root_acceptance=json.loads((root/'status.json').read_text())['review_admissions']
expected={(r['subject_sha'],r['review_sha'],r['verdict']) for r in root_acceptance}
assert len(expected)==len(acceptance)==len(freeze['subject_review_mapping'])==8
assert {(r['subject_sha'],r['review_sha'],r['verdict']) for r in acceptance}==expected
assert {(r['subject_sha'],r['review_sha'],r['verdict']) for r in freeze['subject_review_mapping']}==expected
assert all(r['team_accepted']=='False' for r in acceptance)
assert all(r['team_accepted'] is False for r in freeze['subject_review_mapping'])
for name,sha,subject,field in [('mr03','994c6c0d293ae6053b4e73b279689c5020314e09','f99d6cd52dcc06995bf984fddd2f057226243b06','held_claims'),('mr04','934a32f87ad81adbb6808be3aa50d6072276e779',PRIOR,'boundaries')]:
    event=obj('qualification_event_'+name+'.json')
    rp='dated_comparison_review' if name=='mr03' else 'strategy_synthesis_review'
    original=json.loads(blob(sha,'context/28_evening_run_20261110/'+rp+'/findings.json'))
    assert event['review_commit']==sha and event['subject_commit']==subject
    assert event[field]==original[field] and event['verdict']=='APPROVE_SCOPED'
assert not subprocess.check_output(['git','diff','--name-only',NIGHT,FINAL,'--','context/23_night_run_20261110'])
frozen_at=freeze['owner_frozen_at_utc']
assert frozen_at=='2026-11-10T17:47:39+00:00'
assert freeze['root_global_input_cutoff_msk']=='2026-11-10T21:15:00+03:00'
assert obj('handoff.json')['current_qualification']=='final_acceptance.csv; historical strategy/acceptance_register.csv unchanged'
result=dict(subject_sha=FINAL,analytical_subject=PRIOR,status='METADATA_ONLY_INTAKE_PASS',checks=dict(output_hashes=496,prior_byte_identical=478,prior_changed=changed,new_review_blobs=8,exact_subject_review_mappings=8,MR03_held_claims=11,MR04_boundaries=6,night_diff_empty=True),owner_frozen_at_utc=frozen_at,global_cutoff_unchanged=True,new_calculations=False,review_extended=False,task_complete=False,reproduction_qualification='Freeze bytes are immutable. Replay in a disposable copy; annual_market_caps.csv is semantically equal by keys but may differ in set-derived row order (EV-MR03). Byte hash drift after rerun does not by itself show changed numbers; do not overwrite frozen outputs.',remaining=['dashboard/passport assembly and its bounded verification','root final requirement closure and team handoff'])
Path(__file__).with_name('methods_freeze_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
