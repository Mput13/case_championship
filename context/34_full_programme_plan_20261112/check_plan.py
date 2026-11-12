#!/usr/bin/env python3
"""Check the proposed work graph and document links; not a model acceptance test."""
import csv
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent

class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'a':
            self.links.append(a.get('href', ''))

def main():
    spec = json.loads((BASE / 'common_spec.json').read_text())
    packages = json.loads((BASE / 'work_packages.json').read_text())['packages']
    by_id = {p['id']:p for p in packages}
    assert len(by_id) == len(packages), 'duplicate work package'
    seen, active, ordered = set(), set(), []
    def visit(key):
        assert key in by_id, f'unknown dependency {key}'
        assert key not in active, f'cycle at {key}'
        if key in seen:
            return
        active.add(key)
        for dep in by_id[key]['depends_on']:
            visit(dep)
        active.remove(key)
        seen.add(key)
        ordered.append(key)
    for key in by_id:
        visit(key)
    assert len({p['proposed_write_scope'] for p in packages}) == len(packages)
    assert all(p['task_id'] is None for p in packages)
    assert all(p['status'] == 'PREPARED_NOT_STARTED' for p in packages)
    with (BASE / 'requirements.csv').open() as f:
        reqs = list(csv.DictReader(f))
    assert len({r['id'] for r in reqs}) == len(reqs)
    assert all(r['primary_package'] in by_id and r['acceptance'] for r in reqs)
    with (BASE / 'method_map.csv').open() as f:
        methods = list(csv.DictReader(f))
    lock = json.loads((BASE / 'source_lock.json').read_text())
    source_ids = {s['id'] for s in lock['sources']}
    assert all(m['source_id'] in source_ids for m in methods)
    assert all(k in by_id for m in methods for k in m['packages'].split(','))
    assert spec['accepted']['fixed_finalist_quota'] is None
    assert spec['accepted']['person_day_estimates'] is False
    assert spec['judgement_register_policy']['required']
    assert spec['judgement_register_policy']['scenario_points_are_confidence_bounds'] is False
    ledger=json.loads((BASE/'assumptions_register.json').read_text())
    assert ledger['coverage_status']=='PARTIAL_SEED_REQUIRES_P01_SCAN'
    rows=ledger['records']
    assert len({r['assumption_id'] for r in rows})==len(rows)
    assert len([r for r in rows if r['assumption_id'].startswith('WEIGHT-')])==14
    assert len([r for r in rows if r['assumption_id'].startswith('NET-')])==51
    assert all(r['lower'] is None and r['upper'] is None for r in rows), 'do not invent confidence bounds from scenario points'
    assert next(r for r in rows if r['assumption_id']=='OPEN-BASE_SETUP')['base_value'] is None
    assert 'assumptions_final.csv' in by_id['P17']['outputs']
    policy=json.loads((BASE/'orchestration_policy.json').read_text())
    assigned=[k for r in policy['roles'].values() for k in r['packages']]
    assert set(assigned)==set(by_id)-{'P00'}
    assert len(assigned)==len(set(assigned)), 'multiple role assignments'
    assert policy['capacity']['max_active_children']==4
    assert policy['dispatch']['mode']=='async'
    assert by_id['P06']['target']['model']=='gpt-6-astra'
    assert by_id['P09']['target']['model']=='gpt-6-astra'
    assert by_id['P00R']['target']['model']=='gpt-6-astra'
    assert by_id['P14']['target']['model']=='gpt-6-astra'
    assert by_id['P13']['target']['model']=='gpt-6.1-sol'
    assert by_id['P13']['independence']['fresh_agent']
    assert by_id['P14']['independence']['fresh_agent']
    assert set(by_id['P14']['independence']['must_not_be_author_of']) >= {'P06','P09','P10','P11','P15'}
    assert 'P09' in by_id['P13']['independence']['must_not_be_author_of']
    assert all(by_id[k]['target']['options']['reasoningEffort']=='xhigh' for k in assigned)
    assert len(spec['accepted']['sections']) == 4
    assert not any(spec['execution_boundary'].values())
    assert set(by_id['P09']['depends_on']) >= {'P02','P03','P04','P05','P06','P07','P08'}
    assert set(by_id['P09']['depends_on']) >= {'P02I','P08I'}
    assert spec['international_and_fleet']['international_extensions_share_engine']
    assert spec['international_and_fleet']['case_sj_remains_independent']
    assert spec['international_and_fleet']['new_tu214_annual_schedule'] is None
    assert spec['fleet_scopes']['CASE_SJ']['new_tu214_required'] is False
    assert spec['fleet_scopes']['EXT_NO_NEW_TU214']['new_tu214_in_2027_2028'] == 0
    assert 'P08I' not in spec['result_release_gates']['CASE_SJ']
    def case_inputs(key):
        deps = by_id[key].get('standalone_case_release_dependencies', by_id[key]['depends_on'])
        return set(deps).union(*(case_inputs(d) for d in deps))
    assert not (case_inputs('P09') & {'P02I','P08I'}), 'case solution blocked by optional international/Tu214 work'
    assert 'P15' in by_id['P14']['depends_on'], 'review final whole-business bridge'
    assert set(by_id['P16']['depends_on']) >= {'P13','P14','P15'}
    doc = Document()
    doc.feed((BASE / 'plan.html').read_text())
    assert len(doc.ids) == len(set(doc.ids)), 'duplicate document id'
    for link in doc.links:
        if link.startswith('#'):
            assert link[1:] in doc.ids, link
        elif not link.startswith(('https://','http://','t3-thread://')):
            assert (BASE / link).is_file(), link
    manifest = json.loads((BASE / 'output_manifest.json').read_text())
    assert all(hashlib.sha256((BASE/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in manifest['files'])
    result = {'status':'PASS','scope':'planning_graph_and_document_only','packages':len(packages),'requirements':len(reqs),'methods':len(methods),'topological_order':ordered,'network_execution':'NOT_RUN','agent_launch':'NOT_RUN','market_or_strategy_acceptance':'NOT_ESTABLISHED'}
    (BASE / 'planning_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__ == '__main__':
    main()
