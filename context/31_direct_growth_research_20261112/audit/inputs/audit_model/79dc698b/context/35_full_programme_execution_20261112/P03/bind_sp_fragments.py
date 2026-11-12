"""Bind P06 fragments to an existing immutable P03 payload commit (no circular hash)."""
import argparse,hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent;O=P/'sp_adapter';PREFIX='context/35_full_programme_execution_20261112/P03/'
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--producer-commit',required=True);args=parser.parse_args()
commit=subprocess.check_output(['git','rev-parse',args.producer_commit+'^{commit}'],text=True).strip()
paths=['build_sp_adapter.py','sp_adapter/flights_sp04.csv','sp_adapter/fleet_calendar_sp07.csv','sp_adapter/assignments_sp07.csv','sp_adapter/keep_policies_sp08.csv','sp_adapter/committed_payment_refs.csv','sp_adapter/prior_task_refs.csv','sp_adapter/diagnostic_resource_events_v2.csv','sp_adapter/assumptions_register_v2.json','sp_adapter/p06_producer_fragments.json','sp_adapter/ordinary_return_lower_bound.json']
bound=[]
for path in paths:
 b=subprocess.check_output(['git','show',commit+':'+PREFIX+path])
 bound.append(dict(source_id='P03_V2_'+path.replace('/','_'),commit=commit,path=PREFIX+path,sha256=hashlib.sha256(b).hexdigest()))
fragments=json.loads(subprocess.check_output(['git','show',commit+':'+PREFIX+'sp_adapter/p06_producer_fragments.json']))
def owned_hashes(tree):return {branch:{arm:{k:digest(b[k]) for k in ['flights','fleet_calendar','assignments','keep_policy','committed_payment_refs','prior_task_refs','assumptions']} for arm,b in pair.items()} for branch,pair in tree['branches'].items()}
original_data=owned_hashes(fragments)
for pair in fragments['branches'].values():
 for b in pair.values():
  b['input_manifest']+=bound;b['context']['input_manifest_sha256']=digest(b['input_manifest'])
assert original_data==owned_hashes(fragments)
fragments['producer_payload_commit']=commit
fragments['binding']='These derived fragments bind unchanged P03 table data/adapter and the unbound fragment at the exact producer payload commit. Only manifest/context binding changes.'
dest=O/'p06_bound_fragments.json';dest.write_text(json.dumps(fragments,ensure_ascii=False,indent=2)+'\n')
proof={'producer_payload_commit':commit,'producer_inputs':bound,'preferred_P06_file':'sp_adapter/p06_bound_fragments.json','sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'checks':{'all_input_blobs_exist_and_hash':True,'owned_operating_data_unchanged':original_data==owned_hashes(fragments),'all_context_hashes_match':all(b['context']['input_manifest_sha256']==digest(b['input_manifest']) for pair in fragments['branches'].values() for b in pair.values())},'operational_acceptance':'UNCHANGED CONDITIONAL/INFEASIBLE as in verification.json; no new model calculation','financial_evaluate_compare':'NOT_RUN; producer fragment still needs genuine P04/P05/P07 inputs'}
(O/'binding_manifest.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'producer_payload_commit':commit,'bound_input_files':len(bound),'bound_fragment_sha256':proof['sha256']}))
