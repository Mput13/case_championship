"""Targeted SP04/SP07/SP08 checks using pinned P06 operations, not a full CE rerun."""
import copy,hashlib,importlib,json,subprocess,sys,types
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path

P=Path(__file__).resolve().parent;O=P/'sp_adapter'
def load(name):return json.loads((O/name).read_text())
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
checks=[]
def check(name,ok,detail=None):
 checks.append(dict(name=name,status='PASS' if ok else 'FAIL',detail=detail))
 if not ok:raise AssertionError(name+':'+str(detail))

# The old source/resource tranche is kept byte-identical, not regenerated for another approval.
old=json.loads((P/'output_manifest.json').read_text())
check('v1_payload118hashes_unchanged',len(old['files'])==118 and all(hashlib.sha256((P/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old['files']))
for r in load('input_manifest.json'):
 b=subprocess.check_output(['git','show',r['commit']+':'+r['path']])
 check('pinned_input:'+r['path'],hashlib.sha256(b).hexdigest()==r['sha256'])

# Verify the coordinator's P06 manifest, while loading only the two needed modules.
pin=load('p06_producer_fragments.json')['interface_commit'];prefix='context/35_full_programme_execution_20261112/P06/'
man=load('inputs/P06/output_manifest.json')
check('P06manifest45entries',len(man['files'])==45)
for r in man['files']:
 b=subprocess.check_output(['git','show',pin+':'+prefix+r['path']])
 check('P06manifest_hash:'+r['path'],hashlib.sha256(b).hexdigest()==r['sha256'])
pkg=types.ModuleType('p03_pinned_p06');pkg.__path__=[str((O/'inputs/P06/engine').resolve())];sys.modules[pkg.__name__]=pkg
ops=importlib.import_module('p03_pinned_p06.operations');common=importlib.import_module('p03_pinned_p06.common')
producer=load('inputs/P06/producer_contract.json')
branches=load('p06_producer_fragments.json')['branches']
operations={}
for branch,pair in branches.items():
 p,k=pair['project'],pair['keep']
 check('same_resource_envelope:'+branch,digest(p['fleet_calendar'])==digest(k['fleet_calendar']) and digest(p['keep_policy'])==digest(k['keep_policy']) and digest(p['committed_payment_refs'])==digest(k['committed_payment_refs']))
 check('required_context_fields:'+branch,set(producer['context_required'])<=set(p['context']))
 check('canonical_manifest_hash:'+branch,common.digest(p['input_manifest'])==p['context']['input_manifest_sha256'])
 check('shared_remaining_payment_unknowns:'+branch,all(r['amount'] is None and r['obligation_exists'] is None for r in p['committed_payment_refs']))
 check('missing_economics_not_toy_filled:'+branch,'markets' not in p and 'products' not in p and 'economic_events' not in p and 'cash_events' not in p)
 check('unknowns_not_false_empty_windows:'+branch,all(t['crew_windows'] is None and t['maintenance_intervals'] is None for t in p['fleet_calendar']) and all(a['crew_id'] is None and a['actual_aircraft_registration'] is None for a in p['assignments']))
 registered={a['assumption_id'] for a in p['assumptions']};used=[]
 def walk(x):
  if isinstance(x,dict):
   if 'assumption_id' in x:used.append(x['assumption_id'])
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk({k:v for k,v in p.items() if k!='assumptions'})
 check('P06_scalar_registered_assumption_refs:'+branch,all(isinstance(a,str) and a in registered for a in used))
 for f in p['flights']:
  check('physical_keys_and_seat_bridge:'+branch+':'+f['flight_instance_id'],f['origin_airport']!='MOW' and f['destination_airport']!='MOW' and f['physical_adjacent_leg'] is True and f['seats']-f['technical_blocked_seats']==f['saleable_seats'] and f['source_status']=='scenario' and f['scheduled_status']=='proposed')
 try:out=ops.check_operations(p)
 except common.ContractError as e:raise AssertionError('P06 field contract error:'+str(e))
 operations[branch]=out
 check('P06operations_status:'+branch,out['status']==('CONDITIONAL' if branch=='phased' else 'INFEASIBLE'),{'status':out['status'],'errors':len(out['errors']),'unknowns':len(out['unknowns'])})
 check('separate_reserve_not_used:'+branch,len(out['unused_aircraft'])==1 and out['unused_aircraft'][0].endswith('_01'))
 check('not_dispatch_ready:'+branch,out['dispatch_ready'] is False)

phased=branches['phased']['project'];fs=phased['flights']
pairs={tuple(sorted((f['origin_airport'],f['destination_airport']))) for f in fs}
count=Counter(f['destination_airport'] for f in fs if f['origin_airport']=='GOJ')
proof=load('ordinary_return_lower_bound.json')
check('eight_pairs60legs30returns',len(pairs)==8 and len(fs)==60 and sum(count.values())==30 and count==proof['frequencies_each_way'])
check('resource_lower_bound23days',proof['long_singletons']['count']==16 and proof['long_singletons']['minimum_long_plus_minimum_other']>8 and min(proof['roundtrip_proxy_block_hours'].values())*3>8 and 16+(14+1)//2==23 and 23>3*7)
out=operations['phased'];byday=Counter()
for r in out['rotations']:
 dep=datetime.fromisoformat(r['departure_utc'].replace('Z','+00:00'));arr=datetime.fromisoformat(r['arrival_utc'].replace('Z','+00:00'))
 byday[(r['aircraft_id'],dep.date().isoformat())]+=(arr-dep).total_seconds()/60
check('concrete_template23days_daily480max',len(byday)==23 and max(byday.values())<=480,{'aircraft_days':len(byday),'max_block_minutes_per_unit_day':max(byday.values()),'total_block_minutes':sum(byday.values())})
check('no_synthetic_actual_registrations',all(t['actual_aircraft_registration'] is None for t in phased['fleet_calendar']))
advisory=load('crew_advisory.json')
check('separate_crew_headroom_not_sufficiency',advisory['four_landing_maximum_departure_to_arrival_minutes']==599 and advisory['remaining_minutes_for_combined_pre_post_duty_if_ordinary_day_report']==31)

def must_reject(label,mutator,substring):
 b=copy.deepcopy(phased);mutator(b)
 try:r=ops.check_operations(b)
 except common.ContractError as e:
  check(label,substring.lower() in str(e).lower(),str(e));return
 check(label,any(substring.lower() in e.lower() for e in r['errors']),r['errors'][:3])

must_reject('SP04_MOW_rejected',lambda b:b['flights'][0].update(origin_airport='MOW'),'MOW')
must_reject('SP04_seat_bridge_rejected',lambda b:b['flights'][0].update(technical_blocked_seats=2),'saleable seat bridge')
def duplicate(b):
 f=dict(b['flights'][0]);f['flight_instance_id']='DUPLICATE_MARKETING_ID';b['flights'].append(f)
must_reject('SP04_duplicate_physical_leg_rejected',duplicate,'duplicate physical flight')
def reserve(b):b['assignments'][0]['aircraft_id']=b['fleet_calendar'][0]['aircraft_id']
must_reject('SP07_reserve_assignment_rejected',reserve,'reserve_intervals')
def disconnect(b):
 first=b['assignments'][0]['flight_instance_id'];b['assignments']=[a for a in b['assignments'] if a['flight_instance_id']!=first];b['flights']=[f for f in b['flights'] if f['flight_instance_id']!=first]
must_reject('SP07_missing_positioning_leg_rejected',disconnect,'tail at GOJ')
def overlap(b):
 b['assignments'][1]['aircraft_id']=b['assignments'][2]['aircraft_id']
must_reject('SP07_overlapping_or_disconnected_assignment_rejected',overlap,'tail at')
mutated=copy.deepcopy(branches['phased']['keep']);mutated['fleet_calendar']=mutated['fleet_calendar'][1:]
check('SP08_erase_unused_reserve_changes_envelope',digest(mutated['fleet_calendar'])!=digest(phased['fleet_calendar']))
mutated=copy.deepcopy(branches['phased']['keep']);mutated['committed_payment_refs']=[]
check('SP08_erase_payment_refs_changes_envelope',digest(mutated['committed_payment_refs'])!=digest(phased['committed_payment_refs']))

result={'status':'PASS_TARGETED_SP04_SP07_SP08_INPUT_CHECKS','checks_passed':len(checks),'author_checks_not_independent_review':True,'method_contract_commit':'b7d74e67dd6c603db049b1915b1afec987e3b458','P06_interface_commit':pin,'P06manifest45hashes_verified':True,'prior_v1_payload118hashes_unchanged':True,'P06_check_operations':{k:{'status':v['status'],'errors_count':len(v['errors']),'unknowns_count':len(v['unknowns']),'unused_aircraft':v['unused_aircraft'],'dispatch_ready':v['dispatch_ready']} for k,v in operations.items()},'template':{'flights':60,'physical_pairs':8,'return_aircraft_days':23,'working_scenario_units':4,'reserve_scenario_units':1,'maximum_daily_block_minutes':max(byday.values()),'weekly_block_minutes_after_minute_rounding':sum(byday.values())},'new_rejections_exercised':['MOW','seat bridge','duplicate physical leg','reserve use','missing positioning','assignment position/overlap','changed P/KEEP envelope','erased unresolved payments'],'full_P06_evaluate_compare_scenario':'NOT_RUN: producer fragments omit genuine P04/P05/P07 contributions; no toy demand or money imputed','full_CE_suite':'NOT_RUN; only affected operations/interface cases checked','actual_crew_MRO_airports_and_demand_days':'UNKNOWN','raw_operations_result_file':'p06_operations_results.json'}
(O/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(O/'p06_operations_results.json').write_text(json.dumps(operations,ensure_ascii=False,indent=2)+'\n')
(O/'targeted_check_details.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
