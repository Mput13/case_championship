#!/usr/bin/env python3
"""Root admission of EV-MR04: immutable identity and selected real examples."""
import csv,hashlib,io,json,math,subprocess
from functools import lru_cache
from pathlib import Path
REVIEW='934a32f87ad81adbb6808be3aa50d6072276e779'
SUBJECT='9f0b5d25af720107e99e209e1c69b098497358be'
RP='context/28_evening_run_20261110/strategy_synthesis_review/'
SP='context/28_evening_run_20261110/methods/'
@lru_cache(maxsize=None)
def blob(s,p):return subprocess.check_output(['git','show',s+':'+p])
def review(p):return json.loads(blob(REVIEW,RP+p))
def rows(p):return list(csv.DictReader(io.StringIO(blob(SUBJECT,SP+p).decode())))
def near(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-5),(a,b)
out=review('output_manifest.json');inputs=review('input_manifest.json')
assert out['subject_sha']==inputs['subject']==SUBJECT
for r in out['files']:
    b=blob(REVIEW,RP+r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
for r in inputs['files']:
    b=blob(r['commit'],r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
h=review('handoff.json');f=review('findings.json');c=review('checks.json');e=review('evidence.json')
assert h['subject_sha']==f['subject_sha']==c['subject']==SUBJECT
assert h['verdict']==f['verdict']=='APPROVE_SCOPED' and f['findings']==[]
assert len(c['checks'])==c['passed']==363 and c['failed']==0
assert all(r['passed'] for r in c['checks'])
assert h['EV_MR03']['recomputed'] is False and h['EV_MR03']['verdict_inherited'] is False
assert h['independent_checks']['owner_verifier_executed'] is False
assert len(e['selected_source_cells'])==20
for r in e['selected_source_cells']:
    source=list(csv.DictReader(io.StringIO(blob(SUBJECT,r['path']).decode())))
    cell=source[r['line']-2]
    assert cell['scenario']==r['scenario']
    assert all(cell[k]==v for k,v in r['selectors'].items())
    near(cell[r['column']],r['value'])
    card=next(x for x in rows('strategy/hypothesis_decisions.csv') if x['id']==r['id'])
    near(card[r['scenario']+'_value'],r['value'])
    assert card['unit']==r['unit'] and card['period']==r['period']
for r in e['mixed11']:
    assert r['open'] and r['raw_oneway_q2']<r['planning_seats_oneway_f2'] and r['raw_oneway_q4']<r['planning_seats_oneway_f4']
    near(r['q4_both_directions'],r['q2_both_directions']*(1+math.exp(-2/3)))
    near(r['correction'],(r['q4_both_directions']-r['naive_overlap'])*(r['fare']-r['pax_cost']))
    target=next(x for x in rows('strategy/mixed11_budget.csv') if x['scenario']==r['scenario'])
    near(target['shared_market_corrected_contribution'],r['corrected_total'])
    cap=r['capped_counterexample']
    near(cap['actual_q2'],2*r['planning_seats_oneway_f2'])
    near(cap['actual_q4'],2*r['planning_seats_oneway_f4'])
    near(cap['wrong_closed_form_q4'],cap['actual_q2']*(1+math.exp(-2/3)))
    assert not math.isclose(cap['actual_q4'],cap['wrong_closed_form_q4'],rel_tol=0.01)
for r in e['pair_grain_counterexamples']:
    route_rows=[x for x in rows('strategy/option_routes.csv') if x['option']==r['option']]
    assert len(route_rows)==r['program_rows']==9
    assert len({tuple(sorted((x['origin'],x['destination']))) for x in route_rows})==r['unique_pairs']==8
    freq=[x['frequency_each_direction_week'] for x in route_rows if sorted((x['origin'],x['destination']))==r['duplicate_pair']]
    assert sorted(freq)==sorted(r['frequencies'])
calendar=rows('runs/annual_v1/aircraft_calendar_daily.csv')
for r in e['resource_boundaries']:
    x=next(x for x in calendar if x['branch']=='PHASED' and x['availability']=='14D_GROUNDING_STRESS' and x['date']==r['date'])
    for k,field in [('working','working_new'),('entered','entered_new'),('grounded','planned_grounded_new'),('reserve','reserve_new')]:assert r[k]==int(x[field])
    assert r['entered']-r['grounded']-r['reserve']==r['working']
result=dict(review_sha=REVIEW,subject_sha=SUBJECT,verdict='APPROVE_SCOPED',root_intake='PASS',checks=dict(review_hashes=len(out['files']),input_hashes=len(inputs['files']),independent_check_receipts=363,selected_source_cells=20,mixed_actual_and_capped_examples=2,direct_pair_grain_examples=1,resource_boundary_examples=len(e['resource_boundaries'])),required_fixes=[],retained_limits=['conditional recommendation not TEAM_ACCEPTED or market readiness','one mixed local-only recipe not global optimum','q4 closed form valid only open/noncapped here','daily resource gate not weekly/tail/base/crew approval','historical support shadow not actual award','full PnL/cash and future company rank not accepted','EV-MR03 remains a separate exact f99 review'],not_run_by_root=['repeat 363 independent assertions','live market or operating validation'])
Path(__file__).with_name('strategy_review_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
