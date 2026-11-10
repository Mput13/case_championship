"""Remove only this review's disposable runtime, after process/open-file checks."""
import datetime,json,os,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
target=HERE/'_runtime'
assert target.parent==HERE and target.name=='_runtime'
ps=subprocess.check_output(['ps','-axo','pid=,command='],text=True)
names=('independent_checks.py','owner_replay.py','adversarial_checks.py','prepare.py','provenance_checks.py')
active=[r for r in ps.splitlines() if ('dated_comparison_review/' in r and any(n in r for n in names)) or str(target)+'/' in r]
assert not active,active
lsof=subprocess.run(['lsof','-t','+D',str(target)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) if target.exists() else None
assert lsof is None or not lsof.stdout.strip(),lsof.stdout if lsof else ''
assert lsof is None or lsof.returncode in (0,1),(lsof.returncode,lsof.stderr)
files=[p for p in target.rglob('*') if p.is_file()] if target.exists() else []
result=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),removed_path='_runtime/',files=len(files),bytes=sum(p.stat().st_size for p in files),matching_active_processes=active,open_file_pids=lsof.stdout.strip().splitlines() if lsof else [],removed=False)
if target.exists():shutil.rmtree(target)
result['removed']=not target.exists()
(HERE/'cleanup_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
