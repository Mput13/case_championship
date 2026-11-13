#!/usr/bin/env python3
"""Validate bounded outputs, then write handoff and hash manifest; no external actions."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
required=['README.md','candidate_resource_requirements.csv','dated_templates.csv','verification.json',
          'assumptions.json','inputpins.json','base_resource_requirements.csv','rotations.csv','return_windows.csv',
          'operations_results.json','adversarial_probes.json','reserve_substitution_probes.json',
          'pair_block_assumptions.csv','tail_week_utilisation.csv','build_package.py']
for f in required:
    assert (ROOT/f).is_file(),f
v=json.loads((ROOT/'verification.json').read_text())
assert not v['hard_check_failures'],v['hard_check_failures']
ops=json.loads((ROOT/'operations_results.json').read_text())
assert all(o['status']=='CONDITIONAL' and not o['errors'] for o in ops)
for p in ROOT.rglob('*.json'):
    json.loads(p.read_text())
with (ROOT/'dated_templates.csv').open() as f:
    flights=list(csv.DictReader(f))
assert len(flights)==v['counts']['flights']
assert len({f['template_flight_id'] for f in flights})==len(flights)
assert all(f['seats']=='' and f['saleable_seats']=='' for f in flights)
pins=json.loads((ROOT/'inputpins.json').read_text())
for s in pins['sources']:
    if s['local_copy']:
        assert hashlib.sha256((ROOT/s['local_copy']).read_bytes()).hexdigest()==s['sha256'],s['source_path']

def write(name,obj):
    (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

handoff={
    'package':'context/42_consensus_strategy_20261113/resource_scenarios',
    'status':'BOUNDED_PACKAGE_COMPLETE_CONDITIONAL',
    'overall_strategy_accepted':False,
    'dispatch_ready':False,
    'recommended_slide_statement':'5 готовых:8 пар;6:10 пар;7:12 пар по3RT наOMS;8:12 пар с5RT наOMS–Москва/Иркутск. Условный ресурс, не график поставки.',
    'root_hypothesis_assessment':{
        'under4':'Retain3 Moscow=2working+1standby; explicit1KEEP; deferOMS.',
        'pilot5':'Retain2+1 Moscow and1+1OMS for2OMS pairs.',
        'plan6':'Retain2+1 Moscow and2+1OMS for4OMS pairs.',
        'extra8':'Retain2+1 Moscow and4+1OMS only with explicit frequency deployment; candidate raises Moscow/IKT to5RT.',
        'additional7':'Constructed2+1 Moscow and3+1OMS supports6OMS pairs at3RT; not a universal minimum.',
        'delayed':'Actual ready threshold gates activation; no invented dates or capacity.',
        'no_new':'Existing aircraft require named donor and loss of previous tasks; otherwise no incremental new-resource programme.'
    },
    'calendar_change':'Both orientations same dates: AER/VOG MonThu;GSV/MRV TueFri; two Moscow tails share both triangles.',
    'moscow_branch':{'main':'ZIA diagnostic only','sensitivity':'DME','chosen_airport':None,'observed_MOW_OD_reassigned':False},
    'date_scope':'Two representative dated seasonal weeks per candidate; no full2027-2028 schedule or annualisation.',
    'new_aircraft_earliest_boundary':'2027-07-01; actual delivery/service-entry UNKNOWN',
    'resource_proofs':{'P06_exact_pin':pins['pins']['P06'],'test_counts':v['counts'],
                      'hard_selected_template_failures':0,'base10h_all_runs':'CONDITIONAL',
                      'negative_controls':'wrong location,turn shortfall,reserve without release,variant mismatch all rejected',
                      'return_calendar':'Every tested direct departure has3or4-night and7-night return in repeated pattern; seats and utility UNKNOWN'},
    'material_findings':v['findings'],
    'finance':{'joint_PnL':None,'funding':None,'growth':None,'old_profit_reused':False,'status':'NOT_RUN_UNKNOWN'},
    'required_before_commercial_use':['physical Moscow airport','actual ready and released tail IDs/dates',
                                     'separate base crew and standby roster','type-qualified MRO and reserve response',
                                     'actual directional seasonal blocks,payload and slots','KEEP and donor/alternative cost',
                                     'joint demand,fares,costs,cash and financing'],
    'files':required,
    'manifest':'output_manifest.json',
    'actions':{'children':0,'web_or_paid_calls':0,'servers':0,'bookings':0,'restarts':0,
               'git_mutations':0,'git_reads':'exact git show only','writes':'assigned resource_scenarios directory only'},
    'handoff_state':'STOP; no further polling or work requested'
}
write('handoff.json',handoff)
files=[]
for p in sorted(ROOT.rglob('*')):
    if p.is_file() and p.name!='output_manifest.json':
        raw=p.read_bytes()
        files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
manifest={'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),
          'scope':'bounded resource diagnostic; all files below assigned folder',
          'self_excluded':'output_manifest.json','files':files,'file_count':len(files)}
write('output_manifest.json',manifest)
# In-process verification before final stop; no external polling.
for item in manifest['files']:
    assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()==item['sha256']
print(json.dumps({'status':handoff['status'],'files_sealed':len(files),'counts':v['counts'],
                  'readme':str(ROOT/'README.md'),'handoff':str(ROOT/'handoff.json'),
                  'manifest_sha256':hashlib.sha256((ROOT/'output_manifest.json').read_bytes()).hexdigest()},ensure_ascii=False))
