#!/usr/bin/env python3
"""Bounded root intake of first evidence/digital slices; no market acceptance."""
import csv
import hashlib
import io
import json
import math
import subprocess
import tempfile
from pathlib import Path

E='06cb721b3e8e4eb8710c065c7b02078a112626a9'
D='45c3bf06384ea5a6608eb5435aeb4f80cab3a1e2'
EP='context/28_evening_run_20261110/evidence/'
DP='context/28_evening_run_20261110/digital_growth/'
def blob(s,p): return subprocess.check_output(['git','show',s+':'+p])
def csvrows(s,p): return list(csv.DictReader(io.StringIO(blob(s,p).decode())))
def near(a,b): assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-7),(a,b)
checks={}
manifest=json.loads(blob(E,EP+'input_manifest.json'))
for r in manifest:
    b=blob(E,EP+r['snapshot'])
    assert b==blob(r['commit'],r['path'])
    assert hashlib.sha256(b).hexdigest()==r['sha256']
checks['evidence_git_inputs']=len(manifest)
registry=csvrows(E,EP+'source_registry.csv');captured=0
for r in registry:
    receipt=json.loads(blob(E,EP+r['receipt_path']))
    assert r['source_id']==receipt['source_id'] and r['url']==receipt['url']
    if r['raw_path']:
        b=blob(E,EP+r['raw_path']);assert hashlib.sha256(b).hexdigest()==r['sha256']==receipt['sha256']
        assert len(b)==int(r['bytes'])
        t=blob(E,EP+r['text_path']);assert hashlib.sha256(t).hexdigest()==r['text_sha256']==receipt['text_sha256']
        captured+=1
checks['web_receipts']=len(registry);checks['raw_text_pairs']=captured
with tempfile.TemporaryDirectory(prefix='case5-pdf-intake-') as tmp:
    for sid in ('favt_regional_rules','favt_2026_pdf'):
        pdf=Path(tmp)/(sid+'.pdf');pdf.write_bytes(blob(E,EP+f'raw/web/{sid}/source.pdf'))
        text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'])
        assert text==blob(E,EP+f'raw/web/{sid}/text.txt')
checks['independent_pdf_text_reextractions']=2
rules=blob(E,EP+'raw/web/favt_regional_rules/text.txt').decode()
other=blob(E,EP+'raw/web/favt_2026_pdf/text.txt').decode()
for phrase in ['22-64160-00191','количества выполненных рейсов','только одному','размера субсидии, предоставляемой на один рейс','на все места в салоне экономического класса']:
    assert phrase in rules,phrase
assert '22-68861-00481' in other
pairs=csvrows(E,EP+'pair_registry.csv');links=csvrows(E,EP+'pair_hypothesis_join.csv')
assert len(pairs)==40 and len({x['route'] for x in pairs})==40
assert len(links)==64 and {x['hypothesis'] for x in links}=={'C01','C03','C04','C07','C10','C14','C17','C31','C33','C35'}
assert all(x['route'] in {r['route'] for r in pairs} for x in links)
checks['unique_pairs']=40;checks['hypothesis_links']=64
matched=csvrows(E,EP+'subsidy_route_matches.csv')
rwijk=[x for x in matched if x['route']=='IJK-SVX' and 'Ред Вингс' in x['airline']]
assert len(rwijk)==1 and rwijk[0]['period']=='01.11.2026-31.12.2026'
assert any(x['route']=='KJA-OMS' and 'Аэрофлот' in x['airline'] for x in matched)
caps=csvrows(E,EP+'subsidy_cap_84_103_seats.csv');examples=csvrows(E,EP+'subsidy_cap_examples.csv')
for x in examples:
    km=float(x['official_km']);eligible=[c for c in caps if float(c['min_km'])<=km<=(float(c['max_km']) if c['max_km'] else math.inf)]
    assert len(eligible)==1
    near(x['appendix1_cap_rub_oneway'],eligible[0]['cap_rub_per_oneway_flight'])
    near(x['example_roundtrip_envelope_rub'],2*float(x['appendix1_cap_rub_oneway'])*float(x['coefficient_assumed_for_example']))
checks['cap_examples']=len(examples)

p=json.loads(blob(D,DP+'parameters.json'))
digital=csvrows(D,DP+'digital_thresholds.csv')
for r in digital:
    x=next(x for x in p['digital_scenarios'] if (x['id'],x['scenario'])==(r['id'],r['scenario']))
    gain=x['eligible_events']*x['uplift_absolute']*x['unit_contribution_rub']
    cost=x['cannibalized_contribution_rub']+x['annual_support_cash_rub']+x['implementation_cash_rub']
    near(gain-cost,r['first_year_result_after_implementation_rub'])
    near(cost/(x['eligible_events']*x['unit_contribution_rub']),r['break_even_uplift_absolute'])
resource=csvrows(D,DP+'resource_scale.csv')
for r in resource:
    target=float(r['target_passenger_segments_per_year']);delta=target-p['red_wings_passengers']
    capacity=float(r['seats'])*float(r['load_factor'])*365*float(r['productive_hours_per_active_day'])*float(r['availability_including_reserve'])/float(r['block_hours_per_leg'])
    near(capacity,r['passenger_segments_per_stock_year'])
    assert math.ceil(delta/capacity)==int(r['additional_stock_equivalent_ceil'])
checks['digital_arithmetic_rows']=len(digital);checks['resource_arithmetic_rows']=len(resource)
assert len(digital)==6 and len(resource)==16
result={'evidence_sha':E,'digital_sha':D,'status':'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING','checks':checks,'source_read_findings':['Regional grant and Far East program identities differ','Regional rule uses completed flights and contracted rate/cap/coefficient, not universal1773 per segment','Regional support includes fare obligations; grant upper cap must not be added to unconstrained ticket income','2026 program listing is not a2027 award or payment','Resource equivalents and digital outcomes are diagnostic assumptions, not forecasts'], 'not_run':['full service parser replay','independent live booking journey','full national numeric ranking','future subsidy entitlement'], 'native_web_errors':[{'url':'https://old.favt.gov.ru/public/materials/0/3/9/e/7/039e77a7205ca81e3070590870e45a3e.pdf','error':'TimeoutError'},{'url':'https://favt.gov.ru/public/materials/f/c/d/d/4/fcdd4e01332f1ac475410a0a009a66be.pdf','error':'(400) Timeout fetching'}], 'fallback':'Exact committed PDF hashes and independent pdftotext extraction; no infrastructure changes'}
Path(__file__).with_name('evidence_digital_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
