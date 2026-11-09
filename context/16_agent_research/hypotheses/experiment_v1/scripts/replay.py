#!/usr/bin/env python3
"""Recompute every saved experiment from its exact own-code snapshot offline."""
from pathlib import Path
from datetime import datetime,timezone
import contextlib,hashlib,io,json,shutil,tempfile,types,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(relative,target):
    p=target/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,p)
def own_snapshot(module_name,script_hash,relative,target):
    source=ROOT/'snapshots'/(script_hash+'.blob');assert sha(source)==script_hash
    path=target/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source.read_bytes())
    module=types.ModuleType(module_name);module.__file__=str(path)
    exec(compile(path.read_text(),str(path),'exec'),module.__dict__)
    return module
def compare(expected_dir,actual_dir,manifest_name,field):
    manifest=json.loads((expected_dir/manifest_name).read_text());fail=[]
    for row in manifest[field]:
        p=actual_dir/row['path']
        if not p.exists() or sha(p)!=row['sha256']:fail.append(row['path'])
    assert not fail,fail
    return len(manifest[field])
def main():
    records=[];event={'utc':datetime.now(timezone.utc).isoformat(),'type':'OFFLINE_FRESH_RECOMPUTATION','network_used':False}
    temp_root=ROOT/'replay_tmp';temp_root.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=temp_root,prefix='fresh-') as directory:
            target=Path(directory)
            for rel in ['contract.json','scenario_programs.json','input_manifest.json','input_sets/phase2-frozen-002.json']:copy(rel,target)
            for rel in ['input_manifest.json','input_sets/phase2-frozen-002.json']:
                for row in json.loads((ROOT/rel).read_text())['inputs']:copy(row['stored_path'],target)
            # Each version computes new CSVs; existing published outputs are never modified.
            for run in ['86d92475089a6128','c26661067277af20']:
                expected=ROOT/'runs'/run;manifest=json.loads((expected/'output_manifest.json').read_text());h=manifest['input_hashes']['scripts/evaluate.py']
                module=own_snapshot('own_engine_'+run,h,'scripts/evaluate.py',target)
                out=target/'runs'/run;out.mkdir(parents=True)
                summary=module.evaluate(out,json.loads((target/'contract.json').read_text()),json.loads((target/'scenario_programs.json').read_text()),json.loads((target/'input_manifest.json').read_text()))
                module.write_json(out/'summary.json',summary)
                count=compare(expected,out,'output_manifest.json','files')
                copy('runs/'+run+'/output_manifest.json',target)
                records.append({'kind':'main_experiment','run_id':run,'recomputed_files':count,'status':'BYTE_IDENTICAL','script_sha256':h})
            for run in ['8762cfe3b8961b31','6cf441ef38e2c6c5']:
                expected=ROOT/'cost_resource'/run;manifest=json.loads((expected/'manifest.json').read_text());h=manifest['inputs']['script_sha256']
                module=own_snapshot('own_cost_'+run,h,'scripts/cost_resource_probe.py',target)
                with contextlib.redirect_stdout(io.StringIO()):module.main()
                count=compare(expected,target/'cost_resource'/run,'manifest.json','outputs')
                records.append({'kind':'cost_resource','run_id':run,'recomputed_files':count,'status':'BYTE_IDENTICAL','script_sha256':h})
            run='3906edd033f75bc6';expected=ROOT/'c14_products'/run;manifest=json.loads((expected/'output_manifest.json').read_text());h=manifest['input_hashes']['script']
            module=own_snapshot('own_product_'+run,h,'scripts/c14_product_probe.py',target)
            with contextlib.redirect_stdout(io.StringIO()):module.main()
            count=compare(expected,target/'c14_products'/run,'output_manifest.json','files')
            records.append({'kind':'C14_product','run_id':run,'recomputed_files':count,'status':'BYTE_IDENTICAL','script_sha256':h})
            for kind,run,script,hash_field in [('operating_join','126bccd230436e9f','core_operating_join.py','script_sha256'),('c14_calendar_flex','13bad5060a24f3ce','c14_calendar_flex.py','script')]:
                expected=ROOT/kind/run;manifest=json.loads((expected/'manifest.json').read_text());h=manifest['inputs'][hash_field]
                module=own_snapshot('own_'+kind,h,'scripts/'+script,target)
                with contextlib.redirect_stdout(io.StringIO()):module.main()
                count=compare(expected,target/kind/run,'manifest.json','files')
                records.append({'kind':kind,'run_id':run,'recomputed_files':count,'status':'BYTE_IDENTICAL','script_sha256':h})
        event.update(status='PASS',runs=records,total_recomputed_files=sum(x['recomputed_files'] for x in records),limits='Computational repeatability only; no observed demand, operating clearance or product inventory accepted')
    except Exception as e:
        event.update(status='FAIL',error_type=type(e).__name__,error=str(e));raise
    finally:
        (ROOT/'checks/fresh_replay.json').write_text(json.dumps(event,ensure_ascii=False,indent=2)+'\n')
        with (ROOT/'replay_attempts.jsonl').open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    print(json.dumps({'status':event['status'],'runs':len(records),'recomputed_files':event['total_recomputed_files']}))
if __name__=='__main__':main()
