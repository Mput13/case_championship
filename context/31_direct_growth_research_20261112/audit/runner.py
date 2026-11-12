"""Run scoped author checks and exact legacy functions; no checkout, network or source writes."""
import pathlib,subprocess,sys,json,shutil,hashlib,datetime
R=pathlib.Path(__file__).resolve().parent
I=R/'inputs/audit_model';P='context/35_full_programme_execution_20261112/P06'
receipt={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'market_true':False,'full_baseline_pipeline_replayed':False,'baseline_adapter':'AST copies exact function definitions; processed CSV adapter, no forecast refit, no formula fallback; subset only','limitations':['Raw TOCHNO file not tracked/available','numpy/pandas not installed; installation failed SSL UNEXPECTED_EOF_WHILE_READING','No completed accepted actual P/KEEP full RW input bundle'],'runs':[]}
for x in json.loads((R/'source_manifest.json').read_text()):
 p=pathlib.Path(x['local_path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],p
D=R/'replay/p06';shutil.rmtree(D,ignore_errors=True);shutil.copytree(I/'982f13d9'/P,D)
commands=[([sys.executable,'check_engine.py'],D,'p06_checks.log'),([sys.executable,'-m','engine','evaluate','examples/evaluate_bundle.json','--out','evaluate_replayed.json'],D,'p06_evaluate.log'),([sys.executable,'-m','engine','compare','examples/demo_bundle.json','--out','compare_replayed.json'],D,'p06_compare.log'),([sys.executable,'-m','engine','scenario','examples/scenario_bundle.json','--out','scenario_replayed.json'],D,'p06_scenario.log'),([sys.executable,str(R/'replay_baseline.py')],R,'baseline_subset.log'),([sys.executable,str(R/'build_audit.py')],R,'build_audit.log')]
for cmd,cwd,log in commands:
 p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True);(R/'replay'/log).write_text(p.stdout+p.stderr)
 receipt['runs'].append(dict(command=cmd,cwd=str(cwd),exit_code=p.returncode,log='replay/'+log));assert p.returncode==0,(cmd,p.stderr)
checks=json.loads((D/'mechanical_checks.json').read_text());receipt['p06_check_summary']={k:v for k,v in checks.items() if k not in ['checks','results','source_hashes']};receipt['baseline_subset']=json.loads((R/'replay/baseline_subset.json').read_text())
receipt['tracked_status']=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=R.parents[2],text=True)
receipt['tracked_count']=len(subprocess.check_output(['git','ls-files'],cwd=R.parents[2],text=True).splitlines());assert receipt['tracked_status']=='' and receipt['tracked_count']==436
receipt['source_manifest_sha256']=hashlib.sha256((R/'source_manifest.json').read_bytes()).hexdigest();receipt['runner_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
(R/'replay_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print('PASS: P06 checks + 3 CLIs + baseline subset + artifact build; tracked436 unchanged')
