#!/usr/bin/env python3
"""Immutable dashboard intake and optional byte-preserving import. No model execution."""
import argparse,csv,hashlib,io,json,subprocess
from functools import lru_cache
from pathlib import Path
SHA='5101302f93c349268f4ba0ff26832ff261e1a9e7'
P='context/28_evening_run_20261110/dashboard_handoff/'
ACTIVE={'C01','C03','C04','C07','C10','C14','C17','C31','C33','C35'}
@lru_cache(maxsize=None)
def blob(s,p):return subprocess.check_output(['git','show',s+':'+p])
def obj(p):return json.loads(blob(SHA,P+p))
@lru_cache(maxsize=None)
def table(s,p):return list(csv.DictReader(io.StringIO(blob(s,p).decode('utf-8-sig'))))
def source_row(prov):return table(prov['commit'],prov['path'])[prov['source_row']-2]
parser=argparse.ArgumentParser();parser.add_argument('--import-package',action='store_true');args=parser.parse_args()
manifest=obj('output_manifest.json')['outputs'];sources=obj('source_manifest.json')['sources']
assert len(manifest)==len({r['path'] for r in manifest})==70
for r in manifest:
    b=blob(SHA,P+r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
assert len(sources)==len({(r['commit'],r['path']) for r in sources})==129
for r in sources:
    b=blob(r['commit'],r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
cards=obj('cards.json')['cards'];program=obj('program_changes.json')['rows'];context=obj('route_context.json')['rows']
assert len(cards)==10 and {r['hypothesis_id'] for r in cards}==ACTIVE
assert len(program)==816 and len(context)==639
metric_count=0
for card in cards:
    assert card['team_accepted'] is False
    assert {'base','cautious'}<={m['scenario'] for m in card['metrics']}
    for m in card['metrics']:
        source=source_row(m['provenance'])
        assert source[m['metric']]==m['value'],(card['hypothesis_id'],m['metric'])
        assert source['scenario']==m['scenario']
        assert all(source[k]==v for k,v in m['variant'].items())
        assert m['unit'] and m['period'] and m['accounting_boundary']
        metric_count+=1
    assert all(x in {r['record_id'] for r in program} for x in card['program_change_ids'])
    assert all(x in {r['record_id'] for r in context} for x in card['route_context_ids'])
for group in [program,context]:
    assert len({r['record_id'] for r in group})==len(group)
    for r in group:
        assert r['hypothesis_id'] in ACTIVE
        source=source_row(r['provenance'])
        if r['record_type']=='calculation_pair_gap':
            # A declared derived gap keeps the calculation locator, not raw evidence fields.
            assert r['route']=='-'.join(sorted((source['origin'],source['destination'])))
            assert r['coverage_status']=='NOT_IN_EVIDENCE_PAIR_REGISTRY'
            assert not r['date'] and not r['price_value'] and not r['frequency_value']
            assert r['source_fields']['coverage_status']==r['coverage_status']
        else:
            assert r['source_fields']==source
for r in program:
    if r['record_type']=='route_delta':
        assert len(r['dated_flight_refs'])==1
        flight=source_row(r['dated_flight_refs'][0])
        assert flight['flight_id']==r['flight_id'] and flight.get('date',flight.get('service_date'))==r['date']
for r in table(SHA,P+'airports.csv'):
    if r['code']=='MOW':assert r['latitude']==r['longitude']=='' and r['status']=='CITY_AGGREGATE_UNRESOLVED'
annual=obj('dated_annual.json');assert len(annual['rows'])==96 and annual['subject_sha']=='f99d6cd52dcc06995bf984fddd2f057226243b06'
assert annual['review_sha']=='994c6c0d293ae6053b4e73b279689c5020314e09'
assert obj('source_manifest.json')['pins']['methods_final']=='5512f7d474a5db4bb658aae30b10f8b886629861'
png=[r for r in manifest if r['path'].endswith('.png')];assert len(png)==14
assert all(blob(SHA,P+r['path']).startswith(b'\x89PNG\r\n\x1a\n') for r in png)
coverage=table(SHA,P+'requirements_coverage.csv')
assert len(coverage)==24
result=dict(subject_sha=SHA,status='INTEGRITY_PASS_WITH_OPEN_CONTEXT_JOIN_FINDING',checks=dict(output_hashes=70,package_files_with_manifest=71,input_hashes=129,cards=10,exact_metric_cells_and_selectors=metric_count,program_source_rows=816,context_source_rows=639,dated_annual_cases=96,png=14,coverage_rows=24),open_findings=[dict(id='ROOT-DASH-01',route='KUF-SVX',hypothesis='C33',issue='NOT_IN_EVIDENCE_PAIR_REGISTRY is false globally: evidence38f pair exists, mapped to C03; published context not bridged to C33')],root_remaining=['fresh bounded assembly review','conditional roadmap and links to existing screening/regional-base research','final requirement closure and team handoff'],not_run=['new economics or research','actual UI integration/visual QA','market/fleet/award/fullPnL/cash acceptance'])
if args.import_package:
    target=Path(__file__).resolve().parents[1]/'integration/dashboard_handoff/5101302f'
    assert not target.exists(),'Refuse overwrite of imported immutable package'
    files=[r['path'] for r in manifest]+['output_manifest.json']
    for p in files:
        relative=Path(p);assert not relative.is_absolute() and '..' not in relative.parts
        dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob(SHA,P+p))
    result['byte_preserving_import']=str(target)
Path(__file__).with_name('dashboard_handoff_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
