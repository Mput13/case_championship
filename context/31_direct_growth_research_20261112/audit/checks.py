"""Artifact acceptance: provenance, user calendar and shared-resource boundaries."""
import pathlib,json,csv,hashlib,subprocess
R=pathlib.Path(__file__).resolve().parent
c=json.loads((R/'common_contract.json').read_text());receipt=json.loads((R/'replay_receipt.json').read_text());manifest=json.loads((R/'source_manifest.json').read_text())
for x in manifest:
 p=pathlib.Path(x['local_path']);assert p.is_relative_to(R/'inputs/audit_model')
 b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256']
 assert hashlib.sha256(subprocess.check_output(['git','show',x['commit']+':'+x['path']],cwd=R)).hexdigest()==x['sha256']
assert c['resource']['existing_slots']==[0,1,2]
assert c['resource']['deliveries']['S0']==[]
for scenario,events in c['resource']['deliveries'].items():
 for e in events:assert '2027-07-01'<=e['delivery']<e['entry']
assert c['support_cases']['NS']['route_support']==c['support_cases']['NS']['fuel_credit']==0
assert not receipt['market_true'] and not receipt['full_baseline_pipeline_replayed']
assert len(receipt['runs'])==6 and all(x['exit_code']==0 for x in receipt['runs'])
checks=json.loads((R/'replay/p06/mechanical_checks.json').read_text())
assert len(checks['last_run_selection'])==42
variants=list(csv.DictReader((R/'variant_map.csv').open()));assert len(variants)==12
routes=list(csv.DictReader((R/'route_universe.csv').open()));coverage=json.loads((R/'seed_coverage.json').read_text())
assert set(coverage['longlist_nodes'])<={x[k] for x in routes for k in ['origin','destination']}
assert subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=R.parents[2],text=True)==''
result={'status':'PASS','checks':['exact blobs and SHA256','all scenarios no newSJ beforeH22027','NS both support zero','common0/1/2existing working slots','42synthetic engine checks and3CLI only','subset replay labelled','all longlist nodes retained','tracked files unchanged'],'source_files':len(manifest),'seed_pairs':len(routes),'p06_checks':42,'new_market_validation':False}
(R/'artifact_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
