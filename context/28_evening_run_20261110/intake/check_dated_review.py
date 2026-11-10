#!/usr/bin/env python3
"""Admit the immutable EV-MR03 review without broadening its exact scope."""
import csv, datetime as dt, hashlib, io, json, math, subprocess
from functools import lru_cache
from pathlib import Path

REVIEW = '994c6c0d293ae6053b4e73b279689c5020314e09'
SUBJECT = 'f99d6cd52dcc06995bf984fddd2f057226243b06'
RP = 'context/28_evening_run_20261110/dated_comparison_review/'
SP = 'context/28_evening_run_20261110/methods/'
@lru_cache(maxsize=None)
def blob(s,p): return subprocess.check_output(['git','show',s+':'+p])
def review(p): return json.loads(blob(REVIEW,RP+p))
def rows(p): return list(csv.DictReader(io.StringIO(blob(SUBJECT,SP+p).decode())))
def near(a,b): assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-5),(a,b)

out = review('output_manifest.json')
assert out['subject_commit'] == SUBJECT and out['verdict'] == 'APPROVE_SCOPED'
for r in out['files']:
    b=blob(REVIEW,RP+r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
sources=review('source_manifest.json')
assert sources['subject']==SUBJECT
for r in sources['files']:
    b=blob(SUBJECT,r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    oid=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    assert oid==r['git_blob']
handoff=review('handoff.json');findings=review('findings.json')
assert handoff['subject_commit']==findings['subject_commit']==SUBJECT
assert findings['verdict']==handoff['verdict']=='APPROVE_SCOPED'
assert findings['findings']==[] and all(n==0 for n in findings['severity_counts'].values())
assert len(findings['held_claims'])==11

annual=rows('runs/integer_year_v1/annual_comparison.csv')
oracle=review('annual_oracle_values.json')
assert len(annual)==len(oracle)==96
for r in annual:
    for k,v in oracle[r['case']].items(): near(r[k],v)
    assert r['actual_grant']==r['actual_fleet']==r['full_pnl']==''
raw=rows('inputs/products_3889/outputs/dated_flights.csv')
flights={r['flight_id']:r for r in raw}
assert len(raw)==len(flights)==402
examples=review('product_calendar_examples.json')
for r in examples['new_C31_and_first_C35_day']:
    source=flights[r['flight_id']]
    for k in ['origin','destination','departure_utc','arrival_utc','departure_local','arrival_local']: assert r[k]==source[k]
    for event in ['departure','arrival']:
        assert dt.datetime.fromisoformat(r[event+'_local']).astimezone(dt.timezone.utc)==dt.datetime.fromisoformat(r[event+'_utc'])
for r in examples['eligible_connections']:
    a,b=flights[r['first']],flights[r['second']]
    assert a['destination']==b['origin']=='SVX'
    wait=(dt.datetime.fromisoformat(b['departure_utc'])-dt.datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
    near(wait,r['wait']);assert 60<=wait<=180
    assert r['rw_variant']=='rw_KEEP_retimed'
assert len(examples['eligible_connections'])==16
added=[r for r in raw if r['hypothesis']=='C31' and r['network']=='ADD_SSJ_OMS']
assert len(added)==4 and {r['date'] for r in added}=={'2027-07-05','2027-07-08'}
feed=[r for r in raw if r['hypothesis']=='C35' and r['network']=='external_feed']
assert not ({r['date'] for r in added}&{r['date'] for r in feed})
products=review('product_oracle_values.json')
for s,r in products.items():
    assert r['partner_reserved']==160 and r['partner_payment']==480000
    near(r['C31_ceiling']+r['C35_contribution'],r['joint_ceiling'])
    matches=[x for x in rows('runs/joint_products_v1/joint_frontier.csv') if x['scenario']==s and float(x['Tu_old_mission_loss_probe'])==0]
    assert matches
    for x in matches: near(x['maximum_Tu_allin_plus_K_at_given_donor'],r['joint_ceiling'])
adversarial=review('adversarial_results.json')
assert adversarial['subject']==SUBJECT and adversarial['count']==len(adversarial['probes'])==32
assert sum(x['result']=='REJECTED_BY_REVIEW_ORACLE' for x in adversarial['probes'])==adversarial['rejected_mutations']==16
year_limit=next(x for x in adversarial['probes'] if x['name']=='year_split_policy_limit')
assert min(year_limit['synthetic_daily_working'])==year_limit['whole_week_minimum']==2
assert year_limit['per_year_minima']==[2,3] and year_limit['current_actual_cross_year_program_changes']==0
assert year_limit['result']=='HELD_OUTSIDE_PINNED_INPUTS'

result=dict(review_sha=REVIEW,subject_sha=SUBJECT,verdict='APPROVE_SCOPED',root_intake='PASS',checks=dict(review_hashes=len(out['files']),source_hashes=len(sources['files']),annual_comparisons=len(annual),dated_product_rows=len(raw),UTC_connections_checked=16,C31_new_no_feed=4,adversarial_receipts=32,held_claims=11),real_example=dict(first=examples['eligible_connections'][0]['first'],second=examples['eligible_connections'][0]['second'],wait_minutes=90,base_joint_ceiling=products['base']['joint_ceiling']),retained_new_limit=year_limit,not_run_by_root=['repeat full independent LP and yearly rotation replay','actual market/operating/award/fullPnL/cash acceptance'],acceptance_limits=['exact f99 only; v4 9f0 has separate review','specific fixed bank failure not impossibility of hub','retimed week not annual result','one C31 week plus full C35 contract; internal feed alternative separate','changed January supply requires shared-week selection before year split','all H1-H11 retained'])
Path(__file__).with_name('dated_review_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
